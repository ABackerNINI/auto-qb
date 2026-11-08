# Teleport 目标缺失: 生产版静默不挂子节点, 卸载时抛 TypeError 打断整次 patch

> 摘要: 把 `<teleport :to="<选择器>">` 挂到**目标元素不在文档**的时刻, Vue 生产版会**静默跳过子节点挂载**(无任何警告, 只有 dev 版打 `Invalid Teleport target`), 之后卸载这个 teleport 时 `TeleportImpl.remove` 会遍历那些**从未挂载**的 children 去 `unmount`, 对 `null` component 解构抛 `TypeError: Cannot destructure property 'bum' of 'e' as it is null` —— 异常从 `patchChildren` 里冒出来, **整次 patch 中断**, 页面停在半渲染态(用户所见「切换后内容消失 / 布局卡在旧态 / 再切也回不去」)。判据的**求值时机**是全部难点: 布局换代的 patch 顺序是「先拆旧分支(旧锚随之离场) → 再挂新分支」, 父级渲染里求值的判据在**拆之前**跑, 那一拍旧目标还在 ⇒ 判真; 只有把判据放进 **teleport 自己的挂载拍**(承载它的组件自己的渲染拍)才拿到真值。
> 触发: teleport 目标缺失, Invalid Teleport target, 生产版静默, patch 中断, 内容消失, 半渲染态, 合并态切换, 门跨越, v-if 换代, 锚离场, 桥锚, aq-dt-bridge, dtBridgeOn, dtBridgeTargetOn, Cannot destructure property bum, unmountComponent null
**Refs:** memory-bank/tasks/26-10-14-webui-drawer-merge-bridge-guard.md

## 条目

- **触发**: 变体表格体桥(`<aq-dt-bridge>` 的 `<teleport :to>` 锚选择器, 计划 26-10-12-0527 D1)在布局换代时被挂载 —— 用户报障「种子详情模板合并态切换时内容消失」。合并开关由开转关(或门跨越/切页签/换目标)时, 抽屉抛 `TypeError: Cannot destructure property 'bum' of 'e' as it is null`, 表现为: tp 对关合并后单栏**桥表行归零**(文本仅剩外壳)、再开合并**回不去**(`data-merge` 停在旧值)。
- **判别**: 压缩栈对位 —— 从内往外 `unmountComponent(null)` ← `unmount` ← **`TeleportImpl.remove`**(`Object.remove`, 它遍历 `children` 逐个 `um()`) ← `unmountChildren` ← `unmountComponent` ← `unmount` ← `patchChildren`。**「teleport 的 children 从未挂载」是唯一能造出 `null` component 的入口** ⇒ 反查 `TeleportImpl.mount`: 它先 `resolveTarget(props)`, 取不到目标就**不挂子节点**(生产版静默)。三条自查问句: ①这个 teleport 的目标选择器**此刻**能 `document.querySelector` 到吗? ②判据是在**谁的渲染拍**求值的(父级 = 拆之前, 不可信)? ③有没有一条路径会让目标在「渲染 → patch」之间消失(v-if 换代 / 宿主重建 / 祖先离场)?
  - **反例(别走这条路)**: 在**父级** `v-if` 的判据里加 `document.querySelector` 存在性检查 —— 实测**无效**。父级渲染发生在拆旧分支**之前**, 那一拍旧目标仍在文档里, 判真; 等桥组件真挂载时目标已被拆走。定位手法: 把判据临时改成恒 `false`(sledgehammer), 错误消失即证实肇事者是该 teleport。
- **处置**: 把目标存在性判据放进**承载 teleport 的组件自己的渲染拍**(与 teleport 的 `mount` 同拍), 并用它作 teleport 的 `v-if` —— 目标不存在就整个不挂 teleport(而不是挂一个空目标的 teleport)。锚稍后出现时, 驱动锚状态的响应式数据变更会触发该组件重渲, teleport 自动归位, 内容不缺。本仓落点: `drawer_templates.js::dtBridgeTargetOn(tab, seg)`(`document.querySelector(dtBridgeTo(tab, seg))`)+ `tpl/xtpl.html` 的 `<teleport v-if="$root.dtBridgeTargetOn(tab, seg.key)">`; **逐段**判据顺带覆盖分段桥(08 五分组「组空整节隐藏 ⇒ 锚离场」)的同型隐患。守阵: e2e `合并态切换: 桥变体列换代不得抛错且内容不丢`(gc/tp 双对开关往返 + 门跨越 + 逐点零运行期错误 + 桥表行仍在; 红验 = 判据注入 `return true` 即红) + 静态守阵 `test_drawer_table_bridge_wiring` 两钉(方法名与判据语义 / 模板 `v-if` 计数)。
- **复发**: 0。同类「锚/宿主离场」族已另有两档(坑档 `vif-host-node-stale` 记模块级缓存持旧节点; `drawer-switch-flicker` 记软切换空态闪烁), 但**根因不同**: 那两档是「引用陈旧」, 本档是「Vue 内部对未挂载 children 的卸载崩溃」。
