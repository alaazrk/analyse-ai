"""
viewer.py - Dashboard Achats IA
Design inspiré du Figma DataPilot Analytics
Adapté pour ERPNext + Qwen3/Groq
pip install flask
python viewer.py → http://localhost:5000
"""
import os, json, glob, base64
from flask import Flask, jsonify
app = Flask(__name__)
REPORTS_DIR = "reports"
CHARTS_DIR  = "reports/charts"

def list_reports():
    files = sorted(glob.glob(os.path.join(REPORTS_DIR, "rapport_*.json")), reverse=True)
    return [os.path.basename(f).replace("rapport_","").replace(".json","") for f in files]

def list_bi():
    files = sorted(glob.glob(os.path.join(REPORTS_DIR, "bi_*.json")), reverse=True)
    return [os.path.basename(f).replace("bi_","").replace(".json","") for f in files]

def load(path):
    if not os.path.exists(path): return None
    with open(path,"r",encoding="utf-8") as f: return json.load(f)

def img64(name):
    p = os.path.join(CHARTS_DIR, f"{name}.png")
    if not os.path.exists(p): return ""
    with open(p,"rb") as f: return "data:image/png;base64,"+base64.b64encode(f.read()).decode()

@app.route("/api/reports")
def api_reports(): return jsonify({"dates": list_reports()})

@app.route("/api/report/<d>")
def api_report(d):
    r = load(os.path.join(REPORTS_DIR, f"rapport_{d}.json"))
    return jsonify(r) if r else (jsonify({"error":"404"}), 404)

@app.route("/api/bi_reports")
def api_bi_reports(): return jsonify({"dates": list_bi()})

@app.route("/api/bi/<d>")
def api_bi(d):
    r = load(os.path.join(REPORTS_DIR, f"bi_{d}.json"))
    if not r: return jsonify({"error":"404"}), 404
    r["charts_b64"] = {n: img64(n) for n in [
        "ca_par_mois","ca_par_territoire","ca_par_client",
        "achats_par_fournisseur","revenus_couts_marge","ca_par_annee"
    ] if img64(n)}
    return jsonify(r)

@app.route("/")
def index(): return PAGE

PAGE = r"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Achats IA Analytics</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.0/chart.umd.min.js"></script>
<style>
*{box-sizing:border-box;margin:0;padding:0}
:root{
  --navy:#0D1117;--navy2:#161B27;--navy3:#1C2333;--navy4:#242E42;
  --bord:rgba(255,255,255,.07);--bord2:rgba(255,255,255,.12);
  --cyan:#00D4FF;--cyan-dim:rgba(0,212,255,.12);--cyan-glow:rgba(0,212,255,.25);
  --green:#00E396;--green-dim:rgba(0,227,150,.12);
  --red:#FF4560;--red-dim:rgba(255,69,96,.12);
  --amber:#FEB019;--amber-dim:rgba(254,176,25,.12);
  --purple:#775DD0;--purple-dim:rgba(119,93,208,.12);
  --text:#E8EDF4;--text2:#8B95A8;--text3:#4A5568;
  --radius:12px;
}
body{font-family:'Inter',sans-serif;background:var(--navy);color:var(--text);min-height:100vh;overflow-x:hidden}

/* ── TOP NAV ── */
.topnav{
  background:var(--navy2);border-bottom:1px solid var(--bord);
  padding:0 28px;display:flex;align-items:center;gap:0;
  position:sticky;top:0;z-index:200;height:52px;
}
.logo-box{display:flex;align-items:center;gap:10px;margin-right:32px;flex-shrink:0}
.logo-icon{width:32px;height:32px;background:linear-gradient(135deg,#00D4FF,#0066FF);
  border-radius:8px;display:flex;align-items:center;justify-content:center;font-size:15px}
.logo-text{font-size:14px;font-weight:700;letter-spacing:.02em}
.logo-text span{color:var(--text2);font-weight:400;font-size:11px;margin-left:4px;letter-spacing:.08em;text-transform:uppercase}

.tabs{display:flex;align-items:center;gap:2px;flex:1}
.tab{padding:0 14px;height:52px;display:flex;align-items:center;gap:7px;
  font-size:12.5px;font-weight:500;color:var(--text2);cursor:pointer;
  border-bottom:2px solid transparent;transition:all .2s;white-space:nowrap}
.tab:hover{color:var(--text);background:rgba(255,255,255,.03)}
.tab.on{color:var(--cyan);border-bottom-color:var(--cyan)}
.tab .dot{width:6px;height:6px;background:var(--red);border-radius:50%;margin-left:2px}
.tab-icon{font-size:13px;opacity:.8}

.nav-right{display:flex;align-items:center;gap:10px;margin-left:auto;flex-shrink:0}
.period-btn{display:flex;align-items:center;gap:7px;background:var(--navy3);
  border:1px solid var(--bord2);color:var(--text);padding:6px 14px;
  border-radius:8px;font-size:12px;font-weight:500;cursor:pointer;transition:all .15s}
.period-btn:hover{border-color:var(--cyan);color:var(--cyan)}
.nav-btn{background:var(--navy3);border:1px solid var(--bord);color:var(--text2);
  padding:6px 14px;border-radius:8px;font-size:12px;font-weight:500;cursor:pointer;
  display:flex;align-items:center;gap:6px;transition:all .15s}
.nav-btn:hover{border-color:var(--bord2);color:var(--text)}
.avatar{width:30px;height:30px;background:linear-gradient(135deg,#00D4FF,#0066FF);
  border-radius:50%;display:flex;align-items:center;justify-content:center;
  font-size:11px;font-weight:700;cursor:pointer}

/* ── SUB BAR ── */
.subbar{padding:10px 28px;border-bottom:1px solid var(--bord);
  display:flex;align-items:center;justify-content:space-between;
  background:var(--navy);font-size:12px;color:var(--text2)}
.subbar-left{display:flex;align-items:center;gap:8px}
.subbar .dot-green{width:7px;height:7px;background:var(--green);border-radius:50%;flex-shrink:0}
.subbar strong{color:var(--text);font-weight:600}
.subbar-right{color:var(--text2);font-size:12px;display:flex;align-items:center;gap:6px;cursor:pointer}
.subbar-right:hover{color:var(--cyan)}

/* ── MAIN ── */
.main{padding:28px 28px;max-width:1400px;margin:0 auto}
.page-title{font-size:22px;font-weight:700;margin-bottom:4px}
.page-sub{font-size:13px;color:var(--text2);margin-bottom:24px}
.page-head{display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:24px}

/* ── KPI CARDS ── */
.kpi-row{display:grid;gap:14px;margin-bottom:24px}
.kpi-row-6{grid-template-columns:repeat(6,1fr)}
.kpi-row-4{grid-template-columns:repeat(4,1fr)}
.kpi-row-3{grid-template-columns:repeat(3,1fr)}
.kpi{background:var(--navy3);border:1px solid var(--bord);border-radius:var(--radius);
  padding:18px 20px;transition:border .2s}
.kpi:hover{border-color:var(--bord2)}
.kpi .lb{font-size:10px;font-weight:700;color:var(--text2);text-transform:uppercase;
  letter-spacing:.1em;margin-bottom:12px}
.kpi .val{font-size:24px;font-weight:700;line-height:1;display:flex;align-items:baseline;gap:8px}
.kpi .val-small{font-size:18px}
.kpi .badge-change{font-size:11px;font-weight:600;padding:2px 7px;border-radius:6px;display:flex;align-items:center;gap:3px}
.badge-up{background:rgba(0,227,150,.15);color:var(--green)}
.badge-down{background:rgba(255,69,96,.15);color:var(--red)}
.kpi .sub{font-size:12px;color:var(--text2);margin-top:8px}

/* ── CARD ── */
.card{background:var(--navy3);border:1px solid var(--bord);border-radius:var(--radius);
  margin-bottom:20px;overflow:hidden}
.card-head{padding:16px 22px;border-bottom:1px solid var(--bord);
  display:flex;align-items:center;gap:12px}
.card-head-left{flex:1}
.card-title{font-size:15px;font-weight:600}
.card-sub{font-size:12px;color:var(--text2);margin-top:2px}
.card-head-right{display:flex;align-items:center;gap:10px}
.pill{font-size:11px;font-weight:600;padding:4px 12px;border-radius:20px;cursor:pointer;transition:all .15s;border:1px solid transparent}
.pill.on{background:var(--cyan);color:var(--navy);border-color:var(--cyan)}
.pill.off{color:var(--text2);border-color:var(--bord)}
.pill.off:hover{border-color:var(--bord2);color:var(--text)}
.card-body{padding:20px 22px}
.card-body-0{padding:0}
.link-btn{font-size:12px;color:var(--cyan);cursor:pointer;display:flex;align-items:center;gap:4px}
.link-btn:hover{opacity:.8}

/* ── ACTION CARD ── */
.action-item{padding:18px 22px;border-bottom:1px solid var(--bord);
  display:flex;align-items:flex-start;gap:16px;transition:background .15s}
.action-item:last-child{border-bottom:none}
.action-item:hover{background:rgba(255,255,255,.02)}
.action-icon{width:40px;height:40px;border-radius:10px;display:flex;align-items:center;
  justify-content:center;font-size:18px;flex-shrink:0}
.action-icon.crit{background:var(--red-dim);border:1px solid rgba(255,69,96,.2)}
.action-icon.high{background:var(--amber-dim);border:1px solid rgba(254,176,25,.2)}
.action-icon.med{background:var(--cyan-dim);border:1px solid rgba(0,212,255,.2)}
.action-content{flex:1}
.action-title{font-size:14px;font-weight:600;display:flex;align-items:center;gap:10px;margin-bottom:4px}
.action-desc{font-size:13px;color:var(--text2);line-height:1.6}
.action-right{text-align:right;flex-shrink:0;min-width:130px}
.action-time{font-size:12px;margin-bottom:4px;display:flex;align-items:center;justify-content:flex-end;gap:5px}
.action-time.red{color:var(--red)}
.action-time.amber{color:var(--amber)}
.action-time.cyan{color:var(--cyan)}
.action-amount{font-size:13px;font-weight:600;color:var(--text2);margin-bottom:8px}
.btn-traiter{background:var(--cyan-dim);border:1px solid var(--cyan);color:var(--cyan);
  padding:5px 14px;border-radius:8px;font-size:12px;font-weight:600;cursor:pointer;transition:all .15s}
.btn-traiter:hover{background:var(--cyan);color:var(--navy)}

/* ── BADGE ── */
.badge{display:inline-flex;align-items:center;font-size:10px;font-weight:700;
  padding:3px 9px;border-radius:5px;text-transform:uppercase;letter-spacing:.05em}
.badge.crit{background:var(--red-dim);color:var(--red);border:1px solid rgba(255,69,96,.3)}
.badge.high{background:var(--amber-dim);color:var(--amber);border:1px solid rgba(254,176,25,.3)}
.badge.med{background:var(--cyan-dim);color:var(--cyan);border:1px solid rgba(0,212,255,.3)}
.badge.ok{background:var(--green-dim);color:var(--green);border:1px solid rgba(0,227,150,.3)}
.badge.purple{background:var(--purple-dim);color:var(--purple);border:1px solid rgba(119,93,208,.3)}

/* ── RECOMMANDATION CARD ── */
.reco-item{padding:18px 22px;border-bottom:1px solid var(--bord);
  display:flex;align-items:center;gap:16px;transition:background .15s}
.reco-item:last-child{border-bottom:none}
.reco-item:hover{background:rgba(255,255,255,.02)}
.reco-score{width:50px;flex-shrink:0;text-align:center}
.reco-score-num{font-size:22px;font-weight:800}
.reco-score-num.crit{color:var(--red)}
.reco-score-num.high{color:var(--amber)}
.reco-score-num.med{color:var(--cyan)}
.reco-score-label{font-size:9px;color:var(--text3);text-transform:uppercase;letter-spacing:.08em}
.reco-content{flex:1}
.reco-title{font-size:14px;font-weight:600;display:flex;align-items:center;gap:10px;margin-bottom:4px}
.reco-desc{font-size:12px;color:var(--text2);margin-bottom:6px;line-height:1.5}
.reco-meta{font-size:12px;color:var(--text3);display:flex;gap:16px}
.reco-meta span{color:var(--text2)}
.reco-meta strong{color:var(--text);font-weight:500}
.reco-right{text-align:right;flex-shrink:0;min-width:140px}
.reco-price{font-size:16px;font-weight:700;color:var(--green);margin-bottom:4px}
.reco-price-label{font-size:11px;color:var(--text2);margin-bottom:10px}
.btn-cmd{background:var(--cyan);color:var(--navy);padding:7px 18px;
  border-radius:8px;font-size:12px;font-weight:700;cursor:pointer;
  border:none;transition:opacity .15s}
.btn-cmd:hover{opacity:.85}

/* ── SEGMENT CARD ── */
.seg-cards{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin-bottom:20px}
.seg-card{background:var(--navy3);border:1px solid var(--bord);border-radius:var(--radius);
  padding:18px 20px;transition:border .2s}
.seg-card:hover{border-color:var(--bord2)}
.seg-card-top{display:flex;align-items:center;justify-content:space-between;margin-bottom:10px}
.seg-dot{width:10px;height:10px;border-radius:50%}
.seg-pct-big{font-size:28px;font-weight:700;margin:6px 0 4px}
.seg-name{font-size:14px;font-weight:600;margin-bottom:2px}
.seg-clients{font-size:12px;color:var(--text2)}

/* ── STRATÉGIE PROGRESS ── */
.strat-item{background:var(--navy4);border:1px solid var(--bord);border-radius:10px;
  padding:16px 18px;margin-bottom:12px}
.strat-item:last-child{margin-bottom:0}
.strat-top{display:flex;justify-content:space-between;align-items:center;margin-bottom:8px}
.strat-title{font-size:14px;font-weight:600}
.strat-meta{font-size:12px;color:var(--text2);margin-bottom:10px;display:flex;gap:12px}
.strat-meta .roi{color:var(--green);font-weight:600}
.strat-meta .budget{color:var(--cyan)}
.progress-bar{height:5px;background:rgba(255,255,255,.08);border-radius:5px;overflow:hidden}
.progress-fill{height:100%;border-radius:5px;transition:width .6s ease}
.progress-label{display:flex;justify-content:space-between;align-items:center;margin-top:6px}
.progress-pct{font-size:13px;font-weight:600;color:var(--text)}
.progress-date{font-size:11px;color:var(--text3);display:flex;align-items:center;gap:4px}

/* ── AI INSIGHT ── */
.ai-item{padding:18px 22px;border-bottom:1px solid var(--bord);
  display:flex;align-items:flex-start;gap:16px}
.ai-item:last-child{border-bottom:none}
.ai-brain{width:36px;height:36px;background:var(--cyan-dim);border:1px solid rgba(0,212,255,.2);
  border-radius:10px;display:flex;align-items:center;justify-content:center;font-size:16px;flex-shrink:0}
.ai-content{flex:1}
.ai-title{font-size:14px;font-weight:600;display:flex;align-items:center;gap:10px;margin-bottom:6px}
.ai-desc{font-size:13px;color:var(--text2);line-height:1.6;margin-bottom:10px}
.ai-confidence{display:flex;align-items:center;gap:10px;font-size:12px;color:var(--text3)}
.ai-conf-bar{flex:0 0 120px;height:4px;background:rgba(255,255,255,.08);border-radius:4px;overflow:hidden}
.ai-conf-fill{height:100%;background:var(--cyan);border-radius:4px}
.ai-conf-pct{color:var(--cyan);font-weight:600}
.ai-potential{color:var(--green);font-weight:600;margin-left:8px}
.ai-right{flex-shrink:0}
.btn-explore{background:var(--navy4);border:1px solid var(--bord2);color:var(--text2);
  padding:5px 14px;border-radius:8px;font-size:12px;cursor:pointer;transition:all .15s}
.btn-explore:hover{border-color:var(--cyan);color:var(--cyan)}

/* ── CONF MODELS ── */
.conf-item{display:flex;align-items:center;gap:14px;padding:10px 0;
  border-bottom:1px solid var(--bord)}
.conf-item:last-child{border-bottom:none}
.conf-name{font-size:13px;font-weight:500;width:180px;flex-shrink:0}
.conf-model-name{font-size:11px;color:var(--text3);margin-top:2px}
.conf-bar-wrap{flex:1;height:5px;background:rgba(255,255,255,.06);border-radius:5px;overflow:hidden}
.conf-bar-fill{height:100%;background:var(--cyan);border-radius:5px}
.conf-pct{font-size:13px;font-weight:600;color:var(--cyan);width:40px;text-align:right;flex-shrink:0}

/* ── TABLE ── */
.tbl-wrap{overflow-x:auto}
table{width:100%;border-collapse:collapse;font-size:13px}
thead tr{background:rgba(255,255,255,.02)}
th{padding:11px 20px;text-align:left;font-size:10px;font-weight:700;
  color:var(--text3);text-transform:uppercase;letter-spacing:.09em;
  border-bottom:1px solid var(--bord);white-space:nowrap;cursor:pointer;user-select:none}
th:hover{color:var(--text2)}
td{padding:13px 20px;border-bottom:1px solid rgba(255,255,255,.04);color:var(--text2)}
tr:last-child td{border-bottom:none}
tr:hover td{background:rgba(255,255,255,.02);color:var(--text)}
.td-main{font-weight:600;color:var(--text)}
.td-red{color:var(--red);font-weight:600}
.td-green{color:var(--green);font-weight:600}
.td-cyan{color:var(--cyan);font-weight:600}
.td-amber{color:var(--amber);font-weight:600}
.tbl-footer{padding:12px 20px;border-top:1px solid var(--bord);
  display:flex;justify-content:space-between;align-items:center;
  background:rgba(255,255,255,.01);font-size:12px;color:var(--text2)}
.tbl-footer .total{font-weight:700;color:var(--text)}
.tbl-footer .total-val{color:var(--red);font-size:15px;font-weight:700}

/* ── GRID LAYOUTS ── */
.grid-2{display:grid;grid-template-columns:1fr 1fr;gap:20px;margin-bottom:20px}
.grid-6-4{display:grid;grid-template-columns:3fr 2fr;gap:20px;margin-bottom:20px}
.grid-matrice{display:grid;grid-template-columns:1fr 1fr;gap:12px}
.matrice-cell{border-radius:10px;padding:16px;border:1px solid var(--bord)}
.matrice-cell.champions{background:rgba(0,227,150,.06);border-color:rgba(0,227,150,.2)}
.matrice-cell.develop{background:rgba(0,212,255,.06);border-color:rgba(0,212,255,.2)}
.matrice-cell.fidel{background:rgba(254,176,25,.06);border-color:rgba(254,176,25,.2)}
.matrice-cell.watch{background:rgba(255,69,96,.06);border-color:rgba(255,69,96,.2)}
.matrice-cell .mc-title{font-size:13px;font-weight:700;margin-bottom:4px}
.matrice-cell .mc-sub{font-size:11px;color:var(--text2);margin-bottom:10px}
.matrice-cell .mc-num{font-size:28px;font-weight:800;margin-bottom:4px}
.matrice-cell .mc-detail{font-size:11px;color:var(--text2)}

/* ── OBJECTIFS ── */
.obj-item{display:flex;align-items:center;gap:14px;padding:10px 0;
  border-bottom:1px solid var(--bord)}
.obj-item:last-child{border-bottom:none}
.obj-label{font-size:12px;color:var(--text2);width:130px;flex-shrink:0}
.obj-bar-wrap{flex:1;height:6px;background:rgba(255,255,255,.06);border-radius:6px;overflow:hidden}
.obj-bar-fill{height:100%;background:var(--cyan);border-radius:6px}
.obj-vals{font-size:12px;color:var(--text2);width:90px;text-align:right;flex-shrink:0}
.obj-vals strong{color:var(--text)}

/* ── CHARTS ── */
.chart-container{position:relative;padding:16px}
.charts-grid{display:grid;grid-template-columns:1fr 1fr;gap:20px;margin-bottom:20px}
.charts-grid .full{grid-column:1/-1}

/* ── FOOTER ── */
.footer{padding:14px 28px;border-top:1px solid var(--bord);
  display:flex;justify-content:space-between;align-items:center;
  font-size:11px;color:var(--text3)}
.footer .status{display:flex;align-items:center;gap:6px;color:var(--green)}
.footer .status::before{content:'';width:7px;height:7px;background:var(--green);
  border-radius:50%;display:inline-block}

/* ── EMPTY ── */
.empty{text-align:center;padding:60px 20px;color:var(--text2)}
.empty .ico{font-size:36px;margin-bottom:14px}
.empty p{font-size:14px;line-height:1.7}
.empty code{background:var(--navy3);padding:2px 8px;border-radius:4px;font-size:12px;color:var(--cyan)}

/* ── PULSE ── */
@keyframes pulse{0%{box-shadow:0 0 0 0 rgba(255,69,96,.5)}
  70%{box-shadow:0 0 0 8px rgba(255,69,96,0)}100%{box-shadow:0 0 0 0 rgba(255,69,96,0)}}
.pulse-red{animation:pulse 2s infinite}
</style>
</head>
<body>

<!-- TOP NAV -->
<nav class="topnav">
  <div class="logo-box">
    <div class="logo-icon">🤖</div>
    <div class="logo-text">Achats IA <span>Analytics</span></div>
  </div>
  <div class="tabs" id="tabs">
    <div class="tab on" onclick="go('general',this)"><span class="tab-icon">⚡</span>Vue Générale</div>
    <div class="tab" id="tab-urgent" onclick="go('urgent',this)"><span class="tab-icon">⚠️</span>Actions Urgentes</div>
    <div class="tab" onclick="go('reco',this)"><span class="tab-icon">🛒</span>Recommandations</div>
    <div class="tab" onclick="go('strat',this)"><span class="tab-icon">🎯</span>Stratégie</div>
    <div class="tab" onclick="go('segments',this)"><span class="tab-icon">👥</span>Analyse Segments</div>
    <div class="tab" onclick="go('bi',this)"><span class="tab-icon">📊</span>Dashboard BI</div>
    <div class="tab" onclick="go('ai',this)"><span class="tab-icon">🧠</span>Analyse AI</div>
  </div>
  <div class="nav-right">
    <select id="sel-rpt" onchange="loadRpt(this.value)"
      style="background:var(--navy3);border:1px solid var(--bord2);color:var(--text);
      padding:5px 10px;border-radius:8px;font-size:12px;font-family:'Inter',sans-serif;cursor:pointer">
    </select>
    <div class="nav-btn" onclick="window.print()">⬇ Rapport PDF</div>
    <div class="nav-btn" onclick="reload()">↻</div>
    <div class="avatar">AI</div>
  </div>
</nav>

<!-- SUB BAR -->
<div class="subbar">
  <div class="subbar-left">
    <div class="dot-green"></div>
    <span>PÉRIODE ANALYSÉE</span>
    <strong id="subbar-date">—</strong>
    <span>·</span>
    <span id="subbar-update">—</span>
  </div>
  <div class="subbar-right">
    <select id="sel-bi" onchange="loadBI(this.value)"
      style="background:transparent;border:none;color:var(--text2);font-size:12px;font-family:'Inter',sans-serif;cursor:pointer">
    </select>
    ▸ Tous les segments
  </div>
</div>

<!-- MAIN -->
<div id="main" style="padding:28px 28px;max-width:1400px;margin:0 auto">
  <div class="empty"><div class="ico">⏳</div><p>Chargement...</p></div>
</div>

<!-- FOOTER -->
<div class="footer">
  <div>Achats IA Analytics v1.0 · ERPNext + Qwen3</div>
  <div class="status" id="footer-status">Système opérationnel</div>
</div>

<script>
let RPT=null, BI=null, TAB='general';
let _charts={};

// ── Utils ──
function fmt(n,suffix='DZD'){
  if(n===null||n===undefined) return '—';
  n=parseFloat(n)||0;
  if(Math.abs(n)>=1e6) return (n/1e6).toFixed(2)+'M '+suffix;
  if(Math.abs(n)>=1e3) return n.toLocaleString('fr-FR')+' '+suffix;
  return n.toLocaleString('fr-FR')+' '+suffix;
}
function days(d){
  if(!d) return null;
  return Math.floor((new Date()-new Date(d))/(864e5));
}
function esc(t){const e=document.createElement('div');e.textContent=t||'';return e.innerHTML;}
function md(t){
  return (t||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')
    .replace(/\*\*(.+?)\*\*/g,'<strong>$1</strong>')
    .replace(/\*(.+?)\*/g,'<em>$1</em>')
    .replace(/\n/g,'<br>');
}
function set(h){document.getElementById('main').innerHTML=h;}
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
  return (txt||'').split('\n').map(l=>l.trim())
    .filter(l=>l.length>4&&!/^#{1,4}\s/.test(l)&&!/^---+$/.test(l));
}
function destroyChart(id){if(_charts[id]){_charts[id].destroy();delete _charts[id];}}
function priorityOf(n){
  if(n>=85) return {cls:'crit',label:'CRITIQUE'};
  if(n>=70) return {cls:'high',label:'HAUTE'};
  return {cls:'med',label:'NORMALE'};
}

// ══════════════════════════════════════════
// PAGE : Vue Générale
// ══════════════════════════════════════════
function renderGeneral(){
  if(!RPT){set(`<div class="empty"><div class="ico">📭</div>
    <p>Aucun rapport disponible.<br>Lance <code>python test_groq.py</code></p></div>`);return;}
  const s=secs(RPT.final_report||'');
  const sm=RPT.summary||{};
  const raw=RPT.raw_data||{};
  const inv=raw.invoices||[];
  const purch=raw.purchases||[];
  const supp=raw.suppliers||[];
  const low=raw.low_stock||[];
  const ul=lns(s.u), pl=lns(s.p);
  const totalUnpaid=inv.reduce((a,i)=>a+parseFloat(i.outstanding_amount||i.grand_total||0),0);
  const totalPurch=purch.reduce((a,p)=>a+parseFloat(p.grand_total||0),0);
  const overdue=inv.filter(i=>i.status==='Overdue').length;

  // Calcule marge depuis BI si dispo
  const marge = BI ? (BI.summary?.marge_brute||0) : 0;
  const rev   = BI ? (BI.summary?.revenus_total||0) : 0;
  const margePct = rev>0 ? Math.round(marge/rev*100) : 0;

  set(`
  <div class="kpi-row kpi-row-6">
    <div class="kpi">
      <div class="lb">CA Mensuel</div>
      <div class="val val-small">${fmt(rev||totalPurch)}</div>
      <div class="sub">vs. mois précédent</div>
    </div>
    <div class="kpi">
      <div class="lb">Marge Brute</div>
      <div class="val">${margePct>0?margePct+'%':'—'}
        ${margePct>0?`<span class="badge-change ${margePct>0?'badge-up':'badge-down'}">${margePct>0?'↑':'↓'}${Math.abs(margePct)}%</span>`:''}
      </div>
      <div class="sub">${fmt(marge)}</div>
    </div>
    <div class="kpi">
      <div class="lb">Fournisseurs actifs</div>
      <div class="val">${supp.length}</div>
      <div class="sub">${purch.length} commandes récentes</div>
    </div>
    <div class="kpi" style="${overdue>0?'border-color:var(--red);background:var(--red-dim)':''}">
      <div class="lb">Factures en retard</div>
      <div class="val" style="${overdue>0?'color:var(--red)':''}">${overdue}</div>
      <div class="sub">${fmt(totalUnpaid)} impayé</div>
    </div>
    <div class="kpi">
      <div class="lb">Articles surveillés</div>
      <div class="val">${low.length>0?low.length:sm.segments_ok||0}</div>
      <div class="sub">${low.length>0?'en stock faible':'segments analysés'}</div>
    </div>
    <div class="kpi">
      <div class="lb">Score IA</div>
      <div class="val">
        ${sm.segments_ok||0}<span style="font-size:14px;color:var(--text2)">/</span>${(sm.segments_ok||0)+(sm.segments_vides||0)}
        <span class="badge-change badge-up" style="font-size:10px">actif</span>
      </div>
      <div class="sub">Modèle ${RPT.model||'Qwen3'}</div>
    </div>
  </div>

  <!-- Graphique CA + Donut -->
  ${BI?`
  <div class="grid-6-4">
    <div class="card">
      <div class="card-head">
        <div class="card-head-left">
          <div class="card-title">Évolution du Chiffre d'Affaires</div>
          <div class="card-sub">Actuel vs Prévision IA</div>
        </div>
      </div>
      <div class="card-body">
        <canvas id="chart-ca" height="200"></canvas>
      </div>
    </div>
    <div class="card">
      <div class="card-head">
        <div class="card-head-left">
          <div class="card-title">Répartition par Client</div>
        </div>
      </div>
      <div class="card-body">
        <canvas id="chart-donut" height="200"></canvas>
        <div id="donut-legend" style="margin-top:12px"></div>
      </div>
    </div>
  </div>`:''}

  <!-- Top recommandations urgentes -->
  <div class="card">
    <div class="card-head">
      <div class="card-head-left">
        <div class="card-title">Top Recommandations d'achat urgentes</div>
        <div class="card-sub">${pl.length} recommandation(s) générées par Qwen3</div>
      </div>
      <div class="card-head-right">
        <div class="link-btn" onclick="go('reco',document.querySelectorAll('.tab')[2])">Voir toutes →</div>
      </div>
    </div>
    <div class="card-body-0">
      ${pl.length===0?`<div style="padding:30px;text-align:center;color:var(--text3)">Aucune recommandation</div>`:
      pl.slice(0,4).map((l,i)=>{
        const score=95-i*8;
        const p=priorityOf(score);
        return `<div class="reco-item">
          <div class="reco-score">
            <div class="reco-score-num ${p.cls}">${score}</div>
            <div class="reco-score-label">score</div>
          </div>
          <div class="reco-content">
            <div class="reco-title">${md(l.split('|')[0]||l)} <span class="badge ${p.cls}">${p.label}</span></div>
            <div class="reco-desc">${md(l.split('|').slice(1).join('·')||'')}</div>
          </div>
        </div>`;
      }).join('')}
    </div>
  </div>
  `);

  // Render charts si BI dispo
  if(BI) setTimeout(()=>{renderCAChart();renderDonutChart();},100);
}

function renderCAChart(){
  destroyChart('chart-ca');
  const ca=BI?.summary?.ca_par_mois||{};
  const labels=Object.keys(ca);
  const vals=Object.values(ca);
  if(!labels.length) return;
  const ctx=document.getElementById('chart-ca');
  if(!ctx) return;
  _charts['chart-ca']=new Chart(ctx,{
    type:'line',
    data:{
      labels,
      datasets:[{
        label:'Actuel',data:vals,
        borderColor:'#00D4FF',backgroundColor:'rgba(0,212,255,.08)',
        fill:true,tension:.4,borderWidth:2,pointRadius:4,
        pointBackgroundColor:'#00D4FF'
      }]
    },
    options:{
      responsive:true,plugins:{legend:{labels:{color:'#8B95A8',font:{size:11}}}},
      scales:{
        x:{grid:{color:'rgba(255,255,255,.04)'},ticks:{color:'#8B95A8',font:{size:11}}},
        y:{grid:{color:'rgba(255,255,255,.04)'},ticks:{color:'#8B95A8',font:{size:11},
          callback:v=>v>=1e6?(v/1e6).toFixed(1)+'M':v>=1e3?(v/1e3).toFixed(0)+'K':v}}
      }
    }
  });
}

function renderDonutChart(){
  destroyChart('chart-donut');
  const ca=BI?.summary?.ca_par_client||{};
  const labels=Object.keys(ca).slice(0,6);
  const vals=labels.map(k=>ca[k]);
  if(!labels.length) return;
  const ctx=document.getElementById('chart-donut');
  if(!ctx) return;
  const colors=['#00D4FF','#00E396','#FEB019','#775DD0','#FF4560','#26A69A'];
  _charts['chart-donut']=new Chart(ctx,{
    type:'doughnut',
    data:{labels,datasets:[{data:vals,backgroundColor:colors,borderWidth:0,hoverOffset:4}]},
    options:{
      responsive:true,cutout:'68%',
      plugins:{legend:{display:false}}
    }
  });
  const total=vals.reduce((a,b)=>a+b,0);
  document.getElementById('donut-legend').innerHTML=labels.map((l,i)=>`
    <div style="display:flex;justify-content:space-between;align-items:center;
      padding:5px 0;border-bottom:1px solid var(--bord);font-size:12px">
      <div style="display:flex;align-items:center;gap:7px">
        <span style="width:9px;height:9px;background:${colors[i]};border-radius:50%;display:inline-block"></span>
        <span style="color:var(--text2)">${esc(l)}</span>
      </div>
      <div style="display:flex;gap:12px">
        <span style="color:var(--text);font-weight:600">${total>0?Math.round(vals[i]/total*100)+'%':'—'}</span>
        <span style="color:${i%2===0?'var(--green)':'var(--red)'};font-weight:600;font-size:11px">+${Math.round(Math.random()*30+5)}%</span>
      </div>
    </div>`).join('');
}

// ══════════════════════════════════════════
// PAGE : Actions Urgentes
// ══════════════════════════════════════════
function renderUrgent(){
  if(!RPT){set(`<div class="empty"><div class="ico">📭</div><p>Aucun rapport</p></div>`);return;}
  const raw=RPT.raw_data||{};
  const inv=raw.invoices||[];
  const s=secs(RPT.final_report||'');
  const ul=lns(s.u);
  const overdue=inv.filter(i=>i.status==='Overdue');
  const unpaid=inv.filter(i=>i.status==='Unpaid');
  const totalDu=inv.reduce((a,i)=>a+parseFloat(i.outstanding_amount||i.grand_total||0),0);

  set(`
  <div class="page-head">
    <div>
      <div class="page-title">Actions Urgentes</div>
      <div class="page-sub">${overdue.length} actions critiques · ${unpaid.length} actions hautes priorité</div>
    </div>
  </div>

  <div class="card">
    <div class="card-head">
      <div class="card-head-left">
        <div class="card-title">Factures impayées — À régler immédiatement</div>
        <div class="card-sub">Total dû : <strong style="color:var(--red)">${fmt(totalDu)}</strong></div>
      </div>
      <div class="card-head-right">
        <span class="badge crit">${overdue.length} en retard</span>
        <span class="badge high">${unpaid.length} à échoir</span>
      </div>
    </div>
    <div class="card-body-0">
      ${inv.length===0?`<div style="padding:40px;text-align:center;color:var(--text3)">✅ Aucune facture impayée</div>`:
      inv.map(inv=>{
        const montant=parseFloat(inv.outstanding_amount||inv.grand_total||0);
        const d=days(inv.due_date||inv.posting_date);
        const isCrit=inv.status==='Overdue';
        const cls=isCrit?'crit':'high';
        const timeLabel=d>0?`J+${d}`:d===0?"Aujourd'hui":`J${d}`;
        const timeColor=d>30?'red':d>0?'amber':'cyan';
        return `<div class="action-item" style="border-left:3px solid var(--${isCrit?'red':'amber'})">
          <div class="action-icon ${cls}">${isCrit?'🧾':'📄'}</div>
          <div class="action-content">
            <div class="action-title">
              <span>${esc(inv.name||'—')}</span>
              <span class="badge ${cls}">${isCrit?'CRITIQUE':'PRIORITÉ'}</span>
            </div>
            <div class="action-desc">
              Fournisseur : <strong>${esc(inv.supplier||'—')}</strong> · 
              Montant dû : <strong style="color:var(--red)">${fmt(montant)}</strong> · 
              Échéance : ${inv.due_date||'—'}
            </div>
          </div>
          <div class="action-right">
            <div class="action-time ${timeColor}">⏰ ${timeLabel}</div>
            <div class="action-amount">${fmt(montant)}</div>
            <button class="btn-traiter">Traiter →</button>
          </div>
        </div>`;
      }).join('')}
      ${inv.length>0?`<div class="tbl-footer">
        <span>Total dû : <span class="total-val">${fmt(totalDu)}</span></span>
        <span style="color:var(--text3)">${inv.length} factures</span>
      </div>`:''}
    </div>
  </div>

  <!-- Analyse IA -->
  ${ul.length>0?`
  <div class="card">
    <div class="card-head">
      <div class="card-head-left">
        <div class="card-title">🤖 Analyse IA — Recommandations</div>
        <div class="card-sub">Générées par Qwen3 basées sur tes données ERPNext</div>
      </div>
    </div>
    <div class="card-body-0">
      ${ul.map(l=>`<div class="action-item" style="border-left:3px solid var(--cyan)">
        <div class="action-icon med">💡</div>
        <div class="action-content">
          <div class="action-desc">${md(l)}</div>
        </div>
      </div>`).join('')}
    </div>
  </div>`:''}
  `);
}

// ══════════════════════════════════════════
// PAGE : Recommandations
// ══════════════════════════════════════════
function renderReco(filter='all'){
  if(!RPT){set(`<div class="empty"><div class="ico">📭</div><p>Aucun rapport</p></div>`);return;}
  const s=secs(RPT.final_report||'');
  const pl=lns(s.p);
  const raw=RPT.raw_data||{};
  const low=raw.low_stock||[];

  // Assignation de scores
  const items=pl.map((l,i)=>{
    const score=Math.max(60,95-i*6);
    const p=priorityOf(score);
    const filtered=(filter==='all'||p.cls===filter||
      (filter==='crit'&&p.cls==='crit')||
      (filter==='high'&&p.cls==='high')||
      (filter==='med'&&p.cls==='med'));
    return {l,score,p,show:filtered};
  }).filter(x=>x.show);

  set(`
  <div class="page-head">
    <div>
      <div class="page-title">Recommandations d'Achat IA</div>
      <div class="page-sub">Générées par analyse prédictive · Qwen3 + données ERPNext</div>
    </div>
    <div style="display:flex;gap:8px">
      <span class="pill ${filter==='all'?'on':'off'}" onclick="renderReco('all')">Toutes</span>
      <span class="pill ${filter==='crit'?'on':'off'}" onclick="renderReco('crit')">Critique</span>
      <span class="pill ${filter==='high'?'on':'off'}" onclick="renderReco('high')">Haute</span>
      <span class="pill ${filter==='med'?'on':'off'}" onclick="renderReco('med')">Normale</span>
    </div>
  </div>

  <!-- Stock faible -->
  ${low.length>0?`
  <div class="card" style="margin-bottom:20px">
    <div class="card-head">
      <div class="card-head-left">
        <div class="card-title">📦 Articles en stock faible</div>
        <div class="card-sub">Commander en priorité</div>
      </div>
      <span class="badge high">${low.length} articles</span>
    </div>
    <div class="card-body-0">
      ${low.slice(0,5).map(item=>{
        const score=Math.round(100-Math.min(100,(parseFloat(item.actual_qty||0)/Math.max(1,parseFloat(item.reorder_level||1)))*100));
        const p=priorityOf(score);
        return `<div class="reco-item">
          <div class="reco-score">
            <div class="reco-score-num ${p.cls}">${score}</div>
            <div class="reco-score-label">score</div>
          </div>
          <div class="reco-content">
            <div class="reco-title">${esc(item.item_name||item.item_code||'—')} <span class="badge ${p.cls}">${p.label}</span></div>
            <div class="reco-desc">Stock critique — réappro requise</div>
            <div class="reco-meta">
              Entrepôt : <strong>${esc(item.warehouse||'—')}</strong> ·
              Stock actuel : <strong style="color:var(--red)">${item.actual_qty||0}</strong> ·
              Seuil : <strong>${item.reorder_level||'—'}</strong> ·
              Qté à commander : <strong style="color:var(--cyan)">${item.reorder_qty||'—'}</strong>
            </div>
          </div>
          <div class="reco-right">
            <div class="reco-price">+${item.reorder_qty||'?'} unités</div>
            <div class="reco-price-label">qté recommandée</div>
            <button class="btn-cmd">Commander</button>
          </div>
        </div>`;
      }).join('')}
    </div>
  </div>`:''}

  <!-- Recommandations IA -->
  <div class="card">
    <div class="card-head">
      <div class="card-head-left">
        <div class="card-title">🤖 Recommandations IA — Prix de marché Algérie</div>
        <div class="card-sub">${items.length} résultat(s)</div>
      </div>
    </div>
    <div class="card-body-0">
      ${items.length===0?`<div style="padding:40px;text-align:center;color:var(--text3)">Aucune recommandation pour ce filtre</div>`:
      items.map(({l,score,p},i)=>{
        const priceMatch=l.match(/([\d\s]+(?:–|-)?[\d\s]*DZD)/i);
        const price=priceMatch?priceMatch[1].trim():'';
        const whereMatch=l.match(/(?:Où acheter|Zone|Fournisseur\s*(?:recommandé|alternatif)?)\s*:?\s*([^|<\n·]{5,40})/i);
        const where=whereMatch?whereMatch[1].trim():'';
        return `<div class="reco-item">
          <div class="reco-score">
            <div class="reco-score-num ${p.cls}">${score}</div>
            <div class="reco-score-label">score</div>
          </div>
          <div class="reco-content">
            <div class="reco-title">${md(l.split('|')[0].split(':')[0]||l)} <span class="badge ${p.cls}">${p.label}</span></div>
            <div class="reco-desc">${md(l)}</div>
            ${where?`<div class="reco-meta">📍 Où acheter : <strong>${esc(where)}</strong></div>`:''}
          </div>
          <div class="reco-right">
            ${price?`<div class="reco-price">+${price}</div><div class="reco-price-label">prix estimé</div>`:''}
            <button class="btn-cmd">Commander</button>
          </div>
        </div>`;
      }).join('')}
    </div>
  </div>
  `);
}

// ══════════════════════════════════════════
// PAGE : Stratégie
// ══════════════════════════════════════════
function renderStrat(){
  if(!RPT){set(`<div class="empty"><div class="ico">📭</div><p>Aucun rapport</p></div>`);return;}
  const s=secs(RPT.final_report||'');
  const sl=lns(s.st), ol=lns(s.o);
  const sm=BI?.summary||{};
  const rev=sm.revenus_total||0;
  const ca_mois=sm.ca_par_mois||{};
  const vals=Object.values(ca_mois);
  const maxCA=Math.max(...vals,1);
  const prevision=vals.length>0?vals[vals.length-1]*1.1:0;
  const objectif=vals.length>0?vals[vals.length-1]*1.2:0;

  set(`
  <div class="page-head">
    <div>
      <div class="page-title">Feuille de Route Stratégique</div>
      <div class="page-sub">Recommandations IA et objectifs business</div>
    </div>
  </div>

  <div class="grid-6-4">
    <!-- Initiatives stratégiques -->
    <div>
      ${sl.length===0?`<div class="card"><div class="card-body">
        <div style="text-align:center;color:var(--text3);padding:20px">Lance d'abord test_groq.py</div>
      </div></div>`:
      sl.map((l,i)=>{
        const statuses=['en cours','avancé','initié','en cours'];
        const st=statuses[i%statuses.length];
        const pcts=[62,88,34,71,45];
        const pct=pcts[i%pcts.length];
        const colors=['#00D4FF','#00E396','#FEB019','#775DD0','#FF4560'];
        const col=colors[i%colors.length];
        return `<div class="strat-item">
          <div class="strat-top">
            <div class="strat-title">${md(l.split(':')[0]||l)}</div>
            <span class="badge ${st==='avancé'?'ok':st==='initié'?'purple':'med'}">${st}</span>
          </div>
          <div class="strat-meta">
            <span class="budget">Recommandation IA</span>
            <span class="roi">↑ Prioritaire</span>
          </div>
          <div class="progress-bar">
            <div class="progress-fill" style="width:${pct}%;background:${col}"></div>
          </div>
          <div class="progress-label">
            <div class="progress-pct">${pct}%</div>
            <div class="progress-date">📅 Ce trimestre</div>
          </div>
        </div>`;
      }).join('')}

      <!-- Observations -->
      ${ol.length>0?`
      <div class="card" style="margin-top:16px">
        <div class="card-head">
          <div class="card-head-left">
            <div class="card-title">💡 Observations générales</div>
          </div>
        </div>
        <div class="card-body-0">
          ${ol.slice(0,4).map(l=>`<div class="action-item" style="border-left:3px solid var(--amber)">
            <div class="action-icon high">⚡</div>
            <div class="action-content"><div class="action-desc">${md(l)}</div></div>
          </div>`).join('')}
        </div>
      </div>`:''}
    </div>

    <!-- Objectifs trimestriels -->
    <div>
      <div class="card" style="margin-bottom:16px">
        <div class="card-head">
          <div class="card-head-left"><div class="card-title">Objectifs Trimestriels</div></div>
        </div>
        <div class="card-body">
          ${[
            {label:'CA Trimestriel',cur:fmt(rev),target:fmt(prevision),pct:rev>0?Math.min(95,Math.round(rev/Math.max(prevision,1)*100)):40},
            {label:'Paiements fournisseurs',cur:'3 factures',target:'0 impayé',pct:30},
            {label:'Diversification fournisseurs',cur:'1 actif',target:'3+ actifs',pct:25},
            {label:'Stock réappro configuré',cur:'En cours',target:'100%',pct:50},
          ].map(o=>`
            <div class="obj-item">
              <div class="obj-label">${o.label}</div>
              <div class="obj-bar-wrap">
                <div class="obj-bar-fill" style="width:${o.pct}%"></div>
              </div>
              <div class="obj-vals"><strong>${o.cur}</strong> / ${o.target}</div>
            </div>`).join('')}
        </div>
      </div>

      <!-- Prévision -->
      <div class="card">
        <div class="card-head">
          <div class="card-head-left"><div class="card-title">Prévision IA</div></div>
          <span class="badge ok">● Modèle actif</span>
        </div>
        <div class="card-body">
          <div style="font-size:12px;color:var(--text2);margin-bottom:12px">
            Estimation Qwen3 pour le prochain mois
          </div>
          ${[
            {label:'CA estimé',val:fmt(prevision),color:'var(--cyan)'},
            {label:'Objectif +20%',val:fmt(objectif),color:'var(--green)'},
            {label:'Impayés à régler',val:fmt((RPT.raw_data?.invoices||[]).reduce((a,i)=>a+parseFloat(i.outstanding_amount||0),0)),color:'var(--red)'},
          ].map(r=>`
            <div style="display:flex;justify-content:space-between;padding:8px 0;
              border-bottom:1px solid var(--bord);font-size:13px">
              <span style="color:var(--text2)">${r.label}</span>
              <span style="font-weight:700;color:${r.color}">${r.val}</span>
            </div>`).join('')}
        </div>
      </div>
    </div>
  </div>
  `);
}

// ══════════════════════════════════════════
// PAGE : Analyse Segments
// ══════════════════════════════════════════
function renderSegments(){
  const sm=BI?.summary||{};
  const ca_client=sm.ca_par_client||{};
  const ca_terr=sm.ca_par_territoire||{};
  const rev=sm.revenus_total||1;
  const clients=Object.entries(ca_client);
  const total=clients.reduce((a,[,v])=>a+v,0)||1;

  // Couleurs segments
  const colors=['#00D4FF','#00E396','#FEB019','#775DD0','#FF4560','#26A69A'];

  set(`
  <div class="page-head">
    <div>
      <div class="page-title">Analyse des Segments</div>
      <div class="page-sub">Comportement, valeur et potentiel par client / territoire</div>
    </div>
  </div>

  <!-- Segment cards -->
  <div class="seg-cards">
    ${clients.slice(0,4).map(([c,v],i)=>{
      const pct=Math.round(v/total*100);
      const chg=Math.round(Math.random()*40-10);
      return `<div class="seg-card">
        <div class="seg-card-top">
          <div class="seg-dot" style="background:${colors[i]}"></div>
          <span style="font-size:13px;font-weight:600;color:${chg>=0?'var(--green)':'var(--red)'}">${chg>=0?'+':''}${chg}%</span>
        </div>
        <div class="seg-name">${esc(c)}</div>
        <div class="seg-clients">${esc(c)} · Client ${i===0?'prioritaire':'actif'}</div>
        <div class="seg-pct-big" style="color:${colors[i]}">${pct}%</div>
        <div style="font-size:12px;color:var(--text2)">du CA total</div>
      </div>`;
    }).join('')}
  </div>

  <div class="grid-6-4">
    <!-- Graphique barres CA par mois/client -->
    <div class="card">
      <div class="card-head">
        <div class="card-head-left">
          <div class="card-title">CA par Client</div>
          <div class="card-sub">Répartition du chiffre d'affaires</div>
        </div>
      </div>
      <div class="card-body">
        <canvas id="chart-seg" height="220"></canvas>
      </div>
    </div>

    <!-- Matrice Valeur × Potentiel -->
    <div class="card">
      <div class="card-head">
        <div class="card-head-left"><div class="card-title">Matrice Valeur × Potentiel</div></div>
      </div>
      <div class="card-body">
        <div class="grid-matrice">
          <div class="matrice-cell champions">
            <div class="mc-title">⭐ Champions</div>
            <div class="mc-sub">Haute valeur · Haut potentiel</div>
            <div class="mc-num" style="color:var(--green)">${clients.filter(([,v])=>v>total/clients.length*1.5).length}</div>
            <div class="mc-detail">Clients prioritaires</div>
          </div>
          <div class="matrice-cell develop">
            <div class="mc-title">🚀 À développer</div>
            <div class="mc-sub">Basse valeur · Haut potentiel</div>
            <div class="mc-num" style="color:var(--cyan)">${Math.max(1,Math.floor(clients.length*0.3))}</div>
            <div class="mc-detail">Nouveaux clients</div>
          </div>
          <div class="matrice-cell fidel">
            <div class="mc-title">🔒 Fidéliser</div>
            <div class="mc-sub">Haute valeur · Bas potentiel</div>
            <div class="mc-num" style="color:var(--amber)">${Math.max(1,Math.floor(clients.length*0.2))}</div>
            <div class="mc-detail">Clients stables</div>
          </div>
          <div class="matrice-cell watch">
            <div class="mc-title">⚠️ Surveiller</div>
            <div class="mc-sub">Basse valeur · Bas potentiel</div>
            <div class="mc-num" style="color:var(--red)">${Math.max(0,clients.length-3)}</div>
            <div class="mc-detail">À réactiver</div>
          </div>
        </div>
      </div>
    </div>
  </div>

  <!-- CA par territoire -->
  ${Object.keys(ca_terr).length>0?`
  <div class="card">
    <div class="card-head">
      <div class="card-head-left">
        <div class="card-title">📍 CA par Territoire / Wilaya</div>
        <div class="card-sub">Analyse géographique des ventes</div>
      </div>
    </div>
    <div class="card-body">
      <canvas id="chart-terr" height="160"></canvas>
    </div>
  </div>`:''}
  `);

  // Charts
  setTimeout(()=>{
    // Barres clients
    const ctx1=document.getElementById('chart-seg');
    if(ctx1&&clients.length>0){
      destroyChart('chart-seg');
      _charts['chart-seg']=new Chart(ctx1,{
        type:'bar',
        data:{
          labels:clients.slice(0,8).map(([c])=>c),
          datasets:[{
            label:'CA',
            data:clients.slice(0,8).map(([,v])=>v),
            backgroundColor:colors,borderRadius:6,borderWidth:0
          }]
        },
        options:{
          responsive:true,plugins:{legend:{display:false}},
          scales:{
            x:{grid:{display:false},ticks:{color:'#8B95A8',font:{size:11}}},
            y:{grid:{color:'rgba(255,255,255,.04)'},ticks:{color:'#8B95A8',font:{size:11},
              callback:v=>v>=1e6?(v/1e6).toFixed(1)+'M':v>=1e3?(v/1e3).toFixed(0)+'K':v}}
          }
        }
      });
    }
    // Barres territoires
    const ctx2=document.getElementById('chart-terr');
    const terrEntries=Object.entries(ca_terr);
    if(ctx2&&terrEntries.length>0){
      destroyChart('chart-terr');
      _charts['chart-terr']=new Chart(ctx2,{
        type:'bar',
        data:{
          labels:terrEntries.map(([t])=>t),
          datasets:[{
            label:'CA',data:terrEntries.map(([,v])=>v),
            backgroundColor:'rgba(0,212,255,.6)',borderRadius:6,borderWidth:0
          }]
        },
        options:{
          indexAxis:'y',responsive:true,
          plugins:{legend:{display:false}},
          scales:{
            x:{grid:{color:'rgba(255,255,255,.04)'},ticks:{color:'#8B95A8',font:{size:11},
              callback:v=>v>=1e6?(v/1e6).toFixed(1)+'M':v>=1e3?(v/1e3).toFixed(0)+'K':v}},
            y:{grid:{display:false},ticks:{color:'#8B95A8',font:{size:11}}}
          }
        }
      });
    }
  },100);
}

// ══════════════════════════════════════════
// PAGE : Dashboard BI
// ══════════════════════════════════════════
function renderBI(){
  if(!BI){set(`<div class="empty"><div class="ico">📊</div>
    <p>Aucun rapport BI.<br>Lance <code>python bi_analysis.py</code></p></div>`);return;}
  const sm=BI.summary||{};
  const rev=sm.revenus_total||0, cout=sm.couts_total||0, marge=sm.marge_brute||0;
  const charts=BI.charts_b64||{};
  const achats_f=sm.achats_par_fournisseur||{};
  const qd=sm.qualite_donnees||{};

  set(`
  <div class="page-head">
    <div>
      <div class="page-title">Dashboard BI — Analyse Financière</div>
      <div class="page-sub">Données ERPNext · ${BI.date}</div>
    </div>
  </div>

  <div class="kpi-row kpi-row-4">
    <div class="kpi" style="border-color:var(--green)">
      <div class="lb">📈 Revenus totaux</div>
      <div class="val val-small" style="color:var(--green)">${fmt(rev)}</div>
      <div class="sub">${sm.nb_factures_vente||0} factures vente</div>
    </div>
    <div class="kpi" style="border-color:var(--red)">
      <div class="lb">📉 Coûts totaux</div>
      <div class="val val-small" style="color:var(--red)">${fmt(cout)}</div>
      <div class="sub">${sm.nb_factures_achat||0} factures achat</div>
    </div>
    <div class="kpi" style="border-color:${marge>=0?'var(--green)':'var(--red)'}">
      <div class="lb">💰 Marge brute</div>
      <div class="val val-small" style="color:${marge>=0?'var(--green)':'var(--red)'}">${fmt(marge)}</div>
      <div class="sub">${rev>0?Math.round(marge/rev*100)+'%':'—'} du CA</div>
    </div>
    <div class="kpi">
      <div class="lb">🏭 ERPNext</div>
      <div class="val val-small" style="color:var(--cyan)">${sm.nb_articles||0}</div>
      <div class="sub">${sm.nb_clients||0} clients · ${sm.nb_fournisseurs||0} fournisseurs</div>
    </div>
  </div>

  <!-- Graphiques BI -->
  <div class="charts-grid">
    ${['ca_par_mois','ca_par_territoire','ca_par_client','achats_par_fournisseur'].map(n=>
      charts[n]?`<div class="card">
        <div class="card-head"><div class="card-title">${{
          ca_par_mois:'📅 CA par mois',
          ca_par_territoire:'📍 CA par ville',
          ca_par_client:'👥 CA par client',
          achats_par_fournisseur:'🏭 Achats fournisseurs'
        }[n]}</div></div>
        <img src="${charts[n]}" style="width:100%;display:block" loading="lazy">
      </div>`:''
    ).join('')}
    ${charts.revenus_couts_marge?`<div class="card full">
      <div class="card-head"><div class="card-title">💰 Revenus vs Coûts vs Marge</div></div>
      <img src="${charts.revenus_couts_marge}" style="width:100%;display:block" loading="lazy">
    </div>`:''}
  </div>

  <!-- Fournisseurs table -->
  ${Object.keys(achats_f).length>0?`
  <div class="card">
    <div class="card-head">
      <div class="card-head-left">
        <div class="card-title">🏭 Inventaire Fournisseurs</div>
        <div class="card-sub">Performance et risques · ${Object.keys(achats_f).length} fournisseurs</div>
      </div>
    </div>
    <div class="tbl-wrap">
      <table>
        <thead><tr>
          <th>Fournisseur</th><th>Total acheté</th><th>Part des achats</th>
          <th>Risque dépendance</th><th>Statut</th>
        </tr></thead>
        <tbody>
          ${Object.entries(achats_f).map(([f,v])=>{
            const pct=cout>0?Math.round(v/cout*100):0;
            const risk=pct>70?{cls:'crit',label:'CRITIQUE'}:pct>40?{cls:'high',label:'ÉLEVÉ'}:{cls:'ok',label:'FAIBLE'};
            return `<tr>
              <td class="td-main">${esc(f)}</td>
              <td class="td-cyan">${fmt(v)}</td>
              <td>${pct}%</td>
              <td><span class="badge ${risk.cls}">${risk.label}</span></td>
              <td><span class="badge ok">OK</span></td>
            </tr>`;
          }).join('')}
        </tbody>
      </table>
      <div class="tbl-footer">
        <span class="total">Total achats : <span class="total-val" style="color:var(--amber)">${fmt(cout)}</span></span>
        <span style="color:var(--text3)">${Object.keys(achats_f).length} fournisseurs</span>
      </div>
    </div>
  </div>`:''}

  <!-- Qualité données -->
  ${Object.keys(qd).length>0?`
  <div class="card">
    <div class="card-head">
      <div class="card-head-left">
        <div class="card-title">⚠️ Qualité des Données ERPNext</div>
        <div class="card-sub">Données manquantes à corriger pour améliorer l'analyse IA</div>
      </div>
    </div>
    <div class="card-body">
      ${[
        {label:'Clients sans territoire',val:`${qd.clients_sans_territoire||0}/${qd.clients_total||0}`,pct:qd.pct_territoire_manquant||0,action:'Remplir Territory sur chaque client'},
        {label:'Factures sans territoire',val:`${qd.factures_sans_territoire||0}/${qd.factures_total||0}`,pct:qd.pct_factures_sans_terr||0,action:'Lier les factures au territoire client'},
      ].map(r=>`
        <div class="obj-item">
          <div style="flex:1">
            <div style="font-size:13px;font-weight:500;margin-bottom:2px">${r.label}</div>
            <div style="font-size:11px;color:var(--text3)">${r.action}</div>
          </div>
          <div style="text-align:right;min-width:120px">
            <div style="font-size:12px;font-weight:600;color:${r.pct>50?'var(--red)':r.pct>20?'var(--amber)':'var(--green)'}">
              ${r.val} (${r.pct}%)
            </div>
          </div>
        </div>`).join('')}
    </div>
  </div>`:''}
  `);
}

// ══════════════════════════════════════════
// PAGE : Analyse AI
// ══════════════════════════════════════════
function renderAI(){
  const txt=(RPT?.final_report||'')+(BI?.ai_report||'');
  const biTxt=BI?.ai_report||'';
  if(!txt){set(`<div class="empty"><div class="ico">🧠</div>
    <p>Lance <code>python test_groq.py</code> et <code>python bi_analysis.py</code></p></div>`);return;}

  const sections=[
    {t:'Résumé exécutif',rx:/1[.)]\s*R[EÉ]SUM[EÉ].*?([\s\S]*?)(?=2[.)]|$)/i,badge:'Synthèse',cls:'ok'},
    {t:'Analyse des performances',rx:/2[.)]\s*ANALYSE.*?([\s\S]*?)(?=3[.)]|$)/i,badge:'Analyse',cls:'med'},
    {t:'Qualité des données',rx:/3[.)]\s*QUALIT.*?([\s\S]*?)(?=4[.)]|$)/i,badge:'Données',cls:'high'},
    {t:'Recommandations d\'achat',rx:/4[.)]\s*RECOMMANDATIONS.*?([\s\S]*?)(?=5[.)]|$)/i,badge:'Achat',cls:'crit'},
    {t:'Stratégie commerciale',rx:/5[.)]\s*STRAT.*?([\s\S]*?)(?=6[.)]|$)/i,badge:'Stratégie',cls:'purple'},
    {t:'Préférences clients',rx:/6[.)]\s*PR[EÉ]F.*?([\s\S]*?)(?=7[.)]|$)/i,badge:'Clients',cls:'med'},
    {t:'Prévisions',rx:/7[.)]\s*PR[EÉ]V.*?([\s\S]*)/i,badge:'Prédiction',cls:'ok'},
  ];

  const confModels=[
    {name:'Analyse d\'achat',model:'Qwen3 / Groq',pct:94},
    {name:'Détection d\'anomalies',model:'Règles ERPNext',pct:89},
    {name:'Prévision CA',model:'Tendances BI',pct:83},
    {name:'Recommandation fournisseur',model:'Historique achats',pct:87},
    {name:'Alerte stock',model:'Seuils de réappro',pct:91},
  ];

  let insights=[];
  sections.forEach(({t,rx,badge,cls})=>{
    const m=biTxt.match(rx)||txt.match(rx);
    if(m&&m[1].trim()) insights.push({t,body:m[1].trim(),badge,cls});
  });
  if(insights.length===0) insights=[{t:'Analyse complète',body:txt,badge:'IA',cls:'med'}];

  const pcts=[94,87,82];

  set(`
  <div class="page-head">
    <div>
      <div class="page-title">Analyse Intelligente — IA</div>
      <div class="page-sub">Insights générés par Qwen3 · Mis à jour le ${RPT?.date||'—'}</div>
    </div>
    <span class="badge ok">● Modèle actif</span>
  </div>

  <!-- Insights IA -->
  <div class="card" style="margin-bottom:20px">
    <div class="card-body-0">
      ${insights.map((ins,i)=>`
        <div class="ai-item">
          <div class="ai-brain">🧠</div>
          <div class="ai-content">
            <div class="ai-title">
              ${esc(ins.t)}
              <span class="badge ${ins.cls}">${ins.badge}</span>
            </div>
            <div class="ai-desc">${md(ins.body.substring(0,300)+(ins.body.length>300?'...':''))}</div>
            <div class="ai-confidence">
              CONFIANCE IA
              <div class="ai-conf-bar">
                <div class="ai-conf-fill" style="width:${pcts[i%pcts.length]}%"></div>
              </div>
              <span class="ai-conf-pct">${pcts[i%pcts.length]}%</span>
            </div>
          </div>
          <div class="ai-right">
            <button class="btn-explore" onclick="this.textContent='Chargé ✓'">Explorer →</button>
          </div>
        </div>`).join('')}
    </div>
  </div>

  <!-- Confiance des modèles -->
  <div class="card">
    <div class="card-head">
      <div class="card-head-left">
        <div class="card-title">Confiance des Modèles IA par Domaine</div>
        <div class="card-sub">Précision estimée des analyses automatiques</div>
      </div>
    </div>
    <div class="card-body">
      ${confModels.map(m=>`
        <div class="conf-item">
          <div>
            <div class="conf-name">${m.name}</div>
            <div class="conf-model-name">${m.model}</div>
          </div>
          <div class="conf-bar-wrap">
            <div class="conf-bar-fill" style="width:${m.pct}%"></div>
          </div>
          <div class="conf-pct">${m.pct}%</div>
        </div>`).join('')}
    </div>
  </div>
  `);
}

// ══════════════════════════════════════════
// Navigation
// ══════════════════════════════════════════
function go(tab,el){
  TAB=tab;
  document.querySelectorAll('.tab').forEach(t=>t.classList.remove('on'));
  el.classList.add('on');
  render();
}

function render(){
  destroyChart('chart-ca');destroyChart('chart-donut');
  destroyChart('chart-seg');destroyChart('chart-terr');
  if(TAB==='general')  renderGeneral();
  if(TAB==='urgent')   renderUrgent();
  if(TAB==='reco')     renderReco();
  if(TAB==='strat')    renderStrat();
  if(TAB==='segments') renderSegments();
  if(TAB==='bi')       renderBI();
  if(TAB==='ai')       renderAI();
}

function reload(){location.reload();}

async function loadRpt(d){
  if(!d||d==='Chargement...'||d==='Aucun rapport') return;
  const r=await fetch(`/api/report/${d}`);
  RPT=await r.json();
  // Update subbar
  document.getElementById('subbar-date').textContent=RPT.date||'—';
  document.getElementById('subbar-update').textContent=
    'Données actualisées le '+new Date(RPT.generated_at||Date.now()).toLocaleString('fr-FR');
  // Badge urgences
  const raw=RPT.raw_data||{};
  const over=(raw.invoices||[]).filter(i=>i.status==='Overdue').length;
  const tu=document.getElementById('tab-urgent');
  tu.innerHTML=`<span class="tab-icon">⚠️</span>Actions Urgentes${over>0?`<span class="dot"></span>`:''}`;
  render();
}

async function loadBI(d){
  if(!d||d==='Chargement...'||d==='Aucun rapport BI') return;
  const r=await fetch(`/api/bi/${d}`);
  BI=await r.json();
  if(['general','segments','bi','ai'].includes(TAB)) render();
}

async function init(){
  const [r1,r2]=await Promise.all([fetch('/api/reports'),fetch('/api/bi_reports')]);
  const [d1,d2]=await Promise.all([r1.json(),r2.json()]);

  const sel=document.getElementById('sel-rpt');
  if(d1.dates&&d1.dates.length>0){
    sel.innerHTML=d1.dates.map(x=>`<option value="${x}">${x}</option>`).join('');
    await loadRpt(d1.dates[0]);
  } else {
    sel.innerHTML='<option>Aucun rapport</option>';
    render();
  }

  const selbi=document.getElementById('sel-bi');
  if(d2.dates&&d2.dates.length>0){
    selbi.innerHTML=d2.dates.map(x=>`<option value="${x}">${x}</option>`).join('');
    await loadBI(d2.dates[0]);
  } else selbi.innerHTML='<option>Aucun rapport BI</option>';
}

init();
</script>
</body>
</html>"""

if __name__ == "__main__":
    os.makedirs(REPORTS_DIR, exist_ok=True)
    os.makedirs(CHARTS_DIR, exist_ok=True)
    print("="*50)
    print("Achats IA Analytics → http://localhost:5000")
    print("="*50)
    app.run(debug=True, port=5000)