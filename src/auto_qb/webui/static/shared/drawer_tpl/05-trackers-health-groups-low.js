/* auto-qb WEB UI · 详情面板 trackers 页签变体 05「健康度分组(问题前置)」(计划 26-10-06-0838 S3)
 *
 * 设计稿: resources/detail-panel-templates/05-trackers-health-groups-low.html(low 档;
 * 收起/矮/高三档语义全部收进本变体 —— 收起 = 核心内置摘要条, 矮/高 = 分区列表自适应滚动)。
 * 数据: /trackers qB 透传(drawer.trackers, 5s 轮询); 分区顺序即处理顺序:
 * 失败 -> 警告 -> 更新中 -> 正常 -> 未启用(空分区整节隐藏); 失败区 msg 全文铺开 +
 * 处置建议文案(变体内置映射, 按 msg 关键词分派); 备注类 msg 点击展开全文。
 * 状态分桶(纯数值判据, 不复刻经典链文案单点): status 2=正常 3=更新中 4=失败 1=警告(未连接)
 * 0/虚拟=未启用 —— qB 的 4(not working)在经典链只显「未连接」, 分组语义按设计稿提到失败档。
 * 动作: 失败区重报钮 drawerCmd("reannounce")(torrent 级 = 全 tracker 重报, 经典链同源);
 * 删除(trackerRemove)。设计稿的「已失败时长/上次成功/逐行汇报倒计时」无 per-tracker
 * 数据源, 按渐进纪律省略(P-02 只授权 06 变体以 detail.reannounce_in 近似)。
 * !U3 重写(计划 26-10-12-0527, 分段形态同 08): 五组锚槽 + rowsFn 分段装配 —— **分组头/折叠
 *   留在外壳(分组是版式), 行是引擎表体**(失败处置块/普通行/off 组 chips 合成行三形态,
 *   kind 分支经渲染器分片 tpl-aq-dt05-cells); 无排序(dyn 空键 = 组内 qB 原序, 原口径);
 *   msg 展开态 rowsFn 读取(重建后恢复), 折叠仍 classList 翻转不重挂(锚元素集合不变)。
 * 渲染纪律: dtHtml 全量转义(dtRaw 只用于拼接本变体 dtHtml 产出的预转义片段), replaceChildren
 * 原子换帧, 数据未变(整份 trackers 序列化比对)跳过重建, 各组锚元素跨帧保活(锚被重建 =
 * Teleport 重挂 = 行抖动), 滚动位置/分区折叠/msg 展开态自保。
 * 自包含: 删除本文件 + 三份 index.html 各去 1 行 manifest 即整体退役, 其它零接触。
 */
(function () {
  "use strict";
  const reg = window.AQB_DRAWER_TPL_REG;
  if (!reg) return; /* 核心未载入(清单序错): 静默退出, 守阵会抓 */
  const T = reg.dtHtml;
  const R = reg.dtRaw;
  const H = reg.helpers; /* 公共骨架单点(报告 26-10-07-0845): 工具/sig 比对/滚动自保/事件挂摘/锚保活 */
  const TABLE_ID = "drawerTrackerV05";

  /* 分区定义: 顺序即处理顺序(问题前置); 空分区整节隐藏 */
  const GROUPS = [
    { key: "err", text: "未工作", cnt: "正在拖后腿 · 优先处理" },
    { key: "warn", text: "未联系", cnt: "可用但需关注" },
    { key: "upd", text: "更新中", cnt: "汇报进行时" },
    { key: "ok", text: "工作", cnt: "按 tier 升序" },
    { key: "off", text: "禁用", cnt: "qB 合成 / 已禁用" },
  ];

  /* 视图偏好(跨重渲染与换种子保持): 分区折叠 / msg 展开集合; lastSig 供跳过重建 */
  const ui = { folded: {}, openMsg: {}, lastSig: "" };

  const CSS = [
    /* 顶部计数条 */
    ".drawer .dt05-strip { display:flex; align-items:center; flex-wrap:wrap; gap:5px 12px; padding:6px 12px;",
    "  background:var(--bg-sunken); border:1px solid var(--border); border-radius:var(--radius);",
    "  font-size:12px; color:var(--fg-muted); }",
    ".drawer .dt05-c { display:inline-flex; align-items:center; gap:5px; white-space:nowrap; }",
    ".drawer .dt05-c i { width:7px; height:7px; border-radius:50%; flex:none; }",
    ".drawer .dt05-c b { font-family:var(--font-mono, ui-monospace, monospace); font-weight:600; color:var(--fg); }",
    ".drawer .dt05-note { font-size:11.5px; color:var(--fg-dim); }",
    ".drawer .dt05-spacer { flex:1; }",
    /* 分区(组头/折叠留外壳 —— 分组是版式, 行是引擎表体, U3) */
    ".drawer .dt05-group { margin-top:10px; }",
    ".drawer .dt05-ghead { display:flex; align-items:center; gap:8px; height:26px; cursor:pointer; user-select:none; }",
    ".drawer .dt05-badge { flex:none; display:inline-flex; align-items:center; gap:5px; height:19px; padding:0 8px;",
    "  border-radius:var(--radius-sm); font-size:11px; font-weight:600; background:var(--tg-soft);",
    "  border:1px solid var(--tg-line); color:var(--tg-c); }",
    ".drawer .dt05-badge i { width:6px; height:6px; border-radius:50%; background:var(--tg-c); }",
    ".drawer .dt05-g-err { --tg-c:var(--error); --tg-soft:var(--error-soft); --tg-line:var(--error-line); }",
    ".drawer .dt05-g-warn { --tg-c:var(--warn); --tg-soft:var(--warn-soft); --tg-line:var(--warn-line); }",
    ".drawer .dt05-g-upd { --tg-c:var(--blue); --tg-soft:var(--blue-soft); --tg-line:var(--blue-line); }",
    ".drawer .dt05-g-ok { --tg-c:var(--green); --tg-soft:var(--green-soft); --tg-line:var(--green-line); }",
    ".drawer .dt05-g-off { --tg-c:var(--fg-dim); --tg-soft:var(--surface-1); --tg-line:var(--border-soft); }",
    ".drawer .dt05-ghead b { font-size:12.5px; font-weight:600; color:var(--fg-soft); }",
    ".drawer .dt05-cnt { font-size:11px; color:var(--fg-dim); white-space:nowrap; }",
    ".drawer .dt05-chev { color:var(--fg-dim); flex:none; transition:transform var(--dur) var(--ease); }",
    ".drawer .dt05-ghead::after { content:\"\"; flex:1; height:1px; background:var(--hairline); }",
    ".drawer .dt05-group.folded .dt05-chev { transform:rotate(-90deg); }",
    ".drawer .dt05-group.folded .dt05-gbody { display:none; }",
    ".drawer .dt05-gbody { padding:3px 0 2px; }",
    /* 行容器(引擎 .group-row)的变体个性(D5): 去引擎卡底, 行观感归内容根(.dt05-rowin) */
    ".drawer .dt05-list .group-row { display:block; gap:0; background:transparent; border:0;",
    "  box-shadow:none; padding:2px 0; cursor:default; }",
    ".drawer .dt05-list .group-row:hover { background:transparent; transform:none; border-color:transparent; }",
    ".drawer .dt05-list .group-row.failrow, .drawer .dt05-list .group-row.chipsrow { padding:0; }",
    /* 分区行(警告 / 更新中 / 正常 / 未启用实体)—— 呈现归渲染器分片, 布局类留本变体 */
    ".drawer .dt05-rowin { display:flex; align-items:center; gap:10px; min-height:34px; padding:5px 8px;",
    "  border-radius:var(--radius-sm); }",
    ".drawer .dt05-list .group-row:hover .dt05-rowin { background:var(--bg-hover); }",
    ".drawer .dt05-dot { width:8px; height:8px; border-radius:50%; flex:none; }",
    ".drawer .dt05-g-ok .dt05-dot { background:var(--green); }",
    ".drawer .dt05-g-upd .dt05-dot { background:var(--blue); }",
    ".drawer .dt05-g-warn .dt05-dot { background:var(--warn); }",
    ".drawer .dt05-g-off .dt05-dot { background:var(--border-strong); }",
    ".drawer .dt05-main { flex:1; min-width:0; display:flex; flex-direction:column; gap:2px; }",
    ".drawer .dt05-line { display:flex; align-items:center; gap:7px; min-width:0; }",
    ".drawer .dt05-host { min-width:0; font-family:var(--font-mono, ui-monospace, monospace); font-size:12.5px;",
    "  color:var(--fg); overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }",
    ".drawer .dt05-tier { flex:none; font-family:var(--font-mono, ui-monospace, monospace); font-size:10.5px;",
    "  color:var(--fg-dim); border:1px solid var(--border-soft); border-radius:var(--radius-sm); padding:0 5px; }",
    ".drawer .dt05-sub { align-self:flex-start; max-width:100%; font-size:11px; color:var(--warn); overflow:hidden;",
    "  text-overflow:ellipsis; white-space:nowrap; cursor:pointer; border-radius:var(--radius-sm);",
    "  border:1px dashed transparent; }",
    ".drawer .dt05-sub.dim { color:var(--fg-dim); }",
    ".drawer .dt05-sub:hover { text-decoration:underline; text-underline-offset:2px; }",
    ".drawer .dt05-sub.open { white-space:normal; line-height:1.6; cursor:default; padding:4px 9px; margin:1px 0 2px;",
    "  background:var(--warn-soft); border:1px solid var(--warn-line); }",
    ".drawer .dt05-sub.dim.open { background:var(--surface-1); border-color:var(--border-soft); }",
    ".drawer .dt05-stats { flex:none; display:flex; gap:12px; font-size:11.5px; color:var(--fg-muted); white-space:nowrap; }",
    ".drawer .dt05-s { display:inline-flex; align-items:baseline; gap:4px; }",
    ".drawer .dt05-s b { font-family:var(--font-mono, ui-monospace, monospace); font-weight:600; font-size:12px; color:var(--fg); }",
    ".drawer .dt05-s .z { color:var(--fg-dim); }",
    ".drawer .dt05-acts { flex:none; display:flex; gap:2px; opacity:.45; transition:opacity var(--dur) var(--ease); }",
    ".drawer .dt05-rowin:hover .dt05-acts { opacity:1; }",
    ".drawer .dt05-act { display:inline-flex; align-items:center; justify-content:center; width:22px; height:22px;",
    "  padding:0; border:0; border-radius:var(--radius-sm); background:transparent; color:var(--fg-dim); cursor:pointer;",
    "  transition:color var(--dur) var(--ease), background var(--dur) var(--ease); }",
    ".drawer .dt05-act:hover { color:var(--fg); background:var(--bg-hover); }",
    /* 失败区: 整块突出, msg 全文 + 处置建议 */
    ".drawer .dt05-fail { display:flex; flex-direction:column; gap:7px; padding:9px 12px; margin:2px 0;",
    "  background:var(--error-soft); border:1px solid var(--error-line); border-radius:var(--radius); }",
    ".drawer .dt05-fail .dt05-acts { opacity:1; }",
    ".drawer .dt05-fail .dt05-act:hover { background:var(--bg-hover); }",
    /* 非活跃种子禁汇报: 重报钮置灰不可点(qB 口径)。本变体两处入口 —— 普通行 .dt05-act 与失败区
     * 大钮 .dt05-rbtn; 失败区 hover 是 (0,4,0), 故显式带上 .dt05-fail 前缀一并压过。 */
    ".drawer .dt05-act.is-gated, .drawer .dt05-act.is-gated:hover, .drawer .dt05-fail .dt05-act.is-gated:hover { color:var(--fg-dim); background:transparent; cursor:not-allowed; }",
    ".drawer .dt05-rbtn.is-gated, .drawer .dt05-rbtn.is-gated:hover { color:var(--fg-dim); border-color:var(--border-soft); background:transparent; cursor:not-allowed; }",
    ".drawer .dt05-rtop { display:flex; align-items:center; gap:8px; min-width:0; }",
    ".drawer .dt05-rhost { min-width:0; font-family:var(--font-mono, ui-monospace, monospace); font-size:12.5px;",
    "  font-weight:600; color:var(--fg); overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }",
    ".drawer .dt05-rbtn { flex:none; display:inline-flex; align-items:center; gap:5px; height:26px; padding:0 10px;",
    "  border:1px solid var(--border-strong); border-radius:var(--radius-sm); background:var(--surface-1);",
    "  color:var(--fg); font-size:11.5px; cursor:pointer; margin-left:auto;",
    "  transition:border-color var(--dur) var(--ease), background var(--dur) var(--ease); }",
    ".drawer .dt05-rbtn:hover { border-color:var(--error); }",
    ".drawer .dt05-fmsg { font-family:var(--font-mono, ui-monospace, monospace); font-size:12px; line-height:1.6;",
    "  color:var(--fg); background:var(--bg-sunken); border:1px solid var(--error-line);",
    "  border-radius:var(--radius-sm); padding:6px 10px; word-break:break-all; }",
    ".drawer .dt05-hint { font-size:11.5px; color:var(--fg-muted); line-height:1.6; }",
    ".drawer .dt05-hint b { color:var(--fg-soft); font-weight:600; }",
    /* 未启用区: 虚拟条目 chips(合成行) */
    ".drawer .dt05-offline { display:flex; align-items:center; flex-wrap:wrap; gap:7px; padding:4px 8px; min-height:34px; }",
    ".drawer .dt05-vchip { font-family:var(--font-mono, ui-monospace, monospace); font-size:11.5px; color:var(--fg-muted);",
    "  background:var(--surface-1); border:1px solid var(--border-soft); border-radius:var(--radius-sm); padding:2px 9px; }",
    ".drawer .dt05-offnote { font-size:11.5px; color:var(--fg-dim); }",
    /* 空态 */
    ".drawer .dt05-empty { padding:22px 0; display:flex; align-items:center; justify-content:center; gap:8px;",
    "  color:var(--fg-dim); font-size:12.5px; }",
  ].join("\n");

  /* ---------------- 分桶 / 建议映射 ---------------- */
  function bucketOf(ctx, t) {
    if (ctx.drawerTrackerVirtual(t.url)) return "off";
    const s = Number(t.status);
    if (s === 2) return "ok";
    if (s === 3) return "upd";
    if (s === 4) return "err";
    if (s === 1) return "warn";
    return "off"; /* 0 = 未启用(非虚拟也按此档) */
  }

  /* 处置建议(变体内置映射): 按 tracker msg 关键词分派, 未命中走通用兜底 */
  function adviceFor(msg) {
    const m = String(msg || "").toLowerCase();
    if (/unregistered|not registered|not found|unknown torrent|infohash/.test(m)) {
      return "该种子可能已被站点删除, 或下载信息已失效 —— 重新下载 .torrent 覆盖, 或删除该 tracker 止损。";
    }
    if (/passkey|invalid|unauthor|forbidden|not allowed|auth/.test(m)) {
      return "鉴权信息疑似失效(passkey/身份核验被拒) —— 到站点重新下载 .torrent 或核对账号状态。";
    }
    if (/ban|client/.test(m)) {
      return "客户端或行为可能被站点限制 —— 核对站点客户端规则后强制重新汇报重试。";
    }
    if (/timeout|timed out|unreachable|connection|connect|host|resolve|network|refused/.test(m)) {
      return "网络层不可达(超时/DNS/连接被拒) —— 检查本机网络与代理后强制重新汇报重试。";
    }
    if (/maintenance|temporar|retry|later|busy|overload/.test(m)) {
      return "站点侧暂时不可用(维护/限流) —— 稍后再点强制重新汇报。";
    }
    return "先点「强制重新汇报」重试一次; 若持续失败, 到站点核对种子状态与账号, 或删除该 tracker 止损。";
  }

  const num = (v) => v !== undefined && v !== null && Number(v) >= 0;
  const hostOf = (url) => {
    try {
      return new URL(String(url)).host || String(url);
    } catch (e) {
      return String(url || "");
    }
  };

  /* ---------------- 行装配(U3: 判据在这里, 呈现在渲染器分片 tpl-aq-dt05-cells) ----------------
   * 行三形态: kind = "fail"(失败处置块) / "row"(普通行) / "chips"(off 组虚拟 chips 合成行);
   * msg 展开态(ui.openMsg)在装配时读 —— 重建后展开态恢复(与原口径一致)。 */
  function rowOf(ctx, t, i, rGate) {
    const b = bucketOf(ctx, t);
    const m = String(t.msg || "").trim();
    const open = !!(ui.openMsg[t.url] && m);
    const stats = [];
    const sd = ctx.fmtPeersQb(t.num_seeds, t.num_complete);
    const lc = ctx.fmtPeersQb(t.num_leeches, t.num_incomplete);
    if (num(t.num_seeds) || num(t.num_complete)) {
      stats.push({ label: "种子", val: sd || "—", z: !sd, title: "num_seeds (num_complete)" });
    }
    if (num(t.num_leeches) || num(t.num_incomplete)) {
      stats.push({ label: "用户", val: lc || "—", z: !lc, title: "num_leeches (num_incomplete)" });
    }
    if (num(t.num_downloaded)) {
      stats.push({ label: "完成", val: String(t.num_downloaded), title: "num_downloaded" });
    }
    return {
      k: "t" + i,
      kind: "row",
      b,
      url: String(t.url || ""),
      urlTitle: String(t.url || ""),
      host: hostOf(t.url),
      tier: num(t.tier) ? "T" + t.tier : null,
      pulse: b === "upd",
      m,
      open,
      dim: b !== "warn", /* 警告行 msg 着警示色, 其余弱化备注色 */
      stats,
      gatedOk: rGate.ok,
      gatedTitle: rGate.ok ? "强制重新汇报" : rGate.title,
      _cls: null,
    };
  }

  function failRowOf(ctx, t, i, rGate) {
    const m = String(t.msg || "").trim() || "tracker 未返回消息(not working)";
    return {
      k: "t" + i,
      kind: "fail",
      url: String(t.url || ""),
      urlTitle: String(t.url || ""),
      host: hostOf(t.url),
      tier: num(t.tier) ? "T" + t.tier : null,
      msg: m,
      advice: adviceFor(m),
      gatedOk: rGate.ok,
      gatedTitle: rGate.ok ? "" : rGate.title,
      _cls: "failrow",
    };
  }

  function chipsRowOf(ctx, list) {
    const vs = list.filter((t) => ctx.drawerTrackerVirtual(t.url));
    if (!vs.length) return null;
    return {
      k: "__chips__",
      kind: "chips",
      chips: vs.map((t) => String(t.url)),
      _cls: "chipsrow",
    };
  }

  /* 桥行来源(注册条目 rowsFn ← 根方法 dtTplRows): 描述符 segs=true → 返回 [{key, rows}] 分段。
   * 分桶判据与外壳 render 同一条(GROUPS × bucketOf) —— 桥段与锚槽一一对应; 空组整段缺席。 */
  function rowsFn(ctx) {
    const ts = (ctx.drawer && ctx.drawer.trackers) || [];
    const rGate = ctx.drawerReannounceGate();
    const byKey = { err: [], warn: [], upd: [], ok: [], off: [] };
    ts.forEach((t, i) => byKey[bucketOf(ctx, t)].push({ t, i }));
    return GROUPS.filter((g) => byKey[g.key].length).map((g) => {
      let rows;
      if (g.key === "err") {
        rows = byKey[g.key].map((x) => failRowOf(ctx, x.t, x.i, rGate));
      } else if (g.key === "off") {
        const chips = chipsRowOf(ctx, byKey[g.key].map((x) => x.t));
        rows = (chips ? [chips] : []).concat(
          byKey[g.key].filter((x) => !ctx.drawerTrackerVirtual(x.t.url)).map((x) => rowOf(ctx, x.t, x.i, rGate)));
      } else {
        /* 正常区按 tier 升序(设计稿口径); 其余保 qB 原序 */
        const list = g.key === "ok"
          ? byKey[g.key].slice().sort((a, b2) => (Number(a.t.tier) || 0) - (Number(b2.t.tier) || 0))
          : byKey[g.key];
        rows = list.map((x) => rowOf(ctx, x.t, x.i, rGate));
      }
      return { key: g.key, rows };
    });
  }

  function groupHtml(g, ms) {
    const folded = ui.folded[g.key] ? " folded" : "";
    return T`<section class="dt05-group dt05-g-${g.key}${folded}" data-grp="${g.key}">
      <!-- P3-4: 折叠组头纯 div 模拟控件补键盘达(role=button + tabindex + aria-expanded) -->
      <div class="dt05-ghead" role="button" tabindex="0" aria-expanded="${folded ? "false" : "true"}"
           data-fold title="点击折叠 / 展开">
        <span class="dt05-badge"><i></i>${g.text} ${ms.length}</span>
        <b>${g.text}</b>
        <span class="dt05-cnt">${g.cnt}</span>
        <svg class="ico ico-sm dt05-chev" viewBox="0 0 16 16"><use href="#i-chevron"></use></svg>
      </div>
      <!-- 组体 = 引擎表体(U3 分段桥): 锚槽由 anchFill 换成保活锚, 桥逐段 teleport 行渲染器进锚 -->
      <div class="dt05-gbody"><div data-dt-anchor-slot="${g.key}"></div></div>
    </section>`;
  }

  /* 计数条 HTML —— 整帧重建与数据拍原地回填(paintHtml)共用同一构建器 */
  function stripHtml(n, virtualN) {
    return T`<span class="dt05-c"><i style="background:var(--green)"></i>工作 <b>${n.ok}</b></span>
      <span class="dt05-c"><i style="background:var(--warn)"></i>未联系 <b>${n.warn}</b></span>
      <span class="dt05-c"><i style="background:var(--blue)"></i>更新中 <b>${n.upd}</b></span>
      <span class="dt05-c"><i style="background:var(--error)"></i>未工作 <b>${n.err}</b></span>
      <span class="dt05-c"><i style="background:var(--border-strong)"></i>禁用 <b>${n.off}</b>${virtualN ? R(T`<span class="dt05-note">(虚拟 ${virtualN})</span>`) : ""}</span>
      <span class="dt05-note">5s 自动刷新</span>
      <span class="dt05-spacer"></span>`;
  }

  function render(host, ctx) {
    const ts = (ctx.drawer && ctx.drawer.trackers) || [];
    const loading = ctx.drawer && ctx.drawer.trackersLoading;
    /* P3-5(报告 26-10-07-0542): fetch 失败标记 —— 失败与「真没有」在变体里不同形态 */
    const err = (ctx.drawer && ctx.drawer.trackersError) || "";
    /* 分桶(计数条 + 分区, 与 rowsFn 同判据) */
    const n = { ok: 0, warn: 0, upd: 0, err: 0, off: 0 };
    const byKey = { err: [], warn: [], upd: [], ok: [], off: [] };
    for (const t of ts) {
      const b = bucketOf(ctx, t);
      n[b]++;
      byKey[b].push(t);
    }
    const virtualN = ts.filter((t) => ctx.drawerTrackerVirtual(t.url)).length;
    /* 结构 sig(26-10-12 用户报障根治): 只含"外壳形状"决定项 —— 加载/失败/空态/在场分组集
     * (空组整节隐藏⇒锚离场, 组补⇒新锚进场); **不含 trackers 数据**。折叠态**不进** sig:
     * 折叠只翻 class 不重建(锚元素集合不变, 桥零重挂 —— 既有设计), 数据拍照常跳过。
     * 数据拍不整帧重建的理由同 07: 整帧重建移动锚 = 表格整树重排(80 对端实测
     * 56-75ms longtask/拍 = 每 5s 全表卡顿闪烁, 即用户所报"表格闪烁, 数据随闪烁刷新")。 */
    const vis = GROUPS.filter((g) => byKey[g.key].length);
    const sig = String(!!loading) + "|" + err + "|" + (ts.length ? "y" : "n")
      + "|" + vis.map((g) => g.key).join(",");
    if (H.skipUnchanged(host, ui, sig)) {
      /* 数据拍: 计数条 + 各组头徽章计数原地回填 —— 组区含锚, 只改徽章, 锚不动 */
      if (ts.length && !loading && !err) {
        H.paintHtml(host, ".dt05-strip", stripHtml(n, virtualN));
        for (const g of vis) {
          const sec = host.querySelector('.dt05-group[data-grp="' + g.key + '"]');
          const badge = sec && sec.querySelector(".dt05-badge");
          if (badge) {
            const bh = T`<i></i>${g.text} ${byKey[g.key].length}`;
            if (badge.innerHTML !== bh) badge.innerHTML = bh;
          }
        }
      }
      return;
    }
    if (loading && !ts.length) {
      host.replaceChildren(document.createRange().createContextualFragment(
        T`<div class="dt05-empty"><svg class="ico" viewBox="0 0 16 16"><use href="#i-hourglass"></use></svg><span>正在加载…</span></div>`));
      return;
    }
    /* 错误态先于空态(P3-5): 失败且无数据不是"真的没有", 重试口径真实(本页签 5s 轮询会自动重拉) */
    if (err && !ts.length) {
      host.replaceChildren(document.createRange().createContextualFragment(
        T`<div class="dt05-empty"><svg class="ico" viewBox="0 0 16 16"><use href="#i-warn"></use></svg><span title="${err}">Tracker 列表加载失败, 将在下次自动刷新时重试</span></div>`));
      return;
    }
    if (!ts.length) {
      host.replaceChildren(document.createRange().createContextualFragment(
        T`<div class="dt05-empty"><span>暂无 tracker</span></div>`));
      return;
    }
    /* 分区: 空分区整节隐藏(与 rowsFn 同判据) */
    const secs = vis.map((g) => groupHtml(g, byKey[g.key]));
    /* !行容器必须是 .dt05-list(内层), 外层保持 .dt05-wrap —— 本变体全部 .group-row
     * 版式规则(摘引擎卡底/行观感归 .dt05-rowin/失败区与 chips 合成行)都以 .dt05-list
     * 为作用域前缀(U3 引擎化时写入), 而 2026-10-14 前外壳只有一层 dt05-wrap、行直接
     * 挂在它下面 ⇒ 前缀全程不匹配, 六条规则空转, 行一直带着主表卡底(--bg-row + 描边
     * + 圆角 + padding), 用户报「必现列背景与其他列不一致」诊断时逐面量计算样式才发现
     * (inList=false/inWrap=true)。修法 = 补内层 .dt05-list 包住分区(与 04/06/07/09/
     * 10/11 的 dtNN-wrap(外壳) + dtNN-list(行容器) 两层家族约定对齐; e2e 通用助手
     * openTrackersVariant 也按 .dtNN-wrap 等外壳, 单层改名会打破它)。 */
    const html = T`<div class="dt05-wrap"><div class="dt05-list">
      <div class="dt05-strip">${R(stripHtml(n, virtualN))}</div>
      ${R(secs.join(""))}
    </div></div>`;
    /* 滚动位置自保(纵横成对): 滚动容器是宿主父级(.drawer-body, Vue 所有) —— 单点 helper */
    H.withScroll(host, () => {
      host.replaceChildren(document.createRange().createContextualFragment(html));
      H.anchFill(host, TABLE_ID);
    });
  }

  function onClick(ev) {
    const h = ev.currentTarget;
    const head = ev.target.closest("[data-fold]");
    if (head) {
      const sec = head.closest("[data-grp]");
      if (sec) {
        const k = sec.getAttribute("data-grp");
        ui.folded[k] = !ui.folded[k];
        /* 折叠只翻 class 不重建(锚元素集合不变, 桥零重挂) */
        sec.classList.toggle("folded");
      }
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
    if (act === "report") { ctx.drawerCmd("reannounce", null, "强制重新汇报"); return; }
    if (act === "del") { ctx.trackerRemove(url); }
  }

  /* 视图偏好变化后的强制重渲染(sig 不含偏好, 置空 lastSig 即可) */
  function rerender(host) {
    ui.lastSig = "";
    const ctx = host.__dtCtx;
    if (ctx) _render(host, ctx);
  }

  /* P3-4: 纯 div/span 模拟控件的键盘触发 —— Enter/Space 转发 click 委托; 焦点在原生
   * button/summary 等自身会发 click 的元素上时不接管(防 Enter 双重触发), 纯 div 模拟
   * (折叠组头 data-fold / msg 展开行 data-msg)没有原生 click 才需要手动转发。
   * !msg 行在引擎渲染的行容器内 —— 但锚挂在宿主帧内, 事件委托照常命中。 */
  function onKeyDown(ev) {
    if (ev.key !== "Enter" && ev.key !== " ") return;
    if (ev.target.closest("button, input, select, textarea, a[href], summary")) return;
    if (!ev.target.closest("[data-fold], [data-msg]")) return;
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
    id: "05", tab: "trackers",
    label: "健康分组",
    /* 桥声明(U3, 分段形态): tableId 对应 DRAWER_TABLE_DEFS.drawerTrackerV05(描述符 segs:true),
     * rowsFn 返回 [{key, rows}] 与锚槽一一对应; 组头聚合/折叠留在外壳; 无排序(dyn 空键)。 */
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
