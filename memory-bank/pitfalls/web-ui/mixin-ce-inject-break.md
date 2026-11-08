# Vue 全局 mixin 给每个组件 provide ce: 中间层组件缺透传, 插槽内注入链静默断裂

> 摘要: 全局 mixin(CONFIG_EDITOR)给**每个**组件都挂 `provide(){ce:this}` + 空 cfg 树 —— 把根模板段头抽成中间层组件时, 若它不把注入到的 ce 原样透传, 插槽里的 hub-field 会注入到**该组件实例**: 字段恒显 schema 默认值还带「默认」徽标、拨动不脏树、「保存并应用」永不出现、磁盘不动(重启无效), 而与走 `$root` 的同源读数自相矛盾, 全程零报错。修法 = 中间层组件补 `inject:["ce"]` + `provide(){ce:this.ce}`(范式样本 aq-traffic-card / CE_FIELD_BASE); 守阵必须钉**非缺省态**与写路径往返 —— 默认态断言与断裂回落值同形, 恒真。
> 触发: Vue provide/inject, 全局 mixin, CONFIG_EDITOR, ce 透传, 插槽注入断裂, aq-fold, hub-field, 开关不显示磁盘值, 默认徽标, 设置页开关无效, 保存并应用不出现, 改配置重启无效, 组件插槽内容注入

### 把根模板段头抽成中间层组件: 插槽里的 provide 消费者改注入到它, 配置编辑器读写全落空还不报错

- **触发**: 把原本写在根模板里的「段头 / 骨架块」抽成中间层组件, 且其**默认插槽里放消费 `provide` 的子组件** —— 本项目即 `6ad07b6a`(2026-10-21, 小控件三件套收敛, issue 26-10-20-2231)把折叠段头从普通 `div.hb-blk-hd` 换成 `<aq-fold>` 组件, `hub-field` 从卡片/根的直系孩子变成组件插槽内容。此时全局 mixin(`app.mixin(window.CONFIG_EDITOR)`, app.js:913)给**每个**组件都挂了 `provide(){ce:this}` 与 `data()` 新建的空 cfg 树(`tree:null`); 组件自己的 provide 赢过 mixin 的 provide(Vue 选项合并: 组件选项优先), 于是插槽里的 `hub-field` 注入到**中间层组件实例**。中招点共 5 处: 流量卡三区(traffic-card.html:36/144/271)、xtpl 的 object group 段(xtpl.html:36)、规则卡「触发与节奏」段(settings.html:237)。
- **判别**: 三重签名, 任一命中即中 —— ① **读失真**: 字段恒显 schema 默认值(磁盘 `traffic_source.enabled="false"` 时开关显「启用」)且带「默认」徽标(`cfgIsDefault` 在空树上恒真); ② **写落空**: 拨动不脏树(`cfgDirty` 在空树上恒 false)、「保存并应用」永不出现、磁盘不动(重启无效), 单次拨动还会在 `cfgSetPath` 的 `tree=null` 上抛 TypeError(被 Vue 事件处理器吞成 console.error); ③ **自相矛盾**: 走 `$root.xxx()` 的同源读数是对的(卡头摘要「来源已关闭」), 开关却说「启用」。浏览器级实证: 组件树遍历(subTree/children/slot 递归)看插槽内 hub-field 注入到的 `ce_name === "aq-fold"`; Vue 3 多根片段组件不渲染宿主标签, 选择器取不到, 只能走 `_vnode.component.proxy`。已排除假设: 版本闸门 / 陈旧标签页 / 后端 GET 造假(生产日志里 JSON 确实是 false)。
- **处置**: 中间层组件补 `inject:["ce"]` + `provide(){ return { ce: this.ce }; }`(Vue 选项初始化 inject 先于 provide, 此时 `this.ce` 已就绪) —— 范式样本在仓库里有两份: `aq-traffic-card`(traffic_card.js:15)与 `CE_FIELD_BASE`(config_editor.js:1171), 照抄即可。全局兜底(`CONFIG_EDITOR.provide` 改 `{ce: this.ce || this}`)对二件皆缺的组件无效且触及每个组件, 不采用。新增任何「默认插槽里放 hub-field / 消费 ce」的组件时, 透传是**必填项**而不是可选项。
- **守阵**: `e2e/traffic-source-switch.spec.mjs`(issue 26-10-22-0435 的回归栅): route 桩把磁盘值注入成非缺省态, 断言流量卡开关显关闭 + 无「默认」徽标 + 与摘要同判 + 刷新后仍关闭(读路径), 拨动 → 脏标记 → PUT 载荷(写路径), 规则卡 meta 段第二现场; **摘掉透传后 6 例全红**。教训: views.spec「三区同屏」那条只断言「启用勾选反映 schema 缺省 true」—— 与断裂后的回落值**同形**, 恒真, 这类默认态断言对注入断裂零鉴别力; 判据必须钉**非缺省态**与**写路径往返**。
- **复发**: 0 (复踩时在此行追加「+N (日期): 为什么没命中」, 无复发可删本行)
