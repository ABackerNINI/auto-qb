/* auto-qb WEB UI · 种子详情面板模板核心层(计划 26-10-06-0838 S1)
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
 *     会被当成脏值回落 classic(静默, 不报错)。
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
 *             hrStateLine / hrSiteLine(classic 插件消费, R2 S1)。
 *   调(动作):   drawerCmd(action[, body, okText]) / trackerAdd / trackerRemove /
 *             setFilePriority / openFilePrio / openTargetPath / copyText / qbSetWindow /
 *             fileRowSelect / renameFileRow(classic 插件消费, R2 S1);
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
  /* ---------------- 页签合并(R2 计划 26-10-09-2219 · R3 修订) ----------------
   * 合并 = 抽屉级布局开关(drawerMerge ∈ off|on, 独立持久化键), 不是某页签的变体。R3 修订
   * (用户动议「标签页没有合并」): 开关开启且门内时 **页签栏**把四页签收敛为两对合并页签
   * [常规&内容] [Tracker&用户](可自由切换, 不再二选一); 正文按 **当前页签所属的对** 渲染双列
   * 宿主, 两列各挂对应页签当前所选页插件(classic 或变体)。
   * !R3 修正(用户报「选择并排后 tracker/用户标签显示常规/内容且为空」): 渲染哪一对列与挂载/
   *   数据供给必须同源于「当前页签」—— 判据统一走 dtPair(= 当前页签所属对)。R2 曾按标志值渲染
   *   固定一对, 切到另一对页签时模板渲染旧对的列头、挂载却按当前对找宿主, 两列列头在而内容空。
   * 门 = 视口宽下限(单点常量): 1920 屏每列约 930px 才比单栏 1400px 值得; 以下是暂态遮蔽
   * (dtSplitOn/dtMergeTabsOn 判 false, 标志保留), 不是选择撤销 —— 拉宽自动恢复。 */
  var MERGE_STORE_KEY = "autoqb.ui.drawerMerge";
  var MERGE_VALUES = ["off", "on"];
  var DT_MERGE_MIN_WIDTH = 1920;
  /* 合并对 -> [左列页签, 右列页签](列序固定, 不随当前页签换序; 也是合并页签清单与命中/落点判据) */
  var MERGE_PAIRS = { gc: ["general", "content"], tp: ["trackers", "peers"] };

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
    /* 切换器选项(不含 classic, classic 由模板端恒置首位; classic 现也是注册表正式条目) */
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

  /* ---------------- 核心基础样式(宿主/菜单/流量布局类) ----------------
   * 只用上面白名单内的令牌; 类名 dt-* 供守阵与变体复用。
   * 2026-10-10(模板选择迁右键): 原 .dt-select(头部模板下拉)整套定宽规则随下拉退役删除 ——
   * 菜单本体复用三皮肤既有 .ctx-menu/.ctx-item 样式, 模板项就是普通 .ctx-item(勾选态走 .ctx-tick),
   * 核心不再注入任何模板选择器样式, 也不再有「选择器占位宽随页签变」的病根(原生 select 专属)。 */
  dtInjectCss("00-core", [
    ".drawer .dt-host:empty { display: none; }",
    /* Q1(报告 26-10-07-0542 §2): 变体内容层最大可读宽度 —— 四页签宿主统一限宽居中, 4K 下
     * 键值栅格/英雄行/多列卡片不再等分拉伸到视口宽(单点收口, 15 个变体文件零复刻); 窄视口
     * (内容宽 <= 1400px)零变化。traffic 双宿主不限宽: 图本体/工具条/图例归经典链恒满宽,
     * 13/15 的 KPI 头行限宽会与下方图缘错位, 14 的解读栏自带 288px 固定右栏无拉伸问题。
     * R2(计划 26-10-09-2219 S1): 限宽收窄到 .dt-tpl(变体挂载态) —— classic 现也挂进宿主
     * (页插件化), 而经典链历史上恒满宽, 限宽误伤即行为回归; 核心挂载时按 entry 加/摘类。 */
    ".drawer .dt-host.dt-tpl[data-dt-host=\"general\"], .drawer .dt-host.dt-tpl[data-dt-host=\"trackers\"],",
    "  .drawer .dt-host.dt-tpl[data-dt-host=\"peers\"], .drawer .dt-host.dt-tpl[data-dt-host=\"content\"]",
    "  { max-width: 1400px; margin-left:auto; margin-right:auto; }",
    /* R2 S2 合并双列布局: 生效对的两列各挂各自所选页插件, 单一共享滚动(drawer-body 不变),
     * 列头小节标题; 上限 2400 = 两列各约 1180 可读上限 + gap(与单栏 1400 同一封顶哲学);
     * 门 1920 保证容器 >= ~1880, minmax 下限不会溢出。dt-col-head 是合并态的列标识(单栏无)。 */
    ".drawer .drawer-split { display: grid; grid-template-columns: minmax(560px, 1fr) minmax(620px, 1.15fr);",
    "  gap: 24px; max-width: 2400px; margin-left:auto; margin-right:auto; align-items: start; }",
    ".drawer .dt-col { min-width: 0; }",
    ".drawer .dt-col-head { display:flex; align-items:center; height:26px; margin-bottom:8px;",
    "  font-size:12px; font-weight:600; color:var(--fg-muted, inherit); border-bottom:1px solid var(--border-soft, transparent); }",
    /* R2 S3 右键菜单置灰项: 门不满足时可见但不可点(title 提示原因; 判定在 dtToggleMerge 再拦一道)。
     * 注入在核心层而不是三皮肤 components.css —— 菜单本体是共用模板, 一处注入三皮肤同效。 */
    ".ctx-menu .ctx-item.is-gated { color: var(--fg-dim, #888); cursor: default; }",
    ".ctx-menu .ctx-item.is-gated:hover { background: transparent; }",
    /* 流量块 template 转 div 的布局等价层: 顶替原 fragment 直挂 .drawer-body.is-traffic(flex 纵列)
     * 的几何 —— wrapper 自身成为唯一 flex item 撑满, 内部仍是纵列(qb-chart 的 flex:1 规则
     * `.drawer-body.is-traffic .qb-chart` 是后代选择器, 在 wrapper 内照常命中)。FX-29 遮罩
     * (.drawer-body.switching > *)对 wrapper 生效(display:contents 会废掉 opacity, 故不用)。 */
    ".drawer .dt-traffic-main { flex: 1 1 auto; min-height: 0; display: flex; flex-direction: column; }",
  ].join("\n"));

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
      /* 右键菜单模板选项(经典恒在首位): 注册表是 boot 期静态数据, 依赖目标页签变化即可 */
      dtMenuTplOptions() {
        return [{ id: "classic", label: "经典" }].concat(window.AQB_DRAWER_TPL_REG.options(this.dtMenuTab));
      },
      /* 右键菜单当前模板选择(带勾项) */
      dtMenuTplCurrent() {
        return (this.drawerTplSel || {})[this.dtMenuTab] || "classic";
      },
      /* 右键菜单是否含合并开关: 仅种子详情形态(traffic 形态无合并项, 只出流量模板选项) */
      dtMenuMergeOn() {
        return !!(this.drawer && this.drawer.kind === "seed");
      },
      /* R3: 合并开关是否开启(off|on; 兼容 R2 旧值 gc/tp —— 初值读取已迁移, 这里再兜一道) */
      dtMergeOn() {
        return (this.drawerMerge || "off") !== "off";
      },
      /* R3: 页签栏是否呈现合并页签 —— 开关开 + 门内。页签栏只在种子详情头部渲染(流量形态另有
       * 头部), 故无需再排除流量形态。门外回落四页签(暂态遮蔽, 标志不动)。 */
      dtMergeTabsOn() {
        return this.dtMergeOn && this.dtMergeGateOk();
      },
      /* R3: 当前页签所属的合并对("gc"|"tp"|null) —— 合并双列「渲染哪两列」的单点判据,
       * 与挂载(_dtMountSplit)/数据供给(drawer.js)同源; 流量与对外页签返回 null。 */
      dtPair() {
        return this._dtPairOf(this.drawer && this.drawer.tab);
      },
      /* R2 S2(计划 26-10-09-2219)·R3 修正: 合并布局生效判据(模板 v-if 单点) —— 开关开启 +
       * 种子详情形态 + 当前页签属于某一对 + 门内。门是暂态遮蔽: dtWinW(state.js 显式建字段)由
       * 核心 resize 监听防抖回写, 标志本身不动; 关面板/流量形态自然 false。
       * !R3: 判据与模板列组统一读 dtPair —— R2 只查「属于某个对」而模板按标志值渲染固定一对,
       * 切到另一对页签时列头在而两列宿主空(用户报障), 现修正。 */
      dtSplitOn() {
        if (!this.dtMergeOn) return false;
        if (this.qbTrafficActive) return false;
        if (!this.dtPair) return false;
        return this.dtMergeGateOk();
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
      /* R2 S2: 视口宽回写(dtWinW 是 state.js 显式建字段) + 门边界跨越后重挂 —— 防抖 150ms。
       * 只监听不读几何布局(dtSplitOn 是 computed, Vue 负责响应式翻转 v-if 结构)。 */
      this._dtOnResize = () => {
        clearTimeout(this._dtResizeT);
        this._dtResizeT = setTimeout(() => {
          this._dtResizeT = null;
          this.dtWinW = window.innerWidth;
          this.$nextTick(() => {
            this._dtSync();  /* v-if 换代后旧宿主 isConnected 已假, 卸旧重挂 */
            /* 门跨越恢复双列时第二列数据可能从未拉过(影子期零请求语义), 补给一次 */
            if (this.dtSplitOn && typeof this._drawerMergeSupply === "function") this._drawerMergeSupply();
          });
        }, 150);
      };
      window.addEventListener("resize", this._dtOnResize);
      /* R2 S2: 合并标志换代(右键开关) → 布局重挂 + 第二列数据补给。$watch 单发注册
       * (全局 mixin 的 watch 选项会波及 BaseTransition 假实例, 同 traffic 通知的规避式)。 */
      this._dtUnwatchMerge = this.$watch("drawerMerge", () => {
        this.$nextTick(() => {
          this._dtSync();
          if (this.dtSplitOn && typeof this._drawerMergeSupply === "function") this._drawerMergeSupply();
        });
      });
    },
    beforeUnmount() {
      if (this._dtUnwatchTraffic) {
        this._dtUnwatchTraffic();
        this._dtUnwatchTraffic = null;
      }
      if (this._dtUnwatchMerge) {
        this._dtUnwatchMerge();
        this._dtUnwatchMerge = null;
      }
      if (this._dtOnResize) {
        window.removeEventListener("resize", this._dtOnResize);
        this._dtOnResize = null;
      }
      if (this._dtResizeT) {
        clearTimeout(this._dtResizeT);
        this._dtResizeT = null;
      }
    },
    methods: {
      /* 当前模板归属页签: 流量形态(三挂点)归 traffic, 其余随 drawer.tab */
      _dtCurTab() {
        return this.qbTrafficActive ? "traffic" : this.drawer.tab;
      },
      /* R2 S2·R3: 当前页签所属合并对("gc"|"tp"|null) —— 合并页签命中(dtMergeTabActive)与
       * 双列列组(dtPair)的单点判据; 流量与对外页签返回 null */
      _dtPairOf(tab) {
        if (this.qbTrafficActive) return null;
        for (var k in MERGE_PAIRS) {
          if (MERGE_PAIRS[k].indexOf(tab) >= 0) return k;
        }
        return null;
      },
      /* R2 S3·R3: 合并开关宽度门(右键菜单置灰与挂载守卫共用同一判据, 常量单点 mergeMinWidth) */
      dtMergeGateOk() {
        return (this.dtWinW || window.innerWidth || 0) >= window.AQB_DRAWER_TPL_REG.mergeMinWidth;
      },
      /* R3: 右键菜单单开关落点 —— 门内才生效, 再点即关 + 落盘。
       * 布局换代(_dtSync)与第二列数据补给(_drawerMergeSupply, 本体在 drawer.js)由
       * drawerMerge 的 $watch 单发统一触发(mounted 注册, 假实例守卫同 traffic 通知)。 */
      dtToggleMerge() {
        if (!this.dtMergeGateOk()) return; /* 置灰项双保险: class 拦显示, 这里拦行为 */
        var v = this.dtMergeOn ? "off" : "on";
        this.drawerMerge = v;
        try { localStorage.setItem(MERGE_STORE_KEY, JSON.stringify(v)); } catch (e) { /* 写失败本轮仍生效 */ }
        if (this.drawerMenu) this.drawerMenu.visible = false;
      },
      /* R3: 合并页签点击落点 —— 切到该对(已在其中则零副作用, 避免无谓重拉); 目标页签取对的首列
       * (列序按对固定; 双列两列都会被挂载, 对内的具体取值不影响呈现, 只决定"主列=当前页签"的
       * 挂载归属与头部模板切换器指向)。 */
      dtMergeTabPick(pair) {
        var tabs = MERGE_PAIRS[pair];
        if (!tabs) return;
        if (tabs.indexOf(this.drawer && this.drawer.tab) >= 0) return;
        if (typeof this.drawerTab === "function") this.drawerTab(tabs[0]);
      },
      /* R3: 合并页签高亮判据 —— 当前页签落在该对内即高亮(页签栏 :class 单点) */
      dtMergeTabActive(pair) {
        var tabs = MERGE_PAIRS[pair];
        return !!tabs && tabs.indexOf(this.drawer && this.drawer.tab) >= 0;
      },
      /* 宿主显隐(模板 v-show 唯一入口 —— 变体与 Vue 争 DOM 红线: 显隐只走 host 自身):
       * 错误态与 general 无详情时宿主让位(与经典渲染链的接管口径一致); 流量正文块
       * 自管加载/错误/空态, 宿主在其非空分支内, 无需重复判断。
       * R2 S1: classic 移植为页插件后宿主恒承载内容(classic 不再是「宿主隐 + Vue 包裹层显」),
       * 选中态只决定挂哪个插件; R2 S2: 合并生效时对内两列宿主同显(不只当前页签)。 */
      dtHostOn(tab) {
        if (tab === "traffic") return this._dtCurTab() === "traffic";
        if (this.drawer.error) return false;
        if (tab === "general" && !this.drawer.detail) return false;
        if (this.dtSplitOn) return this._dtPairOf(tab) === this._dtPairOf(this.drawer.tab);
        return this._dtCurTab() === tab;
      },
      /* 右键菜单模板选择落点: 目标页签取 dtMenuTab(右键命中区域), 白名单外脏值忽略(守阵口径同
       * readSel); 合法即落盘 + 重挂, 并收菜单。菜单已开, 无「回落显示值」回写口(那是原生 select
       * 的 value 回写), 故脏值直接 return。 */
      dtMenuPick(id) {
        var tab = this.dtMenuTab;
        id = String(id || "classic");
        if (id !== "classic" && !window.AQB_DRAWER_TPL_REG.has(tab, id)) return;
        this.drawerTplSel[tab] = id;
        this.dtPersistSel();
        this._dtSync();
        if (this.drawerMenu) this.drawerMenu.visible = false;
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
        var entry = window.AQB_DRAWER_TPL_REG.get(tab, sel || CLASSIC);
        if (!entry) return null;
        var host = this._dtFindHost(tab, entry);
        if (!host) return null;
        if (host.classList) {
          if (entry.id !== CLASSIC) host.classList.add("dt-tpl");
          else host.classList.remove("dt-tpl");
        }
        var st = { tab: tab, entry: entry, host: host, ownerKey: "" };
        this._dtRender(st);
        return st;
      },
      _dtMountActive(tab) {
        this._dtMounted = null;
        var sel = (this.drawerTplSel || {})[tab] || CLASSIC;
        var st = this._dtMountOne(tab, sel);
        if (st) {
          st.ownerKey = "_dtMounted";
          this._dtMounted = st;
        }
      },
      /* R2 S2: 合并次列 = 生效对内非当前页签那列; 未生效(单栏/门外/对外页签)恒空 */
      _dtMountSplit() {
        this._dtMounted2 = null;
        if (!this.dtSplitOn) return;
        var pair = MERGE_PAIRS[this._dtPairOf(this.drawer.tab)];
        var other = pair[0] === this.drawer.tab ? pair[1] : pair[0];
        var sel = (this.drawerTplSel || {})[other] || CLASSIC;
        var st = this._dtMountOne(other, sel);
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
        } catch (e) {
          /* classic 自身抛错(R2 S1): 无更低回落层 —— 错误外壳进宿主不空屏, 不复位用户选择。 */
          if (st.entry.id === CLASSIC) {
            try { st.host.replaceChildren(); } catch (e2) { /* host 已不在 DOM */ }
            try { st.host.innerHTML = window.AQB_DRAWER_TPL_REG.kit.error("该页渲染失败"); } catch (e2) { /* 同上 */ }
            if (typeof console !== "undefined" && console.error) {
              console.error("[dt] classic render failed (tab=" + st.tab + "):", e);
            }
            return;
          }
          /* 变体渲染抛错(P2-1, 报告 26-10-07-0542): 该页签自动回落经典渲染层 —— 复位
           * drawerTplSel.<tab>(状态单点仍是 drawerTplSel, 不新增并行标志)并按 classic 语义
           * 卸载本变体(destroy + 清宿主 + 摘 .dt-tpl + 摘挂载态), 后续通知/换页签/重开面板
           * 都按 classic 续走。复位随 dtPersistSel 落盘: 持续抛错的变体不跨会话钉死坏选择。
           * R2 S1: classic 也是插件了, 复位后立即重挂 classic(不再有 Vue 包裹层兜底显示)——
           * 守阵电池的假 ctx 只带回落路径触碰的面, 挂载助手缺省时跳过即时重挂(下一拍通知补齐)。 */
          if (st.entry.destroy) {
            try { st.entry.destroy(st.host, this); } catch (e2) { /* destroy 失败不阻断回落 */ }
          }
          try { st.host.replaceChildren(); } catch (e2) { /* host 已不在 DOM */ }
          if (st.host.classList) st.host.classList.remove("dt-tpl");
          this[st.ownerKey || "_dtMounted"] = null;
          if (this.drawerTplSel && this.drawerTplSel[st.tab] !== CLASSIC) {
            this.drawerTplSel[st.tab] = CLASSIC;
            this.dtPersistSel();
          }
          if (typeof this._dtMountOne === "function" && typeof this._dtFindHost === "function") {
            var stc = this._dtMountOne(st.tab, CLASSIC);
            if (stc) {
              stc.ownerKey = st.ownerKey || "_dtMounted";
              this[st.ownerKey || "_dtMounted"] = stc;
            }
          }
          if (typeof console !== "undefined" && console.error) {
            console.error("[dt] render failed, fallback to classic (tab=" + st.tab + ", variant=" + st.entry.id + "):", e);
          }
        }
      },
      /* 宿主定位: 四页签 = data-dt-host="<tab>"; 流量页签双宿主 data-dt-host="traffic-pre|post" */
      _dtFindHost(tab, entry) {
        var root = document.querySelector(".drawer");
        if (!root) return null;
        var name = tab === "traffic" ? "traffic-" + entry.slot : tab;
        return root.querySelector('.dt-host[data-dt-host="' + name + '"]');
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
        try { st.host.replaceChildren(); } catch (e2) { /* host 已不在 DOM */ }
      },
    },
  };
  /* R2 对外暴露: 门常量与合并对(右键菜单/守阵/数据供给共用, 不抄第二份) */
  window.AQB_DRAWER_TPL_REG.mergeMinWidth = DT_MERGE_MIN_WIDTH;
  window.AQB_DRAWER_TPL_REG.mergePairs = MERGE_PAIRS;
  window.AQB_DRAWER_TPL_REG.mergeValues = MERGE_VALUES.slice();
})();
