# env3(原生 Linux)跑测试/闸门的前置: node PATH 只做了会话级前插(TZ 敏感存量用例已根治)

> 摘要: env3 Ubuntu 24.04 上跑 test.quick/test.full/ship.gate, 不带 `PATH=$HOME/.local/node/bin:$PATH` 则 r4 node 电池族大面积假红(_run_probe 的 shutil.which("node") 落空 -> 「无 node」断言拦下), 是**环境态**红与改动面无关, 别当回归排障。存量第二条前置「TZ=Asia/Shanghai 前置」已随 issue 26-11-12-2347 根治(2026-11-13: 用例模块内自钉 TZ, POSIX 侧任何时区宿主恒绿; Windows 无 tzset 维持宿主时区, 限无 DST 时区恒绿 —— 现有 Windows=Asia/Shanghai / CI=UTC), 前缀里的 TZ= 可撤。
> 触发: env3, 原生 Linux, node 电池, 无 node, r4 batteries, node PATH, TZ, 时区, window_start_on, ship.gate 红, test.quick 红, 闸门预跑红, 环境态红

- **触发**: env3 本机(原生 Linux, 非 WSL/容器)新会话首跑 test.quick/test.full/ship.gate/评审 gate 预跑等 node 依赖面或全量面。
- **判别**: 红面集中在 `test_webui_static_r4_*` 且失败行是「无 node: 本电池静默跳过(与既有电池同口径)」= node 不在 PATH —— `which node` 落空; node 装在 `~/.local/node/bin`(探针报告 26-11-12-2347 的装机配方只做了**会话级** PATH 前插, 未落 profile, 新会话/子进程不继承)。
- **处置**: 测试/闸门命令统一带前置 env —— `PATH="$HOME/.local/node/bin:$PATH" commands run test.quick`(full/gate 同款); 根治归属: node PATH 落 profile 是机器装机收尾(等用户拍板, 不在任务轮顺手改宿主配置); 排障先分「环境态红」与「改动面红」, 别把这两类当新回归去改代码。
- **复发**: 4
  - (2026-11-13, active-context-cleanup 收尾闸门轮) —— 非交互 shell 跑 test.one/test.quick 双症齐发: r4 电池 70 条「无 node」假红 + window_start_on TZ 红 1 条, 症状与本档判别逐字吻合, 带前置 env 复跑即全绿。**为什么没命中**: 会话任务面看着是纯文档清理, 开工路由没进 testing 类 pitfalls(路由没到); 教训: **收尾的闸门/测试轮同样在本坑触发面内**, 只按改动文件类型判路由会漏。(时点注: 本条复发发生在 TZ 根治入库之前, 其后 TZ 症状已随下条根治消失, node PATH 症状仍在)
  - (2026-11-13, webui-uis-enum-drift 修复收尾闸门轮) —— ship.gate 闸门预跑裸跑 test.quick, r4 电池族 69 条「无 node」假红(TZ 症状已根治不再齐发, 纯 node PATH 单症); 判别行与本档逐字吻合, 带 `PATH="$HOME/.local/node/bin:$PATH"` 前置复跑即全绿。**为什么没命中**: 本会话开工路由只进了 issue 指涉的测试文件面, 没路由进 testing 类 pitfalls; 教训: env3 上**任何**闸门/测试命令第一跑就带 node PATH 前缀, 等红了再查坑档白费一轮闸门时长。
  - (2026-11-13, webui-uis-enum-drift R1(0744 修复)收尾闸门轮) —— 同会话第二笔修复的 ship.gate 预跑又裸跑, r4 电池族 69 条「无 node」假红同症; 带前置复跑全绿。**为什么没命中**: 前一笔(0443)踩坑教训写在**那份会话切片与坑档本条**里, 但 shell 每次调用都是非持久新环境, 「上一笔带过前缀」不构成肌肉记忆 —— 本会话开工确实读过任务档案(内有复发记录), 读了没照做; 教训升级: 该前缀不是「踩过一次就记住」的坑, 是**每条测试/闸门命令的固定前缀**, 应写进个人命令习惯而非依赖会话记忆。
  - (2026-11-13, 同批提交轮 ship.commit 首跑) —— 「提交」指令后 ship.commit 内部闸门裸跑 test.quick, r4 电池族 70 条「无 node」假红(比闸门预跑多 1 条=同批措辞守卫修后计数面); 带前置复跑闸门走绿到下一道真闸门(措辞守卫, 另案)。**为什么没命中**: ship.commit 被当「非测试命令」对待, 漏了它**内部还挂着 test.quick 闸门** —— 前缀覆盖面必须是「一切会触发测试的命令」, 提交命令也在内。
- **已根治(2026-11-13)**: 原第二条前置「`TZ=Asia/Shanghai` 前置, 否则 `tests/test_hr_ratelimit.py::test_window_start_on_pins_start_endpoint_and_rollover` 必红」—— issue 26-11-12-2347 修复后该文件模块内 autouse 夹具自钉 `TZ=Asia/Shanghai`(POSIX 侧 `time.tzset()`, Windows 无该原语维持宿主时区)+ 守阵用例, 在 DST 时区宿主实测 18 passed, 前缀中的 `TZ=` 不再需要; 若该用例再见红, 是夹具/守阵被拆的新问题, 不是本条环境态。
**Refs:** memory-bank/tasks/26-11-13-test-port-kill-posix-branch.md, memory-bank/reports/26-11-12-2347-report-linux-env3-probe.html, memory-bank/tasks/26-11-13-memory-bank-active-context-cleanup.md
