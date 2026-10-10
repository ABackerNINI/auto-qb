/* auto-qb WEB UI · 详情面板 general 页签变体 02「语义分区卡片(三列)」(计划 26-10-06-0838 S2)
 *
 * 设计稿: resources/detail-panel-templates/02-general-cards-low.html(low 档; 收起/矮/高三档
 * 语义全部收进本变体 —— 收起 = 核心摘要条(summary 走核心内置默认), 矮/高 = 卡片列自适应滚动)。
 * 数据: 基础/传输/时间/路径分组行直接吃 drawerGeneralSections() 预格式化结果; 卡片为纯前端
 * 聚类(基础 + 传输/标识 + 元信息/存储), 磁力复制走 _editDetail 按需取(BUG-9 先例口径:
 * magnet_uri 不进轮询载荷); 回收未展示字段(tags/category/site/限速/优先级/热度等)。
 * 字段行消费行级 icon 数据(sprite `<use href>` 静态引用, 着色复用经典链 icoTone 派生表,
 * 色值在变体 CSS 里按行类重定作用域 —— 经典的 .f-row .ico-t-* 选择器在变体行不命中;
 * 仅消费分组行自带的 icon, 卡片自建的元信息/磁力行无该数据不补; Q2, 报告 26-10-07-0542)。
 * 动作: 卡片折叠(纯前端)/打开目录/复制/磁力复制。渐进字段: 有则渲染、无则整行/整徽章省略。
 * 渲染纪律: dtHtml 全量转义(dtRaw 只用于拼接本变体 dtHtml 产出的预转义片段), replaceChildren
 * 原子换帧, 数据未变(整份 detail 序列化比对)跳过重建, 滚动位置/折叠态自保。
 * 自包含: 删除本文件 + 三份 index.html 各去 1 行 manifest 即整体退役, 其它零接触。
 */
(function () {
  "use strict";
  const reg = window.AQB_DRAWER_TPL_REG;
  if (!reg) return; /* 核心未载入(清单序错): 静默退出, 守阵会抓 */
  const T = reg.dtHtml;
  const R = reg.dtRaw;
  const H = reg.helpers; /* 公共骨架单点(报告 26-10-07-0845): 工具/sig 比对/滚动自保/事件挂摘 */

  /* qB 原始 state -> 展示文案(徽章用; 与经典链 stateText 的成员视图口径独立, 只覆盖常见值) */
  const STATE_TEXT = {
    uploading: "做种", stalledUP: "做种", forcedUP: "强制做种",
    downloading: "下载", stalledDL: "等待", forcedDL: "强制下载", metaDL: "下载元数据",
    pausedUP: "已完成", pausedDL: "暂停",
    queuedUP: "排队", queuedDL: "排队",
    checkingUP: "校验", checkingDL: "校验", checkingResumeData: "校验恢复数据",
    allocating: "分配中", moving: "移动中", errored: "错误",
  };
  const SEEDING_STATES = ["uploading", "stalledUP", "forcedUP"];

  /* 视图偏好(跨重渲染与换种子保持): 卡片折叠; lastSig 供数据未变跳过重建 */
  const ui = { folded: {}, lastSig: "" };

  const CSS = [
    ".drawer .dt02-wrap { min-width:0; }",
    ".drawer .dt02-cards { display:grid; grid-template-columns:repeat(3, minmax(0, 1fr)); gap:10px; align-items:start; }",
    ".drawer .dt02-col { display:flex; flex-direction:column; gap:10px; min-width:0; }",
    ".drawer .dt02-card { background:var(--bg-card); border:1px solid var(--border); border-radius:var(--radius-lg); overflow:hidden; }",
    ".drawer .dt02-card:hover { border-color:var(--border-strong); }",
    ".drawer .dt02-card.is-hr { border-color:var(--hr-pending-line); }",
    ".drawer .dt02-card.is-hr.is-done { border-color:var(--hr-done-line); }",
    ".drawer .dt02-card-h { display:flex; align-items:center; gap:8px; padding:8px 12px; cursor:pointer; user-select:none;",
    "  border-bottom:1px solid var(--hairline); background:var(--surface-1); }",
    ".drawer .dt02-card-h b { font-size:13px; font-weight:600; color:var(--fg-soft); }",
    ".drawer .dt02-card-h .dt02-cnt { font-size:11px; color:var(--fg-dim); }",
    ".drawer .dt02-card-h .dt02-chev { margin-left:auto; color:var(--fg-dim); transition:transform var(--dur) var(--ease); }",
    ".drawer .dt02-card.folded .dt02-chev { transform:rotate(-90deg); }",
    ".drawer .dt02-card.folded .dt02-card-b { display:none; }",
    ".drawer .dt02-card-b { padding:7px 12px 10px; }",
    /* 键值行(悬浮高亮; Q1 报告 26-10-07-0542: 标签在前值紧随, 不再 space-between 两端推开) */
    ".drawer .dt02-kv { display:flex; align-items:baseline; gap:10px; padding:4px 6px;",
    "  margin:0 -6px; border-radius:var(--radius-sm); }",
    ".drawer .dt02-kv:hover { background:var(--bg-hover); }",
    ".drawer .dt02-kv .k { flex:none; font-size:12px; color:var(--fg-muted); }",
    ".drawer .dt02-kv .v { min-width:0; font-family:var(--font-mono, ui-monospace, monospace); font-size:12px; color:var(--fg);",
    "  text-align:right; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }",
    ".drawer .dt02-kv .v.is-dim { color:var(--fg-dim); }",
    ".drawer .dt02-kv .v.is-up { color:var(--today-up); }",
    ".drawer .dt02-kv .v.is-hr { color:var(--hr-pending); }",
    /* 标识复制行 */
    ".drawer .dt02-crow { display:flex; align-items:center; gap:6px; padding:3px 0; }",
    ".drawer .dt02-crow .k { flex:none; width:58px; font-size:12px; color:var(--fg-muted); }",
    ".drawer .dt02-crow .v { flex:1; min-width:0; font-family:var(--font-mono, ui-monospace, monospace); font-size:11.5px;",
    "  color:var(--fg-soft); overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }",
    /* 徽章 */
    ".drawer .dt02-chips { display:flex; flex-wrap:wrap; gap:6px; margin:2px 0 8px; }",
    ".drawer .dt02-chip { display:inline-flex; align-items:center; height:22px; padding:0 9px;",
    "  border-radius:var(--radius-sm); border:1px solid var(--border-soft); font-size:11.5px; color:var(--fg-soft); }",
    ".drawer .dt02-chip.is-green { color:var(--green); background:var(--green-soft); border-color:var(--green-line); }",
    ".drawer .dt02-chip.is-blue { color:var(--blue); background:var(--blue-soft); border-color:var(--border-soft); }",
    ".drawer .dt02-chip.is-accent { color:var(--accent); background:var(--accent-soft); border-color:var(--accent-line); }",
    ".drawer .dt02-chip.is-hr { color:var(--hr-pending); background:var(--hr-pending-soft); border-color:var(--hr-pending-line); }",
    ".drawer .dt02-chip.is-mono { font-family:var(--font-mono, ui-monospace, monospace); }",
    /* 开关徽章(路径卡) */
    ".drawer .dt02-flags { display:flex; flex-wrap:wrap; gap:6px; margin-top:8px; }",
    ".drawer .dt02-flag { display:inline-flex; align-items:center; gap:5px; height:20px; padding:0 8px;",
    "  border-radius:var(--radius-sm); font-size:11px; border:1px solid var(--border-soft); color:var(--fg-dim);",
    "  background:var(--surface-1); }",
    ".drawer .dt02-flag.is-on { color:var(--accent); border-color:var(--accent-line); background:var(--accent-soft); }",
    ".drawer .dt02-flag i { width:5px; height:5px; border-radius:50%; background:currentColor; }",
    /* HR 卡内部 */
    ".drawer .dt02-hr-line { display:flex; align-items:center; gap:8px; margin:2px 0 8px; }",
    ".drawer .dt02-hr-badge { color:var(--hr-pending); font-weight:600; font-size:12.5px; }",
    ".drawer .dt02-card.is-done .dt02-hr-badge { color:var(--hr-done); }",
    ".drawer .dt02-hr-req { font-size:12px; color:var(--fg-muted); margin-bottom:6px; }",
    ".drawer .dt02-hr-req b { font-family:var(--font-mono, ui-monospace, monospace); color:var(--fg); }",
    ".drawer .dt02-hr-need { display:flex; align-items:baseline; gap:8px; padding:6px 8px; border-radius:var(--radius-sm);",
    "  background:var(--hr-pending-soft); border:1px solid var(--hr-pending-line); }",
    ".drawer .dt02-hr-need .k { font-size:11.5px; color:var(--fg-muted); }",
    ".drawer .dt02-hr-need .v { margin-left:auto; font-size:15px; color:var(--hr-pending); }",
    ".drawer .dt02-card.is-done .dt02-hr-need { background:var(--hr-done-soft); border-color:var(--hr-done-line); }",
    ".drawer .dt02-card.is-done .dt02-hr-need .v { color:var(--hr-done); }",
    /* 行内动作钮 */
    ".drawer .dt02-act { flex:none; display:inline-flex; align-items:center; justify-content:center;",
    "  width:22px; height:22px; padding:0; border:0; border-radius:var(--radius-sm); background:transparent;",
    "  color:var(--fg-dim); cursor:pointer; transition:color var(--dur) var(--ease), background var(--dur) var(--ease); }",
    ".drawer .dt02-act:hover { color:var(--fg); background:var(--bg-hover); }",
    /* Q2(报告 26-10-07-0542): 字段行图标 + 语义着色 —— 与经典链 .f-row .ico-t-* 同色表,
     * 色值同令牌; teal/indigo/cyan/violet/pink 未入变体令牌白名单, 按契约写字面 fallback */
    ".drawer :is(.dt02-kv, .dt02-crow) > .ico { flex:none; align-self:center; color:var(--fg-dim); }",
    ".drawer :is(.dt02-kv, .dt02-crow) .ico-t-io { color:var(--blue); }",
    ".drawer :is(.dt02-kv, .dt02-crow) .ico-t-cap { color:var(--teal, #2dd4bf); }",
    ".drawer :is(.dt02-kv, .dt02-crow) .ico-t-time { color:var(--indigo, #818cf8); }",
    ".drawer :is(.dt02-kv, .dt02-crow) .ico-t-site { color:var(--cyan, #22d3ee); }",
    ".drawer :is(.dt02-kv, .dt02-crow) .ico-t-sw { color:var(--green); }",
    ".drawer :is(.dt02-kv, .dt02-crow) .ico-t-id { color:var(--violet, #a78bfa); }",
    ".drawer :is(.dt02-kv, .dt02-crow) .ico-t-path { color:var(--accent-hi); }",
    ".drawer :is(.dt02-kv, .dt02-crow) .ico-t-state { color:var(--pink, #f472b6); }",
  ].join("\n");

  const { present, size } = H; /* 公共格式化小工具(核心层单点) */

  /* Q2(报告 26-10-07-0542): 字段行图标着色 —— 派生表自经典链 icoTone(drawer.js FX-22)自包含
   * 复制(变体不经 Vue, ctx 白名单无 icoTone); 图标名 -> 色调类, 行内 svg 挂类, 色值在上方
   * 变体 CSS 的 .ico-t-* 规则里走主题令牌。 */
  const ICO_TONE = {
    "#i-download": "ico-t-io", "#i-upload": "ico-t-io", "#i-arrow-up": "ico-t-io", "#i-arrow-down": "ico-t-io",
    "#i-hdd": "ico-t-cap", "#i-layers": "ico-t-cap", "#i-columns": "ico-t-cap",
    "#i-calendar": "ico-t-time", "#i-clock": "ico-t-time", "#i-timer": "ico-t-time",
    "#i-hourglass": "ico-t-time", "#i-eye": "ico-t-time",
    "#i-globe": "ico-t-site", "#i-link": "ico-t-site",
    "#i-lock": "ico-t-sw", "#i-sliders": "ico-t-sw", "#i-play": "ico-t-sw", "#i-sort": "ico-t-sw",
    "#i-bolt": "ico-t-sw", "#i-settings": "ico-t-sw", "#i-refresh": "ico-t-sw",
    "#i-hash": "ico-t-id", "#i-info": "ico-t-id", "#i-tag": "ico-t-id", "#i-list": "ico-t-id",
    "#i-folder": "ico-t-path", "#i-folder-open": "ico-t-path",
    "#i-percent": "ico-t-state", "#i-pulse": "ico-t-state", "#i-check-circle": "ico-t-state",
    "#i-x-circle": "ico-t-state", "#i-warn": "ico-t-state",
  };
  const icoTone = (icon) => ICO_TONE[icon] || "";

  /* 字段行图标(sprite `<use href>` 静态引用 —— 变体是字符串拼 HTML 不走 Vue 绑定,
   * href 直接写 r.icon 同经典链 drawer.html 的静态引用形态, 三皮肤 index.html 的
   * sprite symbol 集合一致, 同文档引用恒可解析)。
   * 返回 R(dtHtml(...)): 本函数产出的是本变体 dtHtml 已转义好的片段, 调用处在外层
   * dtHtml 模板里直接插值, 必须 dtRaw 豁免 —— 否则整个 svg 片段被再次转义成可见文本。 */
  function icoSvg(icon) {
    const tone = icoTone(icon);
    return R(T`<svg class="ico ico-sm${tone ? " " + tone : ""}" viewBox="0 0 16 16"><use href="${icon}"></use></svg>`);
  }

  /* 限速展示: >0 = 限速值(fmtSpeed), 0 = 不限, 负/缺失 = 整行省略(渐进) */
  function limitRow(ctx, label, v) {
    if (v === undefined || v === null || v < 0) return "";
    const txt = v === 0 ? "不限" : ctx.fmtSpeed(v);
    return T`<div class="dt02-kv" title="${label === "上传限制" ? "up_limit" : "dl_limit"}"><span class="k">${label}</span><span class="v${v === 0 ? " is-dim" : ""}">${txt}</span></div>`;
  }

  function kv(label, text, dim, icon) {
    return T`<div class="dt02-kv">${icon ? icoSvg(icon) : ""}<span class="k">${label}</span><span class="v${dim ? " is-dim" : ""}">${text}</span></div>`;
  }

  /* 卡片头(折叠态由 ui.folded 恢复) */
  function card(id, title, cnt, body, hrTone) {
    const folded = ui.folded[id] ? " folded" : "";
    const tone = hrTone ? " " + hrTone : "";
    return T`<section class="dt02-card${folded}${tone}" data-card="${id}">
      <!-- P3-4(报告 26-10-07-0542): 折叠卡头纯 div 模拟控件补键盘达(role=button + tabindex + aria-expanded) -->
      <div class="dt02-card-h" role="button" tabindex="0" aria-expanded="${folded ? "false" : "true"}"
           data-fold title="点击折叠 / 展开">
        <b>${title}</b><span class="dt02-cnt">${cnt}</span>
        <svg class="ico ico-sm dt02-chev" viewBox="0 0 16 16"><use href="#i-chevron"></use></svg>
      </div>
      <div class="dt02-card-b">${R(body)}</div>
    </section>`;
  }

  /* 经典分组行 -> 键值行(保留行级 open/copy 动作钮) */
  function secRows(sec, skip) {
    return sec.rows.filter((r) => !skip || skip.indexOf(r.label) < 0).map((r) => {
      const btn = r.act === "open"
        ? T`<button type="button" class="dt02-act" data-act="open" title="打开目录"><svg class="ico ico-sm" viewBox="0 0 16 16"><use href="#i-folder-open"></use></svg></button>`
        : (r.act === "copy"
          ? T`<button type="button" class="dt02-act" data-act="copy" title="复制${r.label}"><svg class="ico ico-sm" viewBox="0 0 16 16"><use href="#i-copy"></use></svg></button>`
          : "");
      return T`<div class="dt02-kv">${r.icon ? icoSvg(r.icon) : ""}<span class="k">${r.label}</span><span style="min-width:0; display:inline-flex; align-items:center; gap:4px; max-width:100%;"><span class="v" style="text-align:right;">${r.text}</span>${btn ? R(btn) : ""}</span></div>`;
    }).join("");
  }

  /* HR 卡体(渐进: detail 无 HR 字段整卡省略) */
  function hrBody(ctx, d) {
    let tone = "";
    const bits = [];
    if (d.hr_excluded) {
      bits.push(T`<div class="dt02-hr-line"><span class="dt02-hr-badge">已排除出 HR 管理</span></div>`);
      if (d.hr_safety_text) bits.push(T`<div class="dt02-hr-req">${d.hr_safety_text}</div>`);
    } else if (d.hr_triggered) {
      tone = d.hr_satisfied ? "is-done" : "is-hr";
      bits.push(T`<div class="dt02-hr-line"><span class="dt02-hr-badge">${d.hr_satisfied ? "已触发 · 已达标" : "已触发 · 未达标"}</span></div>`);
      const req = [];
      if (d.hr_req_ratio > 0) req.push("要求分享率 " + Number(d.hr_req_ratio).toFixed(2));
      if (d.hr_req_time) req.push("要求做种 " + ctx.fmtDuration(d.hr_req_time));
      if (d.hr_state) req.push((d.hr_safety_text || d.hr_state_text || "") + (d.hr_reason ? " · " + d.hr_reason : ""));
      if (req.length) bits.push(T`<div class="dt02-hr-req">${req.join(" · ")}</div>`);
      if (d.hr_site_lane) {
        if (d.hr_site_need !== "" && d.hr_site_need !== undefined && d.hr_site_need !== null) {
          bits.push(T`<div class="dt02-hr-need" title="hr_site_need"><span class="k">站点侧还需做种</span><span class="v">${ctx.fmtDuration(d.hr_site_need)}</span></div>`);
        }
        if (d.hr_site_remain !== "" && d.hr_site_remain !== undefined && d.hr_site_remain !== null) {
          bits.push(T`<div class="dt02-hr-need" title="hr_site_remain"><span class="k">${d.hr_site_remain === 0 ? "站点侧已达标" : "站点侧剩余达标"}</span><span class="v">${ctx.fmtDuration(d.hr_site_remain)}</span></div>`);
        }
      }
    }
    if (!bits.length) return { tone: "", html: "" };
    return { tone, html: bits.join("") };
  }

  function render(host, ctx) {
    const d = ctx.drawer && ctx.drawer.detail;
    if (!d) {
      host.replaceChildren();
      ui.lastSig = "";
      return;
    }
    /* 数据未变跳过重建(序列化比对比浅比较更强, 开销可忽略) */
    const sig = JSON.stringify(d);
    if (H.skipUnchanged(host, ui, sig)) return;
    const secs = {};
    for (const sec of ctx.drawerGeneralSections()) secs[sec.title] = sec;

    /* 徽章: state/site/category/tags/private(渐进) */
    const chipsOut = [];
    const st = STATE_TEXT[d.state] || d.state || "";
    if (st) {
      const cls = SEEDING_STATES.indexOf(d.state) >= 0 ? " is-green" : (d.state === "downloading" || d.state === "forcedDL" ? " is-blue" : "");
      chipsOut.push(T`<span class="dt02-chip${cls}" title="state">${st}</span>`);
    }
    if (present(d.site) && d.site !== "") chipsOut.push(T`<span class="dt02-chip is-accent is-mono" title="site">${d.site}</span>`);
    if (present(d.category) && d.category !== "") chipsOut.push(T`<span class="dt02-chip is-blue" title="category">${d.category}</span>`);
    for (const tag of String(d.tags || "").split(",")) {
      const t = tag.trim();
      if (t) chipsOut.push(T`<span class="dt02-chip is-hr" title="tags">${t}</span>`);
    }
    if (d.private) chipsOut.push(T`<span class="dt02-chip" title="private">私有站点</span>`);
    const chipsHtml = chipsOut.length ? T`<div class="dt02-chips">${R(chipsOut.join(""))}</div>` : "";

    /* 标识卡: 哈希 v1/v2(带复制)+ 分块 + magnet(点击按需取, BUG-9 口径) */
    const idRows = [];
    for (const r of (secs["基础"] || { rows: [] }).rows) {
      if (r.act === "copy") idRows.push(T`<div class="dt02-crow">${r.icon ? icoSvg(r.icon) : ""}<span class="k">${r.label}</span><span class="v">${r.text}</span><button type="button" class="dt02-act" data-act="copy" title="复制${r.label}"><svg class="ico ico-sm" viewBox="0 0 16 16"><use href="#i-copy"></use></svg></button></div>`);
    }
    for (const r of (secs["基础"] || { rows: [] }).rows) {
      if (r.label === "区块") idRows.push(kv(r.label, r.text, false, r.icon));
    }
    idRows.push(T`<div class="dt02-crow" title="magnet_uri"><span class="k">magnet</span><span class="v">点击按钮按需获取(不进轮询载荷)</span><button type="button" class="dt02-act" data-act="magnet" title="复制 magnet 链接"><svg class="ico ico-sm" viewBox="0 0 16 16"><use href="#i-copy"></use></svg></button></div>`);

    /* 元信息卡: 徽章 + 回收字段(tracker/优先级/热度/已完成量/限速/其它汇报错误) */
    const metaRows = [];
    if (present(d.tracker) && d.tracker !== "") metaRows.push(kv("首选 Tracker", d.tracker, false));
    if (d.priority !== undefined && d.priority !== null) metaRows.push(kv("队列优先级", String(d.priority), false));
    if (d.popularity !== undefined && d.popularity !== null) metaRows.push(kv("热度", Number(d.popularity).toFixed(2), false));
    if (d.completed !== undefined && d.completed !== null) metaRows.push(kv("已完成量", size(ctx, d.completed), false));
    metaRows.push(limitRow(ctx, "上传限制", d.up_limit));
    metaRows.push(limitRow(ctx, "下载限制", d.dl_limit));
    if (d.has_other_announce_error !== undefined && d.has_other_announce_error !== null) {
      metaRows.push(kv("其它汇报错误", d.has_other_announce_error ? "有" : "无", !d.has_other_announce_error));
    }
    const metaBody = chipsHtml + metaRows.join("");

    /* 存储与行为卡: 路径分组行(带打开目录)+ 开关徽章 */
    const flags = [
      ["自动管理", d.auto_tmm], ["强制启动", d.force_start], ["超级做种", d.super_seeding],
      ["按顺序下载", d.seq_dl], ["先下载首尾文件块", d.f_l_piece_prio],
    ].map(([label, on]) => T`<span class="dt02-flag${on ? " is-on" : ""}" title="${label}"><i></i>${label}</span>`).join("");
    const storeBody = secRows(secs["路径"] || { rows: [] }) + (T`<div class="dt02-flags">${R(flags)}</div>`);

    const hr = hrBody(ctx, d);
    const cols = [
      [
        hr.html ? card("hr", "做种要求 (HR)", "HR", hr.html, hr.tone) : "",
        secs["基础"] ? card("base", "基础", secs["基础"].rows.length + " 项", secRows(secs["基础"], ["信息哈希值 v1", "信息哈希值 v2", "区块"])) : "",
        secs["时间"] ? card("time", "时间", secs["时间"].rows.length + " 项", secRows(secs["时间"])) : "",
      ],
      [
        secs["传输"] ? card("xfer", "传输", secs["传输"].rows.length + " 项", secRows(secs["传输"])) : "",
        idRows.length ? card("id", "标识", idRows.length + " 项", idRows.join("")) : "",
      ],
      [
        metaBody ? card("meta", "元信息", "", metaBody) : "",
        (secs["路径"] || flags) ? card("store", "存储与行为", (secs["路径"] || { rows: [] }).rows.length + " 项", storeBody) : "",
      ],
    ];
    const html = T`<div class="dt02-wrap"><div class="dt02-cards">${R(cols.map((col) => T`<div class="dt02-col">${R(col.join(""))}</div>`).join(""))}</div></div>`;
    /* 滚动位置自保(纵横成对): 滚动容器是宿主父级(.drawer-body, Vue 所有) —— 单点 helper */
    H.withScroll(host, () => {
      host.replaceChildren(document.createRange().createContextualFragment(html));
    });
  }

  /* 收起态摘要: 走核心内置默认实现(状态·进度·速度·比率·HR), 本变体不覆写 */

  function destroy(host) {
    ui.lastSig = ""; /* 下次挂载强制整帧重建 */
    /* 宿主元素跨变体复用(同页签只有一个 data-dt-host), 换变体必须摘掉本变体的委托监听,
     * 否则新旧变体监听叠加、同一次点击被多个 handler 重复处理 */
    H.unwireEvents(host);
  }

  /* P3-4: 折叠卡头纯 div 模拟控件(data-fold)的键盘触发 —— Enter/Space 转发 click 委托;
   * 焦点在原生 button 等自身会发 click 的元素上时不接管(防 Enter 双重触发) */
  function onKeyDown(ev) {
    if (ev.key !== "Enter" && ev.key !== " ") return;
    if (ev.target.closest("button, input, select, textarea, a[href], summary")) return;
    if (!ev.target.closest("[data-fold]")) return;
    ev.preventDefault();
    onClick(ev);
  }

  function onClick(ev) {
    const h = ev.currentTarget;
    const foldHead = ev.target.closest("[data-fold]");
    if (foldHead) {
      const cardEl = foldHead.closest("[data-card]");
      if (cardEl) {
        const id = cardEl.getAttribute("data-card");
        ui.folded[id] = !ui.folded[id];
        cardEl.classList.toggle("folded");
      }
      return;
    }
    const btn = ev.target.closest("[data-act]");
    if (!btn) return;
    const ctx = h.__dtCtx;
    const act = btn.getAttribute("data-act");
    if (act === "open") {
      ctx.openTargetPath("torrent", ctx.drawer.hash);
      return;
    }
    if (act === "magnet") {
      /* 磁力按需取(BUG-9 先例口径): _editDetail 在抽屉已开时直接复用 detail, 连请求都不发 */
      ctx._editDetail(ctx.drawer.hash).then((dd) => {
        if (dd && dd.magnet_uri) ctx.copyText(dd.magnet_uri, " magnet 链接");
      });
      return;
    }
    const row = btn.closest(".dt02-crow, .dt02-kv");
    const text = row ? row.querySelector(".v") : null;
    const label = row ? row.querySelector(".k") : null;
    if (text) ctx.copyText(text.textContent, label ? label.textContent : "");
  }

  /* 事件委托挂宿主一次(宿主元素归 Vue 所有且跨重渲染复用; 挂摘成对纪律在核心 helper) */
  function wire(host) {
    H.wireEvents(host, { click: onClick, keydown: onKeyDown });
  }

  const _render = render;
  reg.register({
    id: "02", tab: "general",
    label: "六卡聚类",
    css: CSS,
    render(host, ctx) {
      wire(host);
      host.__dtCtx = ctx;
      _render(host, ctx);
    },
    destroy,
  });
})();
