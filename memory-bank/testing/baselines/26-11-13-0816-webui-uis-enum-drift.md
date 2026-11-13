# 6101 passed + 2 skipped, 覆盖率 99% —— 6101 —— 6101 passed + 2 skipped —— test.full 基线: 守阵文案口径批(纯注释零新增用例)

> 摘要: 6101 —— 6101 passed + 2 skipped —— test.full 基线: 守阵文案口径批(纯注释零新增用例)
> 基线时间: 2026-11-13 08:16

## 验收数字

`commands run test.full` 实测(2026-11-13 08:16, 本机 Windows, develop@acc36968 + 未提交批(0745 文案批含 src 相邻面), 两轮: src 修复前后各一遍逐位一致):

```
TOTAL                                                27113     65   9480     69    99%
6101 passed, 2 skipped in 170.79s (src 修复前) / 248.43s (src 修复后)
```

差值口径: 较最新基线切片 26-11-13-0809(6084+19, env3 宿主)**+17 passed / -17 skipped**, 属跨宿主环境 skip 差异带(0715 切片「跨 clone 环境差异带」同型先例; 两轮实测零新增用例零回归, src 注释修复前后数字逐位一致)。

## 本改动面

- **`tests/test_web_shortcuts_engine.py:5`**: 头部导语「挂载成对(三份 tpl-manifest + app.mixin)」→「挂载成对(全部皮肤(webui_helpers._UI_ALL)的 tpl-manifest + app.mixin)」(0443 批 registry 同款, issue 26-11-13-0745)。
- **`tests/test_webui_static_dom_panel_dialogs.py:23/1761`**: overlay_fit 计划条目与 test docstring「三份 tpl-manifest」→「全部皮肤(_UI_ALL)的 tpl-manifest」。
- **`tests/test_webui_static_dom_panel_traffic.py:5/548`**: qb_traffic 计划条目与 test docstring 同款改口径(548 因行宽顺带换行重排)。
- **`src/auto_qb/webui/static/shared/qb_traffic_chart.js:50/94`**(相邻面, 用户拍板一并修): 生产注释同款旧口径 2 处——50 行枚举括注「见 prism/atlas/console」漏 flux 一并修正为「全部皮肤(atlas/prism/console/flux)」; 94 行最小改「全部皮肤的 tpl-manifest」。纯注释, 断言本体零触碰。
- 验证: test.one 三件 32 passed(tests 面) + 合流后 shortcuts 四件 + dom_panel 两件 49 passed + grep 「三份 tpl-manifest」全 tests/+src/ 清零。
