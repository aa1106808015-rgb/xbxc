(function () {
  "use strict";

  const store = window.XiaoBaiMyRecipes;
  const root = document.getElementById("detailRoot");
  if (!store || !root) return;

  function escapeHtml(value) {
    return String(value == null ? "" : value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  const id = new URLSearchParams(location.search).get("id");
  const recipe = id ? store.find(id) : null;

  if (!recipe) {
    root.innerHTML = `
      <div class="wrap">
        <section class="section">
          <div class="section-head">
            <p class="kicker">我的菜谱</p>
            <h2>没有找到这道菜</h2>
            <p>它可能已经被删除，或者链接不完整。</p>
          </div>
          <a class="pill" href="my-recipes.html">返回我的菜谱</a>
        </section>
      </div>`;
    return;
  }

  const cover = recipe.cover || store.PLACEHOLDER;
  const tags = recipe.tags.length ? recipe.tags : ["我的菜谱"];
  const ingredientCount = recipe.ingredients.length;
  const stepCount = recipe.steps.length;
  const meta = [
    ["难度", recipe.difficulty || "自己掌握"],
    ["用时", recipe.time || "未填写"],
    ["份量", "按自己的份量"],
    ["花费", recipe.cost || "未填写"],
  ];

  const ingredients = recipe.ingredients.length
    ? recipe.ingredients.map((item) => `
        <div class="ing-item">
          <span class="name">${escapeHtml(item.name)}</span>
          <span class="amount">${escapeHtml(item.amount || "按需")}</span>
          <span class="why">${escapeHtml(item.why || "按自己的口味调整。")}</span>
        </div>`).join("")
    : `<p class="tool-note">这道菜还没有填写用料。</p>`;

  const steps = recipe.steps.length
    ? recipe.steps.map((step, index) => `
        <li class="step">
          <div class="step-left">
            <span class="step-no">STEP</span>
            <span class="step-time">${escapeHtml(step.time || `第 ${index + 1} 步`)}</span>
          </div>
          <div class="step-body">
            <h3>${escapeHtml(step.title || `第 ${index + 1} 步`)}</h3>
            <p>${escapeHtml(step.text || "这一步还没有写说明。")}</p>
          </div>
          <img class="step-photo" src="${escapeHtml(step.photo || cover)}" alt="${escapeHtml(step.title || recipe.name)}步骤图" loading="lazy">
        </li>`).join("")
    : `<li class="step"><div class="step-left"><span class="step-no">STEP</span></div><div class="step-body"><h3>还没有步骤</h3><p>回到“我的菜谱”补充做法步骤。</p></div></li>`;

  root.innerHTML = `
    <div class="wrap">
      <section class="recipe-hero">
        <div class="hero-grid">
          <div>
            <nav class="crumb" aria-label="面包屑">
              <a href="my-recipes.html">我的菜谱</a>
              <span>/</span>
              <span>${escapeHtml(recipe.name)}</span>
            </nav>
            <div class="badge-row">
              <span class="badge badge-dark">我的菜谱</span>
              ${tags.slice(0, 3).map((tag) => `<span class="badge">${escapeHtml(tag)}</span>`).join("")}
            </div>
            <h1>${escapeHtml(recipe.name)}</h1>
            <p class="recipe-tagline">${escapeHtml(recipe.lead || "我自己记录的菜谱。")}</p>
            <p class="recipe-lead">${escapeHtml(recipe.notes || "这是我自己保存的做法，可以边做边补充笔记。")}</p>
            <dl class="meta">
              ${meta.map(([label, value]) => `<div><dt>${label}</dt><dd>${escapeHtml(value)}</dd></div>`).join("")}
            </dl>
            <div class="hero-actions">
              <a class="pill" href="#ingredients">开始练习</a>
              <a class="text-link" href="my-recipes.html">← 回我的菜谱</a>
            </div>
          </div>
          <figure class="dish-cover">
            <img class="dish-photo" src="${escapeHtml(cover)}" alt="${escapeHtml(recipe.name)}成品图">
            <span class="index" aria-hidden="true">我的菜谱</span>
            <figcaption class="photo-credit">自制菜谱</figcaption>
          </figure>
        </div>
      </section>
    </div>

    <nav class="page-nav" aria-label="本页内容导航">
      <div class="wrap">
        <ul>
          <li><a href="#goal">本课目标</a></li>
          <li><a href="#ingredients">用料</a></li>
          <li><a href="#steps">步骤</a></li>
          <li><a href="#notes">我的笔记</a></li>
          <li><a href="#done">学会标准</a></li>
          <li><a href="#my-record">我的记录</a></li>
        </ul>
      </div>
    </nav>

    <div class="wrap">
      <section class="section" id="goal">
        <div class="section-head">
          <p class="kicker">01 · 本课目标</p>
          <h2>为什么做这道菜？</h2>
          <p>${escapeHtml(recipe.lead || "这是我自己想学会的一道菜。")}</p>
        </div>
        <div class="goal-grid">
          <div class="goal">
            <strong>用料 ${ingredientCount} 种</strong>
            <span>按自己的习惯准备，缺什么可以随时补进菜谱。</span>
          </div>
          <div class="goal">
            <strong>${stepCount} 步完成</strong>
            <span>步骤按自己的做法记录，做的时候照着走。</span>
          </div>
          <div class="goal">
            <strong>${escapeHtml(tags[0])}</strong>
            <span>${escapeHtml(tags.join("、"))}</span>
          </div>
        </div>
        <p class="learn-note"><b>我的目标：</b>${escapeHtml(recipe.notes || "先把这道菜独立做一遍，再慢慢调整成自己喜欢的味道。")}</p>
      </section>

      <section class="section" id="ingredients">
        <div class="section-head">
          <p class="kicker">02 · 用料</p>
          <h2>买这些就够了</h2>
          <p>用料来自我自己填写的内容，用量可以按人数和口味调整。</p>
        </div>
        <div class="ing-list">${ingredients}</div>
      </section>

      <section class="section" id="steps">
        <div class="section-head">
          <p class="kicker">03 · 跟着做</p>
          <h2>${stepCount} 步，按自己的做法完成</h2>
          <p>每一步后面都可以对照自己试做后的结果，再回来修改菜谱。</p>
        </div>
        <ol class="steps">${steps}</ol>
      </section>

      <section class="section" id="notes">
        <div class="section-head">
          <p class="kicker">04 · 我的笔记</p>
          <h2>记下自己的版本</h2>
          <p>这里保存的是我自己写的笔记，不是标准答案。</p>
        </div>
        <p class="learn-note">${escapeHtml(recipe.notes || "还没有写笔记。练习后可以回来补充翻车点和下次要改的地方。")}</p>
      </section>

      <section class="section" id="done">
        <div class="section-head">
          <p class="kicker">05 · 学会标准</p>
          <h2>怎么算这道菜做成了？</h2>
          <p>不用和外面一模一样，做到下面几条，就算把这道菜变成了自己的。</p>
        </div>
        <ul class="done-list">
          <li><i>1</i><div><b>用料齐全</b><span>需要的东西都准备好了，不再临时缺项。</span></div></li>
          <li><i>2</i><div><b>步骤能独立走完</b><span>看着自己的记录，不用再问别人。</span></div></li>
          <li><i>3</i><div><b>味道可以调整</b><span>知道哪里该加盐、加糖或调火，而不是碰运气。</span></div></li>
          <li><i>4</i><div><b>愿意再做一次</b><span>这道菜进入了自己的常做清单。</span></div></li>
        </ul>
      </section>

      <section class="section" id="my-record">
        <div class="section-head">
          <p class="kicker">06 · 我的记录</p>
          <h2>记录这次练习</h2>
          <p>进度、笔记和成品图只保存在这台设备的浏览器里，不会上传到任何地方。</p>
        </div>
        <div class="learn-panel">
          <div class="learn-head">
            <div>
              <p class="learn-kicker">PERSONAL NOTE</p>
              <h2>${escapeHtml(recipe.name)} · 学习记录</h2>
              <p>把这次做出来的成品图留下来，之后回看会很有用。</p>
            </div>
            <span class="learn-status" id="detailWishStatus"></span>
          </div>
          <div class="learn-actions">
            <button class="learn-wish-btn" id="detailWishBtn" type="button">加入想学</button>
          </div>
          <div class="learn-photo-row">
            <img class="learn-photo hidden" id="practicePhotoPreview" alt="${escapeHtml(recipe.name)}成品图">
            <div>
              <label class="learn-photo-btn" for="practicePhoto">上传我的成品图</label>
              <input class="hidden" id="practicePhoto" type="file" accept="image/*">
              <button class="learn-photo-clear hidden" id="practiceClear" type="button">清除图片</button>
              <p class="learn-photo-note">图片会压缩后保存在本机浏览器，显示在“我的厨房 · 最近练习”里。</p>
            </div>
          </div>
          <textarea class="learn-notes" id="practiceNotes" placeholder="这次做得怎么样？有没有要改的地方？"></textarea>
          <div class="learn-actions">
            <button class="learn-done-btn" id="practiceSave" type="button">保存这次练习</button>
            <span class="learn-meta" id="practiceStatus" role="status"></span>
          </div>
        </div>
      </section>
    </div>`;

  // 与九道菜详情页保持一致：我的记录紧跟在顶部菜谱图之后。
  const recordSection = document.getElementById("my-record");
  const heroWrap = root.querySelector(".wrap");
  if (recordSection && heroWrap) {
    heroWrap.appendChild(recordSection);
  }

  document.title = `${recipe.name} · 我的菜谱 · 小白学菜`;

  const wishBtn = document.getElementById("detailWishBtn");
  const wishStatus = document.getElementById("detailWishStatus");
  const wishlist = window.XiaoBaiWishlist;
  if (wishBtn && wishlist) {
    const renderWish = () => {
      const active = wishlist.has(recipe.id);
      wishBtn.classList.toggle("active", active);
      wishBtn.textContent = active ? "已在想学清单 ✓" : "加入想学";
      wishStatus.textContent = active ? "已在想学清单" : "还没有加入想学";
    };
    wishBtn.addEventListener("click", () => {
      wishlist.toggle({
        id: recipe.id,
        name: recipe.name,
        url: `my-recipe.html?id=${encodeURIComponent(recipe.id)}`,
        cover: recipe.cover,
        lesson: "我的菜谱",
      });
      renderWish();
    });
    renderWish();
  }

  const practicePhotoInput = document.getElementById("practicePhoto");
  const practicePhotoPreview = document.getElementById("practicePhotoPreview");
  const practiceClear = document.getElementById("practiceClear");
  const practiceNotes = document.getElementById("practiceNotes");
  const practiceSave = document.getElementById("practiceSave");
  const practiceStatus = document.getElementById("practiceStatus");
  const practiceLog = window.XiaoBaiPracticeLog;
  let practicePhoto = "";

  function renderPracticePhoto() {
    if (practicePhoto) {
      practicePhotoPreview.src = practicePhoto;
      practicePhotoPreview.classList.remove("hidden");
      practiceClear.classList.remove("hidden");
    } else {
      practicePhotoPreview.removeAttribute("src");
      practicePhotoPreview.classList.add("hidden");
      practiceClear.classList.add("hidden");
    }
  }

  practicePhotoInput.addEventListener("change", () => {
    const file = practicePhotoInput.files && practicePhotoInput.files[0];
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
        practicePhoto = canvas.toDataURL("image/jpeg", 0.75);
        renderPracticePhoto();
      });
      image.src = reader.result;
    });
    reader.readAsDataURL(file);
  });

  practiceClear.addEventListener("click", () => {
    practicePhoto = "";
    practicePhotoInput.value = "";
    renderPracticePhoto();
  });

  practiceSave.addEventListener("click", () => {
    if (!practiceLog) return;
    const saved = practiceLog.upsert({
      recipeId: recipe.id,
      name: recipe.name,
      url: `my-recipe.html?id=${encodeURIComponent(recipe.id)}`,
      date: new Date().toISOString().slice(0, 10),
      notes: practiceNotes.value.trim(),
      photo: practicePhoto,
      cover: recipe.cover,
    });
    practiceStatus.textContent = saved
      ? "已保存，可以去我的厨房查看最近练习。"
      : "保存失败：浏览器存储空间可能已满。";
  });

  renderPracticePhoto();

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
})();
