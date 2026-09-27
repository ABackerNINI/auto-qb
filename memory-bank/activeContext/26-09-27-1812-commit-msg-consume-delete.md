# ship.commit 消息文件改「消费即删」—— 提交落稳后自动删除 COMMIT_MSG_AI

> 摘要: 用户报告 `.git/COMMIT_MSG_AI.txt` 固定路径 + 跨提交残留会让 agent 把上次提交消息当
> 现状误读, 令「改为提交完成后由脚本自动删除」。落地方案(消费即删): commit.py 新增
> `consume_message_file()`, 在 ref 三处核对**通过之后**删除约定路径的消息文件 —— 三个成功
> 出口全覆盖(全量 OK / --no-push OK / PARTIAL, 推送失败但提交已落稳时消息已消费);
> `git commit` 失败与 ref 核对失败**不删**(保留现场, 修好重跑还能用); 只删约定路径 —— 显式
> --message-file 指向别处的文件归调用方管; 删除失败只警告不翻退出码(提交已成功, 不骗重跑,
> 同 stdout 编码兜底教训)。效果: 文件存在 = 有待提交消息, 每次提交前必须重写, 旧消息不可能
> 被读到。该变更推翻计划 26-09-26-2345 的「残留无害(下次提交直接覆盖)」假设。
> 口径同步 4 处: commit.py docstring/help/报错 WHY · ship/config.toml note · 包 README S4 ·
> AGENTS.md 提交流程③(doc.caps 过闸, 但余量只剩个位数 —— 待办里挂了削薄)。
> 触发: my-commit-flow, ship.commit, COMMIT_MSG_AI, 消费即删, 消息文件, 提交协议
> 最后活动: 2026-09-27 18:12

## 状态

**Done**(消费即删已落地 + 回归绿 + 口径回写; 随本轮提交入库)。

## 待办(下一步从这里接)

1. **AGENTS.md 削薄**: doc.caps 建议留 10% 余量削到 7200, 本轮压缩措辞后仅勉强过 8000 上限
   (余量个位数), 下次收尾时顺手做。
2. **my-commit-flow.sync 远端真值探测疑似写死远端名**: 本 clone 远端叫 `origin`(Gitee 主线),
   sync 报「拿不到远端真值」但手动 `git ls-remote origin develop` 成功 —— 疑为脚本按 `gitee`
   探测, 待核实; 若属实属计划外缺陷, 应入池 issue 而非顺手改。

## 取证锚点(复核用)

- 基线 origin/develop @ cbc4b80(手动 ls-remote 核实齐平; sync 本身取远端真值失败见待办②);
  改动 5 文件: scripts/commit.py(consume_message_file + 调用点 + docstring/help/WHY) ·
  scripts/test_commit.py(+3 用例, 3 用例补文件已删断言) · ship/config.toml(note) ·
  包 README.md(S4) · AGENTS.md(流程③)。
- 测试: test.pkg 73 passed; test_commit.py 12 passed; test.full 1742 passed + 3 skipped /
  91%(25.6s) 与前基线 26-09-27-1737 持平(零回归 —— 不触主程序)。
- 判定依据: 新用例名见 scripts/test_commit.py 头部「## 测试计划」
  (test_message_kept_on_commit_fail / test_message_kept_on_verify_fail / test_explicit_message_file_kept)。
