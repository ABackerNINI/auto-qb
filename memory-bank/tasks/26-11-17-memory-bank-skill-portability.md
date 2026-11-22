# 26-11-17-memory-bank-skill-portability — 自制 skill 轨道可移植性改造

**Status:** Done
**Added:** 2026-11-17
**Updated:** 2026-11-18
**Summary:** 自制 skill 轨道可移植性改造: 三波次 S1-S11 全部实施+分批评审闭环入库 —— 配置化/摘链恒绿/fnmatch 化/模板骨架/轨道 runbook/lane 外置/每 skill PORTING/sync 配置化/收口五条验收; 配套合流适配与 5 件观察建档
**Topics:** memory-bank-skill-portability
**Refs:** memory-bank/plans/26-11-17-0010-plan-skill-portability.html, memory-bank/reports/26-11-17-0010-report-skill-portability.html, memory-bank/testing/baselines/26-11-18-0041-memory-bank-skill-portability.md

## 本篇只回答

自制 skill 轨道(skill 目录 + commands 引擎 + `.commands/` 包 + sync 脚本 + KB 数据件骨架 + PORTING)的可移植性改造: 改造方案与执行进度到哪了。方案与拍板单点在计划, 摩擦证据单点在收编报告 —— 本篇只记「怎么修、修到哪」。

## 原始请求

1. 自制 skills 的可移植性改造: skills 需要尽量通用, 理论上移植后不需要修改 skills 本身(表述/代码等), 只需要修改配置。
2. `PTSKIT-farm-helper` 中包含一次真实移植示例, 其 `docs/skill-portability-report.md` 可做参考。
3. grilling 然后出一个可移植性改造计划。
4. (grilling R1) 报告收编: 用户授权 copy 进本仓。
5. (grilling R3/R4) 每个 skill 需要有一个移植帮助文档; 帮助文档中需要对新项目/正在开发中的项目做移植指导, 特别是后者; 配置/帮助文档放相应子目录, 不放 skill 根目录。

## 思考过程与决策

- 四轮 grilling(D1-D20)全部拍板, 结论表与依据单点: `memory-bank/plans/26-11-17-0010-plan-skill-portability.html` §06。
- 关键口径: 改造单位=轨道级(报告 §2.6-1 实证一半工作量在 skill 外); 配置分散自管+宽容回落; fail-closed 守卫摘默认链改显式挂载; red_lines 升级 glob; review_lane 留包内做纯数据外置(支持存量评审); 每 skill 一份 `references/PORTING.md`(双场景, 重点存量项目); 验收五条全收, 场地=仓内沙箱(跨仓红线零消耗)。
- 本轮(立档轮)零代码改动: 报告收编(D6)+计划入库+本档案; S1-S11 未开工。

## 实现计划

计划 `26-11-17-0010-plan-skill-portability.html` §04 三波次 S1-S11(每步验收判据见计划, 此处不重抄):

- 波次 1 (P0 防复发): S1 memory-bank 配置化 / S2 锚守卫摘链+空库恒绿审计 / S3 全包 rmtree 复核。
- 波次 2 (P1 降手工): S4 红线 glob 化 / S5 PORTING 轨道 runbook / S6 配置模板四件+数据件骨架三件 / S7 review_lane 数据外置 / S8 每 skill PORTING.md / S9 sync 配置化。
- 波次 3 (P2 机械面+收口): S10 出厂配置环境中立 / S11 沙箱重放+grep 白名单审计收口。

## 子任务状态表

| 步 | 内容 | 状态 |
|---|---|---|
| R0 | 报告收编+grilling 拍板+计划入库 | Done(2026-11-17) |
| S1 | memory-bank 配置化(config/project.toml + 宽容回落) | Done(2026-11-17, cd1bfcc5) |
| S2 | 锚守卫摘链+kb.check 空库恒绿全链审计 | Done(2026-11-17) |
| S3 | 全包 rmtree/unlink 复核 | Done(2026-11-17) |
| S4 | red_lines/warn_lines glob 化+存量迁移审计 | Done(2026-11-17) |
| S5 | PORTING 升级轨道 runbook(双场景, 重点存量) | Done(2026-11-17, 4323d5f9) |
| S6 | 出厂配置模板四件+数据件骨架三件 | Done(2026-11-17, ad82b1ef+fc1d2193) |
| S7 | review_lane 数据外置 lane.toml(存量评审开箱) | Done(2026-11-17) |
| S8 | 每 skill references/PORTING.md | Done(2026-11-17, 6ef64c16) |
| S9 | sync 配置化(.config/sync.toml) | Done(2026-11-17, 53ce6fb9) |
| S10 | 出厂配置环境中立(uv→python3) | Done(2026-11-17, 随 S6a 出厂设计吸收, 模板面 run 行零 uv) |
| S11 | 沙箱重放+grep 白名单审计收口 | Done(2026-11-17, 收口轮 ①③④ 过; ② 经批9b 四处外置配置后 grep 复验操作性零命中, 用户拍板) |

## 进度日志

> 已外迁: R0 / S2+S3 / S4 / S7 / S1-S10 波次实施轮次全文 → [attachments/26-11-17-memory-bank-skill-portability-progress-archive.md](attachments/26-11-17-memory-bank-skill-portability-progress-archive.md)(2026-11-22 cap 清零)

> 已外迁: S11 收口轮全文 → [attachments/26-11-17-memory-bank-skill-portability-s11-archive.md](attachments/26-11-17-memory-bank-skill-portability-s11-archive.md)(2026-11-22 cap 清零)

### 批9b · 四处操作性命中外置配置 (2026-11-17, 用户拍板「全部外置配置, 照 S1 同款模式」)

- **外置1 nav_data**: `REPO_DENY` 常量 → `DEFAULT_REPO_DENY = (".git", ".env")`(通用默认, 零项目词)+ `effective_repo_deny()` 现读 `<skill>/config/project.toml` `[nav] repo_deny`(server 30s 轮询下改配置即生效); 缺失/形态不对 → 回落默认 + stderr 必打 `[KB-CONFIG]` 提示一次(免轮询刷屏); 显式空列表 = 合法配置(全放行不提示, 口径同 siblings); 坏 TOML 异常上抛 fail-fast。本仓 `[nav] repo_deny = ["config.yml","auto-qb-data",".git",".env"]` = 旧 REPO_DENY 原样搬家, **行为零变化**。读者单点 `_common.config_nav_repo_deny`(S1 读者同款形态判据)。
- **外置2 nav_server**: `MAIN_REMOTE_CANDIDATES` → `DEFAULT_REMOTE_CANDIDATES = ("origin",)`(单远端通用, 对齐报告 §04 横切原则)+ `_remote_candidates()` 读 `[nav] remotes`, 回落语义同上(names[0] 兜底口径不变; 显式空列表 = 直接取 git remote 第一个)。本仓 `remotes = ["gitee","origin","github"]` 原样搬家, 行为零变化。读者单点 `_common.config_nav_remotes`。
- **外置3 tag_release**: 默认附注 `f"auto-qb {tag}"` → 纯函数 `tag_message(message, prefix, tag)` 三分支(--message 显式恒胜 / `<prefix> <tag>` / 空前缀回落通用 `release <tag>` 并置 fallback 旗 → main 打 WARN, 非静默); 项目词经新增 CLI 参 `--tag-note-prefix` 从 `.commands/release/config.toml` 的 release.tag **run 行**传入 —— 沿用该包「项目事实全在 config.toml run 行」的既有参数化模式(PORTING.md 配置键行声明), 不新增脚本读引擎配置的机制; FlagConsistencyTest(旗标 ⊆ argparse)守阵自动覆盖新旗标, 项目事实钉值扩进 test_project_facts_pinned。脚本零项目词(usage/docstring 同步通用化)。
- **外置4 check_updates**: `USER_AGENT` 常量 → `user_agent()` 函数读**新建** `.agents/skills/deps-upgrade/config/project.toml` `[user_agent] value`(D19 统一落点, 该 skill 首份 config); 缺失/形态不对(value 非串/空白/节非表)→ 回落通用 `DEFAULT_USER_AGENT = "deps-upgrade/1.0 (skill script; read-only)"` + stderr `[DEPS-CONFIG]` 提示一次; 坏 TOML fail-fast。选型留痕: User-Agent 是 API 礼仪标识非校验面, 回落提示取「提示着降级」与 D13 同口径(不静默)。
- **PORTING 依赖面同步三处**(不造第二口径): memory-bank runbook「配置落点」skill 面补 `[nav]` 两键; release PORTING 配置键行补 `--tag-note-prefix` 与回落语义; deps-upgrade PORTING 配置键行补 `[user_agent]`(并修正原「零硬编码项目词」声明与事实不符的漂移)。
- **守阵(红绿双验, 各文件头部测试计划同步)**: test_kb_nav_data 4 例(配置生效/整体替换语义/回落零项目词+提示一次/混型回落/显式空合法)、test_kb_nav_server 5 例(remotes 读配置生效/回落 origin+提示一次/候选序无命中退 names[0]/混型回落/显式空直取第一个; 既有 offline 测试改经配置给 gitee 候选序)、test_memory_bank_cli 2 例(本仓成态 [nav] 两节在场钉 + 读者形态判据)、release 包 TagMessageTest 3 例 + run 行项目事实钉值、tests/test_deps_upgrade_user_agent.py 新文件 4 例(配置生效/回落+提示/形态不对/坏 TOML fail-fast)。test.quick 全绿(实测数字与增量单点见新基线切片); dev.fmt 全部改过的 .py。
- **grep 复验(操作性代码零命中达成)**: 分词 grep(-i, auto-qb/auto_qb/qBittorrent/qbittorrent/gitee)对 .agents/skills + .commands + scripts 全量 695 处逐文件分类: C1 配置/数据面(task id 运行面/项目配置/项目数据件)283, C2 历史文档/PORTING/references 38, C3 provenance 注释/docstring 21, C4 守阵合成夹具/钉值 105, C5 项目专属不移植件/平台 API 词汇(PORTING/双场景指导明示声明同源)76, C6 根 scripts/ 项目运行时(非移植单位)172 —— **操作性代码命中 0**(批9b 前 4 处: nav×2/tag_release/check_updates 全部外置归零; 四个文件的余量命中均为注释/docstring, 计划字面词形大小写敏感下 nav_server 的 Gitee 注释等不构成「qBittorrent」形态命中)。**边界留痕**: `check_updates.py:365` 联合分析输出文案含小写 `qbittorrent` 三依赖名 —— 按计划 S11 字面词形(大小写敏感)不命中; -i 口径下归类「依赖面声明/特性词汇」白名单(与 SKILL.md「三特殊依赖联合分析」特性描述同源, 权威数据在 project/deps.toml 数据件), 外置需改输出装配逻辑(超出批9b 四处范围), 留痕供复核。
- **S11 终态**: 验收五条(报告 §5)全过 —— ①拷目录+填配置+0 行代码 diff 过; ②grep 白名单审计操作性代码零命中过(批9b 后); ③kb.check 空库首跑绿+删配置态宽容回落过; ④runbook 照做可复现过(①联验); ⑤my-commit-flow 自带测试 Linux 绿过(Windows 半条场地声明留痕, 见上轮)。S11 翻 **Done**。
- **批9b 评审修正(1 major 必修, 收集面分层)**: 基线切片首版(0653)的增量分解有误 —— 把 release 包 TagMessageTest 3 例计入了 test.full 增量, 静态按用例函数推 +17 与 test.full 实测增量 +14 矛盾。根因 = **收集面分层**: tests/ 收集面(test.full 消费)与 .commands 包收集面(test.pkg 消费)各自独立计数, test_release_pkg 在 test.full 收集面恒为 0 项。实证: 节点级收集清单 diff(stash 态 HEAD 6291 项 → 当前 6305 项, 净 +14, 零删除项; TagMessageTest 不在 test.full 清单)+ 逐文件收集计数(13/24/35/4/13)。处置: ①test.full 与 test.pkg 双面重跑实测(test.full 数字与上轮一致; test.pkg 较收口轮 +3 = TagMessageTest 3 例在其收集面在场); ②0653 切片未提交即废, 按「写完不改」口径删除重切为 26-11-17-0719(增量分解按面分摊 tests/ 面 14 + 包面 3, 与两轮实测严格对账; test_memory_bank_cli 净 +1 —— 既有「本仓 project.toml 成态」用例系加断言改造不计增量, 修正评审「净 +1」判定与首版「+2」的双重偏差); ③全部新守阵收集面自检通过: 14 项在 tests/ 面 node diff 逐条在列, TagMessageTest 3 例经 test.pkg 实测在场 —— 无「测量后扩写」(deps 4 例首版测量前已写, 评审的疑似不成立)。数字与分解单点 = 基线切片 26-11-17-0719。

- 2026-11-18 00:39 S1-S11 全波次实施+分批评审闭环入库: 配置化/摘链恒绿/glob 化/轨道 runbook/lane 外置/PORTING 全配/sync 配置化/收口五条验收; 合流适配修绿上游 Windows 盲区 3 红; 收尾观察 5 件建档; 全链线性推送 Gitee
