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
 * 动作: 添加/删除(trackerAdd/Remove)、强制重新汇报(drawerCmd("reannounce")), 回执/toast
 * 全走现有方法链; 设计稿 foot 的「已失败/上次成功」无 per-tracker 数据源, 按渐进纪律整块省略。
 * !U3 重写(计划 26-10-12-0527, 同 U2 法): 卡片栅格重写为**引擎消费面** —— 外壳只出锚槽
 *   (anchFill 保活), 卡片行由 <aq-dt-bridge> Teleport 进锚(描述符 drawerTrackerV04: 单列
 *   满宽 + 行模型 dt04 + rowCls 卡态)。手搓 CSS order 排序退役(Q4): 分段钮经 dtSortSet
 *   直设引擎 dyn 键(R7: 模式选择语义, 非 h-cell 三态循环; 复合权值 sev*10+tier /
 *   tier*10+sev 在 _raw, 虚拟合并卡恒 95 = 原 order:95 口径), 默认 sev 升序 = 异常优先。
 *   卡片无列语义 → 列头 CSS 隐藏, 拖宽/右键隐藏不适用(Q3 记档); 筛选 pills 是版式语义
 *   → rowsFn + 反应式行更新(W5, 不再 anchTouch 换代)。
 * 渲染纪律: dtHtml 全量转义(dtRaw 只用于拼接本变体 dtHtml 产出的预转义片段), replaceChildren
 * 原子换帧, 数据未变(整份 trackers 序列化比对)跳过重建, 锚元素跨帧保活(锚被重建 = Teleport
 * 重挂 = 行抖动), 滚动位置/筛选态自保。
 * 自包含: 删除本文件 + 三份 index.html 各去 1 行 manifest 即整体退役, 其它零接触。
 */
(function () {
  "use strict";
  const reg = window.AQB_DRAWER_TPL_REG;
  if (!reg) return; /* 核心未载入(清单序错): 静默退出, 守阵会抓 */
  const T = reg.dtHtml;
  const R = reg.dtRaw;
  const H = reg.helpers; /* 公共骨架单点(报告 26-10-07-0845): 工具/sig 比对/滚动自保/事件挂摘/锚保活 */
  const TABLE_ID = "drawerTrackerV04";

  /* 状态分桶 -> 展示文案与排序权值(异常优先 = 权值升序; 虚拟恒排最后) */
  const BUCKET = {
    err: { text: "未工作", sev: 0 },
    warn: { text: "未联系", sev: 1 },
    upd: { text: "更新中", sev: 2 },
    ok: { text: "工作", sev: 3 },
    off: { text: "禁用", sev: 9 },
  };
  /* 色族说明下放到各胶囊(原挂在 .dt04-overview 容器上, 悬浮子元素时 tooltip 锚到容器
   * 中上方远离光标 —— 锚点取最内层 [data-aq-tip], title 须挂在实际悬浮的小元素上) */
  const PILLS = [
    { f: "all", text: "全部", cls: "", tip: "状态分类沿用全局状态色族" },
    { f: "ok", text: "工作", cls: "pd-ok", tip: "工作 = 绿" },
    { f: "warn", text: "未联系", cls: "pd-warn", tip: "未联系 = 黄" },
    { f: "upd", text: "更新中", cls: "pd-upd", tip: "更新中 = 蓝" },
    { f: "err", text: "未工作", cls: "pd-err", tip: "未工作 = 红" },
    { f: "off", text: "禁用", cls: "pd-off", tip: "禁用 = 中性描边" },
  ];

  /* 视图偏好(跨重渲染与换种子保持): 计数筛选; lastSig 供数据未变跳过重建。
   * !排序态已并引擎(dtSortState.drawerTrackerV04, U3) —— 手搓分段排序态退役。 */
  /* W5(计划 26-10-13-0811 L5): 筛选进反应式驱动数据 —— 桥 keyed 写补丁原行更新,
   * 不再 anchTouch 强制换代整表重挂(行抖动的旧结构)。 */
  const ui = Vue.reactive({ filter: "all", lastSig: "" });

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
    /* 卡片栅格(表格体 = 引擎行容器经桥 Teleport 进锚, U3): .group-table 变双列栅格,
     * .group-row 样成卡(只保留行级观感, 排序/换代归引擎)。align-items:stretch = 同排卡片
     * 自动等高(虚拟合并卡与其同排实体卡恒齐平; 2026-10-10 用户报障「虚拟条目卡片高度与其
     * 它的不一致」, 改回 start 即回归, 守阵 test_drawer_tpl_trackers_card_uniform_height 钉住)
     * !width:auto 必配(2026-10-12 用户报障「真实 tracker 卡与虚拟卡之间/虚拟卡后方有长空隙」
     * 根治): 引擎行容器被三皮肤经典表 CSS 继承 width:fit-content(与 min-width:100% 成对,
     * 经典 flex 列容器里靠 min-width 兜底成整行宽); 本栅格是 grid + min-width:0, fit-content
     * 直接生效 ⇒ 卡片收缩到内容宽(实测 ~330px / 695px 格), 两列卡片之间留下 ~700px 永久
     * 空洞, 且卡宽随内容漂移(实体 330 vs 虚拟 378, 违反「宽度统一」)。grid 项 width:auto
     * + 默认 justify-self:stretch 才填满栅格格。守阵双扣(静态第 4 节 + e2e 几何)钉住。 */
    ".drawer .dt04-list { display:flex; flex-direction:column; }",
    ".drawer .dt04-list .group-head { display:none; }",
    ".drawer .dt04-list .group-table { display:grid; grid-template-columns:repeat(2, minmax(0, 1fr));",
    "  gap:10px; align-items:stretch; overflow:visible; padding-bottom:0; }",
    ".drawer .dt04-list .group-row { position:relative; display:block; width:auto; min-width:0; gap:0;",
    "  padding:10px 12px 10px 16px; background:var(--bg-card); border:1px solid var(--border);",
    "  border-radius:var(--radius); box-shadow:var(--shadow-1); cursor:default;",
    "  transition:border-color var(--dur) var(--ease); }",
    ".drawer .dt04-list .group-row::before { content:\"\"; position:absolute; left:0; top:0; bottom:0; width:3px;",
    "  border-radius:var(--radius) 0 0 var(--radius); background:var(--tr-c, var(--border-strong)); }",
    ".drawer .dt04-list .group-row:hover { border-color:var(--border-strong); background:var(--bg-card); transform:none; }",
    ".drawer .dt04-list .group-row.st-ok { --tr-c:var(--green); }",
    ".drawer .dt04-list .group-row.st-warn { --tr-c:var(--warn); }",
    ".drawer .dt04-list .group-row.st-upd { --tr-c:var(--blue); }",
    ".drawer .dt04-list .group-row.st-err { --tr-c:var(--error); background:var(--error-soft); border-color:var(--error-line); }",
    ".drawer .dt04-list .group-row.st-err:hover { border-color:var(--error); }",
    ".drawer .dt04-list .group-row.st-off { --tr-c:var(--border-strong); background:transparent; border-style:dashed; box-shadow:none; }",
    /* 卡头: 状态点 + 文案 + tier + 内网徽章 + host + 行内动作(呈现归渲染器 tpl-aq-dt04-cells) */
    ".drawer .dt04-head { display:flex; align-items:center; gap:8px; min-width:0; }",
    ".drawer .dt04-dot { width:8px; height:8px; border-radius:50%; flex:none; background:var(--tr-c); }",
    ".drawer .dt04-st { flex:none; font-size:12px; font-weight:600; color:var(--tr-c); }",
    ".drawer .dt04-tier { flex:none; font-family:var(--font-mono, ui-monospace, monospace); font-size:10.5px;",
    "  color:var(--fg-dim); border:1px solid var(--border-soft); border-radius:var(--radius-sm); padding:1px 5px; }",
    ".drawer .dt04-list .group-row.st-err .dt04-tier { color:var(--fg-muted); border-color:var(--error-line); }",
    ".drawer .dt04-tag { flex:none; font-size:10.5px; color:var(--fg-muted); background:var(--surface-2);",
    "  border:1px solid var(--border-soft); border-radius:var(--radius-sm); padding:1px 6px; }",
    ".drawer .dt04-host { flex:1; min-width:0; font-family:var(--font-mono, ui-monospace, monospace); font-size:12.5px;",
    "  color:var(--fg); overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }",
    ".drawer .dt04-host.dim { color:var(--fg-dim); font-family:var(--font-mono, ui-monospace, monospace); font-size:11.5px; }",
    ".drawer .dt04-acts { display:flex; gap:2px; flex:none; opacity:.5; transition:opacity var(--dur) var(--ease); }",
    ".drawer .dt04-list .group-row:hover .dt04-acts { opacity:1; }",
    ".drawer .dt04-act { display:inline-flex; align-items:center; justify-content:center; width:22px; height:22px;",
    "  padding:0; border:0; border-radius:var(--radius-sm); background:transparent; color:var(--fg-dim); cursor:pointer;",
    "  transition:color var(--dur) var(--ease), background var(--dur) var(--ease); }",
    ".drawer .dt04-act:hover { color:var(--fg); background:var(--bg-hover); }",
    /* 非活跃种子禁汇报: 重报钮置灰不可点(qB 口径 —— 暂停/停止·排队·校验·错误时 qB 自置灰,
     * libtorrent 的 force_tracker_request 也不发)。特异性 (0,4,0) 压过 base 的 :hover(0,3,0)。 */
    ".drawer .dt04-act.is-gated, .drawer .dt04-act.is-gated:hover { color:var(--fg-dim); background:transparent; cursor:not-allowed; }",
    /* 统计行 + msg 块 */
    ".drawer .dt04-stats { display:flex; flex-wrap:wrap; gap:5px 14px; margin-top:9px; padding-top:9px;",
    "  border-top:1px solid var(--hairline); }",
    ".drawer .dt04-list .group-row.st-err .dt04-stats { border-top-color:var(--error-line); }",
    ".drawer .dt04-s { display:inline-flex; align-items:baseline; gap:5px; font-size:11.5px; color:var(--fg-muted); white-space:nowrap; }",
    ".drawer .dt04-s b { font-family:var(--font-mono, ui-monospace, monospace); font-weight:600; font-size:12px; color:var(--fg); }",
    ".drawer .dt04-s .z { color:var(--fg-dim); }",
    ".drawer .dt04-msg { margin-top:9px; font-size:11.5px; line-height:1.6; border-radius:var(--radius-sm); padding:6px 9px; }",
    ".drawer .dt04-msg.m-err { font-family:var(--font-mono, ui-monospace, monospace); color:var(--fg);",
    "  background:var(--bg-sunken); border:1px solid var(--error-line); }",
    ".drawer .dt04-msg.m-warn { color:var(--fg-soft); background:var(--warn-soft); border:1px solid var(--warn-line); }",
    ".drawer .dt04-msg.m-note { color:var(--fg-dim); background:var(--surface-1); border:1px solid var(--border-soft); }",
    /* 虚拟条目合并卡(与实体卡同占一格半宽; 无虚拟条目整卡省略) —— 与设计稿的刻意差异:
     * ①设计稿 sp2 跨全宽, 本卡取半宽与实体卡对齐(2026-10-09 用户拍板「宽度统一」);
     * ②设计稿 footer 的「qB 下 DHT/PeX/LSD 已禁用」长描述 2026-10-10 用户要求移除 —— 卡面只留
     * head + chips, 高度改由栅格 align-items:stretch 与同排实体卡齐平。 */
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

  /* ---------------- 行装配(U3: 数据判据在这里, 呈现在渲染器分片 tpl-aq-dt04-cells) ----------------
   * 行对象 = 显示值 + _raw 排序权值(复合: sev*10+tier / tier*10+sev —— 引擎 sortedDrawer
   * 消费, 分段钮 dtSortSet 选键) + 修饰字段(stats 渐进数组 / msg / 徽章) + _cls 卡态。
   * 排序由引擎做, 这里不排; 筛选是版式语义(pills), 在 rowsFn 里做。 */
  function rowOf(ctx, t, i, rGate) {
    const b = bucketOf(ctx, t);
    const bk = BUCKET[b];
    const virtual = b === "off" && ctx.drawerTrackerVirtual(t.url);
    const stText = b === "err" ? bk.text : ctx.drawerTrackerStatus(t.status) || bk.text;
    /* 统计行(渐进: num_peers / num_downloaded 缺失省略); 0 值着弱色 */
    const stats = [];
    if (b !== "off" || num(t.num_seeds)) {
      const sd = ctx.fmtPeersQb(t.num_seeds, t.num_complete);
      stats.push({ label: "种子", val: sd || "—", z: !sd, title: "num_seeds (num_complete)" });
    }
    if (b !== "off" || num(t.num_leeches)) {
      const lc = ctx.fmtPeersQb(t.num_leeches, t.num_incomplete);
      stats.push({ label: "用户", val: lc || "—", z: !lc, title: "num_leeches (num_incomplete)" });
    }
    if (num(t.num_peers)) stats.push({ label: "连接", val: String(t.num_peers), title: "num_peers: 经由该 tracker 连接的对端" });
    if (num(t.num_downloaded)) stats.push({ label: "完成下载", val: String(t.num_downloaded), suffix: "次", title: "num_downloaded: 该 tracker 报告的累计完成下载次数" });
    /* msg 块: 失败=错误框 / 警告=黄框 / 其余有 msg 则弱化备注 */
    const m = String(t.msg || "").trim();
    const msg = m && b !== "off" ? { text: m, cls: b === "err" ? "m-err" : (b === "warn" ? "m-warn" : "m-note") } : null;
    /* 排序权值: 异常优先 = sev*10+tier / 按 tier = tier*10+sev(off 恒排最后) */
    const sev = bk.sev, tierN = num(t.tier) ? Number(t.tier) : 9;
    return {
      k: "t" + i,
      kind: "card",
      url: String(t.url || ""),
      urlTitle: String(t.url || ""),
      host: hostOf(t.url),
      dim: false,
      stText,
      tier: num(t.tier) ? "T" + t.tier : null,
      lan: !virtual && LAN_RE.test(String(t.url || "")),
      gatedOk: rGate.ok,
      gatedTitle: rGate.ok ? "强制重新汇报" : rGate.title,
      stats,
      msg,
      offNote: b === "off" && !virtual,
      _raw: { sev: sev * 10 + tierN, tier: tierN * 10 + sev },
      _cls: "st-" + b,
    };
  }

  /* 虚拟条目合并卡 = rowsFn 合成行(排序权值恒 95 = 原 CSS order:95 口径) */
  function virtualRowOf(ctx, trackers) {
    const vs = trackers.filter((t) => ctx.drawerTrackerVirtual(t.url));
    if (!vs.length) return null;
    return {
      k: "__virtual__",
      kind: "virtual",
      vcount: vs.length,
      chips: vs.map((t) => String(t.url)),
      _raw: { sev: 95, tier: 95 },
      _cls: "st-off",
    };
  }

  /* 桥行来源(注册条目 rowsFn ← 根方法 dtTplRows): 实体卡(虚拟条目不进栅格) + 虚拟合并卡
   * (仅 全部/禁用 筛选下附加, 与原口径一致); 重报闸门 torrent 级判据取一次(rGate) */
  function rowsFn(ctx) {
    const ts = (ctx.drawer && ctx.drawer.trackers) || [];
    const rGate = ctx.drawerReannounceGate();
    const rows = [];
    ts.forEach((t, i) => {
      if (ctx.drawerTrackerVirtual(t.url)) return;
      const b = bucketOf(ctx, t);
      if (ui.filter !== "all" && b !== ui.filter) return;
      rows.push(rowOf(ctx, t, i, rGate));
    });
    if (ui.filter === "all" || ui.filter === "off") {
      const v = virtualRowOf(ctx, ts);
      if (v) rows.push(v);
    }
    return rows;
  }

  /* 概览条 HTML(计数胶囊 + 排序分段 + 添加钮) —— 整帧重建与数据拍原地回填共用构建器 */
  function overviewHtml(ctx, ts) {
    const n = countsOf(ctx, ts);
    const real = ts.filter((t) => !ctx.drawerTrackerVirtual(t.url)).length;
    /* 计数胶囊: 全部 = 实体条目(虚拟单列未启用类) */
    const pills = PILLS.map((p) => {
      const cnt = p.f === "all" ? real : n[p.f];
      const act = ui.filter === p.f ? " active" : "";
      const dot = p.cls ? T`<span class="pdot ${p.cls}"></span>` : T`<span class="pdot" style="background:var(--fg-dim)"></span>`;
      return T`<button type="button" class="dt04-pill${act}" data-f="${p.f}" title="${p.tip}">${R(dot)}${p.text} <b>${cnt}</b></button>`;
    }).join("");
    /* 排序分段钮(active 态读引擎 dyn 键): 手搓分段排序态退役, 直设走 dtSortSet */
    const sortKey = ctx.dtSortCell(TABLE_ID).key || "sev";
    const sortSegs = [["sev", "异常优先"], ["tier", "按 tier"]].map(([k, text]) =>
      T`<button type="button" class="dt04-seg${sortKey === k ? " active" : ""}" data-sort="${k}">${text}</button>`).join("");
    return T`${R(pills)}
        <span class="dt04-note">5s 自动刷新</span>
        <span class="dt04-spacer"></span>
        <div class="dt04-sort" role="group" aria-label="卡片排序">${R(sortSegs)}</div>
        <button type="button" class="dt04-add" data-act="add"><svg class="ico ico-sm" viewBox="0 0 16 16"><use href="#i-plus"></use></svg>添加 Tracker</button>`;
  }

  function render(host, ctx) {
    const ts = (ctx.drawer && ctx.drawer.trackers) || [];
    const loading = ctx.drawer && ctx.drawer.trackersLoading;
    /* P3-5(报告 26-10-07-0542): fetch 失败标记 —— 失败与「真没有」在变体里不同形态 */
    const err = (ctx.drawer && ctx.drawer.trackersError) || "";
    /* 结构 sig(26-10-12 用户报障根治): 只含"外壳形状"决定项(加载/失败/空态), **不含
     * trackers 数据本身**。数据拍(5s 轮询每拍必到)不整帧重建 —— 整帧重建会移动锚
     * (=表格整树重排, 80 对端实测 56-75ms longtask/拍 = 每 5s 全表卡顿闪烁, 即用户所报
     * "表格闪烁, 数据随闪烁刷新"); 行走桥响应式, 壳上计数胶囊走 paintHtml 原地回填。
     * 胶囊/排序段的 active 与显隐全在 overviewHtml 里整块重画, 无需进 sig。 */
    const sig = String(!!loading) + "|" + err + "|" + (ts.length ? "y" : "n");
    if (H.skipUnchanged(host, ui, sig)) {
      /* 数据拍: 概览条原地回填(不含锚); 列表区(锚+Teleport 表体)不动 */
      if (ts.length && !loading && !err) H.paintHtml(host, ".dt04-overview", overviewHtml(ctx, ts));
      return;
    }
    if (loading && !ts.length) {
      host.replaceChildren(document.createRange().createContextualFragment(
        T`<div class="dt04-empty"><svg class="ico" viewBox="0 0 16 16"><use href="#i-hourglass"></use></svg><span>正在加载…</span></div>`));
      return;
    }
    /* 错误态先于空态(P3-5): 失败且无数据不是"真的没有", 重试口径真实(本页签 5s 轮询会自动重拉) */
    if (err && !ts.length) {
      host.replaceChildren(document.createRange().createContextualFragment(
        T`<div class="dt04-empty"><svg class="ico" viewBox="0 0 16 16"><use href="#i-warn"></use></svg><span title="${err}">Tracker 列表加载失败, 将在下次自动刷新时重试</span></div>`));
      return;
    }
    if (!ts.length) {
      host.replaceChildren(document.createRange().createContextualFragment(
        T`<div class="dt04-empty"><span>暂无 tracker</span></div>`));
      return;
    }
    /* 表格区 = 空 slot: anchFill 把保活的锚元素替换进 slot 位, 卡片行由桥 Teleport 进锚 */
    const html = T`<div class="dt04-wrap">
      <div class="dt04-overview">${R(overviewHtml(ctx, ts))}</div>
      <div class="dt04-list"><div data-dt-anchor-slot=""></div></div>
    </div>`;
    /* 滚动位置自保(纵横成对): 滚动容器是宿主父级(.drawer-body, Vue 所有) —— 单点 helper */
    H.withScroll(host, () => {
      host.replaceChildren(document.createRange().createContextualFragment(html));
      H.anchFill(host, TABLE_ID);
    });
  }

  function onClick(ev) {
    const h = ev.currentTarget;
    const ctx = h.__dtCtx;
    const pill = ev.target.closest("[data-f]");
    if (pill) {
      ui.filter = pill.getAttribute("data-f");
      rerender(h); /* W5: 筛选态已反应式, 桥行更新自动; rerender 只为外壳 pill active 态 */
      return;
    }
    const seg = ev.target.closest("[data-sort]");
    if (seg) {
      /* 排序并引擎(U3/R7): 分段钮 = 模式选择, dtSortSet 直设 dyn 键(权值升序);
       * 行序由引擎响应式重排, 无需 anchTouch; rerender 只为刷新 active 态 */
      ctx.dtSortSet(TABLE_ID, seg.getAttribute("data-sort"), 1);
      rerender(h);
      return;
    }
    const btn = ev.target.closest("[data-act]");
    if (!btn) return;
    const act = btn.getAttribute("data-act");
    const url = btn.getAttribute("data-url") || "";
    if (act === "add") { ctx.trackerAdd(); return; }
    if (act === "report") { ctx.drawerCmd("reannounce", null, "强制重新汇报"); return; }
    if (act === "del") { ctx.trackerRemove(url); }
  }

  /* 视图偏好变化后的强制重渲染(sig 不含偏好, 置空 lastSig 即可) */
  function rerender(host) {
    ui.lastSig = "";
    const ctx = host.__dtCtx;
    if (ctx) _render(host, ctx);
  }

  /* 事件委托挂宿主一次(宿主元素归 Vue 所有且跨重渲染复用; 挂摘成对纪律在核心 helper) */
  function wire(host) {
    H.wireEvents(host, { click: onClick });
  }

  function destroy(host) {
    ui.lastSig = ""; /* 下次挂载强制整帧重建 */
    /* 宿主元素跨变体复用(同页签只有一个 data-dt-host), 换变体必须摘掉本变体的委托监听,
     * 否则新旧变体监听叠加、同一次点击被多个 handler 重复处理 */
    H.unwireEvents(host);
  }

  const _render = render;
  reg.register({
    id: "04", tab: "trackers",
    label: "状态卡片栅格",
    /* 桥声明(U3): 表格体走引擎 —— tableId 对应 app.js DRAWER_TABLE_DEFS.drawerTrackerV04,
     * rowsFn = 行来源与筛选(版式语义), 排序(分段钮 dtSortSet 直设)/换代/持久化归引擎。 */
    tableId: TABLE_ID,
    rowsFn: rowsFn,
    css: CSS,
    render(host, ctx) {
      wire(host);
      host.__dtCtx = ctx;
      _render(host, ctx);
    },
    destroy,
  });
})();
