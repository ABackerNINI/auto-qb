"""test_legacy_review4_scripts: R4 存量评审 scripts 主题各修复批次的守卫用例(共用落点)。

P3 批(表#4): scripts/check_context_caps.py 的 porcelain 改动集解析 --
`git status --porcelain` 的 rename 行(`R  old -> new`)必须按状态位分流、以 " -> " 拆开,
新旧两侧路径都进改动集: 旧实现整行 line[3:] 塞进集合, 两个真实路径都不在,
`git mv AGENTS.md docs/AGENTS.md` 这类操作会让硬规定的「改动命中」判定(rel in changed)
静默漏检(与 git() 里「整段 strip 吃掉首行行首空格」的自述漏检同类)。普通行(M/A/D/??)不回归。

P4 批(表#6/#23/#11): scripts 三桩的参数解析/索引守卫/零请求口径 --
e2e_selfcheck 的 --blocking/--warn 缺值走 usage 提示退 2(不再 IndexError 抛裸堆栈),
解析提为模块级 parse_port_args(生产 main 真实调用); ui_harness 的 _inject_site_alerts
索引面是 torrents[-4]/[-3], 守卫从 <2 收紧到 <4(--torrents 2/3 不再崩桩);
qb_capture 的 --dry 真零请求: 判定从 run_capture 内部(handshake 之后)提前到 main() 里
Capture 构造之前(QbClient 构造即 POST /auth/login x4), 本地计数假服断言 dry 全程 0 请求。

本文件是 legacy-review4 scripts 各批次共用的测试落点, 后续批次往里追加用例,
头部 docstring 的「## 测试计划」清单随用例同步登记。用例纯内存构造, 不真跑 git
写操作、不连 qB、不写仓库外文件(P4 表#11 的本地计数假服听 127.0.0.1 随机口, 不是 qB)。

## 测试计划(每个测试函数一条, 后续批次往里追加)
- test_porcelain_rename_paths_both_sides_in_changed_set: `R  old -> new` 按两侧拆开入集; `RM`(暂存改名+工作区又改)同款; 集合里不得残留整串形态
- test_porcelain_scored_rename_still_parsed: 带评分形态 `R90 old -> new`(常规 porcelain v1 不出评分, 防御性兼容)同样两侧入集
- test_porcelain_plain_rows_unchanged: M / MM / A / D / ?? / !! 行为不回归; 首行行首空格不被吃(整段 strip 漏检 "GENTS.md" 的旧坑钉住)
- test_porcelain_modified_path_with_arrow_not_split: 非 rename 行(状态位无 R/C)路径里含 " -> " 不被误拆 -- 分流必须看状态位, 不能只看 " -> "
- test_porcelain_blank_and_short_lines_ignored: 空文本 / 空行 / 纯空白行返回空集, 不产伪路径
- test_porcelain_paths_red_on_whole_string_regression: **红验** -- 旧实现(整串塞入)下 rename 两侧路径都不在集合里, 证明绿判据能区分新旧实现, 不是恒绿
- test_e2e_selfcheck_missing_option_value_prints_usage_rc2 (P4 表#6): --blocking/--warn 写在最后一个参数 -> 打印含用法提示的错误行并退 2, 不抛 IndexError; 红验: 旧解析循环逐字重放, 缺值必 IndexError
- test_e2e_selfcheck_parse_port_args_normal_values (P4 表#6): 正常取值/缺省/多值串解析不回归, 未知参数仍走报错行; parse_port_args 为生产 main 真实调用点
- test_ui_harness_site_alerts_needs_four_torrents (P4 表#23): 2/3 条种子整段跳过注入不崩, 4 条放行且倒数第 4/第 3 注入生效; 红验: 旧守卫(len<2)逐字重放, 2 条时 torrents[-4] 必 IndexError
- test_qb_capture_dry_true_zero_requests (P4 表#11): --dry 打本地计数假服请求计数为 0(不 login/不握手/不计数; 缺 --sample 不预查计数), 带 --sample 计划行给出 Nx2; 对照组真构造 Capture 计到 4 个 login, 证明计数器非空转、旧顺序(main 先构造后判 dry)回潮即红
"""

from __future__ import annotations

import http.server
import importlib.util
import logging
import sys
import threading
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
_SPEC = importlib.util.spec_from_file_location("check_context_caps", ROOT / "scripts" / "check_context_caps.py")
mod = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(mod)


def _load_script(name: str):
    """scripts/ 不是包, 按路径加载(与 test_qb_capture.py 同款做法); 经 sys.modules 去重,
    同一 pytest 进程里其它测试文件先加载过的模块直接复用, 不重复执行模块体。"""
    cached = sys.modules.get(name)
    if cached is not None:
        return cached
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    m = importlib.util.module_from_spec(spec)
    sys.modules[name] = m
    spec.loader.exec_module(m)
    return m


def test_porcelain_rename_paths_both_sides_in_changed_set():
    """rename 行(`R  old -> new`)拆开、两侧路径都入改动集; `RM`(暂存改名+工作区又改)同款。"""
    text = (
        "R  AGENTS.md -> docs/AGENTS.md\n"
        "RM README.md -> memory-bank/README.md\n"
        " M scripts/check_context_caps.py\n"
    )
    paths = mod.porcelain_paths(text)
    assert "AGENTS.md" in paths, f"rename 旧路径必须在改动集: {sorted(paths)}"
    assert "docs/AGENTS.md" in paths, f"rename 新路径必须在改动集: {sorted(paths)}"
    assert "README.md" in paths and "memory-bank/README.md" in paths, f"RM 行同样两侧入集: {sorted(paths)}"
    assert "scripts/check_context_caps.py" in paths, "普通 M 行不受影响"
    assert not any(" -> " in p for p in paths), f"改动集里不得残留整串 rename 行: {sorted(paths)}"


def test_porcelain_scored_rename_still_parsed():
    """带评分形态 `R90 old -> new`(常规 porcelain v1 不出评分, 防御性兼容)同样两侧入集。"""
    for line in ("R90 AGENTS.md -> docs/AGENTS.md\n", "R100 AGENTS.md -> docs/AGENTS.md\n"):
        paths = mod.porcelain_paths(line)
        assert paths == {"AGENTS.md", "docs/AGENTS.md"}, f"{line!r} 两侧路径都必须入集: {sorted(paths)}"


def test_porcelain_plain_rows_unchanged():
    """普通 M / MM / A / D / ?? / !! 行为不回归; 首行行首空格不被吃(整段 strip 的旧漏检钉住)。"""
    text = (
        " M AGENTS.md\n"
        "M  src/auto_qb/cli.py\n"
        "MM src/auto_qb/config.py\n"
        "A  docs/new.md\n"
        "D  docs/old.md\n"
        "?? scripts/scratch.py\n"
        "!! ignored.log\n"
    )
    assert mod.porcelain_paths(text) == {
        "AGENTS.md",  # 行首空格必须保住路径起点: 整段 strip 的错位解析会得到 "GENTS.md"
        "src/auto_qb/cli.py",
        "src/auto_qb/config.py",
        "docs/new.md",
        "docs/old.md",
        "scripts/scratch.py",
        "ignored.log",
    }


def test_porcelain_modified_path_with_arrow_not_split():
    """非 rename 行(状态位无 R/C)即使路径里含 " -> " 也整串保留 -- 分流按状态位, 不按 " -> "。"""
    text = " M a -> b.md\n?? weird -> name.md\nA  x -> y.md\n"
    assert mod.porcelain_paths(text) == {"a -> b.md", "weird -> name.md", "x -> y.md"}


def test_porcelain_blank_and_short_lines_ignored():
    """空文本 / 空行 / 纯空白行返回空集, 不产伪路径。"""
    assert mod.porcelain_paths("") == set()
    assert mod.porcelain_paths("\n\n") == set()
    assert mod.porcelain_paths("   \n\t\n") == set()


def test_porcelain_paths_red_on_whole_string_regression():
    """**红验**: 旧实现(整行 line[3:] 整串塞入)下 rename 两侧路径都不在集合里。

    把旧实现逐字内联重放, 断言它确实骗过「两侧路径入集」这一判据 -- 证明上面的
    rename 用例不是恒绿: 生产实现一旦回潮成整串塞入, 本文件的 rename 用例立刻全红。
    """
    text = "R  AGENTS.md -> docs/AGENTS.md\n"
    old_impl = {line[3:].strip() for line in text.splitlines() if line.strip()}  # 旧实现逐字重放
    new_impl = mod.porcelain_paths(text)
    # 新实现: 两侧都入集
    assert "AGENTS.md" in new_impl and "docs/AGENTS.md" in new_impl
    # 旧实现: 两侧都不在, 只塞进整串 -- 这就是回潮时的红面
    assert old_impl == {"AGENTS.md -> docs/AGENTS.md"}
    assert "AGENTS.md" not in old_impl and "docs/AGENTS.md" not in old_impl


# --------------------------------------------------------------------------- P4 表#6: e2e_selfcheck 参数解析
def test_e2e_selfcheck_missing_option_value_prints_usage_rc2(monkeypatch, capsys):
    """P4 表#6: --blocking / --warn 写在最后一个参数(缺值) -> 打印含用法提示的错误行并退 2。

    旧解析循环(逐字重放见下)不判 i+1 越界, 缺值时 args[i+1] 直接 IndexError 抛裸堆栈 --
    用户看到 traceback 而不是 usage。E2E_PORT 先摘掉: main() 的环境闸门在解析之前,
    带着它会在解析前就退 1, 钉不到解析分支。
    """
    mod_e2e = _load_script("e2e_selfcheck")
    monkeypatch.delenv("E2E_PORT", raising=False)
    for argv in (["--blocking"], ["--warn"]):
        rc = mod_e2e.main(argv)
        assert rc == 2, f"{argv} 缺值必须退 2: got {rc}"
        out = capsys.readouterr().out
        assert "缺少值" in out and "--blocking <ports>" in out, f"必须走 usage 提示而非裸堆栈: {out!r}"

    # 红验: 旧解析循环逐字重放 -- 缺值必 IndexError(证明绿判据能区分新旧实现, 不是恒绿)
    def _old_parse_loop(args):
        blocking_raw = ""
        warn_raw = "8099"
        i = 0
        while i < len(args):
            if args[i] == "--blocking":
                blocking_raw = args[i + 1]  # 旧形态: 不判越界直接取值
                i += 2
            elif args[i] == "--warn":
                warn_raw = args[i + 1]
                i += 2
            else:
                return "unknown"
        return (blocking_raw, warn_raw)

    with pytest.raises(IndexError):
        _old_parse_loop(["--blocking"])
    with pytest.raises(IndexError):
        _old_parse_loop(["--warn"])


def test_e2e_selfcheck_parse_port_args_normal_values():
    """P4 表#6 正常面: parse_port_args(生产 main 真实调用点)取值/缺省/多值串不回归, 未知参数仍走报错行。"""
    mod_e2e = _load_script("e2e_selfcheck")
    assert mod_e2e.parse_port_args([]) == ("", mod_e2e.DEFAULT_WARN_PORTS, None), "无参数 -> 缺省(拦截面空, warn=8099)"
    assert mod_e2e.parse_port_args(["--blocking", "8099", "--warn", ""]) == ("8099", "", None)
    assert mod_e2e.parse_port_args(["--warn", "8099,8080"]) == ("", "8099,8080", None), "多值逗号串原样透传"
    blocking, warn, err = mod_e2e.parse_port_args(["--blocking", "70000", "--warn", "70001"])
    assert err is None and blocking == "70000" and warn == "70001"
    _, _, err = mod_e2e.parse_port_args(["--nope"])
    assert err is not None and "未知参数" in err, "未知参数仍走报错行(行为与旧实现一致)"


# --------------------------------------------------------------------------- P4 表#23: ui_harness 站点告警注入守卫
def test_ui_harness_site_alerts_needs_four_torrents():
    """P4 表#23: _inject_site_alerts 的索引面是 torrents[-4]/[-3], 守卫必须 <4。

    旧守卫(len<2)放行 2/3 条后 torrents[-4] 必 IndexError 崩桩(--torrents 2/3 + 默认
    --site-alert on 必触发, 崩在启动行打印前)。新守卫: 2/3 条整段跳过(降级为无站点健康
    两态, 不崩); 4 条放行且注入生效。红验: 旧守卫逐字重放, 2 条时必 IndexError。
    """
    mod_harness = _load_script("ui_harness")

    def _tor(i):
        return SimpleNamespace(
            hash=f"{i:040x}",
            tracker_conf=object(),
            tracker=f"https://tracker.example.net/announce/{i}",
            tracker_health_msg="",
            tracker_health_ts=0.0,
        )

    # 红验: 旧守卫(len<2)逐字重放 -- 2 条放行后在 torrents[-4] 崩
    def _old_inject_site_alerts(torrents):
        if len(torrents) < 2:
            return
        a, b = torrents[-4], torrents[-3]  # 旧形态: -4 索引无守卫
        return a, b

    with pytest.raises(IndexError):
        _old_inject_site_alerts([_tor(0), _tor(1)])

    # 新守卫: 2 / 3 条 -> 整段跳过, 不崩不改
    for n in (2, 3):
        ts = [_tor(i) for i in range(n)]
        mod_harness._inject_site_alerts(ts)
        assert ts[0].tracker_conf is not None, f"{n} 条必须整段跳过注入"
        assert ts[0].tracker_health_msg == "" and ts[-1].tracker_health_msg == ""

    # 4 条 -> 放行: 倒数第 4 / 第 3 两行被注入两态, 其余行不动
    ts4 = [_tor(i) for i in range(4)]
    mod_harness._inject_site_alerts(ts4)
    assert ts4[0].tracker_conf is None, "torrents[-4] 注入 no_site_conf 形态(tracker_conf=None)"
    assert "unknown-site" in ts4[0].tracker
    assert ts4[1].tracker_health_msg, "torrents[-3] 注入 tracker 报错文案"
    assert ts4[1].tracker_health_ts > 0
    assert ts4[2].tracker_health_msg == "" and ts4[3].tracker_health_msg == "", "只注入倒数第 4/第 3 两行"
    assert ts4[2].tracker_conf is not None and ts4[3].tracker_conf is not None


# --------------------------------------------------------------------------- P4 表#11: qb_capture --dry 真零请求
def test_qb_capture_dry_true_zero_requests(tmp_path, caplog):
    """P4 表#11: --dry 真零请求 -- 打本地计数假服, 全程 0 请求(不 login / 不握手 / 不计数)。

    旧实现 main() 先构造 Capture(4 个 QbClient, 构造即 POST /auth/login), run_capture 里
    再 handshake(version/webapiVersion/preferences/maindata 4 个)后才判 dry, 缺 --sample
    还要 _count_torrents 再发 1 个 -- 与 help「不发请求」矛盾。现在 dry 在 main() 里、
    Capture 构造之前分流(_dry_plan), 缺 --sample 不预查计数(计数本身要发请求)。
    对照组: 同一假服上真构造 Capture, 计到 4 个 login -- 证明计数器非空转, 也证明旧顺序
    (main 先构造后判 dry)必然带请求, 回潮即红。
    """
    mod_cap = _load_script("qb_capture")
    hits: list[str] = []

    class _CountingHandler(http.server.BaseHTTPRequestHandler):
        def _respond(self):
            hits.append(f"{self.command} {self.path}")
            body = b"Ok." if self.path.endswith("/auth/login") else b"{}"
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        do_GET = _respond
        do_POST = _respond

        def log_message(self, fmt, *args):  # noqa: A003 - 基类签名; 静默
            pass

    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _CountingHandler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        base = [
            "capture",
            "--out",
            str(tmp_path / "corpus"),
            "--host",
            "127.0.0.1",
            "--port",
            str(srv.server_port),
            "--user",
            "u",
            "--pass",
            "p",
        ]
        # 绿面: dry 全程零请求; 缺 --sample 时不预查计数(计划行以"全库"占位)
        caplog.clear()
        with caplog.at_level(logging.INFO, logger="qb_capture"):
            rc = mod_cap.main(base + ["--dry"])
        assert rc == 0, "--dry 必须正常退出 0"
        assert hits == [], f"--dry 必须零请求(不 login/不握手/不计数), 实发: {hits}"
        dry_lines = [r.getMessage() for r in caplog.records if "[DRY]" in r.getMessage()]
        assert dry_lines and "0 个" in dry_lines[0], f"dry 输出必须自明零请求: {dry_lines}"
        assert "全库种子数" in dry_lines[0], "缺 --sample 时不得预查计数(计数本身要发请求)"

        # 带 --sample: 计划行给出 Nx2, 依旧零请求
        caplog.clear()
        with caplog.at_level(logging.INFO, logger="qb_capture"):
            rc = mod_cap.main(base + ["--dry", "--sample", "7"])
        assert rc == 0 and hits == [], "带 --sample 的 dry 同样必须零请求"
        dry2 = [r.getMessage() for r in caplog.records if "[DRY]" in r.getMessage()]
        assert dry2 and "7x2(files+trackers)" in dry2[0]

        # 对照组(机制自证/红验): 真构造 Capture -- 构造即 4 个 QbClient 各 login 一次。
        # 旧顺序(main 先构造后判 dry)在此必然留下请求, 回潮即红。
        args = mod_cap.build_parser().parse_args(base)
        mod_cap.Capture(args)
        logins = [h for h in hits if "/auth/login" in h]
        assert len(logins) == 4, f"Capture 构造 = 4 个 QbClient 各 login 一次, 实计: {hits}"
    finally:
        srv.shutdown()
        srv.server_close()
