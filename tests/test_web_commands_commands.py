"""test_web_commands_commands 测试计划: Web 命令执行 (_drain_web_commands) 与强制汇报确认

## 测试计划(每个测试函数一条)
- test_virtual_tracker_prefix_single_point: 守阵(issue webui-virtual-tracker-prefix-dup) 虚拟 tracker 前缀集只认 infra 单点 —— commands.py 零字面量 + 改单点即改三处过滤(猴补空元组后 DHT 行进基线)
- test_api_torrent_write_endpoints_enqueue: 二轮种子写端点(15个) POST 转发 cmd/参数入队 + 无密钥 401
"""

import tempfile

import time

from types import SimpleNamespace

from auto_qb.infra.utils import encode_group_key, mask_tracker_url

from auto_qb.webui.runtime import WebUIRuntime

from helpers import capture_logs

from webui_helpers import _make_grouped_manager


def test_virtual_tracker_prefix_single_point(monkeypatch):
    """守阵: 虚拟 tracker 前缀集只认 infra 单点(issue webui-virtual-tracker-prefix-dup)

    commands.py 此前把 ("**","[DHT]","[PeX]","[LSD]") 字面量硬编码 3 处(基线/判定/移除),
    而 infra.utils.VIRTUAL_TRACKER_PREFIXES 是既有单点(views.py 早已引用) —— 增删前缀
    要改单点 + 3 处字面量 + 前端 1 处, 是真实漂移点。
    静态: commands.py 源码零字面量; 行为: 模块级名字就是 infra 单点, 且**改单点即改三处过滤**
    (猴补为空元组后 DHT 行会进基线, 证明过滤读的是单点而不是各自抄的字面量)。
    红验: 任一处写回字面量元组, 静态半判红; 单点删一项而 commands 自抄, 行为半判红。
    """
    from pathlib import Path

    from auto_qb.infra.utils import VIRTUAL_TRACKER_PREFIXES
    from auto_qb.webui import commands as cmd_mod

    src = Path(__file__).resolve().parents[1] / "src" / "auto_qb" / "webui" / "commands.py"
    text = src.read_text(encoding="utf-8")
    for literal in ('"[DHT]"', '"[PeX]"', '"[LSD]"', '"**"'):
        assert literal not in text, f"commands.py 仍在硬编码虚拟 tracker 前缀 {literal}(应 import 单点)"
    assert cmd_mod.VIRTUAL_TRACKER_PREFIXES is VIRTUAL_TRACKER_PREFIXES, "必须复用 infra 单点同一对象"

    with tempfile.TemporaryDirectory() as td:
        mgr, client, _key = _make_grouped_manager(td)
        client.trackers_map["HA"] = [
            {
                "url": "** [DHT] **",
                "status": 0
            },
            {
                "url": "https://tracker.hhanclub.net/announce.php",
                "status": 2
            },
        ]
        baseline, _epoch = mgr._trackers_baseline(["HA"])
        assert set(baseline["HA"]) == {"https://tracker.hhanclub.net/announce.php"}, "虚拟行不入基线"
        # 改单点: 过滤读的是单点(不是各自抄的字面量)
        monkeypatch.setattr(cmd_mod, "VIRTUAL_TRACKER_PREFIXES", ())
        baseline2, _ = mgr._trackers_baseline(["HA"])
        assert "** [DHT] **" in baseline2["HA"], "过滤必须读单点: 单点置空后虚拟行应进基线"


def test_api_torrent_write_endpoints_enqueue(web_env):
    """二轮种子写端点(15个) POST 转发: cmd 与参数正确入队; 无密钥 401(鉴权沿用 /api/* 依赖)"""
    mgr, client = web_env
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    cases = [
        ("/api/torrents/HA/recheck", None, "recheck_torrent", {
            "hash": "HA"
        }),
        ("/api/torrents/HA/super-seeding", {
            "enable": True
        }, "super_seeding", {
            "hash": "HA",
            "enable": True
        }),
        ("/api/torrents/HA/force-start", {
            "enable": False
        }, "force_start", {
            "hash": "HA",
            "enable": False
        }),
        (
            "/api/torrents/HA/limits", {
                "up_limit": 1024,
                "dl_limit": 0
            }, "set_torrent_limits", {
                "hash": "HA",
                "up_limit": 1024,
                "dl_limit": 0
            }
        ),
        ("/api/torrents/HA/limits", {
            "dl_limit": 512
        }, "set_torrent_limits", {
            "hash": "HA",
            "dl_limit": 512
        }),
        (
            "/api/torrents/HA/share-limits", {
                "ratio_limit": 1.5,
                "seeding_time_limit": -1,
                "inactive_seeding_time_limit": -2
            }, "set_share_limits", {
                "hash": "HA",
                "ratio_limit": 1.5,
                "seeding_time_limit": -1,
                "inactive_seeding_time_limit": -2
            }
        ),
        ("/api/torrents/HA/location", {
            "location": "R:/X"
        }, "set_torrent_location", {
            "hash": "HA",
            "location": "R:/X"
        }),
        ("/api/torrents/HA/rename", {
            "name": "New"
        }, "rename_torrent", {
            "hash": "HA",
            "name": "New"
        }),
        ("/api/torrents/HA/queue", {
            "action": "top"
        }, "queue_torrent", {
            "hash": "HA",
            "action": "top"
        }),
        ("/api/torrents/HA/auto-tmm", {
            "enable": True
        }, "set_auto_tmm", {
            "hash": "HA",
            "enable": True
        }),
        ("/api/torrents/HA/trackers/add", {
            "urls": ["u1", "u2"]
        }, "add_trackers", {
            "hash": "HA",
            "urls": ["u1", "u2"]
        }),
        ("/api/torrents/HA/trackers/remove", {
            "url": "a"
        }, "remove_tracker", {
            "hash": "HA",
            "url": "a"
        }),
        (
            "/api/torrents/HA/files/priority", {
                "indices": [0, 2],
                "priority": 7
            }, "set_file_priority", {
                "hash": "HA",
                "indices": [0, 2],
                "priority": 7
            }
        ),
        (
            "/api/torrents/HA/rename-fs", {
                "old_path": "a",
                "new_path": "b",
                "is_folder": True
            }, "rename_fs", {
                "hash": "HA",
                "old_path": "a",
                "new_path": "b",
                "is_folder": True
            }
        ),
        (
            "/api/torrents/bulk", {
                "hashes": ["HA", "HB"],
                "action": "pause"
            }, "bulk_torrents", {
                "hashes": ["HA", "HB"],
                "action": "pause",
                "delete_files": False
            }
        ),
        (
            "/api/torrents/bulk", {
                "hashes": ["HA"],
                "action": "delete",
                "delete_files": True
            }, "bulk_torrents", {
                "hashes": ["HA"],
                "action": "delete",
                "delete_files": True
            }
        ),
    ]
    for path, body, want_cmd, want_payload in cases:
        resp = client.post(path, headers=auth, json=body)
        assert resp.status_code == 200, f"{path}: {resp.text}"
        data = resp.json()
        assert data["queued"] is True and data["cmd_id"], path
        got_cmd, got_payload = mgr.web.commands.get_nowait()
        assert got_cmd == want_cmd, f"{path}: {got_cmd}"
        got_payload.pop("cmd_id")
        got_payload.pop("_queued_ts", None)  # P0-0 埋点元数据, 不参与入队参数断言
        got_payload.pop("_queued_ts", None)  # P0-0 埋点元数据, 不参与入队参数断言
        assert got_payload == want_payload, f"{path}: {got_payload}"
    # 鉴权沿用既有 /api/* 依赖: 无/错密钥 401
    assert client.post("/api/torrents/HA/recheck").status_code == 401
    assert client.post("/api/torrents/bulk", json={"hashes": ["HA"], "action": "pause"}).status_code == 401
