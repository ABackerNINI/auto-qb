# modules — 模块地图

> **本文件是生成物, 不要手改** —— 由 `commands run kb.index` 扫描本目录主题文件的三行头元数据生成; 新增 / 改名 / 改摘要后重跑即可, 冲突也只需重跑。
> 库内细路由见 [memory-bank/README.md](../README.md)。
> **检索纪律**: 先读本索引定位, 再按需打开单个主题文件 —— **不要整读本目录**。
> **摘要**: 包入口与「在哪里改」速查、核心模块(按 config / 运行时 / 领域切三份)、前端契约、mixins、rules 与依赖方向。
> **触发**: 模块, 找功能位置, 在哪里改, 加新模块, mixins, rules, 依赖方向, 前端契约

## 主题

| 主题 | 一句话 | 触发词 |
|---|---|---|
| [core-config.md](core-config.md) | 配置层: 模型 / 校验 / 解析 / 写回 / UI 元数据 / 影响分级。 | config, 配置, 模型, 校验, 解析, 写回, schema, impact |
| [core-domain.md](core-domain.md) | 种子数据层 / 通知 / 托盘 / 自启 / WEB 后端与前端 / 曲线 / 集数 / 剧集 / 导出。 | torrents, notify, ui, autostart, web, static, curves, episodes, tvshows, exporter |
| [core-runtime.md](core-runtime.md) | 入口 / 主协调者 / 表现层门面 / 客户端 / 队列 / Facade / 锁 / 工具 / 日志 / 错误根。 | cli, qbmanager, web_runtime, qbclient, taskqueue, qbapi, locking, utils, logging, errors |
| [mixins.md](mixins.md) | `QbManager` 的 mixin 拆分与组合方式。 | mixins, 职责拆分, 组合, QbManager |
| [overview.md](overview.md) | 包入口在哪、要改某功能该动哪个文件 —— 进本目录前先读这一份。 | 包入口, 在哪里改, 改哪个文件, 入口, src 布局 |
| [rules-and-deps.md](rules-and-deps.md) | 规则插件框架、测试对应关系与单向依赖图。 | rules, 插件框架, tests, 依赖方向, 单向, 无环 |
| [webui-static-contract.md](webui-static-contract.md) | 前端资产(模板 / 逻辑层 / 样式 / 图标)的契约与目录约定。 | 前端契约, static, 模板, shared, atlas, prism, 图标 |
