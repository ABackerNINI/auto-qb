"""test_web_hr_endpoints 测试计划: HR web 端点与搜索 / 文件系统端点

## 测试计划(每个测试函数一条)
- test_api_hr_site_entries_full_fields: 种子明细端点(计划 26-10-01-2216 §7 阶段1)200 全字段 —— 行键面 = §3 P0+P1 全集
- test_api_hr_site_entries_local_present: 明细行 local_present 本地库 join(计划 26-10-02-1936 §3.3 决策点 3a) ——
  v1 命中/仅 v2 命中/大小写差异命中 -> True, 本地不存在 -> False(未做种)
- test_api_hr_site_entries_verified_two_states: verified 有/无两态同表(无记录→未核实; 有记录→verified_ts+source 原值+人话)
- test_api_hr_site_entries_empty_site: 站点已接入但没有 HR 行 -> 200 + 空数组(前端空态)
- test_api_hr_site_entries_guards: HR 未启用 400 / 站点未接入 404(与 confirm-empty 同款话术)
- test_api_hr_site_entries_409_worker_absent: hr 门面在但取数服务缺席(service=None) -> 409 不假装有数据
- test_hr_route_guard_single_point: 守阵(issue webui-hr-route-guard-dup) HR 路由前置守卫与启用站点派生各走单点 —— 派生式/hr_check 读取各只一份 + 三档校验码(400/404/409)不变
- test_api_hr_history_rows_from_real_wave: 拉取历史端点(计划 26-10-04-0312 §3.4)200 —— 行键面 = §3.4 全集,
  真实波次(S2 记录器)落表; 完成徽章/触发人话/档位 lane_text/写者短标识全由后端算好
- test_api_hr_history_site_filter: site 过滤只回该站; 未接入 404 点名已接入清单(与 entries 同款话术)
- test_api_hr_history_guards: HR 未启用 400 / 取数服务缺席 409(与 entries 同款校验)
- test_api_hr_history_limit_clamped: limit 截最新 N 条; 0 钳到 1(不回全量也不回空页)
- test_api_hr_history_read_error_reported_not_raised: 站点文件读坏不抛 —— read_errors{site: err} 带出, rows 剔掉坏站
- test_api_state_excludes_hr_entry_details: 体积守卫 —— 种子明细键不得进 /api/state 轮询载荷(计划 §8)
- test_hr_user_visible_texts_no_graduation_wording: 否定守阵 —— 用户可见文案来源(hr status/resolve/events 字符串常量)「毕业」零残留
  (注释保留域术语, 决策点 2); 无事实分支与带事实分支同文「在线·已达标」(testhr_view_fields_three_state 内钉)
- test_api_hr_refresh_single_site_and_no_runtime: refresh 指定单站受理 + hr 门面缺席回 409
- test_api_hr_confirm_empty: 人工对账戳端点(缺 site/未启用/未接入 400, 成功 ok, 写入失败 409)
- test_api_events_sse_stream_lifecycle: SSE 生成器整块(hello 帧/事件帧/keepalive 心跳/终结退订;
  TestClient 会挂死无限流, 直调端点驱动 body_iterator)
- test_api_events_sse_generator_error_still_unsubscribes: 生成器异常死亡也走 finally 退订
- testhr_view_fields_three_state: 详情字段透出站点侧三态与依据(接入站点才有值, 未接入全空)
- testhr_view_fields_excluded: HR 排除态视图(hr_excluded=True, 触发/达标 False, 站点侧全空, 桥不被打扰)
- test_api_hr_status_disabled_returns_empty_state: 未启用 HR 时 /api/hr/status 回 enabled=false + 说明(前端空态, 不报错)
- test_api_hr_status_reports_site_state: 启用后逐站点摊开现状 —— 新鲜度/覆盖证明/索引与回填进度/配额/熔断/
  「现在为什么不放行」(与 --hr-status 同一 `hr.status` 口径) + 波次明细 lane_text 徽章人话逐档正确(LANE_TEXTS 单点)
- test_api_hr_status_names_the_blocking_step: 覆盖证明不成立时要说清卡在哪一步(用户看到种子没放行时最想知道的一句)
- test_api_hr_refresh_409_when_worker_not_running
- test_api_hr_refresh_accepts_and_returns_requested
- test_api_hr_refresh_requires_enabled_hr
- test_frontend_hr_status_fields_match_backend
"""

import json

import os

import re

import sys

import tempfile

import time

from pathlib import Path

from types import SimpleNamespace

from unittest import mock

import pytest

from platform_tolerance import SLEEP_LOWER_MARGIN_S

from auto_qb.infra import file_access

from auto_qb.infra.utils import encode_group_key

from webui_helpers import _UI_ALL, _ui_aggregate, _hr_status_env, ENTRY_ROW_KEYS_API, HISTORY_ROW_KEYS

from web_hr_support import (
    _AUTH_HEADER_KEY,
)


def test_api_hr_refresh_accepts_and_returns_requested(web_env, tmp_path):
    """成功受理: 调 manager.hr.request_refresh(与插件端点同一实现)并回受理清单"""
    mgr, client = web_env
    _hr_status_env(mgr, tmp_path)
    calls = []

    def _fake_request_refresh(sites=None):
        calls.append(sites)
        return {"requested": ["HHan"], "note": "已受理, 取数由取数线程执行"}

    mgr.hr.request_refresh = _fake_request_refresh
    auth = {_AUTH_HEADER_KEY: f"Bearer {mgr.web.token}"}
    body = client.post("/api/hr/refresh", json={}, headers=auth).json()
    assert body["ok"] is True and body["requested"] == ["HHan"]
    assert calls == [None], "缺省 = 全部启用站点(不逐站点名)"


def test_api_hr_refresh_requires_enabled_hr(web_env, tmp_path):
    """HR 未启用 -> 400; 未接入的站点 -> 400(不受理无档案站点)"""
    mgr, client = web_env
    _hr_status_env(mgr, tmp_path)
    mgr.hr.request_refresh = lambda sites=None: {"requested": ["HHan"], "note": ""}
    auth = {_AUTH_HEADER_KEY: f"Bearer {mgr.web.token}"}
    mgr.config.hr_check.enabled = False
    assert client.post("/api/hr/refresh", json={}, headers=auth).status_code == 400
    mgr.config.hr_check.enabled = True
    r = client.post("/api/hr/refresh", json={"site": "Nope"}, headers=auth)
    assert r.status_code == 400 and "Nope" in r.json()["detail"]


def test_api_hr_refresh_409_when_worker_not_running(web_env, tmp_path):
    """取数线程未启动 -> 409(「现在拉不了」的如实形态, 不假装成功)"""
    mgr, client = web_env
    _hr_status_env(mgr, tmp_path)
    mgr.hr.request_refresh = lambda sites=None: {"requested": [], "note": "取数线程未启动"}
    auth = {_AUTH_HEADER_KEY: f"Bearer {mgr.web.token}"}
    r = client.post("/api/hr/refresh", json={}, headers=auth)
    assert r.status_code == 409 and "取数线程未启动" in r.json()["detail"]


def test_api_hr_site_entries_full_fields(web_env, tmp_path):
    """200 全字段: 行键面 = 计划 §3 P0+P1 全集(前端只消费后端算好字段, 不重算)"""
    mgr, client = web_env
    _hr_status_env(mgr, tmp_path)
    auth = {_AUTH_HEADER_KEY: f"Bearer {mgr.web.token}"}
    r = client.get("/api/hr/sites/HHan/entries", headers=auth)
    assert r.status_code == 200
    body = r.json()
    assert body["site"] == "HHan" and body["read_error"] == "" and body["now"] > 0
    assert len(body["entries"]) == 1
    row = body["entries"][0]
    assert set(row) == ENTRY_ROW_KEYS_API
    assert row["tid"] == 101 and row["name"]
    assert row["infohash_v1"] and row["infohash_v2"], "取过 .torrent 的行 v1/v2 都已回填"
    assert row["local_present"] is False, "夹具本地库为空 -> 全部行是未做种(local_present join 响应层追加)"
    assert row["need_seed_seconds"] is not None and row["need_seed_text"] not in ("", None)
    assert row["lane"] and row["lane_text"], "档位原值 + 人话都要给"
    assert row["active"] is True and "done_iso" in row
    assert row["first_seen"] >= 0.0 and row["last_seen"] >= 0.0, "first_seen/last_seen 原样透传(写入行为属取数管道, 不在此钉)"


def test_api_hr_site_entries_local_present(web_env, tmp_path):
    """local_present 本地库 join(计划 26-10-02-1936 §3.3, 决策点 3a): 明细端点每行带只读标记

    真实 join 用例(端点级): v1 精确命中 / 仅 v2 命中 / 大小写差异命中 -> True;
    本地不存在 -> False(未做种, 含本地从未下载的清单行)。join 键口径单点在
    routes.hr.mark_local_present(纯函数四态由 test_hr_status 钉)。
    """
    mgr, client = web_env
    _hr_status_env(mgr, tmp_path)
    auth = {_AUTH_HEADER_KEY: f"Bearer {mgr.web.token}"}

    def first_row():
        return client.get("/api/hr/sites/HHan/entries", headers=auth).json()["entries"][0]

    r0 = first_row()
    assert r0["local_present"] is False, "本地库为空 -> 未做种"
    h1, h2 = r0["infohash_v1"], r0["infohash_v2"]
    assert h1 and h2, "夹具行 v1/v2 均已回填(不然测不了双键探测)"

    mgr.store.by_hash.clear()
    mgr.store.by_hash[h1] = mock.Mock()
    assert first_row()["local_present"] is True, "v1 命中"

    mgr.store.by_hash.clear()
    mgr.store.by_hash[h2] = mock.Mock()
    assert first_row()["local_present"] is True, "仅 v2 命中(v1 未收录的终态冻结形态)"

    mgr.store.by_hash.clear()
    mgr.store.by_hash[h1.upper()] = mock.Mock()
    assert first_row()["local_present"] is True, "大小写差异命中(站点清单与 qB hash 书写形态不同)"

    mgr.store.by_hash.clear()
    mgr.store.by_hash["deadbeef"] = mock.Mock()
    assert first_row()["local_present"] is False, "本地只有别的种子 -> 未做种"


def test_api_hr_site_entries_verified_two_states(web_env, tmp_path):
    """verified 有/无两态同表: 无记录→未核实(0/""/"未核实"); 有记录→verified_ts + source 原值 + 人话"""
    mgr, client = web_env
    svc = _hr_status_env(mgr, tmp_path)
    auth = {_AUTH_HEADER_KEY: f"Bearer {mgr.web.token}"}
    row = client.get("/api/hr/sites/HHan/entries", headers=auth).json()["entries"][0]
    assert row["verified_ts"] == 0.0
    assert row["verified_source"] == "" and row["verified_source_text"] == "未核实"
    # 注入放行记录(持锁会话写站点文件 —— 与端点读的是同一份数据), 再验有记录态
    from auto_qb.hr.model import SOURCE_EXEMPT, HrVerified

    ts = 1_759_000_000.0
    with svc.store("HHan").hold() as session:
        h = session.data.index[101].infohash_v1
        session.data.verified[h] = HrVerified(infohash=h, tid=101, verified_ts=ts, source=SOURCE_EXEMPT)
        assert session.commit(time.time()) == "written"
    row = client.get("/api/hr/sites/HHan/entries", headers=auth).json()["entries"][0]
    assert row["verified_ts"] == ts
    assert row["verified_source"] == "absent" and row["verified_source_text"] == "D 免罪"


def test_api_hr_site_entries_empty_site(web_env, tmp_path):
    """站点已接入但没有 HR 行 -> 200 + 空数组(前端显示空态, 不当错误)"""
    mgr, client = web_env
    from hr_helpers import EMPTY_TABLE_PAGE

    _hr_status_env(mgr, tmp_path, pages={"A": EMPTY_TABLE_PAGE, "B": EMPTY_TABLE_PAGE, "C": EMPTY_TABLE_PAGE})
    auth = {_AUTH_HEADER_KEY: f"Bearer {mgr.web.token}"}
    r = client.get("/api/hr/sites/HHan/entries", headers=auth)
    assert r.status_code == 200
    assert r.json()["entries"] == []


def test_api_hr_site_entries_guards(web_env, tmp_path):
    """HR 未启用 -> 400; 站点未接入 -> 404 并点名已接入清单(与 confirm-empty 同款话术)"""
    mgr, client = web_env
    _hr_status_env(mgr, tmp_path)
    auth = {_AUTH_HEADER_KEY: f"Bearer {mgr.web.token}"}
    mgr.config.hr_check.enabled = False
    assert client.get("/api/hr/sites/HHan/entries", headers=auth).status_code == 400
    mgr.config.hr_check.enabled = True
    r = client.get("/api/hr/sites/Nope/entries", headers=auth)
    assert r.status_code == 404 and "Nope" in r.json()["detail"]


def test_api_hr_site_entries_409_worker_absent(web_env, tmp_path):
    """hr 门面在但 service 缺席(取数线程未启动的实例形态) -> 409「线程未启动」, 不假装有数据"""
    mgr, client = web_env
    _hr_status_env(mgr, tmp_path)
    mgr.hr.service = None
    auth = {_AUTH_HEADER_KEY: f"Bearer {mgr.web.token}"}
    r = client.get("/api/hr/sites/HHan/entries", headers=auth)
    assert r.status_code == 409 and "取数线程未启动" in r.json()["detail"]


def test_hr_route_guard_single_point(web_env, tmp_path):
    """守阵: HR 路由的「前置守卫」与「启用站点集派生」各走单点(issue webui-hr-route-guard-dup)

    此前 hr.py 五个端点各自重写同一段守卫(取 hr_check → 未启用 400 / service 缺位 409)共 5 处,
    且「启用 hr_check 的站点集」推导式逐字同 4 处 —— 开一个端点要成套抄守卫, 改校验口径要改多处。
    静态: 派生式全文只一份(在 `_hr_enabled_sites`); `getattr(manager.config, "hr_check", None)`
    只一份(在 `_hr_conf` 读取单点, 守卫收进 `_require_hr_enabled`)。
    行为: 三档校验码与话术不变(未启用 400 / 站点未接入 404 / service 缺席 409)。
    红验: 任一端点写回自己的守卫块或派生式, 静态半判红; 改状态码/话术, 行为半判红。
    """
    from pathlib import Path

    src = Path(__file__).resolve().parents[1] / "src" / "auto_qb" / "webui" / "server" / "routes" / "hr.py"
    text = src.read_text(encoding="utf-8")
    assert text.count("tc.hr_check is not None and tc.hr_check.enabled") == 1, "启用站点派生必须只有一份"
    assert text.count('getattr(manager.config, "hr_check", None)') == 1, "hr_check 读取必须收进 _hr_conf 单点"

    mgr, client = web_env
    _hr_status_env(mgr, tmp_path)
    auth = {_AUTH_HEADER_KEY: f"Bearer {mgr.web.token}"}
    mgr.config.hr_check.enabled = False
    for path, method in (("/api/hr/sites/HHan/entries", "get"), ("/api/hr/history", "get")):
        assert getattr(client, method)(path, headers=auth).status_code == 400, f"{path} 未启用须 400"
    mgr.config.hr_check.enabled = True
    r = client.get("/api/hr/sites/Nope/entries", headers=auth)
    assert r.status_code == 404 and "Nope" in r.json()["detail"], "站点未接入 404 点名清单"
    mgr.hr.service = None
    r = client.get("/api/hr/history", headers=auth)
    assert r.status_code == 409 and "取数线程未启动" in r.json()["detail"], "service 缺席 409"


def test_api_hr_history_rows_from_real_wave(web_env, tmp_path):
    """200: 真实波次(S2 记录器落的事件)进历史表 —— 行键面 = §3.4 全集, 人话徽章后端算好"""
    mgr, client = web_env
    _hr_status_env(mgr, tmp_path)
    auth = {_AUTH_HEADER_KEY: f"Bearer {mgr.web.token}"}
    r = client.get("/api/hr/history", headers=auth)
    assert r.status_code == 200
    body = r.json()
    assert body["enabled"] is True and body["read_errors"] == {} and body["now"] > 0
    assert body["rows"], "夹具跑过一轮真实波, 历史表不能是空的"
    row = body["rows"][0]
    assert set(row) == HISTORY_ROW_KEYS
    assert row["site"] == "HHan" and row["kind"] == "wave"
    assert row["result_text"] == "完成" and row["result_tone"] == "ok", "三档全跑完的波 -> 完成徽章(映射单点在 hr.status)"
    assert row["trigger"] == "auto" and row["trigger_text"] == "自动"
    assert row["ts"] > 0 and row["ts_text"] and row["elapsed_text"], "epoch 与人话并给(排序用原值, 展示用文案)"
    assert row["lanes"] and all(l["lane_text"] for l in row["lanes"]), "各档 lane_text 人话随行给出"
    assert row["by"] == "tester", "写者实例短标识随事件透传(多实例分辨「谁抓的」)"


def test_api_hr_history_site_filter(web_env, tmp_path):
    """site 过滤: 给了就只回该站; 未接入的站点 404 并点名已接入清单(与 entries 同款话术)"""
    mgr, client = web_env
    _hr_status_env(mgr, tmp_path)
    auth = {_AUTH_HEADER_KEY: f"Bearer {mgr.web.token}"}
    r = client.get("/api/hr/history?site=HHan", headers=auth)
    assert r.status_code == 200
    rows = r.json()["rows"]
    assert rows and all(row["site"] == "HHan" for row in rows), "过滤键生效, 行只来自指定站点"
    r = client.get("/api/hr/history?site=Nope", headers=auth)
    assert r.status_code == 404 and "Nope" in r.json()["detail"] and "HHan" in r.json()["detail"]


def test_api_hr_history_guards(web_env, tmp_path):
    """HR 未启用 -> 400; 取数服务缺席(service=None) -> 409(与 entries 同款校验口径)"""
    mgr, client = web_env
    _hr_status_env(mgr, tmp_path)
    auth = {_AUTH_HEADER_KEY: f"Bearer {mgr.web.token}"}
    mgr.config.hr_check.enabled = False
    assert client.get("/api/hr/history", headers=auth).status_code == 400
    mgr.config.hr_check.enabled = True
    mgr.hr.service = None
    r = client.get("/api/hr/history", headers=auth)
    assert r.status_code == 409 and "取数线程未启动" in r.json()["detail"]


def test_api_hr_history_limit_clamped(web_env, tmp_path):
    """limit 查询参数: 截最新的 N 条; 0 钳到 1(FastAPI 只管 int 解析, 卫生钳制在这层做)"""
    mgr, client = web_env
    svc = _hr_status_env(mgr, tmp_path)
    auth = {_AUTH_HEADER_KEY: f"Bearer {mgr.web.token}"}
    from auto_qb.hr.model import HrHistoryEvent

    # 合成事件用未来时刻: 夹具真实波的 ts = 当前时间, 必须保证它排不进「最新 N 条」
    base = time.time() + 1000.0
    with svc.store("HHan").hold() as session:
        for offset in (1000.0, 2000.0, 3000.0):
            session.data.history.append(HrHistoryEvent(ts=base + offset, kind="wave", action="refreshed"))
        assert session.commit(time.time()) == "written"
    rows = client.get("/api/hr/history?limit=2", headers=auth).json()["rows"]
    assert [r["ts"] for r in rows] == [base + 3000.0, base + 2000.0], "limit 截最新的 N 条"
    rows = client.get("/api/hr/history?limit=0", headers=auth).json()["rows"]
    assert len(rows) == 1, "limit<=0 钳到 1(不回全量也不回空页)"


def test_api_hr_history_read_error_reported_not_raised(web_env, tmp_path):
    """站点文件读坏不抛: read_errors{site: err} 原样带出, rows 剔掉坏站(表 1 同款只读口径)"""
    mgr, client = web_env
    svc = _hr_status_env(mgr, tmp_path)
    auth = {_AUTH_HEADER_KEY: f"Bearer {mgr.web.token}"}
    svc.store("HHan").path.write_text("{not-json", encoding="utf-8")
    r = client.get("/api/hr/history", headers=auth)
    assert r.status_code == 200
    body = r.json()
    assert body["rows"] == [], "坏站的数据不进行集(历史表宁缺勿错)"
    assert "HHan" in body["read_errors"] and body["read_errors"]["HHan"], "坏文件本身就是要人看的信息"


def test_api_state_excludes_hr_entry_details(web_env):
    """体积守卫: 种子明细键不得进 /api/state 轮询载荷(计划 §8) —— 明细只随表 1 按站点按需拉"""
    mgr, client = web_env
    auth = {_AUTH_HEADER_KEY: f"Bearer {mgr.web.token}"}
    text = json.dumps(client.get("/api/state", headers=auth).json(), ensure_ascii=False)
    for key in ("need_seed_text", "verified_source_text", "lane_text", "missing_streak", "local_present"):
        assert f'"{key}"' not in text, f"/api/state 轮询载荷混入了明细键 {key}"


def test_hr_user_visible_texts_no_graduation_wording():
    """否定守阵(计划 26-10-02-1936 §3.5): 用户可见文案来源「毕业」零残留

    扫 hr/status.py(SOURCE_TEXTS 等)· hr/resolve.py(放行依据文案表 / safety_display 人话)·
    hr/events.py(告警行)的**字符串常量**(AST 层取, 注释天然不在其列 —— 注释按决策点 2
    保留「毕业」域术语, grep 可溯源)。前端静态文案归阶段 2-3 守阵, 不在此。
    """
    import ast

    hr_dir = Path(__file__).resolve().parents[1] / "src" / "auto_qb" / "hr"
    for name in ("status.py", "resolve.py", "events.py"):
        tree = ast.parse((hr_dir / name).read_text(encoding="utf-8"), filename=name)
        offenders = [
            n.value
            for n in ast.walk(tree) if isinstance(n, ast.Constant) and isinstance(n.value, str) and "毕业" in n.value
        ]
        assert not offenders, f"{name} 的用户可见字符串残留「毕业」: {offenders!r}"


def test_api_hr_refresh_single_site_and_no_runtime(web_env, tmp_path):
    """refresh 补遗: 指定 site -> request_refresh 收到 ["HHan"](单站受理, 不是全部);
    hr 门面整个缺席(getattr = None) -> 409「线程未启动」, 不是 500"""
    mgr, client = web_env
    _hr_status_env(mgr, tmp_path)
    auth = {_AUTH_HEADER_KEY: f"Bearer {mgr.web.token}"}
    calls = []

    def _fake(sites=None):
        calls.append(sites)
        return {"requested": list(sites or []), "note": ""}

    mgr.hr.request_refresh = _fake
    body = client.post("/api/hr/refresh", json={"site": "HHan"}, headers=auth).json()
    assert body["ok"] is True and body["requested"] == ["HHan"]
    assert calls == [["HHan"]], "带 site 时只受理该站"
    del mgr.hr  # SimpleNamespace: 模拟取数线程从未启动的实例
    r = client.post("/api/hr/refresh", json={}, headers=auth)
    assert r.status_code == 409 and "取数线程未启动" in r.json()["detail"]


def test_api_hr_confirm_empty(web_env, tmp_path, monkeypatch):
    """人工对账戳端点(§5.3): 缺 site / HR 未启用 / 站点未接入 -> 400; 成功 -> ok+site 且
    run_hr_confirm_empty 收到 [site]; 写入失败(站点锁占用) -> 409"""
    from auto_qb.webui.server.routes import hr as hr_routes

    mgr, client = web_env
    _hr_status_env(mgr, tmp_path)
    auth = {_AUTH_HEADER_KEY: f"Bearer {mgr.web.token}"}
    r = client.post("/api/hr/confirm-empty", json={}, headers=auth)
    assert r.status_code == 400 and "缺少 site" in r.json()["detail"]
    mgr.config.hr_check.enabled = False
    r = client.post("/api/hr/confirm-empty", json={"site": "HHan"}, headers=auth)
    assert r.status_code == 400 and "未启用" in r.json()["detail"]
    mgr.config.hr_check.enabled = True
    r = client.post("/api/hr/confirm-empty", json={"site": "Nope"}, headers=auth)
    assert r.status_code == 400 and "Nope" in r.json()["detail"] and "HHan" in r.json()["detail"]
    calls = []
    monkeypatch.setattr(hr_routes, "run_hr_confirm_empty", lambda config, sites: calls.append(sites) or 0)
    body = client.post("/api/hr/confirm-empty", json={"site": "HHan"}, headers=auth).json()
    assert body == {"ok": True, "site": "HHan"}
    assert calls == [["HHan"]]
    monkeypatch.setattr(hr_routes, "run_hr_confirm_empty", lambda config, sites: 1)
    r = client.post("/api/hr/confirm-empty", json={"site": "HHan"}, headers=auth)
    assert r.status_code == 409 and "写入失败" in r.json()["detail"]


def test_api_events_sse_stream_lifecycle(web_env, monkeypatch):
    """SSE 生成器整块: hello 帧 -> 广播后事件帧(先 touch) -> 无事件时 keepalive 心跳 ->
    消费端关闭 -> 生成器终结执行 finally 退订(subscriber_count 归零)。

    !不走 TestClient 流式读: starlette 1.6 TestClient 的 handle_request 用 portal.call 把
    整个 app 跑到完成为止, 无限 SSE 流永不完成 -> 挂死(实测 90s) —— 改为直调生产路由端点
    拿 StreamingResponse, anyio 驱动 body_iterator(与真实发送同源, 鉴权是全局依赖另行已测)。
    keepalive 间隔猴补 0.05s, 挂钟下界留 20ms 余量(pitfalls/testing/timing-tolerance.md)。
    终结退订是**跨线程终态**(生成器由 anyio 工作线程持有到唤醒消费端之后), 故末尾断言按
    有界等待判据 —— 缘由与实测数字写在断言处注释(同族 pitfalls/testing/timing-tolerance.md)。
    """
    import gc
    import time as _time

    import anyio

    from auto_qb.webui.server.context import WebContext
    from auto_qb.webui.server.routes import events as events_mod

    mgr, _client = web_env
    monkeypatch.setattr(events_mod, "SSE_KEEPALIVE_S", 0.05)
    touches = []
    monkeypatch.setattr(mgr.web, "touch", lambda: touches.append(1))
    route = next(r for r in events_mod.build_router(WebContext(mgr)).routes if r.path == "/api/events")
    resp = route.endpoint()
    assert resp.media_type == "text/event-stream"
    assert resp.headers["cache-control"] == "no-cache"
    assert resp.headers["x-accel-buffering"] == "no"  # 反代不缓冲, SSE 才能逐帧到

    async def _drive():
        frames = resp.body_iterator
        # hello 帧: 订阅即发, 不触发 touch(还没进事件循环)
        assert await frames.__anext__() == 'event: hello\ndata: {"ok": true}\n\n'
        assert touches == []
        # 事件帧: 广播 -> 帧名取 ev.type, payload 原样; touch 标记活跃
        assert mgr.web.notify("cmd_done", {"id": 9}) == 1
        assert await frames.__anext__() == 'event: cmd_done\ndata: {"id": 9}\n\n'
        assert len(touches) == 1
        # keepalive: 队列空 -> Empty 分支 -> 心跳注释帧(必须 < WEB_VIEW_TTL, 自锁防线)
        t0 = _time.monotonic()
        assert await frames.__anext__() == ": keepalive\n\n"
        assert _time.monotonic() - t0 >= 0.05 - SLEEP_LOWER_MARGIN_S
        assert len(touches) == 2
        # 心跳后循环继续(continue): 再广播一条, 事件帧照常送达
        assert mgr.web.notify("view_changed", {"ver": 2}) == 1
        assert await frames.__anext__() == 'event: view_changed\ndata: {"ver": 2}\n\n'
        assert len(touches) == 3
        await frames.aclose()  # 客户端断开: 消费端关闭

    anyio.run(_drive)
    # starlette 1.6 不显式 close 同步生成器 —— 断开后由生成器终结执行 finally 退订;
    # !但终结**不在 aclose 的那一刻**: 同步生成器跑在 anyio 工作线程里, 它的最后一个引用由该线程
    # 在 `call_soon_threadsafe` 之后才 `del`(item/func/args 元组), 而正是同一次调用唤醒消费端 ——
    # 消费端醒来时工作线程可能还没走到那几个 `del`。故这里用「有界等待」而不是单点采样:
    # 退订仍必须发生, 只是允许它有限时间内发生(实测: 16 核压满 2880 轮竞态率 ~2.1%(60 次),
    # 最长自愈 308ms —— 下面 5s 定时 ≈ 己观测最长值的 16 倍; CI 2026-10-16 windows job 的
    # 单点采样红 `1 == 0` 即此形态, 生产代码语义无误)。
    # 同族: pitfalls/testing/timing-tolerance.md(时序断言留余量) / poll-last-round-race.md。
    del resp
    gc.collect()
    deadline = _time.monotonic() + 5.0
    while mgr.web.subscriber_count() and _time.monotonic() < deadline:
        _time.sleep(0.005)  # 必须让出 GIL, 工作线程才能跑完它那几个 `del`
    if mgr.web.subscriber_count():
        gc.collect()  # 兜底: 生成器可能落在环里(异常回溯链), 交环回收器终结
    assert mgr.web.subscriber_count() == 0, "断流后必须退订, 防句柄堆叠"


def test_api_events_sse_generator_error_still_unsubscribes(web_env, monkeypatch):
    """生成器中途异常死亡(touch/序列化等任何异常)也必须走 finally 退订 —— fail-safe 语义"""
    import anyio

    from auto_qb.webui.server.context import WebContext
    from auto_qb.webui.server.routes import events as events_mod

    mgr, _client = web_env
    monkeypatch.setattr(events_mod, "SSE_KEEPALIVE_S", 0.05)
    route = next(r for r in events_mod.build_router(WebContext(mgr)).routes if r.path == "/api/events")
    resp = route.endpoint()

    async def _drive():
        frames = resp.body_iterator
        assert await frames.__anext__() == 'event: hello\ndata: {"ok": true}\n\n'
        monkeypatch.setattr(mgr.web, "touch", lambda: (_ for _ in ()).throw(RuntimeError("view boom")))
        mgr.web.notify("cmd_done", {"id": 1})
        with pytest.raises(RuntimeError, match="view boom"):
            await frames.__anext__()

    anyio.run(_drive)
    assert mgr.web.subscriber_count() == 0, "生成器异常死亡也要退订, 防句柄堆叠"


def test_frontend_hr_status_fields_match_backend():
    """前端 HR 状态块引用的字段必须在后端快照里存在 —— 打错一个字段名就是**整段静默空白**

    两套 UI 各扫一个入口(2026-09-25 起 HR 站点状态并入 Console Hub「HR 在线核实」分区页尾,
    经典设置页与其独立章节/卡片已移除): 这类错误后端全绿、pytest 也全绿, 只有真打开页面才
    看得出来(与 `_scan_page_class_wiring` 的挂件类名同一类故障), 故机检。
    """
    from auto_qb.hr.status import SiteStatus

    site_keys = set(SiteStatus(site="probe").to_dict().keys())
    hrs_keys = {
        "loaded", "loading", "error", "enabled", "note", "sites", "channel", "fetchEnabled", "workerRunning",
        "pollInterval", "confirming", "refreshing", "refreshNote"
    }
    # 锚点必须指向合并块自身: v-if 只在「HR 在线核实」分区模板块这一处出现, 重复出现说明块被复制
    # (2026-09-27 起块内含「站点接入」+「站点状态」两个块, 扫描窗放大到 8000 字符; 26-10-01 阶段2
    # 表 1 又带入嵌套 <template v-for> 明细表 —— 单找第一个 </template> 会切在明细表收口、丢掉块尾
    # 字段覆盖, 故改按模板嵌套深度找**锚点自己的配对收口**, 窗口只作半残兜底: 阶段3 放大到 16000,
    # 26-10-04-0312 S4 表 3 拉取历史全局段再涨(实测块 18.2k 字符)放大到 32000)
    anchor = "hub.view === 'hr_check'"
    for ui in _UI_ALL:
        html = _ui_aggregate(ui)
        idx = html.find(anchor)
        assert idx > 0, f"{ui} 缺少锚点 {anchor} —— 合并进「HR 在线核实」的状态块丢失"
        assert html.find(anchor, idx + 1) < 0, f"{ui} 锚点出现多次 —— 状态块被复制了?"
        open_i = html.rfind("<template", max(0, idx - 200), idx)
        assert open_i >= 0, f"{ui}: 锚点 {anchor} 不在 <template> 开标签内 —— 模板结构被改坏? 同步本守阵"
        depth = 0
        cut = -1
        for m in re.finditer(r"<template\b|</template>", html[open_i:open_i + 32000]):
            depth += 1 if m.group(0).startswith("<template") else -1
            if depth == 0:
                cut = open_i + m.start()
                break
        assert cut > 0, f"{ui}: 状态块没有闭合标签 —— 模板结构被改坏"
        block = html[idx:cut]
        used_site = set(re.findall(r"\bs\.([a-z_]+)\b(?!\()", block))
        assert used_site, f"{ui}: 没扫到任何字段 —— 锚点失效, 这个守阵现在是恒真的"
        missing = sorted(used_site - site_keys)
        assert not missing, f"{ui}: 模板引用了后端快照里没有的字段 {missing}(会整段空白)"
        used_hrs = set(re.findall(r"\bhrs\.([A-Za-z_]+)\b(?!\()", block))
        missing_hrs = sorted(used_hrs - hrs_keys)
        assert not missing_hrs, f"{ui}: 模板引用了 hrs 状态里没有的字段 {missing_hrs}"


def test_api_hr_status_disabled_returns_empty_state(web_env):
    """未启用 HR 时 /api/hr/status 回 enabled=false + 说明(前端据此显示空态, 而不是报错)"""
    mgr, client = web_env
    r = client.get("/api/hr/status", headers={_AUTH_HEADER_KEY: f"Bearer {mgr.web.token}"})
    assert r.status_code == 200
    body = r.json()
    assert body["enabled"] is False and body["sites"] == [] and body["channel"] == {}
    assert "未启用" in body["note"], "要说明为什么没有数据, 不能静默空"


def test_api_hr_status_reports_site_state(web_env, tmp_path):
    """启用后逐站点摊开现状: 新鲜度/覆盖证明/索引与回填进度/配额/熔断/「现在为什么不放行」

    与 `--hr-status` 共用 `hr.status` 一层 —— 这里断言的是那一层的字段真的透到了 HTTP。
    """
    mgr, client = web_env
    _hr_status_env(mgr, tmp_path)
    r = client.get("/api/hr/status", headers={_AUTH_HEADER_KEY: f"Bearer {mgr.web.token}"})
    assert r.status_code == 200
    body = r.json()
    assert body["enabled"] is True and body["fetch_enabled"] is True and body["worker_running"] is True
    assert [s["site"] for s in body["sites"]] == ["HHan"]

    site = body["sites"][0]
    assert site["listing"] == "list" and site["enabled"] is True
    assert site["index_total"] == 1 and site["index_active"] == 1
    assert site["pending_infohash"] == 0 and site["backfill_ratio"] == 1.0
    assert site["managed"] == 0 and site["keys"] == 2, "行名不粗配本地名 → 考察中命中 0; 身份键在终态档占 v1/v2 两个"
    assert all(l["status"] == "ok" for l in site["lanes"]), "三档波次状态全有效"
    # 表 2 波次表档位徽章人话(计划 26-10-01-2216 §6.2 mockup「A 考察中」形态): 曾因 LaneStatus
    # 缺字段渲染为空(幻键), 修后逐档钉值 + 钉「取自 LANE_TEXTS 单点」双断言
    from auto_qb.hr.model import FETCH_LANES
    from auto_qb.hr.status import LANE_TEXTS

    lane_texts = {l["lane"]: l["lane_text"] for l in site["lanes"]}
    assert lane_texts == {"A": "考察中", "B": "已达标", "C": "未达标"}, f"徽章人话逐档不对: {lane_texts}"
    assert lane_texts == {k: LANE_TEXTS[k] for k in FETCH_LANES}, "lane_text 必须取自 LANE_TEXTS 单点, 不另写第二份映射"
    assert "上次取波" in site["fresh_text"] and "复用窗至" in site["fresh_text"]
    assert site["next_wave_at"] > site["fetched_at"], "下次取波 = 上次取数 + 周期"
    assert "今天" in site["quota"]["text"] and site["quota"]["day_max"] > 0
    assert site["channel_text"] in ("正常", "未启用") and site["file_path"].endswith("HHan.json")


def test_api_hr_status_names_the_blocking_step(web_env, tmp_path):
    """覆盖证明不成立时, 状态里要直接说出「现在为什么不放行」(用户看到种子没放行时最想知道的一句)"""
    mgr, client = web_env
    _hr_status_env(mgr, tmp_path, complete=False)
    body = client.get("/api/hr/status", headers={_AUTH_HEADER_KEY: f"Bearer {mgr.web.token}"}).json()
    site = body["sites"][0]
    assert site["releases_enabled"] is False
    assert "blocking" in site, f"要说清卡在哪一步: {site}"
