"""
test_groq.py
------------
Pipeline complet :
    1. ERPNext  → collecte les données
    2. Market   → estime les prix de marché en Algérie
    3. Groq     → analyse tout et génère les recommandations
"""

from erpnext import collect_and_build_prompts
from market_search import run_market_search, build_market_prompt
from groq_client import run_analysis

# ── Étape 1 : Collecte ERPNext ──
erpnext_data = collect_and_build_prompts()

# ── Étape 2 : Recherche prix marché ──
market_data = run_market_search(erpnext_data["raw"])

# ── Étape 3 : Ajouter le prompt marché au prompt final ──
if market_data["prompt"]:
    erpnext_data["final_prompt"] = (
        erpnext_data["final_prompt"]
        + "\n\n"
        + market_data["prompt"]
    )
    erpnext_data["segments"]["market"] = {
        "prompt":     market_data["prompt"],
        "data_count": len(market_data["items"]),
    }

# ── Étape 4 : Analyse Groq ──
rapport = run_analysis(erpnext_data)

print("\n" + "=" * 60)
print("RAPPORT FINAL :")
print("=" * 60)
print(rapport["final_report"])
print("\n✅ Rapport sauvegardé dans reports/")