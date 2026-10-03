# 26-10-04-backend-cross-group-conflict — 跨组文件交叉检测与紧急处置 (计划 26-10-04-0107)

**Status:** Done
**Added:** 2026-10-04
**Updated:** 2026-10-04 04:12
**Summary:** 分析 issue 26-09-22-2221(跨组文件交叉无检测, 三场景可静默覆盖已下载数据)出分步计划并全段实施完成(计划 [plans/26-10-04-0107](../plans/26-10-04-0107-plan-cross-group-file-conflict.html) 置 Done): S1 配置键 `grouping.cross_group_conflict_check` 默认关全链贯通 / S2 检测核心(`_cross_physical_key` + 四步判定, 纯内存零触盘) / S3 处置(组对去重 + 仅暂停涉事下载方 + 消除循环) / S4 Web 组视图 cross_group_conflict 标记 / S5 集成回写。新增用例 19 条, test.full 2441 passed + 4 skipped / 99% / 36.16s(基线 26-10-04-0412), 全绿零回归。issue 已置 Done(§07 修复后补充), 真机走查未做留待用户。
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
| S0 | 认领动作: sync + 复验锚点(37 项精确一致 / 4 项 ±1-3 行微漂) + issue 复验行 | 已完成 675e5071 |
| S1 | 配置键全链路 + 键面基线(154→155 键) + keys.md | 已完成 34f89338 |
| S2 | 检测核心(纯检测) | 已完成 a69e043c |
| S3 | 处置动作(暂停 + 组对去重 + 消除) | 已完成 cc6b2131 |
| S4 | Web 组视图提示 | 已完成 4267ed70 |
| S5 | 集成验证与文档回写 | 已完成 (本步, 无新代码用例) |

## 进度日志

- 2026-10-04 02:02 — 计划轮完成: 勘察 → 四项拍板 → 计划产出(52KB, 8 锚点, dark) → 主会话验收(dark / 无占位符 / 拍板全落文 / S0-S5 结构完整 / src/ 零改动) → 收尾入库。issue 26-09-22-2221 状态仍 Open(未认领), 实施待用户指派。提交时点 sync 撞「树脏挡路」(远端 908fbf28 重叠), 按行内配方 stash → sync → pop 解锁; pop 撞 `plans/_index.md` 生成物冲突(stash 场景 autoresolve 管不到), checkout HEAD + 重跑 kb.index 解决, 处置已补进 pitfalls/git/sync-pull.md。
- 2026-10-04 04:12 — **实施轮完成, S0-S5 全段落地, 档案与计划/issue 均置 Done**。五笔提交分步入库于本地分支 feat/cross-group-file-conflict(实测时点 rebase 在 develop 2ab1f6a3 之上; 后二次 rebase 到 2d2bb5e1, 提交哈希随之改写并由补正笔回写; 已 ff 合入本地 develop(S5 收尾回写 = d4ec1405), 未推送, 等用户显式提交指令):
  - **S0 认领 675e5071**: 计划 41 锚点逐点复验 —— 37 项行号精确一致, 4 项 ±1-3 行微漂(符号与语义全成立); issue §07 补复验行。计划外观察仅记录不修: decorate.js:123 前端重算 sizeMismatch 系既有有意设计, S4 实施时不可误当后端字段先例。
  - **S1 配置键 34f89338**: `grouping.cross_group_conflict_check` 默认 false 全链贯通 —— models.py GroupingConfig 加字段(missing_tag 后) + sections.py KNOWN_GROUPING_KEYS 与 bool 校验元组 + schema Field(对齐 check_missing_files) + 键面基线重生成(154→155 键, version 4 不抬 = 非破坏新增) + keys.md 回写; 3 条守卫用例。
  - **S2 检测核心 a69e043c**: 模块级 `_cross_physical_key`(normcase+normpath, 与 path_normalize 分层 —— 归组键保持词法形态的红线不变) + `_check_cross_group_file_conflicts` 四步判定(物理路径全量展开 → 交叉事件 → MISSING 豁免 → 激活警告), 接线插在 `_on_post` 内 `_handle_save_path_changes` 与 `_check_download_conflicts` 之间, 对 dirty_groups 只读不复位; 8 条用例。不变量自证: utils.py diff 为空、零触盘(仅目录级 realpath_lexical + OSError/ValueError 词法回退)、开关关首行返回。
  - **S3 处置 cc6b2131**: store.py `cross_group_conflict_warned` 组对去重集合(软信号不落盘 + reset_runtime 有意不清, 注释钉死对齐 download_conflict_warned 先例) + active 组对集 (ka,kb,paths,dl_hashes) + 处置循环严格对齐同组检查顺序(警告 → dry_run 止步 → 登记去重 → 仅暂停涉事下载方 `torrents_stop(dl_hashes)`, 绝不传整组) + 消除循环(discard 不在 active 的过期记录); 7 条用例。
  - **S4 Web 组视图 4267ed70**: views.py `_build_group_view` 组字典加 `cross_group_conflict` 布尔(由去重集合派生, 派生值后端算约定) + groups.html name 单元格组名旁 sizeMismatch 同款 `#i-warn` 标记(无新 CSS) + filters.js 未归组虚拟组补 false + grouping_mod 消除/处置两处 warned 增删显式置脏 `store.view_changed`(兜底推导链断裂, 先例 views.refresh_error_reasons); 1 条用例。
  - **边界处理**: by_hash 幽灵成员跳过(组表有快照无 → 不参与豁免与激活判定) / 3+ 组共享路径按两两规范序组对分解 / 完成侧为空显示「无」/ 相对路径斜杠混形态由 normpath 归一。
  - **与计划的偏差(均已在 issue 修复后补充留痕)**: ①计划 S3 伪代码消除段 `pair not in active` 对四元组列表恒假(字面照抄会使消除静默失效), 实现改判 `pair not in pair_paths`(其键即 active 组对集)并注释钉坑; ②计划验收示例非 bool 用例值 "yes" 实测被 parse_bool 接受为 True, 改用真非法值 "maybe"; ③S2 三条用例尾部断言随 S3 语义演进(纯检测期零动作 → S3 后 stop 恰 1 次), 测试 10 补第二做种成员使「做种侧不混入」断言非平凡; ④计划写 groups.html :47-53 系写计划时陈旧参照(该区间实为 size 单元格), S4 按文字描述落在 name 单元格组名旁; ⑤日志断言按 pitfalls/testing/log-capture.md 用直挂 logger 的 `_CrossWarnCapture` 替代 caplog(QbManager 构造链清空 root handlers, caplog.text 恒空先例)。
  - **测试数字(S5, test.full 实测)**: 2441 passed + 4 skipped / 覆盖率 TOTAL 99%(14361 语句 / 135 未覆盖 / 4864 分支 / 106 partial) / 36.16s; 新增 19 用例 = 上基线(26-10-04-0353: 2423+3)净增 19 总数、+18 passed、+1 skipped(POSIX 不误报用例在 Windows 按设计 skip), 全绿零回归。基线切片 [baselines/26-10-04-0412](../testing/baselines/26-10-04-0412-cross-group-conflict-detection.md)。
  - **未验证面**: 真机走查(`dev.run --dry-run` 验警告路径, 计划里属可选项)本轮明确跳过, 留待用户。代码事实回写: systemPatterns/main-loop.md post 相位行补「跨组文件交叉检测」(本轮新增, 一处真实漂移)。
