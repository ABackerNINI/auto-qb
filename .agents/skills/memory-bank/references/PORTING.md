# howto — 把 memory-bank skill 移植到另一个项目

> [SKILL.md](../SKILL.md) 管**本仓库**的会话协议; 本文件管**换一个项目**时怎么把整套东西搬过去。
> **只在移植 / 迁移时读** —— 日常会话不需要它。

## 为什么能整目录拷走

本 skill 是**自足**的: 一切脚本在 `scripts/`, 常量单点 `_common.py`, 不出现项目名、不假定安装深度
(仓库根靠 `.git` 向上探测)。唯一外部依赖是 **create-issue skill**(它的 `gen_issues_index.py` 是生成物
集合的一员) —— 缺它时 `gen_all.py` 报 rc=2 并说明。

时间戳一律 **UTC+8 naive 墙钟**(`scripts/timekit.py`; create-issue 侧本地内联同口径), 与机器时区无关。

## 最小移植 (3 步)

1. **拷 skill 目录**: `.agents/skills/memory-bank/` → 目标项目同名路径, 或用户级
   `~/.workbuddy-ai/skills/memory-bank/`。`scripts/` 整目录带走即可 —— `check_kb_structure.py` /
   `check_doc_links.py` / `timekit.py` / `gen_*.py` / `nav_*.py` 全在里面。
2. **建 KB 骨架**: 建 `memory-bank/` 与各目录 —— `tasks/` `activeContext/` `plans/` `reports/`
   `issues/` `pitfalls/<类>/` `testing/baselines/` 等; 每个**索引目录**放一份 `_about.md`(三行头);
   手写 `memory-bank/README.md` 细路由(它不被生成, 是路由单点)。
3. **首次生成**: 跑 `commands run kb.index` 重建全部 `_index.md`。

## 可选机检 (推荐全挂)

- **pytest 薄壳**: 照抄 `tests/test_memory_bank.py` 的**进程内 import** 模式 —— 它 import skill 的
  `check_kb_structure` / `gen_*` / `gen_active_recent` / `check_doc_links` / `timekit`, 不起子进程。
  项目专属的断言(AGENTS.md 8,000 硬上限等)留在项目侧测试里。
- **命令包**: 建 `.commands/kb/config.toml`(task id: `kb.index` / `kb.check` / `kb.active` /
  `kb.baseline` / `kb.docmap` / `kb.time` / `kb.nav`), 命令里用 `<skill-dir:memory-bank>` 占位符
  —— skill 目录搬家 / 换安装位置时配置零改动。
- **提交闸门**: 把 `kb.check` 与 `timekit.py --check` 挂进提交前闸门(改 `memory-bank/` 即触发);
  另挂 `check_doc_links.py --quiet`(改名 / 搬家后的坏链只有机检看得见)。
- **取时入口**: 收录一条 `kb.time`(跑 `timekit.py`), 并把「时间戳用命令取」的约定写到项目文档里 ——
  没有真命令, 那条约定就只是空话。

## 项目专属值**不搬**(留在项目根 `scripts/`)

- `check_context_caps.py` —— 含项目的 `AGENTS.md` 字符上限(IDE 注入硬约束)。
- `check_command_drift.py` / `sync_agent_skills.py` —— 含项目的包路径与 skill 链接布局。

## 移植后自查

- `commands run kb.time` 三行输出正常(UTC+8, 与机器时区无关)。
- `commands run kb.check` 绿: 索引 == 生成结果 + 日期守卫无违规 + 切片结构 OK。
- `commands run doc.links` 绿: 无坏链。

> 以上 task id 见上「命令包」; 没挂命令包时直接跑 skill `scripts/` 里的同名脚本即可。
