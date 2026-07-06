/**
 * page_general.js
 * ---------------
 * Page "Vue Générale" du dashboard Achats IA.
 * Affiche les KPIs principaux, le graphique CA,
 * le donut clients, et un aperçu des recommandations.
 *
 * Dépendances :
 *   - utils.js  (Utils)
 *   - charts.js (Charts)
 */

const PageGeneral = {

  render(RPT, BI) {
    if (!RPT) {
      Utils.setMain(Utils.emptyState(
        '📭',
        'Aucun rapport disponible',
        'Lance <code>python test_groq.py</code>'
      ));
      return;
    }

    const s       = Utils.parseSections(RPT.final_report || '');
    const sm      = RPT.summary || {};
    const raw     = RPT.raw_data || {};
    const inv     = raw.invoices || [];
    const purch   = raw.purchases || [];
    const supp    = raw.suppliers || [];
    const low     = raw.low_stock || [];
    const ul      = Utils.toLines(s.u);
    const pl      = Utils.toLines(s.p);

    // Calculs financiers
    const totalUnpaid = inv.reduce((a, i) =>
      a + parseFloat(i.outstanding_amount || i.grand_total || 0), 0);
    const overdue = inv.filter(i => i.status === 'Overdue').length;
    const rev     = BI?.summary?.revenus_total  || 0;
    const marge   = BI?.summary?.marge_brute    || 0;
    const margePct = rev > 0 ? Math.round(marge / rev * 100) : 0;

    Utils.setMain(`
      <!-- ── KPI ROW ── -->
      <div class="kpi-row kpi-6">

        <div class="kpi">
          <div class="lb">CA Total</div>
          <div class="val val-sm">${Utils.fmt(rev)}</div>
          <div class="sub">Toutes factures vente</div>
        </div>

        <div class="kpi">
          <div class="lb">Marge Brute</div>
          <div class="val">
            ${margePct > 0 ? margePct + '%' : '—'}
            ${margePct !== 0
              ? `<span class="chg ${margePct >= 0 ? 'chg-up' : 'chg-down'}">
                  ${margePct >= 0 ? '↑' : '↓'} ${Math.abs(margePct)}%
                </span>`
              : ''}
          </div>
          <div class="sub">${Utils.fmt(marge)}</div>
        </div>

        <div class="kpi">
          <div class="lb">Fournisseurs actifs</div>
          <div class="val">${supp.length}</div>
          <div class="sub">${purch.length} commandes récentes</div>
        </div>

        <div class="kpi ${overdue > 0 ? 'pulse-red' : ''}"
          style="${overdue > 0 ? 'border-color:var(--red);background:var(--red-dim)' : ''}">
          <div class="lb">Factures en retard</div>
          <div class="val" style="${overdue > 0 ? 'color:var(--red)' : ''}">${overdue}</div>
          <div class="sub">${Utils.fmt(totalUnpaid)} impayé</div>
        </div>

        <div class="kpi">
          <div class="lb">Articles stock faible</div>
          <div class="val">${low.length || '—'}</div>
          <div class="sub">${low.length > 0 ? 'à réapprovisionner' : 'aucun seuil configuré'}</div>
        </div>

        <div class="kpi">
          <div class="lb">Modèle IA</div>
          <div class="val" style="font-size:13px;margin-top:4px">${RPT.model || 'Qwen3'}</div>
          <div class="sub">${sm.segments_ok || 0} segments · ${new Date(RPT.generated_at)
            .toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' })}</div>
        </div>

      </div>

      <!-- ── GRAPHIQUES ── -->
      ${BI ? `
      <div class="grid-6-4">

        <div class="card">
          <div class="card-head">
            <div class="card-head-left">
              <div class="card-title">Évolution du Chiffre d'Affaires</div>
              <div class="card-sub">Actuel vs Prévision IA</div>
            </div>
          </div>
          <div class="card-body">
            <canvas id="chart-ca-line" height="200"></canvas>
          </div>
        </div>

        <div class="card">
          <div class="card-head">
            <div class="card-head-left">
              <div class="card-title">Répartition par Client</div>
              <div class="card-sub">Part du CA total</div>
            </div>
          </div>
          <div class="card-body">
            <canvas id="chart-donut-clients" height="180"></canvas>
            <div id="donut-legend" style="margin-top:12px"></div>
          </div>
        </div>

      </div>` : ''}

      <!-- ── TOP RECOMMANDATIONS ── -->
      <div class="card">
        <div class="card-head">
          <div class="card-head-left">
            <div class="card-title">Top Recommandations d'achat urgentes</div>
            <div class="card-sub">Générées par Qwen3 · ${pl.length} recommandation(s)</div>
          </div>
          <div class="card-head-right">
            <div class="link-btn" onclick="App.go('reco', document.querySelectorAll('.tab')[2])">
              Voir toutes →
            </div>
          </div>
        </div>
        <div class="card-body-0">
          ${pl.length === 0
            ? `<div style="padding:30px;text-align:center;color:var(--text3)">
                Aucune recommandation disponible
               </div>`
            : pl.slice(0, 4).map((l, i) => {
                const score = 95 - i * 7;
                const p = Utils.priority(score);
                return `
                  <div class="reco-item">
                    <div class="reco-score">
                      <div class="reco-score-num ${p.cls}">${score}</div>
                      <div class="reco-score-label">score</div>
                    </div>
                    <div class="reco-content">
                      <div class="reco-title">
                        ${Utils.md(l.split('|')[0].split(':')[0] || l)}
                        ${Utils.badge(p.label, p.cls)}
                      </div>
                      <div class="reco-desc">${Utils.md(l)}</div>
                    </div>
                  </div>`;
              }).join('')
          }
        </div>
      </div>

      <!-- ── FACTURES IMPAYÉES APERÇU ── -->
      ${inv.length > 0 ? `
      <div class="card">
        <div class="card-head">
          <div class="card-head-left">
            <div class="card-title">🔴 Factures impayées</div>
            <div class="card-sub">
              Total dû : <strong style="color:var(--red)">${Utils.fmt(totalUnpaid)}</strong>
            </div>
          </div>
          <div class="card-head-right">
            ${Utils.badge(overdue + ' en retard', 'crit')}
            <div class="link-btn"
              onclick="App.go('urgent', document.querySelectorAll('.tab')[1])">
              Voir toutes →
            </div>
          </div>
        </div>
        <div class="tbl-wrap">
          <table>
            <thead>
              <tr>
                <th>N° Facture</th>
                <th>Fournisseur</th>
                <th>Montant dû</th>
                <th>Échéance</th>
                <th>Retard</th>
                <th>Statut</th>
              </tr>
            </thead>
            <tbody>
              ${inv.map(i => {
                const montant = parseFloat(i.outstanding_amount || i.grand_total || 0);
                const delay   = Utils.delayLabel(i.due_date || i.posting_date);
                const statusCls = i.status === 'Overdue' ? 'crit'
                                : i.status === 'Paid'    ? 'ok' : 'high';
                return `
                  <tr>
                    <td class="td-main">${Utils.esc(i.name || '—')}</td>
                    <td class="td-cyan">${Utils.esc(i.supplier || '—')}</td>
                    <td class="td-red">${Utils.fmt(montant)}</td>
                    <td>${i.due_date || i.posting_date || '—'}</td>
                    <td style="color:var(--${delay.color})">${delay.label}</td>
                    <td>${Utils.badge(i.status || '—', statusCls)}</td>
                  </tr>`;
              }).join('')}
            </tbody>
          </table>
          <div class="tbl-footer">
            <span class="tbl-total">
              Total impayé : <span class="tbl-total-val">${Utils.fmt(totalUnpaid)}</span>
            </span>
            <span style="color:var(--text3)">${inv.length} factures</span>
          </div>
        </div>
      </div>` : ''}
    `);

    // ── Render les graphiques après l'injection HTML ──
    if (BI) {
      setTimeout(() => {
        Charts.renderCALine('chart-ca-line', BI.summary?.ca_par_mois || {});
        Charts.renderDonut('chart-donut-clients', 'donut-legend', BI.summary?.ca_par_client || {});
      }, 100);
    }
  },
};