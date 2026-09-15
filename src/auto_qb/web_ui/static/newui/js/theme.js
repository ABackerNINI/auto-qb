/* auto-qb 新版 WEB UI · 主题引擎(无依赖, 无构建链)
 *
 * 机制: html[data-theme] + CSS 自定义属性(见 css/tokens.css 与 css/themes/*.css)。
 * - 本文件必须在 <head> 中**同步**执行: 首帧前确定主题, 无 FOUC。
 * - 偏好持久化: localStorage["autoqb.ui.theme"]; 未选择过时跟随系统 prefers-color-scheme
 *   (暗 = 深海机房, 亮 = 极地晨霜), 且系统明暗变化时实时跟随。
 * - 顶栏切换器为事件委托绑定(顶栏在登录验证通过前不渲染, 不能假设元素已存在),
 *   不进 Vue 状态 —— 共享的 app.js 零改动。
 * - 新增主题: 在 css/themes/ 加一个文件 + 在 THEMES 注册表加一行, 组件零改动。
 */
(function () {
  "use strict";
  var KEY = "autoqb.ui.theme";
  var THEMES = [
    { id: "ocean",  name: "深海机房", dark: true  },
    { id: "galaxy", name: "暗夜星云", dark: true  },
    { id: "frost",  name: "极地晨霜", dark: false },
    { id: "golden", name: "麦秋",     dark: false },
    { id: "orbit",  name: "品牌轨道", dark: true  },
  ];
  var DARK_DEFAULT = "ocean";
  var LIGHT_DEFAULT = "frost";

  function stored() {
    try { return localStorage.getItem(KEY); } catch (e) { return null; }
  }
  function systemDark() {
    return !!(window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches);
  }
  function known(id) {
    return THEMES.some(function (t) { return t.id === id; });
  }
  function resolve() {
    var s = stored();
    if (s && known(s)) return s;
    return systemDark() ? DARK_DEFAULT : LIGHT_DEFAULT;
  }
  function apply(id) {
    if (!known(id)) return;
    document.documentElement.setAttribute("data-theme", id);
  }

  apply(resolve());

  /* 未手动选择过主题: 跟随系统明暗实时切换 */
  if (window.matchMedia && !stored()) {
    var mq = window.matchMedia("(prefers-color-scheme: dark)");
    var onSys = function () { apply(resolve()); };
    if (mq.addEventListener) mq.addEventListener("change", onSys);
    else if (mq.addListener) mq.addListener(onSys);
  }

  window.AutoQbTheme = {
    list: THEMES,
    current: function () {
      return document.documentElement.getAttribute("data-theme") || resolve();
    },
    set: function (id) {
      if (!known(id)) return;
      apply(id);
      try { localStorage.setItem(KEY, id); } catch (e) { /* 隐私模式等: 本次会话内仍生效 */ }
      document.documentElement.dispatchEvent(
        new CustomEvent("autoqb:themechange", { detail: { theme: id } }));
      this.syncUI();
    },
    /* 菜单激活态(菜单未渲染时为空操作) */
    syncUI: function () {
      var menu = document.getElementById("theme-menu");
      if (!menu) return;
      var cur = this.current();
      var items = menu.querySelectorAll(".theme-item");
      for (var i = 0; i < items.length; i++) {
        items[i].classList.toggle("on", items[i].getAttribute("data-theme") === cur);
      }
    },
    /* 顶栏切换器: 单个 document 级委托同时处理 开/关菜单、选中主题、点外部关闭 */
    bindUI: function () {
      if (this._bound) return;
      this._bound = true;
      var self = this;
      document.addEventListener("click", function (e) {
        if (!e.target || !e.target.closest) return;
        var menu = document.getElementById("theme-menu");
        if (!menu) return;
        if (e.target.closest("#theme-btn")) {
          menu.hidden = !menu.hidden;
          if (!menu.hidden) self.syncUI();
          return;
        }
        var item = e.target.closest(".theme-item");
        if (item && menu.contains(item)) {
          e.preventDefault();
          self.set(item.getAttribute("data-theme"));
          menu.hidden = true;
          return;
        }
        if (!menu.hidden) menu.hidden = true;
      });
      document.addEventListener("keydown", function (e) {
        if (e.key === "Escape") {
          var menu = document.getElementById("theme-menu");
          if (menu) menu.hidden = true;
        }
      });
    },
  };

  window.AutoQbTheme.bindUI();
})();
