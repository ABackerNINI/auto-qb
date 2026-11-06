# 5468 passed + 10 skipped —— real.down 改走 WebAPI 优雅退出修复全量基线

> 摘要: real.down 改走 WebAPI 优雅退出修复全量基线
> 基线时间: 2026-11-06 06:16

## 验收数字

- 汇总行: **5468 passed + 10 skipped** in 145.78s(0:02:25, xdist 并行, TMPDIR 由 tests/_tmp_bootstrap.py 自举); 命令整体 148.0s, 1 warning。
- 覆盖率 TOTAL 表末行: **TOTAL 24538 stmts / 74 miss / 8396 branch / 41 partial / 99%**(Windows 侧覆盖闸 99.0, PASS)。
- 口径注记: 本轮新增 9 条真机轨安全守阵用例, `src/` 产品代码零改动, 覆盖率分母与上片一致。
- 差值对比: `commands run kb.baseline -n 2`。

## 本改动面

- issue 26-11-06-0448 清偿: `tests-real/runner.py cmd_down` 整段移除 PowerShell 强杀, 改走端口探测 → `guard.check_port` 镜像路径核验 → `Qb.shutdown()` WebAPI 优雅退出 → 等端口释放(超时 fail-closed, 不回退强杀); 抽出 `_port_open` / `_wait_port_gone`, 保留 `--dry-run` 与白名单定位。`tests-real/lib/qb.py` 新增 `shutdown()`(空体 POST), `_open` 的 GET/POST 判据由 `if body` 改为 `body is not None`, 既有读端点仍走 GET。
- 守阵: `tests/test_real_machine_safety.py` 新增 9 条(静态禁强杀字面量 / 6 条 cmd_down 行为 / `Qb.shutdown` 空体 POST 与默认 GET), 头部「## 测试计划」清单同步; 隔离加载 runner 时把模块自身的 `subprocess` 换成拦截器, 红验期间零真实外部进程。红验旧实现 8 failed(副作用越界 0), 修复后 13 passed。
- 验证补充: `commands run real.down -- --port all --dry-run` 输出已改为「经 WebAPI app/shutdown 优雅关闭」; 本地假 HTTP server 真实往返确认 `POST /api/v2/app/shutdown` 空体(Content-Length: 0)、`/app/version` 仍 GET; 未做真机关停实测 —— 测试实例全机共享, 避免打断并行 clone 的实测轮。
- 环境面: 本 clone uv trampoline 入口壳失效(已记坑), `pytest` / `yapf` / `coverage` 三包定点重装后恢复; 复发留痕见 `pitfalls/ops/venv-trampoline-clone-copy.md`。
- 收口评审不触发(计划内缺陷直接修, 立档阈值不命中); 未立任务档案, 本轮无提交动作。
