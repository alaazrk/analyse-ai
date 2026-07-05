"""
viewer.py
---------
Interface web complète :
    - Recommandations d'achat (depuis rapport_*.json)
    - Dashboard BI avec graphiques (depuis bi_*.json)

Lancement :
    pip install flask
    python viewer.py
    → http://localhost:5000
"""

import os
import json
import glob
import base64
from flask import Flask, jsonify, send_file

app = Flask(__name__)
REPORTS_DIR = "reports"
CHARTS_DIR  = "reports/charts"


def list_reports():
    files = sorted(glob.glob(os.path.join(REPORTS_DIR, "rapport_*.json")), reverse=True)
    return [os.path.basename(f).replace("rapport_","").replace(".json","") for f in files]

def list_bi_reports():
    files = sorted(glob.glob(os.path.join(REPORTS_DIR, "bi_*.json")), reverse=True)
    return [os.path.basename(f).replace("bi_","").replace(".json","") for f in files]

def load_report(date_str):
    path = os.path.join(REPORTS_DIR, f"rapport_{date_str}.json")
    if not os.path.exists(path): return None
    with open(path, "r", encoding="utf-8") as f: return json.load(f)

def load_bi(date_str):
    path = os.path.join(REPORTS_DIR, f"bi_{date_str}.json")
    if not os.path.exists(path): return None
    with open(path, "r", encoding="utf-8") as f: return json.load(f)

def img_to_base64(path):
    if not os.path.exists(path): return ""
    with open(path, "rb") as f:
        return "data:image/png;base64," + base64.b64encode(f.read()).decode()

@app.route("/api/reports")
def api_reports():
    return jsonify({"dates": list_reports()})

@app.route("/api/report/<d>")
def api_report(d):
    r = load_report(d)
    return jsonify(r) if r else (jsonify({"error":"Introuvable"}), 404)

@app.route("/api/bi_reports")
def api_bi_reports():
    return jsonify({"dates": list_bi_reports()})

@app.route("/api/bi/<d>")
def api_bi(d):
    r = load_bi(d)
    if not r: return jsonify({"error":"Introuvable"}), 404
    # Ajoute les graphiques en base64
    charts_b64 = {}
    for name in ["ca_par_mois","ca_par_territoire","ca_par_client",
                 "achats_par_fournisseur","revenus_couts_marge","ca_par_annee"]:
        path = os.path.join(CHARTS_DIR, f"{name}.png")
        b64  = img_to_base64(path)
        if b64: charts_b64[name] = b64
    r["charts_b64"] = charts_b64
    return jsonify(r)

@app.route("/")
def index():
    return PAGE

PAGE = r"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Achats IA</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
<style>
*{box-sizing:border-box;margin:0;padding:0}
:root{
  --bg:#0F1117;--surf:#161B27;--card:#1E2535;--bord:#2A3248;
  --blue:#2563EB;--blue-bg:rgba(37,99,235,.12);
  --red:#DC2626;--red-bg:rgba(220,38,38,.12);
  --green:#16A34A;--green-bg:rgba(22,163,74,.12);
  --amber:#D97706;--amber-bg:rgba(217,119,6,.12);
  --purple:#7C3AED;--purple-bg:rgba(124,58,237,.12);
  --text:#F1F5F9;--text2:#94A3B8;--text3:#475569;
}
body{font-family:'Inter',sans-serif;background:var(--bg);color:var(--text);display:flex;min-height:100vh}

/* ── Sidebar ── */
.sb{width:220px;background:var(--surf);border-right:1px solid var(--bord);
  padding:20px 12px;display:flex;flex-direction:column;gap:3px;
  position:fixed;top:0;left:0;bottom:0;overflow-y:auto}
.logo{font-size:15px;font-weight:700;padding:0 8px 18px;
  border-bottom:1px solid var(--bord);margin-bottom:10px}
.logo span{color:var(--blue)}
.grp{font-size:10px;font-weight:700;letter-spacing:.08em;color:var(--text3);
  padding:12px 12px 4px;text-transform:uppercase}
.nav{padding:9px 12px;border-radius:8px;font-size:13px;font-weight:500;
  color:var(--text2);cursor:pointer;display:flex;align-items:center;gap:9px;transition:all .15s}
.nav:hover{background:var(--card);color:var(--text)}
.nav.on{background:var(--blue-bg);color:var(--blue)}
.nav .ct{margin-left:auto;background:var(--red);color:#fff;font-size:10px;
  font-weight:700;border-radius:10px;padding:1px 6px;min-width:18px;text-align:center}
.dbox{margin-top:auto;padding-top:14px;border-top:1px solid var(--bord)}
.dbox label{font-size:11px;color:var(--text3);display:block;margin-bottom:5px;
  text-transform:uppercase;letter-spacing:.05em}
.dbox select{width:100%;background:var(--card);border:1px solid var(--bord);
  color:var(--text);padding:7px 10px;border-radius:8px;font-size:12px;
  font-family:'Inter',sans-serif;cursor:pointer;margin-bottom:8px}

/* ── Main ── */
.main{margin-left:220px;flex:1;padding:28px 32px;min-height:100vh;max-width:calc(100vw - 220px)}
.topbar{margin-bottom:24px}
.ptitle{font-size:22px;font-weight:700}
.psub{font-size:13px;color:var(--text2);margin-top:4px}
.tag{display:inline-block;font-size:11px;background:var(--blue-bg);color:var(--blue);
  padding:3px 10px;border-radius:20px;font-weight:600;margin-top:8px}

/* ── Métriques ── */
.metrics{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin-bottom:22px}
.metric{background:var(--card);border:1px solid var(--bord);border-radius:10px;padding:16px 18px}
.metric.red{border-color:var(--red);background:var(--red-bg)}
.metric.green{border-color:var(--green);background:var(--green-bg)}
.metric.amber{border-color:var(--amber);background:var(--amber-bg)}
.metric.purple{border-color:var(--purple);background:var(--purple-bg)}
.metric .lb{font-size:11px;color:var(--text2);font-weight:600;
  text-transform:uppercase;letter-spacing:.05em;margin-bottom:8px}
.metric .vl{font-size:24px;font-weight:700}
.metric .sb2{font-size:12px;color:var(--text2);margin-top:4px}
.metric.red .vl{color:var(--red)}
.metric.green .vl{color:var(--green)}
.metric.amber .vl{color:var(--amber)}
.metric.purple .vl{color:var(--purple)}

/* ── Carte ── */
.card{background:var(--card);border:1px solid var(--bord);border-radius:12px;
  margin-bottom:18px;overflow:hidden}
.ch{padding:14px 20px;border-bottom:1px solid var(--bord);
  display:flex;align-items:center;gap:10px}
.ci{width:32px;height:32px;border-radius:8px;display:flex;align-items:center;
  justify-content:center;font-size:15px;flex-shrink:0}
.card.red .ci{background:var(--red-bg)}
.card.blue .ci{background:var(--blue-bg)}
.card.green .ci{background:var(--green-bg)}
.card.amber .ci{background:var(--amber-bg)}
.card.purple .ci{background:var(--purple-bg)}
.card.grey .ci{background:rgba(148,163,184,.1)}
.ctitle{font-size:15px;font-weight:600}
.ccount{margin-left:auto;font-size:12px;color:var(--text2);
  background:var(--bord);padding:3px 10px;border-radius:20px}
.cb{padding:18px 20px}

/* ── Items urgents ── */
.ui{background:rgba(220,38,38,.07);border:1px solid rgba(220,38,38,.2);
  border-left:3px solid var(--red);border-radius:8px;padding:12px 16px;
  font-size:13px;line-height:1.7;margin-bottom:10px}
.ui:last-child{margin-bottom:0}

/* ── Items achat ── */
.pi{background:var(--surf);border:1px solid var(--bord);border-radius:10px;
  padding:16px 18px;margin-bottom:12px;display:flex;
  justify-content:space-between;align-items:flex-start;gap:16px;transition:border .15s}
.pi:last-child{margin-bottom:0}
.pi:hover{border-color:var(--blue)}
.pn{font-size:14px;font-weight:600;margin-bottom:6px}
.pd{font-size:13px;color:var(--text2);line-height:1.7}
.pr{text-align:right;flex-shrink:0;min-width:130px}
.pp{font-size:13px;font-weight:700;color:var(--blue)}
.pw{font-size:11px;color:var(--text2);margin-top:4px}

/* ── Stratégie ── */
.si{display:flex;gap:12px;align-items:flex-start;margin-bottom:12px}
.si:last-child{margin-bottom:0}
.sd{width:7px;height:7px;background:var(--green);border-radius:50%;margin-top:6px;flex-shrink:0}
.st{font-size:13px;line-height:1.7}

/* ── Observations ── */
.oi{background:var(--amber-bg);border:1px solid rgba(217,119,6,.2);
  border-radius:8px;padding:12px 16px;font-size:13px;line-height:1.7;
  color:var(--text2);margin-bottom:10px}
.oi:last-child{margin-bottom:0}

/* ── Segments ── */
.sg{display:grid;grid-template-columns:1fr 1fr;gap:12px}
.sc{background:var(--surf);border:1px solid var(--bord);border-radius:10px;padding:14px}
.sct{display:flex;justify-content:space-between;align-items:center;margin-bottom:8px}
.sn{font-size:13px;font-weight:600}
.ss{font-size:10px;font-weight:700;padding:2px 8px;border-radius:10px}
.ss.ok{background:var(--green-bg);color:#4ADE80}
.ss.vide{background:var(--bord);color:var(--text3)}
.ss.erreur{background:var(--red-bg);color:#FCA5A5}
.sr{font-size:12px;color:var(--text2);line-height:1.6;
  max-height:100px;overflow-y:auto;white-space:pre-wrap}

/* ── BI Graphiques ── */
.charts-grid{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:18px}
.chart-card{background:var(--card);border:1px solid var(--bord);border-radius:12px;overflow:hidden}
.chart-title{padding:12px 16px;font-size:13px;font-weight:600;
  border-bottom:1px solid var(--bord);color:var(--text2)}
.chart-card img{width:100%;display:block}
.chart-card.full{grid-column:1/-1}

/* ── BI Métriques financières ── */
.bi-stats{display:grid;grid-template-columns:repeat(3,1fr);gap:14px;margin-bottom:22px}
.bi-stat{background:var(--card);border:1px solid var(--bord);border-radius:10px;padding:16px 18px}
.bi-stat.pos{border-color:var(--green);background:var(--green-bg)}
.bi-stat.neg{border-color:var(--red);background:var(--red-bg)}
.bi-stat.neu{border-color:var(--blue);background:var(--blue-bg)}
.bi-stat .lb{font-size:11px;color:var(--text2);font-weight:600;
  text-transform:uppercase;letter-spacing:.05em;margin-bottom:8px}
.bi-stat .vl{font-size:20px;font-weight:700}
.bi-stat.pos .vl{color:var(--green)}
.bi-stat.neg .vl{color:var(--red)}
.bi-stat.neu .vl{color:var(--blue)}

/* ── BI Analyse IA ── */
.ai-section{background:var(--card);border:1px solid var(--bord);border-radius:12px;
  margin-bottom:16px;overflow:hidden}
.ai-head{padding:14px 20px;border-bottom:1px solid var(--bord);
  display:flex;align-items:center;gap:10px;background:rgba(37,99,235,.05)}
.ai-icon{font-size:18px}
.ai-title{font-size:14px;font-weight:600}
.ai-body{padding:16px 20px;font-size:13px;line-height:1.8;color:var(--text2);white-space:pre-wrap}
.ai-body strong{color:var(--text)}

/* ── Table ── */
.tbl{width:100%;border-collapse:collapse;font-size:13px}
.tbl th{padding:10px 14px;text-align:left;font-size:11px;font-weight:600;
  color:var(--text3);text-transform:uppercase;letter-spacing:.05em;
  border-bottom:1px solid var(--bord)}
.tbl td{padding:10px 14px;border-bottom:1px solid rgba(42,50,72,.5);color:var(--text2)}
.tbl tr:hover td{background:rgba(37,99,235,.04);color:var(--text)}
.tbl tr:last-child td{border-bottom:none}
.tbl .vl{color:var(--text);font-weight:600}
.tbl .pos{color:var(--green);font-weight:600}
.tbl .neg{color:var(--red);font-weight:600}

/* ── Qualité données ── */
.qd-item{display:flex;justify-content:space-between;align-items:center;
  padding:10px 0;border-bottom:1px solid rgba(42,50,72,.5);font-size:13px}
.qd-item:last-child{border-bottom:none}
.qd-label{color:var(--text2)}
.qd-val{font-weight:600}
.qd-val.bad{color:var(--red)}
.qd-val.ok{color:var(--green)}
.qd-val.warn{color:var(--amber)}
.progress{height:4px;background:var(--bord);border-radius:4px;margin-top:4px;width:120px}
.progress-fill{height:100%;border-radius:4px;background:var(--red)}

/* ── État vide ── */
.empty{text-align:center;padding:60px 20px;color:var(--text2)}
.empty .ico{font-size:36px;margin-bottom:14px}
.empty p{font-size:14px;line-height:1.7}
.empty code{background:var(--card);padding:2px 8px;border-radius:4px;
  font-size:12px;color:var(--blue)}

/* ── Pulse ── */
@keyframes pulse{0%{box-shadow:0 0 0 0 rgba(220,38,38,.5)}
  70%{box-shadow:0 0 0 8px rgba(220,38,38,0)}100%{box-shadow:0 0 0 0 rgba(220,38,38,0)}}
.pulse{animation:pulse 2s infinite}

/* ── Tabs BI ── */
.tabs{display:flex;gap:4px;background:var(--surf);padding:4px;
  border-radius:10px;margin-bottom:20px;flex-wrap:wrap}
.tab{padding:7px 14px;border-radius:7px;font-size:12px;font-weight:500;
  color:var(--text2);cursor:pointer;transition:all .15s}
.tab:hover{color:var(--text)}
.tab.on{background:var(--card);color:var(--text)}
</style>
</head>
<body>

<!-- Sidebar -->
<nav class="sb">
  <div class="logo">🤖 <span>Achats</span> IA</div>

  <div class="grp">Recommandations</div>
  <div class="nav on" onclick="go('dash',this)">📊 Vue générale</div>
  <div class="nav" id="nav-urg" onclick="go('urg',this)">🔴 Actions urgentes</div>
  <div class="nav" onclick="go('buy',this)">🛒 Recommandations achat</div>
  <div class="nav" onclick="go('strat',this)">📈 Stratégie</div>
  <div class="nav" onclick="go('segs',this)">🔬 Analyses segments</div>

  <div class="grp">Business Intelligence</div>
  <div class="nav" onclick="go('bi_dash',this)">💰 Dashboard BI</div>
  <div class="nav" onclick="go('bi_charts',this)">📊 Graphiques</div>
  <div class="nav" onclick="go('bi_ai',this)">🤖 Analyse IA</div>

  <div class="dbox">
    <label>Rapport achat</label>
    <select id="sel" onchange="loadRpt(this.value)">
      <option>Chargement...</option>
    </select>
    <label>Rapport BI</label>
    <select id="selbi" onchange="loadBI(this.value)">
      <option>Chargement...</option>
    </select>
  </div>
</nav>

<!-- Main -->
<main class="main" id="main">
  <div class="empty"><div class="ico">⏳</div><p>Chargement...</p></div>
</main>

<script>
let RPT=null, BI=null, TAB='dash';

function fmt(n){
  if(!n) return '0 DZD';
  n=parseFloat(n);
  if(Math.abs(n)>=1e6) return (n/1e6).toFixed(2)+'M DZD';
  if(Math.abs(n)>=1e3) return (n/1e3).toFixed(1)+'K DZD';
  return n.toLocaleString('fr-FR')+' DZD';
}

function md(t){
  if(!t) return '';
  return t.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')
    .replace(/\*\*(.+?)\*\*/g,'<strong>$1</strong>')
    .replace(/\*(.+?)\*/g,'<em>$1</em>')
    .replace(/\n/g,'<br>');
}

function secs(txt){
  const s={u:'',p:'',st:'',o:''};
  if(!txt) return s;
  [[/1[.)]\s*ACTIONS?\s*URGENTES?([\s\S]*?)(?=2[.)]\s*RECOMMANDATIONS?|$)/i,'u'],
   [/2[.)]\s*RECOMMANDATIONS?\s*D.ACHAT([\s\S]*?)(?=3[.)]\s*STRAT|$)/i,'p'],
   [/3[.)]\s*STRAT.GIE([\s\S]*?)(?=4[.)]\s*OBSERVATIONS?|$)/i,'st'],
   [/4[.)]\s*OBSERVATIONS?([\s\S]*)/i,'o']
  ].forEach(([rx,k])=>{const m=txt.match(rx);if(m)s[k]=m[1].trim();});
  if(!s.u&&!s.p&&!s.st&&!s.o) s.p=txt;
  return s;
}

function lns(txt){
  if(!txt) return [];
  return txt.split('\n').map(l=>l.trim())
    .filter(l=>l.length>4&&!/^#{1,4}\s/.test(l)&&!/^---+$/.test(l));
}

function exName(l){
  let t=l.replace(/^[-•*#]\s*/,'').replace(/\*\*/g,'');
  const m1=t.match(/^Article\s*:\s*(.+?)(?:\s*[|:]|$)/i);
  if(m1) return m1[1].trim();
  const m2=t.match(/^([^|:\n]{5,60}?)(?:\s*[|:])/);
  if(m2) return m2[1].trim();
  return t.split(/\s+/).slice(0,5).join(' ');
}

function exPrice(l){
  const m=l.match(/([\d\s]{3,}(?:[–-][\d\s]+)?DZD)/i);
  return m?m[1].trim():'';
}

function exWhere(l){
  const m=l.match(/(?:Où acheter|Fournisseur\s*(?:recommand|alternatif)?|Zone|Marché)\s*:?\s*([^|<\n]{5,50})/i);
  return m?m[1].trim():'';
}

function set(h){document.getElementById('main').innerHTML=h;}

// ══════════════════════════════
// ONGLETS RECOMMANDATIONS
// ══════════════════════════════

function renderDash(){
  if(!RPT){set(empty('Aucun rapport','Lance <code>python test_groq.py</code>'));return;}
  const s=secs(RPT.final_report||'');
  const sm=RPT.summary||{};
  const ul=lns(s.u), pl=lns(s.p);
  let h=`<div class="topbar">
    <div class="ptitle">Vue générale — Recommandations achat</div>
    <div class="psub">Rapport du ${RPT.date}</div>
    <div class="tag">${RPT.model||''}</div>
  </div>
  <div class="metrics">
    <div class="metric ${ul.length>0?'red pulse':'green'}">
      <div class="lb">Actions urgentes</div>
      <div class="vl">${ul.length}</div>
      <div class="sb2">${ul.length>0?"À traiter aujourd'hui":"Aucune urgence"}</div>
    </div>
    <div class="metric amber">
      <div class="lb">Recommandations</div>
      <div class="vl">${pl.length}</div>
      <div class="sb2">Achats suggérés</div>
    </div>
    <div class="metric">
      <div class="lb">Segments analysés</div>
      <div class="vl">${sm.segments_ok||0}</div>
      <div class="sb2">${sm.segments_vides||0} vides</div>
    </div>
    <div class="metric purple">
      <div class="lb">Généré à</div>
      <div class="vl" style="font-size:16px;margin-top:4px">${new Date(RPT.generated_at).toLocaleTimeString('fr-FR',{hour:'2-digit',minute:'2-digit'})}</div>
      <div class="sb2">${RPT.date}</div>
    </div>
  </div>`;
  if(ul.length>0)
    h+=card('red','🔴','Actions urgentes',ul.length,
      ul.slice(0,3).map(l=>`<div class="ui">${md(l)}</div>`).join(''));
  if(pl.length>0)
    h+=card('blue','🛒','Recommandations d\'achat',pl.length,
      pl.slice(0,3).map(l=>pitem(l)).join(''));
  set(h);
}

function renderUrg(){
  if(!RPT){set(empty('Aucun rapport',''));return;}
  const ul=lns(secs(RPT.final_report||'').u);
  const raw=RPT.raw_data||{};
  const invoices=raw.invoices||[];

  // ── Tableau des factures impayées depuis les données brutes ERPNext ──
  let invoiceTable='';
  if(invoices.length>0){
    const today=new Date();
    let totalDu=0;
    const bySupplier={};

    const rows=invoices.map(inv=>{
      const due=new Date(inv.due_date||inv.posting_date||'');
      const retard=isNaN(due)?'—':Math.max(0,Math.floor((today-due)/(1000*60*60*24)));
      const montant=parseFloat(inv.outstanding_amount||inv.grand_total||0);
      totalDu+=montant;
      const sup=inv.supplier||'Inconnu';
      bySupplier[sup]=(bySupplier[sup]||0)+montant;
      const retardClass=retard>30?'neg':retard>0?'warn':'ok';
      return `<tr>
        <td class="vl">${inv.name||'—'}</td>
        <td>${inv.supplier||'—'}</td>
        <td class="neg">${montant.toLocaleString('fr-FR')} DZD</td>
        <td>${inv.due_date||inv.posting_date||'—'}</td>
        <td class="${retardClass}">${retard==='—'?'—':retard+' jours'}</td>
        <td><span class="ss ${inv.status==='Overdue'?'erreur':'vide'}">${inv.status||'—'}</span></td>
      </tr>`;
    }).join('');

    // Totaux par fournisseur
    const supRows=Object.entries(bySupplier).map(([s,v])=>
      `<tr><td class="vl">${s}</td><td class="neg" colspan="4">${v.toLocaleString('fr-FR')} DZD</td></tr>`
    ).join('');

    invoiceTable=`
      <div style="margin-bottom:16px">
        <div style="font-size:13px;font-weight:600;color:var(--text2);margin-bottom:10px;
          text-transform:uppercase;letter-spacing:.05em">📋 Factures impayées — Données ERPNext</div>
        <table class="tbl">
          <thead><tr>
            <th>N° Facture</th><th>Fournisseur</th><th>Montant dû</th>
            <th>Échéance</th><th>Retard</th><th>Statut</th>
          </tr></thead>
          <tbody>${rows}</tbody>
          <tfoot><tr style="border-top:2px solid var(--red)">
            <td colspan="2" style="font-weight:700;color:var(--text)">TOTAL DÛ</td>
            <td colspan="4" class="neg" style="font-size:15px;font-weight:700">${totalDu.toLocaleString('fr-FR')} DZD</td>
          </tr></tfoot>
        </table>
      </div>
      <div style="margin-bottom:16px">
        <div style="font-size:13px;font-weight:600;color:var(--text2);margin-bottom:10px;
          text-transform:uppercase;letter-spacing:.05em">💰 Total dû par fournisseur</div>
        <table class="tbl">
          <thead><tr><th>Fournisseur</th><th colspan="4">Total impayé</th></tr></thead>
          <tbody>${supRows}</tbody>
        </table>
      </div>`;
  }

  set(`<div class="topbar"><div class="ptitle">Actions urgentes</div>
    <div class="psub">À traiter impérativement aujourd'hui</div></div>`+
    card('red','🔴','Factures impayées — Analyse financière',invoices.length,
      invoiceTable+
      (ul.length>0?`<div style="margin-top:16px;font-size:13px;font-weight:600;
        color:var(--text2);margin-bottom:10px;text-transform:uppercase;letter-spacing:.05em">
        🤖 Analyse IA</div>`+
        ul.map(l=>`<div class="ui">${md(l)}</div>`).join(''):'')));
}

function renderBuy(){
  if(!RPT){set(empty('Aucun rapport',''));return;}
  const pl=lns(secs(RPT.final_report||'').p);
  set(`<div class="topbar"><div class="ptitle">Recommandations d'achat</div>
    <div class="psub">${pl.length} recommandation(s) avec prix de marché estimés</div></div>`+
    card('blue','🛒','Articles à acheter',pl.length,
      pl.length===0?empty2('📭','Aucune recommandation'):
      pl.map(l=>pitem(l)).join('')));
}

function renderStrat(){
  if(!RPT){set(empty('Aucun rapport',''));return;}
  const s=secs(RPT.final_report||'');
  const sl=lns(s.st), ol=lns(s.o);
  set(`<div class="topbar"><div class="ptitle">Stratégie & Observations</div>
    <div class="psub">Analyse hebdomadaire et points d'attention</div></div>`+
    card('green','📈','Stratégie de la semaine',sl.length,
      sl.length===0?empty2('📭',''):
      sl.map(l=>`<div class="si"><div class="sd"></div><div class="st">${md(l)}</div></div>`).join(''))+
    card('amber','💡','Observations générales',ol.length,
      ol.length===0?empty2('📭',''):
      ol.map(l=>`<div class="oi">${md(l)}</div>`).join('')));
}

function renderSegs(){
  if(!RPT){set(empty('Aucun rapport',''));return;}
  const segs=Object.entries(RPT.segments_analyses||{});
  set(`<div class="topbar"><div class="ptitle">Analyses détaillées par segment</div>
    <div class="psub">Données collectées depuis ERPNext</div></div>`+
    card('grey','🔬','Segments ERPNext',segs.length,
      `<div class="sg">${segs.map(([k,sg])=>`
        <div class="sc">
          <div class="sct">
            <div class="sn">${sg.segment||k}</div>
            <div class="ss ${sg.status||'vide'}">${sg.status||'vide'}</div>
          </div>
          <div class="sr">${(sg.response||'Aucune donnée').substring(0,250)}</div>
        </div>`).join('')}</div>`));
}

// ══════════════════════════════
// ONGLETS BI
// ══════════════════════════════

function renderBIDash(){
  if(!BI){set(empty('Aucun rapport BI','Lance <code>python bi_analysis.py</code>'));return;}
  const sm=BI.summary||{};
  const rev=sm.revenus_total||0, cout=sm.couts_total||0, marge=sm.marge_brute||0;
  const ca_mois=sm.ca_par_mois||{}, ca_client=sm.ca_par_client||{};
  const ca_terr=sm.ca_par_territoire||{};

  let h=`<div class="topbar">
    <div class="ptitle">Dashboard Business Intelligence</div>
    <div class="psub">Rapport du ${BI.date} — Analyse financière complète</div>
  </div>
  <div class="bi-stats">
    <div class="bi-stat ${rev>0?'pos':'neu'}">
      <div class="lb">Revenus totaux</div>
      <div class="vl">${fmt(rev)}</div>
    </div>
    <div class="bi-stat neg">
      <div class="lb">Coûts totaux</div>
      <div class="vl">${fmt(cout)}</div>
    </div>
    <div class="bi-stat ${marge>=0?'pos':'neg'}">
      <div class="lb">Marge brute</div>
      <div class="vl">${fmt(marge)}</div>
    </div>
  </div>
  <div class="metrics">
    <div class="metric green">
      <div class="lb">Meilleur mois</div>
      <div class="vl" style="font-size:16px;margin-top:2px">${sm.meilleur_mois||'N/A'}</div>
      <div class="sb2">${fmt(sm.meilleur_mois_ca||0)}</div>
    </div>
    <div class="metric blue">
      <div class="lb">Meilleure ville</div>
      <div class="vl" style="font-size:16px;margin-top:2px">${sm.meilleure_ville||'N/A'}</div>
      <div class="sb2">${fmt(sm.meilleure_ville_ca||0)}</div>
    </div>
    <div class="metric">
      <div class="lb">Clients</div>
      <div class="vl">${sm.nb_clients||0}</div>
      <div class="sb2">${sm.nb_fournisseurs||0} fournisseurs</div>
    </div>
    <div class="metric">
      <div class="lb">Articles</div>
      <div class="vl">${sm.nb_articles||0}</div>
      <div class="sb2">${sm.nb_factures_vente||0} factures vente</div>
    </div>
  </div>`;

  // Table CA par mois
  if(Object.keys(ca_mois).length>0){
    const maxCA=Math.max(...Object.values(ca_mois));
    h+=card('blue','📅','CA par mois',Object.keys(ca_mois).length,
      `<table class="tbl"><thead><tr>
        <th>Mois</th><th>CA</th><th>% du total</th><th>Statut</th>
      </tr></thead><tbody>`+
      Object.entries(ca_mois).sort((a,b)=>b[1]-a[1]).map(([m,v])=>`<tr>
        <td class="vl">${m}</td>
        <td class="pos">${fmt(v)}</td>
        <td>${rev>0?Math.round(v/rev*100)+'%':'—'}</td>
        <td>${v===maxCA?'🏆 Meilleur':'—'}</td>
      </tr>`).join('')+
      `</tbody></table>`);
  }

  // Table CA par client
  if(Object.keys(ca_client).length>0){
    const total=Object.values(ca_client).reduce((a,b)=>a+b,0);
    h+=card('green','👥','CA par client',Object.keys(ca_client).length,
      `<table class="tbl"><thead><tr>
        <th>Client</th><th>CA total</th><th>Part</th>
      </tr></thead><tbody>`+
      Object.entries(ca_client).slice(0,10).map(([c,v])=>`<tr>
        <td class="vl">${c}</td>
        <td class="pos">${fmt(v)}</td>
        <td>${total>0?Math.round(v/total*100)+'%':'—'}</td>
      </tr>`).join('')+
      `</tbody></table>`);
  }

  // Table CA par territoire
  if(Object.keys(ca_terr).length>0){
    h+=card('amber','📍','CA par ville / territoire',Object.keys(ca_terr).length,
      `<table class="tbl"><thead><tr>
        <th>Territoire</th><th>CA</th>
      </tr></thead><tbody>`+
      Object.entries(ca_terr).slice(0,10).map(([t,v])=>`<tr>
        <td class="vl">${t}</td>
        <td class="pos">${fmt(v)}</td>
      </tr>`).join('')+
      `</tbody></table>`);
  }

  // Qualité des données
  const qd=sm.qualite_donnees||{};
  if(Object.keys(qd).length>0){
    const pct=qd.pct_territoire_manquant||0;
    h+=card('red','⚠️','Qualité des données',null,
      `<div class="qd-item">
        <div class="qd-label">Clients sans territoire</div>
        <div>
          <div class="qd-val ${pct>50?'bad':pct>20?'warn':'ok'}">${qd.clients_sans_territoire||0} / ${qd.clients_total||0} (${pct}%)</div>
          <div class="progress"><div class="progress-fill" style="width:${pct}%;background:${pct>50?'var(--red)':pct>20?'var(--amber)':'var(--green)'}"></div></div>
        </div>
      </div>
      <div class="qd-item">
        <div class="qd-label">Factures sans territoire</div>
        <div class="qd-val ${(qd.pct_factures_sans_terr||0)>50?'bad':'warn'}">${qd.factures_sans_territoire||0} / ${qd.factures_total||0} (${qd.pct_factures_sans_terr||0}%)</div>
      </div>
      <div class="qd-item">
        <div class="qd-label">Action recommandée</div>
        <div class="qd-val warn">Remplir le champ "Territory" sur chaque client ERPNext</div>
      </div>`);
  }

  set(h);
}

function renderBICharts(){
  if(!BI){set(empty('Aucun rapport BI','Lance <code>python bi_analysis.py</code>'));return;}
  const charts=BI.charts_b64||{};
  const names={
    ca_par_mois:          {t:"CA par mois",icon:"📅"},
    ca_par_territoire:    {t:"CA par ville",icon:"📍"},
    ca_par_client:        {t:"Répartition clients",icon:"👥"},
    achats_par_fournisseur:{t:"Achats fournisseurs",icon:"🏭"},
    revenus_couts_marge:  {t:"Revenus vs Coûts vs Marge",icon:"💰",full:true},
    ca_par_annee:         {t:"Évolution annuelle",icon:"📈"},
  };

  let h=`<div class="topbar">
    <div class="ptitle">Graphiques BI</div>
    <div class="psub">${Object.keys(charts).length} graphiques générés</div>
  </div>
  <div class="charts-grid">`;

  Object.entries(names).forEach(([k,info])=>{
    if(charts[k]){
      h+=`<div class="chart-card ${info.full?'full':''}">
        <div class="chart-title">${info.icon} ${info.t}</div>
        <img src="${charts[k]}" alt="${info.t}" loading="lazy">
      </div>`;
    }
  });

  if(Object.keys(charts).length===0){
    h+=`<div style="grid-column:1/-1">`+
      empty('Aucun graphique disponible',
        'Lance <code>python bi_analysis.py</code> pour générer les graphiques')+
      `</div>`;
  }

  h+=`</div>`;
  set(h);
}

function renderBIAI(){
  if(!BI){set(empty('Aucun rapport BI','Lance <code>python bi_analysis.py</code>'));return;}
  const txt=BI.ai_report||'';
  if(!txt){set(empty('Aucune analyse IA',''));return;}

  // Découpe en sections numérotées
  const section_rx=[
    {t:'Résumé exécutif',rx:/1[.)]\s*R[EÉ]SUM[EÉ]\s*EX[EÉ]CUTIF([\s\S]*?)(?=2[.)]|$)/i,icon:'📋',col:'blue'},
    {t:'Analyse des performances',rx:/2[.)]\s*ANALYSE\s*DES\s*PERFORMANCES([\s\S]*?)(?=3[.)]|$)/i,icon:'📊',col:'green'},
    {t:'Qualité des données',rx:/3[.)]\s*QUALIT[EÉ]\s*DES\s*DONN[EÉ]ES([\s\S]*?)(?=4[.)]|$)/i,icon:'⚠️',col:'red'},
    {t:'Recommandations d\'achat',rx:/4[.)]\s*RECOMMANDATIONS\s*D.ACHAT([\s\S]*?)(?=5[.)]|$)/i,icon:'🛒',col:'amber'},
    {t:'Stratégie commerciale',rx:/5[.)]\s*STRAT[EÉ]GIE\s*COMMERCIALE([\s\S]*?)(?=6[.)]|$)/i,icon:'🎯',col:'purple'},
    {t:'Préférences clients',rx:/6[.)]\s*PR[EÉ]F[EÉ]RENCES([\s\S]*?)(?=7[.)]|$)/i,icon:'👥',col:'blue'},
    {t:'Prévisions',rx:/7[.)]\s*PR[EÉ]VISIONS([\s\S]*)/i,icon:'🔮',col:'green'},
  ];

  let h=`<div class="topbar">
    <div class="ptitle">Analyse IA — Qwen3</div>
    <div class="psub">Rapport complet généré par intelligence artificielle</div>
    <div class="tag">${BI.summary?.model||'Groq / Qwen3'}</div>
  </div>`;

  let found=false;
  section_rx.forEach(({t,rx,icon,col})=>{
    const m=txt.match(rx);
    if(m&&m[1].trim()){
      found=true;
      h+=`<div class="ai-section">
        <div class="ai-head">
          <div class="ai-icon">${icon}</div>
          <div class="ai-title">${t}</div>
        </div>
        <div class="ai-body">${md(m[1].trim())}</div>
      </div>`;
    }
  });

  if(!found){
    h+=`<div class="ai-section">
      <div class="ai-head"><div class="ai-icon">🤖</div><div class="ai-title">Analyse complète</div></div>
      <div class="ai-body">${md(txt)}</div>
    </div>`;
  }

  set(h);
}

// ══════════════════════════════
// HELPERS
// ══════════════════════════════

function card(col,icon,title,count,body){
  return `<div class="card ${col}">
    <div class="ch"><div class="ci">${icon}</div>
      <div class="ctitle">${title}</div>
      ${count!==null?`<div class="ccount">${count}</div>`:''}
    </div>
    <div class="cb">${body}</div>
  </div>`;
}

function pitem(l){
  const n=exName(l), p=exPrice(l), w=exWhere(l);
  return `<div class="pi">
    <div style="flex:1">
      <div class="pn">${md(n)}</div>
      <div class="pd">${md(l)}</div>
    </div>
    <div class="pr">
      ${p?`<div class="pp">${p}</div>`:''}
      ${w?`<div class="pw">📍 ${w}</div>`:''}
    </div>
  </div>`;
}

function empty(title,sub){
  return `<div class="empty"><div class="ico">📭</div>
    <p><strong>${title}</strong><br><br>${sub}</p></div>`;
}

function empty2(ico,txt){
  return `<div class="empty"><div class="ico">${ico}</div><p>${txt}</p></div>`;
}

// ══════════════════════════════
// NAVIGATION & CHARGEMENT
// ══════════════════════════════

function go(tab,el){
  TAB=tab;
  document.querySelectorAll('.nav').forEach(n=>n.classList.remove('on'));
  el.classList.add('on');
  render();
}

function render(){
  if(TAB==='dash')      renderDash();
  if(TAB==='urg')       renderUrg();
  if(TAB==='buy')       renderBuy();
  if(TAB==='strat')     renderStrat();
  if(TAB==='segs')      renderSegs();
  if(TAB==='bi_dash')   renderBIDash();
  if(TAB==='bi_charts') renderBICharts();
  if(TAB==='bi_ai')     renderBIAI();
}

async function loadRpt(d){
  if(!d||d==='Chargement...') return;
  const r=await fetch(`/api/report/${d}`);
  RPT=await r.json();
  const s=secs(RPT.final_report||'');
  const ul=lns(s.u);
  const nav=document.getElementById('nav-urg');
  nav.innerHTML=`🔴 Actions urgentes${ul.length>0?` <span class="ct">${ul.length}</span>`:''}`;
  render();
}

async function loadBI(d){
  if(!d||d==='Chargement...') return;
  const r=await fetch(`/api/bi/${d}`);
  BI=await r.json();
  if(TAB.startsWith('bi_')) render();
}

async function init(){
  // Rapports achat
  const r1=await fetch('/api/reports');
  const d1=await r1.json();
  const sel=document.getElementById('sel');
  if(d1.dates&&d1.dates.length>0){
    sel.innerHTML=d1.dates.map(x=>`<option value="${x}">${x}</option>`).join('');
    await loadRpt(d1.dates[0]);
  } else {
    sel.innerHTML='<option>Aucun rapport</option>';
  }

  // Rapports BI
  const r2=await fetch('/api/bi_reports');
  const d2=await r2.json();
  const selbi=document.getElementById('selbi');
  if(d2.dates&&d2.dates.length>0){
    selbi.innerHTML=d2.dates.map(x=>`<option value="${x}">${x}</option>`).join('');
    await loadBI(d2.dates[0]);
  } else {
    selbi.innerHTML='<option>Aucun rapport BI</option>';
  }

  render();
}

init();
</script>
</body>
</html>"""

if __name__ == "__main__":
    os.makedirs(REPORTS_DIR, exist_ok=True)
    os.makedirs(CHARTS_DIR, exist_ok=True)
    print("=" * 50)
    print("Interface démarrée → http://localhost:5000")
    print("=" * 50)
    app.run(debug=True, port=5000)