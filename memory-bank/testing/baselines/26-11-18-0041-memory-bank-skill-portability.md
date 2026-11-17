# 6433 —— skill 轨道可移植性改造收尾基线(合流后最终树)

> 摘要: skill 轨道可移植性改造收尾基线(合流后最终树)
> 基线时间: 2026-11-18 00:41
**Refs:** memory-bank/tasks/26-11-17-memory-bank-skill-portability.md

## 验收数字

`commands run test.full` 实测(2026-11-18 00:41, 合流上游 webui 工作后的最终树, Linux):

```
TOTAL                                                28864    193  10304     80    99%
6433 passed, 23 skipped in 98.32s (0:01:38)
```

与上基线 26-11-17-0719(6286 passed / 19 skipped)差值来源: 上游合流带入 webui 流量图/relocate 测试面增量(含我方合流适配 3 条修红后的净变化), skipped +4 为上游面新增。

## 本改动面

本轮(skill 轨道可移植性 26-11-17-0010 全波次 + 收尾)落到本树的面, 权威数字以本切片为准:

- 波次 1-3 全部批次(S1-S11): memory-bank skill 配置化 / kb.check 空库恒绿化(双守卫摘链显式挂载) / red_lines fnmatch 化 / 配置模板四件+KB 骨架三件 / PORTING 轨道 runbook+每 skill 九份 / review_lane lane.toml 外置 / sync 配置化 / 收口五条验收(沙箱重放 0 代码 diff + grep 审计操作性零命中) —— 见任务档案进度日志与各批提交。
- 合流适配: relocate_plan.py `_own_alias_symlink`(上游 Windows 盲区代码缺口) + 两条测试平台假设对齐 + docs_forms ARCHIVE_MD_EXCEPTIONS 白名单清理(两路线合流取 HTML 侧)。
- 收尾建档: 观察件 5 份(issues/26-11-17-2339-*)与 R-6 演进史下沉件(26-11-17-0620)。
