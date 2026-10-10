# WEBUI 文案对齐 qB(报告已实施)

> 摘要: 报告 `reports/26-10-10-2237-report-webui-wording-unify.html` 已按用户拍板实施完毕: **完全对齐 qB GUI 译文** + D-Peer 甲(对端词统一「上传中/下载中」)+ D-Sync 甲(resources/ 同步)。shared 层 ~470 处 + resources 9 文件 + schema help + docs + 守阵/e2e 同步全部落地; 基线 `test.full` 实测数字见 `kb.baseline`(`26-10-11-0101` 切片)。工作树含本轮全部改动, `ship.commit` 随本专题入库(等用户显式说「提交」)。
> 最后活动: 2026-10-11 01:01

**Refs:** memory-bank/tasks/26-10-10-webui-wording-unify.md,memory-bank/testing/baselines/26-10-11-0101-webui-wording-gui-unify.md

## 当前状态(无未竟事项)

- 实施明细与「刻意不动」清单(确认框「重新校验」、state.js 自身暂停态、跳检对话框词、复制族/超级做种等)见任务档案与本轮基线切片。
- GUI 与 WebUI 译词差异最终以 GUI 为准落地的关键项: Seeds 列=做种数(tracker 页签=种子)、Completed=已完成、Force Recheck=强制重新检查、Set location=设定位置、Start/Stop=启动/停止。

## 后续候选(未开工, 均需用户另起)

- 术语常量单点化(报告 §09 实施期决策; 本轮为机械替换, 未收常量)。
- `config_hub.js` schema 字段标签(上传限速/下载限速)是否随 GUI 改「上传限制/下载限制」—— 配置域词汇, 报告未列, 本轮未动。
- 三皮肤 CSS 注释里的方向词注释(纯注释, 本轮未动)。
