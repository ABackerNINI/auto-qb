# 6266 —— 行窗口化 pad 等高替换修复批全量基线(issue 26-11-15-0332)

> 摘要: 行窗口化 pad 等高替换修复批全量基线(issue 26-11-15-0332)
> 基线时间: 2026-11-16 03:53

## 验收数字

`commands run test.full` 实测(2026-11-16 04:22, Windows; 机器上有常驻服务在跑, 故 3m38s):

```
TOTAL                                                27855     73   9822     79    99%
Required test coverage of 99.5% reached. Total coverage: 99.59%
6266 passed, 2 skipped in 217.66s (0:03:37)
```

e2e 侧(本批对象): `e2e/drawer-dock-stability.spec.mjs` + `row-window-zoom` + `window-invalidation` + `kbd-scroll-band` 四 spec 串行 **47 passed / 10 skipped**(2.5m, 0 failed); 像素三例 T7 顶界带 / S-A 首开遮挡 / S-C 越过带 单跑 **7 passed / 2 skipped**(flux 专属两条在 prism/atlas 上 skip)。

红验(撤产品修复、保留去预热的判据): T7 前置带 `行顶-列头底 = 5.8125 > 4` 红; S-A 公式落点 `-11 > -14` 红(偏差 5px); node 电池把重探调用停掉后 **11/22 过、8 项红**(绿验四条全红: 陈旧键没被顶掉 / padTop 仍按 69.609 超量累加 / 修复前后差不成立 / `_rowPre` 仍是陈旧前缀和, 另加首拍量遍、三入口同拍去重等), 静态守阵同红(调用点位置断言)。绿验: 全部通过。

## 评审流水(已外迁)

四轮评审流水已外迁: [attachments/26-11-16-0353-…-review-details.md](attachments/26-11-16-0353-issue-26-11-15-0332-rowwin-stale-rowh-fix-review-details.md) —— 评审轮(code-review skill, 7 条: major 1 / minor 5 / nit 1, 含 ROW_H_MAIN_PROBES 探测位 data-table 收窄 major)/ 收口轮(自审, 「换行集重校」整机制删除等 4 项)/ 复评轮(第 2 轮, 10 条: minor 4 / nit 6)/ 分面复评轮(并行 2 路, 4 条: major 2 / minor 2, zoom 基准漂移入池 26-11-16-0716), 全部处置完毕零 blocker; 「本改动面」中 (评审 #N)/(收口 #N)/(复评 #N) 引注均指该件内对应表行。

## 本改动面

- `src/auto_qb/webui/static/shared/columns_grid.js`(+130/−7):
  - 新增 `ROW_H_MAIN_PROBES` 单点(主表三 kind 探测位, `_measureRowH` 与重探共用; 原来选择器写死在 `_measureRowH` 内)。三 kind 各自带 `[data-table="torrent"/"group"/"detail"]` 收窄 —— 剧集页 `.show-row`/`.ep-row` 也带 `data-key`, 裸 `.group-row:not(.torrent-row)` 会把别座表的行记成 group 行高并污染冻结基准的来源均值(评审 #1)。
  - 新增 `_rowHProbeRows(kind)`(解析「此刻还在 DOM 里」的该 kind 行; 抽屉桥按在场变体锚现拼, 不裸扫 `.group-row[data-dt-key]`)与 `_reprobeRenderedRowH(kind, sig)`(出窗最后一探: 只刷已有键、`h<=0` 不采信、同拍 sig 去重且只在真量到行后落盘、抽屉 `content-visibility:auto` 守卫、零全表作废)。
  - `_rowWindow` 一处: 早退之后 / `pre[]` 之前调 `_reprobeRenderedRowH`; 其余不变。
  - `_measureRowH` 主表分支: 占位基准从「每拍跟随均值」改为「首校即冻结」, 门恰两支 —— `!_winMeasured[kind]`(首访量齐)与 `!(this._rowH[kind] > 0)`(存值非正 = 还没校准, 兜住 v-show 收走时 gBR 全报 0 把均值校成 0 的情形, 否则切回来 est 恒回落成 `ROW_WIN_EST_H` 常量)。冻结后新量行只把自己那一项从估算换成真值, 不再连坐搬整段 pad。抽屉内容桥分支不动(仍需逐拍收敛 28→27)。
  - `_rowHAvgOf` 头部注释改写(收口 #2): 不再承诺「估算偏差单调收敛」, 改为「本函数只负责算, 冻结与否由调用方定」+ 抽屉例外。
- `src/auto_qb/webui/static/shared/lifecycle.js`(+4): 根 `created()` 初始化 `_rowProbeSig` 一个非响应式纯缓存(进 data 会每拍多触发一轮整表重渲)。
- `tests/test_webui_static_dom_page_layout.py`(+137): 新增 `test_frontend_outgoing_rowh_reprobe_guard`(调用点位置 / 只刷已有键且必须是 `continue` / 零全表作废黑名单 / 同拍去重且空探不记账 / `h<=0` 跳过 / 抽屉守卫 / 探测位单点且 group 必须带 data-table / 冻结门恰两支 + 已删缓存不许回潮 / 抽屉不冻 / created 初始化)+ 测试计划 docstring 一条。
- `tests/test_webui_static_r4_node_batteries.py`(+236): 新增 node 电池 `test_r4_outgoing_rowh_reprobe_kills_pad_jump`(22 检查, 含项数断言防静默变弱; 红验复现 padTop 按 69.609 超量替换, 绿验真值 65.781 落地且前后差恰 +3.828px; 另钉零全表作废 / 三入口同拍去重 / 几何变了才重探 / rowWin 关闭零重探 / 抽屉未渲染行跳过 / 冻结门两支 / 抽屉不冻)+ docstring。
- `e2e/drawer-dock-stability.spec.mjs`(+36/−34): 删 `preheatRowWindow()` 预热辅助与两处调用(T7 对齐前 / S-A 让位前), 换成「刻意不预热」说明 —— 判据变回真回归探测器; 采样器加分数精度 `rowBf`/`rowTf`, S-C/T7 的位移判据改用分数值比分数基线(原先「取整帧 vs 分数基线」最多带 0.5px 量化偏置, 会把 1px 的选中行箱变读成 1.0625 假红 —— 实测真相是恰 1.0px, 且该箱变在修复前 HEAD 上同样存在)。
- `memory-bank/`: issue 26-11-15-0332 置 Done(§02 位置复校 / §03 处置填实 / 状态日志); 坑档 `pitfalls/web-ui/rowwin-stale-rowh-pad-jump.md` 重写(两根因 + 守阵三面, 原「处置」是已退役的测试侧预热); `testing/flaky-ledger.md` 原 drawer-dock 行补产品侧修复去向; 本基线切片。

## 未做

- 未 commit / 未 push(需用户显式指令)。
- 未改 `_winZoomOf` / `_winCtnSync` / 行高签名因子 —— 本批刻意不碰 rowh-sig-and-transition-geometry 的两个已知坑面。
- 未做「行集变了就重算占位基准」—— 收口轮论证过做不到(见上), 只留边界注释。
- `e2e/kbd-scroll-band.spec.mjs` 的 Home/End(prism)在三 spec 合跑时红过一次, 单独复跑与再次合跑均绿(机器上有常驻服务在跑), 判为负载抖动, 未改动该用例; 与本批改动无因果关系(该用例不涉行高存值, 且红时行窗路径未变)。
