# test-free-port-hold-run-flake

> 摘要: 认领并修复 issue 26-11-10-0456: test_hold_run_discards_run_whose_offset_is_refused 由真实 socket 代理改纯合成 socket(零真实 bind), 根因=断言把并行端口噪声写成判据(并发多一轮重试即红, 首次尝试真实失败反而假绿); 确定性红绿双验 + 机制红验(改坏 hold_run 必红) + test.quick/test.full 全绿(见 kb.baseline, 基线切片 26-11-10-0617); issue 翻 Done 补复验/修复后补充, 坑档 consecutive-port-run.md 复发 +1 并补守阵用例本体口径(复发归因: 入池时该坑档口径只覆盖业务用例断言形态, 未覆盖守阵用例自身用真实端口做底板, 属读了没照做); 零生产代码改动
> 最后活动: 2026-11-10 07:43

**R0(2026-11-10 06:18):** 认领并修复 issue 26-11-10-0456: test_hold_run_discards_run_whose_offset_is_refused 由真实 socket 代理改纯合成 socket(零真实 bind), 根因=断言把并行端口噪声写成判据(并发多一轮重试即红, 首次尝试真实失败反而假绿); 确定性红绿双验 + 机制红验(改坏 hold_run 必红) + test.quick/test.full 全绿(见 kb.baseline, 基线切片 26-11-10-0617); issue 翻 Done 补复验/修复后补充, 坑档 consecutive-port-run.md 复发 +1 并补守阵用例本体口径(复发归因: 入池时该坑档口径只覆盖业务用例断言形态, 未覆盖守阵用例自身用真实端口做底板, 属读了没照做); 零生产代码改动

**R1(2026-11-10 06:21):** 收口: 分批评审按 code-review skill ⑧ 降级为主会话逐条自查 —— 三次只读子代理派遣(general-purpose x2 / Explore x1)均挂起未交回(疑似远端查询与环境交互), 降级从严自查产出零发现, review.check 0 条/通过 0/弃 0, 末轮 review.pack 基哈希 072f601b518d 未漂移; 首轮 pack 前主会话自发修掉一条恒真断言(bases[2] != bases[1] 由桩按尝试序号分配恒真), 换成「返回段不得来自被丢弃的第一次尝试」的行为断言, 按 ⑤ 自发顺手修不进 修/入池 计数; 收口接缝终审核对代码 docstring 测试计划/用例实现/issue §07/坑档/基线切片/本切片六面口径一致, 零发现; test.quick 全量并发两轮全绿 + test.full 全绿(见 kb.baseline, 基线切片 26-11-10-0617), kb.check 与 HTML 标签平衡机检全绿, kb.index 已重跑; 真机不适用(纯桩可验); doc.caps 报 3 项 cap 债务已转告用户另开会话清理; 改动随本专题入库

**R2(2026-11-10 07:38):** 提交轮: 用户显式「提交」→ 开工同步又快进 15 笔(c1200d7b→436303b0, 远端 config v7 与 RM04 真机闭环); 齐平后 test.quick/test.full 撞两条稳定红, 均指向远端刚推的 tests-real 文件(schema_version 6 未跟 v7 / docstring 两个 circled 符号超 ASCII 冻结基线), 与 issue 0456 无关且必拦提交闸门; 经 AskUserQuestion 用户授权「清障并提交」, 按 scope-guard 例外 1(阻塞)+3(当场扩范围)只改两文件共 5 行(3 处版本号 + 2 处符号), dev.fmt 对该文件带出的三处重排当场还原, 零夹带; 两条守卫单跑全绿, test.full 在最终组合树全绿(见 kb.baseline, 最终基线切片 26-11-10-0738); 评审包按最终 diff 重取并降级从严自查, review.check 零发现; 按用户显式指令走 commit+push, 改动随本专题入库

**R3(2026-11-10 07:43):** 更正 R2 的清障措辞: 提交闸门 .my-commit-flow.toml 第一条 dev.fmt 会对本次改过的 py 统一跑 yapf, 手工还原的格式重排被闸门自动重新格式化 —— 最终提交含该文件三处纯格式重排(无语义变化), 闸门实算可评内容 116 行, 末轮 review.pack 基哈希 a2c94b42b247; 基线切片 0738 与提交消息已同步回写; 按用户显式「提交」指令重跑 ship.commit
