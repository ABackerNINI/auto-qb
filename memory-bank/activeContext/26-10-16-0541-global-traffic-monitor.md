---
summary: 全局流量监视小工具(TM 替代)实施 — 计划 26-10-16-0541(Open); S0–S9 落地, S10 由 26-10-17-0339 S15–S19 承接; 2026-10-18 日志降级、2026-10-20 I/O 入池
---

> 摘要: grilling 三轮 16 问收敛(两次纠正: TM 替代、多实例共享), 计划 26-10-16-0541(Open); S0–S9 已落地(骨架/采样/落盘/控制面/通知/自启/配置面/接收面/过渡文档/守阵); S10 待授权
> 最后活动: 2026-11-03 06:32

# activeContext · global-traffic-monitor(26-10-16-0541)

用户要求: 自写独立监视全局流量小工具 —— 独立于 auto-qb 主进程、开机自启、超阈值通知 auto-qb、设置进 auto-qb WebUI(前置报告 26-10-13-1034 指数据源滞后)。**两次范围纠正**: ①定位 = TrafficMonitor 替代(只记整机流量历史, 不做限速/provider 抽象); ②工具是共享服务, auto-qb 是其配置方与消费者之一, 须支持多实例并发接入。

拍板口径: 整机全适配器排回环; 独立包+独立 venv; psutil 采集; TM 兼容 dat 原子写; 控制面 127.0.0.1:8099+token; Δ≥100MiB 通知+启动补发; 工具自有 config、auto-qb WebUI 代理 PUT; 多实例订阅+心跳租约+各自冷却; 通知→auto-qb 重发快照刷新历史图; dat_path 双支持; 三平台自启由 WebUI 开关幂等注册。

**产出**: 计划 `memory-bank/plans/26-10-16-0541-plan-global-traffic-monitor.html`(Open; S0–S10, 参数/依赖/黄金法则, 验收 E1–E6); 档案 `memory-bank/tasks/26-10-16-backend-global-traffic-monitor.md`(阈值 #4)。

**R1 · S0 已实施(2026-10-16 06:01, clone 46d2ea11)**: 新建 `tools/global-traffic-monitor/` 骨架 11 文件(独立 venv、仅 psutil+filelock、入口 gtm), 零 auto-qb 触碰。出口: `gtm --version`=0.1.0、根环境 import psutil 仍失败、冒烟过。坑: 工具内 pytest 拾取根 pytest.ini → pyproject 补 `[tool.pytest.ini_options]`。基线 s0。

**R2 · S1 已实施(2026-10-16 08:15, 开工同步 @ febac58e)**: sampler.py ~430 行(过滤固定顺序 include→exclude→loopback→down; 重置归零告警不产负流量; 跨天 00:00 硬切; restore state 四形态降级 + dat 今天行 KB→字节兜底[行序不敏感, 与 curves.py 正则逐字一致, 不 import auto-qb])。守阵过; 红验全红; 真机只读冒烟过。坑: redverify 复发+1 形态十(LF write_text 反向污染 + read_text 探针洗白; 改 bytes 层+恒等还原)。基线 s1。

**R3 · S2 已实施(2026-10-16 08:55, 开工同步 @ b688437c)**: storage.py ~430 行(atomic_write_text[tmp+fsync+os.replace]; DatStore[lines 头+新日在前+KB 取整+坏行跳过]; StateStore; FlushPolicy[Δ≥1MiB 或 ≥30s]; SingleInstanceLock[filelock+PID]) + __main__ run(单轮失败不退出)。守阵过; 红验全红; 并发读只见完整文件; kill -9 双恢复; 双实例 fail-fast。坑: platform-fs 两节(Windows os.replace 瞬时拒绝; Git Bash `$!`=MSYS pid)。基线 s2。

**R4 · S3 已实施(2026-10-16 09:46, 开工同步 9d9ec930 后)**: config.py ~240(参数+校验) + server.py ~360(Token urlsafe(32) 启动即生成; 强制 127.0.0.1; /status /config / 订阅三端点[租约 180s]) + storage 订阅表+事件号(RLock) + _run_loop 抽出 + pyyaml 6.0.3。守阵过; 红验全红; 真机冒烟过。真缺陷已修: ①热重载静默杀循环(正则列表误传 list; 修=| 并入+校验层拒+线程存活断言); ②token 惰性生成(start 即生成)。坑: redverify 复发+1 形态三/十一(解释器漂移假红; 钉 venv 解释器)。基线 s3。

**R5 · S4 已实施(2026-10-16 10:16, 开工同步 a3ec82ef 后)**: notifier.py ~230(累计基数=上次事件时刻当日合计, **仅派发成功后推进**[首版踩已修]; 跨天/回退只重置基数; 每订阅者一线程; 先落盘→事件号+1→派发) + bump_event_id + 守阵过; 真机 12s 193 帧而假死端点占满 3s; 红验过。发现: ①基数推进纪律; ②红验 M2 未判红(被 total<_last_total 兜底掩盖; red-verify-must-hit-behavior 新形态「兜底分支掩盖」); ③PUT /config 全量覆盖实锤 → S6 读后写。坑: redverify 复发+1 形态十二(TimeoutExpired 未接住)。基线 s4。

**R6 · S5 已实施(2026-10-16 11:09, 开工同步 5654b778 后)**: installer.py ~460(AutostartPlan 解释器=sys.executable; Win schtasks ONLOGON / Linux systemd user / macOS launchd plist; 注入式 Runner; 只信退出码)。幂等判据严格化: 期望态达成才 no-op, Linux/macOS 须「文件一致且已启用」, 只查存在会误判。红验过。真机降级: schtasks.exe 被 Program Blacklist 拦(真判据 stderr PROGRAM BLOCKED) ⇒ 计划任务真注册+登录自起未跑(缺口待补); 其余 PASS。新坑 session-program-blacklist。顺序: 先落命令面, S6 后消费, 无倒挂。基线 s5。

**R7 · S6 已实施(2026-10-16 11:45, 开工同步 3473aa9a 后)**: 首个触碰 auto-qb 步骤; 计划改版(拍板 B 案): 工具控制面新增 POST /autostart, auto-qb 经 HTTP 代理。落点: ①配置段 4 点同步(schema i-traffic; 6 键 enabled/tool_url/token_path/subscribe/cooldown/autostart); ②POST /autostart(200/501/500/400); ③代理 /status、/config(400 透传, 不可达→502)、/autostart(501); ④设置页分区(读后写)。新键过守卫(键面 160→167); 守阵过; 红验过。发现: ①parse_time 须带单位("0S"); ②前端 v-if 链跨分片, 新分区只能链尾→frontend-split。坑: single-file-coverage-gate 复发+1(裸跑单文件假红; 加 --no-cov -n 0)。基线 s6。

**R8 · S7 已实施(2026-10-16 14:04, 开工同步 16d66653→fd26c4e7 快进)**: 接收面 POST /api/traffic/monitor/notify(六键体校验 400; 事件号+冷却双闸 per app 实例; 闸门/未启用 200+action, 体非法 400) + `webui/tool_client.py`(控制面 I/O 全在订阅线程、主循环只置期望态、stop 有界 join、心跳 404 自愈) + module 三时刻接线 + refresh_traffic + speed_curve_mod 只读刷新(不查档/不读写限速)。守阵含端到端; 红验过。发现: ①注销须用注册时地址/密钥路径; ②期望态按恒等 True 判(MagicMock 桩段会起线程); ③stop() 超时不摘引用(否则双订阅); ④写入判据拦下四文件, 授权改写。未闭合 E2。基线 s7。

**R9 · S8 已实施(2026-10-16 17:37, 开工同步 22f0dad8→1ae16235 快进)**: 纯文档轮: `docs/configuration.md` 新段(定位/目录/参数表覆盖语义/自启/6 键/迁移检查单/24h 对照[容差 ≤5%]/双写者禁令)。出口: 文档守卫全绿, links/drift/caps 过; 检查单可跑部分实跑(gtm run 45s: 30s 节流/token 43 字符/401+200)。发现: 3 文档被写入判据拦下, 授权等价改写; 「整文件级探针」并入坑档(复发+1)。未闭合 E1 24h 与自启真机。基线 s8。

**R10 · S9 已实施(2026-10-16 18:24, 开工同步 f8db7019)**: 只补缺口: 新增 `tests/test_traffic_monitor_dat.py` 2 条(工具 DatStore 真写者产出 dat → dat_path 只读刷新读回: 历史行升序/KB 取整/累计重算/更早月份只进历史; 格式单点同值) + notify 补「错 Bearer 也 401」。写法约束: 根测试禁止起子进程 ⇒ 进程内按源码路径加载工具写者(只替 import psutil)。红验过。发现: ①跨侧守阵不能起子进程; ②test.full 踩无 uv on PATH(复发+1); ③窄池假存活(mutation-pool-artifact 复发+1)。未闭合 S10。基线 s9。

**待办(截至 2026-10-20)**: S0–S9 已落地, S10 待逐项授权。①S5 真机缺口(计划任务真注册+登录自起, 需解锁 schtasks), 同缺口在 S8 检查单第 3 步再现; ②S7/S8 真机联调(E2); ③E1 24h 并行对照。档案 2026-10-30 记: S6–S8/S10 已由计划 26-10-17-0339 S15–S19 承接, 本计划口径收口。

**R11(2026-10-18 19:48)**: 通知链路三级日志 INFO→DEBUG: 用户报大流量日(事件 #1200)刷屏, 拍板降级; 消息文本不变, 触发与两条 WARNING 不降; 新增 2 条日志级守阵。提交 318617c9 已推 Gitee develop; 合并后闸门被远端 d7fc97ae(别会话 alias_fs P0)的 6 条环境性红挡下(WinError 1314 无 symlink 权限, 无关本轮), 按补推口径 ship.push 收尾; 未替别会话改码。基线 26-10-18-1947。

**R12(2026-10-20 23:49)**: 只读排查 gtm 常驻进程「I/O 其它」偏高: 实测 72.42 次/秒(累计 782 万)= psutil 网卡枚举控制操作(每轮 177 次), 读 0 次/秒、写 0.42 次/秒=设计值; 入池 perf issue 26-10-20-2345(Open), 未改码。

**引用**(`mb/` = `memory-bank/`): `mb/reports/26-10-13-1034-report-global-traffic-source-lag.html`; `mb/plans/26-10-17-0339-plan-global-traffic-source-integration.html`; 基线 `mb/testing/baselines/attachments/`: s0–s9 = `26-10-16-{0601|0815|0855|0946|1016|1109|1145|1404|1737|1824}-global-traffic-monitor-s{0..9}.md` + `26-10-18-1947-notify-log-debug.md`; 坑档 `mb/pitfalls/`: `testing/{nested-pytest-config,redverify-anchor-lineendings,red-verify-must-hit-behavior,single-file-coverage-gate,mutation-pool-artifact}.md`、`backend/platform-fs.md`、`ops/session-program-blacklist.md`、`web-ui/frontend-split.md`; issue `mb/issues/26-10-20-2345-perf-gtm-sampler-other-io.html`; 文档 `docs/configuration.md`、`mb/config-reference/keys.md`、根 `README.md`。

**R13(2026-11-03 06:16):** 修复 gtm 跨进程单实例锁用例在英文 Windows runner(cp1252)下 print 中文 UnicodeEncodeError 失败: 子进程注入 PYTHONIOENCODING=utf-8 + 捕获端 encoding=utf-8, 同文件另一子进程用例与 manual_e2e_relay 同因加固; 被拒信号(BUSY+PID)断言提到退出码之前; cp1252 复现改前红改后绿, test.gtm 全绿; 坑档并入 testing/ci-only-guard.md

**R14(2026-11-03 06:32):** 生产侧 stdio 编码兜底: gtm __main__ 入口新增 _utf8_stdio() 把非 UTF-8 的 stdout/stderr reconfigure 成 UTF-8(errors=replace, 中文不丢, 退出码语义不变), 覆盖 print/argparse/logging 出口; 新增 3 条守阵(cp1252 TextIOWrapper 整行中文 / python -m gtm 帮助 exit 0 / endpoint stderr 中文 exit 1); 修复 test_module_main_guard_runs_cli 的 RuntimeWarning(runpy 前临时摘除 gtm.__main__ 再还原, 不压制警告); test.gtm 全绿且 0 warning; 同因并入 pitfalls/ops/console-encoding.md
