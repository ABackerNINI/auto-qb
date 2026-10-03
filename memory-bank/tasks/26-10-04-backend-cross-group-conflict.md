# 26-10-04-backend-cross-group-conflict — 跨组文件交叉检测与紧急处置 (计划 26-10-04-0107 已出, 待实施)

**Status:** Open
**Added:** 2026-10-04
**Updated:** 2026-10-04 02:02
**Summary:** 分析 issue 26-09-22-2221(跨组文件交叉无检测, 三场景可静默覆盖已下载数据)出分步修改计划 [plans/26-10-04-0107](../plans/26-10-04-0107-plan-cross-group-file-conflict.html): 主会话拆解后 Explore 勘察 + 用户四项拍板 + general-purpose 撰写。关键发现 = issue 旧锚点因 kernel-module-refactor 全部漂移(grouping_mod.py / infra/utils.py / 相位广播), 检测可基于 store.groups/group_sizes 内存数据零新增 qB 请求。四项拍板: 独立开关 `grouping.cross_group_conflict_check` 默认关 + 三场景全检(含别名解析走 realpath_lexical) / 仅暂停涉事下载方 / 任一侧 MISSING 即豁免 / 暂停 + Web 组视图提示。计划 S1-S5(配置键全链路 / 检测核心 / 处置动作 / Web 组视图 / 集成回写)待实施, issue 仍 Open 未认领。
**Topics:** backend-cross-group-conflict
**Refs:** memory-bank/plans/26-10-04-0107-plan-cross-group-file-conflict.html, memory-bank/issues/26-09-22-2221-feat-cross-group-file-conflict.html

## 原始请求

用户指令: 「先拆解任务, 然后派子智能体分阶段依次实施下面的任务, 强关联的阶段/步骤/项可以合并, 特大任务需要拆分成稍小任务防止子智能体长任务 O(n^2) 的 token 消耗和出错后进度全部丢失, 不要并列执行可能超并发, 一个一个来, 待拍板的先询问, 你只负责委派总结, 不负责实际实施, 完成后等待提交指令. 子智能体非正常失败 3 次后不要继续尝试, 停止任务等待人工介入. 任务: 分析 issue 写一份分步修改计划: 26-09-22-2221-feat-cross-group-file-conflict.html」—— 本会话只到「计划产出 + 入库」, 实施等用户后续指派。

## 思考过程与决策

- **拆解**: 四阶段串行(勘察 Explore → 拍板 AskUserQuestion → 撰写 general-purpose → 主会话验收), 一次只派一个子智能体防超并发; 每阶段非正常失败 3 次即停等人工(实际 0 次; 阶段 3 派发撞 1 次「user concurrency limit exceeded」宿主并发上限, 用户「继续」后重试成功, 不计任务失败)。
- **勘察两大发现**: ①issue 取证(2026-09-22)后代码库经历 kernel-module-refactor, 锚点全漂移 —— `mixins/grouping.py` → `core/modules/grouping_mod.py`(`group_key_of` :41 / `_check_download_conflicts` :373, 由 `_on_post` 相位驱动), `utils.py` → `infra/utils.py`(path_normalize :477-488), qbmanager 直调点改为相位广播(qbmanager.py:842); ②检测零新增 qB 请求 —— store.groups/group_sizes 全内存驻留, 物理路径展开纯内存 O(总文件数)。
- **四项拍板(2026-10-04, 用户)**: D1 配置 = 独立开关默认关 + 三场景全检(部分重叠 / normcase 大小写 / realpath_lexical 别名, Mapped 部署自动退化词法); D2 粒度 = 仅暂停涉事下载方(单 hash); D3 MISSING = 任一侧带 missing_tag 即豁免(对齐同组 mixed「重下补救合法」); D4 附加 = 暂停 + Web 组视图提示(用户改判, 未取推荐「仅暂停」)。
- **撰写子智能体复用了中断草稿**: plans/ 已有一份当天 01:07 同名未跟踪文件(此前中断产出), 未推倒重写, 逐点对照源码复验全部锚点后修订定稿, 并修正约 7 处漂移行号(均当日实证)。
- **两个计划内细化**: 去重粒度收窄为组对 `(key_a, key_b)`(防刷屏, 警告按组对聚合, 路径展示前 3 处 + 等 N 处); 全量展开加「dirty 空即短路」门(静止库零成本, 不破坏独立于 dirty 的拍板语义)。
- **归一层红线**: 大小写折叠 / 别名解析只能加在跨组检测自己的物理 key 归一层(`_cross_physical_key`), 严禁改 `path_normalize` 本身(分组键单一事实源, qb_capture.py 也 import, 还供 match_path_patterns 与 fs 校验)。

## 实现计划

单点: [plans/26-10-04-0107-plan-cross-group-file-conflict.html](../plans/26-10-04-0107-plan-cross-group-file-conflict.html)(§05 分步实施 S1-S5, 锚点行号取证 2026-10-04)。S0 认领动作(sync + 复验锚点 + issue 留复验行, 不计步) → S1 配置键全链路(models / sections 校验 / schema Field / 键面基线 test.keys-update / keys.md) → S2 检测核心(纯检测不处置, 归一层 + 全量展开 + 交叉判定 + MISSING 豁免, 仅日志可独立验证) → S3 处置动作(暂停涉事下载方 + 组对去重集合 + 消除清除 + reset_runtime「不清」决策) → S4 Web 组视图提示(_build_group_view 字段 + 前端渲染) → S5 集成验证与文档回写(test.full 基线 / issue 留痕 / memory-bank 回写)。

## 子任务状态表

| 步骤 | 内容 | 状态 |
|---|---|---|
| S0 | 认领动作: sync + 复验锚点 + issue 复验行 | 待实施 |
| S1 | 配置键全链路 + 键面基线 + keys.md | 待实施 |
| S2 | 检测核心(纯检测) | 待实施 |
| S3 | 处置动作(暂停 + 组对去重 + 消除) | 待实施 |
| S4 | Web 组视图提示 | 待实施 |
| S5 | 集成验证与文档回写 | 待实施 |

## 进度日志

- 2026-10-04 02:02 — 计划轮完成: 勘察 → 四项拍板 → 计划产出(52KB, 8 锚点, dark) → 主会话验收(dark / 无占位符 / 拍板全落文 / S0-S5 结构完整 / src/ 零改动) → 收尾入库。issue 26-09-22-2221 状态仍 Open(未认领), 实施待用户指派。提交时点 sync 撞「树脏挡路」(远端 908fbf28 重叠), 按行内配方 stash → sync → pop 解锁; pop 撞 `plans/_index.md` 生成物冲突(stash 场景 autoresolve 管不到), checkout HEAD + 重跑 kb.index 解决, 处置已补进 pitfalls/git/sync-pull.md。
