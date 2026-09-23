# auto-qb Memory Bank (AI 知识库索引)

> 面向 AI 助手的项目知识库。目标: 让 AI 在不重读全部源码的前提下, 快速建立对项目的准确心智模型, 并安全地修改代码。
> **若代码与本文冲突, 以代码为准并回写更新本文。**
> **入口链**: 根 [AGENTS.md](../AGENTS.md)(粗路由) → **本文件**(库内细路由) → 各 `_index.md` → 主题文件。
> ⚠ **检索纪律: 先索引、后 grep、禁止整读**; 不确定关键词时 `grep -rn "<词>" memory-bank/` 兜底(主题文件头都写了 `触发:` 动作词)。

## 库内细路由 (我要做的事 → 读哪份)

| 我要做的事 | 读 |
|---|---|
| **改代码前扫陷阱 / 跑 git 命令前** | [pitfalls/_index.md](pitfalls/_index.md) —— 7 类, 按动作选类 |
| 写 / 跑测试, 查基线数字 | [testing/_index.md](testing/_index.md) —— 基线单点 [baseline.md](testing/baseline.md) |
| 查配置键 | [config-reference/_index.md](config-reference/_index.md) |
| 规则 / 条件 / 动作 | [rule-system/_index.md](rule-system/_index.md) |
| 架构 / 主循环 / 数据层 / 任务队列 / WEB 运行时 | [systemPatterns/_index.md](systemPatterns/_index.md) |
| 找功能位置 / 加新模块 | [modules/_index.md](modules/_index.md) |
| 命名 / 风格 / 协作约定 | [conventions/_index.md](conventions/_index.md) |
| 项目是什么 / 领域知识 | [productContext.md](productContext.md) · [projectbrief.md](projectbrief.md) |
| 技术栈 / 环境 / 约束 | [techContext.md](techContext.md) |
| 已实现 / 规划中 | [progress/_index.md](progress/_index.md) |
| **现在做到哪 / 上次做到哪** | [activeContext/](activeContext/_about.md) —— 会话滚动状态切片; 读法 `commands run kb.active` |
| **下一步做什么** | `想法.md`(设计草稿待办) + [progress/roadmap.md](progress/roadmap.md)(规划中) |
| **真机走查清单** | [checklists/_index.md](checklists/_index.md) —— 做走查时逐条勾 |
| 跨会话任务档案 (立档 / 查档) | [tasks/_index.md](tasks/_index.md) |
| 计划外问题池 (8 类 × 两档) | [issues/_index.md](issues/_index.md) |
| **计划 / 报告 / 一件事的全部材料** | [plans/_index.md](plans/_index.md) · [reports/_index.md](reports/_index.md) · [_doc-map.md](_doc-map.md) |
| **跑项目命令** | `.commands/` 包(每包一 `config.toml`), 经 `commands` 引擎按 task id 调; 文档不许抄命令(`commands run doc.drift` 判红) |

## 生成物 (冲突时**重跑脚本**, 不要手改)

- 各目录的 `_index.md` —— `commands run kb.index` 扫主题文件的三行头元数据生成
- [tasks/_index.md](tasks/_index.md) —— `commands run kb.index` 扫档案 `Status` / `Summary` 生成
- [issues/_index.md](issues/_index.md) —— create-issue skill 的生成器重建
- [plans/_index.md](plans/_index.md) / [reports/_index.md](reports/_index.md) / [_doc-map.md](_doc-map.md) —— `gen_docs_index.py` / `gen_doc_map.py`(专题视图)
- 新增目录 / 超 cap / 流水触顶的处置见 [memory-bank skill](../.agents/skills/memory-bank/SKILL.md) —— 改目录须同时改本细路由, 少一处守卫就红。

## 一分钟速览

- **项目**: `auto-qb` — 基于 `qbittorrent-api` 的 PT 种子自动化管理工具 (标签/分类/HR 管理、辅种分组与缺文件检查、自定义规则引擎、tracker 级限速、全局限速曲线)。
- **形态**: 单机长驻 Python 程序, 入口 `python src/auto-qb.py [config.yml]`, 主循环 2s tick, 任务队列驱动。
- **核心设计**: 所有工作统一为带 interval 的任务进单一时间优先堆; 增量同步 + `TorrentRecord` 独占种子数据; **主循环单线程, 是唯一改队列与 state_file 的线程**(详见 [systemPatterns/](systemPatterns/_index.md))。
- **测试**: `pytest` + `tests/helpers.py` 全 Fake(无需真实 qBittorrent); 基线数字单点维护于 [testing/baseline.md](testing/baseline.md), 勿在他处手抄。
- **文档**: 根 `README.md` 与 `想法.md` 是上游文档; 本库是代码实况核对版。
- **制品形态**: 记一件事之前先读 [conventions/doc-forms.md](conventions/doc-forms.md) —— 四工位决策树与协议单点。

> **黄金法则与常用命令: 单点定义在根 [AGENTS.md](../AGENTS.md)** —— 本文件不复述。
