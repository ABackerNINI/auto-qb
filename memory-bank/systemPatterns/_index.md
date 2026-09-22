# systemPatterns — 架构与运行时

> **本文件是生成物, 不要手改** —— 由 `python .agents/skills/memory-bank/scripts/gen_kb_index.py` 扫描本目录主题文件的三行头元数据生成; 新增 / 改名 / 改摘要后重跑即可, 冲突也只需重跑。
> 库内细路由见 [memory-bank/README.md](../README.md)。
> **检索纪律**: 先读本索引定位, 再按需打开单个主题文件 —— **不要整读本目录**。
> **摘要**: 组件总览、主循环与每轮数据流、数据层增量同步、任务队列与异步校验、WEB UI 运行时三份、客户端与状态。
> **触发**: 架构, 主循环, 数据层, 任务队列, 线程模型, WEB 运行时, 响应性, 配置编辑器, 状态持久化

## 主题

| 主题 | 一句话 | 触发词 |
|---|---|---|
| [client-and-state.md](client-and-state.md) | 启动期兼容校验、`QbApi` Facade 与状态持久化 —— 三个小主题合成一份。 | QbApi, Facade, 兼容校验, 状态持久化, state_file, RuleEngineMixin |
| [data-layer.md](data-layer.md) | `torrents.py` 的增量同步、变化集与 `TorrentStore` —— rid 语义一处说清。 | 数据层, store, 增量同步, maindata, rid, 变化集, apply_sync |
| [main-loop.md](main-loop.md) | 主循环 `qbmanager.py` 的节拍、分层与每轮 `_refresh_torrents` 的数据流。 | 主循环, tick, 节拍, 数据流, refresh_torrents, 分层 |
| [overview.md](overview.md) | 有哪些组件、谁负责什么 —— 进本目录前先读这一份。 | 组件, 总览, 架构, 有哪些模块, 谁负责什么 |
| [taskqueue.md](taskqueue.md) | 单队列模型、两个动词、线程约束与 full-checking 全流程(含断点续跑)。 | 任务队列, taskqueue, add_task, run_due, 线程模型, 异步校验, full-checking, 断点续跑 |
| [web-config-editor.md](web-config-editor.md) | `web.py` + `config/schema.py` + `config/writer.py` 三件套的分工。 | 图形化配置, 设置页, schema, writer, 配置树 |
| [web-responsiveness.md](web-responsiveness.md) | 按视图回传、窗口化、节拍对齐、命令唤醒 —— 响应性那一整波的设计。 | 响应性, 跟手性, 按视图回传, 窗口化, 节拍, 命令唤醒, P0, P1 |
| [web-runtime.md](web-runtime.md) | `web.py` 的线程模型 —— 主循环与 Web 线程的边界与协作。 | WEB UI 线程, web.py, 线程模型, 主循环解耦 |
