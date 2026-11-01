/* fx-mount.js -- flux 皮肤 fx 动效挂载器(状态驱动面, S6 后半)
 * --------------------------------------------------------------------------
 * 计划: memory-bank/plans/26-10-31-2316-plan-webui-fx-skin.html (S6, S4 选定 24 项)
 *
 * 分工: fx.js(AQB_FX)是零依赖单挂载器, 只认 data-fx 属性; 本文件是 flux 专属
 *   消费层 -- 模板分片是四皮肤共享的, 不能给共享模板加属性, 故**状态驱动**的
 *   效果(行插入/退场、页签方向、toast spawn/退场、dock 让位、登录微震、数字
 *   滚动)由本文件
 *   在运行时程序化补属性; 共享 JS 消费点按 this.ui === "flux" 门控调用本域。
 *   纯 CSS 态效果(hover/active/focus/类触发)在 flux/css/fx-mount.css, 不过这里。
 *
 * 隔离: 本文件只被 flux/index.html 静态 <script> 加载(守阵 test_frontend_fx_wiring),
 *   其它皮肤 window.AQB_FX_MOUNT 恒为 undefined, 加上共享侧的 ui 门控 = 双保险。
 *   不装 MutationObserver(fx.js 同口径, Vue 轮询会让它高频空转); 覆盖新增节点的
 *   机制 = 消费点触发时的差分扫描(本文件)与幂等重扫(fx.js::scan)。
 * -------------------------------------------------------------------------- */
(function () {
  "use strict";

  var FX = window.AQB_FX;
  if (!FX) return; /* fx.js 漏挂: 本域整体不启用(静态信号, 消费方判空跳过) */

  /* ---- ripple(D1-4): document 级 pointerdown 单委托命中 .bt。fx.js 自带委托只认
   * [data-fx~="ripple"](共享模板不给加属性, 恒不命中), 这里按 flux 的按钮族补一条;
   * RM 由 FX.ripple 内部把关(RM 不注入), 载体(裁边)在 flux/css/fx-mount.css。 ---- */
  document.addEventListener("pointerdown", function (ev) {
    var t = ev.target && ev.target.closest ? ev.target.closest(".bt") : null;
    if (t && !t.disabled) FX.ripple(t, ev);
  }, true);

  /* ---- 页签方向感知滑动(D7-4) ----
   * 消费点 = view.js::setViewMode(主表三页签)与 state.js watch.page(主内容页 <-> 设置页)。
   * locKey = 页面位置单值: 主表页用 viewMode, 设置页恒 "settings"(设置页内部的
   * hub.view 二级导航不算页签切换, 不复算方向)。方向 = 槽位序比大小: 前进 = 新页签
   * 从右入(fx-dir-r), 后退 = 从左入(fx-dir-l); 首次调用只记位置不播。
   * 动画目标: 主表页 = main.content(三视图共壳, 跨切换持久), 设置页 = main.ce-page。 */
  var LOC_ORDER = { groups: 0, torrents: 1, shows: 2, settings: 3 };
  var prevLoc = null;
  function tabDir(loc) {
    var prev = prevLoc;
    prevLoc = loc;
    if (prev === null || prev === loc) return;
    var a = LOC_ORDER[prev];
    var b = LOC_ORDER[loc];
    if (a === undefined || b === undefined || a === b) return;
    var direction = b > a ? "right" : "left";
    requestAnimationFrame(function () {
      var el = document.querySelector(loc === "settings" ? "main.ce-page" : "main.content");
      if (!el) return;
      el.setAttribute("data-fx", "dir");
      FX.dir(el, direction);
      FX.scan();
    });
  }

  /* ---- 底部详情面板 push-content(D3-4, transform 版) ----
   * 消费点 = state.js watch.drawerVisible(开/合与切页回来的唯一出入门口)。
   * fx push 原语契约: 消费方写 data-fx-pushed + 作用域 --fx-push-y(让位量)。
   * push 载体 = main.content(主表内容区, 面板吸底遮住的就是它); 让位量 =
   * .drawer-dock 实时高 -- 面板入场由 drawer.js 的 rAF 追高逐帧变化, 用
   * ResizeObserver 跟写 --fx-push-y 保持同幅。RM: fx.css 降级块把过渡归零 =
   * 让位瞬时到位(状态本身保留, 不是装饰动画)。 */
  var ro = null;
  var pushedEl = null;
  function dock(open) {
    var el = document.querySelector("main.content");
    if (!el) return;
    if (el !== pushedEl) {
      pushedEl = el; /* 切页后 main.content 是新节点: 重 stamp */
      el.setAttribute("data-fx", "push");
    }
    if (open) applyPush();
    else pushedEl.removeAttribute("data-fx-pushed");
    if (!ro && window.ResizeObserver) {
      ro = new ResizeObserver(applyPush);
      var dk = document.querySelector(".drawer-dock");
      if (dk) ro.observe(dk);
    }
    FX.scan();
  }
  function applyPush() {
    if (!pushedEl) return;
    var dk = document.querySelector(".drawer-dock");
    var h = dk ? dk.offsetHeight : 0;
    if (h > 0) {
      pushedEl.style.setProperty("--fx-push-y", h + "px");
      pushedEl.setAttribute("data-fx-pushed", "");
    } else {
      pushedEl.removeAttribute("data-fx-pushed");
    }
  }

  /* ---- 行插入/退场(D4-4L / D4-5L, max-height 版) ----
   * 数据差分驱动: 消费点 = state.js watch.torrents / watch.groups(watch 默认 flush
   * pre -- 赋值后、Vue 重渲前, 旧行仍在 DOM, 退场幽灵此刻抓取克隆)。行窗口化
   * (滚动虚拟化)只动可见窗口、不动数据数组, 天然不触发本差分 -- 滚动重渲不会被
   * 误当行插入。RM: 直接只更新缓存(无动效终态 = 行直接出现/消失)。
   * keyAttr: "hash"(种子页平铺行, data-hash) | "key"(辅种组行, data-key)。 */
  var prevKeys = { hash: null, key: null };
  function rows(arr, keyAttr) {
    var cur = {};
    var list = arr || [];
    for (var i = 0; i < list.length; i++) {
      if (list[i] && list[i][keyAttr] != null) cur[list[i][keyAttr]] = 1;
    }
    var prev = prevKeys[keyAttr];
    prevKeys[keyAttr] = cur;
    if (FX.reduced()) return;
    if (!prev) return; /* 首轮只建缓存 */
    var added = [];
    var removed = [];
    var k;
    for (k in cur) if (!prev[k]) added.push(k);
    for (k in prev) if (!cur[k]) removed.push(k);
    if (!added.length && !removed.length) return;
    var ghosts = [];
    for (i = 0; i < removed.length; i++) {
      var g = ghostOf(removed[i], keyAttr);
      if (g) ghosts.push(g);
    }
    requestAnimationFrame(function () {
      /* rAF 在 Vue 微任务 flush 之后、本帧样式计算之前 -- 新行 stamp 与 fx-row-in
       * 动画声明同帧生效, 幽灵此时插入播退场。 */
      var dirty = ghosts.length > 0;
      for (var i = 0; i < added.length; i++) {
        var n = rowNode(added[i], keyAttr);
        if (n && !n.hasAttribute("data-fx")) {
          n.setAttribute("data-fx", "row-in");
          dirty = true;
        }
      }
      for (i = 0; i < ghosts.length; i++) spawnGhost(ghosts[i]);
      if (dirty) FX.scan();
    });
  }
  function rowSel(keyAttr, key) {
    var v = (window.CSS && CSS.escape) ? CSS.escape(String(key)) : String(key).replace(/"/g, "'");
    return (keyAttr === "hash" ? '[data-hash="' : '[data-key="') + v + '"]';
  }
  function rowNode(key, keyAttr) {
    return document.querySelector(rowSel(keyAttr, key));
  }
  /* 退场幽灵: 旧行克隆定格在原位(容器内绝对定位), fx-row-out(max-height 收拢)播完自清 */
  function ghostOf(key, keyAttr) {
    var n = rowNode(key, keyAttr);
    if (!n || !n.parentElement) return null;
    var cont = n.parentElement;
    var r = n.getBoundingClientRect();
    var cr = cont.getBoundingClientRect();
    return {
      el: n.cloneNode(true),
      cont: cont,
      top: r.top - cr.top + cont.scrollTop,
      left: r.left - cr.left + cont.scrollLeft,
      w: r.width,
      h: r.height,
    };
  }
  function spawnGhost(g) {
    if (!g.cont.isConnected) return;
    var s = g.el.style;
    s.position = "absolute";
    s.top = g.top + "px";
    s.left = g.left + "px";
    s.width = g.w + "px";
    s.margin = "0";
    s.pointerEvents = "none";
    s.setProperty("--fx-row-h", g.h + "px"); /* 行高单点按实际行高覆写(fx.css 缺省 44px) */
    g.el.setAttribute("data-fx", "row-out");
    g.cont.appendChild(g.el);
    setTimeout(function () {
      if (g.el.parentNode) g.el.parentNode.removeChild(g.el);
    }, 280); /* 动画 200ms + 余量; animationend 被降级/中断吞掉的超时兜底 */
  }

  /* ---- toast spawn(D6-1 入场半 / D6-2 倒计时 / D6-4 ico-spring / D6-5 danger) ----
   * 消费点 = ui_feedback.js::toast / _finishToast($nextTick 后调本函数)。差分扫描
   * .toast-wrap 现存条(节点由 Vue v-for 渲染, 不给共享模板加属性): 新条 stamp
   * rise 入场 + ico-spring 图标 + 非 sticky 条的 --fx-life 倒计时标记; 已在场条
   * 按kind 类补 danger(busy 等待条结算成 error/timeout 的原位升级)。 */
  var toastSeq = 0;
  function toastSync(ttl) {
    var wrap = document.querySelector(".toast-wrap");
    if (!wrap) return;
    var nodes = wrap.querySelectorAll(".toast");
    for (var i = 0; i < nodes.length; i++) {
      var n = nodes[i];
      if (!n._fxToast) {
        n._fxToast = 1;
        n.setAttribute("data-fx", "rise");
        /* D6-3 队列 FLIP 的身份牌: 退场包进 View Transitions 时按名配对 */
        n.style.viewTransitionName = "fx-toast-" + (++toastSeq);
        if (ttl > 0) {
          n.style.setProperty("--fx-life", ttl + "ms");
          n.setAttribute("data-fx-cd", "");
        }
        var ico = n.querySelector(".ico");
        if (ico) {
          ico.setAttribute("data-fx", "ico-spring");
          ico.setAttribute("data-fx-play", "");
        }
      }
      if (!n._fxDanger && /\b(error|timeout)\b/.test(n.getAttribute("class") || "")) {
        n._fxDanger = 1;
        n.setAttribute("data-fx", "rise danger");
        n.setAttribute("data-fx-play", "");
      }
    }
    FX.scan();
  }

  /* ---- toast 退场(D6-1 退场半 + D6-3 队列重排 FLIP) ----
   * 消费点 = ui_feedback.js::_dropToast。View Transitions 可用且非 RM: 数组更新包进
   * startViewTransition -- 被移除条按 view-transition-name 快照走默认退场(fade),
   * 存活条同名新旧配对 = FLIP 重排; 不支持/RM: 直接提交(D5: 无动效终态)。 */
  function toastDrop(commit) {
    if (FX.reduced() || !document.startViewTransition) {
      commit();
      return;
    }
    FX.viewTransition(commit);
  }

  /* ---- 登录输入校验失败微震(D5-5) ----
   * 消费点 = auth.js 鉴权失败赋 authError 处(ui 门控)。输入框在 flux 自有 shell
   * 标记里, 但登录段受四皮肤 shell parity 守阵约束(逐字相等), data-fx 属性由本
   * 函数程序化补; .is-invalid 挂上即播(fx.css shake 原语, RM 下无动画), 400ms 后
   * 摘除以便连续失败重播。 ---- */
  function loginShake() {
    requestAnimationFrame(function () {
      var input = document.querySelector('.login-card input[type="password"]');
      if (!input) return;
      if (!input.hasAttribute("data-fx")) input.setAttribute("data-fx", "shake");
      input.classList.remove("is-invalid");
      void input.offsetWidth; /* 重置动画: 连续失败也能重播 */
      input.classList.add("is-invalid");
      FX.scan();
      setTimeout(function () { input.classList.remove("is-invalid"); }, 400);
    });
  }

  /* ---- 数字滚动(P1: 速度/体积实时数据, S7) ----
   * 消费点 = state.js watch totalDl/totalUl(computed 每轮询 tick 变化即触发, ui 门控,
   * 调用方 $nextTick 后进 -- 等 Vue 文本渲染落地再读新值)。轻量数值补间: 逐元素
   * 缓存上次数值(el._fxRoll), rAF 360ms ease-out; 格式沿用节点现文本(小数位与
   * 单位取自新文本, 不自拼 = 不与 fmtSpeed/fmtSize 口径分裂), 单位跨界(KiB/s ->
   * MiB/s)或非数值文本(空/"--")直接跳过落值。写回: .sb-spd .val 是纯文本插值;
   * 今日流量 .val 内含 svg, 写尾部文本节点。Vue 下一轮渲染会整体覆写文本 --
   * 补间窗口(360ms)短于轮询间隔, 终帧写的就是 Vue 的目标文本, 竞态无害; 补间中
   * 再触发 = 重定向目标(取消旧 rAF 从当前值续走)。RM: 直接跳过(Vue 文本即时
   * 到位 = 无动效终态)。首轮只建缓存不播(避免首屏整片滚动)。 */
  var ROLL_MS = 360;
  var ROLL_SEL = ".sb-spd .val, .sb-item.sb-today .v-down, .sb-item.sb-today .v-up";
  function rollTarget(el) {
    var node = el.lastChild;
    while (node && node.nodeType !== 3) node = node.previousSibling; /* 尾部文本节点(纯文本插值即元素自身) */
    if (!node) return null;
    var m = (node.nodeValue || "").match(/^([\d.]+)(.*)$/);
    if (!m || m[1].indexOf(".") === 0) return null;
    var num = parseFloat(m[1]);
    if (!isFinite(num)) return null;
    return { node: node, num: num, dec: (m[1].split(".")[1] || "").length, unit: m[2] };
  }
  function rollOne(el, t) {
    var st = el._fxRoll;
    if (st.unit !== undefined && st.unit !== t.unit) { /* 单位跨界: 补间无意义, 直接落值 */
      st.num = t.num;
      st.unit = t.unit;
      return;
    }
    var from = st.num;
    st.num = t.num;
    st.unit = t.unit;
    var t0 = performance.now();
    if (st.raf) cancelAnimationFrame(st.raf);
    var step = function (now) {
      var p = now - t0 >= ROLL_MS ? 1 : (now - t0) / ROLL_MS;
      var e = 1 - Math.pow(1 - p, 3); /* ease-out cubic */
      t.node.nodeValue = (from + (t.num - from) * e).toFixed(t.dec) + t.unit;
      if (p < 1) st.raf = requestAnimationFrame(step);
      else st.raf = 0;
    };
    st.raf = requestAnimationFrame(step);
  }
  function numRoll() {
    if (FX.reduced()) return;
    var nodes = document.querySelectorAll(ROLL_SEL);
    for (var i = 0; i < nodes.length; i++) {
      var el = nodes[i];
      var t = rollTarget(el);
      if (!t) continue;
      if (!el._fxRoll) { el._fxRoll = { num: t.num, unit: t.unit, raf: 0 }; continue; }
      if (el._fxRoll.num === t.num && el._fxRoll.unit === t.unit) continue;
      rollOne(el, t);
    }
  }

  window.AQB_FX_MOUNT = {
    rows: rows,
    tabDir: tabDir,
    dock: dock,
    toastSync: toastSync,
    toastDrop: toastDrop,
    loginShake: loginShake,
    numRoll: numRoll,
  };
})();
