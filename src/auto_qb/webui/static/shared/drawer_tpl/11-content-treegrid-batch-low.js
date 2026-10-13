/* auto-qb WEB UI · 详情面板 content 页签变体 11「增强树表 + 批量优先级(矮)」(计划 26-10-06-0838 S5)
 *
 * 设计稿: resources/detail-panel-templates/11-content-treegrid-batch-low.html(low 档;
 * 矮/高 = 单表承层级自适应滚动。收起档(摘要条)已随面板折叠状态整体移除(2026-10-09)。
 * 数据: 结构单一来源 ctx.drawerFileRows()(树扁平化, 目录行 + 文件行, 文件行带 index),
 * 数值/渐进字段从 ctx.drawer.files[index] 取 —— 目录行聚合(子树大小 / 加权进度 / 文件数 /
 * 最低可用性 / 缺口)前端按路径前缀派生, 零后端改动。
 * 动作(plan §04 映射行): 勾选批量优先级 → setFilePriority(p, indices)(S5 批量通道, indices
 * 从 drawerFileRows() 树收集: 勾目录 = 整棵子树三态框, 一次 POST files/priority); 单文件徽章
 * 点击循环 不下载→正常→高→最高(逐次真实提交, 回执/toast 由既有链自带)。
 * 渐进字段: 每文件 availability 有则整列渲染, 无则整列省略不占位(U4: 引擎 omitEmpty
 * 通用机制接管, 原 hasav/noav 双 grid 手搓退役)。
 * 渲染纪律: dtHtml 全量转义(dtRaw 只用于拼接本变体 dtHtml 产出的预转义片段), replaceChildren
 * 原子换帧, 数据未变(整份 files 序列化比对)跳过重建, 折叠/筛选/勾选集自保(按 path 记账;
 * 换种子只重置勾选集与筛选, 折叠记账跨种子保持 —— P3-6, 报告 26-10-07-0542; 勾选集必须重置:
 * 上一种子的勾选落到新种子文件上是真实的优先级误操作面); 批量条/汇总条 sticky 吸底不随行滚动。
 * 行级键盘: 树行 roving tabindex + 方向键移焦 + Enter/Space 勾选(issue 26-10-07-0846;
 * 锚点/记账/回焦/移焦走核心 helpers 单点, 整行不加 role=button —— 行内已含原生控件)。
 * 桥声明(U4, 计划 26-10-12-0527, D4=A): 表格体走引擎 —— tableId 对应 app.js
 * DRAWER_TABLE_DEFS.drawerContentV11, 外壳只留版式(工具条/批量条), 7 列引擎行容器 +
 * 引擎表头(sticky 吸顶个性反压制), 拖宽/右键隐藏/偏好持久化首次落地(勾选/折叠列 locked
 * —— 隐藏即废功能)。树聚合/筛选/折叠/勾选判据全在 rowsFn(判据零复制), 行来源读反应式
 * UI 态(checked/folded/filter, W5 起 Vue.reactive)。排序不适用(树序 = 树语义, 原口径无排序,
 * 全列 sortable:false + dyn 空键)。行内勾选框三态经分片 :indeterminate 声明式。
 * 自包含: 删除本文件 + 三份 index.html 各去 1 行 manifest 即整体退役, 其它零接触。
 */
(function () {
  "use strict";
  const reg = window.AQB_DRAWER_TPL_REG;
  if (!reg) return; /* 核心未载入(清单序错): 静默退出, 守阵会抓 */
  const T = reg.dtHtml;
  const R = reg.dtRaw;
  const H = reg.helpers; /* 公共骨架单点(报告 26-10-07-0845): 工具/sig 比对/事件挂摘/锚保活 */
  const TABLE_ID = "drawerContentV11";

  const { num } = H; /* 公共工具: Number(v)||0(核心层单点) */
  const PRIO_LABEL = { 0: "不下载", 1: "正常", 4: "高", 6: "高", 7: "最高" };
  const PRIO_CYCLE = [0, 1, 6, 7]; /* 徽章点击循环序(qB 4 档; 旧值 4 = 高, 归入 6 位) */

  /* 视图偏好(跨重渲染与换变体保持): 筛选 / 折叠目录集 / 勾选集(文件 path); lastSig 供跳过重建;
   * focusKey 供真换代(数据帧)后的 rowAfterFn 回焦 —— W5 起交互态不再换代, 平时无人写它。
   * W5(计划 26-10-13-0811 L5): 勾选/折叠/筛选是桥行来源 rowsFn 的读数, 必须**进反应式驱动
   * 数据**(Vue.reactive)—— 点选后桥 keyed 写补丁原行更新, 不再 anchTouch 强制换代整表重挂
   * (旧结构 = 每次点选行 DOM 全换 → 勾选跳动 + 大树点选卡死, 用户 2026-10-13 症状 7/8)。 */
  const ui = Vue.reactive({ filter: "all", folded: new Set(), checked: new Set(), lastSig: "", lastHash: "", focusKey: "" });

  const CSS = [
    /* 骨架: 工具条 / 行区(引擎行容器, .drawer-body 本体滚动)/ 吸底条 */
    ".drawer .dt11-tools { display:flex; align-items:center; gap:6px; margin-bottom:8px; flex-wrap:wrap; }",
    ".drawer .dt11-chip { display:inline-flex; align-items:center; gap:5px; height:24px; padding:0 10px;",
    "  border-radius:999px; border:1px solid var(--border-soft); background:var(--surface-1);",
    "  font:12px/1 system-ui, sans-serif; color:var(--fg-muted); cursor:pointer; user-select:none;",
    "  transition:border-color var(--dur) var(--ease), background var(--dur) var(--ease), color var(--dur) var(--ease); }",
    ".drawer .dt11-chip b { font-family:var(--font-mono, ui-monospace, monospace); font-weight:600; }",
    ".drawer .dt11-chip:hover { border-color:var(--border-strong); color:var(--fg); }",
    ".drawer .dt11-chip.active { background:var(--accent-soft); border-color:var(--accent-line); color:var(--fg); }",
    ".drawer .dt11-chip.c-warn.active { background:var(--warn-soft); border-color:var(--warn-line); }",
    ".drawer .dt11-ghost { display:inline-flex; align-items:center; gap:4px; height:24px; padding:0 9px;",
    "  border-radius:var(--radius-sm); border:1px solid transparent; background:none;",
    "  font:12px/1 system-ui, sans-serif; color:var(--fg-dim); cursor:pointer; }",
    ".drawer .dt11-ghost:hover { color:var(--fg); border-color:var(--border-soft); }",
    ".drawer .dt11-hint { margin-left:auto; font-size:11px; color:var(--fg-dim); }",
    /* 引擎表头 + 行(U4): 列宽/网格/拖宽/右键隐藏归引擎声明, 本变体只保留表头/行观感个性。
     * 吸顶补偿: .drawer-body(滚动容器)的 padding 会内缩 sticky 视矩形 —— top:0 实际停在
     * padding-top 之下, 中途滚动时行文字从那条 14px 缝里漏出来(实测 headTop 比 body 顶缘
     * 恒低 14px); -14px 抵消后表头贴到可见上缘。14px = 三皮肤 .drawer-body 的 padding-top
     * (atlas|console: 14px 18px 20px / prism: 14px 16px 20px), 与下方 .dt11-foot 的
     * margin:-16/-20 同一假设(改皮肤 padding 必须连这里一起核)。 */
    ".drawer .dt11-list { --tbl-pad-x:4px; --tbl-gap:8px; }",
    ".drawer .dt11-list .group-head { position:sticky; top:-14px; z-index:1; min-height:28px; height:28px;",
    "  background:var(--bg-card); border-bottom:1px solid var(--border); color:var(--fg-dim);",
    "  font-size:11.5px; white-space:nowrap; }",
    ".drawer .dt11-list .group-head .hc-size, .drawer .dt11-list .group-head .hc-av { text-align:right; }",
    ".drawer .dt11-list .group-row { min-height:27px; padding:0 var(--tbl-pad-x, 4px); gap:var(--tbl-gap, 8px); align-items:center;",
    "  background:transparent; border:0; border-radius:0; box-shadow:none;",
    "  border-bottom:1px solid var(--hairline); font-size:12px; }",
    ".drawer .dt11-list .group-row:hover { background:var(--bg-hover); transform:none; border-color:transparent; }",
    ".drawer .dt11-list .group-row:focus-visible { outline:2px solid var(--ring); outline-offset:-2px; }",
    ".drawer .dt11-list .group-row.is-chk { background:var(--sel-bg); box-shadow:inset 2px 0 0 var(--accent-line); }",
    ".drawer .dt11-list .group-row.is-chk:hover { background:var(--sel-bg); }",
    ".drawer .dt11-list .group-row.empty-row { display:block; border:0; background:transparent; }",
    /* 行内格(呈现归渲染器 tpl-aq-dt11-cells) */
    ".drawer .dt11-tgl { display:inline-flex; align-items:center; justify-content:center; width:18px; height:18px;",
    "  padding:0; background:none; border:0; color:var(--fg-dim); cursor:pointer; }",
    ".drawer .dt11-tgl:hover { color:var(--fg); }",
    ".drawer .dt11-tgl .ico { width:11px; height:11px; transition:transform var(--dur) var(--ease); }",
    ".drawer .dt11-tgl.closed .ico { transform:rotate(-90deg); }",
    ".drawer .dt11-ck { width:13px; height:13px; margin:0; accent-color:var(--accent); cursor:pointer; }",
    ".drawer .dt11-n { display:flex; align-items:center; gap:6px; min-width:0; }",
    ".drawer .dt11-nm { overflow:hidden; text-overflow:ellipsis; white-space:nowrap; color:var(--fg); }",
    ".drawer .dt11-list .group-row.dir .dt11-nm { font-weight:600; color:var(--fg-soft); }",
    ".drawer .dt11-n .ico { width:13px; height:13px; flex:none; color:var(--fg-dim); }",
    ".drawer .dt11-list .group-row.dir .dt11-n .ico { color:var(--accent); }",
    ".drawer .dt11-meta { flex:none; font-size:10.5px; color:var(--fg-dim); border:1px solid var(--border-soft);",
    "  border-radius:999px; padding:0 6px; line-height:15px; white-space:nowrap; }",
    ".drawer .dt11-meta.is-miss { color:var(--warn); border-color:var(--warn-line); }",
    ".drawer .dt11-sz { font-family:var(--font-mono, ui-monospace, monospace); font-size:11.5px;",
    "  color:var(--fg-soft); text-align:right; white-space:nowrap; }",
    ".drawer .dt11-prog { display:flex; align-items:center; gap:7px; min-width:0; }",
    ".drawer .dt11-prog .bar { flex:1; position:relative; height:5px; border-radius:999px;",
    "  background:var(--bg-sunken); overflow:hidden; }",
    ".drawer .dt11-prog .bar i { position:absolute; inset:0 auto 0 0; border-radius:999px; background:var(--green); }",
    ".drawer .dt11-prog.part .bar i { background:var(--warn); }",
    ".drawer .dt11-prog em { font-style:normal; font-family:var(--font-mono, ui-monospace, monospace); font-size:11px;",
    "  color:var(--fg-muted); width:42px; text-align:right; flex:none; }",
    ".drawer .dt11-av { font-family:var(--font-mono, ui-monospace, monospace); font-size:11.5px; color:var(--fg-soft);",
    "  text-align:right; white-space:nowrap; }",
    ".drawer .dt11-av.low { color:var(--warn); }",
    ".drawer .dt11-pbadge { display:inline-flex; align-items:center; justify-content:center; height:17px; padding:0 7px;",
    "  border-radius:999px; font-size:10.5px; white-space:nowrap; border:1px solid transparent;",
    "  background:var(--surface-2); color:var(--fg-muted); cursor:pointer;",
    "  transition:border-color var(--dur) var(--ease), color var(--dur) var(--ease); }",
    ".drawer .dt11-pbadge:hover { border-color:var(--border-strong); color:var(--fg); }",
    ".drawer .dt11-pbadge.skip { background:transparent; border-style:dashed; border-color:var(--border-strong); color:var(--fg-dim); }",
    ".drawer .dt11-pbadge.high { background:var(--warn-soft); border-color:var(--warn-line); color:var(--warn); }",
    ".drawer .dt11-pbadge.max { background:var(--error-soft); border-color:var(--error-line); color:var(--error); }",
    ".drawer .dt11-pnone { font-family:var(--font-mono, ui-monospace, monospace); font-size:11px; color:var(--fg-dim); }",
    ".drawer .dt11-empty { display:block; padding:24px 0; text-align:center; color:var(--fg-dim); font-size:12px; }",
    /* 吸底条: 勾选 = 批量条, 未勾 = 汇总条(盖过 .drawer-body 的 padding) */
    /* 吸底补偿: 同吸顶, bottom:0 实际停在 padding-bottom 之上, 底缘漏出 20px 行文字
     * (实测 footBottom 比 body 底缘恒高 20px); -20px 抵消后统计条贴到可见下缘,
     * 与自身 margin-bottom:-20px 的盖缝设计同一口径。 */
    ".drawer .dt11-foot { position:sticky; bottom:-20px; z-index:2; display:flex; align-items:center; gap:8px;",
    "  margin:8px -16px -20px; padding:7px 16px 9px; background:var(--bg-card); border-top:1px solid var(--border);",
    "  font-size:11.5px; color:var(--fg-muted); flex-wrap:wrap; }",
    ".drawer .dt11-foot b { font-family:var(--font-mono, ui-monospace, monospace); font-weight:600; color:var(--fg); }",
    ".drawer .dt11-foot b.w { color:var(--warn); }",
    ".drawer .dt11-foot .sp { flex:1; }",
    ".drawer .dt11-bp { display:inline-flex; align-items:center; height:24px; padding:0 10px; border-radius:var(--radius-sm);",
    "  border:1px solid var(--border); background:var(--surface-1); color:var(--fg-muted);",
    "  font:11.5px/1 system-ui, sans-serif; cursor:pointer;",
    "  transition:border-color var(--dur) var(--ease), background var(--dur) var(--ease), color var(--dur) var(--ease); }",
    ".drawer .dt11-bp:hover { border-color:var(--border-strong); color:var(--fg); }",
    ".drawer .dt11-bp.skip { border-style:dashed; }",
    ".drawer .dt11-bp.high { background:var(--warn-soft); border-color:var(--warn-line); color:var(--warn); }",
    ".drawer .dt11-bp.max { background:var(--error-soft); border-color:var(--error-line); color:var(--error); }",
    ".drawer .dt11-clear { height:24px; padding:0 9px; border-radius:var(--radius-sm); border:1px solid transparent;",
    "  background:none; color:var(--fg-dim); font:11.5px/1 system-ui, sans-serif; cursor:pointer; }",
    ".drawer .dt11-clear:hover { color:var(--fg); border-color:var(--border-soft); }",
    ".drawer .dt11-load { padding:26px 0; text-align:center; color:var(--fg-dim); font-size:12px; }",
  ].join("\n");

  /* ---------------- 派生: 行模型 + 目录聚合(路径前缀单遍扫描; 判据单点, U4 保留) ---------------- */
  function fileList(ctx) {
    return (ctx.drawer && ctx.drawer.files) || [];
  }
  /* rows = drawerFileRows() 扁平树; 目录聚合按 path 前缀归到各祖先目录(单遍, 不做 O(D*F)) */
  function derive(ctx) {
    const rows = ctx.drawerFileRows();
    const files = fileList(ctx);
    const hasAv = files.some((f) => f && f.availability !== undefined && f.availability !== null);
    const stats = new Map(); /* 目录 path -> 聚合 */
    const statOf = (dp) => {
      let s = stats.get(dp);
      if (!s) {
        s = { size: 0, done: 0, files: 0, missCnt: 0, miss: 0, skipCnt: 0, minAv: Infinity, hasAv: false };
        stats.set(dp, s);
      }
      return s;
    };
    const fileRows = [];
    const itemByPath = new Map(); /* 文件 path -> 行模型(渲染/动作 O(1) 取用, 不做 O(F^2) find) */
    let total = { size: 0, done: 0, missCnt: 0, skipCnt: 0, skipSize: 0 };
    for (const r of rows) {
      if (r.dir) continue;
      const raw = files[r.index] || {};
      const size = num(raw.size);
      const prog = num(raw.progress); /* 0-1, 与 drawerFileRows 的 r.progress(%) 同源 */
      const prio = num(raw.priority);
      const av = raw.availability;
      const fin = { row: r, size, prog, prio, av };
      fileRows.push(fin);
      itemByPath.set(r.path, fin);
      total.size += size;
      total.done += size * prog;
      if (prog < 1) total.missCnt++;
      if (prio === 0) { total.skipCnt++; total.skipSize += size; }
      const segs = r.path.split("/");
      for (let i = 1; i < segs.length; i++) {
        const s = statOf(segs.slice(0, i).join("/"));
        s.size += size; s.done += size * prog; s.files++;
        if (prog < 1) { s.missCnt++; s.miss += size * (1 - prog); }
        if (prio === 0) s.skipCnt++;
        if (av !== undefined && av !== null) {
          s.hasAv = true;
          if (num(av) < s.minAv) s.minAv = num(av);
        }
      }
    }
    return { rows, fileRows, itemByPath, stats, hasAv, total };
  }
  function statProg(s) {
    return s.size > 0 ? s.done / s.size * 100 : 100;
  }
  function dirMatch(dirPath, filter, stats) {
    const s = stats.get(dirPath);
    if (!s) return false;
    if (filter === "miss") return s.missCnt > 0;
    if (filter === "skip") return s.skipCnt > 0;
    return true;
  }

  /* render 期只读引用(纯格式化), 与 07 同口径 */
  let _ctx = null;
  const ctxOf = () => _ctx;

  function prioBadgeClass(p) {
    if (p === 0) return " skip";
    if (p === 7) return " max";
    if (p === 4 || p === 6) return " high";
    return "";
  }

  /* ---------------- 行装配(U4: 判据在这里, 呈现在渲染器分片) ----------------
   * 行对象 = 显示值 + 修饰字段 + _cls 行态(dir/file + is-chk); 行身份 k = path(引擎行容器
   * data-dt-key 消费)。勾选三态(ckState 0/1/2)在装配时算好, 分片 :checked/:indeterminate
   * 声明式直持(原生 property)。可用性: av 字段(有 availability 才非空串)供 omitEmpty
   * 整列判据, avTxt 供显示(目录 "—"/文件真值或 "—")。 */
  function dirRowOf(ctx, r, d) {
    const s = d.stats.get(r.path);
    const prog = statProg(s || { size: 0, done: 0 });
    const paths = subtreeFiles(r.path, d.fileRows).map((it) => it.row.path);
    return {
      k: r.path,
      kind: "row",
      path: r.path,
      dir: true,
      name: r.name,
      indent: Math.max(0, r.depth) * 14,
      folded: ui.folded.has(r.path),
      meta: (s ? s.files : 0) + " 文件",
      metaTitle: "",
      missTxt: "",
      sizeTxt: ctx.fmtSize(s ? s.size : 0),
      progTxt: prog.toFixed(1),
      progW: Math.min(100, Math.max(0, prog)).toFixed(1),
      part: prog < 100,
      progTitle: "子树加权平均进度 " + prog.toFixed(1) + "%",
      ckState: chkStateOf(paths),
      subFiles: s ? s.files : 0,
      av: undefined,
      avTxt: s && s.hasAv ? s.minAv.toFixed(2) : "—",
      avLow: false,
      avTitle: s && s.hasAv ? "子树内最低可用性(最稀缺文件)" : "子树内暂无可用性数据",
      badge: "",
      badgeCls: "",
      badgeTitle: "",
      _cls: "dir" + (chkStateOf(paths) === 2 ? " is-chk" : ""),
    };
  }
  function fileRowOf(ctx, item, d) {
    const r = item.row;
    const checked = ui.checked.has(r.path);
    const avNum = item.av !== undefined && item.av !== null;
    const missTxt = item.prog < 1 ? ctx.fmtSize(item.size * (1 - item.prog)) : "";
    return {
      k: r.path,
      kind: "row",
      path: r.path,
      dir: false,
      name: r.name,
      indent: Math.max(0, r.depth) * 14,
      folded: false,
      meta: "",
      metaTitle: "",
      missTxt,
      missTitle: missTxt ? "按进度估算缺口约 " + missTxt : "",
      sizeTxt: ctx.fmtSize(item.size),
      progTxt: (item.prog * 100).toFixed(1),
      progW: Math.min(100, Math.max(0, item.prog * 100)).toFixed(1),
      part: item.prog * 100 < 100,
      progTitle: "文件进度 " + (item.prog * 100).toFixed(1) + "%",
      ckState: checked ? 2 : 0,
      subFiles: 0,
      av: avNum ? num(item.av).toFixed(2) : undefined,
      avTxt: avNum ? num(item.av).toFixed(2) : "—",
      avLow: avNum && num(item.av) < 1,
      avTitle: avNum ? "qB availability: 全 swarm 中该文件数据的份数" : "qB 未返回该文件可用性",
      badge: PRIO_LABEL[item.prio] || "正常",
      badgeCls: prioBadgeClass(item.prio).trim(),
      badgeTitle: "优先级: " + (PRIO_LABEL[item.prio] || "正常") + " — 点击循环 不下载→正常→高→最高",
      _cls: "file" + (checked ? " is-chk" : ""),
    };
  }

  /* 桥行来源(注册条目 rowsFn ← 根方法 dtTplRows): 树扁平遍历(筛选 + 折叠判据)。
   * 排序不适用(树序 = 树语义, dyn 空键 = 原序); 筛选空合成空态行(原文案口径)。 */
  function rowsFn(ctx) {
    const files = fileList(ctx);
    if (!files.length) return [];
    const d = derive(ctx);
    const rows = [];
    function isFolded(path) {
      const segs = path.split("/");
      for (let i = 1; i < segs.length; i++) {
        if (ui.folded.has(segs.slice(0, i).join("/"))) return true;
      }
      return false;
    }
    for (const r of d.rows) {
      const show = r.dir
        ? (ui.filter === "all" ? true : dirMatch(r.path, ui.filter, d.stats))
        : (ui.filter === "all" ? true
          : ui.filter === "miss" ? r.progress < 100
            : (files[r.index] ? num(files[r.index].priority) === 0 : false));
      if (!show) continue;
      /* 筛选态下无视折叠全部铺平(命中行可见); 全部态下被折叠目录的整棵子树不渲染 */
      if (ui.filter === "all" && isFolded(r.path)) continue;
      rows.push(r.dir ? dirRowOf(ctx, r, d) : fileRowOf(ctx, d.itemByPath.get(r.path) || { row: r, size: 0, prog: 0, prio: 1, av: undefined }, d));
    }
    if (!rows.length) rows.push({ k: "__empty", kind: "empty", _cls: "empty-row" });
    return rows;
  }

  /* 勾选集工具(全部按文件 path 记账; 判据单点) */
  function chkStateOf(paths) {
    let n = 0;
    for (const p of paths) if (ui.checked.has(p)) n++;
    return n === 0 ? 0 : n === paths.length ? 2 : 1;
  }
  function subtreeFiles(dirPath, fileRows) {
    const pre = dirPath + "/";
    return fileRows.filter((it) => it.row.path.startsWith(pre));
  }
  function toggleSet(paths) {
    const st = chkStateOf(paths);
    for (const p of paths) {
      if (st === 2) ui.checked.delete(p); else ui.checked.add(p);
    }
  }
  function batchIndices(fileRows) {
    const out = [];
    for (const it of fileRows) if (ui.checked.has(it.row.path)) out.push(it.row.index);
    return out;
  }

  function render(host, ctx) {
    const files = fileList(ctx);
    const loading = ctx.drawer && ctx.drawer.filesLoading;
    const hash = (ctx.drawer && ctx.drawer.hash) || "";
    /* P3-5(报告 26-10-07-0542): fetch 失败标记 —— 失败与「真没有」在变体里不同形态 */
    const err = (ctx.drawer && ctx.drawer.filesError) || "";
    /* 换种子: 勾选集/筛选随目标失效(与 classic drawerSelPath 同口径); 折叠集不清(P3-6, 报告
     * 26-10-07-0542: 折叠态口径统一为跨种子保持, 与 general 组 dt01/02 一致) —— 记账 key 是
     * path, 新种子的 path 空间完全不同, 旧条目自然不命中(= 新种子从默认展开态起但容器不清空);
     * 同名目录则延续上一部的折叠选择。勾选集必须重置: 批量优先级会真提交, 旧勾选落到新种子
     * 文件上是误操作面, 与折叠的纯视图语义不同 */
    if (hash !== ui.lastHash) {
      ui.lastHash = hash;
      ui.checked = new Set();
      ui.filter = "all";
    }
    /* 数据未变跳过重建(优先级改动补拉 / 换页签回来都会触发通知); 锚元素由 anchFill 跨帧
     * 保活(锚被重建 = Teleport 重挂 = 行抖动, 桥变体稳定 HTML 不变量) */
    const sig = JSON.stringify(files) + "|" + String(!!loading) + "|" + err;
    if (H.skipUnchanged(host, ui, sig)) return;
    _ctx = ctx;
    if (loading && !files.length) {
      host.replaceChildren(document.createRange().createContextualFragment(
        T`<div class="dt11-load"><svg class="ico" viewBox="0 0 16 16"><use href="#i-hourglass"></use></svg><span>正在加载…</span></div>`));
      return;
    }
    /* 错误态先于空态(P3-5): 失败且无数据不是"真的没有"; content 页签无轮询, 文案不承诺自动重拉 */
    if (err && !files.length) {
      host.replaceChildren(document.createRange().createContextualFragment(
        T`<div class="dt11-load"><svg class="ico" viewBox="0 0 16 16"><use href="#i-warn"></use></svg><span title="${err}">文件列表加载失败, 数据不可用</span></div>`));
      return;
    }
    if (!files.length) {
      host.replaceChildren(document.createRange().createContextualFragment(
        T`<div class="dt11-load"><span>无文件列表</span></div>`));
      return;
    }
    const d = derive(ctx);
    /* 勾选集按现存文件 path 收敛(数据补拉后失效条目自动出清) */
    const alive = new Set(d.fileRows.map((it) => it.row.path));
    for (const p of Array.from(ui.checked)) if (!alive.has(p)) ui.checked.delete(p);
    const allPaths = d.fileRows.map((it) => it.row.path);
    const cnt = { all: d.fileRows.length, miss: d.total.missCnt, skip: d.total.skipCnt };
    const chips = [
      T`<button type="button" class="dt11-chip${ui.filter === "all" ? " active" : ""}" data-f="all">全部 <b>${cnt.all}</b></button>`,
      T`<button type="button" class="dt11-chip c-warn${ui.filter === "miss" ? " active" : ""}" data-f="miss" title="只显示存在缺口的文件">未完成 <b>${cnt.miss}</b></button>`,
      T`<button type="button" class="dt11-chip${ui.filter === "skip" ? " active" : ""}" data-f="skip" title="只显示优先级为不下载的文件">不下载 <b>${cnt.skip}</b></button>`,
    ].join("");
    const checkedIdx = batchIndices(d.fileRows);
    let checkedSize = 0, checkedMiss = 0;
    for (const it of d.fileRows) {
      if (ui.checked.has(it.row.path)) {
        checkedSize += it.size;
        if (it.prog < 1) checkedMiss += it.size * (1 - it.prog);
      }
    }
    const foot = checkedIdx.length
      ? T`<div class="dt11-foot" title="批量优先级走 files/priority indices 数组, 一次提交">
          <span>已选 <b>${checkedIdx.length}</b> 个文件 · <b>${ctxOf().fmtSize(checkedSize)}</b>${R(checkedMiss > 0 ? T` · <b class="w">缺 ${ctxOf().fmtSize(checkedMiss)}</b>` : "")}</span>
          <span class="sp"></span>
          ${R(PRIO_CYCLE.map((p) => T`<button type="button" class="dt11-bp ${p === 0 ? "skip" : p === 7 ? "max" : p === 6 ? "high" : ""}" data-bp="${p}"
              title="将已选 ${checkedIdx.length} 个文件设为${PRIO_LABEL[p]}">${PRIO_LABEL[p]}</button>`).join(""))}
          <button type="button" class="dt11-clear" data-bclear title="清除全部勾选">清除</button>
        </div>`
      : T`<div class="dt11-foot" title="勾选行(勾目录 = 整棵子树)后此处浮出批量优先级条">
          <span>${cnt.all} 个文件 · 合计 <b>${ctxOf().fmtSize(d.total.size)}</b> · 总进度
            <b>${(d.total.size > 0 ? d.total.done / d.total.size * 100 : 100).toFixed(1)}%</b> ·
            未完成 <b class="w">${cnt.miss}</b> · 跳过 <b>${cnt.skip}</b>(占 ${ctxOf().fmtSize(d.total.skipSize)})</span>
          <span class="sp"></span>
          <span style="color:var(--fg-dim)">勾选后批量设优先级 · 点徽章循环单个</span>
        </div>`;
    /* 表格区 = 空 slot: anchFill 把保活的锚元素替换进 slot 位, 树行由桥 Teleport 进锚 */
    const html = T`<div class="dt11-wrap">
      <div class="dt11-tools">
        <input type="checkbox" class="dt11-ck" data-ckmaster>
        ${R(chips)}
        <button type="button" class="dt11-ghost" data-fold="open">展开</button>
        <button type="button" class="dt11-ghost" data-fold="close">折叠</button>
        <span class="dt11-hint">勾选目录 = 整棵子树 · 批量条吸底</span>
      </div>
      <div class="dt11-list"><div data-dt-anchor-slot=""></div></div>
      ${R(foot)}
    </div>`;
    host.replaceChildren(document.createRange().createContextualFragment(html));
    H.anchFill(host, TABLE_ID);
    /* 主勾选框三态(native indeterminate; 行内勾选框三态已在分片声明式直持) */
    const master = host.querySelector("input[data-ckmaster]");
    if (master) {
      const st = chkStateOf(allPaths);
      master.checked = st === 2;
      master.indeterminate = st === 1;
    }
  }

  /* W5(计划 26-10-13-0811 L5): 旧「UI 态翻动 → anchTouch 强制换代」已退役 —— ui 态已进
   * 反应式驱动数据(Vue.reactive), 行更新走桥 keyed 写补丁(行 DOM 身份恒定, 勾选不跳动);
   * 外壳件(foot/master/chips)仍由 rerender 单点重渲(anchFill 保锚, 不换代)。 */

  /* 锚换代重挂后的行级键盘恢复(issue 26-10-07-0846; 描述符 rowAfter → rowAfterFn):
   * roving 锚点(首行; 勾选集无「选中行」语义) + 回焦。 */
  function rowAfterFn(el) {
    if (!el || typeof el.querySelectorAll !== "function") return;
    H.roving(el, "data-dt-key", "");
    H.rowRestore(el, "data-dt-key", ui.focusKey);
  }

  function onClick(ev) {
    const h = ev.currentTarget;
    const ctx = h.__dtCtx;
    if (ev.target.closest(".dt11-ck")) return; /* 勾选走 change 事件, 点选框本身不按行处理 */
    /* 优先级徽章: 循环切换单文件(逐次真实提交) */
    const badge = ev.target.closest("[data-act=\"prio-cycle\"]");
    if (badge) {
      ev.stopPropagation();
      const d = derive(ctx);
      const it = d.itemByPath.get(badge.getAttribute("data-path"));
      if (!it) return;
      const cur = it.prio === 4 ? 6 : it.prio;
      const next = PRIO_CYCLE[(PRIO_CYCLE.indexOf(cur) + 1) % PRIO_CYCLE.length];
      ctx.setFilePriority(next, [it.row.index]);
      return;
    }
    const tgl = ev.target.closest("[data-act=\"fold\"]");
    if (tgl) {
      const p = tgl.getAttribute("data-path") || "";
      if (ui.folded.has(p)) ui.folded.delete(p); else ui.folded.add(p);
      return;
    }
    const foldBtn = ev.target.closest("[data-fold]");
    if (foldBtn) {
      const d = derive(ctx);
      const dirs = [];
      for (const r of d.rows) if (r.dir && r.path) dirs.push(r.path);
      ui.folded = foldBtn.getAttribute("data-fold") === "close" ? new Set(dirs) : new Set();
      return;
    }
    const chip = ev.target.closest("[data-f]");
    if (chip) {
      ui.filter = chip.getAttribute("data-f") || "all";
      rerender(h); /* chip active 态在外壳 */
      return;
    }
    const bp = ev.target.closest("[data-bp]");
    if (bp) {
      const d = derive(ctx);
      const idx = batchIndices(d.fileRows);
      if (!idx.length) return;
      ctx.setFilePriority(Number(bp.getAttribute("data-bp")), idx);
      return;
    }
    if (ev.target.closest("[data-bclear]")) {
      ui.checked = new Set();
      rerender(h);
      return;
    }
    /* 点行 = 勾选(目录 = 整棵子树; 与设计稿 11 同语义); 行容器 = 引擎 .group-row[data-dt-key] */
    const row = ev.target.closest("[data-dt-key]");
    if (row && row.closest(".dt11-list")) toggleRow(row.getAttribute("data-dt-key"), h);
  }
  function toggleRow(path, h) {
    const ctx = h.__dtCtx;
    const d = derive(ctx);
    const r = d.rows.find((x) => x.path === path);
    if (!r || path === "__empty") return;
    toggleSet(r.dir ? subtreeFiles(r.path, d.fileRows).map((it) => it.row.path) : [r.path]);
    rerender(h); /* foot/master 三态在外壳 */
  }
  /* 行级键盘(issue 26-10-07-0846): roving tabindex + 方向键/Home/End 移焦 + Enter/Space
   * 转发行激活(= 勾选, 与 click 同口径)。焦点在行内原生控件(勾选框/折叠钮/优先级徽章)
   * 上时不接管 —— 只有 ev.target 是行容器自身才处理, 原生控件键盘行为自持。
   * 行身份锚 = 引擎行容器 data-dt-key(U4 桥单点输出)。 */
  function onKeyDown(ev) {
    const row = ev.target.closest("[data-dt-key]");
    if (!row || ev.target !== row || !row.closest(".dt11-list")) return;
    if (ev.key === "Enter" || ev.key === " ") {
      ev.preventDefault();
      toggleRow(row.getAttribute("data-dt-key") || "", ev.currentTarget);
      return;
    }
    if (H.rowMove(ev.currentTarget, "data-dt-key", row, ev.key)) ev.preventDefault();
  }
  function onChange(ev) {
    const h = ev.currentTarget;
    const ctx = h.__dtCtx;
    const dirck = ev.target.closest("[data-act=\"dirck\"]");
    if (dirck) {
      const d = derive(ctx);
      toggleSet(subtreeFiles(dirck.getAttribute("data-path") || "", d.fileRows).map((it) => it.row.path));
      rerender(h);
      return;
    }
    const ck = ev.target.closest("[data-act=\"ck\"]");
    if (ck) {
      const p = ck.getAttribute("data-path") || "";
      if (ui.checked.has(p)) ui.checked.delete(p); else ui.checked.add(p);
      rerender(h);
      return;
    }
    if (ev.target.closest("[data-ckmaster]")) {
      const d = derive(ctx);
      toggleSet(d.fileRows.map((it) => it.row.path));
      rerender(h);
    }
  }

  /* 视图偏好变化后的强制重渲染(sig 不含偏好, 置空 lastSig 即可; 口径同 04/07) */
  function rerender(host) {
    ui.lastSig = "";
    const ctx = host.__dtCtx;
    if (ctx) _render(host, ctx);
  }

  function wire(host) {
    H.wireEvents(host, { click: onClick, change: onChange, keydown: onKeyDown });
  }

  function destroy(host) {
    ui.lastSig = ""; /* 下次挂载强制整帧重建 */
    /* 宿主元素跨变体复用(同页签只有一个 data-dt-host), 换变体必须摘掉本变体的委托监听,
     * 否则新旧变体监听叠加、同一次点击被多个 handler 重复处理 */
    H.unwireEvents(host);
  }

  const _render = render;
  reg.register({
    id: "11", tab: "content",
    label: "树表批量",
    /* 桥声明(U4): 表格体走引擎 —— tableId 对应 app.js DRAWER_TABLE_DEFS.drawerContentV11,
     * rowsFn = 行装配(树聚合/筛选/折叠/勾选判据单点), 表头/拖宽/右键隐藏/偏好归引擎。
     * rowAfterFn = 锚换代重挂后的 roving 锚点/回焦(行级键盘, issue 26-10-07-0846)。 */
    tableId: TABLE_ID,
    rowsFn: rowsFn,
    rowAfterFn: rowAfterFn,
    css: CSS,
    render(host, ctx) {
      wire(host);
      host.__dtCtx = ctx;
      _render(host, ctx);
    },
    destroy,
  });
})();
