# auto-qb Memory Bank (极简路由)

> 库内单点路由。**检索纪律: `kb.active`(最近) → 本路由 → grep 兜底**(`grep -rn "<词>" memory-bank/`)。
> 历史件(`tasks/` `plans/` `reports/` `issues/`)冻结不改 —— 指向已删路径的死链不修, 兜底 = grep 文件名 + `git log -- <旧路径>`。

| 我要做的事 | 去哪 |
|---|---|
| **改代码前扫陷阱 / 跑 git 前** | [pitfalls/_index.md](pitfalls/_index.md) —— 7 类触发词表, 先扫再动手(全库唯一保留的 `_index`) |
| **架构设计**(主循环/队列 · 数据与状态 · 规则引擎 · HR 分组 · WEBUI) | [architecture/](architecture/overview.md) 六包, 入口 overview |
| 项目定位 / 范围 / 领域 | [projectbrief.md](projectbrief.md) |
| 配置键权威 | 代码单点: `src/auto_qb/config/schema/` + `validate_config`(配置键不再写参考文档, 免漂移) |
| 测试基线数字 | [testing/baseline.md](testing/baseline.md) + `commands run kb.baseline`(最新基线; 只引用不手抄) |
| 真机实测 | [testing/real-machine.md](testing/real-machine.md) |
| 命名 / 风格 / 协作 / 制品协议 | `conventions/` 七件(协议单点; 制品口径入口 [doc-forms.md](conventions/doc-forms.md)) |
| **现在做到哪 / 上次做到哪** | `commands run kb.active` —— [active-context/](active-context/_about.md) 会话滚动切片 |
| 计划 / 报告 / 档案 / issue(记录层, 只读) | 人走 `commands run kb.nav`(本地导航页); agent 走 grep |
| **建件 / 翻状态 / 改版 / 收尾** | 命令化: `kb.new <族>` · `kb.status` · `kb.bump` · `kb.wrap` —— 口径见 [conventions/doc-forms.md](conventions/doc-forms.md)「创建/更新方式」 |

> 黄金法则与常用命令: 单点在根 [AGENTS.md](../AGENTS.md), 本文件不复述。
> 生成索引只剩 pitfalls 一族(`commands run kb.index` 重建, 不要手改); 新增坑档后重跑 `commands run kb.index`。
