(function () {
  "use strict";

  const store = window.XiaoBaiMyRecipes;
  if (!store) return;

  const form = document.getElementById("editForm");
  const editId = document.getElementById("editId");
  const nameInput = document.getElementById("name");
  const aliasesInput = document.getElementById("aliases");
  const tagsInput = document.getElementById("tags");
  const timeInput = document.getElementById("time");
  const difficultyInput = document.getElementById("difficulty");
  const costInput = document.getElementById("cost");
  const sourceUrlInput = document.getElementById("sourceUrl");
  const coverUrlInput = document.getElementById("coverUrl");
  const coverFileInput = document.getElementById("coverFile");
  const coverPreview = document.getElementById("coverPreview");
  const clearCoverBtn = document.getElementById("clearCover");
  const leadInput = document.getElementById("lead");
  const ingredientsInput = document.getElementById("ingredients");
  const stepCountInput = document.getElementById("stepCount");
  const stepRows = document.getElementById("stepRows");
  const stepMinus = document.getElementById("stepMinus");
  const stepPlus = document.getElementById("stepPlus");
  const notesInput = document.getElementById("notes");
  const saveBtn = document.getElementById("saveBtn");
  const resetBtn = document.getElementById("resetBtn");
  const deleteBtn = document.getElementById("deleteBtn");
  const formStatus = document.getElementById("formStatus");
  const list = document.getElementById("myList");
  const empty = document.getElementById("myEmpty");
  const count = document.getElementById("myCount");
  const searchInput = document.getElementById("mySearch");
  const exportBtn = document.getElementById("exportBtn");
  const importInput = document.getElementById("importInput");

  let coverValue = "";

  function escapeHtml(value) {
    return String(value == null ? "" : value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  function normalizeText(value) {
    return String(value || "").toLowerCase().replace(/\s+/g, "");
  }

  function splitTags(value) {
    return String(value || "")
      .split(/[,，、]/)
      .map((item) => item.trim())
      .filter(Boolean);
  }

  function parseLines(value, fields) {
    return String(value || "")
      .split(/\r?\n/)
      .map((line) => line.trim())
      .filter(Boolean)
      .map((line) => {
        const parts = line.split(/[|｜]/).map((part) => part.trim());
        const item = {};
        fields.forEach((field, index) => {
          item[field] = parts[index] || "";
        });
        return item;
      });
  }

  function linesFromIngredients(items) {
    return (items || [])
      .map((item) => [item.name, item.amount, item.why].filter(Boolean).join(" | "))
      .join("\n");
  }

  function setStatus(message) {
    formStatus.textContent = message;
    clearTimeout(setStatus.timer);
    setStatus.timer = setTimeout(() => {
      formStatus.textContent = "";
    }, 2600);
  }

  function setCover(value, syncInput = true) {
    coverValue = String(value || "").trim();
    if (syncInput) {
      coverUrlInput.value = coverValue.startsWith("data:") ? "" : coverValue;
    }
    coverPreview.src = coverValue || store.PLACEHOLDER;
  }

  function clampStepCount(value) {
    return Math.min(20, Math.max(1, Number(value) || 1));
  }

  function stepRowHTML(step, index) {
    const value = step || {};
    const photo = String(value.photo || "").trim();
    const isData = photo.startsWith("data:");
    return `
      <div class="step-edit-row" data-step-row>
        <span class="step-edit-num">${String(index + 1).padStart(2, "0")}</span>
        <div class="step-edit-fields">
          <input class="step-title" type="text" value="${escapeHtml(value.title || "")}" placeholder="步骤标题，例如：牛腩焯水">
          <textarea class="step-text" rows="2" placeholder="这一步怎么做">${escapeHtml(value.text || "")}</textarea>
          <div class="step-photo-tools">
            <img class="step-photo-preview" src="${escapeHtml(photo || store.PLACEHOLDER)}" alt="步骤图预览">
            <label class="ghost-btn">上传步骤图<input class="hidden step-photo-file" type="file" accept="image/*"></label>
            <input class="step-photo-url" type="text" value="${isData ? "" : escapeHtml(photo)}" placeholder="或粘贴图片地址">
            <button class="ghost-btn step-photo-clear" type="button">清除</button>
            <input class="step-photo-data" type="hidden" value="${isData ? escapeHtml(photo) : ""}">
          </div>
        </div>
      </div>`;
  }

  function readStepRows() {
    return [...stepRows.querySelectorAll(".step-edit-row")].map((row) => ({
      title: row.querySelector(".step-title").value.trim(),
      text: row.querySelector(".step-text").value.trim(),
      photo: (row.querySelector(".step-photo-data").value || row.querySelector(".step-photo-url").value).trim(),
    }));
  }

  function renderStepRows(count, values = []) {
    const total = clampStepCount(count);
    stepCountInput.value = total;
    stepRows.innerHTML = Array.from({ length: total }, (_, index) => stepRowHTML(values[index], index)).join("");
  }

  function compressImage(file, callback) {
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
        callback(canvas.toDataURL("image/jpeg", 0.75));
      });
      image.src = reader.result;
    });
    reader.readAsDataURL(file);
  }

  function resetForm() {
    form.reset();
    editId.value = "";
    setCover("");
    renderStepRows(3);
    deleteBtn.classList.add("hidden");
    saveBtn.textContent = "保存菜谱";
  }

  function fillForm(recipe) {
    editId.value = recipe.id;
    nameInput.value = recipe.name;
    aliasesInput.value = recipe.aliases.join("，");
    tagsInput.value = recipe.tags.join("，");
    timeInput.value = recipe.time;
    difficultyInput.value = recipe.difficulty;
    costInput.value = recipe.cost;
    sourceUrlInput.value = recipe.sourceUrl;
    leadInput.value = recipe.lead;
    ingredientsInput.value = linesFromIngredients(recipe.ingredients);
    renderStepRows(Math.max(1, recipe.steps.length), recipe.steps);
    notesInput.value = recipe.notes;
    setCover(recipe.cover);
    deleteBtn.classList.remove("hidden");
    saveBtn.textContent = "保存修改";
    form.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  function readForm() {
    return {
      id: editId.value || undefined,
      name: nameInput.value.trim(),
      aliases: splitTags(aliasesInput.value),
      tags: splitTags(tagsInput.value),
      time: timeInput.value.trim(),
      difficulty: difficultyInput.value.trim(),
      cost: costInput.value.trim(),
      cover: coverValue.trim(),
      sourceUrl: sourceUrlInput.value.trim(),
      lead: leadInput.value.trim(),
      ingredients: parseLines(ingredientsInput.value, ["name", "amount", "why"]),
      steps: readStepRows().filter((step) => step.title || step.text || step.photo),
      notes: notesInput.value.trim(),
    };
  }

  function matchesSearch(recipe, query) {
    if (!query) return true;
    const text = normalizeText(
      [
        recipe.name,
        recipe.aliases.join(" "),
        recipe.tags.join(" "),
        recipe.ingredients.map((item) => item.name).join(" "),
        recipe.steps.map((item) => item.title).join(" "),
      ].join(" ")
    );
    return normalizeText(query).split(/\s+/).every((token) => text.includes(token));
  }

  function renderList() {
    const all = store.load();
    const query = searchInput.value.trim();
    const filtered = all.filter((recipe) => matchesSearch(recipe, query));

    count.textContent = `${all.length} 道`;
    list.innerHTML = filtered
      .map(
        (recipe) => `
          <article class="my-item">
            <img src="${escapeHtml(recipe.cover || store.PLACEHOLDER)}" alt="${escapeHtml(recipe.name)}封面" loading="lazy">
            <div>
              <h3>${escapeHtml(recipe.name)}</h3>
              <p>${escapeHtml([recipe.time, recipe.difficulty, recipe.cost].filter(Boolean).join(" · ") || "还没有填写时间和难度")}</p>
              <p>${escapeHtml(recipe.tags.join("、") || "没有标签")}</p>
              <div class="my-item-actions">
                <a href="my-recipe.html?id=${encodeURIComponent(recipe.id)}">查看</a>
                <button type="button" data-edit="${escapeHtml(recipe.id)}">编辑</button>
                <button type="button" data-delete="${escapeHtml(recipe.id)}">删除</button>
              </div>
            </div>
          </article>`
      )
      .join("");

    empty.classList.toggle("hidden", filtered.length > 0);
    list.classList.toggle("hidden", filtered.length === 0);
  }

  form.addEventListener("submit", (event) => {
    event.preventDefault();
    const recipe = readForm();
    if (!recipe.name) {
      setStatus("先填写菜名。");
      nameInput.focus();
      return;
    }
    const saved = store.upsert(recipe);
    if (!saved) {
      setStatus("保存失败：浏览器存储空间可能已满。可以少放一张本地图片，或先导出备份。");
      return;
    }
    resetForm();
    renderList();
    setStatus("已保存，菜谱库现在可以搜到这道菜。");
  });

  resetBtn.addEventListener("click", () => {
    resetForm();
    setStatus("表单已清空。");
  });

  deleteBtn.addEventListener("click", () => {
    const id = editId.value;
    if (!id) return;
    if (!window.confirm("确定删除这道菜谱吗？删除后不能恢复。")) return;
    store.remove(id);
    resetForm();
    renderList();
    setStatus("已删除。");
  });

  list.addEventListener("click", (event) => {
    const editButton = event.target.closest("[data-edit]");
    const deleteButton = event.target.closest("[data-delete]");
    if (editButton) {
      const recipe = store.find(editButton.dataset.edit);
      if (recipe) fillForm(recipe);
      return;
    }
    if (deleteButton) {
      const recipe = store.find(deleteButton.dataset.delete);
      if (!recipe) return;
      if (!window.confirm(`确定删除「${recipe.name}」吗？`)) return;
      store.remove(recipe.id);
      if (editId.value === recipe.id) resetForm();
      renderList();
      setStatus("已删除。");
    }
  });

  searchInput.addEventListener("input", renderList);

  coverUrlInput.addEventListener("input", () => {
    setCover(coverUrlInput.value, false);
  });

  clearCoverBtn.addEventListener("click", () => {
    coverFileInput.value = "";
    setCover("");
  });

  coverFileInput.addEventListener("change", () => {
    const file = coverFileInput.files && coverFileInput.files[0];
    if (!file) return;
    compressImage(file, (data) => {
      setCover(data);
      setStatus("封面已压缩并放入表单，保存后生效。");
    });
  });

  stepCountInput.addEventListener("change", () => {
    renderStepRows(stepCountInput.value, readStepRows());
  });

  stepMinus.addEventListener("click", () => {
    const values = readStepRows();
    renderStepRows(clampStepCount(Number(stepCountInput.value) - 1), values);
  });

  stepPlus.addEventListener("click", () => {
    const values = readStepRows();
    renderStepRows(clampStepCount(Number(stepCountInput.value) + 1), values);
  });

  stepRows.addEventListener("change", (event) => {
    const input = event.target.closest(".step-photo-file");
    if (!input) return;
    const file = input.files && input.files[0];
    const row = input.closest(".step-edit-row");
    if (!file || !row) return;
    compressImage(file, (data) => {
      row.querySelector(".step-photo-data").value = data;
      row.querySelector(".step-photo-url").value = "";
      row.querySelector(".step-photo-preview").src = data;
    });
  });

  stepRows.addEventListener("input", (event) => {
    const url = event.target.closest(".step-photo-url");
    if (!url) return;
    const row = url.closest(".step-edit-row");
    row.querySelector(".step-photo-data").value = "";
    row.querySelector(".step-photo-preview").src = url.value.trim() || store.PLACEHOLDER;
  });

  stepRows.addEventListener("click", (event) => {
    const clear = event.target.closest(".step-photo-clear");
    if (!clear) return;
    const row = clear.closest(".step-edit-row");
    row.querySelector(".step-photo-data").value = "";
    row.querySelector(".step-photo-url").value = "";
    row.querySelector(".step-photo-file").value = "";
    row.querySelector(".step-photo-preview").src = store.PLACEHOLDER;
  });

  exportBtn.addEventListener("click", () => {
    const blob = new Blob([store.exportJSON()], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `我的菜谱备份-${new Date().toISOString().slice(0, 10)}.json`;
    link.click();
    URL.revokeObjectURL(url);
    setStatus("备份已导出。");
  });

  importInput.addEventListener("change", () => {
    const file = importInput.files && importInput.files[0];
    if (!file) return;
    const reader = new FileReader();
    reader.addEventListener("load", () => {
      try {
        const imported = store.importJSON(String(reader.result || ""));
        renderList();
        setStatus(`已导入 ${imported} 道菜谱。`);
      } catch (error) {
        setStatus("导入失败：这个文件不是有效的菜谱备份。");
      }
      importInput.value = "";
    });
    reader.readAsText(file);
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

  const params = new URLSearchParams(location.search);
  const editTarget = params.get("edit");
  if (editTarget) {
    const recipe = store.find(editTarget);
    if (recipe) fillForm(recipe);
  }

  renderStepRows(3);
  renderList();
})();
