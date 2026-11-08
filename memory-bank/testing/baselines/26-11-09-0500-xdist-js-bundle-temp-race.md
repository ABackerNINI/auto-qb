# 5,857 passed + 2 skipped —— xdist bundle 竞态修复收尾基线(含 SyntaxWarning 远端同步)

> 摘要: xdist bundle 竞态修复收尾基线(含 SyntaxWarning 远端同步)
> 基线时间: 2026-11-09 05:00

## 验收数字

实测于 2026-11-09 04:5x, 树 = develop `38577658`(远端 15 笔已合流) + 本批未提交改动:

```text
TOTAL                                                26113     42   9082     54    99%
5857 passed, 2 skipped in 164.28s (0:02:44)
```

warnings summary 为空 —— 上一版 CI 的 `invalid escape sequence '\s'` 随远端 `2543a603` 落地后已清零。

## 本改动面

- tests: `webui_helpers.py`(`bundle_file` 落点带 `os.getpid()`)、`extension_proxy_support.py`(`background_bundle` 同修)、`test_webui_static_r4_node_batteries.py`(head 探针同修)—— 三处 xdist 共享临时脚本截断竞态收口;`test_webui_static_r4_static_batteries.py`(守阵 `test_bundle_file_is_process_private` + 测试计划条目);`test_extension_proxy_page_fetch.py`(守阵 `test_background_bundle_is_process_private` + 测试计划条目);head 探针在用例内联断言 pid。
- 知识库: `pitfalls/testing/parallel-run.md`(新坑条)、`tmpdir.md`(复发 +1)、issue 26-11-08-1955 翻 Done 并补「修复后补充」、本切片。
- 远端同步: `2543a603`(test_file_access.py docstring 加 `r` 前缀)已在树, src+tests+tools 547 个 .py `-W error::SyntaxWarning` 编译零命中。
- 环节: `dev.fmt` / `doc.caps` / `kb.check` 全过;定向 `-n 8` 与 ascii/文档守阵全绿后跑 `test.full` 本切片。
