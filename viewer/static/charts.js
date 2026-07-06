/**
 * charts.js
 * ---------
 * Gestion de tous les graphiques Chart.js du dashboard.
 * Utilise les données ERPNext/BI pour générer les visualisations.
 *
 * Dépendances :
 *   - Chart.js (chargé depuis cdnjs dans index.html)
 *   - utils.js (Utils.fmt)
 */

const Charts = {

  // ─────────────────────────────────────────────
  // Stockage des instances Chart.js actives
  // Pour pouvoir les détruire avant de les recréer
  // ─────────────────────────────────────────────
  _instances: {},

  /**
   * Détruit un graphique existant par son ID canvas.
   * Obligatoire avant d'en créer un nouveau sur le même canvas.
   */
  destroy(id) {
    if (this._instances[id]) {
      this._instances[id].destroy();
      delete this._instances[id];
    }
  },

  /**
   * Détruit tous les graphiques actifs.
   * Appelé lors d'un changement de page.
   */
  destroyAll() {
    Object.keys(this._instances).forEach(id => this.destroy(id));
  },

  // ─────────────────────────────────────────────
  // Thème commun
  // ─────────────────────────────────────────────
  _theme: {
    gridColor:  'rgba(255,255,255,.04)',
    tickColor:  '#8B95A8',
    tickFont:   { size: 11, family: 'Inter' },
    colors:     ['#00D4FF', '#00E396', '#FEB019', '#775DD0', '#FF4560', '#26A69A', '#546E7A'],
  },

  /**
   * Formatter Y-axis : affiche en K ou M selon la magnitude.
   */
  _yFormatter(v) {
    if (Math.abs(v) >= 1_000_000) return (v / 1_000_000).toFixed(1) + 'M';
    if (Math.abs(v) >= 1_000)     return (v / 1_000).toFixed(0) + 'K';
    return v;
  },

  // ─────────────────────────────────────────────
  // Graphique 1 : Évolution CA par mois (line)
  // ─────────────────────────────────────────────

  /**
   * Graphique courbe de l'évolution du CA mensuel.
   * Affiche les données réelles + une prévision IA estimée.
   *
   * @param {string} canvasId - ID du canvas HTML
   * @param {object} caMois   - { "2026-01": 120000, "2026-02": 145000, ... }
   */
  renderCALine(canvasId, caMois) {
    this.destroy(canvasId);
    const canvas = document.getElementById(canvasId);
    if (!canvas || !caMois) return;

    const labels = Object.keys(caMois);
    const values = Object.values(caMois);

    // Génère une prévision IA simple : tendance linéaire +10%
    const prevision = values.map((v, i) =>
      i < values.length - 1 ? null : Math.round(v * 1.1)
    );

    this._instances[canvasId] = new Chart(canvas, {
      type: 'line',
      data: {
        labels,
        datasets: [
          {
            label: 'Actuel',
            data: values,
            borderColor:     '#00D4FF',
            backgroundColor: 'rgba(0,212,255,.08)',
            fill: true,
            tension: 0.4,
            borderWidth: 2,
            pointRadius: 4,
            pointBackgroundColor: '#00D4FF',
          },
          {
            label: 'Prévision IA',
            data: [...values.slice(0,-1).map(()=>null), values[values.length-1], Math.round(values[values.length-1]*1.1)],
            borderColor:     '#775DD0',
            borderDash:      [5, 5],
            fill: false,
            tension: 0.4,
            borderWidth: 2,
            pointRadius: 4,
            pointBackgroundColor: '#775DD0',
          },
        ],
      },
      options: {
        responsive: true,
        interaction: { mode: 'index', intersect: false },
        plugins: {
          legend: {
            labels: { color: this._theme.tickColor, font: this._theme.tickFont, boxWidth: 12 },
          },
          tooltip: {
            callbacks: {
              label: ctx => ` ${ctx.dataset.label}: ${Utils.fmt(ctx.raw)}`,
            },
          },
        },
        scales: {
          x: {
            grid:  { color: this._theme.gridColor },
            ticks: { color: this._theme.tickColor, font: this._theme.tickFont },
          },
          y: {
            grid:  { color: this._theme.gridColor },
            ticks: {
              color: this._theme.tickColor,
              font:  this._theme.tickFont,
              callback: v => this._yFormatter(v),
            },
          },
        },
      },
    });
  },

  // ─────────────────────────────────────────────
  // Graphique 2 : Répartition clients (donut)
  // ─────────────────────────────────────────────

  /**
   * Graphique donut de la répartition du CA par client.
   * Met aussi à jour la légende HTML sous le graphique.
   *
   * @param {string} canvasId  - ID du canvas HTML
   * @param {string} legendId  - ID du div légende HTML
   * @param {object} caClient  - { "Client A": 500000, "Client B": 300000, ... }
   */
  renderDonut(canvasId, legendId, caClient) {
    this.destroy(canvasId);
    const canvas = document.getElementById(canvasId);
    if (!canvas || !caClient) return;

    const labels = Object.keys(caClient).slice(0, 6);
    const values = labels.map(k => caClient[k]);
    const total  = values.reduce((a, b) => a + b, 0) || 1;
    const colors = this._theme.colors;

    this._instances[canvasId] = new Chart(canvas, {
      type: 'doughnut',
      data: {
        labels,
        datasets: [{
          data: values,
          backgroundColor: colors.slice(0, labels.length),
          borderWidth: 0,
          hoverOffset: 6,
        }],
      },
      options: {
        responsive: true,
        cutout: '68%',
        plugins: { legend: { display: false } },
      },
    });

    // Légende HTML
    const legendEl = document.getElementById(legendId);
    if (!legendEl) return;
    legendEl.innerHTML = labels.map((l, i) => `
      <div style="display:flex;justify-content:space-between;align-items:center;
        padding:6px 0;border-bottom:1px solid var(--bord);font-size:12px">
        <div style="display:flex;align-items:center;gap:8px">
          <span style="width:9px;height:9px;background:${colors[i]};
            border-radius:50%;display:inline-block;flex-shrink:0"></span>
          <span style="color:var(--text2)">${Utils.esc(l)}</span>
        </div>
        <span style="font-weight:600;color:var(--text)">
          ${Math.round(values[i] / total * 100)}%
        </span>
      </div>`).join('');
  },

  // ─────────────────────────────────────────────
  // Graphique 3 : CA par client (barres verticales)
  // ─────────────────────────────────────────────

  /**
   * @param {string} canvasId - ID du canvas HTML
   * @param {object} caClient - { "Client A": 500000, ... }
   */
  renderBarClients(canvasId, caClient) {
    this.destroy(canvasId);
    const canvas = document.getElementById(canvasId);
    if (!canvas || !caClient) return;

    const entries = Object.entries(caClient).slice(0, 8);
    const labels  = entries.map(([k]) => k);
    const values  = entries.map(([, v]) => v);

    this._instances[canvasId] = new Chart(canvas, {
      type: 'bar',
      data: {
        labels,
        datasets: [{
          label: 'CA',
          data: values,
          backgroundColor: this._theme.colors,
          borderRadius: 6,
          borderWidth: 0,
        }],
      },
      options: {
        responsive: true,
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: { label: ctx => ` CA: ${Utils.fmt(ctx.raw)}` },
          },
        },
        scales: {
          x: { grid: { display: false }, ticks: { color: this._theme.tickColor, font: this._theme.tickFont } },
          y: {
            grid:  { color: this._theme.gridColor },
            ticks: { color: this._theme.tickColor, font: this._theme.tickFont, callback: v => this._yFormatter(v) },
          },
        },
      },
    });
  },

  // ─────────────────────────────────────────────
  // Graphique 4 : CA par territoire (barres horizontales)
  // ─────────────────────────────────────────────

  /**
   * @param {string} canvasId - ID du canvas HTML
   * @param {object} caTerr   - { "Alger": 500000, "Oran": 200000, ... }
   */
  renderBarTerritoire(canvasId, caTerr) {
    this.destroy(canvasId);
    const canvas = document.getElementById(canvasId);
    if (!canvas || !caTerr) return;

    const entries = Object.entries(caTerr).slice(0, 8);
    const labels  = entries.map(([k]) => k);
    const values  = entries.map(([, v]) => v);

    this._instances[canvasId] = new Chart(canvas, {
      type: 'bar',
      data: {
        labels,
        datasets: [{
          label: 'CA',
          data: values,
          backgroundColor: 'rgba(0,212,255,.6)',
          borderRadius: 6,
          borderWidth: 0,
        }],
      },
      options: {
        indexAxis: 'y',
        responsive: true,
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: { label: ctx => ` CA: ${Utils.fmt(ctx.raw)}` },
          },
        },
        scales: {
          x: {
            grid:  { color: this._theme.gridColor },
            ticks: { color: this._theme.tickColor, font: this._theme.tickFont, callback: v => this._yFormatter(v) },
          },
          y: { grid: { display: false }, ticks: { color: this._theme.tickColor, font: this._theme.tickFont } },
        },
      },
    });
  },

  // ─────────────────────────────────────────────
  // Graphique 5 : Achats par fournisseur (barres)
  // ─────────────────────────────────────────────

  /**
   * @param {string} canvasId  - ID du canvas HTML
   * @param {object} achatsF   - { "TTTT": 2380000, "TEST": 21200, ... }
   */
  renderBarFournisseurs(canvasId, achatsF) {
    this.destroy(canvasId);
    const canvas = document.getElementById(canvasId);
    if (!canvas || !achatsF) return;

    const entries = Object.entries(achatsF);
    const labels  = entries.map(([k]) => k);
    const values  = entries.map(([, v]) => v);

    this._instances[canvasId] = new Chart(canvas, {
      type: 'bar',
      data: {
        labels,
        datasets: [{
          label: 'Total acheté',
          data: values,
          backgroundColor: '#FEB019',
          borderRadius: 6,
          borderWidth: 0,
        }],
      },
      options: {
        responsive: true,
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: { label: ctx => ` Total: ${Utils.fmt(ctx.raw)}` },
          },
        },
        scales: {
          x: { grid: { display: false }, ticks: { color: this._theme.tickColor, font: this._theme.tickFont } },
          y: {
            grid:  { color: this._theme.gridColor },
            ticks: { color: this._theme.tickColor, font: this._theme.tickFont, callback: v => this._yFormatter(v) },
          },
        },
      },
    });
  },

  // ─────────────────────────────────────────────
  // Graphique 6 : Revenus vs Coûts vs Marge
  // ─────────────────────────────────────────────

  /**
   * @param {string} canvasId - ID du canvas HTML
   * @param {number} revenus  - Total revenus
   * @param {number} couts    - Total coûts
   * @param {number} marge    - Marge brute
   */
  renderFinancial(canvasId, revenus, couts, marge) {
    this.destroy(canvasId);
    const canvas = document.getElementById(canvasId);
    if (!canvas) return;

    this._instances[canvasId] = new Chart(canvas, {
      type: 'bar',
      data: {
        labels: ['Revenus\n(Ventes)', 'Coûts\n(Achats)', 'Marge\nBrute'],
        datasets: [{
          data: [revenus, couts, marge],
          backgroundColor: [
            'rgba(0,227,150,.7)',
            'rgba(255,69,96,.7)',
            marge >= 0 ? 'rgba(0,212,255,.7)' : 'rgba(255,69,96,.7)',
          ],
          borderRadius: 8,
          borderWidth: 0,
        }],
      },
      options: {
        responsive: true,
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: { label: ctx => ` ${Utils.fmt(ctx.raw)}` },
          },
        },
        scales: {
          x: { grid: { display: false }, ticks: { color: this._theme.tickColor, font: this._theme.tickFont } },
          y: {
            grid:  { color: this._theme.gridColor },
            ticks: { color: this._theme.tickColor, font: this._theme.tickFont, callback: v => this._yFormatter(v) },
          },
        },
      },
    });
  },

  // ─────────────────────────────────────────────
  // Graphique 7 : Radar Performance Stratégique
  // ─────────────────────────────────────────────

  /**
   * @param {string} canvasId - ID du canvas HTML
   * @param {object} data     - données pour les axes du radar
   */
  renderRadar(canvasId, data) {
    this.destroy(canvasId);
    const canvas = document.getElementById(canvasId);
    if (!canvas) return;

    // Calcule des métriques normalisées (0-100) depuis les données ERPNext
    const rev    = data.revenus_total || 0;
    const cout   = data.couts_total || 1;
    const marge  = data.marge_brute || 0;
    const clients = data.nb_clients || 0;
    const suppliers = data.nb_fournisseurs || 1;

    const actuel = [
      Math.min(100, Math.round((marge / Math.max(rev, 1)) * 100 + 50)),  // Rentabilité
      Math.min(100, Math.round(clients * 10)),                            // Valeur
      Math.min(100, Math.round((1 - (cout / Math.max(rev * 3, 1))) * 100)), // Potentiel
      Math.min(100, Math.round(100 - (suppliers > 1 ? 20 : 60))),        // Risque inversé
      Math.min(100, Math.round(clients * 15)),                            // Engagement
      70,                                                                  // Fidélité (estimée)
    ];

    this._instances[canvasId] = new Chart(canvas, {
      type: 'radar',
      data: {
        labels: ['Rentabilité', 'Valeur', 'Potentiel', 'Risque', 'Engagement', 'Fidélité'],
        datasets: [
          {
            label: 'Actuel',
            data: actuel,
            borderColor:     '#00D4FF',
            backgroundColor: 'rgba(0,212,255,.15)',
            borderWidth: 2,
            pointBackgroundColor: '#00D4FF',
          },
          {
            label: 'Cible',
            data: [80, 85, 80, 85, 80, 85],
            borderColor:     '#FEB019',
            backgroundColor: 'rgba(254,176,25,.08)',
            borderWidth: 2,
            borderDash: [4, 4],
            pointBackgroundColor: '#FEB019',
          },
        ],
      },
      options: {
        responsive: true,
        plugins: {
          legend: {
            labels: { color: this._theme.tickColor, font: this._theme.tickFont, boxWidth: 12 },
          },
        },
        scales: {
          r: {
            grid:       { color: 'rgba(255,255,255,.08)' },
            angleLines: { color: 'rgba(255,255,255,.06)' },
            pointLabels: { color: this._theme.tickColor, font: this._theme.tickFont },
            ticks: { display: false },
            suggestedMin: 0,
            suggestedMax: 100,
          },
        },
      },
    });
  },
};