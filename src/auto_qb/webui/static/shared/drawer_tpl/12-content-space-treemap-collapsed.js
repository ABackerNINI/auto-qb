/* auto-qb WEB UI · 详情面板 content 页签变体 12「空间树图(收起)」(计划 26-10-06-0838 S5)
 *
 * 设计稿: resources/detail-panel-templates/12-content-space-treemap-collapsed.html(collapsed 档;
 * 收起 = 摘要条体积构成, 矮/高 = 左树图 + 右体积榜自适应)。
 * 数据: /files qB 透传(drawer.files), squarified 树图纯前端计算 —— 块面积 = 体积占比,
 * 完整块绿面 / 未完成块琥珀水位(完成度 = --lv 渐变高), 顶层目录组头可折叠成单块聚合。
 * 动作(plan §04 映射行): 悬停互联(纯前端) —— 树图块与体积榜行互加高亮; 点选块/行 = 选中
 * 信息条(纯展示, 无优先级动作 —— 优先级回 classic / 变体 10/11 用)。
 * 渐进字段: 每文件 availability 有则进 title/信息条, 无则省略。
 * 渲染纪律: dtHtml 全量转义(dtRaw 只用于拼接本变体 dtHtml 产出的预转义片段), replaceChildren
 * 原子换帧, 数据未变(整份 files 序列化比对)跳过重建, 选中/折叠/筛选态自保(按 path 记账,
 * 换种子重置); ResizeObserver 随面板拖拽/展开重建图, destroy 摘监听 + disconnect。
 * 自包含: 删除本文件 + 三份 index.html 各去 1 行 manifest 即整体退役, 其它零接触。
 */
(function () {
  "use strict";
  const reg = window.AQB_DRAWER_TPL_REG;
  if (!reg) return; /* 核心未载入(清单序错): 静默退出, 守阵会抓 */
  const T = reg.dtHtml;
  const R = reg.dtRaw;

  const num = (v) => Number(v) || 0;
  const PRIO_LABEL = { 0: "跳过", 1: "普通", 4: "高", 6: "高", 7: "最高" };

  /* 视图偏好(跨重渲染保持): 选中 path / 折叠目录组 / 仅看未完成; lastSig 供跳过重建 */
  const ui = { selPath: "", colG: new Set(), fmiss: false, lastSig: "", lastHash: "", tree: null, mapEl: null, host: null };
  let ro = null; /* ResizeObserver 单例: 面板拖拽调高 / 收起展开后重建图 */

  const CSS = [
    ".drawer .dt12-tools { display:flex; align-items:center; gap:8px; margin-bottom:8px; }",
    ".drawer .dt12-chip { display:inline-flex; align-items:center; gap:5px; height:24px; padding:0 10px;",
    "  border-radius:999px; border:1px solid var(--border-soft); background:var(--surface-1);",
    "  font:12px/1 system-ui, sans-serif; color:var(--fg-muted); cursor:pointer; user-select:none;",
    "  transition:border-color var(--dur) var(--ease), background var(--dur) var(--ease), color var(--dur) var(--ease); }",
    ".drawer .dt12-chip:hover { border-color:var(--border-strong); color:var(--fg); }",
    ".drawer .dt12-chip.active { background:var(--warn-soft); border-color:var(--warn-line); color:var(--fg); }",
    ".drawer .dt12-hint { margin-left:auto; font-size:11px; color:var(--fg-dim); }",
    /* 主区: 左树图 + 右体积榜(wrap 纵列承载工具条/主区/信息条, 主区才是两列 grid) */
    ".drawer .dt12-wrap { display:flex; flex-direction:column; min-height:0; }",
    ".drawer .dt12-main { display:grid; grid-template-columns:minmax(0, 1fr) 288px; gap:10px; min-height:0; align-items:start; }",
    ".drawer .dt12-map { position:relative; overflow:hidden; background:var(--bg-sunken);",
    "  border:1px solid var(--border); border-radius:var(--radius); }",
    ".drawer .dt12-gh { position:absolute; z-index:2; display:flex; align-items:center; gap:5px; height:17px;",
    "  padding:0 6px; border:0; border-bottom:1px solid var(--hairline); background:var(--surface-2);",
    "  font:11px/17px system-ui, sans-serif; color:var(--fg-soft); text-align:left; cursor:pointer;",
    "  overflow:hidden; white-space:nowrap; }",
    ".drawer .dt12-gh:hover { color:var(--fg); }",
    ".drawer .dt12-gh .ico { width:9px; height:9px; flex:none; transition:transform var(--dur) var(--ease); }",
    ".drawer .dt12-gh.closed .ico { transform:rotate(-90deg); }",
    ".drawer .dt12-gh b { font-family:var(--font-mono, ui-monospace, monospace); color:var(--fg-dim); font-weight:400; }",
    ".drawer .dt12-blk { position:absolute; overflow:hidden; background:var(--green-soft);",
    "  border:1px solid var(--green-line); border-radius:3px; cursor:pointer; }",
    ".drawer .dt12-blk.part { background:linear-gradient(to top, var(--warn-soft) var(--lv, 0%), transparent var(--lv, 0%));",
    "  border-color:var(--warn-line); }",
    ".drawer .dt12-blk:hover, .drawer .dt12-blk.hl { border-color:var(--accent-hi); z-index:3; }",
    ".drawer .dt12-blk.sel { box-shadow:inset 0 0 0 2px var(--ring); z-index:4; }",
    ".drawer .dt12-lb { position:absolute; left:0; right:0; top:0; padding:3px 6px; font-size:11px; color:var(--fg);",
    "  white-space:nowrap; overflow:hidden; text-overflow:ellipsis; pointer-events:none; }",
    ".drawer .dt12-blk.part .dt12-lb { color:var(--warn); }",
    ".drawer .dt12-sz { position:absolute; left:0; bottom:0; padding:2px 6px;",
    "  font-family:var(--font-mono, ui-monospace, monospace); font-size:10px; color:var(--fg-soft); pointer-events:none; }",
    ".drawer .dt12-blk.part .dt12-sz { color:var(--warn); }",
    ".drawer .dt12-skip { position:absolute; right:2px; top:2px; padding:0 4px; font-size:9.5px; line-height:13px;",
    "  border:1px dashed var(--border-strong); border-radius:999px; color:var(--fg-dim); pointer-events:none; }",
    ".drawer .dt12-wrap.fmiss .dt12-blk.ok { opacity:.14; }",
    ".drawer .dt12-wrap.fmiss .dt12-row.ok { opacity:.32; }",
    /* 体积榜 */
    ".drawer .dt12-list { overflow-y:auto; border:1px solid var(--border); border-radius:var(--radius); background:var(--bg-card); }",
    ".drawer .dt12-row { display:grid; grid-template-columns:14px minmax(0, 1fr) 62px 58px 42px; gap:7px;",
    "  align-items:center; height:25px; padding:0 8px; border-bottom:1px solid var(--hairline);",
    "  font-size:11.5px; cursor:pointer; }",
    ".drawer .dt12-row:hover, .drawer .dt12-row.hl { background:var(--bg-hover); }",
    ".drawer .dt12-row.is-sel { background:var(--sel-bg); box-shadow:inset 2px 0 0 var(--accent-line); }",
    ".drawer .dt12-row .ico { width:12px; height:12px; color:var(--fg-dim); display:block; }",
    ".drawer .dt12-row .nm { overflow:hidden; text-overflow:ellipsis; white-space:nowrap; color:var(--fg); }",
    ".drawer .dt12-row.part .nm { color:var(--warn); }",
    ".drawer .dt12-row .trk { height:3px; border-radius:999px; background:var(--bg-sunken); overflow:hidden; display:block; }",
    ".drawer .dt12-row .trk i { display:block; height:100%; border-radius:999px; background:var(--fg-dim); }",
    ".drawer .dt12-row .sz { font-family:var(--font-mono, ui-monospace, monospace); font-size:11px;",
    "  color:var(--fg-soft); text-align:right; white-space:nowrap; }",
    ".drawer .dt12-row .pg { font-family:var(--font-mono, ui-monospace, monospace); font-size:11px;",
    "  color:var(--fg-muted); text-align:right; white-space:nowrap; }",
    ".drawer .dt12-row.part .pg { color:var(--warn); }",
    /* 选中信息条(纯展示) */
    ".drawer .dt12-info { display:none; align-items:center; gap:12px; margin-top:8px; padding:7px 10px;",
    "  border:1px solid var(--border); border-radius:var(--radius); background:var(--bg-row); }",
    ".drawer .dt12-info.on { display:flex; }",
    ".drawer .dt12-info .ico { width:15px; height:15px; color:var(--fg-dim); flex:none; }",
    ".drawer .dt12-fin { flex:1 1 200px; min-width:140px; overflow:hidden; }",
    ".drawer .dt12-fin .nm { display:block; font-size:12.5px; color:var(--fg); overflow:hidden;",
    "  text-overflow:ellipsis; white-space:nowrap; }",
    ".drawer .dt12-fin .pt { display:block; font-family:var(--font-mono, ui-monospace, monospace); font-size:10.5px;",
    "  color:var(--fg-dim); overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }",
    ".drawer .dt12-stat { display:flex; flex-direction:column; gap:1px; min-width:52px; }",
    ".drawer .dt12-stat i { font-style:normal; font-size:10px; color:var(--fg-dim); }",
    ".drawer .dt12-stat b { font-family:var(--font-mono, ui-monospace, monospace); font-size:12px; font-weight:600;",
    "  color:var(--fg); white-space:nowrap; }",
    ".drawer .dt12-stat.warn b { color:var(--warn); }",
    ".drawer .dt12-bar { display:flex; align-items:center; gap:7px; min-width:110px; }",
    ".drawer .dt12-bar .track { width:70px; height:5px; border-radius:999px; background:var(--bg-sunken);",
    "  overflow:hidden; position:relative; }",
    ".drawer .dt12-bar .track i { position:absolute; inset:0 auto 0 0; border-radius:999px; background:var(--green); }",
    ".drawer .dt12-bar em { font-style:normal; font-family:var(--font-mono, ui-monospace, monospace); font-size:12px; color:var(--fg); }",
    ".drawer .dt12-close { width:22px; height:22px; display:inline-flex; align-items:center; justify-content:center;",
    "  border:0; border-radius:var(--radius-sm); background:none; color:var(--fg-dim); cursor:pointer; flex:none; }",
    ".drawer .dt12-close:hover { color:var(--fg); background:var(--bg-hover); }",
    ".drawer .dt12-close .ico { width:11px; height:11px; }",
    /* 收起态摘要(44px 头部, dt-summary 容器内): 体积构成条 + 未完成数 */
    ".drawer .dt12-cs { display:inline-flex; align-items:center; gap:8px; min-width:0; }",
    ".drawer .dt12-cs .hbar { display:flex; width:120px; height:6px; border-radius:999px; overflow:hidden;",
    "  background:var(--bg-sunken); flex:none; }",
    ".drawer .dt12-cs .hbar i { display:block; height:100%; background:var(--accent); }",
    ".drawer .dt12-cs b { font-family:var(--font-mono, ui-monospace, monospace); font-weight:600; color:var(--fg); }",
    ".drawer .dt12-cs b.w { color:var(--warn); }",
    ".drawer .dt12-load { padding:26px 0; text-align:center; color:var(--fg-dim); font-size:12px; }",
  ].join("\n");

  /* ---------------- 树构建(与 10 同判据, 自包含) ---------------- */
  function fileList(ctx) {
    return (ctx.drawer && ctx.drawer.files) || [];
  }
  function newDir(name, parentPath, parentDepth) {
    return {
      dir: true, name, path: parentPath ? parentPath + "/" + name : name,
      depth: parentDepth + 1, children: [], size: 0, done: 0, miss: 0,
      files: 0, prog: 100, av: undefined,
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
      node.children.push({
        dir: false, name: last, path: node.path ? node.path + "/" + last : last,
        depth: node.depth + 1, index: i, size: num(f.size),
        prog: Math.round(num(f.progress) * 1000) / 10,
        prio: num(f.priority), av: f.availability,
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
      return;
    }
    let avSet = false, minAv = Infinity;
    for (const c of n.children) {
      aggregate(c);
      n.size += c.size; n.done += c.done; n.miss += c.miss; n.files += c.files;
      if (c.av !== undefined) { /* 目录聚合 = 子树内最低可用性(文件/子目录一并计入) */
        if (!avSet || c.av < minAv) minAv = c.av;
        avSet = true;
      }
    }
    n.prog = n.size > 0 ? n.done / n.size * 100 : 100;
    if (avSet) n.av = minAv; /* 目录 = 子树最低可用性(渐进字段, 全树皆无则保持 undefined) */
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
  function leaves(n) {
    const out = [];
    (function scan(x) {
      if (!x.dir) out.push(x);
      else for (const c of x.children) scan(c);
    })(n);
    return out;
  }

  /* ---------------- squarified 树图布局(块面积 = 体积占比) ---------------- */
  function squarify(items, x, y, w, h) {
    const out = [];
    const list = items.filter((i) => i.a > 0).slice().sort((p, q) => q.a - p.a);
    let X = x, Y = y, W = w, H = h;
    const worst = (row, side) => {
      let s = 0;
      for (const n of row) s += n.a;
      const t = s / side;
      let m = 0;
      for (const n of row) {
        const l = n.a / t;
        const r = Math.max(t / l, l / t);
        if (r > m) m = r;
      }
      return m;
    };
    while (list.length) {
      const vert = W >= H; /* 短边 = H 时沿左缘竖排 */
      const side = vert ? H : W;
      const row = [list.shift()];
      while (list.length) {
        const w1 = worst(row, side);
        const w2 = worst(row.concat([list[0]]), side);
        if (w2 <= w1) row.push(list.shift()); else break;
      }
      const s = row.reduce((acc, n) => acc + n.a, 0);
      let th = s / side;
      if (vert) {
        if (th > W) th = W;
        let cy = Y;
        for (const n of row) {
          const lh = n.a / th;
          out.push({ ref: n.ref, x: X, y: cy, w: th, h: lh });
          cy += lh;
        }
        X += th; W -= th;
      } else {
        if (th > H) th = H;
        let cx = X;
        for (const n of row) {
          const lw = n.a / th;
          out.push({ ref: n.ref, x: cx, y: Y, w: lw, h: th });
          cx += lw;
        }
        Y += th; H -= th;
      }
    }
    return out;
  }
  const scaleRects = (nodes, x, y, w, h) => {
    const total = nodes.reduce((s, n) => s + n.size, 0) || 1;
    return squarify(nodes.map((n) => ({ ref: n, a: n.size / total * w * h })), x, y, w, h);
  };

  /* ---------------- 树图渲染 ---------------- */
  let _ctx = null;
  const ctxOf = () => _ctx;

  function blkCls(n) {
    return n.prog < 100 ? "dt12-blk part" : "dt12-blk ok";
  }
  function blkInner(n, w, h) {
    if (w < 34 || h < 20) return ""; /* 太小不放标签, 悬停看 title */
    const skip = n.dir === false && n.prio === 0 && w > 70
      ? T`<span class="dt12-skip" title="优先级: 跳过">跳过</span>` : "";
    const sz = h >= 34 ? T`<span class="dt12-sz">${ctxOf().fmtSize(n.size)}</span>` : "";
    const nm = n.name.length > 42 ? n.name.slice(0, 41) + "…" : n.name;
    return T`<span class="dt12-lb">${nm}</span>${R(sz)}${R(skip)}`;
  }
  function blkTitle(n, total) {
    const t = n.path + "\n" + ctxOf().fmtSize(n.size) + " · 占 " + (n.size / total * 100).toFixed(1) + "% · 进度 " + n.prog.toFixed(1) + "%";
    return t + (n.miss > 0.5 ? " · 缺 " + ctxOf().fmtSize(n.miss) : "")
      + (n.av !== undefined ? " · 可用性 " + num(n.av).toFixed(2) : "")
      + (!n.dir ? " · 优先级 " + (PRIO_LABEL[n.prio] || "普通") : "");
  }
  function leafBlocks(n, r, total, parts) {
    const style = "left:" + r.x.toFixed(1) + "px;top:" + r.y.toFixed(1) + "px;width:"
      + Math.max(r.w, 1).toFixed(1) + "px;height:" + Math.max(r.h, 1).toFixed(1) + "px;";
    const lv = n.prog < 100 ? ";--lv:" + n.prog.toFixed(1) + "%" : "";
    parts.push(T`<div class="${blkCls(n)}${ui.selPath === n.path ? " sel" : ""}" data-blk="${n.path}"
      style="${style + lv}" title="${blkTitle(n, total)}">${R(blkInner(n, r.w, r.h))}</div>`);
  }
  function layoutMap(host) {
    const mapEl = ui.mapEl;
    if (!mapEl || !mapEl.isConnected || !ui.tree) return;
    const body = mapEl.closest(".drawer-body");
    const tools = host.querySelector(".dt12-tools");
    const info = host.querySelector(".dt12-info");
    const used = (tools ? tools.offsetHeight : 0) + (info && info.classList.contains("on") ? info.offsetHeight : 0) + 42;
    const availH = Math.max(160, (body ? body.clientHeight : 420) - used);
    mapEl.style.height = availH + "px";
    const listEl = host.querySelector(".dt12-list");
    if (listEl) listEl.style.maxHeight = availH + "px";
    const W = mapEl.clientWidth, H = mapEl.clientHeight;
    if (W < 60 || H < 60) return; /* 收起态 body 不可见: 展开时 RO 补建 */
    const tree = ui.tree;
    const total = tree.size || 1;
    const parts = [];
    for (const g of scaleRects(tree.children, 0, 0, W, H)) {
      const dir = g.ref;
      const hasHeader = dir.dir && g.w >= 110 && g.h >= 44;
      const inner = hasHeader
        ? { x: g.x + 1, y: g.y + 17, w: g.w - 2, h: g.h - 18 }
        : { x: g.x + 1, y: g.y + 1, w: g.w - 2, h: g.h - 2 };
      const collapsed = ui.colG.has(dir.path);
      if (hasHeader) {
        parts.push(T`<button type="button" class="dt12-gh${collapsed ? " closed" : ""}" data-gh="${dir.path}"
          style="left:${g.x.toFixed(1)}px;top:${g.y.toFixed(1)}px;width:${g.w.toFixed(1)}px"
          title="${dir.path} · ${dir.files} 个文件 · ${ctxOf().fmtSize(dir.size)} · 占 ${(dir.size / total * 100).toFixed(1)}%">
          <svg class="ico" viewBox="0 0 16 16"><use href="#i-chevron"></use></svg>${dir.name}<b> · ${dir.files} 文件 · ${(dir.size / total * 100).toFixed(1)}%</b></button>`);
      }
      if ((hasHeader && collapsed) || (!hasHeader && (inner.w < 12 || inner.h < 12))) {
        /* 整目录单块(折叠或太小) */
        const style = "left:" + inner.x.toFixed(1) + "px;top:" + inner.y.toFixed(1) + "px;width:"
          + Math.max(inner.w, 1).toFixed(1) + "px;height:" + Math.max(inner.h, 1).toFixed(1) + "px;";
        const lv = dir.prog < 100 ? ";--lv:" + dir.prog.toFixed(1) + "%" : "";
        parts.push(T`<div class="${blkCls(dir)}${ui.selPath === dir.path ? " sel" : ""}" data-blk="${dir.path}"
          style="${style + lv}" title="${blkTitle(dir, total)}">${R(blkInner(dir, inner.w, inner.h))}</div>`);
      } else {
        /* 组内按叶子文件铺排(目录层级由组头与 title 路径承接) */
        for (const r of scaleRects(leaves(dir), inner.x, inner.y, inner.w, inner.h)) {
          leafBlocks(r.ref, r, total, parts);
        }
      }
    }
    mapEl.replaceChildren(document.createRange().createContextualFragment(parts.join("")));
  }
  function listHtml(tree) {
    const total = tree.size || 1;
    const rows = leaves(tree).sort((a, b) => b.size - a.size).map((n) => {
      const share = Math.max(n.size / total * 100, 0.8).toFixed(1);
      return T`<div class="dt12-row${n.prog < 100 ? " part" : " ok"}${ui.selPath === n.path ? " is-sel" : ""}" data-row="${n.path}"
        title="${n.path}&#10;占 ${(n.size / total * 100).toFixed(1)}% · 进度 ${n.prog.toFixed(1)}%${n.av !== undefined ? " · 可用性 " + num(n.av).toFixed(2) : ""}">
        <svg class="ico" viewBox="0 0 16 16"><use href="#i-list"></use></svg>
        <span class="nm">${n.name}</span>
        <span class="trk" title="占总体积 ${(n.size / total * 100).toFixed(1)}%"><i style="width:${share}%"></i></span>
        <span class="sz">${ctxOf().fmtSize(n.size)}</span>
        <span class="pg">${n.prog.toFixed(1)}%</span>
      </div>`;
    }).join("");
    return T`<div class="dt12-list">${R(rows)}</div>`;
  }
  function infoHtml(tree) {
    const n = ui.selPath ? findNode(tree, ui.selPath) : null;
    if (!n) return T`<div class="dt12-info"></div>`;
    const total = tree.size || 1;
    const stats = [
      T`<span class="dt12-stat"><i>${n.dir ? "子树大小" : "大小"}</i><b>${ctxOf().fmtSize(n.size)}</b></span>`,
      T`<span class="dt12-stat"><i>占比</i><b>${(n.size / total * 100).toFixed(1)}%</b></span>`,
      n.av !== undefined
        ? T`<span class="dt12-stat"><i title="${n.dir ? "子树内最低可用性" : "qB availability"}">可用性</i><b>${num(n.av).toFixed(2)}</b></span>`
        : "",
      n.miss > 0.5
        ? T`<span class="dt12-stat warn"><i>缺口</i><b>${ctxOf().fmtSize(n.miss)}</b></span>` : "",
    ].join("");
    return T`<div class="dt12-info on">
      <svg class="ico" viewBox="0 0 16 16"><use href="${n.dir ? "#i-folder" : "#i-list"}"></use></svg>
      <span class="dt12-fin"><span class="nm">${n.name}</span><span class="pt">${n.path}</span></span>
      ${R(stats)}
      <span class="dt12-bar"><span class="track"><i style="width:${Math.min(100, Math.max(0, n.prog)).toFixed(1)}%"></i></span>
        <em>${n.prog.toFixed(1)}%</em></span>
      <button type="button" class="dt12-close" data-selclear title="取消选中"><svg class="ico" viewBox="0 0 16 16"><use href="#i-close"></use></svg></button>
    </div>`;
  }

  function render(host, ctx) {
    const files = fileList(ctx);
    const loading = ctx.drawer && ctx.drawer.filesLoading;
    const hash = (ctx.drawer && ctx.drawer.hash) || "";
    /* 换种子: 选中/折叠/筛选随目标失效 */
    if (hash !== ui.lastHash) {
      ui.lastHash = hash;
      ui.selPath = "";
      ui.colG = new Set();
      ui.fmiss = false;
    }
    /* 数据未变跳过重建 */
    const sig = JSON.stringify(files) + "|" + String(!!loading);
    if (sig === ui.lastSig && host.firstChild) return;
    ui.lastSig = sig;
    _ctx = ctx;
    if (loading && !files.length) {
      host.replaceChildren(document.createRange().createContextualFragment(
        T`<div class="dt12-load"><svg class="ico" viewBox="0 0 16 16"><use href="#i-hourglass"></use></svg><span>正在加载…</span></div>`));
      return;
    }
    if (!files.length) {
      host.replaceChildren(document.createRange().createContextualFragment(
        T`<div class="dt12-load"><span>无文件列表</span></div>`));
      return;
    }
    const tree = buildTree(files);
    ui.tree = tree;
    const html = T`<div class="dt12-wrap${ui.fmiss ? " fmiss" : ""}">
      <div class="dt12-tools">
        <button type="button" class="dt12-chip${ui.fmiss ? " active" : ""}" data-fmiss title="只高亮未完成的块与行">仅看未完成</button>
        <span class="dt12-hint">块面积 = 体积占比 · 悬停树图块与右侧体积榜互联 · 点组头折叠目录</span>
      </div>
      <div class="dt12-main">
        <div class="dt12-map" title="空间树图: 块面积 = 该文件占种子总体积的比例"></div>
        ${R(listHtml(tree))}
      </div>
      ${R(infoHtml(tree))}
    </div>`;
    host.replaceChildren(document.createRange().createContextualFragment(html));
    ui.host = host;
    ui.mapEl = host.querySelector(".dt12-map");
    layoutMap(host);
    if (!ro) {
      ro = new ResizeObserver(() => {
        const m = ui.mapEl;
        if (m && m.isConnected && ui.host) layoutMap(ui.host);
      });
    }
    ro.disconnect();
    ro.observe(ui.mapEl);
  }

  /* ---------------- 悬停互联(纯前端): 树图块 <-> 体积榜行 ---------------- */
  function onOver(ev) {
    const blk = ev.target.closest("[data-blk]");
    const row = ev.target.closest("[data-row]");
    const host = ev.currentTarget;
    if (blk) {
      const r = host.querySelector('.dt12-row[data-row="' + cssEsc(blk.getAttribute("data-blk")) + '"]');
      if (r) r.classList.add("hl");
    } else if (row) {
      const b = host.querySelector('.dt12-blk[data-blk="' + cssEsc(row.getAttribute("data-row")) + '"]');
      if (b) b.classList.add("hl");
    }
  }
  function onOut(ev) {
    const host = ev.currentTarget;
    const el = ev.target.closest("[data-blk],[data-row]");
    if (!el) return;
    const key = el.getAttribute("data-blk") || el.getAttribute("data-row");
    const sel = '[data-row="' + cssEsc(key) + '"],[data-blk="' + cssEsc(key) + '"]';
    host.querySelectorAll(sel).forEach((x) => x.classList.remove("hl"));
  }
  /* path 含引号/反斜杠的概率极低, 但属性选择器里必须成对转义(保底) */
  function cssEsc(s) {
    return String(s).replace(/\\/g, "\\\\").replace(/"/g, '\\"');
  }

  function onClick(ev) {
    const h = ev.currentTarget;
    const gh = ev.target.closest("[data-gh]");
    if (gh) {
      const p = gh.getAttribute("data-gh") || "";
      if (ui.colG.has(p)) ui.colG.delete(p); else ui.colG.add(p);
      ui.lastSig = "";
      _render(h, h.__dtCtx); /* 折叠只改布局, 强制重建整帧(含组头箭头态) */
      return;
    }
    const blk = ev.target.closest("[data-blk]");
    if (blk) {
      ui.selPath = blk.getAttribute("data-blk") || "";
      ui.lastSig = "";
      _render(h, h.__dtCtx);
      return;
    }
    const row = ev.target.closest("[data-row]");
    if (row) {
      ui.selPath = row.getAttribute("data-row") || "";
      ui.lastSig = "";
      _render(h, h.__dtCtx);
      return;
    }
    if (ev.target.closest("[data-selclear]")) {
      ui.selPath = "";
      ui.lastSig = "";
      _render(h, h.__dtCtx);
      return;
    }
    if (ev.target.closest("[data-fmiss]")) {
      ui.fmiss = !ui.fmiss;
      ui.lastSig = "";
      _render(h, h.__dtCtx);
    }
  }

  /* 视图偏好变化走 lastSig 置空整帧重建; 数据通知由核心直调 _render */
  function wire(host) {
    if (host.__dt12Wired) return;
    host.__dt12Wired = true;
    host.__dt12Click = onClick;
    host.addEventListener("click", onClick);
    host.__dt12Over = onOver;
    host.addEventListener("mouseover", onOver);
    host.__dt12Out = onOut;
    host.addEventListener("mouseout", onOut);
  }

  function destroy(host) {
    ui.lastSig = ""; /* 下次挂载强制整帧重建 */
    if (ro) {
      ro.disconnect();
    }
    ui.mapEl = null;
    ui.host = null;
    /* 宿主元素跨变体复用(同页签只有一个 data-dt-host), 换变体必须摘掉本变体的委托监听 */
    if (host) {
      if (host.__dt12Click) {
        host.removeEventListener("click", host.__dt12Click);
        host.__dt12Click = null;
      }
      if (host.__dt12Over) {
        host.removeEventListener("mouseover", host.__dt12Over);
        host.__dt12Over = null;
      }
      if (host.__dt12Out) {
        host.removeEventListener("mouseout", host.__dt12Out);
        host.__dt12Out = null;
      }
      host.__dt12Wired = false;
    }
  }

  /* 收起态摘要: 体积构成条(顶层目录/文件按体积占比) + 未完成数(设计稿 12 口径) */
  function summary(ctx) {
    const files = fileList(ctx);
    if (!files.length) return T`<span class="dt12-cs">无文件列表</span>`;
    _ctx = ctx;
    const groups = new Map(); /* 顶层目录名 -> 体积 */
    let total = 0, done = 0, missCnt = 0;
    for (const f of files) {
      const size = num(f.size);
      const prog = num(f.progress);
      total += size;
      done += size * prog;
      if (prog < 1) missCnt++;
      const top = String(f.name || "").split("/")[0] || "(根)";
      groups.set(top, (groups.get(top) || 0) + size);
    }
    const keys = Array.from(groups.keys()).sort((a, b) => groups.get(b) - groups.get(a)).slice(0, 6);
    const denom = keys.reduce((s, k) => s + groups.get(k), 0) || 1;
    const segs = keys.map((k, i) =>
      T`<i style="width:${(groups.get(k) / denom * 100).toFixed(1)}%;opacity:${(1 - i * 0.13).toFixed(2)}"></i>`).join("");
    return T`<span class="dt12-cs" title="体积构成条(顶层目录占比, 透明度梯度)+ 未完成计数">
      <span class="hbar">${R(segs)}</span>
      共 ${files.length} 个 · ${ctxOf().fmtSize(done)} / ${ctxOf().fmtSize(total)} · 未完成 <b class="w">${missCnt}</b></span>`;
  }

  const _render = render;
  reg.register({
    id: "12", tab: "content",
    label: "空间树图(收起)",
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
