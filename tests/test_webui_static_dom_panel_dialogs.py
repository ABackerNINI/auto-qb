"""test_webui_static_dom_panel_dialogs 测试计划: webui 前端静态守阵: 详情面板 / 弹窗 / 浮层

## 测试计划(每个测试函数一条)

- test_removed_redundant_tooltips_stay_removed: 复述型 tooltip 不得复活守阵(报告 26-10-04-0815 + 详情面板二轮清理) —— 模板已移除的复述型原生 title 文案(statusbar「点击修改」「数据状态」/ topbar 页签「按分组展示」「全部种子一行一条」/ drawer「关闭(Esc)」/ dialogs 族 title="关闭" / settings-detail·xtpl「点击收起」/ columns.js H1 横幅「点击关闭」/ drawer_tpl 二轮: 05 图例五色与条级顺序说明·06 等待响应与仅看异常说明·07-09 求和口径/客户端 Top 复述/qB flags 前缀/会话累计/对端整行复述·10-11 展开折叠全部目录与全选与目录文件数·12 优先级跳过与占比细条·13-15 kpis 容器派生口径与窗口累计复述)不得写回, 悬浮提示一律走 shared/ui_feedback.js 拦截层
- test_recheck_confirm_wired_all_mouse_entries: 重新校验确认框三入口接线守阵(T13, 计划 26-10-05-0314 S3) —— commands.js _recheckConfirm 单点(helper 存在 + 文案与 okText 调用形态沿键盘路径原样)+ bulkAct 批量通道 / drawer.js torrentCmd 单选通道各含 recheck 确认分支 + shortcuts.js _kbAct 改调共用 helper 不再内联 confirmDialog 文案 + 共用文案字符串全仓只此一份, 任一接入点被重构摘除即红
- test_skip_check_dialog_precheck_wired: 跳检预检对话框接线守阵(T23, 计划 26-10-05-0314 S4) —— ui_feedback.js _modalInit 声明 okDisabled/busy/verdict 三字段 + popovers.html 确认钮 :disabled="modal.okDisabled" 绑定 / busy 行 / verdict 行式渲染区(强制钮复用 extraText 第三钮 danger-solid) + drawer.js 两入口(skipCheckTorrent/skipCheckMulti, 后者带可选 targets 供单组入口 skipCheckGroup 复用)均交棒 _skipCheckDialog 且不再自带 _openModal + _skipCheckDialog 进框即禁用(busy + 固定警示区)并发预检(_skipPrecheck), 任一被重构摘除即红
- test_skip_check_dialog_verdict_render: 跳检预检三分流渲染逻辑守阵(T24, 计划 26-10-05-0314 S4) —— _skipPrecheck 状态机分支(预检失败降级=启用普通确认且无强制钮 / 含 blocked=确认强制双钮全收 / ok+force 混合=确认钮文案「跳检 N 个可跳检的」+ 强制钮「强制跳检全部」/ force-only=确认保持禁用 / 全 ok=只启用确认)+ ok 子集派生(cls==="ok" 过滤)+ 确认路径送 ok 子集而强制路径送全量+force(_skipExec 单发 body 仅 force 时带 force 键, 批量确认只走 hashes 通道)+ 降级文案「后端闸门仍会在执行时拦截」+ _skipVerdictRows 计数行与分组上限截断(slice(0,5)+等 X 个), 任一分支被改写即红
- test_modal_identity_stamp_landing_guard: 模态身份戳落袋守卫单点(F1-01, issue 26-10-06-0028) —— ui_feedback.js _openModal 每框发自增 mid + _modalIsCurrent 单点(visible + mid 双比对) + drawer.js _skipCheckDialog 把 this.modal.mid 交棒 _skipPrecheck 且落袋守卫为 seq + 身份戳双条件(取消跳检框后开无关 modal, 只有身份戳拦得住迟到回执)
- test_frontend_ctx_menu_multi_select_targets_selection: 多选右键菜单守阵 —— 四个 open*Menu 必须写 menu.multi、三套 UI 的行菜单必须消费注册表 ctxItems(ctxMenuKind()) 且段内无逐项直写(批量支走 ctxAct/ctxDelete)、ctxAct/ctxDelete 必须复用 bulkAct/bulkDelete
- test_frontend_ctx_menu_group_actions_parity: 单组右键菜单与多选批量菜单项集一致守阵(2026-10-09 用户报「单组右键菜单缺选项」)—— 模板只按支名消费注册表(ctxItems(ctxMenuKind()) 单点)、单组支必含六个组级入口(重新校验/跳检/限速/移动/标签分类/导出, 与批量支同项集)、跳检项吃 flags.skip_check_menu 门控、六入口复用多选同一套下游链路(recheckGroup->_actCore / 限速移动跳检->drawer.js 多选对话框 / metaGroup->openMetaDialog / exportGroup->_exportHashes)不为组级另开旁路
- test_frontend_meta_dialog_paired: 标签/分类编辑对话框守阵 —— 三套 UI 成对(metaOpen 对话框 + 批量菜单/单种子菜单两处入口, 批量控制条退役后模板层不再直接调 openMetaDialog(null))、shared 逻辑接线(openMetaDialog 锁定目标 + metaToggleTag 走 bulk 链路 + ctxMeta 先收菜单)、.meta-dialog/.opt-pill 三套 CSS 成对定义
- test_frontend_dialog_shell_single_point: 对话框外壳单点守阵(issue 26-10-20-2231, R23-A-02·A-03·A-08 收敛) —— 三段式外壳(标题头/动作栏/遮罩手势对/关闭钮)只许在组件模板 dialog-shell.html 一处(剥注释后字面量清点), 调用点一律经 <aq-modal>(9 处调用覆盖 10 个对话框开态, :open/:close/:close-args/mask-class/icon-class/width-class/body-class 接线逐点清点) + 无遮罩异形 speed-pop 走 <aq-modal-head>; 管理对话框双胞胎合并为单份模板 + mgrDef 数据表(state.js computed 两态字段/文案/动作全表驱动, dialogs-mgr/popovers 零 mgrOpen 直判残留, dialogs.js mgrSubmitNew 分派) + modal-details 两套并一(state.js::modalDetailRows: verdict 在前 copy=false / details 在后 copy=true, 复制钮边界 String(d.value ?? '') 修 value===0 不出钮)
- test_frontend_rename_dialog_width_wiring: 重命名对话框宽档接线守阵(2026-10-19 用户报「弹窗太小」)—— 字段值 = 完整种子显示名(真实名称 routinely 80~120 字符), 骑通用 .modal 基档 520(为确认/提示一句话设计)时输入框仅 474px, 真浏览器实测 97 字符长名裁掉 223px(桩名 43 字符恰好不裁, 故冒烟从未暴露); 修法 = _openModal 增 cls 附加类选项(空 = 既有对话框零变化)+ 重命名走 rename-dialog 类 + 三皮肤 .modal.rename-dialog 宽档(--modal-w-add 860, 与设定位置/添加种子同档)。钉 _modalInit cls 字段 / popovers.html 根类绑定并入 modal.cls / editRename 传类 / 三皮肤宽档规则成对; 行为面由 e2e/rename-dialog-fit.spec.mjs 真浏览器钉
- test_frontend_add_torrent_drag_drop_wiring: DND-01 全局拖拽添加种子接线守阵(静态) —— window 级 drag 四事件 add/remove 对称、drop handler 必 preventDefault(否则浏览器直接打开文件)、接管判据只认 Files/text-uri-list(不误拦页面内拖文本)、双 UI 落点遮罩成对 + app.js addDragOver 状态
- test_frontend_add_torrent_partial_receipt_wiring: 添加种子「部分受理关窗」回执分流守阵(2026-10-18 用户报障「部分种子添加失败(已存在)时添加窗口不消失」) —— submitAddTorrent 三态分流(r.status === "warn" 分支在, 只判 r.ok 的二态写法回潮即红)+ warn 分支关窗且 warn 类 toast 带详情(后端文案带成功/失败计数)+ ok 分支保持关窗 + error(全拒)分支不得关窗(文件/链接原样没进 qB, 留窗才能改完重提; 部分成功与全部失败混为一谈是本案病根, 两个方向都钉)。行为面由 e2e/add-partial-receipt.spec.mjs 真浏览器钉
- test_frontend_add_combo_blur_close_and_fit: 添加种子三下拉「失焦即收 + 限高不出窗」接线守阵(2026-10-03 报障) —— 三输入框 @focusout 收层 + 收层必须 40ms 合帧守卫(label 转发回焦同步收 = 闪烁) + 三开层方法撤销挂起收层 + 开层 watcher 量「输入行→滚动容器可见底沿」净空限高(滚动条留在窗口内) + 候选异步到位重限 + 三浮层互斥双向(closeAddPopsExcept 单点, 三开层各调一次, 26-10-04-0130)
- test_frontend_ctx_menu_refit_by_measured_size: 浮层菜单开层实测钳位守阵(issue 26-10-06-1717) —— _menuFit 按 offsetWidth/offsetHeight 实测算(退回常量估算即红)且以视口为界、每次复位兜底限高; 三个菜单容器 ref(ctxMenu/headMenuEl/filePrioEl)与三个开层 watcher 的 (stateKey, refName) 一一对上且都在 $nextTick 里量; _menuFitRefit 现读 this[stateKey]/this.$refs[refName] 并守 visible
- test_frontend_add_combo_label_clear_mask_and_refit: 添加种子三下拉「第二轮遗留四项」守阵(2026-10-03, label 闪烁 2026-10-04 三修+四轮 JS 守卫) —— 四个 combo 的字段 label 一律 @mousedown.prevent + @click.stop(mousedown 默认动作 blur 武装的 40ms 合帧定时器在人手按住期间先收层、松手转发回焦再重开 = 闪烁; stop 挡 window click 收层; 缺一即回归)+ 收层 JS 单点守卫 _popBlurShouldHold(收层前判「焦点已回本族输入框 / 本族 label 转发 click 仍在途」→ 不收, 模板修饰符缺位(旧页签残留)时独立根除闪烁, add 三字段 + meta 分类全接)+ 三输入框内嵌清空 x(@mousedown.prevent 保焦点 + @click.stop 挡 window 收层, 缺一即「清完下拉没了」)+ 遮罩关窗改「mousedown 记臂位 + mouseup.self 才关」(全仓 11 处, @click.self 会被"拖选文字终点落在遮罩上抬手"误判成点空白关窗, 零残留)+ 过滤词变化重限高(三个输入值 watcher + meta 侧三处)+ meta 分类下拉补失焦收层与 window click 兜底名单 + 清空钮样式三皮肤成对
- test_frontend_combo_hiscroll_never_scrolls_ancestors: 下拉高亮滚动跟随「只滚菜单内部」守阵(2026-10-29 八修, 用户报「选中新路径后再点下拉框, 弹窗里的文字从上往下滑一次」)—— _hiScroll 禁用 scrollIntoView(它把**所有可滚祖先**一起滚: 开层过渡期 .add-dialog-body 的 scrollHeight 比 clientHeight 大 166px, 于是整段文案被滚走再弹回, 实测 body.scrollTop 0→166→83→18→0; 输入框为空时 hi=-1 无 [data-hi="1"] 故只有"选过路径"才看得见); 必须逐级向上以**菜单根为界**手动差值调 scrollTop(box.contains(n) + 到 box 即 break), 剥注释后不得出现 scrollIntoView 字面量(注释里讲禁令不算违规)。行为面由 e2e/move-dialog-fit.spec.mjs 逐帧采样 body.scrollTop 恒 0 + 文案 top 极差 ≤2px 钉
- test_frontend_add_options_recent_order: 添加种子三候选「最近使用」排序守阵(2026-10-09 用户动议: 保存路径/分类/标签按最近使用排序) —— 口径 = 由种子记录派生(非本机存储): 「最近使用」= 该值下种子 added_on 最大值, 数据面**跨视图自取数** `_addRecencyRows`(与 filters.js::facetRows 同族; 添加入口是顶栏常驻而 /api/state 按 viewMode 裁剪阵列, 直读 this.torrents 会在默认辅种页拿到空表 ⇒ 排序静默退化成字母序, 2026-10-09 e2e 首跑实测) ⇒ 零新存储; node 真跑 _addOrderByRecent(最近使用降序 -> 未用过落末尾并按字母序 -> 表空/表 null/值未命中一律退化纯字母序 + 纯函数不改入参)与 _addNormPath(与后端 infra/utils.path_normalize 同口径; 两侧不同径则 /api/paths 已归一路径与取数行的 qB 原文 save_path 对不上, 时间表恒不命中 ⇒ 静默退化成纯字母序); 静态钉接线(三候选都过 _addOrderByRecent 单点 + pick 不得再内联 .sort + _addRecencyMaps 经 _addRecencyRows 现算且三键齐全 + 路径键过 _addNormPath + _addRecencyRows 按 viewMode 分支且三来源齐全)
- test_frontend_busy_skeleton_single_point: busy+try+反馈+finally 骨架单点守阵(issue 26-10-20-2231) —— dialogs.js 三 helper 在册(_mgrRun 管理对话框写操作 / _panelLoad 面板加载与 tm 槽回执 / _postWaitCmd POST+waitCmd 三态 toast)+ 19 处调用点接线数对账(dialogs 14: mgr 5 + 面板加载 5 + POST 4; config_hub 5: tm 族 4 槽 + 一键导入)+ finally 复位保底住在单点内(漏 finally = 面板永久转圈)+ 裸 busy 置位反向断言(再手抄 = 破单点, 回潮即红)
- test_overlay_fit_single_point: 浮层「贴边留白 + 视口夹取」几何单点守阵(issue 26-10-20-2231) —— ①单点模块 shared/overlay_fit.js 四入口(EDGE=8 / clampAxis / probeRight / probeLeft / fitInViewport)在三份 tpl-manifest 同点登记且装载序在首个消费方 config_hub.js 之前(漏登记/序错 = 运行时取别名 undefined); ②七消费文件接线数逐文件对账(ui_feedback 7 / menu 5 / config_hub 4 / hr 3 / drawer 2 / columns 3 / dialogs 1, 全部经 FIT 别名); ③手写夹取式零残留(8/12 字面量夹取 / PAD / margin=8 / EDGE=8 回潮即红); ④12px 两处(hubAsk / speed-pop)显式命名传参 + 注释在位; ⑤顶层 const/let 跨文件撞名零容忍(实测事故: 经典脚本顶层 let/const 是全局词法环境, 七文件同写顶层 const FIT 致后六文件 SyntaxError、mixin 静默不注册、整页崩而静态守阵全绿; 跨文件别名只许方法内取或包 IIFE); 行为面 node 电池(四入口七型 + 与旧手写式四种书写网格代数等价), 真实浏览器几何由 e2e/menus.spec.mjs CTX-fit 左右缘盯
- test_frontend_move_dialog_combobox_wiring
- test_frontend_pop_item_a11y_contract: .pop-item 三分类 a11y 契约守阵(issue 26-10-29-1335, R23-A-09) ——
  选择式 combobox(单组件 <aq-combo-input>): 输入框 role=combobox + :aria-expanded + aria-autocomplete=list +
  :aria-controls(仅开层时指面板, 关层面板不在 DOM 防悬空引用) + :aria-activedescendant(带界只指真实候选);
  面板 role=listbox + :id=inputId+'-pop'; 两处 v-for 变体候选行 role=option/:id/:aria-selected 各齐两份;
  候选 id 生成式单点 comboOptId(add_torrent.js 定义恰 1 次, 模板消费恰 3 次), 预置行 aria-hidden 不配 option;
  同族顶栏: 列选择器项 Enter/Space 双键逐字同款 handler(筛选器项为基准锚一并钉), UI 切换项 :aria-current=page

## 皮肤档位口径
- 皮肤清单单点在 webui_helpers._UI_ALL(atlas/prism/console/flux); flux(第四套, plan 26-10-31-2316 S5)
  fork 自 console, 按 _UI_ALL 枚举的接线守阵随常量自动收编; 单独点名的成对面(qb-tabs 生效面/
  --qb-gap-hatch 令牌/纵轴控件版式/.opt-pill.is-gated/.meta-dialog/ctx-item hover)已显式加 flux 档。
"""

import json

import os

import re

import shutil

import subprocess

from pathlib import Path

from auto_qb.webui.commands import REANNOUNCE_BLOCKED_STATES as _PY_BLOCKED_STATES

from auto_qb.webui.commands import REANNOUNCE_INACTIVE_SKIP as _PY_INACTIVE_SKIP

from webui_helpers import read_shared
from webui_helpers import (
    STATIC_ROOT,
    _UI_ALL,
    _ui_manifest,
    _ui_aggregate,
    _ui_css_aggregate,
    _ui_css_effective,
    _app_bundle_files,
    _app_bundle_text,
)

from webui_dom_panel_support import _tpl_body


def test_removed_redundant_tooltips_stay_removed():
    """复述型 tooltip 不得复活守阵(报告 26-10-04-0815: A-G 组模板 66 处 + H1 columns.js)

    判定口径: tooltip 只是逐字复述可见内容 / 图标本身自明的都属冗余, 已整体移除;
    全站悬浮提示统一由 shared/ui_feedback.js 拦截层渲染。本守阵读模板/JS 源码钉住
    代表性文案, 哪个文件把已删文案写回去即红。判定为保留的 tooltip(操作说明/后果预告、
    drawer.js 等的 _openModal 弹窗标题字段、config_hub.js 设置节标题、独立图表部件)不在列。
    二轮(I 组): 详情面板 drawer_tpl 冗余 tooltip 清理(与可见文本复述 / 开发者口径 /
    图例按钮自明), IP 地址列 / 对端自身进度 / 按进度估算缺口等有增量 tooltip 保留不在列。
    """
    checks = (
        # A 组 · 底部状态栏: 数值逐字复述 + 「点击修改」增量提示 + 数据状态实现细节
        ("shared/tpl/statusbar.html", ("点击修改", "数据状态")),
        # B 组 · 顶栏页签: 与可见文字同义(图标+「分组」/「种子」)
        ("shared/tpl/topbar.html", ("按分组展示", "全部种子一行一条")),
        # D 组 · 抽屉关闭钮: ✕ 自明, Esc 快捷键在帮助浮层有正式清单
        ("shared/tpl/drawer.html", ("关闭(Esc)", "关闭（Esc）")),
        # E 组 · 对话框族关闭钮: 关闭钮的 ✕ 自明
        ("shared/tpl/dialogs.html", ('title="关闭"', )),
        ("shared/tpl/dialogs-mgr.html", ('title="关闭"', )),
        ("shared/tpl/popovers.html", ('title="关闭"', )),
        # E2 续(issue 26-10-20-2231): 对话框关闭钮收敛进组件模板后, 新单点同样不得复活该 tooltip
        ("shared/tpl/dialog-shell.html", ('title="关闭"', )),
        # F 组 · 曲线标题栏 caret: 箭头方向已表意
        ("shared/tpl/settings-detail.html", ("点击收起", )),
        ("shared/tpl/xtpl.html", ("点击收起", )),
        # H1 · columns.js 列偏好提示横幅: 横幅整体可点 + 手型光标 + 15s 自毁
        ("shared/columns.js", ("点击关闭", )),
        # I 组 · 详情面板冗余 tooltip 二轮(drawer_tpl A/B 清单): 同屏可见文本的复述 +
        #     开发者口径(求和/前端派生) + 图例/按钮自明文案, 同屏信息已足够不再悬浮重复
        ("shared/tpl/drawer.html", (':title="t.url"', )),
        ("shared/drawer_tpl/01-general-hero-tall.js", ('title="${r.label}"', )),
        ("shared/drawer_tpl/02-general-cards-low.js", ('title="${r.label}"', )),
        ("shared/drawer_tpl/03-general-dossier-collapsed.js", ('title="${r.label}"', )),
        (
            "shared/drawer_tpl/05-trackers-health-groups-low.js", (
                'title="正常"',
                'title="警告"',
                'title="更新中"',
                'title="失败"',
                "未启用(含虚拟条目)",
                'title="分区顺序即处理顺序',
            )
        ),
        ("shared/drawer_tpl/06-trackers-table-collapsed.js", (
            "正在等待 tracker 响应",
            "只显示 警告 / 更新中 / 失败 行",
        )),
        (
            "shared/drawer_tpl/07-peers-dashboard-tall.js", (
                "对端 upspeed 求和",
                "对端 dlspeed 求和",
                'title="${k} × ${byClient[k]}"',
                'title="其它 ${keys.length - 3}',
                'title="qB flags: ',
                'title="会话累计"',
                'title="会话累计 0"',
                '· ${p.client || "未知"}"',
            )
        ),
        (
            "shared/drawer_tpl/08-peers-groups-low.js", (
                'title="qB flags: ',
                'title="会话累计"',
                'title="会话累计 0"',
                '· ${p.client || "未知"}"',
            )
        ),
        (
            "shared/drawer_tpl/09-peers-density-collapsed.js", (
                'title="qB flags: ',
                'title="会话累计"',
                'title="会话累计 0"',
                '· ${p.client || "未知"}"',
            )
        ),
        ("shared/drawer_tpl/10-content-tree-detail-tall.js", ("展开全部目录", "折叠全部目录")),
        ("shared/drawer_tpl/11-content-treegrid-batch-low.js", (
            "全选 / 全不选(文件)",
            "目录内共",
            "展开全部目录",
            "折叠全部目录",
        )),
        ("shared/drawer_tpl/12-content-space-treemap-collapsed.js", (
            'title="优先级: 跳过"',
            'title="占总体积 ',
        )),
        # 2026-10-14: 原 13/14/15(流量变体)的复述型 tooltip 断言随流量变体移除而退役。
    )
    for rel, needles in checks:
        text = open(os.path.join(STATIC_ROOT, *rel.split("/")), encoding="utf-8").read()
        for needle in needles:
            assert needle not in text, (
                f"{rel} 出现已移除的复述型 tooltip 文案「{needle}」(报告 26-10-04-0815 判定为移除) —— "
                "悬浮提示一律走 shared/ui_feedback.js 拦截层, 不要把原生 title 写回去"
            )


def test_recheck_confirm_wired_all_mouse_entries():
    """重新校验确认框三入口接线守阵(T13, 计划 26-10-05-0314 S3)

    键盘路径原有确认框(shortcuts.js _kbAct), 鼠标路径(批量右键/单选右键/抽屉)点下即执行
    (issue 26-10-05-0254: 防护不对称)。S3 抽共用 helper(commands.js _recheckConfirm, 文案与
    调用形态逐字沿键盘路径)后四处同一文案。本守阵读 JS 源码钉住三个接入点 + 文案单点,
    任一被重构摘除即红:
    1. commands.js _recheckConfirm 存在, 且 confirmDialog/okText 调用形态与文案逐字原样;
    2. bulkAct(批量右键 ctxAct 的落点, 批量浮条退役后仍是批量通道单点)含 recheck 确认分支;
    3. drawer.js torrentCmd(单选右键与抽屉内命令共同通道)含 recheck 确认分支;
    4. shortcuts.js _kbAct 改调共用 helper, 不再内联 confirmDialog 文案;
    5. 共用文案字符串全仓只在 commands.js 出现一次(防三处各抄一份漂移)。
    """
    cmds = read_shared("commands.js")
    drawer = read_shared("drawer.js")
    shortcuts = read_shared("shortcuts.js")
    text = "全量重读磁盘并校验完整性, 大库上耗时长且不可中断。"

    # ① 共用 helper 单点: 调用形态(标题/okText)与文案逐字沿键盘路径原样
    m = re.search(r"async _recheckConfirm\(what\)\s*\{(.*?)\n    \},", cmds, re.S)
    assert m, "commands.js 找不到 _recheckConfirm(改名或挪走了? 同步本守阵)"
    helper = m.group(1)
    assert 'confirmDialog("重新校验"' in helper and '{ okText: "确定" }' in helper, (
        "共用 helper 未沿键盘路径原调用形态(confirmDialog + okText 确定) —— 入口间确认形态漂移"
    )
    assert text in helper, "共用 helper 丢失键盘路径既有文案(重新校验确认框文案必须逐字保留)"

    # ② 共用文案字符串只此一份(三入口共用, 防各抄一份漂移)
    for name, src in (("commands.js", cmds), ("drawer.js", drawer), ("shortcuts.js", shortcuts)):
        assert src.count(text) == (1 if name == "commands.js" else
                                   0), (f"{name} 内联了重新校验确认文案 —— 共用文案只允许存在 commands.js _recheckConfirm 一份")

    # ③ 批量通道(bulkAct): 批量右键(ctxAct)入口, recheck 先确认后投递, 取消零副作用。
    #    分支按**整行活性**锚定(精确缩进 + if/await/if(!ok) 结构) —— 注释包裹、短路禁用、
    #    挪出确认调用都会破坏匹配而变红; 裸字符串包含判定拦不住这些摘除形态(红验实测)。
    m = re.search(r"async bulkAct\(action\)\s*\{(.*?)\n    \},", cmds, re.S)
    assert m, "commands.js 找不到 bulkAct(改名或挪走了? 同步本守阵)"
    assert re.search(
        r'^      if \(action === "recheck"\) \{\n'
        r"        const ok = await this\._recheckConfirm\(.+\);\n"
        r"        if \(!ok\) return;\n"
        r"      \}$",
        m.group(1),
        re.M,
    ), "bulkAct 的 recheck 确认分支被摘除/改写 —— 批量右键重新校验恢复裸奔(计划 26-10-05-0314 S3; 接入点改写须同步本守阵)"

    # ④ 单选通道(torrentCmd): 单选右键与抽屉内命令入口, 只拦 recheck 其它命令不受影响
    # 2026-10-10(S3): 签名加第 4 参 hash(显式传参, 抽屉/键盘路径不再写 menu.hash 借道)
    m = re.search(
        r"async torrentCmd\(action, body = null, okText = \"\", hash = \"\"\)\s*\{(.*?)\n    \},", drawer, re.S
    )
    assert m, "drawer.js 找不到 torrentCmd(改名或挪走了? 同步本守阵)"
    assert re.search(
        r'^      if \(action === "recheck"\) \{\n'
        r"        const ok = await this\._recheckConfirm\(.+\);\n"
        r"        if \(!ok\) return;\n"
        r"      \}$",
        m.group(1),
        re.M,
    ), "torrentCmd 的 recheck 确认分支被摘除/改写 —— 单选右键/抽屉重新校验恢复裸奔(计划 26-10-05-0314 S3; 接入点改写须同步本守阵)"

    # ⑤ 键盘通道(_kbAct): 改调共用 helper(整行活性锚定), 不得再内联确认框文案
    m = re.search(r"async _kbAct\(action\)\s*\{(.*?)\n    \},", shortcuts, re.S)
    assert m, "shortcuts.js 找不到 _kbAct(改名或挪走了? 同步本守阵)"
    assert re.search(
        r"^        const ok = await this\._recheckConfirm\(what\);$",
        m.group(1),
        re.M,
    ), "_kbAct 未调共用 helper —— 键盘路径自成一份文案必漂移(计划 26-10-05-0314 S3)"
    assert 'confirmDialog("重新校验"' not in m.group(1), ("_kbAct 又内联了重新校验确认框文案 —— 应改调 commands.js _recheckConfirm")


def test_skip_check_dialog_precheck_wired():
    """跳检预检对话框接线守阵(T23, 计划 26-10-05-0314 S4)

    S4 把跳检确认框升级为三分流预检对话框: 共享 modal 扩展 okDisabled/busy/verdict 三字段,
    抽 _skipCheckDialog 取代 skipCheckTorrent/skipCheckMulti 两个各自为政的 _openModal。
    本守阵读 JS/模板源码钉住接线, 整行/整块活性锚定(T13 经验: 字符串包含拦不住突变),
    任一环被重构摘除即红:
    1. ui_feedback.js _modalInit 声明 okDisabled: false / busy: false / verdict: null
       (缺省零变化是「既有全部对话框不受影响」的根基);
    2. popovers.html 确认钮(modalOk)挂 :disabled="modal.okDisabled" 绑定 + busy 行 +
       verdict 行式渲染区(复用 modal-details 范式) + 强制钮仍走 extraText 第三钮
       (danger-solid 破坏性分支);
    3. drawer.js 两入口均交棒 _skipCheckDialog 且方法体内不再自带 _openModal;
    4. _skipCheckDialog 进框即 okDisabled:true + busy:true + verdict(固定警示区)并触发预检
       (_skipPrecheck 调 precheck 端点 + waitCmd 等回执)。
    """
    ui = open(os.path.join(STATIC_ROOT, "shared", "ui_feedback.js"), encoding="utf-8").read()
    tpl = open(os.path.join(STATIC_ROOT, "shared", "tpl", "popovers.html"), encoding="utf-8").read()
    drawer = read_shared("drawer.js")

    # ① _modalInit 三字段(缺省值即零变化契约: 改默认/删字段/改名都红)
    m = re.search(r"_modalInit\(\)\s*\{\s*return\s*\{(.*?)\n      \};", ui, re.S)
    assert m, "ui_feedback.js 找不到 _modalInit(改名或挪走了? 同步本守阵)"
    init = m.group(1)
    assert re.search(r"^        okDisabled: false, // ", init, re.M), \
        "_modalInit 缺 okDisabled: false 声明(确认钮禁用通道) —— 预检对话框状态机失锚"
    assert re.search(r"^        busy: false,\s+// ", init, re.M), \
        "_modalInit 缺 busy: false 声明(预检在途行) —— 预检对话框状态机失锚"
    assert re.search(r"^        verdict: null,\s+// ", init, re.M), \
        "_modalInit 缺 verdict: null 声明(三分流渲染区) —— 预检对话框状态机失锚"

    # ② 模板: 确认钮 :disabled 绑定(整钮块锚定 —— 绑定挪出 modalOk 钮或改静态值即红)
    m = re.search(r'<button ref="modalOk"[\s\S]*?</button>', tpl)
    assert m, "popovers.html 找不到 modalOk 确认钮(模板重构? 同步本守阵)"
    assert ':disabled="modal.okDisabled"' in m.group(0), \
        "modalOk 确认钮缺 :disabled=\"modal.okDisabled\" 绑定 —— 进框禁用/按态解锁失效(计划 26-10-05-0314 S4)"
    # busy 行(整行锚定)与 verdict 渲染区(行式明细; issue 26-10-20-2231 两套明细并一后,
    # 行表由 state.js::modalDetailRows 拼装 —— 消费面在此钉住, 单点本体由
    # test_frontend_dialog_shell_single_point 钉)
    assert '<p v-if="modal.busy" class="modal-body">正在检查前置条件…</p>' in tpl, \
        "popovers.html 缺预检 busy 行 —— 预检在途无反馈(计划 26-10-05-0314 S4)"
    assert '<div v-if="modalDetailRows.length" class="modal-details">' in tpl, \
        "popovers.html 缺 verdict 三分流渲染区(modal-details 行式范式)"
    assert 'v-for="d in modalDetailRows"' in tpl, "verdict 区缺行式 v-for 渲染"
    # 强制钮仍复用 extraText 第三钮通道(danger-solid 破坏性分支; 换自铸强制钮即红)
    assert re.search(r'<button v-if="modal\.extraText" class="bt danger-solid" @click="resolveModal\(\'extra\'\)">', tpl), \
        "第三钮(extraText 通道)被改写 —— S4 强制钮必须复用既有 danger-solid 破坏性分支"

    # ③ 两入口均交棒 _skipCheckDialog, 且方法体内不再自带 _openModal(确认框被取代)
    #    skipCheckMulti 现带可选 targets(单组右键 skipCheckGroup 复用同一状态机, 2026-10-09),
    #    故签名按"可选参"收 —— 只钉"入口存在且交棒"这一语义, 不钉参数表。
    for name in ("skipCheckTorrent", "skipCheckMulti"):
        m = re.search(rf"async {name}\([^)]*\)\s*\{{(.*?)\n    \}},", drawer, re.S)
        assert m, f"drawer.js 找不到 {name}(改名或挪走了? 同步本守阵)"
        assert "this._skipCheckDialog(" in m.group(1), \
            f"{name} 未走 _skipCheckDialog —— 预检对话框两入口共用的状态机被绕开(计划 26-10-05-0314 S4)"
        assert "_openModal" not in m.group(1), \
            f"{name} 仍自带 _openModal 确认框 —— 旧 danger 确认框应被预检对话框取代"

    # ④ _skipCheckDialog: 进框即禁用 + busy + 固定警示区 + 触发预检(调 _skipPrecheck)
    m = re.search(r"async _skipCheckDialog\(hashes, exec\)\s*\{(.*?)\n    \},", drawer, re.S)
    assert m, "drawer.js 找不到 _skipCheckDialog(S4 状态机被改名/挪走? 同步本守阵)"
    dlg = re.sub(r"//[^\n]*", "", m.group(1))  # 剥行注释后锚定代码结构(注释改写不红, 代码突变必红)
    assert "okDisabled: true" in dlg, "_skipCheckDialog 进框未禁用确认钮(预检回执前不得有可执行钮)"
    assert "busy: true" in dlg, "_skipCheckDialog 进框未置 busy(预检在途无反馈)"
    assert "verdict: warnRows" in dlg, "_skipCheckDialog 进框未挂固定警示区(case 3 不代表没有代价)"
    assert "this._skipPrecheck(seq" in dlg, "_skipCheckDialog 未触发预检投递"


def test_skip_check_dialog_verdict_render():
    """跳检预检三分流渲染逻辑守阵(T24, 计划 26-10-05-0314 S4)

    静态钉住 _skipPrecheck/_skipCheckDialog/_skipExec/_skipVerdictRows 的状态机语义,
    防渲染逻辑被改写出「blocked 仍可执行 / 降级态冒出强制钮 / 混合态送错子集」这类
    pytest 静态守阵之外只有真浏览器才看得见的回归:
    1. 六态分支(逐分支提取语句清单与期望比对, 剥注释滤空行): 预检失败降级=启用普通确认且无
       强制钮 / 含 blocked=确认强制双钮全收 / ok+force 混合=确认「跳检 N 个可跳检的」+强制
       「强制跳检全部」/ force-only=确认保持禁用只有强制钮 / 全 ok=只启用确认;
    2. ok 子集派生与提交口径: okHashes 只收 cls==="ok"; 确认路径送 ok 子集(降级送全量),
       强制路径送全量 + force=true(单发 body 仅 force 时带 force 键, 批量确认只走 hashes);
    3. 降级文案明示「后端闸门仍会在执行时拦截」(D10);
    4. 分组展示: 计数行(可跳检/需强制/禁止)+ 组内名称上限截断(slice(0,5)+等 X 个)。
    """
    drawer = read_shared("drawer.js")

    # ① 状态机六态分支: 逐分支提取语句清单(剥注释滤空行后)与期望逐一比对 ——
    #    摘除/新增/改写任一语句(如降级分支删掉解锁行、blocked 分支漏收强制钮)即红
    m = re.search(r"async _skipPrecheck\(seq, mid, hashes, warnRows\)\s*\{(.*?)\n    \},", drawer, re.S)
    assert m, "drawer.js 找不到 _skipPrecheck(S4 状态机被改名/挪走? 同步本守阵)"
    pre = re.sub(r"//[^\n]*", "", m.group(1))

    def _branch(head, nxt):
        bm = re.search(re.escape(head) + r"(.*?)" + re.escape(nxt), pre, re.S)
        assert bm, f"状态机分支锚点丢失: {head!r} -> {nxt!r}(分支结构被改写? 同步本守阵)"
        return [ln.strip() for ln in bm.group(1).splitlines() if ln.strip()]

    assert _branch("if (degraded) {", "} else if (counts.blocked) {") == [
        "this.modal.okDisabled = false;",
        'this.modal.extraText = "";',
    ], "降级分支(D10)被改写 —— 必须启用普通确认(okDisabled=false)且无强制钮(extraText 空)"
    assert _branch("} else if (counts.blocked) {", "} else if (counts.ok && counts.force) {") == [
        "this.modal.okDisabled = true;",
        'this.modal.extraText = "";',
    ], "含 blocked 分支被改写 —— blocked 硬闸: 确认/强制双钮全收, 不得产生任何可执行钮"
    assert _branch("} else if (counts.ok && counts.force) {", "} else if (counts.force) {") == [
        "this.modal.okDisabled = false;",
        "this.modal.okText = `跳检 ${counts.ok} 个可跳检的`;",
        "this.modal.extraText = `强制跳检全部 ${counts.ok + counts.force}`;",
    ], "ok+force 混合分支被改写 —— 确认钮只送 ok 子集文案, 强制钮送全量"
    assert _branch("} else if (counts.force) {", "} else {") == [
        "this.modal.okDisabled = true;",
        "this.modal.extraText = `强制跳检全部 ${counts.ok + counts.force}`;",
    ], "force-only 分支被改写 —— 确认保持禁用, 只有强制钮"
    fm = re.search(re.escape("} else if (counts.force) {") + r"(.*?)" + re.escape("} else {"), pre, re.S)
    assert fm, "force-only 分支锚点丢失(分支结构被改写? 同步本守阵)"
    tail_m = re.search(r"(.*?)\n      \}", pre[fm.end():], re.S)
    assert tail_m, "全 ok 分支锚点丢失(分支结构被改写? 同步本守阵)"
    assert [ln.strip() for ln in tail_m.group(1).splitlines() if ln.strip()] == [
        "this.modal.okDisabled = false;",
        "this.modal.okText = `跳检 ${counts.ok} 个`;",
        'this.modal.extraText = "";',
    ], "全 ok 分支被改写 —— 只启用确认(送全量不带 force), 无强制钮"
    # ok 子集派生: 只收 cls==="ok"(blocked/force 不进确认子集)
    assert 'okHashes = results.filter((x) => x.cls === "ok").map((x) => x.hash);' in pre, \
        "okHashes 未按 cls===\"ok\" 派生 —— 确认子集口径失守"
    # D10 降级文案(两处: 非 ok 回执 + 请求异常, 缺一即红)
    assert pre.count("后端闸门仍会在执行时拦截") == 2, \
        "降级文案「后端闸门仍会在执行时拦截」应恰好覆盖 非 ok 回执 与 请求异常 两分支"

    # ② 确认/强制两路径的提交口径(_skipCheckDialog 分派 + _skipExec 端点载荷)
    m = re.search(r"async _skipCheckDialog\(hashes, exec\)\s*\{(.*?)\n    \},", drawer, re.S)
    assert m, "drawer.js 找不到 _skipCheckDialog"
    dlg = re.sub(r"//[^\n]*", "", m.group(1))
    assert "return this._skipExec(exec, hashes, true);" in dlg, \
        "强制路径未送全量(hashes) —— 强制钮必须送全量 + force"
    assert "return this._skipExec(exec, v.degraded ? hashes : v.okHashes, false);" in dlg, \
        "确认路径未按 态送 ok 子集(降级送全量) —— 混合态把 force/blocked 目标混进普通确认即违背三分流"
    m = re.search(r"async _skipExec\(exec, hashes, force\)\s*\{(.*?)\n    \},", drawer, re.S)
    assert m, "drawer.js 找不到 _skipExec"
    exe = re.sub(r"//[^\n]*", "", m.group(1))
    assert "body: force ? JSON.stringify({ force: true }) : undefined" in exe, \
        "单发跳检 body 应仅在 force 时携带 force 键(缺省载荷与历史一致)"
    assert "keys: force ? exec.groupKeys : []" in exe and "hashes: force ? exec.memberHashes : hashes" in exe, \
        "批量跳检载荷口径失守: 确认=只送 ok 子集(hashes), 强制=keys+hashes 整份"
    assert "...(force ? { force: true } : {})" in exe, \
        "批量强制路径缺 force: true 透传(S2: 提供才入载荷)"

    # ③ 分组展示: 计数行 + 上限截断(5 + 等 X 个)
    m = re.search(r"_skipVerdictRows\(results\)\s*\{(.*?)\n    \},", drawer, re.S)
    assert m, "drawer.js 找不到 _skipVerdictRows"
    rows = re.sub(r"//[^\n]*", "", m.group(1))
    assert "`可跳检 ${ok.length} / 需强制 ${force.length} / 禁止 ${blocked.length}`" in rows, \
        "分组展示缺计数行(可跳检/需强制/禁止)"
    assert "g.names.slice(0, 5)" in rows, "分组行缺名称上限截断(5 个)"
    assert "等 ${g.names.length} 个" in rows, "分组行缺「等 X 个」尾注"


def test_modal_identity_stamp_landing_guard():
    """模态身份戳落袋守卫单点(F1-01, issue 26-10-06-0028) —— 迟到异步回执不得写进无关弹窗

    单例 modal 共用 this.modal, 落袋守卫只复核「seq + visible」兜不住: 用户取消跳检框后
    seq 不递增, 在回执到达前打开限速/重命名/删除确认等任意 modal, 回执落袋即覆写其
    verdict 与按钮文案。修法 = _openModal 每框发自增身份戳 mid, 落袋统一走 _modalIsCurrent
    单点(visible + mid 双比对) —— 本守阵静态钉住四处, 防「单例 modal + 异步落框」同形复发:
    1. ui_feedback.js _openModal 发戳(自增表达式必须内联在 modal 字面量里);
    2. ui_feedback.js _modalIsCurrent 单点存在且双条件齐全;
    3. drawer.js _skipCheckDialog 把 this.modal.mid 交棒 _skipPrecheck;
    4. drawer.js _skipPrecheck 落袋守卫 = seq 代际 + 身份戳, 且位于任何 this.modal 写之前。
    """
    drawer = read_shared("drawer.js")
    ui = open(os.path.join(STATIC_ROOT, "shared", "ui_feedback.js"), encoding="utf-8").read()

    # ① _openModal 发戳: mid 自增必须随 modal 字面量一同创建(后补属性不进 Vue 响应的旧坑)
    m = re.search(r"_openModal\(cfg\)\s*\{(.*?)\n    \},", ui, re.S)
    assert m, "ui_feedback.js 找不到 _openModal(改名或挪走了? 同步本守阵)"
    assert re.search(
        r"this\.modal = \{[^}]*mid: \(this\._modalSeq = \(this\._modalSeq \|\| 0\) \+ 1\)", m.group(1)
    ), "_openModal 未随框发自增身份戳 mid —— 异步落框守卫失锚(F1-01)"

    # ② 守卫单点: visible + mid 双比对(mid 缺省/框已关/被新框取代一律失配)
    m = re.search(r"_modalIsCurrent\(mid\)\s*\{(.*?)\n    \},", ui, re.S)
    assert m, "ui_feedback.js 找不到 _modalIsCurrent(守卫单点被摘除? 同步本守阵)"
    body = re.sub(r"//[^\n]*", "", m.group(1))
    assert "this.modal.visible" in body and "this.modal.mid === mid" in body, \
        "_modalIsCurrent 必须同时复核 visible 与 mid(缺一不可)"

    # ③ 交棒: _skipCheckDialog 发预检时携带本框身份戳
    assert "this._skipPrecheck(seq, this.modal.mid, hashes, warnRows)" in drawer, \
        "_skipCheckDialog 未把 modal 身份戳交棒 _skipPrecheck(F1-01)"

    # ④ 落袋守卫: seq 代际 + _modalIsCurrent, 且在首处 this.modal 写之前
    m = re.search(r"async _skipPrecheck\(seq, mid, hashes, warnRows\)\s*\{(.*?)\n    \},", drawer, re.S)
    assert m, "drawer.js 找不到 _skipPrecheck(签名被改? 同步本守阵)"
    pre = re.sub(r"//[^\n]*", "", m.group(1))
    guard = re.search(r"if \(seq !== this\._skipCheckSeq \|\| !this\._modalIsCurrent\(mid\)\) return;", pre)
    assert guard, "落袋守卫缺身份戳条件(F1-01: 只有 seq 兜不住取消后开无关 modal 的分支)"
    assert pre.index(guard.group(0)) < pre.find("this.modal.busy = false"), \
        "守卫必须前置 —— 迟到回执在守卫通过前不得写任何 this.modal 字段"


def test_frontend_ctx_menu_multi_select_targets_selection():
    """多选右键菜单必须作用于**整个选中集合**, 不是被点的那一行(CTX-03)

    用户报: "多选时右键菜单应该对所有选择的种子生效, 当前仅对鼠标指向的触发右键的种子生效"。
    根因: 四个 open*Menu 只记 anchor(key/hash/episode), 动作端点直接拿它拼 URL ⇒ 无论选了多少,
    都只动被点的那一个。而批量浮条早已有正确实现(bulkAct/bulkDelete 走 _bulkTargets)。

    修法是让菜单在"被点的行属于选中集合"时升级为批量菜单, 动作复用批量浮条的链路。这条守阵
    钉住三处**成对**关系(任一处漏改都会静默退化回单目标, 且 pytest/`node --check` 都看不见):
      1. 四个 open*Menu 必须各自写入 `multi:` —— 漏一处, 那条路径的多选右键就仍是单目标;
      2. 三套 UI 的行菜单都必须存在且消费注册表 `ctxItems(ctxMenuKind())`(W3 起项集/分派在
         shared/ctx_menu.js 注册表单点, 三 UI 同指 /shared/tpl/ctx-menus.html 一份 = 漂移
         结构性不可能; 2026-10-22 issue 26-10-20-2231 起四支骨架合并为一条, 批量支不再有
         独立的 template 段 —— 比对面换成"根块消费 ctxMenuKind() 单点 + 段内无逐项直写");
         注册表 multi 支只能调 ctxAct/ctxDelete;
      3. ctxAct/ctxDelete 必须**复用** bulkAct/bulkDelete —— 自己再拆一遍目标集合就会与批量浮条
         的口径漂移(虚拟行/组展开/失效目标跳过这三条语义都在 _bulkTargets 里)。
    """
    # 1. 四个菜单入口都必须写 multi
    openers = {
        "shared/menu.js": ["openMenu(event, group)", "openMemberMenu(event, member)"],
        "shared/shows.js": ["openShowEpMenu(event, show, ep)", "openShowMenu(event, show)"],
    }
    for rel, fns in openers.items():
        text = open(os.path.join(STATIC_ROOT, rel), encoding="utf-8").read()
        for fn in fns:
            m = re.search(rf"\n    {re.escape(fn)} \{{(.*?)\n    \}},", text, re.S)
            assert m, f"{rel} 找不到 {fn}(改名或挪走了? 同步本守阵)"
            body = m.group(1)
            assert "_ctxMulti(" in body, (
                f"{rel} 的 {fn} 没有调 _ctxMulti 计算 menu.multi —— 该路径的多选右键会退化成"
                f"只作用于被点的那一行(CTX-03)"
            )
            assert "multi:" in body, f"{rel} 的 {fn} 没把 multi 写进 this.menu —— 模板读不到, 批量分支永不渲染"

    # 2. 三套 UI 的行菜单都必须消费注册表; 项集/分派在注册表单点(shared/ctx_menu.js,
    #    三 UI 同指 /shared/tpl/ctx-menus.html = 双 UI 漂移结构性不可能; W3 起逐项分派从
    #    模板文本搬进注册表 act —— 比对面随之搬家, 治的是同一件事)。
    #    2026-10-22(issue 26-10-20-2231-refactor-fe-tpl-ctx-item-branch-dup): 四支各一份骨架
    #    合并为 ctxItems(ctxMenuKind()) 一条, 批量支不再有独立 <template v-if="menu.multi"> 段
    #    —— 比对面从"批量分支段"换成"行菜单根块消费 ctxMenuKind() 单点 + 段内无逐项直写"。
    for ui in _UI_ALL:
        text = _ui_aggregate(ui)
        assert "<!-- 表头右键菜单" in text, f"{ui}/index.html 找不到行右键菜单段锚点(模板分片变了? 同步本守阵)"
        row = text[:text.index("<!-- 表头右键菜单")]
        assert "ctxItems(ctxMenuKind())" in row, (
            f"{ui}/index.html 的行右键菜单没有消费注册表 ctxItems(ctxMenuKind()) —— "
            f"多选右键拿不到批量动作(三 UI 必须成对改, 另一套有而它没有 = 半边用户没有该功能)"
        )
        assert "actTorrent(" not in row and "actEpisode(" not in row, (
            f"{ui}/index.html 行菜单段出现了单目标/单集动作直写 —— 分派必须整份走注册表 act"
            f"(批量支走 ctxAct/ctxDelete, CTX-03)"
        )
    # 注册表 multi 支: 五个批量动作 + ctxDelete 必须在, 且只能调 ctxAct/ctxDelete
    reg = open(os.path.join(STATIC_ROOT, "shared", "ctx_menu.js"), encoding="utf-8").read()
    seg = re.search(r"\n    multi: \[(.*?)\n    \],", reg, re.S)
    assert seg, "ctx_menu.js 找不到 multi 支定义段(注册表结构变了? 同步本守阵)"
    multi_defs = seg.group(1)
    for call in (
        'vm.ctxAct("resume")', 'vm.ctxAct("pause")', 'vm.ctxAct("reannounce")', 'vm.ctxAct("recheck")', 'vm.ctxDelete()'
    ):
        assert call in multi_defs, f"注册表 multi 支缺少 {call}(批量菜单项集漂移, CTX-03)"
    for bad in ("vm.actTorrent(", "vm.actEpisode(", "vm.delTorrent(", "vm.delEpisode(", "vm.act("):
        assert bad not in multi_defs, (f"注册表 multi 支出现单目标分派 {bad} —— 批量菜单必须整份走 ctxAct/ctxDelete")

    # 3. ctxAct/ctxDelete 复用批量浮条链路, 且先收起菜单(菜单根节点 @click.stop, 全局点空白关不掉)
    cmd = read_shared("commands.js")
    for name, delegate in (("ctxAct(action)", "bulkAct(action)"), ("ctxDelete()", "bulkDelete()")):
        m = re.search(rf"\n    {re.escape(name)} \{{(.*?)\n    \}},", cmd, re.S)
        assert m, f"shared/commands.js 找不到 {name}(改名或挪走了? 同步本守阵)"
        body = m.group(1)
        assert delegate in body, (
            f"{name} 必须复用批量浮条的 {delegate} —— 自己再拆一遍目标集合会与 _bulkTargets 的"
            f"口径漂移(虚拟行/组展开/失效目标跳过), CTX-03"
        )
        assert "this.menu.visible = false" in body, f"{name} 必须先收起右键菜单(菜单是 @click.stop, 全局点空白关不掉)"


def test_frontend_ctx_menu_group_actions_parity():
    """单组右键菜单与多选批量菜单「动作项集一致」守阵(2026-10-09 用户报「单组右键菜单缺选项」)

    单组菜单(menu.key 的 v-else 分支)此前只有 开始/暂停/汇报 + 打开文件夹/流量图/删除, 而多选
    批量菜单(menu.multi 分支)还有 重新校验/跳检/限速/移动/标签分类/导出 —— 同一批动作在
    「右键 1 组」与「选 2 组」两条路径上项集不一致(用户报「单组右键菜单缺选项, 参考选中多组」)。
    本守阵钉三处(任一处漂移即静默少一个入口, pytest/node --check 都看不见):
      1. 单组支必须含六个组级入口(与批量分支同项集; 组菜单独有的 打开文件夹/流量图 除外);
      2. 跳检项必须吃 flags.skip_check_menu 门控(fail-closed, 与单选/批量两处同口径);
      3. 六个入口方法必须在 commands.js/drawer.js 落地且复用多选同一套下游链路
         (recheckGroup->_actCore / 限速移动跳检->drawer.js 多选对话框 / metaGroup->openMetaDialog /
          exportGroup->_exportHashes), 不为组级另开旁路。
    W3(计划 26-10-20-0024)起四支项集搬到注册表单点: 模板只按支名取项(ctxItems(支)), 项集/
    门控/分派在 ctx_menu.js group 支定义段 —— 比对面随之搬家。
    2026-10-22(issue 26-10-20-2231-refactor-fe-tpl-ctx-item-branch-dup): 四支各一份骨架合并为
    一条 `ctxItems(ctxMenuKind())` v-for, 单组支不再是独立的 `<template v-else>` 段 ——
    "模板只消费注册表"这条断言改挂 ctxMenuKind() 单点, 项集比对面(下面三处)一字不动。
    """
    tpl = open(os.path.join(STATIC_ROOT, "shared", "tpl", "ctx-menus.html"), encoding="utf-8").read()
    assert "ctxItems(ctxMenuKind())" in tpl, (
        "ctx-menus.html 行菜单未消费注册表 ctxItems(ctxMenuKind()) —— 回退逐项直写 = "
        "四支人肉奇偶复发(2026-10-09 报障: 单组缺选项)"
    )
    reg = open(os.path.join(STATIC_ROOT, "shared", "ctx_menu.js"), encoding="utf-8").read()
    seg = re.search(r"\n    group: \[(.*?)\n    \],", reg, re.S)
    assert seg, "ctx_menu.js 找不到 group 支定义段(注册表结构变了? 同步本守阵)"
    group = seg.group(1)

    # 1. 六个组级入口(与多选批量菜单同项集)
    for token in (
        "vm.recheckGroup()", "vm.skipCheckGroup()", "vm.editLimitsGroup()", "vm.editMoveGroup()", "vm.metaGroup()",
        "vm.exportGroup()"
    ):
        assert token in group, (f"注册表 group 支缺少 {token} —— 与多选批量菜单项集不一致(2026-10-09 报障: 单组缺选项)")

    # 2. 跳检项 fail-closed 门控(注册表 gate: "skip_check_menu"; flags 关 = 渲染层不出该项,
    #    与单选/批量两处同口径; 门在 ctx_menu.js CTX_GATE_FLAG 单点映射)
    skip_line = next((ln for ln in group.splitlines() if "vm.skipCheckGroup()" in ln), "")
    assert skip_line and 'gate: "skip_check_menu"' in skip_line, (
        "单组菜单「跳检…」项缺 skip_check_menu 门控(注册表 gate) —— 关态仍渲染 = fail-closed 破口"
    )

    # 3. 六个入口方法落地 + 复用多选同一套下游链路
    cmd = read_shared("commands.js")
    drw = read_shared("drawer.js")
    assert "_groupTargets()" in cmd, "commands.js 缺 _groupTargets(组级目标集合单点)"
    # 2026-10-10(S3): _groupTargets 退化为 _scopeResolve("anchor") 的投影, 成员展开单点
    # (memberHashesOf)随之收进 selection.js::_selExpandGroups —— 守阵跟着搬家, 语义不变
    assert '_scopeResolve("anchor", { kind: "group", id: k })' in cmd, (
        "commands.js _groupTargets 必须走作用域单点 _scopeResolve(口径收敛, 计划 26-10-10-2001 S3)"
    )
    selsrc = open(os.path.join(STATIC_ROOT, "shared", "selection.js"), encoding="utf-8").read()
    exg = re.search(r"_selExpandGroups\(groupKeys, bag\) \{(.*?)\n    \},", selsrc, re.S)
    assert exg and "this.memberHashesOf(" in exg.group(1), (
        "selection.js _selExpandGroups 未走 memberHashesOf 单点(成员对象直接取 .hash 会被静态守阵拦下)"
    )
    for name in ("recheckGroup", "editLimitsGroup", "editMoveGroup", "skipCheckGroup", "metaGroup", "exportGroup"):
        assert re.search(rf"\n    (?:async )?{name}\(", cmd), f"commands.js 缺组级入口 {name}"
    for delegate in (
        "this.editLimitsMulti(", "this.editMoveMulti(", "this.skipCheckMulti(", "this.openMetaDialog(",
        "this._exportHashes(", "this._actCore("
    ):
        assert delegate in cmd, f"commands.js 组级入口未复用 {delegate}(另开了旁路?)"
    for sig in ("editLimitsMulti(targets = null", "editMoveMulti(targets = null", "skipCheckMulti(targets = null"):
        assert sig in drw, f"drawer.js 缺 {sig}...) 可选 targets 形参 —— 组级入口无法复用同一状态机"


def test_frontend_meta_dialog_paired():
    """标签/分类编辑对话框守阵(静态防回潮)

    对选中集合(或单种子)即时增删标签/改分类。风险形态与批量菜单守阵(CTX-03)同源:
      1. 三套 UI 成对: 对话框与两处菜单入口缺一边 = 那套用户没有入口(W3 计划 26-10-20-0024
         起菜单入口搬到共享注册表单点 shared/ctx_menu.js, 三 UI 同指一份模板 = 结构性成对);
      2. 对话框的投递必须走 bulk 链路(/api/torrents/bulk), 目标集合口径单点在
         _bulkTargets/openMetaDialog —— 自己再拆一遍就会与批量浮条口径漂移;
      3. .opt-pill(atlas 此前没有该组件)与 .meta-dialog 的 CSS 必须两套成对定义,
         模板用到的类在 CSS 无定义 = 静默裸样式(挂件类名错配的变体)。
    """
    # 1. 三套 UI 成对: metaOpen 对话框 + 两处入口(W3 计划 26-10-20-0024 起菜单入口搬到
    #    注册表单点: 批量支 ctxMeta / 单种子支 openMetaDialog(menu.hash); shared/ctx_menu.js
    #    三 UI 同指一份 = 成对结构性保证, 逐项分派不再散在双模板各自演化)
    #    (2026-10-05 批量控制条退役: 模板层不再直接调 openMetaDialog(null), 批量入口统一走 ctxMeta)
    for ui in _UI_ALL:
        text = _ui_aggregate(ui)
        assert ':open="metaOpen"' in text, f"{ui}/index.html 缺少标签/分类对话框(三套 UI 必须成对改)"
        assert "openMetaDialog(null)" not in text, (
            f"{ui}/index.html 又出现模板层直接调 openMetaDialog(null) —— 批量控制条已退役, "
            f"批量入口应统一走 ctxMeta(右键批量菜单)"
        )
    reg = open(os.path.join(STATIC_ROOT, "shared", "ctx_menu.js"), encoding="utf-8").read()
    assert "vm.openMetaDialog(vm.menu.hash)" in reg, ("注册表 member 支缺单种子右键菜单的标签/分类入口(openMetaDialog(vm.menu.hash))")
    assert "vm.ctxMeta()" in reg, "注册表 multi 支缺批量右键菜单的 ctxMeta 入口"
    # 2. shared 逻辑接线(逻辑层两套共用, 只在 shared 出现)
    dlg = read_shared("dialogs.js")
    for token in (
        "openMetaDialog(singleHash)",
        "closeMeta()",
        "_metaBulk(action, extra, okText)",
        "metaToggleTag(tag)",
        "metaAddNewTags()",
        "metaSetCategory(name)",
        "_bulkTargets()",
        "/api/torrents/bulk",
    ):
        assert token in dlg, f"shared/dialogs.js 缺少 {token}(改名或挪走了? 同步本守阵)"
    cmd = read_shared("commands.js")
    m = re.search(r"\n    ctxMeta\(\) \{(.*?)\n    \},", cmd, re.S)
    assert m, "shared/commands.js 找不到 ctxMeta(改名或挪走了? 同步本守阵)"
    assert "this.menu.visible = false" in m.group(1), ("ctxMeta 必须先收起右键菜单(菜单是 @click.stop, 全局点空白关不掉)")
    assert "openMetaDialog(null)" in m.group(1), ("ctxMeta 必须复用 openMetaDialog 打开对话框 —— 目标集合口径单点在它里面")
    # 3. CSS 成对: .meta-dialog 与 .opt-pill 各套 UI 都要有定义(flux 收编 S5)
    for name, t in (
        ("atlas css 聚合(link 序)", _ui_css_aggregate("atlas")),
        (
            "prism/css/dialogs.css", open(os.path.join(STATIC_ROOT, "prism", "css", "dialogs.css"),
                                          encoding="utf-8").read()
        ),
        ("console css 聚合(link 序)", _ui_css_aggregate("console")),
        ("flux css 聚合(link 序)", _ui_css_aggregate("flux")),
    ):
        assert ".meta-dialog" in t, f"{name} 缺少 .meta-dialog 定义"
        assert ".opt-pill" in t, f"{name} 缺少 .opt-pill 定义(atlas 此前没有该组件, 易漏)"


def test_frontend_add_torrent_drag_drop_wiring():
    """DND-01 全局拖拽添加种子接线守阵(静态防回潮)

    拖拽进料口的关键点全在 JS/HTML 静态结构里, pytest 运行时看不见:
      1. window 级 drag 事件四件套(dragenter/dragover/dragleave/drop) add/remove 严格对称
         —— 漏 remove = 卸载后幽灵监听重复 ingest;
      2. drop handler 必须 preventDefault —— 删掉它浏览器会直接打开 .torrent / 跳转链接,
         表现为"拖进去弹出的是文件内容页";
      3. 接管判据只认 "Files"/"text/uri-list" —— 若放宽到 text/plain, 页面内拖选中文本、
         拖词进输入框的原生行为会被误拦;
      4. 双 UI 的落点遮罩成对存在(v-if="addDragOver"), app.js 有 addDragOver 状态 ——
         只改一套皮肤 = 另一套用户拖了没反应。
    """
    import re

    add_js = open(os.path.join(STATIC_ROOT, "shared", "add_torrent.js"), encoding="utf-8").read()
    # 1. 四件套 add/remove 对称
    added, removed = set(), set()
    for hook, bucket in (("mounted", added), ("unmounted", removed)):
        m = re.search(rf"\n  {hook}\(\) \{{(.*?)\n  \}},", add_js, re.S)
        assert m, f"add_torrent.js 找不到 {hook} 钩子(DND-01 监听挂载点, 改名或挪走了? 同步本守阵)"
        for ev in re.findall(r'window\.(?:add|remove)EventListener\("([a-z]+)"', m.group(1)):
            bucket.add(ev)
    expect = {"dragenter", "dragover", "dragleave", "drop"}
    # 子集语义: mounted 还合法挂了 label 失焦收层守卫的 mousedown capture 记录器(四轮, 2026-10-04),
    # 不能再断言"恰好等于四件套" —— 只要求四件套一个不少, 多余监听交给 removed == added 对称性兜住。
    assert expect <= added, f"mounted 缺 drag 事件: {expect - added}(少一个就有一条路径不接管)"
    assert removed == added, f"unmounted 与 mounted 不对称: add={sorted(added)} / remove={sorted(removed)}"

    # 2. drop handler 必须拦默认行为 + depth 归零灭遮罩
    m = re.search(r"\n    _addDragDrop\(e\) \{(.*?)\n    \},", add_js, re.S)
    assert m, "add_torrent.js 找不到 _addDragDrop(drop 分流入口, 改名或挪走了? 同步本守阵)"
    assert "preventDefault()" in m.group(1
                                        ), ("_addDragDrop 少了 preventDefault —— 浏览器会直接打开 .torrent/链接而不是交给添加对话框(DND-01)")

    # 3. 接管判据只认文件与链接, 不得放宽到 text/plain
    m = re.search(r"\n    _addDragTakes\(e\) \{(.*?)\n    \},", add_js, re.S)
    assert m, "add_torrent.js 找不到 _addDragTakes(接管判据, 改名或挪走了? 同步本守阵)"
    takes = m.group(1)
    assert 'types.includes("Files")' in takes and 'types.includes("text/uri-list")' in takes, (
        "_addDragTakes 必须显式认 Files 与 text/uri-list(接管面收窄到拖文件/拖链接)"
    )
    assert "text/plain" not in takes, ("_addDragTakes 不得认 text/plain —— 会误拦页面内拖选中文本/拖词进输入框的原生行为(DND-01)")

    # 4. app.js 状态 + 双 UI 遮罩成对
    app_js = _app_bundle_text()
    assert "addDragOver: false" in app_js, "app.js 缺 addDragOver 状态(遮罩显隐没有数据源)"
    for ui in _UI_ALL:
        html = _ui_aggregate(ui)
        assert 'class="add-drop-mask"' in html and 'v-if="addDragOver"' in html, (
            f"{ui}/index.html 缺拖拽落点遮罩(.add-drop-mask + v-if=\"addDragOver\")—— "
            f"该皮肤用户拖文件进页面没有落点反馈(双 UI 必须成对改)"
        )


def test_frontend_add_torrent_partial_receipt_wiring():
    """添加种子「部分受理关窗」回执分流守阵(2026-10-18 用户报障: 部分种子添加失败(已存在)时
    添加窗口不消失)

    症状根因: 后端旧口径把"部分受理"(qB 对重复种子整批里挑着拒, HTTP 200 + failure_count>0)
    折叠进 error 回执, 前端 submitAddTorrent 只认 r.ok 关窗 ⇒ 明明加进去几个, 窗口赖着不动
    还报"添加种子失败"。修法 = 后端三态回执(ok/warn/error, commands.py::_cmd_add_torrents) +
    前端按 r.status 分流。行为面(pytest 运行时不可见)由 e2e/add-partial-receipt.spec.mjs 真浏览器钉,
    本守阵钉静态接线:
      1. submitAddTorrent 必须按三态分流 —— 有 `r.status === "warn"` 分支(只判 r.ok 即回潮);
      2. warn 分支必须关窗(addOpen = false)并以 warn 类 toast 给出详情(后端文案带计数);
      3. ok 分支保持关窗;
      4. error(全拒)分支**不得**关窗 —— 那一份文件/链接原样没进 qB, 留窗才能改完重提
         (部分成功与全部失败混为一谈是本案病根, 两个方向都钉)。
    """
    import re

    add_js = open(os.path.join(STATIC_ROOT, "shared", "add_torrent.js"), encoding="utf-8").read()
    m = re.search(r"\n    async submitAddTorrent\(\) \{(.*?)\n    \},", add_js, re.S)
    assert m, "add_torrent.js 找不到 submitAddTorrent(提交入口, 改名或挪走了? 同步本守阵)"
    body = m.group(1)

    # 1. 三态分流: warn 分支在(只判 r.ok 的二态写法回潮即红)
    assert 'r.status === "warn"' in body, (
        "submitAddTorrent 缺 r.status === \"warn\" 分支 —— 部分受理被 error 化, 窗口不消失(2026-10-18 报障)"
    )
    # 2. warn 分支: 关窗 + warn 类 toast(详情由后端文案带出, 见 commands.py 三态回执)
    # (缩进锚 10 空格: R4 存量评审 P04 把提交闸 addSubmitting 前置、整个提交段外包 try/finally, 缩进 +2)
    warn_branch = re.search(r'\} else if \(r\.status === "warn"\) \{(.*?)\n          \} else \{', body, re.S)
    assert warn_branch, "warn 分支结构被改写(else if 链形状变了? 同步本守阵)"
    assert "this.addOpen = false" in warn_branch.group(1), ("warn 分支不关窗 —— 部分受理时添加窗口仍留在前台(本案报障原状)")
    assert '"warn", 8000' in warn_branch.group(1), ("warn 分支未以 warn 类 toast 给出部分失败详情(TOAST_MS_FLOOR: warn 停留下限 8s)")
    # 3. ok 分支保持关窗
    ok_branch = re.search(r"if \(r\.ok\) \{(.*?)\n          \} else if", body, re.S)
    assert ok_branch and "this.addOpen = false" in ok_branch.group(1), "ok 分支不关窗(全受理时窗口应消失)"
    # 4. error(全拒)分支不得关窗
    err_branch = re.search(r"\n          \} else \{\n(.*?)\n          \}", body, re.S)
    assert err_branch, "submitAddTorrent 找不到末尾 else(全拒)分支"
    assert "addOpen" not in err_branch.group(1), ("error(全拒)分支关了窗 —— 那一份文件/链接原样没进 qB, 关窗用户就没法改完重提了")


def test_frontend_add_combo_blur_close_and_fit():
    """添加种子三下拉「失焦即收 + 限高不出窗」接线守阵(2026-10-03 报障, 静态防回潮)

    两个用户可见故障形态, 根因都在事件接线/几何量测这类 pytest 运行时看不见的地方:
      1. **点窗口其它位置下拉不收 / 闪烁重现**: 收层判据原来只有 window click(lifecycle.js),
         点字段 label(for= 转发激活)时浏览器先 blur 再把焦点转回输入框, click 关层 + 转发
         click 重开 = 关了又开(leave 过渡被打断 = 闪烁)。修法 = 收层主判据改 @focusout,
         但**不能同步收** —— 必须 40ms 合帧守卫(焦点回来由开层方法撤销), 否则闪烁回潮。
      2. **选项过长把窗口撑变形**: .pop-menu 基础 max-height 只保证菜单自身可滚, 菜单锚在
         输入行下方, 绝对定位溢出会伸出窗口外并把 .add-dialog-body 的 scrollHeight 撑大。
         修法 = 开层时把可滚内层限到「输入行 → 滚动容器可见底沿」的净空内(滚动条留在窗口里)。
    """
    import re

    at = open(os.path.join(STATIC_ROOT, "shared", "add_torrent.js"), encoding="utf-8").read()
    mgr = open(os.path.join(STATIC_ROOT, "shared", "tpl", "dialogs-mgr.html"), encoding="utf-8").read()
    xt = open(os.path.join(STATIC_ROOT, "shared", "tpl", "combo-input.html"), encoding="utf-8").read()

    # 1. 三个输入框全部挂失焦收层(收敛 issue 26-10-20-2230: 输入框骨架进共享组件
    #    #tpl-combo-input(独立分片 combo-input.html), 字段级接线在调用点) —— 漏一个 = 那个下拉点空白不收
    tpl_seg = re.search(r'id="tpl-combo-input">([\s\S]*?)</script>', xt, re.S)
    assert tpl_seg, "combo-input.html 找不到 #tpl-combo-input(combobox 共享模板, 改名或挪走了? 同步本守阵)"
    assert '@focusout="$emit(\'blur\')"' in tpl_seg.group(1), \
        "组件模板缺 @focusout=\"$emit('blur')\"(失焦即收是收层主判据, 组件内漏挂 = 五个下拉全不收)"
    for input_id in ("ad-save-path", "ad-category", "ad-tags"):
        m = re.search(rf'<aq-combo-input input-id="{input_id}"(.*?)>', mgr, re.S)
        assert m, f"dialogs-mgr.html 找不到 #{input_id}(添加窗口三下拉的输入框, 改名或挪走了? 同步本守阵)"
        assert '@blur="addPopBlurClose"' in m.group(1), \
            f"#{input_id} 缺 @blur=\"addPopBlurClose\"(失焦即收是收层主判据, 漏挂 = 该下拉点窗口其它位置不收)"

    # 2. 失焦收层必须带合帧守卫: 40ms 合帧 + _popBlurShouldHold 收敛在 _popBlurArm 单点
    #    (同步收层会被 label 的焦点转回打断 = 闪烁回潮); addPopBlurClose 是薄封装
    arm = re.search(r"_popBlurArm\(timerKey, ids, close\) \{(.*?)\n    \},", at, re.S)
    assert arm, "add_torrent.js 找不到 _popBlurArm(失焦收层合帧单点, 改名或挪走了? 同步本守阵)"
    assert "setTimeout" in arm.group(1) and "clearTimeout" in arm.group(1), \
        "_popBlurArm 必须用定时器合帧(同步收层 + label 转发回焦 = 关了又开闪烁); 定时窗内焦点回来由开层方法撤销"
    assert "COMBO_BLUR_CLOSE_MS" in arm.group(1), \
        "_popBlurArm 漏用 COMBO_BLUR_CLOSE_MS 单点常量(合帧窗改数值要三处同改, 收敛后只剩这一处)"
    assert "_popBlurShouldHold(ids)" in arm.group(
        1
    ), "_popBlurArm 收层前没问守卫(见 test_frontend_add_combo_label_clear_mask_and_refit 第 7 节)"
    body = re.search(r"addPopBlurClose\(\) \{(.*?)\n    \},", at, re.S)
    assert body, "add_torrent.js 找不到 addPopBlurClose(失焦收层入口薄封装)"
    for field in ("addCatMenu", "addTagMenu", "addPathPop"):
        assert f"this.{field} = false" in body.group(1), f"addPopBlurClose 漏收 {field}"

    # 3. 三个开层方法先撤销挂起的收层(焦点回到输入框 = 菜单保持, 不闪)
    for fnname in ("openAddCatMenu", "openAddTagMenu", "openAddPathPop"):
        body = re.search(rf"{fnname}\(\) \{{(.*?)\n    \}},", at, re.S)
        assert body and '_popBlurCancel("_addPopBlurT")' in body.group(1), \
            f"{fnname} 必须先 _popBlurCancel(\"_addPopBlurT\")(焦点转回输入框时撤销挂起的失焦收层, 否则菜单闪烁)"

    # 4. 限高: 开层 watcher 单点(开层入口有四处, 直挂方法会漏) + 量「行→滚动容器可见底沿」净空
    for token in ("addCatMenu(v) {", "addTagMenu(v) {", "addPathPop(v) {"):
        assert token in at, f"add_torrent.js 缺 watcher {token}(开层限高必须走 watcher 单点, 四处开层入口直挂会漏)"
    fit = re.search(r"_fitAddPop\(refName\) \{(.*?)\n    \},", at, re.S)
    assert fit, "add_torrent.js 找不到 _fitAddPop(下拉限高单点, 改名或挪走了? 同步本守阵)"
    fit_body = fit.group(1)
    assert 'closest(".add-input-row")' in fit_body and 'closest(".add-dialog-body")' in fit_body, \
        "_fitAddPop 必须以输入行为锚、以 .add-dialog-body 可见底沿为界量净空(以视口为界会在窗口化/滚动时量错)"
    assert 'list.style.maxHeight = ""' in fit_body, \
        "_fitAddPop 限高前必须先复位旧值(上一次的限高会污染本次测量)"

    # 5. 候选异步到位会改变菜单高度, 开着时也要重限
    for opt in ("addCatOptions", "addTagOptions", "addPathOptions"):
        assert re.search(rf"{opt}\(\) \{{\n      if \(this\.", at), \
            f"add_torrent.js 缺 {opt} 的 watcher(候选异步到位改变菜单高度, 开着时必须重限)"

    # 6. 三浮层互斥必须双向(26-10-04-0130): 开层收别家走 closeAddPopsExcept 单点 —— 单向写法
    #    (只 openAddPathPop 收 cat/tag, 反向不收)会让路径面板与下拉同悬, 且面板盖住相邻字段
    #    label 的点击(走查实测 "subtree intercepts pointer events")
    mutex = re.search(r"closeAddPopsExcept\(kind\) \{(.*?)\n    \},", at, re.S)
    assert mutex, "add_torrent.js 找不到 closeAddPopsExcept(三浮层互斥单点, 改名或挪走了? 同步本守阵)"
    mutex_body = mutex.group(1)
    for field, kind_key in (("addCatMenu", "cat"), ("addTagMenu", "tag"), ("addPathPop", "path")):
        assert f'kind !== "{kind_key}"' in mutex_body, \
            f"closeAddPopsExcept 缺 {field} 分支(互斥单点必须覆盖全部三个浮层)"
    for fnname, kind in (("openAddCatMenu", "cat"), ("openAddTagMenu", "tag"), ("openAddPathPop", "path")):
        body = re.search(rf"{fnname}\(\) \{{(.*?)\n    \}},", at, re.S)
        assert body and f'closeAddPopsExcept("{kind}")' in body.group(1), \
            (f"{fnname} 必须调 closeAddPopsExcept(\"{kind}\") —— 开本浮层时收掉其余两个, "
             f"互斥漏一侧 = 双浮层同悬且盖住相邻字段 label 的点击")


def test_frontend_combo_hiscroll_never_scrolls_ancestors():
    """combobox 高亮滚动跟随「只滚菜单内部」守阵(2026-10-29 八修, 静态防回潮)

    症状(用户报): 选中过一条新路径后再点下拉框, 弹窗里的说明文案**从上往下滑一次**; 输入框为空时正常。
    根因: `_hiScroll` 用 `el.scrollIntoView({block:'nearest'})` —— 它会把**所有可滚祖先**一起滚, 而
    `.add-dialog-body` 正是 overflow-y 容器, 开层过渡期其 scrollHeight 比 clientHeight 大 166px
    (实测 body.scrollTop `0 → 166 → 83 → 18 → 0`, 文案 top `352 → 186 → 269 → 334`)。空输入时
    hi = -1、没有 `[data-hi="1"]`, 所以只有"已选中过路径"才看得见 —— 与用户描述逐字吻合。
    修法 = 手动差值调 scrollTop, 且**只动菜单内部**那层(逐级向上, 到菜单根即止); 与 26-09-29-2142
    (键盘光标滚动跟随)同一条禁令: 禁 scrollIntoView, 它会连带滚整页。
    """
    import re

    at = open(os.path.join(STATIC_ROOT, "shared", "add_torrent.js"), encoding="utf-8").read()
    m = re.search(r"_hiScroll\(refName\) \{(.*?)\n    \},", at, re.S)
    assert m, "add_torrent.js 找不到 _hiScroll(高亮滚动跟随单点, 改名或挪走了? 同步本守阵)"
    # 只查**真代码**: 注释里讲原理(「禁用 scrollIntoView」)不算违规
    body = re.sub(r"^\s*//.*$", "", re.sub(r"/\*[\s\S]*?\*/", "", m.group(1)), flags=re.M)
    assert "scrollIntoView" not in body, \
        ("_hiScroll 不得用 scrollIntoView —— 它逐层滚动**所有可滚祖先**, 而 .add-dialog-body 就是"
         "overflow-y 容器: 开层过渡期会把整段说明文案一起滚走再弹回(2026-10-29 八修, 用户报「选中路径"
         "后再点下拉, 弹窗文字从上往下滑一次」; 同禁令先例 26-09-29-2142)")
    assert "scrollTop" in body and "getBoundingClientRect" in body, \
        "_hiScroll 必须手动差值调 scrollTop(block: nearest 语义, 只滚菜单内部那层)"
    assert "box.contains(n)" in body and "n === box" in body, \
        ("_hiScroll 的逐级滚动必须以菜单根为界(box.contains(n) 循环条件 + 到 box 即 break) —— "
         "不设界就会继续往上滚 .add-dialog-body / 页面, 等于把 scrollIntoView 的危害换个写法重犯")
    assert '[data-hi="1"]' in body, \
        "_hiScroll 找不到高亮项选择器 [data-hi=\"1\"](与模板 data-hi 绑定同源, 改了要两处同步)"


def test_frontend_pop_item_a11y_contract():
    """浮层可点击行 .pop-item 的 a11y 三分类契约守阵(issue 26-10-29-1335, R23-A-09)

    同一可点击行原语被三种浮层复用, 修复前是三套口径且 combobox 一路整段缺失(读屏听不出
    高亮项与面板开关、列选择器 Space 无反应、UI 切换听不出当前项)。守阵按修复定案的三分类逐项钉:
      选择式(combobox, <aq-combo-input> 单组件): 输入框 role=combobox + :aria-expanded +
        aria-autocomplete=list + :aria-controls(仅开层时指面板 —— 面板 v-if 关层即不在 DOM,
        常挂 = 悬空引用) + :aria-activedescendant(带界, 只指真实存在的候选项);
        面板 role=listbox + :id=inputId+'-pop' 与 aria-controls 同源; 候选行 role=option +
        :id + :aria-selected。候选 id 生成式单点是组件方法 comboOptId —— 输入侧与行侧
        各写一份必漂移, 守阵数出现次数(js 定义恰 1, 模板消费恰 3: 输入 1 + 两变体各 1);
        预置行不参与键盘索引, 不配 option 语义, aria-hidden 挂起(可点性读屏忽略, 点击仍在)。
      选择式同族(顶栏列选择器): role=button + Enter/Space 双键, handler 与 @click/@keyup.enter
        逐字同款; 筛选器项是基准锚一并钉住(参照被改 = 全族口径漂移, 同步本守阵)。
      导航式(顶栏 UI 切换 <a href>): 保留链接语义, 当前项 :aria-current="page"。
    右键菜单族(.ctx-item)键盘化是另一件(issue 06 重开条件), 本守阵不管。
    """
    combo_tpl = open(os.path.join(STATIC_ROOT, "shared", "tpl", "combo-input.html"), encoding="utf-8").read()
    body = _tpl_body(combo_tpl, "tpl-combo-input")
    at = open(os.path.join(STATIC_ROOT, "shared", "add_torrent.js"), encoding="utf-8").read()
    topbar = open(os.path.join(STATIC_ROOT, "shared", "tpl", "topbar.html"), encoding="utf-8").read()

    # 1. 选择式: 输入框侧 combobox 语义(逐属性钉, 漂移即红)
    combo_controls = ''':aria-controls="menu ? inputId + '-pop' : null"'''
    combo_descendant = ''':aria-activedescendant="hi >= 0 && hi < options.length ? comboOptId(hi) : null"'''
    panel_binding = ''':id="inputId + '-pop'"'''
    assert 'role="combobox"' in body, "combobox 输入框缺 role=combobox(读屏不报组合框语义, issue 26-10-29-1335)"
    assert ':aria-expanded="menu"' in body, "combobox 输入框缺 :aria-expanded(面板开关状态读屏不播报)"
    assert 'aria-autocomplete="list"' in body, "combobox 输入框缺 aria-autocomplete=list(组合框补全模式语义)"
    assert combo_controls in body, "combobox 输入框缺 :aria-controls(必须仅开层时指面板 id, 关层置 null 防悬空引用)"
    assert combo_descendant in body, (
        "combobox 输入框缺 :aria-activedescendant(键盘高亮只写 hi 无 ARIA 出口 = "
        "读屏听不出当前第几项; 必须带界只指真实存在的候选项)"
    )

    # 2. 选择式: 面板 listbox + id 同源; 两处 v-for 变体候选行 option 语义各齐
    assert 'role="listbox"' in body and panel_binding in body, \
        "候选面板缺 role=listbox + :id=inputId+'-pop'(与输入框 aria-controls 同源)"
    assert body.count('role="option"') == 2, \
        "候选行两处 v-for(innerList 与非 innerList 变体)必须都带 role=option(缺一处 = 该变体读屏不报选项)"
    assert body.count(':id="comboOptId(i)"') == 2, \
        "候选行 :id 必须两处变体都走 comboOptId(i) 单点(手写 id 串 = 与 aria-activedescendant 漂移)"
    assert body.count(':aria-selected="i === hi"') == 2, \
        "候选行 :aria-selected 必须两处变体都有(读屏靠它听高亮, 视觉 .on 不够)"

    # 3. 候选 id 生成式单点: js 定义恰 1 次(钉定义形态, 注释提及不算), 模板消费恰 3 次(输入 1 + 两变体各 1)
    assert at.count("comboOptId(i) {") == 1, \
        "候选 id 生成式必须只在 add_torrent.js 定义一次(重复定义/多份生成式 = 输入侧与行侧漂移)"
    assert '"-opt-"' in at, "comboOptId 生成式里找不到 '-opt-' 后缀(面板 id 家族约定, 改名要同步本守阵)"
    assert body.count("comboOptId(") == 3, \
        "模板 comboOptId( 消费必须恰 3 处: 输入 aria-activedescendant 1 + 两个 v-for 变体各 1"

    # 4. 预置行: 不参与键盘索引就不配 option 语义, aria-hidden 让读屏忽略其可点性(点击仍在)
    m = re.search(r'<div v-if="presetLabel"[^>]*>', body)
    assert m, "combo-input.html 找不到预置行(改名/挪走了? 同步本守阵)"
    assert 'aria-hidden="true"' in m.group(0) and "role=" not in m.group(0), \
        "预置行必须 aria-hidden 且不配 role(option 语义要求参与键盘索引, 它不参与; 裸露可点性又会被读屏误报)"
    assert body.count('aria-hidden="true"') == 1, \
        "模板里 aria-hidden 只许挂在预置行上(候选行都必须能被读屏看到)"

    # 5. 选择式同族: 列选择器项 Enter/Space 双键, handler 逐字同款(与 @click 同式)
    m = re.search(r'<div v-for="c in def\.columns"[^>]*>', topbar)
    assert m, "topbar.html 找不到列选择器项(改名/挪走了? 同步本守阵)"
    col = m.group(0)
    assert '@keyup.enter="!c.locked && toggleColumn(def.id, c.key)"' in col and \
        '@keyup.space.prevent="!c.locked && toggleColumn(def.id, c.key)"' in col, \
        "列选择器项必须 Enter/Space 双键且 handler 逐字同款(Space 无反应 = 与筛选器项口径分裂)"
    # 6. 基准锚: 筛选器项的三键位(它是本族参照; 改它 = 全族口径漂移, 同步本守阵)
    assert '@keyup.enter="toggleFilterValue(f.field, o.value)"' in topbar and \
        '@keyup.space.prevent="toggleFilterValue(f.field, o.value)"' in topbar, \
        "筛选器项基准锚(Enter/Space 双键)被改 —— 全族 Space 口径参照没了, 同步本守阵"
    # 7. 导航式: UI 切换项当前值 aria-current=page(视觉 .on 不够, 读屏听不出当前项)
    m = re.search(r'<a v-for="o in uiOptions"[^>]*>', topbar)
    assert m, "topbar.html 找不到 UI 切换项(改名/挪走了? 同步本守阵)"
    ui_current = ''':aria-current="o.id === ui ? 'page' : null"'''
    assert ui_current in m.group(0), "UI 切换项缺 :aria-current=page(导航式当前项标注, 只靠 .on 上色读屏听不出)"


def test_frontend_ctx_menu_refit_by_measured_size():
    """浮层菜单开层后按**实测**尺寸重钳位(issue 26-10-06-1717 的接线守阵, 静态防回潮)

    症状: 批量菜单(约 10 项, 实测 393px)由 `_menuPos` 的常量 h=222 估算做视口钳位 ——
    锚点落在视口下部时菜单底越过下缘, 底部项(标签分类/导出/批量删除)真实点击不可达
    (Playwright 报 "element is outside of the viewport" 重试到超时)。这类几何缺陷 pytest
    跑不出来, 故这里只钉**接线**; 行为面由 e2e/menus.spec.mjs 的 CTX-fit test 兜底:
      ①_menuFit 必须按 offsetWidth/offsetHeight 实测算(把常量改大一号那种"修法"再犯即红);
      ②三个菜单容器(行右键/表头右键/文件优先级)各有 ref, 且与三个 state 对象各自的
        开层 watcher 里的 (stateKey, refName) 一一对上 —— 漏一处 = 那个菜单静默不钳位;
      ③watcher 必须在 $nextTick 里量(同步量到的是开层前的 DOM)。
    """
    import re

    static = STATIC_ROOT
    fb = open(os.path.join(static, "shared", "ui_feedback.js"), encoding="utf-8").read()
    state_js = open(os.path.join(static, "shared", "state.js"), encoding="utf-8").read()
    tpl = open(os.path.join(static, "shared", "tpl", "ctx-menus.html"), encoding="utf-8").read()

    # 1. 量测必须是**实测**: 两个 offset* 都要出现, 且以视口为界
    fit = re.search(r"_menuFit\(el, x, y\) \{(.*?)\n    \},", fb, re.S)
    assert fit, "ui_feedback.js 找不到 _menuFit(开层实测钳位单点, 改名或挪走了? 同步本守阵)"
    fit_body = fit.group(1)
    assert "el.offsetWidth" in fit_body and "el.offsetHeight" in fit_body, \
        "_menuFit 必须按 offsetWidth/offsetHeight 实测(退回常量估算 = issue 26-10-06-1717 复现)"
    assert "window.innerWidth" in fit_body and "window.innerHeight" in fit_body, \
        "_menuFit 必须以视口为界(innerWidth/innerHeight)"
    assert 'el.style.maxHeight = ""' in fit_body, \
        "_menuFit 必须每次先复位兜底限高(否则本次量到的是上一次压过的高度)"

    # 2. 三容器 ref + 三开层 watcher 成对
    for key, ref in (("menu", "ctxMenu"), ("headMenu", "headMenuEl"), ("filePrio", "filePrioEl")):
        assert f'ref="{ref}"' in tpl, \
            f"ctx-menus.html 缺 ref=\"{ref}\"({key} 菜单量测拿不到容器对象)"
        m = re.search(rf"\n    {key}\(\) \{{\n(.*?)\n    \}},", state_js, re.S)
        assert m, (
            f"state.js 缺 {key} 开层 watcher —— 开层入口有五六处(menu.js/shows.js/drawer.js), "
            f"直挂方法必漏, 与 _fitAddPop 同范式走 watcher 单点"
        )
        assert f'_menuFitRefit("{key}", "{ref}")' in m.group(1), \
            f"{key} watcher 必须调 _menuFitRefit(\"{key}\", \"{ref}\")(stateKey/ref 对不上就量不到)"
        assert "$nextTick" in m.group(1), \
            f"{key} watcher 必须在 $nextTick 里量(同步量到的是开层前的 DOM, 高度恒 0)"

    # 3. 出口现读现取: 闭包捕获旧对象/旧元素会在"开着又换一行"时把旧位置写回新菜单
    refit = re.search(r"_menuFitRefit\(stateKey, refName\) \{(.*?)\n    \},", fb, re.S)
    assert refit, "ui_feedback.js 找不到 _menuFitRefit(watcher 出口单点, 改名或挪走了? 同步本守阵)"
    refit_body = refit.group(1)
    assert "this[stateKey]" in refit_body and "this.$refs[refName]" in refit_body, \
        "_menuFitRefit 必须现读 this[stateKey] / this.$refs[refName](闭包捕获会在重开时写错位置)"
    assert ".visible" in refit_body, "_menuFitRefit 必须守 visible(菜单已关就别再回写位置)"


def test_frontend_add_combo_label_clear_mask_and_refit():
    """添加种子三下拉「第二轮遗留四项」接线守阵(2026-10-03 报障, 静态防回潮)

    上一轮(失焦即收 + 开层限高)之后剩下的四条, 根因同样全在"pytest 看不见的事件/几何接线"里:
      1. **点字段 label 稳定复现下拉闪烁(两轮才修对)**: label 的 click 默认动作把 click **转发**
         给 for= 的输入框, 而它自己那次 click 先冒泡到 window(lifecycle 收层名单) ⇒ 必须
         @click.stop。但只挡 click 赢不了主竞态: label 的 **mousedown** 默认动作先把已聚焦的
         输入框 blur 掉, addPopBlurClose 的 40ms 合帧定时器在**按住期间**(人手 80~150ms 必然
         > 40ms)先触发收层, 松手后 label 转发回焦再重开 = 闪烁。修法 = 四个 combo 的字段 label
         一律 @mousedown.prevent + @click.stop(缺一即回归)。
      2. **三个 combobox 没有清空按钮**: 补 .add-pop-clear, 必须 @mousedown.prevent(不拦默认
         动作按钮会抢焦点 → 输入框失焦走 addPopBlurClose 把下拉收掉, 清完想接着挑就多点一次)。
      3. **拖选输入框文字、终点落在遮罩上抬手 = 关窗**: click 的 target 是 mousedown/mouseup 的
         **公共祖先**, 这情形公共祖先就是遮罩 ⇒ @click.self 误判成"点空白关窗"。修法 = 遮罩
         改成 mousedown 记臂位 + mouseup.self 才关(全仓 11 处遮罩统一, 含无输入框的弹层 ——
         拖选普通文字同样会误关)。
      4. **选中分类后逐字删除, 下拉把窗口撑变形**: 限高只在开层那一刻按**当时**的候选量算过,
         过滤词变化(候选从 1 条涨回全量)时菜单没关过, 开层 watcher 不触发 ⇒ 旧限高不更新。
         修法 = 三个输入值各挂 watcher(开着才重限), meta 对话框的分类下拉同族一并补。
      5. **四轮 JS 收层守卫(2026-10-04 用户报三修后真机仍闪)**: 三修的 Chromium 探针自校验证明
         修饰符修法本身有效(摘掉即复现完整闪烁链), 用户症状与"浏览器跑的还是旧模板"一致 ——
         页签长开不刷新时模板/JS 以加载那一刻为准, 服务端更新到不了。故收层再加 JS 单点守卫
         _popBlurShouldHold: addPopBlurClose/metaCatBlurClose 的 40ms 定时器触发那刻, 焦点已回
         本族输入框或本族 label 转发 click 仍在途(mousedown 记录器 capture 记落点) → 跳过收层。
         模板修饰符在 = 纯 no-op(mousedown 已被 prevent, 定时器不武装); 缺位 = 独立根除闪烁,
         任何模板/JS 代际混合都安全。
      6. **点面板头/空态文案把面板点没了(2026-10-29 六修)**: 面板里除候选行/预置行之外还有两处
         **非交互区** —— .pop-head(标题+计数) 与 .pop-empty(空态文案)。它们点了什么都不该发生, 但
         mousedown 的默认动作把焦点从输入框抢走 → @focusout → 40ms 合帧后收层 = 面板"点一下就消失"
         (光标本来就在候选行正上方, 误触概率极高)。修法 = 焦点纪律挂在**面板根**
         (@mousedown.prevent)一处覆盖全部非交互子元素; 逐个给 .pop-head 打补丁 = 空态那处静默复发
         (e2e 两条断言必须配对: 单看"点头不收"放得过半截修法)。
      7. **按下与抬起落在不同元素, 面板点一下就关(2026-10-29 七修)**: 浏览器把 click 的 target 定成
         mousedown/mouseup 两者的**公共祖先** —— 按在输入框、抬到行内留白/面板/整行时, click 目标是
         `.add-input-row`, 那一层没有 @click.stop 就冒泡到 lifecycle 的 window 收层名单, 面板立刻关。
         无焦点时最易踩(面板在按住期间才挂载, DOM 在按下与抬起之间变化), 皮肤差异也由此而来(输入行
         差 2px + drop-in 从 -4px 起)。修法 = 组件根挂 @click.stop, **只挂组件根**: 挂到对话框层会把
         "点对话框别处收层"一起废掉(e2e 反向守门断言就在测这条)。
    """
    import re

    shared = os.path.join(STATIC_ROOT, "shared")
    at = open(os.path.join(shared, "add_torrent.js"), encoding="utf-8").read()
    dg = read_shared("dialogs.js")
    lf = open(os.path.join(shared, "lifecycle.js"), encoding="utf-8").read()
    mgr = open(os.path.join(shared, "tpl", "dialogs-mgr.html"), encoding="utf-8").read()
    pv = open(os.path.join(shared, "tpl", "popovers.html"), encoding="utf-8").read()
    xt = open(os.path.join(shared, "tpl", "combo-input.html"), encoding="utf-8").read()

    # 1. 四个 combo 的字段 label 全部 @mousedown.prevent + @click.stop(漏一个 = 那个下拉点 label 稳定闪烁;
    #    prevent 挡 mousedown 默认动作的 blur(40ms 合帧窗赢不了人手按住时长), stop 挡 window click 收层)
    for holder, input_id in (
        ("mgr", "ad-save-path"), ("mgr", "ad-category"), ("mgr", "ad-tags"), ("pv", "meta-category")
    ):
        src = mgr if holder == "mgr" else pv
        m = re.search(rf'<label[^>]*for="{input_id}"[^>]*>', src, re.S)
        assert m, f"找不到 for=\"{input_id}\" 的字段 label(改结构了? 同步本守阵)"
        assert "@click.stop" in m.group(0), \
            (f"label[for={input_id}] 缺 @click.stop —— 点它会走「window click 收层 → label 转发 "
             f"click 重开」= 下拉闪烁再现(输入框已聚焦, @focusout 挡不住这一路)")
        assert "@mousedown.prevent" in m.group(0), \
            (f"label[for={input_id}] 缺 @mousedown.prevent —— label 的 mousedown 默认动作把已聚焦的"
             f"输入框 blur 掉, addPopBlurClose 的 40ms 合帧定时器在按住期间(人手 80~150ms > 40ms)"
             f"先收层, 松手 label 转发回焦再重开 = 闪烁(2026-10-04 三修, 真机按住时序实测)")

    # 2. 三个 combobox 内嵌清空(x): 按钮本体收敛进组件模板 #tpl-combo-input(clear-kind 参数化,
    #    issue 26-10-20-2230), 调用点传 kind + @clear 接线; 模板侧钉 has-clear + 双修饰符 + 非空显形
    tpl_seg = re.search(r'id="tpl-combo-input">([\s\S]*?)</script>', xt, re.S)
    assert tpl_seg, "combo-input.html 找不到 #tpl-combo-input(combobox 共享模板)"
    tpl_body = tpl_seg.group(1)
    assert "'has-clear': !!clearKind" in tpl_body, "组件模板输入行缺 has-clear 绑定(清空钮靠它让出右内边距)"
    assert 'class="add-pop-clear"' in tpl_body, "组件模板缺 .add-pop-clear 清空按钮"
    assert 'v-if="clearKind && modelValue"' in tpl_body, "组件模板清空钮缺非空显形条件(空框也显示 = 多点一次空操作)"
    btn = re.search(r'<button[^>]*add-pop-clear[\s\S]{0,200}?>', tpl_body)
    assert btn and "@mousedown.prevent" in btn.group(0), \
        "组件模板清空钮缺 @mousedown.prevent(不拦默认动作会抢焦点 → 下拉被失焦收掉)"
    assert btn and "@click.stop" in btn.group(0), \
        ("组件模板清空钮缺 @click.stop —— 它的 click 会冒泡到 lifecycle 的 window "
         "收层名单, 点一下 x 顺手把下拉一起收了(真机走查实测: 清空后菜单消失)")
    assert "$emit('clear', clearKind)" in tpl_body, "组件模板清空钮没向调用方 emit clear(kind)"
    for input_id, kind, field in (
        ("ad-save-path", "path", "addSavePath"), ("ad-category", "cat", "addCategory"), ("ad-tags", "tag", "addTags")
    ):
        i = mgr.index(f'input-id="{input_id}"')
        seg = mgr[mgr.rindex("<aq-combo-input", 0, i):i + 900]
        assert f'clear-kind="{kind}"' in seg, f"#{input_id} 的调用点没传 clear-kind=\"{kind}\"(无清空钮)"
        assert f'v-model="{field}"' in seg, f"#{input_id} 的调用点没把 {field} 绑进 v-model(清空钮非空显形条件失效)"
        assert '@clear="clearAddField"' in seg, f"#{input_id} 的清空钮没接 @clear=\"clearAddField\""
    clear_body = re.search(r"clearAddField\(kind\) \{(.*?)\n    \},", at, re.S)
    assert clear_body, "add_torrent.js 找不到 clearAddField(三个 combobox 的清空单点)"
    for field in ("addSavePath", "addCategory", "addTags"):
        assert f"this.{field} = \"\";" in clear_body.group(1), f"clearAddField 不清空 {field}"

    # 6. 面板根挂 @mousedown.prevent(2026-10-29 六修): 面板内**非交互区**(.pop-head 标题+计数 /
    #    .pop-empty 空态文案)点了不许把焦点从输入框抢走 —— 抢走即 @focusout → 40ms 合帧收层
    #    = 面板"点一下就消失"。修饰符必须在**根**: 逐个给非交互子元素打补丁, 新增一处即静默复发
    #    (本轮红验证: 只给 .pop-head 挂 prevent 时"点头不收"仍绿, 空态那条才抓到)。
    root_tag = re.search(r'<div v-if="menu" class="pop-menu add-pop"[^>]*>', tpl_body)
    assert root_tag, "组件模板找不到面板根(.pop-menu.add-pop)(改名或挪走了? 同步本守阵)"
    assert "@mousedown.prevent" in root_tag.group(0), \
        ("组件模板面板根缺 @mousedown.prevent —— 点面板头/空态文案时 mousedown 的默认动作把焦点从"
         "输入框抢走, @focusout 的 40ms 合帧定时器收层 = 面板点一下就消失(2026-10-29 六修); "
         "修饰符必须挂根上一处覆盖全部非交互子元素, 逐个打补丁 = 往面板里加一处展示节点就复发")
    assert "@click.stop" in root_tag.group(0), \
        "组件模板面板根丢了 @click.stop(面板内点击会冒泡到 lifecycle 的 window 收层名单, 点一下就把下拉收了)"

    # 7. 组件**根**挂 @click.stop(2026-10-29 七修): 按下与抬起落在不同元素时, click 的 target 是两者的
    #    **公共祖先**(.add-input-row / 面板 / 整行) —— 那一层没人挡就冒泡到 lifecycle 的 window 收层名单
    #    ⇒ 面板点一下就关。无焦点时最易踩: 面板在按住期间才挂载, DOM 在按下与抬起之间变化, 抬起落点被
    #    改写的机会就在那一段(两皮肤输入行差 2px + drop-in 从 -4px 起 = 皮肤差异的来源)。
    #    ⚠ 只许挂在组件根: 挂到更外层(对话框)会把"点对话框别处收层"一起废掉。
    row_tag = re.search(r'<div class="add-input-row"[^>]*>', tpl_body)
    assert row_tag, "组件模板找不到输入行根(.add-input-row)(改名或挪走了? 同步本守阵)"
    assert "@click.stop" in row_tag.group(0), \
        ("组件模板输入行根缺 @click.stop —— 按下与抬起落在不同元素时 click 的 target 是公共祖先"
         "(.add-input-row/面板), 事件冒泡到 window 收层名单 = 面板点一下就关(2026-10-29 七修); "
         "它必须挂在组件根, 挂到对话框层会把「点对话框别处收层」一起废掉")

    # 3. 遮罩关窗: mousedown 记臂位 + mouseup.self 才关; 全仓不许再有 @click.self
    #    (issue 26-10-20-2231 收敛后手势对单点在 <aq-modal> 组件模板(tpl/dialog-shell.html),
    #    调用点不再出现遮罩字面量 —— 改为组件模板一处手势对 + 调用点 :close 接线清点)
    shell = open(os.path.join(shared, "tpl", "dialog-shell.html"), encoding="utf-8").read()
    masks = re.findall(r'<div v-if="open" :class="maskClass"[\s\S]{0,240}?>', shell)
    assert len(masks) == 1, f"dialog-shell.html 应恰有 1 处遮罩(组件单点), 实数 {len(masks)}"
    assert '$root.maskDownSelf($event)' in masks[0] and '$root.maskCloseIfArmed(close, ...closeArgs)' in masks[0], \
        ("aq-modal 的遮罩没接「mousedown 记臂位 + mouseup.self 才关」—— @click.self 会被"
         "『拖选文字终点落在遮罩上抬手』误判成点空白关窗; 手势经 $root 回调根方法(读根 _maskArmed)")
    for name in ("dialogs-mgr.html", "dialogs.html", "popovers.html", "move-dialog.html", "dialog-shell.html"):
        txt = open(os.path.join(shared, "tpl", name), encoding="utf-8").read()
        live = re.sub(r"<!--[\s\S]*?-->", "", txt)  # 注释里讲原理不算(只查真接线)
        assert "@click.self" not in live, \
            f"{name} 仍残留 @click.self 遮罩关窗(拖选文字抬手会误关窗)"
    # 调用点清点: 全部带遮罩对话框都必须走 <aq-modal>(漏一处 = 手抄外壳回潮);
    # 9 处调用覆盖 10 个开态(mgr 两态共用一份模板), speed-pop(无遮罩异形)直用 head 组件
    callsites = {
        "dialogs-mgr.html":
            (
                ':open="addOpen"', ':close="closeAddTorrent"', 'mask-class="modal-mask add-dialog-mask"',
                ':open="dirBrowse.open"', ':close="closeDirBrowse"', 'mask-class="modal-mask dir-browse-mask"'
            ),
        "dialogs.html":
            (
                ':open="statsOpen"', ':close="closeStats"', 'icon-class="ico-chart"',
                '<aq-modal-head icon="#i-gauge" title="限速" :close="closeSpeedDialog">'
            ),
        "popovers.html":
            (
                ':close="closeMgr"', ':open="metaOpen"', ':close="closeMeta"', ':open="modal.visible"',
                ':close="resolveModal"', ':close-args="[false]"', ':x="false"', ':open="historyOpen"',
                ':close="closeHistory"', 'icon-class="ico-history"', '<template #extra>', ':open="kbHelpOpen"',
                ':close="closeKbHelp"'
            ),
        "move-dialog.html": (':open="moveOpen"', ':close="closeMove"'),
    }
    n_calls = 0
    for name, needles in callsites.items():
        ctxt = open(os.path.join(shared, "tpl", name), encoding="utf-8").read()
        for needle in needles:
            assert needle in ctxt, f"{name} 缺 {needle}(对话框没走 <aq-modal>? 手抄外壳回潮)"
        n_calls += ctxt.count("<aq-modal ")
    assert n_calls == 9, f"<aq-modal> 调用点应 9 处(mgr 两态共用一份), 实数 {n_calls}"
    arm = re.search(r"maskDownSelf\(e\) \{(.*?)\n    \},", dg, re.S)
    assert arm and "e.target === e.currentTarget" in arm.group(1), \
        "dialogs.js::maskDownSelf 必须判 target === currentTarget(只有按在遮罩上才算起手)"
    close_arm = re.search(r"maskCloseIfArmed\(closeFn, \.\.\.args\) \{(.*?)\n    \},", dg, re.S)
    assert close_arm and "if (!this._maskArmed) return;" in close_arm.group(1), \
        "dialogs.js::maskCloseIfArmed 必须先判 _maskArmed(起手在对话框内的那一笔不许关窗)"

    # 4. 过滤词变化重限高: 三个输入值 watcher + meta 侧三处(候选到位/开层/过滤词)
    for val, pop in (("addCategory", "addCatMenu"), ("addTags", "addTagMenu"), ("addSavePath", "addPathPop")):
        assert re.search(rf"\n    {val}\(\) \{{\n      if \(this\.{pop}\) this\._fitAddPop", at), \
            (f"add_torrent.js 缺 {val} 的 watcher —— 打开时按当时的候选量限过高, 删字让候选涨回全量时"
             f"菜单没关过(开层 watcher 不触发), 下拉会把窗口撑变形")
    for key, guard in (
        ("metaCatMenu(v)", "if (v)"), ("metaCatInput()", "if (this.metaCatMenu)"),
        ("metaCategories()", "if (this.metaCatMenu)")
    ):
        assert re.search(rf"\n    {re.escape(key)} \{{\n      {re.escape(guard)} this\._fitAddPop", dg), \
            f"dialogs.js 缺 {key} 的限高 watcher(meta 分类下拉与三下拉同族, 撑变形同样会犯)"
    assert 'if (!this.addOpen && !this.metaOpen && !this.moveOpen) return;' in at, \
        "_fitAddPop 必须同时放行 meta 对话框与设定位置对话框(三处共用同一套限高, 只认 addOpen 会让 meta/move 侧恒不生效)"

    # 5. meta 分类下拉补失焦收层 + 进 window click 兜底名单(原本两处都漏 = 点对话框别处下拉不收)
    #    (收敛 issue 26-10-20-2230: 输入框进组件模板, 字段接线在调用点 @blur)
    m = re.search(r'<aq-combo-input input-id="meta-category"(.*?)>', pv, re.S)
    assert m and '@blur="metaCatBlurClose"' in m.group(1), \
        "#meta-category 缺 @blur 收层(点对话框里别的地方下拉悬着不收)"
    blur = re.search(r"metaCatBlurClose\(\) \{(.*?)\n    \},", dg, re.S)
    assert blur and '_popBlurArm("_metaPopBlurT", ["meta-category"]' in blur.group(1), \
        "metaCatBlurClose 必须走 _popBlurArm 合帧单点(同步收层会被 label 转发回焦打断 = 闪烁)"
    open_meta = re.search(r"openMetaCatMenu\(\) \{(.*?)\n    \},", dg, re.S)
    assert open_meta and '_popBlurCancel("_metaPopBlurT")' in open_meta.group(1), \
        "openMetaCatMenu 必须撤销挂起的失焦收层(焦点转回输入框时菜单不闪)"
    assert "this.metaCatMenu = false;" in lf, \
        "lifecycle.js 的 window click 兜底名单缺 metaCatMenu(与三下拉同层, 漏了靠 focusout 单点兜)"

    # 6. 清空钮样式三皮肤成对(漏一档 = 该皮肤按钮无样式: 透明方块 + 文字被压在底下)
    for ui in _UI_ALL:
        css_dir = os.path.join(STATIC_ROOT, ui, "css")
        blob = "".join(
            open(os.path.join(css_dir, f), encoding="utf-8").read()
            for f in sorted(os.listdir(css_dir)) if f.endswith(".css")
        )
        assert ".add-pop-clear" in blob, f"{ui} 缺 .add-pop-clear 样式(清空钮无尺寸/无 hover)"
        assert ".add-input-row.has-clear" in blob, f"{ui} 缺 .has-clear 右内边距(文字会被按钮压住)"

    # 7. 四轮 JS 收层守卫(2026-10-04): 40ms 定时器收层前必须问 _popBlurShouldHold ——
    #    焦点已回本族输入框 / 本族 label 转发 click 仍在途 → 不收。模板修饰符缺位(旧页签
    #    残留模板)时由它独立根除「按住期收层 → 松手回焦重开」, 不依赖模板 JS 同代到达。
    assert "window.addEventListener(\"mousedown\", this._popLabelDownRecorder, { capture: true });" in at, \
        "add_torrent.js mounted 缺 mousedown capture 记录器(守卫没有落点数据 = 形同虚设)"
    assert "removeEventListener(\"mousedown\", this._popLabelDownRecorder" in at, \
        "add_torrent.js unmounted 缺记录器移除(热重载后句柄堆叠, 每次点击记 N 笔)"
    hold = re.search(r"_popBlurShouldHold\(ids\) \{(.*?)\n    \},", at, re.S)
    assert hold, "add_torrent.js 找不到 _popBlurShouldHold(收层守卫单点)"
    assert "document.activeElement" in hold.group(1) and "ids.includes(ae.id)" in hold.group(1), \
        "_popBlurShouldHold 必须先判「焦点已回本族输入框」(转发 click 已落地 → 不收)"
    assert "performance.now() - rec.t <= 350" in hold.group(1), \
        "_popBlurShouldHold 必须带 350ms 新鲜度上界(防旧记录误挡后续无 mousedown 的失焦, 如 Tab)"
    # 收敛(issue 26-10-20-2230)后 addPopBlurClose/metaCatBlurClose 是薄封装, 家族 id 名单随
    # _popBlurArm 实参传入、守卫调用在单点内 —— 断言入口传对名单 + 单点内恒问守卫
    arm = re.search(r"_popBlurArm\(timerKey, ids, close\) \{(.*?)\n    \},", at, re.S)
    assert arm and "_popBlurShouldHold(ids)" in arm.group(1), \
        "_popBlurArm 收层前没问守卫(模板修饰符缺位时 JS 守卫独立根除按住期收层闪烁)"
    add_close = re.search(r"addPopBlurClose\(\) \{(.*?)\n    \},", at, re.S)
    assert add_close and '["ad-save-path", "ad-category", "ad-tags"]' in add_close.group(1), \
        "addPopBlurClose 没传三字段的家族 id 名单(缺一即该字段守卫失效)"
    meta_close = re.search(r"metaCatBlurClose\(\) \{(.*?)\n    \},", dg, re.S)
    assert meta_close and '["meta-category"]' in meta_close.group(1), \
        "metaCatBlurClose 没传 meta 分类的家族 id(meta 分类下拉与三下拉同族, 缺位同闪)"


def test_frontend_move_dialog_combobox_wiring():
    """设定位置对话框(2026-10-13)保存路径下拉接线守阵(静态防回潮)

    单种子/单组/多选批量三入口统一改, 保存路径下拉候选按「最近使用」排序(与添加种子保存路径同口径)。
    钉:
      1. 三入口名/签名(editMove/editMoveMulti/editMoveGroup)与下游投递(editMove→_editPost,
         editMoveMulti/editMoveGroup→_bulkEditPost)不变 —— 守阵 + 触发登记表钉这些;
      2. 排序单点复用 _addOrderByRecent + _addRecencyMaps(跨视图取数, 与添加种子同口径);
      3. combobox 收层/限高/悬同与添加种子三下拉 + meta 分类同套口径(@focusout + 40ms合帧 +
         _popBlurShouldHold + watcher重限 + comboHoverIdx move 分支);
      4. 对话框模板接线: moveOpen 遮罩 + move-path label @mousedown.prevent @click.stop +
         @focusout收层 + @keydown键盘导航 + ref=movePathList + 三皮肤成对 CSS;
      5. 几何修(2026-10-19 用户报「弹窗太小, 下拉显示不全要滚动」): 组合框是表单最后一项,
         朝下开的下拉必伸出 .add-dialog-body 底沿被裁且撑大其 scrollHeight ⇒ 根元素按
         movePathMenu 挂 .pop-open 类 + 三皮肤成对的开层预留(padding-bottom 272px)与
         860 宽档(--modal-w-add)规则, 下拉完整落在对话框内、弹窗体零新增滚动。
      6. 二修(2026-10-29 用户报「点下拉选项就触发移动」+「窗口太小, 点下拉高度跳变」):
         ①点选候选只回填(moveApplyPath 体内不得出现 submitMoveDialog), 移动只由按钮/手输回车发起;
         ②手输回车仍提交 —— 键盘单点回退分支走 (ctx.onEnter || ctx.onPick)(v), 只有 move 传钩子;
         ③空路径按钮置灰; ④打开只聚焦不展开(openMoveDialog 置 moveSuppressOpen, openMovePathMenu
         首行消费); ⑤三皮肤成对: 收层态基线 min-height 360px + 动作条 margin-top:auto 钉底 +
         padding-bottom 200ms 过渡(替掉 0↔272 硬切), 过渡后 settle(MOVE_POP_SETTLE_MS=240)重测限高。
      7. 三修(2026-10-29 用户报「点下拉框, 下拉框出现后自动弹回」): 遮罩默认 align-items:center,
         开层增高上下对半扩 ⇒ 输入行连同刚展开的面板整体上移 77px, 面板顶到光标底下(再点一下即
         命中候选/面板头 = 面板"自动弹回")⇒ 遮罩挂 .move-dialog-mask 改 flex-start + margin-top
         复刻收层态居中偏移, **增长只朝下**。三皮肤成对 + 模板 mask-class 接线。
      8. 四修(2026-10-29 用户报「下拉框出现时弹窗有一瞬间出现滚动条」): 预留 padding 是过渡的,
         面板瞬间挂载 ⇒ 开层头 ~110ms 面板伸出 body 的 padding 盒(实测溢出 256→0), body 是
         overflow-y:auto 的滚动容器 ⇒ 闪滚动条 + 内容横向挤一个滚动条宽。开层期溢出的只有预留
         空白 ⇒ 关掉滚动条(收层态仍 auto, 矮视口 body 兜底滚动不受影响)。
      9. 五修(2026-10-29 用户报「下拉框消失时弹窗仍会有一瞬间出现滚动条」): 收层时面板**不立刻
         离场** —— 离场淡出(~120ms)期间它仍在 DOM 里、高度不变, 而 .pop-open 已摘 ⇒ 溢出涨到
         254px(实测)。开关必须跟「面板是否存在」走(`:has(.add-pop)`), 跟开合状态走只覆盖开层。
    """
    import re

    shared = os.path.join(STATIC_ROOT, "shared")
    dr = read_shared("drawer.js")
    cmd = read_shared("commands.js")
    at = open(os.path.join(shared, "add_torrent.js"), encoding="utf-8").read()
    lf = open(os.path.join(shared, "lifecycle.js"), encoding="utf-8").read()
    st = open(os.path.join(shared, "state.js"), encoding="utf-8").read()
    pv = open(os.path.join(shared, "tpl", "move-dialog.html"), encoding="utf-8").read()

    # 1. 三入口名/签名 + 下游投递不变(与触发登记表/守阵钉)
    assert re.search(r"\n    async editMove\(h = \"\"\)", dr), "drawer.js 缺 editMove(h) 单种子入口"
    assert re.search(r"\n    async editMoveMulti\(targets = null", dr), "drawer.js 缺 editMoveMulti(targets = null) 多选入口"
    assert re.search(r"\n    editMoveGroup\(\)", cmd), "commands.js 缺 editMoveGroup() 单组入口"
    assert "this._editPost(this.moveSingleHash, \"location\"" in dr, "submitMoveDialog 单种子没走 _editPost"
    assert "this._bulkEditPost(this.moveTargets, \"location\"" in dr, "submitMoveDialog 批量没走 _bulkEditPost"

    # 2. 排序单点复用(与添加种子同口径, 跨视图取数)
    assert "_addOrderByRecent(paths, recent.path)" in dr, "loadMoveOptions 没走 _addOrderByRecent 排序单点"
    assert "this._addRecencyMaps()" in dr, "loadMoveOptions 没走跨视图取数单点 _addRecencyMaps"

    # 3. combobox 收层/限高/悬同同套口径(收敛 issue 26-10-20-2230: 合帧+守卫走 add_torrent.js
    #    的 _popBlurArm 单点, 各处只剩定时器键/家族名单/收层动作)
    blur = re.search(r"movePathBlurClose\(\) \{(.*?)\n    \},", dr, re.S)
    assert blur and '_popBlurArm("_movePopBlurT", ["move-path"]' in blur.group(1), \
        "movePathBlurClose 必须走 _popBlurArm 合帧单点(同步收层会被 label 转发回焦打断 = 闪烁)"
    open_move = re.search(r"openMovePathMenu\(\) \{(.*?)\n    \},", dr, re.S)
    assert open_move and '_popBlurCancel("_movePopBlurT")' in open_move.group(1), \
        "openMovePathMenu 必须撤销挂起的失焦收层(焦点转回输入框时菜单不闪)"
    for key, guard in (
        ("movePathMenu(v)", "if (v)"), ("movePathInput()", "if (this.movePathMenu)"),
        ("movePathOptions()", "if (this.movePathMenu)")
    ):
        assert re.search(rf"\n    {re.escape(key)} \{{\n      {re.escape(guard)} this\._fitAddPop", dr), \
            f"drawer.js 缺 {key} 的限高 watcher(与三下拉 + meta 同族, 撑变形同样会犯)"
    assert 'comboHoverIdx("move"' in at or "kind === \"move\"" in at, \
        "comboHoverIdx 缺 move 分支(悬同接管走错 state 对象 = 上下键选中项闪烁)"

    # 4. 对话框模板接线
    assert ':open="moveOpen"' in pv, "move-dialog.html 缺 moveOpen 开合(对话框没走 <aq-modal>?)"
    m = re.search(r'<label[^>]*for="move-path"[^>]*>', pv, re.S)
    assert m and "@click.stop" in m.group(0) and "@mousedown.prevent" in m.group(0), \
        "move-path label 缺 @click.stop + @mousedown.prevent(与三下拉 + meta 同因同修)"
    mi = re.search(r'<aq-combo-input input-id="move-path"(.*?)>', pv, re.S)
    assert mi and '@blur="movePathBlurClose"' in mi.group(1), "#move-path 缺 @blur 收层"
    assert mi and '@keydown="onMovePathKeydown' in mi.group(1), "#move-path 缺 @keydown 键盘导航"
    assert 'menu-ref="movePathList"' in (mi.group(1) if mi else ""), \
        "move-dialog.html 缺 menu-ref=movePathList(限高量拿不到容器; 收敛后 ref 经组件方法函数写根 $refs)"
    assert ':close="closeMove"' in pv, "move 对话框缺 :close 接线(遮罩手势对在组件模板, 调用点只交 close)"
    # 4b. 几何修(2026-10-19): 根元素按 movePathMenu 挂 .pop-open —— 下拉开层时对话框给 body 预留
    # 整高(规则在 5), 否则下拉伸出 body 被裁 + scrollHeight 撑大, 用户必须滚弹窗才能用下拉
    assert re.search(r':width-class="\[\'add-dialog move-dialog\', \{ \'pop-open\': movePathMenu \}\]"', pv), \
        "move-dialog.html 缺 pop-open 并入 width-class(下拉开层时对话框不预留空间)"

    # 4d. 三修(2026-10-29): 开层增长只朝下 —— 遮罩类必须接线(否则居中容器里增高上下对半扩,
    #     输入行上移 77px 把刚展开的面板顶到光标底下 = 用户报的「下拉框出现后自动弹回」)
    assert 'mask-class="modal-mask move-dialog-mask"' in pv, \
        "move-dialog.html 遮罩缺 .move-dialog-mask 类(增长方向改不了 = 面板被顶到光标底下, 2026-10-29 三修回归)"

    # 4c. 二修(2026-10-29): 点选只回填 / 手输回车仍提交 / 空态置灰 / 打开不自动展开
    apply_body = re.search(r"moveApplyPath\(p\) \{(.*?)\n    \},", dr, re.S)
    assert apply_body, "drawer.js 找不到 moveApplyPath(点选候选的回填单点)"
    assert "submitMoveDialog" not in apply_body.group(1), \
        "moveApplyPath 又调了 submitMoveDialog —— 点选候选直接移动(2026-10-29 报障回归)"
    assert "this.movePathInput = p" in apply_body.group(1), "moveApplyPath 必须回填输入框"
    assert "(ctx.onEnter || ctx.onPick)(v)" in at, \
        "comboKeydown 回退分支没走 ctx.onEnter 钩子(手输回车提交链断: 缺省仍须回落 onPick)"
    assert "onEnter: (p) =>" in dr, "onMovePathKeydown 没传 onEnter(手输路径回车不再提交)"
    assert re.search(r'<button class="bt primary" :disabled="moveBusy \|\| !movePathInput\.trim\(\)"', pv), \
        "「设定位置」按钮缺空路径置灰(按钮是唯一鼠标提交路径, 空态点了才 toast 太笨)"
    assert "this.moveSuppressOpen = true" in dr, \
        "openMoveDialog 没置抑制标志(打开即自动展开下拉 = 第一眼开层态, 收层时高度骤变)"
    assert open_move and "if (this.moveSuppressOpen) { this.moveSuppressOpen = false; return; }" in open_move.group(1), \
        "openMovePathMenu 首行缺抑制标志消费(打开就弹面板; 标志还须只消费一次, 后续点击仍展开)"
    assert re.search(r"const MOVE_POP_SETTLE_MS = 240;", dr), \
        "drawer.js 缺 MOVE_POP_SETTLE_MS 常量(过渡期量到的净空只有一半, 不重测会把列表误限到 120px)"
    assert "_movePopSettle()" in open_move.group(1), "openMovePathMenu 没触发过渡后重测限高"

    # 5. 三皮肤成对 CSS(漏一档 = 该皮肤对话框无样式)
    for ui in _UI_ALL:
        css_dir = os.path.join(STATIC_ROOT, ui, "css")
        blob = "".join(
            open(os.path.join(css_dir, f), encoding="utf-8").read()
            for f in sorted(os.listdir(css_dir)) if f.endswith(".css")
        )
        assert ".modal.move-dialog" in blob, f"{ui} 缺 .modal.move-dialog 样式(对话框无宽度)"
        assert ".move-targets" in blob, f"{ui} 缺 .move-targets 样式(目标行无排版)"
        assert re.search(r"\.modal\.move-dialog \{\s*width:\s*var\(--modal-w-add\)", blob), \
            f"{ui} 的 .modal.move-dialog 宽度未走 --modal-w-add(860 宽档, 与添加种子同宽; 560 窄档路径项 ellipsis 少显示)"
        assert re.search(r"\.modal\.move-dialog\.pop-open \.add-dialog-body \{[^}]*padding-bottom:\s*272px", blob), \
            f"{ui} 缺 .pop-open 开层预留规则(下拉伸出 body 被裁 + scrollHeight 撑大 = 用户须滚弹窗; 272px = 面板头 ~46 + 列表 210 + 顶距 4 + 余量)"
        # 四修(2026-10-29): 预留是过渡的、面板是瞬间挂载的 ⇒ 开层头 ~110ms 面板伸出 body(padding 盒)
        # 之外, body 是 overflow-y:auto 的滚动容器 ⇒ 闪一条滚动条(还横向挤一个滚动条宽)。开层期溢出
        # 的只有预留空白 ⇒ 关滚动。五修(同日): 收层时面板离场淡出(~120ms)期间仍在 DOM 里、高度不变,
        # 而 .pop-open 已摘 ⇒ 开关必须跟「面板是否存在」走(:has), 跟开合状态走会漏掉收层那一段。
        assert re.search(r"\.modal\.move-dialog:has\(\.add-pop\) \.add-dialog-body \{[^}]*overflow:\s*hidden", blob), \
            f"{ui} 缺 .move-dialog:has(.add-pop) 的 overflow:hidden(面板在 DOM 期间(body 是滚动容器)闪滚动条; " \
            "只挂 .pop-open 会漏掉离场淡出那 ~120ms)"
        # 二修(2026-10-29): 基线抬到 360(治「窗口太小」) + 动作条钉底 + padding 过渡(治「高度跳变」)
        assert re.search(r"\.modal\.move-dialog \{\s*width:\s*var\(--modal-w-add\);\s*min-height:\s*min\(360px,\s*calc\(100vh - 120px\)\)", blob), \
            f"{ui} 的 .modal.move-dialog 缺收层态基线 min-height(原实测 243px = 用户报的「窗口太小」)"
        assert re.search(r"\.modal\.move-dialog \.modal-actions \{[^}]*margin-top:\s*auto", blob), \
            f"{ui} 动作条没钉底(基线抬高后按钮会浮在中间)"
        assert re.search(r"\.modal\.move-dialog \.add-dialog-body \{[^}]*transition:\s*padding-bottom\s+200ms", blob), \
            f"{ui} 缺 padding-bottom 过渡(0↔272 硬切 = 开/收下拉高度瞬跳, 2026-10-29 报障)"
        # 三修(2026-10-29): 增长只朝下 —— 遮罩改 flex-start + margin-top 复刻收层态居中偏移
        assert re.search(r"\.modal-mask\.move-dialog-mask \{[^}]*align-items:\s*flex-start", blob), \
            f"{ui} 缺 .move-dialog-mask 的 flex-start(居中容器里增高上下对半扩, 输入行上移 = 面板顶到光标底下)"
        assert re.search(r"\.modal\.move-dialog \{[^}]*margin-top:\s*clamp\(0px, calc\(\(100vh - 360px\) / 2 - 20px\)", blob), \
            f"{ui} 的 .modal.move-dialog 缺 margin-top 居中补偿(缺了收层态会顶到视口上沿, 居中观感丢失)"

    # 6. Esc 退栈链 + escBusy 同步(与 meta 同层)
    assert "this.moveOpen) this.closeMove()" in lf, "lifecycle.js Esc 退栈链缺 moveOpen→closeMove"
    assert "this.moveOpen" in lf and "movePathMenu = false" in lf, \
        "lifecycle.js window click 兜底名单缺 movePathMenu(与三下拉同层)"


def test_frontend_rename_dialog_width_wiring():
    """重命名对话框宽档接线守阵(2026-10-19 用户报「弹窗太小」)

    字段值 = 完整种子显示名, 真实名称 routinely 80~120 字符。重命名对话框此前骑通用
    .modal 基档 520(为确认/提示一句话设计), 输入框仅 474px —— 真浏览器实测(1440x900)
    97 字符长名 scrollWidth 695 > clientWidth 472, 裁掉 223px; 桩名 43 字符恰好不裁,
    故冒烟从未暴露。修法 = _openModal 增 cls 附加类选项(空 = 既有对话框零变化),
    重命名走 rename-dialog 类 + 三皮肤 .modal.rename-dialog 宽档(--modal-w-add 860,
    与设定位置/添加种子同档)。行为面由 e2e/rename-dialog-fit.spec.mjs 真浏览器钉。
    钉:
      1. ui_feedback.js _modalInit 声明 cls 字段(附加类名单点, 与 okDisabled/busy/verdict 同届);
      2. popovers.html 模态根类绑定并入 modal.cls(数组形态, 空串不附加类);
      3. drawer.js editRename 传 cls: "rename-dialog";
      4. 三皮肤 .modal.rename-dialog 宽度规则成对且走 --modal-w-add。
    """
    import re

    shared = os.path.join(STATIC_ROOT, "shared")
    uif = open(os.path.join(shared, "ui_feedback.js"), encoding="utf-8").read()
    pv = open(os.path.join(shared, "tpl", "popovers.html"), encoding="utf-8").read()
    dr = read_shared("drawer.js")

    # 1. cls 字段在 _modalInit 单点声明(每框初值; 缺了 = 后补属性不进 Vue 响应, 挂类不生效)
    init = re.search(r"_modalInit\(\) \{\s*return \{(.*?)\n      \};", uif, re.S)
    assert init and re.search(r'\bcls:\s*""', init.group(1)), \
        "ui_feedback.js _modalInit 缺 cls 字段(附加类名单点; 不进初值 = 后补属性不进 Vue 响应)"

    # 2. 模板根类绑定并入 modal.cls(与 danger/wide 并列; 空串零附加, 既有对话框零变化)
    #    (issue 26-10-20-2231: 绑定经 <aq-modal :width-class> 透传, .modal 本体在组件模板)
    shell = open(os.path.join(shared, "tpl", "dialog-shell.html"), encoding="utf-8").read()
    assert '<div class="modal" :class="widthClass"' in shell, \
        "dialog-shell.html 缺 <div class=\"modal\" :class=\"widthClass\">(宽度档透传面被改)"
    m = re.search(r':width-class="(\[modal\.cls[^"]*)"', pv)
    assert m and "modal.cls" in m.group(1), \
        "popovers.html 确认框调用点缺 :width-class 并入 modal.cls(cls 选项挂不上类 = 宽档失生效)"

    # 3. editRename 传 cls: "rename-dialog"(回退到裸 _openModal = 骑 520 基档, 长名被裁)
    ren = re.search(r'async editRename\(h = ""\) \{(.*?)\n    \},', dr, re.S)
    assert ren and 'cls: "rename-dialog"' in ren.group(1), \
        'drawer.js editRename 缺 cls: "rename-dialog"(重命名框骑 520 基档, 97 字符长名裁 223px)'

    # 4. 三皮肤成对宽档(漏一档 = 该皮肤重命名框仍 520)
    for ui in _UI_ALL:
        blob = _ui_css_aggregate(ui)
        assert re.search(r"\.modal\.rename-dialog \{\s*width:\s*var\(--modal-w-add\)", blob), \
            f"{ui} 缺 .modal.rename-dialog 宽档规则(输入框仅 474px, 97 字符长名裁 223px; 860 = 与设定位置/添加种子同档)"


def test_frontend_dialog_shell_single_point():
    """对话框外壳单点守阵(issue 26-10-20-2231, R23-A-02·A-03·A-08 收敛)

    11 处对话框此前各手抄一份三段式外壳(.modal-title 头 11 / .modal-actions 栏 10 /
    遮罩关窗手势对 10), 现外壳一份(tpl/dialog-shell.html 的 <aq-modal> / <aq-modal-head>)
    + 中部插槽。本守阵钉三类回潮:
      1. 手抄外壳回潮: 三段字面量(class="modal-title" / class="modal-actions" / add-dialog-x)
         在 shared/tpl/ 下剥注释后只许出现在组件模板一处; 手写遮罩 div 零残留;
      2. 调用点旁路: 全部带遮罩对话框必须走 <aq-modal>(9 处调用覆盖 10 个开态, :open/:close/
         :close-args/mask-class/icon-class/width-class/body-class 接线逐点清点), 无遮罩异形
         speed-pop 直用 <aq-modal-head>; hist 的无 body 包裹/无动作栏由 bodyClass 空 +
         $slots.actions 条件渲染表达(空 .modal-actions 会多出 16px margin);
      3. 数据表旁路: 管理对话框双胞胎合并后 popovers.html 只剩一份 mgrDef 驱动模板
         (dialogs-mgr/popovers 零 mgrOpen 直判/直渲残留, dialogs.js mgrSubmitNew 分派,
         state.js mgrDef 两态字段表), modal-details 两套并一(state.js::modalDetailRows:
         verdict 在前 copy=false / details 在后 copy=true, 复制钮 String(d.value ?? '') 边界
         —— value===0 时旧写法 String(0 || '') 落空串不出钮)。
    """
    shared = os.path.join(STATIC_ROOT, "shared")
    tpl_dir = os.path.join(shared, "tpl")
    shell = open(os.path.join(tpl_dir, "dialog-shell.html"), encoding="utf-8").read()
    names = sorted(n for n in os.listdir(tpl_dir) if n.endswith(".html"))
    live = {n: re.sub(r"<!--[\s\S]*?-->", "", open(os.path.join(tpl_dir, n), encoding="utf-8").read()) for n in names}

    # 1. 三段外壳字面量只许在组件模板一处(剥注释后清点; 手抄副本回潮 = 散到别文件)
    #    dialogs.html 的动作栏例外 = speed-pop 自有(无遮罩异形不走 aq-modal, 恰 1 处)
    for needle, label, allow in (
        ('class="modal-title"', "标题头", ["dialog-shell.html"]),
        ('class="modal-actions"', "动作栏", ["dialog-shell.html", "dialogs.html"]),
        ('add-dialog-x', "关闭钮", ["dialog-shell.html"]),
    ):
        where = [n for n, t in live.items() if needle in t]
        assert sorted(where) == sorted(allow), \
            f"{label}({needle})超出允许面 {allow}(issue 26-10-20-2231), 现散在: {where}"
    assert live["dialogs.html"].count('class="modal-actions"') == 1, \
        "dialogs.html 的动作栏只许 speed-pop 自有一处(其余对话框的动作栏都在组件模板)"
    for n, t in live.items():
        assert '<div class="modal-mask' not in t, f"{n} 残留手写遮罩 div(应走 <aq-modal> 的 mask-class)"
    # 手势对成对挂在唯一遮罩上, 且经 $root 回调根方法(读根 _maskArmed)
    masks = re.findall(r'<div v-if="open" :class="maskClass"[\s\S]{0,240}?>', shell)
    assert len(masks) == 1, f"dialog-shell.html 应恰有 1 处遮罩, 实数 {len(masks)}"
    assert '$root.maskDownSelf($event)' in masks[0] and '$root.maskCloseIfArmed(close, ...closeArgs)' in masks[0], \
        "aq-modal 遮罩没接成对手势(mousedown 记臂位 + mouseup.self 才关; @click.self 会被拖选文字误判关窗)"
    assert 'v-if="$slots.actions" class="modal-actions"' in shell, \
        "动作栏必须 $slots.actions 条件渲染(hist 无底部条, 空 .modal-actions 会多出 16px margin)"
    assert '<div v-if="bodyClass" :class="bodyClass"><slot></slot></div>' in shell and "<slot v-else></slot>" in shell, \
        "中部必须 bodyClass 条件包裹(hist/确认框裸内容, 不加空 wrapper)"

    # 2. 调用点清点: 9 个 <aq-modal> 覆盖 10 个开态(mgr 两态一份模板) + speed 直用 head
    callsites = {
        "dialogs-mgr.html":
            (
                ':open="addOpen"', ':close="closeAddTorrent"', 'mask-class="modal-mask add-dialog-mask"',
                ':open="dirBrowse.open"', ':close="closeDirBrowse"', 'mask-class="modal-mask dir-browse-mask"'
            ),
        "dialogs.html":
            (
                ':open="statsOpen"', ':close="closeStats"', 'icon-class="ico-chart"',
                '<aq-modal-head icon="#i-gauge" title="限速" :close="closeSpeedDialog">'
            ),
        "popovers.html":
            (
                ':close="closeMgr"', ':open="metaOpen"', ':close="closeMeta"', ':open="modal.visible"',
                ':close="resolveModal"', ':close-args="[false]"', ':x="false"', ':open="historyOpen"',
                ':close="closeHistory"', 'icon-class="ico-history"', '<template #extra>', ':open="kbHelpOpen"',
                ':close="closeKbHelp"', '<template #title><h3>键盘快捷键</h3></template>', 'body-class="kb-help-body"'
            ),
        "move-dialog.html":
            (
                ':open="moveOpen"', ':close="closeMove"',
                ":width-class=\"['add-dialog move-dialog', { 'pop-open': movePathMenu }]\""
            ),
    }
    n_calls = 0
    for name, needles in callsites.items():
        for needle in needles:
            assert needle in live[name], f"{name} 缺 {needle}(对话框没走 <aq-modal>? 手抄外壳回潮)"
        n_calls += live[name].count("<aq-modal ")
    assert n_calls == 9, f"<aq-modal> 调用点应 9 处(mgr 两态共用一份), 实数 {n_calls}"
    assert 'v-if="mgrDef"' in live["popovers.html"], "管理对话框必须 v-if=mgrDef(表驱动单份)"

    # 3. 数据表与明细并一的单点
    st = open(os.path.join(shared, "state.js"), encoding="utf-8").read()
    dg = read_shared("dialogs.js")
    m = re.search(r"mgrDef\(\) \{(.*?)\n    \},", st, re.S)
    assert m, "state.js 找不到 mgrDef(管理对话框数据表被改名/挪走? 同步本守阵)"
    for needle in (
        'this.mgrOpen === "tag"', 'this.mgrOpen === "category"', "mgrDeleteTag(t)", "mgrEditCatPath(c.name)",
        "mgrDeleteCategory(c.name)", 'key: "tags"', 'key: "catName"', 'key: "catPath"', "addDisabled",
        "H&R / 集数 / MISSING", '"未设置保存路径"', "正在加载标签", "正在加载分类"
    ):
        assert needle in m.group(1), f"mgrDef 缺 {needle}(两态差异必须表驱动, 模板分支回潮)"
    assert "mgrSubmitNew()" in dg, "dialogs.js 缺 mgrSubmitNew(新建行提交分派单点)"
    assert 'mgrOpen === "tag"' not in live["popovers.html"] and 'mgrOpen === "category"' not in live["dialogs-mgr.html"], \
        "管理对话框两态分支回潮(popovers/dialogs-mgr 不许再按 mgrOpen 直判/直渲)"
    assert "mgr-list" not in live["dialogs-mgr.html"], "dialogs-mgr.html 残留管理列表(双胞胎合并后只许 popovers 一份)"
    mrows = re.search(r"modalDetailRows\(\) \{(.*?)\n    \},", st, re.S)
    assert mrows and "this.modal.verdict" in mrows.group(1) and "this.modal.details" in mrows.group(1) \
        and '"v" + i' in mrows.group(1) and "copy: false" in mrows.group(1) and "copy: true" in mrows.group(1), \
        "modalDetailRows 必须 verdict(copy:false, key 'v'+i)在前 + details(copy:true, key=label)在后"
    assert live["popovers.html"].count('class="modal-details"') == 1, "modal-details 渲染块必须恰一处(两套并一)"
    assert 'v-for="d in modalDetailRows"' in live["popovers.html"], "明细行必须消费 modalDetailRows 单点"
    assert "String(d.value ?? '')" in live["popovers.html"], \
        "复制钮显形必须 String(d.value ?? '')(value===0 时 String(0 || '') 落空串不出钮)"
    assert "String(d.value || '')" not in live["popovers.html"], "旧边界写法回潮"


# 添加种子三候选「最近使用」排序 node 电池(2026-10-09): 两个模块级纯函数
# _addOrderByRecent/_addNormPath 真跑。无 node 静默跳过(与 _NODE_QB_TRAFFIC_PROBE 同口径)。
_NODE_ADD_RECENT_PROBE = r"""
const fs = require("fs");
global.window = {};
eval(fs.readFileSync(process.argv[1], "utf8"));
const checks = [];
const eq = (n, got, want) => checks.push([n, JSON.stringify(got) === JSON.stringify(want)]);
eq("路径归一: 反斜杠转正斜杠", _addNormPath("R:\\Seeds\\A"), "R:/Seeds/A");
eq("路径归一: 压重复斜杠", _addNormPath("R://Seeds///A"), "R:/Seeds/A");
eq("路径归一: 首尾斜杠保留", _addNormPath("/mnt//media/"), "/mnt/media/");
eq("路径归一: UNC 开头双斜杠豁免", _addNormPath("\\\\NAS\\share//dl"), "//NAS/share/dl");
eq("路径归一: 三斜杠开头收敛到两个", _addNormPath("///NAS/share"), "//NAS/share");
eq("路径归一: 空/null/未定义安全", [_addNormPath(""), _addNormPath(null), _addNormPath(undefined)], ["", "", ""]);
const m = new Map([["Movies", 300], ["TV", 100], ["Anime", 200]]);
eq("最近使用降序", _addOrderByRecent(["TV", "Movies", "Anime"], m), ["Movies", "Anime", "TV"]);
eq("未用过落末尾并按字母序", _addOrderByRecent(["Zeta", "TV", "Alpha", "Movies"], m),
   ["Movies", "TV", "Alpha", "Zeta"]);
eq("表空退化纯字母序", _addOrderByRecent(["b", "a", "C"], new Map()), ["a", "b", "C"]);
eq("表为 null 不炸", _addOrderByRecent(["b", "a"], null), ["a", "b"]);
eq("全部时间 0 按字母序", _addOrderByRecent(["c", "a", "b"], new Map([["c", 0], ["a", 0], ["b", 0]])),
   ["a", "b", "c"]);
eq("部分命中: 命中者在前未命中按字母序", _addOrderByRecent(["Hit", "Miss", "Aaa"], new Map([["Hit", 5]])),
   ["Hit", "Aaa", "Miss"]);
const src = ["b", "a"];
_addOrderByRecent(src, new Map());
eq("纯函数不改入参", src, ["b", "a"]);
eq("大时间戳仍降序(int32 溢出面)", _addOrderByRecent(["Old", "New"],
   new Map([["Old", 1700000000], ["New", 1900000000]])), ["New", "Old"]);
console.log(JSON.stringify({ ok: checks.filter((c) => c[1]).length, total: checks.length,
  failed: checks.filter((c) => !c[1]).map((c) => c[0]) }));
"""


def test_frontend_add_options_recent_order():
    """添加种子三候选「最近使用」排序守阵(2026-10-09 用户动议: 保存路径/分类/标签按最近使用排序)

    口径定案 = **由种子记录派生**(非本机存储): 「最近使用」= 该值下种子 added_on 的最大值。
    数据面**跨视图自取数**(`_addRecencyRows`, 与 filters.js::facetRows 同族): 添加种子入口是
    顶栏常驻, 而 /api/state 按 viewMode 裁剪阵列(辅种页只回 groups + singles / 追剧页回
    shows + groups + singles / 种子页只回 torrents)⇒ 直读 this.torrents 会在默认辅种页拿到
    空表、排序**静默退化**成字母序(2026-10-09 e2e 首跑实测抓到; 判据同 pitfalls/web-ui/
    contract-api.md「跨视图的常驻消费者不能依赖按视图裁剪的阵列」)。两类故障形态机械钉住:
    1. 排序语义(node 真跑 _addOrderByRecent/_addNormPath): 最近使用降序 -> 未用过(时间 0)落
       末尾并按字母序 -> 表空/表 null/值未命中一律退化纯字母序(候选未到位时零观感差异);
       纯函数不改入参(改了会把传进来的候选数组原地打乱)。路径归一必须与后端
       infra/utils.path_normalize 同口径(反斜杠转正斜杠 + 压重复斜杠, 首尾斜杠保留,
       UNC 开头双斜杠豁免) ——
       两侧不同径则 /api/paths 的**已归一**路径与取数行的 qB **原文** save_path 对不上,
       时间表恒不命中, 功能静默退化成纯字母序(不报错、不白屏, 只是"排序没生效");
    2. 接线(静态): loadAddOptions 三个候选都过 _addOrderByRecent 单点(不是各自 .sort()),
       pick 不得再内联 .sort(字母序单点收进纯函数, 两处各写一遍即漂移); 时间表由
       _addRecencyMaps 经 _addRecencyRows 现算且三键齐全, 路径侧必须过 _addNormPath;
       _addRecencyRows 必须按 viewMode 分支且三来源(torrents / singles / decoratedGroups
       的 members)齐全 —— 缺一支即该视图下排序失效。
       无 node 时纯函数电池静默跳过, 但模块级定义与接线断言照常生效(不引入 skip)。
    """
    shared = os.path.join(STATIC_ROOT, "shared")
    at = open(os.path.join(shared, "add_torrent.js"), encoding="utf-8").read()

    # 0. 模块级定义(探针与运行时共用同一份; 缺了则无 node 环境也当场红)
    assert re.search(r"^function _addOrderByRecent\(", at, re.M), \
        "add_torrent.js 缺模块级 _addOrderByRecent(排序单点; 探针与运行时同源)"
    assert re.search(r"^function _addNormPath\(", at, re.M), \
        "add_torrent.js 缺模块级 _addNormPath(路径归一同源)"

    # 1. 纯函数真跑(有 node 时)
    node = shutil.which("node")
    if node:
        proc = subprocess.run(
            [node, "-e", _NODE_ADD_RECENT_PROBE,
             os.path.join(shared, "add_torrent.js")],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace"
        )
        assert proc.returncode == 0, f"_addOrderByRecent node 电池跑挂: {proc.stderr.strip()}"
        report = json.loads(proc.stdout.strip().splitlines()[-1])
        assert report["failed"] == [], \
            f"最近使用排序电池 {report['ok']}/{report['total']} 过, 失败: {report['failed']}"

    # 2. 接线: 三个候选都过排序单点
    body = re.search(r"async loadAddOptions\(\) \{(.*?)\n    \},", at, re.S)
    assert body, "add_torrent.js 找不到 loadAddOptions(改名或挪走了? 同步本守阵)"
    b = body.group(1)
    for opt, key in (("addCatOptions", "cat"), ("addTagOptions", "tag"), ("addPathOptions", "path")):
        assert re.search(rf"this\.{opt} = _addOrderByRecent\(\w+, recent\.{key}\);", b), \
            f"loadAddOptions 的 {opt} 没过 _addOrderByRecent 排序单点(最近使用排序对该列失效)"
    assert "_addRecencyMaps()" in b, "loadAddOptions 未从 _addRecencyMaps 取时间表"
    assert ".sort((a, b) => a.localeCompare(b))" not in b, \
        "loadAddOptions 的 pick 仍内联字母序 .sort —— 排序单点必须只在 _addOrderByRecent 里(两处各写一遍即漂移)"

    # 3. 时间表单点: 从跨视图取数行现算, 三键齐全, 路径过归一
    maps = re.search(r"_addRecencyMaps\(\) \{(.*?)\n    \},", at, re.S)
    assert maps, "add_torrent.js 找不到 _addRecencyMaps(三候选时间表单点)"
    mb = maps.group(1)
    assert "this._addRecencyRows()" in mb, \
        "_addRecencyMaps 必须走跨视图取数单点 _addRecencyRows(直读 this.torrents 会在默认辅种页恒空)"
    for needle in ("r.added_on", "r.category", "r.save_path", "r.tags"):
        assert needle in mb, f"_addRecencyMaps 缺 {needle}(三候选的时间表缺一即该列排序失效)"
    assert "_addNormPath(r.save_path)" in mb, \
        "_addRecencyMaps 的路径键必须过 _addNormPath(缺位 = 与 /api/paths 不同径, 路径排序恒失效)"
    assert "return { cat, tag, path };" in mb, "_addRecencyMaps 必须回三键 {cat, tag, path}"

    # 4. 跨视图取数单点: 添加种子入口是顶栏常驻, 而 /api/state 按 viewMode 裁剪
    #    (VIEW_ARRAYS: 辅种页只回 groups + singles / 追剧页回 shows + groups + singles /
    #    种子页只回 torrents) ⇒ 只读 this.torrents 时用户在默认辅种页开窗拿到空表, 排序
    #    静默退化成纯字母序(2026-10-09 e2e 首跑实测)。三支缺一即该视图下排序失效。
    rows = re.search(r"_addRecencyRows\(\) \{(.*?)\n    \},", at, re.S)
    assert rows, "add_torrent.js 找不到 _addRecencyRows(跨视图取数单点, 与 filters.js::facetRows 同族)"
    rb = rows.group(1)
    assert 'this.viewMode === "torrents"' in rb, "_addRecencyRows 必须按 viewMode 分支(种子页平铺 / 其余并集)"
    for needle in ("this.torrents", "this.singles", "this.decoratedGroups", "g.members"):
        assert needle in rb, \
            f"_addRecencyRows 缺 {needle}(VIEW_ARRAYS 逐视图裁剪, 缺一支 = 该视图下排序静默退化)"


def test_frontend_busy_skeleton_single_point():
    """busy+try+反馈+finally 骨架单点守阵(issue 26-10-20-2231) —— dialogs.js 三 helper 在册
    (_mgrRun 管理对话框写操作 / _panelLoad 面板加载与 tm 槽回执 / _postWaitCmd POST+waitCmd 三态
    toast) + 19 处调用点接线数对账(dialogs 14: mgr 5 + 面板加载 5 + POST 4; config_hub 5: tm 族
    4 槽 + 一键导入) + finally 复位保底必须住在单点内(漏 finally = 面板永久转圈) + 裸 busy 置位
    反向断言(再手抄 = 破单点, 回潮即红; metaBusy 两处例外 = metaSetCategory/metaAddNewTags 过闸
    占闸, R4 终审修复面 —— 计数恰 2 + 占闸/就地复位同住各自方法, 详见第 4 段)。"""
    dlg = read_shared("dialogs.js")
    hub = read_shared("config_hub.js")
    # 1. 三单点在册(dialogs.js 是骨架单点文件, config_hub.js 经同一根实例混入调用)
    for token in (
        "async _mgrRun(fn, okMsg, errMsg)",
        "async _panelLoad(obj, fn, opts)",
        "async _postWaitCmd(busyObj, busyKey, url, body, opts)",
    ):
        assert token in dlg, f"shared/dialogs.js 缺 busy 骨架单点 {token}(改名或挪走了? 同步本守阵)"
    # 2. 接线数对账(19 处全走单点; 少一处 = 有调用点被改回裸骨架或漏接)
    assert dlg.count("this._mgrRun(") == 5, "dialogs.js _mgrRun 接线数漂了(mgr CRUD 应为 5 处)"
    assert dlg.count("this._panelLoad(") == 5, "dialogs.js _panelLoad 接线数漂了(面板加载应为 5 处)"
    assert dlg.count("this._postWaitCmd(") == 4, "dialogs.js _postWaitCmd 接线数漂了(POST+waitCmd 应为 4 处)"
    assert hub.count("this._panelLoad(") == 5, "config_hub.js _panelLoad 接线数漂了(tm 族 4 处 + 一键导入 1 处)"
    # 3. finally 复位保底必须住在单点里(收编动机: 漏 finally 的症状是面板永久转圈)
    m = re.search(r"async _mgrRun\(fn, okMsg, errMsg\) \{.*?\n    \},", dlg, re.S)
    assert m and "this.mgrBusy = false" in m.group(0), "_mgrRun 必须 finally 复位 mgrBusy"
    m = re.search(r"async _panelLoad\(obj, fn, opts\) \{.*?\n    \},", dlg, re.S)
    assert m and "obj[o.loading] = false" in m.group(0), "_panelLoad 必须 finally 复位 loading 位"
    m = re.search(r"async _postWaitCmd\(busyObj, busyKey, url, body, opts\) \{.*?\n    \},", dlg, re.S)
    assert m and "busyObj[busyKey] = false" in m.group(0), "_postWaitCmd 必须 finally 复位 busy 位"
    # 4. 裸骨架散写反向断言: 这些 busy 置位原先各处手抄, 收敛后只许出现在单点内(回潮 = 破单点)
    #    metaBusy 例外收紧(R4 终审修复 + 增量轮): metaSetCategory/metaAddNewTags 过闸同步占闸是
    #    _postWaitCmd 单点之外仅有的两处合法置位 —— 各自的候选资源创建 POST(/api/categories 与
    #    /api/tags)在单点之前 await, 不占闸则该窗口内二次调用漏闸并发; 复位仍归单点 finally
    #    (各自提前 return 就地复位)。计数对账: 恰 2 处且与各自就地复位同住方法体, 再散写 = 回潮即红。
    assert dlg.count("this.metaBusy = true") == 2, \
        "dialogs 域 metaBusy 置位应恰 2 处(metaSetCategory/metaAddNewTags 过闸占闸; 其余一律走 _postWaitCmd 单点)"
    m = re.search(r"async metaSetCategory\(name\) \{(.*?)\n    \},", dlg, re.S)
    assert m and "this.metaBusy = true" in m.group(0) and "this.metaBusy = false" in m.group(0), \
        "metaBusy 占闸与未变化静默返回的就地复位必须同住 metaSetCategory(挪走 = 同步本守阵)"
    m = re.search(r"async metaAddNewTags\(\) \{(.*?)\n    \},", dlg, re.S)
    assert m and "this.metaBusy = true" in m.group(0) and "this.metaBusy = false" in m.group(0), \
        "metaBusy 占闸与空输入提前 return 的就地复位必须同住 metaAddNewTags(挪走 = 同步本守阵)"
    for gone in (
        "this.statsLoading = true",
        "this.mgrLoading = true",
        "this.logs.loading = true",
        "this.historyLoading = true",
        "this.speedOverride.busy = true",
        "this.speedAlt.busy = true",
        "this.altToggling = true",
    ):
        assert gone not in dlg, f"dialogs.js 又出现裸骨架散写 {gone}(应走 _mgrRun/_panelLoad/_postWaitCmd 单点)"
    for gone in (
        "this.tm.loading = true",
        "this.tm.saving = true",
        "this.tm.autoBusy = true",
        "this.tm.pick.loading = true",
        "this.hub.importing = true",
    ):
        assert gone not in hub, f"config_hub.js 又出现裸骨架散写 {gone}(应走 dialogs.js::_panelLoad 单点)"


# 浮层视口夹取几何单点 node 电池(issue 26-10-20-2231): 四入口七型真跑 + 与旧手写式
# (入池前的四种书写: 标准夹取 / openFilePrio 横轴书写 / hubAsk 纵轴 if 链 / 居中夹取,
# 以及两个 Math.max 兜底)网格逐点代数等价 —— 重构改坏几何即红。无 node 静默跳过。
_OVERLAY_FIT_NODE_PROBE = r"""
const fs = require("fs");
global.window = { innerWidth: 1440, innerHeight: 900 };
eval(fs.readFileSync(process.argv[1], "utf8"));
const F = window.AQB_OVERLAY_FIT;
const checks = [];
const ok = (n, c) => checks.push([n, !!c]);
const eq = (n, got, want) => checks.push([n, got === want]);
ok("EDGE 缺省 8", F.EDGE === 8);
// clampAxis 七型
eq("透传", F.clampAxis(100, 150, 1440), 100);
eq("钳下缘", F.clampAxis(2, 150, 1440), 8);
eq("钳上缘", F.clampAxis(1400, 150, 1440), 1282);
eq("浮层宽过可用空间贴上缘", F.clampAxis(700, 1500, 1440), 8);
eq("edge 显式传参(12px 两处用)", F.clampAxis(2, 150, 1440, 12), 12);
// 探针: 右缘(左缘起算 gap=0 与父项右缘+缝 gap=4 两种旧书写)
ok("probeRight 命中", F.probeRight(1400, 150, 4) === true);
ok("probeRight 不命中", F.probeRight(100, 150, 4) === false);
ok("probeRight gap 缺省 0", F.probeRight(1290, 150) === true);
ok("probeLeft 命中", F.probeLeft(100, 380, 10) === true);
ok("probeLeft 不命中", F.probeLeft(800, 380, 10) === false);
// fitInViewport: el 实测与 w/h 估算两路同值
const el = { offsetWidth: 214, offsetHeight: 222 };
const p1 = F.fitInViewport(el, 1400, 900);
eq("fit el x", p1.x, 1218); eq("fit el y", p1.y, 670);
const p2 = F.fitInViewport(null, 1400, 900, { w: 214, h: 222 });
eq("fit est x", p2.x, 1218); eq("fit est y", p2.y, 670);
// 代数等价: 旧手写式网格逐点同值
const oldA = (v, s, vp, e) => Math.max(e, Math.min(v, Math.max(e, vp - s - e)));
const oldB = (v, s, vp, e) => Math.min(Math.max(e, v), Math.max(e, vp - s - e));
const oldC = (v, s, vp, e) => { let t = v; if (t + s > vp - e) t = vp - s - e; if (t < e) t = e; return t; };
const oldCenter = (v, s, vp, e) => Math.max(e, Math.min(vp - s - e, v));
let diff = 0;
for (const vp of [320, 640, 1024, 1440, 1920])
  for (const s of [150, 214, 380, 500])
    for (const v of [-20, 0, 5, 8, 12, 300, 1300, 3000])
      for (const e of [8, 12]) {
        const a = F.clampAxis(v, s, vp, e);
        if (a !== oldA(v, s, vp, e) || a !== oldB(v, s, vp, e)
            || a !== oldC(v, s, vp, e) || a !== oldCenter(v, s, vp, e)) diff++;
        if (F.clampAxis(vp - s, s, vp, e) !== Math.max(e, vp - e - s)) diff++;  // 右缘/底部两兜底
      }
ok("旧手写式代数等价(网格零差)", diff === 0);
console.log(JSON.stringify({ ok: checks.filter((c) => c[1]).length, total: checks.length, failed: checks.filter((c) => !c[1]) }));
"""


def test_overlay_fit_single_point():
    """浮层「贴边留白 + 视口夹取」几何单点守阵(issue 26-10-20-2231) ——
    ① 单点模块 shared/overlay_fit.js 在盘且四入口齐全(EDGE=8 / clampAxis / probeRight /
       probeLeft / fitInViewport), 三份 tpl-manifest 同点登记且装载序在首个消费方
       config_hub.js 之前(漏登记或序错 = 消费方取别名拿到 undefined, 开层即抛);
    ② 七个消费文件全部经 FIT 别名走单点, 接线数逐文件对账(ui_feedback 7 / menu 5 /
       config_hub 4 / hr 3 / drawer 2 / columns 3 / dialogs 1);
    ③ 手写夹取式零残留(8/12 字面量夹取、PAD、margin=8、EDGE=8 等回潮即红);
    ④ 12px 两处(hubAsk / speed-pop)显式命名传参 + 注释在位(不是默默手写字面量);
    ⑤ 顶层 const/let 跨文件撞名零容忍(本轮实测事故: 七文件各写顶层 const FIT, 经典
       脚本顶层 let/const 是全局词法环境, 后六个文件 SyntaxError、mixin 静默不注册、
       整页崩且静态守阵全绿 —— 跨文件别名只许方法内取或包 IIFE);
    ⑥ 行为面 node 电池: 四入口七型 + 与旧手写式网格代数等价(无 node 静默跳过);
    真实浏览器几何由 e2e/menus.spec.mjs 的 CTX-fit 左右缘诸例盯。"""
    shared = os.path.join(STATIC_ROOT, "shared")
    fit_js = open(os.path.join(shared, "overlay_fit.js"), encoding="utf-8").read()
    files = {
        name:
            (
                read_shared(name) if name in ("config_hub.js", "drawer.js", "columns.js", "dialogs.js") else
                open(os.path.join(shared, name), encoding="utf-8").read()
            )
        for name in ("ui_feedback.js", "menu.js", "config_hub.js", "hr.js", "drawer.js", "columns.js", "dialogs.js")
    }
    # 1. 单点在册(四入口 + EDGE 缺省 8)
    assert "window.AQB_OVERLAY_FIT" in fit_js, "缺单点 overlay_fit.js(issue 26-10-20-2231 的收敛落点)"
    for token in (
        "var EDGE = 8;", "function clampAxis(", "function probeRight(", "function probeLeft(", "function fitInViewport("
    ):
        assert token in fit_js, f"overlay_fit.js 缺入口 {token}(改名或挪走了? 同步本守阵)"
    # 2. 三清单同点登记 + 装载序在首个消费方 config_hub.js 之前
    for ui in _UI_ALL:
        scripts = _ui_manifest(ui)["scripts"]
        assert "/shared/overlay_fit.js" in scripts, \
            f"{ui} 清单漏挂 overlay_fit.js(消费方运行时会取到 undefined)"
        assert scripts.index("/shared/overlay_fit.js") < scripts.index("/shared/config_hub.js"), \
            f"{ui} 装载序错: overlay_fit.js 须排在首个消费方 config_hub.js 之前"
    # 3. 消费面接线数对账(七个文件全部走 FIT; 少一处 = 该处回退成手写)
    for name, text in files.items():
        assert "window.AQB_OVERLAY_FIT" in text, f"{name} 缺 FIT 别名(几何回退手写了?)"
    wiring = {
        "ui_feedback.js": {
            "FIT.EDGE": 2,
            "FIT.clampAxis": 3,
            "FIT.fitInViewport": 1,
            "FIT.probeRight": 1
        },
        "menu.js": {
            "FIT.EDGE": 1,
            "FIT.clampAxis": 1,
            "FIT.probeRight": 2,
            "FIT.probeLeft": 1
        },
        "config_hub.js": {
            "FIT.clampAxis": 2,
            "FIT.probeRight": 1,
            "FIT.probeLeft": 1
        },
        "hr.js": {
            "FIT.EDGE": 1,
            "FIT.clampAxis": 2
        },
        "drawer.js": {
            "FIT.clampAxis": 2
        },
        "columns.js": {
            "FIT.EDGE": 2,
            "FIT.clampAxis": 1
        },
        "dialogs.js": {
            "FIT.clampAxis": 1
        },
    }
    for name, wants in wiring.items():
        for token, n in wants.items():
            got = files[name].count(token)
            assert got == n, f"{name} 的 {token} 接线数 {got} != {n}(调用点被改写了? 同步本守阵)"
    # 4. 手写夹取式零残留(收编动机就是这些各处手抄的边距与夹取; 词界防误伤
    #    SPEED_PAD = 12 这类显式命名的合法常量)
    residue = (
        r"Math\.max\(8,",
        r"Math\.min\(Math\.max\(8",
        r"Math\.max\(12,",
        r"innerWidth - 8",
        r"innerHeight - 8",
        r"innerWidth - 12",
        r"innerHeight - 12",
        r"(?<![A-Za-z_])PAD = 8",
        r"(?<![A-Za-z_])PAD = 12",
        r"(?<![A-Za-z_])margin = 8",
        r"(?<![A-Za-z_])EDGE = 8",
    )
    for name, text in files.items():
        for pat in residue:
            assert not re.search(pat, text), \
                f"{name} 又出现手写几何 /{pat}/(应收敛到 overlay_fit.js 单点)"
    # 5. 12px 两处显式命名 + 注释在位(hubAsk / speed-pop; 行为零变化口径保留现值)
    assert "const EDGE = 12, gap = 10;" in files["config_hub.js"], \
        "hubAsk 的 12px 必须显式命名传参(回退成手写字面量即红)"
    assert "const SPEED_PAD = 12;" in files["dialogs.js"], \
        "speed-pop 的 12px 必须显式命名(SPEED_PAD)传参"
    # 6. 顶层 const/let 跨文件撞名零容忍 —— 本轮实测事故: 收敛时七个文件各写了一个顶层
    #    const FIT, 而经典脚本的顶层 let/const 进**全局词法环境**(跨 <script> 共享):
    #    首个声明(config_hub.js)之后的六个文件全部 SyntaxError, window.AQB_* mixin 一个
    #    都没注册, 整页崩, 且静态守阵全绿(只有真浏览器现形)。跨文件别名只许方法内取或
    #    包 IIFE(参照 drawer_tpl 变体的 const T/R/H/P 全在 IIFE 内)。
    seen = {}
    for root, dirs, fnames in os.walk(shared):
        dirs[:] = [d for d in dirs if d != "vendor"]
        for fn in fnames:
            if not fn.endswith(".js"):
                continue
            path = os.path.join(root, fn)
            rel = os.path.relpath(path, shared).replace(os.sep, "/")
            for m in re.finditer(r"(?m)^(?:const|let)\s+([A-Za-z_$][\w$]*)", open(path, encoding="utf-8").read()):
                name = m.group(1)
                assert name not in seen, (
                    f"shared/{rel} 与 shared/{seen[name]} 顶层同名 const/let {name} —— "
                    "经典脚本顶层 let/const 是全局词法环境, 撞名 = 后一个文件 SyntaxError、"
                    "mixin 静默不注册(整页崩, 仅真浏览器现形); 跨文件别名须方法内取或包 IIFE"
                )
                seen[name] = rel
    # 7. 行为面: node 电池(四入口七型 + 旧手写式代数等价)
    node = shutil.which("node")
    if not node:
        return
    proc = subprocess.run(
        [node, "-e", _OVERLAY_FIT_NODE_PROBE,
         os.path.join(shared, "overlay_fit.js")],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    assert proc.returncode == 0, f"overlay_fit node 电池跑挂: {proc.stderr.strip()}"
    report = json.loads(proc.stdout.strip().splitlines()[-1])
    assert report["failed"] == [], f"几何电池 {report['ok']}/{report['total']} 过, 失败: {report['failed']}"
