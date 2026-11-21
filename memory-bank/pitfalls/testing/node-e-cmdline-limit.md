# node 探针 -e 内联脚本与 Windows 命令行长度上限

> 摘要: `node -e <整段探针脚本>` 在 Windows 触顶 CreateProcess 32k 命令行上限(WinError 206 文件名或扩展名太长), 探针越长越接近实爆 —— 电池脚本改走 stdin(固定小 `-e` 包装器 + `input=探针`), argv 形状保持不变。
> 触发: node 探针, node -e, WinError 206, 文件名或扩展名太长, CreateProcess, 命令行上限, node 电池, 测试探针, subprocess.run, 追加用例后突然全 battery 红

**Refs:** memory-bank/tasks/26-11-21-webui-traffic-window-head-trim.md

### node 探针改走 stdin 包装器形态(2026-11-21)

- **触发**: 前端 node 电池探针以 `subprocess.run([node, "-e", <探针脚本>, <js 路径>])` 调用 —— 探针脚本本体整段进 Windows CreateProcess 命令行(上限 32k 字符)。探针是只增不减的电池(每轮追加用例), 平时绿、某次追加后突然红。
- **判别**:
  · 失败栈落在 `subprocess.py` 的 `_winapi.CreateProcess` 且报 `FileNotFoundError: [WinError 206] 文件名或扩展名太长` = 命令行超长, 与被测 JS 无关;
  · 只在 Windows 实爆(Linux ARG_MAX 大得多)—— Docker testbed 里绿、Windows 侧红的探针失败优先怀疑本坑;
  · 2026-11-21 实爆点: 节拍电池追加 S21 用例时(探针已近 32k)。
- **处置**:
  · 电池脚本走 stdin: argv 位固定为小包装器 `_NODE_STDIN_WRAPPER = "eval(require('fs').readFileSync(0,'utf8'))"`, 探针经 `subprocess.run(..., input=<探针>)` 送 stdin —— 包装器形状恒定不随探针增长; 探针内 `process.argv[1]` 契约不变(图表路径仍 argv[1], `node -e script extra-arg` 与 `-e wrapper + input` 的 argv 形状一致);
  · 注意: 纯 `node -`(stdin)会把 `process.argv[1]` 占成 `-`, 破坏探针的 argv[1] 契约 —— 必须用小包装器形态;
  · 探针体内禁顶层 `return`/顶层 `await`(eval 作用域 SyntaxError; await 收进 async IIFE);
  · 本仓已落地样板: `tests/test_webui_static_dom_panel_traffic.py` 13 处调用点 + `_NODE_STDIN_WRAPPER` 常量, 新探针照抄该形态, 不要回潮 `-e` 直内联。
