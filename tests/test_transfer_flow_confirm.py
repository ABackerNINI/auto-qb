"""test_transfer_flow_confirm 测试计划: 种子转移确认弹窗(四段式)守阵(计划 26-10-31-0306 W4 后半/T7)

## 背景
右键菜单「转移到」子项点击后进 transfer_flow.js::transferOpen 的四段式确认流
(预检 -> 明细 -> 执行 -> 结算, 参照 delete_flow::_deleteFlow 范本)。预检是**前端轻量**
(后端无独立预检路由, 不新开): 目标存在+启用 / hash 在当前列表态 / 状态门预演(与
orchestrator.gate_verdict 同口径); export 可用性与目标连通性后置到执行段失败分类。
改写路径预览的前端映射 trMapSavePath 必须与 orchestrator.map_save_path 逐位同语义
(§07 风险 1 的肉眼可查防线, 映射配错 = 目标 recheck 得 0%)。本文件守阵三层:
①映射语义/状态门判据用**后端真函数/真值**对账(node 真跑前端实现, python 侧跑后端单点)
②node 真 vm 桩跑 transferOpen 全链(预检排除/弹窗行表/执行载荷/结算三件套/单飞闸)
③静态接线(mixin 注入 / manifest 装载序 / 顶层声明无撞名 / 字段标签不抄第二份)。

## 测试计划(每个测试函数一条)
- test_tf_map_save_path_parity: 前端 trMapSavePath ↔ 后端 orchestrator.map_save_path
  逐位同语义(node 喂树形状 [{from,to}], python 喂 TransferPathMapEntry(src,dst), 八组
  用例两两对表): 空表原样 / 首条命中生效(有序) / 真前缀才命中 / 无命中原样 / 空 from
  规则跳过 / 前缀恰等 / 只替换一次(命中即返回, 不再吃后续规则)
- test_tf_gate_states_match_backend: 状态门预演集(window.AQB_TRANSFER_GATE_STATES)与
  orchestrator 的 _DOWNLOAD_PIPELINE_STATES/_ALLOWED_STATES/_MISSING_FILES_STATE 逐位
  相等 —— 预演「将跳过」与执行段真门判据漂移 = 弹窗承诺与回执不一致
- test_tf_open_flow_vm_probe: node 真 vm 桩跑 transferOpen 全链: 目标不存在/未启用
  toast 拦下(不开弹窗不投递); hash 失效/下载管线态进 skips(不投递); 全被排除 toast
  收口; 确认取消零副作用; 确认执行 POST /api/transfer/run 载荷(target_id/hashes/
  keep_source 提供才透传) + 结算三件套(回执中文三态 -> 行内图标 ok/warn/error, toast
  失败/跳过/全成三态, truth 缺失不谎称成功) + keep_source 不清选中集 / 默认删源成功后
  清选中集 + 单飞闸(执行中重复 transferOpen 直接返回) + 发送失败撤 pending 图标
- test_tf_wiring_static: 静态接线守阵 —— app.js mixin(window.AQB_TRANSFER_FLOW); 三份
  manifest 装载序 transfer_targets.js < transfer_flow.js < app.js; 顶层声明(TR_*/trMap)
  全仓唯一(classic script 顶层撞名 = 整文件 SyntaxError); 字段/类型标签只从
  transfer_targets.js 的 window 挂载面取(transfer_flow.js 不出现第二份标签字面量);
  弹窗复用 _openModal(checks/details) 不新增 tpl 分片; 结算走 setRowIcon/toast/_finishToast
"""
import json
import os
import re
import shutil
import subprocess

from webui_helpers import STATIC_ROOT, _UI_ALL, _ui_manifest

_TF_JS = os.path.join(STATIC_ROOT, "shared", "transfer_flow.js")
_TT_JS = os.path.join(STATIC_ROOT, "shared", "transfer_targets.js")
_APP_JS = os.path.join(STATIC_ROOT, "shared", "app.js")


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


# node 探针: 前端映射函数(trMapSavePath, 经 window 挂载面)吃树形状 [{from,to}] 的八组用例;
# 输出逐条结果交 python 侧与 orchestrator.map_save_path(TransferPathMapEntry) 两两对表。
_NODE_MAP_PROBE = r"""
const fs = require("fs");
global.window = {};
eval(fs.readFileSync(process.argv[1], "utf8"));
const f = window.AQB_TRANSFER_MAP_SAVE_PATH;
const cases = [
  { sp: "/downloads/a/b", rules: [] },
  { sp: "/a/b/c", rules: [{ from: "/a", to: "/x" }, { from: "/a/b", to: "/y" }] },
  { sp: "/a/b/c", rules: [{ from: "/a/b", to: "/y" }, { from: "/a", to: "/x" }] },
  { sp: "/abc/d", rules: [{ from: "/abx", to: "/z" }] },
  { sp: "/nope/d", rules: [{ from: "/a", to: "/x" }] },
  { sp: "/a/d", rules: [{ from: "", to: "/x" }, { from: "/a", to: "/y" }] },
  { sp: "/a", rules: [{ from: "/a", to: "/x" }] },
  { sp: "/a/b", rules: [{ from: "/a", to: "/x" }, { from: "/a/b", to: "/y" }] },
];
const out = cases.map((c) => f(c.sp, c.rules));
console.log(JSON.stringify(out));
"""

# node 探针: 状态门预演集(直读 window 挂载面)
_NODE_GATE_PROBE = r"""
const fs = require("fs");
global.window = {};
eval(fs.readFileSync(process.argv[1], "utf8"));
console.log(JSON.stringify(window.AQB_TRANSFER_GATE_STATES));
"""


def test_tf_map_save_path_parity():
    """前端改写预览映射 ↔ 后端 orchestrator.map_save_path 逐位同语义(§07 风险 1 防线)

    弹窗预览如果与执行段的真映射语义漂移(有序/首条命中/真前缀), 用户肉眼核对过的路径
    与实际改写结果不一致 —— 预览就成了装饰。两端各跑各的真实现, 八组用例两两对表。
    """
    node = shutil.which("node")
    if not node:
        return
    fe = _run_node(node, _NODE_MAP_PROBE, _TF_JS)

    from auto_qb.config.models import TransferPathMapEntry
    from auto_qb.transfer.orchestrator import map_save_path

    cases = [
        ("/downloads/a/b", []),
        ("/a/b/c", [("/a", "/x"), ("/a/b", "/y")]),
        ("/a/b/c", [("/a/b", "/y"), ("/a", "/x")]),
        ("/abc/d", [("/abx", "/z")]),
        ("/nope/d", [("/a", "/x")]),
        ("/a/d", [("", "/x"), ("/a", "/y")]),
        ("/a", [("/a", "/x")]),
        ("/a/b", [("/a", "/x"), ("/a/b", "/y")]),
    ]
    for (sp, rules), got_fe in zip(cases, fe):
        be = map_save_path(sp, [TransferPathMapEntry(src=a, dst=b) for a, b in rules])
        assert got_fe == be, (f"改写预览与执行段映射语义漂移: save_path={sp!r} rules={rules} "
                              f"前端={got_fe!r} 后端={be!r}")
    # 语义自证(非镜像): 首条命中生效(第二条不吃)、无命中原样、真前缀才命中
    assert fe[1] == "/x/b/c" and fe[2] == "/y/c" and fe[3] == "/abc/d" and fe[4] == "/nope/d"


def test_tf_gate_states_match_backend():
    """状态门预演集 ↔ orchestrator 判据逐位相等(预演承诺 = 执行段真门)"""
    node = shutil.which("node")
    if not node:
        return
    fe = _run_node(node, _NODE_GATE_PROBE, _TF_JS)

    from auto_qb.transfer import orchestrator

    assert sorted(fe["pipeline"]) == sorted(orchestrator._DOWNLOAD_PIPELINE_STATES
                                           ), ("前端下载管线态预演集与后端 _DOWNLOAD_PIPELINE_STATES 漂移")
    assert sorted(fe["allowed"]) == sorted(orchestrator._ALLOWED_STATES), ("前端放行白名单预演集与后端 _ALLOWED_STATES 漂移")
    assert fe["missing"] == orchestrator._MISSING_FILES_STATE, "missingFiles 判据漂移"


# node 探针: 真 vm 桩跑 transferOpen 全链(预检/明细/执行/结算)。桩面只喂 vm 缺的方法,
# 方法体之间的 this 互调与真实例等价(与 test_transfer_targets_editor 探针同范式)。
_NODE_FLOW_PROBE = r"""
const fs = require("fs");
global.window = {};
eval(fs.readFileSync(process.argv[1], "utf8"));  // transfer_targets.js: 字段/类型标签挂载面
eval(fs.readFileSync(process.argv[2], "utf8"));  // transfer_flow.js: 行为层
const M = window.AQB_TRANSFER_FLOW.methods;

function makeVm() {
  const vm = {
    trTargets: [{
      name: "副种机", type: "qb", enabled: "true", skip_check: "true",
      fields: { save_path: "true", category: "true", tags: "false", super_seeding: "false" },
      path_map: [{ from: "/downloads", to: "/data" }],
    }],
    members: new Map([
      ["h-ok", { hash: "h-ok", name: "A", state: "pausedUP", save_path: "/downloads/a" }],
      ["h-dl", { hash: "h-dl", name: "B", state: "downloading", save_path: "/downloads/b" }],
      ["h-up", { hash: "h-up", name: "C", state: "stalledUP", save_path: "/other/c" }],
    ]),
    _transferRunning: false,
    toasts: [], icons: {}, apiCalls: [], reloads: 0, cleared: 0,
    modalCfg: null,
    cmdResult: null,
    confirmRes: null,
    apiShouldThrow: false,
    cfgTruthy(v) {
      if (typeof v === "boolean") return v;
      return ["true", "1", "yes", "on"].includes(String(v).trim().toLowerCase());
    },
    memberByHash: null,  // 下面挂 getter 转发 members
    toast(text, kind) { const id = vm.toasts.length + 1; vm.toasts.push({ id, text, kind }); return id; },
    _finishToast(id, kind, text) {
      const t = vm.toasts.find((x) => x.id === id);
      if (t) { t.kind = kind; t.text = text; t.finished = true; }
    },
    setRowIcon(hash, kind, msg) { vm.icons[hash] = { kind, msg }; },
    api(path, options) {
      if (vm.apiShouldThrow) return Promise.reject(new Error("boom"));
      vm.apiCalls.push([path, options]);
      return Promise.resolve({ cmd_id: "c1" });
    },
    waitCmd() { return Promise.resolve(vm.cmdResult); },
    transferTargetsReload() { vm.reloads += 1; return Promise.resolve(); },
    clearSelection() { vm.cleared += 1; },
    _auditScope() {},
    _openModal(cfg) { vm.modalCfg = cfg; return Promise.resolve(vm.confirmRes); },
  };
  Object.defineProperty(vm, "memberByHash", { get() { return vm.members; } });
  for (const k of Object.keys(M)) vm[k] = M[k].bind(vm);
  return vm;
}

const out = {};

/* 全链异步走 async IIFE(顶层 await 会被 Node 22 模块探测重试成 ESM, require 失效) */
(async () => {

// ---- ① 目标侧拦下: 不存在 / 未启用 -> toast error, 不开弹窗不投递
let vm = makeVm();
vm.trTargets = [];
await vm.transferOpen("副种机", ["h-ok"]);
out.noTarget = { toasts: vm.toasts.length, modal: vm.modalCfg, api: vm.apiCalls.length };
vm = makeVm();
vm.trTargets[0].enabled = "false";
await vm.transferOpen("副种机", ["h-ok"]);
out.disabled = { toasts: vm.toasts.length, modal: vm.modalCfg, api: vm.apiCalls.length };

// ---- ② 预检排除: hash 失效 + 下载管线态进 skips; 弹窗行表含将跳过/字段/路径预览/跳检警示
vm = makeVm();
vm.confirmRes = { checks: { keep_source: false } };
vm.cmdResult = { ok: true, truth: { results: [
  { hash: "h-ok", "状态": "成功", "原因": "" },
], summary: { success: 1, skipped: 0, failed: 0 }, target: "副种机" } };
await vm.transferOpen("副种机", ["h-ok", "h-dl", "h-gone"]);
out.precheck = {
  apiPaths: vm.apiCalls.map((c) => c[0]),
  body: JSON.parse(vm.apiCalls[0][1].body),
  title: vm.modalCfg.title,
  labels: vm.modalCfg.details.map((d) => d.label),
  skipRow: vm.modalCfg.details.find((d) => d.label === "将跳过"),
  fieldsRow: vm.modalCfg.details.find((d) => d.label === "转移字段"),
  pathRows: vm.modalCfg.details.filter((d) => d.label === "改写预览").map((d) => d.value),
  warnRows: vm.modalCfg.details.filter((d) => d.tone === "warn").map((d) => d.label),
  checkDefault: vm.modalCfg.checks[0].checked,
  bodyText: vm.modalCfg.body,
  tone: vm.modalCfg.tone, strip: vm.modalCfg.strip, wide: vm.modalCfg.wide,
};
out.settleOk = {
  icons: vm.icons,
  toast: vm.toasts[0],
  cleared: vm.cleared,
};

// ---- ②b 纯全成(无预检排除): toast ok 档 + 删源口径文案
vm = makeVm();
vm.confirmRes = { checks: { keep_source: false } };
vm.cmdResult = { ok: true, truth: { results: [
  { hash: "h-ok", "状态": "成功", "原因": "" },
], summary: { success: 1, skipped: 0, failed: 0 }, target: "副种机" } };
await vm.transferOpen("副种机", ["h-ok"]);
out.settlePure = { toast: vm.toasts[0] };

// ---- ③ 全被排除: toast 收口, 不开弹窗不投递
vm = makeVm();
await vm.transferOpen("副种机", ["h-dl", "h-gone"]);
out.allExcluded = { toasts: vm.toasts.length, modal: vm.modalCfg, api: vm.apiCalls.length };

// ---- ④ 取消 = 零副作用
vm = makeVm();
vm.confirmRes = null;
await vm.transferOpen("副种机", ["h-ok"]);
out.cancelled = { api: vm.apiCalls.length, icons: Object.keys(vm.icons).length };

// ---- ⑤ keep_source 勾选: 载荷带 keep_source, 结算不清选中集; 部分失败 toast error
vm = makeVm();
vm.confirmRes = { checks: { keep_source: true } };
vm.cmdResult = { ok: true, truth: { results: [
  { hash: "h-ok", "状态": "成功", "原因": "" },
  { hash: "h-up", "状态": "失败", "原因": "源 .torrent 导出失败" },
], summary: { success: 1, skipped: 0, failed: 1 }, target: "副种机" } };
await vm.transferOpen("副种机", ["h-ok", "h-up", "h-dl"]);
out.keepSource = {
  body: JSON.parse(vm.apiCalls[0][1].body),
  icons: vm.icons,
  toast: vm.toasts[0],
  cleared: vm.cleared,
};

// ---- ⑥ 全跳过(部分成功 + 跳过): toast timeout 档
vm = makeVm();
vm.confirmRes = { checks: { keep_source: false } };
vm.cmdResult = { ok: true, truth: { results: [
  { hash: "h-ok", "状态": "成功", "原因": "" },
  { hash: "h-up", "状态": "跳过", "原因": "目标已存在" },
], summary: { success: 1, skipped: 1, failed: 0 }, target: "副种机" } };
await vm.transferOpen("副种机", ["h-ok", "h-up"]);
out.partialSkip = { toast: vm.toasts[0], iconUp: vm.icons["h-up"] };

// ---- ⑦ truth 缺失: ok 回执无 results -> 全批 warn(不谎称成功); 命令失败 -> 全批 error
vm = makeVm();
vm.confirmRes = { checks: { keep_source: false } };
vm.cmdResult = { ok: true, truth: {} };
await vm.transferOpen("副种机", ["h-ok"]);
out.noTruth = { icons: vm.icons, toast: vm.toasts[0] };
vm = makeVm();
vm.confirmRes = { checks: { keep_source: false } };
vm.cmdResult = { ok: false, error: "转移目标未启用: 副种机" };
await vm.transferOpen("副种机", ["h-ok"]);
out.cmdFail = { icons: vm.icons, toast: vm.toasts[0] };

// ---- ⑧ 发送失败: 撤 pending 图标 + toast error
vm = makeVm();
vm.confirmRes = { checks: { keep_source: false } };
vm.apiShouldThrow = true;
await vm.transferOpen("副种机", ["h-ok"]);
out.sendFail = { icons: vm.icons, toast: vm.toasts[0], running: vm._transferRunning };

// ---- ⑨ 单飞闸: 执行中重复 transferOpen 直接返回(不开弹窗不投递)
vm = makeVm();
vm._transferRunning = true;
await vm.transferOpen("副种机", ["h-ok"]);
out.singleFlight = { modal: vm.modalCfg, api: vm.apiCalls.length };

console.log(JSON.stringify(out));

})().catch((e) => { console.error(e && e.stack || e); process.exit(1); });
"""


def test_tf_open_flow_vm_probe():
    """node 真 vm 桩跑 transferOpen 全链: 预检排除/弹窗行表/执行载荷/结算三件套/单飞闸"""
    node = shutil.which("node")
    if not node:
        return
    rep = _run_node(node, _NODE_FLOW_PROBE, _TT_JS, _TF_JS)

    # ---- ① 目标侧拦下
    assert rep["noTarget"] == {"toasts": 1, "modal": None, "api": 0}, rep["noTarget"]
    assert rep["disabled"]["toasts"] == 1 and not rep["disabled"]["modal"] and rep["disabled"]["api"] == 0

    # ---- ② 预检排除 + 明细行表: 只投递放行的 h-ok; 弹窗四类行齐备
    pc = rep["precheck"]
    assert pc["apiPaths"][0] == "/api/transfer/run", pc["apiPaths"]
    # 结算后的列表态刷新走真实现 transferTargetsReload(经 api 拉 /api/config) —— 桩被
    # mixin 真方法覆盖是探针形态使然, 这里就认"结算后确有一次配置拉取"为刷新证据
    assert "/api/config" in pc["apiPaths"], pc["apiPaths"]
    assert pc["body"] == {"target_id": "副种机", "hashes": ["h-ok"]}, (f"预检排除的 hash 不得进投递载荷: {pc['body']}")
    assert "副种机" in pc["title"] and "qBittorrent" in pc["labels"][0] or pc["labels"][0] == "目标"
    assert pc["skipRow"] and "2 个" in pc["skipRow"]["value"], pc["skipRow"]
    assert pc["fieldsRow"] and "分类" in pc["fieldsRow"]["value"] and "标签" not in pc["fieldsRow"]["value"], pc["fieldsRow"
                                                                                                            ]
    assert pc["pathRows"] == ["/downloads/a -> /data/a"], pc["pathRows"]
    assert "跳检警示" in pc["warnRows"] and "将跳过" in pc["warnRows"], pc["warnRows"]
    assert pc["checkDefault"] is False, "「仅本次保留源种子」默认不勾(D1)"
    assert "不动任何数据文件" in pc["bodyText"], "弹窗文案必须体现「转移只移任务不动数据」"
    assert pc["tone"] == "warn" and pc["strip"] is True and pc["wide"] is True

    # ---- ② 结算: 行内图标 + toast(预检排除的 2 个计入跳过数 -> timeout 档) + 清选中集
    so = rep["settleOk"]
    assert so["icons"]["h-ok"]["kind"] == "ok", so["icons"]
    assert so["toast"]["kind"] == "timeout" and "成功 1, 跳过 2" in so["toast"]["text"], so["toast"]
    assert so["cleared"] == 1, so
    # ---- ②b 纯全成: ok 档 + 删源口径文案
    assert rep["settlePure"]["toast"]["kind"] == "ok", rep["settlePure"]["toast"]
    assert "数据文件未动" in rep["settlePure"]["toast"]["text"], rep["settlePure"]["toast"]

    # ---- ③ 全被排除 / ④ 取消零副作用
    assert rep["allExcluded"]["toasts"] == 1 and not rep["allExcluded"]["modal"] and rep["allExcluded"]["api"] == 0
    assert rep["cancelled"]["api"] == 0 and not rep["cancelled"]["icons"]

    # ---- ⑤ keep_source: 载荷透传 + 部分失败 error toast + 不清选中集
    ks = rep["keepSource"]
    assert ks["body"]["keep_source"] is True, ks["body"]
    assert ks["icons"]["h-ok"]["kind"] == "ok" and ks["icons"]["h-up"]["kind"] == "error", ks["icons"]
    assert ks["icons"]["h-up"]["msg"] == "源 .torrent 导出失败", ks["icons"]
    assert ks["toast"]["kind"] == "error" and "失败 1" in ks["toast"]["text"], ks["toast"]
    assert ks["cleared"] == 0, "keep_source 勾选时不得清选中集(源任务保留)"

    # ---- ⑥ 部分跳过: timeout 档 + 跳过图标 warn
    assert rep["partialSkip"]["toast"]["kind"] == "timeout", rep["partialSkip"]["toast"]
    assert rep["partialSkip"]["iconUp"]["kind"] == "warn"

    # ---- ⑦ truth 缺失两兜底都不谎称成功
    assert rep["noTruth"]["icons"]["h-ok"]["kind"] == "warn", rep["noTruth"]["icons"]
    assert rep["noTruth"]["toast"]["kind"] == "timeout"
    assert rep["cmdFail"]["icons"]["h-ok"]["kind"] == "error", rep["cmdFail"]["icons"]
    assert rep["cmdFail"]["toast"]["kind"] == "error" and "未启用" in rep["cmdFail"]["toast"]["text"]

    # ---- ⑧ 发送失败: pending 撤下(图标清空) + 单飞闸复位
    assert rep["sendFail"]["icons"]["h-ok"]["kind"] == "", rep["sendFail"]["icons"]
    assert rep["sendFail"]["toast"]["kind"] == "error"
    assert rep["sendFail"]["running"] is False

    # ---- ⑨ 单飞闸
    assert rep["singleFlight"] == {"modal": None, "api": 0}, rep["singleFlight"]


def test_tf_wiring_static():
    """静态接线守阵: mixin 注入 / manifest 装载序 / 顶层声明无撞名 / 标签不抄第二份"""
    app_js = open(_APP_JS, encoding="utf-8").read()
    assert "app.mixin(window.AQB_TRANSFER_FLOW)" in app_js, "app.js 缺 transfer_flow mixin 注入(整块方法消失)"

    # 三份 manifest 装载序: transfer_targets.js(挂载面供给方) < transfer_flow.js < app.js
    for ui in _UI_ALL:
        scripts = _ui_manifest(ui)["scripts"]
        assert "/shared/transfer_flow.js" in scripts, f"{ui} 清单缺 transfer_flow.js"
        assert scripts.index("/shared/transfer_targets.js") < scripts.index("/shared/transfer_flow.js") \
            < scripts.index("/shared/app.js"), f"{ui} 装载序错误(挂载面必须先于消费方)"

    tf = open(_TF_JS, encoding="utf-8").read()
    # classic script 顶层声明共享全局词法环境: 本文件的顶层 const/function 全仓名单在全仓唯一
    names = re.findall(r"^(?:const|function)\s+([A-Za-z_$][\w$]*)", tf, re.M)
    assert names, "transfer_flow.js 未检出顶层声明(守阵提取失效)"
    for other in os.listdir(os.path.join(STATIC_ROOT, "shared")):
        if not other.endswith(".js") or other == "transfer_flow.js" or other.startswith("vendor"):
            continue
        src = open(os.path.join(STATIC_ROOT, "shared", other), encoding="utf-8").read()
        for n in names:
            assert not re.search(rf"^(?:const|function|let|var)\s+{re.escape(n)}\b", src,
                                 re.M), (f"顶层声明撞名: {n} 同时出现在 transfer_flow.js 与 {other}(整文件 SyntaxError)")
    # 字段/类型标签单点在 transfer_targets.js 的 window 挂载面, 本文件不得抄第二份字面量
    for label in ("分享率限制", "做种时长限制", "超级做种", "Transmission(预留)"):
        assert label not in tf, f"transfer_flow.js 硬编码标签 {label}(单点在 transfer_targets.js, 抄第二份必漂移)"
    assert "window.AQB_TRANSFER_FIELDS" in tf and "window.AQB_TRANSFER_TYPE_LABELS" in tf, (
        "transfer_flow.js 未从挂载面取字段/类型标签"
    )
    # 弹窗复用 _openModal(不新增 tpl 分片); 结算三件套走单点
    for needle in ("_openModal", "setRowIcon", "waitCmd", "_finishToast", "/api/transfer/run"):
        assert needle in tf, f"transfer_flow.js 缺 {needle}(四段式接线断裂)"
