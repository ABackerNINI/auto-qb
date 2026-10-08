# test-webui-e2e-stub-fidelity-s7-memo — 认领复验 issue 26-10-08-0818: 判为重复报告, 关 Done

> 摘要: 用户指派「认领并修复」issue [26-10-08-0818](../issues/26-10-08-0818-test-webui-e2e-stub-fidelity-s7-memo.html)(e2e 存量 6 条失败: 桩保真 hr_link 入 JSON ×4 + S7 装饰记忆化 × 乐观 UI ×2)。认领后**先按建议复验锚点** —— 复跑 `commands run dev.e2e` 实测 **94 passed / 10 skipped / 0 failed (3.2m)**, 6 条失败全数复绿。逐条对账发现两条根因**均已在本件入池取证(10-07 13:36)之后、入池(10-08 08:18)之前**由两笔提交按建议修法修复: 根因 A = `312165f8`(FakeTorrent.to_dict 改按 `compat._SNAPSHOT_FIELDS` 快照分则, `hr_link` 不再进 JSON)、根因 B = `17dc0fc7`(`_decoCache` 加输入指纹 `_decoFpBuild`/`_decoFpHit`, 原地改 kind 后指纹失配自动重算)。**本会话零代码改动**, issue 关 Done(重复报告); 已回写 issue 状态日志 + S10 基线追记。
> 最后活动: 2026-10-08 08:39

## 已完成(详情见 issue 的状态日志与复验段, 不在此复述)

- **会话开工**: `commands run my-commit-flow.sync` → 已同步 `9ddd9193`; `commands run kb.active` 读切片。
- **复验(核心)**: `commands run dev.e2e` → 94 passed / 10 skipped / 0 failed。原 issue 预期 92; 多 2 条 = S10 后新增 `e2e/drawer-peers.spec.mjs`(双皮肤 @fast), 非根因相关。
- **对账**: `git merge-base --is-ancestor 312165f8 HEAD` / `... 17dc0fc7 HEAD` 均成立 → 两修复已在主线 develop; 两提交 message 逐条与本件 §06 建议修法一致(根因 A 建议①、根因 B 建议②的"键纳入指纹"一路), 无改道。
- **回写**: issue 26-10-08-0818 → `issue-status` Open→**Done** + 封面徽标/kicker/lede/footer 同步 + §07 补「复验 / 修复后补充」两段(含 94/10/0 实测数字 + 重复报告教训); `gen_issues_index.py` 重建(条目落入 Done 分区); S10 基线 `26-10-07-1336` 追加〔2026-10-08 追记〕(86/6 成历史, 后续 e2e 对照点改 94/10/0); `commands run kb.index` 重建 20 生成物。

## 正在进行

- 无 —— 本件已闭环。

## 未决项

- **教训待沉淀**(建议另立坑档或并入 `testing/assertions.md`): 入池/登记"存量失败"前必须先重跑锚点并记当场数字, 不要沿用更早切片的历史数字 —— 修复可能在取证与入池之间已落主线, 否则产出重复报告。本会话未新增坑档(遵循范围守恒), 由编排方决定是否立项。
- **activeContext 切片债务**: `kb.active` 报切片数 97 > 70, 不拦提交, 需另开新会话清理(本会话不修)。
- 未跑 `test.full` 出基线切片 —— 本会话**零代码改动**(只改 memory-bank 文档), 按口径不需新基线; e2e 数字已记入 issue 与 S10 基线追记。
