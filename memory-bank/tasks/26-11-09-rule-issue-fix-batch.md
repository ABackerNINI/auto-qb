# 26-11-09-rule-issue-fix-batch — issue 修复批: regex 尾换行双修 + cooldown 浮点 0 + 评审闸门二进制绕过

**Status:** Done
**Added:** 2026-11-09
**Updated:** 2026-11-09
**Summary:** 四 issue(1923×3+1701)三阶段串行修完翻 Done: regex 尾换行改 fullmatch / cooldown 浮点 0 谓词扩 float / 闸门 0 行带 trailer 走基比对;分批评审+接缝终审零 blocker, 全量绿, 三笔提交合回 develop
**Topics:** rule-issue-fix-batch

## 本篇只回答

四个计划外 issue(26-11-08-1923 系列×3 + 26-11-08-1701)按什么口径修、怎么分阶段委派实施与评审、各自修到什么程度。

## 原始请求

1. 先拆解任务,然后派子智能体分阶段依次实施修复 4 个 issue;大任务拆小防子代理 O(n²) token 消耗与进度全丢;关联小任务可合并;不并列执行防超并发,一个一个来;待拍板的先询问;主会话只委派总结不实际实施。
2. 开新本地分支,每步完成后 `ship.commit --no-push` 本地 commit;新本地分支无远端,子代理开工不需要 my-commit-flow.sync;全程本地分支工作,完成后同步到本地 develop 等提交指令。<!-- wording:allow -->
3. 子智能体提前停止可 SendMessage 续跑;非正常失败 3 次后停止任务等人工介入。

## 思考过程与决策

- **拆解**: 4 issue 分 3 阶段串行——阶段 1 合并两个同族 regex 尾换行 light issue(省子代理固定成本),阶段 2 cooldown 浮点 0,阶段 3 闸门二进制绕过;阶段 4 接缝终审 + 全量 + 合回 develop。
- **拍板 D1**(用户 AskUserQuestion 三问): cooldown 浮点 0.0 口径选 A 谓词扩 float(非 issue 原建议的构造期包裹 ConfigError);闸门修法选 A 带 trailer 无条件比对基(非 numstat 折算/维持现状);_V4_DATE_RE 选改 fullmatch(非仅注明 strptime 兜底)。
- **批次锚点修正**: 阶段 1 首次 pack 用 cb9ae719 当基线偏宽,闸门实算打回——9d5d1984(入池提交)带 `Review-Skip:` 也是锚点,正确批 = 44 行;教训见坑档 pitfalls/git/review-trailer-line-parse.md。
- **复验纠错**: cooldown issue 触发面比 §01 记载窄(文件路径走 BaseLoader 标量全字符串,ConfigError 干净拒;破契约的是程序内 dict 路径);闸门 issue §02「tracked 二进制内容变更不动哈希」取证有误(diff 的 index blob 行会动基哈希),均在 issue 复验节修正。
- **评审拓扑**: 阶段 1 首批 465 行(含滚入的入池提交)>400 不可拆 → 派发 2(面 A 代码/测试 + 面 B 文档);阶段 2/3 全能档各 1;阶段 3 一条 minor(第 4 处声明指针漂移)当场修,复评轮 2 零 actionable;接缝终审零发现。

## 实现计划

- S1: alias_fs mount_point 与 _V4_DATE_RE 两消费端改 `re.fullmatch`(照 7d39da4c 修 _INFOHASH_RE 先例),各补尾换行回归测试,f42fe5db。
- S2: `_is_bare_zero` 扩 (int,float)(bool 先行排除)+ base.py cooldown 解析去 `str()` 包裹配套;0.0 视为不冷却、非零浮点照拒;四键口径核对零变化,ad5a628b。
- S3: check_review_trace decide() 首位加 `not REVIEW_LINE_RE.search(message)`,带 trailer 的 0 行批走全链基比对;衍生修复: HEAD 消息来源 0 行批静默让步(提交后复跑不对空批校验历史 trailer);声明面 4 处 + code-review SKILL.md「残余窗口」段同步,53cc9831。
- S4: 接缝终审 + test.full 全量 + 快进合回本地 develop。

## 子任务状态表

| 步 | 内容 | 状态 |
|---|---|---|
| S1 | regex 尾换行双修(1923-alias-fs + 1923-v4-date) | Done(2026-11-09) |
| S2 | cooldown 浮点 0.0 谓词扩 float(1923-cooldown-float-zero) | Done(2026-11-09) |
| S3 | 评审闸门 0 行二进制绕过口径 A(26-11-08-1701) | Done(2026-11-09) |
| S4 | 接缝终审 + 全量 + 合回本地 develop | Done(2026-11-09) |

## 进度日志

### R0 · 立档 (2026-11-09)

四 issue 全部翻 Done;三笔修复带 Review trailer 在本地分支逐笔提交后快进合回 develop;评审累计 检 3/3(修 1,均过 review.check),接缝终审零发现;全量数字见 kb.baseline;真机轨不触发(纯字符串校验/闸门逻辑,桩可验,无 qB 真执行与真文件系统面);`issues/_index.md` 超预算债务已转告(Open 区 76 条,留另场清理)。

**Refs:** memory-bank/issues/26-11-08-1923-bug-alias-fs-mount-point-regex.html, memory-bank/issues/26-11-08-1923-bug-cooldown-float-zero-contract.html, memory-bank/issues/26-11-08-1923-bug-v4-date-re-tail-newline.html, memory-bank/issues/26-11-08-1701-bug-review-gate-binary-zero-line-bypass.html, memory-bank/pitfalls/git/review-trailer-line-parse.md

- 2026-11-09 03:46 修复批收尾: 四 issue(1923x3+1701)三阶段串行实施+分批评审全过, 三笔带 trailer 提交(f42fe5db/ad5a628b/53cc9831)合回本地 develop, 接缝终审零发现, 基线切片 26-11-09-0345; 档案 26-11-09-rule-issue-fix-batch
