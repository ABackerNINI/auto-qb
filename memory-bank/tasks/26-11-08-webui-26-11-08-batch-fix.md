# 26-11-08-webui-26-11-08-batch-fix — 八件入池 issue 批量修复 (26-11-08 四批: webui 显示/契约 + relocate 建链/语义)

**Status:** In Progress
**Added:** 2026-11-08
**Updated:** 2026-11-08
**Summary:** 八件入池 issue 批量修复 (26-11-08 四批: webui 显示/契约 + relocate 建链/语义)
**Topics:** webui-26-11-08-batch-fix

## 本篇只回答

八件 26-11-08 入池 bug(4 webui 显示/契约 + 4 relocate 建链/撤销语义)如何分四批修复、各批评审发现如何处置、修后全量数字几何;各件领域结论以其 issue 档案「修复后补充」为单点,本篇只记派发结构与裁决留痕。

## 原始请求

1. <!-- wording:allow --> 用户 2026-11-08:先拆解任务,派子智能体分阶段依次实施 8 份 issue(26-11-08-1621 ×4 / 26-11-08-1620 / 26-11-08-1608 ×3);大任务拆小防子代理 O(n^2) token 消耗与进度丢失,关联小任务可合并;不并列执行;待拍板的先询问;主会话只委派总结不实施;开新本地分支,每步 `ship.commit --no-push`;新分支无远端故子代理免 sync;完成后同步到本地 develop 等提交指令;子代理异常失败 3 次停待人。

## 思考过程与决策

- 拆解:8 件按域分 4 批串行——批1 webui 显示/面板 3 件(dt02-crow/drawer-rows/kb-guard)、批2 webui 行为契约 2 件(awaitpoll/add-torrent)、批3 relocate 建链单件(high,独立)、批4 relocate 语义 2 件;每批 = 可写子代理实施 → 只读评审(本地分支按「无法核实」口径) → `review.check` 过检 → 修复 → `ship.commit --no-push`。
- 四项用户拍板(AskUserQuestion 2026-11-08):drawer 空值行=①条件 wide;_build_links 修法=①+③ 组合(建链幂等+回滚按 plan 全量);撤终态=①终态守卫拒撤;回搬 fire-and-forget=①接受并登记豁免。
- awaitPoll 件按 issue 自带证据裁决流程由子代理裁决,结论 B 无害(三调用面核对,fail 分支不可达/刻意上抛),行为零改动只固化契约注释+断言。
- 批3 评审核出 1 major(目录别名 skip 支盲 append 台账面翻倍复利,违黄金法则#1)——修为 append 前去重;守阵升级走 _stage_link 生产入口。批1/2/4 与接缝终审共 11 条 minor/major 全部过 `review.check` 后当场修(死 hash 锚 68ae5221→函数名锚、行号锚修前/修后口径统一等)。

## 实现计划

每批固定管线:①子代理读 issue 复验锚点→实施(含测试与 issue 回写 kb.status 翻 Done)→报告;②`review.pack --base <上批提交>` 生成评审包,按行数分档派只读 code-reviewer(>400 拆面串行);③主会话裁决相关性/严重度,`review.check` 逐字校验,发现回派原实施子代理修复;④`ship.commit --no-push`(Review: trailer 记账)。

## 子任务状态表

| 步 | 内容 | 状态 |
|---|---|---|
| 1 | 批1 webui 显示/面板 3 件 + 滚入 R4 文档评审 → d453f3e0 | Done(2026-11-08) |
| 2 | 批2 webui 行为契约 2 件(awaitPoll 裁决 B + addTagList helper) → 601d16a9 | Done(2026-11-08) |
| 3 | 批3 relocate 建链幂等+回滚全量(评审 major 去重修正) → dd6fe04a | Done(2026-11-08) |
| 4 | 批4 relocate 终态守卫+热启用 sweep+豁免登记(原 roadmap, 大重构后迁 architecture/hr-groups.md「已定案口径」) → acf5bfb0 | Done(2026-11-08) |
| 5 | 收尾: test.full 全绿 + 基线切片 26-11-08-2027 + 接缝终审(1 minor 已修) + rebase 大重构(42692a37) | Done(2026-11-08) |

## 进度日志

### R0 · 立档 (2026-11-08)

单会话完成全部分派:四批实施+评审+提交(d453f3e0/601d16a9/dd6fe04a/acf5bfb0)+收尾(test.full 全绿, 数字见基线切片 26-11-08-2027 / kb.baseline; 接缝终审代码面 0 发现、文档面 1 minor 已修)。八件 issue 全部 Open→Done;四批均在本地分支随本专题入库, 与 develop 的合流随后续推送管线走。
