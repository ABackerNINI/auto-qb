"""test_web_hr 测试计划: HR web 端点与搜索 / 文件系统端点

## 测试计划(每个测试函数一条)
- test_api_hr_site_entries_full_fields: 种子明细端点(计划 26-10-01-2216 §7 阶段1)200 全字段 —— 行键面 = §3 P0+P1 全集
- test_api_hr_site_entries_local_present: 明细行 local_present 本地库 join(计划 26-10-02-1936 §3.3 决策点③a) ——
  v1 命中/仅 v2 命中/大小写差异命中 -> True, 本地不存在 -> False(未做种)
- test_api_hr_site_entries_verified_two_states: verified 有/无两态同表(无记录→未核实; 有记录→verified_ts+source 原值+人话)
- test_api_hr_site_entries_empty_site: 站点已接入但没有 HR 行 -> 200 + 空数组(前端空态)
- test_api_hr_site_entries_guards: HR 未启用 400 / 站点未接入 404(与 confirm-empty 同款话术)
- test_api_hr_site_entries_409_worker_absent: hr 门面在但取数服务缺席(service=None) -> 409 不假装有数据
- test_api_hr_history_rows_from_real_wave: 拉取历史端点(计划 26-10-04-0312 §3.4)200 —— 行键面 = §3.4 全集,
  真实波次(S2 记录器)落表; 完成徽章/触发人话/档位 lane_text/写者短标识全由后端算好
- test_api_hr_history_site_filter: site 过滤只回该站; 未接入 404 点名已接入清单(与 entries 同款话术)
- test_api_hr_history_guards: HR 未启用 400 / 取数服务缺席 409(与 entries 同款校验)
- test_api_hr_history_limit_clamped: limit 截最新 N 条; 0 钳到 1(不回全量也不回空页)
- test_api_hr_history_read_error_reported_not_raised: 站点文件读坏不抛 —— read_errors{site: err} 带出, rows 剔掉坏站
- test_api_state_excludes_hr_entry_details: 体积守卫 —— 种子明细键不得进 /api/state 轮询载荷(计划 §8)
- test_hr_user_visible_texts_no_graduation_wording: 否定守阵 —— 用户可见文案来源(hr status/resolve/events 字符串常量)「毕业」零残留
  (注释保留域术语, 决策点②); 无事实分支与带事实分支同文「在线·已达标」(testhr_view_fields_three_state 内钉)
- test_api_hr_refresh_single_site_and_no_runtime: refresh 指定单站受理 + hr 门面缺席回 409
- test_api_hr_confirm_empty: 人工对账戳端点(缺 site/未启用/未接入 400, 成功 ok, 写入失败 409)
- test_api_events_sse_stream_lifecycle: SSE 生成器整块(hello 帧/事件帧/keepalive 心跳/终结退订;
  TestClient 会挂死无限流, 直调端点驱动 body_iterator)
- test_api_events_sse_generator_error_still_unsubscribes: 生成器异常死亡也走 finally 退订
- test_views_published_atomically_when_rebuilt_concurrently: 并发重建(主循环线程 vs Web 线程)时四份视图与版本号必须**同一轮**发布, 不得出现"半新半旧"
- test_flush_views_marks_dirty_on_hr_revision_change: HR 判定新鲜度置脏(plan 26-10-03-0436 Step 2) —— hr.revision 变化后 flush_views 置脏, 重建后基线前移、再次 flush 不再置脏(无循环置脏)
- test_flush_views_hr_facade_missing_null_defense: hr 门面缺失(None)时判空防御 —— 重建记基线与 flush 比对都跳过, 不炸不置脏
- test_build_search_index_files: 搜索索引构建(hash -> name+files), 单条文件拉取失败跳过该种子
- test_build_search_index_incremental_and_evict: 增量维护(不重拉已建条目/补拉新增/淘汰已删)
- test_build_search_index_budget_resumes: 限流分批构建, 未拉完保持脏, 续建至完成
- test_build_search_index_aborts_when_disconnected: qB 断连时中止构建且不写空索引
- test_search_torrents_name_match: 种子名匹配(即时/大小写不敏感)
- test_search_torrents_separator_normalized: 分隔符归一匹配 —— 空格查询词命中点/下划线/连字符分隔的名与文件(回归 "cat and" 搜不到 The.Cat.and… 名)
- test_parse_query_tokens: 查询解析词法 —— 正/负词/短语 + 宽容边界(孤立-/未闭合引号/纯标点/--dv/web-dl)
- test_search_torrents_cross_row_and: 正词逐词跨行 AND(拍板 26-09-27 二次定案, 推翻 26-09-26 文件行隔离)—— 每个正词命中任一候选行(全称行/文件行)即可: 「minions mteam」名字×标签、「delta 03」名字×集文件跨行命中; 负词种子级不变
- test_search_torrents_negative_term: 负词种子级(26-09-27 定案)—— 任一候选行含负词 ⇒ 该种子整体排除: 单种子内季包文件统一计算(任一文件带负词整包排除), 多种子集合逐个算
- test_search_torrents_negative_torrent_veto: 负词种子级回归 —— 名字/保存路径/站点行含负词 ⇒ 整种子排除, 优先于一切正词命中(「cat and -11」+「-mteam」两轮报障回归)
- test_search_torrents_facet_rows: 候选行覆盖全部文本面(站点/分类/路径/标签行即时匹配, by 定位行类别) + facet 行负词整种子排除 —— 三页同源(26-09-26 单点化; 负词种子级 26-09-27 定案)
- test_search_torrents_phrase: 短语 "…" 整段归一为连续子串, 词序敏感(terms-AND 命中而短语不命中的区分用例)
- test_search_torrents_regression_envnv10: 回归(26-09-26 报障)——「恶女 10」命中单文件发布物, -ubweb 可排除
- test_search_torrents_negative_only_empty: 仅负词/空查询返回空 + negative_only 标记, 不投递索引构建
- test_search_torrents_file_match: 文件列表匹配(依赖已建索引)
- test_search_torrents_building_triggers: 索引脏时 building=True 并投递构建命令
- test_api_search_endpoint: GET /api/search 转发与鉴权(含空查询)
- test_api_paths_endpoint: GET /api/paths 已知目录聚合(组 save_path + 现有种子 save_path 归一去重排序; 空路径跳过; 无副作用; 鉴权)
- test_api_open_path_endpoint: POST /api/open-path 打开目标文件夹(FX-14 + R10-10) —— 目录/单文件(select=True 定位选中)/回退 save_path(缺失或下载中未落盘)/组键首元、未知目标 404、kind 非法 400、客户端传 path 被忽略、无副作用、鉴权
- test_api_fs_dirs_endpoint: GET /api/fs/dirs 目录浏览(R10-11) —— 首屏允许根/只列目录(排除文件与越界符号链接)/上溯到根为止/.. 穿越与白名单外 403/不存在 404/无白名单空返回/鉴权/无副作用
- test_api_fs_dirs_case_sibling_is_outside_whitelist: **仅 Linux** —— 大小写兄弟目录(/x/Media 与 /x/media)必须判为越界, 白名单归一不得做 NTFS 式折叠(折叠 => 越界放行, fail-open)
- test_api_fs_mkdir_endpoint: POST /api/fs/mkdir 新建目录(R10-11) —— 正常创建/重名目录幂等/重名文件 409/名字含分隔符或点为 400/白名单外 403/父目录不存在 404/鉴权/不投命令
- test_fs_endpoints_route_fs_calls_through_long_path_prefix: fs 三端点的文件系统调用必须过 add_long_path_prefix_for_win(Windows 长路径 >MAX_PATH 否则 isdir 给假/scandir 抛错 ⇒ 误报 404)
- test_fs_endpoints_unmapped_root_semantic_404: Mapped 模式下白名单内但未命中 fs.path_map 的路径 -> fs 三端点语义化 404「不可判定」而非裸 500(BUG 回归: UNDETERMINED 禁止布尔化, 路由五处两态消费收进 _determinable 单点)
- test_fs_path_helpers_strip_long_path_prefix_before_compare: _bare/_fs_real 比较前剥长路径前缀(否则同一条路径的两种写法被判越界, 子目录全被过滤)
- testhr_view_fields_three_state: 详情字段透出站点侧三态与依据(接入站点才有值, 未接入全空)
- testhr_view_fields_excluded: HR 排除态视图(hr_excluded=True, 触发/达标 False, 站点侧全空, 桥不被打扰)
- test_api_hr_status_disabled_returns_empty_state: 未启用 HR 时 /api/hr/status 回 enabled=false + 说明(前端空态, 不报错)
- test_api_hr_status_reports_site_state: 启用后逐站点摊开现状 —— 新鲜度/覆盖证明/索引与回填进度/配额/熔断/
  「现在为什么不放行」(与 --hr-status 同一 `hr.status` 口径) + 波次明细 lane_text 徽章人话逐档正确(LANE_TEXTS 单点)
- test_api_hr_status_names_the_blocking_step: 覆盖证明不成立时要说清卡在哪一步(用户看到种子没放行时最想知道的一句)
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

from auto_qb.infra import file_access
from auto_qb.infra.utils import encode_group_key

from webui_helpers import _UI_ALL, _ui_aggregate, _hr_status_env

# ---------- 立即拉取(计划 26-09-30-0240): POST /api/hr/refresh ----------


def test_api_hr_refresh_accepts_and_returns_requested(web_env, tmp_path):
    """成功受理: 调 manager.hr.request_refresh(与插件端点同一实现)并回受理清单"""
    mgr, client = web_env
    _hr_status_env(mgr, tmp_path)
    calls = []

    def _fake_request_refresh(sites=None):
        calls.append(sites)
        return {"requested": ["HHan"], "note": "已受理, 取数由取数线程执行"}

    mgr.hr.request_refresh = _fake_request_refresh
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    body = client.post("/api/hr/refresh", json={}, headers=auth).json()
    assert body["ok"] is True and body["requested"] == ["HHan"]
    assert calls == [None], "缺省 = 全部启用站点(不逐站点名)"


def test_api_hr_refresh_requires_enabled_hr(web_env, tmp_path):
    """HR 未启用 -> 400; 未接入的站点 -> 400(不受理无档案站点)"""
    mgr, client = web_env
    _hr_status_env(mgr, tmp_path)
    mgr.hr.request_refresh = lambda sites=None: {"requested": ["HHan"], "note": ""}
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
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
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    r = client.post("/api/hr/refresh", json={}, headers=auth)
    assert r.status_code == 409 and "取数线程未启动" in r.json()["detail"]


# ---------- 种子明细(计划 26-10-01-2216 §7 阶段1): GET /api/hr/sites/{site}/entries ----------


def test_api_hr_site_entries_full_fields(web_env, tmp_path):
    """200 全字段: 行键面 = 计划 §3 P0+P1 全集(前端只消费后端算好字段, 不重算)"""
    mgr, client = web_env
    _hr_status_env(mgr, tmp_path)
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    r = client.get("/api/hr/sites/HHan/entries", headers=auth)
    assert r.status_code == 200
    body = r.json()
    assert body["site"] == "HHan" and body["read_error"] == "" and body["now"] > 0
    assert len(body["entries"]) == 1
    row = body["entries"][0]
    assert set(row) == {
        "tid",
        "dl_id",
        "name",
        "lane",
        "lane_text",
        "uploaded_bytes",
        "downloaded_bytes",
        "ratio",
        "need_seed_seconds",
        "need_seed_text",
        "infohash_v1",
        "infohash_v2",
        "verified_ts",
        "verified_source",
        "verified_source_text",
        "local_present",
        "done_iso",
        "active",
        "missing_streak",
        "first_seen",
        "last_seen",
    }
    assert row["tid"] == 101 and row["name"]
    assert row["infohash_v1"] and row["infohash_v2"], "取过 .torrent 的行 v1/v2 都已回填"
    assert row["local_present"] is False, "夹具本地库为空 -> 全部行是未做种(local_present join 响应层追加)"
    assert row["need_seed_seconds"] is not None and row["need_seed_text"] not in ("", None)
    assert row["lane"] and row["lane_text"], "档位原值 + 人话都要给"
    assert row["active"] is True and "done_iso" in row
    assert row["first_seen"] >= 0.0 and row["last_seen"] >= 0.0, "first_seen/last_seen 原样透传(写入行为属取数管道, 不在此钉)"


def test_api_hr_site_entries_local_present(web_env, tmp_path):
    """local_present 本地库 join(计划 26-10-02-1936 §3.3, 决策点③a): 明细端点每行带只读标记

    真实 join 用例(端点级): v1 精确命中 / 仅 v2 命中 / 大小写差异命中 -> True;
    本地不存在 -> False(未做种, 含本地从未下载的清单行)。join 键口径单点在
    routes.hr.mark_local_present(纯函数四态由 test_hr_status 钉)。
    """
    mgr, client = web_env
    _hr_status_env(mgr, tmp_path)
    auth = {"Authorization": f"Bearer {mgr.web.token}"}

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
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
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
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    r = client.get("/api/hr/sites/HHan/entries", headers=auth)
    assert r.status_code == 200
    assert r.json()["entries"] == []


def test_api_hr_site_entries_guards(web_env, tmp_path):
    """HR 未启用 -> 400; 站点未接入 -> 404 并点名已接入清单(与 confirm-empty 同款话术)"""
    mgr, client = web_env
    _hr_status_env(mgr, tmp_path)
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
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
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    r = client.get("/api/hr/sites/HHan/entries", headers=auth)
    assert r.status_code == 409 and "取数线程未启动" in r.json()["detail"]


# ---------- 拉取历史(计划 26-10-04-0312 §3.4): GET /api/hr/history ----------


def test_api_hr_history_rows_from_real_wave(web_env, tmp_path):
    """200: 真实波次(S2 记录器落的事件)进历史表 —— 行键面 = §3.4 全集, 人话徽章后端算好"""
    mgr, client = web_env
    _hr_status_env(mgr, tmp_path)
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    r = client.get("/api/hr/history", headers=auth)
    assert r.status_code == 200
    body = r.json()
    assert body["enabled"] is True and body["read_errors"] == {} and body["now"] > 0
    assert body["rows"], "夹具跑过一轮真实波, 历史表不能是空的"
    row = body["rows"][0]
    assert set(row) == {
        "ts",
        "ts_text",
        "site",
        "kind",
        "kind_text",
        "trigger",
        "trigger_text",
        "action",
        "result_text",
        "result_tone",
        "reason",
        "reason_kind",
        "pages",
        "rows",
        "torrents_ok",
        "torrents_fail",
        "verified",
        "elapsed_s",
        "elapsed_text",
        "lanes",
        "notes",
        "by",
    }
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
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
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
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
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
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
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
    """站点文件读坏不抛: read_errors{site: err} 原样带出, rows 剔掉坏站(表① 同款只读口径)"""
    mgr, client = web_env
    svc = _hr_status_env(mgr, tmp_path)
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    svc.store("HHan").path.write_text("{not-json", encoding="utf-8")
    r = client.get("/api/hr/history", headers=auth)
    assert r.status_code == 200
    body = r.json()
    assert body["rows"] == [], "坏站的数据不进行集(历史表宁缺勿错)"
    assert "HHan" in body["read_errors"] and body["read_errors"]["HHan"], "坏文件本身就是要人看的信息"


def test_api_state_excludes_hr_entry_details(web_env):
    """体积守卫: 种子明细键不得进 /api/state 轮询载荷(计划 §8) —— 明细只随表①按站点按需拉"""
    mgr, client = web_env
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    text = json.dumps(client.get("/api/state", headers=auth).json(), ensure_ascii=False)
    for key in ("need_seed_text", "verified_source_text", "lane_text", "missing_streak", "local_present"):
        assert f'"{key}"' not in text, f"/api/state 轮询载荷混入了明细键 {key}"


def test_hr_user_visible_texts_no_graduation_wording():
    """否定守阵(计划 26-10-02-1936 §3.5): 用户可见文案来源「毕业」零残留

    扫 hr/status.py(SOURCE_TEXTS 等)· hr/resolve.py(放行依据文案表 / safety_display 人话)·
    hr/events.py(告警行)的**字符串常量**(AST 层取, 注释天然不在其列 —— 注释按决策点②
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
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
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
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
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
        assert _time.monotonic() - t0 >= 0.05 - 0.02
        assert len(touches) == 2
        # 心跳后循环继续(continue): 再广播一条, 事件帧照常送达
        assert mgr.web.notify("view_changed", {"ver": 2}) == 1
        assert await frames.__anext__() == 'event: view_changed\ndata: {"ver": 2}\n\n'
        assert len(touches) == 3
        await frames.aclose()  # 客户端断开: 消费端关闭

    anyio.run(_drive)
    # starlette 1.6 不显式 close 同步生成器 —— 断开后由生成器终结执行 finally 退订;
    # aclose 后引用链已断, collect 使终结确定性发生(生产同语义: 流对象失去引用即退订)
    del resp
    gc.collect()
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
    # 表① 又带入嵌套 <template v-for> 明细表 —— 单找第一个 </template> 会切在明细表收口、丢掉块尾
    # 字段覆盖, 故改按模板嵌套深度找**锚点自己的配对收口**, 窗口只作半残兜底: 阶段3 放大到 16000,
    # 26-10-04-0312 S4 表③ 拉取历史全局段再涨(实测块 18.2k 字符)放大到 32000)
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


def test_build_group_view_hr_counts(tmp_path):
    """组级 H&R 计数: 分母 = 已触发 HR 的成员数, 分子 = 其中未达标的成员数(前端 H&R 栏)"""
    from helpers import FakeClient, FakeTorrent, FakeTracker, _hr_rule, make_manager, seed_store

    hr = _hr_rule(required_share_ratio=2.0)
    conf = FakeTracker("HHan", hr=hr)
    mgr = make_manager(str(tmp_path / "state.json"))
    mgr.client = FakeClient()

    def tor(h, seeding_time, ratio):
        return FakeTorrent(
            hash=h,
            name="Show",
            state="stalledUP",
            size=512**2,
            total_size=512**2,
            downloaded=512**2,
            amount_left=0,
            progress=1.0,
            seeding_time=seeding_time,
            ratio=ratio,
            save_path=r"R:/s",
            tracker_conf=conf,
        )

    seed_store(
        mgr,
        [
            tor("HA", 100, 0.5),  # 已触发但未达标(时长与分享率都不够)
            tor("HB", 100, 3.0),  # 已触发且分享率达标
            tor("HC", 4 * 86400, 0.1),  # 已触发且时长达标
        ]
    )
    key = ("R:/s", ("a.mkv", ))
    mgr.store.groups[key] = ["HA", "HB", "HC"]
    for h in ("HA", "HB", "HC"):
        mgr.store.member_to_key[h] = key

    g = mgr._build_group_view()[0]
    assert g["hr_triggered"] == 3
    assert g["hr_pending"] == 1


def test_build_group_view_added_on_is_latest_member(tmp_path):
    """组级 added_on = 组内**最近添加**成员的时间(前端默认按此降序排序)

    用 max 而非 min: "刚补进来的那个辅种"才是用户最关心的新条目。
    """
    from helpers import FakeClient, FakeTorrent, make_manager, seed_store, seed_store

    mgr = make_manager(str(tmp_path / "state.json"))
    mgr.client = FakeClient()
    t1 = FakeTorrent(hash="HA", name="Show", added_on=1000, save_path=r"R:/s")
    t2 = FakeTorrent(hash="HB", name="Show", added_on=3000, save_path=r"R:/s")
    t3 = FakeTorrent(hash="HC", name="Other", added_on=2000, save_path=r"R:/o")
    seed_store(mgr, [t1, t2, t3])
    key = ("R:/s", ("a.mkv", "b.mkv"))
    mgr.store.groups[key] = ["HA", "HB"]
    mgr.store.member_to_key["HA"] = key
    mgr.store.member_to_key["HB"] = key
    key2 = ("R:/o", ("c.mkv", ))
    mgr.store.groups[key2] = ["HC"]
    mgr.store.member_to_key["HC"] = key2

    groups = {g["name"]: g for g in mgr._build_group_view()}
    assert groups["Show"]["added_on"] == 3000  # max(1000, 3000)
    assert groups["Other"]["added_on"] == 2000
    # 成员级也透出 added_on(排序/展示共用的原始值)
    assert sorted(m["added_on"] for m in groups["Show"]["members"]) == [1000, 3000]


def test_views_published_atomically_when_rebuilt_concurrently(tmp_path):
    """并发重建: 四份视图与版本号必须**同一轮**发布(主循环线程 vs Web 线程)

    web.py 的同步 `def` 处理器跑在 FastAPI 线程池里, 会与主循环同时走 `rebuild_views`。
    无锁时后者的"逐条赋值 + 版本号自增"会被前者插到中间 ⇒ 1.`_group_view_ver += 1` 是
    读-改-写, 丢失更新; 2.Web 线程可能拿到"groups 来自本轮、flat 来自上一轮"的错位组合,
    而版本号只有一个 ⇒ 前端按 rid 判定 updated=true 却把错位数据整表换上去。

    检测手法(刻意做成**确定性**, 不依赖线程调度): 让重建卡在 builder 里不放行, 再把脏标记
    置为 False —— 于是读取路径不需要重建, 它能否返回**只取决于有没有锁**, 与交错时序无关。
    (更直觉的"比对四份视图的 build 号"写法是 flaky 的: 无锁时若两个线程各自完整发布一轮,
    最后发布者胜出, 四份仍是自洽的, 用例会假绿。)
    """
    import threading as _threading

    from helpers import FakeClient, make_manager

    mgr = make_manager(str(tmp_path / "state.json"))
    mgr.client = FakeClient()

    inside = _threading.Event()  # 重建已进入 builder
    release = _threading.Event()  # 放行重建
    errors = []

    def _build_group():
        inside.set()
        release.wait(5)  # 卡在临界区里, 模拟"重建尚未发布"
        return []

    mgr._build_group_view = _build_group

    def _main_loop_path():
        try:
            mgr.web.rebuild_views()  # 主循环 _tick 走的重建路径(持锁)
        except Exception as e:  # 线程内异常不能静默吞掉
            errors.append(e)

    t = _threading.Thread(target=_main_loop_path)
    t.start()
    assert inside.wait(5), "前置: 重建线程应已进入 builder"

    # 关键: 置脏为 False, 让读取路径**不需要重建** —— 于是它是否返回只取决于"有没有锁",
    # 不再受线程调度影响(若改成依赖交错时序, 用例会变 flaky)。
    mgr.web.group_view_dirty = False

    read_done = _threading.Event()

    def _web_path():
        try:
            mgr.web.ensure_view()  # Web 线程路径
        finally:
            read_done.set()

    r = _threading.Thread(target=_web_path)
    r.start()
    assert not read_done.wait(0.5), ("重建进行中读取不应立即返回 —— 锁未生效时, "
                                     "Web 线程会读到半新半旧的四视图组合")
    release.set()
    t.join()
    r.join()
    assert not errors, f"重建线程异常: {errors}"


def test_flush_views_marks_dirty_on_hr_revision_change(tmp_path):
    """HR 判定新鲜度置脏(plan 26-10-03-0436 Step 2): hr.revision 变化 -> flush_views 置脏

    HR 判定结果不是 store 快照字段, store.view_changed 覆盖不到它(与「错误原因」预取
    同一判别法): 取数线程发布新判定(revision 自增)必须显式翻译成一次置脏, 否则界面
    挂在旧判定上直到别的原因碰巧重建。基线随重建前移 => 只置一拍, 无循环置脏。
    """
    from auto_qb.hr.resolve import HrSiteView, HrViewSet

    from helpers import FakeTorrent, make_manager, seed_store

    mgr = make_manager(str(tmp_path / "state.json"))
    seed_store(mgr, [FakeTorrent(hash="HA", name="A")])
    mgr.store.consume_view_changed()  # 排掉 store 构造期置脏(TorrentStore 初始 view_changed=True), 只考察 HR 通道
    mgr.web.group_view_dirty = False
    mgr.web.rebuild_views()  # 重建完成: 基线记下当刻 revision(0)
    assert mgr.web.group_view_dirty is False
    assert mgr.web._hr_rev_at_build == 0

    # 直接推 publisher 模拟取数线程发布新判定(内容指纹变化 => revision 自增)
    pushed = mgr.hr.publisher.publish(HrViewSet(views={"HHan": HrSiteView(site="HHan")}, generated_at=1.0))
    assert pushed is True, "前置: 首个站点视图必须抬 revision"

    mgr.web.flush_views()
    assert mgr.web.group_view_dirty is True, "revision 变化必须置脏"

    # 重建后基线前移, 再次 flush 不再置脏(无循环置脏)
    mgr.web.rebuild_views()
    assert mgr.web.group_view_dirty is False
    assert mgr.web._hr_rev_at_build == mgr.hr.publisher.revision, "基线必须随重建前移"
    mgr.web.flush_views()
    assert mgr.web.group_view_dirty is False, "基线已前移, 不得循环置脏"


def test_flush_views_hr_facade_missing_null_defense(tmp_path):
    """hr 门面缺失(None)时判空防御: 重建记基线与 flush 比对都跳过, 不炸不置脏"""
    from helpers import make_manager

    mgr = make_manager(str(tmp_path / "state.json"))
    mgr.hr = None
    mgr.store.consume_view_changed()  # 排掉 store 构造期置脏, 只考察 HR 通道
    mgr.web.group_view_dirty = False
    mgr.web.rebuild_views()
    assert mgr.web._hr_rev_at_build is None, "无 HR 运行时: 基线记 None"
    mgr.web.flush_views()
    assert mgr.web.group_view_dirty is False, "无 HR 运行时: 新鲜度比对跳过, 不得置脏"


def test_build_search_index_files():
    """build_search_index: 主循环构建索引(hash -> name+files), 单条文件拉取失败跳过该种子"""
    from helpers import FakeClient, FakeTorrent, make_manager, seed_store, seed_store

    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        mgr.client = client
        from helpers import _fake_file
        client.files_map["HA"] = [_fake_file("movie.mkv", 0), _fake_file("sub.srt", 0)]
        client.files_map["HB"] = [_fake_file("anime.mkv", 0)]
        t1 = FakeTorrent(hash="HA", name="Alpha", tracker_conf=None)
        t2 = FakeTorrent(hash="HB", name="Beta", tracker_conf=None)
        seed_store(mgr, [t1, t2])

        # 让 HB 的文件拉取失败: files() 抛异常 -> 该种子 files 为空但不阻塞
        def boom(h):
            if h == "HB":
                raise RuntimeError("fail")
            return [_fake_file("movie.mkv", 0), _fake_file("sub.srt", 0)]

        client.torrents_files = boom

        mgr.build_search_index()
        assert mgr.web.search_index_dirty is False
        idx = mgr.web.search_index
        assert idx["HA"]["name"] == "Alpha"
        assert "movie.mkv" in idx["HA"]["files"]
        assert idx["HB"]["files"] == [], "文件拉取失败的种子 files 应为空"
        assert set(idx.keys()) == {"HA", "HB"}


def test_build_search_index_incremental_and_evict():
    """build_search_index 增量维护: 已建条目只刷新名称(不重拉文件), 新种子补拉, 已消失种子淘汰"""
    from helpers import FakeClient, FakeTorrent, _fake_file, make_manager, seed_store

    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        mgr.client = client
        client.files_map["HA"] = [_fake_file("movie.mkv", 0)]
        ha = FakeTorrent(hash="HA", name="Alpha")
        seed_store(mgr, [ha])
        mgr.build_search_index()
        first_calls = client.files_calls
        assert first_calls == 1

        # 种子集未变: 不重复拉文件列表, 仅刷新名称, 且整体替换引用(原子交换契约)
        idx_before = mgr.web.search_index
        ha.name = "Alpha.Renamed"
        mgr.build_search_index()
        assert client.files_calls == first_calls, "已建条目不重复拉取文件列表"
        assert mgr.web.search_index["HA"]["name"] == "Alpha.Renamed", "名称应刷新"
        assert mgr.web.search_index is not idx_before, "索引应整体替换引用(Web 线程并发只读安全), 不就地增删"

        # HA 消失 + HB 新增: 只补拉新种子, 已删种子淘汰
        client.files_map["HB"] = [_fake_file("anime.mkv", 0)]
        seed_store(mgr, [FakeTorrent(hash="HB", name="Beta")])
        mgr.web.search_index_dirty = True
        mgr.build_search_index()
        assert set(mgr.web.search_index.keys()) == {"HB"}, "已消失种子应被淘汰"
        assert client.files_calls == first_calls + 1, "只补拉新增种子的文件列表"
        assert mgr.web.search_index_dirty is False


def test_build_search_index_budget_resumes(monkeypatch):
    """build_search_index 限流: 单次最多拉预算条, 未拉完保持脏, 下次调用续建至完成"""
    from auto_qb.webui import views as web_view
    from helpers import FakeClient, FakeTorrent, _fake_file, make_manager, seed_store

    monkeypatch.setattr(web_view, "SEARCH_INDEX_BUILD_BUDGET", 1)
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        mgr.client = client
        client.files_map["HA"] = [_fake_file("a.mkv", 0)]
        client.files_map["HB"] = [_fake_file("b.mkv", 0)]
        seed_store(mgr, [FakeTorrent(hash="HA", name="Alpha"), FakeTorrent(hash="HB", name="Beta")])

        mgr.build_search_index()
        assert mgr.web.search_index_dirty is True, "预算用尽应保持脏(待续建)"
        assert set(mgr.web.search_index.keys()) == {"HA"}, "单次只拉预算条数的文件列表"

        mgr.build_search_index()
        assert mgr.web.search_index_dirty is False, "续建后应不再脏"
        assert set(mgr.web.search_index.keys()) == {"HA", "HB"}


def test_build_search_index_aborts_when_disconnected():
    """build_search_index: qB 断开(client None)时中止并保持脏——不把空文件列表当成"已建完"""
    from helpers import FakeClient, FakeTorrent, _fake_file, make_manager, seed_store

    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        mgr.client = client
        client.files_map["HA"] = [_fake_file("movie.mkv", 0)]
        seed_store(mgr, [FakeTorrent(hash="HA", name="Alpha")])

        mgr.client = None  # 模拟 qB 断连(setter 同步解绑 store/api)
        mgr.build_search_index()
        assert mgr.web.search_index_dirty is True, "断连时应保持脏, 待连接恢复后重建"
        assert mgr.web.search_index is None, "断连时不得写入空文件索引"

        mgr.client = client  # 连接恢复
        mgr.build_search_index()
        assert mgr.web.search_index_dirty is False
        assert mgr.web.search_index["HA"]["files"] == ["movie.mkv"]


def test_search_torrents_name_match():
    """search_torrents: 种子名匹配(即时, 无需文件索引), 大小写不敏感"""
    from helpers import FakeClient, FakeTorrent, make_manager, seed_store, seed_store

    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        mgr.client = client
        t1 = FakeTorrent(hash="HA", name="My.Movie.2024", state="stalledUP")
        t2 = FakeTorrent(hash="HB", name="Anime.Series.S01", state="downloading")
        seed_store(mgr, [t1, t2])

        r = mgr.search_torrents("my.movie")
        names = [x["hash"] for x in r["results"]]
        assert names == ["HA"], f"名称命中(小写): {r}"
        assert all(x["by"] == "name" for x in r["results"])


def test_search_torrents_separator_normalized():
    """search_torrents: 分隔符归一匹配 —— 空格查询词命中点/下划线/连字符分隔的种子名与文件名

    回归(26-09-25): "The.Cat.and.the.Dragon.S01.1080p.friDay.WEB-DL.AAC2.0.H.264-MWeb"
    搜 "cat and" 不命中 —— 旧实现裸子串匹配, 查询词里的空格对不上名里的点号。
    """
    from helpers import FakeClient, FakeTorrent, make_manager, seed_store, seed_store, _fake_file

    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        mgr.client = client
        t1 = FakeTorrent(
            hash="HA", name="The.Cat.and.the.Dragon.S01.1080p.friDay.WEB-DL.AAC2.0.H.264-MWeb", state="stalledUP"
        )
        t2 = FakeTorrent(hash="HB", name="Other.Show.S02", state="stalledUP")
        client.files_map["HA"] = [_fake_file("The.Cat.and.the.Dragon.S01E01.1080p.WEB-DL.mkv", 0)]
        client.files_map["HB"] = [_fake_file("the_cat_and_dragon_e02.mkv", 0)]
        seed_store(mgr, [t1, t2])
        mgr.build_search_index()

        r = mgr.search_torrents("cat and")
        # HA 名字命中(回归主案例), HB 的下划线文件名归一后也含 "cat and"(file 路径顺带覆盖)
        assert [x["hash"] for x in r["results"]] == ["HA", "HB"], f"空格查询词应命中点号分隔名: {r}"
        assert [x["by"] for x in r["results"]] == ["name", "file"]
        assert [x["hash"] for x in mgr.search_torrents("web dl")["results"]] == ["HA"], "连字符分隔应命中"
        # 对称: 点号查询词同样归一, 仍命中; 纯分隔符不命中(解析即丢弃, 等价空查询)
        assert [x["hash"] for x in mgr.search_torrents("cat.and")["results"]] == ["HA", "HB"]
        # 同行同现: 词序无关 —— 旧口径 "dragon cat" 因连续子串序敏感不命中;
        # HA 名行与 HB 的下划线文件行均同含两词, 两路各按行命中
        assert [x["hash"] for x in mgr.search_torrents("dragon cat")["results"]] == ["HA", "HB"]
        assert mgr.search_torrents("...")["results"] == []

        # 文件命中: 下划线分隔的文件名按同一口径(HA 名与文件均不含该子串, 排除 seen 去重干扰)
        r = mgr.search_torrents("and dragon e02")
        assert [x["hash"] for x in r["results"]] == ["HB"], f"下划线文件名应命中: {r}"
        assert r["results"][0]["by"] == "file"


def test_parse_query_tokens():
    """_parse_query: 词法 —— 正/负词、短语、宽容边界(孤立 -/未闭合引号/纯标点/--dv/web-dl/词中引号)"""
    from auto_qb.webui.views import _parse_query

    # 基本分词 + 负词(词首 - 后随非空白); 归一小写
    assert _parse_query("恶女 10 -DV") == (["恶女", "10"], ["dv"])
    # 短语整段归一为连续子串(保留空格); 排除短语
    assert _parse_query('"s01e10" 恶女 -"H264 AAC"') == (["s01e10", "恶女"], ["h264 aac"])
    # 宽容: 孤立 - 忽略 / 未闭合引号收至行尾 / 纯标点 token 丢弃 / --dv 等价 -dv / web-dl 是正词
    assert _parse_query("-") == ([], [])
    assert _parse_query('foo "bar') == (["foo", "bar"], [])
    assert _parse_query("...") == ([], [])
    assert _parse_query("--dv") == ([], ["dv"])
    assert _parse_query("WEB-DL") == (["web dl"], [])
    # 词中引号无特殊含义(随归一折叠); 空查询
    assert _parse_query('foo"bar baz"') == (["foo bar", "baz"], [])
    assert _parse_query("") == ([], [])


def test_search_torrents_cross_row_and():
    """search_torrents 正词逐词跨行 AND(拍板 26-09-27 二次定案): 每个正词命中任一候选行即可, 行可不同

    26-09-26 曾拍板「多词须同行, 文件行不参与跨行」(防季包吸词); 26-09-27 用户实测推翻 ——
    「种子名 Gamma.Delta + 集文件 Gamma.E01-E03」搜「delta 03」须命中(标题在名字行、集号只在
    集文件行), 召回优先, 吸词代价(附加词可被包内任一文件名吸收)知情接受。负词种子级否决不变
    (见 negative_term / negative_torrent_veto); 全称行全覆盖的命中排前, 需文件行补词的以 file
    兜底排后。
    """
    from helpers import FakeClient, FakeTorrent, make_manager, seed_store, seed_store, _fake_file

    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        mgr.client = client
        t1 = FakeTorrent(hash="HA", name="Alpha.Beta.S01", state="stalledUP", tags="MTeam")
        t2 = FakeTorrent(hash="HB", name="Gamma", state="stalledUP")
        client.files_map["HB"] = [_fake_file("delta.mkv", 0), _fake_file("Gamma.E03.mkv", 1)]
        # 26-09-27 报障原型: 包名 Gamma.Delta 在名字行, 集号 03 只在集文件行
        t3 = FakeTorrent(hash="HC", name="Gamma.Delta.S01", state="stalledUP")
        client.files_map["HC"] = [
            _fake_file("Gamma.E01.mkv", 0),
            _fake_file("Gamma.E02.mkv", 1),
            _fake_file("Gamma.E03.mkv", 2)
        ]
        seed_store(mgr, [t1, t2, t3])
        mgr.build_search_index()

        # 同行 AND 照常; 全称行跨行(名字×标签)照常(「minions mteam」同型)
        assert [(x["hash"], x["by"]) for x in mgr.search_torrents("alpha s01")["results"]] == [("HA", "name")]
        assert [(x["hash"], x["by"]) for x in mgr.search_torrents("alpha mteam")["results"]] == [("HA", "name")]
        # 报障回归: delta 在名字行、03 只在集文件行 → file 兜底命中(HB 的 delta 则只在文件行)
        assert [(x["hash"], x["by"])
                for x in mgr.search_torrents("delta 03")["results"]] == [("HB", "file"), ("HC", "file")]
        # 26-09-26 的「跨行不命中」断言全部翻转: 词落不同行也命中
        assert [(x["hash"], x["by"])
                for x in mgr.search_torrents("gamma delta")["results"]] == [("HC", "name"), ("HB", "file")]
        assert [(x["hash"], x["by"])
                for x in mgr.search_torrents("gamma e03")["results"]] == [("HB", "file"), ("HC", "file")]
        assert [(x["hash"], x["by"])
                for x in mgr.search_torrents("e03 delta")["results"]] == [("HB", "file"), ("HC", "file")]
        # 单词行为不变; AND 不退化为 OR(alpha 与 delta 无一颗种子同有 → 空)
        assert [(x["hash"], x["by"])
                for x in mgr.search_torrents("delta")["results"]] == [("HC", "name"), ("HB", "file")]
        assert mgr.search_torrents("alpha delta")["results"] == []


def test_search_torrents_negative_term():
    """search_torrents 负词种子级(2026-09-27 定案): 任一候选行含负词 ⇒ 该种子整体排除 —— 单个
    种子内包含的合集(季包文件)统一计算; 多种子集合(辅种组/追剧)里的每个种子单独计算"""
    from helpers import FakeClient, FakeTorrent, make_manager, seed_store, seed_store, _fake_file

    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        mgr.client = client
        t1 = FakeTorrent(hash="HA", name="Show.S01E10.DV.1080p", state="stalledUP")
        # 单种子内包含的合集(季包): E09 文件带 DV ⇒ 统一计算, 整包排除(E10 行干净也救不回)
        t2 = FakeTorrent(hash="HB", name="Show.S01.Complete", state="stalledUP")
        client.files_map["HB"] = [_fake_file("Show.S01E09.DV.mkv", 0), _fake_file("Show.S01E10.1080p.mkv", 1)]
        # 多种子集合里的另一颗单集种子: 干净 ⇒ 留下
        t3 = FakeTorrent(hash="HC", name="Show.S01E10.1080p.CR.WEB-DL", state="stalledUP")
        seed_store(mgr, [t1, t2, t3])
        mgr.build_search_index()

        # "show 10 -dv": HA 名行含 dv ⇒ 排除; HB 的 E09.DV 文件行含 dv ⇒ 整包排除; HC 干净 ⇒ 名字命中
        r = mgr.search_torrents("show 10 -dv")
        assert [(x["hash"], x["by"]) for x in r["results"]] == [("HC", "name")], f"负词种子级: {r}"
        # 不带负词: 三颗都命中(即时命中 [HA, HC] 先于文件命中 HB; 旧口径 -dv 会把 dv 当正词搜, 顺带验证解析)
        assert [x["hash"] for x in mgr.search_torrents("show 10")["results"]] == ["HA", "HC", "HB"]
        # 排除短语: "web dl" 作为短语只排除 HC(HA/HB 不含该短语)
        assert [x["hash"] for x in mgr.search_torrents("show 10 -\"web dl\"")["results"]] == ["HA", "HB"]


def test_search_torrents_negative_torrent_veto():
    """search_torrents 负词种子级(2026-09-27 定案): 任一候选行(名字/站点/分类/路径/标签/文件行)
    含负词 ⇒ 整种子排除, 优先于一切正词命中

    两轮实机报障的收口: 1.「cat and -11」(26-09-26) —— E11 单文件的种子名行含 "11" 被行级作废,
    却被不含 "11" 的保存路径行整颗捞回; 2.「-mteam」(27-09-27) —— 站点/标签行负词拦不住名字行
    正词命中。负词必须是种子级才有可预测的排除语义; 文件行同入种子级否决(见 negative_term)。
    """
    from helpers import FakeClient, FakeTorrent, FakeTracker, make_manager, seed_store, _fake_file

    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        mgr.client = client
        t1 = FakeTorrent(
            hash="HA",
            name="The.Cat.and.the.Dragon.S01E11.1080p.friDay.WEB-DL.AAC2.0.H.264-MWeb.mkv",
            state="stalledUP",
            save_path="D:/TV/The.Cat.and.the.Dragon.S01",
        )
        site = FakeTracker("MTeam")
        site.tags = []  # tracker_name 取 conf.name(默认 tags 会顶掉站点名)
        t2 = FakeTorrent(hash="HB", name="Alpha.S01", state="stalledUP", tracker_conf=site)
        # 名字含负词、文件行干净的种子: 文件轮也须受身份行否决约束
        t3 = FakeTorrent(hash="HC", name="E11.REPACK", state="stalledUP")
        client.files_map["HC"] = [_fake_file("Show.1080p.mkv", 0)]
        seed_store(mgr, [t1, t2, t3])
        mgr.build_search_index()

        # 报障1.回归: HA 名字行含 "11" ⇒ 整种子否决, 保存路径行("cat and" 齐、无 "11")不得捞回
        assert mgr.search_torrents("cat and -11")["results"] == []
        # 无负词时 HA 照常命中(名字行) —— 否决只由负词触发
        assert [(x["hash"], x["by"]) for x in mgr.search_torrents("cat and")["results"]] == [("HA", "name")]
        # 报障2.: HB 名字行通过 "alpha", 但站点行含 "mteam" ⇒ 整种子排除; 去负词后名字行照常命中
        assert mgr.search_torrents("alpha -mteam")["results"] == []
        assert [(x["hash"], x["by"]) for x in mgr.search_torrents("alpha")["results"]] == [("HB", "name")]
        # 文件轮同受身份行否决: HC 名字行含 "repack" ⇒ 排除, 唯一文件行(Show.1080p.mkv)干净也救不回
        assert mgr.search_torrents("show -repack")["results"] == []
        # 对照: 去掉负词后 HC 靠文件行命中("show" 只落在文件行)
        assert [(x["hash"], x["by"]) for x in mgr.search_torrents("show")["results"]] == [("HC", "file")]


def test_search_torrents_facet_rows():
    """search_torrents 候选行覆盖全部文本面(26-09-26 单点化): 站点/分类/保存路径/标签行即时匹配

    正词逐词跨行(拍板 26-09-27 二次定案): 每个正词命中任一候选行(全称行/文件行)即可; 负词
    种子级(26-09-27): facet 行含负词 ⇒ 整种子排除。
    服务端此前的候选行只有 名字/文件, 搜站点/标签只在种子页(旧客户端行)能搜到而分组/追剧页
    搜不到 —— 跨页不一致; 单点化后三页同源, 用 by 定位首个通过的行类别(前端不消费, 测试定位用)。
    """
    from helpers import FakeClient, FakeTorrent, FakeTracker, make_manager, seed_store

    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        mgr.client = client
        site = FakeTracker("MDCx")
        site.tags = []  # tracker_name 取 conf.name(FakeTracker 默认 tags=["HHan"] 会顶掉站点名)
        t1 = FakeTorrent(
            hash="HA",
            name="Alpha.S01E01",
            state="stalledUP",
            save_path="D:/media/anime",
            category="动漫",
            tags="HDCT, 2026",
            tracker_conf=site,
        )
        t2 = FakeTorrent(hash="HB", name="Beta.S01E02", state="stalledUP")
        seed_store(mgr, [t1, t2])
        mgr.build_search_index()

        # 站点/分类/标签/路径行: 各词只落在 HA 的对应行, 不在任何名字/文件里
        assert [(x["hash"], x["by"]) for x in mgr.search_torrents("MDCx")["results"]] == [("HA", "site")]
        assert [(x["hash"], x["by"]) for x in mgr.search_torrents("动漫")["results"]] == [("HA", "category")]
        assert [(x["hash"], x["by"]) for x in mgr.search_torrents("HDCT")["results"]] == [("HA", "tag")]
        assert [(x["hash"], x["by"]) for x in mgr.search_torrents("media anime")["results"]] == [("HA", "path")]
        # facet 行负词 = 整种子排除(2026-09-27 双轨定案): "anime -hdct" 标签行含负词 ⇒ 整种子排除,
        # 路径行干净也救不回(26-09-26 的「负词只作废该行」口径在此类行上被推翻)
        assert mgr.search_torrents("anime -hdct")["results"] == []
        # 同口径: "anime -media" 路径行含负词 ⇒ 整种子排除, 其余行不含 anime → 空结果
        assert mgr.search_torrents("anime -media")["results"] == []


def test_search_torrents_phrase():
    """search_torrents 短语: "…" 整段归一为**连续**子串(可含分隔符), 词序敏感 —— 与词间 AND 的区分用例"""
    from helpers import FakeClient, FakeTorrent, make_manager, seed_store, seed_store

    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        mgr.client = client
        t1 = FakeTorrent(hash="HA", name="Cat.Dog.And.Bird", state="stalledUP")
        seed_store(mgr, [t1])

        # 词间 AND: cat 与 and 同行即命中(不要求相邻)
        assert [x["hash"] for x in mgr.search_torrents("cat and")["results"]] == ["HA"]
        # 短语: 要求归一后连续出现 —— "cat and" 在 "cat dog and" 里不连续 → 不命中; "dog and" 连续 → 命中
        assert mgr.search_torrents('"cat and"')["results"] == []
        assert [x["hash"] for x in mgr.search_torrents('"dog and"')["results"]] == ["HA"]
        # 短语可跨 scene 分隔符: "cat dog" 命中点号分隔的连续两词
        assert [x["hash"] for x in mgr.search_torrents('"cat dog"')["results"]] == ["HA"]


def test_search_torrents_regression_envnv10():
    """search_torrents 回归(26-09-26 用户报障): 「恶女 10」须命中单文件发布物; -排除词生效

    旧口径整句连续子串匹配: 「恶女 10」要求两词连续, 而文件名里「恶女」后跟「雏宫蝶鼠替换传」、
    「10」在远处的 s01e10 里 —— 必不命中。现行逐词跨行 AND 口径下两词同行照常命中。
    """
    from helpers import FakeClient, FakeTorrent, make_manager, seed_store, seed_store

    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        mgr.client = client
        name = (
            "[虽然我不是完美恶女～雏宫蝶鼠替换传～].Futsutsuka.na.Akujo.dewa.Gozaimasu.ga."
            "Suuguu.Chouso.Torikae.Den.2026.S01E10.1080p.CR.WEB-DL.H264.AAC-UBWEB.mkv"
        )
        t1 = FakeTorrent(hash="HA", name=name, state="stalledUP")
        seed_store(mgr, [t1])

        r = mgr.search_torrents("恶女 10")
        assert [x["hash"] for x in r["results"]] == ["HA"], f"报障回归: 恶女 10 应命中: {r}"
        assert r["results"][0]["by"] == "name"
        # 短语与排除词: "s01e10" 连续命中; -ubweb 排除该发布组
        assert [x["hash"] for x in mgr.search_torrents('"s01e10"')["results"]] == ["HA"]
        assert mgr.search_torrents("恶女 10 -ubweb")["results"] == []


def test_search_torrents_negative_only_empty():
    """search_torrents 仅负词/空查询: 无正判据返回空 + negative_only 标记(前端提示依据), 不投递索引构建"""
    from helpers import FakeClient, FakeTorrent, make_manager, seed_store, seed_store

    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        mgr.client = client
        t1 = FakeTorrent(hash="HA", name="Alpha", state="stalledUP")
        seed_store(mgr, [t1])

        r = mgr.search_torrents("-dv")
        assert r == {"results": [], "building": False, "negative_only": True}
        assert mgr.web.commands.empty(), "仅负词无从起搜, 不应投递构建命令"
        # 空查询: 同样空结果, 但 negative_only=False(前端按普通空态处理)
        r2 = mgr.search_torrents("")
        assert r2 == {"results": [], "building": False, "negative_only": False}


def test_search_torrents_file_match():
    """search_torrents: 文件列表匹配(依赖已构建的索引), 命中文件名"""
    from helpers import FakeClient, FakeTorrent, make_manager, seed_store, seed_store

    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        mgr.client = client
        from helpers import _fake_file
        client.files_map["HA"] = [_fake_file("movie.mkv", 0)]
        client.files_map["HB"] = [_fake_file("soundtrack.flac", 0)]
        # 季包回归(26-09-26 报障): 包名不含集号 "12", 查询词只在集文件名里 —— 文件行必须命中
        client.files_map["HC"] = [
            _fake_file("The.Cat.and.the.Dragon.S01E12.1080p.friDay.WEB-DL.AAC2.0.H.264-MWeb.mkv", 0),
        ]
        t1 = FakeTorrent(hash="HA", name="Alpha", state="stalledUP")
        t2 = FakeTorrent(hash="HB", name="Beta", state="stalledUP")
        t3 = FakeTorrent(
            hash="HC", name="The.Cat.and.the.Dragon.S01.1080p.friDay.WEB-DL.AAC2.0.H.264-MWeb", state="stalledUP"
        )
        seed_store(mgr, [t1, t2, t3])
        mgr.build_search_index()  # 先构建索引

        # 文件命中: soundtrack 只在 HB 的文件里, 不在任何种子名中
        r = mgr.search_torrents("soundtrack")
        hashes = [x["hash"] for x in r["results"]]
        assert hashes == ["HB"], f"文件匹配应命中 HB: {r}"
        assert r["results"][0]["by"] == "file"
        assert r["building"] is False, "索引已就绪不应 building"

        # 季包: 名行含 cat 不含 12(12 不在任何全称行), 集文件行同含两词 → file 兜底命中
        r = mgr.search_torrents("cat 12")
        assert [(x["hash"], x["by"]) for x in r["results"]] == [("HC", "file")], f"季包集文件应命中: {r}"


def test_search_torrents_building_triggers():
    """search_torrents: 索引脏(种子集变化后)时返回 building=true 并投递构建命令"""
    from helpers import FakeClient, FakeTorrent, make_manager, seed_store, seed_store, _fake_file

    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        mgr.client = client
        client.files_map["HA"] = [_fake_file("movie.mkv", 0)]
        t1 = FakeTorrent(hash="HA", name="Alpha", state="stalledUP")
        seed_store(mgr, [t1])

        mgr.web.search_index_dirty = True  # 模拟种子集变化后未构建
        r = mgr.search_torrents("movie")
        assert r["building"] is True, "索引脏时 building 应为 True"
        # 名称未命中, 文件索引未就绪 -> 无结果, 但投递了构建命令
        assert r["results"] == []
        cmd, payload = mgr.web.commands.get_nowait()
        assert cmd == "build_search_index" and payload == {}

        # 主循环构建后再查 -> building 消除且文件匹配生效
        mgr._cmd_build_search_index()
        r2 = mgr.search_torrents("movie")
        assert r2["building"] is False
        assert [x["hash"] for x in r2["results"]] == ["HA"]


def test_api_search_endpoint(web_env):
    """GET /api/search: 端点返回搜索结果(名称匹配即时), 空查询返回空"""
    mgr, client = web_env
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    # mock 替身: 直接返回固定结果(端点仅做转发, 逻辑由 search_torrents 单测覆盖); 空查询返回空
    mgr.search_torrents = lambda q: (
        {
            "results": [],
            "building": False
        } if not (q or "").strip() else {
            "results": [{
                "hash": "H1",
                "name": q,
                "by": "name"
            }],
            "building": False
        }
    )
    r = client.get("/api/search", params={"q": "movie"}, headers=auth).json()
    assert r["results"][0]["name"] == "movie"
    r2 = client.get("/api/search", params={"q": ""}, headers=auth).json()
    assert r2["results"] == [] and r2["building"] is False
    # 鉴权: 无密钥 401
    assert client.get("/api/search", params={"q": "movie"}).status_code == 401


def test_api_paths_endpoint(web_env):
    """GET /api/paths: 已知目录聚合(DLG-04): 组 save_path + 现有种子 save_path, 排序去重

    组 key 首元已是规范化 save_path; 种子侧经 path_normalize 归一分隔符后去重(反斜杠写法
    与组同径不重复); 空路径跳过; 只读快照无副作用; 鉴权沿用 /api/* 依赖。
    """
    mgr, client = web_env
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    mgr.store.groups = {
        ("R:/Downloads", ("a.mkv", "b.mkv")): ["HA", "HB"],
        ("D:/ISO", ("x.iso", )): ["HC"],
    }
    mgr.store.by_hash = {
        "HA": SimpleNamespace(hash="HA", save_path="R:\\Downloads"),  # 反斜杠写法 -> 与组 key 同径去重
        "HC": SimpleNamespace(hash="HC", save_path="D:/ISO"),
        "HD": SimpleNamespace(hash="HD", save_path="E:/TV/"),
        "HE": SimpleNamespace(hash="HE", save_path=""),  # 空路径跳过
    }
    r = client.get("/api/paths", headers=auth).json()
    assert r == {"paths": ["D:/ISO", "E:/TV/", "R:/Downloads"]}, r
    # 只读无副作用: 快照未被改动
    assert set(mgr.store.groups) == {("R:/Downloads", ("a.mkv", "b.mkv")), ("D:/ISO", ("x.iso", ))}
    assert set(mgr.store.by_hash) == {"HA", "HC", "HD", "HE"}
    # 鉴权: 无密钥 401
    assert client.get("/api/paths").status_code == 401


def test_api_open_path_endpoint(web_env, tmp_path):
    """POST /api/open-path (FX-14 + R10-10): 服务端自行派生目录/文件后交系统默认程序打开

    覆盖: 目录型 content_path 取自身 / **文件型 content_path 取文件本身并带 select=True(R10-10
    "在文件夹中选中相关文件")** / content_path 缺失回退 save_path / **content_path 未落盘(下载中,
    qB 报逻辑完成名而磁盘尚无该路径)回退 save_path, 不因"未完成"而 404** / 组键取 key 首元 /
    未知组与不存在目录 404 / content 与 save_path 都不存在 404 / kind 非法 400 /
    **客户端额外传入的 path 被忽略**(安全红线: 否则等于把"任意文件执行"暴露给 WEB 端点) / 鉴权 401。
    """
    mgr, client = web_env
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    d_content = tmp_path / "content"
    d_content.mkdir()
    f_file = d_content / "movie.mkv"
    f_file.write_bytes(b"x")
    d_seed = tmp_path / "seeds"
    d_seed.mkdir()
    norm = lambda p: str(p).replace("\\", "/")  # noqa: E731  与 utils.path_normalize 同径(仅统一分隔符)
    mgr.store.groups = {(norm(d_seed), ("a.mkv", )): ["HA"]}
    mgr.store.by_hash = {
        "HA":
            SimpleNamespace(hash="HA", save_path=str(d_seed), content_path=str(d_content)),
        "HB":
            SimpleNamespace(hash="HB", save_path=str(d_seed), content_path=str(f_file)),
        "HC":
            SimpleNamespace(hash="HC", save_path=str(d_seed), content_path=""),
        # 下载中单文件种子: content_path 是 qB 报的逻辑完成名, 磁盘上尚未落盘(或带 .!qB 后缀) —— 实际故障场景
        "HD":
            SimpleNamespace(hash="HD", save_path=str(d_seed), content_path=str(d_seed / "incomplete.mkv")),
        # content 与 save_path 都不存在: 回退后终检兜底 404
        "HE":
            SimpleNamespace(hash="HE", save_path=str(tmp_path / "gone"), content_path=str(tmp_path / "gone" / "x.mkv")),
    }
    # web_env 的 store 是轻量 namespace(get 恒 None), 这里按真实 Store.get 语义接上 by_hash
    mgr.store.get = lambda h: mgr.store.by_hash.get(h)
    post = lambda body: client.post("/api/open-path", json=body, headers=auth)  # noqa: E731
    # patch 地址 = auto_qb.web.common.open_path(web.py 拆 web/ 包后模块地址稳定化;
    # 原地址 auto_qb.web.open_path 随模块拆分失效 —— 管线性改动, plan 26-09-22-1857 W1)
    with mock.patch("auto_qb.webui.server.common.open_path") as spy:
        # 1. 目录型 content_path -> 取自身(非选中语义)
        r = post({"kind": "torrent", "hash": "HA"})
        assert r.status_code == 200 and r.json() == {"opened": norm(d_content), "select": False}, r.text
        spy.assert_called_once_with(norm(d_content), select=False)
        # 2. 文件型 content_path(单文件种子) -> 打开该文件并**定位选中**(R10-10)
        spy.reset_mock()
        assert post({"kind": "torrent", "hash": "HB"}).json() == {"opened": norm(f_file), "select": True}
        spy.assert_called_once_with(norm(f_file), select=True)
        # 3. content_path 缺失 -> 回退 save_path
        spy.reset_mock()
        assert post({"kind": "torrent", "hash": "HC"}).json() == {"opened": norm(d_seed), "select": False}
        spy.assert_called_once_with(norm(d_seed), select=False)
        # 3b. content_path 未落盘(下载中既非目录也非文件) -> 回退 save_path, 不 404
        spy.reset_mock()
        assert post({"kind": "torrent", "hash": "HD"}).json() == {"opened": norm(d_seed), "select": False}
        spy.assert_called_once_with(norm(d_seed), select=False)
        # 4. 组: 组键首元即规范化 save_path(组内成员天然一致)
        spy.reset_mock()
        group_key = encode_group_key((norm(d_seed), ("a.mkv", )))
        assert post({"kind": "group", "key": group_key}).json() == {"opened": norm(d_seed), "select": False}
        spy.assert_called_once_with(norm(d_seed), select=False)
        # 5. 安全: 客户端多传的 path 被忽略 —— 打开的是服务端派生的目录, 不是它
        spy.reset_mock()
        post({"kind": "group", "key": group_key, "path": "C:/Windows/System32"})
        spy.assert_called_once_with(norm(d_seed), select=False)
        # 6. 未知组 / 未知 hash / 不存在目录 -> 404; kind 非法 -> 400; 均不调用系统打开
        spy.reset_mock()
        assert post({"kind": "group", "key": encode_group_key(("D:/nope", ("z", )))}).status_code == 404
        assert post({"kind": "torrent", "hash": "NOPE"}).status_code == 404
        assert post({"kind": "torrent", "hash": "HE"}).status_code == 404  # content 未落盘 + save_path 也不存在 -> 终检兜底 404
        assert post(
            {
                "kind": "group",
                "key": encode_group_key((norm(tmp_path / "missing"), ("a.mkv", )))
            }
        ).status_code == 404
        assert post({"kind": "wat"}).status_code == 400
        spy.assert_not_called()
    # 只读无副作用: 不入命令队列
    assert mgr.web.commands.empty()
    # 鉴权: 无密钥 401
    assert client.post("/api/open-path", json={"kind": "wat"}).status_code == 401


def test_api_fs_dirs_endpoint(web_env, tmp_path):
    """GET /api/fs/dirs (R10-11): 服务端目录浏览 —— 允许根白名单/只列目录/穿越防护/鉴权

    这是本项目唯一新增的**文件系统读**能力, 安全边界逐条固化: 1.首屏(path 空)= 允许根列表;
    2.只返回目录条目(同名文件不出现); 3.上溯到允许根为止(根之上 parent 为空);
    4.`..` 穿越与白名单外路径一律 403; 5.不存在/不是目录 404; 6.无白名单时空返回(不报错);
    7.指向根外的符号链接不出现在列表里(逃逸防护); 8.无密钥 401; 9.只读不入命令队列。
    """
    mgr, client = web_env
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    root = tmp_path / "root"
    (root / "sub" / "deep").mkdir(parents=True)
    (root / "b.txt").write_bytes(b"x")
    outside = tmp_path / "outside"
    outside.mkdir()
    norm = lambda p: str(p).replace("\\", "/")  # noqa: E731  与 utils.path_normalize 同径
    mgr.store.by_hash = {"HA": SimpleNamespace(hash="HA", save_path=str(root), content_path=str(root))}
    get = lambda p=None: client.get("/api/fs/dirs", headers=auth, params={} if p is None else {"path": p})  # noqa: E731

    # 1. 首屏 = 允许根列表(前端入口)
    body = get().json()
    assert body["path"] == "" and body["roots"] == [norm(root)]
    assert body["dirs"] == [{"name": norm(root), "path": norm(root)}]
    # 2. 列子目录: 只出现目录(同名文件被排除); 已在允许根 -> 不能再上溯
    body = get(norm(root)).json()
    assert [d["name"] for d in body["dirs"]] == ["sub"]
    assert body["path"] == norm(root) and body["parent"] == ""
    # 3. 进入子目录后可上溯回根
    body = get(norm(root / "sub")).json()
    assert [d["name"] for d in body["dirs"]] == ["deep"]
    assert body["parent"] == norm(root)
    # 4. 越界 / .. 穿越 / 不存在 -> 403 / 403 / 404
    assert get(norm(outside)).status_code == 403
    assert get(norm(root / ".." / "outside")).status_code == 403
    assert get(norm(root / "nope")).status_code == 404
    assert get(norm(root / "b.txt")).status_code == 404  # 目标存在但是文件 -> 不是目录
    # 5. 符号链接逃逸: 指向根外的子目录不进列表
    #    跳过条件有两种: (a) 环境不允许建链(Windows 未开开发者模式 -> OSError);
    #    (b) **建了但落成真实目录** —— 部分沙箱/文件系统重定向层会让 os.symlink "成功"却
    #    islink=False(实测 mode=0o40777), 此时根本不存在"逃逸链接", 断言无意义。
    #    这两种都是环境能力缺失, 不是代码缺陷 —— 真机上能建真链接时照常断言。
    link = root / "escape"
    try:
        os.symlink(outside, link, target_is_directory=True)
    except (OSError, NotImplementedError, AttributeError):
        pass
    else:
        if os.path.islink(link):
            assert "escape" not in [d["name"] for d in get(norm(root)).json()["dirs"]]
    # 6. 无白名单(还没有任何已知保存路径) -> 空返回而非报错
    mgr.store.by_hash = {}
    assert get().json() == {"path": "", "parent": "", "roots": [], "dirs": []}
    # 7. 鉴权 + 只读无副作用
    assert client.get("/api/fs/dirs").status_code == 401
    assert mgr.web.commands.empty()


@pytest.mark.skipif(not sys.platform.startswith("linux"), reason="只有大小写敏感的 FS(ext4)上两个名字才是两个目录; NTFS 上是同一个, 断言无意义")
def test_api_fs_dirs_case_sibling_is_outside_whitelist(web_env, tmp_path):
    """**大小写兄弟目录必须判为越界** —— `web._fs_real` 不得做 NTFS 式大小写折叠

    生产代码跑在**本机真实磁盘**上: Linux 下 `/x/Media` 与 `/x/media` 是两个**不同**目录。若把归一
    换成 `ntpath.normcase`(折叠大小写 + `/`->`\\`), 后者会被判成"在白名单内" ⇒ **越界放行**
    (fail-open, 安全方向反了)。`os.path.normcase` 在 Linux 是恒等函数, 恰恰是所需语义 —— 钉死它。
    WARN: 本条只能在 Linux 上真跑(NTFS 上根本建不出"仅大小写不同"的两个目录), 由 CI 验。
    """
    mgr, client = web_env
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    root = tmp_path / "Media"
    root.mkdir()
    sibling = tmp_path / "media"  # 仅大小写不同
    sibling.mkdir()
    # 前置校验: 这两者**确实是两个目录**(否则下面的 403 断言说明不了任何事)
    (root / "inside.txt").write_bytes(b"x")
    assert not (sibling / "inside.txt").exists(), "大小写兄弟必须是另一个目录, 否则本条断言无意义"
    norm = lambda p: str(p).replace("\\", "/")  # noqa: E731  与 utils.path_normalize 同径
    mgr.store.by_hash = {"HA": SimpleNamespace(hash="HA", save_path=str(root), content_path=str(root))}
    r = client.get("/api/fs/dirs", headers=auth, params={"path": norm(sibling)})
    assert r.status_code == 403, f"大小写兄弟目录不得被折叠进白名单(折叠 => 越界放行): {r.status_code}"


def test_api_fs_mkdir_endpoint(web_env, tmp_path):
    """POST /api/fs/mkdir (R10-11): 新建目录的边界 —— 单层名字/白名单/幂等/同名文件 409

    覆盖: 正常新建(目录真的出现在磁盘上 + 返回绝对路径) / 重名目录幂等(200 + existed=True) /
    同名**文件** 409 / 名字含分隔符或为 . .. -> 400 / 白名单外父目录 403 / 父目录不存在 404 /
    无密钥 401 / 不入命令队列(只建目录, 不碰任务队列与 state)。
    """
    mgr, client = web_env
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    root = tmp_path / "root"
    root.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    norm = lambda p: str(p).replace("\\", "/")  # noqa: E731
    mgr.store.by_hash = {"HA": SimpleNamespace(hash="HA", save_path=str(root), content_path=str(root))}
    post = lambda body: client.post("/api/fs/mkdir", json=body, headers=auth)  # noqa: E731

    # 1. 正常新建
    r = post({"path": norm(root), "name": "新文件夹"})
    assert r.status_code == 200 and r.json() == {"created": norm(root / "新文件夹"), "existed": False}, r.text
    assert (root / "新文件夹").is_dir()
    # 2. 重名目录幂等(不报错)
    assert post({"path": norm(root), "name": "新文件夹"}).json()["existed"] is True
    # 3. 同名文件 -> 409
    (root / "b.txt").write_bytes(b"x")
    assert post({"path": norm(root), "name": "b.txt"}).status_code == 409
    # 4. 名字含路径成分 / . / .. -> 400(只接受单层名字, 不做路径拼接)
    for bad in ("", "  ", "a/b", "a\\b", ".", ".."):
        assert post({"path": norm(root), "name": bad}).status_code == 400, bad
    # 5. 白名单外 / 父目录不存在 -> 403 / 404
    assert post({"path": norm(outside), "name": "x"}).status_code == 403
    assert post({"path": "", "name": "x"}).status_code == 403
    assert post({"path": norm(root / "missing"), "name": "x"}).status_code == 404
    # 6. 鉴权 + 不入命令队列(不绕过单一写线程: 只建目录)
    assert client.post("/api/fs/mkdir", json={"path": norm(root), "name": "x"}).status_code == 401
    assert mgr.web.commands.empty()


def test_fs_endpoints_route_fs_calls_through_long_path_prefix(web_env, tmp_path, monkeypatch):
    """fs 三端点的**文件系统调用**必须过 `add_long_path_prefix_for_win`(本次报障的核心)

    Windows 上 >MAX_PATH 的裸路径 `isdir` 给假 / `scandir` 抛 WinError 3 ⇒ 不加前缀时端点会
    误报 404, 而前端只看到"目录不存在或不可访问"。这里把前缀 helper 换成 spy, 逐端点钉住
    "确实调了它"。

    WARN: 测的是**路由**而不是平台效果: 真 Windows 行为在 Linux CI 上无法复现(平台固定约定见
    testing/file-conventions.md), 故宿主上前缀是恒等(前缀对 POSIX 路径无意义); 前缀本身的
    正确性与打开层分支另由 `test_exists_dir_file_apply_long_path_prefix` /
    `test_open_path_windows_*` 覆盖。26-09-27: 前缀单点收编进文件访问层(infra/file_access,
    plan 26-09-27-1407) —— spy 地址随单点迁到 `auto_qb.infra.utils.add_long_path_prefix_for_win`,
    断言意图不变(全部本地 syscall 过单点)。
    """
    from auto_qb.infra.utils import add_long_path_prefix_for_win as real_prefix

    mgr, client = web_env
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    root = tmp_path / "root"
    (root / "sub").mkdir(parents=True)
    norm = lambda p: str(p).replace("\\", "/")  # noqa: E731  与 utils.path_normalize 同径
    mgr.store.groups = {(norm(root), ("a.mkv", )): ["HA"]}
    mgr.store.by_hash = {"HA": SimpleNamespace(hash="HA", save_path=str(root), content_path=str(root))}
    mgr.store.get = lambda h: mgr.store.by_hash.get(h)

    calls = []

    def spy(p):
        calls.append(p)
        return real_prefix(p)

    monkeypatch.setattr("auto_qb.infra.utils.add_long_path_prefix_for_win", spy)

    # 1. 目录浏览
    assert client.get("/api/fs/dirs", headers=auth, params={"path": norm(root)}).status_code == 200
    assert norm(root) in calls, f"fs/dirs 的文件系统调用未过前缀 helper: {calls}"
    # 2. 新建目录
    calls.clear()
    assert client.post("/api/fs/mkdir", json={"path": norm(root), "name": "new"}, headers=auth).status_code == 200
    assert norm(root) in calls, f"fs/mkdir 的文件系统调用未过前缀 helper: {calls}"
    # 3. 打开目标文件夹(open_path 必须 mock —— 真调会弹资源管理器, 守阵判越界)
    calls.clear()
    with mock.patch("auto_qb.webui.server.common.open_path"):
        assert client.post("/api/open-path", json={"kind": "torrent", "hash": "HA"}, headers=auth).status_code == 200
    assert norm(root) in calls, f"open-path 的文件系统调用未过前缀 helper: {calls}"


def test_fs_endpoints_unmapped_root_semantic_404(web_env, tmp_path):
    """Mapped 模式下白名单内但未命中映射 -> 三端点语义化 404「不可判定」, 不是裸 500(BUG 回归)

    回归: fs 路由曾有五处两态布尔消费(not fa.isdir / if fa.exists / not fa.isfile),
    Mapped miss 时包装层返回 UNDETERMINED, 其 __bool__ 抛 TypeError ⇒ FastAPI 裸 500。
    收进 _determinable 单点分流后: 未命中 fs.path_map 的允许根 浏览/新建/打开 都返回
    带原因的 404(「不可判定」不冒充「不存在」, 报告 §05)。
    """
    from auto_qb.config import PathMapEntry

    mgr, client = web_env
    saved = file_access.get_file_access()
    file_access._instance = file_access.MappedFileAccess(
        (PathMapEntry(src="D:/Downloads", dst=str(tmp_path / "mnt")), )
    )
    try:
        auth = {"Authorization": f"Bearer {mgr.web.token}"}
        unmapped = tmp_path / "unmapped"
        unmapped.mkdir()  # 宿主真实存在, 但前缀不在映射表里 -> 逻辑空间不可判定
        norm = lambda p: str(p).replace("\\", "/")  # noqa: E731  与 utils.path_normalize 同径
        mgr.store.by_hash = {"HA": SimpleNamespace(hash="HA", save_path=str(unmapped), content_path="")}
        mgr.store.groups = {(norm(unmapped), ("a.mkv", )): ["HA"]}
        mgr.store.get = lambda h: mgr.store.by_hash.get(h)
        # 1. 目录浏览: 白名单内(是已知保存路径)但未命中映射 -> 404 不可判定
        r = client.get("/api/fs/dirs", headers=auth, params={"path": norm(unmapped)})
        assert r.status_code == 404 and "不可判定" in r.json()["detail"], r.text
        # 2. 新建文件夹: 父目录未命中映射 -> 404 不可判定
        r = client.post("/api/fs/mkdir", json={"path": norm(unmapped), "name": "x"}, headers=auth)
        assert r.status_code == 404 and "不可判定" in r.json()["detail"], r.text
        # 3. 打开路径(torrent): content_path 缺失回退 save_path(未命中) -> 404 不可判定
        r = client.post("/api/open-path", json={"kind": "torrent", "hash": "HA"}, headers=auth)
        assert r.status_code == 404 and "不可判定" in r.json()["detail"], r.text
        # 4. 打开路径(组): 组键首元未命中映射 -> 404 不可判定
        key = encode_group_key((norm(unmapped), ("a.mkv", )))
        r = client.post("/api/open-path", json={"kind": "group", "key": key}, headers=auth)
        assert r.status_code == 404 and "不可判定" in r.json()["detail"], r.text
    finally:
        file_access._instance = saved


def test_fs_path_helpers_strip_long_path_prefix_before_compare():
    """`_bare` / `_fs_real`: **比较前必须剥掉 `\\\\?\\` 前缀** —— 否则同一条路径的两种写法被判"越界"

    实测后果(Windows 真机): `os.scandir` 家族给出的 entry 路径**带前缀**, 而允许根
    不带 ⇒ `_within_roots` 恒 False ⇒ **子目录被全部过滤掉**(目录树恒空)。
    `os.path.realpath` 是否保留前缀**与路径长度有关**(实测短路径保留、长路径剥掉), 不能依赖它,
    故必须在比较前显式剥掉。

    本条是纯路径归一, **与宿主平台无关** ⇒ Linux CI 上也守得住(这正是把三个 helper 提到模块级
    而不是留在 `build_router` 闭包里的原因)。
    26-09-27: 前缀剥离/加前缀单点迁入文件访问层(infra/file_access, plan 26-09-27-1407),
    `_fs` 帮手随之删除(包装层内部自理) —— 剥前缀契约改在 file_access 单点断言, `_bare`
    保留薄委托供路由侧钉住。
    """
    from auto_qb.webui.server.routes import fs as fs_mod

    bare = os.path.abspath("x")
    assert fs_mod._bare("\\\\?\\" + bare) == bare
    assert fs_mod._bare(bare) == bare, "无前缀原样返回"
    assert fs_mod._bare("\\\\?\\UNC\\server\\share") == "\\\\server\\share", "UNC 形态还原"
    # 带前缀与不带前缀必须归一到同一个可比较形式(_fs_real 委托包装层, 内部先剥再规范化)
    assert fs_mod._fs_real("\\\\?\\" + bare) == fs_mod._fs_real(bare)
    # 前缀单点幂等: 已是带前缀形态再进包装层不得叠加 —— path_normalize 会把 `\\?\\` 折坏成 `/?/`
    fa = file_access.LocalFileAccess()
    assert fa._pref(fa._pref(bare)) == fa._pref(bare)
    assert file_access._norm_logical(file_access._norm_logical("\\\\?\\" + bare)) == file_access._norm_logical(bare)


def test_build_group_view_hr_tags(tmp_path):
    """分组视图透出 HR 标签展示值: 已触发未达标 -> hr_tag, 已达标 -> hr_tag_done

    判定与打标签流程同源(torrents.check_hr_condition/check_hr_satisfied), 标签文本经
    utils.replace_vars 展开 ${required_seeding_time} —— 前端只按文本相等着色, 故两者必须逐字一致。
    """
    from helpers import FakeClient, FakeTorrent, FakeTracker, _hr_rule, make_manager, seed_store

    hr = _hr_rule(add_tag="!!HR${required_seeding_time}!!", add_tag_for_satisfied="--HR${required_seeding_time}--")
    conf = FakeTracker("HHan", hr=hr)
    mgr = make_manager(str(tmp_path / "state.json"))
    mgr.client = FakeClient()

    def tor(h, name, seeding_time, downloaded=512**2):
        return FakeTorrent(
            hash=h,
            name=name,
            state="stalledUP",
            size=512**2,
            total_size=512**2,
            downloaded=downloaded,
            amount_left=0,
            progress=1.0,
            seeding_time=seeding_time,
            save_path=r"R:/s",
            tracker_conf=conf
        )

    seed_store(
        mgr,
        [
            tor("HA", "Pending.Show", 3600),  # 1 小时: 已触发 HR 但未达标(3D + 12H)
            tor("HB", "Done.Show", 4 * 86400),  # 4 天: 已达标
            tor("HC", "NoHR.Show", 4 * 86400, downloaded=0),  # 纯辅种(无下载量): 不触发 HR
        ]
    )
    for h, key in (("HA", ("R:/p", ("a.mkv", ))), ("HB", ("R:/d", ("b.mkv", ))), ("HC", ("R:/n", ("c.mkv", )))):
        mgr.store.groups[key] = [h]
        mgr.store.member_to_key[h] = key

    members = {g["name"]: g["members"][0] for g in mgr._build_group_view()}
    assert members["Pending.Show"]["hr_tag"] == "!!HR3D!!"
    assert members["Pending.Show"]["hr_tag_done"] == ""
    assert members["Done.Show"]["hr_tag"] == ""
    assert members["Done.Show"]["hr_tag_done"] == "--HR3D--"
    # 未触发 HR 条件时两字段都为空 -> 前端保持普通标签配色
    assert members["NoHR.Show"]["hr_tag"] == "" and members["NoHR.Show"]["hr_tag_done"] == ""
    # 新增展示字段(前端 H&R 栏 / 做种时长与分享率对照列的数据源): 触发与达成布尔 + 要求阈值
    assert members["Pending.Show"]["hr_triggered"] is True
    assert members["Pending.Show"]["hr_satisfied"] is False
    assert members["Pending.Show"]["hr_req_time"] == 3 * 86400 + 12 * 3600
    assert members["Pending.Show"]["hr_req_ratio"] == 0.0
    assert members["Done.Show"]["hr_triggered"] is True and members["Done.Show"]["hr_satisfied"] is True
    assert members["NoHR.Show"]["hr_triggered"] is False


def testhr_view_fields_three_state(tmp_path):
    """详情字段透出站点侧三态与依据 + 删除安全档位×来源(WebUI 可观测性): 接入站点才有值, 未接入全空"""
    from auto_qb.config import HRRule, TrackerConfig
    from auto_qb.config.models import SiteHrCheckConfig
    from auto_qb.core.qbmanager import QbManager
    from auto_qb.hr.resolve import HrIdentity, HrJudgement, HrSiteFacts
    from auto_qb.torrents import TorrentRecord
    from helpers import FakeTorrent, make_manager

    mgr = make_manager(str(tmp_path / "state.json"))
    rec = TorrentRecord.from_torrent(FakeTorrent(hash="HA", state="stalledUP", downloaded=0))
    conf = TrackerConfig(
        name="HHan", domains=["hhanclub.net"], hr=HRRule(required_seeding_time=3 * 86400, condition=("dlratio", 0.7))
    )
    rec.tracker_conf = conf

    # 未接入 hr_check: 三态四项全空(前端据此不显示三态行, 与既有四个字段的空值口径一致);
    # 本地未触发 + 未做种满 => 删除安全 = warning 疑似辅种黄档(计划 26-09-30-0559 §5, 旧「不适用」作废)
    fields = QbManager.hr_view_fields(rec)
    assert fields["hr_state"] == "" and fields["hr_state_text"] == "" and fields["hr_reason"] == ""
    assert fields["hr_safety"] == "warning" and fields["hr_safety_src"] == "local"
    assert fields["hr_safety_text"] == "本地·未达标(疑似辅种)"

    conf.hr_check = SiteHrCheckConfig(
        enabled=True, tracker="hhanclub", hr_page_url="https://hhanclub.net/myhr.php", required_seeding_time=86400.0
    )
    link = mock.Mock()
    link.judge.return_value = HrJudgement(
        identity=HrIdentity.HR, reason="清单命中·考察中(档位 A)", site_satisfied=False, site="HHan"
    )
    rec.hr_link = link
    fields = QbManager.hr_view_fields(rec)
    assert fields["hr_triggered"] is False, "hr_triggered = 纯本地触发判据(展示辅助), downloaded=0 不触发"
    assert fields["hr_satisfied"] is False, "命中考察中 => 义务仍在, 恒未达标"
    assert fields["hr_state"] == "hr" and fields["hr_state_text"] == "受管束"
    assert fields["hr_reason"] == "清单命中·考察中(档位 A)"
    # 删除安全档位: 命中考察中 => 在线·考察中, 不能删(v3: identity=HR 恒映射 site_scope)
    assert fields["hr_safety"] == "danger" and fields["hr_safety_src"] == "site_scope"
    assert fields["hr_safety_text"] == "在线·考察中"

    # 命中行带档位(A 考察中): 档位即结论 —— 在线·考察中, 不能删(本地值不参与)
    link.judge.return_value = HrJudgement(
        identity=HrIdentity.HR,
        reason="清单命中·考察中(档位 A)",
        site_satisfied=False,
        facts=HrSiteFacts(lane="A"),
        site="HHan",
    )
    fields = QbManager.hr_view_fields(rec)
    assert fields["hr_safety"] == "danger" and fields["hr_safety_src"] == "site_scope"
    assert fields["hr_safety_text"] == "在线·考察中"

    # 命中 B 已达标(终态): 放行 + satisfied —— 可删, 来源「在线·已达标」
    link.judge.return_value = HrJudgement(
        identity=HrIdentity.RELEASED,
        reason="清单命中·已达标(B, 终态放行)",
        site_satisfied=True,
        facts=HrSiteFacts(lane="B", remain_seconds=0, ratio=1.5),
        site="HHan",
    )
    fields = QbManager.hr_view_fields(rec)
    assert fields["hr_satisfied"] is True
    assert fields["hr_safety"] == "safe" and fields["hr_safety_src"] == "site_satisfied"
    assert fields["hr_safety_text"] == "在线·已达标"
    # 站点侧值(两套值对账): 已给的照传, 没给的空串 —— 未知与 0 必须可分(0 = 已达标)
    assert fields["hr_site_lane"] == "B" and fields["hr_site_remain"] == 0
    assert fields["hr_site_ratio"] == 1.5 and fields["hr_site_need"] == "" and fields["hr_site_dl"] == ""

    # 命中 C 未达标(终态): 放行但「考核未通过」红档(不能删桶) —— 站点结论已定
    link.judge.return_value = HrJudgement(
        identity=HrIdentity.RELEASED,
        reason="清单命中·未达标(C, 考核结论已定, 终态放行)",
        site_satisfied=False,
        facts=HrSiteFacts(lane="C"),
        site="HHan",
    )
    fields = QbManager.hr_view_fields(rec)
    assert fields["hr_triggered"] is False and fields["hr_state"] == "released_non_hr"
    assert fields["hr_safety"] == "failed" and fields["hr_safety_src"] == "site_unsatisfied"

    # 放行记录(覆盖范围内未列出): 可删, 来源「在线·已核实」
    link.judge.return_value = HrJudgement(identity=HrIdentity.RELEASED, reason="放行记录(覆盖范围内未列出)")
    fields = QbManager.hr_view_fields(rec)
    assert fields["hr_triggered"] is False and fields["hr_state"] == "released_non_hr"
    assert fields["hr_state_text"] == "已核实·放行"
    assert fields["hr_safety"] == "safe" and fields["hr_safety_src"] == "site_released"
    assert fields["hr_safety_text"] == "在线·已核实，安全放行"

    # D 档已免罪(v3.4, 2026-09-26 用户指令): 站点明确终态结论, 来源单列「在线·已免罪」,
    # 不与缺席证据 site_released 混一个 token
    from auto_qb.hr.model import SOURCE_EXEMPT, SOURCE_SATISFIED

    link.judge.return_value = HrJudgement(
        identity=HrIdentity.RELEASED,
        reason="放行记录(D 档已免罪)",
        released_src=SOURCE_EXEMPT,
    )
    fields = QbManager.hr_view_fields(rec)
    assert fields["hr_safety"] == "safe" and fields["hr_safety_src"] == "site_exempt"
    assert fields["hr_safety_text"] == "在线·已免罪"

    # 放行记录无命中行事实 + released_src=satisfied(计划 26-10-02-1936 §3.5): 无事实分支与
    # 带事实分支同文「在线·已达标」—— 同一结论两种写法(旧「在线·已达标(毕业)」)消灭
    link.judge.return_value = HrJudgement(
        identity=HrIdentity.RELEASED,
        reason="放行记录(已达标移出)",
        released_src=SOURCE_SATISFIED,
    )
    fields = QbManager.hr_view_fields(rec)
    assert fields["hr_safety"] == "safe" and fields["hr_safety_src"] == "site_satisfied"
    assert fields["hr_safety_text"] == "在线·已达标"

    # 本地兜底路径(judge 返回 None: 站点侧无可查键/未发布视图): triggered/satisfied 就是本地结论,
    # 来源统一 local —— 呈现口径与打标流程同源, 不会出现"标签说达标、徽章说不能删"
    rec2 = TorrentRecord.from_torrent(
        FakeTorrent(hash="HB", state="stalledUP", size=512**2, total_size=512**2, downloaded=512**2, seeding_time=3600)
    )
    rec2.tracker_conf = conf
    rec2.hr_link = link
    link.judge.return_value = None
    fields = QbManager.hr_view_fields(rec2)
    assert fields["hr_triggered"] is True and fields["hr_satisfied"] is False
    assert fields["hr_safety"] == "danger" and fields["hr_safety_src"] == "local"
    assert fields["hr_safety_text"] == "本地·未达标"
    rec3 = TorrentRecord.from_torrent(
        FakeTorrent(
            hash="HC", state="stalledUP", size=512**2, total_size=512**2, downloaded=512**2, seeding_time=4 * 86400
        )
    )
    rec3.tracker_conf = conf
    rec3.hr_link = link
    fields = QbManager.hr_view_fields(rec3)
    assert fields["hr_safety"] == "safe" and fields["hr_safety_src"] == "local"
    assert fields["hr_safety_text"] == "本地·达标"


def testhr_view_fields_excluded(tmp_path):
    """HR 排除态视图(计划 26-09-28-1805): hr_excluded=True, 触发/达标恒 False,
    删除安全档位短路成空串(「不适用」空白由组装层保证, 计划 26-09-30-0559 §5);
    hr_excluded_by 透出命中来源 token(2026-10-02: 悬停弹窗依据行「按什么排除」的数据源)"""
    from auto_qb.config import HRRule, TrackerConfig
    from auto_qb.config.models import SiteHrCheckConfig
    from auto_qb.core.qbmanager import QbManager
    from auto_qb.torrents import TorrentRecord
    from helpers import FakeTorrent, make_manager

    make_manager(str(tmp_path / "state.json"))  # 与其它视图测试同构(本函数直调类方法, 不读实例态)
    rec = TorrentRecord.from_torrent(FakeTorrent(hash="HD", state="stalledUP", downloaded=0, tags="noHR"))
    conf = TrackerConfig(
        name="HHan",
        domains=["hhanclub.net"],
        hr=HRRule(required_seeding_time=3 * 86400, condition=("dlratio", 0.7), exclude_tags=["noHR"]),
    )
    conf.hr_check = SiteHrCheckConfig(
        enabled=True, tracker="hhanclub", hr_page_url="https://hhanclub.net/myhr.php", required_seeding_time=86400.0
    )
    rec.tracker_conf = conf
    rec.hr_link = mock.Mock()  # 排除种子连判定桥都不该被打扰
    fields = QbManager.hr_view_fields(rec)
    assert fields["hr_excluded"] is True
    assert fields["hr_excluded_by"] == "tag"
    assert fields["hr_triggered"] is False and fields["hr_satisfied"] is False
    assert fields["hr_state"] == "" and fields["hr_safety"] == "" and fields["hr_safety_text"] == ""
    assert fields["hr_safety_src"] == "" and fields["hr_site_lane"] == ""
    rec.hr_link.judge.assert_not_called()

    # 分类命中(2026-10-02 实报的主场景)与双命中: 来源 token 随命中列表走
    conf.hr.exclude_categories = ["keep"]
    rec_cat = TorrentRecord.from_torrent(FakeTorrent(hash="HG", state="stalledUP", downloaded=0, category="keep"))
    rec_cat.tracker_conf = conf
    fields_cat = QbManager.hr_view_fields(rec_cat)
    assert fields_cat["hr_excluded"] is True and fields_cat["hr_excluded_by"] == "category"
    rec.tags = "noHR"
    rec.category = "keep"
    fields_both = QbManager.hr_view_fields(rec)
    assert fields_both["hr_excluded_by"] == "tag+category", "标签与分类同时命中时 token 合并"

    # 未命中排除表: hr_excluded=False, 行为照旧
    rec2 = TorrentRecord.from_torrent(FakeTorrent(hash="HE", state="stalledUP", downloaded=0, tags="HHan"))
    rec2.tracker_conf = conf
    assert QbManager.hr_view_fields(rec2)["hr_excluded"] is False

    # 空配置分支也带 hr_excluded/hr_excluded_by 键(前端字段一致性守阵消费全键集)
    empty = QbManager.hr_view_fields(TorrentRecord.from_torrent(FakeTorrent(hash="HF")))
    assert empty["hr_excluded"] is False and empty["hr_excluded_by"] == ""


def test_api_hr_status_disabled_returns_empty_state(web_env):
    """未启用 HR 时 /api/hr/status 回 enabled=false + 说明(前端据此显示空态, 而不是报错)"""
    mgr, client = web_env
    r = client.get("/api/hr/status", headers={"Authorization": f"Bearer {mgr.web.token}"})
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
    r = client.get("/api/hr/status", headers={"Authorization": f"Bearer {mgr.web.token}"})
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
    # 表② 波次表档位徽章人话(计划 26-10-01-2216 §6.2 mockup「A 考察中」形态): 曾因 LaneStatus
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
    body = client.get("/api/hr/status", headers={"Authorization": f"Bearer {mgr.web.token}"}).json()
    site = body["sites"][0]
    assert site["releases_enabled"] is False
    assert "blocking" in site, f"要说清卡在哪一步: {site}"
