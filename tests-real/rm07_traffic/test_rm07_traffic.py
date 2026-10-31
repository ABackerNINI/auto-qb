"""RM07 限速·流量曲线·全局流量 —— 十条真机用例(限速下发/曲线采样/流量源三态/重启缺口/工具状态面)。

验证面对准冻结计划 plans/26-10-31-1605-plan-real-RM07.html §03 的十条 spec:
未配流量源启动观察项收口(RM07-01)· 来源刷新三态 off/stale/ok(RM07-02)· 切源即刷新(RM07-03)·
限速曲线主链+改档对照(RM07-04)· 全局限速手动保护+退出恢复(RM07-05)· 曲线任务短路三路(RM07-06)·
qB 口径采样+重启尖峰缺口(RM07-07)· L2 互传真实速率聚合(RM07-08)· 采样间隔配比与关块重开(RM07-09)·
工具状态端点五态(RM07-10)。

代码实况落刀点(计划给意图, 这里按 src 实况):
- 全局限速的 qB 5.2 权威面 = **transfer 端点**(app/preferences 旧键 upload/download_limit 已失效,
  qbapi.py:349 注释): 读 `GET /transfer/{upload,download}Limit`(bytes/s), 写
  `PUT /transfer/set{Upload,Download}Limit`(表单 limit, bytes/s)。产品读回经
  bytes_to_kib_floor(整除向下), 手动保护判「奇数 KiB」(infra/utils.is_manual_speed_limit)。
  **预置/还原一律走 transfer 端点**, prefs 的 dl_limit/up_limit 只做伴随快照还原(§2.5 坑:
  两实例默认 dl_limit=1024 既是坑也是原值 —— global_limits fixture 快照还原, 不硬编码)。
- dat 格式(core/curves.py:48 parse_history_dat): 首行 `lines: N` 跳过; 行 = `YYYY/MM/DD 上传KB/下载KB`
  (KB=1024B); 坏行跳过计数; 重复日期取末行。
- 曲线档位 YAML(validation/curves.py): `curves: [{curve: {period, upload_curve/download_curve}}]`,
  点 = 单键映射 `"<阈值>": {upload_speed_limit|download_speed_limit: "<速度>"}`, 阈值严格递增
  (parse_fsize/parse_speed, iB 单位白名单)。
- 来源三态单点 traffic_snapshot_mod.refresh(): off 不读盘 / stale 清 history / ok 发布行;
  「切源即刷新」判定单点 paths.source_signature(commands.py:1350, PUT /api/config 前后各算一次,
  变了立刻投递 refresh_traffic 命令)。
- v4 采样文件(traffic_store.py §01): `<data_dir>/qb-traffic-v4/{global,torrents/<ih>}/<YYYY-MM-DD>.dat`;
  断言一律 parse_v4_day_text 读回(store 口径), 不咬文件二进制。
- 采样节拍: sample_interval 非 main_tick 整数倍 → ceil 取整 + WARNING 一次(D5); 变更 interval →
  关块重开(新旧块各有 interval_s); 块头 B 行 interval_s = **生效值**(ceil 后), 可从文件读回。
- 工具状态端点(traffic_monitor.py:206): 恒 200 + 结构化五态; 未就绪写端点 502。

计划 spec 的两处如实调整(按 src 实况, 详见基线切片):
- RM07-07 单种系列: 零传输种子不进采样集(_sample_torrents 数据门: 目录存在才采)—— L1 单实例
  造不出单种系列, 该面归 RM07-08(L2 互传真数据); 「暂停态种子进 null run」是**活跃但缺字段**
  分支(:831), 健康 qB 到不了, 如实记不硬凹;
- RM07-07 重启首窗 null(sample_series 基线空 → inc=None)只在**非零速率**路径可见, L1 全零流量
  下文件面只体现为「无 r 行无假增量」—— 重启后有真流量的首窗 null 面随 RM07-08 的 L2 语义覆盖。

跑法: `commands run real.suite -- --slice RM07 --yes`(不要裸 pytest)。真实种子全程非活跃;
假种子一律 real-fake 标签(死端口 announce, 零外连); 产品 data_dir 指用例临时目录, 不碰
auto-qb-data/; 配置一律 tests-real 派生 + schema_version: 5。
"""
from __future__ import annotations

import json
import os
import re
import shutil
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from auto_qb.core.traffic_store import V4Sample, parse_v4_day_text  # noqa: E402  (store 口径读回, 不咬二进制)
from lib import app, instances, torrent  # noqa: E402
from lib.net import local_host, is_local_url  # noqa: E402

pytestmark = [
    pytest.mark.skipif(sys.platform != "win32", reason="本片断言含 Windows 特有语义(taskkill/graceful 跑壳)"),
]

WORK = Path(__file__).resolve().parents[1] / ".work" / "rm07"
TAG = "real-fake"
_OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))  # 绕 HTTP_PROXY(127.0.0.1 不走代理)
ANNOUNCE_IP = f"http://{local_host()}:1/announce"  # 本机死端口: 连接即 RST, 零外连(§2.9)
TODAY = date.today()

LIMIT_PREF_KEYS = ("dl_limit", "up_limit", "alt_dl_limit", "alt_up_limit", "use_alt_speed_limits")


# ---------------------------------------------------------------- 基座

def case_dir(name: str) -> Path:
    d = WORK / name
    shutil.rmtree(d, ignore_errors=True)
    d.mkdir(parents=True, exist_ok=True)
    return d


def wait_until(fn, timeout: float, desc: str, interval: float = 0.4):
    """轮询到 fn() 为真值并返回它; 超时抛 AssertionError 带最后一次观测。"""
    deadline = time.time() + timeout
    last = None
    while time.time() < deadline:
        last = fn()
        if last:
            return last
        time.sleep(interval)
    raise AssertionError(f"等待超时({timeout}s): {desc}; 最后观测: {last}")


def log_text(case: Path) -> str:
    return app.read_log(case)


def count_log(case: Path, pattern: str) -> int:
    return len(re.findall(pattern, log_text(case)))


def assert_no_crash(case: Path) -> None:
    assert "Traceback" not in log_text(case), "产品日志出现未捕获异常堆栈"


CONFIG_TEMPLATE = """\
config:
    schema_version: 5
    qbittorrent:
        host: 127.0.0.1
        port: 36596
        username: ""
        password: ""
    data_dir: "{data_dir}"
    main_tick: {main_tick}
    sync_interval: 1.5S
    state_save_interval: 120S
    interval: 60S
    log:
        level: INFO
    grouping:
        enabled: false
    web:
        enabled: {web_enabled}
        host: 127.0.0.1
        port: {web_port}
        skip_local_verify: true
    notify:
        enabled: false
{extra}"""


def write_cfg(case: Path, *, web: bool = False, main_tick: str = "2S", extra: str = "") -> Path:
    """生成临时配置(schema_version: 5, 只指 36596 空库)。extra = 顶层段 YAML 文本(顶格书写,
    这里统一缩进 4 格挂到 config: 之下 —— 段落必须嵌在 config 键组内, 根节点只认 config)。"""
    data_dir = (case / "data").as_posix()
    cfg = case / "config.yml"
    indented = "".join(("    " + line if line.strip() else line) + "\n" for line in extra.splitlines())
    cfg.write_text(
        CONFIG_TEMPLATE.format(
            data_dir=data_dir,
            main_tick=main_tick,
            web_enabled="true" if web else "false",
            web_port=app.free_port(),
            extra=indented,
        ),
        encoding="utf-8",
    )
    text = cfg.read_text(encoding="utf-8")
    if "port: 36595" in text:
        raise AssertionError(f"配置指向了 36595(真实种子), 拒跑: {cfg}")
    if "schema_version: 5" not in text:
        raise AssertionError(f"配置缺 schema_version: 5(会触发迁移改写), 拒跑: {cfg}")
    return cfg


def traffic_source_section(enabled: bool = True, dat_path: str = "", refresh: str = "10S") -> str:
    return (
        "traffic_source:\n"
        f"    enabled: {'true' if enabled else 'false'}\n"
        "    provider: traffic_monitor\n"
        f"    refresh_interval: {refresh}\n"
        "    traffic_monitor:\n"
        f'        dat_path: "{dat_path}"\n'
    )


def qb_traffic_section(sample: str = "4S", flush: str = "60S") -> str:
    return (
        "qb_traffic:\n"
        "    enabled: true\n"
        f"    sample_interval: {sample}\n"
        f"    flush_interval: {flush}\n"
    )


def web_port_of(cfg: Path) -> int:
    """从生成的配置里取 web 端口(write_cfg 用 app.free_port() 现取, 用例要拿它打 API)。"""
    m = re.search(r"web:\n(?:[^\n]*\n)*?\s+port: (\d+)", cfg.read_text(encoding="utf-8"))
    assert m, f"配置里找不到 web 端口: {cfg}"
    return int(m.group(1))


def web_client(port: int):
    """产品 Web API 客户端(GET 返回 dict; 非 2xx 抛 HTTPError, 断言 502 时显式接)。"""

    def req(method: str, path: str, body: dict | None = None) -> dict:
        r = urllib.request.Request(
            f"http://127.0.0.1:{port}{path}",
            method=method,
            data=json.dumps(body).encode("utf-8") if body is not None else None,
        )
        if body is not None:
            r.add_header("Content-Type", "application/json")
        with _OPENER.open(r, timeout=20) as resp:
            return json.loads(resp.read().decode("utf-8"))

    return req


def traffic_view(port: int) -> dict:
    """轮询载荷里的流量快照(public 口径: 无 history 段)。"""
    return web_client(port)("GET", "/api/status")["traffic"]


def traffic_history(port: int) -> dict:
    return web_client(port)("GET", "/api/traffic/history")


def put_config(port: int, mutate) -> dict:
    """GET /api/config -> mutate(tree["config"]) -> PUT 回写(RM05-02 同款热重载配方)。"""
    req = web_client(port)
    tree = req("GET", "/api/config")["tree"]
    mutate(tree["config"])
    return req("PUT", "/api/config", {"tree": tree})


# ---------- dat 造数(parse_history_dat 口径: KB 单位, 首行 lines 声明) ----------

def write_dat(path: Path, rows: list[tuple[date, int, int]], bad_lines: tuple[str, ...] = ()) -> Path:
    """rows: [(日期, 上传KB, 下载KB)]; bad_lines: 故意造的坏行(坏行路径是验证面)。"""
    lines = [f"lines: {len(rows) + len(bad_lines)}"]
    lines += [f"{d:%Y/%m/%d} {up}/{down}" for d, up, down in rows]
    lines += list(bad_lines)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


# ---------- qB 全局限速(transfer 端点 = qB 5.2 权威面, 与产品 qbapi 同一路径) ----------

def global_limit_bytes(qb, direction: str) -> int:
    path = "/transfer/uploadLimit" if direction == "up" else "/transfer/downloadLimit"
    raw = qb._call(path).decode().strip()
    return int(raw) if raw not in ("", "-1") else 0


def set_global_limit_bytes(qb, direction: str, value_bytes: int) -> None:
    path = "/transfer/setUploadLimit" if direction == "up" else "/transfer/setDownloadLimit"
    body = urllib.parse.urlencode({"limit": str(int(value_bytes))}).encode()
    qb._call(path, body, "application/x-www-form-urlencoded")


@pytest.fixture()
def global_limits():
    """实例级全局偏好快照/还原(头号红线): 36596 的 transfer 两方向 + prefs 五键, 结束逐字还原。

    RM07-04/05/06/08 会改写(或依赖)36596 的全局限速 —— 忘还原会毒化后续所有片的
    L2 互传与真实种子行为(§2.5: 默认 dl_limit=1024 既是坑也是原值)。还原值取快照, 不硬编码。
    """
    qb = instances.make(36596)
    saved_prefs = {k: qb.prefs().get(k) for k in LIMIT_PREF_KEYS}
    saved = {"up": global_limit_bytes(qb, "up"), "down": global_limit_bytes(qb, "down")}
    yield qb
    set_global_limit_bytes(qb, "up", saved["up"])
    set_global_limit_bytes(qb, "down", saved["down"])
    qb.set_prefs(**saved_prefs)


@pytest.fixture()
def pin_limits():
    """L2 互传钉速(§2.5): 两实例限速临时钉 256 KiB/s(prefs 五键), 结束按快照逐字还原。

    与 tests-real/conftest.py 的 transfer_limits 同口径, 但不依赖 env fixture(本片用
    rm06 式只读基座); 与 global_limits 叠用时本 fixture 先还原 prefs, 全局 transfer 值
    由外层 global_limits 收口。
    """
    qbs = {port: instances.make(port) for port in (instances.PRIMARY, instances.SECONDARY)}
    saved = {port: {k: qb.prefs().get(k) for k in LIMIT_PREF_KEYS} for port, qb in qbs.items()}
    for qb in qbs.values():
        qb.set_prefs(dl_limit=256 * 1024, up_limit=256 * 1024, alt_dl_limit=256 * 1024,
                     alt_up_limit=256 * 1024, use_alt_speed_limits=False)
    yield 256 * 1024
    for port, qb in qbs.items():
        qb.set_prefs(**saved[port])


# ---------- 假种子(RM07-07/08 用; real-fake 标签, 幂等清场) ----------

def rm_all_fakes(qb) -> list[str]:
    """删 36596 上全部 real-fake 种子(幂等清场); 返回删掉的 hash。"""
    removed = []
    for t in qb.torrents():
        tags = {x.strip() for x in (t.get("tags") or "").split(",")}
        if "real-fake" in tags:
            qb.delete(t["hash"], delete_files=True)
            removed.append(t["hash"])
    return removed


def fake_seed(qb, name: str, size: int, savepath: Path, salt: str, announce: str = ANNOUNCE_IP,
              paused: bool = True) -> str:
    """造一枚 L1 假种子并加入实例(带 real-fake 标签; announce 缺省指本机死端口)。"""
    os.makedirs(savepath, exist_ok=True)
    raw, ih = torrent.build_stream(name, size, "random", salt, announce)
    qb.add_torrent(raw, str(savepath), paused=paused, tags=TAG, infohash_hint=ih)
    return ih


def tracker_urls(qb, ih: str) -> list[str]:
    """该种子的 http tracker 地址(滤掉 ** [DHT] ** 等伪条目, §2.5)。"""
    return [t["url"] for t in qb.trackers(ih) if str(t.get("url", "")).startswith("http")]


# ---------- v4 采样文件读回(store 口径) ----------

def day_file(data_dir: Path, series: str, infohash: str | None = None) -> Path:
    d = data_dir / "qb-traffic-v4" / ("global" if series == "global" else f"torrents/{infohash}")
    return d / f"{TODAY:%Y-%m-%d}.dat"


def parse_day(path: Path):
    return parse_v4_day_text(path.read_text(encoding="utf-8", errors="replace"))


def samples_of(parsed) -> list[V4Sample]:
    """全部块里的 r 记录。"""
    return [r for b in parsed.blocks for r in b.records if isinstance(r, V4Sample)]


# ================================================================ RM07-01


def test_rm07_01_unconfigured_source_startup_warning(global_limits):
    """[RM07-01] RM01 观察项收口: 未配流量源启动 → 「读取流量数据失败()」空路径 WARNING 仍复现且不崩

    前置: 缺省测试配置(不写 traffic_source 段 → enabled 缺省 True/dat_path 空); data_dir 独立
          临时目录; 无需种子; 36596 在线。
    副作用: 产品起停两次; 临时目录。
    回滚: 删临时目录; 实例无写(global_limits fixture 进出零改动)。
    失败判据: 无该 WARNING(行为已变 —— 如实回写锚件 §08 收口, 按实况定档); 启动崩溃或主循环
              不跑(高优 FAIL); WARNING 一次性不再现(节流语义与观察项矛盾, 记新事实)。
    """
    case = case_dir("rm07_01")
    seen = 0  # 跨启动累计的 WARNING 行数(日志追加式, 用增量判定「本次启动又打了」)
    for run in (1, 2):
        cfg = write_cfg(case, web=True)
        prev = seen
        p = app.start(cfg, case)
        try:
            assert p.wait_log("启动 qB 管理器", 40), f"第 {run} 次启动进程没起来:\n{p.log()[-800:]}"
            # 来源刷新任务 next_run=now, 首个任务线节拍即跑 → WARNING 应在启动后数秒内出现
            wait_until(lambda: count_log(case, r"读取流量数据失败\(\)") > prev, 20,
                       f"第 {run} 次启动未出现空路径 WARNING(计数 {prev} 未增长)")
            seen = count_log(case, r"读取流量数据失败\(\)")
            text = p.log()
            # 观察项原文(RM01 §04-6): 空路径形态 + 真实异常文本跟随其后(易带偏排查方向的形态)
            assert "流量快照 | 读取流量数据失败(): [Errno 2] No such file or directory: ''" in text, (
                f"WARNING 文案与观察项原文不符:\n{[l for l in text.splitlines() if '读取流量数据失败' in l]}")
            assert p.alive(), f"打完 WARNING 后进程退出(崩溃): rc={p.returncode()}"
            # 主循环照常跑完节拍: 来源快照按 stale 发布(Web 面), 而不是进程死掉
            port = web_port_of(cfg)
            wait_until(lambda: traffic_view(port).get("state") == "stale", 20, "来源快照未按 stale 发布")
            view = traffic_view(port)
            assert view["source"]["reasons"][0]["code"] == "dat_missing", f"原因码不符: {view['source']}"
            before = count_log(case, r"读取流量数据失败\(\)")
            time.sleep(8)  # 跨 ≥2 个主循环节拍 —— 缺省 600s 刷新间隔内同进程不重复刷
            assert count_log(case, r"读取流量数据失败\(\)") == before, "同进程内 WARNING 反复刷屏(与观察项的单轮语义不符)"
        finally:
            p.stop()
        assert_no_crash(case)
    # 重复启动每次都打: 两次启动后计数 >= 2(非一次性)
    assert count_log(case, r"读取流量数据失败\(\)") >= 2, "第二次启动未再打 WARNING(观察项「重复启动每次都打」失守)"


# ================================================================ RM07-02


def test_rm07_02_source_refresh_three_states():
    """[RM07-02] 来源刷新三态 off/stale/ok: 总开关关 → off 零读盘; 缺 dat → stale 清历史; 本地 dat → ok 发布

    前置: 基座 + 临时 dat(按 parse_history_dat 口径造: 今日行 + 上月行 + 1 坏行); 产品带 WEB。
    副作用: 产品起停一次; 临时 dat; 配置热改(traffic_source 段 ×3)。
    回滚: 删临时 dat + 配置随起停还原。
    失败判据: off 态仍打 WARNING(总开关闸门未拦); stale 态残留旧 history; ok 态聚合值与造行
              不符(parse 口径分叉); 断言咬内部实现而非日志/快照/HTTP(口径错)。
    """
    case = case_dir("rm07_02")
    missing = (case / "absent.dat").as_posix()
    dat_a = write_dat(
        case / "datA.dat",
        [(date(TODAY.year, TODAY.month - 1 if TODAY.month > 1 else 12, 28), 100, 200), (TODAY, 5120, 5120)],
        bad_lines=("这不是一行流量数据",),
    )
    p = None
    try:
        cfg = write_cfg(case, web=True, extra=traffic_source_section(enabled=False, dat_path=missing))
        p = app.start(cfg, case)
        assert p.wait_web(40), f"WEB 没起来:\n{p.log()[-600:]}"
        port = web_port_of(cfg)
        req = web_client(port)

        # ---- ① 总开关关: INFO off 文案 + 零 WARNING 零读盘 + periods/history 清空
        wait_until(lambda: "来源总开关关闭(traffic_source.enabled=false), 发布 off 快照" in p.log(), 20,
                   "off 态缺「来源总开关关闭」INFO")
        wait_until(lambda: traffic_view(port).get("state") == "off", 15, "顶层 state 未翻 off")
        view = traffic_view(port)
        assert view["source"]["state"] == "off", f"source 段不是 off: {view['source']}"
        assert view["source"]["reasons"][0]["code"] == "source_off", f"off 理由码不符: {view['source']}"
        assert "流量来源已关闭" in view["source"]["reasons"][0]["text"], f"off 理由文案不符: {view['source']}"
        assert view["periods"] == [], f"off 态 periods 未清空: {view['periods']}"
        assert traffic_history(port)["history"] == [], "off 态 history 未清空"
        assert count_log(case, r"读取流量数据失败") == 0, "off 态仍打了读取失败 WARNING(总开关未拦读盘)"

        # ---- ② 开关开 + dat 缺失: WARNING 带路径 + stale + 历史/累计清空
        resp = put_config(port, lambda c: c["traffic_source"].__setitem__("enabled", True))
        assert resp.get("applied") is True, f"PUT 未应用: {resp}"
        assert not resp.get("restart_required"), f"traffic_source 段被划 R 级(新事实): {resp}"
        wait_until(lambda: f"读取流量数据失败({missing})" in p.log(), 20, "stale 态缺带路径的 WARNING")
        wait_until(lambda: traffic_view(port).get("state") == "stale", 15, "顶层 state 未翻 stale")
        view = traffic_view(port)
        assert view["source"]["state"] == "stale" and view["source"]["reasons"][0]["code"] == "dat_missing", (
            f"stale 段不符: {view['source']}")
        # stale 语义: history 清空 + periods 归零行(_period_rows 对空行集产出 day/month 0/0, 非空列表)
        zeroed = {r["period"]: (r["up"], r["down"]) for r in view["periods"]}
        assert zeroed == {"day": (0, 0), "month": (0, 0)}, f"stale 态 periods 未归零: {view['periods']}"
        assert traffic_history(port)["history"] == [], "stale 态未清 history"

        # ---- ③ 指向本地 dat: ok + history/periods 与造行一致(KB×1024) + 坏行 WARNING
        resp = put_config(port, lambda c: c["traffic_source"]["traffic_monitor"].__setitem__("dat_path",
                                                                                              dat_a.as_posix()))
        assert resp.get("applied") is True, f"PUT 未应用: {resp}"
        prev_month = date(TODAY.year, TODAY.month - 1 if TODAY.month > 1 else 12, 28)
        expected = [
            {"date": f"{prev_month:%Y-%m-%d}", "up": 100 * 1024, "down": 200 * 1024},
            {"date": f"{TODAY:%Y-%m-%d}", "up": 5120 * 1024, "down": 5120 * 1024},
        ]
        wait_until(lambda: traffic_history(port)["history"] == expected, 20, "ok 态 history 行与造行不符")
        view = traffic_view(port)
        assert view["source"]["state"] == "ok", f"source 段不是 ok: {view['source']}"
        # 顶层 state 实测语义(2026-10-31): off 分支 publish_off 会把 limit 段复位 disabled,
        # 曲线未配置时没有发布者再动它, derive_state 优先级使顶层停在 "disabled" 而非 "ok"
        # —— 与 derive_state 的「曲线未启用 > 正常」格一致, 非缺陷; 来源段 ok 即本条判据。
        assert view["state"] == "disabled", f"顶层 state 实测语义偏离(见注释): {view['state']}"
        day_row = next(r for r in view["periods"] if r["period"] == "day")
        month_row = next(r for r in view["periods"] if r["period"] == "month")
        assert (day_row["up"], day_row["down"]) == (5120 * 1024, 5120 * 1024), f"今日聚合与造行不符: {day_row}"
        assert (month_row["up"], month_row["down"]) == (5120 * 1024, 5120 * 1024), (
            f"本月聚合未按自然月过滤(上月行混入?): {month_row}")
        wait_until(lambda: "流量数据 1 行无法解析已跳过" in p.log(), 10, "坏行未记 WARNING(坏行路径失守)")
        assert_no_crash(case)
    finally:
        if p is not None:
            p.stop()


# ================================================================ RM07-03


def test_rm07_03_source_switch_immediate_refresh():
    """[RM07-03] 流量源切换即刷新: dat_path 热改 → 配置一保存立刻换血, 不等 refresh_interval

    前置: 基座; 两份内容可区分的本地 dat(datA/datB); refresh_interval 配 600S —— 定时器
          10 分钟内不可能到期, 换血若发生只能来自「切源即刷新」触发(判据自证)。
    副作用: 产品起停一次; 临时 dat ×2; 热改配置(traffic_source.traffic_monitor.dat_path)。
    回滚: 删临时 dat; 配置随起停还原。
    失败判据: 切源后 10s 内不换血(要等 refresh_interval —— 「切源即刷新」契约破, FAIL);
              换血后行数/值仍是 datA(身份指纹没把 dat_path 算进判定); 回执报 restart_required。
    """
    case = case_dir("rm07_03")
    dat_a = write_dat(case / "datA.dat", [(TODAY, 1000, 2000)])
    dat_b = write_dat(case / "datB.dat", [(TODAY, 3000, 4000), (date(TODAY.year, TODAY.month, 1), 10, 20)])
    p = None
    try:
        cfg = write_cfg(case, web=True, extra=traffic_source_section(dat_path=dat_a.as_posix(), refresh="600S"))
        p = app.start(cfg, case)
        assert p.wait_web(40), f"WEB 没起来:\n{p.log()[-600:]}"
        port = web_port_of(cfg)
        expect_a = [{"date": f"{TODAY:%Y-%m-%d}", "up": 1000 * 1024, "down": 2000 * 1024}]
        expect_b = [
            {"date": f"{date(TODAY.year, TODAY.month, 1):%Y-%m-%d}", "up": 10 * 1024, "down": 20 * 1024},
            {"date": f"{TODAY:%Y-%m-%d}", "up": 3000 * 1024, "down": 4000 * 1024},
        ]
        wait_until(lambda: traffic_history(port)["history"] == expect_a, 20, "datA 初次发布未到位")
        assert traffic_view(port)["source"]["state"] == "ok"

        # ---- 热改 dat_path → datB: 判据是 10s 内换血(refresh_interval=600S, 定时器不可能到期)
        resp = put_config(port, lambda c: c["traffic_source"]["traffic_monitor"].__setitem__("dat_path",
                                                                                              dat_b.as_posix()))
        assert resp.get("applied") is True, f"PUT 未应用: {resp}"
        assert not resp.get("restart_required"), f"traffic_source 段被划 R 级(新事实, 如实记): {resp}"
        assert "traffic_source" in (resp.get("changes") or {}), f"回执 changes 未含 traffic_source: {resp}"
        wait_until(lambda: traffic_history(port)["history"] == expect_b, 10,
                   "切源后 10s 内未换血(600S 定时器不可能到期 ⇒ 「切源即刷新」契约破)")
        view = traffic_view(port)
        day_row = next(r for r in view["periods"] if r["period"] == "day")
        assert (day_row["up"], day_row["down"]) == (3000 * 1024, 4000 * 1024), f"periods 未换血为 datB: {day_row}"
        assert p.alive(), "切源过程进程退出"
        assert_no_crash(case)
    finally:
        if p is not None:
            p.stop()


# ================================================================ RM07-04

CURVE_MAIN = """\
global_speed_limit_curve:
    enabled: true
    interval: 3S
    curves:
        - curve:
            period: day
            upload_curve:
                - "10MiB":
                    upload_speed_limit: "2MiB/s"
            download_curve:
                - "10MiB":
                    download_speed_limit: "1MiB/s"
                - "50MiB":
                    download_speed_limit: "512KiB/s"
        - curve:
            period: month
            download_curve:
                - "1MiB":
                    download_speed_limit: "640KiB/s"
"""


def test_rm07_04_speed_curve_apply_and_retarget(global_limits):
    """[RM07-04] 限速曲线主链: 本地 dat 查档 → qB 全局限速下发 → 偶数 KiB 回读精确命中 → 改档跨档对照

    前置: 曲线配置(day 曲线 双方向 + month 曲线 下载, interval 3S)+ 本地 dat(今日 上5MiB/下5MiB);
          预置 qB 全局 下=1024KiB(偶)/上=0(不限), 原值已由 fixture 快照。
    副作用: 改写实例全局偏好 upload/download_limit(实例级, 影响 36596 全部传输); 临时 dat。
    回滚: global_limits fixture 按预置前快照还原(非想当然的 1024); 删临时 dat。
    失败判据: 回读≠目标(下发链路断, 高优 FAIL); actual 与 target 不一致且无 read_failed 原因码;
              改档后限速不动(查档/基线推进分叉); 收尾忘还原全局限速(测试侧事故, 立即修)。
    """
    case = case_dir("rm07_04")
    qb = global_limits
    dat = write_dat(case / "hist.dat",
                    [(date(TODAY.year, TODAY.month - 1 if TODAY.month > 1 else 12, 20), 500, 500), (TODAY, 5120, 5120)])
    set_global_limit_bytes(qb, "down", 1024 * 1024)  # 偶数 KiB 现场(非手动), 与目标 640 不同 → 必真写
    set_global_limit_bytes(qb, "up", 0)
    p = None
    try:
        cfg = write_cfg(case, web=True, extra=traffic_source_section(dat_path=dat.as_posix()) + CURVE_MAIN)
        p = app.start(cfg, case)
        assert p.wait_web(40), f"WEB 没起来:\n{p.log()[-600:]}"
        port = web_port_of(cfg)

        # ---- 第一档: 今日下 5MiB(<10MiB) → day 1024KiB; month(1MiB 阈, 5MiB 命中末档) 640KiB
        #      同向取最严 → 640; 上 5MiB(<10MiB) → 2048。偶数 KiB 回读精确命中。
        wait_until(lambda: global_limit_bytes(qb, "down") == 640 * 1024, 30, "下载全局限速未命中第一档 640KiB")
        wait_until(lambda: global_limit_bytes(qb, "up") == 2048 * 1024, 30, "上传全局限速未命中 2048KiB")
        assert "限速曲线 | 设置全局限速" in p.log(), "缺「设置全局限速」日志"
        assert "限速曲线 | 累计上传/下载" in p.log(), "缺「累计上传/下载」统计日志"
        limit = traffic_view(port)["limit"]
        assert limit["state"] == "ok", f"limit 段状态不符: {limit}"
        assert limit["target"] == {"up": 2048, "down": 640}, f"target 不符: {limit['target']}"
        assert limit["actual"] == limit["target"], f"actual 与 target 不一致且无 read_failed: {limit}"
        assert limit["reasons"] == [], f"正常轮不应有 reasons: {limit['reasons']}"

        # ---- 红验(改档对照): 今日下载跨档(20MiB, ≥10MiB 且 <50MiB) → day 512KiB, 最严合并仍 512
        write_dat(dat, [(date(TODAY.year, TODAY.month - 1 if TODAY.month > 1 else 12, 20), 500, 500),
                        (TODAY, 5120, 20480)])
        wait_until(lambda: global_limit_bytes(qb, "down") == 512 * 1024, 30, "改档后下载限速未跟到 512KiB(查档/基线推进分叉)")
        assert global_limit_bytes(qb, "up") == 2048 * 1024, "改档波及了上传方向(方向隔离破)"
        assert "512KiB/s" in p.log(), "改档后缺新档位日志"
        limit = traffic_view(port)["limit"]
        assert limit["target"] == {"up": 2048, "down": 512} and limit["actual"] == limit["target"], (
            f"改档后 limit 段不符: {limit}")
        assert_no_crash(case)
    finally:
        if p is not None:
            p.stop()


# ================================================================ RM07-05

CURVE_MANUAL = """\
global_speed_limit_curve:
    enabled: true
    interval: 3S
    curves:
        - curve:
            period: day
            upload_curve:
                - "1MiB":
                    upload_speed_limit: "1MiB/s"
            download_curve:
                - "1MiB":
                    download_speed_limit: "2MiB/s"
"""


def test_rm07_05_speed_curve_manual_protection(global_limits):
    """[RM07-05] 全局限速手动保护: 预置奇数 KiB → 曲线命中但 skip 不覆盖; 改回偶数 → 覆盖恢复

    前置: 曲线配置(下目标 2048KiB / 上目标 1024KiB, interval 3S)+ 本地 dat; 预置 qB 全局
          下=1025KiB(奇数 = 疑似手动)/上=0(偶数不限速); 原值已由 fixture 快照。
    副作用: 全局偏好被预置/还原; 临时 dat。
    回滚: global_limits fixture 按预置前快照还原; 删临时 dat。
    失败判据: 奇数被覆盖(手动保护失效, 高优 FAIL); upload 侧被连带跳过(逐方向独立破);
              改偶数后仍不覆盖(退出路径断, 红验不红 → 如实降档); 断言咬内部枚举而非 reasons/qB 回读。
    """
    case = case_dir("rm07_05")
    qb = global_limits
    dat = write_dat(case / "hist.dat", [(TODAY, 5120, 5120)])
    set_global_limit_bytes(qb, "down", 1025 * 1024)  # 奇数 KiB = 手动现场
    set_global_limit_bytes(qb, "up", 0)
    p = None
    try:
        cfg = write_cfg(case, web=True, extra=traffic_source_section(dat_path=dat.as_posix()) + CURVE_MANUAL)
        p = app.start(cfg, case)
        assert p.wait_web(40), f"WEB 没起来:\n{p.log()[-600:]}"
        port = web_port_of(cfg)

        # ---- 奇数方向: ≥2 个曲线轮原值 1025 原样; reasons 含 code=manual + 观察文案
        wait_until(lambda: "下载限速当前 1025KiB/s 为奇数" in p.log(), 20, "手动保护未记 INFO(≥2 轮内)")
        time.sleep(7)  # 再跨 ≥2 轮(interval 3S), 给「不覆盖」足够的机会窗口
        assert global_limit_bytes(qb, "down") == 1025 * 1024, "奇数全局限速被曲线覆盖(手动保护失效, 高优 FAIL)"
        limit = traffic_view(port)["limit"]
        manual = [r for r in limit["reasons"] if r.get("code") == "manual"]
        assert manual and manual[0]["dir"] == "down", f"reasons 缺 code=manual(down): {limit['reasons']}"
        assert "1025KiB/s 为奇数(疑似手动设置), 本轮不覆盖" in manual[0]["text"], f"manual 文案不符: {manual[0]}"
        assert limit["state"] == "ok" and limit["target"]["down"] == 2048, f"命中手动时 limit 段不符: {limit}"
        # 日志节流: 同一状态每 1h 才提醒一次 —— 短窗内恰好 1 条 INFO, 不逐轮刷屏
        time.sleep(6)
        assert count_log(case, r"下载限速当前 1025KiB/s 为奇数") == 1, (
            f"手动保护 INFO 逐轮刷屏(节流失守): {count_log(case, r'下载限速当前 1025KiB/s 为奇数')} 条")
        # 同轮 upload 侧(偶数 0)照常下发 —— 逐方向独立
        wait_until(lambda: global_limit_bytes(qb, "up") == 1024 * 1024, 30, "upload 侧被连带跳过(逐方向独立破)")
        assert not [r for r in traffic_view(port)["limit"]["reasons"] if r.get("code") == "manual" and r["dir"] == "up"], \
            "upload 侧出现 manual 理由(0 是偶数, 不该命中)"

        # ---- 红验(退出恢复): 改回偶数 1024 → 下一轮覆盖恢复 + reasons 清 + 节流记忆清
        set_global_limit_bytes(qb, "down", 1024 * 1024)
        wait_until(lambda: global_limit_bytes(qb, "down") == 2048 * 1024, 30, "改偶数后仍未覆盖(退出路径断, 红验不红)")
        assert not [r for r in traffic_view(port)["limit"]["reasons"] if r.get("code") == "manual"], (
            "退出手动保护后 reasons 未清")
        assert_no_crash(case)
    finally:
        if p is not None:
            p.stop()


# ================================================================ RM07-06


def test_rm07_06_curve_short_circuit_three_ways(global_limits):
    """[RM07-06] 曲线任务短路三路: enabled=false → disabled 零触碰; 来源关 → REQUEUE 零发布; dry-run → 零 qB 写

    前置: 基座 + 临时 dat + 三份变体配置(各自独立起停); 每路都预置 下=1024KiB(偶, 若误写即可见)。
    副作用: 产品起停 ×3; 临时目录 ×3。
    回滚: 删临时目录; global_limits fixture 逐路还原。
    失败判据: 任一短路路径仍写 qB 偏好(保守默认破, 高优 FAIL); enabled=false 仍读 dat(S1/D1 闸门
              失守); dry-run 出现 actual 读数或 qB 写。
    """
    case = case_dir("rm07_06")
    qb = global_limits
    dat = write_dat(case / "hist.dat", [(TODAY, 5120, 5120)])
    port = None
    p = None
    try:
        # ---- ① curve.enabled=false: publish disabled, 不读 dat 不写 qB(偏好原值)
        set_global_limit_bytes(qb, "down", 1024 * 1024)
        cfg = write_cfg(case, web=True, extra=traffic_source_section(dat_path=dat.as_posix())
                        + "global_speed_limit_curve:\n    enabled: false\n    interval: 3S\n    curves:\n"
                          "        - curve:\n            period: day\n            download_curve:\n"
                          '                - "1MiB":\n                    download_speed_limit: "640KiB/s"\n')
        p = app.start(cfg, case)
        assert p.wait_web(40), f"WEB 没起来:\n{p.log()[-600:]}"
        port = web_port_of(cfg)
        wait_until(lambda: traffic_view(port)["limit"]["state"] == "disabled", 20, "limit 段未落 disabled")
        time.sleep(8)  # 再跨 ≥2 个曲线轮, 给「误写」足够的机会窗口
        assert global_limit_bytes(qb, "down") == 1024 * 1024, "enabled=false 仍写了 qB 偏好(保守默认破, 高优 FAIL)"
        assert "设置全局限速" not in p.log(), "enabled=false 出现下发日志"
        assert count_log(case, r"读取流量数据失败") == 0, "enabled=false 仍读 dat 报错"
        view = traffic_view(port)
        assert view["state"] == "disabled" and view["limit"]["target"] == {"up": None, "down": None}, (
            f"disabled 语义不符: {view}")
        p.stop()
        p = None

        # ---- ② traffic_source.enabled=false: 曲线任务 REQUEUE 零发布, 来源模块发 off
        cfg = write_cfg(case, web=True, extra=traffic_source_section(enabled=False, dat_path=dat.as_posix())
                        + CURVE_MANUAL)
        p = app.start(cfg, case)
        assert p.wait_web(40), f"WEB 没起来:\n{p.log()[-600:]}"
        wait_until(lambda: "来源总开关关闭(traffic_source.enabled=false), 发布 off 快照" in p.log(), 20,
                   "关源后来源模块未发 off")
        time.sleep(8)
        assert count_log(case, r"限速曲线 \|") == 0, "关源后曲线任务仍有日志/发布(A4「谁写 state」双作者破)"
        assert global_limit_bytes(qb, "down") == 1024 * 1024, "关源后曲线仍写了 qB 偏好(高优 FAIL)"
        port = web_port_of(cfg)
        assert traffic_view(port)["state"] == "off", "关源后顶层 state 不是 off"
        p.stop()
        p = None

        # ---- ③ --dry-run + 全配置: 零 qB 写(dry-run 不启 WEB, 经进程边界 + 日志观测, §2.7)
        set_global_limit_bytes(qb, "down", 1024 * 1024)
        cfg = write_cfg(case, web=True, extra=traffic_source_section(dat_path=dat.as_posix()) + CURVE_MANUAL)
        p = app.start(cfg, case, dry_run=True, graceful_after=15)
        rc = p.wait(60)
        assert rc == 0, f"dry-run 进程退出码 {rc}:\n{p.log()[-600:]}"
        assert global_limit_bytes(qb, "down") == 1024 * 1024, "dry-run 写了 qB 全局限速(零写破, 高优 FAIL)"
        assert "设置全局限速" not in p.log(), "dry-run 出现下发日志"
        assert "读取流量数据失败" not in p.log(), "dry-run 连 dat 都没读到(曲线任务未按 dry_run 口径跑)"
        assert_no_crash(case)
    finally:
        if p is not None:
            p.stop()


# ================================================================ RM07-07


def test_rm07_07_qb_traffic_sample_restart_gap():
    """[RM07-07] qB 口径采样主链 + 重启缺口: 采样落 v4 store → 产品重启 → 恢复采样无假增量无重置审计

    前置: qb_traffic 配置(sample 4S=main_tick 2S 整数倍, flush 60S)+ 1 枚假种子(零传输)在 36596。
    副作用: 1 假种子; v4 采样文件落临时 data_dir; 产品两轮起停(各 graceful)。
    回滚: 删自造种子 + 删临时目录。
    失败判据: 重启后采样文件出现非零增量块(假尖峰, 「重启尖峰缺口」验证面 FAIL); 产品重启后采样
              不恢复(catch-up 链路断); 无计数器重置时出现 reset_log 审计行; 断言咬文件内部二进制
              而非 store 读回(口径错)。
    (spec 调整见模块 docstring: 单种系列/首窗 null 的可见面归 RM07-08 的 L2 真流量。)
    """
    case = case_dir("rm07_07")
    qb = instances.make(36596)
    assert not rm_all_fakes(qb), "开跑前 36596 有 real-fake 残留, 先清场"
    ih = None
    p = None
    try:
        ih = fake_seed(qb, "rm07c7.bin", 256 * 1024, WORK / "rm07_07", "rm07c7")
        cfg = write_cfg(case, web=False, main_tick="2S", extra=qb_traffic_section(sample="4S", flush="60S"))
        data_dir = case / "data"

        # ---- 第一轮: 采样跑 ~75s(≥1 个 flush 窗), graceful 退出 → stop 钩子封游程 + 落盘
        p = app.start(cfg, case, graceful_after=75)
        assert p.wait(150) == 0, f"第一轮未优雅退出:\n{p.log()[-600:]}"
        gf = day_file(data_dir, "global")
        assert gf.is_file(), f"全局系列天文件未落盘: {sorted(data_dir.rglob('*.dat'))}"
        parsed = parse_day(gf)
        assert parsed.key == "global" and parsed.bad_lines == 0, f"天文件解析异常: key={parsed.key} bad={parsed.bad_lines}"
        assert parsed.blocks, "天文件无任何块"
        assert all(b.interval_s == 4.0 for b in parsed.blocks), \
            f"块头 interval_s != 生效值 4s: {[b.interval_s for b in parsed.blocks]}"
        assert not samples_of(parsed), f"零流量却出现 r 行(假增量): {[r for r in samples_of(parsed)][:3]}"
        # 零传输种子不进采样集(数据门): 单种系列目录不存在 —— 按 src 实况的空态语义(见 docstring)
        assert not day_file(data_dir, "torrent", ih).is_file(), "零传输种子出现了单种系列(与数据门语义矛盾)"

        # ---- 第二轮: 重启 → 恢复(catch-up)→ 采样照常 → 同文件续写, 无假增量无重置审计
        p = app.start(cfg, case, graceful_after=75)
        assert p.wait(150) == 0, f"第二轮未优雅退出:\n{p.log()[-600:]}"
        log = p.log()
        assert "流量采样 | 启动恢复开始" in log, "重启后缺「启动恢复开始」(恢复链路未跑)"
        assert re.search(r"流量采样 \| 启动恢复完成: 1 系列", log), (
            f"重启后未恢复现存系列(catch-up 链路断):\n{[l for l in log.splitlines() if '启动恢复' in l]}")
        assert "计数器重置" not in log, "无计数器重置却出现 reset_log 审计行"
        parsed2 = parse_day(gf)
        assert parsed2.bad_lines == 0, f"重启续写引入坏行: bad={parsed2.bad_lines}"
        assert len(parsed2.blocks) >= 2, f"重启后未开新块(块数 {len(parsed2.blocks)})"
        assert not samples_of(parsed2), "重启后出现非零增量 r 行(假尖峰, 「重启尖峰缺口」验证面 FAIL)"
        assert_no_crash(case)
    finally:
        if ih:
            qb.delete(ih, delete_files=True)
        if p is not None:
            p.kill()


# ================================================================ RM07-08


def test_rm07_08_l2_transfer_sampling(primary, secondary, tracker, workdir, global_limits, pin_limits):
    """[RM07-08] L2 互传真实速率聚合: 采样随互传增长 → 单种系列累计 ≥ payload → 全局系列出非零 r 行

    前置: 双实例 + 本地伪 tracker(回对端 peer)+ pin_limits 钉 256KiB/s + 产品 qb_traffic 采样
          (sample 4S / flush 60S)连 36596; 假种子 announce 指本地伪 tracker。
    副作用: 两实例各 1 假种子(4MB 互传); 实例限速被 fixture 临时改写; v4 采样文件落临时 data_dir。
    回滚: finally 两端 delete(delete_files=True) + pin_limits/global_limits 还原 + 删临时目录。
    失败判据: 互传零字节(连不上自己 —— §2.5 伪 tracker 排除请求者/监听端口坑, 排不通记 BLOCKED);
              聚合不增长(采样或聚合装配断); 钉速没生效导致白等超时(测试侧事故)。
    """
    case = case_dir("rm07_08")
    payload = 4 * 1024 * 1024  # 256KiB/s 钉速下 ≈16s 传输, 够 ≥10s 的 dlspeed>0 观测窗
    data = torrent.payload(size=payload, seed=b"auto-qb-rm07-l2")
    raw, ih = torrent.build("rm07-l2.bin", data, tracker.url)
    src, dst = workdir / "seed", workdir / "leech"
    torrent.write_payload(str(src), "rm07-l2.bin", data)
    dst.mkdir(parents=True, exist_ok=True)
    assert not rm_all_fakes(secondary) and not rm_all_fakes(primary), "开跑前有 real-fake 残留, 先清场"
    p = None
    try:
        seed_port = int(primary.prefs()["listen_port"])
        tracker.peers = [(local_host(), seed_port)]
        primary.add_torrent(raw, savepath=str(src), paused=False, infohash_hint=ih)
        secondary.add_torrent(raw, savepath=str(dst), paused=False, infohash_hint=ih)
        cfg = write_cfg(case, web=True, extra=qb_traffic_section(sample="4S", flush="60S"))
        p = app.start(cfg, case)
        assert p.wait_web(40), f"WEB 没起来:\n{p.log()[-600:]}"
        port = web_port_of(cfg)
        req = web_client(port)

        # ---- 互传: leech dlspeed>0 持续 ≥10s(RM00 口径); 全程只打本地 tracker
        # totals 段语义 = 相邻桶快照差分(series_totals_points): 按桶时间戳合并去重后求和
        # 才是真「累计增量」, 轮询窗口滑动不能直接拿 max 当增长信号。
        up_seconds, buckets, growth, done = 0, {}, [], None
        deadline = time.time() + 180
        while time.time() < deadline:
            t2 = secondary.torrent(ih)
            if t2 and t2["dlspeed"] > 0:
                up_seconds += 1
            if t2 and t2["progress"] >= 1.0:
                done = t2
                break
            try:  # 采样活尾: /api/traffic/qb/global 的 totals 随互传增长(零 flush 依赖)
                for x in req("GET", "/api/traffic/qb/global?window=1m")["totals"]:
                    if x and (x.get("dl") or 0) > 0:
                        buckets[x["t"]] = max(buckets.get(x["t"], 0), x["dl"])
                cum = sum(buckets.values())
                if not growth or cum > growth[-1][1]:
                    growth.append((time.time(), cum))
            except Exception:
                pass
            time.sleep(1)
        assert done is not None, (
            f"180s 未完成: leech={secondary.torrent(ih)} / seed={primary.torrent(ih)} / announce={tracker.count(ih)}")
        assert up_seconds >= 10, f"leech dlspeed>0 只观测到 {up_seconds}s(需 ≥10s)"
        assert len(growth) >= 3 and growth[-1][1] > growth[0][1], (
            f"今日聚合字节未随互传增长(采样或聚合装配断): growth={growth[:5]}…共 {len(growth)} 步")

        # ---- flush(≤60s)后: 单种系列天文件落盘, dl_total 累计 ≥ payload; 全局系列出非零 r 行
        tf = day_file(case / "data", "torrent", ih)
        wait_until(lambda: tf.is_file(), 120, f"单种系列天文件未落盘: {sorted((case / 'data').rglob('*.dat'))}")
        tparsed = parse_day(tf)
        assert tparsed.bad_lines == 0, f"单种天文件坏行: {tparsed.bad_lines}"
        tsamples = samples_of(tparsed)
        assert tsamples, "单种系列无任何 r 行(互传了却没采样)"
        assert max(r.dl_total for r in tsamples) >= payload, (
            f"单种 dl_total 累计不足: {max(r.dl_total for r in tsamples)} < {payload}")
        assert any(r.dl_rate > 0 for r in tsamples), "单种系列无非零速率行"
        gf = day_file(case / "data", "global")
        wait_until(lambda: gf.is_file(), 120, "全局系列天文件未落盘")
        gsamples = samples_of(parse_day(gf))
        assert any(r.dl_rate > 0 for r in gsamples), "全局系列无非零下载速率 r 行"
        # 零外连: 两端 tracker 全本地
        for label, qbx in (("seed", primary), ("leech", secondary)):
            urls = tracker_urls(qbx, ih)
            assert urls and all(is_local_url(u) for u in urls), f"{label} 端 tracker 含非本机地址: {urls}"
        assert_no_crash(case)
    finally:
        primary.delete(ih, delete_files=True)
        secondary.delete(ih, delete_files=True)
        if p is not None:
            p.stop()


# ================================================================ RM07-09


def test_rm07_09_sample_interval_ratio_and_reblock():
    """[RM07-09] 采样间隔配比与关块重开: 非整倍 → WARNING+取整生效; 热改 interval → 关块重开; 装载期负向

    前置: 三组配置变体(各自独立起停); ①③ 零种子, ② 零种子。
    副作用: 产品起停 ×2 + run_cli ×3; v4 采样文件落临时 data_dir。
    回滚: 删临时目录。
    失败判据: 非整倍无 WARNING(D5 告警记忆缺失); 取整未生效(块头 interval_s != ceil 值);
              关块重开后旧块尾部数据丢/坏行(封口分叉); 非法配置被静默接受(fail-fast 破, 高优 FAIL)。
    """
    case = case_dir("rm07_09")
    p = None
    try:
        # ---- ① 非整倍(3S vs main_tick 2S): WARNING 恰一次 + 生效值 ceil=4s 落在块头
        cfg = write_cfg(case, web=False, main_tick="2S", extra=qb_traffic_section(sample="3S", flush="60S"))
        p = app.start(cfg, case, graceful_after=20)
        assert p.wait(80) == 0, f"① 未优雅退出:\n{p.log()[-600:]}"
        assert "非 main_tick 2s 整数倍" in p.log(), "非整倍配比无 WARNING(D5 告警缺失)"
        assert "实际节拍取整为 4s" in p.log(), "WARNING 未给出取整生效值"
        time.sleep(0.2)
        assert count_log(case, r"非 main_tick 2s 整数倍") == 1, "同配对 WARNING 重复多次(只告一次失守)"
        gf = day_file(case / "data", "global")
        assert gf.is_file(), f"① 全局天文件未落盘: {sorted((case / 'data').rglob('*.dat'))}"
        parsed = parse_day(gf)
        assert parsed.blocks and all(b.interval_s == 4.0 for b in parsed.blocks), (
            f"块头 interval_s != 生效值 4s: {[b.interval_s for b in parsed.blocks]}")
        assert parsed.bad_lines == 0

        # ---- ② 运行期热改 sample_interval(4S→6S): 触发关块重开, 新数据分块带新 interval。
        # 实测语义(2026-10-31): 纯空闲系列的开放 z 游程**从不形成盘上旧块**(记录只在封口时
        # append, _append_record 才开块)—— 切 interval 时「无开放块的开放游程不封, 将成为
        # 新块首记录」(traffic_sample_mod._close_blocks_for_interval_change docstring 原文),
        # 所以 L1 零流量下盘上只有一个 interval=6s 的块、z 游程无缝横跨全程。「旧块封口」面
        # 需要块内有真记录(r 行), 归 RM07-08 的 L2 真流量同面, 本条如实按空态口径断言。
        shutil.rmtree(case / "data", ignore_errors=True)
        cfg = write_cfg(case, web=True, main_tick="2S", extra=qb_traffic_section(sample="4S", flush="60S"))
        p = app.start(cfg, case, graceful_after=55)
        assert p.wait_web(40), f"WEB 没起来:\n{p.log()[-600:]}"
        port = web_port_of(cfg)
        time.sleep(10)  # 旧节拍(4S)先跑 ~10s
        resp = put_config(port, lambda c: c["qb_traffic"].__setitem__("sample_interval", "6S"))
        assert resp.get("applied") is True, f"PUT 未应用: {resp}"
        assert not resp.get("restart_required"), f"qb_traffic 段被划 R 级(新事实, 如实记): {resp}"
        wait_until(lambda: "流量采样 | 采样率变化 -> 6s: 关闭全部现块, 新数据分块带新 interval" in p.log(), 20,
                   "热改 interval 后缺关块重开日志")
        assert p.wait(80) == 0, f"② 未优雅退出:\n{p.log()[-600:]}"
        gf = day_file(case / "data", "global")
        assert gf.is_file(), "② 全局天文件未落盘"
        parsed = parse_day(gf)
        assert parsed.bad_lines == 0, f"切 interval 后文件出现坏行: bad={parsed.bad_lines}"
        assert [b.interval_s for b in parsed.blocks] == [6.0], (
            f"变更后的数据分块未带新 interval(应恰一个 6s 块): {[b.interval_s for b in parsed.blocks]}")
        zruns = [r for b in parsed.blocks for r in b.records if not isinstance(r, V4Sample)]
        assert zruns and zruns[0].run_len >= 8, f"z 游程未无缝横跨全程(切源前后断链): {zruns[:2]}"

        # ---- ③ 装载期负向: 非法配比必须 validate_config 聚合报错(RM03-05 同款观测法)
        negatives = [
            ("flush_interval < 60s", qb_traffic_section(sample="4S", flush="30S"), "2S"),
            ("sample_interval > 600s", qb_traffic_section(sample="700S", flush="60S"), "2S"),
            ("sample_interval < main_tick", qb_traffic_section(sample="1S", flush="60S"), "2S"),
        ]
        for i, (label, extra, main_tick) in enumerate(negatives):
            ncase = case / f"neg_{i}"
            ncase.mkdir(parents=True, exist_ok=True)
            ncfg = write_cfg(ncase, web=False, main_tick=main_tick, extra=extra)
            cp = app.run_cli([str(ncfg), "--dry-run"], timeout=60)
            blob = (cp.stdout or "") + (cp.stderr or "")
            assert cp.returncode != 0, f"[{label}] 非法配置被静默接受(fail-fast 破, 高优 FAIL): rc=0\n{blob[-300:]}"
            assert "配置错误" in blob, f"[{label}] 退出码非 0 但缺「配置错误」文案:\n{blob[-300:]}"
        assert_no_crash(case)
    finally:
        if p is not None:
            p.kill()


# ================================================================ RM07-10


def test_rm07_10_tool_status_endpoint_five_states():
    """[RM07-10] 工具状态端点: GET /api/traffic/monitor/status 恒 200 + 五态语义 + 结构完整(按实况定档)

    前置: 基座 + WebUI 起(非 dry-run); provider=traffic_monitor 缺省(enabled=false 仍照查)。
          ⚠ 环境实况(2026-10-31): 本机装有 gtm v0.1.0 且在跑(发现指针指向另一 clone
          D:\\Projects\\auto-qb 的数据目录, autostart 已注册, uptime 天级)—— 冻结计划的
          「未安装 → not_installed」前提在本机为假, 按「按实况定档, 不硬凹」改为双分支断言:
          ready 分支验就绪态载荷全貌(工具 /status 回显), 不可达分支验五态 + reachable=false。
    副作用: 无(只读端点; agent 指针探测只读)。
    回滚: 无需。
    失败判据: 非 200(5xx 泄漏 —— 「恒 200 + 结构化结果」契约破); state 不在五态内; 五态字段缺失
              (前端渲染面会炸, 引用 RM08 前置); ready 态 tool_url/pid/data_dir 或 /status 回显缺
              (就绪态语义破)。
    (spec 内「PUT /config 未就绪 → 502」子项: 本机工具恒就绪, 写端点会真写用户运行中的 gtm
    —— 跨 clone 红线, 本轮跳过并记账; 「密钥缺失降级 not_running」同理不可达。)
    """
    case = case_dir("rm07_10")
    p = None
    try:
        cfg = write_cfg(case, web=True)
        p = app.start(cfg, case)
        assert p.wait_web(40), f"WEB 没起来:\n{p.log()[-600:]}"
        port = web_port_of(cfg)
        req = web_client(port)

        # 恒 200: 连打两次(状态区是轮询面, 单次 200 可能是运气); enabled=false(provider=traffic_monitor)也照查
        body1 = req("GET", "/api/traffic/monitor/status")
        body2 = req("GET", "/api/traffic/monitor/status")
        FIVE_STATES = {"not_installed", "launching", "launch_failed", "not_running", "ready"}
        for body in (body1, body2):
            assert body["state"] in FIVE_STATES, f"state 不在五态内: {body['state']}"
        need = {"enabled", "state", "reachable", "tool_url", "token_path", "version", "pid", "data_dir",
                "autostart_registered", "autostart_error", "error", "retry_s", "claim_note"}
        missing = need - set(body1)
        assert not missing, f"状态载荷缺键: {missing}"
        assert body1["enabled"] is False, "provider=traffic_monitor 时 enabled 应为 false"

        if body1["state"] == "ready":  # 本机实况: gtm 真在跑 —— 验就绪态载荷全貌
            assert body1["reachable"] is True, f"state=ready 却 reachable=false: {body1}"
            assert body1["tool_url"] and body1["pid"] and body1["data_dir"], f"就绪态标识字段空: {body1}"
            echo = body1.get("status") or {}
            for k in ("day", "paths", "config"):
                assert k in echo, f"工具 /status 回显缺 {k}: {sorted(echo)}"
            assert echo["paths"].get("dat", "").endswith("history_traffic.dat"), f"回显 dat 路径不符契约: {echo['paths']}"
        else:  # 不可达分支: reachable=false + error 文案(展示端点不抛 5xx)
            assert body1["reachable"] is False, f"state={body1['state']} 却 reachable: {body1}"
            assert body1["error"], "不可达态缺 error 文案"
        assert body1["state"] == body2["state"], "两次探测状态漂移"
        assert_no_crash(case)
    finally:
        if p is not None:
            p.stop()
