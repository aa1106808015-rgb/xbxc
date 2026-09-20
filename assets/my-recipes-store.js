(function () {
  "use strict";

  const KEY = "xiaobai-my-recipes-v1";
  const PLACEHOLDER = "assets/my-recipe-placeholder.svg";

  function uid() {
    if (window.crypto && typeof window.crypto.randomUUID === "function") {
      return `my-${window.crypto.randomUUID()}`;
    }
    return `my-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`;
  }

  function asArray(value) {
    return Array.isArray(value) ? value : [];
  }

  function normalizeIngredient(item) {
    if (typeof item === "string") {
      const [name, amount = "", why = ""] = item.split("|").map((part) => part.trim());
      return { name: name || "", amount, why };
    }
    return {
      name: String(item && item.name ? item.name : "").trim(),
      amount: String(item && item.amount ? item.amount : "").trim(),
      why: String(item && item.why ? item.why : "").trim(),
    };
  }

  function normalizeStep(item, index) {
    if (typeof item === "string") {
      const [title, text = ""] = item.split("|").map((part) => part.trim());
      return { title: title || `第 ${index + 1} 步`, text, time: "" };
    }
    return {
      title: String(item && item.title ? item.title : `第 ${index + 1} 步`).trim(),
      text: String(item && item.text ? item.text : "").trim(),
      time: String(item && item.time ? item.time : "").trim(),
    };
  }

  function normalize(recipe) {
    const source = recipe && typeof recipe === "object" ? recipe : {};
    const now = new Date().toISOString();
    return {
      id: source.id || uid(),
      name: String(source.name || "未命名菜谱").trim(),
      aliases: asArray(source.aliases).map((item) => String(item).trim()).filter(Boolean),
      tags: asArray(source.tags).map((item) => String(item).trim()).filter(Boolean),
      time: String(source.time || "").trim(),
      difficulty: String(source.difficulty || "").trim(),
      cost: String(source.cost || "").trim(),
      cover: String(source.cover || "").trim(),
      sourceUrl: String(source.sourceUrl || "").trim(),
      lead: String(source.lead || "").trim(),
      notes: String(source.notes || "").trim(),
      ingredients: asArray(source.ingredients).map(normalizeIngredient).filter((item) => item.name),
      steps: asArray(source.steps).map(normalizeStep).filter((item) => item.title || item.text),
      createdAt: source.createdAt || now,
      updatedAt: now,
    };
  }

  function load() {
    try {
      const raw = window.localStorage.getItem(KEY);
      const list = raw ? JSON.parse(raw) : [];
      return Array.isArray(list) ? list.map(normalize) : [];
    } catch (error) {
      return [];
    }
  }

  function save(list) {
    try {
      window.localStorage.setItem(KEY, JSON.stringify(asArray(list).map(normalize)));
      return true;
    } catch (error) {
      return false;
    }
  }

  function upsert(recipe) {
    const list = load();
    const next = normalize(recipe);
    const index = list.findIndex((item) => item.id === next.id);
    if (index >= 0) {
      next.createdAt = list[index].createdAt || next.createdAt;
      list[index] = next;
    } else {
      list.unshift(next);
    }
    return save(list) ? next : null;
  }

  function remove(id) {
    const list = load().filter((item) => item.id !== id);
    save(list);
    return list;
  }

  function find(id) {
    return load().find((item) => item.id === id) || null;
  }

  function exportJSON() {
    return JSON.stringify(
      {
        version: 1,
        exportedAt: new Date().toISOString(),
        recipes: load(),
      },
      null,
      2
    );
  }

  function importJSON(text) {
    const data = JSON.parse(text);
    const incoming = Array.isArray(data) ? data : data && Array.isArray(data.recipes) ? data.recipes : [];
    const list = load();
    const map = new Map(list.map((item) => [item.id, item]));
    for (const recipe of incoming) {
      const next = normalize(recipe);
      if (map.has(next.id)) {
        next.createdAt = map.get(next.id).createdAt || next.createdAt;
      }
      map.set(next.id, next);
    }
    save([...map.values()]);
    return incoming.length;
  }

  function loadForSearch() {
    return load().map((recipe) => ({
      id: recipe.id,
      slug: recipe.id,
      name: recipe.name,
      aliases: recipe.aliases,
      tags: recipe.tags,
      level: 99,
      lesson: "我的菜谱",
      badges: ["我的菜谱", ...recipe.tags.slice(0, 2)],
      difficulty: recipe.difficulty || "自定义",
      time: recipe.time || "未填写",
      servings: "",
      cost: recipe.cost || "未填写",
      lead: recipe.lead || recipe.notes || "自己添加并保存的菜谱。",
      ingredients: recipe.ingredients,
      steps: recipe.steps,
      cover: recipe.cover || PLACEHOLDER,
      url: `my-recipe.html?id=${encodeURIComponent(recipe.id)}`,
      source: "custom",
      sourceUrl: recipe.sourceUrl,
    }));
  }

  window.XiaoBaiMyRecipes = {
    KEY,
    PLACEHOLDER,
    load,
    save,
    upsert,
    remove,
    find,
    normalize,
    exportJSON,
    importJSON,
    loadForSearch,
  };
})();
