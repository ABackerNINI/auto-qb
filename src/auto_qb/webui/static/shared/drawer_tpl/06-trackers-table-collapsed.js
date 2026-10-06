/* auto-qb WEB UI · 详情面板 trackers 页签变体 06「增强表格(收起改良)」(计划 26-10-06-0838 S3)
 *
 * 设计稿: resources/detail-panel-templates/06-trackers-table-collapsed.html(collapsed 档;
 * 收起/矮/高三档语义全部收进本变体 —— 收起 = 本变体 summary() 供给 44px 头部健康比例条,
 * 矮/高 = 增强表格自适应滚动)。
 * 数据: /trackers qB 透传(drawer.trackers, 5s 轮询) + detail.reannounce_in(仅 06 授权按 P-02
 * 以全局值近似逐行汇报倒计时, 行内标「全局」; 微条比例 = reannounce_in / reannounce, 后者
 * 缺失整条省略 —— 不造 per-tracker 假数据)。状态色点 / tier / num_downloaded 透传即有(渐进);
 * msg 行内点击展开全文; 「仅看异常」过滤聚焦 警告/更新中/失败 行。
 * 状态分桶(纯数值判据, 不复刻经典链文案单点): status 2=正常 3=更新中 4=失败 1=警告(未连接)
 * 0/虚拟=未启用 —— qB 的 4(not working)在经典链只显「未连接」, 行语义按设计稿提到失败档。
 * 动作: 添加/编辑/删除(trackerAdd/Edit/Remove)、强制汇报(drawerCmd("reannounce")), 虚拟行无动作。
 * 渲染纪律: dtHtml 全量转义(dtRaw 只用于拼接本变体 dtHtml 产出的预转义片段), replaceChildren
 * 原子换帧, 数据未变(整份 trackers + 汇报倒计时序列化比对)跳过重建, 滚动位置/过滤/msg 展开态自保。
 * 自包含: 删除本文件 + 三份 index.html 各去 1 行 manifest 即整体退役, 其它零接触。
 */
(function () {
  "use strict";
  const reg = window.AQB_DRAWER_TPL_REG;
  if (!reg) return; /* 核心未载入(清单序错): 静默退出, 守阵会抓 */
  const T = reg.dtHtml;
  const R = reg.dtRaw;

  /* 状态分桶 -> 文案与排序权值(异常置顶; 虚拟恒排最后) */
  const BUCKET = {
    err: { text: "失败", sev: 0 },
    warn: { text: "警告", sev: 1 },
    upd: { text: "更新中", sev: 2 },
    ok: { text: "正常", sev: 3 },
    off: { text: "未启用", sev: 9 },
  };

  /* 视图偏好(跨重渲染与换种子保持): 仅看异常 / msg 展开集合; lastSig 供跳过重建 */
  const ui = { onlyBad: false, openMsg: {}, lastSig: "" };

  const CSS = [
    /* 工具条 */
    ".drawer .dt06-toolbar { display:flex; align-items:center; gap:10px; margin-bottom:8px; }",
    ".drawer .dt06-note { font-size:11.5px; color:var(--fg-dim); }",
    ".drawer .dt06-toggle { display:inline-flex; align-items:center; gap:6px; height:24px; padding:0 10px;",
    "  border-radius:var(--radius-sm); border:1px solid var(--border-soft); background:var(--surface-1);",
    "  font-size:11.5px; color:var(--fg-muted); cursor:pointer; user-select:none;",
    "  transition:border-color var(--dur) var(--ease), background var(--dur) var(--ease), color var(--dur) var(--ease); }",
    ".drawer .dt06-toggle:hover { border-color:var(--border-strong); color:var(--fg); }",
    ".drawer .dt06-toggle.active { background:var(--bg-hover); border-color:var(--error-line); color:var(--fg); }",
    ".drawer .dt06-toggle i { width:6px; height:6px; border-radius:50%; background:var(--fg-dim); }",
    ".drawer .dt06-toggle.active i { background:var(--error); }",
    ".drawer .dt06-spacer { flex:1; }",
    ".drawer .dt06-add { display:inline-flex; align-items:center; gap:5px; height:26px; padding:0 11px;",
    "  border:1px solid var(--accent); border-radius:var(--radius-sm); background:var(--accent);",
    "  color:var(--bg-card); font-size:11.5px; font-weight:600; cursor:pointer; user-select:none;",
    "  transition:background var(--dur) var(--ease), border-color var(--dur) var(--ease); }",
    ".drawer .dt06-add:hover { background:var(--accent-hi); border-color:var(--accent-hi); }",
    /* 表格(grid 行制; 空态 / 表头 sticky 交给 .drawer-body 滚动容器) */
    ".drawer .dt06-table { display:flex; flex-direction:column; }",
    ".drawer .dt06-table.only-bad .dt06-r[data-benign=\"1\"] { display:none; }",
    ".drawer .dt06-r { display:grid; grid-template-columns:84px minmax(0, 1fr) 44px 78px 78px 70px 122px 84px;",
    "  gap:10px; align-items:center; min-height:38px; padding:4px 8px; border-bottom:1px solid var(--hairline);",
    "  border-radius:var(--radius-sm); }",
    ".drawer .dt06-r.head { min-height:30px; background:var(--bg-card); border-bottom:1px solid var(--border);",
    "  color:var(--fg-dim); font-size:11.5px; }",
    ".drawer .dt06-r:not(.head):hover { background:var(--bg-hover); }",
    ".drawer .dt06-r.err { background:var(--error-soft); }",
    ".drawer .dt06-r.err:hover { box-shadow:inset 0 0 0 1px var(--error-line); }",
    ".drawer .dt06-r.off { opacity:.62; }",
    ".drawer .dt06-r.off:hover { opacity:1; }",
    ".drawer .dt06-num { text-align:right; }",
    /* 状态点 */
    ".drawer .dt06-st { display:flex; align-items:center; gap:6px; font-size:12px; font-weight:600; white-space:nowrap; }",
    ".drawer .dt06-st i { width:7px; height:7px; border-radius:50%; flex:none; }",
    ".drawer .dt06-st.ok { color:var(--green); } .drawer .dt06-st.ok i { background:var(--green); }",
    ".drawer .dt06-st.warn { color:var(--warn); } .drawer .dt06-st.warn i { background:var(--warn); }",
    ".drawer .dt06-st.upd { color:var(--blue); } .drawer .dt06-st.upd i { background:var(--blue); }",
    ".drawer .dt06-st.err { color:var(--error); } .drawer .dt06-st.err i { background:var(--error); }",
    ".drawer .dt06-st.off { color:var(--fg-muted); font-weight:400; } .drawer .dt06-st.off i { background:var(--border-strong); }",
    ".drawer .dt06-st .pulse { animation:dt06-pulse 1.6s var(--ease) infinite; }",
    ".drawer .dt06-next-upd .pulse { animation:dt06-pulse 1.6s var(--ease) infinite; }",
    /* host + msg 展开格 */
    ".drawer .dt06-cell { min-width:0; display:flex; flex-direction:column; gap:2px; }",
    ".drawer .dt06-host { font-family:var(--font-mono, ui-monospace, monospace); font-size:12.5px; color:var(--fg);",
    "  overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }",
    ".drawer .dt06-r.off .dt06-host { color:var(--fg-muted); }",
    ".drawer .dt06-msg { align-self:flex-start; max-width:100%; display:block; font-size:11px; line-height:1.6;",
    "  color:var(--fg-muted); overflow:hidden; text-overflow:ellipsis; white-space:nowrap; cursor:pointer;",
    "  border:1px dashed transparent; border-radius:var(--radius-sm); }",
    ".drawer .dt06-msg:hover { text-decoration:underline; text-underline-offset:2px; }",
    ".drawer .dt06-msg.open { white-space:normal; overflow:visible; cursor:default; padding:4px 9px; margin:1px 0 2px;",
    "  background:var(--bg-sunken); border-color:var(--border-soft); text-decoration:none; }",
    ".drawer .dt06-r.warn .dt06-msg { color:var(--warn); }",
    ".drawer .dt06-r.warn .dt06-msg.open { background:var(--warn-soft); border-color:var(--warn-line); }",
    ".drawer .dt06-r.err .dt06-msg { color:var(--fg); font-family:var(--font-mono, ui-monospace, monospace); }",
    ".drawer .dt06-r.err .dt06-msg.open { background:var(--bg-sunken); border-color:var(--error-line); }",
    ".drawer .dt06-r.ok .dt06-msg { color:var(--fg-dim); }",
    /* 数值列 */
    ".drawer .dt06-v { font-family:var(--font-mono, ui-monospace, monospace); font-size:12px; color:var(--fg);",
    "  min-width:0; white-space:nowrap; }",
    ".drawer .dt06-v.z { color:var(--fg-dim); }",
    ".drawer .dt06-tier { font-family:var(--font-mono, ui-monospace, monospace); font-size:11px; color:var(--fg-dim);",
    "  text-align:right; white-space:nowrap; }",
    /* 下次汇报列: 全局近似值 + 微条比例 */
    ".drawer .dt06-next { display:flex; flex-direction:column; gap:3px; min-width:0; align-items:flex-end; }",
    ".drawer .dt06-next b { font-family:var(--font-mono, ui-monospace, monospace); font-weight:600; font-size:12px; color:var(--fg); }",
    ".drawer .dt06-next .dt06-gb { font-size:10px; color:var(--fg-dim); border:1px solid var(--border-soft);",
    "  border-radius:var(--radius-sm); padding:0 4px; font-family:var(--font-mono, ui-monospace, monospace); }",
    ".drawer .dt06-tbar { display:block; width:100%; height:3px; border-radius:999px; background:var(--bg-sunken); overflow:hidden; }",
    ".drawer .dt06-tbar i { display:block; height:100%; border-radius:999px; background:var(--accent); }",
    ".drawer .dt06-next-upd { display:flex; align-items:center; gap:5px; font-size:11.5px; color:var(--blue); white-space:nowrap; }",
    ".drawer .dt06-next-upd i { width:6px; height:6px; border-radius:50%; background:var(--blue); }",
    ".drawer .dt06-none { text-align:right; font-family:var(--font-mono, ui-monospace, monospace); font-size:12px; color:var(--fg-dim); }",
    /* 行内动作 */
    ".drawer .dt06-ops { display:flex; gap:2px; justify-content:flex-end; opacity:.5; transition:opacity var(--dur) var(--ease); }",
    ".drawer .dt06-r:hover .dt06-ops { opacity:1; }",
    ".drawer .dt06-act { display:inline-flex; align-items:center; justify-content:center; width:22px; height:22px;",
    "  padding:0; border:0; border-radius:var(--radius-sm); background:transparent; color:var(--fg-dim); cursor:pointer;",
    "  transition:color var(--dur) var(--ease), background var(--dur) var(--ease); }",
    ".drawer .dt06-act:hover { color:var(--fg); background:var(--bg-hover); }",
    ".drawer .dt06-ops.dim { justify-content:center; font-family:var(--font-mono, ui-monospace, monospace);",
    "  color:var(--fg-dim); font-size:12px; }",
    /* 空态 */
    ".drawer .dt06-empty { padding:22px 0; display:flex; align-items:center; justify-content:center; gap:8px;",
    "  color:var(--fg-dim); font-size:12.5px; }",
    /* 收起态摘要(核心以 v-html 消费) */
    ".drawer .dt06-cs { display:inline-flex; align-items:center; gap:8px; max-width:100%; overflow:hidden; }",
    ".drawer .dt06-cs .hbar { flex:none; display:inline-flex; width:96px; height:6px; border-radius:999px;",
    "  overflow:hidden; background:var(--bg-sunken); }",
    ".drawer .dt06-cs .hbar i { display:block; height:100%; }",
    ".drawer .dt06-cs .hb-ok { background:var(--green); }",
    ".drawer .dt06-cs .hb-warn { background:var(--warn); }",
    ".drawer .dt06-cs .hb-upd { background:var(--blue); }",
    ".drawer .dt06-cs .hb-err { background:var(--error); }",
    ".drawer .dt06-cs b { font-family:var(--font-mono, ui-monospace, monospace); font-weight:600; color:var(--fg); }",
    ".drawer .dt06-cs .is-err { color:var(--error); }",
  ].join("\n") + "\n@keyframes dt06-pulse { 0%, 100% { opacity: 1; } 50% { opacity: .35; } }";

  /* ---------------- 分桶 / 计数 ---------------- */
  function bucketOf(ctx, t) {
    if (ctx.drawerTrackerVirtual(t.url)) return "off";
    const s = Number(t.status);
    if (s === 2) return "ok";
    if (s === 3) return "upd";
    if (s === 4) return "err";
    if (s === 1) return "warn";
    return "off"; /* 0 = 未启用(非虚拟也按此档) */
  }

  function countsOf(ctx, trackers) {
    const n = { ok: 0, warn: 0, upd: 0, err: 0, off: 0 };
    for (const t of trackers) n[bucketOf(ctx, t)]++;
    return n;
  }

  const num = (v) => v !== undefined && v !== null && Number(v) >= 0;
  const hostOf = (url) => {
    try {
      return new URL(String(url)).host || String(url);
    } catch (e) {
      return String(url || "");
    }
  };

  /* P-02(拍板): 逐 tracker 汇报倒计时缺 per-tracker 口径 —— 以 detail.reannounce_in 全局值
   * 近似展示并标「全局」; 微条比例 = reannounce_in / reannounce(后者缺失/非正整条省略);
   * detail 未落袋显示「—」。更新中行显「正在汇报」, 虚拟/未启用行显「—」。 */
  function nextHtml(ctx) {
    const d = (ctx.drawer && ctx.drawer.detail) || null;
    if (!d || !(d.reannounce_in > 0)) {
      return T`<span class="dt06-v z" title="汇报倒计时数据未落袋">—</span>`;
    }
    const bar = num(d.reannounce) && d.reannounce > 0 && d.reannounce_in <= d.reannounce
      ? T`<span class="dt06-tbar" title="汇报周期剩余比例"><i style="width:${(d.reannounce_in / d.reannounce * 100).toFixed(1)}%"></i></span>`
      : "";
    return T`<span class="dt06-next" title="P-02: 以种子级 detail.reannounce_in 全局值近似, 非逐 tracker 口径">
      <span><b>${ctx.fmtDuration(d.reannounce_in)}</b> <span class="dt06-gb">全局</span></span>
      ${R(bar)}
    </span>`;
  }

  function rowHtml(ctx, t, order) {
    const b = bucketOf(ctx, t);
    const bk = BUCKET[b];
    const virtual = b === "off" && ctx.drawerTrackerVirtual(t.url);
    const m = String(t.msg || "").trim();
    const open = ui.openMsg[t.url] && m;
    const stText = b === "err" ? bk.text : ctx.drawerTrackerStatus(t.status) || bk.text;
    const msg = m
      ? T`<span class="dt06-msg${open ? " open" : ""}" data-msg="${t.url}"
          title="tracker 返回的原始 msg, 点击展开 / 收起">${m}</span>`
      : "";
    const sd = ctx.fmtPeersQb(t.num_seeds, t.num_complete);
    const lc = ctx.fmtPeersQb(t.num_leeches, t.num_incomplete);
    /* benign = 「仅看异常」过滤的目标外行(正常 + 未启用) */
    const benign = b === "ok" || b === "off" ? "1" : "0";
    const next = b === "upd"
      ? T`<span class="dt06-next-upd" title="正在等待 tracker 响应"><i class="pulse"></i>正在汇报</span>`
      : (b === "off" ? T`<span class="dt06-none">—</span>` : nextHtml(ctx));
    const ops = virtual
      ? T`<span class="dt06-ops dim">—</span>`
      : T`<span class="dt06-ops">
          <button type="button" class="dt06-act" data-act="report" title="强制汇报"><svg class="ico ico-sm" viewBox="0 0 16 16"><use href="#i-refresh"></use></svg></button>
          <button type="button" class="dt06-act" data-act="edit" data-url="${t.url}" title="编辑 tracker"><svg class="ico ico-sm" viewBox="0 0 16 16"><use href="#i-pencil"></use></svg></button>
          <button type="button" class="dt06-act" data-act="del" data-url="${t.url}" title="删除 tracker"><svg class="ico ico-sm" viewBox="0 0 16 16"><use href="#i-trash"></use></svg></button>
        </span>`;
    return T`<div class="dt06-r ${b}" data-benign="${benign}" data-idx="${order}" title="${t.url}">
      <span class="dt06-st ${b}"><i class="${b === "upd" ? "pulse" : ""}"></i>${stText}</span>
      <div class="dt06-cell">
        <span class="dt06-host">${virtual ? t.url : hostOf(t.url)}</span>
        ${R(msg)}
      </div>
      <span class="dt06-tier">${num(t.tier) ? t.tier : "—"}</span>
      <span class="dt06-v num${sd ? "" : " z"}">${sd || "—"}</span>
      <span class="dt06-v num${lc ? "" : " z"}">${lc || "—"}</span>
      <span class="dt06-v num${num(t.num_downloaded) ? "" : " z"}">${num(t.num_downloaded) ? t.num_downloaded : "—"}</span>
      ${R(next)}
      ${R(ops)}
    </div>`;
  }

  function render(host, ctx) {
    const ts = (ctx.drawer && ctx.drawer.trackers) || [];
    const loading = ctx.drawer && ctx.drawer.trackersLoading;
    const d = (ctx.drawer && ctx.drawer.detail) || null;
    /* 数据未变跳过重建(含汇报倒计时: detail.reannounce_in 变了也要刷) */
    const sig = JSON.stringify(ts) + "|" + String(!!loading)
      + "|" + String(d ? d.reannounce_in : "") + "|" + String(d ? d.reannounce : "");
    if (sig === ui.lastSig && host.firstChild) return;
    ui.lastSig = sig;
    const scroller = host.parentElement;
    const scroll = scroller ? scroller.scrollTop : 0;
    if (loading && !ts.length) {
      host.replaceChildren(document.createRange().createContextualFragment(
        T`<div class="dt06-empty"><svg class="ico" viewBox="0 0 16 16"><use href="#i-hourglass"></use></svg><span>正在加载…</span></div>`));
      return;
    }
    if (!ts.length) {
      host.replaceChildren(document.createRange().createContextualFragment(
        T`<div class="dt06-empty"><span>暂无 tracker</span></div>`));
      return;
    }
    /* 排序: 异常置顶(sev 升序), 同档保 qB 原序(稳定) */
    const rows = ts.map((t, i) => ({ t, i, b: bucketOf(ctx, t) }))
      .sort((a, b2) => BUCKET[a.b].sev - BUCKET[b2.b].sev || a.i - b2.i);
    const rowsHtml = rows.map((r, k) => rowHtml(ctx, r.t, k)).join("");
    const note = d && d.reannounce_in > 0
      ? "汇报倒计时为种子级全局值(P-02 近似) · 5s 自动刷新"
      : "5s 自动刷新";
    const html = T`<div class="dt06-wrap">
      <div class="dt06-toolbar">
        <span class="dt06-note">${note}</span>
        <button type="button" class="dt06-toggle${ui.onlyBad ? " active" : ""}" data-toggle
          title="只显示 警告 / 更新中 / 失败 行, 聚焦正在拖后腿的条目"><i></i>仅看异常</button>
        <span class="dt06-spacer"></span>
        <button type="button" class="dt06-add" data-act="add"><svg class="ico ico-sm" viewBox="0 0 16 16"><use href="#i-plus"></use></svg>添加 tracker</button>
      </div>
      <div class="dt06-table${ui.onlyBad ? " only-bad" : ""}">
        <div class="dt06-r head">
          <span>状态</span>
          <span>Tracker</span>
          <span class="dt06-tier" title="tier: 汇报层级, 数值越小越优先">tier</span>
          <span class="dt06-num" title="num_seeds (num_complete)">做种</span>
          <span class="dt06-num" title="num_leeches (num_incomplete)">用户</span>
          <span class="dt06-num" title="num_downloaded: 该 tracker 报告的累计完成下载次数">完成下载</span>
          <span title="汇报倒计时(P-02: 种子级全局值近似)">下次汇报</span>
          <span class="dt06-num">操作</span>
        </div>
        ${R(rowsHtml)}
      </div>
    </div>`;
    host.replaceChildren(document.createRange().createContextualFragment(html));
    if (scroller) scroller.scrollTop = scroll;
  }

  /* ---------------- 收起态摘要: 健康比例条(实体计数为权值) ----------------
   * 比例条 + 计数; 返回已转义 HTML(核心以 v-html 消费) */
  function summary(ctx) {
    const ts = (ctx.drawer && ctx.drawer.trackers) || [];
    if (!ts.length) return T`暂无 tracker`;
    const n = countsOf(ctx, ts);
    const real = ts.length - ts.filter((t) => ctx.drawerTrackerVirtual(t.url)).length;
    const total = real || 1;
    /* 比例条段: 返回的是本变体 dtHtml 产出的预转义字符串, join 后统一 R 一次 */
    const seg = (cls, cnt) => (cnt > 0
      ? T`<i class="${cls}" style="width:${(cnt / total * 100).toFixed(1)}%"></i>`
      : "");
    const bar = [seg("hb-ok", n.ok), seg("hb-warn", n.warn), seg("hb-upd", n.upd), seg("hb-err", n.err)].join("");
    const parts = [
      T`<span>正常 <b>${n.ok}</b></span>`,
      n.warn ? T`<span>警告 <b>${n.warn}</b></span>` : "",
      n.err ? T`<span class="is-err">失败 <b>${n.err}</b></span>` : "",
      T`<span>实体 <b>${real}</b></span>`,
      ts.length - real ? T`<span>虚拟 ${ts.length - real}</span>` : "",
    ].filter(Boolean).join("");
    return T`<span class="dt06-cs" title="实体 tracker 健康构成(比例条)+ 异常计数">
      <span class="hbar">${R(bar)}</span>
      ${R(parts)}
    </span>`;
  }

  function destroy(host) {
    ui.lastSig = ""; /* 下次挂载强制整帧重建 */
    /* 宿主元素跨变体复用(同页签只有一个 data-dt-host), 换变体必须摘掉本变体的委托监听,
     * 否则新旧变体监听叠加、同一次点击被多个 handler 重复处理 */
    if (host && host.__dt06Click) {
      host.removeEventListener("click", host.__dt06Click);
      host.__dt06Click = null;
      host.__dt06Wired = false;
    }
  }

  /* 事件委托挂宿主一次(宿主元素归 Vue 所有且跨重渲染复用) */
  function wire(host) {
    if (host.__dt06Wired) return;
    host.__dt06Wired = true;
    host.__dt06Click = onClick;
    host.addEventListener("click", onClick);
  }

  function onClick(ev) {
    const h = ev.currentTarget;
    const toggle = ev.target.closest("[data-toggle]");
    if (toggle) {
      ui.onlyBad = !ui.onlyBad;
      toggle.classList.toggle("active", ui.onlyBad);
      const table = h.querySelector(".dt06-table");
      if (table) table.classList.toggle("only-bad", ui.onlyBad);
      return;
    }
    const sub = ev.target.closest("[data-msg]");
    if (sub) {
      const url = sub.getAttribute("data-msg");
      ui.openMsg[url] = !ui.openMsg[url];
      sub.classList.toggle("open");
      return;
    }
    const btn = ev.target.closest("[data-act]");
    if (!btn) return;
    const ctx = h.__dtCtx;
    const act = btn.getAttribute("data-act");
    const url = btn.getAttribute("data-url") || "";
    if (act === "add") { ctx.trackerAdd(); return; }
    if (act === "report") { ctx.drawerCmd("reannounce", null, "强制汇报"); return; }
    if (act === "edit") { ctx.trackerEdit(url); return; }
    if (act === "del") { ctx.trackerRemove(url); }
  }

  const _render = render;
  reg.register({
    id: "06", tab: "trackers",
    label: "增强表格(收起)",
    css: CSS,
    render(host, ctx) {
      wire(host);
      host.__dtCtx = ctx;
      _render(host, ctx);
    },
    summary,
    destroy,
  });
})();
