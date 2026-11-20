"""test_web_api_core 测试计划: WEB UI 核心 API 读写

## 测试计划(每个测试函数一条)
- test_api_webui_flags_endpoint: R2 功能旗标端点(计划 26-10-02-1955 W1) —— 开/关读实时配置 + 未鉴权 401; qb_traffic_enabled 旗标(P5a)段缺省/关 = False, 开 = True; relocate_enabled 旗标(计划 26-11-07-1300 R6a)同口径透传 relocate.enabled
- test_lifecycle_wait_until_started_and_stop_timeout: 生命周期等待/停止三出口(P0-T0.5)
- test_api_t_skip_check_gated_by_config: R2 skip-check 端点 gate —— 配置关 403(detail 注明 web.skip_check_menu)/ 开 200 入队, 403 不投递命令
- test_api_status_and_groups: 状态与分组快照读取(经注入的 manager; status 含 version)
- test_api_expr_eval_endpoint: 表达式试算端点(校验-only / 按种子求值 + 中间值 / 名字错误 / 种子不存在)
- test_static_assets_disable_heuristic_cache: 静态资源带 no-cache(/api 不受影响), 防升级后仍加载旧前端(UI 目录化路径: atlas/prism/shared)
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
    """静态资源带 no-cache: 不加 Cache-Control 时浏览器会启发式缓存数小时

    症状: 升级程序后仍加载旧前端("改了但没变"), 开发中实际撞到。
    no-cache 仍允许存储, 但每次必须带 ETag 重新校验(未变走 304); /api 响应不受影响。
    路径随 UI 目录化更新: atlas=星图(旧) / prism=棱镜(新) / shared=公共逻辑层。
    """
    mgr, client = web_env
    for path in (
        "/atlas/", "/atlas/style.css", "/shared/tpl/topbar.html", "/prism/", "/shared/app.js", "/shared/boot.js",
        "/shared/vendor/vue.global.prod.js", "/console/", "/console/css/components.css"
    ):
        resp = client.get(path)
        assert resp.status_code == 200, f"{path} 应可访问"
        assert resp.headers.get("cache-control") == "no-cache", f"{path} 应带 no-cache"
    api = client.get("/api/status", headers={"Authorization": f"Bearer {mgr.web.token}"})
    assert api.headers.get("cache-control") != "no-cache", "/api 响应不应被静态策略影响"
    # HEAD 只发头不发体: 中间件若把空 body_iterator 收齐后重建响应, 会把 Content-Length 清零,
    # 破坏 HEAD 应回显与 GET 等效的长度语义 —— 必须保留原响应头(只带 no-cache)。
    head = client.head("/atlas/")
    assert head.status_code == 200, "HEAD /atlas/ 应可访问"
    assert head.content == b"", "HEAD 不应带 body"
    assert int(head.headers["content-length"]) > 0, "HEAD 的 Content-Length 不得被收空 body 的重建响应清零"
    assert head.headers.get("cache-control") == "no-cache", "HEAD 响应仍须 no-cache"


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
