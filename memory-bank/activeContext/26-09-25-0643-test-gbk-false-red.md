# 测试假红修复: commands 引擎 GBK 回退

> 摘要: 用户令"修复测试假红"。目标即 2026-09-24 起记载的 `test_commands_engine` 两条 GBK 码页守阵
> (注入 `PYTHONUTF8=1` 的本工具 shell 恒红)。复现后红验**推翻"纯环境差异"旧定性**: PYTHONUTF8 只影响
> Python 解释器, 原生子进程仍按系统 ANSI 码页输出 ⇒ UTF-8 模式下 `_decode` 回退链退化
> `("utf-8","utf-8")`, 中文静默变 U+FFFD —— **一半是真缺陷**。三件修: ①引擎 `_local_codepage` 改
> `ctypes GetACP`(win32, 不吃 UTF-8 模式); ②两条守阵码页钉在 `_local_codepage` 接缝(monkeypatch →
> cp936, 跨机器确定性; GBK 字节在 cp1252 下也能"解成功"成乱码, 不钉缝非中文环境照样红); ③新增防回潮
> 守阵 `test_local_codepage_ignores_utf8_mode`(仅 win32+UTF-8 模式有判据, 打回旧写法立即红, 红验过)。
> 全量 **1580 collected: 1579 passed + 1 skipped**(耗时 14.3/20.9/21.2s, TOTAL 91%: 10809/789/3582/326)。
> KB 已回写: pitfalls/testing/patching.md(条目改"已修"定性) · testing/baseline.md + baseline-history.md。
> **已入库 `a760da0`**; 本机无 Python/uv, 已装 uv 0.12.18 到用户目录并完成依赖同步
> (收录为 env.sync, 经 commands 引擎跑)。
> 最后活动: 2026-09-25 06:43
