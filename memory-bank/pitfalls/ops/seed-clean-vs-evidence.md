# real.seed.clean 是整目录清空 .work, 不是「种子残留清理」—— clean 前先确认无待留证据

> 摘要: `real.seed.clean` 真实语义 = **整目录清空 tests-real/.work**(不止种子残留;「已清空」即其正常输出)—— 误判为「只扫种子残留」会把 .work 下全部测量证据(gitignored, shutil 直删不进回收站, git 不可恢复, memory-bank 无副本)连带清掉(2026-11-12 实际发生: S0/S5 原始测量证据与复用脚本全丢; 蒸馏数字因已誊写档案不受影响, 但原始证据自此不可复核)。同族第二坑: 复用既有测量脚本先跑后改, 输出路径指向旧目录会原地覆盖旧证据。
> 触发: real.seed.clean, seed.clean, .work, 测量证据, 证据丢失, 覆盖, results, 输出路径, 复用脚本, shutil, 清壳, 归档
**Refs:** memory-bank/issues/26-11-12-2345-chore-real-seed-clean-evidence-guard.html, memory-bank/tasks/26-11-11-webui-group-hash-ref.md (R3 节, 2026-11-12)

### clean 前先确认 .work 无待留证据(整树直删, 不可恢复)

- **触发**: 测量/压测收尾跑 `real.seed.clean --yes` 清理种子与目录壳。
- **判别**: 它清的是 **tests-real/.work 整树**(不只种子残留), 输出「已清空」是正常输出、不代表只清了种子; 目标面 gitignored + shutil 直删不进回收站, git 不可恢复, memory-bank 无副本 —— 删了就是永久丢。
- **处置**: 跑 clean 前先确认 .work 内无待留证据(原始测量 results/、复用脚本、state 等), 有就先搬走/归档再 clean; 蒸馏数字要在事前誊写进档案(誊写在案的数字不受目录丢失影响)。保护闸(clean 前待留证据确认)已入池 issue 26-11-12-2345, 落地前靠本条人工执行。

### 复用既有测量脚本: 第一步核对输出路径

- **触发**: 复用上一轮的测量脚本(只改参数/库形, 不改结构)直接开跑。
- **判别**: 脚本 OUT 指向旧输出目录时, 新一轮首跑会**原地覆盖**旧证据(2026-11-12 实际发生: S0 @5000 的 5 个 steady_*.json 被 S5a 首跑覆盖不可恢复; 关键蒸馏数字因档案已誊写未失, mtime 未动的其余证据不受影响)。
- **处置**: 复用脚本先跑后改之前, **第一步核对输出路径指向(或先 mv 旧证据)**, 再跑。
