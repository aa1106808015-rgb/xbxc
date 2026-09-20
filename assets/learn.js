(function () {
  "use strict";

  const RECIPES = Array.isArray(window.XIAOBAI_RECIPES) ? window.XIAOBAI_RECIPES : [];
  if (!RECIPES.length) return;
  const WISHLIST = window.XiaoBaiWishlist || null;
  const PRACTICE_LOG = window.XiaoBaiPracticeLog || null;

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
    photo: typeof existing.photo === "string" ? existing.photo : "",
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

  function today() {
    return new Date().toISOString().slice(0, 10);
  }

  function syncPracticeLog() {
    if (!PRACTICE_LOG) return;
    if (!record.done && !record.photo && !record.rating && !record.notes) return;
    PRACTICE_LOG.upsert({
      recipeId: recipe.id,
      name: recipe.name,
      url: recipe.url,
      date: today(),
      rating: record.rating,
      notes: record.notes,
      photo: record.photo,
      cover: recipe.cover,
    });
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
        <button class="learn-wish-btn" id="learnWishBtn" type="button">加入想学</button>
        <div class="learn-rating" role="group" aria-label="给这道菜打分">
          <span>我的评分</span>
          ${[1, 2, 3, 4, 5].map((n) => `<button class="learn-star" type="button" data-rating="${n}" aria-label="${n} 星">★</button>`).join("")}
        </div>
      </div>
      <div class="learn-photo-row">
        <img class="learn-photo" id="learnPhotoPreview" alt="${recipe.name}的成品图">
        <div>
          <label class="learn-photo-btn" for="learnPhotoInput">上传我的成品图</label>
          <input class="hidden" id="learnPhotoInput" type="file" accept="image/*">
          <button class="learn-photo-clear" id="learnPhotoClear" type="button">清除图片</button>
          <p class="learn-photo-note">图片会压缩后保存在本机浏览器，显示在“我的厨房 · 最近练习”里。</p>
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
  const wishBtn = section.querySelector("#learnWishBtn");
  const status = section.querySelector("#learnStatus");
  const notes = section.querySelector("#learnNotes");
  const meta = section.querySelector("#learnMeta");
  const photoPreview = section.querySelector("#learnPhotoPreview");
  const photoInput = section.querySelector("#learnPhotoInput");
  const photoClear = section.querySelector("#learnPhotoClear");
  const stars = [...section.querySelectorAll(".learn-star")];

  let notesTimer = 0;

  function render() {
    doneBtn.classList.toggle("done", record.done);
    doneBtn.textContent = record.done ? "已练会 ✓" : "标记已练会";
    doneBtn.setAttribute("aria-pressed", String(record.done));

    status.classList.toggle("done", record.done);
    status.textContent = record.done ? "已点亮" : "还没标记";

    const wished = WISHLIST ? WISHLIST.has(recipe.id) : false;
    wishBtn.classList.toggle("active", wished);
    wishBtn.textContent = wished ? "已在想学清单 ✓" : "加入想学";

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

    if (record.photo) {
      photoPreview.src = record.photo;
      photoPreview.classList.remove("hidden");
      photoClear.classList.remove("hidden");
    } else {
      photoPreview.removeAttribute("src");
      photoPreview.classList.add("hidden");
      photoClear.classList.add("hidden");
    }
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
    syncPracticeLog();
    render();
  });

  wishBtn.addEventListener("click", () => {
    if (!WISHLIST) return;
    const added = WISHLIST.toggle({
      id: recipe.id,
      name: recipe.name,
      url: recipe.url,
      cover: recipe.cover,
      lesson: recipe.lesson,
    });
    render();
    notify(added ? "已加入想学清单，可以去我的厨房看看" : "已从想学清单移除");
  });

  stars.forEach((star) => {
    star.addEventListener("click", () => {
      const value = Number(star.dataset.rating);
      record.rating = record.rating === value ? 0 : value;
      save();
      syncPracticeLog();
      render();
    });
  });

  notes.addEventListener("input", () => {
    clearTimeout(notesTimer);
    notesTimer = setTimeout(() => {
      record.notes = notes.value;
      save();
      syncPracticeLog();
    }, 220);
  });

  notes.addEventListener("blur", () => {
    record.notes = notes.value;
    save();
    syncPracticeLog();
  });

  photoInput.addEventListener("change", () => {
    const file = photoInput.files && photoInput.files[0];
    if (!file) return;
    const reader = new FileReader();
    reader.addEventListener("load", () => {
      const image = new Image();
      image.addEventListener("load", () => {
        const max = 1000;
        const scale = Math.min(1, max / Math.max(image.width, image.height));
        const canvas = document.createElement("canvas");
        canvas.width = Math.max(1, Math.round(image.width * scale));
        canvas.height = Math.max(1, Math.round(image.height * scale));
        canvas.getContext("2d").drawImage(image, 0, 0, canvas.width, canvas.height);
        record.photo = canvas.toDataURL("image/jpeg", 0.75);
        save();
        syncPracticeLog();
        render();
        notify("成品图已保存在本机");
      });
      image.src = reader.result;
    });
    reader.readAsDataURL(file);
  });

  photoClear.addEventListener("click", () => {
    record.photo = "";
    save();
    syncPracticeLog();
    render();
    notify("已清除成品图");
  });

  notes.value = record.notes;
  render();
  syncLevel();
})();
