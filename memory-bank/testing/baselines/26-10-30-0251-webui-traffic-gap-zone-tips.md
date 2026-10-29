# 4065 passed + 10 skipped(根) —— 种子流量图缺口悬停分区段 + e2e 真悬停守阵后全量基线

> 摘要: 缺口(null 桶)悬停文案不再「一律断言成 qB 断联」, 改按「数据链之外 / 链中段」分区段并让主语跟着作用域走; 空态三句与累计注解同口径中性化, 画布斜纹只标记链中段; 守阵从静态字面量扩到 e2e 真鼠标悬停(种子三区段 + 全局主语分支)
> 基线时间: 2026-10-30 02:51
**Refs:** memory-bank/pitfalls/testing/uplot-hover-hit-area.md

## 验收数字

`commands run test.full`(pytest `-n 8 --cov=src --cov-branch --cov-fail-under=99`(pytest.ini addopts); 2026-10-30 实测, 全量 52.3s, 建档 02:51):

```
  TOTAL                                                20817    117   7136    107    99%
  4065 passed, 10 skipped in 50.30s (0:00:50)
```

- 汇总行: **4065 passed + 10 skipped(根)**; 覆盖率门槛 99% 通过(TOTAL 行 99%, missed 107)。
- 逐条口径注记:
  - passed/skipped 与上一可用基线(`26-10-30-0025-hr-thead-sort-gate`, 4064 passed + 10 skipped)相差的 1 例来自两者之间的其它轮次; 本轮**零新增 pytest 用例项** —— 改动是把 `tests/test_webui_static_dom_panel.py` 里钉旧文案的字面锚换成新四句 + 「模板必须引用 computed 单点」+「旧合并文案退场」, 并在既有 node 电池里补了一批 `_qbChainBounds`/`_qbGapZone` 判据与「链外不铺斜纹」断言。
  - **e2e 侧是本轮真正的新增量**: 新建 `e2e/traffic-gap-zones.spec.mjs`(4 例 = 双皮肤 × 种子三区段 / 全局主语分支), 已进 `@fast` 门禁 —— `npm run test:e2e:fast` 全量 **232 passed**(含本 spec 的 205–208 四条, 每条 1.5–2.4s), 无连带影响。
  - **变异红验**: 把 `qbCurGapText` 改成对所有缺口一律返回旧文案「无采样 · 程序未运行或 qB 断联」→ 本 spec 两条(prism 种子 / prism 全局)如期变红, 收到的实际串正是那句旧文案; 精确反向还原后重跑全绿(`git diff --stat` 回到 91+/11-, 且 `grep MUTATION-PROBE` 零命中)。
  - e2e 首跑曾四红在同一步 —— 参考盒取了 `.qb-chart-host` 而非 `.u-over`, 落到 uPlot 交互面外
    ⇒ hoverIdx 回落 -1; 已单独提炼成坑档(见上 Refs), 本基线不展开。
- 未跑: 全量 e2e 矩阵轮(env 参数化的 six-line 串行人跑, 属收尾/排障轨, 本轮未触发)。

## 本改动面

| 文件 | 改动 |
| --- | --- |
| `src/auto_qb/webui/static/shared/qb_traffic_chart.js` | 新增三个模块级纯函数 `_qbChainBounds` / `_qbGapZone` / `_qbPointsColumns`(判据**只认本次 points** —— 不用 `added_on`, 理由见文件头与函数注释); `_qbHoverOf` 缺口分支交付 `zone`; 新增 computed `qbCurGapText`(「区段 × 作用域」单点出句); 空态三句与 `qbCurSummaryHint` 按不归因口径改; `_qbDrawGaps` 只给链中段铺斜纹; 纠正一条引用已退场图例文案的过期注释 |
| `src/auto_qb/webui/static/shared/tpl/drawer.html` | 悬停缺口分支改引 `{{ qbCurGapText }}`(模板只引用不重算); 两处注记同步 |
| `tests/test_webui_static_dom_panel.py` | 旧文案字面锚换成按区段的四句 + 单点引用 + 旧文案退场三条; node 电池补判据实跑; 两份「## 测试计划」docstring 同步 |
| `e2e/traffic-gap-zones.spec.mjs` | **新建**: 真浏览器悬停守阵 —— `page.route` 造契约形状的一帧(60 桶; 链首前 / 链中洞 / 链尾后三段), flags 只翻 `qb_traffic_enabled`; `.u-over` 两点标定把鼠标送到指定桶, 回读 hoverIdx 断言命中, 再断言 tooltip 文案 |
| `memory-bank/pitfalls/testing/uplot-hover-hit-area.md` | 新坑档: 悬停类断言的参考盒必须是 `.u-over`(含 84px 纵轴槽实测数字) |

**未改**: 三个 GET 端点与 `payload_torrent/global/group` 一行未动(payload 契约零变更); `_qbGapRuns` / `_qbSeamHint` / `_qbSummaryOf` 语义不动; 「0 B/s · 空闲/做种」与「数据接缝中 · 服务于 X 重启」两句经确证保留((0,0) 是真实观测点 / 有 `meta.server_started_at` 确证), 中性化反而丢信息。

## 决策留痕(为什么是这套判据)

- **边界不用 `added_on`**: `added_on` 是「最近一次被塞回 qB」的时刻 —— 跳检就是删同 hash 再重加
  (`ops_mod.py` 的 `torrents_delete` → `torrents_add`), 而流量按 infohash 长期留存、删种不清理
  (`traffic_store.py`)。拿它切一刀会把跳检之前的真实历史数据整段标成「尚未添加」—— 与要修的失真
  同型反向。所以只用「本帧数据链从哪到哪」。
- **只有链中段能说「中断」**: 前后都有观测是可观测事实; 链首前 / 链尾后拿不到任何结论, 只陈述
  「该时段没有这个对象的数据」, 且主语按作用域取(全局图上写「此种子」是又一个编造的主语)。
