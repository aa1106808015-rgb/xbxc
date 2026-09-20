(function () {
  "use strict";

  const RECIPES = Array.isArray(window.XIAOBAI_RECIPES) ? window.XIAOBAI_RECIPES : [];
  if (!RECIPES.length) return;

  const slug = (location.pathname.split("/").pop() || "").replace(/\.html$/, "");
  const recipe = RECIPES.find((item) => item.slug === slug || item.url.endsWith(`${slug}.html`));
  if (!recipe || !document.querySelector(".step")) return;

  const RECORD_KEY = "xiaobai-recipe-records-v1";
  const levelKey = `xiaobai-level${recipe.level}-done-v1`;

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
      /* 浏览器禁用存储时，当前页仍然可以查看 */
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

  function loadLevelDone() {
    const ids = parseJSON(storageGet(levelKey), []);
    return new Set(Array.isArray(ids) ? ids : []);
  }

  function saveLevelDone(set) {
    storageSet(levelKey, JSON.stringify([...set]));
  }

  const records = loadRecords();
  const existing = records[recipe.id] || {};
  const levelDone = loadLevelDone();

  const record = {
    done: Boolean(existing.done || levelDone.has(recipe.id)),
    rating: Number(existing.rating) || 0,
    notes: typeof existing.notes === "string" ? existing.notes : "",
    times: Number(existing.times) || 0,
    lastDone: existing.lastDone || "",
  };

  records[recipe.id] = record;
  storageSet(RECORD_KEY, JSON.stringify(records));

  function syncLevel() {
    const set = loadLevelDone();
    if (record.done) {
      set.add(recipe.id);
    } else {
      set.delete(recipe.id);
    }
    saveLevelDone(set);
  }

  function save() {
    records[recipe.id] = record;
    storageSet(RECORD_KEY, JSON.stringify(records));
  }

  function ensureStyles() {
    if (document.querySelector('link[data-learn-style]')) return;
    const link = document.createElement("link");
    link.rel = "stylesheet";
    link.href = "../assets/learn.css";
    link.dataset.learnStyle = "true";
    document.head.appendChild(link);
  }

  function notify(message) {
    if (typeof window.showToast === "function") {
      window.showToast(message);
      return;
    }
    const toast = document.getElementById("toast");
    if (!toast) return;
    toast.textContent = message;
    toast.classList.add("show");
    clearTimeout(notify.timer);
    notify.timer = setTimeout(() => toast.classList.remove("show"), 2200);
  }

  ensureStyles();

  const section = document.createElement("section");
  section.className = "section learn-section";
  section.id = "my-record";
  section.innerHTML = `
    <div class="section-head">
      <p class="kicker">06 · 我的记录</p>
      <h2>这道菜，你练得怎么样？</h2>
      <p>进度、评分和笔记只保存在这台设备的浏览器里，不会上传到任何地方。</p>
    </div>
    <div class="learn-panel">
      <div class="learn-head">
        <div>
          <p class="learn-kicker">PERSONAL NOTE</p>
          <h2>${recipe.name} · 学习记录</h2>
          <p>练过就标记一下；写下来的问题，下次做之前再看一眼。</p>
        </div>
        <span class="learn-status" id="learnStatus"></span>
      </div>
      <div class="learn-actions">
        <button class="learn-done-btn" id="learnDoneBtn" type="button">标记已练会</button>
        <div class="learn-rating" role="group" aria-label="给这道菜打分">
          <span>我的评分</span>
          ${[1, 2, 3, 4, 5].map((n) => `<button class="learn-star" type="button" data-rating="${n}" aria-label="${n} 星">★</button>`).join("")}
        </div>
      </div>
      <textarea class="learn-notes" id="learnNotes" placeholder="写点自己的笔记：哪里翻车了、下次怎么改、家人觉得怎么样……"></textarea>
      <p class="learn-meta" id="learnMeta"></p>
      <a class="learn-link" href="../library.html">去菜谱库搜索更多菜谱 →</a>
    </div>`;

  const wrap = document.querySelector("main .wrap");
  if (!wrap) return;
  wrap.appendChild(section);

  const navList = document.querySelector(".page-nav ul");
  if (navList) {
    const navItem = document.createElement("li");
    navItem.innerHTML = '<a href="#my-record">我的记录</a>';
    navList.appendChild(navItem);
  }

  const doneBtn = section.querySelector("#learnDoneBtn");
  const status = section.querySelector("#learnStatus");
  const notes = section.querySelector("#learnNotes");
  const meta = section.querySelector("#learnMeta");
  const stars = [...section.querySelectorAll(".learn-star")];

  let notesTimer = 0;

  function render() {
    doneBtn.classList.toggle("done", record.done);
    doneBtn.textContent = record.done ? "已练会 ✓" : "标记已练会";
    doneBtn.setAttribute("aria-pressed", String(record.done));

    status.classList.toggle("done", record.done);
    status.textContent = record.done ? "已点亮" : "还没标记";

    stars.forEach((star) => {
      const value = Number(star.dataset.rating);
      star.classList.toggle("on", value <= record.rating);
      star.setAttribute("aria-pressed", String(value === record.rating));
    });

    const bits = [];
    if (record.times) bits.push(`累计练过 ${record.times} 次`);
    if (record.lastDone) bits.push(`最近一次：${record.lastDone}`);
    if (record.rating) bits.push(`评分：${record.rating}/5`);
    meta.textContent = bits.join(" · ") || "还没有记录，完成第一次练习后标记一下。";
  }

  doneBtn.addEventListener("click", () => {
    if (record.done) {
      record.done = false;
      notify("已取消标记，可以再练一次");
    } else {
      record.done = true;
      record.times += 1;
      record.lastDone = new Date().toISOString().slice(0, 10);
      notify(record.times === 1 ? "第一次练会，已点亮" : "又练了一次，已更新记录");
    }
    save();
    syncLevel();
    render();
  });

  stars.forEach((star) => {
    star.addEventListener("click", () => {
      const value = Number(star.dataset.rating);
      record.rating = record.rating === value ? 0 : value;
      save();
      render();
    });
  });

  notes.addEventListener("input", () => {
    clearTimeout(notesTimer);
    notesTimer = setTimeout(() => {
      record.notes = notes.value;
      save();
    }, 220);
  });

  notes.addEventListener("blur", () => {
    record.notes = notes.value;
    save();
  });

  notes.value = record.notes;
  render();
  syncLevel();
})();
