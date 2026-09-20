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
    </section>`;

  document.title = `${recipe.name} · 我的菜谱 · 小白学菜`;

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
