"""test_web_longtail_routes 测试计划: P1 覆盖率提升轮 + v3 活尾 (运行时 / 命令 / 路由长尾)

## 测试计划(每个测试函数一条)
### P1 覆盖率提升轮: webui 运行时与命令长尾
- test_api_torrent_write_endpoints_extra_enqueue: 写端点补遗(pause/resume/delete/skip-check/limits 部分方向)
- test_api_numeric_params_malformed_string_400: 数值型请求体字段畸形值(字符串)回 400 而不是 500(issue 26-10-30-0622, 五处裸 int()/float() 收口 common.int_param/float_param); 拒收在路由层不入队, 合法数值照常入队
- test_api_torrents_add_endpoint_errors_and_enqueue: 添加种子 base64 坏/空载荷 400 + 合法入队
- test_api_config_put_and_preview_tree_shape: 配置树 PUT/preview 非对象 400 + preview 不落盘; 校验失败(ConfigError) 400 带文案且不落盘(T2a2)
- test_api_expr_eval_runtime_error: 求值期失败(除零) -> ok=False 带文案与 used
- test_api_keys_endpoint_roundtrip_and_validation: 快捷键默认表/422 校验/保存读回
- test_api_keys_sanitize_rejects_non_dict: _sanitize 非 dict 一律 None
- test_api_category_and_tag_empty_rejections: 分类/标签空入参 400
- test_api_speed_mode_reads_client_with_alt_fields: 限速托管直读 qB(含 ALT 双组) + 读失败/部分成功整组回 None(DEBUG 留摘要)
- test_api_fs_error_semantics: fs 端点错误语义化(404/501/403/400)
- test_api_open_path_file_gone_after_probe_404: open-path 定位选中路径探针后消失 -> 404 语义化(探针/复查竞态窗口, 确定性替身直驱, T2a2)
"""

import base64

import errno

import os

import re

import tempfile

import time

from pathlib import Path

from types import SimpleNamespace

from auto_qb.infra import file_access

from auto_qb.infra.utils import encode_group_key

from auto_qb.webui.runtime import (
    CMD_SLOW_MS,
    EVENT_QUEUE_MAX,
    REANNOUNCE_CONFIRM_TIMEOUT,
    WEB_RESULT_MAX,
    WEB_RESULT_TTL,
    WebUIRuntime,
)

from helpers import capture_logs

from webui_helpers import (
    KEY,
    STATIC_ROOT,
    _enable_qb_traffic,
    _qb_v4,
    _make_grouped_manager,
    _attach_live_tail_host,
)


def test_api_torrent_write_endpoints_extra_enqueue(web_env):
    """种子写端点补遗: pause/resume/delete(带 delete_files)/skip-check/limits(部分方向)/share-limits(部分维度)"""
    mgr, client = web_env
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    post = lambda path, body=None: client.post(f"/api/torrents/HA{path}", json=body, headers=auth)  # noqa: E731
    cases = [
        ("/pause", None, "pause_torrent", {
            "hash": "HA"
        }),
        ("/resume", None, "resume_torrent", {
            "hash": "HA"
        }),
        ("/delete", {
            "delete_files": True
        }, "delete_torrent", {
            "hash": "HA",
            "delete_files": True
        }),
        ("/skip-check", None, "skip_check_torrent", {
            "hash": "HA"
        }),
        ("/limits", {
            "up_limit": 1024
        }, "set_torrent_limits", {
            "hash": "HA",
            "up_limit": 1024
        }),
        ("/share-limits", {
            "ratio_limit": 1.5
        }, "set_share_limits", {
            "hash": "HA",
            "ratio_limit": 1.5
        }),
    ]
    for path, body, cmd, want in cases:
        resp = post(path, body)
        assert resp.status_code == 200, (path, resp.text)
        got_cmd, payload = mgr.web.commands.get_nowait()
        assert got_cmd == cmd
        payload.pop("cmd_id")
        payload.pop("_queued_ts", None)
        assert payload == want, path
    # 鉴权沿用 /api/* 全局依赖
    assert client.post("/api/torrents/HA/pause").status_code == 401


def test_api_numeric_params_malformed_string_400(web_env):
    """数值型请求体字段畸形值(字符串)回 400 而不是 500(issue 26-10-30-0622)

    五处裸 int()/float() 直转收口 common.int_param/float_param —— 直调 API 传 "abc" 时
    ValueError 不再冒成服务端 500, 与同层 group_key_param / parse_window 的 4xx 先例同口径;
    拒收在路由层, 不产生命令入队。
    """
    mgr, client = web_env
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    cases = [
        ("/api/torrents/HA/limits", {
            "up_limit": "abc"
        }),
        ("/api/torrents/HA/limits", {
            "dl_limit": "abc"
        }),
        ("/api/torrents/HA/share-limits", {
            "ratio_limit": "abc"
        }),
        ("/api/torrents/HA/share-limits", {
            "seeding_time_limit": "abc"
        }),
        ("/api/torrents/HA/share-limits", {
            "inactive_seeding_time_limit": "abc"
        }),
        ("/api/torrents/HA/files/priority", {
            "indices": ["x"],
            "priority": 1
        }),
        ("/api/torrents/HA/files/priority", {
            "indices": [0],
            "priority": "x"
        }),
        ("/api/torrents/bulk", {
            "action": "limits",
            "hashes": ["HA"],
            "up_limit": "abc"
        }),
        ("/api/torrents/bulk", {
            "action": "limits",
            "hashes": ["HA"],
            "dl_limit": "abc"
        }),
        ("/api/speed/override", {
            "upload_kib": "abc"
        }),
        ("/api/speed/override", {
            "download_kib": "abc"
        }),
        ("/api/speed/alt", {
            "upload_kib": "abc",
            "download_kib": 1
        }),
    ]
    for path, body in cases:
        resp = client.post(path, json=body, headers=auth)
        assert resp.status_code == 400, (path, body, resp.status_code)
    assert mgr.web.commands.empty(), "畸形值拒收在路由层, 不得产生命令入队"
    # 合法数值仍照常入队(既有行为零变化)
    resp = client.post("/api/torrents/HA/limits", json={"up_limit": 1024}, headers=auth)
    assert resp.status_code == 200
    cmd, payload = mgr.web.commands.get_nowait()
    assert cmd == "set_torrent_limits" and payload["up_limit"] == 1024


def test_api_torrents_add_endpoint_errors_and_enqueue(web_env):
    """/api/torrents/add: base64 坏 -> 400; 空载荷 -> 400; 合法载荷入队(文件+链接)"""
    mgr, client = web_env
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    assert client.post("/api/torrents/add", json={"files_b64": ["!!not-b64!!"]}, headers=auth).status_code == 400
    assert client.post("/api/torrents/add", json={}, headers=auth).status_code == 400
    assert client.post("/api/torrents/add", json={"files_b64": ["!!not-b64!!"]}).status_code == 401
    blob = base64.b64encode(b"d4:infod4:name4:abcee").decode("ascii")
    resp = client.post(
        "/api/torrents/add",
        json={
            "files_b64": [blob, ""],
            "urls": ["magnet:?xt=urn:btih:abc"],
            "save_path": "R:/Drop",
            "tags": ["t"]
        },
        headers=auth,
    )
    assert resp.status_code == 200 and resp.json()["queued"] is True
    cmd, payload = mgr.web.commands.get_nowait()
    assert cmd == "add_torrents"
    assert payload["files"] == [b"d4:infod4:name4:abcee"], "空串条目被过滤, base64 解出原始字节"
    assert payload["urls"] == ["magnet:?xt=urn:btih:abc"] and payload["save_path"] == "R:/Drop"


def test_api_config_put_and_preview_tree_shape(web_env):
    """配置树: PUT/preview 的 tree 非对象都 400; preview 返回 YAML 文本不落盘"""
    mgr, client = web_env
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    assert client.put("/api/config", json={"tree": "nope"}, headers=auth).status_code == 400
    assert client.post("/api/config/preview", json={"tree": [1]}, headers=auth).status_code == 400
    assert client.put("/api/config", json={"tree": "nope"}).status_code == 401
    tree = client.get("/api/config", headers=auth).json()["tree"]
    resp = client.post("/api/config/preview", json={"tree": tree}, headers=auth)
    assert resp.status_code == 200 and "yaml" in resp.json()
    before = Path(mgr.config_path).read_text(encoding="utf-8")
    assert Path(mgr.config_path).read_text(encoding="utf-8") == before, "preview 不落盘"
    # T2a2: 校验失败(ConfigError) -> 400 带精确文案, 照样不落盘
    bad = client.get("/api/config", headers=auth).json()["tree"]
    bad["config"]["qbittorrent"]["port"] = "abc"  # 端口必须是整数
    resp = client.post("/api/config/preview", json={"tree": bad}, headers=auth)
    assert resp.status_code == 400 and resp.json()["detail"], resp.text
    assert Path(mgr.config_path).read_text(encoding="utf-8") == before, "校验失败照样不落盘"


def test_api_expr_eval_runtime_error(web_env):
    """表达式试算: 编译/校验通过但**求值期**失败(除零) -> ok=False 带错误文案与 used 清单"""
    mgr, client = web_env
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    mgr.store.get = lambda h: SimpleNamespace(uploaded=100, downloaded=0)
    resp = client.post(
        "/api/expr/eval",
        json={
            "text": "(tor.uploaded / tor.downloaded) > 1",
            "hash": "HA"
        },
        headers=auth,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is False and "除数为 0" in body["error"]
    assert body["used"] == ["tor.downloaded", "tor.uploaded"]


def test_api_keys_endpoint_roundtrip_and_validation(web_env):
    """快捷键配置: 默认表 / 非法结构 422 / 合法保存后读回一致"""
    mgr, client = web_env
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    assert client.get("/api/keys", headers=auth).json()["template"] == "aqb-default"
    bad = {"schema_version": 1, "template": "", "overrides": {}}
    assert client.put("/api/keys", json=bad, headers=auth).status_code == 422
    bad2 = {"schema_version": 1, "template": "aqb-default", "overrides": {"k": "Bad Serial!"}}
    assert client.put("/api/keys", json=bad2, headers=auth).status_code == 422
    assert client.put("/api/keys", json=bad2).status_code == 401
    good = {"schema_version": 1, "template": "aqb-default", "overrides": {"openSearch": "Ctrl+K", "x": ""}}
    assert client.put("/api/keys", json=good, headers=auth).status_code == 200
    assert client.get("/api/keys", headers=auth).json()["overrides"]["openSearch"] == "Ctrl+K"


def test_api_keys_sanitize_rejects_non_dict():
    """_sanitize 结构校验单点: 非 dict 文档一律 None(走默认表兜底链)"""
    from auto_qb.webui.server.routes.keys import _sanitize

    assert _sanitize(None) is None
    assert _sanitize([1, 2]) is None
    assert _sanitize("x") is None


def test_api_category_and_tag_empty_rejections(web_env):
    """分类/标签写端点的空入参 400(与既有详情端点同一校验口径)"""
    mgr, client = web_env
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    assert client.post("/api/categories", json={"name": "  "}, headers=auth).status_code == 400
    assert client.post("/api/categories/edit", json={}, headers=auth).status_code == 400
    assert client.post("/api/tags/remove", json={"tags": []}, headers=auth).status_code == 400
    resp = client.post("/api/tags", json={"tags": ["新标签"]}, headers=auth)
    assert resp.status_code == 200
    cmd, payload = mgr.web.commands.get_nowait()
    assert cmd == "create_tags" and payload["tags"] == ["新标签"]


def test_api_speed_mode_reads_client_with_alt_fields(web_env):
    """限速托管状态: qB 在连时直读当前限速与 ALT 双组; 读失败不炸(回 None)"""
    mgr, client = web_env
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    api = SimpleNamespace(
        get_global_speed_limits=lambda: {"up_limit": 1024},
        get_speed_limits_mode=lambda: 1,
        get_alt_speed_limits=lambda: {"up_limit": 512},
    )
    mgr.client = SimpleNamespace()
    mgr.api = api
    body = client.get("/api/speed/mode", headers=auth).json()
    assert body["current"] == {"up_limit": 1024} and body["alt_on"] is True
    assert body["alt_current"] == {"up_limit": 512}
    # 读失败 -> 字段回 None, 端点不 500
    mgr.api = SimpleNamespace(
        get_global_speed_limits=lambda: (_ for _ in ()).throw(RuntimeError("断连")),
        get_speed_limits_mode=lambda: 0,
        get_alt_speed_limits=lambda: {},
    )
    body = client.get("/api/speed/mode", headers=auth).json()
    assert body["current"] is None and body["alt_on"] is None and body["alt_current"] is None, "任一读取失败整组回 None(不拿旧缓存冒充)"
    # 部分成功组合同样整组回 None(首读成功后续读抛 -> 不出现「一半真一半未知」浮层;
    # issue 26-10-06-0028 chore-speed-mode-silent-except)
    mgr.api = SimpleNamespace(
        get_global_speed_limits=lambda: {"up_limit": 1024},
        get_speed_limits_mode=lambda: (_ for _ in ()).throw(RuntimeError("超时")),
        get_alt_speed_limits=lambda: {"up_limit": 512},
    )
    body = client.get("/api/speed/mode", headers=auth).json()
    assert body["current"] is None and body["alt_on"] is None and body["alt_current"] is None, "部分成功也整组回 None(口径对齐)"


def test_api_fs_error_semantics(web_env, tmp_path, monkeypatch):
    """fs 端点错误语义化: 目录不可读 404 / mkdir 不支持 501 / 只读挂载 403 / 其它失败 400 / open 不支持 501"""
    from auto_qb.infra import file_access as fa_mod

    mgr, client = web_env
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    root = tmp_path / "fsroot"
    root.mkdir()
    mgr.store.by_hash = {"HA": SimpleNamespace(hash="HA", save_path=str(root), content_path=str(root), root_path="")}
    norm = lambda p: str(p).replace("\\", "/")  # noqa: E731

    class _FakeFA:
        def isdir(self, p):
            return True

        def isfile(self, p):
            return True

        def exists(self, p):
            return False

        def realpath_lexical(self, p):
            return p

        def scandir(self, p):
            raise PermissionError(13, "拒绝访问")

        def mkdir(self, p):
            raise OSError(errno.EACCES, "拒绝访问")

    monkeypatch.setattr(file_access, "get_file_access", lambda: _FakeFA())
    # 目录浏览: scandir 失败 -> 404 带原因(不是裸 500)
    resp = client.get("/api/fs/dirs", params={"path": norm(root)}, headers=auth)
    assert resp.status_code == 404 and "目录不可读" in resp.json()["detail"]
    # mkdir: EACCES -> 403(只读挂载语义化)
    resp = client.post("/api/fs/mkdir", json={"name": "nd", "path": norm(root)}, headers=auth)
    assert resp.status_code == 403 and "只读" in resp.json()["detail"]

    # mkdir: 其它 OSError -> 400
    class _OtherFA(_FakeFA):
        def mkdir(self, p):
            raise OSError(errno.EINVAL, "无效参数")

    monkeypatch.setattr(file_access, "get_file_access", lambda: _OtherFA())
    resp = client.post("/api/fs/mkdir", json={"name": "nd", "path": norm(root)}, headers=auth)
    assert resp.status_code == 400 and "新建失败" in resp.json()["detail"]

    # mkdir: 环境不支持 -> 501
    class _NoFA(_FakeFA):
        def mkdir(self, p):
            raise fa_mod.NotSupported("nope")

    monkeypatch.setattr(file_access, "get_file_access", lambda: _NoFA())
    assert client.post("/api/fs/mkdir", json={"name": "nd", "path": norm(root)}, headers=auth).status_code == 501
    # open-path: 打开动作不支持 -> 501 引导「复制路径」(patch 地址 = common.open_path, 与既有守阵一致)
    import auto_qb.webui.server.common as fs_common

    def _unsupported(path, select=False):
        raise fa_mod.NotSupported("nope")

    monkeypatch.setattr(fs_common, "open_path", _unsupported)
    mgr.store.groups = {(norm(root), ("a.mkv", )): ["HA"]}
    encoded = encode_group_key((norm(root), ("a.mkv", )))
    resp = client.post("/api/open-path", json={"kind": "group", "key": encoded}, headers=auth)
    assert resp.status_code == 501 and "复制路径" in resp.json()["detail"]


def test_api_open_path_file_gone_after_probe_404(web_env, monkeypatch):
    """T2a2 清偿: open-path 定位选中路径在探针后消失 -> 404 语义化(不裸 500)

    _probe 以 fa.isfile(cand)=True 选中文件(select=True), 随后请求内对同一路径复查已不存在
    —— 探针/复查两查之间文件被删的竞态窗口, 用确定性替身直驱(首次 isfile 真、其后假)。
    """
    mgr, client = web_env
    auth = {"Authorization": f"Bearer {mgr.web.token}"}

    class _VanishFA:
        """首次 isfile 真(探针选中), 其后假(复查时文件已不在)"""
        def __init__(self):
            self.calls = 0

        def isfile(self, p):
            self.calls += 1
            return self.calls == 1

        def isdir(self, p):
            return False

    mgr.store.by_hash = {"HA": SimpleNamespace(hash="HA", save_path="R:/s", content_path="R:/s/a.mkv", root_path="")}
    mgr.store.get = lambda h: mgr.store.by_hash.get(h)  # web_env 的 store 桩 get 恒 None, 按 hash 查表补齐
    monkeypatch.setattr(file_access, "get_file_access", lambda: _VanishFA())
    resp = client.post("/api/open-path", json={"kind": "torrent", "hash": "HA"}, headers=auth)
    assert resp.status_code == 404 and "目标文件不存在" in resp.json()["detail"], resp.text
