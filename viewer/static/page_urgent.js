/**
 * page_urgent.js
 * --------------
 * Page "Actions Urgentes" du dashboard Achats IA.
 * Affiche les factures impayées avec retard,
 * total par fournisseur, et analyse IA.
 *
 * Dépendances :
 *   - utils.js (Utils)
 */

const PageUrgent = {

  render(RPT) {
    if (!RPT) {
      Utils.setMain(Utils.emptyState(
        '📭',
        'Aucun rapport disponible',
        'Lance <code>python test_groq.py</code>'
      ));
      return;
    }

    const raw     = RPT.raw_data || {};
    const inv     = raw.invoices || [];
    const s       = Utils.parseSections(RPT.final_report || '');
    const ul      = Utils.toLines(s.u);
    const overdue = inv.filter(i => i.status === 'Overdue');
    const unpaid  = inv.filter(i => i.status === 'Unpaid');

    // ── Totaux par fournisseur ──
    const bySupplier = {};
    let totalDu = 0;
    inv.forEach(i => {
      const m   = parseFloat(i.outstanding_amount || i.grand_total || 0);
      const sup = i.supplier || 'Inconnu';
      bySupplier[sup] = (bySupplier[sup] || 0) + m;
      totalDu += m;
    });

    Utils.setMain(`

      <!-- ── EN-TÊTE ── -->
      <div class="page-head">
        <div>
          <div class="page-title">Actions Urgentes</div>
          <div class="page-sub">
            ${overdue.length} action(s) critique(s) ·
            ${unpaid.length} action(s) haute priorité
          </div>
        </div>
      </div>

      <!-- ── KPI FOURNISSEURS ── -->
      <div class="kpi-row" style="grid-template-columns:repeat(${Math.min(Object.keys(bySupplier).length + 1, 4)},1fr)">
        ${Object.entries(bySupplier).map(([sup, val]) => `
          <div class="kpi" style="border-color:var(--red);background:var(--red-dim)">
            <div class="lb">${Utils.esc(sup)}</div>
            <div class="val val-sm" style="color:var(--red)">${Utils.fmt(val)}</div>
            <div class="sub">impayé</div>
          </div>`).join('')}
        <div class="kpi" style="border-color:var(--red)">
          <div class="lb">TOTAL GÉNÉRAL</div>
          <div class="val val-sm" style="color:var(--red)">${Utils.fmt(totalDu)}</div>
          <div class="sub">${inv.length} facture(s)</div>
        </div>
      </div>

      <!-- ── TABLEAU DÉTAILLÉ ── -->
      <div class="card">
        <div class="card-head">
          <div class="card-head-left">
            <div class="card-title">🧾 Détail des factures impayées</div>
            <div class="card-sub">
              Total dû :
              <strong style="color:var(--red)">${Utils.fmt(totalDu)}</strong>
              · Cliquez sur une colonne pour trier
            </div>
          </div>
          <div class="card-head-right">
            ${Utils.badge(overdue.length + ' en retard', 'crit')}
            ${Utils.badge(unpaid.length + ' à échoir', 'high')}
          </div>
        </div>
        <div class="card-body-0">

          ${inv.length === 0
            ? `<div style="padding:40px;text-align:center;color:var(--text3)">
                ✅ Aucune facture impayée
               </div>`
            : `
            <!-- Barre de recherche -->
            <div style="padding:12px 20px;border-bottom:1px solid var(--bord);
              display:flex;align-items:center;gap:10px">
              <input
                id="search-inv"
                placeholder="Rechercher une facture, un fournisseur..."
                oninput="PageUrgent.filter()"
                style="flex:1;background:var(--navy4);border:1px solid var(--bord2);
                  color:var(--text);padding:8px 14px;border-radius:8px;
                  font-size:13px;font-family:'Inter',sans-serif;outline:none">
              <span id="inv-count" style="font-size:12px;color:var(--text2)">
                ${inv.length} résultats
              </span>
            </div>

            <div class="tbl-wrap">
              <table>
                <thead>
                  <tr>
                    <th>N° Facture</th>
                    <th>Fournisseur</th>
                    <th>Montant total</th>
                    <th>Montant dû</th>
                    <th>Date facture</th>
                    <th>Échéance</th>
                    <th>Retard</th>
                    <th>Statut</th>
                    <th>Action</th>
                  </tr>
                </thead>
                <tbody id="inv-tbody">
                  ${this._rows(inv)}
                </tbody>
              </table>
            </div>

            <div class="tbl-footer">
              <span class="tbl-total">
                Total impayé :
                <span class="tbl-total-val">${Utils.fmt(totalDu)}</span>
              </span>
              <span style="color:var(--text3)">${inv.length} factures</span>
            </div>`
          }

        </div>
      </div>

      <!-- ── ANALYSE IA ── -->
      ${ul.length > 0 ? `
      <div class="card">
        <div class="card-head">
          <div class="card-head-left">
            <div class="card-title">🤖 Analyse IA — Actions recommandées</div>
            <div class="card-sub">
              Générées par Qwen3 · basées uniquement sur les données ERPNext
            </div>
          </div>
        </div>
        <div class="card-body-0">
          ${ul.map(l => `
            <div class="action-item" style="border-left:3px solid var(--cyan)">
              <div class="action-icon med">💡</div>
              <div class="action-content">
                <div class="action-desc">${Utils.md(l)}</div>
              </div>
            </div>`).join('')}
        </div>
      </div>` : ''}

    `);

    // Stocke les données pour le filtre
    this._data = inv;
  },

  // ── Génère les lignes du tableau ──
  _rows(inv) {
    return inv.map(i => {
      const montant  = parseFloat(i.outstanding_amount || i.grand_total || 0);
      const grand    = parseFloat(i.grand_total || 0);
      const delay    = Utils.delayLabel(i.due_date || i.posting_date);
      const isCrit   = i.status === 'Overdue';
      const statusCls = isCrit ? 'crit' : i.status === 'Paid' ? 'ok' : 'high';

      return `
        <tr>
          <td class="td-main">${Utils.esc(i.name || '—')}</td>
          <td class="td-cyan">${Utils.esc(i.supplier || '—')}</td>
          <td>${Utils.fmt(grand)}</td>
          <td class="td-red">${Utils.fmt(montant)}</td>
          <td>${i.posting_date || '—'}</td>
          <td>${i.due_date || '—'}</td>
          <td style="color:var(--${delay.color});font-weight:600">${delay.label}</td>
          <td>${Utils.badge(i.status || '—', statusCls)}</td>
          <td>
            <button class="btn-traiter"
              onclick="alert('Ouverture de la facture ${Utils.esc(i.name || '')} dans ERPNext')">
              Traiter →
            </button>
          </td>
        </tr>`;
    }).join('');
  },

  // ── Filtre le tableau par recherche ──
  filter() {
    const q     = (document.getElementById('search-inv')?.value || '').toLowerCase();
    const tbody = document.getElementById('inv-tbody');
    const count = document.getElementById('inv-count');
    if (!tbody || !this._data) return;

    const filtered = this._data.filter(i =>
      (i.name      || '').toLowerCase().includes(q) ||
      (i.supplier  || '').toLowerCase().includes(q) ||
      (i.status    || '').toLowerCase().includes(q)
    );

    tbody.innerHTML = this._rows(filtered);
    if (count) count.textContent = filtered.length + ' résultats';
  },

  // Stockage des données pour le filtre
  _data: [],
};