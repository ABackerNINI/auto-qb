/* auto-qb WEB UI · 种子详情面板模板核心层(计划 26-10-06-0838 S1)
 *
 * 注册表 + 宿主生命周期 + dtHtml 转义标签模板 + CSS 注入单点 + autoqb.ui.drawerTpl 读写
 * + 变体公共骨架 helpers(reg.helpers: 工具/sig 比对/滚动自保/事件挂摘, 报告 26-10-07-0845;
 *   行级键盘 roving tabindex 四件套, issue 26-10-07-0846)
 * + 收起态摘要默认实现。本文件是「核心层」: 不含任何具体模板变体 —— 变体是
 * shared/drawer_tpl/<NN>-<tab>-<slug>.js 一个自注册文件, 删除 = 删文件 + 三份 manifest 各去 1 行。
 *
 * 装载序: 必须排在 drawer.js 之后、state.js 之前(三份 index.html 的 tpl-manifest)。
 *   - 在 drawer.js 之后没有强约束(钩子经 this. 调用, 运行时才求值), 放同域便于阅读;
 *   - 在 state.js 之前是硬约束: state.js 的 data() 调 initialDrawerTpl()(app.js), 其白名单
 *     校验依赖注册表 —— 变体文件(自注册)也必须全部排在 state.js 之前, 否则已存的合法 id
 *     会被当成脏值回落 classic(静默, 不报错)。
 *
 * ---------------- ctx 白名单契约(变体只许读/调下列成员) ----------------
 * 变体 render(host, ctx) 的 ctx 就是根组件实例(Vue mixin 方法域全在 this 上)。白名单面:
 *   读(状态): ctx.drawer.detail / .trackers / .files / .peers 及各 *Loading 态 / .error /
 *             各列表失败标记 trackersError / filesError / peersError(P3-5, 报告 26-10-07-0542:
 *             fetch 型变体据此区分「失败」与「真没有」) / .hash / .tab / .collapsed; ctx.qbCurData /
 *             qbCurPoints / qbCurSummary / qbCurWindow / qbCurError / qbCurPending(流量三域);
 *             ctx.memberByHash; ctx.flags(渐进字段门控)。
 *   调(格式化): fmtSpeed / fmtSpeedOrDash / fmtSize / fmtSizeOrDash / fmtDuration / fmtEta /
 *             fmtTs / fmtPeersQb / drawerFileRows / drawerPeerRows / drawerTrackerStatus /
 *             drawerTrackerVirtual / drawerGeneralSections / drawerTitle。
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
      m.set(id, {
        id: id, tab: tab,
        label: String(entry.label || id),
        /* 流量页签双宿主(图前/图后): slot = "pre" | "post"(缺省 post), 其余页签忽略 */
        slot: entry.slot === "pre" ? "pre" : "post",
        render: entry.render,
        summary: typeof entry.summary === "function" ? entry.summary : null,
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
    /* 切换器选项(不含 classic, classic 由模板端恒置首位) */
    options: function (tab) {
      var m = TPL_BY_TAB[tab];
      if (!m) return [];
      var out = [];
      m.forEach(function (e) { out.push({ id: e.id, label: e.label }); });
      return out;
    },
    /* localStorage autoqb.ui.drawerTpl 读侧(initialDrawerTpl 的实现, app.js 薄封装):
     * 按页签记 id, 白名单校验 —— 脏值/缺失/坏 JSON/读失败一律 classic(P-01: 升级零观感差异)。
     * 与 initialDrawerTab 同口径: 不信任存储内容。 */
    readSel: function () {
      var out = {};
      for (var i = 0; i < TABS.length; i++) out[TABS[i]] = CLASSIC;
      try {
        var raw = JSON.parse(localStorage.getItem(STORE_KEY) || "{}");
        if (raw && typeof raw === "object") {
          for (var j = 0; j < TABS.length; j++) {
            var tab = TABS[j];
            var id = raw[tab];
            if (typeof id === "string" && id !== CLASSIC && TPL_REG.has(tab, id)) out[tab] = id;
          }
        }
      } catch (e) { /* 无存储/坏 JSON/隐私模式: 保持全 classic */ }
      return out;
    },
  };
  window.AQB_DRAWER_TPL_REG = TPL_REG;

  /* ---------------- 核心基础样式(切换器/摘要条/宿主/流量布局类) ----------------
   * 只用上面白名单内的令牌; 类名 dt-* 供守阵与变体复用。 */
  dtInjectCss("00-core", [
    /* P3-7(报告 26-10-07-0542): max-width 160 -> 240 —— 160px 硬上限截断长 label 的收起态。
     * 26-10-07 用户报「切页签其它元素跟着变」: 原生 select 的自动最小宽 = 最宽 option 的宽,
     * dtTplOptions 按页签变化 => max-width 上限不改变内容驱动宽的病根, 选择器占位宽随页签变,
     * 同排 .drawer-title(flex:1 1 auto + min-width:0)与收起摘要 .dt-summary 跟着让位回弹。
     * 修法 = 定宽取代 max-width —— 占位宽与选项集/页签/数据全部解耦。
     * 26-10-09 用户报「选择框太长」: 定宽 240 -> 150 —— 只收窄, 定宽口径不变(不回退内容驱动
     * 宽)。150px 扣去内边距/边框/下拉箭头约容 10 个全角字符, 现有 15 个 label 最长 8 全角符
     * (自然宽约 130px 含内边距与下拉箭头)固定宽不截断, text-overflow 只是防未来长 label 的
     * 保险丝(Chromium 对 select 生效, 其余内核退化为裁切, 不引入新的宽度抖动源)。min-width:0
     * 允许极窄窗口下随标题按比例收缩(定宽在 flex 里即基准尺寸, shrink 语义不变)。收起摘要
     * .dt-summary 是另一个独立定宽源(240px, 见下一条), 与本框各按内容域定宽, 不必等宽。 */
    ".drawer .dt-select { align-self: center; width: 150px; min-width: 0; text-overflow: ellipsis; padding: 2px 4px;",,
    "  font: 12px/1.6 system-ui, sans-serif; color: var(--fg-muted); background: var(--bg-hover);",
    "  border: 1px solid var(--border-soft); border-radius: var(--radius-sm); cursor: pointer;",
    "  transition: color var(--dur) var(--ease), border-color var(--dur) var(--ease); }",
    ".drawer .dt-select:hover, .drawer .dt-select:focus { color: var(--fg); border-color: var(--border-strong); outline: none; }",
    ".drawer .dt-select option { color: var(--fg); background: var(--bg-elev); }",
    /* 收起摘要与切换器同款内容驱动宽病(速度/进度每轮询周期都在变, 收起态头部逐秒抖; 切页签
     * 换摘要内容同款): flex-basis 定宽 240px —— 摘要文字短则留白、长则省略, 行几何与页签/数据
     * 恒定解耦。与 .dt-select(150px)同为独立定宽源但各按内容域取值, 不必等宽(26-10-09 切换器
     * 收窄后分叉; 摘要承载速度/进度文案需要更宽的稳定行)。 */
    ".drawer .dt-summary { flex: 0 1 240px; min-width: 0; align-self: center; overflow: hidden;",
    "  text-overflow: ellipsis; white-space: nowrap; font-size: 11.5px; line-height: 1.5;",
    "  color: var(--fg-muted); }",
    ".drawer .dt-host:empty { display: none; }",
    /* Q1(报告 26-10-07-0542 §2): 变体内容层最大可读宽度 —— 四页签宿主统一限宽居中, 4K 下
     * 键值栅格/英雄行/多列卡片不再等分拉伸到视口宽(单点收口, 15 个变体文件零复刻); 窄视口
     * (内容宽 <= 1400px)零变化。traffic 双宿主不限宽: 图本体/工具条/图例归经典链恒满宽,
     * 13/15 的 KPI 头行限宽会与下方图缘错位, 14 的解读栏自带 288px 固定右栏无拉伸问题。 */
    ".drawer .dt-host[data-dt-host=\"general\"], .drawer .dt-host[data-dt-host=\"trackers\"],",
    "  .drawer .dt-host[data-dt-host=\"peers\"], .drawer .dt-host[data-dt-host=\"content\"]",
    "  { max-width: 1400px; margin-left:auto; margin-right:auto; }",
    /* 流量块 template 转 div 的布局等价层: 顶替原 fragment 直挂 .drawer-body.is-traffic(flex 纵列)
     * 的几何 —— wrapper 自身成为唯一 flex item 撑满, 内部仍是纵列(qb-chart 的 flex:1 规则
     * `.drawer-body.is-traffic .qb-chart` 是后代选择器, 在 wrapper 内照常命中)。FX-29 遮罩
     * (.drawer-body.switching > *)对 wrapper 生效(display:contents 会废掉 opacity, 故不用)。 */
    ".drawer .dt-traffic-main { flex: 1 1 auto; min-height: 0; display: flex; flex-direction: column; }",
  ].join("\n"));

  /* ---------------- Vue mixin(app.js 末尾 app.mixin(window.AQB_DRAWER_TPL)) ----------------
   * 方法本体都在这层; drawer.js 只留一行式钩子(_dtSync/_dtNotify/_dtUnmountAll, 经 this. 调用,
   * 模板不可达所以允许 _ 前缀)。模板可达成员不带下划线(dtHostOn/dtPick/dtSummaryHtml)。 */
  window.AQB_DRAWER_TPL = {
    computed: {
      /* 当前生效页签的模板选项(经典恒在首位): 注册表是 boot 期静态数据, 依赖页签变化即可 */
      dtTplOptions() {
        var tab = this._dtCurTab();
        return [{ id: "classic", label: "经典" }].concat(window.AQB_DRAWER_TPL_REG.options(tab));
      },
      dtTplCurrent() {
        var tab = this._dtCurTab();
        return (this.drawerTplSel || {})[tab] || "classic";
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
    },
    beforeUnmount() {
      if (this._dtUnwatchTraffic) {
        this._dtUnwatchTraffic();
        this._dtUnwatchTraffic = null;
      }
    },
    methods: {
      /* 当前模板归属页签: 流量形态(三挂点)归 traffic, 其余随 drawer.tab */
      _dtCurTab() {
        return this.qbTrafficActive ? "traffic" : this.drawer.tab;
      },
      /* 宿主显隐(模板 v-show 唯一入口 —— 变体与 Vue 争 DOM 红线: 显隐只走 host 自身):
       * 错误态与 general 无详情时宿主让位(与经典渲染链的接管口径一致); 流量正文块
       * 自管加载/错误/空态, 宿主在其非空分支内, 无需重复判断。 */
      dtHostOn(tab) {
        if (this._dtCurTab() !== tab) return false;
        if (tab !== "traffic" && this.drawer.error) return false;
        if (tab === "general" && !this.drawer.detail) return false;
        return ((this.drawerTplSel || {})[tab] || "classic") !== "classic";
      },
      /* 切换器 change 落点(种子头部/流量头部共用): 白名单外脏值回落当前值, 合法即落盘 + 重挂 */
      dtPick(ev) {
        var tab = this._dtCurTab();
        var id = String((ev && ev.target && ev.target.value) || "classic");
        if (id !== "classic" && !window.AQB_DRAWER_TPL_REG.has(tab, id)) {
          ev.target.value = this.dtTplCurrent; /* 脏值: 回落当前选择(守阵口径同 readSel) */
          return;
        }
        this.drawerTplSel[tab] = id;
        this.dtPersistSel();
        this._dtSync();
      },
      /* 写侧单漏斗(与 persistDrawerTab 同纪律: 写失败吞异常, 只影响刷新后落点) */
      dtPersistSel() {
        try {
          var out = {};
          var tabs = window.AQB_DRAWER_TPL_REG.tabs;
          for (var i = 0; i < tabs.length; i++) out[tabs[i]] = (this.drawerTplSel || {})[tabs[i]] || "classic";
          localStorage.setItem(STORE_KEY, JSON.stringify(out));
        } catch (e) { /* 写入失败: 本轮仍生效, 刷新后回落 classic */ }
      },
      /* ---------------- 生命周期(drawer.js 一行式钩子的本体) ---------------- */
      /* 换页签/换目标(_loadDrawerTab 尾): 卸旧变体, 按 drawerTplSel 挂当前页签变体并喂现数据;
       * 选中 classic 则只亮经典包裹层(卸载即净)。 */
      _dtSync() {
        this._dtUnmountAll();
        this._dtMountActive(this._dtCurTab());
      },
      /* 数据落袋/收起展开(drawer.js 四 fetcher + _qbLoad + toggleDrawerCollapse): 活动变体重渲染。
       * 未挂载/宿主已被拆时懒挂载兜底 —— 打开抽屉走 general 初值路径时 _loadDrawerTab 不执行
       * (openTorrentDrawer 只拉详情), 变体挂载靠 detail 落袋的第一发通知补齐; 流量正文块的
       * 加载/错误/空态分支会拆装宿主(v-if), 拆过就卸旧重挂(四页签宿主恒在, isConnected 恒真)。 */
      _dtNotify(type) {
        var tab = this._dtCurTab();
        var st = this._dtMounted;
        if (!st || st.tab !== tab || !st.host.isConnected) {
          this._dtUnmountAll();
          this._dtMountActive(tab);
          return;
        }
        if (type === "collapse") return; /* 摘要条走模板响应式(v-html 重算), 通知预留给变体自身状态 */
        if (st.entry.notify) {
          try { st.entry.notify(type, st.host, this); } catch (e) { /* 变体通知失败不拖垮面板 */ }
          return;
        }
        this._dtRender(st);
      },
      _dtRender(st) {
        try {
          st.entry.render(st.host, this);
        } catch (e) {
          /* 变体渲染抛错(P2-1, 报告 26-10-07-0542): 该页签自动回落经典渲染层, 不再降级为整幅空白
           * —— 只清宿主时经典包裹层因 drawerTplSel.<tab> !== 'classic' 仍被 v-show 藏住,
           * .dt-host:empty 又把空宿主藏住, 两条退路同时断掉。复位 drawerTplSel.<tab> 让经典层
           * v-show 自然接管、dtHostOn 随之隐藏宿主(状态单点仍是 drawerTplSel, 不新增并行标志);
           * 并按 classic 语义卸载本变体(destroy + 清宿主 + 摘挂载态), 后续通知/换页签/重开面板
           * 都按 classic 续走。复位随 dtPersistSel 落盘: 持续抛错的变体不跨会话钉死坏选择;
           * 一次性瞬时错误的代价是用户在切换器重选一次 —— 两权取其轻取前者。从回落到 Vue 重渲染
           * 之间的一拍, 空宿主由既有 .dt-host:empty 兜住不闪空白(主路径靠 v-show 切走, 不依赖
           * :empty)。不静默吞栈, 报错带页签与变体 id。 */
          this._dtMounted = null;
          if (st.entry.destroy) {
            try { st.entry.destroy(st.host); } catch (e2) { /* destroy 失败不阻断回落 */ }
          }
          try { st.host.replaceChildren(); } catch (e2) { /* host 已不在 DOM */ }
          if (this.drawerTplSel && this.drawerTplSel[st.tab] !== "classic") {
            this.drawerTplSel[st.tab] = "classic";
            this.dtPersistSel();
          }
          if (typeof console !== "undefined" && console.error) {
            console.error("[dt] render failed, fallback to classic (tab=" + st.tab + ", variant=" + st.entry.id + "):", e);
          }
        }
      },
      _dtMountActive(tab) {
        this._dtMounted = null;
        var sel = (this.drawerTplSel || {})[tab] || "classic";
        if (sel === "classic") return;
        var entry = window.AQB_DRAWER_TPL_REG.get(tab, sel);
        if (!entry) return; /* 存储里的 id 已被删文件: readSel 兜不到的运行期缺失, 回落 classic 语义 */
        var host = this._dtFindHost(tab, entry);
        if (!host) return;
        var st = { tab: tab, entry: entry, host: host };
        this._dtMounted = st;
        this._dtRender(st);
      },
      /* 宿主定位: 四页签 = data-dt-host="<tab>"; 流量页签双宿主 data-dt-host="traffic-pre|post" */
      _dtFindHost(tab, entry) {
        var root = document.querySelector(".drawer");
        if (!root) return null;
        var name = tab === "traffic" ? "traffic-" + entry.slot : tab;
        return root.querySelector('.dt-host[data-dt-host="' + name + '"]');
      },
      /* 关面板(drawer.js closeDrawer): 逐变体 destroy(定时器/监听清理) + 清空宿主子树 */
      _dtUnmountAll() {
        var st = this._dtMounted;
        if (!st) return;
        this._dtMounted = null;
        if (st.entry.destroy) {
          try { st.entry.destroy(st.host); } catch (e) { /* destroy 失败不阻断关闭 */ }
        }
        try { st.host.replaceChildren(); } catch (e2) { /* host 已不在 DOM */ }
      },
      /* ---------------- 收起态摘要(P-06: 压缩进 44px 头部, 模板 v-html 消费) ----------------
       * 活动变体声明 summary(ctx) 则用其返回(契约: 已转义 HTML), 否则用内置默认实现。 */
      dtSummaryHtml() {
        var tab = this._dtCurTab();
        var sel = (this.drawerTplSel || {})[tab] || "classic";
        if (sel !== "classic") {
          var entry = window.AQB_DRAWER_TPL_REG.get(tab, sel);
          if (entry && entry.summary) {
            try {
              var s = entry.summary(this);
              if (s) return String(s);
            } catch (e) { /* 变体摘要失败回落内置默认 */ }
          }
        }
        return this._dtDefaultSummary(tab);
      },
      /* 内置默认摘要(报告 §5 口径): 常规=状态·进度·速度·比率·HR / Tracker=健康比例 /
       * 用户=构成比例 / 内容=体积构成+未完成数 / 流量=窗口累计。全部经 esc 转义。 */
      _dtDefaultSummary(tab) {
        var parts;
        if (tab === "general") {
          var d = this.drawer.detail;
          if (!d) return esc("暂无详情");
          parts = [
            esc(d.state || "—"),
            "进度 " + esc(((d.progress || 0) * 100).toFixed(1) + "%"),
            "上 " + esc(this.fmtSpeedOrDash(d.dlspeed) || "—") + " · 下 " + esc(this.fmtSpeedOrDash(d.upspeed) || "—"),
            "比率 " + esc((d.ratio ?? 0).toFixed(2)),
          ];
          if (d.hr_excluded) parts.push("HR 已排除");
          else if (d.hr_triggered) parts.push("HR " + (d.hr_satisfied ? "已达标" : "未达标"));
          return parts.join(" · ");
        }
        if (tab === "trackers") {
          var ts = this.drawer.trackers || [];
          var real = ts.filter(function (t) { return !this.drawerTrackerVirtual(t.url); }, this);
          var ok = real.filter(function (t) { return t.status === 2; }).length;
          var updating = real.filter(function (t) { return t.status === 3; }).length;
          var bad = real.length - ok - updating;
          parts = ["正常 " + ok + " / " + real.length];
          if (updating) parts.push("更新中 " + updating);
          if (bad) parts.push("异常 " + bad);
          return esc(parts.join(" · "));
        }
        if (tab === "peers") {
          var p = this.drawer.peers || {};
          var list = Array.isArray(p.peers) ? p.peers : Object.values(p.peers || {});
          var dl = list.filter(function (x) { return (x.dlspeed || 0) > 0; }).length;
          var ul = list.filter(function (x) { return (x.upspeed || 0) > 0; }).length;
          return esc("共 " + list.length + " · 取流 " + dl + " · 供流 " + ul);
        }
        if (tab === "content") {
          var files = this.drawer.files || [];
          var total = 0, done = 0, unfinished = 0;
          for (var i = 0; i < files.length; i++) {
            var f = files[i];
            total += f.size || 0;
            done += (f.size || 0) * (f.progress || 0);
            if ((f.progress || 0) < 1) unfinished++;
          }
          return esc("共 " + files.length + " 个 · " + (this.fmtSizeOrDash(done) || "—") + " / "
            + (this.fmtSizeOrDash(total) || "—") + " · 未完成 " + unfinished);
        }
        /* traffic: 窗口累计(qbCurSummary 由 qb_traffic_chart.js 派生, 三挂点同形) */
        var s = this.qbCurSummary;
        if (!s) return esc("暂无流量数据");
        return esc("窗口 " + (s.buckets || 0) + " 桶 · 上传 " + this.fmtSize(s.up || 0)
          + " · 下载 " + this.fmtSize(s.down || 0));
      },
    },
  };
})();
