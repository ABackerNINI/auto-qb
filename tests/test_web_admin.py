"""test_web_admin 测试计划: 管理端点 (分类 / 标签 / 限速 / 添加 / 导出 / 日志)

## 测试计划(每个测试函数一条)
- test_api_category_tag_endpoints: 分类/标签 CRUD 端点(入队与 400 校验)
- test_category_tag_commands_execute: 分类/标签命令执行(QbApi 封装 + 缓存失效)
- test_api_speed_mode_and_override: /api/speed/mode 曲线/停用两形态 + /api/speed/override 落 transfer 端点
- test_api_speed_alt_and_toggle: ALT-01 备用速度 —— /api/speed/mode 增列 alt_on/alt_current + /api/speed/alt 落 setPreferences(alt_*) + /api/speed/alt/toggle 落 toggle 端点
- test_qbapi_alt_speed_limits_normalization: ALT-01 QbApi 备用限速 KiB<->bytes/s 换算 + setPreferences 增量语义(只传非 None 方向) + 模式切换
- test_api_speed_mode_curve_config_disabled: 曲线存在但 enabled=False -> curve_enabled=False(快照之上叠加配置判定)
- test_api_add_torrent_endpoint: /api/torrents/add multipart(bytes 内存直传/选项透传/空来源 400)
- test_add_torrent_receipt_and_optional_flags: 添加回执两形态(API>=2.14.0 的 JSON 元数据 / 旧文本 "Ok.")判受理 + 两个 optional 选项(停止位 is_stopped / 自动管理 use_auto_torrent_management)恒显式下发(省略会吃 qB 会话/全局默认) + 成功走 INFO(改前 WARNING 会直推桌面弹窗)
- test_api_export_endpoint: /api/torrents/{hash}/export 字节流与 disposition(404/503); 非 ASCII 种子名走 filename*(回归: 头 latin-1 编码崩)
- test_content_disposition_encoding: content_disposition 头值纯 ASCII + filename* 百分号编码 + 清洗/回退
- test_api_category_tag_list_endpoints: GET /api/categories 与 /api/tags 列表端点(store 缓存数据源)
- test_api_tags_exclude_auto: /api/tags?exclude_auto=1 剔除程序自动维护标签(站点/HR 精确集 + 集数模板形状; 事件标记保留, 不带参全量)
- test_api_log_endpoint: /api/log tail 与 level 过滤(未配置空)
- test_api_log_level_filter_follows_config_format: 等级过滤按 config.logging.format 定位等级名(生产格式无方括号, 按字面量 `[WARNING` 捞会恒空 —— 2026-09-25 真机 bug)
- test_api_log_level_filter_keeps_multiline_record: 多行日志(整段 traceback)折行后跟随其记录的等级, 筛 ERROR 不丢栈
- test_api_log_note_when_level_unfilterable: 筛不了(格式无等级字段 / 已存行与格式不符)回全部行 + note, 不静默给空
- test_webui_module_apply_toggle_enabled: web.enabled 热开关(关->开启动 / 开->关停止并清句柄; 经 WebUIModule.apply 驱动, P2)
"""
import base64
import logging
import os
import tempfile
from types import SimpleNamespace
from unittest import mock

from auto_qb.webui import create_app

from webui_helpers import _web_stub

# ---------- 管理端点(R2B: 分类/标签/限速/添加/导出/日志) ----------


def test_api_category_tag_endpoints(web_env):
    """分类/标签 CRUD 端点: 正常入队返回 cmd_id; 空名/空列表 400"""
    mgr, client = web_env
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    assert client.post("/api/categories", json={
        "name": "电影",
        "save_path": "R:/mv"
    }, headers=auth).json()["queued"] is True
    assert client.post(
        "/api/categories/edit", json={
            "name": "电影",
            "save_path": "R:/mv2"
        }, headers=auth
    ).status_code == 200
    assert client.post("/api/categories/remove", json={"names": ["电影"]}, headers=auth).status_code == 200
    assert client.post("/api/tags", json={"tags": ["4K", "HDR"]}, headers=auth).status_code == 200
    assert client.post("/api/tags/remove", json={"tags": ["4K"]}, headers=auth).status_code == 200
    assert client.post("/api/categories", json={"name": "  "}, headers=auth).status_code == 400
    assert client.post("/api/categories/remove", json={"names": []}, headers=auth).status_code == 400
    assert client.post("/api/tags", json={"tags": []}, headers=auth).status_code == 400


def test_category_tag_commands_execute():
    """分类/标签命令: create/edit/remove/create_tags/delete_tags 调用 api 封装(带缓存失效)"""
    from helpers import FakeClient, make_manager

    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        mgr.client = client
        mgr._cmd_create_category(name="电影", save_path="R:/mv")
        mgr._cmd_edit_category(name="电影", save_path="R:/mv2")
        mgr._cmd_remove_categories(names=["电影"])
        mgr._cmd_create_tags(tags=["4K", "HDR"])
        mgr._cmd_delete_tags(tags=["4K"])
        assert [c[0] for c in client.calls] == [
            "create_category", "edit_category", "remove_categories", "create_tags", "delete_tags"
        ]
        assert client.calls[0][1] == "电影" and client.calls[0][2] == "R:/mv"
        assert client.calls[3][1] == ["4K", "HDR"]


def test_api_speed_mode_and_override():
    """限速托管(D2): /api/speed/mode 曲线启用/停用两形态(目标来自快照, 当前值直读);
    /api/speed/override 命令落 transfer 端点(KiB -> bytes)"""
    from fastapi.testclient import TestClient

    from helpers import FakeClient, make_manager

    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        mgr.client = client
        mgr.web.token = "t"
        mgr.web.traffic_view = {"state": "enabled", "limit": {"target": {"up": 100, "down": 50}}}
        tc = TestClient(create_app(mgr))
        auth = {"Authorization": "Bearer t"}
        data = tc.get("/api/speed/mode", headers=auth).json()
        assert data["curve_enabled"] is True
        assert data["curve_target"] == {"upload_kib": 100, "download_kib": 50}
        assert data["current"] == {"upload_limit": 0, "download_limit": 0}
        mgr.web.traffic_view = {"state": "disabled", "limit": {}}
        data = tc.get("/api/speed/mode", headers=auth).json()
        assert data["curve_enabled"] is False and data["curve_target"] is None
        # 覆盖命令: 入队 + 主循环消费 -> transfer 端点写入(bytes)
        cmd_id = tc.post("/api/speed/override", json={
            "upload_kib": 2048,
            "download_kib": 1024
        }, headers=auth).json()["cmd_id"]
        mgr.web.consume_commands()
        assert mgr.web.results[cmd_id]["status"] == "ok"
        assert ("transfer_set_upload_limit", 2048 * 1024) in client.calls
        assert ("transfer_set_download_limit", 1024 * 1024) in client.calls


def test_api_speed_alt_and_toggle():
    """ALT-01(计划 26-09-28-0037): 备用速度三端点 —— /api/speed/mode 增列 alt_on/alt_current(读失败回
    None 不冒充); /api/speed/alt 命令落 app/setPreferences(alt_*, bytes/s); /api/speed/alt/toggle
    命令落 transfer/toggleSpeedLimitsMode"""
    from fastapi.testclient import TestClient

    from helpers import FakeClient, make_manager

    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        mgr.client = client
        mgr.web.token = "t"
        mgr.web.traffic_view = {"state": "disabled", "limit": {}}
        tc = TestClient(create_app(mgr))
        auth = {"Authorization": "Bearer t"}

        # 初态: 主速度模式 + 备用限速 0
        data = tc.get("/api/speed/mode", headers=auth).json()
        assert data["alt_on"] is False
        assert data["alt_current"] == {"upload_limit": 0, "download_limit": 0}

        # 备用限速设置: KiB -> bytes 落 setPreferences(alt_*)
        cmd_id = tc.post("/api/speed/alt", json={
            "upload_kib": 1024,
            "download_kib": 512
        }, headers=auth).json()["cmd_id"]
        mgr.web.consume_commands()
        assert mgr.web.results[cmd_id]["status"] == "ok"
        assert client.alt_up_limit_value == 1024 * 1024
        assert client.alt_dl_limit_value == 512 * 1024
        assert ("app_set_preferences", ["alt_dl_limit", "alt_up_limit"]) in client.calls

        # 模式切换: toggle 端点 0 -> 1, mode 读数联动
        data = tc.get("/api/speed/mode", headers=auth).json()
        assert data["alt_current"] == {"upload_limit": 1024, "download_limit": 512}
        cmd_id = tc.post("/api/speed/alt/toggle", headers=auth).json()["cmd_id"]
        mgr.web.consume_commands()
        assert mgr.web.results[cmd_id]["status"] == "ok"
        assert client.speed_limits_mode_value == 1
        data = tc.get("/api/speed/mode", headers=auth).json()
        assert data["alt_on"] is True


def test_qbapi_alt_speed_limits_normalization(tmp_path):
    """ALT-01 QbApi Facade: 备用限速走 app/preferences alt_*(bytes/s, 0=不限) 对外 KiB;
    setPreferences 增量语义(只传非 None 方向, 两方向全 None 不发请求); 模式读/切直透"""
    from helpers import FakeClient, make_manager

    mgr = make_manager(str(tmp_path / "state.json"))
    client = FakeClient()
    mgr.client = client
    api = mgr.api

    assert api.get_alt_speed_limits() == {"upload_limit": 0, "download_limit": 0}  # 0 归一 0
    client.alt_up_limit_value = 512 * 1024
    client.alt_dl_limit_value = -1  # 负值同样归一为 0 = 不限
    assert api.get_alt_speed_limits() == {"upload_limit": 512, "download_limit": 0}

    api.set_alt_speed_limits(upload_kib=2048)  # 只传上行: 增量语义, 下行键不出现
    assert client.alt_up_limit_value == 2048 * 1024
    assert client.alt_dl_limit_value == -1
    assert client.calls[-1] == ("app_set_preferences", ["alt_up_limit"])

    api.set_alt_speed_limits(upload_kib=0, download_kib=3072)  # 0 = 不限 -> 写 0
    assert client.alt_up_limit_value == 0
    assert client.alt_dl_limit_value == 3072 * 1024

    n_calls = len(client.calls)
    api.set_alt_speed_limits()  # 两方向全 None: 不发请求
    assert len(client.calls) == n_calls

    assert api.get_speed_limits_mode() == 0
    api.toggle_speed_limits_mode()
    assert client.speed_limits_mode_value == 1
    assert api.get_speed_limits_mode() == 1


def test_api_speed_mode_curve_config_disabled():
    """曲线存在但 enabled=False -> /api/speed/mode 返回 curve_enabled=False(快照滞后也兑底); 对照 enabled=True 不影响"""
    from fastapi.testclient import TestClient

    from auto_qb.config import CurvePoint, GlobalSpeedLimitCurve, PeriodCurve
    from helpers import FakeClient, make_manager

    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        mgr.client = FakeClient()
        mgr.web.token = "t"
        mgr.config.global_speed_limit_curve = GlobalSpeedLimitCurve(
            dat_path="x.dat",
            curves=[PeriodCurve(period="day", upload_points=[CurvePoint(threshold_bytes=1, speed_bytes_per_s=1)])],
            enabled=False,
        )
        mgr.web.traffic_view = {"state": "ok", "limit": {"target": {"up": 100, "down": 50}}}  # 滞后快照
        tc = TestClient(create_app(mgr))
        auth = {"Authorization": "Bearer t"}
        data = tc.get("/api/speed/mode", headers=auth).json()
        assert data["curve_enabled"] is False and data["curve_target"] is None

        # 对照: 恢复 enabled=True(缺省)后, 快照判定不受配置叠加影响
        mgr.config.global_speed_limit_curve.enabled = True
        data = tc.get("/api/speed/mode", headers=auth).json()
        assert data["curve_enabled"] is True
        assert data["curve_target"] == {"upload_kib": 100, "download_kib": 50}


def test_api_add_torrent_endpoint():
    """添加种子(JSON+base64): bytes 经命令队列内存直传(零临时文件零新依赖) + 选项透传; 空来源 400"""
    import base64

    from fastapi.testclient import TestClient

    from helpers import FakeClient, make_manager

    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        mgr.client = client
        mgr.web.token = "t"
        tc = TestClient(create_app(mgr))
        auth = {"Authorization": "Bearer t"}
        r = tc.post(
            "/api/torrents/add",
            json={
                "files_b64": [base64.b64encode(b"d8:announce").decode()],
                "urls": ["magnet:?xt=urn:btih:X"],
                "save_path": "R:/new",
                "category": "mv",
                "tags": ["4K", "HDR"],
                "paused": True,
                "skip_checking": False,
                "sequential": True,
                "first_last_piece_prio": False,
                "auto_tmm": True,
            },
            headers=auth,
        )
        assert r.status_code == 200
        cmd_id = r.json()["cmd_id"]
        cmd, payload = mgr.web.commands.queue[0]  # peek 不消费: drain 才是回执写入者
        assert cmd == "add_torrents"
        assert payload["files"] == [b"d8:announce"]
        assert payload["urls"] == ["magnet:?xt=urn:btih:X"]
        assert payload["paused"] is True and payload["auto_tmm"] is True
        assert payload["sequential"] is True and payload["skip_checking"] is False
        assert payload["tags"] == ["4K", "HDR"]
        mgr.web.consume_commands()
        assert mgr.web.results[cmd_id]["status"] == "ok"
        adds = [c for c in client.calls if c[0] == "add"]
        assert len(adds) == 2, "文件与链接各一次 torrents_add"
        assert adds[0][1]["paused"] is True and adds[0][1]["use_auto_torrent_management"] is True
        assert adds[0][1]["tags"] == ["4K", "HDR"]
        # 空来源: 400
        assert tc.post("/api/torrents/add", json={}, headers=auth).status_code == 400


def test_add_torrent_receipt_and_optional_flags():
    """添加种子回执两形态 + 两个 optional 选项恒显式下发 + 成功走 INFO(2026-09-24 真机 bug)

    1. 回执判定只认 `"Ok." in str(result)` ⇒ 在 qB 5.2.3(Web API 2.14.0 起 `/torrents/add` 改成
       JSON 元数据 `{success_count, failure_count, pending_count, added_torrent_ids}`)恒为假 ⇒
       种子明明加进去了, WEB UI 却弹"添加种子失败";
    2. 停止位被"False 就不传"的过滤器吞掉 ⇒ qB 回落到**会话级**默认(SessionImpl::
       initLoadTorrentParams 的 `addStopped.value_or(isAddTorrentStopped())`)⇒ 前端「添加后开始」
       勾了没用。另: 停止位只能用 `is_stopped=` 传 —— 库内 `is_paused or is_stopped` 会把
       `is_paused=False` 折成 None(实测请求体为空);
       同类的「自动种子管理」也是 `std::optional`(缺省回落 `savePath 空 ∧ 全局未禁自动管理`),
       一并按"恒显式"钉住;
    3. 成功路径原来记 WARNING, 而 NotifyHandler 挂在 auto_qb logger 上 ⇒ 每次添加成功都往桌面推
       一条 WARNING 弹窗; 成功必须 INFO, 只有未被接受才 WARNING。
    """
    import base64
    import logging

    from fastapi.testclient import TestClient
    from qbittorrentapi.torrents import TorrentsAddedMetadata

    from auto_qb.webui import commands as web_commands
    from helpers import FakeClient, make_manager

    class _Capture(logging.Handler):
        """级别采集器: 挂在**模块 logger** 上"""
        def __init__(self):
            super().__init__(level=logging.INFO)
            self.records = []

        def emit(self, record):
            self.records.append(record)

    with tempfile.TemporaryDirectory() as td:
        # !不能用 caplog: make_manager 走 setup_logging, 那里有 `logging.getLogger().handlers.clear()`
        #   —— 用例体内建 manager 会把 pytest 挂在 root 上的采集 handler 一并清掉, 之后一条也抓不到
        #   (症状是"日志断言恒空")。挂模块 logger 不受 root 清理影响, 且能验到真实级别。
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        mgr.client = client
        mgr.web.token = "t"
        tc = TestClient(create_app(mgr))
        auth = {"Authorization": "Bearer t"}
        orig_add = client.torrents_add
        cap = _Capture()
        web_commands.logger.addHandler(cap)
        try:

            def add_returns(result):
                """保留 FakeClient 的台账记录, 只替换返回值(顶替真机 qB 的响应形态)"""
                client.torrents_add = lambda **kw: (orig_add(**kw), result)[1]

            def post_add(paused, auto_tmm=False):
                r = tc.post(
                    "/api/torrents/add",
                    json={
                        "files_b64": [base64.b64encode(b"d8:announce").decode()],
                        "paused": paused,
                        "auto_tmm": auto_tmm,
                    },
                    headers=auth,
                )
                assert r.status_code == 200
                cmd_id = r.json()["cmd_id"]
                mgr.web.consume_commands()
                return cmd_id

            def add_logs():
                return [(r.levelno, r.getMessage()) for r in cap.records if "添加种子" in r.getMessage()]

            # 1. 新形态(API >= 2.14.0): JSON 元数据 -> 受理; 成功必须是 INFO(改前: error + WARNING)
            add_returns(
                TorrentsAddedMetadata(
                    {
                        "success_count": 1,
                        "failure_count": 0,
                        "pending_count": 0,
                        "added_torrent_ids": ["HASH123"]
                    }
                )
            )
            assert mgr.web.results[post_add(False)]["status"] == "ok"
            assert [lvl for lvl, _ in add_logs()] == [logging.INFO], "受理成功不得走 WARNING(通知联动会直推桌面弹窗)"

            # 2. 部分失败 -> error 回执(部分成功也报错, 与 bulk 同一口径)且走 WARNING
            cap.records.clear()
            add_returns(
                TorrentsAddedMetadata(
                    {
                        "success_count": 1,
                        "failure_count": 1,
                        "pending_count": 0,
                        "added_torrent_ids": ["HASH123"]
                    }
                )
            )
            cid = post_add(False)
            assert mgr.web.results[cid]["status"] == "error"
            assert "成功 1 / 失败 1" in mgr.web.results[cid]["error"]
            assert [lvl for lvl, _ in add_logs()] == [logging.WARNING]

            # 3. 仅 pending(magnet 元数据未就绪)也是受理, 不是失败
            add_returns(
                TorrentsAddedMetadata(
                    {
                        "success_count": 0,
                        "failure_count": 0,
                        "pending_count": 1,
                        "added_torrent_ids": []
                    }
                )
            )
            assert mgr.web.results[post_add(False)]["status"] == "ok"

            # 4. 旧形态文本仍认(API < 2.14.0 的 "Ok."/"Fails.")
            add_returns("Ok.")
            assert mgr.web.results[post_add(False)]["status"] == "ok"
            add_returns("Fails.")
            assert mgr.web.results[post_add(False)]["status"] == "error"

            # 5. 两个 optional 选项必须**显式**下发(省略 = 吃 qB 会话/全局默认, 勾选框失效):
            #    停止位 + 自动种子管理。`use_auto_torrent_management` 由替身记 kw.get(...) ——
            #    没传时是 None, 传 False 才是 False, 两者可分。
            add_returns("Ok.")
            post_add(False)
            last = [c for c in client.calls if c[0] == "add"][-1][1]
            assert last["is_stopped_raw"] is False, "省略 stopped 会吃 qB 会话默认(不自动开始) => 选项失效"
            assert last["use_auto_torrent_management"] is False, "省略 autoTMM 会吃 qB 全局管理模式 => 选项失效"
            assert last["paused"] is False
            # 勾选方向: 两个都显式 True
            post_add(True, auto_tmm=True)
            last = [c for c in client.calls if c[0] == "add"][-1][1]
            assert last["is_stopped_raw"] is True and last["paused"] is True
            assert last["use_auto_torrent_management"] is True
            post_add(True)
            last = [c for c in client.calls if c[0] == "add"][-1][1]
            assert last["is_stopped_raw"] is True and last["paused"] is True
        finally:
            web_commands.logger.removeHandler(cap)


def test_api_export_endpoint(web_env):
    """导出 .torrent: 原始字节 + Content-Disposition; 未知 hash 404, qB 断连 503

    非 ASCII 种子名是回归点: HTTP 头只能 latin-1, 直写中文时 Starlette 编码头抛
    UnicodeEncodeError 导致整个导出 500(TestClient 会把该异常上抛到测试里)。
    """
    from helpers import FakeClient

    from auto_qb.torrents import TorrentRecord

    mgr, client = web_env
    rec = TorrentRecord(hash="HA", name='Show"S01')
    cn = TorrentRecord(hash="HB", name="我的种子/第一季")
    mgr.store.get = lambda h: {"HA": rec, "HB": cn}.get(h)
    fake = FakeClient()
    mgr.client = fake
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    r = client.get("/api/torrents/HA/export", headers=auth)
    assert r.status_code == 200 and r.content == b"TORRENT-DATA"
    assert "attachment" in r.headers["content-disposition"]
    assert "ShowS01.torrent" in r.headers["content-disposition"], "文件名中的引号/路径符应被清洗"
    # 中文名: 回退名用 hash, 原名走 filename*=UTF-8''(百分号编码), 头值本身仍是纯 ASCII
    rc = client.get("/api/torrents/HB/export", headers=auth)
    assert rc.status_code == 200 and rc.content == b"TORRENT-DATA"
    cd = rc.headers["content-disposition"]
    assert 'filename="HB.torrent"' in cd, "纯非 ASCII 名无可用回退 -> 用 hash"
    assert "filename*=UTF-8''%E6%88%91%E7%9A%84%E7%A7%8D%E5%AD%90_%E7%AC%AC%E4%B8%80%E5%AD%A3.torrent" in cd
    assert client.get("/api/torrents/NOPE/export", headers=auth).status_code == 404
    mgr.client = None
    assert client.get("/api/torrents/HA/export", headers=auth).status_code == 503


def test_content_disposition_encoding():
    """content_disposition: 头值恒为 latin-1 可编码的纯 ASCII, 原名走 filename* 百分号编码

    覆盖清洗(引号/路径符/控制字符 -> 防头注入)、ASCII/非 ASCII 混合名的回退、ext 后缀。
    """
    from auto_qb.webui import content_disposition

    # 全非 ASCII: 回退名取 fallback, 原名保留在 filename*
    cd = content_disposition("中文种子", "HASH", "torrent")
    assert cd.encode("latin-1")  # 头值必须可 latin-1 编码, 否则响应 500
    assert 'filename="HASH.torrent"' in cd
    assert cd.endswith("filename*=UTF-8''%E4%B8%AD%E6%96%87%E7%A7%8D%E5%AD%90.torrent")
    # 混合名: 回退名去掉非 ASCII 部分, 中文部分仍需在 filename* 里完整保留
    cd = content_disposition("Show/我的\\种子\"X", "HASH", "torrent")
    assert cd.encode("latin-1")
    assert 'filename="Show__X.torrent"' in cd, "路径符与引号应被清洗"
    assert "%E6%88%91%E7%9A%84_%E7%A7%8D%E5%AD%90X" in cd
    # 控制字符(CR/LF)必须剔除, 否则可截断/注入头
    cd = content_disposition("a\r\nb", "HASH", "torrent")
    assert "\r" not in cd and "\n" not in cd
    assert 'filename="ab.torrent"' in cd
    # 无 ext 时不加后缀
    assert content_disposition("a", "HASH") == "attachment; filename=\"a\"; filename*=UTF-8''a"


def test_api_category_tag_list_endpoints(web_env):
    """GET /api/categories 与 /api/tags 列表端点: 透出 store 缓存(管理对话框数据源)"""
    mgr, client = web_env
    mgr.api = SimpleNamespace(
        torrents_categories=lambda: {"mv": {
            "save_path": "R:/mv"
        }},
        torrents_tags=lambda: ["4K", "HDR"],
    )
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    assert client.get("/api/categories", headers=auth).json() == {"categories": {"mv": {"save_path": "R:/mv"}}}
    assert client.get("/api/tags", headers=auth).json() == {"tags": ["4K", "HDR"]}


def test_api_tags_exclude_auto(web_env):
    """/api/tags?exclude_auto=1: 剔除程序自动维护的标签(站点/HR 精确集 + 集数模板形状)

    添加种子窗口与「标签/分类…」弹窗的候选源; 事件标记(MISSING/zSkipChecked)与普通
    用户标签保留(2026-09-28 拍板); 不带参仍全量 —— 标签管理对话框数据源不受影响。"""
    from types import SimpleNamespace

    mgr, client = web_env
    mgr.config.trackers["HHan"].hr = SimpleNamespace(
        add_tag="HR-${required_seeding_time}",
        add_tag_for_satisfied="",
        required_seeding_time_raw="3D",
    )
    mgr.config.add_episode_tags = SimpleNamespace(
        enabled=True,
        add_tag_single="zE${episode_first}",
        add_tag_multi="zE${episode_first}-${episode_last}",
    )
    mgr.api = SimpleNamespace(torrents_tags=lambda: ["4K", "HHan", "HR-3D", "zE1", "zE1-12", "zE1x", "MISSING"], )
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    assert client.get("/api/tags?exclude_auto=1", headers=auth).json() == {"tags": ["4K", "zE1x", "MISSING"]}
    assert client.get("/api/tags", headers=auth).json() == {
        "tags": ["4K", "HHan", "HR-3D", "zE1", "zE1-12", "zE1x", "MISSING"]
    }


def _log_lines(fmt, recs):
    """按 fmt 渲染真实日志行 —— 手写字符串一旦与 config.logging.format 不符,
    测的就成了"格式不符"那条兜底路径, 真正的等级过滤反而没测到(本轮实测踩过)。
    asctime 取自 record.created, 故同一 record 渲染两次结果一致、可用来对账。"""
    fmtr = logging.Formatter(fmt)
    return [fmtr.format(logging.LogRecord(name, lv, "f.py", 1, msg, None, None)) for name, lv, msg in recs]


def test_api_log_endpoint(web_env):
    """/api/log: 自身日志 tail + 按配置格式串过滤等级; 文件未配置返回空

    必须显式设 format: web_env 替身的 logging.format 是 `%(message)s`(没有等级字段),
    直接拿它测等级过滤只会落到"筛不了"的兜底路径。"""
    from auto_qb.config.models import LoggingConfig

    mgr, client = web_env
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    log_path = os.path.join(mgr.data_dir, "auto-qb.log")
    fmt = mgr.config.logging.format = LoggingConfig().format  # 未配置 log.format 时的默认
    lines = _log_lines(
        fmt, [
            ("auto_qb.core.x", logging.INFO, "启动完成"), ("auto_qb.core.y", logging.WARNING, "连接重试"),
            ("auto_qb.core.z", logging.ERROR, "校验失败")
        ]
    )
    with open(log_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    mgr.config.logging.file = log_path
    data = client.get("/api/log?lines=10", headers=auth).json()
    assert len(data["lines"]) == 3 and data["file"] == log_path and data["note"] == ""
    for lv, want in (("info", lines[0]), ("warning", lines[1]), ("error", lines[2])):
        data = client.get(f"/api/log?lines=10&level={lv}", headers=auth).json()
        assert data["lines"] == [want] and data["note"] == "", lv
    mgr.config.logging.file = ""
    assert client.get("/api/log", headers=auth).json() == {"lines": [], "file": "", "note": ""}


def test_api_log_level_filter_follows_config_format(web_env):
    """等级过滤按 config.logging.format 定位等级名, 不能靠字面量 —— 生产配置的 format 是
    `%(asctime)s - %(levelname)s - %(message)s`(无方括号), 旧实现按 `[WARNING` 捞 ⇒ 恒空,
    界面只剩"日志文件暂无内容"(2026-09-25 真机报告)。"""
    mgr, client = web_env
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    log_path = os.path.join(mgr.data_dir, "auto-qb.log")
    mgr.config.logging.format = "%(asctime)s - %(levelname)s - %(message)s"  # 与 config.yml 同形
    lines = _log_lines(
        mgr.config.logging.format, [
            ("auto_qb.core.x", logging.INFO, "启动完成"), ("auto_qb.core.y", logging.WARNING, "连接重试"),
            ("auto_qb.core.z", logging.ERROR, "校验失败")
        ]
    )
    assert "[WARNING" not in lines[1], "本用例的前提: 该格式的行里没有方括号等级标记"
    with open(log_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    mgr.config.logging.file = log_path
    data = client.get("/api/log?lines=100&level=WARNING", headers=auth).json()
    assert data["lines"] == [lines[1]] and data["note"] == ""
    assert client.get("/api/log?lines=100&level=ERROR", headers=auth).json()["lines"] == [lines[2]]


def test_api_log_level_filter_keeps_multiline_record(web_env):
    """多行日志(exc_info=True 打出的整段 traceback)折行后每行都不带等级标记 —— 过滤按"记录"
    取舍, 否则筛 ERROR 只剩标题行、用户真正要看的栈被丢掉。"""
    mgr, client = web_env
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    log_path = os.path.join(mgr.data_dir, "auto-qb.log")
    fmt = mgr.config.logging.format = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    header = _log_lines(fmt, [("auto_qb.core", logging.ERROR, "主循环异常: boom")])[0]
    body = ["Traceback (most recent call last):", '  File "x.py", line 1, in <module>', "RuntimeError: boom"]
    nxt = _log_lines(fmt, [("auto_qb.core", logging.INFO, "下一轮")])[0]
    with open(log_path, "w", encoding="utf-8") as f:
        f.write("\n".join([header] + body + [nxt]) + "\n")
    mgr.config.logging.file = log_path
    data = client.get("/api/log?lines=100&level=ERROR", headers=auth).json()
    assert data["lines"] == [header] + body and data["note"] == ""


def test_api_log_note_when_level_unfilterable(web_env):
    """两种"筛不了"都回全部行 + note, 不静默给空 —— 否则"筛选失效"与"确实没有该等级日志"
    在界面上长得一模一样(本轮 bug 的观感就是这个)。"""
    from auto_qb.infra.logging import NOTE_FORMAT_MISMATCH, NOTE_NO_LEVEL_FIELD

    mgr, client = web_env
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    log_path = os.path.join(mgr.data_dir, "auto-qb.log")
    mgr.config.logging.format = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    lines = _log_lines(
        mgr.config.logging.format,
        [("auto_qb.core.x", logging.INFO, "启动完成"), ("auto_qb.core.y", logging.WARNING, "连接重试")]
    )
    with open(log_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    mgr.config.logging.file = log_path
    # 1.格式里没有等级字段 -> 等级无从判定
    mgr.config.logging.format = "%(asctime)s %(message)s"
    data = client.get("/api/log?lines=100&level=WARNING", headers=auth).json()
    assert data["lines"] == lines and data["note"] == NOTE_NO_LEVEL_FIELD
    # 2.格式有等级字段, 但文件里的行是另一种格式(改了 format, 旧行还在) -> 一行都对不上
    mgr.config.logging.format = "%(levelname)s|%(asctime)s|%(message)s"
    data = client.get("/api/log?lines=100&level=WARNING", headers=auth).json()
    assert data["lines"] == lines and data["note"] == NOTE_FORMAT_MISMATCH
    # 不过滤时无论哪种格式都照常给全部行, 且不带 note
    data = client.get("/api/log?lines=100", headers=auth).json()
    assert data["lines"] == lines and data["note"] == ""


def test_webui_module_apply_toggle_enabled(monkeypatch):
    """web.enabled 热开关(经 WebUIModule.apply, P2): 关 -> 开(启动服务器); 开 -> 关(停止并清空句柄)"""
    from helpers import make_manager

    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        started = mock.MagicMock(return_value="新句柄")
        stopped = mock.MagicMock()
        monkeypatch.setattr("auto_qb.webui.start_web_server", started)
        monkeypatch.setattr("auto_qb.webui.stop_web_server", stopped)
        mod = mgr.host.get("webui")

        # 关 -> 开(旧句柄为 None, 原先该场景完全不生效)
        mgr.config.web = _web_stub(enabled=True, port=8080)
        mgr.web.handle = None
        mod.apply(SimpleNamespace(web=_web_stub(enabled=False, port=8080)), mgr.config)
        started.assert_called_once()
        assert mgr.web.handle == "新句柄"

        # 开 -> 关: 停止并清空句柄
        mgr.config.web = _web_stub(enabled=False, port=8080)
        mod.apply(SimpleNamespace(web=_web_stub(enabled=True, port=8080)), mgr.config)
        stopped.assert_called_once()
        assert mgr.web.handle is None
