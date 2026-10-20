# 26-10-16-backend-global-traffic-monitor — 全局流量监视小工具 (TrafficMonitor 替代)

**Status:** In Progress
**Added:** 2026-10-16
**Updated:** 2026-10-20
**Summary:** 自写独立整机流量历史记录小工具(TM 替代): 独立进程+开机自启+TM 兼容 dat 原子落盘+阈值变化主动通知多 auto-qb 实例刷新 WebUI 历史图。计划 26-10-16-0541(S0–S10 逐步显式授权); S0 包骨架 + S1 采样器 + S2 落盘 + S3 控制面 + S4 通知 + S5 自启 + S6 auto-qb 配置面 + S7 auto-qb 接收面 + S8 集成与过渡 + S9 守阵测试已落地(含用户拍板改版: 工具控制面加 POST /autostart); S10 待逐项授权。
**Refs:** memory-bank/plans/26-10-16-0541-plan-global-traffic-monitor.html, memory-bank/pitfalls/testing/nested-pytest-config.md, memory-bank/pitfalls/backend/platform-fs.md, memory-bank/pitfalls/testing/redverify-anchor-lineendings.md, memory-bank/pitfalls/testing/red-verify-must-hit-behavior.md, memory-bank/pitfalls/ops/session-program-blacklist.md, memory-bank/pitfalls/testing/single-file-coverage-gate.md, memory-bank/pitfalls/web-ui/frontend-split.md, memory-bank/testing/baselines/26-10-16-0601-global-traffic-monitor-s0.md, memory-bank/testing/baselines/26-10-16-0815-global-traffic-monitor-s1.md, memory-bank/testing/baselines/26-10-16-0855-global-traffic-monitor-s2.md, memory-bank/testing/baselines/26-10-16-0946-global-traffic-monitor-s3.md, memory-bank/testing/baselines/26-10-16-1016-global-traffic-monitor-s4.md, memory-bank/testing/baselines/26-10-16-1109-global-traffic-monitor-s5.md, memory-bank/testing/baselines/26-10-16-1145-global-traffic-monitor-s6.md, memory-bank/testing/baselines/26-10-16-1404-global-traffic-monitor-s7.md, memory-bank/testing/baselines/26-10-16-1737-global-traffic-monitor-s8.md, memory-bank/testing/baselines/26-10-16-1824-global-traffic-monitor-s9.md, memory-bank/pitfalls/testing/no-uv-fallback.md, memory-bank/pitfalls/testing/mutation-pool-artifact.md
**Topics:** global-traffic-monitor

## 原始请求

用户要求自写独立监视全局流量的小工具: 独立于 auto-qb 主进程、开机自启、整机流量变化超阈值时主动通知 auto-qb、工具配置与自启开关进入 auto-qb WebUI 设置页、支持多个 auto-qb 实例同时接入。grilling 三轮 16 问收敛中用户两次纠正需求范围: ①工具定位 = TrafficMonitor 替代, 仅记录整机流量历史(非限速/provider 抽象); ②工具是共享服务, auto-qb 是其配置方与消费者之一。

## 思考过程与决策

全部决策见计划 §01 拍板结论表(监控口径/进程形态/自启/采集库/落盘格式/控制面/通知/配置主权/多实例/接收面/过渡共十项), 实施不得再自行变更; 确需变更按「计划改版 = 同文件内变更记录 + 抬 doc-updated」处理。黄金法则映射见计划 §07, 验收 E1–E6 见 §08, 风险对策见 §09。

## 实现计划

计划文档 S0–S10 共 11 步(包骨架→采样→落盘→控制面→通知→自启→auto-qb 配置面→接收面→过渡→守阵→验收), 每步带改动面、要点与出口判据。顺序与依赖见计划 §06: S0–S2 先出「记录+落盘」闭环(手动跑即可验证, 不等 auto-qb 改动); S3/S4 完成后与 S7 联调; S6 依赖控制面; S5 依赖 S6 开关入口; S8–S10 收口。每步需用户逐项显式授权, 「继续」不算。

## 子任务状态表

| 步 | 内容 | 状态 |
|---|---|---|
| S0 | 包骨架与依赖隔离 | Done (26-10-16-0601) |
| S1 | 采样器 sampler | Done (26-10-16-0815) |
| S2 | 落盘 storage | Done (26-10-16-0855) |
| S3 | 控制面 server | Done (26-10-16-0946) |
| S4 | 通知 notifier | Done (26-10-16-1016) |
| S5 | 自启 installer | Done (26-10-16-1109) |
| S6 | auto-qb 配置面 | Done (26-10-16-1145) |
| S7 | auto-qb 接收面 | Done (26-10-16-1404) |
| S8 | 集成与过渡 | Done (26-10-16-1737) |
| S9 | 守阵测试 | Done (26-10-16-1824) |
| S10 | 真机验收 | Open |

## 进度日志

### R1 · S0 实施 (2026-10-16 06:01)

用户指令「实施计划S0:26-10-16-0541-plan-global-traffic-monitor.html」= 对 S0 的显式授权(S1–S10 不动)。开工同步 46d2ea11(快进)。

**落点**(纯新增, 零 auto-qb 文件触碰): `tools/global-traffic-monitor/` 11 文件 —— `pyproject.toml`(hatchling、src 布局、包名 global-traffic-monitor、入口 `gtm = gtm.__main__:main`、运行时依赖仅 psutil+filelock、dev 组 pytest、自带 `[tool.pytest.ini_options]`)、`src/gtm/` 八文件(`__init__`/`__main__` + config/sampler/storage/server/notifier/installer 六个模块均为 S1–S5 占位)、`README.md`、`tests/test_smoke.py`。

**出口判据全过**: ①独立 venv(`uv sync`;psutil 7.2.2 / filelock 4.2.0 / pytest 9.1.1 仅入工具 `.venv`)下 `gtm --version` 输出 `gtm 0.1.0`; ②隔离验证: 仓库根 `uv run python -c "import psutil"` 仍 ModuleNotFoundError —— 装/卸验证两环境互不污染; ③工具冒烟 4 条全过(版本一致性/模块可导入/--version/骨架提示)。根 `test.full` 回归数字见基线切片 `baselines/26-10-16-0601-global-traffic-monitor-s0.md`(工具测试不在根 testpaths 内)。

**实施期坑**: 工具目录内 `uv run pytest` 向上拾取仓库根 pytest.ini(rootdir 上移, addopts 的 `-n`/`--cov` 在工具 venv 不可用 → unrecognized arguments)。已在工具 pyproject 补 `[tool.pytest.ini_options]`(更近的配置优先), 坑档 `pitfalls/testing/nested-pytest-config.md`。

**滚动面**: 计划 HTML 就地更新(doc-updated=26-10-16-0601, §04 增 R0 实施记录, 补 CSS color-scheme: dark 过 dark 守卫, doc-refs 补本档案) · activeContext 切片追加 R1 · 本档案新建(立档阈值 #4 命中: 已产出计划) · kb.index 重建 · 基线切片新建。

**行号基准**: S0 为纯新目录, 与计划基准 3ba069d7 无关; S6/S7 触碰 auto-qb 前按计划脚注逐条复核漂移。未提交(待用户「提交」指令)。


### R2 · S1 实施 (2026-10-16 08:15)

用户指令「实施计划S1:26-10-16-0541-plan-global-traffic-monitor.html」= 对 S1 的显式授权(S2–S10 不动)。开工同步快进至 febac58e。

**落点**(改 5 文件, 零 auto-qb 触碰): `src/gtm/sampler.py` S1 占位 -> 全量实现(~430 行) + `tests/test_sampler.py` 新文件 29 条守阵 + 工具 README/`__init__.py` 进度注记。设计要点: AdapterFilter 固定顺序(include 白名单 → exclude 黑名单 → exclude_loopback → exclude_down, include 不翻案后两个开关, 保守默认); 回环判别覆盖 lo/lo0/Loopback Pseudo-Interface 1 三平台名; sample_once 单次纯计算(休眠循环按计划属 S2 run), 上下行独立判定重置(本次 < 上次 -> delta 记 0 + WARNING, 不产负流量); 跨天 00:00 硬切累计清零(SampleResult.day_rolled 上报, 旧行落盘属 S2); restore 覆盖今天接续/昨天清零基线续/未来判损坏/六变体损坏降级/未采样空快照自洽; restore_from_dat 今天行 KB->字节兜底(行序不敏感, 解析正则与 curves.py 一致, 不 import auto-qb); snapshot() 六字段载荷 round-trip。

**出口判据全过**: ①工具 33/33(4 条 S0 冒烟 + 29 条 S1, 全替身 hermetic); ②红验 4 条单行锚点突变(重置归零失效/跨天不清零/loopback 不过滤/dat 兜底失效)全部判红, 字节还原后复绿; ③真机只读冒烟: 4 网卡在册(以太网/VMnet1/VMnet8/Loopback 伪接口), 默认过滤正确排除 loopback, 2s 窗 delta up 0.68–1.08 MB / down 33–67 kB 量级吻合, snapshot 载荷字段正确。

**实施期坑**: 临时红验脚本照抄形态四旧例用文本模式读写 —— `Path.write_text()` 在 Windows 把 LF 源码写成 CRLF(apply 后整文件被静默转行尾), 之后 LF 锚点全失配; 且排查用的 `read_text()` 探针走 universal newlines 把 CRLF 归一化洗白, 与脚本内 read_bytes 结果互相矛盾藏住暗点。已按形态十补进 `pitfalls/testing/redverify-anchor-lineendings.md`(复发+1; 未命中原因: 本轮红验非 mutmut 链路, 读该坑时把「写侧污染」只关联到 mutmut dump 场景, 没迁移到「LF 约定仓库 + 临时脚本」场景)。另: 脚本把基线复跑放在 finally 还原之前, 误报一次假红(逻辑坑, 非行尾)。

**滚动面**: 计划 HTML 就地更新(doc-updated=26-10-16-0815, 状态行 S0–S1, §04 R0 增 S1 行) · 本档案 R2 · activeContext 切片 R2 · 基线切片 `baselines/26-10-16-0815-global-traffic-monitor-s1.md`(根 test.full 3413 passed + 4 skipped / 99%, 与 S0 切片逐位一致) · kb.index 重建。未提交(待用户「提交」指令)。

**行号基准**: S1 为纯新目录内文件, 与计划基准 3ba069d7 无关; S6/S7 触碰 auto-qb 前按计划脚注逐条复核漂移。


### R3 · S2 实施 (2026-10-16 08:55)

用户指令「实施计划S2:26-10-16-0541-plan-global-traffic-monitor.html」= 对 S2 的显式授权(S3–S10 不动)。开工同步至 b688437c。

**落点**(改 4 文件 + 1 新文件, 零 auto-qb 触碰): `src/gtm/storage.py` 占位 -> 全量实现(~430 行: atomic_write_text 原子写单点[同目录 tmp+fsync+os.replace, Windows 读者持句柄 WinError 5/32 退避重试 5×50ms]/DatStore[TM 兼容 lines 头+新日在前+KB 向下取整+坏行跳过+加载保留既有日]/StateStore[每次采样必写, 缺失/坏/非对象 -> None]/FlushPolicy[Δ≥1MiB 或 ≥30s, 首帧必落盘, 跨天 reset 新日基线]/SingleInstanceLock[filelock 0 超时+meta 持有者 PID, fail-fast]/Storage 编排[record: 跨天封存旧日 -> upsert -> dat 节流 -> state 必写; recover: state 权威、缺失/损坏/降级 -> dat 兜底; dat_text 内存活尾]) + `__main__.py` run 子命令(--data-dir + default_data_dir 三平台路径策略, acquire_lock fail-fast, recover, 采样-落盘循环, 单轮失败 ERROR 可见下一轮重试不杀守护进程, Ctrl+C 优雅退出最终落盘+释放锁) + `sampler.py` _DAT_ROW_RE -> 公共 DAT_ROW_RE(dat 行格式工具内单点, 读写两侧共用防漂移) + `tests/test_storage.py` 新文件 27 条守阵 + `tests/test_smoke.py` CLI 默认行为断言更新。

**出口判据全过**: ①工具 60/60(4 冒烟 + 29 S1 + 27 S2, 含并发读守阵双形态[线程 + 子进程握手]与 curves.py 真解析器 oracle[importlib 加载, bad==0 值逐日一致]); ②红验 6 条单行锚点突变(原子写失效/replace 重试失效/节流阈值失效/state 不写/锁不竞争[锚点取唯一上下文行偏移, 形态三: self._lock.acquire() 两处出现]/dat 加载丢失)全部判红, 字节恒等还原后复绿(临时脚本 bytes 层, 形态一/十); ③真机冒烟(Windows 临时 data_dir): 第二实例 fail-fast 含持有者 PID/启动时间; taskkill /F kill -9 后重启 state 快照恢复(累计+计数器基线双恢复); dat 首帧落盘值与会话流量逐项吻合。

**实施期坑**: `pitfalls/backend/platform-fs.md` 新增两节 —— ①Windows os.replace 遇读者持句柄的双向瞬时 PermissionError(写侧重试/读侧重试打开, 看不到内容 ≠ 半截内容); ②Git Bash 环境事实($! 是 MSYS pid 不是 Windows pid; grep -c $'\r' 可能退化计数, 行尾事实用 python bytes 层)。冒烟 harness 两轮才跑通: 首轮 Bash 调用间 shell 状态不保持($! 丢失)+pgrep 不存在; 次轮 $! 是 MSYS pid —— 均 harness 问题非工具缺陷, 用 fail-fast 消息提取 Windows pid 解决。

**滚动面**: 计划 HTML 就地更新(doc-updated=26-10-16-0855, 状态行 S0–S2, §04 R0 增 S2 行) · 本档案 R3 · activeContext 切片 R3 · 工具 README/__init__ 进度注记 · pitfalls/backend/platform-fs.md 新增两节 · pitfalls/testing/redverify-anchor-lineendings.md 复发+1(形态三第二例: self._lock.acquire() 两函数重复被 count!=1 兜底) · kb.index 重建 · 基线切片 `baselines/26-10-16-0855-global-traffic-monitor-s2.md`。随用户「提交」指令一并入库。

**行号基准**: S2 为纯新目录内文件, 与计划基准 3ba069d7 无关; S6/S7 触碰 auto-qb 前按计划脚注逐条复核漂移。
### R4 · S3 实施 (2026-10-16 09:46)

用户指令「继续S3」= 对 S3 的显式授权(S4–S10 不动)。开工同步 9d9ec930(S2 提交已推送)。

**落点**(改 4 文件 + 2 新文件 + 1 依赖, 零 auto-qb 触碰): `config.py` 占位 -> 全量实现(~240 行) + `server.py` 占位 -> 全量实现(~360 行) + `storage.py` S3 扩展(~+160 行) + `__main__.py` _run_loop 抽出可测循环 + cmd_run 接线 + `pyproject.toml` 依赖 +pyyaml 6.0.3(与主仓同版本) + `tests/test_config.py` 新文件 17 条 + `tests/test_server.py` 新文件 21 条 + `tests/test_storage.py` +2 条 + README/`__init__` 进度注记与控制面端点表。设计要点: 鉴权 Bearer token(monitor.token 启动即原子生成 urlsafe(32), compare_digest 比对, 缺/错 401); 控制面 ThreadingHTTPServer 强制 127.0.0.1(Windows 关抢占式 allow_reuse_address 才 fail-fast, POSIX 保留 True 绕 TIME_WAIT); 端点 GET /status(采样状态/当日累计/末事件号/订阅者数/路径/配置回显/uptime) / PUT /config(全量聚合校验 -> 原子写 config.yml -> ConfigHolder 热重载 last-writer-wins) / subscribe+heartbeat+unsubscribe(租约 last_heartbeat+lease_ttl 默认 180s 懒剔除, 请求体上限 1MiB); state.json 载荷并入 subscribers+last_event_id, RLock 串行化采样线程与 HTTP 线程的读-改-写(每次写盘为「最近快照+注册表+事件号」完整镜像); 配置热生效范围: sample_interval/适配器过滤/flush 参数即时, http host/port 需重启(文档注明)。

**出口判据全过**: ①鉴权拒绝(无 token/错 token 401)单测 + 写端点同闸; ②租约剔除单测(注入 now: 超租约剔除/未超保留; HTTP 层拨钟后 /status 计数 1->0); ③端口冲突 fail-fast 实测(Windows: 第二实例绑定即 WinError 10048, `gtm: 控制面启动失败 (端口 8099 被占用?)` exit 1); ④config 热重载不丢采样(真 _run_loop + 并发 PUT /config 集成: 改 sample_interval 与 adapter_exclude 后循环线程存活、采样帧数持续增长)。工具 98/98(4 冒烟 + 29 S1 + 27 S2 + 17 S3 配置 + 21 S3 控制面, 全 hermetic: tmp_path + 端口 0 + 注入计数器); 红验 6 条单行锚点突变(鉴权绕过/租约不剔除/未知键不拒/心跳未知 id 放行/热重载失效/注册表丢失)全判红, 字节恒等还原后复绿; 根 test.full 回归数字与前序切片逐位一致(见基线切片)。真机冒烟(Windows 临时 data_dir, 全程后清理): 首启 monitor.token 原子生成(43 字符) -> 带 token /status 全字段 -> subscribe(id + lease 180s) -> PUT /config 热重载(5.0->2.0 即时 + config.yml 落盘) -> kill -9 重启: state 快照恢复 + 注册表续存(subscriber_count 1) + 配置跨重启保留。

**实施期坑(两处真缺陷, 均由测试/冒烟暴露已修)**: ①**热重载静默杀循环** —— AdapterFilter 收单正则串(include/exclude: Optional[str]), config 的模式列表误传 list 致 `re.compile(list)` TypeError, _run_loop 线程猝死(正是出口判据「不丢采样」要防的形态, 首版测试只验帧数增长没验线程存活才漏); 修为模式列表 `|` 并入单正则 + 非法正则在 config 校验层聚合拒绝(黄金法则 4) + 过滤器重建进 try(纵深防御) + 测试加 loop.is_alive() 断言。②**token 惰性生成鸡生蛋** —— 首版只在首个带凭证请求触发生成, 而订阅方(WebUI)需先读文件才能带凭证; 真机冒烟暴露(全部 401, token 文件不存在), 修为 start 即生成/加载 + 补守阵。坑档: `pitfalls/testing/redverify-anchor-lineendings.md` 复发+1 + 形态十一(红验脚本解释器漂移致假红: 临时脚本用 sys.executable=系统 python 无 pytest -> rc!=0 被按「守阵杀变异」判 KILLED, 首跑 6/6 全假红, 基线复跑假红才暴露; 处置=钉死目标 venv 解释器绝对路径 + 突变循环前先跑无变异基线)。另: 本轮**知识库文档回写**又踩形态十(Windows 上 python `write_text()` 把 5 个改动文件静默转 CRLF, HEAD 里全是纯 LF), 提交前 `git status` 全量 bytes 复查发现并 bytes 层修回 —— 该坑已补注「KB 回写同样适用, 一律 read_bytes/write_bytes」。根 test.full 回归数字见基线切片 `baselines/26-10-16-0946-global-traffic-monitor-s3.md`。

**滚动面**: 计划 HTML 就地更新(doc-updated=26-10-16-0946, 状态行 S0–S3, §04 R0 增 S3 行) · 本档案 R4 · activeContext 切片 R4 · 工具 README/__init__ 进度注记与控制面端点表 · pitfalls/testing/redverify-anchor-lineendings.md 复发+1(形态三第二例) + 形态十一 · kb.index 重建 · 基线切片 `baselines/26-10-16-0946-global-traffic-monitor-s3.md`。未提交(待用户「提交」指令)。

**行号基准**: S3 为纯新目录内文件, 与计划基准 3ba069d7 无关; S6/S7 触碰 auto-qb 前按计划脚注逐条复核漂移。


### R5 · S4 实施 (2026-10-16 10:16)

用户指令「实施计划S4:26-10-16-0541-plan-global-traffic-monitor.html」= 对 S4 的显式授权(S5–S10 不动)。开工同步 a3ec82ef(快进)。

**落点**(改 3 文件 + 1 新文件, 零 auto-qb 触碰): `notifier.py` 占位 -> 全量实现(~230 行: `Notifier` 阈值累计 + catch_up 补发 + 守护线程派发[每订阅者一线程, 在途上限 32] + `http_push` 生产推送单点 + `close`/`wait_idle`) + `storage.py` `bump_event_id`(事件号 +1 且落盘) + `__main__.py` `_run_loop` 接通知(首帧 catch_up; 派发抛错保持待补发下一轮重试) + cmd_run 接线(启动日志含通知阈值, 退出时 `notifier.close`) + `tests/test_notifier.py` 新文件 24 条守阵 + 工具 README(新增「通知 (S4)」节)/`__init__` 进度注记。

**设计要点**: 阈值累计基数 = **上次事件时刻**的当日合计, 只在派发成功后推进(随样本推进会把「累计变化」退化成单样本 delta —— 首版即踩, 单测立刻暴露已修); 跨天/累计回退只重置基数不产伪事件; `catch_up` 首帧补发不看阈值(事件号接续, 不从 1 重来); 推送顺序 = 先落盘(dat 节流窗口内活尾即时封口)→ 事件号 +1 落盘 → 派发; 派发在独立守护线程且每订阅者一线程(假死端点既不拖慢采样循环也不拖慢其它订阅者), 失败只记 WARNING 不重试(慢轮询兜底); `http_push` = stdlib urllib POST JSON + Bearer 鉴权头(凭据取订阅时登记的订阅方凭证); 事件体严格六键 {event_id, day, up_bytes, down_bytes, total_bytes, ts}。

**出口判据全过**: ①阈值触发/启动补发/重复投递去重单测(六字段事件体 / 事件号单调且持久化 / 同累计窗口不重发 / 跨天不产伪事件 / 阈值热重载 / 事件号重启接续); ②两订阅者(含假死端点)推送不阻塞采样循环 —— 单测真 `_run_loop` 10s 压测(帧数下界 60 断言通过) + 真机 12s 窗口实测 193 帧(16.1/s) 而假死推送每次占满 3s 超时; 工具 122/122(98 + 24); 红验 7 条锚点突变全判 RED(阈值失效 / 跨天不重置基数 / 事件号不落盘 / 鉴权头写错 / 派发同步化[守阵挂起, 按未绿计] / 推送前不落盘 / 通知前不剔除租约), 字节恒等还原后基线复绿; 真机冒烟: 真 HTTP 订阅者收到事件且 Bearer token 与 monitor.token 一致、假死端点(accept 不回包)只出 WARNING 不阻断、kill -9 重启事件号 5->6(首帧补发)->7 且订阅者续存 2。

**实施期发现**: ①阈值基数推进纪律(实现缺陷, 单测暴露已修); ②红验 M2 未判红 —— 跨天用例首版选「前日合计 > 新日首样本」形态, 被 `total < _last_total` 回退检查替 `day_rolled` 兜底, 突变逃过守阵; 改选「前日合计 < 新日首样本」后判红(坑档 red-verify-must-hit-behavior 新增形态「兜底分支掩盖」); ③`PUT /config` 全量覆盖语义冒烟实锤(只发要改的键会把其余键静默打回默认值 —— sample_interval 0.05 -> 5), S6 设置页「读后写」是硬要求。坑: `pitfalls/testing/redverify-anchor-lineendings.md` 复发+1 + 形态十二(设了子进程超时却没接住 `TimeoutExpired` -> 脚本崩在突变循环中途、收尾基线复跑被跳过)。

**滚动面**: 计划 HTML 就地更新(doc-updated=26-10-16-1016, 状态行 S0–S4, §04 R0 增 S4 行) · 本档案 R5 · activeContext 切片 R5 · 工具 README/`__init__` 进度注记 · pitfalls/testing/redverify-anchor-lineendings.md 复发+1 + 形态十二 · pitfalls/testing/red-verify-must-hit-behavior.md 新增形态 · kb.index 重建 · 基线切片 `baselines/26-10-16-1016-global-traffic-monitor-s4.md`。未提交(待用户「提交」指令)。

**行号基准**: S4 为纯新目录内文件, 与计划基准 3ba069d7 无关; S6/S7 触碰 auto-qb 前按计划脚注逐条复核漂移。

**另(用户 26-10-16-1029 指令「直接修复文档缺陷, 然后提交」)**: 计划 §05 参数表末尾混入 S3 实施记录行(S3 行本应落在 §04 R0 表)—— 计划外文档缺陷已搬回 §04 R0(行序 S0/S1/S2/S3/S4), §05 恢复为纯参数表, 脚注相应改写, doc-updated 抬至 26-10-16-1029。搬移走 bytes 层脚本(先断言 LF 约定未破 + 块唯一, 搬后校验 §05 段内无 S3 行)。


### R6 · S5 实施 (2026-10-16 11:09)

用户指令「实施计划S5:26-10-16-0541-plan-global-traffic-monitor.html」= 对 S5 的显式授权(S6–S10 不动)。开工同步 5654b778(快进)。

**落点**(改 3 文件 + 1 新文件, 零 auto-qb 触碰): `src/gtm/installer.py` 占位 -> 全量实现(~460 行) + `src/gtm/__main__.py` 两子命令 + `cmd_autostart` + `tests/test_installer.py` 新文件 44 条守阵 + README「自启 (S5)」节 + `__init__`/`__main__` 进度注记。

**设计要点**: ①注册项 = 一条 `gtm run --data-dir <DIR>` 守护命令, 解释器取 `sys.executable`(调用本命令的那个 python 按定义就是装了 gtm 的 venv, 不猜路径不靠 PATH), data_dir 解析绝对路径**写死**进注册项(登录会话里 `GTM_DATA_DIR` 不可控)。②三后端: `WindowsTaskBackend`(`schtasks /Create /TN gtm-autostart /SC ONLOGON /TR "<python>" -m gtm run --data-dir "<dir>"`, 当前用户、默认 LeastPrivilege) / `SystemdUserBackend`(`~/.config/systemd/user/gtm.service` 生成物, `ExecStart` 逐段引号, `Restart=on-failure`; daemon-reload + `enable --now`) / `LaunchdBackend`(stdlib `plistlib` 生成 plist, `ProgramArguments` = 守护 argv, `RunAtLoad`+`KeepAlive`; `bootstrap gui/<uid>`)。③**幂等判据严格化**(计划原文「存在则跳过」-> 期望态判据): Windows 只看 `schtasks /Query` 退出码(输出本地化, 不解析); Linux/macOS 看**文件内容一致 且 已启用/已加载**, 未达成则收敛(漂移重写 / 被 disable 重新 enable)。只查「文件存在」会把「单元文件在但服务被 disable」误判成已注册 —— 守阵 `test_linux_register_reenables_when_disabled` 专钉此分支。④`Runner` 依赖注入承载平台命令层(生产路径 `default_runner` = subprocess 收字节 + `_decode` 兜底链 UTF-8 -> 本地码页 -> replace, **只信退出码不解析本地化输出** —— 坑档 console-encoding 那条「表头本地化 -> 读数静默为 0」)。⑤CLI 退出码 0 达成期望态 / 1 平台命令失败或前置条件缺失 / 2 平台不支持(供 S6 设置页开关判成败); `uninstall-autostart` 不带 `--data-dir`(注册项按固定名定位, 卸载不读它 —— 不做「为对称而对称」的参数面)。

**出口判据全过**: ①三平台注册/卸载/重复注册幂等 44/44(工具 166/166 = 122 + 44); ②红验 7 条锚点突变全判 RED —— 幂等跳过失效(`if self.is_registered():` -> `if False:`) / 平台探测恒真(`startswith("win")` -> `True`) / 命令构造(`ONLOGON` -> `ONSTART`) / 卸载反向失效(未注册也发 `/Delete`) / Linux 判据退化(`if same and self._is_enabled():` -> `if same:`) / macOS plist 内容(`KeepAlive` True -> False) / CLI 退出码(`return 2` -> `return 1`), 字节恒等还原后 44 passed 复绿(脚本 `H:/Temp/gtm-s5-redverify.py`: 全程 bytes 层、锚点 count==1 兜底、解释器钉死 venv 绝对路径、突变前先跑无变异基线、子进程 90s 超时且接住 `TimeoutExpired`、apply 后 `ast.parse` 自检、收尾先还原再复跑)。③真机冒烟(Windows, 见下)全 PASS。

**真机冒烟(降级形态 —— 环境拦截)**: 本会话命令安全策略把 `schtasks.exe` 列入 Program Blacklist(报错第一层是 `PermissionError: [WinError 5]` 落在 `CreateProcess` 上, 真判据是 stderr 的 `PROGRAM BLOCKED BY SECURITY POLICY ... cannot be approved or bypassed`, 且明令禁止换壳重试)⇒ **计划任务真注册 + 登录自起这一段真机未跑**。改为验证「除 schtasks 调用之外」的全部真机事实(脚本 `H:/Temp/gtm-s5-smoke.py`, 临时 data_dir + 空闲端口, 全程后清理): ①`build_installer` 真路径给出注册项(平台=windows / 任务名 gtm-autostart / 解释器=工具 venv python)与 TR 字符串; ②该 TR 字符串经 `cmd.exe` 真跑(等价计划任务拉起命令行解析)-> `monitor.token` 生成 -> `GET /status` 200 且可解析、回显 dat 路径落在临时目录、`history_traffic.dat` + `state.json` 落盘; ③无 token 请求 401; ④`taskkill` 按锁 meta PID 停进程后端口释放、临时目录清理 —— 全部 PASS。缺口明写进计划 §04 S5 行与基线切片, **不静默当验过**; 解锁路径 = 用户从 Security Center -> Command Security -> Program Blacklist 移除该项后重跑, 或用户在自己终端手动跑 `gtm install-autostart`(用户终端不经本会话策略)。新坑档 `pitfalls/ops/session-program-blacklist.md`(含「WinError 5 双重误导」判别: 有 `PROGRAM BLOCKED` 行 = 策略拦截, 无则回 `platform-fs.md` 的原子写/句柄族)。

**顺序注记**: 计划 §06 记「S5(自启)依赖 S6 的开关入口」; 本轮按用户显式授权先落 S5 —— 命令面独立可用、真机可跑, S6 落地后由设置页开关消费它, 不构成依赖倒挂。

**滚动面**: 计划 HTML 就地更新(doc-updated=26-10-16-1109, 状态行 S0–S5, §04 R0 增 S5 行, 脚注补 S5 与降级冒烟说明) · 本档案 R6 · activeContext 切片 R6 · 工具 README「自启 (S5)」节 / `__init__` 进度注记 · 新坑档 `pitfalls/ops/session-program-blacklist.md` + `kb.index` 重建 · 基线切片 `baselines/26-10-16-1109-global-traffic-monitor-s5.md`。未提交(待用户「提交」指令)。

**行号基准**: S5 为纯新目录内文件(工具包), 与计划基准 3ba069d7 无关; S6/S7 触碰 auto-qb 前按计划脚注逐条复核漂移。



### R7 · S6 实施 (2026-10-16 11:45)

用户指令「实施计划S6:26-10-16-0541-plan-global-traffic-monitor.html」= 对 S6 的显式授权(S7–S10 不动)。开工同步 3473aa9a(快进)。**首个触碰 auto-qb 的步骤**。

**计划改版(用户拍板, 计划 HTML 同文件内记录)**: S6 原文「自启开关幂等调 `gtm install-autostart`」未定调用路径 —— auto-qb 与工具是两个 venv, auto-qb 无法定位该 CLI(计划 6 键里也无解释器/命令路径键)。向用户提出 A(新增 tool_command 键)/B(工具控制面加端点)/C(本轮不做自启开关)三案, 用户取 **B 案**: 工具控制面新增 `POST /autostart`, auto-qb 经 HTTP 代理调用 —— 与「auto-qb 只经控制面与工具通信」的架构一致。S6 范围因此含一处工具包改动(原表述仅「auto-qb 配置面」)。

**落点**(4 处): ①**配置段 4 点同步**(黄金法则 4): `models.py` `GlobalTrafficMonitorConfig`(enabled/tool_url/tool_token_path/subscribe/notify_cooldown_s/autostart)+ `Config` 字段; `loaders.py` `load_global_traffic_monitor_config` + 接线; `validation`(`KNOWN_CONFIG_KEYS` + `KNOWN_GLOBAL_TRAFFIC_MONITOR_KEYS` + `_validate_global_traffic_monitor`/`_validate_tool_url`: 未知键/bool/tool_url 形状/冷却 0S~24H 聚合校验); `schema/groups.py` 新分组「全局流量监视器」(i-traffic, 排「流量图」之后)。②**工具控制面** `POST /autostart`(`{action: install|uninstall}`; 200 达成期望态含 no-op / 501 平台不支持 / 500 命令失败 / 400 载荷非法; data_dir 取进程自身**不信任请求体**; 注入式 `installer_factory` 供 hermetic 测试)。③**auto-qb 代理路由**(新 `routes/traffic_monitor.py` + 注册进 `ROUTE_BUILDERS` + 金清单): `GET /api/traffic/monitor/status`(展示端点, 恒 200 + 结构化空态 reachable/error) / `PUT .../config`(写端点: 工具 400 逐条透传, 不可达/5xx 收口 502) / `POST .../autostart`(501 透传); token 解析单点(显式 tool_token_path 优先, 否则镜像工具平台默认数据目录; 平台判定走 `utils.is_windows/is_mac` 单点)。④**设置页新分区**(schema 分组自动出卡 + `settings.html` 链尾 `v-else-if` 分支): 联动键走 `hub-field`(与通用表单同源), 工具状态/参数表单/自启开关经代理; 参数表单**读后写**(工具 PUT /config 全量覆盖)。

**出口判据全过**: ①新配置键过 `test_config_schema`(顶层 + 对象段键集合)+ `test_config_key_surface`(键面基线 160→167 + 6 条 loader 回读探针 + keys.md 出处)守卫; ②设置页读写工具参数(以代理路由守阵钉契约, 端到端可见性待 S7 联调复核); ③未知键仍被拒。工具 173/173; 新增守阵 `tests/test_config_traffic_monitor.py`(12 条)+ `tests/test_web_traffic_monitor.py`(15 条); 红验 7 条锚点突变全判 RED(键集合漂移 / 段校验未接线 / loader 漏读 / schema 键名漂移 / status 缺 token 不报错 / PUT 代理路径漂移 / 工具 action 闸失效), 字节恒等还原后基线复绿(脚本 `H:/Temp/gtm-s6-redverify.py`)。

**实施期发现(3)**: ①`utils.parse_time` 只认带单位串("0" 非法, "0S" 合法) —— 冷却键「0 = 不冷却」YAML 里须写 `0S`, 已同步 keys.md/schema help(写测试时暴露)。②前端 `v-if/v-else-if` 链**跨分片延续**(settings.html → settings-detail.html): 新分区只能作 `v-else-if` 插在**链尾**(settings.html 内), 插分片边界会断链(后续 v-else-if 静默失配)、插链尾之后会落 `</main>` 外(`hub.view` 持久化 → 非设置页也渲染); settings.html 加分区后 392/400 行, 下次加内容前须先拆视图分片。已记坑档 `pitfalls/web-ui/frontend-split.md`(新条目)。③**四处结构性守阵首跑全量时判红**(均为「新增配置段/路由/前端 POST 点必须同步登记」的既有网): 平台判定单点(`sys.platform.startswith` 旁路 → 改 `utils.is_windows/is_mac`)、段认领完整性(`WebUIModule.sections()` 加 `global_traffic_monitor`)、schema 端点分组序(`test_config_schema_endpoint` 期望表加新分组)、前端 POST 触发点登记(`triggers.js` calls 加 `config_hub.js::tmAutostart`)。坑: `pitfalls/testing/single-file-coverage-gate.md` 复发+1(红验 harness 裸跑单文件被覆盖率闸假红 —— 未命中原因: 照抄 S5 脚本只搬了「钉死解释器/字节层」, 漏了「单文件跑必须绕覆盖率闸」; 处置 = auto-qb 侧加 `--no-cov -n 0`)。

**滚动面**: 计划 HTML 就地更新(doc-updated=26-10-16-1145, 状态行 S0–S6, §04 R0 增 S6 行 + 改版记录, 脚注补 S6 与 /autostart 改版) · 本档案 R7 + 子任务表 S6→Done · activeContext 切片 R7 · `memory-bank/config-reference/keys.md` 新段 · 工具 README 端点表 · 坑档 `pitfalls/testing/single-file-coverage-gate.md` 复发+1 + `pitfalls/web-ui/frontend-split.md` 新增条目 · kb.index 重建 · 基线切片 `baselines/26-10-16-1145-global-traffic-monitor-s6.md`。未提交(待用户「提交」指令)。

**行号基准**: S6 首次触碰 auto-qb —— 配置四处(models/loaders/validation/schema)+ 路由注册表 + 设置页模板逐条复核, 未发现漂移。S7(接收面)仍按计划脚注逐条复核。

### R8 · S7 实施 (2026-10-16 14:04)

用户指令「实施S7:26-10-16-0541-plan-global-traffic-monitor.html」= 对 S7 的显式授权(S8–S10 不动)。开工同步 16d66653→fd26c4e7(快进)。

**落点**(改 7 文件 + 3 新文件 + 3 文档, 含 1 处接收面新组件): `webui/server/routes/traffic_monitor.py`(通知接收面端点 + 事件号/冷却双闸 + 六键事件体校验) · `webui/tool_client.py` **新文件**(控制面客户端上移为共享件 —— S6 守阵的打桩点逐字不变 + 订阅客户端 `TrafficMonitorSubscriber`) · `webui/module.py`(订阅生命周期三时刻接线) · `webui/commands.py`(`refresh_traffic` 命令) · `core/modules/speed_curve_mod.py`(数据源读法单点 `_read_source_rows` + 只读刷新入口 `refresh_traffic_view`) · `webui/static/shared/dialogs.js`(历史弹层开着时快照 ts 变化即重拉) · `tests/test_traffic_monitor_client.py`(新, 15 条)+ `tests/test_web_traffic_monitor_notify.py`(新, 8 条)。

**设计要点**: 「刷新图」是通知链路的唯一联动动作(不查档、不读不写 qB 限速); 订阅注册 / 心跳 / 注销的**全部控制面 I/O 只在订阅线程**, 主循环侧只置期望态并唤醒(主循环不会因工具假死卡在超时上); 期望态每轮现读配置(热重载即时生效, 不引入跨线程状态传递); 接收闸状态 per app 实例(与 auth 的「只记一次」同款); 端点响应语义按「对话方是工具进程」定: 闸门拦下 / 联动未启用一律 200 + action, 只有事件体非法才 400(工具侧把非 2xx 记成推送失败, 闸门拦下的通知不该伪装成故障)。

**出口判据(单测面全过)**: 23 条新守阵全绿, 其中端到端(进程内)一条打通「真端点 → 命令队列 → 真 handler → 真模块重发快照 → /api/state 与 /api/traffic/history 两取数位」; **红验 6 条锚点突变全判 RED**(事件号去重失效 / 冷却窗口失效 / 曲线未启用也刷新 / 期望态整体退回真值判 / 订阅载荷丢回调凭证 / 命令表漏注册), 字节恒等还原后基线复绿。**未闭合项**: 出口原文的真机联调(真工具进程 → 浏览器看历史图/顶栏刷新)留待 S10 或工具在跑时补; 本轮以进程内端到端钉住同一条链路。

**实施期发现(4)**: ①注销寻址必须用注册时的「工具地址 + 密钥路径」—— 首版按现读配置寻址, 单测第一轮即暴露(配置一改就注销到新地址、拿不到密钥, 订阅留在旧工具上直到租约过期)。②期望态三开关改按**恒等 True** 判: 热重载守阵用 MagicMock 当新配置, 真值判会让桩段被当成「已启用且要订阅」而真起一条常驻订阅线程(实测污染后续用例的线程清点; 同族形态 pitfalls/testing/hot-reload-mock-sections.md)。③`stop()` 超时后**不摘线程引用**: 摘了就没人能 join, 而下一次 sync() 会因「看不到线程」再起一条 = 双订阅。④写入判据连带拦下四处**既有**文件(测试夹具 / 路由金清单 / 计划 HTML / 本档案): 因历史内容里的鉴权字样被判整文件拒写, agent 侧 edit/apply_patch/write 三条路径全拒; 用户拍板取「形态等价改写命中行 + agent 自己写回」(改写仅形态、行为零变化), 并把「范围比代码文件大得多 + 处置优先级」补进坑档 `pitfalls/ops/agent-write-guard-secret-false-positive.md`。

**滚动面**: 计划 HTML 就地更新(doc-updated=26-10-16-1404, 状态行 S0–S7, §04 R0 增 S7 行, 脚注补 S7)· 本档案 R8 · 坑档 `agent-write-guard-secret-false-positive.md` 扩写 · activeContext 切片 R8 · 基线切片 `baselines/26-10-16-1404-global-traffic-monitor-s7.md`。未提交(待用户「提交」指令)。

### R9 · S8 实施 (2026-10-16 17:37)

用户指令「实施S8:26-10-16-0541-plan-global-traffic-monitor.html」= 对 S8 的显式授权(S9–S10 不动)。开工同步 22f0dad8→1ae16235(快进)。**纯文档轮**(零代码/配置/数据改动)。

**落点**(改 3 个文档): ① `docs/configuration.md` 新增「全局流量监视器工具（gtm）」段 —— 定位与边界(唯一写者 / 整机口径 / 只刷新图不参与限速 / 多实例订阅)· 安装运行与三平台数据目录(默认路径表 + 目录内文件用途)· 工具参数表(含配置写入的全量覆盖语义)· 三平台自启(注册项表 + 幂等判据 + 退出码 0/1/2)· auto-qb 侧 6 键联动配置(含两条易踩: enabled 与 dat_path 独立; 曲线未启用时通知只记 INFO 不刷新)· **迁移检查单**(9 步 + 回退路径)· **并行对照(24h, E1)方法**(口径差异先排除 / 容差 ≤5% / 可执行对照脚本)· **双写者禁令**; 另在文档摘要行与「流量数据来源: Traffic Monitor」小节各补一处交叉指针。② `memory-bank/config-reference/keys.md` 的 `global_traffic_monitor` 段补「过渡与迁移」注记。③ 根 `README.md` 配置参考清单补一行条目。

**出口判据**: ① 文档与 schema 一致 —— `test_config_schema`(docs↔代码漂移守卫) + `test_config_key_surface`(键面 + keys.md 反引号出处) + `test_docs_forms` 快跑全绿; `doc.links` / `doc.drift`(无手抄) / `doc.caps` 全过。② 迁移检查单可执行 —— 已实跑其可跑部分(见下)。③ 对照脚本从文档原文抽出即可执行且判读有效。

**沙箱实跑**(临时数据目录, 全程后清理, 零触碰生产文件): ① 工具 venv `uv sync`(本 clone 此前未建 venv, 顺带验证检查单第 1 步) → `gtm --version` = `gtm 0.1.0`; ② 前台 `gtm run --data-dir <tmp>` 45s: `history_traffic.dat`(`lines: "1"` + 当日行 `2026/10/16 2115/5530` KB; 首帧 0/0 → 30s 时间面节流刷新)/ `state.json`(当日累计 up 2,166,638 / down 5,663,252 B, 每帧推进)/ `monitor.token`(43 字符)/ `gtm.lock`(+ 伴生 meta) 齐备; ③ 控制面: 无凭据 `GET /status` → 401, 带凭据 → 200(payload 含 day / day_up_bytes / day_down_bytes / day_total_bytes / last_event_id / subscriber_count / paths{dat,state,config,token} / config / uptime_s); ④ 对照脚本: **从 `docs/configuration.md` 正则抽出代码块原文**执行, 合成 TM 侧(up +3%+100KB / down -2%+100KB)与工具侧真 dat 比较 → `2026-10-16 CHECK up 2.2 vs 2.1 MiB (7.16%) | down 5.4 vs 5.4 MiB (0.20%)`(单侧超 5% 给 CHECK, 判读符合设计); ⑤ terminate 后端口释放、临时目录清理。

**未闭合项(诚实标注)**: S8 出口原文的 **24h 并行对照(差异 ≤ 容差, E1)** 本会话无法完成 —— 需真实 Traffic Monitor 与 24h 挂机(本环境连 TM 数据目录所在盘都不存在); 本轮交付 = 方法(口径差异先排除 + 容差口径)与已实跑验证的对照脚本, 实测数字留 S10 真机验收。检查单第 3 步的 schtasks 自启注册仍受本会话命令安全策略拦截(S5 同一缺口, 解锁路径见坑档); 第 5—8 步涉及真机 auto-qb 与浏览器, 留 S10。

**实施期发现(写入判据整文件拦下 3 个文档文件)**: `docs/configuration.md` / 根 `README.md` / `config-reference/keys.md` 被工作区写入判据**整文件**拒写(命中既有示例占位行 5 处: 口令键旁尖括号占位 ×2、传令牌键旁空串字面量 ×3; 与本次改动无关, 值均为占位符)。按坑档口径不绕过 —— 先做「整文件级探针」(三文件整份拷进 `.openclaw/tmp/` 再在拷贝上改候选形态, 一次判定「改哪几行即可恢复可写」), 再向属主报告; **属主授权形态等价改写**后落 5 行(尖括号占位 → 括号占位 / 空串字面量 → 括号占位), 语义零变化; 写回后 `git diff` 恰为预期 5 行、LF 行尾字节无损(与 HEAD 逐文件对照 crlf=0)。坑档 `pitfalls/ops/agent-write-guard-secret-false-positive.md` 复发 +1 并补「整文件级探针」手法与文档类影响面。

**滚动面**: 计划 HTML 就地更新(doc-updated=26-10-16-1737, 状态行 S0–S8, §04 R0 增 S8 行, 脚注补 S8; 改后跑 HTMLParser 标签平衡机检 —— 未闭合 0 / 乱序 0)· 本档案 R9 + 子任务表 S7/S8 → Done · activeContext 切片 R9 · 坑档复发并入 · kb.index 重建 · 基线切片 `baselines/26-10-16-1737-global-traffic-monitor-s8.md`。

**行号基准**: S8 为文档轮, 无代码落点; 计划脚注的 clone 基准(3ba069d7)与 S8 无关。随本专题入库。

### R10 · S9 实施 (2026-10-16 18:24)

用户指令「实施S9:26-10-16-0541-plan-global-traffic-monitor.html」= 对 S9 的显式授权(S10 不动)。开工同步 f8db7019(已是最新, 无 HEAD 改写步骤)。

**范围判定(先逐项核对再动手)**: 按 S9 清单盘点两侧已有守阵 —— 工具侧七类(采样 delta/重置/日界 · 落盘原子性 · 崩溃恢复 · 通知阈值/事件号/补发/假死端点 · 租约 · config 校验 · installer 幂等[平台命令 mock])与 auto-qb 侧三类(配置键 validate/schema 同步 · notify 鉴权+冷却+幂等 · 订阅生命周期)随 S1–S7 已落地; 缺的只有第四项「`dat_path` 指向工具文件时解析兼容」—— 现有夹具是手搭的 TM 文本(auto-qb 侧)与「真写者 × 真 curves.py」oracle(工具侧, 独立部署时跳过), 两侧按同一种错法漂移时两份守阵都保持绿。

**落点**(1 新文件 + 1 既有测试文件 +2 行): ① `tests/test_traffic_monitor_dat.py`(新, 2 条) —— 跨侧契约: 工具真写者 `gtm.storage.DatStore`(load/upsert/flush 原子写)产出的 dat 设为 `dat_path` → 只读刷新 `refresh_traffic_view` 读回(历史行升序 + KB 向下取整后逐日一致 + day/month 累计重算 + 更早月份只进历史), 加格式单点同值断言(两侧 KB 常量 / `lines: "N"` 表头与数据行数 / 新日在前 / 读侧 bad==0)。**写法上的一处结构性选择**: 根测试的副作用守阵(`tests/sidefx.py`)对 POPEN 只放行 node 与临时 wrapper ⇒ 不能起子进程跑工具 venv, 故按源码路径**进程内**加载工具写者(`monkeypatch.syspath_prepend` + 只替 `import psutil` —— 根环境刻意无 psutil 是 S0 的隔离判据, 而写者路径一次不用它; 真被用到会以 AttributeError 立刻变红, 不静默)。② `tests/test_web_traffic_monitor_notify.py` 的 `test_notify_requires_auth` 补「错 Bearer 也 401」(键名走既有拆写常量, 规避写入判据误报)。

**红验(4 条突变, 全判 RED, 字节恒等还原后基线复绿)**: harness `.openclaw/tmp/redverify_s9.py`(未入库) —— 阈值失效(工具 notifier: 5 条红) / 鉴权绕过(auto-qb 接收面: 1 条红) / 单位漂移(工具 KB=1000: 新守阵 2 条红) / 表头漂移(`lines:`→`rows:`: 只打红格式单点那条 —— 与「值断言抓不到表头层」的设计预期一致)。harness 纪律照坑档全形态: bytes 层读写、锚点 count==1 兜底、钉死两侧 venv 解释器绝对路径、突变前先跑无变异基线、捕获 TimeoutExpired、还原后再复跑基线(全程 ALL-RED-AND-GREEN-AFTER-RESTORE)。

**实施期发现(3)**: ① 上述「跨侧守阵不能起子进程」是全局结构约束(副作用守阵只罩根套件, 工具侧套件在它之外才允许子进程); ② 包内 `test.*` 在本 clone 又踩「无 uv on PATH」—— 首跑 `test.full` 即 FAIL(`'uv' is not recognized`), 处置照坑档首选(调用前把 uv 目录前置进 PATH + `TEMP`/`TMP` 指 C 盘临时区), 坑档复发+1; ③ **窄池假存活**: M2「鉴权绕过」在 notify 单文件池里 SURVIVED(该文件只测「没带 Bearer」, 突变打在它未覆盖的比较分支上), 拿全量池复验才定性 —— 被 `tests/test_web_auth.py::test_api_requires_token` 等 3 条杀死; 据此给 notify 守阵补了错密钥分支(补后本池即可判红)。坑档 `pitfalls/testing/mutation-pool-artifact.md` 复发+1。

**出口判据全过**: ① 全量 `test.full` 全绿(覆盖率门槛达成) + 工具套件全绿, 数字见 kb.baseline 与基线切片; ② 红验 4 条突变判红且还原自证; ③ 基线切片只进 `testing/baselines/`。

**未闭合项(诚实标注)**: S10 真机验收(E1–E6)未动 —— 需真机 TM / 工具进程 / 浏览器, 待逐项授权。

**滚动面**: 计划 HTML 就地更新(doc-updated=26-10-16-1824, 状态行 S0–S9, §04 R0 增 S9 行, 脚注补 S9; HTMLParser 机检未闭合 0 / 乱序 0)· 本档案 R10 + 子任务表 S9→Done · activeContext 切片 R10 · 坑档 (no-uv-fallback / mutation-pool-artifact) 复发+1 · kb.index 重建 · 基线切片 `baselines/26-10-16-1824-global-traffic-monitor-s9.md`。随本专题入库。

**行号基准**: S9 无 `src/` 代码落点(纯测试面 + 一处测试文件); 计划脚注的 clone 基准 3ba069d7 与之无关。

- 2026-10-18 19:48 通知链路三级日志(接收面放行/主循环 WEB UI/快照发布)INFO -> DEBUG: 用户报大流量日(事件 #1200)日志刷屏, 拍板「改为DEBUG级」; 消息文本不变, config 触发与两条 WARNING 路径不降; 新增 2 条日志级守阵; test.full 全量绿(数字见基线切片 26-10-18-1947-notify-log-debug, 口径 kb.baseline)

- 2026-10-20 23:49 只读排查 gtm 常驻进程任务管理器「I/O 其它」偏高: 实测 72.42 次/秒(累计 782 万)确认为 psutil 网卡枚举控制操作(每轮 177 次), 读 0 次/秒、写 0.42 次/秒=设计值; 入池 perf issue 26-10-20-2345(Open), 未改码
