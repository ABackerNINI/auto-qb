/* fx.js -- fx 动效库单挂载器: 扫 data-fx / data-fx-variant 统一初始化
 * --------------------------------------------------------------------------
 * 计划: memory-bank/plans/26-10-31-2316-plan-webui-fx-skin.html (S2 步)
 * 调研: memory-bank/reports/26-10-31-2340-report-webui-fx-skin.html (S1 §06 结论 3:
 *   View Transitions + @starting-style 覆盖「编排」与「display:none 进出场」,
 *   JS 侧瘦身为: 挂载器 + 重触发跳终态 + 少量 rect 测量 -- 本文件即该薄层)。
 *
 * 定位(设计底线, 计划 §01):
 *   - 零依赖: 不引入任何库; classic script + IIFE, 只导出 window.AQB_FX 一域
 *     (顶层不落 let/const -- classic script 全局词法环境撞名会 SyntaxError 白屏,
 *     见 pitfalls/web-ui/classic-script-top-level-const-collision.md)。
 *   - 挂载面(S6 前半): flux shell 静态 <script>(计划 26-10-31-2316; 不进
 *     tpl-manifest -- 四套清单守阵钉逐项相等, fx 只服务 flux)。本文件不读
 *     任何其它 AQB_* 域, 单独加载亦可独立工作; 初始 scan 早于 boot.js 的
 *     模板异步注入属正常 -- 幂等重扫, 消费方挂载 data-fx 元素后再调 scan()。
 *   - 不装 MutationObserver: Vue 轮询把列表行整批换掉(每数秒一次), 观察器会
 *     跟着高频空转(perf-cadence 口径) -- 覆盖新增节点的机制是「幂等重扫」:
 *     任何时刻可再调 AQB_FX.scan(), 已初始化的元素按标记跳过。
 *
 * data-fx 属性约定(与 fx.css 基线规则一一对应; 名录单点 = REGISTRY.effects,
 * 基线 9 个(S2) + S6 提升原语 18 个(showcase S4 选定入库), 空格分隔可多值):
 *   data-fx="<效果名...>"                      见 REGISTRY.effects
 *   data-fx-variant="subtle|bold|spring"       强度变体, 可省
 *   <html data-fx-preset="neon|glass|crisp">   风格层整套配方(fx-presets.css)
 *   data-fx-exit                               退场态标记(挂载器写, 见 exit)
 *   data-fx-play                               一次性动画触发标记(挂载器写, 见 play)
 *   data-fx-dir="left|right"                   dir 方向槽(S6, fx.js::dir 写)
 *   data-fx-pushed                             push 让位态标记(S6; F7e 已退役 —— fx-mount
 *                                              不再 stamp, 仅 fx.css 库面保留规则不消费)
 *   data-fx-on="1"                             已扫描标记(挂载器写, 幂等依据)
 *   --fx-i (style)                             stagger 序号槽(0..N, CSS 算延迟)
 *   --fx-life (style)                          countdown 倒计时毫秒(S6, 消费方写)
 *   --fx-base-tx (style)                       pop 基础位移(S6, 消费方写)
 *   --fx-push-y (style)                        push 让位量(S6; F7e 已退役, 消费方不再写)
 *
 * 漏挂载检测口(S2 交付面之一):
 *   - 扫描时给元素写 data-fx-on 标记; audit() 汇报「有 data-fx 但没标记」的
 *     元素 = 挂载器没跑到它(fx.js 漏进 manifest / 新节点没重扫)。
 *   - fx.js 整个漏挂时 window.AQB_FX 为 undefined, 消费方/排障页可一行判:
 *     if (!window.AQB_FX) ... (fx 挂行没进页面的静态信号)。
 *   - audit() 同时按 REGISTRY 校验未知的动效名/变体名/预设名 -- 模板里写了
 *     data-fx 拼错值时 CSS 静默不生效, 这里是唯一的报错出口。
 */
(function () {
  "use strict";

  var MARK = "data-fx-on";

  /* 动效名/变体名/预设名注册表: fx.css 基线原语 + S6 提升原语 + fx-presets.css
   * 配方名。新增任一名 = CSS 与这里同轮补(漏补 = audit 恒报未知, 不会静默;
   * 反向漏补 CSS 只补注册表 = audit 放行但样式静默不生效, 守阵
   * test_frontend_fx_wiring 逐名对账)。 */
  var REGISTRY = {
    effects: [
      /* 基线(S2): 入场 fade/rise/pop/slip + 注意力 sheen/pulse + 反馈 lift/glow/press */
      "fade", "rise", "pop", "slip", "sheen", "pulse", "lift", "glow", "press",
      /* S6 提升(计划 §06 S4 结论; 与 fx.css「S6 提升原语」段一一对应) */
      "ripple", "icon", "focus-ring", "focus-float", "shake", "headshake", "dir",
      "zoom", "push", "row-hover", "row-sel", "row-in", "row-out",
      "check", "countdown", "ico-spring", "danger",
    ],
    variants: ["subtle", "bold", "spring"],
    presets: ["neon", "glass", "crisp"],
  };

  /* ---- 扫描: 幂等, DOM 就绪后可重复调 ---- */

  function scan(root) {
    var scope = root && root.querySelectorAll ? root : document;
    var nodes = scope.querySelectorAll("[data-fx]");
    var fresh = 0;
    for (var i = 0; i < nodes.length; i++) {
      var el = nodes[i];
      if (el.hasAttribute(MARK)) continue;
      el.setAttribute(MARK, "1");
      fresh++;
    }
    return { total: nodes.length, fresh: fresh };
  }

  /* ---- audit: 漏挂载检测口(纯读, 不改 DOM) ---- */

  function describe(el) {
    var cls = (el.getAttribute("class") || "").split(/\s+/).slice(0, 2).join(".");
    return el.tagName.toLowerCase() + (cls ? "." + cls : "") + "#" + (el.getAttribute("id") || "-");
  }

  function audit(root) {
    var scope = root && root.querySelectorAll ? root : document;
    var nodes = scope.querySelectorAll("[data-fx]");
    var unmounted = [];
    var unknownEffect = [];
    var unknownVariant = [];
    var empty = [];
    for (var i = 0; i < nodes.length; i++) {
      var el = nodes[i];
      var names = (el.getAttribute("data-fx") || "").trim().split(/\s+/).filter(Boolean);
      if (!names.length) { empty.push(describe(el)); continue; }
      if (!el.hasAttribute(MARK)) unmounted.push(describe(el));
      for (var k = 0; k < names.length; k++) {
        if (REGISTRY.effects.indexOf(names[k]) < 0) {
          unknownEffect.push(describe(el) + " data-fx=" + names[k]);
          break;
        }
      }
      var v = el.getAttribute("data-fx-variant") || "";
      if (v && REGISTRY.variants.indexOf(v) < 0) unknownVariant.push(describe(el) + " data-fx-variant=" + v);
    }
    var presetVal = document.documentElement.getAttribute("data-fx-preset") || "";
    var unknownPreset = (presetVal && REGISTRY.presets.indexOf(presetVal) < 0) ? presetVal : "";
    return {
      total: nodes.length,
      unmounted: unmounted,          /* 有 data-fx 但没被扫过 */
      empty: empty,                  /* data-fx 值为空(声明了动效却没给名) */
      unknownEffect: unknownEffect,  /* 未注册的动效名(CSS 不会生效) */
      unknownVariant: unknownVariant,/* 未注册的变体名 */
      unknownPreset: unknownPreset,  /* 未注册的预设名 */
      ok: !(unmounted.length || empty.length || unknownEffect.length || unknownVariant.length || unknownPreset),
    };
  }

  /* ---- 重触发即跳终态(Apple HIG: 动效应可取消, 不排队 -- S1 §04 C7) ---- */

  /* settle: 元素身上所有跑着的 animation/transition 立即推进到终态 */
  function settle(el) {
    if (!el.getAnimations) return;
    var list;
    try { list = el.getAnimations({ subtree: true }); }
    catch (e) { list = el.getAnimations(); }
    for (var i = 0; i < list.length; i++) {
      try { list[i].finish(); } catch (e) { /* 已结束/无限循环动画不可 finish, 留在原地 */ }
    }
  }

  /* play: 一次性动画(sheen/pulse)的触发口 -- 未播完再触发 = 先跳终态再重放,
   * 不排队不复位成半程。用法: AQB_FX.play(el)。 */
  function play(el) {
    settle(el);
    el.removeAttribute("data-fx-play");
    void el.offsetWidth; /* 强制 reflow: 让属性摘除落帧, 重挂才能重启动画 */
    el.setAttribute("data-fx-play", "");
  }

  /* ---- 退场: 写 data-fx-exit(骨对: 短 + accelerate, fx.css 退场态), 等
   *      transitionend 或超时兜底后回调 -- 调用方在 onDone 里移除节点。
   *      exit() 可重复调(幂等: 已在退场态则只补回调)。 ---- */

  function maxDurationMs(el) {
    if (!window.getComputedStyle) return 0;
    var cs = window.getComputedStyle(el);
    var durs = (cs.transitionDuration || "").split(",").map(parseFloat).filter(function (n) { return !isNaN(n); });
    var delays = (cs.transitionDelay || "").split(",").map(parseFloat).filter(function (n) { return !isNaN(n); });
    var max = 0;
    for (var i = 0; i < durs.length; i++) {
      var total = durs[i] + (delays[i % Math.max(delays.length, 1)] || 0);
      if (total > max) max = total;
    }
    return Math.round(max * 1000);
  }

  function exit(el, onDone) {
    var fired = false;
    function finish() {
      if (fired) return;
      fired = true;
      el.removeEventListener("transitionend", onEnd, true);
      if (onDone) onDone();
    }
    function onEnd(ev) {
      if (ev.target === el && (ev.propertyName === "opacity" || ev.propertyName === "transform")) finish();
    }
    el.addEventListener("transitionend", onEnd, true);
    setTimeout(finish, maxDurationMs(el) + 60); /* transitionend 可能被降级/中断吞掉, 超时兜底 */
    el.setAttribute("data-fx-exit", "");
  }

  /* ---- View Transitions 探测(D5): 支持则走编排, 不支持 = 直接执行更新
   *      (无动效终态), 调用方零分支。返回 transition 对象或 null。 ---- */

  function viewTransition(update) {
    if (document.startViewTransition) return document.startViewTransition(update);
    update();
    return null;
  }

  /* ---- 环境探针 ---- */

  function reduced() {
    return !!(window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches);
  }

  function preset() {
    return document.documentElement.getAttribute("data-fx-preset") || "";
  }

  /* ---- S6 提升(showcase 页内实现入库, 计划 §06 S4 结论) ---- */

  /* ripple 波纹(D1-4): 向宿主 [data-fx~="ripple"] 注入一个 .fx-ripple 节点
   * (几何: 直径 = 宿主较长边 x2, 圆心 = 指针落点, 缺省中心), animationend /
   * 超时双通道自清。RM: 不注入(直接按压终态, showcase 同口径)。常规路径走
   * 下方 document 级 pointerdown 单委托, 本函数供程序化触发复用。 */
  function ripple(host, ev) {
    if (reduced()) return;
    var r = host.getBoundingClientRect();
    if (!r.width && !r.height) return;
    var d = Math.max(r.width, r.height) * 2;
    var s = document.createElement("span");
    s.className = "fx-ripple";
    s.style.width = d + "px";
    s.style.height = d + "px";
    var cx = ev && typeof ev.clientX === "number" && (ev.clientX || ev.clientY) ? ev.clientX - r.left : r.width / 2;
    var cy = ev && typeof ev.clientY === "number" && (ev.clientX || ev.clientY) ? ev.clientY - r.top : r.height / 2;
    s.style.left = (cx - d / 2) + "px";
    s.style.top = (cy - d / 2) + "px";
    s.addEventListener("animationend", function () { s.remove(); }, { once: true });
    host.appendChild(s);
    setTimeout(function () { s.remove(); }, 450);
  }

  /* document 级 pointerdown 单委托: 命中 [data-fx~="ripple"] 即注入波纹。
   * 捕获段挂 document 一次, 动态插入的宿主零接线自动覆盖(无 MutationObserver)。 */
  document.addEventListener("pointerdown", function (ev) {
    var t = ev.target && ev.target.closest ? ev.target.closest('[data-fx~="ripple"]') : null;
    if (t) ripple(t, ev);
  }, true);

  /* dir 方向感知滑动重触发口(D7-4): 切页签/切列表方向时调 dir(el, "left"|"right")
   * -- 摘属性 -> 强制 reflow -> 重写, 同方向的连续切换也能重新播放(fx.css 的
   * fx-dir-* 动画吃 data-fx-dir 属性)。 */
  function dir(el, direction) {
    el.removeAttribute("data-fx-dir");
    void el.offsetWidth;
    el.setAttribute("data-fx-dir", direction === "left" ? "left" : "right");
  }

  /* ---- 装载: 就绪即扫; boot.js 保序注入时模板已注入, 兜底 DOMContentLoaded ---- */
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", function () { scan(); });
  } else {
    scan();
  }

  window.AQB_FX = {
    MARK: MARK,
    registry: REGISTRY,
    scan: scan,
    audit: audit,
    settle: settle,
    play: play,
    exit: exit,
    viewTransition: viewTransition,
    ripple: ripple,
    dir: dir,
    reduced: reduced,
    preset: preset,
  };
})();
