# 26-09-30-memory-bank-token-budget — memory-bank cap 翻倍 + commands list 平铺

**Status:** Done
**Added:** 2026-09-30
**Updated:** 2026-09-30
**Topics:** memory-bank-token-budget
**Summary:** 用户定调治理「提交触 cap 多轮返工」的 token 税: ①`_common.CAP_POLICY` 全表翻倍(唯一例外 AGENTS.md 的 IDE 注入硬约束 8000), 触顶处置统一为「精简/外迁到最大值的 50%」(新常量 `TRIM_KEEP=1/2`, 替代原 `LOG_ROTATE_KEEP=2/3`, 从 log 专属推广到全角色); ②`commands list` 由「逐级下钻」改完全平铺(默认一次递归列全树 33 行, `--all` 删除, `list <包>` 降级为聚焦视图, `pin` 降级为 ★ 纯记号)。人读镜像(SKILL.md cap 表 / kb-structure / cap-counting / instructions / 测试 docstring)与两份索引随改重建, 全部机检绿。

## 原始请求

「全面抬升 memory-bank 中各种文档的数字限制为 2 倍, 目前的数量限制会导致提交时经常触发 cap 从而需要经过多轮修改, 十分耗 token。此次目标是减少文档修改次数, 到达限制时再移除/精简/移出到最大值的 50%; 同时将 commands 的下钻改为完全平铺, 每下钻一次都会多一轮, 后期下钻的 token 成本不可接受。」收尾指令:「建档然后提交」。

## 思考过程与决策

- **cap 的机器单点只有一处**: `memory-bank skill scripts/_common.py` 的 `CAP_POLICY`(守卫 import 它), 项目侧 `scripts/check_context_caps.py` 另管三份 SKILL/README 预算 —— 两处各翻倍, 镜像表(SKILL.md cap 表)被 `test_skill_cap_table_matches_cap_policy` 钉住必须同步。
- **`AGENTS.md` 8000 不翻**: 它是 IDE 注入 `slice(0, 8000)` 的硬约束, 放大 = 守卫失效 + 尾部静默截断(恰是该 cap 要防的事故); 当前 7,966/8,000, 修改时顺手把「逐级下钻」句改短净省字符。
- **有意不翻的四个数**(向用户说明过): `CAP_MIN_WARN=1500`(下限 WARN 不阻塞, 翻倍徒增噪音)、`SUMMARY_MAX=80`(自动截断不产生人工轮次, 翻倍反而加速索引膨胀)、`SLICE_COUNT_LIMIT=70`(14 天归档节奏校准值, 26-09-29 刚二次校准)、14 天归档阈值(时间线非尺寸线)。
- **触顶处置从「log 专属轮转 2/3」推广为全角色统一「削到 50%」**: 常量改名 `LOG_ROTATE_KEEP` → `TRIM_KEEP`(语义从流水轮转扩展为通用收缩比例), `check_kb_structure.py` 超 cap 提示对**所有**角色直接给出目标字符数; `check_context_caps.py` 的「削到 90% 留 10% 余量」改「削到 50%」。
- **平铺的实现**: 平铺渲染本已存在(`--all` 递归铺开, 全树实测 33 行), 把它转正为默认即可 —— 删 `show_all` 分支与「pin 浮一级」逻辑, `--all` 参数整体删除(`list <包>` 保留为聚焦视图); `pin` 失去「浮到父级」行为后降级为 ★ 视觉记号, `MAX_PIN_PER_LEVEL` WARN 保留(防 ★ 稀释锚点价值), 引擎文案同步。
- **历史档案不动**: tasks/ 档案、attachments、progress 里引用旧数值(`LOG_ROTATE_KEEP=2/3`、24 KB 等)的行是历史记录, 保留; 只回写「现行口径」引用点(cap-counting.md 的 TRIM_KEEP 句、kb-structure.md、instructions、gen_tasks_index 头文案、测试 docstring), cap-counting.md「两个出口」条补一句 2026-09-29 政策注记(「调上限是最后手段」口径放宽为「已按政策校准」, 渲染口径优先不变)。

## 实现计划

单轮直改(无计划文档): 常量 → 守卫提示 → 人读镜像 → 引擎平铺 → 机检收口 → 建档提交。

## 子任务状态表

| # | 子任务 | 状态 |
|---|---|---|
| 1 | `_common.py`: CAP_POLICY 全表 ×2 + TRIM_KEEP=1/2 + TASK_LOG_CAP/STUB_CAP ×2 | ✅ |
| 2 | `check_kb_structure.py`: 全角色触顶提示削到 50%; 存根口径 ≤2 KB | ✅ |
| 3 | `check_context_caps.py`: SKILL/README 预算 ×2, 触顶文案 90%→50% | ✅ |
| 4 | 镜像回写: SKILL.md cap 表 / kb-structure / cap-counting / instructions / 测试 docstring / gen_tasks_index 头 | ✅ |
| 5 | commands 平铺: `_tree.py` 重写默认递归 + `run.py`/`_config.py`/SKILL/howto 文案 | ✅ |
| 6 | 机检: test.pkg 72 / kb 守卫 24 / test.full 1767+3 / doc.caps / kb.check / doc.links 全绿 | ✅ |

## 进度日志

- **2026-09-30 00:20**: 开工同步 42502f29; 摸底定位 cap 单点(`_common.CAP_POLICY`)与闸门(`check_context_caps.py` + `[[gates]]`)、平铺现状(`--all` 渲染已存在)。全表翻倍 + TRIM_KEEP + 平铺一次改完; 途中两处小失手均当场修复(编辑误删相邻 import 行; `_tree.py` 重写时 `Path` import 落到使用后)。
- **2026-09-30 00:25**: 首轮 test.quick 唯一红 = `test_index_is_regenerated`(生成器头文案改了 24→48 KB 而 `tasks/_index.md` 未重建) —— 重跑 `kb.index` 收口, 复跑 test.quick 1759 passed 全绿; doc.caps 显余量: AGENTS.md 7,966/8,000、memory-bank SKILL 6,347/15,000、commands SKILL 2,628/5,200。
- **2026-09-30 00:18**: 用户指令「建档然后提交」; 同步到 58d72e0a(远端有 WebUI 新提交, 已快进 —— 收尾回写落在合并后基线上); test.full 基线 1767 passed + 3 skipped / 91%(20.2s), 与上基线 26-09-29-2317 完全持平(零用例增删); 档案/切片/基线三件落盘。
- **2026-09-30 00:30**: ship.commit 闸门红一次 —— 新档案缺 `**Topics:**` 跨形态主键(test_docs_forms::test_doc_topics_complete)。已补 `**Topics:** memory-bank-token-budget` 并对该坑 `复发 +1`(cap-counting「生成式跨形态视图」条); **为什么没命中**: 把「新建档案」当归档动作而非 KB 回写动作, 建档后只重跑了 memory-bank 守卫, 没跑 test_docs_forms/kb.check。
