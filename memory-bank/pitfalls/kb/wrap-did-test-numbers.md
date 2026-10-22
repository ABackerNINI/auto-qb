# kb.wrap 的 --did 不能带裸测试数字

> 摘要: `commands run kb.wrap --did "..."` 的一句话会同时写进切片 R 行(`**R1(日期):**` 前缀)与档案进度日志行, 两处都不匹配「带日期前缀的行」豁免; 句里带 `213 passed` 这类裸数字会被 kb.check 的 check_wording 判红(判据族 B, 只拦新增)。2026-10-17 当天两个会话各踩一次, 2026-10-22 再犯。另: 判红时打印的违规行取自**全量命中的扫描序末 N 条**, 常指向无关的存量件 —— 定位新增必须做 HEAD/工作区 `--list-numbers` 清单 diff。
> 触发: kb.wrap, --did, 裸测试数字, check_wording 判红, R 行不写数字, 收尾回写, 手抄数字判红位置, 末 N 条, 存量还是新增, 清单 diff 定位, 误判入池

**Refs:** memory-bank/tasks/26-10-17-webui-traffic-source-fixes.md

### --did 长句里顺手带进测试数字

- **触发**: 收尾时 `--did` 写成口语化长总结, 把「gtm 工具侧 213 passed」这类数字顺手带进句子(2026-10-17 21:17 实测, 同日 webui-delete-reannounce 会话已踩过一次但只记在当日日志、未升坑档)。
- **判别**: `commands run kb.check` 报 `[裸 passed 数字]`, 行号指向 activeContext 切片; 切片 R 行前缀是 `**R1(YYYY-MM-DD HH:MM):**`, **匹配不上**「带日期前缀的行」豁免(那条豁免救的是档案进度日志的 `- <stamp> <did>` 行首日期, 救不了 R 行句中数字); 修完切片行还要修档案进度行——kb.wrap 把同一句写了两处, 只改一处复跑仍红。
- **处置**: `--did` 只写量级/持平表述(「全域回归全绿」), 数字只进 `testing/baselines/` 新基线切片, 正文引切片文件名不抄数字; 写 --did 前先自问「这句里有没有 passed/失败数」。若已判红: 切片 R 行与档案进度行同源文本各改一处, 复跑 kb.check 转绿即可(改动不涉及索引, 不用 kb.index)。
- **复发**: 1 —— 2026-10-22 12:44 会话(`26-10-20-2233-dup-code-audit` R12): `--did` 写了「test.full 实测 3990 passed/10 skipped/覆盖率 99%」。**为什么没命中**: 本坑只登记在 kb 类索引里, 收尾跑 `kb.wrap --did` 时是「填一句话」的动作, 没回读本文件; 且 kb.wrap 的命令输出没提这条约束 —— 收尾动作不在开工路由的视野里(与 cap-counting 复发同因)。附带形态: 同一次 `kb.wrap` 还把这句写进 7 个 dup-code-audit 专题档案的进度日志, 那些行**行首带日期**被判据族 B 的日期行豁免救下(不判红), 所以只有切片 R 行一处报警 —— 修的时候 7 份档案也要一起改, 否则下次清理存量时这些数字会被当成新增。

### 判红位置可能指向**存量**件, 不能照着它找

- **触发**: 2026-10-22 14:37, `test_number_guard_is_green_on_current_kb` 报「手抄测试数字 395 处 > 冻结常数 394」, 紧接着打印的违规行是 `activeContext/26-10-22-0102-test-midnight-window-jitter.md:6` —— 一个**本轮没碰过**的存量切片。据此入池 issue 后核对才发现是误判。
- **根因**: `check_wording.collect_violations` 在超额度时只打印 `num_hits[-over:]`(**扫描序末 N 条**), 目的是"别刷屏", 但这 N 条是**全量命中的末尾**, 与"新增"无关 —— 新增的可能排在扫描序中间(本例真正新增的 `26-10-20-2233` 就排在 `26-10-22-0102` 之前)。按路径排序 `activeContext` 先于 `tasks`, 于是"末条"常落在 activeContext 里, 看起来特别像新件。
- **判别**: 不要信报的那一行, 直接做两份清单 diff —— `python .agents/skills/memory-bank/scripts/check_wording.py --list-numbers > now.txt`, 再 `git archive HEAD memory-bank | tar -x -C /tmp/headmb` 后用 `--root /tmp/headmb --mb-dir /tmp/headmb/memory-bank --list-numbers > head.txt`, `diff head.txt now.txt` 即为**本轮真正新增**的那几条(顺带给出总账: HEAD 数应等于 394)。
- **处置**: 只改 diff 出来的新增行; 存量命中在冻结额度内属债务, 按范围守恒本轮不动。**入池前必须先做这个 diff**, 否则会把存量债务误记成本轮问题。
