# 26-09-30-2112-memory-bank-cap-debt — cap 守卫改债务制 (WARN 不拦提交 + 独立清理会话)

> 摘要: cap 治理专题。守卫改造 2026-09-30 实施完成(除 AGENTS.md 外尺寸全降级为债务: 提交不拦、派生输出转告用户、清理另开会话; AGENTS.md 硬规定照拦), AGENTS.md 削薄已由 10-06 清理轮落地(6,853/8,000)。**2026-10-10 清理会话: 条数债务 125 > 70 清偿 —— 删 79 片留 46 片**(判据与覆盖去向见下), `SLICE_COUNT_LIMIT` 未抬、活跃片零删除。
> 最后活动: 2026-10-10 12:45

## 状态

- 计划文档: `plans/26-09-30-2112-plan-memory-bank-cap-debt.html` (doc-status **Done**); 档案: `tasks/26-09-30-memory-bank-cap-debt.md` (Status **Done**, 状态收口轮见其进度日志 2026-10-07 条)。
- **D1/D2/D3 全部拍板 (2026-09-30)**: AGENTS.md = 硬规定(不套 50%、不入债务体系、无止损线); D2 —— 切片条数阈值归债务通道(`_common.SLICE_COUNT_LIMIT`)。
- **2026-10-09 清理轮**(档案外迁 + tasks/issues 索引压截断): 见基线切片 [26-10-09-0832](../testing/baselines/26-10-09-0832-memory-bank-cap-cleanup.md); 当时明记「切片数 104 > 70 的条数债务仍在, 需另开清理会话」。
- **2026-10-10 本轮(用户令「存量 cap 债务: 基线切片数 125 > 70, 按规则修改」)**: `activeContext/` **125 → 46 片**(删 79), 判据沿用 26-10-06 清理轮成例三条件 + 两条硬约束:
  ①**硬约束一 —— 真实 md-link 入链不可删**: 全库扫描(链接目标逐个解析到真实目录, 区分同名基线切片)实测仅 5 片被 md 链接引用 —— 1 片被冻结基线链(`26-09-30-1007`, 基线是一次性快照不回写), 4 片被 append-only 流水 `implemented-webui-history.md` 链(2026-10-05 坑档判定 append-only 不可改)—— 全部保留; 其余 60+ 片的「引用」全是纯文本提及(`doc.links` 判据是相对链接存在性, 不扫纯文本), 删除不产生机检红。
  ②**硬约束二 —— 活跃状态不删**: 切片或其档案为 In Progress/Open 的 9 片全保留(热重载路线图被接替的例外: 计划已 Superseded, 状态事实经核实后按已完结处理)。
  ③**删除集 = 79**: 档案 Done 且 ≥12h 的 53 片(内容已在档案, 滚动状态完成使命) + 无档案且 ≥5 天的 26 片(蒸馏进 `progress/` 五个 implemented-*.md 后删除; 其中 kb-nav-page / shortcuts-toggle / drawer-merge-tabs / tracker-url 四片确认 progress 已有覆盖, 免蒸馏)。
  ④**保留 46**: 5 md-linked + 9 活跃 + cap-debt 专题片 + 近 5 天无档案的滚动状态片(26-10-10 当天片全留) + 26-10-10 清理轮自身。
- **蒸馏落点**: 无档案旧片按域压缩成 26 条新条目 —— core 7 / webui 5 / perf 2 / testing 9 / tooling 3(含 CI 计时口径、HR 守阵族、run_capture 看门狗等; 守阵与坑档单点均为事实源, 条目只留指针); 5 个 progress 文件全部仍在 20,000 cap 内。
- **链接改指**: 可编辑面 11 处(tasks 1 / progress 1 / cap-debt 片互链 1 / `docs/hr-online-verify-docs.md` 8 —— docs 不在守卫扫描面但属人读文档, 指向删除目标的链接改指档案/报告/progress)。冻结件(基线/报告/计划 HTML)零改动。
- 本轮改动全部随本提交入库; 收口机检 `kb.check` / `doc.links` / `doc.caps -- --strict` / `kb.active` 全绿(数字见基线切片)。

## 债务判据速记(后续清理会话直接复用)

- 条数债务由 `commands run kb.active` 页脚现算(`SLICE_COUNT_LIMIT = 70`, `_common.py` 单点), 不拦提交; `doc.caps` 的债务组不含条数(它只管字符 cap), 所以会出现「doc.caps 报 0 债务而 kb.active 报条数超」的口径差。
- 清理动作 = 蒸馏进 progress/任务档案后删除, **不是调 cap**; 抬 `SLICE_COUNT_LIMIT` 等于把收口线推走, 未拍板不做。
- 删前逐片三查: 档案状态 / 真实 md 入链(解析到目录, 别只匹配文件名 —— 同名基线切片是最大陷阱) / 是否开放决策片。
