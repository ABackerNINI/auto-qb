/* auto-qb WEB UI · 详情面板 peers 页签变体 90「表格体桥验证(stub, 测试专用)」
 * (计划 26-10-12-0527 U1; 拍板 D1 = Teleport 锚桥)
 *
 * !本变体是 **U1 spike 的桥验证 fixture**, 不是产品模板: 仅当 URL 带 `dtstub` 查询参数时
 * 才注册(生产零观感 —— 菜单选项/DOM/CSS 全部不出现), 供 e2e/手测验证「变体外壳字符串 DOM
 * 锚 → Teleport 渲染引擎表壳 + 行渲染器 → 引擎手势全通」的挂载链。
 *
 * 结构即桥契约的最小呈现(对外契约见 shared/table.js 头注「对外契约(P6)」④):
 *   ·外壳 chrome: 一行说明条(dtHtml 拼装, 本变体唯一自管 DOM);
 *   ·表格区: 只输出一个空锚 `<div data-dt-table-anchor="drawerStubV0">` —— 表壳 + 行由
 *     drawer.html 的 <aq-dt-bridge> Teleport 进来(描述符 drawerStubV0 声明 rows/rowKey/
 *     rowModel/rowProp 四件, 列 = DRAWER_PEER_COLUMNS 列子集)。
 * 渲染纪律: skipUnchanged(恒定 sig)→ 锚只建一次不随数据轮询重建 —— 这是桥变体的
 * **稳定 HTML 不变量**(锚被重建 = Teleport 重挂 = 行抖动); withScroll 自保滚动。
 * 自包含: 删除本文件 + 三份 index.html 各去 1 行 manifest 即整体退役, 其它零接触。
 */
(function () {
  "use strict";
  const reg = window.AQB_DRAWER_TPL_REG;
  if (!reg) return; /* 核心未载入(清单序错): 静默退出, 守阵会抓 */
  /* 测试门: 无 ?dtstub 查询参数不注册(生产不可见) */
  if (typeof location === "undefined" || String(location.search).indexOf("dtstub") < 0) return;

  const T = reg.dtHtml;
  const H = reg.helpers;

  const CSS = [
    ".drawer .dt90-chrome { display:flex; align-items:center; gap:8px; padding:6px 10px;",
    "  margin-bottom:8px; border:1px dashed var(--border-strong); border-radius:var(--radius-sm);",
    "  background:var(--surface-1); font-size:11.5px; color:var(--fg-muted); }",
    ".drawer .dt90-chrome b { color:var(--fg); font-size:12px; }",
    ".drawer .dt90-anchor { min-height:24px; }",
  ].join("\n");

  /* chrome + 锚: 内容恒定(sig 恒定 → skipUnchanged 跳过重建 → 锚稳定存活) */
  function render(host /*, ctx */) {
    const ui = host.__dt90Ui || (host.__dt90Ui = { lastSig: "" });
    if (H.skipUnchanged(host, ui, "stub-v1")) return;
    const html = T`
      <div class="dt90-chrome"><b>表格体桥验证</b><span>表格体由引擎经 Teleport 接管(测试变体, ?dtstub 激活)</span></div>
      <div class="dt90-anchor" data-dt-table-anchor="drawerStubV0"></div>`;
    H.withScroll(host, function () { host.innerHTML = html; });
  }

  reg.register({
    id: "stubbridge",
    tab: "peers",
    label: "桥验证(测试)",
    /* 桥声明: 表格体走引擎(D1)。tableId 对应 app.js DRAWER_TABLE_DEFS.drawerStubV0 */
    tableId: "drawerStubV0",
    css: CSS,
    render: render,
  });
})();
