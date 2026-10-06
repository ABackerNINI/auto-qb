/* auto-qb WEB UI · 详情面板 general 页签变体 03「紧凑档案(左主区 + 右 252px 元信息栏)」
 * (计划 26-10-06-0838 S2)
 *
 * 设计稿: resources/detail-panel-templates/03-general-dossier-collapsed.html(collapsed 档;
 * 收起/矮/高三档语义全部收进本变体 —— 收起 = 本变体 summary() 供给 44px 头部摘要条
 * (报告 §5 口径的基准实现: 做种中 · 进度 · 上速 · 比率 · HR 剩余 · 站点), 矮/高 = 双栏自适应滚动)。
 * 数据: 左主区 = 状态行(state/progress/availability)+ 基础/传输/时间/路径分组
 * (drawerGeneralSections() 预格式化结果); 右栏 = 归属徽章/标识(复制)/出处备注/限速配额/更多字段。
 * 动作: 打开目录/复制/磁力复制(_editDetail 按需取, BUG-9 先例口径)。渐进字段: 有则渲染、
 * 无则整行/整徽章省略。
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

  /* qB 原始 state -> 展示文案(徽章/摘要用; 与经典链 stateText 的成员视图口径独立, 只覆盖常见值) */
  const STATE_TEXT = {
    uploading: "做种中", stalledUP: "做种中", forcedUP: "强制做种",
    downloading: "下载中", stalledDL: "等待下载", forcedDL: "强制下载", metaDL: "获取元数据",
    pausedUP: "已暂停(已完成)", pausedDL: "已暂停",
    queuedUP: "排队(做种)", queuedDL: "排队(下载)",
    checkingUP: "校验中", checkingDL: "校验中", checkingResumeData: "恢复校验",
    allocating: "分配中", moving: "移动中", errored: "出错",
  };
  const SEEDING_STATES = ["uploading", "stalledUP", "forcedUP"];

  /* 视图偏好(跨重渲染与换种子保持): 分组折叠 / 右栏更多字段展开; lastSig 供跳过重建 */
  const ui = { folded: {}, extOpen: false, lastSig: "" };

  const CSS = [
    /* 双栏骨架 */
    ".drawer .dt03-wrap { display:flex; align-items:flex-start; min-height:100%; }",
    ".drawer .dt03-main { flex:1; min-width:0; padding-right:16px; }",
    ".drawer .dt03-side { flex:none; width:252px; border-left:1px solid var(--hairline); padding-left:16px; }",
    /* 状态行 */
    ".drawer .dt03-status { display:flex; align-items:center; gap:12px; padding:2px 0 4px; }",
    ".drawer .dt03-badge { display:inline-flex; align-items:center; gap:6px; height:22px; padding:0 10px;",
    "  border-radius:var(--radius-sm); background:var(--green-soft); border:1px solid var(--green-line);",
    "  color:var(--green); font-size:12px; font-weight:600; white-space:nowrap; }",
    ".drawer .dt03-badge i { width:6px; height:6px; border-radius:50%; background:currentColor; }",
    ".drawer .dt03-badge.is-dl { background:var(--blue-soft); border-color:var(--border-soft); color:var(--blue); }",
    ".drawer .dt03-badge.is-pause { background:var(--surface-1); border-color:var(--border-strong); color:var(--fg-muted); }",
    ".drawer .dt03-progress { flex:1; position:relative; height:7px; border-radius:999px; background:var(--bg-sunken);",
    "  overflow:hidden; border:1px solid var(--hairline); }",
    ".drawer .dt03-progress i { position:absolute; inset:0 auto 0 0; border-radius:999px; background:var(--green); }",
    ".drawer .dt03-pct { font-family:var(--font-mono, ui-monospace, monospace); font-size:13px; color:var(--fg);",
    "  min-width:52px; text-align:right; }",
    ".drawer .dt03-remain { font-size:11.5px; color:var(--fg-dim); white-space:nowrap; }",
    /* HR 行(单行) */
    ".drawer .dt03-hrline { display:flex; align-items:center; flex-wrap:wrap; gap:6px 8px; margin:6px 0 2px; padding:5px 10px;",
    "  border-radius:var(--radius-sm); background:var(--hr-pending-soft); border:1px solid var(--hr-pending-line);",
    "  font-size:11.5px; color:var(--fg-muted); }",
    ".drawer .dt03-hrline.is-done { background:var(--hr-done-soft); border-color:var(--hr-done-line); }",
    ".drawer .dt03-hrline.is-info { background:var(--surface-1); border-color:var(--border-soft); }",
    ".drawer .dt03-hrline b { font-family:var(--font-mono, ui-monospace, monospace); color:var(--hr-pending); font-weight:600; }",
    ".drawer .dt03-hrline.is-done b { color:var(--hr-done); }",
    /* 主区分组: 标题 + 延伸细线, 无卡片框 */
    ".drawer .dt03-sec { margin-top:8px; }",
    ".drawer .dt03-sec-h { display:flex; align-items:center; gap:8px; height:28px; cursor:pointer; user-select:none; }",
    ".drawer .dt03-sec-h b { font-size:12.5px; font-weight:600; color:var(--fg-soft); }",
    ".drawer .dt03-sec-h .dt03-cnt { font-size:11px; color:var(--fg-dim); }",
    ".drawer .dt03-sec-h .dt03-chev { color:var(--fg-dim); transition:transform var(--dur) var(--ease); }",
    ".drawer .dt03-sec-h::after { content:\"\"; flex:1; height:1px; background:var(--hairline); }",
    ".drawer .dt03-sec.folded .dt03-chev { transform:rotate(-90deg); }",
    ".drawer .dt03-sec.folded .dt03-grid, .drawer .dt03-sec.folded .dt03-wide { display:none; }",
    ".drawer .dt03-grid { display:grid; grid-template-columns:repeat(3, minmax(0, 1fr)); column-gap:16px; }",
    ".drawer .dt03-item { display:flex; align-items:baseline; justify-content:space-between; gap:8px; padding:4px 6px;",
    "  margin:0 -6px; border-radius:var(--radius-sm); min-width:0; }",
    ".drawer .dt03-item:hover { background:var(--bg-hover); }",
    ".drawer .dt03-item .k { flex:none; font-size:11.5px; color:var(--fg-dim); }",
    ".drawer .dt03-item .v { min-width:0; font-family:var(--font-mono, ui-monospace, monospace); font-size:12px; color:var(--fg);",
    "  text-align:right; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }",
    ".drawer .dt03-item .v.is-dim { color:var(--fg-dim); }",
    /* 整行项(保存路径) */
    ".drawer .dt03-wide { display:flex; flex-direction:column; gap:2px; }",
    ".drawer .dt03-item.wide { margin:0; padding:4px 6px; }",
    ".drawer .dt03-item.wide .v { display:inline-flex; align-items:center; gap:4px; max-width:100%; }",
    /* 行内动作钮 */
    ".drawer .dt03-act { flex:none; display:inline-flex; align-items:center; justify-content:center; width:22px; height:22px;",
    "  padding:0; border:0; border-radius:var(--radius-sm); background:transparent; color:var(--fg-dim); cursor:pointer;",
    "  transition:color var(--dur) var(--ease), background var(--dur) var(--ease); }",
    ".drawer .dt03-act:hover { color:var(--fg); background:var(--bg-hover); }",
    /* 右栏 */
    ".drawer .dt03-side-h { display:flex; align-items:center; gap:6px; height:28px; font-size:12.5px; font-weight:600; color:var(--fg-soft); }",
    ".drawer .dt03-side-sub { margin:10px 0 4px; font-size:11px; color:var(--fg-dim); }",
    ".drawer .dt03-chips { display:flex; flex-wrap:wrap; gap:5px; }",
    ".drawer .dt03-chip { display:inline-flex; align-items:center; height:20px; padding:0 8px; border-radius:var(--radius-sm);",
    "  border:1px solid var(--border-soft); font-size:11px; color:var(--fg-soft); }",
    ".drawer .dt03-chip.is-accent { color:var(--accent); background:var(--accent-soft); border-color:var(--accent-line); }",
    ".drawer .dt03-chip.is-blue { color:var(--blue); background:var(--blue-soft); border-color:var(--border-soft); }",
    ".drawer .dt03-chip.is-hr { color:var(--hr-pending); background:var(--hr-pending-soft); border-color:var(--hr-pending-line); }",
    ".drawer .dt03-chip.is-mono { font-family:var(--font-mono, ui-monospace, monospace); }",
    ".drawer .dt03-crow { display:flex; align-items:center; gap:6px; padding:3px 0; }",
    ".drawer .dt03-crow .k { flex:none; width:52px; font-size:11.5px; color:var(--fg-muted); }",
    ".drawer .dt03-crow .v { flex:1; min-width:0; font-family:var(--font-mono, ui-monospace, monospace); font-size:11px;",
    "  color:var(--fg-soft); overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }",
    ".drawer .dt03-kv { display:flex; align-items:baseline; justify-content:space-between; gap:10px; padding:3px 6px;",
    "  margin:0 -6px; border-radius:var(--radius-sm); }",
    ".drawer .dt03-kv:hover { background:var(--bg-hover); }",
    ".drawer .dt03-kv .k { flex:none; font-size:11.5px; color:var(--fg-muted); }",
    ".drawer .dt03-kv .v { min-width:0; font-family:var(--font-mono, ui-monospace, monospace); font-size:11.5px; color:var(--fg);",
    "  text-align:right; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }",
    ".drawer .dt03-kv .v.is-dim { color:var(--fg-dim); }",
    ".drawer .dt03-kv .v.is-hr { color:var(--hr-pending); }",
    ".drawer .dt03-kv .v.is-clamp2 { white-space:normal; display:-webkit-box; -webkit-line-clamp:2; -webkit-box-orient:vertical;",
    "  line-height:1.5; font-family:'Segoe UI', 'Microsoft YaHei', system-ui, sans-serif; font-size:11.5px;",
    "  color:var(--fg-soft); text-align:left; }",
    ".drawer .dt03-ext { margin-top:10px; border-top:1px solid var(--hairline); padding-top:6px; }",
    ".drawer .dt03-ext summary { cursor:pointer; font-size:11.5px; color:var(--fg-dim); list-style:none;",
    "  display:flex; align-items:center; gap:6px; }",
    ".drawer .dt03-ext summary:hover { color:var(--fg); }",
    ".drawer .dt03-ext[open] summary .dt03-chev { transform:rotate(180deg); }",
    /* 摘要条(收起态, 核心以 v-html 消费) */
    ".drawer .dt03-cs-st { color:var(--green); font-weight:600; }",
    ".drawer .dt03-cs-pct { font-family:var(--font-mono, ui-monospace, monospace); color:var(--fg); }",
    ".drawer .dt03-cs-up { font-family:var(--font-mono, ui-monospace, monospace); color:var(--today-up); }",
    ".drawer .dt03-cs-hr { color:var(--hr-pending); }",
    ".drawer .dt03-cs-site { font-family:var(--font-mono, ui-monospace, monospace); color:var(--accent); }",
  ].join("\n");

  const present = (v) => v !== undefined && v !== null && v !== "";
  const size = (ctx, v) => ctx.fmtSizeOrDash(v) || "—";
  const yn = (v) => (v ? "是" : "否");

  /* 经典分组行 -> 网格键值项(保留行级 open/copy 动作钮); keep 过滤列(值原样) */
  function gridRows(sec, keep) {
    return (sec ? sec.rows : []).filter((r) => !keep || keep.indexOf(r.label) >= 0).map((r) => {
      const btn = r.act === "open"
        ? T`<button type="button" class="dt03-act" data-act="open" title="打开目录"><svg class="ico ico-sm" viewBox="0 0 16 16"><use href="#i-folder-open"></use></svg></button>`
        : (r.act === "copy"
          ? T`<button type="button" class="dt03-act" data-act="copy" title="复制${r.label}"><svg class="ico ico-sm" viewBox="0 0 16 16"><use href="#i-copy"></use></svg></button>`
          : "");
      return T`<div class="dt03-item" title="${r.label}"><span class="k">${r.label}</span><span style="min-width:0; display:inline-flex; align-items:center; gap:4px; max-width:100%;"><span class="v">${r.text}</span>${btn ? R(btn) : ""}</span></div>`;
    }).join("");
  }

  function secHtml(id, title, rowsHtml, count) {
    if (!rowsHtml) return "";
    const folded = ui.folded[id] ? " folded" : "";
    return T`<section class="dt03-sec${folded}" data-sec="${id}">
      <div class="dt03-sec-h" data-fold title="点击折叠 / 展开">
        <svg class="ico ico-sm dt03-chev" viewBox="0 0 16 16"><use href="#i-chevron"></use></svg>
        <b>${title}</b><span class="dt03-cnt">${count} 项</span>
      </div>
      <div class="dt03-grid">${R(rowsHtml)}</div>
    </section>`;
  }

  /* 状态行: state 徽章 + 进度条 + 百分比 + 剩余/可用性 */
  function statusLine(ctx, d) {
    const st = STATE_TEXT[d.state] || d.state || "—";
    const tone = SEEDING_STATES.indexOf(d.state) >= 0 ? ""
      : (d.state === "downloading" || d.state === "forcedDL" || d.state === "stalledDL" || d.state === "metaDL" ? " is-dl" : " is-pause");
    const pct = ((d.progress || 0) * 100).toFixed(1);
    return T`<div class="dt03-status" title="state / progress / amount_left">
      <span class="dt03-badge${tone}"><i></i>${st}</span>
      <span class="dt03-progress"><i style="width:${pct}%"></i></span>
      <span class="dt03-pct">${pct}%</span>
      <span class="dt03-remain">剩余 ${size(ctx, d.amount_left)} · 可用性 ${(d.availability ?? 0).toFixed(2)}</span>
    </div>`;
  }

  /* HR 单行(渐进: 无 HR 字段整行省略) */
  function hrLine(ctx, d) {
    const bits = [];
    let tone = "is-info";
    if (d.hr_excluded) {
      bits.push(T`<span>已排除出 HR 管理</span>`);
      if (d.hr_safety_text) bits.push(T`<span>${d.hr_safety_text}</span>`);
    } else if (d.hr_triggered) {
      tone = d.hr_satisfied ? "is-done" : "";
      bits.push(T`<span>${d.hr_satisfied ? "HR 已触发 · 已达标" : "HR 已触发 · 未达标"}</span>`);
      if (d.hr_req_time) bits.push(T`<span>要求做种 <b>${ctx.fmtDuration(d.hr_req_time)}</b></span>`);
      if (d.hr_req_ratio > 0) bits.push(T`<span>要求分享率 <b>${Number(d.hr_req_ratio).toFixed(2)}</b></span>`);
      if (d.hr_site_lane) {
        if (d.hr_site_need !== "" && d.hr_site_need !== undefined && d.hr_site_need !== null) {
          bits.push(T`<span>站点侧还需做种 <b>${ctx.fmtDuration(d.hr_site_need)}</b></span>`);
        }
        if (d.hr_site_remain !== "" && d.hr_site_remain !== undefined && d.hr_site_remain !== null) {
          bits.push(T`<span>站点侧${d.hr_site_remain === 0 ? "已达标" : "剩余达标"} <b>${ctx.fmtDuration(d.hr_site_remain)}</b></span>`);
        }
      }
    }
    if (!bits.length) return "";
    return T`<div class="dt03-hrline ${tone}" title="${d.hr_reason || ""}">${R(bits.join(""))}</div>`;
  }

  /* 右栏标识行(带复制) */
  function crow(label, text, act, extra) {
    return T`<div class="dt03-crow" title="${label}">
      <span class="k">${label}</span><span class="v">${text}</span>
      <button type="button" class="dt03-act" data-act="${act}" title="复制${extra || label}"><svg class="ico ico-sm" viewBox="0 0 16 16"><use href="#i-copy"></use></svg></button>
    </div>`;
  }

  function sideKv(label, text, cls) {
    return T`<div class="dt03-kv" title="${label}"><span class="k">${label}</span><span class="v${cls ? " " + cls : ""}">${text}</span></div>`;
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
    if (sig === ui.lastSig && host.firstChild) return;
    ui.lastSig = sig;
    const scroller = host.parentElement;
    const scroll = scroller ? scroller.scrollTop : 0;
    const secs = {};
    for (const sec of ctx.drawerGeneralSections()) secs[sec.title] = sec;

    /* ---- 左主区: 状态行 + HR 行 + 基础/传输/时间/路径 ----
     * 各片段都是本变体 dtHtml 产出的预转义字符串, 纯 join 组合(不得混入 R 包装对象) */
    const mainHtml = [
      statusLine(ctx, d),
      hrLine(ctx, d),
      secHtml("base", "基础", gridRows(secs["基础"]), secs["基础"] ? secs["基础"].rows.length : 0),
      secHtml("xfer", "传输", gridRows(secs["传输"]), secs["传输"] ? secs["传输"].rows.length : 0),
      secHtml("time", "时间", gridRows(secs["时间"]), secs["时间"] ? secs["时间"].rows.length : 0),
      secHtml("path", "路径与开关", gridRows(secs["路径"]), secs["路径"] ? secs["路径"].rows.length : 0),
    ].join("");

    /* ---- 右栏 ---- */
    /* 归属徽章(渐进) */
    const chipsOut = [];
    if (present(d.site) && d.site !== "") chipsOut.push(T`<span class="dt03-chip is-accent is-mono" title="site">${d.site}</span>`);
    if (present(d.category) && d.category !== "") chipsOut.push(T`<span class="dt03-chip is-blue" title="category">${d.category}</span>`);
    for (const tag of String(d.tags || "").split(",")) {
      const t = tag.trim();
      if (t) chipsOut.push(T`<span class="dt03-chip is-hr" title="tags">${t}</span>`);
    }
    if (d.private) chipsOut.push(T`<span class="dt03-chip" title="private">私有站点</span>`);
    const chipsHtml = chipsOut.length
      ? T`<div class="dt03-side-sub">归属</div><div class="dt03-chips">${R(chipsOut.join(""))}</div>` : "";

    /* 标识: 哈希 v1/v2 + magnet(按需取) + 分块 */
    const idRows = [];
    for (const r of (secs["基础"] || { rows: [] }).rows) {
      if (r.act === "copy") idRows.push(crow(r.label, r.text, "copy"));
    }
    idRows.push(crow("magnet", "点击按钮按需获取", "magnet", "magnet 链接"));
    for (const r of (secs["基础"] || { rows: [] }).rows) {
      if (r.label === "分块") idRows.push(sideKv(r.label, r.text));
    }
    const idHtml = T`<div class="dt03-side-sub">标识(点击按钮复制)</div>${R(idRows.join(""))}`;

    /* 出处与备注 */
    const srcRows = [];
    for (const r of (secs["基础"] || { rows: [] }).rows) {
      if (r.label === "创建于" || r.label === "创建工具" || r.label === "已含元数据") {
        srcRows.push(sideKv(r.label, r.text));
      }
      if (r.label === "备注") srcRows.push(sideKv("备注", r.text, "is-clamp2"));
    }
    const srcHtml = srcRows.length ? T`<div class="dt03-side-sub">出处与备注</div>${R(srcRows.join(""))}` : "";

    /* 限速与配额(渐进: 缺失/负值整行省略; 0 = 不限) */
    const limRows = [];
    if (d.up_limit !== undefined && d.up_limit !== null && d.up_limit >= 0) {
      limRows.push(sideKv("上行限速", d.up_limit === 0 ? "不限" : ctx.fmtSpeed(d.up_limit), d.up_limit === 0 ? "is-dim" : "is-hr"));
    }
    if (d.dl_limit !== undefined && d.dl_limit !== null && d.dl_limit >= 0) {
      limRows.push(sideKv("下行限速", d.dl_limit === 0 ? "不限" : ctx.fmtSpeed(d.dl_limit), d.dl_limit === 0 ? "is-dim" : ""));
    }
    if (d.max_ratio !== undefined && d.max_ratio !== null && d.max_ratio >= 0) {
      limRows.push(sideKv("分享率限制", d.max_ratio.toFixed(2) + (d.share_limit_action ? " · " + d.share_limit_action : "")));
    }
    const limHtml = limRows.length ? T`<div class="dt03-side-sub">限速与配额</div>${R(limRows.join(""))}` : "";

    /* 更多字段(渐进) */
    const extRows = [];
    const st = STATE_TEXT[d.state] || d.state;
    if (st) extRows.push(sideKv("状态", st));
    if (d.priority !== undefined && d.priority !== null) extRows.push(sideKv("队列优先级", String(d.priority)));
    if (d.popularity !== undefined && d.popularity !== null) extRows.push(sideKv("热度", Number(d.popularity).toFixed(2)));
    if (d.completed !== undefined && d.completed !== null) extRows.push(sideKv("已完成量", size(ctx, d.completed)));
    if (d.has_other_announce_error !== undefined && d.has_other_announce_error !== null) {
      extRows.push(sideKv("其它汇报错误", yn(d.has_other_announce_error), d.has_other_announce_error ? "" : "is-dim"));
    }
    if (present(d.tracker) && d.tracker !== "") extRows.push(sideKv("首选 tracker", d.tracker));
    const extHtml = extRows.length
      ? T`<details class="dt03-ext"${R(ui.extOpen ? " open" : "")}>
          <summary><svg class="ico ico-sm dt03-chev" viewBox="0 0 16 16"><use href="#i-chevron"></use></svg>更多字段(扩展)</summary>
          <div style="margin-top:4px;">${R(extRows.join(""))}</div>
        </details>` : "";

    const html = T`<div class="dt03-wrap">
      <div class="dt03-main">${R(mainHtml)}</div>
      <aside class="dt03-side" title="元信息栏: site / category / tags / 标识 / 限速 / 扩展字段">
        <div class="dt03-side-h"><svg class="ico ico-sm" viewBox="0 0 16 16"><use href="#i-info"></use></svg>元信息</div>
        ${R(chipsHtml)}${R(idHtml)}${R(srcHtml)}${R(limHtml)}${R(extHtml)}
      </aside>
    </div>`;
    host.replaceChildren(document.createRange().createContextualFragment(html));
    if (scroller) scroller.scrollTop = scroll;
  }

  /* ---------------- 收起态摘要(报告 §5 口径的基准实现) ----------------
   * 做种中 · 进度 · 上速 · 比率 · HR 剩余 · 站点; 返回已转义 HTML(值全走 dtHtml) */
  function summary(ctx) {
    const d = ctx.drawer && ctx.drawer.detail;
    if (!d) return T`暂无详情`;
    const parts = [];
    const st = STATE_TEXT[d.state] || d.state || "—";
    const stCls = SEEDING_STATES.indexOf(d.state) >= 0 ? "dt03-cs-st" : "";
    parts.push(T`<span class="${stCls}">${st}</span>`);
    parts.push(T`<span class="dt03-cs-pct">${((d.progress || 0) * 100).toFixed(1)}%</span>`);
    parts.push(T`<span class="dt03-cs-up">↑ ${ctx.fmtSpeedOrDash(d.upspeed) || "—"}</span>`);
    parts.push(T`<span>比率 ${(d.ratio ?? 0).toFixed(2)}</span>`);
    if (d.hr_excluded) parts.push(T`<span>HR 已排除</span>`);
    else if (d.hr_triggered) {
      if (d.hr_satisfied) parts.push(T`<span>HR 已达标</span>`);
      else if (d.hr_site_lane && d.hr_site_remain !== "" && d.hr_site_remain !== undefined && d.hr_site_remain !== null && d.hr_site_remain > 0) {
        parts.push(T`<span class="dt03-cs-hr">HR 剩 ${ctx.fmtDuration(d.hr_site_remain)}</span>`);
      } else parts.push(T`<span class="dt03-cs-hr">HR 未达标</span>`);
    }
    if (present(d.site) && d.site !== "") parts.push(T`<span class="dt03-cs-site" title="site">${d.site}</span>`);
    return parts.join(' <span style="color:var(--fg-dim)">·</span> ');
  }

  function destroy(host) {
    ui.lastSig = ""; /* 下次挂载强制整帧重建 */
    /* 宿主元素跨变体复用(同页签只有一个 data-dt-host), 换变体必须摘掉本变体的委托监听,
     * 否则新旧变体监听叠加、同一次点击被多个 handler 重复处理 */
    if (host && host.__dt03Click) {
      host.removeEventListener("click", host.__dt03Click);
      host.__dt03Click = null;
      host.__dt03Wired = false;
    }
  }

  function onClick(ev) {
    const h = ev.currentTarget;
    const foldHead = ev.target.closest("[data-fold]");
    if (foldHead) {
      const sec = foldHead.closest("[data-sec]");
      if (sec) {
        const id = sec.getAttribute("data-sec");
        ui.folded[id] = !ui.folded[id];
        sec.classList.toggle("folded");
      }
      return;
    }
    const extSum = ev.target.closest(".dt03-ext summary");
    if (extSum) {
      const det = extSum.closest("details");
      setTimeout(() => { ui.extOpen = !!(det && det.open); }, 0);
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
    const row = btn.closest(".dt03-crow, .dt03-item");
    const text = row ? row.querySelector(".v") : null;
    const label = row ? row.querySelector(".k") : null;
    if (text) ctx.copyText(text.textContent, label ? label.textContent : "");
  }

  /* 事件委托挂宿主一次(宿主元素归 Vue 所有且跨重渲染复用) */
  function wire(host) {
    if (host.__dt03Wired) return;
    host.__dt03Wired = true;
    host.__dt03Click = onClick;
    host.addEventListener("click", onClick);
  }

  const _render = render;
  reg.register({
    id: "03", tab: "general",
    label: "紧凑档案(收起)",
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
