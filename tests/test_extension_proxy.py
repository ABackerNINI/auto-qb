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
