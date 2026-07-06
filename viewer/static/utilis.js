/**
 * utils.js
 * --------
 * Fonctions utilitaires partagées par toutes les pages.
 * Formatage, parsing, helpers DOM.
 */

const Utils = {

  // ─────────────────────────────────────────────
  // Formatage des nombres
  // ─────────────────────────────────────────────

  /**
   * Formate un nombre en DZD lisible.
   * ex: 1234567 → "1.23M DZD"
   *     12345   → "12 345 DZD"
   */
  fmt(n, suffix = 'DZD') {
    if (n === null || n === undefined || n === '') return '—';
    n = parseFloat(n) || 0;
    if (Math.abs(n) >= 1_000_000)
      return (n / 1_000_000).toFixed(2) + 'M ' + suffix;
    if (Math.abs(n) >= 1_000)
      return n.toLocaleString('fr-FR') + ' ' + suffix;
    return n.toLocaleString('fr-FR') + ' ' + suffix;
  },

  /**
   * Formate un pourcentage.
   * ex: 0.384 → "38.4%"
   */
  fmtPct(n, decimals = 1) {
    if (n === null || n === undefined) return '—';
    return parseFloat(n).toFixed(decimals) + '%';
  },

  // ─────────────────────────────────────────────
  // Dates
  // ─────────────────────────────────────────────

  /**
   * Calcule le nombre de jours entre aujourd'hui et une date.
   * Retourne un nombre positif si la date est dans le passé (retard).
   * ex: "2026-04-21" → 71 (jours de retard)
   */
  daysSince(dateStr) {
    if (!dateStr) return null;
    const diff = new Date() - new Date(dateStr);
    return Math.floor(diff / (1000 * 60 * 60 * 24));
  },

  /**
   * Formate une date ISO en français.
   * ex: "2026-04-21" → "21/04/2026"
   */
  fmtDate(dateStr) {
    if (!dateStr) return '—';
    const d = new Date(dateStr);
    return d.toLocaleDateString('fr-FR');
  },

  /**
   * Retourne un label de délai coloré.
   * ex: 71 jours → { label: "J+71", color: "red" }
   */
  delayLabel(dateStr) {
    const d = Utils.daysSince(dateStr);
    if (d === null) return { label: '—', color: 'grey' };
    if (d === 0)    return { label: "Aujourd'hui", color: 'cyan' };
    if (d > 0)      return { label: `J+${d}`, color: d > 30 ? 'red' : 'amber' };
    return { label: `J${d}`, color: 'cyan' };
  },

  // ─────────────────────────────────────────────
  // Texte & HTML
  // ─────────────────────────────────────────────

  /**
   * Échappe le HTML pour éviter les injections XSS.
   */
  esc(t) {
    const d = document.createElement('div');
    d.textContent = t || '';
    return d.innerHTML;
  },

  /**
   * Convertit le markdown simple en HTML.
   * Supporte : **gras**, *italique*, retours à la ligne.
   */
  md(t) {
    if (!t) return '';
    return (t + '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
      .replace(/\*(.+?)\*/g,   '<em>$1</em>')
      .replace(/\n/g, '<br>');
  },

  // ─────────────────────────────────────────────
  // Parsing des sections du rapport Qwen3
  // ─────────────────────────────────────────────

  /**
   * Découpe le rapport final Qwen3 en 4 sections.
   * Retourne un objet avec les clés : u, p, st, o
   *   u  = Actions Urgentes
   *   p  = Recommandations d'Achat
   *   st = Stratégie
   *   o  = Observations Générales
   */
  parseSections(txt) {
    const s = { u: '', p: '', st: '', o: '' };
    if (!txt) return s;

    const patterns = [
      { k: 'u',  rx: /1[.)]\s*ACTIONS?\s*URGENTES?([\s\S]*?)(?=2[.)]\s*RECOMMANDATIONS?|$)/i },
      { k: 'p',  rx: /2[.)]\s*RECOMMANDATIONS?\s*D.ACHAT([\s\S]*?)(?=3[.)]\s*STRAT|$)/i },
      { k: 'st', rx: /3[.)]\s*STRAT.GIE([\s\S]*?)(?=4[.)]\s*OBSERVATIONS?|$)/i },
      { k: 'o',  rx: /4[.)]\s*OBSERVATIONS?([\s\S]*)/i },
    ];

    patterns.forEach(({ k, rx }) => {
      const m = txt.match(rx);
      if (m) s[k] = m[1].trim();
    });

    // Fallback : si aucune section trouvée, met tout dans "p"
    if (!s.u && !s.p && !s.st && !s.o) s.p = txt;
    return s;
  },

  /**
   * Découpe un bloc de texte en lignes significatives.
   * Enlève les lignes vides, les titres markdown (#), les séparateurs (---).
   */
  toLines(txt) {
    if (!txt) return [];
    return txt
      .split('\n')
      .map(l => l.trim())
      .filter(l =>
        l.length > 4 &&
        !/^#{1,4}\s/.test(l) &&
        !/^---+$/.test(l) &&
        !/^═+$/.test(l)
      );
  },

  // ─────────────────────────────────────────────
  // Priorités IA
  // ─────────────────────────────────────────────

  /**
   * Retourne la priorité d'un score IA.
   * ex: 92 → { cls: "crit", label: "CRITIQUE" }
   */
  priority(score) {
    if (score >= 85) return { cls: 'crit',  label: 'CRITIQUE' };
    if (score >= 70) return { cls: 'high',  label: 'HAUTE' };
    return              { cls: 'med',   label: 'NORMALE' };
  },

  // ─────────────────────────────────────────────
  // DOM
  // ─────────────────────────────────────────────

  /**
   * Injecte du HTML dans le conteneur principal.
   */
  setMain(html) {
    document.getElementById('main').innerHTML = html;
  },

  /**
   * Retourne le HTML d'un état vide.
   */
  emptyState(icon, title, subtitle = '') {
    return `
      <div class="empty">
        <div class="ico">${icon}</div>
        <p><strong>${title}</strong>${subtitle ? '<br><br>' + subtitle : ''}</p>
      </div>`;
  },

  /**
   * Retourne le HTML d'un badge.
   * cls : 'crit' | 'high' | 'med' | 'ok' | 'purple'
   */
  badge(text, cls = 'med') {
    return `<span class="badge ${cls}">${Utils.esc(text)}</span>`;
  },

  /**
   * Retourne le HTML d'une pill de filtre.
   */
  pill(text, active = false, onclick = '') {
    return `<span class="pill ${active ? 'on' : 'off'}" onclick="${onclick}">${text}</span>`;
  },
};