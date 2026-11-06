/* nav_graph.js ---- kb.nav 关系图组件 (2026-11-07 从 nav_page.html 拆出)

   为什么单独成文件: 图组件自带索引 / 布局 / 交互, 约 500 行, 混进壳里会把三视图的重渲染逻辑淹没;
   拆出来后壳只保留「抽屉里挂一个挂载点」这一行接线。

   两个出口形态 (同一个组件, 不同宿主):
     - 抽屉内 compact 挂载: 只有 局部 / 关联 两档 (420px 宽放不下全库泳道)
     - 全屏层挂载: 局部 / 关联 / 全库 三档
   「关联」= 当前文档 + 它的全部一度关联文档 (我认领 + 认领我 + 库外件), 落在族泳道上;
   「全库」= 整个库的团级图。

   数据契约 (nav_data.collect_nav 的加法字段, 不改 collect() 本体):
     data.items[].targets = [{t, st, raw}]   st: ok | ext | basename | dead
     data.ext = {库外件路径: [声明了它的台账 link]}

   为什么不用 item.refs 直接画: refs 是**声明原值**, 1811 条里 578 条目标"看起来不存在"
   (325 条其实在库内、253 条被归档搬走), 直接画会有一半是悬空边。

   零依赖 / 零 CDN / 纯手写 SVG: 壳的守阵 (tests/test_kb_nav_shell.py) 禁一切 http(s) 资源引用,
   且静态导出件要 file:// 能用 —— 引任何图形库都会同时破这两条。

   对外只暴露 window.MBGraph.mount(host, opts)。 */
(function () {
  "use strict";

  var FORM_CN = { issue: "issue", plan: "计划", report: "报告", task: "档案", ext: "库外件", dead: "失效" };
  var FORM_COLOR = { issue: "#e2a55a", plan: "#56c8d7", report: "#7fc79a", task: "#97a3f5", ext: "#6b7681", dead: "#4a545e" };
  var FORM_RANK = { issue: 0, plan: 1, report: 2, task: 3, ext: 4, dead: 5 };
  var LANES = ["issue", "plan", "report", "task"];
  var NO_KEY = "(无主键)";
  var ST_TAG = { ok: "闭环", single: "单向", ext: "库外件", basename: "归档回退", dead: "失效" };
  var CAP1 = 96;   // 局部图一度关联上限 (超过折叠成一行提示)
  var CAP2 = 84;   // 二度总量上限

  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"]/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c];
    });
  }
  function trunc(s, n) {
    s = String(s == null ? "" : s);
    return s.length > n ? s.slice(0, n - 1) + "\u2026" : s;
  }

  /* ---------- 索引 (按 data 对象缓存: 30s 轮询会换新对象, 重挂载不重建) ---------- */
  var CACHE = new WeakMap();

  function buildIndex(data, byLink) {
    var nodes = new Map(), edges = [], out = new Map(), inn = new Map();
    function node(link, st) {
      var n = nodes.get(link);
      if (n) return n;
      var item = byLink && byLink.get(link);
      n = item
        ? { link: link, form: item.form, title: item.title, topic: item.topic || "", status: item.status || "", ledger: true, deg: 0 }
        : {
            link: link,
            form: st === "dead" ? "dead" : "ext",
            title: link.split("/").pop(),
            topic: "",
            status: "",
            ledger: false,
            exists: st !== "dead",
            deg: 0,
          };
      nodes.set(link, n);
      return n;
    }
    function push(m, k, v) {
      if (!m.has(k)) m.set(k, []);
      m.get(k).push(v);
    }

    (data.items || []).forEach(function (item) {
      node(item.link, "ok");
      (item.targets || []).forEach(function (tg) {
        var e = { s: item.link, t: tg.t, st: tg.st, raw: tg.raw || "" };
        edges.push(e);
        node(tg.t, tg.st);
      });
    });
    /* 库外件的反向边: 坑档 / 基线 / 切片声明了某件 —— 没有这一步,「一个坑档被谁认领」永远看不见 */
    Object.keys(data.ext || {}).forEach(function (path) {
      (data.ext[path] || []).forEach(function (link) {
        edges.push({ s: path, t: link, st: "ok", back: true });
        node(path, "ext");
      });
    });

    var has = new Set();
    edges.forEach(function (e) { has.add(e.s + "\u0000" + e.t); });
    edges.forEach(function (e) {
      e.mutual = has.has(e.t + "\u0000" + e.s);
      nodes.get(e.s).deg++;
      nodes.get(e.t).deg++;
      push(out, e.s, e);
      push(inn, e.t, e);
    });
    return { nodes: nodes, edges: edges, out: out, inn: inn };
  }

  function getIndex(data, byLink) {
    var hit = CACHE.get(data);
    if (!hit) {
      hit = buildIndex(data, byLink);
      CACHE.set(data, hit);
    }
    return hit;
  }

  function neighbors(idx, link) {
    var seen = new Map(), order = [];
    function one(other, e, dir) {
      var o = seen.get(other);
      if (!o) {
        o = { node: idx.nodes.get(other), out: false, in: false, edges: [] };
        seen.set(other, o);
        order.push(other);
      }
      o[dir] = true;
      o.edges.push(e);
    }
    (idx.out.get(link) || []).forEach(function (e) { one(e.t, e, "out"); });
    (idx.inn.get(link) || []).forEach(function (e) { one(e.s, e, "in"); });
    return order.map(function (k) { return seen.get(k); });
  }

  function relState(o) {
    if (o.node.form === "dead") return "dead";
    if (o.node.form === "ext") return o.node.exists === false ? "dead" : "ext";
    return o.out && o.in ? "ok" : "single";
  }

  function radius(n, scale) {
    return ((4.2 + Math.min(8, Math.sqrt(n.deg || 1) * 1.3)) * (scale || 1));
  }

  /* ---------- 局部布局: 同心环, 环深 = 跳数 ---------- */
  function layoutRing(idx, center, steps, W, H) {
    var cx = W / 2, cy = H / 2, pad = 26;
    var ns = neighbors(idx, center.link).sort(function (a, b) {
      var d = FORM_RANK[a.node.form] - FORM_RANK[b.node.form];
      return d || b.node.deg - a.node.deg;
    });
    /* 抽屉 380x250: 圆周长就那么大, 超过 ~18 个节点必然互相压盖成一圈糊 —— 宁可折叠也不能糊 */
    var compact = W < 620;
    var cap = compact ? 18 : CAP1;
    var rs = compact ? 0.74 : 1;   /* 同一套半径按宿主缩 */
    var hidden = Math.max(0, ns.length - cap);
    ns = ns.slice(0, cap);

    var span = Math.min(W, H) / 2 - pad;
    /* 环半径: 给外环留通道 (r2 要比 r1 大出可视距离), 节点多时靠折叠而不是把圆撑满 ——
       撑满会让 96 个 r≈12 的圆挤在同一圆周上互相压盖, 且 2 跳环与一度环重合 (边长为 0)。 */
    var r1 = Math.max(span * 0.42, Math.min(span * 0.58, 34 + ns.length * 1.35));
    var nodes = [{ node: center, x: cx, y: cy, r: radius(center, rs) + 3, ring: 0 }];
    var edges = [], pos = new Map();

    ns.forEach(function (o, k) {
      var a = -Math.PI / 2 + (k / Math.max(1, ns.length)) * Math.PI * 2;
      var n = { node: o.node, x: cx + Math.cos(a) * r1, y: cy + Math.sin(a) * r1, r: radius(o.node, rs), ring: 1, angle: a };
      nodes.push(n);
      pos.set(o.node.link, n);
      edges.push({ from: { x: cx, y: cy }, to: n, st: relState(o), kind: "spoke" });
    });

    if (steps >= 2 && ns.length) {
      var r2 = Math.min(span, r1 + Math.max(30, span * 0.32));
      var budget = compact ? 22 : CAP2, inner = new Set([center.link]);
      ns.forEach(function (o) { inner.add(o.node.link); });
      ns.forEach(function (o) {
        if (budget <= 0) return;
        var sibs = neighbors(idx, o.node.link).filter(function (q) { return !inner.has(q.node.link); });
        sibs.sort(function (a, b) { return b.node.deg - a.node.deg; });
        var take = sibs.slice(0, Math.min(3, budget));
        budget -= take.length;
        var base = pos.get(o.node.link).angle;
        var spread = Math.min(0.36, 0.92 / Math.max(1, take.length));
        take.forEach(function (q, j) {
          inner.add(q.node.link);
          var a = base + (j - (take.length - 1) / 2) * spread;
          var n = { node: q.node, x: cx + Math.cos(a) * r2, y: cy + Math.sin(a) * r2, r: radius(q.node, rs) - 0.8, ring: 2 };
          nodes.push(n);
          edges.push({ from: pos.get(o.node.link), to: n, st: relState(q), kind: "outer" });
        });
      });
    }
    return { W: W, H: H, cx: cx, cy: cy, r1: r1, nodes: nodes, edges: edges, hidden: hidden, compact: W < 620 };
  }

  /* ---------- 全库布局: 族泳道 x 专题团 (确定性, 不跑力导向) ---------- */
  function layoutAtlas(idx, data, focus, scope, W) {
    var related = null;
    if (scope === "related") {
      related = new Set([focus]);
      neighbors(idx, focus).forEach(function (o) { related.add(o.node.link); });
    }
    var cByLink = new Map(), cById = new Map(), byId = new Map(), lanes = {};
    LANES.forEach(function (f) { lanes[f] = []; });
    (data.items || []).forEach(function (i) {
      var key = i.form + "|" + (i.topic || NO_KEY);
      var c = cById.get(key);
      if (!c) {
        c = { id: key, form: i.form, topic: i.topic || NO_KEY, members: [], inn: 0, ext: 0 };
        cById.set(key, c);
        lanes[i.form].push(c);
      }
      c.members.push(i);
      cByLink.set(i.link, c);
    });

    var maxMembers = 0;
    LANES.forEach(function (f) {
      var all = lanes[f], keep = [], singles = 0, frMembers = [];
      all.forEach(function (c) {
        var hit = scope === "related" ? c.members.some(function (m) { return related.has(m.link); }) : true;
        if (c.members.length === 1) {
          /* 全库档: 单件专题不进画布 —— 774 个团里 676 个是单件, 全画出来就是一面对称的墙
             (第一版实测), 结构信息反而归零, 收进本族「碎片节点」保住"大团挂到单件"的关系。
             关联档例外: 用户要的就是"本件 + 它的全部关联", 把一个关联件折进碎片等于没画。 */
          singles++;
          if (scope === "related" && hit) { keep.push(c); return; }
          if (hit) frMembers = frMembers.concat(c.members);
          return;
        }
        if (!hit) return;
        keep.push(c);
        if (c.members.length > maxMembers) maxMembers = c.members.length;
      });
      keep.sort(function (a, b) { return b.members.length - a.members.length || (a.topic < b.topic ? -1 : 1); });
      keep.singles = singles;
      var fr = { id: f + "|__frag__", form: f, topic: "碎片带", members: frMembers, inn: 0, ext: 0, frag: true };
      keep.frag = fr;
      lanes[f] = keep;
      /* 只有**留在画布上**的团进 byId: 被范围过滤掉的团若还留在索引里, 画团间边时取不到坐标
         (实测报 undefined.toFixed) —— cById 走全集做查找, byId 走可见集做绘制 */
      keep.forEach(function (c) { byId.set(c.id, c); });
      if (keep.length) byId.set(fr.id, fr);   /* 空泳道整条不画, 它的碎片节点也不该参与连边 (无坐标) */
    });

    var agg = new Map();
    function anchor(c) { return c.members.length >= 2 ? c : lanes[c.form].frag; }
    idx.edges.forEach(function (e) {
      if (e.st !== "ok") return;
      var a0 = cByLink.get(e.s), b0 = cByLink.get(e.t);
      if (!a0 || !b0) return;
      if (a0 === b0) { a0.inn++; return; }
      var a = anchor(a0), b = anchor(b0);
      if (a === b) return;
      a.ext++;
      b.ext++;
      var k = a.id < b.id ? a.id + "\u0000" + b.id : b.id + "\u0000" + a.id;
      var o = agg.get(k);
      if (!o) { o = { a: a, b: b, w: 0 }; agg.set(k, o); }
      o.w++;
    });
    var pairs = [];
    agg.forEach(function (o) {
      var a = byId.get(o.a.id), b = byId.get(o.b.id);
      if (!a || !b) return;
      o.a = a;
      o.b = b;
      pairs.push(o);
    });

    /* 走货架式布局: 每个团一个气泡, 面积 ~ 件数 */
    var PAD_L = W < 760 ? 54 : 74, PAD_R = 22, GAP = W < 760 ? 9 : 13, ROW_GAP = 16, HEAD = 30, TAIL = 24, FRAG_W = 66;
    var usable = W - PAD_L - PAD_R - FRAG_W;
    var y = 0, contentRight = 0;
    LANES.forEach(function (f) {
      var arr = lanes[f];
      if (!arr.length && scope === "related") { lanes[f].laneH = 0; return; }
      var x = 0, row = 0;
      arr.forEach(function (c) {
        c.r = 7 + Math.sqrt(c.members.length) * (maxMembers > 40 ? 3.1 : 3.8);
        if (x + c.r * 2 > usable && x > 0) { x = 0; row++; }
        c.x = PAD_L + x + c.r;
        c.yRow = row;
        x += c.r * 2 + GAP;
      });
      var rows = [];
      arr.forEach(function (c) { rows[c.yRow] = Math.max(rows[c.yRow] || 0, c.r); });
      var yy = y + HEAD;
      for (var i = 0; i < rows.length; i++) {
        arr.forEach(function (c) { if (c.yRow === i) c.y = yy + rows[i]; });
        yy += rows[i] * 2 + ROW_GAP;
      }
      var laneH = (yy - y) + TAIL;
      lanes[f].laneTop = y;
      lanes[f].laneH = laneH;
      var right = 0;
      arr.forEach(function (c) { right = Math.max(right, c.x + c.r); });
      lanes[f].frag.r = 13;
      /* 碎片节点贴着本族内容右缘, 不钉在画布最右: 关联档常常只有两三个团, 钉死会让连线和空白拉满一整屏 */
      lanes[f].frag.x = Math.min(W - PAD_R - 20, right + 46);
      lanes[f].frag.y = y + HEAD + 12;
      if (right > contentRight) contentRight = right;
      y += laneH + 6;
    });
    return { W: W, H: y + 12, lanes: lanes, pairs: pairs, cById: byId, scope: scope, focus: focus, related: related,
             contentW: Math.max(contentRight + 70, PAD_L + 200) };
  }

  /* ---------- 渲染器 ---------- */
  function mount(host, opts) {
    var data = opts.data, idx = getIndex(data, opts.byLink);
    function normScope(v) {
      if (opts.compact) return v === "atlas" ? "atlas" : "local";   /* 抽屉放不下全库泳道 */
      return v === "atlas" || v === "all" ? v : "local";
    }
    var state = {
      scope: normScope(opts.scope),
      atlasScope: "related",
      steps: opts.steps === 2 ? 2 : 1,
      showFrag: !!opts.showFrag,   /* 碎片节点默认只显示角标不画边: 578/1811 条 ref 的目标是单件专题, 全画出来它变成假枢纽 */
      center: opts.focus,
      sel: null,
      stack: [],
    };
    /* 档位变更回报给壳: 抽屉每 30s 轮询都会重挂一次, 状态留在闭包里就必然被洗回默认
       (同 pitfalls/web-ui/poll-reseed-filter.md 的坑型) —— 壳侧存 S.graph, 重挂时回填。 */
    function notify() {
      if (opts.onState) opts.onState({ scope: state.scope, steps: state.steps, showFrag: state.showFrag });
    }
    var shell = document.createElement("div");
    shell.className = "mg";
    host.appendChild(shell);

    function scopes() {
      var list = [{ k: "local", t: "局部", h: "本件居中, 环深 = 跳数" }, { k: "atlas", t: "关联图", h: "本件 + 全部一度关联, 按族泳道排" }];
      if (!opts.compact) list.push({ k: "all", t: "全库", h: "整个库的团级图" });
      return list;
    }

    function toolbar() {
      var cur = scopes().filter(function (s) { return s.k === state.scope; })[0] || scopes()[0];
      var btns = scopes().map(function (s) {
        return '<button type="button" class="mgscope' + (s.k === state.scope ? " on" : "") + '" data-scope="' + s.k + '" title="' +
          esc(s.h) + '">' + s.t + "</button>";
      }).join("");
      return '<div class="mgbar">' + btns +
        '<span class="mghint">' + esc(cur.h) + "</span>" +
        (state.scope === "local"
          ? '<button type="button" class="mgact' + (state.steps >= 2 ? " on" : "") + '" data-act="hop">2 跳</button>'
          : '<button type="button" class="mgact' + (state.showFrag ? " on" : "") + '" data-act="frag" title="显示 / 隐藏指向单件专题碎片的链">碎片链</button>') +
        (opts.compact ? '<button type="button" class="mgact" data-act="expand">展开</button>' : "") +
        "</div>";
    }

    function legend() {
      return '<div class="mglegend">' +
        '<span><i style="background:' + FORM_COLOR.issue + '"></i>issue</span>' +
        '<span><i style="background:' + FORM_COLOR.plan + '"></i>计划</span>' +
        '<span><i style="background:' + FORM_COLOR.report + '"></i>报告</span>' +
        '<span><i style="background:' + FORM_COLOR.task + '"></i>档案</span>' +
        '<span><i class="hollow"></i>库外件(可跳)</span>' +
        '<span><i class="line solid"></i>双向闭环</span>' +
        '<span><i class="line dash"></i>单向认领</span>' +
        "</div>";
    }

    function drawRing(W, H) {
      var g = layoutRing(idx, idx.nodes.get(state.center), state.steps, W, H);
      var p = [];
      p.push('<defs><marker id="mg-ar" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">' +
        '<path d="M0,0 L10,5 L0,10 z" fill="#e2a55a"/></marker></defs>');
      p.push('<circle cx="' + g.cx + '" cy="' + g.cy + '" r="' + g.r1 + '" fill="none" stroke="rgba(255,255,255,.055)"/>');
      if (state.steps >= 2) {
        p.push('<circle cx="' + g.cx + '" cy="' + g.cy + '" r="' + Math.min(Math.min(W, H) / 2 - 26, g.r1 + Math.min(W, H) / 12) +
          '" fill="none" stroke="rgba(255,255,255,.035)"/>');
      }
      g.edges.forEach(function (e) {
        var x1 = e.from.x, y1 = e.from.y, x2 = e.to.x, y2 = e.to.y;
        var dx = x2 - x1, dy = y2 - y1, L = Math.sqrt(dx * dx + dy * dy) || 1;
        var pad = e.kind === "spoke" ? e.to.r + 2 : e.to.r + 1;
        x2 -= dx / L * pad; y2 -= dy / L * pad;
        x1 += dx / L * (e.kind === "spoke" ? 9 : 2); y1 += dy / L * (e.kind === "spoke" ? 9 : 2);
        var stroke, dash = "", mk = "";
        if (e.kind === "outer") { stroke = "rgba(255,255,255,.12)"; dash = ' stroke-dasharray="2 4"'; }
        else if (e.st === "ok") stroke = "rgba(86,200,215,.55)";
        else if (e.st === "single") { stroke = "rgba(226,165,90,.6)"; dash = ' stroke-dasharray="5 4"'; mk = ' marker-end="url(#mg-ar)"'; }
        else { stroke = "rgba(107,118,129,.45)"; dash = ' stroke-dasharray="1 4"'; }
        p.push('<path d="M' + x1.toFixed(1) + "," + y1.toFixed(1) + " L" + x2.toFixed(1) + "," + y2.toFixed(1) +
          '" stroke="' + stroke + '" stroke-width="1.3" fill="none"' + dash + mk + "/>");
      });
      g.nodes.forEach(function (n) {
        var c = FORM_COLOR[n.node.form] || "#6b7681";
        var hollow = !n.node.ledger;
        p.push('<g class="mgnode" data-link="' + esc(n.node.link) + '" data-ledger="' + (n.node.ledger ? 1 : 0) + '" style="cursor:pointer">' +
          (n.ring === 0 ? '<circle cx="' + n.x + '" cy="' + n.y + '" r="' + (n.r + 5) + '" fill="none" stroke="' + c + '" stroke-opacity=".35"/>' : "") +
          '<circle cx="' + n.x.toFixed(1) + '" cy="' + n.y.toFixed(1) + '" r="' + n.r.toFixed(1) + '" fill="' + (hollow ? "none" : c) +
          '" fill-opacity="' + (hollow ? 0 : 0.82) + '" stroke="' + c + '" stroke-width="' + (n.ring === 0 ? 2 : 1) + '"' +
          (hollow ? ' stroke-dasharray="3 3"' : "") + "/></g>");
      });
      g.nodes.forEach(function (n) {
        if (n.ring === 0) {
          p.push('<text x="' + n.x + '" y="' + (n.y + n.r + (g.compact ? 13 : 16)).toFixed(1) +
            '" fill="#dde3e8" font-size="' + (g.compact ? 10.5 : 12) + '" text-anchor="middle" style="font-family:var(--sans)" pointer-events="none">' +
            esc(trunc(n.node.title, g.compact ? 18 : 26)) + "</text>");
          return;
        }
        if (g.compact || g.nodes.length > 40) return;   /* 抽屉 380px 下逐个打标签只会叠成一团 */
        var dx = n.x - g.cx, dy = n.y - g.cy, L = Math.sqrt(dx * dx + dy * dy) || 1;
        var anchor = dx > 16 ? "start" : dx < -16 ? "end" : "middle";
        p.push('<text x="' + (n.x + dx / L * (n.r + 6)).toFixed(1) + '" y="' + (n.y + dy / L * (n.r + 6) + 3.2).toFixed(1) +
          '" fill="#8e99a3" font-size="9.5" text-anchor="' + anchor + '" style="font-family:var(--sans)" pointer-events="none">' +
          esc(trunc(n.node.title, 16)) + "</text>");
      });
      if (g.hidden) {
        p.push('<text x="' + g.cx + '" y="' + (g.cy + g.r1 + 26) + '" fill="#6b7681" font-size="10" text-anchor="middle" ' +
          'style="font-family:var(--mono)" pointer-events="none">\u2026 另 ' + g.hidden + " 个一度关联已折叠</text>");
      }
      return { svg: p.join(""), W: g.W, H: g.H };
    }

    function drawAtlas(W) {
      var scope = state.scope === "all" ? "all" : "related";
      var g = layoutAtlas(idx, data, state.center, scope, W);
      var p = [];
      LANES.forEach(function (f) {
        var arr = g.lanes[f];
        if (!arr || !arr.length) return;
        var top = arr.laneTop, h = arr.laneH;
        p.push('<rect x="2" y="' + top + '" width="' + (W - 4) + '" height="' + h + '" rx="7" fill="#12161b" stroke="rgba(255,255,255,.045)"/>');
        p.push('<text x="12" y="' + (top + 17) + '" fill="' + FORM_COLOR[f] + '" font-size="10.5" style="font-family:var(--mono)">' + f + "</text>");
        p.push('<text x="12" y="' + (top + 30) + '" fill="#5b666f" font-size="9" style="font-family:var(--mono)">' + arr.length + " 团</text>");
      });
      g.pairs.forEach(function (pr) {
        if (!isFinite(pr.a.x) || !isFinite(pr.b.x)) return;   /* 兜档: 没有坐标的团不画边 */
        if (!state.showFrag && (pr.a.frag || pr.b.frag)) return;
        var ax = pr.a.x, ay = pr.a.y, bx = pr.b.x, by = pr.b.y;
        var dx = bx - ax, dy = by - ay, L = Math.sqrt(dx * dx + dy * dy) || 1;
        var bow = Math.min(52, L * 0.12) * (ax < bx ? 1 : -1);
        var mx = (ax + bx) / 2 + (-dy / L) * bow, my = (ay + by) / 2 + (dx / L) * bow;
        p.push('<path class="mgedge" data-a="' + esc(pr.a.id) + '" data-b="' + esc(pr.b.id) + '" d="M' + ax.toFixed(1) + "," + ay.toFixed(1) +
          " Q" + mx.toFixed(1) + "," + my.toFixed(1) + " " + bx.toFixed(1) + "," + by.toFixed(1) + '" fill="none" stroke="#56c8d7"' +
          ' stroke-opacity="' + Math.min(0.5, 0.08 + pr.w * 0.07).toFixed(3) + '" stroke-width="' + Math.min(2.4, 0.5 + pr.w * 0.3).toFixed(2) + '"/>');
      });
      LANES.forEach(function (f) {
        var arr = g.lanes[f];
        if (!arr || !arr.length) return;
        arr.forEach(function (c) {
          var col = FORM_COLOR[c.form], lonely = c.ext === 0;
          var bd = lonely ? "rgba(226,165,90,.75)" : "rgba(86,200,215,.48)";
          var focal = c.members.some(function (m) { return m.link === state.center; });
          p.push('<g class="mgcl" data-id="' + esc(c.id) + '" style="cursor:pointer">');
          p.push('<circle cx="' + c.x.toFixed(1) + '" cy="' + c.y.toFixed(1) + '" r="' + c.r.toFixed(1) + '" fill="' + col +
            '" fill-opacity="' + (focal ? 0.3 : 0.15) + '" stroke="' + (focal ? "rgba(86,200,215,.95)" : bd) +
            '" stroke-width="' + (focal ? 1.8 : 1.2) + '" data-stroke="' + bd + '"' + (lonely ? ' stroke-dasharray="4 3"' : "") + "/>");
          if (c.r >= 13) {
            p.push('<text x="' + c.x.toFixed(1) + '" y="' + (c.y + 3.2).toFixed(1) + '" fill="#cfd7de" font-size="' + (c.r >= 20 ? 10 : 8.5) +
              '" text-anchor="middle" style="font-family:var(--mono)" pointer-events="none">' + c.members.length + "</text>");
          }
          if (c.r >= 22) {
            p.push('<text x="' + c.x.toFixed(1) + '" y="' + (c.y + c.r + 10).toFixed(1) + '" fill="#8e99a3" font-size="8.5" text-anchor="middle" ' +
              'style="font-family:var(--mono)" pointer-events="none">' + esc(trunc(c.topic, Math.round(c.r / 3.4))) + "</text>");
          }
          p.push("</g>");
        });
        var fr = arr.frag;
        if (scope === "related" && !fr.ext) return;
        p.push('<g class="mgcl" data-id="' + esc(fr.id) + '" style="cursor:pointer">' +
          '<circle cx="' + fr.x.toFixed(1) + '" cy="' + fr.y.toFixed(1) + '" r="' + fr.r + '" fill="#1c242e" stroke="rgba(107,118,129,.5)" ' +
          'stroke-width="1.1" stroke-dasharray="3 3" data-stroke="rgba(107,118,129,.5)"/>' +
          '<text x="' + fr.x.toFixed(1) + '" y="' + (fr.y + 3.2).toFixed(1) + '" fill="#8e99a3" font-size="8.5" text-anchor="middle" ' +
          'style="font-family:var(--mono)" pointer-events="none">' + fr.members.length + "</text></g>");
      });
      return { svg: p.join(""), W: W, H: g.H, layout: g };
    }

    function render() {
      var hostW = Math.max(260, (host.clientWidth || 380) - 2);
      var hostH = Math.max(240, (host.clientHeight || 0) - 62);
      var W = opts.compact ? hostW : Math.max(760, hostW);
      var out, H;
      if (state.scope === "local") {
        H = opts.compact ? 250 : Math.max(340, Math.min(hostH, Math.round(W * 0.62)));
        out = drawRing(W, H);
      } else {
        out = drawAtlas(W);
        var narrow = Math.min(W, out.layout.contentW);   /* 关联档常常只落在两三个团上, 画布跟着收窄 */
        if (narrow < W) out = drawAtlas((W = narrow));
        H = out.H;
      }
      shell.innerHTML = toolbar() + '<div class="mgcanvas"><svg viewBox="0 0 ' + W + " " + H +
        '" width="' + (opts.compact ? "100%" : W) + '" height="' + H + '">' + out.svg + "</svg></div>" + legend();
      bind(W, H, out.layout);
    }

    function tipEl() {
      var t = document.getElementById("mgTip");
      if (!t) {
        t = document.createElement("div");
        t.id = "mgTip";
        t.className = "mgtip";
        document.body.appendChild(t);
      }
      return t;
    }

    function bind(W, H, layout) {
      shell.querySelectorAll(".mgscope").forEach(function (b) {
        b.addEventListener("click", function () {
          state.scope = b.dataset.scope;
          state.stack = [];
          state.center = opts.focus;
          notify();
          render();
        });
      });
      var hop = shell.querySelector('[data-act="hop"]');
      if (hop) hop.addEventListener("click", function () { state.steps = state.steps >= 2 ? 1 : 2; notify(); render(); });
      var fragBtn = shell.querySelector('[data-act="frag"]');
      if (fragBtn) fragBtn.addEventListener("click", function () { state.showFrag = !state.showFrag; notify(); render(); });
      var exp = shell.querySelector('[data-act="expand"]');
      if (exp) exp.addEventListener("click", function () { if (opts.onExpand) opts.onExpand(state.scope); });

      shell.querySelectorAll(".mgnode").forEach(function (el) {
        var link = el.dataset.link;
        el.addEventListener("click", function (ev) {
          var nd = idx.nodes.get(link);
          var isLedger = el.dataset.ledger === "1";
          if (ev.ctrlKey || ev.metaKey || !isLedger) {   /* 库外件 / 新标签: 直接开原文, 不换抽屉 */
            var href = opts.hrefFor ? opts.hrefFor(link) : "";
            if (nd && nd.form !== "dead" && href) window.open(href, "_blank");
            return;
          }
          state.center = link;
          if (opts.onOpen) opts.onOpen(link);
        });
        el.addEventListener("mousemove", function (ev) { showTip(ev, idx.nodes.get(link)); });
        el.addEventListener("mouseleave", function () { tipEl().style.opacity = 0; });
      });

      shell.querySelectorAll(".mgcl").forEach(function (el) {
        var c = layout && layout.cById ? layout.cById.get(el.dataset.id) : null;
        el.addEventListener("mousemove", function (ev) {
          if (c) showTip(ev, { title: c.topic, form: c.form, topic: c.topic, deg: c.members.length, ledger: true });
        });
        el.addEventListener("mouseleave", function () { tipEl().style.opacity = 0; });
        el.addEventListener("click", function () {
          if (c && c.members && c.members.length) {
            var best = c.members.slice().sort(function (a, b) { return (idx.nodes.get(b.link).deg || 0) - (idx.nodes.get(a.link).deg || 0); })[0];
            state.center = best.link;
            if (opts.onOpen) opts.onOpen(best.link);
          }
        });
      });
    }

    function showTip(ev, n) {
      if (!n) return;
      var t = tipEl();
      t.innerHTML = "<b>" + esc(trunc(n.title, 60)) + "</b><div class=\"p\">" + esc(n.link || "") + "</div>" +
        '<div class="m">' + (FORM_CN[n.form] || n.form) + (n.status ? " \u00b7 " + esc(n.status) : "") +
        (n.topic ? ' \u00b7 <span class="mono">' + esc(n.topic) + "</span>" : "") + " \u00b7 度 " + (n.deg || 0) + "</div>";
      t.style.left = Math.max(8, Math.min(ev.clientX + 14, window.innerWidth - 300)) + "px";
      t.style.top = Math.max(8, Math.min(ev.clientY + 12, window.innerHeight - 90)) + "px";
      t.style.opacity = 1;
    }

    render();
    return {
      render: render,
      getState: function () {
        return { scope: state.scope, steps: state.steps, showFrag: state.showFrag, center: state.center };
      },
      setFocus: function (link) { state.center = link; state.stack = []; render(); },
      destroy: function () {
        tipEl().style.opacity = 0;   /* 悬停中被摘掉不会触发 mouseleave, 不手动清会留一个常驻气泡 */
        if (shell.parentNode) shell.parentNode.removeChild(shell);
      },
    };
  }

  window.MBGraph = { mount: mount, FORM_CN: FORM_CN, FORM_COLOR: FORM_COLOR, ST_TAG: ST_TAG };
})();
