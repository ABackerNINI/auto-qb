# 2676 —— dev.e2e 收尾挂死修复提交后的合并态复验 (2be3fe79)

> 摘要: 上一条基线 [26-10-06-0605](26-10-06-0605-playwright-e2e-teardown-fix.md) 记的是**提交前**的
> 2662; 而 `ship.commit` 是**提交先行**(闸门跑在 rebase 之前), 推送时 `ship.push` 又 rebase 并入了
> 别的会话的 `825e5221`(S6 修复批, **含 Python 生产代码**) 与 `da7e7bbf`(更新TODO) ⇒ 合并态的数字
> 没被任何基线覆盖。本切片补上: 合并态实测 **2676 passed + 4 skipped / 99%**, 多出的 +14 全部来自
> 并入的远端提交, 与本次 e2e 收尾修复无关。
> 基线时间: 2026-10-06 06:19

**Refs:** memory-bank/activeContext/26-10-06-0508-playwright-e2e.md, memory-bank/pitfalls/testing/playwright-teardown.md

- 分支: develop @ **2be3fe79**(工作树仅"提交后回写"的文档更正未提交 —— 见文末)
- 命令: `commands run test.full`(Windows —— 耗时口径见 testing/baseline.md「必须带区间」)
- **实测 (Windows)**: **2676 passed + 4 skipped, 覆盖率 TOTAL 99%**, 单次采样 **75.06s**(引擎 76.9s)
  - 语句 16021 / 未覆盖 166 / 分支 5472 / partial 144。
- 相对上一条基线 [26-10-06-0605](26-10-06-0605-playwright-e2e-teardown-fix.md)
  (2662 + 4 / 15952 / 166 / 5444 / 144):
  passed **+14**, 语句 15952 → 16021(+69), 分支 5444 → 5472(+28), 未覆盖 166 → 166(±0)。
- ⚠ **这 +14 全部来自并入的远端提交, 不是本次 e2e 收尾修复** —— `825e5221`(S6: parse_size 表外单位
  回 None + freespace OSError 改抛 ExprError + `sys.torrent_count` 消灭全库拷贝)与 `2119931d`(S5)
  都是别的会话的批次, 本次改动(`e2e/*.mjs` / `playwright.config.mjs` / `.commands/dev/config.toml` /
  文档)**零 Python 改动**。
- **提交链**: 本地提交成功(hash 已随 rebase 重写、不可解析) → 推送时 `ship.push` fetch+rebase 到当时远端 tip `825e5221`
  ⇒ 重写为 **`2be3fe79`** 并推成功; `git ls-remote gitee refs/heads/develop` == 本地 HEAD。
- 旁证(同批核过): `dev.e2e` **14.8s / exit 0 / 4 passed (12.3s)**(合并态后未再单跑, 但该链路只碰
  `e2e/` 与配置, 不受并入的 Python 改动影响); `kb.check` 全绿; 命令漂移闸门 0 处。
- **未提交**: 本条切片 + 任务档案 / activeContext 的"提交后回写"更正(记提交 hash 与合并态数字)
  —— 提交 hash 只能在提交后才知道, 按本仓库惯例随下一次「提交」一并带上。
