"""test_webui_static_skins_table 测试计划: webui 前端资产静态守阵: 皮肤清单 / CSS / 挂件类名

## 测试计划(每个测试函数一条)
- test_frontend_hr_detail_table_wiring: HR 表① 全量详情表前端接线守阵(计划 26-10-01-2216 阶段2 + 26-10-02-1936 阶段3) —— 设置分区表① 模板绑定(档位 chips 本地过滤/已删除种子切换钮/明细行/空态/失踪行挂钩/「数据截至」时间戳/三列重组列名「核实结论」「在列」)+ 拍板守卫(remain_seconds 不进表、不挂 hr-pop、单元格无原生 title、表① 段无 <details>(排障视图在 aqb:hr-diag 独立段)、来源徽章类名 hr-vsrc 不复用已退役 hr-src)+ hr_status.js 按站点明细加载与本地筛选且无 setInterval(不轮询)+ .hr-detail-table 与档位色义四档/失踪行 --paused 弱化/来源徽章样式在三套 UI CSS 成对定义(prism 拆 components.css + views.css 两件)
- test_frontend_hr_table_sort_filter_reorg_wiring: HR 表① 已删除种子过滤 + 三态排序 + 三列重组守阵(计划 26-10-02-1936 阶段3; 文案 26-10-03 定) —— 切换钮默认「显示已删除种子 (N)」且 oldOn 默认关(只看本地仍在列), 旧误导文案「未做种/只看做种中」零残留; 表头十列全 sortable(26-10-29 修复 issue 26-10-29-1348: 列定义补齐 sortable: true —— HRS_SORT_VAL 十键全有访问器; P5 起 markup 收敛到表壳组件 thead 模式, 本守阵改钉 <tr is="vue:aq-table" mode="thead"> 接线 + HR_TABLE_DEFS 注册表十列键 + thead sortable 类/箭头门控同源 col.sortable)而表② 波次表无 sortable; 三态状态机(首点降→再点升→第三击恢复后端默认序, 换列直接降序); 比较器纯函数 hrsCompareRows 用 node 真跑(空值恒末位两方向不反转/verified_ts·last_seen 0 哨兵/档位 A<B<C<D 固定秩/字符串数值分型), 无 node 静默跳过; 新列结构(核实结论徽章+副行 / 在列·失踪徽章+副行)与 CSS 三处成对(th.sortable 箭头 accent·hover faint / .hr-sub 副行 / .hr-pres 徽章 / 名称列限宽钩子 + .hr-full-modal 放开); 旧列辅助 hrsVerifiedText/hrsStatusText 与死件 hrsArrowHref 零残留; 表① 排序箭头绝对定位不占流(计划 26-10-06-1009 §7: 原 display:inline-block 恒占 14px, 把右对齐 num 列表头文字整体左顶)
- test_frontend_table_registry_single_point: 表注册表守阵(计划 26-10-11-1722 P0) —— app.js 必须有 `TABLE_DEFS` 且 `TABLE_PAGES` 由它派生(第二份表清单即红), 四张表(group/detail/torrent/show)的 `columns`/`headRef`/`tableRef` 必须指向既有单点且顺序 = 定义序(顺序漂移 = 列偏好按错表读), `columns.js`/`sort.js` 里四页字面量与 `viewMode` 分派零残留(复活即红 —— 那正是本单点要消灭的重复)
- test_frontend_table_shell_single_point: 表壳/行模型单元格渲染器单点守阵(计划 26-10-11-1722 P1/P2/P3/P5) —— 表头块 5 份内联副本收敛为 `<aq-table>`(shared/table.js + tpl/xtpl.html#tpl-aq-table); 127 条行模型单元格 v-if 分支收敛为五个单份渲染器 `<aq-member-cells>`(member, xtpl.html)/`<aq-group-cells>`/`<aq-torrent-cells>`/`<aq-show-cells>`/`<aq-ep-cells>`(tpl/xtpl-cells.html); 钉 ①六个组件都 app.component 注册 ②表壳模板恰一份且四件交互把手(.h-cell/.h-label/.arrow/.resizer/.col-drop-line)齐备 ③groups.html/shows.html 各 2 个、torrents.html 1 个 `<aq-table>` 调用点、三个页面模板 `.h-cell` 内联零残留、各页行模型渲染器调用点齐备 ④thead 模式(P5): 设置页 HR 详情表表头借壳, 占位须 `<tr is="vue:aq-table" mode="thead">` 且该段内联 `<th>` 零残留; thead 可排序性判据同源 col.sortable(sortable 类与箭头 v-if 由它驱动, issue 26-10-29-1348)
- test_frontend_frozen_column_boundary_wiring: 首列吸左边界提示守阵(2026-10-11 修「向右滚动时状态列被名称列盖住」) —— 横滚时相邻列滑进吸左首格(26-10-06-1717)下方, 未盖满的尾字("做种"的"种"等)紧贴首格右缘露出, 无边界提示时残根读成与名称省略号粘连的坏字(误读成渲染 bug); 钉两层接线: 横滚同步单点 columns.js::syncHeadScroll(ev, page)(P4 把 menu/selection/shows 三份收敛为一份)必须给滚动容器与吸顶表头打 .is-hscrolled(scrollLeft>0 打 / 回 0 摘, CSS 无法感知 scrollLeft, 丢标 = 落影永不出现)且三个滚动容器各带表 id 调用它, 三皮肤 views.css 的 .is-hscrolled 规则必须行吸左首格与表头吸左首格成对(漏表头 = 列名残根仍裸露)且含发丝线(inset -1px)成分、且**不得**再带右缘落影(2026-10-12 用户报「名称列后随机出现阴影」: 落影可见度随首格高度变, 常态行首格 22px 时塌成 2px 近不可见、高行才显形, 逐行深浅差 7 倍读成随机黑块)
- test_frontend_hscroll_indicator_wiring: 主表横滚指示条守阵(计划 26-11-01-0553 S4) —— 原生横条隐藏 + 底部胶囊单点 shared/hscroll.css: 两条隐藏声明缺一即红(只写 ::-webkit-scrollbar 时 Firefox 仍画条槽 / 只写 scrollbar-width 时 Chromium 系仍画, 全局 `*{scrollbar-width:thin}` 挡不住)、三皮肤各恰挂一次且排在本皮肤 views.css 之后(link 序即级联序, 排前面被页面级规则反压)、三皮肤 /shared/*.css 链接集逐字相同(挂载漂移 = 某皮肤缺规则而规则只有一份, 整条静默失效; shared/fx/* 豁免 —— fx 只挂 flux, 计划 26-10-31-2316 D14 隔离拍板)、皮肤自有 CSS 零第二份隐藏声明(副本 = 日后各自漂移)、CSS 四类名与 columns.js 建 DOM/classList 同侧(改名只改一侧 = 胶囊恒不可见且零报错)、syncHeadScroll 尾部仍调 _hscrollSync 且主表白名单 group/torrent/show 齐全(删接线 = 胶囊永不出现 / 删白名单 = 抽屉面 xtpl.html:360 每次横滚在 body 留一个永不用的胶囊)、_hscrollBind() 调用点在 _ensureHeadObserver 体内(退回挂在 _hscrollPill() 里 = 从没横滚过的纯鼠标用户永远见不到胶囊, 而「纯鼠标没有拖拽入口」正是本方案要补的洞)
- test_frontend_pinned_first_cell_bg_per_face: 必现列(吸左首格)底色按面重锚守阵(2026-10-14 修「必现列背景与其他列不一致」, 报障面 = 主表三页 + 抽屉全部变体表格) —— 两层根因: ① 皮肤 `.group-row > :first-child{background:var(--bg-row)}` 是主列表行语言, 抽屉各引擎面复用 .group-row(零特判)致首格与行板三样各算(族面 --tbl-face-bg→--bg / 04 卡 / 05·10 透明 / 08 --bg-row), 行内一条异色竖带(ocean Δ 16/255); ② 追剧表 search-hit 行底是「accent 渐层 over --bg-row」而首格只平铺 --bg-row, 整条渐层丢失(实测 backgroundImage=none)。修复单点 shared/dt_table.css 按面重锚: 族面 06/07/09/11 行板/表头首格同 Token(--tbl-face-bg/--tbl-head-bg) + 悬停 --bg-hover, err(06)/bad(07/09)/is-chk(11)/sel(10) 半透明 tint 一律 `linear-gradient(tint,tint), var(--bg-card)` 合成(**禁** --bg-row 基色/裸半透明令牌), empty-row 随行透明; 04·05 首格是内容根 ⇒ 摘底摘 position:static(05 failrow 保 error-soft); 10 保留吸左取 --bg-card; 08 bad 补合成; 三皮肤 views.css 补 search-hit 首格镜像(90deg 渐层 46% + --bg-row); 05 变体补内层行容器 dt05-list(家族两层 dtNN-wrap+dtNN-list, 修前单层 dt05-wrap 与 CSS 前缀不匹配致六条 .group-row 规则空转、行带主表卡底)。真浏览器量具 e2e/dt-table-face-bg.spec.mjs(首格可见底 == 行板可见底, 含悬停与 err/bad/is-chk/sel 状态行)
- test_frontend_table_head_a11y: 引擎表头可访问性守阵(issue 26-10-12-0800, 计划 26-10-12-2330 方案 C) —— 语义载体用 role="columnheader"(**不是** button: aria-sort 只对该 role 生效, 挂 button 上读屏忽略) + 件套单点(shared/table.js 的 headAriaSort/headActivate 两方法, grid/thead 共用) + grid .h-cell 的 :aria-sort/:tabindex(仅可排序列)/Enter·Space keydown 全走 headActivate + .group-head role=row / 指示线 role=presentation + thead <th> 同补件套 + 各皮肤 .h-cell.sortable:focus-visible(atlas/prism 落 views.css; console/flux 落 components.css —— 后者曾顶 700 行 cap; flux S5 收编); 键盘真按键行为在 e2e/table-head-a11y.spec.mjs
- test_frontend_pinned_first_cell_hover_transition_parity: 必显列(吸左首格)悬停过渡与行板同源守阵(2026-10-20 修「必显列鼠标滑过时背景与其它列不一致, 短暂后恢复一致」) —— 行板 `.group-row` 有 transition: background var(--dur)(160ms) 而吸左首格无过渡 ⇒ 滑入瞬间首格 snap 到 --bg-hover、其余列还在从 --bg-row 渐入, 160ms 内行内一条竖带, 过渡完才"恢复一致"(真浏览器逐帧: prism/frost Δ14、atlas/ocean Δ18, 三主表 × 双皮肤全中; 移出同理反号); 钉 ①行板过渡仍以 `background var(--dur)` 声明(时长基准) ②各皮肤 `.group-row > :first-child` 体内 `transition: background-color var(--dur)`(禁字面毫秒, 否则行板调时长又漂) ③首格悬停镜像 `:hover > :first-child` → `--bg-hover` 不得丢(丢了是整段悬停期的持久竖带) ④首格过渡**只在各皮肤 views.css 单点**, 抽屉按面重锚(dt_table.css)与变体注入 CSS 不得自带 `transition`(带即脱离 --dur 与行板错拍; 2026-10-20 审计: 主表三页 + 经典抽屉表 + 06/07/09/10/11 六面逐帧差全 0; 26-10-30-0217 阶段2 起豁免 shared/row_lang.css —— 其 :first-child 上的 transition 只有行语言名称列左条 ::before 的 .12s 本体动效(D4 拍板 M2); 首格 hover/选中底为 color-mix 纯色换 background-color(26-10-30 复验二修, ::after 已撤销), 过渡继承 views.css 单点)。flux 收编定案(S5, plan 26-10-31-2316): 随 _UI_ALL 自动罩住 —— fork 后规则逐字同 console 天然满足; S6 挂 fx 动效时若要动行板/首格过渡, 必须仍守「views.css 单点 + var(--dur) 同源」前提, 破前提先改本守阵。行为面(逐帧差 ≤ 2、稳态同色)由 e2e/main-table-pinned-hover.spec.mjs 真浏览器采
- test_frontend_pinned_first_cell_selected_row_keeps_base: 选中/半选行「保留行底」守阵(2026-10-20 修「选中的行必显列背景与其它列不一致」) —— 旧规则 `.group-row.selected { background: var(--sel-bg) }` 用半透明 tint **替换**行底(而非叠在行底上), 行板露出页底 `--bg`, 而吸左首格按 `--bg-row` 合成 ⇒ 两侧承光底分家, 选中行名称列整列异色竖带(真浏览器逐像素: atlas Δ9/255、prism Δ5/255, 三主表×双皮肤全中, 未选中行 Δ0); 钉 ①`.group-row.selected`/`.group-row.partial` 的 background 末层是 `var(--bg-row)`(裸半透明令牌即红) ②行板与首格镜像的 tint 同字面(`var(--sel-bg, var(--accent-soft))`) ③首格镜像合成基色与行板同令牌 ④拆分后 `.member-row.selected` 仍在(成员行无吸左首格, 保持裸柔底)。行为面(行板与首格计算背景逐字相等, 选中/悬停选中)由 e2e/main-table-pinned-selected.spec.mjs 采
- test_frontend_pinned_first_cell_expanded_row_keeps_base: 展开行「保留行底」守阵(2026-10-20 与选中态同轮收, 用户「group 一同修」) —— `.group-row.expanded { background: var(--bg-sunken) }` 同样把行底**替换**成半透明下沉底, 行板承光层变页底 `--bg`, 而首格按 `--bg-row` 合成; 真浏览器逐像素: 展开行 atlas Δ5/255、prism Δ2/255(低于可辨阈, 上轮按范围守恒未动); 钉 ①三皮肤 `.group-row.expanded` 的 background 末层是 `var(--bg-row)`(prism 在 views.css, atlas/console 在 components.css, 按选择器找) ②首格镜像同基色 ③console 独享的 `.group-row.expanded:hover` 不得跌回裸 `--bg-sunken`(否则悬停那一下又分家)。行为面由 e2e/main-table-pinned-selected.spec.mjs 的展开行用例采
- test_drawer_table_bridge_wiring: 桥接线守阵(计划 26-10-12-0527; W3 增补) —— 桥模板行源单点
  已从直调 sortedDrawer 收进 dtBridgeLines(窗表 = drawerWinView 窗口切片, 其余回落 sortedDrawer
  全量; 排序机仍只有 sortedDrawer 一份, drawer_templates.js 两支调用点任缺即红), 本守阵同步钉
  $root.dtBridgeLines(tab, seg) 在位 + sortedDrawer 调用点 ≥2(回落支 + 窗支)
- test_drawer_tpl_table_face_bg_single_point
- test_frontend_ctx_src_target_marker_parity: 右键目标行「持续可见标识」守阵(2026-11-02 用户报「强调动效结束后看不出右键目标行」) —— 四皮肤四行类 .ctx-src 全覆盖 + 静态实心 2px accent outline 框(outline-offset:-2px) + 禁用 box-shadow(row_lang flat 会归零, atlas 实测恒 none)与左条(与选中条同几何同色) + 规则体零 background/零 --sel-* 令牌(不被读成选中) + 零 animation(标识常驻菜单打开期而非闪一下) + 四皮肤逐字同值

## 皮肤档位口径
- 皮肤清单单点在 webui_helpers._UI_ALL(atlas/prism/console/flux); flux(第四套, plan 26-10-31-2316 S5)
  fork 自 console、只换令牌取值与视觉规则(类名/DOM/令牌名不动), 上述按 _UI_ALL 枚举的守阵随常量自动收编;
  单独点名的守阵(表头 a11y 落点/令牌 parity/按钮成对/HR 各族成对面)已显式加 flux 档。
"""

import json

import os

import re

import shutil

import subprocess

from webui_helpers import read_shared
from webui_helpers import (
    STATIC_ROOT,
    _UI_ALL,
    _ui_manifest,
    _ui_aggregate,
    _ui_css_files,
    _ui_css_aggregate,
    _ui_css_effective,
    _app_bundle_files,
    _app_bundle_text,
    _tpl_path,
)

from webui_static_scan_common import (
    _NODE_HRS_SORT_PROBE,
    _css_bg,
    _css_body,
    _css_rules,
)


def test_frontend_table_shell_single_point():
    """表壳 / 行模型单元格渲染器单点守阵(计划 26-10-11-1722 P1/P2/P3)

    表头块曾是 **5 份逐字近似**的内联副本(groups.html 组头 + 明细头 · shows.html 剧头 + 明细头 ·
    torrents.html 种子头); 行模型单元格曾是散在页面模板里的 **127 条 v-if 分支**。收敛为单点后,
    "又有人往页面模板里内联一份"是**静默**回潮: 页面照常工作, 单点却慢慢失效(改一处漏一处 ——
    正是本轮要消灭的维护点)。钉三层:
    ① 组件注册单点: `app.component("aq-table", window.AQ_TABLE_COMPONENT)`(表壳) 与五个行模型
       渲染器 —— 主视图五个 `<aq-member-cells>`(member) / `<aq-group-cells>`(group) /
       `<aq-torrent-cells>`(torrent) / `<aq-show-cells>`(追剧剧行) / `<aq-ep-cells>`(追剧集行);
       组件模板里的行为一律经 `$root` 回调根实例。
       (2026-10-22 加站点 chip 单点 `<aq-site-chip>`(收敛 issue 26-10-20-2231 / R23-B-09:
       group/torrent/ep 三处站点单元格的 11 行骨架合一, torrent 版顺带补上 search-hit)——
       chip 是**单元格内**元素, 组件根即 span.site-chip, 渲染 DOM 与旧三份逐字同,
       不触碰"单元格必须是行直接子元素"的 grid 约束。)
       (2026-10-14: 抽屉三表的 `<aq-tracker-cells>` / `<aq-peer-cells>` / `<aq-file-cells>`
       随「移除四内容页签经典 UI」一并删除 —— 那三张经典表只由已删的 drawer-tabs.html 渲染,
       四内容页签的表格体此后全部走变体桥。)
    ② 表壳模板唯一且内容齐备: tpl/xtpl.html 恰一份 `#tpl-aq-table`, 且四件交互把手
       (`.h-cell` / `.h-label` / `.arrow` / `.resizer` / `.col-drop-line`)都在里面 —— 把手丢了
       表现为"拖了没反应 / 右键没菜单", 无任何报错;
    ③ 接线单点: groups.html / shows.html 各 2 个 `<aq-table>` 调用点, torrents.html 1 个
       (种子页表头自 P3/P4 起也已迁移 —— 原 `.h-cell` 内联例外已删), **drawer-tabs.html 3 个**
       (W2: trackers / peers / content 三页签各一张), 且各模板里 `.h-cell` 内联零残留;
       各页面还必须有对应行模型渲染器的调用点(漏挂 = 该页值格全空)。
    ④ thead 模式(P5, 计划 26-10-11-1722): 同一个表壳的第二根 —— 原生 <table> 表头行, 设置页
       HR 详情表借壳。占位必须写成 `<tr is="vue:aq-table" mode="thead">`(in-DOM 表内容模型),
       且该段内联 `<th>` 零残留(回潮 = 表头 markup 又有第二份)。可排序性判据同源 col.sortable ——
       sortable 类与箭头 v-if 都由它驱动(issue 26-10-29-1348: 曾硬编码 class="sortable" 而行为侧
       headActivate 早退, HR 表排序整表静默失效)。
    """
    app_js = open(os.path.join(STATIC_ROOT, "shared", "app.js"), encoding="utf-8").read()
    comps = (
        ("aq-table", "AQ_TABLE_COMPONENT"),
        ("aq-member-cells", "AQ_MEMBER_CELLS_COMPONENT"),
        ("aq-group-cells", "AQ_GROUP_CELLS_COMPONENT"),
        ("aq-torrent-cells", "AQ_TORRENT_CELLS_COMPONENT"),
        ("aq-show-cells", "AQ_SHOW_CELLS_COMPONENT"),
        ("aq-ep-cells", "AQ_EP_CELLS_COMPONENT"),
        ("aq-site-chip", "AQ_SITE_CHIP_COMPONENT"),
    )
    for name, glob in comps:
        assert re.search(r'app\.component\(\s*"%s"\s*,\s*window\.%s\s*\)' % (name, glob),
                         app_js), (f'app.js 缺 app.component("{name}", window.{glob}) —— 组件未注册, 用到它的页面模板整块渲染不出来')
    table_js = open(os.path.join(STATIC_ROOT, "shared", "table.js"), encoding="utf-8").read()
    for _name, glob in comps:
        assert f"window.{glob} = {{" in table_js, f"shared/table.js 缺 window.{glob} 定义(组件单点被搬走/改名?)"
    xtpl = open(os.path.join(STATIC_ROOT, "shared", "tpl", "xtpl.html"), encoding="utf-8").read()
    for tid in ("tpl-aq-table", "tpl-aq-member-cells"):
        assert xtpl.count(f'id="{tid}"') == 1, f"shared/tpl/xtpl.html 的 {tid} 模板必须恰一份(表壳/渲染器单点)"
    xtpl_cells = open(os.path.join(STATIC_ROOT, "shared", "tpl", "xtpl-cells.html"), encoding="utf-8").read()
    for tid in (
        "tpl-aq-group-cells",
        "tpl-aq-torrent-cells",
        "tpl-aq-show-cells",
        "tpl-aq-ep-cells",
    ):
        assert xtpl_cells.count(f'id="{tid}"') == 1, \
            f"shared/tpl/xtpl-cells.html 的 {tid} 模板必须恰一份(行模型渲染器单点)"
    shell = xtpl[xtpl.index('id="tpl-aq-table"'):]
    shell = shell[:shell.index("</script>")]
    for handle in ('class="h-cell"', 'class="h-label"', 'class="arrow"', 'class="resizer"', 'class="col-drop-line"'):
        assert handle in shell, (f"#tpl-aq-table 缺 {handle} —— 表壳四件交互把手(列名/排序箭头/拖宽把手/重排指示线)缺一即静默失效")
    # thead 模式(P5, 计划 26-10-11-1722): 原生 <table> 表头行 —— 设置页 HR 详情表借壳。表头 markup
    # (sortable + 排序箭头)只此一份; 占位必须写成 `<tr is="vue:aq-table" mode="thead">` —— 根模板是
    # in-DOM 的(#app innerHTML), 浏览器只认表格内容模型, 自定义元素直接放 <thead> 会被 foster-parent
    # 移出表格(表现为表头整个消失), 故借 <tr> 占位 + `vue:` 前缀让编译器当组件。
    # 可排序性唯一判据 = 列定义 col.sortable(issue 26-10-29-1348): thead 曾硬编码 class="sortable"
    # 且箭头恒渲染, 而 headActivate 按 col.sortable 早退 —— 唯一调用方 HR 表十列全无标记,
    # 「看着能排」点着没反应。sortable 类与箭头门控必须与行为侧同源, 不得回退硬编码。
    assert 'mode="thead"' in shell and "#i-arrow-up" in shell, \
        "#tpl-aq-table 缺 thead 模式分支(sortable 表头行 + 排序箭头) —— HR 详情表借壳会退回内联副本"
    thead_seg = shell.split("<tr v-if=\"mode === 'thead'\">", 1)[1].split("</tr>", 1)[0]
    assert ':class="{ sortable: col.sortable, num: col.num }"' in thead_seg, \
        "thead 列头 sortable 类必须由 col.sortable 驱动(硬编码 class=\"sortable\" 与 headActivate 门控分叉, issue 26-10-29-1348)"
    assert '<span v-if="col.sortable" class="arrow"' in thead_seg, \
        "thead 排序箭头必须由 col.sortable 门控(不可排序列不得摆箭头位, issue 26-10-29-1348)"
    settings = open(os.path.join(STATIC_ROOT, "shared", "tpl", "settings-detail.html"), encoding="utf-8").read()
    settings_text = re.sub(r"<!--.*?-->", "", settings, flags=re.S)
    assert 'is="vue:aq-table" mode="thead"' in settings_text, \
        "settings-detail.html 的 HR 详情表表头未借表壳 thead 模式(须 <tr is=\"vue:aq-table\" mode=\"thead\">)"
    hrd = settings.split("aqb:hr-detail-table:begin")[1].split("aqb:hr-detail-table:end")[0]
    assert not re.search(r"<th[\s>]", hrd), \
        "HR 详情表段又出现内联 <th> —— 表壳单点回潮(表头应走 <tr is=\"vue:aq-table\" mode=\"thead\">)"
    # 页面模板接线: <aq-table> 调用点数(注释里提到不算) + 行模型渲染器调用点 + .h-cell 内联零残留
    for tpl, want_tables, cells in (
        ("tpl/groups.html", 2, ("aq-group-cells", )),
        ("tpl/shows.html", 2, ("aq-show-cells", "aq-ep-cells")),
        ("tpl/torrents.html", 1, ("aq-torrent-cells", )),
    ):
        raw = open(os.path.join(STATIC_ROOT, "shared", tpl), encoding="utf-8").read()
        text = re.sub(r"<!--.*?-->", "", raw, flags=re.S)
        n = len(re.findall(r"<aq-table\b", text))
        assert n == want_tables, (f"shared/{tpl} 的 <aq-table> 调用点应为 {want_tables}, 实为 {n} —— 表壳接线漏挂/重复挂")
        for comp in cells:
            assert f"<{comp}" in text, f"shared/{tpl} 未使用 <{comp}> —— 行模型渲染器接线漏挂(该页值格全空)"
        assert 'class="h-cell"' not in text, (f"shared/{tpl} 又出现内联表头块(.h-cell) —— 表壳单点回潮, 应走 <aq-table>")


def test_frontend_table_head_a11y():
    """引擎表头可访问性守阵(issue 26-10-12-0800, 计划 26-10-12-2330 方案 C)

    D3「排序并引擎」后旧手搓表头的 P3-4 件套随载体退役, 而引擎 aq-table 表头**从未具备** ——
    全域(主视图 4 + 抽屉 3 + 桥变体 8 + HR thead 1)表头键盘不可达、读屏不知排序态。方案 C 要点:
    语义载体用 role="columnheader"(不是 button —— aria-sort 只对该 role 生效), 件套收进表壳组件
    单点, grid / thead 两模式同轮。钉五条(缺一即静默退化):
    ① 件套单点: AQ_TABLE_COMPONENT 有 headAriaSort/headActivate 两方法(散在模板即回潮);
    ② grid 模式: .h-cell 有 role=columnheader + :aria-sort + :tabindex + Enter/Space keydown;
       .group-head 有 role=row、.col-drop-line 有 role=presentation(容器语义);
    ③ thead 模式: <th> 有 :aria-sort + :tabindex + keydown(原生 th 隐含 columnheader);
    ④ 激活单点: click 与 keydown 同走 headActivate(grid→$root.setSort / thead→$emit('sort'));
    ⑤ 三皮肤焦点可见: 各皮肤有 .h-cell.sortable:focus-visible(键盘能聚焦但看不见焦点 = 没做)。
    """
    table_js = open(os.path.join(STATIC_ROOT, "shared", "table.js"), encoding="utf-8").read()
    comp = table_js[table_js.index("window.AQ_TABLE_COMPONENT"):]
    comp = comp[:comp.index("\n};")]
    assert "headAriaSort(col) {" in comp and "headActivate(col) {" in comp, \
        "表壳组件缺 headAriaSort/headActivate 件套单点(a11y 属性/激活各写一份即回潮)"
    assert re.search(r"headAriaSort\(col\) \{.*?sortDir === 1 \? \"ascending\" : \"descending\"", comp, re.S), \
        "headAriaSort 未按 sortDir 出 ascending/descending(aria-sort 方向会与箭头分叉)"
    assert re.search(r'headActivate\(col\) \{.*?this\.mode === "thead".*?\$emit\("sort", col\.key\)', comp, re.S), \
        "headActivate 未按模式分派(thead 借壳须 emit, grid 走引擎单点)"
    assert "this.$root.setSort(col.key, this.tableId)" in comp, \
        "headActivate 的 grid 分支未调 $root.setSort(tableId 当 scope)"
    xtpl = open(os.path.join(STATIC_ROOT, "shared", "tpl", "xtpl.html"), encoding="utf-8").read()
    shell = xtpl[xtpl.index('id="tpl-aq-table"'):]
    shell = shell[:shell.index("</script>")]
    thead_seg = shell.split("<tr v-if=\"mode === 'thead'\">", 1)[1].split("</tr>", 1)[0]
    grid_seg = shell.split("<div v-else", 1)[1]
    assert 'role="columnheader"' in grid_seg, \
        "grid .h-cell 缺 role=columnheader(aria-sort 只对该 role 生效, 挂 button 上读屏忽略)"
    assert ':aria-sort="headAriaSort(col)"' in grid_seg, "grid .h-cell 缺 :aria-sort 绑定"
    assert ':tabindex="col.sortable ? 0 : null"' in grid_seg, "grid .h-cell 缺可排序列 tabindex(键盘不可聚焦)"
    assert '@keydown.enter.prevent="headActivate(col)"' in grid_seg \
        and '@keydown.space.prevent="headActivate(col)"' in grid_seg, \
        "grid .h-cell 缺 Enter/Space 转发(键盘激活不触发排序)"
    assert '@click="headActivate(col)"' in grid_seg, "grid .h-cell click 未走 headActivate 单点"
    assert 'role="row"' in grid_seg, "表头容器 .group-head 缺 role=row"
    assert 'role="presentation"' in grid_seg, "重排指示线 .col-drop-line 缺 role=presentation(污染 row 内容模型)"
    assert ':aria-sort="headAriaSort(col)"' in thead_seg, "thead <th> 缺 :aria-sort(HR 详情表读屏不知排序态)"
    assert '@keydown.enter.prevent="headActivate(col)"' in thead_seg, "thead <th> 缺 keydown 转发(键盘不可达)"
    assert ":tabindex=" in thead_seg, "thead <th> 缺 tabindex(键盘不可聚焦)"
    # atlas 落 views.css 而非 components.css: 后者顶 700 行 cap(views.css 首注有约定); console/flux
    # (flux fork 自 console)与 prism 各按 .h-cell.sortable 现有落点。
    for ui, rel in (
        ("atlas", "views.css"), ("console", "components.css"), ("prism", "views.css"), ("flux", "components.css")
    ):
        css = open(os.path.join(STATIC_ROOT, ui, "css", rel), encoding="utf-8").read()
        assert ".h-cell.sortable:focus-visible" in css, \
            f"{ui} 皮肤缺 .h-cell.sortable:focus-visible(键盘能聚焦但看不见焦点 = 等于没做)"


def test_frontend_table_registry_single_point():
    """表注册表 TABLE_DEFS 是「表身份」单点(计划 26-10-11-1722 P0)

    表身份(列定义 / 表头 ref / 行容器 ref / grid 与可见列 computed 名 / 行窗口化 kind / 排序键)
    此前散落在 `columns.js` 的四页字面量(`["group","detail","torrent","show"]`)、`_headEl` 的 ref
    名映射、`_winGapOf` 的三元分支与 `sort.js` 的 `viewMode` 分派里 —— 加一张表要改 4 处以上,
    漏一处是**静默**的(该表拖不动 / 排不了序, 无任何报错)。本守阵钉三层:
    ① app.js 有 `TABLE_DEFS` 且 `TABLE_PAGES` 由它派生(出现第二份表清单即红);
    ② 四张表各自的 `columns` / `headRef` / `tableRef` 指向既有单点, 且**顺序 = 定义序**
       (顺序漂移 = 列宽/列序偏好按错表读);
    ③ `columns.js` / `sort.js` 里四页字面量与 `viewMode` 分派零残留(复活即红)。
    """
    app = _app_bundle_text()
    assert "const TABLE_DEFS = {" in app, "app.js 缺表注册表 TABLE_DEFS(表身份单点被删/改名? 同步本守阵)"
    assert "const TABLE_PAGES = Object.keys(TABLE_DEFS);" in app, (
        "TABLE_PAGES 未由 TABLE_DEFS 派生 —— 又出现第二份表清单(新增表要改两处, 顺序也可能漂移)"
    )
    m = re.search(r"const TABLE_DEFS = \{(.*?)\n\};", app, re.S)
    assert m, "app.js TABLE_DEFS 不是 `const TABLE_DEFS = { ... \\n};` 形态(同步本守阵)"
    body = m.group(1)
    # (表 id, 列定义常量, 表头 ref, 行容器 ref | None) —— 顺序即定义序, 与旧字面量逐位一致
    want = (
        ("group", "GROUP_COLUMNS", "groupHead", "groupTable"),
        ("detail", "DETAIL_COLUMNS", "detailHead", None),
        ("torrent", "TORRENT_COLUMNS", "torrentHead", "torrentTable"),
        ("show", "SHOW_COLUMNS", "showHead", "showTable"),
    )
    for tid, const, head, table in want:
        seg = re.search(r"\n  %s: \{(.*?)\n  \}," % tid, body, re.S)
        assert seg, f"TABLE_DEFS 缺 {tid} 表(或段落格式变了, 同步本守阵)"
        s = seg.group(1)
        assert f"columns: {const}" in s, f"TABLE_DEFS.{tid}.columns 未指向 {const}(列定义单点断了)"
        assert f'headRef: "{head}"' in s, f"TABLE_DEFS.{tid}.headRef 不是 {head}"
        if table:
            assert f'tableRef: "{table}"' in s, f"TABLE_DEFS.{tid}.tableRef 不是 {table}"
        else:
            assert "tableRef: null" in s, f"TABLE_DEFS.{tid}.tableRef 应为 null(成员行容器 = .detail 父元素)"
    order = [app.index(f'headRef: "{h}"') for _tid, _c, h, _t in want]
    assert order == sorted(order), "TABLE_DEFS 的表顺序与定义序不符(TABLE_PAGES 顺序漂移 = 列偏好按错表读)"
    cols = read_shared("columns.js")
    assert '["group", "detail", "torrent", "show"]' not in cols, ("columns.js 又出现四页字面量 —— 应走 TABLE_PAGES(注册表派生)")
    sort_js = open(os.path.join(STATIC_ROOT, "shared", "sort.js"), encoding="utf-8").read()
    for probe in ('viewMode === "torrents"', 'viewMode === "shows"'):
        assert probe not in sort_js, (f"sort.js 又出现 {probe} 视图分派 —— 应走 TABLE_DEFS[id].sort(注册表单点)")

    # ---------------- 变体表格体接引擎(计划 26-10-12-0527; 2026-10-14 经典三表退役) ----------------
    # 抽屉变体表的**表身份**必须独立于 TABLE_PAGES: 并进 TABLE_DEFS 会让 TABLE_PAGES 把它们当"页面"
    # 参与行窗口化与"全表"动作, 而它们没有视图、也没有 3000 行的窗口化需求。但列的**交互引擎**
    # (拖宽/拖序/右键隐藏/持久化/对齐注入)要覆盖它们 —— 故引擎侧另取 ALL_TABLE_PAGES 全集。
    m2 = re.search(r"const DRAWER_TABLE_DEFS = \{(.*?)\n\};", app, re.S)
    assert m2, "app.js 缺 DRAWER_TABLE_DEFS(抽屉变体表的表身份注册表) —— 形态变了请同步本守阵"
    dbody = m2.group(1)
    # 2026-10-14: 经典三表(drawerTracker/drawerPeer/drawerFile)随「移除四内容页签经典 UI」删除
    # —— 不得回潮; 回潮即列选择器多出一个永不渲染的表分组(且经典渲染器已不存在)。
    for dead in ("drawerTracker", "drawerPeer", "drawerFile"):
        assert not re.search(r"\n  %s: \{" % dead, dbody), \
            (f"经典表 {dead} 的 def 不得回潮(2026-10-14 经典渲染链已删) —— "
             f"回潮即列选择器多出一个永不渲染的表分组")
    variant_tables = (
        ("drawerPeerV07", "DRAWER_PEER_V07_COLUMNS"),
        ("drawerPeerV08", "DRAWER_PEER_V08_COLUMNS"),
        ("drawerPeerV09", "DRAWER_PEER_V09_COLUMNS"),
        ("drawerTrackerV04", "DRAWER_TRACKER_V04_COLUMNS"),
        ("drawerTrackerV05", "DRAWER_TRACKER_V05_COLUMNS"),
        ("drawerTrackerV06", "DRAWER_TRACKER_V06_COLUMNS"),
        ("drawerContentV10", "DRAWER_CONTENT_V10_COLUMNS"),
        ("drawerContentV11", "DRAWER_CONTENT_V11_COLUMNS"),
    )
    for tid, const in variant_tables:
        assert tid not in body, (
            f"{tid} 混进了 TABLE_DEFS —— 变体表进了 TABLE_PAGES 就会被当成页面"
            f"(列选择器多一个'页面'/行窗口化多一个 kind); 表身份走 DRAWER_TABLE_DEFS"
        )
        seg = re.search(r"\n  %s: \{(.*?)\n  \}," % tid, dbody, re.S)
        assert seg, f"DRAWER_TABLE_DEFS 缺 {tid}(或段落格式变了, 同步本守阵)"
        s = seg.group(1)
        assert f"columns: {const}" in s, f"DRAWER_TABLE_DEFS.{tid}.columns 未指向 {const}(列定义单点断了)"
        assert "headRef: null" in s, ("抽屉表头渲染在变体外壳/桥模板内部, 根实例 $refs 取不到 —— "
                                      "headRef 必须是 null 走 _headEl 的 DOM 兜底")
        assert "dyn: true" in s, \
            f"DRAWER_TABLE_DEFS.{tid} 排序未走 dyn(变体表排序状态须进 dtSortState 映射, 按 table-id 通用存取)"
        assert f"const {const} = [" in app, f"app.js 缺列定义常量 {const}"
    # 列定义常量仍保留 —— 变体列集(DRAWER_*_V*_COLUMNS)由它们派生, 不是随表删掉的
    for const in ("DRAWER_TRACKER_COLUMNS", "DRAWER_PEER_COLUMNS", "DRAWER_FILE_COLUMNS"):
        assert f"const {const} = [" in app, f"app.js 缺列定义常量 {const}(变体列集仍由它派生)"
    # TABLE_PAGES 仍由 TABLE_DEFS 派生(不是 ALL_TABLE_DEFS); 引擎侧全集另有一条
    assert re.search(r"const TABLE_PAGES = Object\.keys\(TABLE_DEFS\)", app), \
        "TABLE_PAGES 不再是 Object.keys(TABLE_DEFS) —— 上面那条'抽屉表不进 TABLE_PAGES'的独立性判据就失效了"
    assert re.search(r"const ALL_TABLE_PAGES = Object\.keys\(ALL_TABLE_DEFS\)", app), \
        "app.js 缺 ALL_TABLE_PAGES(列交互引擎的表 id 全集)"
    # 三处**接线**(缺一即静默坏, 静态层面只能靠形态钉):
    # ① 表壳列头必须把自己的 tableId 当排序 scope 传下去 —— 传 undefined 会回落"当前视图的表";
    # ② sort.js 必须按表 id 解析 scope(抽屉三表各有一座独立排序键靠它);
    # ③ columns.js `_headEl` 必须有 DOM 兜底 —— 表头在页签组件内, ref 路径取不到它;
    # ④ 列选择器与"全表"两个动作都必须覆盖全集 —— 否则右键隐藏是不可逆动作(无恢复入口)。
    xtpl = open(os.path.join(STATIC_ROOT, "shared", "tpl", "xtpl.html"), encoding="utf-8").read()
    shell = xtpl[xtpl.index('id="tpl-aq-table"'):]
    shell = shell[:shell.index("</script>")]
    # 计划 26-10-12-2330: 列头 click 与 keydown 收进 headActivate 激活单点(2026-10-12), setSort 落
    # table.js 组件方法体 —— 断言从「模板含字面串」改为「模板走 headActivate + 组件内传 tableId」。
    table_js = open(os.path.join(STATIC_ROOT, "shared", "table.js"), encoding="utf-8").read()
    assert "headActivate(col)" in shell, \
        "表壳列头未走 headActivate 激活单点(click 与 keydown 须同路) —— 排序接线断了"
    assert "setSort(col.key, this.tableId)" in table_js, \
        ("表壳 headActivate 未把 tableId 当排序 scope 传下去 —— setSort 会按当前视图解析: "
         "点抽屉列头排的是主视图, 本表箭头永不出现(静默)")
    assert "ALL_TABLE_DEFS[scope] ? scope" in sort_js, \
        "sort.js `_sortKeys` 未按表 id 解析 scope(抽屉三表各自独立的排序键靠它)"
    assert '.group-head[data-table="' in cols, \
        ("columns.js `_headEl` 缺 DOM 兜底 —— 抽屉表头在页签组件内(根实例 $refs 取不到它的 ref), "
         "没有兜底时拖宽/双击自适应第一行就 return, 表现为'拖了完全没反应'且无报错")
    m3 = re.search(r"\n    tableDefs\(\) \{(.*?)\n    \},", cols, re.S)
    assert m3, "columns.js tableDefs computed 形态漂移(守阵正则失配, 同步本守阵)"
    # 26-10-12-0527 U1 改版: 全集遍历 + 变体表过滤(带 variantTab 的表只在对应变体被选中时
    # 进选择器)。恢复入口不变式不变 —— 变体选中期间右键隐藏的列仍可在选择器勾回; 经典表
    # (无 variantTab)恒在, 语义与全集逐位一致。
    assert "for (const id of ALL_TABLE_PAGES)" in m3.group(1) and "def.columns" in m3.group(1), \
        ("列选择器必须遍历**全集**(含抽屉三表): 表头右键隐藏是不可逆动作, 选择器不给入口就只能改 "
         "localStorage 才能把列找回来。这是计划 §07 括注的**有意偏差**, §11 变更记录已登记")
    assert "def.variantTab" in m3.group(1) and "dtBridgeTbl(def.variantTab) !== id" in m3.group(1), \
        ("变体表格体的选择器过滤失守: 八个变体表恒列出会把生产选择器撑爆 —— 只许在对应变体被"
         "选中时出现(经 dtBridgeTbl 反查), 过滤口只有这一处")


def test_drawer_table_bridge_wiring():
    """变体表格体 Teleport 锚桥接线守阵(计划 26-10-12-0527 U1 桥 + U2 分段/保活, D1 拍板)。

    桥 = 变体外壳字符串 DOM 锚 + <aq-dt-bridge> Teleport(表壳 + 行渲染器) + 锚代数单调换代。
    四件挂载时序路径(初开/切页签/软切换/合并双列)由 e2e/drawer-bridge-stub.spec.mjs 钉死,
    本守阵钉**接线不变量**: 断任何一环, 桥静默失效或内容写进游离旧锚(e2e 路径C 实测根因)。
    U2 段: 07/08/09 三变体接入(描述符/列集/渲染器/锚保活/触碰) + 变体文件零手搓排序状态机
    零列宽 grid(U5 终态判据的用户表份额, 先到先钉)。
    """
    import os
    import re
    shared = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src", "auto_qb", "webui", "static", "shared"
    )

    def read(*parts):
        return open(os.path.join(shared, *parts), encoding="utf-8").read()

    # ① state.js: dtBridge = { gen(单调), on } —— gen 永不回落(回落即 :key 净零 → 游离旧锚)
    st = read("state.js")
    m = re.search(r"dtBridge: \{\},", st)
    assert m, "state.js 缺 dtBridge 桥代数 data(U1 桥的锚代数表)"
    assert "gen **单调自增**" in st and "on = 锚当前在 DOM" in st, \
        "state.js dtBridge 注释口径漂移(gen 单调 + on 摘除两件必须写明 —— 那是路径C 红验换来的)"

    # ② drawer_templates.js: register 收 tableId/rowsFn(字符集校验) + 锚代数单调自增 + 卸载只摘 on
    dt = read("drawer_templates.js")
    assert 'throw new Error("[dt] register: bad tableId " + tableId)' in dt, \
        "register 未校验 tableId 字符集(tableId 要进选择器与锚属性, 与 id 同纪律)"
    assert "rowsFn: typeof entry.rowsFn === \"function\" ? entry.rowsFn : null" in dt, \
        "register 未收 rowsFn(桥变体行装配的回读口, U2)"
    assert "gen: (cur ? cur.gen : 0) + 1" in dt, \
        "锚代数必须**单调自增**(gen 恒定 = :key 净零 = Teleport 原地补丁进游离旧锚, e2e 路径C 红验根因)"
    assert "this.dtBridge[tid].on = false" in dt and "gen 保持单调, 只摘 on" in dt, \
        "卸载必须只摘 on(gen 保持单调)且不得清 gen"
    assert "data-dt-table-anchor" in dt, \
        "挂载/卸载机械未按锚属性 data-dt-table-anchor 扫描(锚约定单点, 见 table.js 对外契约④)"
    # ②b 锚对账/保活/触碰三件(U2): 对账在 _dtRender 尾部单点; 保活/触碰经 H 消费
    assert "function dtSyncAnchors(host, vm)" in dt and "dtSyncAnchors(st.host, this)" in dt, \
        "缺锚对账单点 dtSyncAnchors(挂载拍 + 数据通知 + 回落清宿主三路必须同走一处, U2 收口)"
    assert "anchFill: function (host, tableId)" in dt and "data-dt-anchor-slot" in dt, \
        "缺锚保活 helper anchFill(外壳整帧重建必须保住锚元素身份, 锚被重建 = Teleport 重挂 = 行抖动)"
    assert "anchTouch: function (host, vm, tableId)" in dt, \
        "缺锚触碰 helper anchTouch(变体 UI 态翻动后桥必须换代重读 rowsFn, 引擎对非响应式行源无感知)"

    # ③ 桥方法四件 + 取数六件(drawer.html 的 <aq-dt-bridge> 消费面; U2 加 Segs/RowCls/dtTplRows)
    for name in (
        "dtBridgeTbl", "dtBridgeOn", "dtBridgeTo", "dtBridgeKey", "dtBridgeDef", "dtBridgeRows", "dtBridgeRowKey",
        "dtBridgeRowModel", "dtBridgeRowProp", "dtBridgeRowCls", "dtBridgeSegs", "dtTplRows", "dtBridgeTargetOn"
    ):
        assert f"      {name}(" in dt, f"drawer_templates.js 缺桥方法 {name}(桥消费面被拆即静默失效)"
    # ③b Teleport 目标存在性判据(2026-10-14 合并态切换「内容消失」): 布局换代的 patch 顺序是
    # 「先拆旧分支(旧锚离场) → 再挂新分支」, 而父级 v-if(dtBridgeOn) 在拆之前求值 —— 判据必须在
    # **桥组件自己的渲染拍**(与 teleport mount 同拍)做, 否则那一窗里 teleport 挂到已消失的锚上:
    # Vue 生产版静默不挂子节点, 卸载时对 null component 解构抛 TypeError ⇒ 整次 patch 中断。
    assert "dtBridgeTargetOn(tab, seg)" in dt and "document.querySelector(sel)" in dt, \
        "缺 Teleport 目标存在性判据 dtBridgeTargetOn(锚离场那一窗挂 teleport = patch 中断 + 内容消失)"

    # ④ drawer.html: 桥挂点恰两处(单栏 v-for + 合并列), :key 含锚代数(换代纪律)
    drh = read("tpl", "drawer.html")
    assert drh.count("<aq-dt-bridge") == 2, \
        f"drawer.html 桥挂点应为恰 2 处(单栏 + 合并列), 实测 {drh.count('<aq-dt-bridge')}"
    assert drh.count(':key="dtBridgeKey(') == 2, \
        "桥挂点缺 :key=锚代数(不换代 = 宿主重建后内容写进游离旧锚)"
    # 2026-10-30 (26-10-29-1354): 单栏桥页签清单收进 dtTabItems(单点 DT_TAB_LABELS 投影) ——
    # 宿主与桥两个 v-for 共两处, 内联页签名数组字面量不得回潮。
    assert drh.count('v-for="t in dtTabItems"') == 2, \
        "单栏桥/宿主未按 dtTabItems v-for 自点亮(页签名数组字面量回潮会让页签清单存回两份)"

    # ⑤ 桥组件 + x-template: 表壳/行渲染器/滚动同步/引擎排序全走 $root 单点; 分段 teleport
    tbl = read("table.js")
    assert 'name: "aq-dt-bridge"' in tbl and 'template: "#tpl-aq-dt-bridge"' in tbl, \
        "table.js 缺 aq-dt-bridge 组件定义(桥的载体)"
    xt = read("tpl", "xtpl.html")
    m2 = re.search(r'<script type="text/x-template" id="tpl-aq-dt-bridge">(.*?)</script>', xt, re.S)
    assert m2, "xtpl.html 缺桥 x-template 分片"
    btpl = m2.group(1)
    assert "$root.dtBridgeTo(tab" in btpl, "桥模板 teleport :to 未走 dtBridgeTo 单点(锚约定)"
    assert btpl.count('v-if="$root.dtBridgeTargetOn(tab, seg.key)"') == 1, \
        "桥模板 teleport 缺目标存在性 v-if(dtBridgeTargetOn) —— 锚离场那一窗挂 teleport = patch 中断 + 内容消失"
    assert "$root.dtBridgeSegs(tab)" in btpl, "桥模板未走分段取数 dtBridgeSegs(U2: 分组变体逐段 teleport)"
    assert "<aq-table" in btpl and "-cells" in btpl, "桥模板必须复用表壳 + 行渲染器(不许自拼表格)"
    # W3(计划 26-11-02-0351)起桥行序走 dtBridgeLines 行源单点(窗表 = 窗口切片, 其余 =
    # sortedDrawer 全量) —— 模板不再直调 sortedDrawer; 排序机仍必须只有 sortedDrawer 一份
    # (dtBridgeLines 回落支与 drawerWinView 窗支都调它, 不得手拼比较器)。
    assert "$root.dtBridgeLines(tab, seg)" in btpl, "桥模板 v-for 未走 dtBridgeLines 行源单点(W3 窗切片/全量回落)"
    dtpl = read("drawer_templates.js")
    assert dtpl.count("this.sortedDrawer(") >= 2, (
        "drawer_templates.js 的 dtBridgeLines 回落支与 drawerWinView 窗支必须都走 sortedDrawer 单点 —— 手拼即第二份排序机"
    )
    assert "$root.syncHeadScroll(" in btpl, "桥缺表头横滚同步(横滚时表头不动 = 静默坏)"
    assert "$root.dtBridgeRowCls(tab)" in btpl, "桥行缺 rowCls 修饰类绑定(变体行级个性失守, D5)"

    # ⑥ sort.js: dyn 分支(变体表排序状态按 table-id 通用存取, 不再每表加 state 字段)
    srt = read("sort.js")
    assert srt.count("setSort(key, scope)") == 1, "sort.js setSort 出现重复定义(重构残留)"
    assert "if (s.dyn) return { dyn: true, id, defKey: s.defKey, defDir: s.defDir };" in srt, \
        "_sortKeys 缺 dyn 分支(变体表排序状态走 dtSortState 映射)"
    assert "def.sort.dyn ? this.dtSortCell(tableId)" in srt, \
        "sortedDrawer 缺 dyn 分支(变体表行序回退恒原序, 排序静默无效)"

    # ⑦ columns.js: 渐进列 omitEmpty 单点(07/08 的 qB files 字段整列省略)
    col = read_shared("columns.js")
    assert "_colsOmitEmpty(page, out)" in col and "c.omitEmpty" in col, \
        "_visibleCols 尾部缺 omitEmpty 单点(渐进列省略必须表头/行/grid/对齐同走一条路, 否则 nofiles 错位 bug 类回潮)"

    # ⑧ app.js: stub + U2/U3/U4 八描述符行 + 列子集 + 描述符导出口 + 渲染器注册
    app = read("app.js")
    assert "drawerStubV0: {" in app and "variantTab: \"peers\"" in app, \
        "app.js 缺 drawerStubV0 描述符行(U1 spike 的桥验证表)"
    for tid, segs, vtab in (
        ("drawerPeerV07", False, "peers"),
        ("drawerPeerV08", True, "peers"),
        ("drawerPeerV09", False, "peers"),
        ("drawerTrackerV04", False, "trackers"),
        ("drawerTrackerV05", True, "trackers"),
        ("drawerTrackerV06", False, "trackers"),
        ("drawerContentV10", False, "content"),
        ("drawerContentV11", False, "content"),
    ):
        assert f"{tid}: {{" in app, f"app.js 缺 {tid} 描述符行(U2 用户表/U3 tracker 表/U4 内容树变体接入)"
        blk = app.split(f"{tid}: {{", 1)[1].split("\n  },", 1)[0]
        assert 'rows: "dtTplRows"' in blk and f'variantTab: "{vtab}"' in blk and "rowCls: \"_cls\"" in blk, \
            f"{tid} 描述符缺 rows/variantTab/rowCls 三件(U2/U3/U4 桥契约)"
        assert ('segs: true' in blk) == segs, f"{tid} segs 声明与预期不符(08/05 分段桥, 其余单锚)"
    # U4 行级键盘面: 10/11 行容器 tabindex/data-dt-key + rowAfter 回调的声明位
    for tid in ("drawerContentV10", "drawerContentV11"):
        blk = app.split(f"{tid}: {{", 1)[1].split("\n  },", 1)[0]
        assert "rowTab: true" in blk and "rowAfter: true" in blk, \
            f"{tid} 描述符缺 rowTab/rowAfter 声明位(行级键盘 roving 面, issue 26-10-07-0846)"
    assert "const DRAWER_STUB_V0_COLUMNS = [" in app and "DRAWER_PEER_COLUMNS[0]" in app, \
        "stub 列子集未以经典用户列集为底裁剪(D2 口径: 列个性 = 数据声明)"
    tbl_cols_blk = app.split("const TABLE_COLUMNS = {", 1)[1].split("\n};", 1)[0]
    for cst, reg_key in (
        ("DRAWER_PEER_V07_COLUMNS", "drawerPeerV07"),
        ("DRAWER_PEER_V08_COLUMNS", "drawerPeerV08"),
        ("DRAWER_PEER_V09_COLUMNS", "drawerPeerV09"),
        ("DRAWER_TRACKER_V04_COLUMNS", "drawerTrackerV04"),
        ("DRAWER_TRACKER_V05_COLUMNS", "drawerTrackerV05"),
        ("DRAWER_TRACKER_V06_COLUMNS", "drawerTrackerV06"),
        ("DRAWER_CONTENT_V10_COLUMNS", "drawerContentV10"),
        ("DRAWER_CONTENT_V11_COLUMNS", "drawerContentV11"),
    ):
        assert f"const {cst} = [" in app, f"{cst} 未声明(变体列集 = 数据声明, D2)"
        assert f"{reg_key}: {cst}" in tbl_cols_blk, \
            f"{reg_key} 未注册进 TABLE_COLUMNS(_visibleCols 按 page 取列定义)"
    # 2026-10-13(计划 26-10-13-0811 铁律): 抽屉侧 omitEmpty 渐进声明清零 —— 轨道数随数据
    # 浮动是「多一格/少一列」类症状温床; 列常驻 + 渲染器 — 占位(avTxt / dt07·dt08-files)。
    # 机制 _colsOmitEmpty 保留(主列表「文件」列等共有路径仍在用)。
    assert "omitEmpty: true" not in app, \
        "抽屉列定义残留 omitEmpty 声明(渐进列随数据整列消失, 轨道数浮动, 已废除)"
    for comp in (
        "aq-dt07-cells", "aq-dt08-cells", "aq-dt09-cells", "aq-dt04-cells", "aq-dt05-cells", "aq-dt06-cells",
        "aq-dt10-cells", "aq-dt11-cells"
    ):
        assert f'app.component("{comp}"' in app, f"app.js 未注册 {comp}(U2/U3/U4 变体格渲染器没接线)"
    # U3: 04 分段钮排序并引擎的直设口(模式选择语义, 非 h-cell 三态循环)
    assert "dtSortSet(tableId, key, dir)" in srt, "sort.js 缺 dtSortSet(04 分段钮排序并引擎的直设口)"
    assert "window.AQB_DRAWER_TPL_DEFS = DRAWER_TABLE_DEFS;" in app, \
        "app.js 未导出 DRAWER_TABLE_DEFS 读取口(桥反查依赖, 经 window 中转保装载序)"
    assert "drawerStubV0: DRAWER_STUB_V0_COLUMNS" in app, \
        "TABLE_COLUMNS 未注册 stub 列集(_visibleCols 按 page 取列定义)"

    # ⑨ 渲染器分片: 六份 x-template + 列 key 配对(值格漏分支 = 表头在、值恒空)
    cells = read("tpl", "xtpl-cells.html")
    cells_dt = read("tpl", "xtpl-cells-dt.html")
    # !issue 26-10-20-2231(三族重复收敛): dt07/dt08/dt09 三份值格模板合一为单一
    # tpl-aq-dt-peer-cells(dt07≡dt08 逐字同, dt09 密度雷达三处特化经 pfx/occ 两个
    # prop 表达) —— 加一个 peer 列只改模板一处, 漏一处 = 三变体该列齐空白且无任何
    # 报错。守阵口径随之升级: 单一模板必须覆盖**三变体列键并集**(逐变体子集天然
    # 被覆盖; dt09 列模型无 files ⇒ files 分支对它是死分支, 无害)。
    tpl_blk = re.search(r'<script type="text/x-template" id="tpl-aq-dt-peer-cells">(.*?)</script>', cells, re.S)
    assert tpl_blk, "xtpl-cells.html 缺 tpl-aq-dt-peer-cells 分片(peers 三变体共用值格模板)"
    peer_keys = set()
    for colconst in ("DRAWER_PEER_V07_COLUMNS", "DRAWER_PEER_V08_COLUMNS", "DRAWER_PEER_V09_COLUMNS"):
        m3 = re.search(r"const %s = \[(.*?)\];" % colconst, app, re.S)
        assert m3, f"app.js 缺 {colconst}"
        peer_keys.update(re.findall(r'\{ key: "(\w+)"', m3.group(1)))
    for k in sorted(peer_keys):
        assert f"col.key === '{k}'" in tpl_blk.group(1), f"peers 共用值格模板缺 {k} 值格分支(表头在、值恒空)"
    for comp in ("dt04", "dt05", "dt06", "dt10", "dt11"):
        assert f'id="tpl-aq-{comp}-cells"' in cells_dt, f"xtpl-cells-dt.html 缺 tpl-aq-{comp}-cells 分片"
    # U3 tracker 三分片: 06 列驱动(逐列 key 配对), 04/05 单列满宽(卡片/分组行 = kind 分支非列分支)
    m3 = re.search(r"const DRAWER_TRACKER_V06_COLUMNS = \[(.*?)\];", app, re.S)
    assert m3, "app.js 缺 DRAWER_TRACKER_V06_COLUMNS"
    tpl_blk = re.search(r'<script type="text/x-template" id="tpl-aq-dt06-cells">(.*?)</script>', cells_dt, re.S)
    assert tpl_blk, "xtpl-cells-dt.html 缺 dt06 分片"
    for k in re.findall(r'\{ key: "(\w+)"', m3.group(1)):
        assert f"col.key === '{k}'" in tpl_blk.group(1), f"dt06 渲染器缺 {k} 值格分支(表头在、值恒空)"
    for comp in ("dt04", "dt05"):
        tpl_blk = re.search(
            r'<script type="text/x-template" id="tpl-aq-%s-cells">(.*?)</script>' % comp, cells_dt, re.S
        )
        assert tpl_blk and 'p.kind' in tpl_blk.group(1), \
            f"{comp} 渲染器缺 kind 分支(单列满宽行的形态分派: 卡片/虚拟卡、处置块/普通行/chips)"
    # U4 内容树两分片: 列驱动(逐列 key 配对 —— 树缩进格/勾选/大小/进度/[可用性]),
    # 空态合成行 kind 分支(筛选空 = 合成行, 非桥「暂无数据」泛化文案)
    for comp, colconst in (
        ("dt10", "DRAWER_CONTENT_V10_COLUMNS"),
        ("dt11", "DRAWER_CONTENT_V11_COLUMNS"),
    ):
        m3 = re.search(r"const %s = \[(.*?)\];" % colconst, app, re.S)
        assert m3, f"app.js 缺 {colconst}"
        tpl_blk = re.search(
            r'<script type="text/x-template" id="tpl-aq-%s-cells">(.*?)</script>' % comp, cells_dt, re.S
        )
        assert tpl_blk, f"xtpl-cells-dt.html 缺 {comp} 分片"
        for k in re.findall(r'\{ key: "(\w+)"', m3.group(1)):
            assert f"col.key === '{k}'" in tpl_blk.group(1), f"{comp} 渲染器缺 {k} 值格分支(表头在、值恒空)"
        assert "p.kind === 'empty'" in tpl_blk.group(1), \
            f"{comp} 渲染器缺空态合成行分支(筛选空态走变体原文案, 不落桥「暂无数据」泛化)"
    # 11 勾选三态声明式(原生 property, Vue patch 直持 —— 原 render 后补挂目录三态的面收进分片)
    m3 = re.search(r'<script type="text/x-template" id="tpl-aq-dt11-cells">(.*?)</script>', cells_dt, re.S)
    assert ":indeterminate=" in m3.group(1) and ":checked=" in m3.group(1), \
        "dt11 渲染器缺勾选框 :checked/:indeterminate 声明式(子树三态)"
    # 2026-10-14 用户复查修法(报告 26-10-14-0136 §02「操作按钮独立成列 / 展开按钮没有层级」):
    # tgl/prio 两条交互轨道已删 —— 折叠钮收编进 name 格首部(随缩进 =层级可视), 优先级徽章
    # 收编进 name 格尾部(margin-left:auto 右对齐, 不占轨道); name 列 locked(L4 续效: 交互件
    # 随格走, 隐藏 name = 一并废掉折叠钮与徽章)。回潮判据三条: 列集无 tgl/prio 键 / name 列
    # locked / 两个交互件都在 name 分支里(整分片只有一处 fold 与一处徽章动作属性)。
    # !2026-10-14 用户二次复查(报告 26-10-14-0136 §02 续): ck 勾选框仍独立成列且拖宽可调 ——
    # 勾选框收进 name 格首(随缩进); ck 列删除(终态 11 = name/size/prog/av 四列), 回潮判据
    # 续: 列集无 ck 键(dt11)/ 勾选框动作恰一次且 name 分支内.
    for comp, colconst, badge_act in (
        ("dt10", "DRAWER_CONTENT_V10_COLUMNS", "prio-menu"),
        ("dt11", "DRAWER_CONTENT_V11_COLUMNS", "prio-cycle"),
    ):
        m3 = re.search(r"const %s = \[(.*?)\];" % colconst, app, re.S)
        keys = re.findall(r'\{ key: "(\w+)"', m3.group(1))
        assert "tgl" not in keys and "prio" not in keys, (
            f"{colconst} 的 tgl/prio 独立列回潮 —— 折叠钮/徽章须收编进 name 格(用户 2026-10-14 复查: "
            f"「操作按钮独立成列」「展开按钮没有层级」)"
        )
        assert "ck" not in keys, (
            f"{colconst} 的 ck 独立列回潮 —— 勾选框须收进 name 格(用户 2026-10-14 二次复查: "
            f"「复选框仍然独立成列, 还能调整位置」)"
        )
        name_col = re.search(r'\{ key: "name"[^{}]*\}', m3.group(1))
        assert name_col and "locked: true" in name_col.group(0), (
            f"{colconst} 的 name 列必须 locked(交互件在格内, 隐藏 name = 废掉交互件, L4)"
        )
        tpl_blk = re.search(
            r'<script type="text/x-template" id="tpl-aq-%s-cells">(.*?)</script>' % comp, cells_dt, re.S
        ).group(1)
        assert tpl_blk.count('data-act="fold"') == 1, \
            f"{comp} 渲染器折叠钮须恰一次且在 name 格内(独立列回潮 = 层级丢失)"
        assert tpl_blk.count(f'data-act="{badge_act}"') == 1, \
            f"{comp} 渲染器徽章动作须恰一次且在 name 格内(独立列回潮 = 按钮占列)"
        if comp == "dt11":
            assert tpl_blk.count('data-act="ck"') == 1 and tpl_blk.count('data-act="dirck"') == 1, \
                f"{comp} 渲染器勾选框动作须恰一次(文件 ck + 目录 dirck)且收进 name 格内(独立列回潮 = 拖宽可调)"

    # ⑩ stub 变体: ?dtstub 门 + 桥声明 + 稳定 HTML 不变量
    stub = read("drawer_tpl", "90-peers-stub-bridge.js")
    assert 'indexOf("dtstub")' in stub, "stub 变体缺 ?dtstub 查询参数门(生产必须零观感)"
    assert 'tableId: "drawerStubV0"' in stub, "stub 变体未声明 tableId(桥契约的声明侧)"
    assert "H.skipUnchanged" in stub, "stub 变体缺 skipUnchanged(桥变体的稳定 HTML 不变量: 锚不得随轮询重建)"

    # ⑪ U2/U3/U4 八变体: tableId/rowsFn 声明 + 锚保活 + 零手搓排序状态机 + 零列宽 grid + 零排序表头
    # react(W5, 计划 26-10-13-0811 L5「更新是写字段, 不是重建」): 行来源含交互 UI 态的变体
    # (04 筛选 pills/07 chips/08 分区+在传/09 chips/10 选中+折叠+筛选/11 勾选+折叠+筛选)
    # 必须 Vue.reactive —— 桥 keyed 写补丁原行更新, 行 DOM 身份恒定(勾选不跳动/速度格原节点
    # 续用); 旧 anchTouch 强制换代 = 整表重挂(行抖动/焦点丢/大树卡死), 2026-10-13 已退役并
    # 钉死不得回潮。05/06 的 ui 态(折叠/msg 展开)只翻 class 不改行来源, 无需反应式。
    # data-sort: 04 分段钮是 dtSortSet 直设的选择器属性(引擎单点消费), 非手搓状态机 ——
    # 只对 U2 三行钉零残留。
    for fname, tid, segkey, vtab, need_react in (
        ("07-peers-dashboard-tall.js", "drawerPeerV07", "", "peers", True),
        ("08-peers-groups-low.js", "drawerPeerV08", "take", "peers", True),
        ("09-peers-density-collapsed.js", "drawerPeerV09", "", "peers", True),
        ("04-trackers-status-cards-tall.js", "drawerTrackerV04", "", "trackers", True),
        ("05-trackers-health-groups-low.js", "drawerTrackerV05", "err", "trackers", False),
        ("06-trackers-table-collapsed.js", "drawerTrackerV06", "", "trackers", False),
        ("10-content-tree-detail-tall.js", "drawerContentV10", "", "content", True),
        ("11-content-treegrid-batch-low.js", "drawerContentV11", "", "content", True),
    ):
        v = read("drawer_tpl", fname)
        # 声明形态两可: 字面(U2 三行)或模块常量 TABLE_ID(U3 三行 —— 文件内多处引用)
        assert re.search(rf'tableId: (TABLE_ID|"{tid}")', v), f"{fname} 未声明 tableId(桥契约的声明侧)"
        assert f'"{tid}"' in v, f"{fname} 缺 table-id 字面(锚保活/触碰的寻址侧)"
        assert "rowsFn: rowsFn" in v, f"{fname} 未声明 rowsFn(桥变体必须自带行装配, U2)"
        assert "H.anchFill(host," in v and f'"{tid}"' in v, f"{fname} 缺锚保活(锚被重建 = Teleport 重挂 = 行抖动)"
        if need_react:
            assert "Vue.reactive(" in v, \
                f"{fname} 缺反应式 ui 态(W5/L5: 行来源读数必须 Vue 可跟踪, 交互更新走 keyed 写补丁)"
            assert "H.anchTouch(" not in v, \
                f"{fname} 残留 anchTouch(W5 已退役: 反应式 ui 下换代重挂 = 勾选跳动/行抖动回潮)"
        assert "ui.sortKey" not in v and "ui.sort" not in v, \
            f"{fname} 残留手搓排序状态机(U3/Q3: 排序并引擎, D3)"
        if vtab == "peers":
            assert "data-sort" not in v, f"{fname} 残留手搓排序属性(U3/Q3: 排序并引擎, D3)"
        # Q4 判据本体 = 表格容器上零列宽 grid(列宽归引擎 aq-table 的 grid 契约);
        # 卡片/图例等版式 grid 是 D5 保留面(07 四卡仪表条/图例, 04 的 .group-table 双列卡片栅格
        # —— 卡片布局不是列宽, 由 test_drawer_tpl_trackers_card_uniform_height 另行钉住)。
        nn = tid[-2:]
        for ln in v.splitlines():
            if "grid-template-columns" in ln and (
                ".group-head" in ln or ".group-row" in ln or re.search(r"\.dt%s-(?:h|r|head|row|gcols)\b" % nn, ln)
            ):
                raise AssertionError(f"{fname} 表格容器残留列宽 grid 硬编码(Q4: 列宽归引擎): {ln.strip()[:80]}")
        assert "dt07-sortable" not in v and "dt08-sortable" not in v and "dt09-sortable" not in v, \
            f"{fname} 残留手搓排序表头(表头归引擎 aq-table)"
        if segkey:
            # 分段桥锚槽是动态寻址(data-dt-anchor-slot="${g.key}"), 逐组 teleport :to 追 [data-dt-seg=key];
            # segkey 钉在分组键表声明侧(键名漂移即桥段寻址失配) —— 两可形态: 组表字面(08)或
            # 核心桶序派生(05, issue 26-10-29-1343 后键集单源在核心 TRACKER_BUCKET_ORDER,
            # 逐键由 test_drawer_tracker_bucket_text_single_point 钉住)。
            assert 'data-dt-anchor-slot="${g.key}"' in v, f"{fname} 缺分组锚槽动态寻址(分段桥的段寻址侧)"
            if f'{{ key: "{segkey}"' not in v:
                assert "TRACKER_BUCKET_ORDER" in v, \
                    f"{fname} 缺分组键 {segkey}(分段桥段寻址的声明侧: 组表字面或核心桶序派生)"
        else:
            assert 'data-dt-anchor-slot=""' in v, f"{fname} 缺单锚槽"
    # 04 排序并引擎的正向钉: 分段钮经 dtSortSet 直设 dyn 键(引擎单点), active 态读 dtSortCell
    v04 = read("drawer_tpl", "04-trackers-status-cards-tall.js")
    assert "dtSortSet(TABLE_ID" in v04 and "dtSortCell(TABLE_ID)" in v04, \
        "04 分段钮排序未并引擎(须 dtSortSet 直设 + active 态读 dtSortCell, 手搓排序态退役)"

    # ⑫ 各皮肤 index.html: stub 装载行各 1 条
    for skin in ("atlas", "console", "prism", "flux"):
        idx = open(os.path.join(os.path.dirname(shared), skin, "index.html"), encoding="utf-8").read()
        assert idx.count("drawer_tpl/90-peers-stub-bridge.js") == 1, f"{skin} index.html stub 装载行失守"


def test_drawer_tpl_table_face_bg_single_point():
    """W6 表格面背景/密度族单点守阵(计划 26-10-13-0811 W6, 症状1)。

    症状1 根因: 06/07/09/11 各自手写表头底 background:var(--bg-card), 行板又各算
    (skin 卡底 --bg-row / 透明), frost 下表头 rgb(253,254,255) vs 页面底
    rgb(242,246,251) 一块可见色带。修复: 背景族收口 shared/dt_table.css
    (表头/行板默认 --bg, 与主列表吸顶列头「页面面板」语义同源), 变体只声明
    密度令牌(--tbl-head-minh/--tbl-row-minh)与吸顶个性。
    判据: ① 四变体的表头声明零 --bg-card 回潮; ② 密度令牌声明在位;
    ③ 共享层文件存在且含族选择器/令牌; ④ 三皮肤 index.html 各挂载一次。
    """
    import os
    shared = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src", "auto_qb", "webui", "static", "shared"
    )

    def read(*parts):
        return open(os.path.join(shared, *parts), encoding="utf-8").read()

    faces = {
        "06-trackers-table-collapsed.js": {
            "head_minh": True,
            "row_minh": True
        },
        "07-peers-dashboard-tall.js": {
            "head_minh": False,
            "row_minh": True
        },
        "09-peers-density-collapsed.js": {
            "head_minh": False,
            "row_minh": True
        },
        "11-content-treegrid-batch-low.js": {
            "head_minh": True,
            "row_minh": True
        },
    }
    for fname, need in faces.items():
        v = read("drawer_tpl", fname)
        for ln in v.splitlines():
            if ".group-head" in ln and "--bg-card" in ln:
                raise AssertionError(
                    f"{fname} 表头声明残留 --bg-card(W6 症状1: 底色归 shared/dt_table.css --bg 族): {ln.strip()[:80]}"
                )
        if need["row_minh"]:
            assert "--tbl-row-minh:" in v, f"{fname} 缺行密度令牌 --tbl-row-minh(W6: 行高声明侧在变体)"
        if need["head_minh"]:
            assert "--tbl-head-minh:" in v, f"{fname} 缺列头密度令牌 --tbl-head-minh(W6)"

    dt_css = os.path.join(shared, "dt_table.css")
    assert os.path.isfile(dt_css), "缺 shared/dt_table.css(W6 背景/密度族单点)"
    css = open(dt_css, encoding="utf-8").read()
    for sel in (".dt06-list", ".dt07-list", ".dt09-list", ".dt11-list"):
        assert f".drawer-body {sel} .group-head" in css and f".drawer-body {sel} .group-row" in css, \
            f"dt_table.css 缺族选择器 {sel}(四面背景族必须同点声明)"
    for token in ("--tbl-head-bg", "--tbl-face-bg", "--tbl-head-minh", "--tbl-row-minh"):
        assert token in css, f"dt_table.css 缺令牌 {token}"

    for skin in ("atlas", "console", "prism", "flux"):
        idx = open(os.path.join(os.path.dirname(shared), skin, "index.html"), encoding="utf-8").read()
        assert idx.count('/shared/dt_table.css') == 1, f"{skin} index.html dt_table.css 挂载失守(须恰一次)"


def test_frontend_pinned_first_cell_bg_per_face():
    """必现列(吸左首格)底色按面重锚守阵(2026-10-14 修「必现列背景与其他列不一致」)

    用户报障面: 主表(种子/辅种/追剧) + 种子详情面板全部变体表格。两层根因:
    ① 皮肤 views.css 的 `.group-row > :first-child { background: var(--bg-row) }` 是
       **主列表**行语言(不透明卡底 + stretch), 抽屉各引擎面复用 .group-row(外壳/桥零
       特判, D5 口径) ⇒ 首格规则漏进抽屉, 与各面行板语言(族面 --tbl-face-bg→--bg /
       04 卡 --bg-card / 05·10 透明 / 08 --bg-row)三样各算, 行内画出一条异色竖带
       (实测 prism/frost: 行板 rgb(242,246,251) vs 首格 rgb(247,250,253); ocean 主题
       --bg #0d1724 vs --bg-row #112034, Δ 达 16/255, 用户默认暗色主题下肉眼可辨);
    ② 追剧表搜索命中行: 行底是「accent 渐层 over --bg-row」(components.css
       .group-row.search-hit), 首格只有平铺 --bg-row —— 整条渐层丢失(实测首格
       backgroundImage=none, 左缘渐层最强处 Δ≈18/14/9)。
    修复: shared/dt_table.css 按面重锚(族面同 Token + err/bad/is-chk/sel 半透明 tint
    一律合成在**不透明 --bg-card** 上 / 04·05 摘底摘吸左 / 10 取 --bg-card / 08 补 bad
    合成 / 族表头同 --tbl-head-bg / empty-row 随行透明), 三皮肤 views.css 补
    search-hit 首格镜像; 另修 05 变体接线 —— 补内层行容器 dt05-list(家族两层
    dtNN-wrap + dtNN-list; 修前只有单层 dt05-wrap, 与 CSS 前缀不匹配致六条
    .group-row 规则全程空转、行带主表卡底)。
    真浏览器量具: e2e/dt-table-face-bg.spec.mjs(首格计算底 == 行板计算底)。
    """
    import os
    import re
    shared = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src", "auto_qb", "webui", "static", "shared"
    )

    # ① 三皮肤 search-hit 首格镜像: 行是「90deg accent 渐层 over --bg-row」, 首格必须
    #    同款合成(渐变停靠点同行 46%) —— 只平铺 --bg-row 即丢整条渐层。
    for ui in _UI_ALL:
        css = open(os.path.join(STATIC_ROOT, ui, "css", "views.css"), encoding="utf-8").read()
        ms = re.search(r"\.group-row\.search-hit > :first-child \{([^}]*)\}", css)
        assert ms, (
            f"{ui} views.css 缺 .group-row.search-hit > :first-child 镜像规则"
            "(2026-10-14 修「必现列背景与其他列不一致」: 首格只拿平铺 --bg-row 会丢整条 accent 渐层)"
        )
        body = ms.group(1)
        assert "linear-gradient(90deg, var(--accent-soft), transparent 46%)" in body, (
            f"{ui} search-hit 首格镜像缺同款 90deg 渐层(停靠点须同行 46%)"
        )
        assert "var(--bg-row)" in body, f"{ui} search-hit 首格镜像缺 --bg-row 基色(渐层 over 卡底)"

    # ② dt_table.css 按面重锚(剥注释后按规则块取 body, 注释里的示例代码含花括号)
    dt_css = os.path.join(shared, "dt_table.css")
    assert os.path.isfile(dt_css), "缺 shared/dt_table.css(必现列按面重锚单点)"
    css = re.sub(r"/\*[\s\S]*?\*/", "", open(dt_css, encoding="utf-8").read())

    def body_of(sel):
        for mo in re.finditer(r"([^{}]+)\{([^{}]*)\}", css):
            if sel in [s.strip() for s in mo.group(1).split(",")]:
                return mo.group(2)
        return None

    def need(sel, *fragments, forbid=()):
        body = body_of(sel)
        assert body is not None, f"dt_table.css 缺必现列重锚规则 {sel}(按面重锚单点被删/改名?)"
        for frag in fragments:
            assert frag in body, f"{sel} 缺成分 {frag}(现 body: {body.strip()[:100]})"
        for frag in forbid:
            assert frag not in body, (
                f"{sel} 不得含 {frag}(合成基色按面确定: 族面/10 = 抽屉卡底 --bg-card, 08 = 分组段底 "
                "--bg-row; 半透明 tint 不得裸用)"
            )

    # 族面 06/07/09/11: 行板首格与行板同 Token; 表头首格与表头同 Token
    for face in ("06", "07", "09", "11"):
        need(f".drawer-body .dt{face}-list .group-head > .h-cell:first-child", "var(--tbl-head-bg")
        need(f".drawer-body .dt{face}-list .group-row > :first-child", "var(--tbl-face-bg")
        need(f".drawer-body .dt{face}-list .group-row:hover > :first-child", "var(--bg-hover)")
    # 06 err 行: 半透明 error-soft 合成在**抽屉卡底 --bg-card** 上(不是主表 --bg-row)
    need(
        ".drawer-body .dt06-list .group-row.err > :first-child",
        "linear-gradient(var(--error-soft), var(--error-soft))",
        "var(--bg-card)",
        forbid=("var(--bg-row)", ),
    )
    need(
        ".drawer-body .dt06-list .group-row.err:hover > :first-child", "var(--error-soft)"
    )  # 变体 err:hover 保 error-soft
    # 07/09 bad 行: 同款合成(bad+hover 行底是 --bg-hover, 由悬停规则覆盖, 不另写)
    for face in ("07", "09"):
        need(
            f".drawer-body .dt{face}-list .group-row.bad > :first-child",
            "linear-gradient(var(--error-soft), var(--error-soft))",
            "var(--bg-card)",
            forbid=("var(--bg-row)", ),
        )
    # 11 is-chk 行: sel-bg 合成; 空行随行透明
    need(
        ".drawer-body .dt11-list .group-row.is-chk > :first-child",
        "linear-gradient(var(--sel-bg), var(--sel-bg))",
        "var(--bg-card)",
    )
    need(".drawer-body .dt11-list .group-row.is-chk:hover > :first-child", "var(--sel-bg)")
    need(".drawer-body .dt11-list .group-row.empty-row > :first-child", "transparent")
    # 08 bad 行: 行板本就是引擎 --bg-row(基础态首格同语言无需重锚), bad 才合成。
    # ⚠ 2026-10-20 修正基色: 08 的 tint **叠在分组段底 `.dt08-grp`(--bg-row) 上**, 不是
    #   抽屉卡底 —— 实测 section.dt08-grp 计算底 rgb(247,250,253)(= --bg-row), 旧写法取
    #   --bg-card 时首格与相邻列实际差 5.3(prism)/3.4(atlas)。真浏览器量具见 e2e
    #   dt-table-face-bg 的 STATE_CASES['08'](补测位, 修前红/修后绿)。
    need(
        ".drawer-body .dt08-rows .group-row.bad > :first-child",
        "linear-gradient(var(--error-soft), var(--error-soft))",
        "var(--bg-row)",
        forbid=("var(--bg-card)", ),
    )
    # 04 卡片 / 05 健康分组: 首格是内容根(卡头/rowin), 摘底摘吸左
    for face in ("04", "05"):
        need(f".drawer-body .dt{face}-list .group-row > :first-child", "transparent", "position: static")
    need(".drawer-body .dt05-list .group-row.failrow > :first-child", "var(--error-soft)")
    # 10 内容树: 保留吸左, 首格取承光底 --bg-card; sel 行合成
    need(".drawer-body .dt10-list .group-row > :first-child", "var(--bg-card)", forbid=("var(--bg-row)", ))
    need(".drawer-body .dt10-list .group-row:hover > :first-child", "var(--bg-hover)")
    need(
        ".drawer-body .dt10-list .group-row.sel > :first-child", "linear-gradient(var(--sel-bg), var(--sel-bg))",
        "var(--bg-card)"
    )

    # ③ 05 变体接线: 外壳两层结构 dt05-wrap(外壳) + dt05-list(行容器) —— 六条 .group-row
    #    版式规则以 .dt05-list 为前缀, 行必须活在它里面(U3 引擎化时只有单层 dt05-wrap,
    #    前缀全程不匹配致规则空转、行带主表卡底); 判检剥块注释后判(注释里允许留旧类名沿革)。
    v05 = open(os.path.join(shared, "drawer_tpl", "05-trackers-health-groups-low.js"), encoding="utf-8").read()
    v05_code = re.sub(r"/\*[\s\S]*?\*/", "", v05)
    assert 'class="dt05-wrap"' in v05_code, (
        "05 变体外壳缺 dt05-wrap(家族约定 = dtNN-wrap 外壳 + dtNN-list 行容器两层;"
        "e2e 通用助手 openTrackersVariant 按 .dtNN-wrap 等外壳)"
    )
    assert '<div class="dt05-wrap"><div class="dt05-list">' in v05_code, (
        "05 变体未按家族两层结构渲染(<div class=\"dt05-wrap\"><div class=\"dt05-list\"> 相邻) —— "
        "行容器必须是内层 dt05-list, 六条 .group-row 版式规则以 .dt05-list 为作用域前缀"
    )
    assert ".drawer .dt05-list .group-row" in v05_code, "05 变体 CSS 前缀未与行容器类名对齐(.drawer .dt05-list .group-row)"


def test_frontend_hr_detail_table_wiring():
    """HR 表① 全量详情表前端接线守阵(2026-10-01, 计划 26-10-01-2216 阶段2; 26-10-02-1936 阶段3 扩)

    表① 是设置分区「站点状态」块里逐站点的种子明细表(数据 /api/hr/sites/<site>/entries,
    阶段1 交付), 四类"漏一处 = 静默失效 / 拍板被推翻"的故障形态机械钉住:
    1. 模板绑定: 档位 chips(本地过滤不回后端)/ 已删除种子切换钮(阶段3)/ 明细行 / 空态 / 失踪行挂钩 /
      「数据截至」时间戳(拍板⑥)+ 三列重组列名「核实结论」「在列」(阶段3 拍板④, 口径钉在列名)——
      缺一处该功能消失;
    2. 拍板守卫: remain_seconds 不得进表(拍板③, 2026-09-25 误读教训)/ 不挂 hr-pop 不做行内跳转
      (拍板⑤)/ 单元格无原生 title(hr-tooltip-overlap: 与悬停弹窗叠出遮挡)/ 表① 段无 <details>
      (排障视图在 aqb:hr-diag 独立段, 阶段3 交付)/ 来源徽章类名是 hr-vsrc —— .hr-src 是列表页已退役
      的文字 chip 族(守阵钉了 class="hr-src" 零残留, 复用即撞红);
    3. JS 接线: hr_status.js 有按站点明细加载(loadHrSiteEntries)与本地筛选(hrsLaneSelOf),
      且无 setInterval(计划 §5.5 刷新纪律: 打开拉一次 + 手动刷新, 不轮询、不进 /api/state);
    4. CSS 三处成对(计划 §5.6): .hr-detail-table 在 atlas / console / prism 的 CSS 聚合各 ≥1,
      档位色义四档(A=warn / B=green / C=error / D=blue)与失踪行 --paused 弱化规则成对;
      prism 拆两文件 —— 表头过滤栏段在 components.css、表格徽章段在 views.css(漏一件即该套静默失效)。
    """
    shared = os.path.join(STATIC_ROOT, "shared")
    tpl = open(os.path.join(shared, "tpl", "settings-detail.html"), encoding="utf-8").read()
    m = re.search(r"<!-- aqb:hr-detail-table:begin.*?-->(.*?)<!-- aqb:hr-detail-table:end.*?-->", tpl, re.S)
    assert m, "settings-detail.html 缺 aqb:hr-detail-table 扫描锚 —— 表① 模板被移走或锚被删? 同步本守阵"
    frag = m.group(1)

    # 1. 模板绑定: chips / 已删除种子切换钮 / 明细行 / 空态 / 失踪行 / 时间戳 / 拍板④重组列名
    for needle, what in (
        ("hrsLaneChips()", "档位筛选 chips"),
        ("hrsSetLaneSel(", "chips 点击切换"),
        ("hrsToggleOld(", "已删除种子切换钮点击(阶段3)"),
        ("hrsOldBtnText(", "已删除种子切换钮文案计数(阶段3)"),
        ('v-for="e in hrsDetailRows', "明细行渲染"),
        ('class="drawer-table hr-detail-table"', "表格骨架(同挂 .drawer-table 一类)"),
        ("hrsEmptyText(s.site)", "空态文案单点(阶段3: 区分本地无 HR/档位暂无/已删除视图空)"),
        ("数据截至", "「数据截至」时间戳(拍板⑥)"),
        (':class="{ missing: !e.active }"', "失踪行弱化挂钩"),
    ):
        assert needle in frag, f"表① 模板缺 {what}(应有 `{needle}`)"

    # 2. 拍板 / 悬浮纪律守卫
    assert "remain_seconds" not in frag, "remain_seconds 不得进表①(拍板③: 考核窗口倒计时, 2026-09-25 误读教训)"
    assert "hrPopEnter" not in frag, "表① 不得挂 hr-pop 悬停(拍板⑤: 第一期纯清单)"
    assert "title=" not in frag, "表① 单元格不得挂原生 title(hr-tooltip-overlap: 与悬停弹窗叠出遮挡)"
    assert "<details" not in frag.lower(), "表① 段不得混入 <details>(排障视图在 aqb:hr-diag 独立段, 阶段3 已交付)"
    assert 'class="hr-src"' not in frag, "来源徽章类名必须是 hr-vsrc —— hr-src 是列表页已退役 chip 族(复活即撞守阵)"

    # 3. JS 接线: 按站点按需加载 + 本地筛选 + 不轮询
    hr_status_js = open(os.path.join(shared, "hr_status.js"), encoding="utf-8").read()
    for needle, what in (
        ("loadHrSiteEntries", "明细加载函数"),
        ("/api/hr/sites/${encodeURIComponent(site)}/entries", "明细端点拼接"),
        ("hrsLaneSelOf", "档位筛选读取"),
        ("hrsDetailRows", "本地过筛行集(不回后端)"),
        ("该站点本地没有 HR 种子", "空站点空态文案(阶段3: 做种中视图全空)"),
        ("该档位暂无", "档位过滤空态文案(阶段3)"),
        ('label: "核实结论"', "拍板④ 重组列名(口径钉在列名)"),
        ('label: "在列"', "拍板④ 重组列名(口径钉在列名)"),
    ):
        assert needle in hr_status_js, f"hr_status.js 缺 {what}({needle})"
    assert "setInterval" not in hr_status_js, "hr_status.js 不得有轮询定时器(计划 §5.5: 打开拉一次 + 手动刷新)"

    # 4. CSS 三处成对 + 档位色义 + 失踪行弱化
    # 判据落在**最终生效面**(皮肤聚合 + shared 共用层, link 序): issue 26-10-20-2231 把表头过滤栏 /
    # 档位色义 / 失踪行弱化 / 排序头收进 shared/console_hub.css(三皮肤逐条同 ⇒ 单点一份),
    # 徽章**底形族**(.hr-vsrc/.hr-pres/.hr-sub)因三皮肤描边与副行字体取值不同仍留在各皮肤内。
    # 故这里同时钉两件事: ①收敛族在共用层有且生效; ②底形族在每套皮肤自己的文件里(真差异不许
    # 被共用层顺手抹平)。原先「prism 拆 components.css + views.css 两件」的钉法随收敛失效 ——
    # 那两段已不在 prism 文件里, 改成钉共用层持有它们。
    shared_css = read_shared("console_hub.css")
    assert ".hr-detail-table-bar" in shared_css, "shared/console_hub.css 缺表头过滤栏段(chips + 数据截至)"
    assert ".hr-detail-table .hr-lane-a" in shared_css, "shared/console_hub.css 缺表格徽章色义段"
    for css, name in (
        (_ui_css_effective("atlas"), "atlas 生效样式面(聚合 + shared)"),
        (_ui_css_effective("console"), "console 生效样式面(聚合 + shared)"),
        (_ui_css_effective("prism"), "prism 生效样式面(聚合 + shared)"),
        (_ui_css_effective("flux"), "flux 生效样式面(聚合 + shared)"),
    ):
        assert ".hr-detail-table" in css, f"{name} 缺 .hr-detail-table 段 —— 各套 UI 必须成对改(计划 §5.6)"
        for lane in ("a", "b", "c", "d"):
            assert f".hr-detail-table .hr-lane-{lane}" in css, f"{name} 缺 .hr-lane-{lane} 档位色义(计划 §5.4)"
        assert ".hr-detail-table tr.missing .hr-lane" in css, f"{name} 缺失踪行 --paused 描边弱化规则"
        assert ".hr-vsrc" in css, f"{name} 缺来源小徽章(.hr-vsrc)样式"
    for ui in ("atlas", "console", "prism", "flux"):
        own = _ui_css_aggregate(ui)
        for rule, what in (
            # 带 `{` 边界: 不带的话 `.hr-detail-table .hr-pres` 会被 `.hr-pres.hr-pres-on`
            # 那条修饰规则**子串命中**, 底形本体删了也照样绿(2026-10-21 红验实测)
            (".hr-detail-table .hr-vsrc {", "来源徽章底形"),
            (".hr-detail-table .hr-pres {", "在列/退役徽章底形"),
            (".hr-detail-table .hr-sub {", "副行小字"),
        ):
            assert rule in own, f"{ui} 自己的 CSS 缺 {rule}({what}) —— 底形族是三皮肤真差异, 不许并进共用层"


def test_frontend_hr_table_sort_filter_reorg_wiring():
    """HR 表① 未做种过滤 + 三态排序 + 三列重组守阵(2026-10-02, 计划 26-10-02-1936 阶段3)

    三块新交互"漏一处 = 静默失效 / 拍板被推翻"的故障形态机械钉住:
    1. 已删除种子切换钮(§3.3 决策点③a): 默认文案「显示已删除种子 (N)」、oldOn 默认关(只看本地仍在列 =
      local_present true), 切换后「只看本地仍在列 (M)」; 计数在站点全行集现算;
    2. 三态排序(§3.4, 对齐 shared/sort.js): 表头十列全 sortable 而表② 波次表不接排序;
      P5(计划 26-10-11-1722)起表头 **markup** 收敛到表壳组件 thead 模式(<tr is="vue:aq-table"
      mode="thead">, 与主视图同一份表壳), 列定义单点在 HR_TABLE_DEFS.hrDetail —— 本守阵改为钉
      表① 自己的接线(占位 + :cols/:sort-key 绑定 + @sort="hrsSetSort(s.site, $event)")与注册表
      十列键(26-10-29-1348 修复: 注册表十列全标 sortable: true, thead sortable 类/箭头门控同源 col.sortable), markup 面由 test_frontend_table_shell_single_point 钉; 状态机 = 首点降 → 再点升 →
      第三击恢复后端默认序, 换列直接降序; 比较器纯函数 hrsCompareRows 用 node 真跑语义电池
      (空值恒末位两方向不反转 / 0 哨兵 / 档位 A<B<C<D 固定秩 / 字符串·数值分型 / 同值稳定),
      无 node 的机器静默跳过本项(不引入 pytest skip, 基线 0 skipped);
    3. 三列重组(§3.6 决策点④): 模板新列结构(核实结论徽章 hr-vsrc + 副行 / 在列·失踪徽章
      hr-pres + 副行)+ CSS 三处成对(th.sortable 箭头激活 accent·hover faint / .hr-sub 副行小字 /
      .hr-pres 徽章 / 名称列限宽钩子 + .hr-full-modal 放开); 旧列辅助 hrsVerifiedText /
      hrsStatusText 随列退役, 零残留。
    4. 几何归正(2026-10-06, 计划 26-10-06-1009 §7 · 报告 26-10-06-0945 B1): 表① 排序箭头改
      **绝对定位不占流**(原 display:inline-block 恒占 11px + 3px, 把右对齐 num 列表头文字整体左顶
      14px); 静态断言看不见盒子模型, 只钉「不再参与行内布局」这一必要条件, 几何量测见坑档。
    """
    shared = os.path.join(STATIC_ROOT, "shared")
    tpl = open(os.path.join(shared, "tpl", "settings-detail.html"), encoding="utf-8").read()
    js = open(os.path.join(shared, "hr_status.js"), encoding="utf-8").read()
    m = re.search(r"<!-- aqb:hr-detail-table:begin.*?-->(.*?)<!-- aqb:hr-detail-table:end.*?-->", tpl, re.S)
    assert m, "settings-detail.html 缺 aqb:hr-detail-table 扫描锚 —— 表① 模板被移走或锚被删? 同步本守阵"
    frag = m.group(1)

    # 1. 已删除种子切换钮: 默认态文案 + oldOn 默认关(只看本地仍在列)
    #    文案 2026-10-03 用户二次驳回: 默认过滤实为「本地已删除」而非「没在做种」, 反向态含暂停/异常
    assert "显示已删除种子 (" in js and "只看本地仍在列 (" in js, "切换钮双态文案缺失(计划 §3.3, 26-10-03 文案)"
    # 旧措辞只在测试说明里提; 前端源码零残留(含注释 —— 注释解释的是「为何不再用做种措辞」)
    assert "未做种" not in js and "只看做种中" not in js, "旧误导文案残留(26-10-03 二次驳回)"
    mo = re.search(r"hrsOldOnOf\(site\) \{\n(.*?)\n    \},", js, re.S)
    assert mo and "!!" in mo.group(1), "hrsOldOnOf 必须默认 falsy(默认只看本地仍在列, 计划 §3.3)"
    assert "hrsToggleOld(s.site)" in frag and "hrsOldBtnText(s.site)" in frag, "工具条缺已删除种子切换钮绑定"
    assert "e.local_present" in js, "行集过滤必须消费后端 local_present(决策点③a), 前端不得自算 join"

    # 2. 三态排序: 表头接线 + 列模型单点 + 状态机 + 纯函数
    #    表头 markup(class="sortable" + 排序箭头)自 P5(计划 26-10-11-1722)起收敛到表壳组件的
    #    thead 模式(shared/tpl/xtpl.html#tpl-aq-table), 由 test_frontend_table_shell_single_point 钉;
    #    这里钉表① 自己的**接线**(占位形态 + 列/键绑定 + 排序事件)与列模型注册表单点。
    assert 'is="vue:aq-table" mode="thead"' in frag, (
        "表① 表头未借表壳组件(thead 模式占位 <tr is=\"vue:aq-table\" mode=\"thead\">) —— 排序表头退回内联副本"
    )
    assert ':cols="hrsCols()"' in frag and ':sort-key="hrsSortKeyOf(s.site)"' in frag, "表① 表头列模型/排序键接线缺失"
    assert '@sort="hrsSetSort(s.site, $event)"' in frag, \
        "表① 表头排序事件未接 hrsSetSort(D3=B: 只借壳, 排序仍走 HR 自己的三态机)"
    xtpl = open(os.path.join(shared, "tpl", "xtpl.html"), encoding="utf-8").read()
    shell = xtpl[xtpl.index('id="tpl-aq-table"'):]
    shell = shell[:shell.index("</script>")]
    assert "#i-arrow-up" in shell and "#i-arrow-down" in shell, \
        "表壳 thead 模式缺 sprite 双箭头(P5: 表① 表头 markup 收敛到表壳, 与种子页同款图标)"
    thead_seg = shell.split("<tr v-if=\"mode === 'thead'\">", 1)[1].split("</tr>", 1)[0]
    assert ':class="{ sortable: col.sortable, num: col.num }"' in thead_seg \
        and '<span v-if="col.sortable" class="arrow"' in thead_seg, \
        "thead 可排序性判据必须同源 col.sortable(issue 26-10-29-1348: 曾硬编码 sortable/恒画箭头" \
        "而 headActivate 早退, HR 表列头点着没反应)"
    mreg = re.search(r"const HR_TABLE_DEFS = \{(.*?)\n\};", js, re.S)
    assert mreg, "hr_status.js 缺 HR 表注册表 HR_TABLE_DEFS(P5 表身份单点)"
    assert "return HR_TABLE_DEFS.hrDetail.columns" in js, "hrsCols() 未取 HR 表注册表(列定义单点断了)"
    mdet = re.search(r"\n  hrDetail: \{(.*?)\n  \},", mreg.group(1), re.S)
    assert mdet, "HR_TABLE_DEFS 缺 hrDetail 表(或段落格式变了, 同步本守阵)"
    keys = re.findall(r'key: "([a-z_]+)"', mdet.group(1))
    assert len(keys) == 10 and len(set(keys)) == 10, f"表① 必须 10 列可排, 实得 {len(keys)}: {keys}"
    assert set(keys) == {
        "lane", "name", "tid", "uploaded_bytes", "downloaded_bytes", "ratio", "need_seed_seconds", "done_iso",
        "verified_ts", "last_seen"
    }, "十列排序键漂移, 同步本守阵"
    # 判据同源(issue 26-10-29-1348): 十列全标 sortable: true, 且每个 key 在 HRS_SORT_VAL 都有
    # 访问器 —— 缺访问器的 key 标 sortable 后点该列, hrsCompareRows 取 undefined 访问器直接 TypeError
    macc = re.search(r"const HRS_SORT_VAL = \{(.*?)\n\};", js, re.S)
    assert macc, "hr_status.js 缺 HRS_SORT_VAL 访问器注册表(排序纯函数单点)"
    acc_keys = set(re.findall(r"\n  ([a-z_]+): \(e\) =>", macc.group(1)))
    assert not [k for k in keys if k not in acc_keys], \
        "列定义存在缺 HRS_SORT_VAL 访问器的 key —— 标 sortable 后点该列 hrsCompareRows 会 TypeError"
    srt = re.findall(r"sortable: true", mdet.group(1))
    assert len(srt) == 10, \
        f"表① 十列必须全部标 sortable: true(漏标 = thead 行为侧 headActivate 静默早退, issue 26-10-29-1348), 实得 {len(srt)}"
    mo = re.search(r"hrsSetSort\(site, key\) \{\n(.*?)\n    \},", js, re.S)
    assert mo, "hr_status.js 缺 hrsSetSort 三态状态机"
    body = mo.group(1)
    assert "!== key" in body and "sortDir[site] = -1" in body, "换列必须直接降序开始(sort.js 同款)"
    assert 'hrsSortDirOf(site) === -1' in body and "sortDir[site] = 1" in body, "第二击必须转升序"
    assert 'hrsSortKeyOf(site) = ""' in body or 'sortSel[site] = ""' in body, "第三击必须恢复后端默认序"
    for fn in ("HRS_LANE_RANK", "HRS_SORT_VAL", "hrsValEmpty", "hrsCompareRows"):
        assert re.search(rf"\b{fn}\b", js), f"hr_status.js 缺排序纯函数 {fn}(模块级单例, 供 node 单测)"
    # 排序必须作用在当前过滤后的行集上(hrsDetailRows 内, 而不是另一个未过滤的行集)
    mo = re.search(r"hrsDetailRows\(site\) \{\n(.*?)\n    \},", js, re.S)
    assert mo and "hrsCompareRows" in mo.group(1) and "local_present" in mo.group(1), \
        "hrsDetailRows 必须做 chips × 未做种 AND 过滤后再排序(计划 §3.4)"
    # 表② 波次表不接排序(行数 <=4)
    md = re.search(r"<!-- aqb:hr-diag:begin.*?-->(.*?)<!-- aqb:hr-diag:end.*?-->", tpl, re.S)
    assert md and "sortable" not in md.group(1), "表② 波次表不得接排序(计划 §3.4)"
    # 有 node 时真跑比较器语义电池(无 node 静默跳过, 不引入 skip)
    node = shutil.which("node")
    if node:
        proc = subprocess.run(
            [node, "-e", _NODE_HRS_SORT_PROBE, os.path.join(shared, "hr_status.js")],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace"
        )
        assert proc.returncode == 0, f"hrsCompareRows node 电池跑挂: {proc.stderr.strip()}"
        report = json.loads(proc.stdout.strip().splitlines()[-1])
        assert report["failed"] == [], f"排序语义电池 {report['ok']}/{report['total']} 过, 失败: {report['failed']}"

    # 3. 三列重组: 新列结构 + 旧辅助零残留 + CSS 三处成对
    for needle, what in (
        ('class="hr-vsrc"', "核实结论徽章(沿用 hr-vsrc 色义)"),
        ("hrsVerdictText(e)", "核实结论主层文案"),
        ("hrsVerdictSub(e)", "核实结论副行(来源人话 · 时刻)"),
        ('class="hr-pres"', "在列/退役徽章"),
        ("hrsPresenceText(e)", "在列主层文案"),
        ("hrsPresenceSub(e)", "在列副行(观察期 · 最近被见到)"),
        ('class="hr-sub"', "副行小字"),
    ):
        assert needle in frag, f"表① 三列重组缺 {what}(应有 `{needle}`)"
    # 4. 文案语义修正(2026-10-03 §8 B3/B4): 退役行不再借「失踪 N 波」, 终态在列行不再一律「未核实」
    #    (注: 「失踪行」是 CSS tr.missing 的既有叫法, 与徽章文案不是一回事 —— 只钉模板 literal)
    assert "失踪 ${" not in js, "退役行「失踪 N 波」文案残留(§8 B4: missing_streak 退役即清零, 显示恒 0 是语义错位)"
    assert "已移出" in js and "已退役" in js, "退役行主徽章三态缺失(§8 B4: 已移出 / 已退役)"
    assert "hrsTerminalLane" in js, "B3 终态档判据 helper 缺失(核实结论中间态)"
    assert "在列·" in js, "B3 中间态文案「在列·<档位人话>」缺失"
    mo = re.search(r"hrsVerdictText\(e\) \{\n(.*?)\n    \},", js, re.S)
    assert mo and "hrsTerminalLane" in mo.group(1), "hrsVerdictText 未消费终态档判据(B3 中间态)"
    mo = re.search(r"hrsPresenceText\(e\) \{\n(.*?)\n    \},", js, re.S)
    assert mo and "verified_source" in mo.group(1), "hrsPresenceText 退役行未按放行记录分流(B4)"
    assert "missing_streak" not in mo.group(1), "退役行主徽章不得再用 missing_streak(B4)"
    for dead in ("hrsVerifiedText", "hrsStatusText", "hrsArrowHref"):
        # 判定只认代码态(剥块/行注释 —— 历史注释里提旧名不算残留)
        # hrsArrowHref 自 P5 起退役: 箭头 href 由表壳组件 thead 模式按 sortKey/sortDir 现算
        js_code = re.sub(r"/\*.*?\*/", "", js, flags=re.S)
        js_code = re.sub(r"//[^\n]*", "", js_code)
        tpl_code = re.sub(r"<!--.*?-->", "", tpl, flags=re.S)
        assert dead not in js_code and dead not in tpl_code, f"{dead} 随旧列退役, 不得残留(死代码)"
    # 生效面(聚合 + shared): 排序头/箭头/限宽钩子已收敛进 shared/console_hub.css(各皮肤逐条同),
    # 徽章底形族仍各皮肤自带 —— 两处都在这张面上, 判据不变(各皮肤都得吃到; flux 收编 S5)。
    for css, name in (
        (_ui_css_effective("atlas"), "atlas 生效样式面(聚合 + shared)"),
        (_ui_css_effective("console"), "console 生效样式面(聚合 + shared)"),
        (_ui_css_effective("prism"), "prism 生效样式面(聚合 + shared)"),
        (_ui_css_effective("flux"), "flux 生效样式面(聚合 + shared)"),
    ):
        for rule, what in (
            (".hr-detail-table th.sortable", "排序表头"),
            (".hr-detail-table th .arrow", "排序箭头位"),
            (".hr-detail-table th.sortable .arrow.on", "激活列箭头 accent"),
            (".hr-detail-table th.sortable:hover .arrow", "非激活列 hover 浅色占位"),
            (".hr-detail-table .hr-sub", "副行小字(--fg-dim 等宽)"),
            (".hr-detail-table .hr-pres", "在列/退役徽章底形"),
            (".hr-detail-table .hr-pres.hr-pres-on", "在列徽章色义"),
            (".hr-detail-table .hr-pres.hr-pres-out", "已移出徽章 --blue 色义"),
            (".hr-detail-table td.wrap { max-width", "名称列限宽钩子(卡片上下文)"),
            (".hr-full-modal .hr-detail-table td.wrap { max-width: none", "全屏态名称列放开限宽"),
        ):
            assert rule in css, f"{name} 缺 {rule}({what}) —— 三套 UI 必须成对改(计划 §5.6)"

    # 5. 几何归正(2026-10-06, 计划 26-10-06-1009 §7 · 报告 26-10-06-0945 B1): 表① 排序箭头必须
    #    **绝对定位不占流** —— 原 display:inline-block 恒占 11px + margin-left 3px = 14px, 把右对齐
    #    (num)列的表头文字整体左顶(实测 14px, 三主题一致; 表头文字右缘 vs 值文字右缘)。静态断言
    #    看不见盒子模型, 这里只钉「不再参与行内布局」这一必要条件(几何量测见
    #    pitfalls/web-ui/header-cell-gutter.md: DOM 复现 14px -> 0px)。
    for css, name in (
        (_ui_css_effective("atlas"), "atlas 生效样式面(聚合 + shared)"),
        (_ui_css_effective("console"), "console 生效样式面(聚合 + shared)"),
        (_ui_css_effective("prism"), "prism 生效样式面(聚合 + shared)"),
        (_ui_css_effective("flux"), "flux 生效样式面(聚合 + shared)"),
    ):
        mo = re.search(r"\.hr-detail-table th \.arrow\s*\{([^}]*)\}", css)
        assert mo, f"{name} 缺 .hr-detail-table th .arrow 规则体(计划 26-10-06-1009 §7)"
        body = mo.group(1)
        assert "position: absolute" in body, (
            f"{name} 排序箭头未脱离行内布局(应为 position:absolute) —— 右对齐(num)列表头会被顶 14px(报告 26-10-06-0945 B1)"
        )
        assert "display: inline-block" not in body, (
            f"{name} 排序箭头仍在行内布局(display:inline-block 恒占 11px + 3px) —— 见 pitfalls/web-ui/header-cell-gutter.md"
        )


def test_frontend_frozen_column_boundary_wiring():
    """首列吸左边界提示守阵(2026-10-11 修「向右滚动时状态列被名称列盖住」)

    横滚时相邻列滑进吸左首格(issue 26-10-06-1717)下方, 未盖满的尾字("做种"的"种"等)会紧贴
    首格右缘露出; 无边界提示时残根读成与名称省略号粘连的坏字, 被误读成渲染 bug(用户报障)。
    钉两层接线, 缺任何一层 = 残根回归"裸露":
    1. JS: 横滚同步**单点** columns.js::syncHeadScroll(ev, page)(计划 26-10-11-1722 P4 把
       menu/selection/shows 三份收敛为一份)必须给滚动容器与吸顶表头打 .is-hscrolled
       (scrollLeft>0 打 / 回 0 摘) —— CSS 无法感知 scrollLeft, 丢标 = 边界落影永不出现;
       三个滚动容器(辅种/种子/追剧)必须各自带表 id 调用它;
    2. CSS: 三皮肤 views.css 的 .is-hscrolled 规则必须行吸左首格与表头吸左首格**成对**
       (漏表头 = 列名残根仍裸露), 且只含发丝线(边界)一个成分 —— 原第二条"右缘渐隐落影"
       (`16px 0 14px -10px rgba(0,0,0,.55)`)已于 2026-10-12 按用户报障整条删除(下条)。
    3. CSS: 三皮肤 `.group-row > :first-child` 必须 `align-self: stretch` —— 行是
       align-items: center, 网格项默认不拉伸, 吸左首格只有单行内容高; 站点/标签等多 chip 格
       换行把行撑高时(小窗常态), 滑入首格下方的 chip 从首格上下两段露出来(2026-10-11 用户
       复报「小窗时站点的徽标不会被名称列挡住」)。真浏览器红验: 关掉 stretch 后名称格 22px
       vs 站点格 71px, chip 成排透出; stretch 后全盖。
    4. CSS(2026-10-12): 三皮肤 `.is-hscrolled` 规则**不得**再带右缘落影 —— 用户报
       「WEBUI 名称列后随机出现阴影」。根因不是接线错, 是落影的可见度随**首格高度**变:
       box-shadow 的 spread -10 先从首格四周内缩 10px 再模糊 14px, 常态行首格仅 22px 高
       ⇒ 落影矩形塌成 2px、只剩模糊尾巴(近不可见); 站点/标签多 chip 格换行把行撑高
       (首格 46px+)时才显形 ⇒ 同一个"横滚"状态逐行深浅差 7 倍(桩服务截图实测 Δ 2.0 vs 13.7),
       读成"随机出现的黑块"。发丝线无此问题(inset 阴影铺满首格, 与高度无关), 故保留。
       本守阵把"删掉落影"钉成声明式契约(回潮即红)。
    """
    shared = os.path.join(STATIC_ROOT, "shared")
    # 1. JS: 横滚同步单点 —— 计划 26-10-11-1722 P4 起 menu/selection/shows 三份收敛为
    #    columns.js 的 syncHeadScroll(ev, page) 一份; 三个滚动容器各带自己的表 id 调它。
    cols_js = read_shared("columns.js")
    anchor = "syncHeadScroll(ev, page) {"
    assert anchor in cols_js, ("columns.js 缺横滚同步单点 syncHeadScroll(ev, page)(P4 收敛后被删/改名? 同步本守阵)")
    seg = cols_js[cols_js.index(anchor):]
    seg = seg[:seg.index("\n    },")]
    assert 'ev.target.classList.toggle("is-hscrolled", x > 0)' in seg, (
        "columns.js syncHeadScroll 缺滚动容器 is-hscrolled 打标 "
        "(CSS 无法感知 scrollLeft, 丢标 = 吸左边界落影永不出现)"
    )
    assert 'head.classList.toggle("is-hscrolled", x > 0)' in seg, (
        "columns.js syncHeadScroll 缺表头 is-hscrolled 打标(表头吸左首格残根裸露)"
    )
    for tpl, page in (("tpl/groups.html", "group"), ("tpl/torrents.html", "torrent"), ("tpl/shows.html", "show")):
        text = open(os.path.join(shared, tpl), encoding="utf-8").read()
        assert f'@scroll="syncHeadScroll($event, \'{page}\')"' in text, (
            f"shared/{tpl} 的滚动容器未接横滚同步单点 syncHeadScroll($event, '{page}')"
            "(P4 收敛后漏改 / 回退到已删的 sync*HeadScroll?)"
        )
    for ui in _UI_ALL:
        css = open(os.path.join(STATIC_ROOT, ui, "css", "views.css"), encoding="utf-8").read()
        mo = re.search(
            r"\.group-table\.is-hscrolled \.group-row > :first-child,\s*"
            r"\.group-head\.is-hscrolled > \.h-cell:first-child \{([^}]*)\}",
            css,
        )
        assert mo, (f"{ui} views.css 缺 .is-hscrolled 吸左边界落影规则"
                    "(行吸左首格与表头吸左首格必须成对声明, 漏表头 = 列名残根仍裸露)")
        body = mo.group(1)
        assert "inset -1px 0 0" in body, f"{ui} 边界提示缺发丝线(inset -1px 0 0)成分 —— 残根无边界可依"
        assert "rgba(0, 0, 0" not in body, (
            f"{ui} 边界提示又带上了右缘落影(2026-10-12 用户报「名称列后随机出现阴影」已删) —— "
            "落影可见度随首格高度变(常态行首格 22px 时塌成 2px 近不可见、高行才显形), "
            "逐行深浅差 7 倍读成随机黑块; 要重新引入须先有「跨行一致」的画法"
        )
        ms = re.search(r"\.group-row > :first-child \{([^}]*)\}", css)
        assert ms, f"{ui} views.css 缺 .group-row > :first-child 吸左首格规则"
        assert "align-self: stretch" in ms.group(1), (
            f"{ui} 吸左首格缺 align-self: stretch —— 行是 align-items:center, 首格只有单行内容高, "
            "多 chip 格换行撑高行后徽标从首格上下两段漏出(小窗常态, 2026-10-11 用户复报)"
        )


def test_frontend_hscroll_indicator_wiring():
    """主表横滚指示条守阵(计划 26-11-01-0553 S4)

    主表 .group-table 横向滚动时原生横条被隐藏, 改由底部一条 3px 胶囊指示当前位置。藏条是
    视觉决定, 但**纯鼠标用户没有触控板的横滚入口** —— 原生条是他们唯一"还能往右"的提示,
    藏了不补指示条 = 横滚能力被藏起来。本守阵钉三族静默故障(全部零报错, pytest 会假绿):
    1. **两条隐藏声明缺一即红**: 只写 ::-webkit-scrollbar 时 Firefox 仍画 10px 条槽(三皮肤
       全局都有 `* { scrollbar-width: thin }`), 只写 scrollbar-width 时 Chromium 系仍画条槽
       (元素级 display:none 才不绘制, 全局 `*` 规则挡不住);
    2. **挂载与级联序**: 三皮肤各恰挂一次、且排在本皮肤 views.css **之后**(link 序即级联序,
       排前面会被页面级规则反压); 三皮肤 /shared/*.css 链接集还必须**逐字相同** —— 共享层
       挂载漂移 = 某皮肤缺规则, 而规则本身只有一份, 缺了就是整条静默失效(没有第二处兜底);
    3. **单点与 DOM 契约**: 皮肤自有 CSS 里不得出现第二份隐藏声明(副本 = 日后各自漂移);
       CSS 的四个类名选择器与 columns.js 的建 DOM / classList 操作必须同侧(改了类名只改一侧
       = 胶囊恒不可见); syncHeadScroll 尾部仍调 _hscrollSync(删了 = 胶囊永不出现)且主表白名单
       三 id 齐全(删了 = 抽屉变体面 shared/tpl/xtpl.html:360 每次横滚都在 body 里留下一个
       永不用的胶囊); _hscrollBind() 的调用点必须在 _ensureHeadObserver 体内(ef734485 修的
       缺陷: 监听若退回挂在 _hscrollPill() 里, 从没横滚过的用户永远见不到胶囊 —— 而"纯鼠标
       用户没有拖拽入口"正是本方案要补的那个洞)。
    """
    shared = os.path.join(STATIC_ROOT, "shared")
    hcss_path = os.path.join(shared, "hscroll.css")
    assert os.path.isfile(hcss_path), (
        "缺 shared/hscroll.css(主表横滚: 原生横条隐藏 + 底部指示条外观的三皮肤单点) —— "
        "三份 index.html 仍挂着 link 时 = 404, 原生横条重新画出来且胶囊完全没有外观"
    )
    hcss = open(hcss_path, encoding="utf-8").read()
    # 判据 2: 两条隐藏声明缺一即红
    for needle, why in (
        ("scrollbar-width: none", "Firefox 仍画 10px 条槽(三皮肤全局 * { scrollbar-width: thin })"),
        ("::-webkit-scrollbar", "Chromium/WebKit 侧的元素级规则整条不在"),
        ("display: none", "Chromium/WebKit 仍画条槽(元素级 display:none 才不绘制)"),
    ):
        assert needle in hcss, f"shared/hscroll.css 缺 `{needle}` —— {why}"

    shared_sets = {}
    for ui in _UI_ALL:
        shell = open(os.path.join(STATIC_ROOT, ui, "index.html"), encoding="utf-8").read()
        # 判据 3: 各恰挂一次
        assert shell.count("/shared/hscroll.css") == 1, (
            f"{ui} index.html 的 /shared/hscroll.css 挂载失守(须恰一次, 实测 {shell.count('/shared/hscroll.css')}) "
            "—— 漏挂 = 该皮肤横条重现且胶囊无外观; 挂两次 = 规则重复进级联"
        )
        # 判据 4: 级联序 —— 必须在本皮肤 views.css 之后
        pos_views = shell.find(f'href="/{ui}/css/views.css"')
        pos_shared = shell.find('href="/shared/hscroll.css"')
        assert pos_views > 0, f"{ui} index.html 找不到 /{ui}/css/views.css 的 link(级联序判据失去锚点)"
        assert pos_shared > pos_views, (
            f"{ui} index.html 里 /shared/hscroll.css 排在 /{ui}/css/views.css 之前 —— "
            "link 序即级联序, 共享层的隐藏声明会被皮肤页面级规则反压(原生横条又露出来)"
        )
        # 判据 5: 皮肤自有 CSS 不得有第二份隐藏声明(副本 = 日后各自漂移)
        own = _ui_css_aggregate(ui)
        assert ".group-table::-webkit-scrollbar" not in own, (
            f"{ui} 皮肤自有 CSS 里又出现 .group-table::-webkit-scrollbar —— 隐藏规则单点在 "
            "shared/hscroll.css, 第二份副本 = 日后各自漂移(改一处漏一处)"
        )
        own_nc = re.sub(r"/\*.*?\*/", "", own, flags=re.S)  # 先剥注释, 注释里的示例不算
        stray = [
            " ".join(mo.group(1).split()) for mo in re.finditer(r"([^{}]*)\{([^}]*)\}", own_nc)
            if "scrollbar-width" in mo.group(2) and ".group-table" in mo.group(1)
        ]
        assert not stray, (
            f"{ui} 皮肤自有 CSS 里又给 .group-table 声明了 scrollbar-width({stray}) —— "
            "隐藏规则单点在 shared/hscroll.css, 第二份副本 = 日后各自漂移"
        )
        # 判据 6: 共享层链接集逐字相同(有序) —— shared/fx/* 豁免: fx 动效库只挂
        # flux(计划 26-10-31-2316 S6, D14 存量隔离拍板), 不参与四皮肤一致口径;
        # 其挂载与级联序由 test_frontend_fx_wiring 单独钉
        shared_sets[ui] = [
            h for h in re.findall(r'href="(/shared/[^"]+\.css)"', shell) if not h.startswith("/shared/fx/")
        ]
    base_shared = shared_sets[_UI_ALL[0]]
    assert "/shared/hscroll.css" in base_shared, ("共享层链接集里没有 /shared/hscroll.css(有序清单抽取口径坏了? 同步本守阵)")
    for ui in _UI_ALL[1:]:
        assert shared_sets[ui] == base_shared, (
            f"{ui} 的 /shared/*.css 链接集与 {_UI_ALL[0]} 不一致 —— 共享层挂载漂移 = 该皮肤缺规则, "
            f"而规则只有一份, 缺了就是整条静默失效: {_UI_ALL[0]}={base_shared} / {ui}={shared_sets[ui]}"
        )

    # 判据 7: CSS 类名 ←→ JS 建 DOM / classList 操作同侧(改名只改一侧 = 胶囊恒不可见且零报错)
    for sel in (".hscroll-pill", ".hscroll-pill.on", ".hscroll-pill.drag", ".hscroll-pill > i"):
        assert sel in hcss, (f"shared/hscroll.css 缺选择器 `{sel}` —— CSS 与 columns.js 的 DOM 契约只剩一侧, "
                             "类名不同名时胶囊恒不可见且零报错")
    cols_js = read_shared("columns.js")
    assert '"hscroll-pill"' in cols_js, ("columns.js 里没有 \"hscroll-pill\" —— 建 DOM 用的类名被改/被删, CSS 那四条规则整族空转")
    for cls in ("on", "drag"):
        assert re.search(r'classList\.(?:toggle|add|remove)\("%s"' % cls, cols_js), (
            f"columns.js 里没有对 `{cls}` 的 classList 操作 —— 与 CSS 的 .hscroll-pill.{cls} 断链: "
            f"胶囊永不{'显示' if cls == 'on' else '加粗/保持可见'}(零报错)"
        )

    # 判据 7b: 色系契约 —— 滑块与轨道必须分属两个色系, 且 hover 不许改轨道色(2026-11-01 用户反馈)
    # 初版: 轨道 hover 提亮到 --fg-dim, 滑块用 --fg-muted, 两者同属中性灰系 ⇒ 一提亮就几乎同色,
    # 实测对比度 静息 2.78~3.79:1 → hover 1.21~1.74:1(golden 1.21 基本等于同色), 可拖动部分
    # 反而更难辨认。修法 = 轨道恒中性 --border-strong, 滑块换主题强调色 --accent, hover 只加粗。
    # 这条断言钉两件事: ①滑块必须用 --accent(不是任何灰阶令牌); ②hover/.drag 规则体内**不得**
    # 出现 background —— 一旦有人"顺手给 hover 加个提亮", 滑块与轨道的对比度会被自己拉平, 而这
    # 种退化在真浏览器里只表现为"看起来糊在一起", 没有任何报错。
    thumb_body = re.search(r"\.hscroll-pill > i\s*\{([^}]*)\}", hcss)
    assert thumb_body, "shared/hscroll.css 找不到 `.hscroll-pill > i` 规则体(选择器在但块解析不到, 同步本守阵)"
    assert "var(--accent)" in thumb_body.group(1), (
        "滑块(`.hscroll-pill > i`)没用主题强调色 var(--accent) —— 与中性轨道同属灰系时"
        "两者亮度接近, 用户分不出哪一段能拖(2026-11-01 报障形态)"
    )
    hover_body = re.search(r"\.hscroll-pill:hover,\s*\.hscroll-pill\.drag\s*\{([^}]*)\}", hcss)
    assert hover_body, "shared/hscroll.css 找不到 `.hscroll-pill:hover, .hscroll-pill.drag` 规则体(同步本守阵)"
    assert "background" not in hover_body.group(1), (
        "hover/.drag 规则体里出现了 background —— hover 改轨道色会改变滑块与轨道的对比度: "
        "早先提到 --fg-dim 后与滑块几乎同色(实测 1.21~1.74:1), 交互反馈请只走高度"
    )

    # 判据 8: syncHeadScroll 尾部仍调 _hscrollSync(删了 = 胶囊永不出现)
    anchor = "syncHeadScroll(ev, page) {"
    assert anchor in cols_js, "columns.js 缺横滚同步单点 syncHeadScroll(ev, page)(被删/改名? 同步本守阵)"
    seg = cols_js[cols_js.index(anchor):]
    seg = seg[:seg.index("\n    },")]
    assert "this._hscrollSync(ev.target, page)" in seg, (
        "columns.js syncHeadScroll 尾部不再调 _hscrollSync —— 指示条唯一的几何入口被摘掉, "
        "胶囊永远停在初始几何(实际表现: 永不出现)"
    )
    anchor = "_hscrollSync(el, page) {"
    assert anchor in cols_js, "columns.js 缺 _hscrollSync(el, page)(指示条几何单点被删/改名?)"
    body = cols_js[cols_js.index(anchor):]
    body = body[:body.index("\n    },")]
    for page in ("group", "torrent", "show"):
        assert f'page !== "{page}"' in body, (
            f"columns.js _hscrollSync 的主表白名单缺 `{page}` —— 三个主表 id 必须齐全: "
            "漏一个 = 该页胶囊永不出现; 白名单整条被删 = 抽屉变体面(shared/tpl/xtpl.html:360)每次横滚 "
            "都在 body 里留下一个永不用的胶囊"
        )

    # 判据 9: 文档级监听必须挂载即绑(调用点在 _ensureHeadObserver 体内)
    anchor = "_ensureHeadObserver() {"
    assert anchor in cols_js, "columns.js 缺 _ensureHeadObserver()(挂载钩子被删/改名?)"
    body = cols_js[cols_js.index(anchor):]
    body = body[:body.index("\n    },")]
    assert "this._hscrollBind()" in body, (
        "columns.js _ensureHeadObserver 体内不再调 _hscrollBind() —— 监听退回「第一次横滚才挂」, "
        "从没横滚过的用户(纯鼠标、无触控板, 正是本方案要补的那类人)永远见不到胶囊, 且零报错"
    )
    anchor = "_hscrollPill() {"
    assert anchor in cols_js, "columns.js 缺 _hscrollPill()(胶囊建 DOM 单点被删/改名?)"
    body = cols_js[cols_js.index(anchor):]
    body = body[:body.index("\n    },")]
    assert "this._hscrollBind()" not in body, (
        "columns.js _hscrollPill() 体内又出现了 _hscrollBind() —— 这正是 ef734485 修掉的缺陷: "
        "监听与建 DOM 同生共死 = 不横滚就不建 DOM、不建 DOM 就不挂监听、不挂监听就永远不建"
    )


def test_frontend_pinned_first_cell_hover_transition_parity():
    """必显列(吸左首格)悬停过渡与行板同源守阵(2026-10-20 修「滑过时背景与其它列不一致, 短暂后恢复一致」)

    **报障与根因**: 行板 `.group-row` 自带 `transition: background var(--dur)`(160ms), 而吸左首格
    (三主表的必显列 = name / site)此前**没有任何过渡** ⇒ 鼠标滑过瞬间首格已 snap 到 `--bg-hover`,
    其余列还在从 `--bg-row` 渐入, 160ms 内行内出现一条比其余列更亮的竖带, 过渡结束后又"恢复一致"
    (真浏览器逐帧采样: prism/frost Δ14、atlas/ocean Δ18, 三主表 × 双皮肤全部命中; 移出方向同理反号)。
    修法 = 首格补同源时长/缓动的 `background-color` 过渡(渐变状态不可插值的残留见坑档 frozen-column)。

    钉四件事, 缺任一件即回到 snap 或竖带:
    1. 行板过渡仍带 `background` 且时长读 `--dur`(首格必须与它**同源**, 两处各写字面值会悄悄漂移);
    2. `.group-row > :first-child` 体内声明 `transition: background-color var(--dur)` —— 改了行板
       时长就再也对不上, 故不许写字面毫秒;
    3. 首格悬停镜像规则仍在(`:hover > :first-child` → `--bg-hover`), 丢了它首格会在整段悬停期
       停在基色上(持久竖带, 比闪一下更重);
    4. 首格过渡**只在三皮肤 views.css 单点声明** —— 抽屉按面重锚(shared/dt_table.css)与变体注入
       CSS 一律不得自带 `transition`(否则脱离 --dur 单点, 与行板错拍)。2026-10-20 审计实测: 三个
       主表 + 经典抽屉表 + 06/07/09/10/11 六个变体面, 滑入/移出逐帧差全 0, 正是「全部继承同一条
       皮肤规则」的结果 —— 本款把这个前提钉死。
    行为面(逐帧底色差 ≤ 2、稳态同色)由 e2e/main-table-pinned-hover.spec.mjs 采; 这里只钉声明式契约。
    """
    for ui in _UI_ALL:
        # 行板规则所在文件按皮肤分家(prism 在 views.css; atlas/console 在 components.css), 按特征
        # `position: relative` 认块 —— 不硬编码文件名, 以免某次「规则搬家」把守阵变成摆设。
        row_body = None
        for name in ("views.css", "components.css"):
            path = os.path.join(STATIC_ROOT, ui, "css", name)
            if not os.path.exists(path):
                continue
            text = open(path, encoding="utf-8").read()
            mo = re.search(r"\n\.group-row \{([^}]*)\}", text)
            if mo and "position: relative" in mo.group(1):
                row_body = mo.group(1)
                break
        assert row_body is not None, f"{ui} 找不到行板 .group-row 规则(首格过渡的时长基准)"
        assert "transition: background var(--dur)" in row_body, (
            f"{ui} 行板过渡未以 `background var(--dur)` 声明(时长单点被改/被删?) —— "
            "首格过渡与它同源, 基准不在则对不上"
        )
        css = open(os.path.join(STATIC_ROOT, ui, "css", "views.css"), encoding="utf-8").read()
        ms = re.search(r"\.group-row > :first-child \{([^}]*)\}", css)
        assert ms, f"{ui} views.css 缺 .group-row > :first-child 吸左首格规则"
        cell = ms.group(1)
        assert re.search(r"transition:\s*background-color\s+var\(--dur\)", cell), (
            f"{ui} 吸左首格缺 `transition: background-color var(--dur)` —— 行板渐变 160ms 而首格瞬切, "
            "滑过/移出瞬间行内现竖带, 过渡完才\"恢复一致\"(2026-10-20 用户报障)"
        )
        assert not re.search(r"transition:\s*background(-color)?\s+\d",
                             cell), (f"{ui} 首格过渡写了字面时长 —— 必须读 var(--dur), 否则行板调时长时又漂")
        mh = re.search(r"\.group-row:hover > :first-child \{\s*background: var\(--bg-hover\);\s*\}", css)
        assert mh, (
            f"{ui} 缺首格悬停镜像 `.group-row:hover > :first-child` —— 行板悬停变 --bg-hover 而首格停在"
            "--bg-row, 整段悬停期呈持久竖带(比过渡期闪一下更重)"
        )
    # ④ 首格过渡只能在三皮肤 views.css 单点声明。抽屉按面重锚(shared/dt_table.css)只改背景色值,
    #    变体注入 CSS 只改版式 —— 任一处自带 transition 就会脱离 var(--dur), 与行板错拍。
    #    2026-10-20 审计: 主表三页 + 经典抽屉表 + 06/07/09/10/11 六面, 滑入/移出逐帧差全 0,
    #    前提就是「这些面都没有自己的首格过渡声明」。
    stray = []
    for dirpath, _dirs, files in os.walk(STATIC_ROOT):
        for name in sorted(files):
            if not name.endswith(".css"):
                continue
            path = os.path.join(dirpath, name)
            rel = os.path.relpath(path, STATIC_ROOT).replace(os.sep, "/")
            if rel in {f"{ui}/css/views.css" for ui in _UI_ALL}:
                continue  # 单点本人
            if rel == "shared/row_lang.css":
                continue  # 行语言结构规则单点(计划 26-10-30-0217 阶段2): 其 :first-child 规则里的
                # transition 只有名称列左条 ::before 的 opacity/background .12s 渐入(行语言本体
                # 动效, D4 拍板 M2)。首格 hover/选中底 26-10-30 复验二修后 = color-mix 现算纯色
                # 直接换 background-color(::after 覆盖层已撤销), 底色过渡继承三皮肤 views.css
                # 首格的 `background-color var(--dur) var(--ease)` 单点 —— row_lang.css 自身
                # 不声明任何首格底色 transition, 与本守阵钉死的「单点声明」前提一致。
                # 其余抽屉/变体面照旧禁自带 transition。
            text = open(path, encoding="utf-8").read()
            for mo in re.finditer(r"([^{}]*)\{([^}]*)\}", text):
                sel, body = mo.group(1), mo.group(2)
                if ":first-child" not in sel and ":first-of-type" not in sel:
                    continue
                if ".group-row" not in sel and ".h-cell" not in sel:
                    continue
                if "transition" in body:
                    stray.append(f"{rel}: {' '.join(sel.split())[:70]} 体内带了 transition")
    assert not stray, ("首格过渡声明出了皮肤单点(views.css) —— 以下抽屉/变体面规则自带 transition, 会与行板错拍:\n  - " + "\n  - ".join(stray))


def test_frontend_pinned_first_cell_selected_row_keeps_base():
    """选中/半选行「保留行底」守阵(2026-10-20 修「选中的行必显列背景与其它列不一致」)

    **报障与根因**: 选中的行里必显列(吸左首格)与其余列底色不同 —— 一条整列高的异色竖带。
    旧规则 `.group-row.selected { background: var(--sel-bg) }` 用**半透明 tint 替换**了行底(而不是叠在
    行底上), 于是行板实际露出的是页底 `--bg`; 而吸左首格的合成基色是 `--bg-row`(坑档
    pitfalls/web-ui/frozen-column.md ②⑥ 的按面重锚口径) ⇒ 两侧承光底分家。真浏览器实测(1440×900,
    选中首行, 首格与相邻格同相对位置取像素): atlas Δ9/255、prism Δ5/255, 三主表 × 双皮肤全中;
    未选中行 Δ0。修复 = 行底不被状态替换: 同色 `linear-gradient(tint, tint)` 叠 `var(--bg-row)`,
    与首格镜像同一个合成表达式 ⇒ 逐字节相等(修后实测 atlas ≤1 取整、prism 0)。

    钉三件事:
    1. `.group-row.selected` / `.group-row.partial` 的 background 末层必须是 `var(--bg-row)` ——
       裸 `var(--sel-bg)` 等于把行底换成半透明, 页底透上来(本条就是报障形态);
    2. tint 令牌与首格镜像**同字面**(`var(--sel-bg, var(--accent-soft))`), 两处各写一份会随主题漂移;
    3. 首格镜像 `.group-row.{state} > :first-child` 的合成基色与行板**同令牌**(`var(--bg-row)`) ——
       这条把「行板留底」与「首格取该底」锁成一对, 任改一边即红(改一边仍自洽的形态静态看不出,
       故行为面另有 e2e 采计算背景逐字相等)。
    成员行没有吸左首格、也不承 row 底色 ⇒ 保持裸 tint 写法; 这里只钉它没在拆分时被丢掉。
    """
    tint = r"var\(--sel-bg,\s*var\(--accent-soft\)\)"

    for ui in _UI_ALL:
        css = open(os.path.join(STATIC_ROOT, ui, "css", "views.css"), encoding="utf-8").read()
        rules = _css_rules(css)
        for state in ("selected", "partial"):
            row_bg = _css_bg(_css_body(rules, f".group-row.{state}", f"{ui} views.css"))
            assert row_bg.endswith("var(--bg-row)"), (
                f"{ui} `.group-row.{state}` 的行底被半透明 tint 替换了(background 末层不是 --bg-row) —— "
                "行板透到页底 --bg 而吸左首格按 --bg-row 合成, 选中行名称列成整列异色竖带"
                "(实测 atlas Δ9/255、prism Δ5/255; 2026-10-20 用户报障)"
            )
            assert "linear-gradient(" in row_bg and re.search(tint, row_bg), (
                f"{ui} `.group-row.{state}` 的 tint 未走「同色 linear-gradient 叠行底」, 当前: {row_bg}"
            )
            cell_bg = _css_bg(_css_body(rules, f".group-row.{state} > :first-child", f"{ui} views.css"))
            assert cell_bg.endswith("var(--bg-row)"), (
                f"{ui} `.group-row.{state} > :first-child` 的合成基色不是 --bg-row, 当前: {cell_bg} —— "
                "首格与行板必须读同一个行底令牌, 否则两侧承光底分家"
            )
            assert re.search(tint, cell_bg), (f"{ui} `.group-row.{state}` 首格镜像的 tint 与行板不同字面, 当前: {cell_bg}")
        assert re.search(r"\.member-row\.selected\s*\{",
                         css), (f"{ui} 拆分行板规则时丢了 `.member-row.selected`(成员行选中态柔底) —— 成员行没有吸左首格, "
                                "不参与合成, 必须保留")


def test_frontend_pinned_first_cell_expanded_row_keeps_base():
    """展开行「保留行底」守阵(2026-10-20, 用户「group 一同修」与选中态同轮收掉下沉态)

    `.group-row.expanded { background: var(--bg-sunken) }` 与选中态是同一类缺陷: 半透明下沉底**替换**
    了行底 ⇒ 行板承光层变成页底 `--bg`, 而吸左首格按 `var(--bg-row)` 合成(坑档
    pitfalls/web-ui/frozen-column.md ⑩)。真浏览器逐像素(辅种页展开行, 首格与相邻格同相对位置):
    atlas Δ5/255、prism Δ2/255 —— 低于可辨阈(20), 上一轮按「范围守恒」未动, 本轮一并收(修后 Δ0)。

    钉三件事:
    1. `.group-row.expanded` 的 background 末层是 `var(--bg-row)`(prism 在 views.css,
       atlas/console 在 components.css —— 按选择器找, 不硬编码文件);
    2. 首格镜像 `.group-row.expanded > :first-child` 同基色(任改一边即分家);
    3. `.group-row.expanded:hover` 若自带 background(console 独有, 压过行板悬停), 同样不得跌回裸
       `--bg-sunken` —— 否则悬停那一下又露出页底。
    """
    for ui in _UI_ALL:
        row_body = None
        for name in ("views.css", "components.css"):
            path = os.path.join(STATIC_ROOT, ui, "css", name)
            if not os.path.exists(path):
                continue
            for sels, body in _css_rules(open(path, encoding="utf-8").read()):
                if ".group-row.expanded" in sels:
                    row_body = body
                    break
            if row_body:
                break
        assert row_body, f"{ui} 找不到 `.group-row.expanded` 行板规则(展开态底色契约的落点)"
        bg = _css_bg(row_body)
        assert bg.endswith("var(--bg-row)"), (
            f"{ui} `.group-row.expanded` 的行底被半透明下沉底替换了(background 末层不是 --bg-row) —— "
            "行板透到页底 --bg 而吸左首格按 --bg-row 合成, 展开行名称列成异色竖带"
            "(实测 atlas Δ5/255、prism Δ2/255; 2026-10-20 用户报「group 一同修」)"
        )
        assert "linear-gradient(" in bg and "var(--bg-sunken)" in bg, (
            f"{ui} `.group-row.expanded` 未走「同色 linear-gradient 叠行底」, 当前: {bg}"
        )
        views = open(os.path.join(STATIC_ROOT, ui, "css", "views.css"), encoding="utf-8").read()
        cell_bg = _css_bg(_css_body(_css_rules(views), ".group-row.expanded > :first-child", f"{ui} views.css"))
        assert cell_bg.endswith("var(--bg-row)"), (
            f"{ui} `.group-row.expanded > :first-child` 的合成基色不是 --bg-row, 当前: {cell_bg} —— "
            "首格与展开行板必须读同一个行底令牌"
        )
        mhover = re.search(r"\.group-row\.expanded:hover\s*\{([^}]*)\}", views)
        if mhover and "background:" in mhover.group(1):
            hbg = _css_bg(mhover.group(1))
            assert hbg.endswith("var(--bg-row)"), (
                f"{ui} `.group-row.expanded:hover` 自带 background 却跌回了半透明({hbg}) —— "
                "悬停展开行那一下首格与行板又分家"
            )


def test_frontend_ctx_src_target_marker_parity():
    """右键目标行「持续可见标识」守阵(2026-11-02 用户报「强调动效结束后看不出右键目标行」)

    现象: 右键种子行时只有一次性强调, 动效结束后行上没有任何持久标记 —— 用户无法确认
    "这次菜单操作针对哪一行"。

    口径(三态不可混): 选中 = `--sel-bar` 左条 + `--sel-bg` 底色; 键盘光标 = `.kb-cursor`
    1px 虚线; 右键目标 = `.ctx-src` **实心 2px accent 闭合框(outline, offset -2px), 不铺底色,
    不用左条**。
    故本守阵钉四件事(四皮肤逐条同值):
    1. 四个行类(group/member/show/ep)都被 `.ctx-src` 规则覆盖 —— 漏一支 = 该视图右键无标识;
    2. 标记是静态声明(实心 2px accent outline, offset -2px), 不依赖一次性动效; 禁用 box-shadow
       (row_lang flat 行语言会归零)与左条(与选中条同几何同色);
    3. 规则体内**零 background**、零 `--sel-*` 令牌 —— 否则会被读成"已选中";
    4. 不挂 animation —— 标识必须常驻菜单打开期间, 而不是闪一下。
    """
    bodies = {}
    want_outline = "outline: 2px solid var(--accent); outline-offset: -2px"
    for ui in _UI_ALL:
        rel = f"{ui}/css/components.css"
        path = os.path.join(STATIC_ROOT, ui, "css", "components.css")
        rules = _css_rules(open(path, encoding="utf-8").read())
        for sel in (".group-row.ctx-src", ".member-row.ctx-src", ".show-row.ctx-src", ".ep-row.ctx-src"):
            assert any(sel in sels for sels, _ in rules), f"{rel} 缺 `{sel}` 规则 —— 该行类右键时无目标标识"
        body = " ".join(_css_body(rules, ".group-row.ctx-src", rel).split())
        assert want_outline in body, (
            f"{rel} 的 .ctx-src 标识退化了(期望 `{want_outline}`) —— "
            "box-shadow 会被 row_lang.css 的 flat 行语言归零(atlas 实测恒 none), 左条又与选中条同几何同色"
        )
        assert "box-shadow" not in body, (
            f"{rel} 的 .ctx-src 用 box-shadow 画框 —— row_lang.css 的 flat 行语言(特异性更高)会把它归零, "
            "皮肤里怎么写都不生效"
        )
        assert "background" not in body, f"{rel} 的 .ctx-src 铺了底色 —— 会被误读成「已选中」"
        assert "--sel-bar" not in body and "--sel-bg" not in body, (f"{rel} 的 .ctx-src 引用了选中态令牌族 —— 右键目标与选中必须两套视觉")
        assert "animation" not in body, (f"{rel} 的 .ctx-src 挂了 animation —— 标识会在动效结束后消失, 正是本单要修的形态")
        bodies[ui] = body
    assert len(set(bodies.values())) == 1, (
        "各皮肤的 .ctx-src 标识不一致 —— 全皮肤必须逐条同值(用户口径: prism/atlas 一致, 另两皮肤不漂移):\n" +
        "\n".join(f"  {k}: {v}" for k, v in bodies.items())
    )
