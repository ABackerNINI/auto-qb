# howto — 把 memory-bank skill 移植到另一个项目

> [SKILL.md](../SKILL.md) 管**本仓库**的会话协议; 本文件管**换一个项目**时怎么把整套东西搬过去。
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
   `issues/` `pitfalls/<类>/` `testing/baselines/` 等; 索引目录(现仅 pitfalls)放一份 `_about.md`(三行头);
   手写 `memory-bank/README.md` 细路由(它不被生成, 是路由单点)。
3. **首次生成**: 跑 `commands run kb.index` 重建 pitfalls 的 `_index.md`(全库唯一生成索引)。

## 可选机检 (推荐全挂)

- **pytest 薄壳**: 照抄 `tests/test_memory_bank_*.py` 的**进程内 import** 模式 —— 它 import skill 的
  `check_kb_structure` / `gen_*` / `gen_active_recent` / `check_doc_links` / `timekit`, 不起子进程。
  项目专属的断言(AGENTS.md 8,000 硬上限等)留在项目侧测试里。
- **命令包**: 建 `.commands/kb/config.toml`(task id: `kb.index` / `kb.check` / `kb.active` /
  `kb.baseline` / `kb.new` / `kb.time` / `kb.nav`), 命令里用 `<skill-dir:memory-bank>` 占位符
  —— skill 目录搬家 / 换安装位置时配置零改动。
- **提交闸门**: 把 `kb.check` 与 `timekit.py --check` 挂进提交前闸门(改 `memory-bank/` 即触发);
  另挂 `check_doc_links.py --quiet`(改名 / 搬家后的坏链只有机检看得见)。
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
- `check_command_drift.py` / `sync_agent_skills.py` —— 含项目的包路径与 skill 链接布局。

## 移植后自查

- `commands run kb.time` 三行输出正常(UTC+8, 与机器时区无关)。
- `commands run kb.check` 绿: 索引 == 生成结果 + 日期守卫无违规 + 切片结构 OK。(空库骨架首跑
  恒绿; fail-closed 守卫都已摘出默认链, 见上「项目可选守卫勿默认移植」。)
- `commands run doc.links` 绿: 无坏链。

> 以上 task id 见上「命令包」; 没挂命令包时直接跑 skill `scripts/` 里的同名脚本即可。
