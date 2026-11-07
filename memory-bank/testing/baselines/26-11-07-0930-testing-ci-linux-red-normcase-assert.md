# 5622 passed / 2 skipped —— ci-linux-red-normcase-assert 收尾基线: test.full 5622+2

> 摘要: ci-linux-red-normcase-assert 收尾基线: test.full 5622+2
> 基线时间: 2026-11-07 09:30

## 验收数字

`commands run test.full` 实测 (2026-11-07 09:28, 138.3s):

```text
TOTAL                                                25499      5   8796     27    99%
5622 passed, 2 skipped, 1 warning
```

覆盖率门槛 99.5 过(`commands run test.full` 退出码 0; 精确百分比以该命令输出为准, 此处不另抄)。
相对上一切片(07:22, 5609+13)的增量与 skipped 13→2 都来自远端合流(dc6feb57 自带基线已是
5621+2); 本批对 `tests/` 净 +0 例(一条既有用例改断言, 不动收集面)。现存的 2 条 skip 是
「仅 POSIX 成立」的设计性跳过(`test_grouping_misc.py:219` / `test_web_hr_fs.py:267`, -rs 实核)。

包内脚本测试 `commands run test.pkg`: 本批零改动(纯测试断言修改, 未跑)。

## 本改动面

- `tests/test_relocate_exec_verify.py`: `test_under_alias_root_dual_criteria` 两条命中断言的期望值由
  写死的 Windows 折叠形 `"r:/media"` 改为 `ru._norm(root)`(平台中立)—— 生产码
  `relocate_units._norm` 跟随平台(`os.path.normcase`, Windows 折叠 / POSIX 恒等)符合 §3.3 设计口径
  不动; Linux CI 上 `posixpath.normcase` 是恒等函数, 写死小写盘符必红(本机 Windows 绿、CI 红)。
- 坑档: `pitfalls/testing/attachments/patching-form-path-api.md`(patching 形态④ 外迁原文) `复发` +1
  —— 这次方向相反: 生产码跟随平台是对的, 红在测试期望值绑了平台折叠结果; 修法是断言对
  `_norm(root)` 平台中立项。
- `memory-bank/` 索引/切片为 `kb.index` / `kb.wrap` 生成物。

