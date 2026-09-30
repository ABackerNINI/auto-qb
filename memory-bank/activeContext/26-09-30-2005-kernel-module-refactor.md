# QbManager 内核化重构(P0-P1 完成, P2-P6 待续)

> 摘要: plan 26-09-30-1819 滚动实施 —— P0 内核地基(契约+StateService+属性委托)之后, P1 基建模块化完成: core/modules 包 LoggingModule/NotifyModule 契约样板(sections 认领 + apply 整段短路), 装配清单挂入两模块, run() 启动接线改 host.start_all, 热重载 L1 手工重挂两段改 host.apply 无条件广播(hot-reload W1+W2 子集, 影子并行: L1 分支暂留 qb 重连+web 重启), 托盘 4 处 _notify_handler 直写改 ctx.notify 公开方法。test.full 1850+3 / 91%。
> 最后活动: 2026-09-30 20:05

## 已完成

- P1(2026-09-30): 新增 core/modules 包(140 行)+ tests/test_core_modules.py 守阵 7 例(P1 指定守阵「改 notify 段才重挂、无关保存零动作」在内); qbmanager `_setup_logging`/`_notify_handler` 删除, 单点迁模块; tray/app.py 私有面清零。基线切片 testing/baselines/26-09-30-2000-p1-foundation-modules.md。
- P0(2026-09-30, 详见上一切片 26-09-30-1912 与任务档案进度日志)。
- 档案单点: tasks/26-09-30-backend-kernel-module-refactor.md(P0/P1 Done, 执行偏差与 P2 注记都在进度日志)。

## 正在进行

- 无(等下一轮指令; 未提交 —— 等用户说「提交」)。

## 下一步(按计划 P2-P6, 未开工)

- P2 门面转正: WebUIRuntime/HrRuntime 挂 Module 协议(签名对齐+sections 认领), run() 的 web 启动块/hr.start/finally 停止序列改 host.start_all/stop_all, _apply_web_config 并入 webui.apply, 主循环 `self.web.*` 五语义调用改 loop hooks; 注记: 装配序与现启动次序在 notify/web 之间换位(notify 不依赖 web, 已评估无风险)。
- P3-P5 小/中坚/最大一刀(tracker+speed_curve+maintenance → grouping+ops → rules+刷新管线收口)。
- P6 回写 + 真机四场景走查 + 段认领守阵; 别名层处置另立计划(D4)。
