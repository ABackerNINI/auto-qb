# TMPDIR 坑 · 复发流水外迁(1 / 2+3 / 4→9)

> 摘要: `pitfalls/testing/tmpdir.md` 的早期复发逐条流水 —— 主文件顶到 pitfall cap(6,000)后按 skill 处置外迁(2026-09-27), 原位留指针; 正文**原样照搬**未改一字。
> 触发: TMPDIR, pytest-current, 复发, 外迁流水

- **复发**: 1 —— 2026-09-23 走提交流水线时, 预检的 pytest 闸门**没带 TMPDIR**, 又抛
  `PermissionError [WinError 5] … pytest-current`(rc=1)⇒ STOP。**为什么没命中**: 读过也知道要设,
  但只给**自己手工跑**的测试带了, 没意识到**闸门是配置里的另一条执行路径** —— 坑里记了
  "跑测试时要设", 没写"闸门也是跑测试"。⇒ 收口即上面的配置改动: **改配置比改记忆可靠**。
- **复发**: 2+3 —— 2026-09-25 两踩: `TMPDIR="$(cygpath -w /tmp)"` 前缀 ⇒ 指回 `H:\Temp` 照崩(AGENTS.md 已写
  「不要再手工加前缀」, 读了没照做); `cmd //c` 嵌套引号挑子集 ⇒ 路径/`-k` 表达式被原样传进 pytest。
  ⇒ 只走 `commands run test.*`; 挑子集 `test.one -- '<路径> -k "<表达式>"'`(整串加引号);
  bash 前缀 `TMPDIR='R:/Temp/auto-qb/tests'` 亦有效。
- **复发**: 4→9 —— 2026-09-25/26 共六踩, 同一根因: **把"单跑一条 / 单文件小跑"当轻量例外而绕开引擎**
  (裸跑 `uv run pytest <文件>` 三次、手拼 `TMPDIR=… uv run pytest <单测>` 两次) ⇒ 默认 `H:\Temp` 收尾同崩
  `PermissionError … pytest-current`(一次碰巧没崩, 但同属绕开引擎)。2026-09-26 又一踩: 修搜索报障时
  裸跑 `uv run pytest tests/test_web.py -k search` 崩 + 手拼 `TMPDIR=/tmp/...` 前缀(POSIX 前缀本 shell 不生效)
  + `--basetemp=.pytest-tmp` 指进仓库内(即上上条的"仓内 basetemp"坑)。**为什么没命中**: "读了没照做" ——
  AGENTS.md 与本文件都写着「一律走 `test.*`」, 动手时仍裸跑。⇒ **任何 pytest 一律**
  `commands run test.one -- '<路径> [-k "…"]'`; 带全新 `TMPDIR` 的裸跑仅作兜底。
