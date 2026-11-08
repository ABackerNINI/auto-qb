# 5,833 passed + 2 skipped —— test_file_access.py docstring 无效转义告警清零

> 摘要: test_file_access.py docstring 无效转义告警清零
> 基线时间: 2026-11-08 20:34

## 验收数字

`commands run test.full` 2026-11-08 20:31 实测: **5,833 passed, 2 skipped in 125.58s**; 覆盖率 99% (TOTAL 26,073 语句 / 33 未覆盖 / 9,058 分支 / 51 未覆盖)。纯 docstring 改动, 测试集合未变, 数字与基线 26-11-08-2009 一致。

## 本改动面

- `tests/test_file_access.py:289`: `test_mapped_unc_source_scandir_logical` 的 docstring 加 `r` 前缀改 raw string, 消除 `\\NAS\share` 中 `\s` 的无效转义 SyntaxWarning; 1 行 1 字符, 产品代码零改动, 测试集合未变。
- 验证: 改前 `python -W error::SyntaxWarning` 编译精确报 line 289, 改后同命令无告警且 AST 取出的 docstring 保真 UNC 双反斜杠; 全树 321 个 .py 逐一 compile, 无效转义命中 0; 单文件与全量均全绿; `commands run kb.check` 全绿。
- `memory-bank/issues/26-11-08-1841-chore-test-file-access-docstring-escape.html`: 复验留痕 + 修复后补充(实际修法 / 验证方式与测试数字), 状态 Open → In Progress → Done。
- 会话开工同步快进远端 9 笔; 首次全量两条 webui 静态 node 探针用例在 xdist 并行下偶发红, 单跑与重跑全量均全绿, 与本改动无关, 按范围守卫未修未入池。真机不适用(纯测试源码 docstring 卫生)。
