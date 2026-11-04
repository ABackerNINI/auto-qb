# 26-11-04-memory-bank-code-review — 收口 code review 制度化: code-review skill + review 命令包 + 协议挂钩

**Status:** Done
**Added:** 2026-11-04
**Updated:** 2026-11-04
**Summary:** 已落地: 完整任务收口前固定跑 code review —— 规程住 code-review skill(八节, 双 hash 三件套), 机械面进 .commands/review 包(review.pack/review.check, 27 例测试), 触发挂收尾 DoD 第 0 步; 首跑评审闭环(3 分面 24 发现全修 + 二轮核验 24/24 真修), sync 子代理豁免改全 6 处。
**Topics:** memory-bank-code-review
**Refs:** memory-bank/plans/26-11-04-0554-plan-memory-bank-code-review.html, memory-bank/testing/baselines/26-11-04-0704-code-review-institution.md

## 原始请求

1. 初步拟定将 code review 作为收尾 DoD 前的固定动作: 完成某项任务后做一次 code review, 能派遣子智能体就派遣; 相关问题当场修, 不相关问题入池(scope guard); 「某项任务」指完整任务而非大任务的一部分(分步计划所有步骤做完才 review)。问: 写成 skill 还是加入现有 AGENTS.md 或现有 skill? 要求 grilling。
2. 调研指令: code review 的具体方法可以派子智能体调研成熟做法做参考。
3. 追加关注: 派遣子智能体时其上下文自动带 AGENTS.md, 可能尝试开工 sync 导致行号变化, 如何解决。
4. 追加关注: 整个过程中有没有可以脚本固化/辅助的步骤, 减少出错。
5. 「先写一个计划文档方便后面排障, 然后实施」—— 授权实施。

## 思考过程与决策

- 全程 grilling 15 题(Q1-Q14 + 机械化 Q15), 逐题拍板, 结论表见计划 §06(D1-D15): 计划路径 `memory-bank/plans/26-11-04-0554-plan-memory-bank-code-review.html`。
- 关键取舍: ①判断与机械分离(收口判定/相关性裁决留 agent; 引文校验/分档/基线自检落脚本); ②reviewer 只读 + 基线 hash 钉死(单一写线程在评审场景的延伸); ③子代理 sync 风险三层修复(AGENTS.md 豁免句治本 → 评审提示模板三件套固化 → 开工自检兜底, 子代理只看得到 AGENTS.md 所以豁免必须写在那); ④既有闸门不重复(红线/非ASCII/配置键同步已有机检, checklist 标注"闸门已兜底")。
- 两轮子代理调研支撑: 人工方法论(Google 七维度/OWASP/SmartBear 400 行上限/严重度四级) + AI 评审实践(逐字引文校验/风险分档/不报清单)。

## 实现计划

按计划 §04 五步, 每步验收判据在计划表内:

1. 新建 `.agents/skills/code-review/SKILL.md` 八节。
2. 新建 `.commands/review/` 包: `review.pack` / `review.check` 两 task id + 测试。
3. 改 `.agents/skills/memory-bank/SKILL.md` 两处(DoD 第 0 步 + 子代理豁免句)。
4. 改 `AGENTS.md` 四处(路由句 + 豁免句 + 三处漂移) + `doc.caps` 自查。
5. 收尾: 首跑 dogfood → 立档(已建) → `test.full` + 基线切片 → `kb.wrap`。

## 子任务状态表

| 步 | 内容 | 状态 |
|---|---|---|
| 1 | code-review skill 八节 | Done(2026-11-04) |
| 2 | review 命令包 pack/check + 测试(27 例全绿) | Done(2026-11-04) |
| 3 | memory-bank SKILL.md 挂钩两处 | Done(2026-11-04) |
| 4 | AGENTS.md 四处 + doc.caps 自查(7487/8000) | Done(2026-11-04) |
| 5 | 首跑 dogfood + test.full + 基线 + kb.wrap | Done(2026-11-04) |

## 进度日志

### R0 · 立档 (2026-11-04)

grilling 15 题定稿; 立档 + 计划文档 `26-11-04-0554` 落盘; 待实施。

### R1 · 实施 + 首跑评审 (2026-11-04)

- 实施五步全部落地: skill 八节 / `.commands/review` 包 / memory-bank 挂钩 / AGENTS.md 四处(7487/8000 字符) / 计划+档案。
- **首跑 dogfood**: `review.pack` 888 行 → 分面档 → 3 个分面子代理(正确性/安全/测试缺口)派 24 条发现(0 blocker / 4 major / 15 minor / 5 nit), `review.check` 校验 24/24 PASS 零幻觉引文; 裁决全部相关, 当场修 22 条(脚本加固 10 处、测试补至 27 例、skill 双 hash+契约扩展+收尾复核、sync 豁免改全 4 文件、计划指路 2 处), 2 条部分失真修正后落地(deps-upgrade 实无 sync 条款)。
- 修复 diff >100 行 → 按 skill 规则追加二轮评审: **24/24 真修 0 未修**, 另出 2 条 minor(计划节号 ④→③、skill relevance 枚举带"(初判)"缀) → 已修, 修复 diff 极小不需三轮。
- 回归: 包内测试 27/27 绿; `review.pack` 冒烟正常(1071 行→分面)。

### R2 · 测试文件重写与终态复验 (2026-11-04)

- 上一编辑轮的输出污染(多处注入无关词)损坏了 `test_review_pkg.py`(内容截断且断言语义错误), 已整体重写并三重校验(ast 语法 / 注入词扫描 / 实跑): 27 例全部还原(含一轮评审要求的 R/D 分支、缺闸门降级、窗口边界、stdin、根外拒绝、非 UTF-8 兜底、行注入、rc 语义)。
- 同时撤回超范围改动: 曾为绕 `tests/sidefx.py` 给脚本加的 `REVIEW_GIT` 覆盖已删除 —— 该冲突只出现在「把 `tests/` 与 `.commands/review` 合并进一条 pytest」这种错误用法, 真实闸门(`test.pkg.scoped` / `test.full`)单点收集不会触发; 已在测试文件头写明运行边界。
- 终态复验: `test.one -- .commands/review` 27/27 绿; `test.pkg.scoped` 27/27 绿; `test.full` **5127 passed + 2 skipped**、TOTAL 23893/212/8158/167/99%, 与基线切片逐位一致(切片已补记 08:25 复测)。

- 2026-11-04 08:25 测试文件污染重写 + 超范围改动撤回; 27/27 双路径绿; 全量 5127 passed 与基线逐位一致
