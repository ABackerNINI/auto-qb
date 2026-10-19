# 26-09-30-2112-memory-bank-cap-debt — cap 守卫改债务制 (WARN 不拦提交 + 独立清理会话)

> 摘要: cap 治理专题。守卫改造 2026-09-30 实施完成(除 AGENTS.md 外尺寸全降级为债务: 提交不拦、派生输出转告用户、清理另开会话; AGENTS.md 硬规定照拦), AGENTS.md 削薄已由 10-06 清理轮落地(6,853/8,000)。**2026-10-10 清理会话: 条数债务 125 > 70 清偿 —— 删 79 片留 46 片**(判据与覆盖去向见下), `SLICE_COUNT_LIMIT` 未抬、活跃片零删除。**2026-10-11 清理会话(用户令「清理 cap 债务」): 字符 cap 债务 5 项 → 0** —— 索引三件(issues 走**视图归档** `CLOSED_KEEP=60` + 全量归档索引落 `attachments/`; tasks / web-ui 类索引压渲染口径) + 手写两件按「切最老一半」外迁到 `attachments/`; 条数债务本就不超(64 ≤ 70)。判据与副产物见 [26-10-11-1745 切片](../testing/baselines/26-10-11-1745-memory-bank-cap-cleanup.md) 与坑档 [index-archive-view(索引条目数撑爆 → 视图归档)](../pitfalls/kb/index-archive-view.md)。**2026-10-19 清理会话: 条数债务 150 > 70 清偿 —— 删 90 片留 60 片**(冻结钉住/活跃档案/温片全保留; 49 片蒸馏复核全免蒸馏 —— 坑档纪律成熟后修复类切片全有归宿), 判据细化见下「债务判据速记」。
> 最后活动: 2026-10-19 23:00

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

- **2026-10-11 清理轮(字符 cap 债务 5 → 0)**: 开工 `doc.caps -- --strict` 报 5 项 ——
  `issues/_index.md` 31,196 / `tasks/_index.md` 25,974 / `pitfalls/web-ui/_index.md` 25,940 /
  `progress/implemented-webui.md` 23,251 / `tasks/26-10-08-test-mutation-audit.md` 56,960。
  按「先量无摘要口径」分三路(详见 [26-10-11-1745 切片](../testing/baselines/26-10-11-1745-memory-bank-cap-cleanup.md)):
  ①issues 侧无摘要口径 27,336 = cap **108%**(条目数撑爆)⇒ **视图归档**(文件不动, 只出索引);
  ②tasks / web-ui 侧无摘要口径仍 < cap ⇒ 压**渲染口径**; ③两件手写文档按「切最老一半」外迁。
  **未抬任何 cap、未调 `SLICE_COUNT_LIMIT`**。收口 `doc.caps` 0 债务 / `doc.links` 绿 / `kb.check` 全绿 /
  test.full **3124 passed + 4 skipped**(基线切片 `testing/baselines/26-10-11-1745-memory-bank-cap-cleanup.md`)。

- **2026-10-13 清理轮(用户令「清理cap债务」; 字符 cap 债务 3 → 0)**: 开工 `doc.caps` 报 3 项 ——
  `modules/webui-static-contract.md` 34,647 / `pitfalls/web-ui/drawer-switch-flicker.md` 16,813 /
  `testing/guards.md` 24,174 (条数债务 94>70 本会话不修, 治理政策未拍板不调)。三件按「触顶外迁原文到
  `attachments/` 留一行指针, 随迁相对链接整体上移一层」处置 —— 主档落 7,823 / 10,319 / 9,889 (≤ 50% 线);
  另 kb-nav-page 切片 13,988 撞 slice cap 蒸馏跟进轮九~十七进 `progress/implemented-tooling.md` → 5,675。
  收口 `doc.caps --strict` 0 债务 / `doc.links` 绿 / `kb.check` 全绿 / test.full **3192 passed + 4 skipped**
  (基线切片 `testing/baselines/26-10-13-0914-memory-bank-cap-debt-cleanup.md`)。

- **2026-10-19 清理轮(用户令「清理:切片总数 150 > 70」; 条数债务 90 片清偿, 150 → 60)**: 判据沿用 10-10 成例 + 机检判据细化三分(见速记 2026-10-19 补):
  ①**删除集 = 90**: 档案 Done/Dropped 且 ≥12h 的 41 片(其中 24 片先摘除 tasks 档案 `**Refs:**` 里的切片 token、空则整行删 —— docmap 声明方强校验目标存在, 不清即闸门红) + 无档案且 ≥5 天的 49 片(**蒸馏复核全免蒸馏** —— 逐片语义关键词 grep `progress/`+`pitfalls/`+`tasks/`, 全部已有专属坑档或同专题档案/报告/计划归宿; slug 字面搜索漏报率极高, 不得用它判覆盖)。
  ②**保留 60**: 冻结面钉住 16(基线 .md 真实 `](` 链接 ×2 / append-only 流水链接 ×4 / plans·reports·issues `doc-refs` ×10 —— 声明方冻结不可改, 切片必须留) + 活跃档案(In Progress/Open)22 + 近 5 天无档案温片 21 + 本专题片 1。
  ③收口 `kb.check`(主键 733 / 认领链双向闭环) / `doc.links` / `doc.caps` / `kb.active`(页脚 60 ≤ 70, 条数债务行消失) 全绿; test.full 数字见新基线切片。`SLICE_COUNT_LIMIT` 未动。两处超长切片(15-0728 19,375 / 16-0541 14,305)属字符债务, 随既有 4 项(doc.caps)另行清理。

## 债务判据速记(后续清理会话直接复用)

- 条数债务由 `commands run kb.active` 页脚现算(`SLICE_COUNT_LIMIT = 70`, `_common.py` 单点), 不拦提交; `doc.caps` 的债务组不含条数(它只管字符 cap), 所以会出现「doc.caps 报 0 债务而 kb.active 报条数超」的口径差。
- 清理动作 = 蒸馏进 progress/任务档案后删除, **不是调 cap**; 抬 `SLICE_COUNT_LIMIT` 等于把收口线推走, 未拍板不做。
- 删前逐片三查: 档案状态 / 真实 md 入链(解析到目录, 别只匹配文件名 —— 同名基线切片是最大陷阱) / 是否开放决策片。
- 2026-10-19 机检判据细化: 「真实 md 入链」只是机检面的一半, **声明方在不在 docmap 决定 Refs 是否强校验** ——
  ①冻结声明方(plans/reports/issues HTML `doc-refs`、基线 .md 与 append-only 流水的 `](` 链接) ⇒ 指向谁谁就得留;
  ②可编辑声明方(tasks 档案 `**Refs:**` —— gen_doc_map 只认首个 Refs 行 —— 与可编辑 md 的 `](` 内链) ⇒ 摘 token/改指后可删, 空 Refs 行整行删;
  ③纯文本提及(基线 `**Refs:**`、坑档/progress/slices 的 Refs —— `doc.links` 与认领链都不扫) ⇒ 容忍不动。
  逐片蒸馏复核用**语义关键词** grep progress/pitfalls/tasks/conventions —— slug 字面搜不准(用词不同漏报率极高, 本轮 49/49 免蒸馏全靠语义命中)。

**R1(2026-10-19 23:00):** 条数债务清偿 150>70: 删 90 片留 60(16 冻结声明方/链接钉住 + 22 活跃档案 + 21 近5天温片 + 1 专题片), 49 片蒸馏复核全免蒸馏(坑档/同专题档案/报告/计划已覆盖), 29 档案 Refs 摘除死 token; 收口 kb.check/doc.links/kb.active 全绿, test.full 数字见新基线切片
