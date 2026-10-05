# 基线切片 26-10-05-1814 — qB 流量存储 v3 块头 interval_s 放宽小数秒(S6 追修)

> 摘要: 用户报「sample_interval=1.5s 实际 2s」。根因 = `_apply_interval` 把为块头 B 行
> 设计的整数秒口径 `int(ceil(effective))` 同时赋给 `task.interval` —— 1.5s 配
> main_tick=1.5s 恰为整数倍(失配告警不触发)却被静默抬到 2s 调度。修法: 生效间隔保持
> 浮点(`task.interval = effective`)+ 格式规格放宽「整秒 → >=1 允许小数秒」(规范十进制:
> 整值不带小数点与历史文件形态一致, 非整值最短往返表示如 1.5; 解析侧 NaN/inf/越界坏行)。
> 兼容性 = 纯放宽(旧整秒文件是小数子集, 零迁移)。
> 基线时间: 2026-10-05 18:14

**Refs:** memory-bank/tasks/26-10-04-backend-qb-traffic-storage-v3.md

- 分支: develop @ c2ba6054 + 工作区改动(未提交, 等提交指令)
- 命令: `commands run test.full`(Windows)
- **实测 (Windows)**: **2619 passed + 4 skipped, 25.80s, 覆盖率 TOTAL 99%**
  (15813 语句 / 167 未覆盖 / 5398 分支 / 140 partial; 门槛 98% 达标)
- 相对上一基线 [26-10-05-1007](26-10-05-1007-qb-traffic-v3-s6-live-tail.md) 真值
  (2596 passed / 15482 语句 / 163 未覆盖 / 5330 分支 / 137 partial): passed **+23** =
  本轮 +2(`test_interval_decimal_match_kept_not_ceiled` / `test_v3_decimal_interval_roundtrip_and_bad_parse`)
  + 自 S6 基线后经 sync 合入的其它会话用例(+21, 非本轮范围); 语句 +331 / 分支 +68
  同源(sync 合入 + 本轮新增)。重钉 1 例: `test_v3_format_fail_fast_and_torn_tail`
  的 interval_s 非法清单(30.5 从非法移出为合法小数秒, 补 NaN/inf/字符串与整值形态断言)。
- 核心守阵: sample 侧 `test_interval_decimal_match_kept_not_ceiled` 钉「匹配小数档三处
  如实」(task.interval == 1.5 / _effective_interval == 1.5 / B 行文本 `,1.5` 结尾) +
  同块两记录标称 1.5s 推进零漂移(r 行不写显式 dt); store 侧
  `test_v3_decimal_interval_roundtrip_and_bad_parse` 钉 roundtrip(解析还原 1.5 +
  标称槽位推进 1.5s: 1000.0 → 1001.5)与解析非法族(0.5/abc/nan/inf/1.5.5 整行计坏不开新块)。
- 既有失配语义不变: main_tick=2 配 3s→4s、5s→6s 用例照旧通过(取整只发生在失配归倍数层)。
