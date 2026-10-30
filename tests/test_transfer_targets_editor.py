"""test_transfer_targets_editor 测试计划: 种子转移目标编辑器守阵(计划 26-10-31-0306 W1/T5)

## 背景
「WebUI」设置卡新增「种子转移」目标编辑器: 目标列表(增删改/测试连接) + 编辑器(名称/类型/
地址/凭据/启用/字段集/转移后状态/跳检/路径映射), 编辑直接落 cfg.tree.config.web.transfer
(整对象替换, 脏标记/保存/放弃走全局 actbar), 行为层在 shared/transfer_targets.js,
模板在 shared/tpl/transfer-targets.html(x-template 组件, traffic-card.html 同范式)。
本文件守阵三层: ①字段集单点与后端契约逐位对账 ②node 真跑**写路径**喂后端 validate_config
(两端对"合法目标"的认定必须一致) ③静态接线(manifest 装载序 / mixin+component / 挂载面 /
密码遮显三件套 / saveError 展示 / CSS 成对)。

## 测试计划(每个测试函数一条)
- test_tt_field_keys_match_backend: 前端字段集单点 ↔ 后端契约 —— window.AQB_TRANSFER_FIELDS
  的键与序 == models.TRANSFER_FIELD_KEYS 逐位; node 真跑 ttAdd 落树的新建模板 fields 与
  default_transfer_fields 逐键相等(两处各抄一份默认布尔表 = 漂移必红)
- test_tt_write_shape_passes_config_contract: node 真跑编辑器**写路径**(ttAdd/ttSet/ttSetEnabled/
  ttSetField/ttSetSkip/ttMapAdd/ttMapSet/ttMapMove/ttMapDel/ttRemove + ttSecret + ttTest),
  产出的 config.web.transfer 必须过 validate_config 零错误; 空表删键(不写空列表);
  ttRemove 走 confirmDialog 确认; 密码框非焦点 input 不写树(自动填充防线); ttTest:
  脏树/未保存拒发 + 已保存走 POST /api/transfer/test -> waitCmd, ok/error 两态都回显
- test_tt_editor_wiring: 静态接线守阵 —— app.js mixin(window.AQB_TRANSFER_TARGETS) +
  app.component("aq-transfer-targets"); 三份 manifest 成对登记且装载序
  ctx_menu_custom.js < transfer_targets.js < app.js(与分片 transfer-targets.html);
  settings-detail.html 的 hub.view === 'webui' 分支挂载 <aq-transfer-targets>; 模板:
  密码框 autocomplete="new-password" 且恒显空串(无 :value="t.password" 回显已存密码) +
  保存路径锁死置灰(disabled) + after_state 单选 + 路径映射 ↑↓/增删 + 测试连接按钮 +
  cfg.saveError 聚合报错展示(pre-wrap); state.js trTgt 视图态(不持久化, 无 localStorage);
  shared/console_hub.css 的 .tr-tgt-* 规则成对
- test_tt_password_mask_sentinel_compat: 掩码哨兵兼容守阵(D4 掩码落地的前端配合) —— GET 后
  树里 targets[].password 是后端掩码哨兵(writer.MASK_SENTINEL 单点导入), 编辑器只凭「非空」
  判已设置(占位符提示「留空 = 不修改」, 空值 = 未设置); 前端 JS 与模板不得硬编码哨兵字面量
  (掩码语义单点在后端, 第二份字面量 = 双哨兵漂移)
"""
import json
import os
import re
import shutil
import subprocess

from webui_helpers import STATIC_ROOT, _UI_ALL, _ui_manifest

_TT_JS = os.path.join(STATIC_ROOT, "shared", "transfer_targets.js")
_TT_TPL = os.path.join(STATIC_ROOT, "shared", "tpl", "transfer-targets.html")
_DETAIL_TPL = os.path.join(STATIC_ROOT, "shared", "tpl", "settings-detail.html")
_STATE_JS = os.path.join(STATIC_ROOT, "shared", "state.js")
_SHARED_CSS = os.path.join(STATIC_ROOT, "shared", "console_hub.css")

# node 探针: 在真 vm 桩上跑目标编辑器的**写路径**(transfer_targets.js 的 methods), 输出
# 实际写回的 config.web.transfer 形状与视图态 —— 交 python 侧过 validate_config(两端对
# "合法目标"的认定必须一致)。方法之间走 this.xxx 互调, 整面方法都挂到桩上(同 ctx 探针)。
_NODE_TT_WRITE_PROBE = r"""
const fs = require("fs");
global.window = {};
eval(fs.readFileSync(process.argv[1], "utf8"));   // transfer_targets.js: 行为层 + 字段集单点
const M = window.AQB_TRANSFER_TARGETS;
const asyncOk = { v: true };                      // confirmDialog 桩: 可翻转(验删除确认)
const vm = {
  cfg: { tree: { config: { web: {} } }, saving: false, saveError: "" },
  trTgt: { edit: -1, test: null, testing: "" },
  cfgDirty: false,
  apiCalls: [],
  cfgConfig() { return this.cfg.tree.config || {}; },
  cfgTruthy(v) {
    if (typeof v === "boolean") return v;
    return ["true", "1", "yes", "on"].includes(String(v).trim().toLowerCase());
  },
  confirmDialog: async () => asyncOk.v,
  toast() {},
  api: async (path, options) => { vm.apiCalls.push([path, options]); return { cmd_id: "c1" }; },
  waitCmd: async (id) => vm.cmdResult,
};
for (const k of Object.keys(M.methods)) vm[k] = M.methods[k];
/* computed 在真 Vue 实例上是取值属性(方法里 this.ttList 拿数组), 桩里用 getter 同形 */
Object.defineProperty(vm, "ttList", { get() { return M.computed.ttList.call(vm); } });

const out = {};

// ---- ① 新建模板默认
vm.ttAdd();
out.template = vm.cfg.tree.config.web.transfer.targets[0];
out.editAfterAdd = vm.trTgt.edit;

// ---- ② 逐字段编辑写回
vm.ttSet(0, "name", "副种机");
vm.ttSet(0, "type", "qb");
vm.ttSet(0, "base_url", "http://127.0.0.1:8081");
vm.ttSet(0, "username", "admin");
vm.ttSetEnabled(0, true);
vm.ttSetSkip(0, false);
vm.ttSet(0, "after_state", "paused");
vm.ttSetField(0, "super_seeding", true);
out.patched = vm.cfg.tree.config.web.transfer.targets[0];

// ---- ③ 路径映射: 加两行 -> 改值 -> 换位 -> 删一行
vm.ttMapAdd(0);
vm.ttMapAdd(0);
vm.ttMapSet(0, 0, "from", "/downloads");
vm.ttMapSet(0, 0, "to", "/data");
vm.ttMapSet(0, 1, "from", "/x");
vm.ttMapSet(0, 1, "to", "/y");
vm.ttMapMove(0, 0, 1);   // 首条与次条换位 -> 表序即优先级
out.mapAfterMove = vm.cfg.tree.config.web.transfer.targets[0].path_map;
vm.ttMapDel(0, 0);       // 删掉首位(换位后的原次条) -> 剩一条
out.mapOne = vm.cfg.tree.config.web.transfer.targets[0].path_map;

// ---- ④ 密码: 非焦点 input 一律不写树; 焦点键入写树
const elFake = {};
global.document = { activeElement: {} };   // 焦点在别处 = 自动填充形态
vm.ttSecret({ target: elFake }, 0);        // activeElement !== el -> 不写
out.secretAfterUnfocused = vm.cfg.tree.config.web.transfer.targets[0].password;
global.document.activeElement = elFake;    // 聚焦(真实键入/粘贴必先聚焦)
elFake.value = "s3cret";
vm.ttSecret({ target: elFake }, 0);        // activeElement === el -> 写树
out.secretAfterTyped = vm.cfg.tree.config.web.transfer.targets[0].password;
delete global.document;

// ---- ⑤ 删除确认: 拒绝 = 不动; 确认 = 移行且编辑器下标随动
asyncOk.v = false;
vm.ttRemove(0).then(() => {
  out.denied = vm.cfg.tree.config.web.transfer.targets.length;
  asyncOk.v = true;
  vm.ttToggleEditor(0);              // 展开第 0 行编辑器
  vm.ttRemove(0).then(() => {
    out.confirmed = vm.cfg.tree.config.web.transfer || null;
    out.editAfterRemove = vm.trTgt.edit;
    // ---- ⑥ 空表删键: 最后一个目标删掉 = transfer 键整段消失(不写空列表)
    vm.ttAdd();
    vm.ttRemove(0).then(() => {
      out.emptyTree = vm.cfg.tree.config.web;
      // ---- ⑦ 测试连接: 脏树拒发 / 干净树走 cmd 管线(ok 与 error 两态)
      vm.ttAdd();
      vm.ttSet(0, "name", "未保存机");
      vm.cfgDirty = true;
      vm.ttTest(0).then(() => {
        out.testDirtyBlocked = vm.apiCalls.length === 0 && vm.trTgt.test === null;
        vm.cfgDirty = false;
        vm.ttSet(0, "name", "已存机");
        vm.cfg.tree = { config: { web: vm.cfg.tree.config.web } };  // 桩里 baseline 恒同步
        vm.cmdResult = { ok: true, truth: { info: "qBittorrent 5.1.0" } };
        vm.ttTest(0).then(() => {
          out.testOk = vm.trTgt.test;
          vm.cmdResult = { ok: false, error: "认证失败: 401" };
          vm.ttTest(0).then(() => {
            out.testErr = vm.trTgt.test;
            out.apiPaths = vm.apiCalls.map((c) => c[0]);
            console.log(JSON.stringify(out));
          });
        });
      });
    });
  });
});
"""

# 纯 node 电池: 字段集单点(TT_FIELDS)的键序与模板默认(不依赖 vm, 直读 window 挂载面)
_NODE_TT_FIELDS_PROBE = r"""
const fs = require("fs");
global.window = {};
eval(fs.readFileSync(process.argv[1], "utf8"));
console.log(JSON.stringify({ fields: window.AQB_TRANSFER_FIELDS }));
"""


def _run_node(node, probe, *args):
    proc = subprocess.run(
        [node, "-e", probe, *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    assert proc.returncode == 0, f"探针跑挂: {proc.stderr.strip()}"
    return json.loads(proc.stdout.strip().splitlines()[-1])


def test_tt_field_keys_match_backend():
    """前端字段集单点 ↔ 后端契约(计划 §03 字段集表 / D3): 键序逐位一致 + 模板默认逐键一致

    AQB_TRANSFER_FIELDS 是前端唯一手写面(键序 = UI 展示序), 对应后端单点
    models.TRANSFER_FIELD_KEYS; 新建模板默认只许从它推导(locked 或非 defOff = 开),
    对应 default_transfer_fields —— 两处各抄一份布尔表 = 新目标默认值漂移, 必红。
    """
    node = shutil.which("node")
    if not node:
        return
    rep = _run_node(node, _NODE_TT_FIELDS_PROBE, _TT_JS)
    fe_keys = [f["key"] for f in rep["fields"]]

    from auto_qb.config.models import TRANSFER_FIELD_KEYS, default_transfer_fields

    assert fe_keys == list(TRANSFER_FIELD_KEYS), (
        f"前端字段集 {fe_keys} != 后端 TRANSFER_FIELD_KEYS {list(TRANSFER_FIELD_KEYS)} —— "
        "键面单点漂移: 校验按后端闭集把关, 前端多键被拒/少键落默认"
    )
    # 模板默认: locked 或非 defOff = 开 —— 与 default_transfer_fields 逐键相等
    expect = {k: ("true" if v else "false") for k, v in default_transfer_fields().items()}
    assert {f["key"]: ("false" if f.get("defOff") else "true") for f in rep["fields"]} == expect
    # save_path 必须标 locked(UI 置灰; 后端显式 false 校验拒绝)
    locked = [f["key"] for f in rep["fields"] if f.get("locked")]
    assert locked == ["save_path"], f"锁死必开的字段应是 save_path, 实测 {locked}"


def test_tt_write_shape_passes_config_contract():
    """契约闭环守阵(W1/T5): 编辑器真写路径 → 后端 validate_config 必须认

    前端与后端对"合法目标"各有一套认定(编辑器只摆控件不校验 / validate 聚合把关),
    两边漂移的形态极隐蔽: 编辑器照常能填、保存照常发出, 只是后端 400 整批拒下。
    故在 node 里用真 vm 桩跑**编辑器的方法**(不是手搓一份 targets), 把写出来的东西
    直接喂给后端校验器, 并钉: 模板默认 / 映射换位语义 / 密码遮显防线 / 删除确认 /
    空表删键 / 测试连接的保存门槛与回显两态。
    """
    node = shutil.which("node")
    if not node:
        return
    rep = _run_node(node, _NODE_TT_WRITE_PROBE, _TT_JS)

    from auto_qb.config.models import default_transfer_fields
    from auto_qb.config.validation import validate_config

    # ---- ① 新建模板默认(与 default_transfer_fields 逐键一致; 启用/跳检/状态按计划拍板)
    tpl = rep["template"]
    assert tpl["enabled"] == "false", "新建目标默认未启用(保守默认, 黄金法则 2)"
    assert tpl["skip_check"] == "true" and tpl["after_state"] == "keep"
    assert "path_map" not in tpl, "path_map 缺省不落键(空 = 原样, 零残留)"
    expect_fields = {k: ("true" if v else "false") for k, v in default_transfer_fields().items()}
    assert tpl["fields"] == expect_fields, f"新建模板 fields != 后端 default_transfer_fields: {tpl['fields']}"
    assert rep["editAfterAdd"] == 0, "新增后应展开该行编辑器"

    # ---- ② 编辑写回的整树过 validate_config 零错误
    tree = {"config": {"web": {"transfer": {"targets": [dict(rep["patched"], path_map=rep["mapOne"])]}}}}
    assert validate_config(tree) == [], f"编辑器真写路径产出过不了后端校验: {validate_config(tree)}"
    t = tree["config"]["web"]["transfer"]["targets"][0]
    assert t["name"] == "副种机" and t["enabled"] == "true" and t["after_state"] == "paused"
    assert t["skip_check"] == "false" and t["fields"]["super_seeding"] == "true"
    # ↑↓ 换位生效(表序即优先级) + 删首位: 换位后原次条在首位, 删掉的是它
    assert rep["mapAfterMove"] == [{
        "from": "/x",
        "to": "/y"
    }, {
        "from": "/downloads",
        "to": "/data"
    }], (f"映射 ↑↓ 换位语义不对: {rep['mapAfterMove']}")
    assert rep["mapOne"] == [{"from": "/downloads", "to": "/data"}], f"映射删除语义不对: {rep['mapOne']}"

    # ---- ③ 密码遮显防线: 非焦点 input 不写树, 焦点键入写树(自动填充坑档同款判据)
    assert rep["secretAfterUnfocused"] == "", "非焦点 input 事件把值写进了树(自动填充会凭空造脏)"
    assert rep["secretAfterTyped"] == "s3cret", "焦点键入未写树"

    # ---- ④ 删除确认 + 编辑器下标随动 + 空表删键
    assert rep["denied"] == 1, "确认框拒绝后目标被删了(删除必须先确认)"
    assert rep["confirmed"] is None, "确认删除后 transfer 段应整段消失(空表删键)"
    assert rep["editAfterRemove"] == -1, "删掉展开中的目标后编辑器应收起"
    assert "transfer" not in rep["emptyTree"], "空 targets 不许写空列表(键缺失 == 未配置, 全树 JSON 对比才同构)"

    # ---- ⑤ 测试连接: 未保存拒发 / 已保存走 POST /api/transfer/test, ok/error 两态回显
    assert rep["testDirtyBlocked"] is True, "脏树(有未保存改动)仍发了测试请求 —— 后端按名字找目标, 未保存找不到"
    assert rep["apiPaths"] == ["/api/transfer/test", "/api/transfer/test"], rep["apiPaths"]
    assert rep["testOk"] == {"name": "已存机", "ok": True, "text": "qBittorrent 5.1.0"}, rep["testOk"]
    assert rep["testErr"] == {"name": "已存机", "ok": False, "text": "认证失败: 401"}, rep["testErr"]


def test_tt_editor_wiring():
    """静态接线守阵: mixin/component/manifest 装载序/挂载面/密码遮显/saveError/CSS 成对

    任一处漏接 = 整块静默消失或行为回退(全部是"pytest 之外才炸"的形态, 故逐一静态钉住)。
    """
    app_js = open(os.path.join(STATIC_ROOT, "shared", "app.js"), encoding="utf-8").read()
    assert 'app.mixin(window.AQB_TRANSFER_TARGETS)' in app_js, "app.js 缺目标编辑器 mixin 注入(整块方法消失)"
    assert 'app.component("aq-transfer-targets", window.AQ_TRANSFER_TARGETS_COMPONENT)' in app_js, (
        "app.js 缺 aq-transfer-targets 组件注册(挂载点渲染不出)"
    )

    # 三份 manifest 成对登记 + 装载序: ctx_menu_custom.js < transfer_targets.js < app.js
    for ui in _UI_ALL:
        mf = _ui_manifest(ui)
        scripts = mf["scripts"]
        assert "/shared/transfer_targets.js" in scripts, f"{ui} 清单缺 transfer_targets.js(行为层加载不上)"
        i_cust = scripts.index("/shared/ctx_menu_custom.js")
        i_tt = scripts.index("/shared/transfer_targets.js")
        i_app = scripts.index("/shared/app.js")
        assert i_cust < i_tt < i_app, f"{ui} 装载序错误: {i_cust}/{i_tt}/{i_app}"
        parts = [p["src"] for p in mf["parts"]]
        assert "/shared/tpl/transfer-targets.html" in parts, f"{ui} 清单缺 transfer-targets.html 分片(模板 404 整页占位)"

    detail = open(_DETAIL_TPL, encoding="utf-8").read()
    m = re.search(r"<template v-else-if=\"hub\.view === 'webui'\">(.*?)</template>\s*(?:<!--|$)", detail, re.S)
    assert m, "settings-detail.html 的 webui 分支切不出来(结构变了? 同步守阵)"
    blk = m.group(1)
    assert "<aq-transfer-targets" in blk, "webui 分支缺 <aq-transfer-targets> 挂载(编辑器不渲染)"

    tpl = open(_TT_TPL, encoding="utf-8").read()
    assert 'type="text/x-template" id="tpl-aq-transfer-targets"' in tpl, "x-template id 变了(组件找不到模板)"
    # 密码遮显三件套(xtpl.html 密码分支同款): autocomplete + 恒空显 + 非焦点不写树
    assert 'autocomplete="new-password"' in tpl, "密码框缺 autocomplete=new-password(自动填充会造脏)"
    assert "$root.ttSecret($event, i)" in tpl, "密码写回未走 ttSecret(非焦点 input 会把填充值写进树)"
    assert ':value="t.password"' not in tpl and ":value=\"$root.ttHasSecret" not in tpl, ("密码框不得绑定树值回显(已存密码明文不得出现在界面)")
    # 保存路径锁死: disabled + 锁死标注
    assert ':disabled="!!f.locked"' in tpl, "字段 checkbox 未按 locked 置灰(保存路径必须锁死必开)"
    # 单选/映射/测试连接
    assert "tr-after-" in tpl and 'value="paused"' in tpl, "转移后状态单选缺失"
    assert "$root.ttMapMove" in tpl and "$root.ttMapAdd" in tpl and "$root.ttMapDel" in tpl, "路径映射增删排序缺失"
    assert "$root.ttTest" in tpl and "/api/transfer/test" in open(_TT_JS, encoding="utf-8").read(), ("测试连接按钮与端点调用不成对")
    # 聚合报错展示: cfg.saveError 由 cfgSave 写入(config_editor.js 单点), 编辑器块内 pre-wrap 展开
    ce = open(os.path.join(STATIC_ROOT, "shared", "config_editor.js"), encoding="utf-8").read()
    assert "this.cfg.saveError = e.message" in ce, "cfgSave 失败未写 saveError(消费方拿不到聚合报错)"
    assert "$root.cfg.saveError" in tpl and "tr-tgt-saveerr" in tpl, "编辑器缺聚合报错展示位"

    # state.js 视图态存在; 编辑器分片与 state.js 不得持久化视图态(不进 localStorage)
    state = open(_STATE_JS, encoding="utf-8").read()
    assert "trTgt:" in state, "state.js 缺 trTgt 视图态(编辑器展开/测试回执无处落)"
    for p in (_TT_JS, _TT_TPL):
        assert "localStorage" not in open(p, encoding="utf-8").read(), f"{os.path.basename(p)} 不得持久化视图态"

    # CSS 成对: 模板用到的 .tr-tgt-* 类必须在共享层有规则(三皮肤共担, 无单皮肤遗漏面)
    css = open(_SHARED_CSS, encoding="utf-8").read()
    used = set(re.findall(r'class="([^"]*)"', tpl))
    need = set()
    for c in used:
        for token in c.split():
            if token.startswith("tr-tgt"):
                need.add(token)
    assert need, "模板未检出 .tr-tgt-* 类(守阵提取失效)"
    for cls in sorted(need):
        assert f".{cls}" in css, f"shared/console_hub.css 缺 .{cls} 规则(整段无样式)"


# node 电池: 掩码哨兵下的密码状态判定(D4 掩码落地的前端配合) —— 不依赖 vm 全家桶,
# 直取 methods 判 ttHasSecret / ttSecretPlaceholder 对哨兵值/空值/真值的口径
_NODE_TT_SECRET_PROBE = r"""
const fs = require("fs");
global.window = {};
eval(fs.readFileSync(process.argv[1], "utf8"));
const vm = Object.assign({}, window.AQB_TRANSFER_TARGETS.methods);
const sentinel = process.argv[2];
console.log(JSON.stringify({
  masked: { has: vm.ttHasSecret({ password: sentinel }), ph: vm.ttSecretPlaceholder({ password: sentinel }) },
  empty: { has: vm.ttHasSecret({ password: "" }), ph: vm.ttSecretPlaceholder({ password: "" }) },
  typed: { has: vm.ttHasSecret({ password: "typed-pw" }), ph: vm.ttSecretPlaceholder({ password: "typed-pw" }) },
}));
"""


def test_tt_password_mask_sentinel_compat():
    """掩码哨兵兼容守阵(D4): GET 后树里 targets[].password 是后端哨兵, 前端只凭「非空」判已设置

    后端 /api/config 掩码后哨兵进树(留空 = 不修改语义靠 unmask_tree 按磁盘旧值还原), 编辑器
    无需知道哨兵字面量: 非空(含哨兵)= 显示「已设置, 留空 = 不修改」, 空 = 未设置。前端 JS 与
    模板不得硬编码哨兵字面量 —— 掩码语义单点在后端 writer.MASK_SENTINEL, 第二份字面量即漂移。
    """
    node = shutil.which("node")
    if not node:
        return
    from auto_qb.config.writer import MASK_SENTINEL

    rep = _run_node(node, _NODE_TT_SECRET_PROBE, _TT_JS, MASK_SENTINEL)
    assert rep["masked"]["has"] is True, "哨兵值应判为已设置(占位符提示留空 = 不修改)"
    assert "留空" in rep["masked"]["ph"], "哨兵值的占位符应提示「留空 = 不修改」"
    assert rep["empty"]["has"] is False and rep["empty"]["ph"] == "未设置", "空密码应判为未设置"
    assert rep["typed"]["has"] is True, "真值照旧判已设置"
    for path in (_TT_JS, _TT_TPL):
        with open(path, encoding="utf-8") as f:
            assert MASK_SENTINEL not in f.read(), f"{os.path.basename(path)} 不得硬编码掩码哨兵字面量"
