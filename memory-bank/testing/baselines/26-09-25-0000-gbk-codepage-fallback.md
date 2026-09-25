# 1579 → 1580 (+1) —— commands 引擎 GBK 回退修复

> 摘要: 失败 2 → 0; PYTHONUTF8 只影响解释器, 原生子进程仍按 ANSI ⇒ 码页回退真失效, `_local_codepage` 改 ctypes GetACP; 时分不可考; 当日序位第 12
> 基线时间: 2026-09-25 00:00

- ↑ 收集数 **1579 → 1580**(+1)、失败 **2 → 0**(2026-09-25 **commands 引擎 GBK 回退修复**): 注入
  `PYTHONUTF8=1` 的本工具 shell 里, `test_commands_engine` 两条 GBK 码页守阵恒红(2026-09-24 起记载为
  "已知假红, `env -u` 转绿")。本轮红验推翻"纯环境差异"定性: `PYTHONUTF8` 只影响 Python 解释器,
  原生子进程仍按 ANSI 码页输出 ⇒ UTF-8 模式下引擎码页回退**真失效**(回退链退化, 中文静默变 U+FFFD)。
  修三件: 引擎 `_local_codepage` 改 `ctypes GetACP`(win32); 两条守阵钉缝(monkeypatch `_local_codepage`
  → cp936, GBK 字节在 cp1252 下也能"解成功"成乱码, 不钉缝在非中文环境照样红); 新增防回潮守阵
  `test_local_codepage_ignores_utf8_mode`(打回旧写法立即红)。
  TOTAL **91%**(10809 / 789 / 3582 / 326 —— 语句 10905 → 10809 随快进合并 fda13cd → 1516bd6 的 20 个
  主线提交而来, 非本轮所致)。详见 [pitfalls/testing/patching.md](../../pitfalls/testing/patching.md)。

耗时: 并行 14.3 / 20.9 / 21.2s(3 次采样, 全部 test.full)。
