# 限速曲线手动保护日志刷屏 — 已实施, 待提交

> 摘要: 用户报「重复的『限速曲线 | 下载限速当前 10265KiB/s 为奇数, 疑似用户手动设置, 本轮不覆盖』LOG 过多」。根因单一: `speed_curve.py` 的手动保护分支**逐轮**打 INFO, 而手动值是**持续状态**(不改 qB 就一直命中) ⇒ `interval: 10M` 下每天上百条且永不停止。命中已记判据 `pitfalls/ops/alert-levels.md` ②④(**该条复发 +1** —— 同一套保护在 `tracker.py` 是静默的, 只有这里逐轮刷)。已实施: 抽 `_log_manual_skip`(进入状态/手动值变化记一条 INFO + 每 1h 提醒一次, 其余轮次降 DEBUG; 退出手动保护清记忆) + `_MANUAL_REMIND_GAP` 常量 + 宿主 `_curve_manual_log` 槽位; Web UI 的 `reasons(code=manual)` 照旧逐轮带, 去重不丢信号。+3 守阵(变异测试实测: 还原旧行为 3 条全红)。
> 最后活动: 2026-09-26 20:55

## 已完成

- **根因**: `speed_curve.py` 手动保护分支(原 137-138 行)每轮无条件 `logger.info(...)`。用户配置
  `global_speed_limit_curve.interval: 10M` ⇒ 每天约 144 条(双向都手动则 288), 且**永不停止**。
  违反本项目已定判据 `pitfalls/ops/alert-levels.md` ②「同一根因只说明白一次」/④「持续状态按周期
  再提醒、被去重的轮次留 DEBUG」; 同族参考实现 `hr/worker.py::_note`(状态指纹 + `channel_silence_warn`)
  与 `hr/service.py::_warn_no_channel`(每站只报一次 + 恢复后重置)。
- **实施**(用户拍板「状态变化 + 周期提醒」): `speed_curve.py` 加 `_MANUAL_REMIND_GAP = 3600.0` +
  `_log_manual_skip(dir_key, label, cur)` —— 进入状态 / 手动值变化 → INFO, 同状态超周期 → 再提醒一次,
  其余 → DEBUG; 退出保护分支 `pop` 清记忆; `qbmanager.__init__` 加 `_curve_manual_log: dict` 槽位。
  **未新增配置键**(日志节流不是行为开关 ⇒ 模块常量, 不触发 `validate_config`/schema 同步)。
- **测试**: `tests/test_speed_curve.py` +3 条(`_CurveLogCapture` 复用既有"给模块 logger 挂 StringIO"
  姿势 —— `setup_logging` 会清空 root handlers 故 caplog 失效); 文件头「## 测试计划」已同步。
  **变异测试**(临时还原旧行为)实测 **3 条全红** ⇒ 守阵非空转。
- **实测**: `test.full` **1682 passed + 1 skipped / 0 failed**(28.4s, 并行); 覆盖率 TOTAL **91%**
  (11308 语句 / 816 未覆盖 / 3726 分支 / 331 partial), `speed_curve.py` **98%**
  (117 语句 / 3 未覆盖 / 42 分支 / 0 partial)。基线切片见 `testing/baselines/26-09-26-2055-speed-curve-manual-log-throttle.md`。
- 知识库回写: `modules/mixins.md` 行数 200→261 + 方法清单补 `_log_manual_skip`;
  `pitfalls/ops/alert-levels.md` 同族旧账补本例(守阵指针 + 「别把 `tracker.py` 的静默当模板」反例 + 复发闭环);
  `pitfalls/testing/tmpdir.md` **复发 4→8**(开工后裸跑 `uv run pytest <单文件>`, 读了没照做; 同因条目已合并压缩以回到 cap 内)。
- **切片退役**(用户拍板): 本切片使切片数达 41 > 上限 40(`kb.active` 报 0 个 14 天陈旧可退) ⇒ 退役最老存根
  `26-09-22-2038-backend-qb-move-dot-qb`(内容已全在计划 HTML + 任务档案), 其唯一待办「计划待过目后实施」
  已蒸馏进 `想法.md` TODO(沿用 2026-09-26 config-value-range 的同款先例)。

## 正在进行

- **代码与测试已就绪, 未提交** —— 用户未说「提交」, 按请求边界不自作主张。

## 下一步

- 待用户显式「提交」后走 `my-commit-flow` 流水线(预检 → 合并远端 → 回写随主提交暂存 →
  `ship.commit` → `ship.push` → 核 ref 三处)。
- **未立档**: 不命中立档阈值(2 个源文件 < 3, 指令 1 轮) ⇒ 本切片即本次全部滚动状态。
