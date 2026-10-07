/* auto-qb WEB UI · 详情面板 peers 页签变体 07「四卡仪表 + 流向联动列表」(计划 26-10-06-0838 S4)
 *
 * 设计稿: resources/detail-panel-templates/07-peers-dashboard-tall.html(tall 档; 收起/矮/高三档
 * 语义全部收进本变体 —— 收起 = 核心内置摘要条, 矮/高 = 仪表 + 列表自适应滚动)。
 * 数据: /peers qB sync 透传整包(drawer.peers, 5s 轮询), 四卡聚合全部前端派生自 peers 数组:
 * 实时流量(对端速度求和 + 会话累计 + 上行去向分段)/ 连接构成(五桶)/ 客户端 Top / 链路健康。
 * 上行去向分段与列表行内速度微条同色(--today-up, plan §04 落地要点; 设计稿多色系不在 S1
 * 令牌白名单, 分段用透明度梯度区分)。方向构成五桶色: take=--today-up / feed=--today-down /
 * idle=--border-strong / choke=--warn / hand=--fg-dim。
 * 动作: 纯观察无动作(plan §4 映射行); 筛选 chips 与列头排序为纯前端态。
 * 吸血嫌疑 = client 名含 "XL/迅雷" 启发式, 纯展示(与 09 同判据); 链路健康卡的警戒条不接动作。
 * 渐进字段: country_code/connection/files 随 qB 版本浮动 —— 有则渲染, files 整列省略、
 * cc 徽章逐行省略; flags 缺失行归握手段。
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

  /* 方向五桶(与 08/09 同判据, 纯 flags 派生): U=我方向其上传 D=对端向我供数
   * u=被我方限流 ?/空=握手未完成, 其余(含 K 完整副本)=闲置 */
  const BUCKETS = [
    { key: "take", text: "取流中", color: "--today-up", tip: "我方正在向其上传数据的对端" },
    { key: "feed", text: "供流中", color: "--today-down", tip: "我方正在从其下载数据的对端" },
    { key: "idle", text: "闲置同伴", color: "--border-strong", tip: "完整副本且当前无流量" },
    { key: "choke", text: "被我方限流", color: "--warn", tip: "对方有意下载, 但我方已将其限流" },
    { key: "hand", text: "握手中", color: "--fg-dim", tip: "握手未完成, 身份未明" },
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

  /* 筛选 chips: bad 档仅有嫌疑对端时出现(渐进) */
  const FILTERS = [
    { key: "all", text: "全部" },
    { key: "up", text: "上行中" },
    { key: "down", text: "下行中" },
    { key: "bad", text: "吸血嫌疑" },
    { key: "lan", text: "内网" },
    { key: "hand", text: "握手中" },
  ];

  /* 视图偏好(跨重渲染与换种子保持): 筛选 / 排序 / 微条满刻度; lastSig 供跳过重建 */
  const ui = { filter: "all", sortKey: "up", sortDir: -1, maxUp: 1, maxDown: 1, lastSig: "" };

  const CSS = [
    /* 四卡仪表条 */
    ".drawer .dt07-cards { display:grid; grid-template-columns:repeat(4, minmax(0, 1fr)); gap:10px;",
    "  align-items:stretch; margin-bottom:10px; }",
    ".drawer .dt07-card { min-width:0; background:var(--bg-row); border:1px solid var(--border);",
    "  border-radius:var(--radius); padding:10px 12px; }",
    ".drawer .dt07-label { display:flex; align-items:center; gap:6px; font-size:11px; color:var(--fg-dim);",
    "  margin-bottom:7px; }",
    ".drawer .dt07-label em { font-style:normal; margin-left:auto;",
    "  font-family:var(--font-mono, ui-monospace, monospace); color:var(--fg-dim); }",
    /* 卡 1: 实时流量 */
    ".drawer .dt07-flow { display:flex; flex-direction:column; gap:5px; }",
    ".drawer .dt07-big { display:flex; align-items:baseline; gap:7px;",
    "  font-family:var(--font-mono, ui-monospace, monospace); }",
    ".drawer .dt07-big b { font-size:19px; font-weight:600; }",
    ".drawer .dt07-big.u .ico, .drawer .dt07-big.u b { color:var(--today-up); }",
    ".drawer .dt07-big.d .ico, .drawer .dt07-big.d b { color:var(--today-down); }",
    ".drawer .dt07-big em { font-style:normal; font-size:11px; color:var(--fg-dim);",
    "  font-family:system-ui, sans-serif; }",
    ".drawer .dt07-flowbar { display:flex; height:7px; margin:3px 0 1px; border-radius:999px;",
    "  overflow:hidden; background:var(--bg-sunken); }",
    ".drawer .dt07-flowbar i { display:block; height:100%; background:var(--today-up); }",
    ".drawer .dt07-foot { font-family:var(--font-mono, ui-monospace, monospace); font-size:11px; color:var(--fg-dim); }",
    /* 卡 2: 连接构成 */
    ".drawer .dt07-dirbar { display:flex; height:7px; border-radius:999px; overflow:hidden; background:var(--bg-sunken); }",
    ".drawer .dt07-dirbar i { display:block; height:100%; }",
    ".drawer .dt07-legend { display:grid; grid-template-columns:1fr 1fr; gap:4px 12px; margin-top:8px; }",
    ".drawer .dt07-lg { display:flex; align-items:center; gap:6px; font-size:11.5px; color:var(--fg-muted); white-space:nowrap; }",
    ".drawer .dt07-lg i { width:8px; height:8px; border-radius:2px; flex:none; }",
    ".drawer .dt07-lg b { font-family:var(--font-mono, ui-monospace, monospace); font-weight:600;",
    "  color:var(--fg); margin-left:auto; }",
    /* 卡 3: 客户端 Top */
    ".drawer .dt07-cl { display:flex; align-items:center; gap:8px; font-size:11.5px; color:var(--fg-muted); margin-top:6px; }",
    ".drawer .dt07-cl:first-of-type { margin-top:1px; }",
    ".drawer .dt07-cl .n { flex:none; width:88px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }",
    ".drawer .dt07-cl .track { flex:1; height:5px; border-radius:999px; background:var(--bg-sunken); overflow:hidden; }",
    ".drawer .dt07-cl .track b { display:block; height:100%; border-radius:999px; background:var(--accent); }",
    ".drawer .dt07-cl .ct { flex:none; font-family:var(--font-mono, ui-monospace, monospace); font-weight:600;",
    "  color:var(--fg); width:16px; text-align:right; }",
    /* 卡 4: 链路健康 + 吸血警戒(纯展示) */
    ".drawer .dt07-chips { display:flex; flex-wrap:wrap; gap:6px; }",
    ".drawer .dt07-chip { display:inline-flex; align-items:center; gap:5px; height:22px; padding:0 8px;",
    "  border-radius:999px; background:var(--surface-1); border:1px solid var(--border-soft);",
    "  font-size:11px; color:var(--fg-muted); white-space:nowrap; }",
    ".drawer .dt07-chip b { font-family:var(--font-mono, ui-monospace, monospace); font-weight:600; color:var(--fg); }",
    ".drawer .dt07-chip.c-accent b { color:var(--accent); }",
    ".drawer .dt07-chip.c-blue b { color:var(--blue); }",
    ".drawer .dt07-chip.c-warn b { color:var(--warn); }",
    ".drawer .dt07-chip.c-green b { color:var(--green); }",
    ".drawer .dt07-alert { margin-top:9px; display:flex; align-items:center; gap:7px; padding:6px 9px;",
    "  border-radius:var(--radius-sm); background:var(--error-soft); border:1px solid var(--error-line);",
    "  color:var(--error); font-size:11.5px; text-align:left; }",
    ".drawer .dt07-alert b { font-family:var(--font-mono, ui-monospace, monospace); font-weight:600; }",
    /* 筛选 chips 行 */
    ".drawer .dt07-bar { display:flex; align-items:center; gap:6px; margin-bottom:8px; }",
    ".drawer .dt07-fchip { display:inline-flex; align-items:center; gap:5px; height:24px; padding:0 10px;",
    "  border-radius:999px; border:1px solid var(--border-soft); background:var(--surface-1);",
    "  font-size:11.5px; color:var(--fg-muted); cursor:pointer; user-select:none;",
    "  transition:border-color var(--dur) var(--ease), background var(--dur) var(--ease), color var(--dur) var(--ease); }",
    ".drawer .dt07-fchip b { font-family:var(--font-mono, ui-monospace, monospace); font-weight:600; }",
    ".drawer .dt07-fchip:hover { border-color:var(--border-strong); color:var(--fg); }",
    ".drawer .dt07-fchip.active { background:var(--accent-soft); border-color:var(--accent-line); color:var(--fg); }",
    ".drawer .dt07-fchip.c-err.active { background:var(--error-soft); border-color:var(--error-line); }",
    ".drawer .dt07-note { margin-left:auto; font-size:11.5px; color:var(--fg-dim); }",
    /* 列表(grid 行制) */
    ".drawer .dt07-list { display:flex; flex-direction:column; }",
    ".drawer .dt07-r, .drawer .dt07-head { display:grid;",
    "  grid-template-columns:190px 142px 104px minmax(110px, 1fr) 112px 100px 88px 76px 76px 46px;",
    "  gap:8px; align-items:center; padding:0 8px; }",
    /* files 整列省略时: 9 列, 「正在取」槽位让位给进度列 */
    ".drawer .dt07-r.nofiles, .drawer .dt07-head.nofiles {",
    "  grid-template-columns:190px 142px 104px minmax(150px, 1fr) 112px 100px 88px 76px 76px; }",
    ".drawer .dt07-head { position:sticky; top:0; z-index:1; height:28px; background:var(--bg-card);",
    "  border-bottom:1px solid var(--border); color:var(--fg-dim); font-size:11.5px; white-space:nowrap; }",
    ".drawer .dt07-head .num { text-align:right; }",
    ".drawer .dt07-sortable { cursor:pointer; user-select:none; display:inline-flex; align-items:center; gap:3px;",
    "  justify-content:flex-end; width:100%; }",
    ".drawer .dt07-sortable:hover { color:var(--fg); }",
    ".drawer .dt07-sortable .chev { opacity:0; transition:opacity var(--dur) var(--ease), transform var(--dur) var(--ease); }",
    ".drawer .dt07-sortable.on { color:var(--accent); }",
    ".drawer .dt07-sortable.on .chev { opacity:1; }",
    ".drawer .dt07-sortable.asc .chev { transform:rotate(180deg); }",
    ".drawer .dt07-r { min-height:35px; border-bottom:1px solid var(--hairline); border-radius:var(--radius-sm); }",
    ".drawer .dt07-r:hover { background:var(--bg-hover); }",
    ".drawer .dt07-r.bad { background:var(--error-soft); }",
    ".drawer .dt07-r.bad:hover { box-shadow:inset 0 0 0 1px var(--error-line); }",
    ".drawer .dt07-r.lan { box-shadow:inset 2px 0 0 var(--blue); }",
    ".drawer .dt07-r.hand { opacity:.55; }",
    /* 单元格 */
    ".drawer .dt07-addr { display:flex; align-items:center; gap:7px; min-width:0; }",
    ".drawer .dt07-cc { flex:none; min-width:26px; text-align:center; padding:1px 4px; border-radius:var(--radius-sm);",
    "  background:var(--surface-1); border:1px solid var(--border-soft);",
    "  font-family:var(--font-mono, ui-monospace, monospace); font-size:10px; color:var(--fg-dim); }",
    ".drawer .dt07-cc.lan { color:var(--blue); background:var(--blue-soft); border-color:transparent; }",
    ".drawer .dt07-ip { min-width:0; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;",
    "  font-family:var(--font-mono, ui-monospace, monospace); font-size:12px; color:var(--fg); }",
    ".drawer .dt07-client { display:flex; align-items:center; gap:5px; min-width:0; font-size:12px; color:var(--fg-soft); }",
    ".drawer .dt07-client .cname { min-width:0; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }",
    ".drawer .dt07-badb { flex:none; display:inline-flex; align-items:center; height:15px; padding:0 5px;",
    "  border-radius:999px; background:var(--error-soft); border:1px solid var(--error-line);",
    "  color:var(--error); font-size:10px; }",
    ".drawer .dt07-flags { display:flex; gap:3px; flex-wrap:wrap; }",
    ".drawer .dt07-fl { min-width:16px; height:16px; padding:0 3px; display:inline-flex; align-items:center;",
    "  justify-content:center; border-radius:var(--radius-sm);",
    "  font-family:var(--font-mono, ui-monospace, monospace); font-size:10.5px; font-weight:600; }",
    ".drawer .dt07-fl-d { background:var(--blue-soft); color:var(--blue); }",
    ".drawer .dt07-fl-u { background:var(--green-soft); color:var(--green); }",
    ".drawer .dt07-fl-uo { background:var(--warn-soft); color:var(--warn); }",
    ".drawer .dt07-fl-k { background:transparent; border:1px solid var(--border-strong); color:var(--fg-muted); }",
    ".drawer .dt07-fl-e { background:var(--accent-soft); color:var(--accent); }",
    ".drawer .dt07-fl-p { background:var(--blue-soft); color:var(--blue); }",
    ".drawer .dt07-fl-x { background:var(--hr-pending-soft); color:var(--hr-pending); }",
    ".drawer .dt07-fl-h { background:var(--surface-2); color:var(--fg-dim); }",
    ".drawer .dt07-fl-i { background:var(--surface-2); color:var(--fg-muted); }",
    ".drawer .dt07-fl-q { background:transparent; border:1px dashed var(--border-strong); color:var(--fg-dim); }",
    ".drawer .dt07-files { display:block; min-width:0; overflow:hidden; text-overflow:ellipsis;",
    "  white-space:nowrap; font-size:11.5px; color:var(--fg-muted); }",
    ".drawer .dt07-files.dimc { color:var(--fg-dim); }",
    ".drawer .dt07-prog { display:flex; align-items:center; gap:7px; }",
    ".drawer .dt07-prog .bar { flex:1; position:relative; height:5px; border-radius:999px;",
    "  background:var(--bg-sunken); overflow:hidden; }",
    ".drawer .dt07-prog .bar i { position:absolute; inset:0 auto 0 0; border-radius:999px; background:var(--blue); }",
    ".drawer .dt07-prog em { font-style:normal; font-family:var(--font-mono, ui-monospace, monospace); font-size:11.5px;",
    "  color:var(--fg-muted); width:40px; text-align:right; }",
    ".drawer .dt07-prog.zero em { color:var(--fg-dim); }",
    ".drawer .dt07-none { font-family:var(--font-mono, ui-monospace, monospace); font-size:12px; color:var(--fg-dim); }",
    /* 速度微条: 上行 = --today-up(与卡 1 上行去向分段同色联动) / 下行 = --today-down */
    ".drawer .dt07-spd { display:flex; flex-direction:column; align-items:flex-end; gap:3px; min-width:0; }",
    ".drawer .dt07-spd b { font-family:var(--font-mono, ui-monospace, monospace); font-weight:600; font-size:12px;",
    "  line-height:1; white-space:nowrap; }",
    ".drawer .dt07-spd.u b { color:var(--today-up); }",
    ".drawer .dt07-spd.d b { color:var(--today-down); }",
    ".drawer .dt07-spd b.z { color:var(--fg-dim); font-weight:400; }",
    ".drawer .dt07-spd .track { width:100%; height:3px; border-radius:999px; background:var(--bg-sunken); overflow:hidden; }",
    ".drawer .dt07-spd .track i { display:block; height:100%; border-radius:999px; }",
    ".drawer .dt07-r.bad .dt07-spd.u b { color:var(--error); }",
    ".drawer .dt07-amt { display:block; font-family:var(--font-mono, ui-monospace, monospace); font-size:11.5px;",
    "  color:var(--fg-soft); text-align:right; white-space:nowrap; }",
    ".drawer .dt07-amt.z { color:var(--fg-dim); }",
    ".drawer .dt07-rel { display:block; font-family:var(--font-mono, ui-monospace, monospace); font-size:11.5px;",
    "  color:var(--fg-muted); text-align:right; }",
    ".drawer .dt07-empty { padding:26px 0; text-align:center; color:var(--fg-dim); font-size:12px; }",
  ].join("\n");

  /* ---------------- 派生 ---------------- */
  function peerList(ctx) {
    const p = (ctx.drawer && ctx.drawer.peers) || {};
    return Array.isArray(p.peers) ? p.peers : Object.values(p.peers || {});
  }
  const { num } = H; /* 公共工具: Number(v)||0(核心层单点) */
  function flagTokens(p) {
    return String(p.flags || "").split(/\s+/).filter(Boolean);
  }
  function flagHas(p, f) {
    return flagTokens(p).indexOf(f) >= 0;
  }
  /* 吸血嫌疑启发式(与 09 同判据): client 名含 "XL/迅雷", 纯展示 */
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
  function clientName(p) {
    const c = String(p.client || "").trim();
    return c ? c.split(/\s+/)[0] : "未知";
  }
  function countsOf(list) {
    const n = { take: 0, feed: 0, idle: 0, choke: 0, hand: 0 };
    for (const p of list) n[bucketOf(p)]++;
    return n;
  }
  function countOf(list, key) {
    if (key === "all") return list.length;
    if (key === "up") return list.filter((p) => num(p.upspeed) > 0).length;
    if (key === "down") return list.filter((p) => num(p.dlspeed) > 0).length;
    if (key === "bad") return list.filter(isBad).length;
    if (key === "lan") return list.filter((p) => isLanIp(p.ip)).length;
    if (key === "hand") return list.filter((p) => bucketOf(p) === "hand").length;
    return 0;
  }

  /* ---------------- 卡片 ---------------- */
  function card1Html(ctx, list) {
    const upTotal = list.reduce((s, p) => s + num(p.upspeed), 0);
    const dnTotal = list.reduce((s, p) => s + num(p.dlspeed), 0);
    const upN = countOf(list, "up");
    const dnN = countOf(list, "down");
    const sent = list.reduce((s, p) => s + num(p.uploaded), 0);
    const recv = list.reduce((s, p) => s + num(p.downloaded), 0);
    /* 上行去向分段: 按 client 首词聚合 upspeed, Top 5; 与行内速度微条同色(--today-up) */
    const byClient = {};
    for (const p of list) {
      if (num(p.upspeed) <= 0) continue;
      const k = clientName(p);
      byClient[k] = (byClient[k] || 0) + num(p.upspeed);
    }
    const top = Object.keys(byClient).sort((a, b) => byClient[b] - byClient[a]).slice(0, 5);
    const denom = top.reduce((s, k) => s + byClient[k], 0);
    const segs = top.map((k, i) => {
      const w = denom > 0 ? (byClient[k] / denom * 100).toFixed(1) : "0";
      const op = (1 - i * 0.15).toFixed(2);
      return T`<i style="width:${w}%;opacity:${op}"></i>`;
    }).join("");
    const tip = top.length
      ? "上行去向(按占比): " + top.map((k) => k + " " + (byClient[k] / denom * 100).toFixed(1) + "%").join(" · ")
        + " — 与列表行内速度微条同色(--today-up)"
      : "当前无上行对端";
    return T`<div class="dt07-card">
      <div class="dt07-label"><svg class="ico ico-sm" viewBox="0 0 16 16"><use href="#i-pulse"></use></svg>实时流量</div>
      <div class="dt07-flow">
        <div class="dt07-big u" title="对端 upspeed 求和"><svg class="ico ico-sm" viewBox="0 0 16 16"><use href="#i-upload"></use></svg><b>${ctx.fmtSpeed(upTotal)}</b><em>发给 ${upN} 个对端</em></div>
        <div class="dt07-big d" title="对端 dlspeed 求和"><svg class="ico ico-sm" viewBox="0 0 16 16"><use href="#i-download"></use></svg><b>${ctx.fmtSpeed(dnTotal)}</b><em>收自 ${dnN} 个对端</em></div>
        <div class="dt07-flowbar" title="${tip}">${R(segs)}</div>
        <div class="dt07-foot">会话累计 发 ${ctx.fmtSize(sent)} · 收 ${ctx.fmtSize(recv)}</div>
      </div>
    </div>`;
  }

  function card2Html(list) {
    const n = countsOf(list);
    const total = list.length || 1;
    const segs = BUCKETS.filter((b) => n[b.key] > 0).map((b) =>
      T`<i style="width:${(n[b.key] / total * 100).toFixed(1)}%;background:var(${b.color})"></i>`).join("");
    const legend = BUCKETS.map((b) =>
      T`<span class="dt07-lg" title="${b.tip}"><i style="background:var(${b.color})"></i>${b.text}<b>${n[b.key]}</b></span>`).join("");
    const tip = BUCKETS.map((b) => b.text + " " + n[b.key]).join(" · ") + "(共 " + list.length + " 连接)";
    return T`<div class="dt07-card">
      <div class="dt07-label"><svg class="ico ico-sm" viewBox="0 0 16 16"><use href="#i-link"></use></svg>连接构成<em>${list.length} 连接</em></div>
      <div class="dt07-dirbar" title="${tip}">${R(segs)}</div>
      <div class="dt07-legend">${R(legend)}</div>
    </div>`;
  }

  function card3Html(list) {
    const byClient = {};
    for (const p of list) {
      const k = clientName(p);
      byClient[k] = (byClient[k] || 0) + 1;
    }
    const keys = Object.keys(byClient).sort((a, b) => byClient[b] - byClient[a]);
    const top = keys.slice(0, 3);
    const restN = keys.length > 3 ? keys.slice(3).reduce((s, k) => s + byClient[k], 0) : 0;
    const total = list.length || 1;
    const rows = top.map((k) =>
      T`<div class="dt07-cl" title="${k} × ${byClient[k]}"><span class="n">${k}</span><span class="track"><b style="width:${(byClient[k] / total * 100).toFixed(1)}%"></b></span><b class="ct">${byClient[k]}</b></div>`).join("");
    const rest = restN
      ? T`<div class="dt07-cl" title="其它 ${keys.length - 3} 种客户端 × ${restN}"><span class="n">其它</span><span class="track"><b style="width:${(restN / total * 100).toFixed(1)}%"></b></span><b class="ct">${restN}</b></div>`
      : "";
    return T`<div class="dt07-card">
      <div class="dt07-label"><svg class="ico ico-sm" viewBox="0 0 16 16"><use href="#i-monitor"></use></svg>客户端分布<em>${list.length} 连接</em></div>
      ${R(rows)}${R(rest)}
    </div>`;
  }

  function card4Html(list) {
    const total = list.length;
    const enc = list.filter((p) => flagHas(p, "E")).length;
    const utp = list.filter((p) => flagHas(p, "P")).length;
    const v6 = list.filter((p) => String(p.ip || "").indexOf(":") >= 0).length;
    const lan = list.filter((p) => isLanIp(p.ip)).length;
    const bad = list.filter(isBad);
    const alert = bad.length
      ? T`<div class="dt07-alert" title="吸血嫌疑 = client 名含 XL/迅雷 启发式, 纯展示无动作(计划 P-04 口径)">
          <svg class="ico ico-sm" viewBox="0 0 16 16"><use href="#i-warn"></use></svg>
          吸血嫌疑 <b>${bad.length}</b> · 拿 ${fmtSizeOf(bad.reduce((s, p) => s + num(p.downloaded), 0))}
          回 ${fmtSizeOf(bad.reduce((s, p) => s + num(p.uploaded), 0))}
        </div>`
      : "";
    return T`<div class="dt07-card">
      <div class="dt07-label"><svg class="ico ico-sm" viewBox="0 0 16 16"><use href="#i-lock"></use></svg>链路健康</div>
      <div class="dt07-chips">
        <span class="dt07-chip c-accent" title="加密连接的对端数(E flag) / 总连接">加密 <b>${enc}/${total}</b></span>
        <span class="dt07-chip c-blue" title="走 uTP 传输的对端数(P flag)">uTP <b>${utp}/${total}</b></span>
        <span class="dt07-chip c-warn" title="IPv6 地址的对端数">IPv6 <b>${v6}</b></span>
        <span class="dt07-chip c-green" title="局域网直连对端(私有地址段启发式), 不占公网带宽">内网 <b>${lan}</b></span>
      </div>
      ${R(alert)}
    </div>`;
  }

  /* ---------------- 列表 ---------------- */
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

  let _ctx = null; /* render 期只读引用(纯格式化; 动作链仍走 host.__dtCtx) */
  const fmtSpeedOf = (v) => _ctx.fmtSpeed(v);
  const fmtSizeOf = (v) => _ctx.fmtSize(v);

  function flagsHtml(p) {
    const f = flagTokens(p);
    if (!f.length) return T`<span class="dt07-none" title="flags 缺失">—</span>`;
    return T`${R(f.map((x) => {
      const m = FLAG_META[x];
      return m
        ? T`<span class="dt07-fl ${m.c}" title="${m.t}">${x}</span>`
        : T`<span class="dt07-fl fl-h" title="qB flags: ${x}">${x}</span>`;
    }).join(""))}`;
  }
  function addrHtml(p) {
    const lan = isLanIp(p.ip);
    const cc = lan
      ? T`<span class="dt07-cc lan" title="局域网直连(私有地址段启发式)">内网</span>`
      : (p.country_code
        ? T`<span class="dt07-cc" title="${p.country || p.country_code}">${p.country_code}</span>`
        : "");
    const conn = p.connection ? " · " + p.connection : "";
    return T`<span class="dt07-addr">${R(cc)}<span class="dt07-ip" title="${p.ip || "?"}:${p.port || ""}${conn}">${p.ip || "?"}${p.port ? ":" + p.port : ""}</span></span>`;
  }
  function clientHtml(p) {
    const badge = isBad(p)
      ? T`<span class="dt07-badb" title="吸血嫌疑 = client 名含 XL/迅雷 启发式, 纯展示">吸血</span>`
      : "";
    return T`<span class="dt07-client"><span class="cname" title="${p.client || "未知"}">${p.client || "未知"}</span>${R(badge)}</span>`;
  }
  function progHtml(p) {
    const pct = Math.round((p.progress || 0) * 100);
    return T`<span class="dt07-prog${pct === 0 ? " zero" : ""}" title="对端自身进度 ${pct}%">
      <span class="bar"><i style="width:${pct}%"></i></span><em>${pct}%</em></span>`;
  }
  function spdHtml(p, dir, maxV) {
    const v = num(dir === "u" ? p.upspeed : p.dlspeed);
    const b = v > 0 ? T`<b>${fmtSpeedOf(v)}</b>` : T`<b class="z">0</b>`;
    const bar = v > 0 && maxV > 0
      ? T`<span class="track"><i style="width:${(v / maxV * 100).toFixed(1)}%"></i></span>`
      : "";
    return T`<span class="dt07-spd ${dir}">${R(b)}${R(bar)}</span>`;
  }
  const amtHtml = (v) => (num(v) > 0
    ? T`<span class="dt07-amt" title="会话累计">${fmtSizeOf(v)}</span>`
    : T`<span class="dt07-amt z" title="会话累计 0">0</span>`);
  const relHtml = (p) =>
    T`<span class="dt07-rel" title="relevance: 该对端拥有我缺失数据的比例">${Math.round((p.relevance || 0) * 100)}%</span>`;

  function rowHtml(p, hasFiles) {
    const b = bucketOf(p);
    const cls = ["dt07-r", isBad(p) ? "bad" : "", isLanIp(p.ip) ? "lan" : "", b === "hand" ? "hand" : ""]
      .filter(Boolean).join(" ");
    const files = hasFiles
      ? (p.files
        ? T`<span class="dt07-files" title="对端正在获取的文件(qB files 字段)">${p.files}</span>`
        : T`<span class="dt07-files dimc">—</span>`)
      : "";
    return T`<div class="${cls}" title="${p.ip || "?"}:${p.port || ""} · ${p.client || "未知"}">
      ${R(addrHtml(p))}${R(clientHtml(p))}<span class="dt07-flags">${R(flagsHtml(p))}</span>${R(files)}${R(progHtml(p))}
      ${R(spdHtml(p, "u", ui.maxUp))}${R(spdHtml(p, "d", ui.maxDown))}
      ${R(amtHtml(p.uploaded))}${R(amtHtml(p.downloaded))}${R(relHtml(p))}
    </div>`;
  }

  function headHtml(hasFiles) {
    const seg = (k, text, tip) => {
      const on = ui.sortKey === k;
      /* P3-4(报告 26-10-07-0542): 排序表头纯 span 模拟控件补键盘达 + aria-sort(升/降/无
       * 随当前排序态在渲染函数里输出) */
      const asort = !on ? "none" : (ui.sortDir === 1 ? "ascending" : "descending");
      return T`<span class="num dt07-sortable${on ? " on" : ""}${on && ui.sortDir === 1 ? " asc" : ""}"
        role="button" tabindex="0" aria-sort="${asort}" data-sort="${k}" title="${tip}">${text}<svg class="ico ico-sm chev" viewBox="0 0 16 16"><use href="#i-chevron"></use></svg></span>`;
    };
    return T`<div class="dt07-head${hasFiles ? "" : " nofiles"}">
      <span>对端</span>
      <span>客户端</span>
      <span title="qB peer_info 标志位, 悬停每个字母看逐项解释">Flags</span>
      ${R(hasFiles ? T`<span title="对端正在获取的文件(qB files 字段)">正在取</span>` : "")}
      ${R(seg("prog", "进度", "对端自身进度"))}
      ${R(seg("up", "上行", "我方发给该对端的即时速度(qB upspeed)"))}
      ${R(seg("down", "下行", "我方从该对端收到的即时速度(qB dlspeed)"))}
      ${R(seg("sent", "已发", "本次会话我方已发给该对端的累计(qB uploaded)"))}
      ${R(seg("recv", "已收", "本次会话我方已从该对端收到的累计(qB downloaded)"))}
      ${R(seg("rel", "关联", "relevance: 该对端拥有我缺失数据的比例"))}
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
    ui.maxUp = Math.max.apply(null, [1].concat(list.map((p) => num(p.upspeed))));
    ui.maxDown = Math.max.apply(null, [1].concat(list.map((p) => num(p.dlspeed))));
    if (loading && !list.length) {
      host.replaceChildren(document.createRange().createContextualFragment(
        T`<div class="dt07-empty"><svg class="ico" viewBox="0 0 16 16"><use href="#i-hourglass"></use></svg><span>正在加载…</span></div>`));
      return;
    }
    /* 错误态先于空态(P3-5): 失败且无数据不是"真的没有", 重试口径真实(本页签 5s 轮询会自动重拉) */
    if (err && !list.length) {
      host.replaceChildren(document.createRange().createContextualFragment(
        T`<div class="dt07-empty"><svg class="ico" viewBox="0 0 16 16"><use href="#i-warn"></use></svg><span title="${err}">用户列表加载失败, 将在下次自动刷新时重试</span></div>`));
      return;
    }
    if (!list.length) {
      host.replaceChildren(document.createRange().createContextualFragment(
        T`<div class="dt07-empty"><span>暂无已连接用户</span></div>`));
      return;
    }
    const hasFiles = list.some((p) => p.files);
    const chips = FILTERS.filter((f) => f.key !== "bad" || countOf(list, "bad") > 0).map((f) =>
      T`<button type="button" class="dt07-fchip${ui.filter === f.key ? " active" : ""}${f.key === "bad" ? " c-err" : ""}" data-f="${f.key}">${f.text} <b>${countOf(list, f.key)}</b></button>`).join("");
    const rows = sorted(filtered(list)).map((p) => rowHtml(p, hasFiles)).join("");
    const html = T`<div class="dt07-wrap">
      <div class="dt07-cards">${R(card1Html(ctx, list))}${R(card2Html(list))}${R(card3Html(list))}${R(card4Html(list))}</div>
      <div class="dt07-bar">${R(chips)}<span class="dt07-note">5s 自动刷新 · 列头点击排序, 默认按「上行」降序</span></div>
      <div class="dt07-list">${R(headHtml(hasFiles))}${R(rows)}</div>
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
    id: "07", tab: "peers",
    label: "四卡仪表",
    css: CSS,
    render(host, ctx) {
      wire(host);
      host.__dtCtx = ctx;
      _render(host, ctx);
    },
    destroy,
  });
})();
