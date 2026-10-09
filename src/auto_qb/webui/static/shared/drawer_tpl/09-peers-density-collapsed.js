/* auto-qb WEB UI · 详情面板 peers 页签变体 09「密度雷达表(收起改良)」(计划 26-10-06-0838 S4)
 *
 * 设计稿: resources/detail-panel-templates/09-peers-density-collapsed.html(collapsed 档;
 * 矮/高 = 30px 行距密度表自适应滚动。收起档(头部 44px 雷达摘要: 构成比例条 + 上下行
 * 合计 + 吸血 / 连接计数, 本变体 summary() 供给)已随面板折叠状态整体移除(2026-10-09)。
 * 数据: /peers qB sync 透传整包(drawer.peers, 5s 轮询); 「↑ 占用」列 = 该对端 upspeed 占
 * 当前上行合计的比重(条长 + 数值), 默认按它降序 —— 第一行就是最吃上行的对端。
 * 动作: 悬停标记(展示, CSS :hover); 筛选 chips 与列头排序为纯前端态。
 * 拍板 P-04: 悬停封禁钮 v1 省略(无后端端点), 设计稿「处置」列不落地; 迅雷红标 = client 名含
 * "XL/迅雷" 启发式(与 07/08 同判据), 纯展示(红行 + 吸血徽章, 徽章 title 说明判据)。
 * 渐进字段: country_code/connection 随 qB 版本浮动 —— cc 徽章逐行省略; flags 缺失行不猜。
 * 渲染纪律: dtHtml 全量转义(dtRaw 只用于拼接本变体 dtHtml 产出的预转义片段), replaceChildren
 * 原子换帧, 数据未变(整份 peers 序列化比对)跳过重建, 滚动位置/筛选/排序态自保。
 * 自包含: 删除本文件 + 三份 index.html 各去 1 行 manifest 即整体退役, 其它零接触。
 */
(function () {
  "use strict";
  const reg = window.AQB_DRAWER_TPL_REG;
  if (!reg) return; /* 核心未载入(清单序错): 静默退出, 守阵会抓 */
  const T = reg.dtHtml;
  const R = reg.dtRaw;
  const H = reg.helpers; /* 公共骨架单点(报告 26-10-07-0845): 工具/sig 比对/滚动自保/事件挂摘 */

  /* qB peer_info 标志位逐项解释(设计稿同款; 色映射按 S1 白名单就近取) */
  const FLAG_META = {
    D: { c: "fl-d", t: "D — 我方正在从该 peer 下载数据" },
    U: { c: "fl-u", t: "U — 我方正在向该 peer 上传数据" },
    u: { c: "fl-uo", t: "u — 对方有意向我下载, 但我方已将其限流(choked)" },
    K: { c: "fl-k", t: "K — 完整副本(对方是做种者)" },
    E: { c: "fl-e", t: "E — 加密连接" },
    H: { c: "fl-h", t: "H — 该 peer 经 DHT 引入" },
    X: { c: "fl-x", t: "X — 该 peer 经 PEX(对端交换)引入" },
    I: { c: "fl-i", t: "I — 对方主动连入(incoming)" },
    P: { c: "fl-p", t: "P — uTP 传输" },
    "?": { c: "fl-q", t: "? — 握手未完成, 状态未知" },
  };

  /* 筛选 chips: bad 档仅有嫌疑对端时出现(渐进) */
  const FILTERS = [
    { key: "all", text: "全部" },
    { key: "up", text: "上行中" },
    { key: "down", text: "下行中" },
    { key: "bad", text: "吸血嫌疑" },
    { key: "lan", text: "内网" },
  ];

  /* 视图偏好(跨重渲染与换种子保持): 筛选 / 排序 / 上行合计(占用条分母); lastSig 供跳过重建 */
  const ui = { filter: "all", sortKey: "up", sortDir: -1, upTotal: 0, lastSig: "" };

  const CSS = [
    /* 筛选 chips 行 */
    ".drawer .dt09-bar { display:flex; align-items:center; gap:6px; margin-bottom:8px; }",
    ".drawer .dt09-fchip { display:inline-flex; align-items:center; gap:5px; height:24px; padding:0 10px;",
    "  border-radius:999px; border:1px solid var(--border-soft); background:var(--surface-1);",
    "  font-size:11.5px; color:var(--fg-muted); cursor:pointer; user-select:none;",
    "  transition:border-color var(--dur) var(--ease), background var(--dur) var(--ease), color var(--dur) var(--ease); }",
    ".drawer .dt09-fchip b { font-family:var(--font-mono, ui-monospace, monospace); font-weight:600; }",
    ".drawer .dt09-fchip:hover { border-color:var(--border-strong); color:var(--fg); }",
    ".drawer .dt09-fchip.active { background:var(--accent-soft); border-color:var(--accent-line); color:var(--fg); }",
    ".drawer .dt09-fchip.c-err.active { background:var(--error-soft); border-color:var(--error-line); }",
    ".drawer .dt09-note { margin-left:auto; font-size:11.5px; color:var(--fg-dim); }",
    /* 密度表(30px 行距) */
    ".drawer .dt09-list { display:flex; flex-direction:column; }",
    ".drawer .dt09-r, .drawer .dt09-head { display:grid;",
    "  grid-template-columns:184px 150px 100px 112px minmax(160px, 1fr) 90px 74px 74px 44px;",
    "  gap:8px; align-items:center; padding:0 8px; }",
    /* 吸顶补偿: .drawer-body(滚动容器)的 padding 会内缩 sticky 视矩形 —— top:0 实际停在
     * padding-top(14px)之下, 中途滚动时行文字从那条缝里漏出来; 与 dt11 同族(机理/判据单点
     * 见 pitfalls/web-ui/sticky-scrollpad-inset.md), -14px 抵消后表头贴到可见上缘。 */
    ".drawer .dt09-head { position:sticky; top:-14px; z-index:1; height:26px; background:var(--bg-card);",
    "  border-bottom:1px solid var(--border); color:var(--fg-dim); font-size:11.5px; white-space:nowrap; }",
    ".drawer .dt09-head .num, .drawer .dt09-head .occ-h { text-align:right; }",
    ".drawer .dt09-head .occ-h { justify-content:flex-start; }",
    ".drawer .dt09-sortable { cursor:pointer; user-select:none; display:inline-flex; align-items:center;",
    "  gap:3px; width:100%; }",
    ".drawer .dt09-sortable.num, .drawer .dt09-sortable.num .chev { justify-content:flex-end; }",
    ".drawer .dt09-sortable:hover { color:var(--fg); }",
    ".drawer .dt09-sortable .chev { opacity:0; transition:opacity var(--dur) var(--ease), transform var(--dur) var(--ease); }",
    ".drawer .dt09-sortable.on { color:var(--accent); }",
    ".drawer .dt09-sortable.on .chev { opacity:1; }",
    ".drawer .dt09-sortable.asc .chev { transform:rotate(180deg); }",
    ".drawer .dt09-r { min-height:30px; border-bottom:1px solid var(--hairline); border-radius:var(--radius-sm);",
    "  font-size:12px; }",
    ".drawer .dt09-r:hover { background:var(--bg-hover); }",
    ".drawer .dt09-r.bad { background:var(--error-soft); }",
    ".drawer .dt09-r.bad:hover { box-shadow:inset 0 0 0 1px var(--error-line); }",
    ".drawer .dt09-r.lan { box-shadow:inset 2px 0 0 var(--blue); }",
    ".drawer .dt09-r.handrow { opacity:.55; }",
    /* 单元格 */
    ".drawer .dt09-addr { display:flex; align-items:center; gap:7px; min-width:0; }",
    ".drawer .dt09-cc { flex:none; min-width:26px; text-align:center; padding:1px 4px; border-radius:var(--radius-sm);",
    "  background:var(--surface-1); border:1px solid var(--border-soft);",
    "  font-family:var(--font-mono, ui-monospace, monospace); font-size:10px; color:var(--fg-dim); }",
    ".drawer .dt09-cc.lan { color:var(--blue); background:var(--blue-soft); border-color:transparent; }",
    ".drawer .dt09-ip { min-width:0; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;",
    "  font-family:var(--font-mono, ui-monospace, monospace); font-size:11.5px; color:var(--fg); }",
    ".drawer .dt09-client { display:flex; align-items:center; gap:5px; min-width:0; font-size:12px; color:var(--fg-soft); }",
    ".drawer .dt09-client .cname { min-width:0; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }",
    ".drawer .dt09-badb { flex:none; display:inline-flex; align-items:center; height:15px; padding:0 5px;",
    "  border-radius:999px; background:var(--error-soft); border:1px solid var(--error-line);",
    "  color:var(--error); font-size:10px; }",
    ".drawer .dt09-flags { display:flex; gap:3px; flex-wrap:wrap; }",
    ".drawer .dt09-fl { min-width:16px; height:16px; padding:0 3px; display:inline-flex; align-items:center;",
    "  justify-content:center; border-radius:var(--radius-sm);",
    "  font-family:var(--font-mono, ui-monospace, monospace); font-size:10.5px; font-weight:600; }",
    ".drawer .dt09-fl-d { background:var(--blue-soft); color:var(--blue); }",
    ".drawer .dt09-fl-u { background:var(--green-soft); color:var(--green); }",
    ".drawer .dt09-fl-uo { background:var(--warn-soft); color:var(--warn); }",
    ".drawer .dt09-fl-k { background:transparent; border:1px solid var(--border-strong); color:var(--fg-muted); }",
    ".drawer .dt09-fl-e { background:var(--accent-soft); color:var(--accent); }",
    ".drawer .dt09-fl-p { background:var(--blue-soft); color:var(--blue); }",
    ".drawer .dt09-fl-x { background:var(--hr-pending-soft); color:var(--hr-pending); }",
    ".drawer .dt09-fl-h { background:var(--surface-2); color:var(--fg-dim); }",
    ".drawer .dt09-fl-i { background:var(--surface-2); color:var(--fg-muted); }",
    ".drawer .dt09-fl-q { background:transparent; border:1px dashed var(--border-strong); color:var(--fg-dim); }",
    ".drawer .dt09-prog { display:flex; align-items:center; gap:7px; }",
    ".drawer .dt09-prog .bar { flex:1; position:relative; height:4px; border-radius:999px;",
    "  background:var(--bg-sunken); overflow:hidden; }",
    ".drawer .dt09-prog .bar i { position:absolute; inset:0 auto 0 0; border-radius:999px; background:var(--blue); }",
    ".drawer .dt09-prog em { font-style:normal; font-family:var(--font-mono, ui-monospace, monospace);",
    "  font-size:11.5px; color:var(--fg-muted); width:40px; text-align:right; }",
    ".drawer .dt09-prog.zero em { color:var(--fg-dim); }",
    ".drawer .dt09-none { font-family:var(--font-mono, ui-monospace, monospace); font-size:11.5px; color:var(--fg-dim); }",
    /* 「↑ 占用」列: 条长 = 占当前上行合计的比重, 色随方向令牌; 嫌疑行红 */
    ".drawer .dt09-occ { display:flex; align-items:center; gap:8px; min-width:0; }",
    ".drawer .dt09-occ .track { flex:1; height:4px; border-radius:999px; background:var(--bg-sunken); overflow:hidden; }",
    ".drawer .dt09-occ .track i { display:block; height:100%; border-radius:999px; background:var(--today-up); }",
    ".drawer .dt09-occ b { flex:none; font-family:var(--font-mono, ui-monospace, monospace); font-weight:600;",
    "  font-size:12px; color:var(--today-up); white-space:nowrap; }",
    ".drawer .dt09-occ b.z { color:var(--fg-dim); font-weight:400; }",
    ".drawer .dt09-r.bad .dt09-occ b { color:var(--error); }",
    ".drawer .dt09-r.bad .dt09-occ .track i { background:var(--error); }",
    ".drawer .dt09-dn { display:block; font-family:var(--font-mono, ui-monospace, monospace); font-weight:600;",
    "  font-size:12px; color:var(--today-down); text-align:right; white-space:nowrap; }",
    ".drawer .dt09-dn.z { color:var(--fg-dim); font-weight:400; }",
    ".drawer .dt09-amt { display:block; font-family:var(--font-mono, ui-monospace, monospace); font-size:11.5px;",
    "  color:var(--fg-soft); text-align:right; white-space:nowrap; }",
    ".drawer .dt09-amt.z { color:var(--fg-dim); }",
    ".drawer .dt09-rel { display:block; font-family:var(--font-mono, ui-monospace, monospace); font-size:11.5px;",
    "  color:var(--fg-muted); text-align:right; }",
    ".drawer .dt09-empty { padding:26px 0; text-align:center; color:var(--fg-dim); font-size:12px; }",
  ].join("\n");

  /* ---------------- 派生(与 07/08 同判据) ---------------- */
  function peerList(ctx) {
    const p = (ctx.drawer && ctx.drawer.peers) || {};
    return Array.isArray(p.peers) ? p.peers : Object.values(p.peers || {});
  }
  const { num } = H; /* 公共工具: Number(v)||0(核心层单点) */
  function flagTokens(p) {
    return String(p.flags || "").split(/\s+/).filter(Boolean);
  }
  /* 吸血嫌疑启发式: client 名含 "XL/迅雷", 纯展示 */
  function isBad(p) {
    const c = String(p.client || "");
    return c.indexOf("迅雷") >= 0 || /(^|[^A-Za-z])XL([^A-Za-z]|$)/.test(c);
  }
  function bucketOf(p) {
    const f = flagTokens(p);
    if (!f.length || f.indexOf("?") >= 0) return "hand";
    if (f.indexOf("u") >= 0) return "choke";
    if (f.indexOf("U") >= 0) return "take";
    if (f.indexOf("D") >= 0) return "feed";
    return "idle";
  }
  function isLanIp(ip) {
    const s = String(ip || "");
    if (s.indexOf(":") >= 0) return /^fe80:/i.test(s) || s === "::1";
    const m = /^(\d+)\.(\d+)\.(\d+)\.(\d+)/.exec(s);
    if (!m) return false;
    const a = +m[1], b = +m[2];
    return a === 10 || a === 127 || (a === 192 && b === 168) || (a === 172 && b >= 16 && b <= 31);
  }
  function countOf(list, key) {
    if (key === "all") return list.length;
    if (key === "up") return list.filter((p) => num(p.upspeed) > 0).length;
    if (key === "down") return list.filter((p) => num(p.dlspeed) > 0).length;
    if (key === "bad") return list.filter(isBad).length;
    if (key === "lan") return list.filter((p) => isLanIp(p.ip)).length;
    return 0;
  }
  function filtered(list) {
    const f = ui.filter;
    if (f === "all") return list;
    return list.filter((p) => countOf([p], f) > 0);
  }
  function sorted(list) {
    const k = ui.sortKey, dir = ui.sortDir;
    const val = (p) => {
      if (k === "prog") return num(p.progress);
      if (k === "up") return num(p.upspeed);
      if (k === "down") return num(p.dlspeed);
      if (k === "sent") return num(p.uploaded);
      if (k === "recv") return num(p.downloaded);
      return num(p.relevance);
    };
    return list.slice().sort((a, b) => (val(a) - val(b)) * dir);
  }

  let _ctx = null; /* render 期只读引用(纯格式化) */
  const fmtSpeedOf = (v) => _ctx.fmtSpeed(v);
  const fmtSizeOf = (v) => _ctx.fmtSize(v);

  /* ---------------- 单元格 ---------------- */
  function flagsHtml(p) {
    const f = flagTokens(p);
    if (!f.length) return T`<span class="dt09-none" title="flags 缺失">—</span>`;
    return T`${R(f.map((x) => {
      const m = FLAG_META[x];
      return m
        ? T`<span class="dt09-fl ${m.c}" title="${m.t}">${x}</span>`
        : T`<span class="dt09-fl fl-h">${x}</span>`;
    }).join(""))}`;
  }
  function addrHtml(p) {
    const lan = isLanIp(p.ip);
    const cc = lan
      ? T`<span class="dt09-cc lan" title="局域网直连(私有地址段启发式)">内网</span>`
      : (p.country_code
        ? T`<span class="dt09-cc" title="${p.country || p.country_code}">${p.country_code}</span>`
        : "");
    const conn = p.connection ? " · " + p.connection : "";
    return T`<span class="dt09-addr">${R(cc)}<span class="dt09-ip" title="${p.ip || "?"}:${p.port || ""}${conn}">${p.ip || "?"}${p.port ? ":" + p.port : ""}</span></span>`;
  }
  function clientHtml(p) {
    const badge = isBad(p)
      ? T`<span class="dt09-badb" title="吸血嫌疑 = client 名含 XL/迅雷 启发式, 纯展示">吸血</span>`
      : "";
    return T`<span class="dt09-client"><span class="cname" title="${p.client || "未知"}">${p.client || "未知"}</span>${R(badge)}</span>`;
  }
  function progHtml(p) {
    const pct = Math.round((p.progress || 0) * 100);
    return T`<span class="dt09-prog${pct === 0 ? " zero" : ""}" title="对端自身进度 ${pct}%">
      <span class="bar"><i style="width:${pct}%"></i></span><em>${pct}%</em></span>`;
  }
  function occHtml(p) {
    const v = num(p.upspeed);
    const b = v > 0 ? T`<b>${fmtSpeedOf(v)}</b>` : T`<b class="z">0</b>`;
    const bar = v > 0 && ui.upTotal > 0
      ? T`<span class="track"><i style="width:${(v / ui.upTotal * 100).toFixed(1)}%"></i></span>`
      : "";
    return T`<span class="dt09-occ" title="我方发给该对端的即时速度(qB upspeed); 条长 = 占当前上行合计(${fmtSpeedOf(ui.upTotal)})的比重">${R(bar)}${R(b)}</span>`;
  }
  const dnHtml = (p) => (num(p.dlspeed) > 0
    ? T`<span class="dt09-dn" title="我方从该对端收到的即时速度(qB dlspeed)">${fmtSpeedOf(num(p.dlspeed))}</span>`
    : T`<span class="dt09-dn z" title="我方从该对端收到的即时速度(qB dlspeed)">0</span>`);
  const amtHtml = (v) => (num(v) > 0
    ? T`<span class="dt09-amt">${fmtSizeOf(v)}</span>`
    : T`<span class="dt09-amt z">0</span>`);
  const relHtml = (p) =>
    T`<span class="dt09-rel" title="relevance: 该对端拥有我缺失数据的比例">${Math.round((p.relevance || 0) * 100)}%</span>`;

  function rowHtml(p) {
    const cls = ["dt09-r", isBad(p) ? "bad" : "", isLanIp(p.ip) ? "lan" : "",
      bucketOf(p) === "hand" ? "handrow" : ""].filter(Boolean).join(" ");
    return T`<div class="${cls}">
      ${R(addrHtml(p))}${R(clientHtml(p))}<span class="dt09-flags">${R(flagsHtml(p))}</span>${R(progHtml(p))}${R(occHtml(p))}
      ${R(dnHtml(p))}${R(amtHtml(p.uploaded))}${R(amtHtml(p.downloaded))}${R(relHtml(p))}
    </div>`;
  }

  function headHtml() {
    const seg = (k, text, tip, numCls) => {
      const on = ui.sortKey === k;
      /* P3-4(报告 26-10-07-0542): 排序表头纯 span 模拟控件补键盘达 + aria-sort(升/降/无
       * 随当前排序态在渲染函数里输出) */
      const asort = !on ? "none" : (ui.sortDir === 1 ? "ascending" : "descending");
      return T`<span class="${numCls} dt09-sortable${on ? " on" : ""}${on && ui.sortDir === 1 ? " asc" : ""}"
        role="button" tabindex="0" aria-sort="${asort}" data-sort="${k}" title="${tip}">${text}<svg class="ico ico-sm chev" viewBox="0 0 16 16"><use href="#i-chevron"></use></svg></span>`;
    };
    return T`<div class="dt09-head">
      <span>对端</span>
      <span>客户端</span>
      <span title="qB peer_info 标志位, 悬停每个字母看逐项解释">Flags</span>
      ${R(seg("prog", "进度", "对端自身进度", "num"))}
      ${R(seg("up", "↑ 占用", "我方发给该对端的即时速度(qB upspeed); 条长 = 该对端占当前上行合计的比重", "occ-h num"))}
      ${R(seg("down", "下行", "我方从该对端收到的即时速度(qB dlspeed)", "num"))}
      ${R(seg("sent", "已发", "本次会话我方已发给该对端的累计(qB uploaded)", "num"))}
      ${R(seg("recv", "已收", "本次会话我方已从该对端收到的累计(qB downloaded)", "num"))}
      ${R(seg("rel", "关联", "relevance: 该对端拥有我缺失数据的比例", "num"))}
    </div>`;
  }

  function render(host, ctx) {
    const list = peerList(ctx);
    const loading = ctx.drawer && ctx.drawer.peersLoading;
    /* P3-5(报告 26-10-07-0542): fetch 失败标记 —— 失败与「真没有」在变体里不同形态 */
    const err = (ctx.drawer && ctx.drawer.peersError) || "";
    /* 数据未变跳过重建(5s 通知频度下不闪不丢态) */
    const sig = JSON.stringify(ctx.drawer && ctx.drawer.peers) + "|" + String(!!loading) + "|" + err;
    if (H.skipUnchanged(host, ui, sig)) return;
    _ctx = ctx;
    ui.upTotal = list.reduce((s, p) => s + num(p.upspeed), 0);
    if (loading && !list.length) {
      host.replaceChildren(document.createRange().createContextualFragment(
        T`<div class="dt09-empty"><svg class="ico" viewBox="0 0 16 16"><use href="#i-hourglass"></use></svg><span>正在加载…</span></div>`));
      return;
    }
    /* 错误态先于空态(P3-5): 失败且无数据不是"真的没有", 重试口径真实(本页签 5s 轮询会自动重拉) */
    if (err && !list.length) {
      host.replaceChildren(document.createRange().createContextualFragment(
        T`<div class="dt09-empty"><svg class="ico" viewBox="0 0 16 16"><use href="#i-warn"></use></svg><span title="${err}">用户列表加载失败, 将在下次自动刷新时重试</span></div>`));
      return;
    }
    if (!list.length) {
      host.replaceChildren(document.createRange().createContextualFragment(
        T`<div class="dt09-empty"><span>暂无已连接用户</span></div>`));
      return;
    }
    const chips = FILTERS.filter((f) => f.key !== "bad" || countOf(list, "bad") > 0).map((f) =>
      T`<button type="button" class="dt09-fchip${ui.filter === f.key ? " active" : ""}${f.key === "bad" ? " c-err" : ""}" data-f="${f.key}">${f.text} <b>${countOf(list, f.key)}</b></button>`).join("");
    const rows = sorted(filtered(list)).map(rowHtml).join("");
    const html = T`<div class="dt09-wrap">
      <div class="dt09-bar">${R(chips)}
        <span class="dt09-note">默认按「↑ 占用」降序, 最吃上行的排最前 · 5s 自动刷新</span>
      </div>
      <div class="dt09-list">${R(headHtml())}${R(rows)}</div>
    </div>`;
    /* 纵横滚动位成对自保(表格定宽 grid 窄窗口下必有横向滚动, 整帧重建只还 scrollTop 会把
     * 用户的横向滚动位打回最左) —— 单点 helper */
    H.withScroll(host, () => {
      host.replaceChildren(document.createRange().createContextualFragment(html));
    });
  }

  

  function onClick(ev) {
    const h = ev.currentTarget;
    const chip = ev.target.closest("[data-f]");
    if (chip) {
      ui.filter = chip.getAttribute("data-f") || "all";
      rerender(h);
      return;
    }
    const seg = ev.target.closest("[data-sort]");
    if (seg) {
      const k = seg.getAttribute("data-sort");
      if (ui.sortKey === k) ui.sortDir = -ui.sortDir;
      else { ui.sortKey = k; ui.sortDir = -1; }
      rerender(h);
    }
  }

  /* 视图偏好变化后的强制重渲染(sig 不含偏好, 置空 lastSig 即可; 口径同 04) */
  function rerender(host) {
    ui.lastSig = "";
    const ctx = host.__dtCtx;
    if (ctx) _render(host, ctx);
  }

  /* P3-4: 排序表头纯 span 模拟控件(data-sort)的键盘触发 —— Enter/Space 转发 click 委托;
   * 焦点在原生 button 等自身会发 click 的元素上时不接管(防 Enter 双重触发) */
  function onKeyDown(ev) {
    if (ev.key !== "Enter" && ev.key !== " ") return;
    if (ev.target.closest("button, input, select, textarea, a[href], summary")) return;
    if (!ev.target.closest("[data-sort]")) return;
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
    id: "09", tab: "peers",
    label: "密度雷达",
    css: CSS,
    render(host, ctx) {
      wire(host);
      host.__dtCtx = ctx;
      _render(host, ctx);
    },
    destroy,
  });
})();
