# 26-10-12-2223 WEBUI 种子详情模板表格每 5s 闪烁根治(第八次复发)

> 摘要: 用户二次报障「闪烁没有修好 + 数据不实时刷新而是随闪烁刷新 + 疑与 5s 自动刷新有关」+「我一开始就说了是种子详情页所有表格」。第七次(beca3f6a)修 dtSyncAnchors 多锚假阳换代未触及数据拍整帧重建本身。病根(帧间隔+longtask 双证, 80 对端真量级): 六个桥变体(04/05/06 trackers + 07/08/09 peers)render 的 sig 全含整包列表数据 ⇒ 5s 轮询每拍必整帧重建 ⇒ anchFill 移动锚 ⇒ 锚里 Teleport 的整表整树重排 —— 07 实测每拍 52-93ms 慢帧 + 56-75ms longtask, 经典表同数据量 0ms; 成本拆分实锤冻源 = 锚移动(重排)非 HTML 计算。前七次探针全绿因 harness 桩 12 条(重建 <16ms 一帧内完成无中间态) + 无 SSE —— 量级与驱动必须同时复刻。修复(7 文件): 核心新 helper paintHtml(数据依赖子树原地 innerHTML 回填, 同值跳过); 六变体 sig 收窄为结构态(加载/失败/空态/在场分组集/折叠态), 数据拍走 skipUnchanged 跳过分支 + 回填壳上数值(共用构建器: 07 cardsHtml/barHtml · 09 barHtml · 08 组头 gcnt/gagg · 04 overviewHtml · 05 stripHtml+徽章 · 06 toolbarHtml); xtpl.html 桥模板 v-if 判空 sortedDrawer().length → seg.rows.length(每拍每段少排一遍 80 行); 06 sig 去 nowSec(逐行倒计时走桥响应式, 粒度恒 5s 与旧设计一致)。验证: 六变体 80 量级探针宿主整批换帧 0 次/拍、longtask 全归零、数据每拍实时; 抽屉 e2e 13 套 70/70; test.full 见基线切片。

> 最后活动: 2026-10-12 22:32

**Refs:** memory-bank/pitfalls/web-ui/drawer-switch-flicker.md,memory-bank/testing/baselines/26-10-12-2115-webui-drawer-tpl-flicker-fix2.md,memory-bank/tasks/26-10-12-webui-drawer-table-rework.md

## 背景

用户二次报障: 「未修复成功, 种子详情用户页的几个模板表格, 数据不实时刷新, 而是随闪烁刷新,
猜测和『5s 自动刷新』有关」+「我一开始就说了是种子详情页所有表格」。第七次(beca3f6a)修的是
dtSyncAnchors 多锚假阳换代, 未触及数据拍整帧重建本身。

## 病根(实测定位, 非推理)

六个桥变体(04/05/06 trackers + 07/08/09 peers)render 的 sig 全含整包列表数据 ⇒ 5s 轮询每拍
必整帧重建(replaceChildren + anchFill **移动锚**) ⇒ 锚里 Teleport 的整表**整树重排**。

帧间隔 + longtask 双证(80 对端真量级):
- 变体 07: 每拍 52-93ms 慢帧 + 3 个 56-75ms longtask
- 经典表(同数据同拍): **0 慢帧 0 longtask**
- 成本拆分: 排除壳层重建 ⇒ longtask 归零、慢帧 33-46ms; 保留计算只不动锚 ⇒ 同样归零
  ⇒ **冻源 = 锚移动(重排), 非 HTML 计算**

harness 前七次探针全绿的原因: 桩数据 12 条(整帧重建 <16ms 一帧内完成, 无中间态可绘) + 无 SSE。
**量级与驱动必须同时复刻**。

## 修复(7 个文件)

- `drawer_templates.js`: 新 helper `H.paintHtml(host, sel, html)` —— 数据依赖子树原地回填
  (innerHTML 相同则跳过写); 文档注释记入病根与判据
- 六个变体: sig 收窄为**结构 sig**(加载/失败/空态/在场分组集/折叠态), 数据不进 sig; 数据拍走
  skipUnchanged 跳过分支 + paintHtml 原地回填壳上数值(各自抽出与整帧重建共用的构建器:
  07 cardsHtml/barHtml · 09 barHtml · 08 组头 gcnt/gagg · 04 overviewHtml · 05 stripHtml+徽章 ·
  06 toolbarHtml); 行走桥响应式(drawer.peers 更替 → 根重渲染 → 行原地补丁)
- `tpl/xtpl.html`: 桥模板 v-if 判空 `sortedDrawer(...).length` → `seg.rows.length`
  (排序不减长度; 原写法每拍对每段多排一遍 80 行)
- 06 sig 去 nowSec: 逐行倒计时只在桥行、随根重渲染重算, 粒度恒 5s(_dtNotify 只随数据落袋触发),
  nowSec 进 sig 从来不产生更细粒度, 只是白搭每拍重建

## 验证

| 项 | 结果 |
|---|---|
| 六变体 80 量级探针 | 宿主整批换帧 **0 次/拍**(前: 1), longtask **全归零**(前: 56-75ms), 数据每拍实时 |
| 04 单独 | 0 慢帧 0 longtask(卡片壳最轻) |
| 抽屉 e2e 13 套 | **70/70**(含 04-09 全部手势) |
| test.full | 见基线切片 |

## 遗留

- 07/08 残留 33-59ms 慢帧/拍(行补丁固有: dt0X-cells 行模型比经典 peer-cells 重; 掉帧非冻帧,
  无中间态绘制)。若要再压: 行模型瘦身或可见列数裁剪, 属引擎层优化, 另立题
- content 10/11 无 5s 轮询(不周期性渲染), 未做同款改造 —— 其整帧重建发生在换目标/开页签,
  数据确为整包变更, 重建正确
