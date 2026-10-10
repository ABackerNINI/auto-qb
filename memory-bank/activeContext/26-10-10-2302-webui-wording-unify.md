# WEBUI 文案对齐 qB(全量术语排查)

> 摘要: 用户要求把 WEBUI 文案统一到 qB 口径, 且不止点名的几处(「上传/下载 vs 上行/下行 vs 取流中/供流中」), 要"全面排查"(例证:「做种」在 qB 叫「做种数」)。本轮**只摸底 + 出报告**。基准 = 本机 qBittorrent 源码官方 zh_CN 译文(`D:\Projects\Else\qBittorrent\src\webui\www\translations\webui_zh_CN.ts` 为主 + `src/lang/qbittorrent_zh_CN.ts` 交叉); 打法 = grep 全量枚举 `shared/` 可见中文 × qB 逐条对照。报告 `reports/26-10-10-2237-report-webui-wording-unify.html` 覆盖 6 概念域(列头字段 / 状态词 / 动作菜单 / 传输方向词 / 对端状态词 / 保持不动与自有概念), 约 32 条需改术语 + ~50 处方向词字面改点 + 5 处对端状态词, 涉 16 个 shipped 文件。**关键**: qB 的 WebUI 与 GUI 译文在个别词上不同(Seeds: WebUI「种子」/ GUI「做种数」), 须先选边; 我方状态词系统性多加「中/已」且自身不统一。报告列 6 个决策点待拍板, 未动任何生产文件。
> 最后活动: 2026-10-10 23:02

**Refs:** memory-bank/tasks/26-10-10-webui-wording-unify.md

## 正在进行

- **待用户拍板报告 §10 的 6 个决策点**(D-Base 选边 / D-State 状态词 / D-C 动作词 / D-Dir 方向词 / D-Peer 对端词 / D-Sync 设计稿同步)。拍板后按报告 §09 的影响面出 `plans/` 实施计划(逐文件改点 + 守阵同步), 再动手改文案。

## 关键结论(供后续实施参考)

- **qB 无「上行/下行」**(全库 grep 零命中), 传输方向一律「上传/下载」;「取流/供流」是自造词。→ 方向词族约 50 处字面替换即可。
- **qB 两版译文不一致**(报告 §02 有全表): Seeds / Completed / All-time share ratio / Session waste / Connected peers / 剩余空间 / Trackerless —— 第一件事是"以 qB WebUI 还是 GUI 为准"(推荐 WebUI, 形态同构)。
- **我方状态词系统性偏差**: qB 用「下载/做种/校验/暂停/排队/等待/错误」(不加「中」不加「已」), 我方大量「下载中/做种中/校验中/已暂停/等待下载」, 且**自身不统一**(同一错误态: 抽屉「出错」vs 列表「错误」;「做种」vs「做种中」)。
- **对端状态词 6 种叫法**: 07「取流中/供流中」、08「正在从我这下载/正在给我上传」、07/09 chips「上行中/下行中」, 且视角不统一(对端 vs 我方); 07 同面板图例与 chips 用词还不一致。
- **别把状态「做种」改成方向词「上传」** —— 两者不同轴; 且状态里的"上传态"在 qB 就叫「做种」。
- 我方自有概念(站点/H&amp;R/跳检/导出/通知/HR 核实)无 qB 对应词, 不算"不符"。

## 后续候选(未开工)

- 收术语单点: 是否把方向词/状态词收成常量(按 `conventions/webui.md`「单点口径原则」) —— 属实施期决策。
- 设计稿 `resources/detail-panel-templates/*.html`(10 文件 133 处)与 `docs/configuration.md`、后端 schema help(`config/schema/groups.py`)的同步。
