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
      <section class="panel">
        <div class="panel-head">
          <div>
            <h2>没有找到这道菜</h2>
            <p>它可能已经被删除，或者链接不完整。</p>
          </div>
        </div>
        <a class="pill" href="my-recipes.html">返回我的菜谱</a>
      </section>`;
    return;
  }

  const cover = recipe.cover || store.PLACEHOLDER;
  const tags = recipe.tags.length ? recipe.tags : ["我的菜谱"];
  const meta = [
    recipe.time && `用时：${recipe.time}`,
    recipe.difficulty && `难度：${recipe.difficulty}`,
    recipe.cost && `花费：${recipe.cost}`,
  ].filter(Boolean);

  const ingredients = recipe.ingredients.length
    ? recipe.ingredients
        .map(
          (item) => `
            <div class="ingredient">
              <strong>${escapeHtml(item.name)}${item.amount ? ` · ${escapeHtml(item.amount)}` : ""}</strong>
              <span>${escapeHtml(item.why || "按自己的口味调整用量。")}</span>
            </div>`
        )
        .join("")
    : `<div class="empty">还没有填写用料。</div>`;

  const steps = recipe.steps.length
    ? recipe.steps
        .map(
          (step, index) => `
            <li>
              <span class="step-num">${String(index + 1).padStart(2, "0")}</span>
              <div>
                <h3>${escapeHtml(step.title)}</h3>
                <p>${escapeHtml(step.text || "这一步还没有写说明。")}</p>
              </div>
            </li>`
        )
        .join("")
    : `<div class="empty">还没有填写做法步骤。</div>`;

  root.innerHTML = `
    <nav class="crumb" aria-label="面包屑">
      <a href="my-recipes.html">我的菜谱</a>
      <span>/</span>
      <span>${escapeHtml(recipe.name)}</span>
    </nav>

    <section class="detail-top">
      <div>
        <p class="eyebrow">我的菜谱</p>
        <h1>${escapeHtml(recipe.name)}</h1>
        <p class="detail-lead">${escapeHtml(recipe.lead || recipe.notes || "这是你自己添加并保存的菜谱。")}</p>
        <div class="badge-row">${tags.map((tag) => `<span class="badge">${escapeHtml(tag)}</span>`).join("")}</div>
        ${meta.length ? `<p class="meta">${meta.map(escapeHtml).join("<span>·</span>")}</p>` : ""}
        <div class="hero-actions">
          <a class="pill" href="my-recipes.html?edit=${encodeURIComponent(recipe.id)}">编辑这道菜</a>
          <button class="ghost-btn" id="detailWishBtn" type="button">加入想学</button>
          <a class="ghost-btn" href="library.html">去菜谱库搜索</a>
          ${recipe.sourceUrl ? `<a class="ghost-btn" href="${escapeHtml(recipe.sourceUrl)}" target="_blank" rel="noopener">打开来源链接</a>` : ""}
        </div>
      </div>
      <img class="detail-cover" src="${escapeHtml(cover)}" alt="${escapeHtml(recipe.name)}封面">
    </section>

    <section class="detail-section">
      <h2>用料</h2>
      <div class="ingredients">${ingredients}</div>
    </section>

    <section class="detail-section">
      <h2>做法步骤</h2>
      <ol class="steps-list">${steps}</ol>
    </section>

    <section class="detail-section">
      <h2>我的笔记</h2>
      <div class="notes-box">${escapeHtml(recipe.notes || "还没有写笔记。练习后可以回来补充翻车点和下次要改的地方。")}</div>
    </section>

    <section class="detail-section" id="practice">
      <h2>记录这次练习</h2>
      <div class="practice-row">
        <img class="practice-photo" id="practicePhotoPreview" alt="${escapeHtml(recipe.name)}成品图">
        <div class="practice-tools">
          <label class="ghost-btn" for="practicePhoto">上传成品图</label>
          <input class="hidden" id="practicePhoto" type="file" accept="image/*">
          <button class="ghost-btn" id="practiceClear" type="button">清除图片</button>
        </div>
      </div>
      <textarea class="detail-textarea" id="practiceNotes" rows="3" placeholder="这次做得怎么样？有没有要改的地方？"></textarea>
      <div class="hero-actions">
        <button class="pill" id="practiceSave" type="button">保存这次练习</button>
        <span class="detail-status" id="practiceStatus" role="status"></span>
      </div>
    </section>`;

  document.title = `${recipe.name} · 我的菜谱 · 小白学菜`;

  const wishBtn = document.getElementById("detailWishBtn");
  const wishlist = window.XiaoBaiWishlist;
  if (wishBtn && wishlist) {
    const renderWish = () => {
      const active = wishlist.has(recipe.id);
      wishBtn.classList.toggle("active", active);
      wishBtn.textContent = active ? "已在想学清单 ✓" : "加入想学";
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
