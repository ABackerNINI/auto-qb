# linux-env3-probe

> 摘要: 第三开发环境(Ubuntu 24.04 原生 Linux)接入探测收口: 依赖链断点排障(argv[0] 污染/uv/py2)与装机(uv 0.13.7/CPython 3.13.18 南大镜像/node v22.20.0/python-is-python3), develop 切换, 测试面实测(quick 6055P/0F/31.34s, full 110.4s 覆盖 99% 过非 Windows 闸 99.0), grilling 拍板后三件入库(探测报告/TZ 敏感用例入池 26-11-12-2347/argv0 坑档), 两轮评审 7 发现全修, 计划 26-11-12-0152 拍板不动
> 最后活动: 2026-11-13 02:38

**R0(2026-11-13 01:05):** 第三开发环境(Ubuntu 24.04 原生 Linux)接入探测收口: 依赖链断点排障(argv[0] 污染/uv/py2)与装机(uv 0.13.7/CPython 3.13.18 南大镜像/node v22.20.0/python-is-python3), develop 切换, 测试面实测(quick 6055P/0F/31.34s, full 110.4s 覆盖 99% 过非 Windows 闸 99.0), grilling 拍板后三件入库(探测报告/TZ 敏感用例入池 26-11-12-2347/argv0 坑档), 两轮评审 7 发现全修, 计划 26-11-12-0152 拍板不动

**R1(2026-11-13 01:14):** 批后回写: run.md:18 覆盖率闸旧口径(99.0/98.5, 落后两轮升闸)修为 99.5/99.0 并钉「阈值权威=conftest 常量」, 用户指令修复并提交; 两轮评审循环(报告批 7 发现全修 + run.md 批零发现)闭环, 三件随 8e07d5f3 入库

**R2(2026-11-13 01:28):** clone2/clone3 备产完成(按探测报告 26-11-12-2347): 两 clone 各装 repo 级 commands wrapper(install_wrapper.py)+my-commit-flow.sync 快进 5dfb3662→73f65b0f+env.sync(uv sync 裸跑, 锁 canonical 未动), 双 clone test.quick(TZ=Asia/Shanghai+node PATH)各全绿(实测数字留痕探测报告 §2.4 同口径, 正文不手抄); node PATH 持久化补齐(~/.local/node/bin 入 ~/.zshrc, 此前仅会话级); docker 按用户拍板本轮不配

**R3(2026-11-13 02:23):** e2e 前置三 clone 原生就位(用户拍板不走 docker): npm ci(直连 registry.npmjs.org 200, npm ci 不写 lock 无烤锁面)+chromium 二进制(cdn.playwright.dev 直达, chromium-1243/headless-shell/ffmpeg 入共享缓存 ~/.cache/ms-playwright, 三 clone playwright 1.63.0 锁同 MD5); clone1 fast e2e 全量实跑 2 红同属 traffic-source-switch.spec.mjs 收尾竞态(全量例数/红绿/耗时随证据入池 issue 26-11-13-0234-test-e2e-stubdisk-teardown-race, 正文不手抄; route.fetch: Test ended, 断言本体过, CI retries=1 探测器口径重试即绿), 非环境缺件; 计划外发现: scripts/port_kill.py listening_pids/process_info 纯 PowerShell 无 os.name 分支, dev.e2e-check/dev.port-kill 原生 Linux 必炸 FileNotFoundError(CI ubuntu 不跑 selfcheck 故从未暴露); 本机 e2e 日常门禁适配: 直跑 npm run test:e2e:fast 跳过 selfcheck

**R4(2026-11-13 02:38):** 用户显式拍板两件计划外发现入池: 26-11-13-0234-bug-port-kill-linux-no-posix-branch(bug/L2: listening_pids/process_info 纯 PowerShell 无 os.name 分支, dev.e2e-check/dev.e2e/dev.port-kill 原生 Linux 必炸, CI ubuntu 不跑 selfcheck 故未暴露; 建议 /proc 直读 A 案+守阵双平台分派先例)与 26-11-13-0234-test-e2e-stubdisk-teardown-race(test/L2: stubDisk route 回调收尾竞态 route.fetch Test ended, 断言本体过, CI 探测器口径重试即绿; 建议 unrouteAll ignoreErrors 兜底 A 案), 均 L2 六段填齐 --refs 双向补链探测报告; 顺手清 kb.check 新增违规: 切片 R2/R3 裸 passed 数字改引述措辞(判据族 B)
