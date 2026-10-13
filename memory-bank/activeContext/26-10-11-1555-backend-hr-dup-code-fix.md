# hr 重复代码重构 · 两轮(R1 5 条 + R2 3 条 refactor issue 认领与修复)

> 摘要: R1(2026-10-11) 用户「修复hr部分问题…」按拍板只做低风险高收益子集(5 条) + 保守口径(无行为变化收口): adapter-parse / report-cli / lane-transition / warn-dedup / model 强转。R2(2026-10-13) 用户「认领并修复hr相关的3个refactor issues」续认领 3 条: ① `hr-site-derive-convention-dup`(派生单点上收 `Config.hr_site_confs()`, runtime/report 改走单点; webui 半留轮 15) ② `hr-token-persist-convention-dup`(抽 `infra.utils.resolve_or_create_token`, hr/webui 两端一行委托, logger 身份经参保持) ③ `torrents-hr-entry-guard-dup`(抽 `TorrentRecord._hr_guard`, 三判定入口守卫收口; `hr_judgement` 语义不同不并入)。两轮均**零行为变化**, 各配静态守阵。仍留 `Open`: store-recover(与轮 18 合并) / thread-lifecycle(机制不同收益低) / fetchable(待拍板)。R2 全量验证见基线切片 `baselines/26-10-13-2150-backend-hr-dup-code-fix.md`。
> 最后活动: 2026-10-13 21:50

**Refs:** memory-bank/tasks/26-10-11-backend-hr-dup-code-fix.md

## 正在进行

- 无 —— R2 已收口(3 条 issue 置 `Done` + 守阵 + 全量基线), 全程见任务档案 R2 段。

## 关键结论(供后续执行参考)

- **(R1) 报告口径要复核, 不照抄**: 档位处置三处 fail_streak/告警各不相同 → `_settle_lane` 用 `count_failure` 显式承载; 节流窗口四处值不同 → 只抽算法(`warn_gap_floor`)不动模块常量补丁面; `stamp_text_ts` 死件删除(含单测)。
- **(R2) 单点落位选「共同既有依赖」而非报告建议**: 站点派生报告建议以 HrRuntime 为单点, 但 report 是无 runtime 的 CLI 入口(反向依赖拉进 server 栈) —— 落在 Config 聚合根(两侧已共同依赖)更稳。
- **(R2) 跨模块单点必须显式传 logger 身份**: 两侧守阵按 logger 名(caplog record.name)钉「密钥不进日志」; 单点放 infra 后 logger 由调用方传入, 4 条 monkeypatch(patch 地址 = 实现所在地 `infra.utils.atomic_write`)随迁。
- **(R2) rationale 注释搬进 infra docstring 注意守阵**: `test_no_o_trunc_write` 扫非注释 token(STRING 含 docstring) —— 「O_TRUNC」字面量在 docstring 里也判红, 搬运时改写措辞。
- **(R2) `hr_judgement` 不并入 `_hr_guard`**: 它排除时返回 None(走本地字段逻辑)而非 False, 返回语义不同, 强并会改行为。

## 后续候选(未开工)

- hr 仍 `Open` 的 3 条: `hr-store-recover-lock-family-dup`(与轮 18 infra 合并) / `hr-thread-lifecycle-boilerplate-dup`(收益低可暂缓) / `hr-fetchable-dead-config`(二选一待拍板)。
- webui 半合流: token(R15-C01) / 站点派生(R15-C03) 随轮 15 改走 infra/Config 单点(守阵白名单已预留)。
- `hr-lane-transition` 的 B 类子项(各档摘要串 service ↔ status, `(全深度)` vs `(全)`)需先钉文案差异点 + 回归保护再合。
- 重复代码审查主线: Phase 2 前端(轮 20–23)、Phase 3 测试与横切(24–25)、Phase 4 汇总(轮 26)仍未开工(见 `26-10-10-backend-dup-code-audit`)。
