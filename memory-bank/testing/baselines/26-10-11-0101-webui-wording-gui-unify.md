# 3112 —— WEBUI 文案全量对齐 qB GUI(报告实施)基线

> 摘要: 用户拍板实施 `26-10-10-2237-report-webui-wording-unify.html`, 口径 = **完全对齐 qB GUI 译文**(D-Base=乙) + **D-Peer 甲**(对端状态词统一「上传中/下载中」我方视角) + **D-Sync 甲**(resources/ 设计稿同步); 由此 D-State/D-C/D-Dir 均按 GUI 严格对齐执行。基准取自本机 qBittorrent `src/lang/qbittorrent_zh_CN.ts`(逐 source 抽取, 不靠记忆)。实施面: ①列头/字段(做种→做种数、做种(总)→做种数(总)、剩余量→剩余、见到完整副本→最后完整可见、浪费→已丢弃、做种时长→做种时间、Hash v1/v2/Hash→信息哈希值 v1/v2、限速族→上传限制/下载限制、上传上限/下载上限→上传限制(KiB/s)/下载限制(KiB/s)、本次会话下载/上传→会话已下载/上传、连接数→连接、活跃时间→活动时间、tracker 页签做种→种子); ②状态词贴 GUI 去「中/已」(下载中→下载、做种中→做种、校验中→校验、已暂停→暂停、已暂停(已完成)→已完成、等待下载→等待、排队(做种)/(下载)→排队、出错→错误、文件缺失→丢失文件、获取元数据→下载元数据、恢复校验→校验恢复数据; REANNOUNCE 阻断原因串同步); ③动作菜单(开始/暂停→启动/停止、强制开始→强制启动、重新校验(菜单项)→强制重新检查、强制汇报→强制重新汇报、移动…→设定位置…、限速…→速度限制…、批量限速→批量速度限制、队列置顶/上移/下移/置底→队列顶部/向上移动队列/向下移动队列/队列底部、顺序下载→按顺序下载、首末块优先→先下载首尾文件块、跳检…(菜单项)→跳过哈希校验…; **确认框「重新校验」保留**(qB GUI 的 recheck 确认框本身就用「重新校验」, 守阵 `confirmDialog("重新校验")` 断言不破)); ④方向词 上行/下行→上传/下载(shared 全层 + 状态栏限速短句「上 X/下 X」→「上传 X/下载 X」); ⑤对端状态词 07/08/09 六种叫法统一「上传中/下载中」; ⑥D-Sync 甲: `resources/detail-panel-templates/` 9 文件 ~290 处同步 + `config/schema/groups.py` 两处 help + `docs/configuration.md:416`; ⑦守阵同步: `tests/test_webui_static_dom_panel.py` 4 处断言 + `e2e/menus.spec.mjs` 8 处选择器 + `e2e/delta-sync.spec.mjs` 2 处。刻意不动: `state.js:384`「已暂停」(是 auto-qb 自身暂停态, 非种子状态)、确认框 helper 文案、复制族/超级做种/自动种子管理/分享率限制等自有或已对齐词、三皮肤 CSS 注释。
> 基线时间: 2026-10-11 01:01

**Refs:** memory-bank/tasks/26-10-10-webui-wording-unify.md

## test.full 实测

- 分支: `develop`(会话开工 `my-commit-flow.sync` 已同步 `55c5786d`; 工作树含本轮全部文案/守阵改动时实测)
- 命令: `commands run test.full`
- **实测 (Windows)**: **3112 passed + 4 skipped, 0 failed, 覆盖率 TOTAL 99%**
  (16586 语句 / 156 未覆盖 / 5724 分支 / 143 partial; 门槛 98% 达标; 本轮 25.6s)
- 前置机检: 改动 JS 全量 `node --check` 通过; `dev.fmt` 过 groups.py 与守阵测试文件。
- 改动面(摘要): `src/auto_qb/webui/static/shared/`(根 JS + tpl/*.html + drawer_tpl/*.js + drawer_pages/*.js 约 25 文件, ~470 处)、`resources/detail-panel-templates/` 9 文件、`src/auto_qb/config/schema/groups.py`、`docs/configuration.md`、`tests/test_webui_static_dom_panel.py`、`e2e/menus.spec.mjs`、`e2e/delta-sync.spec.mjs`。
- 未纳入本轮(刻意不越界): 术语常量单点化(报告 §09 的实施期决策)、三皮肤 CSS 注释、复制族文案、`config_hub.js` 的 schema 字段标签(上传限速/下载限速, 属配置域词汇)。
