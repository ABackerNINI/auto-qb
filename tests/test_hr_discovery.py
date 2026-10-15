"""test_hr_discovery 测试计划: 发现服务 + 实例注册表 + 配对码(计划 26-10-14-1241 S2/S3/S6)

分四层:
1. 候选表与注册表(纯逻辑/文件): 连号候选与 65535 截断 / upsert+TTL 过滤 / 写路径剪枝超龄条目
   (死实例不永久堆积, 边界与 alive 同判据) / 缺文件与坏文件容忍 / 测试期路径隔离守阵
   (runtime 的注册表路径必须被 conftest 重定向到临时目录, 不许写用户真实 app-data);
2. 发现路由(纯逻辑): origin 门 403 / OPTIONS / 404 / 配对三门(缺=pairing_required,
   错=pairing_invalid, 对=200+no-store) / auto 生效分叉(回环免码, 非回环强制) / 凭证等价形态 /
   聚合与 TTL / 0.0.0.0 的 Host 头替换(只影响响应文本);
3. 生命周期(真绑定): 候选先绑先得(首位被占 ⇒ 实绑次位) / 三候选全占 ⇒ start False 不抛 +
   后台退避重试接管(占用者退出后一个周期内) / stop 幂等;
4. 配对码族 + runtime 接线: 展示码跨重启稳定 / 密钥文件生成与复用 / 删除即吊销 / 每来源
   失败计数超阈临时静默(C3) / runtime 构造与启动发现 / discovery_port=0 关闭 / 监听身份
   覆盖 host/discovery_port/pairing / 非回环 auto 的展示码 INFO 与发现门全流程 / 发现绑定
   失败不影响数据端点 / L0 热重载不重建发现对象。

真绑定用例一律用**动态空闲端口**当候选表基底 —— 全量并行(-n 8)下固定 18788 会被其它
worker 的同族用例占住, 候选轮换是特性而非碰撞。
"""
import json
import logging
import os
import re
import socket
import time

from auto_qb.hr.channel import pairing_display_code, pairing_needed, resolve_pairing_secret
from auto_qb.hr.discovery import (
    API_DISCOVER,
    PAIRING_HEADER,
    INSTANCE_TTL_S,
    HrDiscoveryServer,
    InstanceRegistry,
    default_registry_path,
    discovery_candidates,
)
from auto_qb.hr.runtime import HrRuntime
from test_hr_runtime import _FakeManager, make_config

ORIGIN = "chrome-extension://" + "a" * 32
TK = "t" * 48  # 测试用数据端点密钥(字面量本身无意义, 只验聚合透传)
SC = "s" * 48  # 测试用配对密钥(同上; 真生成路径由 runtime 用例走 resolve_pairing_secret)


def _free_port() -> int:
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    return port


def _hold_ports(ports):
    """占住一组端口(测试占位 socket); 返回句柄列表, 由调用方负责释放"""
    socks = []
    for p in ports:
        s = socket.socket()
        s.bind(("127.0.0.1", p))
        socks.append(s)
    return socks


def make_discovery(**overrides):
    """构造被测发现服务(默认: 回环 + 随机端口基底 + on 配对 + 密钥已注入)"""
    params = dict(
        host="127.0.0.1",
        port=_free_port(),
        entry_id="e" * 12,
        entry_name="inst-1",
        endpoint_fn=lambda: "http://127.0.0.1:51000",
        token=TK,
        registry=None,
        pairing="on",
        pairing_secret=SC,
        extension_id="",
    )
    params.update(overrides)
    return HrDiscoveryServer(**params)


def _get(srv, headers, path=API_DISCOVER):
    return srv.route("GET", path, headers)


# ---------- 1. 候选表与注册表 ----------


def test_candidates_consecutive_and_cap():
    assert discovery_candidates(18788) == [18788, 18789, 18790]
    assert discovery_candidates(65534) == [65534, 65535], "上限 65535 截断"
    assert discovery_candidates(65535) == [65535]
    assert discovery_candidates(0) == [], "0 = 关闭发现, 不产生候选(运行期不会走到, 防御性)"


def test_registry_upsert_and_ttl(tmp_path):
    reg = InstanceRegistry(str(tmp_path / "instances.json"))
    now = 1000.0
    reg.upsert(entry_id="a" * 12, name="one", endpoint="http://127.0.0.1:1", token="k1", ts=now)
    reg.upsert(entry_id="b" * 12, name="two", endpoint="http://127.0.0.1:2", token="k2", ts=now - 10)
    got = reg.alive(ttl=INSTANCE_TTL_S, now=now)
    assert [e["id"] for e in got] == ["a" * 12, "b" * 12], "两条都活着"
    # 同 id 再登记 = 覆盖(upsert), 不出双条; 续写条目追加在表尾(顺序即文件序)
    reg.upsert(entry_id="a" * 12, name="one", endpoint="http://127.0.0.1:11", token="k1", ts=now)
    got = reg.alive(ttl=INSTANCE_TTL_S, now=now)
    assert [e["endpoint"] for e in got] == ["http://127.0.0.1:2", "http://127.0.0.1:11"]
    # TTL 过滤: 超龄条目消失(b 落在 now-10, 5s 窗口外)
    assert [e["id"] for e in reg.alive(ttl=5.0, now=now)] == ["a" * 12]
    # 残条目(缺 token / 坏 ts)剔除, 不给扩展半条
    raw = json.loads((tmp_path / "instances.json").read_text(encoding="utf-8"))
    raw.append({"id": "c" * 12, "name": "bad", "endpoint": "http://x:3", "token": "", "ts": now})
    raw.append({"id": "d" * 12, "name": "bad2", "endpoint": "http://x:4", "token": "k", "ts": "最近"})
    (tmp_path / "instances.json").write_text(json.dumps(raw), encoding="utf-8")
    assert [e["id"]
            for e in reg.alive(ttl=INSTANCE_TTL_S, now=now)] == ["b" * 12, "a" * 12], "顺序 = 文件序(a 上次 upsert 追加到表尾)"


def test_registry_tolerates_missing_and_corrupt(tmp_path):
    reg = InstanceRegistry(str(tmp_path / "none.json"))
    assert reg.alive(ttl=INSTANCE_TTL_S, now=1.0) == [], "缺文件当空"
    (tmp_path / "none.json").write_text("{oops", encoding="utf-8")
    assert reg.alive(ttl=INSTANCE_TTL_S, now=1.0) == [], "坏 JSON 当空不抛"
    (tmp_path / "none.json").write_text('{"a": 1}', encoding="utf-8")
    assert reg.alive(ttl=INSTANCE_TTL_S, now=1.0) == [], "非列表形态当空"
    # 写路径自愈: upsert 一次后文件恢复合法列表
    reg.upsert(entry_id="a" * 12, name="n", endpoint="http://x:1", token="k", ts=1.0)
    data = json.loads((tmp_path / "none.json").read_text(encoding="utf-8"))
    assert [e["id"] for e in data] == ["a" * 12]


def test_default_registry_path_platform_shape():
    p = default_registry_path()
    assert os.path.basename(p) == "instances.json"
    assert "auto-qb-hr" in p


def test_registry_prunes_expired_on_upsert(tmp_path):
    """写路径剪枝(2026-10-16 用户实报「发现产生很多无关条目」的成因之一)

    只读时过滤(alive)不够: 死实例只是「看不见」, 文件仍无界增长(实报时累积到 684 条),
    且每次心跳都要整份读 + 整份写。upsert 顺手剪掉超龄条目, 边界与 alive 用同一条判据。
    """
    reg = InstanceRegistry(str(tmp_path / "instances.json"))
    now = 1000.0
    reg.upsert(entry_id="old" * 4, name="dead", endpoint="http://127.0.0.1:1", token="k1", ts=now - INSTANCE_TTL_S - 1)
    assert reg.alive(ttl=INSTANCE_TTL_S, now=now) == [], "超龄条目读时本就看不见"
    reg.upsert(entry_id="new" * 4, name="live", endpoint="http://127.0.0.1:2", token="k2", ts=now)
    raw = json.loads((tmp_path / "instances.json").read_text(encoding="utf-8"))
    assert [e["id"] for e in raw] == ["new" * 4], "写路径把它从文件里剪掉了(不只是读时过滤)"
    # 边界: 恰好等于 TTL 的条目仍在窗口内(与 alive 同判据, 不许差一)
    reg.upsert(entry_id="edge" * 3, name="edge", endpoint="http://127.0.0.1:3", token="k3", ts=now - INSTANCE_TTL_S)
    assert [e["id"] for e in reg.alive(ttl=INSTANCE_TTL_S, now=now)] == ["new" * 4, "edge" * 3]


def test_hr_registry_path_is_isolated_from_real_file(_isolated_hr_registry):
    """守阵: 测试期 runtime 用的注册表路径必须被 conftest 重定向到临时目录

    !为什么: 真实注册表在用户 `%LOCALAPPDATA%/auto-qb-hr/instances.json` 且**无界增长** ——
    条目 id 是 `sha1(data_dir)[:12]` 而测试的 data_dir 是每例唯一的 tmp_path ⇒ 每个用例都算
    「一个全新实例」, 实测跑一次 test_hr_runtime.py 就往真实文件追加 24 条死条目; 累积后被扩展
    「立即发现」整批采纳(列表全是无关实例、主实例指向死端口)。本守阵钉住「测试永不写真实注册表」
    这条纪律 —— 删掉或改坏 conftest 的 `_isolated_hr_registry` 夹具, 它就会红。
    """
    import auto_qb.hr.runtime as hr_runtime

    from auto_qb.hr.discovery import default_registry_path as real_path

    assert hr_runtime.default_registry_path() == _isolated_hr_registry
    assert _isolated_hr_registry != real_path(), "临时路径不得与真实 app-data 路径重合"


# ---------- 2. 发现路由 ----------


def test_route_origin_gate_403():
    srv = make_discovery()
    status, headers, body = _get(srv, {"Origin": "https://evil.example"})
    assert status == 403 and b"origin not allowed" in body
    assert "Access-Control-Allow-Origin" not in headers
    status, _h, _b = _get(srv, {"Origin": "chrome-extension://" + "b" * 32})
    assert status == 401, "其它扩展 origin 过 origin 门(未配 extension_id), 落到配对门"


def test_route_options_preflight_and_404():
    srv = make_discovery()
    status, headers, body = srv.route("OPTIONS", API_DISCOVER, {"Origin": ORIGIN})
    assert status == 204 and body == b""
    assert PAIRING_HEADER in headers["Access-Control-Allow-Headers"]
    assert headers["Access-Control-Allow-Origin"] == ORIGIN
    # 预检不要求配对码(浏览器预检不带自定义头)
    assert status == 204
    # 门序(计划 §04 S2): origin 门 -> 配对门 -> discover; 配对门作用于 discover 之外的路径
    status, _h, body = srv.route("POST", API_DISCOVER, {}, b"{}")
    assert status == 401 and json.loads(body) == {"error": "pairing_required"}, "配对门先于 404"
    status, _h, body = srv.route("POST", API_DISCOVER, {PAIRING_HEADER: pairing_display_code(SC)}, b"{}")
    assert status == 404 and b"not found" in body, "过配对门后非 GET 不受理"
    status, _h, body = _get(srv, {PAIRING_HEADER: pairing_display_code(SC)}, path="/api/hr/other")
    assert status == 404 and b"not found" in body


def test_pairing_gate_three_ways():
    srv = make_discovery()
    code = pairing_display_code(SC)
    # 缺码
    status, headers, body = _get(srv, {"Origin": ORIGIN})
    assert status == 401 and json.loads(body) == {"error": "pairing_required"}
    # 错码
    status, _h, body = _get(srv, {"Origin": ORIGIN, PAIRING_HEADER: "000000"})
    assert status == 401 and json.loads(body) == {"error": "pairing_invalid"}
    # 对码(展示码形态): 200 + no-store + 实例数组字段齐全
    status, headers, body = _get(srv, {"Origin": ORIGIN, PAIRING_HEADER: code})
    assert status == 200
    assert headers["Cache-Control"] == "no-store"
    payload = json.loads(body)
    assert payload["instances"] == [], "registry 未注入时给空清单"
    assert "server_time" in payload
    # 对码(凭证形态): 机器比对等价
    from auto_qb.hr.channel import pairing_credential

    status, _h, _b = _get(srv, {"Origin": ORIGIN, PAIRING_HEADER: pairing_credential(SC)})
    assert status == 200, "HMAC 凭证与展示码等价(无额外状态, 同一密钥现导)"


def test_pairing_auto_branches_by_host():
    assert pairing_needed("auto", "127.0.0.1") is False
    assert pairing_needed("auto", "::1") is False
    assert pairing_needed("auto", "localhost") is False
    assert pairing_needed("auto", "192.168.1.10") is True
    assert pairing_needed("auto", "10.0.0.5") is True
    assert pairing_needed("auto", "172.16.31.5") is True
    assert pairing_needed("on", "127.0.0.1") is True
    assert pairing_needed("off", "192.168.1.10") is False
    # auto + 回环 ⇒ 免码直通; auto + 私网 ⇒ 401 pairing_required
    loop = make_discovery(pairing="auto")
    assert loop.pairing_required is False
    status, _h, _b = _get(loop, {"Origin": ORIGIN})
    assert status == 200, "同机默认形态(回环 + auto)不需要配对码"
    priv = make_discovery(pairing="auto", host="192.168.1.10")
    status, _h, body = _get(priv, {"Origin": ORIGIN})
    assert status == 401 and json.loads(body) == {"error": "pairing_required"}


def test_discover_aggregates_and_filters(tmp_path):
    reg = InstanceRegistry(str(tmp_path / "instances.json"))
    now = time.time()  # 服务用真实时钟: 条目 ts 必须落真实时刻, TTL 过滤才可判
    reg.upsert(entry_id="a" * 12, name="one", endpoint="http://192.168.1.10:5001", token="k1", ts=now)
    # 过期条目直接落盘(超龄 b)
    raw = json.loads((tmp_path / "instances.json").read_text(encoding="utf-8"))
    raw.append(
        {
            "id": "b" * 12,
            "name": "two",
            "endpoint": "http://192.168.1.10:5002",
            "token": "k2",
            "ts": now - INSTANCE_TTL_S - 1
        }
    )
    (tmp_path / "instances.json").write_text(json.dumps(raw), encoding="utf-8")
    srv = make_discovery(registry=reg, pairing="off")
    status, _h, body = _get(srv, {"Origin": ORIGIN})
    assert status == 200
    payload = json.loads(body)
    assert [e["id"] for e in payload["instances"]] == ["a" * 12], "超 TTL 的条目被过滤"
    assert payload["instances"][0]["token"] == "k1", "token 随发现响应自动分发(免手抄)"


def test_wildcard_host_uses_request_host(tmp_path):
    reg = InstanceRegistry(str(tmp_path / "instances.json"))
    reg.upsert(entry_id="a" * 12, name="one", endpoint="http://192.168.1.10:5001", token="k1", ts=time.time())
    wild = make_discovery(registry=reg, pairing="off", host="0.0.0.0")
    status, _h, body = _get(wild, {"Origin": ORIGIN, "Host": "198.51.100.7:18788"})
    payload = json.loads(body)
    assert payload["instances"][0]["endpoint"] == "http://198.51.100.7:5001", "0.0.0.0 自述按请求 Host 头换主机部分"
    # Host 头缺失 ⇒ 原样返回(只影响响应文本, 不进任何判据)
    _s, _h, body = _get(wild, {"Origin": ORIGIN})
    assert json.loads(body)["instances"][0]["endpoint"] == "http://192.168.1.10:5001"
    specific = make_discovery(registry=reg, pairing="off", host="192.168.1.10")
    _s, _h, body = _get(specific, {"Origin": ORIGIN, "Host": "198.51.100.7:18788"})
    assert json.loads(body)["instances"][0]["endpoint"] == "http://192.168.1.10:5001", "具体 bind 地址优先"


# ---------- 3. 生命周期(真绑定) ----------


def test_start_binds_first_free_candidate():
    base = _free_port()
    holds = _hold_ports([base])
    srv = make_discovery(port=base)
    try:
        assert srv.start() is True
        assert srv.bound_port == base + 1, "首位被占 ⇒ 顺延次位(候选表先绑先得)"
        assert srv.started
    finally:
        srv.stop()
        for s in holds:
            s.close()


def test_start_all_busy_returns_false_and_retries():
    base = _free_port()
    candidates = discovery_candidates(base)
    holds = _hold_ports(candidates)
    srv = make_discovery(port=base)
    srv.retry_min_s = 0.05
    srv.retry_max_s = 0.1
    try:
        assert srv.start() is False, "三候选全占 ⇒ 不抛、返回 False(数据端点照常的语义)"
        assert not srv.started
        holds[0].close()  # 释放首位: 占用者退出
        deadline = time.monotonic() + 5.0
        while not srv.started and time.monotonic() < deadline:
            time.sleep(0.05)
        assert srv.started, "后台退避重试在占用者退出后接管(R6 翻转)"
        assert srv.bound_port == base, "接管绑定的正是释放出来的首位"
    finally:
        srv.stop()
        for s in holds:
            s.close()


def test_stop_is_idempotent_and_releases():
    base = _free_port()
    srv = make_discovery(port=base)
    assert srv.start() is True
    bound = srv.bound_port
    assert srv.stop() is True
    assert srv.stop() is True, "幂等"
    assert not srv.started and srv.bound_port == 0
    probe = socket.socket()
    try:
        probe.bind(("127.0.0.1", bound)), "端口已释放(可再次绑定)"
    finally:
        probe.close()


# ---------- 4. 配对码族 + runtime 接线 ----------


def test_pairing_display_code_shape_and_stability():
    code = pairing_display_code(SC)
    assert re.fullmatch(r"\d{6}", code), "6 位十进制"
    assert pairing_display_code(SC) == code, "同密钥跨重启稳定"
    assert pairing_display_code(SC + "x") != code, "不同密钥不同码"


def test_resolve_pairing_secret_creates_once(tmp_path):
    logger = logging.getLogger("probe.pairing")
    first = resolve_pairing_secret(str(tmp_path), logger=logger)
    path = tmp_path / "hr.pairing"
    assert path.exists()
    assert path.read_text(encoding="ascii").strip() == first, "密钥持久化, 重启复用同一值"
    assert resolve_pairing_secret(str(tmp_path), logger=logger) == first


def test_revocation_by_deleting_file(tmp_path):
    logger = logging.getLogger("probe.revoke")
    first = resolve_pairing_secret(str(tmp_path), logger=logger)
    (tmp_path / "hr.pairing").unlink()
    second = resolve_pairing_secret(str(tmp_path), logger=logger)
    assert second != first, "删除文件即吊销: 重新生成新密钥"
    assert pairing_display_code(first) != pairing_display_code(second), "旧展示码一并失效"


def test_pairing_flood_limit_silences_per_source(caplog):
    srv = make_discovery()
    with caplog.at_level(logging.DEBUG, logger="auto_qb.hr.server"):
        for _ in range(8):
            _get(srv, {"Origin": ORIGIN, PAIRING_HEADER: "000000"})
        warns = [r for r in caplog.records if r.levelno >= logging.WARNING]
        assert len(warns) == 2, [r.getMessage() for r in warns]
        assert "配对失败" in warns[0].getMessage()
        assert "临时静默" in warns[1].getMessage(), "第 6 次起(60s 窗口 5 次上限)转静默, 只报一次"
        caplog.clear()
        _get(srv, {"Origin": ORIGIN, PAIRING_HEADER: "000000"})
        warns2 = [r for r in caplog.records if r.levelno >= logging.WARNING]
        assert len(warns2) == 0, "仍在静默窗口内"


def _isolate_registry(monkeypatch, tmp_path) -> None:
    """把 runtime 命名空间的注册表路径单点指到 tmp: 测试不得写真实 app-data 注册表"""
    import auto_qb.hr.runtime as rt

    monkeypatch.setattr(rt, "default_registry_path", lambda: str(tmp_path / "instances.json"))


def test_runtime_builds_and_starts_discovery(tmp_path, monkeypatch):
    _isolate_registry(monkeypatch, tmp_path)
    base = _free_port()
    cfg = make_config(tmp_path, enabled=True, channel=True)
    cfg.hr_check.channel.discovery_port = base
    runtime = HrRuntime(_FakeManager(cfg))
    assert runtime.start() is True
    try:
        assert runtime.discovery is not None and runtime.discovery.started
        assert runtime.discovery.bound_port == base, "空闲基底 ⇒ 实绑首位"
        assert runtime.discovery.bound_port in runtime.discovery.candidates
        st = runtime.status()
        assert re.fullmatch(r"发现 \d+ · 配对 关 · 数据 \d+", st.channel.note), st.channel.note
        assert str(runtime.discovery.bound_port) in st.channel.note, "note 携带发现实绑端口(C6)"
    finally:
        runtime.stop()
    assert runtime.discovery is None, "stop 一并收掉发现服务"


def test_runtime_discovery_disabled_when_port_zero(tmp_path, monkeypatch):
    _isolate_registry(monkeypatch, tmp_path)
    cfg = make_config(tmp_path, enabled=True, channel=True)
    cfg.hr_check.channel.discovery_port = 0
    runtime = HrRuntime(_FakeManager(cfg))
    runtime.start()
    try:
        assert runtime.discovery is None
        st = runtime.status()
        assert st.channel.note.startswith("发现 关 · 配对 关 · 数据 "), st.channel.note
    finally:
        runtime.stop()


def test_runtime_identity_covers_new_keys(tmp_path):
    cfg = make_config(tmp_path, enabled=True, channel=True)
    ident = HrRuntime._identity(cfg.hr_check)
    cfg.hr_check.channel.host = "192.168.1.10"
    assert HrRuntime._identity(cfg.hr_check) != ident, "host 变 = 监听身份变"
    cfg.hr_check.channel.host = "127.0.0.1"
    cfg.hr_check.channel.discovery_port = 18790
    assert HrRuntime._identity(cfg.hr_check) != ident, "discovery_port 变 = 监听身份变"
    cfg.hr_check.channel.discovery_port = 18788
    cfg.hr_check.channel.pairing = "on"
    assert HrRuntime._identity(cfg.hr_check) != ident, "pairing 变 = 监听身份变"


def test_runtime_non_loopback_pairing_full_flow(tmp_path, caplog, monkeypatch):
    _isolate_registry(monkeypatch, tmp_path)
    """非回环 + auto: 密钥按需生成 + 展示码 INFO + 发现门全流程

    !不真绑私网地址: 本机无私网 NIC 时绑定报 10049, 且 sidefx 台账只放行回环绑定 ——
    配对门逻辑与端口绑定解耦, 走 _build()(只建不绑) + route() 纯逻辑; 真机跨机直绑
    归验收判据 V3 的真机步(本机 + LAN 别名)。
    """
    cfg = make_config(tmp_path, enabled=True, channel=True)
    cfg.hr_check.channel.host = "192.168.1.10"
    runtime = HrRuntime(_FakeManager(cfg))
    runtime._build()  # 只建不绑: 发现服务与配对密钥在此就绪, 端口尚未监听
    try:
        assert (tmp_path / "hr.pairing").exists(), "非回环 + auto ⇒ 需要配对, 密钥文件此时才生成"
        sec_val = (tmp_path / "hr.pairing").read_text(encoding="ascii").strip()
        code = pairing_display_code(sec_val)
        with caplog.at_level(logging.INFO, logger="auto_qb.hr"):
            runtime._advise_pairing()
        msgs = [r.getMessage() for r in caplog.records if "配对已生效" in r.getMessage()]
        assert any(code in m for m in msgs), "启动 INFO 带展示码(S3 展示面)"
        # 发现门全流程: 免码 401 pairing_required -> 对码过门(数据端点未监听 ⇒ 聚合为空, 不撒谎)
        assert runtime.discovery.pairing_required is True
        status, _h, body = runtime.discovery.route("GET", API_DISCOVER, {"Origin": ORIGIN})
        assert status == 401 and json.loads(body) == {"error": "pairing_required"}
        status, _h, body = runtime.discovery.route("GET", API_DISCOVER, {"Origin": ORIGIN, PAIRING_HEADER: code})
        assert status == 200
        assert json.loads(body)["instances"] == []
    finally:
        runtime.stop()


def test_runtime_discovery_bind_failure_keeps_data_endpoint(tmp_path, caplog, monkeypatch):
    _isolate_registry(monkeypatch, tmp_path)
    base = _free_port()
    holds = _hold_ports(discovery_candidates(base))
    cfg = make_config(tmp_path, enabled=True, channel=True)
    cfg.hr_check.channel.discovery_port = base
    runtime = HrRuntime(_FakeManager(cfg))
    try:
        with caplog.at_level(logging.WARNING, logger="auto_qb.hr.discovery"):
            runtime.start()
        try:
            assert runtime.endpoint is not None and runtime.endpoint.started, "发现全占 ⇒ 数据端点照常"
            assert runtime.discovery is not None and not runtime.discovery.started
            assert any("全部被占" in r.getMessage() for r in caplog.records), "明确日志(R2)"
            assert runtime.status().channel.note.startswith("发现 关 ·"), "note 如实反映发现不可用"
        finally:
            runtime.stop()
    finally:
        for s in holds:
            s.close()


def test_runtime_l0_rebuild_keeps_discovery(tmp_path, monkeypatch):
    _isolate_registry(monkeypatch, tmp_path)
    base = _free_port()
    cfg = make_config(tmp_path, enabled=True, channel=True)
    cfg.hr_check.channel.discovery_port = base
    runtime = HrRuntime(_FakeManager(cfg))
    runtime.start()
    try:
        before = runtime.discovery
        old = runtime.global_conf
        cfg.trackers["pt.example.com"].hr_check.refresh_interval = 6 * 3600.0
        runtime.apply(old)
        assert runtime.discovery is before, "L0 重建不重建发现对象(监听身份未变)"
        assert runtime.discovery.started
    finally:
        runtime.stop()
