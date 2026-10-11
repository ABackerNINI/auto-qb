/* auto-qb WEB UI · 详情面板 trackers 页签变体 06「增强表格(收起改良)」(计划 26-10-06-0838 S3)
 *
 * 设计稿: resources/detail-panel-templates/06-trackers-table-collapsed.html(collapsed 档;
 * 矮/高 = 增强表格自适应滚动。收起档(头部 44px 健康比例条, 本变体 summary() 供给)
 * 已随面板折叠状态整体移除(2026-10-09)。
 * 数据: /trackers qB 透传(drawer.trackers, 5s 轮询)。逐行汇报倒计时按 P-02 升级为真 per-tracker
 * 口径(行级 next_announce, qB 5.2+/WebAPI 2.13.0 起随 /trackers 透传, Unix epoch 秒) 减 now;
 * qB < 5.2 无该字段 → 回退种子级 detail.reannounce_in 全局近似并标「全局」; 真口径下
 * per-tracker interval 不可得(微条分母缺失), 故不画微条 —— 不造 per-tracker 假数据)。
 * 状态色点 / tier / num_downloaded 透传即有(渐进);
 * msg 行内点击展开全文; 「仅看异常」过滤聚焦 警告/更新中/失败 行。
 * 状态分桶(纯数值判据, 不复刻经典链文案单点): status 2=正常 3=更新中 4=失败 1=警告(未连接)
 * 0/虚拟=未启用 —— qB 的 4(not working)在经典链只显「未连接」, 行语义按设计稿提到失败档。
 * 动作: 添加/删除(trackerAdd/Remove)、强制重新汇报(drawerCmd("reannounce")), 虚拟行无动作。
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
  const H = reg.helpers; /* 公共骨架单点(报告 26-10-07-0845): 工具/sig 比对/滚动自保/事件挂摘 */

  /* 状态分桶 -> 文案与排序权值(异常置顶; 虚拟恒排最后) */
  const BUCKET = {
    err: { text: "未工作", sev: 0 },
    warn: { text: "未联系", sev: 1 },
    upd: { text: "更新中", sev: 2 },
    ok: { text: "工作", sev: 3 },
    off: { text: "禁用", sev: 9 },
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
    /* 下次重新汇报列: 全局近似值 + 微条比例 */
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
    /* 非活跃种子禁汇报: 重报钮置灰不可点(qB 口径)。特异性 (0,4,0) 压过 base 的 :hover(0,3,0)。 */
    ".drawer .dt06-act.is-gated, .drawer .dt06-act.is-gated:hover { color:var(--fg-dim); background:transparent; cursor:not-allowed; }",
    ".drawer .dt06-ops.dim { justify-content:center; font-family:var(--font-mono, ui-monospace, monospace);",
    "  color:var(--fg-dim); font-size:12px; }",
    /* 空态 */
    ".drawer .dt06-empty { padding:22px 0; display:flex; align-items:center; justify-content:center; gap:8px;",
    "  color:var(--fg-dim); font-size:12.5px; }",
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

  const num = (v) => v !== undefined && v !== null && Number(v) >= 0;
  const hostOf = (url) => {
    try {
      return new URL(String(url)).host || String(url);
    } catch (e) {
      return String(url || "");
    }
  };

  /* P-02(拍板升级, 2026-10-09): 逐行汇报倒计时改真 per-tracker 口径 —— 行级 next_announce
   * (qB 5.2+ 随 /trackers 透传, Unix epoch 绝对秒) 减 nowSec 得剩余; 去「全局」标; 真口径下
   * per-tracker interval 不可得, 不画微条(不造假)。!epoch 是绝对时间不是倒计时, 必须先减 now。
   * 回退: 行缺 next_announce(qB < 5.2) → 种子级 detail.reannounce_in 全局近似 + 「全局」标 +
   * 种子级微条(即旧路径)。detail 未落袋显示「—」。更新中行显「正在汇报」, 虚拟/未启用行显「—」
   * (后两者由调用方分流, 不进本函数)。 */
  function nextHtml(ctx, t, nowSec) {
    const na = t ? t.next_announce : null;
    if (num(na) && na > 0) {
      const rem = Math.max(0, Math.round(na - nowSec));
      return T`<span class="dt06-next" title="该 tracker 的下次重新汇报倒计时(行级 next_announce 真值)">
        <span><b>${ctx.fmtDuration(rem)}</b></span>
      </span>`;
    }
    const d = (ctx.drawer && ctx.drawer.detail) || null;
    if (!d || !(d.reannounce_in > 0)) {
      return T`<span class="dt06-v z" title="汇报倒计时数据未落袋">—</span>`;
    }
    const bar = num(d.reannounce) && d.reannounce > 0 && d.reannounce_in <= d.reannounce
      ? T`<span class="dt06-tbar" title="汇报周期剩余比例"><i style="width:${(d.reannounce_in / d.reannounce * 100).toFixed(1)}%"></i></span>`
      : "";
    return T`<span class="dt06-next" title="P-02 回退: qB 无 per-tracker 口径, 以种子级 detail.reannounce_in 全局值近似">
      <span><b>${ctx.fmtDuration(d.reannounce_in)}</b> <span class="dt06-gb">全局</span></span>
      ${R(bar)}
    </span>`;
  }

  function rowHtml(ctx, t, order, nowSec) {
    const b = bucketOf(ctx, t);
    const bk = BUCKET[b];
    const virtual = b === "off" && ctx.drawerTrackerVirtual(t.url);
    const m = String(t.msg || "").trim();
    const open = ui.openMsg[t.url] && m;
    const stText = b === "err" ? bk.text : ctx.drawerTrackerStatus(t.status) || bk.text;
    /* P3-4(报告 26-10-07-0542): msg 展开行纯 span 模拟控件补键盘达(role=button + tabindex) */
    const msg = m
      ? T`<span class="dt06-msg${open ? " open" : ""}" role="button" tabindex="0"
          aria-expanded="${open ? "true" : "false"}" data-msg="${t.url}"
          title="tracker 返回的原始 msg, 点击展开 / 收起">${m}</span>`
      : "";
    const sd = ctx.fmtPeersQb(t.num_seeds, t.num_complete);
    const lc = ctx.fmtPeersQb(t.num_leeches, t.num_incomplete);
    /* benign = 「仅看异常」过滤的目标外行(正常 + 未启用) */
    const benign = b === "ok" || b === "off" ? "1" : "0";
    const next = b === "upd"
      ? T`<span class="dt06-next-upd"><i class="pulse"></i>正在汇报</span>`
      : (b === "off" ? T`<span class="dt06-none">—</span>` : nextHtml(ctx, t, nowSec));
    /* 重报钮置灰判据(非活跃种子禁汇报, qB 口径; 判据单点 = decorate.js::drawerReannounceGate) */
    const rGate = ctx.drawerReannounceGate();
    const ops = virtual
      ? T`<span class="dt06-ops dim">—</span>`
      : T`<span class="dt06-ops">
          <button type="button" class="dt06-act${rGate.ok ? "" : " is-gated"}" data-act="report" title="${rGate.ok ? "强制重新汇报" : rGate.title}"><svg class="ico ico-sm" viewBox="0 0 16 16"><use href="#i-refresh"></use></svg></button>
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
    /* P3-5(报告 26-10-07-0542): fetch 失败标记 —— 失败与「真没有」在变体里不同形态 */
    const err = (ctx.drawer && ctx.drawer.trackersError) || "";
    /* 汇报倒计时基准(本机 epoch, 秒): 逐行 next_announce 是绝对时间, 减它得剩余(见 nextHtml)。
     * 计入 sig —— 时间每前进 1s 都该重算, 否则跳过重建会把倒计时冻在上一帧(粒度 = 5s 轮询)。 */
    const nowSec = Math.floor(Date.now() / 1000);
    /* 数据未变跳过重建(含汇报倒计时: 逐行 next_announce / detail.reannounce_in / nowSec 变了都要刷) */
    const sig = JSON.stringify(ts) + "|" + String(!!loading)
      + "|" + String(d ? d.reannounce_in : "") + "|" + String(d ? d.reannounce : "")
      + "|" + nowSec
      + "|" + err;
    if (H.skipUnchanged(host, ui, sig)) return;
    if (loading && !ts.length) {
      host.replaceChildren(document.createRange().createContextualFragment(
        T`<div class="dt06-empty"><svg class="ico" viewBox="0 0 16 16"><use href="#i-hourglass"></use></svg><span>正在加载…</span></div>`));
      return;
    }
    /* 错误态先于空态(P3-5): 失败且无数据不是"真的没有", 重试口径真实(本页签 5s 轮询会自动重拉) */
    if (err && !ts.length) {
      host.replaceChildren(document.createRange().createContextualFragment(
        T`<div class="dt06-empty"><svg class="ico" viewBox="0 0 16 16"><use href="#i-warn"></use></svg><span title="${err}">Tracker 列表加载失败, 将在下次自动刷新时重试</span></div>`));
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
    const rowsHtml = rows.map((r, k) => rowHtml(ctx, r.t, k, nowSec)).join("");
    /* 工具条注: 有任一行带 next_announce(qB 5.2+) = 真口径; 否则回退种子级全局近似 */
    const perTracker = ts.some((t) => num(t.next_announce) && t.next_announce > 0);
    const note = perTracker
      ? "汇报倒计时为逐 tracker 真值(qB next_announce) · 5s 自动刷新"
      : (d && d.reannounce_in > 0 ? "汇报倒计时为种子级全局值(qB 无 per-tracker 口径) · 5s 自动刷新" : "5s 自动刷新");
    const html = T`<div class="dt06-wrap">
      <div class="dt06-toolbar">
        <span class="dt06-note">${note}</span>
        <button type="button" class="dt06-toggle${ui.onlyBad ? " active" : ""}" data-toggle
          ><i></i>仅看异常</button>
        <span class="dt06-spacer"></span>
        <button type="button" class="dt06-add" data-act="add"><svg class="ico ico-sm" viewBox="0 0 16 16"><use href="#i-plus"></use></svg>添加 Tracker</button>
      </div>
      <div class="dt06-table${ui.onlyBad ? " only-bad" : ""}">
        <div class="dt06-r head">
          <span>状态</span>
          <span>Tracker</span>
          <span class="dt06-tier" title="tier: 汇报层级, 数值越小越优先">tier</span>
          <span class="dt06-num" title="num_seeds (num_complete)">种子</span>
          <span class="dt06-num" title="num_leeches (num_incomplete)">用户</span>
          <span class="dt06-num" title="num_downloaded: 该 tracker 报告的累计完成下载次数">完成下载</span>
          <span title="下次重新汇报倒计时(逐 tracker 真值 next_announce; qB 无该字段时回退种子级全局近似)">下次重新汇报</span>
          <span class="dt06-num">操作</span>
        </div>
        ${R(rowsHtml)}
      </div>
    </div>`;
    /* 纵横滚动位成对自保(表格定宽 grid 窄窗口下必有横向滚动, 整帧重建只还 scrollTop 会把
     * 用户的横向滚动位打回最左) —— 单点 helper */
    H.withScroll(host, () => {
      host.replaceChildren(document.createRange().createContextualFragment(html));
    });
  }

  

  function destroy(host) {
    ui.lastSig = ""; /* 下次挂载强制整帧重建 */
    /* 宿主元素跨变体复用(同页签只有一个 data-dt-host), 换变体必须摘掉本变体的委托监听,
     * 否则新旧变体监听叠加、同一次点击被多个 handler 重复处理 */
    H.unwireEvents(host);
  }

  /* P3-4: 纯 span 模拟控件(msg 展开行 data-msg)的键盘触发 —— Enter/Space 转发 click 委托;
   * 焦点在原生 button 等自身会发 click 的元素上时不接管(防 Enter 双重触发) */
  function onKeyDown(ev) {
    if (ev.key !== "Enter" && ev.key !== " ") return;
    if (ev.target.closest("button, input, select, textarea, a[href], summary")) return;
    if (!ev.target.closest("[data-msg]")) return;
    ev.preventDefault();
    onClick(ev);
  }

  /* 事件委托挂宿主一次(宿主元素归 Vue 所有且跨重渲染复用; 挂摘成对纪律在核心 helper) */
  function wire(host) {
    H.wireEvents(host, { click: onClick, keydown: onKeyDown });
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
    if (act === "report") { ctx.drawerCmd("reannounce", null, "强制重新汇报"); return; }
    if (act === "del") { ctx.trackerRemove(url); }
  }

  const _render = render;
  reg.register({
    id: "06", tab: "trackers",
    label: "增强表格",
    css: CSS,
    render(host, ctx) {
      wire(host);
      host.__dtCtx = ctx;
      _render(host, ctx);
    },
    destroy,
  });
})();
