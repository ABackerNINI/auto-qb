/* auto-qb WEB UI · 详情面板 traffic 页签变体 15「紧凑自适应(收起)」(计划 26-10-06-0838 S6)
 *
 * 设计稿: resources/detail-panel-templates/15-traffic-adaptive-collapsed.html(collapsed 档;
 * 收起/矮/高三档语义全部收进本变体)。三档处置:
 *   - 高档 = KPI 5 格全量(累计上/下行 / 峰值上行 / 平均上行 / 采样健康; 限速格渐进同 13);
 *   - 矮档 = KPI 收成单行(标签左值右, 副文隐藏);
 *   - 收起档 = 正文 KPI 行整体隐藏(图独占), 头部 44px 摘要条由 summary() 供给
 *     (P-06: 近 30 分钟上行迷你走势内联 SVG + 当前窗口累计上下行 + 峰值 + 窗口名)。
 * 降级机制(纯 CSS, 不量 JS): 仅当本变体 KPI 在场时把 .dt-traffic-main 声明为 size 容器
 * (:has() 探测, 不碰 Vue 元素属性), @container 按容器高三档切换 KPI 行形态 —— 随抽屉拖拽
 * /换档实时跟随, ResizeObserver 只属于图本体(经典链), 变体零 JS 参与。
 * 边界(计划 §04): uPlot 图本体/tooltip/图例/汇总/窗口工具条全留 Vue 经典链,
 * qb_traffic_chart.js 零改动; 窗口切换走经典工具条(qbSetWindow 单点)。
 * svg-chart-mapping 坑档处置: 摘要迷你走势是非交互 viewBox + preserveAspectRatio="none"
 * 拉伸形(与设计稿一致), 无鼠标取值/十字线 —— 「映射必须按渲染缩放算」的判据不适用,
 * 刻意不走几何换算; 数据面若将来加悬停必须改用逐像素映射(见坑档)。
 * 渲染纪律: dtHtml 全量转义(SVG 内层为纯数字点串, 经 dtRaw 拼接), replaceChildren 原子换帧,
 * 数据未变(qbCurData 引用 + 限速字段浅比较)跳过重建; 无监听无定时器, destroy 只作重置。
 * KPI 图标(Q2, 报告 26-10-07-0542): KPI 行每格标签前置 sprite 图标, 图形/着色与变体 13 同族
 * (sprite 既有 symbol + 值色随格); 收起摘要条不加 —— 44px 头部已有迷你走势 SVG 作视觉锚点,
 * ↑/↓ 单字符是摘要条的紧凑既有记法(与变体 03 摘要同语言), 12px 图标不增信息密度。
 * 自包含: 删除本文件 + 三份 index.html 各去 1 行 manifest 即整体退役, 其它零接触。
 */
(function () {
  "use strict";
  const reg = window.AQB_DRAWER_TPL_REG;
  if (!reg) return; /* 核心未载入(清单序错): 静默退出, 守阵会抓 */
  const T = reg.dtHtml;
  const R = reg.dtRaw;

  const ui = { lastData: null, lastKey: "" };

  const CSS = [
    /* 容器声明 + 三档降级(容器 = .dt-traffic-main; 仅本变体 KPI 在场时生效) */
    ".drawer .dt-traffic-main:has(.dt15-kpis) { container-type:size; container-name:dt15; }",
    "@container dt15 (max-height: 430px) {",
    "  .drawer .dt15-kpi { padding:3px 12px; flex-direction:row; align-items:baseline; gap:8px; }",
    "  .drawer .dt15-kpi .v { font-size:13px; flex:1; text-align:right; }",
    "  .drawer .dt15-kpi .s { display:none; }",
    "}",
    "@container dt15 (max-height: 300px) {",
    "  .drawer .dt15-kpis { display:none; }",
    "}",
    /* KPI 行(高档全量形态, 与变体 13 同族; 类名分前缀互不串扰) */
    ".drawer .dt15-kpis { display:grid; grid-template-columns:repeat(auto-fit, minmax(150px, 1fr)); gap:1px;",
    "  background:var(--hairline); border:1px solid var(--hairline); border-radius:var(--radius);",
    "  overflow:hidden; margin-bottom:8px; flex:none; }",
    ".drawer .dt15-kpi { background:var(--bg-card); padding:5px 12px 6px; display:flex; flex-direction:column;",
    "  gap:1px; min-width:0; }",
    ".drawer .dt15-kpi .k { font-size:11px; color:var(--fg-dim); white-space:nowrap; overflow:hidden;",
    "  text-overflow:ellipsis; }",
    ".drawer .dt15-kpi .v { font-family:var(--font-mono, ui-monospace, monospace); font-size:15px; line-height:1.2;",
    "  color:var(--fg); white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }",
    ".drawer .dt15-kpi .v.is-up { color:var(--today-up); }",
    ".drawer .dt15-kpi .v.is-dl { color:var(--today-down); }",
    ".drawer .dt15-kpi .s { font-size:10.5px; color:var(--fg-dim); white-space:nowrap; overflow:hidden;",
    "  text-overflow:ellipsis; }",
    /* Q2(报告 26-10-07-0542): KPI 标签图标(与变体 13 同族) —— 内联在 .k 文本流里(保住
     * ellipsis), 矮档 flex 化后 margin 仍成立; 着色随本格值色 */
    ".drawer .dt15-kpi .k .ico { width:12px; height:12px; margin-right:5px; vertical-align:-1.5px;",
    "  color:var(--fg-dim); }",
    ".drawer .dt15-kpi .k .ico.is-up { color:var(--today-up); }",
    ".drawer .dt15-kpi .k .ico.is-dl { color:var(--today-down); }",
    /* 收起摘要条内联件(44px 头部, 核心以 v-html 消费) */
    ".drawer .dt15-spark { width:118px; height:22px; flex:none; vertical-align:middle; }",
    ".drawer .dt15-spark .base { stroke:var(--border-soft); stroke-width:1; fill:none; }",
    ".drawer .dt15-spark .curve { stroke:var(--today-up); stroke-width:1.5; fill:none;",
    "  stroke-linejoin:round; stroke-linecap:round; }",
    ".drawer .dt15-cs-up { font-family:var(--font-mono, ui-monospace, monospace); color:var(--today-up); }",
    ".drawer .dt15-cs-dl { font-family:var(--font-mono, ui-monospace, monospace); color:var(--today-down); }",
    ".drawer .dt15-cs-pk { font-family:var(--font-mono, ui-monospace, monospace); color:var(--fg); }",
    ".drawer .dt15-cs-win { color:var(--fg-dim); }",
  ].join("\n");

  function fmtIv(s) {
    if (!(s > 0)) return "—";
    if (s < 60) return (Number.isInteger(s) ? String(s) : s.toFixed(1)) + "s";
    if (s < 3600) return Math.round(s / 60) + "m";
    if (s < 86400) return Math.round(s / 3600) + "h";
    return Math.round(s / 86400) + "d";
  }

  /* 逐桶派生(与变体 13 同族口径, 自包含复制) */
  function derive(ctx) {
    const pts = ctx.qbCurPoints || [];
    const meta = (ctx.qbCurData && ctx.qbCurData.meta) || {};
    let cnt = 0, miss = 0, idle = 0, upSum = 0, dlSum = 0, peak = 0;
    for (const p of pts) {
      if (!p) { miss++; continue; }
      cnt++;
      const up = p.up || 0, dl = p.dl || 0;
      upSum += up;
      dlSum += dl;
      if (up > peak) peak = up;
      if (up === 0 && dl === 0) idle++;
    }
    return {
      cnt, miss, idle, peak,
      avgUp: cnt ? upSum / cnt : 0,
      avgDl: cnt ? dlSum / cnt : 0,
      iv: Number(meta.interval_s) || 0,
      sum: ctx.qbCurSummary,
    };
  }

  /* KPI 格(Q2 补图标, 与变体 13 同族): icon = sprite 既有 symbol id; tone = "is-up"/"is-dl"
   * 随本格值色, 缺省中性 --fg-dim */
  function kpiCell(k, v, s, cls, title, icon, tone) {
    const ico = icon
      ? T`<svg class="ico${tone ? " " + tone : ""}" viewBox="0 0 16 16"><use href="${icon}"></use></svg>`
      : "";
    return T`<div class="dt15-kpi" title="${title}">
      <span class="k">${icon ? R(ico) : ""}${k}</span><span class="v${cls ? " " + cls : ""}">${v}</span><span class="s">${s}</span>
    </div>`;
  }

  /* 限速格(P-03 文字展示; 仅单种挂点有 detail, 渐进同 13) */
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
      kpiCell("峰值上行", ctx.fmtSpeed(c.peak), c.peak > 0 ? "有采样桶最大值" : "—", "",
        "窗口内上行速率峰值(单桶最大值)", "#i-pulse"),
      kpiCell("平均上行", ctx.fmtSpeed(c.avgUp), "按有采样 " + c.cnt + " 桶计", "",
        "有采样桶的上行均值", "#i-gauge"),
      kpiCell("采样健康", c.cnt + " 桶",
        "间隔 " + fmtIv(c.iv) + (c.miss ? " · 缺口 " + c.miss : "") + (c.idle ? " · 空闲 " + c.idle : ""),
        "", "窗口内桶数 / 采样间隔 / 缺口与空闲桶", "#i-check-circle"),
      limitCell(ctx),
    ].join("");
    const html = T`<div class="dt15-kpis" title="窗口 ${ctx.qbCurWindow} · 前端派生自 points/totals">${R(cells)}</div>`;
    host.replaceChildren(document.createRange().createContextualFragment(html));
  }

  /* ---------------- 收起态摘要(P-06): 近 30 分钟上行迷你走势 + 窗口累计 ----------------
   * 迷你走势取窗口尾部(采样间隔口径的 30 分钟桶数; agg 段窗桶宽 > 30 分钟时取末 12 桶近似),
   * null 桶断段(spanGaps 语义与图本体一致); 无有效采样只剩基线。 */
  function sparkInner(ctx) {
    const pts = ctx.qbCurPoints || [];
    if (!pts.length) return "";
    const iv = Number((ctx.qbCurData && ctx.qbCurData.meta && ctx.qbCurData.meta.interval_s) || 0) || 0;
    const n = iv > 0 ? Math.max(2, Math.round(1800 / iv)) : 12;
    const tail = pts.slice(Math.max(0, pts.length - n));
    let max = 0;
    for (const p of tail) if (p && (p.up || 0) > max) max = p.up || 0;
    if (!(max > 0)) max = 1;
    const W = 118, H = 22, PAD_B = 2, PAD_T = 2;
    const segs = [];
    let cur = null;
    for (let i = 0; i < tail.length; i++) {
      const p = tail[i];
      if (!p) {  /* null 桶断段 */
        if (cur && cur.length > 1) segs.push(cur.join(" "));
        cur = null;
        continue;
      }
      const x = (tail.length > 1 ? (i / (tail.length - 1)) * W : 0).toFixed(1);
      const y = (H - PAD_B - ((p.up || 0) / max) * (H - PAD_B - PAD_T)).toFixed(1);
      if (!cur) cur = [];
      cur.push(x + "," + y);
    }
    if (cur && cur.length > 1) segs.push(cur.join(" "));
    let inner = `<line class="base" x1="0" y1="${H - PAD_B}" x2="${W}" y2="${H - PAD_B}"/>`;
    for (const s2 of segs) inner += `<polyline class="curve" points="${s2}"/>`;
    return inner;
  }

  function summary(ctx) {
    const c = derive(ctx);
    const s = c.sum || { up: 0, down: 0 };
    const inner = sparkInner(ctx);
    const spark = T`<svg class="dt15-spark" viewBox="0 0 118 22" preserveAspectRatio="none" aria-hidden="true">${R(inner)}</svg>`;
    const parts = [spark,
      T`<span class="dt15-cs-up" title="当前窗口累计上传">↑ ${ctx.fmtSize(s.up || 0)}</span>`,
      T`<span class="dt15-cs-dl" title="当前窗口累计下载">↓ ${ctx.fmtSize(s.down || 0)}</span>`,
      T`<span class="dt15-cs-pk" title="当前窗口上行峰值">峰值 ${ctx.fmtSpeed(c.peak)}</span>`,
      T`<span class="dt15-cs-win">窗口 ${ctx.qbCurWindow}</span>`];
    return parts.join(' <span style="color:var(--fg-dim)">·</span> ');
  }

  reg.register({
    id: "15", tab: "traffic", slot: "pre",
    label: "自适应 KPI 行",
    css: CSS,
    render,
    summary,
    destroy(host) {
      ui.lastData = null; /* 下次挂载强制整帧重建 */
      if (host) host.replaceChildren();
    },
  });
})();
