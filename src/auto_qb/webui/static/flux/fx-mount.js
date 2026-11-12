/* fx-mount.js -- flux 皮肤 fx 动效挂载器(状态驱动面, S6 后半)
 * --------------------------------------------------------------------------
 * 计划: memory-bank/plans/26-10-31-2316-plan-webui-fx-skin.html (S6, S4 选定 24 项)
 *
 * 分工: fx.js(AQB_FX)是零依赖单挂载器, 只认 data-fx 属性; 本文件是 flux 专属
 *   消费层 -- 模板分片是四皮肤共享的, 不能给共享模板加属性, 故**状态驱动**的
 *   效果(行插入/退场、页签方向、toast spawn/退场、面板出入落定回执、登录微震、数字
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

  /* ---- 底部详情面板出入(D3-4; R5 精修 F7e: push 位移本体弃用) ----
   * 消费点 = state.js watch.drawerVisible(开/合与切页回来的唯一出入门口)。
   * 历史口径: S6 起 D3-4 = 开门时 main.content 整体上移(dock 实时高全幅 --fx-push-y,
   * relative-top 载体 = R1 B4); R3(F7c) 改纯过渡 + 滚动结果交还原版三点
   * (drawer.js open $nextTick / afterEnter 钩子 / drawer_store._drawerDone ->
   * _kbRevealRow); R4(F7d) 加 push 落定回执 + 共享侧重入原版可视区单点。
   * F7e 弃用缘由(打点实测, 桩 8137 1440x900): push 位移是布局级搬移, 而原版让位/
   * 重入只有 window 滚动一个工具 -- 文档顶(scrollY=0)没有上滚余量, 点击**上半部分**
   * 行开门时行被位移推出视野(222.2 -> -155.8), 落定回执如期发出、行目标正确
   * (drawer.hash)、原版 _kbScrollRowIntoView 也如期执行, 但负向 scrollBy 被钳制成
   * 无操作 -- 下半部分行(scrollY>0 有余量)则一切正常。用户拍板「全面弃用新逻辑,
   * 只加面板上滑出现以及上推过渡动效」:
   *   - push 位移本体退役: 本文件不再 stamp data-fx="push"/data-fx-pushed/--fx-push-y,
   *     fx-mount.css 的 push 载体段一并删除; shared/fx/fx.css 的 push 原语是通用库面
   *     (REGISTRY 在档), 保留不消费。内容零位移后, 原版三点让位与 console 同构,
   *     任意滚动位置都能兑现「聚焦行上推至不被窗口遮挡的最低位置」。
   *   - dock 只保留动效职责: (1)面板入场动效本体在 flux/css/dialogs.css
   *     (translateY(100%) 底部上滑, 令牌 --fx-dur-panel); (2)入场**落定后**发一次回执
   *     (dock 第二参, F7d 机制保留、换锚), 共享侧消费点(state.js)据此对打开面板的
   *     那一行(drawer.hash, 与输入模态无关)重入原版可视区单点 _kbScrollRowIntoView
   *     -- 本文件只发信号, 不做任何几何解算/滚动(6c 单点纪律)。 */
  var settleCb = null;
  var settleArmed = false;
  var settleTimer = 0;
  /* fx-glide 两个定时器句柄(重复触发幂等面, dock 两分支各撤两个):
   * - glideAddTimer: 回执后挂类的 setTimeout(0) 句柄 —— 关面板/重开若落在「回执→宏任务」间隙
   *   (毫秒级, 程序化关闭可复现), 不撤则回调会在面板已关后才把 fx-glide 挂上并存续 800ms,
   *   期间再开又被 dock(true) 带进新开门窗口(平滑进开门窗 = S-A 症状复发);
   * - glideTimer: 挂上后的 800ms 摘除句柄 —— 上一轮窗口的摘除若还挂着, 会把这一轮回执后刚
   *   挂上的平滑提前摘走(窗口缩短, 键盘滚动手感漂移)。
   * 类本身的残局(定时器已 fire、类还在)由 dock(true) 的防御性摘类兜底。 */
  var glideAddTimer = 0;
  var glideTimer = 0;
  /* 面板入场时长: 与 dialogs.css .drawer-enter-active 消费的 --fx-dur-panel 同源。
   * dock(true) 在 watch pre-flush 跑、面板还没挂载, 读不到计算样式, 故取常量;
   * 主路 transitionend 不依赖本值, 只有兜底定时器用它。 */
  var PANEL_ENTER_MS = 300;
  function dock(open, onSettled) {
    if (onSettled) settleCb = onSettled;
    if (open) {
      settleArmed = true;
      /* 武装兜底定时器(R5#179): 主路 transitionend 在 RM 过渡归零/过渡被打断/后台标签页
       * 丢事件时永不点火 —— 不武装则回执不发、fx-glide 恒驻留(键盘 End/Home/翻页一直平滑)。
       * 与下方 transitionend 双路并存, fireSettle 的 settleArmed 单发守卫保证只发一次。 */
      armSettle();
      /* S-A(2026-11-13 用户报「flux 首开种子先被面板遮挡、之后才上移」): fx-glide 不再开门
       * 即挂 —— 开门窗口(enter 起拍到面板升完)内的让位/重入滚动(openTorrentDrawer 开场 /
       * _drawerDone 兑现 / afterEnter 补发 / 落定回执重入, 四写者职责与挂点全不动)走瞬时,
       * 与抽屉上升同步(对齐 prism「种子跟着上升」手感); 平滑挂点挪到落定回执后(fireSettle)。
       * 开门即挂的旧口径下四个 scrollBy 互相重启/累加平滑爬行(实测 490ms+), 面板 300ms 就
       * 升完而行还在半路。 */
      /* 撤上一轮残局(重复触发幂等): 两个定时器句柄 + 防御性摘类 —— 重开若落在「回执→宏任务」
       * 间隙或上一轮 800ms 平滑窗口内, 挂类定时器/摘除定时器/类本身都可能还挂着, 不撤/不摘
       * 则平滑被带进本次开门窗口, S-A 症状复发。 */
      if (glideAddTimer) { clearTimeout(glideAddTimer); glideAddTimer = 0; }
      if (glideTimer) { clearTimeout(glideTimer); glideTimer = 0; }
      document.documentElement.classList.remove("fx-glide");
    } else {
      settleArmed = false;
      document.documentElement.classList.remove("fx-glide");
      if (glideAddTimer) { clearTimeout(glideAddTimer); glideAddTimer = 0; }
      if (glideTimer) { clearTimeout(glideTimer); glideTimer = 0; }
      if (settleTimer) { clearTimeout(settleTimer); settleTimer = 0; } /* 关面板不再发落定回执 */
    }
  }
  /* 面板入场落定回执(F7d 机制保留, F7e 换锚): (1)面板本体 transform 过渡的
   * transitionend 为主路; (2)兜底定时器 = 入场时长 + 100ms(RM 过渡归零不派
   * transitionend / 过渡被打断 / 后台标签页丢事件)。双路都过 settleArmed 单发
   * 守卫 -- 关面板路径的过渡结束不发(关闭不需要重入)。 */
  function armSettle() {
    if (!settleCb) return;
    if (settleTimer) clearTimeout(settleTimer);
    settleTimer = setTimeout(fireSettle, PANEL_ENTER_MS + 100);
  }
  function fireSettle() {
    if (settleTimer) { clearTimeout(settleTimer); settleTimer = 0; }
    if (!settleArmed || !settleCb) return;
    settleArmed = false;
    settleCb();
    /* S-A: fx-glide 改在落定回执后挂(原为开门即挂) —— 面板升完前让位/重入走瞬时(S-A 修复),
     * 升完后恢复平滑。挂点必须经 setTimeout 宏任务延迟, 不是可选优化: fireSettle 跑在
     * transitionend 派发的捕获阶段, 同一次派发的目标阶段还有 Vue Transition 的 onAfterEnter
     * (#3 补发入口, drawerAfterEnterHook -> _kbRevealRow), 回执重入(#4)也在本回调内同步进入
     * _kbScrollRowIntoView —— 两发的 scrollBy 都在本任务收尾后的微任务里落地。若在 fireSettle
     * 内同步挂类, 类会先于 afterEnter 监听器挂上(同步挂会赶上 afterEnter 那发), 两发全被平滑
     * 重启爬行, S-A 症状复发; 宏任务挂点把挂类推到本任务(含全部微任务)跑完之后, 两发已瞬时
     * 落地。挂/摘两个定时器都留句柄(glideAddTimer/glideTimer), dock 两分支各撤两个(幂等面)。 */
    glideAddTimer = setTimeout(function () {
      glideAddTimer = 0;  /* 已执行: 先清句柄, 免得残留旧 id 被下一次 dock 误撤(no-op 无害, 求准) */
      document.documentElement.classList.add("fx-glide");
      /* 回执后挂的平滑窗口 800ms 后摘(余量口径不变): 面板开着期间的后续键盘滚动在此窗口内
       * 平滑、之后回原版瞬时(fx-mount.css html.fx-glide 段注)。 */
      glideTimer = setTimeout(function () {
        glideTimer = 0;
        document.documentElement.classList.remove("fx-glide");
      }, 800);
    }, 0);
  }
  document.addEventListener("transitionend", function (ev) {
    if (!settleArmed || !settleCb) return;
    var t = ev.target;
    if (!t || !t.matches || !t.matches(".drawer-dock > .drawer") || ev.propertyName !== "transform") return;
    fireSettle();
  }, true);

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
  /* ---- toast 文字排版(D6-2 骨架, 用户口径 2026-11-02 四轮 / 五轮扩分隔符 + 六轮文案统一) ----
   * 共享模板只渲染一条 `<span>{{ t.text }}</span>`(四皮肤共用, 不动模板), flux 在挂载层
   * 把它读作「主标题 + 说明」两段, 与 showcase D6-2「倒计时进度条」样例同一排版语法
   * (13px/600 标题行 + 12px/--fg-muted 明细行, 图标顶对齐)。拆段规则纯结构、不猜语义:
   * 首个 `:` / `：` / `,` / `，` 之前的**动作短语**(≤14 字、不含括号)当主标题, 其后的剩余当说明。
   * 说明门槛只留 2 字 —— 六轮把生产文案统一成「主标题: 说明」(无分隔符的回执都补了说明句),
   * 说明常常就是一个名字/计数(「已执行: 重命名」「已复制: 名称已写入剪贴板」), 门槛再高会让
   * 这批条退回去单行, 与「都改成主标题+说明」的口径打架。残留单行 = 说明侧 trim 后不足 2 字
   * (分隔符后的连接空格不算进门槛), 那是数据现实, 不是样式缺口; 单行条字重由 CSS 基座统一 600, 与标题行同貌。
   * 每次 sync 都跑并按 `.toast-t` 是否存在判重: Vue 在 .text 变更时会覆写 span 子节点
   * (hostSetElementText), 标记位会骗人, 按 DOM 现状判才可靠。文本一律 textContent,
   * 不拼 innerHTML —— err.message 里可以是任意字符。 */
  var TOAST_SPLIT = /^([^:：,，()（）\n]{1,14})[:：,，]\s*([\s\S]{2,})$/;
  function shapeToastText(n) {
    var span = null;
    for (var i = 0; i < n.children.length; i++) {
      if (n.children[i].tagName === "SPAN") { span = n.children[i]; break; }
    }
    if (!span || span.querySelector(".toast-t")) return; /* 已塑形 */
    span.classList.add("toast-txt");                     /* 单行也挂: 让 flex:1 / min-width:0 生效 */
    var text = span.textContent || "";
    var m = TOAST_SPLIT.exec(text);
    if (!m || m[2].trim().length < 2) return;  /* 说明侧按 trim 后计长 —— 分隔符后的连接空格
      (口径是 ": "/", " 接说明)不算进 2 字门槛, 见 webui-fx.md 消息面文字排版(四轮)/toast 文案(六轮);
      trim 后不足 2 字 = 残留单行, 那是数据现实, 不是样式缺口(issue 26-11-08-0229 #12) */
    span.textContent = "";
    var head = document.createElement("span");
    head.className = "toast-t";
    head.textContent = m[1].trim();
    var tail = document.createElement("span");
    tail.className = "toast-s";
    tail.textContent = m[2].trim();
    span.appendChild(head);
    span.appendChild(tail);
  }
  function toastSync(ttl, id) {
    var wrap = document.querySelector(".toast-wrap");
    if (!wrap) return;
    var nodes = wrap.querySelectorAll(".toast");
    for (var i = 0; i < nodes.length; i++) {
      var n = nodes[i];
      shapeToastText(n);
      /* 本次 ttl 只属于**这一条**(data-id 精确命中); 没传 id 时退化为最新一条(栈尾) ——
       * 消费点永远传自己的 id(见下方倒计时段), 这条只是漏传时的合理兜底。 */
      var own = id != null
        ? n.getAttribute("data-id") === String(id)
        : i === nodes.length - 1;
      if (!n._fxToast) {
        n._fxToast = 1;
        n.setAttribute("data-fx", "rise");
        /* 栈里已有别的条 => 这次是「队列推入」: 新条从下方一整格进场, 与旧条上移让位同速,
         * 两条不叠画(见 fx-mount.css 的 [data-fx-queue] 规则)。首条不加 —— 单条没有让位需求。 */
        if (nodes.length > 1) n.setAttribute("data-fx-queue", "");
        /* D6-3 队列 FLIP 的身份牌: 退场包进 View Transitions 时按名配对 */
        n.style.viewTransitionName = "fx-toast-" + (++toastSeq);
        var ico = n.querySelector(".ico");
        if (ico) {
          ico.setAttribute("data-fx", "ico-spring");
          ico.setAttribute("data-fx-play", "");
        }
      }
      /* 倒计时条(D6-2)挂载/刷新 —— 只给本条, 且 ttl 与这条自己的退场定时器同源。
       * !2026-11-02 十一轮(用户报「强制重新汇报失败的窗口时间指示条到了但没消失」): 此前 stamp
       *   分支用**整栈共用**的 ttl 给所有新条挂条 —— 而 `_settleRunningToast` 在同一个 tick 里
       *   先给归档条发 4000(settle), 再推结果条(12000), 两份 $nextTick 按注册序执行, 于是
       *   4000 先落到刚渲染的结果条上: 进度条 4s 走完, 条却按 12000ms 才移除, 中间 8s 干挂。
       *   实测 t=5106ms 动画 finished、t=13013ms 节点才消失。现在 stamp 时也按 id 命中, 归档条
       *   拿 4000、结果条拿 12000, 进度条终点 = 退场时刻。
       * sticky 条建时 ttl=0(按设计不给进度条), 归档成终态/「已投递」时才拿到 TTL —— 只在挂载
       * 那一刻挂条的话, 这条会"无进度条突然消失", 与同屏新条两套观感, 故两处共用本段。
       * --fx-life 变了要摘掉标记 + 强制回流重播(改 animation-duration 不会重启已在跑的动画)。 */
      if (own && ttl > 0) {
        n.style.setProperty("--fx-life", ttl + "ms");
        if (n.hasAttribute("data-fx-cd")) {
          n.removeAttribute("data-fx-cd");
          void n.offsetWidth;
        }
        n.setAttribute("data-fx-cd", "");
      }
      if (!n._fxDanger && /\b(error|timeout)\b/.test(n.getAttribute("class") || "")) {
        n._fxDanger = 1;
        n.setAttribute("data-fx", "rise danger");
        n.setAttribute("data-fx-play", "");
      }
    }
    flipStack();
    FX.scan();
  }

  /* ---- toast 队列重排 FLIP(D6-3, 用户八轮口径 2026-11-02) ----
   * 报障: 「强制汇报的两个窗口(已投递/回执)没有统一, 且会互相重叠」——
   *   (1) 两态(等待中 / 已确认)高度不同(等待态说明折两行 76px, 回执 59px), 结算时盒子瞬间抽高,
   *      看起来像两个窗口叠了一下 —— 文案侧已压成同高一行说明(commands.js 2026-11-02 注解);
   *   (2) 队列本身没有重排动效: 新条插入/旧条退场时, 现存条**瞬移**到新位置, 与正在入场的条
   *      同帧叠着画 —— 这就是「互相重叠」的另一半。
   * 本函数按 D6-3「队列重排 FLIP」补上后半: 每次栈几何变化时, 用上一轮的布局位置给现存条
   * 反向位移(translateY)后归零, 让"让位"是滑出去的而不是跳过去的; 自身高度变化(等待态结算
   * 成终态)同理 —— 高度从旧值动到新值, 底锚定, 上沿自然跟着走, 不再两个盒子叠一下。
   * 读布局用 offsetTop/offsetHeight(相对 .toast-wrap 的布局盒), **不用** getBoundingClientRect:
   * 后者会被正在跑的 transform 污染, 连续 sync 会把位移读成 0(FLIP 失效)。
   * RM / 无 WAAPI: 只记位不动画(降级 = 无动效终态, 与 fx 库其他原语同口径)。 */
  var toastGeo = typeof WeakMap === "function" ? new WeakMap() : null;
  var toastAnim = typeof WeakMap === "function" ? new WeakMap() : null;
  function flipStack() {
    var wrap = document.querySelector(".toast-wrap");
    if (!wrap) return;
    var nodes = wrap.querySelectorAll(".toast");
    if (!nodes.length) return;
    var reduced = FX.reduced() || !nodes[0].animate;
    /* 量之前先把自己上一轮的位移动画摘掉: 读的是"纯布局位置", 否则 transform 会把
     * getBoundingClientRect 带偏, 连续 sync 时位移会被读成 0(FLIP 静默失效)。
     * 位置用**视口坐标**: 栈是底部锚定的, 新条插入时容器整体上移, 而各条在容器内的
     * offsetTop 不变(实测恒为 0) —— 只有视口坐标能看出"用户看到的位置变了"。 */
    var list = [];
    var i, n;
    for (i = 0; i < nodes.length; i++) {
      n = nodes[i];
      var running = toastAnim && toastAnim.get(n);
      if (running && running.playState !== "finished") running.cancel();
      var r = n.getBoundingClientRect();
      list.push({ n: n, top: r.top, h: r.height });
    }
    for (i = 0; i < list.length; i++) {
      var it = list[i];
      var prev = toastGeo && toastGeo.get(it.n);
      if (toastGeo) toastGeo.set(it.n, { top: it.top, h: it.h });
      if (!prev || reduced || it.n.hasAttribute("data-fx-exit")) continue;
      var dh = it.h - prev.h;
      var dy = prev.top - it.top;      /* >0 = 这一轮它上移了 */
      if (Math.abs(dh) < 1 && Math.abs(dy) < 1) continue;
      /* 高度变了 = 这条自己换内容(等待态结算成终态): 只补高度, 位置由底锚定自然带出来;
       * 否则是邻居进出: 补位移。两者都从"上一轮的样子"过渡到"现在的样子"。 */
      var frames = Math.abs(dh) >= 1
        ? [{ height: prev.h + "px" }, { height: it.h + "px" }]
        : [{ transform: "translateY(" + dy + "px)" }, { transform: "translateY(0)" }];
      var anim = it.n.animate(frames, { duration: 200, easing: "cubic-bezier(.2,.8,.3,1)" });
      if (toastAnim) toastAnim.set(it.n, anim);
    }
  }

  /* ---- toast 退场(D6-1 退场半 + D6-3 队列重排 FLIP) ----
   * 消费点 = ui_feedback.js::_dropToast。View Transitions 可用且非 RM: 数组更新包进
   * startViewTransition -- 被移除条按 view-transition-name 快照走默认退场(fade),
   * 存活条同名新旧配对 = FLIP 重排; 不支持/RM: 提交后由 flipStack 补位移动画。 */
  function toastDrop(commit) {
    if (FX.reduced() || !document.startViewTransition) {
      commit();
      /* commit 只改数组, DOM 要等 Vue nextTick 才落地 —— 本帧 rAF 里量才是"删掉之后"的布局 */
      requestAnimationFrame(function () { flipStack(); });
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
