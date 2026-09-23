# progress — 路线图与项目状态

> **本文件是生成物, 不要手改** —— 由 `commands run kb.index` 扫描本目录主题文件的三行头元数据生成; 新增 / 改名 / 改摘要后重跑即可, 冲突也只需重跑。
> 库内细路由见 [memory-bank/README.md](../README.md)。
> **检索纪律**: 先读本索引定位, 再按需打开单个主题文件 —— **不要整读本目录**。
> **摘要**: 做过的(已实现, 按域分 6 份)、还没做的(路线图)、已知缺陷、演进脉络、给 AI 的实现建议。
> **触发**: 做过没有, 已实现, 规划中, 路线图, 已知 BUG, TODO, 演进, 实现建议

## 主题

| 主题 | 一句话 | 触发词 |
|---|---|---|
| [evolution.md](evolution.md) | 从 git log 提炼的演进脉络 —— 用来理解「为什么现在是这样」。 | 演进, 为什么是这样, 历史脉络, 设计由来 |
| [implemented-core.md](implemented-core.md) | 摘要: 后端主干与内置功能的落地记录 —— 客户端 / 主循环 / 数据层 / 任务队列 / 托盘 / 通知 / 标签 / HR / 分组。 | 做过没有, 主循环, 数据层, 任务队列, 托盘, 通知, 标签, HR, 分组, 单实例锁 |
| [implemented-rules.md](implemented-rules.md) | 摘要: 规则引擎、checking 动作、限速(单种 + 全局曲线)、fail-fast 配置校验的落地记录。 | 做过没有, 规则, 条件, 动作, checking, 限速, 配置校验 |
| [implemented-testing.md](implemented-testing.md) | 摘要: 测试基座与副作用治理的落地记录; 语料回放线见 [roadmap.md](roadmap.md) 的对应小节。 | 做过没有, 测试, 副作用, 守阵, 基线 |
| [implemented-tooling.md](implemented-tooling.md) | 摘要: 依赖现代化与知识库机制本身的落地记录。 | 做过没有, 依赖, uv, 知识库, 立档, 索引 |
| [implemented-webui-perf.md](implemented-webui-perf.md) | 摘要: 前端性能、交互时序与状态色的落地记录 —— app.js 拆分 / 轮询节拍 / 跟手性三波次 / 乐观 UI / 状态色收口 / 组件库。 | 跟手性, 性能, 乐观 UI, 轮询节拍, 状态色, app.js 拆分, 组件库, 命令埋点 |
| [implemented-webui.md](implemented-webui.md) | 摘要: 前端界面与视图的落地记录 —— 设置页 / 追剧视图 / 双界面 / 错误原因 / 各轮修复。 | WEB UI 做过没有, 前端功能, 设置页, 视图, 状态色, 修复轮次, 双界面 |
| [known-bugs.md](known-bugs.md) | 来自 `想法.md` 的已知缺陷, 以及代码里仍留着的 TODO 清单。 | 已知 BUG, TODO, 待办, 缺陷, 未修 |
| [roadmap.md](roadmap.md) | 尚未实现的功能线、仍敞着的设计取舍, 以及「已定案、别改回去」的方向性口径。 | 规划中, 下一步做什么, 路线图, 已定案口径, 别改回去, 未实现 |
| [suggestions.md](suggestions.md) | 基于现有架构的延伸方向 —— 动手改架构 / 工程化前先看这里有没有既定建议。 | 实现建议, 延伸方向, 工程化, 知识库改进, 架构建议 |
