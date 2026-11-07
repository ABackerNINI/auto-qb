"""test_bt_backup_editor 测试计划: BT_backup 路径表编辑器静态接线守阵(计划 26-11-07-0708 S2)

## 背景
设置页「整组迁移」块内嵌 bt_backup 自定义映射编辑器(键 = qB 连接身份 host:port, 值 = 该实例
BT_backup 目录路径): bt_backup 在 schema 打 hidden(通用编辑树表达不了用户自定键的动态映射),
由本组件接管渲染。分层与写回口径同 transfer_targets.js 范式 —— 行为层 shared/bt_backup_editor.js
(bb* 系列, 整对象替换 / 空映射删键), 模板 shared/tpl/bt-backup-editor.html(x-template 组件),
挂载在 settings-detail.html 通用分区分支的 config.relocate 块内。
组件增删改的写路径行为断言由 S5 e2e spec 承载(计划拍板), 本文件只守静态接线 —— 漏接的全部
形态都是"pytest 之外才炸"(模板 404 整页占位 / 组件当未知元素渲染整块消失 / 皮肤间清单漂移)。

## 测试计划(每个测试函数一条)
- test_bb_editor_wiring: 静态接线守阵 —— app.js mixin(window.AQB_BT_BACKUP_EDITOR) +
  app.component("aq-bt-backup-editor"); 四皮肤清单成对登记(分片 + 行为 JS, 且 JS 排在
  app.js 之前、紧跟 transfer_targets.js 同区同序); settings-detail.html 的 config.relocate
  块内挂载(v-if 按 b.key 定位); 模板: x-template id / bb* 全走 $root 回调 / 空表 =
  「功能未启用」文案 / 原生 title 悬浮提示 / cfg.saveError 聚合报错展示位; JS: 整对象替换 +
  空映射删键(cfgDelPath)双口径在档、无 localStorage 持久化; shared/console_hub_panels.css
  的 .bt-bk-* 规则与模板用量成对。
"""
import os
import re

from webui_helpers import STATIC_ROOT, _UI_ALL, _ui_manifest

_BB_JS = os.path.join(STATIC_ROOT, "shared", "bt_backup_editor.js")
_BB_TPL = os.path.join(STATIC_ROOT, "shared", "tpl", "bt-backup-editor.html")
_DETAIL_TPL = os.path.join(STATIC_ROOT, "shared", "tpl", "settings-detail.html")
_APP_JS = os.path.join(STATIC_ROOT, "shared", "app.js")
_PANELS_CSS = os.path.join(STATIC_ROOT, "shared", "console_hub_panels.css")


def test_bb_editor_wiring():
    """静态接线守阵: mixin/component/四皮肤清单/挂载面/模板回调/空表文案/CSS 成对

    任一处漏接 = 整块静默消失或行为回退(全部是"pytest 之外才炸"的形态, 故逐一静态钉住)。
    """
    app_js = open(_APP_JS, encoding="utf-8").read()
    assert "app.mixin(window.AQB_BT_BACKUP_EDITOR)" in app_js, "app.js 缺 bt_backup 编辑器 mixin 注入(整块方法消失)"
    assert 'app.component("aq-bt-backup-editor", window.AQ_BT_BACKUP_EDITOR_COMPONENT)' in app_js, (
        "app.js 缺 aq-bt-backup-editor 组件注册(挂载点渲染不出)"
    )

    # 四皮肤清单成对登记 + 装载序: transfer_targets.js < bt_backup_editor.js < app.js(同区同序)
    for ui in _UI_ALL:
        mf = _ui_manifest(ui)
        scripts = mf["scripts"]
        assert "/shared/bt_backup_editor.js" in scripts, f"{ui} 清单缺 bt_backup_editor.js(行为层加载不上)"
        i_tt = scripts.index("/shared/transfer_targets.js")
        i_bb = scripts.index("/shared/bt_backup_editor.js")
        i_app = scripts.index("/shared/app.js")
        assert i_tt < i_bb < i_app, f"{ui} 装载序错误: transfer_targets={i_tt} / bt_backup={i_bb} / app={i_app}"
        parts = [p["src"] for p in mf["parts"]]
        assert "/shared/tpl/bt-backup-editor.html" in parts, f"{ui} 清单缺 bt-backup-editor.html 分片(模板 404 整页占位)"

    # 挂载面: settings-detail.html 通用分区分支的 config.relocate 块内(D3: 嵌入组内, 非独立卡)
    detail = open(_DETAIL_TPL, encoding="utf-8").read()
    assert '<aq-bt-backup-editor v-if="b.key === \'config.relocate\'"></aq-bt-backup-editor>' in detail, (
        "settings-detail.html 缺 <aq-bt-backup-editor> 挂载(或 v-if 锚变了) —— 编辑器不渲染"
    )

    # 模板: x-template id + 回调全走 $root(bb* 方法域在 bt_backup_editor.js, 组件内零方法) +
    # 空表 = 「功能未启用」显式文案 + 原生 title 悬浮提示 + saveError 聚合报错展示位
    tpl = open(_BB_TPL, encoding="utf-8").read()
    assert 'type="text/x-template" id="tpl-aq-bt-backup-editor"' in tpl, "x-template id 变了(组件找不到模板)"
    for cb in ("$root.bbRows", "$root.bbSetKey", "$root.bbSetValue", "$root.bbAdd", "$root.bbRemove"):
        assert cb in tpl, f"模板缺 {cb} 回调(编辑面断线)"
    assert "未启用" in tpl, "模板缺空表 = 「fastresume 收尾未启用」状态文案(空表语义必须显式给出)"
    assert tpl.count('title="') >= 2, "键/值输入框缺原生 title 悬浮提示(前端规则: 悬浮提示写原生 title)"
    assert "$root.cfg.saveError" in tpl and "bt-bk-saveerr" in tpl, "编辑器缺聚合报错展示位(后端 400 报错无处展开)"

    # JS: 写回双口径在档(整对象替换 cfgSetPath / 空映射删键 cfgDelPath); 不持久化视图态
    js = open(_BB_JS, encoding="utf-8").read()
    assert 'this.cfgSetPath(["config", "bt_backup"], map)' in js, "JS 缺整对象替换写回单点(深层写不给渲染留缝隙)"
    assert 'this.cfgDelPath(["config", "bt_backup"])' in js, "JS 缺空映射删键(空对象与键缺失不同构, 脏标记会卡住)"
    for p in (_BB_JS, _BB_TPL):
        assert "localStorage" not in open(p, encoding="utf-8").read(), f"{os.path.basename(p)} 不得持久化视图态"

    # CSS 成对: 模板用到的 .bt-bk-* 类必须在共享层有规则(三皮肤共担, 无单皮肤遗漏面)
    css = open(_PANELS_CSS, encoding="utf-8").read()
    used = set()
    for c in re.findall(r'class="([^"]*)"', tpl):
        for token in c.split():
            if token.startswith("bt-bk"):
                used.add(token)
    assert used, "模板未检出 .bt-bk-* 类(守阵提取失效)"
    for cls in sorted(used):
        assert f".{cls}" in css, f"shared/console_hub_panels.css 缺 .{cls} 规则(整段无样式)"
