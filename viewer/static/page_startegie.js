/**
 * page_strat.js
 * -------------
 * Page "Stratégie" du dashboard Achats IA.
 * Affiche la feuille de route stratégique, le radar de performance,
 * les objectifs trimestriels et les observations IA.
 *
 * Dépendances :
 *   - utils.js  (Utils)
 *   - charts.js (Charts)
 */

const PageStrat = {

  render(RPT, BI) {
    if (!RPT) {
      Utils.setMain(Utils.emptyState(
        '📭',
        'Aucun rapport disponible',
        'Lance <code>python test_groq.py</code>'
      ));
      return;
    }

    const s  = Utils.parseSections(RPT.final_report || '');
    const sl = Utils.toLines(s.st);
    const ol = Utils.toLines(s.o);
    const sm = BI?.summary || {};

    const rev      = sm.revenus_total || 0;
    const cout     = sm.couts_total   || 0;
    const marge    = sm.marge_brute   || 0;
    const inv      = RPT.raw_data?.invoices || [];
    const totalDu  = inv.reduce((a, i) =>
      a + parseFloat(i.outstanding_amount || i.grand_total || 0), 0);

    // Prévision simple : dernier mois * 1.1
    const caMois   = sm.ca_par_mois || {};
    const vals     = Object.values(caMois);
    const lastCA   = vals.length > 0 ? vals[vals.length - 1] : 0;
    const prevision = Math.round(lastCA * 1.1);
    const objectif  = Math.round(lastCA * 1.2);

    // Couleurs pour les barres de progression
    const progColors = ['#00D4FF', '#00E396', '#FEB019', '#775DD0', '#FF4560'];
    const progPcts   = [62, 88, 34, 71, 45];
    const statuses   = ['en cours', 'avancé', 'initié', 'en cours', 'en cours'];

    Utils.setMain(`

      <!-- ── EN-TÊTE ── -->
      <div class="page-head">
        <div>
          <div class="page-title">Feuille de Route Stratégique</div>
          <div class="page-sub">Recommandations IA et objectifs business · ${RPT.date}</div>
        </div>
      </div>

      <div class="grid-6-4">

        <!-- ── GAUCHE : Initiatives stratégiques ── -->
        <div>

          ${sl.length === 0
            ? `<div class="card">
                <div class="card-body">
                  <div style="text-align:center;color:var(--text3);padding:20px">
                    Lance <code>python test_groq.py</code> pour générer des recommandations
                  </div>
                </div>
               </div>`
            : sl.map((l, i) => {
                const st  = statuses[i % statuses.length];
                const pct = progPcts[i % progPcts.length];
                const col = progColors[i % progColors.length];
                const stCls = st === 'avancé' ? 'ok'
                            : st === 'initié' ? 'purple' : 'med';

                return `
                  <div class="strat-item">
                    <div class="strat-top">
                      <div class="strat-title">
                        ${Utils.md(l.split(':')[0] || l)}
                      </div>
                      ${Utils.badge(st, stCls)}
                    </div>
                    <div class="strat-meta">
                      <span class="budget">Recommandation IA</span>
                      <span class="roi">↑ Prioritaire</span>
                    </div>
                    <div class="prog-bar">
                      <div class="prog-fill"
                        style="width:${pct}%;background:${col}">
                      </div>
                    </div>
                    <div class="prog-foot">
                      <div class="prog-pct">${pct}%</div>
                      <div class="prog-date">📅 Ce trimestre</div>
                    </div>
                  </div>`;
              }).join('')
          }

          <!-- Observations générales -->
          ${ol.length > 0 ? `
          <div class="card" style="margin-top:16px">
            <div class="card-head">
              <div class="card-head-left">
                <div class="card-title">💡 Observations générales</div>
                <div class="card-sub">${ol.length} point(s) identifié(s)</div>
              </div>
            </div>
            <div class="card-body-0">
              ${ol.slice(0, 5).map(l => `
                <div class="action-item"
                  style="border-left:3px solid var(--amber)">
                  <div class="action-icon high">⚡</div>
                  <div class="action-content">
                    <div class="action-desc">${Utils.md(l)}</div>
                  </div>
                </div>`).join('')}
            </div>
          </div>` : ''}

        </div>

        <!-- ── DROITE : Radar + Objectifs ── -->
        <div>

          <!-- Radar Performance Stratégique -->
          <div class="card" style="margin-bottom:16px">
            <div class="card-head">
              <div class="card-head-left">
                <div class="card-title">Performance Stratégique — Radar</div>
                <div class="card-sub">Actuel vs Cible</div>
              </div>
            </div>
            <div class="card-body">
              <canvas id="chart-radar" height="240"></canvas>
            </div>
          </div>

          <!-- Objectifs trimestriels -->
          <div class="card">
            <div class="card-head">
              <div class="card-head-left">
                <div class="card-title">Objectifs Trimestriels</div>
              </div>
            </div>
            <div class="card-body">
              ${[
                {
                  label: 'CA Trimestriel',
                  cur:   Utils.fmt(rev),
                  target: Utils.fmt(prevision),
                  pct:   rev > 0 ? Math.min(95, Math.round(rev / Math.max(prevision, 1) * 100)) : 40,
                },
                {
                  label: 'Paiements fournisseurs',
                  cur:   Utils.fmt(totalDu) + ' dû',
                  target: '0 DZD impayé',
                  pct:   totalDu > 0 ? 20 : 100,
                },
                {
                  label: 'Diversification fournisseurs',
                  cur:   (RPT.raw_data?.suppliers?.length || 0) + ' actifs',
                  target: '5+ fournisseurs',
                  pct:   Math.min(100, Math.round((RPT.raw_data?.suppliers?.length || 0) / 5 * 100)),
                },
                {
                  label: 'Marge brute',
                  cur:   Utils.fmt(marge),
                  target: '> 0 DZD',
                  pct:   marge > 0 ? 80 : 10,
                },
              ].map(o => `
                <div class="obj-item">
                  <div class="obj-label">${o.label}</div>
                  <div class="obj-bar">
                    <div class="obj-bar-fill" style="width:${o.pct}%"></div>
                  </div>
                  <div class="obj-vals">
                    <strong>${o.cur}</strong> / ${o.target}
                  </div>
                </div>`).join('')}
            </div>
          </div>

          <!-- Prévision IA -->
          <div class="card" style="margin-top:16px">
            <div class="card-head">
              <div class="card-head-left">
                <div class="card-title">🔮 Prévision IA — Prochain mois</div>
              </div>
              <div class="card-head-right">
                ${Utils.badge('● Modèle actif', 'ok')}
              </div>
            </div>
            <div class="card-body">
              ${[
                { label: 'CA estimé (+10%)',  val: Utils.fmt(prevision), color: 'var(--cyan)'  },
                { label: 'Objectif +20%',     val: Utils.fmt(objectif),  color: 'var(--green)' },
                { label: 'Impayés à régler',  val: Utils.fmt(totalDu),   color: 'var(--red)'   },
                { label: 'Coûts estimés',     val: Utils.fmt(cout),      color: 'var(--amber)' },
              ].map(r => `
                <div style="display:flex;justify-content:space-between;
                  padding:9px 0;border-bottom:1px solid var(--bord);font-size:13px">
                  <span style="color:var(--text2)">${r.label}</span>
                  <span style="font-weight:700;color:${r.color}">${r.val}</span>
                </div>`).join('')}
            </div>
          </div>

        </div>
      </div>
    `);

    // Render le radar après injection HTML
    if (BI) {
      setTimeout(() => {
        Charts.renderRadar('chart-radar', BI.summary || {});
      }, 100);
    }
  },
};