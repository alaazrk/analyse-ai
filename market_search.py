"""
market_search.py
----------------
Recherche des prix de marché externes pour les articles
identifiés par erpnext.py.

Stratégie :
    Au lieu du web scraping (bloqué par DuckDuckGo),
    on demande directement à Qwen3/Groq d'estimer les prix
    du marché algérien pour chaque article.

    Qwen3 a été entraîné sur des données incluant des prix
    de matériaux industriels en Algérie — il peut donner
    des estimations raisonnables avec des fourchettes de prix.

    On lui demande EXPLICITEMENT de :
    - Donner une fourchette de prix (min/max)
    - Nommer des fournisseurs/marchés connus en Algérie
    - Indiquer le niveau de confiance de ses estimations

IMPORTANT :
    Ces prix sont des ESTIMATIONS basées sur les données
    d'entraînement de Qwen3. Ils doivent être vérifiés
    avant toute décision d'achat réelle.

Prérequis :
    pip install requests python-dotenv

Variables d'environnement (.env) :
    GROQ_API_KEY = gsk_xxxxxxxxxxxxxxxx
    GROQ_MODEL   = qwen/qwen3-32b
    MARKET_COUNTRY  = algerie
    MARKET_CURRENCY = DZD
"""

import os
import re
import time
import json
import logging
from dotenv import load_dotenv
import requests

load_dotenv()

GROQ_API_KEY    = os.getenv("GROQ_API_KEY")
GROQ_MODEL      = os.getenv("GROQ_MODEL", "qwen/qwen3-32b")
GROQ_URL        = "https://api.groq.com/openai/v1/chat/completions"
MARKET_COUNTRY  = os.getenv("MARKET_COUNTRY", "Algérie")
MARKET_CURRENCY = os.getenv("MARKET_CURRENCY", "DZD")
MAX_ITEMS       = int(os.getenv("MARKET_MAX_ITEMS", "5"))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)


# ─────────────────────────────────────────────
# Classe principale
# ─────────────────────────────────────────────
class MarketSearcher:
    """
    Utilise Qwen3 via Groq pour estimer les prix de marché
    des articles en Algérie.

    Pourquoi Qwen3 et pas du scraping ?
    ------------------------------------
    Le web scraping est bloqué par la plupart des sites
    (DuckDuckGo, Google, sites e-commerce algériens).

    Qwen3 a été entraîné sur des données incluant :
    - des sites de vente de matériaux industriels
    - des forums algériens de construction
    - des catalogues de prix de grossistes

    Il peut donc estimer des fourchettes de prix réalistes
    avec une précision suffisante pour une recommandation d'achat.
    """

    def __init__(self):
        if not GROQ_API_KEY:
            raise ValueError("GROQ_API_KEY manquante dans .env")

    @staticmethod
    def _clean_thinking(text: str) -> str:
        """Enlève les balises <think>...</think> de Qwen3."""
        cleaned = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
        return cleaned.strip()

    def _ask_groq(self, prompt: str) -> str:
        """Envoie un prompt à Groq et retourne la réponse."""
        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": GROQ_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2,   # bas = réponses plus factuelles
            "max_tokens": 1500,
        }
        try:
            resp = requests.post(GROQ_URL, json=payload, headers=headers, timeout=60)
            resp.raise_for_status()
            text = resp.json()["choices"][0]["message"]["content"].strip()
            return self._clean_thinking(text)
        except requests.exceptions.HTTPError as e:
            if resp.status_code == 429:
                log.warning("   Rate limit Groq — attente 30s...")
                time.sleep(30)
                return self._ask_groq(prompt)
            log.error(f"   Erreur Groq : {e}")
            return ""
        except Exception as e:
            log.error(f"   Erreur : {e}")
            return ""

    def search_prices_for_items(self, items: list) -> str:
        """
        Demande à Qwen3 d'estimer les prix de marché
        pour une liste d'articles en Algérie.

        On envoie TOUS les articles en un seul appel Groq
        pour économiser le quota gratuit.

        Args:
            items : liste de dicts avec item_code et item_name

        Returns:
            Texte de réponse de Qwen3 avec les prix estimés
        """
        if not items:
            return ""

        # ── Construction du prompt ──
        articles_list = "\n".join([
            f"- {i.get('item_name') or i.get('item_code', '')}"
            for i in items[:MAX_ITEMS]
        ])

        prompt = f"""Tu es un expert en approvisionnement industriel en {MARKET_COUNTRY}.

Pour chaque article de la liste ci-dessous, donne :
1. La fourchette de prix de marché actuelle en {MARKET_CURRENCY}
2. Les principaux fournisseurs ou marchés où trouver cet article en {MARKET_COUNTRY}
   (ex: Zone industrielle Rouiba, grossistes Alger, marchés spécialisés...)
3. Le prix minimum et maximum constaté
4. Un conseil d'achat (quelle quantité commander pour avoir un bon prix)

ARTICLES À RECHERCHER :
{articles_list}

FORMAT DE RÉPONSE OBLIGATOIRE pour chaque article :
Article: [nom de l'article]
Prix min : [X] {MARKET_CURRENCY}
Prix max : [X] {MARKET_CURRENCY}
Où acheter : [noms des fournisseurs/marchés/zones en {MARKET_COUNTRY}]
Conseil : [quantité optimale, période d'achat, remarque]
Confiance : [Élevée / Moyenne / Faible]
---

Sois précis avec les prix. Si tu n'es pas sûr d'un prix, indique "Confiance: Faible".
Réponds en français."""

        log.info(f"🌐 Recherche prix marché pour {len(items[:MAX_ITEMS])} articles via Qwen3...")
        response = self._ask_groq(prompt)
        log.info(f"   ✅ Estimations reçues ({len(response)} caractères)")
        return response


# ─────────────────────────────────────────────
# Construction du prompt final pour Qwen3
# ─────────────────────────────────────────────
def build_market_prompt(market_response: str, items: list) -> str:
    """
    Formate la réponse de recherche marché en prompt
    pour l'inclure dans la synthèse finale.
    """
    if not market_response:
        return ""

    item_names = ", ".join([
        i.get("item_name") or i.get("item_code", "")
        for i in items[:MAX_ITEMS]
    ])

    return (
        f"=== PRIX DE MARCHÉ ESTIMÉS EN {MARKET_COUNTRY.upper()} ===\n"
        f"Articles recherchés : {item_names}\n"
        f"Source : Estimation Qwen3 basée sur données marché {MARKET_COUNTRY}\n"
        f"⚠️  Ces prix sont des estimations — à vérifier avant achat réel.\n\n"
        f"{market_response}\n\n"
        f"Question : En comparant ces prix de marché avec les prix ERPNext internes, "
        f"quels articles peut-on acheter moins cher ailleurs ? "
        f"Recommande des fournisseurs alternatifs avec prix estimés.\n"
    )


# ─────────────────────────────────────────────
# Fonction principale — utilisée par scheduler.py
# ─────────────────────────────────────────────
def run_market_search(erpnext_raw: dict) -> dict:
    """
    Lance la recherche de prix de marché.

    Priorité des articles à rechercher :
    1. Articles en stock faible (urgent)
    2. Top articles vendus
    3. Articles des commandes d'achat récentes
    """
    searcher = MarketSearcher()

    # ── Sélection des articles à rechercher ──
    items = []

    # Priorité 1 : stock faible
    for item in erpnext_raw.get("low_stock", [])[:MAX_ITEMS]:
        items.append({
            "item_code": item.get("item_code", ""),
            "item_name": item.get("item_name", ""),
        })

    # Priorité 2 : top articles vendus
    if len(items) < MAX_ITEMS:
        for item in erpnext_raw.get("top_items", [])[:MAX_ITEMS - len(items)]:
            items.append({
                "item_code": item.get("item_code", ""),
                "item_name": item.get("item_name", ""),
            })

    # Priorité 3 : articles depuis les commandes d'achat récentes
    if len(items) < MAX_ITEMS:
        purchases = erpnext_raw.get("purchases", [])
        for p in purchases[:MAX_ITEMS - len(items)]:
            items.append({
                "item_code": p.get("name", ""),
                "item_name": p.get("supplier", ""),
            })

    if not items:
        log.info("Aucun article disponible pour la recherche marché")
        return {"prompt": "", "results": "", "items": []}

    # ── Recherche via Qwen3 ──
    market_response = searcher.search_prices_for_items(items)
    prompt          = build_market_prompt(market_response, items)

    return {
        "prompt":  prompt,
        "results": market_response,
        "items":   items,
    }


# ─────────────────────────────────────────────
# Test direct
# ─────────────────────────────────────────────
if __name__ == "__main__":
    log.info("🔧 Mode test — recherche prix marché Algérie")

    test_items = [
        {"item_code": "TOLE-INOX",   "item_name": "Tole inox 2000x1000x0.6mm 430 satiné"},
        {"item_code": "CHAISE-T2",   "item_name": "chaise élevée type 2"},
        {"item_code": "CONTRE-PLAQ", "item_name": "contre-plaqué multiplis 18mm beech"},
    ]

    searcher  = MarketSearcher()
    response  = searcher.search_prices_for_items(test_items)
    prompt    = build_market_prompt(response, test_items)

    print("\n" + "=" * 60)
    print("ESTIMATIONS DE PRIX MARCHÉ ALGÉRIE :")
    print("=" * 60)
    print(response)
    print("\n" + "=" * 60)
    print("PROMPT GÉNÉRÉ POUR QWEN3 :")
    print("=" * 60)
    print(prompt[:500] + "..." if len(prompt) > 500 else prompt)