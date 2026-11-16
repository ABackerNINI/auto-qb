# 自制 skill 可移植性改造报告

> **收编注记 (2026-11-17, auto-qb 仓)**: 本件由 `PTSKIT-farm-helper/docs/skill-portability-report.md` 经用户显式授权原样拷入(存档特例: reports/ 惯例为单文件 HTML, 此处保真优先保 .md; 改造计划见 `memory-bank/plans/26-11-17-0010-plan-skill-portability.html`)。
> 原文中的「本仓」指**源仓 PTSKIT-farm-helper**; 文内指向源仓 git 历史与 `memory-bank/tasks/26-11-14-kb-init-porting.md` 的引用在拷贝后失效, 证据以本文所记文字为准。
> 原文「改造实施时建议把本文件挪到 auto-qb 仓库」已由本次收编执行。

> 依据：2026-11-13/14 auto-qb → PTSKIT-farm-helper 的一次完整实战移植（7 自制 skill + 命令包轨道 + 守卫薄壳，
> 7 笔提交、9 个评审/复评代理、1 起清库事故）。本报告是**消费者视角的摩擦实录**，为在 auto-qb 侧做可移植性改造提供依据。
> 定位：改造实施时建议把本文件挪到 auto-qb 仓库（此处仅存档）。所有"本次证据"均可在本仓 git 历史与
> `memory-bank/tasks/26-11-14-kb-init-porting.md` 追溯。
**Refs:** memory-bank/plans/26-11-17-0010-plan-skill-portability.html, memory-bank/tasks/26-11-17-memory-bank-skill-portability.md

## 0. 一句话结论

移植摩擦的根因高度集中：**"自足"只在 skill 目录边界内成立，边界外的东西——项目词汇、项目专属守卫、项目数据件、工作流轨道——既没声明也没隔离**。改造主轴一句话：**把这四类绑定从代码移进配置/数据，把 PORTING.md 从"skill 拷贝指南"升级为"轨道移植 runbook"**。

## 1. 验证有效的设计（改造时不要动）

| 设计 | 本次证据 |
|---|---|
| commands 引擎：`find_root` 靠 `.git` 向上探测 + `<skill-dir:NAME>` 占位符 | **零代码改动**移植成功 |
| ship 配置外置 `.my-commit-flow.toml`（引擎不认识"提交"） | my-commit-flow 适配**只改了这一个文件**（3429 字符），脚本零改 |
| timekit UTC+8 naive 钉死、单点取时 | 全部日期在 **UTC-8 时区的沙箱里**取值仍全对；kb.time 三行格式稳定 |
| create-issue 物理并入 memory-bank（脚本/模板/常量合一） | 零额外移植工作，只拷 SKILL.md |
| `templates/` + SLOT 派生机制 | kb.new/kb.wrap 建件全部机械派生，零手写时间戳 |
| code-review ③"本地分支态探针" | 无远端 bootstrap 期全程可用，未阻塞一次评审 |
| PORTING.md 存在 + 三步骨架 | 方向正确（本报告只谈它的覆盖缺口） |
| 第三方 skill 的"单文件零依赖"标准 | grilling（31 行）/gitmoji **零摩擦**——这就是可移植性的对照基准 |
| 守卫薄壳"进程内 import"测试模式 | 45 条用例 0.4s 跑完，无子进程、无环境依赖 |

## 2. 需要改造的清单（按 skill，含本次临时补丁作证据）

优先级：**P0** = 本次实测踩雷/出事故；**P1** = 本次花了手工改造成本；**P2** = 洁癖级。

### 2.1 memory-bank（核心，改动最多）

| # | 问题 | 本次证据 | 根因 | 改造方案 | 级 |
|---|---|---|---|---|---|
| 1 | **`TASK_DOMAINS` 项目词汇硬编码**在 `_common.py` | T5 被迫改代码（`userscript/dom/kb/...`），否则 `kb.new task` 拒收 | 领域枚举是项目词汇，却住在"自足"脚本里 | 移到项目侧配置（如 `memory-bank/config.toml [domains]`），`_common` 读配置、无配置回落内置默认；SKILL.md 只写"枚举单点在 KB 配置" | P0 |
| 2 | **`new_doc.py` 跨 clone 查重硬编码 `../auto-qb-*` glob** | T3 删 `_sibling_tasks_dirs`（31 行 diff） | 多 clone 工作区假设写死进代码 | 同一配置文件加 `[siblings]` 路径列表（空=单 clone），删 glob | P0 |
| 3 | **`check_mutation_anchor` 混在 kb.check 默认链**且 fail-closed（锚缺失判红） | T5 实测 PLAN"空库自然通过"预判错误 → 被迫立锚占位 issue → 用户拍板清退（ee86af6） | 项目专属守卫（变异测试审计）伪装成通用守卫随 skill 出走；fail-closed 无 opt-out | 与 `check_context_caps` 同等对待：列入 PORTING"**项目可选守卫，勿默认移植**"清单；或 kb.check 配置化（`[guards]` 开关）。**原则：默认链只允许"对空库恒绿"的检查** | P0 |
| 4 | SKILL.md 内嵌项目绑定：qB 真机自检段、`../auto-qb-*`、源仓 AGENTS.md 章节名、conventions 数据件引用 | T3 四处改造 | 协议层与项目层未分离 | SKILL.md 只留协议；真机轨细节全下放 `testing/real-machine.md`（数据件）；跨项目引用一律写成"本项目 AGENTS.md / 本 KB conventions/..." | P1 |
| 5 | **KB 数据件无模板**：SKILL.md 引用 `conventions/{doc-forms,collaboration}.md`、`testing/{baseline,real-machine}.md`，PORTING 让你自己写 | T5 从零手写 4 件（~3000 字符/件） | templates/ 只覆盖 task/slice/pitfall 等，缺 conventions/testing 类 | templates/ 增补这 4 件的骨架模板（带 TODO 占位 + 三行头），PORTING 第 2 步改"复制后填空" | P1 |
| 6 | SKILL.md 正文混大量演进史（裁定编号、复盘故事、源仓 reports 链接） | T3 逐条判定"provenance 保留/操作性改写"，花裁决成本 | 协议与历史未分层 | 演进史下沉 `references/history.md`，SKILL.md 正文只留协议（历史引用一次即可） | P2 |

### 2.2 my-commit-flow（配置外置做得最好，仍有四点）

| # | 问题 | 本次证据 | 改造方案 | 级 |
|---|---|---|---|---|
| 1 | **gates 节深度绑定项目任务**（dev.fmt/yapf、test.pkg.scoped、vnu jar、check_context_caps） | T4 重写整个闸门节（12 条→3 条起步） | `.my-commit-flow.toml` 出厂**最小模板**随包发布（可选闸门注释掉+一行说明），PORTING 链接它；项目自行启用 | P1 |
| 2 | **red_lines/warn_lines 匹配语义反直觉**：`hit()` = 前缀 startswith **或子串 in**，非 glob——`*.cookies*` 永不命中且无告警 | T4 面A评审实测确认；我们的配置头注补了语义说明 | ①config 模板头注写死语义与正反例；②或支持 glob（`fnmatch`）——建议前者，语义改动影响面大 | P1 |
| 3 | **真 bug：`test_snapshot.py` 清理可 `rmtree(Path("").parent)`=仓库根**（子进程解析失败时 `snap=Path("")`，cleanup 注册在断言前） | **T4 清库事故**（沙箱 shim 使 `sys.executable` 失真触发），已加固 | 双防线：①cleanup 注册前**必须**校验路径非空、不在 cwd/仓库根下（写进包内测试守则）；②全包 grep `rmtree|unlink` 审计一遍"解析值直接当路径"模式；③运行期 `_snapshot.py` 同款防御 | **P0** |
| 4 | 环境绑定：`[sys.executable, ...]` 子进程（shim 环境下失真）、两处 Windows 断言 | T4 事故根因链 + 2 处 `os.name=="nt"` 守卫 | 测试守则：平台断言一律 `os.name` 条件化；`sys.executable` 派生子进程前校验是真实解释器（可 `shutil.which` 兜底） | P1 |

### 2.3 review 包

| # | 问题 | 本次证据 | 改造方案 | 级 |
|---|---|---|---|---|
| 1 | **`review_lane.py`（1000 行）+ `review.lane.*` 六个 task id 是 R4 存量评审专属**，混在核心包里 | T4 裁剪（config 重写 + test 删三个 Lane 测试类） | 拆到独立目录（如 `.commands/review-lane/`）或标 `# LEGACY (R4)` 区块；PORTING 标"不移植" | P1 |
| 2 | config 里 `uv run python` 环境假设 | T4 统一改 `python3` | 出厂配置用 `python3`（脚本纯 stdlib），uv 是项目偏好不入默认 | P2 |
| 3 | check_review_trace 从 `.my-commit-flow.toml` 读红线——已同源通用 | 面A核验通过 | 保持，无需动 | — |

### 2.4 对照组：无需改造

**commands / create-issue / scope-guard 零改动通过**。scope-guard 纯语义单文件；create-issue 随 memory-bank；commands 引擎如上。它们是"可移植"的活样板——改造其他 skill 时对齐它们的标准即可：**判断在 SKILL.md（语义层），机械在 scripts（自足层），项目差异在配置/数据（外置层）**。

### 2.5 `scripts/sync_agent_skills.py`（半自制）

| # | 问题 | 本次证据 | 改造方案 | 级 |
|---|---|---|---|---|
| 1 | `EXCLUDED = {"autoclaw-design-capability"}` 硬编码项目条目 | T2 拷贝后清空 | 排除表配置文件化（如 `.agents/skills/.sync-exclude`，一行一个） | P1 |
| 2 | `LINK_TARGETS` 只有 `.codebuddy/skills`（workbuddy CLI 假设） | 本仓同样只挂了一处 | 目标列表同样进配置（多 harness：.codebuddy/.zcode/...） | P2 |

### 2.6 PORTING.md 本身（最大的杠杆点）

| # | 缺口 | 本次证据 | 改造方案 | 级 |
|---|---|---|---|---|
| 1 | **覆盖面只有 memory-bank skill 本体**——实际的移植单位是"轨道"：skill + commands 引擎 + `.commands/{kb,my-commit-flow,review,test}` + `scripts/sync_agent_skills.py` + KB 数据件 | T4/T5 的一半工作量在 PORTING 没写的地方 | 升级为**轨道 runbook**：一张移植单位清单表（拷什么/改什么配置/建什么数据件/跑什么验收），以本次移植为校准用例 | P0 |
| 2 | **缺"项目可选守卫"清单** | check_mutation_anchor 教训（见 2.1-3） | 列出所有"要求项目对象存在"的检查，标注默认不移植 | P0 |
| 3 | 缺最小配置模板集（`.my-commit-flow.toml` / kb 包 / test 包） | T4 重写、T6 从零建 | 模板随包发布，PORTING 只写"复制+改键" | P1 |
| 4 | 缺数据件骨架 | T5 手写 4 件 | 见 2.1-5 | P1 |

### 2.7 test 包

源仓 test 包（Docker testbed/TMPDIR 自举/覆盖率闸/随机序）深度项目绑定，**不值得改造成可移植**——正确做法是 PORTING 附一个"最小 test 包模板"（node --check + pytest tests 两条起步，本仓 `.commands/test/config.toml` 可直接当模板），不试图移植原包。

## 3. 横切原则（从摩擦提炼，改造时的判据）

1. **配置/数据与代码分离**：项目词汇（领域枚举）、项目路径（sibling workspaces）、排除表、闸门清单一律外置；代码读配置、无配置回落通用默认。判定法：**换项目时不该需要改任何 `.py`**。
2. **fail-closed 守卫必须显式 opt-in**：默认检查链只允许"对新空库恒绿"的成员；要求"某文件必须存在"的守卫属于项目层，进可选清单。
3. **环境中立默认值**：`python3` 而非 `uv run`；单远端而非 gitee/github 双远端假设；**无远端是合法稳态**（本地分支、离线 bootstrap）。
4. **测试卫生**：清理路径先校验后删（非空 + 不在 cwd 下）；`sys.executable` 派生子进程要防御解释器失真；平台断言条件化。移植是测试最好的 cross-check——**本次唯一真 bug 就是移植暴露的**。
5. **协议与演进史分离**：SKILL.md 是协议，历史进 references/history.md。
6. **可移植性声明**：每个 skill 的 PORTING 段落给一张"依赖面清单"（需要项目提供哪些数据件/配置键/可选守卫），让消费者一眼知道要建什么。

## 4. 建议波次

| 波次 | 内容 | 验证法 |
|---|---|---|
| **波次 1（P0，防复发）** | ①test_snapshot 类清理加固 + 全包 rmtree 审计；②check_mutation_anchor 出默认链 + PORTING 可选守卫清单；③TASK_DOMAINS 与 sibling-glob 配置化 | 用本仓重放：重新从改后的 auto-qb 拷 skill 到一个干净目录，**0 行代码 diff** 即通过 |
| **波次 2（P1，降手工）** | ④PORTING 升级轨道 runbook + 三份最小配置模板 + 4 份数据件骨架模板；⑤my-commit-flow gates 出厂模板；⑥review_lane 拆分；⑦sync 脚本排除表配置化 | 照新 runbook 在第三个项目做一次演练移植，记录手工步骤数（目标 ≤ 半天） |
| **波次 3（P2，洁癖）** | ⑧SKILL.md 去项目化措辞/历史下沉；⑨red_lines 语义文档化、uv→python3 默认；⑩sync 链接目标配置化 | grep 白名单审计（见下） |

## 5. 改造后的可判定验收标准

1. **最小移植 = 拷目录 + 填 ≤10 个配置键 + 0 行代码 diff**（以本仓为对照组重放）。
2. kb.check 默认链对**空库首跑绿**（无需先立任何占位对象）。
3. `grep -rn 'auto-qb\|auto_qb\|qBittorrent\|gitee' skills/` 命中仅在白名单（provenance 注释/历史文档），**操作性代码零命中**。
4. PORTING runbook 照做能复现本仓结果（把本仓当移植测试场，diff 应只剩配置/数据差异）。
5. my-commit-flow 自带测试 Linux/Windows 双绿；全包无"未校验路径直接 rmtree"调用点。

## 6. 本次临时补丁 → 改造方向对照（附录）

| 本次补丁（本仓） | 对应改造项 |
|---|---|
| SKILL.md 四处改造（21354a9） | 2.1-4 |
| `new_doc.py` 删 `_sibling_tasks_dirs`（同上） | 2.1-2 |
| `_common.py` TASK_DOMAINS 换血（d4b2e37） | 2.1-1 |
| 锚占位 → 清退（d4b2e37 → ee86af6） | 2.1-3 |
| `.my-commit-flow.toml` 适配（cea09a2） | 2.2-1/2 |
| test_snapshot 加固（cea09a2） | 2.2-3 |
| review 包裁剪 R4/Lane（cea09a2） | 2.3-1 |
| sync_agent_skills 清空 EXCLUDED（21354a9） | 2.5-1 |
| tests 四件 3064→1205 行剔除清单（c2cd672） | 2.1-1/2 旁证：项目断言全部可辨识、可剥离——说明"剥离点"存在，只欠声明 |
| 手写 4 份 KB 数据件（d4b2e37） | 2.1-5 |
