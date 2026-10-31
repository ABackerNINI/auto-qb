# 种子详情面板重构(字符串 DOM 变体 → Vue 面板) · W3 已落地

> 摘要: 用户命题「按推荐实施 [计划 26-10-11-2106]」= 拍板点 **D1–D4 一律取推荐项 A**(Vue 3 组件重建 · 收敛为声明式密度变体 · 按页签分波替换 · 三列表注册进 `<aq-table>`)。**W0** = 冻结契约与验收基线; **W1** = 数据层抽离(A/B DOM dump 逐字节等价); **W2** = 四页签 Vue 重建 + 三列表接壳(拍板「全部一起做」+「Vue 连变体一起声明式实现」+「div 网格与主视图同源」+「观感变化整体接受」)。**W3**(本轮 26-10-12-0009)= 流量页签与形态收敛: 用户先拍板「**缺陷留到 W5**」(`esc-attr-quote-dead-class` 不回灌 15 个变体, 随 W5 退役消失 —— 上轮的未决拍板项就此了结), 随后「继续 W3」。新增 `shared/drawer_head.js` + `tpl/drawer-head.html`: `<aq-drawer-head>` 收掉「两形态各一份头部」复写, `<aq-qb-ctl>`(**多根片段**)让控件组两挂点共用一份实现; `drawer.kind` 判据收归 `drawerIsSeed`/`drawerIsTraffic`; **有意偏差**: 流量正文留在壳模板(根实例 `$refs` 取不到子组件 ref, 搬进组件图表静默不画)。`test.full` 3130 passed(基线 + 新增 1 条守阵)/ e2e 164 passed 与 W2 基线逐位一致; 四条红验(RC1 拆双头部 / RC2 包 wrapper / RC3 翻谓词 / RC4 回退 qbCurPending)均 rc=1, 其中 RC2 实证**类名 count 守阵对 wrapper 回潮失明**, 已补结构级判根。数字见基线切片。W4–W6 待起。
>
> 最后活动: 2026-10-12 00:09

**Refs:** memory-bank/tasks/26-10-11-webui-drawer-refactor.md,memory-bank/testing/baselines/attachments/26-10-12-0009-webui-drawer-refactor-w3.md

## 本轮完成 (W3)

- **头部件单点**: 新增 `AQ_DRAWER_HEAD_COMPONENT`(props: tone/icon/text/textTitle/statusTitle; 后两者缺省 `null`, 流量形态不长出多余 title 属性)+ `AQ_QB_CTL_COMPONENT`; `tpl/drawer-head.html` 两个 x-template; `tpl/drawer.html` 两段 `<header class="drawer-head">` 复写换成 `v-if="drawerIsTraffic"` / `v-else` 两行调用, seed「流量」页签 `.qb-statctl` 挂点同接 `<aq-qb-ctl>`。三 shell manifest 成对登记(prism/console 压相邻 parts 项腾行, 208/204/208 行, cap 210 内)。
- **形态判据收口**: `drawer.js` 新增 `drawerIsSeed`/`drawerIsTraffic`/`drawerMember`/`drawerMemberKind`; 九处调用点同轮换(openTorrentDrawer / drawerAfterEnterHook / dtMenuMergeOn / openDrawerMenu / `_kbDrawerTab` / `_kbOpenDrawer` / `_kbToggleQbTraffic` / drawer.html 三形态分支)。全前端 `drawer.kind` 字面量仅剩两个谓词定义 + `qb_traffic_chart.js` 谓词(停手点冻结, 守阵注豁免, W6 收口时摘)。
- **守阵同轮改版(不放宽)**: `test_webui_static_dom_panel.py` 六条用例 pin 迁移 + 旧「两处控件组逐字同源」换成**更强的单点钉法**(单一实现 + 面板零拷贝 + 恰两挂点)+ 新增结构级判根 `_tpl_top_level_tags` + 新增 `test_frontend_drawer_form_judge_single_point`; `test_web_shortcuts.py` 七处 pin 同轮换。
- **验收**: `test.full` = 3130 passed + 4 skipped / `TOTAL 16517 151 5626 134 99%`; e2e = 164 passed + 0 failed + 10 skipped 与 W2 基线逐位一致(W3 验收口径是守阵, 未加 e2e 用例); 三皮肤 CSS 与 `qb_traffic_chart.js`/uPlot 零改动。

## 三处非显然的判断(下轮别再踩)

1. **`$refs` 只登记在声明它的实例上** —— 根实例方法经 `this.$refs[x]` 找 DOM 的, 目标节点要么留在壳模板, 要么补 DOM 兜底。W2(表头拖宽)与 W3(图表挂载点)连续两轮同病灶族; W3 因此把「薄包装」落在壳模板的 `v-if="drawerIsTraffic"` 分支而非组件, 并在 drawer.html 与守阵双向注根因。
2. **类名 count 守阵对「包 wrapper」失明** —— RC2 红验实证: wrapper 加进来类名计数一个不变、全绿, 但三皮肤四组直接子选择器(`.drawer-head > .qb-tabs/.qb-tools` 与 `.qb-statctl > .qb-tabs/.qb-tools`)已全部静默失效。多根片段的根形态必须 HTML 解析 depth-0 结构判根(`_tpl_top_level_tags`), 字符串计数不可靠。
3. **props 缺省 `null` 才是「不加属性」** —— Vue 里 `:title="undefined"` 不渲染属性但 `:title="''"` 会渲染空 title; 头部件的 textTitle/statusTitle 缺省定为 `null`, 否则流量形态凭空长出 `title=""` 被 `ui_feedback.js` 迁成 `data-aq-tip`, 观感回归。

## 待办 / 移交

- **W4–W6 待起**: W4 = 合并双列 + 右键模板选择(计划给 W4 派了四条 e2e; 接壳后 `_drawerMenuColByX` 坐标兜底需复核); W5 = 15 变体 → 声明式密度变体(**已拍板** `esc-attr-quote-dead-class` 缺陷随 W5 退役消失, 不回灌修法); W6 = 退役第二套渲染技术(顺势摘 `qb_traffic_chart.js` 谓词冻结豁免, 换吃 `drawerIsTraffic`)。
- **债务(承接, 不拦提交)**: `modules/webui-static-contract.md` 超 evergreen cap(W2/W3 各加一条, 债务加深); `kb.check` 切片数 > 70。两项均需另开新会话收口。
- **工作树**: W2 + W3 两轮改动均未提交(用户未要求 commit)。
