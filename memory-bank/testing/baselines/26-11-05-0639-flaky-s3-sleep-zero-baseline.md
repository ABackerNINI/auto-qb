# 5364 passed + 2 skipped(根) —— flaky 治理 S3 收口全量基线(裸 sleep 清零 + 性能断言裁决)

> 摘要: flaky 治理 S3 收口全量基线(裸 sleep 清零 + 性能断言裁决)
> 基线时间: 2026-11-05 06:39
**Refs:**

## 验收数字

`commands run test.full` 实测(2026-11-05 06:36-06:39, 148.02s, 8 worker 带覆盖率):

- 汇总行: **5364 passed, 2 skipped, 1 warning in 148.02s (0:02:28)**
- TOTAL 表: 24495 statements / 52 missed / 8388 branches / 34 partial, 覆盖率 **99%**
- 副作用台账: 共若干条, **越界 0 条**(会话级守阵收尾零越界)
- 口径注记:
  - 与上基线持平(不低于): `test.full` 5364 passed, 2 skipped —— 零净增/净减用例, 本轮只改等待形态与断言余量, 不增删测试。
  - 白名单终态: `ALLOW_SLEEP_TESTS` 仅剩 `tests/clock.py` 合法等待单点本体 1 处(带理由保留); 独立 AST 复扫 tests/ 裸 `time.sleep` 实调用 = 恰好 1 处(clock.py:105), 守阵两侧对账全绿(`test_flaky_timing_guards.py` 9 passed)。
  - 1 warning 为既有既有告警(非本轮引入)。

## 本改动面

- **S3 第 2 条余量(12 文件 18 处裸 sleep 清零, 前序会话完成于工作树、本轮核实+定向复跑)**:
  - 线程协作点改 `wait_until`(判据①): `test_hr_discovery.py`(3 处)、`test_hr_fetcher_channel.py`(1)、`test_hr_runtime_lifecycle.py`(1)、`test_hr_server.py`(2)、`test_tray.py`(1)、`test_ui.py`(2 轮询 + run 循环改事件同步)、`test_notify.py`(1, 注明 emit 内同步无窗)、`test_locking.py`(1, 注明 acquire 同步落盘无窗)。
  - 时间语义改注入假钟(判据②): `test_relocate_probe_cache.py`(覆盖戳同秒语义改 FakeClock 推进, `>=` 弱断言升 `>`)、`test_webui_relocate_chain.py`(ChainCache TTL 改注入假钟 advance)。
  - 有意真窗(判据③): `test_web_auth.py`(h11 头分片时序刺激, `Event.wait(0.15)` 真窗)、`test_hr_worker_lifecycle.py`(忙等观察窗 0.4s 真窗 + 经过时间下界断言)。
- **S3 第 4 条(挂钟性能断言裁决)**: `test_clock.py::test_wait_until_returns_fast_on_immediate_true` 上界重构 —— interval 显式 0.5s + 上界 0.3s(被守回归量级定界: 混入一次节拍即红, 对真实耗时余量 6x); 其余上界逐条裁决为行为断言保留(详见任务报告)。
