# qB 流量采样 1.5s 档被整数秒口径静默抬到 2s(修复完成)

> 摘要: 用户报「qb_traffic.sample_interval=1.5s 实际 2s, main_tick=1.5s」。分析定位 +
> 用户拍板「直接修」。根因 = `traffic_sample_mod._apply_interval` 把为块头 B 行设计的
> 整数秒口径 `int(ceil(effective))` 同时赋给 `task.interval`: 1.5 恰是 main_tick=1.5 的
> 整数倍(失配告警不触发)却被静默抬到 2s 调度; `Task.interval` 本为 float(`next_run =
> now + interval`), 根本不需要取整。深层是 v3 计划自身不一致: 下限=main_tick 硬校验 +
> 前端 A4 轮询下界 1500ms 都按 1.5s 档设计, 唯格式 §02 钉死整秒。修法: ①生效间隔保持
> 浮点(`task.interval = effective`, 取整只发生在失配归倍数层); ②格式放宽「整秒 → >=1
> 允许小数秒」(规范十进制, 整值不带小数点与历史文件一致; 解析 NaN/inf/越界坏行;
> `append_records` 去 `int(header[1])` 静默截断点)。兼容性 = 纯放宽, 旧文件零迁移。
> 不满足立档阈值(单点 bug fix, 回写 v3 既有档案进度日志)。
> test.full **2619 passed + 4 skipped / 99% / 25.80s**(基线切片 26-10-05-1814)。
> 最后活动: 2026-10-05 18:14

**Refs:** memory-bank/tasks/26-10-04-backend-qb-traffic-storage-v3.md, memory-bank/testing/baselines/26-10-05-1814-qb-traffic-v3-decimal-interval.md

## 现状

- **修复完成, 待提交**。改动面: `src/auto_qb/core/traffic_store.py`(格式化/解析/类型/
  docstring 契约) · `src/auto_qb/core/modules/traffic_sample_mod.py`(`_apply_interval` 浮点
  化 + BlockBuffer/`_effective_interval` 类型) · 两测试文件(新增 2 例 + 重钉 1 例) ·
  本切片 · 基线切片 · v3 档案进度日志 · keys.md sample_interval 行 · `kb.index` 生成物。
- 新增守阵: `test_interval_decimal_match_kept_not_ceiled`(匹配小数档三处如实: task.interval /
  _effective_interval / B 行文本 `,1.5`; 同块零漂移 r 行不写 dt) +
  `test_v3_decimal_interval_roundtrip_and_bad_parse`(roundtrip 1.5 + 标称槽位 1000.0→1001.5 +
  解析非法族 0.5/abc/nan/inf 计坏); 重钉 `test_v3_format_fail_fast_and_torn_tail`(30.5 移出
  非法清单, 补 NaN/inf/字符串/整值 float 形态断言)。既有失配语义(3/2→4, 5/2→6)不变。
- 验证: 定向 95 例先绿 → 全量 test.full 2619 passed + 4 skipped / 99% / 25.80s。
- 待办: 用户说「提交」走 ship.commit; 真机复核(config.yml 已是 1.5s 配置, 修复生效后
  dat 块头应出现 `B,<start>,1.5` 且 dt 链零漂移)。
