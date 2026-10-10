/* auto-qb WEB UI · 详情面板 peers 页签变体 08「语义分区(五区折叠)」(计划 26-10-06-0838 S4)
 *
 * 设计稿: resources/detail-panel-templates/08-peers-groups-low.html(low 档; 收起/矮/高三档
 * 语义全部收进本变体 —— 收起 = 核心内置摘要条, 矮/高 = 分区列表自适应滚动)。
 * 数据: /peers qB sync 透传整包(drawer.peers, 5s 轮询); 五区按 flags 派生(纯 flags 判据,
 * 与 07/09 同函数): take(U)/ feed(D)/ idle(其余, 含 K 完整副本)/ choke(u)/ hand(?或空);
 * 组头聚合数随 5s 轮询刷新; 组头折叠(折叠态自保, 仅记用户显式翻过的组); 「只看在传数据」
 * 一键收起安静分区(idle/hand 整组隐藏)。
 * 动作: 分组折叠 + 只看在传数据过滤(纯前端, plan §4 映射行)。
 * 吸血嫌疑 = client 名含 "XL/迅雷" 启发式, 纯展示红标(与 07/09 同判据)。
 * 渐进字段: country_code/connection/files 随 qB 版本浮动 —— files 整列省略、cc 徽章逐行省略;
 * 关联度列设计稿未纳入(分区语义已隐含), 空分区整节隐藏。
 * 渲染纪律: dtHtml 全量转义(dtRaw 只用于拼接本变体 dtHtml 产出的预转义片段), replaceChildren
 * 原子换帧, 数据未变(整份 peers 序列化比对)跳过重建, 滚动位置/折叠/筛选/排序态自保。
 * 自包含: 删除本文件 + 三份 index.html 各去 1 行 manifest 即整体退役, 其它零接触。
 */
(function () {
  "use strict";
  const reg = window.AQB_DRAWER_TPL_REG;
  if (!reg) return; /* 核心未载入(清单序错): 静默退出, 守阵会抓 */
  const T = reg.dtHtml;
  const R = reg.dtRaw;
  const H = reg.helpers; /* 公共骨架单点(报告 26-10-07-0845): 工具/sig 比对/滚动自保/事件挂摘 */

  /* 分区定义: 顺序即设计稿五区; quiet = 「只看在传数据」过滤的目标外分区 */
  const GROUPS = [
    { key: "take", text: "上传中", color: "--today-up", tip: "对端正在从我方下载数据(U flag); HR 做种时间的来源", quiet: false },
    { key: "feed", text: "下载中", color: "--today-down", tip: "对端正在向我方供数(D flag), 补齐我缺失的数据", quiet: false },
    { key: "idle", text: "闲置同伴", color: "--border-strong", tip: "完整副本且当前无流量的同伴", quiet: true },
    { key: "choke", text: "被我方限流", color: "--warn", tip: "对方有意下载, 但我方已将其限流(u flag)", quiet: false },
    { key: "hand", text: "握手中", color: "--fg-dim", tip: "握手未完成, 客户端与进度未知", quiet: true },
  ];

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

  const SORTS = ["prog", "up", "down", "sent", "recv"];

  /* 视图偏好(跨重渲染与换种子保持): 只看在传数据 / 组折叠(默认 idle/hand 收起) /
   * 组内排序; lastSig 供跳过重建 */
  const ui = { onlyMoving: false, folded: { idle: true, hand: true }, sortKey: "up", sortDir: -1,
    maxUp: 1, maxDown: 1, lastSig: "" };

  const CSS = [
    /* 工具行 */
    ".drawer .dt08-bar { display:flex; align-items:center; gap:10px; margin-bottom:9px; }",
    ".drawer .dt08-note { font-size:11.5px; color:var(--fg-dim); }",
    ".drawer .dt08-spacer { flex:1; }",
    ".drawer .dt08-toggle { display:inline-flex; align-items:center; gap:6px; height:24px; padding:0 10px;",
    "  border-radius:var(--radius-sm); border:1px solid var(--border-soft); background:var(--surface-1);",
    "  font-size:11.5px; color:var(--fg-muted); cursor:pointer; user-select:none;",
    "  transition:border-color var(--dur) var(--ease), background var(--dur) var(--ease), color var(--dur) var(--ease); }",
    ".drawer .dt08-toggle:hover { border-color:var(--border-strong); color:var(--fg); }",
    ".drawer .dt08-toggle.active { background:var(--bg-hover); border-color:var(--accent-line); color:var(--fg); }",
    ".drawer .dt08-toggle i { width:6px; height:6px; border-radius:50%; background:var(--fg-dim); }",
    ".drawer .dt08-toggle.active i { background:var(--accent); }",
    /* 分区 */
    ".drawer .dt08-grp { margin-bottom:10px; background:var(--bg-row); border:1px solid var(--border);",
    "  border-radius:var(--radius); overflow:hidden; }",
    ".drawer .dt08-grp.g-take { box-shadow:inset 2px 0 0 var(--today-up); }",
    ".drawer .dt08-grp.g-feed { box-shadow:inset 2px 0 0 var(--today-down); }",
    ".drawer .dt08-grp.g-idle { box-shadow:inset 2px 0 0 var(--border-strong); }",
    ".drawer .dt08-grp.g-choke { box-shadow:inset 2px 0 0 var(--warn); }",
    ".drawer .dt08-grp.g-hand { box-shadow:inset 2px 0 0 var(--fg-dim); }",
    ".drawer .dt08-ghead { display:flex; align-items:center; gap:8px; min-height:36px; padding:0 12px;",
    "  cursor:pointer; user-select:none; }",
    ".drawer .dt08-ghead:hover { background:var(--surface-1); }",
    ".drawer .dt08-chev { width:13px; height:13px; flex:none; color:var(--fg-dim);",
    "  transition:transform var(--dur) var(--ease); }",
    ".drawer .dt08-grp.folded .dt08-chev { transform:rotate(-90deg); }",
    ".drawer .dt08-dot { width:7px; height:7px; border-radius:50%; flex:none; }",
    ".drawer .dt08-gname { font-size:12.5px; font-weight:600; color:var(--fg); white-space:nowrap; }",
    ".drawer .dt08-gcnt { flex:none; font-family:var(--font-mono, ui-monospace, monospace); font-size:11px;",
    "  color:var(--fg-muted); background:var(--surface-2); border-radius:999px; padding:1px 7px; }",
    ".drawer .dt08-gagg { margin-left:auto; min-width:0; overflow:hidden; text-overflow:ellipsis;",
    "  white-space:nowrap; font-family:var(--font-mono, ui-monospace, monospace); font-size:11.5px;",
    "  color:var(--fg-muted); }",
    ".drawer .dt08-gagg b { color:var(--fg); font-weight:600; }",
    ".drawer .dt08-grp.g-take .dt08-gagg b { color:var(--today-up); }",
    ".drawer .dt08-grp.g-feed .dt08-gagg b { color:var(--today-down); }",
    ".drawer .dt08-rows { display:none; flex-direction:column; border-top:1px solid var(--hairline); }",
    ".drawer .dt08-grp:not(.folded) .dt08-rows { display:flex; }",
    /* 行(grid 10 列: 对端/客户端/Flags/正在取/进度/上传/下载/已发/已收/关联) */
    ".drawer .dt08-r, .drawer .dt08-gcols { display:grid;",
    "  grid-template-columns:180px 140px 96px minmax(96px, 1fr) 104px 96px 88px 72px 72px 44px;",
    "  gap:8px; align-items:center; padding:0 12px; min-height:33px; }",
    /* files 整列省略时: 9 列(关联列并入末列宽) */
    ".drawer .dt08-r.nofiles, .drawer .dt08-gcols.nofiles {",
    "  grid-template-columns:180px 140px 96px minmax(120px, 1fr) 104px 96px 88px 72px 72px; }",
    ".drawer .dt08-gcols { min-height:26px; background:var(--surface-1); color:var(--fg-dim);",
    "  font-size:11.5px; white-space:nowrap; }",
    ".drawer .dt08-rows .dt08-r:not(.gcols) { border-bottom:1px solid var(--hairline); border-radius:var(--radius-sm); }",
    ".drawer .dt08-rows .dt08-r:not(.gcols):hover { background:var(--bg-hover); }",
    ".drawer .dt08-r.bad { background:var(--error-soft); }",
    ".drawer .dt08-r.bad:hover { box-shadow:inset 0 0 0 1px var(--error-line); }",
    ".drawer .dt08-r.lan { box-shadow:inset 2px 0 0 var(--blue); }",
    ".drawer .dt08-r.handrow { opacity:.55; }",
    ".drawer .dt08-headcell.num, .drawer .dt08-cellr { text-align:right; }",
    ".drawer .dt08-sortable { cursor:pointer; user-select:none; display:inline-flex; align-items:center;",
    "  gap:3px; justify-content:flex-end; width:100%; }",
    ".drawer .dt08-sortable:hover { color:var(--fg); }",
    ".drawer .dt08-sortable .chev { opacity:0; transition:opacity var(--dur) var(--ease), transform var(--dur) var(--ease); }",
    ".drawer .dt08-sortable.on { color:var(--accent); }",
    ".drawer .dt08-sortable.on .chev { opacity:1; }",
    ".drawer .dt08-sortable.asc .chev { transform:rotate(180deg); }",
    /* 单元格(与 07 同款尺寸) */
    ".drawer .dt08-addr { display:flex; align-items:center; gap:7px; min-width:0; }",
    ".drawer .dt08-cc { flex:none; min-width:26px; text-align:center; padding:1px 4px; border-radius:var(--radius-sm);",
    "  background:var(--surface-1); border:1px solid var(--border-soft);",
    "  font-family:var(--font-mono, ui-monospace, monospace); font-size:10px; color:var(--fg-dim); }",
    ".drawer .dt08-cc.lan { color:var(--blue); background:var(--blue-soft); border-color:transparent; }",
    ".drawer .dt08-ip { min-width:0; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;",
    "  font-family:var(--font-mono, ui-monospace, monospace); font-size:12px; color:var(--fg); }",
    ".drawer .dt08-client { display:flex; align-items:center; gap:5px; min-width:0; font-size:12px; color:var(--fg-soft); }",
    ".drawer .dt08-client .cname { min-width:0; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }",
    ".drawer .dt08-badb { flex:none; display:inline-flex; align-items:center; height:15px; padding:0 5px;",
    "  border-radius:999px; background:var(--error-soft); border:1px solid var(--error-line);",
    "  color:var(--error); font-size:10px; }",
    ".drawer .dt08-flags { display:flex; gap:3px; flex-wrap:wrap; }",
    ".drawer .dt08-fl { min-width:16px; height:16px; padding:0 3px; display:inline-flex; align-items:center;",
    "  justify-content:center; border-radius:var(--radius-sm);",
    "  font-family:var(--font-mono, ui-monospace, monospace); font-size:10.5px; font-weight:600; }",
    ".drawer .dt08-fl-d { background:var(--blue-soft); color:var(--blue); }",
    ".drawer .dt08-fl-u { background:var(--green-soft); color:var(--green); }",
    ".drawer .dt08-fl-uo { background:var(--warn-soft); color:var(--warn); }",
    ".drawer .dt08-fl-k { background:transparent; border:1px solid var(--border-strong); color:var(--fg-muted); }",
    ".drawer .dt08-fl-e { background:var(--accent-soft); color:var(--accent); }",
    ".drawer .dt08-fl-p { background:var(--blue-soft); color:var(--blue); }",
    ".drawer .dt08-fl-x { background:var(--hr-pending-soft); color:var(--hr-pending); }",
    ".drawer .dt08-fl-h { background:var(--surface-2); color:var(--fg-dim); }",
    ".drawer .dt08-fl-i { background:var(--surface-2); color:var(--fg-muted); }",
    ".drawer .dt08-fl-q { background:transparent; border:1px dashed var(--border-strong); color:var(--fg-dim); }",
    ".drawer .dt08-files { display:block; min-width:0; overflow:hidden; text-overflow:ellipsis;",
    "  white-space:nowrap; font-size:11.5px; color:var(--fg-muted); }",
    ".drawer .dt08-files.dimc { color:var(--fg-dim); }",
    ".drawer .dt08-prog { display:flex; align-items:center; gap:7px; }",
    ".drawer .dt08-prog .bar { flex:1; position:relative; height:5px; border-radius:999px;",
    "  background:var(--bg-sunken); overflow:hidden; }",
    ".drawer .dt08-prog .bar i { position:absolute; inset:0 auto 0 0; border-radius:999px; background:var(--blue); }",
    ".drawer .dt08-prog em { font-style:normal; font-family:var(--font-mono, ui-monospace, monospace);",
    "  font-size:11.5px; color:var(--fg-muted); width:40px; text-align:right; }",
    ".drawer .dt08-prog.zero em { color:var(--fg-dim); }",
    ".drawer .dt08-none { font-family:var(--font-mono, ui-monospace, monospace); font-size:12px; color:var(--fg-dim); }",
    /* 速度微条: 上传 = --today-up / 下载 = --today-down(方向色令牌) */
    ".drawer .dt08-spd { display:flex; flex-direction:column; align-items:flex-end; gap:3px; min-width:0; }",
    ".drawer .dt08-spd b { font-family:var(--font-mono, ui-monospace, monospace); font-weight:600; font-size:12px;",
    "  line-height:1; white-space:nowrap; }",
    ".drawer .dt08-spd.u b { color:var(--today-up); }",
    ".drawer .dt08-spd.d b { color:var(--today-down); }",
    ".drawer .dt08-spd b.z { color:var(--fg-dim); font-weight:400; }",
    ".drawer .dt08-spd .track { width:100%; height:3px; border-radius:999px; background:var(--bg-sunken); overflow:hidden; }",
    ".drawer .dt08-spd .track i { display:block; height:100%; border-radius:999px; }",
    ".drawer .dt08-amt { display:block; font-family:var(--font-mono, ui-monospace, monospace); font-size:11.5px;",
    "  color:var(--fg-soft); text-align:right; white-space:nowrap; }",
    ".drawer .dt08-amt.z { color:var(--fg-dim); }",
    ".drawer .dt08-rel { display:block; font-family:var(--font-mono, ui-monospace, monospace); font-size:11.5px;",
    "  color:var(--fg-muted); text-align:right; }",
    ".drawer .dt08-empty { padding:26px 0; text-align:center; color:var(--fg-dim); font-size:12px; }",
  ].join("\n");

  /* ---------------- 派生(与 07/09 同判据) ---------------- */
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

  /* 组头聚合(设计稿同款口径) */
  function aggText(key, ms) {
    const sum = (k) => ms.reduce((s, p) => s + num(p[k]), 0);
    if (key === "take") return T`↑ <b>${fmtSpeedOf(sum("upspeed"))}</b> · 会话已上传 <b>${fmtSizeOf(sum("uploaded"))}</b>`;
    if (key === "feed") return T`↓ <b>${fmtSpeedOf(sum("dlspeed"))}</b> · 会话已下载 <b>${fmtSizeOf(sum("downloaded"))}</b>`;
    if (key === "idle") return T`完整副本同伴 · 当前无流量`;
    if (key === "choke") return T`对方有意 · 我方已限流`;
    return T`握手未完成`;
  }

  let _ctx = null; /* render 期只读引用(纯格式化; 动作链仍走 host.__dtCtx) */
  const fmtSpeedOf = (v) => _ctx.fmtSpeed(v);
  const fmtSizeOf = (v) => _ctx.fmtSize(v);

  /* ---------------- 单元格(与 07 同款) ---------------- */
  function flagsHtml(p) {
    const f = flagTokens(p);
    if (!f.length) return T`<span class="dt08-none" title="flags 缺失">—</span>`;
    return T`${R(f.map((x) => {
      const m = FLAG_META[x];
      return m
        ? T`<span class="dt08-fl ${m.c}" title="${m.t}">${x}</span>`
        : T`<span class="dt08-fl fl-h">${x}</span>`;
    }).join(""))}`;
  }
  function addrHtml(p) {
    const lan = isLanIp(p.ip);
    const cc = lan
      ? T`<span class="dt08-cc lan" title="局域网直连(私有地址段启发式)">内网</span>`
      : (p.country_code
        ? T`<span class="dt08-cc" title="${p.country || p.country_code}">${p.country_code}</span>`
        : "");
    const conn = p.connection ? " · " + p.connection : "";
    return T`<span class="dt08-addr">${R(cc)}<span class="dt08-ip" title="${p.ip || "?"}:${p.port || ""}${conn}">${p.ip || "?"}${p.port ? ":" + p.port : ""}</span></span>`;
  }
  function clientHtml(p) {
    const badge = isBad(p)
      ? T`<span class="dt08-badb" title="吸血嫌疑 = client 名含 XL/迅雷 启发式, 纯展示">吸血</span>`
      : "";
    return T`<span class="dt08-client"><span class="cname" title="${p.client || "未知"}">${p.client || "未知"}</span>${R(badge)}</span>`;
  }
  function progHtml(p) {
    const pct = Math.round((p.progress || 0) * 100);
    return T`<span class="dt08-prog${pct === 0 ? " zero" : ""}" title="对端自身进度 ${pct}%">
      <span class="bar"><i style="width:${pct}%"></i></span><em>${pct}%</em></span>`;
  }
  function spdHtml(p, dir, maxV) {
    const v = num(dir === "u" ? p.upspeed : p.dlspeed);
    const b = v > 0 ? T`<b>${fmtSpeedOf(v)}</b>` : T`<b class="z">0</b>`;
    const bar = v > 0 && maxV > 0
      ? T`<span class="track"><i style="width:${(v / maxV * 100).toFixed(1)}%"></i></span>`
      : "";
    return T`<span class="dt08-spd ${dir}">${R(b)}${R(bar)}</span>`;
  }
  const amtHtml = (v) => (num(v) > 0
    ? T`<span class="dt08-amt">${fmtSizeOf(v)}</span>`
    : T`<span class="dt08-amt z">0</span>`);
  const relHtml = (p) =>
    T`<span class="dt08-rel" title="relevance: 该对端拥有我缺失数据的比例">${Math.round((p.relevance || 0) * 100)}%</span>`;

  function rowHtml(p, hasFiles) {
    /* nofiles 必须与列头同进退: 列头无 files 时已切 9 列网格(.dt08-gcols.nofiles),
     * 行若仍走 10 列网格而只渲染 9 格, 1fr 列两侧宽度各算各的(头部 1fr 多吞
     * 44px 末列 + 1 个 gap 的份额), 「进度」起的所有列整体错位(用户报) */
    const cls = ["dt08-r", hasFiles ? "" : "nofiles", isBad(p) ? "bad" : "", isLanIp(p.ip) ? "lan" : "",
      bucketOf(p) === "hand" ? "handrow" : ""].filter(Boolean).join(" ");
    const files = hasFiles
      ? (p.files
        ? T`<span class="dt08-files" title="对端正在获取的文件(qB files 字段)">${p.files}</span>`
        : T`<span class="dt08-files dimc">—</span>`)
      : "";
    return T`<div class="${cls}">
      ${R(addrHtml(p))}${R(clientHtml(p))}<span class="dt08-flags">${R(flagsHtml(p))}</span>${R(files)}${R(progHtml(p))}
      ${R(spdHtml(p, "u", ui.maxUp))}${R(spdHtml(p, "d", ui.maxDown))}
      ${R(amtHtml(p.uploaded))}${R(amtHtml(p.downloaded))}${R(relHtml(p))}
    </div>`;
  }

  function colHeadHtml(hasFiles) {
    const seg = (k, text, tip) => {
      const on = ui.sortKey === k;
      /* P3-4(报告 26-10-07-0542): 排序表头纯 span 模拟控件补键盘达 + aria-sort(升/降/无
       * 随当前排序态在渲染函数里输出) */
      const asort = !on ? "none" : (ui.sortDir === 1 ? "ascending" : "descending");
      return T`<span class="dt08-headcell num dt08-sortable${on ? " on" : ""}${on && ui.sortDir === 1 ? " asc" : ""}"
        role="button" tabindex="0" aria-sort="${asort}" data-sort="${k}" title="${tip}">${text}<svg class="ico ico-sm chev" viewBox="0 0 16 16"><use href="#i-chevron"></use></svg></span>`;
    };
    return T`<div class="dt08-gcols${hasFiles ? "" : " nofiles"}">
      <span>IP/地址</span>
      <span>客户端</span>
      <span title="qB peer_info 标志位, 悬停每个字母看逐项解释">标志</span>
      ${R(hasFiles ? T`<span title="对端正在获取的文件(qB files 字段)">文件</span>` : "")}
      ${R(seg("prog", "进度", "对端自身进度"))}
      ${R(seg("up", "上传速度", "我方发给该对端的即时速度(qB upspeed)"))}
      ${R(seg("down", "下载速度", "我方从该对端收到的即时速度(qB dlspeed)"))}
      ${R(seg("sent", "已上传", "本次会话我方已发给该对端的累计(qB uploaded)"))}
      ${R(seg("recv", "已下载", "本次会话我方已从该对端收到的累计(qB downloaded)"))}
      <span class="dt08-headcell num" title="relevance: 该对端拥有我缺失数据的比例">文件关联</span>
    </div>`;
  }

  function groupHtml(g, ms, hasFiles) {
    const folded = ui.folded[g.key] ? " folded" : "";
    const rows = sorted(ms).map((p) => rowHtml(p, hasFiles)).join("");
    return T`<section class="dt08-grp g-${g.key}${folded}" data-grp="${g.key}">
      <!-- P3-4: 折叠组头纯 div 模拟控件补键盘达(role=button + tabindex + aria-expanded) -->
      <div class="dt08-ghead" role="button" tabindex="0" aria-expanded="${folded ? "false" : "true"}"
           data-fold title="${g.tip} · 点击折叠 / 展开">
        <svg class="ico ico-sm dt08-chev" viewBox="0 0 16 16"><use href="#i-chevron"></use></svg>
        <span class="dt08-dot" style="background:var(${g.color})"></span>
        <span class="dt08-gname">${g.text}</span>
        <span class="dt08-gcnt">${ms.length}</span>
        <span class="dt08-gagg">${R(aggText(g.key, ms))}</span>
      </div>
      <div class="dt08-rows">${R(colHeadHtml(hasFiles))}${R(rows)}</div>
    </section>`;
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

  function render(host, ctx) {
    const list = peerList(ctx);
    const loading = ctx.drawer && ctx.drawer.peersLoading;
    /* P3-5(报告 26-10-07-0542): fetch 失败标记 —— 失败与「真没有」在变体里不同形态 */
    const err = (ctx.drawer && ctx.drawer.peersError) || "";
    /* 数据未变跳过重建(5s 通知频度下不闪不丢态, 组头聚合数随落袋数据刷新) */
    const sig = JSON.stringify(ctx.drawer && ctx.drawer.peers) + "|" + String(!!loading) + "|" + err;
    if (H.skipUnchanged(host, ui, sig)) return;
    _ctx = ctx;
    ui.maxUp = Math.max.apply(null, [1].concat(list.map((p) => num(p.upspeed))));
    ui.maxDown = Math.max.apply(null, [1].concat(list.map((p) => num(p.dlspeed))));
    if (loading && !list.length) {
      host.replaceChildren(document.createRange().createContextualFragment(
        T`<div class="dt08-empty"><svg class="ico" viewBox="0 0 16 16"><use href="#i-hourglass"></use></svg><span>正在加载…</span></div>`));
      return;
    }
    /* 错误态先于空态(P3-5): 失败且无数据不是"真的没有", 重试口径真实(本页签 5s 轮询会自动重拉) */
    if (err && !list.length) {
      host.replaceChildren(document.createRange().createContextualFragment(
        T`<div class="dt08-empty"><svg class="ico" viewBox="0 0 16 16"><use href="#i-warn"></use></svg><span title="${err}">用户列表加载失败, 将在下次自动刷新时重试</span></div>`));
      return;
    }
    if (!list.length) {
      host.replaceChildren(document.createRange().createContextualFragment(
        T`<div class="dt08-empty"><span>暂无已连接用户</span></div>`));
      return;
    }
    const hasFiles = list.some((p) => p.files);
    /* 五区分桶(空分区整节隐藏; 「只看在传数据」= quiet 分区整组隐藏) */
    const buckets = { take: [], feed: [], idle: [], choke: [], hand: [] };
    for (const p of list) buckets[bucketOf(p)].push(p);
    const groups = GROUPS
      .filter((g) => buckets[g.key].length && !(ui.onlyMoving && g.quiet))
      .map((g) => groupHtml(g, buckets[g.key], hasFiles));
    const body = groups.length
      ? groups.join("")
      : T`<div class="dt08-empty"><span>该过滤下没有对端连接</span></div>`;
    const html = T`<div class="dt08-wrap">
      <div class="dt08-bar">
        <span class="dt08-note">按「这条连接此刻在干什么」分五区 · 点击组头折叠 / 展开 · 组头聚合数随 5s 轮询刷新</span>
        <span class="dt08-spacer"></span>
        <button type="button" class="dt08-toggle${ui.onlyMoving ? " active" : ""}" data-toggle
          title="收起「闲置同伴 / 握手中」等无流量分区, 只看正在传输数据的连接"><i></i>只看在传数据</button>
      </div>
      ${R(body)}
    </div>`;
    /* 纵横滚动位成对自保(表格定宽 grid 窄窗口下必有横向滚动, 整帧重建只还 scrollTop 会把
     * 用户的横向滚动位打回最左) —— 单点 helper */
    H.withScroll(host, () => {
      host.replaceChildren(document.createRange().createContextualFragment(html));
    });
  }

  function onClick(ev) {
    const h = ev.currentTarget;
    const toggle = ev.target.closest("[data-toggle]");
    if (toggle) {
      ui.onlyMoving = !ui.onlyMoving;
      rerender(h);
      return;
    }
    const foldHead = ev.target.closest("[data-fold]");
    if (foldHead) {
      const grp = foldHead.closest("[data-grp]");
      if (grp) {
        const key = grp.getAttribute("data-grp");
        ui.folded[key] = !ui.folded[key];
        grp.classList.toggle("folded");
      }
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

  /* P3-4: 纯 div/span 模拟控件的键盘触发(折叠组头 data-fold / 排序表头 data-sort) ——
   * Enter/Space 转发 click 委托; 焦点在原生 button 等自身会发 click 的元素上时不接管
   * (防 Enter 双重触发) */
  function onKeyDown(ev) {
    if (ev.key !== "Enter" && ev.key !== " ") return;
    if (ev.target.closest("button, input, select, textarea, a[href], summary")) return;
    if (!ev.target.closest("[data-fold], [data-sort]")) return;
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
    id: "08", tab: "peers",
    label: "五区分组",
    css: CSS,
    render(host, ctx) {
      wire(host);
      host.__dtCtx = ctx;
      _render(host, ctx);
    },
    destroy,
  });
})();
