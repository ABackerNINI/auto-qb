# real.seed.clean 是整目录清空 .work, 不是「种子残留清理」—— clean 前先确认无待留证据

> 摘要: `real.seed.clean` 真实语义 = **整目录清空 tests-real/.work**(不止种子残留;「已清空」即其正常输出)—— 误判为「只扫种子残留」会把 .work 下全部测量证据(gitignored, shutil 直删不进回收站, git 不可恢复, memory-bank 无副本)连带清掉(2026-11-12 实际发生: S0/S5 原始测量证据与复用脚本全丢; 蒸馏数字因已誊写档案不受影响, 但原始证据自此不可复核)。同族第二坑: 复用既有测量脚本先跑后改, 输出路径指向旧目录会原地覆盖旧证据。
> 触发: real.seed.clean, seed.clean, .work, 测量证据, 证据丢失, 覆盖, results, 输出路径, 复用脚本, shutil, 清壳, 归档
**Refs:** memory-bank/issues/26-11-12-2345-chore-real-seed-clean-evidence-guard.html, memory-bank/tasks/26-11-11-webui-group-hash-ref.md (R3 节, 2026-11-12)

### clean 前先确认 .work 无待留证据(整树直删, 不可恢复)

- **触发**: 测量/压测收尾跑 `real.seed.clean --yes` 清理种子与目录壳。
- **判别**: 它清的是 **tests-real/.work 整树**(不只种子残留), 输出「已清空」是正常输出、不代表只清了种子; 目标面 gitignored + shutil 直删不进回收站, git 不可恢复, memory-bank 无副本 —— 删了就是永久丢。
- **处置**: 跑 clean 前先确认 .work 内无待留证据(原始测量 results/、复用脚本、state 等), 有就先搬走/归档再 clean; 蒸馏数字要在事前誊写进档案(誊写在案的数字不受目录丢失影响)。证据保护闸已落地(2026-11-13, issue 26-11-12-2345): clean 对 .work 顶层 seeds/rmNN 之外的内容自动拒跑(rc=1) —— 但 **rmNN 用例目录内**与 **--dir 显式指名的子树**仍会整清, 这两面的证据留存仍靠本条人工执行(先搬走/誊写再清)。**--dir 指名前先 ls 盘点**: 目标若不是本轮亲手建的目录, 先 `ls` 盘点其中非本轮所建的子目录/散件再指名; 「逐案 evidence 落 case 根」的旧惯例目录(rmNN case root)本身就是**历史证据沉积层** —— 更早轮的散件会沉积在里面, 整树清一次带走一批(片F/G 已按盘点纪律执行零复发)。
- **复发**: 1 (2026-11-19, RM04 片E R26 重跑轮: `real.seed.clean --dir tests-real/.work/rm04 --yes` 把 .work/rm04 整树清空 22 文件 83KB, 连更早轮散落在 case 根下的历史证据层(rm04_06/10/14-21 逐案 evidence/auto-qb log)一并清掉 —— 幸 20 份在 rm04-sliceA/prev-run-archive/rm04-evidence-old/ 有片A 归档副本, 真损失仅 2 份无文档引用散件(rm04_06_recovery_path.txt/rm04_19diag.log)。为什么没命中: 路由没到(坑档检索未跑), 且读档后没把「--dir 指名」与「先搬走」纪律连起来 —— 误以为 --dir 定点=只清本轮 footprint。增量面已并入上方处置行)

### 复用既有测量脚本: 第一步核对输出路径

- **触发**: 复用上一轮的测量脚本(只改参数/库形, 不改结构)直接开跑。
- **判别**: 脚本 OUT 指向旧输出目录时, 新一轮首跑会**原地覆盖**旧证据(2026-11-12 实际发生: S0 @5000 的 5 个 steady_*.json 被 S5a 首跑覆盖不可恢复; 关键蒸馏数字因档案已誊写未失, mtime 未动的其余证据不受影响)。
- **处置**: 复用脚本先跑后改之前, **第一步核对输出路径指向(或先 mv 旧证据)**, 再跑。
