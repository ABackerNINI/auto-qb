# auto-qb AI 知识库

> 面向 AI 助手的项目知识库。目标: 让 AI 在不重读全部源码的前提下, 快速建立对项目的准确心智模型, 并安全地修改代码。
>
> 所有内容均基于 2026-09-05 的 `develop` 分支源码逐文件核实 (commit `51374bd`)。若代码与本文冲突, 以代码为准并回写更新本文。

## 按任务选择文档

| 你要做的事 | 先读 |
|-----------|------|
| 第一次接触本项目 / 问"这是什么" | [01-overview.md](01-overview.md) |
| 理解主循环/任务队列/数据层/异步校验 | [02-architecture.md](02-architecture.md) |
| 找某个功能在哪个文件 / 加新模块 | [03-modules.md](03-modules.md) |
| 改规则、条件、动作相关代码 | [04-rule-system.md](04-rule-system.md) |
| 改配置解析 / 加配置键 / 排查配置问题 | [05-config-reference.md](05-config-reference.md) |
| 写任何代码之前 (命名/风格/约定) | [06-conventions.md](06-conventions.md) |
| 写测试 / 跑测试 | [07-testing.md](07-testing.md) |
| 改代码前必读 (魔法值/风险点/文档漂移) | [08-pitfalls.md](08-pitfalls.md) |
| 问"XX做了吗 / XX计划怎么做" | [09-roadmap.md](09-roadmap.md) |

## 一分钟速览

- **项目**: `auto-qb` — 基于 `qbittorrent-api` 的 PT 种子自动化管理工具 (标签/分类/HR 管理、辅种分组与缺文件检查、自定义规则引擎、tracker 级限速、全局限速曲线)。
- **形态**: 单机长驻 Python 程序, 无包管理配置 (pip 装依赖即用), 入口 `python src/auto-qb.py [config.yml]`, 主循环 2s tick, 任务队列驱动。
- **核心设计**: `QbManager` 由 6 个 mixin 组合; 所有工作 (种子刷新/规则/内置功能/校验轮询) 统一为带内置 interval 的任务, 进单一时间优先堆; `TorrentStore` 每 tick 全量快照 + 惰性缓存; `QbApi` 门面写后同步快照; 主循环单线程, 唯一修改队列与 state_file 的线程。
- **测试**: `pytest` + `tests/helpers.py` 全 Fake (无需真实 qBittorrent)。当前基线: **580 passed, 覆盖率 94%**, 全量运行约 1 秒。
- **文档**: `README.md` (用户视角) 与 `想法.md` (设计草稿) 是上游文档; 本知识库是代码实况的核对版 (README 有少量滞后, 见 [08-pitfalls.md](08-pitfalls.md))。

## 修改代码的黄金法则 (来自项目设计原则)

1. **幂等性**: 动作重复执行不得产生副作用; "每天一次"等窗口语义必须靠 state_file 去重 (`record_execution`), 不能依赖循环频率。
2. **保守默认**: 高风险动作 (跳检/强制汇报/删除种子/覆盖限速) 默认关闭, 只对显式配置的范围生效。
3. **状态持久化**: 跨轮次状态统一进 `state_file`, 程序退出时才落盘 (减少磁盘写入)。
4. **fail-fast**: 配置在加载时全部校验, 之后可假定配置正确; 新配置键必须在 `config.py` 加载函数中校验。
5. **单一写线程**: 只有主循环线程修改任务队列结构与 state_file; 不要引入绕开该假设的并发代码。

## 快速命令

```bash
# 测试 (项目 venv: .venv, Python 3.12)
.venv/Scripts/python.exe -m pytest tests -q            # 全量 580 项, ~1s
.venv/Scripts/python.exe -m pytest tests/test_grouping.py -q
.venv/Scripts/python.exe -m pytest --cov=src --cov-report=term-missing tests -q

# 运行 (需真实 qBittorrent; 干跑用 -n)
python src/auto-qb.py config.yml --dry-run

# 代码格式 (yapf, 配置见 .style.yapf: facebook 风格, 列宽 120)
yapf -i src/auto_qb/**/*.py
```
