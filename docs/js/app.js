/* 飘投资研究库 — 前端逻辑：加载 data.json、hash 路由、分类、全文搜索、文章渲染 */
(function () {
  'use strict';

  const CATS = {
    companies: '公司研究',
    industries: '行业研究',
    options: '期权研究',
    macro: '宏观经济',
    reports: '研报分析',
    learning: '学习',
    books: '书刊笔记',
    history: '经济历史',
  };

  const $main = document.getElementById('main');
  const $tabs = document.getElementById('tabs');
  const $search = document.getElementById('search-input');
  const $footInfo = document.getElementById('foot-info');
  const $offline = document.getElementById('offline-badge');

  let DATA = { entries: [], version: '' };
  let catFilter = null; // 分类页内的 ticker/tag 筛选

  /* ── 数据加载 ── */
  fetch('data.json')
    .then((r) => r.json())
    .then((d) => {
      DATA = d;
      $footInfo.textContent = `飘投资研究库 · ${d.count} 篇 · 更新 ${fmtVersion(d.version)}`;
      route();
    })
    .catch(() => {
      $main.innerHTML = '<div class="empty">数据加载失败。若是首次离线打开，请先联网访问一次。</div>';
    });

  window.addEventListener('online', () => ($offline.hidden = true));
  window.addEventListener('offline', () => ($offline.hidden = false));
  if (!navigator.onLine) $offline.hidden = false;

  function fmtVersion(v) {
    return v && v.length >= 8 ? `${v.slice(0, 4)}-${v.slice(4, 6)}-${v.slice(6, 8)}` : '';
  }

  /* ── 路由 ── */
  window.addEventListener('hashchange', () => { catFilter = null; route(); });

  function route() {
    const h = decodeURIComponent(location.hash || '#/');
    const mArticle = h.match(/^#\/a\/(.+)$/);
    const mCat = h.match(/^#\/c\/(\w+)$/);
    const mSearch = h.match(/^#\/s\/(.*)$/);
    if (mArticle) return renderArticle(mArticle[1]);
    if (mCat && CATS[mCat[1]]) return renderCategory(mCat[1]);
    if (mSearch) { $search.value = mSearch[1]; return renderSearch(mSearch[1]); }
    renderHome();
  }

  function setTab(cat) {
    $tabs.querySelectorAll('a').forEach((a) => a.classList.toggle('active', a.dataset.cat === cat));
  }

  /* ── 搜索框 ── */
  let searchTimer;
  $search.addEventListener('input', () => {
    clearTimeout(searchTimer);
    searchTimer = setTimeout(() => {
      const q = $search.value.trim();
      if (q) location.hash = '#/s/' + encodeURIComponent(q);
      else if (location.hash.startsWith('#/s/')) location.hash = '#/';
    }, 250);
  });

  /* ── 视图：总览 ── */
  function renderHome() {
    setTab('home');
    const counts = {};
    DATA.entries.forEach((e) => (counts[e.category] = (counts[e.category] || 0) + 1));
    const stats = Object.keys(CATS)
      .map((c) => `<a class="stat" href="#/c/${c}"><div class="stat-num">${counts[c] || 0}</div><div class="stat-label">${CATS[c]}</div></a>`)
      .join('');
    const recent = DATA.entries.slice(0, 15).map(cardHTML).join('');
    $main.innerHTML = `
      <div class="stats">${stats}</div>
      <div class="section-title">最近记录</div>
      <div class="cards">${recent || '<div class="empty">还没有记录。用 Claude / Codex 分析后说「记录到网站」即可。</div>'}</div>`;
  }

  /* ── 视图：分类 ── */
  function renderCategory(cat) {
    setTab(cat);
    let list = DATA.entries.filter((e) => e.category === cat);

    // 收集该分类下的 ticker（公司页）和 tag 作为筛选 chips
    const keys = {};
    list.forEach((e) => {
      (cat === 'companies' ? e.tickers : []).concat(e.tags).forEach((k) => (keys[k] = (keys[k] || 0) + 1));
    });
    const chipKeys = Object.keys(keys).sort((a, b) => keys[b] - keys[a]).slice(0, 30);
    const chips = chipKeys.length
      ? `<div class="chips">${chipKeys.map((k) => `<span class="chip ${catFilter === k ? 'active' : ''}" data-k="${esc(k)}">${esc(k)} (${keys[k]})</span>`).join('')}</div>`
      : '';

    if (catFilter) list = list.filter((e) => e.tickers.includes(catFilter) || e.tags.includes(catFilter));

    $main.innerHTML = `
      <div class="section-title">${CATS[cat]} · ${list.length} 篇</div>
      ${chips}
      <div class="cards">${list.map(cardHTML).join('') || '<div class="empty">该分类暂无记录</div>'}</div>`;

    $main.querySelectorAll('.chip').forEach((el) =>
      el.addEventListener('click', () => {
        catFilter = catFilter === el.dataset.k ? null : el.dataset.k;
        renderCategory(cat);
      })
    );
  }

  /* ── 视图：搜索 ── */
  function renderSearch(q) {
    setTab(null);
    const terms = q.toLowerCase().split(/\s+/).filter(Boolean);
    const hits = DATA.entries.filter((e) => {
      const hay = (e.title + ' ' + e.tickers.join(' ') + ' ' + e.tags.join(' ') + ' ' + e.body).toLowerCase();
      return terms.every((t) => hay.includes(t));
    });
    $main.innerHTML = `
      <div class="section-title">搜索「${esc(q)}」· ${hits.length} 篇</div>
      <div class="cards">${hits.map((e) => cardHTML(e, terms)).join('') || '<div class="empty">没有匹配的记录</div>'}</div>`;
  }

  /* ── 视图：文章 ── */
  function renderArticle(id) {
    const e = DATA.entries.find((x) => x.id === id);
    if (!e) { $main.innerHTML = '<div class="empty">未找到该记录</div>'; return; }
    setTab(e.category);
    $main.innerHTML = `
      <span class="back" onclick="history.back()">← 返回</span>
      <div class="article">
        <div class="article-head">
          <div class="card-meta">
            <span class="badge cat">${CATS[e.category]}</span>
            <span>${e.date}</span>
            ${e.tickers.map((t) => `<span class="badge ticker">${esc(t)}</span>`).join('')}
            ${e.source ? `<span class="badge src">${esc(e.source)}</span>` : ''}
          </div>
          <h1>${esc(e.title)}</h1>
          ${e.tags.length ? `<div class="card-tags">${e.tags.map((t) => `<span class="tag">${esc(t)}</span>`).join('')}</div>` : ''}
        </div>
        <div class="md">${marked.parse(e.body)}</div>
      </div>`;
    window.scrollTo(0, 0);
  }

  /* ── 卡片 ── */
  function cardHTML(e, terms) {
    let excerpt = e.excerpt;
    if (terms && terms.length) {
      // 搜索时显示第一个命中词附近的片段并高亮
      const low = e.body.toLowerCase();
      const idx = low.indexOf(terms[0]);
      if (idx >= 0) {
        const start = Math.max(0, idx - 40);
        excerpt = (start > 0 ? '…' : '') + e.body.slice(start, idx + 120).replace(/[#*`>\[\]|]/g, '') + '…';
      }
      terms.forEach((t) => {
        excerpt = excerpt.replace(new RegExp('(' + escapeReg(t) + ')', 'gi'), '\x01$1\x02');
      });
      excerpt = esc(excerpt).replaceAll('\x01', '<mark>').replaceAll('\x02', '</mark>');
    } else {
      excerpt = esc(excerpt);
    }
    return `
      <a class="card" href="#/a/${e.id}">
        <div class="card-meta">
          <span class="badge cat">${CATS[e.category]}</span>
          <span>${e.date}</span>
          ${e.tickers.slice(0, 4).map((t) => `<span class="badge ticker">${esc(t)}</span>`).join('')}
        </div>
        <div class="card-title">${esc(e.title)}</div>
        <div class="card-excerpt">${excerpt}</div>
        ${e.tags.length ? `<div class="card-tags">${e.tags.map((t) => `<span class="tag">${esc(t)}</span>`).join('')}</div>` : ''}
      </a>`;
  }

  function esc(s) {
    return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }
  function escapeReg(s) {
    return s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  }
})();
