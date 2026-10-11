# 3122 —— WEBUI 抽屉重构 W5 变体退役与声明式密度档(26-10-11-2106 计划)

**Refs:** memory-bank/tasks/26-10-11-webui-drawer-refactor.md,memory-bank/plans/26-10-11-2106-plan-webui-drawer-refactor.html,memory-bank/testing/baselines/26-10-12-0117-webui-drawer-refactor-w4.md

> 摘要: 计划 `memory-bank/plans/26-10-11-2106-plan-webui-drawer-refactor.html`(专题 `webui-drawer-refactor`)的 **W5** —— 15 个过程式变体(`shared/drawer_tpl/` 15 文件 5739 行)整体退役, 「换版式」收敛为每页签 2 档的**声明式密度档**(classic / compact, `DRAWER_DENSITY` 一张表驱动; 旧 id 显式迁移 tall→classic / low·collapsed→compact / 脏值→classic); 插件挂载机械(`_dtMount*`/`_dtSync`/`_dtNotify`/`_dtRender`/`dtHtml` 等)全删, 换档走 Vue 响应式; 结构开关(raw/hint)走模板 `v-if` 真隐藏。判据: ① `test.full` 对账吻合(收集清单 diff 逐条闭合); ② e2e = W4 基线 166 − 退役 14 + 新增 4 = 156, 零失败; ③ 红验两条均非退化; ④ 验收动词(档位切换生效并持久化 / 旧 id 不报错有去向)各有守阵 + e2e 钉。
> 基线时间: 2026-10-12 02:24

## test.full 实测

- 分支: `develop`(HEAD `acd0e26f`; 工作树含 W2+W3+W4+W5 四轮改动, 均未提交)
- 命令: `commands run test.full`(Windows, 单次采样; 本轮 28.6s)
- **实测 (Windows)**: **3122 passed + 4 skipped, 0 failed, 覆盖率 TOTAL 99%**
  (16517 语句 / 151 未覆盖 / 5626 分支 / 134 partial —— 与 W4 基线四项逐位不变)
- **对账(worktree 收集清单 diff, 逐条闭合)**: HEAD `acd0e26f` 收集 3134(= 3130 passed + 4 skipped); 工作树 3126 = 3134 **+1**(W3 未提交守阵 `test_frontend_drawer_form_judge_single_point`, W4 切片已记)**+1**(本轮新增 `test_drawer_tpl_facility_retired`)**−10**(变体专用守阵退役: width_discipline / card_uniform_height / field_icons / scrollleft_restore / per_tracker_reannounce / keyboard_roving / no_singleton_shadowing / cross_seed_fold / render_error_fallback_classic / seed_reentry_variant_remount)—— 无其他漂移, passed 3130+1−10 = **3122** ✓。
- **守阵改动(同轮改版, 不放宽)**: `test_drawer_tpl_registry_wiring` 改密度档接线钉; 七份守阵文件的变体读取面同轮改(a11y 失败标记 / reannounce torrentCmd 兜底 / 右键菜单无插件机械 / page_guard `if (!s) return;` / traffic 切片锚等), 断言口径未放宽(154 passed + 2 skipped 收口轮)。

## e2e 实测

- 命令: `commands run dev.e2e`(Windows; 桩由 webServer 自动起; 4.0m)
- **实测 (Windows)**: **156 passed + 0 failed + 10 skipped**
- **对账**: W4 基线 **166** − 退役 **14**(4 条变体专用 spec, 经 `--list` 实数: dt11-sticky 1 + peers-columns 3 + sticky-flush 2 + trackers-reannounce 1 = 7 用例 × 2 皮肤)+ 新增 **4**(`drawer-density.spec.mjs` 2 用例 × 2 皮肤)= **156** ✅ 逐位对齐。
- ⚠ **对账插曲**: 首轮 dev.e2e(154 passed + 2 failed)的 2 条失败是**红验注入窗口撞车** —— dev.e2e 运行期间恰覆盖红验 RC2 的注入(compact raw→true), 「紧凑档原始键值区 v-if 真隐藏」即红, 与注入缺陷表现一致; 源码还原后重跑全绿。教训: **红验注入与长跑验证不得并行**(此前波次均为串行, 本轮并行省时撞出假红)。
- **本轮新增**: `e2e/drawer-density.spec.mjs` —— ① 旧变体 id 预置迁移(general=01/trackers=06/peers=zz/content=10 混预置 → DOM 逐页签断言档位生效 + runtime error guard 零报错; traffic 页签受 `qbTrafficOn` 门控不在桩内, 该腿由静态 node 电池承接); ② 右键切档 + 持久化(紧凑 → `dd-compact` + 结构开关真隐藏 + `autoqb.ui.drawerTpl` 落盘不牵连 content → 刷新恢复 → 经典回切反向)。
- **改版**: `drawer-merge.spec.mjs` 用例⑤(右键各列模板选择 → 各列密度档: 紧凑/经典 + `dd-compact` + 结构开关断言; 右列空白归列回归保留); `drawer-tables.spec.mjs` 用例③(变体/经典单一挂载点 → 菜单锚点解析**效果判别**: 选紧凑须落 trackers 记忆而非 general + 插件宿主负 pin)。
- **退役**: `drawer-content-dt11-sticky` / `drawer-peers-columns` / `drawer-peers-sticky-flush` / `drawer-trackers-reannounce`(变体表格专属几何/能力; 等价不变式由经典 aq-table e2e 与静态守阵承接, dt06 逐行倒计时的**逐行口径**无等价物, 见任务档案待办)。

## W5 验收动词 × 红验(「按下去到底行不行」的记录)

| 验收件 | 断言位置 | 红验注入 | 结果 |
|---|---|---|---|
| 旧 id 显式迁移(tall→classic) | `test_drawer_tpl_classic_default` node 电池 + `test_drawer_tpl_registry_wiring` 迁移映射钉 | **RC1**: general legacy `"01"` 改指 compact | rc=1 (红 ✓; 电池报「旧 tall id(01/04/07/10/13) → classic」「旧 id 01 显式迁移为 classic」两条) |
| 结构开关真隐藏(raw) | `_DT_DENSITY_NODE_PROBE` drawerTier 开关断言 + wiring | **RC2**: `DD_TIERS.compact.raw` 改 true | rc=1 (红 ✓; wiring + 电池双红) |
| 档位切换生效并持久化 | `drawer-density.spec.mjs` ② + `test_drawer_tpl_classic_default` | (e2e 真手势覆盖, 未重注) | — |
| 插件机械不得复活 | `test_drawer_tpl_facility_retired`(活代码形态锚定) | (新增退役确认阵, 注入即红的机理同 W4 教训: 锚代码形态非裸字符串) | — |

## 风险 / 观察

- **00-density 密度 CSS 与 00-core 合并 CSS 同一 W6 债务**: `dd-compact` 收紧规则仍由 `drawer_templates.js` 的 `dtInjectCss("00-density")` 注入 —— W6 退役该文件时与 00-core 的 `.drawer-split` 族一并迁三皮肤 CSS。
- **drawer_templates.js 只余选择层**(624→约 250 行): 菜单选项源 / 读侧归一 / 显隐判据 / 密度 CSS 四件 —— W6 整文件退役时的迁移清单已写进文件头注(菜单/读侧/判据迁 drawer.js, CSS 迁三皮肤)。
- **dt06 逐行汇报倒计时能力随变体消失**: 经典 trackers 列表无逐行「下次汇报」列(静态守阵 `test_drawer_tpl_trackers_per_tracker_reannounce` 亦随退役删除) —— 若用户需要该口径, 需在经典列表上加列(新需求, 不属重构范围), 已在任务档案待办注明。
- **traffic 页签的密度档 e2e 盲区**: 流量页签按钮 `v-if="qbTrafficOn"` 桩服务默认不启用, 档位迁移/切换的 e2e 断言覆盖 general/trackers/peers/content 四页签; traffic 腿由 `_DT_DENSITY_NODE_PROBE` 的 normalize/tierOf 断言静态承接(`.dt-traffic-main` 挂类逻辑与四页签同一条描述符路径)。
- **对账纪律(沿用 W4)**: 基数可能因其他会话的提交漂移 —— 遇 passed 数与预期差, 先 worktree 收集清单 diff 定位再下结论; **红验与长跑验证串行**执行(本轮实证)。
- **债务(承接, 不拦提交)**: `modules/webui-static-contract.md` 超 evergreen cap(W2–W5 各加一条, 债务继续加深); `kb.check` 切片数 > 70。两项均需另开新会话收口(`doc.caps -- --strict` / 切片归档)。
