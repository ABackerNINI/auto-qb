# 26-09-26-memory-bank-baseline-slice-per-file — 测试基线切片化(单文件改每条一档)

**Status:** Done
**Added:** 2026-09-26
**Updated:** 2026-09-26
**Summary:** 实施计划 26-09-26-0529: testing/baseline.md 单文件 9 组 + baseline-history.md 两层流水改为 baselines/ 一条基线一个切片; 机制四触点 + 37 条存量迁移 + 引用回写 10 处; test.full 1640+1 持平, 守卫全绿。
**Topics:** baseline-slice-per-file
**Refs:** memory-bank/plans/26-09-26-0529-plan-baseline-slice-per-file.html

## 原始请求

用户:「实施计划 memory-bank/plans/26-09-26-0529-plan-baseline-slice-per-file.html」—— 把 baseline 存储从「单文件堆 9 组状态 + history 再垫两层流水」改造成「一条基线一个切片文件、脚本列最近 3 条、不设 _index.md」(用户三条定案 2026-09-26; 前案 v1 已否决并入计划 §00)。

## 思考过程与决策

- **机制面照搬 activeContext 母本**: 复用 `SLICE_FILE_RE` 命名 / 三行头 / cap 检查; 差异只有三点 —— 排序键换 `> 基线时间:`、默认截最近 3 条(基线是不可变快照, 截断语义成立)、无 `_index`(特性, 口径段写明不许补)。
- **`gen_docs_index` / `gen_doc_map` / `check_kb_structure` 对 `testing/baselines/` 免疫(读码证实, 计划 §07 风险解除)**: 三者分别只扫 `plans|reports/*.html`、四形态目录、含 `_about.md` 的自发现目录 —— baselines/ 无 `_about.md` 即天然不纳入, 无需豁免登记。
- **时分考据修正计划的一处 assigns(唯一偏离, 已双向记录)**: 计划把合流重测 / 1639 的时分定为「1700」(取切片前缀), 但 git 链证明该切片时钟偏移(其提交 d0c39bf 实为 03:54; 合并 d72a538/c8f98f4 实为 04:28–04:38)。**文件名沿计划定案保留 1700**, 切片头「基线时间」字段取考据值 —— 否则按(基线时间, 文件名)排序, kb.baseline 最新是重测而非 1641 定稿, 直接违反计划 §06 验收「最新为 1641 定稿」。1638 同理由计划的 0000+序位细化为 a497fba 的 04:25。偏差与理由在两枚切片摘要与本档案双记录。
- **kb.baseline 必须带 `<args>` 占位符**: 计划 §05 要求 AGENTS.md 写「排障 --all」, 而 commands 引擎对无 `<args>` 的任务拒收参数 —— 首跑即 STOP, 已补。**顺手发现既有缺陷(后经用户指令修复)**: `kb.active` 同样无 `<args>`, 故 `GEN_CMD_BY_SCRIPT` 里 `gen_active_recent.py → commands run kb.active --check` 的提示是一条跑不动的命令(与 2026-09-24「指错命令」守阵要防的形态同类, 但该守阵只校验任务存在与 run 列表包含, 判不出引擎拒参) —— 修复轮已补 `<args>`(见进度日志)。
- **存量迁移体量与 cap**: 计划按「存量最长条目约 0.9k」定 cap 4000; 实测 history 条目最长约 2.2k(H1+摘要+正文), 37 条全部 ≤ 4000, cap 不必校准。耗时聚合条按属主拆散进各轮切片; 无属主的孤儿采样(禁令解除回写 19.5/18.5s → 判明属 1596 态, 已随属主落档; 搜索分隔符 17.0/17.9s → 随 1601 两线合一)未丢弃。
- **验证期的两个真红与修复(均迁移必然后果, 非回归)**: ① `memory-bank/README.md` 3,100 > index cap 3,000 —— 回写行收紧(检索纪律括注在 AGENTS.md 有等价路由, 一并精简), 现 ≤ 3,000; ② 4 处指向已删 `baseline-history.md` 的历史链接(tasks 档案 ×1 / 冷库回指针 ×2 / testing/run.md ×1)—— 按计划 §04「链接改写是唯一易错点」改指 `baseline.md` 口径段或纯文本注记; 冷库只动了回指针两行, 内容未迁。

## 实现计划

照计划 §06 顺序执行: ①机制先行(`_common.py` role_of 登记 `baseline-slice` + CAP_POLICY 4000 + GEN_CMD_BY_SCRIPT → 新脚本 `gen_baseline_recent.py` → `.commands/kb/config.toml` 加 `kb.baseline` + `kb.check` 追加 `--check` → 守卫测试脚本清单 5→6 + SKILL cap 表加行) → ②一次性迁移(37 切片 + 链接加深 + 时分回填) → ③收口(baseline.md 转长青入口, 删 baseline-history.md) → ④引用方回写(计划 §05 四处 + grep 清点的 6 处) → ⑤验证与收尾(本档案)。

## 子任务状态表

| 子任务 | 状态 | 备注 |
|---|---|---|
| 机制四触点 + SKILL cap 表同步 | Done | kb.check 六项全绿; test.quick 1640+1 |
| 37 条存量切片迁移(链接加深 / 时分回填 / 序位注记) | Done | `gen_baseline_recent --check` 37/37 绿 |
| baseline.md 转长青入口 + 删 baseline-history.md | Done | 8,602 → 约 3.4k 字符(口径+警告, 不存数字) |
| 引用方回写(AGENTS / README / SKILL / 存根 / techContext / file-conventions / run.md / pitfalls×3) | Done | doc.caps PASS; 全库 grep 无残留"数字在 baseline.md 顶部"型锚点 |
| 冷库回指针 ×2 + 任务档案坏链 ×1 修复 | Done | 计划 §04 链接改写类; 冷库内容未动 |
| kb.baseline 验收(列 3 条 / 最新 = 1641 定稿) | Done | 附带 `<args>` 修正 |
| test.full 数字持平 + 本档案 + 认领链 | Done | 1640+1 / 92% (11013/787/3656/330) |

## 进度日志

- **2026-09-26**: 开工自检 sync PASS @ 2b19f42e; 机制先行并验证(空目录宽容分支绿 / test.quick 1640+1); 37 条切片迁移与 `--check` 全绿; baseline.md 长青化 + history 删除; 引用回写 10 处; 首轮 test.full 抓出 README 超 cap 与 4 处坏链(见决策节), 当场修复; 终轮 test.full **1640 passed + 1 skipped / TOTAL 92%(11013 / 787 / 3656 / 330) / 19.6s** 与 1641 基线持平, sidefx 越界 0; kb.baseline / kb.check / doc.caps 全绿; 立档 + 计划 doc-refs 双向认领链补齐(计划 doc-status → Done)。未提交 —— 等用户显式指令。
- **2026-09-26 提交轮**: 用户令「提交」。远端已推进(e7b9299, schema 版本链轮), 按「同步路径」合流: `.git` 备份 → 移出生成物副本 → stash(-u) → `merge --ff-only` → stash pop(唯一冲突 baseline.md, 保长青版; 对方条目转切片 `0633-schema-version-chain`)。对方 progress 追加使 implemented-core.md 超 cap(10,064 > 10,000), 最小压缩回线(9,995, 事实未动, 仅紧连接词 + 修「摘要: 摘要:」重复); ⚠ 该文件已贴顶, 下次追加前需先蒸馏外迁。合并树重测 **1664 passed + 1 skipped / TOTAL 92%(11112 / 783 / 3692 / 330) / 18.35s**(切片 `0703-two-line-merge-schema-versioning`) → ship.commit / ship.push。
- **2026-09-26 修复轮**: 用户令「修复 kb.active --check 拒参, 然后提交」→ `.commands/kb/config.toml` 的 kb.active 补 `<args>` 占位符(与 kb.baseline 同法), 实测 `kb.active --check` 可达且绿; kb.check 6 项绿。随本提交入库。
