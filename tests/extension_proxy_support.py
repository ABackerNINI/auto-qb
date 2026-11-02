"""`extension_proxy_support` 支撑: 从 `test_extension_proxy.py` 拆出的模块级辅助/常量(move-only 搬迁, 未改语义)."""

import json

import pathlib

import re

import shutil

import subprocess

import pytest

from auto_qb.hr.channel import API_RESULT, API_SITES, API_TASKS, TOKEN_HEADER, HrChannelError, HrResult

from auto_qb.hr.discovery import API_DISCOVER, DISCOVERY_DEFAULT_PORT

EXT_DIR = pathlib.Path(__file__).resolve().parents[1] / "extensions" / "hr-fetch-proxy"

MANIFEST = EXT_DIR / "manifest.json"

NORMALIZE_JS = EXT_DIR / "normalize.js"

DISCOVERY_JS = EXT_DIR / "discovery.js"

SITE_CAPS_JS = EXT_DIR / "site-caps.js"

BACKGROUND_JS = EXT_DIR / "background.js"

OPTIONS_JS = EXT_DIR / "options.js"

OPTIONS_HTML = EXT_DIR / "options.html"

JS_FILES = (NORMALIZE_JS, DISCOVERY_JS, SITE_CAPS_JS, BACKGROUND_JS, OPTIONS_JS)

#: 归一化的行为钉死表 —— **含用户 2026-09-24 实际踩到的两种写法**。
#: (kind, 输入, 期望输出或 None=应当报错)
#: 去端口+跨机(计划 26-10-14-1241 S4/V5)翻转的两条旧语义: 私网放行(原「非回环即抛」)、
#: https 保留(原「一律折 http」); 新增 disc 类 = normalizeDiscovery(缺端口补 18788)。
NORMALIZE_CASES = [
    ("ep", "127.0.0.1:8788", "http://127.0.0.1:8788"),
    ("ep", "  http://127.0.0.1:8788/  ", "http://127.0.0.1:8788"),
    ("ep", "http://localhost:8788/", "http://127.0.0.1:8788"),
    ("ep", "https://127.0.0.1:8788", "https://127.0.0.1:8788"),
    ("ep", "127.0.0.1", None),
    ("ep", "192.168.1.9:8788", "http://192.168.1.9:8788"),
    ("ep", "10.0.0.5:8788", "http://10.0.0.5:8788"),
    ("ep", "172.16.31.5:8788", "http://172.16.31.5:8788"),
    ("ep", "pt.example.com:8788", None),
    ("ep", "http://pt.example.com:8788", None),
    ("ep", "", None),
    ("disc", "192.168.1.10", "http://192.168.1.10:18788"),
    ("disc", "http://192.168.1.10:18788/", "http://192.168.1.10:18788"),
    ("disc", "nas.local", None),
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
const mod = new Function(src + '\\nreturn {normalizeEndpoint, normalizeOrigin, normalizeDiscovery};')();
const out = [];
for (const [kind, input] of JSON.parse(process.argv[2])) {
  try {
    const fn = kind === 'ep' ? mod.normalizeEndpoint : kind === 'disc' ? mod.normalizeDiscovery : mod.normalizeOrigin;
    out.push({ kind, input, got: fn(input) });
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


def _balanced_block(text: str, start: int) -> str:
    """从 start(须指向 '{')起取到配平的 '}' —— 切出 JS 回调/函数体(本文件的块内无含花括号的字符串)"""
    depth = 0
    for i in range(start, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return text[start:i + 1]
    raise AssertionError("花括号不配平")


def _js_object_block(text: str, decl: str) -> str:
    """切出 `const X = { ... };` 的块体(首个 `};` 收尾)"""
    start = text.index(decl)
    return text[start:text.index("};", start)]


def _js_object_keys(block: str) -> list:
    """取对象字面量的顶层键名(保序; 键可带引号, 如 'no-hit')"""
    return re.findall(r"(?m)^\s*'?([A-Za-z_][\w-]*)'?\s*:", block)


#: 两个页面样本(单点定义: 注入给 node 脚本, Python 侧断言也用同一份)
#: 1. 服务端渲染的真页面(自带表格) 2. 挑战页形态(短小、无表格 ⇒ 应当升级到渲染通道)
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
vm.runInContext(fs.readFileSync(process.argv[3], 'utf8'), sandbox);   // discovery.js(默认发现端口常量; 模拟 importScripts)
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
            str(DISCOVERY_JS),
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


#: 用**真** storage(内存)真跑 background.js: 台账必须真存真读, 否则「计数」是自欺欺人。
#: 四个场景一次跑完: 1.页面上限(第 cap+1 次被拒且**不发请求**) 2.下载有独立额度(页面用满照样能下)
#: 3.窗口键过期 ⇒ 计数归零 4.日上限 ⇒ 拒发且 retry_after 指向次日。
#: !阈值一律从 site-caps.js 现值动态取(SITE_CAPS), 场景与断言**不许硬编码魔法数字** ——
#: 09d4109(配额双桶)把 10/50 提到 60/600·50/200 时, 硬编码守阵红了一天没人看见(本机无 node 静默跳过)。
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
vm.runInContext(fs.readFileSync(process.argv[3], 'utf8'), sandbox);   // discovery.js(默认发现端口常量; 模拟 importScripts)
vm.runInContext(fs.readFileSync(process.argv[2], 'utf8'), sandbox);   // site-caps.js(模拟 importScripts)
vm.runInContext(fs.readFileSync(process.argv[1], 'utf8'), sandbox);   // background.js
const LEDGER = vm.runInContext('SITE_LEDGER_KEY', sandbox);
const CAPS = JSON.parse(vm.runInContext('JSON.stringify(SITE_CAPS)', sandbox));   // 阈值动态取: 不硬编码(漂移教训)
const HOST = 'pt.example.com';
const page = (id) => sandbox.runTask({ id: id, kind: 'page', url: PAGE_URL }).then((r) => r.payload);
const torrent = (id) => sandbox.runTask({ id: id, kind: 'torrent', url: DL_URL }).then((r) => r.payload);
(async () => {
  const out = { pages: [], torrent: null, afterRollover: null, dayRefusal: null, ledgerKey: LEDGER };
  for (let i = 1; i <= CAPS.page.perHour + 1; i += 1) out.pages.push(await page('p' + i));
  out.pageHourCap = CAPS.page.perHour;
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
    day: CAPS.page.perDay,                      // 日上限已到
  };
  out.pageDayCap = CAPS.page.perDay;
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
            str(DISCOVERY_JS),
            str(SITE_CAPS_JS)
        ]
    )
    assert proc.returncode == 0, f"node 跑 background.js 的配额场景失败: {proc.stderr.strip()}"
    _QUOTA_TRACE.update(json.loads(proc.stdout))
    return _QUOTA_TRACE


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
vm.runInContext(fs.readFileSync(process.argv[3], 'utf8'), sandbox);   // discovery.js(默认发现端口常量; 模拟 importScripts)
vm.runInContext(fs.readFileSync(process.argv[2], 'utf8'), sandbox);   // site-caps.js(模拟 importScripts)
vm.runInContext(fs.readFileSync(process.argv[1], 'utf8'), sandbox);   // background.js
(async () => {
  const r = await sandbox.runTask({ id: 't1', kind: 'torrent', url: DL_URL });
  process.stdout.write(JSON.stringify({ payload: r.payload }));
})();
"""

#: 事件环(选项页两表的数据源)守阵: 真跑 background.js 走六类场景 —— 页面成功×2 / HTTP 失败 /
#: .torrent 成功 / .torrent 登录页 / 配额让位 —— 断言每类都双写出结构化事件且字段齐全。
_NODE_RUN_EVENTS = """
const fs = require('fs');
const vm = require('vm');
const noop = { addListener() {} };
const PAGE_URL = 'https://pt.example.com/myhr.php?hrtype=A';
const DL_URL = 'https://pt.example.com/download.php?id=313852';
const PAGE_WITH_TABLE = '<html><body><table class="main"><tr><td>HR</td></tr></table></body></html>';
const LOGIN_HTML = '<!doctype html><html><body><form><input type="password"></form></body></html>';
const BIN = new Uint8Array(2048).fill(65);
let mode = 'page-ok';
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
const sandbox = {
  chrome, importScripts: () => {}, console, setTimeout, clearTimeout, Date, Promise, JSON, URL, btoa,
  TextDecoder, TextEncoder,
  fetch: async () => {
    if (mode === 'http-403') return { ok: false, status: 403 };
    if (mode === 'torrent-ok') {
      return { ok: true, status: 200, headers: { get: () => 'application/x-bittorrent' }, arrayBuffer: async () => BIN.buffer };
    }
    if (mode === 'torrent-login') {
      const bytes = new TextEncoder().encode(LOGIN_HTML);
      return { ok: true, status: 200, headers: { get: () => 'text/html' }, arrayBuffer: async () => bytes.buffer };
    }
    return { ok: true, status: 200, text: async () => PAGE_WITH_TABLE, json: async () => ({}) };
  },
};
vm.createContext(sandbox);
vm.runInContext(fs.readFileSync(process.argv[3], 'utf8'), sandbox);   // discovery.js(默认发现端口常量; 模拟 importScripts)
vm.runInContext(fs.readFileSync(process.argv[2], 'utf8'), sandbox);   // site-caps.js(模拟 importScripts)
vm.runInContext(fs.readFileSync(process.argv[1], 'utf8'), sandbox);   // background.js
(async () => {
  await sandbox.runTask({ id: 'p1', kind: 'page', url: PAGE_URL });    // ok(计 1 次访问)
  await sandbox.runTask({ id: 'p2', kind: 'page', url: PAGE_URL });    // ok(计 2)
  mode = 'http-403';
  await sandbox.runTask({ id: 'p3', kind: 'page', url: PAGE_URL });    // error(计 3)
  mode = 'torrent-ok';
  await sandbox.runTask({ id: 't1', kind: 'torrent', url: DL_URL });   // ok(下种计数独立)
  mode = 'torrent-login';
  await sandbox.runTask({ id: 't2', kind: 'torrent', url: DL_URL });   // login
  mode = 'page-ok';
  const CAPS = JSON.parse(vm.runInContext('JSON.stringify(SITE_CAPS)', sandbox));  // 阈值动态取: 不硬编码(漂移教训)
  for (let i = 0; i < CAPS.page.perHour - 3; i += 1) await sandbox.requireAllowance('page', PAGE_URL);  // 计满本时访问额度(3+fill=cap)
  const quota = await sandbox.runTask({ id: 'p4', kind: 'page', url: PAGE_URL }); // 超限那次 → quota
  await sandbox.flushEvents();
  process.stdout.write(JSON.stringify({ quotaPayload: quota.payload, events: store.events || [] }));
})();
"""

#: 真跑 background.js 的日志场景: 1.默认记录级别 info ⇒ debug 直接丢, 且条目字段齐全、超长字段截断
#: 2.环形上限 10 ⇒ 灌 25 条只留最新 10 条 3.记录级别实时生效(debug 收得进 / error 起滤掉 info)
#: 4.clearLogs 清空后 storage 里是空数组。
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
vm.runInContext(fs.readFileSync(process.argv[3], 'utf8'), sandbox);   // discovery.js(默认发现端口常量; 模拟 importScripts)
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

#: 连不上时的降噪场景(2026-09-28 用户实报: 后端不在跑时每轮一条全量排查清单 ERROR + 状态栏同文,
#: 日志环被复读机灌满)。真跑 background.js 的 pollAll 五步: 1.首报全量 2.连败降 debug 3.第 30 轮重提
#: 4.恢复补 INFO 并清计数 5.恢复后再挂重新首报。记录级别预置 debug —— 连败期的 debug 短句要看得见;
#: normalize.js 也要真载入(safeEndpoint 要用 normalizeEndpoint)。
_NODE_RUN_NOISE = """
const fs = require('fs');
const vm = require('vm');
const noop = { addListener() {} };
const EP = 'http://127.0.0.1:18788';
const TASKS_URL = EP + '/api/hr/tasks';
// discoveryAddress 置空 = 显式关闭发现: 本用例钉的是「连接失败降噪」, 不让发现流的日志混进计数
const store = { enabled: true, logLevel: 'debug', discoveryAddress: '', instances: [{ name: '本机', endpoint: EP, token: 't' }] };
let down = true;
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
const sandbox = { chrome, importScripts: () => {}, console, setTimeout, clearTimeout, Date, Promise, JSON, URL,
  fetch: async () => {
    if (down) throw new TypeError('Failed to fetch');
    return { ok: true, status: 200, text: async () => '', json: async () => ({ tasks: [] }) };
  } };
vm.createContext(sandbox);
vm.runInContext(fs.readFileSync(process.argv[2], 'utf8'), sandbox);   // normalize.js(safeEndpoint 要用)
vm.runInContext(fs.readFileSync(process.argv[3], 'utf8'), sandbox);   // discovery.js(与 importScripts 同序)
vm.runInContext(fs.readFileSync(process.argv[4], 'utf8'), sandbox);   // site-caps.js(模拟 importScripts)
vm.runInContext(fs.readFileSync(process.argv[1], 'utf8'), sandbox);   // background.js
const delta = async (fn) => {   // 只取本轮新增的日志行(级别|类别|文案)
  const before = (store.logs || []).length;
  await fn();
  return (store.logs || []).slice(before).map((e) => e.lvl + '|' + e.cat + '|' + e.msg);
};
(async () => {
  const out = {};
  out.r1 = await delta(() => sandbox.pollAll('定时'));            // 第 1 轮: 首报全量
  out.r2 = await delta(() => sandbox.pollAll('定时'));            // 第 2 轮: 连败降噪
  out.r3 = await delta(() => sandbox.pollAll('定时'));            // 第 3 轮: 同上
  out.streak = JSON.parse(JSON.stringify(store.netFailStreak || {}));   // 深拷贝快照: 活引用会被后续轮次原地变异
  store.netFailStreak = { [TASKS_URL]: { n: 29 } };                     // 造「已连败 29 轮」
  out.r30 = await delta(() => sandbox.pollAll('定时'));                  // 第 30 轮: 重提全量
  down = false;
  out.rOk = await delta(() => sandbox.pollAll('定时'));                  // 恢复: 补一句 INFO + 清计数
  out.streakAfterOk = JSON.parse(JSON.stringify(store.netFailStreak || {}));
  down = true;
  out.rAgain = await delta(() => sandbox.pollAll('定时'));        // 恢复后再挂: 重新首报
  process.stdout.write(JSON.stringify(out));
})();
"""

#: 真跑 discovery.js —— 候选推导 / 合并语义 / 配对判定 / 形态过滤(纯函数, node 直接 eval)。
_NODE_RUN_DISCOVERY_HELPERS = """
const fs = require('fs');
const src = fs.readFileSync(process.argv[1], 'utf8');
const mod = new Function(src + '\\nreturn {API_DISCOVER, DISCOVERY_DEFAULT_PORT, discoveryCandidates, buildDiscoveryUrl, pairingNeeded, mergeInstances, isManualEntry, validDiscoveryPayload};')();
const out = {};
out.apiDiscover = mod.API_DISCOVER;
out.defaultPort = mod.DISCOVERY_DEFAULT_PORT;
out.cands = mod.discoveryCandidates('http://192.168.1.10:18788');
out.candsCap = mod.discoveryCandidates('http://192.168.1.10:65534');
out.candsBad = mod.discoveryCandidates('not-a-url');
out.url = mod.buildDiscoveryUrl('http://192.168.1.10:18788/');
out.pairYes = mod.pairingNeeded({ status: 401, error: 'pairing_required' });
out.pairNoStatus = mod.pairingNeeded({ status: 403, error: 'pairing_required' });
out.pairNoError = mod.pairingNeeded({ status: 401, error: 'unauthorized' });
out.merged = mod.mergeInstances(
  [
    { name: 'm', endpoint: 'http://192.168.1.10:5001', token: 'old' },
    { name: 'hand', endpoint: 'http://127.0.0.1:8788', token: 'h' },
  ],
  [
    { name: 'd1', endpoint: 'http://192.168.1.10:5001', token: 'new' },
    { name: 'd2', endpoint: 'http://192.168.1.10:5002', token: 't2' },
    { name: 'half', endpoint: 'http://192.168.1.10:5003' },
  ]
);
// 整批替换: 旧的 discovered 条目(死端点)必须被剪除, 手动条目照旧
out.replaced = mod.mergeInstances(
  [
    { name: 'hand', endpoint: 'http://127.0.0.1:8788', token: 'h' },
    { name: 'dead', endpoint: 'http://192.168.1.10:5099', token: 'x', source: 'discovered' },
  ],
  [
    { name: 'd1', endpoint: 'http://192.168.1.10:5001', token: 'new' },
    { name: 'd2', endpoint: 'http://192.168.1.10:5002', token: 't2' },
  ]
);
// 空集例外(C1): 发现返回空 ⇒ 保留旧发现集, 绝不清空
out.emptyKept = mod.mergeInstances(
  [
    { name: 'hand', endpoint: 'http://127.0.0.1:8788', token: 'h' },
    { name: 'stale', endpoint: 'http://192.168.1.10:5099', token: 'x', source: 'discovered' },
  ],
  []
);
out.manualFlags = [
  mod.isManualEntry({ endpoint: 'http://a:1' }),
  mod.isManualEntry({ endpoint: 'http://a:1', source: 'discovered' }),
  mod.isManualEntry(null),
];
out.validOk = mod.validDiscoveryPayload({ instances: [{ endpoint: 'http://x:1', token: 't' }] });
out.validNoArray = mod.validDiscoveryPayload({});
out.validHalf = mod.validDiscoveryPayload({ instances: [{ endpoint: 'http://x:1' }] });
process.stdout.write(JSON.stringify(out));
"""

_DISCOVERY_HELPERS_TRACE: dict = {}


def discovery_helpers_trace() -> dict:
    """跑一次 node 拿 discovery.js 纯函数的全部断言点(缓存: 合并语义的多条用例共用同一次 node 运行)"""
    if _DISCOVERY_HELPERS_TRACE:
        return _DISCOVERY_HELPERS_TRACE
    node = _node()
    if not node:
        return {}
    proc = _run_node([node, "-e", _NODE_RUN_DISCOVERY_HELPERS, str(DISCOVERY_JS)])
    assert proc.returncode == 0, f"node 执行 discovery.js 失败: {proc.stderr.strip()}"
    _DISCOVERY_HELPERS_TRACE.update(json.loads(proc.stdout))
    return _DISCOVERY_HELPERS_TRACE


#: 真跑 background.js 的发现流程: 三候选并行探测(命中次位)/ 配对码随头上来 / 合并落盘 /
#: 401 pairing_required 置标记 / 异形应答按「非本服务」忽略 / 全未命中明确报告(退手动, 不静默)。
_NODE_RUN_DISCOVERY_FLOW = """
const fs = require('fs');
const vm = require('vm');
const noop = { addListener() {} };
const store = { enabled: true, logLevel: 'debug', discoveryAddress: 'http://192.168.1.10:18788', pairingCode: '123456' };
let mode = 'ok-second';   // 首候选被普通应用占用(404), 次候选命中
let calls = [];
const DISCOVER_BODY = { instances: [
  { id: 'a1', name: 'nas', endpoint: 'http://192.168.1.10:5001', token: 'k1' },
  { id: 'a2', name: 'nas2', endpoint: 'http://192.168.1.10:5002', token: 'k2' },
] };
const chrome = {
  alarms: { create() {}, onAlarm: noop },
  runtime: { onInstalled: noop, onStartup: noop, onMessage: noop },
  permissions: { onAdded: noop },
  storage: { onChanged: noop, local: {
    get: (defaults) => { const out = {}; for (const k of Object.keys(defaults || {})) out[k] = (k in store) ? store[k] : defaults[k]; return Promise.resolve(out); },
    set: (obj) => { Object.assign(store, obj); return Promise.resolve(); },
  } },
};
const sandbox = { chrome, importScripts: () => {}, console, setTimeout, clearTimeout, Date, Promise, JSON, URL,
  fetch: async (url, opts) => {
    calls.push([String(url), opts && opts.headers ? opts.headers['X-Hr-Pairing'] : undefined]);
    if (mode === 'down') throw new TypeError('Failed to fetch');
    if (mode === 'pairing') return { status: 401, json: async () => ({ error: 'pairing_required' }) };
    if (mode === 'weird') return { status: 200, json: async () => ({ html: '<html>not-us</html>' }) };
    if (mode === 'ok-second' && Number(new URL(url).port) === 18788) return { status: 404, json: async () => ({}) };
    return { status: 200, json: async () => DISCOVER_BODY };
  } };
vm.createContext(sandbox);
vm.runInContext(fs.readFileSync(process.argv[2], 'utf8'), sandbox);   // normalize.js
vm.runInContext(fs.readFileSync(process.argv[3], 'utf8'), sandbox);   // discovery.js
vm.runInContext(fs.readFileSync(process.argv[4], 'utf8'), sandbox);   // site-caps.js
vm.runInContext(fs.readFileSync(process.argv[1], 'utf8'), sandbox);   // background.js
(async () => {
  const out = {};
  out.hit = await sandbox.runDiscovery('测试');
  out.hitCalls = calls.slice();
  out.instances = JSON.parse(JSON.stringify(store.instances || []));
  out.pairingCleared = store.pairingNeeded;
  calls = []; mode = 'pairing';
  store.pairingNeeded = false;
  out.pair = await sandbox.runDiscovery('测试');
  out.pairFlag = store.pairingNeeded;
  mode = 'weird';
  out.weird = await sandbox.runDiscovery('测试');
  mode = 'down';
  out.down = await sandbox.runDiscovery('测试');
  process.stdout.write(JSON.stringify(out));
})();
"""

#: 真跑 background.js 的**自愈**场景(六轮 pollAll + 徽标四态), 一轮一断言点:
#: 1. 1 死 1 活(旧口径「全部实例连败」不触发) ⇒ 任一失败即发现 + 落结构化快照 + 台账/徽标
#: 2. 紧接着再跑一轮 ⇒ 60s 节流: 不重复发现
#: 3. 全 401(端点有应答=连接是通的, 距上次 70s) ⇒ **不**触发发现
#: 4. 同钟位正对照: 真失败 ⇒ 发现开火(证明第 3 轮的"没开火"不是被节流挡的)
#: 5. 实例清单为空 + 距上次 130s ⇒ 仍按周期发现(R1: 否则发现集为空时连接再也回不来)
#: 6. 徽标四态纯函数取值 + 禁用清空 + 图标点击开选项页
_NODE_RUN_SELFHEAL = """
const fs = require('fs');
const vm = require('vm');
const noop = { addListener() {} };
const A = 'http://127.0.0.1:9001';   // 恒活
const B = 'http://127.0.0.1:9002';   // 可坏
const store = {
  enabled: true, logLevel: 'debug', discoveryAddress: 'http://127.0.0.1:18788',
  instances: [{ name: 'a', endpoint: A, token: 't1' }, { name: 'b', endpoint: B, token: 't2' }],
};
let bDown = true;
let b401 = false;
let fetches = [];
let badge = { text: null, color: null, title: null };
let icon = null;
let opened = 0;
let onClicked = null;
const chrome = {
  alarms: { create() {}, onAlarm: noop },
  runtime: {
    onInstalled: noop, onStartup: noop, onMessage: noop,
    openOptionsPage: () => { opened += 1; return Promise.resolve(); },
  },
  permissions: { onAdded: noop },
  action: {
    onClicked: { addListener: (fn) => { onClicked = fn; } },
    setBadgeText: (o) => { badge.text = o.text; return Promise.resolve(); },
    setBadgeBackgroundColor: (o) => { badge.color = o.color; return Promise.resolve(); },
    setTitle: (o) => { badge.title = o.title; return Promise.resolve(); },
    setIcon: (o) => { icon = o.path; return Promise.resolve(); },
  },
  storage: { onChanged: noop, local: {
    get: (defaults) => { const out = {}; for (const k of Object.keys(defaults || {})) out[k] = (k in store) ? store[k] : defaults[k]; return Promise.resolve(out); },
    set: (obj) => { Object.assign(store, obj); return Promise.resolve(); },
  } },
};
const sandbox = { chrome, importScripts: () => {}, console, setTimeout, clearTimeout, Date, Promise, JSON, URL,
  fetch: async (url) => {
    const u = String(url);
    fetches.push(u);
    if (u.endsWith('/api/hr/discover')) {
      // 首候选被普通应用占用(404), 次候选(18788)命中 —— 逐候选结果因此有内容可渲染
      if (!u.includes(':18788')) return { status: 404, json: async () => ({}) };
      return { status: 200, json: async () => ({ instances: [{ id: 'd', name: 'd', endpoint: 'http://127.0.0.1:9003', token: 'k3' }] }) };
    }
    if (u.startsWith(B) && bDown) throw new TypeError('Failed to fetch');
    if (u.startsWith(B) && b401) return { status: 401, ok: false, json: async () => ({}) };
    return { ok: true, status: 200, json: async () => ({ tasks: [] }) };
  } };
vm.createContext(sandbox);
vm.runInContext(fs.readFileSync(process.argv[2], 'utf8'), sandbox);   // normalize.js
vm.runInContext(fs.readFileSync(process.argv[3], 'utf8'), sandbox);   // discovery.js
vm.runInContext(fs.readFileSync(process.argv[4], 'utf8'), sandbox);   // site-caps.js
vm.runInContext(fs.readFileSync(process.argv[1], 'utf8'), sandbox);   // background.js
const discovers = () => fetches.filter((u) => u.endsWith('/api/hr/discover')).length;
const snap = (v) => JSON.parse(JSON.stringify(v));
(async () => {
  const out = {};
  out.period = vm.runInContext('DISCOVERY_EVERY_MINUTES', sandbox);
  out.minGapMs = vm.runInContext('DISCOVERY_MIN_GAP_MS', sandbox);

  await sandbox.pollAll('定时');                       // 1. 1 死 1 活
  out.aDiscovers = discovers();
  out.aSnapshot = snap(store.lastDiscovery || null);
  out.aHealth = snap(store.instanceHealth || {});
  out.aBadge = snap(badge);

  await sandbox.pollAll('定时');                       // 2. 60s 节流
  out.bDiscovers = discovers();
  out.bHealth = snap(store.instanceHealth || {});

  store.lastDiscoveryAt = Date.now() - 70000;          // 3. 全 401: 有应答 ⇒ 不算失败
  bDown = false; b401 = true;
  await sandbox.pollAll('定时');
  out.cDiscovers = discovers();

  b401 = false; bDown = true;                          // 4. 同钟位正对照: 真失败 ⇒ 开火
  store.lastDiscoveryAt = Date.now() - 70000;
  await sandbox.pollAll('定时');
  out.dDiscovers = discovers();

  store.instances = [];                                // 5. 实例为空也跑周期发现(R1)
  store.lastDiscoveryAt = Date.now() - 130000;
  await sandbox.pollAll('定时');
  out.eDiscovers = discovers();
  out.eHealth = snap(store.instanceHealth || {});

  out.badgeStates = [                                  // 6. 徽标四态 + 禁用清空 + 点击
    sandbox.badgeStateOf({ instances: [], discoveryAddress: '' }),
    sandbox.badgeStateOf({
      instances: [{ endpoint: A }], discoveryAddress: 'http://127.0.0.1:18788', instanceHealth: { [A]: { ok: true } }
    }),
    sandbox.badgeStateOf({
      instances: [], discoveryAddress: 'http://127.0.0.1:18788', instanceHealth: {},
      lastDiscovery: { ok: false, answered: true }
    }),
    sandbox.badgeStateOf({
      instances: [{ endpoint: A }], discoveryAddress: 'http://127.0.0.1:18788', instanceHealth: {},
      lastDiscovery: { ok: false, answered: false }
    }),
  ];
  store.instances = [{ name: 'a', endpoint: A, token: 't1' }];
  store.instanceHealth = { [A]: { ok: true, at: Date.now(), note: 'a: 无任务', failStreak: 0 } };
  store.lastDiscovery = { ok: true, answered: true };
  await sandbox.refreshBadge();
  out.badgeOk = snap(badge);
  out.iconOk = snap(icon);
  store.enabled = false;
  await sandbox.refreshBadge();
  out.badgeDisabled = snap(badge);
  out.iconDisabled = snap(icon);
  // R4(计划 26-10-16-0214 S6): 四态图标外框 + 徽标文本仅「发现失败」态非空(平时零遮挡)
  const iconCfgs = [
    ['unconfigured', { instances: [], discoveryAddress: '' }],
    ['ok', { instances: [{ endpoint: A }], discoveryAddress: 'http://127.0.0.1:18788', instanceHealth: { [A]: { ok: true } } }],
    ['reconnecting', { instances: [{ endpoint: A }], discoveryAddress: 'http://127.0.0.1:18788', instanceHealth: {}, lastDiscovery: { ok: false, answered: true } }],
    ['discoveryFailed', { instances: [{ endpoint: A }], discoveryAddress: 'http://127.0.0.1:18788', instanceHealth: {}, lastDiscovery: { ok: false, answered: false } }],
  ];
  out.iconStates = [];
  for (const [st, cfg] of iconCfgs) {
    Object.assign(store, { enabled: true }, cfg);
    await sandbox.refreshBadge();
    out.iconStates.push({ state: st, text: badge.text, color: badge.color, icon: snap(icon), title: badge.title });
  }
  out.hasOnClicked = typeof onClicked === 'function';
  if (onClicked) await onClicked();
  out.opened = opened;
  process.stdout.write(JSON.stringify(out));
})();
"""

_SELFHEAL_TRACE: dict = {}


def selfheal_trace() -> dict:
    """跑一次 node 拿自愈场景的全部断言点(缓存: 多条用例共用同一次 node 运行)"""
    if _SELFHEAL_TRACE:
        return _SELFHEAL_TRACE
    node = _node()
    if not node:
        return {}
    proc = _run_node(
        [node, "-e", _NODE_RUN_SELFHEAL,
         str(BACKGROUND_JS),
         str(NORMALIZE_JS),
         str(DISCOVERY_JS),
         str(SITE_CAPS_JS)]
    )
    assert proc.returncode == 0, f"node 跑 background.js 的自愈场景失败: {proc.stderr.strip()}"
    _SELFHEAL_TRACE.update(json.loads(proc.stdout))
    return _SELFHEAL_TRACE


#: 真跑 options.js::rowHealthOf(切出函数体, 不载入整页): 行级四态真值表 —— 数据源是后台落的
#: instanceHealth 台账条目(键=端点); 红(401/403)优先于 ok(401 在轮询口径里记 ok:true, 但表格必须
#: 标红); 旧台账无 state 字段按 C2 降级(ok->绿, 否则橙), 无迁移脚本。
_NODE_RUN_ROW_HEALTH = """
const fs = require('fs');
function grab(src, name) {
  const i = src.indexOf('function ' + name + '(');
  if (i < 0) throw new Error('未找到函数 ' + name);
  let depth = 0, seen = false;
  for (let k = i; k < src.length; k += 1) {
    const ch = src[k];
    if (ch === '{') { depth += 1; seen = true; }
    else if (ch === '}') { depth -= 1; if (seen && depth === 0) return src.slice(i, k + 1); }
  }
  throw new Error('函数体花括号不配平: ' + name);
}
const fn = new Function(grab(fs.readFileSync(process.argv[1], 'utf8'), 'rowHealthOf') + '\\nreturn rowHealthOf;')();
const cases = [
  ['null', null],
  ['empty', {}],
  ['ok', { ok: true }],
  ['ok-state-ok', { ok: true, state: 'ok' }],
  ['bad-401-oktrue', { ok: true, state: '401' }],
  ['bad-403-oktrue', { ok: true, state: '403' }],
  ['bad-401-okfalse', { ok: false, state: '401' }],
  ['bad-403-okfalse', { ok: false, state: '403' }],
  ['warn-legacy-no-state', { ok: false }],
  ['warn-down', { ok: false, state: 'down' }],
  ['warn-http', { ok: false, state: 'http' }],
  ['warn-bad-endpoint', { ok: false, state: 'bad-endpoint' }],
  ['warn-streak1', { ok: false, failStreak: 1 }],
  ['warn-streak2', { ok: false, failStreak: 2 }],
  ['warn-streak5-down', { ok: false, failStreak: 5, state: 'down' }],
];
process.stdout.write(JSON.stringify(cases.map(([k, h]) => ({ k, out: fn(h) }))));
"""

#: 真跑 background.js 的 probe-all 消息: 三实例各一(200 / 连不上 / 401), 逐实例只读探测,
#: 结论经 noteInstanceHealth 落台账 —— 实例表状态列的单一数据源(C1 单一写入口)。
_NODE_RUN_PROBE_ALL = """
const fs = require('fs');
const vm = require('vm');
const noop = { addListener() {} };
const A = 'http://127.0.0.1:9001';   // 200 无任务 => ok
const B = 'http://127.0.0.1:9002';   // 连不上 => down
const C = 'http://127.0.0.1:9003';   // 401 => ok:true + state:'401'(端点有应答, 行级红判据源)
const store = {
  enabled: true, logLevel: 'info', discoveryAddress: '',
  instances: [
    { name: 'a', endpoint: A, token: 't1' },
    { name: 'b', endpoint: B, token: 't2' },
    { name: 'c', endpoint: C, token: 't3' },
  ],
};
let onMessageFn = null;
const chrome = {
  alarms: { create() {}, onAlarm: noop },
  runtime: {
    onInstalled: noop, onStartup: noop,
    onMessage: { addListener: (fn) => { onMessageFn = fn; } },
    openOptionsPage: () => Promise.resolve(),
  },
  permissions: { onAdded: noop },
  action: {
    onClicked: { addListener() {} },
    setBadgeText: () => Promise.resolve(),
    setBadgeBackgroundColor: () => Promise.resolve(),
    setTitle: () => Promise.resolve(),
    setIcon: () => Promise.resolve(),
  },
  storage: { onChanged: noop, local: {
    get: (defaults) => { const out = {}; for (const k of Object.keys(defaults || {})) out[k] = (k in store) ? store[k] : defaults[k]; return Promise.resolve(out); },
    set: (obj) => { Object.assign(store, obj); return Promise.resolve(); },
  } },
};
const sandbox = { chrome, importScripts: () => {}, console, setTimeout, clearTimeout, Date, Promise, JSON, URL,
  fetch: async (url) => {
    const u = String(url);
    if (u.startsWith(A)) return { ok: true, status: 200, json: async () => ({ tasks: [], next_poll_s: 60 }) };
    if (u.startsWith(B)) throw new TypeError('Failed to fetch');
    if (u.startsWith(C)) return { ok: false, status: 401, json: async () => ({}) };
    throw new Error('unexpected fetch: ' + u);
  } };
vm.createContext(sandbox);
vm.runInContext(fs.readFileSync(process.argv[2], 'utf8'), sandbox);   // normalize.js
vm.runInContext(fs.readFileSync(process.argv[3], 'utf8'), sandbox);   // discovery.js
vm.runInContext(fs.readFileSync(process.argv[4], 'utf8'), sandbox);   // site-caps.js
vm.runInContext(fs.readFileSync(process.argv[1], 'utf8'), sandbox);   // background.js
(async () => {
  let resp = null;
  const sendResponse = (r) => { resp = r; };
  if (!onMessageFn) throw new Error('background.js 没注册 onMessage');
  onMessageFn({ type: 'probe-all' }, {}, sendResponse);
  for (let i = 0; i < 400 && resp === null; i += 1) await new Promise((r) => setTimeout(r, 5));
  process.stdout.write(JSON.stringify({ resp, health: store.instanceHealth || {} }));
})();
"""


def _js_func_body(js: str, name: str) -> str:
    """切出 `function name(...) { ... }` 的函数体(花括号配平; 模板串里的 ${} 自带配平)"""
    i = js.index(f"function {name}(")
    start = js.index("{", i)
    depth = 0
    for k in range(start, len(js)):
        if js[k] == "{":
            depth += 1
        elif js[k] == "}":
            depth -= 1
            if depth == 0:
                return js[start:k + 1]
    raise AssertionError(f"函数 {name} 花括号不配平")


def _js_string_literals(js: str) -> list:
    """JS 字符串字面量(单引号/双引号/反引号), 先剥注释 —— 反向断言只钉用户可见串, 不误伤历史注释"""
    body = re.sub(r"/\*.*?\*/", "", js, flags=re.S)
    body = re.sub(r"(?<![:\\])//[^\n]*", "", body)  # (?<!:) 放过 http:// 这类 URL
    return re.findall(r"'[^'\n]*'|\"[^\"\n]*\"|`[^`\n]*`", body)


#: 真跑 background.js::badgeIconOf(切出函数体): 四态 -> {16,32} 图标路径映射(R4 路径 A)。
_NODE_RUN_BADGE_ICON = """
const fs = require('fs');
function grab(src, name) {
  const i = src.indexOf('function ' + name + '(');
  if (i < 0) throw new Error('未找到函数 ' + name);
  let depth = 0, seen = false;
  for (let k = i; k < src.length; k += 1) {
    const ch = src[k];
    if (ch === '{') { depth += 1; seen = true; }
    else if (ch === '}') { depth -= 1; if (seen && depth === 0) return src.slice(i, k + 1); }
  }
  throw new Error('函数体花括号不配平: ' + name);
}
const src = fs.readFileSync(process.argv[1], 'utf8');
const iconDecl = src.indexOf('const BADGE_ICON = {');
const iconBlock = src.slice(iconDecl, src.indexOf('};', iconDecl) + 2);
const fn = new Function(iconBlock + '\\n' + grab(src, 'badgeIconOf') + '\\nreturn badgeIconOf;')();
process.stdout.write(JSON.stringify(['unconfigured', 'ok', 'reconnecting', 'discoveryFailed'].map((s) => [s, fn(s)])));
"""

#: 跨层机械比对(计划 26-10-15-2357 S6 + 档案「机械比对缺口」): 徽标态(background.js::badgeStateOf)与
#: 顶部总览态(options.js::connStateOf)是**同一条判据的两个展示面** —— 两份实现分头演化就会出现
#: 「徽标报警但页面说正常」这类最危险的静默漂移(用户最怕的正是这个)。这里把两个函数体各自从文件里
#: **切出来真跑**同一张真值表逐输入比对; 另钉四态键集(BADGE vs CONN_STATE_TEXT)与徽标图例文案同源。
_NODE_RUN_CROSS_LAYER_STATE = """
const fs = require('fs');
function grab(src, name) {
  const i = src.indexOf('function ' + name + '(');
  if (i < 0) throw new Error('未找到函数 ' + name);
  let depth = 0;
  let seen = false;
  for (let k = i; k < src.length; k += 1) {
    const ch = src[k];
    if (ch === '{') { depth += 1; seen = true; }
    else if (ch === '}') { depth -= 1; if (seen && depth === 0) return src.slice(i, k + 1); }
  }
  throw new Error('函数体花括号不配平: ' + name);
}
function objKeys(src, name) {
  const i = src.indexOf('const ' + name + ' = {');
  if (i < 0) throw new Error('未找到常量 ' + name);
  const body = src.slice(i, src.indexOf('};', i));
  return (body.match(/^\\s*([A-Za-z_][\\w]*):/gm) || []).map((s) => s.trim().replace(':', ''));
}
const bg = fs.readFileSync(process.argv[1], 'utf8');
const opt = fs.readFileSync(process.argv[2], 'utf8');
const badgeFn = new Function(grab(bg, 'badgeStateOf') + '\\nreturn badgeStateOf;')();
const connFn = new Function(grab(opt, 'connStateOf') + '\\nreturn connStateOf;')();
const A = 'http://127.0.0.1:9001';
const cases = [
  { instances: [], discoveryAddress: '' },
  { instances: [], discoveryAddress: 'http://127.0.0.1:18788' },
  { instances: [{ endpoint: A }], discoveryAddress: '', instanceHealth: { [A]: { ok: true } } },
  {
    instances: [{ endpoint: A }], discoveryAddress: 'http://127.0.0.1:18788',
    instanceHealth: { [A]: { ok: false } }, lastDiscovery: { ok: false, answered: false }
  },
  {
    instances: [{ endpoint: A }], discoveryAddress: 'http://127.0.0.1:18788',
    instanceHealth: {}, lastDiscovery: { ok: false, answered: true }
  },
  { instances: [{ endpoint: A }], discoveryAddress: '', instanceHealth: {}, lastDiscovery: null },
  {
    instances: [{ endpoint: A }], discoveryAddress: 'http://127.0.0.1:18788',
    instanceHealth: { [A]: { ok: true } }, lastDiscovery: { ok: false, answered: false }
  },
  // 26-10-29-0147 D5: 通道通 + 站点未授权 ⇒ noSitePermission(必须压过 ok, 否则「连接正常」是假话)
  {
    instances: [{ endpoint: A }], discoveryAddress: '',
    instanceHealth: { [A]: { ok: true } },
    sitePerms: { 'https://pt.example.com': { granted: false, checkedAt: 1 } }
  },
  // 反向对照: 同样有未授权记录但端点不通 ⇒ 仍是重连中(不许拿站点未授权盖住连接故障)
  {
    instances: [{ endpoint: A }], discoveryAddress: '',
    instanceHealth: { [A]: { ok: false } },
    sitePerms: { 'https://pt.example.com': { granted: false, checkedAt: 1 } }
  },
  // 全部已授权 ⇒ 回到 ok
  {
    instances: [{ endpoint: A }], discoveryAddress: '',
    instanceHealth: { [A]: { ok: true } },
    sitePerms: { 'https://pt.example.com': { granted: true, checkedAt: 1 } }
  },
];
const badgeBlock = bg.slice(bg.indexOf('const BADGE = {'), bg.indexOf('function badgeStateOf'));
const labels = (badgeBlock.match(/label: '([^']*)'/g) || []).map((s) => s.replace("label: '", '').replace("'", ''));
process.stdout.write(JSON.stringify({
  badgeOut: cases.map((c) => badgeFn(c)),
  connOut: cases.map((c) => connFn(c)),
  badgeKeys: objKeys(bg, 'BADGE'),
  connKeys: objKeys(opt, 'CONN_STATE_TEXT'),
  labels: labels,
}));
"""

#: 一次跑完: ① 两份 originGranted(background / options)对同一张真值表必须一致;
#: ② runTask 三场景 —— 未授权(不发请求, kind=no-permission) / 已授权但 fetch 抛 Failed to fetch
#: (kind=network) / 已授权且成功(ok)。
_NODE_RUN_SITE_PERM = """
const fs = require('fs');
const vm = require('vm');
function grab(src, name) {
  const i = src.indexOf('function ' + name + '(');
  if (i < 0) throw new Error('未找到函数 ' + name);
  let depth = 0, seen = false;
  for (let k = i; k < src.length; k += 1) {
    const ch = src[k];
    if (ch === '{') { depth += 1; seen = true; }
    else if (ch === '}') { depth -= 1; if (seen && depth === 0) return src.slice(i, k + 1); }
  }
  throw new Error('函数体花括号不配平: ' + name);
}
const bg = fs.readFileSync(process.argv[1], 'utf8');
const opt = fs.readFileSync(process.argv[2], 'utf8');
const mk = (src) => new Function(
  grab(src, 'splitPattern') + '\\n' + grab(src, 'originGranted') + '\\nreturn originGranted;'
)();
const bgFn = mk(bg);
const optFn = mk(opt);

// 真值表: [origin, 已授予模式, 期望]
const CASES = [
  ['https://pt.example.com', ['https://pt.example.com/*'], true],
  ['https://pt.example.com', ['http://pt.example.com/*'], false],
  ['https://pt.example.com', ['https://*.example.com/*'], true],
  ['https://example.com', ['https://*.example.com/*'], false],
  ['https://pt.example.com', ['https://*/*'], true],
  ['https://pt.example.com', [], false],
  ['https://pt.example.com', ['<all_urls>'], false],
  ['https://pt.example.com', ['http://127.0.0.1/*'], false],
  ['https://pt.example.com', ['https://pt.example.com'], true],
];

const noop = { addListener() {} };
const PAGE = '<html><body><table><tr><td>1</td></tr></table></body></html>';
const PAGE_URL = 'https://pt.example.com/myhr.php?hrtype=A';
const store = {};
let fetches = 0;
let grantedOrigins = [];
let failFetch = false;
const chrome = {
  alarms: { create: () => {}, onAlarm: noop },
  runtime: { onInstalled: noop, onStartup: noop, onMessage: noop, onSuspend: noop },
  permissions: {
    onAdded: noop, onRemoved: noop,
    getAll: async () => ({ origins: grantedOrigins.slice() }),
  },
  storage: {
    onChanged: noop,
    local: {
      get: (defaults) => {
        const out = {};
        for (const key of Object.keys(defaults || {})) out[key] = (key in store) ? store[key] : defaults[key];
        return Promise.resolve(out);
      },
      set: (obj) => { Object.assign(store, obj); return Promise.resolve(); },
    },
  },
  action: {
    setBadgeText: async () => {}, setBadgeBackgroundColor: async () => {},
    setIcon: async () => {}, setTitle: async () => {}, onClicked: noop,
  },
  scripting: { executeScript: async () => [{ result: PAGE }] },
  windows: {
    create: async () => ({ id: 1, tabs: [{ id: 2 }] }),
    get: async () => ({ id: 1 }), getLastFocused: async () => ({ id: 1 }),
    update: async () => ({}), remove: async () => {},
  },
  tabs: { create: async () => ({ id: 2, windowId: 1 }), get: async () => ({ id: 2, status: 'complete' }), remove: async () => {} },
};
const sandbox = {
  chrome, importScripts: () => {}, console, setTimeout, clearTimeout, Date, Promise, JSON, URL,
  btoa, TextDecoder, TextEncoder,
  fetch: async () => {
    fetches += 1;
    if (failFetch) throw new TypeError('Failed to fetch');
    return {
      ok: true, status: 200, headers: { get: () => 'text/html' },
      text: async () => PAGE, arrayBuffer: async () => new ArrayBuffer(8), json: async () => ({}),
    };
  },
};
vm.createContext(sandbox);
vm.runInContext(fs.readFileSync(process.argv[3], 'utf8'), sandbox);   // discovery.js
vm.runInContext(fs.readFileSync(process.argv[4], 'utf8'), sandbox);   // site-caps.js
vm.runInContext(bg, sandbox);                                        // background.js

async function run(label, origins, fail) {
  grantedOrigins = origins; failFetch = Boolean(fail); fetches = 0;
  const got = await sandbox.runTask({ id: label, kind: 'page', url: PAGE_URL });
  return { label: label, payload: got.payload, fetches: fetches, sitePerms: JSON.parse(JSON.stringify(store.sitePerms || {})) };
}
(async () => {
  const tasks = [];
  tasks.push(await run('no-perm', [], false));                                  // 未授权: 一个字节都不发
  tasks.push(await run('net-fail', ['https://pt.example.com/*'], true));        // 已授权但网络层失败
  tasks.push(await run('ok', ['https://pt.example.com/*'], false));             // 已授权且成功
  process.stdout.write(JSON.stringify({
    cases: CASES,
    bgOut: CASES.map((c) => bgFn(c[0], c[1])),
    optOut: CASES.map((c) => optFn(c[0], c[1])),
    tasks: tasks,
    sitePerms: store.sitePerms || {},
  }));
})();
"""

_SITE_PERM_TRACE: dict = {}


def site_perm_trace() -> dict:
    """跑一次 node 拿真值表 + runTask 三场景(缓存: 两个用例共用同一次 node 运行)"""
    if _SITE_PERM_TRACE:
        return _SITE_PERM_TRACE
    node = _node()
    if not node:
        return {}
    proc = _run_node(
        [node, "-e", _NODE_RUN_SITE_PERM,
         str(BACKGROUND_JS),
         str(OPTIONS_JS),
         str(DISCOVERY_JS),
         str(SITE_CAPS_JS)]
    )
    assert proc.returncode == 0, f"node 跑站点权限场景失败: {proc.stderr.strip()}"
    _SITE_PERM_TRACE.update(json.loads(proc.stdout))
    return _SITE_PERM_TRACE
