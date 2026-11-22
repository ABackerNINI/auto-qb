# 并行跑测试: 共享实例根下的聚合脚本截断窗

> 摘要: `pitfalls/testing/parallel-run.md`「共享实例根下的聚合脚本: `open("w")` 截断窗让 node 读到 0 字节」节原文整体外迁 —— `-n 8` 下多 worker 共用实例根 + 固定文件名, 截断写让另一个 worker 的 node 读到空串的根因与 process-private 落点处置。
> 触发: 聚合脚本, bundle_file, 共享实例根, TMPDIR, 截断窗, 空文件, node 电池, open("w"), os.getpid, os.replace, 并行 worker

### 共享实例根下的聚合脚本: `open("w")` 截断窗让 node 读到 0 字节(2026-11-08, 已修)

- **触发**: `-n 8` 下多 worker 同跑一域 node 电池(`bundle_file` 等临时聚合脚本); Linux CI 偶发
  `TypeError: Cannot read properties of undefined (reading 'methods')` @ `window.AQB_SHORTCUTS.methods`,
  单跑恒绿。
- **判别**: 栈里 `<anonymous>:5:34` ⇔ `new Function(src + …)` 的 **src 是空串**(100 行 src 报
  `:104:34`) ⇒ node 读到 0 字节。根因: worker 共用实例根 `TMPDIR` + 固定文件名, `open(…, "w")`
  截断写时另一 worker 的 node 正在读。
- **处置**: 落点掺 `os.getpid()`; **别用 `os.replace`**(Windows 替换被打开的目标会 `PermissionError`)。
  守阵 `test_bundle_file_is_process_private` 与 `test_background_bundle_is_process_private`。
