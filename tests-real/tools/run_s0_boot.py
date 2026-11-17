"""S0 受控重启驱动(计划 26-11-18-0259: 重启后 WebUI 首份数据取证)。

编排一轮「起产品 → 测量 → 优雅停 → 重启 → 再测量」: 产品用本脚本生成的派生配置
(RM08 同款最小配置形状 + grouping 开 + trackers 命中假种子),
`python -m auto_qb` 等价入口(进程内 cli.main)起 —— **非 dry-run**(WEB 必须真启,
首轮数据管线正是被测对象; 任务线 interval=60S 照常, 不用 dev.webui 的 86400S 形态)。

优雅停口径(real-machine.md §2.6 / app.py 三硬事实): Windows 外部 SIGTERM=强杀,
唯一优雅路径 = 进程内 signal.raise_signal(SIGTERM) —— 本脚本生成 stopfile 看门 runner,
收尾 touch stopfile 触发; **全程零 taskkill**。

测量口径: measure_boot_first_data.run_measurement(t0=spawn 双时钟, 轮询 --interval, 缺省 0.15s)。
每轮产物: <case>/run<r>.measure.json(时间线) + <case>/run<r>.logslice.txt(产品日志切片,
起点 = 本轮 Popen 前的日志文件长度 —— 含本轮启动至测量结束, **停机段在切片外**) + 汇总
<case>/s0_summary.json。

用法:
  uv run python tests-real/tools/run_s0_boot.py --runs 2 [--case-dir tests-real/.work/s0boot]
前置: tests-real/tools/seed_bulk_boot.py 已造好假种子(本脚本不造不清, 留存口径 S3 复测后才清)。
case 目录白名单: resolve 后必须在 tests-real/.work/ 之下(防手滑指到仓库根覆盖生产文件);
--qb-port 只认白名单实例(guard.WHITELIST_PORTS)。
"""
from __future__ import annotations

import argparse
import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))  # tests-real/
sys.path.insert(0, str(HERE))  # tools/ —— 复用测量脚本

from lib import guard, instances  # noqa: E402
from measure_boot_first_data import run_measurement  # noqa: E402

ROOT = HERE.parents[1]  # 仓库根(tests-real/tools -> tests-real -> 根)
PY = ROOT / ".venv" / "Scripts" / "python.exe"
WEB_PORT_LO, WEB_PORT_HI = 39000, 39999  # 与 lib/app.py 同段(避开主/副实例与生产)
WORK_ROOT = (HERE.parent / ".work").resolve()  # case 目录白名单根(越界拒跑, 防覆盖红线文件)

RUNNER = """\
import os, signal, sys, threading, time
from auto_qb import cli
# argv: <脚本> <配置> <stopfile>; stopfile 先 pop, 否则 cli argparse 报 unrecognized
stopfile = sys.argv.pop(2)
cfg = sys.argv[1]

def _watch():
    while not os.path.exists(stopfile):
        time.sleep(0.2)
    signal.raise_signal(signal.SIGTERM)  # 进程内触发 handler -> KeyboardInterrupt -> 优雅退出(§2.6)

threading.Thread(target=_watch, daemon=True).start()
raise SystemExit(cli.main() or 0)
"""

CONFIG_TEMPLATE = """\
config:
    schema_version: 8
    qbittorrent:
        host: 127.0.0.1
        port: {qb_port}
        username: ""
        password: ""
        api_key: ""
    data_dir: "{data_dir}"
    main_tick: 2S
    sync_interval: 1.5S
    interval: 60S
    max_tasks_per_tick: 20
    remove_similar_tags: false
    skip_checking_tag: zSkipChecked
    add_episode_tags:
        enabled: false
    delete_tags: []
    hr:
        add_tag: ""
        add_category: ""
        overwrite_category: false
        add_tag_for_satisfied: ""
        add_category_for_satisfied: ""
        overwrite_category_for_satisfied: false
    log:
        level: INFO
    grouping:
        enabled: true
        missing_tag: ""
        check_missing_files: false
    web:
        enabled: true
        host: 127.0.0.1
        port: {web_port}
        skip_local_verify: true
    trackers:
        boot-fake:
            domains:
                - 127.0.0.1
            upload_speed_limit: 0KiB/s
            download_speed_limit: 0KiB/s
    notify:
        enabled: false
"""


def port_free(port: int) -> bool:
    """裸 bind 探空(不加 SO_REUSEADDR —— lib/app.py RM01-07 教训: 抢占式 bind 假空闲)。"""
    s = socket.socket()
    try:
        s.bind(("127.0.0.1", port))
        return True
    except OSError:
        return False
    finally:
        s.close()


def pick_web_port() -> int:
    for port in range(WEB_PORT_LO, WEB_PORT_HI + 1):
        if port_free(port):
            return port
    raise RuntimeError(f"{WEB_PORT_LO}-{WEB_PORT_HI} 无可用端口")


def wait_port_free(port: int, timeout: float = 30.0) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if port_free(port):
            return
        time.sleep(0.3)
    raise RuntimeError(f"端口 {port} 等待释放超时({timeout}s) —— 查残留进程")


def setup_case(case: Path, qb_port: int) -> tuple[Path, int]:
    """建用例目录 + 写派生配置(只写一次, 重启轮复用同一配置与数据目录; web 口径存 meta)。

    fs.path_map 不配(Windows 宿主直跑形态, 校验要求 to 为 / 开头容器挂载点): path_map
    空 = 现状, path_map_selfcheck 短路 no-op —— pathmap issue 的本地地板基线口径。
    双保险(评审 major 2): case 目录越界(main 已拒)之外, 目录里已有 config.yml 但无
    s0_meta.json 伴生 = 非本工具产物(可能是手放的生产形态配置) ⇒ 拒写报红。
    """
    data_dir = (case / "data").as_posix()
    cfg_path = case / "config.yml"
    meta_path = case / "s0_meta.json"
    if meta_path.is_file():
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        assert int(meta.get("qb_port", -1)) == int(qb_port), (
            f"case 目录复用核验失败: meta.qb_port={meta.get('qb_port')} != 本次 --qb-port {qb_port} "
            f"—— 换 --case-dir 或显式传同一 qb-port"
        )
        return cfg_path, int(meta["web_port"])
    if cfg_path.is_file():
        raise SystemExit(f"[FAIL] {cfg_path} 已存在但无 s0_meta.json 伴生 —— 非本工具产物, 拒写; 换 --case-dir")
    case.mkdir(parents=True, exist_ok=True)
    web_port = pick_web_port()
    cfg_path.write_text(
        CONFIG_TEMPLATE.format(qb_port=qb_port, data_dir=data_dir, web_port=web_port),
        encoding="utf-8",
    )
    text = cfg_path.read_text(encoding="utf-8")
    assert f"port: {qb_port}" in text and f"port: {instances.PRIMARY}" not in text, "配置目标实例复核失败"
    assert "schema_version: 8" in text, "schema_version 必须是产品现行版(§2.6)"
    runner = case / "runner_s0.py"
    runner.write_text(RUNNER, encoding="utf-8")
    meta_path.write_text(json.dumps({"web_port": web_port, "qb_port": qb_port}, ensure_ascii=False), encoding="utf-8")
    return cfg_path, web_port


def boot_once(
    case: Path, cfg: Path, web_port: int, run_no: int, *, interval: float, timeout: float, fetch_timeout: float
) -> tuple[dict, subprocess.Popen]:
    """起产品 + 测量(不停)。返回 (测量结果, 进程句柄)。

    日志切片起点 = **本轮 Popen 前**的日志文件长度(评审 minor 4: 原实现用上轮测量结束的
    偏移, 声明不实)—— 切片含本轮启动至测量结束, 停机段在切片外(docstring 已如实声明)。
    """
    stopfile = case / "stop.now"
    if stopfile.exists():
        stopfile.unlink()
    wait_port_free(web_port)
    out_f = open(case / f"run{run_no}.stdout.log", "wb")
    err_f = open(case / f"run{run_no}.stderr.log", "wb")
    log_file = case / "data" / "logs" / "auto-qb.log"
    log_start = log_file.stat().st_size if log_file.is_file() else 0
    t0_epoch = time.time()
    t0_mono = time.monotonic()
    popen = subprocess.Popen(
        [str(PY), str(case / "runner_s0.py"), str(cfg), str(stopfile)],
        cwd=str(ROOT),
        stdout=out_f,
        stderr=err_f,
        env={
            **os.environ, "PYTHONIOENCODING": "utf-8"
        },
    )
    url = f"http://127.0.0.1:{web_port}"
    result = run_measurement(
        url,
        str(case / f"run{run_no}.measure.json"),
        t0_epoch=t0_epoch,
        t0_mono=t0_mono,
        interval=interval,
        timeout=timeout,
        fetch_timeout=fetch_timeout
    )
    result["popen_pid"] = popen.pid
    result["spawn_epoch"] = t0_epoch
    result["log_slice_start"] = log_start
    out_path = case / f"run{run_no}.measure.json"
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")  # 补齐 spawn 字段再落盘
    # 产品日志切片(本轮 Popen 前起的内容), 供管线时间窗解析; 停机段不在切片内
    if log_file.is_file() and log_file.stat().st_size > log_start:
        with open(log_file, "rb") as f:
            f.seek(log_start)
            slice_bytes = f.read()
        (case / f"run{run_no}.logslice.txt").write_bytes(slice_bytes)
    return result, popen


def graceful_stop(case: Path, popen: subprocess.Popen, *, timeout: float = 40.0) -> dict:
    """touch stopfile -> runner 进程内 raise SIGTERM -> cli 优雅退出; 超时即报红停手(不降级强杀)。"""
    (case / "stop.now").write_text("stop", encoding="utf-8")
    t = time.time()
    try:
        rc = popen.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        raise RuntimeError(
            f"产品进程 {popen.pid} 优雅退出超时({timeout}s) —— 按纪律不强制杀; "
            "请人工核查(real-machine.md §2.2: 不降级 taskkill)"
        ) from None
    for f in (popen.stdout, popen.stderr):
        if f is not None:
            f.close()
    return {"exit_code": rc, "stop_s": round(time.time() - t, 2)}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="S0 受控重启测量驱动")
    ap.add_argument("--runs", type=int, default=2, help="重启测量轮数(≥2)")
    ap.add_argument("--case-dir", default=str(HERE.parent / ".work" / "s0boot"))
    ap.add_argument(
        "--qb-port",
        type=int,
        default=instances.SECONDARY,
        choices=list(guard.WHITELIST_PORTS),
        help="产品连接的 qB 测试实例(只认白名单, 缺省副实例空库)"
    )
    ap.add_argument("--interval", type=float, default=0.15)
    ap.add_argument("--fetch-timeout", type=float, default=10.0, help="单次 HTTP 超时秒(空代竞态探测轮用 0.1)")
    ap.add_argument("--timeout", type=float, default=150.0, help="单轮测量超时秒")
    ap.add_argument("--quiesce", type=float, default=3.0, help="测量完成后静置秒(再优雅停)")
    args = ap.parse_args(argv)

    case = Path(args.case_dir).resolve()
    # case 目录白名单(评审 major 2): 只许 tests-real/.work/ 之下 —— 越界(如仓库根)一律拒跑,
    # 防手滑把派生 config.yml 写到红线生产文件上
    if case != WORK_ROOT and WORK_ROOT not in case.parents:
        raise SystemExit(f"[FAIL] --case-dir {case} 不在 {WORK_ROOT} 之下 —— 拒跑(派生配置落点白名单)")
    cfg, web_port = setup_case(case, args.qb_port)
    print(f"[case] {case} web={web_port} cfg={cfg}")
    summary = {"case_dir": str(case), "web_port": web_port, "cfg": str(cfg), "runs": []}
    for r in range(1, args.runs + 1):
        print(f"=== 第 {r}/{args.runs} 轮: 起产品 + 测量 ===")
        result, popen = boot_once(
            case, cfg, web_port, r, interval=args.interval, timeout=args.timeout, fetch_timeout=args.fetch_timeout
        )
        time.sleep(args.quiesce)
        stop_info = graceful_stop(case, popen)
        result["stop"] = stop_info
        out_path = case / f"run{r}.measure.json"
        out_path.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")  # 连 stop 一起落盘
        fr = result.get("first_response")
        ne = result.get("first_nonempty", {})
        row = {
            "run": r,
            "spawn_epoch": result.get("spawn_epoch"),
            "web_up": result.get("web_up"),
            "first_response_counts": fr,
            "first_nonempty": ne,
            "all_nonempty": result.get("all_nonempty"),
            "rid_sequence": result.get("rid_sequence"),
            "error": result.get("error"),
            "stop": stop_info,
        }
        summary["runs"].append(row)
        print(f"[run{r}] 汇总: {json.dumps(row, ensure_ascii=False)}")
    out = case / "s0_summary.json"
    out.write_text(json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"[ok] 汇总 → {out}")
    return 1 if any(r.get("error") for r in summary["runs"]) else 0


if __name__ == "__main__":
    raise SystemExit(main())
