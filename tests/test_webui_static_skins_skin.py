"""test_webui_static_skins_skin 测试计划: webui 前端资产静态守阵: 皮肤清单 / CSS / 挂件类名

## 测试计划(每个测试函数一条)
- test_frontend_static_bundle_health: 前端静态资源静态守阵(冲突标记/注释孤儿续行/node --check 语法校验/CSS 规则漏闭合/CSS 注释提前终止/<transition> 吞弹窗/静态引用缺失/追剧视图集成员取 hash 未走 memberHashesOf/STATE_RANK 与后端 _SHOW_STATE_RANK 漂移 + STATE_RANK_LAST 兜底秩与 _SHOW_STATE_RANK_LAST 一致 / 键位归一化正则 KB_DEF_RE 与后端 _KEYS_SERIAL_RE 逐字一致 / ETA 哨兵与后端 _ETA_SENTINEL 跨层一致(全树零命中即红) / 页面挂件类名必须有对应 CSS 规则 / 列模型每列必须有值单元格分支+默认隐藏单点接线 —— 均为"pytest 全绿但界面废掉"的故障形态; 计划 26-10-31-2316 S2 起 @starting-style 计入容器型 at-rule、shared/fx/fx.js 曾以"待接线豁免"登记(S6 挂 flux shell 静态 script 后豁免已删) / flux 弹窗毛玻璃 vs 浮层不透明底对照(2026-11-03, _scan_flux_modal_frost) / 右键次级子面板宽: 四皮肤 .ctx-sub min-width 互证同值 260px + menu.js 首帧估宽算术绑定 260+12(2026-11-13, _scan_ctx_sub_width)
- test_frontend_template_split_wiring: 模板分片接线守阵(26-09-26 拆分 plans/26-09-26-2233 W1) —— 清单完整性(漏挂=整块消失 / 404=整页占位 / into 非法)+ 双 UI 分片名单同名同序 + 聚合标签配平 + shell≤256 行(S1 定 200, 26-10-06-0838 S5/S6 各 +3, R2 26-10-09-2219 S1 +4, W6 26-10-13-0811 +2, 26-10-30-0217 阶段2 row_lang.css 挂载 +2 → 218, 26-11-01-0553 hscroll.css 挂载 +2 → 220, 26-10-31-2316 S6 fx 三件挂 flux +7 → 227, S6 后半 fx 挂载面(fx-mount.css+fx-mount.js, flux 专属) +6 → 233, R4 域片段挂载(console_hub.css 拆 4 link 净 +3 + 7 域 20 片段 script)+23 → 256)/单分片≤400 行 + 清单脚本序(vendor 首 app.js 尾) + 各皮肤 CSS 链接序(atlas/console/flux(fork 自 console, S5 收编): style→components→views→dialogs; prism: tokens→五主题→base→components→views→dialogs, 弹窗层必须最后; shared 层 row_lang.css 在各皮肤 views.css 之后, 计划 26-10-30-0217 阶段2)与单文件 700 行体量口径(prism/css/views.css 818 行存量冻结, 只许减不许增)
- test_frontend_skin_css_token_parity: 各皮肤令牌**名集**相等守阵(issue 26-10-20-2231; 26-11-01 S5 收编 flux) —— 皮肤少声明令牌 = 该皮肤下 `var(--x)` 整条声明在计算值阶段作废且无报错(星图此前少 3 个字体令牌 86 vs 89, 自己 4 处 `var(--font-mono)` 裸引用全程失效、共用层只能各写兜底链); 钉名集相等(取值自由), 差异按缺/多两侧成对报出
- test_frontend_shell_sprite_login_parity: 各皮肤 index.html shell 内联段守阵(issue 26-10-20-2231; S5 收编 flux) —— sprite 段(80 行/67 symbol)逐字相等(manifest 已被 split_wiring 钉死, 本守阵补上 sprite 与 login)+ #app+login 段(注释/空行归一后, 皮肤说明注释为合法差异不参与比对)相等; symbol 数下限防"sprite 整体外提成共享文件后各份同时消失、相等断言恒真"; 失败信息提示"改图标/改登录遮罩须各皮肤同步"
- test_frontend_button_system_paired: 按钮体系(.bt)迁移守阵 —— ce-btn/ce-icon 全语料零残留、.bt 六变体各套 CSS 成对定义(atlas/prism/console/flux, S5 收编 flux)、atlas/prism 模板 bt 用量逐类相等、双色令牌(on-accent/on-accent-ink/on-error)星图 :root + 棱镜五主题成对声明
- test_frontend_fx_wiring: fx 动效库挂行守阵(计划 26-10-31-2316 S6 前半 + 后半) —— shared/fx 三件只挂 flux: flux shell 恰挂 fx.css/fx-presets.css 各一次(head link, 级联序排本皮肤全部 CSS 之后)与 fx.js 一次(shell 静态 script, 不进 tpl-manifest —— 四套清单守阵钉逐项相等), S6 后半追加 flux 专属挂载面 fx-mount.css(link, 排 fx 三件之后)与 fx-mount.js(script)恰一次、三旧皮肤对 /shared/fx/ 与 fx-mount 零引用(D14 隔离反向钉)、flux <html> 带 data-fx-preset="glass"(S4 主 preset 拍板)、fx.js REGISTRY.effects 逐名能在 fx.css 找到 [data-fx~="名"] 规则且 presets 逐名能在 fx-presets.css 找到配方块(漏 CSS = audit 放行但样式静默不生效; 2026-11-03 用户要求移除 flux 右键强调动效 ⇒ row-flash/D4-3 连同 keyframes/RM 降级/注册项退役, 注册表 26 名); R1 精修(26-10-31-2316 §06)追加回归钉: fx-mount.css 不得复活行板 :hover gradient 叠底(B2 行板/首格悬停管线分家)/fx-mount.js 滚动干预三符号(ensureFocusedVisible/scheduleReveal/revealFocusedRow)反向钉不在档(F7c: R3 精修退役 R1 B3 自定义回拉, 滚动单点交还 shortcuts.js 原版逻辑; F7d: 落定回执链路钉 —— fx-mount.js transitionend/兜底定时器/单发守卫 + state.js dock 第二参重入原版 _kbScrollRowIntoView; F7e(R5 精修): push 位移本体弃用反向钉(fx-mount.css/js 零 push 载体/--fx-push-y 规则, 打点实证 scrollY=0 时位移把聚焦行推出视野且滚动不可恢复) + 两段动效落点钉(dialogs.css 面板底部上滑 translateY(100%) 消费 --fx-dur-panel/--fx-ease-out, fx-mount.css 面板开着 scroll-behavior:smooth 的 :has 作用域), 缺一即回退到「聚焦行终位被推出视野」的 D3-4 三轮报障缺陷; R5#179: dock(true) 须真武装 armSettle 兜底定时器(此前零调用, 回执丢失场景 fx-glide 恒驻留))
- test_frontend_fx_site_chip_shape_layering: flux 站点 chip 形状分层守阵(计划 26-11-10-0921 W2 + S4) —— fx-mount.css 的 html[data-fx-preset] .site-chip 本体规则体必须含 clip-path: none(本体重新持裁剪 = box-shadow 辉光被整圈裁掉, 用户报「辉光仅显示一侧或两侧」回归) + .site-chip::before 规则体含切角 polygon(3px 0, ...) 逐字(3px 微切角视觉 = R3「逐字恢复」拍板); components.css:332 本体 clip-path 被覆盖而非删除的事实不设防(700 行体量断言只限净增行, 钉不住减行删除), 级联正确性由同批 W2 e2e 主判据(computed clipPath === 'none')兜底; S4(f7f4658c)状态边线迁移面: ::before 三条边线载体(paused/other --paused-line、search-hit --accent-line、sa-no-conf dashed --warn)+ 本体三条关闭(box-shadow: none ×3 / border-bottom: 0)+ ::before 渐隐过渡段含 box-shadow var(--dur-fast), 缺任一半 = 边线消失或方角线双线叠画
- test_frontend_fx_tag_cat_chip_glow_layering: flux tag/cat chip 辉光放行 + H&R 竖线迁层守阵(计划 26-11-12-1012 S1+S2) —— 旧计划 26-11-10-0921 只救 .site-chip 本体裁剪, tag/cat chip 的 hover 辉光仍被两层裁掉(「辉光仅显示一侧或两侧」第二根因: 直接父容器 .g-tags/.m-tags/.g-cat/.m-cat 的 overflow:hidden 裁掉画在盒外的 box-shadow 外发光, components.css:340-341): S1 段逐字钉四祖先(html[data-fx-preset] 前缀, 不入四皮肤键集扫描)规则体含 overflow: clip + overflow-clip-margin: 16px(clip 非 visible = 不建滚动容器保留内容裁剪语义 I3, 标签全量展开换行行高与吸左首格几何不动; 16px = 12px blur + 3px spread + 1px 硬芯余量(stack 最大层 0 0 12px 3px), 零新增令牌 I2; .g-sites 本来无裁剪不加同款 D5); S2 段钉 .tag-chip 补 position: relative(基线 components.css:342 无定位包含块, .f-on:380 同值不冲突)+ .hr-pending/.hr-done::before 迁层三条(content:""/absolute/inset:0/pointer-events:none 共用绘制盒 + box-shadow: inset 2px 0 0 var(--hr-pending)/var(--hr-done) 两档语义色竖线)+ 本体 box-shadow: none 关闭(缺任一半 = hover 前后竖线消失或本体线与 ::before 线双线叠画, 同 site-chip S4 迁移面; HR = H&R 做种考核状态类, 非人力资源)+ ::before 渐隐过渡段(RM 媒体块内, box-shadow 段令牌逐字沿用 site-chip::before 渐隐段 --dur-fast/--ease, hr-pending<->hr-done 状态类切换竖线色渐变不跳变); any() 存在性断言只防删行/改值, hover 本体仍单独消费同一条 --fx-glow-stack, 级联胜负由 S3 像素采样 e2e 仲裁(纯静态/纯 computed 均对绘制层裁剪无感)
- test_frontend_console_square_radius: console 方角口径守阵(R1 精修 B1, 用户报「console 详情模板/文字元素出现圆角」) —— console/style.css 的 --radius-lg/--radius/--radius-sm 三令牌全 0px + console 自有 CSS 与 console 实际加载的四件共享面(row_lang/dt_table/hscroll/console_hub)的 border-radius 声明值全量白名单(0/999px 胶囊/小值/50%/var(--radius*)/inherit, 现存值盘点后冻结): flux 意图的圆角 16/10/6 写进共享面 = 三皮肤同时回归, 新值入列必须显式改白名单(有意识决策)
- test_frontend_tpl_ctl_bits_single_source

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
    _CONSOLE_RADIUS_ALLOW,
    _CSS_CONTAINER_AT,
    _EP_MEMBERS_RE,
    _FLUX_BACKDROP_BUDGET,
    _MSG_NEUTRAL_KINDS,
    _MSG_TONE_EXPECT,
    _NODE_SYNTAX_CHECK,
    _PAGE_HOOK_CLASSES,
    _PERF_BACKDROP_BANNED,
    _RADIUS_RE,
    _STATE_TOKEN_EXPECT,
    _args_texts,
    _assert_tags_balanced,
    _computed_body,
    _extract_column_keys,
    _first_arg_text,
    _section_members,
    _skip_braces,
    _skip_string,
    _strip_js_comments,
    _toast_kinds_in_use,
    _toast_literal_texts,
)
from webui_static_scan_css import (
    _scan_backdrop_filter,
    _scan_column_cells_paired,
    _scan_css_blocks,
    _scan_css_comments,
    _scan_progress_val_parity,
    _scan_state_color_tokens,
)
from webui_static_scan_js import (
    _scan_episode_member_hashes,
    _scan_eta_sentinel,
    _scan_filter_facets,
    _scan_frontend_assets,
    _scan_js_syntax_with_node,
    _scan_keys_serial_re,
    _scan_message_surface_parity,
    _scan_mixin_wiring,
    _scan_page_class_wiring,
    _scan_pending_settle,
    _scan_state_rank,
    _scan_template_transitions,
    _scan_toast_copy_two_part,
    _scan_ui_diff_registry,
)


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


def test_frontend_template_split_wiring():
    """模板分片接线守阵(2026-09-26 W1; 26-09-27 收敛后 = 单一语义源 shared/tpl): 清单完整性 + 差异口 + 聚合配平

    模板拆分/收敛后的静默故障形态(与 JS 片段的 _scan_mixin_wiring 同源):
      1. 分片文件在盘上但清单漏挂 —— boot 不注入, 该页面区整块消失(零报错);
      2. 清单挂了不存在的分片 / into 非法 —— boot fetch 404, 整页停在错误占位;
      3. 两套 shell 清单漂移(各自演化 parts/scripts)—— 单一语义模板下等于偷偷分裂出第二份模板;
      4. 绕开 UI 差异口私拷模板块(双模板副本的复发形态)—— 由 _scan_ui_diff_registry 钉住。
    另钉: 聚合标签配平(切割边界错位的兜底)、shell ≤256 行(S1 定 200, 26-10-06-0838 S5/S6 各 +3, R2 26-10-09-2219 S1 +4, W6 26-10-13-0811 dt_table.css 挂载 +2, issue 26-10-20-2231 prism dialogs.css 挂载 +2, 计划 26-10-30-0217 阶段2 row_lang.css 挂载(注释+link)+2 → 218; 计划 26-11-01-0553 shared/hscroll.css 挂载(注释+link)+2 → 220; 计划 26-10-31-2316 S6 fx 三件挂 flux(注释+2link+注释+script)+7 → 227; S6 后半 fx 挂载面(fx-mount.css 注释+link + fx-mount.js 注释+script, flux 专属)+6 → 233; R4 计划 26-11-02-2342 §07 域片段挂载(console_hub.css 拆 4 link 净 +3 + 7 域 20 片段 script)+23 → 256; 26-11-08 计划 26-11-07-2344 S3 flux 挂 relocate_pop.js 靠 hr.js 同行并排, 净 +0 → 256)/ 单分片 ≤400 行(popovers.html 例外 440, 26-11-08 计划 26-11-07-2344 S3 relPop 块)、清单脚本序(vendor 首 / app.js 尾)。
    """
    problems = []
    manifests = {}
    for ui in _UI_ALL:
        shell = open(os.path.join(STATIC_ROOT, ui, "index.html"), encoding="utf-8").read()
        udir = os.path.join(STATIC_ROOT, ui)
        mf = _ui_manifest(ui)
        manifests[ui] = mf
        n_shell = shell.count("\n") + (0 if shell.endswith("\n") else 1)
        if n_shell > 256:
            problems.append(
                f"{ui}/index.html {n_shell} 行, shell 体量上限 256"
                "(S1 定 200 = 核心层 1 行 + 首批 9 变体; 计划 26-10-06-0838 S5/S6 各 +3; "
                "R2 计划 26-10-09-2219 S1 起 drawer_pages classic 插件 +4; "
                "W6 计划 26-10-13-0811 shared/dt_table.css 挂载(注释+link)+2; "
                "issue 26-10-20-2231 prism/css/dialogs.css 挂载(注释+link)+2; "
                "计划 26-10-30-0217 阶段2 shared/row_lang.css 挂载(注释+link)+2 → 218; "
                "计划 26-11-01-0553 shared/hscroll.css 挂载(注释+link)+2 → 220; "
                "计划 26-10-31-2316 S6 fx 三件挂 flux(注释+2link+注释+script)+7 → 227; "
                "计划 26-10-31-2316 S6 后半 fx 挂载面(flux 专属: fx-mount.css 注释+link + fx-mount.js 注释+script)+6 → 233; "
                "R4 计划 26-11-02-2342 §07 域片段挂载(console_hub.css 拆 4 link 净 +3 + 7 域 20 个片段 script)+23 → 256)"
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
            # 单分片体量上限默认 400; settings-detail.html 是 HR 表 1(计划 26-10-01-2216 阶段2,
            # 拍板 2b 按站点明细表)的落点, 391 -> 435 行属功能增长不是拆分回潮, 单独点名给例外额度
            # (其余分片仍钉 400); 26-10-02-1936 阶段2 折叠头 + 覆盖式全屏覆盖层再涨 454 -> 473,
            # 额度提到 500; 26-10-04-0312 S4 表 3 拉取历史(全局 <details> 段)再涨 482 -> 539,
            # 额度提到 560 —— 该分片下次再长应把 speed/keys 等视图拆成独立分片 —— 切割须过
            # 等价性验证(pitfalls/web-ui/frontend-split.md), 不得顺手抽文件
            # 26-10-18(计划 26-10-17-1737 S6/S7)曾给 settings.html 开 440 的例外: 「全局流量来源」卡
            # 补了 provider 条件隐藏与单位下拉, 400 -> 418 行; 注释当时就写了「下次再长应先把该卡整体
            # 重构成独立组件」。26-10-18(计划 26-10-18-0813 B3/D15)正是这么做的 —— 三张卡并成
            # 「流量与限速」并抽成 aq-traffic-card + shared/tpl/traffic-card.html, settings.html 只剩
            # 一行挂载, 例外额度随之删除(不留给下一次"再加一点")。
            # 26-11-08(计划 26-11-07-2344 S3)给 popovers.html 开 440 的例外: 迁移悬停浮窗 relPop
            # teleport 块(+锚注释)按任务拍板落在 HR 弹窗同款锚旁, 397 -> 426 行 —— 该分片是全部
            # 悬停/链/确认浮层的既有单点, 不为 26 行再拆独立分片; 下次再长应把浮窗族拆出(同上口径)。
            name = os.path.basename(part["src"])
            cap = 560 if name == "settings-detail.html" else 440 if name == "popovers.html" else 400
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
        if ui in ("atlas", "console", "flux"):
            rels = [os.path.relpath(p, STATIC_ROOT).replace(os.sep, "/") for p in css_files]
            # flux 链尾多一件 fx-mount.css(S6 后半 fx 挂载面, flux 专属作用域 CSS,
            # 排 fx 三件之后 = 本皮肤全部 CSS 与 shared/fx 的最后一级联)
            expected_css = [
                f"{ui}/style.css", f"{ui}/css/components.css", f"{ui}/css/views.css", f"{ui}/css/dialogs.css"
            ]
            if ui == "flux":
                expected_css.append("flux/css/fx-mount.css")
            assert rels == expected_css, (f"{ui} CSS 链接顺序漂移: {rels}(级联序 = link 序; 拆分是连续字节切片, 重排顺序前先核对视觉等价)")
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
    # flux 收编(plan 26-10-31-2316 S5/D14): fork 只许换取值, 令牌名一个都不能少 —— 少名 = 该皮肤下
    # var(--x) 声明计算值阶段整条静默作废(风险表「flux 令牌静默失效」的守阵面)。
    sets = {ui: _tokens([os.path.join(STATIC_ROOT, ui, "style.css")]) for ui in ("atlas", "console", "flux")}
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

    # 2. .bt 体系块与变体在各套 CSS 成对定义(flux 收编 plan 26-10-31-2316 S5)
    variants = ["primary", "ghost", "danger", "danger-solid", "icon", "sm"]
    for css, name in (
        (atl_css, "atlas css 聚合(link 序)"),
        (pri_css, "prism/css/components.css"),
        (_ui_css_aggregate("console"), "console css 聚合(link 序)"),
        (_ui_css_aggregate("flux"), "flux css 聚合(link 序)"),
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


def test_frontend_fx_wiring():
    """fx 动效库挂行守阵(计划 26-10-31-2316 S6 前半 + 后半) —— shared/fx 三件与
    flux 专属挂载面(fx-mount.css/fx-mount.js)只挂 flux

    静默故障形态(fx 三件在盘上、pytest 却无从判红的挂载面问题):
      1. flux 漏挂/挂两次: fx.css/fx-presets.css 漏 = 库令牌与规则整族不在, S6 后半的
         data-fx 挂载全部静默不生效; 挂两次 = 配方重复进级联。S6 后半追加的挂载面
         (fx-mount.css 作用域挂载层 / fx-mount.js 状态驱动挂载器)同口径。
      2. 级联序漂移: fx 链接被挪到本皮肤 CSS 之前(共库层惯例 = 排最后, link 序即级联序);
         fx-mount.css 必须排 fx 三件之后(挂载面要覆盖 flux 既有同选择器规则)。
      3. 隔离反向破防: 三旧皮肤(atlas/prism/console)出现 /shared/fx/ 或 fx-mount 引用 ——
         D14 存量隔离拍板被顺手破坏, 三旧皮肤视觉漂移。
      4. 注册表与 CSS 脱钩: fx.js REGISTRY 里有效果名而 fx.css 没有对应 [data-fx~=] 规则
         —— audit 放行但样式静默不生效(与「audit 报未知」相反方向的漏补)。
    fx.js/fx-mount.js 走 shell 静态 <script> 而非 tpl-manifest: 四套清单守阵(split_wiring)
    钉逐项相等, fx 只服务 flux, 进清单就得四套同挂 = 破隔离。
    """
    flux_shell = open(os.path.join(STATIC_ROOT, "flux", "index.html"), encoding="utf-8").read()
    # 1. flux 恰挂一次
    for needle, why in (
        ('href="/shared/fx/fx.css"', "fx 库基线(fx.css)漏挂/重复挂"),
        ('href="/shared/fx/fx-presets.css"', "fx 风格配方(fx-presets.css)漏挂/重复挂"),
        ('src="/shared/fx/fx.js"', "fx 挂载器(fx.js)漏挂/重复挂"),
        ('href="/flux/css/fx-mount.css"', "fx 作用域挂载层(fx-mount.css, S6 后半)漏挂/重复挂"),
        ('src="/flux/fx-mount.js"', "fx 状态驱动挂载器(fx-mount.js, S6 后半)漏挂/重复挂"),
    ):
        assert flux_shell.count(needle
                               ) == 1, (f"flux shell 的 {needle} 挂载失守(须恰一次, 实测 {flux_shell.count(needle)}) —— {why}")
    # 2. 级联序: fx.css 在本皮肤 views.css 与 shared 收尾件(dt_table.css)之后;
    #    fx-presets.css 在 fx.css 之后(showcase 同序: 基线在前, 配方覆盖在后);
    #    fx-mount.css 排 fx 三件之后(S6 后半挂载面 = 最后一级联, 覆盖 flux 既有同选择器规则)
    pos_views = flux_shell.find('href="/flux/css/views.css"')
    pos_dt = flux_shell.find('href="/shared/dt_table.css"')
    pos_fx = flux_shell.find('href="/shared/fx/fx.css"')
    pos_pre = flux_shell.find('href="/shared/fx/fx-presets.css"')
    pos_mount = flux_shell.find('href="/flux/css/fx-mount.css"')
    assert pos_views > 0 and pos_dt > 0, "flux shell 缺 views.css/dt_table.css link(fx 级联序判据失去锚点)"
    assert pos_fx > pos_views and pos_fx > pos_dt, (
        "flux shell 里 /shared/fx/fx.css 排在本皮肤 views.css / shared 收尾件之前 —— "
        "link 序即级联序, 共库层惯例 = 排最后"
    )
    assert pos_pre > pos_fx, "fx-presets.css 须排在 fx.css 之后(基线在前, 配方覆盖在后)"
    assert pos_mount > pos_pre, "fx-mount.css 须排在 fx-presets.css 之后(S6 后半挂载面是最后一级联)"
    # 3. 隔离反向: 三旧皮肤对 /shared/fx/ 与 flux fx 挂载面零引用(D14 拍板)
    for ui in ("atlas", "prism", "console"):
        shell = open(os.path.join(STATIC_ROOT, ui, "index.html"), encoding="utf-8").read()
        assert "/shared/fx/" not in shell, (
            f"{ui} shell 出现 /shared/fx/ 引用 —— fx 动效库只服务 flux(D14 存量隔离拍板), "
            "三旧皮肤挂上即视觉漂移"
        )
        assert "fx-mount" not in shell, (
            f"{ui} shell 出现 fx-mount 引用 —— fx 挂载面(fx-mount.css/fx-mount.js)是 flux 专属"
            "(S6 后半), 三旧皮肤挂上即动效泄漏"
        )
    # 4. preset 落档: flux <html> 带 data-fx-preset="glass"(S4 主 preset 拍板)
    assert 'data-fx-preset="glass"' in flux_shell, (
        'flux <html> 缺 data-fx-preset="glass" —— S4 人工挑选主 preset 为 glass, '
        "缺档 = flux 落回 fx.css :root 基线值而非 glass 配方"
    )
    # 5. 注册表 <-> CSS 同步(fx.js 单点声明, 两侧同轮补)
    fx_js = open(os.path.join(STATIC_ROOT, "shared", "fx", "fx.js"), encoding="utf-8").read()
    fx_css = open(os.path.join(STATIC_ROOT, "shared", "fx", "fx.css"), encoding="utf-8").read()
    fx_pre = open(os.path.join(STATIC_ROOT, "shared", "fx", "fx-presets.css"), encoding="utf-8").read()
    m = re.search(r"effects:\s*\[(.*?)\]", fx_js, re.S)
    assert m, "fx.js REGISTRY.effects 解析失败(守阵口径跟实现走, 同步本守阵)"
    effects = re.findall(r'"([^"]+)"', m.group(1))
    assert len(effects) >= 26, f"fx.js REGISTRY.effects 仅 {len(effects)} 名(基线 9 + S6 提升 17, 缩水即红)"
    for name in effects:
        assert f'[data-fx~="{name}"]' in fx_css, (
            f'fx.js REGISTRY.effects 的 "{name}" 在 fx.css 无 [data-fx~="{name}"] 规则 —— '
            "audit 会放行但样式静默不生效, CSS 与注册表必须同轮补"
        )
    mp = re.search(r"presets:\s*\[(.*?)\]", fx_js, re.S)
    assert mp, "fx.js REGISTRY.presets 解析失败"
    for name in re.findall(r'"([^"]+)"', mp.group(1)):
        assert f'[data-fx-preset="{name}"]' in fx_pre, (
            f'fx.js REGISTRY.presets 的 "{name}" 在 fx-presets.css 无配方块(缺档 = 切换落空)'
        )
    # 6. R1 精修回归钉(计划 26-10-31-2316 §06 精修轮 R1, 四 bug 修复面):
    mount_css = open(os.path.join(STATIC_ROOT, "flux", "css", "fx-mount.css"), encoding="utf-8").read()
    mount_js = open(os.path.join(STATIC_ROOT, "flux", "fx-mount.js"), encoding="utf-8").read()
    # 6a. B2(D4-1 让位): fx-mount.css 不得再挂行板 hover 底 —— 原版「gradient 叠 --bg-row」
    #     特异性压过 row_lang flat 行板 hover, 与吸左首格消费的 flat color-mix 纯色分家,
    #     悬停期名称列持久竖带。行板 hover 底单点 = shared/row_lang.css(复活即回归)。
    assert not re.search(r"\.group-row:hover[^{]*\{[^}]*linear-gradient", mount_css), (
        "fx-mount.css 复活了行板 :hover 的 gradient 叠底 —— 行板/首格悬停管线分家回归"
        "(B2, 用户报「名称列 hover 背景与其它列不一致」); hover 底单点在 shared/row_lang.css"
    )
    # 6b. F7e(R5 精修, 用户拍板「全面弃用新逻辑」): push 位移本体退役 —— 打点实证
    #     scrollY=0 时点击上半部分行开门, 行被全幅位移推出视野且滚动不可恢复(负向
    #     scrollBy 在文档顶被钳制)。反向钉: fx-mount.css/js 不得再持有任何 push
    #     载体/让位量规则或 stamp(B4 relative-top 载体随之退役; 复活即回归)。
    assert "data-fx-pushed" not in mount_css and "--fx-push-y" not in mount_css, (
        "fx-mount.css 复活 push 载体规则(F7e 已弃用) -- 内容位移在 scrollY=0 时把聚焦行"
        "推出视野且原版滚动无法恢复, 回归即重蹈 D3-4 三轮报障"
    )
    # 6c. F7c(R3 精修, 用户否掉 F7a 自定义方案): 滚动行为完全交还原版单点
    #     shared/shortcuts.js(console 原版开面板路径同款让位) -- fx-mount.js
    #     不得再挂自己的滚动干预/可视区回拉/push 量裁剪(R1 B3 的
    #     ensureFocusedVisible/scheduleReveal/revealFocusedRow 整体退役, 复活即回归:
    #     与原版单点双写滚动打架)。反向钉: 三个符号在 fx-mount.js 出现即红。
    for gone in ("ensureFocusedVisible", "scheduleReveal", "revealFocusedRow"):
        assert gone not in mount_js, (
            f"fx-mount.js 残留 {gone}(F7c 已退役: 滚动行为单点交还 shortcuts.js 原版逻辑, "
            "flux 不再做自己的滚动干预/push 量裁剪)"
        )
    for gone_code in ('setProperty("--fx-push-y"', 'setAttribute("data-fx-pushed"', 'setAttribute("data-fx", "push")'):
        assert gone_code not in mount_js, (
            f"fx-mount.js 复活 push 位移 stamp({gone_code}, F7e 已弃用) -- 内容位移在 scrollY=0 时把聚焦行"
            "推出视野且原版滚动无法恢复, 回归即重蹈 D3-4 三轮报障"
        )
    #     F7d(F7c 裁决项 b 落地) + F7e 换锚: 落定回执机制保留, 锚点从 push 过渡落定
    #     换到面板入场过渡落定。钉链路四件(缺一 = 回退到时序缺陷):
    #     a) fx-mount.js 发信号: 面板 transform 过渡 transitionend + 兜底定时器
    #        (armSettle/fireSettle), 且发前过 settleArmed 单发守卫(关面板不发);
    #     b) state.js 消费点登记重入回调(dock 第二参)且重入调**原版**可视区单点
    #        _kbScrollRowIntoView -- 几何/滚动全在 shortcuts.js 单点, 共享侧只做
    #        数据 plumbing; 行目标 = drawer.hash(显式打开的入参, 与输入模态无关)。
    for needle, why in (
        ("transitionend", "fx-mount.js 缺面板入场落定信号(transitionend) -- F7d/F7e 落定回执链路断"),
        ("function armSettle", "fx-mount.js 缺落定兜底定时器重臂(armSettle) -- RM/后台标签页/过渡被打断时回执不发"),
        ("function fireSettle", "fx-mount.js 缺落定回执单发(fireSettle)"),
        ("settleArmed", "fx-mount.js 落定回执缺 settleArmed 单发守卫 -- 关面板路径会误发重入"),
    ):
        assert needle in mount_js, f"fx-mount.js 缺 {needle} —— {why}"
    #     R5#179: armSettle 必须在 dock(true) 时真的武装(此前全仓库零调用, 兜底定时器从未生效:
    #     RM 过渡归零不派 transitionend/过渡被打断/后台标签页丢事件场景下回执永不发,
    #     fx-glide 恒驻留 -- 键盘 End/Home/翻页一直平滑)。双路并存, fireSettle 单发守卫兜冲突。
    dock_blk = re.search(r"function dock\(open, onSettled\) \{(.*?)\n  \}", mount_js, re.S)
    assert dock_blk and "armSettle()" in dock_blk.group(1), (
        "fx-mount.js dock(true) 分支缺 armSettle() 武装(R5#179) -- 兜底定时器与 transitionend "
        "双路并存, 不武装则回执丢失场景下 fx-glide 恒驻留(键盘滚动一直平滑)"
    )
    state_js = open(os.path.join(STATIC_ROOT, "shared", "state.js"), encoding="utf-8").read()
    assert re.search(r"AQB_FX_MOUNT\.dock\(v,\s*\(\)",
                     state_js), ("state.js 的 dock 消费点缺落定回执回调(第二参) -- F7d 重入链路断, "
                                 "面板落定后无人把聚焦行算回可见带")
    assert "this._kbScrollRowIntoView(rows, idx)" in state_js, (
        "state.js 落定回执未重入原版可视区单点 _kbScrollRowIntoView -- 几何/滚动必须"
        "全在 shortcuts.js 单点(上界吸顶列头下 8px / 下界面板顶缘上 8px), 共享侧只做 plumbing"
    )
    #     F7e 两段动效落点(用户口径「只加面板上滑出现以及上推过渡动效」):
    #     c) 面板底部上滑出现: flux/css/dialogs.css 入场 translateY(100%)->0,
    #        时长/缓动消费 fx 骨令牌(--fx-dur-panel/--fx-ease-out);
    #     d) 上推过渡: fx-mount.css 面板开着时 window 滚动走平滑
    #        (scroll-behavior: smooth, :has 门作用域, RM 下不生效 = 原版瞬时)。
    dialogs_css = open(os.path.join(STATIC_ROOT, "flux", "css", "dialogs.css"), encoding="utf-8").read()
    assert re.search(
        r"\.drawer-enter-from\s*\{[^}]*translateY\(100%\)", dialogs_css
    ), ("flux dialogs.css 面板入场不是底部上滑(translateY(100%)) -- F7e 动效 1 落点缺失, "
        "回退到 translateY(-16px) 微移即用户口径不兑现")
    assert re.search(
        r"\.drawer-enter-active\s*\{[^}]*var\(--fx-dur-panel\)[^}]*var\(--fx-ease-out\)", dialogs_css, re.S
    ), ("flux dialogs.css 面板入场时长/缓动未消费 fx 骨令牌(--fx-dur-panel/--fx-ease-out) -- "
        "令牌化单点纪律(改时长只动 fx.css)")
    assert re.search(
        r"html\.fx-glide\s*\{\s*scroll-behavior:\s*smooth", mount_css
    ), ("fx-mount.css 缺上推过渡(html.fx-glide 的 scroll-behavior: smooth) -- F7e 动效 2 落点缺失, "
        "原版让位滚动回退成瞬时跳变")
    assert "fx-glide" in mount_js, ("fx-mount.js 缺 fx-glide 窗口挂/摘(动效 2 的作用域开关) -- 平滑滚动作用域失控(罩全程 = "
                                    "键盘滚动手感漂移, 或恒不生效)")


def test_frontend_fx_site_chip_shape_layering():
    """flux 站点 chip 形状分层守阵(计划 26-11-10-0921 W2): 切角在 ::before 绘制层, 本体不持 clip-path

    W1(399bdb2e)把 .site-chip 的 3px 微切角从本体挪到 ::before 绘制层(控件层 clip-path
    会把 box-shadow 外发光整圈裁掉 = 用户报「辉光仅显示一侧或两侧」的根因), 本体 clip-path
    覆盖为 none。两个静默回归形态(缺一 = W1 修复回退而 pytest 无感):
      1. 本体重新持有 clip-path(删掉 none 覆盖或改回 polygon)= 切角裁发光回归 ——
         fx-mount 媒体块内三种 chip 共用的 --fx-glow-stack 再次被裁成两侧;
      2. ::before 的切角 polygon 漂移/丢失 = R3「逐字恢复」拍板被推翻(3px 微切角视觉消失)。
    覆盖链如实口径: components.css:332 的本体 clip-path 仍单点存在(被 fx-mount 链尾
    none 覆盖), 但「被覆盖而非删除」这一面**不设防** —— 700 行体量断言只限单 CSS 净增行,
    删掉该 clip-path 行是减行、恒绿且视觉等价, 钉不住删除; 级联正确性(none 真赢 components.css:332)
    由同批 W2 e2e 主判据(computed clipPath === 'none')兜底。
    S4(f7f4658c, W1-3 预留路径)把 paused/other/search-hit 的 inset 状态边线与 sa-no-conf
    的虚线底边也迁到 ::before 切角绘制层, 本体侧整组覆盖关闭。该迁移面删任一行 pytest/e2e
    全绿(computed 边线属旁证), 另有三个静默回归形态:
      3. ::before 边线载体缺失 = 状态边线消失(paused/other 的 --paused-line、search-hit 的
         --accent-line、sa-no-conf 的 dashed --warn);
      4. 本体关闭漏写 = 本体方角 inset 线与 ::before 切角线双线叠画 / 方角虚线叠加在切角虚线上;
      5. ::before 渐隐过渡段的 box-shadow 段缺失 = 状态类切换时边线跳变不渐隐。
    """

    mount_css = open(os.path.join(STATIC_ROOT, "flux", "css", "fx-mount.css"), encoding="utf-8").read()
    # 注释先剥再逐条规则收集(手法对齐 widget 守阵 _selectors, 避免注释里的示例被当成规则);
    # 收集口径 = 归一选择器(逗号拆分逐个) -> 该选择器名下全部规则体, 按
    # 精确匹配取用, 不把 .site-chip.seeding::before 等误收进本体/绘制层。
    # any() 为存在性断言(只防删行/改值, 不防日后追加第三条同名规则重赢级联),
    # 级联胜负由同批 e2e 主判据(computed clipPath === 'none')仲裁
    css = re.sub(r"/\*.*?\*/", "", mount_css, flags=re.S)
    rules = {}
    for mo in re.finditer(r"(?m)^\s*([^{}@/][^{}]*)\{([^}]*)\}", css):
        for sel in mo.group(1).split(","):
            sel = " ".join(sel.split())
            rules.setdefault(sel, []).append(mo.group(2))
    main_bodies = rules.get("html[data-fx-preset] .site-chip", [])
    before_bodies = rules.get("html[data-fx-preset] .site-chip::before", [])

    def _body_has(sel, needle, why):
        bodies = rules.get("html[data-fx-preset] .site-chip" + sel, [])
        assert bodies, f"fx-mount.css 缺 html[data-fx-preset] .site-chip{sel} 规则 —— {why}"
        assert any(needle in " ".join(b.split())
                   for b in bodies), (f"fx-mount.css 的 .site-chip{sel} 规则体缺 {needle} —— {why}")

    # 1. 本体不持 clip-path: 形状分层规则必须显式 clip-path: none(缺行/改回 polygon 均红)
    assert any(re.search(r"clip-path\s*:\s*none\b", " ".join(b.split())) for b in main_bodies), (
        "fx-mount.css 的 html[data-fx-preset] .site-chip 本体规则缺 clip-path: none —— 本体重新持有"
        "裁剪时 box-shadow 辉光被整圈裁掉(「辉光仅显示一侧或两侧」回归, 计划 26-11-10-0921 W2 判据 1)"
    )
    # 2. 切角在 ::before 绘制层, polygon 逐字(白空格归一比对: 源文件按行宽折行)
    POLYGON = ("polygon(3px 0, 100% 0, 100% calc(100% - 3px), "
               "calc(100% - 3px) 100%, 0 100%, 0 3px)")
    assert before_bodies, (
        "fx-mount.css 缺 html[data-fx-preset] .site-chip::before 规则 —— 切角绘制层整块丢失"
        "(3px 微切角视觉消失, 计划 26-11-10-0921 W2 判据 2)"
    )
    assert any(POLYGON in " ".join(b.split()) for b in before_bodies), (
        "fx-mount.css 的 .site-chip::before 规则体缺切角 polygon(3px 0, ...) —— 3px 微切角视觉"
        "漂移/丢失(R3「逐字恢复」拍板被推翻, 计划 26-11-10-0921 W2 判据 2)"
    )
    # 3. S4 状态边线迁移守阵(f7f4658c): 边线载体在 ::before 切角绘制层, 本体侧整组关闭。
    #    缺任一半 = 静默回归: ::before 载体删行 = 状态边线消失; 本体关闭删行 = 方角 inset 线
    #    与切角线双线叠画 / 方角虚线叠加(本体线不吃 clip-path 切角, 视觉直接穿帮)。
    for sel, needle in (
        (".paused::before", "box-shadow: inset 0 0 0 1px var(--paused-line)"),
        (".other::before", "box-shadow: inset 0 0 0 1px var(--paused-line)"),
        (".search-hit::before", "box-shadow: inset 0 0 0 1px var(--accent-line)"),
    ):
        _body_has(sel, needle, "S4 迁入的 inset 状态边线载体缺失 —— 状态边线消失(迁移回退)")
    _body_has(
        ".sa-no-conf::before", "border-bottom: 1px dashed var(--warn)",
        ("S4 迁入的缺配置虚线底边载体缺失 —— 边线消失(dashed 是 D4 非颜色通道, 迁移回退)")
    )
    for sel in (".paused", ".other", ".search-hit"):
        _body_has(sel, "box-shadow: none", ("S4 本体侧关闭漏写 —— 本体方角 inset 线与 ::before 切角线双线叠画"))
    _body_has(".sa-no-conf", "border-bottom: 0", ("S4 本体侧关闭漏写 —— 方角虚线叠加在 ::before 切角虚线上"))
    # 4. ::before 渐隐过渡段(RM 媒体块内)含 box-shadow 段: S4 后 inset 边线画在绘制层,
    #    状态类切换的渐隐随迁, 缺段 = 边线跳变不渐隐
    assert any(
        "box-shadow var(--dur-fast)" in " ".join(b.split()) for b in before_bodies
    ), ("fx-mount.css 的 .site-chip::before 渐隐过渡段缺 box-shadow var(--dur-fast) —— "
        "状态类切换时 inset 边线跳变不渐隐(S4 渐隐补段回退)")


def test_frontend_fx_tag_cat_chip_glow_layering():
    """flux tag/cat chip 辉光放行 + H&R 竖线迁层守阵(计划 26-11-12-1012 S1 + S2)

    旧计划 26-11-10-0921 只救了 .site-chip 本体裁剪(W1), 三种 chip 共用的 hover 辉光
    配方(--fx-glow-stack)对 tag/cat chip 仍被两层裁掉(用户报「辉光仅显示一侧或两侧」
    的第二根因, 本体无 clip-path 但祖先链有):
      1. 直接父容器 .g-tags/.m-tags/.g-cat/.m-cat 带 overflow: hidden(components.css:340-341),
         裁掉画在盒外的 box-shadow 外发光 —— S1 用 overflow: clip + overflow-clip-margin: 16px
         覆盖放行: clip 不建立滚动容器、保留内容裁剪语义(标签全量展开换行的逐行实测行高与
         吸左首格几何不动, I3), 16px = 12px blur + 3px spread + 1px 硬芯余量(stack 最大层
         0 0 12px 3px), 零新增令牌(I2); .g-sites 本来无裁剪, 不加同款(零收益扩面, D5)。
      2. .tag-chip.hr-pending/.hr-done 的 H&R 状态竖线画在本体 box-shadow
         (components.css:346-349), hover 规则整体写入辉光 stack ⇒ 竖线被替换消失;
         S2 仿旧计划 S4 迁到空闲的 .tag-chip::before(.f-on::after 底线占 ::after 不冲突),
         本体常态竖线以 box-shadow: none 撤下。HR = H&R(PT 做种考核)状态类, 非人力资源。
    静默回归形态(缺一 = 本计划修复回退而 pytest 无感; 纯 computed 值断言对绘制层裁剪无感):
      3. S1 放行段删行/改值(overflow 退回 hidden 或 margin 归零)= 辉光再被祖先裁成一侧/两侧;
      4. ::before 迁层载体缺失(content/inset 绘制盒或两档语义色竖线)= hover 前后竖线消失
         (本体侧已 none, 无人承接);
      5. 本体 box-shadow: none 关闭漏写 = 本体 inset 竖线与 ::before 竖线双线叠画;
      6. .tag-chip 的 position: relative 缺失 = ::before 脱离 chip 盒, 竖线画进最近的
         定位祖先包含块(基线 components.css:342 无 position, 必须显式补);
      7. ::before 渐隐过渡段(RM 媒体块内)缺 box-shadow 段 = hr-pending<->hr-done
         状态类切换时竖线色跳变不渐隐(评审 minor 修, 仿 site-chip S4 渐隐补段先例)。
    any() 存在性断言只防删行/改值, 不防日后追加同名规则重赢级联; hover 时本体仍单独
    消费同一条 --fx-glow-stack(与 ::before 竖线互不同属性), 级联胜负由 S3 像素采样
    e2e 仲裁。
    """

    mount_css = open(os.path.join(STATIC_ROOT, "flux", "css", "fx-mount.css"), encoding="utf-8").read()
    # 手法对齐 test_frontend_fx_site_chip_shape_layering: 注释先剥再逐条规则收集,
    # 归一选择器(逗号拆分逐个) -> 该选择器名下全部规则体, 精确匹配取用
    # (不把 .tag-chip.hr-* 误收进 .tag-chip 本体)
    css = re.sub(r"/\*.*?\*/", "", mount_css, flags=re.S)
    rules = {}
    for mo in re.finditer(r"(?m)^\s*([^{}@/][^{}]*)\{([^}]*)\}", css):
        for sel in mo.group(1).split(","):
            sel = " ".join(sel.split())
            rules.setdefault(sel, []).append(mo.group(2))

    def _body_has(sel, needle, why):
        bodies = rules.get(sel, [])
        assert bodies, f"fx-mount.css 缺 {sel} 规则 —— {why}"
        assert any(needle in " ".join(b.split()) for b in bodies), f"fx-mount.css 的 {sel} 规则体缺 {needle} —— {why}"

    # 1. S1 祖先裁剪放行: 四个直接父容器逐字 overflow: clip + overflow-clip-margin: 16px
    for sel in (
        "html[data-fx-preset] .g-tags", "html[data-fx-preset] .m-tags", "html[data-fx-preset] .g-cat",
        "html[data-fx-preset] .m-cat"
    ):
        _body_has(
            sel, "overflow: clip",
            ("S1 祖先裁剪放行缺失/退回 hidden —— hover 辉光被 "
             "overflow: hidden 祖先裁成一侧/两侧(计划 26-11-12-1012 判据)")
        )
        _body_has(
            sel, "overflow-clip-margin: 16px",
            ("S1 裁剪边界外扩缺失/归零 —— clip 虽保留, "
             "辉光 16px 余量仍被裁(12px blur + 3px spread + 1px 硬芯)")
        )
    # 2. S2 迁层前置: .tag-chip 补 position: relative(::before absolute 的定位包含块)
    _body_has(
        "html[data-fx-preset] .tag-chip", "position: relative",
        ("S2 迁层前置缺失 —— 基线 components.css:342 无 position, ::before 脱离 chip 盒"
         "画进最近的定位祖先包含块")
    )
    # 3. S2 迁层载体: ::before 三条(共用 content/inset 绘制盒 + pending/done 两档语义色竖线)
    for sel, needle in (
        (
            "html[data-fx-preset] .tag-chip.hr-pending::before",
            'content: ""; position: absolute; inset: 0; pointer-events: none;'
        ),
        (
            "html[data-fx-preset] .tag-chip.hr-done::before",
            'content: ""; position: absolute; inset: 0; pointer-events: none;'
        ),
        ("html[data-fx-preset] .tag-chip.hr-pending::before", "box-shadow: inset 2px 0 0 var(--hr-pending)"),
        ("html[data-fx-preset] .tag-chip.hr-done::before", "box-shadow: inset 2px 0 0 var(--hr-done)"),
    ):
        _body_has(sel, needle, ("S2 H&R 状态竖线迁层载体缺失 —— hover 前后竖线消失"
                                "(本体侧已 none 无人承接, 迁移回退)"))
    # 4. S2 本体侧关闭: 常态竖线撤下, 缘由同 site-chip S4(漏写 = 本体线与 ::before 线双线叠画)
    for sel in ("html[data-fx-preset] .tag-chip.hr-pending", "html[data-fx-preset] .tag-chip.hr-done"):
        _body_has(sel, "box-shadow: none", ("S2 本体侧关闭漏写 —— 本体 inset 竖线与 ::before 竖线双线叠画"))
    # 5. S2 渐隐过渡段(RM 媒体块内, 评审 minor 修): ::before 的 box-shadow 段随迁,
    #    hr-* 状态类切换线色渐变不跳变; 令牌逐字沿用 site-chip::before 渐隐段
    #    (--dur-fast/--ease), 缺段 = 竖线色跳变(同 site-chip S4 渐隐补段先例)
    for sel in ("html[data-fx-preset] .tag-chip.hr-pending::before", "html[data-fx-preset] .tag-chip.hr-done::before"):
        _body_has(
            sel, "transition: box-shadow var(--dur-fast) var(--ease)",
            ("S2 ::before 渐隐过渡段缺 box-shadow 段 —— hr-pending<->hr-done 状态类"
             "切换竖线色跳变不渐隐(仿 site-chip S4 渐隐补段先例)")
        )


def test_frontend_console_square_radius():
    """console 方角口径守阵(R1 精修 B1, 用户报「console 详情模板/文字元素出现圆角」)

    console 设计语言是方角(--radius 三档全 0px), flux 自 R3 精修(F7c)起形状同归方角
    (S5 圆角三档 16/10/6 已退役, 令牌取值回 0px; flux 侧不受本守阵白名单管辖, 形状
    回退由 flux 自有 CSS 与令牌取值承担)。
    回归向量 = flux 意图的圆角经**共享面**漏进 console: console 实际加载 shared/row_lang.css、
    dt_table.css、hscroll.css、console_hub.css 四件, 任何一件被写进大半径圆角, console 的
    详情模板(抽屉变体表格走 dt_table)与文字元素即集体变圆。真机复现轮(2026-11-01)在
    develop@d127d3b0 上全状态扫描(groups/torrents/抽屉/右键菜单/shows/设置面)未复现
    (仅存量 999px 胶囊), 说明当前树是干净的 —— 本守阵把它钉住, 防再犯。

    钉两层(按**声明值**白名单, 新值入列必须显式改本测试 = 有意识决策):
    1. console/style.css 方角令牌单点: --radius-lg/--radius/--radius-sm 全为 0px
       (var 引用值是否方角由本条决定);
    2. console 自有 CSS(style.css + css/*.css)与上述四件共享面的 border-radius 声明值
       全部在方角白名单内。
    """
    files = [
        os.path.join(STATIC_ROOT, "console", "style.css"),
        *(os.path.join(STATIC_ROOT, "console", "css", n) for n in ("components.css", "views.css", "dialogs.css")),
        *(
            os.path.join(STATIC_ROOT, "shared", n)
            for n in ("row_lang.css", "dt_table.css", "hscroll.css", "console_hub.css")
        ),
    ]
    tokens = open(files[0], encoding="utf-8").read()
    for tok in ("--radius-lg", "--radius", "--radius-sm"):
        mo = re.search(rf"{tok}\s*:\s*([^;]+);", tokens)
        assert mo, f"console/style.css 缺方角令牌 {tok}(console 方角口径的声明单点)"
        val = mo.group(1).strip()
        assert val == "0px", (
            f"console/style.css 的 {tok} = {val} —— console 设计语言是方角(三档全 0px), "
            "非 0 即 flux 圆角口径泄漏(B1)"
        )
    for path in files:
        text = re.sub(r"/\*.*?\*/", "", open(path, encoding="utf-8").read(), flags=re.S)
        rel = os.path.relpath(path, STATIC_ROOT).replace(os.sep, "/")
        for mo in _RADIUS_RE.finditer(text):
            val = " ".join(mo.group(1).split())
            assert val in _CONSOLE_RADIUS_ALLOW, (
                f"{rel} 出现白名单外的 border-radius: {val} —— console 方角口径被写进共享面/"
                "皮肤面(B1 回归向量: flux 意图的圆角 16/10/6 漏进 console 加载面); "
                "若确属 console 设计变更, 显式更新本守阵白名单"
            )
