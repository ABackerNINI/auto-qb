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
 * 渲染纪律: dtHtml 全量转义(dtRaw 只用于拼接本变体 dtHtml 产出的预转义片段), replaceChildren
 * 原子换帧, 数据未变(整份 trackers 序列化比对)跳过重建, 滚动位置/分区折叠/msg 展开态自保。
 * 自包含: 删除本文件 + 三份 index.html 各去 1 行 manifest 即整体退役, 其它零接触。
 */
(function () {
  "use strict";
  const reg = window.AQB_DRAWER_TPL_REG;
  if (!reg) return; /* 核心未载入(清单序错): 静默退出, 守阵会抓 */
  const T = reg.dtHtml;
  const R = reg.dtRaw;
  const H = reg.helpers; /* 公共骨架单点(报告 26-10-07-0845): 工具/sig 比对/滚动自保/事件挂摘 */

  /* 分区定义: 顺序即处理顺序(问题前置); 空分区整节隐藏 */
  const GROUPS = [
    { key: "err", text: "失败", cnt: "正在拖后腿 · 优先处理" },
    { key: "warn", text: "警告", cnt: "可用但需关注" },
    { key: "upd", text: "更新中", cnt: "汇报进行时" },
    { key: "ok", text: "正常", cnt: "按 tier 升序" },
    { key: "off", text: "未启用", cnt: "qB 合成 / 已禁用" },
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
    /* 分区 */
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
    /* 分区行(警告 / 更新中 / 正常 / 未启用实体) */
    ".drawer .dt05-row { display:flex; align-items:center; gap:10px; min-height:34px; padding:5px 8px;",
    "  border-radius:var(--radius-sm); }",
    ".drawer .dt05-row:hover { background:var(--bg-hover); }",
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
    ".drawer .dt05-s i { font-style:normal; font-family:var(--font-mono, ui-monospace, monospace); font-size:11px; color:var(--fg-dim); }",
    ".drawer .dt05-s .z { color:var(--fg-dim); }",
    ".drawer .dt05-acts { flex:none; display:flex; gap:2px; opacity:.45; transition:opacity var(--dur) var(--ease); }",
    ".drawer .dt05-row:hover .dt05-acts { opacity:1; }",
    ".drawer .dt05-act { display:inline-flex; align-items:center; justify-content:center; width:22px; height:22px;",
    "  padding:0; border:0; border-radius:var(--radius-sm); background:transparent; color:var(--fg-dim); cursor:pointer;",
    "  transition:color var(--dur) var(--ease), background var(--dur) var(--ease); }",
    ".drawer .dt05-act:hover { color:var(--fg); background:var(--bg-hover); }",
    /* 失败区: 整块突出, msg 全文 + 处置建议 */
    ".drawer .dt05-fail { display:flex; flex-direction:column; gap:7px; padding:9px 12px; margin:2px 0;",
    "  background:var(--error-soft); border:1px solid var(--error-line); border-radius:var(--radius); }",
    ".drawer .dt05-fail .dt05-acts { opacity:1; }",
    ".drawer .dt05-fail .dt05-act:hover { background:var(--bg-hover); }",
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
    /* 未启用区: 虚拟条目 chips */
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
      return "客户端或行为可能被站点限制 —— 核对站点客户端规则后强制汇报重试。";
    }
    if (/timeout|timed out|unreachable|connection|connect|host|resolve|network|refused/.test(m)) {
      return "网络层不可达(超时/DNS/连接被拒) —— 检查本机网络与代理后强制汇报重试。";
    }
    if (/maintenance|temporar|retry|later|busy|overload/.test(m)) {
      return "站点侧暂时不可用(维护/限流) —— 稍后再点强制汇报。";
    }
    return "先点「强制汇报」重试一次; 若持续失败, 到站点核对种子状态与账号, 或删除该 tracker 止损。";
  }

  const num = (v) => v !== undefined && v !== null && Number(v) >= 0;
  const hostOf = (url) => {
    try {
      return new URL(String(url)).host || String(url);
    } catch (e) {
      return String(url || "");
    }
  };

  /* 分区行(警告 / 更新中 / 正常): host + tier + msg(点击展开) + 统计 + 行内动作 */
  function rowHtml(ctx, t) {
    const b = bucketOf(ctx, t);
    const m = String(t.msg || "").trim();
    const dim = b !== "warn"; /* 警告行 msg 着警示色, 其余弱化备注色 */
    const open = ui.openMsg[t.url] && m;
    /* P3-4(报告 26-10-07-0542): 纯 span 模拟控件补键盘达(role=button + tabindex + aria-expanded) */
    const sub = m
      ? T`<span class="dt05-sub${dim ? " dim" : ""}${open ? " open" : ""}" role="button" tabindex="0"
          aria-expanded="${open ? "true" : "false"}" data-msg="${t.url}"
          title="tracker 返回的原始 msg, 点击展开 / 收起">${m}</span>`
      : "";
    const stats = [];
    const sd = ctx.fmtPeersQb(t.num_seeds, t.num_complete);
    const lc = ctx.fmtPeersQb(t.num_leeches, t.num_incomplete);
    if (num(t.num_seeds) || num(t.num_complete)) {
      stats.push(sd
        ? T`<span class="dt05-s" title="num_seeds (num_complete)">做种 <b>${sd}</b></span>`
        : T`<span class="dt05-s" title="num_seeds (num_complete)">做种 <b class="z">—</b></span>`);
    }
    if (num(t.num_leeches) || num(t.num_incomplete)) {
      stats.push(lc
        ? T`<span class="dt05-s" title="num_leeches (num_incomplete)">用户 <b>${lc}</b></span>`
        : T`<span class="dt05-s" title="num_leeches (num_incomplete)">用户 <b class="z">—</b></span>`);
    }
    if (num(t.num_downloaded)) {
      stats.push(T`<span class="dt05-s" title="num_downloaded">完成 <b>${t.num_downloaded}</b></span>`);
    }
    return T`<div class="dt05-row" title="${t.url}">
      <span class="dt05-dot${b === "upd" ? " pulse" : ""}"></span>
      <div class="dt05-main">
        <div class="dt05-line">
          <span class="dt05-host">${hostOf(t.url)}</span>
          ${num(t.tier) ? R(T`<span class="dt05-tier" title="tier: 汇报层级, 数值越小越优先">T${t.tier}</span>`) : ""}
        </div>
        ${R(sub)}
      </div>
      ${stats.length ? R(T`<span class="dt05-stats">${R(stats.join(""))}</span>`) : ""}
      <span class="dt05-acts">
        <button type="button" class="dt05-act" data-act="report" title="强制汇报"><svg class="ico ico-sm" viewBox="0 0 16 16"><use href="#i-refresh"></use></svg></button>
        <button type="button" class="dt05-act" data-act="del" data-url="${t.url}" title="删除 tracker"><svg class="ico ico-sm" viewBox="0 0 16 16"><use href="#i-trash"></use></svg></button>
      </span>
    </div>`;
  }

  /* 失败块: msg 全文 + 处置建议 + 重报/删除 */
  function failHtml(ctx, t) {
    const m = String(t.msg || "").trim() || "tracker 未返回消息(not working)";
    return T`<div class="dt05-fail" title="${t.url}">
      <div class="dt05-rtop">
        <span class="dt05-dot"></span>
        <span class="dt05-rhost">${hostOf(t.url)}</span>
        ${num(t.tier) ? R(T`<span class="dt05-tier" title="tier: 汇报层级, 数值越小越优先">T${t.tier}</span>`) : ""}
        <button type="button" class="dt05-rbtn" data-act="report"><svg class="ico ico-sm" viewBox="0 0 16 16"><use href="#i-refresh"></use></svg>强制汇报</button>
        <span class="dt05-acts">
          <button type="button" class="dt05-act" data-act="del" data-url="${t.url}" title="删除失效 tracker"><svg class="ico ico-sm" viewBox="0 0 16 16"><use href="#i-trash"></use></svg></button>
        </span>
      </div>
      <div class="dt05-fmsg" title="tracker 返回的原始 msg">${m}</div>
      <div class="dt05-hint"><b>处置建议:</b>${adviceFor(m)}</div>
    </div>`;
  }

  function render(host, ctx) {
    const ts = (ctx.drawer && ctx.drawer.trackers) || [];
    const loading = ctx.drawer && ctx.drawer.trackersLoading;
    /* P3-5(报告 26-10-07-0542): fetch 失败标记 —— 失败与「真没有」在变体里不同形态 */
    const err = (ctx.drawer && ctx.drawer.trackersError) || "";
    /* 数据未变跳过重建(5s 通知频度下不闪不丢态) */
    const sig = JSON.stringify(ts) + "|" + String(!!loading) + "|" + err;
    if (H.skipUnchanged(host, ui, sig)) return;
    if (loading && !ts.length) {
      host.replaceChildren(document.createRange().createContextualFragment(
        T`<div class="dt05-empty"><svg class="ico" viewBox="0 0 16 16"><use href="#i-hourglass"></use></svg><span>正在加载…</span></div>`));
      return;
    }
    /* 错误态先于空态(P3-5): 失败且无数据不是"真的没有", 重试口径真实(本页签 5s 轮询会自动重拉) */
    if (err && !ts.length) {
      host.replaceChildren(document.createRange().createContextualFragment(
        T`<div class="dt05-empty"><svg class="ico" viewBox="0 0 16 16"><use href="#i-warn"></use></svg><span title="${err}">tracker 列表加载失败, 将在下次自动刷新时重试</span></div>`));
      return;
    }
    if (!ts.length) {
      host.replaceChildren(document.createRange().createContextualFragment(
        T`<div class="dt05-empty"><span>暂无 tracker</span></div>`));
      return;
    }
    /* 分桶计数(计数条) */
    const n = { ok: 0, warn: 0, upd: 0, err: 0, off: 0 };
    const byKey = { err: [], warn: [], upd: [], ok: [], off: [] };
    for (const t of ts) {
      const b = bucketOf(ctx, t);
      n[b]++;
      byKey[b].push(t);
    }
    const virtualN = ts.filter((t) => ctx.drawerTrackerVirtual(t.url)).length;
    /* 计数条: 正常 / 警告 / 更新中 / 失败 / 未启用(虚拟 m) */
    const strip = T`<span class="dt05-c"><i style="background:var(--green)"></i>正常 <b>${n.ok}</b></span>
      <span class="dt05-c"><i style="background:var(--warn)"></i>警告 <b>${n.warn}</b></span>
      <span class="dt05-c"><i style="background:var(--blue)"></i>更新中 <b>${n.upd}</b></span>
      <span class="dt05-c"><i style="background:var(--error)"></i>失败 <b>${n.err}</b></span>
      <span class="dt05-c"><i style="background:var(--border-strong)"></i>未启用 <b>${n.off}</b>${virtualN ? R(T`<span class="dt05-note">(虚拟 ${virtualN})</span>`) : ""}</span>
      <span class="dt05-note">5s 自动刷新</span>
      <span class="dt05-spacer"></span>`;
    /* 分区: 空分区整节隐藏; 正常区按 tier 升序(设计稿口径) */
    const secs = GROUPS.map((g) => {
      const list = byKey[g.key];
      if (!list.length) return "";
      const folded = ui.folded[g.key] ? " folded" : "";
      let bodyHtml;
      if (g.key === "err") {
        bodyHtml = list.map((t) => failHtml(ctx, t)).join("");
      } else if (g.key === "off") {
        const virtual = list.filter((t) => ctx.drawerTrackerVirtual(t.url));
        const disabled = list.filter((t) => !ctx.drawerTrackerVirtual(t.url));
        const chips = virtual.map((t) => T`<span class="dt05-vchip" title="qB 合成的虚拟条目">${t.url}</span>`).join("");
        const rows = disabled.map((t) => rowHtml(ctx, t)).join("");
        bodyHtml = T`<div class="dt05-offline">${R(chips)}${virtual.length ? T`<span class="dt05-offnote">虚拟条目由 qBittorrent 合成, 不参与汇报</span>` : ""}</div>${R(rows)}`;
      } else {
        const sorted = g.key === "ok"
          ? list.slice().sort((a, b2) => (Number(a.tier) || 0) - (Number(b2.tier) || 0))
          : list;
        bodyHtml = sorted.map((t) => rowHtml(ctx, t)).join("");
      }
      return T`<section class="dt05-group dt05-g-${g.key}${folded}" data-grp="${g.key}">
        <!-- P3-4: 折叠组头纯 div 模拟控件补键盘达(role=button + tabindex + aria-expanded) -->
        <div class="dt05-ghead" role="button" tabindex="0" aria-expanded="${folded ? "false" : "true"}"
             data-fold title="点击折叠 / 展开">
          <span class="dt05-badge"><i></i>${g.text} ${list.length}</span>
          <b>${g.text}</b>
          <span class="dt05-cnt">${g.cnt}</span>
          <svg class="ico ico-sm dt05-chev" viewBox="0 0 16 16"><use href="#i-chevron"></use></svg>
        </div>
        <div class="dt05-gbody">${R(bodyHtml)}</div>
      </section>`;
    }).join("");
    const html = T`<div class="dt05-wrap">
      <div class="dt05-strip">${R(strip)}</div>
      ${R(secs)}
    </div>`;
    /* 滚动位置自保(纵横成对): 滚动容器是宿主父级(.drawer-body, Vue 所有) —— 单点 helper */
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

  /* P3-4: 纯 div/span 模拟控件的键盘触发 —— Enter/Space 转发 click 委托; 焦点在原生
   * button/summary 等自身会发 click 的元素上时不接管(防 Enter 双重触发), 纯 div 模拟
   * (折叠组头 data-fold / msg 展开行 data-msg)没有原生 click 才需要手动转发 */
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

  function onClick(ev) {
    const h = ev.currentTarget;
    const head = ev.target.closest("[data-fold]");
    if (head) {
      const sec = head.closest("[data-grp]");
      if (sec) {
        const k = sec.getAttribute("data-grp");
        ui.folded[k] = !ui.folded[k];
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
    if (act === "report") { ctx.drawerCmd("reannounce", null, "强制汇报"); return; }
    if (act === "del") { ctx.trackerRemove(url); }
  }

  const _render = render;
  reg.register({
    id: "05", tab: "trackers",
    label: "健康分组",
    css: CSS,
    render(host, ctx) {
      wire(host);
      host.__dtCtx = ctx;
      _render(host, ctx);
    },
    destroy,
  });
})();
