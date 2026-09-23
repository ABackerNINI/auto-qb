# conventions — 编码规范与项目约定

> **本文件是生成物, 不要手改** —— 由 `python .agents/skills/memory-bank/scripts/gen_kb_index.py` 扫描本目录主题文件的三行头元数据生成; 新增 / 改名 / 改摘要后重跑即可, 冲突也只需重跑。
> 库内细路由见 [memory-bank/README.md](../README.md)。
> **检索纪律**: 先读本索引定位, 再按需打开单个主题文件 —— **不要整读本目录**。
> **摘要**: 协作约定与跨仓库红线、代码风格与设计约定、流程约定(dry_run/幂等/Git/闸门)、WEB UI 产出口径与令牌。
> **触发**: 约定, 规范, 命名, 风格, 协作, 跨仓库, dry_run, 幂等, Git, WEB UI 口径

## 主题

| 主题 | 一句话 | 触发词 |
|---|---|---|
| [code-style.md](code-style.md) | 函数设计 / 可测试性 / 模块职责 / 命名 / 类型注解 / 性能 / 注释 / 日志 / 格式化 / dataclass / 其它工程约定。 | 命名, 类型注解, 函数设计, 可测试性, 模块职责, 注释, 日志, 格式化, yapf, dataclass |
| [collaboration.md](collaboration.md) | 用户明示的协作约定、跨仓库操作红线、生产配置禁令 —— 动手改协作方式前先读。 | 协作约定, 跨仓库, 红线, 授权, 生产配置, 多 clone |
| [doc-forms.md](doc-forms.md) | 计划 / 报告 / issue / 任务档案四类制品的「放哪、叫什么、状态怎么流转、索引谁生成」—— 记一件事之前先读这张决策树。 | 写计划, 写报告, 入池, 立档, 制品放哪, 文档形态, doc-topic, 状态词, 计划入库, 报告入库, 认领链, 计划改版 |
| [process.md](process.md) | dry_run 纪律、幂等与去重、Git 约定、提交闸门自动执行。 | dry_run, 幂等, 去重, Git 约定, 提交闸门 |
| [webui.md](webui.md) | 菜单/入口分层、令牌分工、HTML dark 主题 —— 前端产出口径的唯一出处。 | WEB UI 约定, 菜单分层, 令牌, 主题, dark, HTML 产出 |
