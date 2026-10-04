# 基线切片 26-10-04-1606 — kb.nav 可观测性: commands 引擎 stream 通道 + nav_server 精简 log/自动开浏览器 (+4 条守阵)

> 摘要: 用户报「`commands run kb.nav` 无 log、不知道端口、Ctrl-C 不好使」, 本轮: ①commands 引擎加
> `stream` 任务旗标(_config.py TASK_KEYS/Task/run.py 直连分支) —— stdio 直连终端、不吃 timeout、
> Ctrl-C 引擎层捕获转 `[stop]` 行 rc 0; ②kb.nav 标 `stream = true`; ③nav_server.py 精简 log
> (log_request 过滤: /api/data 30s 轮询与壳加载成功不上屏, 错误与静态映射留痕) + 启动自动开浏览器
> (`--no-open` 关) + Ctrl-C 收尾行 + `_utf8_stdout` 补 line_buffering(管道捕获下启动行不再滞留)。
> 守阵 +4: test_engine.py 3 条(stream 解析/直连 kwargs/Ctrl-C 干净停) + test_kb_nav.py 1 条(log 过滤)。

> 基线时间: 2026-10-04 16:06
> 档案: memory-bank/activeContext/26-10-04-0952-kb-nav-page.md (跟进轮)

**Refs:** memory-bank/activeContext/26-10-04-0952-kb-nav-page.md

- 分支: develop @ 3d1e1665 (+ 本轮未提交改动: .agents/skills/commands/scripts/{_config.py,run.py,test_engine.py} / .commands/kb/config.toml / .agents/skills/memory-bank/scripts/nav_server.py / tests/test_kb_nav.py / 本切片 / activeContext 切片 / pitfalls)
- 命令: `commands run test.full`(Windows, 单次采样 —— 耗时口径见 testing/baseline.md「必须带区间」)
- **实测 (Windows)**: **2508 passed + 4 skipped, 29.61s (引擎计 30.6s), 覆盖率 TOTAL 99%**
  (14677 语句 / 152 未覆盖 / 4964 分支 / 112 partial; 门槛 98% 达标)
- 相对上基线 (26-10-04-1039: 2471 passed + 4 skipped / 99% / 29.98s): passed **+37, 全部可归因**
  —— ①本文件 +4 (engine stream 3 条 + kb_nav log 过滤 1 条); ②+33 = 开工同步合入的 qB 流量存储
  v2 P1-P5 提交链 (f2437a0a..3d1e1665, traffic 三测 + web 共 +1133 行用例)。skip 集合不变
  (Windows 侧 4 条 POSIX 专属)。
- 冒烟: `commands run kb.nav -- --port 8799 --no-open` 启动行实时可见 (修 line_buffering 前
  管道捕获下完全不可见); `--gen-static` 产物 222962 bytes 正常。Ctrl-C 真机路径由引擎单测钉
  (KeyboardInterrupt → rc 0 + [stop]), SIGTERM 路径 timeout 6s 实测 [FAIL] exit 143 属预期。
