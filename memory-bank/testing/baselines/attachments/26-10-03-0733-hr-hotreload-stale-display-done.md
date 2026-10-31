# 基线 · 2325 passed + 3 skipped / 99% —— HR 热重载存量绑定 + WebUI 判定置脏修复轮(阶段4 收尾)

> 摘要: 计划 26-10-03-0436 阶段4 收尾: P1 `TrackerModule.apply` 重绑存量绑定(`2a5d07a2`, test_tracker +3) /
> P2 `WebUIRuntime` 补 `hr.revision` 新鲜度置脏(`e4df1fc0`, test_web +2)均红验过; P3 桩走查四时刻链路 PASS
> (判定桥手工接线、取数为直推 publisher 模拟, 真机复核待用户); P4 收尾回写(坑档 hot-reload-stale-bindings-derived-views
> + 常青文档回写 + 立档)。全量回归一次通过(首轮唯一红为收尾新档未进认领链声明, 修正 refs 后复跑全绿)。
> 基线时间: 2026-10-03 07:33, develop @ c91be940(test.full 实测, 工作区含 P4 未提交回写件 —— 纯文档, 不影响数字)。
> Linux 侧: 待补(仅 Windows 侧重测, 见 baseline.md 常驻警告)。

TOTAL **2325 passed + 3 skipped / 99%**(13,433 语句 / 88 未覆盖 / 4,542 分支 / 89 partial,
test.full 30.26s, rc=0)。
相对上一切片(26-10-03-0440: 2309 passed + 3 skipped / 99%, 13,354 语句 / 4,502 分支, @ 8cb2da59)
**passed +16** —— 8cb2da59 → c91be940 共 12 提交的合计(本计划 P1+P2 的 5 用例 + 同区间远端推进:
双向认领链机检下沉 / 站点级三态基座 v3→v4 / 冒烟走查 W5 / 多选导出等的用例), 未逐项拆分;
语句 +79 / 分支 +40 同因。
