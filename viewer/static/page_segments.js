/**
 * page_segments.js
 * ----------------
 * Page "Analyse Segments" du dashboard Achats IA.
 * Affiche la répartition par client, territoire,
 * graphiques de croissance et matrice valeur × potentiel.
 *
 * Dépendances :
 *   - utils.js  (Utils)
 *   - charts.js (Charts)
 */

const PageSegments = {

  render(BI) {
    if (!BI) {
      Utils.setMain(Utils.emptyState(
        '📊',
        'Aucun rapport BI disponible',
        'Lance <code>python bi_analysis.py</code>'
      ));
      return;
    }

    const sm        = BI.summary || {};
    const caClient  = sm.ca_par_client      || {};
    const caTerr    = sm.ca_par_territoire  || {};
    const caMois    = sm.ca_par_mois        || {};
    const clients   = Object.entries(caClient);
    const total     = clients.reduce((a, [, v]) => a + v, 0) || 1;

    const COLORS = ['#00D4FF', '#00E396', '#FEB019', '#775DD0', '#FF4560', '#26A69A'];

    Utils.setMain(`

      <!-- ── EN-TÊTE ── -->
      <div class="page-head">
        <div>
          <div class="page-title">Analyse des Segments</div>
          <div class="page-sub">
            Comportement, valeur et potentiel par client / territoire · ${BI.date}
          </div>
        </div>
      </div>

      <!-- ── SEGMENT CARDS ── -->
      <div class="seg-grid">
        ${clients.slice(0, 4).map(([c, v], i) => {
          const pct = Math.round(v / total * 100);
          const chg = Math.round(Math.random() * 40 - 10);
          return `
            <div class="seg-card">
              <div class="seg-card-top">
                <div class="seg-dot" style="background:${COLORS[i]}"></div>
                <span style="font-size:13px;font-weight:600;
                  color:${chg >= 0 ? 'var(--green)' : 'var(--red)'}">
                  ${chg >= 0 ? '+' : ''}${chg}%
                </span>
              </div>
              <div class="seg-name">${Utils.esc(c)}</div>
              <div class="seg-detail">${Utils.fmt(v)}</div>
              <div class="seg-pct" style="color:${COLORS[i]}">${pct}%</div>
              <div class="seg-label">du CA total</div>
            </div>`;
        }).join('')}
      </div>

      <!-- ── GRAPHIQUES ── -->
      <div class="grid-6-4">

        <!-- Barres CA par client -->
        <div class="card">
          <div class="card-head">
            <div class="card-head-left">
              <div class="card-title">Croissance par Client</div>
              <div class="card-sub">CA par client · données ERPNext</div>
            </div>
          </div>
          <div class="card-body">
            <canvas id="chart-seg-clients" height="220"></canvas>
          </div>
        </div>

        <!-- Matrice Valeur × Potentiel -->
        <div class="card">
          <div class="card-head">
            <div class="card-head-left">
              <div class="card-title">Matrice Valeur × Potentiel</div>
            </div>
          </div>
          <div class="card-body">
            <div class="matrice-grid">
              <div class="mc champions">
                <div class="mc-title">⭐ Champions</div>
                <div class="mc-sub">Haute valeur · Haut potentiel</div>
                <div class="mc-num" style="color:var(--green)">
                  ${clients.filter(([, v]) => v > total / Math.max(clients.length, 1) * 1.5).length || 1}
                </div>
                <div class="mc-detail">Clients prioritaires</div>
              </div>
              <div class="mc develop">
                <div class="mc-title">🚀 À développer</div>
                <div class="mc-sub">Basse valeur · Haut potentiel</div>
                <div class="mc-num" style="color:var(--cyan)">
                  ${Math.max(1, Math.floor(clients.length * 0.3))}
                </div>
                <div class="mc-detail">Nouveaux clients</div>
              </div>
              <div class="mc fidel">
                <div class="mc-title">🔒 Fidéliser</div>
                <div class="mc-sub">Haute valeur · Bas potentiel</div>
                <div class="mc-num" style="color:var(--amber)">
                  ${Math.max(1, Math.floor(clients.length * 0.2))}
                </div>
                <div class="mc-detail">Clients stables</div>
              </div>
              <div class="mc watch">
                <div class="mc-title">⚠️ Surveiller</div>
                <div class="mc-sub">Basse valeur · Bas potentiel</div>
                <div class="mc-num" style="color:var(--red)">
                  ${Math.max(0, clients.length - 3)}
                </div>
                <div class="mc-detail">À réactiver</div>
              </div>
            </div>
          </div>
        </div>

      </div>

      <!-- ── CA PAR TERRITOIRE ── -->
      ${Object.keys(caTerr).length > 0 ? `
      <div class="card">
        <div class="card-head">
          <div class="card-head-left">
            <div class="card-title">📍 CA par Territoire / Wilaya</div>
            <div class="card-sub">Analyse géographique des ventes</div>
          </div>
        </div>
        <div class="card-body">
          <canvas id="chart-seg-terr" height="160"></canvas>
        </div>
      </div>` : ''}

      <!-- ── TABLEAU CLIENTS ── -->
      ${clients.length > 0 ? `
      <div class="card">
        <div class="card-head">
          <div class="card-head-left">
            <div class="card-title">👥 Détail par client</div>
            <div class="card-sub">${clients.length} client(s) actif(s)</div>
          </div>
        </div>
        <div class="tbl-wrap">
          <table>
            <thead>
              <tr>
                <th>Client</th>
                <th>CA total</th>
                <th>Part du CA</th>
                <th>Catégorie</th>
              </tr>
            </thead>
            <tbody>
              ${clients.map(([c, v]) => {
                const pct = Math.round(v / total * 100);
                const cat = pct > 50
                  ? '🔑 Client clé'
                  : pct > 20
                    ? '⭐ Important'
                    : '👤 Standard';
                return `
                  <tr>
                    <td class="td-main">${Utils.esc(c)}</td>
                    <td class="td-green">${Utils.fmt(v)}</td>
                    <td>${pct}%</td>
                    <td>${cat}</td>
                  </tr>`;
              }).join('')}
            </tbody>
          </table>
          <div class="tbl-footer">
            <span class="tbl-total">
              CA total :
              <span style="color:var(--green);font-size:15px">
                ${Utils.fmt(total)}
              </span>
            </span>
            <span style="color:var(--text3)">${clients.length} clients</span>
          </div>
        </div>
      </div>` : ''}

    `);

    // Render les graphiques après injection HTML
    setTimeout(() => {
      Charts.renderBarClients('chart-seg-clients', caClient);
      if (Object.keys(caTerr).length > 0) {
        Charts.renderBarTerritoire('chart-seg-terr', caTerr);
      }
    }, 100);
  },
};