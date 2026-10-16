# 26-10-16-0935-atomic-write-replace-retry — Windows 原子写退避重试(主仓单点) + 注册表读侧分档

> 摘要: 用户实报 HR 实例注册表心跳 `PermissionError: [WinError 5] 拒绝访问: 'instances.json.<rand>.tmp' -> 'instances.json'`。定位为**已记坑在主仓的复发** —— `pitfalls/backend/platform-fs.md`「Windows 原子写与并发读者的双向瞬时拒绝」当天(08:55 S2)刚记档, 但处置只落在 gtm 工具内, 主仓单点 `infra/utils.py::atomic_write` 没同步这层重试。修法 = 退避重试沉进 `atomic_write`(所有原子写受益, 含 state.json) + 读侧把「瞬时拒绝」与「内容损坏/空表」分开。
> 最后活动: 2026-10-16 09:35
> 状态: Done

## 本轮落点(代码事实)

- `src/auto_qb/infra/utils.py`: 新增常量 `REPLACE_RETRY_ATTEMPTS = 5` / `REPLACE_RETRY_DELAY_S = 0.05` 与 `_replace_retry`(**只重试 `PermissionError`**, 其它 `OSError` 立即抛, 不白等); `atomic_write` 的末步换名改走它。与 gtm `tools/global-traffic-monitor/src/gtm/storage.py::_replace_retry` 是**两个独立单点、常量必须同值**(工具不 import 主仓)。
- `src/auto_qb/hr/discovery.py`: 新增 `_read_registry_text`(读侧退避重试; 缺文件不重试 —— 那是有语义的稳定态)与 `REGISTRY_READ_ATTEMPTS` / `REGISTRY_READ_RETRY_DELAY_S`; `InstanceRegistry._load` 改返回 `Optional[List]` —— `None` = **读不到**(瞬时拒绝且重试耗尽), `[]` = 真空/缺文件/损坏(容忍口径不变: 坏 JSON 仍 WARNING + 下次心跳写回自愈); `upsert` 遇 `None` 抛 `RuntimeError` **本轮不写**(读不到却写回只含自己的表 = 静默抹掉其它实例条目), 心跳侧容错仍是「下一周期重试」; `alive` 遇 `None` 当空列表。
- `tests/test_utils.py` +3: 重试穿过(2 次被拒后第 3 次落地) / 耗尽后仍抛且旧内容完好 + 临时文件清理 + 次数按单点常量 / 非 `PermissionError` 一次即抛。
- `tests/test_hr_discovery.py` +2: 首次被拒后重试成功(不误判为损坏) / 重试耗尽「读不到 ≠ 空表」(不写回、文件原样、`alive` 当空列表); 新增 `_simulate_read_denial` 夹具(只拦目标文件的 `builtins.open`, `Path.read_text` 与其它路径放行)。两个测试文件头部「测试计划」同步。
- **红验 3 条**(单行锚点突变、还原后字节恒等): ①`_replace_retry(` -> `os.replace(` ⇒ 写侧两条红; ②`range(REGISTRY_READ_ATTEMPTS)` -> `range(1)` ⇒ 读侧两条红; ③`_load` 的 `return None` -> `return []` ⇒ 「读不到 ≠ 空表」红(实测表现为注册表被覆盖成只含自己)。
- 实测数字与全量结果见 `commands run kb.baseline` 最新切片。

## 现场取证(为什么是外部瞬时句柄)

- 全日志仅 1 次(08:39:35,529), 5 个轮转档 0 次; 失败后 `instances.json` 持续刷新(mtime 09:19:36)⇒ 下一周期已自愈。
- 同进程读者不可能自撞: `alive()` 与 `upsert()` 共用同一把 `threading.Lock`, 且全仓唯一 `InstanceRegistry` 构造点在 `hr/runtime.py`(`_build_discovery`); 08:39 前后无热重载/重绑日志。
- 同机无第二个注册表访问者: 另一实例 `auto-qb-long-seeding`(10/13 启动, 早于该特性)只监听 38081、无发现端点; 候选 18789/18790 空闲; 读侧降级告警 0 次。
- ⇒ 持有者是**进程外的瞬时句柄**(杀软 / 索引器 / 另一进程的开-读-关窗口), 与坑档定论一致: 不指认持有者, 处置是退避重试。

## 未改(有意)

心跳失败日志仍是 `logger.error(..., exc_info=True)` —— 本仓 WARNING+ 会推**系统通知**, 但重试落地后这类瞬时事件基本不再浮上来(读者窗口是微秒~毫秒, 5×50ms 足以穿过), 保留 ERROR 让真故障可见; 若后续仍嫌噪音, 降档是与本轮解耦的独立决定。

## 下一步 / 移交

- 真机观察: 若修复生效后仍出现同一 `WinError 5` 行, 说明该窗口 > 250ms(疑杀软长持), 那时应调大次数/间隔, 而不是继续在调用点加代码。
- 立档阈值判定: 2 个源文件 + 2 个测试文件、单会话 2 轮指令 ⇒ **未命中阈值**(≥3 源文件 / ≥5 轮 / 跨会话 / 长周期表述), 按 memory-bank skill 只写本切片, 不建 tasks 档案。
