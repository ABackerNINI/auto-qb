# 详情面板桥锚 · 合并态切换内容消失（Teleport 目标缺失 ⇒ patch 中断）修复

> 摘要: 用户报「修复: 种子详情模板合并态切换时内容消失」。真浏览器探针逐步取证定案：**不是样式/数据问题，而是变体表格体桥（`<aq-dt-bridge>` 的 `<teleport :to>` 锚选择器）在目标已离场的那一窗被挂载**。布局换代（合并开关 / 门跨越）的 patch 顺序 = 「先拆旧分支（旧锚随之离场）→ 再挂新分支」，而父级 `v-if` 的 `dtBridgeOn` 在**拆之前**求值（那一拍旧锚还在 ⇒ 判真）；Vue 生产版对目标缺失的 teleport **静默不挂子节点**（无警告），之后卸载它时对 `null` component 解构抛 `TypeError: Cannot destructure property 'bum' of 'e' as it is null`，**整次 patch 中断** ⇒ 抽屉停在半渲染态：tp 对关合并后单栏桥表行归零（`bodyRows 0`、文本仅剩外壳 90 字符）、再开合并也回不去（`split` 停在 false）。两条对照实验定根因：①父级判据里加 `document.querySelector` 存在性检查 → **无效**（拆之前求值，那一拍旧锚还在文档里）；②`dtBridgeOn` 恒 `false`（sledgehammer）→ **零错误**，证实肇事者就是桥的 teleport。**修法**：目标存在性判据 `dtBridgeTargetOn(tab, seg)` 移进**桥组件自己的渲染拍**（与 teleport 的 `mount` 同拍，拿到的才是真值）+ 桥模板 `<teleport>` 加 `v-if`；逐段判据顺带覆盖分段桥（08「组空整节隐藏 ⇒ 锚离场」）同型隐患。**验证**：e2e 新用例（gc/tp 双对开关往返 + 门跨越 + 逐点零运行期错误 + 桥表行仍在）双皮肤全绿，红验 = 判据注入 `return true` 即红（报障现场重现，还原即绿）；`dev.e2e --grep @fast` 全绿；`test.full` 全绿（数字见基线切片 `26-10-14-0143`）。改动面 2 源文件 + 2 测试文件，**零 API / 零观感变化**。

> 最后活动: 2026-10-14 01:43

**Refs:** memory-bank/tasks/26-10-14-webui-drawer-merge-bridge-guard.md,memory-bank/testing/baselines/26-10-14-0143-webui-drawer-merge-bridge-guard.md,memory-bank/pitfalls/web-ui/teleport-target-missing-patch-abort.md

## 正在进行

（无 —— 本专题单轮闭环：复现 → 根因 → 修 → 红绿双验 → 收尾回写。）

## 已完成(迁自「正在进行」)

- **复现与取证**：临时探针（`e2e/drawer-merge.spec.mjs` 内，取证后删）逐步 dump `drawer-body` 文本长度 / 每列行数 / 每宿主子节点数 + 逐步 console 错误，第一轮即锁定「合并开关由开转关」两处（gc 对与 tp 对）抛错，且 tp 对那一步单栏内容只剩外壳。
- **根因**：压缩栈对位（`Object.remove` = `TeleportImpl.remove`；最内层 `unmountComponent(null)` ⇒ 该 teleport 的子节点从未挂载）+ 两条对照实验（父级 DOM 检查无效 / 恒 false 零错）。
- **修**：`drawer_templates.js::dtBridgeTargetOn(tab, seg)` + `tpl/xtpl.html` 桥模板 teleport `v-if`。
- **守阵**：e2e 用例「合并态切换: 桥变体列换代不得抛错且内容不丢」× 双皮肤（红绿双验）；静态守阵 `test_drawer_table_bridge_wiring` 两钉（方法名 + 判据语义 / 模板 `v-if` 计数）。
- **回写**：任务档案 + 本切片 + 坑档 `pitfalls/web-ui/teleport-target-missing-patch-abort.md` + 基线切片 + `kb.index` 重建。`modules/webui-static-contract.md` **有意未动**（已在 cap 债务内，且本修法不新增变体侧接入面）。

## 遗留债务(需另开会话)

- **cap 债务**：`modules/webui-static-contract.md` 超 evergreen cap（承 26-10-12-1800 切片结转，本轮未加深）；清理需跑 `commands run doc.caps -- --strict`。
- **切片数债务**：`kb.check` 报「切片数 > 70」（本专题新增 1 片）。
