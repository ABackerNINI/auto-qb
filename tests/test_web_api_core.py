"""test_web_api_core 测试计划: WEB UI 核心 API 读写

## 测试计划(每个测试函数一条)
- test_api_webui_flags_endpoint: R2 功能旗标端点(计划 26-10-02-1955 W1) —— 开/关读实时配置 + 未鉴权 401; qb_traffic_enabled 旗标(P5a)段缺省/关 = False, 开 = True
- test_api_t_skip_check_gated_by_config: R2 skip-check 端点 gate —— 配置关 403(detail 注明 web.skip_check_menu)/ 开 200 入队, 403 不投递命令
- test_api_status_and_groups: 状态与分组快照读取(经注入的 manager; status 含 version)
- test_api_expr_eval_endpoint: 表达式试算端点(校验-only / 按种子求值 + 中间值 / 名字错误 / 种子不存在)
- test_static_assets_disable_heuristic_cache: 静态资源带 no-cache(/api 不受影响), 防升级后仍加载旧前端(UI 目录化路径: atlas/prism/shared)
- test_ui_root_and_legacy_newui_redirect: / -> 307 上次使用的 UI(autoqb_ui 皮肤 cookie, 未记录/失效回落星图); 旧 /newui/* 书签 -> 307 /prism/*
- test_frontend_ui_skin_cookie_persisted: boot.js 必须把当前 UI 写进 autoqb_ui cookie —— 根路径「记住上次 UI」的数据源(307 在服务端裁决, cookie 是唯一读得到的载体)
"""
import os

from auto_qb import __version__

from webui_helpers import STATIC_ROOT, _enable_qb_traffic


def test_api_webui_flags_endpoint(web_env):
    """R2 功能旗标端点(计划 26-10-02-1955 W1): 开/关读**实时配置** + 未鉴权 401

    FakeConfig 测试侧默认 skip_check_menu=True(helpers, 供既有 skip-check 用例直通);
    关闭用例实例级置 False(深拷贝, 不跨测试泄漏) —— 端点必须现取 manager.config 引用,
    不按值持有旧 Config(hot-reload-held-config 坑)。
    qb_traffic_enabled(P5a, plan 26-10-03-0946 §07): 段缺省 None / enabled=false 均 False,
    _enable_qb_traffic 置段 enabled=True 后即时翻真(读实时配置口径)。
    """
    mgr, client = web_env
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    assert client.get("/api/webui/flags", headers=auth).json() == {
        "skip_check_menu": True,
        "qb_traffic_enabled": False,  # FakeConfig 默认 qb_traffic=None(未启用)
    }
    mgr.config.web.skip_check_menu = False
    assert client.get("/api/webui/flags", headers=auth).json() == {
        "skip_check_menu": False,
        "qb_traffic_enabled": False,
    }
    _enable_qb_traffic(mgr, enabled=True)
    assert client.get("/api/webui/flags", headers=auth).json()["qb_traffic_enabled"] is True
    _enable_qb_traffic(mgr, enabled=False)
    assert client.get("/api/webui/flags", headers=auth).json()["qb_traffic_enabled"] is False
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
    """状态与分组快照读取: 徽章数据/组名/站点明细齐全; status 携带版本号(顶栏展示)"""
    mgr, client = web_env
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    status = client.get("/api/status", headers=auth).json()
    assert status["connected"] is True and status["torrents"] == 2
    assert status["version"] == __version__, "status 应透出包版本号"
    data = client.get("/api/groups", headers=auth).json()
    assert len(data["groups"]) == 1
    g = data["groups"][0]
    assert g["name"] == "Show" and g["count"] == 2 and g["upspeed"] == 2048
    assert [m["site"] for m in g["members"]] == ["HHan", "M-Team"]


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
    三套 UI 共用 boot.js = 唯一写入口(打开即记录, 切换菜单无需单独埋点)。服务端取值校验
    (形状 + 目录存在性)见 test_ui_root_and_legacy_newui_redirect。
    """
    boot = open(os.path.join(STATIC_ROOT, "shared", "boot.js"), encoding="utf-8").read()
    assert '"autoqb_ui="' in boot, "boot.js 未写 autoqb_ui cookie —— 关窗重开根路径会回到默认星图"
    assert "location.pathname.split" in boot, "boot.js 未从 URL 路径段判定当前 UI"
    assert "Max-Age=" in boot, "皮肤 cookie 必须带有效期(会话 cookie 关窗即丢, 等于没修)"
    assert "Path=/" in boot, "皮肤 cookie 必须 Path=/(根路径 / 要能读到)"
