"""test_web_commands 测试计划: Web 命令执行 (_drain_web_commands) 与强制汇报确认

## 测试计划(每个测试函数一条)
- test_drain_web_commands_group_actions: 组级暂停/开始/汇报/删除命令执行并作用于整组 hash
- test_drain_web_commands_torrent_actions: 单种子命令作用于该 hash; 种子不在快照 -> 跳过(删除守阵)
- test_api_torrent_write_endpoints_enqueue: 二轮种子写端点(15个) POST 转发 cmd/参数入队 + 无密钥 401
- test_api_t_bulk_group_keys_enqueue: bulk 组键模式(DLG-02): keys 编码组键入队解码回 tuple, 可与 hashes 混合; 纯 hash 载荷不带 keys 键; 无密钥 401
- test_api_t_bulk_tags_category_enqueue: bulk 标签/分类动作入队 —— tags 过滤空串非空才透传、category 按键存在性透传(空串=清除分类要保留)、未提供时载荷不带键(历史形态不变); 无密钥 401
- test_api_t_bulk_limits_location_enqueue: bulk 限速/移动动作入队(计划 26-10-02-1955 W2) —— up/dl/location 提供才透传(0=不限合法), 负数/limits 全空/location 空路径 400 不入队; 历史载荷形态不变; 无密钥 401
- test_api_t_bulk_skip_check_enqueue: bulk 跳检动作入队(计划 26-10-02-1955 W3) —— 无额外参数(载荷只有 hashes/action/delete_files); 无密钥 401; gate 在 drain 分派处, 路由层开关关时仍 200 入队
- test_drain_web_commands_torrent_write_actions: 二轮写命令正常执行(参数透传/cmd_id 回执 ok/限速位置同步快照)
- test_drain_web_commands_torrent_write_unknown_hash_skips: 二轮写命令未知 hash 静默跳过不调 API
- test_drain_web_commands_share_limits_and_queue_mapping: share-limits 缺省维度 -2 补齐; queue 动作映射; 未知动作 error 回执
- test_drain_web_commands_torrent_write_param_errors: 写命令参数错误 -> error 回执且不调 API, 后续命令继续
- test_drain_web_commands_bulk_torrents: 批量多 hash 一次调用 + 聚合回执(部分缺失/未知动作/空列表 -> error)
- test_drain_web_commands_bulk_torrents_group_keys: bulk 组键模式(DLG-02): 组键展开级联全组成员删除; 与 hashes 混合去重; 缺失组计组数; 组不存在不调 API
- test_drain_web_commands_bulk_torrents_tags_category: bulk 标签/分类命令执行 —— add_tags/remove_tags/set_category 单次调用带全部 hash; 缺 tags / 缺 category 键 error 回执; 空串分类(清除)合法; 标签非空校验
- test_drain_web_commands_bulk_torrents_limits_location: bulk 限速/移动分派 —— 只调有值方向、每方向一次调用传全 hashes; 写后快照同步(up_limit/dl_limit/save_path); 缺值 error 回执不调 API
- test_cmd_trackers_write_invalidates_lazy_cache: tracker 三兄弟写后失效 _trackers_info 惰性缓存(重读拉新值)
- test_drain_web_commands_unknown_and_error_continues: 未知命令与执行异常只记日志, 不中断后续消费
- test_drain_web_commands_empty_queue: 队列为空直接返回(queue.Empty 分支)
- test_verdict_reannounce_epoch_matrix: epoch 判定矩阵(②在途/③前跳 ==TOL 边界 pending/基线 status 0/1 行极值不触发/④status4+msg rejected 且先于前跳判, 空 msg 不判败; plan 26-10-05-0923)
- test_verdict_reannounce_legacy_matrix: legacy 判定矩阵(基线行无 epoch 字段 -> ②/③′/④ 生效, 前跳判据不参与)
- test_verdict_reannounce_min_window_guard: 判据② min 窗口守卫(基线 min 在未来 updating=推迟登记假瞬态 -> pending; 过期/缺失/0 后在途直证, S0 探针实证)
- test_trackers_baseline_shape_and_epoch_mode: baseline 形状回归 {url: {status, updating, next, min}} + epoch_mode 字段存在性探测(虚拟行排除)
- test_reannounce_receipt_prefix_contract: D4=warn 前缀文案契约(三前缀常量钉死, 改文案必红; 机器分流依据 = status 三值)
- test_reannounce_confirm_success_and_timeout: epoch 确认回执: 前跳命中 -> ok 回执跟踪清空; 超时 -> warn「未确认」不再判「失败」
- test_reannounce_confirm_group_aggregate: 组汇报三桶聚合(ok+error -> error 带计数与原因; 全推迟 -> warn「已受理」早回执 + 后台登记)
- test_reannounce_register_immediate_verdicts_and_deadline: 注册直判(停止种子立即 warn/推迟检出早回执+后台登记) + item 级 deadline 公式与 600 上限
- test_reannounce_stopped_midwindow_direct_verdict: 窗口内暂停直判(下一 tick warn「种子已停止」, 不等 deadline)
- test_reannounce_background_verify_and_cap: 推迟后台核实(达 min_e 出结论落 INFO/WARNING 日志并移除/逾时 DEBUG 静默移除/500 上限丢最旧 WARNING)
- test_cmd_group_actions_skip_missing_group: 组 key 不存在/成员不在快照 -> 空 hashes 不调 API
- test_cmd_reload_config_delegates: reload_config 命令委托 apply_new_config
"""
import tempfile
import time
from types import SimpleNamespace

from auto_qb.infra.utils import encode_group_key, mask_tracker_url
from auto_qb.webui.runtime import WebUIRuntime

from webui_helpers import _make_grouped_manager, module_log


def test_drain_web_commands_group_actions():
    """_drain_web_commands: 组级暂停/开始/汇报/删除命令在主循环侧执行, 作用于整组 hash"""
    with tempfile.TemporaryDirectory() as td:
        mgr, client, key = _make_grouped_manager(td)
        mgr.web.commands.put(("pause_group", {"key": key}))
        mgr.web.commands.put(("resume_group", {"key": key}))
        mgr.web.commands.put(("reannounce_group", {"key": key}))
        mgr.web.consume_commands()
        # reannounce 走 FakeClient 旧约定(记 None; test_actions 多处断言依赖), pause/resume 记 hash 列表
        assert client.calls == [("pause", ["HA", "HB"]), ("resume", ["HA", "HB"]), ("reannounce", None)], client.calls
        # 删除整组: delete_files 透传, 成员从快照移除
        mgr.web.commands.put(("delete_group", {"key": key, "delete_files": True}))
        mgr.web.consume_commands()
        assert client.calls[-1] == ("delete", True), f"delete_group: {client.calls}"
        assert mgr.store.by_hash == {}, "删除整组后成员应已从快照移除"


def test_drain_web_commands_torrent_actions():
    """_drain_web_commands: 单种子命令只作用于该 hash; 种子不在快照 -> 跳过(删除守阵)"""
    with tempfile.TemporaryDirectory() as td:
        mgr, client, key = _make_grouped_manager(td)
        for cmd in ("pause_torrent", "resume_torrent", "reannounce_torrent"):
            mgr.web.commands.put((cmd, {"hash": "HA"}))
        mgr.web.consume_commands()
        assert [c[0] for c in client.calls] == ["pause", "resume", "reannounce"], client.calls
        assert client.calls[0][1] == ["HA"] and client.calls[1][1] == ["HA"], "单种子命令只作用于该 hash"
        # 删除守阵: 种子已不在快照 -> 不调 API
        before = list(client.calls)
        mgr.web.commands.put(("pause_torrent", {"hash": "GONE"}))
        mgr.web.commands.put(("delete_torrent", {"hash": "GONE", "delete_files": True}))
        mgr.web.consume_commands()
        assert client.calls == before, "种子不在快照应跳过(删除守阵)"


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


def test_api_t_bulk_group_keys_enqueue(web_env):
    """bulk 组键模式(DLG-02): keys 传编码组键, 入队前解码回 tuple; 可与 hashes 混合

    纯 hash 调用不带 keys 键(队列载荷与历史形态完全一致, 不碰既有断言); 无密钥 401。
    """
    mgr, client = web_env
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    key = encode_group_key(("R:/Downloads", ("a.mkv", "b.mkv")))
    # 混合选择: hashes + keys(解码回原组键 tuple) 同 payload 入队
    resp = client.post(
        "/api/torrents/bulk",
        headers=auth,
        json={
            "hashes": ["HC"],
            "keys": [key],
            "action": "delete",
            "delete_files": True
        },
    )
    assert resp.status_code == 200 and resp.json()["queued"] is True
    cmd, payload = mgr.web.commands.get_nowait()
    payload.pop("cmd_id")
    payload.pop("_queued_ts", None)  # 同上
    payload.pop("_queued_ts", None)  # 同上
    assert cmd == "bulk_torrents"
    assert payload == {
        "hashes": ["HC"],
        "keys": [("R:/Downloads", ("a.mkv", "b.mkv"))],
        "action": "delete",
        "delete_files": True,
    }, payload
    # 纯 hash 调用: 载荷不含 keys 键(历史形态不变)
    client.post("/api/torrents/bulk", headers=auth, json={"hashes": ["HA"], "action": "pause"})
    _, payload2 = mgr.web.commands.get_nowait()
    assert "keys" not in payload2
    # 鉴权: 无密钥 401
    assert client.post("/api/torrents/bulk", json={"keys": [key], "action": "delete"}).status_code == 401


def test_api_t_bulk_tags_category_enqueue(web_env):
    """bulk 标签/分类动作入队: tags 过滤空段非空才透传; category 按键存在性透传(空串=清除分类要保留);
    未提供时载荷不带这两个键(纯 pause 调用的队列载荷与历史形态完全一致); 无密钥 401"""
    mgr, client = web_env
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    cases = [
        # add_tags: 空段过滤后透传
        (
            {
                "hashes": ["HA"],
                "action": "add_tags",
                "tags": ["HR", "", "Keep"]
            },
            {
                "hashes": ["HA"],
                "action": "add_tags",
                "delete_files": False,
                "tags": ["HR", "Keep"]
            },
        ),
        (
            {
                "hashes": ["HA"],
                "action": "remove_tags",
                "tags": ["HR"]
            },
            {
                "hashes": ["HA"],
                "action": "remove_tags",
                "delete_files": False,
                "tags": ["HR"]
            },
        ),
        # set_category: category="" 也必须透传(清除分类的语义靠空串承载, 按键存在性判断)
        (
            {
                "hashes": ["HA"],
                "action": "set_category",
                "category": ""
            },
            {
                "hashes": ["HA"],
                "action": "set_category",
                "delete_files": False,
                "category": ""
            },
        ),
        (
            {
                "hashes": ["HA"],
                "action": "set_category",
                "category": "电影"
            },
            {
                "hashes": ["HA"],
                "action": "set_category",
                "delete_files": False,
                "category": "电影"
            },
        ),
        # 历史形态: 不带 tags/category 的载荷不加新键
        (
            {
                "hashes": ["HA"],
                "action": "pause"
            },
            {
                "hashes": ["HA"],
                "action": "pause",
                "delete_files": False
            },
        ),
    ]
    for body, want_payload in cases:
        resp = client.post("/api/torrents/bulk", headers=auth, json=body)
        assert resp.status_code == 200, f"{body}: {resp.text}"
        assert resp.json()["queued"] is True
        cmd, payload = mgr.web.commands.get_nowait()
        assert cmd == "bulk_torrents"
        payload.pop("cmd_id")
        payload.pop("_queued_ts", None)  # P0-0 埋点元数据, 不参与入队参数断言
        assert payload == want_payload, body
    assert client.post(
        "/api/torrents/bulk", json={
            "hashes": ["HA"],
            "action": "add_tags",
            "tags": ["x"]
        }
    ).status_code == 401


def test_api_t_bulk_limits_location_enqueue(web_env):
    """bulk 限速/移动动作入队(计划 26-10-02-1955 W2): up/dl 提供才透传(0=不限合法, 负数 400)、
    location 非空才透传; limits 两方向全空 / location 空路径 -> 400 不入队;
    纯 pause 调用的队列载荷不带新键(历史形态不变); 无密钥 401"""
    mgr, client = web_env
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    cases = [
        # 只提供上传方向: 载荷只带 up_limit(0 = qB 语义的不限速, 合法)
        (
            {
                "hashes": ["HA", "HB"],
                "action": "limits",
                "up_limit": 1024
            },
            {
                "hashes": ["HA", "HB"],
                "action": "limits",
                "delete_files": False,
                "up_limit": 1024
            },
        ),
        # 两方向都提供: 0 原样透传(不限速)
        (
            {
                "hashes": ["HA"],
                "action": "limits",
                "up_limit": 0,
                "dl_limit": 2048
            },
            {
                "hashes": ["HA"],
                "action": "limits",
                "delete_files": False,
                "up_limit": 0,
                "dl_limit": 2048
            },
        ),
        # 批量移动: 非空路径透传(首尾空白剥掉)
        (
            {
                "hashes": ["HA"],
                "action": "location",
                "location": "  R:/X  "
            },
            {
                "hashes": ["HA"],
                "action": "location",
                "delete_files": False,
                "location": "R:/X"
            },
        ),
    ]
    for body, want_payload in cases:
        resp = client.post("/api/torrents/bulk", headers=auth, json=body)
        assert resp.status_code == 200, f"{body}: {resp.text}"
        assert resp.json()["queued"] is True
        cmd, payload = mgr.web.commands.get_nowait()
        assert cmd == "bulk_torrents"
        payload.pop("cmd_id")
        payload.pop("_queued_ts", None)  # P0-0 埋点元数据, 不参与入队参数断言
        assert payload == want_payload, body
    # 参数错误 -> 400 且不入队(负数 / limits 全空 / location 空路径)
    bad = [
        {
            "hashes": ["HA"],
            "action": "limits",
            "up_limit": -1
        },
        {
            "hashes": ["HA"],
            "action": "limits",
            "dl_limit": -1024
        },
        {
            "hashes": ["HA"],
            "action": "limits"
        },
        {
            "hashes": ["HA"],
            "action": "location",
            "location": ""
        },
        {
            "hashes": ["HA"],
            "action": "location",
            "location": "   "
        },
        {
            "hashes": ["HA"],
            "action": "location"
        },
    ]
    for i, body in enumerate(bad):
        resp = client.post("/api/torrents/bulk", headers=auth, json=body)
        assert resp.status_code == 400, f"case {i}: {resp.status_code} {resp.text}"
        assert mgr.web.commands.qsize() == 0, f"case {i}: 参数错误不应入队"
    # 历史 形态: 不带新键的纯 pause 载荷不变
    client.post("/api/torrents/bulk", headers=auth, json={"hashes": ["HA"], "action": "pause"})
    _, payload = mgr.web.commands.get_nowait()
    payload.pop("cmd_id")
    payload.pop("_queued_ts", None)
    assert payload == {"hashes": ["HA"], "action": "pause", "delete_files": False}, payload
    # 鉴权: 无密钥 401
    assert client.post(
        "/api/torrents/bulk", json={
            "hashes": ["HA"],
            "action": "limits",
            "up_limit": 1
        }
    ).status_code == 401


def test_api_t_bulk_skip_check_enqueue(web_env):
    """bulk 跳检动作入队(计划 26-10-02-1955 W3): 无额外参数, 载荷只有 hashes/action/delete_files
    (多余键不出现); 无密钥 401。gate 在 drain 分派处(路由层不设), 故开关关时这里仍 200 入队"""
    mgr, client = web_env
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    resp = client.post("/api/torrents/bulk", headers=auth, json={"hashes": ["HA", "HB"], "action": "skip_check"})
    assert resp.status_code == 200 and resp.json()["queued"] is True
    cmd, payload = mgr.web.commands.get_nowait()
    assert cmd == "bulk_torrents"
    payload.pop("cmd_id")
    payload.pop("_queued_ts", None)
    assert payload == {"hashes": ["HA", "HB"], "action": "skip_check", "delete_files": False}, payload
    # 鉴权: 无密钥 401
    assert client.post("/api/torrents/bulk", json={"hashes": ["HA"], "action": "skip_check"}).status_code == 401


def test_drain_web_commands_torrent_write_actions():
    """二轮写命令: 参数正确传给 QbApi(真链路), cmd_id 回执 ok, 限速/保存路径写后同步快照"""
    with tempfile.TemporaryDirectory() as td:
        mgr, client, key = _make_grouped_manager(td)
        # S3 删除改道(plan 26-10-07-0055): remove_tracker 收 mask 值, 后端重取原文比对
        client.trackers_map["HA"] = [{"url": "https://c.example/announce?passkey=SUPERSECRET123", "status": 2}]
        cmds = [
            ("recheck_torrent", {
                "hash": "HA",
                "cmd_id": "c1"
            }),
            ("super_seeding", {
                "hash": "HA",
                "enable": True,
                "cmd_id": "c2"
            }),
            ("force_start", {
                "hash": "HA",
                "enable": True,
                "cmd_id": "c3"
            }),
            ("set_torrent_limits", {
                "hash": "HA",
                "up_limit": 1024,
                "dl_limit": 2048,
                "cmd_id": "c4"
            }),
            (
                "set_share_limits", {
                    "hash": "HA",
                    "ratio_limit": 1.5,
                    "seeding_time_limit": -1,
                    "inactive_seeding_time_limit": -2,
                    "cmd_id": "c5"
                }
            ),
            ("set_torrent_location", {
                "hash": "HA",
                "location": "R:/Moved",
                "cmd_id": "c6"
            }),
            ("rename_torrent", {
                "hash": "HA",
                "name": "NewName",
                "cmd_id": "c7"
            }),
            ("set_auto_tmm", {
                "hash": "HA",
                "enable": True,
                "cmd_id": "c8"
            }),
            ("add_trackers", {
                "hash": "HA",
                "urls": ["https://a/announce", "https://b/announce"],
                "cmd_id": "c9"
            }),
            (
                "remove_tracker", {
                    "hash": "HA",
                    "url": mask_tracker_url("https://c.example/announce?passkey=SUPERSECRET123"),
                    "cmd_id": "c10"
                }
            ),
            ("set_file_priority", {
                "hash": "HA",
                "indices": [0, 1],
                "priority": 6,
                "cmd_id": "c11"
            }),
            (
                "rename_fs", {
                    "hash": "HA",
                    "old_path": "old/file.mkv",
                    "new_path": "new/file.mkv",
                    "is_folder": False,
                    "cmd_id": "c12"
                }
            ),
        ]
        for cmd, payload in cmds:
            mgr.web.commands.put((cmd, payload))
        mgr.web.consume_commands()
        assert client.calls[0] == ("recheck", None) and client.recheck_hashes_calls[0] == "HA"
        assert client.calls[1] == ("set_super_seeding", True)
        assert client.calls[2] == ("set_force_start", True)
        assert client.calls[3] == ("set_upload_limit", 1024)
        assert client.calls[4] == ("set_download_limit", 2048)
        assert client.calls[5] == ("set_share_limits", (1.5, -1, -2)), "share-limits 三值映射"
        assert client.calls[6] == ("set_location", "R:/Moved")
        assert client.calls[7] == ("rename", ("HA", "NewName")), "rename 参数形态(torrent_hash, new_torrent_name)"
        assert client.calls[8] == ("set_auto_tmm", True)
        assert client.calls[9] == ("add_trackers", ("HA", ["https://a/announce", "https://b/announce"]))
        assert client.calls[10] == ("remove_trackers", ("HA", ["https://c.example/announce?passkey=SUPERSECRET123"])), \
            "mask 入参须换回原文传 qB(qB 按原文精确匹配)"
        assert client.calls[11] == ("file_priority", ("HA", [0, 1], 6))
        assert client.calls[12] == ("rename_file", ("HA", "old/file.mkv", "new/file.mkv"))
        # !D2 之后回执**在 drain 阶段就写**(不再扣住等真值)—— 真机实测 qB 翻状态要 1258ms,
        #   扣着回执等 = 撤下被钉死在 1.25s+(实测撤下 2947ms)。回执只表示"命令已执行"。
        assert mgr.web.results["c1"]["status"] == "ok", "回执必须立即发, 不再等真值落地"
        # recheck_torrent 已入延迟回执族(plan 26-09-30-0109: handler 经 ops 提交并自写回执,
        # 拒绝时回执带自解释文案) —— 它不再走 RESYNC 的 defer_receipt 真值登记; 校验态由
        # 正常快照刷新可见, 乐观 UI 也不做 recheck(结果在远端)
        assert "c1" not in mgr.web.truth_pending, "recheck 由 handler 自写回执, 不登记真值待推"
        # 回执**不带 truth**: 带上未落地的真值 = 让前端采纳命令前的旧值 ⇒ 弹回(红线)
        assert "truth" not in mgr.web.results["c1"], "回执不得带真值(真值改由 truth 事件推送)"
        # 真值登记为待推, 由 run() 无条件 flush(幂等; 漏调会让前端一直挂着乐观值)
        assert "c2" in mgr.web.truth_pending, "RESYNC 命令应登记待推真值"
        mgr.web.flush_truths()
        assert mgr.web.flush_truths() is None, "重复 flush 必须是安全的空操作"
        # 全部命令回执 ok(c10=edit_tracker 已随编辑功能下线移除, 现为 c1..c12)
        assert all(mgr.web.results[f"c{i}"]["status"] == "ok" for i in range(1, 13)), mgr.web.results
        # 限速/保存路径写后快照同步(QbApi update_torrent_fields)
        rec = mgr.store.get("HA")
        assert rec.up_limit == 1024 and rec.dl_limit == 2048 and rec.save_path == "R:/Moved"


def test_drain_web_commands_torrent_write_unknown_hash_skips():
    """二轮写命令: hash 不在快照 -> 静默跳过不调 API(照 pause_torrent 删除守阵样板)"""
    with tempfile.TemporaryDirectory() as td:
        mgr, client, key = _make_grouped_manager(td)
        cmds = [
            ("recheck_torrent", {
                "hash": "GONE"
            }),
            ("super_seeding", {
                "hash": "GONE",
                "enable": True
            }),
            ("force_start", {
                "hash": "GONE",
                "enable": True
            }),
            ("set_torrent_limits", {
                "hash": "GONE",
                "up_limit": 1,
                "dl_limit": 1
            }),
            (
                "set_share_limits", {
                    "hash": "GONE",
                    "ratio_limit": 1.0,
                    "seeding_time_limit": -1,
                    "inactive_seeding_time_limit": -1
                }
            ),
            ("set_torrent_location", {
                "hash": "GONE",
                "location": "R:/X"
            }),
            ("rename_torrent", {
                "hash": "GONE",
                "name": "N"
            }),
            ("queue_torrent", {
                "hash": "GONE",
                "action": "top"
            }),
            ("set_auto_tmm", {
                "hash": "GONE",
                "enable": True
            }),
            ("add_trackers", {
                "hash": "GONE",
                "urls": ["u"]
            }),
            ("remove_tracker", {
                "hash": "GONE",
                "url": "a"
            }),
            ("set_file_priority", {
                "hash": "GONE",
                "indices": [0],
                "priority": 1
            }),
            ("rename_fs", {
                "hash": "GONE",
                "old_path": "a",
                "new_path": "b",
                "is_folder": True
            }),
        ]
        for cmd, payload in cmds:
            mgr.web.commands.put((cmd, payload))
        mgr.web.consume_commands()
        assert client.calls == [] and client.recheck_hashes_calls == [], client.calls


def test_drain_web_commands_share_limits_and_queue_mapping():
    """share-limits: 缺省维度按 -2(用全局)补齐; queue: 四动作映射到对应 qB 方法, 未知动作 error 回执"""
    with tempfile.TemporaryDirectory() as td:
        mgr, client, key = _make_grouped_manager(td)
        # queue 四动作 -> qB 队列端点方法(方法名映射正确)
        for action, want in (
            ("top", "queue_top"), ("up", "queue_up"), ("down", "queue_down"), ("bottom", "queue_bottom")
        ):
            mgr.web.commands.put(("queue_torrent", {"hash": "HA", "action": action}))
            mgr.web.consume_commands()
            assert client.calls[-1] == (want, ["HA"]), f"{action}: {client.calls[-1]}"
        # share-limits 缺省维度 -2 补齐(库不过滤 None, 直传会以字面量 "None" 发给 qB)
        mgr.web.commands.put(("set_share_limits", {"hash": "HA", "ratio_limit": 2.0}))
        mgr.web.consume_commands()
        assert client.calls[-1] == ("set_share_limits", (2.0, -2, -2)), client.calls[-1]
        # 未知队列动作 -> error 回执且不调 API
        before = list(client.calls)
        mgr.web.commands.put(("queue_torrent", {"hash": "HA", "action": "middle", "cmd_id": "qerr"}))
        mgr.web.consume_commands()
        assert client.calls == before
        r = mgr.web.results["qerr"]
        assert r["status"] == "error" and "middle" in r["error"], r


def test_drain_web_commands_torrent_write_param_errors():
    """写命令参数错误(空名称/路径/URL/非法优先级) -> error 回执且不调 API, 后续命令继续消费"""
    with tempfile.TemporaryDirectory() as td:
        mgr, client, key = _make_grouped_manager(td)
        errs = [
            ("rename_torrent", {
                "hash": "HA",
                "name": ""
            }, "e1"),
            ("set_torrent_location", {
                "hash": "HA",
                "location": ""
            }, "e2"),
            ("add_trackers", {
                "hash": "HA",
                "urls": []
            }, "e3"),
            ("remove_tracker", {
                "hash": "HA",
                "url": ""
            }, "e5"),
            ("set_file_priority", {
                "hash": "HA",
                "indices": [0],
                "priority": 3
            }, "e6"),
            ("set_file_priority", {
                "hash": "HA",
                "indices": [],
                "priority": 1
            }, "e7"),
            ("rename_fs", {
                "hash": "HA",
                "old_path": "a",
                "new_path": "",
                "is_folder": False
            }, "e8"),
        ]
        for cmd, payload, cmd_id in errs:
            mgr.web.commands.put((cmd, {**payload, "cmd_id": cmd_id}))
        mgr.web.commands.put(("pause_torrent", {"hash": "HA"}))  # 后续命令不受影响
        mgr.web.consume_commands()
        assert client.calls == [("pause", ["HA"])], client.calls
        for _, _, cmd_id in errs:
            assert mgr.web.results[cmd_id]["status"] == "error", (cmd_id, mgr.web.results[cmd_id])


def test_drain_web_commands_bulk_torrents():
    """批量命令: 多 hash 一次 API 调用 + 聚合回执; 部分缺失/未知动作/空列表 -> error 回执"""
    with tempfile.TemporaryDirectory() as td:
        mgr, client, key = _make_grouped_manager(td)
        # pause: 一次调用传全部 hashes(单条 call 即单次调用), 全部命中 -> ok
        mgr.web.commands.put(("bulk_torrents", {"hashes": ["HA", "HB"], "action": "pause", "cmd_id": "b1"}))
        mgr.web.consume_commands()
        assert client.calls[-1] == ("pause", ["HA", "HB"]), client.calls[-1]
        assert mgr.web.results["b1"]["status"] == "ok"
        # recheck: 经 ops 层逐个提交(R1 第二入口) —— 每 hash 一次提交并各自登记在途,
        # 不再是"一次 API 传全部"(直调 API 会让批量路径绕过在途互斥, 留下 C1 旁路)
        mgr.web.commands.put(("bulk_torrents", {"hashes": ["HA", "HB"], "action": "recheck", "cmd_id": "b2"}))
        mgr.web.consume_commands()
        assert client.recheck_hashes_calls == ["HA", "HB"], client.recheck_hashes_calls
        assert mgr.web.results["b2"]["status"] == "ok"
        # delete: delete_files 透传, 成员从快照移除
        mgr.web.commands.put(
            ("bulk_torrents", {
                "hashes": ["HA"],
                "action": "delete",
                "delete_files": True,
                "cmd_id": "b3"
            })
        )
        mgr.web.consume_commands()
        assert client.calls[-1] == ("delete", True)
        assert mgr.store.get("HA") is None
        assert mgr.web.results["b3"]["status"] == "ok"
        # 部分缺失: 已知种子仍执行, 回执 error 带缺失计数
        mgr.web.commands.put(("bulk_torrents", {"hashes": ["HB", "GONE"], "action": "resume", "cmd_id": "b4"}))
        mgr.web.consume_commands()
        assert client.calls[-1] == ("resume", ["HB"])
        r = mgr.web.results["b4"]
        assert r["status"] == "error" and "1/2" in r["error"], r
        # 未知动作 -> error 回执, 不调 API
        before = list(client.calls)
        mgr.web.commands.put(("bulk_torrents", {"hashes": ["HB"], "action": "purge", "cmd_id": "b5"}))
        mgr.web.consume_commands()
        assert client.calls == before
        assert mgr.web.results["b5"]["status"] == "error" and "purge" in mgr.web.results["b5"]["error"]
        # 空 hash 列表 -> error 回执
        mgr.web.commands.put(("bulk_torrents", {"hashes": [], "action": "pause", "cmd_id": "b6"}))
        mgr.web.consume_commands()
        assert mgr.web.results["b6"]["status"] == "error"


def test_drain_web_commands_bulk_torrents_group_keys():
    """bulk 组键模式(DLG-02): 逐组展开成员级联全组, 与 hashes 合并去重, 缺失按组计数

    组键删除 = 组内全部在册成员一次 API 调用(与 delete_group 同级联语义);
    组不存在/成员全部不在快照计一个缺失组(不按种子数), 回执文案与种子缺失分列。
    """
    with tempfile.TemporaryDirectory() as td:
        mgr, client, key = _make_grouped_manager(td)
        # 组键删除: 级联全组(一次调用传全部成员), delete_files 透传, 成员从快照移除, 回执 ok
        mgr.web.commands.put(
            ("bulk_torrents", {
                "keys": [key],
                "action": "delete",
                "delete_files": True,
                "cmd_id": "g1"
            })
        )
        mgr.web.consume_commands()
        assert client.calls[-1] == ("delete", True), client.calls
        assert mgr.store.get("HA") is None and mgr.store.get("HB") is None
        assert mgr.web.results["g1"]["status"] == "ok"


def test_drain_web_commands_bulk_torrents_group_keys_mixed_and_missing():
    """bulk 组键模式: 混合选择合并去重(显式 hash 与组员重叠不重复调用); 缺失组分列计数"""
    with tempfile.TemporaryDirectory() as td:
        mgr, client, key = _make_grouped_manager(td)
        # 混合: 组(含 HA/HB) + 散种子 HA(重叠) + 散种子 GONE(缺失) -> 去重后 [HA, HB] 一次调用; 回执带缺失计数
        mgr.web.commands.put(
            ("bulk_torrents", {
                "hashes": ["HA", "GONE"],
                "keys": [key],
                "action": "pause",
                "cmd_id": "g2"
            })
        )
        mgr.web.consume_commands()
        assert client.calls[-1] == ("pause", ["HA", "HB"]), client.calls[-1]
        r = mgr.web.results["g2"]
        assert r["status"] == "error" and "1/2" in r["error"], r
        # 组键不存在/成员不在快照 -> 计缺失组, 不调 API
        before = list(client.calls)
        gone_key = ("R:/gone", ("x.mkv", ))
        mgr.web.commands.put(("bulk_torrents", {"keys": [gone_key], "action": "pause", "cmd_id": "g3"}))
        mgr.web.consume_commands()
        assert client.calls == before, "缺失组不应调用 qB API"
        r = mgr.web.results["g3"]
        assert r["status"] == "error" and "1/1 个组" in r["error"], r
        # 组部分成员仍在: 只作用于在册成员, 组不算缺失
        mgr.store.by_hash.pop("HA")
        mgr.web.commands.put(("bulk_torrents", {"keys": [key], "action": "resume", "cmd_id": "g4"}))
        mgr.web.consume_commands()
        assert client.calls[-1] == ("resume", ["HB"]), client.calls[-1]
        assert mgr.web.results["g4"]["status"] == "ok"


def test_drain_web_commands_bulk_torrents_tags_category():
    """bulk 标签/分类命令: 单次 API 调用带全部在册 hash; 缺 tags / 缺 category 键 error 回执;
    空串分类(清除)合法; 标签缺失计数照常分列(同一聚合回执链路)"""
    with tempfile.TemporaryDirectory() as td:
        mgr, client, key = _make_grouped_manager(td)
        # add_tags: 一次调用(tags 由替身记录; 作用范围/缺失过滤与 pause 共用同一链路), 部分缺失回执 error 带计数
        mgr.web.commands.put(
            (
                "bulk_torrents",
                {
                    "hashes": ["HA", "HB", "GONE"],
                    "action": "add_tags",
                    "tags": ["HR", "Keep"],
                    "cmd_id": "t1"
                },
            )
        )
        mgr.web.consume_commands()
        assert client.calls[-1] == ("add_tags", ["HR", "Keep"]), client.calls[-1]
        r = mgr.web.results["t1"]
        assert r["status"] == "error" and "1/3" in r["error"], r
        # remove_tags
        mgr.web.commands.put(
            ("bulk_torrents", {
                "hashes": ["HA"],
                "action": "remove_tags",
                "tags": ["HR"],
                "cmd_id": "t2"
            })
        )
        mgr.web.consume_commands()
        assert client.calls[-1] == ("remove_tags", ["HR"]), client.calls[-1]
        assert mgr.web.results["t2"]["status"] == "ok"
        # set_category: 非空
        mgr.web.commands.put(
            ("bulk_torrents", {
                "hashes": ["HA", "HB"],
                "action": "set_category",
                "category": "电影",
                "cmd_id": "t3"
            })
        )
        mgr.web.consume_commands()
        assert client.calls[-1] == ("set_category", "电影"), client.calls[-1]
        assert mgr.web.results["t3"]["status"] == "ok"
        # set_category: category="" = 清除分类, 合法(只有 None/缺键才 error)
        mgr.web.commands.put(
            ("bulk_torrents", {
                "hashes": ["HA"],
                "action": "set_category",
                "category": "",
                "cmd_id": "t4"
            })
        )
        mgr.web.consume_commands()
        assert client.calls[-1] == ("set_category", ""), client.calls[-1]
        assert mgr.web.results["t4"]["status"] == "ok"
        # add_tags 缺 tags -> error 回执, 不调 API
        before = list(client.calls)
        mgr.web.commands.put(("bulk_torrents", {"hashes": ["HA"], "action": "add_tags", "cmd_id": "t5"}))
        mgr.web.consume_commands()
        assert client.calls == before, "缺 tags 不应调用 qB API"
        r = mgr.web.results["t5"]
        assert r["status"] == "error" and "标签" in r["error"], r
        # set_category 缺 category 键(None) -> error 回执
        mgr.web.commands.put(("bulk_torrents", {"hashes": ["HA"], "action": "set_category", "cmd_id": "t6"}))
        mgr.web.consume_commands()
        assert client.calls == before, "缺 category 不应调用 qB API"
        r = mgr.web.results["t6"]
        assert r["status"] == "error" and "分类" in r["error"], r


def test_drain_web_commands_bulk_torrents_limits_location():
    """bulk 限速/移动分派(计划 26-10-02-1955 W2): 只调有值方向、每方向一次调用传全 hashes
    (不逐枚循环); 0=不限速合法; 缺值(直投队列绕过路由校验)-> error 回执不调 API"""
    with tempfile.TemporaryDirectory() as td:
        mgr, client, key = _make_grouped_manager(td)
        # limits: 两方向都有 -> 各一次调用, 每次收全 hashes; 回执 ok
        mgr.web.commands.put(
            (
                "bulk_torrents", {
                    "hashes": ["HA", "HB"],
                    "action": "limits",
                    "up_limit": 1024,
                    "dl_limit": 2048,
                    "cmd_id": "l1"
                }
            )
        )
        mgr.web.consume_commands()
        assert client.calls[-2:] == [("set_upload_limit", 1024), ("set_download_limit", 2048)]
        assert client.limit_location_hashes_calls[-2:] == [
            ("set_upload_limit", ["HA", "HB"]),
            ("set_download_limit", ["HA", "HB"]),
        ], client.limit_location_hashes_calls
        assert mgr.web.results["l1"]["status"] == "ok"
        # 写后快照同步(QbApi 写方法同步 store, 同 tick 读到新值)
        assert mgr.store.get("HA").up_limit == 1024 and mgr.store.get("HB").dl_limit == 2048
        # limits: 只提供下载方向(0 = 不限速, 合法)-> 只调下载方向
        mgr.web.commands.put(
            ("bulk_torrents", {
                "hashes": ["HA", "HB", "GONE"],
                "action": "limits",
                "dl_limit": 0,
                "cmd_id": "l2"
            })
        )
        mgr.web.consume_commands()
        assert client.calls[-1] == ("set_download_limit", 0), client.calls[-1]
        assert client.limit_location_hashes_calls[-1] == ("set_download_limit", ["HA", "HB"]), \
            "缺失 hash 过滤后一次调用传全部在册 hashes"
        assert mgr.web.results["l2"]["status"] == "error" and "1/3" in mgr.web.results["l2"]["error"]
        # location: 一次调用传全 hashes, 快照 save_path 同步
        mgr.web.commands.put(
            ("bulk_torrents", {
                "hashes": ["HA", "HB"],
                "action": "location",
                "location": "R:/X",
                "cmd_id": "l3"
            })
        )
        mgr.web.consume_commands()
        assert client.calls[-1] == ("set_location", "R:/X"), client.calls[-1]
        assert client.limit_location_hashes_calls[-1] == ("set_location", ["HA", "HB"])
        assert mgr.web.results["l3"]["status"] == "ok"
        assert mgr.store.get("HA").save_path == "R:/X"
        # limits 两方向全空 -> error 回执不调 API(直投队列绕过路由 400 时的 handler 兜底)
        before = list(client.calls)
        mgr.web.commands.put(("bulk_torrents", {"hashes": ["HA"], "action": "limits", "cmd_id": "l4"}))
        mgr.web.consume_commands()
        assert client.calls == before, "缺限速值不应调用 qB API"
        assert mgr.web.results["l4"]["status"] == "error" and "限速值" in mgr.web.results["l4"]["error"]
        # location 空路径 -> error 回执不调 API
        mgr.web.commands.put(
            ("bulk_torrents", {
                "hashes": ["HA"],
                "action": "location",
                "location": "  ",
                "cmd_id": "l5"
            })
        )
        mgr.web.consume_commands()
        assert client.calls == before, "空路径不应调用 qB API"
        assert mgr.web.results["l5"]["status"] == "error" and "目标路径" in mgr.web.results["l5"]["error"]


def test_cmd_trackers_write_invalidates_lazy_cache():
    """tracker 三兄弟写后失效 _trackers_info 惰性缓存: 下轮读取拉新值(同 tick 内后续读不拿旧值)"""
    with tempfile.TemporaryDirectory() as td:
        mgr, client, key = _make_grouped_manager(td)
        rec = mgr.store.get("HA")
        # 预热: 惰性缓存持有旧 tracker 列表
        assert rec.trackers_info(mgr.client)[0]["url"] == "https://tracker.hhanclub.net/announce.php"
        assert rec._trackers_info is not None
        client.trackers_map["HA"] = [{"url": "https://new.example.com/announce"}]
        mgr.web.commands.put(("add_trackers", {"hash": "HA", "urls": ["https://extra.example.com/announce"]}))
        mgr.web.consume_commands()
        assert rec._trackers_info is None, "add_trackers 应失效惰性缓存"
        assert rec.trackers_info(mgr.client) == [{"url": "https://new.example.com/announce"}]
        # remove: 再次失效
        rec.trackers_info(mgr.client)  # 重新预热
        mgr.web.commands.put(("remove_tracker", {"hash": "HA", "url": "https://new.example.com/announce"}))
        mgr.web.consume_commands()
        assert rec._trackers_info is None, "remove_tracker 应失效惰性缓存"


def test_drain_web_commands_unknown_and_error_continues():
    """_drain_web_commands: 未知命令(KeyError)与执行异常只记日志, 不中断后续命令消费"""
    with tempfile.TemporaryDirectory() as td:
        mgr, client, key = _make_grouped_manager(td)
        mgr.web.commands.put(("no_such_command", {}))  # KeyError 分支
        mgr.web.commands.put(("build_search_index", {"bogus": 1}))  # 参数错误 -> TypeError 分支
        mgr.web.commands.put(("pause_group", {"key": key}))  # 后续命令仍应执行
        mgr.web.consume_commands()
        assert client.calls[-1] == ("pause", ["HA", "HB"]), f"异常命令不应中断消费: {client.calls}"
        assert mgr.web.commands.empty()


def test_drain_web_commands_empty_queue():
    """_drain_web_commands: 队列为空时直接返回(queue.Empty 分支), 无任何 API 调用"""
    with tempfile.TemporaryDirectory() as td:
        mgr, client, key = _make_grouped_manager(td)
        mgr.web.consume_commands()
        assert client.calls == []


# ---------- 强制汇报确认重构(plan 26-10-05-0923: epoch 前跳证据门控 + D4=warn 三桶) ----------


def _epoch_tracker(url="u", status=2, updating=False, next_announce=10_000, min_announce=5_000, msg=""):
    """构造 epoch 语义的 qB tracker 行替身(next_announce/min_announce 是 Unix epoch 绝对秒)"""
    return {
        "url": url,
        "status": status,
        "updating": updating,
        "next_announce": next_announce,
        "min_announce": min_announce,
        "msg": msg,
    }


def test_verdict_reannounce_epoch_matrix():
    """epoch 判定矩阵(§3.1): ②在途/③前跳=confirmed(==TOL 边界=pending, 基线 status 0/1 行不判),
    ④status4+msg=rejected(空 msg 不判败), 其余 pending"""
    from auto_qb.core.qbmanager import QbManager

    f = QbManager._verdict_reannounce
    base = {"u": {"status": 2, "updating": False, "next": 10_000, "min": 5_000}}
    kw = dict(t0=9_000, tol=3.0, now=20_000)
    # ② updating / status==3(min 已过期) -> confirmed
    assert f([_epoch_tracker(updating=True)], base, **kw) == ("confirmed", "announce 在途")
    assert f([_epoch_tracker(status=3)], base, **kw) == ("confirmed", "announce 在途")
    # ③ 主判据: 前跳 > TOL -> confirmed; ==TOL 边界不触发
    assert f([_epoch_tracker(next_announce=10_004)], base, **kw)[0] == "confirmed"
    state, reason = f([_epoch_tracker(next_announce=10_504, min_announce=6_000)], base, **kw)
    assert state == "confirmed" and "epoch 前跳 +504s" in reason and "min 同前跳" in reason, "min 同向前跳作佐证"
    assert f([_epoch_tracker(next_announce=10_003)], base, **kw) == ("", ""), "==TOL 边界 -> pending"
    assert f([_epoch_tracker(next_announce=10_001)], base, **kw) == ("", ""), "跳幅 <= TOL -> pending"
    assert f([_epoch_tracker()], base, **kw) == ("", ""), "无变化继续等待"
    # ③ 判定域限基线 status>=2: 基线未联系行(status 0/1)带极值 next 不触发假前跳
    for b_status in (0, 1):
        b = {"u": {"status": b_status, "updating": False, "next": 10_000, "min": 5_000}}
        assert f([_epoch_tracker(next_announce=999_999)], b, **kw) == ("", ""), f"基线 status={b_status} 行不判前跳"
    # ④ tracker 拒绝: status4+msg -> rejected(逐行先于前跳判, 防 status4 行的重试排程误判成功)
    assert f([_epoch_tracker(status=4, msg="tracker message", next_announce=99_999)], base,
             **kw) == ("rejected", "失败: tracker 未接受汇报(not working): tracker message")
    assert f([_epoch_tracker(status=4)], base, **kw) == ("", ""), "status4 空 msg 不武断判败"
    # 虚拟 tracker 行不参与判定
    assert f([_epoch_tracker(url="** [DHT]", next_announce=99_999)], base, **kw) == ("", "")


def test_verdict_reannounce_legacy_matrix():
    """legacy 判定矩阵(§3.2): 基线行无 epoch 字段 -> ②在途/③′变 working/④拒绝生效, 前跳判据不参与"""
    from auto_qb.core.qbmanager import QbManager

    f = QbManager._verdict_reannounce
    base = {"u": {"status": 1, "updating": None, "next": None, "min": None}}  # 行无 epoch 字段
    kw = dict(t0=9_000, tol=3.0, now=20_000)
    assert f([_epoch_tracker(status=3)], base, **kw) == ("confirmed", "announce 在途")
    assert f([_epoch_tracker(updating=True)], base, **kw) == ("confirmed", "announce 在途")
    assert f([_epoch_tracker(status=2)], base, **kw) == ("confirmed", "tracker 状态转为 working")
    assert f([_epoch_tracker(status=4, msg="bad")], base, **kw) == ("rejected", "失败: tracker 未接受汇报(not working): bad")
    # 无前跳判据: 基线非 working + 当前仍非 working, next_announce 再大也不得判成功
    assert f([_epoch_tracker(status=1, next_announce=99_999)], base, **kw) == ("", "")
    assert f([_epoch_tracker(status=1)], base, **kw) == ("", ""), "基线 1 -> 1 无结论"
    b2 = {"u": {"status": 2, "updating": None, "next": None, "min": None}}
    assert f([_epoch_tracker(status=2)], b2, **kw) == ("", ""), "基线已是 working -> ③′ 不触发"
    assert f([_epoch_tracker(status=4)], base, **kw) == ("", ""), "status4 空 msg 不武断判败"


def test_verdict_reannounce_min_window_guard():
    """判据② min 窗口守卫(S0 探针实证): 基线 min 在未来时 updating 是推迟登记假瞬态 -> pending; 过期后在途直证"""
    from auto_qb.core.qbmanager import QbManager

    f = QbManager._verdict_reannounce
    base = {"u": {"status": 2, "updating": False, "next": 100_000, "min": 200_000}}
    kw = dict(t0=190_000, tol=3.0)
    assert f([_epoch_tracker(updating=True)], base, now=150_000, **kw) == ("", ""), "min 未过期: updating 是假瞬态"
    assert f([_epoch_tracker(status=3)], base, now=199_999, **kw) == ("", "")
    assert f([_epoch_tracker(updating=True)], base, now=200_000, **kw)[0] == "confirmed", "min 已过期: 在途直证"
    # min 缺失/为 0: 无窗口信息可用, 不加守卫(在途即直证)
    b_none = {"u": {"status": 2, "updating": False, "next": 100_000, "min": None}}
    assert f([_epoch_tracker(updating=True)], b_none, now=150_000, **kw)[0] == "confirmed"
    b_zero = {"u": {"status": 2, "updating": False, "next": 100_000, "min": 0}}
    assert f([_epoch_tracker(updating=True)], b_zero, now=150_000, **kw)[0] == "confirmed"


def test_trackers_baseline_shape_and_epoch_mode():
    """baseline 形状回归: {url: {status, updating, next, min}} + epoch_mode(任一 real 行含 next_announce 键)"""
    from auto_qb.core.qbmanager import QbManager

    from helpers import FakeClient

    client = FakeClient()
    client.trackers_map = {
        "HA":
            [
                _epoch_tracker(url="https://t.example/ann", status=2, next_announce=1000, min_announce=900),
                {
                    "url": "** [DHT]",
                    "status": 2,
                    "next_announce": 5,
                    "min_announce": 5
                },
            ],
        "HB": [{
            "url": "https://t2.example/ann",
            "status": 1,
            "msg": "x"
        }],  # 无 epoch 字段行
    }
    baseline, epoch_mode = QbManager._trackers_baseline(SimpleNamespace(client=client), ["HA", "HB"])
    assert epoch_mode is True, "任一 real 行含 next_announce 键 = epoch 模式"
    assert baseline["HA"] == {
        "https://t.example/ann": {
            "status": 2,
            "updating": False,
            "next": 1000,
            "min": 900
        }
    }, "real 行按新 dict 形状记录, 虚拟行排除"
    assert baseline["HB"] == {"https://t2.example/ann": {"status": 1, "updating": None, "next": None, "min": None}}
    # 全部行都无 next_announce 键 -> legacy 模式
    client.trackers_map = {"HA": [{"url": "https://t.example/ann", "status": 1}]}
    baseline, epoch_mode = QbManager._trackers_baseline(SimpleNamespace(client=client), ["HA"])
    assert epoch_mode is False and baseline["HA"]["https://t.example/ann"]["next"] is None


def test_reannounce_receipt_prefix_contract():
    """D4=warn 双契约(§3.4): 三前缀常量文案钉死(改文案必红); 机器分流依据是回执 status 三值"""
    from auto_qb.webui.commands import RC_DEFERRED_PREFIX, RC_FAIL_PREFIX, RC_UNCONFIRMED_PREFIX

    assert RC_FAIL_PREFIX == "失败: tracker 未接受汇报(not working): "
    assert RC_DEFERRED_PREFIX == "已受理: 最小间隔未过期, 推迟至 "
    assert RC_UNCONFIRMED_PREFIX == "未确认: "


def test_reannounce_confirm_success_and_timeout():
    """强制汇报确认(epoch 语义): 前跳命中 -> ok 回执且跟踪清空; 超时 -> warn「未确认」不再判「失败」"""
    import time as _time

    with tempfile.TemporaryDirectory() as td:
        mgr, client, key = _make_grouped_manager(td)
        u = "https://tracker.hhanclub.net/announce.php"
        client.trackers_map = {"HA": [_epoch_tracker(url=u, status=2, next_announce=100_000, min_announce=90_000)]}
        # 确认前不写回执(登记 pending), tracker 无变化时继续等待
        mgr.web.commands.put(("reannounce_torrent", {"hash": "HA", "cmd_id": "cmd1"}))
        mgr.web.consume_commands()
        assert "cmd1" in mgr.web.reannounce_pending and "cmd1" not in mgr.web.results
        mgr.web.check_pending()
        assert "cmd1" not in mgr.web.results, "无前跳证据应继续等待"
        client.trackers_map["HA"][0]["next_announce"] = 105_000  # epoch 前跳 +5000s
        mgr.web.check_pending()
        assert mgr.web.results["cmd1"]["status"] == "ok"
        assert mgr.web.reannounce_pending == {}, "全部确认后跟踪应移除"
        # 超时: item 级 deadline 已过仍无证据 -> warn「未确认」(不与 error「失败」混淆)
        mgr.web.commands.put(("reannounce_torrent", {"hash": "HA", "cmd_id": "cmd2"}))
        mgr.web.consume_commands()
        mgr.web.reannounce_pending["cmd2"]["items"]["HA"]["deadline"] = _time.time() - 1
        mgr.web.check_pending()
        r = mgr.web.results["cmd2"]
        assert r["status"] == "warn"
        assert "未确认: " in r["error"] and "前跳" in r["error"]
        assert "汇报确认失败" not in r["error"], "超时不再用旧「失败」标签"


def test_reannounce_confirm_group_aggregate():
    """组强制汇报三桶聚合: ok+error -> error 带计数与原因; 全推迟 -> warn「已受理」早回执 + 后台登记"""
    import time as _time

    with tempfile.TemporaryDirectory() as td:
        mgr, client, key = _make_grouped_manager(td)
        u = "https://tracker.hhanclub.net/announce.php"
        client.trackers_map = {
            "HA": [_epoch_tracker(url=u, status=2, next_announce=100_000, min_announce=90_000)],
            "HB": [_epoch_tracker(url=u, status=4, msg="rejected by tracker", next_announce=100_000)],
        }
        mgr.web.commands.put(("reannounce_group", {"key": key, "cmd_id": "cmd3"}))
        mgr.web.consume_commands()
        assert "cmd3" not in mgr.web.results
        # HA 前跳命中(ok); HB status4+msg(rejected) -> 聚合 error
        client.trackers_map["HA"][0]["next_announce"] = 105_000
        mgr.web.check_pending()
        r = mgr.web.results["cmd3"]
        assert r["status"] == "error"
        assert "成功 1, 失败 1, 未确认 0" in r["error"]
        assert "失败: tracker 未接受汇报(not working): rejected by tracker" in r["error"]
        assert mgr.web.reannounce_pending == {}
    with tempfile.TemporaryDirectory() as td:
        mgr, client, key = _make_grouped_manager(td)
        u = "https://tracker.hhanclub.net/announce.php"
        fut = _time.time() + 1000  # min_e - t0 = 1000s > 25s -> 双双推迟
        client.trackers_map = {
            "HA": [_epoch_tracker(url=u, status=2, next_announce=fut, min_announce=fut)],
            "HB": [_epoch_tracker(url=u, status=2, next_announce=fut + 5, min_announce=fut)],
        }
        mgr.web.commands.put(("reannounce_group", {"key": key, "cmd_id": "cmd4"}))
        mgr.web.consume_commands()
        items = mgr.web.reannounce_pending["cmd4"]["items"]
        assert all(it["done"] and it["status"] == "warn" for it in items.values()), "推迟 item 注册即出结论"
        assert set(mgr.web.reannounce_background) == {"HA", "HB"}, "推迟 item 登记后台核实"
        mgr.web.check_pending()  # 全部 item 注册时已出结论 -> 下一 tick 即聚合
        r = mgr.web.results["cmd4"]
        assert r["status"] == "warn" and "成功 0, 失败 0, 未确认 2" in r["error"]
        assert r["error"].count("已受理: 最小间隔未过期, 推迟至 ") == 2
        assert mgr.web.reannounce_pending == {}


def test_reannounce_register_immediate_verdicts_and_deadline():
    """注册直判: 停止种子立即 warn; 推迟检出早回执 + 后台登记; item 级 deadline 公式与 600 上限"""
    import time as _time

    with tempfile.TemporaryDirectory() as td:
        mgr, client, key = _make_grouped_manager(td)
        # (a) 停止种子: store 快照 state_enum.is_stopped -> 立即 done+warn, 不等窗口
        rec = mgr.store.get("HA")
        rec.state = "stoppedUP"
        rec._state_enum = None  # 复位惰性缓存(state_enum 按新 state 重算)
        mgr.web.commands.put(("reannounce_torrent", {"hash": "HA", "cmd_id": "cmd5"}))
        mgr.web.consume_commands()
        it = mgr.web.reannounce_pending["cmd5"]["items"]["HA"]
        assert it["done"] and it["status"] == "warn"
        assert it["reason"] == "未确认: 种子已停止, qB 静默忽略强制汇报"
        assert mgr.web.reannounce_background == {}, "停止种子不走推迟后台"
    with tempfile.TemporaryDirectory() as td:
        mgr, client, key = _make_grouped_manager(td)
        u = "https://tracker.hhanclub.net/announce.php"
        fut = _time.time() + 1000
        client.trackers_map = {"HA": [_epoch_tracker(url=u, status=2, next_announce=fut, min_announce=fut)]}
        # (b) 推迟检出: min_e - t0 > 25s -> 立即 warn「已受理」+ 后台登记
        mgr.web.commands.put(("reannounce_torrent", {"hash": "HA", "cmd_id": "cmd6"}))
        mgr.web.consume_commands()
        it = mgr.web.reannounce_pending["cmd6"]["items"]["HA"]
        assert it["done"] and it["status"] == "warn"
        assert it["reason"].startswith("已受理: 最小间隔未过期, 推迟至 ")
        assert it["reason"].endswith("(后台继续核实, 结果见日志)")
        assert it["deadline"] - it["t0"] == 600.0, "窗口公式 capped 600(异常大 min 值不撑爆窗口)"
        bg = mgr.web.reannounce_background["HA"]
        assert bg["min_e"] == fut and bg["baseline"] == it["baseline"] and bg["epoch_mode"] is True
    with tempfile.TemporaryDirectory() as td:
        mgr, client, key = _make_grouped_manager(td)
        u = "https://tracker.hhanclub.net/announce.php"
        # 立即路径: min_e - t0 = 20s(<= 25 不推迟) -> deadline = t0 + max(30, 20+15) = t0+35
        now = _time.time()
        client.trackers_map = {"HA": [_epoch_tracker(url=u, status=2, next_announce=now + 20, min_announce=now + 20)]}
        mgr.web.commands.put(("reannounce_torrent", {"hash": "HA", "cmd_id": "cmd7"}))
        mgr.web.consume_commands()
        it = mgr.web.reannounce_pending["cmd7"]["items"]["HA"]
        assert not it["done"], "min_e - t0 <= 25s 走立即路径轮询"
        assert 34.9 <= it["deadline"] - it["t0"] <= 35.0
        assert "HA" not in mgr.web.reannounce_background
        # 无 min 信息: min_e 按 0 -> max(30, 负) = 30 基础窗口; legacy 行 epoch_mode=False
        client.trackers_map = {"HB": [{"url": u, "status": 1}]}
        mgr.web.commands.put(("reannounce_torrent", {"hash": "HB", "cmd_id": "cmd8"}))
        mgr.web.consume_commands()
        it8 = mgr.web.reannounce_pending["cmd8"]["items"]["HB"]
        assert not it8["done"] and it8["epoch_mode"] is False
        assert 29.9 <= it8["deadline"] - it8["t0"] <= 30.1


def test_reannounce_stopped_midwindow_direct_verdict():
    """窗口内暂停直判: 确认窗口内用户暂停种子 -> 下一 tick 立即 warn「种子已停止」, 不等 deadline"""
    with tempfile.TemporaryDirectory() as td:
        mgr, client, key = _make_grouped_manager(td)
        u = "https://tracker.hhanclub.net/announce.php"
        client.trackers_map = {"HA": [_epoch_tracker(url=u, status=2, next_announce=100_000, min_announce=90_000)]}
        mgr.web.commands.put(("reannounce_torrent", {"hash": "HA", "cmd_id": "cmd9"}))
        mgr.web.consume_commands()
        mgr.web.check_pending()
        assert "cmd9" not in mgr.web.results, "运行中无证据继续等待"
        rec = mgr.store.get("HA")
        rec.state = "stoppedUP"
        rec._state_enum = None
        mgr.web.check_pending()
        r = mgr.web.results["cmd9"]
        assert r["status"] == "warn" and "未确认: 种子已停止" in r["error"]
        assert mgr.web.reannounce_pending == {}


def test_reannounce_background_verify_and_cap():
    """推迟后台核实(D1): 达 min_e 出结论落日志并移除; 逾时静默移除; 500 上限丢最旧并 WARNING"""
    from auto_qb.core.qbmanager import QbManager
    from auto_qb.webui.commands import REANNOUNCE_BACKGROUND_MAX

    base = {"u": {"status": 2, "updating": False, "next": 100_000, "min": 90_000}}

    def _runtime(rows):
        client = SimpleNamespace(torrents_trackers=lambda h: rows)
        return WebUIRuntime(SimpleNamespace(client=client, _verdict_reannounce=QbManager._verdict_reannounce))

    # confirmed: 达 min_e 后前跳 -> INFO 日志后移除
    rt = _runtime([_epoch_tracker(next_announce=105_000)])
    rt.reannounce_background["H_OK"] = {
        "min_e": time.time() - 10,
        "baseline": base,
        "epoch_mode": True,
        "t0": time.time() - 40
    }
    with module_log("auto_qb.webui.runtime") as messages:
        rt.check_pending()
    assert "H_OK" not in rt.reannounce_background
    assert any("后台核实已确认" in m for m in messages)
    # rejected: status4+msg -> WARNING 日志后移除
    rt = _runtime([_epoch_tracker(status=4, msg="nope")])
    rt.reannounce_background["H_BAD"] = {
        "min_e": time.time() - 10,
        "baseline": base,
        "epoch_mode": True,
        "t0": time.time() - 40
    }
    with module_log("auto_qb.webui.runtime") as messages:
        rt.check_pending()
    assert "H_BAD" not in rt.reannounce_background
    assert any("后台核实失败" in m for m in messages)
    # 未达 min_e: 不读不判, 条目保留; 逾时(min_e + TIMEOUT)未出结论 -> DEBUG 静默移除
    rt = _runtime([_epoch_tracker()])
    rt.reannounce_background["H_FUT"] = {
        "min_e": time.time() + 500,
        "baseline": base,
        "epoch_mode": True,
        "t0": time.time()
    }
    rt.reannounce_background["H_OLD"] = {
        "min_e": time.time() - 100,
        "baseline": base,
        "epoch_mode": True,
        "t0": time.time() - 200
    }
    with module_log("auto_qb.webui.runtime") as messages:
        rt.check_pending()
    assert "H_FUT" in rt.reannounce_background, "未达 min_e 不核实"
    assert "H_OLD" not in rt.reannounce_background, "逾时未出结论静默移除"
    assert any("逾时移除" in m for m in messages)
    # 上限 500: 超限丢最旧并 WARNING 一次
    rt = _runtime([_epoch_tracker()])
    for i in range(REANNOUNCE_BACKGROUND_MAX):
        rt.reannounce_background[f"H{i:03d}"] = {
            "min_e": time.time() + 500,
            "baseline": base,
            "epoch_mode": True,
            "t0": time.time()
        }
    host = SimpleNamespace(
        client=SimpleNamespace(torrents_trackers=lambda h: []),
        store=SimpleNamespace(get=lambda h: None),
        _verdict_reannounce=QbManager._verdict_reannounce,
    )
    host.web = rt
    fut = time.time() + 1000  # min_e - t0 > 25s: HNEW 以推迟身份登记, 触发超限逐出
    bg_base = {"u": {"status": 2, "updating": False, "next": fut, "min": fut}}
    with module_log("auto_qb.webui.commands") as cmd_messages:
        QbManager._register_reannounce_pending(host, "cmd_bg", ["HNEW"], {"HNEW": bg_base}, True)
    assert len(rt.reannounce_background) == REANNOUNCE_BACKGROUND_MAX
    assert "H000" not in rt.reannounce_background and "HNEW" in rt.reannounce_background, "超限丢最旧"
    assert any("丢弃最旧" in m for m in cmd_messages)


def test_cmd_group_actions_skip_missing_group():
    """组级命令: 组 key 不存在或成员已不在快照 -> 空 hashes, 不调 qB API"""
    with tempfile.TemporaryDirectory() as td:
        mgr, client, key = _make_grouped_manager(td)
        gone = ("R:/gone", ("x.mkv", ))
        mgr.store.groups[gone] = ["NOT_IN_STORE"]  # 成员不在快照 -> _group_hashes 过滤为空
        assert mgr._group_hashes(gone) == []
        for cmd in ("pause_group", "resume_group", "reannounce_group", "delete_group"):
            mgr.web.commands.put((cmd, {"key": gone}))
        mgr.web.commands.put(("pause_group", {"key": ("R:/nonexistent", ("y.mkv", ))}))  # 组 key 不存在
        mgr.web.consume_commands()
        assert client.calls == [], f"空组不应调用 qB API: {client.calls}"


def test_cmd_reload_config_delegates():
    """_cmd_reload_config: 委托 apply_new_config(热重载分级应用逻辑本身由 config 影响分析测试覆盖)"""
    with tempfile.TemporaryDirectory() as td:
        mgr, client, key = _make_grouped_manager(td)
        applied = []
        mgr.apply_new_config = lambda cfg: applied.append(cfg) or {"applied": True}
        new_cfg = object()
        mgr.web.commands.put(("reload_config", {"config": new_cfg}))
        mgr.web.consume_commands()
        assert applied == [new_cfg], "reload_config 命令应把新配置交给 apply_new_config"
