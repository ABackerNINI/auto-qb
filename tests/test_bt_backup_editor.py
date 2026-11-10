"""test_bt_backup_editor 测试计划: BT_backup 编辑器静态接线守阵(计划 26-11-07-0708 S2 建, 26-11-11-0259 S4 重写)

## 背景
设置页「整组迁移」块内嵌 BT_backup 单路径编辑器(relocate.bt_backup 标量, S1 收编; 原
config.bt_backup 多实例键值表已退役): schema 打 hidden(S4, 组件接管渲染 —— 不打则通用行与本
编辑器同键双输入框), 由本组件接管渲染。分层同 transfer_targets.js 范式 —— 行为层
shared/bt_backup_editor.js(bb* 系列: 标量写回 ["config","relocate","bt_backup"] + 探测回填),
模板 shared/tpl/bt-backup-editor.html(x-template 组件), 挂载在 settings-detail.html 通用分区
分支的 config.relocate 块内。五态(verdict)判定在后端 probe.verdict 单点, 前端只渲染;
POST /api/relocate/bt_backup_probe 调用点登记在 triggers.js calls 表(test_webui_trigger_registry
钉), 本文件不重复。组件行为的浏览器级断言由 e2e settings-bt-backup.spec.mjs 承载, 本文件只守
静态接线 —— 漏接的全部形态都是"pytest 之外才炸"(模板 404 整页占位 / 组件当未知元素渲染整块
消失 / 皮肤间清单漂移 / 五态证据区漏一支 = 用户拿到无声证据)。

## 测试计划(每个测试函数一条)
- test_bb_editor_wiring: 静态接线守阵 —— app.js mixin(window.AQB_BT_BACKUP_EDITOR) +
  app.component("aq-bt-backup-editor"); 四皮肤清单成对登记(分片 + 行为 JS, 且 JS 排在
  app.js 之前、紧跟 transfer_targets.js 同区同序); settings-detail.html 的 config.relocate
  块内挂载(v-if 按 b.key 定位); 模板: x-template id / 回调全走 $root / placeholder
  「留空 = 未启用, 可点自动探测」+ 原生 title 悬浮提示 / 探测按钮态(禁用 + 「探测中」忙文案) /
  cfg.saveError 聚合报错展示位 / 证据区(候选明细 + 证据行 + offline 未自证标注); JS:
  写回路径 ["config","relocate","bt_backup"] 标量单点、旧 ["config","bt_backup"] 整对象替换/
  删键与 bbRows 行模型零残留(不残留第二套写法)、探测端点接线、hit 回填不覆盖已有草稿、
  hit 回填 hash 自证优先(消歧 hit 不取首个 qualified)、hit 话术按 filled 分流(未回填主行
  不称「已回填」)、五态话术表逐键在档、无 localStorage 持久化; CSS: .bt-bk-* 与模板用量成对。
- test_bb_schema_takeover: schema 接管前提 —— relocate.bt_backup 打 hidden 且仍是 path 字段
  (键在契约里, 键面守卫不判删键; hidden 单点语义 = 组件接管, 与 web.transfer/ctx_menu 同款)。
"""
import os
import re

from auto_qb.config import schema

from webui_helpers import STATIC_ROOT, _UI_ALL, _ui_manifest

_BB_JS = os.path.join(STATIC_ROOT, "shared", "bt_backup_editor.js")
_BB_TPL = os.path.join(STATIC_ROOT, "shared", "tpl", "bt-backup-editor.html")
_DETAIL_TPL = os.path.join(STATIC_ROOT, "shared", "tpl", "settings-detail.html")
_APP_JS = os.path.join(STATIC_ROOT, "shared", "app.js")
_PANELS_CSS = os.path.join(STATIC_ROOT, "shared", "console_hub_panels.css")

#: 计划 §3.2 五态字面量(probe.verdict 单点同词) —— JS 话术表必须逐键在档
_BB_VERDICTS = ["hit", "ambiguous", "miss", "unusable-sqlite", "manual-set"]


def test_bb_editor_wiring():
    """静态接线守阵: mixin/component/四皮肤清单/挂载面/模板回调/五态证据区/CSS 成对

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
    # placeholder「留空 = 未启用」(D3 草稿留空 = 功能未启用的显式口) + 原生 title 悬浮提示 +
    # 探测按钮态(禁用 + 忙文案) + saveError 聚合报错展示位 + 证据区(候选明细/证据行/离线标注)
    tpl = open(_BB_TPL, encoding="utf-8").read()
    assert 'type="text/x-template" id="tpl-aq-bt-backup-editor"' in tpl, "x-template id 变了(组件找不到模板)"
    for cb in (
        "$root.bbValue",
        "$root.bbSet(",
        "$root.bbProbeRun(",
        "$root.bbVerdictText()",
        "$root.bbVerdictCls()",
        "$root.bbNotes()",
        "$root.bbStorageText()",
        "$root.bbOriginText(",
    ):
        assert cb in tpl, f"模板缺 {cb} 回调(编辑/证据面断线)"
    assert "留空 = 未启用, 可点自动探测" in tpl, "模板缺 placeholder「留空 = 未启用, 可点自动探测」(D3 读法2 的入口文案)"
    assert "未启用" in tpl, "模板缺「fastresume 收尾未启用」语义文案(空值语义必须显式给出)"
    assert tpl.count('title="') >= 1, "路径输入框缺原生 title 悬浮提示(前端规则: 悬浮提示写原生 title)"
    assert ':disabled="$root.bbProbe.running"' in tpl and "探测中" in tpl, ("探测按钮缺忙态(禁用 + 文案切换) —— 探测期间可重复触发 = 竞态面")
    assert "$root.cfg.saveError" in tpl and "bt-bk-saveerr" in tpl, "编辑器缺聚合报错展示位(后端 400 报错无处展开)"
    assert "$root.bbProbe.result.candidates" in tpl, "证据区缺候选明细渲染(D5: 歧义/miss 必须列全部候选)"
    assert "$root.bbProbe.result.reason" in tpl, "证据区缺后端 reason 行(hit 自证依据 / miss 扫描数 / sqlite 指向 qB 设置)"
    assert "$root.bbNotes()" in tpl, "证据区缺证据行渲染(notes: 后缀枚举来源/定位失败/离线标注)"
    assert "$root.bbProbe.result.online === false" in tpl and "未自证" in tpl, (
        "证据区缺离线标注(online=false 必须标「未自证」—— hash 自证未参与, 用户不可当已核实)"
    )
    assert "$root.bbProbe.filled" in tpl, "证据区缺「已回填/未覆盖」区分位(hit 回填与保留用户草稿两种 hit 混同 = 提示失真)"

    # JS: 写回单点 = relocate.bt_backup 标量; 旧键值表写法零残留(不残留第二套写法);
    # 探测端点接线 + hit 回填不覆盖已有草稿(保守默认) + 五态话术表逐键在档; 不持久化视图态
    js = open(_BB_JS, encoding="utf-8").read()
    assert 'this.cfgSetPath(["config", "relocate", "bt_backup"], value)' in js, (
        "JS 缺 relocate.bt_backup 标量写回单点(编辑面断线)"
    )
    for legacy in (
        'cfgSetPath(["config", "bt_backup"]', "cfgDelPath", "bbRows", "bbAdd", "bbSetKey", "bbSetValue", "bbRemove"
    ):
        assert legacy not in js, f"JS 残留旧键值表写法「{legacy}」(S1 退役面不得有第二套实现)"
    assert 'this.api("/api/relocate/bt_backup_probe", { method: "POST" })' in js, (
        "JS 缺探测端点接线(无 body POST, Bearer 随 api() 既有惯例)"
    )
    assert 'data.verdict === "hit" && !draftExisted' in js, ("JS 缺 hit 回填 + 草稿已有值不覆盖判据(保守默认: 探测不静默丢用户输入)")
    assert 'cands.find((c) => c.qualified && c.hash_matched) || cands.find((c) => c.qualified)' in js, (
        "JS hit 回填缺 hash 自证优先选择(消歧 hit = 多候选合格恰一命中, 取首个 qualified 会回填 hash 未命中的错误路径)"
    )
    assert 'r.verdict === "hit" && !this.bbProbe.filled' in js and "草稿已有值, 探测结果未覆盖" in js, (
        "JS 缺 hit 话术按 filled 分流(未回填的 hit 主行不得声称「已回填」—— 与实际行为矛盾会诱导用户保存)"
    )
    for v in _BB_VERDICTS:
        assert f'"{v}"' in js, f"JS 五态话术表缺 {v}(证据区该态回退成原始字面量)"
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


def test_bb_schema_takeover():
    """schema 接管前提: relocate.bt_backup 打 hidden 且键仍在契约里(path 字段)

    hidden 单点语义 = 组件接管渲染(web.transfer/ctx_menu 同款): 不打则通用编辑树与本编辑器
    同键双输入框; 摘字段则键面守卫判删键(破坏性变更) —— 两个方向都不许走。
    """
    fields = {f.key: f for f in next(g for g in schema.GROUPS if g.key == "maintenance").fields}
    relocate = fields.get("relocate")
    assert relocate is not None and relocate.kind == "object", "maintenance 段缺 relocate object 字段(结构漂移)"
    sub = {f.key: f for f in relocate.fields}
    bb = sub.get("bt_backup")
    assert bb is not None, "relocate 段缺 bt_backup 字段(键面守卫会判删键, 破坏性变更)"
    assert bb.hidden is True, "relocate.bt_backup 未打 hidden —— 通用行与本编辑器同键双输入框(S4 接管前提)"
    assert bb.kind == "path", "relocate.bt_backup kind 漂移(编辑器按 path 语义呈现)"
