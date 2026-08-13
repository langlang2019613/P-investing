/* 飘投资研究库 — 前端逻辑：加载 data.json、hash 路由、分类、全文搜索、文章渲染 */
(function () {
  'use strict';

  const CATS = {
    companies: '公司研究',
    industries: '行业研究',
    options: '期权研究',
    macro: '宏观经济',
    reports: '研报分析',
    interviews: '访谈',
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
  let MOMENTUM = null;
  let momentumPromise = null;
  let momentumInputTimer = null;
  const momentumState = {
    mode: 'market',
    query: '',
    sector: '',
    signal: '',
    stage: '',
    minScore: '',
    minMarketCap: '',
    maxPe: '',
    minRevenueGrowth: '',
    minRet20: '',
    sort: 'momentumRank',
    order: 'asc',
    page: 1,
    perPage: 50,
  };

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
    if (h === '#/momentum') return renderMomentum();
    $main.classList.remove('wide');
    if (mArticle) return renderArticle(mArticle[1]);
    if (mCat && CATS[mCat[1]]) return renderCategory(mCat[1]);
    if (mSearch) { $search.value = mSearch[1]; return renderSearch(mSearch[1]); }
    renderHome();
  }

  function setTab(cat) {
    let active = null;
    $tabs.querySelectorAll('a').forEach((a) => {
      const selected = a.dataset.cat === cat;
      a.classList.toggle('active', selected);
      if (selected) active = a;
    });
    if (active) requestAnimationFrame(() => active.scrollIntoView({ block: 'nearest', inline: 'center' }));
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

  /* ── 视图：动量追踪 ── */
  function loadMomentum() {
    if (MOMENTUM) return Promise.resolve(MOMENTUM);
    if (!momentumPromise) {
      momentumPromise = fetch('momentum.json', { cache: 'no-store' })
        .then((response) => {
          if (!response.ok) throw new Error(`HTTP ${response.status}`);
          return response.json();
        })
        .then((data) => (MOMENTUM = data))
        .finally(() => { momentumPromise = null; });
    }
    return momentumPromise;
  }

  function renderMomentum() {
    setTab('momentum');
    $main.classList.add('wide');
    if (!MOMENTUM) {
      $main.innerHTML = '<div class="loading">正在加载动量数据…</div>';
      loadMomentum()
        .then(() => {
          if (decodeURIComponent(location.hash) === '#/momentum') renderMomentum();
        })
        .catch(() => {
          $main.innerHTML = '<div class="empty">动量数据加载失败，请稍后刷新重试。</div>';
        });
      return;
    }

    const rows = filteredMomentumRows();
    const pageCount = Math.max(1, Math.ceil(rows.length / momentumState.perPage));
    momentumState.page = Math.min(momentumState.page, pageCount);
    const start = (momentumState.page - 1) * momentumState.perPage;
    const visible = rows.slice(start, start + momentumState.perPage);
    const sectors = [...new Set(MOMENTUM.rows.map((row) => row.sector).filter(Boolean))].sort();
    const isMarket = momentumState.mode === 'market';
    const scoreField = isMarket ? 'momentumScore' : 'fundamentalScore';
    const strongCount = MOMENTUM.rows.filter((row) => (row[scoreField] || 0) >= (isMarket ? 65 : 60)).length;
    const benchmark = MOMENTUM.benchmark || {};
    const filterFields = `
      <label>行业<select data-filter="sector"><option value="">全部行业</option>${sectors.map((sector) => `<option value="${esc(sector)}" ${momentumState.sector === sector ? 'selected' : ''}>${esc(sector)}</option>`).join('')}</select></label>
      <label>${isMarket ? '信号' : '状态'}<select data-filter="signal"><option value="">全部</option>${momentumLabels(isMarket).map((label) => `<option value="${esc(label)}" ${momentumState.signal === label ? 'selected' : ''}>${esc(label)}</option>`).join('')}</select></label>
      ${isMarket ? `<label>阶段<select data-filter="stage"><option value="">全部</option>${['主升', '上升', '整理', '下行'].map((label) => `<option value="${label}" ${momentumState.stage === label ? 'selected' : ''}>${label}</option>`).join('')}</select></label>` : ''}
      <label>最低综合分<input data-filter="minScore" type="number" min="0" max="100" step="1" value="${esc(momentumState.minScore)}" placeholder="0–100"></label>
      <label>最低市值（十亿美元）<input data-filter="minMarketCap" type="number" min="0" step="1" value="${esc(momentumState.minMarketCap)}" placeholder="例如 10"></label>
      ${isMarket ? `<label>最低 20 日涨幅（%）<input data-filter="minRet20" type="number" step="1" value="${esc(momentumState.minRet20)}" placeholder="例如 0"></label>` : `<label>最低收入增速（%）<input data-filter="minRevenueGrowth" type="number" step="1" value="${esc(momentumState.minRevenueGrowth)}" placeholder="例如 10"></label><label>最高 P/E<input data-filter="maxPe" type="number" min="0" step="1" value="${esc(momentumState.maxPe)}" placeholder="例如 40"></label>`}
    `;

    $main.innerHTML = `
      <section class="momentum-hero">
        <div>
          <p class="eyebrow">PUBLIC-DATA SIGNAL LAB</p>
          <h1>动量追踪</h1>
          <p>量价趋势与已报告基本面的交叉筛选器。每日自动刷新，点击任意股票查看完整指标。</p>
        </div>
        <div class="momentum-asof"><span>数据日期</span><strong>${esc(MOMENTUM.asOf || '—')}</strong><small>${esc(formatGeneratedAt(MOMENTUM.generatedAt))}</small></div>
      </section>
      <div class="momentum-kpis">
        <div><span>已筛选</span><strong>${MOMENTUM.universe.screened}</strong><small>只股票</small></div>
        <div><span>${isMarket ? '偏强及以上' : '稳健及以上'}</span><strong>${strongCount}</strong><small>${isMarket ? '分数 ≥ 65' : '分数 ≥ 60'}</small></div>
        <div><span>SPY 20 日</span><strong class="${valueClass(benchmark.ret20)}">${fmtPct(benchmark.ret20)}</strong><small>相对强弱基准</small></div>
        <div><span>财务覆盖</span><strong>${MOMENTUM.coverage.fundamentals}</strong><small>/ ${MOMENTUM.coverage.price}</small></div>
      </div>
      <div class="momentum-tabs" role="tablist">
        <button data-mode="market" class="${isMarket ? 'active' : ''}">量价动量雷达<small>趋势 · 相对强弱 · 量能</small></button>
        <button data-mode="fundamental" class="${!isMarket ? 'active' : ''}">基本面动量榜<small>增长 · 质量 · 估值</small></button>
      </div>
      <section class="momentum-controls">
        <div class="momentum-search-row">
          <label class="momentum-query">搜索<input data-filter="query" type="search" value="${esc(momentumState.query)}" placeholder="代码、公司、行业"></label>
          <button id="momentum-reset" type="button">重置筛选</button>
          <button id="momentum-export" type="button">导出 CSV</button>
        </div>
        <div class="momentum-filter-grid">${filterFields}</div>
      </section>
      <div class="momentum-resultbar">
        <span>显示 <strong>${rows.length}</strong> / ${MOMENTUM.rows.length} 只</span>
        <span>点击表头排序 · 点击股票展开明细</span>
      </div>
      <div class="momentum-table-wrap">
        <table class="momentum-table">
          ${momentumTableHead(isMarket)}
          <tbody>${visible.map((row) => momentumRow(row, isMarket)).join('') || '<tr><td colspan="15" class="empty-cell">没有符合当前条件的股票</td></tr>'}</tbody>
        </table>
      </div>
      <div class="momentum-pagination">
        <button data-page="prev" ${momentumState.page <= 1 ? 'disabled' : ''}>上一页</button>
        <span>第 ${momentumState.page} / ${pageCount} 页</span>
        <button data-page="next" ${momentumState.page >= pageCount ? 'disabled' : ''}>下一页</button>
        <select id="momentum-per-page" aria-label="每页行数">${[25, 50, 100].map((size) => `<option value="${size}" ${momentumState.perPage === size ? 'selected' : ''}>每页 ${size}</option>`).join('')}</select>
      </div>
      <details class="momentum-method">
        <summary>数据来源、计算口径与风险提示</summary>
        <p><strong>量价动量：</strong>${esc(MOMENTUM.methodology.momentum)}</p>
        <p><strong>基本面动量：</strong>${esc(MOMENTUM.methodology.fundamental)}</p>
        <p>${esc(MOMENTUM.methodology.notice)}</p>
        <p>来源：${(MOMENTUM.sources || []).map((source) => `<a href="${esc(source.url)}" target="_blank" rel="noopener">${esc(source.name)}</a>`).join(' · ')}</p>
      </details>`;
    bindMomentumEvents(rows);
  }

  function filteredMomentumRows() {
    const isMarket = momentumState.mode === 'market';
    const scoreField = isMarket ? 'momentumScore' : 'fundamentalScore';
    const statusField = isMarket ? 'signal' : 'fundamentalStatus';
    const query = momentumState.query.trim().toLowerCase();
    const minScore = nullableNumber(momentumState.minScore);
    const minMarketCap = nullableNumber(momentumState.minMarketCap);
    const maxPe = nullableNumber(momentumState.maxPe);
    const minRevenueGrowth = nullableNumber(momentumState.minRevenueGrowth);
    const minRet20 = nullableNumber(momentumState.minRet20);
    const rows = MOMENTUM.rows.filter((row) => {
      const haystack = `${row.symbol} ${row.name} ${row.sector} ${row.industry}`.toLowerCase();
      if (query && !haystack.includes(query)) return false;
      if (momentumState.sector && row.sector !== momentumState.sector) return false;
      if (momentumState.signal && row[statusField] !== momentumState.signal) return false;
      if (isMarket && momentumState.stage && row.stage !== momentumState.stage) return false;
      if (minScore !== null && (row[scoreField] === null || row[scoreField] < minScore)) return false;
      if (minMarketCap !== null && (row.marketCap === null || row.marketCap < minMarketCap * 1e9)) return false;
      if (maxPe !== null && (row.pe === null || row.pe > maxPe || row.pe <= 0)) return false;
      if (minRevenueGrowth !== null && (row.revenueGrowth === null || row.revenueGrowth < minRevenueGrowth)) return false;
      if (minRet20 !== null && (row.ret20 === null || row.ret20 < minRet20)) return false;
      return true;
    });
    return rows.sort((a, b) => compareMomentum(a, b, momentumState.sort, momentumState.order));
  }

  function momentumLabels(isMarket) {
    return isMarket ? ['强势', '偏强', '中性', '转弱', '弱势', '数据不足'] : ['高质量扩张', '稳健增长', '中性观察', '基本面承压', '数据不足'];
  }

  function momentumTableHead(isMarket) {
    const columns = isMarket
      ? [['momentumRank', '#'], ['symbol', '代码'], ['name', '公司'], ['sector', '行业'], ['price', '价格'], ['ret1', '1日'], ['ret20', '20日'], ['ret60', '60日'], ['ret120', '120日'], ['relative20', '相对SPY'], ['volumeRatio', '量比'], ['distMa200', '距MA200'], ['momentumScore', '综合分'], ['signal', '信号']]
      : [['fundamentalRank', '#'], ['symbol', '代码'], ['name', '公司'], ['sector', '行业'], ['marketCap', '市值'], ['revenueGrowth', '收入增速'], ['revenueCagr3', '3年CAGR'], ['epsGrowth', 'EPS增速'], ['netMargin', '净利率'], ['fcfMargin', 'FCF率'], ['roic', 'ROIC'], ['debtEquity', '负债/权益'], ['pe', 'P/E'], ['fundamentalScore', '综合分'], ['fundamentalStatus', '状态']];
    return `<thead><tr>${columns.map(([field, label]) => `<th data-sort="${field}" class="${momentumState.sort === field ? 'sorted' : ''}">${label}${momentumState.sort === field ? (momentumState.order === 'asc' ? ' ↑' : ' ↓') : ''}</th>`).join('')}</tr></thead>`;
  }

  function momentumRow(row, isMarket) {
    const rank = isMarket ? row.momentumRank : row.fundamentalRank;
    const rankChange = isMarket ? row.momentumRankChange : row.fundamentalRankChange;
    const cells = isMarket
      ? [
          rankCell(rank, rankChange), symbolCell(row), nameCell(row), `<td>${esc(row.sector)}</td>`, `<td>${fmtMoney(row.price, row.currency)}</td>`,
          metricCell(row.ret1, 'pct'), metricCell(row.ret20, 'pct'), metricCell(row.ret60, 'pct'), metricCell(row.ret120, 'pct'),
          metricCell(row.relative20, 'pct'), metricCell(row.volumeRatio, 'ratio'), metricCell(row.distMa200, 'pct'),
          scoreCell(row.momentumScore), signalCell(row.signal),
        ]
      : [
          rankCell(rank, rankChange), symbolCell(row), nameCell(row), `<td>${esc(row.sector)}</td>`, `<td>${fmtMarketCap(row.marketCap)}</td>`,
          metricCell(row.revenueGrowth, 'pct'), metricCell(row.revenueCagr3, 'pct'), metricCell(row.epsGrowth, 'pct'),
          metricCell(row.netMargin, 'pct'), metricCell(row.fcfMargin, 'pct'), metricCell(row.roic, 'pct'),
          metricCell(row.debtEquity, 'ratio'), metricCell(row.pe, 'multiple'), scoreCell(row.fundamentalScore), signalCell(row.fundamentalStatus),
        ];
    return `<tr class="momentum-data-row" data-symbol="${esc(row.symbol)}" tabindex="0">${cells.join('')}</tr><tr class="momentum-detail-row" data-detail="${esc(row.symbol)}" hidden><td colspan="15">${momentumDetail(row)}</td></tr>`;
  }

  function momentumDetail(row) {
    return `<div class="momentum-detail">
      <div class="spark-card"><span>近 60 个交易日</span>${sparkline(row.sparkline || [])}</div>
      <dl>
        <div><dt>交易所</dt><dd>${esc(row.exchange || '—')}</dd></div>
        <div><dt>20日波动率</dt><dd>${fmtPct(row.volatility20)}</dd></div>
        <div><dt>距52周高点</dt><dd>${fmtPct(row.fromHigh52)}</dd></div>
        <div><dt>距MA20 / MA50 / MA200</dt><dd>${fmtPct(row.distMa20)} / ${fmtPct(row.distMa50)} / ${fmtPct(row.distMa200)}</dd></div>
        <div><dt>营业利润率</dt><dd>${fmtPct(row.operatingMargin)}</dd></div>
        <div><dt>P/S</dt><dd>${fmtMultiple(row.ps)}</dd></div>
      </dl>
      <p><strong>${esc(row.symbol)}</strong> 当前处于“${esc(row.stage)}”阶段；量价分 ${fmtNumber(row.momentumScore, 1)}，基本面分 ${fmtNumber(row.fundamentalScore, 1)}。分数是同一股票池内的横截面相对值，不是目标价或买卖建议。</p>
    </div>`;
  }

  function bindMomentumEvents(currentRows) {
    $main.querySelectorAll('[data-mode]').forEach((button) => button.addEventListener('click', () => {
      momentumState.mode = button.dataset.mode;
      momentumState.signal = '';
      momentumState.stage = '';
      momentumState.sort = momentumState.mode === 'market' ? 'momentumRank' : 'fundamentalRank';
      momentumState.order = 'asc';
      momentumState.page = 1;
      renderMomentum();
    }));
    $main.querySelectorAll('[data-filter]').forEach((control) => {
      const event = control.tagName === 'SELECT' ? 'change' : 'input';
      control.addEventListener(event, () => {
        momentumState[control.dataset.filter] = control.value;
        momentumState.page = 1;
        clearTimeout(momentumInputTimer);
        momentumInputTimer = setTimeout(renderMomentum, event === 'input' ? 180 : 0);
      });
    });
    $main.querySelectorAll('th[data-sort]').forEach((header) => header.addEventListener('click', () => {
      const field = header.dataset.sort;
      if (momentumState.sort === field) momentumState.order = momentumState.order === 'asc' ? 'desc' : 'asc';
      else {
        momentumState.sort = field;
        momentumState.order = ['symbol', 'name', 'sector', 'signal', 'fundamentalStatus'].includes(field) ? 'asc' : 'desc';
      }
      momentumState.page = 1;
      renderMomentum();
    }));
    $main.querySelectorAll('.momentum-data-row').forEach((row) => {
      const toggle = () => {
        const detail = $main.querySelector(`[data-detail="${cssEsc(row.dataset.symbol)}"]`);
        if (detail) detail.hidden = !detail.hidden;
      };
      row.addEventListener('click', toggle);
      row.addEventListener('keydown', (event) => { if (event.key === 'Enter' || event.key === ' ') toggle(); });
    });
    $main.querySelectorAll('[data-page]').forEach((button) => button.addEventListener('click', () => {
      momentumState.page += button.dataset.page === 'next' ? 1 : -1;
      renderMomentum();
      window.scrollTo({ top: 250, behavior: 'smooth' });
    }));
    document.getElementById('momentum-per-page').addEventListener('change', (event) => {
      momentumState.perPage = Number(event.target.value);
      momentumState.page = 1;
      renderMomentum();
    });
    document.getElementById('momentum-reset').addEventListener('click', () => {
      Object.assign(momentumState, {
        query: '', sector: '', signal: '', stage: '', minScore: '', minMarketCap: '', maxPe: '',
        minRevenueGrowth: '', minRet20: '', page: 1,
        sort: momentumState.mode === 'market' ? 'momentumRank' : 'fundamentalRank', order: 'asc',
      });
      renderMomentum();
    });
    document.getElementById('momentum-export').addEventListener('click', () => exportMomentumCsv(currentRows));
  }

  function compareMomentum(a, b, field, order) {
    const left = a[field];
    const right = b[field];
    if (left === null || left === undefined) return 1;
    if (right === null || right === undefined) return -1;
    const result = typeof left === 'number' && typeof right === 'number'
      ? left - right
      : String(left).localeCompare(String(right), 'zh-CN', { numeric: true });
    return order === 'asc' ? result : -result;
  }

  function exportMomentumCsv(rows) {
    const fields = momentumState.mode === 'market'
      ? ['momentumRank', 'symbol', 'name', 'sector', 'industry', 'price', 'ret1', 'ret5', 'ret20', 'ret60', 'ret120', 'ret252', 'relative20', 'volumeRatio', 'volatility20', 'distMa20', 'distMa50', 'distMa200', 'fromHigh52', 'momentumScore', 'signal', 'stage']
      : ['fundamentalRank', 'symbol', 'name', 'sector', 'industry', 'marketCap', 'revenueGrowth', 'revenueCagr3', 'epsGrowth', 'netMargin', 'operatingMargin', 'fcfMargin', 'roic', 'debtEquity', 'pe', 'ps', 'fundamentalScore', 'fundamentalStatus'];
    const csv = [fields.join(','), ...rows.map((row) => fields.map((field) => csvCell(row[field])).join(','))].join('\r\n');
    const blob = new Blob(['\ufeff' + csv], { type: 'text/csv;charset=utf-8' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = `p-investing-${momentumState.mode}-${MOMENTUM.asOf}.csv`;
    link.click();
    URL.revokeObjectURL(link.href);
  }

  function sparkline(values) {
    if (!values.length) return '<span class="no-data">—</span>';
    const min = Math.min(...values), max = Math.max(...values), spread = max - min || 1;
    const points = values.map((value, index) => `${(index / Math.max(1, values.length - 1) * 240).toFixed(1)},${(56 - (value - min) / spread * 48).toFixed(1)}`).join(' ');
    const up = values[values.length - 1] >= values[0];
    return `<svg viewBox="0 0 240 64" role="img" aria-label="近60日价格走势"><polyline points="${points}" fill="none" stroke="${up ? '#22c55e' : '#ef4444'}" stroke-width="2" vector-effect="non-scaling-stroke"/></svg>`;
  }

  function rankCell(rank, change) {
    const changeText = change === null || change === undefined ? 'NEW' : change === 0 ? '—' : `${change > 0 ? '↑' : '↓'}${Math.abs(change)}`;
    return `<td class="rank-cell"><strong>${rank || '—'}</strong><small class="${valueClass(change)}">${changeText}</small></td>`;
  }
  function symbolCell(row) { return `<td><strong class="symbol">${esc(row.symbol)}</strong><small>${esc(row.exchange || '')}</small></td>`; }
  function nameCell(row) { return `<td class="company-cell"><strong>${esc(row.name)}</strong><small>${esc(row.industry)}</small></td>`; }
  function scoreCell(value) { return `<td><strong class="score-pill ${scoreClass(value)}">${fmtNumber(value, 1)}</strong></td>`; }
  function signalCell(label) { return `<td><span class="signal ${signalClass(label)}">${esc(label || '—')}</span></td>`; }
  function metricCell(value, type) {
    let display = fmtNumber(value);
    if (type === 'pct') display = fmtPct(value);
    if (type === 'ratio') display = value === null || value === undefined ? '—' : `${fmtNumber(value)}x`;
    if (type === 'multiple') display = fmtMultiple(value);
    return `<td class="${type === 'pct' ? valueClass(value) : ''}">${display}</td>`;
  }
  function nullableNumber(value) { const parsed = Number(value); return value === '' || !Number.isFinite(parsed) ? null : parsed; }
  function fmtNumber(value, digits = 2) { return value === null || value === undefined || !Number.isFinite(Number(value)) ? '—' : Number(value).toLocaleString('zh-CN', { maximumFractionDigits: digits }); }
  function fmtPct(value) { return value === null || value === undefined || !Number.isFinite(Number(value)) ? '—' : `${Number(value) > 0 ? '+' : ''}${fmtNumber(value)}%`; }
  function fmtMultiple(value) { return value === null || value === undefined || !Number.isFinite(Number(value)) ? '—' : `${fmtNumber(value)}x`; }
  function fmtMoney(value, currency) { return value === null || value === undefined ? '—' : `${currency === 'USD' ? '$' : ''}${fmtNumber(value)}`; }
  function fmtMarketCap(value) { if (value === null || value === undefined) return '—'; return value >= 1e12 ? `$${fmtNumber(value / 1e12, 1)}T` : `$${fmtNumber(value / 1e9, 1)}B`; }
  function valueClass(value) { return Number(value) > 0 ? 'positive' : Number(value) < 0 ? 'negative' : '' ; }
  function scoreClass(value) { return Number(value) >= 75 ? 'high' : Number(value) >= 50 ? 'mid' : 'low'; }
  function signalClass(label) { return /强势|偏强|高质量|稳健/.test(label || '') ? 'positive' : /转弱|弱势|承压/.test(label || '') ? 'negative' : 'neutral'; }
  function formatGeneratedAt(value) { if (!value) return ''; const date = new Date(value); return Number.isNaN(date.getTime()) ? '' : `生成于 ${date.toLocaleString('zh-CN', { hour12: false })}`; }
  function csvCell(value) { const text = value === null || value === undefined ? '' : String(value); return /[",\r\n]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text; }
  function cssEsc(value) { return window.CSS && CSS.escape ? CSS.escape(value) : String(value).replace(/[^a-zA-Z0-9_-]/g, '\\$&'); }

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
