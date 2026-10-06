# my-commit-flow 输出契约 v3.1 — 步骤行(改写留痕)

> 摘要: v3「沉默即成功」一次成功只吐一行结果行, 但一次命令内部 HEAD 会被改写多次(`ship.commit` 最多三次:
> 提交自身 → 内部同步 rebase → 闸门复跑改文件后 amend), 结果行只给终值 ⇒ 执行者看到 hash 与印象不符
> (`同步成功 <hash>` 里 rebase 前后必然不同)就回头查原因。用户 2026-10-06 定调: **把中间执行步骤如实补齐**,
> 但「尽量精简、不要引入新的疑惑」。v3.1 补法 = **结果行逐字不动, 真改写 HEAD 的步骤在它上面各留一行
> `旧hash→新hash`**; 没发生的(齐平 / 本地领先 / 闸门复跑无改动)一律不报。改动面: 三脚本 + `_pipeline.py`
> 步骤登记器 + 两份守阵测试 + 包内与库内文档口径。
> 最后活动: 2026-10-06 10:12

**Refs:** memory-bank/tasks/26-09-28-commands-shipflow-output-contract.md, memory-bank/testing/baselines/26-10-06-1012-commands-shipflow-steps.md

## 现状

- **实现**: `_pipeline.py` 新增「步骤登记」段 —— `step(steps, text)` 登记 + `emit_steps(steps)` 打印,
  显式列表逐层透传(`run_sync(steps)` / `run_push(steps)` / `commit.emit(steps, line)`), 传 `None` = 不留痕。
  不用模块级全局缓冲(跨测试残留会互相污染)。
- **登记点**: sync 的 快进 / 生成物重叠后快进 / 分叉 rebase 重放 / 生成物重跑后 amend;
  commit 的 闸门复跑后 amend。**未登记**: 齐平、本地领先(未推送)。
- **顺序是显式编排出来的**: `_resolve_rebase` 只返回事实(`ok, 重跑处数, landed, amended`), 两行由
  `run_sync` 按发生顺序登记(rebase 在前、amend 在后) —— 初版把 amend 行登记在函数**内部**,
  打印出的箭头链就是倒的; 替身 `test_rebase_then_amend_steps_are_in_order` 钉住这个顺序。
- **`commit.py` 结果行唯一出口 = `emit()`** —— 全部 `print(结果行)` 收口到它, 任一处绕开该 hash 变化就没人解释。
- **文档同步**: 包 `README.md` / `config.toml` / `references/pipeline.md`(新增 v3.1 专节) / `ship/config.toml`(两条 note) /
  `AGENTS.md`(会话协议①与提交节) / `pitfalls/git/push.md` 与 `_index.md`; `kb.index` 重建 20 个生成物。
- **验证**: `test.pkg` 111 passed(my-commit-flow 单独 91 条); `test.full` 2676 + 4 / 99%(基线 `26-10-06-1012`) ——
  后者与上一条基线逐项全同, 因改动面根本不在 `tests/` 与 `src/`。
- **真机实证**: 收尾跑 `my-commit-flow.sync` 时另一半正好推了一笔且本地 `_index` 刚重生成过 ⇒ 生成物重叠自动化解,
  实贴输出 `同步: 远端领先 1 笔 · 重叠 1 处全在生成物 → 丢弃本地那份后快进 295bb226→c2e43cf9` +
  `同步成功 c2e43cf9 自动重跑生成物 1 处` —— 正是要消掉的那种「hash 变了却没人解释」。

## 关键决策

- **只认「改写 HEAD」这一条判据**: 曾给「本地领先(未推送)」也加了一行(理由是 `已同步` 怕被读成已推平),
  复核时按登记纪律②删掉 —— 该路径没改写 HEAD, 报它就是「跑了但什么都没做」的噪音, 会退回 v2 检查表的老路。
- **结果行逐字不动**: 步骤行只加在**上面**, 三条结果行模板(`已同步` / `同步成功` / `提交成功`)一个字没改,
  贴进回复与档案的值仍是一行。
- **失败时步骤行照旧吐**: 失败已自动回滚(结果行的 hash 是回滚后的 HEAD), 把「期间 tip 到过哪」摆出来,
  才不会让人怀疑回滚漏了东西。
- **相邻两步首尾相接**: 每个改写步骤同时给旧值与新值, 于是任意两次改写之间都接得上 —— 守阵
  `test_head_rewrite_trace_ends_at_result_hash` 校验「链尾 == 结果行 hash」与「上一步终点 == 下一步起点」。

## 未闭环

- **同日实证(本轮动机)**: 09:1x 那次 `ship.commit` 报「提交成功 aac3dcc5(未推送)」, 补 `ship.push` 后
  最终 hash 变 `295bb226` —— 当时只能在日志里写「以 verify-ref 的 hash 为准」把疑惑兜住;
  v3.1 之后这条路径会自己在 `推送成功 295bb226` 上面留一行 `rebase 重放本地 1 笔 aac3dcc5→295bb226`。
- `memory-bank/issues/_index.md` **cap 债务**(25,598 > 25,200)与 `activeContext/` **切片数债务**(92 > 70)都是
  **本轮之前就有**的, 未动 —— 按债务制转告用户另开会话清理。
- **`ship.commit` 侧仍是未验收的半条**: 本轮的步骤行只在真实 `my-commit-flow.sync` 上实证过;
  `commit.py` 的「闸门复跑 → amend」那一行要真机上再撞一次「提交后远端前移」才走得到。
