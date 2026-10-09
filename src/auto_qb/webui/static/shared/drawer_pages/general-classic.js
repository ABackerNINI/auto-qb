/* auto-qb WEB UI · 详情面板 general 页签 classic 页插件(R2 S1, 计划 26-10-09-2219)
 *
 * 经典链从 tpl/drawer.html 的 Vue 模板移植为注册表正式条目(id "classic")—— 移植不重写:
 * 类名与结构逐位一致(HR 块 / drawer-sec 分组键值 / drawer-raw 原始字段折叠), CSS 钩子
 * (.drawer-hr/.drawer-sec/.f-rows/.f-row/.ico-t-* /.drawer-raw)原样命中三皮肤既有规则;
 * 额外只加惰性 data-dt-act 标记供事件委托判别(变体同习语, CSS/e2e 不感知)。
 * 数据: ctx.drawerGeneralSections() 预格式化单点(哨兵翻译单点不复刻, 变体同源);
 * 图标着色 ctx.icoTone 派生表; HR 两行走 ctx.hrStateLine/ctx.hrSiteLine。
 * 动作: 打开目录/复制走 ctx.openTargetPath/ctx.copyText(与原模板行内 act 平移)。
 * 状态自保: drawer-raw 展开态(ui.rawOpen; Vue 原地 patch 天然保留, 全量重建自己记账) +
 * 滚动位置(withScroll); 数据未变(整份 detail 序列化比对)跳过重建(skipUnchanged)。
 */
(function () {
  "use strict";
  const reg = window.AQB_DRAWER_TPL_REG;
  if (!reg) return; /* 核心未载入(清单序错): 静默退出, 守阵会抓 */
  const T = reg.dtHtml;
  const H = reg.helpers;

  /* 视图偏好(跨重渲染保持): 原始键值折叠区展开态; lastSig 供数据未变跳过重建 */
  const ui = { rawOpen: false, lastSig: "" };

  function rowHtml(r) {
    const tone = icoTone(r.icon);
    let h = T`<div class="f-row${r.wide ? " wide" : ""}">`;
    h += T`<svg class="ico ico-sm${tone ? " " + tone : ""}" viewBox="0 0 16 16"><use href="${r.icon}"></use></svg>`;
    h += T`<span class="k">${r.label}</span>`;
    h += T`<span class="v mono" title="${String(r.text)}">${r.text}</span>`;
    if (r.act === "open" || r.act === "copy") {
      h += T`<button type="button" class="bt icon f-row-act" data-dt-act="${r.act}"><svg class="ico ico-sm" viewBox="0 0 16 16"><use href="${r.act === "open" ? "#i-folder-open" : "#i-copy"}"></use></svg></button>`;
    }
    h += T`</div>`;
    return h;
  }

  /* FX-22: 字段行图标着色 —— 派生表单点在经典链(drawer.js icoTone), 经 ctx 消费不复刻 */
  function icoTone(icon) {
    return ctx0 ? ctx0.icoTone(icon) : "";
  }
  let ctx0 = null; /* render 期暂存(icoTone 是实例方法, 须有 ctx 才能调) */

  function render(host, ctx) {
    const d = ctx.drawer && ctx.drawer.detail;
    if (!d) {
      host.replaceChildren();
      ui.lastSig = "";
      return;
    }
    /* 数据未变跳过重建(hash 入 sig: 换种子必重建); 序列化比对比浅比较更强, 开销可忽略 */
    const sig = ctx.drawer.hash + "|" + JSON.stringify(d);
    if (H.skipUnchanged(host, ui, sig)) return;
    ctx0 = ctx;
    let h = "";
    /* HR 块(条件/类名与原模板逐位一致) */
    if (d.hr_triggered || d.hr_state || d.hr_excluded) {
      const cls = d.hr_triggered ? (d.hr_satisfied ? "done" : "pending") : "info";
      h += T`<div class="drawer-hr ${cls}">`;
      if (d.hr_excluded) h += T`<b>已排除出 HR 管理</b>`;
      else if (d.hr_triggered) h += T`<b>${d.hr_satisfied ? "H&R 已达标" : "H&R 未达标"}</b>`;
      if (d.hr_state) h += T`<span title="${d.hr_reason}">${ctx.hrStateLine(d)}</span>`;
      if (d.hr_site_lane) h += T`<span title="站点侧值(账号级权威, 滞后一个刷新周期)">${ctx.hrSiteLine(d)}</span>`;
      if (d.hr_tag) h += T`<span>${d.hr_tag}</span>`;
      if (d.hr_tag_done) h += T`<span>${d.hr_tag_done}</span>`;
      if (d.hr_triggered) h += T`<span>要求做种 ${ctx.fmtDuration(d.hr_req_time)}</span>`;
      if (d.hr_triggered && d.hr_req_ratio > 0) h += T`<span>要求分享率 ${d.hr_req_ratio.toFixed(2)}</span>`;
      h += T`</div>`;
    }
    /* 分组键值(FX-22 卡片化结构原样: h4 标题 + 右侧汇总 + 行级图标/长值块行/行内动作) */
    for (const sec of ctx.drawerGeneralSections()) {
      h += T`<section class="drawer-sec"><h4><span>${sec.title}</span>`;
      if (sec.sum) h += T`<span class="s-sum">${sec.sum}</span>`;
      h += T`</h4><div class="f-rows">${R(sec.rows.map(rowHtml).join(""))}</div></section>`;
    }
    /* 原始字段折叠区(open 态自保; qB API 字段名原样, 对象值 JSON 化) */
    h += T`<details class="drawer-raw"${ui.rawOpen ? " open" : ""}><summary>全部字段(原始键值, 与 qB API 字段名一致)</summary><div class="drawer-rows">`;
    for (const k of Object.keys(d)) {
      const v = typeof d[k] === "object" ? JSON.stringify(d[k]) : d[k];
      h += T`<span class="k">${k}</span><span class="v mono">${v}</span>`;
    }
    h += T`</div></details>`;
    /* 滚动位置自保(纵横成对): 滚动容器是宿主父级(.drawer-body, Vue 所有) —— 单点 helper */
    H.withScroll(host, () => {
      host.replaceChildren(document.createRange().createContextualFragment(h));
    });
  }

  function destroy(host) {
    ui.lastSig = ""; /* 下次挂载强制整帧重建 */
    /* 宿主元素跨插件复用(同页签只有一个 data-dt-host), 必须摘掉本插件的委托监听 */
    H.unwireEvents(host);
  }

  function onClick(ev) {
    const h = ev.currentTarget;
    const ctx = h.__dtCtx;
    const rawsum = ev.target.closest(".drawer-raw > summary");
    if (rawsum) {
      const det = rawsum.closest("details");
      /* 点击后 details 才翻转 open, 宏任务里回读(变体 01 同款) */
      setTimeout(() => { ui.rawOpen = !!(det && det.open); }, 0);
      return;
    }
    const btn = ev.target.closest(".f-row-act[data-dt-act]");
    if (!btn) return;
    const rowEl = btn.closest(".f-row");
    if (btn.getAttribute("data-dt-act") === "open") {
      ctx.openTargetPath("torrent", ctx.drawer.hash);
      return;
    }
    const vEl = rowEl ? rowEl.querySelector(".v") : null;
    const kEl = rowEl ? rowEl.querySelector(".k") : null;
    if (vEl) ctx.copyText(vEl.textContent, kEl ? kEl.textContent : "");
  }

  /* 事件委托挂宿主一次(宿主元素归 Vue 所有且跨重渲染复用; 挂摘成对纪律在核心 helper) */
  function wire(host) {
    H.wireEvents(host, { click: onClick });
  }

  const R = reg.dtRaw;
  reg.register({
    id: "classic",
    tab: "general",
    label: "经典",
    render(host, ctx) {
      wire(host);
      host.__dtCtx = ctx;
      render(host, ctx);
    },
    notify(type, host, ctx) {
      render(host, ctx); /* skipUnchanged 在 render 内做 sig 比对, 任意类型通知都安全 */
    },
    destroy,
  });
})();
