/* auto-qb WEB UI · 详情面板 content 页签变体 11「增强树表 + 批量优先级(矮)」(计划 26-10-06-0838 S5)
 *
 * 设计稿: resources/detail-panel-templates/11-content-treegrid-batch-low.html(low 档; 收起/矮/高
 * 三档语义全部收进本变体 —— 收起 = 摘要条, 矮/高 = 单表承层级自适应滚动)。
 * 数据: 结构单一来源 ctx.drawerFileRows()(树扁平化, 目录行 + 文件行, 文件行带 index),
 * 数值/渐进字段从 ctx.drawer.files[index] 取 —— 目录行聚合(子树大小 / 加权进度 / 文件数 /
 * 最低可用性 / 缺口)前端按路径前缀派生, 零后端改动。
 * 动作(plan §04 映射行): 勾选批量优先级 → setFilePriority(p, indices)(S5 批量通道, indices
 * 从 drawerFileRows() 树收集: 勾目录 = 整棵子树三态框, 一次 POST files/priority); 单文件徽章
 * 点击循环 跳过→普通→高→最高(逐次真实提交, 回执/toast 由既有链自带)。
 * 渐进字段: 每文件 availability 有则整列渲染, 无则整列省略不占位。
 * 渲染纪律: dtHtml 全量转义(dtRaw 只用于拼接本变体 dtHtml 产出的预转义片段), replaceChildren
 * 原子换帧, 数据未变(整份 files 序列化比对)跳过重建, 折叠/筛选/勾选集自保(按 path 记账;
 * 换种子只重置勾选集与筛选, 折叠记账跨种子保持 —— P3-6, 报告 26-10-07-0542; 勾选集必须重置:
 * 上一种子的勾选落到新种子文件上是真实的优先级误操作面); 批量条/汇总条 sticky 吸底不随行滚动。
 * 行级键盘: 树行 roving tabindex + 方向键移焦 + Enter/Space 勾选(issue 26-10-07-0846;
 * 锚点/记账/回焦/移焦走核心 helpers 单点, 整行不加 role=button —— 行内已含原生控件)。
 * 自包含: 删除本文件 + 三份 index.html 各去 1 行 manifest 即整体退役, 其它零接触。
 */
(function () {
  "use strict";
  const reg = window.AQB_DRAWER_TPL_REG;
  if (!reg) return; /* 核心未载入(清单序错): 静默退出, 守阵会抓 */
  const T = reg.dtHtml;
  const R = reg.dtRaw;
  const H = reg.helpers; /* 公共骨架单点(报告 26-10-07-0845): 工具/sig 比对/事件挂摘 */

  const { num } = H; /* 公共工具: Number(v)||0(核心层单点) */
  const PRIO_LABEL = { 0: "跳过", 1: "普通", 4: "高", 6: "高", 7: "最高" };
  const PRIO_CYCLE = [0, 1, 6, 7]; /* 徽章点击循环序(qB 4 档; 旧值 4 = 高, 归入 6 位) */

  /* 视图偏好(跨重渲染与换变体保持): 筛选 / 折叠目录集 / 勾选集(文件 path); lastSig 供跳过重建 */
  const ui = { filter: "all", folded: new Set(), checked: new Set(), lastSig: "", lastHash: "" };

  const CSS = [
    /* 骨架: 工具条 / 滚动行区(.drawer-body 本体滚动)/ 吸底条 */
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
    /* 行区: 表头吸顶 + 行 grid */
    ".drawer .dt11-head, .drawer .dt11-r { display:grid; gap:8px; align-items:center; padding:0 4px; }",
    ".drawer .dt11-head.hasav, .drawer .dt11-r.hasav { grid-template-columns:26px 18px minmax(0, 1fr) 78px 130px 62px 64px; }",
    ".drawer .dt11-head.noav, .drawer .dt11-r.noav { grid-template-columns:26px 18px minmax(0, 1fr) 78px 130px 64px; }",
    ".drawer .dt11-head { position:sticky; top:0; z-index:1; height:28px; background:var(--bg-card);",
    "  border-bottom:1px solid var(--border); color:var(--fg-dim); font-size:11.5px; white-space:nowrap; }",
    ".drawer .dt11-head .num { text-align:right; }",
    ".drawer .dt11-r { min-height:27px; border-bottom:1px solid var(--hairline); font-size:12px; cursor:default; }",
    ".drawer .dt11-r:hover { background:var(--bg-hover); }",
    ".drawer .dt11-r:focus-visible { outline:2px solid var(--ring); outline-offset:-2px; }",
    ".drawer .dt11-r.is-chk { background:var(--sel-bg); box-shadow:inset 2px 0 0 var(--accent-line); }",
    ".drawer .dt11-r.is-chk:hover { background:var(--sel-bg); }",
    ".drawer .dt11-tgl { display:inline-flex; align-items:center; justify-content:center; width:18px; height:18px;",
    "  padding:0; background:none; border:0; color:var(--fg-dim); cursor:pointer; }",
    ".drawer .dt11-tgl:hover { color:var(--fg); }",
    ".drawer .dt11-tgl .ico { width:11px; height:11px; transition:transform var(--dur) var(--ease); }",
    ".drawer .dt11-tgl.closed .ico { transform:rotate(-90deg); }",
    ".drawer .dt11-ck { width:13px; height:13px; margin:0; accent-color:var(--accent); cursor:pointer; }",
    ".drawer .dt11-n { display:flex; align-items:center; gap:6px; min-width:0; }",
    ".drawer .dt11-nm { overflow:hidden; text-overflow:ellipsis; white-space:nowrap; color:var(--fg); }",
    ".drawer .dt11-r.dir .dt11-nm { font-weight:600; color:var(--fg-soft); }",
    ".drawer .dt11-n .ico { width:13px; height:13px; flex:none; color:var(--fg-dim); }",
    ".drawer .dt11-r.dir .dt11-n .ico { color:var(--accent); }",
    ".drawer .dt11-meta { flex:none; font-size:10.5px; color:var(--fg-dim); border:1px solid var(--border-soft);",
    "  border-radius:999px; padding:0 6px; line-height:15px; white-space:nowrap; }",
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
    ".drawer .dt11-empty { padding:24px 0; text-align:center; color:var(--fg-dim); font-size:12px; }",
    /* 吸底条: 勾选 = 批量条, 未勾 = 汇总条(盖过 .drawer-body 的 padding) */
    ".drawer .dt11-foot { position:sticky; bottom:0; z-index:2; display:flex; align-items:center; gap:8px;",
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
    /* 收起态摘要(44px 头部, dt-summary 容器内) */
    ".drawer .dt11-cs b { font-family:var(--font-mono, ui-monospace, monospace); font-weight:600; color:var(--fg); }",
    ".drawer .dt11-cs b.w { color:var(--warn); }",
    ".drawer .dt11-cs .dim { color:var(--fg-dim); }",
    ".drawer .dt11-load { padding:26px 0; text-align:center; color:var(--fg-dim); font-size:12px; }",
  ].join("\n");

  /* ---------------- 派生: 行模型 + 目录聚合(路径前缀单遍扫描) ---------------- */
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

  /* ---------------- 行渲染 ---------------- */
  let _ctx = null;
  const ctxOf = () => _ctx;
  function prioBadgeClass(p) {
    if (p === 0) return " skip";
    if (p === 7) return " max";
    if (p === 4 || p === 6) return " high";
    return "";
  }
  function rowHtml(item, d, hasAv) {
    const r = item.row;
    const folded = ui.folded.has(r.path);
    const tgl = r.dir
      ? T`<button type="button" class="dt11-tgl${folded ? " closed" : ""}" data-tgl="${r.path}"
          title="${folded ? "展开" : "折叠"} ${r.name}"><svg class="ico" viewBox="0 0 16 16"><use href="#i-chevron"></use></svg></button>`
      : T`<span></span>`;
    const s = r.dir ? d.stats.get(r.path) : null;
    const meta = r.dir
      ? T`<span class="dt11-meta">${s ? s.files : 0} 文件</span>`
      : (item.prog < 1
        ? T`<span class="dt11-meta" title="按进度估算缺口约 ${ctxOf().fmtSize(item.size * (1 - item.prog))}" style="color:var(--warn); border-color:var(--warn-line)">缺 ${ctxOf().fmtSize(item.size * (1 - item.prog))}</span>`
        : "");
    const sizeTxt = r.dir ? ctxOf().fmtSize(s ? s.size : 0) : ctxOf().fmtSize(item.size);
    const prog = r.dir ? statProg(s || { size: 0, done: 0 }) : item.prog * 100;
    const part = prog < 100;
    const avCell = hasAv
      ? (r.dir
        ? (s && s.hasAv
          ? T`<span class="dt11-av" title="子树内最低可用性(最稀缺文件)">${s.minAv.toFixed(2)}</span>`
          : T`<span class="dt11-av" title="子树内暂无可用性数据">—</span>`)
        : (item.av !== undefined && item.av !== null
          ? T`<span class="dt11-av${num(item.av) < 1 ? " low" : ""}" title="qB availability: 全 swarm 中该文件数据的份数">${num(item.av).toFixed(2)}</span>`
          : T`<span class="dt11-av" title="qB 未返回该文件可用性">—</span>`))
      : "";
    const badge = r.dir
      ? T`<span class="dt11-pnone" title="目录本身无优先级; 勾选目录后整棵子树批量设置">—</span>`
      : T`<button type="button" class="dt11-pbadge${prioBadgeClass(item.prio)}" data-cyc="${r.path}"
          title="优先级: ${PRIO_LABEL[item.prio] || "普通"} — 点击循环 跳过→普通→高→最高">${PRIO_LABEL[item.prio] || "普通"}</button>`;
    const chk = r.dir
      ? T`<input type="checkbox" class="dt11-ck" data-dirck="${r.path}" title="勾选 = 整棵子树(${s ? s.files : 0} 个文件)">`
      : T`<input type="checkbox" class="dt11-ck" data-ck="${r.path}" title="勾选该文件">`;
    const hl = r.dir
      ? (chkStateOf(subtreeFiles(r.path, d.fileRows).map((it) => it.row.path)) === 2)
      : ui.checked.has(r.path);
    return T`<div class="dt11-r${r.dir ? " dir" : " file"}${hl ? " is-chk" : ""} ${hasAv ? "hasav" : "noav"}" data-node="${r.path}" tabindex="-1">
      ${R(chk)}${R(tgl)}
      <span class="dt11-n" style="padding-left:${r.depth * 14}px" title="${r.path}"><svg class="ico" viewBox="0 0 16 16"><use href="${r.dir ? "#i-folder" : "#i-list"}"></use></svg><span class="dt11-nm">${r.name}</span>${R(meta)}</span>
      <span class="dt11-sz" title="${r.dir ? "子树合计大小" : "文件大小"}">${sizeTxt}</span>
      <span class="dt11-prog${part ? " part" : ""}" title="${r.dir ? "子树加权平均进度" : "文件进度"} ${prog.toFixed(1)}%">
        <span class="bar"><i style="width:${Math.min(100, Math.max(0, prog)).toFixed(1)}%"></i></span><em>${prog.toFixed(1)}%</em></span>
      ${R(avCell)}
      ${R(badge)}
    </div>`;
  }

  /* 勾选集工具(全部按文件 path 记账) */
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
    /* 数据未变跳过重建(优先级改动补拉 / 换页签回来都会触发通知) */
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

    const htmlRows = [];
    for (const r of d.rows) {
      const show = r.dir
        ? (ui.filter === "all" ? true : dirMatch(r.path, ui.filter, d.stats))
        : (ui.filter === "all" ? true
          : ui.filter === "miss" ? r.progress < 100
            : (files[r.index] ? num(files[r.index].priority) === 0 : false));
      if (!show) continue;
      /* 筛选态下无视折叠全部铺平(命中行可见); 全部态下被折叠目录的整棵子树不渲染 */
      if (ui.filter === "all" && isFolded(r.path)) continue;
      if (r.dir) {
        htmlRows.push(rowHtml({ row: r }, d, d.hasAv));
        continue;
      }
      htmlRows.push(rowHtml(d.itemByPath.get(r.path) || { row: r, size: 0, prog: 0, prio: 1, av: undefined }, d, d.hasAv));
    }
    function isFolded(path) {
      const segs = path.split("/");
      for (let i = 1; i < segs.length; i++) {
        if (ui.folded.has(segs.slice(0, i).join("/"))) return true;
      }
      return false;
    }

    const allPaths = d.fileRows.map((it) => it.row.path);
    const cnt = {
      all: d.fileRows.length,
      miss: d.total.missCnt,
      skip: d.total.skipCnt,
    };
    const chips = [
      T`<button type="button" class="dt11-chip${ui.filter === "all" ? " active" : ""}" data-f="all">全部 <b>${cnt.all}</b></button>`,
      T`<button type="button" class="dt11-chip c-warn${ui.filter === "miss" ? " active" : ""}" data-f="miss" title="只显示存在缺口的文件">未完成 <b>${cnt.miss}</b></button>`,
      T`<button type="button" class="dt11-chip${ui.filter === "skip" ? " active" : ""}" data-f="skip" title="只显示优先级为跳过的文件">跳过 <b>${cnt.skip}</b></button>`,
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
    const html = T`<div class="dt11-wrap">
      <div class="dt11-tools">
        <input type="checkbox" class="dt11-ck" data-ckmaster>
        ${R(chips)}
        <button type="button" class="dt11-ghost" data-fold="open">展开</button>
        <button type="button" class="dt11-ghost" data-fold="close">折叠</button>
        <span class="dt11-hint">勾选目录 = 整棵子树 · 批量条吸底</span>
      </div>
      <div class="dt11-head${d.hasAv ? " hasav" : " noav"}">
        <span></span><span></span><span>名称</span><span class="num">大小</span><span>进度</span>
        ${R(d.hasAv ? T`<span class="num" title="qB availability: 全 swarm 中该数据的份数; 目录取子树最低值">可用性</span>` : "")}
        <span title="点击徽章循环: 跳过 → 普通 → 高 → 最高">优先级</span>
      </div>
      <div class="dt11-body">${R(htmlRows.join(""))}${htmlRows.length ? "" : T`<div class="dt11-empty">该筛选下没有文件</div>`}</div>
      ${R(foot)}
    </div>`;
    const focusKey = H.rowFocusKey(host, "data-node"); /* 重建前记账焦点行(原子换帧打断焦点链) */
    host.replaceChildren(document.createRange().createContextualFragment(html));
    H.roving(host, "data-node", ""); /* 行级键盘锚点(首行, issue 26-10-07-0846; 勾选集无「选中行」语义) */
    H.rowRestore(host, "data-node", focusKey);
    /* 目录行 / 主勾选框三态(native indeterminate) */
    host.querySelectorAll("input[data-dirck]").forEach((el) => {
      const st = chkStateOf(subtreeFiles(el.getAttribute("data-dirck"), d.fileRows).map((it) => it.row.path));
      el.checked = st === 2;
      el.indeterminate = st === 1;
    });
    const master = host.querySelector("input[data-ckmaster]");
    if (master) {
      const st = chkStateOf(allPaths);
      master.checked = st === 2;
      master.indeterminate = st === 1;
    }
  }

  function onClick(ev) {
    const h = ev.currentTarget;
    if (ev.target.closest(".dt11-ck")) return; /* 勾选走 change 事件, 点选框本身不按行处理 */
    /* 优先级徽章: 循环切换单文件(逐次真实提交) */
    const badge = ev.target.closest("[data-cyc]");
    if (badge) {
      ev.stopPropagation();
      const d = derive(_ctx);
      const it = d.itemByPath.get(badge.getAttribute("data-cyc"));
      if (!it) return;
      const cur = it.prio === 4 ? 6 : it.prio;
      const next = PRIO_CYCLE[(PRIO_CYCLE.indexOf(cur) + 1) % PRIO_CYCLE.length];
      _ctx.setFilePriority(next, [it.row.index]);
      return;
    }
    const tgl = ev.target.closest("[data-tgl]");
    if (tgl) {
      const p = tgl.getAttribute("data-tgl") || "";
      if (ui.folded.has(p)) ui.folded.delete(p); else ui.folded.add(p);
      rerender(h);
      return;
    }
    const foldBtn = ev.target.closest("[data-fold]");
    if (foldBtn) {
      const d = derive(_ctx);
      const dirs = [];
      for (const r of d.rows) if (r.dir && r.path) dirs.push(r.path);
      ui.folded = foldBtn.getAttribute("data-fold") === "close" ? new Set(dirs) : new Set();
      rerender(h);
      return;
    }
    const chip = ev.target.closest("[data-f]");
    if (chip) {
      ui.filter = chip.getAttribute("data-f") || "all";
      rerender(h);
      return;
    }
    const bp = ev.target.closest("[data-bp]");
    if (bp) {
      const d = derive(_ctx);
      const idx = batchIndices(d.fileRows);
      if (!idx.length) return;
      _ctx.setFilePriority(Number(bp.getAttribute("data-bp")), idx);
      return;
    }
    if (ev.target.closest("[data-bclear]")) {
      ui.checked = new Set();
      rerender(h);
      return;
    }
    /* 点行 = 勾选(目录 = 整棵子树; 与设计稿 11 同语义) */
    const row = ev.target.closest("[data-node]");
    if (row) toggleRow(row, h);
  }
  function toggleRow(row, h) {
    const d = derive(_ctx);
    const r = d.rows.find((x) => x.path === row.getAttribute("data-node"));
    if (!r) return;
    toggleSet(r.dir ? subtreeFiles(r.path, d.fileRows).map((it) => it.row.path) : [r.path]);
    rerender(h);
  }
  /* 行级键盘(issue 26-10-07-0846): roving tabindex + 方向键/Home/End 移焦 + Enter/Space
   * 转发行激活(= 勾选, 与 click 同口径)。焦点在行内原生控件(勾选框/折叠钮/优先级徽章)
   * 上时不接管 —— 只有 ev.target 是行容器自身才处理, 原生控件键盘行为自持 */
  function onKeyDown(ev) {
    const row = ev.target.closest("[data-node]");
    if (!row || ev.target !== row) return;
    if (ev.key === "Enter" || ev.key === " ") {
      ev.preventDefault();
      toggleRow(row, ev.currentTarget);
      return;
    }
    if (H.rowMove(ev.currentTarget, "data-node", row, ev.key)) ev.preventDefault();
  }
  function onChange(ev) {
    const h = ev.currentTarget;
    const dirck = ev.target.closest("[data-dirck]");
    if (dirck) {
      const d = derive(_ctx);
      toggleSet(subtreeFiles(dirck.getAttribute("data-dirck") || "", d.fileRows).map((it) => it.row.path));
      rerender(h);
      return;
    }
    const ck = ev.target.closest("[data-ck]");
    if (ck) {
      const p = ck.getAttribute("data-ck") || "";
      if (ui.checked.has(p)) ui.checked.delete(p); else ui.checked.add(p);
      rerender(h);
      return;
    }
    if (ev.target.closest("[data-ckmaster]")) {
      const d = derive(_ctx);
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
    /* 宿主元素跨变体复用(同页签只有一个 data-dt-host), 换变体必须摘掉本变体的委托监听 */
    H.unwireEvents(host);
  }

  /* 收起态摘要: 勾选批次 + 文件 / 未完成计数(设计稿 11 的 drawer-csum 口径) */
  function summary(ctx) {
    const files = fileList(ctx);
    if (!files.length) return T`<span class="dt11-cs">无文件列表</span>`;
    _ctx = ctx;
    const d = derive(ctx);
    let checkedSize = 0;
    for (const it of d.fileRows) if (ui.checked.has(it.row.path)) checkedSize += it.size;
    const n = ui.checked.size;
    const head = n
      ? T`<span title="当前勾选批次">已勾 <b>${n}</b> 项 · <b>${ctxOf().fmtSize(checkedSize)}</b></span> · `
      : T`<span class="dim">未勾选 — 勾选行可批量设优先级</span> · `;
    return T`<span class="dt11-cs">${R(head)}<span title="文件计数">文件 <b>${d.fileRows.length}</b></span> · <span title="未完成计数">未完成 <b class="w">${d.total.missCnt}</b></span></span>`;
  }

  const _render = render;
  reg.register({
    id: "11", tab: "content",
    label: "树表批量",
    css: CSS,
    render(host, ctx) {
      wire(host);
      host.__dtCtx = ctx;
      _render(host, ctx);
    },
    summary,
    destroy,
  });
})();
