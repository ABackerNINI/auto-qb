# runner.cmd_guard 未传 skip_tags: guard 把 real-fake 计入「真实种子 N 个」并暂停

> 摘要: 真机开工自检 `real.guard`(runner.cmd_guard 路径)调 qB API 时没传 skip_tags 过滤, 我方 real-fake 假种子被计入「真实种子 N 个」并被暂停 —— guard 输出形似「现场被别人污染」, 实为自家种子; real.seed 内部那次 guard 调用传了 skip_tags 所以显示 0, 两处输出互相矛盾是本坑最快判别。
> 触发: cmd_guard, skip_tags, real-fake, 真实种子, guard 计数, guard 暂停, 真机开工, real.guard

## 本篇只回答

真机开工跑 `commands run real.guard` 时「真实种子 N 个」把自家 real-fake 假种子计入并暂停, 怎么判别、怎么处置。

### 「真实种子 1 个」但明明只造了自家假种子 —— cmd_guard 未传 skip_tags

- **触发**: 真机轮开工/中途跑 `real.guard`(runner.cmd_guard), 而该实例上有本轮(或上轮残留)的 real-fake 标签假种子 —— guard 拉种子清单时不按标签过滤, 假种子全被当真实种子点名并暂停(state 变 stoppedUP)。26-11-12 真机复测 P1/P2 两轮都撞(复发 2 次)。
- **判别**: ①输出行「真实种子 N 个」且 N 恰等于本机 real-fake 种子数(例: N=1, 名字 real-probe-l0.bin / g####.bin); ②同轮 `real.seed` 输出的 guard 行显示「真实种子 0 个」(那条调用链传了 skip_tags) —— 同一实例两处计数矛盾即中; ③种子被暂停为 stoppedUP/非开工预期态。
- **处置**: 看到该行先 `real.seed.list -- --port <port>` 核对种子标签归属, 确认全部 real-fake 就不是污染, 照常开工(被暂停的假种子对探针无影响 —— 探针只认 BT_backup hash 集); 修面 = runner.cmd_guard 调 qB API 处补 skip_tags=real-fake(与 real.seed 内 guard 调用同参), 属产品侧 test runner 改动, 走入池不就地修。
- **守阵**: 无机检(真机自检命令面); 纪律靠本条 —— guard「真实种子 N>0」先核标签再判污染。
- **复发**: 2 (26-11-12 真机复测 P1/P2 两轮都撞, 立档前无本条可命中 —— 计数供「下沉守阵」排序参考)

**Refs:** memory-bank/testing/real-baselines/26-11-12-0229-real-relocate-bt-backup-retest.md
