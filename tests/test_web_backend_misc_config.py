"""test_web_backend_misc_config 测试计划: WEB 后端杂项: config / token / sites / 分组视图 / 错误原因

## 测试计划(每个测试函数一条)
- test_config_schema_endpoint: 图形化配置元数据端点(分组/插件/热重载级别)
- test_config_tree_roundtrip: 配置树读取/保存写回文件并投递热重载命令
- test_config_tree_invalid_rejected: 非法配置树 -> 400 且不写回
- test_config_tree_requires_config_root: 缺少 config 根段 -> 400
- test_config_tree_restart_field_fallback: R 级字段(data_dir)提交后被回退为磁盘旧值
- test_config_tree_preserves_comments: round-trip 写盘保留已有键的注释
- test_config_tree_masks_secrets: /api/config 掩码敏感字段, 且"读取→原样保存"不会把密码写成占位串
- test_config_tree_masks_transfer_target_passwords: /api/config 对 web.transfer.targets[].password 同哨兵掩码(D4) —— GET 不回明文, 原样保存磁盘仍是真密码且无哨兵
"""

import logging

import os

import re

import time

from types import SimpleNamespace

import pytest

from auto_qb.infra.utils import decode_group_key, encode_group_key

from webui_helpers import WEB_ENV_CONFIG_TEXT, _make_web_manager, STATIC_ROOT, _UI_ALL, _ui_aggregate


def test_config_schema_endpoint(web_env):
    """图形化配置元数据端点: 分组/站点字段/规则字段/插件表/热重载级别齐全"""
    mgr, client = web_env
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    data = client.get("/api/config/schema", headers=auth).json()
    # 2026-09-26: 日志/WebUI/通知 三个短段并入 basic(设置页不再单列三张卡)
    # 26-10-06 用户要求重排: 站点提到第二(紧跟常规), 限速 / HR 在线核实 后置到末尾
    # 26-10-18(计划 26-10-18-0813 B1/D17): 「流量图」「全局流量来源」「限速曲线」三组并成
    # 一组 traffic_limit(「流量与限速」) —— 8 -> 6 组; 三组共用一份流量口径, 分成三张首页卡会
    # 让「关掉来源后曲线与图一起停」这件事在三处各说一半。合并卡内三区见 traffic-card.html
    assert [g["key"]
            for g in data["groups"]] == ["basic", "trackers", "maintenance", "traffic_limit", "rules", "hr_check"]
    tl = next(g for g in data["groups"] if g["key"] == "traffic_limit")
    assert [f["key"] for f in tl["fields"]] == ["traffic_source", "global_speed_limit_curve", "qb_traffic"], \
        "合并组的字段序 = 卡内区序(来源 -> 限速曲线 -> 流量图采样)"
    assert [f["key"] for f in data["groups"][0]["fields"]][-3:] == ["log", "web", "notify"]
    # 2026-09-28: 三段在「常规」页必须各自成块展示分类名(「常规/日志」而非并入「常规/常规」) ——
    # 成块的前提是不声明 open(open 段被 cfgFlatten 平铺成无标题同级字段, 正是本次回归的根因)
    for f in data["groups"][0]["fields"][-3:]:
        assert f["kind"] == "object" and not f.get("open"), f["key"]
    assert {p["name"] for p in data["plugins"]["condition"]} >= {"size", "tags", "state", "freespace"}
    assert {p["name"] for p in data["plugins"]["action"]} >= {"add_tags", "checking", "reannounce"}
    # 段认领由模块 sections() 派生(W4 级别表退役; 前端不消费, 留给排障对照)
    assert data["levels"]["claimed_sections"]["web"] == ["webui"]
    assert data["levels"]["claimed_sections"]["trackers"] == ["tracker"]
    assert data["levels"]["claimed_sections"]["rules_config"] == ["rules"]


def test_config_tree_roundtrip(web_env):
    """配置树读取与保存: 树为 YAML 同构(标量字符串), 写回文件 + 热重载命令入队"""
    mgr, client = web_env
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    data = client.get("/api/config", headers=auth).json()
    tree = data["tree"]
    assert tree["config"]["qbittorrent"]["host"] == "h", "树应为 YAML 同构的字符串标量"

    tree["config"]["main_tick"] = "5s"
    resp = client.put("/api/config", headers=auth, json={"tree": tree})
    assert resp.status_code == 200, resp.text
    assert resp.json()["applied"] is True
    assert "main_tick" in resp.json()["changes"], "PUT 回执应报变更段路径(W4: 路径字符串)"
    with open(mgr.config_path, encoding="utf-8") as f:
        assert "5s" in f.read(), "新配置应写回 config 文件"
    cmd, payload = mgr.web.commands.get_nowait()
    assert cmd == "reload_config" and payload["config"].main_tick == 5.0


def test_config_tree_invalid_rejected(web_env):
    """非法配置树 -> 400, config 文件不被覆盖"""
    mgr, client = web_env
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    tree = client.get("/api/config", headers=auth).json()["tree"]
    tree["config"]["main_tick"] = "abc"
    before = open(mgr.config_path, encoding="utf-8").read()
    resp = client.put("/api/config", headers=auth, json={"tree": tree})
    assert resp.status_code == 400
    assert "main_tick" in resp.json()["detail"]
    assert open(mgr.config_path, encoding="utf-8").read() == before
    assert mgr.web.commands.empty(), "校验失败不应投递热重载"


def test_config_tree_requires_config_root(web_env):
    """缺少 config 根段 -> 400(防止误删整段被当作"全默认"静默接受)"""
    mgr, client = web_env
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    resp = client.put("/api/config", headers=auth, json={"tree": {"qbittorrent": {}}})
    assert resp.status_code == 400
    assert "config" in resp.json()["detail"]


def test_config_tree_restart_field_fallback(web_env):
    """R 级字段提交后回退为磁盘旧值(进程身份不可热切换), 并回报 restart_required"""
    mgr, client = web_env
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    with open(mgr.config_path, "w", encoding="utf-8") as f:
        f.write("config:\n  schema_version: 8\n  data_dir: old-dir\n  qbittorrent:\n    host: h\n")

    tree = client.get("/api/config", headers=auth).json()["tree"]
    tree["config"]["data_dir"] = "new-dir"
    resp = client.put("/api/config", headers=auth, json={"tree": tree})
    assert resp.status_code == 200, resp.text
    # data_dir 变更会连带派生 state_file(<data_dir>/state.json), 两者同为 R 级
    assert "data_dir" in resp.json()["restart_required"]
    text = open(mgr.config_path, encoding="utf-8").read()
    assert "old-dir" in text, "R 级字段应保留旧值"
    assert "new-dir" not in text, "R 级字段的新值不得写入磁盘"


def test_config_tree_preserves_comments(web_env):
    """round-trip 写盘保留已有键注释(列表项注释为已记录的取舍)"""
    mgr, client = web_env
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    with open(mgr.config_path, "w", encoding="utf-8") as f:
        f.write("config:\n  schema_version: 8\n  # 保留我\n  main_tick: 2s\n  qbittorrent:\n    host: h\n")

    tree = client.get("/api/config", headers=auth).json()["tree"]
    tree["config"]["main_tick"] = "3s"
    resp = client.put("/api/config", headers=auth, json={"tree": tree})
    assert resp.status_code == 200, resp.text
    text = open(mgr.config_path, encoding="utf-8").read()
    assert "# 保留我" in text, "已有键的注释应在 round-trip 写盘后保留"
    assert "3s" in text


def test_config_tree_masks_secrets(web_env):
    """/api/config 掩码敏感字段, 且"读取后原样保存"不会把密码写成占位串

    掩码只影响展示: PUT 侧用磁盘旧值还原哨兵, 因此前端不改密码地保存一遍仍是真密码 ——
    只掩码不还原的话, 一次保存就会毁掉生产配置。
    """
    mgr, client = web_env
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    data = client.get("/api/config", headers=auth).json()
    assert data["masked"] is True
    assert data["tree"]["config"]["qbittorrent"]["password"] == data["mask_sentinel"]
    assert data["tree"]["config"]["qbittorrent"]["host"] == "h", "非敏感字段不掩码"

    resp = client.put("/api/config", headers=auth, json={"tree": data["tree"]})
    assert resp.status_code == 200, resp.text
    text = open(mgr.config_path, encoding="utf-8").read()
    assert "password: p" in text, f"原样保存不得把密码写成占位串: {text}"
    assert data["mask_sentinel"] not in text


_TRANSFER_CONFIG_TEXT = (
    "config:\n"
    "  schema_version: 8\n"
    "  qbittorrent:\n"
    "    host: h\n"
    "    port: 1\n"
    "    username: u\n"
    "    password: p\n"
    "  web:\n"
    "    transfer:\n"
    "      targets:\n"
    "        - name: a\n"
    "          type: qb\n"
    "          base_url: http://a:8080\n"
    "          username: ua\n"
    "          password: pa\n"
    "          enabled: false\n"
)


@pytest.mark.parametrize("web_env", [{"config_text": _TRANSFER_CONFIG_TEXT}], indirect=True)
def test_config_tree_masks_transfer_target_passwords(web_env):
    """/api/config 对 web.transfer.targets[].password 同哨兵掩码(D4): GET 不回明文进浏览器

    掩码往返无损: GET 后条目 password == 哨兵, 原样 PUT 回去(unmask_tree 按 name 配对还原)
    磁盘仍是真密码; 哨兵不落盘。
    """
    mgr, client = web_env
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    data = client.get("/api/config", headers=auth).json()
    sentinel = data["mask_sentinel"]
    targets = data["tree"]["config"]["web"]["transfer"]["targets"]
    assert targets[0]["password"] == sentinel, "GET 不得把 targets 明文密码送进浏览器"
    assert targets[0]["name"] == "a" and targets[0]["username"] == "ua", "非敏感字段不掩码"

    resp = client.put("/api/config", headers=auth, json={"tree": data["tree"]})
    assert resp.status_code == 200, resp.text
    disk = open(mgr.config_path, encoding="utf-8").read()
    assert "password: pa" in disk, f"原样保存不得把密码写成占位串: {disk}"
    assert sentinel not in disk
