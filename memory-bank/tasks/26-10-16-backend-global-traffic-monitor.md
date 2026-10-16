# 26-10-16-backend-global-traffic-monitor — 全局流量监视小工具 (TrafficMonitor 替代)

**Status:** In Progress
**Added:** 2026-10-16
**Updated:** 2026-10-16 10:16
**Summary:** 自写独立整机流量历史记录小工具(TM 替代): 独立进程+开机自启+TM 兼容 dat 原子落盘+阈值变化主动通知多 auto-qb 实例刷新 WebUI 历史图。计划 26-10-16-0541(S0–S10 逐步显式授权); S0 包骨架 + S1 采样器 + S2 落盘 + S3 控制面 + S4 通知已落地。
**Refs:** memory-bank/plans/26-10-16-0541-plan-global-traffic-monitor.html, memory-bank/pitfalls/testing/nested-pytest-config.md, memory-bank/pitfalls/backend/platform-fs.md, memory-bank/pitfalls/testing/redverify-anchor-lineendings.md, memory-bank/pitfalls/testing/red-verify-must-hit-behavior.md, memory-bank/testing/baselines/26-10-16-0601-global-traffic-monitor-s0.md, memory-bank/testing/baselines/26-10-16-0815-global-traffic-monitor-s1.md, memory-bank/testing/baselines/26-10-16-0855-global-traffic-monitor-s2.md, memory-bank/testing/baselines/26-10-16-0946-global-traffic-monitor-s3.md, memory-bank/testing/baselines/26-10-16-1016-global-traffic-monitor-s4.md
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
| S5 | 自启 installer | Open |
| S6 | auto-qb 配置面 | Open |
| S7 | auto-qb 接收面 | Open |
| S8 | 集成与过渡 | Open |
| S9 | 守阵测试 | Open |
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

**设计要点**: 阈值累计基数 = **上次事件时刻**的当日合计, 只在派发成功后推进(随样本推进会把「累计变化」退化成单样本 delta —— 首版即踩, 单测立刻暴露已修); 跨天/累计回退只重置基数不产伪事件; `catch_up` 首帧补发不看阈值(事件号接续, 不从 1 重来); 推送顺序 = 先落盘(dat 节流窗口内活尾即时封口)→ 事件号 +1 落盘 → 派发; 派发在独立守护线程且每订阅者一线程(假死端点既不拖慢采样循环也不拖慢其它订阅者), 失败只记 WARNING 不重试(慢轮询兜底); `http_push` = stdlib urllib POST JSON + `Authorization: Bearer <订阅 token>`; 事件体严格六键 {event_id, day, up_bytes, down_bytes, total_bytes, ts}。

**出口判据全过**: ①阈值触发/启动补发/重复投递去重单测(六字段事件体 / 事件号单调且持久化 / 同累计窗口不重发 / 跨天不产伪事件 / 阈值热重载 / 事件号重启接续); ②两订阅者(含假死端点)推送不阻塞采样循环 —— 单测真 `_run_loop` 10s 压测(帧数下界 60 断言通过) + 真机 12s 窗口实测 193 帧(16.1/s) 而假死推送每次占满 3s 超时; 工具 122/122(98 + 24); 红验 7 条锚点突变全判 RED(阈值失效 / 跨天不重置基数 / 事件号不落盘 / 鉴权头写错 / 派发同步化[守阵挂起, 按未绿计] / 推送前不落盘 / 通知前不剔除租约), 字节恒等还原后基线复绿; 真机冒烟: 真 HTTP 订阅者收到事件且 Bearer token 与 monitor.token 一致、假死端点(accept 不回包)只出 WARNING 不阻断、kill -9 重启事件号 5->6(首帧补发)->7 且订阅者续存 2。

**实施期发现**: ①阈值基数推进纪律(实现缺陷, 单测暴露已修); ②红验 M2 未判红 —— 跨天用例首版选「前日合计 > 新日首样本」形态, 被 `total < _last_total` 回退检查替 `day_rolled` 兜底, 突变逃过守阵; 改选「前日合计 < 新日首样本」后判红(坑档 red-verify-must-hit-behavior 新增形态「兜底分支掩盖」); ③`PUT /config` 全量覆盖语义冒烟实锤(只发要改的键会把其余键静默打回默认值 —— sample_interval 0.05 -> 5), S6 设置页「读后写」是硬要求。坑: `pitfalls/testing/redverify-anchor-lineendings.md` 复发+1 + 形态十二(设了子进程超时却没接住 `TimeoutExpired` -> 脚本崩在突变循环中途、收尾基线复跑被跳过)。

**滚动面**: 计划 HTML 就地更新(doc-updated=26-10-16-1016, 状态行 S0–S4, §04 R0 增 S4 行) · 本档案 R5 · activeContext 切片 R5 · 工具 README/`__init__` 进度注记 · pitfalls/testing/redverify-anchor-lineendings.md 复发+1 + 形态十二 · pitfalls/testing/red-verify-must-hit-behavior.md 新增形态 · kb.index 重建 · 基线切片 `baselines/26-10-16-1016-global-traffic-monitor-s4.md`。未提交(待用户「提交」指令)。

**行号基准**: S4 为纯新目录内文件, 与计划基准 3ba069d7 无关; S6/S7 触碰 auto-qb 前按计划脚注逐条复核漂移。

**另(用户 26-10-16-1029 指令「直接修复文档缺陷, 然后提交」)**: 计划 §05 参数表末尾混入 S3 实施记录行(S3 行本应落在 §04 R0 表)—— 计划外文档缺陷已搬回 §04 R0(行序 S0/S1/S2/S3/S4), §05 恢复为纯参数表, 脚注相应改写, doc-updated 抬至 26-10-16-1029。搬移走 bytes 层脚本(先断言 LF 约定未破 + 块唯一, 搬后校验 §05 段内无 S3 行)。

