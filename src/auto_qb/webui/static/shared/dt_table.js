/* auto-qb WEB UI · 详情面板表格内核(计划 26-10-13-0811 W1 落地)
 *
 * 背景(用户 2026-10-13 报障, 八项症状归三个根因簇):
 *   簇 A  一张表的「几列 / 每列多宽 / 怎么对齐 / 每格渲染什么」落在互不相识的几处, 且没有
 *         任何一处做一致性校验 —— 表现为表头错位、多出的横带、内容挤成一堆、对齐不一致、
 *         列名里自带方向符号再叠一个排序箭头。
 *   簇 B  两条渲染通道拼同一块画布, 表头与表身的祖先不由同一套样式作用域管理。
 *   簇 C  值更新走「通知 -> 重装配行 -> 重新渲染」, 高频小变量与低频结构更新抢同一扇门。
 *
 * 本文件是簇 A 的解: 把「几何」收成**一个出口**。W0 复核(2026-10-13)已确认 —— 变体里早就
 * 没有手搓表格(只剩槽位, 表格由共享桥渲染), 重复实际在引擎侧的四处列派生与变体侧覆盖几何
 * 的 CSS 之间。故本文件先只提供「算」的能力与「验」的能力, 不接管渲染:
 *
 *   DT.layout(cols, widths)            列数组 -> { tracks, gridTemplate, aligns, keys, count }
 *                                      轨道 / 对齐 / 列键三者在**同一个返回值**里出来,
 *                                      表头与数据行只能拿到同一份答案(簇 A 的直接解药)
 *   DT.assertLayout(headEl, rowEl, cols, tableId)  三处计数必须相等, 不等即返回问题列表
 *                                      (渲染即自查; 计划 26-11-10-0027 W2(1) 起常驻生产:
 *                                      挂载点 = 主视图根 updated(_assertLayouts) + 抽屉桥
 *                                      渲染钩子(dtAssertLayout), 不一致只 console.error)
 *   DT.checkLabels(cols)               L3 守卫: 列名是纯文案, 不许自带方向符号
 *   DT.CELLS / DT.registerCell()       单元格渲染器注册表(L2 的落点, 后续波次填充)
 *
 * !为什么对齐要随列返回而不是事后注入: 现状的对齐是按列序号生成的一份注入式样式表, 它依赖
 *   DOM 层级与列序号 —— 列集一变(隐藏一列 / 渐进列生效 / 变体换子集)规则就失配, 且失配的
 *   表现是「某一个相邻列被改了颜色或加了线」, 用户看不懂, 工具也测不出来。
 * !接线状态(计划 26-11-10-0027): W1 起 layout 是全仓表格几何单一生产者(columns_grid.
 *   _gridTemplate / columns_computed.colAlignCss 内部委托); W2 起 assertLayout 常驻生产渲染
 *   自查 —— 挂载点实证选定: 主视图四面在根实例 updated()(lifecycle.js -> _assertLayouts,
 *   ref 在场才查, 零 document 扫描), 抽屉桥九变体面在桥模板 .group-table 的 @vue:mounted /
 *   @vue:updated 钩子(dtAssertLayout, 锚内配对, 零 document 扫描)。例外清单(D4): HR 三表
 *   (hrDetail/hrWave/hrKv)与 04 卡片形态面不接 —— 由 node 电池例外清单守阵钉住
 *   (test_r4_dt_table_exception_list_geometry_guard)。
 *
 * !本文件是纯函数层: 不持有状态、不碰 DOM(断言函数只读 DOM)、不引用 app.js 的常量
 *   (装载序: 本文件排在 app.js 之前, 模块级读不到那些 const; 需要列定义时由调用方传入)。
 * !注释里不得出现星号斜杠序列(既有的 CSS/JS 注释终止符坑, 会静默吞掉后续内容)。
 */
(function () {
  "use strict";

  /* L3 守卫用的方向符号集合: 箭头族 + 几何图形箭头 + 杂项箭头 + 三角。
   * 列名是**文案**, 方向只能由排序态单点渲染(表壳的 .arrow), 两个来源叠加就是用户报的
   * 「密度雷达占用表头前多一个箭头」。 */
  var DT_ARROW_RE = /[\u2190-\u21FF\u25B2\u25BC\u25C0-\u25FF\u2B00-\u2BFF\u27A1\u2B05\u2B06\u2B07]/;

  /* 缺省轨道: 列定义没声明宽度时给一个均分且可收缩的轨道, 而不是固定值 —— 固定值会让
   * 面板在窄屏下横向溢出, 溢出后表头与行容器的滚动不同步(既有的横滚同步坑)。 */
  var DEFAULT_TRACK = "minmax(0, 1fr)";

  function trackOf(col, widths) {
    if (widths && widths[col.key]) return widths[col.key];
    return col.tpl || col.width || DEFAULT_TRACK;
  }

  /* 几何单一出口: 一次调用把一张表需要的几何全部算出来。
   * cols   可见列数组(顺序即列序, 与表头、行单元格同一份)
   * widths 用户固化过的宽度 map(键 = 列 key, 值 = CSS 长度); 没有就按列定义的模板
   * 返回 { tracks, gridTemplate, aligns, keys, count } —— 调用方不许自己再拼一次。 */
  function layout(cols, widths) {
    var list = Array.isArray(cols) ? cols : [];
    var tracks = [];
    var aligns = [];
    var keys = [];
    for (var i = 0; i < list.length; i++) {
      var c = list[i] || {};
      tracks.push(trackOf(c, widths));
      aligns.push(c.align || "left");
      keys.push(c.key);
    }
    return {
      tracks: tracks,
      gridTemplate: tracks.join(" "),
      aligns: aligns,
      keys: keys,
      count: tracks.length,
    };
  }

  /* 轨道串 -> 轨道数: 按**括号深度**切分。裸 split(/\s+/) 是错的 —— display:none 的表头(08
   * 分组空组/列头 CSS 隐藏面)computed 返回**指定形**(minmax(0px, 1fr) 78px ...), 一个 minmax
   * 会被空白切成两段, 10 轨实测数成 17(W2(1) 挂载首日 parity e2e 实证); 有盒表头返回已解析
   * 的 px 形态两者才一致。指定形的计数同样可信(它就是单点产出的轨道串), 故不做「无盒跳过」。
   * "none"(零轨道的 grid)计 0; repeat(N, ...) 整体计一轨 —— 单点产物不含 repeat, 真出现了
   * 计数必失配而报, 恰好把非引擎几何也兜进自查。 */
  function trackCountOf(tpl) {
    if (!tpl || tpl === "none") return 0;
    var n = 0, depth = 0, inTok = false;
    for (var i = 0; i < tpl.length; i++) {
      var ch = tpl.charAt(i);
      if (depth === 0 && /\s/.test(ch)) {
        if (inTok) { n++; inTok = false; }
        continue;
      }
      if (ch === "(") depth++;
      else if (ch === ")" && depth > 0) depth--;
      inTok = true;
    }
    if (inTok) n++;
    return n;
  }

  /* 渲染即自查(计划 26-11-10-0027 W2(1) 起常驻生产, 拍板 D3): 三处计数必须相等 —— 网格轨道数
   * / 表头格数 / 首个数据行的子格数。不相等就是「多一格 / 少一列」, 而它的视觉表现正是用户报的
   * 「速度列下方有异常横条」与「多列内容挤在一起」。这里把它变成一条看得见的问题, 而不是一堆猜。
   * tableId(可选)只进消息前缀(生产挂载点传入, 便于定位是哪张表), 不参与判据。
   * 返回问题数组(空数组 = 一致; 有问题时首行是「[tableId] 轨道 X / 列头 Y / 行格 Z vs 列数 C」
   * 摘要 —— 三方计数一次看全, 后续 per-metric 明细不动)。只读 DOM, 不改任何东西, 不抛异常
   * (调用方承诺不一致只 console.error 不打断渲染)。 */
  function assertLayout(headEl, rowEl, cols, tableId) {
    var problems = [];
    var lay = layout(cols);
    if (!headEl || !rowEl) return problems; /* 未挂载/未渲染: 不算不一致 */
    var tracks = 0;
    try {
      var tpl = (window.getComputedStyle(headEl).gridTemplateColumns || "").trim();
      tracks = trackCountOf(tpl);
    } catch (e) {
      problems.push("读取网格轨道失败: " + e);
    }
    var heads = headEl.querySelectorAll(":scope > .h-cell").length;
    var cells = rowEl.children ? rowEl.children.length : 0;
    if (tracks !== lay.count) problems.push("网格轨道数 " + tracks + " != 列数 " + lay.count);
    if (heads !== lay.count) problems.push("列头格数 " + heads + " != 列数 " + lay.count);
    if (cells !== lay.count) problems.push("数据行子格数 " + cells + " != 列数 " + lay.count);
    if (problems.length) {
      problems.unshift("[" + (tableId || "?") + "] 轨道 " + tracks + " / 列头 " + heads
        + " / 行格 " + cells + " vs 列数 " + lay.count);
    }
    return problems;
  }

  /* L3: 列名含方向符号即违规。返回违规列的 key 数组。 */
  function checkLabels(cols) {
    var list = Array.isArray(cols) ? cols : [];
    var bad = [];
    for (var i = 0; i < list.length; i++) {
      var c = list[i] || {};
      if (typeof c.label === "string" && DT_ARROW_RE.test(c.label)) bad.push(c.key);
    }
    return bad;
  }

  /* 单元格渲染器注册表(L2 的落点): 按名字登记, 查不到即报错 —— 不许「渲染空白」。
   * W1 只建接口, 具体的格渲染器在 W2 起随表格面一起接入。 */
  function registerCell(name, fn) {
    if (!name || typeof fn !== "function") throw new Error("registerCell: 需要名字与函数");
    CELLS[name] = fn;
  }
  function cellOf(name) {
    var fn = CELLS[name];
    if (!fn) throw new Error("未登记的单元格渲染器: " + name);
    return fn;
  }
  var CELLS = {};

  window.DT_TABLE = {
    layout: layout,
    assertLayout: assertLayout,
    checkLabels: checkLabels,
    registerCell: registerCell,
    cellOf: cellOf,
    CELLS: CELLS,
    DEFAULT_TRACK: DEFAULT_TRACK,
    /* 供守阵与排障用: 判定一个列名是否自带方向符号 */
    hasArrow: function (s) { return typeof s === "string" && DT_ARROW_RE.test(s); },
  };
})();
