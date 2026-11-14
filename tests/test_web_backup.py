"""test_web_backup 测试计划: 配置备份 bundle 导出 GET /api/backup/export(计划 26-11-14-0624 S1)

## 测试计划(每个测试函数一条)
- test_backup_export_requires_auth: 无 Bearer 一律 401(与其它 /api/* 同走 factory 全局鉴权闸)
- test_backup_export_bundle_shape_and_masks: bundle 顶层形状(format/bundle_version/created_at/
  app_version)+ 敏感键全掩码(主 qB 密码 / tracker passkey / hr.token / transfer targets 条目
  password+api_key 同一哨兵; web.token 留空不掩码)+ 全响应无任何明文凭据(D2 掩码不出机);
  契约负例钉死: 普通列表(非 targets)不下钻(条目内 password 键原样保留), targets 条目
  空值不掩码
- test_backup_export_mask_diff_only_sensitive_lines: R7 byte 级钉 —— config_yaml 与
  dump(load(原文)) 无掩码基线逐行比对: 行数一致, 差异行必是敏感值行(掩码侧含哨兵),
  前注/行尾注释/空行/尾换行全保留
- test_backup_export_mask_failure_500_no_secret_echo: 重复键坏 YAML(ruamel DuplicateKeyError
  路径) -> 500, 且响应不含异常文本回显的任何明文凭据(500 detail 只留固定文案 + 类型名,
  绝不拼 {e} —— 异常文本逐字回显重复键明文值, D2)
- test_mask_yaml_text_non_mapping_returns_empty: mask_yaml_text 直调 —— 空串/列表 YAML/
  标量 YAML 输入一律返回 ""(非映射当空, 与 read_tree 同口径, 堵明文原样返回的 D2 旁路)
- test_backup_export_gtm_offline_section_null: 工具离线(agent 探活 None) -> bundle["gtm"]
  is None(缺段 = 不含该面), 且 config_yaml/webui_keys 照常导出(离线不致命, D9)
- test_backup_export_missing_config_file_empty_section: config.yml 不存在 -> config_yaml 段
  为空串, 其余段(webui_keys/gtm/顶层形状)照常导出
- test_backup_export_mask_exception_wrapped_500: monkeypatch mask_yaml_text 抛异常 -> 500,
  detail 含「掩码化失败」与异常类型名, 不含异常文本(泄敏面同上)
- test_backup_export_gtm_online_section: 工具在线 -> gtm 段 = {config 合并树, tool_version,
  captured_at}, 与 GET /api/traffic/monitor/status 同源(同走 _source_status 单点)
- test_backup_export_gtm_echo_not_dict_null: 探活成功但 /status 回显非 200(如密钥不符)/
  ToolUnreachable 竞态 -> bundle["gtm"] is None 且整体 200(离线不致命, D9)
- test_backup_export_keys_section_matches_get_api_keys: webui_keys 段形状与 GET /api/keys
  逐字一致(同走 load_keys_doc 单点)
"""
import io
import json
import re
from datetime import datetime
from pathlib import Path

import pytest
import yaml

from auto_qb import __version__
from auto_qb.config import writer as config_writer
from auto_qb.config.writer import MASK_SENTINEL, SENSITIVE_KEY_PARTS as _SENSITIVE_PARTS, _build_yaml
from auto_qb.core.traffic_source import agent
from auto_qb.webui.server.routes import traffic_monitor as tm_routes

# 导出夹具配置文本(测试独用 tmp 路径, 与生产 config.yml 无关): 覆盖全部敏感键类别
# (qB 密码 / tracker passkey / hr.token / transfer targets 条目 password+api_key) +
# web.token 留空(自动生成 = 非机密, 不掩码) + 前注/行尾注释/空行(R7 注释保留面) +
# 两段契约负例: targets 条目空 password/api_key(空值不掩码) + 普通列表不下钻
# (path_map 条目内 password 键原样保留 —— 与 mask_tree「不进列表」同口径)
BACKUP_CONFIG_TEXT = """\
# 顶部注释: 备份导出夹具
config:
  schema_version: 8
  # qB 凭据(敏感)
  qbittorrent:
    host: 127.0.0.1
    port: 8080
    username: admin
    password: "qb-real-pass"   # 行尾注释
  web:
    token: ""
    skip_check_menu: true
    transfer:
      targets:
        - name: local
          type: local
          base_url: ""
          password: target-secret
          api_key: target-api-key-123
        - name: empty-pass-target
          type: local
          base_url: ""
          password: ""
          api_key: ""
    # 普通列表(非 targets): 掩码不下钻的契约负例
    path_map:
      - password: list-item-pass
        src: a
        dst: b
  hr:
    token: hr-real-token
trackers:
  DemoSite:  # 站点注释
    tags: [demo]
    passkey: tracker-passkey-999
"""

# 夹具里的全部明文凭据(D2: 任一出现在响应即红)。刻意不含 list-item-pass ——
# 普通列表不下钻是既有掩码契约(见 BACKUP_CONFIG_TEXT 注), 该值在掩码测试里断言原样保留
SECRET_PLAINTEXTS = (
    "qb-real-pass",
    "target-secret",
    "target-api-key-123",
    "hr-real-token",
    "tracker-passkey-999",
)

# 重复键坏 YAML(ruamel round-trip loader 抛 DuplicateKeyError; 异常文本回显重复键明文值)
DUP_KEY_CONFIG_TEXT = """\
config:
  schema_version: 8
  qbittorrent:
    host: 127.0.0.1
    port: 8080
    username: admin
    password: "dup-first-pass"
    password: "dup-second-pass"
"""


def _export(mgr, client):
    """带鉴头的导出响应(bundle 测试共用的单行入口)"""
    return client.get("/api/backup/export", headers={"Authorization": f"Bearer {mgr.web.token}"})


def _online_gtm_env(mgr, tmp_path, monkeypatch):
    """探活成功 + 工具密钥就绪的 gtm 环境(在线/回显缺失两类用例共用)"""
    token_file = tmp_path / "gtm" / "monitor.token"
    token_file.parent.mkdir(parents=True, exist_ok=True)
    token_file.write_text("tool-token-abc\n", encoding="utf-8")
    monkeypatch.setattr(
        agent,
        "probe",
        lambda timeout=None: agent.ToolEndpoint(
            base_url="http://127.0.0.1:8099",
            token_path=str(token_file),
            data_dir=str(tmp_path / "gtm-data"),
            version="0.1.0",
            pid=4321,
            autostart_registered=True,
            autostart_error=None,
        ),
    )
    monkeypatch.setattr(agent, "resolve_launch_target", lambda conf: object())


def test_backup_export_requires_auth(web_env):
    """无 Bearer 一律 401(鉴权由 factory 全局 dependencies 单点覆盖, 端点不另挂)"""
    _, client = web_env
    assert client.get("/api/backup/export").status_code == 401


@pytest.mark.parametrize("web_env", [{"config_text": BACKUP_CONFIG_TEXT}], indirect=True)
def test_backup_export_bundle_shape_and_masks(web_env):
    """bundle 形状(§03) + 敏感键全掩码 + 全响应无明文凭据(D2)+ 列表不下钻/空值不掩码负例"""
    mgr, client = web_env
    r = _export(mgr, client)
    assert r.status_code == 200, r.text
    assert r.headers["content-type"].startswith("application/json")
    # 可下载 JSON: 文件名 auto-qb-backup-<YYYYMMDD-HHMMSS>.json(Content-Disposition 先例同 .torrent 导出)
    cd = r.headers["content-disposition"]
    assert re.search(r'filename="auto-qb-backup-\d{8}-\d{6}\.json"', cd), cd
    bundle = r.json()
    assert bundle["format"] == "auto-qb-config-bundle"
    assert bundle["bundle_version"] == 1
    assert bundle["app_version"] == __version__
    datetime.fromisoformat(bundle["created_at"])  # 可解析的时间戳(带时区)
    # 敏感键全掩码(含 transfer targets 条目; 与 mask_tree 同一套哨兵)
    tree = yaml.safe_load(bundle["config_yaml"])
    qb = tree["config"]["qbittorrent"]
    web = tree["config"]["web"]
    assert qb["password"] == MASK_SENTINEL
    assert tree["config"]["hr"]["token"] == MASK_SENTINEL
    assert tree["trackers"]["DemoSite"]["passkey"] == MASK_SENTINEL
    targets = web["transfer"]["targets"]
    assert targets[0]["password"] == MASK_SENTINEL
    assert targets[0]["api_key"] == MASK_SENTINEL
    # 空值不掩码(web.token 留空 = 自动生成; targets 条目空 password/api_key 同口径)
    assert web["token"] == ""
    assert targets[1]["password"] == "" and targets[1]["api_key"] == ""
    # 普通列表(非 targets)不下钻: 条目内 password 键原样保留(掩码契约与 mask_tree 同一口径)
    assert web["path_map"][0]["password"] == "list-item-pass"
    # 非敏感键原样
    assert qb["username"] == "admin" and qb["host"] == "127.0.0.1"
    # ui_prefs 服务端零接触(D3): 响应不含该段, 前端并入后再落盘
    assert "ui_prefs" not in bundle
    # 掩码不出机: 整个响应文本(含 headers 不看, body 全量)不含任何明文凭据
    for secret in SECRET_PLAINTEXTS:
        assert secret not in r.text, secret


@pytest.mark.parametrize("web_env", [{"config_text": BACKUP_CONFIG_TEXT}], indirect=True)
def test_backup_export_mask_diff_only_sensitive_lines(web_env):
    """R7 byte 级钉: 与 dump(load(原文)) 无掩码基线逐行比对, 差异仅敏感值行 + 注释全保留"""
    mgr, client = web_env
    with open(mgr.config_path, "r", encoding="utf-8") as f:
        raw = f.read()
    # 无掩码基线: 同一 ruamel 实例工厂 load+dump(剔除 ruamel 归一化差异, 基线口径见 mask_yaml_text docstring)
    ry = _build_yaml()
    baseline_buf = io.StringIO()
    ry.dump(ry.load(io.StringIO(raw)), baseline_buf)
    baseline = baseline_buf.getvalue()

    bundle = _export(mgr, client).json()
    masked = bundle["config_yaml"]

    base_lines = baseline.splitlines()
    mask_lines = masked.splitlines()
    assert len(base_lines) == len(mask_lines), "掩码不得增删行"
    for i, (bl, ml) in enumerate(zip(base_lines, mask_lines)):
        if bl == ml:
            continue
        # 差异行必是敏感值行: 掩码侧含哨兵, 基线侧键名含敏感片段
        assert MASK_SENTINEL in ml, f"第 {i + 1} 行非敏感值被改动: {bl!r} -> {ml!r}"
        key = bl.split(":", 1)[0].strip().lower()
        assert any(part in key for part in _SENSITIVE_PARTS), f"第 {i + 1} 行非敏感值被改动: {bl!r} -> {ml!r}"
    # 注释 byte 级保留(前注 / 行尾注释 / 嵌套注释) + 尾换行形态一致
    for note in ("# 顶部注释: 备份导出夹具", "# qB 凭据(敏感)", "# 行尾注释", "# 站点注释"):
        assert note in masked, note
    assert masked.endswith("\n") == baseline.endswith("\n")


@pytest.mark.parametrize("web_env", [{"config_text": DUP_KEY_CONFIG_TEXT}], indirect=True)
def test_backup_export_mask_failure_500_no_secret_echo(web_env):
    """重复键坏 YAML(DuplicateKeyError) -> 500, 响应不含异常文本回显的明文凭据(D2)"""
    mgr, client = web_env
    r = _export(mgr, client)
    assert r.status_code == 500
    assert "掩码化失败" in r.text
    # 异常文本会逐字回显重复键的明文值 —— detail 进响应 = 泄敏, 两个明文凭据都不得出现
    for secret in ("dup-first-pass", "dup-second-pass"):
        assert secret not in r.text, secret


def test_mask_yaml_text_non_mapping_returns_empty():
    """mask_yaml_text 直调: 空串/列表/标量文档一律返回 ""(非映射当空, 堵明文旁路)"""
    from auto_qb.config.writer import mask_yaml_text

    assert mask_yaml_text("") == ""
    assert mask_yaml_text("- a\n- b\n") == ""
    assert mask_yaml_text("just-a-scalar\n") == ""


def test_backup_export_gtm_offline_section_null(web_env, monkeypatch):
    """工具离线(agent 探活 None) -> bundle["gtm"] is None, 其余段照常导出(D9 离线不致命)"""
    mgr, client = web_env
    monkeypatch.setattr(agent, "probe", lambda timeout=None: None)
    monkeypatch.setattr(agent, "resolve_launch_target", lambda conf: None)
    r = _export(mgr, client)
    assert r.status_code == 200, r.text
    bundle = r.json()
    assert bundle["gtm"] is None
    assert bundle["config_yaml"] != ""
    assert bundle["webui_keys"]["schema_version"] == 1


@pytest.mark.parametrize("web_env", [{"config_text": BACKUP_CONFIG_TEXT}], indirect=True)
def test_backup_export_missing_config_file_empty_section(web_env, monkeypatch):
    """config.yml 不存在 -> config_yaml 段空串, 其余段照常导出(不致命)"""
    mgr, client = web_env
    Path(mgr.config_path).unlink()
    monkeypatch.setattr(agent, "probe", lambda timeout=None: None)
    monkeypatch.setattr(agent, "resolve_launch_target", lambda conf: None)
    r = _export(mgr, client)
    assert r.status_code == 200, r.text
    bundle = r.json()
    assert bundle["config_yaml"] == ""
    assert bundle["format"] == "auto-qb-config-bundle"
    assert bundle["webui_keys"]["schema_version"] == 1
    assert bundle["gtm"] is None


@pytest.mark.parametrize("web_env", [{"config_text": BACKUP_CONFIG_TEXT}], indirect=True)
def test_backup_export_mask_exception_wrapped_500(web_env, monkeypatch):
    """掩码化抛异常 -> 500, detail 含「掩码化失败」+ 类型名, 不含异常文本(泄敏面同 500 收口)"""
    mgr, client = web_env

    def boom(text):
        raise RuntimeError("leak-exception-text")

    monkeypatch.setattr(config_writer, "mask_yaml_text", boom)  # 端点内延迟导入, 调用时现取属性
    r = _export(mgr, client)
    assert r.status_code == 500
    assert "掩码化失败" in r.text
    assert "RuntimeError" in r.text
    assert "leak-exception-text" not in r.text


@pytest.mark.parametrize("web_env", [{"config_text": BACKUP_CONFIG_TEXT}], indirect=True)
def test_backup_export_gtm_online_section(web_env, tmp_path, monkeypatch):
    """工具在线 -> gtm 段 = {config 合并树, tool_version, captured_at}(与 /api/traffic/monitor/status 同源)"""
    mgr, client = web_env
    _online_gtm_env(mgr, tmp_path, monkeypatch)
    tool_config = {"sample_interval": 5.0, "http_host": "127.0.0.1", "http_port": 8099}
    monkeypatch.setattr(tm_routes, "_call_tool", lambda *a, **k: (200, {"ok": True, "config": tool_config}))
    bundle = _export(mgr, client).json()
    assert bundle["gtm"]["config"] == tool_config
    assert bundle["gtm"]["tool_version"] == "0.1.0"
    datetime.fromisoformat(bundle["gtm"]["captured_at"])


@pytest.mark.parametrize("web_env", [{"config_text": BACKUP_CONFIG_TEXT}], indirect=True)
def test_backup_export_gtm_echo_not_dict_null(web_env, tmp_path, monkeypatch):
    """探活成功但 /status 回显非 200 / ToolUnreachable 竞态 -> gtm 段 None 且整体 200(D9 不致命)"""
    mgr, client = web_env
    _online_gtm_env(mgr, tmp_path, monkeypatch)
    # 分支一: 工具 /status 回非 200(如密钥不符) -> reachable 但 status=None -> gtm 段 None
    monkeypatch.setattr(tm_routes, "_call_tool", lambda *a, **k: (401, {"error": "invalid token"}))
    r = _export(mgr, client)
    assert r.status_code == 200, r.text
    assert r.json()["gtm"] is None
    assert r.json()["config_yaml"] != ""

    # 分支二: 探活与 /status 之间工具掉线(ToolUnreachable) -> 展示面降级 -> gtm 段 None
    def boom(*a, **k):
        raise tm_routes.ToolUnreachable("connection refused")

    monkeypatch.setattr(tm_routes, "_call_tool", boom)
    r2 = _export(mgr, client)
    assert r2.status_code == 200, r2.text
    assert r2.json()["gtm"] is None


@pytest.mark.parametrize("web_env", [{"config_text": BACKUP_CONFIG_TEXT}], indirect=True)
def test_backup_export_keys_section_matches_get_api_keys(web_env):
    """webui_keys 段形状与 GET /api/keys 逐字一致(同走 load_keys_doc 单点)"""
    mgr, client = web_env
    doc = {"schema_version": 1, "template": "aqb-default", "overrides": {"act-pause": "Ctrl+KeyP"}}
    assert client.put("/api/keys", headers={"Authorization": f"Bearer {mgr.web.token}"}, json=doc).status_code == 200
    keys_doc = client.get("/api/keys", headers={"Authorization": f"Bearer {mgr.web.token}"}).json()
    bundle = _export(mgr, client).json()
    assert bundle["webui_keys"] == keys_doc
    assert json.loads(json.dumps(bundle["webui_keys"])) == doc
