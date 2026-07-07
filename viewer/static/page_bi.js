/**
 * page_bi.js
 * ----------
 * Page "Dashboard BI" du dashboard Achats IA.
 * Affiche les métriques financières, graphiques BI,
 * tableau fournisseurs et qualité des données ERPNext.
 *
 * Dépendances :
 *   - utils.js  (Utils)
 *   - charts.js (Charts)
 */

const PageBI = {

  render(BI) {
    if (!BI) {
      Utils.setMain(Utils.emptyState(
        '📊',
        'Aucun rapport BI disponible',
        'Lance <code>python bi_analysis.py</code>'
      ));
      return;
    }

    const sm      = BI.summary || {};
    const rev     = sm.revenus_total  || 0;
    const cout    = sm.couts_total    || 0;
    const marge   = sm.marge_brute    || 0;
    const charts  = BI.charts_b64    || {};
    const achatsF = sm.achats_par_fournisseur || {};
    const caMois  = sm.ca_par_mois           || {};
    const qd      = sm.qualite_donnees       || {};

    const margePct = rev > 0 ? Math.round(marge / rev * 100) : 0;

    Utils.setMain(`

      <!-- ── EN-TÊTE ── -->
      <div class="page-head">
        <div>
          <div class="page-title">Dashboard BI — Analyse Financière</div>
          <div class="page-sub">Données ERPNext · ${BI.date}</div>
        </div>
      </div>

      <!-- ── KPI FINANCIERS ── -->
      <div class="kpi-row kpi-3">
        <div class="kpi" style="border-color:var(--green)">
          <div class="lb">📈 Revenus totaux</div>
          <div class="val val-sm" style="color:var(--green)">${Utils.fmt(rev)}</div>
          <div class="sub">${sm.nb_factures_vente || 0} factures de vente</div>
        </div>
        <div class="kpi" style="border-color:var(--red)">
          <div class="lb">📉 Coûts totaux</div>
          <div class="val val-sm" style="color:var(--red)">${Utils.fmt(cout)}</div>
          <div class="sub">${sm.nb_factures_achat || 0} factures d'achat</div>
        </div>
        <div class="kpi" style="border-color:${marge >= 0 ? 'var(--green)' : 'var(--red)'}">
          <div class="lb">💰 Marge brute</div>
          <div class="val val-sm" style="color:${marge >= 0 ? 'var(--green)' : 'var(--red)'}">
            ${Utils.fmt(marge)}
          </div>
          <div class="sub">${margePct}% du CA</div>
        </div>
      </div>

      <div class="kpi-row kpi-4">
        <div class="kpi">
          <div class="lb">Meilleur mois</div>
          <div class="val val-sm" style="color:var(--cyan);font-size:16px;margin-top:4px">
            ${sm.meilleur_mois || '—'}
          </div>
          <div class="sub">${Utils.fmt(sm.meilleur_mois_ca || 0)}</div>
        </div>
        <div class="kpi">
          <div class="lb">Meilleure ville</div>
          <div class="val val-sm" style="color:var(--amber);font-size:16px;margin-top:4px">
            ${sm.meilleure_ville || '—'}
          </div>
          <div class="sub">${Utils.fmt(sm.meilleure_ville_ca || 0)}</div>
        </div>
        <div class="kpi">
          <div class="lb">Clients actifs</div>
          <div class="val">${sm.nb_clients || 0}</div>
          <div class="sub">${sm.nb_fournisseurs || 0} fournisseurs</div>
        </div>
        <div class="kpi">
          <div class="lb">Articles stockables</div>
          <div class="val">${sm.nb_articles || 0}</div>
          <div class="sub">${sm.nb_factures_vente || 0} factures vente</div>
        </div>
      </div>

      <!-- ── GRAPHIQUES BI (depuis PNG matplotlib) ── -->
      ${Object.keys(charts).length > 0 ? `
      <div class="charts-grid">
        ${['ca_par_mois', 'ca_par_territoire', 'ca_par_client', 'achats_par_fournisseur']
          .filter(n => charts[n])
          .map(n => `
            <div class="card">
              <div class="card-head">
                <div class="card-title">${{
                  ca_par_mois:           '📅 CA par mois',
                  ca_par_territoire:     '📍 CA par ville',
                  ca_par_client:         '👥 CA par client',
                  achats_par_fournisseur:'🏭 Achats fournisseurs',
                }[n]}</div>
              </div>
              <img src="${charts[n]}" style="width:100%;display:block" loading="lazy">
            </div>`).join('')}

        ${charts.revenus_couts_marge ? `
        <div class="card full">
          <div class="card-head">
            <div class="card-title">💰 Revenus vs Coûts vs Marge</div>
          </div>
          <img src="${charts.revenus_couts_marge}"
            style="width:100%;display:block" loading="lazy">
        </div>` : ''}
      </div>` : `
      <div class="card" style="margin-bottom:20px">
        <div class="card-body">
          ${Utils.emptyState('📊', 'Graphiques non générés',
            'Lance <code>python bi_analysis.py</code> pour générer les graphiques')}
        </div>
      </div>`}

      <!-- ── CA PAR MOIS (tableau) ── -->
      ${Object.keys(caMois).length > 0 ? `
      <div class="card">
        <div class="card-head">
          <div class="card-head-left">
            <div class="card-title">📅 CA par mois — Détail</div>
          </div>
        </div>
        <div class="tbl-wrap">
          <table>
            <thead>
              <tr>
                <th>Mois</th>
                <th>CA</th>
                <th>% du total</th>
                <th>Performance</th>
              </tr>
            </thead>
            <tbody>
              ${Object.entries(caMois)
                .sort((a, b) => b[1] - a[1])
                .map(([m, v]) => {
                  const pct    = rev > 0 ? Math.round(v / rev * 100) : 0;
                  const maxV   = Math.max(...Object.values(caMois));
                  const avg    = rev / Math.max(Object.keys(caMois).length, 1);
                  const perf   = v === maxV
                    ? '🏆 Meilleur mois'
                    : v > avg
                      ? '📈 Au-dessus moyenne'
                      : '📉 En dessous';
                  return `
                    <tr>
                      <td class="td-main">${Utils.esc(m)}</td>
                      <td class="td-green">${Utils.fmt(v)}</td>
                      <td>${pct}%</td>
                      <td>${perf}</td>
                    </tr>`;
                }).join('')}
            </tbody>
          </table>
          <div class="tbl-footer">
            <span class="tbl-total">
              CA total :
              <span style="color:var(--green);font-size:15px">${Utils.fmt(rev)}</span>
            </span>
            <span style="color:var(--text3)">
              ${Object.keys(caMois).length} mois
            </span>
          </div>
        </div>
      </div>` : ''}

      <!-- ── FOURNISSEURS ── -->
      ${Object.keys(achatsF).length > 0 ? `
      <div class="card">
        <div class="card-head">
          <div class="card-head-left">
            <div class="card-title">🏭 Analyse Fournisseurs</div>
            <div class="card-sub">
              Performance et risques · ${Object.keys(achatsF).length} fournisseur(s)
            </div>
          </div>
        </div>
        <div class="tbl-wrap">
          <table>
            <thead>
              <tr>
                <th>Fournisseur</th>
                <th>Total acheté</th>
                <th>Part des achats</th>
                <th>Risque dépendance</th>
                <th>Statut</th>
              </tr>
            </thead>
            <tbody>
              ${Object.entries(achatsF).map(([f, v]) => {
                const pct  = cout > 0 ? Math.round(v / cout * 100) : 0;
                const risk = pct > 70
                  ? { cls: 'crit',  label: 'CRITIQUE' }
                  : pct > 40
                    ? { cls: 'high', label: 'ÉLEVÉ' }
                    : { cls: 'ok',   label: 'FAIBLE' };
                return `
                  <tr>
                    <td class="td-main">${Utils.esc(f)}</td>
                    <td class="td-cyan">${Utils.fmt(v)}</td>
                    <td>${pct}%</td>
                    <td>${Utils.badge(risk.label, risk.cls)}</td>
                    <td>${Utils.badge('Actif', 'ok')}</td>
                  </tr>`;
              }).join('')}
            </tbody>
          </table>
          <div class="tbl-footer">
            <span class="tbl-total">
              Total achats :
              <span class="tbl-total-val" style="color:var(--amber)">
                ${Utils.fmt(cout)}
              </span>
            </span>
            <span style="color:var(--text3)">
              ${Object.keys(achatsF).length} fournisseurs
            </span>
          </div>
        </div>
      </div>` : ''}

      <!-- ── QUALITÉ DES DONNÉES ── -->
      ${Object.keys(qd).length > 0 ? `
      <div class="card">
        <div class="card-head">
          <div class="card-head-left">
            <div class="card-title">⚠️ Qualité des Données ERPNext</div>
            <div class="card-sub">
              Données manquantes à corriger pour améliorer l'analyse IA
            </div>
          </div>
        </div>
        <div class="card-body">
          ${[
            {
              label:  'Clients sans territoire',
              val:    `${qd.clients_sans_territoire || 0} / ${qd.clients_total || 0}`,
              pct:    qd.pct_territoire_manquant || 0,
              action: 'Remplir le champ Territory sur chaque client ERPNext',
            },
            {
              label:  'Factures sans territoire',
              val:    `${qd.factures_sans_territoire || 0} / ${qd.factures_total || 0}`,
              pct:    qd.pct_factures_sans_terr || 0,
              action: 'Lier les factures au territoire du client',
            },
          ].map(r => `
            <div class="obj-item">
              <div style="flex:1">
                <div style="font-size:13px;font-weight:500;margin-bottom:2px">
                  ${r.label}
                </div>
                <div style="font-size:11px;color:var(--text3)">${r.action}</div>
              </div>
              <div style="text-align:right;min-width:150px">
                <div style="font-size:13px;font-weight:600;
                  color:${r.pct > 50 ? 'var(--red)' : r.pct > 20 ? 'var(--amber)' : 'var(--green)'}">
                  ${r.val} (${r.pct}% manquant)
                </div>
              </div>
            </div>`).join('')}
        </div>
      </div>` : ''}

    `);
  },
};