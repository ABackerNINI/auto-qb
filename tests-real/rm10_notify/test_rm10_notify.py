"""RM10 通知·外部集成 —— 八条真机用例(通知通道 AUMID 注册表面 / 日志→通知管线 / notify_fatal 致命旁路 / YAML 模板导出 / guardian 删链 RM04 遗留收口)。

验证面对准冻结计划 plans/26-10-31-1922-plan-real-RM10.html §03 的八条 spec:
导出正向与真实 qB 域名集对照(RM10-01)· 导出负向对照 dry-run 零写/only-missing 骨架/双跑幂等(RM10-02)·
AUMID 注册表面键值逐字/幂等/legacy .lnk 清理/回退路径(RM10-03)· 通知管线进程级发送尝试计数
(档位/节流/免打扰/去重/enabled 门, RM10-04)· guardian 删链正向三证→verify→removing→removed(RM10-05)·
guardian 负向 verify_mismatch 零删链/终态挡删 stopped(RM10-06)· guardian 参数与互斥面
no_spec/already_running/timeout + CLI 形状(RM10-07)· notify_fatal 直发恰 1 次/防自环/不放大(RM10-08)。

驱动形态(计划 §01): 真 CLI(仅 RM10-01/02, `python -m auto_qb <tests-real 派生配置> --export-yaml …`,
exporter 原样重读 config_path —— 配置一律本片派生件, 红线 config.yml 零触碰)· 进程内直调
(RM10-03/04/08: NotifyConfig/PlatformChannel/setup_notify/notify_fatal 直驱真实代码路径, 真注册表写
+ 真 PowerShell 子进程)· finalize_watch.run 短参直调(RM10-05/06/07: heartbeat/stable/poll/max_wait
全注入, spec 落 <data_dir>/relocate/<job>.spec.json, qB 用死端口/哑 socket 本地构造, 不碰任何真 qB)。

外发红线在本片的兑现(计划 §05 预申报): toast 是系统本地通知, 全片真实 toast 弹出 ≤6 条
(RM10-04 ≤4 实测 2 + RM10-08 ≤2 实测 1), 全部为进程级断言的物理副产物; 零 Webhook/邮件渠道
(v1 仅 platform 单渠道); 不真装浏览器扩展; 导出文件含真实 tracker 域名只落
tests-real/.work/rm10/, 收尾整目录删; AUMID 注册表键按开跑前存在性快照回滚; gtm 零触碰;
真实种子 8 枚全程 paused 零触碰(仅 RM10-01/02 只读扫描)。

跑法: `commands run real.suite -- --slice RM10 --yes`(官方一轮); 单跑
`commands run real.run -- --case RM10-nn --yes`。解析一律 strip, 幂等: 各条自建临时物落
.work/rm10/ 前缀目录自清, guardian job_id 一律 rm10-* 前缀防撞。
"""
from __future__ import annotations

import json
import logging
import os
import re
import shutil
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from lib import app, instances  # noqa: E402

pytestmark = [
    pytest.mark.skipif(sys.platform != "win32", reason="本片断言含 Windows 特有语义(HKCU 注册表/junction/tasklist/PowerShell toast)"),
]

WORK = Path(__file__).resolve().parents[1] / ".work" / "rm10"

from auto_qb.config import NotifyConfig  # noqa: E402
from auto_qb.core import exporter  # noqa: E402
from auto_qb.infra import alias_fs, notify  # noqa: E402
from auto_qb.infra.relocate_journal import (  # noqa: E402
    acquire_pid,
    journal_path,
    pid_path,
    read_journal,
    release_pid,
    write_journal,
    write_spec,
)
from auto_qb.infra.utils import extract_tracker_hostnames  # noqa: E402
from auto_qb.infra.versioning import CURRENT_VERSIONS  # noqa: E402

PROBE_LOGGER = logging.getLogger("auto_qb.rm10probe")  # 防 self-loop 探针(不得以 auto_qb.notify 开头)
PKG_LOGGER = logging.getLogger("auto_qb")
ATTEMPT_WINDOW_S = 12.0  # 发送尝试采样窗: ≥ PlatformChannel.TIMEOUT_S(10s), 防慢派发误判零尝试
GUARDIAN_JOB = "rm10-{}"  # guardian job_id 一律 rm10-* 前缀(计划幂等口径, 防撞生产 job)

# ---------------------------------------------------------------- 通用小件


def metric(line: str) -> None:
    """实测数字落盘(<.work>/rm10/metrics.log): pytest -q 吞掉通过用例的 stdout, 基线切片从这里誊写。"""
    WORK.mkdir(parents=True, exist_ok=True)
    with open(WORK / "metrics.log", "a", encoding="utf-8") as f:
        f.write(f"{time.strftime('%H:%M:%S')} {line}\n")


def _is_link(p) -> bool:
    """链接形态判定(与产品 alias_fs.alias_kind_of 同口径的本地探针; RM04 同款)。"""
    import stat

    try:
        st = os.lstat(p)
    except OSError:
        return None
    tag = getattr(st, "st_reparse_tag", 0)
    return bool(tag) or stat.S_ISLNK(st.st_mode)


def purge_tree(root) -> None:
    """删目录树, **绝不递归删穿链接**(RM04 §08 红线): junction/symlink 只 os.rmdir 本体。

    rglob/glob 会跟随 junction 展开, 所以用 os.walk(topdown) 遇链接剪枝 + 根单独判;
    悬空 junction 的 lstat/rmdir 均可用(lstat 不跟随)。
    """
    root = Path(root)
    if _is_link(root):
        os.rmdir(root)
        return
    if not root.exists():
        return
    for dirpath, dirnames, _files in os.walk(root, topdown=True):
        for d in list(dirnames):
            full = Path(dirpath) / d
            if _is_link(full):
                os.rmdir(full)
                dirnames.remove(d)
    shutil.rmtree(root, ignore_errors=True)


def case_dir(name: str) -> Path:
    """用例专属目录 <tests-real>/.work/rm10/<name>; 开跑先清自己(幂等), 链接安全。"""
    purge_tree(WORK / name)
    d = WORK / name
    d.mkdir(parents=True, exist_ok=True)
    return d


def dead_port() -> int:
    """探空死端口: 本会话不复用(lib/app.free_port 记账), 与白名单 36595/36596 及 26803/60539 段零重叠。"""
    return app.free_port()


# ---------------------------------------------------------------- 通知面(进程表采样)


def _ps_pids() -> set:
    """当前进程表里的 powershell.exe pid 集(tasklist CSV, 与 finalize_watch._names_from_tasklist 同款采样)。"""
    r = subprocess.run(
        ["tasklist", "/NH", "/FO", "CSV"],
        capture_output=True,
        text=True,
        timeout=20,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    pids = set()
    for line in (r.stdout or "").splitlines():
        parts = line.split('","')
        if parts and parts[0].strip('"').strip().lower() == "powershell.exe":
            pids.add(parts[1].strip('"').strip())
    return pids


def send_attempts(emit_fn, window: float = ATTEMPT_WINDOW_S) -> int:
    """「发送尝试」计数 = 采样窗内新出现的 powershell.exe pid 数(进程表采样, 外发红线口径:
    只数子进程出现, 不断言 toast 内容/弹出 —— 那是 L0 目视面)。

    emit_fn 放进后台线程与采样并发: handler 路径的派发是异步的(emit 立即返回, powershell
    在 drain 线程跑), 但 notify_fatal 是**同步** send(子进程随调用出现并退出)—— 不并发采样
    就会在采样开始前错过它(首轮实测 RM10-08① 假红 0 的根因)。
    handler 派发线程逐条 subprocess.run(串行, 不重叠)⇒ 每次尝试 = 恰一个新 pid。
    """
    base = _ps_pids()
    seen = set()
    th = threading.Thread(target=emit_fn, daemon=True)
    th.start()
    deadline = time.time() + window
    while time.time() < deadline:
        seen |= _ps_pids() - base
        time.sleep(0.2)
    th.join(timeout=ATTEMPT_WINDOW_S)
    return len(seen)


def mount(cfg: NotifyConfig):
    """setup_notify 真挂载; 返回 handler(用例收尾统一 unmount)。"""
    return notify.setup_notify(cfg)


def unmount(handler) -> None:
    """卸载并唤醒派发线程优雅退出(logging.shutdown 同款路径)。"""
    if handler is None:
        return
    PKG_LOGGER.removeHandler(handler)
    handler.close()


def pkg_handlers() -> list:
    return list(PKG_LOGGER.handlers)


# ---------------------------------------------------------------- 导出面(CLI 派生配置)


EXPORT_CONFIG_TEMPLATE = """\
config:
    schema_version: 5
    qbittorrent:
        host: 127.0.0.1
        port: 36595
        username: ""
        password: ""
        api_key: "{api_key}"
    data_dir: "{data_dir}"
    main_tick: 2S
    sync_interval: 1.5S
    interval: 86400S
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
        enabled: false
        missing_tag: ""
        check_missing_files: false
    web:
        enabled: false
        host: 127.0.0.1
        port: {web_port}
        skip_local_verify: true
    trackers:
        rm10_probe_invalid:
            domains:
                - rm10probe.invalid
            tags:
                - Rm10Probe
            upload_speed_limit: 0KiB/s
            download_speed_limit: 0KiB/s
            hr:
                required_seeding_time: 3D
                required_share_ratio: 0
                extra_seeding_time: 12H
                condition: 80%
    notify:
        enabled: false
"""

# 派生配置的已配域(与真实 tracker 域零重叠: .invalid 保留 TLD, 计划 §03 RM10-01 前置)
CONFIGURED_DOMAINS = {"rm10probe.invalid"}


def write_export_cfg(case: Path) -> Path:
    """生成 tests-real 派生导出配置(指 36595 真实例, api_key 直连; 红线 config.yml 零触碰)。"""
    api_key = instances.token_for(instances.PRIMARY) or ""
    assert api_key, "36595 缺 token(tests-real/config/instances.local.json)—— 无法派生导出配置"
    cfg = case / "config.yml"
    cfg.write_text(
        EXPORT_CONFIG_TEMPLATE.format(
            api_key=api_key,
            data_dir=(case / "data").as_posix(),
            web_port=app.free_port(),
        ),
        encoding="utf-8",
    )
    text = cfg.read_text(encoding="utf-8")
    assert "port: 36595" in text and "rm10probe.invalid" in text
    return cfg


def qb_aggregated_domains() -> set:
    """从 36595 真实例聚合全部 tracker 域名(与 exporter.collect_all_tracker_hostnames 同函数同口径:
    伪条目 `** [DHT] **` 等 url 取不出 host 会被 _split_url 自然滤掉)。真实种子全程 paused, 只读。"""
    qb = instances.make(instances.PRIMARY)
    domains = set()
    for tor in qb.torrents():
        try:
            domains |= extract_tracker_hostnames(qb.trackers(tor["hash"]))
        except Exception:
            continue
    return domains


def exported_domains(data: dict) -> set:
    return {str((e or {}).get("domains", [None])[0]).strip() for e in data["config"]["trackers"].values()}


def assert_domain_sets_match(actual: set, expected: set) -> None:
    """域名集对照单点(红验共用: 期望集错一位必须在这里红)。"""
    missing = expected - actual
    extra = actual - expected
    assert not missing and not extra, f"域名集不符: 多出={sorted(extra)} 缺失={sorted(missing)}"


# ---------------------------------------------------------------- guardian 面


class _StepClock:
    """假时钟: 每次 +step(注入 finalize_watch.run 的 clock)。step=0.25 时, 第 4 轮 stable=0.5 凑齐。"""

    def __init__(self, step: float = 0.25):
        self.t = -step
        self.step = step

    def __call__(self) -> float:
        self.t += self.step
        return self.t


def _journal_watch(jp: Path, stop: threading.Event, sink: dict) -> None:
    """紧轮询 journal 原文(原子替换, 读到的都是完整内容), 记录出现过的相位与 removing/removed 快照。

    removing→removed 之间只有 _delete_links 的执行时间(≈N×0.25ms), 必须毫秒级轮询才抓得住中间相位;
    这是对「journal 相位链 armed→removing→removed」唯一不碰产品代码的观测法。结果写进 sink:
    {"seen": set, "removing": dict|None, "removed": dict|None}。
    """
    while not stop.is_set():
        try:
            raw = jp.read_bytes()
        except OSError:
            time.sleep(0.0005)
            continue
        if b'"armed"' in raw:
            sink["seen"].add("armed")
        if b'"removing"' in raw:
            sink["seen"].add("removing")
            if sink["removing"] is None:
                try:
                    sink["removing"] = json.loads(raw)
                except Exception:
                    pass
        if b'"removed"' in raw:
            sink["seen"].add("removed")
            if sink["removed"] is None:
                try:
                    sink["removed"] = json.loads(raw)
                except Exception:
                    pass


def _accept_loop(sock: socket.socket, stop: threading.Event) -> None:
    """哑监听 socket 的应答循环: accept 到连接立即关闭(保持端口「可连」, 不占 backlog)。"""
    while not stop.is_set():
        try:
            conn, _ = sock.accept()
            conn.close()
        except OSError:
            if stop.is_set():
                return
            time.sleep(0.02)


def build_guardian_scene(case: Path, job: str, *, n_alias: int = 3, files: list | None = None,
                         spec_files: list | None = None, port: int | None = None) -> tuple[Path, Path, list]:
    """RM10-05/06/07 共享基座: dst 真文件 + alias_fs 产品同款通道建 junction + spec 落盘。

    files = 磁盘真文件 [(rel, size)]; spec_files = spec 里声明的清单(缺省与 files 一致;
    RM10-06① 故意错位时单独给)。返回 (data_dir, dst, alias_paths)。job_id 一律 rm10-* 前缀。
    """
    d = case_dir(case.name)
    data_dir = d / "data"
    dst = d / "dst"
    (dst / "sub").mkdir(parents=True, exist_ok=True)
    disk_files = list(files or [("f1.bin", 1024), ("sub/f2.bin", 2048)])
    for rel, size in disk_files:
        p = dst / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(b"r" * size)
    files_spec = [[rel, size] for rel, size in (spec_files or disk_files)]
    aliases = []
    target = str(dst)
    for i in range(n_alias):
        link = d / f"alias_{i:03d}"
        alias_fs.create_dir_alias(str(link), target, alias_fs.KIND_JUNCTION)
        aliases.append(str(link))
    spec = {
        "files": files_spec,
        "dst": str(dst),
        "alias_paths": aliases,
        "host": "127.0.0.1",
        "port": port if port is not None else dead_port(),
    }
    write_spec(str(data_dir), job, spec)
    return data_dir, dst, aliases


# ================================================================ RM10-01


def test_rm10_01_export_positive():
    """[RM10-01] 导出正向: 真 CLI 全量导出, 域名集与真实 qB 对照

    前置: 36595 connected(真实种子 8 枚全 paused, 只读扫描); tests-real 派生配置
      (tracker 段 rm10probe.invalid 与真实域零重叠); .work/rm10/ 已建。
    副作用: 只读 qB; 写 .work/rm10/rm10_01/export-full.yml 一个本地文件(含真实 tracker 域名,
      不外发, 收尾整目录删)。
    回滚: 删 .work/rm10/rm10_01/。
    失败判据: 文件缺失 / YAML 解析失败 / 域名集与 qB 聚合不符(多、漏、错) / schema_version
      缺失或过期 / tracker 名生成冲突。
    """
    case = case_dir("rm10_01")
    cfg = write_export_cfg(case)
    out = case / "export-full.yml"
    r = app.run_cli([str(cfg), "--export-yaml", str(out)], timeout=120)
    assert r.returncode == 0, f"CLI 导出非 0: rc={r.returncode}\nstdout={r.stdout[-800:]}\nstderr={r.stderr[-800:]}"
    assert out.is_file(), "导出文件缺失"

    data = yaml.safe_load(out.read_text(encoding="utf-8"))
    assert isinstance(data, dict) and "config" in data, "导出 YAML 不可解析或缺 config 块"
    assert data["config"]["schema_version"] == CURRENT_VERSIONS["config"], \
        f"schema_version 应为当前版本 {CURRENT_VERSIONS['config']}, 实际 {data['config'].get('schema_version')!r}"

    aggregated = qb_aggregated_domains()
    expected_missing = exporter.find_missing_domains(aggregated, CONFIGURED_DOMAINS)
    actual = exported_domains(data)
    assert_domain_sets_match(actual, CONFIGURED_DOMAINS | expected_missing)

    names = list(data["config"]["trackers"])
    assert len(names) == len(set(names)), "tracker 名冲突(gen_tracker_name taken 集失守)"
    assert all(re.fullmatch(r"[A-Za-z0-9_]+", n) for n in names), f"tracker 名含非法字符: {names}"
    metric(f"RM10-01 qB域名={len(aggregated)} 缺失={len(expected_missing)} 导出条目={len(names)}")
    purge_tree(case)


# ================================================================ RM10-02


def test_rm10_02_export_negative():
    """[RM10-02] 导出负向对照: dry-run 零写 / only-missing 骨架 / 双跑幂等

    前置: 同 RM10-01(36595 connected 只读; tests-real 派生配置)。
    副作用: 写 .work/rm10/rm10_02/export-missing.yml; dry_run 轮零写; 红验用进程内直调
      exporter(dry_run 门双跑对照, 零 qB)。
    回滚: 删 .work/rm10/rm10_02/。
    失败判据: dry_run 轮文件出现(写侧失守) / 骨架含非 trackers 段 / 双跑字节漂移 / 红验跑不出红。
    """
    case = case_dir("rm10_02")
    cfg = write_export_cfg(case)
    out_dry = case / "export-dry.yml"
    out_m = case / "export-missing.yml"

    # ① dry-run: 日志照打「已导出」但输出文件必须不存在(写路径零触碰)
    r = app.run_cli([str(cfg), "--export-yaml", str(out_dry), "--dry-run"], timeout=120)
    assert r.returncode == 0, f"dry-run 导出非 0: {r.stderr[-500:]}"
    assert "已导出" in (r.stdout + r.stderr), "dry-run 轮缺「已导出」日志"
    assert not out_dry.exists(), "dry_run 轮输出文件出现 —— 写侧失守"

    # ② only-missing: 骨架只含 config.trackers 键(无其它段回显), 已配域不出现
    r = app.run_cli([str(cfg), "--export-yaml", str(out_m), "--only-missing"], timeout=120)
    assert r.returncode == 0, f"only-missing 导出非 0: {r.stderr[-500:]}"
    data = yaml.safe_load(out_m.read_text(encoding="utf-8"))
    assert set(data) == {"config"}, f"顶层多余段: {set(data)}"
    keys = set(data["config"])
    assert keys == {"trackers", "schema_version"}, f"骨架应只含 trackers+schema_version(版本章), 实际 {keys}"
    assert not (exported_domains(data) & CONFIGURED_DOMAINS), "骨架混入已配域"

    # ③ 同参数双跑 → 输出字节级一致(idempotent, tracker 名不漂移)
    first = out_m.read_bytes()
    r = app.run_cli([str(cfg), "--export-yaml", str(out_m), "--only-missing"], timeout=120)
    assert r.returncode == 0
    assert out_m.read_bytes() == first, "双跑输出字节漂移(tracker 名/序不稳定)"

    # 红验(计划 §03 L3): ①期望域名集错一位 → 对照断言必须红; ②摘掉 dry_run 判断 → 零写断言必须红
    aggregated = qb_aggregated_domains()
    expected_missing = exporter.find_missing_domains(aggregated, CONFIGURED_DOMAINS)
    try:
        assert_domain_sets_match(CONFIGURED_DOMAINS | expected_missing, CONFIGURED_DOMAINS | expected_missing | {"bogus.rm10.invalid"})
    except AssertionError:
        pass
    else:
        raise AssertionError("红验失败: 期望域名集错一位, 对照断言没有红")

    class _StubApi:  # 零种子桩: 只为走 exporter 真实写路径(不连 qB)
        def torrents_info(self):
            return []

        def torrents_trackers(self, _h):
            return []

    stub_cfg = type("C", (), {"trackers": {}})()
    out_red = case / "export-red.yml"
    exporter.export_yaml_template(_StubApi(), stub_cfg, str(cfg), str(out_red), True)
    assert not out_red.exists(), "红验失败: dry_run=True 仍写出 —— 零写断言没有红"
    exporter.export_yaml_template(_StubApi(), stub_cfg, str(cfg), str(out_red), False)
    assert out_red.exists(), "红验失败: dry_run=False 未写出 —— 写路径没被走到"

    metric(f"RM10-02 dry零写=ok 骨架条目={len(data['config']['trackers'])} 双跑字节一致=ok")
    purge_tree(case)


# ================================================================ RM10-03


AUMID_KEY = rf"Software\Classes\AppUserModelId\{notify.WINDOWS_TOAST_APPID}"


def _aumid_values() -> dict:
    import winreg

    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, AUMID_KEY) as key:
        vals = {}
        i = 0
        while True:
            try:
                name, value, _ = winreg.EnumValue(key, i)
            except OSError:
                break
            vals[name] = value
            i += 1
        return vals


def _aumid_exists() -> bool:
    import winreg

    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, AUMID_KEY):
            return True
    except OSError:
        return False


def _make_probe_lnk(path: str) -> None:
    """造真实探针 .lnk(WScript.Shell COM, TargetPath 指 notepad): 产品 legacy 清理只判 exists+remove,
    但用真 .lnk 更忠实 —— 造不出来就响亮失败, 不静默降级。"""
    r = subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-Command",
         f"$ws = New-Object -ComObject WScript.Shell; "
         f"$s = $ws.CreateShortcut('{path}'); $s.TargetPath = 'C:\\Windows\\System32\\notepad.exe'; $s.Save()"],
        capture_output=True, text=True, timeout=30,
    )
    assert r.returncode == 0 and os.path.exists(path), f"探针 .lnk 造法失败: {r.stderr[-300:]}"


def test_rm10_03_aumid_registry(monkeypatch, caplog):
    """[RM10-03] AUMID 注册表面: 键值逐字 / 幂等 / legacy .lnk 清理 / 回退路径

    前置: 记录 AUMID 键开跑前存在性快照(HKCU\\Software\\Classes\\AppUserModelId\\AutoQB.UI);
      探针 AutoQB.UI.lnk / AutoQB.lnk 自造于 Start Menu\\Programs。
    副作用: 真写 HKCU 一个键(产品有意行为, 每进程构造期幂等覆盖); 删自造探针 .lnk。
    回滚: 开跑前键不存在 → 收尾删除还原; 在 → 原样保留(产品态); 探针 .lnk 已删不补。
    失败判据: 键缺失 / 值与常量不符 / 重复构造漂移 / 探针 .lnk 残留 / 回退路径未回退。
    """
    import winreg

    existed_before = _aumid_exists()
    appdata = os.environ.get("APPDATA", "")
    programs = os.path.join(appdata, "Microsoft", "Windows", "Start Menu", "Programs")
    probes = [os.path.join(programs, name) for name in notify.LEGACY_SHORTCUTS]
    for p in probes:
        assert not os.path.exists(p), f"探针位被占(非本用例自造), 拒跑: {p}"
    try:
        for p in probes:
            _make_probe_lnk(p)

        ch = notify.PlatformChannel()  # 进程内直调: 真注册表写
        assert ch._appid == notify.WINDOWS_TOAST_APPID, f"来源标识应为主 AUMID, 实际 {ch._appid!r}"
        assert _aumid_exists(), "构造后 AUMID 键缺失"
        vals = _aumid_values()
        assert vals.get("DisplayName") == "auto-qb", f"DisplayName 与常量不符: {vals.get('DisplayName')!r}"
        assert vals.get("IconUri") == notify.ICON_ICO, f"IconUri 与常量不符: {vals.get('IconUri')!r}"
        assert os.path.isabs(str(vals.get("IconUri"))) and vals.get("IconUri", "").endswith("assets\\icon.ico"), \
            "IconUri 应为 assets/icon.ico 绝对路径"

        ch2 = notify.PlatformChannel()  # 重复构造: 幂等覆盖写, 值稳定
        assert ch2._appid == notify.WINDOWS_TOAST_APPID
        assert _aumid_values() == vals, "重复构造后键值漂移(幂等覆盖写失守)"

        for p in probes:  # legacy 清理: 预置探针 .lnk 被构造过程删除
            assert not os.path.exists(p), f"legacy .lnk 未被清理: {p}"

        # 回退路径: 注册表故意拒写(OSError)→ 回退 PowerShell AUMID + DEBUG 日志
        def _refuse():
            raise OSError("rm10 probe: registry refuse")

        monkeypatch.setattr(notify.PlatformChannel, "_register_appid_registry", staticmethod(_refuse))
        with caplog.at_level(logging.DEBUG, logger="auto_qb.infra.notify"):
            ch3 = notify.PlatformChannel()
        assert ch3._appid == notify.WINDOWS_TOAST_APPID_FALLBACK, \
            f"拒写场景应回退 {notify.WINDOWS_TOAST_APPID_FALLBACK!r}, 实际 {ch3._appid!r}"
        assert any("回退" in rec.getMessage() for rec in caplog.records), "回退路径缺 DEBUG 日志"
        metric(f"RM10-03 键开跑前存在={existed_before} 键值逐字=ok 幂等=ok 探针清理=ok 回退=ok")
    finally:
        for p in probes:  # 探针 .lnk 残留兜底清理(已删不补)
            try:
                os.remove(p)
            except OSError:
                pass
        if not existed_before:  # 注册表按开跑前快照回滚: 原不存在 → 删除还原
            try:
                winreg.DeleteKey(winreg.HKEY_CURRENT_USER, AUMID_KEY)
            except OSError:
                pass
    if existed_before:
        assert _aumid_exists(), "开跑前已存在的键被误删"
    else:
        assert not _aumid_exists(), "开跑前不存在的键未回滚"
    assert not pkg_handlers(), "本用例不应挂任何通知 handler"


# ================================================================ RM10-04


def test_rm10_04_notify_pipeline():
    """[RM10-04] 通知管线进程级: 发送尝试计数(档位/免打扰/去重/enabled 门)

    前置: .work/rm10/ 临时数据目录; 采样窗口 ≥ TIMEOUT_S(10s)防误判; 各子步间重挂 handler
      清 throttle 态。⚠ 本条桌面会弹 ≤4 条真实 toast(实测 2 条: 子步①④各 1, 计划 §05 预申报)。
    副作用: 桌面 toast ≤4 条; PowerShell 子进程 ≤4 个(自然退出); 无持久物。
    回滚: unmount handler(close 路径), 校验 auto_qb logger 零残留 handler。
    失败判据: ERROR 零尝试 / WARNING 出尝试 / 免打扰出尝试 / 双发 2 次 / enabled=False 仍尝试。
    """
    base_cfg = dict(min_level="ERROR", max_per_hour=3, dedup_window=60.0)

    try:
        # ① ERROR → 恰 1 次发送尝试
        h1 = mount(NotifyConfig(enabled=True, **base_cfg))
        assert h1 is not None
        n1 = send_attempts(lambda: PROBE_LOGGER.error("rm10-04 ERROR probe A"))
        unmount(h1)
        assert n1 == 1, f"ERROR 应恰 1 次发送尝试, 实际 {n1}"

        # ② WARNING(min_level=ERROR)→ 零尝试
        h2 = mount(NotifyConfig(enabled=True, **base_cfg))
        n2 = send_attempts(lambda: PROBE_LOGGER.warning("rm10-04 WARNING probe B"))
        unmount(h2)
        assert n2 == 0, f"WARNING 不应触发发送尝试, 实际 {n2}"

        # ③ quiet_hours 覆盖当前时刻(00:00-23:59 全天, 分钟粒度端点含)→ ERROR 零尝试
        h3 = mount(NotifyConfig(enabled=True, quiet_hours="00:00-23:59", **base_cfg))
        n3 = send_attempts(lambda: PROBE_LOGGER.error("rm10-04 quiet probe C"))
        unmount(h3)
        assert n3 == 0, f"免打扰时段不应触发发送尝试, 实际 {n3}"

        # ④ 同源消息双发 → 仍恰 1(dedup)
        h4 = mount(NotifyConfig(enabled=True, **base_cfg))

        def _double():
            PROBE_LOGGER.error("rm10-04 dedup probe D")
            PROBE_LOGGER.error("rm10-04 dedup probe D")

        n4 = send_attempts(_double)
        unmount(h4)
        assert n4 == 1, f"同源双发应恰 1 次尝试(dedup), 实际 {n4}"

        # ⑤ 红验(计划 §04 L3 双对照之一): enabled=False 不挂载 → ERROR 零尝试
        #    (①「ERROR 必有尝试」+ ⑤「关开关必零」成对: 摘掉 enabled 门, ⑤必红; 管线断, ①必红)
        assert mount(NotifyConfig(enabled=False, **base_cfg)) is None, "enabled=False 不应挂载 handler"
        n5 = send_attempts(lambda: PROBE_LOGGER.error("rm10-04 disabled probe E"))
        assert n5 == 0, f"enabled=False 仍触发发送尝试({n5}) —— 开关失守"

        metric(f"RM10-04 尝试计数 ERROR=1 WARN={n2} quiet={n3} dedup=1 disabled={n5} toast=2")
    finally:
        for h in pkg_handlers():
            PKG_LOGGER.removeHandler(h)
            h.close()
    assert not pkg_handlers(), "收尾后 auto_qb logger 仍有残留 handler"


# ================================================================ RM10-05


def test_rm10_05_guardian_removed():
    """[RM10-05] guardian 删链正向(RM04 遗留): 三证 → verify → removing → removed

    前置: 死端口经探空确认(app.free_port 会话不复用); 别名用 alias_fs 产品同款通道建
      (junction, 判 kind 才算数); job_id 前缀 rm10-; 零 qB 参与(spec 指死端口)。
    副作用: 建/删 .work 内 300 条 junction 与小文件; 写 spec/journal/pid 文件。
    回滚: purge_tree 整 case 目录(链接安全删法, 绝不递归删穿)。
    失败判据: 结论非 removed / 相位链缺失或乱序 / 链接未删 / dst 文件被误碰 / qb_down_evidence 缺字段。
    """
    from auto_qb.tools import finalize_watch

    case = case_dir("rm10_05")
    job = GUARDIAN_JOB.format("05")
    data_dir, dst, aliases = build_guardian_scene(case, job, n_alias=300)
    assert all(alias_fs.alias_kind_of(a) == alias_fs.KIND_JUNCTION for a in aliases), "别名未以 junction 落地"
    jp = Path(journal_path(str(data_dir), job))
    stop = threading.Event()
    sink = {"seen": set(), "removing": None, "removed": None}
    watcher = threading.Thread(target=_journal_watch, args=(jp, stop, sink), daemon=True)
    watcher.start()
    try:
        # 假时钟: 每轮 +0.25 ⇒ 第 4 轮 stable=0.5 凑齐动手; sleep 注入让出 GIL 给 watcher
        result = finalize_watch.run(str(data_dir), job, heartbeat=0.2, stable=0.5, poll=0.1,
                                    clock=_StepClock(0.25), sleep=lambda _s: time.sleep(0.01))
    finally:
        stop.set()
        watcher.join(timeout=5)
    seen = sink["seen"]
    removing_snap = sink["removing"]
    removed_snap = sink["removed"]

    assert result == "removed", f"结论应 removed, 实际 {result}"
    assert {"armed", "removing", "removed"} <= seen, f"journal 相位链不全: {seen}"
    assert removing_snap and set((removing_snap.get("qb_down_evidence") or {})) == \
        {"proc_absent", "port_refused", "stable_secs"}, f"removing 缺 qb_down_evidence 三字段: {removing_snap}"
    assert removed_snap and (removed_snap.get("checks") or {}).get("links_removed") == len(aliases), \
        f"removed.checks.links_removed 应为 {len(aliases)}: {removed_snap}"
    final = read_journal(str(data_dir), job) or {}
    assert str(final.get("phase")) == "removed", f"journal 终相应 removed: {final.get('phase')!r}"
    assert all(alias_fs.alias_kind_of(a) is None for a in aliases), "junction 未被真删"
    assert (dst / "f1.bin").stat().st_size == 1024 and (dst / "sub" / "f2.bin").stat().st_size == 2048, "dst 文件被误碰"
    metric(f"RM10-05 removed 相位链={'/'.join(sorted(seen))} 别名={len(aliases)} dst完整=ok")
    purge_tree(case)


# ================================================================ RM10-06


def test_rm10_06_guardian_negative():
    """[RM10-06] guardian 负向对照: verify_mismatch 零删链 / 终态挡删 stopped

    前置: 同 RM10-05 基座两路; ②路先 write_journal(phase=done) 再 run。
    副作用: 同 RM10-05(①路别名必须存活; ②路别名必须存活)。
    回滚: purge_tree 整 case 目录。
    失败判据: ①路删了任何链接(红验本体) / 结论错 / 终态被心跳覆盖 / ②路动了别名。
    """
    from auto_qb.tools import finalize_watch

    case = case_dir("rm10_06")

    # ① spec.files 故意错 size → verify_mismatch, 一个链接都不删(保守默认, 黄金法则 2 真机红验)
    job_a = GUARDIAN_JOB.format("06a")
    data_a, dst_a, aliases_a = build_guardian_scene(
        case, job_a, n_alias=5,
        spec_files=[("f1.bin", 999), ("sub/f2.bin", 2048)],  # 磁盘 f1.bin 实际 1024, spec 故意错位
    )
    r_a = finalize_watch.run(str(data_a), job_a, heartbeat=0.2, stable=0.5, poll=0.1,
                             clock=_StepClock(0.3), sleep=lambda _s: time.sleep(0.01))
    assert r_a == "verify_mismatch", f"①路结论应 verify_mismatch, 实际 {r_a}"
    ja = read_journal(str(data_a), job_a) or {}
    assert str(ja.get("phase")) == "failed" and str(ja.get("reason")) == "verify_mismatch", f"①路 journal: {ja}"
    assert all(alias_fs.alias_kind_of(a) == alias_fs.KIND_JUNCTION for a in aliases_a), \
        "红验命中: verify_mismatch 路删了链接 —— 保守默认失守"
    assert (dst_a / "f1.bin").stat().st_size == 1024, "①路 dst 被误碰"

    # ② 三证凑齐前预写 journal 终态 phase=done → stopped, 零删除, 终态未被心跳覆盖(前向合并)
    job_b = GUARDIAN_JOB.format("06b")
    data_b, dst_b, aliases_b = build_guardian_scene(case, job_b, n_alias=3)
    assert write_journal(str(data_b), job_b, {"phase": "done", "reason": "external"}), "预写终态失败"
    r_b = finalize_watch.run(str(data_b), job_b, heartbeat=0.2, stable=0.5, poll=0.1,
                             clock=_StepClock(0.3), sleep=lambda _s: time.sleep(0.01))
    assert r_b == "stopped", f"②路结论应 stopped, 实际 {r_b}"
    jb = read_journal(str(data_b), job_b) or {}
    assert str(jb.get("phase")) == "done", f"终态被心跳覆盖: {jb.get('phase')!r}"
    assert all(alias_fs.alias_kind_of(a) == alias_fs.KIND_JUNCTION for a in aliases_b), "②路动了别名"

    metric("RM10-06 verify_mismatch零删链=ok 终态挡删=ok")
    purge_tree(case)


# ================================================================ RM10-07


def test_rm10_07_guardian_params_mutex():
    """[RM10-07] guardian 参数与互斥面: no_spec / already_running / timeout + CLI 形状

    前置: 哑监听 socket 用例内自起自关(本机回环临时端口, 非白名单实例端口); 死端口探空。
    副作用: .work 内 spec/journal/pid 文件; 哑 socket 短暂监听。
    回滚: purge_tree 整 case 目录; 关 socket; release_pid。
    失败判据: 结论串错 / 占锁下第二实例仍动手 / timeout 路删了链接或无 armed 心跳 / argparse 退出码 0。
    """
    from auto_qb.tools import finalize_watch

    case = case_dir("rm10_07")

    # ① 空 data_dir → no_spec(零动作: pid/journal 都不该出现)
    empty = case / "empty_data"
    empty.mkdir(parents=True, exist_ok=True)
    assert finalize_watch.run(str(empty), GUARDIAN_JOB.format("07a")) == "no_spec"
    assert not Path(pid_path(str(empty), GUARDIAN_JOB.format("07a"))).exists(), "no_spec 却动了 pid 锁"
    assert not Path(journal_path(str(empty), GUARDIAN_JOB.format("07a"))).exists(), "no_spec 却写了 journal"

    # ② 先 acquire_pid 占锁再 run → already_running(单 guardian 不变量); 第二实例零动作
    job_b = GUARDIAN_JOB.format("07b")
    data_b, dst_b, aliases_b = build_guardian_scene(case, job_b, n_alias=2)
    assert acquire_pid(str(data_b), job_b), "预占 pid 锁失败"
    try:
        assert finalize_watch.run(str(data_b), job_b, heartbeat=0.2, stable=0.5, poll=0.1,
                                  clock=_StepClock(0.3), sleep=lambda _s: time.sleep(0.01)) == "already_running", \
            "占锁下第二实例未让位"
        assert all(alias_fs.alias_kind_of(a) == alias_fs.KIND_JUNCTION for a in aliases_b), "占锁路动了别名"
        assert Path(pid_path(str(data_b), job_b)).exists(), "占锁路误清了持锁者的 pid 文件"
    finally:
        release_pid(str(data_b), job_b)

    # ③ spec 就绪 + qB「在跑」面(哑监听 socket, accept 线程随连随关)→ max_wait 到期 timeout、
    #    零删除、armed 心跳已落盘。!listen backlog 不 accept 会失真: 首个探测连接占满 backlog(1)
    #    后, guardian 后续探测全部拒连 ⇒ 它看到的就是「qB 已退」按设计删链(首轮实测假红根因:
    #    timeout 期望变成 removed)—— 产品三证逻辑无缺陷, 哑 socket 必须真应答连接。
    job_c = GUARDIAN_JOB.format("07c")
    data_c, dst_c, aliases_c = build_guardian_scene(case, job_c, n_alias=2)
    dummy = socket.socket()
    stop_accept = threading.Event()
    acceptor = threading.Thread(target=_accept_loop, args=(dummy, stop_accept), daemon=True)
    try:
        dummy.bind(("127.0.0.1", 0))
        dummy.listen(8)
        dummy.settimeout(0.2)
        acceptor.start()
        live_port = dummy.getsockname()[1]
        assert live_port not in (36595, 36596, 26803, 60539), f"哑 socket 端口撞禁用面: {live_port}"
        spec_path_c = data_c / "relocate" / f"{job_c}.spec.json"
        spec_c = json.loads(spec_path_c.read_text(encoding="utf-8"))
        spec_c["port"] = live_port
        spec_path_c.write_text(json.dumps(spec_c, ensure_ascii=False), encoding="utf-8")
        r_c = finalize_watch.run(str(data_c), job_c, heartbeat=0.2, stable=0.5, poll=0.1, max_wait=1.0)
        assert r_c == "timeout", f"③路结论应 timeout, 实际 {r_c}"
        jc = read_journal(str(data_c), job_c) or {}
        assert str(jc.get("phase")) == "armed", f"timeout 路缺 armed 心跳: {jc.get('phase')!r}"
        assert all(alias_fs.alias_kind_of(a) == alias_fs.KIND_JUNCTION for a in aliases_c), "timeout 路删了链接"
    finally:
        stop_accept.set()
        acceptor.join(timeout=3)
        dummy.close()

    # ④ CLI 形状: 缺 --data-dir/--job → argparse 非 0
    r = subprocess.run([str(app.PY), "-m", "auto_qb.tools.finalize_watch"], capture_output=True,
                       text=True, cwd=str(app.ROOT), timeout=60,
                       env={**os.environ, "PYTHONIOENCODING": "utf-8"})
    assert r.returncode != 0, "缺参应 argparse 非 0"
    assert "--data-dir" in (r.stderr + r.stdout), "缺参报错未提示 --data-dir"

    metric("RM10-07 no_spec/already_running/timeout/CLI形状 全对")
    purge_tree(case)


# ================================================================ RM10-08


def test_rm10_08_notify_fatal(monkeypatch):
    """[RM10-08] notify_fatal 致命旁路: 直发恰 1 次 / 防自环 / 不放大

    前置: .work/rm10/ 临时目录; 采样窗口同 RM10-04。⚠ 本条桌面会弹 ≤2 条真实 toast(实测 1 条:
    子步①, 计划 §05 预申报)。
    副作用: 桌面 toast ≤2 条; PowerShell 子进程 ≤2 个(自然退出); 无持久物。
    回滚: 无持久物; unmount handler 校验零残留。
    失败判据: 直发零尝试或多次 / 自环 logger 触发尝试 / notify_fatal 异常逃逸。
    """
    try:
        # ① 直发恰 1 次, 且不受 max_per_hour=0 影响(旁路语义: 不过 handler/节流)
        n1 = send_attempts(lambda: notify.notify_fatal(
            "rm10-08 fatal probe", NotifyConfig(enabled=True, max_per_hour=0)))
        assert n1 == 1, f"notify_fatal 应恰 1 次发送尝试, 实际 {n1}"

        # ② 防自环: 挂真 handler 后经 auto_qb.notify 前缀 logger emit → 零尝试(NOTIFY_LOGGER_PREFIX 门)
        h = mount(NotifyConfig(enabled=True, min_level="ERROR", max_per_hour=20, dedup_window=60.0))
        assert h is not None
        n2 = send_attempts(
            lambda: logging.getLogger("auto_qb.notify.rm10probe").error("rm10-08 selfloop probe"))
        unmount(h)
        assert n2 == 0, f"自环 logger 触发了发送尝试({n2}) —— NOTIFY_LOGGER_PREFIX 门失守"

        # ③ cli.py 顶层异常出口形状: PlatformChannel 构造失败 → notify_fatal 吞掉不放大, 进程存活
        class _BoomChannel:
            def __init__(self, *a, **k):
                raise OSError("rm10 probe: channel refuse")

        monkeypatch.setattr(notify, "PlatformChannel", _BoomChannel)
        notify.notify_fatal("rm10-08 raise probe", NotifyConfig(enabled=True))  # 不外抛即过
        notify.notify_fatal("rm10-08 none probe", None)  # config=None 静默返回
        metric(f"RM10-08 fatal尝试={n1} 自环={n2} 不放大=ok toast=1")
    finally:
        for hh in pkg_handlers():
            PKG_LOGGER.removeHandler(hh)
            hh.close()
    assert not pkg_handlers(), "收尾后 auto_qb logger 仍有残留 handler"
