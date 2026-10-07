/* auto-qb WEB UI · 详情面板 trackers 页签变体 04「健康总览计数 + 状态卡片栅格」
 * (计划 26-10-06-0838 S3)
 *
 * 设计稿: resources/detail-panel-templates/04-trackers-status-cards-tall.html(tall 档;
 * 收起/矮/高三档语义全部收进本变体 —— 收起 = 核心内置摘要条, 矮/高 = 双列卡片自适应滚动)。
 * 数据: /trackers qB 透传(drawer.trackers, 5s 轮询); 顶部计数胶囊即筛选, 卡片「异常优先 /
 * 按 tier」双排序; tier / num_peers / num_downloaded 透传即有(渐进: 缺失省略); 虚拟条目
 * (** / [DHT] / [PeX] / [LSD])沿用 drawerTrackerVirtual 判定, 合并一张弱化卡。
 * 状态分桶(纯数值判据, 不复刻经典链文案单点): status 2=正常 3=更新中 4=失败 1=警告(未连接)
 * 0/虚拟=未启用 —— qB 的 4(not working)在经典链只显「未连接」, 卡片语义按设计稿提到失败档。
 * 动作: 添加/删除(trackerAdd/Remove)、强制汇报(drawerCmd("reannounce")), 回执/toast
 * 全走现有方法链; 设计稿 foot 的「已失败/上次成功」无 per-tracker 数据源, 按渐进纪律整块省略。
 * 渲染纪律: dtHtml 全量转义(dtRaw 只用于拼接本变体 dtHtml 产出的预转义片段), replaceChildren
 * 原子换帧, 数据未变(整份 trackers 序列化比对)跳过重建, 滚动位置/筛选/排序态自保。
 * 自包含: 删除本文件 + 三份 index.html 各去 1 行 manifest 即整体退役, 其它零接触。
 */
(function () {
  "use strict";
  const reg = window.AQB_DRAWER_TPL_REG;
  if (!reg) return; /* 核心未载入(清单序错): 静默退出, 守阵会抓 */
  const T = reg.dtHtml;
  const R = reg.dtRaw;

  /* 状态分桶 -> 展示文案与排序权值(异常优先 = 权值升序; 虚拟恒排最后) */
  const BUCKET = {
    err: { text: "失败", sev: 0 },
    warn: { text: "警告", sev: 1 },
    upd: { text: "更新中", sev: 2 },
    ok: { text: "正常", sev: 3 },
    off: { text: "未启用", sev: 9 },
  };
  const PILLS = [
    { f: "all", text: "全部", cls: "" },
    { f: "ok", text: "正常", cls: "pd-ok" },
    { f: "warn", text: "警告", cls: "pd-warn" },
    { f: "upd", text: "更新中", cls: "pd-upd" },
    { f: "err", text: "失败", cls: "pd-err" },
    { f: "off", text: "未启用", cls: "pd-off" },
  ];

  /* 视图偏好(跨重渲染与换种子保持): 计数筛选 / 排序; lastSig 供数据未变跳过重建 */
  const ui = { filter: "all", sort: "sev", lastSig: "" };

  /* 视图偏好变化后的强制重渲染(sig 不含偏好, 置空 lastSig 即可) */
  function rerender(host) {
    ui.lastSig = "";
    const ctx = host.__dtCtx;
    if (ctx) render(host, ctx);
  }

  const CSS = [
    /* 总览行: 计数胶囊(即筛选) + 排序 + 添加 */
    ".drawer .dt04-overview { display:flex; align-items:center; flex-wrap:wrap; gap:7px; margin-bottom:12px; }",
    ".drawer .dt04-pill { display:inline-flex; align-items:center; gap:6px; height:26px; padding:0 10px;",
    "  border-radius:var(--radius-sm); border:1px solid var(--border-soft); background:var(--surface-1);",
    "  font-size:11.5px; color:var(--fg-muted); cursor:pointer; user-select:none;",
    "  transition:border-color var(--dur) var(--ease), background var(--dur) var(--ease), color var(--dur) var(--ease); }",
    ".drawer .dt04-pill:hover { border-color:var(--border-strong); color:var(--fg); }",
    ".drawer .dt04-pill.active { background:var(--bg-hover); border-color:var(--border-strong); color:var(--fg); }",
    ".drawer .dt04-pill .pdot { width:7px; height:7px; border-radius:50%; flex:none; background:var(--fg-dim); }",
    ".drawer .dt04-pill .pd-ok { background:var(--green); }",
    ".drawer .dt04-pill .pd-warn { background:var(--warn); }",
    ".drawer .dt04-pill .pd-upd { background:var(--blue); }",
    ".drawer .dt04-pill .pd-err { background:var(--error); }",
    ".drawer .dt04-pill .pd-off { background:var(--border-strong); }",
    ".drawer .dt04-pill b { font-family:var(--font-mono, ui-monospace, monospace); font-weight:600; font-size:11.5px; color:var(--fg); }",
    ".drawer .dt04-note { font-size:11.5px; color:var(--fg-dim); }",
    ".drawer .dt04-spacer { flex:1; }",
    ".drawer .dt04-add { display:inline-flex; align-items:center; gap:5px; height:26px; padding:0 11px;",
    "  border:1px solid var(--accent); border-radius:var(--radius-sm); background:var(--accent);",
    "  color:var(--bg-card); font-size:11.5px; font-weight:600; cursor:pointer; user-select:none;",
    "  transition:background var(--dur) var(--ease), border-color var(--dur) var(--ease); }",
    ".drawer .dt04-add:hover { background:var(--accent-hi); border-color:var(--accent-hi); }",
    ".drawer .dt04-sort { display:flex; align-items:center; gap:2px; padding:2px; background:var(--bg-sunken);",
    "  border:1px solid var(--border); border-radius:var(--radius); }",
    ".drawer .dt04-seg { border:0; background:none; padding:3px 9px; border-radius:var(--radius-sm);",
    "  font-size:11.5px; color:var(--fg-dim); cursor:pointer; }",
    ".drawer .dt04-seg:hover { color:var(--fg); }",
    ".drawer .dt04-seg.active { background:var(--bg-hover); color:var(--fg); }",
    /* 卡片栅格(双列; 异常排序用 order, 不动 DOM 顺序) */
    ".drawer .dt04-grid { display:grid; grid-template-columns:repeat(2, minmax(0, 1fr)); gap:10px; align-items:start; }",
    ".drawer .dt04-card { position:relative; min-width:0; padding:10px 12px 10px 16px; background:var(--bg-card);",
    "  border:1px solid var(--border); border-radius:var(--radius); box-shadow:var(--shadow-1);",
    "  transition:border-color var(--dur) var(--ease); }",
    ".drawer .dt04-card::before { content:\"\"; position:absolute; left:0; top:0; bottom:0; width:3px;",
    "  border-radius:var(--radius) 0 0 var(--radius); background:var(--tr-c, var(--border-strong)); }",
    ".drawer .dt04-card:hover { border-color:var(--border-strong); }",
    ".drawer .dt04-card.st-ok { --tr-c:var(--green); }",
    ".drawer .dt04-card.st-warn { --tr-c:var(--warn); }",
    ".drawer .dt04-card.st-upd { --tr-c:var(--blue); }",
    ".drawer .dt04-card.st-err { --tr-c:var(--error); background:var(--error-soft); border-color:var(--error-line); }",
    ".drawer .dt04-card.st-err:hover { border-color:var(--error); }",
    ".drawer .dt04-card.st-off { --tr-c:var(--border-strong); background:transparent; border-style:dashed; box-shadow:none; }",
    ".drawer .dt04-card.sp2 { grid-column:1 / -1; }",
    /* 卡头: 状态点 + 文案 + tier + 内网徽章 + host + 行内动作 */
    ".drawer .dt04-head { display:flex; align-items:center; gap:8px; min-width:0; }",
    ".drawer .dt04-dot { width:8px; height:8px; border-radius:50%; flex:none; background:var(--tr-c); }",
    ".drawer .dt04-st { flex:none; font-size:12px; font-weight:600; color:var(--tr-c); }",
    ".drawer .dt04-tier { flex:none; font-family:var(--font-mono, ui-monospace, monospace); font-size:10.5px;",
    "  color:var(--fg-dim); border:1px solid var(--border-soft); border-radius:var(--radius-sm); padding:1px 5px; }",
    ".drawer .dt04-card.st-err .dt04-tier { color:var(--fg-muted); border-color:var(--error-line); }",
    ".drawer .dt04-tag { flex:none; font-size:10.5px; color:var(--fg-muted); background:var(--surface-2);",
    "  border:1px solid var(--border-soft); border-radius:var(--radius-sm); padding:1px 6px; }",
    ".drawer .dt04-host { flex:1; min-width:0; font-family:var(--font-mono, ui-monospace, monospace); font-size:12.5px;",
    "  color:var(--fg); overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }",
    ".drawer .dt04-host.dim { color:var(--fg-dim); font-family:var(--font-mono, ui-monospace, monospace); font-size:11.5px; }",
    ".drawer .dt04-acts { display:flex; gap:2px; flex:none; opacity:.5; transition:opacity var(--dur) var(--ease); }",
    ".drawer .dt04-card:hover .dt04-acts { opacity:1; }",
    ".drawer .dt04-act { display:inline-flex; align-items:center; justify-content:center; width:22px; height:22px;",
    "  padding:0; border:0; border-radius:var(--radius-sm); background:transparent; color:var(--fg-dim); cursor:pointer;",
    "  transition:color var(--dur) var(--ease), background var(--dur) var(--ease); }",
    ".drawer .dt04-act:hover { color:var(--fg); background:var(--bg-hover); }",
    /* 统计行 + msg 块 */
    ".drawer .dt04-stats { display:flex; flex-wrap:wrap; gap:5px 14px; margin-top:9px; padding-top:9px;",
    "  border-top:1px solid var(--hairline); }",
    ".drawer .dt04-card.st-err .dt04-stats { border-top-color:var(--error-line); }",
    ".drawer .dt04-s { display:inline-flex; align-items:baseline; gap:5px; font-size:11.5px; color:var(--fg-muted); white-space:nowrap; }",
    ".drawer .dt04-s b { font-family:var(--font-mono, ui-monospace, monospace); font-weight:600; font-size:12px; color:var(--fg); }",
    ".drawer .dt04-s i { font-style:normal; font-family:var(--font-mono, ui-monospace, monospace); font-size:11px; color:var(--fg-dim); }",
    ".drawer .dt04-s .z { color:var(--fg-dim); }",
    ".drawer .dt04-msg { margin-top:9px; font-size:11.5px; line-height:1.6; border-radius:var(--radius-sm); padding:6px 9px; }",
    ".drawer .dt04-msg.m-err { font-family:var(--font-mono, ui-monospace, monospace); color:var(--fg);",
    "  background:var(--bg-sunken); border:1px solid var(--error-line); }",
    ".drawer .dt04-msg.m-warn { color:var(--fg-soft); background:var(--warn-soft); border:1px solid var(--warn-line); }",
    ".drawer .dt04-msg.m-note { color:var(--fg-dim); background:var(--surface-1); border:1px solid var(--border-soft); }",
    /* 虚拟条目合并卡 */
    ".drawer .dt04-vchips { display:flex; flex-wrap:wrap; gap:7px; margin-top:9px; }",
    ".drawer .dt04-vchip { font-family:var(--font-mono, ui-monospace, monospace); font-size:11.5px; color:var(--fg-muted);",
    "  background:var(--surface-1); border:1px solid var(--border-soft); border-radius:var(--radius-sm); padding:3px 9px; }",
    ".drawer .dt04-vnote { margin-top:8px; font-size:11px; color:var(--fg-dim); }",
    /* 空态 */
    ".drawer .dt04-empty { padding:22px 0; display:flex; align-items:center; justify-content:center; gap:8px;",
    "  color:var(--fg-dim); font-size:12.5px; }",
  ].join("\n");

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

  /* host 展示: 去 scheme 只留 host:port(qB 的 url 常带 passkey, 全文只在 title) */
  function hostOf(url) {
    try {
      return new URL(String(url)).host || String(url);
    } catch (e) {
      return String(url || "");
    }
  }

  /* 内网启发式(设计稿「内网」徽章; 纯展示, 渐进: 不命中不显示) */
  const LAN_RE = /^https?:\/\/(192\.168\.|10\.|172\.(1[6-9]|2\d|3[01])\.|localhost|\[?fd)/i;
  const num = (v) => v !== undefined && v !== null && Number(v) >= 0;

  function cardHtml(ctx, t, i) {
    const b = bucketOf(ctx, t);
    const bk = BUCKET[b];
    const virtual = b === "off" && ctx.drawerTrackerVirtual(t.url);
    const tier = num(t.tier) ? T`<span class="dt04-tier" title="tier: 汇报层级, 数值越小越优先">T${t.tier}</span>` : "";
    const lan = !virtual && LAN_RE.test(String(t.url || "")) ? T`<span class="dt04-tag" title="局域网 tracker, 不经过公网">内网</span>` : "";
    const acts = virtual ? "" : T`<span class="dt04-acts">
      <button type="button" class="dt04-act" data-act="report" data-url="${t.url}" title="强制汇报"><svg class="ico ico-sm" viewBox="0 0 16 16"><use href="#i-refresh"></use></svg></button>
      <button type="button" class="dt04-act" data-act="del" data-url="${t.url}" title="删除 tracker"><svg class="ico ico-sm" viewBox="0 0 16 16"><use href="#i-trash"></use></svg></button>
    </span>`;
    /* 统计行(渐进: num_peers / num_downloaded 缺失省略); 0 值着弱色, 走分支而非插值(插值会转义) */
    const stats = [];
    if (b !== "off" || num(t.num_seeds)) {
      const sd = ctx.fmtPeersQb(t.num_seeds, t.num_complete);
      stats.push(sd
        ? T`<span class="dt04-s" title="num_seeds (num_complete)">做种 <b>${sd}</b></span>`
        : T`<span class="dt04-s" title="num_seeds (num_complete)">做种 <b class="z">—</b></span>`);
    }
    if (b !== "off" || num(t.num_leeches)) {
      const lc = ctx.fmtPeersQb(t.num_leeches, t.num_incomplete);
      stats.push(lc
        ? T`<span class="dt04-s" title="num_leeches (num_incomplete)">用户 <b>${lc}</b></span>`
        : T`<span class="dt04-s" title="num_leeches (num_incomplete)">用户 <b class="z">—</b></span>`);
    }
    if (num(t.num_peers)) stats.push(T`<span class="dt04-s" title="num_peers: 经由该 tracker 连接的对端">连接 <b>${t.num_peers}</b></span>`);
    if (num(t.num_downloaded)) stats.push(T`<span class="dt04-s" title="num_downloaded: 该 tracker 报告的累计完成下载次数">完成下载 <b>${t.num_downloaded}</b> 次</span>`);
    /* msg 块: 失败=错误框 / 警告=黄框 / 其余有 msg 则弱化备注 */
    let msg = "";
    const m = String(t.msg || "").trim();
    if (m && b !== "off") {
      const cls = b === "err" ? "m-err" : (b === "warn" ? "m-warn" : "m-note");
      msg = T`<div class="dt04-msg ${cls}" title="tracker 返回的原始 msg">${m}</div>`;
    }
    const offNote = b === "off" && !virtual
      ? T`<div class="dt04-vnote" title="status = 0">该 tracker 已被 qB 禁用(状态「未启用」), 不参与汇报</div>` : "";
    const stText = b === "err" ? bk.text : ctx.drawerTrackerStatus(t.status) || bk.text;
    /* 排序权值: 异常优先 = sev*10+tier / 按 tier = tier*10+sev(off 恒排最后) */
    const sev = bk.sev, tierN = num(t.tier) ? Number(t.tier) : 9;
    const order = ui.sort === "tier" ? tierN * 10 + sev : sev * 10 + tierN;
    return T`<article class="dt04-card st-${b}" data-idx="${i}" style="order:${order}">
      <header class="dt04-head">
        <span class="dt04-dot"></span>
        <span class="dt04-st">${stText}</span>
        ${R(tier)}${R(lan)}
        <span class="dt04-host${virtual ? " dim" : ""}" title="${t.url}">${virtual ? t.url : hostOf(t.url)}</span>
        ${R(acts)}
      </header>
      ${stats.length ? R(T`<div class="dt04-stats">${R(stats.join(""))}</div>`) : ""}
      ${R(msg)}${R(offNote)}
    </article>`;
  }

  /* 虚拟条目合并卡(设计稿 sp2 弱化卡; 无虚拟条目整卡省略) */
  function virtualCardHtml(ctx, trackers) {
    const vs = trackers.filter((t) => ctx.drawerTrackerVirtual(t.url));
    if (!vs.length) return "";
    const chips = vs.map((t) => T`<span class="dt04-vchip" title="qB 合成的虚拟条目">${t.url}</span>`).join("");
    return T`<article class="dt04-card st-off sp2" title="由 qBittorrent 合成, 非真实 tracker" style="order:95">
      <header class="dt04-head">
        <span class="dt04-dot"></span>
        <span class="dt04-st">未启用 · 虚拟条目 ×${vs.length}</span>
        <span class="dt04-host dim">由 qBittorrent 合成, 非真实 tracker</span>
      </header>
      <div class="dt04-vchips">${R(chips)}</div>
      <div class="dt04-vnote">私有 tracker 种子: DHT / PeX / LSD 已由 qB 禁用, 状态恒为「未启用」, 不参与汇报</div>
    </article>`;
  }

  function render(host, ctx) {
    const ts = (ctx.drawer && ctx.drawer.trackers) || [];
    const loading = ctx.drawer && ctx.drawer.trackersLoading;
    /* P3-5(报告 26-10-07-0542): fetch 失败标记 —— 失败与「真没有」在变体里不同形态 */
    const err = (ctx.drawer && ctx.drawer.trackersError) || "";
    /* 数据未变跳过重建(5s 通知频度下不闪不丢态); 序列化比对比浅比较更强, 开销可忽略 */
    const sig = JSON.stringify(ts) + "|" + String(!!loading) + "|" + err;
    if (sig === ui.lastSig && host.firstChild) return;
    ui.lastSig = sig;
    /* 滚动位置自保: 滚动容器是宿主父级(.drawer-body, Vue 所有) —— 只读写 scrollTop 不碰结构 */
    const scroller = host.parentElement;
    const scroll = scroller ? scroller.scrollTop : 0;
    if (loading && !ts.length) {
      host.replaceChildren(document.createRange().createContextualFragment(
        T`<div class="dt04-empty"><svg class="ico" viewBox="0 0 16 16"><use href="#i-hourglass"></use></svg><span>正在加载…</span></div>`));
      return;
    }
    /* 错误态先于空态(P3-5): 失败且无数据不是"真的没有", 重试口径真实(本页签 5s 轮询会自动重拉) */
    if (err && !ts.length) {
      host.replaceChildren(document.createRange().createContextualFragment(
        T`<div class="dt04-empty"><svg class="ico" viewBox="0 0 16 16"><use href="#i-warn"></use></svg><span title="${err}">tracker 列表加载失败, 将在下次自动刷新时重试</span></div>`));
      return;
    }
    if (!ts.length) {
      host.replaceChildren(document.createRange().createContextualFragment(
        T`<div class="dt04-empty"><span>暂无 tracker</span></div>`));
      return;
    }
    const n = countsOf(ctx, ts);
    const real = ts.filter((t) => !ctx.drawerTrackerVirtual(t.url)).length;
    /* 计数胶囊: 全部 = 实体条目(虚拟单列未启用类) */
    const pills = PILLS.map((p) => {
      const cnt = p.f === "all" ? real : n[p.f];
      const act = ui.filter === p.f ? " active" : "";
      const dot = p.cls ? T`<span class="pdot ${p.cls}"></span>` : T`<span class="pdot" style="background:var(--fg-dim)"></span>`;
      return T`<button type="button" class="dt04-pill${act}" data-f="${p.f}">${R(dot)}${p.text} <b>${cnt}</b></button>`;
    }).join("");
    const sortSegs = [["sev", "异常优先"], ["tier", "按 tier"]].map(([k, text]) =>
      T`<button type="button" class="dt04-seg${ui.sort === k ? " active" : ""}" data-sort="${k}">${text}</button>`).join("");
    /* 实体卡: 虚拟条目不进栅格(合并卡另出); 筛选命中才渲染(order 排序在 CSS grid 上做) */
    const cards = [];
    ts.forEach((t, i) => {
      if (ctx.drawerTrackerVirtual(t.url)) return;
      const b = bucketOf(ctx, t);
      if (ui.filter !== "all" && b !== ui.filter) return;
      cards.push(cardHtml(ctx, t, i));
    });
    if ((ui.filter === "all" || ui.filter === "off")) cards.push(virtualCardHtml(ctx, ts));
    const body = cards.length
      ? T`<div class="dt04-grid">${R(cards.join(""))}</div>`
      : T`<div class="dt04-empty"><span>该分类下暂无 tracker</span></div>`;
    const html = T`<div class="dt04-wrap">
      <div class="dt04-overview" title="状态分类沿用全局状态色族: 正常=绿 / 警告=黄 / 更新中=蓝 / 失败=红 / 未启用=中性描边">
        ${R(pills)}
        <span class="dt04-note">5s 自动刷新</span>
        <span class="dt04-spacer"></span>
        <div class="dt04-sort" role="group" aria-label="卡片排序">${R(sortSegs)}</div>
        <button type="button" class="dt04-add" data-act="add"><svg class="ico ico-sm" viewBox="0 0 16 16"><use href="#i-plus"></use></svg>添加 tracker</button>
      </div>
      ${R(body)}
    </div>`;
    host.replaceChildren(document.createRange().createContextualFragment(html));
    if (scroller) scroller.scrollTop = scroll;
  }

  function destroy(host) {
    ui.lastSig = ""; /* 下次挂载强制整帧重建 */
    /* 宿主元素跨变体复用(同页签只有一个 data-dt-host), 换变体必须摘掉本变体的委托监听,
     * 否则新旧变体监听叠加、同一次点击被多个 handler 重复处理 */
    if (host && host.__dt04Click) {
      host.removeEventListener("click", host.__dt04Click);
      host.__dt04Click = null;
      host.__dt04Wired = false;
    }
  }

  /* 事件委托挂宿主一次(宿主元素归 Vue 所有且跨重渲染复用) */
  function wire(host) {
    if (host.__dt04Wired) return;
    host.__dt04Wired = true;
    host.__dt04Click = onClick;
    host.addEventListener("click", onClick);
  }

  function onClick(ev) {
    const h = ev.currentTarget;
    const pill = ev.target.closest("[data-f]");
    if (pill) {
      ui.filter = pill.getAttribute("data-f");
      rerender(h);
      return;
    }
    const seg = ev.target.closest("[data-sort]");
    if (seg) {
      ui.sort = seg.getAttribute("data-sort");
      rerender(h);
      return;
    }
    const btn = ev.target.closest("[data-act]");
    if (!btn) return;
    const ctx = h.__dtCtx;
    const act = btn.getAttribute("data-act");
    const url = btn.getAttribute("data-url") || "";
    if (act === "add") { ctx.trackerAdd(); return; }
    if (act === "report") { ctx.drawerCmd("reannounce", null, "强制汇报"); return; }
    if (act === "del") { ctx.trackerRemove(url); }
  }

  const _render = render;
  reg.register({
    id: "04", tab: "trackers",
    label: "状态卡片栅格",
    css: CSS,
    render(host, ctx) {
      wire(host);
      host.__dtCtx = ctx;
      _render(host, ctx);
    },
    destroy,
  });
})();
