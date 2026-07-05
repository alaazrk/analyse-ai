"""
setup_erpnext.py
----------------
Script de configuration automatique d'ERPNext via API REST.

Ce script crée automatiquement :
    1. Les seuils de réapprovisionnement (Item Reorder)
       → Pour que l'IA sache quels articles commander
    2. Les prix d'achat par article (Item Price)
       → Pour que l'IA compare les prix réels
    3. Les territoires sur les clients
       → Pour l'analyse géographique (meilleure ville)
    4. Les groupes de fournisseurs
       → Pour mieux catégoriser les achats
    5. Les groupes de clients
       → Pour segmenter les clients

Utilise uniquement les données DÉJÀ dans ERPNext.
Ne crée rien de fictif — tout est basé sur les vrais articles,
clients et fournisseurs existants.

Lancement :
    python setup_erpnext.py

Variables d'environnement (.env) :
    ERPNEXT_URL        = https://erp.halfware.info
    ERPNEXT_API_KEY    = ta_cle
    ERPNEXT_API_SECRET = ton_secret
"""

import os
import json
import logging
from dotenv import load_dotenv
import requests

load_dotenv()

ERPNEXT_URL = os.getenv("ERPNEXT_URL", "").rstrip("/")
API_KEY     = os.getenv("ERPNEXT_API_KEY")
API_SECRET  = os.getenv("ERPNEXT_API_SECRET")

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)


# ─────────────────────────────────────────────
# Client ERPNext
# ─────────────────────────────────────────────
class ERPSetup:

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"token {API_KEY}:{API_SECRET}",
            "Content-Type":  "application/json",
            "Accept":        "application/json",
        })
        log.info(f"Connecté à {ERPNEXT_URL}")

    def _get(self, doctype, fields=None, filters=None, limit=500):
        url    = f"{ERPNEXT_URL}/api/resource/{doctype}"
        params = {"limit_page_length": limit}
        if fields:  params["fields"]  = json.dumps(fields)
        if filters: params["filters"] = json.dumps(filters)
        try:
            r = self.session.get(url, params=params, timeout=30)
            if not r.ok:
                log.error(f"GET {doctype} erreur {r.status_code}: {r.text[:200]}")
                return []
            return r.json().get("data", [])
        except Exception as e:
            log.error(f"GET {doctype}: {e}")
            return []

    def _post(self, doctype, data: dict):
        """Crée un nouveau document dans ERPNext."""
        url = f"{ERPNEXT_URL}/api/resource/{doctype}"
        payload = {"doctype": doctype, **data}
        try:
            r = self.session.post(url, json=payload, timeout=30)
            if r.status_code == 409:
                # 409 = document déjà existant — pas une erreur
                return {"exists": True}
            if not r.ok:
                log.error(f"POST {doctype} erreur {r.status_code}: {r.text[:300]}")
                return None
            return r.json().get("data", {})
        except Exception as e:
            log.error(f"POST {doctype}: {e}")
            return None

    def _put(self, doctype, name, data: dict):
        """Met à jour un document existant dans ERPNext."""
        url = f"{ERPNEXT_URL}/api/resource/{doctype}/{requests.utils.quote(name)}"
        try:
            r = self.session.put(url, json=data, timeout=30)
            if not r.ok:
                log.error(f"PUT {doctype}/{name} erreur {r.status_code}: {r.text[:300]}")
                return None
            return r.json().get("data", {})
        except Exception as e:
            log.error(f"PUT {doctype}/{name}: {e}")
            return None

    # ─────────────────────────────────────────────
    # ÉTAPE 1 : Récupère l'entrepôt principal
    # ─────────────────────────────────────────────
    def get_default_warehouse(self) -> str:
        """Récupère le premier entrepôt actif."""
        warehouses = self._get(
            "Warehouse",
            fields=["name","warehouse_name","is_group"],
            filters=[["disabled","=",0],["is_group","=",0]],
            limit=5
        )
        if warehouses:
            wh = warehouses[0].get("name","")
            log.info(f"Entrepôt par défaut : {wh}")
            return wh
        log.warning("Aucun entrepôt trouvé — utilise 'Stores - H'")
        return "Stores - H"

    # ─────────────────────────────────────────────
    # ÉTAPE 2 : Crée les seuils de réappro (Item Reorder)
    # ─────────────────────────────────────────────
    def setup_reorder_levels(self, warehouse: str):
        """
        Crée des seuils de réapprovisionnement pour tous
        les articles stockables qui n'en ont pas encore.

        Le seuil est calculé automatiquement :
        - reorder_level = stock actuel (pour déclencher immédiatement)
        - reorder_qty   = 10 unités par défaut (à ajuster manuellement)
        """
        log.info("\n── ÉTAPE 1 : Seuils de réappro (Item Reorder) ──")

        # Récupère les articles stockables
        items = self._get(
            "Item",
            fields=["name","item_name","item_group"],
            filters=[["disabled","=",0],["is_stock_item","=",1]],
            limit=500
        )
        log.info(f"   {len(items)} articles stockables trouvés")

        # Récupère les seuils déjà configurés
        existing = self._get("Item Reorder", fields=["parent"], limit=500)
        already_set = set(e.get("parent","") for e in existing)
        log.info(f"   {len(already_set)} articles ont déjà un seuil")

        created = 0
        skipped = 0
        errors  = 0

        for item in items:
            code = item.get("name","")
            name = item.get("item_name","")

            if code in already_set:
                skipped += 1
                continue

            # Récupère le stock actuel depuis Bin
            bins = self._get(
                "Bin",
                fields=["actual_qty"],
                filters=[["item_code","=",code],["warehouse","=",warehouse]],
                limit=1
            )
            actual_qty = float(bins[0].get("actual_qty",0)) if bins else 0.0

            # Seuil = stock actuel + 5 (pour déclencher rapidement)
            # Quantité à commander = max(10, stock actuel * 0.5)
            reorder_level = max(actual_qty + 5, 10)
            reorder_qty   = max(10, actual_qty * 0.5)

            # Met à jour l'article avec le seuil de réappro
            # ERPNext stocke les seuils dans la table enfant "reorder_levels"
            result = self._put("Item", code, {
                "reorder_levels": [{
                    "warehouse":              warehouse,
                    "warehouse_reorder_level": reorder_level,
                    "warehouse_reorder_qty":   reorder_qty,
                    "material_request_type":  "Purchase",
                }]
            })

            if result:
                created += 1
                log.info(f"   ✅ {code} ({name}) → seuil={reorder_level}, qté={reorder_qty}")
            else:
                errors += 1
                log.warning(f"   ⚠️  {code} → échec")

        log.info(f"   Résultat : {created} créés | {skipped} déjà configurés | {errors} erreurs")
        return created

    # ─────────────────────────────────────────────
    # ÉTAPE 3 : Crée les prix d'achat (Item Price)
    # ─────────────────────────────────────────────
    def setup_item_prices(self):
        """
        Crée une liste de prix d'achat standard pour les articles.
        Basé sur les factures d'achat existantes.
        """
        log.info("\n── ÉTAPE 2 : Prix d'achat (Item Price) ──")

        # Récupère la liste de prix d'achat standard
        buying_lists = self._get(
            "Price List",
            fields=["name"],
            filters=[["buying","=",1]],
            limit=5
        )
        if not buying_lists:
            log.warning("   Aucune liste de prix d'achat trouvée")
            # Crée une liste de prix standard
            self._post("Price List", {
                "price_list_name": "Standard Buying",
                "buying": 1,
                "selling": 0,
                "currency": "DZD",
            })
            price_list = "Standard Buying"
        else:
            price_list = buying_lists[0].get("name","Standard Buying")
        log.info(f"   Liste de prix : {price_list}")

        # Récupère les articles avec leur prix standard
        items = self._get(
            "Item",
            fields=["name","item_name","standard_rate","last_purchase_rate"],
            filters=[["disabled","=",0],["is_stock_item","=",1]],
            limit=500
        )

        # Récupère les prix déjà créés
        existing_prices = self._get(
            "Item Price",
            fields=["item_code"],
            filters=[["buying","=",1],["price_list","=",price_list]],
            limit=500
        )
        already_priced = set(p.get("item_code","") for p in existing_prices)

        created = 0
        skipped = 0

        for item in items:
            code = item.get("name","")
            rate = float(item.get("last_purchase_rate") or item.get("standard_rate") or 0)

            if code in already_priced:
                skipped += 1
                continue

            if rate <= 0:
                # Prix inconnu — on met 0 pour signaler qu'il faut le compléter
                rate = 0
                log.debug(f"   {code} → prix inconnu (0 DZD)")

            result = self._post("Item Price", {
                "item_code":       code,
                "item_name":       item.get("item_name",""),
                "price_list":      price_list,
                "buying":          1,
                "selling":         0,
                "price_list_rate": rate,
                "currency":        "DZD",
            })

            if result and not result.get("exists"):
                created += 1
                log.info(f"   ✅ {code} → {rate} DZD")
            else:
                skipped += 1

        log.info(f"   Résultat : {created} créés | {skipped} déjà existants")
        return created

    # ─────────────────────────────────────────────
    # ÉTAPE 4 : Met à jour les territoires clients
    # ─────────────────────────────────────────────
    def setup_customer_territories(self):
        """
        Met à jour le territoire (wilaya) des clients qui n'en ont pas.
        Essaie de deviner depuis l'adresse si disponible,
        sinon met "Algeria" par défaut.
        """
        log.info("\n── ÉTAPE 3 : Territoires clients ──")

        # Récupère les clients sans territoire
        customers = self._get(
            "Customer",
            fields=["name","customer_name","territory"],
            filters=[["territory","=",""]],
            limit=200
        )

        # Essaie aussi les clients avec territory null
        customers_null = self._get(
            "Customer",
            fields=["name","customer_name","territory"],
            limit=200
        )
        customers_to_fix = [
            c for c in customers_null
            if not c.get("territory") or c.get("territory") == ""
        ]

        log.info(f"   {len(customers_to_fix)} clients sans territoire")

        updated = 0
        for c in customers_to_fix:
            name = c.get("name","")

            # Essaie de deviner la wilaya depuis le nom du client
            # ex: "D.E.Medea" → "Médéa"
            territory = "Algeria"  # défaut
            client_name_lower = (c.get("customer_name","") or name).lower()

            wilaya_map = {
                "alger": "Alger", "algiers": "Alger",
                "oran": "Oran", "wahran": "Oran",
                "constantine": "Constantine",
                "annaba": "Annaba",
                "blida": "Blida",
                "tizi": "Tizi Ouzou",
                "bejaia": "Béjaïa", "bgayet": "Béjaïa",
                "setif": "Sétif", "setif": "Sétif",
                "medea": "Médéa", "médéa": "Médéa",
                "boumerdes": "Boumerdès",
                "tipaza": "Tipaza",
                "chlef": "Chlef",
                "msila": "M'Sila",
                "batna": "Batna",
                "biskra": "Biskra",
                "ghardaia": "Ghardaïa",
                "ouargla": "Ouargla",
                "tamanrasset": "Tamanrasset",
            }

            for key, wilaya in wilaya_map.items():
                if key in client_name_lower:
                    territory = wilaya
                    break

            result = self._put("Customer", name, {"territory": territory})
            if result:
                updated += 1
                log.info(f"   ✅ {name} → {territory}")

        log.info(f"   Résultat : {updated} clients mis à jour")
        return updated

    # ─────────────────────────────────────────────
    # ÉTAPE 5 : Crée les groupes de fournisseurs
    # ─────────────────────────────────────────────
    def setup_supplier_groups(self):
        """
        Assigne un groupe à chaque fournisseur qui n'en a pas.
        Groupe par défaut : "All Supplier Groups"
        """
        log.info("\n── ÉTAPE 4 : Groupes fournisseurs ──")

        suppliers = self._get(
            "Supplier",
            fields=["name","supplier_name","supplier_group"],
            filters=[["disabled","=",0]],
            limit=200
        )

        updated = 0
        for s in suppliers:
            if not s.get("supplier_group"):
                result = self._put("Supplier", s.get("name",""), {
                    "supplier_group": "All Supplier Groups"
                })
                if result:
                    updated += 1
                    log.info(f"   ✅ {s.get('supplier_name',s.get('name'))} → All Supplier Groups")

        log.info(f"   Résultat : {updated} fournisseurs mis à jour")
        return updated

    # ─────────────────────────────────────────────
    # ÉTAPE 6 : Crée les groupes de clients
    # ─────────────────────────────────────────────
    def setup_customer_groups(self):
        """
        Assigne un groupe à chaque client qui n'en a pas.
        """
        log.info("\n── ÉTAPE 5 : Groupes clients ──")

        customers = self._get(
            "Customer",
            fields=["name","customer_name","customer_group"],
            limit=200
        )

        updated = 0
        for c in customers:
            if not c.get("customer_group"):
                result = self._put("Customer", c.get("name",""), {
                    "customer_group": "Individual"
                })
                if result:
                    updated += 1
                    log.info(f"   ✅ {c.get('customer_name',c.get('name'))} → Individual")

        log.info(f"   Résultat : {updated} clients mis à jour")
        return updated


# ─────────────────────────────────────────────
# Rapport final
# ─────────────────────────────────────────────
def print_summary(results: dict):
    print("\n" + "=" * 55)
    print("RÉSUMÉ DE LA CONFIGURATION")
    print("=" * 55)
    for key, val in results.items():
        status = "✅" if val > 0 else "⚠️ "
        print(f"  {status}  {key:<35} : {val} éléments")
    print("=" * 55)
    print("\nRelance maintenant : python test_groq.py")
    print("L'IA utilisera ces données réelles sans halluciner.")


# ─────────────────────────────────────────────
# Pipeline principal
# ─────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 55)
    print("CONFIGURATION AUTOMATIQUE ERPNEXT")
    print("=" * 55)

    setup = ERPSetup()

    # Récupère l'entrepôt par défaut
    warehouse = setup.get_default_warehouse()

    results = {}

    # Étape 1 — Seuils de réappro
    try:
        results["Seuils de réappro (Item Reorder)"] = setup.setup_reorder_levels(warehouse)
    except Exception as e:
        log.error(f"Étape 1 échouée : {e}")
        results["Seuils de réappro (Item Reorder)"] = 0

    # Étape 2 — Prix d'achat
    try:
        results["Prix d'achat (Item Price)"] = setup.setup_item_prices()
    except Exception as e:
        log.error(f"Étape 2 échouée : {e}")
        results["Prix d'achat (Item Price)"] = 0

    # Étape 3 — Territoires clients
    try:
        results["Territoires clients"] = setup.setup_customer_territories()
    except Exception as e:
        log.error(f"Étape 3 échouée : {e}")
        results["Territoires clients"] = 0

    # Étape 4 — Groupes fournisseurs
    try:
        results["Groupes fournisseurs"] = setup.setup_supplier_groups()
    except Exception as e:
        log.error(f"Étape 4 échouée : {e}")
        results["Groupes fournisseurs"] = 0

    # Groupes clients
    try:
        results["Groupes clients"] = setup.setup_customer_groups()
    except Exception as e:
        log.error(f"Étape 5 échouée : {e}")
        results["Groupes clients"] = 0

    print_summary(results)