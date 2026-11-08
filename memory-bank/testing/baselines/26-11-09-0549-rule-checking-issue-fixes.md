# 5,866 passed + 2 skipped —— checking 四批 issue 修复收口(终审 2 minor 修复)

> 摘要: checking 四批 issue 修复收口(终审 2 minor 修复)
> 基线时间: 2026-11-09 05:49

## 验收数字

`commands run test.full` 2026-11-09 05:47 实测: **5,866 passed, 2 skipped in 139.65s**; 覆盖率 99% (TOTAL 26,153 语句 / 42 未覆盖 / 9,100 分支 / 54 未覆盖分支)。较基线 26-11-08-2034(5,833+2)净增 33 条用例: 四批各自新增(谓词化改造/自定义校验 5 条/冷却窗口系/loader 键表钉)加收口批闸门窗口取值用例 1 条。

## 本改动面

- `src/auto_qb/rules/actions/checking.py`: 决策链 0.5 冷却闸门注释修正(记录路径仅 rule 源失败/清除路径校验成功全来源执行, 对齐 ops_mod SUCCESS 分支)。
- `tests/test_checking_full.py`: 新增 `test_checking_fail_cooldown_window_from_spec`(spec 配 30M: 窗口内 20min 记录拦截 / 过窗 40min 放行, 钉 make_check_cfg fail_cooldown 参数消费面) + 头部测试计划清单同步。
- memory-bank 回写: architecture/rule-engine.md(决策链补 0.5 闸门与 custom 超时键/保护按 source 区分表述精化) + architecture/data-state.md(state 主要键补 recheck_cooldowns) + tasks/26-11-09-rule-checking-issue-fixes.md(立档) + pitfalls/testing/frozen-allowlist-baseline-drift.md(新坑档) + 四条 issue doc-refs 反向认领补链。
