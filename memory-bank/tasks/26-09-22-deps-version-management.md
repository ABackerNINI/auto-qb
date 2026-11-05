# 26-09-22-deps-version-management — 软件版本管理方案（版本号 / Tag / CHANGELOG / 发版流程）

**Status:** In Progress
**Added:** 2026-09-22
**Updated:** 2026-11-06
**Summary:** 「版本管理」立项：git VCS 健在，空白在软件版本/发布层。v1 方案（0.x 语义化 + `__init__` 单源 + 手工三步发版 + Keep a Changelog）经六轮 grilling（2026-11-05–11-06）改版为 **v2 机械化发版管线**：minor/patch 机器算+agent 执行、major 人工三判据；hash 尾双路径（源码运行时派生/wheel 构建期注入）；develop=工作主线/master=发布线双分支（ff-only，tag/Release 锚 master）；本地全测门（test.full+dev.e2e+real.suite，变异测试不进门）+ GitHub CI 全绿门；三层载体（release skill 规程+脚本本体 / .commands 薄引用 / conventions 口径）。16 项拍板见计划 v2 §09，待实施（阶段 1 八步）。
**Topics:** deps-version-management

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
| 方案文档产出（26-09-22-2318） | 已完成（2026-09-22）；v2 改版（2026-11-06） |
| v1 决策点 ①基线 tag 时机 ②版本载体 ③CHANGELOG 档位 | 已完成/并入 v2（tag 已打 2026-09-23/25；载体与 CHANGELOG 档位由 v2 拍板覆盖） |
| grilling 六轮 16 项拍板（v2 机械化改版：触发词/分工/hash 双路径/双分支/CI 门/全测门/三层载体） | 已完成（2026-11-06） |
| 阶段 1 八步（单源接线+issue 1408 清偿 / CHANGELOG 骨架 / 决策器+守阵 / bump-my-version / release skill+commands / 管线首跑补发 0.3.0 / 口径回写） | 待认领实施 |
| 阶段 2（Release 页 token / exe 立项 / git-cliff 评估 / 1.0 里程碑） | 未排期 |

## 进度日志

- 2026-09-22 23:18 会话：立项取证（git 健康度 / tag / 双远端 / 双源漂移）+ 三层方案对比 + 方案文档产出 + 本档案建立。全量测试实测 **1189 passed + 1 skipped in 29.66s**（TMPDIR=R:/Temp/auto-qb/tests，exit 0，基线不变；本轮未动任何代码，数字为环境基线确认）。等待决策点 ①②③ 拍板。
- 2026-09-22 23:47 会话（用户令「提交」）：预检发现主线领先 9 提交（另一 clone 的 src 布局归拢 W1–W4b + W5 回写），按 [pitfalls/git/history-integration.md](../pitfalls/git/history-integration.md)「先同步远端、后提交」流程合流（备份 .git 至 R:/Temp/auto-qb/git-backup-20260922-2343 → 移出 2 个改动文件 → ff-only 至 d4dea8b → 施回），全程零 merge/rebase 提交；方案内路径引用按新布局校正（ui.py→tray/app.py、web/→webui/server/、__init__ 行号 14→18），漂移事实复验不变（pyproject "0.1.0" vs __version__ "0.2.0" @ :18，tag 仍 0）。合流后树全量复测 **1189 passed + 1 skipped in 27.63s**（--no-cov，exit 0）。

- 2026-11-06 01:23 认领 issue 26-09-21-1408(Open→In Progress 双向链) + 计划 v2 定稿: 六轮 grilling 16 项拍板(机械化发版管线八步/三层载体 skill scripts+commands 薄引用/hash尾双路径/双分支 develop工作线-master发布线/本地全测门变异不进门/CI门 master run 全绿+发版轮镜像例外); 阶段1 八步待实施, 本轮零代码改动

- 2026-11-06 02:33 评审面修复轮: S0-S5 增量(f31c4082)收口评审 —— review.pack 分面档(769行)三面串行, 14 发现 review.check 14/14 过, blocker 0/major 2/minor 9/nit 3, 相关性全部相关无一入池, 当场全修(breaking 判定严格化/停手指引可达/JSON+草稿合流/单行错误契约/捕获组校验/UTF-8 锁/⚠️ 去除/bumpversion 守阵 major/错误路径契约 major/测试缺口 5 面, 守阵 30→41); 计划 §6.2 步骤③补 uv sync 刷元数据; test.quick 5392 绿; c9a190d2 入库

- 2026-11-06 03:10 S6 落地: wheel build hook(hatch_build.py BUILD_ID 侧车 .dist-info/extra_metadata/, 版本保持纯 SemVer) + release skill 规程(SKILL.md 八步管线/停手清单/降级/幂等) + 5 管线脚本(apply_bump/ff_merge/tag_release/ci_gate/release_page, 全零项目事实) + .commands/release 包 7 task; 真机冒烟 suggest(minor->0.3.0)与 build(BUILD_ID ga3ccf82e 落位)通; 守阵 20 条(管线)+61 全体, test.quick 5412 绿; 发现 uv build 全量=sdist两段式丢 git 上下文陷阱(已记 skill); 引擎 run 列表=命令串+<args> 占位机制已吃透; 另发现 Windows CI 存量红(ced9a88a 起)待入池请示

- 2026-11-06 04:20 S6 收口评审修复轮: 分面档三面 27 条全修(blocker 0/major 4/minor 18/nit 5, 引文核验 25 逐字+2 邻近=27/27 零幻觉) —— 发版轮 github 推送机械落点(release.merge 二跑+SKILL 05 两跑修正虚假保证)/release_page 优先级 bug+Bearer 头+tag 校验/ff_merge 剥壳/ci_gate 解析收口/hatch atexit/智能默认链与 hatch_build 守阵补全; 另入池 issue 26-11-06-0321(Windows CI 存量红, 用户拍板); gh 已装(winget 2.103.3, token 用户自理); 守阵 86+全量 5427 绿
