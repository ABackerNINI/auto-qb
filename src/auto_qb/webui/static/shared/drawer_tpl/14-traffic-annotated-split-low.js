/* auto-qb WEB UI · 详情面板 traffic 页签变体 14「图注双栏 · 左图右解读(矮)」(计划 26-10-06-0838 S6)
 *
 * 设计稿: resources/detail-panel-templates/14-traffic-annotated-split-low.html(low 档)。
 * 边界(计划 §04): uPlot 图本体/tooltip/图例/汇总/窗口工具条全留 Vue 经典链 —— 本变体只往
 * 图后宿主(traffic-post)渲染静态解读栏, qb_traffic_chart.js 零改动。
 * 分栏几何(变体与 Vue 争 DOM 红线的处置): 不给任何 Vue 元素加类/属性 —— 布局纯 CSS:
 * :has() 探测图后宿主内有本变体解读栏(.dt14-side)时, 给 .dt-traffic-main 右侧让位 288px 并把
 * 宿主绝对定位成右栏; 宿主为空(:empty 隐藏)或换变体时自动回落经典纵列, 零残留。
 * 解读栏内容(全部前端派生, P-05 拍板: v1 静态不与图悬停联动):
 *   - 窗口合计与上下行占比(qbCurSummary, 占比条 = 上/下行字节份额);
 *   - 峰值 Top3(有采样桶按上行速率排序, 时段 + 数值 + 相对条);
 *   - 缺口事件列表(连续 null 桶游程, 起止取邻桶真值 t, 边缘游程按 interval 反推)。
 * 悬停看数值沿用图上既有 tooltip(不变)。
 * KPI 行图标(Q2, 报告 26-10-07-0542): 段一(窗口合计)三行标签前置 sprite 图标(`<use href>`
 * 静态引用, 全用 sprite 既有 symbol); 段二/段三不加 —— 峰值行已有 #N 排位标记、缺口行已有
 * 「缺口」徽章, 再叠图标属重复编码; 着色随本行值色(上/下行 -> today 令牌, 其余中性)。
 * 渲染纪律: dtHtml 全量转义, replaceChildren 原子换帧, 数据未变(qbCurData 引用浅比较)跳过重建;
 * 无监听无定时器, destroy 只作重置。
 * 自包含: 删除本文件 + 三份 index.html 各去 1 行 manifest 即整体退役, 其它零接触。
 */
(function () {
  "use strict";
  const reg = window.AQB_DRAWER_TPL_REG;
  if (!reg) return; /* 核心未载入(清单序错): 静默退出, 守阵会抓 */
  const T = reg.dtHtml;
  const R = reg.dtRaw;

  const ui = { lastData: null };

  const CSS = [
    /* 分栏: 图后宿主出现解读栏时右侧让位(纯 CSS 探测, 不碰 Vue 元素属性)。
     * .dt-traffic-main 本就是 flex 纵列(核心注入的布局等价层), 左列既有 flex/撑满规则
     * (.qb-chart flex:1)全部照旧 —— 图宽随 padding-right 收窄, 建图侧 ResizeObserver
     * 跟随重画, 无需动 qb_traffic_chart.js。 */
    ".drawer .dt-traffic-main:has(> .dt-host[data-dt-host=\"traffic-post\"] .dt14-side) {",
    "  position:relative; padding-right:296px; }",
    ".drawer .dt-traffic-main:has(> .dt-host[data-dt-host=\"traffic-post\"] .dt14-side)",
    "  > .dt-host[data-dt-host=\"traffic-post\"] {",
    "  position:absolute; top:0; right:0; bottom:0; width:288px; overflow-y:auto; }",
    /* 解读栏(设计稿 14 .t-side 形态) */
    ".drawer .dt14-side { display:flex; flex-direction:column; gap:8px; min-height:0; }",
    ".drawer .dt14-sec { flex:none; border:1px solid var(--hairline); border-radius:var(--radius);",
    "  background:var(--bg-card); padding:7px 10px 8px; }",
    ".drawer .dt14-sec h4 { margin:0 0 5px; font-size:11.5px; font-weight:600; color:var(--fg-dim);",
    "  white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }",
    /* Q1(报告 26-10-07-0542): 解读栏键值行标签在前、值紧随, 不再用 space-between 两端推开 */
    ".drawer .dt14-row { display:flex; align-items:baseline; gap:8px;",
    "  padding:1px 0; font-size:12px; }",
    ".drawer .dt14-row .k { color:var(--fg-muted); }",
    ".drawer .dt14-row .v { font-family:var(--font-mono, ui-monospace, monospace); color:var(--fg); }",
    ".drawer .dt14-row .v.is-up { color:var(--today-up); }",
    ".drawer .dt14-row .v.is-dl { color:var(--today-down); }",
    /* Q2(报告 26-10-07-0542): 段一 KPI 行标签图标(同变体 13 口径; 内联文本流保住 ellipsis) */
    ".drawer .dt14-row .k .ico { width:12px; height:12px; margin-right:5px; vertical-align:-1.5px;",
    "  color:var(--fg-dim); }",
    ".drawer .dt14-row .k .ico.is-up { color:var(--today-up); }",
    ".drawer .dt14-row .k .ico.is-dl { color:var(--today-down); }",
    ".drawer .dt14-ratio { display:flex; height:6px; border-radius:999px; overflow:hidden;",
    "  background:var(--bg-sunken); border:1px solid var(--border-soft); margin-top:4px; }",
    ".drawer .dt14-ratio i { display:block; height:100%; }",
    ".drawer .dt14-ratio .r-up { background:var(--today-up); }",
    ".drawer .dt14-ratio .r-dl { background:var(--today-down); }",
    ".drawer .dt14-pk { display:grid; grid-template-columns:18px minmax(0, 1fr) auto; gap:2px 8px;",
    "  align-items:center; padding:3px 4px; border-radius:var(--radius-sm); font-size:11.5px; }",
    ".drawer .dt14-pk:hover { background:var(--bg-hover); }",
    ".drawer .dt14-pk .rk { color:var(--fg-dim); font-family:var(--font-mono, ui-monospace, monospace); font-size:10.5px; }",
    ".drawer .dt14-pk .rg { color:var(--fg-soft); font-family:var(--font-mono, ui-monospace, monospace);",
    "  overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }",
    ".drawer .dt14-pk .pv { color:var(--today-up); font-family:var(--font-mono, ui-monospace, monospace); }",
    ".drawer .dt14-pk .pkbar { grid-column:2/4; height:3px; border-radius:999px; background:var(--bg-sunken);",
    "  overflow:hidden; display:block; }",
    ".drawer .dt14-pk .pkbar i { display:block; height:100%; background:var(--today-up); }",
    ".drawer .dt14-ev { display:flex; align-items:flex-start; gap:8px; padding:3px 4px; border-radius:var(--radius-sm);",
    "  font-size:11.5px; }",
    ".drawer .dt14-ev:hover { background:var(--bg-hover); }",
    ".drawer .dt14-badge { flex:none; display:inline-flex; align-items:center; height:17px; padding:0 7px;",
    "  border-radius:999px; font-size:10.5px; margin-top:1px; color:var(--warn);",
    "  background:var(--warn-soft); border:1px solid var(--warn-line); }",
    ".drawer .dt14-ev .et { color:var(--fg); font-family:var(--font-mono, ui-monospace, monospace); white-space:nowrap; }",
    ".drawer .dt14-ev .en { color:var(--fg-dim); min-width:0; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }",
    ".drawer .dt14-empty { font-size:11.5px; color:var(--fg-dim); padding:2px 4px; }",
    ".drawer .dt14-foot { padding:2px 4px; font-size:10.5px; color:var(--fg-dim); }",
  ].join("\n");

  function fmtIv(s) {
    if (!(s > 0)) return "—";
    if (s < 60) return (Number.isInteger(s) ? String(s) : s.toFixed(1)) + "s";
    if (s < 3600) return Math.round(s / 60) + "m";
    if (s < 86400) return Math.round(s / 3600) + "h";
    return Math.round(s / 86400) + "d";
  }

  /* 峰值 Top3: 有采样桶按上行速率降序取 3 */
  function topPeaks(pts, n) {
    const arr = [];
    for (let i = 0; i < pts.length; i++) {
      const p = pts[i];
      if (p && (p.up || 0) > 0) arr.push(p);
    }
    arr.sort((a, b) => b.up - a.up);
    return arr.slice(0, n);
  }

  /* 缺口游程: 连续 null 桶段; 起止用邻桶真值 t(边缘游程按 interval 反推, 只用于展示) */
  function gapRuns(pts, iv) {
    const runs = [];
    let i = 0;
    while (i < pts.length) {
      if (pts[i]) { i++; continue; }
      let j = i;
      while (j < pts.length && !pts[j]) j++;
      const prev = i > 0 ? pts[i - 1] : null;
      const next = j < pts.length ? pts[j] : null;
      const t0 = prev ? prev.t : (next ? next.t - (j - i) * iv : 0);
      const t1 = next ? next.t : (prev ? prev.t + (j - i) * iv : 0);
      runs.push({ len: j - i, t0, t1 });
      i = j;
    }
    return runs;
  }

  /* 段一 KPI 行标签图标(Q2, 与变体 13 同口径): sprite 既有 symbol + 值色随行 */
  function rowIco(icon, tone) {
    return T`<svg class="ico${tone ? " " + tone : ""}" viewBox="0 0 16 16"><use href="${icon}"></use></svg>`;
  }

  function render(host, ctx) {
    const d = ctx.qbCurData;
    const pts = ctx.qbCurPoints || [];
    if (!d || !pts.length) {
      host.replaceChildren();
      ui.lastData = null;
      return;
    }
    if (ui.lastData === d && host.firstChild) return;
    ui.lastData = d;
    const iv = Number((d.meta && d.meta.interval_s) || 0) || 0;
    const s = ctx.qbCurSummary || { up: 0, down: 0 };
    const total = (s.up || 0) + (s.down || 0);
    const upPct = total > 0 ? ((s.up || 0) / total) * 100 : 0;

    /* 段一: 窗口合计与占比 */
    const sec1 = T`<section class="dt14-sec">
      <h4 title="静态解读栏(前端派生; 悬停看逐桶数值请用图上 tooltip)">窗口合计(${ctx.qbCurWindow})</h4>
      <div class="dt14-row"><span class="k">${R(rowIco("#i-upload", "is-up"))}上行累计</span><span class="v is-up">${ctx.fmtSize(s.up || 0)}</span></div>
      <div class="dt14-row"><span class="k">${R(rowIco("#i-download", "is-dl"))}下行累计</span><span class="v is-dl">${ctx.fmtSize(s.down || 0)}</span></div>
      <div class="dt14-row"><span class="k">${R(rowIco("#i-percent"))}上下行占比</span><span class="v">${total > 0 ? upPct.toFixed(0) + " : " + (100 - upPct).toFixed(0) : "—"}</span></div>
      <div class="dt14-ratio" title="上行 / 下行 字节占比"><i class="r-up" style="width:${upPct.toFixed(1)}%"></i><i class="r-dl" style="width:${(100 - upPct).toFixed(1)}%"></i></div>
    </section>`;

    /* 段二: 峰值 Top3(静态, P-05: 不做悬停定位联动) */
    const tops = topPeaks(pts, 3);
    const pkRows = tops.length
      ? tops.map((p, n) => {
        const w = (p.up / tops[0].up) * 100;
        return T`<div class="dt14-pk" title="该桶上行速率峰值(时段为桶宽区间)">
          <span class="rk">#${n + 1}</span>
          <span class="rg">${ctx.fmtTs(p.t) || "—"}</span>
          <span class="pv">${ctx.fmtSpeed(p.up)}</span>
          <span class="pkbar"><i style="width:${w.toFixed(0)}%"></i></span>
        </div>`;
      }).join("")
      : T`<div class="dt14-empty">窗口内无有效采样</div>`;
    const sec2 = T`<section class="dt14-sec">
      <h4>峰值时段 Top 3</h4>${R(pkRows)}
    </section>`;

    /* 段三: 缺口事件(连续无采样游程, 最多列 4 条) */
    const runs = gapRuns(pts, iv);
    const MAX_RUNS = 4;
    const evRows = runs.length
      ? runs.slice(0, MAX_RUNS).map((r) => T`<div class="dt14-ev" title="连续无采样桶(停机 / qB 断连 / 程序未运行)">
          <span class="dt14-badge">缺口</span>
          <span class="et">${(ctx.fmtTs(r.t0) || "?") + " – " + (ctx.fmtTs(r.t1) || "?")}</span>
          <span class="en">${r.len} 桶${iv > 0 ? " · 约 " + ctx.fmtDuration(r.len * iv) : ""}</span>
        </div>`).join("") + (runs.length > MAX_RUNS
          ? T`<div class="dt14-empty">另有 ${runs.length - MAX_RUNS} 段缺口未列出</div>` : "")
      : T`<div class="dt14-empty">该窗口无缺口</div>`;
    const sec3 = T`<section class="dt14-sec">
      <h4>缺口事件</h4>${R(evRows)}
    </section>`;

    const html = T`<div class="dt14-side">
      ${R(sec1)}${R(sec2)}${R(sec3)}
      <div class="dt14-foot">${pts.length} 桶 × ${fmtIv(iv)} 采样 · 静态解读(P-05)</div>
    </div>`;
    host.replaceChildren(document.createRange().createContextualFragment(html));
  }

  reg.register({
    id: "14", tab: "traffic", slot: "post",
    label: "图注双栏",
    css: CSS,
    render,
    destroy(host) {
      ui.lastData = null; /* 下次挂载强制整帧重建 */
      if (host) host.replaceChildren();
    },
  });
})();
