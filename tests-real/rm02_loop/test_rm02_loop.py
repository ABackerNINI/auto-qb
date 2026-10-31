"""RM02 主循环·调度·持久化 —— 八条真机用例(节拍/落盘/热重载/断连退避/兜底恢复)。

验证面对准冻结计划 plans/26-10-31-0927-plan-real-RM02.html §02 的七条代码映射:
interval 真节拍(qbmanager.run 双时间线)· 优雅退出落盘 · 非优雅终止丢失窗口(maybe_flush)·
热重载 L0/R 闸(apply_new_config)· queue_rebuilt 相位(has_named 幂等)·
连不上 qB 的节流与退避(RM01 拍板 D1 移交)· state 损坏恢复(store_recovery)。

基建: 节拍观测与断连注入走 `lib/proxy.py`(产品 <-> 36596 之间的本机转发件);
进程起停复用 `lib/app.py` 的 AppProc/graceful 跑壳, 配置自带 main_tick/sync_interval/
state_save_interval 形参(指向代理端口或空端口时不能走 app.start 的 36596 断言)。

跑法: `real.suite --slice RM02`(task id), 不要裸 pytest。真实种子全程非活跃(八条零种子)。
"""
from __future__ import annotations

import json
import os
import re
import shutil
import statistics
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import pytest

from lib import app
from lib.proxy import TcpProxy

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

pytestmark = [
    pytest.mark.skipif(sys.platform != "win32", reason="本片断言含 Windows 特有语义(无控制台 SIGTERM/taskkill)"),
]

WORK = Path(__file__).resolve().parents[1] / ".work" / "rm02"
_OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))  # 绕 HTTP_PROXY(127.0.0.1 不走代理)


# ---------------------------------------------------------------- 基座

def case_dir(name: str) -> Path:
    d = WORK / name
    shutil.rmtree(d, ignore_errors=True)
    d.mkdir(parents=True, exist_ok=True)
    return d


def cleanup(case: Path) -> None:
    shutil.rmtree(case, ignore_errors=True)


CONFIG_TEMPLATE = """\
config:
    schema_version: 5
    qbittorrent:
        host: 127.0.0.1
        port: {qb_port}
        username: ""
        password: ""
    data_dir: "{data_dir}"
    main_tick: {main_tick}
    sync_interval: {sync_interval}
    state_save_interval: {state_save_interval}
    interval: {interval}
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
"""


def write_cfg(
    case: Path,
    qb_port: int = app.QB_PORT,
    web_enabled: bool = False,
    main_tick: str = "2S",
    sync_interval: str = "1.5S",
    state_save_interval: str = "120S",
    interval: str = "60S",
) -> Path:
    """生成临时配置(schema_version: 5)。qb_port 可指向代理端口/空端口 —— 那两种形态
    过不了 app.start 的 36596 断言, 所以本片用下面的 start() 代替, 安全面自己复核。"""
    data_dir = (case / "data").as_posix()
    cfg = case / "config.yml"
    cfg.write_text(
        CONFIG_TEMPLATE.format(
            qb_port=qb_port,
            data_dir=data_dir,
            main_tick=main_tick,
            sync_interval=sync_interval,
            state_save_interval=state_save_interval,
            interval=interval,
            web_enabled="true" if web_enabled else "false",
            web_port=app.free_port(),
        ),
        encoding="utf-8",
    )
    text = cfg.read_text(encoding="utf-8")
    if "port: 36595" in text:
        raise AssertionError(f"配置指向了 36595(真实种子), 拒跑: {cfg}")
    if "schema_version: 5" not in text:
        raise AssertionError(f"配置缺 schema_version: 5(会触发迁移改写), 拒跑: {cfg}")
    return cfg


def start(cfg: Path, case: Path, *, dry_run: bool = False, graceful_after: float | None = None,
          extra_args: list[str] | None = None) -> app.AppProc:
    """起产品进程(复用 lib/app.py 的跑壳与 AppProc, 只绕过 36596 断言 —— 配置已自查)"""
    if graceful_after is not None:
        cmd = [str(app.PY), str(app._graceful_runner(case)), str(cfg), str(graceful_after)]
    else:
        cmd = [str(app.PY), "-m", "auto_qb", str(cfg)]
    if dry_run:
        cmd.append("--dry-run")
    if extra_args:
        cmd.extend(extra_args)
    popen = subprocess.Popen(
        cmd, cwd=str(app.ROOT), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
    )
    return app.AppProc(popen, case, cfg)


_TS_RE = re.compile(r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}) \[(\w+)\]", re.M)


def log_records(case: Path) -> list[tuple[float, str, str]]:
    """日志按记录切分(多行 ERROR 的 traceback 只算首行): [(ts, level, line)]"""
    text = app.read_log(case)
    out = []
    for m in _TS_RE.finditer(text):
        end = text.find("\n", m.start())
        line = text[m.start():end if end != -1 else None]
        t = time.mktime(time.strptime(m.group(1)[:19], "%Y-%m-%d %H:%M:%S")) + int(m.group(1)[20:]) / 1000.0
        out.append((t, m.group(2).upper(), line))
    return out


def records_in(case: Path, t0: float, t1: float) -> list[tuple[float, str, str]]:
    return [r for r in log_records(case) if t0 <= r[0] <= t1]


def web_req(port: int, method: str, path: str, body: dict | None = None) -> dict:
    req = urllib.request.Request(
        f"http://127.0.0.1:{port}{path}", method=method,
        data=json.dumps(body).encode("utf-8") if body is not None else None,
    )
    if body is not None:
        req.add_header("Content-Type", "application/json")
    with _OPENER.open(req, timeout=20) as r:
        return json.loads(r.read().decode("utf-8"))


def sync_gaps(proxy: TcpProxy, window: float, skip: int = 1, since: float | None = None) -> list[float]:
    """采集 window 秒的 sync/maindata 请求间隔(默认跳过切换过渡的第 1 个间隔)。

    since: 只统计该时刻之后的请求(热重载前后对比用, 免得把变更前的历史间隔算进新窗口)。"""
    start = since if since is not None else time.time()
    end = start + window
    ts: list[float] = []
    while time.time() < end:
        ts = [t for t in proxy.sync_times() if t >= start]
        time.sleep(0.3)
    return [b - a for a, b in zip(ts, ts[1:])][skip:]


# ---------------------------------------------------------------- RM02-01

def test_rm02_01_interval_cadence():
    """[RM02-01] interval 真节拍: 同步线请求周期与 sync_interval 一致, 无死段无空转

    前置: 36596 在线空库; 本地 TCP 代理(39000-39999 探空端口, 转发到 36596);
          配置 schema_version: 5、qB 地址指代理、main_tick=2S/sync_interval=1.5S、非 dry-run。
    副作用: 无(对 qB 零写, 只读快照请求; 用例目录随收尾删除)。
    回滚: 停进程 + 关代理 + 删用例目录。
    失败判据: 同步线请求间隔中位数偏离 1.5s 超出 +-20%; 或出现 >4.5s 的无请求死段;
              或请求频率达到 _throttle 回归特征(25s 内数百次 = 空转)。
    """
    case = case_dir("rm02_01")
    px = TcpProxy(app.QB_PORT, port=app.free_port())
    px.start()
    p = None
    try:
        cfg = write_cfg(case, qb_port=px.port)
        p = start(cfg, case)
        assert p.wait_log("启动 qB 管理器", 40), f"进程没起来:\n{p.log()[-800:]}"
        assert px.wait_requests(6, 30), f"30s 内没有请求经代理到达 36596:\n{p.log()[-600:]}"

        gaps = sync_gaps(px, window=26.0)
        sync = px.sync_times()
        assert len(gaps) >= 6, f"26s 内同步线请求过少({len(sync)} 次), 间隔序列无法判读: {px.requests()[:8]}"
        med = statistics.median(gaps)
        assert 1.2 <= med <= 1.8, f"同步线节拍中位数 {med:.2f}s 偏离 1.5s 超出 +-20%: gaps={gaps}"
        assert max(gaps) <= 4.5, f"出现 >4.5s 的无请求死段(3 个 sync_interval): gaps={gaps}"
        total = len(px.requests())
        assert total < 300, f"25s+ 内总请求数 {total} —— _throttle 空转回归特征(数百次/秒级)"
    finally:
        if p is not None:
            p.stop()
        px.stop()
        cleanup(case)


# ---------------------------------------------------------------- RM02-02

def test_rm02_02_graceful_exit_saves_state():
    """[RM02-02] 优雅退出落盘: state.json 退出即写 + 锁 meta 清干净; 红验: dry-run 必须不写

    前置: 直连 36596(不经代理); 非 dry-run; 进程内 8s 后自投 SIGTERM(graceful_after);
          启动前 state.json 不存在(fresh 目录)。
    副作用: 用例目录写 state.json/.bak/state.lock(随目录清理); 36596 零写。
    回滚: 进程已自行退出; 删用例目录。
    失败判据: 日志无优雅退出锚(非托管模式 SIGTERM 经 KeyboardInterrupt 走 run() 的
              except KeyboardInterrupt ->「停止」一行; 托管模式才是「收到停止信号, 退出主循环」)
              / 退出码非 0 / state.json 没写出 / state.lock.meta.json 残留;
              红验: 同法 dry-run 跑一遍必须**不写** state.json(否则「落盘」断言恒绿)。
    """
    case = case_dir("rm02_02")
    try:
        cfg = write_cfg(case)  # 直连 36596, web 关
        state_json = case / "data" / "state.json"
        meta = case / "data" / "state.lock.meta.json"
        assert not state_json.exists(), "fresh 目录里不该有 state.json, 用例前提不成立"

        t_start = time.time()
        p = start(cfg, case, graceful_after=8.0)
        rc = p.wait(90)
        assert rc == 0, f"优雅退出退出码应为 0, 实际 {rc}; 日志尾部:\n{p.log()[-900:]}"
        stop_lines = [ln for _t, _lv, ln in log_records(case) if ln.rstrip().endswith("停止")]
        assert stop_lines, "日志没有优雅退出行(「停止」), 收尾路径可能没跑"
        assert state_json.is_file(), f"优雅退出后 state.json 没落盘(非 dry-run 退出必须 save):\n{p.log()[-600:]}"
        assert state_json.stat().st_mtime >= t_start - 1, "state.json 是旧文件, 不是这次退出写的"
        # 注: .bak 只在「写盘前已存在旧文件」时生成(atomic_write keep_backup 语义) ——
        # fresh 目录首次退出没有旧文件可备, .bak 断言归 RM02-08(两次起停后)管。
        assert not meta.exists(), "优雅退出后 state.lock.meta.json 残留(release 没走完)"
        del p

        # ---- 红验: dry-run 不落盘是设计口径 —— 对照必须真不写, 否则上面的断言恒绿
        case2 = case_dir("rm02_02_dry")
        cfg2 = write_cfg(case2)
        d = start(cfg2, case2, dry_run=True, graceful_after=5.0)
        try:
            rc2 = d.wait(90)
            assert rc2 == 0, f"dry-run 退出码 {rc2}; 日志:\n{d.log()[-600:]}"
            assert not (case2 / "data" / "state.json").exists(), \
                "红验失败: dry-run 也写了 state.json —— 「非 dry-run 才落盘」这条断言从此恒绿, 本条作废"
        finally:
            cleanup(case2)
    finally:
        cleanup(case)


# ---------------------------------------------------------------- RM02-03

def test_rm02_03_flush_window():
    """[RM02-03] 非优雅终止丢失窗口 <= state_save_interval; 红验: interval=0 必须不中途写盘

    前置: 配置 state_save_interval=30S(校验下限); 非 dry-run 运行 >=70s; 直连 36596。
    副作用: 用例目录 state.json 多次改写; 进程被 taskkill /F /T 强杀。
    回滚: 删用例目录(强杀进程已死, 无需停)。
    失败判据: 运行期内 mtime 推进次数 <2(75s 应有 ~30s/60s 两次); taskkill 后最后写入
              距 kill 时刻 > interval(30s)+裕量(10s); 红验: state_save_interval=0S 时
              运行期内 state.json 不出现(0=关) —— 对照不红则本条按 L3 验收不合格。
    """
    case = case_dir("rm02_03")
    try:
        cfg = write_cfg(case, state_save_interval="30S")
        p = start(cfg, case)
        try:
            assert p.wait_log("启动 qB 管理器", 40), f"进程没起来:\n{p.log()[-800:]}"
            state_json = case / "data" / "state.json"
            mtimes: list[float] = []
            deadline = time.time() + 75.0
            while time.time() < deadline:
                if state_json.is_file():
                    m = state_json.stat().st_mtime
                    if not mtimes or m > mtimes[-1] + 0.5:
                        mtimes.append(m)
                time.sleep(1.0)
            assert len(mtimes) >= 2, f"75s 运行期内周期落盘 mtime 只推进 {len(mtimes)} 次(预期 >=2): {mtimes}"

            kill_ts = time.time()
            p.kill()
            assert not p.alive(), "taskkill 后进程还活着"
            last = state_json.stat().st_mtime if state_json.is_file() else 0.0
            loss = kill_ts - last
            assert loss <= 40.0, \
                f"丢失窗口 {loss:.0f}s 超过 state_save_interval(30s)+裕量(10s): 最后落盘 {last:.0f}, kill {kill_ts:.0f}"
        finally:
            if p.alive():
                p.kill()
        del p

        # ---- 红验: interval=0(关闭)运行期内必须不写盘
        case2 = case_dir("rm02_03_off")
        cfg2 = write_cfg(case2, state_save_interval="0S")
        p2 = start(cfg2, case2)
        try:
            assert p2.wait_log("启动 qB 管理器", 40), f"红验进程没起来:\n{p2.log()[-600:]}"
            state2 = case2 / "data" / "state.json"
            deadline = time.time() + 45.0
            while time.time() < deadline:
                assert not state2.is_file(), \
                    "红验失败: state_save_interval=0 运行期内 state.json 出现了(0=关语义丢失) —— 主断言恒绿, 本条作废"
                time.sleep(1.0)
        finally:
            p2.kill()
            cleanup(case2)
    finally:
        cleanup(case)


# ---------------------------------------------------------------- RM02-04

def test_rm02_04_hot_reload_l0_and_rgate():
    """[RM02-04] 热重载: L0 键(main_tick/sync_interval)即时生效 + R 闸(data_dir)拒绝

    前置: 代理基座(产品 <-> 代理 <-> 36596) + WEB 启用(非 dry-run); 基线节拍 1.5s。
    副作用: 运行期经 PUT /api/config 改写用例目录的临时配置文件。
    回滚: 停进程 + 关代理 + 删用例目录。
    失败判据: 提交 main_tick/sync_interval 变更后代理观测同步线节拍未变(2.5s 期望);
              提交 data_dir 变更未被拒(响应缺 restart_required 或磁盘被写穿); 进程意外退出。
    """
    case = case_dir("rm02_04")
    px = TcpProxy(app.QB_PORT, port=app.free_port())
    px.start()
    p = None
    try:
        cfg = write_cfg(case, qb_port=px.port, web_enabled=True)
        web_port = int(re.search(r"port: (\d+)", cfg.read_text(encoding="utf-8").split("web:")[1]).group(1))
        p = start(cfg, case)
        assert p.wait_web(40), f"WEB 没起来:\n{p.log()[-800:]}"
        assert px.wait_requests(6, 30), f"代理上没有同步线请求:\n{p.log()[-600:]}"

        base = sync_gaps(px, window=12.0)
        assert base and 1.2 <= statistics.median(base) <= 1.8, \
            f"基线同步线节拍不是 1.5s: {base}"

        # ---- L0: 节拍键变更即时生效(主循环每轮现读)
        tree = web_req(web_port, "GET", "/api/config")["tree"]
        assert tree["config"]["main_tick"] and tree["config"]["sync_interval"], f"树里没有节拍键: {tree['config'].keys()}"
        tree["config"]["main_tick"] = "4S"
        tree["config"]["sync_interval"] = "2.5S"
        resp = web_req(web_port, "PUT", "/api/config", {"tree": tree})
        assert resp.get("applied") is True, f"PUT 未应用: {resp}"
        assert not resp.get("restart_required"), f"节拍键不该触发重启闸: {resp}"
        assert "main_tick" in resp.get("changes", []) and "sync_interval" in resp.get("changes", []), \
            f"变更清单没含节拍键: {resp}"

        post = sync_gaps(px, window=17.0, skip=2, since=time.time())  # 跳过切换过渡的两个间隔
        assert len(post) >= 3 and 2.0 <= statistics.median(post) <= 3.0, \
            f"热重载后同步线节拍未变为 2.5s(期望区间 2.0-3.0): {post}"

        # ---- R 闸: data_dir 变更必须被拒且磁盘不被写穿
        tree2 = web_req(web_port, "GET", "/api/config")["tree"]
        old_dd = tree2["config"]["data_dir"]
        assert old_dd == (case / "data").as_posix(), f"GET 树里的 data_dir 与预期不符: {old_dd}"
        tree2["config"]["data_dir"] = (case / "data2").as_posix()
        resp2 = web_req(web_port, "PUT", "/api/config", {"tree": tree2})
        assert "data_dir" in (resp2.get("restart_required") or []), \
            f"R 闸丢失: data_dir 变更未被报 restart_required: {resp2}"
        text = cfg.read_text(encoding="utf-8")
        assert f"data_dir: \"{old_dd}\"" in text, "磁盘配置的 data_dir 被改写了(R 级字段必须回退旧值)"
        assert "data2" not in text, "data2 写穿到了磁盘"
        assert p.alive(), "R 闸拒绝动作把进程带走了"
        n0 = len(px.requests())
        assert px.wait_requests(n0 + 2, 15), "R 闸提交后同步线停摆 —— 内核可能被打断"
    finally:
        if p is not None:
            p.stop()
        px.stop()
        cleanup(case)


# ---------------------------------------------------------------- RM02-05

def test_rm02_05_queue_rebuilt_idempotent():
    """[RM02-05] queue_rebuilt 相位: 连续两次 L2 重建, 全局任务不重不丢

    前置: 直连 36596 + WEB 启用; 经 PUT /api/config 改 interval(rules 模块认领段)触发
          L2 重建, 连续两次。
    副作用: 运行期改写用例目录的临时配置文件(interval 60S->61S->62S)。
    回滚: 停进程 + 删用例目录。
    失败判据: 第二次重建后「创建全局任务 N 个」的 N 翻倍(has_named 幂等被打穿); 或
              重建后全局任务消失(该日志不再出现); 或 L2 重建路径根本没走
              (「应用结构级配置变更」缺行, 测试空转)。
    """
    case = case_dir("rm02_05")
    p = None
    try:
        cfg = write_cfg(case, web_enabled=True)
        web_port = int(re.search(r"port: (\d+)", cfg.read_text(encoding="utf-8").split("web:")[1]).group(1))
        p = start(cfg, case)
        assert p.wait_web(40), f"WEB 没起来:\n{p.log()[-800:]}"

        def task_lines() -> list[str]:
            return [ln for _t, _lv, ln in log_records(case) if "创建全局任务" in ln]

        assert p.wait_log("创建全局任务", 40), f"启动期没有全局任务注册日志:\n{p.log()[-800:]}"
        assert len(task_lines()) == 1, f"启动期「创建全局任务」应为 1 行, 实际 {len(task_lines())}: {task_lines()}"

        for new_interval, expect in (("61S", 2), ("62S", 3)):
            tree = web_req(web_port, "GET", "/api/config")["tree"]
            tree["config"]["interval"] = new_interval
            resp = web_req(web_port, "PUT", "/api/config", {"tree": tree})
            assert resp.get("applied") is True, f"PUT 未应用: {resp}"
            deadline = time.time() + 30
            while time.time() < deadline and len(task_lines()) < expect:
                time.sleep(0.3)

        lines = task_lines()
        assert len(lines) == 3, f"「创建全局任务」应为 3 行(启动+两次重建), 实际 {len(lines)}: {lines}"
        ns = [int(m.group(1)) for ln in lines for m in [re.search(r"创建全局任务 (\d+) ", ln)] if m]
        assert len(ns) == 3 and ns == [ns[0]] * 3, f"重建后全局任务数翻倍/漂移(has_named 被打穿?): {ns} / {lines}"
        assert ns[0] >= 1, "全局任务数为 0 —— 重建后任务消失"

        rebuilds = [ln for _t, _lv, ln in log_records(case) if "应用结构级配置变更" in ln]
        assert len(rebuilds) == 2, f"L2 重建日志应为 2 行(证明重建路径真走了), 实际 {len(rebuilds)}"
        assert p.alive(), "连续重建把进程打挂了"
    finally:
        if p is not None:
            p.stop()
        cleanup(case)


# ---------------------------------------------------------------- RM02-06

def test_rm02_06_first_connect_fail():
    """[RM02-06] 连不上 qB·首连失败: 非托管 fail-fast 退出码 1 / 托管重试节流不刷屏

    前置: 配置指向无监听的空端口(39000-39999 探空, 不是任何 qB 实例); 不起真实 qB 连接。
          托管小节经 --tray 起常驻进程(Windows 上 SIGTERM 对 Tk 主循环无效 —— 本轮实测,
          托管进程不验优雅退出, 收尾 taskkill /F /T)。
    副作用: 无(非托管进程自然退出; 托管进程被强杀)。
    回滚: 删用例目录。
    失败判据: 非托管退出码 != 1 或 stderr 带堆栈或缺「无法连接 qBittorrent」; 托管模式
              10s 内就死(应常驻重试)或重试 WARNING/连接失败 ERROR 各超过 1 行(逐拍刷屏)。
    """
    case = case_dir("rm02_06")
    try:
        dead = app.free_port()
        assert app.port_free(dead), f"探空端口 {dead} 意外有人监听, 换口重跑"
        cfg = write_cfg(case, qb_port=dead)

        # ---- 非托管: fail-fast, 干净退出码 1
        r = app.run_cli([str(cfg)], timeout=90)
        assert r.returncode == 1, f"期望退出码 1, 实际 {r.returncode}; stderr={r.stderr!r}"
        assert "无法连接 qBittorrent" in r.stderr, f"stderr 缺「无法连接 qBittorrent」: {r.stderr!r}"
        assert "Traceback" not in r.stderr, f"QbConnectError 通道被打穿, 打出了堆栈: {r.stderr!r}"
        del r, cfg

        # ---- 托管(--tray 传 stop_event): 常驻重试, WARNING 只说一次, ERROR 只记一次
        # 注: 本机 loopback 连接失败单次要 ~2s(实测), 首个 connect() 周期(detect_scheme
        # http/https + login 三连)约 20-40s 才落第一条 ERROR —— 等待窗给足, 慢不是挂死。
        case2 = case_dir("rm02_06_tray")
        dead2 = app.free_port()
        assert app.port_free(dead2), f"探空端口 {dead2} 意外有人监听"
        cfg2 = write_cfg(case2, qb_port=dead2)
        p = start(cfg2, case2, extra_args=["--tray"])
        try:
            time.sleep(10.0)
            assert p.alive(), f"托管模式 10s 内就退出了(应按 main_tick 重试常驻):\n{p.log()[-900:]}"
            assert p.wait_log("连接 qBittorrent 失败", 60), \
                f"60s 内没有连接失败记录(重试循环没跑?):\n{p.log()[-900:]}"
            time.sleep(10.0)  # 再给一个观察窗: 若逐拍刷屏, 这 10s(main_tick=2s)足够多出几行
            warns = [ln for _t, lv, ln in log_records(case2) if lv == "WARNING" and "连接 qBittorrent 失败" in ln]
            errs = [ln for _t, lv, ln in log_records(case2) if lv == "ERROR" and "连接 qBittorrent 失败" in ln]
            assert len(warns) == 1, f"重试 WARNING 应只打一次(A-07), 实际 {len(warns)} 行: {warns[:3]}"
            assert len(errs) == 1, f"连接失败 ERROR 应只记一次(转换节流), 实际 {len(errs)} 行: {errs[:3]}"
        finally:
            p.kill()
            cleanup(case2)
    finally:
        cleanup(case)


# ---------------------------------------------------------------- RM02-07

def test_rm02_07_disconnect_throttle_and_backoff():
    """[RM02-07] 运行期断连: 失败日志节流 + 重连退避(不逐拍) + 恢复自动接上(红验/L3)

    前置: 代理基座; 非 dry-run 连上后运行 >=60s; 掐断代理(不碰 qB 进程)观测 >=70s
          (覆盖退避 2->4->8->16->30s 上限), 恢复代理后等待重连。
    副作用: 无(对 qB 零写; 掐断的是本机代理)。
    回滚: 恢复代理 + 停进程 + 删用例目录。
    失败判据: 断开期间 ERROR/WARNING 记录数 > 转换次数(逐拍刷屏 = A-07 回归); 重连尝试
              逐拍打满(探测数 > 8); 恢复代理后 60s 内未自动回连(无「已重新连接」INFO 收尾,
              同步线不恢复)。红验即注入本身: 断开后必须看到连接失败 ERROR(注入生效)。
    """
    case = case_dir("rm02_07")
    px = TcpProxy(app.QB_PORT, port=app.free_port())
    px.start()
    p = None
    try:
        cfg = write_cfg(case, qb_port=px.port)
        p = start(cfg, case)
        assert p.wait_log("启动 qB 管理器", 40), f"进程没起来:\n{p.log()[-800:]}"
        assert px.wait_requests(6, 30), f"连接没建立(代理无请求):\n{p.log()[-600:]}"

        # 连上后运行 >=60s(冻结计划口径), 期间同步线应持续有请求
        time.sleep(55.0)
        assert len(px.sync_times()) >= 20, "60s 内同步线请求过少, 基线不成立"

        # ---- 掐断
        cut_ts = time.time()
        px.cut()
        time.sleep(75.0)  # 覆盖退避 2->4->8->16->30 上限
        restore_ts = time.time()

        win = records_in(case, cut_ts, restore_ts)
        conn_errs = [r for r in win if r[1] == "ERROR" and "连接 qBittorrent 失败" in r[2]]
        assert conn_errs, "断开期间没有任何连接失败 ERROR —— 注入不生效(节流断言恒绿), 记 BLOCKED 不硬撑"
        bad_lv = [r for r in win if r[1] in ("ERROR", "WARNING")]
        assert len(bad_lv) <= 3, \
            f"断开期间 ERROR/WARNING 记录 {len(bad_lv)} 条(应 <= 转换次数)—— 逐拍刷屏(A-07 回归): {[r[2][:110] for r in bad_lv[:8]]}"
        probes = [t for t in px.probes() if cut_ts <= t <= restore_ts]
        assert len(probes) <= 8, \
            f"断开 {restore_ts-cut_ts:.0f}s 内重连尝试 {len(probes)} 次 —— 逐拍重连(退避失守): {[f'{t-cut_ts:.1f}' for t in probes[:12]]}"
        gaps = [b - a for a, b in zip(probes, probes[1:])]
        assert all(g <= 32.0 for g in gaps), f"重试间隔超过 30s 上限(+裕量): {gaps}"

        # ---- 恢复: 60s 内应自动回连(INFO 收尾), 同步线恢复
        px.restore()
        ok = p.wait_log("已重新连接 qBittorrent", 60)
        assert ok, (f"恢复代理后 60s 内未自动回连(无「已重新连接 qBittorrent」INFO 收尾); "
                    f"断开窗口日志: {[r[2][:110] for r in bad_lv[:6]]}; 此后日志尾部:\n{p.log()[-1200:]}")
        n0 = len(px.requests())
        assert px.wait_requests(n0 + 2, 15), "回连 INFO 有了但同步线请求没恢复"
    finally:
        if p is not None:
            p.stop()
        px.stop()
        cleanup(case)


# ---------------------------------------------------------------- RM02-08

def test_rm02_08_state_corruption_recovery():
    """[RM02-08] state 损坏恢复: .bak 回退 + 自愈写回 + 孤儿 tmp 清理

    前置: 先正常起停**两次**生成合法 state.json + .bak(.bak 只在写盘前已有旧文件时生成,
          首次退出没有 —— atomic_write keep_backup 语义); 停机态把主文件写坏(乱字节);
          另留一个孤儿 <state_file>.<随机>.tmp。
    副作用: 用例目录 state.json 被自愈重写; 孤儿 tmp 被删; 第二次优雅退出再写一对新件。
    回滚: 删用例目录。
    失败判据: 启动崩溃或退出码非 0; 未从 .bak 恢复(主文件内容不回); 恢复了但没写回主文件;
              日志缺「状态文件损坏」WARNING / 「已用备份恢复状态」INFO; 孤儿 tmp 残留。
    """
    case = case_dir("rm02_08")
    try:
        cfg = write_cfg(case)  # 直连 36596
        state_json = case / "data" / "state.json"
        state_bak = case / "data" / "state.json.bak"

        # 两次正常起停: 第一轮生成 state.json, 第二轮退出时才有 .bak(keep_backup 语义)
        for i in (1, 2):
            pi = start(cfg, case, graceful_after=6.0)
            rci = pi.wait(90)
            assert rci == 0, f"第 {i} 次起停退出码 {rci}:\n{pi.log()[-600:]}"
            del pi
        assert state_json.is_file() and state_bak.is_file(), "两次优雅退出后没有 state.json/.bak, 前提不成立"
        good = json.loads(state_bak.read_text(encoding="utf-8"))
        assert isinstance(good, dict), ".bak 不是 JSON 对象"

        # 停机态注入: 主文件写坏 + 孤儿 tmp
        garbage = b"\xff\xfe NOT-JSON {{{ nope"
        state_json.write_bytes(garbage)
        orphan = case / "data" / "state.json.orphan-test.tmp"
        orphan.write_bytes(b"{}")
        assert not _is_json(state_json), "损坏注入没生效"

        # 带伤启动: 必须用 .bak 恢复 + 自愈写回 + 清孤儿 tmp
        p2 = start(cfg, case, graceful_after=6.0)
        try:
            rc2 = p2.wait(90)
            assert rc2 == 0, f"带伤启动退出码 {rc2}(应不崩):\n{p2.log()[-1200:]}"
            log = p2.log()
            assert "状态文件损坏" in log, "日志缺「状态文件损坏」WARNING(损坏没有被报出来)"
            assert "已用备份恢复状态" in log, "日志缺「已用备份恢复状态」INFO(.bak 回退没走)"
            assert "清理 1 个孤儿临时文件" in log, "孤儿 tmp 没被清理(或清理日志缺失)"
            assert _is_json(state_json), "主文件没有自愈写回(下次 save 会把坏内容复制成新 .bak)"
            healed = json.loads(state_json.read_text(encoding="utf-8"))
            assert isinstance(healed, dict) and "schema_version" in healed, \
                f"自愈内容不对(应来自 .bak, 带 schema_version): {str(healed)[:120]}"
            assert not orphan.exists(), "孤儿 .tmp 残留"
        finally:
            if p2.alive():
                p2.kill()
    finally:
        cleanup(case)


def _is_json(path: Path) -> bool:
    try:
        json.loads(path.read_text(encoding="utf-8"))
        return True
    except Exception:  # noqa: BLE001 —— 探针, 坏件本来就该 False
        return False
