# 2622 —— WEBUI toast 错误/超时停留下限 (用户报「右下角错误信息太短」)

> 摘要: 用户报 WEBUI 右下角错误提示停留太短 —— `shared/ui_feedback.js` 头部新增按 kind 的停留下限
> `TOAST_MS_FLOOR`(error 12000 / timeout 12000 / warn 8000), `toast()` 与 `_finishToast()` 的 `ms` 缺省
> 改为 `null` 并统一经 `toastMs(kind, ms)` 解析(显式传更短的值抬到下限, 传更长不封顶); 新增静态守阵
> `test_frontend_toast_duration_floor_by_kind`(tests/test_web.py)钉住下限与两条排期路径。
> 三皮肤共用单点, 零 CSS / 模板改动。
> 基线时间: 2026-10-05 20:07

**Refs:** memory-bank/activeContext/26-10-05-2007-webui-toast-duration-floor.md

- 分支: develop @ 00865dbf(会话开工同步; 工作树含本轮改动: ui_feedback.js + tests/test_web.py +
  guards.md + 本切片 + activeContext 切片, 未提交)
- 命令: `commands run test.full`(Windows, 单次采样 —— 耗时口径见 testing/baseline.md「必须带区间」)
- **实测 (Windows)**: **2622 passed + 4 skipped, 48.9s, 覆盖率 TOTAL 99%**
  (15813 语句 / 167 未覆盖 / 5398 分支 / 140 partial; 门槛 98% 达标)
  同树二次采样(写完本切片 + `kb.index` 后的终态树): **2622 + 4 / 99% / 47.8s** —— 耗时区间
  **47.8 ~ 48.9s**, 用例与覆盖率五项逐字相同。
- 相对上一条**本 clone** 基线 [26-10-05-2000](26-10-05-2000-qb-traffic-v4-delta-report.md)
  (2621 passed + 4 skipped @ 80f48bc7): passed **+1**, 语句 / 分支 / 未覆盖三项**逐项持平**
  (15813 / 167 / 5398 / 140) —— 增量恰为本轮新守阵 `test_frontend_toast_duration_floor_by_kind`
  (只读 `ui_feedback.js` 源码, 不触被覆盖面, 故覆盖率三项零变化)。
- 靶向验证: `commands run test.one -- tests/test_web.py::test_frontend_toast_duration_floor_by_kind` 绿;
  **三例红验全红**(下限降到 4s / 排期改回裸 `ms` / `ms` 缺省写死 4000), 恢复后复核 `toastMs(kind, ms)`
  恰 2 处、`error: 12000` 恰 1 处、`ms = null` 恰 2 处; `node --check ui_feedback.js` 语法 OK。
  另有 Node 临时探针直接驱动生产原语(假造 DOM)实测 11 例时长, 结论见 activeContext 切片(探针跑完即删)。
- 改动面: `src/auto_qb/webui/static/shared/ui_feedback.js`(+20/-4) · `tests/test_web.py`(守阵 +1, 计划清单 +1 行) ·
  `memory-bank/testing/guards.md`(登记 1 行) · 本切片 + activeContext 切片 · `kb.index` 生成物。
