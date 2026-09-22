# 26-09-22-memory-bank-activecontext-conflict — activeContext 多 clone 冲突治理

**Status:** Pending
**Added:** 2026-09-22
**Updated:** 2026-09-22
**Summary:** activeContext.md 全体收尾必写 + 「最后更新」滚动栈同段重写 → develop 汇合高频冲突; 解法 = 按 clone 拆文件 + 生成式聚合索引 + merge-tree 只读预检, W1–W4 待拍板。

## 原始请求

用户 2026-09-22 23:20 提问:「分析如何解决多agent合作activeContext易冲突的问题」; 23:43 指令「产出计划然后提交」—— 产出计划文档(单文件 HTML, docs/plans/)并按「提交」口径 commit + push。

## 思考过程与决策

- **根因定性**: 不是 agent 手滑, 是结构必然 —— 一个所有 clone 的收尾 DoD 都必写的单文件, 最热写点(「最后更新」滚动栈)还集中在文件头同一段; 本质是「并行会话状态」被塞进「串行媒介(单文件 + 线性 git 历史)」。本环境(禁 rebase/stash、非快进+脏=必炸、合并后未触及文件可消失)把冲突处置成本放大到危险级, 详见 pitfalls/git/history-integration.md。
- **放大因素**: 写点重叠(滚动栈 = 每会话重写头部同几十行) × 高频(每执行轮收尾必写; 09-22 一天头部叠加 5 个时段状态) × 反馈滞后(push 被拒才暴露)。
- **现有防线评估**: 12 KB cap / 流水账禁令 / 先同步后开工 缩小的都是爆炸半径, 没有动写点重叠根因; collaboration.md「合并冲突交用户主导」是承认冲突必然并转嫁成本。
- **解法空间**: 三条正交路线 —— 写点并行化(拆文件) / 读点聚合化(生成物) / 写串行化(单写者); 五案对比 A 拆文件 / B 生成式聚合 / C 同文件分段 / D git 兜底(merge-tree 预检 + rerere; union driver 对滚动替换结构不适用) / E 单写者。
- **决策**: 推荐 **A + B + D**。A 消灭冲突源(clone-id 沿用工作区目录名 auto-qb/clone1/clone2/long-seeding, 不发明新机制); B 兜住「别人在干嘛」读点(生成物冲突解法 = 重跑, 与 tasks/_index、pitfalls/_index 同模式); D 做最后保险。C 治标; E 牺牲并行且 global 段本就低频, 不值得。
- **职责澄清**: activeContext 混了两种性质相反的状态 —— 全局项目焦点(低频共享)与会话滚动状态(高频 per-clone); 只有后者需要拆。
- **不碰的东西**: tasks/ 档案「不带时分、同天同专题必撞同路径」是故意设计的 add/add 查重信号(SKILL.md 明文), 保持不动; issues 认领状态继续走 Gitee 单一事实源, 不进 activeContext。

## 实现计划

计划文档(含目标结构、协议变化对照、波次、验收标准):
[docs/plans/26-09-22-2350-activecontext-conflict-plan.html](../../docs/plans/26-09-22-2350-activecontext-conflict-plan.html)

要点: W1 结构拆分(activeContext/ 目录 + 存根 + CAP_POLICY 新档 + check_kb_structure 纳入) →
W2 聚合生成(gen_active_index.py + test_memory_bank.py 新守卫) →
W3 协议接线(SKILL.md / AGENTS.md / collaboration.md / README 细路由) →
W4 可选加固(preflight merge-tree 预判 + rerere)。
**W1–W3 必须连续入库**(同批提交分笔连续推送), 避免双 clone 协议错位窗口跨同步周期。

## 子任务状态表

| 子任务 | 状态 | 说明 |
|---|---|---|
| W1 结构拆分 | Pending | activeContext/ 目录 + 存根 + cap 档 + 结构检查纳入 |
| W2 聚合生成与守卫 | Pending | gen_active_index.py + test_memory_bank.py 扩展 |
| W3 协议接线 | Pending | SKILL.md / AGENTS.md / collaboration.md / README 四处指针 |
| W4 预检加固(可选) | Pending | preflight.py merge-tree 预判 + rerere.enabled |
| 冲突演练(AC-3) | Pending | 双 clone 各改自己文件 → merge-tree exit 0; 旧结构对照组应报冲突 |

## 进度日志

- **2026-09-22 23:20–23:50 (问答 → 计划产出)**: 先按问答轮完成根因分析(读 activeContext.md / collaboration.md / SKILL.md / pitfalls/git/history-integration.md + git grep 检索); 用户指令「产出计划然后提交」后转入执行: 开工 ff-only 同步 9 提交至 `d4dea8b`(含 W5 src 布局重构), 工作区干净; 立档查重(本 clone + 跨工作区 ls)无同名 slug; 闸门①等价动作 —— 干净代码态跑全量 `uv run pytest tests -q` = **1189 passed + 1 skipped**(32.9s, 覆盖率 91%, TMPDIR 已设 R:/Temp/auto-qb/tests), 与重构前基线一致; 计划 HTML 落盘 docs/plans/26-09-22-2350-activecontext-conflict-plan.html(25.6 KB, dark 主题)。仅文档, 未改代码。
