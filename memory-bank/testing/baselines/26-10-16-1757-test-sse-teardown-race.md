# 3483 passed + 4 skipped —— SSE 断流退订断言改有界等待(跨线程终态竞态)

> 摘要: 用户报 GitHub CI 报错 `test_api_events_sse_stream_lifecycle`(`assert 1 == 0`)→ 本机压满复现 + 定根因(跨线程终态被单点采样)+ 断言改有界等待 + 真回归红验 + 写入侧判据误报按样板收敛。生产代码一行未动, 只改 `tests/test_web_hr.py`。
> 基线时间: 2026-10-16 17:57

- test.full: 3483 passed + 4 skipped / TOTAL 17684 语句 245 未覆盖 6012 分支 180 partial / 98%(闸门过)。耗时两采样 189.9s(测试体 187.41s) / 195.9s(测试体 193.37s, 回写前同树首次采样 —— 两次采样同数)。口径见 baseline.md。
- 修复前后压测对照(忠实照抄用例体的 scratch 副本, 16 核起 24 进程 × 120 轮 = 2880 轮, 每进程 1 个忙线程; 未入库): 旧断言判红约 1.0%(30/2880, 仪器化轮更高)⇒ 新断言(有界等待)同载荷**零红**, 竞态命中率 2.1%~3.2%(60/2880 与 93/2880), 最长自愈 515ms ⇒ 定时取 5s(约 10 倍余量)。
- 红绿双验: 拔掉 `src/auto_qb/webui/server/routes/events.py` 生成器 `finally` 里的退订 → 用例判红(约 6.31s, 撞 5s 定时); 字节恒等还原(SHA256 ed3ffc33… 复现一致)后复绿 —— 有界等待没有把真回归放过。
- 兼办(用户拍板): `tests/test_web_hr.py` 被写入侧凭据判据整文件拦下(29 处鉴权头字典字面量, 误报)→ 按既有样板收敛成模块级拆写常量, 行为零变化(`test.one` 跑该文件全绿)。
- 环境注记: 本 clone 工具 shell 无 uv(按 `pitfalls/testing/no-uv-fallback.md` 首选前置 `C:\Users\<用户>\.local\bin` 后全线恢复); `TMPDIR=R:/Temp/...` 因 R 盘不存在自然回落 C 盘临时区; python 3.14.7-final-0(uv 解析)—— CI 失败侧是 windows job 3.13.16, 复现与验证在本机 3.14.7(竞态与调度器相关, 与语言版本无关: 机制在 anyio/starlette 侧)。
- Linux/macOS 侧未跑 —— 改动是断言写法与测试文件内的等价替换, 无平台分支; 本条 Windows 侧数字为事实源。

## 本改动面

- `tests/test_web_hr.py`: `test_api_events_sse_stream_lifecycle` 末尾断言改有界等待(`del resp` → `gc.collect()` → `while count and monotonic() < 5.0: sleep(0.005)` → 兜底 `gc.collect()` → 断言), 断言处注释写明竞态机制/实测数字/余量依据, 测试 docstring 同步; 另 29 处鉴权头字典字面量收敛成模块级 `_AUTH_HEADER_KEY` 常量(拆写, 行为零变化)。
- `memory-bank/`: 新坑档 `pitfalls/testing/cross-thread-teardown-assert.md` + activeContext 切片 `activeContext/26-10-16-1757-test-sse-teardown-race.md` + `pitfalls/testing/credential-shape-write-guard.md` 复发 +2(第三处不可写文件) + `pitfalls/testing/no-uv-fallback.md` 复发 +2。
