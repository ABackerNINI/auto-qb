/* auto-qb WEB UI · 详情面板 general 页签变体 01「英雄行 + 4 列键值栅格」(计划 26-10-06-0838 S2)
 *
 * 设计稿: resources/detail-panel-templates/01-general-hero-tall.html(tall 档; 收起/矮/高三档
 * 语义全部收进本变体 —— 收起 = 核心摘要条(summary 走核心内置默认), 矮/高 = 正文自适应滚动)。
 * 数据: 英雄行五数字 = progress / ratio / upspeed / num_seeds / reannounce_in; 下方分组键值
 * 栅格直接吃 drawerGeneralSections() 预格式化结果(qB 哨兵翻译单点在经典链, 不复刻)。
 * 动作: 打开目录(openTargetPath)/复制(copyText), 经典行级 act 平移; 分组折叠为纯前端态。
 * 渐进字段(state/site/category/tags/private 徽章): detail 有则渲染、无则整枚省略。
 * 渲染纪律: dtHtml 全量转义(dtRaw 只用于拼接本变体 dtHtml 产出的预转义片段), replaceChildren
 * 原子换帧, 数据未变(整份 detail 序列化比对)跳过重建, 滚动位置/折叠态/原始键值展开态自保。
 * 自包含: 删除本文件 + 三份 index.html 各去 1 行 manifest 即整体退役, 其它零接触。
 */
(function () {
  "use strict";
  const reg = window.AQB_DRAWER_TPL_REG;
  if (!reg) return; /* 核心未载入(清单序错): 静默退出, 守阵会抓 */
  const T = reg.dtHtml;
  const R = reg.dtRaw;

  /* qB 原始 state -> 展示文案(徽章用; 与经典链 stateText 的成员视图口径独立, 只覆盖常见值) */
  const STATE_TEXT = {
    uploading: "做种中", stalledUP: "做种中", forcedUP: "强制做种",
    downloading: "下载中", stalledDL: "等待下载", forcedDL: "强制下载", metaDL: "获取元数据",
    pausedUP: "已暂停(已完成)", pausedDL: "已暂停",
    queuedUP: "排队(做种)", queuedDL: "排队(下载)",
    checkingUP: "校验中", checkingDL: "校验中", checkingResumeData: "恢复校验",
    allocating: "分配中", moving: "移动中", errored: "出错",
  };
  const SEEDING_STATES = ["uploading", "stalledUP", "forcedUP"];

  /* 视图偏好(跨重渲染与换种子保持): 分组折叠 / 原始键值展开; lastSig 供数据未变跳过重建 */
  const ui = { folded: {}, rawOpen: false, lastSig: "" };

  const CSS = [
    /* 英雄行 */
    ".drawer .dt01-wrap { display:flex; flex-direction:column; gap:12px; min-width:0; }",
    ".drawer .dt01-hero { display:flex; align-items:stretch; padding:12px 16px 13px;",
    "  background:var(--bg-sunken); border:1px solid var(--border); border-radius:var(--radius-lg); }",
    ".drawer .dt01-hero > div { flex:1 1 0; min-width:0; padding:0 16px; border-left:1px solid var(--hairline);",
    "  display:flex; flex-direction:column; gap:3px; }",
    ".drawer .dt01-hero > div:first-child { border-left:0; padding-left:0; }",
    ".drawer .dt01-k { font-size:12px; color:var(--fg-muted); }",
    ".drawer .dt01-v { font-size:27px; line-height:1.12; color:var(--fg); }",
    ".drawer .dt01-v .u { font-size:14px; color:var(--fg-muted); margin-left:2px; }",
    ".drawer .dt01-v.is-up { color:var(--today-up); }",
    ".drawer .dt01-v.is-green { color:var(--green); }",
    ".drawer .dt01-s { font-size:11.5px; color:var(--fg-dim); overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }",
    ".drawer .dt01-bar { position:relative; height:7px; margin-top:5px; border-radius:999px; background:var(--bg-sunken);",
    "  overflow:hidden; border:1px solid var(--hairline); }",
    ".drawer .dt01-bar i { position:absolute; inset:0 auto 0 0; border-radius:999px; background:var(--green); }",
    /* 徽章行 */
    ".drawer .dt01-chips { display:flex; flex-wrap:wrap; gap:6px; }",
    ".drawer .dt01-chip { display:inline-flex; align-items:center; height:22px; padding:0 9px;",
    "  border-radius:var(--radius-sm); border:1px solid var(--border-soft); font-size:11.5px; color:var(--fg-soft); }",
    ".drawer .dt01-chip.is-green { color:var(--green); background:var(--green-soft); border-color:var(--green-line); }",
    ".drawer .dt01-chip.is-blue { color:var(--blue); background:var(--blue-soft); border-color:var(--border-soft); }",
    ".drawer .dt01-chip.is-accent { color:var(--accent); background:var(--accent-soft); border-color:var(--accent-line); }",
    ".drawer .dt01-chip.is-hr { color:var(--hr-pending); background:var(--hr-pending-soft); border-color:var(--hr-pending-line); }",
    ".drawer .dt01-chip.is-mono { font-family:var(--font-mono, ui-monospace, monospace); }",
    /* HR 摘要条 */
    ".drawer .dt01-hr { display:flex; align-items:center; flex-wrap:wrap; gap:6px 10px; padding:7px 12px;",
    "  border-radius:var(--radius); font-size:12px; color:var(--fg-muted); }",
    ".drawer .dt01-hr.is-pending { background:var(--hr-pending-soft); border:1px solid var(--hr-pending-line); }",
    ".drawer .dt01-hr.is-done { background:var(--hr-done-soft); border:1px solid var(--hr-done-line); }",
    ".drawer .dt01-hr.is-info { background:var(--surface-1); border:1px solid var(--border-soft); }",
    ".drawer .dt01-hr b { font-family:var(--font-mono, ui-monospace, monospace); font-weight:600; }",
    ".drawer .dt01-hr.is-pending b, .drawer .dt01-hr.is-pending .dt01-hr-badge { color:var(--hr-pending); }",
    ".drawer .dt01-hr.is-done b, .drawer .dt01-hr.is-done .dt01-hr-badge { color:var(--hr-done); }",
    ".drawer .dt01-hr-badge { font-weight:600; white-space:nowrap; }",
    /* 分组键值栅格 */
    ".drawer .dt01-sec-h { display:flex; align-items:center; gap:8px; height:28px; cursor:pointer;",
    "  user-select:none; color:var(--fg-muted); }",
    ".drawer .dt01-sec-h:hover { color:var(--fg-soft); }",
    ".drawer .dt01-sec-h b { font-size:13px; font-weight:600; color:var(--fg-soft); }",
    ".drawer .dt01-chev { transition:transform var(--dur) var(--ease); }",
    ".drawer .dt01-sec.folded .dt01-chev { transform:rotate(-90deg); }",
    ".drawer .dt01-sec.folded .dt01-grid, .drawer .dt01-sec.folded .dt01-sec-h .dt01-sum { display:none; }",
    ".drawer .dt01-cnt { font-size:11px; color:var(--fg-dim); }",
    ".drawer .dt01-sum { margin-left:auto; font-size:11.5px; color:var(--fg-dim); overflow:hidden;",
    "  text-overflow:ellipsis; white-space:nowrap; }",
    ".drawer .dt01-grid { display:grid; grid-template-columns:repeat(4, minmax(0, 1fr)); gap:1px;",
    "  background:var(--hairline); border:1px solid var(--hairline); border-radius:var(--radius); overflow:hidden; }",
    ".drawer .dt01-cell { min-width:0; display:flex; align-items:baseline; justify-content:space-between; gap:8px;",
    "  padding:7px 10px; background:var(--bg-card); }",
    ".drawer .dt01-cell:hover { background:var(--bg-hover); }",
    ".drawer .dt01-cell.is-wide { grid-column:span 2; }",
    ".drawer .dt01-cell .dt01-k { flex:none; }",
    ".drawer .dt01-v-cell { min-width:0; display:inline-flex; align-items:center; gap:4px; max-width:100%; }",
    ".drawer .dt01-vv { min-width:0; font-family:var(--font-mono, ui-monospace, monospace); font-size:12px;",
    "  color:var(--fg); text-align:right; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }",
    /* 行内动作钮(打开目录/复制) */
    ".drawer .dt01-act { flex:none; display:inline-flex; align-items:center; justify-content:center;",
    "  width:22px; height:22px; padding:0; border:0; border-radius:var(--radius-sm); background:transparent;",
    "  color:var(--fg-dim); cursor:pointer; transition:color var(--dur) var(--ease), background var(--dur) var(--ease); }",
    ".drawer .dt01-act:hover { color:var(--fg); background:var(--bg-hover); }",
    /* 原始键值折叠 */
    ".drawer .dt01-raw { border:1px solid var(--hairline); border-radius:var(--radius); }",
    ".drawer .dt01-raw summary { cursor:pointer; padding:8px 12px; font-size:12px; color:var(--fg-muted);",
    "  border-radius:var(--radius); list-style:none; }",
    ".drawer .dt01-raw summary:hover { color:var(--fg); background:var(--surface-1); }",
    ".drawer .dt01-rawgrid { display:grid; grid-template-columns:210px minmax(0, 1fr); gap:3px 14px;",
    "  padding:4px 14px 12px; margin:0; font-family:var(--font-mono, ui-monospace, monospace); font-size:11.5px; }",
    ".drawer .dt01-rawgrid dt { color:var(--fg-dim); }",
    ".drawer .dt01-rawgrid dd { margin:0; color:var(--fg-soft); word-break:break-all; }",
  ].join("\n");

  const dur = (ctx, v, dash) => (v === null || v === undefined || v < 0) ? (dash || "未设") : ctx.fmtDuration(v);
  const size = (ctx, v) => ctx.fmtSizeOrDash(v) || "—";
  const present = (v) => v !== undefined && v !== null && v !== "";

  /* HR 摘要条(渐进: detail 无 HR 字段整条省略); 色调 未达标=pending / 达标=done / 其它=info */
  function hrStrip(ctx, d) {
    const bits = [];
    let tone = "is-info";
    if (d.hr_excluded) {
      bits.push(T`<span class="dt01-hr-badge">已排除出 HR 管理</span>`);
      if (d.hr_safety_text) bits.push(T`<span>${d.hr_safety_text}</span>`);
    } else if (d.hr_triggered) {
      tone = d.hr_satisfied ? "is-done" : "is-pending";
      bits.push(T`<span class="dt01-hr-badge">${d.hr_satisfied ? "H&R 已达标" : "H&R 未达标"}</span>`);
      if (d.hr_req_time) bits.push(T`<span>要求做种 <b>${ctx.fmtDuration(d.hr_req_time)}</b></span>`);
      if (d.hr_req_ratio > 0) bits.push(T`<span>要求分享率 <b>${Number(d.hr_req_ratio).toFixed(2)}</b></span>`);
      if (d.hr_state) {
        const line = (d.hr_safety_text || d.hr_state_text || "") + (d.hr_reason ? " · " + d.hr_reason : "");
        if (line) bits.push(T`<span>${line}</span>`);
      }
      if (d.hr_site_lane) {
        if (d.hr_site_need !== "" && d.hr_site_need !== undefined && d.hr_site_need !== null) {
          bits.push(T`<span>站点侧还需做种 <b>${ctx.fmtDuration(d.hr_site_need)}</b></span>`);
        }
        if (d.hr_site_remain !== "" && d.hr_site_remain !== undefined && d.hr_site_remain !== null) {
          bits.push(T`<span>站点侧 ${d.hr_site_remain === 0 ? "已达标" : "剩余达标"} <b>${ctx.fmtDuration(d.hr_site_remain)}</b></span>`);
        }
      }
    }
    if (d.hr_tag) bits.push(T`<span class="dt01-chip is-hr">${d.hr_tag}</span>`);
    if (d.hr_tag_done) bits.push(T`<span class="dt01-chip is-hr">${d.hr_tag_done}</span>`);
    if (!bits.length) return "";
    return T`<div class="dt01-hr ${tone}" title="${d.hr_reason || ""}">${R(bits.join(""))}</div>`;
  }

  /* 英雄行五数字: progress / ratio / upspeed / num_seeds / reannounce_in */
  function hero(ctx, d) {
    const pct = ((d.progress || 0) * 100).toFixed(1);
    const up = ctx.fmtSpeedOrDash(d.upspeed) || "—";
    return T`<div class="dt01-hero">
      <div title="progress / amount_left / availability">
        <span class="dt01-k">进度</span>
        <span class="dt01-v is-green">${pct}<span class="u">%</span></span>
        <span class="dt01-bar"><i style="width:${pct}%"></i></span>
        <span class="dt01-s">剩余 ${size(ctx, d.amount_left)} · 可用性 ${(d.availability ?? 0).toFixed(2)}</span>
      </div>
      <div title="ratio / uploaded / downloaded">
        <span class="dt01-k">分享率</span>
        <span class="dt01-v">${(d.ratio ?? 0).toFixed(2)}</span>
        <span class="dt01-s">上传 ${size(ctx, d.uploaded)} · 下载 ${size(ctx, d.downloaded)}</span>
      </div>
      <div title="upspeed / dlspeed">
        <span class="dt01-k">上行速度</span>
        <span class="dt01-v is-up">${up}</span>
        <span class="dt01-s">下行 ${ctx.fmtSpeedOrDash(d.dlspeed) || "—"}</span>
      </div>
      <div title="num_seeds(num_complete) / num_leechs(num_incomplete)">
        <span class="dt01-k">做种 / 用户</span>
        <span class="dt01-v">${d.num_seeds ?? 0}<span class="u">/ ${d.num_leechs ?? 0}</span></span>
        <span class="dt01-s">swarm ${d.num_seeds ?? 0}(${d.num_complete ?? 0}) · 连接 ${d.connections_count ?? 0} / ${d.connections_limit ?? 0}</span>
      </div>
      <div title="reannounce_in / trackers_count">
        <span class="dt01-k">下次汇报</span>
        <span class="dt01-v">${dur(ctx, d.reannounce_in || d.reannounce, "—")}</span>
        <span class="dt01-s">tracker ${d.trackers_count ?? 0} 个</span>
      </div>
    </div>`;
  }

  /* 徽章行(渐进字段: 有则渲染、无则整枚省略) */
  function chips(d) {
    const out = [];
    const st = STATE_TEXT[d.state] || d.state || "";
    if (st) {
      const cls = SEEDING_STATES.indexOf(d.state) >= 0 ? " is-green" : (d.state === "downloading" || d.state === "forcedDL" ? " is-blue" : "");
      out.push(T`<span class="dt01-chip${cls}" title="state">${st}</span>`);
    }
    if (present(d.site)) out.push(T`<span class="dt01-chip is-accent is-mono" title="site">${d.site}</span>`);
    if (present(d.category) && d.category !== "") out.push(T`<span class="dt01-chip is-blue" title="category">${d.category}</span>`);
    for (const tag of String(d.tags || "").split(",")) {
      const t = tag.trim();
      if (t) out.push(T`<span class="dt01-chip" title="tags">${t}</span>`);
    }
    if (d.private) out.push(T`<span class="dt01-chip" title="private">私有站点</span>`);
    if (!out.length) return "";
    return T`<div class="dt01-chips">${R(out.join(""))}</div>`;
  }

  /* 行内动作钮(经典行级 act 平移: open=打开目录, copy=复制) */
  function actBtn(r) {
    if (r.act === "open") return T`<button type="button" class="dt01-act" data-act="open" title="打开目录"><svg class="ico ico-sm" viewBox="0 0 16 16"><use href="#i-folder-open"></use></svg></button>`;
    if (r.act === "copy") return T`<button type="button" class="dt01-act" data-act="copy" title="复制${r.label}"><svg class="ico ico-sm" viewBox="0 0 16 16"><use href="#i-copy"></use></svg></button>`;
    return "";
  }

  function cell(r) {
    const cls = "dt01-cell" + (r.wide ? " is-wide" : "");
    const btn = actBtn(r);
    return T`<div class="${cls}" title="${r.label}"><span class="dt01-k">${r.label}</span><span class="dt01-v-cell"><span class="dt01-vv">${r.text}</span>${btn ? R(btn) : ""}</span></div>`;
  }

  function secHtml(sec) {
    const folded = ui.folded[sec.title] ? " folded" : "";
    return T`<section class="dt01-sec${folded}" data-sec="${sec.title}">
      <div class="dt01-sec-h" data-fold title="点击折叠 / 展开">
        <svg class="ico ico-sm dt01-chev" viewBox="0 0 16 16"><use href="#i-chevron"></use></svg>
        <b>${sec.title}</b><span class="dt01-cnt">${sec.rows.length} 项</span>
        ${sec.sum ? R(T`<span class="dt01-sum">${sec.sum}</span>`) : ""}
      </div>
      <div class="dt01-grid">${R(sec.rows.map(cell).join(""))}</div>
    </section>`;
  }

  /* 全部原始键值(与经典折叠区同内容): 哨兵值原样透出, 只做转义 */
  function rawHtml(d) {
    const rows = Object.keys(d).map((k) => {
      const v = typeof d[k] === "object" && d[k] !== null ? JSON.stringify(d[k]) : d[k];
      return T`<dt>${k}</dt><dd>${v}</dd>`;
    }).join("");
    const open = ui.rawOpen ? " open" : "";
    return T`<details class="dt01-raw"${R(open)}>
      <summary class="dt01-rawsum">全部字段(原始键值, 与 qB API 字段名一致)</summary>
      <dl class="dt01-rawgrid">${R(rows)}</dl>
    </details>`;
  }

  function render(host, ctx) {
    const d = ctx.drawer && ctx.drawer.detail;
    if (!d) {
      host.replaceChildren();
      ui.lastSig = "";
      return;
    }
    /* 数据未变跳过重建(5s 通知频度下不闪不丢态); 序列化比对比浅比较更强, 开销可忽略 */
    const sig = JSON.stringify(d);
    if (sig === ui.lastSig && host.firstChild) return;
    ui.lastSig = sig;
    /* 滚动位置自保: 滚动容器是宿主父级(.drawer-body, Vue 所有) —— 只读写 scrollTop 不碰结构 */
    const scroller = host.parentElement;
    const scroll = scroller ? scroller.scrollTop : 0;
    const wrap = T`<div class="dt01-wrap">${R(hrStrip(ctx, d))}${R(hero(ctx, d))}${R(chips(d))}${R(ctx.drawerGeneralSections().map(secHtml).join(""))}${R(rawHtml(d))}</div>`;
    host.replaceChildren(document.createRange().createContextualFragment(wrap));
    if (scroller) scroller.scrollTop = scroll;
  }

  /* 收起态摘要: 走核心内置默认实现(状态·进度·速度·比率·HR), 本变体不覆写 */

  function destroy(host) {
    ui.lastSig = ""; /* 下次挂载强制整帧重建 */
    /* 宿主元素跨变体复用(同页签只有一个 data-dt-host), 换变体必须摘掉本变体的委托监听,
     * 否则新旧变体监听叠加、同一次点击被多个 handler 重复处理 */
    if (host && host.__dt01Click) {
      host.removeEventListener("click", host.__dt01Click);
      host.__dt01Click = null;
      host.__dt01Wired = false;
    }
  }

  function onClick(ev) {
    const h = ev.currentTarget;
    const foldHead = ev.target.closest("[data-fold]");
    if (foldHead) {
      const sec = foldHead.closest("[data-sec]");
      if (sec) {
        const title = sec.getAttribute("data-sec");
        ui.folded[title] = !ui.folded[title];
        sec.classList.toggle("folded");
      }
      return;
    }
    const rawsum = ev.target.closest(".dt01-rawsum");
    if (rawsum) {
      const det = rawsum.closest("details");
      /* 点击后 details 才翻转 open, 宏任务里回读 */
      setTimeout(() => { ui.rawOpen = !!(det && det.open); }, 0);
      return;
    }
    const btn = ev.target.closest("[data-act]");
    if (!btn) return;
    const ctx = h.__dtCtx;
    const cellEl = btn.closest(".dt01-cell");
    if (btn.getAttribute("data-act") === "open") {
      ctx.openTargetPath("torrent", ctx.drawer.hash);
      return;
    }
    const text = cellEl ? cellEl.querySelector(".dt01-vv") : null;
    const label = cellEl ? cellEl.querySelector(".dt01-k") : null;
    if (text) ctx.copyText(text.textContent, label ? label.textContent : "");
  }

  /* 事件委托挂宿主一次(宿主元素归 Vue 所有且跨重渲染复用) */
  function wire(host) {
    if (host.__dt01Wired) return;
    host.__dt01Wired = true;
    host.__dt01Click = onClick;
    host.addEventListener("click", onClick);
  }

  const _render = render;
  reg.register({
    id: "01", tab: "general",
    label: "英雄行·键值栅格(高)",
    css: CSS,
    render(host, ctx) {
      wire(host);
      host.__dtCtx = ctx;
      _render(host, ctx);
    },
    destroy,
  });
})();
