/* auto-qb WEB UI · 详情面板 traffic 页签变体 13「图表主导 KPI 头行(高)」(计划 26-10-06-0838 S6)
 *
 * 设计稿: resources/detail-panel-templates/13-traffic-chart-led-tall.html(tall 档)。
 * 边界(计划 §04): uPlot 图本体/tooltip/图例/汇总/窗口工具条全留 Vue 经典链 —— 本变体只往
 * 图前宿主(traffic-pre)渲染一行 KPI 头行, qb_traffic_chart.js 零改动。
 * 数据(全部前端派生): 窗口累计上/下行 = qbCurSummary(totals 单点, 与经典汇总行同源);
 * 峰值上行 / 平均上行 / 采样健康(桶数·间隔·缺口·空闲)从 qbCurPoints 逐桶派生。
 * 窗口切换走经典工具条(qbSetWindow 单点, 13 档清单 QB_WINDOW_NAMES) —— 变体不自建窗口 UI。
 * 限速值(P-03 拍板: v1 省略图上虚线/斜纹注解层): 以 KPI 文字格展示, 仅单种挂点有
 * drawer.detail(up_limit/dl_limit)时出现(全局/分组无该数据, 渐进字段纪律整格省略)。
 * 渲染纪律: dtHtml 全量转义, replaceChildren 原子换帧, 数据未变(qbCurData 引用 + 限速字段
 * 浅比较)跳过重建; 无监听无定时器, destroy 只作重置。
 * KPI 图标(Q2, 报告 26-10-07-0542): 每格标签前置 sprite 图标(`<use href>` 静态引用,
 * 全用三皮肤 index.html sprite 既有 symbol, 不引入图标库/不新增资源); 着色随本格值色
 * (上/下累计格 is-up/is-dl -> today 令牌, 其余中性 fg-dim)。
 * 自包含: 删除本文件 + 三份 index.html 各去 1 行 manifest 即整体退役, 其它零接触。
 */
(function () {
  "use strict";
  const reg = window.AQB_DRAWER_TPL_REG;
  if (!reg) return; /* 核心未载入(清单序错): 静默退出, 守阵会抓 */
  const T = reg.dtHtml;
  const R = reg.dtRaw;

  /* lastData/lastKey 供浅比较跳过重建(轮询落袋的 data 是整对象替换, 引用比较即真值) */
  const ui = { lastData: null, lastKey: "" };

  const CSS = [
    /* KPI 头行: 细线分格栅格(设计稿 13 .t-kpis 形态) */
    ".drawer .dt13-kpis { display:grid; grid-template-columns:repeat(auto-fit, minmax(150px, 1fr)); gap:1px;",
    "  background:var(--hairline); border:1px solid var(--hairline); border-radius:var(--radius);",
    "  overflow:hidden; margin-bottom:8px; flex:none; }",
    ".drawer .dt13-kpi { background:var(--bg-card); padding:6px 12px 7px; display:flex; flex-direction:column;",
    "  gap:2px; min-width:0; }",
    ".drawer .dt13-kpi .k { font-size:11px; color:var(--fg-dim); white-space:nowrap; overflow:hidden;",
    "  text-overflow:ellipsis; }",
    ".drawer .dt13-kpi .v { font-family:var(--font-mono, ui-monospace, monospace); font-size:17px; line-height:1.2;",
    "  color:var(--fg); white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }",
    ".drawer .dt13-kpi .v.is-up { color:var(--today-up); }",
    ".drawer .dt13-kpi .v.is-dl { color:var(--today-down); }",
    ".drawer .dt13-kpi .s { font-size:10.5px; color:var(--fg-dim); white-space:nowrap; overflow:hidden;",
    "  text-overflow:ellipsis; }",
    /* Q2(报告 26-10-07-0542): KPI 标签图标 —— 内联在 .k 文本流里(保住 ellipsis), 尺寸/间距
     * 对齐经典链字段行口径(ico-sm 族), 着色随本格值色 */
    ".drawer .dt13-kpi .k .ico { width:12px; height:12px; margin-right:5px; vertical-align:-1.5px;",
    "  color:var(--fg-dim); }",
    ".drawer .dt13-kpi .k .ico.is-up { color:var(--today-up); }",
    ".drawer .dt13-kpi .k .ico.is-dl { color:var(--today-down); }",
  ].join("\n");

  /* 采样间隔人读形(raw 段窗可能带小数秒, 26-10-05 十进制间隔口径) */
  function fmtIv(s) {
    if (!(s > 0)) return "—";
    if (s < 60) return (Number.isInteger(s) ? String(s) : s.toFixed(1)) + "s";
    if (s < 3600) return Math.round(s / 60) + "m";
    if (s < 86400) return Math.round(s / 3600) + "h";
    return Math.round(s / 86400) + "d";
  }

  /* 逐桶派生: 只数有采样桶(cnt), null 桶计缺口(miss), 0 速率真值桶计空闲(idle) */
  function derive(ctx) {
    const pts = ctx.qbCurPoints || [];
    const meta = (ctx.qbCurData && ctx.qbCurData.meta) || {};
    let cnt = 0, miss = 0, idle = 0, upSum = 0, dlSum = 0, peak = 0, peakT = 0;
    for (const p of pts) {
      if (!p) { miss++; continue; }
      cnt++;
      const up = p.up || 0, dl = p.dl || 0;
      upSum += up;
      dlSum += dl;
      if (up > peak) { peak = up; peakT = p.t; }
      if (up === 0 && dl === 0) idle++;
    }
    return {
      cnt, miss, idle, peak, peakT,
      avgUp: cnt ? upSum / cnt : 0,
      avgDl: cnt ? dlSum / cnt : 0,
      iv: Number(meta.interval_s) || 0,
      sum: ctx.qbCurSummary,  /* 窗口累计(bytes, totals 单点; null = 尚无落袋) */
    };
  }

  /* KPI 格(Q2 补图标): icon = sprite 既有 symbol id(如 "#i-upload"); tone = "is-up"/"is-dl"
   * 随本格值色, 缺省中性 --fg-dim */
  function kpiCell(k, v, s, cls, title, icon, tone) {
    const ico = icon
      ? T`<svg class="ico${tone ? " " + tone : ""}" viewBox="0 0 16 16"><use href="${icon}"></use></svg>`
      : "";
    return T`<div class="dt13-kpi" title="${title}">
      <span class="k">${icon ? R(ico) : ""}${k}</span><span class="v${cls ? " " + cls : ""}">${v}</span><span class="s">${s}</span>
    </div>`;
  }

  /* 限速格(P-03): 单种挂点且有 detail 时展示; 0 = 不限(qB 口径, 与变体 03 同判); 缺失省略 */
  function limitCell(ctx) {
    const d = ctx.drawer.detail;
    if (!d) return "";
    const up = d.up_limit, dl = d.dl_limit;
    const known = (v) => v !== undefined && v !== null && v >= 0;
    if (!known(up) && !known(dl)) return "";
    const fmt = (v) => (v === 0 ? "不限" : known(v) ? ctx.fmtSpeed(v) : "—");
    return kpiCell("上行限速", fmt(up), "下行 " + fmt(dl), "", "限速值(站点/qB 规则; P-03: 文字展示)", "#i-turtle");
  }

  function render(host, ctx) {
    const d = ctx.qbCurData;
    if (!d || !ctx.qbCurPoints || !ctx.qbCurPoints.length) {
      host.replaceChildren();
      ui.lastData = null;
      return;
    }
    const det = ctx.drawer.detail;
    const key = [ctx.drawer.hash, det && det.up_limit, det && det.dl_limit].join("|");
    if (ui.lastData === d && ui.lastKey === key && host.firstChild) return;
    ui.lastData = d;
    ui.lastKey = key;
    const c = derive(ctx);
    const s = c.sum || { up: 0, down: 0 };
    const cells = [
      kpiCell("窗口累计上传", ctx.fmtSize(s.up || 0),
        s.down > 0 ? "相对下载 ×" + ((s.up || 0) / s.down).toFixed(1) : "窗口内无下载",
        "is-up", "窗口内上传字节累计(响应 totals 求和)", "#i-upload", "is-up"),
      kpiCell("窗口累计下载", ctx.fmtSize(s.down || 0),
        c.avgDl > 0 ? "下载均速 " + ctx.fmtSpeed(c.avgDl) : "做种窗口, 下行为 0",
        "is-dl", "窗口内下载字节累计(响应 totals 求和)", "#i-download", "is-dl"),
      kpiCell("峰值上行", ctx.fmtSpeed(c.peak),
        c.peak > 0 && c.peakT ? "出现于 " + (ctx.fmtTs(c.peakT) || "—") : "—",
        "", "窗口内上行速率峰值(单桶最大值)", "#i-pulse"),
      kpiCell("平均上行", ctx.fmtSpeed(c.avgUp), "按有采样 " + c.cnt + " 桶计", "",
        "有采样桶的上行均值", "#i-gauge"),
      kpiCell("采样健康", c.cnt + " 桶",
        "间隔 " + fmtIv(c.iv) + (c.miss ? " · 缺口 " + c.miss : "") + (c.idle ? " · 空闲 " + c.idle : ""),
        "", "窗口内桶数 / 采样间隔 / 缺口与空闲桶", "#i-check-circle"),
      limitCell(ctx),
    ].join("");
    const html = T`<div class="dt13-kpis">${R(cells)}</div>`;
    host.replaceChildren(document.createRange().createContextualFragment(html));
  }

  reg.register({
    id: "13", tab: "traffic", slot: "pre",
    label: "KPI 头行",
    css: CSS,
    render,
    destroy(host) {
      ui.lastData = null; /* 下次挂载强制整帧重建 */
      if (host) host.replaceChildren();
    },
  });
})();
