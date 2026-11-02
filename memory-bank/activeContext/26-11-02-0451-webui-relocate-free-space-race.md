# webui-relocate-free-space-race

> 摘要: 认领修复 issue 26-11-02-0413: test_relocate_volume_free_ancestor_fallback 桩 disk_usage(存在回固定free/不存在抛FileNotFoundError)消两次采样断言竞态; 定向2过+整文件31过, 全量见 kb.baseline; issue 置 Done
> 最后活动: 2026-11-02 04:51
**Refs:**

**R0(2026-11-02 04:51):** 认领修复 issue 26-11-02-0413: test_relocate_volume_free_ancestor_fallback 桩 disk_usage(存在回固定free/不存在抛FileNotFoundError)消两次采样断言竞态; 定向2过+整文件31过; issue 置 Done

**R1(2026-11-02 06:20):** 全量直跑 4812过/11红(1519s, 机载~15x): 8 junction族(本shell junction Target被改写落沙箱, 直接探针实证环境性)+2端口(他agent harness占口)+1耗时预算; 与本改动零因果(零src改动); 全量未绿不产新基线; 未提交(用户: 不推远端, ship.commit无免推路径)
