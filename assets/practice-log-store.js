(function () {
  "use strict";

  const KEY = "xiaobai-practice-log-v1";

  function load() {
    try {
      const raw = window.localStorage.getItem(KEY);
      const list = raw ? JSON.parse(raw) : [];
      return Array.isArray(list)
        ? list
            .filter((item) => item && item.recipeId && item.date)
            .sort((a, b) => String(b.updatedAt || b.date).localeCompare(String(a.updatedAt || a.date)))
        : [];
    } catch (error) {
      return [];
    }
  }

  function save(list) {
    try {
      window.localStorage.setItem(KEY, JSON.stringify(list));
      return true;
    } catch (error) {
      return false;
    }
  }

  function upsert(entry) {
    const date = String(entry.date || new Date().toISOString().slice(0, 10));
    const id = String(entry.id || `${entry.recipeId}__${date}`);
    const next = {
      id,
      recipeId: String(entry.recipeId || ""),
      name: String(entry.name || ""),
      url: String(entry.url || ""),
      date,
      rating: Number(entry.rating) || 0,
      notes: String(entry.notes || ""),
      photo: String(entry.photo || ""),
      cover: String(entry.cover || ""),
      updatedAt: new Date().toISOString(),
    };
    if (!next.recipeId) return null;
    const list = load().filter((item) => item.id !== id);
    list.unshift(next);
    return save(list) ? next : null;
  }

  function remove(id) {
    return save(load().filter((item) => item.id !== id));
  }

  window.XiaoBaiPracticeLog = {
    KEY,
    load,
    save,
    upsert,
    remove,
  };
})();
