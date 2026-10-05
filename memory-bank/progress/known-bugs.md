# 已知 BUG 与代码内待办

> 摘要: 来自 `想法.md` 的已知缺陷, 以及代码里仍留着的 TODO 清单。
> 触发: 已知 BUG, TODO, 待办, 缺陷, 未修

## 已知 BUG (来自 想法.md)

- 复杂限速规则 (tracker+时段组合等)
- web 服务器三条安全发现 S1-01 / S1-02 待在 `web/auth.py` / `web/events.py` 局部落刀(S1-05 脱敏上游已修 `44c1a0f`; 来源 2026-09-22 web.py→web/ 包拆分审查, 原 activeContext 切片蒸馏)
- **2026-10-06 全项目全面 Code Review 落池**: 十批只读评审(计划 26-10-05-0951, 报告 26-10-05-1036)产出 57 条发现, 分级 P0×0 / P1×3 / P2×8 / P3×46; **28 条新 issue 入池 + 3 条并池备注**(权威清单与文件名单点 = issues/_index.md, 逐条详情 = 各 issue 与报告 §3.2.1, 本文件不重抄 —— 工位纪律: 缺陷现状以 issues 池为准)
- 性能: 主循环拆分平滑占用、全面优化 (想法.md 标注) —— **2026-09-14 已修其中一处严重回归**: 非托管模式下主循环完全不节流(空转约 2800 tick/s, 详见 08 陷阱); 其余优化(如 `update_state_snapshot` 增量化)经评估风险大于收益, 暂不做

### 代码内待办 (TODO 清单, 2026-09-09 核对; 位置用函数/方法名锚定, 行号易漂移)
| 位置 | 内容 |
|------|------|
| rules/actions/checking.py `CheckAction.execute` 闸门 0 上方 | 未完成且暂停的种子 recheck 后仍未完成, 下一轮会再次校验 (3 次失败冷却兜底, TODO 未销) |
| rules/actions/checking.py `_find_reference` 上方 | 优化为 `has_reference() -> bool` 提前返回 |
| rules/actions/checking.py 分段执行处 | 重新设计自定义 (custom) 校验流程 |
| config/loaders.py `load_global_hr` / `load_tracker_hr` | 函数上方 `# TODO: optimize` |
