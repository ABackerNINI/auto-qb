"""test_web_commands_dispatch 测试计划: Web 命令执行 (_drain_web_commands) 与强制汇报确认

## 测试计划(每个测试函数一条)
- test_drain_web_commands_group_actions: 组级暂停/开始/汇报/删除命令执行并作用于整组 hash
- test_drain_web_commands_torrent_actions: 单种子命令作用于该 hash; 种子不在快照 -> 跳过(删除守阵)
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
- test_cmd_group_actions_skip_missing_group: 组 key 不存在/成员不在快照 -> 空 hashes 不调 API
- test_cmd_reload_config_delegates: reload_config 命令委托 apply_new_config
- test_build_search_index_still_dirty_skips_completion_log: 索引仍脏不落「已构建」完成日志(分批不刷屏)
- test_reannounce_group_no_cmd_id_and_inactive_group: 组汇报直驱 —— 无 cmd_id 照发不写回执; 全非活跃 warn
- test_bulk_guard_matrix_without_cmd_id: bulk 早退守卫矩阵(无 cmd_id 直投): 七类非法载荷只 return 不写回执不调 API(第 7 类 = 部分组闸拒早退, issue 26-11-11-0823)
- test_cmd_handlers_without_cmd_id_stay_silent: 无 cmd_id 一侧全覆盖(CLI/内部触发旁路) —— 14 处 `if cmd_id:` 假弧 + _bulk_receipt 两档 + _bulk_missing_msgs 缺失组文案 + skip_check 菜单关早退 + 部分组闸拒静默早退(issue 26-11-11-0823) + add_torrents 无回执: 不写回执(空键不出现)、不炸、日志照记
- test_drain_web_commands_bulk_torrents_group_keys_mixed_and_missing
"""

import tempfile

import time

from types import SimpleNamespace

from auto_qb.infra.utils import encode_group_key, mask_tracker_url

from auto_qb.webui.runtime import WebUIRuntime

from helpers import capture_logs

from webui_helpers import _make_grouped_manager


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
    """二轮写命令: 参数正确传给 QbApi(真链路), cmd_id 回执 ok, 限速同 tick 生效; 保存路径**等上报**"""
    with tempfile.TemporaryDirectory() as td:
        mgr, client, key = _make_grouped_manager(td)
        old_save_path = mgr.store.get("HA").save_path
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
        assert client.calls[5] == ("set_share_limits", (1.5, -1, -2, "Default", "Default")), \
            "share-limits 三值映射 + mode/action 恒传 Default(5.3/5.0+ 必填参, 缺失 400)"
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
        assert rec.up_limit == 1024 and rec.dl_limit == 2048, "限速是确定性字段: 写后同步"
        assert rec.save_path == old_save_path, "保存路径改为等上报(26-10-21-2323 S2)"


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
        # share-limits 缺省维度 -2 补齐; mode/action 恒传 Default(qB 5.3 必填 shareLimitsMode /
        # 5.0+ 必填 shareLimitAction, 缺失 400; facade docstring 已修正 None 语义: 库对 None 值键
        # 一律不发, 非"发字面量 None")
        mgr.web.commands.put(("set_share_limits", {"hash": "HA", "ratio_limit": 2.0}))
        mgr.web.consume_commands()
        assert client.calls[-1] == ("set_share_limits", (2.0, -2, -2, "Default", "Default")), client.calls[-1]
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
        # delete: delete_files 透传, 成员从快照移除 —— 平铺全组(部分组×带文件删除已被
        # 部分组闸门 fail-closed 拒收, issue 26-11-11-0823; 拒收面电池在 test_web_commands_bulk)
        mgr.web.commands.put(
            ("bulk_torrents", {
                "hashes": ["HA", "HB"],
                "action": "delete",
                "delete_files": True,
                "cmd_id": "b3"
            })
        )
        mgr.web.consume_commands()
        assert client.calls[-1] == ("delete", True)
        assert mgr.store.get("HA") is None and mgr.store.get("HB") is None
        assert mgr.web.results["b3"]["status"] == "ok"
        # b3 已删全组, b4 需要一个存活种子 —— 重灌 HB(FakeClient 的 delete 会连 client.torrents
        # 一并弹出; seed_store 不传列表 = 全量口径, 见 test_web_commands_bulk._seed_group 注)
        from helpers import FakeTorrent, _fake_file, seed_store

        hb = FakeTorrent(hash="HB", name="Show", save_path=r"R:\Downloads")
        client.torrents["HB"] = hb
        client.files_map["HB"] = [_fake_file("movie.mkv", 100)]
        seed_store(mgr)
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
        # location: 一次调用传全 hashes; 快照 save_path 不改(等上报, 26-10-21-2323 S2)
        save_before = mgr.store.get("HA").save_path
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
        assert mgr.store.get("HA").save_path == save_before, "save_path 等 qB 上报, 不在命令后改写"
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


def test_build_search_index_still_dirty_skips_completion_log():
    """索引构建后仍脏(分批未完成): 不落「已构建」完成日志(避免分批刷屏)"""
    with tempfile.TemporaryDirectory() as td:
        mgr, _client, _key = _make_grouped_manager(td)
        mgr.build_search_index = lambda: None  # 分批构建的中间轮: 索引仍脏
        mgr.web.search_index_dirty = True
        mgr.web.commands.put(("build_search_index", {}))
        with capture_logs("auto_qb.webui.commands") as cap:
            mgr.web.consume_commands()
        assert not any("搜索索引已构建" in m for m in cap.messages), "仍脏不得报完成"
        assert mgr.web.search_index_dirty is True


def test_reannounce_group_no_cmd_id_and_inactive_group():
    """组汇报直驱: 无 cmd_id 照发不写回执; 全非活跃 warn 回执(有无 cmd_id 两路)"""
    from helpers import FakeTorrent

    with tempfile.TemporaryDirectory() as td:
        mgr, client, key = _make_grouped_manager(td)
        cmds = mgr
        # 无 cmd_id: 只发指令, 不写回执(524->530 守卫另一侧)
        cmds._cmd_reannounce_group(key)
        assert ("reannounce", None) in client.calls or ("reannounce", ["HA", "HB"]) in client.calls, client.calls
        assert mgr.web.results.get("never", None) is None

        # 组内成员全部非活跃(快照置 pausedUP): 有 cmd_id -> warn 回执 + 不发指令
        for h in ("HA", "HB"):
            mgr.store.get(h).state = "pausedUP"
        client.calls.clear()
        cmds._cmd_reannounce_group(key, cmd_id="c-inactive")
        rec = mgr.web.results.get("c-inactive")
        assert rec is not None and rec["status"] == "warn" and "均非活跃" in rec["error"]
        assert ("reannounce", None) not in client.calls and not any(c[0] == "reannounce" for c in client.calls)


def test_bulk_guard_matrix_without_cmd_id():
    """bulk 早退守卫矩阵(无 cmd_id 直投队列): 每个非法载荷只 return 不写回执不调 API(七类)"""
    with tempfile.TemporaryDirectory() as td:
        mgr, client, key = _make_grouped_manager(td)
        bad_payloads = [
            {
                "hashes": ["HA"],
                "action": "nope"
            },  # 未知动作
            {
                "hashes": [],
                "action": "pause"
            },  # 空 hash 列表
            {
                "hashes": ["HA"],
                "action": "add_tags"
            },  # 缺 tags
            {
                "hashes": ["HA"],
                "action": "set_category"
            },  # 缺 category(None)
            {
                "hashes": ["HA"],
                "action": "limits"
            },  # limits 两方向全空
            {
                "hashes": ["HA"],
                "action": "location"
            },  # 缺目标路径
            {
                "hashes": ["HA"],
                "action": "delete",
                "delete_files": True
            },  # 部分组×带文件删除(闸拒早退, issue 26-11-11-0823): HA/HB 同组, HA 是部分组
        ]
        for payload in bad_payloads:
            mgr.web.commands.put(("bulk_torrents", payload))
        mgr.web.consume_commands()
        assert mgr.web.results == {}, "无 cmd_id 的非法载荷不得写回执"
        assert client.calls == [], "非法载荷不得触达 qB API"


def test_cmd_handlers_without_cmd_id_stay_silent(monkeypatch):
    """无 cmd_id 一侧全覆盖: 各 handler 的 `if cmd_id:` 假弧 + _bulk_* 单点 + 直投旁路

    真机除 Web 前端外还有 CLI/内部触发等**不经回执通道**的调用方; 既有用例几乎都带
    cmd_id(回执正是被断言的对象), 于是 commands.py 里 14 处 `if cmd_id:` 的假弧全滞留
    partial —— 把 `if cmd_id:` 误改成无条件 `_set_web_result` 写空键这条回归没人看得见。
    本用例逐 handler 过一遍无 cmd_id 一侧: 不写回执(空键不出现)、不炸、指令/日志照旧
    (含 commands_torrents.py 部分组闸拒的 `if cmd_id:` 假弧, issue 26-11-11-0823)。
    """
    from auto_qb.infra.utils import encode_group_key

    with tempfile.TemporaryDirectory() as td:
        mgr, client, key = _make_grouped_manager(td)
        cmds = mgr

        # 组汇报: 全非活跃整组跳过(524->530) + 单种逐 hash 跳过(568->570)
        for h in ("HA", "HB"):
            mgr.store.get(h).state = "pausedUP"
        client.calls.clear()
        cmds._cmd_reannounce_group(key)
        cmds._cmd_reannounce_torrent("HA")
        assert not any(c[0] == "reannounce" for c in client.calls), "非活跃不得发指令"

        # recheck / skip_check 单种: ops 受理与拒绝两档, 无 cmd_id 均静默(666/670/684/688)
        monkeypatch.setattr(mgr.ctx.ops, "recheck", lambda *a, **k: SimpleNamespace(is_ok=True, message="ok"))
        cmds._cmd_recheck_torrent("HA")
        monkeypatch.setattr(
            mgr.ctx.ops, "recheck", lambda *a, **k: SimpleNamespace(is_ok=False, is_pending=False, message="校验进行中")
        )
        cmds._cmd_recheck_torrent("HA")
        monkeypatch.setattr(mgr.ctx.ops, "skip_check", lambda *a, **k: SimpleNamespace(is_ok=True, message="ok"))
        cmds._cmd_skip_check_torrent("HA")
        monkeypatch.setattr(mgr.ctx.ops, "skip_check", lambda *a, **k: SimpleNamespace(is_ok=False, message="今天已跳过"))
        cmds._cmd_skip_check_torrent("HA")

        # 预检族 + 撤销: 无 cmd_id 只聚合日志不写回执(706/726/739/754)
        monkeypatch.setattr(mgr.ctx.ops, "skip_check_precheck", lambda req: [])
        cmds._cmd_skip_check_precheck(["HA"])
        monkeypatch.setattr(mgr.ctx.relocate, "relocate_precheck", lambda req, loc: [])
        monkeypatch.setattr(mgr.ctx.relocate, "precheck_add", lambda s, n: {"cls": "ok"})
        monkeypatch.setattr(mgr.ctx.relocate, "relocate_cancel", lambda j, cost_confirmed: {"cls": "confirm"})
        cmds._cmd_relocate_precheck(["HA"], "R:/x")
        cmds._cmd_relocate_precheck_add("R:/x", "n")
        cmds._cmd_relocate_cancel("job-1")

        # _bulk_receipt 单点无 cmd_id 两档: 有异常文案(1122->1124) / 全清(1126->1128)
        cmds._bulk_receipt("", ["1/2 个种子不存在或已被删除"], "批量 recheck(提交 1 个种子)", "批量 recheck(提交 1, 跳过 0, 失败 1)")
        cmds._bulk_receipt("", [], "批量 recheck(提交 1 个种子)", "批量 recheck(提交 1, 跳过 0, 失败 1)")

        # bulk 分派: skip_check_menu 关闭 + 无 cmd_id -> 静默早退(1026->1028)
        monkeypatch.setattr(mgr.ctx.config.web, "skip_check_menu", False)
        cmds._cmd_bulk_torrents(hashes=["HA"], action="skip_check")
        monkeypatch.setattr(mgr.ctx.config.web, "skip_check_menu", True)

        # bulk 部分组闸拒: 无 cmd_id -> 静默早退(issue 26-11-11-0823) —— HA/HB 同组即部分组;
        # 闸拒的 return 若误挪进 if cmd_id: 内, 直投队列的部分组 delete_files 会直发 qB 删共享文件
        cmds._cmd_bulk_torrents(hashes=["HA"], action="delete", delete_files=True)

        # 批量缺失: 无 cmd_id 只记日志(1090->1092); 缺失组走 _bulk_missing_msgs 单点(1111)
        bad_key = encode_group_key(("R:/no-such", ("x.mkv", )))
        monkeypatch.setattr(
            mgr.ctx.ops,
            "recheck",
            lambda h, source=None: SimpleNamespace(is_ok=True, is_skipped=False, is_failed=False, message="ok")
        )
        cmds._cmd_bulk_torrents(hashes=["HA"], keys=[bad_key], action="recheck", cmd_id="c-mgm")
        cmds._cmd_bulk_torrents(hashes=["GONE"], keys=[bad_key], action="pause")

        # 添加种子: 无 cmd_id 只落日志不写回执(1375->1385)
        f = td + "/x.torrent"
        with open(f, "wb") as fh:
            fh.write(b"d8:announce3:fooe")
        cmds._cmd_add_torrents(files=[f])

        # 总断言: 全程只有带 cmd_id 的那一次写了回执, 空键从未出现
        assert set(mgr.web.results) == {"c-mgm"}, mgr.web.results
        assert "" not in mgr.web.results, "无 cmd_id 不得以空键写回执"
        assert "个组不存在或成员为空" in mgr.web.results["c-mgm"]["error"]
