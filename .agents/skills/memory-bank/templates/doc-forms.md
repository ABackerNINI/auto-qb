# 文档形态与制品协议 —— TODO: 一句话概述本项目的四工位口径

> 摘要: TODO 计划 / 报告 / issue / 任务档案四类制品在本项目「放哪、叫什么、状态怎么流转」—— 记一件事之前先读这张决策树。
> 触发: TODO 写计划, 写报告, 入池, 立档, 制品放哪, 文档形态, doc-topic, 状态词, 计划入库, 报告入库, 认领链, 创建方式, kb.new

<!--
复制填空模板(memory-bank skill templates/, 骨架先例: baseline.md): 复制到
memory-bank/conventions/doc-forms.md 后逐节把 TODO 换成项目事实, 全部填完删掉本注释块。
协议层(doc-* meta 字段名 / 状态 5 词表 / 认领链机制)由 memory-bank skill 单点定义,
**照抄不改** —— 本项目要填的只有: 目录名、工位到目录的映射、命名口径、创建命令表。
-->

## 四工位 (类型 token = 新件文件名的第二段)

TODO: 工位语义固定, 只有「目录」列按本项目实际落位改; 载体(Html / Markdown)与寿命照抄:

| 工位 | 回答什么 | 目录 | 载体 | 寿命 | 唯一权威 |
|---|---|---|---|---|---|
| issue | 要不要修、什么时候修 | TODO: memory-bank/issues/ | HTML | 终态即冻结 | 优先级与排期 |
| plan | 怎么修、为什么这么修 | TODO: memory-bank/plans/ | HTML | **拍板后冻结** | 方案与取舍 |
| report | 当时现场是什么样 | TODO: memory-bank/reports/ | HTML | 出厂即冻结 | 证据快照 |
| task | 实际怎么修、做到哪了 | TODO: memory-bank/tasks/ | Markdown | **唯一滚动更新** | 执行与验证数字 |

(照抄别删)每条事实只在一个工位有权威, 其余件只引用不重写 —— 重写必然漂移。

## 决策树: 要记一件事 → 放哪儿

TODO: 按本项目目录改「放」列; 保留 Form 判定两问(读者在做事还是理解? 在获取技能还是应用技能?), 它切内容形态、与四工位正交。

- 撞见计划外的问题, 暂不修 -> TODO: issues 目录与入池命令(create-issue skill)
- 要改动, 需方案与拍板 -> TODO: plans 目录
- 审计 / 故障取证 / 可行性分析 -> TODO: reports 目录
- 跨会话推进的专题 -> TODO: tasks 目录与命名(YY-MM-DD-<领域>-<专题>.md)
- 本次会话做到哪 -> TODO: active-context 目录(切片, 读法 = kb.active)
- 长期结论 / 已实现事实 -> TODO: 主题文档放哪(conventions/ · architecture/ · projectbrief.md)

## 命名 (新件强制; 存量豁免)

TODO: 新件 = `YY-MM-DD-HHMM-<type>-<topic>.html`(时间戳用 `kb.time stamp` 取当前值, 禁手工推算);
一篇一件事; 计划改版 = 同文件内变更记录段 + 抬 doc-updated, 禁止 `-v2` / `-roundN` 新文件。
TODO: 目录名或前缀与上面不同的, 在这里写清差异与理由。

## meta 协议 (doc-*) 与状态词

TODO: 字段名照 skill 单点照抄不改(doc-type / doc-topic(单值 kebab 主键, 多对多走 doc-refs) /
doc-status / doc-added / doc-updated / doc-refs; 档案用 `**Status:**` 等同义字段);
状态 5 词 = `Open` / `In Progress` / `Done` | `Dropped` | `Superseded`(与档案 4 词表不同, 别互相套用)。
TODO 填: 状态词表与主键校验挂在本项目哪个机检入口(kb.check / 可选的 kb.docmap)。

## 认领链

TODO: issue 被认领 -> 两侧都记引用(issue 的 doc-refs 与档案的 `**Refs:**` 双向声明);
值 = 仓库根相对路径, 多目标英文逗号一行写全; 引向无法反向声明的文件 = 单向链, 判红。
TODO 填: 本项目的机检挂载点(可选守卫 kb.docmap, 见 PORTING「项目可选守卫勿默认移植」——
认领链建起来之前不启用, 启用后挂提交闸门)。

## 创建/更新方式 (命令化)

TODO: 把下表 task id 列换成本项目 .commands/kb/config.toml 里的实际 id; 文档里只写
task id, 不抄命令本体(漂移守卫会判红手抄):

| 动作 | 命令 (task id) | 派生 (零手写) |
|---|---|---|
| 新建计划 / 报告 / 任务档案 / issue / 坑档 / 基线切片 | TODO: kb.new ... | 戳 / 命名 / 头部 / SLOT |
| 翻转状态 | TODO: kb.status | 词表校验 / 抬 doc-updated |
| 改版落盘 | TODO: kb.bump | 抬时间戳 + 变更记录追加 |
| 收尾机械面 | TODO: kb.wrap | 切片活动 + 档案进度日志 |
| 认领链回填 | TODO: kb.ref | 双向声明一次落盘 |
