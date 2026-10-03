# 基线切片 26-10-03-2348 — HR 取证报告 §8 显示缺陷修复(B2/B3/B4 + C1)

> 摘要: 用户指派「一并看看」→ 落地取证报告 §8 的 B2/B3/B4 与候选 C1 四项。B2/B3/B4 为显示语义, C1 为真后端 bug(wave_ts 跨波冻结)。

- 时间: 2026-10-03 23:48 (GMT+8)
- 分支: develop @ (本轮回写件, 待用户提交指令)
- 命令: `commands run test.full`
- 实测: **2417 passed + 3 skipped, 37.22s, 覆盖率 99%** (Required coverage of 98% reached)
- 改动面:
  - `src/auto_qb/webui/static/shared/hr_status.js` — B4 退役行徽章三态(已移出/已退役) + B3 中间态(在列·<档位人话>) + 新增 `hrsTerminalLane` + B2 kv 行标签「下次核对清单」
  - `src/auto_qb/webui/static/{atlas,console}/css/dialogs.css` + `prism/css/views.css` — `hr-pres-miss` 退役 → `hr-pres-out`(蓝) / `hr-pres-off`(中性) 三套成对
  - `src/auto_qb/hr/status.py` — B2 `fresh_text`「下次核对清单」+ blocking_reason 兜底 + 注释
  - `src/auto_qb/hr/service.py` — C1 `wave_ts` 不跨波继承(置 0 本波重算) + 注释
  - `src/auto_qb/webui/server/routes/hr.py` — docstring 换词
  - `tests/test_web.py` — B3/B4 守阵(退役文案 literal 零残留 / hr-pres-out 色义 / 中间态 helper 与文案)
  - `tests/test_hr_status.py` — B2 兜底文案换词
  - `tests/test_hr_service.py` — 新增 `test_wave_ts_refreshes_every_wave_not_frozen`(变异验证: 还原旧码即红)
- 未做: A1 设计确认项 / C3(30 天静默淘汰预告) —— 等指派
- 未验证面: 真机走查(需真实 qB + HR 数据)仍待用户执行
