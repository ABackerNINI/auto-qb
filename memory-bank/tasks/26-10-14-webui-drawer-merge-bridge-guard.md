# 26-10-14-webui-drawer-merge-bridge-guard — 种子详情模板合并态切换时内容消失（Teleport 目标缺失 ⇒ patch 中断）

**Status:** Done
**Added:** 2026-10-14
**Updated:** 2026-10-14 01:43
**Summary:** 用户报「种子详情模板合并态切换时内容消失」。逐帧取证定案：不是样式或数据问题，而是变体表格体桥（`<aq-dt-bridge>` 的 `<teleport :to>` 锚选择器）在**目标已离场**的那一窗被挂载 —— 布局换代（合并开关 / 门跨越）的 patch 顺序是「先拆旧分支（旧锚随之离场）→ 再挂新分支」，而父级 `v-if` 的 `dtBridgeOn` 是**拆之前**求值的（那一拍旧锚还在 ⇒ 判真）；Vue 生产版对目标缺失的 teleport **静默不挂子节点**（无警告），之后卸载它时对 `null` component 解构抛 `TypeError: Cannot destructure property 'bum' of 'e' as it is null`，**整次 patch 中断** ⇒ 抽屉停在半渲染态（桥表行归零、再开合并也回不去）。修法 = 目标存在性判据 `dtBridgeTargetOn(tab, seg)` 移进**桥组件自己的渲染拍**（与 teleport 的 mount 同拍，拿到的才是真值）+ 桥模板 teleport 加 `v-if`；并加 e2e 守阵（合并开关往返 × gc/tp 两对 × 门跨越，红绿双验）与静态守阵两钉。改动面 2 源文件 + 2 测试文件，零 API/观感变化。
**Topics:** webui-drawer-merge-bridge-guard
**Refs:** memory-bank/testing/baselines/26-10-14-0143-webui-drawer-merge-bridge-guard.md,memory-bank/pitfalls/web-ui/teleport-target-missing-patch-abort.md

## 原始请求

用户一句话报障：「修复: 种子详情模板合并态切换时内容消失」。（无复现步骤、无截图 —— 复现路径由本档取证补齐。）

## 思考过程与决策

- **先复现，不猜**：按仓库纪律用真浏览器探针（`e2e/drawer-merge.spec.mjs` 内临时探针，取证后删除）逐步骤 dump `drawer-body` 文本长度 / 每列行数 / 每宿主子节点数 + 逐步 console 错误。第一轮即锁定两个失败点：**合并开关由开转关时**（gc 对与 tp 对各一次）出现一条 `TypeError`，且 tp 对那一步单栏内容**只剩外壳 90 字符、行数 0**（用户所报「内容消失」的现场）。
- **Vue 内部栈反查**：报错栈为 `patchChildren → patchKeyedChildren → unmount → unmountComponent → unmountChildren → unmount → TeleportImpl.remove → unmount → unmountComponent(null)`。把 `vue.global.prod.js` 的压缩列号解出来对位：`Object.remove` 正是 `TeleportImpl.remove`（它遍历 `children` 逐个 `um()`），最内层 `el` 是 `unmountComponent` 对 `let{bum:r,...}=e` 解构 —— `e` 为 `null` 只可能来自「teleport 的子节点**从未挂载**」。
- **为什么从未挂载**：Vue 的 `TeleportImpl.mount` 先 `resolveTarget(props)`，取不到目标就**不挂子节点**（生产版连警告都没有，只有 dev 版打 `Invalid Teleport target`）。所以「挂载拍目标不存在」是唯一入口。
- **两条实验证伪/证真**（都留在本档，探针未进仓库）：
  1. 把 `dtBridgeOn` 里加一道 `document.querySelector` 存在性检查 → **无效**。因为父级判据在**拆之前**求值，那一拍旧锚还在文档里，判真；等桥组件真挂载时锚已被拆走。→ 否掉「父级判据加 DOM 检查」这条路。
  2. 把 `dtBridgeOn` 直接改成恒 `false`（sledgehammer）→ **零错误**。→ 证实肇事者就是桥的 teleport，且确认所改文件确实被桩服务按源文件提供。
- **定案修法**：判据必须落在**桥组件自己的渲染拍** —— 桥组件是 patch 期才挂的，那时旧分支已拆、旧锚已离场，`querySelector` 拿到的才是真值。锚稍后由 `_dtSync`（`$nextTick`）挂变体时出现 ⇒ `dtBridge` 状态变更 ⇒ 桥重渲 ⇒ teleport 归位，**内容不缺**。逐段判据（`dtBridgeTargetOn(tab, seg)`）顺带把分段桥（08 五分组「组空整节隐藏 ⇒ 锚离场」）的同型隐患一并覆盖。
- **不选「在布局换代前同步摘 on」的时序修法**：那样要同时改 `dtToggleMerge` / resize 防抖 / `drawerTab` / 换目标四条路径，且依赖 Vue 的 flush 顺序假设；而「目标不存在就不挂 teleport」是不变量式修法，一处覆盖全部四条路径（含未来新路径）。
- **范围守恒**：本缺陷是桥锚机制（计划 26-10-12-0527 U1「挂载时序四路径闸门」）**声明覆盖但实际漏测**的那条路径（合并列 × 桥变体）的补漏；计划外发现（如 `modules/webui-static-contract.md` 已超 cap 债务）一行未改。

## 实现计划

1. 探针复现 + 逐步 dump 定位失败步骤（临时探针，取证后删）。
2. Vue 压缩栈对位 + 两条对照实验（父级加 DOM 检查 / sledgehammer 关闭桥）定根因。
3. 修：`drawer_templates.js` 新增 `dtBridgeTargetOn(tab, seg)`；`tpl/xtpl.html` 桥模板 teleport 加 `v-if`。
4. 守阵：e2e 用例（合并开关往返 + gc/tp 双对 + 门跨越 + 逐点零错误断言）红绿双验；静态守阵两钉（方法存在 + 模板 v-if 存在）。
5. 收尾：档案 + activeContext 切片 + 坑档 + 基线切片 + `kb.index` 重建。

## 子任务状态表

| 子任务 | 状态 | 备注 |
| --- | --- | --- |
| 真浏览器复现 + 逐步骤取证 | Done | 探针在 `e2e/drawer-merge.spec.mjs` 内临时落地，取证后删除（未进仓库） |
| Vue 压缩栈对位 + 两条对照实验 | Done | 父级 DOM 检查无效（拆之前求值）→ 否掉；恒 false 零错 → 证实肇事者 |
| 修：`dtBridgeTargetOn` + 桥模板 teleport `v-if` | Done | 判据落在桥组件渲染拍（与 teleport mount 同拍） |
| e2e 守阵（红绿双验） | Done | 新增「合并态切换: 桥变体列换代不得抛错且内容不丢」×双皮肤；红验 = 判据恒 true 即红（报障现场重现） |
| 静态守阵两钉 | Done | `test_drawer_table_bridge_wiring`：③ 方法名入列 + ③b 判据语义钉 + ⑤ 模板 `v-if` 计数钉 |
| 收尾回写（档案/切片/坑档/基线/kb.index） | Done | 见「进度日志」末条 |

## 进度日志

- **2026-10-14 01:30（复现 + 根因）**：临时探针（`ZZPROBE`，取证后删）逐步 dump 定位到「合并开关由开转关」两处抛 `TypeError: Cannot destructure property 'bum' of 'e' as it is null`；tp 对那一步单栏 `bodyLen 90 / bodyRows 0`（修前）对 `272 / 3`（修后）= 用户所报「内容消失」的量化现场。压缩栈对位确认 `Object.remove` = `TeleportImpl.remove`、最内层为 `unmountComponent(null)`。两条对照实验：父级 `dtBridgeOn` 加 DOM 检查**无效**；`dtBridgeOn` 恒 false → **零错误**。
- **2026-10-14 01:35（修 + 守阵）**：`drawer_templates.js` 加 `dtBridgeTargetOn(tab, seg)`（`document.querySelector(dtBridgeTo(tab, seg))`）；`tpl/xtpl.html` 的 `<teleport>` 加 `v-if="$root.dtBridgeTargetOn(tab, seg.key)"`。e2e 新用例覆盖：gc 对（右列 10 树+详情）开关往返、tp 对（04 状态卡片栅格 + 07 四卡仪表）关合并后当前页签桥表行仍在、门跨越往返，每步断言零运行期错误。**红验**：判据注入 `return true` → 双皮肤均在「关合并后桥表行仍在」处红（报障现场重现）；还原即绿。静态守阵两钉同轮加。
- **2026-10-14 01:41（验证）**：`dev.e2e` 定向单文件(`e2e/drawer-merge.spec.mjs`)12 passed（双皮肤全绿）；`dev.e2e`(@fast 子集)**134 passed**；`test.one -- tests/test_webui_static_skins.py` 15 passed；`test.full` 全绿（数字见基线切片 `26-10-14-0143`）。
- **2026-10-14 01:43（收尾）**：本档案 + activeContext 切片 + 坑档 `pitfalls/web-ui/teleport-target-missing-patch-abort.md` + 基线切片 + `commands run kb.index`。`modules/webui-static-contract.md` **有意未动**（该文件已列在 cap 债务里，契约面无变化：本修法不新增变体侧接入面）。**未提交**（等用户显式指令）。
