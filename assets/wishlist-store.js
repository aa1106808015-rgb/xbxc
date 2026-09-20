(function () {
  "use strict";

  const KEY = "xiaobai-wishlist-v1";

  function load() {
    try {
      const raw = window.localStorage.getItem(KEY);
      const list = raw ? JSON.parse(raw) : [];
      return Array.isArray(list) ? list.filter((item) => item && item.id) : [];
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

  function has(id) {
    return load().some((item) => item.id === id);
  }

  function add(snapshot) {
    const item = {
      id: String(snapshot.id || ""),
      name: String(snapshot.name || "未命名菜谱"),
      url: String(snapshot.url || ""),
      cover: String(snapshot.cover || ""),
      lesson: String(snapshot.lesson || ""),
      addedAt: new Date().toISOString(),
    };
    if (!item.id) return false;
    const list = load().filter((entry) => entry.id !== item.id);
    list.unshift(item);
    return save(list);
  }

  function remove(id) {
    return save(load().filter((item) => item.id !== id));
  }

  function toggle(snapshot) {
    if (has(snapshot.id)) {
      remove(snapshot.id);
      return false;
    }
    add(snapshot);
    return true;
  }

  window.XiaoBaiWishlist = {
    KEY,
    load,
    save,
    has,
    add,
    remove,
    toggle,
  };
})();
