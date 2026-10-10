# 26-10-10-webui-wording-unify — WEBUI 文案对齐 qB(全量术语排查)

**Status:** In Progress
**Added:** 2026-10-10
**Updated:** 2026-10-10 23:02
**Topics:** webui-wording-unify
**Summary:** 用户要求把 WEBUI 的文案统一到 qB 的口径, 且不止其点名的几处 —— 「有的地方是"上传"/"下载", 有的地方是"上行"/"下行", 还有"取流中"/"供流中"的说法, 需要统一成 qb 的文案, qb 中没有的向 qb 的文案靠近而不是随意新造词」; 追加要求「全面的排查, 不只是我提到的几个点, 比如"做种"在 qb 中叫"做种数"」。本轮**只做摸底 + 出报告**(不改任何代码/文案): 以本机 qBittorrent 源码的官方 zh_CN 译文为基准(`src/webui/www/translations/webui_zh_CN.ts` 为主 + `src/lang/qbittorrent_zh_CN.ts` 交叉), 对 `shared/` 全部面向用户的中文文案逐概念域对照, 产出报告 `26-10-10-2237-report-webui-wording-unify.html`(6 概念域: 列头字段 / 状态词 / 动作菜单 / 传输方向词 / 对端状态词 / 保持不动与自有概念)。关键结论: ①qB 无「上行/下行」, 一律「上传/下载」; ②「取流中/供流中」为自造词, 同一语义在 07/08/09 有 6 种叫法且视角不统一; ③qB **WebUI 与 GUI 译文在个别词上不同**(Seeds: WebUI「种子」/ GUI「做种数」), 须先选边; ④我方状态词系统性多加「中/已」且自身不统一(出错 vs 错误、做种 vs 做种中)。报告末尾列 6 个决策点(D-Base/D-State/D-C/D-Dir/D-Peer/D-Sync), 待用户拍板后出逐文件实施计划。
**Refs:** memory-bank/reports/26-10-10-2237-report-webui-wording-unify.html,memory-bank/activeContext/26-10-10-2302-webui-wording-unify.md,memory-bank/testing/baselines/26-10-10-2302-webui-wording-unify.md

## 原始请求

> 用户(2026-10-10): 「WEBUI统一文案: 有的地方是"上传"/"下载", 有的地方是"上行"/"下行", 还有"取流中"/"供流中"的说法, 需要统一成qb的文案, qb中没有的向qb的文案靠近而不是随意新造词. 先写一个报告, 理清哪些文案不统一需要更改.」
>
> 用户(2026-10-10, 追加): 「我需要的是全面的排查, 不只是我提到的几个点, 比如"做种"在qb中叫"做种数"」

## 思考过程与决策

- **请求边界判定**: 第一轮「先写一个报告」= 执行任务(产出报告制品); 追加「全面排查」把范围从"方向词"扩到"全量术语对照"。
- **基准取法(不靠记忆)**: qB 源码在本机 `D:\Projects\Else\qBittorrent`, 直接读官方 zh_CN 译文, 不重拉、不用训练记忆。**发现 qB 两版译文本身有差异** —— 故报告以 qB **WebUI** 版为主基准、GUI 版作交叉参考, 并把差异单列一表(Seeds / Completed / All-time share ratio / Session waste / Connected peers / 剩余空间 / Trackerless)。
- **"qB 未收录"的列名处理**: `Down/Up Speed`、`Address`、`Client`、`Relevance`、`Peer`、`Amount Left`、`Last Activity` 等 qB 两版都没译 —— 按用户口径"向 qB 语言习惯靠拢"(用方向词、"已X"式前缀), 不另立名词; 未把这些算作"不符"。
- **排除项**: 我方自有概念(站点 / H&amp;R / 站数 / 版本 / 剧名·集 / 详细信息 / 导出 .torrent / 跳检 / HR 在线核实 / 通知面板…)无 qB 对应词, 不算"不符"; qB 的状态词「做种」(Seeding) **不得**被方向词的「上传」替换(两者是不同轴)。
- **只摸底不改**: 本轮明确不改任何生产文件; 报告给出「改 / 保持 / 待拍板」判定与 6 个决策点, 实施留待拍板。

## 实现计划

- **P1(已完成) 基准采集**: 读本机 qB 两份 zh_CN 译文(src/webui + src/lang), 建 qB 术语表(列头/状态/动作/统计/枚举 GUI-WebUI 差异)。
- **P2(已完成) 我方清点**: grep 全量枚举 `shared/` 的可见中文文案(列模型 label、drawer 行、drawer_tpl 各变体、ctx-menus、dialogs、config_hub、hr*、filters、commands), 按概念域归类。
- **P3(已完成) 对照出报告**: 单文件 dark HTML, 落 `reports/` 并重建索引。
- **P4(待拍板) 决策**: D-Base(WebUI/GUI 选边)/ D-State(状态词去「中/已」)/ D-C(动作词是否严格贴 qB)/ D-Dir / D-Peer / D-Sync。
- **P5(未开工) 实施**: 逐文件改点 + 守阵同步(见报告 §09)+ 设计稿 `resources/` 与文档同步; 出 `plans/` 实施计划后再动手。

## 子任务状态表

| 步骤 | 内容 | 状态 |
|---|---|---|
| P1 | qB 基准术语表(本机译文, WebUI 主 + GUI 辅) | Done |
| P2 | 我方 `shared/` 可见文案全量清点 | Done |
| P3 | 对照报告(单文件 HTML)+ 索引 | Done |
| P4 | 6 个决策点拍板 | Open |
| P5 | 实施(逐文件改点 + 守阵 + 设计稿/文档同步) | Open |

## 进度日志

- **2026-10-10 23:02** 开工 `my-commit-flow.sync`(已同步 `e4282642`)→ 首版报告(仅方向词/对端状态词)落 `reports/26-10-10-2237-report-webui-wording-unify.html` → 用户追加「全面排查」→ 改为读**本机** qB 源码译文(`D:\Projects\Else\qBittorrent`)建全量基准, 发现 qB WebUI 与 GUI 译文在 Seeds 等词上不一致 → 报告扩写为 6 概念域全量对照(含决策点)→ `kb.index` 重建 → 收尾: 立本档案 + 会话切片 + 基线切片 + 报告补 `doc-refs`。
