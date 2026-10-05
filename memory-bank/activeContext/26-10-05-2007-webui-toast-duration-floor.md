# WEBUI toast 错误/超时停留下限 (用户报「右下角错误信息太短」)

> 摘要: 用户报 WEBUI 右下角错误提示停留太短 —— 停留时长原本是单点缺省 4000ms(error / timeout 类仅少数调用点
> 自填 8000ms), 而报错文案常带原因段, 4s 读不完。改法: `shared/ui_feedback.js` 头部新增**按 kind 的停留下限**
> `TOAST_MS_FLOOR`(error 12000 / timeout 12000 / warn 8000), `toast()` 与 `_finishToast()` 的 `ms` 缺省改为
> `null` 并统一经 `toastMs(kind, ms)` 解析 —— 调用点显式传更短的值一律抬到下限, 传更长照旧(不封顶), 于是全量
> error / timeout 调用点(约 30 处, 散在 8 个片段文件)无需逐个改, 以后新写的调用点也不会再退回短停留。
> 三皮肤共用此单点, 零 CSS / 模板改动。不满足立档阈值(单会话、单文件 + 1 条守阵, 无任务档案)。
> test.full **2622 passed + 4 skipped / 99% / 48.9s**(基线切片 26-10-05-2007)。
> 最后活动: 2026-10-05 20:07

**Refs:** memory-bank/testing/baselines/26-10-05-2007-webui-toast-duration-floor.md

## 现状

- **改动完成, 待提交**。改动面: `src/auto_qb/webui/static/shared/ui_feedback.js`(+20/-4) ·
  `tests/test_web.py`(新守阵 `test_frontend_toast_duration_floor_by_kind` + 测试计划清单一行) ·
  `memory-bank/testing/guards.md`(登记一行) · 本切片 + 基线切片 · `kb.index` 重建生成物。
- 口径 = **按 kind 设下限**, 不是给每个调用点改数字: 调用点缺省 `ms` 取下限; 显式传更短的抬到下限; 传更长不封顶。
  `sticky` 常驻条(强制汇报「等待中」)在排期前 early return, 不经此处; `info` / `ok` 类行为不变(缺省 4000)。
- 验证: Node 临时探针直接驱动生产原语(假造 DOM, 跑完即删)实测 11 例 —— error 缺省 / 旧显式 8000 → 12000 ·
  timeout 6000 → 12000 · warn 缺省 / 旧显式 4000 → 8000 · info 缺省 → 4000 · ok 2500 → 2500(不变) ·
  sticky → 不排定时器 · `_finishToast` 两态同口径。守阵三例红验全红(下限降到 4s / 排期绕过 `toastMs` /
  `ms` 缺省写死 4000)。全量 `test.full` 2622 passed + 4 skipped / 99% / 48.9s。
- 未验证面: 未跑浏览器真机走查 —— 纯常量 + 排期点改动, 三皮肤共用单点且零 CSS / 模板改动。
- 调档口子: 想再调长只改 `ui_feedback.js` 的 `TOAST_MS_FLOOR` 一行; 守阵按「error / timeout ≥ 8s」判,
  不与具体值耦合, 调档不会红。
