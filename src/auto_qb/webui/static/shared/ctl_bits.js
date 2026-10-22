/* ctl_bits.js — 模板层「小控件」三件套的组件定义(收敛 issue 26-10-20-2231 / 台账 R23-B-01·02·16·17)
 *
 * 模板在 shared/tpl/ctl-bits.html(x-template, tpl-manifest 注入 body); 本文件在 HTML 里必须排在
 * app.js **之前**(app.js 末尾要 app.component(...) 读 window.AQ_*), 与 aq-combo-input(定义在
 * add_torrent.js)同范式 —— **组件只贡献模板与 props, 不持有任何业务状态**, 数据与动作一律经
 * 回调回到拥有它的那一层(根实例 / hub-field)。在这里复写一份方法会触发 _scan_mixin_wiring 的
 * 重名守阵: 被 Vue 合并策略盖掉的那一套永不执行, 且不报错。
 *
 * 为什么不拆三个文件: 三件套是同一层东西 —— 都只解决「同一件事在模板里写了好几遍」, 共用同一份
 * tpl 分片; 拆开只会把「什么时候该用哪一种」的口径备注撕成散落的几段。
 *
 * 回调 prop(onChange / onToggle / onPick)而不是 emit: 组件常同时出现在根模板与 hub-field 两种
 * 调用面里, 回调形态两边写法一致(emit 在 $root 侧还要额外留 @xxx 落点); 与组合框组件
 * aq-combo-input 的 onPick 同款, 不再引入第二套口径。
 *
 * !Vue 会把 methods 绑到实例上, 故 `:on-toggle="toggleGroup"` 直接传组件方法引用是安全的
 *  (this 不会丢); 需要带参的一律在调用点用箭头函数包一层。
 */

/* 开关 <aq-switch>: 7 处 hb-switch 手抄块的收敛形态(R23-B-01)。
 * 「什么时候该带文字」的判据写在模板分片头注里 —— 那才是不会再漂移一次的位置:
 * 改模板的人会读到它, 改 JS 的人不会。 */
window.AQ_SWITCH_COMPONENT = {
  name: "aq-switch",
  props: {
    checked: { type: Boolean, default: false },
    disabled: { type: Boolean, default: false },
    onChange: { type: Function, required: true },  // (checked: boolean) => void
    tone: { type: String, default: "" },           // 色调类名(.important / .danger, 来自 hubToneOf)
    tip: { type: String, default: "" },            // title 悬浮说明; 空 = 不渲染 title
    text: { type: [Boolean, String], default: false },  // false = 不渲染; true = 启用/关闭; 字符串 = 自定义标签
  },
  computed: {
    /* 文案三态都判在这一处: 字符串 = 调用方给的标签(内联从属开关), true = 启用/关闭,
     * false = 不渲染 —— 收敛前「4 带文字 / 3 不带」的样子保持不变, 变的是判据单点化 */
    swText() {
      if (this.text === true) return this.checked ? "启用" : "关闭";
      if (typeof this.text === "string" && this.text) return this.text;
      return null;
    },
  },
  template: "#tpl-aq-switch",
};

/* 可折叠区段 <aq-fold>: 5 处 hb-sub-toggle 段头的收敛形态(R23-B-02 + R23-B-16)。
 * 三种 toggle 签名(字符串 key / 组件方法 / 双参数)归一为「回调 + open 布尔」—— 组件不关心
 * key 长什么样; 键盘契约(role=button + tabindex=0 + Enter)与 aria 挂层只有这一份实现。
 * !不加 keyup.space: 段头里常自带 focusable 子元素(hb-ask 等), 空格会从它们冒泡上来 ——
 *   里层钮的 click 与本层的 toggle 各打一次, 净效果是「按了没反应」。这条因此刻意与 pop-item
 *   的 enter+space 口径不等, 差异写在这里, 免得下次有人当作漏项补上去。
 *
 * ce 透传(与 aq-traffic-card / CE_FIELD_BASE 同范式, 缺了它就是静默事故):
 * <aq-fold> 的默认插槽里常直接放 <hub-field>(流量卡三区 / xtpl 的 object group 段 /
 * 规则 meta 段) —— 而全局 mixin(CONFIG_EDITOR)给**每个**组件都挂了 provide(){ce:this},
 * 本组件若不把自己注入到的 ce 原样透传, 插槽里的 hub-field 会注入到**本组件实例**:
 * 它带着 mixin data() 新建的空 cfg 树(tree=null), 于是字段只显 schema 默认值、编辑不进
 * 根树。2026-10-22 实测(流量卡「启用」开关): 磁盘 enabled=false 时开关恒显「启用」且带
 * 「默认」徽标, 拨动不脏树、「保存并应用」永不出现, 与横幅($root.tmSourceOff 读到 false)
 * 自相矛盾。Vue 选项初始化 inject 先于 provide, 此时 this.ce 已就绪。 */
window.AQ_FOLD_COMPONENT = {
  name: "aq-fold",
  inject: ["ce"],
  provide() {
    return { ce: this.ce };
  },
  props: {
    open: { type: Boolean, default: false },
    onToggle: { type: Function, required: true },  // () => void
    title: { type: String, default: "" },
    note: { type: String, default: "" },
  },
  template: "#tpl-aq-fold",
};

/* 分段单选钮 <aq-seg>: 四套分段钮(hist-tabs / qb-tabs / qb-seg / drawer-tabs)的收敛形态(R23-B-17)。
 * items = [{ v, label }] —— 清单改由调用方各自的领域单点提供(历史粒度 / 窗口档位 / 纵轴三态 /
 * 抽屉页签), 组件只管「按钮长什么样、哪个 active、点了回调谁」。
 * !容器不在组件里: 容器类名是 CSS 选择器的一部分(见模板分片头注), 且四套的 DOM 位置差异很大
 *  (nav[role=tablist] / .hist-tabs / 嵌在 .qb-tools 里的 .qb-seg) —— 硬要由组件吐容器, 父组件的
 *  结构守阵(如 <aq-qb-ctl> 恰两根)就得跟着下沉。 */
window.AQ_SEG_COMPONENT = {
  name: "aq-seg",
  props: {
    items: { type: Array, default: () => [] },     // [{ v, label }]
    value: { type: [String, Number], default: "" },// 当前选中项的 v
    onPick: { type: Function, required: true },    // (v) => void
  },
  template: "#tpl-aq-seg",
};
