# 重启恢复判据不能从外部现场反推「指令是否下发过」

> 摘要: 「先落账、后下发」的恢复点若按相位一律置 issue=False, 崩溃窗口(外部系统从未收到指令)在两处现场上与「发了没动静」同形 ⇒ 静默等到停滞超时误判失败; 判据必须靠账上「已下发」位分流, 且两条下发路径都要落账
> 触发: 重启恢复, 崩溃恢复, 崩溃窗口, setLocation 补发, move_issued, 恢复判据, 账上事实, 下发路径, _load_jobs, recover_exec_phase, 死代码判据
**Refs:** memory-bank/issues/26-10-30-0616-bug-moving-phase-issue-restore.html

### 恢复判据靠「现场同形」推断 ⇒ 该补发的不补发, 该等的不等

- **触发**: 给「账先落、指令后发」这类流程(先写 state/job 账, 再调 qB 等外部系统)加崩溃恢复。
  典型写法是在恢复点(`_load_jobs` 一类)按相位一律置 `issue=False`(「重启不要重发, 会排队/覆盖」)
  —— 这句话对「qB 还在搬」成立, 对「指令根本还没发出去」就是灾难: 现场是 qB 不在 moving + 目标侧
  无数据, 于是永远等不到搬运, 只在超时(本仓 `move_stall_timeout`)后按停滞误判失败。
- **判别**: ① 恢复点写「一律 False / 一律 True」而没有按现场分流 ⇒ 可疑; ② 问一句「若在落账与
  下发之间断电, 重启后靠什么知道指令发没发出去?」—— 答不出「账上有某一位」就是本条;
  ③ 现场 <b>不能</b>分辨这两种情形: 「指令没发出」与「发了但对面没动静」在外部系统侧完全同形,
  任何只看外部现场的判据都会把前者判成后者。
- **处置**: 在账上补一个**只记录事实**的位(`RelocateJob.move_issued`: 下发成功后置位并落盘), 恢复时
  用它把两种情形分开 —— 未下发 ⇒ 补发一次(此刻外部系统不在搬, 无排队/覆盖风险); 已下发 ⇒ 走现场
  三分流(`recover_exec_phase`: 仍在搬 ⇒ 只轮询 / 数据已到目的地 ⇒ 补做后续 / 都没有 ⇒ 交停滞判据,
  **不要**立刻判失败, 快照滞后会让「刚下发还没动」与真停滞同形)。
  ⚠ 落账点要**数清下发路径**: 「新建时下发」与「恢复后补发」是两条路, 只在其中一条落账, 另一条就会
  让下一次重启再把同一 job 当崩溃窗口重发 —— 本轮实测就是这么漏的(首跑新守阵立刻转红)。
  同理, 「恢复判据」写好了却没人调用也是白搭: 死代码不等于已接线, `grep -rn <函数名> src/` 结果只有
  定义处就该警觉。
- **守阵**: `tests/test_relocate_exec.py::test_restart_reissues_setlocation_when_never_issued`(崩溃窗口
  必补发) · `::test_restart_issued_without_evidence_keeps_polling`(已下发不重发不立刻失败) ·
  `::test_restart_recovers_to_moved_when_data_already_at_dst` · 反向底线
  `::test_restart_does_not_reissue_setlocation`(qB 仍在搬不许重发)
- **复发**: 0
