/* auto-qb WEB UI · 详情面板 content 页签变体 10「折叠树 + 选中详情(高)」(计划 26-10-06-0838 S5)
 *
 * 设计稿: resources/detail-panel-templates/10-content-tree-detail-tall.html(tall 档; 收起/矮/高
 * 三档语义全部收进本变体 —— 收起 = 核心内置摘要条, 矮/高 = 左树 + 右 324px 详情自适应滚动)。
 * 数据: /files qB 透传(drawer.files, 进入页签拉一次 + 优先级改动后静默补拉), 树与子树聚合
 * (子树大小 / 文件数 / 加权进度 / 缺口字节 / 最低可用性)全部前端派生, 零后端改动。
 * 动作(plan §04 映射行): 目录点选子树聚合; 文件行优先级徽章 → openFilePrio(经典锚定小菜单,
 * 回执/toast 由既有链自带); 右侧详情优先级分段 → setFilePriority(p, indices)(S5 批量通道,
 * 单文件 = [index], 目录 = 整棵子树收集)。重命名不在本变体设计内 → 回 classic 用(试用期对照)。
 * 渐进字段: 每文件 availability(qB 版本浮动)有则渲染可用性格与详情格, 无则整格省略不占位。
 * 渲染纪律: dtHtml 全量转义(dtRaw 只用于拼接本变体 dtHtml 产出的预转义片段), replaceChildren
 * 原子换帧, 数据未变(整份 files 序列化比对)跳过重建, 滚动/折叠/筛选/选中态自保(换种子只重置
 * 选中与筛选, 折叠记账跨种子保持 —— P3-6, 报告 26-10-07-0542)。
 * 行级键盘: 树行 roving tabindex + 方向键移焦 + Enter/Space 激活(issue 26-10-07-0846;
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
  const PRIO_ORDER = [0, 1, 6, 7];

  /* 视图偏好(跨重渲染与换变体保持): 筛选 / 折叠目录集 / 选中节点路径; lastSig 供跳过重建 */
  const ui = { filter: "all", folded: new Set(), selPath: "", lastSig: "", lastHash: "" };

  const CSS = [
    /* 主从双栏骨架(右栏 324px = 设计稿口径)。滚动容器是 .drawer-body 本身(overflow:auto),
     * 左栏随内容自然生长, 右栏详情 sticky 吸顶 + 内部滚动 —— 高/矮档都成立 */
    ".drawer .dt10-wrap { display:grid; grid-template-columns:minmax(0, 1fr) 324px; align-items:start; }",
    ".drawer .dt10-left { min-width:0; padding-right:14px; }",
    ".drawer .dt10-right { position:sticky; top:0; max-height:58vh; overflow-y:auto;",
    "  border-left:1px solid var(--border); padding-left:14px; padding-bottom:6px; }",
    /* 工具条: 筛选 chips + 展开/折叠 */
    ".drawer .dt10-tools { flex:none; display:flex; align-items:center; gap:6px; margin-bottom:8px; flex-wrap:wrap; }",
    ".drawer .dt10-chip { display:inline-flex; align-items:center; gap:5px; height:24px; padding:0 10px;",
    "  border-radius:999px; border:1px solid var(--border-soft); background:var(--surface-1);",
    "  font:12px/1 system-ui, sans-serif; color:var(--fg-muted); cursor:pointer; user-select:none;",
    "  transition:border-color var(--dur) var(--ease), background var(--dur) var(--ease), color var(--dur) var(--ease); }",
    ".drawer .dt10-chip b { font-family:var(--font-mono, ui-monospace, monospace); font-weight:600; }",
    ".drawer .dt10-chip:hover { border-color:var(--border-strong); color:var(--fg); }",
    ".drawer .dt10-chip.active { background:var(--accent-soft); border-color:var(--accent-line); color:var(--fg); }",
    ".drawer .dt10-chip.c-warn.active { background:var(--warn-soft); border-color:var(--warn-line); }",
    ".drawer .dt10-ghost { display:inline-flex; align-items:center; gap:4px; height:24px; padding:0 9px;",
    "  border-radius:var(--radius-sm); border:1px solid transparent; background:none;",
    "  font:12px/1 system-ui, sans-serif; color:var(--fg-dim); cursor:pointer; }",
    ".drawer .dt10-ghost:hover { color:var(--fg); border-color:var(--border-soft); }",
    ".drawer .dt10-hint { margin-left:auto; font-size:11px; color:var(--fg-dim); }",
    /* 树行(grid 行制): 引导缩进 + 类型 + 名称 + 大小 + 进度 + 优先级 */
    ".drawer .dt10-tree { min-height:0; }",
    ".drawer .dt10-r { display:grid; grid-template-columns:18px minmax(0, 1fr) 78px 128px 62px;",
    "  gap:8px; align-items:center; height:29px; padding-right:4px; border-bottom:1px solid var(--hairline);",
    "  font-size:12px; cursor:default; }",
    ".drawer .dt10-r:hover { background:var(--bg-hover); }",
    ".drawer .dt10-r.sel { background:var(--sel-bg); box-shadow:inset 2px 0 0 var(--accent-line); }",
    ".drawer .dt10-r:focus-visible { outline:2px solid var(--ring); outline-offset:-2px; }",
    ".drawer .dt10-tgl { display:inline-flex; align-items:center; justify-content:center; width:18px; height:18px;",
    "  padding:0; background:none; border:0; color:var(--fg-dim); cursor:pointer; }",
    ".drawer .dt10-tgl:hover { color:var(--fg); }",
    ".drawer .dt10-tgl .ico { width:11px; height:11px; transition:transform var(--dur) var(--ease); }",
    ".drawer .dt10-tgl.closed .ico { transform:rotate(-90deg); }",
    ".drawer .dt10-n { display:flex; align-items:center; gap:6px; min-width:0; }",
    ".drawer .dt10-nm { overflow:hidden; text-overflow:ellipsis; white-space:nowrap; color:var(--fg); }",
    ".drawer .dt10-r.dir .dt10-nm { font-weight:600; color:var(--fg-soft); }",
    ".drawer .dt10-n .ico { width:13px; height:13px; flex:none; color:var(--fg-dim); }",
    ".drawer .dt10-r.dir .dt10-n .ico { color:var(--accent); }",
    ".drawer .dt10-meta { flex:none; font-size:10.5px; color:var(--fg-dim); border:1px solid var(--border-soft);",
    "  border-radius:999px; padding:0 6px; line-height:15px; white-space:nowrap; }",
    ".drawer .dt10-miss { flex:none; font-size:10.5px; color:var(--warn); background:var(--warn-soft);",
    "  border:1px solid var(--warn-line); border-radius:999px; padding:0 6px; line-height:15px; white-space:nowrap; }",
    ".drawer .dt10-sz { font-family:var(--font-mono, ui-monospace, monospace); font-size:11.5px;",
    "  color:var(--fg-soft); text-align:right; white-space:nowrap; }",
    ".drawer .dt10-prog { display:flex; align-items:center; gap:7px; min-width:0; }",
    ".drawer .dt10-prog .bar { flex:1; position:relative; height:5px; border-radius:999px;",
    "  background:var(--bg-sunken); overflow:hidden; }",
    ".drawer .dt10-prog .bar i { position:absolute; inset:0 auto 0 0; border-radius:999px; background:var(--green); }",
    ".drawer .dt10-prog.part .bar i { background:var(--warn); }",
    ".drawer .dt10-prog em { font-style:normal; font-family:var(--font-mono, ui-monospace, monospace); font-size:11px;",
    "  color:var(--fg-muted); width:44px; text-align:right; flex:none; }",
    ".drawer .dt10-pbadge { display:inline-flex; align-items:center; justify-content:center; height:17px; padding:0 7px;",
    "  border-radius:999px; font-size:10.5px; white-space:nowrap; border:1px solid transparent;",
    "  background:var(--surface-2); color:var(--fg-muted); cursor:pointer;",
    "  transition:border-color var(--dur) var(--ease), color var(--dur) var(--ease); }",
    ".drawer .dt10-pbadge:hover { border-color:var(--border-strong); color:var(--fg); }",
    ".drawer .dt10-pbadge.skip { background:transparent; border-style:dashed; border-color:var(--border-strong); color:var(--fg-dim); }",
    ".drawer .dt10-pbadge.high { background:var(--warn-soft); border-color:var(--warn-line); color:var(--warn); }",
    ".drawer .dt10-pbadge.max { background:var(--error-soft); border-color:var(--error-line); color:var(--error); }",
    ".drawer .dt10-pnone { font-family:var(--font-mono, ui-monospace, monospace); font-size:11px; color:var(--fg-dim); }",
    ".drawer .dt10-foot { flex:none; margin-top:8px; font-size:11.5px; color:var(--fg-dim); }",
    ".drawer .dt10-foot b { font-family:var(--font-mono, ui-monospace, monospace); color:var(--fg-muted); font-weight:600; }",
    ".drawer .dt10-foot b.w { color:var(--warn); }",
    /* 右栏详情 */
    ".drawer .dt10-empty { padding:40px 8px; text-align:center; color:var(--fg-dim); font-size:12px; line-height:1.8; }",
    ".drawer .dt10-kicker { display:flex; align-items:center; gap:6px; font-size:11px; color:var(--fg-dim); margin-top:2px; }",
    ".drawer .dt10-kicker .ico { width:13px; height:13px; }",
    ".drawer .dt10-dname { margin:6px 0 4px; font-size:13.5px; font-weight:600; line-height:1.5; color:var(--fg); word-break:break-all; }",
    ".drawer .dt10-dpath { font-family:var(--font-mono, ui-monospace, monospace); font-size:11px; color:var(--fg-dim);",
    "  line-height:1.6; word-break:break-all; }",
    ".drawer .dt10-dchips { display:flex; gap:6px; flex-wrap:wrap; margin:10px 0 2px; }",
    ".drawer .dt10-stchip { display:inline-flex; align-items:center; height:20px; padding:0 8px; border-radius:999px;",
    "  font-size:11px; border:1px solid transparent; }",
    ".drawer .dt10-stchip.ok { background:var(--green-soft); border-color:var(--green-line); color:var(--green); }",
    ".drawer .dt10-stchip.warn { background:var(--warn-soft); border-color:var(--warn-line); color:var(--warn); }",
    ".drawer .dt10-stchip.skip { background:transparent; border-style:dashed; border-color:var(--border-strong); color:var(--fg-dim); }",
    ".drawer .dt10-dprog { display:flex; align-items:center; gap:10px; margin:8px 0 12px; }",
    ".drawer .dt10-dprog b { font-family:var(--font-mono, ui-monospace, monospace); font-size:22px; font-weight:600;",
    "  color:var(--fg); line-height:1; white-space:nowrap; }",
    ".drawer .dt10-dprog .bar { flex:1; position:relative; height:6px; border-radius:999px; background:var(--bg-sunken); overflow:hidden; }",
    ".drawer .dt10-dprog .bar i { position:absolute; inset:0 auto 0 0; border-radius:999px; background:var(--green); }",
    ".drawer .dt10-dgrid { display:grid; grid-template-columns:1fr 1fr; gap:1px; background:var(--hairline);",
    "  border:1px solid var(--hairline); }",
    ".drawer .dt10-cell { background:var(--bg-card); padding:8px 10px; }",
    ".drawer .dt10-cell i { display:block; font-style:normal; font-size:10.5px; color:var(--fg-dim); margin-bottom:3px; }",
    ".drawer .dt10-cell b { font-family:var(--font-mono, ui-monospace, monospace); font-size:13px; font-weight:600; color:var(--fg); }",
    ".drawer .dt10-cell.warn b { color:var(--warn); }",
    ".drawer .dt10-sec { margin:14px 0 6px; font-size:12px; font-weight:600; color:var(--fg-muted); }",
    ".drawer .dt10-pseg { display:grid; grid-template-columns:repeat(4, 1fr); gap:4px; }",
    ".drawer .dt10-seg { height:26px; border:1px solid var(--border); border-radius:var(--radius-sm);",
    "  background:var(--surface-1); color:var(--fg-muted); font:11.5px/1 system-ui, sans-serif; cursor:pointer;",
    "  transition:border-color var(--dur) var(--ease), background var(--dur) var(--ease), color var(--dur) var(--ease); }",
    ".drawer .dt10-seg:hover { border-color:var(--border-strong); color:var(--fg); }",
    ".drawer .dt10-seg.skip.on { background:transparent; border-style:dashed; border-color:var(--border-strong); color:var(--fg-dim); }",
    ".drawer .dt10-seg.norm.on { background:var(--surface-2); border-color:var(--border-strong); color:var(--fg); }",
    ".drawer .dt10-seg.high.on { background:var(--warn-soft); border-color:var(--warn-line); color:var(--warn); }",
    ".drawer .dt10-seg.max.on { background:var(--error-soft); border-color:var(--error-line); color:var(--error); }",
    ".drawer .dt10-note { margin:10px 0 0; font-size:11px; color:var(--fg-dim); line-height:1.7; }",
    ".drawer .dt10-note b { color:var(--fg-muted); font-weight:600; }",
    /* 收起态摘要(44px 头部, dt-summary 容器内) */
    ".drawer .dt10-cs b { font-family:var(--font-mono, ui-monospace, monospace); font-weight:600; color:var(--fg); }",
    ".drawer .dt10-cs b.w { color:var(--warn); }",
    ".drawer .dt10-cs .dim { color:var(--fg-dim); }",
    ".drawer .dt10-load { padding:26px 0; text-align:center; color:var(--fg-dim); font-size:12px; }",
  ].join("\n");

  /* ---------------- 树构建与子树聚合 ---------------- */
  function fileList(ctx) {
    return (ctx.drawer && ctx.drawer.files) || [];
  }
  function newDir(name, parentPath, parentDepth) {
    return {
      dir: true, name, path: parentPath ? parentPath + "/" + name : name,
      depth: parentDepth + 1, children: [], size: 0, done: 0, miss: 0,
      files: 0, dirs: 0, prog: 100, minAv: Infinity, hasAv: false,
    };
  }
  function buildTree(files) {
    const root = newDir("", "", -1);
    for (let i = 0; i < files.length; i++) {
      const f = files[i];
      const parts = String(f.name || "").split("/").filter(Boolean);
      let node = root;
      for (let d = 0; d < parts.length - 1; d++) {
        let next = null;
        for (const c of node.children) {
          if (c.dir && c.name === parts[d]) { next = c; break; }
        }
        if (!next) {
          next = newDir(parts[d], node.path, node.depth);
          node.children.push(next);
        }
        node = next;
      }
      const last = parts[parts.length - 1] || "文件 " + i;
      const prio = num(f.priority);
      node.children.push({
        dir: false, name: last, path: node.path ? node.path + "/" + last : last,
        depth: node.depth + 1, index: i, size: num(f.size),
        prog: Math.round(num(f.progress) * 1000) / 10,
        prio, availability: f.availability,
      });
    }
    aggregate(root);
    return root;
  }
  function aggregate(n) {
    if (!n.dir) {
      n.done = n.size * (n.prog / 100);
      n.miss = Math.max(0, n.size - n.done);
      n.files = 1;
      if (n.availability !== undefined && n.availability !== null) {
        n.hasAv = true;
        n.minAv = num(n.availability);
      }
      return;
    }
    for (const c of n.children) {
      aggregate(c);
      n.size += c.size; n.done += c.done; n.miss += c.miss; n.files += c.files;
      if (c.dir) n.dirs += c.dirs + 1;
      if (c.hasAv && c.minAv < n.minAv) n.minAv = c.minAv;
      n.hasAv = n.hasAv || c.hasAv;
    }
    n.prog = n.size > 0 ? n.done / n.size * 100 : 100;
  }
  function findNode(n, path) {
    if (path && n.path === path) return n;
    if (!n.dir) return null;
    for (const c of n.children) {
      const hit = findNode(c, path);
      if (hit) return hit;
    }
    return null;
  }
  function subtreeIndices(n) {
    const out = [];
    (function scan(x) {
      if (!x.dir) out.push(x.index);
      else for (const c of x.children) scan(c);
    })(n);
    return out;
  }

  /* ---------------- 筛选 ---------------- */
  function leafMatch(n) {
    if (ui.filter === "miss") return !n.dir && n.prog < 100;
    if (ui.filter === "skip") return !n.dir && n.prio === 0;
    return true;
  }
  function match(n) {
    if (ui.filter === "all") return true;
    if (!n.dir) return leafMatch(n);
    for (const c of n.children) if (match(c)) return true;
    return false;
  }

  /* ---------------- 行渲染 ---------------- */
  function prioBadgeClass(p) {
    if (p === 0) return " skip";
    if (p === 6 || p === 4 || p === 7) return p === 7 ? " max" : " high";
    return "";
  }
  function progHtml(n, dirLabel) {
    const part = n.prog < 100;
    return T`<span class="dt10-prog${part ? " part" : ""}" title="${dirLabel} ${n.prog.toFixed(1)}%">
      <span class="bar"><i style="width:${Math.min(100, Math.max(0, n.prog)).toFixed(1)}%"></i></span>
      <em>${n.prog.toFixed(1)}%</em></span>`;
  }
  function rowHtml(n) {
    const folded = ui.folded.has(n.path);
    const tgl = n.dir
      ? T`<button type="button" class="dt10-tgl${folded ? " closed" : ""}" data-tgl="${n.path}"
          title="${folded ? "展开" : "折叠"} ${n.name}"><svg class="ico" viewBox="0 0 16 16"><use href="#i-chevron"></use></svg></button>`
      : T`<span></span>`;
    const meta = n.dir
      ? T`<span class="dt10-meta" title="目录内共 ${n.files} 个文件${n.dirs ? " · " + n.dirs + " 个子目录" : ""}">${n.files} 文件</span>`
      : (n.prog < 100 ? T`<span class="dt10-miss" title="按进度估算缺口约 ${ctxOf().fmtSize(n.miss)}">缺 ${ctxOf().fmtSize(n.miss)}</span>` : "");
    const badge = n.dir
      ? T`<span class="dt10-pnone" title="目录本身无优先级; 选中后可在右侧整目录批量设置">—</span>`
      : T`<button type="button" class="dt10-pbadge${prioBadgeClass(n.prio)}" data-prio="${n.index}"
          title="优先级: ${PRIO_LABEL[n.prio] || "普通"} — 点击弹出优先级小菜单">${PRIO_LABEL[n.prio] || "普通"}</button>`;
    return T`<div class="dt10-r${n.dir ? " dir" : " file"}${ui.selPath === n.path ? " sel" : ""}" data-node="${n.path}" tabindex="-1">
      ${R(tgl)}
      <span class="dt10-n" style="padding-left:${n.depth * 14}px" title="${n.path}"><svg class="ico" viewBox="0 0 16 16"><use href="${n.dir ? "#i-folder" : "#i-list"}"></use></svg><span class="dt10-nm">${n.name}</span>${R(meta)}</span>
      <span class="dt10-sz" title="${n.dir ? "子树合计大小" : "文件大小"}">${ctxOf().fmtSize(n.size)}</span>
      ${R(progHtml(n, n.dir ? "子树加权平均进度" : "文件进度"))}
      ${R(badge)}
    </div>`;
  }

  /* render 期只读引用(纯格式化), 与 07 同口径 */
  let _ctx = null;
  const ctxOf = () => _ctx;

  function detailHtml(n, hasAv) {
    if (!n) {
      return T`<div class="dt10-empty">未选中节点<br>点选左侧任意文件或目录查看详情</div>`;
    }
    const isDir = n.dir;
    const done = n.dir ? n.done : n.size * (n.prog / 100);
    const chips = isDir
      ? (n.miss > 0.5
        ? T`<span class="dt10-stchip warn" title="子树内 ${n.files - countDone(n)} 个文件仍有缺口">未完成 ${n.files - countDone(n)} 个 · 缺 ${ctxOf().fmtSize(n.miss)}</span>`
        : T`<span class="dt10-stchip ok" title="子树内全部文件均已完整">全部完整</span>`)
      : (n.prog < 100
        ? T`<span class="dt10-stchip warn" title="按块校验存在缺口, 有源可补">缺块 ${ctxOf().fmtSize(n.miss)}</span>`
        : T`<span class="dt10-stchip ok" title="该文件全部块均已完整">已完成</span>`);
    const skipChip = (!isDir && n.prio === 0)
      ? T`<span class="dt10-stchip skip" title="优先级为跳过: 不参与下载, 已有数据保留">已跳过</span>` : "";
    const avCell = hasAv
      ? T`<div class="dt10-cell"><i title="${isDir ? "子树内最低可用性(最稀缺文件)" : "qB availability: 全 swarm 中该文件数据的份数"}">可用性</i><b>${isDir ? n.minAv.toFixed(2) : num(n.availability).toFixed(2)}</b></div>`
      : "";
    const segs = PRIO_ORDER.map((p) => {
      const on = !isDir && n.prio === p;
      const cls = p === 0 ? "skip" : p === 1 ? "norm" : p === 7 ? "max" : "high";
      return T`<button type="button" class="dt10-seg ${cls}${on ? " on" : ""}" data-setp="${p}"
        title="设为${PRIO_LABEL[p]}${isDir ? " — 作用于目录内全部 " + n.files + " 个文件" : ""}">${PRIO_LABEL[p]}</button>`;
    }).join("");
    return T`<div class="dt10-kicker"><svg class="ico" viewBox="0 0 16 16"><use href="${isDir ? "#i-folder" : "#i-list"}"></use></svg>${isDir ? (n.depth < 0 ? "种子根目录" : "目录") : "文件"}</div>
      <div class="dt10-dname" title="${n.name}">${n.name}</div>
      <div class="dt10-dpath" title="${n.path}">${n.path || "(根)"}</div>
      <div class="dt10-dchips">${R(chips)}${R(skipChip)}</div>
      <div class="dt10-dprog"><b>${n.prog.toFixed(1)}<i style="font-style:normal; font-size:12px; color:var(--fg-muted)">%</i></b>
        <span class="bar"><i style="width:${Math.min(100, Math.max(0, n.prog)).toFixed(1)}%"></i></span></div>
      <div class="dt10-dgrid">
        <div class="dt10-cell"><i>${isDir ? "子树大小" : "大小"}</i><b>${ctxOf().fmtSize(n.size)}</b></div>
        <div class="dt10-cell"><i>${isDir ? "文件 / 子目录" : "已完成"}</i><b>${isDir ? n.files + " / " + n.dirs : ctxOf().fmtSize(done)}</b></div>
        <div class="dt10-cell${n.miss > 0.5 ? " warn" : ""}"><i>缺口</i><b>${n.miss > 0.5 ? ctxOf().fmtSize(n.miss) : "0"}</b></div>
        ${R(avCell)}
      </div>
      <div class="dt10-sec">${isDir ? "目录批量优先级" : "优先级"}</div>
      <div class="dt10-pseg">${R(segs)}</div>
      <p class="dt10-note">${R(isDir
        ? T`作用于目录内全部 <b>${n.files}</b> 个文件(含子目录), 走既有 files/priority 命令链, 回执见 toast。`
        : T`优先级徽章(左树)弹出小菜单; 此处分段直接生效。重命名请切回「经典」模板。`)}</p>`;
  }
  function countDone(n) {
    let c = 0;
    (function scan(x) {
      if (!x.dir) { if (x.prog >= 100) c++; }
      else for (const k of x.children) scan(k);
    })(n);
    return c;
  }

  function render(host, ctx) {
    const files = fileList(ctx);
    const loading = ctx.drawer && ctx.drawer.filesLoading;
    const hash = (ctx.drawer && ctx.drawer.hash) || "";
    /* P3-5(报告 26-10-07-0542): fetch 失败标记 —— 失败与「真没有」在变体里不同形态 */
    const err = (ctx.drawer && ctx.drawer.filesError) || "";
    /* 换种子: 选中/筛选随目标失效(与 classic drawerSelPath 同口径); 折叠集不清(P3-6, 报告
     * 26-10-07-0542: 折叠态口径统一为跨种子保持, 与 general 组 dt01/02 一致) —— 记账 key 是
     * path, 新种子的 path 空间完全不同, 旧条目自然不命中(= 新种子从默认展开态起但容器不清空);
     * 同名目录(剧集/专辑系列)则延续上一部的折叠选择。容器随「展开全部」按钮与重折叠自然回收 */
    if (hash !== ui.lastHash) {
      ui.lastHash = hash;
      ui.selPath = "";
      ui.filter = "all";
    }
    /* 数据未变跳过重建(优先级改动补拉 / 换页签回来都会触发通知) */
    const sig = JSON.stringify(files) + "|" + String(!!loading) + "|" + err;
    if (H.skipUnchanged(host, ui, sig)) return;
    _ctx = ctx;
    const hasAv = files.some((f) => f && f.availability !== undefined && f.availability !== null);
    if (loading && !files.length) {
      host.replaceChildren(document.createRange().createContextualFragment(
        T`<div class="dt10-load"><svg class="ico" viewBox="0 0 16 16"><use href="#i-hourglass"></use></svg><span>正在加载…</span></div>`));
      return;
    }
    /* 错误态先于空态(P3-5): 失败且无数据不是"真的没有"; content 页签无轮询, 文案不承诺自动重拉 */
    if (err && !files.length) {
      host.replaceChildren(document.createRange().createContextualFragment(
        T`<div class="dt10-load"><svg class="ico" viewBox="0 0 16 16"><use href="#i-warn"></use></svg><span title="${err}">文件列表加载失败, 数据不可用</span></div>`));
      return;
    }
    if (!files.length) {
      host.replaceChildren(document.createRange().createContextualFragment(
        T`<div class="dt10-load"><span>无文件列表</span></div>`));
      return;
    }
    const tree = buildTree(files);
    const sel = findNode(tree, ui.selPath);
    const rows = [];
    (function emit(n) {
      for (const c of n.children) {
        if (!match(c)) continue;
        rows.push(rowHtml(c));
        if (c.dir && (ui.filter !== "all" || !ui.folded.has(c.path))) emit(c);
      }
    })(tree);
    const cnt = { all: tree.files };
    const missCnt = countBy(tree, (x) => !x.dir && x.prog < 100);
    const skipCnt = countBy(tree, (x) => !x.dir && x.prio === 0);
    cnt.miss = missCnt; cnt.skip = skipCnt;
    const chips = [
      T`<button type="button" class="dt10-chip${ui.filter === "all" ? " active" : ""}" data-f="all">全部 <b>${cnt.all}</b></button>`,
      T`<button type="button" class="dt10-chip c-warn${ui.filter === "miss" ? " active" : ""}" data-f="miss" title="只显示存在缺口的文件">未完成 <b>${cnt.miss}</b></button>`,
      T`<button type="button" class="dt10-chip${ui.filter === "skip" ? " active" : ""}" data-f="skip" title="只显示优先级为跳过的文件">跳过 <b>${cnt.skip}</b></button>`,
    ].join("");
    const html = T`<div class="dt10-wrap">
      <section class="dt10-left">
        <div class="dt10-tools">${R(chips)}
          <button type="button" class="dt10-ghost" data-fold="open" title="展开全部目录">展开</button>
          <button type="button" class="dt10-ghost" data-fold="close" title="折叠全部目录">折叠</button>
          <span class="dt10-hint">点行查看详情 · 点箭头折叠目录</span>
        </div>
        <div class="dt10-tree">${R(rows.join(""))}</div>
        <div class="dt10-foot">${tree.files} 个文件${tree.dirs ? " · " + tree.dirs + " 个目录" : ""} ·
          <b>${ctxOf().fmtSize(tree.size)}</b> · 总进度 <b>${tree.prog.toFixed(1)}%</b> ·
          未完成 <b class="w">${cnt.miss}</b></div>
      </section>
      <aside class="dt10-right">${R(detailHtml(sel, hasAv))}</aside>
    </div>`;
    const focusKey = H.rowFocusKey(host, "data-node"); /* 重建前记账焦点行(原子换帧打断焦点链) */
    host.replaceChildren(document.createRange().createContextualFragment(html));
    H.roving(host, "data-node", ui.selPath); /* 行级键盘锚点(选中行或首行, issue 26-10-07-0846) */
    H.rowRestore(host, "data-node", focusKey);
  }
  function countBy(n, pred) {
    let c = 0;
    (function scan(x) {
      if (pred(x)) c++;
      for (const k of x.children || []) scan(k);
    })(n);
    return c;
  }

  function onClick(ev) {
    const h = ev.currentTarget;
    /* 优先级徽章: 复用经典锚定小菜单(openFilePrio 读 currentTarget 定位, 委托下 currentTarget
     * 是宿主 —— 手工传入徽章元素; 先 stopPropagation, 防宿主外 window click 收层器立即关菜单) */
    const badge = ev.target.closest("[data-prio]");
    if (badge) {
      ev.stopPropagation();
      const idx = Number(badge.getAttribute("data-prio"));
      _ctx.openFilePrio({ target: ev.target, currentTarget: badge }, idx);
      return;
    }
    const seg = ev.target.closest("[data-setp]");
    if (seg) {
      const sel = findNode(buildTree(fileList(_ctx)), ui.selPath);
      if (!sel) return;
      const p = Number(seg.getAttribute("data-setp"));
      _ctx.setFilePriority(p, subtreeIndices(sel));
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
      const all = collectDirs(buildTree(fileList(_ctx)));
      ui.folded = foldBtn.getAttribute("data-fold") === "close" ? new Set(all) : new Set();
      rerender(h);
      return;
    }
    const chip = ev.target.closest("[data-f]");
    if (chip) {
      ui.filter = chip.getAttribute("data-f") || "all";
      rerender(h);
      return;
    }
    const row = ev.target.closest("[data-node]");
    if (row) {
      const p = row.getAttribute("data-node") || "";
      ui.selPath = ui.selPath === p ? "" : p; /* 再点同一行取消(与 classic fileRowSelect 同口径) */
      rerender(h);
    }
  }
  function collectDirs(n) {
    const out = [];
    (function scan(x) {
      if (x.dir && x.path) out.push(x.path);
      for (const c of x.children || []) scan(c);
    })(n);
    return out;
  }

  /* 视图偏好变化后的强制重渲染(sig 不含偏好, 置空 lastSig 即可; 口径同 04/07) */
  function rerender(host) {
    ui.lastSig = "";
    const ctx = host.__dtCtx;
    if (ctx) _render(host, ctx);
  }

  /* 行级键盘(issue 26-10-07-0846): roving tabindex + 方向键/Home/End 移焦 + Enter/Space
   * 转发行激活(与 click 同口径: 再触发同路径取消)。焦点在行内原生控件(折叠钮/优先级
   * 徽章)上时不接管 —— 只有 ev.target 是行容器自身才处理, 原生控件键盘行为自持 */
  function onKeyDown(ev) {
    const row = ev.target.closest("[data-node]");
    if (!row || ev.target !== row) return;
    if (ev.key === "Enter" || ev.key === " ") {
      ev.preventDefault();
      const p = row.getAttribute("data-node") || "";
      ui.selPath = ui.selPath === p ? "" : p;
      rerender(ev.currentTarget);
      return;
    }
    if (H.rowMove(ev.currentTarget, "data-node", row, ev.key)) ev.preventDefault();
  }

  function wire(host) {
    H.wireEvents(host, { click: onClick, keydown: onKeyDown });
  }

  function destroy(host) {
    ui.lastSig = ""; /* 下次挂载强制整帧重建 */
    /* 宿主元素跨变体复用(同页签只有一个 data-dt-host), 换变体必须摘掉本变体的委托监听 */
    H.unwireEvents(host);
  }

  /* 收起态摘要: 当前选中节点 + 文件 / 未完成计数(设计稿 10 的 drawer-csum 口径) */
  function summary(ctx) {
    const files = fileList(ctx);
    if (!files.length) return T`<span class="dt10-cs">无文件列表</span>`;
    _ctx = ctx;
    let miss = 0;
    for (const f of files) if (num(f.progress) < 1) miss++;
    const selLast = ui.selPath ? ui.selPath.split("/").pop() : "";
    return T`<span class="dt10-cs" title="已选节点 + 文件 / 未完成计数">${R(selLast
      ? T`已选 <b>${selLast}</b> · ` : T`<span class="dim">未选中 —</span> · `)}共 ${files.length} 文件 · 未完成 <b class="w">${miss}</b></span>`;
  }

  const _render = render;
  reg.register({
    id: "10", tab: "content",
    label: "树 + 详情",
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
