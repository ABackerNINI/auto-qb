"""test_web_api_core 测试计划: WEB UI 核心 API 读写

## 测试计划(每个测试函数一条)
- test_api_webui_flags_endpoint: R2 功能旗标端点(计划 26-10-02-1955 W1) —— 开/关读实时配置 + 未鉴权 401; qb_traffic_enabled 旗标(P5a)段缺省/关 = False, 开 = True; relocate_enabled 旗标(计划 26-11-07-1300 R6a)同口径透传 relocate.enabled
- test_lifecycle_wait_until_started_and_stop_timeout: 生命周期等待/停止三出口(P0-T0.5)
- test_api_t_skip_check_gated_by_config: R2 skip-check 端点 gate —— 配置关 403(detail 注明 web.skip_check_menu)/ 开 200 入队, 403 不投递命令
- test_api_status_and_groups: 状态与分组快照读取(经注入的 manager; status 含 version)
- test_api_expr_eval_endpoint: 表达式试算端点(校验-only / 按种子求值 + 中间值 / 名字错误 / 种子不存在)
- test_static_assets_disable_heuristic_cache: 缓存分流(D6/P2-2) —— 裸路径 no-cache / 带当前 v immutable, /api 与 HTML 不受影响, HEAD 保留 Content-Length; 防升级后仍加载旧前端(UI 目录化路径: atlas/prism/shared/console/flux)
- test_static_cache_split_four_states: 缓存分流四态(D6) —— 当前 v immutable / 裸 no-cache / 过期 v no-cache / HTML 带 v 仍 no-cache(过期 v 必须可重验, 不变量 3)
- test_bootjs_withv_url_append: boot.js withV URL 追加(D4/P2-2, node 行为电池) —— 无 query 加 ?v= / 已有 query 加 &v= / fetch·preload·script src 三处同形同 V / 缺 window.AQB_V 与无 window 优雅退化
- test_static_cache_upgrade_invalidation: 升级演练(D6/不变量 3) —— 换 V 重建 app 后旧 URL 不再 immutable、新 URL immutable; 四套 HTML 与 boot.js 静态守阵无硬编码 V
- test_ui_root_and_legacy_newui_redirect: / -> 307 上次使用的 UI(autoqb_ui 皮肤 cookie, 未记录/失效回落星图); 旧 /newui/* 书签 -> 307 /prism/*
- test_frontend_ui_skin_cookie_persisted: boot.js 必须把当前 UI 写进 autoqb_ui cookie —— 根路径「记住上次 UI」的数据源(307 在服务端裁决, cookie 是唯一读得到的载体)
- test_static_version_hash_stability: 静态树内容哈希 V(D5) —— 同内容恒等 / 改或增任一纳入文件即变 / 白名单外 .pyc/.log 不参与(抖动的 V 永远缓存未命中, 恒定的 V 升级后继续吃旧资源)
- test_static_version_token_head_shape: 四套 index.html head 令牌形态(D4 静态守阵读盘) —— 所有 head script/link 都带 ?v=__AQB_V__ 且注入 window.AQB_V, 令牌数与资源数相等(漏一个 = 那份 JS/CSS 仍吃旧缓存且无报错)
- test_static_version_token_response_replacement: HTML 版本令牌响应时替换(D4/D6) —— 四套皮肤目录/直取两种 URL 形态都无残留、替换为真实 V、仍 no-cache; 无令牌的 CSS/模板分片逐字节零副作用
"""
import os
import re

from auto_qb import __version__
from auto_qb.webui.server.static_version import compute_static_version

from webui_helpers import STATIC_ROOT, _UI_ALL, _enable_qb_traffic

IMMUTABLE = "public, max-age=31536000, immutable"

# node 行为电池(P2-2/D4): 真加载 boot.js, 钉 withV 三处 URL 同形 + query 形态 + 缺失退化。
# 与 P1 并发电池同款桩法(window/document/fetch/setTimeout 全桩, 不碰真实网络); 本探针自己
# 提供 window.AQB_V —— P1 并发电池不提供, 故那边仍走「字面量」退化分支, 两电池互不干扰。
_NODE_BOOT_WITHV_PROBE = r"""
const fs = require("fs");
const checks = [];
const ok = (name, cond) => checks.push([name, !!cond]);
const bootSrc = fs.readFileSync(process.argv[1], "utf8");
const V = "abc123def4567890";
const flush = async () => { for (let i = 0; i < 30; i++) await null; };
const resp = () => ({ ok: true, status: 200, text: async () => "X" });
const mf = {
  parts: [
    { src: "/shared/tpl/a.html", into: "app" },
    { src: "/shared/tpl/b.html?x=1", into: "body" },
  ],
  scripts: ["/shared/s0.js", "/shared/s1.js?mode=2"],
};

function makeEnv(win) {
  const calls = [];
  const pending = [];
  if (win === null) delete global.window; else global.window = win;
  global.setTimeout = () => 1;
  global.clearTimeout = () => {};
  const appEl = {
    innerHTML: "",
    querySelector: () => null,
    querySelectorAll: () => [],
    insertAdjacentHTML: () => {},
  };
  const mfEl = { textContent: JSON.stringify(mf) };
  const links = [];
  const scripts = [];
  global.document = {
    get cookie() { return ""; },
    set cookie(v) {},
    getElementById: (id) => (id === "app" ? appEl : mfEl),
    body: { textContent: "", insertAdjacentHTML: () => {} },
    createElement: (tag) => (tag === "link"
      ? { tag: tag, rel: "", as: "", href: "", onload: null, onerror: null }
      : { tag: tag, src: "", async: true, onerror: null }),
    head: { appendChild: (el) => { (el.tag === "link" ? links : scripts).push(el); } },
  };
  global.location = { pathname: "/atlas/" };
  global.fetch = (src) => { calls.push(src); return new Promise((res) => pending.push({ src: src, res: res })); };
  return { calls: calls, pending: pending, links: links, scripts: scripts };
}

(async () => {
  // 1 有 V: 三处都追加同一个 V, 已有 query 用 &v=
  const env = makeEnv({ AQB_V: V });
  eval(bootSrc);
  ok("分片 fetch 无 query -> ?v=V", env.calls[0] === "/shared/tpl/a.html?v=" + V);
  ok("分片 fetch 已有 query -> &v=V", env.calls[1] === "/shared/tpl/b.html?x=1&v=" + V);
  env.pending.forEach((p) => p.res(resp()));
  await flush();
  ok("preload href 无 query -> ?v=V", env.links[0].href === "/shared/s0.js?v=" + V);
  ok("preload href 已有 query -> &v=V", env.links[1].href === "/shared/s1.js?mode=2&v=" + V);
  env.links.forEach((l) => l.onload());
  await flush();
  ok("script src 与 preload href 逐字同形(预取可复用)",
     env.scripts.length === 2 && env.scripts.every((s, i) => s.src === env.links[i].href));
  ok("fetch / preload / script 三处同一个 V",
     env.calls.every((u) => u.indexOf("v=" + V) >= 0)
     && env.scripts.every((s) => s.src.indexOf("v=" + V) >= 0));

  // 2 window 存在但无 AQB_V: 优雅退化为清单字面量, 不崩
  const env2 = makeEnv({});
  eval(bootSrc);
  ok("缺 AQB_V 时 fetch 退化为字面量",
     env2.calls[0] === "/shared/tpl/a.html" && env2.calls[1] === "/shared/tpl/b.html?x=1");
  env2.pending.forEach((p) => p.res(resp()));
  await flush();
  env2.links.forEach((l) => l.onload());
  await flush();
  ok("缺 AQB_V 时 preload/script 仍用字面量",
     env2.scripts.every((s, i) => s.src === mf.scripts[i] && s.src.indexOf("?v=") < 0));

  // 3 完全无 window(直接开文件/诊断桩/node): typeof 守卫不抛, 仍退化
  const env3 = makeEnv(null);
  eval(bootSrc);
  ok("无 window 时不抛且退化为字面量",
     typeof window === "undefined"
     && env3.calls[0] === "/shared/tpl/a.html" && env3.calls[1] === "/shared/tpl/b.html?x=1");
  env3.pending.forEach((p) => p.res(resp()));
  await flush();

  console.log(JSON.stringify({ ok: checks.filter((c) => c[1]).length, total: checks.length,
    failed: checks.filter((c) => !c[1]).map((c) => c[0]) }));
})();
"""


def test_api_webui_flags_endpoint(web_env):
    """R2 功能旗标端点(计划 26-10-02-1955 W1): 开/关读**实时配置** + 未鉴权 401

    FakeConfig 测试侧默认 skip_check_menu=True(helpers, 供既有 skip-check 用例直通);
    关闭用例实例级置 False(深拷贝, 不跨测试泄漏) —— 端点必须现取 manager.config 引用,
    不按值持有旧 Config(hot-reload-held-config 坑)。
    qb_traffic_enabled(P5a, plan 26-10-03-0946 §07): 段缺省 None / enabled=false 均 False,
    _enable_qb_traffic 置段 enabled=True 后即时翻真(读实时配置口径)。
    relocate_enabled(计划 26-11-07-1300 R6a): relocate.enabled 原样透传, FakeConfig 用真
    RelocateConfig 模型(缺省 enabled=False 保守默认), 置 True/False 即时翻真(同口径)。
    """
    mgr, client = web_env
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    assert client.get("/api/webui/flags", headers=auth).json() == {
        "skip_check_menu": True,
        "qb_traffic_enabled": False,  # FakeConfig 默认 qb_traffic=None(未启用)
        "relocate_enabled": False,  # FakeConfig 默认 relocate=RelocateConfig()(enabled=False)
        "ctx_menu": None,  # FakeConfig 默认无布局(计划 26-10-20-0024 W1: None = 默认菜单)
    }
    mgr.config.web.skip_check_menu = False
    assert client.get("/api/webui/flags", headers=auth).json() == {
        "skip_check_menu": False,
        "qb_traffic_enabled": False,
        "relocate_enabled": False,
        "ctx_menu": None,
    }
    # ctx_menu 原样下发(实时配置): 置布局即回布局, 与 skip_check_menu 同口径现取现真
    mgr.config.web.ctx_menu = {"group": {"order": ["resume", "sep:d1"], "hidden": ["export"]}}
    assert client.get("/api/webui/flags", headers=auth).json()["ctx_menu"] == {
        "group": {
            "order": ["resume", "sep:d1"],
            "hidden": ["export"]
        }
    }
    _enable_qb_traffic(mgr, enabled=True)
    assert client.get("/api/webui/flags", headers=auth).json()["qb_traffic_enabled"] is True
    _enable_qb_traffic(mgr, enabled=False)
    assert client.get("/api/webui/flags", headers=auth).json()["qb_traffic_enabled"] is False
    # relocate_enabled(计划 26-11-07-1300 R6a): relocate.enabled 翻转即时生效(读实时配置口径)
    mgr.config.relocate.enabled = True
    assert client.get("/api/webui/flags", headers=auth).json()["relocate_enabled"] is True
    mgr.config.relocate.enabled = False
    assert client.get("/api/webui/flags", headers=auth).json()["relocate_enabled"] is False
    assert client.get("/api/webui/flags").status_code == 401


def test_api_t_skip_check_gated_by_config(web_env):
    """R2 skip-check 端点 gate(D2=是 · fail-closed): 配置关 403(detail 注明键名) / 配置开 200 入队

    gate 读实时配置 —— 同一 client 内翻转配置键即时生效; 403 时不得投递命令。
    rule 源跳检回归哨: test_ops.py 全部零改动全绿。
    """
    mgr, client = web_env
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    mgr.config.web.skip_check_menu = False
    resp = client.post("/api/torrents/HA/skip-check", headers=auth)
    assert resp.status_code == 403, resp.text
    assert "web.skip_check_menu" in resp.json()["detail"], "403 detail 必须注明配置键名"
    assert mgr.web.commands.empty(), "配置关时不得投递命令"
    mgr.config.web.skip_check_menu = True
    resp = client.post("/api/torrents/HA/skip-check", headers=auth)
    assert resp.status_code == 200, resp.text
    cmd, payload = mgr.web.commands.get_nowait()
    assert cmd == "skip_check_torrent" and payload["hash"] == "HA"


def test_api_status_and_groups(web_env):
    """状态与分组快照读取: 徽章数据/组名/成员 hash 引用齐全(P-02 二期); status 携带版本号(顶栏展示)"""
    mgr, client = web_env
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    status = client.get("/api/status", headers=auth).json()
    assert status["connected"] is True and status["torrents"] == 2
    assert status["version"] == __version__, "status 应透出包版本号"
    data = client.get("/api/groups", headers=auth).json()
    assert len(data["groups"]) == 1
    g = data["groups"][0]
    assert g["name"] == "Show" and g["count"] == 2 and g["upspeed"] == 2048
    # P-02 二期(hash 引用式): 组行 members = hash 字符串数组(成员明细经 memberByHash 索引还原)
    assert g["members"] == ["HA", "HB"]


def test_api_expr_eval_endpoint(web_env):
    """表达式试算端点 /api/expr/eval: 校验-only 与"按种子求值 + 中间值"两条路径

    前端「试算」按钮靠它: 写错表达式不用等到保存才知道; 填了种子 hash 还能看到
    每个取值到底取到了什么(中间值), 这是排查"条件为什么不匹配"最有用的一条信息。
    """
    mgr, client = web_env
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    # 替身 store 默认 get() 恒 None: 塞一条合成种子进去(试算要读它的字段)
    from auto_qb.torrents import TorrentRecord

    rec = TorrentRecord(hash="h1", name="Show 1", size=5 * 1024**3, state="uploading")
    mgr.store.get = lambda h: rec if h == "h1" else None
    h = "h1"

    ok = client.post("/api/expr/eval", json={"text": "(tor.size >= 1GiB)"}, headers=auth).json()
    assert ok["ok"] is True and ok["used"] == ["tor.size"] and ok["value"] is None

    bad = client.post("/api/expr/eval", json={"text": "tor.nope > 1"}, headers=auth).json()
    assert bad["ok"] is False and "未知取值" in bad["error"]

    val = client.post(
        "/api/expr/eval", json={
            "text": "(tor.size >= 1GiB) and (tor.name ~ \"Show\")",
            "hash": h
        }, headers=auth
    ).json()
    assert val["ok"] is True and isinstance(val["value"], bool)
    assert [t["name"] for t in val["trace"]] == ["tor.size", "tor.name"]

    missing = client.post("/api/expr/eval", json={"text": "(tor.size >= 1GiB)", "hash": "nope"}, headers=auth).json()
    assert missing["ok"] is False and "找不到种子" in missing["error"]


def test_static_assets_disable_heuristic_cache(web_env):
    """静态资源缓存分流(D6/P2-2): 裸路径 no-cache, 带当前 v immutable; /api 与 HTML 不受影响

    症状: 升级程序后仍加载旧前端("改了但没变")。裸路径仍 no-cache(每次 ETag 重验); 装配端点
    (head/boot.js)带上的当前 v 资源走 immutable 长缓存, 不再逐请求重验。HTML 自身永远 no-cache
    (D6 —— 它是版本清单的载体, 长缓存会让新 V 永远下不到浏览器)。UI 目录化路径:
    atlas=星图(旧) / prism=棱镜(新) / console / flux / shared=公共逻辑层。
    """
    mgr, client = web_env
    v = compute_static_version(STATIC_ROOT)
    html_paths = {"/atlas/", "/prism/", "/console/", "/shared/tpl/topbar.html"}
    paths = (
        "/atlas/", "/atlas/style.css", "/shared/tpl/topbar.html", "/prism/", "/shared/app.js", "/shared/boot.js",
        "/shared/vendor/vue.global.prod.js", "/console/", "/console/css/components.css"
    )
    # 1 裸路径: 无 v 可比对 -> 一律保守 no-cache
    for path in paths:
        resp = client.get(path)
        assert resp.status_code == 200, f"{path} 应可访问"
        assert resp.headers.get("cache-control") == "no-cache", f"{path} 裸路径应带 no-cache"
    # 2 带当前 v: 非 HTML 走 immutable, HTML 仍 no-cache
    for path in paths:
        url = path + ("&" if "?" in path else "?") + "v=" + v
        resp = client.get(url)
        assert resp.status_code == 200, f"{url} 应可访问"
        expect = "no-cache" if path in html_paths else IMMUTABLE
        assert resp.headers.get("cache-control") == expect, f"{url} 缓存头应为 {expect}"
    api = client.get("/api/status", headers={"Authorization": f"Bearer {mgr.web.token}"})
    assert api.headers.get("cache-control") != "no-cache", "/api 响应不应被静态策略影响"
    # HEAD 只发头不发体: 中间件若把空 body_iterator 收齐后重建响应, 会把 Content-Length 清零,
    # 破坏 HEAD 应回显与 GET 等效的长度语义 —— 必须保留原响应头(只带 no-cache)。
    head = client.head("/atlas/")
    assert head.status_code == 200, "HEAD /atlas/ 应可访问"
    assert head.content == b"", "HEAD 不应带 body"
    assert int(head.headers["content-length"]) > 0, "HEAD 的 Content-Length 不得被收空 body 的重建响应清零"
    assert head.headers.get("cache-control") == "no-cache", "HEAD 响应仍须 no-cache"


def test_static_cache_split_four_states(web_env):
    """缓存分流四态(D6): 当前 v immutable / 裸 no-cache / 过期 v no-cache / HTML 带 v 仍 no-cache

    升级安全的判据落在「v 与当前版本逐字相等」: 任何不等的 v(含旧版本)都不得 immutable,
    否则升级后旧 app.js 会被浏览器永久缓存(不变量 3)。HTML 即便带当前 v 也只发 no-cache ——
    HTML 是版本清单的载体, 一旦长缓存, 新 V 永远下发不到浏览器。
    另钉两条边界: 非 2xx(307 重定向/404 缺失资源)带当前 v 也不得 immutable; HEAD 带当前 v
    的静态资源仍 immutable 且保留 Content-Length。
    """
    _, client = web_env
    v = compute_static_version(STATIC_ROOT)
    stale = "0" * 16 if v != "0" * 16 else "f" * 16
    assert client.get(f"/shared/app.js?v={v}").headers["cache-control"] == IMMUTABLE
    assert client.get("/shared/app.js").headers["cache-control"] == "no-cache"
    assert client.get(f"/shared/app.js?v={stale}").headers["cache-control"] == "no-cache"
    html = client.get(f"/atlas/?v={v}")
    assert html.status_code == 200
    assert html.headers["cache-control"] == "no-cache", "HTML 带当前 v 也不得 immutable"
    # 非 2xx 带当前 v 也必须 no-cache: 带 v 的 307 若被 immutable, 换皮肤后书签会永久跳旧 UI;
    # 404 若被 immutable 则缺失资源永久占位。TestClient 默认 follow_redirects=True, 须关掉才看得到 307。
    root = client.get("/?v=" + v, follow_redirects=False)
    assert root.status_code == 307, "带当前 v 的根路径仍须 307 到上次 UI 的裁决目标"
    assert root.headers["cache-control"] == "no-cache", "307 带当前 v 不得 immutable"
    assert root.headers["location"].endswith("/"), "307 的 Location 不得被缓存分流破坏"
    legacy = client.get("/newui?v=" + v, follow_redirects=False)
    assert legacy.status_code == 307, "带当前 v 的旧书签仍须 307"
    assert legacy.headers["cache-control"] == "no-cache", "307 带当前 v 不得 immutable"
    missing = client.get("/shared/__no_such_asset__.js?v=" + v, follow_redirects=False)
    assert missing.status_code == 404, "不存在的静态路径应 404"
    assert missing.headers["cache-control"] == "no-cache", "404 带当前 v 不得 immutable"
    # HEAD 带当前 v: 缓存头在中间件 HEAD 提前 return 之前已算好, immutable 与 GET 同口径;
    # 提前 return 不做 body 重建, Content-Length 保持与 GET 等效(与 P2-a 的 HEAD 修复一致)。
    head = client.head("/shared/app.js?v=" + v)
    assert head.headers["cache-control"] == IMMUTABLE, "HEAD 带当前 v 的静态资源应 immutable"
    assert int(head.headers["content-length"]) > 0, "HEAD 的 Content-Length 不得被清空"


def test_bootjs_withv_url_append():
    """boot.js withV URL 追加(D4/P2-2): 三处同形同 V + query 两形态 + 缺失优雅退化

    withV 是分片 fetch / 脚本 preload href / 最终 script src 的公共出口 —— preload 与 script
    src 必须逐字同形, 否则预取缓存复用失效, 脚本二次请求。已有 query 用 &v=、无则 ?v=;
    window.AQB_V 缺失(或不存在的 window)时退化为清单字面量, 不崩。静态锚先钉三处都过单点,
    行为面 node 电池真跑(无 node 静默跳过, 与 P1 并发电池同口径)。
    """
    boot = os.path.join(STATIC_ROOT, "shared", "boot.js")
    src = open(boot, encoding="utf-8").read()
    # 静态锚: 定义 + 三处调用共 4 个 withV(, 两种 query 形态的字面量都在
    assert "function withV(" in src and "window.AQB_V" in src, "boot.js 缺 withV 版本单点"
    assert src.count("withV(") >= 4, "分片 fetch / preload href / script src 未全走 withV"
    assert '"&v="' in src and '"?v="' in src, "withV 未同时覆盖已有 query 与无 query 两种形态"

    import json
    import shutil
    import subprocess

    node = shutil.which("node")
    if not node:
        return
    proc = subprocess.run(
        [node, "-e", _NODE_BOOT_WITHV_PROBE, boot],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    assert proc.returncode == 0, f"boot.js withV node 电池跑挂: {proc.stderr.strip()}"
    lines = proc.stdout.strip().splitlines()
    assert lines, "boot.js withV node 电池无输出(被悬挂挂住了?)"
    report = json.loads(lines[-1])
    assert report["failed"] == [], \
        f"withV 电池 {report['ok']}/{report['total']} 过, 失败: {report['failed']}"


def test_static_cache_upgrade_invalidation(web_env, monkeypatch):
    """升级演练(D6/不变量 3): V 变化后旧 URL 不再 immutable, 新 URL 才 immutable

    版本源在挂载时算一次, 由中间件闭包持有。模拟升级 = 换掉版本源再建一个 app: 旧 V 的 URL
    必须落回 no-cache(浏览器拿 ETag 重验刷成新内容), 新 V 的 URL 才 immutable。同时静态守阵:
    四套 index.html 与 boot.js 不得出现硬编码 16 位 V —— 版本只能来自令牌 / window.AQB_V,
    否则换版本的升级演练形同虚设。
    """
    mgr, client = web_env
    v1 = compute_static_version(STATIC_ROOT)
    assert client.get(f"/shared/app.js?v={v1}").headers["cache-control"] == IMMUTABLE
    assert client.get("/shared/app.js?v=aaaaaaaaaaaaaaaa").headers["cache-control"] == "no-cache"

    from fastapi.testclient import TestClient

    from auto_qb.webui import create_app
    from auto_qb.webui.server import static_ui

    v2 = "b" * 16 if v1 != "b" * 16 else "c" * 16
    monkeypatch.setattr(static_ui, "compute_static_version", lambda _d: v2)
    upgraded = TestClient(create_app(mgr))
    assert upgraded.get(f"/shared/app.js?v={v2}").headers["cache-control"] == IMMUTABLE
    old = upgraded.get(f"/shared/app.js?v={v1}")
    assert old.status_code == 200, "旧 URL 仍须取到内容(只是不许 immutable)"
    assert old.headers["cache-control"] == "no-cache", \
        "升级后旧 V 不得 immutable —— 否则用户永久吃旧 app.js"

    for ui in _UI_ALL:
        shell = open(os.path.join(STATIC_ROOT, ui, "index.html"), encoding="utf-8").read()
        assert not re.search(r"\?v=[0-9a-f]{16}\b", shell), f"{ui} 硬编码了 16 位 V —— 升级后不会更新"
    boot = open(os.path.join(STATIC_ROOT, "shared", "boot.js"), encoding="utf-8").read()
    assert not re.search(r"\b[0-9a-f]{16}\b", boot), "boot.js 硬编码了 16 位 V —— 版本必须来自 window.AQB_V"


def test_ui_root_and_legacy_newui_redirect(web_env):
    """根路径与旧 /newui/* 重定向: / -> 上次使用的 UI(autoqb_ui 皮肤 cookie); /newui/* -> 307 /prism/*

    UI 目录化后 StaticFiles 根下无 index.html, 根路径由显式路由兜底; 默认星图, 但带皮肤 cookie
    (shared/boot.js 在每套 UI 加载时写入)时直达该 UI —— 修复「关窗口重开总回星图」(2026-09-29 用户报)。
    cookie 值双重校验: 形状合法 + static/<名>/index.html 真实存在 —— UI 改名/删除后的旧 cookie
    与路径逃逸形状一律回落星图。/newui 兼容路由保住升级前书签(子路径原样映射到 /prism/*)。
    """
    _, client = web_env
    for cookie, expect in (
        ({}, "/atlas/"),  # 未记录(首次访问/清过站点数据) -> 默认星图
        ({
            "autoqb_ui": "prism"
        }, "/prism/"),  # 上次用棱镜 -> 直达棱镜
        ({
            "autoqb_ui": "console"
        }, "/console/"),  # 上次用控制台 -> 直达控制台
        ({
            "autoqb_ui": "atlas"
        }, "/atlas/"),  # 上次用星图(显式记录)
        ({
            "autoqb_ui": "ghost"
        }, "/atlas/"),  # 目录已不存在(UI 改名/删除后的旧 cookie)
        ({
            "autoqb_ui": "../prism"
        }, "/atlas/"),  # 形状不合法(路径逃逸形状不得进重定向目标)
    ):
        # starlette 1.6 弃用逐请求 cookies=<...>(审计 L8, b 类: 测试代码用了弃用 API), 按官方迁移路径
        # 改设到 client 实例; 每档先清空再写入, 保持"该次请求只带本档 cookie"的独立语义
        # (307 应答不带 Set-Cookie, 不存在串档; 清空是防未来路由加 Set-Cookie 后跨档污染)。
        client.cookies.clear()
        client.cookies.update(cookie)
        root = client.get("/", follow_redirects=False)
        assert root.status_code == 307, f"cookie={cookie} 根路径应 307 重定向"
        assert root.headers["location"] == expect, f"cookie={cookie} 应重定向到 {expect}"
    for old, new in (
        ("/newui", "/prism/"), ("/newui/", "/prism/"), ("/newui/css/tokens.css", "/prism/css/tokens.css"),
        ("/newui/js/theme.js", "/prism/js/theme.js")
    ):
        resp = client.get(old, follow_redirects=False)
        assert resp.status_code == 307, f"{old} 应 307 重定向"
        assert resp.headers["location"] == new, f"{old} 应映射到 {new}"


def test_frontend_ui_skin_cookie_persisted():
    """boot.js 必须把当前 UI 写进 autoqb_ui cookie —— 根路径「记住上次 UI」的数据源(2026-09-29 用户报)

    根路径 307 由服务端在收到请求那一刻裁决, localStorage 服务端读不到, cookie 是唯一可行载体;
    四套 UI 共用 boot.js = 唯一写入口(打开即记录, 切换菜单无需单独埋点)。服务端取值校验
    (形状 + 目录存在性)见 test_ui_root_and_legacy_newui_redirect。
    """
    boot = open(os.path.join(STATIC_ROOT, "shared", "boot.js"), encoding="utf-8").read()
    assert '"autoqb_ui="' in boot, "boot.js 未写 autoqb_ui cookie —— 关窗重开根路径会回到默认星图"
    assert "location.pathname.split" in boot, "boot.js 未从 URL 路径段判定当前 UI"
    assert "Max-Age=" in boot, "皮肤 cookie 必须带有效期(会话 cookie 关窗即丢, 等于没修)"
    assert "Path=/" in boot, "皮肤 cookie 必须 Path=/(根路径 / 要能读到)"


def test_lifecycle_wait_until_started_and_stop_timeout(monkeypatch):
    """WEB 服务生命周期辅助(P0-T0.5): 等待就绪的三出口(就绪/线程死/超时) + 停止超时仍放行重启"""
    import threading
    import time
    from types import SimpleNamespace

    from auto_qb.webui.server import lifecycle

    dead = threading.Thread(target=lambda: None)  # 未启动: is_alive() False
    handle_dead = SimpleNamespace(started=False, thread=dead)
    assert lifecycle._wait_until_started(handle_dead, 1.0) is False, "线程提前退出(启动失败) -> False"

    # !线程必须**一直活着**才走得到 deadline 分支: 早先 target 是 lambda: None, 线程秒退,
    #   于是「超时」断言实际测的是 is_alive()=False 那条(假绿, 155 行从未执行)
    hold = threading.Event()
    alive = threading.Thread(target=hold.wait, daemon=True)
    alive.start()
    try:
        assert alive.is_alive(), "前提: 线程活着(否则测的不是超时分支)"
        handle_alive = SimpleNamespace(started=False, thread=alive)
        t0 = time.monotonic()
        assert lifecycle._wait_until_started(handle_alive, 0.1) is False, "超时 -> False(有界等待)"
        elapsed = time.monotonic() - t0
        assert 0.05 <= elapsed < 2.0, f"必须真等满窗口再放弃, 实得 {elapsed:.3f}s"
        handle_ok = SimpleNamespace(started=True, thread=alive)
        assert lifecycle._wait_until_started(handle_ok, 0.1) is True, "已就绪 -> True"
    finally:
        hold.set()
        alive.join(timeout=1.0)

    # 停止超时: wait 返回 False -> stop_web_server 如实回 False(调用方决定是否仍重启)
    calls = {"stop": 0}
    handle_stuck = SimpleNamespace(
        stop=lambda: calls.__setitem__("stop", calls["stop"] + 1), wait=lambda timeout=None: False
    )
    assert lifecycle.stop_web_server(handle_stuck, 0.05) is False
    assert calls["stop"] == 1
    # 正常停止: wait 返回 True -> True
    handle_ok = SimpleNamespace(stop=lambda: None, wait=lambda timeout=None: True)
    assert lifecycle.stop_web_server(handle_ok, 0.05) is True


def test_static_version_hash_stability(tmp_path, monkeypatch):
    """静态树内容哈希 V(D5): 同内容恒等 / 改或增任一纳入文件即变 / 白名单外扩展名不进哈希

    V 是 head 资源 ?v= 的取值来源: 抖动的 V 让浏览器永远缓存未命中, 恒定的 V 让升级后
    继续吃旧 JS/CSS —— 两头都是故障, 故两头都钉。用临时树算, 不碰真实 static/。
    """
    root = tmp_path / "static"
    (root / "atlas").mkdir(parents=True)
    (root / "shared").mkdir()
    (root / "atlas" / "index.html").write_text("<html>?v=__AQB_V__</html>", encoding="utf-8")
    (root / "atlas" / "style.css").write_text("body{color:red}", encoding="utf-8")
    (root / "shared" / "app.js").write_text("window.AQB_V=1;", encoding="utf-8")
    (root / "shared" / "icon.png").write_bytes(b"\x89PNG\r\n\x1a\n")

    # 真钉排序(而非靠同进程 os.walk 天然稳定): patch 计算所用 os.walk, 让两次调用的
    # dirs/files 与目录顺序都翻转 —— static_version.py 的 dirs.sort()/entries.sort()
    # 一旦被去掉, 收集顺序即变, 断言随之变红。context 限定作用域, 后续内容用例用真 walk。
    real_walk = os.walk
    snapshots = [(r, list(dirs), list(files)) for r, dirs, files in real_walk(str(root))]
    state = {"call": 0}

    def _shuffled_walk(top, *args, **kwargs):
        state["call"] += 1
        reverse = state["call"] % 2 == 0
        seq = list(reversed(snapshots)) if reverse else snapshots
        for r, dirs, files in seq:
            out_dirs = list(reversed(dirs)) if reverse else list(dirs)
            out_files = list(reversed(files)) if reverse else list(files)
            yield r, out_dirs, out_files

    with monkeypatch.context() as m:
        m.setattr(os, "walk", _shuffled_walk)
        v_shuffled = compute_static_version(str(root))
        assert re.fullmatch(r"[0-9a-f]{16}", v_shuffled), f"V 应是 16 位十六进制, 实得 {v_shuffled}"
        v_again = compute_static_version(str(root))
        assert v_again == v_shuffled, ("同内容两次计算必须相等(遍历顺序不得影响 V —— dirs.sort()/entries.sort() 必须保留)")

    v1 = compute_static_version(str(root))
    assert v1 == v_shuffled, "dirs/files 遍历顺序被打乱时 V 仍须相等"

    # 白名单外扩展名: 运行期噪声文件进出不得改变 V
    (root / "shared" / "junk.pyc").write_bytes(b"\x00\x01noise")
    (root / "shared" / "run.log").write_text("noise", encoding="utf-8")
    assert compute_static_version(str(root)) == v1, ".pyc/.log 不得进入哈希"

    # 改任一纳入文件: V 必须变
    (root / "atlas" / "style.css").write_text("body{color:blue}", encoding="utf-8")
    v2 = compute_static_version(str(root))
    assert v2 != v1, "纳入文件变化后 V 必须变"
    # 新增纳入文件: 同样必须变
    (root / "shared" / "extra.js").write_text("x", encoding="utf-8")
    assert compute_static_version(str(root)) != v2, "新增纳入文件后 V 必须变"


def test_static_version_token_head_shape():
    """四套 index.html head 令牌形态(D4 静态守阵读盘): script/link 全挂 ?v=__AQB_V__ 且注入 window.AQB_V

    服务端替换只发生在响应层, 磁盘文件必须保留令牌本身(写回真实 V 会自毁哈希稳定性)。
    漏一个资源 = 升级后那份 JS/CSS 仍吃旧缓存且无任何报错; 四套同口径.
    """
    for ui in _UI_ALL:
        shell = open(os.path.join(STATIC_ROOT, ui, "index.html"), encoding="utf-8").read()
        head = shell.split("</head>", 1)[0]
        srcs = re.findall(r'<script[^>]*\ssrc="([^"]+)"', head)
        links = re.findall(r'<link[^>]*\shref="([^"]+)"', head)
        assert srcs and links, f"{ui} head 没解析到 script/link(守阵口径坏了)"
        for url in srcs + links:
            assert "?v=__AQB_V__" in url, f"{ui} head 资源 {url} 缺版本令牌"
        assert 'window.AQB_V = "__AQB_V__";' in head, f"{ui} head 缺 window.AQB_V 注入"
        assert head.count("?v=__AQB_V__") == len(srcs) + len(links), (f"{ui} head 版本令牌数与资源数不等 —— 有资源漏挂或重复挂")


def test_static_version_token_response_replacement(web_env):
    """HTML 版本令牌响应时替换(D4/D6): 四皮肤无残留、形状正确、仍 no-cache; 无令牌响应零副作用

    走 TestClient 真请求, 覆盖 /atlas/ 等目录形态与 /atlas/index.html 直取形态 ——
    StaticFiles(html=True) 两条路径都吐同一份 index.html, 替换必须都生效。
    """
    _, client = web_env
    v = compute_static_version(STATIC_ROOT)
    assert re.fullmatch(r"[0-9a-f]{16}", v)
    for ui in _UI_ALL:
        for path in (f"/{ui}/", f"/{ui}/index.html"):
            resp = client.get(path)
            assert resp.status_code == 200, f"{path} 应可访问"
            assert resp.headers.get("cache-control") == "no-cache", f"{path} 仍须 no-cache"
            assert int(resp.headers["content-length"]) == len(resp.content), (f"{path} Content-Length 必须按替换后字节数回填")
            assert "__AQB_V__" not in resp.text, f"{path} 有令牌残留"
            assert f'window.AQB_V = "{v}";' in resp.text, f"{path} window.AQB_V 未被赋真实 V"
            assert f"?v={v}" in resp.text, f"{path} head 资源未带真实 V"
    # 无 token 的响应零副作用: CSS 与模板分片逐字节等于磁盘文件
    css = client.get("/atlas/style.css")
    assert css.status_code == 200 and css.headers.get("cache-control") == "no-cache"
    with open(os.path.join(STATIC_ROOT, "atlas", "style.css"), "rb") as f:
        assert css.content == f.read(), "CSS 二进制不得被令牌替换逻辑改动"
    tpl = client.get("/shared/tpl/topbar.html")
    assert tpl.status_code == 200 and "__AQB_V__" not in tpl.text
    with open(os.path.join(STATIC_ROOT, "shared", "tpl", "topbar.html"), "rb") as f:
        assert tpl.content == f.read(), "无令牌的 HTML 分片应原样返回"
