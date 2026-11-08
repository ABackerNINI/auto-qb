# 26-11-09-rule-checking-issue-fixes — checking 四批 issue 修复收口

**Status:** Done
**Added:** 2026-11-09
**Updated:** 2026-11-09
**Summary:** TODO 清理池 checking/loaders 四条 refactor issue 分四批修复入库, 接缝终审 2 minor 过检修复后收口
**Topics:** rule-checking-issue-fixes
**Refs:** memory-bank/issues/26-11-08-1717-refactor-checking-has-reference-bool.html, memory-bank/issues/26-11-08-1717-refactor-checking-custom-flow-redesign.html, memory-bank/issues/26-11-08-1717-refactor-checking-paused-recheck-loop.html, memory-bank/issues/26-11-08-1717-refactor-loaders-hr-optimize-todo.html, memory-bank/pitfalls/testing/frozen-allowlist-baseline-drift.md

## 本篇只回答

本档案只回答: TODO 清理池(issue 26-11-08-1717 族)中 checking/loaders 四条 refactor issue 怎么分批修复、各批取舍与接缝终审结论是什么。领域结论(checking 决策链/冷却窗口/state 键)在 architecture/rule-engine.md 与 data-state.md, 不在本篇重复。

## 原始请求

1. 用户指派修复 TODO 清理池四条 refactor issue(26-11-08-1717 族): checking-has-reference-bool / checking-custom-flow-redesign / checking-paused-recheck-loop / loaders-hr-optimize-todo, 分四批提交、每批评审。
2. 四批落地后做接缝终审; 终审 2 条 minor 均裁决「相关, 必修」, 随收口批修复。

## 思考过程与决策

- 四批各自独立成提交(05ef90b9 / 0df16210 / 643caf51 / c7742273), 每批带 Review trailer, 单批评审零 actionable 后进下一批。
- 批2 自定义校验取方案 B(用户拍板): 超时可配置(动作级 spec 键 custom_basic_check_timeout, 缺省 600s)但不提供关闭语义, C27 超时保险丝不消失; 错误面三分类(TimeoutExpired/OSError -> WARNING 视为非参考, 其它异常 -> ERROR)对齐 traffic_source agent 形制。
- 批3 冷却窗口记一次(用户拍板口径): 记录点在 ops 层轮询 FAILED 判定仅 rule 源, 闸门在决策链 0.5(一次失败即冷却, 不烧 recheck_fails 额度), 两机制并存互不替代; 窗口值走动作 spec 键 recheck_fail_cooldown(缺省 1H, 正时间校验, 不可关闭), ops 层记录/清除不消费窗口值。
- 批4 loaders 选键表驱动而非 dataclass 手段: 解析职责留在 loaders, models 保持纯字段定义; 回退链与原 _get 逐路径等价。
- 接缝终审 2 minor(均过检必修): ①决策链 0.5 注释「记录/清除路径也只认 rule 源失败」与 ops_mod SUCCESS 分支全来源清除矛盾, 注释改两分表述(记录仅 rule 源/校验成功全来源清除); ②make_check_cfg 的 fail_cooldown 参数全套测试零消费(死脚手架), 补闸门窗口取值用例(spec 配 30M: 窗口内 20min 记录拦截 / 过窗 40min 放行 —— 40min 在缺省 1h 档仍会拦, 恰好区分窗口来源是 spec 值)。

## 实现计划

总体思路: 每批 = 修复 + 用例 + 批评审 + 提交; 收口批 = 终审发现过检(review.check) -> 修复 -> memory-bank 回写 -> 全量基线 -> 收口提交。

## 子任务状态表

| 步 | 内容 | 状态 |
|---|---|---|
| T1 | 批1: checking 谓词化 has_reference(05ef90b9) | Done(2026-11-09) |
| T2 | 批2: 自定义校验重设计 + custom_basic_check_timeout(0df16210) | Done(2026-11-09) |
| T3 | 批3: 校验失败冷却窗口 + recheck_fail_cooldown(643caf51) | Done(2026-11-09) |
| T4 | 批4: loaders HRRule 键表驱动收敛(c7742273) | Done(2026-11-09) |
| T5 | 接缝终审 2 minor 过检修复 + 回写 + 基线 + 收口提交 | Done(2026-11-09) |

## 进度日志

### R0 · 立档 (2026-11-09)

四批提交均已带 Review trailer 入库、四条 issue 随批翻 Done。收口轮: 终审 2 minor 过检(2/2 PASS)修复, test.quick 全绿(见 kb.baseline), 回写 rule-engine/data-state 漂移点(决策链 0.5 闸门/recheck_cooldowns 键/custom 超时键), 新立坑档 frozen-allowlist-baseline-drift(见下), 全量基线切片后收口提交。

T1 曾撞预存 ASCII 守卫漂移: a35463d4 在 test_webui_static_r4_addtorrent.py 注释引入的图形符号晚于冻结清单生成未登记, 提交闸门红且干净基线同样复现; 用户拍板把该注释改 ASCII 写法解锁, 坑档已立(pitfalls/testing/frozen-allowlist-baseline-drift.md)。

- 2026-11-09 05:45 四批 issue 修复收口: 接缝终审 2 minor(0.5 闸门注释矛盾/fail_cooldown 死脚手架)过检修复, rule-engine/data-state 漂移点回写, 新坑档 frozen-allowlist-baseline-drift, 全量基线切片, 收口提交
