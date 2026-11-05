# 5381 passed + 2 skipped —— 全量基线: 提交信息机检收口评审修复后

> 摘要: 全量基线: 提交信息机检收口评审修复后
> 基线时间: 2026-11-06 02:47
**Refs:** memory-bank/tasks/26-11-06-rule-commit-msg-review.md

## 验收数字

```
TOTAL                                                24483     60   8396     35    99%
5381 passed, 2 skipped, 1 warning in 156.66s (0:02:36)
```

- 口径: `commands run test.full`(coverage on); 1 warning 为既有告警面。
- 本切片 = 收口评审修复轮(3 子代理 17 条发现, 修 12 含 c2 降警告与 B3 旗类收敛; 语料终测硬拦 4/200)。

## 本改动面

- `msg_check.py`: c2 降警告(词前缀)、B3 仅对已知 gitmoji 生效、SLOT 行首锚定+hash 形态移出、d6 行内特征、a3 签名表修正、假名/谚文/CJK-A 走 b1、b4 明细截断、读取补重试。
- `commit.py`: 自动修写回补重试与干净失败行、违规明细前缀换 ASCII。
- `test_commit.py`: +6 例(旗类回归锚/前导空行/b4 截断/第二段 c2/--message-file 受检/白名单类型非法)与「机检先于闸门」金丝雀。
