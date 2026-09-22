# auto-qb Memory Bank (AI 知识库索引)

> 面向 AI 助手的项目知识库。目标: 让 AI 在不重读全部源码的前提下, 快速建立对项目的准确心智模型, 并安全地修改代码。
> **若代码与本文冲突, 以代码为准并回写更新本文。**
> **路由单点**: 按任务该读哪份文档, 见根 [AGENTS.md](../AGENTS.md)「知识库路由」表 —— 本文件不复述, 免得两处各自演化。

## 库内索引 (两个生成物, 冲突时重跑脚本而不是手改)

- [tasks/_index.md](tasks/_index.md) —— 跨会话任务档案 (立档 / 查档), 由 `python .agents/skills/memory-bank/scripts/gen_tasks_index.py` 生成
- [issues/_index.md](issues/_index.md) —— 计划外问题池 (8 类类型 × 便签 / 标准两档), 由 create-issue skill 的生成器重建

## 一分钟速览

- **项目**: `auto-qb` — 基于 `qbittorrent-api` 的 PT 种子自动化管理工具 (标签/分类/HR 管理、辅种分组与缺文件检查、自定义规则引擎、tracker 级限速、全局限速曲线)。
- **形态**: 单机长驻 Python 程序, 无包管理配置 (pip 装依赖即用), 入口 `python src/auto-qb.py [config.yml]`, 主循环 2s tick, 任务队列驱动。
- **核心设计**: `QbManager` 由 6 个 mixin 组合; 所有工作 (种子刷新/规则/内置功能/校验轮询) 统一为带内置 interval 的任务, 进单一时间优先堆; `TorrentStore.apply_sync` 走 qB `/api/v2/sync/maindata` rid 增量同步(只对变化种子调 `apply_delta`), `TorrentRecord` 是种子数据的唯一所有者(快照 slot + `_raw` 兜底); `QbApi` Facade写后同步快照; 主循环单线程, 唯一修改队列与 state_file 的线程。
- **测试**: `pytest` + `tests/helpers.py` 全 Fake (无需真实 qBittorrent; 另有 `FakeQbServer` 本地假 HTTP 服务, 供真实 `qbittorrent-api`/requests 栈的集成测试)。基线数字 (passed/skipped/覆盖率) 单点维护于 [testing.md](testing.md) 顶部, 勿在他处手抄; 全量耗时实测见 [pitfalls.md](pitfalls.md)「本机测试速度画像」(带 `--cov-branch` 约 32 秒 / `--no-cov` 约 25 秒)。
- **文档**: `README.md` (用户视角) 与 `想法.md` (设计草稿) 是上游文档; 本知识库是代码实况的核对版, 发现漂移时回写更新 (遗留差异见 [pitfalls.md](pitfalls.md))。

## 黄金法则与命令

> **改代码的黄金法则**(幂等 / 保守默认 / 状态持久化 / fail-fast / 单一写线程 / 范围守恒 / 请求边界)**与常用命令, 单点定义在根 [AGENTS.md](../AGENTS.md)** 的「黄金法则」与「命令」两节; 测试命令与基线另见 [testing.md](testing.md)。本文件不复述。
