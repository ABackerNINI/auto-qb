/* auto-qb WEB UI · 详情面板 content 页签 classic 页插件(R2 S1, 计划 26-10-09-2219)
 *
 * 经典链从 tpl/drawer.html 的 Vue 模板移植为注册表正式条目(id "classic")—— 移植不重写:
 * 工具栏(重命名… + 提示语)/ 加载态 / 四列文件树表(文件/大小/进度/优先级)/ 空态, 类名与
 * 结构逐位一致(.drawer-toolbar/.drawer-toolbar-hint/.empty/.drawer-table/.dir-name/.prio-btn/
 * .skipped/.sel/.clickable), CSS 原样命中; 额外只加惰性 data-dt-idx 标记供委托取行下标。
 * 数据: ctx.drawerFileRows()(构树扁平化单点: 目录聚合/缩进深度/优先级翻译) + filesLoading。
 * 交互(功能完整保留): 行点选 ctx.fileRowSelect(选中态直接翻行类, 万级行不整帧重建) /
 * 优先级小菜单 ctx.openFilePrio(合成事件对象只换 currentTarget 锚点, 真实 target/传播原样) /
 * 重命名 ctx.renameFileRow。
 * 状态自保: 行选中是 app 级单点 drawerSelPath(rename-fs 的作用对象, 实例间语义不变);
 * 优先级小菜单是文档级单例 —— 实例销毁即收回(归属权随实例转移)。
 */
(function () {
  "use strict";
  const reg = window.AQB_DRAWER_TPL_REG;
  if (!reg) return; /* 核心未载入(清单序错): 静默退出, 守阵会抓 */
  const T = reg.dtHtml;
  const H = reg.helpers;
  const K = reg.kit;

  const ui = { lastSig: "", rows: [] };

  function render(host, ctx) {
    const rows = ctx.drawerFileRows();
    const loading = !!ctx.drawer.filesLoading;
    const sel = ctx.drawerSelPath || "";
    const sig = ctx.drawer.hash + "|" + loading + "|" + sel + "|" + JSON.stringify(rows);
    if (H.skipUnchanged(host, ui, sig)) return;
    ui.rows = rows;
    let h = '<div class="drawer-toolbar"><button class="bt ghost sm" data-dt-act="rename">' +
      '<svg class="ico ico-sm" viewBox="0 0 16 16"><use href="#i-pencil"></use></svg>重命名…</button>' +
      '<span class="drawer-toolbar-hint">点击行名选中文件/目录 · 点击优先级修改</span></div>';
    if (loading && !rows.length) {
      h += K.loading("正在加载…");
    } else if (rows.length) {
      const trs = rows.map((r, i) => {
        /* 行类可叠加(原模板 {skipped, sel} 两键独立): 跳过态行也能是重命名选中行 */
        const cls = [r.skipped ? "skipped" : "", r.path === sel ? "sel" : ""].filter(Boolean).join(" ");
        let t = T`<tr${cls ? ' class="' + cls + '"' : ""}>`;
        t += T`<td class="wrap clickable" data-dt-idx="${i}"><span class="dir-name${r.dir ? " dir" : ""}" style="padding-left:${r.depth * 16}px">${r.name}</span></td>`;
        t += T`<td class="mono-cell num">${r.text}</td>`;
        t += T`<td class="num">${r.dir ? "—" : r.progress + "%"}</td>`;
        t += "<td>";
        if (!r.dir) t += T`<button class="prio-btn" data-dt-idx="${i}"${r.skipped ? ' class="skipped"' : ""}>${r.prio}</button>`;
        else t += "<span>—</span>";
        t += "</td></tr>";
        return t;
      }).join("");
      h += K.table(["文件", { label: "大小", num: true }, { label: "进度", num: true }, "优先级"], trs);
    } else {
      h += K.empty("无文件列表");
    }
    H.withScroll(host, () => {
      host.replaceChildren(document.createRange().createContextualFragment(h));
    });
  }

  function destroy(host, ctx) {
    ui.lastSig = "";
    /* 优先级小菜单是文档级单例: 挂载它的实例销毁即收回(与 drawerTab 换页签收起同语义) */
    if (ctx && ctx.filePrio) ctx.filePrio.visible = false;
    H.unwireEvents(host);
  }

  function onClick(ev) {
    const ctx = ev.currentTarget.__dtCtx;
    const prio = ev.target.closest(".prio-btn[data-dt-idx]");
    if (prio) {
      ev.stopPropagation(); /* 原模板 @click.stop: 防止开菜单的点击立即被窗口关闭监听收掉 */
      const r = ui.rows[Number(prio.getAttribute("data-dt-idx"))];
      if (!r) return;
      /* 合成事件对象只换 currentTarget 锚点(小菜单按它定位), _markCtxSource 读真实 target */
      ctx.openFilePrio({ target: ev.target, currentTarget: prio }, r.index);
      return;
    }
    const cell = ev.target.closest("td.clickable[data-dt-idx]");
    if (cell) {
      const r = ui.rows[Number(cell.getAttribute("data-dt-idx"))];
      if (!r) return;
      ctx.fileRowSelect(r); /* app 级单点翻转(再点同行取消), rename-fs 作用对象 */
      /* 选中态直接翻行类(万级行不整帧重建) */
      const tbody = cell.closest("tbody");
      if (tbody) {
        const prev = tbody.querySelector("tr.sel");
        if (prev) prev.classList.remove("sel");
        if (ctx.drawerSelPath === r.path) cell.closest("tr").classList.add("sel");
      }
      ui.lastSig = ""; /* sel 已变: 下次通知强制重建对齐(防 sig 记账与 DOM 脱节) */
      return;
    }
    if (ev.target.closest('[data-dt-act="rename"]')) ctx.renameFileRow();
  }

  reg.register({
    id: "classic",
    tab: "content",
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
