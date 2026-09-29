# 26-09-30-rule-dangerous-op-layer — 危险操作独立操作层 (rules → ops ← web)

**Status:** Done
**Added:** 2026-09-30
**Updated:** 2026-09-30
**Summary:** 危险操作收编计划 v3(P2' 抽取方案)全量实施: ops 层 OpsMixin(ops_recheck/ops_skip_check, R1 提交点检查 + R2 实时复核 + 保护按 source 区分), 规则/WEB 改一行委托, 右键跳检落地, webui 不 import rules 静态守阵; 基线 1801 passed / 91%。

**Topics:** rule-dangerous-op-layer

**Legacy-ID:** 无

## 原始请求

用户: 「实施计划26-09-30-0109-plan-dangerous-op-consolidation.html」—— 按计划 v3.1 实施 P1(R2 跳检实时复核 + R1 WEB recheck 提交点拒绝, 单发 + bulk 两入口)与 P2'(操作层抽取 + WEBUI 右键跳检 + webui 不 import rules 静态守阵)。§06 四决策点按计划建议拍板: D1 保护策略按来源区分(采纳) / D2 在途只读视图(不做) / D3 C3+C4 接受现状 / D4 只抽 recheck 与 skip_check。

## 思考过程与决策

- **依赖方向**: v2 收编方案(WEB 调 full_checking 提交路径)依赖做反已否决(计划 §02.2); v3 摆正为 rules → ops ← web —— 执行体与保护策略单点归 `core/mixins/ops.py` 的 OpsMixin, 两个调用方都只做委托。
- **OpsMixin 挂 manager 侧而非独立对象**(计划 §3.4): ops 依赖的 api/task_queue/state 本就挂在 manager, WEB 命令处理器 self 就是 manager, 调用零转换。
- **导入方向防环(实施中新增决策)**: ops 需要轮询常量与冷却 helper, 若反向由 full_checking import ops 会成环(ops → rules.base 触发 rules 包 __init__ → actions → full_checking)。故常量/helper 单点留在 full_checking.py, ops 从它 import; full_checking.py 头与 ops.py 头均注明「full_checking 不得反向 import ops」。
- **poll 闭包等价性红线**(计划 §3.4): 迁移后 poll 继续读 store 活记录(原地更新语义), docstring 显式禁止改为闭包缓存字段值或每次 API 直查; 由既有 test_full_checking 断言族钉住。
- **WEB recheck 回执形态**: recheck_torrent / skip_check_torrent 加入 DEFERRED_RECEIPT_COMMANDS —— handler 经 ops 提交并**自写回执**(拒绝时 error 带自解释文案「校验进行中」), 不走 RESYNC 的 defer_receipt 真值登记(校验态由快照刷新可见, 乐观 UI 本就不做 recheck)。
- **bulk recheck 不在 _BULK_ACTIONS 单次 API**: 逐 hash 经 ops_recheck(source="web") —— 在途互斥对每个 hash 生效, 聚合回执带「N 个校验进行中已跳过」; 直调 API 会给批量路径留下 C1 旁路(计划 C1 第二入口)。_BULK_ACTIONS.get 返回 None 的放行需特判 `action != "recheck"`, 否则先撞「未知动作」。
- **R2 实时复核位置**: 前置闸门之后、导出之前(计划 §3.3) —— 拒绝发生在备份与删除之前, 零副作用无孤儿备份; 复核读**客户端实时状态**(api.torrents_info), 不是快照。
- **测试桩适配 R2(实施发现)**: 4 个既有用例的桩只灌 store 不灌 client.torrents, R2 复核读客户端时误判「种子已删」—— 逐个补灌 client 或把 info 故障改为「删除生效后才开始」(test_actions delete_not_confirmed), 语义与真机一致。
- **测试 patch 目标随实现迁移**: 6 处 `patch("auto_qb.rules.actions.skip_checking/full_checking...")` 跟随实现迁到 `auto_qb.core.mixins.ops...`; `_infer_content_layout` / `_backup_torrent` 的归属改为 OpsMixin/manager。
- **路由金清单 +1**: POST /api/torrents/{hash}/skip-check(右键跳检), _GOLDEN_ROUTES 66 条(旧注释 61/63 本就漂移, 已统一); test_webui_no_rules_import 边界守阵两层口径: 操作链 4 模块禁任何 rules 引用, 其余 webui 模块禁规则根包/动作插件(rules.expr 仅限 config 表达式编辑器既有合法用途)。

## 实现计划

计划单点: [plans/26-09-30-0109-plan-dangerous-op-consolidation.html](../plans/26-09-30-0109-plan-dangerous-op-consolidation.html)(doc-status 已置 Done, colophon 记实施结果)。P1 与 P2' 实际一次落地(同轮), 与计划「P1 → P2' 顺序」无冲突。

## 子任务状态表

| # | 子任务 | 状态 |
|---|---|---|
| 1 | ops.py: ops_recheck(R1 + 冷却按 source + poll 迁移) + ops_skip_check(四阶段 + R2) + 备份/清理/布局推断随迁 | Done |
| 2 | full_checking.py 改薄(1.5/1.6 闸门 + 常量 helper 保留) + skip_checking.py 一行委托 + checking.py docstring 更新 | Done |
| 3 | OpsMixin 组合进 QbManager(mixins/__init__ + qbmanager) | Done |
| 4 | WEB handler: recheck_torrent 经 ops + 回执映射; bulk recheck 逐个经 ops + 聚合回执; skip_check_torrent 新命令 | Done |
| 5 | 后端路由 POST /api/torrents/{hash}/skip-check + 前端菜单项 + 危险确认框(skipCheckTorrent) | Done |
| 6 | 测试: test_ops.py 新建 7 条; test_checking R2 1 条; test_web 4 条(单发拒绝/bulk 跳过/右键跳检/守阵); 既有 patch 目标与桩适配 | Done |
| 7 | 全量回归 + 基线切片 + 知识库回写 | Done |

## 进度日志

- **2026-09-30**: 同步 develop@2146659 后开工。P1+P2' 全部落地(14 文件: 9 src + 5 tests, 新建 ops.py 474 行 / test_ops.py 7 条)。迁移期 12 个既有测试失败全部修复(patch 目标 6 处随实现迁移 + 4 个 R2 桩适配 + test_web 断言适配: bulk recheck 逐个提交、recheck 入延迟回执族、金清单 +1)。`commands run test.full`: **1801 passed + 3 skipped + 3 failed**(3 败为 develop 既有文档守阵: 26-09-28 键盘快捷键计划的状态词不在词表, 本轮未触碰, 按范围守恒不入池不修), 覆盖率 91%, 21.07s。基线切片 testing/baselines/26-09-30-1210-dangerous-ops-layer.md。知识库回写: rule-system/checking.md / systemPatterns/taskqueue.md / modules/rules-and-deps.md / modules/overview.md / 计划 doc 置 Done。改动未提交(等用户显式「提交」指令)。
- **2026-09-30**: 本档案初建漏 `**Topics:**` 行, test_doc_topics_complete 在 test.quick 红 —— 踩中 cap-counting「生成式跨形态视图」条(复发 +1 已记)。**为什么没命中**: 建档时把状态行四件套当必备清单照抄, Topics 行不在我的清单里, 仍靠守卫兜底而非建档时带上; 守卫本轮确实拦住了(quick 里红, 未拖到 ship 闸门, 比复发 6 晚了一道闸)。
- **2026-09-30 (提交流)**: 收到「提交」—— sync 报「落后+树脏且重叠」(远端 87d154c7: 键盘快捷键 W1-W7 + HR 触发语义两专题, 与本地交集 4 文件)。按 pipeline 处置表走 stash → sync 快进 → stash pop: overview.md / tasks/_index.md 自动并, plans/_index.md(kb.index 重建)与 test_web.py(两侧同在文件尾追加, 两块都保留)手工解决。合并后基线重测: **1829 passed + 3 skipped / 91%**(远端把 26-09-28 计划 doc-status 置 Done, 上一基线时点的 3 个既有文档守阵失败消掉; 远端 +25 条测试), test.full 24.82s。基线切片与 activeContext 数字按合并后实测更新。
