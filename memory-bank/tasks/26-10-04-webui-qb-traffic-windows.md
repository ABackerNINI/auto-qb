# 26-10-04-webui-qb-traffic-windows — WEBUI qB 流量图十档时间窗

**Status:** Done
**Added:** 2026-10-04
**Updated:** 2026-10-04
**Summary:** 用户要求流量图添加 1/5/30 分钟、3/6/12/24 小时视图(与 qB 速度图窗口对齐)外加 3/7 天视图, 组/种子流量图同样。后端 `WINDOW_SPECS`/`WINDOW_NAMES` 扩为十档(1m/5m/30m/3h/6h/12h/24h 消费 raw 段桶宽=采样间隔; 3d/7d/30d 消费 hour 段桶宽恒 3600s, 零存储改动), 前端抽屉窗口按钮组 2→10 档 + `qbWindowLabel` 紧凑文案 + `_qbTickLabel` 三族刻度(1m/5m 标到秒, 3d/7d/30d 标日期, 其余标时刻)。test.full 2442 passed + 4 skipped / 99%(基线 26-10-04-0458)。改动留工作树未提交, 等用户显式提交指令。

**Topics:** torrent-traffic-stats

## 原始请求

用户指令: 「WEBUI qb流量图需要添加1/5/30分钟,3/6/12/24小时流量视图, 与qb行为对齐, 外加3/7天视图. 组/种子流量视图同样。」—— 全局/分组/单种三挂点同源(三挂点共用同一后端窗口参数与同一段前端窗口切换逻辑), 一处扩展三处生效。

## 思考过程与决策

- **窗口 → 消费段映射**: 既有两档已定口径(24h=raw 段桶宽=采样间隔, 30d=hour 段桶宽恒 3600s), 新窗口按同口径就近归段 —— 分钟/小时档(1m-24h)全部走 raw 段(数据粒度 = 采样间隔, qB 对齐正是要短窗细粒度), 天档(3d/7d)与 30d 同走 hour 段(3d=72 点 / 7d=168 点, 均在直渲染余量内), **存储层零改动**(raw_window 缺省 24h 恰好覆盖 raw 段窗全跨度; rollup_window 校验边界 7d 起恒覆盖 3d/7d; 配置收窄时超窗部分如实出 null 断线, 与既有 24h/30d 行为一致)。
- **短窗退化场景**: 1m 窗 @ 缺省 30s 采样 = 2-3 桶(粗但真值, 采样间隔可配到 1.5s 细化); 采样间隔上限 600s 时 1m/5m 窗近乎全 null —— 数据不存在, 如实呈现, 不伪补。
- **刻度文案三族**: `_qbTickLabel` 按窗口族出格式 —— 1m/5m 标 `HH:MM:SS`(桶可落在同分钟内, HH:MM 会重标); 3d/7d/30d 标 `MM-DD`(沿 30d 先例); 其余 raw 段窗标 `HH:MM`(沿 24h 先例)。
- **按钮文案**: 十档全用紧凑两字格(1分/5分/30分/3时/6时/12时/24时/3天/7天/30天), 经新方法 `qbWindowLabel(w)` 出文案(模板内联 map 10 键过长); `.qb-tabs` 胶囊按钮 padding 3px 12px 实测不挤工具条。
- **窗口合法性单点**: 后端唯一校验点 `parse_window`(traffic_qb.py), `WINDOW_NAMES` 扩十档 + 400 detail 动态拼; `build_grid` ValueError 文案同步动态拼(不双写清单)。
- **轮询语义不受影响**: meta.interval_s raw 段窗=采样间隔(夹取 [15s,600s]), hour 段窗=3600(夹到 600s 上界), 既有夹取逻辑原样覆盖十档。

## 实现计划

1. 后端: `core/traffic_grid.py` `WINDOW_SPECS` 2→10 项(注释/ValueError 文案同步)。
2. 后端: `webui/server/traffic_qb.py` `WINDOW_NAMES`/`parse_window`/docstring 同步。
3. 前端: `tpl/drawer.html` 窗口按钮组 2→10 档 + `qbWindowLabel`; `shared/state.js` 三挂点 window 字段注释。
4. 前端: `shared/qb_traffic_chart.js` `_qbTickLabel` 三族刻度 + 头注释/轮询注释口径更新。
5. 测试: `test_traffic_grid.py` 新增 `test_build_grid_extended_windows` + ValueError 探针改 "90d"(7d 已合法); `test_web.py` 窗口校验测试十档全放行 + 非法探针改 "90d"。
6. 回写: `memory-bank/config-reference/keys.md` qb_traffic 段视图口径 + 基线切片 + 本档案 + activeContext 切片。

## 子任务状态表

| # | 子任务 | 状态 |
|---|--------|------|
| 1 | 后端窗口集扩展(traffic_grid / traffic_qb) | Done |
| 2 | 前端窗口按钮组 + 刻度文案(drawer.html / qb_traffic_chart.js / state.js) | Done |
| 3 | 测试更新与新增(grid / web) | Done |
| 4 | test.full 基线 + memory-bank 回写 | Done |

## 进度日志

- **2026-10-04 04:58**: 全部实现完成, `commands run test.quick` 2442 passed + 4 skipped 预验 → `test.full` **2442 passed + 4 skipped / 29.62s / 覆盖率 99%**(14361 语句 / 135 未覆盖 / 4864 分支 / 106 partial), 相对上基线(26-10-04-0412: 2441+4)**净增 1 用例**(`test_build_grid_extended_windows`)。基线切片 [baselines/26-10-04-0458](../testing/baselines/26-10-04-0458-webui-qb-traffic-windows.md)。未验证面: 真机换窗走查(短窗桶数/刻度文案/轮询续拉)待用户; 改动留工作树未提交。
