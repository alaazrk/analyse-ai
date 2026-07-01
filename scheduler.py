"""
scheduler.py
------------
Orchestre l'analyse quotidienne complète :
    1. Récupère les données ERPNext (erpnext.py)
    2. Envoie à Ollama/Qwen3 pour analyse (ollama.py)
    3. Sauvegarde le rapport final

Peut tourner de 2 façons :
    A) Lancé manuellement       : python scheduler.py --once
    B) Lancé en tâche planifiée : python scheduler.py
       (boucle infinie qui attend l'heure programmée chaque jour)

Prérequis :
    pip install requests python-dotenv schedule

Variables d'environnement (.env) :
    SCHEDULE_TIME = 07:00   (heure d'exécution quotidienne, format 24h)
"""

import os
import sys
import json
import logging
import argparse
import traceback
from datetime import datetime
from dotenv import load_dotenv

# On importe nos 2 modules précédents
from erpnext import collect_and_build_prompts
from ollama import run_analysis

# ─────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────
load_dotenv()

SCHEDULE_TIME = os.getenv("SCHEDULE_TIME", "07:00")
LOG_DIR       = "logs"
TODAY         = datetime.today().strftime("%Y-%m-%d")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),  # affiche dans le terminal
    ]
)
log = logging.getLogger(__name__)


# ─────────────────────────────────────────────
# Fonction principale — exécute le pipeline complet
# ─────────────────────────────────────────────
def run_daily_analysis() -> dict:
    """
    Exécute le pipeline complet une fois :
        ERPNext → Ollama → Rapport sauvegardé

    Returns:
        Le rapport final (dict) ou None si erreur
    """
    log.info("█" * 60)
    log.info(f"DÉBUT DE L'ANALYSE QUOTIDIENNE — {TODAY}")
    log.info("█" * 60)

    start_time = datetime.now()

    try:
        # ── Étape 1 : Récupère les données ERPNext ──
        log.info("\n┌─────────────────────────────────────┐")
        log.info("│  ÉTAPE 1/2 — Collecte ERPNext        │")
        log.info("└─────────────────────────────────────┘")

        erpnext_data = collect_and_build_prompts()

        # Vérifie qu'on a bien récupéré quelque chose
        total_items = sum(
            seg["data_count"] for seg in erpnext_data["segments"].values()
        )
        log.info(f"✅ Collecte terminée — {total_items} éléments au total")

        if total_items == 0:
            log.warning("⚠️  Aucune donnée trouvée dans ERPNext.")
            log.warning("    Le rapport sera quand même généré mais sera vide.")

        # ── Étape 2 : Analyse avec Ollama/Qwen3 ──
        log.info("\n┌─────────────────────────────────────┐")
        log.info("│  ÉTAPE 2/2 — Analyse Ollama/Qwen3    │")
        log.info("└─────────────────────────────────────┘")

        rapport = run_analysis(erpnext_data)

        # ── Résumé final ──
        duration = (datetime.now() - start_time).total_seconds()

        log.info("\n" + "█" * 60)
        log.info("ANALYSE QUOTIDIENNE TERMINÉE AVEC SUCCÈS")
        log.info(f"  Durée totale       : {duration:.1f}s")
        log.info(f"  Segments analysés  : {rapport['summary']['segments_ok']}")
        log.info(f"  Segments vides     : {rapport['summary']['segments_vides']}")
        log.info(f"  Erreurs            : {rapport['summary']['segments_error']}")
        log.info(f"  Rapport sauvegardé : reports/rapport_{TODAY}.json")
        log.info("█" * 60)

        # Sauvegarde un log de succès
        _log_run_status(success=True, duration=duration, rapport=rapport)

        return rapport

    except Exception as e:
        # ── En cas d'erreur, on log tout et on continue (ne pas crasher) ──
        duration = (datetime.now() - start_time).total_seconds()
        error_trace = traceback.format_exc()

        log.error("\n" + "█" * 60)
        log.error("ÉCHEC DE L'ANALYSE QUOTIDIENNE")
        log.error(f"  Erreur : {e}")
        log.error(f"  Durée avant échec : {duration:.1f}s")
        log.error("█" * 60)
        log.error(f"\nDétail technique :\n{error_trace}")

        _log_run_status(success=False, duration=duration, error=str(e))

        return None


# ─────────────────────────────────────────────
# Suivi des exécutions (historique)
# ─────────────────────────────────────────────
def _log_run_status(success: bool, duration: float, rapport: dict = None, error: str = None):
    """
    Garde un historique de toutes les exécutions du scheduler
    dans un fichier JSON — utile pour voir si le cron tourne bien.
    """
    os.makedirs(LOG_DIR, exist_ok=True)
    history_path = os.path.join(LOG_DIR, "run_history.json")

    # Charge l'historique existant
    history = []
    if os.path.exists(history_path):
        try:
            with open(history_path, "r", encoding="utf-8") as f:
                history = json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            history = []

    # Ajoute l'entrée du jour
    entry = {
        "date":      TODAY,
        "timestamp": datetime.now().isoformat(),
        "success":   success,
        "duration_seconds": round(duration, 1),
    }
    if rapport:
        entry["summary"] = rapport.get("summary", {})
    if error:
        entry["error"] = error

    history.append(entry)

    # Garde seulement les 90 derniers jours pour ne pas grossir indéfiniment
    history = history[-90:]

    with open(history_path, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)


# ─────────────────────────────────────────────
# Mode A : Exécution unique (pour tests ou cron système)
# ─────────────────────────────────────────────
def run_once():
    """Lance l'analyse une seule fois puis quitte. Utilisé pour les tests
    et pour les tâches planifiées système (cron Linux, Planificateur Windows)."""
    log.info("Mode : exécution unique")
    rapport = run_daily_analysis()

    if rapport:
        sys.exit(0)  # code de sortie 0 = succès (important pour cron)
    else:
        sys.exit(1)  # code de sortie 1 = échec


# ─────────────────────────────────────────────
# Mode B : Boucle planifiée intégrée (alternative à cron)
# ─────────────────────────────────────────────
def run_scheduled():
    """
    Lance une boucle infinie qui exécute l'analyse
    chaque jour à l'heure définie dans SCHEDULE_TIME.

    Utile si tu ne veux pas configurer cron/Planificateur de tâches
    et préfères laisser ce script tourner en arrière-plan (ex: avec
    pm2, supervisor, ou un service systemd dédié).
    """
    try:
        import scheduler
        import time
    except ImportError:
        log.error("Le package 'schedule' n'est pas installé.")
        log.error("Installe-le avec : pip install schedule")
        sys.exit(1)

    log.info(f"Mode : planifié — exécution chaque jour à {SCHEDULE_TIME}")
    log.info("Le script tourne en continu. Ctrl+C pour arrêter.")

    scheduler.every().day.at(SCHEDULE_TIME).do(run_daily_analysis)

    # Affiche le prochain run prévu
    log.info(f"Prochaine exécution prévue : {SCHEDULE_TIME}")

    while True:
        scheduler.run_pending()
        time.sleep(60)  # vérifie chaque minute si c'est l'heure


# ─────────────────────────────────────────────
# Point d'entrée
# ─────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Scheduler d'analyse ERPNext + Ollama"
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Lance l'analyse une seule fois puis quitte (pour tests ou cron système)"
    )
    args = parser.parse_args()

    if args.once:
        run_once()
    else:
        run_scheduled()