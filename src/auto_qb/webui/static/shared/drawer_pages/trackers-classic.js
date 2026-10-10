/* auto-qb WEB UI · 详情面板 trackers 页签 classic 页插件(R2 S1, 计划 26-10-09-2219)
 *
 * 经典链从 tpl/drawer.html 的 Vue 模板移植为注册表正式条目(id "classic")—— 移植不重写:
 * 工具栏(添加 tracker)/ 加载态 / 六列表格(URL/状态/做种/用户/消息/操作)/ 空态, 类名与结构
 * 逐位一致(.drawer-toolbar/.empty/.drawer-table/.virtual/.cell-act/.row-btn), CSS 原样命中;
 * 额外只加惰性 data-dt-act 标记供事件委托判别(变体同习语)。
 * 数据: ctx.drawer.trackers + trackersLoading; 翻译走 ctx.drawerTrackerStatus/
 * drawerTrackerVirtual/fmtPeersQb(哨兵与虚拟条目判别单点不复刻)。
 * 动作: 添加 ctx.trackerAdd / 行内删除 ctx.trackerRemove(url 取自行首格文本 —— 与展示值同源,
 * 后端本就按 mask 值当场重取原文比对)。
 * 三态外壳与表格骨架走部件工具箱(reg.kit, 与其余 classic 插件共享)。
 */
(function () {
  "use strict";
  const reg = window.AQB_DRAWER_TPL_REG;
  if (!reg) return; /* 核心未载入(清单序错): 静默退出, 守阵会抓 */
  const T = reg.dtHtml;
  const H = reg.helpers;
  const K = reg.kit;

  const ui = { lastSig: "" };

  function render(host, ctx) {
    const list = ctx.drawer.trackers || [];
    const loading = !!ctx.drawer.trackersLoading;
    const sig = ctx.drawer.hash + "|" + loading + "|" + JSON.stringify(list);
    if (H.skipUnchanged(host, ui, sig)) return;
    let h = '<div class="drawer-toolbar"><button class="bt ghost sm" data-dt-act="add">' +
      '<svg class="ico ico-sm" viewBox="0 0 16 16"><use href="#i-plus"></use></svg>添加 Tracker</button></div>';
    if (loading && !list.length) {
      h += K.loading("正在加载…");
    } else if (list.length) {
      const rows = list.map((t) => {
        const virtual = ctx.drawerTrackerVirtual(t.url);
        let r = T`<tr${virtual ? ' class="virtual"' : ""}>`;
        r += T`<td class="wrap mono-cell">${t.url}</td>`;
        r += T`<td>${ctx.drawerTrackerStatus(t.status)}</td>`;
        r += T`<td class="num">${ctx.fmtPeersQb(t.num_seeds, t.num_complete)}</td>`;
        r += T`<td class="num">${ctx.fmtPeersQb(t.num_leeches, t.num_incomplete)}</td>`;
        r += T`<td class="wrap">${t.msg || "—"}</td>`;
        r += '<td class="cell-act">';
        if (!virtual) {
          r += T`<button class="row-btn danger" data-dt-act="del" data-dt-url="${t.url}"><svg class="ico ico-sm" viewBox="0 0 16 16"><use href="#i-trash"></use></svg></button>`;
        }
        r += "</td></tr>";
        return r;
      }).join("");
      h += K.table(["URL", "状态", { label: "种子", num: true }, { label: "用户", num: true }, "消息", { label: "", cls: "th-act" }], rows);
    } else {
      h += K.empty("暂无 tracker");
    }
    H.withScroll(host, () => {
      host.replaceChildren(document.createRange().createContextualFragment(h));
    });
  }

  function destroy(host) {
    ui.lastSig = "";
    H.unwireEvents(host);
  }

  function onClick(ev) {
    const ctx = ev.currentTarget.__dtCtx;
    const del = ev.target.closest('[data-dt-act="del"]');
    if (del) {
      ctx.trackerRemove(del.getAttribute("data-dt-url") || "");
      return;
    }
    if (ev.target.closest('[data-dt-act="add"]')) ctx.trackerAdd();
  }

  reg.register({
    id: "classic",
    tab: "trackers",
    label: "经典",
    render(host, ctx) {
      H.wireEvents(host, { click: onClick });
      host.__dtCtx = ctx;
      render(host, ctx);
    },
    notify(type, host, ctx) {
      render(host, ctx);
    },
    destroy,
  });
})();
