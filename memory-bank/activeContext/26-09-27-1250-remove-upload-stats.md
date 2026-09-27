# 暂时移除不成熟的限速统计设计 (upload_size 四条件 + begin_round 底座) — 已完成待提交

> 摘要: 计划 26-09-27-1232 全量执行完毕 —— 代码 7 触点(conditions.py 删 4 类 / env.py 删 3 表达式名 /
> rule_engine mixin 删 begin_round+upload_delta / qbmanager 删调用点 / schema 删 4 Plugin 元数据 /
> full_checking docstring 口径引用改写 / versioning state v1→v2 迁移清 upload_snapshots,
> 另修 _migrate_state_dict 空 dict 短路防首启误盖章); 测试删 3 用例改 8 处版本章断言 + 新增生产迁移测试;
> 文档回写 9 处(docs/configuration.md 条件表 16→12 种 / deployment.md / memory-bank 5 份 / TODO.md)。
> 重设计待办已入 feature issue 26-09-27-1248(候选: global_* 全局口径 / 补下载量单种口径)。
> 提交前 ff 合并远端 56c04e0(hr carpt 适配器 + webui 模板聚合化), 合并树上重测:
> test.full 1691 passed + 1 skipped(基线切片 26-09-27-1250 已更新为合并后实测)。等待用户说「提交」(已发出, 提交中)。
> 最后活动: 2026-09-27 13:00
> 档案: memory-bank/plans/26-09-27-1232-plan-remove-upload-stats.html
