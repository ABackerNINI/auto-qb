# 4175 passed + 2 skipped —— submitAltLimits 非空闸修复后基线

> 摘要: 备用限速组补非空闸(读失败窗口不再静默写 0/0)修复后基线
> 基线时间: 2026-10-30 08:35
**Refs:** memory-bank/issues/26-10-30-0622-bug-alt-limits-submit-empty-gate.html

## 验收数字

`commands run test.full` 实测(2026-10-30 08:35, Windows, 修复落盘后):

```
TOTAL                                                21124     95   7142    100    99%
4175 passed, 2 skipped in 120.08s (0:02:00)
```

- **汇总行**: **4175 passed / 2 skipped**, 墙时 **120.08s** 区间口径见 testing/baseline.md「耗时与覆盖率口径」。
- **TOTAL 表**: 语句 **21124** / 未覆盖 **95** / 分支 **7142** / partial **100** / 覆盖率 **99%**。
- **红验**: 新电池 `test_alt_limits_empty_gate_node` 五案直接断言零 POST(A/B 案)与载荷数值(D/E 案),
  闸被移除即 A/B 案红(空串会走 POST)。

## 本改动面

| 文件 | 改动 |
|---|---|
| `src/auto_qb/webui/static/shared/dialogs.js` | `submitAltLimits` 补与 `speedOvReady` 同形的非空闸: 两框任一为空/非有限数即整组跳过不下发(返回 true 不挡主速组), 堵 /api/speed/mode 读失败窗口(altCurrent=null, `_fillSpeedFields` 回空)下 `Number("")\|\|0`=0 静默写不限速的缺口 |
| `tests/test_webui_optimistic_rename_alt.py` | 新增 `test_alt_limits_empty_gate_node` 五案 node 电池(真跑 submitAltLimits) + 头部「## 测试计划」同步 |
| `memory-bank/issues/26-10-30-0622-bug-alt-limits-submit-empty-gate.html` | 认领: Open → In Progress → Done, 补复验 / 实际修法 / 验证方式 |
| `memory-bank/testing/baselines/26-10-30-0835-webui-alt-limits-empty-gate.md` | 本切片 |
