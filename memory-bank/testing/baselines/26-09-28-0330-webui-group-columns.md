# 1818 passed / 3 skipped —— 辅种页扩列(组级聚合 + 明细差异列 + hide 默认隐藏)

> 摘要: 辅种页扩列(拍板见 tasks/26-09-28-webui-group-columns.md): 分组列 +4 默认(进度 max/剩余时间 最小有效 eta/已下载 Σ/最近活动 max) +4 hide(剩余量 min/做种时长 平均/可用性 max/分享率 Σ上传÷单份大小); 明细列 +1 默认(剩余时间) +12 hide(限速上下行/Tracker/Hash/Hash v2/做种(总)/用户(总)/已下载/完成于/最近活动/活跃时间/可用性/见到完整副本)。
> 基线时间: 2026-09-28 03:30
> 档案: 26-09-28-webui-group-columns

- **本线新增用例 2 条 + 守阵 1 条**(test_web.py): `test_build_group_view_group_aggregates`(双组:
  有效聚合逐项断言 + 全无效回 0/None)/`test_member_view_extended_fields`(分钟量化 + 哨兵带过 +
  12 字段透传); `_scan_column_cells_paired`(列模型每列 key 必须有模板值单元格分支 —— group→groups.html,
  detail→groups.html+shows.html 两处成对, torrent/show 同理; loadColState 必须消费 hide 标志)挂
  `_scan_frontend_assets` 第 14 项。用例总数较上条基线(1816+3)的 +2 即本条。
- 实机验证(dev.harness 桩 `--port 8921` + Playwright, 非本基线数字来源): atlas/prism 新列头渲染、
  hide 列默认隐藏、列选择器勾选 Tracker 开启、意图落盘 hidden 集正确、零页面 JS 错误; 冒烟抓到
  loadColState 空存储提前 return 绕过 hide 播种的真 bug(已修 + 坑档回写 columns-persist.md)。
- 8099/8123 被一周旧孤儿进程占住(LISTENING, 命令行不可读)—— 未杀进程, 换口 `--port` 绕开。

TOTAL **91%**(12512 语句 / 914 未覆盖 / 4204 分支 / 387 partial), views.py 98%, 耗时 23.01s(单次采样)。
