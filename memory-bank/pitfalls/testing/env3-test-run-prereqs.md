# env3(原生 Linux)跑测试/闸门的两条前置: node PATH 只做了会话级前插 + TZ 敏感存量用例

> 摘要: env3 Ubuntu 24.04 上跑 test.quick/test.full/ship.gate, 不带 `PATH=$HOME/.local/node/bin:$PATH` 则 r4 node 电池族大面积假红(_run_probe 的 shutil.which("node") 落空 -> 「无 node」断言拦下), 不带 `TZ=Asia/Shanghai` 则 TZ 敏感存量用例(issue 26-11-12-2347 已入池)必红 —— 两者都是**环境态**, 与改动面无关, 别当回归排障。
> 触发: env3, 原生 Linux, node 电池, 无 node, r4 batteries, node PATH, TZ, 时区, window_start_on, ship.gate 红, test.quick 红, 闸门预跑红, 环境态红

- **触发**: env3 本机(原生 Linux, 非 WSL/容器)新会话首跑 test.quick/test.full/ship.gate/评审 gate 预跑等 node 依赖面或全量面。
- **判别**: ①红面集中在 `test_webui_static_r4_*` 且失败行是「无 node: 本电池静默跳过(与既有电池同口径)」= node 不在 PATH —— `which node` 落空; node 装在 `~/.local/node/bin`(探针报告 26-11-12-2347 的装机配方只做了**会话级** PATH 前插, 未落 profile, 新会话/子进程不继承)。②唯一红是 `tests/test_hr_ratelimit.py::test_window_start_on_pins_start_endpoint_and_rollover` = TZ 敏感存量用例(26-11-12-2347): 仅美制 DST 切换时区(如 America/Los_Angeles, 切换日 2026-03-08 落在用例钉死窗口)必红, UTC 等固定偏移时区绿, 口径随该 issue 单点 —— `TZ=Asia/Shanghai` 下单跑即绿可自证。
- **处置**: 测试/闸门命令统一带前置 env —— `TZ=Asia/Shanghai PATH="$HOME/.local/node/bin:$PATH" commands run test.quick`(full/gate 同款); 根治归属: node PATH 落 profile 是机器装机收尾(等用户拍板, 不在任务轮顺手改宿主配置), TZ 用例根治走已入池 issue; 排障先分「环境态红」与「改动面红」, 别把这两类当新回归去改代码。
- **复发**: 1 (2026-11-13, active-context-cleanup 收尾闸门轮) —— 非交互 shell 跑 test.one/test.quick 双症齐发: r4 电池 70 条「无 node」假红 + window_start_on TZ 红 1 条, 症状与本档判别逐字吻合, 带前置 env 复跑即全绿。**为什么没命中**: 会话任务面看着是纯文档清理, 开工路由没进 testing 类 pitfalls(路由没到); 教训: **收尾的闸门/测试轮同样在本坑触发面内**, 只按改动文件类型判路由会漏。
**Refs:** memory-bank/tasks/26-11-13-test-port-kill-posix-branch.md, memory-bank/reports/26-11-12-2347-report-linux-env3-probe.html, memory-bank/tasks/26-11-13-memory-bank-active-context-cleanup.md
