"""
app.py
------
Serveur Flask pour le dashboard Achats IA.
Sert uniquement les routes API et la page principale.

Lancement :
    pip install flask
    python app.py
    → http://localhost:5000
"""

import os
import json
import glob
import base64
from flask import Flask, jsonify, render_template, request

app = Flask(__name__)

# ─────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────
REPORTS_DIR = os.path.join(os.path.dirname(__file__), "..", "reports")
CHARTS_DIR  = os.path.join(os.path.dirname(__file__), "..", "reports", "charts")


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────
def list_files(pattern: str) -> list:
    """Liste les fichiers JSON d'un pattern, du plus récent au plus ancien."""
    files = sorted(glob.glob(os.path.join(REPORTS_DIR, pattern)), reverse=True)
    return files


def load_json(path: str) -> dict:
    """Charge un fichier JSON."""
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def image_to_base64(name: str) -> str:
    """Convertit un graphique PNG en base64 pour l'envoyer via l'API."""
    path = os.path.join(CHARTS_DIR, f"{name}.png")
    if not os.path.exists(path):
        return ""
    with open(path, "rb") as f:
        return "data:image/png;base64," + base64.b64encode(f.read()).decode()


# ─────────────────────────────────────────────
# Page principale
# ─────────────────────────────────────────────
@app.route("/")
def index():
    """Sert la page principale HTML."""
    return render_template("index.html")


# ─────────────────────────────────────────────
# API — Rapports d'achat (rapport_*.json)
# ─────────────────────────────────────────────
@app.route("/api/reports")
def api_list_reports():
    """Retourne la liste des dates de rapports d'achat disponibles."""
    files = list_files("rapport_*.json")
    dates = [
        os.path.basename(f).replace("rapport_", "").replace(".json", "")
        for f in files
    ]
    return jsonify({"dates": dates})


@app.route("/api/report/<date_str>")
def api_get_report(date_str):
    """Retourne le contenu complet d'un rapport d'achat."""
    path = os.path.join(REPORTS_DIR, f"rapport_{date_str}.json")
    data = load_json(path)
    if not data:
        return jsonify({"error": "Rapport introuvable"}), 404
    return jsonify(data)


# ─────────────────────────────────────────────
# API — Rapports BI (bi_*.json)
# ─────────────────────────────────────────────
@app.route("/api/bi_reports")
def api_list_bi():
    """Retourne la liste des dates de rapports BI disponibles."""
    files = list_files("bi_*.json")
    dates = [
        os.path.basename(f).replace("bi_", "").replace(".json", "")
        for f in files
    ]
    return jsonify({"dates": dates})


@app.route("/api/bi/<date_str>")
def api_get_bi(date_str):
    """
    Retourne le contenu d'un rapport BI + les graphiques en base64.
    Les graphiques sont inclus directement pour éviter des appels séparés.
    """
    path = os.path.join(REPORTS_DIR, f"bi_{date_str}.json")
    data = load_json(path)
    if not data:
        return jsonify({"error": "Rapport BI introuvable"}), 404

    # Ajoute les graphiques en base64
    chart_names = [
        "ca_par_mois",
        "ca_par_territoire",
        "ca_par_client",
        "achats_par_fournisseur",
        "revenus_couts_marge",
        "ca_par_annee",
    ]
    data["charts_b64"] = {
        name: image_to_base64(name)
        for name in chart_names
        if image_to_base64(name)
    }

    return jsonify(data)


# ─────────────────────────────────────────────
# API — Statut système
# ─────────────────────────────────────────────
@app.route("/api/status")
def api_status():
    """Retourne le statut du système."""
    nb_reports = len(list_files("rapport_*.json"))
    nb_bi      = len(list_files("bi_*.json"))
    nb_charts  = len(glob.glob(os.path.join(CHARTS_DIR, "*.png")))

    return jsonify({
        "status":     "operational",
        "reports":    nb_reports,
        "bi_reports": nb_bi,
        "charts":     nb_charts,
        "reports_dir": os.path.abspath(REPORTS_DIR),
    })


# ─────────────────────────────────────────────
# Lancement
# ─────────────────────────────────────────────
if __name__ == "__main__":
    os.makedirs(REPORTS_DIR, exist_ok=True)
    os.makedirs(CHARTS_DIR, exist_ok=True)
    print("=" * 50)
    print("Achats IA Analytics → http://localhost:5000")
    print("=" * 50)
    app.run(debug=True, port=5000)