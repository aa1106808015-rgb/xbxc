(function () {
  "use strict";

  const RECIPES = Array.isArray(window.XIAOBAI_RECIPES) ? window.XIAOBAI_RECIPES : [];
  const CUSTOM_STORE = window.XiaoBaiMyRecipes || null;
  const WISHLIST = window.XiaoBaiWishlist || null;
  const LEVEL_KEYS = [
    "xiaobai-level1-done-v1",
    "xiaobai-level2-done-v1",
    "xiaobai-level3-done-v1",
  ];
  const RECORD_KEY = "xiaobai-recipe-records-v1";
  const HISTORY_KEY = "xiaobai-search-history-v1";

  const state = {
    q: "",
    level: "all",
    tag: "all",
    progress: "all",
    source: "all",
  };

  const searchInput = document.getElementById("searchInput");
  const searchForm = document.getElementById("searchForm");
  const clearBtn = document.getElementById("clearBtn");
  const results = document.getElementById("results");
  const resultCount = document.getElementById("resultCount");
  const activeQuery = document.getElementById("activeQuery");
  const emptyState = document.getElementById("emptyState");
  const unlockPanel = document.getElementById("unlockPanel");
  const tagFilters = document.getElementById("tagFilters");
  const recentWrap = document.getElementById("recentWrap");
  const recentChips = document.getElementById("recentChips");

  function storageGet(key) {
    try {
      return window.localStorage.getItem(key);
    } catch (error) {
      return null;
    }
  }

  function storageSet(key, value) {
    try {
      window.localStorage.setItem(key, value);
    } catch (error) {
      /* 浏览器禁用存储时，搜索本身仍可使用 */
    }
  }

  function parseJSON(raw, fallback) {
    if (!raw) return fallback;
    try {
      return JSON.parse(raw);
    } catch (error) {
      return fallback;
    }
  }

  function loadRecords() {
    const records = parseJSON(storageGet(RECORD_KEY), {});
    return records && typeof records === "object" ? records : {};
  }

  function loadDoneIds() {
    const done = new Set();
    for (const key of LEVEL_KEYS) {
      const ids = parseJSON(storageGet(key), []);
      if (Array.isArray(ids)) ids.forEach((id) => done.add(id));
    }
    const records = loadRecords();
    Object.keys(records).forEach((id) => {
      if (records[id] && records[id].done) done.add(id);
    });
    return done;
  }

  function allRecipes() {
    const custom = CUSTOM_STORE ? CUSTOM_STORE.loadForSearch() : [];
    return [...RECIPES, ...custom];
  }

  function escapeHtml(value) {
    return String(value == null ? "" : value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  function normalize(value) {
    return String(value == null ? "" : value)
      .toLowerCase()
      .replace(/\s+/g, "")
      .replace(/[，,。、！!？?：:；;（）()「」『』“”‘’·\-—_/]/g, "");
  }

  function tokenize(query) {
    return String(query || "")
      .split(/[\s,，、;；]+/)
      .map(normalize)
      .filter(Boolean);
  }

  function highlight(text, tokens) {
    let html = escapeHtml(text);
    for (const token of tokens) {
      if (!token) continue;
      const escaped = token.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
      html = html.replace(new RegExp(`(${escaped})`, "ig"), "<mark>$1</mark>");
    }
    return html;
  }

  function scoreRecipe(recipe, tokens) {
    let total = 0;

    for (const token of tokens) {
      let best = 0;

      const hit = (text, weight) => {
        const value = normalize(text);
        if (!value) return;
        if (value === token) {
          best = Math.max(best, weight + 12);
        } else if (value.includes(token)) {
          best = Math.max(best, weight);
        }
      };

      hit(recipe.name, 120);
      for (const alias of recipe.aliases || []) hit(alias, 106);
      for (const tag of recipe.tags || []) hit(tag, 72);
      for (const item of recipe.ingredients || []) {
        hit(item.name, 82);
        hit(item.amount, 28);
      }
      for (const step of recipe.steps || []) {
        hit(step.title, 74);
        hit(step.text, 50);
        hit(step.check, 36);
      }
      hit(recipe.lead, 42);
      hit(recipe.lesson, 30);
      for (const badge of recipe.badges || []) hit(badge, 26);

      if (!best) return 0;
      total += best;
    }

    return total;
  }

  function findSnippet(recipe, tokens) {
    if (!tokens.length) return "";

    for (const token of tokens) {
      for (const item of recipe.ingredients || []) {
        if (normalize(item.name).includes(token)) {
          return `用料：${item.name} ${item.amount}`.trim();
        }
      }
      for (const step of recipe.steps || []) {
        if (normalize(step.title).includes(token)) {
          return `步骤：${step.title}`;
        }
        if (normalize(step.text).includes(token)) {
          return `步骤：${step.text}`;
        }
      }
      for (const tag of recipe.tags || []) {
        if (normalize(tag).includes(token)) {
          return `类型：${tag}`;
        }
      }
      if (normalize(recipe.lead).includes(token)) {
        return `简介：${recipe.lead}`;
      }
    }

    return "";
  }

  function matchesFilters(recipe, done) {
    if (state.level !== "all" && String(recipe.level) !== state.level) return false;
    if (state.tag !== "all" && !(recipe.tags || []).includes(state.tag)) return false;
    if (state.progress === "done" && !done.has(recipe.id)) return false;
    if (state.progress === "todo" && done.has(recipe.id)) return false;
    const source = recipe.source || "builtin";
    if (state.source !== "all" && source !== state.source) return false;
    return true;
  }

  function cardHTML(recipe, tokens) {
    const snippet = findSnippet(recipe, tokens);
    const tags = (recipe.tags || []).slice(0, 4);
    const lessonText = (recipe.lesson || "").split("·")[0].trim() || "基础课";
    const sourceTag = recipe.source === "custom" ? `<span class="source-tag">我的菜谱</span>` : "";
    const wished = WISHLIST ? WISHLIST.has(recipe.id) : false;

    return `
      <article class="card" data-recipe-id="${escapeHtml(recipe.id)}">
        <a class="card-link" href="${escapeHtml(recipe.url)}">
          <div class="cover">
            <img src="${escapeHtml(recipe.cover)}" alt="${escapeHtml(recipe.name)}成品实拍图" loading="lazy">
            <span class="level">${escapeHtml(lessonText)} · ${escapeHtml(recipe.difficulty)}</span>
          </div>
          <div class="card-body">
            <div class="card-meta">
              <span>${escapeHtml(recipe.lesson)}</span>
              <span>${escapeHtml(recipe.time)}</span>
              <span>${escapeHtml(recipe.cost)}</span>
            </div>
            <h3>${highlight(recipe.name, tokens)}</h3>
            <p>${escapeHtml(recipe.lead)}</p>
            <div class="card-tags">${sourceTag}${tags.map((tag) => `<span>${escapeHtml(tag)}</span>`).join("")}</div>
            ${snippet ? `<p class="match"><b>匹配：</b>${escapeHtml(snippet)}</p>` : ""}
          </div>
        </a>
        <div class="card-foot">
          <button class="wish-btn${wished ? " active" : ""}" type="button" data-wish="${escapeHtml(recipe.id)}">${wished ? "已在想学清单 ✓" : "加入想学"}</button>
        </div>
      </article>`;
  }

  function render() {
    const tokens = tokenize(state.q);
    const done = loadDoneIds();
    const recipes = allRecipes();

    const list = recipes
      .filter((recipe) => matchesFilters(recipe, done))
      .map((recipe) => ({ recipe, score: tokens.length ? scoreRecipe(recipe, tokens) : 0 }))
      .filter((item) => !tokens.length || item.score > 0)
      .sort((a, b) => {
        if (tokens.length && b.score !== a.score) return b.score - a.score;
        return a.recipe.level - b.recipe.level;
      })
      .map((item) => item.recipe);

    results.innerHTML = list.map((recipe) => cardHTML(recipe, tokens)).join("");
    emptyState.classList.toggle("hidden", list.length > 0);
    results.classList.toggle("hidden", list.length === 0);

    if (tokens.length) {
      resultCount.textContent = `找到 ${list.length} 道菜`;
      activeQuery.textContent = `关键词：${state.q.trim()}`;
    } else {
      const customCount = recipes.filter((recipe) => recipe.source === "custom").length;
      resultCount.textContent = `共 ${list.length} 道菜谱`;
      activeQuery.textContent = customCount
        ? `九道基础课 + ${customCount} 道我的菜谱`
        : "九道基础课的完整菜谱";
    }

    if (list.length > 0) {
      const first = list[0];
      const firstSnippet = findSnippet(first, tokens);
      if (firstSnippet) {
        document.title = `${state.q.trim()} · 菜谱库 · 小白学菜`;
      }
    }
  }

  function renderUnlock() {
    const done = loadDoneIds();
    const count = done.size;
    const allDone = count >= RECIPES.length;

    unlockPanel.classList.toggle("is-open", allDone);
    unlockPanel.innerHTML = allDone
      ? `
        <div>
          <strong>九道基础菜已学完</strong>
          <span>菜谱库已全部解锁。你可以按食材、做法和口味自由搜索，也可以继续记录每次练习的笔记。</span>
        </div>
        <div class="unlock-progress">9/9</div>`
      : `
        <div>
          <strong>学完全部基础课，进入自由搜索</strong>
          <span>九道基础课完成后，这里会标记为已学完；现在也可以用关键词搜索全部菜谱。</span>
        </div>
        <div class="unlock-progress">${count}/9</div>`;
  }

  function renderTags() {
    const counts = new Map();
    for (const recipe of allRecipes()) {
      for (const tag of recipe.tags || []) {
        counts.set(tag, (counts.get(tag) || 0) + 1);
      }
    }

    const tags = [...counts.entries()]
      .sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0], "zh-CN"))
      .slice(0, 12)
      .map(([tag]) => tag);

    tagFilters.innerHTML = [
      `<button class="chip ${state.tag === "all" ? "selected" : ""}" type="button" data-value="all">全部</button>`,
      ...tags.map((tag) => {
        const selected = state.tag === tag ? "selected" : "";
        return `<button class="chip ${selected}" type="button" data-value="${escapeHtml(tag)}">${escapeHtml(tag)}</button>`;
      }),
    ].join("");
  }

  function syncChips() {
    document.querySelectorAll("[data-filter]").forEach((row) => {
      const key = row.dataset.filter;
      const value = state[key] || "all";
      row.querySelectorAll(".chip").forEach((chip) => {
        chip.classList.toggle("selected", chip.dataset.value === value);
      });
    });
  }

  function loadHistory() {
    const list = parseJSON(storageGet(HISTORY_KEY), []);
    return Array.isArray(list) ? list.filter((item) => typeof item === "string").slice(0, 6) : [];
  }

  function pushHistory(query) {
    const value = String(query || "").trim();
    if (!value) return;
    const list = [value, ...loadHistory().filter((item) => item !== value)].slice(0, 6);
    storageSet(HISTORY_KEY, JSON.stringify(list));
    renderHistory();
  }

  function renderHistory() {
    const list = loadHistory();
    recentWrap.classList.toggle("hidden", list.length === 0);
    recentChips.innerHTML = list
      .map((item) => `<button type="button" data-recent="${escapeHtml(item)}">${escapeHtml(item)}</button>`)
      .join("");
  }

  function syncUrl() {
    const params = new URLSearchParams();
    if (state.q.trim()) params.set("q", state.q.trim());
    if (state.level !== "all") params.set("level", state.level);
    if (state.tag !== "all") params.set("tag", state.tag);
    if (state.progress !== "all") params.set("progress", state.progress);
    if (state.source !== "all") params.set("source", state.source);
    const query = params.toString();
    const url = `${location.pathname}${query ? `?${query}` : ""}`;
    try {
      history.replaceState(null, "", url);
    } catch (error) {
      /* 直接双击打开本地 HTML 时，部分浏览器禁止改写 file:// 地址 */
    }
  }

  function readUrl() {
    const params = new URLSearchParams(location.search);
    state.q = params.get("q") || "";
    state.level = params.get("level") || "all";
    state.tag = params.get("tag") || "all";
    state.progress = params.get("progress") || "all";
    state.source = params.get("source") || "all";
    searchInput.value = state.q;
  }

  let debounceTimer = 0;
  function scheduleRender() {
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => {
      render();
      syncUrl();
    }, 160);
  }

  searchInput.addEventListener("input", () => {
    state.q = searchInput.value;
    scheduleRender();
  });

  searchForm.addEventListener("submit", (event) => {
    event.preventDefault();
    state.q = searchInput.value;
    pushHistory(state.q);
    render();
    syncUrl();
  });

  clearBtn.addEventListener("click", () => {
    searchInput.value = "";
    state.q = "";
    render();
    syncUrl();
    searchInput.focus();
  });

  document.querySelectorAll(".filters").forEach((filters) => {
    filters.addEventListener("click", (event) => {
      const chip = event.target.closest(".chip");
      if (!chip) return;
      const row = chip.closest("[data-filter]");
      if (!row) return;
      state[row.dataset.filter] = chip.dataset.value;
      syncChips();
      render();
      syncUrl();
    });
  });

  recentChips.addEventListener("click", (event) => {
    const button = event.target.closest("[data-recent]");
    if (!button) return;
    searchInput.value = button.dataset.recent;
    state.q = searchInput.value;
    render();
    syncUrl();
  });

  results.addEventListener("click", (event) => {
    const button = event.target.closest("[data-wish]");
    if (!button || !WISHLIST) return;
    event.preventDefault();
    const recipe = allRecipes().find((item) => item.id === button.dataset.wish);
    if (!recipe) return;
    const added = WISHLIST.toggle({
      id: recipe.id,
      name: recipe.name,
      url: recipe.url,
      cover: recipe.cover,
      lesson: recipe.lesson,
    });
    button.classList.toggle("active", added);
    button.textContent = added ? "已在想学清单 ✓" : "加入想学";
  });

  const menuBtn = document.getElementById("menuBtn");
  const menuPop = document.getElementById("menuPop");
  if (menuBtn && menuPop) {
    menuBtn.addEventListener("click", (event) => {
      event.stopPropagation();
      const open = menuPop.classList.toggle("hidden") === false;
      menuBtn.setAttribute("aria-expanded", String(open));
    });

    document.addEventListener("click", (event) => {
      const wrap = document.querySelector(".menu-wrap");
      if (!menuPop.classList.contains("hidden") && wrap && !wrap.contains(event.target)) {
        menuPop.classList.add("hidden");
        menuBtn.setAttribute("aria-expanded", "false");
      }
    });
  }

  readUrl();
  renderTags();
  syncChips();
  renderHistory();
  render();
  renderUnlock();
})();
