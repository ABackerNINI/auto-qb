/* auto-qb WEB UI · 详情面板的头部外壳与流量控件组组件(计划 26-10-11-2106 W3)
 *
 * 与 <aq-table> / drawer_tabs.js 同范式: 组件**只贡献模板与最小实例态**, 数据与动作一律经
 * $root 回调根实例(模板里写 $root.xxx, this 仍是根实例, 与内联模板逐字节等价; 且**不复制**
 * 任何方法实现 —— 复制会触发 _scan_mixin_wiring 的重名守阵: 后者覆盖前者, 被盖掉的永不执行)。
 * 模板放 tpl/drawer-head.html(x-template, tpl-manifest 注入 body); 本文件在 HTML 里必须排在
 * app.js **之前**(app.js 末尾要 app.component(...) 读 window.AQ_*), 排在 drawer_tabs.js 之后。
 *
 * 两个组件的**存在理由**与结构约束(多根片段 / 直接子选择器 / 单点化)全写在模板文件头注里,
 * 改它们之前先读那段 —— 尤其「<aq-qb-ctl> 不能包 wrapper」一条: 破了是**静默**的布局塌陷,
 * 静态守阵看不见(e2e/drawer-traffic.spec.mjs 按直接子元素钉)。
 */

window.AQ_DRAWER_HEAD_COMPONENT = {
  name: "aq-drawer-head",
  props: {
    /* 徽标色档: 渲染成 g-status 的 k-<tone> 类(种子形态 = 成员状态 kind; 流量形态恒 "other") */
    tone: { type: String, default: "other" },
    /* 徽标图标(sprite href); 种子形态 = kindIcon(成员 kind), 流量形态恒 "#i-chart" */
    icon: { type: String, required: true },
    /* 标题文本(种子形态 = drawerTitle(); 流量形态 = qbTrafficTitle) */
    text: { type: String, default: "" },
    /* 标题悬浮提示; null = 不渲 title 属性(traffic 形态旧版就没有 —— 而 title 会被
     * ui_feedback.js 落 DOM 时迁成 data-aq-tip, 凭空多一个空 tooltip 是行为变化, 故显式区分) */
    textTitle: { type: String, default: null },
    /* 徽标悬浮状态语(种子形态 = stateText(成员)); null/空 = 不渲 title 属性(同上) */
    statusTitle: { type: String, default: null },
  },
  template: "#tpl-aq-drawer-head",
};

window.AQ_QB_CTL_COMPONENT = {
  name: "aq-qb-ctl",
  template: "#tpl-aq-qb-ctl",
};
