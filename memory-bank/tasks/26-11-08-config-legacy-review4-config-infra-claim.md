# 26-11-08-config-legacy-review4-config-infra-claim — 存量评审 R4 config-infra 主题修复批: 36 条六批委派实施与收编

**Status:** Done
**Added:** 2026-11-08
**Updated:** 2026-11-08
**Summary:** issue 26-11-07-0527(R4 存量评审 config-infra 汇总, 36 条 = major 2/minor 34)认领修复批: 六批(major2/infra5/validation7/config7/infra6/rules8)串行委派实施, 每批=实施子代理→只读评审(review.check 引文逐字校验)→修复→本地 commit(Review: trailer); 用户拍板 4 项+证据裁决改道 2 项; 逐批评审发现全修、接缝终审零发现; 全量回归全绿(见 kb.baseline); issue Open→Done; 计划外入池 6 件(26-11-08-0703 系列)。
**Topics:** config-legacy-review4-config-infra-claim
**Refs:** memory-bank/issues/26-11-07-0527-bug-legacy-review4-config-infra.html, memory-bank/testing/baselines/26-11-08-0713-legacy-review4.md

## 本篇只回答

issue 26-11-07-0527(R4 存量评审 config-infra 汇总, 36 条)怎么组织认领、分批修复与收编 —— 批次映射、拍板/改道、评审发现统计与本地任务分支运营要点在本篇; 逐条明细与复验记录在 issue 侧, 本档案不复述。

## 原始请求

1. 认领修复存量评审 R4·config-infra 汇总 issue(memory-bank/issues/26-11-07-0527-bug-legacy-review4-config-infra.html, 36 条 = major 2 + minor 34, 锚定 freeze f0883292): 本地任务分支六批委派实施+收尾, 每批独立 commit, 主会话统一提交(带 Review: trailer, 不走 ship.commit)。
2. 收口: 逐批评审+接缝终审无 blocker 后, issue 置 Done、计划外入池、文档回写、merge 到 develop、全量基线切片、立档。

## 思考过程与决策

- **委派模式**: 主会话拆解+委派, 实施子代理与只读评审子代理全程串行; 每批 = 实施子代理 → 只读评审(code-review skill, 发现过 `review.check` 引文逐字校验) → 修复 → 主会话本地 commit。子代理禁跑 my-commit-flow.sync(本地任务分支无远端), 与远端的齐平判断由主会话收口。
- **用户拍板 4 项**: #8 删 plugins_by_kind 函数+测试改道 / #17 写盘走模块级 _WRITE_LOCK(preview_tree 纯读不加锁) / #18 悬挂注解收 TYPE_CHECKING / #19 删 volume_free 死导出。
- **证据裁决改道 2 项(主会话)**: #9/#15 裸 0 特判放行方向 —— 与 models.py/groups.py 既有文档口径一致, 属「校验层放行 loader 裸抛」的必要延伸(_is_bare_zero 单点+loader _parse_time_bare_zero_ok 闭环); #27 display_host 可达等价折叠 —— issue 建议修法有可用性棱角(消费点是可连接地址提示, 127.0.0.2 绑定 localhost 拒连), 折叠收窄裁决并回写 issue 改道说明。
- **复验即修门槛**: #26 复验已消失(acquire_pid 随 66418c7e 退役) —— 认领条目先复验再修, 已消失条目只记录不造修。

## 实现计划

无独立计划 HTML(认领指令直行)。链路: 六批(串行委派+每批本地 commit)→ 接缝终审 → issue 置 Done+复验+逐批修法回写 → 6 条计划外入池 → modules/rules-and-deps.md 漂移修正 → merge develop → test.full 基线切片 → 立档。

## 子任务状态表

| 步 | 内容 | 状态 |
|---|---|---|
| 批1 | major×2: #1 path_normalize 归一豁免 UNC 根边界(开头 2+ 斜杠收敛到两个, 前端 _addNormPath 锁步镜像) + #2 HrCondition 构造期校验 mode∈HR_MODES(ConfigError fail-fast) | Done(2026-11-08, f5edc616) |
| 批2 | infra×5: #23 _match 逃逸 fall-through(SEC-1 无绕过) + #19 删 volume_free(拍板) + #20 挂载点正向测试 + #21/#22 docstring | Done(2026-11-08, fd08ebb6) |
| 批3 | validation×7: #9/#15 裸 0 特判放行闭环 + #14/#10 parse_bool 关闭判定 + #12 mode 守卫 + #13 未知键 + #11 gtm 回归 | Done(2026-11-08, 64e0cc8c) |
| 批4 | config×7: #16 targets 身份核对防串密码 + #17 写盘模块级锁(拍板) + #5 去重统一按 raw + #8 删 plugins_by_kind(拍板) + #4/#6/#7 禁字符/docstring | Done(2026-11-08, 2deebdb5) |
| 批5 | infra×6: #24 notify 0 窗口不记键 + #25 _unmount 摘后 close 修线程泄漏 + #27 display_host 可达等价折叠(改道) + #18 TYPE_CHECKING(拍板) + #3/#28 文档 + #26 复验已消失 | Done(2026-11-08, fa4ddeaf) |
| 批6 | rules×8: #31 DateTimeCondition 构造期解析(time_in_range 拆 parse_time_range+time_within, 消费面零变化) + #36 expr parser 深度上限 64 + #32-#35 话术对齐 + #29/#30 docstring | Done(2026-11-08, dfb6384a) |
| 收编 | issue Open→Done(复验+逐批修法落 issue 侧) + 6 条计划外入池(26-11-08-0703 系列) + modules/rules-and-deps.md 漂移修正 + merge develop(0469bf0c) + 基线切片 + 立档 | Done(2026-11-08) |

## 影响面与验证

- 代码: src/auto_qb/ infra(utils_paths/file_access/alias_fs/notify/utils/utils_parse/versioning)、config(loaders/validation×3/schema/migrations/compat/writer)、rules(conditions/expr×4/actions) 三域 + webui 4 文件(前端 _addNormPath 锁步); 新增/扩展测试散布 14 文件; 6 批 commit + 文档收尾 commit(80df0b9a) + merge(0469bf0c)。
- 评审: 六批发现全过 review.check 且全修、零 blocker —— 批1 1minor+2nit; 批2 1minor; 批3 2nit; 批4 1minor+2nit(含 issue 编号笔误 26-11-08→26-11-07 七处); 批5 2minor(线程断言基线化+display_host 折叠收窄裁决); 批6 1nit; 接缝终审零发现。
- 回归: 逐批 test.quick 递增、终局 test.full 全绿, 数字单点见基线切片(memory-bank/testing/baselines/26-11-08-0713-legacy-review4.md, merge 后 develop 树)。

## 运营要点 (供后人复用)

- 本地任务分支工作流: 子代理禁 sync、主会话统一 commit(Review: trailer 保批次锚点链); 合流用 merge 而非 rebase —— 保批次 hash, issue 回写里逐批 hash 引用不落空; 生成物冲突(_index.md/_archive.md)取一侧+重跑 kb.index+kb.check 自证。
- 远端并行前移豁免: 批次 3-6 评审期间远端两次前移(722eb3b0→7ddc6b57→70bba719), 以「前移与评审范围零文件交集」实证齐平放行(三钉第 3 钉的场景适配)。
- 子代理超时处置: 批次 2 实施子代理 600s 超时被切断但工作已完成 —— 主会话核 diff+跑测试验证后继续, 不重派。

## 进度日志

### R0 · 立档 (2026-11-08)

收尾轮立档: 阈值命中 #2(改动 ≥3 源文件)与 #3(批次波次表述); issue 26-11-07-0527 收编 Open→Done(复验/逐批修法/批次映射落 issue 侧); 基线切片 26-11-08-0713 已建(merge 后 develop 树); 认领链双向(kb.ref: issue + 基线切片); issues/_index.md 超 8,000 字符预算为既有债务, 按债务制转告待另行清理, 本轮不动。

- 2026-11-08 07:20 issue 26-11-07-0527(R4 config-infra 36 条)六批修复收编: issue 置 Done+复验+逐批修法, 认领链双向(kb.ref), 6 件计划外入池(26-11-08-0703 系列), 基线切片 26-11-08-0713 补 Refs(认领链), 立档本篇。
