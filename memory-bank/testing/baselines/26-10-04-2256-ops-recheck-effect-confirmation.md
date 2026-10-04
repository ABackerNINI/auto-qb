# 基线切片 26-10-04-2256 — recheck 生效确认证据门控重设计全量基线 (计划 26-10-04-1824 S4 收尾)

> 摘要: 认领 issue 26-10-03-1140(recheck 首跳误判已完成种子校验成功)的重设计四笔提交后全量实测。核心 =
> 判定提为纯函数 `poll_verdict`(SUCCESS 仅 seen_checking 可达, 「无证据成功」签名层面不可表达)+ 生效证据
> 谓词 `is_piece_checking` 收窄排除 checkingResumeData 伪证据 + poll 闭包证据门控状态机(未见证据 progress
> 回落提前判败)+ 宽限耗尽一次性仲裁直查 + 提交点 R1 实时复核与 live 基线; 本轮 S4 收尾另落坑档
> `pitfalls/backend/effect-confirmation.md` 与 ops_mod 判定纪律一句。

> 基线时间: 2026-10-04 22:56
> 档案: memory-bank/plans/26-10-04-1824-plan-ops-recheck-effect-confirmation.html

**Refs:** memory-bank/issues/26-10-03-1140-bug-ops-recheck-false-success.html · memory-bank/pitfalls/backend/effect-confirmation.md · memory-bank/testing/baseline.md

- 分支: ops-recheck-effect-confirmation @ d51c0d93 (+ 本轮未提交改动: src/auto_qb/core/modules/ops_mod.py
  docstring / memory-bank/pitfalls/backend/effect-confirmation.md / issue 与计划 HTML 留痕 / 本切片)
- 命令: `commands run test.full`(Windows, 单次采样 —— 耗时口径见 testing/baseline.md「必须带区间」)
- **实测 (Windows)**: **2530 passed + 4 skipped, 36.76s (引擎计 37.5s), 覆盖率 TOTAL 99%**
  (14868 语句 / 153 未覆盖 / 4982 分支 / 113 partial; 门槛 98% 达标, 精确 98.63%)
- 靶向四文件(test_ops + test_checking + test_modules_p4 + test_trigger_events): **131 passed**(3.21s, 与计划验收数字一致)
- 相对上基线 (26-10-04-1849: 2515 passed + 4 skipped / 99% / 37.45s): passed **+15** —— 本分支四笔提交
  (fd3b9a5d / 6b408006 / 8c5c3548 / d51c0d93)新增 15 条用例(A 组 3 / B 组 3 / C 组 3 / D 组 4 / E 组 2)+
  既有用例适配 27 处; skip 集合不变(Windows 侧 4 条 POSIX 专属)。
- 改动面: src/auto_qb/rules/checking_meta.py(PollVerdict / poll_verdict / is_piece_checking 纯函数)·
  src/auto_qb/core/modules/ops_mod.py(recheck poll 证据门控 + R1 实时复核 + 仲裁直查)· tests/test_checking.py(A 组)·
  tests/test_ops.py(B/C/D/E 组)· tests/test_modules_p4.py / tests/test_trigger_events.py / tests/helpers.py(适配)。
