# 3418 passed + 4 skipped —— 主仓原子写 `os.replace` 退避重试 + HR 注册表读侧分档(新增 5 条守阵)

> 摘要: 用户实报 HR 实例注册表心跳 `PermissionError: [WinError 5]`(坑档 platform-fs「Windows 原子写与并发读者的双向瞬时拒绝」在**主仓**的复发 —— 当天该坑的处置只落在 gtm 工具内)。修法: `infra/utils.py` 新增 `_replace_retry`(仅 PermissionError, 5 次 × 50ms)并被 `atomic_write` 末步采用(所有原子写受益, 含 state.json); `hr/discovery.py` 新增 `_read_registry_text` 读侧退避重试, `_load` 分档为 `None`(读不到)/`[]`(缺失/损坏), `upsert` 遇 `None` 本轮不写(不覆盖别家条目)、`alive` 当空列表。本切片为根 test.full 回归闸门数字, 测在含上述 4 文件改动与文档回写的工作树上。
> 基线时间: 2026-10-16 09:40

**Refs:** memory-bank/pitfalls/backend/platform-fs.md

## 验收数字

- test.full: 3418 passed + 4 skipped / TOTAL 17383 185 5856 159 98%; 耗时 135.34s(单次采样, 口径见 baseline.md)。新增 5 条从根集来: `test_utils` +3 / `test_hr_discovery` +2。
- 红验(单行锚点突变、还原后字节恒等, 3 条全 RED): ①主仓末步 `_replace_retry(` -> `os.replace(` ⇒ 写侧 2 条红(实测 `assert 1 == 5` —— 重试计数); ②`range(REGISTRY_READ_ATTEMPTS)` -> `range(1)` ⇒ 读侧 2 条红(实测日志「读取被瞬时拒绝(退避重试耗尽)」); ③`_load` 的 `return None` -> `return []` ⇒ 「读不到 ≠ 空表」1 条红(表现为注册表被覆盖成只含自己)。
- 定向回归: `commands run test.one -- tests/test_utils.py tests/test_hr_discovery.py` 124 passed(含新增 5 条)7.2s, 副作用台账越界 0; 还原后复跑同样 124 passed。
- 同族未重测: gtm 工具侧(独立 venv, 不在根 testpaths 内)本轮零触碰, 其 `_replace_retry` 未改。
- Linux(WSL)侧未跑 —— 本轮改动含 Windows 专属分支(replace 退避重试; POSIX 上不触发), 本条 Windows 侧数字为事实源。

## 本改动面

- `src/auto_qb/infra/utils.py`: `REPLACE_RETRY_ATTEMPTS = 5` / `REPLACE_RETRY_DELAY_S = 0.05` + `_replace_retry`(只重试 `PermissionError`, 其它 `OSError` 原样抛) + `atomic_write` 末步换名改走它 + docstring 补坑档指针。
- `src/auto_qb/hr/discovery.py`: `REGISTRY_READ_ATTEMPTS` / `REGISTRY_READ_RETRY_DELAY_S` + `_read_registry_text`(缺文件不重试) + `_load` 改返回 `Optional[List]`(`None` = 读不到, `[]` = 缺失/损坏, 后者容忍口径不变) + `upsert` 遇 `None` 抛 RuntimeError 本轮不写 + `alive` 当空列表。
- `tests/test_utils.py`: 新增 3 条(退避后穿过 / 耗尽仍抛不吞 + 旧内容完好 + 临时文件清理 + 次数按单点常量 / 非 `PermissionError` 一次即抛), 头部测试计划同步。
- `tests/test_hr_discovery.py`: 新增 2 条(首次被拒后重试成功 / 重试耗尽「读不到 ≠ 空表」) + `_simulate_read_denial` 夹具(只拦目标文件的 `builtins.open`), 头部测试计划同步。
- 滚动面(文档): `memory-bank/pitfalls/backend/platform-fs.md` 该条更新处置(两个独立单点并列)+ `复发 +1` 与未命中原因; activeContext 切片 `26-10-16-0935-atomic-write-replace-retry.md`; 本切片。
