"""真机轨安全边界守卫(issue 26-11-02-1208 复验).

## 测试计划
2026-11-02 issue 26-11-02-1208 复验(L490 前置改显式入口, 移除隐藏卷依赖):
- test_tests_real_source_has_no_hidden_volume_access: 扫描 tests/real/ 源码, 禁止
  FindFirstVolumeW/FindNextVolumeW/卷 GUID 字面量/隐藏卷 junction 构造函数名;
  一旦有人再引入隐藏卷路径即红。
- test_small_target_guard_rejects_unsafe_paths: 入口守卫拒绝 UNC/无盘符/系统盘/
  reparse point/hidden 属性; 普通临时目录放行 (受控桩分支把 SystemDrive 指向非系统
  盘符且桩掉祖先属性, 不依赖 tmp_path 所在卷/目录属性)。
- test_small_target_missing_env_fails_with_instructions: 未设入口环境变量时显式失败,
  提示里含准备指引(不是 skip)。
- test_label_forbidden_keywords: Recovery/System/EFI 类卷标关键词判定。

2026-11-06 issue 26-11-06-0448 修复(real.down 强杀 → WebAPI app/shutdown 优雅退出):
- test_real_down_source_has_no_forced_kill: 扫 tests/real/runner.py 禁止进程强杀字面量,
  并要求 cmd_down 走 .shutdown(); 旧实现(Stop-Process -Force)必红。
- test_cmd_down_dry_run_never_touches_webapi: dry-run 零副作用, 不核验进程也不发 API。
- test_cmd_down_uses_webapi_shutdown_and_waits_for_port_release: 正常路径只发一次 shutdown,
  带 pid 回执并等端口释放。
- test_cmd_down_skips_when_port_not_listening: 实例没起 -> skip, 不误发 shutdown。
- test_cmd_down_refuses_non_test_instance: 镜像路径核验失败 -> rc=1 且不发 shutdown。
- test_cmd_down_fails_closed_on_api_error: API 失败 -> rc=1, 不回退强杀。
- test_cmd_down_reports_timeout_without_force_kill: 等退出超时 -> rc=1 如实报, 不强杀。
- test_qb_shutdown_is_post_with_empty_body: app/shutdown 是空体 POST(不是 GET)。
- test_qb_default_calls_stay_get: 默认读端点仍是 GET, 防 _open 改动带偏既有调用。

2026-11-13 issue 26-11-12-2345 修复(real.seed.clean 证据保护闸):
- test_seed_clean_refuses_unknown_work_top_level: .work 顶层出现 seeds/rmNN 之外的内容
  (results 目录/散装 json)即拒跑 rc=1, dry-run 与 --yes 同拒且一个文件都不删;
  拒跑信息逐项列出未知内容并带 issue 指称。
- test_seed_clean_explicit_dir_named_subtree_bypasses_guard: --dir 指名子树不过闸、只清
  指名处不波及证据; --dir 指 .work 本体与默认同闸。
- test_seed_allowed_rejects_prefix_sibling_dir(评审轮1发现): 白名单按路径分量判严格包含,
  .work 同前缀兄弟目录拒收(SystemExit), 落点内的路径照常放行。

2026-11-21 issue 26-11-21-0638 修复(clean 整扫对 rmNN 内层不设防, RM11 实损 38 份取证):
- test_seed_clean_refuses_rmnn_case_dirs_with_files: rmNN 内层有文件即整单拒跑
  (dry-run/--yes 同拒, seeds/ 也不清), 拒跑信息列出各 rmNN 的内层文件清单与 issue 指称;
  --dir 指名 rmNN 子树仍是显式豁免口, 且指名清不波及 seeds/。
- test_seed_clean_sweeps_seeds_and_ram_when_no_case_files(原
  test_seed_clean_sweeps_known_namespaces_when_no_strays 收紧后重写): rmNN 零文件空壳
  (含空子目录)照旧整扫收掉, seeds/ 与 R: 内存盘根清扫契约不变; dry-run 零删除。

2026-11-21 issue 26-11-21-0639 修复(guard「真实种子」计数把 real-fake 假种子计入):
- test_guard_snapshot_skips_tagged_seeds: snapshot 的 skip_tags 语义 —— 带标签的不暂停
  不计入保护面, 缺省裸调才会把假种子计入(即 0639 的误标源)。
- test_real_guard_snapshot_callers_pass_skip_tags: 静态守阵 —— tests/real 里所有
  snapshot 调用必须显式传 skip_tags; 自带已知违规活性探针, 防守阵死分支。
- test_cmd_guard_reports_real_and_fake_counts / test_cmd_pause_all_skips_fakes:
  两条命令把豁免标签传给 snapshot, 且计数双口径(真实 N / 自造 M)分开报。
"""
from __future__ import annotations

import importlib.util
import os
import stat
import sys
import types
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
TESTS_REAL = ROOT / "tests/real"


def _load_small_target():
    p = TESTS_REAL / "lib" / "small_target.py"
    spec = importlib.util.spec_from_file_location("real_small_target_guard", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.mark.skipif(sys.platform != "win32", reason="Windows 盘符/卷标/属性语义")  # owner: abacker
def test_tests_real_source_has_no_hidden_volume_access():
    forbidden = (
        "FindFirstVolumeW",
        "FindNextVolumeW",
        "FindFirstVolume(",
        "FindNextVolume(",
        "small_volume_junction",
        "_volume_roots",
        "Volume{",
    )
    hits = []
    for f in sorted(TESTS_REAL.rglob("*.py")):
        text = f.read_text(encoding="utf-8", errors="ignore")
        for token in forbidden:
            if token in text:
                hits.append(f"{f.relative_to(ROOT)}: {token}")
    assert not hits, "真机轨源码出现隐藏卷枚举/挂接路径(已废弃并禁止):\n" + "\n".join(hits)


@pytest.mark.skipif(sys.platform != "win32", reason="Windows 盘符/卷标/属性语义")  # owner: abacker
def test_small_target_guard_rejects_unsafe_paths(tmp_path, monkeypatch):
    mod = _load_small_target()
    with pytest.raises(AssertionError, match="UNC"):
        mod.assert_safe_target("\\\\?\\Volume{deadbeef}\\")
    with pytest.raises(AssertionError, match="绝对路径"):
        mod.assert_safe_target("C:relative-real-machine-no-drive")
    sysdrive = os.environ.get("SystemDrive") or "C:"
    with pytest.raises(AssertionError, match="系统卷"):
        mod.assert_safe_target(sysdrive + "\\")

    # reparse point / hidden 用受控桩验证判定分支, 不在真实盘上建 junction/改属性
    # (真机轨里的显式入口守卫本身会读真实属性; 这里只守控制流, 避免测试自己造副作用)
    # 本机临时目录可能落在系统卷 (TMP=C:), 守卫会在系统卷检查处提前拒绝; 受控桩分支
    # 先把 SystemDrive 指向不存在的盘符, 使控制流测试不依赖 tmp_path 所在卷。
    monkeypatch.setenv("SystemDrive", "Z:")
    real_dir = tmp_path / "real"
    real_dir.mkdir()
    (real_dir / "link").mkdir()
    monkeypatch.setattr(mod, "_is_link", lambda p: Path(p).name == "link")
    # 祖先目录在真实盘上可能带 hidden/system 属性 (本机 tmp 落在 AppData 下), 受控桩一律返回 0,
    # 只让 "hid" 命中 hidden 分支 —— 否则会先撞祖先属性检查, 测不到目标分支。
    monkeypatch.setattr(mod, "_get_attrs", lambda p: 0)
    with pytest.raises(AssertionError, match="reparse"):
        mod.assert_safe_target(str(real_dir / "link"))

    (real_dir / "hid").mkdir()
    monkeypatch.setattr(
        mod,
        "_get_attrs",
        lambda p: (stat.FILE_ATTRIBUTE_HIDDEN | stat.FILE_ATTRIBUTE_DIRECTORY if Path(p).name == "hid" else 0),
    )
    with pytest.raises(AssertionError, match="hidden"):
        mod.assert_safe_target(str(real_dir / "hid"))


def test_small_target_missing_env_fails_with_instructions(monkeypatch):
    mod = _load_small_target()
    monkeypatch.delenv(mod.SMALL_TARGET_ENV, raising=False)
    with pytest.raises(AssertionError) as ei:
        mod.require_small_target(134217728)
    msg = str(ei.value)
    assert mod.SMALL_TARGET_ENV in msg
    assert "准备" in msg


def test_label_forbidden_keywords():
    mod = _load_small_target()
    for label in ("Recovery", "SYSTEM", "EFI", "系统恢复"):
        assert mod.label_forbidden(label), f"应判为禁用卷标: {label}"
    assert not mod.label_forbidden("Data")


# ---- real.down 进程安全守阵 (issue 26-11-06-0448) ----
# 关停测试实例只许走 qB 自己的 WebAPI app/shutdown: 外部强杀既触 AGENTS.md 进程红线,
# 又会跳过 fastresume/state 的优雅写回, 与 relocate 下线窗口机制相抵触。
FORCE_KILL_TOKENS = ("Stop-Process", "taskkill", "TerminateProcess", "os.kill", ".kill(", "-Force")


def _blocked_subprocess_run(*args, **kwargs):
    """守阵用例绝不允许真实起外部进程 —— 红验时旧实现会走到 PowerShell 强杀路径。

    只替换 runner 模块自己的 subprocess 引用(不改标准库模块对象), 避免污染同进程其它用例。
    """
    pytest.fail("守阵用例禁止真实起外部进程(会触进程安全红线)")


class _FakeResponse:
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def read(self):
        return b""


def _load_qb():
    p = TESTS_REAL / "lib" / "qb.py"
    spec = importlib.util.spec_from_file_location("_real_qb_under_test", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _load_runner(monkeypatch, ports=(36596, )):
    """隔离加载 tests/real/runner.py: 注入假 lib 包, 全程不触 netstat / qB / 系统进程。

    runner 模块级会 sys.path.insert, 先把 sys.path 换成可恢复的副本; `from lib import ...`
    由 sys.modules 里的假包承接, 不把真实 lib 命名空间带进主套件。
    """
    exe = {p: f"C:/qb-testing/{p}/qbittorrent.exe" for p in ports}
    fake_guard = types.SimpleNamespace(
        WHITELIST_PORTS=tuple(ports),
        EXE=exe,
        REAL_FAKE_TAG="real-fake",
        GuardError=type("GuardError", (RuntimeError, ), {}),
        check_port=lambda port: {
            "port": port,
            "pid": 4242,
            "image": exe[port]
        },
    )
    fake_lib = types.ModuleType("lib")
    fake_lib.guard = fake_guard
    fake_lib.env_registry = types.SimpleNamespace(ENVIRONMENTS={})
    fake_lib.instances = types.SimpleNamespace(make=lambda port: None)
    monkeypatch.setitem(sys.modules, "lib", fake_lib)
    monkeypatch.setattr(sys, "path", list(sys.path))
    spec = importlib.util.spec_from_file_location("_real_runner_under_test", TESTS_REAL / "runner.py")
    mod = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, spec.name, mod)
    spec.loader.exec_module(mod)
    monkeypatch.setattr(mod, "subprocess", types.SimpleNamespace(run=_blocked_subprocess_run))
    return mod, fake_guard


def _down_args(port="36596", dry_run=False):
    return types.SimpleNamespace(port=port, dry_run=dry_run)


def _fake_qb(calls):
    return types.SimpleNamespace(shutdown=lambda: calls.append("shutdown"))


def test_real_down_source_has_no_forced_kill():
    text = (TESTS_REAL / "runner.py").read_text(encoding="utf-8")
    hits = [token for token in FORCE_KILL_TOKENS if token in text]
    assert not hits, f"真机轨 runner.py 出现进程强杀形态 {hits}; 关停实例只走 WebAPI app/shutdown"
    assert ".shutdown()" in text, "cmd_down 必须调用 WebAPI app/shutdown 优雅退出"


def test_cmd_down_dry_run_never_touches_webapi(monkeypatch, capsys):
    calls = []
    mod, fake_guard = _load_runner(monkeypatch)
    monkeypatch.setattr(fake_guard, "check_port", lambda port: pytest.fail("dry-run 不该核验进程"))
    monkeypatch.setattr(mod, "_qb", lambda port: _fake_qb(calls))
    assert mod.cmd_down(_down_args(dry_run=True)) == 0
    assert calls == []
    assert "app/shutdown" in capsys.readouterr().out


def test_cmd_down_uses_webapi_shutdown_and_waits_for_port_release(monkeypatch, capsys):
    calls = []
    mod, _ = _load_runner(monkeypatch)
    monkeypatch.setattr(mod, "_qb", lambda port: _fake_qb(calls))
    monkeypatch.setattr(mod, "_wait_port", lambda port, timeout=40.0: True)
    monkeypatch.setattr(mod, "_wait_port_gone", lambda port, timeout=60.0: True)
    assert mod.cmd_down(_down_args()) == 0
    assert calls == ["shutdown"]
    out = capsys.readouterr().out
    assert "优雅退出" in out and "pid=4242" in out


def test_cmd_down_skips_when_port_not_listening(monkeypatch, capsys):
    calls = []
    mod, fake_guard = _load_runner(monkeypatch)
    monkeypatch.setattr(mod, "_qb", lambda port: _fake_qb(calls))
    monkeypatch.setattr(mod, "_wait_port", lambda port, timeout=40.0: False)
    monkeypatch.setattr(fake_guard, "check_port", lambda port: pytest.fail("端口没起不该核验进程"))
    assert mod.cmd_down(_down_args()) == 0
    assert calls == []
    assert "未在跑" in capsys.readouterr().out


def test_cmd_down_refuses_non_test_instance(monkeypatch, capsys):
    calls = []
    mod, fake_guard = _load_runner(monkeypatch)

    def reject(port):
        raise fake_guard.GuardError(f"端口 {port} 被 {exe} 占用 —— 拒跑(可能是生产 qB)")

    exe = "C:/Program Files/qBittorrent/qbittorrent.exe"
    monkeypatch.setattr(fake_guard, "check_port", reject)
    monkeypatch.setattr(mod, "_qb", lambda port: _fake_qb(calls))
    monkeypatch.setattr(mod, "_wait_port", lambda port, timeout=40.0: True)
    assert mod.cmd_down(_down_args()) == 1
    assert calls == []
    assert "[FAIL]" in capsys.readouterr().out


def test_cmd_down_fails_closed_on_api_error(monkeypatch, capsys):
    def boom():
        raise RuntimeError("port 36596 /app/shutdown -> 401")

    mod, _ = _load_runner(monkeypatch)
    monkeypatch.setattr(mod, "_qb", lambda port: types.SimpleNamespace(shutdown=boom))
    monkeypatch.setattr(mod, "_wait_port", lambda port, timeout=40.0: True)
    assert mod.cmd_down(_down_args()) == 1
    assert "app/shutdown" in capsys.readouterr().out


def test_cmd_down_reports_timeout_without_force_kill(monkeypatch, capsys):
    calls = []
    mod, _ = _load_runner(monkeypatch)
    monkeypatch.setattr(mod, "_qb", lambda port: _fake_qb(calls))
    monkeypatch.setattr(mod, "_wait_port", lambda port, timeout=40.0: True)
    monkeypatch.setattr(mod, "_wait_port_gone", lambda port, timeout=60.0: False)
    assert mod.cmd_down(_down_args()) == 1
    out = capsys.readouterr().out
    assert "超时" in out and "未强杀" in out


def test_qb_shutdown_is_post_with_empty_body(monkeypatch):
    mod = _load_qb()
    seen = {}

    def fake_open(req, timeout=None):
        seen.update(method=req.get_method(), url=req.full_url, data=req.data)
        return _FakeResponse()

    monkeypatch.setattr(mod._OPENER, "open", fake_open)
    mod.Qb(36596).shutdown()
    assert seen["method"] == "POST"
    assert seen["url"].endswith("/api/v2/app/shutdown")
    assert seen["data"] == b""


def test_qb_default_calls_stay_get(monkeypatch):
    mod = _load_qb()
    seen = {}

    def fake_open(req, timeout=None):
        seen.update(method=req.get_method(), url=req.full_url, data=req.data)
        return _FakeResponse()

    monkeypatch.setattr(mod._OPENER, "open", fake_open)
    mod.Qb(36596).version()
    assert seen["method"] == "GET"
    assert seen["url"].endswith("/api/v2/app/version")
    assert seen["data"] is None


# ---- guard 豁免语义与计数口径 (issue 26-11-21-0639) ----
# snapshot 的 skip_tags 定义了「自造种子既不暂停也不计入保护面」的豁免语义, 但三处调用
# (runner guard/pause-all、conftest env)全走缺省空元组 —— 假种子被计入「真实种子 N 个」,
# 环境/计划誊写跟着误标。守阵钉两头: snapshot 语义本身 + 所有调用方必须显式传豁免。


def _load_guard(monkeypatch):
    """隔离加载 tests/real/lib/guard.py: 假 lib 包承接相对导入, 环境注册表给桩值。"""
    fake_env_registry = types.ModuleType("lib.env_registry")
    fake_env_registry.active = lambda: {
        "primary": 36595,
        "secondary": 36596,
        "image_prefix": "C:/qb-testing",
        "exe": {
            36595: "C:/qb-testing/36595/qbittorrent.exe",
            36596: "C:/qb-testing/36596/qbittorrent.exe"
        },
        "bt_listen": {
            36595: 10001,
            36596: 10002
        },
        "machine": "stub",
    }
    fake_lib = types.ModuleType("lib")
    fake_lib.env_registry = fake_env_registry
    monkeypatch.setitem(sys.modules, "lib", fake_lib)
    monkeypatch.setitem(sys.modules, "lib.env_registry", fake_env_registry)
    monkeypatch.setattr(sys, "path", list(sys.path))
    spec = importlib.util.spec_from_file_location("lib.guard", TESTS_REAL / "lib" / "guard.py")
    mod = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, spec.name, mod)
    spec.loader.exec_module(mod)
    return mod


def test_guard_snapshot_skips_tagged_seeds(monkeypatch):
    mod = _load_guard(monkeypatch)
    real_hash, fake_hash = "a" * 40, "b" * 40

    class _FakeQb:
        port = 36595

        def __init__(self):
            self.real_paused = False
            self.pause_calls = []

        def torrents(self):
            out = [
                {
                    "hash": real_hash,
                    "name": "ubuntu-24.04.iso",
                    "tags": "",
                    "state": "pausedUP" if self.real_paused else "uploading"
                },
                {
                    "hash": fake_hash,
                    "name": "fake-256K.bin",
                    "tags": mod.REAL_FAKE_TAG,
                    "state": "stalledUP"
                },
            ]
            return out

        def pause(self, joined):
            self.real_paused = True
            self.pause_calls.append(joined)

    qb = _FakeQb()
    hashes = mod.snapshot(qb, skip_tags=(mod.REAL_FAKE_TAG, ))
    assert set(hashes) == {real_hash}, "带豁免标签的自造种子不计入真实种子保护面"
    assert qb.pause_calls == [real_hash], "被暂停的只有真实种子"
    assert [t["state"] for t in qb.torrents() if t["hash"] == real_hash] == ["pausedUP"]

    qb_bare = _FakeQb()
    hashes_bare = mod.snapshot(qb_bare)
    assert fake_hash in hashes_bare, "缺省裸调不豁免 —— 这正是 0639 误标的来源(守阵钉住契约两端)"


def _snapshot_call_violations(text: str) -> list[str]:
    """找出裸调 snapshot 的行(出现 snapshot 调用但该行没传 skip_tags)。独立成函数便于活性探针红验。"""
    out = []
    for i, line in enumerate(text.splitlines(), 1):
        s = line.strip()
        if s.startswith("#"):
            continue
        if "guard.snapshot(" in s and "skip_tags" not in s:
            out.append(f"{i}: {s}")
    return out


def test_real_guard_snapshot_callers_pass_skip_tags():
    """tests/real 里所有 snapshot 调用必须显式传 skip_tags(issue 26-11-21-0639)。

    活性探针先行: 注入已知违规必须命中、合规样本与注释行必须放行, 防守阵死分支
    (pitfalls/testing/guard-dead-branch.md)。
    """
    assert _snapshot_call_violations("hashes = guard.snapshot(qb)\n") == ["1: hashes = guard.snapshot(qb)"]
    assert _snapshot_call_violations("hashes = guard.snapshot(qb, skip_tags=(guard.REAL_FAKE_TAG, ))\n") == []
    assert _snapshot_call_violations("# 用法见 guard.snapshot(qb) 的 docstring\n") == [], "注释行不算调用"
    hits = []
    for f in sorted(TESTS_REAL.rglob("*.py")):
        rel = f.relative_to(ROOT)
        for v in _snapshot_call_violations(f.read_text(encoding="utf-8", errors="ignore")):
            hits.append(f"{rel}:{v}")
    assert not hits, "tests/real 出现不带 skip_tags 的 snapshot 调用(假种子会被计入真实种子计数):\n" + "\n".join(hits)


def test_cmd_guard_reports_real_and_fake_counts(monkeypatch, capsys):
    mod, fake_guard = _load_runner(monkeypatch)
    seen = {}

    def fake_snapshot(qb, skip_tags=()):
        seen["skip_tags"] = skip_tags
        return {"a" * 40: "ubuntu-24.04.iso"}

    monkeypatch.setattr(fake_guard, "snapshot", fake_snapshot, raising=False)
    monkeypatch.setattr(fake_guard, "fakes", lambda qb: [{"hash": "b" * 40}, {"hash": "c" * 40}], raising=False)
    monkeypatch.setattr(fake_guard, "check_online", lambda qb: "connected", raising=False)
    monkeypatch.setattr(mod, "_qb", lambda port: types.SimpleNamespace(version=lambda: "v5.0.0"))
    assert mod.cmd_guard(_down_args()) == 0
    assert seen["skip_tags"] == (fake_guard.REAL_FAKE_TAG, ), "豁免标签必须传给 snapshot"
    out = capsys.readouterr().out
    assert "真实种子 1 个" in out and "自造(real-fake) 2 个" in out, "计数必须双口径分开报(环境指纹誊写面)"
    assert "v5.0.0" in out and "vv" not in out, "版本串必须原样打印(qb.version() 自带 v 前缀, 不得再拼 v)"


def test_cmd_pause_all_skips_fakes(monkeypatch, capsys):
    mod, fake_guard = _load_runner(monkeypatch)
    seen = {}

    def fake_snapshot(qb, skip_tags=()):
        seen["skip_tags"] = skip_tags
        return {"a" * 40: "ubuntu-24.04.iso"}

    monkeypatch.setattr(fake_guard, "snapshot", fake_snapshot, raising=False)
    monkeypatch.setattr(fake_guard, "fakes", lambda qb: [{"hash": "b" * 40}], raising=False)
    monkeypatch.setattr(mod, "_qb", lambda port: types.SimpleNamespace())
    assert mod.cmd_pause_all(_down_args()) == 0
    assert seen["skip_tags"] == (fake_guard.REAL_FAKE_TAG, ), "豁免标签必须传给 snapshot"
    out = capsys.readouterr().out
    assert "真实种子 1 个" in out and "自造(real-fake) 1 个未动" in out


# ---- real.seed.clean 证据保护闸 (issue 26-11-12-2345) ----
# clean 的旧契约是整目录清空 tests/real/.work —— 2026-11-12 S5 收尾一跑把整树测量证据
# (results/、复用脚本)清掉且 git 不可恢复。守阵钉死: .work 顶层出现 seeds/rmNN 之外的
# 内容即拒跑(rc=1, dry-run 也拒, 删除动作一个都不发生); 只有 --dir 显式指名的子树
# 可以逐处清, 不存在绕过闸门的一键全清。


def _load_seed(monkeypatch, work: Path, ram: Path):
    """隔离加载 tests/real/seed.py: 假 lib 包 + 落点改指 tmp 树。

    真实 tests/real/.work 正是闸门要守的证据面(本 clone 里就躺着 review-findings/
    reconcile-e2e 等), 守阵一律在 tmp 搭景, 不给真实证据面任何被误清的机会。
    """
    fake_guard = types.SimpleNamespace(
        WHITELIST_PORTS=(36595, 36596), REAL_FAKE_TAG="real-fake", check_port=lambda port: {}
    )
    fake_lib = types.ModuleType("lib")
    fake_lib.guard = fake_guard
    fake_lib.instances = types.SimpleNamespace(PRIMARY=36595, SECONDARY=36596)
    fake_lib.torrent = types.SimpleNamespace(PATTERNS=("random", "zeros", "text"), PIECE_LEN=16384)
    monkeypatch.setitem(sys.modules, "lib", fake_lib)
    monkeypatch.setattr(sys, "path", list(sys.path))
    spec = importlib.util.spec_from_file_location("_real_seed_under_test", TESTS_REAL / "seed.py")
    mod = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, spec.name, mod)
    spec.loader.exec_module(mod)
    monkeypatch.setattr(mod, "WORK_ROOT", work)
    monkeypatch.setattr(mod, "WORK", work / "seeds")
    monkeypatch.setattr(mod, "RAM_ROOT", ram)
    monkeypatch.setattr(mod, "ALLOWED_ROOTS", (work, ram))
    return mod


def test_seed_clean_refuses_unknown_work_top_level(tmp_path, monkeypatch, capsys):
    mod = _load_seed(monkeypatch, tmp_path / "work", tmp_path / "ram")
    work = tmp_path / "work"
    (work / "seeds").mkdir(parents=True)
    (work / "seeds" / "fake.bin").write_bytes(b"x")
    (work / "rm03").mkdir()
    (work / "rm03" / "data.bin").write_bytes(b"x")
    (work / "results_3000").mkdir()  # 事故里被整树清掉的证据目录形态
    (work / "review-findings.json").write_text("{}", encoding="utf-8")
    for yes in (False, True):
        assert mod.cmd_clean(types.SimpleNamespace(dir="", yes=yes)) == 1, "顶层有未知内容必须拒跑"
        assert (work / "seeds" / "fake.bin").exists(), "拒跑必须一个文件都不删(含认得的落点)"
        assert (work / "results_3000").exists() and (work / "rm03" / "data.bin").exists()
    out = capsys.readouterr().out
    assert "results_3000" in out and "review-findings.json" in out, "拒跑信息要逐项列出未知内容"
    assert "26-11-12-2345" in out, "守卫信息要带 issue 指称, 便于回溯事故档案"


def test_seed_clean_refuses_rmnn_case_dirs_with_files(tmp_path, monkeypatch, capsys):
    """rmNN 内层有文件即整单拒跑(issue 26-11-21-0638): 顶层白名单放行 rmNN 后整树 rglob 全删,
    RM11 实证把 rm04/async/ 取证连锅端 —— rmNN 是用例工作区与取证的混合沉积层, 整扫不许碰。"""
    mod = _load_seed(monkeypatch, tmp_path / "work", tmp_path / "ram")
    work, ram = tmp_path / "work", tmp_path / "ram"
    (work / "seeds").mkdir(parents=True)
    (work / "seeds" / "fake.bin").write_bytes(b"x")
    (work / "rm04").mkdir()
    (work / "rm04" / "rm04_10_evidence.json").write_text("{}", encoding="utf-8")
    (work / "rm04" / "async").mkdir()
    (work / "rm04" / "async" / "probe.json").write_text("{}", encoding="utf-8")
    ram.mkdir()
    (ram / "big.bin").write_bytes(b"x")
    for yes in (False, True):
        assert mod.cmd_clean(types.SimpleNamespace(dir="", yes=yes)) == 1, "rmNN 内层有文件必须整单拒跑"
        assert (work / "seeds" / "fake.bin").exists(), "拒跑连认得的 seeds/ 都一个文件不删"
        assert (work / "rm04" / "async" / "probe.json").exists() and (ram / "big.bin").exists()
    out = capsys.readouterr().out
    assert "rm04" in out and "2 个文件" in out, "拒跑信息要带各 rmNN 的内层文件数(免费盘点)"
    assert ("async/probe.json" in out) or ("async\\probe.json" in out), "内层清单要落到具体文件"
    assert "26-11-21-0638" in out, "守卫信息要带 issue 指称, 便于回溯事故档案"
    assert mod.cmd_clean(types.SimpleNamespace(dir=str(work / "rm04"), yes=True)) == 0, "--dir 指名 rmNN 是显式豁免口"
    assert not (work / "rm04" / "async" / "probe.json").exists(), "指名清 rm04 照常执行"
    assert (work / "seeds" / "fake.bin").exists(), "指名清 rm04 不波及 seeds"


def test_seed_clean_sweeps_seeds_and_ram_when_no_case_files(tmp_path, monkeypatch, capsys):
    """rmNN 零文件空壳(含空子目录)照旧整扫收掉, seeds/ 与 R: 内存盘根的清扫契约不变
    (26-11-12-2345 原契约; 26-11-21-0638 收紧只针对有文件的 rmNN)。"""
    mod = _load_seed(monkeypatch, tmp_path / "work", tmp_path / "ram")
    work, ram = tmp_path / "work", tmp_path / "ram"
    (work / "seeds" / "fake-256k").mkdir(parents=True)
    (work / "seeds" / "fake-256k" / "fake.bin").write_bytes(b"x")
    (work / "seeds" / "fake.torrent").write_bytes(b"x")
    (work / "rm04").mkdir()
    (work / "rm04" / "async").mkdir()  # 零文件空壳: 没有文件就没有可丢的证据
    (ram / "big").mkdir(parents=True)
    (ram / "big" / "big.bin").write_bytes(b"x")
    assert mod.cmd_clean(types.SimpleNamespace(dir="", yes=False)) == 0
    assert (work / "seeds" / "fake-256k" / "fake.bin").exists() and (ram / "big" / "big.bin").exists(), "dry-run 零删除"
    assert mod.cmd_clean(types.SimpleNamespace(dir="", yes=True)) == 0
    assert not (work / "seeds" / "fake-256k").exists(), "seeds 照旧清(含空目录壳子)"
    assert not (work / "rm04").exists(), "零文件空壳整扫顺带收掉"
    assert not (ram / "big").exists(), "R: 内存盘根照旧整清"


def test_seed_clean_explicit_dir_named_subtree_bypasses_guard(tmp_path, monkeypatch, capsys):
    mod = _load_seed(monkeypatch, tmp_path / "work", tmp_path / "ram")
    work = tmp_path / "work"
    (work / "seeds").mkdir(parents=True)
    (work / "seeds" / "fake.bin").write_bytes(b"x")
    (work / "probe-accept").mkdir()
    (work / "probe-accept" / "evidence.json").write_text("{}", encoding="utf-8")
    assert mod.cmd_clean(types.SimpleNamespace(dir=str(work / "seeds"), yes=True)) == 0
    assert not (work / "seeds" / "fake.bin").exists(), "--dir 指名子树照常清"
    assert (work / "probe-accept" / "evidence.json").exists(), "指名清 seeds 不该波及证据目录"
    assert mod.cmd_clean(types.SimpleNamespace(dir=str(work), yes=True)) == 1, "--dir 指 .work 本体与默认同闸"
    assert (work / "probe-accept" / "evidence.json").exists()


def test_seed_allowed_rejects_prefix_sibling_dir(tmp_path, monkeypatch):
    """白名单按路径分量判严格包含: .work 的同前缀兄弟目录(.work-20261112 之类)不算落点。

    裸字符串前缀匹配会把兄弟目录误收 —— --dir 指过去即整树清且绕过证据闸(评审轮1发现)。
    """
    mod = _load_seed(monkeypatch, tmp_path / "work", tmp_path / "ram")
    sibling = tmp_path / "work-backup"
    sibling.mkdir()
    (sibling / "evidence.json").write_text("{}", encoding="utf-8")
    with pytest.raises(SystemExit, match="不在允许的落点"):
        mod._allowed(sibling)
    with pytest.raises(SystemExit, match="不在允许的落点"):
        mod.cmd_clean(types.SimpleNamespace(dir=str(sibling), yes=True))
    assert (sibling / "evidence.json").exists(), "兄弟目录里的东西一个都不许动"
    assert mod._allowed(tmp_path / "work" / "seeds" / "x.bin") == (tmp_path / "work" / "seeds" / "x.bin").resolve()
