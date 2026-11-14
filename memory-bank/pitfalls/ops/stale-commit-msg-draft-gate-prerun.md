# 残留 COMMIT_MSG_AI.txt 把 ship.gate 预跑翻进「按草稿对账」模式: review.trace 声明/实算不匹配假红

> 摘要: `.git/COMMIT_MSG_AI.txt` 是提交脚本「提交后自动删除」的草稿件 —— 上一笔提交后残留(跨会话/跨 clone 同步后遗留)时, `commands run ship.gate` 预跑不再走「略过消息依赖闸门」路径, 而是拿**陈旧草稿的 `Review:` trailer**(旧批的行数/基哈希)对账**当前待提交批**, 报 `评审留痕: Review: 声明 N 行 ≠ 实算 M 行` —— 看起来像本批漏评/错报, 实为残留文件假红。
> 触发: ship.gate 预跑, review.trace 假红, 声明 行 实算 行 不匹配, COMMIT_MSG_AI.txt 残留, 消息依赖闸门, when_message, 闸门预跑红, 评审留痕, 提交草稿残留

### 判别与处置

- **触发**: pack 前置跑 `commands run ship.gate`(code-review skill ③), 报 `review.trace` 的 `声明 <N> 行 ≠ 实算 <M> 行`, 且 N 对不上本批任何数 —— N 是**历史某笔批**的行数。
- **判别**: 看预跑输出有没有 `[预跑] 略过 1 条消息依赖闸门(消息文件不存在, 评审尚未发生)` 行 —— 没有这行而 review.trace 真跑了 = 消息文件在场; `ls .git/COMMIT_MSG_AI.txt` 在场即中招。再核归属: 草稿首行标题/`Review:` trailer 与 `git log` 近几笔比对, 对上某笔已入库提交即证陈旧残留(正常流程提交后脚本自动删除该文件; 跨 clone 同步/异常退出会留下)。机制单点: `.commands/my-commit-flow/scripts/gate.py` 的 when_message 过滤段(文件不存在才略过 review.trace; 文件在场则经 `COMMIT_FLOW_MSG_FILE` 递给子进程按草稿对账)。
- **处置**: 核实草稿归属已入库提交后备份到仓外(如 `H:/Temp/`)再删除 `.git/COMMIT_MSG_AI.txt`, 重跑 ship.gate 即绿(`[预跑] 略过` 行恢复, review.trace 回到「评审尚未发生」的正确略过态)。**别照失败行去「改对 Review: 行」** —— 那是让本批提前伪造 trailer, 数字对不上是设计行为不是本批的错。
- **别踩的坑**: ①把预跑红一律当「本批没评」而提前编 trailer —— trailer 的 `· 基` 要等 review.pack 出基哈希, 预跑时点根本还没有; ②跨 clone 工作区里残留草稿各自独立, 本 clone 同步进来的远端提交不会替你删本地残留。

实测(2026-11-15 06:2x, 本仓 clone2): 残留草稿属已入库的 2031ba16(trailer 179 行), 预跑报 `声明 179 行 ≠ 实算 29 行`; 备份删除后重跑 `闸门全绿: 命中 9 条 ... (略过 1 条)`。
