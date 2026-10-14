# webui-pinned-first-cell-bg — 必现列背景与其他列不一致: 按面重锚(专题 Done)

> 摘要: 专题 webui-pinned-first-cell-bg.
> 最后活动: 2026-10-15 03:50

## 正在进行

- 用户报「必现列背景与其他列不一致」, 报障面 = 主表三页(种子/辅种/追剧)
  + 种子详情面板全部变体表格(附录报告 26-10-14-0136)。专题 Done。
- 两层根因(逐面量计算样式 + 像素双口径实证):
  ① 皮肤 views.css `.group-row > :first-child{background:var(--bg-row)}`
    是**主列表行语言**; 抽屉各引擎面复用 .group-row(外壳/桥零特判, D5)
    ⇒ 首格规则漏进抽屉, 与各面行板三样各算(族面 --tbl-face-bg→--bg /
    04 卡 --bg-card / 05·10 透明 / 08 引擎 --bg-row), 行内一条异色竖带
    (prism/frost 行板 242,246,251 vs 首格 247,250,253; ocean Δ 16/255);
  ② 追剧表 search-hit 行底是「90deg accent 渐层 over --bg-row」, 首格只
    平铺 --bg-row ⇒ 整条渐层丢失(实测首格 backgroundImage=none, 左缘
    最强处 Δ≈18/14/9)。
- 附带查出 05 变体**行容器接线坑**: 家族结构 = 外层 .dtNN-wrap(外壳) + 内层
  .dtNN-list(行容器), 05 修前只有单层 dt05-wrap、行直接挂下面 ⇒ CSS 前缀
  .dt05-list 全程不匹配, 六条 .group-row 版式规则空转, 行一直带主表卡底
  (inList=false/inWrap=true 实测); 修法 = 补内层 .dt05-list 包住分区。
  ⚠ 首版直接把外层改名 dt05-list, "全仓搜无引用"漏了 e2e 动态拼接的
  `.dt${variantId}-wrap`, 全量 @fast 2 例红当场抓住(判据元教训已入坑档⑧)。
- 修法单点 shared/dt_table.css「必现列按面重锚」段: 族面 06/07/09/11
  首格同行板 Token + 悬停同 --bg-hover; err/bad/is-chk/sel 半透明 tint
  一律 `linear-gradient(tint,tint), var(--bg-card)` 合成(承光底是抽屉
  卡底, **不是** --bg-row); 04/05 首格 = 内容根 ⇒ 摘底 + position:static;
  10 保留吸左取 --bg-card; 08 bad 补合成; 族表头首格显式同 --tbl-head-bg;
  三皮肤 views.css 补 search-hit 首格同款渐层镜像。
- 守阵/量具: pytest 新增 `test_frontend_pinned_first_cell_bg_per_face`
  (静态两文件 59/59 绿); e2e dt-table-face-bg.spec.mjs 扩八面 + 状态行 +
  05 专用 + search-hit 镜像(本 spec 38/38 绿), **@fast 全量 166/166 绿**
  (修前基线 128 例, 本 spec 新增 38 例)。
- 坑档回填: pitfalls/web-ui/frozen-column.md 增 ⑥⑦⑧(按面重锚/search-hit
  渐层镜像/外壳类名接线); pitfalls/testing/smoke.md 端口复发 +1
  (8137 被 auto-qb-clone5 残留桩占, curl 被环境代理蒙骗, 以
  Get-NetTCPConnection 现查为准)。

## 下一步

- 无 —— 待 @fast 全量收尾确认后随主提交入库。
- 若用户复查仍见竖带: 先问「哪个面/哪个主题/常态还是悬停」, 用
  dt-table-face-bg.spec.mjs 同款探针(可见底色合成)逐面量; 主题面重点
  看 ocean(Δ 最大的暗色主题)。
