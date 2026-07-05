"""
groq_client.py
--------------
Alternative GRATUITE à ollama.py pour tester ton pipeline
en attendant que ton serveur Ollama soit accessible.

Groq héberge Qwen3-32B gratuitement via une API compatible OpenAI.
Aucune carte bancaire requise.

Comment obtenir une clé API :
    1. Va sur https://console.groq.com
    2. Connecte-toi avec email ou Google
    3. API Keys → Create API Key
    4. Copie la clé dans ton .env

Prérequis :
    pip install requests python-dotenv

Variables d'environnement (.env) :
    GROQ_API_KEY = gsk_xxxxxxxxxxxxxxxx
    GROQ_MODEL   = qwen/qwen3-32b

IMPORTANT :
Ce fichier a EXACTEMENT la même structure que ollama.py
(mêmes noms de fonctions, mêmes paramètres) pour que
scheduler.py puisse utiliser l'un ou l'autre sans changement.
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

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL   = os.getenv("GROQ_MODEL", "qwen/qwen3-32b")
GROQ_URL     = "https://api.groq.com/openai/v1/chat/completions"
TODAY        = datetime.today().strftime("%Y-%m-%d")

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)


# ─────────────────────────────────────────────
# Classe principale Groq (remplace OllamaClient)
# ─────────────────────────────────────────────
class OllamaClient:
    """
    Même nom que dans ollama.py exprès — pour que scheduler.py
    puisse importer 'OllamaClient' depuis ce fichier à la place
    sans rien changer dans le reste du code.

    Différence avec Ollama :
        - Ollama : POST /api/generate avec {"prompt": "..."}
        - Groq   : POST /v1/chat/completions avec {"messages": [...]}
          (format "chat" standard utilisé par la plupart des APIs cloud)
    """

    def __init__(self):
        self.url   = GROQ_URL
        self.model = GROQ_MODEL
        self._check_connection()

    def _check_connection(self):
        """Vérifie que la clé API Groq est valide."""
        if not GROQ_API_KEY:
            log.error("❌ GROQ_API_KEY manquante dans .env")
            log.error("   Crée une clé sur https://console.groq.com")
            raise ValueError("GROQ_API_KEY manquante")

        try:
            resp = requests.get(
                "https://api.groq.com/openai/v1/models",
                headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
                timeout=10
            )
            resp.raise_for_status()
            models = [m["id"] for m in resp.json().get("data", [])]
            log.info(f"✅ Groq connecté — {len(models)} modèles disponibles")

            if self.model not in models:
                log.warning(f"⚠️  Modèle '{self.model}' non trouvé dans la liste Groq.")
                log.warning(f"   Modèles disponibles : {models[:10]}")
        except requests.RequestException as e:
            log.error(f"❌ Impossible de contacter Groq : {e}")
            raise

    @staticmethod
    def _clean_thinking(text: str) -> str:
        """
        Enlève les balises <think>...</think> que Qwen3 ajoute
        pour montrer son raisonnement interne avant la réponse finale.

        Exemple de ce que Qwen3 renvoie parfois :
            <think>
            Okay, let's analyze this... le fournisseur TTTT...
            </think>
            # Rapport Supply Chain
            1. ACTIONS URGENTES
            ...

        On garde seulement la partie après </think>.
        """
        import re
        # Enlève tout le bloc <think>...</think> (même sur plusieurs lignes)
        cleaned = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
        return cleaned.strip()

    def ask(self, prompt: str, label: str = "analyse") -> str:
        """
        Envoie un prompt à Groq/Qwen3 et retourne la réponse complète.
        Même signature que OllamaClient.ask() dans ollama.py.
        """
        log.info(f"🤖 Envoi à Groq — {label} ({len(prompt)} caractères)...")
        start = time.time()

        # Format "chat" — différent d'Ollama mais standard pour les APIs cloud
        payload = {
            "model": self.model,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.3,
            "max_tokens": 2000,
        }

        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json",
        }

        try:
            resp = requests.post(self.url, json=payload, headers=headers, timeout=60)
            resp.raise_for_status()
            data = resp.json()

            # Format de réponse Groq (style OpenAI) :
            # { "choices": [ { "message": { "content": "..." } } ] }
            response = data["choices"][0]["message"]["content"].strip()

            # Qwen3 a un mode "raisonnement" qui pense à voix haute
            # entre des balises <think>...</think> avant la vraie réponse.
            # On les enlève — l'utilisateur final ne doit voir que le résultat.
            response = self._clean_thinking(response)

            duration = time.time() - start

            log.info(f"   ✅ Réponse reçue en {duration:.1f}s — {len(response)} caractères")
            return response

        except requests.exceptions.HTTPError as e:
            # Erreur fréquente : 429 = trop de requêtes (limite gratuite atteinte)
            if resp.status_code == 429:
                log.warning("   ⚠️  Rate limit Groq — attente 60 secondes puis retry...")
                time.sleep(62)
                # Retry automatique
                try:
                    resp2 = requests.post(self.url, json=payload, headers=headers, timeout=60)
                    resp2.raise_for_status()
                    data2    = resp2.json()
                    response2 = data2["choices"][0]["message"]["content"].strip()
                    return self._clean_thinking(response2)
                except Exception as e2:
                    log.error(f"   ❌ Retry échoué : {e2}")
                    return "ERREUR: Limite de requêtes atteinte après retry."
            log.error(f"   ❌ Erreur HTTP Groq : {e}")
            log.error(f"   Réponse : {resp.text[:300]}")
            return f"ERREUR: {str(e)}"
        except requests.Timeout:
            log.error("   ❌ Timeout Groq")
            return "ERREUR: Timeout"
        except (KeyError, IndexError) as e:
            log.error(f"   ❌ Réponse Groq inattendue : {e}")
            return f"ERREUR: Format de réponse inattendu"
        except requests.RequestException as e:
            log.error(f"   ❌ Erreur Groq : {e}")
            return f"ERREUR: {str(e)}"


# ─────────────────────────────────────────────
# Le reste est IDENTIQUE à ollama.py
# (copié tel quel pour garder la compatibilité)
# ─────────────────────────────────────────────
class SegmentAnalyzer:
    """Analyse chaque segment de données ERPNext séparément, puis fait une synthèse finale."""

    def __init__(self, client: OllamaClient):
        self.client = client

    def analyze_segment(self, segment_name: str, prompt: str) -> dict:
        if not prompt or len(prompt.strip()) < 50:
            log.info(f"   ⏭️  Segment '{segment_name}' vide — ignoré")
            return {
                "segment":  segment_name,
                "status":   "vide",
                "response": "Aucune donnée disponible pour ce segment.",
                "duration": 0
            }

        start    = time.time()
        response = self.client.ask(prompt, label=segment_name)
        duration = time.time() - start

        return {
            "segment":  segment_name,
            "status":   "ok" if not response.startswith("ERREUR") else "erreur",
            "response": response,
            "duration": round(duration, 1)
        }

    def analyze_all(self, erpnext_data: dict) -> dict:
        """
        Mode économique — 1 seul appel Groq au lieu de 6.

        Pourquoi ?
        ----------
        Groq gratuit a une limite de tokens/minute.
        Envoyer 5 segments + 1 synthèse = 6 appels → rate limit.

        Solution : on envoie SEULEMENT le prompt final (qui contient
        déjà tous les segments assemblés) → 1 seul appel, même résultat.

        Les segments sont quand même marqués "analysés" dans le rapport
        pour que l'interface puisse les afficher correctement.
        """
        log.info("=" * 55)
        log.info("DÉBUT DE L'ANALYSE GROQ / QWEN3 (mode économique)")
        log.info("=" * 55)

        # ── Marque les segments sans les envoyer individuellement ──
        # On ne fait PAS d'appels séparés par segment pour éviter le rate limit.
        # Le prompt final contient déjà toutes les données assemblées.
        segments_results = {}
        segment_labels = {
            "stock":       "📦 Stock & Réapprovisionnement",
            "purchases":   "🛒 Commandes d'achat",
            "sales":       "💰 Ventes",
            "top_items":   "🏆 Top articles",
            "item_prices": "💰 Historique prix",
            "suppliers":   "🏭 Fournisseurs & Paiements",
        }

        for key, label in segment_labels.items():
            segment_data = erpnext_data["segments"].get(key, {})
            prompt       = segment_data.get("prompt", "")
            data_count   = segment_data.get("data_count", 0)

            # Marque vide ou prêt sans envoyer à Groq
            segments_results[key] = {
                "segment":  label,
                "status":   "ok" if (prompt and len(prompt) > 50) else "vide",
                "response": f"{data_count} éléments collectés — inclus dans la synthèse finale.",
                "duration": 0
            }

        # ── UN SEUL appel Groq : le prompt de synthèse finale ──
        log.info("\n── Synthèse finale (appel unique Groq) ──")
        final_prompt   = erpnext_data.get("final_prompt", "")
        final_response = self.client.ask(final_prompt, label="SYNTHÈSE FINALE")

        rapport = {
            "date":              TODAY,
            "model":             f"groq/{GROQ_MODEL}",
            "generated_at":      datetime.now().isoformat(),
            "segments_analyses": segments_results,
            "final_report":      final_response,
            "summary": {
                "segments_ok":    sum(1 for r in segments_results.values() if r["status"] == "ok"),
                "segments_vides": sum(1 for r in segments_results.values() if r["status"] == "vide"),
                "segments_error": sum(1 for r in segments_results.values() if r["status"] == "erreur"),
                "total_duration": 0,
            },
            # Données brutes ERPNext pour l'interface viewer.py
            # Permet d'afficher les tableaux financiers sans dépendre de Qwen3
            "raw_data": {
                "invoices":   erpnext_data.get("raw", {}).get("invoices", []),
                "purchases":  erpnext_data.get("raw", {}).get("purchases", []),
                "suppliers":  erpnext_data.get("raw", {}).get("suppliers", []),
                "low_stock":  erpnext_data.get("raw", {}).get("low_stock", []),
                "item_prices":erpnext_data.get("raw", {}).get("item_prices", []),
            }
        }

        log.info("\n" + "=" * 55)
        log.info("ANALYSE TERMINÉE — 1 seul appel Groq utilisé")
        log.info(f"  Segments avec données : {rapport['summary']['segments_ok']}")
        log.info(f"  Segments vides        : {rapport['summary']['segments_vides']}")
        log.info("=" * 55)

        return rapport


def save_report(rapport: dict, output_dir: str = "reports") -> str:
    """Identique à ollama.py — sauvegarde JSON + texte lisible."""
    os.makedirs(output_dir, exist_ok=True)

    json_path = os.path.join(output_dir, f"rapport_{TODAY}.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(rapport, f, ensure_ascii=False, indent=2)
    log.info(f"📁 Rapport JSON sauvegardé : {json_path}")

    txt_path = os.path.join(output_dir, f"rapport_{TODAY}.txt")
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(f"RAPPORT D'ANALYSE ERP — {TODAY}\n")
        f.write(f"Modèle : {rapport['model']}\n")
        f.write(f"Généré le : {rapport['generated_at']}\n")
        f.write("=" * 60 + "\n\n")

        f.write("ANALYSES PAR SEGMENT\n")
        f.write("-" * 60 + "\n\n")
        for key, result in rapport["segments_analyses"].items():
            f.write(f"▶ {result['segment']}\n")
            f.write(f"  Statut : {result['status']} | Durée : {result['duration']}s\n\n")
            f.write(result["response"])
            f.write("\n\n" + "-" * 60 + "\n\n")

        f.write("\nSYNTHÈSE FINALE — RECOMMANDATIONS\n")
        f.write("=" * 60 + "\n\n")
        f.write(rapport["final_report"])

    log.info(f"📄 Rapport texte sauvegardé  : {txt_path}")
    return json_path


def run_analysis(erpnext_data: dict) -> dict:
    """Point d'entrée principal — même signature que dans ollama.py."""
    client   = OllamaClient()
    analyzer = SegmentAnalyzer(client)
    rapport  = analyzer.analyze_all(erpnext_data)
    save_report(rapport)
    return rapport


# ─────────────────────────────────────────────
# Test direct (avec données fictives)
# ─────────────────────────────────────────────
if __name__ == "__main__":
    log.info("🔧 Mode test — Groq avec données fictives")

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
    print("SYNTHÈSE FINALE DE QWEN3 (via Groq) :")
    print("=" * 60)
    print(rapport["final_report"])
    print("\n Test terminé — vérifie le dossier reports/")