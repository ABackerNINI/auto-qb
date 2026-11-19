# 6486 passed, 6 skipped —— deps-upgrade 退化配置空 joint 中性文案修复批基线

> 摘要: deps-upgrade 退化配置空 joint 中性文案修复批基线
> 基线时间: 2026-11-19 08:54

## 验收数字

实测树: 本地 develop tip `105c093f` + 本批工作树(修复 + issue 翻灯 + 回写, 随本专题入库)。`commands run test.full` 实测(2026-11-19 08:5x, 189.2s):

```
TOTAL                                                28915     44  10322     61    99%
6486 passed, 6 skipped, 7 warnings in 187.42s (0:03:07)
```

与上一条切片(26-11-19-0837, 6480P/6S)差值: 总量 28896→28915、passed 6480→6486 —— 含本批新增 1 用例(`test_build_report_empty_joint_degenerate_config`)与两分支间用例面差异(对方实测树是其本地分支 `fix-e2e-issues-261119` tip `726fb31b`, 非同树不可逐位对齐)。

## 本改动面

- `.agents/skills/deps-upgrade/scripts/check_updates.py`: `build_report` 联合分析句装配加空集守卫——`[joint] deps` 为空的退化配置下不再装配 "all 0 special deps ()" 数量词句, 改走中性文案 `(none) - no joint deps configured ([joint] deps is empty).`; 触发行不套 joint 框架罗列(pin 表 support 列照常可见)。正常配置两模式输出逐字节不变(评审核实)。
- `tests/test_deps_upgrade_check_updates.py`: 新增 `test_build_report_empty_joint_degenerate_config` 回归 + 文件头测试计划清单同步(25 用例)。
- KB: issue 26-11-18-0611 翻 Done(§03 补实际修法/验证段); `pitfalls/testing/parallel-run.md` 偶发红条目 复发+1(闸门预跑撞 `test_hr_discovery` 端口偶发红, 单跑绿, traceback 又只截 tail 未落盘)。
- 真机轨不适用: 本批为 skill 巡检脚本的报告文案分支, 纯桩可验, 不涉 qB 真执行/真文件系统·进程·注册表面。
