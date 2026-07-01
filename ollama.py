"""
ollama.py
---------
Envoie les prompts générés par erpnext.py
à Ollama (modèle Qwen3) installé sur ton serveur.
Récupère les recommandations et les sauvegarde.

Prérequis :
    pip install requests python-dotenv

Variables d'environnement (.env) :
    OLLAMA_URL = http://IP_DE_TON_SERVEUR:11434
    OLLAMA_MODEL = qwen3:14b   (ou qwen3:7b selon ta RAM)
"""

import os
import json
import logging
import time
from datetime import datetime
from dotenv import load_dotenv
import requests

# ─────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────
load_dotenv()

OLLAMA_URL   = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen3:14b")
TODAY        = datetime.today().strftime("%Y-%m-%d")

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)


# ─────────────────────────────────────────────
# Classe principale Ollama
# ─────────────────────────────────────────────
class OllamaClient:
    """
    Client REST pour Ollama.
    Envoie un prompt à Qwen3 et retourne la réponse texte.
    """

    def __init__(self):
        self.url   = OLLAMA_URL
        self.model = OLLAMA_MODEL
        self._check_connection()

    def _check_connection(self):
        """Vérifie que Ollama est bien accessible avant de commencer."""
        try:
            resp = requests.get(f"{self.url}/api/tags", timeout=5)
            resp.raise_for_status()
            models = [m["name"] for m in resp.json().get("models", [])]
            log.info(f" Ollama connecté — Modèles disponibles : {models}")

            # Vérifie que le modèle demandé est bien installé
            model_base = self.model.split(":")[0]
            if not any(model_base in m for m in models):
                log.warning(f"  Modèle '{self.model}' non trouvé.")
                log.warning(f"   Lance : ollama pull {self.model}")
        except requests.RequestException as e:
            log.error(f"Impossible de contacter Ollama sur {self.url}")
            log.error(f"   Erreur : {e}")
            log.error(f"   Vérifie que Ollama tourne : ollama serve")
            raise

    def ask(self, prompt: str, label: str = "analyse") -> str:
        """
        Envoie un prompt à Ollama et retourne la réponse complète.

        Args:
            prompt : Le texte du prompt à envoyer
            label  : Nom de l'analyse (pour les logs)

        Returns:
            La réponse texte de Qwen3
        """
        log.info(f"Envoi à Ollama — {label} ({len(prompt)} caractères)...")
        start = time.time()

        payload = {
            "model":  self.model,
            "prompt": prompt,
            "stream": False,          # On attend la réponse complète
            "options": {
                "temperature": 0.3,   # Bas = réponses plus précises et cohérentes
                "top_p": 0.9,
                "num_predict": 2000,  # Nombre max de tokens en réponse
            }
        }

        try:
            resp = requests.post(
                f"{self.url}/api/generate",
                json=payload,
                timeout=300           # 5 minutes max (Qwen3 peut être lent)
            )
            resp.raise_for_status()
            data     = resp.json()
            response = data.get("response", "").strip()
            duration = time.time() - start

            log.info(f"   Réponse reçue en {duration:.1f}s — {len(response)} caractères")
            return response

        except requests.Timeout:
            log.error(f"   Timeout — Ollama a mis trop de temps (>5min)")
            return "ERREUR: Timeout — le modèle a mis trop de temps à répondre."
        except requests.RequestException as e:
            log.error(f"    Erreur Ollama : {e}")
            return f"ERREUR: {str(e)}"


# ─────────────────────────────────────────────
# Analyseur par segments
# ─────────────────────────────────────────────
class SegmentAnalyzer:
    """
    Analyse chaque segment de données ERPNext séparément,
    puis fait une synthèse finale globale.

    Pourquoi analyser par segment ?
    → Qwen3 a une limite de contexte.
    → Chaque segment = une analyse ciblée et précise.
    → La synthèse finale regroupe tout intelligemment.
    """

    def __init__(self, ollama: OllamaClient):
        self.ollama = ollama

    def analyze_segment(self, segment_name: str, prompt: str) -> dict:
        """Analyse un seul segment et retourne le résultat structuré."""

        if not prompt or len(prompt.strip()) < 50:
            log.info(f"   ⏭️  Segment '{segment_name}' vide — ignoré")
            return {
                "segment":  segment_name,
                "status":   "vide",
                "response": "Aucune donnée disponible pour ce segment.",
                "duration": 0
            }

        start    = time.time()
        response = self.ollama.ask(prompt, label=segment_name)
        duration = time.time() - start

        return {
            "segment":  segment_name,
            "status":   "ok" if not response.startswith("ERREUR") else "erreur",
            "response": response,
            "duration": round(duration, 1)
        }

    def analyze_all(self, erpnext_data: dict) -> dict:
        """
        Analyse tous les segments un par un,
        puis envoie le prompt de synthèse finale.

        Args:
            erpnext_data : Résultat de collect_and_build_prompts() dans erpnext.py

        Returns:
            Dictionnaire complet avec toutes les analyses + synthèse finale
        """
        log.info("=" * 55)
        log.info("DÉBUT DE L'ANALYSE OLLAMA / QWEN3")
        log.info("=" * 55)

        segments_results = {}

        # ── Étape 1 : Analyse de chaque segment ──────────
        segment_labels = {
            "stock":     " Stock & Réapprovisionnement",
            "purchases": " Commandes d'achat",
            "sales":     "Ventes",
            "top_items": "Top articles",
            "suppliers": "Fournisseurs & Paiements",
        }

        for key, label in segment_labels.items():
            log.info(f"\n── Analyse segment : {label} ──")
            segment_data = erpnext_data["segments"].get(key, {})
            prompt       = segment_data.get("prompt", "")

            result = self.analyze_segment(label, prompt)
            segments_results[key] = result

            # Pause courte entre les appels pour ne pas surcharger Ollama
            time.sleep(1)

        # ── Étape 2 : Synthèse finale globale ────────────
        log.info("\n── Synthèse finale globale ──")
        final_prompt   = erpnext_data.get("final_prompt", "")
        final_response = self.ollama.ask(final_prompt, label="SYNTHÈSE FINALE")

        # ── Construction du rapport complet ──────────────
        rapport = {
            "date":              TODAY,
            "model":             OLLAMA_MODEL,
            "generated_at":      datetime.now().isoformat(),
            "segments_analyses": segments_results,
            "final_report":      final_response,
            "summary": {
                "segments_ok":    sum(1 for r in segments_results.values() if r["status"] == "ok"),
                "segments_vides": sum(1 for r in segments_results.values() if r["status"] == "vide"),
                "segments_error": sum(1 for r in segments_results.values() if r["status"] == "erreur"),
                "total_duration": round(sum(r["duration"] for r in segments_results.values()), 1),
            }
        }

        log.info("\n" + "=" * 55)
        log.info("ANALYSE TERMINÉE")
        log.info(f"  Segments analysés : {rapport['summary']['segments_ok']}")
        log.info(f"  Segments vides    : {rapport['summary']['segments_vides']}")
        log.info(f"  Erreurs           : {rapport['summary']['segments_error']}")
        log.info("=" * 55)

        return rapport


# ─────────────────────────────────────────────
# Sauvegarde du rapport
# ─────────────────────────────────────────────
def save_report(rapport: dict, output_dir: str = "reports") -> str:
    """
    Sauvegarde le rapport JSON et un fichier texte lisible.

    Returns:
        Chemin du fichier JSON sauvegardé
    """
    os.makedirs(output_dir, exist_ok=True)

    # ── Fichier JSON (pour l'interface et Frappe) ──
    json_path = os.path.join(output_dir, f"rapport_{TODAY}.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(rapport, f, ensure_ascii=False, indent=2)
    log.info(f"📁 Rapport JSON sauvegardé : {json_path}")

    # ── Fichier texte lisible (pour vérification rapide) ──
    txt_path = os.path.join(output_dir, f"rapport_{TODAY}.txt")
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(f"RAPPORT D'ANALYSE ERP — {TODAY}\n")
        f.write(f"Modèle : {rapport['model']}\n")
        f.write(f"Généré le : {rapport['generated_at']}\n")
        f.write("=" * 60 + "\n\n")

        # Analyses par segment
        f.write("ANALYSES PAR SEGMENT\n")
        f.write("-" * 60 + "\n\n")
        for key, result in rapport["segments_analyses"].items():
            f.write(f"▶ {result['segment']}\n")
            f.write(f"  Statut : {result['status']} | Durée : {result['duration']}s\n\n")
            f.write(result["response"])
            f.write("\n\n" + "-" * 60 + "\n\n")

        # Synthèse finale
        f.write("\nSYNTHÈSE FINALE — RECOMMANDATIONS\n")
        f.write("=" * 60 + "\n\n")
        f.write(rapport["final_report"])

    log.info(f" Rapport texte sauvegardé  : {txt_path}")
    return json_path


# ─────────────────────────────────────────────
# Fonction principale — utilisée par scheduler.py
# ─────────────────────────────────────────────
def run_analysis(erpnext_data: dict) -> dict:
    """
    Point d'entrée principal.
    Reçoit les données d'erpnext.py, lance l'analyse Ollama,
    sauvegarde et retourne le rapport.

    Args:
        erpnext_data : Résultat de collect_and_build_prompts()

    Returns:
        Le rapport complet
    """
    client   = OllamaClient()
    analyzer = SegmentAnalyzer(client)
    rapport  = analyzer.analyze_all(erpnext_data)
    save_report(rapport)
    return rapport


# ─────────────────────────────────────────────
# Test direct (sans ERPNext — avec données fictives)
# ─────────────────────────────────────────────
if __name__ == "__main__":
    log.info(" Mode test — données fictives")

    # Données de test pour vérifier que Ollama répond bien
    fake_data = {
        "date": TODAY,
        "segments": {
            "stock": {
                "prompt": f"""=== ANALYSE STOCK ===
Date : {TODAY}
Articles en stock faible :
  - Article: CIMENT-50KG | Stock actuel: 5 | Niveau réappro: 50 | Entrepôt: Principal
  - Article: FER-10MM    | Stock actuel: 2 | Niveau réappro: 20 | Entrepôt: Principal
Question : Quels articles faut-il réapprovisionner en priorité ?""",
                "data_count": 2
            },
            "purchases":  {"prompt": "", "data_count": 0},
            "sales":      {"prompt": "", "data_count": 0},
            "top_items":  {"prompt": "", "data_count": 0},
            "suppliers":  {"prompt": "", "data_count": 0},
        },
        "final_prompt": f"""Tu es expert en gestion des achats.
Date : {TODAY}

=== STOCK FAIBLE ===
- CIMENT-50KG : stock=5, seuil=50
- FER-10MM    : stock=2, seuil=20

Donne :
1. ACTIONS URGENTES
2. RECOMMANDATIONS D'ACHAT
3. STRATÉGIE DE LA SEMAINE
4. OBSERVATIONS GÉNÉRALES
"""
    }

    rapport = run_analysis(fake_data)

    print("\n" + "=" * 60)
    print("SYNTHÈSE FINALE DE QWEN3 :")
    print("=" * 60)
    print(rapport["final_report"])
    print("\n Test terminé — vérifie le dossier reports/")