# 26-09-22-deps-version-management — 软件版本管理方案（版本号 / Tag / CHANGELOG / 发版流程）

**Status:** In Progress
**Added:** 2026-09-22
**Updated:** 2026-09-22
**Summary:** 「版本管理」立项：git VCS 健在（develop @ 49eacb8 与 gitee 齐平），空白在软件版本/发布层 —— 本地与 gitee 0 tag、无 CHANGELOG、无发版流程、版本号双源已漂移（pyproject "0.1.0" vs `__init__.__version__` "0.2.0"）。方案已出待拍板：0.x 语义化 + `__init__` 单源（hatchling regex 动态接线）+ 手工三步发版 + Keep a Changelog + 打 v0.2.0 基线 tag；3 个决策点待用户拍板，批准后阶段 0（不涉码）先行。

## 原始请求

用户（2026-09-22 22:57）：「当前项目没有版本管理, 分析项目可以使用哪些版本管理方案, 各方案的对比, 产出一个方案文档」。对应 `想法.md` L281 待办「版本管理」与 activeContext「下一步候选」同名条目。

## 思考过程与决策

- **前提核实**：用户口径「没有版本管理」先与仓库事实对表 —— git 健在（develop @ 49eacb8 与 gitee/develop 齐平，`preflight.py --check-started` PASS，工作区净，双远端齐全），故按「软件版本号 / 发布管理」立项；方案 §01 显式写明这层口径，若用户原意是 VCS 选型，现状盘点一节即答案（git 已被托管 / AI 工具链 / 多 clone 工作流锁定，无重选空间）。
- **关键取证**（2026-09-22 23:10–23:18 实测）：版本号双源漂移 —— pyproject `version = "0.1.0"` vs `src/auto_qb/__init__.py:18` `__version__ = "0.2.0"`；tag 本地 0 + `git ls-remote --tags gitee` 空；github `ls-remote` 代理拒连（报告一次不重试，按既有口径）；README 无版本提及；classifiers = Beta。
- **立档查重**：本 clone `tasks/_index.md` 无同名 slug；跨 clone `ls ../auto-qb*/memory-bank/tasks/` 无命中（2026-09-22 23:1X 实测）。
- **领域取 deps**：沿用 `26-09-15-deps-env-modernization` 先例（uv / pyproject 打包元数据类工作归 deps）。
- **方案取舍**：载体否决「pyproject + 源码双写」（漂移已实证、违反单点事实源），推荐 V2（`__init__` 单源 + hatchling regex 动态）——显示路径零改动（`tray/app.py` / `webui/server/common.py` 照旧 import `__version__`），运行时零 metadata 依赖；发版流程否决 python-semantic-release 类自动定版（要求 conventional commits，与 gitmoji + 中文提交规范冲突），起步用手工三步；CHANGELOG 用 Keep a Changelog + gitmoji 映射。

## 实现计划

- 方案文档：[memory-bank/plans/26-09-22-2318-version-management-plan.html](../plans/26-09-22-2318-version-management-plan.html)（现状盘点 / 目标约束 / 版本号·载体·流程三层对比 / 三阶段落地 / 风险 / 3 个决策点）。
- **阶段 0（不涉码，拍板即可做）**：① 建 CHANGELOG.md（Keep a Changelog 骨架 + [0.2.0] 基线段）② tag v0.2.0 @ 49eacb8 + show-ref 核对 ③ push gitee 显式 ref + `ls-remote --tags` 判定，github 尝试一次 ④ 发版三步与 `fetch --tags` 约定回写 conventions/collaboration.md。
- **阶段 1（涉码，单独立项走认领流程）**：pyproject `dynamic = ["version"]` + `[tool.hatch.version]` regex 接线；SemVer 正则守阵（红验后合入）；`cli.py` 加 `--version`；（可选）uv.lock 版本一致性守阵。
- **阶段 2（按需，不排期）**：`scripts/release.py` 前置校验 + 一条龙；git-cliff 半自动 changelog（regex 自定义解析，官网确认在维护）；Gitee / GitHub Release 页。

## 子任务状态表

| 子任务 | 状态 |
|---|---|
| 现状取证与三层方案对比 | 已完成（2026-09-22） |
| 方案文档产出（26-09-22-2318） | 已完成（2026-09-22） |
| 决策点 ①基线 tag 时机 ②版本载体 ③CHANGELOG 档位 | 待用户拍板 |
| 阶段 0（CHANGELOG + 基线 tag + 约定回写） | 待拍板后 |
| 阶段 1（hatch 接线 + 守阵 + --version，单独立项） | 待拍板后 |
| 阶段 2（脚本化 / git-cliff / Release 页） | 未排期 |

## 进度日志

- 2026-09-22 23:18 会话：立项取证（git 健康度 / tag / 双远端 / 双源漂移）+ 三层方案对比 + 方案文档产出 + 本档案建立。全量测试实测 **1189 passed + 1 skipped in 29.66s**（TMPDIR=R:/Temp/auto-qb/tests，exit 0，基线不变；本轮未动任何代码，数字为环境基线确认）。等待决策点 ①②③ 拍板。
- 2026-09-22 23:47 会话（用户令「提交」）：预检发现主线领先 9 提交（另一 clone 的 src 布局归拢 W1–W4b + W5 回写），按 [pitfalls/git/history-integration.md](../pitfalls/git/history-integration.md)「先同步远端、后提交」流程合流（备份 .git 至 R:/Temp/auto-qb/git-backup-20260922-2343 → 移出 2 个改动文件 → ff-only 至 d4dea8b → 施回），全程零 merge/rebase 提交；方案内路径引用按新布局校正（ui.py→tray/app.py、web/→webui/server/、__init__ 行号 14→18），漂移事实复验不变（pyproject "0.1.0" vs __version__ "0.2.0" @ :18，tag 仍 0）。合流后树全量复测 **1189 passed + 1 skipped in 27.63s**（--no-cov，exit 0）。
