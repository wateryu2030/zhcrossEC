/**
 * CPG-Hub 前端 - OpenClaw + 百度优选 Skill
 */

var API_BASE = (typeof window !== 'undefined' && window.__API_BASE__) || '/api/v1';
var API_BASE_SAFE = '/api/v1';

/** 安全 API 地址：保证永不请求到 /undefined，防止扩展覆盖或变量未定义 */
function apiUrl(path, queryString) {
  var base = (typeof API_BASE === 'string' && API_BASE && String(API_BASE) !== 'undefined')
    ? API_BASE.replace(/\/+$/, '') : API_BASE_SAFE;
  var p = (path != null && String(path) !== 'undefined') ? String(path).replace(/^\/+/, '') : '';
  var url = p ? base + '/' + p : base;
  if (queryString != null && String(queryString) !== '' && String(queryString) !== 'undefined')
    url += (url.indexOf('?') >= 0 ? '&' : '?') + String(queryString).replace(/^\?/, '');
  return url;
}

/** 安全链接：避免 href 为 undefined 导致 404 */
function safeHref(url) {
  if (url == null || String(url).trim() === '' || String(url) === 'undefined') return '';
  return escapeHtml(String(url).trim());
}

// 首屏加载：优先真实环境数据，并展示数据来源与配置提示
async function loadDemo() {
  try {
    const res = await fetch(apiUrl('demo'));
    const data = await res.json();
    if (data.stats) renderStatsStrip(data.stats, data.media_count);
    if (data.data_source) renderDataSourceBadge(data.data_source, data.warnings, data.config_links, data.configured);
    if (data.hot_categories?.length) renderHotCategories(data.hot_categories);
    if (data.industry_news?.length) renderIndustryNews(data.industry_news);
    if (data.analyze_samples?.length) renderQuickAnalyze(data.analyze_samples);
    else if (data.analyze_sample?.overseas) renderQuickAnalyze([data.analyze_sample]);
    if (data.trending?.length) renderTrendingDemo(data.trending);
    var policiesResult = document.getElementById('policies-result');
    if (policiesResult) {
      policiesResult.innerHTML = '<p class="hint">请点击「刷新·法务政策库」或「从数据库加载」加载政策列表（支持分页与省市筛选）</p>';
    }
    if (data.analyze_sample?.overseas || data.analyze_samples?.length) {
      renderAnalyzeDemo(data.analyze_samples?.[0] || data.analyze_sample);
    } else {
      renderAnalyzeDemoEmpty();
    }
  } catch (e) {
    console.warn('Demo load failed:', e);
  }
}

function renderDataSourceBadge(dataSource, warnings, configLinks, configured) {
  const strip = document.getElementById('stats-strip');
  if (!strip) return;
  const existing = document.getElementById('data-source-banner');
  if (existing) existing.remove();
  const banner = document.createElement('div');
  banner.id = 'data-source-banner';
  banner.className = 'data-source-banner';
  const label = dataSource === 'real' ? '真实数据' : dataSource === 'mixed' ? '混合（部分真实）' : '暂无数据';
  const cls = dataSource === 'real' ? 'real' : dataSource === 'mixed' ? 'mixed' : 'demo';
  let html = `<span class="data-source-badge ${cls}">${escapeHtml(label)}</span>`;
  if (configured && configured.length) {
    html += `<div class="config-configured"><span>已配置：</span>${escapeHtml(configured.join('、'))}</div>`;
  }
  if (warnings && warnings.length) {
    html += `<div class="data-source-warnings"><span>配置提示：</span><ul>${warnings.map(w => `<li>${escapeHtml(w)}</li>`).join('')}</ul></div>`;
  }
  if (configLinks && configLinks.length) {
    html += '<div class="config-links"><span>完善配置：</span><ul class="config-links-list">';
    configLinks.forEach(function (c) {
      if (c.key_url) {
        html += `<li><strong>${escapeHtml(c.name)}</strong> ${escapeHtml(c.desc || '')} — <a href="${escapeHtml(c.signup_url)}" target="_blank" rel="noopener">注册</a> · <a href="${escapeHtml(c.key_url)}" target="_blank" rel="noopener">获取 Key</a></li>`;
      } else if (c.links && c.links.length) {
        const linkParts = c.links.map(function (l) { return `<a href="${escapeHtml(l.url)}" target="_blank" rel="noopener">${escapeHtml(l.label)}</a>`; });
        html += `<li><strong>${escapeHtml(c.name)}</strong> ${escapeHtml(c.desc || '')} — ${linkParts.join(' · ')}</li>`;
      } else {
        html += `<li><strong>${escapeHtml(c.name)}</strong> ${escapeHtml(c.desc || '')} — <a href="${escapeHtml(c.signup_url)}" target="_blank" rel="noopener">申请</a></li>`;
      }
    });
    html += '</ul></div>';
  }
  banner.innerHTML = html;
  strip.insertBefore(banner, strip.firstChild);
}

function renderHotCategories(cats) {
  const el = document.getElementById('overview-hot-categories');
  if (!el || !cats.length) return;
  el.innerHTML = `
    <div class="section-title">热门类目</div>
    <div class="hot-categories-grid">
      ${cats.map(c => `
        <div class="hot-cat-item">
          <span class="hot-cat-name">${escapeHtml(c.name || '')}</span>
          <span class="hot-cat-count">${c.count ?? 0}</span>
          <span class="hot-cat-trend">${escapeHtml(c.trend || '')}</span>
          <span class="hot-cat-note">${escapeHtml(c.note || '')}</span>
        </div>
      `).join('')}
    </div>
  `;
}

function renderIndustryNews(news) {
  const el = document.getElementById('overview-news');
  if (!el || !news.length) return;
  el.innerHTML = `
    <div class="section-title">行业资讯</div>
    <div class="news-list">
      ${news.map(n => `
        <div class="news-item">
          <div class="news-title">${escapeHtml(n.title || '')}</div>
          <div class="news-meta">${escapeHtml(n.source || '')} · ${n.date || ''}</div>
          <div class="news-summary">${escapeHtml(n.summary || '')}</div>
        </div>
      `).join('')}
    </div>
  `;
}

function renderQuickAnalyze(samples) {
  const el = document.getElementById('overview-quick-analyze');
  if (!el || !samples?.length) return;
  el.innerHTML = `
    <div class="section-title">选品速览</div>
    <div class="quick-analyze-list">
      ${samples.slice(0, 6).map(s => {
        const o = s.overseas || {};
        const diff = s.price_diff ?? 0;
        const rec = s.recommendation || '';
        return `
          <div class="quick-analyze-item">
            <div class="value">${escapeHtml(o.title || '')}</div>
            <div class="label">$${o.price ?? 0} · 差价 $${diff} · ${escapeHtml(rec)}</div>
          </div>
        `;
      }).join('')}
    </div>
  `;
}

function renderStatsStrip(stats, mediaCount) {
  const el = document.getElementById('stats-strip');
  if (!el || !stats) return;
  const items = [
    ['trending_count', '热销品', stats.trending_count ?? 0],
    ['policy_count', '政策', stats.policy_count ?? 0],
    ['media_count', '媒体', stats.media_count ?? mediaCount ?? 0],
    ['avg_price_diff', '均价差', stats.avg_price_diff ?? '-'],
    ['hot_category', '热门类目', stats.hot_category ?? '-'],
  ];
  if (stats.high_profit_count != null) {
    items.splice(3, 0, ['high_profit_count', '高潜力', stats.high_profit_count]);
  }
  el.innerHTML = items.map(([, lbl, val]) => `
    <div class="stat-item"><span class="stat-val">${escapeHtml(String(val))}</span><span class="stat-lbl">${escapeHtml(lbl)}</span></div>
  `).join('');
}

function renderTrendingDemo(items) {
  const el = document.getElementById('trending-result');
  if (!el) return;
  el.innerHTML = items.map(item => {
    const o = item.overseas || {};
    const bd = item.baidu_domestic || {};
    const domestic = bd.products || [];
    const diff = item.price_diff ?? 0;
    const profit = item.profit_potential || '';
    const note = item.note || '';
    const profitClass = profit === '高' ? 'profit-high' : profit === '中' ? 'profit-mid' : 'profit-low';
    return `
      <div class="trending-card">
        ${o.badge ? `<span class="overseas-badge">${escapeHtml(o.badge)}</span>` : ''}
        <div class="trending-overseas">
          <div class="label">海外热销</div>
          <div class="value">${escapeHtml(o.title || '')}</div>
          <div class="label">$${o.price ?? 0} · ⭐ ${o.rating ?? '-'} · ${o.sales_volume || ''}</div>
        </div>
        <div class="trending-baidu">
          <div class="label"><span class="source-badge">${escapeHtml(bd.source || '百度优选')}</span> 国内同款</div>
          ${domestic.length ? domestic.map(p => `
            <div class="item">
              <div class="value">${escapeHtml(p.name || '')}</div>
              <div class="label">${p.platform || ''} · ¥${p.price ?? 0} ${p.rating ? '⭐ ' + p.rating : ''}</div>
            </div>
          `).join('') : ''}
          <div class="trending-meta">
            ${diff !== undefined ? `<span class="trending-diff">差价 $${diff}</span>` : ''}
            ${profit ? `<span class="profit-tag ${profitClass}">${profit}潜力</span>` : ''}
          </div>
          ${note ? `<p class="trending-note">${escapeHtml(note)}</p>` : ''}
        </div>
      </div>
    `;
  }).join('');
}

/** 单条政策卡片的法务溯源性 HTML（效力、风险、目标国、生效/废止、修订说明、原文链接） */
function policyLegalMetaHtml(p) {
  const risk = p.risk_level || (p.impact || {}).risk_level || '';
  const riskClass = risk === '高' ? 'risk-high' : risk === '中' ? 'risk-mid' : 'risk-low';
  const parts = [];
  if (p.target_region) parts.push(`<span class="policy-region">${escapeHtml(p.target_region)}</span>`);
  if (p.validity_level) parts.push(`<span class="policy-validity">${escapeHtml(p.validity_level)}</span>`);
  if (risk) parts.push(`<span class="policy-risk ${riskClass}">${escapeHtml(risk)}</span>`);
  const points = Array.isArray(p.risk_points) ? p.risk_points : [];
  const dateParts = [];
  if (p.publish_date) dateParts.push('发布 ' + escapeHtml(p.publish_date));
  if (p.effective_date) dateParts.push('生效 ' + escapeHtml(p.effective_date));
  if (p.repeal_date) dateParts.push('废止 ' + escapeHtml(p.repeal_date));
  const dateLine = dateParts.length ? dateParts.join(' · ') : '';
  let html = (parts.length ? `<div class="policy-meta-row">${parts.join(' ')}</div>` : '') +
    (p.source || dateLine ? `<div class="label policy-date">${p.source ? '发布机构：' + escapeHtml(p.source) : ''}${p.source && dateLine ? ' · ' : ''}${dateLine || ''}</div>` : '');
  if (p.validity_note) html += `<div class="policy-validity-note">${escapeHtml(p.validity_note)}</div>`;
  if (p.revision_notes) html += `<div class="policy-revision-notes"><span class="label">修订说明</span> ${escapeHtml(p.revision_notes)}</div>`;
  if (points.length) html += `<div class="policy-section"><div class="label">风险点</div><ul>${points.map(x => `<li>${escapeHtml(String(x))}</li>`).join('')}</ul></div>`;
  if (safeHref(p.url)) html += `<a href="${safeHref(p.url)}" target="_blank" rel="noopener" class="policy-link">查看原文 →</a>`;
  return html;
}

function renderPoliciesDemo(policies) {
  const el = document.getElementById('policies-result');
  const filters = document.getElementById('policy-filters');
  if (!el) return;
  const cats = [...new Set(policies.map(p => p.applicable_scenario || p.category).filter(Boolean))];
  if (filters && cats.length) {
    filters.innerHTML = '<button class="filter-btn active" data-cat="">全部</button>' +
      cats.map(c => `<button class="filter-btn" data-cat="${escapeHtml(c)}">${escapeHtml(c)}</button>`).join('');
    filters.querySelectorAll('.filter-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        filters.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        const cat = btn.dataset.cat || '';
        const filtered = cat ? policies.filter(p => (p.applicable_scenario || p.category) === cat) : policies;
        el.innerHTML = filtered.map(p => {
          const imp = p.impact || {};
          const risk = p.risk_level || imp.risk_level || '';
          const riskClass = risk === '高' ? 'risk-high' : risk === '中' ? 'risk-mid' : 'risk-low';
          const br = p.baidu_related || {};
          const scenario = p.applicable_scenario || p.category || '综合';
          const dataSource = (p.id || '').startsWith('search-') ? '自动搜索' : (p.id || '').startsWith('crawl-') ? '官网采集' : '政策库';
          return `
            <div class="policy-card">
              <div class="policy-header">
                <span class="policy-cat">${escapeHtml(scenario)}</span>
                ${risk ? `<span class="policy-risk ${riskClass}">${escapeHtml(risk)}</span>` : ''}
                <span class="policy-source-tag">${escapeHtml(dataSource)}</span>
              </div>
              <div class="value policy-title">${escapeHtml(p.title || '')}</div>
              ${policyLegalMetaHtml(p)}
              <div class="policy-summary">${escapeHtml(imp.summary || '')}</div>
              ${(br.products || []).length ? `
                <div class="policy-section">
                  <div class="label"><span class="source-badge">${escapeHtml(br.source || '百度优选')}</span> 相关选品</div>
                  <div class="baidu-products">
                    ${(br.products || []).map(prod => `
                      <div class="item"><span class="value">${escapeHtml(prod.name || '')}</span> · ${prod.platform || ''} ¥${prod.price ?? 0}</div>
                    `).join('')}
                  </div>
                </div>
              ` : ''}
            </div>
          `;
        }).join('');
      });
    });
  }
  el.innerHTML = policies.map(p => {
    const imp = p.impact || {};
    const risk = p.risk_level || imp.risk_level || '';
    const riskClass = risk === '高' ? 'risk-high' : risk === '中' ? 'risk-mid' : 'risk-low';
    const br = p.baidu_related || {};
    const scenario = p.applicable_scenario || p.category || '综合';
    const dataSource = (p.id || '').startsWith('search-') ? '自动搜索' : (p.id || '').startsWith('crawl-') ? '官网采集' : '政策库';
    return `
      <div class="policy-card">
        <div class="policy-header">
          <span class="policy-cat">${escapeHtml(scenario)}</span>
          ${risk ? `<span class="policy-risk ${riskClass}">${escapeHtml(risk)}</span>` : ''}
          <span class="policy-source-tag">${escapeHtml(dataSource)}</span>
        </div>
        <div class="value policy-title">${escapeHtml(p.title || '')}</div>
        ${policyLegalMetaHtml(p)}
        <div class="policy-summary">${escapeHtml(imp.summary || '')}</div>
        ${(imp.impact_points || []).length ? `
          <div class="policy-section">
            <div class="label">影响点</div>
            <ul>${(imp.impact_points || []).map(i => `<li>${escapeHtml(i)}</li>`).join('')}</ul>
          </div>
        ` : ''}
        ${(br.products || []).length ? `
          <div class="policy-section">
            <div class="label"><span class="source-badge">${escapeHtml(br.source || '百度优选')}</span> 相关选品</div>
            <div class="baidu-products">
              ${(br.products || []).map(prod => `
                <div class="item"><span class="value">${escapeHtml(prod.name || '')}</span> · ${prod.platform || ''} ¥${prod.price ?? 0}</div>
              `).join('')}
            </div>
          </div>
        ` : ''}
      </div>
    `;
  }).join('');
}

function renderAnalyzeDemoEmpty() {
  const el = document.getElementById('analyze-demo');
  if (!el) return;
  el.innerHTML = '<div class="analyze-demo-empty">暂无选品分析示例，请到「选品分析」输入 Amazon 链接获取真实对比数据。</div>';
}

function renderAnalyzeDemo(sample) {
  const el = document.getElementById('analyze-demo');
  if (!el || !sample?.overseas) return;
  const o = sample.overseas || {};
  const domestic = sample.domestic_products || [];
  el.innerHTML = `
    <div class="demo-label">百度优选 · 选品对比（真实数据）</div>
    <div class="analyze-demo-card">
      <div class="item">
        <div class="label">海外商品</div>
        <div class="value">${escapeHtml(o.title || '')}</div>
        <div class="label">海外价格 · 评分</div>
        <div class="value">$${o.price ?? 0} ${o.currency || 'USD'} · ⭐ ${o.rating ?? '-'} · ${o.sales_volume || ''}</div>
        <div class="label">差价 · 选品得分</div>
        <div class="value">$${sample.price_diff ?? 0} · ${sample.selection_score ?? 0} 分</div>
        <span class="badge warning">${escapeHtml(sample.recommendation || '')}</span>
        ${sample.reputation_summary ? `<p class="reputation-note">${escapeHtml(sample.reputation_summary)}</p>` : ''}
      </div>
      ${domestic.length ? `
        <div class="label" style="margin-top:1rem"><span class="source-badge">${escapeHtml(sample.baidu_source || '百度优选')}</span> 国内同款</div>
        ${domestic.map(p => `
          <div class="item">
            <div class="value">${escapeHtml(p.name || '')}</div>
            <div class="label">${p.platform || ''} · ¥${p.price ?? 0} ${p.rating ? '⭐ ' + p.rating : ''}</div>
          </div>
        `).join('')}
      ` : ''}
    </div>
  `;
}

document.addEventListener('DOMContentLoaded', loadDemo);

function showPanel(id) {
  document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
  const panel = document.getElementById(`panel-${id}`);
  const btn = document.querySelector(`[data-tab="${id}"]`);
  if (panel) panel.classList.add('active');
  if (btn) btn.classList.add('active');
}

document.querySelectorAll('.nav-btn').forEach(btn => {
  btn.addEventListener('click', () => showPanel(btn.dataset.tab));
});

document.querySelectorAll('.quick-nav-btn').forEach(btn => {
  btn.addEventListener('click', () => showPanel(btn.dataset.tab));
});

// 选品分析
const amazonInput = document.getElementById('amazon-input');
const btnAnalyze = document.getElementById('btn-analyze');
const analyzeResult = document.getElementById('analyze-result');

btnAnalyze.addEventListener('click', async () => {
  const url = amazonInput.value?.trim();
  if (!url) {
    analyzeResult.innerHTML = '<p class="error">请输入 Amazon 链接或 ASIN</p>';
    return;
  }

  const analyzeDemo = document.getElementById('analyze-demo');
  if (analyzeDemo) analyzeDemo.innerHTML = '';

  btnAnalyze.disabled = true;
  analyzeResult.innerHTML = '<p class="loading">分析中...</p>';

  try {
    const res = await fetch(apiUrl('analyze'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ amazon_url: url }),
    });
    const data = await res.json();

    if (!res.ok) throw new Error(data.detail || '请求失败');
    if (data.error) {
      analyzeResult.innerHTML = `<p class="error">${escapeHtml(data.error)}</p><p class="hint">${escapeHtml(data.recommendation || '请配置 OMKAR_CLOUD_API_KEY 后重试')}</p>`;
      return;
    }

    const o = data.overseas || {};
    const rec = data.recommendation || '';
    const diff = data.price_diff ?? 0;
    const score = data.selection_score ?? 0;
    const domestic = data.domestic_products || [];
    const baiduSource = data.baidu_source || '百度优选';

    let html = `
      <div class="item">
        <div class="label">海外商品</div>
        <div class="value">${escapeHtml(o.title || '')}</div>
        <div class="label">海外价格</div>
        <div class="value">$${o.price ?? 0} ${o.currency || 'USD'}</div>
        <div class="label">差价</div>
        <div class="value">$${diff}</div>
        <div class="label">选品得分</div>
        <div class="value">${score}</div>
        <span class="badge ${rec.includes('适合') ? 'success' : 'warning'}">${escapeHtml(rec)}</span>
      </div>
    `;

    if (domestic.length) {
      html += `<div class="label" style="margin-top:1rem"><span class="source-badge">${escapeHtml(baiduSource)}</span> 国内同款</div>`;
      domestic.slice(0, 3).forEach(p => {
        html += `
          <div class="item">
            <div class="value">${escapeHtml(p.name || '')}</div>
            <div class="label">${p.platform || ''} · ¥${p.price ?? 0}</div>
          </div>
        `;
      });
    }

    analyzeResult.innerHTML = html;
  } catch (e) {
    analyzeResult.innerHTML = `<p class="error">${escapeHtml(e.message)}</p><p class="hint">可刷新页面恢复演示数据</p>`;
  } finally {
    btnAnalyze.disabled = false;
  }
});

// 热销趋势
const btnTrending = document.getElementById('btn-load-trending');
const trendingResult = document.getElementById('trending-result');

btnTrending.addEventListener('click', async () => {
  btnTrending.disabled = true;
  trendingResult.innerHTML = '<p class="loading">加载中...</p>';

  try {
    const res = await fetch(apiUrl('trending'));
    const data = await res.json();
    const items = data.items || [];

    if (data.error) {
      trendingResult.innerHTML = `<p class="error">${escapeHtml(data.error)}</p><p class="hint">请在 .env 中配置 OMKAR_CLOUD_API_KEY 后重试</p>`;
      return;
    }
    if (items.length === 0) {
      const demoRes = await fetch(apiUrl('demo'));
      const demo = await demoRes.json();
      if (demo.trending?.length) {
        renderTrendingDemo(demo.trending);
      } else {
        trendingResult.innerHTML = '<p class="hint">暂无热销数据。配置 OMKAR_CLOUD_API_KEY 并点击刷新，或等待后台同步积累。</p>';
      }
    } else {
      trendingResult.innerHTML = items.map(item => {
        const o = item.overseas || {};
        const bd = item.baidu_domestic || {};
        const domestic = bd.products || [];
        const diff = item.price_diff ?? 0;
        return `
          <div class="trending-card">
            <div class="trending-overseas">
              <div class="label">海外热销</div>
              <div class="value">${escapeHtml(o.title || '')}</div>
              <div class="label">$${o.price ?? 0} · ${o.sales_volume || ''}</div>
            </div>
            <div class="trending-baidu">
              <div class="label"><span class="source-badge">${escapeHtml(bd.source || '百度优选')}</span> 国内同款</div>
              ${domestic.length ? domestic.map(p => `
                <div class="item">
                  <div class="value">${escapeHtml(p.name || '')}</div>
                  <div class="label">${p.platform || ''} · ¥${p.price ?? 0}</div>
                </div>
              `).join('') : '<p class="hint">暂无同款</p>'}
              ${diff > 0 ? `<div class="trending-diff">差价约 $${diff}</div>` : ''}
            </div>
          </div>
        `;
      }).join('');
    }
  } catch (e) {
    trendingResult.innerHTML = `<p class="error">${escapeHtml(e.message)}</p>`;
  } finally {
    btnTrending.disabled = false;
  }
});

// 政策动态（法务自用：合规场景+目标国+风险等级，无百度依赖）
const btnPolicies = document.getElementById('btn-load-policies');
const policiesResult = document.getElementById('policies-result');
const policyFilters = document.getElementById('policy-filters');
const policyFiltersRegion = document.getElementById('policy-filters-region');
const policyFiltersRisk = document.getElementById('policy-filters-risk');
const policyFiltersRegionLabel = document.getElementById('policy-filters-region-label');
const policyIncludeRepealed = document.getElementById('policy-include-repealed');

let currentPolicyScenario = '';
let currentPolicyRegion = '';
let currentPolicyRisk = '';
let currentPolicyRegionLabel = '';
let currentPolicyLibraryPage = 0;
const POLICY_LIBRARY_PAGE_SIZE = 30;

async function loadPolicies(opts) {
  opts = opts || {};
  const scenario = opts.scenario ?? currentPolicyScenario;
  const target_region = opts.region ?? currentPolicyRegion;
  const risk_level = opts.risk ?? currentPolicyRisk;
  const region_label = opts.region_label ?? currentPolicyRegionLabel;
  const include_repealed = policyIncludeRepealed ? policyIncludeRepealed.checked : false;
  btnPolicies.disabled = true;
  policiesResult.innerHTML = '<p class="loading">加载中...</p>';
  const policyDbPaginationEl = document.getElementById('policy-db-pagination');
  if (policyDbPaginationEl) policyDbPaginationEl.style.display = 'none';

  try {
    const params = new URLSearchParams();
    if (scenario) params.set('scenario', scenario);
    if (target_region) params.set('target_region', target_region);
    if (region_label) params.set('region_label', region_label);
    if (risk_level) params.set('risk_level', risk_level);
    if (include_repealed) params.set('include_repealed', 'true');
    const policyPage = opts.page ?? currentPolicyLibraryPage;
    const policyLimit = 30;
    params.set('limit', String(policyLimit));
    params.set('offset', String(policyPage * policyLimit));
    const res = await fetch(apiUrl('policies', params.toString()));
    const data = await res.json();
    const policies = data.policies || [];
    const total_count = data.total_count ?? policies.length;
    const limit = data.limit ?? POLICY_LIBRARY_PAGE_SIZE;
    const offset = data.offset ?? 0;
    const categories = data.categories || [];
    const target_regions = data.target_regions || ['中国', '欧盟', '美国', '其他'];
    const region_labels = data.region_labels || [];

    if (policyFilters && categories.length) {
      policyFilters.innerHTML = '<span class="filter-label">合规场景</span><button class="filter-btn ' + (!scenario ? 'active' : '') + '" data-scenario="">全部</button>' +
        categories.map(c => `<button class="filter-btn ${scenario === c.id ? 'active' : ''}" data-scenario="${escapeHtml(c.id)}">${escapeHtml(c.name)} (${c.count || 0})</button>`).join('');
      policyFilters.querySelectorAll('.filter-btn').forEach(btn => {
        btn.addEventListener('click', () => {
          currentPolicyScenario = btn.dataset.scenario || '';
          policyFilters.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
          btn.classList.add('active');
          currentPolicyLibraryPage = 0;
          loadPolicies({ scenario: currentPolicyScenario, region: currentPolicyRegion, risk: currentPolicyRisk, region_label: currentPolicyRegionLabel });
        });
      });
    }
    if (policyFiltersRegion && target_regions.length) {
      policyFiltersRegion.innerHTML = '<span class="filter-label">目标国/地区</span><button class="filter-btn ' + (!target_region ? 'active' : '') + '" data-region="">全部</button>' +
        target_regions.map(r => `<button class="filter-btn ${target_region === r ? 'active' : ''}" data-region="${escapeHtml(r)}">${escapeHtml(r)}</button>`).join('');
      policyFiltersRegion.querySelectorAll('.filter-btn').forEach(btn => {
        btn.addEventListener('click', () => {
          currentPolicyRegion = btn.dataset.region || '';
          policyFiltersRegion.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
          btn.classList.add('active');
          currentPolicyLibraryPage = 0;
          loadPolicies({ scenario: currentPolicyScenario, region: currentPolicyRegion, risk: currentPolicyRisk, region_label: currentPolicyRegionLabel });
        });
      });
    }
    if (policyFiltersRisk) {
      const risks = [{ id: '', name: '全部' }, { id: '高', name: '高' }, { id: '中', name: '中' }, { id: '低', name: '低' }];
      policyFiltersRisk.innerHTML = '<span class="filter-label">风险等级</span>' +
        risks.map(r => `<button class="filter-btn ${risk_level === r.id ? 'active' : ''}" data-risk="${escapeHtml(r.id)}">${escapeHtml(r.name)}</button>`).join('');
      policyFiltersRisk.querySelectorAll('.filter-btn').forEach(btn => {
        btn.addEventListener('click', () => {
          currentPolicyRisk = btn.dataset.risk || '';
          policyFiltersRisk.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
          btn.classList.add('active');
          currentPolicyLibraryPage = 0;
          loadPolicies({ scenario: currentPolicyScenario, region: currentPolicyRegion, risk: currentPolicyRisk, region_label: currentPolicyRegionLabel });
        });
      });
    }
    if (policyFiltersRegionLabel && region_labels.length) {
      policyFiltersRegionLabel.innerHTML = '<span class="filter-label">各地</span><button class="filter-btn ' + (!region_label ? 'active' : '') + '" data-region-label="">全部</button>' +
        region_labels.slice(0, 24).map(r => `<button class="filter-btn ${region_label === r ? 'active' : ''}" data-region-label="${escapeHtml(r)}">${escapeHtml(r)}</button>`).join('');
      policyFiltersRegionLabel.querySelectorAll('.filter-btn').forEach(btn => {
        btn.addEventListener('click', () => {
          currentPolicyRegionLabel = btn.dataset.regionLabel || '';
          policyFiltersRegionLabel.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
          btn.classList.add('active');
          currentPolicyLibraryPage = 0;
          loadPolicies({ scenario: currentPolicyScenario, region: currentPolicyRegion, risk: currentPolicyRisk, region_label: currentPolicyRegionLabel });
        });
      });
    }
    const analysisRegionSelect = document.getElementById('policy-analysis-region');
    if (analysisRegionSelect && region_labels.length) {
      analysisRegionSelect.innerHTML = '<option value="全部">全部</option>' + region_labels.map(r => `<option value="${escapeHtml(r)}">${escapeHtml(r)}</option>`).join('');
    }
    if (policyIncludeRepealed) {
      policyIncludeRepealed.addEventListener('change', () => { currentPolicyLibraryPage = 0; loadPolicies({ scenario: currentPolicyScenario, region: currentPolicyRegion, risk: currentPolicyRisk, region_label: currentPolicyRegionLabel }); });
    }

    const policyLibraryPagination = document.getElementById('policy-library-pagination');
    if (policyLibraryPagination) policyLibraryPagination.style.display = 'none';
    if (!policies.length) {
      const demoRes = await fetch(apiUrl('demo'));
      const demo = await demoRes.json();
      if (demo.policies?.length) {
        renderPoliciesDemo(demo.policies);
      } else {
        policiesResult.innerHTML = '<p class="hint">暂无政策数据</p>';
      }
    } else {
      const from = offset + 1;
      const to = offset + policies.length;
      const headerHtml = total_count > limit
        ? `<div class="policy-result-header">共 <strong>${total_count}</strong> 条（当前第 ${from}–${to} 条）</div>`
        : `<div class="policy-result-header">共 ${total_count} 条</div>`;
      policiesResult.innerHTML = headerHtml + policies.map(p => {
        const imp = p.impact || {};
        const risk = p.risk_level || imp.risk_level || '';
        const riskClass = risk === '高' ? 'risk-high' : risk === '中' ? 'risk-mid' : 'risk-low';
        const scenario = p.applicable_scenario || p.category || '综合';
        const repealedClass = p.is_repealed ? ' policy-card--repealed' : '';
        return `
          <div class="policy-card${repealedClass}">
            <div class="policy-header">
              <span class="policy-cat">${escapeHtml(scenario)}</span>
              ${p.is_repealed ? '<span class="policy-repealed-badge">已废止</span>' : ''}
              ${risk ? `<span class="policy-risk ${riskClass}">${escapeHtml(risk)}</span>` : ''}
              <span class="policy-source-tag">${escapeHtml(p.source_tier || '政策库')}</span>
            </div>
            <div class="value policy-title">${escapeHtml(p.title || '')}</div>
            ${policyLegalMetaHtml(p)}
            <div class="policy-summary">${escapeHtml(imp.summary || '')}</div>
          </div>
        `;
      }).join('');
      if (total_count > limit && policyLibraryPagination) {
        const totalPages = Math.ceil(total_count / limit);
        let paginationHtml = '<div class="pagination-bar"><span class="pagination-info">第 ' + from + '–' + to + ' 条 / 共 ' + total_count + ' 条</span> ';
        if (currentPolicyLibraryPage > 0) {
          paginationHtml += '<button type="button" class="btn btn-secondary pagination-btn" data-page="' + (currentPolicyLibraryPage - 1) + '">上一页</button> ';
        }
        paginationHtml += '<span class="pagination-pages">第 ' + (currentPolicyLibraryPage + 1) + ' / ' + totalPages + ' 页</span>';
        if (currentPolicyLibraryPage < totalPages - 1) {
          paginationHtml += ' <button type="button" class="btn btn-secondary pagination-btn" data-page="' + (currentPolicyLibraryPage + 1) + '">下一页</button>';
        }
        paginationHtml += '</div>';
        policyLibraryPagination.innerHTML = paginationHtml;
        policyLibraryPagination.style.display = 'block';
        policyLibraryPagination.querySelectorAll('.pagination-btn').forEach(btn => {
          btn.addEventListener('click', function() {
            const p = parseInt(btn.getAttribute('data-page'), 10);
            if (!isNaN(p)) { currentPolicyLibraryPage = p; loadPolicies({ page: p, scenario: currentPolicyScenario, region: currentPolicyRegion, risk: currentPolicyRisk, region_label: currentPolicyRegionLabel }); }
          });
        });
      }
    }
  } catch (e) {
    policiesResult.innerHTML = `<p class="error">${escapeHtml(e.message)}</p>`;
  } finally {
    btnPolicies.disabled = false;
  }
}

btnPolicies.addEventListener('click', () => loadPolicies({}));

// 各地政策特点 · AI 分析
const btnAnalyzeRegions = document.getElementById('btn-analyze-regions');
const policyAnalysisResult = document.getElementById('policy-analysis-result');
if (btnAnalyzeRegions && policyAnalysisResult) {
  btnAnalyzeRegions.addEventListener('click', async () => {
    const sel = document.getElementById('policy-analysis-region');
    const region = sel ? sel.value : '全部';
    btnAnalyzeRegions.disabled = true;
    policyAnalysisResult.innerHTML = '<p class="loading">AI 分析中...</p>';
    try {
      const res = await fetch(apiUrl('policies/analyze-regions'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ region }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || res.statusText);
      policyAnalysisResult.innerHTML = `
        <div class="policy-analysis-card">
          <div class="policy-analysis-region">${escapeHtml(data.region || '')}</div>
          <div class="policy-analysis-summary">${escapeHtml(data.summary || '')}</div>
          ${(data.highlights || []).length ? `<div class="policy-analysis-highlights"><strong>特点</strong><ul>${(data.highlights || []).map(h => `<li>${escapeHtml(h)}</li>`).join('')}</ul></div>` : ''}
          ${(data.risk_focus || []).length ? `<div class="policy-analysis-risks"><strong>主要风险点</strong><ul>${(data.risk_focus || []).map(r => `<li>${escapeHtml(r)}</li>`).join('')}</ul></div>` : ''}
          ${data.comparison ? `<div class="policy-analysis-comparison"><strong>与其它地区差异</strong><p>${escapeHtml(data.comparison)}</p></div>` : ''}
        </div>
      `;
    } catch (e) {
      policyAnalysisResult.innerHTML = `<p class="error">${escapeHtml(e.message)}</p>`;
    } finally {
      btnAnalyzeRegions.disabled = false;
    }
  });
}

// 从数据库加载政策（爬虫周更 + 丝路电商伙伴国），支持按省市/分类/国家筛选
const btnPoliciesDb = document.getElementById('btn-load-policies-db');
const policyDbRegion = document.getElementById('policy-db-region');
const policyDbCategory = document.getElementById('policy-db-category');
const policyDbCountry = document.getElementById('policy-db-country');
const policyDbPagination = document.getElementById('policy-db-pagination');
const policyDbRegionChipsWrap = document.getElementById('policy-db-region-chips-wrap');
const policyDbRegionChips = document.getElementById('policy-db-region-chips');

const POLICY_DB_PAGE_SIZE = 20;
let policyDbCurrentPage = 0;

async function loadPoliciesFromDb(page) {
  if (!btnPoliciesDb || !policiesResult) return;
  if (typeof page === 'number') policyDbCurrentPage = Math.max(0, page);
  btnPoliciesDb.disabled = true;
  policiesResult.innerHTML = '<p class="loading">加载中...</p>';
  if (policyDbPagination) policyDbPagination.style.display = 'none';
  const policyLibraryPaginationEl = document.getElementById('policy-library-pagination');
  if (policyLibraryPaginationEl) policyLibraryPaginationEl.style.display = 'none';
  const params = new URLSearchParams();
  if (policyDbRegion && policyDbRegion.value) params.set('region', policyDbRegion.value);
  if (policyDbCategory && policyDbCategory.value) params.set('category', policyDbCategory.value);
  if (policyDbCountry && policyDbCountry.value) params.set('country', policyDbCountry.value);
  params.set('limit', String(POLICY_DB_PAGE_SIZE));
  params.set('offset', String(policyDbCurrentPage * POLICY_DB_PAGE_SIZE));
  try {
    const res = await fetch(apiUrl('policies/db') + (params.toString() ? '?' + params.toString() : ''));
    const data = await res.json();
    const policies = data.policies || [];
    const total_count = data.total_count ?? 0;
    const limit = data.limit || POLICY_DB_PAGE_SIZE;
    const offset = data.offset || 0;
    if (data.regions && policyDbRegion) {
      policyDbRegion.innerHTML = '<option value="">全部</option>' + (data.regions || []).map(r => `<option value="${escapeHtml(r)}">${escapeHtml(r)}</option>`).join('');
      if (params.get('region')) policyDbRegion.value = params.get('region');
    }
    if (data.regions && data.regions.length && policyDbRegionChipsWrap && policyDbRegionChips) {
      policyDbRegionChipsWrap.style.display = 'block';
      policyDbRegionChips.innerHTML = '<button type="button" class="filter-btn chip' + (!policyDbRegion.value ? ' active' : '') + '" data-region="">全部</button>' +
        (data.regions || []).map(r => '<button type="button" class="filter-btn chip' + (policyDbRegion.value === r ? ' active' : '') + '" data-region="' + escapeHtml(r) + '">' + escapeHtml(r) + '</button>').join('');
      policyDbRegionChips.querySelectorAll('.filter-btn.chip').forEach(btn => {
        btn.addEventListener('click', function() {
          const r = btn.getAttribute('data-region') || '';
          if (policyDbRegion) policyDbRegion.value = r;
          policyDbRegionChips.querySelectorAll('.filter-btn.chip').forEach(b => b.classList.remove('active'));
          btn.classList.add('active');
          policyDbCurrentPage = 0;
          loadPoliciesFromDb();
        });
      });
    }
    if (data.categories && policyDbCategory) {
      policyDbCategory.innerHTML = '<option value="">全部</option>' + (data.categories || []).map(c => `<option value="${escapeHtml(c)}">${escapeHtml(c)}</option>`).join('');
      if (params.get('category')) policyDbCategory.value = params.get('category');
    }
    if (data.countries && policyDbCountry) {
      policyDbCountry.innerHTML = '<option value="">全部</option>' + (data.countries || []).map(c => `<option value="${escapeHtml(c)}">${escapeHtml(c)}</option>`).join('');
      if (params.get('country')) policyDbCountry.value = params.get('country');
    }
    const dataSourceLabel = '当前数据源：数据库（爬虫周更）';
    const latestAt = data.latest_crawled_at ? (' · 最后更新：' + (data.latest_crawled_at.replace('T', ' ').slice(0, 19))) : '';
    if (!policies.length) {
      policiesResult.innerHTML = '<p class="policy-result-header">' + escapeHtml(dataSourceLabel) + latestAt + '</p><p class="hint">数据库暂无政策，请先运行 <code>bash scripts/run_policy_full_sync.sh</code> 或等待周任务；丝路电商伙伴国政策会一并入库。</p>';
    } else {
      const from = offset + 1;
      const to = Math.min(offset + policies.length, total_count);
      const headerHtml = '<p class="policy-result-header">' + escapeHtml(dataSourceLabel) + latestAt + ' · 共 <strong>' + total_count + '</strong> 条（当前第 ' + from + '–' + to + ' 条，筛选：省市/分类/国家）</p>';
      const cardsHtml = policies.map((p, idx) => {
        const region = p.region || '';
        const country = p.country || '';
        const regionBadge = region ? `<span class="policy-card__region-badge region-central">${escapeHtml(region)}</span>` : '';
        const countryBadge = country ? `<span class="policy-card__region-badge region-overseas">丝路 · ${escapeHtml(country)}</span>` : '';
        const sourceTag = [region ? '爬虫 · ' + region : '', country ? '丝路电商 · ' + country : ''].filter(Boolean).join(' · ') || '政策';
        const dateStr = p.publish_date ? (p.publish_date.replace('T', ' ').slice(0, 10)) : '';
        const cardId = 'policy-card-' + (offset + idx);
        return `
            <div class="policy-card" id="${cardId}">
              <div class="policy-card__top-row">
                ${regionBadge}
                ${countryBadge}
                <span class="policy-card__date">${escapeHtml(dateStr)}</span>
                <span class="policy-cat">${escapeHtml(p.category || '综合')}</span>
                <span class="policy-source-tag">${escapeHtml(sourceTag)}</span>
              </div>
              <div class="value policy-title">${escapeHtml(p.title || '')}</div>
              <div class="label">${escapeHtml(p.source_org || '')}</div>
              ${p.content_snippet ? `<div class="policy-card__summary policy-summary">${escapeHtml(p.content_snippet)}</div>` : ''}
              <div class="policy-card__interpret">
                <button type="button" class="policy-card__interpret-btn" data-title="${escapeHtml((p.title || '').slice(0, 300))}" data-snippet="${escapeHtml((p.content_snippet || '').slice(0, 500))}">AI 解读</button>
                <div class="policy-card__interpret-text" data-interpret-placeholder></div>
              </div>
              ${safeHref(p.url) ? `<a href="${safeHref(p.url)}" target="_blank" rel="noopener" class="policy-link">查看原文 →</a>` : ''}
            </div>
          `;
      }).join('');
      policiesResult.innerHTML = headerHtml + cardsHtml;
      policiesResult.querySelectorAll('.policy-card__interpret-btn').forEach(function(btn) {
        btn.addEventListener('click', async function() {
          var placeholder = btn.closest('.policy-card__interpret').querySelector('[data-interpret-placeholder]');
          if (!placeholder) return;
          if (placeholder.innerText) return;
          var title = btn.getAttribute('data-title') || '';
          var snippet = btn.getAttribute('data-snippet') || '';
          btn.disabled = true;
          placeholder.innerText = '解读中…';
          try {
            var res = await fetch(apiUrl('policies/interpret'), {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ title: title, snippet: snippet })
            });
            var data = await res.json();
            if (data.interpretation) {
              placeholder.innerText = data.interpretation;
              placeholder.classList.add('policy-card__interpret-text--filled');
            } else {
              placeholder.innerText = data.error || '解读失败';
            }
          } catch (e) {
            placeholder.innerText = '网络错误';
          }
          btn.disabled = false;
        });
      });
      if (total_count > limit && policyDbPagination) {
        const totalPages = Math.ceil(total_count / limit);
        let paginationHtml = '<div class="pagination-bar"><span class="pagination-info">第 ' + from + '–' + to + ' 条 / 共 ' + total_count + ' 条</span> ';
        if (policyDbCurrentPage > 0) {
          paginationHtml += '<button type="button" class="btn btn-secondary pagination-btn" data-page="' + (policyDbCurrentPage - 1) + '">上一页</button> ';
        }
        paginationHtml += '<span class="pagination-pages">第 ' + (policyDbCurrentPage + 1) + ' / ' + totalPages + ' 页</span>';
        if (policyDbCurrentPage < totalPages - 1) {
          paginationHtml += ' <button type="button" class="btn btn-secondary pagination-btn" data-page="' + (policyDbCurrentPage + 1) + '">下一页</button>';
        }
        paginationHtml += '</div>';
        policyDbPagination.innerHTML = paginationHtml;
        policyDbPagination.style.display = 'block';
        policyDbPagination.querySelectorAll('.pagination-btn').forEach(btn => {
          btn.addEventListener('click', function() {
            const p = parseInt(btn.getAttribute('data-page'), 10);
            if (!isNaN(p)) loadPoliciesFromDb(p);
          });
        });
      }
    }
  } catch (e) {
    policiesResult.innerHTML = `<p class="error">${escapeHtml(e.message)}</p>`;
  } finally {
    btnPoliciesDb.disabled = false;
  }
}

if (btnPoliciesDb) {
  btnPoliciesDb.addEventListener('click', function() { policyDbCurrentPage = 0; loadPoliciesFromDb(0); });
}
if (policyDbRegion) policyDbRegion.addEventListener('change', function() { policyDbCurrentPage = 0; loadPoliciesFromDb(0); });
if (policyDbCategory) policyDbCategory.addEventListener('change', function() { policyDbCurrentPage = 0; loadPoliciesFromDb(0); });
if (policyDbCountry) policyDbCountry.addEventListener('change', function() { policyDbCurrentPage = 0; loadPoliciesFromDb(0); });

// 媒体热点
const btnMedia = document.getElementById('btn-load-media');
const mediaResult = document.getElementById('media-result');
const mediaLinksList = document.getElementById('media-links-list');
const formAddMediaLink = document.getElementById('form-add-media-link');
const btnAhotnewsSync = document.getElementById('btn-ahotnews-sync');

async function loadMediaLinks() {
  if (!mediaLinksList) return;
  try {
    const res = await fetch(apiUrl('media_links'));
    const data = await res.json();
    const items = data.items || [];
    if (!items.length) {
      mediaLinksList.innerHTML = '<p class="hint">暂无链接，在上方添加抖音/快手/财新/微博等链接</p>';
    } else {
      mediaLinksList.innerHTML = items.map(m => `
        <div class="media-link-item">
          <span class="media-link-platform">${escapeHtml(m.platform || '')}</span>
          <a href="${safeHref(m.url) || '#'}" target="_blank" rel="noopener">${escapeHtml(m.title || m.url || '')}</a>
          <button type="button" class="btn-link delete-media-link" data-url="${escapeHtml(m.url || '')}">删除</button>
        </div>
      `).join('');
      mediaLinksList.querySelectorAll('.delete-media-link').forEach(btn => {
        btn.addEventListener('click', async () => {
          const url = btn.getAttribute('data-url');
          if (!url) return;
          try {
            await fetch(apiUrl('media_links', 'url=' + encodeURIComponent(url)), { method: 'DELETE' });
            loadMediaLinks();
          } catch (e) {
            console.warn(e);
          }
        });
      });
    }
  } catch (e) {
    mediaLinksList.innerHTML = `<p class="error">${escapeHtml(e.message)}</p>`;
  }
}

if (formAddMediaLink) {
  formAddMediaLink.addEventListener('submit', async (e) => {
    e.preventDefault();
    const platform = document.getElementById('media-link-platform')?.value || 'other';
    const url = document.getElementById('media-link-url')?.value?.trim();
    const title = document.getElementById('media-link-title')?.value?.trim() || '';
    if (!url) return;
    try {
      const res = await fetch(apiUrl('media_links'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ platform, url, title }),
      });
      const data = await res.json();
      if (data.ok) {
        document.getElementById('media-link-url').value = '';
        document.getElementById('media-link-title').value = '';
        loadMediaLinks();
      } else {
        alert(data.detail || '添加失败');
      }
    } catch (err) {
      alert(err.message || '添加失败');
    }
  });
}

if (btnAhotnewsSync) {
  btnAhotnewsSync.addEventListener('click', async () => {
    btnAhotnewsSync.disabled = true;
    btnAhotnewsSync.textContent = '同步中…';
    try {
      const res = await fetch(apiUrl('crawl/ahotnews', 'platforms=dy,ks,wb'), { method: 'POST' });
      const data = await res.json();
      if (data.ok) {
        const msg = `已同步 ${data.synced_count ?? 0} 条；爬取 ${data.run_ok ? '成功' : '未执行或失败'}`;
        if (btnMedia) btnMedia.click();
        btnAhotnewsSync.textContent = msg;
        setTimeout(() => { btnAhotnewsSync.textContent = '从 ahotnews 同步'; }, 3000);
      } else {
        btnAhotnewsSync.textContent = data.reason || '同步失败';
        setTimeout(() => { btnAhotnewsSync.textContent = '从 ahotnews 同步'; }, 3000);
      }
    } catch (e) {
      btnAhotnewsSync.textContent = '同步失败';
      setTimeout(() => { btnAhotnewsSync.textContent = '从 ahotnews 同步'; }, 3000);
    } finally {
      btnAhotnewsSync.disabled = false;
    }
  });
}

if (btnMedia && mediaResult) {
  btnMedia.addEventListener('click', async () => {
    btnMedia.disabled = true;
    mediaResult.innerHTML = '<p class="loading">加载中...</p>';
    try {
      const res = await fetch(apiUrl('media_hot'));
      const data = await res.json();
      const items = data.items || [];
      if (!items.length) {
        mediaResult.innerHTML = '<p class="hint">暂无媒体热点，可添加「我的媒体链接」或点击「从 ahotnews 同步」</p>';
      } else {
        mediaResult.innerHTML = items.map(m => `
          <div class="trending-card">
            <div class="policy-header">
              <span class="policy-cat">${escapeHtml(m.platform || 'web')}</span>
            </div>
            <div class="value">${escapeHtml(m.title || '')}</div>
            <div class="label">${escapeHtml(m.author || '')} · ${m.publish_date || ''}</div>
            ${m.content_snippet ? `<p class="trending-note">${escapeHtml(m.content_snippet)}</p>` : ''}
            ${safeHref(m.url) ? `<a href="${safeHref(m.url)}" target="_blank" rel="noopener" class="policy-link">查看 →</a>` : ''}
          </div>
        `).join('');
      }
    } catch (e) {
      mediaResult.innerHTML = `<p class="error">${escapeHtml(e.message)}</p>`;
    } finally {
      btnMedia.disabled = false;
    }
  });
}

// 进入媒体 tab 时加载「我的媒体链接」
const panelMedia = document.getElementById('panel-media');
if (panelMedia && mediaLinksList) {
  const observer = new MutationObserver((mutations) => {
    mutations.forEach((m) => {
      if (m.attributeName === 'class' && panelMedia.classList.contains('active')) loadMediaLinks();
    });
  });
  observer.observe(panelMedia, { attributes: true });
  if (panelMedia.classList.contains('active')) loadMediaLinks();
}

/** 将周报中的简易 Markdown（### 标题、**粗体**、换行）转为安全 HTML */
function policySummaryToHtml(text) {
  if (!text || typeof text !== 'string') return '';
  var placeholders = [];
  var idx = 0;
  var s = text
    .replace(/###\s*(.+?)(?=\n|$)/gm, function(_, t) { placeholders.push(['h4', t]); return '\x01P' + (idx++) + '\x01'; })
    .replace(/\*\*(.+?)\*\*/g, function(_, t) { placeholders.push(['b', t]); return '\x01P' + (idx++) + '\x01'; });
  s = escapeHtml(s);
  for (var i = 0; i < placeholders.length; i++) {
    var tag = placeholders[i][0];
    var content = placeholders[i][1];
    s = s.replace('\x01P' + i + '\x01', tag === 'h4' ? '<h4 class="policy-insights-h4">' + escapeHtml(content) + '</h4>' : '<strong>' + escapeHtml(content) + '</strong>');
  }
  return s.replace(/\n/g, '<br>');
}

// 方向与行动建议（从 policy_analysis 表读取）
async function loadPolicyInsights() {
  const el = document.getElementById('policy-insights-result');
  if (!el) return;
  el.innerHTML = '<p class="loading">加载中...</p>';
  try {
    const res = await fetch(apiUrl('policies/insights'));
    const data = await res.json();
    const insights = data.insights || [];
    if (!insights.length) {
      el.innerHTML = '<p class="hint">' + escapeHtml(data.message || '暂无方向与行动建议，请先运行政策流水线（见 README）。') + '</p>';
      return;
    }
    const row = insights[0];
    const summary = row.summary || '';
    const directions = Array.isArray(row.directions) ? row.directions : [];
    const actionItems = Array.isArray(row.action_items) ? row.action_items : [];
    const created = row.created_at ? new Date(row.created_at).toLocaleString('zh-CN') : '';
    const summaryHtml = summary ? policySummaryToHtml(summary) : '';
    el.innerHTML =
      (created ? '<p class="policy-insights-meta">生成时间：' + escapeHtml(created) + '</p>' : '') +
      (summaryHtml ? '<div class="policy-insights-summary policy-insights-summary--md">' + summaryHtml + '</div>' : '') +
      (directions.length ? '<div class="policy-insights-directions"><strong>方向性思考</strong><ul>' + directions.map(d => '<li>' + escapeHtml(d) + '</li>').join('') + '</ul></div>' : '') +
      (actionItems.length ? '<div class="policy-insights-actions"><strong>行动建议</strong><ul>' + actionItems.map(a => '<li>' + escapeHtml(a) + '</li>').join('') + '</ul></div>' : '');
  } catch (e) {
    el.innerHTML = '<p class="error">' + escapeHtml(e.message) + '</p>';
  }
}

// 进入政策 tab 时：若未加载过列表或仍是「请点击…」提示，则自动拉取法务政策库（带分页）并加载方向与建议
const panelPolicies = document.getElementById('panel-policies');
if (panelPolicies && policyFilters) {
  const observer = new MutationObserver((mutations) => {
    mutations.forEach((m) => {
      if (m.attributeName === 'class' && panelPolicies.classList.contains('active')) {
        var resultEl = document.getElementById('policies-result');
        var hasHintOnly = resultEl && resultEl.innerText && resultEl.innerText.indexOf('请点击') >= 0;
        if (!policyFilters.querySelector('.filter-btn') || hasHintOnly) loadPolicies({});
        loadPolicyInsights();
      }
    });
  });
  observer.observe(panelPolicies, { attributes: true });
}

function escapeHtml(s) {
  if (s == null) return '';
  const div = document.createElement('div');
  div.textContent = s;
  return div.innerHTML;
}
