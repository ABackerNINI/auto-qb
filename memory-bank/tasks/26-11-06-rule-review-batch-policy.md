# 26-11-06-rule-review-batch-policy — 分批评审: 一批一评 + 提交闸门强制留痕

**Status:** Done
**Added:** 2026-11-06
**Updated:** 2026-11-06
**Summary:** 把 code review 的评审单元从「任务」改成「批」, 用提交闸门强制 `Review:` trailer; 依据是一场 10 次派发 / 56 条发现的对照实验, 它把 400 行从容量红线改判为产出密度选择。
**Topics:** rule-review-batch-policy
**Refs:** memory-bank/plans/26-11-06-0759-plan-review-batch-policy.html, memory-bank/reports/26-11-06-0723-report-review-capacity-experiment.html, memory-bank/testing/baselines/26-11-06-0818-rule-review-batch-policy.md

## 本篇只回答

code review 什么时候评、一次评多少、评过没有怎么被机器强制 —— 三件事的规则与机械面。

## 原始请求

1. 「code review 环节在一半会话中没有被正确触发, 需要优化引导以及添加强制闸门, 初步想法是加在 my-commit-flow 中, 需要在提交信息或基线或 task 等文档中留痕才允许提交。grilling」
2. 「一个大任务/计划应该在每步执行完就做 code review 还是所有步骤都执行完才做 code review, 哪个更好? 调研成熟的方案对比优劣。另外当前的小修豁免让一些值得 review 的逃逸了, 也需要纳入考量, 初步想法是取消小修豁免。重新 grilling」
3. 「Q1 C, agent 每次能验的行数应该远超人类, 先看看有没有权威数据, 另外之前的 skill 设计是按照人类来的还是 agent? 注意 skill 是给 agent 读的, 参考人类的数据是错误的做法; Q5 文档的改动其实也该审, 这两天实践中多次发现审核出文档问题。其余按推荐」
4. 「先跑实验, 几天是根据人类的能力来判断的, agent 不需要那么久。其余按推荐」
5. 「按 1/2/3 做」(报告 / 改 skill / 写闸门)
6. 「补一个计划文档, 将拍板都记录下来, code review 然后收尾」

## 思考过程与决策

- 病根不是疏忽, 是**结构性逃逸**: 豁免判据「立档阈值 4 条不命中」是判断题, 再叠加「中途提交不触发」——只要 agent 从不宣布收口, 就能连续几天不立档不评审。实测 skill 落地后 20 份档案 8 份零提及, 62 份切片 95 条 R 行只有 23 条含评审。
- 第二个病在 grilling 中被挖出: 「全部做完再评一次」对大计划结构性失效。mypy 计划收口 1495 行、假钟计划 3357 行, 是 400 行线的 3.7 / 8.4 倍; 现有「分面 2–3 代理」只按面切, 切完每面仍约 1100 行。
- 用户纠了一次方法论: skill 是给 agent 读的, 而原 `TIER_LIMIT=400` 的来源是 SmartBear/Cisco 的**人类注意力**研究。查证结论: 长上下文研究(Lost in the Middle / Context Rot / RULER)只给出「越长越差」的共识, **没有任何「评审多少行」的数字** → 只能自己做实验。
- 实验(10 次派发 / 56 条发现 / 0 条引文被弃)三条结论: 发现数 ≈ 派发次数 × 5.6, 与批次大小无关; 幻觉率不随批次变大上升(推翻事前假设); 大块不是少找几条而是**换了地方找**(有真值的 diff: 2 批召回 7/8, 1 批 0/8)。
- 16 条拍板 + 3 条被否方案全部记进计划 §04(D1–D16), 含两条被推翻/被取代的(D12 行数口径、原拟 `review_anchor` 配置)。

## 实现计划

1. 报告: 实验设计与数据落 `reports/26-11-06-0723`。
2. skill: `code-review/SKILL.md` 整篇重写(①触发 ②批次与容量 ③评审包 ④派遣 ⑤产出 ⑥checklist 20 条 ⑦留痕 ⑧降级); 连带改 `AGENTS.md` 收尾行与 `memory-bank/SKILL.md` DoD 第 0 步。
3. 闸门: `check_review_trace.py`(锚点法) + `review.trace` task + `.my-commit-flow.toml` 条目 + `commit.py` 注入消息路径与阶段标记。
4. msg_check: `Review`/`Review-Skip` 进正文合法标签集 + 数字提醒。
5. 测试: review 包 22 条(12 纯判定 + 10 端到端), commit 包 3 条(闸门守卫 / 空清单命中 / msg_check 标签)。
6. 分面评审(正确性 / 安全 / 测试缺口) → 修复 → 收尾。

## 子任务状态表

| 步 | 内容 | 状态 |
|---|---|---|
| S1 | 实验: 两 diff × 三档粒度, 10 次派发 | Done(2026-11-06) |
| S2 | 报告 `reports/26-11-06-0723` | Done(2026-11-06) |
| S3 | skill 重写 + AGENTS.md / memory-bank SKILL.md 连带 | Done(2026-11-06) |
| S4 | 闸门脚本 + task + 配置 + commit.py 接线 | Done(2026-11-06) |
| S5 | msg_check 标签整合 | Done(2026-11-06) |
| S6 | 测试(两包 + 守卫) | Done(2026-11-06) |
| S7 | 分批评审 + 修复 + 收尾 | Done(2026-11-06) |

## 进度日志

### R0 · 立档 (2026-11-06)

- 四轮 grilling 拍板 D1–D16(计划 §04 全表); 实验报告落地; S1–S6 实现完成, 两包测试与 test.full 全绿(见 kb.baseline)。
- 实现期踩到并修掉的三个真问题: ①实验快照放 `test-results/` 里让 `test_free_port` / `test_tmp_bootstrap` 的单点守卫判红(已移到仓库外, 坑档 `pitfalls/testing/repo-snapshot-in-tree.md`); ②闸门初次实现用「消息文件在不在」判复跑, 手工跑时会静默放行 → 改由 commit.py 注入 `COMMIT_FLOW_GATE_PHASE`; ③`match=[""]` 的闸门在纯删除提交上根本不跑(`present` 为空) → `gates_for` 改成空串即恒命中。
- 新闸门当场把本批判红: 1000 行 > 400, 按新规则走分面档。

### R1 · 分批评审 (2026-11-06)

- review: blocker 0, 修 10(4 major + 6 minor), 入池 0, 分面(3 子代理串行: 正确性 / 安全 / 测试缺口), 10 条发现全过 `review.check` 引文校验(零 refute)。
- 四条 major 全是**这条闸门自己的洞**, 也正好证明分面评审值得: ①合流复跑按「消息文件在不在」判, `--message-file` 的文件不被消费 → 假红, 改由 commit.py 注入 `COMMIT_FLOW_GATE_PHASE=post`; ②同一判据在「本笔无 trailer」时反过来漏判, 把 rebase 进来的远端提交算成本批; ③`match=[""]` 的闸门在**纯删除提交**上根本不跑(commit.py 传的是 `present`, 空清单)→ `gates_for` 改成空串恒命中, 否则删 500 行可零评审入库; ④锚点只扫最近 200 笔, 第 201 笔有 trailer 时静默退回 HEAD, 与「漏评提交滚进下一批」的连坐机制正相反 → 去掉窗口。
- 六条 minor: Review 段应在下限之后判(5 行小改不该被硬拦)、`core.quotepath=off`(非 ASCII 路径会被转义成不存在的路径)、未跟踪二进制按 0 行计、`--no-renames`(numstat 的 `a/{b => c}/d` 合成串绕开排除)、`review/config.toml` 与 `AGENTS.md` 的 skill 节号漂移(③→④、②→③、④→⑤)。
- 收尾期另修一处认领链单向(计划/报告/档案三件未互指), `test_docs_forms` 判红后补齐 `doc-refs`。

- 2026-11-06 08:10 分批评审落地: 闸门 review.trace + skill 重写 + 报告/计划; 分面评审 10 条(4 major/6 minor)全修; 两包测试与 test.full 全绿(见 kb.baseline)
