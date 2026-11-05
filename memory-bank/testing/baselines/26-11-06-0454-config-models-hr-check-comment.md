# 5456 passed + 10 skipped in 154.20s (TOTAL 24538 stmts, 99% cover, 74 miss) —— models.py 旧键兼容注释修正全量基线

> 摘要: models.py 旧键兼容注释修正全量基线
> 基线时间: 2026-11-06 04:54
**Refs:**

## 验收数字

- 汇总行: **5456 passed + 10 skipped** in 154.20s(0:02:34, xdist 并行, TMPDIR 由 tests/_tmp_bootstrap.py 自举); 命令整体 160.4s, 1 warning。
- 覆盖率 TOTAL 表末行: **TOTAL 24538 stmts / 74 miss / 8396 branch / 41 partial / 99%**(Windows 侧覆盖闸 99.0, PASS)。
- 口径注记: 与上基线(26-11-06-0427)数字不同源于开工快进 68 笔后的树不同(远端合流面), 非本改动引入; 本轮零新增用例、产品行为零改动。
- 差值对比: `commands run kb.baseline -n 2`。

## 本改动面

- issue 26-11-06-0306 清偿: 仅改 `src/auto_qb/config/models.py:204-205` 注释 —— 旧键表述由「兼容接受并等价迁移」改为「已随 schema v2 废除 / 仅迁移链一次性改写存量配置 / 校验层 sections.py 命中即报错 / 无常驻兼容层」; 行为、校验、schema 与测试零改动, `python -m yapf -d` 无格式差异。
- 收尾件: issue 报告两处状态 Open→In Progress→Done + 复验/实际修法留痕; `issues/_index.md` 与 `issues/attachments/_archive.md` 由 `kb.index` 重建; 坑档 `pitfalls/ops/uv-trampoline-broken.md` 复发 +1 并订正处置口径; activeContext 切片走 `kb.wrap`。
- 环境面: 本 clone `.venv/Scripts/pytest.exe` / `yapf.exe` 入口壳失效(已记坑), 删壳后按 `commands run env.sync` 的定点重装形态(--reinstall-package 指向 pytest/yapf 两包)重装, 重跑 `dev.fmt` 与 `test.full` 恢复正常; 完整命令见 `memory-bank/pitfalls/ops/venv-trampoline-clone-copy.md`。
- 收口评审不触发(立档阈值不命中 + 纯注释/文档改动); 未立任务档案, 本轮无提交动作。
