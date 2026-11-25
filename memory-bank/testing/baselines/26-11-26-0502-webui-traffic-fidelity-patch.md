# 7036 passed, 6 skipped, TOTAL 31424/108/11198/94 99% —— webui-traffic-fidelity-patch S4 守阵总收口全量基线

> 摘要: 保真修补计划 26-11-26-0227 S4 守阵总收口批后基线: e2e 裁剪面 C 案 P6 改判(先红后绿) + 受影响面 e2e 全绿 + 全量绿
> 基线时间: 2026-11-26 05:02

## 验收数字

`commands run test.full` 实测(2026-11-26 05:01, Windows, rc=0, 126.11s, 本地分支 webui-traffic-fidelity-patch 七笔前置提交(348002a3/b8d1f2f2/523fa0b0/f737bcf6/9cfe6a24/f00b99fa/6fe8ad28)后的 S4 守阵批态):

```
TOTAL                                                31424    108  11198     94    99%
7036 passed, 6 skipped, 1 warning in 126.11s (0:02:06)
```

与上基线(26-11-26-0145 合流终态注记, 7036P/6S, TOTAL 31424/108/11198/93)对账: 通过/跳过/语句/分支总数完全一致, 用例数零变化(本批只改 e2e 断言, 不进 pytest 覆盖面); 覆盖缺口 93→94, 差 1 落在前置 S1-S3 生产代码批(qb_traffic_chart.js 辉光重构/粒子三因子/钳制退役)之后, 本批无法逐行定位到语句, 如实记录不归因。

## 本改动面

- `e2e/traffic-fx-frames.spec.mjs`(S4 守阵唯一改动文件): 裁剪面机制探针 C 案按 P6(plan 26-11-26-0227 §03.3)改判 —— 旧断言钉「fx 段 clip 上沿 = 绘图区上沿 T / 高恰 = 绘图区高 H(下缘不放宽)」已与 P6 落地后的生产口径(装饰主 clip 上下缘放宽到画布上下缘)冲突, 红先实测(两皮肤同红: 主 clip 上沿 0 vs 断言期望 T=17); 改判为双 clip 分类断言(主 clip = [L, 0, max(W, canvasW-L), canvasH] —— F5 右缘放宽 + P6 上下缘=画布缘; 束体自含 clip = [L, T, max(W, canvasW-L), H] 只右缘放宽), 帧记录补画布高 ch, 注释/用例名/stub 注释同步(环心钳制/底缘镜像已退役, 由电池 G11/G12 反向钉)。
- pytest 守阵面零改动: 静态钉/e2e 之外的旧口径改判(辉光常驻/视口裁剪严格 rect/常驻 blur 预算 ≤5 与帧末清零/P6 装饰 clip 上下缘=画布缘且不铺底/粒子三因子/360° 喷射/P4 小菱形/P5 DOM 锚随末点滑/G11 去钳制/G12 去镜像)已随 S1-S3 七笔前置提交入库, 本批逐项复核无旧口径残留。
- e2e 受影响面实测(2026-11-26, Windows headless chromium): `commands run dev.e2e-perf-serial`(traffic-fx-frames 全量 + perf + drawer-content-perf 量具) 37 passed / 3.5m; `commands run dev.e2e -- e2e/traffic-fx-anchor.spec.mjs e2e/traffic-fx-panel.spec.mjs` 32 passed / 1.1m; C 案改判后单跑绿验 2 passed(prism/atlas)。
- 未跑面: Linux 三面(test.linux / test.linux-e2e / 变异)需 Docker testbed, 本轮环境未起容器, 如实记未跑; 真机五项对照与 I3/I8/I10/I7/G7 回归自检(计划 §04 S4 验收的真机面)无真机 qB 环境, 未做, 交父会话排程。
