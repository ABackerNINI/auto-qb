# 3199 —— 详情面板桥锚: 合并态切换内容消失修复(Teleport 目标判据)执行基线

> 摘要: 任务档案 [26-10-14-webui-drawer-merge-bridge-guard](../../tasks/26-10-14-webui-drawer-merge-bridge-guard.md)。用户报「修复: 种子详情模板合并态切换时内容消失」→ 真浏览器取证定案 = 变体表格体桥的 `<teleport>` 在**目标已离场**那一窗被挂载(Vue 生产版静默不挂子节点, 卸载时对 `null` component 解构抛 `TypeError`, **整次 patch 中断** ⇒ 半渲染态)。修法 = 目标存在性判据 `dtBridgeTargetOn(tab, seg)` 落在**桥组件自己的渲染拍** + 桥模板 teleport `v-if`。改动面: `src/auto_qb/webui/static/shared/drawer_templates.js` + `src/auto_qb/webui/static/shared/tpl/xtpl.html` + `e2e/drawer-merge.spec.mjs`(新 e2e 用例 ×双皮肤) + `tests/test_webui_static_skins.py`(静态守阵两钉)。
> 基线时间: 2026-10-14 01:43

**Refs:** memory-bank/tasks/26-10-14-webui-drawer-merge-bridge-guard.md

上一基线: memory-bank/testing/baselines/26-10-13-2150-backend-hr-dup-code-fix.md

## 验收数字

- `test.full`: **3199 passed + 4 skipped, 0 failed** / 覆盖率 `TOTAL 16770 157 5708 140 99%`。
- 耗时: pytest 37.89s ~ 50.10s(墙钟 39.8s ~ 52.1s; 两次采样, 同一棵树、同一数字 —— 耗时随机器负载波动, 以通过数与覆盖率为准)。
- 本轮自身**未新增 pytest 用例**(新守阵是既有 e2e spec 内的新用例 + 既有静态守阵函数内的新断言, 前者不进 pytest 收集), 故 passed 的差值不来自本轮 —— 它来自上基线之后合入的提交; 逐位差值 `commands run kb.baseline -n 2` 现列。
- `dev.e2e`(@fast 子集, 前端门禁): **134 passed / 0 failed**(双皮肤)。
- `dev.e2e` 定向单文件(`e2e/drawer-merge.spec.mjs`, 抽屉合并 spec): **12 passed**(双皮肤, 含本轮新用例)。
- Linux 侧未重测(改动为纯前端静态资源 + 前端守阵, 无平台分支)。

## 本波改动面

- **修**: `drawer_templates.js` 新增 `dtBridgeTargetOn(tab, seg)`(目标存在性判据, 落在桥组件渲染拍 —— 与 teleport 的 `mount` 同拍); `tpl/xtpl.html` 桥模板 `<teleport v-if="$root.dtBridgeTargetOn(tab, seg.key)">`。
- **守阵 ×1 e2e 用例**: `e2e/drawer-merge.spec.mjs` 「合并态切换: 桥变体列换代不得抛错且内容不丢」—— gc 对(内容列 10 树+详情)开关往返、tp 对(04 状态卡片栅格 + 07 四卡仪表)关合并后当前页签桥表行仍在、门跨越往返; 每步断言零运行期错误。**红验**: 判据注入 `return true` → 双皮肤均在「关合并后桥表行仍在」处红(报障现场重现), 还原即绿。
- **静态守阵两钉**: `tests/test_webui_static_skins.py::test_drawer_table_bridge_wiring` —— ③ 方法名入列(`dtBridgeTargetOn`)+ ③b 判据语义钉(`document.querySelector(sel)`)+ ⑤ 桥模板 teleport `v-if` 计数钉(=1)。
- **回写**: 任务档案 + activeContext 切片 + 坑档 `pitfalls/web-ui/teleport-target-missing-patch-abort.md` + 本基线切片 + `kb.index` 重建。`modules/webui-static-contract.md` 有意未动(已在 cap 债务内, 且契约面无变化)。

## 已知偏差 / 移交

- 无行为面偏差: 判据只**跳过**目标不存在的 teleport(那时本就无内容可显), 锚一出现即由 `dtBridge` 状态变更触发重渲归位; 正常路径(初开/切页签/换目标/合并双列挂载)判据恒真, 逐段与旧行为等价。
- 移交: 分段桥(08 五分组)的「组空整节隐藏 ⇒ 锚离场」同型隐患随逐段判据一并覆盖, 但**未单独落 e2e 用例**(本轮 e2e 只走单锚变体); 若后续要钉, 可扩 08 分组过滤路径。
