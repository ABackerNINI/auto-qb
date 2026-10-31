# 2850 —— 本地通道传输安全调研(WebUI + HR 取数通道)基线

> 摘要: 用户命题「WebUI⇄auto-qb 与 auto-qb⇄扩展两条通道均为明文 HTTP, 有安全风险, 要求调研成熟加密方案并对比」。本轮产出可行性报告 `reports/26-10-09-1529-report-transport-encryption-feasibility.html`(单文件 HTML, `doc-topic=transport-encryption`, 状态 `Done`)。**零 `src/` 与 `tests/` 改动** —— 相对上基线 [26-10-09-1522](../baselines/26-10-09-1522-test-mutation-audit-hr-plan.md) 的 pytest 面四项逐位持平(passed 与覆盖率同值)。
> 基线时间: 2026-10-09 15:29

**Refs:** memory-bank/activeContext/26-10-09-1529-transport-encryption.md

## test.full 实测

- 分支: `develop`(HEAD `de0c4fa6`, 工作树含本轮报告 + 回写件时实测)
- 命令: `commands run test.full`(Windows, 单次采样 —— 耗时口径见 testing/baseline.md「必须带区间」)
- **实测 (Windows)**: **2850 passed + 4 skipped, 0 failed, 覆盖率 TOTAL 99%**
  (16567 语句 / 169 未覆盖 / 5716 分支 / 145 partial; 门槛 98% 达标)
- 相对上基线 [26-10-09-1522](../baselines/26-10-09-1522-test-mutation-audit-hr-plan.md)
  (2850 passed + 4 skipped, 同 16567 语句 / 169 未覆盖 / 5716 分支 / 145 partial):
  passed **±0** / 语句 **±0** / 未覆盖 **±0** / 分支 **±0** / partial **±0**。
- **±0 的归属**: 本会话**零 `src/` 与 `tests/` 改动**, 且会话开工 `my-commit-flow.sync` 从
  `9926953b` 快进到 `de0c4fa6` 的提交未触及测试收集面 ⇒ 与上基线同值。
- 增量明细(本轮真正新增): `memory-bank/reports/26-10-09-1529-report-transport-encryption-feasibility.html`;
  回写 `memory-bank/activeContext/26-10-09-1529-transport-encryption.md`、
  `memory-bank/issues/26-10-09-0855-feat-hr-channel-loopback-only.html`(`doc-refs` 补双向认领链);
  重建 `memory-bank/reports/_index.md`。`tests/` 与 `src/` **零改动** ⇒ pytest 收集面不变。

## 对照判据(后续沿用)

- 以本切片(2850+4 / 16567 / 169 / 5716 / 145)为对照点: 预期 passed 只升不降、未覆盖 / partial 不升。
- 本报告**不产生代码改动**; 若后续按报告建议落地「暴露即加密闸门 / 一键本地 CA」(涉及
  `cryptography`/`trustme` 依赖与 `web.tls.*` 配置键), 数字变化在实施轮另立基线切片。
