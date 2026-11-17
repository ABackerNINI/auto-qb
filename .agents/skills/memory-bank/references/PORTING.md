# howto — 轨道移植 runbook: 把自制 skill 轨道搬进另一个项目

> [SKILL.md](../SKILL.md) 管**本仓库**的会话协议; 本文件管**换一个项目**时怎么把整条**轨道**搬过去。
> 移植单位 = **轨道**而非单个 skill: skill 目录 + commands 引擎 + `.commands/` 包 + sync 脚本 + KB 数据件骨架
> + 本文件(计划 26-11-17-0010 D1 —— 收编报告 §2.6-1 实证: 一半移植工作量在 skill 目录之外)。
> **只在移植 / 迁移时读** —— 日常会话不需要它。

## 为什么能整目录拷走

本 skill 是**自足**的: 一切脚本在 `scripts/`, 常量单点 `_common.py`, 不出现项目名、不假定安装深度
(仓库根靠 `.git` 向上探测)。2026-11-08 重构后生成器只剩 `gen_kb_index.py`(仅 pitfalls 一族有生成索引,
其余族的 `_index` 已退役) —— 生成物集合不再有 skill 外部依赖。

时间戳一律 **UTC+8 naive 墙钟**(`scripts/timekit.py` 单点), 与机器时区无关。

## 最小移植 (3 步)

1. **拷 skill 目录**: `.agents/skills/memory-bank/` → 目标项目同名路径, 或用户级
   `~/.workbuddy-ai/skills/memory-bank/`。`scripts/` 整目录带走即可 —— `check_kb_structure.py` /
   `check_doc_links.py` / `timekit.py` / `gen_*.py` / `nav_*.py` 全在里面。
2. **建 KB 骨架**: 建 `memory-bank/` 与各目录 —— `tasks/` `active-context/` `plans/` `reports/`
   `issues/` `pitfalls/<类>/` `testing/baselines/` 等; 索引目录(现仅 pitfalls)放一份 `_about.md`(三行头) ——
   **空库阶段 `_about.md` 里不要预挂类级 `_index.md` 链接**(空类目录不生成类级索引, 挂了 `doc.links` 必红;
   写入第一份坑档并重跑 `kb.index` 后再挂);
   手写 `memory-bank/README.md` 细路由(它不被生成, 是路由单点)。
3. **首次生成**: 跑 `commands run kb.index` 重建 pitfalls 的 `_index.md`(全库唯一生成索引)。

> 上面只是最小内核。**全量轨道**照「移植单位清单表」逐行走; 配置填空照「模板清单」复制改名;
> 按项目现状选路径走「双场景指导」。skill 拷过去但 `config/project.toml` 不建也能跑 ——
> 领域校验与跨 clone 查重按 D13 宽容回落, 每次打 `[KB-CONFIG]` 提示行(禁静默降级),
> 是「提示着降级」而不是「静默没这功能」; 想消掉提示行就照「双场景指导·领域枚举对齐」把配置补上。

## 移植单位清单表

照行推进, 每行右四列就是该单位的全部门(拷 / 配 / 件 / 验)。**环境中立**: 表内路径写通用形态;
标「本项目实例」的是本仓的具体取值, 只作示例, 目标项目按自己现状换。

| # | 移植单位 | 拷什么 | 改什么配置 | 建什么数据件 | 跑什么验收 |
|---|---|---|---|---|---|
| 1 | memory-bank skill 目录 | `.agents/skills/memory-bank/` 整目录(`scripts/` 全带走)→ 目标项目同名路径或用户级 skills 目录 | 建并填 `<skill>/config/project.toml`(`[domains]` / `[siblings]`; 填法见「双场景指导·领域枚举对齐」) | `memory-bank/` 目录骨架(`tasks/` `active-context/` `plans/` `reports/` `issues/` `pitfalls/<类>/` `testing/baselines/` 等; 类枚举单点 `PITFALL_CLASSES`, 索引目录放 `_about.md` 三行头) + 手写 `memory-bank/README.md` 细路由 | `kb.time` 三行正常(UTC+8); `kb.check` 空库绿; `kb.new task` 建档成功(领域枚举/查重生效) |
| 2 | commands 引擎 | `.agents/skills/commands/` 整目录 | 无引擎级配置; 各包配置见下行 | 无 | `commands list` 列得出包; `commands run kb.check` 经引擎跑通(`<skill-dir:NAME>` 占位符解析, 项目级 `.agents/skills/` 优先、用户级兜底) |
| 3 | `.commands/` 包 | 按需拷 `my-commit-flow/` `test/` `kb/` `review/` 各包(`scripts/` 与模板一并); **test 包例外: 只取它的 `config.minimal.toml` 起步, 原包脚本深度项目绑定不移植**(见「双场景指导·与既有测试套共存」) | 每包照「模板清单」的 `config.minimal.toml` 复制 → 改名(`config.toml`; my-commit-flow 改名 `.my-commit-flow.toml`)→ 逐节填空 | review 包另建 `lane.toml`(只做存量评审才建, 见「双场景指导·存量评审 lane」) | 各包脚本 `--help`; 预检 `--dry-run`; 起步闸门手工跑一遍绿 |
| 4 | sync 脚本 | 项目根 `scripts/sync_agent_skills.py` | 排除表与链接目标改成本项目值(本项目实例: `.agents/skills/.config/sync.toml` 的 `[exclude] names` / `[link_targets] paths`, 2026-11-17 S9 已落地; 口径见「配置落点与命名口径」) | 链接目标目录(本项目实例: `.codebuddy/skills/`) | 跑一遍后 `ls` 链接目标可见各 skill 链接 |
| 5 | KB 数据件骨架 | 按需拷 [templates/doc-forms.md](../templates/doc-forms.md) / [templates/collaboration.md](../templates/collaboration.md) / [templates/real-machine.md](../templates/real-machine.md)(既有骨架先例: [baseline.md](../templates/baseline.md)) | 无 | 复制到 `memory-bank/` 对应位置逐节填空(去向见「模板清单」); **不需要的件不复制**, SKILL.md 里引用它的段落一并摘除 | `check_doc_links.py --quiet` 绿(摘引用后无坏链) |
| 6 | 本文件 PORTING | 随单位 1 自动带走 | 移植后按目标项目现状回写(依赖面清单漂移是本改造头号风险 R-4) | 无 | 无 |

## 配置落点与命名口径 (D19)

单点口径, 别在别处再写第二份:

- **skill 面**: `<skill>/config/project.toml` —— 统一名, 项目绑定面(领域枚举 / 兄弟 clone 清单 /
  kb.nav 的 `[nav]`(红线排除 `repo_deny` / 远端候选序 `remotes`) / …)单点。
- **帮助文档**: `<skill>/references/PORTING.md` —— 每 skill 一份(D16, 允许薄); **包面不另建包级移植文件**,
  由本轨道 runbook 分节覆盖(D17, my-commit-flow `references/config.md` 先例)。
  每份随各自 skill 目录自动带走(拷目录即得), 依赖面以各文件为准, 本文件不汇总复制;
  覆盖口径 = 自制+半自制全配、第三方件不配(零依赖对照基准) —— 本项目实例: 已配 commands /
  create-issue / scope-guard / code-review / deps-upgrade / release / mutation-testing /
  autoclaw-design-capability / delivery-artifact 九份, memory-bank 本文件即轨道 runbook。
- **包面**: 跟包根先例 —— `.commands/my-commit-flow/.my-commit-flow.toml` 与 `.commands/review/lane.toml`
  (两者同构: 数据在包根文件, 脚本只读不写)。
- **sync 脚本例外**: `.agents/skills/.config/sync.toml`(点前缀, 防被 skill 遍历误收)—— S9 批次落地;
  本仓已创建(2026-11-17 S9), 即本仓生效配置。
- **配置缺失回落语义**(D13): 校验类缺失 → 跳过对应校验 + **必打** `[KB-CONFIG]` 提示行(禁静默降级;
  机制单点 `_common.load_project_config`); 运行必需数据(如 lane 批次矩阵)缺失 → 引导性报错。
  细则以代码单点为准, 本文件不复制。

## 双场景指导 (D20 —— 重点存量)

### 场景 A: 新项目绿地 (从零起步)

1. 按清单表 **#1 + #2** 起步: 拷 skill + 引擎, 建 `config/project.toml` 与 KB 骨架。
2. 按「模板清单」复制四件配置模板 → 改名 → 填空; **全部 TODO 填完、人工核对过才把 `confirmed` 改
   true** —— 未核对的初稿就去拦提交, 等于把配置错误埋进每笔提交。
3. KB 数据件(清单表 #5)按需复制; 不需要的连 SKILL.md 引用段一起摘(防坏链)。
4. 跑「移植后自查」全绿, 再按场景 B 第 2 条把闸门逐条开起来。

停手点: 任何一步验收红, 停在那里修, 不带红往下走。`kb.check` 对新空库**恒绿**是默认链成员资格
判据(单点见「项目可选守卫勿默认移植」), 绿地首跑红 = 移植动作有错, 不是库的问题。

### 场景 B: 开发中途存量 (重点)

1. **存量评审 lane 用法**(对当前代码做 code-review 的启用路径):
   - 拷 review 包(清单表 #3), `.commands/review/lane.toml` 就位后逐字段填空: `freeze_branch` =
     项目当前主干分支(冻结钉定: manifest 生成时点核验, 认领后拒改); 批次矩阵按**现状目录**划分路线,
     globs 宁缺勿滥 —— manifest 生成时有互斥 + 全覆盖守卫, 重叠/漏配即拒并列清单。
   - 机械面已接线(S7): review_lane 从 lane.toml 读全部项目数据(批次矩阵/分层范围/指针/分支策略),
     机械流程零改; 字段说明单点 = lane.toml 头注, 本节不复述。未配置远端时 freeze 取本地 HEAD
     (无远端稳态, 本地分支/离线项目也能评存量)。
   - 路径: 填矩阵 → 生成 manifest 冻结基线 → 路线认领(`route-<R>.json`, 重复认领被拒)→ 按批派只读评审子代理。
   - 停手点: 矩阵缺失 / 重叠拿到的是**引导性报错**(D13, 指路 lane.toml 与具体必填字段), 照文案补字段,
     不是退回手写流程。
2. **闸门渐进启用**(别一次性全开):
   - 先 `config.minimal.toml` 的 3 条起步闸门: 未确认态(`confirmed = false`)先靠体检命令
     (`_pipeline.py --show-config`)观察输出, 填空核对后改 true。
   - `red_lines` 从项目真实的「生产配置 / 运行时数据 / 凭据」各写一两条起步(条目 = fnmatch glob,
     语义单点 [references/config.md「匹配语义」节](../../../../.commands/my-commit-flow/references/config.md),
     不凭印象写); `warn_lines` 先当观察面, 不急着升 STOP。
   - 可选闸门(kb.check / 文档链接检查 / 格式化)等**对应移植单位验收绿了**再逐条开注释 ——
     对应单位还没移植就开它的闸门, 等于每笔提交必红。
3. **领域枚举对齐现状**(把存量档案的实际主题收编进 `[domains]`):
   - `ls memory-bank/tasks/` 取文件名去日期前缀后的**首段**, 去重 → `[domains] values`
     (本项目实例: 八域 `webui` / `backend` / `rule` / `memory-bank` / `docs` / `test` / `deps` / `config`;
     枚举项可含短横线, `kb.new task --topic` 按**最长前缀**匹配)。
   - 不收编也能跑: domains 缺失按 D13 跳过领域校验 + 打提示行 —— 但存量项目放着不管提示行会一直在,
     收编一次就干净。
   - 兄弟工作区同理: 多 clone 并行的项目把各 clone 目录名写进 `[siblings] tasks_dirs` **显式列表**
     (本项目实例: `["auto-qb-zcode-clone2", "auto-qb-zcode-clone3"]`; 只读 ls 各自 `memory-bank/tasks/`,
     忽略日期前缀按 slug 比对); 单 clone 留空列表 = 合法配置, 不查跨 clone。
4. **与既有测试套共存**:
   - 起步闸门里的 pytest / node 命令改成项目**自己的**测试入口(test 包
     [config.minimal.toml](../../../../.commands/test/config.minimal.toml) 就是最小起步设计;
     本项目实例的 test 包 —— Docker testbed / TMPDIR 自举 / 覆盖率闸 —— 深度项目绑定, **不移植原包**)。
   - memory-bank 的 pytest 薄壳(`tests/test_memory_bank_*.py` 进程内 import 模式, 见「可选机检」)是
     **可选增量**: 文件名独立前缀不与既有套冲突, 挂不挂由项目拍板。
   - 存量测试先跑绿再挂闸门: 把红的套件挂进闸门 = 每笔提交必红, 先修后挂。

## 模板清单 (复制 → 改名 → 填空)

S6 产物七件, 四件配置模板 + 三件数据件骨架, 全部「复制 → 改名 → 逐节填空」用法:

| 模板(源仓路径) | 复制到(目标项目) | 用法要点 |
|---|---|---|
| [my-commit-flow/config.minimal.toml](../../../../.commands/my-commit-flow/config.minimal.toml) | `.commands/my-commit-flow/.my-commit-flow.toml` | 3 条起步闸门 + 可选闸门注释示例; 文件头注写死 D13 回落语义与 fnmatch 匹配语义(细则单点 references/config.md「匹配语义」节); TOML 陷阱(顶层键必须写在 `[[gates]]` 表头之前)也在头注 |
| [test/config.minimal.toml](../../../../.commands/test/config.minimal.toml) | `.commands/test/config.toml` | `node --check` + pytest 两条起步; 解释器出厂 `python3`(uv 等项目偏好不入出厂面) |
| [kb/config.minimal.toml](../../../../.commands/kb/config.minimal.toml) | `.commands/kb/config.toml` | 标准 task id 起步超集(index / check / active / baseline / new / time / wrap / status / bump / ref; nav 归可选注释)+ 可选守卫(kb.docmap / kb.anchor)注释示例; 默认链成员资格判据见「项目可选守卫勿默认移植」 |
| [review/lane.toml](../../../../.commands/review/lane.toml) | 同路径就地填空 | 存量评审批次矩阵(机械面已接线 S7, 本仓矩阵即真实实例); 复制后按头注字段说明整文件替换成本项目值; 引导性报错口径 D13 以头注为准 |
| [templates/doc-forms.md](../templates/doc-forms.md) | `memory-bank/conventions/doc-forms.md` | 四工位文档形态协议骨架; 协议层(doc-* meta / 状态词表 / 认领链机制)照抄不改, 只填项目目录映射 / 命名口径 / 创建命令表 |
| [templates/collaboration.md](../templates/collaboration.md) | `memory-bank/conventions/collaboration.md` | 协作约定骨架; 只记「用户明示」的约定, 每条标日期; 细则单点在项目 AGENTS.md, 这里只写指针 |
| [templates/real-machine.md](../templates/real-machine.md) | `memory-bank/testing/real-machine.md` | 真机实测轨规程骨架; **没有真机轨的项目不复制本件**, SKILL.md 里引用本件的那段一并摘除 |

> issue 族模板(`issue-light.html` / `issue-standard.html`)与 pitfall / plan / report / slice / task 等
> 出厂模板走 `kb.new` 派生建件, 不在复制清单内; `templates/baseline.md` 是数据件骨架的既有先例, 一并可用。

## 可选机检 (推荐全挂)

- **pytest 薄壳**: 照抄 `tests/test_memory_bank_*.py` 的**进程内 import** 模式 —— 它 import skill 的
  `check_kb_structure` / `gen_*` / `gen_active_recent` / `check_doc_links` / `timekit`, 不起子进程。
  项目专属的断言(AGENTS.md 8,000 硬上限等)留在项目侧测试里。
- **命令包**: 照 [kb/config.minimal.toml](../../../../.commands/kb/config.minimal.toml) 复制改名
  `config.toml`(标准 task id: `kb.index` / `kb.check` / `kb.active` / `kb.baseline` / `kb.new` /
  `kb.time` / `kb.wrap` / `kb.status` / `kb.bump` / `kb.ref`; `kb.nav` 在模板里归可选注释, 按需开),
  命令里用
  `<skill-dir:memory-bank>` 占位符 —— skill 目录搬家 / 换安装位置时配置零改动。
- **提交闸门**: 把 `kb.check` 与 `timekit.py --check` 挂进提交前闸门(改 `memory-bank/` 即触发);
  另挂 `check_doc_links.py --quiet`(改名 / 搬家后的坏链只有机检看得见)。挂法照
  my-commit-flow 模板的可选闸门注释示例, 时机见「双场景指导·闸门渐进启用」。
- **取时入口**: 收录一条 `kb.time`(跑 `timekit.py`), 并把「时间戳用命令取」的约定写到项目文档里 ——
  没有真命令, 那条约定就只是空话。

## 项目可选守卫勿默认移植

默认检查链(`kb.check` / 提交闸门)只允许「对新空库恒绿」的成员(计划 26-11-17-0010 设计原则 2):
凡「要求某个具体文件必须存在」的 fail-closed 守卫都是**项目层**守卫 —— 空库上它必红, 进默认链
等于让新项目首跑就堵死。这类守卫以**显式挂载**方式存在于本项目(独立 task id + 闸门引用改指),
移植时**不得**顺手抄进默认链, 是否需要由目标项目自己拍板:

- **`check_mutation_anchor.py`(常驻锚防流水守卫, 首条)**: 钉住变异测试排期锚
  `issues/*-test-mutation-audit-standing.html` 的形态(锚文件缺失即红, 见 `collect_violations`)。
  本项目侧经 `.commands/kb` 的 `kb.anchor` task 显式挂载, 提交闸门(memory-bank/)经 commands
  引擎指向该 task; 它**不在** `kb.check` 默认链。没有排期锚(未做变异测试审计)的项目不需要它。
- **`gen_doc_map.py --check`(主键校验 + 认领链双向守卫, 第二条)**: 空库判红「没有任何件声明引用
  —— 认领链守阵失去校验对象」(零文档件上认领链守阵无校验对象, 见 `check_claim_chain` 的
  `if not checked` 分支)。本项目侧经 `.commands/kb` 的 `kb.docmap` task 显式挂载, 提交闸门
  (memory-bank/)经 commands 引擎指向该 task; 它**不在** `kb.check` 默认链。目标项目的认领链
  (第一份带 `Refs:` / `doc-refs` 的文档)建起来后, 再照本条显式挂载。

默认链成员资格判据: 新空库骨架(各族目录全建、零文档件)上 `--check` 全绿; 活体校验在本项目
`tests/test_memory_bank_docs.py` 的 `test_kb_check_default_chain_empty_kb_audit`。

## 测试与脚本卫生 (清理路径先校验后删)

全包(`.commands/` 与 `.agents/skills/` 下的脚本)的 rmtree/unlink 调用点做过全量复核
(计划 26-11-17-0010 S3; 主案 33e3a3d6 已修: 锚定守卫 + 侧信道 + conftest 防呆 + 双防呆)。
新增脚本自查清单与复核方法论:

- **清理路径先校验后删**: `rmtree`/`unlink` 的目标若不是脚本自己构造的路径(tempfile 产物 /
  常量拼接), 删前必须校验 —— **非空** + **不在 cwd / 仓库根下**(resolve 后比较; 现成范本:
  review_lane.py 的 `_guard_snap_path`、_snapshot.py `_sweep_old` 的双防呆)。
- **解析值禁直接当路径**: 从文件内容 / 命令输出解析出来的字符串先过校验再进删除目标;
  有界来源(git porcelain 只报仓库相对路径)按「来源语义有界」单独论证后放行。
- **删前认自证标记**: 只删带本体系标记的目录/文件(`.run-pid` / `.snapshot-hash` / wrapper MARK),
  撞名的外来对象一律不碰。
- **`sys.executable` 派生子进程**: 起 python 子进程一律 `sys.executable`, 不裸写 `python` /
  `python3` —— 防解释器失真(venv / 容器 / 系统 python 混用时测试结果不可复现)。
- **平台断言一律 `os.name` 条件化**: 写 `os.name == "nt"` 分支, 不对 `sys.platform` 或盘符
  形态写死断言。

对照复核结论(2026-11-17): 全包调用点逐点过, 零「解析值未校验直接当路径」调用点 —— 已校验形态
= tempfile 自建 / 常量拼接 / 删前认标记 / 删前容器守卫 / 只删约定路径并核等值(consume_message_file) /
生成器自产残留页(stale_volume_pages); 有界形态 = git porcelain 解析路径(sync.py restore 用,
git 保证仓库相对)。

## 项目专属值**不搬**(留在项目根 `scripts/`)

- `check_context_caps.py` —— 含项目的 `AGENTS.md` 字符上限(IDE 注入硬约束)。
- `check_command_drift.py` / `sync_agent_skills.py` —— 含项目的包路径与 skill 链接布局
  (本项目实例: sync 的 `LINK_TARGETS` / `EXCLUDED`; S9 配置化后改填 `.agents/skills/.config/sync.toml`,
  见「配置落点与命名口径」)。

## 移植后自查

- `commands run kb.time` 三行输出正常(UTC+8, 与机器时区无关)。
- `commands run kb.check` 绿: 索引 == 生成结果 + 日期守卫无违规 + 切片结构 OK。(空库骨架首跑
  恒绿; fail-closed 守卫都已摘出默认链, 见上「项目可选守卫勿默认移植」。)
- `commands run doc.links` 绿: 无坏链。
- my-commit-flow 体检(`python3 <my-commit-flow 包>/scripts/_pipeline.py --show-config`, 不走 commands
  引擎): 配置缺失 / 占位符展开不了会停手打引导文案 —— 存量项目渐进启用闸门时先看这个再挂闸。
- `commands run kb.new task --topic <领域>-<示例专题> --title "移植冒烟"` 建档成功后即删:
  领域枚举(`[domains]`)与跨 clone 查重(`[siblings]`)真实生效才算配置面移植完成。

> 以上 task id 见上「可选机检 · 命令包」; 没挂命令包时直接跑 skill `scripts/` 里的同名脚本即可。
