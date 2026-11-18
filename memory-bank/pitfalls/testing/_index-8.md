# testing — 测试 / 冒烟 / 仿真纪律 · 卷 8/8

> **本文件是生成物, 不要手改** —— 由 `commands run kb.index` 生成; 主索引 [_index.md](_index.md) 是分卷路由。
> 本卷主题: `tmpdir.md` … `xdist-worker-global-snapshot.md`(共 11 条); 主题越多时索引按文件名分卷, 每卷 ≤ 8,000 字符。
> **检索纪律**: 先读本索引定位, 再按需打开单个主题文件 —— **不要整读本目录**。

## 主题

| 主题 | 一句话 | 触发词 |
|---|---|---|
| [tmpdir.md](tmpdir.md) | 临时目录必须在 `tempfile.gettempdir()` 之下、覆盖率文件不能留仓库根、`TMPDIR` 不设收尾会崩, 别手工加前缀。 | 跑全量, basetemp, TMPDIR, 临时目录, 覆盖率文件, pytest-current, 耗时, 手工跑子集, R 盘缺席, 回落 TEMP, 快照守阵, 自举, auto-qb-tests, 外部 TMPDIR 拒收, rc=4, rc=3, 测试互斥锁, coverage 落点 |
| [tool-mode-coverage.md](tool-mode-coverage.md) | 一次性工具/校验器若支持**多种运行模式**(全量 vs 分批、dry-run vs apply、演练 vs 生产), 而演练只覆盖了其中一种, 另一种模式的代码路径就**从未被任何用例或红验碰过** —— 它要么静默放过(假绿), 要么在真实使用时才报一堆假红。判别: 工具的每种模式都应有独立的演练 + 红验, 且红验注入的失败形态要与该模式**同构**; 只看「工具跑通了一次」不等于「工具的所有模式都验过」。 | 一次性工具, 迁移脚本, 分批模式, 批模式, --files 子集, dry-run, 演练, 校验器, 红验, 模式覆盖, 假绿, 假红, 只演练了一种模式, 末批, 删除源文件, 收尾批, split_test_web |
| [ui-preview-harness.md](ui-preview-harness.md) | 前端视觉改动的真浏览器冒烟: Vue 生产版拿不到 `app._instance`、无头 Edge 的 virtual-time 与 SSE 坑 —— 都有固定解法。 | UI 冒烟, 截图, 无头浏览器, 弹窗驱动, Vue 实例, createApp, 截图工装 |
| [unreached-branch-guard.md](unreached-branch-guard.md) | 一个测试名字/断言都对, 但**夹具数据让被测分支根本进不去**, 于是它测的是另一条路; | 红验, 守阵, 假绿灯, 假绿, 分支不可达, 未导入, NameError, 未执行行, 覆盖率盲区, 夹具, 注入 bug, 原地改配置, 热重载短路 |
| [uplot-axes-splits-generator.md](uplot-axes-splits-generator.md) | 读 uPlot x 轴刻位(tick 位置)时 `u.axes[0].splits` **不是数组**, 是生成刻位的函数(vendor 1.6.32: 绘制时 `t._splits = t.splits(...)` 回填); 拿它当数组用得到的是函数对象本身(长度/下标全错或 typeof 直接炸), 真·刻位数组在 `u.axes[0]._splits`(每次绘制回填的网格/轴标同源真值)。读 `._splits` 只读运行态回填值, 不碰生产内部, e2e 可用。 | uPlot axes, splits, _splits, 刻位真值, tick 位置, split 集, 网格刻度, 生成器函数, vendor 1.6.32, 轴标断言, split 数恒定 |
| [uplot-hover-hit-area.md](uplot-hover-hit-area.md) | 给 uPlot 图写「悬停第 N 个桶」类 e2e 断言时, 拿宿主 `.qb-chart-host` 的盒子推像素会落到**交互面之外** —— uPlot 收不到 mousemove, hoverIdx 回落 -1, 且报错指向 tooltip 而非几何、看不出病因; 真正的交互面是宿主内那个 `.u-over`(实测宿主宽 1382px 时它从 x+84 起、宽 1273)。等距栅格下桶 index 与 px 严格线性, 两点标定即能解出任意桶的落点。 | 悬停断言, hoverIdx -1, 落点到图外, u-over, qb-chart-host, uPlot 交互面, 纵轴槽, 84px, 桶 index 转 px, 两点标定, e2e 点画布, tooltip 不出现 |
| [uv-build-file-lock.md](uv-build-file-lock.md) | 同 clone 并行跑两条 uv 测试任务(如 test.gtm + test.quick)时, 后到者 uv 构建子包失败 os error 32 —— 串行重跑即绿, 不是代码问题 | 并行跑测试, os error 32, 文件被占用, Failed to build, uv, test.gtm, test.quick, 另一个程序正在使用此文件 |
| [vnu-rejects-vue-templates.md](vnu-rejects-vue-templates.md) | `shared/tpl/*.html` 是 Vue 模板**片段**, `v-if` / `@click` / `:class` 是指令不是 HTML 属性 —— 送 W3C v.Nu 校验必然逐条报 `Attribute "…" not allowed`, 提交闸门因此整批红 | v.Nu 报 Attribute not allowed, check_html --vnu 红, 提交闸门 HTML 规范级, Vue 指令校验, tpl 分片, overlays.html, 皮肤壳 index.html, 模板片段不是文档 |
| [web-auth-test-forms.md](web-auth-test-forms.md) | TestClient 缺省 Host=testserver / client=testclient 都不是本机形态, 跨站闸(Host 白名单)开启后必 403; loopback 免鉴权分支**先于** token 校验 —— skip 开启时 loopback 对端连错密钥也 200。 | 改 webui 鉴权, 写鉴权测试, skip_local_verify, Host 白名单, 跨站, 403, 错密钥 200, TestClient, client 参数 |
| [win-fake-clock-timestamp-oserror.md](win-fake-clock-timestamp-oserror.md) | 生产纯函数新增「缺 self 状态时按传入 now 现场推算本地日/月 epoch」的回落分支, 被既有用例的 1970 附近假时钟(流量族惯用 `H1 = 11 * HOUR = 39600` 量级)首次触达 —— Windows 上 `datetime.timestamp()` 对 1970 前**本地**日期抛 `OSError [Errno 22] Invalid argument`, 一批与本次改动无关的既有用例在 Windows 面红、Linux 面绿。修法 = 两级推算包 `try/except (ValueError, OSError, OverflowError)` 静默缺级: 生产时钟恒正(≥1.7×10^9)该面不可达, 纯增益面缺一级只回到改动前形态。通用教训: 新读侧函数被假时钟 first-touch 时, 本地时间换算的异常面要按平台放宽, 且**别改用例时钟迁就实现**。 | Windows, 假时钟, 1970, timestamp, OSError, Errno 22, Invalid argument, v4_day_epoch, v4_month_epoch, 无关用例集体红, Linux 绿 Windows 红, 新增读侧函数, 本地时间换算, 异常型平台差分 |
| [xdist-worker-global-snapshot.md](xdist-worker-global-snapshot.md) | xdist 每个 worker 是常驻进程, 量「全进程线程数/句柄数等全局快照不变」的断言会被同 worker 其它用例的线程启停污染 —— 单跑恒绿、全量偶发红, 且失败方向与被测模块无关。 | active_count, threading.active_count, 线程计数, 全局快照, xdist, worker 进程, 偶发红, 单跑通过, 全量红, flaky, 不变式断言, 模块不建线程 |
