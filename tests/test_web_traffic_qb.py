"""test_web_traffic_qb 测试计划: qB 口径流量图三 GET 端点(26-11-15-1104 F2 点位归属归桶重锚:
raw 段样本落其所在格, 速率一次算定 —— 断言键/值逐条改判处见用例 docstring 内 F2 标注)

## 测试计划(每个测试函数一条)
- test_api_traffic_qb_disabled_empty_state: qB 口径流量三端点未启用(qb_traffic None / enabled=false)空态与 /api/traffic/history 同构(plan 26-10-03-0946 §08 P4)+ P4 meta 契约(plan 26-10-15-0829): server_started_at = 后端进程出生时刻, 未启用空态与三端点都携带(同一 _meta 装配单点), 旧键逐字不变(只增不改, 旧前端忽略未知键), 改模块常量新响应立即携带 = 无实例级缓存面
- test_api_traffic_qb_requires_token (三 GET 端点沿用全局 token 鉴权单点, 无凭证 401; 冒号键值形态会被写入侧凭据判据误报, 故用括号注记)
- test_api_traffic_qb_window_validation: window 非法值 400 / 缺省 24h / 仅认 WINDOW_NAMES 十三档(D4 沿用: 1m-30d + 6mo/1y/all, 90d 延后)
- test_api_traffic_qb_global_24h_points_totals_and_stale: (F2 改判)global 24h 窗天文件块 -> 点位归属归桶一次算定 -> 栅格直映(points 样本落格键 +180/空桶 null=断连真空/链首 0 线) + totals 差分(重置/断链, 口径不受速率变换影响) + 读取竞态降级回上一份快照标 stale + meta 全量形状含 P4 新键 server_started_at 与 F6 只增键 sample_interval_s(plan 26-11-14-1313)
- test_api_traffic_qb_raw_rate_basis_delta_per_w_totals_unchanged: (F2 改判)raw 窗速率口径 = 桶内样本差分和/覆盖时长一次算定 —— 已知 totals 序列逐桶断言 + 瞬时直采值零上图 + totals 通道逐字节不变(窗首基线缺失/相邻差分照旧) + 活尾桶跨盘/尾接缝差分(图尾同为区间平均)
- test_api_traffic_qb_raw_live_tail_hold_extension: (F4; F2 改判)raw 段窗传 now —— 末样本槽位恒距 now 30..59s(holding 桶与末样本桶恒隔一格, 纯持有桶 totals delta 恒 0 不重计)—— 活尾链端持有限界延伸(间隙上界 max(interval_s, 采样间隔) x 2): 采样链活跃时响应尾桶(进行中桶)恒有观测且值接续末观测桶值(持有面), totals 尾桶 0 增量不造字节; 端点取时冻结假钟消除 now 竞态
- test_api_traffic_qb_group_raw_live_tail_hold_extension: (F4; F2 改判)组端点 raw 段窗成员循环同款接线钉 —— 成员活尾(torrent:HA)延伸, 组响应尾桶恒有观测(Σ 成员 = 持有面)且 totals 0 增量; 防 now=/max_gap_s= 在组调用点被变异丢弃时电池照绿
- test_api_traffic_qb_raw_seed_extension_window_start_baseline: (F2 改判)窗首种子: 种子块移到 first-30(窗前样本作首桶差分基线)—— 窗首桶 rate = 差分/覆盖(非 0 线非瞬时值), 窗前桶被 v4_grid_obs 窗外过滤不外发
- test_api_traffic_qb_raw_seed_vacuum_chain_break_and_recover: (F2 改判)种子跨真空: 种子/恢复块各移 30s(未观测恰 60s = 重启缝)—— 恢复首桶 = step/实测对跨 90s 摊配回收(107/53), 次桶基线恢复
- test_api_traffic_qb_raw_seed_vacuum_null_1s_edge_band: (F2 改判)窗首种子 1 秒边界带: 恢复样本落格 g_t0+30 —— 接收桶 = step/实测对跨 60.5s(149/74, 误接旧值 300 可判红), 离线字节不进 totals
- test_api_traffic_qb_global_30d_hour_segment: global 30d 窗 agg hour 行直映栅格桶(epoch 即桶键), interval_s=3600, 相邻桶差分
- test_api_traffic_qb_global_6mo_1y_day_segment: (S3b D4 沿用)6mo/1y 窗 agg day 行直映本地日界桶 —— 滚动窗切片(300 天前行 1y 可见/6mo 不可见), 缺日断链, interval_s=86400
- test_api_traffic_qb_global_all_month_segment: (S3b D4 沿用)all 窗 agg month 行数据面逐月铺格(缺失月 null), 相邻月差分, interval_s=标称月长; 空数据面空态
- test_api_traffic_qb_torrent_endpoint: (F2 改判)单种端点取数(样本落格 base+180)/ 非法哈希 400 + detail 种子哈希非法(存储层 v4_series_dir ValueError 转译, 多非法字符形态守阵, issue 26-11-07-0536 R4#37)/ 未知哈希空态 / 冻结种子历史仍可查
- test_api_traffic_qb_torrent_1y_single_agg_cold_read: (S3b 验收)年视图单 agg 文件冷读恰 1 open, 缓存命中再查零 open
- test_api_traffic_qb_global_24h_reads_only_involved_day_files: (S3b 端点面回归)24h 窗只开窗口涉及日期天文件(含窗首种子外扩: 常态恰 2 个/跨午夜边界至多 3 个), 窗外日期/agg.dat 零 open; 三档时钟 —— 真钟(钉入口时刻, 消除用例 now 与服务端收边横跨零点的竞态) + 假钟 00:05(issue 26-10-20-0024: base 恒取本地当日 00:00, 不随真钟漂前一日) + 假钟 00:00:15(2026-10-22 跨日窗口抖动: 当日首记录 base+30 未到窗尾时 base 桶为空桶 null, 期望值按几何分档)
- test_api_traffic_qb_group_endpoint: (F2 改判)分组读侧现算(断言键 +30/Σ 成员差分一次算定/全员空闲 z 覆盖 0 线/全员无观测断线 —— 借 global 判 null 退役且零全局读取/成员重置贡献 0/历史回溯可见/解析不到成员空态/畸形 key 400)
- test_api_traffic_qb_group_30d_reads_member_agg_only: (S3b 验收)3d+ 窗组图只读成员 agg 文件(2 成员恰 2 open = M×1, 天文件零读取)
- test_api_traffic_qb_group_never_transferred_empty_state: 组从未有成员产过流量 -> 空态
- test_api_traffic_qb_group_member_only_zruns_not_empty: (F2 改判)组空态判据观测面 —— 成员只剩 z 块不算「从未产过流量」, 出 0 线而非空态(z 块落格 start+30)
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
    """global 24h 窗(raw 段): 天文件块 -> 桶点 -> 速率口径变换(区间平均 delta/w, 计划
    26-10-07-2127 S2) -> 栅格展开(points 对齐桶 / 空桶 null = 断连真空 / 窗首无种子基线
    缺失 D4 豁免 0 线) + totals 相邻桶快照差分(重置 null / 断连断链, 口径不受速率变换
    影响) + 读取竞态降级: 回上一份成功快照标 stale=true, 不以空态冒充无数据(§08)"""
    from auto_qb.core.traffic_store import V4Block, V4DayCache, V4NullRun, V4Sample, v4_epoch_date_str
    from auto_qb.webui.server import traffic_qb as _tq_meta

    mgr, client = web_env
    auth = _auth(mgr)
    # (26-11-15-1104 F1 改判)生效间隔 30s(multiplier 15 x main_tick 2.0): 24h 桶宽 = 30 x
    # ceil(86400/15000) = 180 —— 旧口径 max(30, ceil(span/2880)) = 30 不再可达, 数据节律随
    # 桶宽改 180s(每桶恰一记录, 断言语义一一对应; 双几何实证见计划 §02)
    _enable_qb_traffic(mgr, sample_interval_multiplier=15)
    store = _qb_v4(mgr)
    now = int(time.time())
    base = ((now - 7200) // 180) * 180  # 窗内 2h 处的 180s 对齐桶(栅格桶键 = 180 的整倍)
    # 块首记录槽位恰在 base+180(w=180) -> 桶 base 1:1 对位, 其后标称 180s 逐桶对齐;
    # n 游程 3 槽(槽位 base+1080/1260/1440)在响应面 = 连续空桶(断连), 尾记录以游程终点续链
    # v4 行型: 计数器回落处拆块(与写侧「重置强制关块重立基线」一致), 槽位序列不变
    store.append_records(
        "global",
        v4_epoch_date_str(base + 180),
        (base + 180, 180),
        (
            V4Sample(100, 50, 1000, 500),  # 桶 base
            V4Sample(200, 70, 2800, 1400),  # 桶 base+180: delta(1800,900)/180 -> 10/5
            V4Sample(5, 5, 2980, 1580),  # 桶 base+360: delta(180,180)/180 -> 1/1
            V4Sample(300, 90, 3880, 1760),  # 桶 base+540: delta(900,180)/180 -> 5/1
        ),
        (1000, 500),
    )
    store.append_records(
        "global",
        v4_epoch_date_str(base + 180),
        (base + 900, 180),
        (
            V4Sample(10, 10, 2740, 1940),  # 桶 base+720: dl 快照回落(重置, 新块立基线); up delta 180 -> 1
            V4NullRun(3, dt_ms=540000),  # 断连 3 槽: 桶 base+900/1080/1260 空
            V4Sample(12, 22, 3940, 2120, dt_ms=180000),  # 桶 base+1440(断链后基线缺失)
        ),
        (2740, 1940),
    )

    def point_at(body, bucket):
        return next((p for p in body["points"] if p and p["t"] == bucket), None)

    def total_at(body, bucket):
        return next((p for p in body["totals"] if p and p["t"] == bucket), None)

    r = client.get("/api/traffic/qb/global", headers=auth)
    assert r.status_code == 200
    body = r.json()
    # meta 全量形状(P4 新键 server_started_at 一并钉住; 值语义/兼容面由未启用空态用例专测)。
    # sample_interval_s = F6 只增键(plan 26-11-14-1313): 生效采样间隔 = 15 x main_tick 2.0s
    # (与桶宽 interval_s=180 分离 —— F1: 24h 桶宽 = 生效间隔的整倍加宽, 桶数 <= 500)
    assert body["meta"] == {
        "window": "24h",
        "interval_s": 180,
        "sample_interval_s": 30.0,
        "source": "qb",
        "stale": False,
        "server_started_at": _tq_meta._SERVER_STARTED_AT,
    }
    assert len(body["points"]) == 481  # 满窗栅格(26-11-14-1313 F3 floor+1 + F1: 180 | 86400 恒整倍, n 恒 481)
    # (F2 改判)样本 @base+180.. 点位归属落其所在格(旧 cell 键 = 桶键-180): 断言键整体 +180
    assert point_at(body, base + 180) == {"t": base + 180, "dl": 0, "up": 0}  # 窗内首点无基线: D4 豁免 0 线(非 null)
    assert point_at(body, base + 360) == {"t": base + 360, "dl": 10, "up": 5}  # 区间平均: delta(1800,900)/180
    assert point_at(body, base + 900) == {"t": base + 900, "dl": 0, "up": 1}  # dl 重置派不出 0 线 + up delta(180)/180
    assert point_at(body, base + 1080) is None  # 断连段: 连续空桶 = null(不连线)
    assert point_at(body, base + 1260) is None
    assert point_at(body, base + 1440) is None
    assert point_at(body, base + 1620) == {
        "t": base + 1620,
        "dl": None,
        "up": None
    }  # 洞后(未观测 540s > 60)基线缺失: 断链未知 -> null 不造数
    #   (issue 26-10-16-0954 修复语义: 修复前出 D4 0 线 -> 全窗只剩它一个非 null 值时前端孤点/值域塌)
    # totals: 桶 base+180 窗内首个有观测桶 -> 基线缺失 null; 相邻桶差分; 重置逐向独立; 断链后基线缺失
    assert total_at(body, base + 180) == {"t": base + 180, "dl": None, "up": None}
    assert total_at(body, base + 360) == {"t": base + 360, "dl": 1800, "up": 900}
    assert total_at(body, base + 540) == {"t": base + 540, "dl": 180, "up": 180}
    assert total_at(body, base + 720) == {"t": base + 720, "dl": 900, "up": 180}
    assert total_at(body, base + 900) == {"t": base + 900, "dl": None, "up": 180}  # dl 重置
    assert total_at(body, base + 1260) is None  # 断连桶
    assert total_at(body, base + 1620) == {"t": base + 1620, "dl": None, "up": None}  # 断链后基线缺失

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
    auth = _auth(mgr)
    _enable_qb_traffic(mgr, sample_interval_multiplier=15)  # main_tick=2.0 -> 15 x 2 = 30s 生效(与种子块 30s 桶宽一致)
    store = _qb_v4(mgr)
    now = int(time.time())
    b0 = ((now - 240) // 30) * 30  # 5m 窗内, 远离窗首/窗尾栅格边缘(种子外扩区无数据)
    # (F2 改判)块首移到 b0: 样本 @b0/30/60 点位归属落格 b0/b0+30/b0+60(旧 cell 键 = 桶键-30)
    store.append_records(
        "global",
        v4_epoch_date_str(b0),
        (b0, 30),
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
                    start_epoch=b0,
                    interval_s=30,
                    projected_ts=float(b0 + 90),
                    records=(V4Sample(8888, 8888, 3400, 1700), ),  # 槽 @b0+90 落格 b0+90: delta(600,300)/30 -> 20/10
                    open_run=None,
                )
        },
    )
    body = client.get("/api/traffic/qb/global", headers=auth, params={"window": "5m"}).json()

    def pt(seg, t):
        return next((p for p in body[seg] if p and p["t"] == t), None)

    assert body["meta"]["stale"] is False and body["meta"]["interval_s"] == 30
    assert body["meta"]["sample_interval_s"] == 30.0  # F6 只增键: 15 x main_tick 2.0s, 此处与桶宽恰等
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


def test_api_traffic_qb_raw_live_tail_hold_extension(web_env, monkeypatch):
    """(计划 26-11-14-1313 F4)raw 段窗活尾链端延伸: 端点向 v4_live_tail_slots 传 now(请求
    时刻, 冻结假钟钉死)与间隙上界 max(interval_s, 采样间隔) x 2 —— 采样链活跃时 holding
    槽豁免窗尾过滤, 响应尾桶(进行中桶)恒有观测且值接续末观测桶值(持有面 20/10, 瞬时
    垃圾字段 9999 零上图); totals 尾桶 0 增量(holding totals = 末次快照同值, 不造字节)。
    活尾纯内存(不落盘), 磁盘零块 -> 无真空缝, 差分链干净"""
    from auto_qb.core.traffic_store import LiveTail, V4Sample

    mgr, client = web_env
    auth = _auth(mgr)
    _enable_qb_traffic(mgr, sample_interval_multiplier=15)  # main_tick=2.0 -> 30s 生效(桶宽 30, 间隙上界 60)
    _qb_v4(mgr)  # 建 v4 目录(磁盘零块: 全部观测走活尾)
    now = int(time.time())
    if now % 30 == 0:
        # int 冻结钟特有边角(生产 float now 零测度不可达): now 恰落桶边界 -> hold 覆盖
        # [projected, now] 与进行中桶 [now, now+30) 零重叠 -> 尾桶 None(墙钟相位 1/30,
        # 提交闸门 26-11-15 实测撞红); +1s 偏离边界, 相位守卫后 gap 恒 != 30
        now += 1
    _freeze_traffic_endpoint_clock(monkeypatch, now)  # 端点取时单点冻结(用例与请求同一 now)
    # (F2 改判)末样本槽位恒距 now 30..59s(gap = now mod 30 + 30, 恒 <= 上界 60): holding 桶
    # (grid.last)与末样本桶恒隔一格 —— 纯持有桶 totals = 末次快照同值, delta 恒 0(不重计
    # 末样本已入账的增量); 旧「hold 覆盖与末样本桶重叠相位」下 0/600 摇摆的口径随覆盖几何退役
    projected = (now // 30) * 30 - 30
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
                        V4Sample(9999, 9999, 1600, 800),  # 槽 projected-60
                        V4Sample(9999, 9999, 2200, 1100),  # 槽 projected-30
                        V4Sample(9999, 9999, 2800, 1400),  # 槽 projected: delta(600,300)/30 -> 20/10
                    ),
                    open_run=None,
                )
        },
    )
    body = client.get("/api/traffic/qb/global", headers=auth, params={"window": "5m"}).json()
    assert body["meta"]["stale"] is False and body["meta"]["interval_s"] == 30
    last_pt = body["points"][-1]
    assert last_pt is not None and last_pt["dl"] == 20 and last_pt["up"] == 10  # 尾桶恒有观测(持有面)
    assert body["totals"][-1] is not None
    assert body["totals"][-1]["dl"] == 0 and body["totals"][-1]["up"] == 0  # holding 桶 0 增量
    assert all(p["dl"] < 1000 and p["up"] < 1000 for p in body["points"] if p is not None)  # 瞬时垃圾零上图


def test_api_traffic_qb_group_raw_live_tail_hold_extension(web_env, monkeypatch):
    """(计划 26-11-14-1313 F4)组端点 raw 段成员循环的延伸接线钉(与 global 用例同构):
    成员活尾挂在 torrent:HA(键 = TORRENT_KEY_PREFIX + 成员 hash), holding 槽豁免窗尾
    过滤 -> 组响应尾桶(进行中桶)恒有观测且值 = Σ 成员持有面(仅 HA 有活尾, HB 无行按
    0 计 -> 20/10); totals 尾桶 0 增量(holding totals = 末次快照同值, 不造字节)。
    组空态判据计入活尾(member_has_tail), 变异丢弃 now=/max_gap_s= 实参即红"""
    from auto_qb.core.traffic_store import LiveTail, V4Sample

    mgr, client = web_env
    auth = _auth(mgr)
    _enable_qb_traffic(mgr, sample_interval_multiplier=15)  # 30s 生效(桶宽 30, 间隙上界 60)
    _qb_v4(mgr)  # 磁盘零块: 观测面全部走成员活尾
    now = int(time.time())
    if now % 30 == 0:
        # 同 global 用例: int 冻结钟桶边界相位(墙钟 1/30)使 hold 覆盖与进行中桶零重叠,
        # 尾桶 None —— +1s 偏离边界(生产 float now 零测度不可达, 见 global 用例注)
        now += 1
    _freeze_traffic_endpoint_clock(monkeypatch, now)  # 端点取时单点冻结(用例与请求同一 now)
    # (F2 改判)末样本槽位恒距 now 30..59s(gap = now mod 30 + 30, 恒 <= 上界 60): holding 桶
    # (grid.last)与末样本桶恒隔一格 —— 纯持有桶 totals = 末次快照同值, delta 恒 0(不重计
    # 末样本已入账的增量); 旧「hold 覆盖与末样本桶重叠相位」下 0/600 摇摆的口径随覆盖几何退役
    projected = (now // 30) * 30 - 30
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
                        V4Sample(9999, 9999, 1600, 800),  # 槽 projected-60
                        V4Sample(9999, 9999, 2200, 1100),  # 槽 projected-30
                        V4Sample(9999, 9999, 2800, 1400),  # 槽 projected: delta(600,300)/30 -> 20/10
                    ),
                    open_run=None,
                )
        },
    )
    body = client.get(f"/api/traffic/qb/group/{encode_group_key(KEY)}", headers=auth, params={"window": "5m"}).json()
    assert body["meta"]["stale"] is False and body["meta"]["interval_s"] == 30
    last_pt = body["points"][-1]
    assert last_pt is not None and last_pt["dl"] == 20 and last_pt["up"] == 10  # 尾桶恒有观测(持有面)
    assert body["totals"][-1] is not None
    assert body["totals"][-1]["dl"] == 0 and body["totals"][-1]["up"] == 0  # holding 桶 0 增量
    assert all(p["dl"] < 1000 and p["up"] < 1000 for p in body["points"] if p is not None)  # 瞬时垃圾零上图


def test_api_traffic_qb_raw_seed_extension_window_start_baseline(web_env):
    """(计划 26-10-07-2127 S2/D3)窗首种子: read_window/v4_series_points 的 t0 外扩一个响应
    桶宽(grid.t0 - grid.interval)取前驱桶点作差分基线 —— 窗首桶 rate = delta/w(旧口径下
    是瞬时直采值; 无种子时是 D4 0 线), 瞬时垃圾值零上图; 种子点自身基线缺失且被 v4_grid_obs
    窗外过滤天然不外发。数据跨窗首等距等差铺放(逐桶 delta 恒 600/300), 对窗首 floor 对齐
    位置与端点取 now 的 ±1s 秒漂不敏感(断言值恒定)"""
    from auto_qb.core.traffic_store import V4Sample, v4_epoch_date_str

    mgr, client = web_env
    auth = _auth(mgr)
    _enable_qb_traffic(mgr, sample_interval_multiplier=15)  # main_tick=2.0 -> 15 x 2 = 30s 生效(与种子块 30s 桶宽一致)
    store = _qb_v4(mgr)
    now = int(time.time())
    first = (now - 300) - ((now - 300) % 30)  # 5m 窗栅格首桶(floor 对齐)
    totals = ((1000, 500), (1600, 800), (2200, 1100), (2800, 1400), (3400, 1700))
    # (F2 改判)种子 = 窗前样本 @first-30(读文件外扩区): 首个窗内桶的差分基线;
    # 旧「首样本 cell = 窗首桶」口径随 cell 几何退役 —— 点位归属下样本落其所在格
    store.append_records(
        "global",
        v4_epoch_date_str(first - 30),
        (first - 30, 30),
        tuple(V4Sample(9999, 9999, dl, up) for dl, up in ((400, 200), ) + totals),  # 瞬时字段全垃圾, 只看差分
        (400, 200),
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
    """(计划 26-10-07-2127 S2/D3; issue 26-10-16-0954 修复轮改口径)种子跨真空: 窗首前种子
    块与窗内恢复块之间程序停机(缝恰 60s = 重启缝) —— v4_series_points 既有真空判定出
    null 点断链, 恢复首桶按真实跨度摊配回收(覆盖份额口径: step 9600/4800 x 30 // span 90
    = 3200/1600 -> rate 107/53, 离线期字节不再单桶放大; 误接旧值 = 9600/30 = 320 可判红),
    次桶起基线恢复 delta/w; 离线字节不进 totals(恢复首桶 totals 基线缺失 null)"""
    from auto_qb.core.traffic_store import V4Sample, v4_epoch_date_str

    mgr, client = web_env
    auth = _auth(mgr)
    _enable_qb_traffic(mgr, sample_interval_multiplier=15)  # main_tick=2.0 -> 15 x 2 = 30s 生效(与种子块 30s 桶宽一致)
    store = _qb_v4(mgr)
    now = int(time.time())
    first = (now - 300) - ((now - 300) % 30)
    store.append_records(  # 窗前种子块: 单记录 @first-30(落格窗外, 读文件外扩区, 不外发)
        "global", v4_epoch_date_str(first - 30), (first - 30, 30), (V4Sample(1111, 1111, 1000, 500), ), (1000, 500)
    )
    store.append_records(  # 停机后恢复块(未观测恰 60s = 重启缝): 首记录 totals 已含离线期字节 9000/4500
        "global",
        v4_epoch_date_str(first + 60),
        (first + 60, 30),
        (
            V4Sample(9999, 9999, 10600, 5300),  # 槽 @first+60 落格 first+60: 缝后恢复点
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
    assert pt("points", first + 60) == {"t": first + 60, "dl": 107, "up": 53}  # 重启缝按真实跨度回收(误接旧值 320)
    assert pt("points", first + 90) == {"t": first + 90, "dl": 20, "up": 10}  # 基线恢复
    assert pt("points", first + 120) == {"t": first + 120, "dl": 20, "up": 10}
    assert all(p["dl"] < 1000 and p["up"] < 1000 for p in body["points"] if p is not None)  # 瞬时垃圾值零上图
    assert pt("totals", first + 60) == {"t": first + 60, "dl": None, "up": None}  # 离线字节不进 totals(基线缺失)
    assert pt("totals", first + 90) == {"t": first + 90, "dl": 600, "up": 300}
    assert all(p is None or (p["dl"] in (None, 600) and p["up"] in (None, 300)) for p in body["totals"])


def test_api_traffic_qb_raw_seed_vacuum_null_1s_edge_band(web_env, monkeypatch):
    """(issue 26-10-08-0141; issue 26-10-16-0954 修复轮改口径)窗首种子 1 秒边界带: 停机时刻
    落在 (seed_t0-1, seed_t0) 时真空 null 点 t = int(prev_chain_end) 取整后 = seed_t0-1
    恰落窗外 —— 修复前被丢弃, 种子点(覆盖桶触及窗首照收)与恢复首点之间差分链误接,
    离线期 qB 自行传输的字节被误归恢复首桶出假尖峰(rate 300 / totals 9000); 修复后标记
    保留并断链, 恢复首桶按真实跨度摊配回收(覆盖份额 9000/4500 x 30 // span 60 = 4500/2250
    -> rate 150/75, 误接旧值 300 可判红), 离线字节不进 totals。时钟钉死(1 秒带需确定性
    now; 端点 _grid 走 traffic_qb.SYSTEM_CLOCK 单点, patch 模块内单点名请求时现读)"""
    from types import SimpleNamespace

    from auto_qb.core.traffic_store import V4Sample, v4_epoch_date_str
    from auto_qb.webui.server import traffic_qb as tq

    mgr, client = web_env
    auth = _auth(mgr)
    _enable_qb_traffic(mgr, sample_interval_multiplier=15)  # main_tick=2.0 -> 15 x 2 = 30s 生效(与种子块 30s 桶宽一致)
    store = _qb_v4(mgr)
    fixed = 1_800_000_000.0  # 30 的整倍 -> 5m 窗栅格对齐(确定性几何)

    monkeypatch.setattr(tq, "SYSTEM_CLOCK", FakeClock(start=fixed))
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
    # (F2 改判)恢复样本 @g_t0+30 落格 g_t0+30: 接收桶 = step/实测对跨 60.5s = 148.76 -> 149
    # (误接旧值 300 可判红; 旧 ceil 口径 150/75)
    assert pt("points", g_t0 + 30) == {"t": g_t0 + 30, "dl": 149, "up": 74}
    assert pt("points", g_t0 + 60) == {"t": g_t0 + 60, "dl": 20, "up": 10}  # 次桶基线恢复 delta/覆盖
    assert all(p["dl"] < 1000 and p["up"] < 1000 for p in body["points"] if p is not None)  # 离线字节不单桶放大
    assert pt("totals", g_t0 + 30) == {"t": g_t0 + 30, "dl": None, "up": None}  # 离线字节不进 totals(修复前 = 9000)
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
    # (26-11-15-1104 F1 改判)24h 桶宽 = 30 x ceil(86400/15000) = 180(旧口径取 30), 数据节律随桶宽
    _enable_qb_traffic(mgr, sample_interval_multiplier=15)
    store = _qb_v4(mgr)
    now = int(time.time())
    base = ((now - 3600) // 180) * 180
    # 块首记录槽位恰在 base+180(w=180) -> 桶 base 1:1 对位
    store.append_records(
        "torrent:HA", v4_epoch_date_str(base + 180), (base + 180, 180), (V4Sample(500, 100, 5000, 1000), ),
        (5000, 1000)
    )
    body = client.get("/api/traffic/qb/torrent/HA", headers=auth).json()
    assert body["meta"]["source"] == "qb" and body["meta"]["stale"] is False
    p = next(p for p in body["points"] if p and p["t"] == base + 180)
    assert p == {"t": base + 180, "dl": 0, "up": 0}  # (F2 改判)单记录落格 base+180: 窗首无基线, D4 豁免 0 线(瞬时值不上图)
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
    """24h 窗端点面回归(§05.2): 只开窗口涉及的日期天文件(24h 窗恰 2 个, 窗外更早天文件
    零 open), agg.dat 亦不触。三档时钟: 真钟(钉在本用例入口时刻)+ 假钟本地 00:05(每天头
    10 分钟窗口, issue 26-10-20-0024)+ 假钟本地 00:00:15(当日首记录未入窗窗口, 2026-10-22
    跨日窗口抖动)"""
    from datetime import datetime, timedelta

    from auto_qb.core.traffic_grid import build_grid as tg_build_grid
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
    # (26-11-15-1104 F1 改判)生效间隔 30s: 24h 桶宽 = 180(旧口径 30), 本地 00:00(86400 整倍)
    # 仍是 180 的整倍 -> base 依旧恰为栅格桶键, 断言不变; 种子外扩镜像改走 build_grid 单点
    _enable_qb_traffic(mgr, sample_interval_multiplier=15)
    store = _qb_v4(mgr)
    now = int(_pinned)
    # base 恒取本地当日 00:00(30 对齐): 它必在 24h 窗内(窗尾是 now, 当日总在窗里)且恒落
    # involved 末日 —— 跨日长洞的 null 语义依赖这个前提。旧写法 ((now - 600) // 30) * 30
    # 在每天 00:00-00:10 会把 base 甩到前一日, 与 involved[0] 撞进同一天, 长洞不成立(判 0)
    base = v4_day_epoch(now)
    _mirror = tg_build_grid("24h", now, 30.0)  # 与端点 _grid 同参(生效间隔 30s)
    involved = sorted(v4_window_dates(_mirror.t0 - _mirror.interval, _mirror.t1))  # 镜像端点窗首种子外扩(S2/D3: t0 - 一个桶宽)
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
    # base 桶期望值按几何分档(窗尾 t1 = now, 当日首记录槽 base+30 的入窗条件 = base+30 < t1):
    # - now > base+30: 首记录在窗内, 与昨日块相隔约 24h -> 跨日长洞断链未知 -> null 字典;
    # - now <= base+30(00:00:00-00:00:30 窗口): 当日首记录还没到窗尾 -> 当日桶无观测 =
    #   空桶 null(生产正确形态: 那天尚未采样; 旧断言只认 null 字典, 这 30 秒必假红)
    # (F2 注)24h 桶宽 180: 记录 @base+30 点位归属落格 base(桶 [base, base+180) 恰含之,
    # 与旧 cell 键同位) —— 断言键不变
    entry = next((p for p in body["points"] if p and p["t"] == base), None)
    if now <= base + 30:
        assert entry is None, "当日首记录未入窗时 base 桶应为空桶"
    else:
        assert entry == {"t": base, "dl": None, "up": None}  # 跨日长洞: 断链未知 -> null(issue 26-10-16-0954 修复语义)


def test_api_traffic_qb_group_endpoint(web_env, monkeypatch):
    """分组端点读侧现算(观测面, §05.1/§05.4): Σ 成员均值 / 全员空闲(z 覆盖)出 0 线 /
    全员无观测(停机)整桶断线 —— 「借 global 判 null」退役: 全程零全局系列文件读取 /
    成员重置贡献 0 不拖垮全组 / 成员历史回溯可见 / 解析不到成员空态 / 畸形 key 400"""
    from auto_qb.core.traffic_store import V4Sample, V4ZeroRun, v4_epoch_date_str

    mgr, client = web_env
    auth = _auth(mgr)
    # (26-11-15-1104 F1 改判)窗口显式 5m + 生效间隔 30s: 桶宽 30(旧默认 24h 窗 si=2.0 桶宽
    # 也是 30, F1 后 24h@2s 采样桶宽 174 不再对位 30s 数据节律 —— 本用例钉组读侧语义而非
    # 窗口几何, 改显式 5m 窗保持 30s 桶栅格, 断言逐字不变)
    _enable_qb_traffic(mgr, sample_interval_multiplier=15)
    store = _qb_v4(mgr)
    now = int(time.time())
    base = ((now - 240) // 30) * 30  # 5m 窗内(远离窗首/尾; 24h 旧位 now-3600 在 5m 窗外)
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
    body = client.get(f"/api/traffic/qb/group/{enc}", headers=auth, params={"window": "5m"}).json()
    monkeypatch.undo()
    # 组端点无 global 依赖: 请求全程零 qb-traffic-v4/global/ 读取(本用例根本未造全局数据)
    assert not [p for p in _v4_opens(opened) if "/global/" in p]

    def pt(seg, t):
        return next((p for p in body[seg] if p and p["t"] == t), None)

    assert body["meta"]["source"] == "qb" and body["meta"]["stale"] is False
    # (F2 改判)样本 @bX+30 点位归属落格 bX+30(旧 cell 键 = 桶键-30): 断言键整体 +30
    assert pt("points", b1) == {"t": b1, "dl": 0, "up": 0}  # 双成员窗首点基线缺失 D4 0 线(回溯可见性不变: 桶非 null)
    assert pt("points", b2) == {"t": b2, "dl": 40, "up": 0}  # 区间平均: HA delta(1000)/30=33 + HB delta(200)/30=7
    assert pt("points", b3) == {"t": b3, "dl": 3, "up": 0}  # HA 重置派不出 0 线 + HB delta(100)/30=3
    assert pt("points", b4) == {"t": b4, "dl": 3, "up": 0}  # HA delta(100)/30=3, HB 无行按 0 计
    assert pt("points", b5) == {"t": b5, "dl": 0, "up": 0}  # HA z 覆盖空闲观测 -> 0 线(非 null)
    assert pt("points", b5 + 30) is None  # 全员无观测(停机)整桶断线 —— 成员观测面裁决, 不借 global
    assert pt("totals", b1) == {"t": b1, "dl": 0, "up": 0}  # 双成员窗内基线缺失 -> 0(不出洞)
    assert pt("totals", b2) == {"t": b2, "dl": 1200, "up": 0}  # HA +1000, HB +200
    assert pt("totals", b3) == {"t": b3, "dl": 100, "up": 0}  # HA 重置贡献 0(不是 -1500), HB +100
    assert pt("totals", b4) == {"t": b4, "dl": 100, "up": 0}  # HA +100, HB 无行基线缺失 0
    assert pt("totals", b5) == {"t": b5, "dl": 0, "up": 0}  # z 快照同值 delta=0
    assert pt("totals", b5 + 30) is None  # null 桶整桶 None
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


def test_api_traffic_qb_group_member_only_zruns_not_empty(web_env):
    """组空态判据观测面(§05.4 沿用): 成员只剩 z 块(raw 已滑出
    窗/从未活跃传输)不算「从未产过流量」—— z 覆盖是真实观测, 组出 0 线而非空态;
    全程不读全局系列(本用例未造任何全局数据)"""
    from auto_qb.core.traffic_store import V4ZeroRun, v4_epoch_date_str

    mgr, client = web_env
    auth = _auth(mgr)
    # (26-11-15-1104 F1 改判)同组端点用例: 显式 5m 窗 + 30s 生效间隔保持 30s 桶栅格(断言不变)
    _enable_qb_traffic(mgr, sample_interval_multiplier=15)
    store = _qb_v4(mgr)
    now = int(time.time())
    start = ((now - 240) // 30) * 30  # 5m 窗内(24h 旧位 now-600 在 5m 窗外)
    # 块首记录 = z 游程: 块首槽位恰在 start+30 -> 桶 start 1:1 对位
    store.append_records(
        "torrent:HA", v4_epoch_date_str(start + 30), (start + 30, 30), (V4ZeroRun(1, 100, 50), ), (100, 50)
    )
    body = client.get(f"/api/traffic/qb/group/{encode_group_key(KEY)}", headers=auth, params={"window": "5m"}).json()
    assert body["points"] != []  # 非空态: 只剩 z 覆盖的成员仍产出 points
    p = next(p for p in body["points"] if p and p["t"] == start + 30)
    assert p == {"t": start + 30, "dl": 0, "up": 0}  # (F2 改判)z 块槽 @start+30 落格 start+30: 空闲 0 线


# ---------- P1-T1.5 守卫与容错簇(计划 26-10-20-2101) ----------


def test_service_defensive_paths(web_env, monkeypatch):
    """读侧装配的防御面(直接驱动服务对象, 免端点样板):
    - limitscache 构造期预建(无惰性双构造面); 限速读失败 = 空注解面(不 500, 缺线不冒充空态)
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
