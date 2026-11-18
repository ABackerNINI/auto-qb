# 6469 passed + 6 skipped / TOTAL 99% (99.73%, 语句 28890 / 未覆盖 44) —— 限速曲线 period 排序 S1-S5 收尾批基线

> 摘要: 限速曲线 period 排序 S1-S5 收尾批基线
> 基线时间: 2026-11-19 02:02

## 验收数字

```
6469 passed, 6 skipped in 219.84s (0:03:39)
TOTAL  28890  44  10312  61  99%
```

- 总覆盖率 99.73% 由上一行实测 TOTAL 表按 (语句-未覆盖+分支-半分支)/(语句+分支) 推得(test.full 的 silent_success 只上屏 TOTAL/汇总两行, Required 行被引擎静默); 推法以对上一基线 26-11-18-0721 复算逐位吻合背书。
- 对上一基线(26-11-18-0721 backend-qbmanager-startup-reload-discard)差值: passed +9(S1 排序键单测 5 条 + S2/S3 loader/GET 单测 4 条, 含幂等测试改写), skipped 不变; 语句 28864→28890 / 未覆盖 43→44(period_sort_key 及调用点的注释性 docstring 增量落在已覆盖面外一行), 单轮跑净无 flaky。

## 本改动面

- src/auto_qb/core/curves.py: period_sort_key helper(S1, ab9c756f)+ docstring 互指现在时(S2/S3、S4 各修订)。
- src/auto_qb/config/loaders.py: 构造 GlobalSpeedLimitCurve 前排序一行(S2, ae108430)。
- src/auto_qb/webui/server/routes/config.py: _sort_tree_curve_periods(树形五层形状防御 + 任一 period 非法整段放弃), GET /api/config 在 mask_tree 前调用(S3, ae108430)。
- src/auto_qb/webui/static/shared/config_editor_curve.js + src/auto_qb/webui/tpl/traffic-card.html: JS 排序键复刻(注释互指)+ 新增定位插入 + 改值 @change 提交重排 + 回车提交后 blur 收口 + 解析失败整段放弃(S4, ae588e66)。
- tests/test_speed_curve_config.py / tests/test_web_backend_misc_config.py: 新增 9 条单测 + 文件头测试计划同步(S1/S2/S3)。
- e2e/config-curve-period-sort.spec.mjs: 新 spec 4 用例 x prism/atlas 双皮肤(e2e 轨, 不计 pytest 基线数)。
- docs/configuration.md:「全局限速曲线」节新增「曲线排序: 按 period 自动排序」小节(S5, 本批)。

