"""test_extension_proxy 测试计划: 浏览器扩展(HR 取数代理)的静态与行为守阵

扩展是**要用户装进浏览器**的交付物: pytest 跑不到它的运行期, 但四类故障是**静态/半静态可查**的,
且都属于"pytest 全绿、用户装上就报错"的形态 —— 2026-09-24 实测两条:
① 裸域名直喂 `chrome.permissions.request` ⇒ `Invalid value for origin pattern pt.btschool.club:
   Missing scheme separator.`(**未捕获的 Promise 拒绝**);
② 端点没起 / 地址写法不对时用户只看到一句 `TypeError: Failed to fetch`(浏览器对网络层失败只给这句)。
故这里钉死: manifest 的作用域、JS 语法、**与后端的协议常量**、以及"输入先归一化再交给浏览器 API"。

## 测试计划(每个测试函数一条)
- test_manifest_is_mv3_and_scoped: MV3 + service worker + 只申请回环与可选站点权限, **绝不出现 <all_urls>**
- test_manifest_covers_loopback_aliases: localhost / [::1] 也在 host_permissions 里(归一化会用到, 否则 fetch 被拦)
- test_js_syntax_passes_node_check: 三个 JS 过 node 语法校验(无 node 时静默跳过, 与前端守阵同口径)
- test_normalizers_behave: **真跑** normalize.js(裸域名补 scheme / localhost 折 127.0.0.1 / https 折 http / 非法报错)
- test_normalizers_are_shared_not_duplicated: 归一化只有一份(normalize.js), 两个消费方都载入它
- test_protocol_matches_backend: 端点路径 / 鉴权头 / 回传字段名与 `hr.channel` + `HrResult` 一致(改一边漏改另一边必红)
- test_options_normalizes_before_browser_api: 站点源与端点先归一化再进权限/存储 API(本次报错的形态)
- test_options_rejections_are_always_handled: 选项页不得留下裸 Promise 拒绝(兜底 unhandledrejection + 逐个 catch)
"""
import json
import pathlib
import re
import shutil
import subprocess

import pytest

from auto_qb.hr.channel import API_RESULT, API_TASKS, TOKEN_HEADER, HrChannelError, HrResult

EXT_DIR = pathlib.Path(__file__).resolve().parents[1] / "extensions" / "hr-fetch-proxy"
MANIFEST = EXT_DIR / "manifest.json"
NORMALIZE_JS = EXT_DIR / "normalize.js"
BACKGROUND_JS = EXT_DIR / "background.js"
OPTIONS_JS = EXT_DIR / "options.js"
OPTIONS_HTML = EXT_DIR / "options.html"
JS_FILES = (NORMALIZE_JS, BACKGROUND_JS, OPTIONS_JS)

#: 归一化的行为钉死表 —— **含用户 2026-09-24 实际踩到的两种写法**。
#: (kind, 输入, 期望输出或 None=应当报错)
NORMALIZE_CASES = [
    ("ep", "127.0.0.1:8788", "http://127.0.0.1:8788"),
    ("ep", "  http://127.0.0.1:8788/  ", "http://127.0.0.1:8788"),
    ("ep", "http://localhost:8788/", "http://127.0.0.1:8788"),
    ("ep", "https://127.0.0.1:8788", "http://127.0.0.1:8788"),
    ("ep", "127.0.0.1", None),
    ("ep", "192.168.1.9:8788", None),
    ("ep", "", None),
    ("og", "pt.btschool.club", "https://pt.btschool.club/*"),
    ("og", "https://pt.btschool.club/", "https://pt.btschool.club/*"),
    ("og", "pt.btschool.club/myhr.php", "https://pt.btschool.club/*"),
    ("og", "http://pt.example.com/a/b", "http://pt.example.com/*"),
    ("og", "notadomain", None),
    ("og", "", None),
]

#: 在 node 里 eval normalize.js 并跑上表(纯函数, 不引用 document/chrome ⇒ 可直接载入)
_NODE_RUN_NORMALIZERS = """
const fs = require('fs');
const src = fs.readFileSync(process.argv[1], 'utf8');
const mod = new Function(src + '\\nreturn {normalizeEndpoint, normalizeOrigin};')();
const out = [];
for (const [kind, input] of JSON.parse(process.argv[2])) {
  try {
    out.push({ kind, input, got: kind === 'ep' ? mod.normalizeEndpoint(input) : mod.normalizeOrigin(input) });
  } catch (e) {
    out.push({ kind, input, err: String(e.message) });
  }
}
process.stdout.write(JSON.stringify(out));
"""


def _node() -> str:
    return shutil.which("node") or ""


def _run_node(args):
    """跑 node 并**显式按 UTF-8 解码** —— node 的输出是 UTF-8, 而 `text=True` 会按本机 locale
    (本机是 GBK)去解 ⇒ 归一化的中文报错会让读取线程直接抛 UnicodeDecodeError(实测)。
    """
    return subprocess.run(args, capture_output=True, encoding="utf-8", errors="replace")


def _read(path: pathlib.Path) -> str:
    return path.read_text(encoding="utf-8")


# ---------- manifest ----------


def test_manifest_is_mv3_and_scoped():
    manifest = json.loads(_read(MANIFEST))
    assert manifest["manifest_version"] == 3
    assert manifest["background"]["service_worker"].endswith(".js")
    host_permissions = manifest["host_permissions"]
    assert "http://127.0.0.1/*" in host_permissions, "端点只监听回环: 没有这条 host_permission, fetch 直接被拦"
    # 站点权限走**可选**(按站点授予), 而不是一次性写进必给的 host_permissions
    optional = manifest["optional_host_permissions"]
    assert optional, "站点源应走 optional_host_permissions"
    for pattern in host_permissions + optional:
        assert pattern != "<all_urls>", "不给全站权限是设计约束"
        assert pattern.startswith(("http://", "https://")), f"匹配模式必须带 scheme: {pattern}"


def test_manifest_covers_loopback_aliases():
    """localhost / [::1] 也要在 host_permissions 里: 用户这么写时归一化会兜住, 但排查/手改时也不能被拦"""
    manifest = json.loads(_read(MANIFEST))
    host_permissions = manifest["host_permissions"]
    assert "http://localhost/*" in host_permissions
    assert "http://[::1]/*" in host_permissions


# ---------- 语法与行为 ----------


def test_js_syntax_passes_node_check():
    node = _node()
    if not node:
        return  # 与前端守阵同口径: 没装 node 就静默跳过(不引入 skip 计数)
    for path in JS_FILES:
        proc = _run_node([node, "--check", str(path)])
        assert proc.returncode == 0, f"{path.name} 语法错误: {proc.stderr.strip()}"


def test_normalizers_behave():
    """真跑 normalize.js —— 这是本次两条报错的直接守阵

    ❗node --check 只看语法, 看不见"LOOPBACK_HOSTS 未定义"这类运行期错(本次重构时就真出现过一次),
    所以这里必须**执行**它。
    """
    node = _node()
    if not node:
        return
    cases = [[kind, text] for kind, text, _want in NORMALIZE_CASES]
    proc = _run_node([node, "-e", _NODE_RUN_NORMALIZERS, str(NORMALIZE_JS), json.dumps(cases)])
    assert proc.returncode == 0, f"node 执行 normalize.js 失败: {proc.stderr.strip()}"
    got = json.loads(proc.stdout)
    assert len(got) == len(NORMALIZE_CASES)
    for case, result in zip(NORMALIZE_CASES, got):
        kind, text, want = case
        label = f"{kind}({text!r})"
        if want is None:
            assert "err" in result, f"{label} 应当报错(给不出可操作提示就是错的), 实际得到 {result.get('got')}"
            assert result["err"], f"{label} 的错误消息不能为空(要能直接给用户看)"
        else:
            assert result.get("got") == want, f"{label} 应归一化为 {want}, 实际 {result}"


def test_normalizers_are_shared_not_duplicated():
    """归一化只能有一份 —— 两份分头演化的症状是「配了不生效」; 选项页与后台都必须载入它"""
    for path in (BACKGROUND_JS, OPTIONS_JS):
        text = _read(path)
        assert not re.search(r"(?m)^function normalizeEndpoint", text), f"{path.name} 又定义了本地副本"
        assert not re.search(r"(?m)^function normalizeOrigin", text), f"{path.name} 又定义了本地副本"
    assert "importScripts('normalize.js')" in _read(BACKGROUND_JS)
    assert _read(OPTIONS_HTML).index("normalize.js") < _read(OPTIONS_HTML).index("options.js"), "载入顺序: 归一化在前"


# ---------- 与后端的协议 ----------


def test_protocol_matches_backend():
    """扩展与后端的线上格式钉在一处: 常量取 `hr.channel`, 字段名取 `HrResult.from_json` 的实测行为"""
    background = _read(BACKGROUND_JS)
    assert API_TASKS in background and API_RESULT in background, "端点路径必须与 hr.channel 一致"
    assert TOKEN_HEADER in background and TOKEN_HEADER in _read(OPTIONS_JS), "鉴权头名必须两边一致"
    # 扩展实际发出去的两条结果形态(见 background.js::runTask)必须能被后端解析
    for payload in (
        {
            "id": "t1",
            "ok": True,
            "status": 200,
            "url": "https://pt.example.com/a",
            "text": "<html/>"
        },
        {
            "id": "t2",
            "ok": True,
            "status": 200,
            "url": "https://pt.example.com/b",
            "body_b64": "AAEC"
        },
        {
            "id": "t3",
            "ok": False,
            "url": "https://pt.example.com/c",
            "error": "HTTP 403"
        },
    ):
        parsed = HrResult.from_json(payload)
        assert parsed.task_id == payload["id"] and parsed.ok == payload["ok"]
    # 清单与批量信封的键名, 以及"任务 id 由后端给、扩展只回显"这条不变量
    assert "data.tasks" in background and "results" in background
    assert "id: task.id" in background, "回传的 id 必须回显后端下发的 task.id(扩展不得自己编号)"
    with pytest.raises(HrChannelError):
        HrResult.from_json({"ok": True, "text": "缺 id"})


# ---------- 选项页的输入处理 ----------


def test_options_normalizes_before_browser_api():
    """本次报错的形态: 原始输入直接进浏览器 API —— 钉住"先归一化、再落盘/授权"

    判据不是"文件里出现过 normalizeXxx", 而是**调用顺序**: 归一化必须在权限/存储 API 之前。
    """
    text = _read(OPTIONS_JS)
    assert "chrome.permissions.request" in text, "用例本身要跟着实现走: 授权入口改名就一起改"
    start = text.index("async function grant()")
    nxt = text.find("\nasync function ", start + 1)
    grant_body = text[start:nxt if nxt > 0 else len(text)]
    assert grant_body.index("parseOrigins()") < grant_body.index("chrome.permissions.request"), \
        "站点源必须先归一化再交给 chrome.permissions.request(裸域名会被它拒且是未捕获拒绝)"
    assert "$('origins').value" not in grant_body, "绝不把原始文本直接喂给权限 API"
    # 非法输入不拖垮整批: 好的照收、坏的逐条报(否则用户改好一条还得再猜其它条)
    assert "bad.push(" in text and "被跳过" in text


def test_options_rejections_are_always_handled():
    """选项页不得留下裸 Promise 拒绝(用户只会看到一行英文红字, 完全无从下手)"""
    text = _read(OPTIONS_JS)
    assert "unhandledrejection" in text, "要有兜底: 漏网的拒绝也得落到状态栏"
    assert text.count(".catch(") >= 5, "四个按钮 + 初始 load 都要 catch"
    assert "try {" in text, "授权/自测这类浏览器 API 调用必须包 try(它们会同步抛)"


# ---------- 页面取数: 隐藏窗口(用户实报「抓数据时开着新标签」) ----------

#: 用**假 chrome API** 真跑 background.js, 记录每一次窗口/标签调用 —— 纯字符串断言看不见调用形态。
_NODE_RUN_PAGE_SNAPSHOT = """
const fs = require('fs');
const vm = require('vm');
const calls = [];
const noop = { addListener() {} };
function record(name, ret) {
  return function () {
    const args = Array.prototype.slice.call(arguments);
    calls.push([name].concat(args));
    return Promise.resolve(typeof ret === 'function' ? ret.apply(null, args) : ret);
  };
}
const stealFocus = process.argv[2] === 'steal';   // 模拟"新建窗口把浏览器抬到前台"
const chrome = {
  alarms: { create: record('alarms.create'), onAlarm: noop },
  runtime: { onInstalled: noop, onStartup: noop, onMessage: noop, onSuspend: noop },
  permissions: { onAdded: noop },
  storage: { local: { get: async () => ({}), set: async () => {} } },   // noteStatus 只落状态
  windows: {
    create: record('windows.create', () => ({ id: 777 })),
    get: async (id) => ({ id }),
    getLastFocused: (() => { let n = 0; return async () => ({ id: (stealFocus && n++ > 0) ? 777 : 1 }); })(),
    update: record('windows.update', () => ({})),
    remove: record('windows.remove', () => {}),
    onRemoved: noop,
  },
  tabs: {
    create: record('tabs.create', () => ({ id: 42, windowId: 777 })),
    get: async () => ({ id: 42, status: 'complete' }),
    remove: record('tabs.remove', () => {}),
  },
  scripting: { executeScript: async () => [{ result: '<html>page</html>' }] },
};
const sandbox = { chrome, importScripts: () => {}, console, setTimeout, clearTimeout, Date, Promise, JSON };
vm.createContext(sandbox);
vm.runInContext(fs.readFileSync(process.argv[1], 'utf8'), sandbox);
(async () => {
  const html = await sandbox.pageSnapshot('https://pt.example.com/myhr.php?hrtype=A');
  await sandbox.closeHiddenWindow();   // 顺手验证空闲关闭(否则 2 分钟的计时器会拖住 node)
  process.stdout.write(JSON.stringify({ html, calls }));
})();
"""


def _page_snapshot_trace(mode: str = "") -> dict:
    node = _node()
    if not node:
        return {}
    args = [node, "-e", _NODE_RUN_PAGE_SNAPSHOT, str(BACKGROUND_JS)]
    if mode:
        args.append(mode)
    proc = _run_node(args)
    assert proc.returncode == 0, f"node 跑 background.js 失败: {proc.stderr.strip()}"
    return json.loads(proc.stdout)


def _arg_of(trace: dict, name: str, key: str):
    """取某次调用里某个参数(断言用的小工具)"""
    for call in trace["calls"]:
        if call[0] == name and call[1] and isinstance(call[1], dict) and key in call[1]:
            return call[1][key]
    return None


def test_page_fetch_runs_in_dedicated_hidden_window():
    """❗页面取数必须在**自己的隐藏窗口**里: 用户窗口里开后台标签会连窗口一起被抬起来

    2026-09-25 用户实报「抓数据时会打开新的标签而不是后台抓取」: `chrome.tabs.create({active:false})`
    只保证「不是那个窗口的活动标签」, **不保证窗口不被抬起来** —— 扩展被 alarm 唤醒时用户往往正在
    别的程序里, Chrome 会把窗口连同新标签一起显示出来。故: 取数在自己建的窗口里做(最小化 + 不聚焦),
    且**任何**标签创建都必须带上那个窗口 id(否则又回到用户窗口里)。
    """
    trace = _page_snapshot_trace()
    if not trace:
        return  # 没装 node: 与其它前端守阵同口径静默跳过
    assert trace["html"] == "<html>page</html>"

    created = [c for c in trace["calls"] if c[0] == "windows.create"]
    assert len(created) == 1, f"应当只建一个取数窗口: {trace['calls']}"
    opts = created[0][1]
    assert opts.get("focused") is False, "取数窗口绝不能抢焦点"
    assert opts.get("state") == "minimized", "取数窗口要最小化(不占屏幕、不占任务栏焦点)"

    tabs = [c for c in trace["calls"] if c[0] == "tabs.create"]
    assert tabs, "页面取数仍要开标签页(需要真实渲染的 DOM)"
    for call in tabs:
        assert call[1].get("windowId") == 777, f"标签必须开在取数窗口里, 实际: {call[1]}"
        assert call[1].get("active") is False, f"标签不得成为活动标签: {call[1]}"
    assert "tabs.remove" in [c[0] for c in trace["calls"]], "取完要关标签(不留脏标签)"


def test_hidden_window_is_closed_when_idle_and_focus_handed_back():
    """空闲要能关掉那个窗口; 万一新建窗口把焦点抢走了, 取完要把焦点还回原窗口"""
    trace = _page_snapshot_trace()
    if not trace:
        return
    removed = [c for c in trace["calls"] if c[0] == "windows.remove"]
    assert [c[1] for c in removed] == [777], "空闲关闭必须真的删掉那个窗口"

    stolen = _page_snapshot_trace("steal")
    if not stolen:
        return
    restore = [c for c in stolen["calls"] if c[0] == "windows.update" and c[1] == 1]
    assert restore and restore[0][2].get("focused") is True, \
        f"焦点被抢走后要还回原窗口(否则用户正打字就被切走了): {stolen['calls']}"
