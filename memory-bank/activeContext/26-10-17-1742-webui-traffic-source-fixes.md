# webui-traffic-source-fixes

> 摘要: Phase 1 缺陷修复 S1–S5 已完成(总开关 + 取数闸门/off 快照 + 工具 shutdown + 「关闭工具」 + 去黑框)；S6–S8 待续
> 最后活动: 2026-10-18 06:26

**R0(2026-10-17 17:42):** grilling 六轮收敛并落盘 Phase 1 修复计划；新增顶层 traffic_source.enabled 总开关(修订 0339-D1)；0339 记 R3

**Refs:** memory-bank/tasks/26-10-17-webui-traffic-source-fixes.md

**R1(2026-10-17 21:17):** S1-S3 实施完成: traffic_source.enabled 总开关四层契约 + 取数闸门/off 快照/expr 文案/前端灰显 + gtm POST /shutdown 与 auto-qb 代理; 全域回归全绿(数字见基线切片 26-10-17-2114); S4-S8 按用户指令不在本轮范围

**R2(2026-10-18 06:10):** S4-S5 实施完成: 「关闭工具」按钮(三条件可见)+ 确认框(清单来自 schema affects)+ 先存 enabled=false 再停工具 + 失败回滚/不谎报, 并补登 triggers 注册表; 去黑框(launch_tool 换 CREATE_NO_WINDOW + launch.cmd 三级回退优先 pythonw); 新增两处守阵, 回写 docs/configuration.md; 全域回归见 kb.baseline 最新切片(其中 test_memory_bank 两例跨零点时间炸弹为已知红, 入池 issues/26-10-18-0608)

**R3(2026-10-18 06:26):** 计划外(用户指派): 修掉 test_memory_bank 两例跨零点时间炸弹 —— 三处日期断言改为与 timekit.now() 同源取时(_kb_clock helper), 只动测试零实现改动; 相关 issue 置 Done; 全域回归转全绿(见 kb.baseline 最新切片)
