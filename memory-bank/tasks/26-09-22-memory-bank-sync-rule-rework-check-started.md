# 26-09-22-memory-bank-sync-rule-rework-check-started.md — 开工同步规则重写与 --check-started 开工自检

**Status:** Done
**Added:** 2026-09-22
**Updated:** 2026-09-22
**Summary:** AGENTS「会话协议·开始」①与 rebase 禁令互斥(a1f3476 补丁漏改①)致规则静默失效; 4 处 always-on 入口一次改全为 fetch + ls-remote + merge --ff-only(锚点改"首个执行动作前"+问答轮豁免), preflight 落后判据 ls-remote 现查并新增 --check-started 只读开工自检; skill 自测 34 passed / 全量 1189+1 / 两项真跑 exit 0
**Topics:** memory-bank-git-rules

## 原始请求

用户 2026-09-22 20:44 指派:「分析为什么 AGENTS 中的"**开始**: ①**先拉远程**"未生效」; 21:32 指令「先同步然后执行 1-4, 最后详细解释第 5 项」(1=①与复述点改写 / 2=锚点 / 3=ls-remote 判据 / 4=机检文案); 21:58「授权修改, 然后实施 5」(显式授权动通用资产两处入口 + 实施开工自检); 22:07「提交」。

## 思考过程与决策

- **根因六层**(现场取证): ①字面命令 `pull --rebase` 与同文件 L62 禁令互斥(禁令 a1f3476 07:38 落地漏改①, `git log -S` 证实①文本自 09-21 15:17 后未动); 触发锚点「会话开始」与黄金法则 7(问答轮只作答)互斥, 执行动作开始后无条款补触发; 前置"拉取前清空工作区"在 stash 被禁下断裂; `status -sb` 快照 + refs/remotes 静默丢弃给假绿灯(实测本 clone 落后而 status 报齐平); 机检错位(preflight 只在提交时跑, 且 L371/L373 建议文本写着"先 rebase"); 多 clone 并行磨掉收益(当晚 6 个纯同步 merge, c9c347c 自证"双方同日修同一批 issue")。
- **同步命令取舍**: 取 fetch + merge --ff-only FETCH_HEAD(树净时), 不取裸 pull(分叉时静默产生 merge commit)也不取 rebase(本 shell 已禁); 落后判据只认 ls-remote 每次现查(网络真值), status -sb 降级为参考; 替代路径锚回 history-integration.md。
- **锚点语义**: 问答/只读轮次显式豁免①, 首个执行动作(改文件 / 跑测试 / 任何 git 写操作)前必须完成 —— 与黄金法则 7 对齐, 消除"会话开始已过"的失效窗口。
- **通用资产判别法**: SKILL.md / ai-lib.md 只承载机制(命令用 `<主线远端>` 占位或指针), 本仓库事实(远端名 gitee)留在 AGENTS.md 与 copilot-instructions.md; preflight 消息文本保持通用(不写本仓库 pitfalls 路径), repo 事实全在 .commit-flow.toml。
- **自检刻意无状态**: --check-started 不存"已同步"标记文件 —— 不引入第二个会陈旧的快照; 连 fetch 都不做(不写任何 ref/对象), 与 #5 提交期检查的唯一区别。
- **挂 preflight 而非独立脚本**: 复用配置解析 / PASS-WARN-STOP 协议 / GBK 兜底, 分类逻辑抽纯函数 classify_sync 便于自测。

## 实现计划

无需计划文档(规则文本修正 + 单脚本增强); 实施顺序: 只读取证 → 同步本 clone → 修正 1-4 → 授权补两处入口 → 实施第 5 项 → 立档随主提交。

## 子任务状态表

| 子任务 | 状态 |
|---|---|
| 六层根因取证分析(reflog / ls-remote / -S 文本考古 / 上限检查) | 完成(2026-09-22) |
| 本 clone 同步: fetch + merge --ff-only 5197679→5ef10ba | 完成(2026-09-22) |
| 修正 1-4(①重写 + collaboration 两处 + copilot 入口 + preflight 判据与文案) | 完成(2026-09-22) |
| 授权同步 SKILL.md / ai-lib.md(4 处入口改全) | 完成(2026-09-22) |
| 第 5 项 --check-started(classify_sync 七状态 + 主流程只读短路 + 自测 7 例 + 机检句) | 完成(2026-09-22) |
| 提交 + 推送 + 幽灵 diff 核查 | 本笔(随主提交入库) |

## 进度日志

- 2026-09-22 20:44-21:20 — 只读取证: `-S 'pull --rebase'` 证实①文本 09-21 15:17 后未动而禁令 07:38 落地; reflog 当日 4 pull / 6 merge / 0 rebase, 无人按①原文执行; status -sb 假绿灯现场(远端 c5b1e37→93c0155, 本地连对象都没有); preflight L371/L373 处置文本仍在引导"先 rebase"。
- 2026-09-22 21:32-21:52 — 用户指令执行 1-4: 本 clone fetch + ff-only 同步; AGENTS.md ①重写 + collaboration.md L12/L16 + copilot-instructions.md; preflight 落后判据 ls-remote 化 + 文案去 rebase; SKILL.md / ai-lib.md 按通用资产规则暂不动并报请授权。
- 2026-09-22 21:58-22:07 — 用户「授权修改, 然后实施 5」: 两处入口同步(4 处改全, `pull --rebase` 现行文档归零); preflight 新增 --check-started(classify_sync 纯函数 + 主流程只读短路 + AGENTS.md 机检句 + SKILL.md 机检钩子引用); 实测: skill 自测 34 passed / 全量 1189 passed + 1 skipped / AGENTS.md 6568/8000 / preflight 端到端与 --check-started 真跑均 exit 0; 跨 clone 查重无同名 slug, 立档随主提交。
