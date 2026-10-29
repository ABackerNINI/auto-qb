"""test_webui_static_skins 测试计划: webui 前端资产静态守阵: 皮肤清单 / CSS / 挂件类名

## 测试计划(每个测试函数一条)
- test_frontend_static_bundle_health: 前端静态资源静态守阵(冲突标记/注释孤儿续行/node --check 语法校验/CSS 规则漏闭合/CSS 注释提前终止/<transition> 吞弹窗/静态引用缺失/追剧视图集成员取 hash 未走 memberHashesOf/STATE_RANK 与后端 _SHOW_STATE_RANK 漂移 + STATE_RANK_LAST 兜底秩与 _SHOW_STATE_RANK_LAST 一致 / 键位归一化正则 KB_DEF_RE 与后端 _KEYS_SERIAL_RE 逐字一致 / ETA 哨兵与后端 _ETA_SENTINEL 跨层一致(全树零命中即红) / 页面挂件类名必须有对应 CSS 规则 / 列模型每列必须有值单元格分支+默认隐藏单点接线 —— 均为"pytest 全绿但界面废掉"的故障形态)
- test_frontend_template_split_wiring: 模板分片接线守阵(26-09-26 拆分 plans/26-09-26-2233 W1) —— 清单完整性(漏挂=整块消失 / 404=整页占位 / into 非法)+ 双 UI 分片名单同名同序 + 聚合标签配平 + shell≤212 行(S1 定 200, 26-10-06-0838 S5/S6 各 +3, R2 26-10-09-2219 S1 +4, W6 26-10-13-0811 +2)/单分片≤400 行 + 清单脚本序(vendor 首 app.js 尾) + 三皮肤 CSS 链接序(atlas/console: style→components→views→dialogs; prism: tokens→五主题→base→components→views→dialogs, 弹窗层必须最后)与单文件 700 行体量口径(prism/css/views.css 818 行存量冻结, 只许减不许增)
- test_frontend_skin_css_token_parity: 三皮肤令牌**名集**相等守阵(issue 26-10-20-2231) —— 皮肤少声明令牌 = 该皮肤下 `var(--x)` 整条声明在计算值阶段作废且无报错(星图此前少 3 个字体令牌 86 vs 89, 自己 4 处 `var(--font-mono)` 裸引用全程失效、共用层只能各写兜底链); 钉名集相等(取值自由), 差异按缺/多两侧成对报出
- test_frontend_shell_sprite_login_parity: 三份 index.html shell 内联段守阵(issue 26-10-20-2231) —— sprite 段(80 行/67 symbol)三皮肤逐字相等(manifest 已被 split_wiring 钉死, 本守阵补上 sprite 与 login)+ #app+login 段(注释/空行归一后, console 合法多一行皮肤说明注释)相等; symbol 数下限防"sprite 整体外提成共享文件后三份同时消失、相等断言恒真"; 失败信息提示"改图标/改登录遮罩须三皮肤同步"
- test_frontend_button_system_paired: 按钮体系(.bt)迁移守阵 —— ce-btn/ce-icon 全语料零残留、.bt 六变体两套 CSS 成对定义、两套模板 bt 用量逐类相等、双色令牌(on-accent/on-accent-ink/on-error)星图 :root + 棱镜五主题成对声明
- test_frontend_search_syntax_wiring: 搜索匹配**服务端单点**的前端接线守阵 —— 清除钮 @mousedown.prevent 成对(焦点态清除失灵回归)/前端不得复活任何文本匹配实现(filters.js _parseSearchQuery 等四函数、hr.js/shows.js 旧整句 includes、app.js searchHitsQ 均已删, 复活即红)/filteredTorrents 必须消费 searchHits
- test_frontend_search_pending_no_collapse: 搜索待响应期空命中集不得接管列表(2026-10-07 修详情面板/流量图搜索跳动) —— view.js searchPending 生命周期(输入武装防抖即置位/doSearch 直达入口补武装/resetSearch 清除/落袋且过代际守卫后清除) + filters.js _searchGateActive 单点(待响应且命中集未落袋 = 门不生效, 两个派生 filteredTorrents/filteredGroups 都走它; 渐进输入命中集非空仍按旧集过滤) + 三皮肤 .layout min-height: calc(100vh - var(--head-h)) 撑满首屏(停靠面板 sticky 锚点与列表长短无关, 筛到短列表不再脱锚跳)
- test_frontend_hr_safety_wiring: 删除安全档位前端接线守阵 —— hr.js 的 token 映射表与后端 resolve.py 的 SRC_* 常量逐字一致、做种时长列每套 UI 2 处换绑 hrDurClass/hrSrcClass(计划 26-10-11-1722 P2 起明细成员单元格收敛为单份 <aq-member-cells> 渲染器, 触发面 3→2, 该渲染器由辅种页/追剧页共用)+ 挂 hrSrcFull/hrSrcHalf 底线与 hrPopEnter 触发 + 来源与已排除文案都走 hrDurHint 进 title(行内不留 chip) + 弹窗单例 DOM 每套 UI 恰一份、三套 CSS 的 hr-warn/hr-line/hr-pop 成对定义、js 引用的 m.hr_* 字段都在后端 hr_view_fields 键集里(字段打错 = 页面静默空白)
- test_frontend_hr_detail_table_wiring: HR 表① 全量详情表前端接线守阵(计划 26-10-01-2216 阶段2 + 26-10-02-1936 阶段3) —— 设置分区表① 模板绑定(档位 chips 本地过滤/已删除种子切换钮/明细行/空态/失踪行挂钩/「数据截至」时间戳/三列重组列名「核实结论」「在列」)+ 拍板守卫(remain_seconds 不进表、不挂 hr-pop、单元格无原生 title、表① 段无 <details>(排障视图在 aqb:hr-diag 独立段)、来源徽章类名 hr-vsrc 不复用已退役 hr-src)+ hr_status.js 按站点明细加载与本地筛选且无 setInterval(不轮询)+ .hr-detail-table 与档位色义四档/失踪行 --paused 弱化/来源徽章样式在三套 UI CSS 成对定义(prism 拆 components.css + views.css 两件)
- test_frontend_hr_table_sort_filter_reorg_wiring: HR 表① 已删除种子过滤 + 三态排序 + 三列重组守阵(计划 26-10-02-1936 阶段3; 文案 26-10-03 定) —— 切换钮默认「显示已删除种子 (N)」且 oldOn 默认关(只看本地仍在列), 旧误导文案「未做种/只看做种中」零残留; 表头十列全 sortable(26-10-29 修复 issue 26-10-29-1348: 列定义补齐 sortable: true —— HRS_SORT_VAL 十键全有访问器; P5 起 markup 收敛到表壳组件 thead 模式, 本守阵改钉 <tr is="vue:aq-table" mode="thead"> 接线 + HR_TABLE_DEFS 注册表十列键 + thead sortable 类/箭头门控同源 col.sortable)而表② 波次表无 sortable; 三态状态机(首点降→再点升→第三击恢复后端默认序, 换列直接降序); 比较器纯函数 hrsCompareRows 用 node 真跑(空值恒末位两方向不反转/verified_ts·last_seen 0 哨兵/档位 A<B<C<D 固定秩/字符串数值分型), 无 node 静默跳过; 新列结构(核实结论徽章+副行 / 在列·失踪徽章+副行)与 CSS 三处成对(th.sortable 箭头 accent·hover faint / .hr-sub 副行 / .hr-pres 徽章 / 名称列限宽钩子 + .hr-full-modal 放开); 旧列辅助 hrsVerifiedText/hrsStatusText 与死件 hrsArrowHref 零残留; 表① 排序箭头绝对定位不占流(计划 26-10-06-1009 §7: 原 display:inline-block 恒占 14px, 把右对齐 num 列表头文字整体左顶)
- test_frontend_table_registry_single_point: 表注册表守阵(计划 26-10-11-1722 P0) —— app.js 必须有 `TABLE_DEFS` 且 `TABLE_PAGES` 由它派生(第二份表清单即红), 四张表(group/detail/torrent/show)的 `columns`/`headRef`/`tableRef` 必须指向既有单点且顺序 = 定义序(顺序漂移 = 列偏好按错表读), `columns.js`/`sort.js` 里四页字面量与 `viewMode` 分派零残留(复活即红 —— 那正是本单点要消灭的重复)
- test_frontend_table_shell_single_point: 表壳/行模型单元格渲染器单点守阵(计划 26-10-11-1722 P1/P2/P3/P5) —— 表头块 5 份内联副本收敛为 `<aq-table>`(shared/table.js + tpl/xtpl.html#tpl-aq-table); 127 条行模型单元格 v-if 分支收敛为五个单份渲染器 `<aq-member-cells>`(member, xtpl.html)/`<aq-group-cells>`/`<aq-torrent-cells>`/`<aq-show-cells>`/`<aq-ep-cells>`(tpl/xtpl-cells.html); 钉 ①六个组件都 app.component 注册 ②表壳模板恰一份且四件交互把手(.h-cell/.h-label/.arrow/.resizer/.col-drop-line)齐备 ③groups.html/shows.html 各 2 个、torrents.html 1 个 `<aq-table>` 调用点、三个页面模板 `.h-cell` 内联零残留、各页行模型渲染器调用点齐备 ④thead 模式(P5): 设置页 HR 详情表表头借壳, 占位须 `<tr is="vue:aq-table" mode="thead">` 且该段内联 `<th>` 零残留; thead 可排序性判据同源 col.sortable(sortable 类与箭头 v-if 由它驱动, issue 26-10-29-1348)
- test_frontend_site_alert_icon_wiring: 站点 chip 改色表达守阵(计划 26-10-19-2206 S4, 取代 26-10-19-2007 的两槽口径) —— 站点问题走**颜色**(缺配置橙底+虚线下边 / tracker 报错红底)、命令结果走**图标**且固定放站点名之后: 三皮肤样式键集相等(含 reduced-motion 降级/搜索命中让出底色/明细行染色)/模板三处 cell 只剩一个图标槽且 tooltip 挂整块 chip/旧图标类 `.sa` 零残留/token->符号单点只含命令结果四种
- test_frontend_frozen_column_boundary_wiring: 首列吸左边界提示守阵(2026-10-11 修「向右滚动时状态列被名称列盖住」) —— 横滚时相邻列滑进吸左首格(26-10-06-1717)下方, 未盖满的尾字("做种"的"种"等)紧贴首格右缘露出, 无边界提示时残根读成与名称省略号粘连的坏字(误读成渲染 bug); 钉两层接线: 横滚同步单点 columns.js::syncHeadScroll(ev, page)(P4 把 menu/selection/shows 三份收敛为一份)必须给滚动容器与吸顶表头打 .is-hscrolled(scrollLeft>0 打 / 回 0 摘, CSS 无法感知 scrollLeft, 丢标 = 落影永不出现)且三个滚动容器各带表 id 调用它, 三皮肤 views.css 的 .is-hscrolled 规则必须行吸左首格与表头吸左首格成对(漏表头 = 列名残根仍裸露)且含发丝线(inset -1px)成分、且**不得**再带右缘落影(2026-10-12 用户报「名称列后随机出现阴影」: 落影可见度随首格高度变, 常态行首格 22px 时塌成 2px 近不可见、高行才显形, 逐行深浅差 7 倍读成随机黑块)
- test_frontend_pinned_first_cell_bg_per_face: 必现列(吸左首格)底色按面重锚守阵(2026-10-14 修「必现列背景与其他列不一致」, 报障面 = 主表三页 + 抽屉全部变体表格) —— 两层根因: ① 皮肤 `.group-row > :first-child{background:var(--bg-row)}` 是主列表行语言, 抽屉各引擎面复用 .group-row(零特判)致首格与行板三样各算(族面 --tbl-face-bg→--bg / 04 卡 / 05·10 透明 / 08 --bg-row), 行内一条异色竖带(ocean Δ 16/255); ② 追剧表 search-hit 行底是「accent 渐层 over --bg-row」而首格只平铺 --bg-row, 整条渐层丢失(实测 backgroundImage=none)。修复单点 shared/dt_table.css 按面重锚: 族面 06/07/09/11 行板/表头首格同 Token(--tbl-face-bg/--tbl-head-bg) + 悬停 --bg-hover, err(06)/bad(07/09)/is-chk(11)/sel(10) 半透明 tint 一律 `linear-gradient(tint,tint), var(--bg-card)` 合成(**禁** --bg-row 基色/裸半透明令牌), empty-row 随行透明; 04·05 首格是内容根 ⇒ 摘底摘 position:static(05 failrow 保 error-soft); 10 保留吸左取 --bg-card; 08 bad 补合成; 三皮肤 views.css 补 search-hit 首格镜像(90deg 渐层 46% + --bg-row); 05 变体补内层行容器 dt05-list(家族两层 dtNN-wrap+dtNN-list, 修前单层 dt05-wrap 与 CSS 前缀不匹配致六条 .group-row 规则空转、行带主表卡底)。真浏览器量具 e2e/dt-table-face-bg.spec.mjs(首格可见底 == 行板可见底, 含悬停与 err/bad/is-chk/sel 状态行)
- test_drawer_tpl_variant_interaction_single_point: 变体交互单点定型守阵(计划 26-10-12-0527 U5①) —— drawer_tpl/*.js 全目录扫 ui.sort(手搓排序状态机不允许在任何变体复活); 凡声明 tableId+rowsFn(桥表格变体)的文件**声明即受检**, 另强制零表格容器列宽 grid(列宽唯一来源 = 引擎列集 computed; 版式 grid 卡片/双栏/图例是 D5 保留面) —— 未来新变体接引擎即自动落入本守阵, 无需改守阵, 即「定型」之义
- test_frontend_table_head_a11y: 引擎表头可访问性守阵(issue 26-10-12-0800, 计划 26-10-12-2330 方案 C) —— 语义载体用 role="columnheader"(**不是** button: aria-sort 只对该 role 生效, 挂 button 上读屏忽略) + 件套单点(shared/table.js 的 headAriaSort/headActivate 两方法, grid/thead 共用) + grid .h-cell 的 :aria-sort/:tabindex(仅可排序列)/Enter·Space keydown 全走 headActivate + .group-head role=row / 指示线 role=presentation + thead <th> 同补件套 + 三皮肤 .h-cell.sortable:focus-visible(atlas 落 views.css —— components.css 顶 700 行 cap); 键盘真按键行为在 e2e/table-head-a11y.spec.mjs
- test_frontend_pinned_first_cell_hover_transition_parity: 必显列(吸左首格)悬停过渡与行板同源守阵(2026-10-20 修「必显列鼠标滑过时背景与其它列不一致, 短暂后恢复一致」) —— 行板 `.group-row` 有 transition: background var(--dur)(160ms) 而吸左首格无过渡 ⇒ 滑入瞬间首格 snap 到 --bg-hover、其余列还在从 --bg-row 渐入, 160ms 内行内一条竖带, 过渡完才"恢复一致"(真浏览器逐帧: prism/frost Δ14、atlas/ocean Δ18, 三主表 × 双皮肤全中; 移出同理反号); 钉 ①行板过渡仍以 `background var(--dur)` 声明(时长基准) ②三皮肤 `.group-row > :first-child` 体内 `transition: background-color var(--dur)`(禁字面毫秒, 否则行板调时长又漂) ③首格悬停镜像 `:hover > :first-child` → `--bg-hover` 不得丢(丢了是整段悬停期的持久竖带) ④首格过渡**只在三皮肤 views.css 单点**, 抽屉按面重锚(dt_table.css)与变体注入 CSS 不得自带 `transition`(带即脱离 --dur 与行板错拍; 2026-10-20 审计: 主表三页 + 经典抽屉表 + 06/07/09/10/11 六面逐帧差全 0)。行为面(逐帧差 ≤ 2、稳态同色)由 e2e/main-table-pinned-hover.spec.mjs 真浏览器采
- test_frontend_pinned_first_cell_selected_row_keeps_base: 选中/半选行「保留行底」守阵(2026-10-20 修「选中的行必显列背景与其它列不一致」) —— 旧规则 `.group-row.selected { background: var(--sel-bg) }` 用半透明 tint **替换**行底(而非叠在行底上), 行板露出页底 `--bg`, 而吸左首格按 `--bg-row` 合成 ⇒ 两侧承光底分家, 选中行名称列整列异色竖带(真浏览器逐像素: atlas Δ9/255、prism Δ5/255, 三主表×双皮肤全中, 未选中行 Δ0); 钉 ①`.group-row.selected`/`.group-row.partial` 的 background 末层是 `var(--bg-row)`(裸半透明令牌即红) ②行板与首格镜像的 tint 同字面(`var(--sel-bg, var(--accent-soft))`) ③首格镜像合成基色与行板同令牌 ④拆分后 `.member-row.selected` 仍在(成员行无吸左首格, 保持裸柔底)。行为面(行板与首格计算背景逐字相等, 选中/悬停选中)由 e2e/main-table-pinned-selected.spec.mjs 采
- test_frontend_pinned_first_cell_expanded_row_keeps_base: 展开行「保留行底」守阵(2026-10-20 与选中态同轮收, 用户「group 一同修」) —— `.group-row.expanded { background: var(--bg-sunken) }` 同样把行底**替换**成半透明下沉底, 行板承光层变页底 `--bg`, 而首格按 `--bg-row` 合成; 真浏览器逐像素: 展开行 atlas Δ5/255、prism Δ2/255(低于可辨阈, 上轮按范围守恒未动); 钉 ①三皮肤 `.group-row.expanded` 的 background 末层是 `var(--bg-row)`(prism 在 views.css, atlas/console 在 components.css, 按选择器找) ②首格镜像同基色 ③console 独享的 `.group-row.expanded:hover` 不得跌回裸 `--bg-sunken`(否则悬停那一下又分家)。行为面由 e2e/main-table-pinned-selected.spec.mjs 的展开行用例采
- test_drawer_table_bridge_wiring
- test_drawer_tpl_table_face_bg_single_point
- test_frontend_tpl_ctl_bits_single_source
"""
import json
import os
import re
import shutil
import subprocess

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


def _assert_tags_balanced(text, label):
    """HTML 标签配平(HTMLParser 视角): 分片切割边界错位(把半个元素切进相邻分片)在聚合上现形

    分片本身因 wrapper 跨片(template v-else / .layout / .hb-wrap)**允许不配平**,
    配平只对「按清单序拼接后的聚合」成立 —— 它必须与拆分前的整页等价。
    void 元素与自闭合不参与; script/style 内容是 CDATA(内部尖括号不参与)。
    """
    from html.parser import HTMLParser

    void = {
        "meta", "link", "img", "input", "br", "hr", "source", "col", "area", "base", "wbr", "embed", "track", "param"
    }

    class _Balance(HTMLParser):
        def __init__(self):
            super().__init__(convert_charrefs=False)
            self.stack, self.bad = [], []

        def handle_starttag(self, tag, attrs):
            if tag not in void:
                self.stack.append((tag, self.getpos()[0]))

        def handle_startendtag(self, tag, attrs):
            pass

        def handle_endtag(self, tag):
            if tag in void:
                return
            if not self.stack:
                self.bad.append(f"多余的 </{tag}> @行{self.getpos()[0]}")
                return
            open_tag, open_line = self.stack.pop()
            if open_tag != tag:
                self.bad.append(f"</{tag}> @行{self.getpos()[0]} 与未闭合的 <{open_tag}> @行{open_line} 交错")

    p = _Balance()
    p.feed(text)
    p.close()
    leftovers = [f"<{t}> @行{l}" for t, l in p.stack]
    problems = p.bad + [f"未闭合的 {x}" for x in leftovers]
    assert not problems, f"{label} 标签不配平(分片切割边界错位?): " + "; ".join(problems[:8])


# CSS 容器型 at-rule: "开块后下一行是嵌套规则"属正常写法, 不参与"漏闭合"判定
_CSS_CONTAINER_AT = ("@media", "@supports", "@keyframes", "@container", "@layer", "@scope")
# 追剧视图的"集成员"两种写法(e.members / ep.members) —— 取 hash 必须经 memberHashesOf 归一
_EP_MEMBERS_RE = re.compile(r"\b(?:ep|e)\.members\b")


def _scan_css_blocks(path, rel, problems):
    """CSS 规则块守阵: 顶层规则开了块却没闭合, 而下一非空行又开了新规则 -> 漏写 `; }`

    (2026-09-17 实测: prism/css/views.css 曾有一条 `.ce-subcard .ce-field { … padding: 7px 0` 漏了
    `; }`, 浏览器把其后约 200 条规则整段当作"未结束的声明块"丢弃 —— 棱镜大半样式静默消失而
    pytest 全绿。注意**全文件花括号计数是配平的**(别处有多余 `}`), 只数括号查不出来。
    该规则本身已随经典设置页的死代码清理删除, 此处只作判据来源留档。)
    """
    with open(path, encoding="utf-8") as f:
        lines = f.read().splitlines()
    depth = 0
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        opens, closes = line.count("{"), line.count("}")
        if depth == 0 and opens > closes and not stripped.startswith(_CSS_CONTAINER_AT):
            nxt = next((l.strip() for l in lines[i:] if l.strip()), "")
            if "{" in nxt:  # 本块还没闭合, 下一行又开了新规则 -> 语法已坏
                problems.append(f"{rel}:{i} 规则块未闭合(下一非空行又开了新规则)")
        depth += opens - closes
        if depth < 0:
            problems.append(f"{rel}:{i} 多余的 `}}`")
            depth = 0
    if depth != 0:
        problems.append(f"{rel} 花括号未配平(差 {depth})")


def _scan_css_comments(path, rel, problems):
    """CSS 注释提前终止守阵: 注释体内的 `*/` 会把注释砍断, 尾巴落成代码态的孤立垃圾 ——
    浏览器按错误恢复丢弃到下一个 `}` 为止, **紧跟的那条规则整条静默消失**(无任何报错)。

    (2026-09-28 实测: console/css/components.css 进度条注释写了 `(s-*/member-row 族)`,
    `s-*` 后的 `*/` 提前闭合注释, 紧随其后的 `.m-progress { display: flex; … }` 被整条吞掉
    —— 三处表格(辅种/种子/追剧明细)进度条只剩百分比没有条。判据 = 浏览器同款注释语义
    (字符串感知)扫一遍: 正常文件的所有 `*/` 都应消费在注释态里, 代码态出现孤立 `*/` 即中招。)
    """
    with open(path, encoding="utf-8") as f:
        text = f.read()
    i, n = 0, len(text)
    in_comment = False
    str_ch = None
    while i < n:
        c = text[i]
        if in_comment:
            if c == "*" and i + 1 < n and text[i + 1] == "/":
                in_comment = False
                i += 2
                continue
            i += 1
            continue
        if str_ch:
            if c == "\\":
                i += 2
                continue
            if c == str_ch:
                str_ch = None
            i += 1
            continue
        if c in "\"'":
            str_ch = c
            i += 1
            continue
        if c == "/" and i + 1 < n and text[i + 1] == "*":
            in_comment = True
            i += 2
            continue
        if c == "*" and i + 1 < n and text[i + 1] == "/":
            line = text.count("\n", 0, i) + 1
            problems.append(f"{rel}:{line} 注释被体内 `*/` 提前终止(其后规则被浏览器整条丢弃)")
            i += 2
            continue
        i += 1


def _scan_template_transitions(path, rel, problems):
    """模板 `<transition>` 结构守阵: 必须配对, 且弹窗不得落在 `<transition>` 内

    (2026-09-17 实测: 抽屉外层多了一个未闭合的 `<transition name="pop">`, 于是统计/限速/添加/
    管理/确认框全被浏览器解析成它的子节点 —— `Transition` 只渲染第一个子节点, **所有弹窗被静默
    丢弃**: 点击毫无反应、控制台也不报错。配对计数 + 弹窗嵌套双查, 二者都能抓住这个 bug。)
    """
    with open(path, encoding="utf-8") as f:
        lines = f.read().splitlines()
    depth = 0
    for i, line in enumerate(lines, 1):
        low = line.lower()
        if "modal-mask" in low and depth > 0:
            problems.append(f"{rel}:{i} 弹窗(.modal-mask)落在 <transition> 内(Transition 只渲染首个子节点 -> 弹窗会被丢弃)")
        depth += low.count("<transition") - low.count("</transition>")
        if depth < 0:
            problems.append(f"{rel}:{i} 多余的 </transition>")
            depth = 0
    if depth != 0:
        problems.append(f"{rel} `<transition>` 未闭合(差 {depth})")


# `node -e` 批量校验脚本(不落盘): 逐文件按 **CommonJS 包装**编译 —— 与 `node --check` 同语义, 但只起一个进程。
# WARN: 必须经 `Module.wrap`: 裸 `new vm.Script(src)` 按**经典脚本**解析, 会把顶层 `return`(CommonJS 下合法)
#   判成语法错误 ⇒ 比原判据凭空变严(2026-09-23 实测: 同一批样本里只有该边界项判定不同)。
_NODE_SYNTAX_CHECK = (
    "const fs=require('fs'),vm=require('vm'),M=require('module');let bad=0;"
    "for(const f of process.argv.slice(1)){"
    "try{new vm.Script(M.wrap(fs.readFileSync(f,'utf8')),{filename:f});}"
    "catch(e){bad++;console.error(f+'\\t'+e.message);}}"
    "process.exit(bad?1:0);"
)


def _scan_js_syntax_with_node(js_files, problems):
    """有 node 时对前端 JS 做**真**语法校验(2026-09-17 起本机已装 node)

    这是启发式扫描(注释孤儿续行等)之上的一道硬闸: 任何语法错误都能以 `文件:行` 形式报出。
    无 node(未装的机器/精简 CI)时**静默跳过**本项 —— 不引入 pytest skip(基线是 0 skipped),
    启发式扫描仍在拦最常见的那类损坏。

    !2026-09-23 由「逐文件起一个 `node --check`」改为**单进程批量**: 20 个文件 = 20 次进程启动,
    实测 7.4s, 其中 95% 是进程启动开销(批量 0.38s)。校验语义已逐样本对齐过 ——
    6 个故障样本(注释孤儿续行 / 未闭括号 / 未闭字符串 / 未闭模板串 / 坏正则 / 未闭圆括号)
    + 1 个正常样本 + 1 个顶层 `return` 边界样本, 判定与 `node --check` **8/8 一致**。
    """
    node = shutil.which("node")
    if not node:
        return
    paths = [path for path, _rel in js_files]
    if not paths:
        return
    proc = subprocess.run([node, "-e", _NODE_SYNTAX_CHECK, *paths], capture_output=True, text=True)
    if proc.returncode == 0:
        return
    rel_of = {os.path.normcase(path): rel for path, rel in js_files}
    for line in (proc.stderr or proc.stdout).strip().splitlines():
        name, _, message = line.partition("\t")
        rel = rel_of.get(os.path.normcase(name.strip()), name.strip())
        problems.append(f"{rel} node 语法校验报错: {message.strip() or 'unknown'}")


def _section_members(text, section):
    """取片段文件 / app.js 里 `methods: {` 或 `computed: {` 块的成员名(4 空格缩进的 `name(` / `name:`)

    块结束判据 = **缩进不深于段起始行**的 `}` 或 `},`(2026-10-20 修, 计划 26-10-20-0024 W4):
    原判据写死 `line in ("  },", "  }")`, 只认 2 空格收尾 —— 对 `window.X = {` 缩进在 IIFE 内
    (2 空格对象 / 4 空格段 / 6 空格成员)的片段, 段的收尾是 4 空格, 判据不触发 ⇒ 扫描一路吃到
    下一个 `methods: {` 并把 "methods" 记成上一个段的**幻影成员**, 于是任意两个这种写法的片段
    互相"重名"(实测: drawer_templates.js 给 ctx_menu_custom.js 报 computed.methods 重名)。
    成员名仍只认 4 空格缩进(本仓库 col-0 对象约定下的成员位置) —— 深缩进片段的成员不在此扫描,
    与修改前一致, 不放宽也不收紧。
    """
    names, in_block, base = [], False, 0
    for line in text.splitlines():
        if not in_block:
            if line.strip() == section + ": {":
                in_block, base = True, len(line) - len(line.lstrip())
            continue
        indent = len(line) - len(line.lstrip())
        if line.strip() in ("},", "}") and indent <= base:
            break
        m = re.match(r"^    (?:async )?([A-Za-z_$][\w$]*)\s*[(:]", line)
        if m:
            names.append(m.group(1))
    return names


def _scan_mixin_wiring(problems):
    """拆分接线守阵(2026-09-20): 片段文件必须「HTML 引用了」且「app.js 注入了」, 且成员不得重名

    拆成多文件后有两类**静默**故障形态(pytest 全绿 / 界面局部废掉):
    1. 文件写了但漏加 <script> 或漏 app.mixin() —— 那一整块功能凭空消失, 控制台不报错
       (Vue 直接把没注册的 mixin 当不存在);
    2. 两个片段里出现同名成员 —— Vue 的 mixin 合并是**后者覆盖前者**, 不报错, 但被覆盖的那个
       实现从此永不执行(表现为"点了没反应"或行为回到旧逻辑)。
    """
    bundle = _app_bundle_files()
    refs = {rel for _p, rel in bundle}
    # boot.js 走 shell 静态 <script src>(它自己负责按清单放行其余脚本, 不在清单内), 两张 shell 的
    # 静态引用同样算"已接线"
    for ui in _UI_ALL:
        shell = open(os.path.join(STATIC_ROOT, ui, "index.html"), encoding="utf-8").read()
        refs |= {m.lstrip("/") for m in re.findall(r'<script src="(/shared/[^"]+\.js)"></script>', shell)}
    for dirpath, _dirs, files in os.walk(os.path.join(STATIC_ROOT, "shared")):
        if os.path.basename(dirpath) == "vendor":  # 第三方压缩产物, 不参与本仓库的片段约定
            continue
        for name in sorted(files):
            if not name.endswith(".js"):
                continue
            path = os.path.join(dirpath, name)
            rel = os.path.relpath(path, STATIC_ROOT).replace(os.sep, "/")
            if rel in refs:
                continue
            problems.append(f"{rel} 未被 tpl-manifest 清单或 shell 静态 <script> 引用(拆分片段漏挂 -> 整块功能静默消失)")

    app_text = open(os.path.join(STATIC_ROOT, "shared", "app.js"), encoding="utf-8").read()
    # 三种"已接线"形态:
    #   1. mixin    —— window.AQB_* 注入 Vue 实例
    #   2. component —— 注册为组件(如 hub-field 走 app.component)
    #   3. **行为基座** —— 被另一个全局用 `Object.assign({}, window.X, …)` 拷走复用(如 config_hub.js
    #      的 HUB_FIELD_COMPONENT 拷 config_editor.js 的 CE_FIELD_BASE)。它本身不是组件、不注册,
    #      但成员确实在跑 ⇒ 不该报"定义了没注入"。
    #      WARN: 只认 `Object.assign({}, window.X` 这一种形态(本项目唯一的复用写法), 不要放宽成"出现即算"。
    #      (2026-09-25: 经典设置页移除后 ce-field 组件与 tpl-ce-field 模板删除, 基座随之改名去组件化。)
    #   4. **根选项展开** —— `...window.X` 展开进 createApp 根组件选项(W2b: state.js 的 data/computed/watch
    #      与 lifecycle.js 的生命周期)。!这类成员**不许**走 app.mixin: 全局 mixin 会波及 hub-field 等
    #      组件实例(watch/mounted 双份执行)。只认 app.js 里 `...window.X` 展开形态, 不放宽。
    registered = set(re.findall(r"app\.mixin\(window\.(\w+)\)", app_text))
    registered |= set(re.findall(r"app\.component\(\s*\"[^\"]+\"\s*,\s*window\.(\w+)\)", app_text))
    registered |= set(re.findall(r"\.\.\.window\.(\w+)", app_text))
    for path, _rel in bundle:
        registered |= set(re.findall(r"Object\.assign\(\{\},\s*window\.(\w+)", open(path, encoding="utf-8").read()))
    seen = {}
    for path, rel in bundle:
        text = open(path, encoding="utf-8").read()
        for glob in re.findall(r"^window\.(\w+) = \{", text, re.M):
            if glob not in registered:
                problems.append(f"{rel} 定义了 window.{glob} 但 app.js 没有 app.mixin(window.{glob})(片段漏注入)")
        for section in ("methods", "computed"):
            for member in _section_members(text, section):
                if member in seen:
                    problems.append(
                        f"{rel} 的 {section}.{member} 与 {seen[member]} 重名 —— Vue mixin 后者覆盖前者, "
                        "被盖掉的实现永不执行且不报错"
                    )
                seen[member] = rel


def _scan_episode_member_hashes(text, rel, problems):
    """追剧视图"集成员 -> hash"守阵 (2026-09-19 实测事故)

    后端 shows 视图的 `members` 是 **hash 数组**, 而前端 `decoratedShows` 会把它换成**成员对象**
    (带 hit 标记, 供行内渲染/筛选)。菜单与命令只认 hash —— 一旦把对象当 hash 传出去, 拼进
    URL/JSON 时字符串化成 `[object Object]` ⇒ 后端查不到该 hash ⇒ 404「种子不存在」:
    整集/整剧的 开始/暂停/强制汇报/打开目标文件夹/删除 全线哑火(单种子菜单传的是 `member.hash`,
    不受影响 —— "种子右键正常、剧/集右键失败"就是这形状)。故凡是"从集成员取 hash"的地方
    一律走 `memberHashesOf`(两形态都收), 这里只做静态拦截。
    """
    lines = text.splitlines()
    for i, line in enumerate(lines, 1):
        if not _EP_MEMBERS_RE.search(line):
            continue
        wants_hash = "hashes" in line or ".hash" in line or "for (const h of" in line
        if wants_hash and "memberHashesOf(" not in line:
            problems.append(
                f"{rel}:{i} 集成员取 hash 未走 memberHashesOf"
                "(members 在前端已是对象 -> 传出去会变成 [object Object], 后端 404「种子不存在」)"
            )


def _scan_state_rank(text, rel, problems):
    """状态优先级表守阵: 前端 `STATE_RANK` 必须与后端 `_SHOW_STATE_RANK` 逐项一致(2026-09-19)

    两表是**同一概念**("一组/一集种子该显示成什么状态")的两份实现:
    前端那份决定辅种页组行取哪个成员状态着色(`decoratedGroups.status.primary`),
    后端那份决定追剧页集行的 `e.state`。漂移的后果有两层 ——
    1. 同一批种子在辅种页与追剧页显示成**不同颜色**(用户没法解释, 只会觉得"颜色乱");
    2. 乐观 UI: 前端按自己的表算出"点击后的颜色", 下一轮回执却按后端的表算真值 ⇒ 颜色弹回。
    实测曾漂移两处({downloading,checking} 与 {paused,seeding} 两组取值相反), 人眼不可能发现,
    故机械比对(改一边必须改另一边 —— 这正是本守阵要逼出来的动作)。

    表外兜底秩(2026-10-15, issue 26-10-11-0310): 表里没有的 kind 排最后, 前端
    `STATE_RANK_LAST` ↔ 后端 `_SHOW_STATE_RANK_LAST` 也必须同值 —— 它俩管的是同一件事
    ("未知状态排多后"), 漂移的后果是某页把未知状态排到了已知状态中间。
    """
    from auto_qb.webui.views import _SHOW_STATE_RANK, _SHOW_STATE_RANK_LAST

    m = re.search(r"const STATE_RANK = \{([^}]*)\}", text)
    if not m:
        problems.append(f"{rel} 找不到 `const STATE_RANK = {{...}}`(状态优先级单点表, 见 isPending 一带注释)")
        return
    front = {k: int(v) for k, v in re.findall(r"(\w+)\s*:\s*(\d+)", m.group(1))}
    if front != _SHOW_STATE_RANK:
        problems.append(
            f"{rel} STATE_RANK 与后端 _SHOW_STATE_RANK 不一致"
            f"(前端 {front} / 后端 {_SHOW_STATE_RANK}) —— 同一批种子会在辅种页与追剧页显示成不同颜色"
        )
    m_last = re.search(r"const STATE_RANK_LAST = (\d+)", text)
    if not m_last:
        problems.append(f"{rel} 找不到 `const STATE_RANK_LAST = <n>`(表外 kind 兜底秩单点, 见 decorate.js rankKind)")
    elif int(m_last.group(1)) != _SHOW_STATE_RANK_LAST:
        problems.append(
            f"{rel} STATE_RANK_LAST({m_last.group(1)}) 与后端 _SHOW_STATE_RANK_LAST"
            f"({_SHOW_STATE_RANK_LAST})不一致 —— 未知 kind 的兜底排序两页不同(某页会把未知状态排进已知状态中间)"
        )
    # 顺序语义(2026-09-21): 做种必须排在**暂停之前** —— 组内"部分暂停部分做种中"取**做种色**。
    # 上面的逐项比对只能保证"两页同色", 保证不了"同成哪个色": 2026-09-19 的 BUG-7 把前端表整体
    # 对齐后端时, 顺手把 {paused,seeding} 也翻成 paused ⇒ 辅种页做种中的组整行变灰(用户报
    # "辅种页状态色错误, 以前是对的")。两表一起改才不会重蹈覆辙, 故此处单独钉住顺序。
    if front and front.get("seeding", _SHOW_STATE_RANK_LAST) >= front.get("paused", -1):
        problems.append(
            f"{rel} STATE_RANK 把 paused 排在 seeding 之前或同级(前端 {front}) —— "
            "组/集内\"部分暂停部分做种中\"会取暂停色(灰), 用户口径是取**做种色**(绿); "
            "见 app.js STATE_RANK 注释与 memory-bank/pitfalls.md"
        )


def _scan_keys_serial_re(text, rel, problems):
    """键位归一化正则跨层守阵: 后端 `_KEYS_SERIAL_RE` ↔ 前端 `KB_DEF_RE` 逐字同源(2026-10-15, issue 26-10-11-0310)

    两端各一份是刻意的: 前端录制/保存自定义键位时要能在无往返时判形态(shortcuts.js),
    后端读 webui-keys.json 时要能校验(routes/keys.py)。但两边正则只要差一个字符,
    症状就是**单边静默**: 前端放行的串后端 422(自定义键位存不进去), 或后端放行的串
    前端判非法(录完即被丢弃) —— 不报错, 只是"键位莫名其妙存不上/失效"。
    故逐字比对两侧正则源(JS 字面量剥定界符后与 Python pattern 比); "找不到声明"同样报红
    (判据被改名/搬走后不许空转, 见 pitfall guard-dead-branch)。
    """
    from auto_qb.webui.server.routes.keys import _KEYS_SERIAL_RE

    m = re.search(r"const KB_DEF_RE = /([^/\n]+)/;", text)
    if not m:
        problems.append(f"{rel} 找不到 `const KB_DEF_RE = /.../`(键位归一化正则单点被改名/删除? 见 routes/keys.py::_KEYS_SERIAL_RE)")
        return
    js_src = m.group(1)
    if js_src != _KEYS_SERIAL_RE.pattern:
        problems.append(
            f"{rel} KB_DEF_RE 与后端 _KEYS_SERIAL_RE 不一致"
            f"(JS /{js_src}/ vs Python {_KEYS_SERIAL_RE.pattern!r}) —— "
            "前端放行的键位形态后端可能拒收(422), 或反向(录完即被前端判非法丢弃)"
        )


def _scan_eta_sentinel(problems):
    """ETA 哨兵跨层守阵: 后端 `_ETA_SENTINEL` ↔ 前端全部 `sec/eta >= <数>` 比较点同值(2026-10-15, issue 26-10-11-0310)

    同一事实(qB 协议"无 ETA"哨兵)有多处表示: 后端 views.py `_ETA_SENTINEL` 定聚合口径
    (`_min_valid_eta` 只收 0<eta<哨兵), 前端 format.js `fmtEta` 与模板 `zero:` 类判据定
    显示口径(>= 哨兵即空白/弱化)。任何一边改值另一边没跟, 症状是**静默**的: 后端已不把
    某个 eta 当哨兵而前端还显示空白(或反向) —— 无报错, 只是"该有 ETA 的地方恒空"。
    故按全静态树(.js/.html, 除 vendor)抓比较点逐个比对; **零命中即红** —— "没扫到"必须
    与"没违规"可区分(判据被改名/删光时守阵不许空转, 见 pitfall guard-dead-branch)。
    """
    from auto_qb.webui.views import _ETA_SENTINEL

    hits = []
    for dirpath, _dirs, files in os.walk(STATIC_ROOT):
        for name in sorted(files):
            if not name.endswith((".js", ".html")):
                continue
            path = os.path.join(dirpath, name)
            rel = os.path.relpath(path, STATIC_ROOT).replace(os.sep, "/")
            if "/vendor/" in f"/{rel}":
                continue
            with open(path, encoding="utf-8") as f:
                for i, line in enumerate(f.read().splitlines(), 1):
                    for m in re.finditer(r"\b(?:sec|eta) >= (\d+)", line):
                        hits.append((rel, i, int(m.group(1))))
    if not hits:
        problems.append("静态树找不到任何 `sec/eta >= <数>` 哨兵比较点(fmtEta / 模板 zero 判据被改名或删除? 见 views._ETA_SENTINEL)")
        return
    for rel, i, v in hits:
        if v != _ETA_SENTINEL:
            problems.append(
                f"{rel}:{i} ETA 哨兵 {v} 与后端 _ETA_SENTINEL({_ETA_SENTINEL})不一致 —— "
                "前端空白/弱化判据与后端聚合口径分家(该显示 ETA 的行恒空, 或哨兵值被当成真 ETA 计时)"
            )


def _scan_pending_settle(text, rel, problems):
    """乐观 UI「撤下」守阵(2026-09-19, 与主线 32f531d / 12657ee 同一族缺陷的第二道锁)

    背景: 「点击 → 行恢复正常」曾实测 3785~5178ms, 根因是 pending 只有 3s 常量兜底一个出口 ——
    systemPatterns 明写的「真值匹配即清」**从未实现过**; 而且这个兜底还只在 refresh() 里被顺带
    求值 ⇒ 撤下 = 3000ms + 等到下一次 /api/state。真机连报三次同一现象, 前三次修复全只动"贴上",
    因为没人量过"撤下"。

    主线修法落地后有两处**极易被改回去/写反**的地方, 本守阵逐条钉住:
      1. `_snapshotTruth(state)` 必须在 `reapplyPending()` **之前** —— 快照要的是服务端原始值;
         挪到之后就变成"行上的补丁值 vs 补丁值", 恒真 ⇒ pending 一瞬间就清(实测 28ms),
         而且冒烟里「落回的是真值」那条**照样 PASS**(补丁值还留在行上, 看着就像真值)。
      2. 判定必须走 `_optimisticSettled`(比真值快照)而不是"拿行上的当前值比" —— 同上。

    !2026-09-21 P3 后1.2.**仍然保留, 且必须保留**: 真值现在主要由 `truth` 事件(SSE)推送,
      但 **SSE 断线期间推的事件会丢**; 这时 `_optimisticSettled` 是唯一的安全网 —— 轮询带回的
      `/api/state` 一旦已经含真值就提前收工, 不用干等到 TRUTH_HOLD_MS(8s)超时回滚。
      没有它, SSE 一断就会出现"命令其实成功了, 8 秒后却回滚"的假失败。
    !已删除的旧机制(勿复活): `_settleFromTruth`(回执带真值就地撤下)、
      `_pullTruthAfterCmd`(回执后拉全量, 1500ms 预算) —— 真值改由事件推送后它们成了死代码。
    """
    i_snap = text.find("this._snapshotTruth(state)")
    i_reap = text.find("this.reapplyPending()")
    if i_snap < 0:
        problems.append(f"{rel} 找不到 `this._snapshotTruth(state)` —— 判「真值是否对齐」没有服务端原始值可比")
    elif i_reap >= 0 and i_snap > i_reap:
        problems.append(
            f"{rel} _snapshotTruth 写在 reapplyPending **之后** —— 快照到的是被补丁改过的行值,"
            "判定恒真 ⇒ pending 立刻清、失败路径留假状态(红线)"
        )
    if "this._optimisticSettled(" not in text:
        problems.append(
            f"{rel} 找不到 _optimisticSettled 的调用点 —— 它是 **SSE 断线时的安全网**: 没有它,"
            "推送丢失就只能干等 TRUTH_HOLD_MS 超时回滚(命令其实成功 ⇒ 假失败)"
        )
    # 反向守阵: 已删的机制不许复活(它们是真值改推送后遗留的死代码)
    for dead in ("_settleFromTruth", "_pullTruthAfterCmd"):
        if dead in text:
            problems.append(f"{rel} 残留已删机制 {dead} —— 真值已改由 truth 事件推送, 它只会拖慢撤下")


def _computed_body(text, name):
    """取 computed 成员 `<name>() { ... }` 的函数体(按缩进配平到同缩进或更浅的 `},`/`}`)

    只做"这段实现里有没有出现某个调用"这类**存在性**判定(见 _scan_filter_facets),
    故不需要真解析: 从定义行开始收集, 遇到缩进不大于定义行的 `}` 即停。
    """
    m = re.search(rf"^\s*{name}\(\)\s*\{{", text, re.M)
    if not m:
        return None
    indent = len(m.group(0)) - len(m.group(0).lstrip())
    out = []
    for line in text[m.end():].splitlines():
        if line.strip() in ("}", "},") and len(line) - len(line.lstrip()) <= indent:
            break
        out.append(line)
    return "\n".join(out)


def _strip_js_comments(text):
    """去掉 JS 的块注释与行注释 —— 供**存在性**守阵使用, 避免被注释骗过

    !这是本项目踩过的坑(memory-bank/testing.md 列偏好守阵那条): 只查"字符串出现了没有",
    注释里正写着那个名字 ⇒ 真被注释掉的代码照样判过。故存在性判定一律先剥注释。
    行注释只认"前面不是冒号"的 `//`(避开 `https://` 这类字面量), 不做完整词法分析 ——
    本函数只服务"某标识符在这段实现里有没有被调用", 不需要精确到字符串内部。
    """
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    out = []
    for line in text.splitlines():
        m = re.search(r"(?<!:)//", line)
        out.append(line[:m.start()] if m else line)
    return "\n".join(out)


def _scan_filter_facets(text, rel, problems):
    """筛选器选项"取数面"守阵(2026-09-21, 用户报「种子页筛选器无数据」)

    选项必须走**单点取数面** `facetRows`(filters.js): 组视图/追剧视图按组(计数=含该值的组数),
    种子页按种子(计数=含该值的种子数)。四个筛选器(标签/分类/站点/路径)原先各自遍历 `groups`
    计算, 而种子页按视图分片**不回 groups**(`VIEW_ARRAYS["torrent"] = ("torrents",)`) ⇒
    四个弹层恒空、只剩"暂无数据"(H&R 是固定两档, 表现为 0/0 —— 更隐蔽)。
    这类"跨视图的常驻消费者去依赖按视图裁剪的阵列"本项目**已犯三次**:
    状态栏速度(issue 26-09-20-1646) / 追剧页成员索引(BUG-8) / 本次筛选器,
    故机械钉住: 每个选项 computed 必须出现单点调用, 且按组算的旧实现不得复活。
    """
    text = _strip_js_comments(text)  # 注释里出现这些名字不算数(见 _strip_js_comments)
    if not re.search(r"^\s*facetRows\(\)\s*\{", text, re.M):
        problems.append(f"{rel} 找不到 facetRows() —— 筛选器选项的取数面单点(见 filters.js 注释)")
    for name in ("tagOptions", "categoryOptions", "siteOptions", "pathOptions"):
        body = _computed_body(text, name)
        if body is None:
            problems.append(f"{rel} 找不到 computed.{name}(改名前请同步本守阵)")
        elif "_facetOptions(" not in body:
            problems.append(
                f"{rel} computed.{name} 没走 _facetOptions 单点 —— 各自遍历集合会在种子页"
                "(按视图分片不回 groups)算出空选项, 弹层只剩\"暂无数据\""
            )
    for name in ("hrOptions", "hrSrcOptions"):
        body = _computed_body(text, name)
        if body is not None and "facetRows" not in body:
            problems.append(f"{rel} computed.{name} 没走 facetRows 单点 —— 种子页不回 groups ⇒ H&R 档位恒 0/0")
    if "_memberValueOptions" in text:
        problems.append(f"{rel} 残留 _memberValueOptions —— 选项一律走 facetRows/_facetOptions 单点"
                        "(按组算的第二条口径正是本次故障的成因)")


# 挂件级类名白名单 —— 只盯这些; 组件层类名(`.ico` / `.row` / `.cell` 等)不进, 否则满屏误报。
# 添加新挂件类时请同步这里。
_PAGE_HOOK_CLASSES = ("hub-page", "ce-page", "layout")


def _scan_page_class_wiring(problems):
    """挂件类名配对: HTML 的 `<main class="X ...">` 里出现的挂件类名必须在 CSS 里有规则

    现象(2026-09-21, 用户报"输入框缺发光 + 排版竖着"):
    CSS 里 `.hb-page`(前缀化时手滑)定义 `--tone` 等, 而 HTML 上是 `class="ce-page hub-page"` ——
    `.hb-page` 选择器**永远不命中**任何元素 ⇒ `--tone` 从未定义 ⇒ 所有 `var(--tone)` 派生值
    替换时判为无效 ⇒ 描边回退、发光整条消失、等宽字体也不生效(剩下字体 fallback)。
    静悄悄地废掉一整块视觉,**没有运行时报错**, 靠真浏览器量 computedStyle 才看得出来。

    为防止再犯: 每张 index.html 的 `<main class="...">` 里出现的挂件类名, 都必须能在某份
    CSS(shared/* 或同目录的 *.css)里找到对应的选择器规则。
    """
    css_text = ""
    for dirpath, _dirs, files in os.walk(STATIC_ROOT):
        for name in sorted(files):
            if not name.endswith(".css"):
                continue
            if "/vendor/" in f"/{dirpath}/{name}":
                continue
            css_text += open(os.path.join(dirpath, name), encoding="utf-8").read() + "\n"
    selectors = set(re.findall(r"^\s*\.([A-Za-z_][\w-]*)\s*[\{,]", css_text, re.M))
    for dirpath, _dirs, files in os.walk(STATIC_ROOT):
        for name in sorted(files):
            if not name.endswith(".html"):
                continue
            rel = os.path.relpath(os.path.join(dirpath, name), STATIC_ROOT).replace(os.sep, "/")
            if "/vendor/" in f"/{rel}":
                continue
            text = open(os.path.join(dirpath, name), encoding="utf-8").read()
            for m in re.finditer(r"<\s*main\b[^>]*\bclass=\"([^\"]+)\"", text):
                for cls in m.group(1).split():
                    if cls not in _PAGE_HOOK_CLASSES:
                        continue
                    if cls not in selectors:
                        problems.append(
                            f"{rel} `<main class=\"...{cls}...\">` 在所有 CSS 里都找不到 `{cls}` "
                            f"的选择器规则 —— 该挂件类上的令牌/变量定义永不生效, 派生样式全部失效"
                            f"(参考 2026-09-21 把 .hb-page 错写成 .hub-page 之外的类名, 整页无发光)"
                        )


# PERF-01(2026-09-24): 这两类元素**不许**再挂 backdrop-filter —— 它们要么是全屏遮罩, 要么是
# 常驻吸顶/吸底条, 都处在别的遮罩的 backdrop 里; 一旦两块毛玻璃叠在一起, Chromium 每帧都要
# 回读并重复模糊整个视口(星图"点状态栏历史流量卡顿"的实测根因)。
# 注: 抽屉遮罩 `.drawer-mask` 不在此列 —— 它是**当时唯一在用的**遮罩, 底下已无第二块毛玻璃,
# 两套 UI 同款且棱镜侧实测无卡顿; 一并摘掉会单边改动棱镜外观, 超出本次范围(见 scope-guard)。
_PERF_BACKDROP_BANNED = ("modal-mask", "topbar", "status-strip", "statusbar", "ce-actions")


def _scan_backdrop_filter(problems):
    """毛玻璃守阵: 全屏遮罩 / 吸顶吸底条不得带 backdrop-filter, 且星图与棱镜的数量必须对齐

    现象(2026-09-24, 用户报"星图卡顿, 点状态栏历史流量尤其明显; 棱镜无此问题"):
    星图 atlas/style.css 一度挂了 5 处 backdrop-filter —— 顶栏 blur(12px) / 状态分布条 blur(10px) /
    弹层遮罩 blur(3px) / 配置页吸底条 blur(10px) / 抽屉遮罩 blur(2px); 棱镜侧只有抽屉遮罩一处。
    点开"历史流量"时, .modal-mask(全屏 fixed + blur)的 backdrop 里正压着顶栏与状态分布条这两块
    毛玻璃 —— **嵌套毛玻璃**迫使每帧回读 + 重复模糊整个视口, 而弹层内的 hist-draw 描边动画
    还在主线程逐帧重绘, 两者叠成肉眼可见的卡顿。棱镜 .modal-mask 从来没加过 backdrop-filter,
    所以无此症状。

    两层断言(缺一不可):
    1.**位置**: 上述六类元素一律不许出现 backdrop-filter(不论哪套 UI、哪份 CSS);
    2.**数量**: 各套 UI 自己的声明数必须相等 —— 防"只在某一侧加回来"这类单边改动
      (shared/console_hub.css 是共用层, 各边同担, 不计入各自计数)。
    扫描前先剥 `/* ... */`, 否则本文件里解释这段历史的注释会被当成真实声明(实测会误报)。
    """
    counts = {ui: 0 for ui in _UI_ALL}
    for dirpath, _dirs, files in os.walk(STATIC_ROOT):
        for name in sorted(files):
            if not name.endswith(".css") or "/vendor/" in f"/{dirpath}/{name}":
                continue
            path = os.path.join(dirpath, name)
            rel = os.path.relpath(path, STATIC_ROOT).replace(os.sep, "/")
            text = re.sub(r"/\*.*?\*/", "", open(path, encoding="utf-8").read(), flags=re.S)
            sel = ""
            for line in text.splitlines():
                if "{" in line:
                    sel = (sel + " " + line.split("{", 1)[0]).strip()
                if re.search(r"backdrop-filter\s*:", line):
                    for ui in _UI_ALL:
                        if rel.startswith(ui + "/"):
                            counts[ui] += 1
                    for bad in _PERF_BACKDROP_BANNED:
                        if re.search(r"\.%s\b" % re.escape(bad), sel):
                            problems.append(
                                f"{rel} `{sel or '(未识别选择器)'}` 上出现 backdrop-filter —— "
                                f"{bad} 是全屏遮罩或常驻吸顶/吸底条, 加毛玻璃会与弹层遮罩叠成嵌套模糊"
                                f"(每帧回读 + 重复模糊整个视口; 星图 2026-09-24 卡顿根因, 见 PERF-01)"
                            )
                if "}" in line:
                    sel = ""
    if len(set(counts.values())) != 1:
        problems.append(
            f"各套 UI 的 backdrop-filter 声明数不对齐: "
            f"{' / '.join(f'{ui} {n} 处' for ui, n in counts.items())} —— "
            f"单边加毛玻璃会重新引入嵌套模糊卡顿(遮罩类从不带 backdrop-filter, 见 PERF-01)"
        )


def _extract_column_keys(app_js: str, const_name: str):
    """从 app.js 提取列模型数组的 key 清单(缺该数组返回 None —— 列模型被改名/搬走的信号)"""
    m = re.search(r"const %s = \[(.*?)\n\];" % const_name, app_js, re.S)
    if not m:
        return None
    return re.findall(r'key: "(\w+)"', m.group(1))


def _scan_column_cells_paired(problems):
    """列模型每个列 key 必须在对应行模型渲染器里有值单元格分支(辅种扩列 2026-09-28 守阵; P2/P3 改扫渲染器)

    列模型(TABLE_COLUMNS)是表头/grid 模板/列选择器的单一来源 —— 但**值单元格**是渲染器里的
    v-if/v-else-if 分支, 漏写某列的分支时没有任何报错: 表头照常渲染、列选择器照常可勾,
    值格却永远空白, 且无法从"pytest 全绿"察觉。

    !值单元格自计划 26-10-11-1722 P2/P3 起**不再是页面模板里的内联副本**:
      · group / torrent / show-ep 三类收敛为**每行模型单份**渲染器
        (<aq-group-cells> / <aq-torrent-cells> / <aq-show-cells> / <aq-ep-cells>,
         模板在 shared/tpl/xtpl-cells.html);
      · 明细成员单元格(member)在 P2 已收敛为 <aq-member-cells>(模板在 shared/tpl/xtpl.html)。
    故改为扫渲染器所在分片, 并额外钉住"注册为全局组件 + 页面调用点都走它"—— 漏一处即退回内联副本
    (静默回潮)。"删一个渲染器分支必须报红"的语义不变, 只是红点从页面模板挪到渲染器。
    另钉住默认隐藏策略单点(2026-10-12 issue 26-10-12-1911 收口): loadColState 必须消费
    DEFAULT_HIDDEN_KEYS(漏消费 = 默认隐藏列全部默认可见), 且列定义不得再写 hide:true
    (回潮即三表口径再漂移)。
    """
    app_js = open(os.path.join(STATIC_ROOT, "shared", "app.js"), encoding="utf-8").read()
    plans = (
        ("GROUP_COLUMNS", "tpl/xtpl-cells.html"),  # 单份渲染器 <aq-group-cells>(P3)
        ("DETAIL_COLUMNS", "tpl/xtpl.html"),  # 单份渲染器 <aq-member-cells>(P2)
        ("TORRENT_COLUMNS", "tpl/xtpl-cells.html"),  # 单份渲染器 <aq-torrent-cells>(P3)
        ("SHOW_COLUMNS", "tpl/xtpl-cells.html"),  # 单份渲染器 <aq-show-cells>/<aq-ep-cells>(P3)
    )
    for const, tpl in plans:
        keys = _extract_column_keys(app_js, const)
        if keys is None:
            problems.append(f"app.js 缺少列模型 {const}(列模型单一来源被改名/搬走?)")
            continue
        text = open(os.path.join(STATIC_ROOT, "shared", tpl), encoding="utf-8").read()
        for k in keys:
            if f"col.key === '{k}'" not in text:
                problems.append(f"{const} 列 {k} 在 shared/{tpl} 没有值单元格分支(col.key === '{k}') —— 表头在、值永远空白")
    # 行模型渲染器的接线单点(注册 + 页面调用点): 漏注册 = 该页整块渲染不出来; 漏调用 = 退回内联副本
    renderers = (
        ("aq-member-cells", "AQ_MEMBER_CELLS_COMPONENT", ("tpl/groups.html", "tpl/shows.html")),
        ("aq-group-cells", "AQ_GROUP_CELLS_COMPONENT", ("tpl/groups.html", )),
        ("aq-torrent-cells", "AQ_TORRENT_CELLS_COMPONENT", ("tpl/torrents.html", )),
        ("aq-show-cells", "AQ_SHOW_CELLS_COMPONENT", ("tpl/shows.html", )),
        ("aq-ep-cells", "AQ_EP_CELLS_COMPONENT", ("tpl/shows.html", )),
    )
    for name, glob, tpls in renderers:
        if not re.search(r'app\.component\(\s*"%s"\s*,\s*window\.%s\s*\)' % (name, glob), app_js):
            problems.append(f"app.js 未注册 {name}(window.{glob}) —— 行模型渲染器没接线, 该页值格全空")
        for tpl in tpls:
            text = open(os.path.join(STATIC_ROOT, "shared", tpl), encoding="utf-8").read()
            if f"<{name}" not in text:
                problems.append(f"shared/{tpl} 未使用 <{name}> —— 行模型渲染器收敛回潮"
                                "(该页退回内联副本, 改一处漏一处)")
    if "DEFAULT_HIDDEN_KEYS" not in app_js or "DEFAULT_HIDDEN_KEYS.has(c.key)" not in app_js:
        problems.append("app.js loadColState 未消费默认隐藏单点 DEFAULT_HIDDEN_KEYS(默认隐藏列全部可见)")
    if "hide: true" in app_js:
        problems.append("app.js 列定义又见 hide:true —— 默认隐藏策略只应写在 DEFAULT_HIDDEN_KEYS 单点(issue 26-10-12-1911)")


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
    # atlas 落 views.css 而非 components.css: 后者顶 700 行 cap(views.css 首注有约定); console/prism
    # 各按 .h-cell.sortable 现有落点。
    for ui, rel in (("atlas", "views.css"), ("console", "components.css"), ("prism", "views.css")):
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
    cols = open(os.path.join(STATIC_ROOT, "shared", "columns.js"), encoding="utf-8").read()
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
    assert "$root.sortedDrawer(" in btpl, "桥行序必须走 sortedDrawer 单点(dyn 分支) —— 手拼即第二份排序机"
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
    col = read("columns.js")
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

    # ⑫ 三份 index.html: stub 装载行各 1 条
    for skin in ("atlas", "console", "prism"):
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

    for skin in ("atlas", "console", "prism"):
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


def test_drawer_tpl_variant_interaction_single_point():
    """变体交互单点定型守阵(计划 26-10-12-0527 U5①)。

    判据**按声明识别(声明即受检)**: drawer_tpl/*.js 全目录扫 ui.sort —— 手搓排序状态机
    (ui.sortKey/ui.sortDir)不允许在任何变体复活; 凡声明 tableId+rowsFn(桥表格变体)的文件
    另强制零表格容器列宽 grid —— 列宽唯一来源 = 引擎列集(columns.js computed), 变体 CSS
    不得对表格容器(.group-head/.group-row/旧手搓容器命名族 .dtNN-h|r|head|row|gcols)写
    grid-template-columns。版式 grid(卡片栅格/双栏/图例, 含 04 的 .group-table 双列卡片栅格
    —— 卡片布局不是列宽, 等高由 test_drawer_tpl_trackers_card_uniform_height 另行钉住)是
    D5 保留面, 不在禁令内。未来新变体接引擎(tableId+rowsFn 落地)即自动落入本守阵,
    无需改守阵 —— 即「定型」之义; 已知八桥变体清单兜底(判据不得静默缩水)。
    """
    import os
    import re
    shared = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src", "auto_qb", "webui", "static", "shared"
    )
    tpl_dir = os.path.join(shared, "drawer_tpl")
    # 已知八桥变体兜底: 每个都必须被「声明即受检」识别到(识别失灵 = 判据空转)
    known_bridge = {
        "07-peers-dashboard-tall.js",
        "08-peers-groups-low.js",
        "09-peers-density-collapsed.js",
        "04-trackers-status-cards-tall.js",
        "05-trackers-health-groups-low.js",
        "06-trackers-table-collapsed.js",
        "10-content-tree-detail-tall.js",
        "11-content-treegrid-batch-low.js",
    }
    # 表格容器选择器族(⑪ 同口径): 引擎行/列头容器 + 旧手搓表格容器命名族(.dtNN-list 等版式
    # 类不在此族 —— 04 的 .group-table 卡片栅格与 07 的 .group-table 表壳栅格是 D5 保留面)
    colgrid_sel = re.compile(r"\.group-head|\.group-row|\.dt\d\d-(?:h|r|head|row|gcols)\b")

    seen_bridge = set()
    for fname in sorted(f for f in os.listdir(tpl_dir) if f.endswith(".js")):
        text = open(os.path.join(tpl_dir, fname), encoding="utf-8").read()
        # 全目录: 手搓排序状态机零残留(排序并引擎 D3, 任何变体不得复活)
        assert "ui.sort" not in text, f"{fname} 残留手搓排序状态机 ui.sort(U5 定型: 排序归引擎单点)"
        # 声明即受检: tableId+rowsFn 双声明 = 桥表格变体 → 列宽 grid 禁令生效
        if re.search(r"\btableId\s*:", text) and re.search(r"\browsFn\s*:", text):
            seen_bridge.add(fname)
            for ln in text.splitlines():
                if "grid-template-columns" in ln and colgrid_sel.search(ln):
                    raise AssertionError(f"{fname} 表格容器残留列宽 grid 硬编码(U5 定型 Q4: 列宽归引擎): {ln.strip()[:80]}")
    missing = known_bridge - seen_bridge
    assert not missing, f"已知桥变体未被「声明即受检」识别到(判据空转或声明丢失): {sorted(missing)}"


def _scan_progress_val_parity(problems):
    """进度条数值盒守阵: 三套皮肤的 `.m-progress .val` 都必须恰 1 条且带 min-width 定宽(2026-09-28)

    现象(用户报"种子页进度条长度不一致, 似乎受后面的进度文本长度影响"): `.m-progress` 是
    flex 行, `.bar { flex: 1 1 auto }` 吃剩余空间, `.val` 只占自身文本宽 —— 「100.0%」比
    「5.2%」宽, 同一列各行条的起点/长度随百分比文本宽度逐行漂移。处置 = 数值盒
    `min-width: 4em`(容纳最宽的「100.0%」, 三套皮肤字号 11.5-12px 下实测文本 ≈3.5em 以内)
    + `text-align: right`, 条长即与文本解耦; 本守阵防"只在某一侧加 / 新皮肤漏带"。
    """
    hits = {ui: 0 for ui in _UI_ALL}
    for dirpath, _dirs, files in os.walk(STATIC_ROOT):
        for name in sorted(files):
            if not name.endswith(".css") or "/vendor/" in f"/{dirpath}/{name}":
                continue
            path = os.path.join(dirpath, name)
            rel = os.path.relpath(path, STATIC_ROOT).replace(os.sep, "/")
            ui = next((u for u in _UI_ALL if rel.startswith(u + "/")), None)
            if ui is None:
                continue
            text = re.sub(r"/\*.*?\*/", "", open(path, encoding="utf-8").read(), flags=re.S)
            lines = text.splitlines()
            for idx, line in enumerate(lines):
                if not re.match(r"^\s*\.m-progress \.val\s*\{", line):
                    continue
                hits[ui] += 1
                body = line.split("{", 1)[1]
                j = idx
                while "}" not in body and j + 1 < len(lines):
                    j += 1
                    body += lines[j]
                if not re.search(r"min-width\s*:", body):
                    problems.append(f"{rel} `.m-progress .val` 缺 min-width 定宽 —— 条吃剩余空间, "
                                    "数值盒不定宽时条长随百分比文本宽度逐行漂移")
    for ui, n in hits.items():
        if n != 1:
            problems.append(f"{ui} 皮肤的 `.m-progress .val` 基础规则数 = {n}(应恰 1 条且带 min-width 定宽)")


def _scan_frontend_assets():
    """扫描 webui/static 返回问题清单(空 = 健康)

    检查项(均为"整页白屏 / 整块功能静默失效"级故障, 且 Python 侧测试天然看不见):
    1. 合并冲突标记残留(`<<<<<<<` / `>>>>>>>` / 单独一行 `=======`) —— 语法错误;
    2. JS 里"注释已闭合却仍留续行"(上一非空行以 `*/` 结尾, 本行又以 `*` 起头) ——
       整包 SyntaxError, app.js 不执行, Vue 从不 mount, `v-cloak` 的 #app 恒 display:none;
    3. JS 语法硬校验: 有 node 时单进程批量校验(语义同 `node --check`, 见 _scan_js_syntax_with_node);
    4. CSS 规则块漏闭合(浏览器会把其后规则整段当声明丢弃) —— 见 _scan_css_blocks;
    5. 模板 `<transition>` 不配对 / 把弹窗包进 `<transition>`(只渲染首子节点 -> 弹窗全丢);
    6. 模板/样式里以 `/` 开头的 src|href 引用, 在 static 根下必须真实存在(防改名/漏档 404);
    7. 追剧视图"集成员 -> hash"必须走 `memberHashesOf`(见 _scan_episode_member_hashes);
    8. `STATE_RANK` 必须与后端 `_SHOW_STATE_RANK` 逐项一致(见 _scan_state_rank) ——
       两表分别决定"辅种页组行"与"追剧页集行"的颜色, 漂移的后果是同一批种子两页不同色;
       该项同时钉住**顺序语义**: seeding 必须排在 paused 之前(混合态取做种色, 2026-09-21 用户口径);
    9. 乐观 UI 的**撤下**路径: 真值快照必须早于补丁重贴、判定必须走 `_optimisticSettled`、
       回执后必须调 `_pullTruthAfterCmd`(见 _scan_pending_settle) —— 任一被绕过, 撤下就退回
       3s 常量兜底(真机连报三次的那条), 或判定恒真导致失败路径留假状态(红线)。
    10. 拆分接线: 片段文件必须被 HTML 引用 + 被 app.js `app.mixin()` 注入, 且成员不得重名
       (见 _scan_mixin_wiring) —— 漏挂/漏注入 = 整块功能静默消失, 重名 = 被覆盖者永不执行。

    11. 筛选器选项必须走 `facetRows` 单点取数面(见 _scan_filter_facets) —— 各自遍历 `groups`
       会在种子页(按视图分片不回数组)算出空选项, 弹层只剩"暂无数据"。
    12. 页面"挂件类名"必须配对存在 CSS 规则: HTML 的 `<main class="...hub-page...">` / `ce-page` /
       `layout` 这类挂件类名, 都必须在对应 CSS(shared/console_hub.css / prism/views.css /
       atlas/style.css)里有规则, 否则**整段页面没样式**(实测: 把 `.hub-page` 错写成 `.hb-page`
       后 `--tone` 从未定义, 所有 `var(--tone)` 派生的描边/发光/语义色全部失效, 还以为"页面正常"
       只是"缺发光"; 真浏览器量 computedStyle 才看得出来)。
       (见 _scan_page_class_wiring)

    13. 毛玻璃(backdrop-filter)不得挂在全屏遮罩 / 吸顶吸底条上, 且星图与棱镜的声明数必须相等
       (见 _scan_backdrop_filter) —— 嵌套毛玻璃会让"点状态栏历史流量"这类开弹层的动作明显卡顿,
       且**只在星图侧复现**(棱镜 .modal-mask 从不带 backdrop-filter), 属于"两边都能跑、一边更卡"
       的差异, 肉眼走查看不出来, 只能靠计数兜底。

    14. 列模型每个列 key 必须在对应模板有值单元格分支(见 _scan_column_cells_paired) ——
       模板漏写分支无任何报错(表头在、列选择器可勾、值永远空白); 明细列两份模板
       (groups.html/shows.html)必须成对; loadColState 必须消费 DEFAULT_HIDDEN_KEYS 单点
       (默认隐藏列注入单点, 列定义禁止再写 hide:true)。

    15. CSS 注释体内不得出现 `*/`(见 _scan_css_comments) —— 注释被提前终止后, 尾巴落成
       代码态垃圾, 浏览器按错误恢复把紧跟的规则整条静默丢弃(2026-09-28 实测: console 皮肤
       进度条注释 `(s-*/member-row 族)` 吞掉 `.m-progress { display: flex }`, 三处表格
       进度条只剩百分比没有条)。

    16. 三套皮肤的 `.m-progress .val` 基础规则必须恰 1 条且带 min-width 定宽(见
       _scan_progress_val_parity) —— 条吃剩余空间, 数值盒不定宽时进度条长度随百分比
       文本宽度逐行漂移(2026-09-28 实测: 「100.0%」的行比「5.2%」的行条短)。

    17. ETA 哨兵跨层一致(见 _scan_eta_sentinel, 2026-10-15 issue 26-10-11-0310):
       后端 `_ETA_SENTINEL` ↔ 全静态树每一处 `sec/eta >= <数>` 比较点(format.js fmtEta
       + 模板 zero 判据)必须同值 —— 聚合口径与显示口径分家是静默故障(该有 ETA 的行恒空);
       零命中即红(判据被改名/删光不许空转)。

    18. 键位归一化正则跨层一致(见 _scan_keys_serial_re, 2026-10-15 issue 26-10-11-0310):
       后端 `_KEYS_SERIAL_RE` ↔ 前端 `KB_DEF_RE` 逐字同源 —— 差一个字符就是单边静默
       (前端放的串后端 422 / 后端放的串前端录完即丢弃)。


    WARN: 7/8/9/11/18 五项按 **app.js 整包**(HTML 加载顺序拼接 app.js + 各片段)扫描, 不按单文件 ——
      拆分后同一条不变量的代码可能分处两个文件, 只看一个文件必然漏(2026-09-20 实测);
      17 按**全静态树**(含模板分片, 哨兵比较点在 tpl 里也有)扫描, 同样不按单文件。
    """
    problems = []
    js_files = []
    for dirpath, _dirs, files in os.walk(STATIC_ROOT):
        for name in sorted(files):
            path = os.path.join(dirpath, name)
            rel = os.path.relpath(path, STATIC_ROOT).replace(os.sep, "/")
            if not name.endswith((".js", ".css", ".html")):
                continue
            with open(path, encoding="utf-8") as f:
                lines = f.read().splitlines()
            for i, line in enumerate(lines, 1):
                if line.startswith(("<<<<<<<", ">>>>>>>")) or line == "=======":
                    problems.append(f"{rel}:{i} 合并冲突标记残留")
            # 只扫自家前端(vendor 为第三方压缩产物, 不适用本仓库注释/结构规范)
            if "/vendor/" not in f"/{rel}":
                if name.endswith(".js"):
                    js_files.append((path, rel))
                    for i, line in enumerate(lines):
                        if not re.match(r"^\s*\*(?!/)", line):
                            continue
                        prev = next((l for l in reversed(lines[:i]) if l.strip()), "")
                        if prev.rstrip().endswith("*/"):
                            problems.append(f"{rel}:{i + 1} 注释块已闭合后仍有续行(会造成整包 SyntaxError)")
                elif name.endswith(".css"):
                    _scan_css_blocks(path, rel, problems)
                    _scan_css_comments(path, rel, problems)
                elif name.endswith(".html"):
                    _scan_template_transitions(path, rel, problems)
            for ref in re.findall(r'(?:src|href)="(/[^"]+)"', "\n".join(lines)):
                if not os.path.exists(os.path.join(STATIC_ROOT, ref.lstrip("/"))):
                    problems.append(f"{rel} 引用不存在的静态资源 {ref}")
    _scan_js_syntax_with_node(js_files, problems)
    # app.js 已按域拆分(2026-09-20): 跨文件不变量按**整包**(HTML 加载顺序拼接)扫描 ——
    # 只看 app.js 会把搬进片段的那半漏掉, 只看片段又拿不到 app.js 里的表格常量与 refresh 主链。
    bundle = _app_bundle_files()
    bundle_text = "\n".join(open(p, encoding="utf-8").read() for p, _r in bundle)
    rel = "shared/app.js(整包 %d 个文件)" % len(bundle)
    _scan_episode_member_hashes(bundle_text, rel, problems)
    _scan_state_rank(bundle_text, rel, problems)
    _scan_keys_serial_re(bundle_text, rel, problems)
    _scan_eta_sentinel(problems)
    _scan_pending_settle(bundle_text, rel, problems)
    _scan_filter_facets(bundle_text, rel, problems)
    _scan_mixin_wiring(problems)
    _scan_page_class_wiring(problems)
    _scan_backdrop_filter(problems)
    _scan_column_cells_paired(problems)
    _scan_progress_val_parity(problems)
    return problems


def test_frontend_static_bundle_health():
    """前端静态资源守阵: 冲突残留/注释孤儿续行/node 语法校验/CSS 漏闭合/transition 吞弹窗/引用缺失/集成员取 hash/状态优先级表/列单元格配对

    三个实测故障(2026-09-17)都是"pytest 全绿但界面废掉"的形态:
    1. app.js 注释续行留在已闭合的 `*/` 之后 -> 整包 SyntaxError -> Vue 不 mount -> 只剩背景色;
    2. prism views.css 一条规则漏 `; }` -> 其后约 200 条规则被浏览器丢弃 -> 棱镜大半样式消失;
    3. 抽屉外层 `<transition>` 未闭合 -> 统计/限速/添加/确认框被 Transition 丢弃(点了没反应且无报错)。
    装了 node 的机器还会在此跑 `node --check` 对所有前端 JS 做真语法校验(无 node 则静默跳过)。
    """
    problems = _scan_frontend_assets()
    assert not problems, "前端静态资源问题: " + "; ".join(problems)


def _scan_ui_diff_registry(problems):
    """收集 shared/tpl 里的 UI 差异口(`v-if="ui === ...'"`) —— 「活差异清单」的机械面

    收敛定案(plans/26-09-26-2233 W3): 单一语义模板后, 模板级 UI 差异只允许写成
    `<template v-if="ui === 'atlas'|'prism'">` 条件块, 且块前必须带 `ui-diff:` 注释说明原因;
    新增差异走这个口, **不许另开分片副本**(双模板副本的复发形态就是绕开这个口私拷一份)。
    """
    registry = []
    shared_dir = os.path.join(STATIC_ROOT, "shared", "tpl")
    if not os.path.isdir(shared_dir):
        problems.append("缺 shared/tpl 单一语义分片目录(模板分裂回潮?)")
        return registry
    for name in sorted(os.listdir(shared_dir)):
        if not name.endswith(".html"):
            continue
        lines = open(os.path.join(shared_dir, name), encoding="utf-8").read().split("\n")
        for i, ln in enumerate(lines):
            m = re.search(r"v-if=\"ui\s*===\s*'(\w+)'\"", ln)
            if not m:
                continue
            side = m.group(1)
            if side not in _UI_ALL:
                problems.append(f"shared/tpl/{name}:{i + 1} UI 条件取值非法: {side!r}(只认 {'|'.join(_UI_ALL)})")
            if "ui-diff:" not in "\n".join(lines[max(0, i - 3):i + 1]):
                problems.append(f"shared/tpl/{name}:{i + 1} ui 条件块缺 `ui-diff:` 注释(差异口必须写明原因)")
            registry.append(f"{name}:{i + 1}:{side}")
    return registry


def test_frontend_template_split_wiring():
    """模板分片接线守阵(2026-09-26 W1; 26-09-27 收敛后 = 单一语义源 shared/tpl): 清单完整性 + 差异口 + 聚合配平

    模板拆分/收敛后的静默故障形态(与 JS 片段的 _scan_mixin_wiring 同源):
      1. 分片文件在盘上但清单漏挂 —— boot 不注入, 该页面区整块消失(零报错);
      2. 清单挂了不存在的分片 / into 非法 —— boot fetch 404, 整页停在错误占位;
      3. 两套 shell 清单漂移(各自演化 parts/scripts)—— 单一语义模板下等于偷偷分裂出第二份模板;
      4. 绕开 UI 差异口私拷模板块(双模板副本的复发形态)—— 由 _scan_ui_diff_registry 钉住。
    另钉: 聚合标签配平(切割边界错位的兜底)、shell ≤214 行(S1 定 200, 26-10-06-0838 S5/S6 各 +3, R2 26-10-09-2219 S1 +4, W6 26-10-13-0811 dt_table.css 挂载 +2, issue 26-10-20-2231 prism dialogs.css 挂载 +2)/ 单分片 ≤400 行、清单脚本序(vendor 首 / app.js 尾)。
    """
    problems = []
    manifests = {}
    for ui in _UI_ALL:
        shell = open(os.path.join(STATIC_ROOT, ui, "index.html"), encoding="utf-8").read()
        udir = os.path.join(STATIC_ROOT, ui)
        mf = _ui_manifest(ui)
        manifests[ui] = mf
        n_shell = shell.count("\n") + (0 if shell.endswith("\n") else 1)
        if n_shell > 214:
            problems.append(
                f"{ui}/index.html {n_shell} 行, shell 体量上限 214"
                "(S1 定 200 = 核心层 1 行 + 首批 9 变体; 计划 26-10-06-0838 S5/S6 各 +3; "
                "R2 计划 26-10-09-2219 S1 起 drawer_pages classic 插件 +4; "
                "W6 计划 26-10-13-0811 shared/dt_table.css 挂载(注释+link)+2; "
                "issue 26-10-20-2231 prism/css/dialogs.css 挂载(注释+link)+2)"
            )
        assert '<script src="/shared/boot.js"></script>' in shell, f"{ui} shell 缺 boot.js 引用(分片无人注入)"
        names = []
        for part in mf["parts"]:
            path = _tpl_path(part["src"], ui)
            names.append(os.path.basename(part["src"]))
            if not os.path.isfile(path):
                problems.append(f"{ui}: 清单挂了不存在的分片 {part['src']}(boot fetch 404 = 整页停在错误占位)")
                continue
            n = open(path, encoding="utf-8").read().count("\n")
            # 单分片体量上限默认 400; settings-detail.html 是 HR 表①(计划 26-10-01-2216 阶段2,
            # 拍板②b 按站点明细表)的落点, 391 -> 435 行属功能增长不是拆分回潮, 单独点名给例外额度
            # (其余分片仍钉 400); 26-10-02-1936 阶段2 折叠头 + 覆盖式全屏覆盖层再涨 454 -> 473,
            # 额度提到 500; 26-10-04-0312 S4 表③ 拉取历史(全局 <details> 段)再涨 482 -> 539,
            # 额度提到 560 —— 该分片下次再长应把 speed/keys 等视图拆成独立分片 —— 切割须过
            # 等价性验证(pitfalls/web-ui/frontend-split.md), 不得顺手抽文件
            # 26-10-18(计划 26-10-17-1737 S6/S7)曾给 settings.html 开 440 的例外: 「全局流量来源」卡
            # 补了 provider 条件隐藏与单位下拉, 400 -> 418 行; 注释当时就写了「下次再长应先把该卡整体
            # 重构成独立组件」。26-10-18(计划 26-10-18-0813 B3/D15)正是这么做的 —— 三张卡并成
            # 「流量与限速」并抽成 aq-traffic-card + shared/tpl/traffic-card.html, settings.html 只剩
            # 一行挂载, 例外额度随之删除(不留给下一次"再加一点")。
            name = os.path.basename(part["src"])
            cap = 560 if name == "settings-detail.html" else 400
            if n > cap:
                problems.append(f"{ui}/{part['src']} {n} 行, 超 {cap} 行单分片体量上限")
            if part.get("into") not in ("app", "body"):
                # 其余值 = #app 内自定义选择器落点(boot.js 会先查常规 DOM 再下钻 <template> 片段;
                # 方案A 停靠面板 26-10-03-0917 W1 起 drawer 分片落 .drawer-dock)。约定: 必须以
                # "." 开头且落点容器真实存在于某分片, 防手滑写成任意字符串
                into = part.get("into")
                if not (isinstance(into, str) and into.startswith(".") and into):
                    problems.append(f"{ui}/{part['src']} into 非法: {into!r}(boot 只认 app|body 或 '.' 开头的选择器)")
                    continue
                # 自定义落点容器必须真实存在于某分片(boot.js 运行时 fail-fast, 这里提前到静态)
                if into[1:] not in _ui_aggregate(ui):
                    problems.append(f"{ui}/{part['src']} into 落点 {into} 在任何分片中都不存在(boot 会 fail-fast 停在错误占位)")
        tpl_dir = os.path.join(udir, "tpl")
        if os.path.isdir(tpl_dir):
            problems.append(f"{ui}: 残留 {ui}/tpl/ 目录(收敛后唯一源是 shared/tpl, 双副本必须删除)")
        assert mf["scripts"], f"{ui} 清单缺 scripts(逻辑脚本无人放行)"
        assert mf["scripts"][0].endswith("vue.global.prod.js"), f"{ui} 清单首个脚本必须是 Vue vendor"
        assert mf["scripts"][-1].endswith("/app.js"), (f"{ui} 清单末个脚本必须是 app.js(它末尾才 createApp, 且启动时要读 window.AQB_*)")
        # CSS 分层: 链接顺序即级联序; 单文件 ≤700 行体量守阵
        css_files = _ui_css_files(ui)
        if ui in ("atlas", "console"):
            rels = [os.path.relpath(p, STATIC_ROOT).replace(os.sep, "/") for p in css_files]
            assert rels == [
                f"{ui}/style.css", f"{ui}/css/components.css", f"{ui}/css/views.css", f"{ui}/css/dialogs.css"
            ], (f"{ui} CSS 链接顺序漂移: {rels}(级联序 = link 序; 拆分是连续字节切片, 重排顺序前先核对视觉等价)")
            for p in css_files:
                n = open(p, encoding="utf-8").read().count("\n")
                if n > 700:
                    problems.append(f"{os.path.relpath(p, STATIC_ROOT)} {n} 行, 超 700 行单 CSS 体量上限")
        else:
            # prism 分层(issue 26-10-20-2231): 令牌 → 五主题 → base → components → views → **dialogs**。
            # dialogs 必须排在 views 之后 —— 弹窗族是最后介入级联的本皮肤层, 排在前面就会被页面级
            # 规则反压(该皮肤此前正是这种"级联序相反"的变形结构, 约 300 行错位克隆噪音由此而来)。
            rels = [os.path.relpath(p, STATIC_ROOT).replace(os.sep, "/") for p in css_files]
            assert rels == ["prism/css/tokens.css"] + [
                f"prism/css/themes/{t}.css" for t in ("ocean", "galaxy", "frost", "golden", "orbit")
            ] + ["prism/css/base.css", "prism/css/components.css", "prism/css/views.css", "prism/css/dialogs.css"
                ], (f"prism CSS 链接顺序漂移: {rels}(级联序 = link 序; 令牌/主题必须在最前, 弹窗层在最后)")
            # 体量: 存量冻结 —— prism/css/views.css 现存 818 行(页面级版式密度本就高于另两皮肤),
            # 拆它属独立排期; 这里冻结现值, 只拦"再长"。其余文件一律吃 700 行口径。
            frozen = {"prism/css/views.css": 818}
            for p in css_files:
                rel = os.path.relpath(p, STATIC_ROOT).replace(os.sep, "/")
                n = open(p, encoding="utf-8").read().count("\n")
                limit = frozen.get(rel, 700)
                if n > limit:
                    problems.append(f"{rel} {n} 行, 超 {limit} 行单 CSS 体量上限" + ("(存量冻结, 只许减不许增)" if rel in frozen else ""))
    # 单一语义模板: 各套 shell 清单必须逐项相等 —— 漂移 = 偷偷分裂出第二份模板(收敛前态回潮)
    base_mf = manifests[_UI_ALL[0]]
    for ui in _UI_ALL[1:]:
        assert manifests[ui] == base_mf, (
            f"{ui} 的 tpl-manifest 与 {_UI_ALL[0]} 不一致 —— 单一语义模板下清单漂移 = 模板分裂回潮, 必须逐项对齐: "
            f"{_UI_ALL[0]}={base_mf} / {ui}={manifests.get(ui)}"
        )
    # 盘上孤儿分片: shared/tpl 存在但清单漏挂
    shared_dir = os.path.join(STATIC_ROOT, "shared", "tpl")
    listed = {os.path.basename(p["src"]) for p in manifests["atlas"]["parts"]}
    if os.path.isdir(shared_dir):
        for f in sorted(os.listdir(shared_dir)):
            if f.endswith(".html") and f not in listed:
                problems.append(f"shared/tpl/{f} 在盘上但清单漏挂(boot 不注入 = 该页面区整块消失)")
    # UI 差异口注册表(活差异清单): 条件块只认 _UI_ALL 内的皮肤名且必须带 ui-diff 注释
    registry = _scan_ui_diff_registry(problems)
    assert registry, "UI 差异口注册表为空 —— 该机制是收敛后新增模板级差异的唯一入口; 若确已全部消除, 同步本守阵"
    assert not problems, "模板分片接线问题: " + "; ".join(problems)
    # 聚合配平放最后: 切割边界错位(半个元素切进相邻分片)在这里现形
    for ui in _UI_ALL:
        _assert_tags_balanced(_ui_aggregate(ui), f"{ui} 聚合模板")


def test_frontend_tpl_ctl_bits_single_source():
    """模板层「小控件」三件套单点守阵(issue 26-10-20-2231 / 台账 R23-B-01·02·16·17)

    收敛前四族"小控件"各有多份实现(开关 7 / 折叠段头 5 / 折叠交互 4 种 / 分段钮 4 套), 它们
    不是风格差异而是同一件事写了好几遍: 给开关加一项能力要改 7 处、改一次折叠键盘策略要改 5 处。
    统一到 <aq-switch> / <aq-fold> / <aq-seg>(模板 shared/tpl/ctl-bits.html, 定义 shared/ctl_bits.js)
    之后, 真正要钉的是**不许悄悄长出第二份实现** —— 复写回潮的形态全是静默的:
      1. 手抄块回到某个调用点(类名照旧、样式照旧, 只有"下次改一处"失效);
      2. 分段钮的档位清单又写回模板(与 JS 单点漂移, 加一档漏一处);
      3. 三件套没接线(模板在盘上但清单漏挂 / 组件没注册 = 页面整块空白且零报错)。
    故本守阵三条: 手抄块全仓归零且唯一实现只在三件套 / 四套分段钮都吃数据 / 三件套接线齐。
    """
    tpl_dir = os.path.join(STATIC_ROOT, "shared", "tpl")
    bits_path = os.path.join(tpl_dir, "ctl-bits.html")
    assert os.path.isfile(bits_path), \
        "缺 shared/tpl/ctl-bits.html(三件套模板的唯一实现; 改回各调用点手抄 = 收敛作废)"
    bits = open(bits_path, encoding="utf-8").read()
    for tpl_id in ("tpl-aq-switch", "tpl-aq-fold", "tpl-aq-seg"):
        assert bits.count(f'id="{tpl_id}"') == 1, \
            f"ctl-bits.html 里 {tpl_id} 必须恰一份(模板层唯一实现)"
    # 可访问性契约随实现一起钉住(issue 26-10-20-2231 的唯一"真影响可用性"项):
    #   · 折叠段头 = 唯一可点元素(role=button + tabindex=0 + aria-expanded 挂在它身上);
    #   · 里层「收起/展开」钮 = 鼠标重复入口, 必须 aria-hidden + tabindex=-1 —— 移出 tab 链,
    #     否则 Tab 到内钮按 Enter, 内钮 click 与本层 toggle 各打一次, 净效果"按了没反应";
    #     e2e 的 getByRole('button') 也正因此找不到它(见坑档 pitfalls/web-ui/template-render)。
    assert 'role="button" tabindex="0" :aria-expanded="open"' in bits, \
        "aq-fold 段头必须 role=button + tabindex=0 + aria-expanded(aria 只能挂可点的那一层)"
    assert 'aria-hidden="true" tabindex="-1"' in bits, \
        "aq-fold 里层「收起/展开」钮必须 aria-hidden + tabindex=-1(否则 tab 链里出现双触发点)"

    # 1. 手抄块归零: 三件套的 CSS 钩子类名在整个 tpl 目录里各只出现一次, 且就在三件套自己身上。
    #    先剥注释 —— 三件套头注里会引用这些类名解释"为什么这么写"。
    def _strip(text):
        return re.sub(r"<!--[\s\S]*?-->", "", text)

    tpl_files = {
        f: _strip(open(os.path.join(tpl_dir, f), encoding="utf-8").read())
        for f in sorted(os.listdir(tpl_dir)) if f.endswith(".html")
    }
    for needle, owner in (('class="hb-switch"', "aq-switch"), ('class="hb-blk-hd hb-sub-toggle"', "aq-fold")):
        where = [(f, t.count(needle)) for f, t in tpl_files.items() if needle in t]
        assert where == [
            ("ctl-bits.html", 1)
        ], (f"{needle} 必须只在 ctl-bits.html 出现一次(实测 {where}) —— 调用点手抄回潮: "
            f"应改用 <{owner}>, 否则「改一处」又变成改 N 处")

    # 2. 四套分段钮都吃数据(清单单点各自在 JS 领域层, 模板只交 items/value/pick)
    pop = tpl_files["popovers.html"]
    drawer_tpl = tpl_files["drawer.html"]
    head_tpl = tpl_files["drawer-head.html"]
    for text, needle, why in (
        (pop, ':items="$root.histGranItems"', "历史粒度三档(清单在 dialogs.js HIST_GRAN_ITEMS)"),
        (drawer_tpl, ':items="dtMergeTabList"', "抽屉合并态页签(投影自 MERGE_PAIRS)"),
        (drawer_tpl, ':items="dtTabItems"', "抽屉非合并态四页签(投影自 DT_TAB_LABELS)"),
        (head_tpl, ':items="$root.qbWindowTabs"', "流量窗口档位(投影自 QB_WINDOW_NAMES)"),
        (head_tpl, ':items="$root.qbYAxisTabs"', "纵轴三态(投影自 QB_YAXIS_MODES)"),
    ):
        assert needle in text, f"缺 {needle} —— {why} 的按钮又回模板里手写了"
    # 档位文案不得在模板里出现第二份(drawer.html 的流量页签是**能力门**而非档位, 单独留一个
    # v-if=qbTrafficOn 按钮; 它的门控在 test_frontend_qb_traffic_chart_wiring 里钉着)
    for literal in (">常规<", ">Tracker<", ">用户<", ">内容<", ">自动<", ">限速+20%<", ">手动<", "['day', 'month', 'year']"):
        assert literal not in drawer_tpl and literal not in head_tpl and literal not in pop, \
            f"模板里仍有硬编码档位/页签文案 {literal} —— 文案单点在 JS 领域层(分段钮只吃 items)"

    # 3. 三件套接线: 定义(ctl_bits.js 挂 window.AQ_*) + 注册(app.js app.component) + 清单(parts 注入 body,
    #    scripts 排在 app.js 之前 —— app.js 末尾才 createApp 并读 window.AQ_*, 排后面拿到 undefined)
    js = open(os.path.join(STATIC_ROOT, "shared", "ctl_bits.js"), encoding="utf-8").read()
    app_js = open(os.path.join(STATIC_ROOT, "shared", "app.js"), encoding="utf-8").read()
    for name, comp in (
        ("aq-switch", "AQ_SWITCH_COMPONENT"), ("aq-fold", "AQ_FOLD_COMPONENT"), ("aq-seg", "AQ_SEG_COMPONENT")
    ):
        assert f"window.{comp} = {{" in js, f"ctl_bits.js 缺 window.{comp} 定义(<{name}> 无实现)"
        assert app_js.count(f'app.component("{name}", window.{comp})') == 1, \
            f"app.js 缺/重复 app.component(\"{name}\")(未注册 = 模板里当未知元素渲染, 整块控件消失且零报错)"
    for ui in _UI_ALL:
        mf = _ui_manifest(ui)
        parts = [p["src"] for p in mf["parts"]]
        assert "/shared/tpl/ctl-bits.html" in parts, f"{ui} 清单漏挂 ctl-bits.html 分片(boot 不注入)"
        i_bits = mf["scripts"].index("/shared/ctl_bits.js")
        i_app = mf["scripts"].index("/shared/app.js")
        assert i_bits < i_app, f"{ui} 清单里 ctl_bits.js 必须排在 app.js 之前(否则注册时 window.AQ_* 尚未定义)"


def test_frontend_shell_sprite_login_parity():
    """三份 index.html shell 内联段守阵(issue 26-10-20-2231): sprite 段与 #app+login 段三皮肤对齐

    三 shell 除 head 资源清单外逐字同约 87.5%, 但三处物理拷贝里只有 tpl-manifest 被
    test_frontend_template_split_wiring 钉死"逐项相等" —— sprite(80 行/67 symbol)与 #app+login 段
    没有守阵: 加一个图标/改一处登录遮罩要改 3 个文件, 漏一个的表现是"某皮肤下该图标空白且无任何
    报错"(登录遮罩则是首屏第一眼、在任何 JS 之前渲染的块)。合并唯一路径是后端渲染时注入, 会让
    index.html 失去"可直接静态打开"的能力(测试亦直接读盘), 属能力回退 —— 故补齐守阵让重复不漂:
      1. sprite 段: <svg class="icon-sprite" 起到配套 </svg>, 三份逐字相等(当前实测相等);
      2. #app+login 段: <div id="app" 起到 tpl-manifest 前, 归一 HTML 注释与空行后相等
         (console 合法多一行皮肤说明注释; 注释不渲染, 归一后比 —— 标记/属性/文本 drift 一律红)。
    另钉 symbol 数下限: sprite 若被整体外提成共享文件, 三份会同时消失、相等断言恒真 —— 下限逼
    那种迁移显式改守阵(同轮补覆盖, 不是放宽)。
    """
    shells = {}
    for ui in _UI_ALL:
        with open(os.path.join(STATIC_ROOT, ui, "index.html"), encoding="utf-8") as f:
            shells[ui] = f.read()

    def _segment(text, start, end, keep_end=False):
        i = text.find(start)
        assert i != -1, f"shell 缺起始锚点 {start!r}(守阵提取失败 = 没守住任何东西)"
        j = text.find(end, i + len(start))
        assert j != -1, f"shell 起始锚点 {start!r} 之后缺结束锚点 {end!r}"
        return text[i:j + (len(end) if keep_end else 0)]

    def _strip_comments_blanks(text):
        text = re.sub(r"<!--.*?-->", "", text, flags=re.S)
        return "\n".join(ln.rstrip() for ln in text.split("\n") if ln.strip())

    def _first_diff(a, b):
        la, lb = a.split("\n"), b.split("\n")
        for k in range(min(len(la), len(lb))):
            if la[k] != lb[k]:
                return f"首个差异在第 {k + 1} 行: {la[k]!r} != {lb[k]!r}"
        return f"前缀相同但行数不同: {len(la)} vs {len(lb)}"

    # 1. sprite 段: 逐字相等(动一个字节都要三皮肤同步)
    sprites = {ui: _segment(t, '<svg class="icon-sprite"', "</svg>", keep_end=True) for ui, t in shells.items()}
    base_sprite = sprites[_UI_ALL[0]]
    n_symbol = base_sprite.count("<symbol")
    assert n_symbol >= 40, (
        f"{_UI_ALL[0]} sprite 段仅 {n_symbol} 个 <symbol>(当前实测 67) —— 下限逼「整体外提」类迁移显式改守阵, "
        f"不放任相等断言在三份同时清空后恒真"
    )
    for ui in _UI_ALL[1:]:
        assert sprites[ui] == base_sprite, (
            f"{ui} 的图标 sprite 段与 {_UI_ALL[0]} 不一致 —— 改图标须三皮肤同步(漏改的表现: 该皮肤下图标空白"
            f"且无任何报错); {_first_diff(base_sprite, sprites[ui])}"
        )

    # 2. #app+login 段: 注释与空行归一后相等(console 多一行皮肤说明注释是合法差异, 不参与比对)
    apps = {
        ui: _strip_comments_blanks(_segment(t, '<div id="app"', '<script type="application/json" id="tpl-manifest">'))
        for ui, t in shells.items()
    }
    base_app = apps[_UI_ALL[0]]
    assert 'id="app"' in base_app and 'class="login-mask"' in base_app, (
        f"{_UI_ALL[0]} 的 #app 段提取结果不像登录遮罩块(id=app: {'id=\"app\"' in base_app} / "
        f"login-mask: {'class=\"login-mask\"' in base_app})"
    )
    for ui in _UI_ALL[1:]:
        assert apps[ui] == base_app, (
            f"{ui} 的 #app+login 段与 {_UI_ALL[0]} 不一致(注释/空行已归一) —— 改登录遮罩须三皮肤同步; "
            f"{_first_diff(base_app, apps[ui])}"
        )


def test_frontend_skin_css_token_parity():
    """三皮肤令牌**名集**相等守阵(issue 26-10-20-2231)

    三皮肤各自维护一份令牌声明块(atlas/console 在 style.css 的 :root, prism 在 css/tokens.css +
    css/themes/*), 取值本就该按设计语言各写各的 —— 但**名字**必须齐: 皮肤少声明一个令牌,
    别处 `var(--x)` 的那条声明会在计算值阶段判无效而被整条丢弃(既无报错也无回退), 表现为
    "某皮肤下某处字体/圆角静默失效"。星图此前正是这样少了 3 个字体令牌(86 vs 89):
    自己 css 里 4 处 `var(--font-mono)` 裸引用全程失效, 共用层 shared/console_hub.css 只能
    靠 "星图没有 --font-mono" 的兜底链各自为政(两套兜底链还不一致)。
    故钉: 三皮肤令牌名集必须相等(取值自由); 差异按缺/多两侧成对列出, 便于直接补漏。
    """
    def _tokens(paths):
        names = set()
        for p in paths:
            with open(p, encoding="utf-8") as f:
                for line in f:
                    m = re.match(r"\s*(--[\w-]+)\s*:", line)
                    if m:
                        names.add(m.group(1))
        return names

    prism_css = os.path.join(STATIC_ROOT, "prism", "css")
    sets = {ui: _tokens([os.path.join(STATIC_ROOT, ui, "style.css")]) for ui in ("atlas", "console")}
    sets["prism"] = _tokens(
        [os.path.join(prism_css, "tokens.css"),
         os.path.join(prism_css, "base.css")] + sorted(
             os.path.join(prism_css, "themes", f)
             for f in os.listdir(os.path.join(prism_css, "themes")) if f.endswith(".css")
         )
    )
    base = sets[_UI_ALL[0]]
    assert len(base) > 60, f"{_UI_ALL[0]} 只解析出 {len(base)} 个令牌 —— 提取口径坏了(守阵会恒真)"
    for ui in _UI_ALL[1:]:
        missing, extra = sorted(base - sets[ui]), sorted(sets[ui] - base)
        assert sets[ui] == base, (
            f"{ui} 与 {_UI_ALL[0]} 的令牌名集不一致(相对 {_UI_ALL[0]}: 缺 {missing} / 多 {extra}) —— "
            f"皮肤少声明一个令牌, 该皮肤下 `var(--x)` 的那条声明在计算值阶段整条作废且无任何报错; "
            f"补令牌, 或把消费方改成带兜底的 var(--x, fallback)"
        )


def test_frontend_button_system_paired():
    """按钮体系(.bt)迁移守阵(2026-09-26, 方案 B 星图胶囊 / C 棱镜双色) —— "两套 UI 成对改"的静态兜底

    迁移是一次大批量类名替换(ce-btn/ce-icon -> bt 变体), 最危险的残缺形态是"只改一边"或
    "模板换了 CSS 没换"(页面静默回退到 UA 默认按钮)。四类机械断言:
    1. 旧类名 ce-btn / ce-icon 在全部前端语料(html/css/js)里零残留;
    2. .bt 体系块与六个语义变体在两套 CSS 各有成对定义(星图 style.css / 棱镜 components.css);
    3. 两套 index.html 的 bt 变体用量逐类相等(模板本就同构, 数量不等 = 单边漏改/误删);
    4. 双色配方令牌 --on-accent / --on-accent-ink / --on-error 在星图 :root 与棱镜五主题成对声明
      (缺一个主题, 该主题实心主钮/危险钮的前景色会掉回继承或 UA 默认)。
    """
    atl = os.path.join(STATIC_ROOT, "atlas")
    pri = os.path.join(STATIC_ROOT, "prism")
    atl_html = _ui_aggregate("atlas")
    pri_html = _ui_aggregate("prism")
    atl_css = _ui_css_aggregate("atlas")
    pri_css = open(os.path.join(pri, "css", "components.css"), encoding="utf-8").read()

    # 1. 旧类名零残留(全语料: static 树下全部 html/css/js, 排除 vendor; 类名若只留在注释里
    #    也应清理, 留着会误导下一次死类判定)
    corpus_files = []
    for root, dirs, files in os.walk(STATIC_ROOT):
        dirs[:] = [d for d in dirs if d != "vendor"]
        for f in files:
            if f.endswith((".html", ".css", ".js")):
                corpus_files.append(os.path.join(root, f))
    leftovers = []
    for f in corpus_files:
        text = open(f, encoding="utf-8").read()
        for bad in ("ce-btn", "ce-icon"):
            if bad in text:
                leftovers.append(f"{os.path.relpath(f, STATIC_ROOT)}:{bad}")
    assert not leftovers, f"旧按钮类名必须零残留: {leftovers}"

    # 2. .bt 体系块与变体在两套 CSS 成对定义
    variants = ["primary", "ghost", "danger", "danger-solid", "icon", "sm"]
    for css, name in (
        (atl_css, "atlas css 聚合(link 序)"),
        (pri_css, "prism/css/components.css"),
        (_ui_css_aggregate("console"), "console css 聚合(link 序)"),
    ):
        assert re.search(r"^\.bt \{", css, re.M), f"{name} 缺 .bt 体系块"
        for v in variants:
            assert re.search(rf"^\.bt\.{re.escape(v)} \{{", css, re.M), f"{name} 缺 .bt.{v} 变体"

    # 3. 两套模板的 bt 用量逐类相等(class="bt ..." 静态写法; :class 动态绑定单独对账)
    def _bt_counts(html):
        counts = {}
        for m in re.finditer(r'class="(bt[^"]*)"', html):
            for cls in m.group(1).split():
                if cls == "bt" or cls.startswith("bt-"):
                    counts[cls] = counts.get(cls, 0) + 1
                elif cls in ("primary", "ghost", "danger", "danger-solid", "icon", "sm"):
                    counts[f"~{cls}"] = counts.get(f"~{cls}", 0) + 1
        return counts

    a_cnt, p_cnt = _bt_counts(atl_html), _bt_counts(pri_html)
    assert a_cnt == p_cnt, f"两套模板 bt 用量不成对: atlas={a_cnt} prism={p_cnt}"
    assert a_cnt, "模板里没有任何 bt 按钮(迁移被整体回退?)"
    for dyn in ("'danger-solid'", "'primary'"):
        assert atl_html.count(dyn) == pri_html.count(dyn) and atl_html.count(dyn) >= 1, \
            f"站内确认框的动态变体绑定 {dyn} 未成对"

    # 4. 双色配方令牌成对声明(星图 :root 一处 + 棱镜五主题各一处)
    for tok in ("--on-accent:", "--on-accent-ink:", "--on-error:"):
        assert atl_css.count(tok) == 1, f"星图 :root 应恰好声明一次 {tok}"
        themes = os.path.join(pri, "css", "themes")
        for tf in os.listdir(themes):
            tcss = open(os.path.join(themes, tf), encoding="utf-8").read()
            assert tok in tcss, f"棱镜主题 {tf} 缺 {tok}(五主题须成对)"


def test_frontend_search_syntax_wiring():
    """搜索匹配**服务端单点**的前端接线守阵(2026-09-26 统一, 治"同一语义修三遍")

    两类"pytest 全绿但交互废掉 / 前端再长出第二套匹配实现"的故障形态, 一律机械钉住:
    1. 顶栏搜索清除钮必须挂 @mousedown.prevent —— 缺了它, 按下瞬间输入框失焦收窄
      (focus 时 240→300px 的宽度过渡回退), 绝对定位在右沿的按钮随收窄移出光标,
      click 落空 => "有焦点时点 x 清不掉, 无焦点正常"; 两套 index.html 成对断言。
    2. 三页(辅种/种子/追剧)搜索命中一律消费服务端 searchHits(views.py::search_torrents 的
      行级裁决, 候选行 = 名字/站点/分类/路径/标签/文件名): 前端**不得再出现**任何文本匹配
      实现 —— 26-09-26 统一前 filters.js(_parseSearchQuery/_searchNorm/_torrentTextMatch)、
      hr.js(更早的整句 includes)、shows.js(剧名整句 includes)各持一份, 同一语义
      (恶女 10 / 季包"cat 12")前后端修了三遍; 复活任何一个即与单点漂移, 直接红。
      语法(词 AND/-排除/短语/归一)行为级用例在服务端侧: test_parse_query_tokens /
      test_search_torrents_*(对账守阵已无对象 —— 客户端没有解析器了)。
    """
    shared = os.path.join(STATIC_ROOT, "shared")
    filters_js = open(os.path.join(shared, "filters.js"), encoding="utf-8").read()
    hr_js = open(os.path.join(shared, "hr.js"), encoding="utf-8").read()
    app_js = open(os.path.join(shared, "app.js"), encoding="utf-8").read()
    shows_js = open(os.path.join(shared, "shows.js"), encoding="utf-8").read()

    # 1. 清除钮 mousedown.prevent 成对(两套模板的 search-clear 按钮逐个检查)
    for theme in _UI_ALL:
        html = _ui_aggregate(theme)
        m = re.search(r'<button[^>]*class="search-clear"[^>]*>', html)
        assert m, f"{theme} 模板找不到 search-clear 按钮"
        tag = m.group(0)
        assert "@mousedown.prevent" in tag, f"{theme} search-clear 缺 @mousedown.prevent(焦点态清除失灵回归)"
        assert '@click="clearSearch"' in tag, f"{theme} search-clear 缺 clearSearch 接线"

    # 2. 前端无第二匹配实现(反漂移: 任何一个复活即红); 三页接线走 searchHits
    # (注释里允许引用旧函数名讲历史, 故断言"名字+括号"—— 定义或调用才算复活)
    for name in ("_parseSearchQuery", "_searchNorm", "_torrentTextMatch", "_torrentSearchPass"):
        assert not re.search(rf"{name}\s*\(", filters_js), \
            f"filters.js 复活了客户端匹配 {name}(搜索匹配单点在 views.py, 复活即漂移)"
    assert "_torrentTextMatch" not in hr_js, "hr.js 不得再留 _torrentTextMatch 旧整句实现(双实现漂移)"
    assert 'searchHitsQ' not in app_js, "app.js 残留 searchHitsQ(客户端匹配时代的陈旧守卫, 已随单点化删除)"
    assert "hits.has(r.hash)" in filters_js, "filteredTorrents 未消费 searchHits(种子页搜索断线)"
    assert "(s.name || \"\").toLowerCase().includes(q)" not in shows_js, \
        "shows.js 复活了剧名整句 includes 旧匹配(剧名命中应来自服务端名字行)"


def test_frontend_search_pending_no_collapse():
    """搜索待响应期空命中集不得接管列表守阵(2026-10-07 修详情面板/流量图搜索/筛选时跳动)

    两层缺陷各钉一处, 都是"首词待响应窗把整个列表塌成 0 行"的上下游:
    1. view.js/filters.js: 首词的 searchHits 还是空集(没有"上一查询"可沿用), filteredTorrents/
      filteredGroups 的命中门照常生效 => 防抖 400ms + 请求往返的整个待响应窗里列表塌成 0 行:
      文档高塌掉 -> 滚动位置被钳回 0(列表中部搜一次整页跳顶), 底部停靠面板失去 sticky 锚点
      跟着弹(实测 docH 18582→800→1141、面板 top 430↔416 反复横跳)。
      钉住 searchPending 生命周期(输入武装防抖即置位 / doSearch 直达入口补武装 / resetSearch
      清除 / 落袋且过代际守卫后清除)与 _searchGateActive 单点(两个派生都走它, 任何一个绕开
      单点现写命中门即红; 渐进输入命中集非空时仍按旧集过滤, 标准 search-as-you-type 不变)。
    2. 三皮肤 .layout min-height 撑满首屏: 停靠面板(.drawer-dock)的 sticky 吸底只在"自然落点
      低于视口下界"时生效, 列表被筛短(真 0 命中/筛选到短列表)后文档变矮, 面板脱锚跟着内容
      末尾上浮(视口越高跳得越多)。内容列恒撑满(顶栏实测高走既有单点 --head-h)后锚点稳定。
    """
    shared = os.path.join(STATIC_ROOT, "shared")
    view_js = open(os.path.join(shared, "view.js"), encoding="utf-8").read()
    filters_js = open(os.path.join(shared, "filters.js"), encoding="utf-8").read()
    state_js = open(os.path.join(shared, "state.js"), encoding="utf-8").read()

    # 1a. searchPending 声明与生命周期(缺任何一环 = 待响应窗判定失真, 空集照样接管或永挂 pending)
    assert "searchPending: false" in state_js, "state.js 缺 searchPending 声明(待响应期判定无载体)"
    assert view_js.count("this.searchPending = true") == 2, \
        "view.js 武装点应恰两处(onSearchInput 防抖武装 + doSearch 直达入口补武装)"
    on_input = view_js[view_js.index("onSearchInput(event)"):]
    assert on_input.index("this.searchPending = true") < on_input.index("setTimeout(() => this.doSearch()"), \
        "onSearchInput 必须在武装防抖前置位 pending(否则首词防抖窗 400ms 里空集照样接管列表)"
    assert "this.searchPending = false;" in view_js[view_js.index("resetSearch()"):view_js.index("async doSearch")], \
        "resetSearch 必须清除 pending(清空搜索立即恢复全列表, 不得挂死在待响应态)"
    landing = view_js[view_js.index("this.searchHits = new Set(results.map"):]
    assert "this.searchPending = false" in landing[:landing.index("this.searchUncovered")], \
        "doSearch 落袋必须在写命中集后、派生消费前清除 pending(迟清一帧 = 真结果被当待响应态跳过)"
    # 落袋清除必须排在代际守卫**之后**(失配弃单不得清掉新词在途的 pending)
    do_search = view_js[view_js.index("async doSearch"):]
    assert do_search.index("(this.searchQuery || \"\").trim() !== q") < do_search.index("this.searchPending = false;"), \
        "doSearch 落袋清除 pending 必须在请求代际守卫之后(失配弃单不得清新词的待响应态)"

    # 1b. 命中门收单点: 两个派生都走 _searchGateActive, 不得绕开单点现写命中门
    assert "_searchGateActive(q)" in filters_js, "filters.js 缺 _searchGateActive 单点"
    assert filters_js.count("_searchGateActive(") >= 3, \
        "_searchGateActive 定义 + 两个派生(filteredTorrents/filteredGroups)都要消费"
    assert "if (!q) return base;" not in filters_js, \
        "filteredGroups 残留旧门 `if (!q) return base;`(未走 _searchGateActive, 待响应空集照样塌列表)"
    assert re.search(r"if \(!this\._searchGateActive\(q\)\) return base;", filters_js), \
        "filteredGroups 的文本段必须整段走 _searchGateActive 门"
    assert re.search(r"const gate = this\._searchGateActive\(q\);", filters_js) and "if (gate && !hits.has(r.hash)) continue;", \
        "filteredTorrents 的命中门必须走 _searchGateActive(绕开单点现写 = 待响应塌列表回归)"

    # 2. 三皮肤 .layout min-height 撑满首屏(dock sticky 锚点与列表长短无关)
    for theme in _UI_ALL:
        css_path = os.path.join(STATIC_ROOT, theme, "css", "views.css" if theme == "prism" else "components.css")
        css = open(css_path, encoding="utf-8").read()
        m = re.search(r"\.layout \{[^}]*\}", css, re.S)
        assert m, f"{theme} 找不到 .layout 规则"
        assert "min-height: calc(100vh - var(--head-h" in m.group(0), \
            f"{theme} .layout 缺 min-height 撑满首屏(列表筛短后停靠面板脱锚跳)"


def test_frontend_hr_safety_wiring():
    """删除安全档位的前端接线守阵(2026-09-25, 计划 webui-hr-safety-display)

    四类"字段/令牌打错 = pytest 全绿但页面静默空白或配色失效"的故障形态, 一律机械钉住:
    1. hr.js 的 token 映射表(HR_SRC_CLASSES / HR_SRC_BUCKETS)必须与后端 resolve.py 的 SRC_* 常量
      逐字一致 —— 来源档位是前后端契约, 打错字来源标记静默消失; 三档类名驱动单元格底线三编码(CSS),
      文字结论改由悬停弹窗承载(原生 title 已移除, 避免与弹窗叠出被遮挡的冗余提示);
    2. 做种时长列在两套 UI 各 3 处(组内成员/种子页/明细)都必须换绑 hrDurClass + hrSrcClass, 并由
      hrSrcFull/hrSrcHalf 挂底线 + hrPopEnter 触发 —— 漏一处那一列就不显示安全档位/来源线/悬停弹窗;
      弹窗单例 DOM(teleport body)每套 UI 恰一份(26-09-26-webui-hr-popup 起 :title 换成悬停弹窗触发);
      要求时长的渲染门只认「已做种非空 + 有要求」, 不得依赖 hr_triggered(2026-09-29 实报:
      未核/在线行被一并藏掉要求, 只剩孤立的来源芯片);
    3. hr-unk / hr-fail / hr-line 新样式必须三套 CSS 成对定义(改这里时同步另一套的纪律);
      hr-pop 弹窗规则(浮层/箭头/双轨)同理成对;
      整格线(在线)必须挂**文字包裹层** .dur-body 而不是单元格 .m-dur —— 行是 grid, 单元格被拉满整列宽,
      挂它上面 width:100% 的空 <i> 就画成整列一条(线随列宽不随文字, 2026-09-29 真机实报);
    4. 前端 js 里引用的 m.hr_* 字段必须都在后端 hr_view_fields 的键集里(字段一致性守阵,
      M4 设置页守阵同款思路)。
    """
    shared = os.path.join(STATIC_ROOT, "shared")
    hr_js = open(os.path.join(shared, "hr.js"), encoding="utf-8").read()
    resolve_py = open(
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src", "auto_qb", "hr", "resolve.py"),
        encoding="utf-8",
    ).read()

    # 1. 来源 token 契约: 后端常量集 == 前端两张映射表的键集
    src_tokens = set(re.findall(r'^SRC_[A-Z_]+ = "([a-z_]+)"', resolve_py, re.M))
    assert len(
        src_tokens
    ) == 6, f"resolve.py 的 SRC_* 常量应为 6 个(v3: 删 policy/local_exempt; 26-09-30 计划 hr-trigger-semantics: 删 unverified), 实测 {sorted(src_tokens)}"
    assert "unverified" not in src_tokens, "SRC_UNVERIFIED 应已随「未核实」灰档退役(本地统一 SRC_LOCAL)"

    def _map_keys(name):
        m = re.search(rf"const {name} = \{{(.*?)\}};", hr_js, re.S)
        assert m, f"hr.js 缺 const {name}"
        return set(re.findall(r"([a-z_]+):", m.group(1)))

    assert _map_keys("HR_SRC_CLASSES") == src_tokens, "HR_SRC_CLASSES 键与后端 SRC_* 不一致"
    assert _map_keys("HR_SRC_BUCKETS") == src_tokens, "HR_SRC_BUCKETS 键与后端 SRC_* 不一致"
    # 来源文案不再进原生 title(2026-09-29 晚: 原生 title 与悬停弹窗叠出, 出现「来源:未核实」等
    #   被弹窗遮挡的冗余提示; 来源改由 hrSrcClass → CSS 底线编码, 文字结论在悬停弹窗内)。
    #   故 hrDurHint / HR_SRC_TITLES / HR_EXCLUDED_TITLE 整套应已退役。
    assert "hrDurHint" not in hr_js, "hr.js 仍残留 hrDurHint(来源+已排除的 title 组装) —— 原生 title 已移除"
    assert "HR_SRC_TITLES" not in hr_js, "hr.js 仍残留 HR_SRC_TITLES —— 来源文案不再进 title"
    assert "HR_EXCLUDED_TITLE" not in hr_js, "hr.js 仍残留 HR_EXCLUDED_TITLE —— 已排除文案不再进 title"
    # 四个安全档位(2026-09-25 用户修正起 failed=未达标终态红档; 2026-09-30 计划
    # hr-trigger-semantics: unknown 灰档退役, 换 warning 黄档=疑似辅种): warning 由前端映射 hr-warn 黄
    for name in ("HR_SAFETY_CLASSES", "HR_SAFETY_BUCKETS"):
        assert _map_keys(name) == {"danger", "failed", "safe", "warning"}, f"{name} 键集应为四个安全档位"

    # 2. 做种时长列换绑 + 弹窗单例: 每套 UI 2 处触发面 / 各 1 份弹窗 DOM
    # !触发面自 3 收敛为 2(计划 26-10-11-1722 P2): 明细成员单元格的两份副本(辅种页 / 追剧集)
    #   合并为**单份**渲染器 <aq-member-cells>(模板在 tpl/xtpl.html#tpl-aq-member-cells), 该渲染器
    #   由两页共用 ⇒ 计数 3 → 2 是收敛的结果, 不是漏换绑。!渲染器里的行为经 `$root.` 回调根实例
    #   (根数据只在根实例上), 故下列 pattern 两种形态都收 —— 裸名(页面模板) / `$root.` 前缀(渲染器)。
    #   两页共用关系由 test_frontend_table_shell_single_point 与 _scan_column_cells_paired 兜住
    #   (两处调用点都必须用 <aq-member-cells>), 覆盖不丢。
    for ui in _UI_ALL:
        html = _ui_aggregate(ui)
        for pattern, want in (
            (r':class="\[(?:\$root\.)?hrDurClass\(m\), (?:\$root\.)?hrSrcClass\(m\)\]"', 2),
            (r'v-if="(?:\$root\.)?hrSrcHalf\(m\)"', 2),  # 半格线(本地 / 未核实)画在数值上
            (r'v-if="(?:\$root\.)?hrSrcFull\(m\)"', 2),  # 整格线(在线)画在**文字包裹层**上
            (r'class="dur-body"', 2),  # 文字包裹层: 整格线随文字不随列宽(挂单元格 = 随列宽)
            (r'@mouseenter="(?:\$root\.)?hrPopEnter\(\$event, m\)"', 2),
            (r'@mouseleave="(?:\$root\.)?hrPopLeave"', 3),  # 2 处触发面 + 弹窗自身(移入弹窗不隐藏)
            (r'<teleport to="body">', 1),
            (r'ref="hrPop"', 1),
        ):
            got = len(re.findall(pattern, html))
            assert got == want, f"{ui} 里 `{pattern}` 应出现 {want} 处, 实测 {got}"
        # 旧绑定不得残留(换绑遗漏的形态)
        assert ':class="hrTimeClass(m)"' not in html, f"{ui} 仍有做种时长列挂着旧 hrTimeClass —— 漏换绑"
        assert "hrSrcBadge" not in html, f"{ui} 仍挂着旧的 2 字来源徽标 hrSrcBadge —— 漏换绑"
        assert "hrDurTitle" not in html, f"{ui} 仍有做种时长列挂原生 :title —— 应已换悬停弹窗触发"
        assert ':title="hrDurHint(m)"' not in html, f"{ui} 做种时长列仍挂原生 :title(hrDurHint) —— 应只靠悬停弹窗"
        # 行内文字 chip 零残留(2026-09-29 非文字化的对象就是这两个 chip, 复活即列宽问题回归)
        assert 'class="hr-src"' not in html, f"{ui} 做种时长列仍有 .hr-src 文字 chip —— 文案应只走 title"
        assert ">已排除<" not in html, f"{ui} 做种时长列仍有「已排除」文字 chip —— 应已撤进 title"
        # 要求时长必须「有要求就显示」(2026-09-29 用户实报: 未核/在线行只剩来源芯片, 看不到要求):
        # 门只能是「已做种非空 + 有要求」—— 依赖 hr_triggered 会把未触发行连要求一起藏掉。
        # !自计划 26-10-11-1722 P3 起该列也搬进了渲染器(种子页 <aq-torrent-cells>), 行为经 $root
        #   回调根实例 —— 故 pattern 两种形态都收(裸名 / $root. 前缀), 与上方其它换绑项同口径。
        assert re.search(r'v-if="(?:\$root\.)?cellSeedingTime\(m\) && m\.hr_req_time"', html), \
            f"{ui} 做种时长列的要求渲染门被改 —— 应只按 hr_req_time 判定(未触发行也要看得到要求)"

    # 弹窗「无时长要求」收起条件: 不得再把 unverified 包进去(它有本地要求, 收起就看不到),
    # 真放行/免罪(义务已了)仍收起——2026-09-29 实报后定稿
    collapse = re.search(r"if \(\[([^\]]*)\]\.includes\(src\) \|\| !\(req > 0\)\)", hr_js)
    assert collapse, "hr.js 弹窗的「无时长要求」收起条件找不到了 —— 渲染规则被改? 同步本守阵"
    assert "unverified" not in collapse.group(1), "未核实行不得收起为「无时长要求」(本地有要求, 收起即失真)"
    assert "site_released" in collapse.group(1) and "site_exempt" in collapse.group(1), "真放行/免罪仍应收起轨道"

    # 3. 新样式两套 CSS 成对
    atlas_css = _ui_css_aggregate("atlas")
    prism_css = _ui_css_aggregate("prism")  # issue 26-10-20-2231: hr-pop 段已并入 prism/css/dialogs.css, 改读聚合
    console_css = _ui_css_aggregate("console")
    for css, name in (
        (atlas_css, "atlas css 聚合(link 序)"), (prism_css, "prism css 聚合(link 序)"),
        (console_css, "console css 聚合(link 序)")
    ):
        for rule in (
            ".m-pair.hr-warn",
            ".m-pair.hr-fail",
            ".m-dur .hr-line",
            ".hr-pop",
            ".hp-arrow",
            ".hp-gauge",
            ".hp-badge",
            # 排除命中行的中性灰档(2026-10-02): 弹窗 lane=excluded 的点与结论色, 三套成对
            ".hp-dot.excluded",
            ".hp-verdict.excluded",
        ):
            assert rule in css, f"{name} 缺 {rule} 规则 —— 三套 UI 必须成对定义"
        # 死样式零残留: 最后一个 .hr-src 消费方(已排除 chip)已撤进 title
        assert ".m-pair .hr-src" not in css, f"{name} 仍留着 .hr-src chip 样式 —— 已无消费方, 应删除"
        assert "z-index: 140" in css, f"{name} 缺弹窗 z-index: 140(须高于 ctx-menu 100 与 speed-pop 131)"
        # 半格线是空 <i>: 只给 left:0 而 width:auto 会收缩成 0 —— 线整条不可见(2026-09-29 实报)
        for half in (".m-dur .dur-val > .hr-line", ".m-dur.src-local .hr-line"):
            assert half in css, f"{name} 缺 {half} 规则 —— 本地的半格线会消失"
        # 死档位样式零残留(2026-09-30 计划 hr-trigger-semantics: unknown/unverified 随灰档退役)
        assert ".m-pair.hr-unk" not in css, f"{name} 仍留着 .hr-unk 死样式 —— 未核实档已退役"
        assert ".src-unver" not in css, f"{name} 仍留着 .src-unver 死样式 —— unverified 来源档已退役"
        assert re.search(r"\.m-dur \.dur-val > \.hr-line \{[^}]*width: 100%", css), \
            f"{name} 半格线没写显式 width:100% —— 空 <i> 的 width:auto 会收缩成 0(线整条不可见)"
        # 整格线(在线)必须挂文字包裹层 .dur-body —— 挂 .m-dur 上会随列宽(2026-09-29 真机实报:
        # 行是 grid, 单元格被拉满整列宽, width:100% 的空 <i> 画成整列一条, 与「随文字」相反)
        for full in (".m-dur .dur-body {", ".m-dur .dur-body > .hr-line"):
            assert full in css, f"{name} 缺 {full} 规则 —— 在线的整格线会随列宽而不是随文字"
        assert re.search(r"\.m-dur \.dur-body > \.hr-line \{[^}]*width: 100%", css), \
            f"{name} 整格线没写显式 width:100% —— 空 <i> 的 width:auto 会收缩成 0(线整条不可见)"
        assert ".m-dur > .hr-line" not in css, \
            f"{name} 整格线仍挂在单元格 .m-dur 上 —— 单元格是 grid item 会被拉满列宽, 线随列宽不随文字"

    # 4. 前端引用的 m.hr_* 字段 ⊆ 后端 hr_view_fields 键集(字段一致性)
    from auto_qb.core.qbmanager import QbManager
    from auto_qb.torrents import TorrentRecord
    from helpers import FakeTorrent

    keys = set(QbManager.hr_view_fields(TorrentRecord.from_torrent(FakeTorrent(hash="HX"))))
    assert keys, "hr_view_fields 连空配置分支都该返回全键集"
    used = set()
    for name in sorted(os.listdir(shared)):
        if name.endswith(".js"):
            used |= set(re.findall(r"\bm\.(hr_[a-z_]+)", open(os.path.join(shared, name), encoding="utf-8").read()))
    for ui in _UI_ALL:
        used |= set(re.findall(r"\bm\.(hr_[a-z_]+)", _ui_aggregate(ui)))
    unknown = used - keys
    assert not unknown, f"前端引用了后端不存在的 HR 字段: {sorted(unknown)}(字段打错 = 页面静默空白)"


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
    shared_css = open(os.path.join(STATIC_ROOT, "shared", "console_hub.css"), encoding="utf-8").read()
    assert ".hr-detail-table-bar" in shared_css, "shared/console_hub.css 缺表头过滤栏段(chips + 数据截至)"
    assert ".hr-detail-table .hr-lane-a" in shared_css, "shared/console_hub.css 缺表格徽章色义段"
    for css, name in (
        (_ui_css_effective("atlas"), "atlas 生效样式面(聚合 + shared)"),
        (_ui_css_effective("console"), "console 生效样式面(聚合 + shared)"),
        (_ui_css_effective("prism"), "prism 生效样式面(聚合 + shared)"),
    ):
        assert ".hr-detail-table" in css, f"{name} 缺 .hr-detail-table 段 —— 三套 UI 必须成对改(计划 §5.6)"
        for lane in ("a", "b", "c", "d"):
            assert f".hr-detail-table .hr-lane-{lane}" in css, f"{name} 缺 .hr-lane-{lane} 档位色义(计划 §5.4)"
        assert ".hr-detail-table tr.missing .hr-lane" in css, f"{name} 缺失踪行 --paused 描边弱化规则"
        assert ".hr-vsrc" in css, f"{name} 缺来源小徽章(.hr-vsrc)样式"
    for ui in ("atlas", "console", "prism"):
        own = _ui_css_aggregate(ui)
        for rule, what in (
            # 带 `{` 边界: 不带的话 `.hr-detail-table .hr-pres` 会被 `.hr-pres.hr-pres-on`
            # 那条修饰规则**子串命中**, 底形本体删了也照样绿(2026-10-21 红验实测)
            (".hr-detail-table .hr-vsrc {", "来源徽章底形"),
            (".hr-detail-table .hr-pres {", "在列/退役徽章底形"),
            (".hr-detail-table .hr-sub {", "副行小字"),
        ):
            assert rule in own, f"{ui} 自己的 CSS 缺 {rule}({what}) —— 底形族是三皮肤真差异, 不许并进共用层"


# node 单测探针(不落盘): 加载真实 hr_status.js, 对模块级纯函数 hrsCompareRows 跑排序语义电池
# (计划 26-10-02-1936 §3.4: 空值恒末位两方向不反转 / verified_ts·last_seen 0 哨兵 / 档位固定秩 /
#  字符串·数值分型 / 同值稳定性)。无 node 静默跳过(与 _scan_js_syntax_with_node 同口径)。
_NODE_HRS_SORT_PROBE = r"""
const fs = require("fs");
global.window = {};
eval(fs.readFileSync(process.argv[1], "utf8"));
const rows = [
  { tid: 10, name: "kb", uploaded_bytes: 200, ratio: 2.0, need_seed_seconds: 3600,
    done_iso: "2026-09-01T10:00:00", verified_ts: 100, last_seen: 200, lane: "B" },
  { tid: 20, name: "ka", uploaded_bytes: null, ratio: null, need_seed_seconds: null,
    done_iso: null, verified_ts: 0, last_seen: 0, lane: "A" },
  { tid: 30, name: "kc", uploaded_bytes: 300, ratio: 30.0, need_seed_seconds: 60,
    done_iso: "2026-09-02T10:00:00", verified_ts: 300, last_seen: 100, lane: "C" },
  { tid: 40, name: "kd", uploaded_bytes: 300, ratio: 15.0, need_seed_seconds: 60,
    done_iso: null, verified_ts: 200, last_seen: 300, lane: "D" },
];
const seq = (key, dir) => [...rows].sort((a, b) => hrsCompareRows(a, b, key, dir)).map((r) => r.tid);
const checks = [
  ["bytes 降序 null 末位", JSON.stringify(seq("uploaded_bytes", -1)) === "[30,40,10,20]"],
  ["bytes 升序 null 仍末位", JSON.stringify(seq("uploaded_bytes", 1)) === "[10,30,40,20]"],
  ["同值稳定性(两方向 30 在 40 前)", seq("uploaded_bytes", -1).indexOf(30) < seq("uploaded_bytes", -1).indexOf(40)
    && seq("uploaded_bytes", 1).indexOf(30) < seq("uploaded_bytes", 1).indexOf(40)],
  ["verified_ts 0 哨兵降序末位", JSON.stringify(seq("verified_ts", -1)) === "[30,40,10,20]"],
  ["verified_ts 0 哨兵升序仍末位", JSON.stringify(seq("verified_ts", 1)) === "[10,40,30,20]"],
  ["last_seen 两方向空恒末位", JSON.stringify(seq("last_seen", -1)) === "[40,10,30,20]"
    && JSON.stringify(seq("last_seen", 1)) === "[30,10,40,20]"],
  ["档位固定秩降序 D>C>B>A", JSON.stringify(seq("lane", -1)) === "[40,30,10,20]"],
  ["档位固定秩升序 A<B<C<D", JSON.stringify(seq("lane", 1)) === "[20,10,30,40]"],
  ["名称字符串升序", JSON.stringify(seq("name", 1)) === "[20,10,30,40]"],
  ["名称字符串降序", JSON.stringify(seq("name", -1)) === "[40,30,10,20]"],
  ["need_seed_seconds null 两方向末位", JSON.stringify(seq("need_seed_seconds", -1)) === "[10,30,40,20]"
    && JSON.stringify(seq("need_seed_seconds", 1)) === "[30,40,10,20]"],
  ["done_iso 空串两方向末位", JSON.stringify(seq("done_iso", 1)) === "[10,30,20,40]"
    && JSON.stringify(seq("done_iso", -1)) === "[30,10,20,40]"],
];
console.log(JSON.stringify({ ok: checks.filter((c) => c[1]).length, total: checks.length,
  failed: checks.filter((c) => !c[1]).map((c) => c[0]) }));
"""


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
    # 生效面(聚合 + shared): 排序头/箭头/限宽钩子已收敛进 shared/console_hub.css(三皮肤逐条同),
    # 徽章底形族仍各皮肤自带 —— 两处都在这张面上, 判据不变(三皮肤都得吃到)。
    for css, name in (
        (_ui_css_effective("atlas"), "atlas 生效样式面(聚合 + shared)"),
        (_ui_css_effective("console"), "console 生效样式面(聚合 + shared)"),
        (_ui_css_effective("prism"), "prism 生效样式面(聚合 + shared)"),
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


def test_frontend_site_alert_icon_wiring():
    """站点 chip 改色表达守阵(计划 26-10-19-2206 S4, 取代 26-10-19-2007 的两槽口径)

    通道分工: 站点问题(缺配置 / tracker 报错)走**颜色**, 命令结果走**图标**(固定放站点名之后)。
    三件事必须同时成立, 缺一条就是"pytest 全绿但界面废掉":
      ① 三皮肤样式**键集合相等**(漏一套 = 某皮肤下 chip 不变色/图标没颜色, 只在一套皮肤上看得见);
         缺配置的虚线底边(非颜色通道, D4)与搜索命中"让出底色改描边"(D6)同属可读性契约, 一并钉住;
      ② 站点 chip 骨架收敛为单点组件 <aq-site-chip>(issue 26-10-20-2231 / R23-B-09, 此前种子页/
         组行/集行各抄一份 11 行骨架、torrent 版还漏 search-hit): 单点模板里**一个**图标槽
         (命令结果), 三处调用点都走它, tooltip 挂整块 chip; 旧图标类(`.sa` / `sa-<token>`)
         必须零残留 —— 残留 = 某个视图还在画第二个图标;
      ③ 图标 token -> 符号映射单点在 commands.js(模板里不得出现第二份 `#i-xxx` 映射),
         且该表**只含命令结果四种 token**(站点问题不该再有图标)。
    """
    CMD_TOKENS = ("pending", "ok", "warn", "error")
    NEED = {".site-chip .sx", ".g-status.k-error .ico", ".site-chip.search-hit"}
    NEED |= {f".site-chip .sx-{t}" for t in CMD_TOKENS}
    NEED |= {".site-chip.sa-no-conf", ".site-chip.sa-tracker"}

    def _selectors(css):
        """从 CSS 文本里收集本守阵关心的选择器(注释先剥, 避免注释里的示例文字被当成规则)

        只收三类: 命令结果图标槽(.site-chip .sx*) / 站点问题变色类(.site-chip.sa-*) /
        搜索命中(.site-chip.search-hit); 另加状态列错误图标强化(.g-status.k-error)。
        种子状态色(.site-chip.seeding 等)不在本守阵范围(它们由 components.css 各自维护)。
        """
        body = re.sub(r"/\*[\s\S]*?\*/", "", css)
        keys = (".site-chip .sx", ".site-chip.sa-", ".site-chip.search-hit", ".g-status.k-error")
        found = set()
        for sel in re.findall(r"(?m)^\s*([^{}@/][^{}]*)\{", body):
            for one in sel.split(","):
                one = " ".join(one.split())
                if one.startswith(keys):
                    found.add(one)
        return found

    per_skin = {}
    for ui in _UI_ALL:
        css = _ui_css_aggregate(ui)
        per_skin[ui] = _selectors(css)
        missing = NEED - per_skin[ui]
        assert not missing, f"{ui} 缺站点 chip 样式: {sorted(missing)}"
        assert "animation: none" in css, f"{ui} 缺 prefers-reduced-motion 降级"
        # 旧图标类零残留(R6): 站点问题已改走底色, 图标类必须清零(只删模板不删样式 = 两套语义并存)
        assert "sa-no_site_conf" not in css and "sa-tracker_error" not in css, (
            f"{ui} 仍残留旧站点图标类 sa-<token> —— 站点问题已改走 chip 底色, 图标类必须清零"
        )
        assert not re.search(r"\.site-chip \.sa\b", css), f"{ui} 仍残留 .sa 图标槽规则"
        # D4: 缺配置必须带非颜色通道(虚线底边) —— 灰度/色盲下与实底红可区分
        body = re.search(r"\.site-chip\.sa-no-conf\s*\{([^}]*)\}", css)
        assert body, f"{ui} 缺 .site-chip.sa-no-conf 规则体"
        assert "dashed" in body.group(1), f"{ui} 缺配置 chip 缺虚线底边(D4 非颜色通道)"
        # D6: 搜索命中让出底色 —— 不得再用 accent 柔底占住 chip 填充
        hit = re.search(r"\.site-chip\.search-hit\s*\{([^}]*)\}", css)
        assert hit, f"{ui} 缺 .site-chip.search-hit 规则体"
        assert "--accent-soft" not in hit.group(1), (f"{ui} 搜索命中仍占 accent 柔底 —— 站点问题/种子状态的底色被吞(D6)")
        assert "inset" in hit.group(1) and "--accent-line" in hit.group(1), (f"{ui} 搜索命中未改 accent 描边(D6/R2)")
        # D9: 明细行站点文本同语义(只染文字色)
        assert ".m-site.sa-no-conf" in css and ".m-site.sa-tracker" in css, (f"{ui} 缺明细行站点文本染色规则(D9)")

    base = per_skin[_UI_ALL[0]]
    for ui in _UI_ALL[1:]:
        assert per_skin[ui] == base, (
            f"{ui} 的站点 chip 样式键集与 {_UI_ALL[0]} 不一致 —— 三皮肤必须齐备(计划 R3): "
            f"{_UI_ALL[0]}-{ui}={sorted(base - per_skin[ui])} / {ui}-{_UI_ALL[0]}={sorted(per_skin[ui] - base)}"
        )

    # ② 站点 chip 骨架单点(issue 26-10-20-2231 / R23-B-09): 组件模板一个图标槽, 三处调用点都走它
    tpl = open(os.path.join(STATIC_ROOT, "shared", "tpl", "xtpl-cells.html"), encoding="utf-8").read()
    assert 'id="tpl-aq-site-chip"' in tpl, "xtpl-cells.html 缺 #tpl-aq-site-chip 单点模板(site-chip 三份回潮?)"
    assert tpl.count("<aq-site-chip ") == 3, "站点 chip 必须恰三处调用点(种子页/组行/集行)且都走单点组件(调用点必带 :m prop, 故标签后一定有空格; 注释里的字面提及不计)"
    assert tpl.count('class="ico sx"') == 1, "chip 单点模板里要有一个命令结果图标槽"
    assert tpl.count("'search-hit': m.hit") == 1, "chip 单点必须带 search-hit 绑定(torrent 版曾漏, 见 issue 26-10-20-2231)"
    assert 'class="ico sa"' not in tpl, "站点问题不再走图标 —— 模板里不得再有 .sa 图标槽"
    assert "'sa-' + m.site_alert" not in tpl, "旧站点图标类拼接必须清零"
    # tooltip 挂整块 chip(D8): 单点模板绑合并文案, 图标不再各自挂 title
    assert tpl.count("$root.siteAlertClass(m)") == 1, "chip 单点按站点问题染色"
    assert tpl.count("$root.chipAlertTip(m)") == 1, "tooltip 必须挂整块 chip"
    assert tpl.count("$root.siteAlertAria(m)") == 1, "站点问题必须补 aria-label(D4)"
    for seg in re.findall(r"<svg[^>]*class=\"ico sx\"[^>]*>", tpl):
        assert ":title" not in seg, "命令结果图标不再单独挂 title(触发面已放大到整块 chip)"

    # ③ token -> 符号单点: 命令结果符号一律经 alertIconHref 取, 不得内联第二份映射
    # (单点模板 × 1 槽 = 1 次; 模板里既有的 #i-warn/#i-caret 属于别的语义, 不在此列)
    assert tpl.count("$root.alertIconHref(") == 1, "命令结果图标必须经 alertIconHref 单点取符号"
    cmds = open(os.path.join(STATIC_ROOT, "shared", "commands.js"), encoding="utf-8").read()
    m = re.search(r"const ALERT_ICON = \{([\s\S]*?)\};", cmds)
    assert m, "commands.js 必须有 ALERT_ICON 单点"
    assert set(re.findall(r"(\w+):\s*\"#i-",
                          m.group(1))) == set(CMD_TOKENS), ("ALERT_ICON 键集必须只含命令结果四种 token(站点问题已改走颜色, 不得留图标映射)")


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
    cols_js = open(os.path.join(shared, "columns.js"), encoding="utf-8").read()
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


def _css_rules(text):
    """(选择器列表, 规则体) 序列。先剥注释 —— 注释落在选择器捕获里会污染逐字比较。"""
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    out = []
    for mo in re.finditer(r"([^{}]*)\{([^}]*)\}", text):
        sels = [s.strip() for s in mo.group(1).split(",") if s.strip()]
        out.append((sels, mo.group(2)))
    return out


def _css_body(rules, sel, where):
    """按**完整选择器**取规则体(不用子串 —— 子串会被 `... > :first-child` 那条先撞上)。"""
    for sels, body in rules:
        if sel in sels:
            return body
    raise AssertionError(f"{where} 缺规则 `{sel}` —— 底色契约的落点被删或被改名?")


def _css_bg(body):
    """取 background 声明值(空白归一); 缺声明即红。"""
    mo = re.search(r"background:\s*([^;]*);", body)
    assert mo, f"规则体内找不到 background 声明: {body.strip()[:80]}"
    return " ".join(mo.group(1).split())


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
