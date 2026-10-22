/* overlay_fit.js — 浮层「贴边留白 + 视口夹取」几何单点
 * --------------------------------------------------------------------------
 * issue 26-10-20-2231(refactor): 这套几何原在 6 个片段文件里手写了十几遍 —— 8px 边距
 * 6 处、12px 边距 2 处(hubAsk / speed-pop, 均无注释)、五处手写夹取, 而 menu.js 的
 * _subFitViewport 早已是子面板的钳位单点却只服务子面板。本文件把几何收编为唯一单点,
 * 边距提为参数(缺省 8px); 12px 的两处显式传参并注明原因。
 *
 * 装载序: 必须排在首个消费方 config_hub.js **之前**(见三份 index.html 的
 * tpl-manifest, 插在 fetch_low.js 之后)。消费方只在方法体(运行时)取用, 顶层取别名即可。
 *
 * 边界: 本文件只算坐标, 不碰 DOM 结构、不写样式。放置策略(上方优先 / 翻右 / 箭头 /
 * 子面板不得搬出父项)与「菜单高过视口限高可滚」兜底都不是几何, 留在各调用方 ——
 * 前者是产品决策, 后者有守阵钉着(ui_feedback.js::_menuFit)。
 *
 * 入口(纯函数, 可单测):
 *   EDGE            默认边距 8(原先每处各写一个字面 8)
 *   clampAxis       轴夹取: 理想坐标 + 浮层尺寸收进 [edge, vp - size - edge]
 *   probeRight      右缘溢出探针: 浮层左缘落在 startX(+gap) 时是否探出右缘留白外
 *   probeLeft       左缘溢出探针: 浮层右缘落在 anchorLeft(-gap) 时是否探出左缘留白外
 *   fitInViewport   组合入口: 量 el 实测尺寸(或 opts.w/h 估算)后两轴夹取 -> {x, y}
 */
(function () {
  "use strict";

  var EDGE = 8;

  /* 轴夹取: v = 理想坐标(视口系左上角), size = 该轴尺寸, vp = 视口尺寸(innerWidth/
   * innerHeight), edge = 贴边留白(缺省 EDGE)。浮层比可用空间还大时贴上缘(留白优先,
   * 尺寸兜底由调用方的限高策略负责)。与旧手写式 Math.max(edge, Math.min(v,
   * Math.max(edge, vp - size - edge))) 逐分支等价。 */
  function clampAxis(v, size, vp, edge) {
    if (edge == null) edge = EDGE;
    return Math.max(edge, Math.min(v, Math.max(edge, vp - size - edge)));
  }

  /* 右缘溢出探针: 浮层左缘 = startX + gap、宽 w 时, 右缘是否越过视口右缘的留白。
   * 覆盖旧两种手写 —— _menuOverflowsRight(左缘起算, gap=0)与 _subOverflowsRight
   * (父项右缘 + 4px 缝起算, 估宽 202)。 */
  function probeRight(startX, w, gap, edge) {
    if (gap == null) gap = 0;
    if (edge == null) edge = EDGE;
    return startX + gap + w > window.innerWidth - edge;
  }

  /* 左缘溢出探针: 浮层右缘 = anchorLeft - gap、宽 w 时, 左缘是否越过视口左缘的留白。
   * 覆盖 hubAsk 翻左后的 left < 12 判定与 _subFitViewport 的 roomLeft。 */
  function probeLeft(anchorLeft, w, gap, edge) {
    if (gap == null) gap = 0;
    if (edge == null) edge = EDGE;
    return anchorLeft - gap - w < edge;
  }

  /* 组合入口: el = 浮层元素(量 offsetWidth/offsetHeight); 传 null 表示尚未渲染的
   * 开层初值, 尺寸走 opts.w/h 估算(同 _menuPos 的常量估算口径)。 */
  function fitInViewport(el, x, y, opts) {
    opts = opts || {};
    var edge = opts.edge == null ? EDGE : opts.edge;
    var w = el ? el.offsetWidth : opts.w;
    var h = el ? el.offsetHeight : opts.h;
    return {
      x: clampAxis(x, w, window.innerWidth, edge),
      y: clampAxis(y, h, window.innerHeight, edge),
    };
  }

  window.AQB_OVERLAY_FIT = {
    EDGE: EDGE,
    clampAxis: clampAxis,
    probeRight: probeRight,
    probeLeft: probeLeft,
    fitInViewport: fitInViewport,
  };
})();
