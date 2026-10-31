# 基线 · 1742 passed + 3 skipped —— ship.commit 消息文件「消费即删」轮(命令包, 不触主程序)

> 摘要: activeContext 切片 26-09-27-1812: `.git/COMMIT_MSG_AI.txt` 改「消费即删」—— commit.py
> 在 ref 三处核对通过后自动删除约定路径的消息文件(失败路径保留 / 显式非约定路径不删 /
> 删除失败只警告), 治「固定路径残留旧消息被 agent 误读」。本轮只动 .commands/my-commit-flow/
> 与 AGENTS.md, 主程序零改动。
> 数字取自提交前实测(`commands run test.full`, 基线 origin/develop @ cbc4b80)。
> 基线时间: 2026-09-27 18:12
> 档案: memory-bank/activeContext/26-09-27-1812-commit-msg-consume-delete.md

- **测试增量**: 命令包侧 +3 —— scripts/test_commit.py 新增
  test_message_kept_on_commit_fail(commit 失败不消费) / test_message_kept_on_verify_fail
  (ref 核对失败保留现场) / test_explicit_message_file_kept(--message-file 非约定路径不删);
  另 3 个成功路径用例补「消息文件已删」断言。主程序测试零增量。
  该包测试不在 testpaths(tests/) 收录范围, 数字走 `test.pkg`(73 passed)单独验证;
  test.full 数字与本轮无关仅作零回归凭据。

TOTAL 1742 passed + 3 skipped / 91%(11691 语句 / 852 未覆盖, test.full 25.6s)
对比前基线(26-09-27-1737): 1742 passed + 3 skipped / 91%(11691 语句) —— 完全持平, 零回归。
覆盖率口径见 [baseline.md](../../testing/baseline.md)。
