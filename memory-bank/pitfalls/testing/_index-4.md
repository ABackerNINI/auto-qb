# testing — 测试 / 冒烟 / 仿真纪律 · 卷 4/4

> **本文件是生成物, 不要手改** —— 由 `commands run kb.index` 生成; 主索引 [_index.md](_index.md) 是分卷路由。
> 本卷主题: `sidefx-import-time-temp-roots.md` … `xdist-worker-global-snapshot.md`(共 22 条); 主题越多时索引按文件名分卷, 每卷 ≤ 8,000 字符。
> **检索纪律**: 先读本索引定位, 再按需打开单个主题文件 —— **不要整读本目录**。

## 主题

| 主题 | 一句话 | 触发词 |
|---|---|---|
| [sidefx-import-time-temp-roots.md](sidefx-import-time-temp-roots.md) | sidefx 会话守卫的临时根集合不得在模块导入时固化 | 串行 -n 0 跑测试出现 sidefx 越界, 临时目录内删除/建链被判越界, TEMP_ROOTS 与 gettempdir 不一致 |
| [sim-root-sentinel.md](sim-root-sentinel.md) | `scripts/sim_qb.py` 的 `prepare_root` 只在 root 目录**不存在**时才写哨兵 `.auto-qb-sim-root`; 自己先 `mkdir` 出来的空目录第一次跑会被当"合法空目录"放过但不留哨兵, 跑过一次目录非空后, 之后每次起 s… | dev.sim, B1, 哨兵, sim root, 已存在且非空, BoundaryViolation, 删除场景 |
| [single-file-coverage-gate.md](single-file-coverage-gate.md) | 只跑单个测试文件时, 全部用例绿但收尾仍打 `FAIL Required test coverage of <门槛>% not reached. Total coverage: ~18%` —— 覆盖率**全局门槛**只对全量收集有意义, 部分运行收集面小必然红, 用例本身全过。… | test.one, 单文件, 单测一个文件, coverage FAIL, not reached, 18%, 假红, 排查单个用例, 裸跑 pytest 单文件 |
| [smoke.md](smoke.md) | `scripts/ui_harness.py` + `e2e/`(@playwright/test)是本仓库覆盖前端渲染的唯一手段; 这里是它的环境坑与验证手法 | 浏览器冒烟, e2e, Playwright, Edge, 白屏, 前端改完, 时序复现, 聚合行状态色, Cannot find module playwright, 修饰键点击, Ctrl+click, 多选失败, site-chip,… |
| [stale-repo-copy-scan-red.md](stale-repo-copy-scan-red.md) | gitignored 的旧全量仓库副本被 `rglob` 扫描守阵算进「源码散落」, 报错指向副本而非产品代码; 移出副本即绿, 不是代码缺陷。 | test_free_port_single_source, 端口实现散落, tmp-analysis, 旧仓库副本, rglob, 扫描守阵假红, 环境残留 |
| [static-guard-mutation.md](static-guard-mutation.md) | 读 JS/模板源码的静态守阵, 若断言只查「字符串在不在」或把多个弱正则串起来, 行为被突变(短路禁用/删语句)后它照样绿 —— 守阵看着活着, 拦不住真突变。升级方向: **整行活性锚定**(匹配带上下文的整行/整块, 摘一个 token 即失配) + **逐分支语句清单**(… | 静态守阵, 静态守卫, 字符串包含, in 断言, 链式正则, 突变盲区, 红验不红, 守阵空转, 短路禁用, 删语句 |
| [stub-bypass-apply.md](stub-bypass-apply.md) | 桩直改字段/手写派生产物(绕过生产单点函数)当时能过, 生产侧后来加了**以生产函数副作用为判据**的新判定后, 桩链路静默退化成另一条路径 —— 表现是「生产对、桩错」且无报错。本仓实例: ui_harness 直写 delta_fields 绕过 store._apply,… | ui_harness, 冒烟桩, delta_fields, rounds_applied, keyed, unkeyed_command_source, 恒 full, store._apply, 桩失真, 手写派生字段, view_ch… |
| [stubs-sim.md](stubs-sim.md) | 测试替身"长得像"不等于"够用"; 仿真端最容易变成"自以为在测"的测假陷阱。 | 写替身, FakeClient, FakeTorrent, FakeQbServer, sim_qb, 仿真, 判据空壳, 反向对照, 回执判定, FakeConfig, 假配置, 新配置键, 替身漂移, 枚举成员, dev 脚本, ui_… |
| [test-lock-path-injection.md](test-lock-path-injection.md) | 工具侧 `Storage` 的默认锁锚点(S12/D8)从 `data_dir` 迁到用户级指针目录(`%LOCALAPPDATA%/global-traffic-monitor/instance.lock` 等) —— 于是 `Storage(str(tmp_path))` 后… | 加/改工具侧测试, Storage, acquire_lock, 真实用户目录, PermissionError WinError 5, 拒绝访问, AppData, LOCALAPPDATA, global-traffic-monitor… |
| [tests-real-qb-api-traps.md](tests-real-qb-api-traps.md) | 手工压测/relocate 取证直接打 qB WebAPI 时的五类坑 —— 短 hash 静默 200、renameFolder 账面级假成功(ENOENT 也算成功且零日志)、addTrackers 参数是单数 hash、FakeTracker 的 peer 表是构造时静态注… | tests-real, 手工压测, renameFolder, renameFile, addTrackers, FakeTracker, 短hash, 静默200, bencode decode, 真机实验, relocate 取证, 内… |
| [time-tick-collapse-strict-advance.md](time-tick-collapse-strict-advance.md) | 挂钟严格推进断言的本机粒度坍缩: 背靠背 time.time() 同值(判别须追基线值来源 —— 活钟读数才中招, 夹具常量天然稳, 2026-10-22 实证误报一例) | ts 推进, time.time 同值, 背靠背, 粒度坍缩, 严格大于断言, 递增假钟, monkeypatch time, flaky, traffic_view, _publish |
| [timing-tolerance.md](timing-tolerance.md) | 挂钟计时断言的两个假红面 —— ①**下界**零容差: Windows 等待原语按 15.6ms 定时器刻度取整, 50ms 等待实测可提前到 46.8ms(3 刻度); ②**上界**零容差: 合法负载 / CI 抢占直接撞线(2026-10-05 实测)。守阵余量一律以"被守… | 计时断言, 挂钟, elapsed, sleep 精度, 定时器刻度, 假红, 节流守阵, 节拍, Event.wait, 抖动, flaky, 耗时上界, 性能上界, CPU 时间, process_time, 并行 worker, xd… |
| [tmpdir.md](tmpdir.md) | 临时目录必须在 `tempfile.gettempdir()` 之下、覆盖率文件不能留仓库根、`TMPDIR` 不设收尾会崩, 别手工加前缀。 | 跑全量, basetemp, TMPDIR, 临时目录, 覆盖率文件, pytest-current, 耗时, 手工跑子集, R 盘缺席, 回落 TEMP, 快照守阵, 自举, auto-qb-tests, 外部 TMPDIR 拒收, rc… |
| [tool-mode-coverage.md](tool-mode-coverage.md) | 一次性工具/校验器若支持**多种运行模式**(全量 vs 分批、dry-run vs apply、演练 vs 生产), 而演练只覆盖了其中一种, 另一种模式的代码路径就**从未被任何用例或红验碰过** —— 它要么静默放过(假绿), 要么在真实使用时才报一堆假红。判别: 工具的每… | 一次性工具, 迁移脚本, 分批模式, 批模式, --files 子集, dry-run, 演练, 校验器, 红验, 模式覆盖, 假绿, 假红, 只演练了一种模式, 末批, 删除源文件, 收尾批, split_test_web |
| [ui-preview-harness.md](ui-preview-harness.md) | 前端视觉改动的真浏览器冒烟: Vue 生产版拿不到 `app._instance`、无头 Edge 的 virtual-time 与 SSE 坑 —— 都有固定解法。 | UI 冒烟, 截图, 无头浏览器, 弹窗驱动, Vue 实例, createApp, 截图工装 |
| [unreached-branch-guard.md](unreached-branch-guard.md) | 一个测试名字/断言都对, 但**夹具数据让被测分支根本进不去**, 于是它测的是另一条路; | 红验, 守阵, 假绿灯, 假绿, 分支不可达, 未导入, NameError, 未执行行, 覆盖率盲区, 夹具, 注入 bug, 原地改配置, 热重载短路 |
| [uplot-hover-hit-area.md](uplot-hover-hit-area.md) | 给 uPlot 图写「悬停第 N 个桶」类 e2e 断言时, 拿宿主 `.qb-chart-host` 的盒子推像素会落到**交互面之外** —— uPlot 收不到 mousemove, hoverIdx 回落 -1, 且报错指向 tooltip 而非几何、看不出病因; 真正的… | 悬停断言, hoverIdx -1, 落点到图外, u-over, qb-chart-host, uPlot 交互面, 纵轴槽, 84px, 桶 index 转 px, 两点标定, e2e 点画布, tooltip 不出现 |
| [uv-build-file-lock.md](uv-build-file-lock.md) | 同 clone 并行跑两条 uv 测试任务(如 test.gtm + test.quick)时, 后到者 uv 构建子包失败 os error 32 —— 串行重跑即绿, 不是代码问题 | 并行跑测试, os error 32, 文件被占用, Failed to build, uv, test.gtm, test.quick, 另一个程序正在使用此文件 |
| [vnu-rejects-vue-templates.md](vnu-rejects-vue-templates.md) | `shared/tpl/*.html` 是 Vue 模板**片段**, `v-if` / `@click` / `:class` 是指令不是 HTML 属性 —— 送 W3C v.Nu 校验必然逐条报 `Attribute "…" not allowed`, 提交闸门因此整批红 | v.Nu 报 Attribute not allowed, check_html --vnu 红, 提交闸门 HTML 规范级, Vue 指令校验, tpl 分片, overlays.html, 皮肤壳 index.html, 模板片段不是… |
| [web-auth-test-forms.md](web-auth-test-forms.md) | TestClient 缺省 Host=testserver / client=testclient 都不是本机形态, 跨站闸(Host 白名单)开启后必 403; loopback 免鉴权分支**先于** token 校验 —— skip 开启时 loopback 对端连错密钥也… | 改 webui 鉴权, 写鉴权测试, skip_local_verify, Host 白名单, 跨站, 403, 错密钥 200, TestClient, client 参数 |
| [win-fake-clock-timestamp-oserror.md](win-fake-clock-timestamp-oserror.md) | 生产纯函数新增「缺 self 状态时按传入 now 现场推算本地日/月 epoch」的回落分支, 被既有用例的 1970 附近假时钟(流量族惯用 `H1 = 11 * HOUR = 39600` 量级)首次触达 —— Windows 上 `datetime.timestamp()… | Windows, 假时钟, 1970, timestamp, OSError, Errno 22, Invalid argument, v4_day_epoch, v4_month_epoch, 无关用例集体红, Linux 绿 Windo… |
| [xdist-worker-global-snapshot.md](xdist-worker-global-snapshot.md) | xdist 每个 worker 是常驻进程, 量「全进程线程数/句柄数等全局快照不变」的断言会被同 worker 其它用例的线程启停污染 —— 单跑恒绿、全量偶发红, 且失败方向与被测模块无关。 | active_count, threading.active_count, 线程计数, 全局快照, xdist, worker 进程, 偶发红, 单跑通过, 全量红, flaky, 不变式断言, 模块不建线程 |
