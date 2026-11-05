# 平台差异 · PYTHONUTF8 假红原文(外迁)

> 摘要: `pitfalls/testing/patching.md`「本工具 shell 注入 `PYTHONUTF8=1`」节原文整体外迁(2026-11-05 压缩), 正文原样照搬, 标题降一级以避开坑档条目扫描。
> 触发: PYTHONUTF8, PYTHONIOENCODING, locale, cp936, GBK 回退, 码页, GetACP, _local_codepage, 假红

## ❗本工具 shell 注入 `PYTHONUTF8=1` —— "本地码页回退"假红(**2026-09-25 已修: 一半是环境, 一半真缺陷**)

- **触发**: 测试断言依赖 `locale.getpreferredencoding()` / 本地码页(GBK·cp936), 或跑 `commands run test.*` 时红。
- **判别**: 本工具会话的环境里注入了 **`PYTHONUTF8=1` + `PYTHONIOENCODING=utf-8`**(还有 `LANG`/`LC_ALL=C.UTF-8`)
  ⇒ `locale.getpreferredencoding(False)` 返回 **`utf-8`**、`sys.flags.utf8_mode == 1`, 而真机(未注入时)是 **`cp936`**。
  症状: `tests/test_commands_engine.py` 的 GBK 回退两条在本 shell **恒红**
  (`'������ 16 ������' != '已生成 16 个索引'`)。
  ⚠ **2026-09-25 修正旧结论**: "不是代码坏了"只对一半 —— `PYTHONUTF8` 只影响 **Python 解释器**,
  **原生(非 Python)子进程照样按系统 ANSI 码页输出**, 所以 UTF-8 模式下引擎的 GBK 回退是**真失效**
  (回退链 `("utf-8", locale)` 退化为 `("utf-8", "utf-8")`, 静默落 replace 变 U+FFFD)。
  守阵抓的是真缺陷, 不是纯环境差异 —— 环境只是让它现形。
- **处置(2026-09-25 已修, 全绿)**:
  ① 引擎 `run.py::_local_codepage` 在 win32 直接问系统要 ANSI 码页(`ctypes GetACP`), 不吃 UTF-8 模式;
  ② 两条守阵码页钉在 `_local_codepage` 接缝(monkeypatch → cp936), 任何机器/CI 确定性通过
  (GBK 字节在 cp1252 下也能"解成功"成乱码);
  ③ 防回潮守阵 `test_local_codepage_ignores_utf8_mode`(仅 win32 + UTF-8 模式有判据): 打回旧写法立即红。
  判这类红仍先看 `env | grep -iE "python|lang|lc_"`; `PYTHONUTF8=0` 复现真机形态。
  泛化: **"回退本地环境"的代码, 环境被工具 shell 改写时既可能是假红也可能是真缺陷 ——
  先问"被回退的真实对象吃不吃这个环境变量"再定性**。
