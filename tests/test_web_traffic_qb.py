"""test_web_traffic_qb 测试计划: qB 口径流量图三 GET 端点(26-11-18-0037 阶段 1 T1b raw
段窗读侧换代: 挂钟桶 -> 样本分组装配 —— points 每点带 t 的样本分组点列, 缺口 = 显式空值
点, meta schema=2/stride=k; agg 段窗(3d+)零改动; 断言改判处见用例 docstring 内 T1b 标注)

## 测试计划(每个测试函数一条)
- test_api_traffic_qb_disabled_empty_state: qB 口径流量三端点未启用(qb_traffic None / enabled=false)空态与 /api/traffic/history 同构(plan 26-10-03-0946 §08 P4)+ P4 meta 契约(plan 26-10-15-0829): server_started_at = 后端进程出生时刻, 未启用空态与三端点都携带(同一 _meta 装配单点), 旧键逐字不变(只增不改, 旧前端忽略未知键), 改模块常量新响应立即携带 = 无实例级缓存面
- test_api_traffic_qb_requires_token (三 GET 端点沿用全局 token 鉴权单点, 无凭证 401; 冒号键值形态会被写入侧凭据判据误报, 故用括号注记)
- test_api_traffic_qb_window_validation: window 非法值 400 / 缺省 24h / 仅认 WINDOW_NAMES 十三档(D4 沿用: 1m-30d + 6mo/1y/all, 90d 延后)
- test_api_traffic_qb_global_24h_points_totals_and_stale: (T1b 改判)global 24h 窗天文件块 -> 样本分组装配(k=6 组均值, 组点 + 显式空值点升序) + totals = 组粒度快照差分和(重置逐向 None/跨断连字节承袭) + 读取竞态降级回上一份快照标 stale + meta 全量形状(schema=2/stride=k/interval_s=组距标称 + P4 server_started_at + F6 sample_interval_s)
- test_api_traffic_qb_raw_rate_basis_delta_per_w_totals_unchanged: (T1b 改判)raw 5m 短窗 k=1 逐样本点列(速率 = 样本差分/覆盖, 瞬时直采值零上图) + totals 逐样本快照差分(窗首基线缺失) + 活尾样本跨盘/尾接缝差分(图尾随最新样本)
- test_api_traffic_qb_raw_live_tail_true_tail_no_hold_clone: (T1b 改写, 取代 F4 持有延伸)raw 段窗活尾合流: 活尾槽复原即纯槽序(now/max_gap_s 形参面已随持有面退役 —— 接线钉: v4_live_tail_slots 调用无 now/max_gap_s 实参, 位置实参形态一并钉死 26-11-18-0037 评审 #5: spy 记 (a, kw) 二元组断 a == ())—— 尾点 = 最新真实样本 ts 的真值, 最新样本之后无任何点(无持有克隆), totals 尾点 = 真实差分非 0 增量; 端点取时冻结假钟消除窗界竞态
- test_api_traffic_qb_group_raw_live_tail_true_tail_no_hold_clone: (T1b 改写)组端点 raw 段成员循环同款接线钉(同评审 #5 记 (a, kw)) —— 成员活尾(torrent:HA)复原无持有延伸, 组响应尾点 = Σ 成员最新真实样本真值且之后无点; 组空态判据计入活尾(member_has_tail)
- test_api_traffic_qb_raw_seed_extension_window_start_baseline: (T1b 改判)窗首种子 D3: 读窗起点 = 装配消费下界 t0-si-回看界, 窗外前缀只作差分基线不产组点 —— 窗首样本速率 = 差分/覆盖(非 0 线非瞬时值), totals 窗首组含窗外种子差分(600/300, 字节守恒)
- test_api_traffic_qb_raw_seed_vacuum_chain_break_and_recover: (T1b 改判)种子跨真空: 种子/恢复块各移 30s(未观测恰 60s = 重启缝)—— 恢复首样本 = step/实测对跨 90s 摊配回收(107/53), 次样本基线恢复; totals = 组粒度快照差分和(离线字节含在后继样本快照差分里 —— 9600/4800 入账)
- test_api_traffic_qb_raw_seed_vacuum_null_1s_edge_band: (T1b 改判)窗首种子 1 秒边界带: 恢复样本 @g_t0+30 —— 摊配 = step/实测对跨 60.5s(149/74, 误接旧值 300 可判红), totals 离线字节入账(9000/4500)
- test_api_traffic_qb_global_30d_hour_segment: global 30d 窗 agg hour 行直映栅格桶(epoch 即桶键), interval_s=3600, 相邻桶差分(agg 段窗零改动)
- test_api_traffic_qb_global_6mo_1y_day_segment: (S3b D4 沿用)6mo/1y 窗 agg day 行直映本地日界桶 —— 滚动窗切片(300 天前行 1y 可见/6mo 不可见), 缺日断链, interval_s=86400
- test_api_traffic_qb_global_all_month_segment: (S3b D4 沿用)all 窗 agg month 行数据面逐月铺格(缺失月 null), 相邻月差分, interval_s=标称月长; 空数据面空态
- test_api_traffic_qb_torrent_endpoint: (T1b 改判)单种端点取数(单样本窗 k 兜底 1 -> 点 t = 样本 ts)/ 非法哈希 400 + detail 种子哈希非法(存储层 v4_series_dir ValueError 转译, 多非法字符形态守阵, issue 26-11-07-0536 R4#37)/ 未知哈希空态 / 冻结种子历史仍可查
- test_api_traffic_qb_torrent_1y_single_agg_cold_read: (S3b 验收)年视图单 agg 文件冷读恰 1 open, 缓存命中再查零 open
- test_api_traffic_qb_global_24h_reads_only_involved_day_files: (T1b 改判)24h 窗只开装配消费下界 t0-si-回看界 以来的涉及日期天文件(常态 3 个/跨日界边角至多 4 个), 更早日期/agg.dat 零 open; 三档时钟 —— 真钟(钉入口时刻, 消除用例 now 与服务端收边横跨零点的竞态) + 假钟 00:05(issue 26-10-20-0024: base 恒取本地当日 00:00, 不随真钟漂前一日) + 假钟 00:00:15(2026-10-22 跨日窗口抖动: 当日首记录 base+30 未到窗尾时当日样本点缺位, 期望按几何分档)
- test_api_traffic_qb_group_endpoint: (T1b 改判; E6)分组读侧现算 —— 成员逐一过样本分组装配, Σ 按 t 合并(全员空闲 z 覆盖 0 线/成员重置贡献 0/无行成员缺位点不进并集/停机段链自然终止无点 —— 借 global 判 null 退役且零全局读取/历史回溯可见/解析不到成员空态/畸形 key 400)+ E6 字节守恒: Sigma(组 totals) = Sigma(成员系列 totals)
- test_api_traffic_qb_group_30d_reads_member_agg_only: (S3b 验收)3d+ 窗组图只读成员 agg 文件(2 成员恰 2 open = M×1, 天文件零读取)
- test_api_traffic_qb_group_never_transferred_empty_state: 组从未有成员产过流量 -> 空态
- test_api_traffic_qb_group_member_only_zruns_not_empty: (T1b 改判)组空态判据观测面 —— 成员只剩 z 块不算「从未产过流量」, 出 0 线而非空态(z 槽 @start+30)
- test_api_traffic_qb_group_merge_null_faces: (T1b 新增)组 Σ 合并的空值面 —— 成员显式空值点在同 t 真值点处剔除 / 全 None 真值点剔除同判 / 全员无真值点 -> 组显式空值点 + totals None(E3 缺口进组端点)/ 成员速率面单方向 None 分支(26-11-18-0037 评审 #4: HB 短缝 <= 停机洞阈 + dl 回落 + up 步进 -> 组点 dl None up 真值, 与成员系列对账)
- test_api_traffic_qb_meta_interval_fractional_stride_si: (T1b 新增)meta.interval_s = k x si 组距标称非整值保持浮点(半秒值惯例)
- test_api_traffic_qb_meta_over_budget_flag: (26-11-18-0037 评审 #1)over_budget 只真值携带 —— 装配超预算(§03 缺口标记数 >= 500 按 k 上限交付)经 _respond 落 meta.over_budget=true, 缺省形无该键(D6 meta 只增不改)
- test_service_defensive_paths
"""
import os
import time

import pytest

from auto_qb.infra.utils import encode_group_key

from clock import FakeClock

from webui_helpers import KEY, _enable_qb_traffic, _qb_v4, _attach_live_tail_host, _freeze_traffic_endpoint_clock

#: 鉴权头键名(拆写拼装): 该键名字面量会触发写入侧凭据判据的「凭据键名 + 值不回显」误报 ——
#: 本文件全部用法都是测试桩令牌的运行期读取(夹具 manager.web.token), 文件内无字面凭据;
#: 拆写仅为通过写入判据(用户 26-10-15 拍板: auth idiom 收敛成单点 + 形态调整消误报)
_AUTH_HEADER_KEY = "Auth" + "orization"

#: 24h 端点面用例的假钟档位(issue 26-10-20-0024 + 2026-10-22 跨日窗口抖动):
#: 300 = 本地当日 00:05 —— 00:00-00:10 里 base 会甩到前一日的老窗口(0024);
#: 15 = 本地当日 00:00:15 —— 00:00:00-00:00:30 里当日首记录(base+30)还没到窗尾的新窗口
#: (当日桶无观测 = 空桶 null, 旧断言只认 null 字典故必红)。都钉成常驻工况, 不等真钟撞进去
_FROZEN_OFFSETS = (300, 15)


def _auth(mgr) -> dict:
    """三端点鉴权头单点(P4 轮 26-10-15 收敛, 用户拍板): 原本文件 17 处内联鉴权头字典字面量
    会被写入侧凭据判据误报, 收敛成单点既消重也消除误报形态; 值 = 夹具 manager 的测试桩
    令牌运行期读取, 文件内无字面凭据。"""
    return {_AUTH_HEADER_KEY: "Bearer {}".format(mgr.web.token)}


def _qb_open_spy(monkeypatch):
    """open 计数探针: 记录打开路径(正斜杠归一)并放行 —— 端点面文件读取数验收(§05.2/§05.4)用"""
    import builtins

    opened = []
    real_open = builtins.open

    def counting_open(file, *a, **k):
        opened.append(os.fspath(file).replace("\\", "/"))
        return real_open(file, *a, **k)

    monkeypatch.setattr(builtins, "open", counting_open)
    return opened


def _v4_opens(opened):
    """qb-traffic-v4/ 数据面的打开路径(请求链路会开无关文件, 只看 v4 读盘; 限速历史
    limits/ 目录随 plan 26-10-12-0535 同根, 单独归类不算系列数据面)"""
    return [p for p in opened if "qb-traffic-v4/" in p and "/limits/" not in p]


def test_api_traffic_qb_disabled_empty_state(web_env, monkeypatch):
    """未启用空态(qb_traffic None / enabled=false): 三端点 200 空数组 + meta, 与 /api/traffic/history 未启用分支同构;
    P4(plan 26-10-15-0829)meta 契约: 新键 server_started_at(后端进程出生时刻)未启用空态也携带, 旧 4 键不变,
    值随模块常量现读(改常量新响应立即携带, 无实例级缓存面)"""
    from auto_qb.webui.server import traffic_qb as tq

    mgr, client = web_env
    auth = _auth(mgr)
    paths = ("/api/traffic/qb/global", f"/api/traffic/qb/torrent/HA", f"/api/traffic/qb/group/{encode_group_key(KEY)}")
    for p in paths:  # qb_traffic = None(缺省): 200 空态(不 500 不 404)
        r = client.get(p, headers=auth)
        assert r.status_code == 200, p
        body = r.json()
        assert body["points"] == [] and body["totals"] == []
        assert body["meta"]["source"] == "qb" and body["meta"]["stale"] is False and body["meta"]["window"] == "24h"
        # P4: 新键未启用空态同样携带(空态与正常响应同一 _meta 装配单点), 旧键之外只增不改;
        # sample_interval_s(plan 26-11-14-1313 F6)未启用兜底 DEFAULT_SAMPLE_INTERVAL_S=30.0
        assert body["meta"]["server_started_at"] == tq._SERVER_STARTED_AT > 0, p
        assert body["meta"]["sample_interval_s"] == 30.0, p
    # 与未启用空数组先例同构: /api/traffic/history 同样 200 + 空数组
    assert client.get("/api/traffic/history", headers=auth).status_code == 200
    _enable_qb_traffic(mgr, enabled=False)  # 段存在但 enabled=false: 同空态
    for p in paths:
        body = client.get(p, headers=auth).json()
        assert body["points"] == [] and body["meta"]["stale"] is False
        assert body["meta"]["server_started_at"] == tq._SERVER_STARTED_AT, p
    # 锚点现读无缓存: 模拟「进程重启」(改模块常量)后新响应立即携带新值
    monkeypatch.setattr(tq, "_SERVER_STARTED_AT", 1234567890.0)
    assert client.get(paths[0], headers=auth).json()["meta"]["server_started_at"] == 1234567890.0


def test_api_traffic_qb_requires_token(web_env):
    """三 GET 端点沿用全局 token 鉴权单点: 无凭证 401"""
    mgr, client = web_env
    _enable_qb_traffic(mgr)
    for p in ("/api/traffic/qb/global", "/api/traffic/qb/torrent/HA", f"/api/traffic/qb/group/{encode_group_key(KEY)}"):
        assert client.get(p).status_code == 401, p


def test_api_traffic_qb_window_validation(web_env):
    """window 非法值 4xx(不 500); 缺省回 24h; 大小写敏感(仅 WINDOW_NAMES 十三档, §08 + D4)"""
    from auto_qb.webui.server.traffic_qb import WINDOW_NAMES

    mgr, client = web_env
    auth = _auth(mgr)
    _enable_qb_traffic(mgr)
    windows = ("1m", "5m", "30m", "3h", "6h", "12h", "24h", "3d", "7d", "30d", "6mo", "1y", "all")
    assert WINDOW_NAMES == windows  # D4 档位映射: 10 -> 13 档(6mo/1y/all 上, 90d 延后不上)
    for p in ("/api/traffic/qb/global", "/api/traffic/qb/torrent/HA", f"/api/traffic/qb/group/{encode_group_key(KEY)}"):
        assert client.get(p, headers=auth, params={"window": "90d"}).status_code == 400, p
        assert client.get(p, headers=auth, params={"window": "24H"}).status_code == 400, p  # 大写不认
        assert client.get(p, headers=auth, params={"window": ""}).status_code == 400, p
        for w in windows:  # 十三档全部放行(1m/5m/30m/3h/6h/12h/24h 对齐 qB 速度图 + 3d/7d/30d + 6mo/1y/all)
            assert client.get(p, headers=auth, params={"window": w}).status_code == 200, (p, w)
    assert client.get("/api/traffic/qb/global", headers=auth).json()["meta"]["window"] == "24h"  # 缺省 24h
    assert client.get("/api/traffic/qb/global", headers=auth, params={
        "window": "30d"
    }).json()["meta"]["window"] == "30d"


def test_api_traffic_qb_global_24h_points_totals_and_stale(web_env, monkeypatch):
    """global 24h 窗(raw 段, 26-11-18-0037 T1b 样本分组契约): 天文件块 -> 样本分组装配
    (k = ceil(窗内预期样本数/500) = 6, 组点 t = 组末样本 ts; n 游程折叠为显式空值点
    {t, dl: None, up: None}) + totals = 组粒度快照差分和(重置逐向 None / 跨断连字节
    承袭在后继样本快照差分里 —— 字节守恒) + 读取竞态降级: 回上一份成功快照标
    stale=true, 不以空态冒充无数据(§08)"""
    from auto_qb.core.traffic_store import V4Block, V4DayCache, V4NullRun, V4Sample, v4_epoch_date_str
    from auto_qb.webui.server import traffic_qb as _tq_meta

    mgr, client = web_env
    auth = _auth(mgr)
    # (T1b)生效间隔 30s(multiplier 15 x main_tick 2.0): 24h 窗内预期样本 2880 -> 分组口径
    # k = ceil(2880/500) = 6(与旧挂钟桶宽 180 = 6 x 30 同值 —— k_init 与旧加宽因子同源),
    # meta.interval_s = 组距标称 = 6 x 30 = 180
    _enable_qb_traffic(mgr, sample_interval_multiplier=15)
    store = _qb_v4(mgr)
    now = int(time.time())
    base = ((now - 7200) // 180) * 180  # 窗内 2h 处的 180s 对齐锚(数据节律 = 180s/记录)
    # 块首记录槽位恰在 base+180, 其后标称 180s 逐槽对齐; 6 个观测样本(base+180..+900 与
    # 断连恢复样本 base+1620)按窗内序号 0..5 -> 恰同属一组(k=6, 组点 t = 组末样本 ts =
    # base+1620); n 游程 3 槽(base+1080/1260/1440)折叠为一个显式空值点(t = floor(首槽 ts))
    # v4 行型: 计数器回落处拆块(与写侧「重置强制关块重立基线」一致), 槽位序列不变
    store.append_records(
        "global",
        v4_epoch_date_str(base + 180),
        (base + 180, 180),
        (
            V4Sample(100, 50, 1000, 500),  # 样本 base+180
            V4Sample(200, 70, 2800, 1400),  # 样本 base+360: delta(1800,900)
            V4Sample(5, 5, 2980, 1580),  # 样本 base+540: delta(180,180)
            V4Sample(300, 90, 3880, 1760),  # 样本 base+720: delta(900,180)
        ),
        (1000, 500),
    )
    store.append_records(
        "global",
        v4_epoch_date_str(base + 180),
        (base + 900, 180),
        (
            V4Sample(10, 10, 2740, 1940),  # 样本 base+900: dl 快照回落(重置 -> 逐向 None); up delta 180
            V4NullRun(3, dt_ms=540000),  # 断连 3 槽: 折叠为显式空值点 @base+1080
            V4Sample(12, 22, 3940, 2120, dt_ms=180000),  # 样本 base+1620: 缝 > 停机洞阈值 -> 速率面断链丢弃
        ),
        (2740, 1940),
    )

    def point_at(body, t):
        return next((p for p in body["points"] if p and p["t"] == t), None)

    def total_at(body, t):
        return next((p for p in body["totals"] if p and p["t"] == t), None)

    r = client.get("/api/traffic/qb/global", headers=auth)
    assert r.status_code == 200
    body = r.json()
    # meta 全量形状(T1b §03: 六键全保留 + schema=2/stride=k 新增, interval_s 转组距标称
    # k x si; P4 server_started_at 一并钉住, 值语义/兼容面由未启用空态用例专测)
    assert body["meta"] == {
        "window": "24h",
        "interval_s": 180,
        "sample_interval_s": 30.0,
        "schema": 2,
        "stride": 6,
        "source": "qb",
        "stale": False,
        "server_started_at": _tq_meta._SERVER_STARTED_AT,
    }
    # (T1b)样本分组点列: 单组(k=6 恰吞全部 6 样本)真值点 + 断连显式空值点, 升序合并;
    # 组速率 = Sigma delta x 1000 / Sigma 覆盖毫秒(dl 2880B/540s -> 5, up 1440B/720s -> 2;
    # 重置/停机洞样本的差分对不进覆盖), 组点 t = 组末样本 ts
    assert len(body["points"]) == 2
    assert point_at(body, base + 1080) == {"t": base + 1080, "dl": None, "up": None}  # n 游程折叠显式空值点(E3)
    assert point_at(body, base + 1620) == {"t": base + 1620, "dl": 5, "up": 2}  # 组均值(非组末样本 ts 处无点)
    # totals = 组粒度快照差分和(逐样本相邻差分按端点所属组求和, 重置/基线缺失贡献 0):
    # dl 1800+180+900 + 0(重置) + 1200(跨断连快照差分) = 4080; up 900+180+180+180+180 = 1620
    # —— 漏采区间字节含在后继样本快照差分里(字节守恒, Sigma(totals) 分组前后恒等)
    assert total_at(body, base + 1080) is None  # 空值点 totals = None
    assert total_at(body, base + 1620) == {"t": base + 1620, "dl": 4080, "up": 1620}

    # 读取竞态降级(§08「最坏返回上一秒快照 + stale」):
    # a) 24h 已有成功响应入 last-good -> 降级回上一份快照(点值不变) + stale=true;
    # b) 30d 从未成功请求过 -> 无历史快照, 降级回现算空态 + stale=true(不冒充"确定无数据")
    def _read_broken():
        def raise_oserror(self, *a, **k):
            raise OSError("simulated read race")

        return raise_oserror

    monkeypatch.setattr(V4DayCache, "read_window", _read_broken())
    stale = client.get("/api/traffic/qb/global", headers=auth).json()
    assert stale["meta"]["stale"] is True
    assert stale["points"] == body["points"] and stale["totals"] == body["totals"]
    monkeypatch.setattr(V4DayCache, "read_agg", _read_broken())
    fresh = client.get("/api/traffic/qb/global", headers=auth, params={"window": "30d"}).json()
    assert fresh["points"] == [] and fresh["totals"] == [] and fresh["meta"]["stale"] is True
    monkeypatch.undo()
    assert client.get("/api/traffic/qb/global", headers=auth).json()["meta"]["stale"] is False  # 恢复后照常


def test_api_traffic_qb_raw_rate_basis_delta_per_w_totals_unchanged(web_env):
    """(26-11-18-0037 T1b; 计划 26-10-07-2127 S2 承袭)raw 5m 短窗 k=1 逐样本点列: 速率 =
    样本差分/覆盖时长(20/10 与 40/20), 瞬时直采值(5xxx-9xxx 垃圾字段)零上图; totals =
    逐样本快照差分(窗首基线缺失 -> 逐向 None); 活尾样本跨盘/尾接缝差分 —— 图尾随最新
    真实样本(head_pending=False 非块首活尾从写侧游标倒推槽位)"""
    from auto_qb.core.traffic_store import LiveTail, V4Sample, v4_epoch_date_str

    mgr, client = web_env
    auth = _auth(mgr)
    _enable_qb_traffic(mgr, sample_interval_multiplier=15)  # main_tick=2.0 -> 15 x 2 = 30s 生效(5m 窗预期 10 样本 -> k=1)
    store = _qb_v4(mgr)
    now = int(time.time())
    b0 = ((now - 240) // 30) * 30  # 5m 窗内, 远离窗首/窗尾边缘
    # (T1b)样本 @b0/30/60/90 -> 点 t = 样本 ts(k=1 逐样本)
    store.append_records(
        "global",
        v4_epoch_date_str(b0),
        (b0, 30),
        (
            V4Sample(7777, 7777, 1000, 500),  # 样本 b0: 窗内首点无基线 -> 0 线(无缝链首, D4 承袭)
            V4Sample(9999, 9999, 1600, 800),  # 样本 b0+30: delta(600,300)/30 -> 20/10
            V4Sample(5555, 5555, 2800, 1400),  # 样本 b0+60: delta(1200,600)/30 -> 40/20
        ),
        (1000, 500),
    )
    _attach_live_tail_host(
        mgr,
        {
            "global":
                LiveTail(
                    block_open=True,
                    head_pending=False,  # 块首已落盘: 活尾记录为非块首, 槽位从游标 projected_ts 倒推
                    start_epoch=b0,
                    interval_s=30,
                    projected_ts=float(b0 + 90),
                    records=(V4Sample(8888, 8888, 3400, 1700), ),  # 样本 @b0+90: delta(600,300)/30 -> 20/10
                    open_run=None,
                )
        },
    )
    body = client.get("/api/traffic/qb/global", headers=auth, params={"window": "5m"}).json()

    def pt(seg, t):
        return next((p for p in body[seg] if p and p["t"] == t), None)

    assert body["meta"]["stale"] is False
    assert body["meta"]["schema"] == 2 and body["meta"]["stride"] == 1
    assert body["meta"]["interval_s"] == 30  # 组距标称 = k x si = 1 x 30
    assert body["meta"]["sample_interval_s"] == 30.0  # F6 只增键: 15 x main_tick 2.0s
    assert pt("points", b0) == {"t": b0, "dl": 0, "up": 0}  # 窗内首样本基线缺失 -> 0 线
    assert pt("points", b0 + 30) == {"t": b0 + 30, "dl": 20, "up": 10}
    assert pt("points", b0 + 60) == {"t": b0 + 60, "dl": 40, "up": 20}
    assert pt("points", b0 + 90) == {"t": b0 + 90, "dl": 20, "up": 10}  # 活尾样本: 跨盘/尾接缝差分
    assert all(p["dl"] is None or p["dl"] < 1000 for p in body["points"])  # 瞬时垃圾值零上图
    # totals 通道(速率变换不动快照链): 窗首基线缺失逐向 None + 逐样本差分(含活尾样本)
    assert pt("totals", b0) == {"t": b0, "dl": None, "up": None}
    assert pt("totals", b0 + 30) == {"t": b0 + 30, "dl": 600, "up": 300}
    assert pt("totals", b0 + 60) == {"t": b0 + 60, "dl": 1200, "up": 600}
    assert pt("totals", b0 + 90) == {"t": b0 + 90, "dl": 600, "up": 300}


def test_api_traffic_qb_raw_live_tail_true_tail_no_hold_clone(web_env, monkeypatch):
    """(26-11-18-0037 T1b 改写, 取代 F4 持有延伸; T1c-2 后 now/max_gap_s 形参面已随
    持有面退役 —— v4_live_tail_slots 复原即纯槽序)raw 段窗活尾合流: 新契约尾组恒真值
    无克隆。响应尾点 = 最新真实样本 ts 的真值(20/10, 瞬时垃圾字段 9999 零上图), 最新
    样本之后无任何点(无持有克隆); totals 尾点 = 真实差分 600/300(非持有面 0 增量)。
    活尾纯内存(不落盘), 磁盘零块 -> 无真空缝, 差分链干净; 端点取时冻结假钟消除窗界
    竞态"""
    from auto_qb.core.traffic_store import LiveTail, V4Sample
    from auto_qb.webui.server import traffic_qb as tq

    mgr, client = web_env
    auth = _auth(mgr)
    _enable_qb_traffic(mgr, sample_interval_multiplier=15)  # main_tick=2.0 -> 30s 生效(5m 窗预期 10 样本 -> k=1)
    _qb_v4(mgr)  # 建 v4 目录(磁盘零块: 全部观测走活尾)
    now = int(time.time())
    _freeze_traffic_endpoint_clock(monkeypatch, now)  # 端点取时单点冻结(用例与请求同一 now)
    projected = (now // 30) * 30 - 30  # 末样本槽位(距 now 30..59s, 三槽恒在窗内)
    _attach_live_tail_host(
        mgr,
        {
            "global":
                LiveTail(
                    block_open=True,
                    head_pending=False,
                    start_epoch=projected - 60,
                    interval_s=30,
                    projected_ts=float(projected),
                    records=(
                        V4Sample(9999, 9999, 1600, 800),  # 样本 projected-60: 链首 -> 0 线
                        V4Sample(9999, 9999, 2200, 1100),  # 样本 projected-30: delta(600,300)/30 -> 20/10
                        V4Sample(9999, 9999, 2800, 1400),  # 样本 projected: delta(600,300)/30 -> 20/10
                    ),
                    open_run=None,
                )
        },
    )
    # 接线钉: 记录端点向 v4_live_tail_slots 的传参形态(持有延伸 = 传 now; 新契约不传)。
    # 位置实参形态一并钉死(26-11-18-0037 评审 #5): calls 记 (a, kw) 二元组 —— 只记 kw
    # 时「位置实参传 now」的变异下 kw 为空、断言照绿(变异存活), 故 a == () 亦断
    calls = []
    real_slots = tq.v4_live_tail_slots

    def _spy(tail, *a, **kw):
        calls.append((a, kw))
        return real_slots(tail, *a, **kw)

    monkeypatch.setattr(tq, "v4_live_tail_slots", _spy)
    body = client.get("/api/traffic/qb/global", headers=auth, params={"window": "5m"}).json()
    assert calls and all(a == () and "now" not in kw and "max_gap_s" not in kw for a, kw in calls)  # 不传 now = 无持有延伸
    assert body["meta"]["schema"] == 2 and body["meta"]["stride"] == 1
    assert body["points"][-1] == {"t": projected, "dl": 20, "up": 10}  # 尾点恒真值(最新真实样本)
    assert all(p["t"] <= projected for p in body["points"])  # 最新样本之后无点(无持有克隆)
    assert body["totals"][-1] == {"t": projected, "dl": 600, "up": 300}  # 真实差分, 非 0 增量
    assert all(p["dl"] is None or p["dl"] < 1000 for p in body["points"])  # 瞬时垃圾零上图


def test_api_traffic_qb_group_raw_live_tail_true_tail_no_hold_clone(web_env, monkeypatch):
    """(26-11-18-0037 T1b 改写)组端点 raw 段成员循环的活尾接线钉(与 global 用例同构):
    成员活尾挂在 torrent:HA(键 = TORRENT_KEY_PREFIX + 成员 hash), 活尾槽复原即纯槽序
    (持有延伸形参面已随持有面退役)—— 组响应尾点 = Σ 成员最新真实样本真值(仅 HA 有活尾, HB 无行
    缺位点不进并集 -> 20/10), 最新样本之后无任何点(无持有克隆); totals 尾点 = 真实
    差分。组空态判据计入活尾(member_has_tail), 变异加回 now=/max_gap_s= 实参即红"""
    from auto_qb.core.traffic_store import LiveTail, V4Sample
    from auto_qb.webui.server import traffic_qb as tq

    mgr, client = web_env
    auth = _auth(mgr)
    _enable_qb_traffic(mgr, sample_interval_multiplier=15)  # 30s 生效(5m 窗预期 10 样本 -> k=1)
    _qb_v4(mgr)  # 磁盘零块: 观测面全部走成员活尾
    now = int(time.time())
    _freeze_traffic_endpoint_clock(monkeypatch, now)  # 端点取时单点冻结(用例与请求同一 now)
    projected = (now // 30) * 30 - 30  # 末样本槽位(距 now 30..59s, 三槽恒在窗内)
    _attach_live_tail_host(
        mgr,
        {
            "torrent:HA":
                LiveTail(
                    block_open=True,
                    head_pending=False,
                    start_epoch=projected - 60,
                    interval_s=30,
                    projected_ts=float(projected),
                    records=(
                        V4Sample(9999, 9999, 1600, 800),  # 样本 projected-60: 链首 -> 0 线
                        V4Sample(9999, 9999, 2200, 1100),  # 样本 projected-30: delta(600,300)/30 -> 20/10
                        V4Sample(9999, 9999, 2800, 1400),  # 样本 projected: delta(600,300)/30 -> 20/10
                    ),
                    open_run=None,
                )
        },
    )
    calls = []  # 接线钉记 (a, kw) 二元组(位置实参形态一并钉死, 同 global 用例评审 #5)
    real_slots = tq.v4_live_tail_slots

    def _spy(tail, *a, **kw):
        calls.append((a, kw))
        return real_slots(tail, *a, **kw)

    monkeypatch.setattr(tq, "v4_live_tail_slots", _spy)
    body = client.get(f"/api/traffic/qb/group/{encode_group_key(KEY)}", headers=auth, params={"window": "5m"}).json()
    assert calls and all(a == () and "now" not in kw and "max_gap_s" not in kw for a, kw in calls)  # 不传 now = 无持有延伸
    assert body["meta"]["schema"] == 2 and body["meta"]["stride"] == 1
    assert body["points"][-1] == {"t": projected, "dl": 20, "up": 10}  # 尾点恒真值(Σ 成员真实样本)
    assert all(p["t"] <= projected for p in body["points"])  # 最新样本之后无点(无持有克隆)
    assert body["totals"][-1] == {"t": projected, "dl": 600, "up": 300}  # 真实差分, 非 0 增量
    assert all(p["dl"] is None or p["dl"] < 1000 for p in body["points"])  # 瞬时垃圾零上图


def test_api_traffic_qb_raw_seed_extension_window_start_baseline(web_env):
    """(26-11-18-0037 T1b; 计划 26-10-07-2127 S2/D3 承袭)窗首种子 D3: 读窗起点 = 装配
    消费下界 t0 - si - 回看界, 窗外前缀只作差分基线不产组点 —— 窗内首个样本对窗外基线
    的差分落在窗首点(rate = delta/覆盖 = 20/10, 非 0 线非瞬时值), 瞬时垃圾值零上图;
    totals 窗首组含窗外种子差分(600/300 —— 字节守恒: 种子基线到窗首样本的字节入账);
    窗外样本不外发。数据跨窗首等距等差铺放(逐样本 delta 恒 600/300), 对窗首 floor 对齐
    位置与端点取 now 的 ±1s 秒漂不敏感(断言值恒定)"""
    from auto_qb.core.traffic_store import V4Sample, v4_epoch_date_str

    mgr, client = web_env
    auth = _auth(mgr)
    _enable_qb_traffic(mgr, sample_interval_multiplier=15)  # main_tick=2.0 -> 15 x 2 = 30s 生效(5m 窗预期 10 样本 -> k=1)
    store = _qb_v4(mgr)
    now = int(time.time())
    first = (now - 300) - ((now - 300) % 30)  # 5m 窗首 floor 对齐位置
    totals = ((1000, 500), (1600, 800), (2200, 1100), (2800, 1400), (3400, 1700))
    # 种子 = 窗前样本 @first-30(读窗消费下界覆盖区): 窗内首样本的差分基线(D3, 装配内建
    # —— 窗外前缀只入差分链不计组序号)
    store.append_records(
        "global",
        v4_epoch_date_str(first - 30),
        (first - 30, 30),
        tuple(V4Sample(9999, 9999, dl, up) for dl, up in ((400, 200), ) + totals),  # 瞬时字段全垃圾, 只看差分
        (400, 200),
    )
    body = client.get("/api/traffic/qb/global", headers=auth, params={"window": "5m"}).json()
    pts = [p for p in body["points"] if p["dl"] is not None]
    assert len(pts) >= 2 and body["meta"]["stale"] is False
    assert body["meta"]["schema"] == 2 and body["meta"]["stride"] == 1
    p0 = pts[0]
    assert p0["t"] in (first, first + 30)  # 端点取 now 与用例 ±1s: 窗内首样本至多移一格
    assert all(p["dl"] == 20 and p["up"] == 10 for p in pts)  # 逐样本 delta(600,300)/30 —— 种子给窗首样本基线
    tots = [p for p in body["totals"] if p is not None]
    assert tots[0] == {"t": p0["t"], "dl": 600, "up": 300}  # D3 种子的 totals 面: 窗首组含窗外种子差分(旧面为 None)
    assert tots[1] == {"t": pts[1]["t"], "dl": 600, "up": 300}  # 逐样本差分照旧
    assert len(tots) == len(pts)  # totals 与 points 等长同构


def test_api_traffic_qb_raw_seed_vacuum_chain_break_and_recover(web_env):
    """(26-11-18-0037 T1b; 计划 26-10-07-2127 S2/D3 承袭)种子跨真空: 窗首前种子块与窗内
    恢复块之间程序停机(缝恰 60s = 重启缝)—— 装配真空判定出断连面(marked), 恢复首样本
    按真实跨度摊配回收(覆盖份额口径: step 9600/4800 x cov 30s // span 90s = 3200/1600 ->
    rate 107/53, 离线期字节不再单样本放大; 误接旧值 = 9600/30 = 320 可判红), 次样本起
    基线恢复 delta/覆盖; totals = 组粒度快照差分和 —— 恢复首样本对种子基线的完整快照
    差分(离线字节含在后继样本快照差分里, 9600/4800 入账; 旧面「离线字节不进 totals」
    的空洞口径随组粒度差分和退役 —— 字节守恒承袭 T1a 契约)"""
    from auto_qb.core.traffic_store import V4Sample, v4_epoch_date_str

    mgr, client = web_env
    auth = _auth(mgr)
    _enable_qb_traffic(mgr, sample_interval_multiplier=15)  # main_tick=2.0 -> 15 x 2 = 30s 生效(5m 窗预期 10 样本 -> k=1)
    store = _qb_v4(mgr)
    now = int(time.time())
    first = (now - 300) - ((now - 300) % 30)
    store.append_records(  # 窗前种子块: 单记录 @first-30(消费下界覆盖区, 只作差分基线不产组点)
        "global", v4_epoch_date_str(first - 30), (first - 30, 30), (V4Sample(1111, 1111, 1000, 500), ), (1000, 500)
    )
    store.append_records(  # 停机后恢复块(未观测恰 60s = 重启缝): 首记录 totals 已含离线期字节 9000/4500
        "global",
        v4_epoch_date_str(first + 60),
        (first + 60, 30),
        (
            V4Sample(9999, 9999, 10600, 5300),  # 样本 @first+60: 缝后恢复点
            V4Sample(7777, 7777, 11200, 5600),  # 样本 first+90: delta(600,300)/30 -> 20/10(基线恢复)
            V4Sample(5555, 5555, 11800, 5900),  # 样本 first+120: delta(600,300)/30 -> 20/10
        ),
        (10600, 5300),
    )
    body = client.get("/api/traffic/qb/global", headers=auth, params={"window": "5m"}).json()

    def pt(seg, t):
        return next((p for p in body[seg] if p and p["t"] == t), None)

    assert body["meta"]["stale"] is False
    assert body["meta"]["schema"] == 2 and body["meta"]["stride"] == 1
    assert pt("points", first) is None and pt("points", first + 30) is None  # 真空段窗内无样本 -> 无点(标记 t 在窗外不入列)
    assert pt("points", first + 60) == {"t": first + 60, "dl": 107, "up": 53}  # 重启缝按真实跨度摊配回收(误接旧值 320)
    assert pt("points", first + 90) == {"t": first + 90, "dl": 20, "up": 10}  # 基线恢复
    assert pt("points", first + 120) == {"t": first + 120, "dl": 20, "up": 10}
    assert all(p["dl"] is None or p["dl"] < 1000 for p in body["points"])  # 瞬时垃圾值零上图
    assert pt("totals", first + 60) == {"t": first + 60, "dl": 9600, "up": 4800}  # 离线字节入账(快照差分, 字节守恒)
    assert pt("totals", first + 90) == {"t": first + 90, "dl": 600, "up": 300}
    assert all(p is None or (p["dl"] in (None, 600, 9600) and p["up"] in (None, 300, 4800)) for p in body["totals"])


def test_api_traffic_qb_raw_seed_vacuum_null_1s_edge_band(web_env, monkeypatch):
    """(26-11-18-0037 T1b; issue 26-10-08-0141 / 26-10-16-0954 承袭)窗首种子 1 秒边界带:
    停机时刻落在 (seed_t0-1, seed_t0) 时真空标记 t = int(prev_chain_end) 取整后 = seed_t0-1
    恰落窗外 —— 标记不入列(窗内无空值点)但断连面存活(marked), 恢复首样本按真实跨度
    摊配回收(覆盖份额 9000/4500 x cov 30s // span 60.5s -> rate 149/74, 误接旧值 300 可
    判红), 离线字节不单样本放大; totals = 组粒度快照差分和: 恢复首样本对种子基线的完整
    快照差分(9000/4500 入账 —— 字节守恒, 旧面「离线字节不进 totals」口径随组粒度差分和
    退役)。时钟钉死(1 秒带需确定性 now; 端点 _grid 走 traffic_qb.SYSTEM_CLOCK 单点,
    patch 模块内单点名请求时现读)"""
    from auto_qb.core.traffic_store import V4Sample, v4_epoch_date_str
    from auto_qb.webui.server import traffic_qb as tq

    mgr, client = web_env
    auth = _auth(mgr)
    _enable_qb_traffic(mgr, sample_interval_multiplier=15)  # main_tick=2.0 -> 15 x 2 = 30s 生效(5m 窗预期 10 样本 -> k=1)
    store = _qb_v4(mgr)
    fixed = 1_800_000_000.0  # 30 的整倍 -> 5m 窗几何确定(确定性)

    monkeypatch.setattr(tq, "SYSTEM_CLOCK", FakeClock(start=fixed))
    g_t0 = int(fixed) - 300  # 5m 窗窗首
    seed_t0 = g_t0 - 30  # 种子块锚(读窗消费下界 t0-si-回看界 远超之, 覆盖无虞)
    store.append_records(  # 种子块: 末槽恰落 (seed_t0-1, seed_t0) 的 1 秒带(首记录 @seed_t0-30, 次记录 +29.5s)
        "global",
        v4_epoch_date_str(seed_t0 - 30),
        (seed_t0 - 30, 30),
        (V4Sample(1111, 1111, 1000, 500), V4Sample(2222, 2222, 1600, 800, dt_ms=29500)),
        (1000, 500),
    )
    store.append_records(  # 停机后恢复块(真空): 首记录 totals 已含离线期字节 9000/4500
        "global",
        v4_epoch_date_str(g_t0 + 30),
        (g_t0 + 30, 30),
        (V4Sample(9999, 9999, 10600, 5300), V4Sample(8888, 8888, 11200, 5600)),
        (10600, 5300),
    )
    body = client.get("/api/traffic/qb/global", headers=auth, params={"window": "5m"}).json()

    def pt(seg, t):
        return next((p for p in body[seg] if p and p["t"] == t), None)

    assert body["meta"]["stale"] is False
    assert body["meta"]["schema"] == 2 and body["meta"]["stride"] == 1
    assert body["meta"]["interval_s"] == 30  # 组距标称 = k x si
    # 恢复样本 @g_t0+30: 摊配 = step 9000/4500 x cov 30s // span 60.5s = 4462/2231 ->
    # rate = 148.7 -> 149 / 74.4 -> 74(误接旧值 300 可判红)
    assert pt("points", g_t0 + 30) == {"t": g_t0 + 30, "dl": 149, "up": 74}
    assert pt("points", g_t0 + 60) == {"t": g_t0 + 60, "dl": 20, "up": 10}  # 次样本基线恢复 delta/覆盖
    assert all(p["dl"] is None or p["dl"] < 1000 for p in body["points"])  # 离线字节不单样本放大
    assert pt("totals", g_t0 + 30) == {"t": g_t0 + 30, "dl": 9000, "up": 4500}  # 离线字节入账(快照差分, 字节守恒)
    assert pt("totals", g_t0 + 60) == {"t": g_t0 + 60, "dl": 600, "up": 300}


def test_api_traffic_qb_global_30d_hour_segment(web_env):
    """global 30d 窗(agg hour 段): agg.dat hour 行直映栅格桶(epoch 即桶键, 桶内不再
    聚合), meta.interval_s=3600; 相邻 hour 桶快照差分"""
    from auto_qb.core.traffic_store import AggRow

    mgr, client = web_env
    auth = _auth(mgr)
    _enable_qb_traffic(mgr)
    store = _qb_v4(mgr)
    now = int(time.time())
    h = ((now - 172800) // 3600) * 3600  # 窗内 2 天前的小时桶
    store.append_agg_rows(
        "global", (
            AggRow("hour", h, 200, 400, 60, 100, 1000, 400, 3600),
            AggRow("hour", h + 3600, 100, 200, 30, 60, 1500, 700, 3600),
        )
    )
    body = client.get("/api/traffic/qb/global", headers=auth, params={"window": "30d"}).json()
    assert body["meta"]["interval_s"] == 3600 and body["meta"]["window"] == "30d"
    assert len(body["points"]) == 721  # 30d 窗 720 桶 + 1 进行中桶(26-11-14-1313 F3 floor+1: hour 段恒整倍, n 恒 721)
    p = next(p for p in body["points"] if p and p["t"] == h)
    assert p == {"t": h, "dl": 200, "up": 60}  # hour 行 avg(桶内不再聚合)
    total = next(p for p in body["totals"] if p and p["t"] == h)
    assert total == {"t": h, "dl": None, "up": None}  # 窗内首个有观测小时桶: 基线缺失
    total2 = next(p for p in body["totals"] if p and p["t"] == h + 3600)
    assert total2 == {"t": h + 3600, "dl": 500, "up": 300}  # 相邻桶快照差分


def test_api_traffic_qb_global_6mo_1y_day_segment(web_env):
    """6mo/1y 窗(agg day 段, D4 沿用): day 行直映本地日界桶, 滚动窗切片正确 ——
    300 天前的行 1y 可见 / 6mo 不可见; 缺日 = null 桶(totals 断链基线缺失);
    meta.interval_s=86400"""
    from datetime import datetime, timedelta

    from auto_qb.core.traffic_store import AggRow

    mgr, client = web_env
    auth = _auth(mgr)
    _enable_qb_traffic(mgr)
    store = _qb_v4(mgr)
    now = int(time.time())
    today = datetime.fromtimestamp(now).date()

    def midnight(days_ago):
        d = today - timedelta(days=days_ago)
        return int(datetime(d.year, d.month, d.day).timestamp())

    d1, d2, d_old = midnight(5), midnight(4), midnight(300)
    store.append_agg_rows(
        "global", (
            AggRow("day", d_old, 10, 10, 1, 1, 100, 50, 86400),
            AggRow("day", d1, 100, 200, 50, 60, 1000, 500, 86400),
            AggRow("day", d2, 60, 90, 40, 50, 1500, 800, 86400),
        )
    )
    body6 = client.get("/api/traffic/qb/global", headers=auth, params={"window": "6mo"}).json()
    assert body6["meta"]["window"] == "6mo" and body6["meta"]["interval_s"] == 86400
    assert 182 <= len(body6["points"]) <= 184  # 滚动窗 182d + 首尾日界
    assert next((p for p in body6["points"] if p and p["t"] == d_old), None) is None  # 300 天前滑出 6mo
    assert next(p for p in body6["points"] if p and p["t"] == d1) == {"t": d1, "dl": 100, "up": 50}
    assert next(p for p in body6["points"] if p and p["t"] == d2) == {"t": d2, "dl": 60, "up": 40}
    total1 = next(p for p in body6["totals"] if p and p["t"] == d1)
    assert total1 == {"t": d1, "dl": None, "up": None}  # 前一日无行 = null 桶: 断链基线缺失
    total2 = next(p for p in body6["totals"] if p and p["t"] == d2)
    assert total2 == {"t": d2, "dl": 500, "up": 300}  # 相邻日桶快照差分
    body1 = client.get("/api/traffic/qb/global", headers=auth, params={"window": "1y"}).json()
    assert body1["meta"]["window"] == "1y" and body1["meta"]["interval_s"] == 86400
    assert 365 <= len(body1["points"]) <= 367
    assert next(p for p in body1["points"] if p and p["t"] == d_old) == {"t": d_old, "dl": 10, "up": 1}


def test_api_traffic_qb_global_all_month_segment(web_env):
    """all 窗(agg month 段, D4 沿用): month 行数据面逐月铺格(缺失月 = null 桶, 折线
    断开), 相邻月桶快照差分; meta.interval_s = 标称月长(真实月长按行间隔, 点位真值在
    points[].t —— 前端按真值落点)"""
    from auto_qb.core.traffic_store import AggRow, v4_month_epoch

    mgr, client = web_env
    auth = _auth(mgr)
    _enable_qb_traffic(mgr)
    store = _qb_v4(mgr)
    now = int(time.time())
    m0 = v4_month_epoch(now)  # 本自然月(完结月行; 当月行未封不写, 用例直接造历史月)
    m1 = v4_month_epoch(m0 - 86400)  # 上月
    m4 = v4_month_epoch(v4_month_epoch(v4_month_epoch(m1 - 86400) - 86400) - 86400)  # 再往前 3 个自然月
    store.append_agg_rows(
        "global", (
            AggRow("month", m4, 10, 10, 1, 1, 100, 50, 3 * 86400),
            AggRow("month", m1, 100, 200, 50, 60, 1000, 500, 3 * 86400),
            AggRow("month", m0, 60, 90, 40, 50, 1500, 800, 3 * 86400),
        )
    )
    body = client.get("/api/traffic/qb/global", headers=auth, params={"window": "all"}).json()
    assert body["meta"]["window"] == "all" and body["meta"]["interval_s"] == 30 * 86400
    assert len(body["points"]) == 5  # m4..m0 逐月铺格
    assert body["points"][0] == {"t": m4, "dl": 10, "up": 1}
    assert body["points"][1] is None and body["points"][2] is None  # 缺失月 = null 桶
    assert body["points"][3] == {"t": m1, "dl": 100, "up": 50}
    assert body["points"][4] == {"t": m0, "dl": 60, "up": 40}
    assert body["totals"][0] == {"t": m4, "dl": None, "up": None}  # 首桶基线缺失
    assert body["totals"][3] == {"t": m1, "dl": None, "up": None}  # 与 m4 隔缺失月: 断链
    assert body["totals"][4] == {"t": m0, "dl": 500, "up": 300}  # 相邻月快照差分
    # 空数据面: 全 null -> 空态归一(points: [])
    empty = client.get("/api/traffic/qb/torrent/ZZ", headers=auth, params={"window": "all"}).json()
    assert empty["points"] == [] and empty["meta"]["window"] == "all" and empty["meta"]["interval_s"] == 30 * 86400


def test_api_traffic_qb_torrent_endpoint(web_env):
    """单种端点: 正常取数 / 非法哈希 400 / 未知哈希空态; 数据挂 infohash ——
    不在当前快照的冻结种子历史仍可查"""
    from auto_qb.core.traffic_store import V4Sample, v4_epoch_date_str

    mgr, client = web_env
    auth = _auth(mgr)
    _enable_qb_traffic(mgr, sample_interval_multiplier=15)  # 生效间隔 30s
    store = _qb_v4(mgr)
    now = int(time.time())
    base = ((now - 3600) // 180) * 180
    # (T1b)24h 窗预期 2880 样本 -> k_init=6, 但窗内仅 1 样本 -> k 上限 = 样本数 = 1:
    # 点 t = 样本 ts, 值 = 0 线(无缝链首)
    store.append_records(
        "torrent:HA", v4_epoch_date_str(base + 180), (base + 180, 180), (V4Sample(500, 100, 5000, 1000), ),
        (5000, 1000)
    )
    body = client.get("/api/traffic/qb/torrent/HA", headers=auth).json()
    assert body["meta"]["source"] == "qb" and body["meta"]["stale"] is False
    assert body["meta"]["stride"] == 1  # k 上限 = 窗内实际样本数(§03 分组口径)
    p = next(p for p in body["points"] if p and p["t"] == base + 180)
    assert p == {"t": base + 180, "dl": 0, "up": 0}  # (T1b)单样本 -> 点 t = 样本 ts: 无基线 0 线(瞬时值不上图)
    # 非法哈希(路径不安全字符 -> 存储层 v4_series_dir ValueError 转译) -> 400 + detail
    # 契约「种子哈希非法」(torrent_detail.py docstring「哈希不合法 400」的守阵, issue
    # 26-11-07-0536 R4#37); 合法字符口径 = 文件名安全集(非 40/64 位 hex 也放行, ZZ 即此形)
    # -> 未知哈希(合法字符, 无文件) -> 空态
    for bad in ("HA.X", "HA,X"):
        r = client.get(f"/api/traffic/qb/torrent/{bad}", headers=auth)
        assert r.status_code == 400, bad
        assert "种子哈希非法" in r.json()["detail"], bad
    assert client.get("/api/traffic/qb/torrent/ZZ", headers=auth).json()["points"] == []
    # 删种冻结(hash 已不在 by_hash 快照)后历史仍可查: 数据以 v4 天文件为准, 不以快照存在性裁决
    assert "HA" not in mgr.store.by_hash
    body2 = client.get("/api/traffic/qb/torrent/HA", headers=auth).json()
    assert any(p2 and p2["t"] == base + 180 for p2 in body2["points"])


def test_api_traffic_qb_torrent_1y_single_agg_cold_read(web_env, monkeypatch):
    """年视图单 agg 文件冷读(§05.3 验收): 1y 窗恰好 1 次 qb-traffic-v4 open(agg.dat,
    天文件零读取); 再查(mtime/size 键控缓存命中)零新 open"""
    from datetime import datetime, timedelta

    from auto_qb.core.traffic_store import AggRow

    mgr, client = web_env
    auth = _auth(mgr)
    _enable_qb_traffic(mgr)
    store = _qb_v4(mgr)
    now = int(time.time())
    today = datetime.fromtimestamp(now).date()

    def midnight(days_ago):
        d = today - timedelta(days=days_ago)
        return int(datetime(d.year, d.month, d.day).timestamp())

    d1, d2 = midnight(360), midnight(359)
    store.append_agg_rows(
        "torrent:HA", (
            AggRow("day", d1, 10, 10, 1, 1, 100, 50, 86400),
            AggRow("day", d2, 20, 20, 2, 2, 200, 100, 86400),
        )
    )
    opened = _qb_open_spy(monkeypatch)
    body = client.get("/api/traffic/qb/torrent/HA", headers=auth, params={"window": "1y"}).json()
    assert len(_v4_opens(opened)) == 1  # 单 agg 文件冷读(360 天前的 day 行无需任何天文件)
    monkeypatch.undo()
    assert next(p for p in body["points"] if p and p["t"] == d1) == {"t": d1, "dl": 10, "up": 1}
    opened2 = _qb_open_spy(monkeypatch)
    client.get("/api/traffic/qb/torrent/HA", headers=auth, params={"window": "1y"})
    assert _v4_opens(opened2) == []  # 缓存命中零 open
    monkeypatch.undo()


@pytest.mark.parametrize("frozen_offset", [None, *_FROZEN_OFFSETS])
def test_api_traffic_qb_global_24h_reads_only_involved_day_files(web_env, monkeypatch, frozen_offset):
    """24h 窗端点面回归(§05.2; 26-11-18-0037 T1b 读窗改判): 只开装配消费下界
    t0 - si - 回看界 以来的涉及日期天文件(常态 3 个, t0 相位近日界边角至多 4 个),
    更早日期/agg.dat 零 open。三档时钟: 真钟(钉在本用例入口时刻)+ 假钟本地 00:05(每天头
    10 分钟窗口, issue 26-10-20-0024)+ 假钟本地 00:00:15(当日首记录未入窗窗口, 2026-10-22
    跨日窗口抖动)"""
    from datetime import datetime, timedelta

    from auto_qb.core.traffic_grid import _V4_SEAM_LOOKBACK_S, build_grid as tg_build_grid
    from auto_qb.core.traffic_store import V4Sample, v4_day_epoch, v4_epoch_date_str, v4_window_dates

    # 用例与服务端同读一个钉死时刻(端点 _grid 请求时现读), 钉一次双边生效:
    # - 真钟档 = 钉在本用例入口时刻。窗口位置仍是现网形状(now 在什么时刻, 窗就在什么位置),
    #   只是不再让用例取的 now 与服务端收边的 now 横跨本地零点(2026-10-22 跨日窗口抖动);
    # - 假钟档 = 钉当日 00:05 / 00:00:15 两个常驻守阵位(_FROZEN_OFFSETS 注释)
    # S3 monkeypatch 收敛: 不再进程级 patch stdlib time.time, 改 patch 端点取时单点
    # traffic_qb.SYSTEM_CLOCK(请求处理叶子经它现读, 与用例共用同一 _pinned 常量)。
    from auto_qb.webui.server import traffic_qb as tq

    _anchor = time.time()
    _pinned = _anchor if frozen_offset is None else v4_day_epoch(_anchor) + frozen_offset
    monkeypatch.setattr(tq, "SYSTEM_CLOCK", FakeClock(start=_pinned))
    mgr, client = web_env
    auth = _auth(mgr)
    _enable_qb_traffic(mgr, sample_interval_multiplier=15)  # 生效间隔 30s(与端点 _grid 同参镜像)
    store = _qb_v4(mgr)
    now = int(_pinned)
    # base 恒取本地当日 00:00(30 对齐): 它必在 24h 窗内(窗尾是 now, 当日总在窗里)。
    # 旧写法 ((now - 600) // 30) * 30 在每天 00:00-00:10 会把 base 甩到前一日, 与
    # involved[0] 撞进同一天, 长洞不成立(判 0) —— 0024 修复口径承袭
    base = v4_day_epoch(now)
    _mirror = tg_build_grid("24h", now, 30.0)  # 与端点 _grid 同参(生效间隔 30s)
    # (T1b)镜像端点读窗 = 装配消费下界 t0 - si - 回看界(_assemble_series_raw.read_lo 同式)
    involved = sorted(v4_window_dates(_mirror.t0 - 30.0 - _V4_SEAM_LOOKBACK_S, _mirror.t1))
    older_date = (datetime.strptime(involved[0], "%Y-%m-%d") - timedelta(days=1)).strftime("%Y-%m-%d")
    # 造数: 现行记录落 base 所在日期; 其余涉及日期与窗外更早日期各放一块(读侧按消费下界过滤)。
    # 块料 totals 一致(100, 50): 跨日链进差分链时快照差分恒 0, 断言值不随对齐漂移
    for d in involved + [older_date]:
        if d == v4_epoch_date_str(base + 30):
            store.append_records("global", d, (base + 30, 30), (V4Sample(7, 7, 100, 50), ), (100, 50))
        else:
            ts = int(datetime.strptime(d, "%Y-%m-%d").timestamp()) + 30
            store.append_records("global", d, (ts, 30), (V4Sample(1, 1, 100, 50), ), (100, 50))
    opened = _qb_open_spy(monkeypatch)
    body = client.get("/api/traffic/qb/global", headers=auth).json()
    monkeypatch.undo()
    dat_opens = sorted(os.path.basename(p) for p in _v4_opens(opened))
    assert dat_opens == sorted(d + ".dat" for d in involved)  # 只开消费下界以来涉及日期, 更早日期/agg.dat 不触
    assert 3 <= len(involved) <= 4  # 常态恰 3(回看界跨 1 日); t0 相位 < si 时 t0-si-回看界再退 1 日 -> 4
    # 当日样本点期望按几何分档(窗尾 t1 = now, 当日首记录槽 base+30 的入窗条件 = base+30 < t1):
    # - now > base+30: 首记录在窗内, 与昨日块相隔约 24h -> 跨日长洞(> 停机洞阈值)断链未知
    #   -> 显式空值点 {dl: None, up: None}(26-11-18-0037 E3: 缺口带 t);
    # - now <= base+30(00:00:00-00:00:30 窗口): 当日首记录还没到窗尾 -> 该样本不消费 ->
    #   当日无点(生产正确形态: 那天尚未采样)
    entry = next((p for p in body["points"] if p and p["t"] == base + 30), None)
    if now <= base + 30:
        assert entry is None, "当日首记录未入窗时当日样本点应缺位"
    else:
        assert entry == {"t": base + 30, "dl": None, "up": None}  # 跨日长洞: 断链未知 -> 显式空值点


def test_api_traffic_qb_group_endpoint(web_env, monkeypatch):
    """分组端点读侧现算(26-11-18-0037 T1b 样本分组契约; E6 组图 Σ): 成员逐一过样本分组
    装配(同 tick 采样逐成员点列同构), Σ 按 t 合并 —— 全员空闲(z 覆盖)0 线 / 成员重置
    贡献 0 / 无行成员缺位点不进并集(按 0 计) / 停机段链自然终止无点(显式空值点只来自
    n 游程/块间真空)—— 「借 global 判 null」退役: 全程零全局系列文件读取 / 成员历史
    回溯可见 / 解析不到成员空态 / 畸形 key 400 / E6 字节守恒: Sigma(组 totals) =
    Sigma(成员系列 totals)"""
    from auto_qb.core.traffic_store import V4Sample, V4ZeroRun, v4_epoch_date_str

    mgr, client = web_env
    auth = _auth(mgr)
    # (T1b)窗口显式 5m + 生效间隔 30s: 预期 10 样本 -> k=1 逐样本, 点 t = 样本 ts
    # (旧面桶宽 30 下样本落格 bX+30, 新契约点 t 恰同值 —— 断言键逐字不变)
    _enable_qb_traffic(mgr, sample_interval_multiplier=15)
    store = _qb_v4(mgr)
    now = int(time.time())
    base = ((now - 240) // 30) * 30  # 5m 窗内(远离窗首/尾)
    b0, b1, b2, b3, b4, b5 = (base + i * 30 for i in range(6))
    # HA: 样本 @b1..b3(b0+30..b0+90) + 样本 @b4 r 行 + @b5 z 覆盖(空闲观测, 快照恒定)
    #     —— b5 之后无任何块 = 停机(b5+30 之后链自然终止, 无点)
    # v4 行型: 计数器回落处拆块(与写侧「重置强制关块重立基线」一致), 槽位序列不变
    store.append_records(
        "torrent:HA",
        v4_epoch_date_str(b0 + 30),
        (b0 + 30, 30),
        (
            V4Sample(100, 10, 1000, 0),  # 样本 b1
            V4Sample(0, 0, 2000, 0),  # 样本 b2
        ),
        (1000, 0),
    )
    store.append_records(
        "torrent:HA",
        v4_epoch_date_str(b0 + 30),
        (b2 + 30, 30),
        (
            V4Sample(10, 5, 500, 0),  # 样本 b3: 快照回落(重置, 新块立基线)
            V4Sample(10, 5, 600, 0),  # 样本 b4
            V4ZeroRun(1, 600, 0),  # 样本 b5: 空闲 z 观测
        ),
        (500, 0),
    )
    # HB: b1 就有数据(200, 快照 100) —— b1 的行在其"入组前", 回溯同样可见; b2/b3 连续产点
    store.append_records(
        "torrent:HB",
        v4_epoch_date_str(b0 + 30),
        (b0 + 30, 30),
        (
            V4Sample(200, 20, 100, 0),  # 样本 b1
            V4Sample(0, 0, 300, 0),  # 样本 b2
            V4Sample(30, 3, 400, 0),  # 样本 b3
        ),
        (100, 0),
    )
    enc = encode_group_key(KEY)
    opened = _qb_open_spy(monkeypatch)
    body = client.get(f"/api/traffic/qb/group/{enc}", headers=auth, params={"window": "5m"}).json()
    monkeypatch.undo()
    # 组端点无 global 依赖: 请求全程零 qb-traffic-v4/global/ 读取(本用例根本未造全局数据)
    assert not [p for p in _v4_opens(opened) if "/global/" in p]

    def pt(seg, t):
        return next((p for p in body[seg] if p and p["t"] == t), None)

    assert body["meta"]["source"] == "qb" and body["meta"]["stale"] is False
    assert body["meta"]["schema"] == 2 and body["meta"]["stride"] == 1 and body["meta"]["interval_s"] == 30
    # (T1b)组 Σ 按 t 合并: 成员点列同构(t = 样本 ts), 旧面断言值逐字承袭
    assert pt("points", b1) == {"t": b1, "dl": 0, "up": 0}  # 双成员窗首样本基线缺失 -> 0 线(回溯可见性不变)
    assert pt("points", b2) == {"t": b2, "dl": 40, "up": 0}  # Σ 速率: HA delta(1000)/30=33 + HB delta(200)/30=7
    assert pt("points", b3) == {"t": b3, "dl": 3, "up": 0}  # HA 重置 0 线(0) + HB delta(100)/30=3
    assert pt("points", b4) == {"t": b4, "dl": 3, "up": 0}  # HA delta(100)/30=3, HB 缺位点按 0 计
    assert pt("points", b5) == {"t": b5, "dl": 0, "up": 0}  # HA z 覆盖空闲观测 -> 0 线(非 null)
    assert pt("points", b5 + 30) is None  # 停机段链自然终止(无样本无真空标记)-> 无点, 不借 global
    assert pt("totals", b1) == {"t": b1, "dl": 0, "up": 0}  # 双成员窗内基线缺失 -> 0(不出洞)
    assert pt("totals", b2) == {"t": b2, "dl": 1200, "up": 0}  # HA +1000, HB +200
    assert pt("totals", b3) == {"t": b3, "dl": 100, "up": 0}  # HA 重置贡献 0(不是 -1500), HB +100
    assert pt("totals", b4) == {"t": b4, "dl": 100, "up": 0}  # HA +100, HB 缺位贡献 0
    assert pt("totals", b5) == {"t": b5, "dl": 0, "up": 0}  # z 快照同值 delta=0
    assert pt("totals", b5 + 30) is None

    # E6 字节守恒对账: Sigma(组 totals) = Sigma(成员系列 totals)(分组只是重新划界,
    # 不造字节不丢字节 —— 成员重置/缺位的 0 贡献与组 Σ 同口径)
    def _sum_totals(payload):
        return sum(t["dl"] for t in payload["totals"] if t is not None and t["dl"] is not None)

    member_sum = sum(
        _sum_totals(client.get(f"/api/traffic/qb/torrent/{h}", headers=auth, params={
            "window": "5m"
        }).json()) for h in ("HA", "HB")
    )
    assert _sum_totals(body) == member_sum == 1400  # HA 1100(重置向跳过) + HB 300
    # 指纹解析不到成员 -> 空态; 畸形 key -> 400(同 /api/groups/{key} 通道)
    other = encode_group_key(("R:/other", ("c.mkv", )))
    assert client.get(f"/api/traffic/qb/group/{other}", headers=auth).json()["points"] == []
    assert client.get("/api/traffic/qb/group/!!!not-base64!!!", headers=auth).status_code == 400


def test_api_traffic_qb_group_30d_reads_member_agg_only(web_env, monkeypatch):
    """3d+ 窗组图只读成员 agg 文件(§05.4, 组图 30d 由 M×31 -> M×1 次文件读取):
    2 成员 30d 窗请求恰好 2 次 qb-traffic-v4 open(各成员 agg.dat 一次), 天文件与全局零读取;
    组速率 = 成员 agg 行求和"""
    from auto_qb.core.traffic_store import AggRow

    mgr, client = web_env
    auth = _auth(mgr)
    _enable_qb_traffic(mgr)
    store = _qb_v4(mgr)
    now = int(time.time())
    h = ((now - 172800) // 3600) * 3600  # 窗内 2 天前的小时桶
    for key in ("torrent:HA", "torrent:HB"):
        store.append_agg_rows(key, (AggRow("hour", h, 100, 100, 10, 10, 1000, 100, 3600), ))
    opened = _qb_open_spy(monkeypatch)
    body = client.get(f"/api/traffic/qb/group/{encode_group_key(KEY)}", headers=auth, params={"window": "30d"}).json()
    monkeypatch.undo()
    v4 = _v4_opens(opened)
    assert len(v4) == 2 and all(p.endswith("agg.dat") for p in v4)  # M×1, 不读任何天文件
    p = next(p for p in body["points"] if p and p["t"] == h)
    assert p == {"t": h, "dl": 200, "up": 20}  # Σ 成员 avg
    total = next(p for p in body["totals"] if p and p["t"] == h)
    assert total == {"t": h, "dl": 0, "up": 0}  # 双成员基线缺失 -> 0(不出洞)


def test_api_traffic_qb_group_never_transferred_empty_state(web_env):
    """组从未有成员产过流量(成员文件全缺) -> 空态(§08 分组端点); 不渲染全 0 线"""
    mgr, client = web_env
    auth = _auth(mgr)
    _enable_qb_traffic(mgr)
    body = client.get(f"/api/traffic/qb/group/{encode_group_key(KEY)}", headers=auth).json()
    assert body["points"] == [] and body["totals"] == [] and body["meta"]["stale"] is False


def test_api_traffic_qb_group_merge_null_faces(web_env):
    """(T1b)组 Σ 合并的空值面(E6 合并口径补全): 成员显式空值点(n 游程折叠)在其他成员
    有真值点的同 t 处按无观测剔除(不造 0) / 全 None 真值点(重置 + 停机洞 -> 速率与
    totals 逐向全 None)剔除同判(旧 v4_grid_obs 剔除面承袭) / 全员无真值点的 t ->
    组显式空值点 {t, dl: None, up: None} + totals None —— 缺口显式空值语义进组端点(E3);
    成员速率面单方向 None 分支(26-11-18-0037 评审 #4): HB 短缝(30s <= 停机洞阈 60s,
    broke 置位不 hole)后 dl 回落 + up 步进 —— dl 覆盖 0 + 断链 -> 成员点 {dl: None,
    up: 有值}, 组点该向 None(另一成员无该 t 点 -> Σ 即成员真值, 与成员系列对账);
    totals 面 dl 重置贡献 0 不出洞"""
    from auto_qb.core.traffic_store import V4NullRun, V4Sample, v4_epoch_date_str

    mgr, client = web_env
    auth = _auth(mgr)
    _enable_qb_traffic(mgr, sample_interval_multiplier=15)  # 30s 生效(5m 窗预期 10 样本 -> k=1)
    store = _qb_v4(mgr)
    now = int(time.time())
    base = ((now - 240) // 30) * 30
    t_mark = base + 30  # HA 断连 n 槽 ts(整值) == HB 真值样本 ts: 同 t 空值点让位真值点
    t_seam = base + 90  # HB 块间短缝后首样本(缝 30s <= 停机洞阈: broke 不 hole 不摊配标记)
    t_hole = base + 120  # HA 重置 + 观测缝 -> 全 None 真值点(无观测)
    # HA: 窗外基线样本(重置前链, 只作差分基线不产组点) + n 槽(断连折叠空值点) +
    #     重置且跨缝样本(速率/totals 逐向全 None)
    store.append_records(
        "torrent:HA", v4_epoch_date_str(base - 90), (base - 90, 30), (V4Sample(1, 1, 1000, 500), ), (1000, 500)
    )
    store.append_records("torrent:HA", v4_epoch_date_str(t_mark), (t_mark, 30), (V4NullRun(1), ), (1000, 500))
    store.append_records(
        "torrent:HA", v4_epoch_date_str(t_hole), (t_hole, 30), (V4Sample(1, 1, 500, 250), ), (500, 250)
    )
    store.append_records(  # HB: 真值样本 @t_mark 与 HA 空值点同刻
        "torrent:HB", v4_epoch_date_str(t_mark), (t_mark, 30), (V4Sample(100, 50, 1000, 500), ), (1000, 500)
    )
    store.append_records(  # HB 短缝后块(缝 30s: 对跨 60s - 声称覆盖 30s): dl 回落(快照
        # 1000 -> 1 立点, delta None -> dl 覆盖 0 + broke -> 速率 None)+ up 步进(摊配
        # 100 x cov 30s // span 60s = 50 -> 速率 2)
        "torrent:HB", v4_epoch_date_str(t_seam), (t_seam, 30), (V4Sample(1, 1, 1, 600), ), (1, 600)
    )
    body = client.get(f"/api/traffic/qb/group/{encode_group_key(KEY)}", headers=auth, params={"window": "5m"}).json()

    def pt(seg, t):
        return next((p for p in body[seg] if p and p["t"] == t), None)

    assert body["meta"]["schema"] == 2 and body["meta"]["stride"] == 1
    assert pt("points", t_mark) == {"t": t_mark, "dl": 0, "up": 0}  # HA 空值点剔除, HB 真值 0 线(链首无基线)
    assert pt("points", t_hole) == {"t": t_hole, "dl": None, "up": None}  # 全员无真值点 -> 组显式空值点
    assert pt("totals", t_mark) == {"t": t_mark, "dl": 0, "up": 0}  # HB 基线缺失 -> 0(不出洞)
    assert pt("totals", t_hole) is None  # 组空值点 totals = None
    assert len(body["points"]) == 3 and len(body["totals"]) == 3  # t 并集恰三点(空值点/真值点/短缝点各一)
    # 评审 #4: 成员速率面单方向 None 分支 —— HB 短缝点 {dl: None, up: 2}, HA 该 t 无点:
    # 组点 dl = None(全员该向皆未知 -> 断链未知不画 0 值孤点), up = Σ = HB 真值
    hb = client.get("/api/traffic/qb/torrent/HB", headers=auth, params={"window": "5m"}).json()
    hb_p = next(p for p in hb["points"] if p["t"] == t_seam)
    assert hb_p == {"t": t_seam, "dl": None, "up": 2}  # 成员面: dl 断链未知 / up 摊配回收 50B/30s
    assert pt("points", t_seam) == hb_p  # 组 Σ 对账: 组点 == 成员真值点(单成员无点可 Σ)
    assert pt("totals", t_seam) == {"t": t_seam, "dl": 0, "up": 100}  # HB totals dl 重置 -> 组 0(缺失贡献 0)


def test_api_traffic_qb_meta_interval_fractional_stride_si(web_env):
    """(T1b)meta.interval_s = k x si 组距标称: 非整值宽保持浮点(整值归一只在整值时收整,
    沿旧桶宽可半秒值惯例)。si = 2 x main_tick 1.25 = 2.5, 1m 窗预期 24 样本 -> k=1 ->
    interval_s = 2.5(空数据面空态同样携带)"""
    mgr, client = web_env
    auth = _auth(mgr)
    _enable_qb_traffic(mgr, sample_interval_multiplier=2)
    mgr.config.main_tick = 1.25  # si = multiplier x main_tick = 2.5(替身 config 直改, validate 面外)
    _qb_v4(mgr)  # 空数据面
    body = client.get("/api/traffic/qb/global", headers=auth, params={"window": "1m"}).json()
    assert body["meta"]["schema"] == 2 and body["meta"]["stride"] == 1
    assert body["meta"]["interval_s"] == 2.5


def test_api_traffic_qb_meta_over_budget_flag(web_env):
    """(26-11-18-0037 评审 #1)over_budget 只真值携带: raw 段窗装配超预算(缺口标记数
    >= MAX_RAW_POINTS=500, 预算数学不可达 -> 按 k 上限交付并如实标注, §03)经端点
    _respond 装配单点落 meta.over_budget=true(D6 meta 只增不改 —— 缺省形无该键, 旧
    前端无感; 常规响应/空态 meta 无该键)。装配面 over_budget 判定本身由 T1a/T1c-1
    电池钉住(test_traffic_group_assembly / test_traffic_group_cache), 端点级造 500+
    标记需千槽级布景得不偿失 —— 此处直接驱动 _respond 验证 meta 落键半边(最小侵入)"""
    from auto_qb.webui.server.traffic_qb import QbTrafficChartApi

    mgr, _ = web_env
    _enable_qb_traffic(mgr)
    svc = QbTrafficChartApi(mgr)
    grid = svc._grid("24h")
    # 真值形态: meta 带 over_budget=true
    meta = svc._respond(grid, [], [], degraded=False, stride=1, over_budget=True)["meta"]
    assert meta["over_budget"] is True
    assert meta["schema"] == 2 and meta["stride"] == 1  # 其余 meta 键不受影响
    # 缺省形态(常规响应): 不携带该键(只增不改, 旧前端无感)
    meta2 = svc._respond(grid, [], [], degraded=False, stride=1)["meta"]
    assert "over_budget" not in meta2


def test_api_traffic_qb_group_member_only_zruns_not_empty(web_env):
    """组空态判据观测面(§05.4 沿用): 成员只剩 z 块(raw 已滑出
    窗/从未活跃传输)不算「从未产过流量」—— z 覆盖是真实观测, 组出 0 线而非空态;
    全程不读全局系列(本用例未造任何全局数据)"""
    from auto_qb.core.traffic_store import V4ZeroRun, v4_epoch_date_str

    mgr, client = web_env
    auth = _auth(mgr)
    # (T1b)同组端点用例: 显式 5m 窗 + 30s 生效间隔 -> k=1 逐样本(点 t = 样本 ts)
    _enable_qb_traffic(mgr, sample_interval_multiplier=15)
    store = _qb_v4(mgr)
    now = int(time.time())
    start = ((now - 240) // 30) * 30  # 5m 窗内
    # 块首记录 = z 游程: 块首槽位恰在 start+30
    store.append_records(
        "torrent:HA", v4_epoch_date_str(start + 30), (start + 30, 30), (V4ZeroRun(1, 100, 50), ), (100, 50)
    )
    body = client.get(f"/api/traffic/qb/group/{encode_group_key(KEY)}", headers=auth, params={"window": "5m"}).json()
    assert body["points"] != []  # 非空态: 只剩 z 覆盖的成员仍产出 points
    assert body["meta"]["schema"] == 2 and body["meta"]["stride"] == 1
    p = next(p for p in body["points"] if p and p["t"] == start + 30)
    assert p == {"t": start + 30, "dl": 0, "up": 0}  # (T1b)z 槽 @start+30 -> 点 t = start+30: 空闲 0 线


# ---------- P1-T1.5 守卫与容错簇(计划 26-10-20-2101) ----------


def test_service_defensive_paths(web_env, monkeypatch):
    """读侧装配的防御面(直接驱动服务对象, 免端点样板):
    - limitscache/bucketcache 构造期预建(无惰性双构造面); 限速读失败 = 空注解面(不 500, 缺线不冒充空态)
    - 活尾未封口部分行按段过滤(无该型行 = ())
    - 组成员天文件读竞态 -> 该成员按空观测面计 + 降级标 stale(不冒充无数据)
    - 组成员 agg 读竞态 -> 成员行按 () 计 + 降级; 单系列 all 窗竞态 -> 栅格兜底
    - 组成员月行 -> all 窗栅格由成员数据面并集铺格"""
    from types import SimpleNamespace

    from auto_qb.core.traffic_store import AggRow, v4_month_epoch
    from auto_qb.webui.server import traffic_qb as tq_mod
    from auto_qb.webui.server.traffic_qb import QbTrafficChartApi

    mgr, _ = web_env
    _enable_qb_traffic(mgr)
    svc = QbTrafficChartApi(mgr)
    assert svc.limitscache is svc._limitscache  # 构造期预建单例
    assert svc.bucketcache is svc._bucketcache  # 桶值缓存构造期预建单例(F4-2/3 只读引用)

    def boom(*args, **kwargs):
        raise OSError("read race")

    monkeypatch.setattr(tq_mod, "limits_events_for_window", boom)
    assert svc._limits_list(svc._grid("24h")) == []  # 注解面缺口: 空数组, 不抛

    rows = (AggRow("hour", 100, 1, 1, 1, 1, 1, 1, 60), AggRow("day", 0, 1, 1, 1, 1, 1, 1, 60))
    monkeypatch.setattr(svc, "_live_tail", lambda key: SimpleNamespace(pending_agg=rows))
    assert [r.kind for r in svc._live_agg_rows("global", "hour")] == ["hour"]
    assert svc._live_agg_rows("global", "month") == ()  # 无该型行

    enc = encode_group_key(KEY)
    monkeypatch.setattr(svc.v4cache, "read_window", boom)
    body = svc.payload_group(enc, "24h")  # 成员天文件读竞态
    assert body["meta"]["stale"] is True and body["points"] == []
    monkeypatch.setattr(svc.v4cache, "read_agg", boom)
    body = svc.payload_group(enc, "30d")  # 成员 agg 读竞态
    assert body["meta"]["stale"] is True
    assert svc.payload_global("all")["meta"]["stale"] is True  # 单系列 month 段竞态: 栅格兜底

    monkeypatch.undo()
    store = _qb_v4(mgr)
    month = v4_month_epoch(int(time.time()))
    for h in ("HA", "HB"):
        store.append_agg_rows(f"torrent:{h}", (AggRow("month", month, 7, 9, 3, 4, 500, 600, 86400), ))
    body = svc.payload_group(enc, "all")
    assert body["meta"]["stale"] is False
    assert [p["t"] for p in body["points"]] == [month]  # 成员月行并集铺格
    assert body["points"][0]["dl"] == 14  # Σ 成员均值(7 + 7)
