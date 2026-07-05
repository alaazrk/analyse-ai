"""
erpnext.py
----------
Connexion à ERPNext via API REST.
Récupère les données par segments, les analyse,
et génère des prompts résumés pour Ollama.

Prérequis :
    pip install requests python-dotenv

Variables d'environnement (.env) :
    ERPNEXT_URL        = http://192.168.1.XX:8000
    ERPNEXT_API_KEY    = xxxxxxxxxxxxxxxx
    ERPNEXT_API_SECRET = xxxxxxxxxxxxxxxx

Comment créer une clé API dans ERPNext :
    1. Va dans Settings > API Access
    2. Crée un utilisateur avec les droits Read sur Stock, Purchase, Sales
    3. Génère une API Key + API Secret
    4. Copie les deux dans ton .env
"""

import os
import json
import logging
from datetime import datetime, timedelta
from dotenv import load_dotenv
import requests

# ─────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────
load_dotenv()

ERPNEXT_URL  = os.getenv("ERPNEXT_URL", "http://localhost:8000")
API_KEY      = os.getenv("ERPNEXT_API_KEY")
API_SECRET   = os.getenv("ERPNEXT_API_SECRET")
TODAY        = datetime.today().strftime("%Y-%m-%d")
LAST_30_DAYS = (datetime.today() - timedelta(days=30)).strftime("%Y-%m-%d")

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)


# ─────────────────────────────────────────────
# Classe ERPNextClient
# ─────────────────────────────────────────────
class ERPNextClient:
    """
    Boîte à outils pour parler à ERPNext via son API REST.

    Authentification :
        ERPNext utilise des tokens API.
        Chaque requête envoie le header :
            Authorization: token CLE:SECRET
        ERPNext vérifie ce token et retourne les données
        auxquelles cet utilisateur a accès.
    """

    def __init__(self):
        if not API_KEY or not API_SECRET:
            raise ValueError(
                "ERPNEXT_API_KEY et ERPNEXT_API_SECRET manquent dans .env\n"
                "Crée une clé API dans ERPNext : Settings > API Access"
            )

        # On crée une session HTTP réutilisable
        # Avantage : le header Authorization est envoyé automatiquement
        # à CHAQUE requête sans avoir à le répéter
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"token {API_KEY}:{API_SECRET}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        })
        log.info(f"✅ ERPNextClient initialisé — URL: {ERPNEXT_URL}")

    def _get(self, doctype: str, filters: list = None, fields: list = None, limit: int = 200) -> list:
        """
        Appel GET sur l'API Resource d'ERPNext.

        Comment fonctionne l'API ERPNext ?
        -----------------------------------
        ERPNext expose chaque table (DocType) via une URL :
            GET /api/resource/NOM_DU_DOCTYPE

        Les paramètres se mettent dans l'URL après le ? :
            ?fields=["item_code","qty"]        ← quelles colonnes récupérer
            &filters=[["status","=","Active"]] ← conditions de filtrage
            &limit_page_length=200             ← nombre de lignes max

        ERPNext retourne toujours :
            { "data": [ {...}, {...}, ... ] }

        Exemples d'URLs réelles appelées :
            GET http://monserveur:8000/api/resource/Bin
                ?fields=["item_code","actual_qty","reorder_level"]
                &limit_page_length=500

            GET http://monserveur:8000/api/resource/Purchase Order
                ?fields=["name","supplier","grand_total","status"]
                &filters=[["transaction_date",">=","2025-05-01"]]
                &limit_page_length=200
        """

        # Construction de l'URL : base + nom du doctype
        url = f"{ERPNEXT_URL}/api/resource/{doctype}"

        # Paramètres GET — requests les ajoute automatiquement après le ?
        params = {"limit_page_length": limit}

        # filters et fields DOIVENT être des chaînes JSON
        # Pas des listes Python — ERPNext les lit comme du texte dans l'URL
        if filters:
            params["filters"] = json.dumps(filters)
        if fields:
            params["fields"] = json.dumps(fields)

        log.debug(f"   GET {url} params={params}")

        try:
            resp = self.session.get(url, params=params, timeout=30)

            # ERPNext retourne des erreurs HTTP avec des messages JSON utiles
            if not resp.ok:
                log.error(f"   ERPNext erreur {resp.status_code} sur {doctype}")
                log.error(f"   Message : {resp.text[:400]}")
                return []

            # resp.json() transforme le texte JSON en dictionnaire Python
            return resp.json().get("data", [])

        except requests.exceptions.ConnectionError:
            log.error(f"   Impossible de contacter ERPNext sur {ERPNEXT_URL}")
            log.error(f"   Vérifie ERPNEXT_URL dans ton .env")
            return []
        except requests.exceptions.Timeout:
            log.error(f"   Timeout ERPNext sur {doctype}")
            return []
        except Exception as e:
            log.error(f"   Erreur inattendue sur {doctype} : {e}")
            return []

    # ─────────────────────────────────────────────
    # Segment 1 : Stock faible
    # ─────────────────────────────────────────────
    def get_low_stock(self) -> list:
        """
        Récupère les articles dont le stock est faible.

        Pourquoi 3 étapes ?
        -------------------
        reorder_level est interdit sur Item ET sur Bin via API Frappe.
        La vraie table des seuils est : Item Reorder (table enfant de Item)
        Elle contient : parent (=item_code), warehouse_reorder_level, warehouse_reorder_qty

        Étape 1 : GET /api/resource/Item
                  → noms et items actifs (sans reorder_level)

        Étape 2 : GET /api/resource/Item Reorder
                  → seuils par article (warehouse_reorder_level autorisé ici)

        Étape 3 : GET /api/resource/Bin
                  → stock actuel par article + entrepôt

        Croisement Python : actual_qty <= warehouse_reorder_level → à commander
        """
        log.info("Segment 1 — Stock faible (Item + Item Reorder + Bin)...")

        # ── Étape 1 : liste des articles actifs ──
        items = self._get(
            doctype="Item",
            filters=[
                ["disabled", "=", 0],
                ["is_stock_item", "=", 1],
            ],
            fields=["name", "item_name", "item_group"],
            limit=500
        )
        log.info(f"   {len(items)} articles actifs")

        # Dictionnaire item_code → item_name
        items_dict = {i.get("name"): i.get("item_name", "") for i in items}

        # ── Étape 2 : seuils depuis Item Reorder ──
        # Item Reorder = table enfant qui contient les seuils de réappro
        # Champs autorisés : parent, warehouse_reorder_level, warehouse_reorder_qty
        reorders = self._get(
            doctype="Item Reorder",
            fields=[
                "parent",                   # = item_code
                "warehouse",               # entrepôt concerné
                "warehouse_reorder_level", # seuil de réappro
                "warehouse_reorder_qty",   # quantité à commander
                "material_request_type",   # type : Purchase ou Transfer
            ],
            limit=500
        )
        log.info(f"   {len(reorders)} règles de réappro trouvées")

        # Dictionnaire : item_code → seuil
        seuils_dict = {}
        for r in reorders:
            code  = r.get("parent")
            level = float(r.get("warehouse_reorder_level") or 0)
            if code and level > 0:
                seuils_dict[code] = {
                    "item_name":     items_dict.get(code, code),
                    "warehouse":     r.get("warehouse", ""),
                    "reorder_level": level,
                    "reorder_qty":   float(r.get("warehouse_reorder_qty") or 0),
                }
        log.info(f"   {len(seuils_dict)} articles ont un seuil configuré")

        # ── Étape 3 : stock actuel depuis Bin ──
        all_bins = self._get(
            doctype="Bin",
            fields=[
                "item_code", "warehouse", "actual_qty",
                "reserved_qty", "ordered_qty", "projected_qty",
            ],
            limit=500
        )
        log.info(f"   {len(all_bins)} lignes Bin récupérées")

        # ── Croisement Python ──
        low = []
        for bin_row in all_bins:
            code       = bin_row.get("item_code")
            actual_qty = float(bin_row.get("actual_qty") or 0)

            if code not in seuils_dict:
                continue

            seuil = seuils_dict[code]

            if actual_qty <= seuil["reorder_level"]:
                low.append({
                    "item_code":     code,
                    "item_name":     seuil["item_name"],
                    "warehouse":     bin_row.get("warehouse"),
                    "actual_qty":    actual_qty,
                    "reserved_qty":  float(bin_row.get("reserved_qty")  or 0),
                    "ordered_qty":   float(bin_row.get("ordered_qty")   or 0),
                    "projected_qty": float(bin_row.get("projected_qty") or 0),
                    "reorder_level": seuil["reorder_level"],
                    "reorder_qty":   seuil["reorder_qty"],
                })

        log.info(f"   {len(low)} articles sous le seuil de réappro")
        return low

    # ─────────────────────────────────────────────
    # Segment 2 : Commandes d'achat récentes
    # ─────────────────────────────────────────────
    def get_purchase_orders(self) -> list:
        """
        Commandes d'achat des 30 derniers jours.

        Doctype : Purchase Order
        URL appelée :
        GET /api/resource/Purchase Order
            ?fields=["name","supplier","transaction_date","grand_total","status","per_received"]
            &filters=[["transaction_date",">=","2025-05-01"]]
            &limit_page_length=200
        """
        log.info("Segment 2 — Commandes d'achat (Purchase Order)...")

        orders = self._get(
            doctype="Purchase Order",
            filters=[
                ["transaction_date", ">=", LAST_30_DAYS],  # Date >= il y a 30 jours
                ["docstatus", "=", 1],                      # 1 = document soumis (pas brouillon)
            ],
            fields=[
                "name",             # Numéro de commande ex: PO-2025-00123
                "supplier",         # Nom du fournisseur
                "transaction_date", # Date de la commande
                "grand_total",      # Montant total TTC
                "status",           # Draft / Submitted / Closed / Cancelled
                "per_received",     # % de la commande déjà reçu
                "per_billed",       # % de la commande déjà facturé
                "currency",         # Devise
            ],
            limit=200
        )

        log.info(f"   {len(orders)} commandes d'achat trouvées")
        return orders

    # ─────────────────────────────────────────────
    # Segment 3 : Ventes récentes
    # ─────────────────────────────────────────────
    def get_sales_orders(self) -> list:
        """
        Commandes de vente des 30 derniers jours.

        Doctype : Sales Order
        URL appelée :
        GET /api/resource/Sales Order
            ?fields=["name","customer","transaction_date","grand_total","status","per_delivered"]
            &filters=[["transaction_date",">=","2025-05-01"],["docstatus","=",1]]
            &limit_page_length=200
        """
        log.info("Segment 3 — Ventes (Sales Order)...")

        orders = self._get(
            doctype="Sales Order",
            filters=[
                ["transaction_date", ">=", LAST_30_DAYS],
                ["docstatus", "=", 1],
            ],
            fields=[
                "name",
                "customer",
                "transaction_date",
                "grand_total",
                "status",
                "per_delivered",    # % livré
                "per_billed",       # % facturé
                "currency",
            ],
            limit=200
        )

        log.info(f"   {len(orders)} commandes de vente trouvées")
        return orders

    # ─────────────────────────────────────────────
    # Segment 4 : Top articles vendus
    # ─────────────────────────────────────────────
    def get_top_items(self) -> list:
        """
        Articles les plus vendus sur 30 jours.

        Pourquoi 2 étapes ?
        -------------------
        Sales Invoice Item est une table ENFANT dans ERPNext.
        Les tables enfants ont des restrictions API :
        - posting_date est interdit dans les filtres
        - On ne peut pas filtrer par date directement

        Solution en 2 étapes :
        Étape 1 : récupère les factures (table PARENT = Sales Invoice)
                  filtrée par posting_date → autorisé ici
                  → on obtient la liste des noms de factures

        Étape 2 : récupère les lignes d'articles (table ENFANT = Sales Invoice Item)
                  filtrée par le nom de la facture parent → autorisé
                  → on obtient les articles vendus

        URLs appelées :
        Étape 1 : GET /api/resource/Sales Invoice
                      ?fields=["name"]
                      &filters=[["posting_date",">=","2026-05-30"],["docstatus","=",1]]

        Étape 2 : GET /api/resource/Sales Invoice Item
                      ?fields=["item_code","item_name","qty","amount","parent"]
                      &filters=[["parent","in",["SINV-001","SINV-002",...]]]
        """
        log.info("Segment 4 — Top articles (Sales Invoice + Sales Invoice Item)...")

        # ── Étape 1 : récupère les factures des 30 derniers jours ──
        # posting_date est autorisé sur Sales Invoice (table parent)
        factures = self._get(
            doctype="Sales Invoice",
            filters=[
                ["posting_date", ">=", LAST_30_DAYS],  # ✅ autorisé sur table parent
                ["docstatus", "=", 1],
            ],
            fields=["name", "posting_date"],
            limit=300
        )

        log.info(f"   {len(factures)} factures trouvées sur 30 jours")

        if not factures:
            log.info("   Aucune facture — 0 top articles")
            return []

        # On extrait juste les noms des factures ex: ["SINV-001", "SINV-002"]
        noms_factures = [f.get("name") for f in factures if f.get("name")]

        # ── Étape 2 : récupère les lignes d'articles de ces factures ──
        # On filtre par "parent" = nom de la facture
        # "in" veut dire : parent est dans cette liste
        lines = self._get(
            doctype="Sales Invoice Item",
            filters=[
                ["parent", "in", noms_factures],  # ✅ autorisé sur table enfant
            ],
            fields=[
                "item_code",
                "item_name",
                "qty",      # Quantité vendue
                "amount",   # Montant
                "parent",   # Nom de la facture parent
            ],
            limit=1000
        )

        log.info(f"   {len(lines)} lignes d'articles récupérées")

        # ── Agrégation Python par item_code ──
        # On additionne les quantités et montants par article
        aggregated = {}
        for line in lines:
            code = line.get("item_code", "INCONNU")
            if code not in aggregated:
                aggregated[code] = {
                    "item_code":    code,
                    "item_name":    line.get("item_name", ""),
                    "total_qty":    0.0,
                    "total_amount": 0.0,
                }
            aggregated[code]["total_qty"]    += float(line.get("qty")    or 0)
            aggregated[code]["total_amount"] += float(line.get("amount") or 0)

        # Tri par quantité décroissante — top 20
        top = sorted(aggregated.values(), key=lambda x: x["total_qty"], reverse=True)[:20]
        log.info(f"   {len(top)} top articles identifiés")
        return top

    # ─────────────────────────────────────────────
    # Segment 4bis : Historique achats par fournisseur
    # ─────────────────────────────────────────────
    def get_item_prices(self) -> list:
        """
        Récupère l'historique des montants payés par fournisseur
        depuis Purchase Invoice (factures d'achat validées).

        Pourquoi Purchase Invoice et pas Purchase Order Item ?
        -------------------------------------------------------
        Frappe bloque les champs des tables enfants (Purchase Order Item,
        Purchase Invoice Item) via l'API REST — on ne peut pas récupérer
        item_code + rate directement.

        Solution : on utilise Purchase Invoice (table parent) qui est
        accessible et donne : supplier + grand_total + posting_date.

        Ça permet à Qwen3 de comparer le volume d'achat par fournisseur
        et d'identifier quel fournisseur coûte le plus/moins cher globalement.

        URL appelée :
        GET /api/resource/Purchase Invoice
            ?fields=["name","supplier","grand_total","posting_date","status"]
            &filters=[["docstatus","=",1]]
        """
        log.info("Segment 4bis — Historique achats par fournisseur (Purchase Invoice)...")

        invoices = self._get(
            doctype="Purchase Invoice",
            filters=[["docstatus", "=", 1]],
            fields=[
                "name",
                "supplier",
                "grand_total",    # montant total de la facture
                "posting_date",   # date de la facture
                "status",         # Paid / Unpaid / Overdue
            ],
            limit=200
        )
        log.info(f"   {len(invoices)} factures d'achat trouvées")

        if not invoices:
            return []

        # ── Agrégation par fournisseur ──
        # On regroupe toutes les factures par fournisseur pour avoir :
        # - le total payé à chaque fournisseur
        # - le nombre de factures
        # - la date du dernier achat
        aggregated = {}
        for inv in invoices:
            supplier = inv.get("supplier", "Inconnu")
            total    = float(inv.get("grand_total") or 0)
            date     = inv.get("posting_date", "")

            if supplier not in aggregated:
                aggregated[supplier] = {
                    "supplier":        supplier,
                    "total_achats":    0.0,
                    "nb_factures":     0,
                    "dernier_achat":   "",
                    "factures":        []
                }
            aggregated[supplier]["total_achats"] += total
            aggregated[supplier]["nb_factures"]  += 1
            if date > aggregated[supplier]["dernier_achat"]:
                aggregated[supplier]["dernier_achat"] = date
            aggregated[supplier]["factures"].append({
                "name":        inv.get("name"),
                "grand_total": total,
                "date":        date,
                "status":      inv.get("status"),
            })

        # Tri par total décroissant — fournisseur le plus utilisé en premier
        result = sorted(aggregated.values(), key=lambda x: x["total_achats"], reverse=True)
        log.info(f"   {len(result)} fournisseurs avec historique d'achats")
        return result

    # ─────────────────────────────────────────────
    # Segment 5 : Fournisseurs actifs
    # ─────────────────────────────────────────────
    def get_suppliers(self) -> list:
        """
        Liste des fournisseurs actifs.

        Doctype : Supplier
        URL appelée :
        GET /api/resource/Supplier
            ?fields=["name","supplier_name","supplier_group","country","on_hold"]
            &filters=[["disabled","=",0]]
            &limit_page_length=100
        """
        log.info("Segment 5 — Fournisseurs (Supplier)...")

        suppliers = self._get(
            doctype="Supplier",
            filters=[
                ["disabled", "=", 0],   # 0 = actif, 1 = désactivé
            ],
            fields=[
                "name",
                "supplier_name",    # Nom complet du fournisseur
                "supplier_group",   # Groupe ex: Local, Import, Matériaux...
                "country",          # Pays
                "on_hold",          # 1 = suspendu (ne pas commander)
            ],
            limit=100
        )

        log.info(f"   {len(suppliers)} fournisseurs actifs")
        return suppliers

    # ─────────────────────────────────────────────
    # Segment 6 : Factures fournisseur impayées
    # ─────────────────────────────────────────────
    def get_unpaid_invoices(self) -> list:
        """
        Factures fournisseur impayées ou en retard.

        Doctype : Purchase Invoice
        URL appelée :
        GET /api/resource/Purchase Invoice
            ?fields=["name","supplier","posting_date","due_date","grand_total","outstanding_amount","status"]
            &filters=[["status","in",["Unpaid","Overdue"]],["docstatus","=",1]]
            &limit_page_length=100
        """
        log.info("Segment 6 — Factures impayées (Purchase Invoice)...")

        invoices = self._get(
            doctype="Purchase Invoice",
            filters=[
                ["status", "in", ["Unpaid", "Overdue"]],  # in = parmi ces valeurs
                ["docstatus", "=", 1],
            ],
            fields=[
                "name",
                "supplier",
                "posting_date",         # Date de la facture
                "due_date",             # Date d'échéance
                "grand_total",          # Montant total
                "outstanding_amount",   # Montant encore dû
                "status",               # Unpaid ou Overdue
            ],
            limit=100
        )

        log.info(f"   {len(invoices)} factures impayées")
        return invoices


# ─────────────────────────────────────────────
# Classe PromptBuilder
# ─────────────────────────────────────────────
class PromptBuilder:
    """
    Transforme les données brutes ERPNext en texte
    lisible et structuré pour Ollama/Qwen3.

    Pourquoi construire des prompts texte ?
    → Qwen3 est un modèle de langage, il comprend du texte.
    → Il faut lui présenter les données de façon claire
      avec une question précise à la fin.
    """

    @staticmethod
    def _truncate(data: list, max_items: int = 15) -> list:
        """Garde seulement les N premiers éléments pour ne pas dépasser le contexte du modèle."""
        return data[:max_items]

    def build_stock_prompt(self, low_stock: list) -> str:
        if not low_stock:
            return ""
        items = self._truncate(low_stock, 20)
        lines = []
        for i in items:
            lines.append(
                f"  - Article: {i.get('item_code')} | "
                f"Entrepôt: {i.get('warehouse')} | "
                f"Stock actuel: {i.get('actual_qty')} | "
                f"Seuil réappro: {i.get('reorder_level')} | "
                f"Stock projeté: {i.get('projected_qty')} | "
                f"Qté à commander: {i.get('reorder_qty') or 'non défini'}"
            )
        return (
            f"=== STOCK FAIBLE ({len(low_stock)} articles) ===\n"
            f"Date : {TODAY}\n\n"
            + "\n".join(lines)
            + "\n\nQuestion : Quels articles commander en priorité et pourquoi ?\n"
        )

    def build_purchases_prompt(self, orders: list) -> str:
        if not orders:
            return ""
        items = self._truncate(orders, 15)
        total = sum(float(o.get("grand_total", 0)) for o in orders)
        lines = []
        for o in items:
            lines.append(
                f"  - {o.get('name')} | {o.get('supplier')} | "
                f"{o.get('transaction_date')} | {o.get('grand_total')} {o.get('currency','')} | "
                f"Statut: {o.get('status')} | Reçu: {o.get('per_received')}%"
            )
        return (
            f"=== ACHATS 30 JOURS ({len(orders)} commandes — Total: {total:.2f}) ===\n"
            f"Date : {TODAY}\n\n"
            + "\n".join(lines)
            + "\n\nQuestion : Dépendance excessive sur un fournisseur ? Tendances anormales ?\n"
        )

    def build_sales_prompt(self, orders: list) -> str:
        if not orders:
            return ""
        items = self._truncate(orders, 15)
        total = sum(float(o.get("grand_total", 0)) for o in orders)
        lines = []
        for o in items:
            lines.append(
                f"  - {o.get('name')} | {o.get('customer')} | "
                f"{o.get('transaction_date')} | {o.get('grand_total')} | "
                f"Livré: {o.get('per_delivered')}%"
            )
        return (
            f"=== VENTES 30 JOURS ({len(orders)} commandes — CA: {total:.2f}) ===\n"
            f"Date : {TODAY}\n\n"
            + "\n".join(lines)
            + "\n\nQuestion : Quels signaux de demande forte nécessitent des achats anticipés ?\n"
        )

    def build_top_items_prompt(self, top_items: list) -> str:
        if not top_items:
            return ""
        lines = []
        for i in top_items:
            lines.append(
                f"  - {i.get('item_code')} ({i.get('item_name')}) | "
                f"Qté vendue: {i.get('total_qty')} | "
                f"CA: {i.get('total_amount'):.2f}"
            )
        return (
            f"=== TOP 20 ARTICLES VENDUS (30 jours) ===\n"
            f"Date : {TODAY}\n\n"
            + "\n".join(lines)
            + "\n\nQuestion : Quels articles acheter en priorité pour maintenir le stock ?\n"
        )

    def build_item_prices_prompt(self, prices: list) -> str:
        """
        Construit le prompt avec l'historique des achats par fournisseur.
        Basé sur Purchase Invoice (montants totaux par facture).
        """
        if not prices:
            return ""

        lines = []
        total_global = 0.0
        for p in prices[:10]:
            total_global += p.get("total_achats", 0)
            lines.append(
                f"  - {p.get('supplier')} | "
                f"Total payé: {p.get('total_achats', 0):.2f} DZD | "
                f"Nb factures: {p.get('nb_factures', 0)} | "
                f"Dernier achat: {p.get('dernier_achat', 'N/A')}"
            )

        return (
            f"=== HISTORIQUE ACHATS PAR FOURNISSEUR ({len(prices)} fournisseurs) ===\n"
            f"Date : {TODAY}\n"
            f"Total global payé à tous les fournisseurs : {total_global:.2f} DZD\n\n"
            + "\n".join(lines)
            + "\n\nQuestion : Quel fournisseur représente le plus gros volume d'achat ? "
              "Est-ce une concentration risquée ? Quel fournisseur recommandes-tu "
              "pour diversifier les achats ?\n"
        )

    def build_suppliers_prompt(self, suppliers: list, invoices: list) -> str:
        lines_sup = []
        for s in self._truncate(suppliers, 10):
            hold = "⚠️ SUSPENDU" if s.get("on_hold") else "OK"
            lines_sup.append(
                f"  - {s.get('supplier_name')} | {s.get('supplier_group')} | "
                f"{s.get('country')} | {hold}"
            )
        lines_inv = []
        total_unpaid = 0.0
        for inv in self._truncate(invoices, 10):
            total_unpaid += float(inv.get("outstanding_amount") or 0)
            lines_inv.append(
                f"  - {inv.get('name')} | {inv.get('supplier')} | "
                f"Échéance: {inv.get('due_date')} | "
                f"Dû: {inv.get('outstanding_amount')} | {inv.get('status')}"
            )
        return (
            f"=== FOURNISSEURS & PAIEMENTS ===\n"
            f"Date : {TODAY}\n"
            f"Fournisseurs actifs : {len(suppliers)} | "
            f"Factures impayées : {len(invoices)} (Total : {total_unpaid:.2f})\n\n"
            f"Fournisseurs :\n" + "\n".join(lines_sup) + "\n\n"
            f"Factures à payer :\n"
            + ("\n".join(lines_inv) if lines_inv else "  Aucune facture impayée.")
            + "\n\nQuestion : Risques de rupture ? Paiements urgents à planifier ?\n"
        )

    def build_final_synthesis_prompt(
        self,
        all_sections: list,
        noms_fournisseurs: list = None,
        noms_articles: list = None,
    ) -> str:
        """
        Assemble toutes les sections en un prompt final pour Qwen3.
        Injecte la liste exacte des noms autorisés pour bloquer les hallucinations.
        """
        combined = "\n\n".join([s for s in all_sections if s])

        # ── Liste des noms autorisés ──
        fournisseurs_str = (
            "\n".join([f"  • {n}" for n in noms_fournisseurs])
            if noms_fournisseurs else "  (aucun fournisseur trouvé)"
        )
        articles_str = (
            "\n".join([f"  • {n}" for n in noms_articles[:20]])
            if noms_articles else "  (aucun article en stock faible)"
        )

        return (
            f"Tu es un expert en gestion des achats et supply chain.\n"
            f"Voici les données ERP de l'entreprise au {TODAY}.\n\n"
            f"{combined}\n\n"
            f"{'═'*60}\n"
            f"LISTE EXACTE DES NOMS AUTORISÉS DANS TON RAPPORT\n"
            f"{'═'*60}\n"
            f"FOURNISSEURS (utilise uniquement ces noms) :\n"
            f"{fournisseurs_str}\n\n"
            f"ARTICLES EN STOCK FAIBLE (utilise uniquement ces noms) :\n"
            f"{articles_str}\n\n"
            f"{'═'*60}\n"
            f"⛔ INTERDICTIONS STRICTES :\n"
            f"• NE JAMAIS inventer un nom qui n'est pas dans la liste ci-dessus\n"
            f"• Si tu veux citer un fournisseur non listé → écris exactement : [non dans ERPNext]\n"
            f"• Si tu veux citer un article non listé → écris exactement : [non dans ERPNext]\n"
            f"• Toute hallucination de nom sera une erreur grave\n"
            f"{'═'*60}\n\n"
            f"Produis un rapport structuré avec exactement ces 4 sections :\n\n"
            f"1. ACTIONS URGENTES (à faire aujourd'hui)\n"
            f"   a) TABLEAU DES FACTURES IMPAYÉES :\n"
            f"      Pour CHAQUE facture impayée cite : Numéro | Fournisseur | Montant | Échéance | Retard (jours)\n"
            f"   b) TOTAL DÛ PAR FOURNISSEUR :\n"
            f"      Calcule et affiche le total dû à chaque fournisseur.\n"
            f"   c) TOTAL GÉNÉRAL impayé (somme de toutes les factures).\n"
            f"   d) Risques si non payé.\n"
            f"   Cite uniquement les fournisseurs de la liste autorisée.\n\n"
            f"2. RECOMMANDATIONS D'ACHAT\n"
            f"   TABLEAU : Article | Quantité suggérée | Fournisseur | Prix estimé | Justification\n"
            f"   Fournisseur = uniquement ceux dans la liste autorisée.\n"
            f"   Si aucun article en stock faible → dis-le clairement.\n\n"
            f"3. STRATEGIE DE LA SEMAINE\n"
            f"   Tendances et risques basés uniquement sur les données réelles.\n\n"
            f"4. OBSERVATIONS GENERALES\n"
            f"   TABLEAU FINANCIER :\n"
            f"      Total achats (30j) | Total impayés | % impayés/achats | Risque\n"
            f"   Points d'attention basés uniquement sur les données réelles.\n\n"
            f"Réponds en français. Utilise des tirets et des tableaux markdown pour chaque section.\n"
            f"{'═'*60}\n"
        )


# ─────────────────────────────────────────────
# Fonction principale
# ─────────────────────────────────────────────
def collect_and_build_prompts() -> dict:
    """
    1. Se connecte à ERPNext
    2. Récupère les données segment par segment
    3. Construit les prompts
    4. Retourne tout dans un dictionnaire pour ollama.py
    """
    client  = ERPNextClient()
    builder = PromptBuilder()

    log.info("=" * 55)
    log.info("COLLECTE ERPNEXT — DÉBUT")
    log.info("=" * 55)

    low_stock    = client.get_low_stock()
    purchases    = client.get_purchase_orders()
    sales        = client.get_sales_orders()
    top_items    = client.get_top_items()
    item_prices  = client.get_item_prices()
    suppliers    = client.get_suppliers()
    invoices     = client.get_unpaid_invoices()

    p_stock     = builder.build_stock_prompt(low_stock)
    p_purchases = builder.build_purchases_prompt(purchases)
    p_sales     = builder.build_sales_prompt(sales)
    p_top       = builder.build_top_items_prompt(top_items)
    p_prices    = builder.build_item_prices_prompt(item_prices)
    p_suppliers = builder.build_suppliers_prompt(suppliers, invoices)
    # ── Liste exacte des noms autorisés ──
    # On extrait les vrais noms depuis les données brutes
    # et on les injecte dans le prompt pour bloquer les hallucinations

    noms_fournisseurs = list(set([
        s.get("supplier_name") or s.get("name","")
        for s in suppliers if s.get("name")
    ]))
    noms_articles = list(set([
        b.get("item_code","")
        for b in low_stock if b.get("item_code")
    ]))
    noms_clients = []  # sera rempli si Sales Order disponible

    p_final = builder.build_final_synthesis_prompt(
        all_sections=[p_stock, p_purchases, p_sales, p_top, p_prices, p_suppliers],
        noms_fournisseurs=noms_fournisseurs,
        noms_articles=noms_articles,
    )

    log.info("=" * 55)
    log.info("COLLECTE TERMINÉE")
    log.info("=" * 55)

    return {
        "date": TODAY,
        "segments": {
            "stock":       {"prompt": p_stock,     "data_count": len(low_stock)},
            "purchases":   {"prompt": p_purchases, "data_count": len(purchases)},
            "sales":       {"prompt": p_sales,     "data_count": len(sales)},
            "top_items":   {"prompt": p_top,       "data_count": len(top_items)},
            "item_prices": {"prompt": p_prices,    "data_count": len(item_prices)},
            "suppliers":   {"prompt": p_suppliers, "data_count": len(suppliers)},
        },
        "final_prompt": p_final,
        "raw": {
            "low_stock":   low_stock,
            "purchases":   purchases,
            "sales":       sales,
            "top_items":   top_items,
            "item_prices": item_prices,
            "suppliers":   suppliers,
            "invoices":    invoices,
            "all_items":   client._get(
                doctype="Item",
                filters=[["disabled","=",0],["is_stock_item","=",1]],
                fields=["name","item_name","item_group"],
                limit=50
            ),
        }
    }


# ─────────────────────────────────────────────
# Test direct
# ─────────────────────────────────────────────
if __name__ == "__main__":
    result = collect_and_build_prompts()
    print("\n── PROMPT FINAL ──\n")
    print(result["final_prompt"])

    with open("last_prompts.json", "w", encoding="utf-8") as f:
        json.dump({
            "date":         result["date"],
            "final_prompt": result["final_prompt"],
            "segments":     {k: v["data_count"] for k, v in result["segments"].items()}
        }, f, ensure_ascii=False, indent=2)
    print("\nPrompts sauvegardés dans last_prompts.json")