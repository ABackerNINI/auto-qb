# 辅种页扩列: 组级聚合 + 明细差异列 + hide 默认隐藏

> 摘要: 分组列默认加 进度(max)/剩余时间(最小有效 eta)/已下载(Σ)/最近活动(max), hide 可选列加 剩余量(min)/做种时长(平均)/可用性(max)/分享率(Σ上传÷单份大小); 明细列默认加 剩余时间, hide 加 限速/Tracker/Hash/Hash v2/做种(总)/用户(总) 等; 聚合口径总原则 = 组内同一份文件, 字节量取单份视角、网络流量才可求和。列模型新增 `hide` 标志(loadColState 尾部播种, 空存储路径必须覆盖 —— 冒烟抓过提前 return 绕过的真 bug)。守阵新增 _scan_column_cells_paired(列 key ↔ 模板分支配对, 明细列 groups/shows 两处成对)。
> 最后活动: 2026-09-28 03:30

## 正在进行

(无 —— 本轮已收尾, test.full 1818 passed, 双皮肤冒烟全绿; 档案 tasks/26-09-28-webui-group-columns.md)

## 待办 / 遗留

- kb.check 报两条 2026-09-27 旧基线切片文件名不合 `YY-MM-DD-HHMM-<slug>`(console-skin / ui-switch-dropdown) —— 既有问题待拍板是否入池。
