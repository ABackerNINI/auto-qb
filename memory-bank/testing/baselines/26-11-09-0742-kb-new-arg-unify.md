# 5,872 passed + 2 skipped —— kb.new 传参统一: 主键位置参数与 --topic 全族等价(issue 26-11-08-1131)

> 摘要: 5,872 passed + 2 skipped —— kb.new 传参统一: 主键位置参数与 --topic 全族等价(issue 26-11-08-1131)
> 基线时间: 2026-11-09 07:42
**Refs:** memory-bank/tasks/26-11-09-memory-bank-kb-new-arg-unify.md

## 验收数字

`commands run test.full` 2026-11-09 08:42 实测(本轮收尾终跑, 最终代码态 = 本批 + 同步进树的 f4221c14): **5,872 passed, 2 skipped in 154.85s**; 覆盖率 99% (TOTAL 26,153 语句 / 41 未覆盖 / 9,102 分支 / 53 未覆盖分支)。较基线 26-11-09-0653(5,869+2)净增 3 用例 = 本批新增 `test_new_doc_key_arg_unified_positional` 1 例 + pack 前置同步进树的 cb545741(torrents 快照 magnet_uri 掩码, issue 26-11-08-0043)自带 2 例; TOTAL 语句面含 cb545741(+1)与 f4221c14 死字段摘除(-1)。

## 本改动面

- `.agents/skills/memory-bank/scripts/new_doc.py`: 传参统一(issue 26-11-08-1131) —— 专题主键**位置参数与 `--topic` 两形态全族等价**: 删非 issue 族位置 slug 拒收分支(原「不接受位置参数」失败行); 非 issue 族 `args.topic = --topic or 位置参数`(同给异值 fail-fast 歧义拒, 同值幂等); issue 族位置缺省时 `--topic` 兼作 slug(位置给足时仍是 doc-topic 覆盖, W3 行为不变); docstring 用法行 / argparse help / 失败行文案同步(含 task 族领域枚举失败行形式中立, 评审 round1 minor)。
- `tests/test_memory_bank_cli.py`: `test_new_doc_issue_params_fail_fast` 的「其余族传位置 slug 拒收」断言翻正为异值歧义拒; 新增 `test_new_doc_key_arg_unified_positional`(位置单传 plan/baseline 可建 + doc-topic 断言 / 同值幂等 / 异值拒 / issue `--topic` 兼作 slug / issue 覆盖形态保留); 头部测试计划两处同步。
- `memory-bank/conventions/doc-forms.md`: 「创建/更新方式」表下新增「专题主键两形态全族等价」注记(表内 `--topic` 均可位置参数替代)。
- `.commands/kb/config.toml`: `kb.new` note 首段补传参统一事实(`commands show kb.new` 注意行即轻修面)。
- `--total` 多处示例核对(issue §03 顺带项): doc-forms 族表泛形 "N passed + M skipped" 与 `new_doc.py` help/失败行具体例 "3498 passed + 4 skipped(根)" 形态一致(字符串摘要非裸数字), 无需改。
- 评审: 批次两轮(全能档 1 派 ×2)修 1 minor 复评零 actionable + 收口接缝终审 1 派出 3 minor(note/注记口径半句互补不齐 ×2、基线↔档案互引缺失 ×1)当场修, 修复增量复评零 actionable; 引文过检累计 P=4/T=4, 修 4 入池 0。
