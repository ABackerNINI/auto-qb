"""RM04-20 整组迁移 file_links+symlink 形态全链真机闭环: 迁移发起 -> qB 侧自检 skipped(运行时F
假阴性修复生效, 不再 qb_side_check_failed) -> armed -> 双测试实例优雅下线窗(daemon 改写非 mover
fastresume) -> 重启全员落位 dst + 删链门删净别名 -> job done + 组不裂 + 收尾零残留。

计划 plans/26-11-10-0230-plan-relocate-listing-false-negative.html §03.3 S4b: 把 S4a 闭环实验
(tests-real/.work/relocate-rlfn-e2e/, gitignored)沉淀为耐久用例; 断言面 = 实验切片
memory-bank/testing/real-baselines/26-11-10-0435-real-relocate-rlfn-e2e.md 的 13 项(全 PASS)。

## 测试计划(每个测试函数一条)
- test_rm04_20_rlfn_symlink_window_e2e: A1 双实例在线自检 -> A2 产品实例(relocate on + bt_backup
  查表) -> A3 两颗共享文件假种子归同组 -> A4 整组迁移发起(形态 file_links) -> A5 qB 侧自检
  skipped 且零 qb_side_check_failed -> A6 armed -> A7 armed 现场(src symlink + 非 mover
  fastresume 未触碰) -> A8 双实例优雅下线 + wrapper 名册窄化开窗(新 patch 行或在位健康 patched
  watcher 二者其一) -> A9 daemon 改写非 mover
  fastresume(journal 账 + fastresume 字节双证) -> A10 重启全员落位 dst(零 recheck 零异常态)
  -> A11 job done + 删链门删净 -> A12 组不裂(组键整体迁移) -> A13 收尾零残留 + 环境还原。

【daemon 离线窗旁路 —— 人工闸, 已授权 2026-11-10】
本机生产 16585/26586 常驻在跑, 全机 qbittorrent.exe 名册判据下离线窗永不开
(memory-bank/pitfalls/testing/relocate-window-machine-roster.md)。按计划 §03.3 走产品自留测试
接缝(用户 2026-11-10 明示授权; 授权面 = 人工闸, 不随用例自动扩大):
- 产品进程内替换 relocate_exec.ExecMixin._spawn_daemon(产品 docstring 自留测试接缝「测试替换本
  方法」), 让 daemon 经 tests-real/tools/daemon_window_wrapper.py 拉起(收编入库版, 判据/边界见其
  docstring);
- wrapper 仅在 daemon 进程内把名册窄化为 D:\\Programs\\qBittorrent-testing* 镜像前缀(生产实例
  不计入), 端口拒连 + 30s 稳定窗对 L2/L3 层保持产品原样; L1 路径无稳定期(见
  daemon_window_wrapper docstring L1 注记); 盘上产品代码零改动; 决策留痕
  tests-real/.work/tools-daemon-wrapper/daemon_wrapper.log。

拓扑钉死(计划 §03.3 + §07 风险表): src = R:/qbt-fake/rm04/rm04_20/src(R: 内存盘, 与 qB CWD D:
异盘 => fastresume 保存键绝对形态, daemon 改写可达); dst = tests-real/.work/rm04/rm04_20/dst
(D:, 与 src 异盘 + 单文件 1 < 阈值 8 => file_links+symlink, 生产事故 jr-a2ce556d0165 同款形态)。
R: 缺席(环境2 C盘机)⇒ 拓扑不成立 ⇒ skip, 不回退落点(钉死口径, 不做环境自适应)。

前置: 双测试实例在线(没起先 `commands run real.up -- --port <白名单端口>`); 副实例无 real-fake
残留; 本用例独占约 5-10 分钟(qB 两次起停 + 30s 稳定窗 + 60s daemon 宽限), conftest serial 锁
串行保护; 实例起停经 runner.py cmd_up/cmd_down(real.up/real.down task id 同一实现面)。
副作用: 副实例 加 2 假种子(real-fake)并整组迁移 R:->D:; src 出现 symlink 再被删链门删除; 两
测试实例各优雅下线/重启一次; 副实例 BT_backup 新增本用例哈希的 fastresume/torrent 且非 mover 的
被 daemon 改写; 产品 case 目录落账; wrapper 决策日志追加。
回滚: 产品优雅退出(sentinel 进程内 SIGTERM); 双实例恢复在线; real-fake 种子删净(连数据);
src/dst/case 目录删净; BT_backup 只清本用例哈希残留 + 逐文件比对开工快照(queue 记账豁免);
daemon 靠自扫断粮 + 宽限退位自杀(绝不外杀, AGENTS.md 进程安全红线)。
失败判据: A5 日志出现 qb_side_check_failed(假阴性复发); A9 非 mover 未 rewritten 或改写后仍指
SRC; A10 出现 recheck/error/missing 或未全员落位 dst —— 其中 recheck 面为轮询窗内尽力观测(WebAPI
可达且 save_path 未全员落位的 0.4s 窗, qB 启动期/亚秒级重校验不可见), 错向回归由 progress==1.0 /
零 error/missing / save_path 等值断言兜底; A11 job 非 done 或 src 链接残留;
A12 组裂(两颗不同组); A13 有残留或环境未还原。

升档(规程 §08): L2(脚本自动断言, A1-A13 全链)。L3 负向对照未加, 原因: D 级 NEGATIVE 要求 qB
列目录条目 (size, mtime) 与 dst stat 和源侧链接 lstat **双双不符** —— qB 5.2.3 Windows 对本
拓扑只产出两种可判定条目: junction/硬链接 = 目标侧真实元数据(恒 POSITIVE); 文件级 symlink =
链接对象自身元数据(与源侧 lstat 恒相等, 恒 skipped)。无合法产品流可确定性造出「双不符」; 唯一
注入点 = 自检瞬间改文件(亚秒竞态), 不可确定性复现。NEGATIVE 语义已由单测三态守阵
(tests/test_relocate_proof*, 计划 S1 红验)钉死。

跑法: `commands run real.run -- --case RM04-20 --yes`(不要裸 pytest)。
"""
from __future__ import annotations

import argparse
import ctypes
import importlib.util
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]  # tests-real/rm04_relocate -> 仓库根(wrapper 收编版与 .work 都从根派生)
sys.path.insert(0, str(HERE))
import test_rm04_relocate as M  # noqa: E402  (复用 RM04 的造种/清场/断言助手)

from lib import app, guard, instances  # noqa: E402
from auto_qb.core import fastresume as frmod  # noqa: E402  (产品码: fastresume 只读解码)
from auto_qb.core.modules import relocate_units as ru  # noqa: E402  (DAEMON_HEARTBEAT_MAX_AGE 单点)
from auto_qb.infra import relocate_journal as rj  # noqa: E402  (daemon 心跳账只读)

pytestmark = [
    pytest.mark.skipif(sys.platform != "win32", reason="本片断言含 Windows 特有语义(symlink/优雅退出通路)"),
]

# 拓扑单点(钉死, 见模块 docstring): src 在 R: 内存盘, dst 在 .work(D:); 旁路 wrapper 收编入库版
R_ROOT = Path("R:/qbt-fake/rm04")
WRAP = REPO / "tests-real" / "tools" / "daemon_window_wrapper.py"
WRAPPER_LOG = REPO / "tests-real" / ".work" / "tools-daemon-wrapper" / "daemon_wrapper.log"
BT_BACKUP = Path(guard.EXE[instances.SECONDARY]).parent / "profile" / "qBittorrent" / "data" / "BT_backup"
PROD_PORTS = (16585, 26586)  # 生产实例端口(本机事实): 只读识别留痕, 全程零触碰
FILE_NAME = "rm04c20.bin"
FILE_SIZE = 1024 * 1024
PIECE_LENS = (16384, 32768)  # 同文件异 infohash 的区分面(两颗成员)
assert WRAP.is_file(), f"daemon_window_wrapper.py 缺失(收编入库版被移除?): {WRAP}"

# real.up/real.down task id 的同一实现面(runner.py): qB 起停不另写机制, 优雅退出语义/白名单核验
# 全部继承 —— 测试进程内直接调, 与 `commands run real.up -- --port N` 等价(同一脚本同一函数)。
_spec = importlib.util.spec_from_file_location("real_runner", HERE.parent / "runner.py")
REAL_RUNNER = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(REAL_RUNNER)


def qb_up(port: int) -> None:
    rc = REAL_RUNNER.cmd_up(argparse.Namespace(port=str(port), dry_run=False))
    assert rc == 0, f"real.up {port} 失败(rc={rc})"


def qb_down(port: int) -> None:
    """优雅下线(WebAPI app/shutdown + 等端口释放); 绝不 taskkill(real.down 实现面自证)。"""
    rc = REAL_RUNNER.cmd_down(argparse.Namespace(port=str(port), dry_run=False))
    assert rc == 0, f"real.down {port} 失败(rc={rc})"


# ---------------------------------------------------------------- 旁路 runner(产品进程内)

# 仅替换 relocate_exec.ExecMixin._spawn_daemon(产品 docstring 自留测试接缝)—— daemon 经收编入库
# 的 wrapper 拉起(实例级开窗判据; 已授权 2026-11-10, 见模块 docstring)。盘上产品代码零改动;
# sentinel 文件触发的进程内 SIGTERM = Windows 上唯一优雅退出通路(lib/app.py 三条硬事实第 2 条)。
_RUNNER_BYPASS = '''import signal, sys, threading, time, os
WRAP = r"{wrap}"
import auto_qb.core.modules.relocate_exec as rex
_orig_popen = rex.ExecMixin._popen_detached

def _spawn_daemon_bypass(self, data_dir, host, port):
    args = [sys.executable, WRAP, "--data-dir", data_dir, "--host", str(host or ""),
            "--port", str(int(port or 0))]
    _orig_popen(args)  # detached 单点照旧(never taskkill 口径不变)

rex.ExecMixin._spawn_daemon = _spawn_daemon_bypass
from auto_qb import cli
sentinel = sys.argv.pop(2)
def _watch():
    while not os.path.exists(sentinel):
        time.sleep(0.2)
    try:
        os.remove(sentinel)
    except OSError:
        pass
    signal.raise_signal(signal.SIGTERM)
threading.Thread(target=_watch, daemon=True).start()
raise SystemExit(cli.main() or 0)
'''.replace("{wrap}", str(WRAP))


class BypassApp(app.AppProc):
    """产品进程(旁路 runner): 观测面全继承 AppProc, 收尾改走 sentinel 优雅退出。"""
    def __init__(self, popen: subprocess.Popen, case: Path, cfg: Path, sentinel: Path):
        super().__init__(popen, case, cfg)
        self.sentinel = sentinel

    def stop(self, timeout: float = 40.0):
        if not self.alive():
            return self.returncode()
        self.sentinel.write_text("stop", encoding="utf-8")
        try:
            return self.popen.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            self.kill()  # 优雅通路失守才强杀(自造产品进程; RM04-06 同款, qB 进程红线不涉及)
            return self.returncode()


def start_bypass_app(case: Path, cfg: Path) -> BypassApp:
    runner = case / "runner_sigterm.py"
    runner.write_text(_RUNNER_BYPASS, encoding="utf-8")
    sentinel = case / "stop.sentinel"
    if sentinel.exists():
        sentinel.unlink()
    popen = subprocess.Popen(
        [str(app.PY), str(runner), str(cfg), str(sentinel)],
        cwd=str(REPO),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        env={
            **os.environ, "PYTHONIOENCODING": "utf-8"
        },
    )
    return BypassApp(popen, case, cfg, sentinel)


def stop_lingering_product(case: Path) -> None:
    """上一轮残留的产品进程优雅退出(sentinel); 无在跑返回。锁 meta 的 pid 是真解释器(app.real_pid 同款)。"""
    meta = case / "data" / "state.lock.meta.json"
    try:
        pid = int(json.loads(meta.read_text(encoding="utf-8")).get("pid") or 0)
    except (OSError, ValueError, json.JSONDecodeError):
        return
    if pid <= 0 or not _pid_alive(pid):
        return
    (case / "stop.sentinel").write_text("stop", encoding="utf-8")
    M.wait_until(lambda: True if not _pid_alive(pid) else None, 40, f"残留产品进程 {pid} 未按优雅路径退出")


def _pid_alive(pid: int) -> bool:
    k32 = ctypes.windll.kernel32
    h = k32.OpenProcess(0x1000, False, int(pid))  # PROCESS_QUERY_LIMITED_INFORMATION
    if not h:
        return False
    try:
        code = ctypes.c_ulong(0)
        ok = k32.GetExitCodeProcess(h, ctypes.byref(code))
        return bool(ok) and code.value == 259  # STILL_ACTIVE
    finally:
        k32.CloseHandle(h)


# ---------------------------------------------------------------- 配置 / fastresume / 证据面


def _write_cfg(case: Path, web_port: int) -> Path:
    """测试派生配置(生产配置零触碰): 直连副实例 + relocate 开(阈值默认 8) + bt_backup 标量 + WEB 开。

    relocate.bt_backup = 副实例 portable profile 的 BT_backup(由 env_registry EXE 派生, 不手抄
    路径) —— daemon 按 spec.bt_backup 定位 fastresume, 缺它整条改写链静默空转(v8 起单实例
    标量, 旧顶层多实例表已退役且无兼容读法, 计划 26-11-11-0259 S2)。
    """
    cfg = case / "config.yml"
    cfg.write_text(
        f"""config:
    schema_version: 8
    qbittorrent:
        host: 127.0.0.1
        port: {instances.SECONDARY}
        username: ""
        password: ""
    data_dir: "{(case / "data").as_posix()}"
    main_tick: 2S
    sync_interval: 1.5S
    state_save_interval: 30S
    interval: 60S
    log:
        level: INFO
    grouping:
        enabled: true
        cross_group_conflict_check: false
    trackers:
        rm04fake:
            domains: ["{M.FAKE_TRACKER_HOST}"]
    relocate:
        enabled: true
        alias_file_threshold: 8
        bt_backup: "{BT_BACKUP.as_posix()}"
    web:
        enabled: true
        host: 127.0.0.1
        port: {web_port}
        skip_local_verify: true
    notify:
        enabled: false
""",
        encoding="utf-8",
    )
    text = cfg.read_text(encoding="utf-8")
    if f"port: {instances.SECONDARY}" not in text:
        raise AssertionError(f"配置未指向副实例 {instances.SECONDARY}, 拒跑: {cfg}")
    if f"port: {instances.PRIMARY}" in text:
        raise AssertionError(f"配置指向了 {instances.PRIMARY}(真实种子), 拒跑: {cfg}")
    if "schema_version: 8" not in text:
        raise AssertionError(f"配置缺 schema_version: 8(会触发迁移改写), 拒跑: {cfg}")
    return cfg


def fr_path_keys(ih: str) -> dict:
    """fastresume 三路径键原始值(save_path / qBt-savePath / qBt-downloadPath), 剔除空串键。

    空串 qBt-downloadPath 为良性特类(daemon unmatched 原样保留, 实验切片 §04「断言校准」第 1 条), 不参与断言。
    """
    p = frmod.locate_fastresume(BT_BACKUP, ih)
    assert p is not None, f"{ih[:8]} fastresume 不在 BT_backup: {BT_BACKUP}"
    val = frmod.load_fastresume(p)
    out = {}
    for k in (b"save_path", b"qBt-savePath", b"qBt-downloadPath"):
        v = val.get(k)
        if isinstance(v, (bytes, bytearray)) and v.strip():
            out[k.decode()] = v.decode("utf-8", "replace")
    return out


def bt_backup_snapshot() -> dict:
    return {p.name: (p.stat().st_size, int(p.stat().st_mtime)) for p in sorted(BT_BACKUP.iterdir())}


def wrapper_lines() -> list[str]:
    if not WRAPPER_LOG.is_file():
        return []
    return WRAPPER_LOG.read_text(encoding="utf-8", errors="replace").splitlines()


def live_daemon_pid(case: Path) -> int | None:
    """本 case 在位的健康回收 daemon pid(产品 ACT_ENSURE_DAEMON 同判据: pid 活 + 心跳未过期)。

    上一轮用例的 patched daemon 可能仍在宽限窗(60s)内 —— 产品按「健康 watcher 在位不重复拉起」
    复用它, 本轮不新起进程 ⇒ 无新 patch 行属正常。该 watcher 必然经 wrapper 拉起: 写本 case
    daemon.<key>.json 的只有 --data-dir 指向本 case 的 daemon, 而产品进程的 _spawn_daemon 已被
    旁路 runner 单点替换为经 WRAP 拉起(本实例 36596 不存在第二条 daemon 产生通路)。
    """
    key = rj.instance_key("127.0.0.1", instances.SECONDARY)
    data_dir = str(case / "data")
    if rj.daemon_stale(data_dir, key, max_age=ru.DAEMON_HEARTBEAT_MAX_AGE):
        return None
    return int((rj.read_daemon_state(data_dir, key) or {}).get("pid") or 0) or None


def _flush(ev: dict, case: Path) -> None:
    """证据落盘(gitignored .work, 与 visibility 片同落点): 全量断言现场 + 产品日志副本。"""
    ev["ts"] = time.strftime("%Y-%m-%d %H:%M:%S")
    (M.WORK /
     "rm04_20_evidence.json").write_text(json.dumps(ev, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    (M.WORK / "rm04_20_auto-qb.log").write_text(app.read_log(case), encoding="utf-8")


def _require_r_topology() -> None:
    """拓扑钉死的第一半: R: 必须在(环境1 D盘机)。缺席 = 拓扑不成立, skip 不回退(模块 docstring)。"""
    try:
        R_ROOT.mkdir(parents=True, exist_ok=True)
        probe = R_ROOT / ".probe"
        probe.write_bytes(b"x")
        probe.unlink()
    except OSError as e:
        pytest.skip(f"R: 盘缺席/不可写, 跨盘拓扑(src R: vs dst D:)不成立 —— 本用例钉死环境1 D盘机拓扑: {e}")


# ================================================================ RM04-20


def test_rm04_20_rlfn_symlink_window_e2e():
    """[RM04-20] 整组迁移 file_links+symlink 全链真机闭环(13 断言 A1-A13, 断言明细见模块 docstring)

    前置: R: 在 + 双实例在线 + 副实例无 real-fake 残留; wrapper 收编入库版在位; 副实例 BT_backup
          可定位(env_registry EXE 派生)。
    副作用/回滚/失败判据: 见模块 docstring(四行契约)。
    """
    _require_r_topology()
    case = M.case_dir("rm04_20")
    stop_lingering_product(case)
    qb = M.qbfake()
    assert not M.rm_all_fakes(qb), "开跑前 副实例 有 real-fake 残留, 先清场"
    assert BT_BACKUP.is_dir(), f"副实例 BT_backup 不在(env_registry EXE 派生路径失效?): {BT_BACKUP}"

    qb_up(instances.SECONDARY)  # 已在线则 [skip](runner 同一实现面, 无副作用)
    qb_up(instances.PRIMARY)

    ev: dict = {"case": str(case), "bt_backup": str(BT_BACKUP), "topology": {"src_root": str(R_ROOT)}}
    _flush(ev, case)
    job_id = None
    p = None
    h1 = None  # finally 的收尾按"已知多少清多少"推进, 早退时未造的成员不参与清理
    h2 = None
    src = R_ROOT / "rm04_20" / "src"
    dst = case / "dst"
    link = src / FILE_NAME
    snap_before = bt_backup_snapshot()
    wl0 = len(wrapper_lines())  # wrapper 决策日志起点(本用例新增行 = [wl0:])
    try:
        # ---- A1 双实例在线 + connection_status 非 disconnected(§2.4 假红陷阱闸)
        env_rows = {}
        for port in (instances.PRIMARY, instances.SECONDARY):
            rep = guard.check_port(port)
            status = guard.check_online(instances.make(port))
            assert status != "disconnected", f"{port} connection_status=disconnected(假红陷阱), 拒跑"
            env_rows[port] = {"pid": rep["pid"], "image": rep["image"], "connection_status": status}
        ev["A1_env"] = env_rows
        # 生产实例只读识别留痕(零触碰; wrapper 名册按测试前缀窄化, 生产在场不挡窗 —— A8 实证)
        out = subprocess.run(
            ["netstat", "-ano", "-p", "tcp"],
            capture_output=True,
            text=True,
            encoding="gbk",
            errors="replace",
            timeout=20
        ).stdout
        ev["prod_pids_observed"] = sorted(
            {
                ln.split()[4]
                for ln in out.splitlines() if len(ln.split()) >= 5 and ln.split()[0].upper() == "TCP" and
                ln.split()[3].upper() == "LISTENING" and any(ln.split()[1].endswith(f":{pp}") for pp in PROD_PORTS)
            }
        )
        M.purge_tree(src.parent)
        _flush(ev, case)

        # ---- A2 产品实例(派生配置: relocate on + relocate.bt_backup 标量; 旁路 runner 已装)
        web_port = app.free_port()
        cfg = _write_cfg(case, web_port)
        p = start_bypass_app(case, cfg)
        assert p.wait_web(45), f"WEB 没起来:\n{p.log()[-800:]}"
        assert p.wait_log("整组迁移已启用", 20), f"relocate 启动日志缺失(开关没生效?):\n{p.log()[-600:]}"
        ev["A2_product"] = {"web_port": web_port, "cfg": str(cfg)}
        _flush(ev, case)

        # ---- A3 两颗共享文件假种子(同文件异 infohash)归同组
        h1 = M.fake_with_data(qb, FILE_NAME, FILE_SIZE, src, "rm04c20", piece_len=PIECE_LENS[0], write=True)
        h2 = M.fake_with_data(qb, FILE_NAME, FILE_SIZE, src, "rm04c20", piece_len=PIECE_LENS[1], write=False)
        assert h1 != h2, "两颗 infohash 撞车(必须同文件异 infohash)"
        M.wait_complete(qb, [h1, h2], 120)
        M.wait_store_progress(web_port, [h1, h2])  # 迁移闸门读产品快照, 等 1-2 个同步拍追平
        g = M.wait_group(web_port, h1, {h1, h2}, 30, "两颗未归入同一辅种组(共享文件归组前提不成立)")
        kpath, kfiles = M.decode_key(g["key"])
        assert M.norm(kpath) == M.norm(src), f"组键首元不是 src 内容根: {kpath}"
        assert tuple(sorted(kfiles)) == (FILE_NAME, ), f"组键文件列表不符: {kfiles}"
        ev["A3_group_before"] = {"key": g["key"], "members": [h1, h2]}
        _flush(ev, case)

        # ---- A4 整组迁移发起(origin=web 语义): 回执 started + 迁移发起(形态 file_links)
        result = M.cmd_post_and_wait(
            web_port, f"/api/torrents/{h1}/location", {
                "location": str(dst),
                "confirm": True
            }, timeout=60
        )
        item = M.one_started_item(result)
        job_id = item.get("job_id")
        assert job_id, f"回执 started 项缺 job_id: {json.dumps(item, ensure_ascii=False)[:400]}"
        assert p.wait_log("迁移发起", 10), "日志缺「迁移发起」(搬迁没有真正下发)"
        start_line = [ln for ln in M.log_text(case).splitlines() if job_id in ln and "迁移发起" in ln]
        assert any("形态 file_links" in ln for ln in start_line), \
            f"迁移发起未复现事故形态 file_links: {start_line[:3]}"
        ev["A4_started"] = {"job_id": job_id, "line": start_line[-1:]}

        # ---- A5+A6 armed: qB 侧自检 skipped(修复生效第一证据)+ 零 qb_side_check_failed
        job = M.wait_job_phase(case, job_id, {"armed", "failed"}, 240, "job 未到 armed(或提前 failed)")
        assert job.get("phase") == "armed", \
            f"job 未武装: phase={job.get('phase')} reason={job.get('reason')} —— 假阴性复发或闸门拒绝"
        log_lines = M.log_text(case).splitlines()
        job_lines = [ln for ln in log_lines if job_id in ln]
        skipped = [ln for ln in log_lines if "qB 侧自检跳过" in ln and "未解析文件级 symlink" in ln]
        assert skipped, ("日志未见「qB 侧自检跳过(未解析文件级 symlink)」—— 修复证据缺失\n" + "\n".join(job_lines[-40:]))
        assert any(FILE_NAME in ln for ln in skipped), f"skipped 行未指到本组文件: {skipped[:2]}"
        assert not any("qb_side_check_failed" in ln for ln in log_lines), "日志出现 qb_side_check_failed(假阴性复发)"
        assert any("已武装收尾" in ln for ln in log_lines), "日志缺「已武装收尾」(arm 段没走)"
        ev["A5_skipped"] = skipped[-1]
        ev["A6_armed"] = {"phase": job.get("phase")}

        # ---- A7 armed 现场: src 链接位 symlink(穿透可读) + 非 mover fastresume 未被触碰(窗口外零改动)
        ts = {t["hash"]: t for t in qb.torrents()}
        movers = [h for h in (h1, h2) if M.norm(ts[h]["save_path"]) == M.norm(dst)]
        nonmovers = [h for h in (h1, h2) if h not in movers]
        assert len(movers) == 1, f"mover 识别异常: {[(h, ts[h]['save_path']) for h in (h1, h2)]}"
        nonmover = nonmovers[0]
        assert M.reparse_kind(link) == "symlink", f"src 链接位形态非 symlink: {M.reparse_kind(link)}"
        target = os.readlink(str(link))
        assert f"{M.norm(dst)}/{FILE_NAME}" in M.norm(target), f"symlink 未指 dst: {target}"
        assert len(link.read_bytes()) == FILE_SIZE, "经 src 原路径穿透读不到同 size(链没建好)"
        keys = fr_path_keys(nonmover)
        assert keys, f"armed 时 {nonmover[:8]} fastresume 无非空路径键"
        assert all(M.norm(v) == M.norm(src) for v in keys.values()), \
            f"armed 时 {nonmover[:8]} fastresume 已被改写(违反窗口外零触碰): {keys}"
        ev["A7_armed_scene"] = {"mover": movers[0], "nonmover": nonmover, "symlink_target": target, "fr_keys": keys}
        _flush(ev, case)

        # ---- A8 双测试实例优雅下线 -> wrapper 名册窄化开窗(已授权 2026-11-10, 见模块 docstring)
        wl1 = len(wrapper_lines())
        patched = [ln for ln in wrapper_lines()[wl0:] if "patched rd._proc_absent" in ln]
        if not patched:
            reused = live_daemon_pid(case)
            assert reused, ("wrapper 决策日志无新 patch 行且无在位健康 daemon(旁路没装上?)\n" + "\n".join(wrapper_lines()[wl0:][-10:]))
            patched = [f"reused live patched daemon pid={reused}(前轮宽限窗内在位, 产品按健康 watcher 复用)"]
        qb_down(instances.SECONDARY)
        qb_down(instances.PRIMARY)
        ev["A8_down"] = {"wl1": wl1, "patched": patched[-1]}
        _flush(ev, case)

        # ---- A9 daemon 改写非 mover fastresume(journal 账 + fastresume 字节双证)
        def rewrite_settled():
            jr = M.journal_of(case, job_id) or {}
            rws = jr.get("rewrites") or {}
            if rws and all(
                ((rws.get(h) or {}).get("status")) in ("rewritten", "already", "unmatched") for h in (h1, h2)
            ):
                return jr
            return None

        jr = M.wait_until(rewrite_settled, 300, f"daemon 未在下线窗完成改写(job={job_id}; 30s 稳定窗+改写预算内)")
        rws = jr.get("rewrites") or {}
        rec = rws.get(nonmover) or {}
        assert rec.get("status") == "rewritten", f"非 mover {nonmover[:8]} 改写账 status={rec.get('status')} != rewritten"
        assert rec.get("keys"), f"非 mover {nonmover[:8]} 逐键明细缺失: {rec}"
        assert (rws.get(movers[0]) or {}).get("status") in ("already", "rewritten"), \
            f"mover {movers[0][:8]} 改写账异常: {rws.get(movers[0])}"
        keys_after = fr_path_keys(nonmover)
        assert keys_after, f"改写后 {nonmover[:8]} fastresume 无非空路径键"
        assert all(M.norm(v).startswith(M.norm(dst)) for v in keys_after.values()), \
            f"{nonmover[:8]} 改写后未指 dst: {keys_after}"
        M.wait_until(
            lambda: (M.journal_of(case, job_id) or {}).get("phase") == "rewritten" or None, 120,
            "journal 相位未翻 rewritten"
        )
        wnew = wrapper_lines()[wl1:]
        assert any("test_qb=0" in ln and "refused=True" in ln and "absent=True" in ln for ln in wnew), \
            "wrapper 决策日志未见「测试 qB 全下线 => absent=True」开窗判定(名册窄化未生效?)"
        ev["A9_rewrite"] = {
            "rewrites": {
                h[:8]: rws.get(h)
                for h in (h1, h2)
            },
            "fr_keys_after": keys_after,
            "wrapper_new_lines": wnew[-20:]
        }
        _flush(ev, case)

        # ---- A10 重启 -> 全员落位 dst(零 recheck、零 error/missing)
        qb_up(instances.SECONDARY)
        qb_up(instances.PRIMARY)
        checking_seen: list[str] = []

        def all_at_dst():
            cur = {t["hash"]: t for t in qb.torrents()}
            for h in (h1, h2):
                s = (cur.get(h) or {}).get("state") or ""
                if "checking" in s.lower():
                    checking_seen.append(s)
            if all(M.norm((cur.get(h) or {}).get("save_path") or "") == M.norm(dst) for h in (h1, h2)):
                return {h: cur[h]["save_path"] for h in (h1, h2)}
            return None

        M.wait_until(
            all_at_dst, 120, lambda: f"重启后未全员落位 dst: "
            f"{ {h: (qb.torrent(h) or {}).get('save_path') for h in (h1, h2)} }"
        )
        assert not checking_seen, f"观测到重校验(改写链不该引发 recheck): {sorted(set(checking_seen))}"
        for h in (h1, h2):
            t = qb.torrent(h) or {}
            assert t.get("progress") == 1.0, f"{h[:8]} progress != 1.0: {t.get('progress')}"
            assert "error" not in str(t.get("state")).lower() and "missing" not in str(t.get("state")).lower(), \
                f"{h[:8]} 异常态: {t.get('state')}"
        ev["A10_restart"] = {"save_paths": all_at_dst(), "checking_seen": checking_seen}
        _flush(ev, case)

        # ---- A11 job done + 删链门删净别名
        job = M.wait_job_phase(case, job_id, {"done", "failed"}, 300, "job 未收敛到 done")
        assert job.get("phase") == "done", f"job 终态非 done: phase={job.get('phase')} reason={job.get('reason')}"
        assert not os.path.lexists(str(link)), f"src 链接位残留(删链门没删): {link}"
        assert "收尾完成" in M.log_text(case), "日志缺「收尾完成」(收尾链没走)"
        assert not any("qb_side_check_failed" in ln for ln in M.log_text(case).splitlines()), \
            "全程出现 qb_side_check_failed(假阴性复发)"
        ev["A11_done"] = {"phase": job.get("phase"), "reason": job.get("reason"), "src_link_gone": True}

        # ---- A12 组不裂(终态解析登记表退出后, 全员 save_path==dst 组键归一)
        g2 = M.wait_group(web_port, h1, {h1, h2}, 60, "重启后组未归一(两颗不同组 = 裂组)")
        k2 = M.decode_key(g2["key"])
        assert M.norm(k2[0]) == M.norm(dst), f"终态组键首元不是 dst: {k2[0]}"
        assert tuple(sorted(k2[1])) == (FILE_NAME, ), f"终态组键文件列表不符: {k2[1]}"
        ev["A12_group_after"] = {"key": g2["key"]}
        _flush(ev, case)

    finally:
        # ---- A13 收尾: 产品优雅退出 -> 实例恢复 -> 删种子(连数据) -> BT_backup 核净 -> 目录删净
        # 每步独立收集失败(不吞: 结尾聚合重抛, 原始失败信息一并保留); 证据先落盘再删目录。
        ev["A13_cleanup"] = {}
        errs: list[str] = []
        if p is not None:
            try:
                ev["A13_cleanup"]["product_stop_rc"] = p.stop(40)
            except Exception as e:  # noqa: BLE001 —— 收尾失败聚合重抛, 不静默
                errs.append(f"产品停止失败: {e!r}")
        _flush(ev, case)
        for port in (instances.SECONDARY, instances.PRIMARY):
            try:
                qb_up(port)  # 环境还原: 双实例回在线(conftest 模块闸与后续片的开工前提)
            except Exception as e:  # noqa: BLE001
                errs.append(f"real.up {port} 恢复失败: {e!r}")
        try:
            ev["A13_cleanup"]["seeds_removed"] = M.rm_all_fakes(M.qbfake())
        except Exception as e:  # noqa: BLE001
            errs.append(f"real-fake 种子清理失败: {e!r}")
        try:
            removed = []
            my_hashes = [h for h in (h1, h2) if h]
            for ih in my_hashes:
                for suffix in (".fastresume", ".torrent", ".fastresume.bak", ".torrent.bak"):
                    fp = BT_BACKUP / f"{ih}{suffix}"
                    if fp.is_file():
                        fp.unlink()
                        removed.append(fp.name)
            now = bt_backup_snapshot()
            residue = [k for k in now if k not in snap_before and not any(k.startswith(ih) for ih in my_hashes)]
            # 比对面只认开工前已有的逐种子文件; queue = qB 自身记账文件(会话期合法变化, 豁免)
            before_files = {k: v for k, v in snap_before.items() if (BT_BACKUP / k).is_file() and k != "queue"}
            changed = [k for k, v in before_files.items() if now.get(k) != v]
            ev["A13_cleanup"].update(
                {
                    "bt_backup_removed": removed,
                    "residue": residue,
                    "changed": changed,
                    "before_count": len(snap_before),
                    "after_count": len(now)
                }
            )
            if residue:
                errs.append(f"BT_backup 出现非本用例的未知残留: {residue}")
            if changed:
                errs.append(f"开工前已有 BT_backup 逐种子文件被改动: {changed}")
        except Exception as e:  # noqa: BLE001
            errs.append(f"BT_backup 核净失败: {e!r}")
        _flush(ev, case)
        try:
            M.purge_tree(src.parent)  # 只删本用例子树; 产品不删空内容根目录(设计内, 实验切片 §04)
            M.purge_tree(case)
        except Exception as e:  # noqa: BLE001
            errs.append(f"目录清理失败: {e!r}")
        if errs:
            detail = "; ".join(errs)
            raise AssertionError(f"收尾未净(A13): {detail}")
