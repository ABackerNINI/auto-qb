# docs issue 清理轮 — 4 条 docs issue 全部修复置 Done

> 摘要: 一次性认领 4 条 docs issue 修复并收尾入库(用户授权「最后一起提交」)。
> 最后活动: 2026-10-03 06:40

## 已完成 (2026-10-03)

- **26-10-02-0728 AUMID 文档漂移**: `memory-bank/modules/core-domain.md` AUMID 表述改为按现状事实(函数存在但生产零调用点, 标注关联 bug 26-10-02-0727 未决); `src/auto_qb/tray/app.py` `_set_windows_appid` docstring 的 AutoQB.UI.lnk 残留改为注册表键机制描述。
- **26-10-01-2212 schema docstring 退役级别表**: `src/auto_qb/config/schema/__init__.py` docstring 删对已退役 SECTION_LEVELS/TRACKER_FIELD_LEVELS 的提及, 改写为现状机制(R 级重启闸 + 消费模块 apply 自判)。
- **26-09-21-1408 README 用例数与 modules 行数快照**: `README.md` 补回带口径日期的实测用例数(2026-10-03, collect-only 2312 = 2309 passed + 3 skipped); `memory-bank/modules/` 下 5 份(overview/core-runtime/core-domain/core-config/rules-and-deps)行数快照全量重扫并注明口径「wc -l 实测, 快照日期即口径截止日」。
- **26-09-20-1427 skill USER.md 口径冲突**: `.agents/skills/aesthetic-preset-library/SKILL.md` 「写入 USER.md」口径改为与 autoclaw 一致(仅当次会话生效, 不自动写回/不宣称跨会话保存, 用户明确要求除外)。
- 4 条全部置 Done(封面徽标 + meta + 状态日志各追一行), `kb.index` 重建后均落 Done 分区; **26-09-28-1946(插件 spec 逐键文档)按用户拍板保持 Open, 本轮不做**。
- 收尾: 基线切片 [baselines/26-10-03-0637](../testing/baselines/26-10-03-0637-docs-issue-clearance.md)(2314 passed + 3 skipped / 99% @ fe70fccd, 合并远端 fe70fccd 后实测); 无新坑; 本轮为 issue 清理不立新任务档(用户明示)。

## 状态

任务完结, 等待 ship.commit 入库(用户已授权一次性提交; 同步已完成 @ fe70fccd)。
