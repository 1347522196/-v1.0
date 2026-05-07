const state = {
  products: [],
  favorites: [],
  productTotal: 0,
  page: 1,
  pageSize: 12,
  sortBy: "comprehensive",
  sortOrder: "desc",
  keywords: [],
  dashboard: null,
  aiSettings: null,
};

const elements = {
  seedButton: document.getElementById("seedButton"),
  refreshAllButton: document.getElementById("refreshAllButton"),
  clearAllProductsButton: document.getElementById("clearAllProductsButton"),
  clearAllKeywordsButton: document.getElementById("clearAllKeywordsButton"),
  clearAllCompetitorsButton: document.getElementById("clearAllCompetitorsButton"),
  clearScrapeRunsButton: document.getElementById("clearScrapeRunsButton"),
  aiSettingsForm: document.getElementById("aiSettingsForm"),
  aiAnalyzeForm: document.getElementById("aiAnalyzeForm"),
  aiApiKey: document.getElementById("aiApiKey"),
  aiModel: document.getElementById("aiModel"),
  aiScope: document.getElementById("aiScope"),
  aiQuestion: document.getElementById("aiQuestion"),
  aiSettingsMeta: document.getElementById("aiSettingsMeta"),
  aiResultMeta: document.getElementById("aiResultMeta"),
  aiResult: document.getElementById("aiResult"),
  clearAiSettingsButton: document.getElementById("clearAiSettingsButton"),
  runAiAnalysisButton: document.getElementById("runAiAnalysisButton"),
  sortDrawerToggle: document.getElementById("sortDrawerToggle"),
  sortDrawer: document.getElementById("sortDrawer"),
  sortDrawerBackdrop: document.getElementById("sortDrawerBackdrop"),
  sortDrawerClose: document.getElementById("sortDrawerClose"),
  sortDrawerForm: document.getElementById("sortDrawerForm"),
  sortBy: document.getElementById("sortBy"),
  sortOrder: document.getElementById("sortOrder"),
  sortResetButton: document.getElementById("sortResetButton"),
  sortDescriptionTitle: document.getElementById("sortDescriptionTitle"),
  sortDescriptionBody: document.getElementById("sortDescriptionBody"),
  taskMessage: document.getElementById("taskMessage"),
  keywordForm: document.getElementById("keywordForm"),
  keywordTargetProducts: document.getElementById("keywordTargetProducts"),
  filterForm: document.getElementById("filterForm"),
  keywordTableBody: document.getElementById("keywordTableBody"),
  favoriteBoard: document.getElementById("favoriteBoard"),
  productTableBody: document.getElementById("productTableBody"),
  tableMeta: document.getElementById("tableMeta"),
  pageText: document.getElementById("pageText"),
  prevPage: document.getElementById("prevPage"),
  nextPage: document.getElementById("nextPage"),
  topKeywordsList: document.getElementById("topKeywordsList"),
  recentRunsList: document.getElementById("recentRunsList"),
  statusBreakdownList: document.getElementById("statusBreakdownList"),
  emptyStateTemplate: document.getElementById("emptyStateTemplate"),
  keywordFilter: document.getElementById("keywordFilter"),
  statProducts: document.getElementById("statProducts"),
  statKeywords: document.getElementById("statKeywords"),
  statCompetitors: document.getElementById("statCompetitors"),
  statAvgPrice: document.getElementById("statAvgPrice"),
  statAvgRating: document.getElementById("statAvgRating"),
  statFavorites: document.getElementById("statFavorites"),
};

const DEPARTMENT_OPTIONS = [
  { value: "", label: "不限定类目 / 全站搜索" },
  { value: "tools", label: "tools - 五金工具" },
  { value: "grocery", label: "grocery - 食品杂货" },
  { value: "electronics", label: "electronics - 电子产品" },
  { value: "office-products", label: "office-products - 办公用品" },
  { value: "industrial", label: "industrial - 工业用品" },
  { value: "automotive", label: "automotive - 汽车用品" },
  { value: "baby-products", label: "baby-products - 母婴用品" },
  { value: "beauty", label: "beauty - 美妆个护" },
  { value: "hpc", label: "hpc - 家清个护" },
  { value: "lawngarden", label: "lawngarden - 庭院园艺" },
  { value: "pets", label: "pets - 宠物用品" },
  { value: "arts-crafts", label: "arts-crafts - 手工艺品" },
  { value: "appliances", label: "appliances - 家电" },
  { value: "videogames", label: "videogames - 电子游戏" },
  { value: "mi", label: "mi - 乐器" },
  { value: "mobile", label: "mobile - 手机配件" },
  { value: "fashion", label: "fashion - 服饰" },
  { value: "kitchen", label: "kitchen - 厨房家居" },
  { value: "toys-and-games", label: "toys-and-games - 玩具游戏" },
];

const DEPARTMENT_LABELS = Object.fromEntries(
  DEPARTMENT_OPTIONS.map((item) => [item.value, item.label])
);

const SORT_OPTIONS = {
  comprehensive: {
    label: "综合排序",
    description: "综合机会分、评分、评论量、Prime、广告状态和收藏标记，适合优先看更值得研究的商品。",
  },
  opportunity_score: {
    label: "机会分排序",
    description: "优先显示系统判断更有操作空间的商品。",
  },
  estimated_sales: {
    label: "销量排序",
    description: "当前用评论数近似估算热度，适合先看更热门的商品。",
  },
  review_count: {
    label: "评论数排序",
    description: "优先显示评论沉淀更多的商品。",
  },
  rating: {
    label: "评分排序",
    description: "优先显示当前口碑更高的商品。",
  },
  price: {
    label: "价格排序",
    description: "适合从高客单价或低价格带两个方向筛商品。",
  },
  source_rank: {
    label: "搜索排名排序",
    description: "按搜索页里的出现位置排序，越靠前通常曝光越高。",
  },
  newest: {
    label: "最新采集排序",
    description: "优先查看刚刚采集回来的新数据。",
  },
  updated: {
    label: "最近更新排序",
    description: "优先查看最近被改过状态、备注或重新入库的商品。",
  },
  favorite: {
    label: "收藏优先排序",
    description: "优先显示你已经标记为重点的商品。",
  },
  prime: {
    label: "Prime 优先排序",
    description: "优先显示带 Prime 标记的商品。",
  },
};

function buildInlinePlaceholder(label = "Product") {
  const safeLabel = String(label || "Product").slice(0, 20);
  const svg = `
    <svg xmlns="http://www.w3.org/2000/svg" width="320" height="320" viewBox="0 0 320 320">
      <defs>
        <linearGradient id="g" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stop-color="#f2e2cc" />
          <stop offset="100%" stop-color="#d4b089" />
        </linearGradient>
      </defs>
      <rect width="320" height="320" rx="36" fill="url(#g)" />
      <rect x="28" y="28" width="264" height="264" rx="28" fill="rgba(255,255,255,0.55)" />
      <text x="160" y="150" text-anchor="middle" font-family="Segoe UI, Arial, sans-serif" font-size="28" font-weight="700" fill="#6f513d">No Image</text>
      <text x="160" y="192" text-anchor="middle" font-family="Segoe UI, Arial, sans-serif" font-size="18" fill="#7a604d">${safeLabel}</text>
    </svg>
  `.trim();
  return `data:image/svg+xml;charset=UTF-8,${encodeURIComponent(svg)}`;
}

function buildImageSrc(url, label) {
  if (!url || !/^https?:\/\//i.test(url)) {
    return buildInlinePlaceholder(label);
  }
  return `/api/image-proxy?url=${encodeURIComponent(url)}&label=${encodeURIComponent(label || "Product")}`;
}

function handleImageError(img, label) {
  img.onerror = null;
  img.src = buildInlinePlaceholder(label);
}

window.handleImageError = handleImageError;

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: {
      "Content-Type": "application/json",
    },
    ...options,
  });

  const isJson = response.headers.get("content-type")?.includes("application/json");
  const payload = isJson ? await response.json() : null;

  if (!response.ok) {
    throw new Error(payload?.detail || payload?.message || "请求失败");
  }
  return payload;
}

function setMessage(message, isError = false) {
  elements.taskMessage.textContent = message;
  elements.taskMessage.style.color = isError ? "var(--danger)" : "var(--text)";
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function formatNumber(value) {
  if (value === null || value === undefined || value === "") {
    return "暂无";
  }
  return Number(value).toLocaleString("zh-CN");
}

function formatPrice(value, currency = "USD") {
  if (value === null || value === undefined || value === "") {
    return "暂无价格";
  }
  return `${currency} ${Number(value).toFixed(2)}`;
}

function formatDate(value) {
  if (!value) {
    return "暂无";
  }
  return new Date(value).toLocaleString("zh-CN", { hour12: false });
}

function formatDepartmentLabel(value) {
  const key = String(value ?? "");
  return DEPARTMENT_LABELS[key] || key || "不限定类目 / 全站搜索";
}

function formatBought(value) {
  if (value === null || value === undefined || value === "") {
    return "暂无";
  }
  return `${formatNumber(value)} / 月`;
}

function renderOpportunityBreakdown(item, compact = false) {
  const breakdown = Array.isArray(item.opportunity_breakdown) ? item.opportunity_breakdown : [];
  if (!breakdown.length) {
    return "";
  }

  const rows = breakdown
    .map(
      (part) => `
        <div class="score-breakdown-row">
          <strong>${escapeHtml(part.label)}</strong>
          <span>权重 ${part.weight}%</span>
          <span>子分 ${part.component_score}</span>
          <span>贡献 ${part.contribution}</span>
          <small>${escapeHtml(part.reason || "")}</small>
        </div>
      `
    )
    .join("");

  return `
    <details class="score-breakdown ${compact ? "score-breakdown-compact" : ""}">
      <summary>机会分 ${item.opportunity_score ?? 0} · 查看组成与权重</summary>
      <div class="score-breakdown-body">${rows}</div>
    </details>
  `;
}

function containsChinese(value) {
  return /[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]/.test(String(value || ""));
}

function looksLikeRealAsin(value) {
  const asin = String(value || "").trim().toUpperCase();
  if (asin.length !== 10) return false;
  if (!/^[A-Z0-9]+$/.test(asin)) return false;
  if (asin.startsWith("B0DEMO")) return false;
  return true;
}

function buildKeepaUrl(asin, marketplace) {
  if (!looksLikeRealAsin(asin)) {
    return "";
  }

  const domainMap = {
    com: 1,
    "co.uk": 2,
    de: 3,
    "co.jp": 5,
  };
  const domainId = domainMap[String(marketplace || "com")];
  if (!domainId) {
    return "";
  }
  return `https://keepa.com/#!product/${domainId}-${encodeURIComponent(String(asin).trim().toUpperCase())}`;
}

function buildCamelUrl(asin, marketplace) {
  if (!looksLikeRealAsin(asin)) {
    return "";
  }

  const normalizedAsin = encodeURIComponent(String(asin).trim().toUpperCase());
  const hostMap = {
    com: "https://camelcamelcamel.com",
    "co.uk": "https://uk.camelcamelcamel.com",
    de: "https://de.camelcamelcamel.com",
  };
  const host = hostMap[String(marketplace || "com")];
  if (!host) {
    return "";
  }
  return `${host}/product/${normalizedAsin}`;
}

function renderHistoryActions(asin, marketplace) {
  const keepaUrl = buildKeepaUrl(asin, marketplace);
  const camelUrl = buildCamelUrl(asin, marketplace);
  const actions = [];

  if (keepaUrl) {
    actions.push(
      `<a class="button button-ghost link-button" href="${keepaUrl}" target="_blank" rel="noreferrer">Keepa 历史</a>`
    );
  }

  if (camelUrl) {
    actions.push(
      `<a class="button button-ghost link-button" href="${camelUrl}" target="_blank" rel="noreferrer">Camel 历史</a>`
    );
  }

  if (!actions.length) {
    actions.push(`<span class="button button-ghost is-disabled" title="演示数据或无效 ASIN 暂时无法打开历史图">无历史图</span>`);
  }

  return actions.join("");
}

function currentSortLabel() {
  return SORT_OPTIONS[state.sortBy]?.label || "综合排序";
}

function updateSortDescription() {
  const selected = SORT_OPTIONS[elements.sortBy.value] || SORT_OPTIONS.comprehensive;
  elements.sortDescriptionTitle.textContent = selected.label;
  elements.sortDescriptionBody.textContent = selected.description;
}

function openSortDrawer() {
  elements.sortBy.value = state.sortBy;
  elements.sortOrder.value = state.sortOrder;
  updateSortDescription();
  elements.sortDrawer.setAttribute("aria-hidden", "false");
  elements.sortDrawer.classList.add("is-open");
  elements.sortDrawerBackdrop.hidden = false;
  document.body.classList.add("drawer-open");
}

function closeSortDrawer() {
  elements.sortDrawer.setAttribute("aria-hidden", "true");
  elements.sortDrawer.classList.remove("is-open");
  elements.sortDrawerBackdrop.hidden = true;
  document.body.classList.remove("drawer-open");
}

function populateDepartmentSelects() {
  const markup = DEPARTMENT_OPTIONS.map(
    (item) => `<option value="${escapeHtml(item.value)}">${escapeHtml(item.label)}</option>`
  ).join("");
  document.getElementById("keywordDepartment").innerHTML = markup;
}

function readTargetProducts() {
  const value = Number(elements.keywordTargetProducts.value);
  if (!Number.isFinite(value)) {
    return 100;
  }
  return Math.max(10, Math.min(200, Math.round(value)));
}

function buildProductQuery() {
  const params = new URLSearchParams();
  const query = document.getElementById("searchQuery").value.trim();
  const status = document.getElementById("statusFilter").value;
  const marketplace = document.getElementById("filterMarketplace").value;
  const keyword = document.getElementById("keywordFilter").value;
  const minPrice = document.getElementById("minPrice").value;
  const maxPrice = document.getElementById("maxPrice").value;
  const onlyFavorites = document.getElementById("onlyFavorites").checked;

  if (query) params.set("query", query);
  if (status) params.set("status", status);
  if (marketplace) params.set("marketplace", marketplace);
  if (keyword) params.set("keyword", keyword);
  if (minPrice) params.set("min_price", minPrice);
  if (maxPrice) params.set("max_price", maxPrice);
  if (onlyFavorites) params.set("only_favorites", "true");

  params.set("sort_by", state.sortBy);
  params.set("sort_order", state.sortOrder);
  params.set("page", String(state.page));
  params.set("page_size", String(state.pageSize));
  return params.toString();
}

async function loadDashboard() {
  state.dashboard = await api("/api/dashboard");
  renderDashboard();
}

async function loadAISettings() {
  state.aiSettings = await api("/api/ai/settings");
  renderAISettings();
}

async function loadKeywords() {
  state.keywords = await api("/api/keywords");
  renderKeywords();
  renderKeywordFilter();
}

async function loadFavorites() {
  const payload = await api("/api/products?only_favorites=true&page=1&page_size=100&sort_by=updated&sort_order=desc");
  state.favorites = payload.items;
  renderFavorites();
}

async function loadProducts() {
  const payload = await api(`/api/products?${buildProductQuery()}`);
  state.products = payload.items;
  state.productTotal = payload.total;
  renderProducts();
}

async function refreshAll() {
  await Promise.all([loadDashboard(), loadKeywords(), loadFavorites(), loadProducts(), loadAISettings()]);
}

function renderDashboard() {
  if (!state.dashboard) {
    return;
  }

  const totals = state.dashboard.totals;
  elements.statProducts.textContent = String(totals.products);
  elements.statKeywords.textContent = String(totals.keywords);
  elements.statCompetitors.textContent = String(totals.favorites);
  elements.statAvgPrice.textContent = formatPrice(totals.avg_price);
  elements.statAvgRating.textContent = `${totals.avg_rating || 0}`;
  elements.statFavorites.textContent = String(totals.active_keywords);

  elements.topKeywordsList.innerHTML = renderStackList(
    state.dashboard.top_keywords,
    (item) => `
      <div class="stack-item">
        <strong>${escapeHtml(item.keyword)}</strong>
        <span>${escapeHtml(item.marketplace)} · ${item.product_count} 个商品 · 平均机会分 ${item.avg_opportunity_score || 0}</span>
      </div>
    `,
    "还没有形成关键词分析数据"
  );

  elements.recentRunsList.innerHTML = renderStackList(
    state.dashboard.recent_runs,
    (item) => `
      <div class="stack-item">
        <strong>${escapeHtml(item.keyword)} · ${escapeHtml(item.marketplace)}</strong>
        <span>${escapeHtml(item.status)} · 抓取 ${item.scraped_count} / 写入 ${item.saved_count}</span>
        <small>${escapeHtml(item.message)} · ${escapeHtml(formatDate(item.created_at))}</small>
      </div>
    `,
    "还没有采集记录"
  );

  elements.statusBreakdownList.innerHTML = state.dashboard.status_breakdown.length
    ? state.dashboard.status_breakdown
        .map(
          (item) => `
            <div class="status-chip">
              <strong>${escapeHtml(item.label)}</strong>
              <span>${item.count}</span>
            </div>
          `
        )
        .join("")
    : `<div class="empty-inline">还没有商品状态数据</div>`;
}

function renderStackList(items, renderItem, emptyText) {
  if (!items.length) {
    return `<div class="empty-inline">${escapeHtml(emptyText)}</div>`;
  }
  return items.map(renderItem).join("");
}

function renderAISettings() {
  if (!state.aiSettings) {
    return;
  }
  elements.aiModel.value = state.aiSettings.model || "deepseek-v4-flash";
  if (state.aiSettings.has_api_key) {
    elements.aiApiKey.placeholder = `当前会话已填写：${state.aiSettings.masked_api_key}`;
    elements.aiSettingsMeta.textContent = `当前模型：${state.aiSettings.model} · 仅在本次运行有效`;
  } else {
    elements.aiApiKey.placeholder = "输入 DeepSeek API Key（仅本次运行有效）";
    elements.aiSettingsMeta.textContent = "尚未配置 API Key，关闭程序后不会保留";
  }
}

function renderKeywordFilter() {
  const current = elements.keywordFilter.value;
  elements.keywordFilter.innerHTML = [
    `<option value="">全部关键词</option>`,
    ...state.keywords.map(
      (item) => `<option value="${escapeHtml(item.keyword)}">${escapeHtml(item.keyword)} · ${escapeHtml(item.marketplace)}</option>`
    ),
  ].join("");
  elements.keywordFilter.value = current;
}

function renderKeywords() {
  if (!state.keywords.length) {
    elements.keywordTableBody.innerHTML = `<tr><td colspan="7">${elements.emptyStateTemplate.innerHTML}</td></tr>`;
    return;
  }

  elements.keywordTableBody.innerHTML = state.keywords
    .map(
      (item) => `
        <tr data-id="${item.id}">
          <td>
            <strong>${escapeHtml(item.keyword)}</strong>
            <div class="cell-subtext">${escapeHtml(formatDepartmentLabel(item.department))}</div>
          </td>
          <td>${escapeHtml(item.marketplace)}</td>
          <td>
            <select data-role="priority">
              ${[5, 4, 3, 2, 1]
                .map((priority) => `<option value="${priority}" ${Number(item.priority) === priority ? "selected" : ""}>${priority}</option>`)
                .join("")}
            </select>
          </td>
          <td>
            <select data-role="status">
              ${["active", "paused", "archived"]
                .map((status) => `<option value="${status}" ${item.status === status ? "selected" : ""}>${status}</option>`)
                .join("")}
            </select>
          </td>
          <td>
            <div class="cell-subtext">${escapeHtml(formatDate(item.last_scraped_at))}</div>
            <div class="cell-subtext">最近结果 ${item.last_result_count || 0}</div>
          </td>
          <td>
            <input data-role="note" type="text" value="${escapeHtml(item.note || "")}" placeholder="关键词备注" />
          </td>
          <td>
            <div class="row-actions">
              <button type="button" class="button button-primary" data-action="save-keyword">保存</button>
              <button type="button" class="button button-secondary" data-action="scrape-keyword">采集</button>
              <button type="button" class="button button-ghost" data-action="delete-keyword">删除</button>
            </div>
          </td>
        </tr>
      `
    )
    .join("");
}

function renderFavorites() {
  if (!state.favorites.length) {
    elements.favoriteBoard.innerHTML = elements.emptyStateTemplate.innerHTML;
    return;
  }

  elements.favoriteBoard.innerHTML = state.favorites
    .map(
      (item) => `
        <article class="favorite-card" data-id="${item.id}">
          <div class="mini-product favorite-head">
            <img class="product-thumb small-thumb" src="${buildImageSrc(item.image_url, item.title)}" alt="${escapeHtml(item.title)}" onerror="handleImageError(this, '${escapeHtml(item.title)}')" />
            <div>
              <strong>${escapeHtml(item.title)}</strong>
              <div class="cell-subtext">ASIN: ${escapeHtml(item.asin)}</div>
              <div class="cell-subtext">${escapeHtml(item.marketplace)} · ${escapeHtml(item.keyword || "未标记关键词")}</div>
            </div>
          </div>
          <div class="favorite-meta">
            <span>${escapeHtml(formatPrice(item.price, item.currency))}</span>
            <span>评分 ${item.rating ?? "暂无"} / 评论 ${item.review_count ?? "暂无"}</span>
            <span>月购买量 ${escapeHtml(formatBought(item.estimated_monthly_bought))}</span>
            <span>机会分 ${item.opportunity_score ?? 0}</span>
            <span>${escapeHtml(formatDate(item.updated_at || item.scraped_at))}</span>
          </div>
          ${renderOpportunityBreakdown(item, true)}
          <div class="row-actions">
            ${renderHistoryActions(item.asin, item.marketplace)}
            <a class="button button-ghost link-button" href="/api/products/${item.id}/open" target="_blank" rel="noreferrer">打开商品</a>
            <button type="button" class="button button-secondary" data-action="favorite-product">取消收藏</button>
          </div>
        </article>
      `
    )
    .join("");
}

function renderAIResult(text, meta = "") {
  elements.aiResult.textContent = text;
  elements.aiResultMeta.textContent = meta || "AI 分析结果已更新";
}

function renderProducts() {
  if (!state.products.length) {
    elements.productTableBody.innerHTML = `<tr><td colspan="6">${elements.emptyStateTemplate.innerHTML}</td></tr>`;
    elements.tableMeta.textContent = `共 0 条记录 · 当前排序：${currentSortLabel()} / ${state.sortOrder === "desc" ? "降序" : "升序"}`;
    elements.pageText.textContent = `第 ${state.page} 页`;
    syncPager();
    return;
  }

  elements.productTableBody.innerHTML = state.products
    .map(
      (item) => `
        <tr data-id="${item.id}" data-asin="${escapeHtml(item.asin)}" data-marketplace="${escapeHtml(item.marketplace)}" data-keyword="${escapeHtml(item.keyword)}">
          <td>
            <div class="product-cell">
              <img class="product-thumb" src="${buildImageSrc(item.image_url, item.title)}" alt="${escapeHtml(item.title)}" onerror="handleImageError(this, '${escapeHtml(item.title)}')" />
              <div>
                <div class="product-title">${escapeHtml(item.title)}</div>
                <div class="product-meta">
                  <span class="pill">ASIN: ${escapeHtml(item.asin)}</span>
                  <span class="pill">${escapeHtml(item.keyword)}</span>
                  <span class="pill">${escapeHtml(item.brand || "未知品牌")}</span>
                  <span class="pill">机会分 ${item.opportunity_score ?? 0}</span>
                  <span class="pill">月购买量 ${escapeHtml(formatBought(item.estimated_monthly_bought))}</span>
                  ${item.badge ? `<span class="pill">${escapeHtml(item.badge)}</span>` : ""}
                  ${item.is_prime ? `<span class="pill">Prime</span>` : ""}
                  ${item.is_sponsored ? `<span class="pill sponsored">Sponsored</span>` : ""}
                  ${item.is_favorite ? `<span class="pill favorite">Favorite</span>` : ""}
                </div>
                ${renderOpportunityBreakdown(item)}
              </div>
            </div>
          </td>
          <td>
            <div class="meta-stack">
              <span>${escapeHtml(item.marketplace)} · 排名 ${item.source_rank ?? "-"}</span>
              <span>${escapeHtml(item.category_path || "Hardware > Tools")}</span>
              <span>${escapeHtml(formatDate(item.scraped_at))}</span>
            </div>
          </td>
          <td>
            <div class="meta-stack">
              <span class="price-text">${escapeHtml(formatPrice(item.price, item.currency))}</span>
              <span>评分 ${item.rating ?? "暂无"} / 评论 ${item.review_count ?? "暂无"}</span>
              <span>月购买量 ${escapeHtml(formatBought(item.estimated_monthly_bought))}</span>
              <span>${escapeHtml(item.availability || "状态未知")}</span>
            </div>
          </td>
          <td>
            <select class="status-select" data-role="status">
              ${["new", "tracking", "follow_up", "archived"]
                .map((status) => `<option value="${status}" ${item.custom_status === status ? "selected" : ""}>${status}</option>`)
                .join("")}
            </select>
          </td>
          <td>
            <textarea class="note-input" data-role="note" placeholder="运营备注">${escapeHtml(item.note || "")}</textarea>
          </td>
          <td>
            <div class="row-actions">
              <button type="button" class="button button-secondary" data-action="favorite-product">${item.is_favorite ? "取消收藏" : "收藏"}</button>
              <button type="button" class="button button-primary" data-action="save-product">保存</button>
              ${renderHistoryActions(item.asin, item.marketplace)}
              <a class="button button-ghost link-button" href="/api/products/${item.id}/open" target="_blank" rel="noreferrer">打开商品</a>
              <button type="button" class="button button-ghost" data-action="delete-product">删除</button>
            </div>
          </td>
        </tr>
      `
    )
    .join("");

  elements.tableMeta.textContent = `共 ${state.productTotal} 条记录 · 当前排序：${currentSortLabel()} / ${state.sortOrder === "desc" ? "降序" : "升序"}`;
  elements.pageText.textContent = `第 ${state.page} 页`;
  syncPager();
}

function syncPager() {
  const totalPages = Math.max(1, Math.ceil(state.productTotal / state.pageSize));
  elements.prevPage.disabled = state.page <= 1;
  elements.nextPage.disabled = state.page >= totalPages;
}

async function handleSeedData() {
  elements.seedButton.disabled = true;
  setMessage("正在导入演示数据...");
  try {
    await api("/api/demo-seed", { method: "POST" });
    state.page = 1;
    await refreshAll();
    setMessage("演示数据已导入。");
  } catch (error) {
    setMessage(error.message, true);
  } finally {
    elements.seedButton.disabled = false;
  }
}

async function handleRefreshAll() {
  elements.refreshAllButton.disabled = true;
  setMessage("正在刷新全部数据...");
  try {
    await refreshAll();
    setMessage("数据已刷新。");
  } catch (error) {
    setMessage(error.message, true);
  } finally {
    elements.refreshAllButton.disabled = false;
  }
}

async function handleKeywordCreate(event) {
  event.preventDefault();
  const submitButton = elements.keywordForm.querySelector("button[type='submit']");
  submitButton.disabled = true;
  setMessage("正在新增关键词...");

  try {
    await api("/api/keywords", {
      method: "POST",
      body: JSON.stringify({
        keyword: document.getElementById("keywordName").value.trim(),
        marketplace: document.getElementById("keywordMarketplace").value,
        department: document.getElementById("keywordDepartment").value.trim(),
        priority: Number(document.getElementById("keywordPriority").value),
        note: document.getElementById("keywordNote").value.trim(),
      }),
    });

    elements.keywordForm.reset();
    document.getElementById("keywordDepartment").value = "";
    document.getElementById("keywordPriority").value = "3";
    elements.keywordTargetProducts.value = "100";
    setMessage("关键词已加入关键词库。");
    await Promise.all([loadKeywords(), loadDashboard()]);
  } catch (error) {
    setMessage(error.message, true);
  } finally {
    submitButton.disabled = false;
  }
}

async function handleAISettingsSubmit(event) {
  event.preventDefault();
  const submitButton = elements.aiSettingsForm.querySelector("button[type='submit']");
  submitButton.disabled = true;
  setMessage("正在应用本次 AI 设置...");

  try {
    const apiKey = elements.aiApiKey.value.trim();
    if (!apiKey && !state.aiSettings?.has_api_key) {
      throw new Error("请先输入 DeepSeek API Key。");
    }

    const payload = await api("/api/ai/settings", {
      method: "POST",
      body: JSON.stringify({
        api_key: apiKey,
        model: elements.aiModel.value,
      }),
    });
    elements.aiApiKey.value = "";
    state.aiSettings = payload;
    renderAISettings();
    setMessage(payload.message || "AI 设置已写入本次运行。");
  } catch (error) {
    setMessage(error.message, true);
  } finally {
    submitButton.disabled = false;
  }
}

async function handleClearAISettings() {
  if (!window.confirm("确认清空本次运行里的 DeepSeek API Key 吗？")) {
    return;
  }

  elements.clearAiSettingsButton.disabled = true;
  try {
    const result = await api("/api/ai/settings", { method: "DELETE" });
    elements.aiApiKey.value = "";
    await loadAISettings();
    renderAIResult("可以先输入本次会话的 API Key，再选择“收藏夹 / 商品库 / 关键词库”开始分析。", "AI 设置已清空");
    setMessage(result.message || "AI 设置已清空。");
  } catch (error) {
    setMessage(error.message, true);
  } finally {
    elements.clearAiSettingsButton.disabled = false;
  }
}

async function handleAIAnalyze(event) {
  event.preventDefault();
  elements.runAiAnalysisButton.disabled = true;
  const scopeMap = {
    favorites: "收藏夹",
    products: "商品库",
    keywords: "关键词库",
  };
  const scopeLabel = scopeMap[elements.aiScope.value] || "收藏夹";
  setMessage(`正在用 DeepSeek 分析${scopeLabel}...`);
  renderAIResult("AI 正在分析中，请稍候...", `分析范围：${scopeLabel}`);

  try {
    const result = await api("/api/ai/analyze", {
      method: "POST",
      body: JSON.stringify({
        scope: elements.aiScope.value,
        question: elements.aiQuestion.value.trim(),
      }),
    });
    const summary = result.dataset_summary || {};
    renderAIResult(
      result.analysis || "AI 没有返回内容。",
      `模型：${result.model} · 范围：${scopeLabel} · 总量 ${summary.total_items || 0} · 送样 ${summary.sample_size || 0}`
    );
    setMessage(`${scopeLabel} AI 分析完成。`);
  } catch (error) {
    renderAIResult(
      `AI 分析失败：${error.message}`,
      "分析失败"
    );
    setMessage(error.message, true);
  } finally {
    elements.runAiAnalysisButton.disabled = false;
  }
}

function handleProductFilter(event) {
  event.preventDefault();
  state.page = 1;
  loadProducts().catch((error) => setMessage(error.message, true));
}

async function handleKeywordRowClick(event) {
  const button = event.target.closest("[data-action]");
  if (!button) return;

  const row = button.closest("tr[data-id]");
  if (!row) return;

  const keywordId = row.dataset.id;
  button.disabled = true;

  try {
    if (button.dataset.action === "save-keyword") {
      await api(`/api/keywords/${keywordId}`, {
        method: "PATCH",
        body: JSON.stringify({
          status: row.querySelector("[data-role='status']").value,
          priority: Number(row.querySelector("[data-role='priority']").value),
          note: row.querySelector("[data-role='note']").value,
        }),
      });
      setMessage("关键词已更新。");
    }

    if (button.dataset.action === "scrape-keyword") {
      const targetProducts = readTargetProducts();
      const result = await api(`/api/keywords/${keywordId}/scrape?target_products=${targetProducts}`, {
        method: "POST",
      });
      const warningText = result.warning ? ` ${result.warning}` : "";
      setMessage(
        `${result.keyword} 采集完成，目标 ${result.target_products} 条，实际抓取 ${result.scraped_count} 条。${warningText}`
      );
    }

    if (button.dataset.action === "delete-keyword") {
      if (!window.confirm("确认删除这个关键词吗？")) return;
      await api(`/api/keywords/${keywordId}`, { method: "DELETE" });
      setMessage("关键词已删除。");
    }

    await refreshAll();
  } catch (error) {
    setMessage(error.message, true);
  } finally {
    button.disabled = false;
  }
}

async function applyFavoriteToggle(productId, nextMessage) {
  await api(`/api/products/${productId}/favorite`, { method: "POST" });
  setMessage(nextMessage);
  await Promise.all([loadFavorites(), loadProducts(), loadDashboard()]);
}

async function handleFavoriteBoardClick(event) {
  const button = event.target.closest("[data-action]");
  if (!button) return;
  const card = button.closest("[data-id]");
  if (!card) return;

  if (button.dataset.action === "favorite-product") {
    button.disabled = true;
    try {
      await applyFavoriteToggle(card.dataset.id, "收藏状态已更新。");
    } catch (error) {
      setMessage(error.message, true);
    } finally {
      button.disabled = false;
    }
  }
}

async function handleProductRowClick(event) {
  const button = event.target.closest("[data-action]");
  if (!button) return;

  const row = button.closest("tr[data-id]");
  if (!row) return;

  const productId = row.dataset.id;
  button.disabled = true;

  try {
    if (button.dataset.action === "save-product") {
      await api(`/api/products/${productId}`, {
        method: "PATCH",
        body: JSON.stringify({
          custom_status: row.querySelector("[data-role='status']").value,
          note: row.querySelector("[data-role='note']").value,
        }),
      });
      setMessage("商品信息已更新。");
      await Promise.all([loadProducts(), loadFavorites(), loadDashboard()]);
    }

    if (button.dataset.action === "favorite-product") {
      await applyFavoriteToggle(productId, "收藏状态已更新。");
    }

    if (button.dataset.action === "delete-product") {
      if (!window.confirm("确认删除这条商品记录吗？")) return;
      await api(`/api/products/${productId}`, { method: "DELETE" });
      setMessage("商品已删除。");
      await Promise.all([loadProducts(), loadFavorites(), loadDashboard()]);
    }
  } catch (error) {
    setMessage(error.message, true);
  } finally {
    button.disabled = false;
  }
}

async function handleClearAll(path, confirmMessage, button, successMessage) {
  if (!window.confirm(confirmMessage)) return;

  button.disabled = true;
  try {
    const result = await api(path, { method: "DELETE" });
    setMessage(result?.message || successMessage);
    state.page = 1;
    await refreshAll();
  } catch (error) {
    setMessage(error.message, true);
  } finally {
    button.disabled = false;
  }
}

async function handleSortApply(event) {
  event.preventDefault();
  state.sortBy = elements.sortBy.value;
  state.sortOrder = elements.sortOrder.value;
  state.page = 1;
  closeSortDrawer();
  setMessage(`已切换到${currentSortLabel()}。`);
  await loadProducts();
}

function handleSortReset() {
  elements.sortBy.value = "comprehensive";
  elements.sortOrder.value = "desc";
  updateSortDescription();
}

function handlePrevPage() {
  if (state.page <= 1) return;
  state.page -= 1;
  loadProducts().catch((error) => setMessage(error.message, true));
}

function handleNextPage() {
  const totalPages = Math.max(1, Math.ceil(state.productTotal / state.pageSize));
  if (state.page >= totalPages) return;
  state.page += 1;
  loadProducts().catch((error) => setMessage(error.message, true));
}

populateDepartmentSelects();
updateSortDescription();

elements.seedButton.addEventListener("click", handleSeedData);
elements.refreshAllButton.addEventListener("click", handleRefreshAll);
elements.clearAllProductsButton.addEventListener("click", () =>
  handleClearAll("/api/products", "确认清空整个商品库吗？此操作不可恢复。", elements.clearAllProductsButton, "商品库已清空。")
);
elements.clearAllKeywordsButton.addEventListener("click", () =>
  handleClearAll("/api/keywords", "确认清空整个关键词库吗？此操作不可恢复。", elements.clearAllKeywordsButton, "关键词库已清空。")
);
elements.clearAllCompetitorsButton.addEventListener("click", () =>
  handleClearAll("/api/competitors", "确认清空旧竞品库吗？此操作不可恢复。", elements.clearAllCompetitorsButton, "旧竞品库已清空。")
);
elements.clearScrapeRunsButton.addEventListener("click", () =>
  handleClearAll("/api/scrape-runs", "确认清空采集记录吗？此操作不可恢复。", elements.clearScrapeRunsButton, "采集记录已清空。")
);
elements.sortDrawerToggle.addEventListener("click", openSortDrawer);
elements.sortDrawerClose.addEventListener("click", closeSortDrawer);
elements.sortDrawerBackdrop.addEventListener("click", closeSortDrawer);
elements.sortBy.addEventListener("change", updateSortDescription);
elements.sortResetButton.addEventListener("click", handleSortReset);
elements.sortDrawerForm.addEventListener("submit", (event) => {
  handleSortApply(event).catch((error) => setMessage(error.message, true));
});
elements.keywordForm.addEventListener("submit", handleKeywordCreate);
elements.aiSettingsForm.addEventListener("submit", handleAISettingsSubmit);
elements.aiAnalyzeForm.addEventListener("submit", handleAIAnalyze);
elements.clearAiSettingsButton.addEventListener("click", () => {
  handleClearAISettings().catch((error) => setMessage(error.message, true));
});
elements.filterForm.addEventListener("submit", handleProductFilter);
elements.keywordTableBody.addEventListener("click", handleKeywordRowClick);
elements.favoriteBoard.addEventListener("click", handleFavoriteBoardClick);
elements.productTableBody.addEventListener("click", handleProductRowClick);
elements.prevPage.addEventListener("click", handlePrevPage);
elements.nextPage.addEventListener("click", handleNextPage);

refreshAll()
  .then(() => setMessage("系统已就绪。"))
  .catch((error) => setMessage(error.message, true));
