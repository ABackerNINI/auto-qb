/* aq-traffic-card: 「流量与限速」合并卡的组件壳(计划 26-10-18-0813 B3/D15)
 *
 * 纯模板件: 模板在 shared/tpl/traffic-card.html(x-template, into: body), 数据与动作经 $root
 * 回调根实例(config_hub.js 的 tm* / hubSub* / cfgCurve* 系列)。**这里不定义任何方法** ——
 * 组件里再写一份 tmXxx 会与根 mixin 同名, Vue 的合并是后者覆盖前者且不报错, 被盖掉的那份
 * 永不执行(test_webui_static_skins 的 _scan_mixin_wiring 专门钉这种形态)。
 *
 * inject/provide 不是可选项: 全局 mixin(CONFIG_EDITOR) 给**每个**组件都挂了 provide(){ce:this},
 * 于是本组件若不显式透传, 卡内的 <hub-field> 注入到的 ce 就是本组件实例(没有 cfg* 方法) ——
 * 表现为字段只显默认值、编辑不进根树。这里照 CE_FIELD_BASE 的写法把自己注入到的 ce 原样
 * provide 下去(根实例的 ce 恒为自身, 任意深度都拿到同一个)。
 */
window.AQ_TRAFFIC_CARD_COMPONENT = {
  name: "aq-traffic-card",
  inject: ["ce"],
  provide() {
    return { ce: this.ce };
  },
  template: "#tpl-aq-traffic-card",
};
