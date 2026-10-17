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
 * 渐进字段: country_code/connection/files 随 qB 版本浮动 —— files 列在列定义声明 omitEmpty
 * (无任何对端携带时整列省略, 引擎单点 columns.js _colsOmitEmpty); cc 徽章逐行省略;
 * 关联度列设计稿未纳入(分区语义已隐含, 列定义 sortable:false), 空分区整节隐藏(2026-10-18
 * 起改**原地 hidden 类**切换, 不再整节缺席, 见下段根治注)。
 * !U2 重写(计划 26-10-12-0527, 拍板 D1=锚桥/D2=列个性/D3=排序并引擎/D5=观感保持/D6=键独立):
 *   表格体重写为**引擎消费面**, 分段桥(segs)形态 —— 分组头留在外壳(分组是版式), 每组的
 *   行体是引擎表体: 每组一个锚槽(data-dt-anchor-slot="<组key>"), 桥按段 teleport
 *   aq-table + 行渲染器进各组锚。rowsFn 返回 [{key, rows}] 分段(与外壳同一条分桶判据),
 *   组内排序走引擎 dyn 键且**跨组共享一座键**(与原手搓状态机同口径)。描述符
 *   drawerPeerV08: 列集 DRAWER_PEER_V08_COLUMNS + 行模型 dt08 + rowCls 行修饰。
 *   手搓排序状态机/列宽 grid/每组列头拼装全部退役(Q4)。
 * !2026-10-18(用户报障「五区分组中『握手中』的组消失与出现导致详情模板高度跳动」根治):
 *   病根两层: ①面板高度内容自适应 —— 未拖拽过时 drawerPanelStyle 返回 {} 走 CSS max-height
 *   上限(无确定 height), 组进出场即改面板实高(已在 drawer.js 单点修掉: 展开恒锁高度,
 *   内容超高由 .drawer-body 内部滚动消化); ②本变体结构 sig 含在场分组集 ⇒ 组空⇒整节隐藏
 *   (锚离场)、组补⇒新锚进场, 每翻动一次就整帧 replaceChildren + anchFill + Teleport 重挂
 *   = 全组表格抖动。修法: **五区恒在场** —— 空组不进 sig, 只切 hidden 类(.dt08-hide,
 *   display:none); rowsFn 保留空段 ⇒ 桥 v-for 段集合不变 ⇒ teleport 不卸不重挂, 握手中组
 *   再现时行原地补丁进场; 数据拍(render 的 skip 分支内)原地切隐藏类 + 回填组头计数/聚合数。
 *   「只看在传数据」是用户显式动作, 维持整组离场口径(quiet 组不进 DOM, 单次 rebuild 可接受)。
 * 渲染纪律: dtHtml 全量转义(dtRaw 只用于拼接本变体 dtHtml 产出的预转义片段), replaceChildren
 * 原子换帧, **结构态**(加载/失败/空态/只看在传/折叠)未变跳过重建 —— 数据拍(5s 轮询每拍必到,
 * 组 membership 随握手翻动是常态)不整帧重建(整帧重建 = 56-75ms longtask/拍 = 用户所报
 * "表格闪烁, 数据随闪烁刷新"); 行走桥响应式, 组头计数/聚合数/空组隐藏类走 paintTick 原地
 * 回填(不含锚的子树), 各组锚元素跨帧保活(锚被重建 = Teleport 重挂 = 行抖动), 滚动位置/
 * 折叠/筛选态自保。
 * 自包含: 删除本文件 + 三份 index.html 各去 1 行 manifest 即整体退役, 其它零接触。
 */
(function () {
  "use strict";
  const reg = window.AQB_DRAWER_TPL_REG;
  if (!reg) return; /* 核心未载入(清单序错): 静默退出, 守阵会抓 */
  const T = reg.dtHtml;
  const R = reg.dtRaw;
  const H = reg.helpers; /* 公共骨架单点(报告 26-10-07-0845): 工具/sig 比对/滚动自保/事件挂摘/锚保活 */

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

  /* 视图偏好(跨重渲染与换种子保持): 只看在传数据 / 组折叠(默认 idle/hand 收起);
   * lastSig 供跳过重建。!排序态已并引擎(dtSortState.drawerPeerV08, U2) —— 手搓
   * sortKey/sortDir/组内 maxUp/maxDown 退役(微条满刻度在 rowsFn 现算)。 */
  /* W5(计划 26-10-13-0811 L5): 只看在传/分组折叠进反应式驱动数据 —— 桥 keyed 写补丁原行更新,
   * 不再 anchTouch 强制换代整表重挂(行抖动的旧结构)。 */
  const ui = Vue.reactive({ onlyMoving: false, folded: { idle: true, hand: true }, lastSig: "" });

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
    /* 2026-10-18(用户报障根治): 空组整节隐藏改**原地类切换** —— 五区恒在场(锚/表格体不卸不
     * 重挂), 空组只切 dt08-hide。组 membership 随 5s 轮询翻动(握手动不动进出场)时零整帧重建 */
    ".drawer .dt08-grp.dt08-hide { display:none; }",
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
    /* 引擎行容器的变体个性(D5: 只保留行级观感, 列宽/网格/列头归引擎) */
    ".drawer .dt08-rows .group-row { min-height:33px; border-bottom:1px solid var(--hairline);",
    "  border-radius:var(--radius-sm); }",
    ".drawer .dt08-rows .group-row:hover { background:var(--bg-hover); }",
    ".drawer .dt08-rows .group-row.bad { background:var(--error-soft); }",
    ".drawer .dt08-rows .group-row.bad:hover { box-shadow:inset 0 0 0 1px var(--error-line); }",
    ".drawer .dt08-rows .group-row.lan { box-shadow:inset 2px 0 0 var(--blue); }",
    ".drawer .dt08-rows .group-row.handrow { opacity:.55; }",
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
    /* 速度数值: 上传 = --today-up / 下载 = --today-down(方向色令牌) */
    ".drawer .dt08-spd { display:flex; flex-direction:column; align-items:flex-end; gap:3px; min-width:0; }",
    ".drawer .dt08-spd b { font-family:var(--font-mono, ui-monospace, monospace); font-weight:600; font-size:12px;",
    "  line-height:1; white-space:nowrap; }",
    ".drawer .dt08-spd.u b { color:var(--today-up); }",
    ".drawer .dt08-spd.d b { color:var(--today-down); }",
    ".drawer .dt08-spd b.z { color:var(--fg-dim); font-weight:400; }",
    ".drawer .dt08-amt { display:block; font-family:var(--font-mono, ui-monospace, monospace); font-size:11.5px;",
    "  color:var(--fg-soft); text-align:right; white-space:nowrap; }",
    ".drawer .dt08-amt.z { color:var(--fg-dim); }",
    ".drawer .dt08-rel { display:block; font-family:var(--font-mono, ui-monospace, monospace); font-size:11.5px;",
    "  color:var(--fg-muted); text-align:right; }",
    ".drawer .dt08-empty { padding:26px 0; text-align:center; color:var(--fg-dim); font-size:12px; }",
    /* 「只看在传数据」过滤到空场合的提示: 恒在帧内(不进结构 sig), 由 render 的数据拍回填段切
     * on 类 —— 显隐本身不触发整帧重建(2026-10-18 同口径) */
    ".drawer .dt08-none { display:none; }",
    ".drawer .dt08-none.on { display:block; }",
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

  /* ---------------- 行装配(U2: 数据判据在这里, 呈现在渲染器分片; 分段 = 分桶) ---------------- */
  function rowOf(ctx, p) {
    const f = flagTokens(p);
    const lan = isLanIp(p.ip);
    const up = num(p.upspeed), down = num(p.dlspeed);
    const addr = `${p.ip || "?"}${p.port ? ":" + p.port : ""}`;
    return {
      addr,
      addrTitle: `${p.ip || "?"}:${p.port || ""}${p.connection ? " · " + p.connection : ""}`,
      cc: lan ? "内网" : String(p.country_code || ""),
      ccTitle: lan ? "局域网直连(私有地址段启发式)" : String(p.country || p.country_code || ""),
      lan,
      client: String(p.client || "未知"),
      bad: isBad(p),
      flagToks: f.map((x) => {
        const m = FLAG_META[x];
        return { ch: x, cls: m ? m.c : "fl-h", tip: m ? m.t : "" };
      }),
      files: String(p.files || ""),
      progress: Math.round((p.progress || 0) * 100),
      upspeed: up > 0 ? ctx.fmtSpeed(up) : "0",
      dlspeed: down > 0 ? ctx.fmtSpeed(down) : "0",
      uploaded: num(p.uploaded) > 0 ? ctx.fmtSize(num(p.uploaded)) : "0",
      downloaded: num(p.downloaded) > 0 ? ctx.fmtSize(num(p.downloaded)) : "0",
      relevance: Math.round((p.relevance || 0) * 100) + "%",
      _raw: {
        addr, client: String(p.client || ""), flags: String(p.flags || ""),
        progress: p.progress || 0, dlspeed: down, upspeed: up,
        downloaded: num(p.downloaded), uploaded: num(p.uploaded), relevance: p.relevance || 0,
      },
      _cls: [isBad(p) ? "bad" : "", lan ? "lan" : "", bucketOf(p) === "hand" ? "handrow" : ""]
        .filter(Boolean).join(" ") || null,
    };
  }
  /* 桥行来源(注册条目 rowsFn ← 根方法 dtTplRows): 描述符 segs=true → 返回 [{key, rows}] 分段。
   * 分桶判据与外壳 render 同一条(GROUPS × bucketOf × onlyMoving) —— 桥段与锚槽一一对应。
   * !2026-10-18(用户报障根治): **空段不撤** —— 恒返回只看在传过滤后的全部五区, 空区给 [] 行。
   * 段集合不变 ⇒ 桥 v-for 的 :key 稳定 ⇒ teleport 不卸载不重挂: 握手中组随握手进出场时,
   * 该组行原地补丁进场(v-if seg.rows.length 翻 div), 其余组的行/横滚位/列宽/排序态全不动。
   * 旧口径撤空段, 再现即整表重挂 = 面板内容整块抖动(与面板高度跳动的报障同源)。 */
  function rowsFn(ctx) {
    const list = peerList(ctx);
    const buckets = { take: [], feed: [], idle: [], choke: [], hand: [] };
    for (const p of list) buckets[bucketOf(p)].push(p);
    return GROUPS
      .filter((g) => !(ui.onlyMoving && g.quiet))
      .map((g) => ({ key: g.key, rows: buckets[g.key].map((p) => rowOf(ctx, p)) }));
  }

  /* 组的可见性单点(空组整节隐藏 + 只看在传送 quiet 区进隐藏口径):
   * !2026-10-18 起可见性**不进结构 sig** —— 组空/组补只切 .dt08-hide 类(数据拍原地切),
   * 不整帧重建; 锚元素与表格体全程在场(display:none 不影响 Teleport 目标寻址)。
   * 「只看在传数据」例外: quiet 区由 render 的整组离场口径处理(用户显式动作, 单次 rebuild)。 */
  function groupHidden(g, ms) {
    return !ms.length || (ui.onlyMoving && g.quiet);
  }
  /* 帧内至少一组可见(驱动「该过滤下没有对端连接」提示的 on 类; 整帧与数据拍共用) */
  function anyVisible(buckets) {
    return GROUPS.some((g) => !(ui.onlyMoving && g.quiet) && buckets[g.key].length);
  }

  function groupHtml(g, ms, hidden) {
    const folded = ui.folded[g.key] ? " folded" : "";
    return T`<section class="dt08-grp g-${g.key}${folded}${hidden ? " dt08-hide" : ""}" data-grp="${g.key}">
      <!-- P3-4: 折叠组头纯 div 模拟控件补键盘达(role=button + tabindex + aria-expanded) -->
      <div class="dt08-ghead" role="button" tabindex="0" aria-expanded="${folded ? "false" : "true"}"
           data-fold title="${g.tip} · 点击折叠 / 展开">
        <svg class="ico ico-sm dt08-chev" viewBox="0 0 16 16"><use href="#i-chevron"></use></svg>
        <span class="dt08-dot" style="background:var(${g.color})"></span>
        <span class="dt08-gname">${g.text}</span>
        <span class="dt08-gcnt">${ms.length}</span>
        <span class="dt08-gagg">${R(aggText(g.key, ms))}</span>
      </div>
      <!-- 组体 = 引擎表体(U2 分段桥): 锚槽由 anchFill 换成保活锚, 桥逐段 teleport
           aq-table(列头, 替代原 dt08-gcols 手拼) + 行渲染器进锚 -->
      <div class="dt08-rows"><div data-dt-anchor-slot="${g.key}"></div></div>
    </section>`;
  }

  /* ---------------- 数据拍原地回填(2026-10-18 用户报障根治) ----------------
   * 组头计数/聚合数 + 空组隐藏类 + 过滤空态提示, 全部落在**不含锚**的子树上, 锚元素与表格体
   * 零接触(桥零重挂)。组空⇒该组 section 切 dt08-hide(display:none), 组补⇒摘类原地进场;
   * 5s 轮询每拍必到, 只在真变时写 DOM(classList.toggle 带 force 幂等, 文本先比后写)。
   * 与整帧同一条判据(groupHidden) —— 组 membership 翻动(握手动不动进出场)零整帧重建。 */
  function render(host, ctx) {
    const list = peerList(ctx);
    const loading = ctx.drawer && ctx.drawer.peersLoading;
    /* P3-5(报告 26-10-07-0542): fetch 失败标记 —— 失败与「真没有」在变体里不同形态 */
    const err = (ctx.drawer && ctx.drawer.peersError) || "";
    /* 五区分桶(空分区不缺席, 由 hidden 类隐藏; 判据与 rowsFn / 数据拍回填同一条) */
    const buckets = { take: [], feed: [], idle: [], choke: [], hand: [] };
    for (const p of list) buckets[bucketOf(p)].push(p);
    /* 结构 sig(2026-10-18 用户报障根治收口): 只含**帧形态**决定项 —— 加载/失败/空态/只看在传/
     * 折叠态; **不再含在场分组集**。旧口径组空⇒整节隐藏(锚离场)、组补⇒新锚进场都算结构变化
     * ⇒ 握手连接翻动一次就整帧 replaceChildren + anchFill + Teleport 重挂(全组表格抖动);
     * 现五区恒在场, 组的进出场走 paintTick 原地切类, 不触发任何重建。
     * **不含 peers 数据**: 数据拍(5s 轮询每拍必到)不整帧重建, 行走桥响应式。 */
    const sig = String(!!loading) + "|" + err + "|" + (list.length ? "y" : "n")
      + "|" + String(!!ui.onlyMoving) + "|" + Object.keys(ui.folded).filter((k) => ui.folded[k]).join(",");
    if (H.skipUnchanged(host, ui, sig)) {
      /* 数据拍: 各组头的计数/聚合数 + 空组隐藏类 + 过滤空态提示原地回填 —— 锚全程不动。
       * quiet 区在「只看在传数据」下整组离场(无 section), 原地查询天然跳过。 */
      if (list.length && !loading && !err) {
        let vis = false;
        for (const g of GROUPS) {
          const sec = host.querySelector('.dt08-grp[data-grp="' + g.key + '"]');
          if (!sec) continue;
          const ms = buckets[g.key];
          if (!groupHidden(g, ms)) vis = true;
          sec.classList.toggle("dt08-hide", groupHidden(g, ms));
          const cnt = sec.querySelector(".dt08-gcnt");
          const agg = sec.querySelector(".dt08-gagg");
          if (cnt && cnt.textContent !== String(ms.length)) cnt.textContent = String(ms.length);
          if (agg) { const a = aggText(g.key, ms); if (agg.innerHTML !== a) agg.innerHTML = a; }
        }
        const none = host.querySelector(".dt08-none");
        if (none) none.classList.toggle("on", !vis);
      }
      return;
    }
    _ctx = ctx;
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
    /* 五区恒在场(quiet 区在「只看在传数据」下整组离场, 其余区空组以 dt08-hide 隐藏)——
     * 组头计数/聚合数在数据拍由 paintTick 原地回填, 隐藏类随组 membership 翻动原地切换 */
    const body = GROUPS
      .filter((g) => !(ui.onlyMoving && g.quiet))
      .map((g) => groupHtml(g, buckets[g.key], groupHidden(g, buckets[g.key])))
      .join("");
    const noneOn = anyVisible(buckets) ? "" : " on";
    const html = T`<div class="dt08-wrap">
      <div class="dt08-bar">
        <span class="dt08-note">按「这条连接此刻在干什么」分五区 · 点击组头折叠 / 展开 · 组头聚合数随 5s 轮询刷新</span>
        <span class="dt08-spacer"></span>
        <button type="button" class="dt08-toggle${ui.onlyMoving ? " active" : ""}" data-toggle
          title="收起「闲置同伴 / 握手中」等无流量分区, 只看正在传输数据的连接"><i></i>只看在传数据</button>
      </div>
      ${R(body)}
      <div class="dt08-empty dt08-none${noneOn}"><span>该过滤下没有对端连接</span></div>
    </div>`;
    /* 纵横滚动位成对自保(表格定宽 grid 窄窗口下必有横向滚动, 整帧重建只还 scrollTop 会把
     * 用户的横向滚动位打回最左) —— 单点 helper */
    H.withScroll(host, () => {
      host.replaceChildren(document.createRange().createContextualFragment(html));
      H.anchFill(host, "drawerPeerV08");
    });
  }

  function onClick(ev) {
    const h = ev.currentTarget;
    const toggle = ev.target.closest("[data-toggle]");
    if (toggle) {
      ui.onlyMoving = !ui.onlyMoving;
      rerender(h);
      /* W5: 过滤态已反应式, 桥行更新自动(keyed 写补丁); 外壳区头折叠态由 rerender 同步 */
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
    }
  }

  /* 视图偏好变化后的强制重渲染(sig 不含偏好, 置空 lastSig 即可; 口径同 04) */
  function rerender(host) {
    ui.lastSig = "";
    const ctx = host.__dtCtx;
    if (ctx) _render(host, ctx);
  }

  /* P3-4: 折叠组头纯 div 模拟控件(data-fold)的键盘触发 —— Enter/Space 转发 click 委托;
   * 焦点在原生 button 等自身会发 click 的元素上时不接管(防 Enter 双重触发)。
   * !排序表头的键盘达(U2 起归引擎表壳原生 click 面) —— 手搓排序表头随手搓表头退役。 */
  function onKeyDown(ev) {
    if (ev.key !== "Enter" && ev.key !== " ") return;
    if (ev.target.closest("button, input, select, textarea, a[href], summary")) return;
    if (!ev.target.closest("[data-fold]")) return;
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
    /* 桥声明(U2, 分段形态): tableId 对应 DRAWER_TABLE_DEFS.drawerPeerV08(描述符 segs:true),
     * rowsFn 返回 [{key, rows}] 与锚槽一一对应; 组头聚合/折叠留在外壳。 */
    tableId: "drawerPeerV08",
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
