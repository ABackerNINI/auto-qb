# state.json 30S 周期落盘迟滞 + journal armed 相位恒无文件: 过程断言取数面单点

> 摘要: state.json 30S 周期落盘迟滞 + journal armed 相位恒无文件: 过程断言取数面单点
> 触发: 磁盘账, jobs_on_disk, state.json 迟滞, 30S 落盘, journal 相位, armed 相位恒无, journal_of, 相位断言, 过程断言, 收缩断言, 组账断言, 成员详情端点, relocate.phase, wait_job_phase, 真机相位, maybe_flush, state_save_interval
**Refs:** memory-bank/testing/real-baselines/26-11-19-0330-real-rm04-sliceF.md, memory-bank/testing/real-baselines/26-11-19-0102-real-rm04-sliceE.md, memory-bank/testing/real-baselines/26-11-18-0648-real-rm04-sliceC.md, memory-bank/tasks/26-11-15-backend-relocate-refactor.md, memory-bank/pitfalls/testing/restart-transient-and-offline-cmd-window.md

## 本篇只回答

relocate 真机/集成用例对「相位 / 组账 / 成员收缩」做**过程断言**(armed/rewritten 等中间态的实时观测)时, 取数面选了 jobs_on_disk 或 journal_of 会结构性扑空或拿到陈旧值 —— 本篇钉住两个取数面各自的语义与「过程断言 / 终态等待」的正确分工。

### 磁盘账是 30S 迟滞面: 过程断言拿 jobs_on_disk 会拿到旧组账/旧相位

- **触发**: 用例经 `jobs_on_disk`(读磁盘 state.json 的 relocate.jobs)断言 armed/收尾窗的**中间态**(相位、组账收缩、成员在不在)—— 例如「收缩后断言组账已收缩」「armed 期断言账面零扰动」。
- **判别**: 断言值与产品实际状态不符且稳定不随时间收敛(30s 内): 磁盘账的相位/组账**滞后于产品内存账** —— 真落盘由 state 服务 `maybe_flush` 按 `state_save_interval`(配置端下限 30S, 0=关)周期负责, `relocate_mod._persist` 只写内存账(片F RM04-30 try1 实锤: 组账已收缩而磁盘账仍全员在, finalize face members_gone=False 假断言; 片E RM04-28 首跑旁证: 账面观测恒 None/陈旧)。
- **处置**: 取数面分工钉死 —— **过程断言**(相位/收缩/组账的实时面)走 live 面: ①成员详情端点 `GET /api/torrents/{hash}` 的 `relocate.phase`(产品快照内存值, 实时; E9 mover_of 同源, `views.py:_relocate_member` / `views_relocate.member_relocate` 单点); ②产品 WARNING 行(日志即时); ③chain 端点 finalize face(members_gone/note/phase)。**jobs_on_disk 只配终态等待**(done/finalized 落账稳定后等 flush, 容 30s 迟滞)。P4 判定账誊写成用例时必须连同取数面纪律一起誊(P4 run_exp.py:987 自注「state.json 的 job 相位随 state_save_interval 落盘, 有迟滞」)。另: R4 收缩判定拍本身还有拍频纪律(main_tick 必须 < sync_interval, 删除轮证据才必被判定), 见 real-baselines 26-11-18-0648 片C §03.2-1。

### journal 在 armed 相位恒无文件: 「job 仍 armed」类断言按 journal_of 取数结构性扑空

- **触发**: 用例用 `journal_of(case, job_id)` 断言「相位未变 / 仍 armed」—— journal 看起来像账, 于是按它取数。
- **判别**: armed 稳态下 `journal_of` 恒返回 None, 等待超时(片E RM04-28 首跑实锤: S3 自加 journal 锚结构性扑空 30s)。journal 是 **daemon/下线窗侧账**: 改写 settled 写 rewritten 相位、对账重建回写 armed 相位、收尾写 done —— 主循环在 armed 相位**不写 journal**, 文件根本不存在。
- **处置**: 按等待目标选取数面: ①「armed 相位等值」→ 成员详情端点 relocate 相位(实时面, 上条); ②「rewritten 态 / daemon 改写已落盘」→ journal 相位(`journal_of(...).phase == "rewritten"`, 与 daemon 改写账同面)—— 账面相位在窗内冻结于 armed、窗后合并与 VERIFY 同拍瞬态(互链 [restart-transient-and-offline-cmd-window.md](restart-transient-and-offline-cmd-window.md)), 不可作等待目标; ③evidence 双记 probe_phase(账面)+ journal_phase(改写账)如实留证, 不混用。片G(26-11-19-0505)按本条纪律零复发。取数面速查表(两形态合并):

| 要观测什么 | 正确取数面 | 不要用 |
|---|---|---|
| armed/收尾窗相位、收缩、组账过程态 | 成员详情端点 `relocate.phase` / WARNING 行 / chain finalize face | jobs_on_disk(30S 迟滞)、journal_of(armed 恒 None) |
| daemon 改写已落盘(rewritten 态等待) | journal 相位 | 账面相位(窗内冻结/窗后同拍瞬态) |
| 终态(done/failed/cancelled) | jobs_on_disk(等 flush, 容 30s 迟滞) | — |

- **守阵**: 无机检 —— 取数面选错是结构性扑空(超时假红), 片级记账逐片传承纪律(片G 已零复发)。
- **复发**: 0 (复踩时在此行追加「+N (日期): 为什么没命中」, 无复发可删本行)
