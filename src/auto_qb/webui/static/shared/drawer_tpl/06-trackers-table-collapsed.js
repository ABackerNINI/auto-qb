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
 * !U3 重写(计划 26-10-12-0527, 同 U2 法): 表格体重写为**引擎消费面** —— 外壳只出锚槽
 *   (anchFill 保活), 8 列表壳/行渲染器由 <aq-dt-bridge> Teleport 进锚(描述符
 *   drawerTrackerV06: 原 grid 逐列转列声明 + 行模型 dt06 + dyn 排序 + rowCls 行态)。
 *   手搓固定排序退役(Q4): 默认 sev 升序 = 原口径「异常置顶, 同档保 qB 原序」(引擎稳定排序),
 *   其余列拖宽/右键隐藏/偏好持久化首次与主表同源; 「下次重新汇报」不可排(R7 记档:
 *   行级真值/种子级回退/正在汇报三态混合口径, 无单一排序原值)。仅看异常 = 外壳容器类
 *   切换(行不重装配, 与原口径同); msg 展开态 rowsFn 读取(重建后恢复)。
 * 渲染纪律: dtHtml 全量转义(dtRaw 只用于拼接本变体 dtHtml 产出的预转义片段), replaceChildren
 * 原子换帧, 数据未变(整份 trackers + 汇报倒计时序列化比对)跳过重建, 锚元素跨帧保活(锚被
 * 重建 = Teleport 重挂 = 行抖动), 滚动位置/过滤/msg 展开态自保。
 * 自包含: 删除本文件 + 三份 index.html 各去 1 行 manifest 即整体退役, 其它零接触。
 */
(function () {
  "use strict";
  const reg = window.AQB_DRAWER_TPL_REG;
  if (!reg) return; /* 核心未载入(清单序错): 静默退出, 守阵会抓 */
  const T = reg.dtHtml;
  const R = reg.dtRaw;
  const H = reg.helpers; /* 公共骨架单点(报告 26-10-07-0845): 工具/sig 比对/滚动自保/事件挂摘/锚保活 */
  const TABLE_ID = "drawerTrackerV06";

  /* 状态分桶 -> 文案与排序权值(异常置顶; 虚拟恒排最后) */
  const BUCKET = {
    err: { text: "未工作", sev: 0 },
    warn: { text: "未联系", sev: 1 },
    upd: { text: "更新中", sev: 2 },
    ok: { text: "工作", sev: 3 },
    off: { text: "禁用", sev: 9 },
  };

  /* 视图偏好(跨重渲染与换种子保持): 仅看异常 / msg 展开集合; lastSig 供跳过重建。
   * !排序态已并引擎(dtSortState.drawerTrackerV06, U3) —— 手搓固定排序退役。 */
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
    /* 表格体 = 引擎表壳 + 行渲染器经桥 Teleport 进锚(U3): 列宽/网格/排序表头归引擎,
     * 本变体只保留行级观感(行距/发丝线/状态行底色)与表头对齐个性。 */
    ".drawer .dt06-list { display:flex; flex-direction:column; }",
    ".drawer .dt06-list.only-bad .group-row.benign { display:none; }",
    ".drawer .dt06-list .group-head { min-height:30px; background:var(--bg-card);",
    "  border-bottom:1px solid var(--border); color:var(--fg-dim); font-size:11.5px; }",
    ".drawer .dt06-list .group-head .hc-tier, .drawer .dt06-list .group-head .hc-seeds,",
    ".drawer .dt06-list .group-head .hc-leeches, .drawer .dt06-list .group-head .hc-downloaded,",
    ".drawer .dt06-list .group-head .hc-ops { text-align:right; }",
    ".drawer .dt06-list .group-row { min-height:38px; padding:4px 8px; gap:10px; align-items:center;",
    "  background:transparent; border:0; border-bottom:1px solid var(--hairline);",
    "  border-radius:var(--radius-sm); box-shadow:none; }",
    ".drawer .dt06-list .group-row:hover { background:var(--bg-hover); transform:none; border-color:transparent; }",
    ".drawer .dt06-list .group-row.err { background:var(--error-soft); }",
    ".drawer .dt06-list .group-row.err:hover { background:var(--error-soft); box-shadow:inset 0 0 0 1px var(--error-line); }",
    ".drawer .dt06-list .group-row.off { opacity:.62; }",
    ".drawer .dt06-list .group-row.off:hover { opacity:1; }",
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
    /* host + msg 展开格(呈现归渲染器 tpl-aq-dt06-cells) */
    ".drawer .dt06-cell { min-width:0; display:flex; flex-direction:column; gap:2px; }",
    ".drawer .dt06-host { font-family:var(--font-mono, ui-monospace, monospace); font-size:12.5px; color:var(--fg);",
    "  overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }",
    ".drawer .dt06-list .group-row.off .dt06-host { color:var(--fg-muted); }",
    ".drawer .dt06-msg { align-self:flex-start; max-width:100%; display:block; font-size:11px; line-height:1.6;",
    "  color:var(--fg-muted); overflow:hidden; text-overflow:ellipsis; white-space:nowrap; cursor:pointer;",
    "  border:1px dashed transparent; border-radius:var(--radius-sm); }",
    ".drawer .dt06-msg:hover { text-decoration:underline; text-underline-offset:2px; }",
    ".drawer .dt06-msg.open { white-space:normal; overflow:visible; cursor:default; padding:4px 9px; margin:1px 0 2px;",
    "  background:var(--bg-sunken); border-color:var(--border-soft); text-decoration:none; }",
    ".drawer .dt06-list .group-row.warn .dt06-msg { color:var(--warn); }",
    ".drawer .dt06-list .group-row.warn .dt06-msg.open { background:var(--warn-soft); border-color:var(--warn-line); }",
    ".drawer .dt06-list .group-row.err .dt06-msg { color:var(--fg); font-family:var(--font-mono, ui-monospace, monospace); }",
    ".drawer .dt06-list .group-row.err .dt06-msg.open { background:var(--bg-sunken); border-color:var(--error-line); }",
    ".drawer .dt06-list .group-row.ok .dt06-msg { color:var(--fg-dim); }",
    /* 数值列 */
    ".drawer .dt06-v { font-family:var(--font-mono, ui-monospace, monospace); font-size:12px; color:var(--fg);",
    "  min-width:0; white-space:nowrap; }",
    ".drawer .dt06-v.z { color:var(--fg-dim); }",
    ".drawer .dt06-tier { font-family:var(--font-mono, ui-monospace, monospace); font-size:11px; color:var(--fg-dim);",
    "  text-align:right; white-space:nowrap; }",
    /* 下次重新汇报列: 全局近似值 + 微条比例 */
    ".drawer .dt06-nextcell { min-width:0; display:flex; justify-content:flex-end; }",
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
    ".drawer .dt06-opscell { min-width:0; display:flex; justify-content:flex-end; }",
    ".drawer .dt06-ops { display:flex; gap:2px; justify-content:flex-end; opacity:.5; transition:opacity var(--dur) var(--ease); }",
    ".drawer .dt06-list .group-row:hover .dt06-ops { opacity:1; }",
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
   * (后两者由调用方分流, 不进本函数)。U3: 返回数据对象(渲染在分片), 判据不变。 */
  function nextOf(ctx, t, nowSec) {
    const na = t ? t.next_announce : null;
    if (num(na) && na > 0) {
      return { kind: "real", val: ctx.fmtDuration(Math.max(0, Math.round(na - nowSec))) };
    }
    const d = (ctx.drawer && ctx.drawer.detail) || null;
    if (!d || !(d.reannounce_in > 0)) {
      return { kind: "none", val: "—" }; /* 汇报倒计时数据未落袋 */
    }
    const bar = num(d.reannounce) && d.reannounce > 0 && d.reannounce_in <= d.reannounce
      ? Number((d.reannounce_in / d.reannounce * 100).toFixed(1)) : 0;
    return { kind: "global", val: ctx.fmtDuration(d.reannounce_in), bar };
  }

  /* ---------------- 行装配(U3: 判据在这里, 呈现在渲染器分片) ----------------
   * 行对象 = 显示值 + _raw 排序原值(sort.js _sortVal 消费) + 修饰字段 + _cls 行态。
   * 排序由引擎做(默认 sev 升序 = 异常置顶, 同档稳定保 qB 原序); benign = 「仅看异常」
   * 过滤的目标外行标记(正常 + 未启用)—— 行不重装配, 外壳容器类切换(原口径)。 */
  function rowOf(ctx, t, i, nowSec, rGate) {
    const b = bucketOf(ctx, t);
    const bk = BUCKET[b];
    const virtual = b === "off" && ctx.drawerTrackerVirtual(t.url);
    const m = String(t.msg || "").trim();
    const open = !!(ui.openMsg[t.url] && m);
    const stText = b === "err" ? bk.text : ctx.drawerTrackerStatus(t.status) || bk.text;
    const sd = ctx.fmtPeersQb(t.num_seeds, t.num_complete);
    const lc = ctx.fmtPeersQb(t.num_leeches, t.num_incomplete);
    const next = b === "upd"
      ? { kind: "upd" }
      : (b === "off" ? { kind: "none" } : nextOf(ctx, t, nowSec));
    return {
      k: "t" + i,
      url: String(t.url || ""),
      urlTitle: String(t.url || ""),
      host: virtual ? String(t.url) : hostOf(t.url),
      dim: virtual,
      b,
      stText,
      pulse: b === "upd",
      m,
      open,
      tier: num(t.tier) ? String(t.tier) : "—",
      seeds: { val: sd || "—", z: !sd },
      leeches: { val: lc || "—", z: !lc },
      downloaded: { val: num(t.num_downloaded) ? String(t.num_downloaded) : "—", z: !num(t.num_downloaded) },
      next,
      virtual,
      gatedOk: rGate.ok,
      gatedTitle: rGate.ok ? "强制重新汇报" : rGate.title,
      _raw: {
        sev: bk.sev,
        host: hostOf(t.url),
        tier: num(t.tier) ? Number(t.tier) : null,
        seeds: num(t.num_seeds) ? Number(t.num_seeds) : (num(t.num_complete) ? Number(t.num_complete) : null),
        leeches: num(t.num_leeches) ? Number(t.num_leeches) : (num(t.num_incomplete) ? Number(t.num_incomplete) : null),
        downloaded: num(t.num_downloaded) ? Number(t.num_downloaded) : null,
      },
      _cls: [b, b === "ok" || b === "off" ? "benign" : ""].filter(Boolean).join(" ") || null,
    };
  }

  /* 桥行来源(注册条目 rowsFn ← 根方法 dtTplRows): 全量行(仅看异常是容器类切换不裁行);
   * 排序由引擎按 dyn 键做(默认 sev 升序), 这里不排。 */
  function rowsFn(ctx) {
    const ts = (ctx.drawer && ctx.drawer.trackers) || [];
    const nowSec = Math.floor(Date.now() / 1000);
    const rGate = ctx.drawerReannounceGate();
    return ts.map((t, i) => rowOf(ctx, t, i, nowSec, rGate));
  }

  /* 工具条 HTML —— 整帧重建与数据拍原地回填(paintHtml)共用同一构建器 */
  function toolbarHtml(ctx, ts, d) {
    /* 工具条注: 有任一行带 next_announce(qB 5.2+) = 真口径; 否则回退种子级全局近似 */
    const perTracker = ts.some((t) => num(t.next_announce) && t.next_announce > 0);
    const note = perTracker
      ? "汇报倒计时为逐 tracker 真值(qB next_announce) · 5s 自动刷新"
      : (d && d.reannounce_in > 0 ? "汇报倒计时为种子级全局值(qB 无 per-tracker 口径) · 5s 自动刷新" : "5s 自动刷新");
    return T`<span class="dt06-note">${note}</span>
        <button type="button" class="dt06-toggle${ui.onlyBad ? " active" : ""}" data-toggle
          ><i></i>仅看异常</button>
        <span class="dt06-spacer"></span>
        <button type="button" class="dt06-add" data-act="add"><svg class="ico ico-sm" viewBox="0 0 16 16"><use href="#i-plus"></use></svg>添加 Tracker</button>`;
  }

  function render(host, ctx) {
    const ts = (ctx.drawer && ctx.drawer.trackers) || [];
    const loading = ctx.drawer && ctx.drawer.trackersLoading;
    const d = (ctx.drawer && ctx.drawer.detail) || null;
    /* P3-5(报告 26-10-07-0542): fetch 失败标记 —— 失败与「真没有」在变体里不同形态 */
    const err = (ctx.drawer && ctx.drawer.trackersError) || "";
    /* 结构 sig(26-10-12 用户报障根治): 只含"外壳形状"决定项(加载/失败/空态), **不含
     * trackers 数据 / 倒计时基准 nowSec / 种子级 reannounce**。数据拍(5s 轮询每拍必到)
     * 不整帧重建 —— 整帧重建移动锚 = 表格整树重排(80 对端实测 56-75ms longtask/拍 =
     * 每 5s 全表卡顿闪烁, 即用户所报"表格闪烁, 数据随闪烁刷新"); 行走桥响应式, 壳上
     * 工具条注(真口径/全局口径随数据与 detail 变)走 paintHtml 原地回填。逐行倒计时
     * 随根重渲染重算, 粒度仍是 5s 轮询 —— 与修复前一致(nowSec 进 sig 从来不产生更细
     * 粒度: _dtNotify 只随数据落袋触发)。仅看异常的显隐是 class 直翻(onClick 自保),
     * 不进 sig。 */
    const sig = String(!!loading) + "|" + err + "|" + (ts.length ? "y" : "n");
    if (H.skipUnchanged(host, ui, sig)) {
      if (ts.length && !loading && !err) H.paintHtml(host, ".dt06-toolbar", toolbarHtml(ctx, ts, d));
      return;
    }
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
    /* 表格区 = 空 slot: anchFill 把保活的锚元素替换进 slot 位, 表壳/行由桥 Teleport 进锚 */
    const html = T`<div class="dt06-wrap">
      <div class="dt06-toolbar">${R(toolbarHtml(ctx, ts, d))}</div>
      <div class="dt06-list${ui.onlyBad ? " only-bad" : ""}"><div data-dt-anchor-slot=""></div></div>
    </div>`;
    /* 纵横滚动位成对自保(表格定宽 grid 窄窗口下必有横向滚动, 整帧重建只还 scrollTop 会把
     * 用户的横向滚动位打回最左) —— 单点 helper */
    H.withScroll(host, () => {
      host.replaceChildren(document.createRange().createContextualFragment(html));
      H.anchFill(host, TABLE_ID);
    });
  }

  function onClick(ev) {
    const h = ev.currentTarget;
    const toggle = ev.target.closest("[data-toggle]");
    if (toggle) {
      ui.onlyBad = !ui.onlyBad;
      toggle.classList.toggle("active", ui.onlyBad);
      const list = h.querySelector(".dt06-list");
      if (list) list.classList.toggle("only-bad", ui.onlyBad);
      return;
    }
    const sub = ev.target.closest("[data-msg]");
    if (sub) {
      const url = sub.getAttribute("data-msg");
      ui.openMsg[url] = !ui.openMsg[url];
      /* 展开态只翻 class 不重建(重建会重置滚动), 与 ui.openMsg 同步供 5s 重渲染后恢复 */
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

  /* 视图偏好变化后的强制重渲染(sig 不含偏好, 置空 lastSig 即可) */
  function rerender(host) {
    ui.lastSig = "";
    const ctx = host.__dtCtx;
    if (ctx) _render(host, ctx);
  }

  /* P3-4: 纯 span 模拟控件(msg 展开行 data-msg, 在引擎渲染的行容器内)的键盘触发 ——
   * Enter/Space 转发 click 委托; 焦点在原生 button 等自身会发 click 的元素上时不接管
   * (防 Enter 双重触发)。锚挂在宿主帧内, 事件委托照常命中。 */
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

  function destroy(host) {
    ui.lastSig = ""; /* 下次挂载强制整帧重建 */
    /* 宿主元素跨变体复用(同页签只有一个 data-dt-host), 换变体必须摘掉本变体的委托监听,
     * 否则新旧变体监听叠加、同一次点击被多个 handler 重复处理 */
    H.unwireEvents(host);
  }

  const _render = render;
  reg.register({
    id: "06", tab: "trackers",
    label: "增强表格",
    /* 桥声明(U3): 表格体走引擎 —— tableId 对应 app.js DRAWER_TABLE_DEFS.drawerTrackerV06,
     * rowsFn = 行装配(判据单点), 8 列表头/排序/拖宽/右键隐藏/偏好持久化归引擎。 */
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
