# 3148 —— 数据拍整帧重建移动锚根治(sig 结构态 + paintHtml 原地回填, 第八次复发)

**Refs:** memory-bank/pitfalls/web-ui/drawer-switch-flicker.md,memory-bank/activeContext/26-10-12-2223-webui-drawer-tpl-flicker-fix3.md,memory-bank/testing/baselines/26-10-12-2115-webui-drawer-tpl-flicker-fix2.md

> 摘要: 用户二次报障「闪烁没有修好 + 数据不实时刷新而是随闪烁刷新 + 疑与 5s 自动刷新有关」+「我一开始就说了是种子详情页所有表格」。第七次(beca3f6a)修 dtSyncAnchors 多锚假阳换代, 未触及数据拍整帧重建本身。病根(帧间隔 + longtask 双证, 80 对端真量级): 六个桥变体(04/05/06 trackers + 07/08/09 peers)render 的 sig 全含整包列表数据 ⇒ 5s 轮询每拍必整帧重建 ⇒ anchFill 移动锚 ⇒ 锚里 Teleport 的整表整树重排 —— 变体 07 实测每拍 52-93ms 慢帧 + 56-75ms longtask, 经典表同数据量 0ms; 成本拆分实锤冻源 = 锚移动(重排)非 HTML 计算。前七次探针全绿因 harness 桩 12 条(重建 <16ms 一帧内完成无中间态可绘) + 无 SSE —— 量级与驱动必须同时复刻。修复(7 个生产文件): 核心新 helper `H.paintHtml`(数据依赖子树原地 innerHTML 回填, 同值跳过); 六变体 sig 收窄为结构态(加载/失败/空态/在场分组集/折叠态), 数据拍走 skipUnchanged 跳过分支 + 回填壳上数值(与整帧重建共用的构建器: 07 cardsHtml/barHtml · 09 barHtml · 08 组头 gcnt/gagg · 04 overviewHtml · 05 stripHtml+徽章 · 06 toolbarHtml); `xtpl.html` 桥模板 v-if 判空 `sortedDrawer().length` → `seg.rows.length`(每拍每段少排一遍 80 行); 06 sig 去 nowSec(逐行倒计时走桥响应式, 粒度恒 5s 与旧设计一致 —— nowSec 进 sig 从来不产生更细粒度, 只是白搭每拍重建)。守阵: `test_drawer_tpl_trackers_per_tracker_reannounce` ④ 改钉结构 sig(原钉 nowSec 进 sig, 与新设计冲突), 新增 `test_drawer_tpl_data_beat_no_anchor_move` 跨六变体钉「sig 无数据口径 + 回填在跳过路径上 + paintHtml 判空同值跳过」。
> 基线时间: 2026-10-12 22:36

上一基线：memory-bank/testing/baselines/26-10-12-2115-webui-drawer-tpl-flicker-fix2.md

## 验收数字

- `test.full`: **3148 passed + 4 skipped** / 覆盖率 `TOTAL 16708 161 5688 140 99%`(98.63%, 与上一基线 3147 相比 +1 = 本波新增守阵 test_drawer_tpl_data_beat_no_anchor_move; 原 1 failed 的 nowSec 守阵已按新设计适配转绿)。
- 抽屉回归(13 套): drawer-bridge-stub + trackers/peers/content 三套 variant-tables + peers-sticky-flush + drawer-merge + trackers-reannounce + tables + peers + peers-columns + groups-shows + content-dt11-sticky + dock-stability 共 **70 passed / 0 failed**(2.5m, 含 04-09 全部手势: 引擎排序三态/拖宽/右键隐藏/筛选 anchTouch/折叠/只看在传/msg)。
- 帧间隔/longtask 探针(临时, 未进仓库; 80 peers/trackers 真量级 + dict 真形态 + 每拍值变/序变/组分变): 六变体宿主整批换帧 **0 次/拍**(修复前每拍 1 次), **longtask 全部归零**(修复前 56-75ms/拍), 行文本/卡值/chips/组头计数每拍实时; 成本拆分实验(排除壳层重建 / 保留计算只不动锚)双双归零 ⇒ 冻源 = 锚移动。

## 本波改动面

- **生产代码**(7 文件): `shared/drawer_templates.js`(新 helper paintHtml + 病根注释); `drawer_tpl/` 六变体 04/05/06/07/08/09(sig 结构态 + 跳过分支原地回填 + 构建器抽出); `shared/tpl/xtpl.html`(桥模板 v-if 判空改 seg.rows.length)。
- **测试**: `tests/test_webui_static_dom_panel.py` —— reannounce 守阵 ④ 改钉结构 sig + rowsFn 现读 nowSec + 工具条回填; 新增跨变体守阵 `test_drawer_tpl_data_beat_no_anchor_move`。
- **知识库回写**: 坑档「复发 +1(第八次)」(判别/处置/验证 + 探针纪律再添两条: 量级不复刻测不出闪、身份探针全绿≠不闪必须上帧间隔/longtask); activeContext 切片 `26-10-12-2223-webui-drawer-tpl-flicker-fix3.md`(补三行头元数据)。

## 已知偏差 / 移交

- 07/08 残留 33-59ms 慢帧/拍(行补丁固有: dt0X-cells 行模型比经典 peer-cells 重; 掉帧非冻帧, 无中间态绘制)。若要再压: 行模型瘦身或可见列数裁剪, 属引擎层优化, 另立题。
- content 10/11/12 无 5s 轮询(不周期性渲染), 未做同款改造 —— 其整帧重建发生在换目标/开页签, 数据确为整包变更, 重建正确。
- 存量转告(同前): ① `modules/webui-static-contract.md` 超 evergreen cap(33,064 > 20,000, 本波未增长); ② activeContext 切片数债务(> 70, 本波 +1); ③ 引擎表头 a11y 缺口 issue 26-10-12-0800(Open 未认领)。
- 未 commit / 未 push(用户未发指令); 若真机仍有残余闪烁, 按本轮探针手法(帧间隔 + longtask + MutationObserver + 80 量级)扩展取证, 重点先看是否落在 07/08 行补丁量级(掉帧非冻帧)还是仍有整帧重建回归。
