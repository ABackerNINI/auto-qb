/* auto-qb 新版 WEB UI · 主表行语言引擎(无依赖, 无构建链)
 *
 * 机制: html[data-rowlang] + CSS 结构规则(阶段 2 落地 shared/row_lang.css, 单点作用域 .rl-scope)。
 * - 本文件必须在 <head> 中**同步**执行: 首帧前确定行语言, 无 FOUC(仿 prism/js/theme.js 模式)。
 * - 偏好持久化: localStorage["autoqb.ui.rowlang"]; 值域 flat(平板发丝线, 默认) / wave(波纹扩散);
 *   未存储或存储值非法时用默认 flat; 隐私模式写入失败仅降级为会话内生效。
 * - 切换时在 documentElement 上派发 CustomEvent "autoqb:rowlangchange"(detail.lang), 不进 Vue 状态
 *   —— 共享的 app.js 零改动。
 * - 菜单条目 class 固定为 .rowlang-item, **绝不能复用 .theme-item**: theme.js 的 document 级委托会把
 *   .theme-item 一律当主题切换处理, 复用会让行语言点击被主题引擎误吞。
 * - 菜单开合分两场景(topbar.html 两个 ui-diff 条件块, 同一页面只渲染其一):
 *   - prism: 分组内嵌 #theme-menu, 开合/Escape/点外部关闭由 theme.js 对 #theme-menu 的既有委托
 *     统一承担, 本文件只管条目点击与 #theme-btn 点击后的激活态同步;
 *   - 非 prism(atlas/console): 独立 #rowlang-btn/#rowlang-menu, 开合/点外部关闭/Escape 由本文件
 *     自管(两场景按元素存在性自然分流, 元素不存在即空操作, 互不干扰)。
 *   菜单未渲染时所有 UI 同步均为空操作。
 * - 阶段3: wave 专属运行时 —— 斑马标线(.rl-zebra 按 .group-table 容器内数据行序打标)与波源
 *   坐标(--mx = mousemove 行盒内百分比, 扫层 transform-origin)。flat 下两者全部空转(不写
 *   class/style), 行为与阶段2 完全一致。
 */
(function () {
  "use strict";
  var KEY = "autoqb.ui.rowlang";
  var LANGS = ["flat", "wave"];
  var DEFAULT = "flat";

  function stored() {
    try { return localStorage.getItem(KEY); } catch (e) { return null; }
  }
  function known(id) {
    return LANGS.indexOf(id) !== -1;
  }
  function resolve() {
    var s = stored();
    if (s && known(s)) return s;
    return DEFAULT;
  }
  function apply(id) {
    if (!known(id)) return;
    document.documentElement.setAttribute("data-rowlang", id);
  }

  apply(resolve());

  /* ---- 阶段3: wave 斑马标线(.rl-zebra) + 波源坐标(--mx) ----
   * 斑马计数口径: 每个 .group-table 容器内独立起算 —— 三主表(种子/辅种/追剧)每页各有且仅有
   * 一个 .group-table(挂在同一个常驻 main.content.rl-scope 下, 页面切换时整块重建), 容器内
   * 之前同级 .group-row 兄弟数 = 整页可见数据行序; 分组展开体(.detail)与占位(.row-pad)不是
   * .group-row, 不计数, 故展开/收起与窗口化换行都不会扰动已滚过行的奇偶。
   * 不能用 :nth-child: 直接子元素混有 .detail/.row-pad, DOM 序 != 数据序(计划 26-10-30-0217 §07)。
   * MutationObserver 盯 body childList(subtree): 行窗口化/筛选/页面切换都是整块增删, 回调里
   * 对每个容器**全量重标**(每容器几十行, classList.toggle 幂等), 不做增量 diff; rAF 合并同一
   * 帧内的多次 mutation。flat 时 toggle 条件恒 false = 摘标空操作, 对 flat 零副作用。
   */
  function isWave() {
    return document.documentElement.getAttribute("data-rowlang") === "wave";
  }
  function zebraTable(table, wave) {
    var n = 0;
    var kids = table.children;
    for (var i = 0; i < kids.length; i++) {
      var el = kids[i];
      if (!el.classList || !el.classList.contains("group-row")) continue;
      el.classList.toggle("rl-zebra", wave && n % 2 === 1);
      n++;
    }
  }
  function rezebra() {
    var wave = isWave();
    var scopes = document.querySelectorAll(".rl-scope");
    for (var i = 0; i < scopes.length; i++) {
      var tables = scopes[i].querySelectorAll(".group-table");
      for (var j = 0; j < tables.length; j++) zebraTable(tables[j], wave);
    }
  }
  var zebraScheduled = false;
  function scheduleRezebra() {
    if (zebraScheduled) return;
    zebraScheduled = true;
    window.requestAnimationFrame(function () {
      zebraScheduled = false;
      rezebra();
    });
  }
  function bindZebra() {
    if (!window.MutationObserver) return; /* 无 observer 的老环境: 仅降级掉斑马(纯观感), 波动效不受影响 */
    var mo = new MutationObserver(scheduleRezebra);
    function start() {
      mo.observe(document.body, { childList: true, subtree: true });
      rezebra(); /* 首屏已静态渲染的内容; 此后的 Vue 渲染走 observer */
    }
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", start);
    } else {
      start();
    }
    /* 切换语言即刻重算: wave <- 立刻打标(不等下一次 DOM 变动); flat <- 全量摘标。
     * class 变更不触发 childList observer, 这里必须显式调。 */
    document.documentElement.addEventListener("autoqb:rowlangchange", rezebra);
  }

  /* --mx: document 级委托 mousemove(rAF 节流, 每帧最多一次 getBoundingClientRect), 命中
   * .rl-scope .group-row 时按行盒写百分比。**仅 wave 写**: flat 下没有任何规则消费 --mx,
   * 白写 style 变更还与 Vue 的 :style 补丁共写同一 attribute, 有害无益 —— 故 flat 热路径
   * (mousemove 高频)第一行即返回, 零副作用。行窗口化重建的行丢失 --mx 属预期(未 hover 的行
   * 扫层恒 scaleX(0), 无所谓 origin)。 */
  var mxEvent = null;
  var mxScheduled = false;
  function applyMx() {
    mxScheduled = false;
    var e = mxEvent;
    mxEvent = null;
    if (!e || !e.target || !e.target.closest) return;
    var row = e.target.closest(".rl-scope .group-row");
    if (!row) return;
    var rect = row.getBoundingClientRect();
    if (!rect.width) return;
    var pct = ((e.clientX - rect.left) / rect.width) * 100;
    row.style.setProperty("--mx", pct.toFixed(2) + "%");
  }
  function bindMx() {
    document.addEventListener("mousemove", function (e) {
      if (!isWave()) return;
      mxEvent = e;
      if (mxScheduled) return;
      mxScheduled = true;
      window.requestAnimationFrame(applyMx);
    }, { capture: true, passive: true });
  }

  bindZebra();
  bindMx();

  window.AutoQbRowLang = {
    current: function () {
      return document.documentElement.getAttribute("data-rowlang") || resolve();
    },
    set: function (id) {
      if (!known(id)) return;
      apply(id);
      try { localStorage.setItem(KEY, id); } catch (e) { /* 隐私模式等: 本次会话内仍生效 */ }
      document.documentElement.dispatchEvent(
        new CustomEvent("autoqb:rowlangchange", { detail: { lang: id } }));
      this.syncUI();
    },
    /* 菜单激活态(菜单未渲染时 querySelectorAll 落空, 即空操作) */
    syncUI: function () {
      var cur = this.current();
      var items = document.querySelectorAll(".rowlang-item");
      for (var i = 0; i < items.length; i++) {
        items[i].classList.toggle("on", items[i].getAttribute("data-rowlang") === cur);
      }
    },
    /* 行语言条目: 单个 document 级委托, 两场景共管:
     * - prism(#theme-btn 存在): 菜单本体由 theme.js 开合, 与 theme.js 的委托顺序无关 ——
     *   点 #theme-btn 后用 setTimeout(syncUI, 0) 在开合处理完再刷激活态;
     * - 非 prism(#rowlang-btn 存在): 本文件自管开合(点按钮翻 hidden / 点外部收 / Escape 收),
     *   开合后立即 syncUI。元素不存在的一侧全部空操作。 */
    bindUI: function () {
      if (this._bound) return;
      this._bound = true;
      var self = this;
      document.addEventListener("click", function (e) {
        if (!e.target || !e.target.closest) return;
        if (e.target.closest("#theme-btn")) {
          window.setTimeout(function () { self.syncUI(); }, 0);
          return;
        }
        if (e.target.closest("#rowlang-btn")) {
          var menu = document.getElementById("rowlang-menu");
          if (menu) {
            menu.hidden = !menu.hidden;
            self.syncUI();
          }
          return;
        }
        var item = e.target.closest(".rowlang-item");
        if (item) {
          e.preventDefault();
          self.set(item.getAttribute("data-rowlang"));
          var themeMenu = item.closest(".theme-menu");
          if (themeMenu) themeMenu.hidden = true;
          var rowlangMenu = item.closest(".rowlang-menu");
          if (rowlangMenu) rowlangMenu.hidden = true;
          return;
        }
        /* 非 prism 点外部关闭: prism 场景 #rowlang-menu 不存在, 空操作; 点在菜单内部
         * (标题等非条目区)不收 —— contains 判定。 */
        var rlMenu = document.getElementById("rowlang-menu");
        if (rlMenu && !rlMenu.hidden && !rlMenu.contains(e.target)) rlMenu.hidden = true;
      });
      /* 非 prism Escape 收起(prism 场景空操作, theme.js 的 Escape 链不归本文件管) */
      document.addEventListener("keydown", function (e) {
        if (e.key !== "Escape") return;
        var rlMenu = document.getElementById("rowlang-menu");
        if (rlMenu && !rlMenu.hidden) rlMenu.hidden = true;
      });
    },
  };

  window.AutoQbRowLang.bindUI();
})();
