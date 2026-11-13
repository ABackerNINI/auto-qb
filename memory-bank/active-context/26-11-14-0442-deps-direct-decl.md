# deps-direct-decl

> 摘要: 修复 issue 26-11-12-0739: requests==2.34.2 钉现值收编直接依赖(零版本变更, 纯声明显式化, uv.lock 根包两处登记+revision 3→5 机械面); §03 顺带排查全仓裸 import 收编同款两组 anyio==4.15.1/starlette==1.10.0 进 dev 组(hatchling 已有桩规避无患); issue 翻 Done 补修复后补充; impact-map §1.2 事实回写; 评审 2 轮(轮1 1 minor 节序/id 先例混用已修, 轮2 零 actionable), 检 1/1 修 1 入池 0; test.full 6086+19 覆盖 99% 基线切片 26-11-14-0442; 零新坑
> 最后活动: 2026-11-14 04:54

**R0(2026-11-14 04:42):** 修复 issue 26-11-12-0739: requests==2.34.2 钉现值收编直接依赖(零版本变更, 纯声明显式化, uv.lock 根包两处登记+revision 3→5 机械面); §03 顺带排查全仓裸 import 收编同款两组 anyio==4.15.1/starlette==1.10.0 进 dev 组(hatchling 已有桩规避无患); issue 翻 Done 补修复后补充; impact-map §1.2 事实回写; 评审 2 轮(轮1 1 minor 节序/id 先例混用已修, 轮2 零 actionable), 检 1/1 修 1 入池 0; test.full 6086+19 覆盖 99% 基线切片 26-11-14-0442; 零新坑
