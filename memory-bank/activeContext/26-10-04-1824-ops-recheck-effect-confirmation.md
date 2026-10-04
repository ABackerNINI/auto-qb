# OPS recheck 假成功 — 已认领, 生效确认重设计计划待拍板

> 摘要: 认领 issue 26-10-03-1140(已完成种子 recheck 首跳误判「校验成功」)。复验(基线 ea2f2a51)确认三锚点仍复现, 并新确认两个同族缺陷: (b) 小种子校验在采样间隔内完成 → 永远见不到 checking → 600s 误判「启动超时」假失败; (c) `TorrentState.is_checking` 覆盖 `checkingResumeData`(qB 启动期简历校验), 直接补 `seen_checking` 门控会打开 qB 重启场景的新假成功路径。全库盘点确认 recheck 轮询是唯一「宣称成败却无证据门控」的判定点(WEBUI 真值落地 / reannounce 确认 / 跳检 R2 / 直查不回落红线四处为范本)。计划 [26-10-04-1824](../plans/26-10-04-1824-plan-ops-recheck-effect-confirmation.html)(Open, 待拍板)已立: 证据门控轮询重构(P0, verdict 纯函数 poka-yoke)+ R1 提交点实时复核(P1)+ 模式固化(P2), 场景适用性审计覆盖全部 10 个异步操作点。代码零改动。
> 最后活动: 2026-10-04 18:24

**Refs:** memory-bank/issues/26-10-03-1140-bug-ops-recheck-false-success.html, memory-bank/plans/26-10-04-1824-plan-ops-recheck-effect-confirmation.html

## 现状

- issue 已置 In Progress(用户指派认领), 复验行已写回; 认领链双向闭环(kb.docmap --check 通过)。
- 计划 §01 列了 5 个拍板点(D1 小种子残余风险接受 / D2 纯函数落点 checking_meta / D3 R1 live 纳入 + fail-closed / D4 拒绝状态 delta 证据 / D5 仲裁直查限 1 次)。
- 2026-10-04 晚: 三个子代理源码调研(官方 WebUI / forceRecheck 链 / WebAPI 端点面+社区)结论并入计划 §3.4 并留变更记录 —— 官方 WebUI 不宣称只反映; WebAPI 无「已受理/排队/回看」任何信号(completion_on·seen_complete 双向否定, log/main 无校验日志, queuedForChecking 已死); 排队种子同显 checkingUP(新增 S11, 批量无假超时); 重复提交 no-op 或重扫(D3 动机修正)。方案结构与 D1–D5 不变。

## 下一步

- 用户拍板(逐项确认或全盘)→ 按计划 §11 切分实施: P0(checking_meta 谓词+verdict → ops_mod poll 重构 → 测试 A/B/C/E/G)→ P1(R1 live + 测试 D)→ P2(坑档 + issue Fixed + kb.index), 收尾跑 test.full 数字回填基线切片。
