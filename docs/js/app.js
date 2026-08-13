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
  const TENX_MODEL_STORAGE_KEY = 'p-investing-tenx-model-v1';
  const TENX_MODEL_DEFAULTS = Object.freeze({
    preset: 'default',
    research: { quality: 60, catalyst: 25, momentum: 15 },
    quality: { growth: 25, business: 45, financial: 10, capital: 10, confidence: 10 },
    risk: { valuation: 8, leverage: 6, negativeFcf: 6 },
  });
  const TENX_MODEL_PRESETS = {
    default: {
      label: '原版平衡',
      description: '经营质量为主，兼顾催化和连续动量。',
      research: { quality: 60, catalyst: 25, momentum: 15 },
      quality: { growth: 25, business: 45, financial: 10, capital: 10, confidence: 10 },
    },
    growth: {
      label: '成长优先',
      description: '提高收入与盈利成长的影响，适合寻找扩张期公司。',
      research: { quality: 70, catalyst: 20, momentum: 10 },
      quality: { growth: 50, business: 25, financial: 5, capital: 10, confidence: 10 },
    },
    quality: {
      label: '质量优先',
      description: '更重视利润、现金流、资本回报和财务稳健。',
      research: { quality: 75, catalyst: 15, momentum: 10 },
      quality: { growth: 15, business: 45, financial: 15, capital: 20, confidence: 5 },
    },
    catalyst: {
      label: '催化动量',
      description: '提高 Alpha 催化与市场确认，排名对价格变化更敏感。',
      research: { quality: 35, catalyst: 35, momentum: 30 },
      quality: { growth: 30, business: 35, financial: 10, capital: 15, confidence: 10 },
    },
  };
  let tenxModel = loadTenxModel();
  let tenxModelCache = { key: '', rows: [] };
  const momentumState = {
    mode: 'tenx',
    query: '',
    sector: '',
    signal: '',
    stage: '',
    minScore: '',
    minMarketCap: '',
    maxPe: '',
    minRevenueGrowth: '',
    minRet20: '',
    sort: 'researchPriorityRank',
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
    const mMomentum = h.match(/^#\/momentum\/(tenx|movement)$/);
    if (mMomentum) return renderMomentum(mMomentum[1]);
    if (h === '#/momentum') { location.hash = '#/momentum/tenx'; return; }
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

  function copyTenxModel(source) {
    const safeNumber = (value, fallback, max) => {
      const parsed = Number(value);
      return Number.isFinite(parsed) ? Math.max(0, Math.min(max, parsed)) : fallback;
    };
    const sourceResearch = source && source.research || {};
    const sourceQuality = source && source.quality || {};
    const sourceRisk = source && source.risk || {};
    return {
      preset: source && typeof source.preset === 'string' ? source.preset : 'default',
      research: {
        quality: safeNumber(sourceResearch.quality, 60, 100),
        catalyst: safeNumber(sourceResearch.catalyst, 25, 100),
        momentum: safeNumber(sourceResearch.momentum, 15, 100),
      },
      quality: {
        growth: safeNumber(sourceQuality.growth, 25, 100),
        business: safeNumber(sourceQuality.business, 45, 100),
        financial: safeNumber(sourceQuality.financial, 10, 100),
        capital: safeNumber(sourceQuality.capital, 10, 100),
        confidence: safeNumber(sourceQuality.confidence, 10, 100),
      },
      risk: {
        valuation: safeNumber(sourceRisk.valuation, 8, 25),
        leverage: safeNumber(sourceRisk.leverage, 6, 25),
        negativeFcf: safeNumber(sourceRisk.negativeFcf, 6, 25),
      },
    };
  }

  function loadTenxModel() {
    try {
      const saved = localStorage.getItem(TENX_MODEL_STORAGE_KEY);
      return copyTenxModel(saved ? JSON.parse(saved) : TENX_MODEL_DEFAULTS);
    } catch (_) {
      return copyTenxModel(TENX_MODEL_DEFAULTS);
    }
  }

  function saveTenxModel() {
    tenxModelCache.key = '';
    try { localStorage.setItem(TENX_MODEL_STORAGE_KEY, JSON.stringify(tenxModel)); } catch (_) { /* private mode */ }
  }

  function tenxModelIsDefault() {
    return ['research', 'quality', 'risk'].every((group) =>
      Object.keys(TENX_MODEL_DEFAULTS[group]).every((key) =>
        Number(tenxModel[group][key]) === Number(TENX_MODEL_DEFAULTS[group][key])
      )
    );
  }

  function sumWeights(group) {
    return Object.values(tenxModel[group]).reduce((total, value) => total + Number(value || 0), 0);
  }

  function weightedAvailable(parts) {
    const present = parts.filter(([value, weight]) => value !== null && value !== undefined && Number.isFinite(Number(value)) && Number(weight) > 0);
    const total = present.reduce((sum, item) => sum + Number(item[1]), 0);
    if (!present.length || total <= 0) return null;
    return present.reduce((sum, item) => sum + Number(item[0]) * Number(item[1]), 0) / total;
  }

  function sortedPopulation(rows, key, sector) {
    return rows
      .filter((row) => !sector || row.sector === sector)
      .map((row) => Number(row[key]))
      .filter((value) => Number.isFinite(value) && (key !== 'pe' || value > 0))
      .sort((a, b) => a - b);
  }

  function percentileScore(value, population, inverse) {
    const numeric = Number(value);
    if (!Number.isFinite(numeric) || !population.length) return null;
    let below = 0, equal = 0;
    population.forEach((candidate) => {
      if (candidate < numeric) below += 1;
      else if (candidate === numeric) equal += 1;
    });
    const rank = (below + Math.max(0, equal - 1) / 2) / Math.max(1, population.length - 1) * 100;
    return inverse ? 100 - rank : rank;
  }

  function tenxComponentRows() {
    const rawRows = MOMENTUM.rows || [];
    const metrics = ['revenueGrowth', 'revenueCagr3', 'epsGrowth', 'fcfMargin', 'roic', 'netMargin', 'debtEquity', 'fcfYield'];
    const globalPopulations = Object.fromEntries(metrics.map((key) => [key, sortedPopulation(rawRows, key)]));
    const sectorPopulations = {};
    [...new Set(rawRows.map((row) => row.sector).filter(Boolean))].forEach((sector) => {
      sectorPopulations[sector] = Object.fromEntries(metrics.map((key) => [key, sortedPopulation(rawRows, key, sector)]));
    });
    const score = (row, key, inverse) => {
      const sectorValues = sectorPopulations[row.sector] && sectorPopulations[row.sector][key] || [];
      return percentileScore(row[key], sectorValues.length >= 5 ? sectorValues : globalPopulations[key], inverse);
    };
    return rawRows.map((row) => {
      const coverageKeys = ['revenueGrowth', 'revenueCagr3', 'epsGrowth', 'fcfMargin', 'roic', 'netMargin', 'debtEquity', 'pe'];
      const coverage = coverageKeys.filter((key) => row[key] !== null && row[key] !== undefined && Number.isFinite(Number(row[key]))).length / coverageKeys.length * 100;
      const growth = weightedAvailable([[score(row, 'revenueGrowth'), 40], [score(row, 'revenueCagr3'), 30], [score(row, 'epsGrowth'), 30]]);
      const business = weightedAvailable([[score(row, 'fcfMargin'), 35], [score(row, 'roic'), 35], [score(row, 'netMargin'), 30]]);
      const financial = weightedAvailable([[score(row, 'debtEquity', true), 70], [score(row, 'fcfMargin'), 30]]);
      const capital = weightedAvailable([[score(row, 'roic'), 70], [score(row, 'fcfYield'), 30]]);
      const alpha = row.davisDouble === '双重确认' ? 100 : row.alphaCatalyst === '是' ? 65 : 25;
      return { row, components: { growth, business, financial, capital, confidence: coverage }, alpha };
    });
  }

  function tenxRowsForModel() {
    if (tenxModelIsDefault()) return MOMENTUM.rows;
    const cacheKey = `${MOMENTUM.generatedAt || ''}|${JSON.stringify(tenxModel)}`;
    if (tenxModelCache.key === cacheKey) return tenxModelCache.rows;
    const research = sumWeights('research') > 0 ? tenxModel.research : TENX_MODEL_DEFAULTS.research;
    const quality = sumWeights('quality') > 0 ? tenxModel.quality : TENX_MODEL_DEFAULTS.quality;
    const risk = tenxModel.risk;
    const rows = tenxComponentRows().map(({ row, components, alpha }) => {
      const customQualityModel = weightedAvailable([
        [components.growth, quality.growth],
        [components.business, quality.business],
        [components.financial, quality.financial],
        [components.capital, quality.capital],
        [components.confidence, quality.confidence],
      ]) || 0;
      const defaultQualityModel = weightedAvailable([
        [components.growth, TENX_MODEL_DEFAULTS.quality.growth],
        [components.business, TENX_MODEL_DEFAULTS.quality.business],
        [components.financial, TENX_MODEL_DEFAULTS.quality.financial],
        [components.capital, TENX_MODEL_DEFAULTS.quality.capital],
        [components.confidence, TENX_MODEL_DEFAULTS.quality.confidence],
      ]) || 0;
      const publishedQuality = Number.isFinite(Number(row.fundamentalScore)) ? Number(row.fundamentalScore) : defaultQualityModel;
      const quality100 = Math.max(0, Math.min(100, publishedQuality + customQualityModel - defaultQualityModel));
      let riskPenalty = 0;
      let defaultRiskPenalty = 0;
      if ((row.pe || 0) > 100) riskPenalty += risk.valuation;
      if ((row.pe || 0) > 100) defaultRiskPenalty += TENX_MODEL_DEFAULTS.risk.valuation;
      if ((row.debtEquity || 0) > 3) riskPenalty += risk.leverage;
      if ((row.debtEquity || 0) > 3) defaultRiskPenalty += TENX_MODEL_DEFAULTS.risk.leverage;
      if (row.fcfMargin !== null && row.fcfMargin !== undefined && row.fcfMargin < 0) riskPenalty += risk.negativeFcf;
      if (row.fcfMargin !== null && row.fcfMargin !== undefined && row.fcfMargin < 0) defaultRiskPenalty += TENX_MODEL_DEFAULTS.risk.negativeFcf;
      const customResearchModel = weightedAvailable([
        [quality100, research.quality],
        [alpha, research.catalyst],
        [row.momentumScore, research.momentum],
      ]) || 0;
      const defaultResearchModel = weightedAvailable([
        [publishedQuality, TENX_MODEL_DEFAULTS.research.quality],
        [alpha, TENX_MODEL_DEFAULTS.research.catalyst],
        [row.momentumScore, TENX_MODEL_DEFAULTS.research.momentum],
      ]) || 0;
      const publishedResearch = Number.isFinite(Number(row.researchPriorityScore)) ? Number(row.researchPriorityScore) * 20 : defaultResearchModel - defaultRiskPenalty;
      const research100 = Math.max(0, Math.min(100, publishedResearch + customResearchModel - defaultResearchModel - (riskPenalty - defaultRiskPenalty)));
      const result = Object.assign({}, row, {
        _modelComponents: components,
        _modelAlphaScore: alpha,
        _modelRiskPenalty: riskPenalty,
        fundamentalScore: Math.round(quality100 * 10) / 10,
        qualityScore: Math.round(quality100 / 2) / 10,
        researchPriorityScore: Math.round(research100 / 2) / 10,
        currentStatus: research100 >= 75 ? '重点研究' : research100 >= 55 ? '继续跟踪' : '观察',
        watchAction: research100 >= 75 ? '重点研究' : research100 >= 60 ? '继续跟踪' : research100 >= 45 ? '等待确认' : '暂缓',
      });
      result.whyWatch = `自定义模型综合分${result.researchPriorityScore.toFixed(1)}，经营质量分${result.qualityScore.toFixed(1)}，季度趋势为${result.quarterlyTrend || '未覆盖'}，量价信号为${result.signal || '数据不足'}。`;
      return result;
    });
    [...rows].sort((a, b) => b.fundamentalScore - a.fundamentalScore).forEach((row, index) => { row.sectorQualityRank = index + 1; });
    [...rows].sort((a, b) => b.researchPriorityScore - a.researchPriorityScore || (b.momentumScore || 0) - (a.momentumScore || 0)).forEach((row, index) => {
      const baseRank = row.researchPriorityRank;
      row.researchPriorityRank = index + 1;
      row.researchPriorityRankChange = baseRank ? baseRank - row.researchPriorityRank : null;
    });
    tenxModelCache = { key: cacheKey, rows };
    return rows;
  }

  function activeMomentumRows() {
    return momentumState.mode === 'tenx' ? tenxRowsForModel() : MOMENTUM.rows;
  }

  function renderMomentum(mode) {
    if (mode) momentumState.mode = mode;
    setTab(momentumState.mode);
    $main.classList.add('wide');
    if (!MOMENTUM) {
      $main.innerHTML = '<div class="loading">正在加载动量数据…</div>';
      loadMomentum()
        .then(() => {
          if (decodeURIComponent(location.hash).startsWith('#/momentum/')) renderMomentum();
        })
        .catch(() => {
          $main.innerHTML = '<div class="empty">动量数据加载失败，请稍后刷新重试。</div>';
        });
      return;
    }

    const allRows = activeMomentumRows();
    const rows = filteredMomentumRows(allRows);
    const pageCount = Math.max(1, Math.ceil(rows.length / momentumState.perPage));
    momentumState.page = Math.min(momentumState.page, pageCount);
    const start = (momentumState.page - 1) * momentumState.perPage;
    const visible = rows.slice(start, start + momentumState.perPage);
    const sectors = [...new Set(allRows.map((row) => row.sector).filter(Boolean))].sort();
    const isTenx = momentumState.mode === 'tenx';
    const schema = momentumSchema();
    const columns = schema.columns || [];
    const computedCount = columns.filter((column) => column.source !== 'licensed').length;
    const licensedCount = columns.length - computedCount;
    const scoreField = isTenx ? 'researchPriorityScore' : 'momentumScore';
    const strongCount = allRows.filter((row) => isTenx ? row.currentStatus === '重点研究' : (row[scoreField] || 0) >= 65).length;
    const benchmark = MOMENTUM.benchmark || {};
    const filterFields = `
      <label>行业<select data-filter="sector"><option value="">全部行业</option>${sectors.map((sector) => `<option value="${esc(sector)}" ${momentumState.sector === sector ? 'selected' : ''}>${esc(sector)}</option>`).join('')}</select></label>
      <label>${isTenx ? '当前状态' : '动量信号'}<select data-filter="signal"><option value="">全部</option>${momentumLabels(isTenx).map((label) => `<option value="${esc(label)}" ${momentumState.signal === label ? 'selected' : ''}>${esc(label)}</option>`).join('')}</select></label>
      ${!isTenx ? `<label>阶段<select data-filter="stage"><option value="">全部</option>${['主升', '上升', '整理', '下行'].map((label) => `<option value="${label}" ${momentumState.stage === label ? 'selected' : ''}>${label}</option>`).join('')}</select></label>` : ''}
      <label>最低综合分<input data-filter="minScore" type="number" min="0" max="${isTenx ? 5 : 100}" step="${isTenx ? .1 : 1}" value="${esc(momentumState.minScore)}" placeholder="${isTenx ? '0–5' : '0–100'}"></label>
      <label>最低市值（十亿美元）<input data-filter="minMarketCap" type="number" min="0" step="1" value="${esc(momentumState.minMarketCap)}" placeholder="例如 10"></label>
      ${isTenx ? `<label>最低收入增速（%）<input data-filter="minRevenueGrowth" type="number" step="1" value="${esc(momentumState.minRevenueGrowth)}" placeholder="例如 10"></label><label>最高 TTM P/E<input data-filter="maxPe" type="number" min="0" step="1" value="${esc(momentumState.maxPe)}" placeholder="例如 40"></label>` : `<label>最低 20 日涨幅（%）<input data-filter="minRet20" type="number" step="1" value="${esc(momentumState.minRet20)}" placeholder="例如 0"></label>`}
    `;

    $main.innerHTML = `
      <section class="momentum-hero">
        <div>
          <p class="eyebrow">PUBLIC-DATA SIGNAL LAB</p>
          <h1>动量追踪</h1>
          <p>拆分为 10 倍股研究优先级与每日动量移动追踪；两个主表完整保留核对版 Excel 的全部 84 项指标。</p>
        </div>
        <div class="momentum-asof"><span>公开数据日期</span><strong>${esc(MOMENTUM.asOf || '—')}</strong><small>${esc(formatGeneratedAt(MOMENTUM.generatedAt))}</small></div>
      </section>
      <div class="momentum-kpis">
        <div><span>已筛选</span><strong>${MOMENTUM.universe.screened}</strong><small>只股票</small></div>
        <div><span>${isTenx ? '优先研究' : '偏强及以上'}</span><strong>${strongCount}</strong><small>${isTenx ? '当前状态 = 重点研究' : '动量分 ≥ 65'}</small></div>
        <div><span>本表指标</span><strong>${columns.length}</strong><small>${computedCount} 自动 · ${licensedCount} 待授权</small></div>
        <div><span>SPY 20 日</span><strong class="${valueClass(benchmark.ret20)}">${fmtPct(benchmark.ret20)}</strong><small>相对强弱基准</small></div>
      </div>
      <div class="momentum-tabs" role="tablist">
        <button data-mode="tenx" class="${isTenx ? 'active' : ''}">10倍股雷达<small>33项 · 增长 · 质量 · 估值 · 催化</small></button>
        <button data-mode="movement" class="${!isTenx ? 'active' : ''}">动量移动追踪<small>51项 · 现货 · 期权 · Gamma · 波动</small></button>
      </div>
      ${isTenx ? tenxModelWorkbench() : ''}
      <section class="momentum-controls">
        <div class="momentum-search-row">
          <label class="momentum-query">搜索<input data-filter="query" type="search" value="${esc(momentumState.query)}" placeholder="代码、公司、行业"></label>
          <button id="momentum-reset" type="button">重置筛选</button>
          <button id="momentum-export" type="button">导出全部指标 CSV</button>
        </div>
        <div class="momentum-filter-grid">${filterFields}</div>
      </section>
      <div class="field-coverage-note">
        <span><i class="source-dot computed"></i>公开数据自动计算 ${computedCount} 项</span>
        <span><i class="source-dot licensed"></i>待合规授权数据源 ${licensedCount} 项</span>
        <span>字段核对 ${esc(MOMENTUM.schemas.auditedAt)} · 参考版本 ${esc(schema.referenceVersion)}</span>
      </div>
      <div class="momentum-resultbar">
        <span>显示 <strong>${rows.length}</strong> / ${allRows.length} 只 · 完整 ${columns.length} 列</span>
        <span>${isTenx && !tenxModelIsDefault() ? '自定义模式：排名变化为相对原版模型 · ' : ''}横向滚动查看全部指标 · 点击表头排序 · 点击股票展开明细</span>
      </div>
      <div class="momentum-table-wrap">
        <table class="momentum-table full-schema" style="min-width:${Math.max(1500, columns.length * 128)}px">
          ${momentumTableHead(columns)}
          <tbody>${visible.map((row) => momentumRow(row, columns)).join('') || `<tr><td colspan="${columns.length}" class="empty-cell">没有符合当前条件的股票</td></tr>`}</tbody>
        </table>
      </div>
      <div class="momentum-pagination">
        <button data-page="prev" ${momentumState.page <= 1 ? 'disabled' : ''}>上一页</button>
        <span>第 ${momentumState.page} / ${pageCount} 页</span>
        <button data-page="next" ${momentumState.page >= pageCount ? 'disabled' : ''}>下一页</button>
        <select id="momentum-per-page" aria-label="每页行数">${[25, 50, 100].map((size) => `<option value="${size}" ${momentumState.perPage === size ? 'selected' : ''}>每页 ${size}</option>`).join('')}</select>
      </div>
      <details class="momentum-method" ${isTenx ? '' : 'open'}>
        <summary>${isTenx ? '数据边界与公开来源' : `${esc(schema.title)}方法论与数据边界`}</summary>
        <p>${esc(isTenx ? MOMENTUM.methodology.tenx : MOMENTUM.methodology.movement)}</p>
        ${isTenx ? '' : methodologyDetails(false)}
        <p>${esc(MOMENTUM.methodology.notice)}</p>
        <p><strong>完整性说明：</strong>所有 Excel 主表字段均已呈现。期权链、Gamma、Reddit 和分析师预期等不能由当前公开源可靠生成的字段显示“待授权源”，避免用猜测值冒充真实指标。</p>
        <p>公开来源：${(MOMENTUM.sources || []).map((source) => `<a href="${esc(source.url)}" target="_blank" rel="noopener">${esc(source.name)}</a>`).join(' · ')}</p>
      </details>
      ${referenceInventory(schema)}`;
    bindMomentumEvents(rows);
  }

  function momentumSchema() {
    return MOMENTUM.schemas[momentumState.mode] || { columns: [], sheets: [] };
  }

  function filteredMomentumRows(sourceRows) {
    const isTenx = momentumState.mode === 'tenx';
    const scoreField = isTenx ? 'researchPriorityScore' : 'momentumScore';
    const statusField = isTenx ? 'currentStatus' : 'signal';
    const query = momentumState.query.trim().toLowerCase();
    const minScore = nullableNumber(momentumState.minScore);
    const minMarketCap = nullableNumber(momentumState.minMarketCap);
    const maxPe = nullableNumber(momentumState.maxPe);
    const minRevenueGrowth = nullableNumber(momentumState.minRevenueGrowth);
    const minRet20 = nullableNumber(momentumState.minRet20);
    const rows = (sourceRows || activeMomentumRows()).filter((row) => {
      const haystack = `${row.symbol} ${row.name} ${row.sector} ${row.industry}`.toLowerCase();
      if (query && !haystack.includes(query)) return false;
      if (momentumState.sector && row.sector !== momentumState.sector) return false;
      if (momentumState.signal && row[statusField] !== momentumState.signal) return false;
      if (!isTenx && momentumState.stage && row.stage !== momentumState.stage) return false;
      if (minScore !== null && (row[scoreField] === null || row[scoreField] < minScore)) return false;
      if (minMarketCap !== null && (row.marketCap === null || row.marketCap < minMarketCap * 1e9)) return false;
      if (maxPe !== null && (row.pe === null || row.pe > maxPe || row.pe <= 0)) return false;
      if (minRevenueGrowth !== null && (row.revenueGrowth === null || row.revenueGrowth < minRevenueGrowth)) return false;
      if (minRet20 !== null && (row.ret20 === null || row.ret20 < minRet20)) return false;
      return true;
    });
    return rows.sort((a, b) => compareMomentum(a, b, momentumState.sort, momentumState.order));
  }

  function momentumLabels(isTenx) {
    return isTenx ? ['重点研究', '继续跟踪', '观察'] : ['强势', '偏强', '中性', '转弱', '弱势', '数据不足'];
  }

  function momentumTableHead(columns) {
    const groups = [];
    columns.forEach((column) => {
      const last = groups[groups.length - 1];
      if (last && last.name === column.group) last.count += 1;
      else groups.push({ name: column.group, count: 1 });
    });
    const groupRow = `<tr class="indicator-groups">${groups.map((group) => `<th colspan="${group.count}">${esc(group.name)}</th>`).join('')}</tr>`;
    const labelRow = `<tr>${columns.map((column) => `<th data-sort="${column.key}" class="${momentumState.sort === column.key ? 'sorted' : ''}" title="${column.source === 'licensed' ? '字段已保留，当前待合规授权数据源' : '公开数据或独立计算'}"><i class="source-dot ${column.source === 'licensed' ? 'licensed' : 'computed'}"></i>${esc(column.label)}${momentumState.sort === column.key ? (momentumState.order === 'asc' ? ' ↑' : ' ↓') : ''}</th>`).join('')}</tr>`;
    return `<thead>${groupRow}${labelRow}</thead>`;
  }

  function momentumRow(row, columns) {
    const cells = columns.map((column) => indicatorCell(row, column));
    return `<tr class="momentum-data-row" data-symbol="${esc(row.symbol)}" tabindex="0">${cells.join('')}</tr><tr class="momentum-detail-row" data-detail="${esc(row.symbol)}" hidden><td colspan="${columns.length}">${momentumDetail(row)}</td></tr>`;
  }

  function momentumDetail(row) {
    const modelBreakdown = row._modelComponents ? `<p class="model-breakdown"><strong>自定义模型拆解：</strong>成长 ${fmtNumber(row._modelComponents.growth, 1)} · 业务质量 ${fmtNumber(row._modelComponents.business, 1)} · 财务强度 ${fmtNumber(row._modelComponents.financial, 1)} · 资本配置 ${fmtNumber(row._modelComponents.capital, 1)} · 数据置信度 ${fmtNumber(row._modelComponents.confidence, 1)} · Alpha ${fmtNumber(row._modelAlphaScore, 1)} · 风险扣分 ${fmtNumber(row._modelRiskPenalty, 1)}</p>` : '';
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
      ${modelBreakdown}
    </div>`;
  }

  function bindMomentumEvents(currentRows) {
    $main.querySelectorAll('[data-mode]').forEach((button) => button.addEventListener('click', () => {
      momentumState.mode = button.dataset.mode;
      momentumState.signal = '';
      momentumState.stage = '';
      momentumState.sort = momentumState.mode === 'tenx' ? 'researchPriorityRank' : 'momentumRank';
      momentumState.order = 'asc';
      momentumState.page = 1;
      location.hash = `#/momentum/${momentumState.mode}`;
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
    $main.querySelectorAll('[data-tenx-group]').forEach((control) => {
      control.addEventListener('input', () => {
        const group = control.dataset.tenxGroup;
        const key = control.dataset.tenxKey;
        tenxModel[group][key] = Number(control.value);
        tenxModel.preset = 'custom';
        const output = $main.querySelector(`[data-tenx-output="${group}.${key}"]`);
        if (output) output.textContent = `${control.value}${group === 'risk' ? '分' : '%'}`;
        const total = $main.querySelector(`[data-tenx-total="${group}"]`);
        if (total) {
          const value = sumWeights(group);
          total.textContent = value <= 0 ? '0% · 回退原版' : `合计 ${value}%`;
          total.classList.toggle('invalid', value <= 0);
        }
        const state = $main.querySelector('.model-state');
        if (state) { state.textContent = '自定义模型'; state.classList.add('custom'); }
      });
      control.addEventListener('change', () => {
        saveTenxModel();
        momentumState.page = 1;
        renderMomentum();
      });
    });
    $main.querySelectorAll('[data-tenx-preset]').forEach((button) => button.addEventListener('click', () => {
      const key = button.dataset.tenxPreset;
      const preset = TENX_MODEL_PRESETS[key];
      if (!preset) return;
      tenxModel = copyTenxModel({ preset: key, research: preset.research, quality: preset.quality, risk: TENX_MODEL_DEFAULTS.risk });
      saveTenxModel();
      momentumState.page = 1;
      momentumState.sort = 'researchPriorityRank';
      momentumState.order = 'asc';
      renderMomentum();
    }));
    const resetModel = document.getElementById('tenx-reset-model');
    if (resetModel) resetModel.addEventListener('click', () => {
      tenxModel = copyTenxModel(TENX_MODEL_DEFAULTS);
      saveTenxModel();
      momentumState.page = 1;
      momentumState.sort = 'researchPriorityRank';
      momentumState.order = 'asc';
      renderMomentum();
    });
    $main.querySelectorAll('th[data-sort]').forEach((header) => header.addEventListener('click', () => {
      const field = header.dataset.sort;
      if (momentumState.sort === field) momentumState.order = momentumState.order === 'asc' ? 'desc' : 'asc';
      else {
        momentumState.sort = field;
        const column = momentumSchema().columns.find((item) => item.key === field);
        momentumState.order = column && ['text', 'symbol', 'company', 'status', 'date'].includes(column.format) ? 'asc' : 'desc';
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
        sort: momentumState.mode === 'tenx' ? 'researchPriorityRank' : 'momentumRank', order: 'asc',
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
    const columns = momentumSchema().columns;
    const csv = [columns.map((column) => csvCell(column.label)).join(','), ...rows.map((row) => columns.map((column) => csvCell(row[column.key])).join(','))].join('\r\n');
    const blob = new Blob(['\ufeff' + csv], { type: 'text/csv;charset=utf-8' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    const modelSuffix = momentumState.mode === 'tenx' && !tenxModelIsDefault() ? '-custom-model' : '';
    link.download = `p-investing-${momentumState.mode}${modelSuffix}-${MOMENTUM.asOf}.csv`;
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
  function indicatorCell(row, column) {
    const value = row[column.key];
    if ((value === null || value === undefined || value === '') && column.source === 'licensed') {
      return '<td class="pending-source"><span>待授权源</span></td>';
    }
    if (column.format === 'symbol') return symbolCell(row);
    if (column.format === 'company') return nameCell(row);
    if (column.format === 'rank') return `<td class="rank-cell"><strong>${fmtNumber(value, 0)}</strong></td>`;
    if (column.format === 'rankChange') {
      const display = value === null || value === undefined ? 'NEW' : value === 0 ? '—' : `${value > 0 ? '↑' : '↓'}${Math.abs(value)}`;
      return `<td class="rank-cell"><small class="${valueClass(value)}">${display}</small></td>`;
    }
    if (column.format === 'marketCap') return `<td>${fmtMarketCap(value)}</td>`;
    if (column.format === 'price') return `<td>${fmtMoney(value, row.currency)}</td>`;
    if (column.format === 'pct') return `<td class="${valueClass(value)}">${fmtPct(value)}</td>`;
    if (column.format === 'ratio') return `<td>${value === null || value === undefined ? '—' : `${fmtNumber(value)}x`}</td>`;
    if (column.format === 'multiple') return `<td>${fmtMultiple(value)}</td>`;
    if (column.format === 'score100') return scoreCell(value);
    if (column.format === 'score5') return `<td><strong class="score-pill ${scoreClass5(value)}">${fmtNumber(value, 1)}</strong></td>`;
    if (column.format === 'status') return signalCell(value);
    if (column.format === 'days') return `<td>${value === null || value === undefined ? '—' : `${fmtNumber(value, 0)}天`}</td>`;
    if (column.format === 'number') return `<td>${fmtNumber(value)}</td>`;
    if (column.format === 'longText') {
      const text = value === null || value === undefined ? '—' : String(value);
      return `<td class="long-cell" title="${esc(text)}">${esc(text)}</td>`;
    }
    return `<td>${esc(value === null || value === undefined ? '—' : value)}</td>`;
  }
  function referenceInventory(schema) {
    const sheets = schema.sheets || [];
    return `<details class="indicator-inventory"><summary>Excel 工作表与全部字段核对清单</summary><div class="inventory-grid">${sheets.map((sheet) => `<section><h3>${esc(sheet.name)}${sheet.count ? ` · ${sheet.count}项` : ''}</h3>${sheet.type === 'methodology' ? '<p>方法论/使用说明页</p>' : sheet.fields ? `<div>${sheet.fields.map((field) => `<span>${esc(field)}</span>`).join('')}</div>` : `<div>${(schema.columns || []).map((field) => `<span>${esc(field.label)}</span>`).join('')}</div>`}</section>`).join('')}</div></details>`;
  }
  function tenxWeightControl(group, key, label, description, max = 100) {
    const value = tenxModel[group][key];
    return `<label class="tenx-weight-row">
      <span><strong>${esc(label)}</strong><small>${esc(description)}</small></span>
      <input type="range" min="0" max="${max}" step="1" value="${value}" data-tenx-group="${group}" data-tenx-key="${key}" aria-label="${esc(label)}">
      <output data-tenx-output="${group}.${key}">${value}${group === 'risk' ? '分' : '%'}</output>
    </label>`;
  }

  function tenxModelWorkbench() {
    const researchTotal = sumWeights('research');
    const qualityTotal = sumWeights('quality');
    const custom = !tenxModelIsDefault();
    return `<section class="tenx-workbench">
      <div class="tenx-workbench-head">
        <div><p class="eyebrow">INTERACTIVE RESEARCH MODEL</p><h2>10倍股权重实验室</h2><p>调整任一滑杆后，松手即重算全部股票的经营质量分、研究优先级分、状态与排名；权重保存在当前浏览器。</p></div>
        <span class="model-state ${custom ? 'custom' : ''}">${custom ? '自定义模型' : '原版模型'}</span>
      </div>
      <div class="tenx-presets" aria-label="模型预设">
        ${Object.entries(TENX_MODEL_PRESETS).map(([key, preset]) => `<button type="button" data-tenx-preset="${key}" class="${tenxModel.preset === key && (key !== 'default' || !custom) ? 'active' : ''}" title="${esc(preset.description)}"><strong>${esc(preset.label)}</strong><small>${esc(preset.description)}</small></button>`).join('')}
        <button type="button" id="tenx-reset-model" class="reset-model"><strong>恢复原版</strong><small>清除本机自定义设置</small></button>
      </div>
      <div class="tenx-model-grid">
        <section class="tenx-weight-card">
          <div class="weight-card-head"><div><h3>① 研究优先级</h3><p>决定最终 0–5 分及先后顺序</p></div><span data-tenx-total="research" class="${researchTotal <= 0 ? 'invalid' : ''}">${researchTotal <= 0 ? '0% · 回退原版' : `合计 ${researchTotal}%`}</span></div>
          ${tenxWeightControl('research', 'quality', '经营质量', '增长、利润、现金流与资本效率')}
          ${tenxWeightControl('research', 'catalyst', 'Alpha 催化', '经营恢复与市场确认的共振')}
          ${tenxWeightControl('research', 'momentum', '市场动量', '连续价格趋势和相对强弱')}
        </section>
        <section class="tenx-weight-card">
          <div class="weight-card-head"><div><h3>② 经营质量五维</h3><p>决定经营质量 0–5 分</p></div><span data-tenx-total="quality" class="${qualityTotal <= 0 ? 'invalid' : ''}">${qualityTotal <= 0 ? '0% · 回退原版' : `合计 ${qualityTotal}%`}</span></div>
          ${tenxWeightControl('quality', 'growth', '成长质量', '收入、三年复合增长、EPS')}
          ${tenxWeightControl('quality', 'business', '业务质量', '利润率、FCF率、ROIC')}
          ${tenxWeightControl('quality', 'financial', '财务强度', '杠杆与现金流韧性')}
          ${tenxWeightControl('quality', 'capital', '资本配置', 'ROIC 与 FCF Yield')}
          ${tenxWeightControl('quality', 'confidence', '数据置信度', '关键公开字段覆盖完整度')}
        </section>
        <section class="tenx-weight-card risk-card">
          <div class="weight-card-head"><div><h3>③ 风险扣分</h3><p>在加权总分之后直接扣减</p></div><span>最高 ${sumWeights('risk')}分</span></div>
          ${tenxWeightControl('risk', 'valuation', '极端估值', 'TTM P/E > 100x', 25)}
          ${tenxWeightControl('risk', 'leverage', '高杠杆', 'Debt/Equity > 3x', 25)}
          ${tenxWeightControl('risk', 'negativeFcf', '负自由现金流', 'FCF Margin < 0', 25)}
          <div class="tenx-formula"><strong>实时公式</strong><code>优先级 = 加权(经营质量, Alpha, 动量) − 风险扣分</code><small>同组权重不必手工凑到 100%，计算时按当前合计自动归一化。自定义结果以当日原版分数为锚点，叠加新旧权重差；若一组全部为 0，该组暂按原版权重计算。</small></div>
        </section>
      </div>
      <div class="tenx-guide-grid">
        <details open>
          <summary>使用指南</summary>
          <ol>
            <li><strong>先选模型：</strong>原版平衡适合建立研究清单；成长优先偏向高速扩张；质量优先偏向现金流与资本回报；催化动量更快响应价格。</li>
            <li><strong>再做微调：</strong>拖动任一权重，松手后全股票池即时重算。调整一层不会隐藏任何原始指标。</li>
            <li><strong>看结果：</strong>优先级分越高，代表“现在越值得先研究”，并不代表未来涨幅或成为十倍股的概率。</li>
            <li><strong>配合筛选：</strong>用行业、市值、收入增速、P/E 和最低综合分缩小范围，再点击股票核对趋势、估值与风险。</li>
            <li><strong>比较排名：</strong>自定义模式下“排名变化”表示相对原版模型上升或下降；原版模式显示每日历史排名变化。</li>
            <li><strong>保存与更新：</strong>参数自动保存在本机浏览器。每日数据更新后会继续套用当前参数；更换设备需重新设置。</li>
          </ol>
        </details>
        <details open>
          <summary>10倍股方法论</summary>
          ${methodologyDetails(true)}
        </details>
      </div>
    </section>`;
  }
  function methodologyDetails(isTenx) {
    if (isTenx) return `
      <div class="methodology-grid">
        <section><h3>研究优先级</h3><p>原版权重为 <code>60% 经营质量 + 25% Alpha 催化 + 15% 连续市场动量 − 风险扣分</code>。三个权重可调整，并按合计自动归一化；新结果以当日原版分数为锚点计算权重差。</p></section>
        <section><h3>经营质量</h3><p>原版权重为成长质量 25%、业务质量 45%、财务强度 10%、资本配置 10%、数据置信度 10%；公开版以行业内增长、利润率、FCF、ROIC 与杠杆分位数做代理。</p></section>
        <section><h3>季度验证</h3><p>使用最近季度收入同比/环比、营业利润率与自由现金流，分为加速增长、平稳、增速放缓、趋势恶化及未覆盖。</p></section>
        <section><h3>Alpha 催化</h3><p>要求市场动量与至少两项经营恢复信号共同出现。分析师周度预期需要授权快照，因此 FY1 增速、FY2 Forward P/E 与预期变化列保留但不填猜测值。</p></section>
        <section><h3>五个核心维度</h3><p>成长空间、商业质量、资本配置、估值与安全边际、季度经营趋势验证。投资画像用于选择适合的研究路径，不等于交易评级。</p></section>
        <section><h3>主要边界</h3><p>TAM、技术壁垒、竞争格局、管理层、资源储量与资产 NAV 仍需定性研究；极端估值、高杠杆、负 FCF 与接近高点会触发复核提醒。</p></section>
      </div>`;
    return `
      <div class="methodology-grid">
        <section><h3>排名含义</h3><p>综合分衡量当日异常强度，不是上涨概率。公开版目前以 20/60/120/252 日相对强弱、量能、均线与波动状态形成现货动量分。</p></section>
        <section><h3>现货模块</h3><p><code>RS%=个股20日收益−SPY 20日收益</code>；<code>放量比=5日均量÷20日均量</code>；连续放量用于区分单日脉冲和持续参与。</p></section>
        <section><h3>波动模块</h3><p>布林压缩按当前20日带宽相对近120日历史分位识别；波动率状态比较10日与60日实现波动，区分扩张、正常和压缩。</p></section>
        <section><h3>期权模块</h3><p>P/C、ATM IV、IV/HV、Delta方向、期限结构、Vol/OI、Call OI占比与期权分需要完整期权链授权数据。字段均在主表，未授权时明确显示待授权源。</p></section>
        <section><h3>Gamma 模块</h3><p>γ Wall、Call Wall、GEX净值、局部GEX环境、Zero Gamma及数据质量必须由同一完整链按一致到期桶计算，不可从股价反推。</p></section>
        <section><h3>信号跟踪</h3><p>每日快照记录排名、分数、首次捕捉与信号天龄。共振只有在现货和期权方向均可验证时才成立；当前仅标记“现货确认·待期权”。</p></section>
      </div>`;
  }
  function nullableNumber(value) { const parsed = Number(value); return value === '' || !Number.isFinite(parsed) ? null : parsed; }
  function fmtNumber(value, digits = 2) { return value === null || value === undefined || !Number.isFinite(Number(value)) ? '—' : Number(value).toLocaleString('zh-CN', { maximumFractionDigits: digits }); }
  function fmtPct(value) { return value === null || value === undefined || !Number.isFinite(Number(value)) ? '—' : `${Number(value) > 0 ? '+' : ''}${fmtNumber(value)}%`; }
  function fmtMultiple(value) { return value === null || value === undefined || !Number.isFinite(Number(value)) ? '—' : `${fmtNumber(value)}x`; }
  function fmtMoney(value, currency) { return value === null || value === undefined ? '—' : `${currency === 'USD' ? '$' : ''}${fmtNumber(value)}`; }
  function fmtMarketCap(value) { if (value === null || value === undefined) return '—'; return value >= 1e12 ? `$${fmtNumber(value / 1e12, 1)}T` : `$${fmtNumber(value / 1e9, 1)}B`; }
  function valueClass(value) { return Number(value) > 0 ? 'positive' : Number(value) < 0 ? 'negative' : '' ; }
  function scoreClass(value) { return Number(value) >= 75 ? 'high' : Number(value) >= 50 ? 'mid' : 'low'; }
  function scoreClass5(value) { return Number(value) >= 3.75 ? 'high' : Number(value) >= 2.5 ? 'mid' : 'low'; }
  function signalClass(label) { return /强势|偏强|高质量|稳健|重点|确认|加速|是/.test(label || '') ? 'positive' : /转弱|弱势|承压|恶化|暂缓|否/.test(label || '') ? 'negative' : 'neutral'; }
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
