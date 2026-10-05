# qb-traffic-v4-delta — qB 流量 v4 delta 格式实施(收尾滚动)

> 摘要: v4 格式换代三批实施完成, 已迁出 progress/implemented-core.md(🆕 首条)。本切片只留未决项。
> 最后活动: 2026-10-06 01:55

**Refs:** memory-bank/tasks/26-10-05-backend-qb-traffic-v4-delta.md

## 未决项

- 交付合并与推送待用户指令: B1 已提交(6a98c504)、B2 三棒待合并前 squash、批 3 回写改动留工作区 —— 「提交」触发词走 ship.commit。
- 旧目录处置(qb-traffic-v3/ 删留): 决定权在用户(R2 现状 = 原样留存不读不迁移)。
- 真实落盘产物观察: dry-run 已验证零 ERROR 但零落盘(v4 写路径静默跳过), 首日 qb-traffic-v4/ 目录产物需用户非 dry-run 真跑确认。
- 配比失配监测: 30S/10M 缺省恰在 20 行界上(30s 档 B 行约 5%), 若后续真机实测发现普遍失配, 再议 validate_config 非阻断提示(另立计划, 见计划 §05 风险表)。
