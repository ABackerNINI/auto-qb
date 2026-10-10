/* auto-qb WEB UI · 详情面板 peers 页签 classic 页插件(R2 S1, 计划 26-10-09-2219)
 *
 * 经典链从 tpl/drawer.html 的 Vue 模板移植为注册表正式条目(id "classic")—— 移植不重写:
 * 九列表格(地址/客户端/标记/进度/下载/上传/已下载/已上传/关联度)类名与结构逐位一致
 * (.drawer-table/.num/.mono-cell/.wrap), CSS 原样命中; 本页无行内动作(观察态页签)。
 * 数据: ctx.drawerPeerRows()(qB peers 响应 dict/array 双形态归一单点) + peersLoading。
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
    const rows = ctx.drawerPeerRows();
    const loading = !!ctx.drawer.peersLoading;
    const sig = ctx.drawer.hash + "|" + loading + "|" + JSON.stringify(rows);
    if (H.skipUnchanged(host, ui, sig)) return;
    let h = "";
    if (loading && !rows.length) {
      h += K.loading("正在加载…");
    } else if (rows.length) {
      const trs = rows.map((p) =>
        T`<tr><td class="mono-cell">${p.addr}</td><td class="wrap">${p.client}</td><td>${p.flags}</td>` +
        T`<td class="num">${p.progress}%</td><td class="num">${p.dlspeed}</td><td class="num">${p.upspeed}</td>` +
        T`<td class="num">${p.downloaded}</td><td class="num">${p.uploaded}</td><td class="num">${p.relevance}</td></tr>`
      ).join("");
      h += K.table(
        ["地址", "客户端", "标记", { label: "进度", num: true }, { label: "下载", num: true },
         { label: "上传", num: true }, { label: "已下载", num: true }, { label: "已上传", num: true },
         { label: "关联度", num: true }],
        trs
      );
    } else {
      h += K.empty("暂无已连接用户");
    }
    H.withScroll(host, () => {
      host.replaceChildren(document.createRange().createContextualFragment(h));
    });
  }

  function destroy(host) {
    ui.lastSig = "";
    H.unwireEvents(host);
  }

  reg.register({
    id: "classic",
    tab: "peers",
    label: "经典",
    render(host, ctx) {
      host.__dtCtx = ctx;
      render(host, ctx);
    },
    notify(type, host, ctx) {
      render(host, ctx);
    },
    destroy,
  });
})();
