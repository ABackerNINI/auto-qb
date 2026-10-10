# 26-10-10-webui-wording-unify — WEBUI 文案对齐 qB(全量术语排查)

**Status:** Done
**Added:** 2026-10-10
**Updated:** 2026-10-11 02:23
**Topics:** webui-wording-unify
**Summary:** 用户要求把 WEBUI 的文案统一到 qB 的口径, 且不止其点名的几处(「上传/下载 vs 上行/下行 vs 取流中/供流中」;「做种」在 qB 叫「做种数」)。P1-P3 已产出全量排查报告 `26-10-10-2237-report-webui-wording-unify.html`(6 概念域 + 6 决策点)。**P4 已拍板(2026-10-11): 实施报告, 完全对齐 qB GUI(D-Base=乙, 状态/动作词随 GUI 严格对齐), D-Peer 甲(对端词统一「上传中/下载中」), D-Sync 甲(resources/ 同步)**。P5 已实施: 基准取自本机 `qBittorrent/src/lang/qbittorrent_zh_CN.ts` 逐词抽取; shared 层 ~470 处 + resources 9 文件 ~290 处 + groups.py help + docs/configuration.md + 守阵 4 处 + e2e 10 处。要点: 状态词去「中/已」(下载/做种/校验/暂停/等待/排队/错误/丢失文件/下载元数据/校验恢复数据, pausedUP→已完成); 菜单动词 启动/停止、强制重新检查、强制重新汇报、设定位置…、速度限制…、队列顶部/向上(下)移动队列/队列底部、强制启动、按顺序下载、先下载首尾文件块、跳过哈希校验…; 确认框「重新校验」**保留**(qB GUI 确认框本身就这么写, 守阵断言同文案); state.js「已暂停」是 auto-qb 自身暂停态, 刻意不动。基线实测数字见 kb.baseline(`26-10-11-0101` 切片)。**P6 二轮补漏(2026-10-11, 用户复查指出抽屉/用户页遗漏, 报告扩 §11)**: 一轮清点面只吃了 app.js 列模型 + drawer.js general 行, 变体与 drawer_pages 页插件没进清点面。二轮补齐: 用户页表头族(对端→IP/地址、Flags→标志、正在取→文件、下载/上传→下载速度/上传速度、已发/已收→已下载/已上传、关联/关联度→文件关联、会话已发/收→会话已上传/下载); tracker 状态词(正常→工作、失败/未连接→未工作、警告→未联系、未启用→禁用、添加 tracker→添加 Tracker、下次汇报→下次重新汇报); 文件优先级(跳过→不下载、普通→正常, 一轮 §05 标「保持」系误判); general 残留(分块→区块、首末块优先→先下载首尾文件块、用户(下载)→用户、tracker→Tracker 大小写)。shared 17 文件 ~88 处 + resources 12 文件 72 处 + e2e 1 处 + 守阵 3 处; test.quick 3112 passed; 基线实测见 kb.baseline。
**Refs:** memory-bank/reports/26-10-10-2237-report-webui-wording-unify.html,memory-bank/activeContext/26-10-10-2302-webui-wording-unify.md,memory-bank/testing/baselines/26-10-11-0101-webui-wording-gui-unify.md

## 原始请求

> 用户(2026-10-10): 「WEBUI统一文案: 有的地方是"上传"/"下载", 有的地方是"上行"/"下行", 还有"取流中"/"供流中"的说法, 需要统一成qb的文案, qb中没有的向qb的文案靠近而不是随意新造词. 先写一个报告, 理清哪些文案不统一需要更改.」
>
> 用户(2026-10-10, 追加): 「我需要的是全面的排查, 不只是我提到的几个点, 比如"做种"在qb中叫"做种数"」
>
> 用户(2026-10-11, 拍板): 「实施26-10-10-2237-report-webui-wording-unify.html, 先完全对齐qb GUI, D-Peer甲;D-Sync 甲;」

## 思考过程与决策

- **请求边界判定**: 第一二轮 = 产出报告制品; 第三轮「实施…」= 显式授权动生产文件, 附带三个口径决定。
- **拍板解读**: 「先完全对齐qb GUI」= D-Base 取乙(qB GUI 为准), 且「完全」压过报告里 D-C 甲的保守推荐 → 动作词也严格贴 GUI(启动/停止/强制启动); 「先」字按"本轮以 GUI 为基准"理解, 若用户后续要换 WebUI 口径属增量轮。D-State/D-Dir 未单独点名, 由「完全对齐 GUI」覆盖(状态词贴 GUI、方向词两版同词)。D-Peer 甲/D-Sync 甲按字面执行。
- **基准取法(不靠记忆)**: GUI 词逐条从 `qbittorrent_zh_CN.ts` 按 source 抽取; 关键差异: Seeds 列=做种数(TransferListModel)但 tracker 页签 Seeds=种子(TrackerListModel)、Completed=已完成、Wasted=已丢弃(PropertiesWidget)、Seeding time=做种时间(TorrentShareLimitsWidget)、Connections=连接、Down/Up Limit=下载限制/上传限制、Force Recheck=**强制重新检查**(与 WebUI「强制重新校验」不同)、Set location=**设定位置**、队列=队列顶部/底部/向上(下)移动队列、Start/Stop=启动/停止。
- **刻意不动**: `state.js:384` statusBadge「已暂停」是 auto-qb 程序自身的暂停态(不是种子状态); commands.js `_recheckConfirm` 确认框标题/正文「重新校验」(qB GUI 确认框原文如此, 且守阵 :2189 逐字钉住); 复制族/超级做种/自动种子管理/分享率限制…; `config_hub.js` 的 schema 字段标签(配置域词汇, 报告未列); 三皮肤 CSS 注释。
- **menu 词与对话框词分离**: 跳检仅改菜单项显示名(跳过哈希校验…), 预检对话框/门控文案保留「跳检」——后者是本项目自有特性词汇(报告 §08 自有概念)。
- **连带的字符串引用**: 02 变体 `secs["基础"]` 卡片按**行 label 串**过滤(["信息哈希值 v1",…]), drawer.js 详情行 label 改名必须同步这类引用表 —— 已同步, 未记独立坑(守阵未覆盖, 若再改 label 先 grep 旧词全库)。

## 实现计划

- **P1(已完成) 基准采集**: 本机 qB 两份 zh_CN 译文, GUI 版逐 source 抽取建表。
- **P2(已完成) 我方清点**: grep 全量枚举 `shared/` 可见中文文案, 按概念域归类出报告。
- **P3(已完成) 对照报告**: `reports/26-10-10-2237-report-webui-wording-unify.html`。
- **P4(已完成) 拍板**: 见上(2026-10-11 用户消息)。
- **P5(已完成) 实施**: 有序批量替换(上下文词先于通用方向词, `按顺序下载` 加防重前缀守卫)+ ~40 组定向 Edit + 守阵/e2e 同步 + `node --check` 全绿 + `test.full` 基线(见 kb.baseline)。

## 子任务状态表

| 步骤 | 内容 | 状态 |
|---|---|---|
| P1 | qB 基准术语表(本机译文, WebUI 主 + GUI 辅) | Done |
| P2 | 我方 `shared/` 可见文案全量清点 | Done |
| P3 | 对照报告(单文件 HTML)+ 索引 | Done |
| P4 | 6 个决策点拍板 | Done |
| P5 | 实施(逐文件改点 + 守阵 + 设计稿/文档同步) | Done |
| P6 | 二轮补漏(抽屉五页签 classic + 15 变体 + resources 同步) | Done |

## 进度日志

- **2026-10-10 23:02** 开工 `my-commit-flow.sync`(已同步 `e4282642`)→ 首版报告(仅方向词/对端状态词)落 `reports/26-10-10-2237-report-webui-wording-unify.html` → 用户追加「全面排查」→ 改为读**本机** qB 源码译文(`D:\Projects\Else\qBittorrent`)建全量基准, 发现 qB WebUI 与 GUI 译文在 Seeds 等词上不一致 → 报告扩写为 6 概念域全量对照(含决策点)→ `kb.index` 重建 → 收尾: 立本档案 + 会话切片 + 基线切片 + 报告补 `doc-refs` → `ship.commit` 核 ref 报 packed-refs 陈旧假红(已记坑 `refs.md`, 复发 5→6): ⑤ 的分流根治已生效 —— 失败行直接送本条并给 `git pack-refs --all`, 一步处置后 `ship.push` 补推; 本笔提交 `fb2f93f7`。
- **2026-10-11 01:01** 用户拍板(实施 + GUI 基准 + D-Peer 甲 + D-Sync 甲)→ `my-commit-flow.sync`(已同步 `55c5786d`)→ 读 qB GUI `.ts` 抽基准词 → shared 层有序批量替换(~470 处, 25 文件)+ 定向 Edit(状态词/菜单动词/对话框标题/Hash 标签/tracker 种子列)→ resources 9 文件 ~290 处 → groups.py 两处 help + docs/configuration.md → 守阵 `test_webui_static_dom_panel.py` 4 处断言 + `e2e/menus.spec.mjs` 8 处 + `e2e/delta-sync.spec.mjs` 2 处 → 改动 JS 全量 `node --check` 绿 → `test.quick` 3112 passed → `dev.fmt` → `test.full` 基线切片 `26-10-11-0101`(数字见 kb.baseline)→ 报告补实施注记 → `kb.index` 重建; `ship.commit` 随本专题入库(等用户显式说「提交」)。
- **2026-10-11 02:23** 用户复查指出二轮遗漏(种子详情面板/用户页)→ `my-commit-flow.sync`(已同步 `1d7c864b`)→ 清点面扩到抽屉全部 classic 页插件(drawer_pages 4)+ 15 变体, 基准仍逐词抽 qB `.ts`(Relevance=文件关联、Flags=标志、Do not download=不下载、Normal=正常、Working=工作/Not working=未工作/Not contacted yet=未联系/Disabled=禁用、Reannounce In=下次重新汇报、Pieces=区块、IP/Address=IP/地址)→ 精确替换脚本(shared 17 文件 ~92 处, 每处断言命中数)+ resources 12 文件 72 处 + e2e `drawer-peers-columns.spec.mjs` 1 处(「正在取」断言→「文件」)→ 守阵错误态文案 3 处同步(tracker 列表→Tracker 列表, 首跑红后修)→ 改动 JS 全量 `node --check` 绿 → `test.quick` 3112 passed → 报告补 §11 二轮章节 + doc-updated → `test.full` 基线切片(数字见 kb.baseline)→ `kb.index` 重建; 工作树含二轮全部改动, `ship.commit` 随本专题入库(等用户显式说「提交」)。**根因记档**: 一轮清点面漏了变体与 drawer_pages —— 「全量排查」的清点面必须覆盖全部渲染出口(变体/页插件/模板), 不只主数据链。
