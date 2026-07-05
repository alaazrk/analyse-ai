"""
bi_analysis.py
--------------
Analyse Business Intelligence complète depuis ERPNext.

Analyses disponibles :
    - Meilleur mois de CA
    - Meilleure ville/territory
    - Produit le plus vendu
    - Revenus et marges
    - Graphiques (clients, fournisseurs, CA par mois/produit)
    - Recommandations IA (Groq/Qwen3)
    - Stratégie commerciale

Prérequis :
    pip install requests python-dotenv matplotlib

Lancement :
    python bi_analysis.py
"""

import os
import json
import logging
from datetime import datetime, timedelta
from collections import defaultdict
from dotenv import load_dotenv
import requests

load_dotenv()

ERPNEXT_URL = os.getenv("ERPNEXT_URL")
API_KEY     = os.getenv("ERPNEXT_API_KEY")
API_SECRET  = os.getenv("ERPNEXT_API_SECRET")
GROQ_KEY    = os.getenv("GROQ_API_KEY")
GROQ_MODEL  = os.getenv("GROQ_MODEL", "qwen/qwen3-32b")
GROQ_URL    = "https://api.groq.com/openai/v1/chat/completions"
TODAY       = datetime.today().strftime("%Y-%m-%d")

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)


# ─────────────────────────────────────────────
# Collecte ERPNext
# ─────────────────────────────────────────────
class BICollector:

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"token {API_KEY}:{API_SECRET}",
            "Content-Type": "application/json",
        })

    def _get(self, doctype, fields=None, filters=None, limit=500):
        url    = f"{ERPNEXT_URL}/api/resource/{doctype}"
        params = {"limit_page_length": limit}
        if fields:  params["fields"]  = json.dumps(fields)
        if filters: params["filters"] = json.dumps(filters)
        try:
            r = self.session.get(url, params=params, timeout=30)
            if not r.ok:
                log.error(f"Erreur {r.status_code} sur {doctype}: {r.text[:200]}")
                return []
            return r.json().get("data", [])
        except Exception as e:
            log.error(f"Erreur {doctype}: {e}")
            return []

    def collect_all(self):
        log.info("=" * 55)
        log.info("COLLECTE BI — DÉBUT")
        log.info("=" * 55)

        # Factures de vente
        log.info("Collecte Sales Invoice...")
        sales_invoices = self._get(
            "Sales Invoice",
            fields=["name","customer","posting_date","grand_total",
                    "total","territory","status"],
            filters=[["docstatus","=",1]],
            limit=500
        )
        log.info(f"   {len(sales_invoices)} factures de vente")

        # Clients
        log.info("Collecte Customers...")
        customers = self._get(
            "Customer",
            fields=["name","customer_name","territory","customer_group"],
            limit=200
        )
        log.info(f"   {len(customers)} clients")

        # Factures d'achat
        log.info("Collecte Purchase Invoice...")
        purchase_invoices = self._get(
            "Purchase Invoice",
            fields=["name","supplier","posting_date","grand_total","status"],
            filters=[["docstatus","=",1]],
            limit=500
        )
        log.info(f"   {len(purchase_invoices)} factures d'achat")

        # Fournisseurs
        log.info("Collecte Suppliers...")
        suppliers = self._get(
            "Supplier",
            fields=["name","supplier_name","supplier_group","country"],
            filters=[["disabled","=",0]],
            limit=200
        )
        log.info(f"   {len(suppliers)} fournisseurs")

        # Articles
        log.info("Collecte Items...")
        items = self._get(
            "Item",
            fields=["name","item_name","item_group","standard_rate"],
            filters=[["disabled","=",0]],
            limit=500
        )
        log.info(f"   {len(items)} articles")

        log.info("COLLECTE TERMINÉE")
        return {
            "sales_invoices":    sales_invoices,
            "customers":         customers,
            "purchase_invoices": purchase_invoices,
            "suppliers":         suppliers,
            "items":             items,
        }


# ─────────────────────────────────────────────
# Analyses BI
# ─────────────────────────────────────────────
class BIAnalyzer:

    def __init__(self, data: dict):
        self.data = data

    def ca_par_mois(self) -> dict:
        """CA total par mois."""
        mois = defaultdict(float)
        for inv in self.data["sales_invoices"]:
            date = inv.get("posting_date","")
            if len(date) >= 7:
                mois_key = date[:7]  # "2026-03"
                mois[mois_key] += float(inv.get("grand_total") or 0)
        return dict(sorted(mois.items()))

    def meilleur_mois(self) -> tuple:
        """Retourne (mois, CA) du meilleur mois."""
        ca = self.ca_par_mois()
        if not ca:
            return None, 0
        m = max(ca, key=ca.get)
        return m, ca[m]

    def ca_par_territoire(self) -> dict:
        """CA par territoire/ville en croisant clients + factures."""
        # Map client → territoire
        client_territory = {}
        for c in self.data["customers"]:
            t = c.get("territory") or "Non défini"
            client_territory[c.get("name")] = t

        terr = defaultdict(float)
        for inv in self.data["sales_invoices"]:
            client = inv.get("customer","")
            t      = inv.get("territory") or client_territory.get(client, "Non défini")
            terr[t] += float(inv.get("grand_total") or 0)
        return dict(sorted(terr.items(), key=lambda x: x[1], reverse=True))

    def meilleure_ville(self) -> tuple:
        """Retourne (ville, CA) de la meilleure ville."""
        terr = self.ca_par_territoire()
        if not terr:
            return None, 0
        v = max(terr, key=terr.get)
        return v, terr[v]

    def ca_par_client(self) -> dict:
        """CA total par client."""
        clients = defaultdict(float)
        for inv in self.data["sales_invoices"]:
            clients[inv.get("customer","Inconnu")] += float(inv.get("grand_total") or 0)
        return dict(sorted(clients.items(), key=lambda x: x[1], reverse=True))

    def achats_par_fournisseur(self) -> dict:
        """Montant total d'achat par fournisseur."""
        fournisseurs = defaultdict(float)
        for inv in self.data["purchase_invoices"]:
            fournisseurs[inv.get("supplier","Inconnu")] += float(inv.get("grand_total") or 0)
        return dict(sorted(fournisseurs.items(), key=lambda x: x[1], reverse=True))

    def revenus_total(self) -> float:
        """CA total sur toutes les factures de vente."""
        return sum(float(i.get("grand_total") or 0) for i in self.data["sales_invoices"])

    def couts_total(self) -> float:
        """Total des achats fournisseurs."""
        return sum(float(i.get("grand_total") or 0) for i in self.data["purchase_invoices"])

    def marge_brute(self) -> float:
        """Marge brute estimée = Revenus - Coûts."""
        return self.revenus_total() - self.couts_total()

    def ca_par_annee(self) -> dict:
        """CA par année."""
        annees = defaultdict(float)
        for inv in self.data["sales_invoices"]:
            date = inv.get("posting_date","")
            if len(date) >= 4:
                annees[date[:4]] += float(inv.get("grand_total") or 0)
        return dict(sorted(annees.items()))

    def qualite_donnees(self) -> dict:
        """Analyse la qualité des données — valeurs manquantes."""
        clients = self.data["customers"]
        total   = len(clients)
        if total == 0:
            return {}

        sans_territory = sum(1 for c in clients if not c.get("territory"))
        sans_group     = sum(1 for c in clients if not c.get("customer_group"))

        sales  = self.data["sales_invoices"]
        total_s = len(sales)
        sans_territory_s = sum(1 for s in sales if not s.get("territory"))

        return {
            "clients_total":            total,
            "clients_sans_territoire":  sans_territory,
            "clients_sans_groupe":      sans_group,
            "pct_territoire_manquant":  round(sans_territory/total*100) if total else 0,
            "factures_total":           total_s,
            "factures_sans_territoire": sans_territory_s,
            "pct_factures_sans_terr":   round(sans_territory_s/total_s*100) if total_s else 0,
        }

    def full_summary(self) -> dict:
        """Résumé complet de toutes les analyses."""
        mm, mm_val = self.meilleur_mois()
        mv, mv_val = self.meilleure_ville()
        return {
            "revenus_total":         self.revenus_total(),
            "couts_total":           self.couts_total(),
            "marge_brute":           self.marge_brute(),
            "meilleur_mois":         mm,
            "meilleur_mois_ca":      mm_val,
            "meilleure_ville":       mv,
            "meilleure_ville_ca":    mv_val,
            "ca_par_mois":           self.ca_par_mois(),
            "ca_par_territoire":     self.ca_par_territoire(),
            "ca_par_client":         self.ca_par_client(),
            "achats_par_fournisseur":self.achats_par_fournisseur(),
            "ca_par_annee":          self.ca_par_annee(),
            "qualite_donnees":       self.qualite_donnees(),
            "nb_clients":            len(self.data["customers"]),
            "nb_fournisseurs":       len(self.data["suppliers"]),
            "nb_articles":           len(self.data["items"]),
            "nb_factures_vente":     len(self.data["sales_invoices"]),
            "nb_factures_achat":     len(self.data["purchase_invoices"]),
        }


# ─────────────────────────────────────────────
# Graphiques matplotlib
# ─────────────────────────────────────────────
def generate_charts(summary: dict, output_dir: str = "reports/charts"):
    """Génère tous les graphiques et les sauvegarde en PNG."""
    try:
        import matplotlib
        matplotlib.use('Agg')  # sans interface graphique
        import matplotlib.pyplot as plt
        import matplotlib.ticker as ticker
    except ImportError:
        log.warning("matplotlib non installé — pip install matplotlib")
        return []

    os.makedirs(output_dir, exist_ok=True)
    charts = []
    DARK_BG   = '#0F1117'
    CARD_BG   = '#1E2535'
    BLUE      = '#2563EB'
    GREEN     = '#16A34A'
    AMBER     = '#D97706'
    RED       = '#DC2626'
    TEXT      = '#F1F5F9'
    TEXT2     = '#94A3B8'
    COLORS    = [BLUE, GREEN, AMBER, RED, '#7C3AED', '#0891B2', '#BE185D']

    plt.rcParams.update({
        'figure.facecolor': DARK_BG,
        'axes.facecolor':   CARD_BG,
        'axes.edgecolor':   '#2A3248',
        'axes.labelcolor':  TEXT2,
        'xtick.color':      TEXT2,
        'ytick.color':      TEXT2,
        'text.color':       TEXT,
        'grid.color':       '#2A3248',
        'grid.linestyle':   '--',
        'grid.alpha':       0.5,
        'font.family':      'DejaVu Sans',
    })

    def fmt_dzd(x, _):
        if x >= 1_000_000: return f'{x/1_000_000:.1f}M'
        if x >= 1_000:     return f'{x/1_000:.0f}K'
        return str(int(x))

    # ── Graphique 1 : CA par mois ──
    ca_mois = summary.get("ca_par_mois", {})
    if ca_mois:
        fig, ax = plt.subplots(figsize=(10, 5))
        mois   = list(ca_mois.keys())
        valeurs = list(ca_mois.values())
        bars = ax.bar(mois, valeurs, color=BLUE, alpha=0.85, width=0.5)
        # Meilleur mois en vert
        max_idx = valeurs.index(max(valeurs))
        bars[max_idx].set_color(GREEN)
        ax.set_title("Chiffre d'affaires par mois", fontsize=14, fontweight='bold', pad=15)
        ax.set_ylabel("CA (DZD)", fontsize=11)
        ax.yaxis.set_major_formatter(ticker.FuncFormatter(fmt_dzd))
        ax.grid(axis='y')
        for bar, val in zip(bars, valeurs):
            ax.text(bar.get_x()+bar.get_width()/2, bar.get_height()+5000,
                    fmt_dzd(val,None), ha='center', va='bottom', fontsize=9, color=TEXT2)
        plt.tight_layout()
        path = f"{output_dir}/ca_par_mois.png"
        plt.savefig(path, dpi=150, bbox_inches='tight')
        plt.close()
        charts.append(path)
        log.info(f"   ✅ Graphique CA par mois : {path}")

    # ── Graphique 2 : CA par territoire ──
    ca_terr = summary.get("ca_par_territoire", {})
    if ca_terr:
        fig, ax = plt.subplots(figsize=(8, 5))
        labels = list(ca_terr.keys())
        values = list(ca_terr.values())
        ax.barh(labels, values, color=COLORS[:len(labels)], alpha=0.85)
        ax.set_title("CA par territoire / ville", fontsize=14, fontweight='bold', pad=15)
        ax.set_xlabel("CA (DZD)", fontsize=11)
        ax.xaxis.set_major_formatter(ticker.FuncFormatter(fmt_dzd))
        ax.grid(axis='x')
        for i, (label, val) in enumerate(zip(labels, values)):
            ax.text(val+2000, i, fmt_dzd(val,None), va='center', fontsize=9, color=TEXT2)
        plt.tight_layout()
        path = f"{output_dir}/ca_par_territoire.png"
        plt.savefig(path, dpi=150, bbox_inches='tight')
        plt.close()
        charts.append(path)
        log.info(f"   ✅ Graphique CA par territoire : {path}")

    # ── Graphique 3 : Top clients (pie) ──
    ca_client = summary.get("ca_par_client", {})
    if ca_client:
        fig, ax = plt.subplots(figsize=(8, 6))
        labels = list(ca_client.keys())[:6]
        values = [ca_client[k] for k in labels]
        wedges, texts, autotexts = ax.pie(
            values, labels=labels, autopct='%1.1f%%',
            colors=COLORS[:len(labels)], startangle=90,
            textprops={'color': TEXT, 'fontsize': 10}
        )
        for at in autotexts:
            at.set_color(DARK_BG)
            at.set_fontweight('bold')
        ax.set_title("Répartition CA par client", fontsize=14, fontweight='bold')
        plt.tight_layout()
        path = f"{output_dir}/ca_par_client.png"
        plt.savefig(path, dpi=150, bbox_inches='tight')
        plt.close()
        charts.append(path)
        log.info(f"   ✅ Graphique clients : {path}")

    # ── Graphique 4 : Achats par fournisseur ──
    achats_f = summary.get("achats_par_fournisseur", {})
    if achats_f:
        fig, ax = plt.subplots(figsize=(8, 5))
        labels = list(achats_f.keys())
        values = list(achats_f.values())
        bars = ax.bar(labels, values, color=AMBER, alpha=0.85, width=0.5)
        ax.set_title("Achats par fournisseur", fontsize=14, fontweight='bold', pad=15)
        ax.set_ylabel("Total achats (DZD)", fontsize=11)
        ax.yaxis.set_major_formatter(ticker.FuncFormatter(fmt_dzd))
        ax.grid(axis='y')
        for bar, val in zip(bars, values):
            ax.text(bar.get_x()+bar.get_width()/2, bar.get_height()+5000,
                    fmt_dzd(val,None), ha='center', va='bottom', fontsize=9, color=TEXT2)
        plt.tight_layout()
        path = f"{output_dir}/achats_par_fournisseur.png"
        plt.savefig(path, dpi=150, bbox_inches='tight')
        plt.close()
        charts.append(path)
        log.info(f"   ✅ Graphique fournisseurs : {path}")

    # ── Graphique 5 : Revenus vs Coûts ──
    revenus = summary.get("revenus_total", 0)
    couts   = summary.get("couts_total", 0)
    marge   = summary.get("marge_brute", 0)
    if revenus > 0 or couts > 0:
        fig, ax = plt.subplots(figsize=(7, 5))
        cats   = ["Revenus\n(Ventes)", "Coûts\n(Achats)", "Marge\nBrute"]
        values = [revenus, couts, marge]
        colors = [GREEN, RED, BLUE if marge >= 0 else RED]
        bars = ax.bar(cats, values, color=colors, alpha=0.85, width=0.4)
        ax.set_title("Revenus vs Coûts vs Marge", fontsize=14, fontweight='bold', pad=15)
        ax.set_ylabel("Montant (DZD)", fontsize=11)
        ax.yaxis.set_major_formatter(ticker.FuncFormatter(fmt_dzd))
        ax.grid(axis='y')
        for bar, val in zip(bars, values):
            ax.text(bar.get_x()+bar.get_width()/2,
                    max(bar.get_height(), 0)+10000,
                    fmt_dzd(val,None), ha='center', va='bottom', fontsize=10,
                    color=TEXT, fontweight='bold')
        ax.axhline(y=0, color=TEXT2, linewidth=0.8)
        plt.tight_layout()
        path = f"{output_dir}/revenus_couts_marge.png"
        plt.savefig(path, dpi=150, bbox_inches='tight')
        plt.close()
        charts.append(path)
        log.info(f"   ✅ Graphique revenus/coûts : {path}")

    # ── Graphique 6 : CA par année ──
    ca_annee = summary.get("ca_par_annee", {})
    if len(ca_annee) >= 1:
        fig, ax = plt.subplots(figsize=(7, 5))
        annees = list(ca_annee.keys())
        values = list(ca_annee.values())
        ax.plot(annees, values, color=BLUE, marker='o', linewidth=2.5,
                markersize=8, markerfacecolor=GREEN)
        ax.fill_between(annees, values, alpha=0.1, color=BLUE)
        ax.set_title("Évolution CA par année", fontsize=14, fontweight='bold', pad=15)
        ax.set_ylabel("CA (DZD)", fontsize=11)
        ax.yaxis.set_major_formatter(ticker.FuncFormatter(fmt_dzd))
        ax.grid(axis='both')
        for x, y in zip(annees, values):
            ax.annotate(fmt_dzd(y,None), (x,y), textcoords="offset points",
                        xytext=(0,10), ha='center', fontsize=10, color=TEXT)
        plt.tight_layout()
        path = f"{output_dir}/ca_par_annee.png"
        plt.savefig(path, dpi=150, bbox_inches='tight')
        plt.close()
        charts.append(path)
        log.info(f"   ✅ Graphique CA annuel : {path}")

    log.info(f"Total : {len(charts)} graphiques générés dans {output_dir}/")
    return charts


# ─────────────────────────────────────────────
# Analyse IA — Groq/Qwen3
# ─────────────────────────────────────────────
def ask_groq(prompt: str) -> str:
    import re, time
    headers = {"Authorization": f"Bearer {GROQ_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": GROQ_MODEL,
        "messages": [{"role":"user","content":prompt}],
        "temperature": 0.3,
        "max_tokens": 2000,
    }
    try:
        r = requests.post(GROQ_URL, json=payload, headers=headers, timeout=60)
        r.raise_for_status()
        text = r.json()["choices"][0]["message"]["content"].strip()
        return re.sub(r"<think>.*?</think>","",text,flags=re.DOTALL).strip()
    except Exception as e:
        log.error(f"Erreur Groq : {e}")
        return ""


def generate_ai_report(summary: dict) -> str:
    """Demande à Qwen3 une analyse complète basée sur le résumé BI."""
    mm    = summary.get("meilleur_mois","N/A")
    mm_ca = summary.get("meilleur_mois_ca",0)
    mv    = summary.get("meilleure_ville","N/A")
    mv_ca = summary.get("meilleure_ville_ca",0)
    rev   = summary.get("revenus_total",0)
    cout  = summary.get("couts_total",0)
    marge = summary.get("marge_brute",0)
    qd    = summary.get("qualite_donnees",{})

    # CA par mois formaté
    ca_mois_txt = "\n".join([
        f"  {m} : {v:,.0f} DZD"
        for m,v in summary.get("ca_par_mois",{}).items()
    ])

    # CA par territoire
    ca_terr_txt = "\n".join([
        f"  {t} : {v:,.0f} DZD"
        for t,v in list(summary.get("ca_par_territoire",{}).items())[:5]
    ])

    # Top clients
    ca_client_txt = "\n".join([
        f"  {c} : {v:,.0f} DZD"
        for c,v in list(summary.get("ca_par_client",{}).items())[:5]
    ])

    # Fournisseurs
    fournisseurs_txt = "\n".join([
        f"  {f} : {v:,.0f} DZD"
        for f,v in list(summary.get("achats_par_fournisseur",{}).items())[:5]
    ])

    prompt = f"""Tu es un expert en analyse business et stratégie commerciale pour une PME algérienne.

Voici les données business de l'entreprise au {TODAY} :

=== FINANCES ===
Revenus totaux (ventes)  : {rev:,.0f} DZD
Coûts totaux (achats)    : {cout:,.0f} DZD
Marge brute estimée      : {marge:,.0f} DZD ({round(marge/rev*100) if rev else 0}%)

=== PERFORMANCE PAR MOIS ===
{ca_mois_txt if ca_mois_txt else "Aucune donnée"}
Meilleur mois : {mm} ({mm_ca:,.0f} DZD)

=== PERFORMANCE PAR VILLE/TERRITOIRE ===
{ca_terr_txt if ca_terr_txt else "Aucune donnée"}
Meilleure ville : {mv} ({mv_ca:,.0f} DZD)

=== TOP CLIENTS ===
{ca_client_txt if ca_client_txt else "Aucune donnée"}

=== FOURNISSEURS ===
{fournisseurs_txt if fournisseurs_txt else "Aucune donnée"}

=== QUALITÉ DES DONNÉES ===
Clients sans territoire : {qd.get("clients_sans_territoire",0)}/{qd.get("clients_total",0)} ({qd.get("pct_territoire_manquant",0)}%)
Factures sans territoire: {qd.get("factures_sans_territoire",0)}/{qd.get("factures_total",0)} ({qd.get("pct_factures_sans_terr",0)}%)

─────────────────────────────────────────
⚠️ RÈGLES ABSOLUES OBLIGATOIRES :
- Utilise UNIQUEMENT les noms de fournisseurs, clients et articles présents dans les données ci-dessus.
- NE JAMAIS inventer de noms (pas de "Mehdi Circulaire", "Fourn1", "Client X" ou tout autre nom fictif).
- Si un nom n'est pas dans les données, écris "non identifié dans ERPNext".
- Si les données sont insuffisantes pour une section, dis-le clairement.
─────────────────────────────────────────
Produis un rapport complet avec ces 7 sections :

1. RÉSUMÉ EXÉCUTIF
   Situation globale en 3-4 points clés.

2. ANALYSE DES PERFORMANCES
   Meilleur mois, meilleure ville, tendances observées.
   Combien l'entreprise gagne-t-elle réellement ?

3. QUALITÉ DES DONNÉES
   Problèmes identifiés (valeurs manquantes).
   Comment normaliser et standardiser les données ERPNext.
   Actions concrètes à faire dans ERPNext.

4. RECOMMANDATIONS D'ACHAT
   Basé sur les coûts vs revenus, que faut-il acheter/optimiser ?

5. STRATÉGIE COMMERCIALE
   - Ciblage géographique : quelles villes cibler en priorité ?
   - Promotions : quels clients/produits privilégier ?
   - Comment augmenter les ventes de 20% ce mois-ci ?

6. PRÉFÉRENCES ET HABITUDES CLIENTS
   Analyse des patterns d'achat observés.
   Quels clients reviennent ? Quand achètent-ils le plus ?

7. PRÉVISIONS
   Estimation du CA du prochain mois basée sur les tendances.
   Objectif réaliste à atteindre.

Réponds en français. Sois précis et actionnable.
─────────────────────────────────────────"""

    log.info("Envoi analyse BI à Groq/Qwen3...")
    return ask_groq(prompt)


# ─────────────────────────────────────────────
# Sauvegarde
# ─────────────────────────────────────────────
def save_bi_report(summary: dict, ai_report: str, charts: list):
    os.makedirs("reports", exist_ok=True)
    date = datetime.today().strftime("%Y-%m-%d")

    # JSON
    json_path = f"reports/bi_{date}.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump({
            "date":      date,
            "summary":   summary,
            "ai_report": ai_report,
            "charts":    charts,
        }, f, ensure_ascii=False, indent=2)
    log.info(f"Rapport BI JSON : {json_path}")

    # TXT
    txt_path = f"reports/bi_{date}.txt"
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(f"RAPPORT BI — {date}\n")
        f.write("=" * 60 + "\n\n")
        f.write(f"Revenus     : {summary['revenus_total']:,.0f} DZD\n")
        f.write(f"Coûts       : {summary['couts_total']:,.0f} DZD\n")
        f.write(f"Marge brute : {summary['marge_brute']:,.0f} DZD\n")
        f.write(f"Meilleur mois  : {summary['meilleur_mois']} ({summary['meilleur_mois_ca']:,.0f} DZD)\n")
        f.write(f"Meilleure ville: {summary['meilleure_ville']} ({summary['meilleure_ville_ca']:,.0f} DZD)\n")
        f.write("\n" + "=" * 60 + "\n\n")
        f.write("ANALYSE IA\n\n")
        f.write(ai_report)
    log.info(f"Rapport BI TXT  : {txt_path}")

    return json_path


# ─────────────────────────────────────────────
# Pipeline principal
# ─────────────────────────────────────────────
def run():
    # 1. Collecte
    collector = BICollector()
    data      = collector.collect_all()

    # 2. Analyse
    analyzer  = BIAnalyzer(data)
    summary   = analyzer.full_summary()

    print("\n" + "=" * 55)
    print("RÉSUMÉ BI")
    print("=" * 55)
    print(f"Revenus totaux  : {summary['revenus_total']:,.0f} DZD")
    print(f"Coûts totaux    : {summary['couts_total']:,.0f} DZD")
    print(f"Marge brute     : {summary['marge_brute']:,.0f} DZD")
    print(f"Meilleur mois   : {summary['meilleur_mois']} → {summary['meilleur_mois_ca']:,.0f} DZD")
    print(f"Meilleure ville : {summary['meilleure_ville']} → {summary['meilleure_ville_ca']:,.0f} DZD")
    print(f"Nb clients      : {summary['nb_clients']}")
    print(f"Nb fournisseurs : {summary['nb_fournisseurs']}")
    print(f"Nb articles     : {summary['nb_articles']}")

    # 3. Graphiques
    log.info("Génération des graphiques...")
    charts = generate_charts(summary)

    # 4. Analyse IA
    ai_report = generate_ai_report(summary)

    print("\n" + "=" * 55)
    print("ANALYSE IA (Qwen3)")
    print("=" * 55)
    print(ai_report)

    # 5. Sauvegarde
    save_bi_report(summary, ai_report, charts)
    print(f"\nGraphiques sauvegardés dans reports/charts/")
    print(f"Rapport complet dans reports/bi_{TODAY}.txt")


if __name__ == "__main__":
    run()