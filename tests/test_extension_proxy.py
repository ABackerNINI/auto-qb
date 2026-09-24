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
- test_page_fetch_is_headless_when_html_looks_fine: 直取能拿到页面时**不得开任何窗口/标签**(用户实报两轮)
- test_page_fetch_renders_offscreen_only_when_needed: 只在内容不像页面时才升级, 且用**离屏 popup 窗口**
- test_page_fetch_renders_when_direct_fetch_hits_login_page: 直取拿到登录页也要升级(SameSite 安全网)
- test_page_fetch_hands_focus_back_when_window_steals_it: 万一窗口抢了焦点, 取完还回原窗口
- test_site_caps_are_shared_single_source: 硬上限只有一份(site-caps.js), 后台与选项页都载入它
- test_extension_quota_caps_and_refuses: 真跑 background.js —— 同站访问/下载各自计数, 超限即**拒发**
  (不发请求 + 回传 kind=ext-quota + retry_after); 窗口键变了计数归零
- test_extension_torrent_login_page_detected: 真跑 background.js —— download.php 返回 HTML(登录页)时
  回传 kind=login-page, 让后端按「HR 登录失效」处置而不烧 .torrent 重试额度(2026-09-25 实报)
- test_logger_levels_ring_truncation_and_clear: 真跑 background.js —— 运行日志分级(低于记录级别直接丢)、
  环形上限(丢最旧)、超长字段截断(页面 HTML 整份进日志会撑爆 storage 配额)、清空后落盘为空数组
- test_log_ui_wiring_and_escape: 选项页日志面 —— 清空走 clear-logs 协议(两边一致, 直接改 storage
  会被后台内存缓冲盖回)、渲染过 esc 转义(明细含站点 URL/页面片段)、限渲染条数、
  storage.onChanged 自动刷新、日志容器在脚本之前
- test_options_poll_label_matches_background: 选项页「启用轮询(每 N 分钟…)」文案与 background.js 的
  POLL_MINUTES 同步(漂移史: 文案停在 5 分钟, 实际 v2.6 起已改 1 分钟, 用户照文案理解行为必对不上)
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
SITE_CAPS_JS = EXT_DIR / "site-caps.js"
BACKGROUND_JS = EXT_DIR / "background.js"
OPTIONS_JS = EXT_DIR / "options.js"
OPTIONS_HTML = EXT_DIR / "options.html"
JS_FILES = (NORMALIZE_JS, SITE_CAPS_JS, BACKGROUND_JS, OPTIONS_JS)

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


def test_site_caps_are_shared_single_source():
    """硬上限只有一份(site-caps.js): 后台用 importScripts、选项页用 <script> —— 都不许写死阈值

    两份分头演化的后果很具体: 选项页显示的数字与实际生效的阈值不符, 用户据此理解行为, 结果对不上。
    """
    caps = _read(SITE_CAPS_JS)
    assert "SITE_CAPS" in caps and "perHour" in caps and "perDay" in caps
    assert "importScripts('site-caps.js')" in _read(BACKGROUND_JS)
    html = _read(OPTIONS_HTML)
    assert "site-caps.js" in html and html.index("site-caps.js") < html.index("options.js"), "载入顺序: 常量在前"
    for path in (BACKGROUND_JS, OPTIONS_JS):
        assert not re.search(r"(?m)^const SITE_CAPS", _read(path)), f"{path.name} 又定义了一份阈值"
        assert "SITE_CAPS[" in _read(path) or "Object.entries(SITE_CAPS)" in _read(path), \
            f"{path.name} 应当消耗共享阈值而不是写死数字"


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


# ---------- 页面取数: 不打扰用户(实报两轮: 先「开新标签」后「开新窗口」) ----------

#: 两个页面样本(单点定义: 注入给 node 脚本, Python 侧断言也用同一份)
#: ① 服务端渲染的真页面(自带表格) ② 挑战页形态(短小、无表格 ⇒ 应当升级到渲染通道)
PAGE_WITH_TABLE = '<html><body><table class="main"><tr><td>HR编号</td></tr></table></body></html>'
CHALLENGE_LIKE = '<html><head><title>Just a moment...</title></head><body>Checking your browser</body></html>'
#: 带表格的**登录页** —— 直取可能因为 SameSite 不带 cookie 而拿到它, 必须当成"要升级渲染"的信号
LOGIN_LIKE = (
    '<html><body><table><tr><td>登录</td></tr></table>'
    '<form action="takelogin.php"><input type="password" name="password"></form></body></html>'
)

#: 用**假 chrome API** 真跑 background.js, 记录每一次窗口/标签调用 —— 纯字符串断言看不见调用形态。
#: 三个场景一次跑完(省 node 启动开销): direct=直取(页面自带表格) / render=直取内容不像页面 ⇒ 离屏渲染 /
#: steal=渲染时新窗口把浏览器抬到前台(看是否把焦点还回去)。
_NODE_RUN_PAGE_FETCH = """
const fs = require('fs');
const vm = require('vm');
const noop = { addListener() {} };
const PAGE_URL = 'https://pt.example.com/myhr.php?hrtype=A';
const PAGE_WITH_TABLE = __PAGE_WITH_TABLE__;
const CHALLENGE_LIKE = __CHALLENGE_LIKE__;
const LOGIN_LIKE = __LOGIN_LIKE__;
const store = {};
let calls = [];
let stealFocus = false;
function record(name, ret) {
  return function () {
    const args = Array.prototype.slice.call(arguments);
    calls.push([name].concat(args));
    return Promise.resolve(typeof ret === 'function' ? ret.apply(null, args) : ret);
  };
}
let focusedCalls = 0;
const chrome = {
  alarms: { create: record('alarms.create'), onAlarm: noop },
  runtime: { onInstalled: noop, onStartup: noop, onMessage: noop, onSuspend: noop },
  permissions: { onAdded: noop },
  storage: {
    onChanged: noop,   // background.js 顶层注册了「设置联动 / 外部清空采纳」监听
    local: {
      get: (defaults) => {
        const out = {};
        for (const key of Object.keys(defaults || {})) out[key] = (key in store) ? store[key] : defaults[key];
        return Promise.resolve(out);
      },
      set: (obj) => { Object.assign(store, obj); return Promise.resolve(); },
    },
  },   // 真存真读: noteStatus 与硬上限台账都要跨调用可见
  windows: {
    create: record('windows.create', () => ({ id: 777, tabs: [{ id: 42 }] })),
    get: async (id) => ({ id }),
    // 焦点守卫: 取数前返回用户窗口 1; 取数后若被抢走则返回我们建的窗口 777
    getLastFocused: async () => ({ id: (stealFocus && ++focusedCalls > 1) ? 777 : 1 }),
    update: record('windows.update', () => ({})),
    remove: record('windows.remove', () => {}),
  },
  tabs: {
    create: record('tabs.create', () => ({ id: 42, windowId: 777 })),
    get: async () => ({ id: 42, status: 'complete' }),
    remove: record('tabs.remove', () => {}),
  },
  scripting: { executeScript: async () => [{ result: PAGE_WITH_TABLE }] },
};
let nextPage = PAGE_WITH_TABLE;
const sandbox = {
  chrome, importScripts: () => {}, console, setTimeout, clearTimeout, Date, Promise, JSON, URL,
  fetch: async () => ({ ok: true, status: 200, text: async () => nextPage, json: async () => ({}) }),
};
vm.createContext(sandbox);
vm.runInContext(fs.readFileSync(process.argv[2], 'utf8'), sandbox);   // site-caps.js(模拟 importScripts)
vm.runInContext(fs.readFileSync(process.argv[1], 'utf8'), sandbox);   // background.js
async function scenario(name, page, steal) {
  calls = []; focusedCalls = 0; stealFocus = Boolean(steal); nextPage = page;
  const out = await sandbox.pageText(PAGE_URL);
  return [name, { out, calls }];
}
(async () => {
  const rows = [];
  rows.push(await scenario('direct', PAGE_WITH_TABLE, false));      // 直取: 页面自带表格
  rows.push(await scenario('render', CHALLENGE_LIKE, false));       // 直取内容不像页面 ⇒ 离屏渲染
  rows.push(await scenario('login', LOGIN_LIKE, false));            // 直取拿到登录页 ⇒ 也得升级渲染
  rows.push(await scenario('steal', CHALLENGE_LIKE, true));         // 同上, 且新窗口抢了焦点
  process.stdout.write(JSON.stringify(Object.fromEntries(rows)));
})();
"""

_PAGE_FETCH_TRACE: dict = {}


def page_fetch_trace() -> dict:
    """跑一次 node 拿三个场景的调用轨迹(缓存: 三个用例共用同一次 node 运行)"""
    if _PAGE_FETCH_TRACE:
        return _PAGE_FETCH_TRACE
    node = _node()
    if not node:
        return {}
    proc = _run_node(
        [
            node,
            "-e",
            _NODE_RUN_PAGE_FETCH.replace("__PAGE_WITH_TABLE__", json.dumps(PAGE_WITH_TABLE)).replace(
                "__CHALLENGE_LIKE__", json.dumps(CHALLENGE_LIKE)
            ).replace("__LOGIN_LIKE__", json.dumps(LOGIN_LIKE)),
            str(BACKGROUND_JS),
            str(SITE_CAPS_JS),
        ]
    )
    assert proc.returncode == 0, f"node 跑 background.js 失败: {proc.stderr.strip()}"
    _PAGE_FETCH_TRACE.update(json.loads(proc.stdout))
    return _PAGE_FETCH_TRACE


def _calls(trace: dict, name: str) -> list:
    return [c[0] for c in trace["calls"] if c[0] == name]


def _first(trace: dict, name: str):
    for call in trace["calls"]:
        if call[0] == name:
            return call
    return None


def test_page_fetch_is_headless_when_html_looks_fine():
    """❗默认必须**无界面**: 直取(带站点 cookie 的 fetch)就能拿到页面时, 绝不打开任何窗口/标签

    用户实报过两轮(先「抓数据时打开新标签」, 改完又「打开新窗口」)—— 所以这里钉死的不是
    「窗口该怎么开」, 而是**能不开就不开**: 站点侧页面(NexusPHP 这类)本来就是服务端渲染的表格。
    """
    trace = page_fetch_trace()
    if not trace:
        return  # 没装 node: 与其它前端守阵同口径静默跳过
    direct = trace["direct"]
    assert direct["out"] == {"text": PAGE_WITH_TABLE, "rendered": False}
    assert _calls(direct, "windows.create") == [], f"直取时不得开窗口: {direct['calls']}"
    assert _calls(direct, "tabs.create") == [], f"直取时不得开标签: {direct['calls']}"


def test_page_fetch_renders_offscreen_only_when_needed():
    """直取内容不像页面(挑战页 / 需 JS 渲染)才退到渲染通道: **离屏 popup + 不聚焦**, 用完连窗口删掉"""
    trace = page_fetch_trace()
    if not trace:
        return
    render = trace["render"]
    assert render["out"]["rendered"] is True, "内容里连表格都没有就该升级到渲染通道"
    assert render["out"]["text"] == PAGE_WITH_TABLE, "渲染通道要返回 DOM 快照"

    created = _first(render, "windows.create")
    assert created is not None, f"渲染通道要自己建窗口: {render['calls']}"
    opts = created[1]
    assert opts.get("type") == "popup", "popup 不进任务栏(比普通窗口更难被用户看到)"
    assert opts.get("state") == "minimized", "创建时就最小化(不再依赖后续 update)"
    assert opts.get("focused") is False, "绝不能抢焦点"
    assert opts.get("left") == -32000 and opts.get("top") == -32000, "必须离屏(最小化在部分平台仍会先显示)"
    assert opts.get("url") == "https://pt.example.com/myhr.php?hrtype=A", "建窗口时直接带目标 URL"
    assert _calls(render, "tabs.create") == [], "不得往用户窗口里开标签"
    assert _calls(render, "windows.remove") == ["windows.remove"], "用完要连窗口一起删"


def test_page_fetch_renders_when_direct_fetch_hits_login_page():
    """直取拿到**登录页**(带表格, 所以表格判据放过它)时也要升级渲染 —— SameSite 的安全网

    无 `SameSite` 属性的 cookie 按 Lax 对待, 而扩展发起的 fetch 算跨站子资源请求, 有可能不带 cookie。
    若不把「登录页」当成升级信号, 就会把「扩展取不到登录态」误报成站点改版(表头缺失), 把排查引到
    错的方向。渲染通道是真正的顶层导航, 一定带 cookie。
    """
    trace = page_fetch_trace()
    if not trace:
        return
    login = trace["login"]
    assert login["out"]["rendered"] is True, "登录页要升级渲染, 不能当正常页面"
    assert login["out"]["text"] == PAGE_WITH_TABLE, "升级后拿到的应当是渲染 DOM"
    assert _calls(login, "windows.create") == ["windows.create"], "升级就要开那个离屏窗口"


def test_page_fetch_hands_focus_back_when_window_steals_it():
    """万一建窗口仍把浏览器抬到前台: 取完要把焦点还回原窗口(用户可能正在打字)"""
    trace = page_fetch_trace()
    if not trace:
        return
    stolen = trace["steal"]
    restore = [c for c in stolen["calls"] if c[0] == "windows.update" and c[1] == 1]
    assert restore and restore[0][2].get("focused") is True, \
        f"焦点被抢走后要还回原窗口: {stolen['calls']}"


# ---------- 扩展侧硬上限(第二道闸: 后端出错时的兜底, 2026-09-25 用户指定) ----------

#: 用**真** storage(内存)真跑 background.js: 台账必须真存真读, 否则「计数」是自欺欺人。
#: 四个场景一次跑完: ①页面上限 10/时(第 11 次被拒且**不发请求**) ②下载有独立额度(页面用满照样能下)
#: ③窗口键过期 ⇒ 计数归零 ④日上限 50 ⇒ 拒发且 retry_after 指向次日
_NODE_RUN_QUOTA = """
const fs = require('fs');
const vm = require('vm');
const noop = { addListener() {} };
const PAGE_URL = 'https://pt.example.com/myhr.php?hrtype=A';
const DL_URL = 'https://pt.example.com/download.php?id=313852';
const PAGE = __PAGE_WITH_TABLE__;
const store = {};
let fetches = 0;
function getWithDefaults(defaults) {
  const out = {};
  for (const key of Object.keys(defaults || {})) out[key] = (key in store) ? store[key] : defaults[key];
  return Promise.resolve(out);
}
const chrome = {
  alarms: { create() {}, onAlarm: noop },
  runtime: { onInstalled: noop, onStartup: noop, onMessage: noop },
  permissions: { onAdded: noop },
  storage: { onChanged: noop, local: {   // onChanged: background.js 顶层注册了「设置联动 / 外部清空采纳」监听
    get: (defaults) => getWithDefaults(defaults),
    set: (obj) => { Object.assign(store, obj); return Promise.resolve(); },
  } },
  windows: {
    create: async () => ({ id: 1, tabs: [{ id: 1 }] }),
    getLastFocused: async () => ({ id: 1 }),
    update: async () => ({}),
    remove: async () => {},
  },
  tabs: { create: async () => ({ id: 1 }), get: async () => ({ status: 'complete' }), remove: async () => {} },
  scripting: { executeScript: async () => [{ result: PAGE }] },
};
const sandbox = {
  chrome, importScripts: () => {}, console, setTimeout, clearTimeout, Date, Promise, JSON, URL, btoa,
  TextDecoder, TextEncoder,   // fetchBinary 解析响应头/首字节要用(真实 SW 里有, 桩必须同形)
  fetch: async () => {
    fetches += 1;
    return { ok: true, status: 200,
             headers: { get: () => 'application/octet-stream' },   // 与真实 Response 同形(fetchBinary 读 content-type)
             text: async () => PAGE, arrayBuffer: async () => new ArrayBuffer(8),
             json: async () => ({}) };
  },
};
vm.createContext(sandbox);
vm.runInContext(fs.readFileSync(process.argv[2], 'utf8'), sandbox);   // site-caps.js(模拟 importScripts)
vm.runInContext(fs.readFileSync(process.argv[1], 'utf8'), sandbox);   // background.js
const LEDGER = vm.runInContext('SITE_LEDGER_KEY', sandbox);
const HOST = 'pt.example.com';
const page = (id) => sandbox.runTask({ id: id, kind: 'page', url: PAGE_URL }).then((r) => r.payload);
const torrent = (id) => sandbox.runTask({ id: id, kind: 'torrent', url: DL_URL }).then((r) => r.payload);
(async () => {
  const out = { pages: [], torrent: null, afterRollover: null, dayRefusal: null, ledgerKey: LEDGER };
  for (let i = 1; i <= 11; i += 1) out.pages.push(await page('p' + i));
  out.fetchesAfterPages = fetches;
  out.torrent = await torrent('t1');            // 下载与访问分开计数: 页面用满不影响它
  out.fetchesAfterTorrent = fetches;
  const led = store[LEDGER] || {};
  led[HOST].page.hk = '1970-01-01T00';          // 造「小时窗口已经翻篇」
  store[LEDGER] = led;
  out.afterRollover = await page('p12');        // 计数归零 ⇒ 又能取
  const led2 = store[LEDGER] || {};
  led2[HOST].page = {
    hk: vm.runInContext('hourKey(Date.now())', sandbox),
    dk: vm.runInContext('dayKey(Date.now())', sandbox),
    hour: 1,
    day: 50,                                    // 日上限已到
  };
  store[LEDGER] = led2;
  out.dayRefusal = await page('p13');
  out.fetchesAtEnd = fetches;
  out.ledger = store[LEDGER];
  process.stdout.write(JSON.stringify(out));
})();
"""

_QUOTA_TRACE: dict = {}


def quota_trace() -> dict:
    """跑一次 node 拿四个场景的结果(缓存: 两个用例共用同一次 node 运行)"""
    if _QUOTA_TRACE:
        return _QUOTA_TRACE
    node = _node()
    if not node:
        return {}
    proc = _run_node(
        [
            node, "-e",
            _NODE_RUN_QUOTA.replace("__PAGE_WITH_TABLE__", json.dumps(PAGE_WITH_TABLE)),
            str(BACKGROUND_JS),
            str(SITE_CAPS_JS)
        ]
    )
    assert proc.returncode == 0, f"node 跑 background.js 的配额场景失败: {proc.stderr.strip()}"
    _QUOTA_TRACE.update(json.loads(proc.stdout))
    return _QUOTA_TRACE


def test_extension_quota_caps_and_refuses():
    """超限即**拒发**: 不发请求 + 回传 kind=ext-quota + retry_after(后端据此让位, 不计失败)
    ❗这条闸的意义在「后端出错时」: 后端频控写错 / 配置被改坏 / 有人手工灌任务时, 浏览器仍然
    打不爆站点。所以断言要看两件事: ①第 11 次被拒 ②**它真的没有发出请求**(只看回传字段不算数)。
    """
    trace = quota_trace()
    if not trace:
        return  # 没装 node: 与其它前端守阵同口径静默跳过
    pages = trace["pages"]
    ok_pages = [p for p in pages if p.get("ok")]
    refused = [p for p in pages if not p.get("ok")]
    assert len(ok_pages) == 10, f"本小时访问上限 10 次: {[p.get('error') for p in pages]}"
    assert len(refused) == 1, "第 11 次必须被拒"
    assert refused[0].get("kind") == "ext-quota", f"要能被后端识别成配额让位: {refused[0]}"
    assert refused[0].get("retry_after", 0) > 0, "要告诉后端下一个窗口还有多久"
    assert "本小时" in refused[0].get("error", ""), refused[0].get("error")
    assert trace["fetchesAfterPages"] == 10, f"被拒的那次**不得发出请求**(发出去就白算安全网): {trace}"
    assert trace["torrent"].get("ok") is True, "下载与访问分开计数: 页面用满不该挡住 .torrent"
    assert trace["fetchesAfterTorrent"] == 11


def test_extension_quota_windows_roll_over():
    """窗口键翻篇就归零(与后端同一套口径), 日上限独立生效 —— 不能出现「一次超限永久停摆」"""
    trace = quota_trace()
    if not trace:
        return
    assert trace["afterRollover"].get("ok") is True, f"小时窗口翻篇后应恢复: {trace['afterRollover']}"
    day = trace["dayRefusal"]
    assert day.get("ok") is False and day.get("kind") == "ext-quota"
    assert "本日" in day.get("error", ""), day.get("error")
    assert day.get("retry_after", 0) > 0 and day.get("retry_after", 0) <= 86400
    assert trace["fetchesAtEnd"] == trace["fetchesAfterTorrent"] + 1, "日上限那次同样不得发出请求"


#: download.php 返回 HTML(登录页)的场景: fetchBinary 必须识别并标 kind=login-page,
#: 让后端按「HR 登录失效」处置(不计取数失败), 而不是回传 HTML 让 infohash 解析烧重试额度。
_NODE_RUN_LOGIN_PAGE = """
const fs = require('fs');
const vm = require('vm');
const noop = { addListener() {} };
const DL_URL = 'https://pt.example.com/download.php?id=313852';
const LOGIN_HTML = '<!doctype html><html><body><form action="takelogin.php">' +
  '<input type="password" name="password"></form></body></html>';
const store = {};
function getWithDefaults(defaults) {
  const out = {};
  for (const key of Object.keys(defaults || {})) out[key] = (key in store) ? store[key] : defaults[key];
  return Promise.resolve(out);
}
const chrome = {
  alarms: { create() {}, onAlarm: noop },
  runtime: { onInstalled: noop, onStartup: noop, onMessage: noop },
  permissions: { onAdded: noop },
  storage: { onChanged: noop, local: {   // onChanged: background.js 顶层注册了「设置联动 / 外部清空采纳」监听
    get: (defaults) => getWithDefaults(defaults),
    set: (obj) => { Object.assign(store, obj); return Promise.resolve(); },
  } },
};
const sandbox = {
  chrome, importScripts: () => {}, console, setTimeout, clearTimeout, Date, Promise, JSON, URL, btoa,
  TextDecoder, TextEncoder,
  fetch: async () => {
    const bytes = new TextEncoder().encode(LOGIN_HTML);
    return { ok: true, status: 200, headers: { get: () => 'text/html; charset=utf-8' },
             text: async () => LOGIN_HTML, arrayBuffer: async () => bytes.buffer, json: async () => ({}) };
  },
};
vm.createContext(sandbox);
vm.runInContext(fs.readFileSync(process.argv[2], 'utf8'), sandbox);   // site-caps.js(模拟 importScripts)
vm.runInContext(fs.readFileSync(process.argv[1], 'utf8'), sandbox);   // background.js
(async () => {
  const r = await sandbox.runTask({ id: 't1', kind: 'torrent', url: DL_URL });
  process.stdout.write(JSON.stringify({ payload: r.payload }));
})();
"""


def test_extension_torrent_login_page_detected():
    """download.php 返回 HTML ⇒ 回传 kind=login-page(后端按「登录失效」处置, 不计取数失败)"""
    node = _node()
    if not node:
        return  # 没装 node: 与其它前端守阵同口径静默跳过
    proc = _run_node([node, "-e", _NODE_RUN_LOGIN_PAGE, str(BACKGROUND_JS), str(SITE_CAPS_JS)])
    assert proc.returncode == 0, f"node 跑 background.js 的登录页场景失败: {proc.stderr.strip()}"
    payload = json.loads(proc.stdout)["payload"]
    assert payload.get("ok") is False
    assert payload.get("kind") == "login-page", f"必须标成登录页让后端免计失败: {payload}"
    assert "登录" in payload.get("error", ""), payload.get("error")


# ---------- 运行日志(分级 + 环形上限 + 落 storage) ----------

#: 真跑 background.js 的日志场景: ①默认记录级别 info ⇒ debug 直接丢, 且条目字段齐全、超长字段截断
#: ②环形上限 10 ⇒ 灌 25 条只留最新 10 条 ③记录级别实时生效(debug 收得进 / error 起滤掉 info)
#: ④clearLogs 清空后 storage 里是空数组。
_NODE_RUN_LOGGER = """
const fs = require('fs');
const vm = require('vm');
const noop = { addListener() {} };
const store = {};
const chrome = {
  alarms: { create() {}, onAlarm: noop },
  runtime: { onInstalled: noop, onStartup: noop, onMessage: noop },
  permissions: { onAdded: noop },
  storage: { onChanged: noop, local: {   // onChanged: background.js 顶层注册了「设置联动 / 外部清空采纳」监听
    get: (defaults) => {
      const out = {};
      for (const key of Object.keys(defaults || {})) out[key] = (key in store) ? store[key] : defaults[key];
      return Promise.resolve(out);
    },
    set: (obj) => { Object.assign(store, obj); return Promise.resolve(); },
  } },
};
const sandbox = { chrome, importScripts: () => {}, console, setTimeout, clearTimeout, Date, Promise, JSON };
vm.createContext(sandbox);
vm.runInContext(fs.readFileSync(process.argv[2], 'utf8'), sandbox);   // site-caps.js(模拟 importScripts)
vm.runInContext(fs.readFileSync(process.argv[1], 'utf8'), sandbox);   // background.js
(async () => {
  const out = {};
  await sandbox.log('debug', '任务', 'debug 行(应被丢)');
  await sandbox.log('info', '命令', '收到命令', { 站点: 'pt.example.com', url: 'https://pt.example.com/x', 耗时: '12ms' });
  await sandbox.log('warn', '配额', 'warn 行');
  await sandbox.log('error', '任务', 'error 行', { url: 'ab'.repeat(1000) });
  await sandbox.flushLogs();
  out.byLevel = (store.logs || []).map((e) => e.lvl);
  out.fields = (store.logs || [])[0];
  const longEntry = (store.logs || []).find((e) => e.lvl === 'error');
  out.longLen = (longEntry.url || '').length;
  out.longMark = (longEntry.url || '').includes('…(共');
  sandbox.applyLogSettings(10, undefined);
  for (let i = 1; i <= 25; i += 1) await sandbox.log('info', '任务', '行 ' + i);
  await sandbox.flushLogs();
  out.ringLen = store.logs.length;
  out.ringFirst = store.logs[0].msg;
  out.ringLast = store.logs[store.logs.length - 1].msg;
  sandbox.applyLogSettings(undefined, 'debug');
  await sandbox.log('debug', '任务', 'debug 行(应收)');
  sandbox.applyLogSettings(undefined, 'error');
  await sandbox.log('info', '任务', 'info 行(应被丢)');
  await sandbox.flushLogs();
  out.debugKept = store.logs.some((e) => e.msg === 'debug 行(应收)');
  out.infoDropped = !store.logs.some((e) => e.msg === 'info 行(应被丢)');
  await sandbox.clearLogs();
  out.afterClear = Array.isArray(store.logs) && store.logs.length === 0;
  process.stdout.write(JSON.stringify(out));
})();
"""


def test_logger_levels_ring_truncation_and_clear():
    """运行日志: 分级(低于记录级别直接丢) / 环形上限(丢最旧) / 超长截断 / 清空 —— 真跑 background.js"""
    node = _node()
    if not node:
        return  # 没装 node: 与其它前端守阵同口径静默跳过
    proc = _run_node([node, "-e", _NODE_RUN_LOGGER, str(BACKGROUND_JS), str(SITE_CAPS_JS)])
    assert proc.returncode == 0, f"node 跑 background.js 的日志场景失败: {proc.stderr.strip()}"
    got = json.loads(proc.stdout)
    assert got["byLevel"] == ["info", "warn", "error"], f"低于记录级别(debug)要直接丢弃: {got['byLevel']}"
    fields = got["fields"]
    for key in ("t", "lvl", "cat", "msg", "站点", "url", "耗时"):
        assert key in fields, f"日志条目缺字段 {key}: {fields}"
    assert got["longMark"] and got["longLen"] < 450, f"超长字段必须截断(整份 HTML 进日志会撑爆配额): {got}"
    assert got["ringLen"] == 10 and got["ringFirst"] == "行 16" and got["ringLast"] == "行 25", f"环形缓冲要丢最旧的: {got}"
    assert got["debugKept"] and got["infoDropped"], f"记录级别要实时生效: {got}"
    assert got["afterClear"], f"清空后 storage 里应是空数组: {got}"


def test_log_ui_wiring_and_escape():
    """选项页日志面: 清空走后台协议(直接改 storage 会被后台内存缓冲盖回)、渲染必须转义、限渲染条数"""
    js = _read(OPTIONS_JS)
    bg = _read(BACKGROUND_JS)
    html = _read(OPTIONS_HTML)
    assert "'clear-logs'" in js and "'clear-logs'" in bg, "清空要经后台清(内存缓冲是唯一写入口)"
    assert "logMax" in js and "logLevel" in js, "条数上限与记录级别要能落盘"
    assert "logFilter" in html and "logView" in html, "分级显示的过滤控件与日志视图要在页面上"
    assert html.index("logView") < html.index("options.js"), "日志容器要在脚本之前(否则 getElementById 拿不到)"
    assert "esc(" in js, "日志渲染必须过 HTML 转义(明细含站点 URL/页面片段, 裸插 innerHTML 是注入面)"
    assert "chrome.storage.onChanged" in js, "后台落盘后选项页要自动刷出来(不用手点刷新)"
    assert "LOG_RENDER_CAP" in js, "全量渲染 10000 行会卡死选项页, 必须限渲染条数"


def test_options_poll_label_matches_background():
    """选项页的轮询周期文案必须与 background.js 的 POLL_MINUTES 同步(漂移史: 文案停在 5 分钟,
    实际 v2.6 起已改 1 分钟 —— 用户按选项页显示的数字理解行为, 对不上就把排查引向歧途)"""
    bg = _read(BACKGROUND_JS)
    html = _read(OPTIONS_HTML)
    m = re.search(r"const POLL_MINUTES = (\d+);", bg)
    assert m, "POLL_MINUTES 常量要存在(改用别的名字时这条断言一起改)"
    assert f"每 {m.group(1)} 分钟" in html, f"选项页轮询周期文案与 POLL_MINUTES={m.group(1)} 不一致, 两处要同步改"
