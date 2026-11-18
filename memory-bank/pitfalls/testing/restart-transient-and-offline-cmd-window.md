# 重启后合并与 VERIFY 同拍: 账面 rewritten 毫秒瞬态轮询不可观测 + 下线窗命令回执被重连 connect 阻塞 ~29s/次

> 摘要: 重启后合并与 VERIFY 同拍: 账面 rewritten 毫秒瞬态轮询不可观测 + 下线窗命令回执被重连 connect 阻塞 ~29s/次
> 触发: 账面 rewritten, rewritten 瞬态, 相位瞬态, 轮询不可观测, 合并同拍, ACT_VERIFY 同拍, 下线窗回执, cmd_post_and_wait 超时, 回执 30s 未落, urllib3 重试, connect 阻塞, 断连稳态, 重启瞬态, D13, 镜像合并, wait rewritten 超时
**Refs:** memory-bank/testing/real-baselines/26-11-19-0102-real-rm04-sliceE.md, memory-bank/tasks/26-11-15-backend-relocate-refactor.md, memory-bank/pitfalls/testing/state-file-lag-and-journal-absence.md

## 本篇只回答

relocate 离线窗/重启链用例的两个「happy path 下结构性测不到/等不到」形态: ①「等账面相位 == rewritten」永远等不到(合并与 VERIFY 同拍, rewritten 是毫秒瞬态); ②下线窗内产品 WEB 命令回执延迟上界 ~29s+, 默认 30s 等待窗贴线必红。两形态都源自同一机制(主循环断连稳态), 片E RM04-28 R26 重跑轮三轮二分实锤。

### 账面 rewritten 是毫秒瞬态: 「等账面 == rewritten」的 wait 结构性超时

- **触发**: 离线窗用例在 daemon 改写后「等账面相位 == rewritten, N 秒」再布 rewritten 态探针。
- **判别**: wait 全程超时, evidence 里账面观测恒 armed/None; 而同窗 journal 已 rewritten。机制(代码链, 片E §03b.1 实证): 镜像合并(journal rewritten → 账面相位 rewritten)只在主循环 `_step_reconcile`(D13 协议, relocate_exec.py:947-948/965-968)做, 经 on_task_line→_advance 触发(relocate_lifecycle.py:527-553), **没有任何 daemon 侧写账面相位的路径**; qB 离线后主循环处断连稳态(qbmanager.py:623-644)不执行任何请求线只做重连判定 —— 任务线(含合并)整个下线窗不跑; 重启后对账表 all_at_dst && qb_up → ACT_VERIFY(relocate_units.py:1704)与合并在**同一拍**执行(_step_reconcile 顶部合并 → 表判 VERIFY → _step_verify 删别名+done), 账面 armed→rewritten→done 一拍内完成, 0.4s 轮询不可观测。
- **处置**: 「rewritten 态」探针/断言的取数面单点 = **journal 相位**(`journal_of(...).phase == "rewritten"`, daemon 改写账, 与 S4 rewrite_settled 同面); 账面相位只作双记如实留证(evidence probe_phase), 不可作等待目标。probe_phase 实测恒 armed 恰是「镜像冻结于 armed」这一真实用户面的证词, 不是探针坏了。若要测账面 rewritten 本体, 须走 verify 悬挂等异常路径(RM04-27/34 领域), 非 happy path。

### 下线窗命令回执延迟上界 ~29s: cmd_post_and_wait 默认 30s 贴线

- **触发**: 下线窗(qB 已离线、主循环断连稳态)内向产品 WEB 发命令(precheck-add / finalize-now / relocate-cancel 等)并 `cmd_post_and_wait` 等回执, 用默认 30s 窗。
- **判别**: 回执 pending 超时, 产品 log 里连接失败转换后零回执行; 机制: 命令线只在主循环**轮顶**跑(qbmanager.py:584), 而断连稳态的重连轮 `connect()` 被 urllib3 重试预算阻塞 ~29s/次 —— 命令入队正落在在途 connect 里就要等整段, 回执延迟上界 ≈ 29s + 下一轮(片E 实测两形态: 原 pass1 回执 24.5s 险过 = 贴线带运气; pass1b 差 ~1s 未落 30s 窗即红)。
- **处置**: 下线窗内一切命令回执等待**显式放宽**(建议 timeout=90, 3x 裕量); 「等 qB 在线态」类探针不受影响(在线态判定不走命令线)。前置 wait 的等待目标照上条选 journal 相位, 不要把回执窗浪费在结构性等不到的目标上。

- **守阵**: 无机检 —— 两形态都是「结构性超时假红」, 靠片级记账传承(片E R26 重跑轮修后 2 正式遍全 PASS, probe_phase/journal_phase 双记如实落盘)。
- **复发**: 0 (复踩时在此行追加「+N (日期): 为什么没命中」, 无复发可删本行)
