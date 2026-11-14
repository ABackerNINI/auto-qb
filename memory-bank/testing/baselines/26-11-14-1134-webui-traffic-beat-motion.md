# 6133 —— webui 流量图节拍动效合流后基线

> 摘要: webui 流量图节拍动效合流后基线
> 基线时间: 2026-11-14 11:34

## 验收数字

`commands run test.full`（develop 合流并行 61 笔后终树实测）:

```text
TOTAL                                                27285     68   9582     73    99%
Required test coverage of 99.5% reached. Total coverage: 99.61%
6133 passed, 2 skipped in 177.34s (0:02:57)
```

## 本改动面

- 合流收口: `feat/traffic-beat-motion` 九笔（S0-a..S5）rebase 到远端 develop（dbfed3b4, 并行 61 笔）, 冲突两处手工解（test_webui_static_dom_panel_traffic.py docstring 取我方+采纳 e17bd088 的 _UI_ALL 措辞; webui.md 摘要取我方+触发行取双方并集）; rebase 后重跑 test.full 补一轮
- e2e 接线: traffic-fx-panel.spec.mjs / traffic-fx-frames.spec.mjs 补 `installRouteCleanup(test)`（远端 58d443a8 新守阵 test_repo_route_fetch_specs_wired_route_cleanup 要求含 route.fetch( 的 spec 顶层接线, 本分支两 spec 并行期不知情漏接 —— 合流后守阵抓出, 修复即本基线触发面）
- 前基线: 26-11-14-0949-webui-traffic-beat-s5（合流前分支树 6086 passed、2 skipped、覆盖 99.63%、177.62s）; 差值 = 远端并行 61 笔新增用例并入（6101 面本文/新增 e2e 守阵等）+ 本接线批 1 例（守阵计数不含 e2e）
