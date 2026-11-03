# 生产旁路诊断探针在测试里真跑外部命令

> 摘要: 生产失败路径上的「只进日志」诊断探针(端口占用者 `ss -ltnp` / `lsof` / PowerShell)在测试里会真跑外部命令 ⇒ Linux CI 的 sidefx 越界; Windows 本机的绿是被通知器守卫偶然遮蔽, 且报错归属到该 worker 最后跑的用例, 与肇事者无关
> 触发: sidefx 越界, POPEN, ss -ltnp, port_owner, describe_port_owner, 端口占用者探针, WebUIBindError, CI 红本机绿, xdist, teardown ERROR

### 只验异常文案的用例会把「旁路诊断探针」整条真跑一遍

- **触发**: 生产代码在失败路径上落「旁路诊断」(如 `WebUIModule.start` 在 `handle.started` 为假时调 `describe_port_owner` 打 INFO 诊断块); 用例为了验 fail-fast 文案/句柄, 直接驱动真实启动失败而不注入探针替身 —— 探针就一路真 `subprocess` 走到 `ss -ltnp`(Linux)/`lsof`(回退)/PowerShell(Windows)。
- **判别**: CI 收尾报「测试期出现 1 条越界的真实系统副作用」`POPEN ... !! ['ss', '-ltnp']`, 而本机 Windows 全绿。两个容易看错的点: ① 会话级 autouse 夹具的收尾错误**永远归属到该 worker 最后跑的那个用例**(CI 里是 `test_scope_audit_wiring`, 与肇事者无关 —— 别顺着该用例查); ② 本机的绿来自 `tests/conftest.py` 的通知器守卫按**命令名**拦 `powershell`(直接抛 `FileNotFoundError` ⇒ 探针降级 unavailable), 属**偶然遮蔽**, 不是「测试不跑外部命令」的设计保证。
- **处置**: 在用例里注入替身并保留一条「探针仍被调用」的断言 —— `monkeypatch.setattr("auto_qb.webui.module.describe_port_owner", probe)` + `assert probe_calls == [(host, port)]`; 前者消除真实外部命令, 后者钉住诊断接线(摘掉调用点或改成绕开该符号直接 import 时判红)。**不要**把 `ss` / `lsof` / `powershell` 登记进 `tests/sidefx.py` 放行清单: 探针结果只进日志、用例断言与它无关, 放行只是把副作用合法化并扩大盲区。跨平台口径随之统一: Windows 侧同类探测(`Get-NetTCPConnection` 合并查询)同样不需要登记, 因为测试里根本不该跑真实探针。
- **守阵**: 用例内探针替身调用断言(摘接线即红, 实测该形态可红); `tests/test_port_owner.py` 用 mock `subprocess.run` 精确钉住 argv(`ss -ltnp`)、三态降级与时间预算; `tests/sidefx.py` 会话级台账兜底。
- **复发**: 0 (2026-11-03 首记)

