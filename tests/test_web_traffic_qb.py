"""test_web_traffic_qb 测试计划: qB 口径流量图三 GET 端点

## 测试计划(每个测试函数一条)
- test_api_traffic_qb_disabled_empty_state: qB 口径流量三端点未启用(qb_traffic None / enabled=false)空态与 /api/traffic/history 同构(plan 26-10-03-0946 §08 P4)
- test_api_traffic_qb_requires_token: 三 GET 端点沿用全局 token 鉴权单点(无凭证 401)
- test_api_traffic_qb_window_validation: window 非法值 400 / 缺省 24h / 仅认 WINDOW_NAMES 十三档(D4 沿用: 1m-30d + 6mo/1y/all, 90d 延后)
- test_api_traffic_qb_global_24h_points_totals_and_stale: global 24h 窗天文件块 -> 速率口径变换(区间平均 delta/w, 计划 26-10-07-2127 S2) -> 栅格展开(points 对齐桶/空桶 null=断连真空/窗首无种子 D4 0 线) + totals 差分(重置/断链, 口径不受速率变换影响) + 读取竞态降级回上一份快照标 stale
- test_api_traffic_qb_raw_rate_basis_delta_per_w_totals_unchanged: (计划 26-10-07-2127 S2)raw 窗速率口径 = 计数器差分区间平均 delta/w —— 已知 totals 序列逐桶断言 + 瞬时直采值零上图 + totals 通道逐字节不变(窗首基线缺失/相邻差分照旧) + 活尾桶跨盘/尾接缝差分(图尾同为区间平均)
- test_api_traffic_qb_raw_seed_extension_window_start_baseline: (S2/D3)窗首种子: read_window/v4_series_points t0 外扩一个响应桶宽取前驱桶点作差分基线 —— 窗首桶 rate = delta/w(非 0 线非瞬时值), 种子点被 v4_grid_obs 窗外过滤不外发
- test_api_traffic_qb_raw_seed_vacuum_chain_break_and_recover: (S2/D3)种子跨真空: 真空 null 点断链 —— 恢复首桶 rate 派不出(D4 0 线)且离线期字节不进速率与 totals, 次桶基线恢复 delta/w
- test_api_traffic_qb_raw_seed_vacuum_null_1s_edge_band: (issue 26-10-08-0141)窗首种子 1 秒边界带: 停机落 (seed_t0-1, seed_t0) 时真空 null 点取整后落窗外 —— 修复后标记保留断链, 恢复首桶 D4 0 线且离线字节不进速率/totals(修复前链误接出假尖峰)
- test_api_traffic_qb_global_30d_hour_segment: global 30d 窗 agg hour 行直映栅格桶(epoch 即桶键), interval_s=3600, 相邻桶差分
- test_api_traffic_qb_global_6mo_1y_day_segment: (S3b D4 沿用)6mo/1y 窗 agg day 行直映本地日界桶 —— 滚动窗切片(300 天前行 1y 可见/6mo 不可见), 缺日断链, interval_s=86400
- test_api_traffic_qb_global_all_month_segment: (S3b D4 沿用)all 窗 agg month 行数据面逐月铺格(缺失月 null), 相邻月差分, interval_s=标称月长; 空数据面空态
- test_api_traffic_qb_torrent_endpoint: 单种端点取数 / 非法哈希 400 / 未知哈希空态 / 冻结种子历史仍可查
- test_api_traffic_qb_torrent_1y_single_agg_cold_read: (S3b 验收)年视图单 agg 文件冷读恰 1 open, 缓存命中再查零 open
- test_api_traffic_qb_global_24h_reads_only_involved_day_files: (S3b 端点面回归)24h 窗只开窗口涉及日期天文件(含窗首种子外扩: 常态恰 2 个/跨午夜边界至多 3 个), 窗外日期/agg.dat 零 open
- test_api_traffic_qb_group_endpoint: 分组读侧现算(Σ 成员区间平均/全员空闲 z 覆盖 0 线/全员无观测断线 —— 借 global 判 null 退役且零全局读取/成员重置贡献 0/历史回溯可见/解析不到成员空态/畸形 key 400)
- test_api_traffic_qb_group_30d_reads_member_agg_only: (S3b 验收)3d+ 窗组图只读成员 agg 文件(2 成员恰 2 open = M×1, 天文件零读取)
- test_api_traffic_qb_group_never_transferred_empty_state: 组从未有成员产过流量 -> 空态
- test_api_traffic_qb_group_member_only_zruns_not_empty: 组空态判据观测面 —— 成员只剩 z 块不算「从未产过流量」, 出 0 线而非空态
"""
import os
import time

from auto_qb.infra.utils import encode_group_key

from webui_helpers import KEY, _enable_qb_traffic, _qb_v4, _attach_live_tail_host


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
    """qb-traffic-v4/ 数据面的打开路径(请求链路会开无关文件, 只看 v4 读盘)"""
    return [p for p in opened if "qb-traffic-v4/" in p]


def test_api_traffic_qb_disabled_empty_state(web_env):
    """未启用空态(qb_traffic None / enabled=false): 三端点 200 空数组 + meta, 与 /api/traffic/history 未启用分支同构"""
    mgr, client = web_env
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    paths = ("/api/traffic/qb/global", f"/api/traffic/qb/torrent/HA", f"/api/traffic/qb/group/{encode_group_key(KEY)}")
    for p in paths:  # qb_traffic = None(缺省): 200 空态(不 500 不 404)
        r = client.get(p, headers=auth)
        assert r.status_code == 200, p
        body = r.json()
        assert body["points"] == [] and body["totals"] == []
        assert body["meta"]["source"] == "qb" and body["meta"]["stale"] is False and body["meta"]["window"] == "24h"
    # 与未启用空数组先例同构: /api/traffic/history 同样 200 + 空数组
    assert client.get("/api/traffic/history", headers=auth).status_code == 200
    _enable_qb_traffic(mgr, enabled=False)  # 段存在但 enabled=false: 同空态
    for p in paths:
        body = client.get(p, headers=auth).json()
        assert body["points"] == [] and body["meta"]["stale"] is False


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
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
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
    """global 24h 窗(raw 段): 天文件块 -> 桶点 -> 速率口径变换(区间平均 delta/w, 计划
    26-10-07-2127 S2) -> 栅格展开(points 对齐桶 / 空桶 null = 断连真空 / 窗首无种子基线
    缺失 D4 豁免 0 线) + totals 相邻桶快照差分(重置 null / 断连断链, 口径不受速率变换
    影响) + 读取竞态降级: 回上一份成功快照标 stale=true, 不以空态冒充无数据(§08)"""
    from auto_qb.core.traffic_store import V4Block, V4DayCache, V4NullRun, V4Sample, v4_epoch_date_str

    mgr, client = web_env
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    _enable_qb_traffic(mgr)
    store = _qb_v4(mgr)
    now = int(time.time())
    base = ((now - 7200) // 30) * 30  # 窗内 2h 处的 30s 对齐桶
    # 块首记录槽位恰在 base+30(w=30) -> 桶 base 1:1 对位, 其后标称 30s 逐桶对齐;
    # n 游程 3 槽(槽位 base+180/210/240)在响应面 = 连续空桶(断连), 尾记录以游程终点续链
    # v4 行型: 计数器回落处拆块(与写侧「重置强制关块重立基线」一致), 槽位序列不变
    store.append_records(
        "global",
        v4_epoch_date_str(base + 30),
        (base + 30, 30),
        (
            V4Sample(100, 50, 1000, 500),  # 桶 base
            V4Sample(200, 70, 2000, 800),  # 桶 base+30
            V4Sample(5, 5, 2400, 900),  # 桶 base+60
            V4Sample(300, 90, 3400, 1300),  # 桶 base+90
        ),
        (1000, 500),
    )
    store.append_records(
        "global",
        v4_epoch_date_str(base + 30),
        (base + 150, 30),
        (
            V4Sample(10, 10, 2900, 1400),  # 桶 base+120: dl 快照回落(重置, 新块立基线)
            V4NullRun(3, dt_ms=90000),  # 断连 3 槽: 桶 base+150/180/210 空
            V4Sample(12, 22, 3500, 1500, dt_ms=30000),  # 桶 base+240(断链后基线缺失)
        ),
        (2900, 1400),
    )

    def point_at(body, bucket):
        return next((p for p in body["points"] if p and p["t"] == bucket), None)

    def total_at(body, bucket):
        return next((p for p in body["totals"] if p and p["t"] == bucket), None)

    r = client.get("/api/traffic/qb/global", headers=auth)
    assert r.status_code == 200
    body = r.json()
    assert body["meta"] == {"window": "24h", "interval_s": 30, "source": "qb", "stale": False}
    assert 2880 <= len(body["points"]) <= 2881  # 满窗栅格(窗首对齐时恰 2880)
    assert point_at(body, base) == {"t": base, "dl": 0, "up": 0}  # 窗内首点无基线: D4 豁免 0 线(非 null)
    assert point_at(body, base + 30) == {"t": base + 30, "dl": 33, "up": 10}  # 区间平均: delta(1000,300)/30
    assert point_at(body, base + 120) == {"t": base + 120, "dl": 0, "up": 3}  # dl 重置派不出 0 线 + up delta(100)/30
    assert point_at(body, base + 150) is None  # 断连段: 连续空桶 = null(不连线)
    assert point_at(body, base + 180) is None
    assert point_at(body, base + 210) is None
    assert point_at(body, base + 240) == {"t": base + 240, "dl": 0, "up": 0}  # 断链后基线缺失: D4 0 线
    # totals: 桶 base 窗内首个有观测桶 -> 基线缺失 null; 相邻桶差分; 重置逐向独立; 断链后基线缺失
    assert total_at(body, base) == {"t": base, "dl": None, "up": None}
    assert total_at(body, base + 30) == {"t": base + 30, "dl": 1000, "up": 300}
    assert total_at(body, base + 60) == {"t": base + 60, "dl": 400, "up": 100}
    assert total_at(body, base + 90) == {"t": base + 90, "dl": 1000, "up": 400}
    assert total_at(body, base + 120) == {"t": base + 120, "dl": None, "up": 100}  # dl 重置
    assert total_at(body, base + 180) is None  # 断连桶
    assert total_at(body, base + 240) == {"t": base + 240, "dl": None, "up": None}  # 断链后基线缺失

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
    """(计划 26-10-07-2127 S2)raw 窗速率口径 = 计数器差分区间平均 delta/w: 已知 totals 序列
    逐桶断言(20/10 与 40/20), 瞬时直采值(5xxx-9xxx 垃圾字段)零上图; totals 通道逐字节不变
    (窗首基线缺失 null + 相邻差分照旧); 活尾槽带绝对 totals —— 图尾桶跨盘/尾接缝差分,
    同为区间平均(head_pending=False 非块首活尾从写侧游标倒推槽位)"""
    from auto_qb.core.traffic_store import LiveTail, V4Sample, v4_epoch_date_str

    mgr, client = web_env
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    _enable_qb_traffic(mgr)
    store = _qb_v4(mgr)
    now = int(time.time())
    b0 = ((now - 240) // 30) * 30  # 5m 窗内, 远离窗首/窗尾栅格边缘(种子外扩区无数据)
    store.append_records(
        "global",
        v4_epoch_date_str(b0 + 30),
        (b0 + 30, 30),
        (
            V4Sample(7777, 7777, 1000, 500),  # 桶 b0: 窗内首点无基线 -> D4 0 线
            V4Sample(9999, 9999, 1600, 800),  # 桶 b0+30: delta(600,300)/30 -> 20/10
            V4Sample(5555, 5555, 2800, 1400),  # 桶 b0+60: delta(1200,600)/30 -> 40/20
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
                    start_epoch=b0 + 30,
                    interval_s=30,
                    projected_ts=float(b0 + 120),
                    records=(V4Sample(8888, 8888, 3400, 1700), ),  # 桶 b0+90: delta(600,300)/30 -> 20/10
                    open_run=None,
                )
        },
    )
    body = client.get("/api/traffic/qb/global", headers=auth, params={"window": "5m"}).json()

    def pt(seg, t):
        return next((p for p in body[seg] if p and p["t"] == t), None)

    assert body["meta"]["stale"] is False and body["meta"]["interval_s"] == 30
    assert pt("points", b0) == {"t": b0, "dl": 0, "up": 0}  # 窗内首点基线缺失 D4 0 线
    assert pt("points", b0 + 30) == {"t": b0 + 30, "dl": 20, "up": 10}
    assert pt("points", b0 + 60) == {"t": b0 + 60, "dl": 40, "up": 20}
    assert pt("points", b0 + 90) == {"t": b0 + 90, "dl": 20, "up": 10}  # 活尾桶: 跨盘/尾接缝差分
    assert all(p["dl"] < 1000 and p["up"] < 1000 for p in body["points"] if p is not None)  # 瞬时垃圾值零上图
    # totals 通道逐字节不变(速率变换不动快照链): 窗首基线缺失 + 相邻差分(含活尾桶)
    assert pt("totals", b0) == {"t": b0, "dl": None, "up": None}
    assert pt("totals", b0 + 30) == {"t": b0 + 30, "dl": 600, "up": 300}
    assert pt("totals", b0 + 60) == {"t": b0 + 60, "dl": 1200, "up": 600}
    assert pt("totals", b0 + 90) == {"t": b0 + 90, "dl": 600, "up": 300}


def test_api_traffic_qb_raw_seed_extension_window_start_baseline(web_env):
    """(计划 26-10-07-2127 S2/D3)窗首种子: read_window/v4_series_points 的 t0 外扩一个响应
    桶宽(grid.t0 - grid.interval)取前驱桶点作差分基线 —— 窗首桶 rate = delta/w(旧口径下
    是瞬时直采值; 无种子时是 D4 0 线), 瞬时垃圾值零上图; 种子点自身基线缺失且被 v4_grid_obs
    窗外过滤天然不外发。数据跨窗首等距等差铺放(逐桶 delta 恒 600/300), 对窗首 floor 对齐
    位置与端点取 now 的 ±1s 秒漂不敏感(断言值恒定)"""
    from auto_qb.core.traffic_store import V4Sample, v4_epoch_date_str

    mgr, client = web_env
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    _enable_qb_traffic(mgr)
    store = _qb_v4(mgr)
    now = int(time.time())
    first = (now - 300) - ((now - 300) % 30)  # 5m 窗栅格首桶(floor 对齐)
    totals = ((1000, 500), (1600, 800), (2200, 1100), (2800, 1400), (3400, 1700))
    store.append_records(
        "global",
        v4_epoch_date_str(first),
        (first, 30),
        tuple(V4Sample(9999, 9999, dl, up) for dl, up in totals),  # 瞬时字段全垃圾, 只看差分
        (1000, 500),
    )
    body = client.get("/api/traffic/qb/global", headers=auth, params={"window": "5m"}).json()
    pts = [p for p in body["points"] if p is not None]
    assert len(pts) >= 2 and body["meta"]["stale"] is False
    p0 = pts[0]
    assert p0["t"] in (first, first + 30)  # 端点取 now 与用例 ±1s: 窗首桶至多移一格
    assert all(p["dl"] == 20 and p["up"] == 10 for p in pts)  # 逐桶 delta(600,300)/30 —— 种子给窗首桶基线
    tots = [p for p in body["totals"] if p is not None]
    assert tots[0] == {"t": p0["t"], "dl": None, "up": None}  # totals 口径不变: 窗首桶基线缺失
    assert tots[1] == {"t": pts[1]["t"], "dl": 600, "up": 300}  # 相邻桶差分照旧


def test_api_traffic_qb_raw_seed_vacuum_chain_break_and_recover(web_env):
    """(计划 26-10-07-2127 S2/D3)种子跨真空: 窗首前种子块与窗内恢复块之间程序停机 ——
    v4_series_points 既有真空判定出 null 点断链, 恢复首桶 rate 派不出(D4 豁免 0 线, 非
    null 非尖峰), 离线期 qB 自行传输的字节既不进速率也不进 totals(恢复首桶 totals 基线
    缺失 null), 次桶起基线恢复 delta/w"""
    from auto_qb.core.traffic_store import V4Sample, v4_epoch_date_str

    mgr, client = web_env
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    _enable_qb_traffic(mgr)
    store = _qb_v4(mgr)
    now = int(time.time())
    first = (now - 300) - ((now - 300) % 30)
    store.append_records(  # 窗首前种子块: 单记录, 桶 first-30(被 v4_grid_obs 窗外过滤不外发)
        "global", v4_epoch_date_str(first), (first, 30), (V4Sample(1111, 1111, 1000, 500), ), (1000, 500)
    )
    store.append_records(  # 停机后恢复块(真空 [first, first+60)): 首记录 totals 已含离线期字节 9000/4500
        "global",
        v4_epoch_date_str(first + 90),
        (first + 90, 30),
        (
            V4Sample(9999, 9999, 10600, 5300),  # 桶 first+60: 恢复首点基线缺失 -> D4 0 线(离线字节不进速率)
            V4Sample(7777, 7777, 11200, 5600),  # 桶 first+90: delta(600,300)/30 -> 20/10(基线恢复)
            V4Sample(5555, 5555, 11800, 5900),  # 桶 first+120: delta(600,300)/30 -> 20/10
        ),
        (10600, 5300),
    )
    body = client.get("/api/traffic/qb/global", headers=auth, params={"window": "5m"}).json()

    def pt(seg, t):
        return next((p for p in body[seg] if p and p["t"] == t), None)

    assert body["meta"]["stale"] is False
    assert pt("points", first) is None and pt("points", first + 30) is None  # 真空段断线(不连线)
    assert pt("points", first + 60) == {"t": first + 60, "dl": 0, "up": 0}  # 恢复首桶 D4 0 线(非 null 非尖峰)
    assert pt("points", first + 90) == {"t": first + 90, "dl": 20, "up": 10}  # 基线恢复
    assert pt("points", first + 120) == {"t": first + 120, "dl": 20, "up": 10}
    assert all(p["dl"] < 1000 and p["up"] < 1000 for p in body["points"] if p is not None)  # 瞬时垃圾值零上图
    assert pt("totals", first + 60) == {"t": first + 60, "dl": None, "up": None}  # 离线字节不进 totals(基线缺失)
    assert pt("totals", first + 90) == {"t": first + 90, "dl": 600, "up": 300}
    assert all(p is None or (p["dl"] in (None, 600) and p["up"] in (None, 300)) for p in body["totals"])


def test_api_traffic_qb_raw_seed_vacuum_null_1s_edge_band(web_env, monkeypatch):
    """(issue 26-10-08-0141)窗首种子 1 秒边界带: 停机时刻落在 (seed_t0-1, seed_t0) 时真空
    null 点 t = int(prev_chain_end) 取整后 = seed_t0-1 恰落窗外 —— 修复前被丢弃, 种子点
    (覆盖桶触及窗首照收)与恢复首点之间差分链误接, 离线期 qB 自行传输的字节被误归恢复首桶
    出假尖峰(rate 300 / totals 9000); 修复后标记保留并断链, 恢复首桶 rate 派不出(D4 0 线)
    且离线字节不进速率与 totals。时钟钉死(1 秒带需确定性 now; 端点 _grid 走 traffic_qb.time.time)"""
    from auto_qb.core.traffic_store import V4Sample, v4_epoch_date_str
    from auto_qb.webui.server import traffic_qb as tq

    mgr, client = web_env
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    _enable_qb_traffic(mgr)
    store = _qb_v4(mgr)
    fixed = 1_800_000_000.0  # 30 的整倍 -> 5m 窗栅格对齐(确定性几何)

    class _FixedClock:
        def time(self):
            return fixed

    monkeypatch.setattr(tq, "time", _FixedClock())
    g_t0 = int(fixed) - 300  # 5m 窗栅格首桶
    seed_t0 = g_t0 - 30  # D3 窗首种子外扩 = grid.t0 - grid.interval
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

    assert body["meta"]["stale"] is False and body["meta"]["interval_s"] == 30
    assert pt("points", g_t0) == {"t": g_t0, "dl": 0, "up": 0}  # 恢复首桶 D4 0 线(修复前 = 假尖峰 300)
    assert pt("points", g_t0 + 30) == {"t": g_t0 + 30, "dl": 20, "up": 10}  # 次桶基线恢复 delta/w
    assert all(p["dl"] < 1000 and p["up"] < 1000 for p in body["points"] if p is not None)  # 离线字节零上图
    assert pt("totals", g_t0) == {"t": g_t0, "dl": None, "up": None}  # 离线字节不进 totals(修复前 = 9000)
    assert pt("totals", g_t0 + 30) == {"t": g_t0 + 30, "dl": 600, "up": 300}


def test_api_traffic_qb_global_30d_hour_segment(web_env):
    """global 30d 窗(agg hour 段): agg.dat hour 行直映栅格桶(epoch 即桶键, 桶内不再
    聚合), meta.interval_s=3600; 相邻 hour 桶快照差分"""
    from auto_qb.core.traffic_store import AggRow

    mgr, client = web_env
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
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
    assert 720 <= len(body["points"]) <= 721  # 30d 窗 ≈720 桶
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
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
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
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
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
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    _enable_qb_traffic(mgr)
    store = _qb_v4(mgr)
    now = int(time.time())
    base = ((now - 3600) // 30) * 30
    # 块首记录槽位恰在 base+30(w=30) -> 桶 base 1:1 对位
    store.append_records(
        "torrent:HA", v4_epoch_date_str(base + 30), (base + 30, 30), (V4Sample(500, 100, 5000, 1000), ), (5000, 1000)
    )
    body = client.get("/api/traffic/qb/torrent/HA", headers=auth).json()
    assert body["meta"]["source"] == "qb" and body["meta"]["stale"] is False
    p = next(p for p in body["points"] if p and p["t"] == base)
    assert p == {"t": base, "dl": 0, "up": 0}  # 区间平均口径: 单记录窗首无基线, D4 豁免 0 线(瞬时值不上图)
    # 非法哈希(路径不安全字符, 存储层 fail-fast) -> 400; 未知哈希(合法字符, 无文件) -> 空态
    assert client.get("/api/traffic/qb/torrent/HA.X", headers=auth).status_code == 400
    assert client.get("/api/traffic/qb/torrent/ZZ", headers=auth).json()["points"] == []
    # 删种冻结(hash 已不在 by_hash 快照)后历史仍可查: 数据以 v4 天文件为准, 不以快照存在性裁决
    assert "HA" not in mgr.store.by_hash
    body2 = client.get("/api/traffic/qb/torrent/HA", headers=auth).json()
    assert any(p2 and p2["t"] == base for p2 in body2["points"])


def test_api_traffic_qb_torrent_1y_single_agg_cold_read(web_env, monkeypatch):
    """年视图单 agg 文件冷读(§05.3 验收): 1y 窗恰好 1 次 qb-traffic-v4 open(agg.dat,
    天文件零读取); 再查(mtime/size 键控缓存命中)零新 open"""
    from datetime import datetime, timedelta

    from auto_qb.core.traffic_store import AggRow

    mgr, client = web_env
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
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


def test_api_traffic_qb_global_24h_reads_only_involved_day_files(web_env, monkeypatch):
    """24h 窗端点面回归(§05.2): 只开窗口涉及的日期天文件(24h 窗恰 2 个, 窗外更早天文件
    零 open), agg.dat 亦不触"""
    from datetime import datetime, timedelta

    from auto_qb.core.traffic_store import V4Sample, v4_epoch_date_str, v4_window_dates

    mgr, client = web_env
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    _enable_qb_traffic(mgr)
    store = _qb_v4(mgr)
    now = int(time.time())
    base = ((now - 600) // 30) * 30  # 窗内 10 分钟前的对齐桶
    involved = sorted(v4_window_dates(now - 86400 - 30, now))  # 镜像端点窗首种子外扩(S2/D3: t0 - 一个桶宽)
    older_date = (datetime.strptime(involved[0], "%Y-%m-%d") - timedelta(days=1)).strftime("%Y-%m-%d")
    # 造数: 现行记录落 base 所在日期; 其余涉及日期与窗外更早日期各放一块(读侧按窗过滤)。
    # 块料 totals 与 base 块一致(100, 50): 窗首恰跨午夜被链进差分链时 delta=0, 窗首桶值恒 (0,0) 不随对齐漂移
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
    assert dat_opens == sorted(d + ".dat" for d in involved)  # 只开涉及日期(含种子外扩), 更早日期/agg.dat 不触
    assert 2 <= len(involved) <= 3  # 常态恰 2; 窗首种子外扩跨本地午夜边界时至多 3(S2/D3)
    assert next(p for p in body["points"] if p and p["t"] == base) == {"t": base, "dl": 0, "up": 0}  # D4 0 线


def test_api_traffic_qb_group_endpoint(web_env, monkeypatch):
    """分组端点读侧现算(观测面, §05.1/§05.4): Σ 成员均值 / 全员空闲(z 覆盖)出 0 线 /
    全员无观测(停机)整桶断线 —— 「借 global 判 null」退役: 全程零全局系列文件读取 /
    成员重置贡献 0 不拖垮全组 / 成员历史回溯可见 / 解析不到成员空态 / 畸形 key 400"""
    from auto_qb.core.traffic_store import V4Sample, V4ZeroRun, v4_epoch_date_str

    mgr, client = web_env
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    _enable_qb_traffic(mgr)
    store = _qb_v4(mgr)
    now = int(time.time())
    base = ((now - 3600) // 30) * 30
    b0, b1, b2, b3, b4, b5 = (base + i * 30 for i in range(6))
    # HA: b0..b3 r 行(块首槽位恰在 b0+30 -> 桶 1:1 对位) + b4 z 覆盖(空闲观测, 快照恒定)
    #     —— b4 之后无任何块 = 停机(桶 b5 全员无观测)
    # v4 行型: 计数器回落处拆块(与写侧「重置强制关块重立基线」一致), 槽位序列不变
    store.append_records(
        "torrent:HA",
        v4_epoch_date_str(b0 + 30),
        (b0 + 30, 30),
        (
            V4Sample(100, 10, 1000, 0),  # 桶 b0
            V4Sample(0, 0, 2000, 0),  # 桶 b1
        ),
        (1000, 0),
    )
    store.append_records(
        "torrent:HA",
        v4_epoch_date_str(b0 + 30),
        (b2 + 30, 30),
        (
            V4Sample(10, 5, 500, 0),  # 桶 b2: 快照回落(重置, 新块立基线)
            V4Sample(10, 5, 600, 0),  # 桶 b3
            V4ZeroRun(1, 600, 0),  # 桶 b4: 空闲 z 观测
        ),
        (500, 0),
    )
    # HB: b0 就有数据(200, 快照 100) —— b0 的行在其"入组前", 回溯同样可见; b1/b2 连续产点
    store.append_records(
        "torrent:HB",
        v4_epoch_date_str(b0 + 30),
        (b0 + 30, 30),
        (
            V4Sample(200, 20, 100, 0),  # 桶 b0
            V4Sample(0, 0, 300, 0),  # 桶 b1
            V4Sample(30, 3, 400, 0),  # 桶 b2
        ),
        (100, 0),
    )
    enc = encode_group_key(KEY)
    opened = _qb_open_spy(monkeypatch)
    body = client.get(f"/api/traffic/qb/group/{enc}", headers=auth).json()
    monkeypatch.undo()
    # 组端点无 global 依赖: 请求全程零 qb-traffic-v4/global/ 读取(本用例根本未造全局数据)
    assert not [p for p in _v4_opens(opened) if "/global/" in p]

    def pt(seg, t):
        return next((p for p in body[seg] if p and p["t"] == t), None)

    assert body["meta"]["source"] == "qb" and body["meta"]["stale"] is False
    assert pt("points", b0) == {"t": b0, "dl": 0, "up": 0}  # 双成员窗首点基线缺失 D4 0 线(回溯可见性不变: 桶非 null)
    assert pt("points", b1) == {"t": b1, "dl": 40, "up": 0}  # 区间平均: HA delta(1000)/30=33 + HB delta(200)/30=7
    assert pt("points", b2) == {"t": b2, "dl": 3, "up": 0}  # HA 重置派不出 0 线 + HB delta(100)/30=3
    assert pt("points", b3) == {"t": b3, "dl": 3, "up": 0}  # HA delta(100)/30=3, HB 无行按 0 计
    assert pt("points", b4) == {"t": b4, "dl": 0, "up": 0}  # HA z 覆盖空闲观测 -> 0 线(非 null)
    assert pt("points", b5) is None  # 全员无观测(停机)整桶断线 —— 成员观测面裁决, 不借 global
    assert pt("totals", b0) == {"t": b0, "dl": 0, "up": 0}  # 双成员窗内基线缺失 -> 0(不出洞)
    assert pt("totals", b1) == {"t": b1, "dl": 1200, "up": 0}  # HA +1000, HB +200
    assert pt("totals", b2) == {"t": b2, "dl": 100, "up": 0}  # HA 重置贡献 0(不是 -1500), HB +100
    assert pt("totals", b3) == {"t": b3, "dl": 100, "up": 0}  # HA +100, HB 无行基线缺失 0
    assert pt("totals", b4) == {"t": b4, "dl": 0, "up": 0}  # z 快照同值 delta=0
    assert pt("totals", b5) is None  # null 桶整桶 None
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
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
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
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    _enable_qb_traffic(mgr)
    body = client.get(f"/api/traffic/qb/group/{encode_group_key(KEY)}", headers=auth).json()
    assert body["points"] == [] and body["totals"] == [] and body["meta"]["stale"] is False


def test_api_traffic_qb_group_member_only_zruns_not_empty(web_env):
    """组空态判据观测面(§05.4 沿用): 成员只剩 z 块(raw 已滑出
    窗/从未活跃传输)不算「从未产过流量」—— z 覆盖是真实观测, 组出 0 线而非空态;
    全程不读全局系列(本用例未造任何全局数据)"""
    from auto_qb.core.traffic_store import V4ZeroRun, v4_epoch_date_str

    mgr, client = web_env
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    _enable_qb_traffic(mgr)
    store = _qb_v4(mgr)
    now = int(time.time())
    start = ((now - 600) // 30) * 30
    # 块首记录 = z 游程: 块首槽位恰在 start+30 -> 桶 start 1:1 对位
    store.append_records(
        "torrent:HA", v4_epoch_date_str(start + 30), (start + 30, 30), (V4ZeroRun(1, 100, 50), ), (100, 50)
    )
    body = client.get(f"/api/traffic/qb/group/{encode_group_key(KEY)}", headers=auth).json()
    assert body["points"] != []  # 非空态: 只剩 z 覆盖的成员仍产出 points
    p = next(p for p in body["points"] if p and p["t"] == start)
    assert p == {"t": start, "dl": 0, "up": 0}  # z 覆盖桶 -> 空闲 0 线
