# 26-11-09-memory-bank-kb-new-arg-unify — kb.new 各族传参统一: 位置 slug/topic 全族收敛

**Status:** In Progress
**Added:** 2026-11-09
**Updated:** 2026-11-09
**Summary:** kb.new 各族传参统一: 位置 slug/topic 全族收敛
**Topics:** memory-bank-kb-new-arg-unify
**Refs:** memory-bank/issues/26-11-08-1131-refactor-kb-new-arg-unify.html, memory-bank/testing/baselines/26-11-09-0742-kb-new-arg-unify.md

## 本篇只回答

kb.new 各族 slug/topic 传参方式如何统一(2026-11-08 实踩 2 笔 rc=1): 选哪个方向、`new_doc.py` 怎么改、哪些文档与守阵跟着同步。

## 原始请求

1. 用户(2026-11-09): 「认领 memory-bank/issues/26-11-08-1131-refactor-kb-new-arg-unify.html」
2. issue §01 内嵌用户拍板(2026-11-08): 「能彻底解决就统一各族传参方式, 统一是首选」—— 轻修(show 按族列签名)仅在统一不可行时考虑。

## 思考过程与决策

- **方向选型**(issue §03 授权实施时按兼容面定): 两个候选 ——
  - 全 `--topic`: issue 族的 slug 位置参数要改 `--topic`, 打破 create-issue skill 示例与最近肌肉记忆, 兼容面更差;
  - **全位置参数(选定)**: issue 族不动; 其余族**追加**接受位置参数(等价 `--topic`), `--topic` 各族继续认 —— 既有用法零破坏, 两种形态全族通吃, 是加法不是改法。
- **歧义裁决**: 非 issue 族位置参数与 `--topic` 同时给出且值不同 → fail-fast rc=1(fail-fast 法则); 相同值幂等放行。issue 族位置 slug + `--topic` 覆盖是既有合法形态, 不动。
- **连带面**: `doc-forms.md` 族表「创建/更新方式」、`.commands/kb/config.toml` 的 kb.new note、测试守阵(`test_memory_bank_cli.py` 拒收用例翻正 + 新增统一面用例)、`new_doc.py` docstring 用法行与 argparse help、失败行文案。

## 实现计划

1. `new_doc.py`: 非 issue 族收位置 slug(= topic); 两者同给异值 fail-fast; 同步 docstring/help/失败行。
2. 文档同步: doc-forms 族表、kb.new note、memory-bank skill 用法行(如涉)。
3. 守阵: 改 `test_new_doc_issue_params_fail_fast` 拒收断言为歧义拒收; 新增「位置参数全族可建」用例; 同步文件头测试计划。
4. 全量测试 + 基线切片; 真机不适用(纯命令面参数解析, 桩可验)。

## 子任务状态表

| 步 | 内容 | 状态 |
|---|---|---|
| 1 | new_doc.py 传参统一实现 | Done(2026-11-09) |
| 2 | doc-forms 族表 / kb.new note 同步(skill 既有示例仍合法, 无需改) | Done(2026-11-09) |
| 3 | 守阵翻正 + 新增统一面用例 | Done(2026-11-09) |
| 4 | test.full 全量 + 基线切片 | Done(2026-11-09) |

## 进度日志

### R0 · 立档 (2026-11-09)

- 认领 issue 26-11-08-1131(Open→In Progress, 双向补链); 复核 `new_doc.py` 取证锚点与 §02 一致; 方向选型定「全位置参数 + --topic 双轨」, 兼容面分析见思考过程与决策。

### R1 · 实施与收口 (2026-11-09)

- 2026-11-09 08:04 传参统一落地: 主键位置参数与 --topic 两形态全族等价(非 issue 族异值歧义拒, issue 缺位置 --topic 兼作 slug), 守阵翻正+新增统一面用例, 全量绿(见 kb.baseline), 评审两轮修 1 minor 复评零 actionable
- 实现: 删「不接受位置参数」拒收分支; 非 issue 族主键解析 `--topic or 位置参数`(同给异值 fail-fast 歧义拒, 同值幂等); issue 族位置缺省 `--topic` 兼作 slug(位置给足时仍是 doc-topic 覆盖, W3 行为不变); task 族领域枚举失败行形式中立(评审 round1 minor)。
- 文档: doc-forms「创建/更新方式」表下新增两形态等价注记; `.commands/kb/config.toml` kb.new note 首段补统一事实(即 issue §03 的 show 注意行轻修面); memory-bank/create-issue skill 既有示例全部仍合法, 零改动。
- 验证: 七形态冒烟(实踩 plan/baseline 位置单传转绿/原形态保持/歧义拒/issue 兼作 slug/领域校验照走) + 守阵 26 用例绿 + 全量终跑绿(见 kb.baseline); 真机不适用 —— 纯命令面参数解析, 无 qB 执行/真文件系统/进程面, 桩可验。
- 评审: 批次两轮全能档 1 派(修复循环扳机触发复评), round1 出 1 minor(task 族领域枚举失败行漏形式中立)当场修, round2 复评零 actionable; 收口接缝终审出 3 minor(note/族表口径半句互补不齐 ×2、基线↔档案互引缺失 ×1)当场修 + 修复增量复评零 actionable; 引文过检累计 P=4/T=4, 修 4 入池 0; 期间远端推进一次(f4221c14, 与本批零重叠), sync 后新锚复评通过。
