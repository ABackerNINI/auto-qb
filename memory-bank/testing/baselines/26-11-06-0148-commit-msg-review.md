# 5351 passed + 2 skipped —— 全量基线: 提交信息机检(msg_check)落地后

> 摘要: 全量基线: 提交信息机检(msg_check)落地后
> 基线时间: 2026-11-06 01:48
**Refs:** memory-bank/tasks/26-11-06-rule-commit-msg-review.md

## 验收数字

```
TOTAL                                                24475     57   8396     35    99%
5351 passed, 2 skipped, 1 warning in 160.77s (0:02:40)
```

- 口径: `commands run test.full`(coverage on); 1 warning 为既有告警面, 与本改动无关。
- 环境: 本 clone trampoline 定点重装(pytest/yapf, 见 venv-trampoline-clone-copy 复发行)后首条本机基线之一。

## 本改动面

- 新增 `.commands/my-commit-flow/scripts/msg_check.py`(提交消息三态机检: 10 硬拦 + 3 骨架位自动修 + 6 警告 + 白名单)。
- `.commands/my-commit-flow/scripts/commit.py` 接线(检查点在闸门前)、`_ship_config.py`(msg_check_allow 键 + 白名单 id 校验)。
- `test_commit.py` +16 例(纯函数面 + 接线面); 夹具默认消息改合规形态「✨ 测试」。
