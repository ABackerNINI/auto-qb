# 计划 Index

> **本文件是生成物, 不要手改** —— 由 `commands run kb.index` 扫描 `plans/*.html` 的 `doc-*` meta 生成;
> 新增制品或改状态后重跑脚本即可, 合并冲突也只需重跑。
> 每行 = `[时间戳] 标题 — 专题`(分区即状态); 状态取值: `In Progress` / `Open` / `Done` / `Dropped` / `Superseded`。
> **已完结状态**(Done / Dropped / Superseded)只列**最近若干条**(上限 `CLOSED_KEEP`, 装不进 8,000 字符预算就继续收紧; 更老的**制品原地不动**, 只是不出本索引): 全量清单见
> [attachments/_archive.md](attachments/_archive.md), 该目录不计 cap。
> 状态写在制品 `<head>` 的 `<meta name="doc-status">` 一行(单处); 协议与决策树见
> [conventions/doc-forms.md](../conventions/doc-forms.md), 跨形态专题视图用 `commands run kb.docmap` 查(不落盘)。
> 机械守卫: `tests/test_docs_forms.py`(索引 == 生成结果 / meta 完整 / 命名合规 / dark 主题)。

## In Progress

- [26-10-31-1119] [qBittorrent 5.3.x 双版本支持落地计划(facade 修复→升库→升 qB→走查→回写)](26-10-31-1119-plan-qb-5-3-support.html) — `qb-5-3-support`
- [26-10-10-2001] [计划 · WEBUI 选中 × 触发 一致性](26-10-10-2001-plan-webui-selection-trigger-parity.html) — `webui-selection-trigger-parity`
- [26-09-22-2318] [auto-qb 软件版本管理方案 v2 · 版本号 / Tag / CHANGELOG / 机械化发版](26-09-22-2318-version-management-plan.html) — `deps-version-management`

## Open

- [26-11-07-0441] [code-review 留痕面修补: 派发次数与引文校验进闸门](26-11-07-0441-plan-review-trace-fields.html) — `review-trace-fields`
- [26-11-05-1049] [memory-bank 文档压缩与防回涨分步执行计划(8K 新口径)](26-11-05-1049-plan-kb-doc-compress.html) — `kb-doc-compress`
- [26-11-05-0848] [跳检自身失败闸门 G9: WEB case-2 强制 + 规则侧硬 skip 双点同谓词](26-11-05-0848-plan-skip-check-self-fail-gate-g9.html) — `skip-check-self-fail-gate-g9`
- [26-11-03-2212] [整组迁移同盘证明误拒：根因与修复计划](26-11-03-2212-plan-relocate-same-fs-proof.html) — `relocate-same-fs-proof`

## Done

- [26-11-07-0452] [GitHub CI WEB UI smoke 门禁改造: 超时根因、分片接线与 push 节流全量轮](26-11-07-0452-plan-github-ci-smoke-gate.html) — `github-ci-smoke-gate`
- [26-11-07-0201] [code-review 跨 clone rebase 组合缺口修补](26-11-07-0201-plan-review-rebase-gap.html) — `review-rebase-gap`
- [26-11-06-0759] [分批评审: 从「收口一次评」到「一批一评 + 强制留痕」](26-11-06-0759-plan-review-batch-policy.html) — `review-batch-policy`
- [26-11-06-0124] [提交信息自动审查: ship.commit 内联三态机检(BOM/乱码/骨架/残留)](26-11-06-0124-plan-commit-msg-review.html) — `commit-msg-review`
- [26-11-05-2335] [存量代码全库评审 R4·五路线并行体系化](26-11-05-2335-plan-legacy-code-review-4.html) — `legacy-code-review-4`
- [26-11-05-0808] [relocate 整组迁移重构: fastresume 改写收尾(回收 daemon 下线窗口)+ 未收尾再迁移](26-11-05-0808-plan-relocate-fastresume-finalize.html) — `relocate-fastresume-finalize`
- [26-11-05-0635] [类型注解标准清偿与 mypy 渐进接入分步计划](26-11-05-0635-plan-type-annotations-mypy.html) — `type-annotations-mypy`
- [26-11-05-0546] [relocate 零搬移修复方案压测(renameFolder 两步复位 + 三闸门)](26-11-05-0546-plan-relocate-zero-move-fix-stress.html) — `relocate-zero-move-fix-stress`
- [26-11-05-0118] [flaky 测试结构化治理: 时钟注入与抖动消除](26-11-05-0118-plan-flaky-test-governance.html) — `flaky-test-governance`
- [26-11-04-2357] [跳检 dedup 闸门遮蔽修复: 提到 G3 之前恢复 skip 语义与文案](26-11-04-2357-plan-skip-check-gates.html) — `skip-check-gates`
- [26-11-04-1042] [待收尾迁移种子的 WebUI 可见性与路径链展示计划](26-11-04-1042-plan-webui-relocate-visibility.html) — `webui-relocate-visibility`
- [26-11-04-0554] [收口 code review 制度化实施计划](26-11-04-0554-plan-memory-bank-code-review.html) — `memory-bank-code-review`
- [26-11-04-0157] [测试覆盖率提升 · 第三轮 — 新欠账清偿与出生即绿 (99% / 319 单位 → 收敛)](26-11-04-0157-plan-test-coverage-uplift-3.html) — `test-coverage-uplift-3`
- [26-11-04-0140] [真机实测 RM08 附加轮: /api/sites/missing groups 分组字段(缺失站点合并 WebUI 读侧)](26-11-04-0140-plan-real-rm08-addendum-missing-merge.html) — `real-rm08-addendum-missing-merge`
- [26-11-04-0115] [RM10 附加轮: 缺失站点导出合并真机实测(导出面)](26-11-04-0115-plan-real-rm10-addendum-missing-merge.html) — `real-rm10-addendum-missing-merge`
- [26-11-04-0055] [同机证明实施计划:D+F 主方案 + E1 一次性强探测](26-11-04-0055-plan-relocate-same-fs-proof.html) — `relocate-same-fs-proof`
- [26-11-03-2337] [缺失站点导出/导入 tracker 合并](26-11-03-2337-plan-missing-site-tracker-merge.html) — `missing-site-tracker-merge`
- [26-11-03-2223] [热重载 L2 重建后分组索引恢复（辅种页空态修复）计划](26-11-03-2223-plan-hot-reload-group-index.html) — `hot-reload-group-index`
- [26-11-03-1102] [GTM 逐网卡基线重构 + C-prime 单轮速率告警 实施方案（v3）](26-11-03-1102-plan-gtm-day-total-inflation.html) — `gtm-day-total-inflation`
- [26-11-03-0930] [WebUI bind 失败改为启动期 fail-fast](26-11-03-0930-plan-webui-bind-fail-fast.html) — `webui-bind-fail-fast`
- [26-11-03-0557] [实施计划: 全项目第三次全面 Code Review — 增量区间评审与遗留测试面补审](26-11-03-0557-plan-full-code-review-3.html) — `full-code-review-3`
- [26-11-03-0456] [已完成种子下载保险丝（极简版）](26-11-03-0456-plan-skip-check-download-fuse.html) — `skip-check-download-fuse`
- [26-11-03-0316] [测试侧端口改 0 自动分配](26-11-03-0316-plan-test-port-zero.html) — `test-port-zero`
- [26-11-03-0120] [WEBUI 搜索结果随新增种子自动更新](26-11-03-0120-plan-webui-search-auto-refresh.html) — `webui-search-auto-refresh`
- [26-11-02-2342] [大文件多轮拆分实施计划（&gt;1000 行候选 80 个）](26-11-02-2342-plan-big-file-split.html) — `big-file-split`
- [26-11-02-0657] [测试临时目录自举与互斥锁方案 — R→H→%TEMP% 固定探测 · 禁静默降级 · 禁外部 TMPDIR · 锁自举 · 评审稿](26-11-02-0657-plan-testing-tmpdir-bootstrap.html) — `testing-tmpdir-bootstrap`
- [26-11-02-0351] [WEBUI 大文件列表性能统一优化(抽屉千级文件 + 主表千级复测)](26-11-02-0351-plan-webui-large-filelist-perf.html) — `webui-large-filelist-perf`
- [26-11-02-0134] [整组迁移 qb_temp 闸门按归属收窄](26-11-02-0134-plan-relocate-qbtemp-narrow.html) — `relocate-qbtemp-narrow`
- [26-11-01-2212] [RM09 WebUI 写侧 漂移复测轮排期计划](26-11-01-2212-plan-real-rm09-drift.html) — `real-rm09-drift`
- [26-11-01-2123] [RM08 WebUI 读侧 漂移复测轮排期计划](26-11-01-2123-plan-real-rm08-drift.html) — `real-rm08-drift`
- [26-11-01-2033] [RM04 辅种与分组 漂移复测轮排期计划](26-11-01-2033-plan-real-machine-rm04-drift-plan.html) — `real-machine-rm04-drift-plan`
- [26-11-01-1921] [RM02 主循环·调度·持久化 · 真机实测分步计划(漂移复测轮)](26-11-01-1921-plan-real-machine-rm02-drift-plan.html) — `real-machine-rm02-drift-plan`
- [26-11-01-1031] [RM03 规则引擎 · 真机实测分步计划(漂移复测轮)](26-11-01-1031-plan-real-machine-rm03-drift-plan.html) — `real-machine-rm03-drift-plan`
- [26-11-01-0553] [WEBUI 主表横向滚动条隐藏与底部紧凑指示条](26-11-01-0553-plan-webui-hscroll-indicator.html) — `webui-hscroll-indicator`
- [26-11-01-0434] [提交闸门按改动收窄优化](26-11-01-0434-plan-commit-gate-scope.html) — `commit-gate-scope`
- [26-11-01-0106] [规则引擎重设计方案](26-11-01-0106-plan-rule-engine-redesign.html) — `rule-engine-redesign`
- [26-10-31-2354] [reannounce 确认跟踪改消解等待模型:废除在途直证,成功凭 working/前跳正证据](26-10-31-2354-plan-webui-write-side.html) — `webui-write-side`
- [26-10-31-2316] [WEBUI 动效皮肤 flux 分步实施计划](26-10-31-2316-plan-webui-fx-skin.html) — `webui-fx-skin`
- [26-10-31-1922] [RM10 通知·外部集成 · 真机实测分步计划](26-10-31-1922-plan-real-rm10.html) — `real-machine-rm10-plan`
- [26-10-31-1754] [RM08 WebUI 读侧 · 真机实测分步计划](26-10-31-1754-plan-real-rm08.html) — `real-machine-rm08-plan`

> 更早的 **177** 条已出本索引 —— 制品仍在 `plans/` 目录(未搬动), 全量清单见 [attachments/_archive.md](attachments/_archive.md).

## Dropped

- [26-10-01-1758] [Issue 全量清偿路线图 — 摸排 · 分波 · 执行顺序](26-10-01-1758-plan-issue-clearance-roadmap.html) — `issue-clearance-roadmap`

## Superseded

- [26-11-05-0247] [整组迁移回收机制改造: 单回收进程与未收尾再迁移](26-11-05-0247-plan-relocate-single-recycler.html) — `relocate-single-recycler`
- [26-10-13-0413] [种子状态双写通道重构 · B2 实施计划 — 真值回写 + 显式自写变更发射](26-10-13-0413-plan-seed-state-writeback-truth-emission.html) — `seed-state-writeback`
- [26-10-09-0856] [HR 取数通道「外部扩展 / 跨机」支持 · 分步实施计划 · auto-qb](26-10-09-0856-plan-hr-channel-remote.html) — `hr-channel-remote`
- [26-09-30-1751] [计划 · 热重载机制简化: 统一挂载口 vs 保存即重启](26-09-30-1751-plan-hot-reload-simplify.html) — `hot-reload-simplify`
- [26-09-26-0822] [计划 · WEB UI 键盘快捷键（可自定义）· 可行性分析与实施计划](26-09-26-0822-plan-webui-keyboard-shortcuts.html) — `webui-keyboard-shortcuts`
- [26-09-25-2043] [HR 悬停弹窗模板 · T1 档案卡 · auto-qb](26-09-25-2043-plan-webui-hr-popup-t1-spec-card.html) — `webui-hr-popup-t1`
- [26-09-25-2043] [HR 悬停弹窗模板 · T2 结论卡 · auto-qb](26-09-25-2043-plan-webui-hr-popup-t2-verdict-card.html) — `webui-hr-popup-t2`
- [26-09-15-0910] [auto-qb · WEB UI 第七轮优化计划](26-09-15-0910-webui-optimization-plan-v2.html) — `webui-optimization`
- [26-09-15-0658] [auto-qb · WEB UI 优化计划](26-09-15-0658-webui-optimization-plan.html) — `webui-optimization`
