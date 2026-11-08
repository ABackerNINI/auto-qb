"""test_web_admin 测试计划: 管理端点 (分类 / 标签 / 限速 / 添加 / 导出 / 日志)

## 测试计划(每个测试函数一条)
- test_api_category_tag_endpoints: 分类/标签 CRUD 端点(入队与 400 校验)
- test_category_tag_commands_execute: 分类/标签命令执行(QbApi 封装 + 缓存失效)
- test_api_speed_mode_and_override: /api/speed/mode 曲线/停用两形态 + /api/speed/override 落 transfer 端点(负数 400 / 0 放行, issue 26-11-08-0044)
- test_api_speed_alt_and_toggle: ALT-01 备用速度 —— /api/speed/mode 增列 alt_on/alt_current + /api/speed/alt 落 setPreferences(alt_*) + /api/speed/alt/toggle 落 toggle 端点(负数 400 / 0 放行, issue 26-11-08-0044)
- test_qbapi_alt_speed_limits_normalization: ALT-01 QbApi 备用限速 KiB<->bytes/s 换算 + setPreferences 增量语义(只传非 None 方向) + 模式切换
- test_api_speed_mode_curve_config_disabled: 曲线存在但 enabled=False -> curve_enabled=False(快照之上叠加配置判定)
- test_api_add_torrent_endpoint: /api/torrents/add multipart(bytes 内存直传/选项透传/空来源 400)
- test_add_torrent_receipt_and_optional_flags: 添加回执两形态(API>=2.14.0 的 JSON 元数据 / 旧文本 "Ok.")判受理 + 两个 optional 选项(停止位 is_stopped / 自动管理 use_auto_torrent_management)恒显式下发(省略会吃 qB 会话/全局默认) + 成功走 INFO(改前 WARNING 会直推桌面弹窗) + 三态回执(全受理 ok / 部分受理 warn / 全拒 error, 2026-10-18「部分失败时窗口不消失」报障)
- test_api_export_endpoint: /api/torrents/{hash}/export 字节流与 disposition(404/503); 非 ASCII 种子名走 filename*(回归: 头 latin-1 编码崩)
- test_content_disposition_encoding: content_disposition 头值纯 ASCII + filename* 百分号编码 + 清洗/回退
- test_api_category_tag_list_endpoints: GET /api/categories 与 /api/tags 列表端点(store 缓存数据源)
- test_api_tags_exclude_auto: /api/tags?exclude_auto=1 剔除程序自动维护标签(站点/HR 精确集 + 集数模板形状; 事件标记保留, 不带参全量)
- test_api_log_endpoint: /api/log tail 与 level 过滤(未配置空)
- test_api_log_level_filter_follows_config_format: 等级过滤按 config.logging.format 定位等级名(生产格式无方括号, 按字面量 `[WARNING` 捞会恒空 —— 2026-09-25 真机 bug)
- test_api_log_level_filter_keeps_multiline_record: 多行日志(整段 traceback)折行后跟随其记录的等级, 筛 ERROR 不丢栈
- test_api_log_note_when_level_unfilterable: 筛不了(格式无等级字段 / 已存行与格式不符)回全部行 + note, 不静默给空
- test_webui_module_apply_toggle_enabled: web.enabled 热开关(关->开启动 / 开->关停止并清句柄; 经 WebUIModule.apply 驱动, P2)
- test_webui_module_start_raises_bind_error_when_port_taken: 端口被占 -> WebUIModule.start 抛 WebUIBindError(启动期 fail-fast); 消息单行且含 host/port/配置键/常见原因/处置; 低层仍返回未就绪句柄(R1); 探针替身注入(不真跑 ss/lsof/powershell), 并断言探针仍被调用一次(诊断接线未断)
- test_webui_module_bind_diagnosis_block_when_port_taken: 端口被占 -> start 落多行 INFO 诊断块(host/port/配置键/原因/占用者/处置三选一/退出后果), 异常消息不含探针内容
- test_webui_module_bind_diagnosis_probe_unrecognized: 探针不可用或抛异常 -> 诊断块固定写「未识别」且异常类型/消息不变; 探针失败只写 DEBUG
- test_webui_module_bind_diagnosis_adds_no_error_events: 探针 found / 抛异常两轮对比, auto_qb 树下 ERROR 条数不变(既有 lifecycle 两条保持原样)
### T2a 覆盖率第三轮: 诊断面静默采集与探针降级
- test_bind_capture_swallows_poisoned_record: _BindFailureCapture.emit 采集失败静默(坏记录不逃逸不伪造原因), 好记录仍可采集
- test_port_owner_line_absent_state: 探针回 STATE_ABSENT -> 固定降级文案「未找到(端口可能刚被释放)」
"""
import base64
import logging
import os
import tempfile
from types import SimpleNamespace
from unittest import mock

import pytest

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
        # issue 26-11-08-0044: 负数 400 拒收(与单发/bulk 限速路由同口径), 0 = 不限合法
        r = tc.post("/api/speed/override", json={"upload_kib": -1, "download_kib": 0}, headers=auth)
        assert r.status_code == 400 and "upload_kib" in r.json()["detail"]
        r = tc.post("/api/speed/override", json={"upload_kib": 0, "download_kib": -5}, headers=auth)
        assert r.status_code == 400 and "download_kib" in r.json()["detail"]
        cmd_id = tc.post("/api/speed/override", json={
            "upload_kib": 0,
            "download_kib": 0
        }, headers=auth).json()["cmd_id"]
        mgr.web.consume_commands()
        assert mgr.web.results[cmd_id]["status"] == "ok"
        assert ("transfer_set_upload_limit", 0) in client.calls
        assert ("transfer_set_download_limit", 0) in client.calls


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

        # issue 26-11-08-0044: 负数 400 拒收(与单发/bulk 限速路由同口径, 400 不入队不落
        # setPreferences, 不影响后续 toggle 断言)
        r = tc.post("/api/speed/alt", json={"upload_kib": -1, "download_kib": 0}, headers=auth)
        assert r.status_code == 400 and "upload_kib" in r.json()["detail"]
        r = tc.post("/api/speed/alt", json={"upload_kib": 0, "download_kib": -5}, headers=auth)
        assert r.status_code == 400 and "download_kib" in r.json()["detail"]

        # 模式切换: toggle 端点 0 -> 1, mode 读数联动
        data = tc.get("/api/speed/mode", headers=auth).json()
        assert data["alt_current"] == {"upload_limit": 1024, "download_limit": 512}
        cmd_id = tc.post("/api/speed/alt/toggle", headers=auth).json()["cmd_id"]
        mgr.web.consume_commands()
        assert mgr.web.results[cmd_id]["status"] == "ok"
        assert client.speed_limits_mode_value == 1
        data = tc.get("/api/speed/mode", headers=auth).json()
        assert data["alt_on"] is True

        # issue 26-11-08-0044: 0 = 不限合法(两方向 0 入队落 setPreferences(0))
        cmd_id = tc.post("/api/speed/alt", json={"upload_kib": 0, "download_kib": 0}, headers=auth).json()["cmd_id"]
        mgr.web.consume_commands()
        assert mgr.web.results[cmd_id]["status"] == "ok"
        assert client.alt_up_limit_value == 0
        assert client.alt_dl_limit_value == 0


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


def test_api_speed_mode_curve_config_disabled(web_env):
    """曲线存在但 enabled=False -> /api/speed/mode 返回 curve_enabled=False(快照滞后也兑底); 对照 enabled=True 不影响"""
    from auto_qb.config import CurvePoint, GlobalSpeedLimitCurve, PeriodCurve

    mgr, tc = web_env
    mgr.config.global_speed_limit_curve = GlobalSpeedLimitCurve(
        curves=[PeriodCurve(period="day", upload_points=[CurvePoint(threshold_bytes=1, speed_bytes_per_s=1)])],
        enabled=False,
    )
    mgr.config.traffic_source.traffic_monitor.dat_path = "x.dat"
    mgr.web.traffic_view = {"state": "ok", "limit": {"target": {"up": 100, "down": 50}}}  # 滞后快照
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
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
    4. 部分受理(有成功有失败, qB 对重复种子整批里挑着拒 = HTTP 200 + failure_count>0)原来被
       折叠进 error 回执 ⇒ 前端只能"关窗/留窗"二选一, 用户报「部分种子添加失败(已存在)时
       添加窗口不消失」(2026-10-18)。改为三态回执: 部分受理 = warn(带计数详情), 前端按它关窗。
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

            # 2. 部分受理(有成功有失败, qB 对重复种子整批里挑着拒) -> warn 回执(2026-10-18
            #    报障「部分种子添加失败(已存在)时添加窗口不消失」: 旧口径把部分受理折叠进
            #    error, 前端留窗; 改三态后按 warn 关窗)且仍走 WARNING(有种子没进去)
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
            assert mgr.web.results[cid]["status"] == "warn"
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


def test_webui_module_start_raises_bind_error_when_port_taken(tmp_path, monkeypatch):
    """WebUIModule.start: 端口被占 -> 抛 WebUIBindError(启动期 fail-fast), 消息单行且含关键字段

    R1 抛点在模块层: 低层 `start_web_server` 保持「返回 handle」的原契约(其契约守阵在
    test_web_views_reload), 热重载 apply() 复用同一低层函数, 行为不变。

    !探针必须注入替身: 本用例只验消息面, 但生产路径会调 `describe_port_owner` —— Linux 上那会
    真跑 `ss -ltnp`, 即一条越界的真实系统副作用(CI 曾因此红; Windows 只是被 conftest 的通知器
    守卫偶然挡住 powershell, 不是设计保证)。注入后仍断言探针被调用一次: 诊断接线被摘掉/绕开
    时该断言会红, 「不 spawn」与「接线在」两件事同时钉住。
    """
    import socket

    from auto_qb.infra.port_owner import PortProbe
    from auto_qb.webui import stop_web_server
    from auto_qb.webui.server.lifecycle import WebUIBindError

    from helpers import make_manager

    probe_calls = []

    def probe(host, _port):
        probe_calls.append((host, _port))
        return PortProbe.unavailable("测试替身: 诊断旁路不跑外部命令")

    monkeypatch.setattr("auto_qb.webui.module.describe_port_owner", probe)
    with socket.socket() as holder:  # 占住端口(bind + listen 后不可再绑)
        holder.bind(("127.0.0.1", 0))
        holder.listen(1)
        port = holder.getsockname()[1]
        mgr = make_manager(str(tmp_path / "state.json"))
        mgr.config.web.enabled = True
        mgr.config.web.port = port
        mod = mgr.host.get("webui")
        try:
            with pytest.raises(WebUIBindError) as excinfo:
                mod.start(mgr.ctx, dry_run=False)
        finally:
            if mgr.web.handle is not None:
                stop_web_server(mgr.web.handle)

        handle = mgr.web.handle
        assert handle is not None and handle.started is False, "低层仍返回未就绪句柄(R1: 不改原契约)"
        message = str(excinfo.value)
        assert "\n" not in message, "stderr 文案必须单行"
        assert "WebUI 启动失败" in message
        assert f"127.0.0.1:{port}" in message, "文案必须给出配置原值的 host:port"
        assert f"web.port={port}" in message and "web.enabled=true" in message, "文案必须含配置键路径"
        assert "同机多实例默认同端口" in message, "常见原因要点明多实例同端口"
        assert "web.enabled: false" in message and "采集不会启动" in message, "处置与退出后果必须可照做"
        assert probe_calls == [(mgr.config.web.host, port)], (
            "启动失败诊断仍须调用端口占用者探针(接线被摘掉=诊断面退化); 且调用点必须是"
            "`auto_qb.webui.module.describe_port_owner`(绕开该符号=替身失效, 真实外部命令会重新跑起来)"
        )


def _start_webui_on_taken_port(tmp_path, monkeypatch, probe, logger_name="auto_qb.webui.module"):
    """真占端口后驱动 WebUIModule.start(S2b): 探针替身经 monkeypatch 注入, 返回 (mgr, port, 异常, 捕获日志)

    !日志捕获走 helpers.capture_logs 直挂 logger, 不用 caplog —— make_manager 的
      setup_logging 会清空 root handlers, pytest 挂在 root 上的采集 handler 一并被清。
    """
    import socket

    from auto_qb.webui import stop_web_server
    from auto_qb.webui.server.lifecycle import WebUIBindError

    from helpers import capture_logs, make_manager

    monkeypatch.setattr("auto_qb.webui.module.describe_port_owner", probe)
    with socket.socket() as holder:  # 占住端口(bind + listen 后不可再绑)
        holder.bind(("127.0.0.1", 0))
        holder.listen(1)
        port = holder.getsockname()[1]
        mgr = make_manager(str(tmp_path / "state.json"))
        mgr.config.web.enabled = True
        mgr.config.web.port = port
        with capture_logs(logger_name) as cap:
            try:
                with pytest.raises(WebUIBindError) as excinfo:
                    mgr.host.get("webui").start(mgr.ctx, dry_run=False)
            finally:
                if mgr.web.handle is not None:
                    stop_web_server(mgr.web.handle)
    return mgr, port, excinfo.value, cap


def test_webui_module_bind_diagnosis_block_when_port_taken(tmp_path, monkeypatch):
    """端口被占 -> 多行 INFO 诊断块: 无法监听的配置原值 + 原因 + 占用者 + 处置三选一 + 退出后果

    S2b: 诊断是同一故障的附加信息(INFO), 不是新的失败事件; 探针内容只进日志,
    不进 WebUIBindError 消息(stderr 单行与 notify_fatal 内容与 S2a 完全一致)。
    """
    from auto_qb.infra.port_owner import PortOwner, PortProbe
    from auto_qb.webui.server.lifecycle import _bind_message

    def probe(host, _port):
        return PortProbe.found(PortOwner(pid=4321, name="python.exe", cmdline="python -m http.server 40000"))

    mgr, port, exc, cap = _start_webui_on_taken_port(tmp_path, monkeypatch, probe)
    diag = cap.text
    assert "WEB UI 启动失败诊断" in diag, "沿用既有检索字样"
    assert f"web.enabled=true, web.host=127.0.0.1, web.port={port}" in diag, "诊断块必须给出配置原值"
    assert "原因: 端口无法监听" in diag
    assert "占用者: pid=4321, 进程=python.exe, 命令行=python -m http.server 40000" in diag
    assert "改 web.port" in diag and "改 web.host" in diag and "web.enabled: false" in diag, "处置三选一必须可照做"
    assert "退出码 1" in diag and "采集不会启动" in diag, "退出后果必须写明"
    # 诊断块恰一条, 且必须是 INFO(不得新增 ERROR 事件)
    diag_records = [r for r in cap.records if "WEB UI 启动失败诊断" in r.getMessage()]
    assert len(diag_records) == 1 and diag_records[0].levelno == logging.INFO
    # 异常消息不含探针内容: 与 S2a 的单行消息逐字相同
    message = str(exc)
    assert message == _bind_message(mgr.config.web)
    assert "4321" not in message and "占用者" not in message and "命令行" not in message


@pytest.mark.parametrize("probe_kind", ["unavailable", "raises"])
def test_webui_module_bind_diagnosis_probe_unrecognized(tmp_path, monkeypatch, probe_kind):
    """探针不可用/抛异常 -> 占用者行固定写「未识别」, 异常类型与消息不变, 失败只写 DEBUG"""
    from auto_qb.infra.port_owner import PortProbe
    from auto_qb.webui.server import lifecycle

    if probe_kind == "unavailable":

        def probe(host, _port):
            return PortProbe.unavailable("ss 不可用")
    else:

        def probe(host, _port):
            raise RuntimeError("probe boom")

    mgr, port, exc, cap = _start_webui_on_taken_port(tmp_path, monkeypatch, probe)
    diag = cap.text
    assert "WEB UI 启动失败诊断" in diag
    assert "占用者: 未识别(本机无 ss/lsof 或查询超时)" in diag, "不可用时不得静默省略占用者行"
    assert "pid=" not in diag, "未识别分支不得伪造占用者"
    assert f"web.host=127.0.0.1, web.port={port}" in diag
    # 异常类型/消息与探针结果无关
    assert isinstance(exc, lifecycle.WebUIBindError)
    message = str(exc)
    assert message == lifecycle._bind_message(mgr.config.web)
    assert "未识别" not in message and "probe boom" not in message and "占用者" not in message
    if probe_kind == "raises":
        assert any(r.levelno == logging.DEBUG and "探针异常" in r.getMessage() for r in cap.records), \
            "探针失败只允许写 debug 级"


def test_webui_module_bind_diagnosis_adds_no_error_events(tmp_path, monkeypatch):
    """探针 found / 抛异常两轮对比: auto_qb 树下 ERROR 条数不变 —— 既有 lifecycle 两条保持原样"""
    from auto_qb.infra.port_owner import PortOwner, PortProbe

    def found(host, _port):
        return PortProbe.found(PortOwner(pid=7, name="n", cmdline="c"))

    def raises(host, _port):
        raise RuntimeError("probe boom")

    runs = []
    for probe in (found, raises):
        _mgr, _port, _exc, cap = _start_webui_on_taken_port(tmp_path, monkeypatch, probe, logger_name="auto_qb")
        errors = [r for r in cap.records if r.levelno >= logging.ERROR]
        runs.append(errors)

    # 两轮 ERROR 事件面同形(探针失败不新增 ERROR); 每轮恰是既有两条, 都来自 lifecycle
    assert [len(errs) for errs in runs] == [2, 2]
    assert [{r.name for r in errs} for errs in runs] == [{"auto_qb.web"}, {"auto_qb.web"}]
    messages = [r.getMessage() for r in runs[1]]
    assert any("WEB UI 服务异常退出" in m for m in messages), "既有 _run_server 的 ERROR 必须原样保留"
    assert any("WEB UI 启动失败" in m for m in messages), "既有 start_web_server 的 ERROR 必须原样保留"


# ---------- T2a 覆盖率第三轮: 启动诊断的静默采集与占用者探针降级 ----------


def test_bind_capture_swallows_poisoned_record():
    """_BindFailureCapture.emit 采集失败静默: 记录本身坏掉(文案插值炸)不得逃逸,
    也不得污染已采集的原因(启动期 fail-fast 不被诊断面干扰)"""
    from auto_qb.webui.module import _BindFailureCapture

    capture = _BindFailureCapture()
    poisoned = logging.LogRecord(
        name="t",
        level=logging.ERROR,
        pathname=__file__,
        lineno=1,
        msg="bad %d",
        args=("not-a-number", ),
        exc_info=None
    )
    capture.emit(poisoned)  # 不得抛(采集器永不干扰业务日志)
    assert capture.reason == "", "坏记录不得伪造原因"
    # 正常记录仍可采集(对照: 同一 handler 对好记录工作)
    good = logging.LogRecord(
        name="t", level=logging.ERROR, pathname=__file__, lineno=1, msg="OSError: bind", args=(), exc_info=None
    )
    capture.emit(good)
    assert capture.reason == "OSError: bind"


def test_port_owner_line_absent_state(monkeypatch):
    """占用者探针回 STATE_ABSENT(端口已释放) -> 固定降级文案「未找到」(不写未识别)"""
    from auto_qb.infra.port_owner import STATE_ABSENT
    from auto_qb.webui import module as webui_module

    monkeypatch.setattr(
        "auto_qb.webui.module.describe_port_owner",
        lambda host, port: SimpleNamespace(state=STATE_ABSENT, owner=None),
    )
    assert webui_module._port_owner_line("127.0.0.1", 18080) == "占用者: 未找到(端口可能刚被释放)"
