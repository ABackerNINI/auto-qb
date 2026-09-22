# auto-qb Memory Bank (AI 知识库索引)

> 面向 AI 助手的项目知识库。目标: 让 AI 在不重读全部源码的前提下, 快速建立对项目的准确心智模型, 并安全地修改代码。
> **若代码与本文冲突, 以代码为准并回写更新本文。**
> **入口链**: 根 [AGENTS.md](../AGENTS.md)(粗路由) → **本文件**(库内细路由) → 各 `_index.md` → 主题文件。
> ⚠ **检索纪律: 先索引、后 grep、禁止整读** —— 任一目录整体仍是几十 KB 量级, 整读一次这次目录化就白做了。
> 不确定关键词时 `grep -rn "<词>" memory-bank/` 是兜底(每个主题文件头部都写了 `触发:` 动作词)。

## 库内细路由 (我要做的事 → 读哪份)

| 我要做的事 | 读 |
|---|---|
| **改代码前扫陷阱 / 跑 git 命令前** | [pitfalls/_index.md](pitfalls/_index.md) —— 7 类 (git · web-ui · backend · testing · ops · kb · docs) |
| 写 / 跑测试, 查基线数字 | [testing/_index.md](testing/_index.md) —— 基线数字单点在 [testing/baseline.md](testing/baseline.md) |
| 查配置键 | [config-reference.md](config-reference.md) |
| 规则 / 条件 / 动作 | [rule-system.md](rule-system.md) |
| 架构 / 主循环 / 数据层 / 任务队列 | [systemPatterns.md](systemPatterns.md) |
| 找功能位置 / 加新模块 | [modules.md](modules.md) |
| 命名 / 风格 / 协作约定 | [conventions.md](conventions.md) |
| 项目是什么 / 领域知识 | [productContext.md](productContext.md) · [projectbrief.md](projectbrief.md) |
| 技术栈 / 环境 / 约束 | [techContext.md](techContext.md) |
| 已实现 / 规划中 | [progress/_index.md](progress/_index.md) |
| **现在做到哪 / 下一步** | [activeContext.md](activeContext.md)(易变层, ≤12 KB) |
| **真机走查清单** | [checklists/_index.md](checklists/_index.md) —— 做走查时逐条勾 |
| 跨会话任务档案 (立档 / 查档) | [tasks/_index.md](tasks/_index.md) |
| 计划外问题池 (8 类 × 两档) | [issues/_index.md](issues/_index.md) |

## 生成物 (冲突时**重跑脚本**, 不要手改)

- 各目录的 `_index.md` —— `python .agents/skills/memory-bank/scripts/gen_kb_index.py` 扫主题文件的三行头元数据生成
- [tasks/_index.md](tasks/_index.md) —— `python .agents/skills/memory-bank/scripts/gen_tasks_index.py` 扫档案 `Status` / `Summary` 生成
- [issues/_index.md](issues/_index.md) —— create-issue skill 的生成器重建
- 新增一个目录 = 建目录 + 写 `_about.md`(标题 / 一句话 / 触发) + 写主题文件(三行头) + **重跑生成器**;
  ⚠ 单条内容超 cap 时**先外迁再登记**(如 `progress/attachments/` 放超长叙事、`tasks/attachments/` 放档案纪要段);
  再在**本文件的细路由表里登记**一行 —— 少一处结构守卫就红。

## 一分钟速览

- **项目**: `auto-qb` — 基于 `qbittorrent-api` 的 PT 种子自动化管理工具 (标签/分类/HR 管理、辅种分组与缺文件检查、自定义规则引擎、tracker 级限速、全局限速曲线)。
- **形态**: 单机长驻 Python 程序, 入口 `python src/auto-qb.py [config.yml]`, 主循环 2s tick, 任务队列驱动。
- **核心设计**: `QbManager` 由 6 个 mixin 组合; 所有工作统一为带内置 interval 的任务进单一时间优先堆; `TorrentStore.apply_sync` 走 qB `/sync/maindata` rid 增量同步, `TorrentRecord` 是种子数据的唯一所有者; `QbApi` Facade 写后同步快照; **主循环单线程, 是唯一修改队列与 state_file 的线程**。
- **测试**: `pytest` + `tests/helpers.py` 全 Fake(无需真实 qBittorrent); 基线数字单点维护于 [testing.md](testing.md) 顶部, 勿在他处手抄。
- **文档**: 根 `README.md`(用户视角)与 `想法.md`(设计草稿)是上游文档; 本库是代码实况的核对版。

## 黄金法则与命令

> **改代码的黄金法则**(幂等 / 保守默认 / 状态持久化 / fail-fast / 单一写线程 / 范围守恒 / 请求边界)**与常用命令, 单点定义在根 [AGENTS.md](../AGENTS.md)**; 本文件不复述。
