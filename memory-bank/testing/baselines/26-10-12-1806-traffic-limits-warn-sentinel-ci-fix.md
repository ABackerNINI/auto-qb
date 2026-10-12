# 3145 — 修复 CI 红: 限速历史节流哨兵吞掉首次告警(monotonic 起点=开机时刻)

**Refs:** memory-bank/tasks/26-10-12-webui-traffic-limit-history.md,memory-bank/pitfalls/testing/monotonic-warn-sentinel.md

> 摘要: `core/traffic_limits.py` 两处节流哨兵 `0.0` → `None`(开机不满 1 小时的机器上首次告警不再被吞) + 新增 1 条守阵(monkeypatch 时钟钉在开机 2 分钟)。
> 基线时间: 2026-10-12 18:07

上一基线: memory-bank/testing/baselines/26-10-12-1036-webui-drawer-table-rework-u4.md

## 本波改动面
- `core/traffic_limits.py`: `SpeedLimitRecorder._oswarn_ts` / `_guard_ts` 初值 `0.0` → `None`, 两处判据补 `is None or` 前缀(「从未告警」不再被 `now - 0.0 < GAP` 误判成"刚告警过")。
- `tests/test_traffic_limits.py`: 新增 `test_recorder_warn_first_fire_on_fresh_boot`(守阵; 头部「## 测试计划」同步补一行)。

## 验收数字
- `test.full`: **3145 passed + 4 skipped** / 38.5s / 覆盖率 `TOTAL 16708 161 5688 140 99%`。
- CI 复现与红验(本机等价论证, 不依赖 CI): 把时钟钉成开机 2 分钟(`time.monotonic = lambda: 120.0`)后 ——
  ① 还原旧哨兵 ⇒ **精确复现 GitHub CI 那两条红**(`test_recorder_oserror_degrade` / `test_recorder_patological_flip_guard`, 签名同为 `assert False = any(<generator ...>)`);
  ② 修复后同条件 13 passed; ③ 新增守阵在旧哨兵下本机即红、还原即绿。
- 注: 本片只测 Windows 侧; Linux 侧未重测(改动为纯逻辑, 无平台面)。
