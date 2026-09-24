"""test_commands_engine 测试计划: commands 引擎(`.agents/skills/commands/scripts/`)的输出预算与 id 解析

引擎不在 `src/` 下(pytest.ini 的 pythonpath 只含 src), 用路径显式装载。

## 测试计划(每个测试函数一条)
- test_digest_keeps_anomaly_lines: 摘要必须留住**中段**的异常行 —— 只取末 N 行会让"2 项 WARN"的**内容**消失(实测: 预检因此被跑了两遍)
- test_digest_keeps_preflight_warn_rows: 回归守阵 —— 预检形态的输出(结论行在最后、WARN 行在中段)摘要里必须同时有两者
- test_digest_short_output_untouched: 输出本身就短 → 原样返回, 不报"略过"
- test_digest_caps_anomaly_lines: 异常行也要封顶(病态输出不能把上下文灌满)
- test_digest_ignores_lowercase_noise: 小写 warnings/error 是正常输出的一部分, 不算异常行
- test_emit_prints_truncation_note: 有省略时必须打印一行"略过 N 行 + 怎么看全文", 不能静默截断
- test_pick_accepts_pack_qualified_id: 包路径限定写法(`包/子包.<task>`)与短 id 等价 —— 只认一种会在"看起来对"的另一种上 STOP
- test_pick_unknown_id_stops_with_howto: 未知 id → STOP 且提示里给出可解析的写法(不是只说"没有这个 task")
- test_wrapper_bodies_are_platform_specific: POSIX 只给 `commands`, Windows 多一份 `commands.cmd`(cmd/PowerShell 按 PATHEXT 解析)
- test_wrapper_bodies_carry_ownership_marker: 两份内容都带归属标记 —— 没标记就不敢覆盖同名文件
- test_wrapper_cmd_body_is_batch_safe: `.cmd` 只留 ASCII、rem 行不含引号/括号/反引号(实测这三样会让批处理静默退出 2)
- test_wrapper_cmd_written_with_crlf_no_bom: `.cmd` 必须 CRLF 且无 BOM(LF 会被 cmd 拆错行)
- test_wrapper_write_is_idempotent: 重复安装 → "已是最新", 内容不变
- test_wrapper_write_refuses_foreign_file: 同名文件没有标记 → 停手不改; `--force` 才覆盖
- test_wrapper_repo_root_walk: 从深层子目录向上找到含 `.commands/` 的仓库根
- test_wrapper_path_dir_picks_dir_on_path: 只在**已在 PATH 上**的目录里装"项目无关"那份; 在 PATH 上但不存在则建出来
- test_wrapper_end_to_end_passes_args: 真跑一次生成的 wrapper —— 找到假引擎并把参数原样转过去(端到端)
- test_decode_falls_back_to_local_codepage: 子进程按本地码页(GBK)输出中文时必须解出人话 —— 按 UTF-8 硬解会让"已生成 16 个索引"变一串 U+FFFD(2026-09-24 实测)
- test_decode_prefers_utf8: UTF-8 是首选(子进程已被强制), 不能被本地码页抢解
- test_decode_never_raises_on_garbage: 任意字节(含 None)都不抛 —— 解码失败不该让整条命令看起来失败
- test_shell_child_env_forces_utf8_stdio: 子进程环境必须带 PYTHONIOENCODING=utf-8 —— 否则 Windows 上 Python 子进程被管道接住时按 cp936 输出
- test_shell_injects_env_and_captures_bytes: `_shell` 真把 _CHILD_ENV 合并进子进程环境(pack env 仍可覆盖), 且按字节收输出(不再 text 模式硬解)
- test_shell_decodes_gbk_child_output: 子进程交回 GBK 字节(kb.index 实测形态)时, `_shell` 返回的文本必须可读
- test_shell_failure_keeps_rc: 非 0 退出码照旧传出去(解码改动不能吞掉失败)
"""
from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
from pathlib import Path

import pytest

ENGINE_DIR = Path(__file__).resolve().parents[1] / ".agents" / "skills" / "commands" / "scripts"


def _engine():
    """装载引擎入口(带缓存: 模块级 import 会往 sys.path 插它自己的目录, 只需一次)。"""
    if "cmd_engine" not in sys.modules:
        spec = importlib.util.spec_from_file_location("cmd_engine", ENGINE_DIR / "run.py")
        assert spec and spec.loader
        mod = importlib.util.module_from_spec(spec)
        sys.modules["cmd_engine"] = mod
        spec.loader.exec_module(mod)
    return sys.modules["cmd_engine"]


def _preflight_like_output() -> str:
    """预检形态: 12 行检查表(WARN 在中段) + 决策点指针 + 结论行。"""
    return "\n".join(
        [
            "预检结果(PASS / WARN / STOP):",
            "",
            "  [PASS] 外置配置  .commands/my-commit-flow/.my-commit-flow.toml",
            "  [PASS] 分支    当前 develop(探测/配置为 develop)",
            "  [WARN] 上游    origin/develop(期望 gitee/develop)",
            "  [PASS] 落后主线  与主线齐平(本地领先 0)",
            "  [WARN] 工作区   未暂存 6 个 / 已暂存 0 个",
            "  [PASS] 自动闸门  9 条全过 (共 21.6s)",
            "",
            "决策点指针(改代码 / 跑 git 前先读): memory-bank/pitfalls/git/_index.md",
            "",
            "无 STOP；2 项 WARN 需人工确认 —— 可以继续。",
        ]
    )


def test_digest_keeps_anomaly_lines():
    """摘要留住中段异常行: 只取末 3 行时, "2 项 WARN"的**内容**会被截掉(实测代价 = 重跑一次预检)"""
    lines, skipped = _engine()._digest(_preflight_like_output())
    text = "\n".join(lines)

    assert "[WARN] 上游" in text, "中段的 WARN 行必须留下(否则调用方只能重跑一遍)"
    assert "[WARN] 工作区" in text
    assert "可以继续" in text, "结论行照旧保留"
    assert skipped > 0, "确实略过了若干行"


def test_digest_keeps_preflight_warn_rows():
    """回归守阵: 结论行 + 中段 WARN 行同时要在 —— 缺任一半都会让人再跑一次"""
    picked, _ = _engine()._digest(_preflight_like_output())
    assert any("[WARN]" in ln for ln in picked) and any("无 STOP" in ln for ln in picked)


def test_digest_short_output_untouched():
    """短输出原样返回(不截断、不报略过)"""
    picked, skipped = _engine()._digest("第一行\n第二行")
    assert picked == ["第一行", "第二行"] and skipped == 0


def test_digest_caps_anomaly_lines():
    """异常行封顶: 病态输出(满屏 FAILED)不能把上下文灌满"""
    mod = _engine()
    out = "\n".join(f"FAILED test_{i}" for i in range(50))
    picked, skipped = mod._digest(out)
    assert len(picked) <= mod.SUMMARY_LINES + mod.ANOMALY_MAX
    assert skipped == len(out.splitlines()) - len(picked)


def test_digest_ignores_lowercase_noise():
    """小写 warnings / error 是正常输出的一部分(pytest 收尾行), 不该被当成异常行抽出来"""
    mod = _engine()
    out = "\n".join(["line 0", "6 warnings in 1.0s"] + [f"line {i}" for i in range(2, 12)])
    picked, _ = mod._digest(out)
    assert "6 warnings in 1.0s" not in picked, "小写 warnings 不是异常行"
    assert picked == ["line 9", "line 10", "line 11"], "只保留末 3 行"


def test_emit_prints_truncation_note(capsys):
    """截断必须可见: 打印"略过 N 行 + 怎么看全文", 不静默丢"""
    _engine()._emit("\n".join(f"line {i}" for i in range(20)), "test.quick")
    out = capsys.readouterr().out
    assert "略过 17 行" in out and "show test.quick" in out


def test_pick_accepts_pack_qualified_id():
    """包路径限定写法与短 id 等价 —— 文档/人习惯写全路径, list 里显示的是短 id"""
    mod = _engine()
    tree = mod.C.load_tree()
    assert mod._pick(tree, "my-commit-flow/ship.commit").id == "ship.commit"
    assert mod._pick(tree, "ship.commit").id == "ship.commit"
    assert mod._pick(tree, "my-commit-flow.preflight").id == "my-commit-flow.preflight"


def test_pick_unknown_id_stops_with_howto():
    """未知 id: STOP 且提示给出可解析的写法(否则调用方只能靠 list 逐级试)"""
    mod = _engine()
    tree = mod.C.load_tree()
    with pytest.raises(SystemExit) as exc:
        mod._pick(tree, "my-commit-flow/ship.pus")
    msg = str(exc.value)
    assert "没有这个 task" in msg and "ship.push" in msg and "包/子包.<task>" in msg


# ---------------------------------------------------------------- wrapper


def _wrapper():
    """装载 wrapper 生成器(与引擎同目录, 同样按路径装载)。"""
    if "cmd_wrapper" not in sys.modules:
        spec = importlib.util.spec_from_file_location("cmd_wrapper", ENGINE_DIR / "install_wrapper.py")
        assert spec and spec.loader
        mod = importlib.util.module_from_spec(spec)
        sys.modules["cmd_wrapper"] = mod
        spec.loader.exec_module(mod)
    return sys.modules["cmd_wrapper"]


def test_wrapper_bodies_are_platform_specific():
    """Windows 两种都给(`commands` 给 Git Bash, `commands.cmd` 给 cmd/PowerShell); POSIX 只要 `commands`"""
    assert set(_wrapper().bodies("posix")) == {"commands"}
    assert set(_wrapper().bodies("nt")) == {"commands", "commands.cmd"}


def test_wrapper_bodies_carry_ownership_marker():
    """两份内容都带归属标记 —— 没有它就不敢覆盖目标位置的同名文件"""
    for text in _wrapper().bodies("nt").values():
        assert _wrapper().MARK in text


def test_wrapper_cmd_body_is_batch_safe():
    """`.cmd`: 全 ASCII; rem 行不含引号/括号/反引号 —— 带这些字符的版本实测静默退出 2 且无输出"""
    body = _wrapper().bodies("nt")["commands.cmd"]
    assert all(ord(ch) < 128 for ch in body), "cmd 按 OEM 码页读批处理, 非 ASCII 会变 mojibake"
    for line in body.splitlines():
        if line.strip().lower().startswith("rem"):
            assert not set(line) & {'"', "`", "(", ")"}, f"rem 行含批处理敏感字符: {line}"
    assert "exit /b 2" in body, "找不到仓库根/引擎时必须有非 0 退出码"


def test_wrapper_cmd_written_with_crlf_no_bom(tmp_path):
    """`.cmd` 必须 CRLF 且无 BOM —— LF 会被 cmd 拆错行(报 'exist 不是内部或外部命令')"""
    mod = _wrapper()
    target = tmp_path / "commands.cmd"
    mod.write_one(target, mod.bodies("nt")["commands.cmd"], dry_run=False, force=False)
    raw = target.read_bytes()
    assert b"\r\n" in raw and raw.count(b"\n") == raw.count(b"\r\n"), "必须整篇 CRLF"
    assert raw[:3] != b"\xef\xbb\xbf", "带 BOM 的批处理会被 cmd 拒"


def test_wrapper_write_is_idempotent(tmp_path):
    """重复安装: 第二次报"已是最新", 不重写、不报错"""
    mod = _wrapper()
    target = tmp_path / "commands"
    text = mod.bodies("posix")["commands"]
    assert "已写入" in mod.write_one(target, text, dry_run=False, force=False)
    assert "已是最新" in mod.write_one(target, text, dry_run=False, force=False)
    assert target.read_text(encoding="utf-8") == text


def test_wrapper_write_refuses_foreign_file(tmp_path):
    """目标已存在且不是本脚本生成的 → 停手(不覆盖别人的同名文件); --force 才动"""
    mod = _wrapper()
    target = tmp_path / "commands"
    target.write_text("#!/bin/sh\necho 别人的脚本\n", encoding="utf-8")
    result = mod.write_one(target, mod.bodies("posix")["commands"], dry_run=False, force=False)
    assert "[STOP]" in result and "别人的脚本" in target.read_text(encoding="utf-8")
    assert "已写入" in mod.write_one(target, mod.bodies("posix")["commands"], dry_run=False, force=True)
    assert mod.MARK in target.read_text(encoding="utf-8")


# ---------------------------------------------------------------- 子进程编码


def test_decode_falls_back_to_local_codepage():
    """回归守阵(2026-09-24 实测): 子进程按本地码页(GBK)输出中文时, 必须解出人话而非 U+FFFD"""
    mod = _engine()
    raw = "已生成 16 个索引".encode("gbk")
    assert mod._decode(raw) == "已生成 16 个索引"
    assert "\ufffd" not in mod._decode(raw)


def test_decode_prefers_utf8():
    """UTF-8 是首选: 子进程已被强制 UTF-8, 不能被本地码页抢解成乱码"""
    mod = _engine()
    text = "更新 memory-bank/tasks/_index.md"
    assert mod._decode(text.encode("utf-8")) == text


def test_decode_never_raises_on_garbage():
    """任意字节(含 None)都不抛 —— 解码失败不该让整条命令看起来失败了"""
    mod = _engine()
    assert mod._decode(None) == ""
    assert mod._decode(b"\xff\xfe\x00\x81") != ""


def test_shell_child_env_forces_utf8_stdio():
    """子进程环境必须带 PYTHONIOENCODING=utf-8 —— Windows 上管道接住的 Python 子进程默认按 cp936 输出"""
    assert _engine()._CHILD_ENV.get("PYTHONIOENCODING") == "utf-8"


class _FakeProc:
    """假子进程: 只提供 `_shell` 要读的三个属性。"""
    def __init__(self, stdout: bytes, stderr: bytes = b"", returncode: int = 0):
        self.stdout, self.stderr, self.returncode = stdout, stderr, returncode


def _patch_run(monkeypatch, proc: _FakeProc) -> dict:
    """换掉 subprocess.run 并回传收到的参数 —— **进程内**验证接线。

    本项目测试禁止真起外部进程(`tests/sidefx.py` 的 POPEN 记账会判越界), 所以
    "子进程给了什么字节"由假对象直接给, 反而比真跑更好控制。
    """
    mod = _engine()
    seen: dict = {}

    def fake(cmd, **kwargs):
        seen["cmd"] = cmd
        seen.update(kwargs)
        return proc

    monkeypatch.setattr(mod.subprocess, "run", fake)
    return seen


def test_shell_injects_env_and_captures_bytes(monkeypatch):
    """接线守阵: 注入 _CHILD_ENV(pack env 仍可覆盖), 并按**字节**收输出。"""
    seen = _patch_run(monkeypatch, _FakeProc(b"ok"))
    ok, out = _engine()._shell("python x.py", 5, env={"CMD_PACK": "kb"})
    assert ok and out == "ok"
    assert seen["env"]["PYTHONIOENCODING"] == "utf-8", "子进程必须被强制 UTF-8 stdio"
    assert seen["env"]["CMD_PACK"] == "kb", "包自己的环境变量不能被引擎覆盖"
    assert not seen.get("text") and not seen.get("encoding"), "按字节收, 解码交给 _decode 兜底"


def test_shell_decodes_gbk_child_output(monkeypatch):
    """回归守阵(2026-09-24 实测形态): 子进程交回 GBK 字节时, 返回文本必须可读而非 U+FFFD"""
    _patch_run(
        monkeypatch,
        _FakeProc("已生成 16 个索引\n".encode("gbk"), "更新 memory-bank/tasks/_index.md\n".encode("gbk")),
    )
    ok, out = _engine()._shell("python gen_index.py", 5)
    assert ok
    assert "已生成 16 个索引" in out and "更新 memory-bank/tasks/_index.md" in out
    assert "\ufffd" not in out, "按 UTF-8 硬解 GBK 字节会得到一串 U+FFFD"


def test_shell_failure_keeps_rc(monkeypatch):
    """非 0 退出码照旧传出去 —— 解码改动不能把失败吞成成功"""
    _patch_run(monkeypatch, _FakeProc("boom\n".encode("gbk"), returncode=1))
    ok, out = _engine()._shell("python fail.py", 5)
    assert not ok and "boom" in out


def test_wrapper_repo_root_walk(tmp_path):
    """从深层子目录向上找含 `.commands/` 的仓库根 —— wrapper 运行期用的是同一判据"""
    mod = _wrapper()
    root = tmp_path / "proj"
    (root / ".commands" / "demo").mkdir(parents=True)
    deep = root / "src" / "pkg" / "sub"
    deep.mkdir(parents=True)
    assert mod.repo_root(deep) == root
    assert mod.repo_root(tmp_path) is None, "不在项目里必须返回 None(而不是瞎猜一个根)"


def test_wrapper_path_dir_picks_dir_on_path(tmp_path, monkeypatch):
    """只在**已在 PATH 上**的目录里装"项目无关"那份; 在 PATH 上但不存在 → 建出来"""
    mod = _wrapper()
    monkeypatch.setattr(Path, "home", staticmethod(lambda: tmp_path))
    absent = tmp_path / "bin"
    got, note = mod.path_dir({"PATH": str(absent)})
    assert got == absent and absent.is_dir(), "在 PATH 上但不存在 → 建出来"
    assert "新建" in note
    got, note = mod.path_dir({"PATH": str(absent)})
    assert got == absent and "已在 PATH 上" in note
    got, note = mod.path_dir({"PATH": str(tmp_path / "elsewhere")})
    assert got is None and "不在 PATH 上" in note


def test_wrapper_end_to_end_passes_args(tmp_path):
    """端到端: 生成的 wrapper 真跑一次 —— 向上找到假仓库根 → 找到假引擎 → 参数原样转过去

    这是这个功能的**核心承诺**(`commands run <task>` 真的可敲), 所以按平台跑真脚本:
    POSIX 直接 exec sh; Windows 经 shell 跑 `.cmd`(CreateProcess 不认 shebang)。
    """
    mod = _wrapper()
    root = tmp_path / "proj"
    engine = root / ".agents" / "skills" / "commands" / "scripts" / "run.py"
    engine.parent.mkdir(parents=True)
    (root / ".commands" / "demo").mkdir(parents=True)
    engine.write_text("import sys\nprint('STUB', *sys.argv[1:])\n", encoding="utf-8")
    names = mod.bodies(os.name)
    for name, text in names.items():
        mod.write_one(root / name, text, dry_run=False, force=False)

    if os.name == "nt":
        proc = subprocess.run(
            f'"{root / "commands.cmd"}" show demo.x',
            cwd=str(root),
            shell=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace"
        )
    else:
        proc = subprocess.run(
            [str(root / "commands"), "show", "demo.x"],
            cwd=str(root),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace"
        )
    assert proc.returncode == 0, proc.stderr
    assert "STUB show demo.x" in proc.stdout, "参数必须原样转发给引擎"

    # 从子目录调用也要能找到仓库根(项目无关那份靠的就是这个)
    sub = root / "src"
    sub.mkdir()
    if os.name == "nt":
        proc = subprocess.run(
            f'"{root / "commands.cmd"}" list',
            cwd=str(sub),
            shell=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace"
        )
    else:
        proc = subprocess.run(
            [str(root / "commands"), "list"],
            cwd=str(sub),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace"
        )
    assert proc.returncode == 0 and "STUB list" in proc.stdout
