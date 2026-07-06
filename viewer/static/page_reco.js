/**
 * page_reco.js
 * ------------
 * Page "Recommandations d'Achat IA" du dashboard.
 * Affiche les articles en stock faible + recommandations Qwen3
 * avec scores de priorité, prix de marché et bouton Commander.
 *
 * Dépendances :
 *   - utils.js (Utils)
 */

const PageReco = {

  // Filtre actif : 'all' | 'crit' | 'high' | 'med'
  _filter: 'all',
  _items:  [],

  render(RPT, filter = 'all') {
    this._filter = filter;

    if (!RPT) {
      Utils.setMain(Utils.emptyState(
        '📭',
        'Aucun rapport disponible',
        'Lance <code>python test_groq.py</code>'
      ));
      return;
    }

    const s   = Utils.parseSections(RPT.final_report || '');
    const pl  = Utils.toLines(s.p);
    const raw = RPT.raw_data || {};
    const low = raw.low_stock || [];

    // Assigne un score à chaque recommandation IA
    this._items = pl.map((l, i) => ({
      text:  l,
      score: Math.max(60, 95 - i * 6),
    }));

    // Filtre selon la priorité sélectionnée
    const filtered = filter === 'all'
      ? this._items
      : this._items.filter(({ score }) => Utils.priority(score).cls === filter);

    Utils.setMain(`

      <!-- ── EN-TÊTE ── -->
      <div class="page-head">
        <div>
          <div class="page-title">Recommandations d'Achat IA</div>
          <div class="page-sub">
            Générées par analyse prédictive · Qwen3 + données ERPNext
          </div>
        </div>
        <div style="display:flex;gap:8px">
          ${Utils.pill('Toutes',   filter === 'all',  "PageReco.render(App.RPT,'all')")}
          ${Utils.pill('Critique', filter === 'crit', "PageReco.render(App.RPT,'crit')")}
          ${Utils.pill('Haute',    filter === 'high', "PageReco.render(App.RPT,'high')")}
          ${Utils.pill('Normale',  filter === 'med',  "PageReco.render(App.RPT,'med')")}
        </div>
      </div>

      <!-- ── STOCK FAIBLE ── -->
      ${low.length > 0 ? `
      <div class="card">
        <div class="card-head">
          <div class="card-head-left">
            <div class="card-title">📦 Articles en stock faible</div>
            <div class="card-sub">À commander en priorité — données ERPNext</div>
          </div>
          <div class="card-head-right">
            ${Utils.badge(low.length + ' articles', 'high')}
          </div>
        </div>
        <div class="card-body-0">
          ${low.slice(0, 5).map(item => {
            const actual  = parseFloat(item.actual_qty   || 0);
            const level   = parseFloat(item.reorder_level || 1);
            const score   = Math.min(99, Math.round(100 - (actual / level) * 100));
            const p       = Utils.priority(Math.max(score, 60));

            return `
              <div class="reco-item">
                <div class="reco-score">
                  <div class="reco-score-num ${p.cls}">${score}</div>
                  <div class="reco-score-label">score</div>
                </div>
                <div class="reco-content">
                  <div class="reco-title">
                    ${Utils.esc(item.item_name || item.item_code || '—')}
                    ${Utils.badge(p.label, p.cls)}
                  </div>
                  <div class="reco-desc">
                    Stock critique — réapprovisionnement requis
                  </div>
                  <div class="reco-meta">
                    Entrepôt : <strong>${Utils.esc(item.warehouse || '—')}</strong> ·
                    Stock actuel : <strong style="color:var(--red)">${actual}</strong> ·
                    Seuil : <strong>${level}</strong> ·
                    Qté à commander :
                    <strong style="color:var(--cyan)">${item.reorder_qty || '—'}</strong>
                  </div>
                </div>
                <div class="reco-right">
                  <div class="reco-price">+${item.reorder_qty || '?'} unités</div>
                  <div class="reco-price-label">qté recommandée</div>
                  <button class="btn-cmd"
                    onclick="alert('Commander ${Utils.esc(item.item_code || '')}')">
                    Commander
                  </button>
                </div>
              </div>`;
          }).join('')}
        </div>
      </div>` : ''}

      <!-- ── RECOMMANDATIONS IA ── -->
      <div class="card">
        <div class="card-head">
          <div class="card-head-left">
            <div class="card-title">🤖 Recommandations IA — Prix de marché Algérie</div>
            <div class="card-sub">${filtered.length} résultat(s)</div>
          </div>
        </div>
        <div class="card-body-0">
          ${filtered.length === 0
            ? `<div style="padding:40px;text-align:center;color:var(--text3)">
                Aucune recommandation pour ce filtre
               </div>`
            : filtered.map(({ text, score }) => {
                const p          = Utils.priority(score);
                const priceMatch = text.match(/([\d\s]+(?:–|-)?[\d\s]*DZD)/i);
                const price      = priceMatch ? priceMatch[1].trim() : '';
                const whereMatch = text.match(
                  /(?:Où acheter|Zone|Fournisseur\s*(?:recommand[eé]|alternatif)?)\s*:?\s*([^|<\n·]{5,50})/i
                );
                const where = whereMatch ? whereMatch[1].trim() : '';
                const title = text.split('|')[0].split(':')[0] || text;

                return `
                  <div class="reco-item">
                    <div class="reco-score">
                      <div class="reco-score-num ${p.cls}">${score}</div>
                      <div class="reco-score-label">score</div>
                    </div>
                    <div class="reco-content">
                      <div class="reco-title">
                        ${Utils.md(title)}
                        ${Utils.badge(p.label, p.cls)}
                      </div>
                      <div class="reco-desc">${Utils.md(text)}</div>
                      ${where
                        ? `<div class="reco-meta">
                            📍 Où acheter : <strong>${Utils.esc(where)}</strong>
                           </div>`
                        : ''}
                    </div>
                    <div class="reco-right">
                      ${price
                        ? `<div class="reco-price">+${Utils.esc(price)}</div>
                           <div class="reco-price-label">prix estimé marché</div>`
                        : ''}
                      <button class="btn-cmd"
                        onclick="alert('Commande initiée')">
                        Commander
                      </button>
                    </div>
                  </div>`;
              }).join('')
          }
        </div>
      </div>

    `);
  },
};