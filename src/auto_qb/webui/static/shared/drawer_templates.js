/* auto-qb WEB UI · 种子详情面板模板核心层(计划 26-10-06-0838 S1; W7 恢复版)
 *
 * !2026-10-14(用户令「移除种子详情面板除流量页外的 4 个经典 UI, 以及流量页/qB 流量页的除经典
 * 外的 UI」): 本层是全仓「经典 / 变体」两档制的**唯一判据点** —— 四内容页签经典渲染链
 * (drawer_tabs.js 四组件 + tpl/drawer-tabs.html + 三个经典单元格渲染器 + 经典表注册/排序字段/
 * 行装配方法)已整体删除, 流量变体 13/14/15 亦已删除。终态: 四内容页签变体独档(缺省 = 首个
 * 变体), 流量页签经典独档。CLASSIC_TABS / defaultSel / choices 三处即该口径的单点。
 *
 * !W7(计划 26-10-11-2106)恢复注(历史): W5/W6 曾退役本文件与 15 个变体(改声明式密度档) —— 用户
 * 裁定**越权**(计划目标只是「表格与主表能力统一」= W2 接壳, 从未授权动模板), 本文件与
 * drawer_tpl/ 全体按 W4 期形态原样恢复。相对 a05d35da 基座的三处适配(均为 W2-W4 已定案):
 *   ① 合并机械住 drawer.js(W4 收口), 本层只经 window.AQB_DRAWER_MERGE.pairOf 消费对结构;
 *   ② 00-core 注入只余变体专属的 .dt-tpl 限宽规则(合并/菜单/流量布局规则 W6 起在
 *      三皮肤 views/components.css, 单一来源, 此处不重复注入);
 *   ③ dtMenuPick 落盘后 $nextTick 再 _dtSync(换变体要重建宿主子树, 同拍挂载会撞上未提交的渲染)。
 *
 * 注册表 + 宿主生命周期 + dtHtml 转义标签模板 + CSS 注入单点 + autoqb.ui.drawerTpl 读写
 * + 变体公共骨架 helpers(reg.helpers: 工具/sig 比对/滚动自保/事件挂摘, 报告 26-10-07-0845;
 *   行级键盘 roving tabindex 四件套, issue 26-10-07-0846)。本文件是「核心层」: 不含任何具体模板变体 —— 变体是
 * shared/drawer_tpl/<NN>-<tab>-<slug>.js 一个自注册文件, 删除 = 删文件 + 三份 manifest 各去 1 行。
 *
 * 装载序: 必须排在 drawer.js 之后、state.js 之前(三份 index.html 的 tpl-manifest)。
 *   - 在 drawer.js 之后没有强约束(钩子经 this. 调用, 运行时才求值), 放同域便于阅读;
 *   - 在 state.js 之前是硬约束: state.js 的 data() 调 initialDrawerTpl()(app.js), 其白名单
 *     校验依赖注册表 —— 变体文件(自注册)也必须全部排在 state.js 之前, 否则已存的合法 id
 *     会被当成脏值回落该页签缺省档(静默, 不报错)。
 *
 * ---------------- ctx 白名单契约(变体只许读/调下列成员) ----------------
 * 变体 render(host, ctx) 的 ctx 就是根组件实例(Vue mixin 方法域全在 this 上)。白名单面:
 *   读(状态): ctx.drawer.detail / .trackers / .files / .peers 及各 *Loading 态 / .error /
 *             各列表失败标记 trackersError / filesError / peersError(P3-5, 报告 26-10-07-0542:
 *             fetch 型变体据此区分「失败」与「真没有」) / .hash / .tab; ctx.qbCurData /
 *             qbCurPoints / qbCurSummary / qbCurWindow / qbCurError / qbCurPending(流量三域);
 *             ctx.memberByHash; ctx.flags(渐进字段门控)。
 *   调(格式化): fmtSpeed / fmtSpeedOrDash / fmtSize / fmtSizeOrDash / fmtDuration / fmtEta /
 *             fmtTs / fmtPeersQb / drawerFileRows / drawerPeerRows / drawerTrackerStatus /
 *             drawerTrackerVirtual / drawerGeneralSections / drawerTitle / icoTone /
 *             hrStateLine / hrSiteLine。
 *   调(动作):   drawerCmd(action[, body, okText]) / trackerAdd / trackerRemove /
 *             setFilePriority / openFilePrio / openTargetPath / copyText / qbSetWindow;
 *             需要详情原始字段(如 magnet_uri)时走 _editDetail(hash)(按需单发, 不进轮询载荷)。
 *   禁: 不触碰面板几何(dock/动画/高度/drawerPanelStyle)、轮询生命周期(_startDrawerPoll 族)、
 *       路由/视图状态; 不直接发请求(动作一律走现有方法链, 回执/toast 由其自带)。
 *   DOM: host 子树归变体自管, Vue 零感知(模板只渲染空 host 元素, 显隐只走 host 自身 v-show)。
 *        变体内禁止 innerHTML 裸拼 —— 一律走 dtHtml 标签模板(插值自动转义, dtRaw 显式豁免);
 *        每次重建用 replaceChildren 原子换帧, 自保滚动位置与内部 UI 态(折叠/筛选/选中)。
 *
 * ---------------- CSS 令牌白名单(S1 对账, plan §05 ①) ----------------
 * 变体 CSS 只允许引用下列令牌(已对 atlas / console / prism 三皮肤逐一核实同名存在;
 * prism 的颜色令牌在 css/themes/*.css 五主题内逐一核实, 结构令牌在 css/tokens.css)。
 * 未入名单的一律写字面值或 var(--x, <字面 fallback>)。对账脚本口径: 提取各皮肤
 * `--` 自定义属性名集合求交(2026-10-06 实测):
 *   表面: --bg --bg-card --bg-row --bg-hover --bg-sunken --bg-elev --glass
 *   前景: --fg --fg-muted --fg-dim --fg-soft
 *   语义: --accent --accent-hi --accent-soft --accent-line --green --green-soft --green-line
 *         --blue --blue-soft --warn --warn-soft --warn-line --error --error-soft --error-line
 *         --paused --paused-soft --paused-line --hr-pending --hr-pending-soft --hr-pending-line
 *         --hr-done --hr-done-soft --hr-done-line --today-up --today-down --sel-bg --ring
 *   描边: --border --border-strong --border-soft --surface-1 --surface-2 --hairline
 *   几何: --radius-lg --radius --radius-sm --ease --ease-out --dur --dur-fast --dur-slow
 *         --shadow-1 --shadow-2 --shadow-3 --font-mono
 * (atlas 的 --font-ui / --font-display 不存在, 变体要写字体时用字面栈或 var(--font-ui, <字面>))。
 *
 * S6 接入说明(计划 26-10-06-0838): traffic 形态(三挂点)不走 _loadDrawerTab, 流量取数单点
 * _qbLoad 在 qb_traffic_chart.js(本计划零改动面, 不能像四 fetcher 那样在落袋处插一行通知)
 * —— 落袋通知改由根实例 mounted 后 $watch(qbCurData) 覆盖同一时机(不写成 watch 选项: 全局
 * mixin 会波及 <transition> 的 BaseTransition 假实例, 实测 getter 求值即抛, 见 methods 前注);
 * 数据落袋 = qbCurData 引用替换(过期响应不落袋不触发, 与四 fetcher 的 stale 纪律天然同构);
 * _dtNotify 对「宿主已被拆」的情况卸旧重挂(流量正文块的 v-if 加载/错误/空态分支会拆装宿主,
 * 与四页签恒在宿主不同)。
 */
(function () {
  "use strict";

  var TABS = ["general", "trackers", "peers", "content", "traffic"];
  var STORE_KEY = "autoqb.ui.drawerTpl";
  var CLASSIC = "classic";
  /* ---------------- 「经典」档只存在于流量页签(2026-10-14 用户令) ----------------
   * 移除种子详情面板除「流量」页外的 4 个经典 UI(常规/Tracker/用户/内容 —— 即 drawer_tabs.js
   * 那四个 Vue 组件, 连同其模板/单元格渲染器/表注册一并删除), 同时移除「流量」页与 qB 流量页
   * 的变体(13/14/15)。终态:
   *   ·四内容页签 = **变体独档**(菜单无「经典」, 缺省与渲染失败回落都落该页签首个变体);
   *   ·流量页签(含 qB 全局/分组挂点) = **经典独档**(无变体可选, 模板菜单随之无内容不弹)。
   * 本常量是「哪些页签还有经典渲染」的单点判据(有经典才有「经典」候选与 classic 缺省)。 */
  var CLASSIC_TABS = ["traffic"];
  /* ---------------- 页签合并(W4 起住 drawer.js; W7 恢复注) ----------------
   * 合并四判据(dtMergeOn/dtMergeTabsOn/dtPair/dtSplitOn)/四方法/两条监听/常量已整体收进
   * drawer.js(AQB_DRAWER_MERGE 跨文件单点), 本层只经 window.AQB_DRAWER_MERGE.pairOf 消费
   * 对结构(_dtMountSplit) —— 插件层不得自建第二份映射(双份判据即 R2 空列 bug 的根)。 */

  /* ---------------- CSS 注入单点: <style data-dt="..."> ----------------
   * 变体 CSS 在 register 时注入(id 即 data-dt 值), 核心基础样式用 "00-core"。
   * 规则一律挂在 .drawer 作用域下 —— 不污染面板外, 三皮肤 CSS 文件零改动。 */
  function dtInjectCss(id, css) {
    if (typeof document === "undefined") return; /* node 单测探针环境无 DOM: 跳过注入 */
    var el = document.querySelector('style[data-dt="' + id + '"]');
    if (el) {
      el.textContent = css;
      return;
    }
    el = document.createElement("style");
    el.setAttribute("data-dt", id);
    el.textContent = css;
    document.head.appendChild(el);
  }

  /* ---------------- dtHtml: 转义标签模板(dtRaw 显式豁免) ----------------
   * XSS 单点收口(对齐 F1/F2 审计口径): 变体禁止 innerHTML 裸拼, 一律
   *   dtHtml`<b>${name}</b>`          插值自动转义
   *   dtHtml`${dtRaw(预转义好的html)}` 显式豁免(传已转义/可信 HTML)
   * 守阵 grep 变体文件裸 innerHTML。 */
  function esc(v) {
    return String(v === null || v === undefined ? "" : v)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;").replace(/'/g, "&#39;");
  }
  function dtRaw(html) {
    return { __dtRaw: true, html: String(html) };
  }
  /* 属性选择器值转义(path 可能含引号/反斜杠, 概率极低但必须成对转义保底) */
  function cssAttrEsc(s) {
    return String(s).replace(/\\/g, "\\\\").replace(/"/g, '\\"');
  }
  function dtHtml(strings) {
    var out = "";
    for (var i = 0; i < strings.length; i++) {
      out += strings[i];
      if (i + 1 < arguments.length) {
        var v = arguments[i + 1];
        if (v && v.__dtRaw) out += v.html;
        else if (Array.isArray(v)) out += v.map(esc).join("");
        else out += esc(v);
      }
    }
    return out;
  }

  /* ---------------- 变体公共骨架 helpers(reg.helpers, 报告 26-10-07-0845) ----------------
   * 01-12 十二份变体各自复刻的四类骨架代码收口成单点, 变体经 reg.helpers 消费:
   *   - dur/size/present/num: 格式化小工具(dur 缺失/负值回退文案; size 空值补 —;
   *     num = Number(v)||0 —— 注意 04/05/06 里的同名 num 是「非负谓词」语义, 属另一函数不共用);
   *   - skipUnchanged: sig 比对跳过重建(序列化比对, 宿主非空才跳; 变了先记账再放行);
   *   - withScroll: 滚动位置自保(滚动容器是宿主父级 .drawer-body, Vue 所有 —— 原子换帧前后
   *     纵横两轴成对恢复, 恢复次序 scrollLeft 先 scrollTop 后);
   *   - wireEvents/unwireEvents: 事件委托挂摘成对(宿主元素跨变体复用, 换变体必须摘掉旧监听,
   *     否则新旧变体监听叠加、同一次点击被多个 handler 重复处理)。挂摘都记账在同一张
   *     host.__dtEvents 事件表上, 成对纪律由实现保证, 变体不再各自维护 __dtNNWired 标志;
   *   - roving/rowFocusKey/rowRestore/rowMove: 行级键盘 roving tabindex(issue 26-10-07-0846,
   *     content 组 dt10/11/12 消费) —— 锚点设置/焦点记账/重建回焦/方向键移焦四步。 */
  var HELPERS = {
    dur: function (ctx, v, dash) {
      return (v === null || v === undefined || v < 0) ? (dash || "未设") : ctx.fmtDuration(v);
    },
    size: function (ctx, v) { return ctx.fmtSizeOrDash(v) || "—"; },
    present: function (v) { return v !== undefined && v !== null && v !== ""; },
    num: function (v) { return Number(v) || 0; },
    skipUnchanged: function (host, ui, sig) {
      if (sig === ui.lastSig && host.firstChild) return true;
      ui.lastSig = sig;
      return false;
    },
    withScroll: function (host, swap) {
      var sc = host ? host.parentElement : null;
      var top = sc ? sc.scrollTop : 0;
      var left = sc ? sc.scrollLeft : 0;
      swap();
      if (sc) {
        sc.scrollLeft = left;
        sc.scrollTop = top;
      }
    },
    /* ---------------- 数据拍原地回填(计划 26-10-12 用户报障: 模板表格每 5s 闪) ----------------
     * 病根(80 对端实测): 变体 render 的 sig 含整包列表数据 ⇒ 5s 轮询每拍必整帧重建
     * (replaceChildren + anchFill 把锚换进新 slot = **锚移动**)。锚里 Teleport 着整张表,
     * 锚移动 = 表格整树重排 —— 实测每拍 56-75ms longtask(经典表同数据量 0ms), 浏览器
     * 卡顿近 5 帧, 用户观感即"表格每 5s 闪一下, 数据只随闪刷新"(经典表走纯 Vue 补丁故丝滑)。
     * 正解: sig 只含**结构态**(加载/失败/空态/分组成员/UI 态), 数据拍不重建外壳 ——
     * 行走桥自身响应式(drawer.peers 更替 → 根重渲染 → 行原地补丁), 壳上数据依赖值
     * (卡值/chips 计数/组头聚合)由各变体把同一构建器的产出 paintHtml 进**不含锚**的
     * 子树(卡区/筛选条/工具条), 列表区(锚+表)自始至终不动 ⇒ 无重排无闪。
     * sel 命中不到(首帧/空态/结构刚变)时静默跳过 —— 调用方靠结构 sig 保证只在整帧态进场。
     * innerHTML 相同则跳过写(内容没变的拍零 DOM 操作)。 */
    paintHtml: function (host, sel, html) {
      var el = host ? host.querySelector(sel) : null;
      if (el && el.innerHTML !== html) el.innerHTML = html;
    },
    wireEvents: function (host, map) {
      if (!host || host.__dtEvents) return;
      host.__dtEvents = map;
      for (var k in map) host.addEventListener(k, map[k]);
    },
    unwireEvents: function (host) {
      if (!host || !host.__dtEvents) return;
      for (var k in host.__dtEvents) host.removeEventListener(k, host.__dtEvents[k]);
      host.__dtEvents = null;
    },
    /* ---- 行级键盘 roving tabindex(issue 26-10-07-0846, content 组 dt10/11/12 消费) ----
     * 行/块容器 tabindex="-1" 不进 Tab 序(行内原生控件自然参与 Tab), 锚点(选中行或首行)
     * 由 roving() 在整帧重建后设为 0; 方向键/Home/End 由变体 keydown 委托调 rowMove() 移焦;
     * Enter/Space 由变体转发为行激活。原子换帧会打断焦点链 —— rowFocusKey() 在重建前记账
     * 焦点行、rowRestore() 重建后回焦, 否则一次激活就把键盘用户甩回文档头。
     * 整行不加 role="button": 行内已含原生控件(button/checkbox), 嵌套交互语义反而更糟
     * (入池报告根因段口径) —— 键盘可达靠 tabindex + 委托, 读屏语义靠行内控件自身。 */
    roving: function (host, attr, selKey) {
      if (!host) return;
      var rows = host.querySelectorAll("[" + attr + "]");
      var anchor = null;
      for (var i = 0; i < rows.length; i++) {
        rows[i].tabIndex = -1;
        if (!anchor && selKey && rows[i].getAttribute(attr) === selKey) anchor = rows[i];
      }
      if (!anchor && rows.length) anchor = rows[0];
      if (anchor) anchor.tabIndex = 0;
    },
    /* 焦点行 key 记账: 焦点落在行容器或其内部任一元素上都算; 不在 host 内返回 "" */
    rowFocusKey: function (host, attr) {
      var el = typeof document === "undefined" ? null : document.activeElement;
      if (!host || !el || !host.contains(el)) return "";
      var row = el.closest("[" + attr + "]");
      return row ? (row.getAttribute(attr) || "") : "";
    },
    /* 重建后回焦: 记账 key 命中才回, 且回焦行本身可聚焦(tabindex=-1 也可程序聚焦) */
    rowRestore: function (host, attr, key) {
      if (!host || !key) return;
      var row = host.querySelector("[" + attr + '="' + cssAttrEsc(key) + '"]');
      if (row) row.focus();
    },
    /* 方向键移焦: key 为 KeyboardEvent.key(ArrowUp/Down/Left/Right/Home/End), 移了返回 true */
    rowMove: function (host, attr, el, key) {
      var rows = host.querySelectorAll("[" + attr + "]");
      var row = el && el.closest ? el.closest("[" + attr + "]") : null;
      if (!row || !rows.length) return false;
      var i = Array.prototype.indexOf.call(rows, row);
      var next = -1;
      if (key === "ArrowDown" || key === "ArrowRight") next = i + 1;
      else if (key === "ArrowUp" || key === "ArrowLeft") next = i - 1;
      else if (key === "Home") next = 0;
      else if (key === "End") next = rows.length - 1;
      if (next < 0 || next >= rows.length) return false;
      rows[next].focus();
      return true;
    },
    /* ---------------- 桥锚保活/触碰(U2, 计划 26-10-12-0527; 与模块函数 dtSyncAnchors 同族) ----------------
     * anchFill: 桥变体外壳整帧重建时**保住锚元素身份** —— 帧内表格区放
     *   `<div data-dt-anchor-slot="<segKey>"></div>`(单锚段 key 留空), 重建后由本 helper 把
     *   宿主记账的锚元素(首次则新建)替换进 slot 位。锚元素不换 = dtSyncAnchors 不换代 =
     *   桥零重挂(行更新走引擎响应式; stub 的"恒定 sig 锚不重建"不变量在真实变体上的等价物:
     *   锚被重建 = Teleport 重挂 = 行抖动 + .group-table 横滚位丢失)。段离场(组空/过滤)时
     *   记账丢弃, 再现即换新锚(代数自增)。
     * anchTouch: 变体 UI 态(筛选/只看在传)变化后的强制换代 —— 锚元素身份没变但 rowsFn 的
     *   读数(ui.filter 等, 非响应式)变了, 引擎无从感知; 对在场锚自增一代, 桥重挂重读行装配。
     *   锚全部离场的态翻转(如过滤后无组)由 dtSyncAnchors 对账摘 on, 不在这里硬点。 */
    anchFill: function (host, tableId) {
      if (!host || typeof host.querySelectorAll !== "function") return;
      var slots = host.querySelectorAll("[data-dt-anchor-slot]");
      var book = host.__dtAnchorKeep || (host.__dtAnchorKeep = {});
      var keep = {};
      for (var i = 0; i < slots.length; i++) {
        var seg = slots[i].getAttribute("data-dt-anchor-slot") || "";
        var key = tableId + "#" + seg;
        var el = book[key];
        if (!el) {
          el = document.createElement("div");
          el.setAttribute("data-dt-table-anchor", tableId);
          if (seg) el.setAttribute("data-dt-seg", seg);
        }
        slots[i].replaceWith(el);
        /* 驻留态复位(dtHoldAnchors 持有期间置了 display:none): 归位即可见。
         * 只在真被置过时写 —— 稳定路径(锚从未离场)零样式操作。 */
        if (el.style && el.style.display === "none") el.style.display = "";
        keep[key] = el;
      }
      host.__dtAnchorKeep = keep;
    },
    anchTouch: function (host, vm, tableId) {
      dtSyncAnchors(host, vm); /* 先按在场元素对账(锚离场的态翻转在这里摘 on) */
      var cur = vm && vm.dtBridge ? vm.dtBridge[tableId] : null;
      if (cur && cur.on) vm.dtBridge[tableId] = { gen: cur.gen + 1, on: true };
    },
    /* ---------------- 三态空帧(issue 26-10-20-2231) ----------------
     * 04-12 九件桥变体各手抄一份「加载态(沙漏)/ 错态(警告 + err 原文 title)/ 空态
     * (纯文案) + 整帧替换」—— 27 块除槽类名与文案外逐字同(入池报告 R21-B)。general
     * 三件的裸空态(无槽无文案 + lastSig 复位记账)形状不同, 刻意不入本 helper。
     * 调用方已从 ctx 取好 loading/err 与数据长度; 本 helper 只认开关: has = 有数据
     * (直接返 false, 调用方继续走整帧); 否则按 loading → err → empty 优先级渲对应
     * 空帧并返 true(调用方直接 return) —— 与原三块 if 的判定序和 !length 合并语义
     * 逐位对齐。err 进 title 经 esc(与 dtHtml 插值同口径 —— API 错误文案可能带引号),
     * 静态文案同样过 esc(与 KIT 同口径)。 */
    emptyFrame: function (host, o) {
      if (o.has) return false; /* 有数据: 不是空帧, 调用方继续整帧 */
      var inner;
      if (o.loading) {
        inner = '<svg class="ico" viewBox="0 0 16 16"><use href="#i-hourglass"></use></svg><span>正在加载…</span>';
      } else if (o.err) {
        inner = '<svg class="ico" viewBox="0 0 16 16"><use href="#i-warn"></use></svg>' +
          '<span title="' + esc(o.err) + '">' + esc(o.errText) + "</span>";
      } else {
        inner = "<span>" + esc(o.emptyText) + "</span>";
      }
      host.replaceChildren(document.createRange().createContextualFragment(
        '<div class="' + o.cls + '">' + inner + "</div>"));
      return true;
    },
  };

  /* ---------------- 部件工具箱(reg.kit, R2 S1 计划 26-10-09-2219) ----------------
   * 经典链移植为页插件后的共享构建器单点: 三态外壳 + 表格骨架。classic 四件全走这里,
   * 变体可选迁移(本轮不强制, 渐进收敛); 产出 HTML 字符串, 文本一律经 esc 转义,
   * 调用方再用 dtHtml 拼接插值。DOM 结构与原 Vue 经典链逐类名一致(移植不重写)。 */
  var KIT = {
    loading: function (text) {
      return '<div class="empty"><span>' + esc(text || "正在加载…") + "</span></div>";
    },
    empty: function (text) {
      return '<div class="empty"><span>' + esc(text || "暂无数据") + "</span></div>";
    },
    error: function (text) {
      return '<div class="empty"><svg class="ico" viewBox="0 0 16 16"><use href="#i-warn"></use></svg><span>' +
        esc(text || "加载失败") + "</span></div>";
    },
    /* 表格骨架: headers = 字符串或 {label, num, cls}; rowsHtml = 预构建的 tbody 内联 HTML(调用方转义) */
    table: function (headers, rowsHtml) {
      var ths = headers.map(function (h) {
        var label = typeof h === "string" ? h : h.label;
        var cls = [];
        if (h && h.num) cls.push("num");
        if (h && h.cls) cls.push(h.cls);
        return "<th" + (cls.length ? ' class="' + cls.join(" ") + '"' : "") + ">" + esc(label) + "</th>";
      }).join("");
      return '<table class="drawer-table"><thead><tr>' + ths + "</tr></thead><tbody>" + (rowsHtml || "") + "</tbody></table>";
    },
  };

  /* ---------------- peers 判据共用模块(reg.peers, issue 26-10-20-2231) ----------------
   * 07/08/09 三件 peers 变体各手抄一份的判据簇: FLAG_META(flags 徽章表) / flagTokens
   * (bucketOf 的依赖) / isBad(吸血启发式) / bucketOf(flags 方向分桶) / isLanIp(内网
   * 判定) —— 程序化 diff 三份逐字同(入池报告 R21-C)。漂移代价: 判据只改一份 ⇒ 同一
   * peer 在三个版式下分桶不同(吸血名单/内网口径各说各话)。提为单点, 三变体经同一
   * reg 消费。变体私有不入本模块: BUCKETS(方向桶配色, 07 独有) / FILTERS(筛选档,
   * 07 比 09 多 hand 档) / flagHas·clientName·countsOf(07 独有封装)。 */
  var PEERS = {
    /* qB peer_info 标志位逐项解释(设计稿同款; 色映射按 S1 白名单就近取) */
    FLAG_META: {
      D: { c: "fl-d", t: "D — 我方正在从该 peer 下载数据" },
      U: { c: "fl-u", t: "U — 我方正在向该 peer 上传数据" },
      u: { c: "fl-uo", t: "u — 对方有意向我下载, 但我方已将其限流(choked)" },
      K: { c: "fl-k", t: "K — 完整副本(对方是做种者)" },
      E: { c: "fl-e", t: "E — 加密连接" },
      H: { c: "fl-h", t: "H — 该 peer 经 DHT 引入" },
      X: { c: "fl-x", t: "X — 该 peer 经 PEX(对端交换)引入" },
      I: { c: "fl-i", t: "I — 对方主动连入(incoming)" },
      P: { c: "fl-p", t: "P — uTP 传输" },
      "?": { c: "fl-q", t: "? — 握手未完成, 状态未知" },
    },
    flagTokens: function (p) {
      return String(p.flags || "").split(/\s+/).filter(Boolean);
    },
    /* 吸血嫌疑启发式: client 名含 "XL/迅雷", 纯展示 */
    isBad: function (p) {
      var c = String(p.client || "");
      return c.indexOf("迅雷") >= 0 || /(^|[^A-Za-z])XL([^A-Za-z]|$)/.test(c);
    },
    /* 方向五桶(与变体 BUCKETS 展示配置同键): U=我方向其上传 D=对端向我供数
     * u=被我方限流 ?/空=握手未完成, 其余(含 K 完整副本)=闲置 */
    bucketOf: function (p) {
      var f = PEERS.flagTokens(p);
      if (!f.length || f.indexOf("?") >= 0) return "hand";
      if (f.indexOf("u") >= 0) return "choke";
      if (f.indexOf("U") >= 0) return "take";
      if (f.indexOf("D") >= 0) return "feed";
      return "idle";
    },
    isLanIp: function (ip) {
      var s = String(ip || "");
      if (s.indexOf(":") >= 0) return /^fe80:/i.test(s) || s === "::1";
      var m = /^(\d+)\.(\d+)\.(\d+)\.(\d+)/.exec(s);
      if (!m) return false;
      var a = +m[1], b = +m[2];
      return a === 10 || a === 127 || (a === 192 && b === 168) || (a === 172 && b >= 16 && b <= 31);
    },
  };

  /* ---------------- 注册表(变体文件直接消费的单例, 不走 app.mixin) ----------------
   * !书写形态约定(pitfalls web-ui/frontend-split): 赋值右侧不写对象字面量,
   * 否则接线守阵会把它当漏注入的 mixin。 */
  var TPL_BY_TAB = {}; /* tab -> Map(id -> entry) */
  function tabMap(tab) {
    if (!TPL_BY_TAB[tab]) TPL_BY_TAB[tab] = new Map();
    return TPL_BY_TAB[tab];
  }
  var TPL_REG = {
    tabs: TABS.slice(),
    dtHtml: dtHtml,
    dtRaw: dtRaw,
    helpers: HELPERS,
    kit: KIT,
    peers: PEERS,
    /* 变体自注册入口: (id, tab) 唯一, tab 必须是五页签之一; id 只收 [A-Za-z0-9_-]
     * (要进 data-dt 属性与 CSS 选择器)。非法/重复 fail-fast 抛错 —— 变体半残比静默好。 */
    register: function (entry) {
      if (!entry || typeof entry !== "object") throw new Error("[dt] register: entry required");
      var id = String(entry.id || "");
      var tab = String(entry.tab || "");
      if (TABS.indexOf(tab) < 0) throw new Error("[dt] register: bad tab " + tab);
      if (!id || /[^A-Za-z0-9_-]/.test(id)) throw new Error("[dt] register: bad id " + id);
      if (typeof entry.render !== "function") throw new Error("[dt] register: render required (id " + id + ")");
      var m = tabMap(tab);
      if (m.has(id)) throw new Error("[dt] register: duplicate (id, tab) = (" + id + ", " + tab + ")");
      /* 变体表格体桥声明(计划 26-10-12-0527 D1): tableId = DRAWER_TABLE_DEFS 键 —— 变体声明
       * 了 tableId 即表示其表格体走引擎(dtHtml 只出锚, 行/表壳由 drawer.html 的 Teleport 渲染);
       * 缺省 ""(外壳自管表格, 现状)。字符集与 id 同纪律(要进选择器与锚属性)。 */
      var tableId = String(entry.tableId || "");
      if (tableId && /[^A-Za-z0-9_-]/.test(tableId)) throw new Error("[dt] register: bad tableId " + tableId);
      m.set(id, {
        id: id, tab: tab,
        label: String(entry.label || id),
        tableId: tableId,
        /* 变体行装配(U2): 桥描述符 rows: "dtTplRows" → 根方法按本条目回调 —— 行来源与筛选
         * 是版式语义(过滤 chips/只看在传/五区分桶), 单点回变体文件; 排序仍由引擎 sortedDrawer
         * 做。声明了 tableId 却无 rowsFn 的变体行恒空(守阵钉"桥变体必须配 rowsFn")。 */
        rowsFn: typeof entry.rowsFn === "function" ? entry.rowsFn : null,
        /* U4 行级键盘面(issue 26-10-07-0846, content 树表 10/11): 锚每次换代重挂后的
         * 行级键盘恢复回调(roving 锚点/rowRestore 回焦) —— 与 rowsFn 同法经根方法
         * dtRowAfter 回调(描述符 rowAfter 声明位), 变体闭包不外泄。 */
        rowAfterFn: typeof entry.rowAfterFn === "function" ? entry.rowAfterFn : null,
        render: entry.render,
        notify: typeof entry.notify === "function" ? entry.notify : null,
        destroy: typeof entry.destroy === "function" ? entry.destroy : null,
      });
      if (entry.css) dtInjectCss(id, String(entry.css));
    },
    has: function (tab, id) {
      var m = TPL_BY_TAB[tab];
      return !!(m && m.has(id));
    },
    get: function (tab, id) {
      var m = TPL_BY_TAB[tab];
      return m ? (m.get(id) || null) : null;
    },
    /* 切换器选项(不含 classic, classic 由模板端恒置首位; W2 起 classic = Vue 组件非注册表条目) */
    options: function (tab) {
      var m = TPL_BY_TAB[tab];
      if (!m) return [];
      var out = [];
      m.forEach(function (e) {
        if (e.id === CLASSIC) return; /* classic 恒由模板端置首位, 不进选项集 */
        out.push({ id: e.id, label: e.label });
      });
      return out;
    },
    /* 该页签是否仍有经典渲染(只有流量页签为真, 见 CLASSIC_TABS) */
    hasClassic: function (tab) {
      return CLASSIC_TABS.indexOf(tab) >= 0;
    },
    /* 该页签的缺省档: 有经典 → classic; 无经典(四内容页签) → **首个注册变体**
     * (注册序 = manifest 装载序 = 设计稿编号序)。无变体可落时回 classic 兜底。 */
    defaultSel: function (tab) {
      if (CLASSIC_TABS.indexOf(tab) >= 0) return CLASSIC;
      var m = TPL_BY_TAB[tab];
      if (m && m.size) return m.keys().next().value;
      return CLASSIC;
    },
    /* 模板菜单候选(经典在首位 + 变体注册序)。长度 < 2 = 该页签没有可挑的档
     * (流量页签移除变体后只剩经典一档) —— openDrawerMenu 据此不弹菜单。 */
    choices: function (tab) {
      var out = [];
      if (CLASSIC_TABS.indexOf(tab) >= 0) out.push({ id: CLASSIC, label: "经典" });
      return out.concat(TPL_REG.options(tab));
    },
    /* localStorage autoqb.ui.drawerTpl 读侧(initialDrawerTpl 的实现, app.js 薄封装):
     * 按页签记 id, 白名单校验 —— 脏值/缺失/坏 JSON/读失败一律回**该页签缺省档**(defaultSel:
     * 四内容页签 = 首个变体, 流量页签 = classic; P-01 升级零观感差异语义不变)。
     * 与 initialDrawerTab 同口径: 不信任存储内容。旧存值(四页签的 "classic"、流量页签的
     * 13/14/15)在此自然失效回落缺省档 —— 无需迁移脚本。 */
    readSel: function () {
      var out = {};
      for (var i = 0; i < TABS.length; i++) out[TABS[i]] = TPL_REG.defaultSel(TABS[i]);
      try {
        var raw = JSON.parse(localStorage.getItem(STORE_KEY) || "{}");
        if (raw && typeof raw === "object") {
          for (var j = 0; j < TABS.length; j++) {
            var tab = TABS[j];
            var id = raw[tab];
            if (typeof id === "string" && id !== CLASSIC && TPL_REG.has(tab, id)) out[tab] = id;
          }
        }
      } catch (e) { /* 无存储/坏 JSON/隐私模式: 保持全缺省档 */ }
      return out;
    },
  };
  window.AQB_DRAWER_TPL_REG = TPL_REG;

  /* ---------------- 核心基础样式(变体专属限宽) ----------------
   * W7 恢复注: 合并双列/列头/菜单置灰/流量布局/.dt-host:empty 等共用规则 W6 起在
   * 三皮肤 views.css/components.css(单一来源), 此处**不重复注入**; 本注入只余变体挂载态
   * 专属的 .dt-tpl 限宽 —— Q1(报告 26-10-07-0542 §2)病根收口: 四页签变体宿主统一限宽居中,
   * 4K 下键值栅格/英雄行/多列卡片不再等分拉伸到视口宽; 窄视口(内容宽 <= 1400px)零变化。
   * traffic 双宿主不限宽: 图本体归 Vue 恒满宽, 13/15 的 KPI 头行限宽会与下方图缘错位,
   * 14 的解读栏自带 288px 固定右栏无拉伸问题。R2 S1: 限宽只挂 .dt-tpl(变体挂载态) ——
   * 经典链历史上恒满宽, 限宽误伤即行为回归; 核心挂载时按 entry 加/摘类。 */
  dtInjectCss("00-core", [
    ".drawer .dt-host.dt-tpl[data-dt-host=\"general\"], .drawer .dt-host.dt-tpl[data-dt-host=\"trackers\"],",
    "  .drawer .dt-host.dt-tpl[data-dt-host=\"peers\"], .drawer .dt-host.dt-tpl[data-dt-host=\"content\"]",
    "  { max-width: 1400px; margin-left:auto; margin-right:auto; }",
  ].join("\n"));

  /* ---------------- 桥锚对账(计划 26-10-12-0527 U2 收口单点) ----------------
   * U1 的锚代数账记在 _dtMountOne(只看挂载一拍); U2 起真实变体的外壳随数据轮询整帧重建,
   * 锚的生死/换代散落在三条路径上, 收口成一个模块函数, 三处消费:
   *   ·_dtRender 成功后(挂载 + 每次数据通知) —— 对账: 锚在场且元素没换 = 不动(桥零重挂,
   *     行更新走引擎自身响应式); 锚新出现/被外壳重建 = gen 单调自增; 锚全部离场(空态) = 摘 on。
   *   ·_dtRender 的回落 catch(变体渲染抛错清宿主后) —— 同一次对账把 on 摘干净(否则桥 teleport
   *     悬在已消失的锚上)。
   *   ·H.anchTouch(变体 UI 态变化: 筛选 chips/只看在传 —— 锚元素身份没变但行来源变了, 引擎
   *     无感知) —— 先对账再对在场 tid 强制自增一代, 桥重挂后 rowsFn 重读变体行装配。
   * !判据是**按 (tid, seg) 映射的元素身份**, 不是位置数组(2026-10-12 用户报障实锤):
   *   多锚同 id(08 五分组/05 健康分组)的段集合随数据增减/重排是**常态** —— 组空整节隐藏
   *   (锚离场)、组补进新锚、dtHoldAnchors 早分支把锚改挂宿主尾部(次序变), 集合内容没变
   *   也会被位置比对误判"换代" → gen++ → **整桥(所有组的表)重挂 = 全表格闪烁**, 且 5s 轮询
   *   下活数据每拍组 membership 翻动 = 每拍全闪(数据还只随重挂刷新, 观感"冻在一帧一爆")。
   *   正解: 仅当**同一 seg 的锚元素被换新**才换代 —— 那段 teleport 的目标元素变了, 必须重挂
   *   重解析(Vue 3 Teleport 目标被外部换新后不会自行迁回); seg 新增不换代(该段 segment 本就
   *   随 v-for 新挂进新锚), seg 消失不换代(该段 segment 随 rowsFn 过滤卸载, 无游离 teleport)。
   * !gen **单调自增**永不回落(U1 路径C 红验): 回落即 :key 净零, Teleport 原地补丁写进游离旧锚。 */
  function dtSyncAnchors(host, vm) {
    if (!host || typeof host.querySelectorAll !== "function" || !vm || !vm.dtBridge) return;
    var prev = host.__dtAnchorEls || {};   /* tid -> { seg -> el }(上一拍对账快照) */
    var seen = {};                         /* tid -> { seg -> el }(本拍在场锚) */
    var anchors = host.querySelectorAll("[data-dt-table-anchor]");
    for (var i = 0; i < anchors.length; i++) {
      var tid = anchors[i].getAttribute("data-dt-table-anchor");
      var seg = anchors[i].getAttribute("data-dt-seg") || "";
      if (tid) (seen[tid] || (seen[tid] = {}))[seg] = anchors[i];
    }
    for (var t in seen) {
      var cur = vm.dtBridge[t];
      var old = prev[t] || {};
      var same = !!cur && !!cur.on;
      if (same) {
        var emptyHost = true;
        for (var _k in old) { emptyHost = false; break; }
        /* 2026-10-14(四内容页签经典移除后 100% 暴露): **宿主是新的**时, 上一拍对账必为空
         * (__dtAnchorEls 按宿主记账, 换宿主/重建宿主都从空开始)。此时"上拍没有这个 seg"不再
         * 能推出"新段随 v-for 新挂进旧锚"—— 桥的 Teleport 目标还钉在**已离文档的旧锚**上,
         * 而 :to 选择器串没变, Vue 不会重解析目标 ⇒ 表格体挂进游离节点, 新锚恒空、行恒 0。
         * 判别 = 该 tid 在这台宿主上**从无记账**(old 空) ⇒ 锚元素对本宿主是新的, 必须换代
         * 让桥重挂一次(重挂才会重解析 :to)。原判据保留(同宿主同元素不换代, 数据轮询零重挂;
         * 同宿主**新增 seg** 仍不换代 —— 该段随桥自身 v-for 新挂进新锚)。 */
        for (var s in seen[t]) {
          /* 只问"这个 seg 上拍的锚还在不在、是不是同一个元素"; 上拍没有的 seg(新增)
           * 不构成换代理由 —— 新段随 v-for 新挂, 新锚就是它的首宿。 */
          if (old[s] && old[s] !== seen[t][s]) { same = false; break; }
        }
      }
      if (same) continue; /* 各在场段的锚元素都没换: 代数不动(数据轮询下桥零重挂) */
      vm.dtBridge[t] = { gen: (cur ? cur.gen : 0) + 1, on: true };
    }
    for (var t2 in prev) {
      if (!seen[t2] && vm.dtBridge[t2]) vm.dtBridge[t2].on = false; /* 锚全离场(空态/换变体): 摘 on, gen 保持单调 */
    }
    host.__dtAnchorEls = seen;
  }

  /* ---------------- 桥锚驻留(模板表格闪烁修复, 与 dtSyncAnchors/anchFill 同族) ----------------
   * 病根: 变体早分支(正在加载 / 加载失败 / 暂无数据)用 replaceChildren 清掉整帧时, 宿主里
   * 记账的锚元素(Teleport 表格体就挂在它里面)随之离场 → dtSyncAnchors 当场摘 on → 桥卸载;
   * 数据回来整帧重建, 锚再现 → gen 自增 → 桥重挂。这一卸一挂在用户眼里就是**表格闪烁**,
   * 且卸/挂两拍与根渲染批一旦错位(换代拍的 :key 净写在途), Teleport 内容会被抛进**游离旧锚**
   * —— 表格直接消失且不恢复(本缺陷的两种面貌, 真机复现取证所见)。
   * 驻留: 早分支清帧后把记账锚按原样接回宿主(display:none 隐藏持有)——
   *   ·锚不离场 ⇒ dtSyncAnchors 不摘 on ⇒ 桥不卸载 ⇒ 零闪烁;
   *   ·整帧回来时 anchFill 把**同一元素**换回 slot 位并复位 display, 元素身份不变 ⇒ 不换代
   *     ⇒ 不重挂(行更新照走引擎响应式, 横滚位/列宽/排序态全保留)。
   * 观感口径: 早分支文案(加载/失败/空态)原样呈现, 只是等待期不再拆掉旧表格 —— 与 FX-29
   * 「拉新数据前先清空旧数据」坑档同向(快中间态本身就是闪)。多锚同 id(08 五分组)逐段驻留。
   * 只认「整帧未渲染(无 slot)且记账非空」: 整帧路径锚归 anchFill 管, 不插手; 宿主从未出过
   * 锚(首载 loading)时记账为空, 零操作。回落 catch 路径**不**驻留(变体已弃守, 桥须随摘)。 */
  function dtHoldAnchors(host) {
    if (!host || typeof host.querySelectorAll !== "function") return;
    var book = host.__dtAnchorKeep;
    if (!book) return;
    if (host.querySelector("[data-dt-anchor-slot]")) return; /* 整帧在: 锚归 anchFill 管 */
    for (var key in book) {
      var el = book[key];
      /* 判据是**离文档**(isConnected 假)而非"父节点不是宿主": 整帧渲染后锚在
       * .dt07-list 里(父节点是列表容器不是宿主), 按父节点判会把已就位的锚每次
       * 渲染后都挪走并隐藏 —— 表格反而被藏掉。早分支 replaceChildren 才真离文档。 */
      if (el && !el.isConnected) {
        if (el.style) el.style.display = "none";
        host.appendChild(el);
      }
    }
  }

  /* ---------------- Vue mixin(app.js 末尾 app.mixin(window.AQB_DRAWER_TPL)) ----------------
   * 方法本体都在这层; drawer.js 只留一行式钩子(_dtSync/_dtNotify/_dtUnmountAll, 经 this. 调用,
   * 模板不可达所以允许 _ 前缀)。模板可达成员不带下划线(dtHostOn/dtMenuPick)。 */
  window.AQB_DRAWER_TPL = {
    computed: {
      /* 2026-10-10(模板选择迁右键): 菜单目标页签 —— openDrawerMenu 按右键命中区域落的
       * drawerMenu.tab(变体宿主 data-dt-host / 合并列 data-dt-tab), 缺省回落当前页签。
       * 选择器相关 computed(dtTplOptions/dtTplCurrent)随头部下拉一并退役, 由下列菜单 computed 取代。 */
      dtMenuTab() {
        return (this.drawerMenu && this.drawerMenu.tab) || this._dtCurTab();
      },
      /* 右键菜单模板候选(注册表是 boot 期静态数据, 依赖目标页签变化即可): 有经典的页签
       * (仅流量)「经典」在首位, 四内容页签只有变体 —— 长度 < 2 即无可挑, openDrawerMenu 不弹 */
      dtMenuTplOptions() {
        return window.AQB_DRAWER_TPL_REG.choices(this.dtMenuTab);
      },
      /* 右键菜单当前模板选择(带勾项): 缺省回落该页签缺省档(四内容页签 = 首个变体) */
      dtMenuTplCurrent() {
        var tab = this.dtMenuTab;
        return (this.drawerTplSel || {})[tab] || window.AQB_DRAWER_TPL_REG.defaultSel(tab);
      },
      /* 右键菜单是否含合并开关: 仅种子详情形态(traffic 形态无合并项, 只出流量模板选项)。
       * W3(计划 26-10-11-2106): 走形态判据单点 drawerIsSeed(drawer.js, 自带假实例守卫)。 */
      dtMenuMergeOn() {
        return this.drawerIsSeed;
      },
    },
    /* traffic 数据落袋通知(S6, 见文件头「S6 接入说明」)不写成 watch 选项: 本 mixin 走
     * app.mixin 全局注入, Vue 的 <transition> 内置假实例(BaseTransition)也会吃进全局 mixin
     * 的 watch —— 其上没有 data 面(drawer 未定义), getter 求值即抛 TypeError(实测 13 个
     * transition = 13 条报错)。改为根实例 mounted 后 $watch 单发注册(下方守卫保证只落在
     * 有数据面的真实例上), 卸载时摘除。 */
    mounted() {
      if (!this.drawer) return; /* BaseTransition 等假实例无数据面: 跳过(真根实例恒有 drawer) */
      this._dtUnwatchTraffic = this.$watch("qbCurData", () => {
        if (!this.qbTrafficActive) return; /* 非流量形态(含关面板的数据 null 化)不通知 */
        this.$nextTick(() => this._dtNotify("traffic"));
      });
      /* W4: resize 防抖回写 dtWinW 与 drawerMerge 换代重挂两条监听已收进 drawer.js(合并是
       * 抽屉级布局状态) —— 本层只管 traffic 落袋通知, 两层 mixin 各自注册互不重复。 */
    },
    beforeUnmount() {
      if (this._dtUnwatchTraffic) {
        this._dtUnwatchTraffic();
        this._dtUnwatchTraffic = null;
      }
    },
    methods: {
      /* 全部变体表格体桥熄灯(先落一帧, 再让 DOM 分支/合并标志翻转): 拆桥与"拆它的 Teleport
       * 目标"同帧发生时 Vue 运行期崩溃(见 drawer.js dtToggleMerge 注), 故合并开关 / 视口门跨越
       * 都调本方法先卸桥。gen 不动, 只摘 on —— 下一帧 dtSyncAnchors 会按在场锚重新点亮。 */
      _dtBridgesOff() {
        if (!this.dtBridge) return;
        for (var t in this.dtBridge) {
          if (this.dtBridge[t]) this.dtBridge[t].on = false;
        }
      },
      /* 当前模板归属页签: 流量形态(三挂点)归 traffic, 其余随 drawer.tab */
      _dtCurTab() {
        return this.qbTrafficActive ? "traffic" : this.drawer.tab;
      },
      /* 该页签生效档的**唯一取值口**: 选中表缺键/脏值 → 该页签缺省档(四内容页签 = 首个变体,
       * 流量 = classic)。全层不再出现 `|| CLASSIC` 字面量 —— 缺省口径单点在注册表 defaultSel。 */
      _dtSel(tab) {
        return (this.drawerTplSel || {})[tab] || window.AQB_DRAWER_TPL_REG.defaultSel(tab);
      },
      /* 宿主显隐(模板 v-show 唯一入口 —— 变体与 Vue 争 DOM 红线: 显隐只走 host 自身):
       * 错误态与 general 无详情时宿主让位; 四内容页签自 2026-10-14 起**恒由变体宿主承载**
       * (经典渲染链已整体移除, 不再有 v-if/v-else 双分支 —— 宿主是唯一正文载体, 故本门只
       * 管"此刻该不该显示"); R2 S2: 合并生效时对内两列宿主同显(不只当前页签)。 */
      dtHostOn(tab) {  /* dtSplitOn/_dtPairOf 自 W4 起住 drawer.js mixin, 经 this 消费同源判据 */
        if (this.drawer.error) return false;
        if (tab === "general" && !this.drawer.detail) return false;
        if (this.dtSplitOn) return this._dtPairOf(tab) === this._dtPairOf(this.drawer.tab);
        return this._dtCurTab() === tab;
      },
      /* ---------------- 变体表格体桥(计划 26-10-12-0527 D1 = Teleport 锚) ----------------
       * 变体声明 tableId 时, 其表格体 = dtHtml 输出的空锚 + drawer.html 的 <teleport> 渲染
       * (表壳 aq-table + 行渲染器, 全 Vue 管理)。锚代数表 dtBridge(state.js data):
       * _dtMountOne 每见一次锚自增(:key 含代数 → 宿主重建后 Teleport 强制重挂进**当前**锚,
       * 不重挂会残留进游离节点 —— Vue 3 Teleport 目标被移除后不会自行迁回), _dtUnmountOne
       * 清零(v-if 摘内容, 防死锚泄漏)。四件方法都是模板可达(不带下划线)。 */
      /* 该页签当前选中变体的桥表 id; 经典/未声明 tableId/未注册 → ""(无桥) */
      dtBridgeTbl(tab) {
        var sel = this._dtSel(tab);
        var e = window.AQB_DRAWER_TPL_REG.get(tab, sel);
        return e && e.tableId ? e.tableId : "";
      },
      /* 桥是否点亮: 有表 id + 描述符在 + 该锚当前有代数(锚在 DOM) */
      dtBridgeOn(tab) {
        var tid = this.dtBridgeTbl(tab);
        return !!tid && !!window.AQB_DRAWER_TPL_DEFS && !!window.AQB_DRAWER_TPL_DEFS[tid] && !!(this.dtBridge[tid] && this.dtBridge[tid].on);
      },
      /* Teleport 目标是否**此刻真在文档里**(挂载拍判据, 2026-10-14 合并态切换报障)。
       * 为什么必须由**桥组件自己的渲染拍**判, 不能并进 dtBridgeOn: 布局换代(合并开关/门跨越/
       * 切页签/换目标)的 patch 顺序是「先拆旧分支(旧锚随之离场) → 再挂新分支」, 而父级 v-if 的
       * dtBridgeOn 是**拆之前**求值的 —— 那一拍旧锚还在, 判真; 等桥组件真挂载时锚已消失。
       * 目标不存在的 teleport, Vue 生产版**静默不挂子节点**(无警告), 之后卸载它时对 null
       * component 解构而抛 TypeError, 整次 patch 中断 ⇒ 抽屉停在半渲染态(用户所见「合并态
       * 切换后内容消失」)。本判据在桥组件渲染拍求值, 与 teleport 的 mount 同拍, 故为真值。
       * 锚稍后由 _dtSync 挂变体时出现 ⇒ dtBridge 状态变更 ⇒ 桥重渲 ⇒ teleport 归位, 不缺内容。 */
      dtBridgeTargetOn(tab, seg) {
        var sel = this.dtBridgeTo(tab, seg);
        if (!sel || typeof document === "undefined") return false;
        return !!document.querySelector(sel);
      },
      /* Teleport :to(锚选择器, 约定单点: data-dt-table-anchor="<tableId>"; 分段桥(U2, 08
       * 五分组)追 [data-dt-seg="<segKey>"] —— 同一 tableId 的多锚按段寻址, 单锚段 seg 恒 "") */
      dtBridgeTo(tab, seg) {
        var base = '[data-dt-table-anchor="' + this.dtBridgeTbl(tab) + '"]';
        return seg ? base + '[data-dt-seg="' + seg + '"]' : base;
      },
      /* Teleport :key(含代数 —— 代数变即重挂) */
      dtBridgeKey(tab) {
        var st = this.dtBridge[this.dtBridgeTbl(tab)];
        return this.dtBridgeTbl(tab) + "@" + (st ? st.gen : 0);
      },
      /* 桥描述符取数(drawer.html 的 teleport 块消费; 描述符字段见 app.js DRAWER_TABLE_DEFS
       * 变体行注 —— rows/rowKey/rowModel/rowProp 四件)。非桥形态返回 null(模板 v-if 已挡)。 */
      dtBridgeDef(tab) {
        var tid = this.dtBridgeTbl(tab);
        return tid ? ((window.AQB_DRAWER_TPL_DEFS || {})[tid] || null) : null;
      },
      dtBridgeRows(tab) {
        var def = this.dtBridgeDef(tab);
        if (!def || !this[def.rows]) return [];
        return this[def.rows](tab);
      },
      /* 行修饰类字段名(U2): 变体行装配在行对象上预挂的类串(bad/lan/hand…), 桥模板绑到
       * .group-row 上 —— 行级个性(红行/内网标/握手半透明)经引擎行容器保留(D5 口径)。 */
      dtBridgeRowCls(tab) {
        var def = this.dtBridgeDef(tab);
        return (def && def.rowCls) || "";
      },
      /* 分段桥(U2): 描述符 segs = true 时 rows 方法返回 [{key, rows}](08 五分组: 每组一个
       * 锚, 分组头留在外壳 —— 分组是版式, 行是引擎表体); 否则归一为单段 { key: "", rows }。
       * 排序在桥模板对**每段**调 sortedDrawer(同 tableId 同一座排序键 —— 08 的组内排序
       * 跨组共享, 与原手搓状态机同口径)。 */
      dtBridgeSegs(tab) {
        var def = this.dtBridgeDef(tab);
        if (!def) return [];
        var rs = this.dtBridgeRows(tab);
        if (def.segs) return Array.isArray(rs) ? rs : [];
        return [{ key: "", rows: rs || [] }];
      },
      /* 变体行装配单点(U2): 描述符 rows: "dtTplRows" → 按当前选中变体的注册条目回调
       * rowsFn(ctx)。行来源与筛选是版式语义(变体文件自管), 排序/列交互归引擎 —— 两层
       * 在桥模板会合。无 rowsFn 的条目返回 [](行恒空, 守阵钉"桥变体必须配 rowsFn")。 */
      dtTplRows(tab) {
        var sel = this._dtSel(tab);
        var e = window.AQB_DRAWER_TPL_REG.get(tab, sel);
        return e && typeof e.rowsFn === "function" ? e.rowsFn(this) : [];
      },
      dtBridgeRowKey(tab) {
        var def = this.dtBridgeDef(tab);
        return (def && def.rowKey) || "";
      },
      dtBridgeRowModel(tab) {
        var def = this.dtBridgeDef(tab);
        return (def && def.rowModel) || "";
      },
      dtBridgeRowProp(tab) {
        var def = this.dtBridgeDef(tab);
        return (def && def.rowProp) || "r";
      },
      /* U4 行级键盘面(issue 26-10-07-0846): 描述符 rowTab 声明的表, 行容器 tabindex=-1
       * (不进 Tab 序, 行内原生控件自然参与 Tab; 锚点行由变体 rowAfterFn roving 设 0)。 */
      dtBridgeRowTab(tab) {
        var def = this.dtBridgeDef(tab);
        return !!(def && def.rowTab);
      },
      /* U4: .group-table @vue:mounted 的回调(锚每次换代重挂恰好一次)。描述符 rowAfter
       * 声明位 → 按归属变体反查注册条目 rowAfterFn(el)。异常吞掉不阻断渲染链。 */
      dtRowAfter(tab, vnode) {
        var def = this.dtBridgeDef(tab);
        if (!def || !def.rowAfter) return;
        var sel = this._dtSel(tab);
        var e = window.AQB_DRAWER_TPL_REG.get(tab, sel);
        if (!e || typeof e.rowAfterFn !== "function") return;
        var el = vnode && vnode.el ? vnode.el : vnode;
        try { e.rowAfterFn(el); } catch (err) { /* 渲染后回调不阻断渲染 */ }
      },
      /* 右键菜单模板选择落点: 目标页签取 dtMenuTab(右键命中区域), 白名单外脏值忽略(守阵口径同
       * readSel); 合法即落盘 + 重挂, 并收菜单。菜单已开, 无「回落显示值」回写口(那是原生 select
       * 的 value 回写), 故脏值直接 return。 */
      dtMenuPick(id) {
        var tab = this.dtMenuTab;
        id = String(id || "");
        /* 合法档 = 该页签候选集内(四内容页签只有变体; 流量页签只有 classic) —— 集外脏值忽略 */
        var ok = window.AQB_DRAWER_TPL_REG.choices(tab).some(function (o) { return o.id === id; });
        if (!ok) return;
        this.drawerTplSel[tab] = id;
        this.dtPersistSel();
        /* 落盘后 $nextTick 再 _dtSync: 换变体要重建宿主子树(外壳 + 桥锚), 同拍挂载可能撞上
         * Vue 尚未提交的渲染 —— 等一拍宿主就位再挂, 一次挂准(general 无列表轮询 = 不补挂)。 */
        var self = this;
        this.$nextTick(function () { self._dtSync(); });
        if (this.drawerMenu) this.drawerMenu.visible = false;
      },
      /* 写侧单漏斗(与 persistDrawerTab 同纪律: 写失败吞异常, 只影响刷新后落点) */
      dtPersistSel() {
        try {
          var out = {};
          var tabs = window.AQB_DRAWER_TPL_REG.tabs;
          for (var i = 0; i < tabs.length; i++) out[tabs[i]] = this._dtSel(tabs[i]);
          localStorage.setItem(STORE_KEY, JSON.stringify(out));
        } catch (e) { /* 写入失败: 本轮仍生效, 刷新后回落缺省档 */ }
      },
      /* ---------------- 生命周期(drawer.js 一行式钩子的本体) ----------------
       * R2 S1: classic 移植为页插件 —— _dtMountActive 对 classic 也挂载(不再是「classic 不挂、
       * Vue 包裹层接管」); R2 S2: 合并双列 = 主列(当前页签, _dtMounted) + 次列(_dtMounted2),
       * 主列挂载语义与回落守阵完全不动, 次列独立挂载态成对卸载/通知。 */
      /* 换页签/换目标(_loadDrawerTab 尾): 卸旧全部实例, 挂当前页签(主列)+ 合并次列 */
      _dtSync() {
        this._dtUnmountAll();
        this._dtMountActive(this._dtCurTab());
        this._dtMountSplit();
      },
      /* 单实例挂载: 按选择取注册表条目; 变体挂载态给宿主加 .dt-tpl(限宽作用域类, R2 S1 ——
       * 经典链历史上恒满宽, 限宽只归变体), classic 摘除。挂载失败返回 null(未挂载语义)。 */
      _dtMountOne(tab, sel) {
        var entry = window.AQB_DRAWER_TPL_REG.get(tab, sel || this._dtSel(tab));
        if (!entry) return null;
        var host = this._dtFindHost(tab);
        if (!host) return null;
        /* 挂载态给宿主加 .dt-tpl(变体专属限宽作用域类) —— 2026-10-14 起注册表里只剩变体
         * (经典渲染链已删), 故挂载即变体, 恒加。 */
        if (host.classList) host.classList.add("dt-tpl");
        var st = { tab: tab, entry: entry, host: host, ownerKey: "" };
        this._dtRender(st);
        /* 桥锚代数(U2 起)在 _dtRender 尾部统一对账(dtSyncAnchors) —— 挂载与数据通知共用
         * 一个对账单点, 这里不再重复扫描(U1 的挂载拍扫描已并入)。 */
        return st;
      },
      _dtMountActive(tab) {
        this._dtMounted = null;
        var st = this._dtMountOne(tab, this._dtSel(tab));
        if (st) {
          st.ownerKey = "_dtMounted";
          this._dtMounted = st;
        }
      },
      /* R2 S2: 合并次列 = 生效对内非当前页签那列; 未生效(单栏/门外/对外页签)恒空 */
      _dtMountSplit() {
        this._dtMounted2 = null;
        if (!this.dtSplitOn) return;
        var p = window.AQB_DRAWER_MERGE.pairOf(this.drawer.tab);  /* W4: 对结构单点在 drawer.js */
        var other = p.tabs[0] === this.drawer.tab ? p.tabs[1] : p.tabs[0];
        var st = this._dtMountOne(other, this._dtSel(other));
        if (st) {
          st.ownerKey = "_dtMounted2";
          this._dtMounted2 = st;
        }
      },
      /* 数据落袋(drawer.js 四 fetcher + _qbLoad): 活动实例逐个重渲染。
       * 未挂载/宿主已被拆时懒挂载兜底 —— 打开抽屉走 general 初值路径时 _loadDrawerTab 不执行
       * (openTorrentDrawer 只拉详情), 插件挂载靠 detail 落袋的第一发通知补齐; 流量正文块的
       * 加载/错误/空态分支会拆装宿主(v-if), 拆过就卸旧重挂(四页签宿主恒在, isConnected 恒真);
       * 合并次列同判据独立兜底(v-if 换代/合并开关翻转都会拆掉旧宿主)。 */
      _dtNotify(type) {
        var tab = this._dtCurTab();
        var st = this._dtMounted;
        if (!st || st.tab !== tab || !st.host.isConnected) {
          this._dtUnmountAll();
          this._dtMountActive(tab);
          this._dtMountSplit();
          return;
        }
        this._dtNotifySt(st, type);
        var st2 = this._dtMounted2;
        if (st2) {
          if (!st2.host.isConnected || this._dtPairOf(st2.tab) !== this._dtPairOf(tab)) {
            this._dtUnmountOne("_dtMounted2");
            this._dtMountSplit();
            return;
          }
          this._dtNotifySt(st2, type);
        }
      },
      _dtNotifySt(st, type) {
        if (st.entry.notify) {
          try { st.entry.notify(type, st.host, this); } catch (e) { /* 插件通知失败不拖垮面板 */ }
          return;
        }
        this._dtRender(st);
      },
      _dtRender(st) {
        try {
          st.entry.render(st.host, this);
          /* 桥锚驻留(模板表格闪烁修复): 早分支(加载/错误/空态)清帧后把记账锚接回宿主
           * 隐藏持有 —— 锚不离场 => 下面 dtSyncAnchors 不摘 on => 桥不卸载(表格不闪),
           * 数据回来 anchFill 原元素归位不换代(不重挂)。node 探针环境无 DOM(函数内自守)。 */
          dtHoldAnchors(st.host);
          /* 桥锚对账(U2 单点): 挂载拍 + 每次数据通知都过这里 —— 锚在场且元素身份未变不换代
           * (数据轮询下桥零重挂, 行更新走引擎响应式); 锚新现/重建 gen 单调自增; 锚离场摘 on。
           * node 探针环境无 DOM(函数内自守)。 */
          dtSyncAnchors(st.host, this);
        } catch (e) {
          /* 变体渲染抛错(P2-1, 报告 26-10-07-0542): 该页签自动回落到**缺省档** —— 复位
           * drawerTplSel.<tab>(状态单点仍是 drawerTplSel, 不新增并行标志)并按缺省档语义卸载
           * 本变体(destroy + 清宿主 + 摘 .dt-tpl + 摘挂载态), 后续通知/换页签/重开面板都按
           * 缺省档续走。复位随 dtPersistSel 落盘: 持续抛错的变体不跨会话钉死坏选择。
           * !2026-10-14: 经典渲染链已整体移除, 兜底不再是 classic —— 四内容页签的缺省档 =
           * 该页签**首个变体**(defaultSel), 下一拍 _dtNotify 按新档重挂; 若失败档恰是缺省档
           * 则不改写(不落盘空转), 宿主留空并由下方 console.error 留痕。 */
          if (st.entry.destroy) {
            try { st.entry.destroy(st.host, this); } catch (e2) { /* destroy 失败不阻断回落 */ }
          }
          try { st.host.replaceChildren(); } catch (e2) { /* host 已不在 DOM */ }
          /* 锚离场对账(U2): 回落清宿主后把桥 on 摘干净 —— 否则 teleport 悬在已消失的锚上 */
          try { dtSyncAnchors(st.host, this); } catch (e2) { /* node 探针环境假宿主 */ }
          if (st.host.classList) st.host.classList.remove("dt-tpl");
          this[st.ownerKey || "_dtMounted"] = null;
          var def = window.AQB_DRAWER_TPL_REG.defaultSel(st.tab);
          if (this.drawerTplSel && this.drawerTplSel[st.tab] !== def && window.AQB_DRAWER_TPL_REG.has(st.tab, def)) {
            this.drawerTplSel[st.tab] = def;
            this.dtPersistSel();
          }
          if (typeof console !== "undefined" && console.error) {
            console.error("[dt] render failed, fallback to " + def + " (tab=" + st.tab + ", variant=" + st.entry.id + "):", e);
          }
        }
      },
      /* 宿主定位: 逐页签 data-dt-host="<tab>"(流量页签自 2026-10-14 起无变体, 不设宿主) */
      _dtFindHost(tab) {
        var root = document.querySelector(".drawer");
        if (!root) return null;
        return root.querySelector('.dt-host[data-dt-host="' + tab + '"]');
      },
      /* 关面板(drawer.js closeDrawer): 逐实例 destroy(定时器/监听清理) + 清空宿主子树 */
      _dtUnmountAll() {
        this._dtUnmountOne("_dtMounted");
        this._dtUnmountOne("_dtMounted2");
      },
      _dtUnmountOne(key) {
        var st = this[key];
        if (!st) return;
        this[key] = null;
        if (st.entry.destroy) {
          try { st.entry.destroy(st.host, this); } catch (e) { /* destroy 失败不阻断关闭 */ }
        }
        if (st.host.classList) st.host.classList.remove("dt-tpl");
        /* 桥 on 全表摘除(2026-10-14 修运行期崩溃): 宿主要拆, 任何桥都不许继续点亮 ——
         * 旧写法只按**当场扫到的锚**摘 on, 而锚可能已不在宿主里(变体早分支清帧 / dtHoldAnchors
         * 挂到宿主尾 / 跨列重挂), 漏摘的桥会拖着一个已被 replaceChildren 摘掉的 Teleport 目标
         * 活到下一拍, Vue 拆它时报 `Cannot destructure property 'bum' of 'e' as it is null`
         * (合并开关 / 视口门跨越二连必现, 经典移除后四内容页签默认就带桥, 100% 暴露)。
         * gen 保持单调, 只摘 on; 锚扫描保留(记账清零照旧)。 */
        for (var bt in this.dtBridge) {
          if (this.dtBridge[bt]) this.dtBridge[bt].on = false;
        }
        try {
          var anchors = st.host.querySelectorAll("[data-dt-table-anchor]");
          for (var i = 0; i < anchors.length; i++) {
            var tid = anchors[i].getAttribute("data-dt-table-anchor");
            if (tid && this.dtBridge[tid]) this.dtBridge[tid].on = false; /* 幂等, 与上同 */
          }
        } catch (e3) { /* node 探针环境假宿主 */ }
        st.host.__dtAnchorEls = null;   /* 桥锚对账记账清零(U2): 下次挂载按"全新锚"换代 */
        st.host.__dtAnchorKeep = null;  /* 锚保活记账清零: 跨变体复用的宿主不得复用旧变体的锚元素 */
        try { st.host.replaceChildren(); } catch (e2) { /* host 已不在 DOM */ }
      },
    },
  };
})();
