# 5191 passed + 10 skipped —— webui 迁移可见性收口评审与修复后全量

> 摘要: webui 迁移可见性收口评审与修复后全量
> 基线时间: 2026-11-04 21:06
**Refs:**

## 验收数字

```
TOTAL                                                24385    228   8352    171    99%
5191 passed, 10 skipped in 180.58s (0:03:00)
```

- 环境: Windows 本地, `commands run test.full`(含覆盖率闸 99.0%)。
- node 探针用例在本机实际执行(node 可用); 非 node 环境按既有惯例静默跳过。

## 本改动面

- src/auto_qb/core/modules/relocate_lifecycle.py: `_reconcile_pending_tags` 补「已加未摘」终态 job 的退避重试, docstring 与实现对齐
- src/auto_qb/infra/alias_fs.py: 新增 `is_remote_path` / `_drive_type`(UNC、设备前缀 UNC、盘符映射网络盘 DRIVE_REMOTE)
- src/auto_qb/webui/server/routes/relocate_chain.py: 起点派生改用 `is_remote_path`(远端仍零 syscall)
- src/auto_qb/webui/static/shared/drawer_rows.js: 迁移源/目标路径行 act `open`→`copy`(动作与展示路径一致)
- src/auto_qb/webui/views_relocate.py: pending/total 计数口径注释修正
- tests/test_alias_fs.py: +3 例(远端判定/映射盘/取盘类型失败降级)
- tests/test_relocate_tag_mirror.py: +1 例(终态摘标签失败重试与零写放大)
- tests/test_webui_relocate_visibility.py: +2 例(node 行为探针、详情端点投影) 并收紧焦点环断言
