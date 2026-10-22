# 26-10-22-test-plan-docstring-guard — 「## 测试计划」docstring 机械守阵落地与全量回填

**Status:** Done
**Added:** 2026-10-22
**Updated:** 2026-10-22
**Summary:** 「## 测试计划」清单↔def test_* 机械守阵落地(扫描器+合成源红验内建+全仓零漂移断言+豁免名单): 存量回填 51 文件 295 条缺列 + 2 文件新建段 + 2 文件伪清单升格, 幽灵 6 处逐条人裁(2 改名/1 拆分对/3 删除); 全仓对账归零, test.full 全绿(基线切片 26-10-22-1907), src/ 零改动
**Topics:** test-plan-docstring-guard
**Refs:** memory-bank/issues/26-10-21-0502-test-test-plan-docstring-guard.html, memory-bank/testing/baselines/26-10-22-1907-test-plan-docstring-guard.md

## 原始请求

1. 用户: 「认领并修复26-10-21-0502-test-test-plan-docstring-guard.html」—— 用户指派认领, 授权范围 = 认领 + 按 issue §03 建议修复(守阵先行 + 存量回填); commit/push 未授权, 改动随本专题入库。

## 思考过程与决策

- **复验先行**(防过期原则第 5 条): HEAD 已从取证基线 `cecbe4a9` 前进到 `40cceff8`, ast 机械复查实测 **51 漂移 / 295 未列 / 4 无清单段 / 6 幽灵**(126 个测试文件) —— 现象仍在, 以此为本轮底数。
- **守阵判据与取证脚本同口径**: 段定位 = 模块 docstring 首个含「测试计划」的 `##` 标题行; 只认列表行条目(散文引用豁免); 缺列 = `def test_*` 名未出现在任何列表行; 幽灵只判**行首锚定**(跳过 `**`/反引号/`[x]` 装饰), 行中交叉引用不作幽灵; 豁免名单 `EXEMPT_FILES`/`EXEMPT_NAMES` 每条必须带理由, 存量清零后保持空表。
- **段边界一次事故一堂课**: 首版回填/守阵把 `startswith('##')` 当段边界, 段内 `###` 小节标题被误判成同级边界提前截断 —— 16 个含 `###` 小节的文件(hr 族为主)缺列整段翻倍, 首跑误插 814 条(真值 341)。靠「先复验出底数, 回填逐文件数字必须与底数对上」当场识破; `git restore` 本轮 tests/ 改动 → 边界修正为 `## `(带空格) → 重跑逐文件吻合。教训入 `pitfalls/testing/plan-docstring-section-boundary.md`。
- **回填形态**: 缺列以裸名 `- test_name` 追加到段内最后一个列表行之后(不虚构描述, 语义说明随后续改动自然补写); `test_sync`/`test_logging` 的伪清单标题(「测试清单:」「计划覆盖:」)整行升格为正式 `## 测试计划` 标题(既有描述全保留); `test_hr_discovery`/`test_snapshot_sync` 纯散文 docstring 尾部新建全量段。
- **回填脚本字节级**: 只插入行/升格标题行, 不改既有行内容; 新行用文件自身换行符; 保留 BOM; 每文件改后重解析自验(def 集不变 + 缺列清零)才写盘 —— 兑现 `ast-migration-fidelity` 坑档「内容从源行取」的纪律。
- **幽灵 6 处逐条人裁**: dom_panel 2 条就地改名(`test_drawer_tpl_default_sel` / `test_drawer_tpl_render_error_fallback_default`, 后继 def docstring 有「原名」声明铁证, 描述同步到 2026-10-14 缺省档新口径); hr_worker silence 两分支 1 拆 2(两条 `_label` 后继接手旧描述并标注拆分来源); 删 3 条(hr_worker 2 条改版重写无 1:1 后继; hr_status 1 条已并入 `test_site_status_rich_snapshot_fields`, 其断言文本与 ghost 描述逐字对应且后继已在清单)。
- **红验内建而非一次性**: 守阵自带合成源单测钉检出能力(缺列/幽灵/段边界/装饰/豁免), 另做活体突变红验(真实测试文件追加未登记 def → 守阵当场红 → 原字节还原)。
- **AGENTS.md 硬规则未动**(治理文件): 是否把守阵指针挂进 AGENTS.md 留给用户决定。

## 实现计划

issue §03 两步走 + 收尾, 每步独立可验: S1 开工同步+复验出底数 → S2 落守阵(扫描器+合成源红验+全仓断言) → S3 一次性回填(字节级脚本, 自验后才写盘) → S4 幽灵逐条人裁 → S5 验证(对账归零+守阵全绿+活体红验+dev.fmt+test.full) → S6 收尾回写(基线切片/issue 翻 Done/坑档/wrap/index)。

## 子任务状态表

| 步 | 内容 | 状态 |
|---|---|---|
| S1 | 开工同步 40cceff8(快进 c3e7a71f→40cceff8) + ast 复验底数 51 漂移/295 未列/4 无段/6 幽灵 | Done(2026-10-22) |
| S2 | 守阵 tests/test_test_plan_docstring_guard.py(扫描器+合成源红验 5 条+全仓断言 1 条+豁免名单) | Done(2026-10-22) |
| S3 | 存量回填 53 文件(+341 条: 51 文件 295 缺列 + 2 文件新建段 46 条; 2 文件伪清单升格) —— 含 ### 边界事故恢复重跑 | Done(2026-10-22) |
| S4 | 幽灵 6 处清理(2 就地改名 / 1 拆分对接手 / 3 删除) | Done(2026-10-22) |
| S5 | 验证: 全仓对账 0 漂移/0 无段/0 幽灵(含守阵自身) + 守阵 6/6 + 活体突变红验 + dev.fmt 56 文件零扰动 + test.full 全绿 | Done(2026-10-22) |
| S6 | 收尾回写(基线切片 26-10-22-1907 / issue 翻 Done / 坑档 plan-docstring-section-boundary / kb.wrap / kb.index) | Done(2026-10-22) |

## 进度日志

### R0 · 立档与实施 (2026-10-22)

- 复验底数(`40cceff8`): 51 漂移 / 295 未列 / 4 无清单段 / 6 幽灵(126 个测试文件); 26-10-05 曾清理过一轮(11 文件 21 幽灵)后再次积压 —— 无机械守阵, 漂移必然回潮, 守阵化是本件的实质修复面。
- 守阵落地 + 回填 + 幽灵人裁后全仓对账归零(含守阵文件自身自受管辖)。
- 首跑回填把 `###` 小节当段边界致 16 文件误插(814 vs 真值 341), `git restore` 本轮改动后修正口径重跑, 逐文件账目吻合 —— 见 `pitfalls/testing/plan-docstring-section-boundary.md`。
- 验证: test.full 全绿(数字见 `testing/baselines/26-10-22-1907-test-plan-docstring-guard.md`); 守阵合成源红验 6/6 + 活体突变红验过; `src/` 零改动, 改动面 = tests/ 56 文件 + memory-bank/ 制品。

- 2026-10-22 19:12 守阵落地+存量回填53文件+幽灵6处人裁, 全仓对账归零, test.full 全绿(基线切片 26-10-22-1907); issue 翻 Done
