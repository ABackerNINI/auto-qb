"""引擎输出契约测试 —— RESULT 协议 / 无裸 rc / 全文透传 / 声明式静默 / 自证压缩 / 超时指名。

被测对象是 commands 引擎本体(.agents/skills/commands/scripts/run.py), 测试贴着引擎放;
test.pkg 收集面 = .commands + .agents/skills/commands, 改引擎必被收到(修复"闸门空转")。
不碰真实仓库状态: cmd_run 的 _shell 全部 monkeypatch, load_tree 只读真实包配置。

输出形态(2026-09-30 定调): 默认**全文透传**, 引擎不做有损摘要、不打「略过 N 行」提示 ——
摘要 + 提示会逼调用方 show → 裸跑两步返工(会话后期每步都是带全量历史的整轮请求, token 税)。
省 token 走声明式: 任务标 silent_success → 成功只出结论行, 失败照旧全文。

## 测试计划
- test_conclusions_keep_conclusion_line          声明式静默: 结论行(N passed / TOTAL)必留, 噪音明细不上屏
- test_conclusions_fallback_when_no_conclusion   无结论形态 → 退回末 N 行, 不变盲
- test_conclusion_patterns_are_anchored          结论判据钉锚(行中 passed 不算)
- test_silent_success_flag_parsed_from_config    test.full/quick/pkg 从配置解析 silent_success, 信息类不声明
- test_stream_flag_parsed_from_config            kb.nav 声明 stream, 其余任务不声明
- test_stream_mode_runs_attached                 stream 任务 stdio 直连(不捕获/不吃 timeout), 成功出 [ok]
- test_stream_mode_ctrlc_is_clean_stop           stream 任务 Ctrl-C → rc 0 + [stop] 行, 不裸 traceback
- test_silent_success_success_is_quiet           静默任务成功只出结论行; 「略过」提示不给
- test_silent_success_falls_back_at_cmd_run      静默任务输出形态变了 → cmd_run 层面退回末 N 行, 仍无提示
- test_run_success_passthrough_full              默认成功: 全文透传, 中段内容原样可见, 无「略过」提示
- test_run_failure_passthrough_full              失败: [FAIL] + 协议行转述一遍 + 全文, 中段异常行可见, 无提示
- test_run_failure_transcribes_protocol          失败路径: [FAIL] 行后转述协议行, 文本无裸 rc
- test_run_failure_without_protocol              失败且无协议行 → 原文透传, 不炸
- test_run_success_keeps_evidence                成功路径协议行(证据)存活
- test_run_selfcheck_compressed                  risky 自证 = 首条 + 条数, 不再全量打印
- test_run_timeout_names_command                 超时指名卡住的命令
- test_shell_kills_process_tree_on_timeout       超时杀**整棵进程树**(不 kill 直接子进程) + 上抛 TimeoutExpired
- test_utf8_self_stdio_reconfigures_text_layer   引擎自身 stdio 锁 UTF-8: cp936 文本层重配后中文按 UTF-8 出
- test_engine_self_stdio_utf8_in_pipes           管道 + 剥离 UTF-8 变量子进程: 引擎输出 strict UTF-8 解码必过
"""

import argparse
import io
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import _config as C  # noqa: E402
import run as engine  # noqa: E402


def _shell_returning(ok: bool, out: str):
    return lambda *a, **k: (ok, out)


def test_conclusions_keep_conclusion_line():
    """声明式静默只留结论行: pytest 警告明细 / 覆盖率表打在结论行前后, 都不上屏。"""
    lines = [f"coverage row {i:02d}" for i in range(20)]
    lines[2] = "1818 passed, 3 skipped, 6 warnings in 20.09s"  # 结论在 coverage 表之前
    lines[-1] = "src\\auto_qb\\webui\\views.py  305  6  130  3  97%"  # 末行是表尾噪音
    lines[6] = "TOTAL 12504 914 4204 388 91%"
    picked = engine._conclusions("\n".join(lines))
    text = "\n".join(picked)
    assert "1818 passed" in text  # 结论行必留
    assert "TOTAL 12504" in text
    assert "views.py" not in text  # 噪音明细不上屏


def test_conclusions_fallback_when_no_conclusion():
    """无结论形态 → 退回末 N 行, 不让输出彻底变盲。"""
    lines = [f"plain line {i}" for i in range(10)]
    picked = engine._conclusions("\n".join(lines))
    assert picked == [f"plain line {i}" for i in range(7, 10)]


def test_conclusion_patterns_are_anchored():
    """结论判据钉锚: 表格中段含 'passed' 字样的行不算结论, 免得静默输出被撑爆。"""
    lines = [f"noise {i:02d}" for i in range(30)]
    lines[10] = "  it passed the sanity check of module x"  # 行中 passed, 非结论形态
    picked = engine._conclusions("\n".join(lines))
    assert "it passed the sanity check" not in "\n".join(picked)


def test_silent_success_flag_parsed_from_config():
    """test.full/quick/pkg 声明了 silent_success —— 引擎从真实包配置解析出该旗标; 信息类不声明。"""
    mod = engine
    tree = mod.C.load_tree()
    assert tree.tasks["test.full"].silent_success is True
    assert tree.tasks["test.quick"].silent_success is True
    assert tree.tasks["test.pkg"].silent_success is True
    assert tree.tasks["kb.index"].silent_success is False  # 信息类: 成功全文透传, 靠声明而非引擎摘要省 token


def test_stream_flag_parsed_from_config():
    """kb.nav 声明 stream(前台长跑) —— 引擎从真实包配置解析出该旗标; 其余任务不声明。"""
    mod = engine
    tree = mod.C.load_tree()
    assert tree.tasks["kb.nav"].stream is True
    assert tree.tasks["kb.index"].stream is False
    assert tree.tasks["test.full"].stream is False


def test_stream_mode_runs_attached(monkeypatch, capsys):
    """stream 任务直连执行: 不捕获输出(实时可见)、不吃 timeout(常驻服务没有"跑完")。"""
    recorded = {}

    class _Proc:
        returncode = 0

    def _fake_run(cmd, **kwargs):
        recorded["cmd"] = cmd
        recorded.update(kwargs)
        return _Proc()

    monkeypatch.setattr(engine.subprocess, "run", _fake_run)
    rc = engine.cmd_run(argparse.Namespace(task="kb.nav", extra=[]))
    captured = capsys.readouterr().out
    assert rc == 0
    assert "capture_output" not in recorded or recorded["capture_output"] is False
    assert "timeout" not in recorded  # timeout 不适用 —— 常驻服务不能被引擎按秒杀掉
    assert "[ok] kb.nav" in captured


def test_stream_mode_ctrlc_is_clean_stop(monkeypatch, capsys):
    """stream 任务 Ctrl-C: 引擎层捕获 KeyboardInterrupt → rc 0 + [stop] 行, 不给调用方裸 traceback。"""
    def _fake_run(cmd, **kwargs):
        raise KeyboardInterrupt()

    monkeypatch.setattr(engine.subprocess, "run", _fake_run)
    rc = engine.cmd_run(argparse.Namespace(task="kb.nav", extra=[]))
    captured = capsys.readouterr().out
    assert rc == 0
    assert "[stop] kb.nav" in captured


def test_silent_success_success_is_quiet(monkeypatch, capsys):
    out = "\n".join(
        [
            "=" * 40, "1818 passed, 3 skipped in 20.17s", "TOTAL 12512 914 4204 388 91%",
            *(f"cov row {i}" for i in range(30))
        ]
    )
    monkeypatch.setattr(engine, "_shell", _shell_returning(True, out))
    rc = engine.cmd_run(argparse.Namespace(task="test.full", extra=[]))
    captured = capsys.readouterr().out
    assert rc == 0
    assert "[ok] test.full" in captured
    assert "1818 passed" in captured and "TOTAL 12512" in captured  # 结论行在
    assert "略过" not in captured  # 「略过」提示任何形态都不给
    assert "cov row" not in captured  # 明细不上屏


def test_silent_success_falls_back_at_cmd_run(monkeypatch, capsys):
    """旗标任务输出形态变了(一条结论都没有) → 退回末 N 行, 不变盲; 提示仍不打。"""
    out = "\n".join(f"plain line {i}" for i in range(10))
    monkeypatch.setattr(engine, "_shell", _shell_returning(True, out))
    rc = engine.cmd_run(argparse.Namespace(task="test.full", extra=[]))
    captured = capsys.readouterr().out
    assert rc == 0
    assert "plain line 9" in captured  # 末 N 行兜底
    assert "plain line 0" not in captured
    assert "略过" not in captured


def test_run_success_passthrough_full(monkeypatch, capsys):
    """默认(未声明静默)成功 = 全文透传: 首尾与中段全部可见, 无「略过」提示 —— 修两步返工的 token 税。"""
    out = "\n".join(f"slice {i}" for i in range(30))
    monkeypatch.setattr(engine, "_shell", _shell_returning(True, out))
    rc = engine.cmd_run(argparse.Namespace(task="doc.links", extra=[]))
    captured = capsys.readouterr().out
    assert rc == 0
    assert "slice 0" in captured and "slice 29" in captured  # 首尾都在
    assert "slice 15" in captured  # 中段不被截
    assert "略过" not in captured


def test_run_failure_passthrough_full(monkeypatch, capsys):
    """失败 = 协议行转述一遍 + 全文透传: 中段的异常内容必须可见, 失败不该再逼一次重跑。"""
    lines = [f"noise {i:02d}" for i in range(40)]
    lines[10] = "  [STOP] 中段的具体原因"
    lines += ["RESULT: FAIL 预检未过", "NEXT: 处理后重跑"]
    monkeypatch.setattr(engine, "_shell", _shell_returning(False, "\n".join(lines)))
    rc = engine.cmd_run(argparse.Namespace(task="doc.links", extra=[]))
    captured = capsys.readouterr().out
    assert rc == engine.FAILED
    assert "[FAIL] doc.links" in captured
    assert "[STOP] 中段的具体原因" in captured  # 中段异常行不被截
    assert captured.count("RESULT: FAIL 预检未过") == 1  # 转述一遍, 正文里已剥掉
    assert captured.count("NEXT: 处理后重跑") == 1
    assert "略过" not in captured


def test_run_failure_transcribes_protocol(monkeypatch, capsys):
    out = "\n".join(
        [
            "预检结果:",
            "  [STOP] 落后主线: 落后 3 个提交 —— 先合并远端, 再收尾回写、后提交",
            "RESULT: FAIL 落后远端 3 个提交, 未提交",
            "WHY: 收尾回写必须落在合并后的新基线上",
            "NEXT: git fetch gitee develop && git merge --ff-only FETCH_HEAD",
        ]
    )
    monkeypatch.setattr(engine, "_shell", _shell_returning(False, out))
    rc = engine.cmd_run(argparse.Namespace(task="doc.links", extra=[]))
    captured = capsys.readouterr().out
    assert rc == engine.FAILED
    assert "[FAIL] doc.links" in captured
    assert "RESULT: FAIL 落后远端 3 个提交" in captured
    assert "WHY: 收尾回写" in captured
    assert "NEXT: git fetch gitee develop" in captured
    assert "rc" not in captured  # 文本通道无裸 rc —— 别给调用方留"去查码表"的钩子


def test_run_failure_without_protocol(monkeypatch, capsys):
    monkeypatch.setattr(engine, "_shell", _shell_returning(False, "Traceback …\nValueError: boom"))
    rc = engine.cmd_run(argparse.Namespace(task="doc.links", extra=[]))
    captured = capsys.readouterr().out
    assert rc == engine.FAILED
    assert "[FAIL] doc.links" in captured  # [FAIL] 行照旧
    assert "ValueError: boom" in captured  # 原文透传, 不炸


def test_run_success_keeps_evidence(monkeypatch, capsys):
    out = "推送完成\nEVIDENCE: remote=abc local=abc\nRESULT: OK 已推送, 远端一致"
    monkeypatch.setattr(engine, "_shell", _shell_returning(True, out))
    rc = engine.cmd_run(argparse.Namespace(task="doc.links", extra=[]))
    captured = capsys.readouterr().out
    assert rc == 0
    assert "RESULT: OK 已推送, 远端一致" in captured
    assert "EVIDENCE: remote=abc local=abc" in captured


def test_run_selfcheck_compressed(monkeypatch, capsys):
    tree = C.load_tree()
    task = tree.tasks["kb.check"]  # 借**多命令** task 冒充 risky(进程内改动, 不落盘)
    task.risky = True
    monkeypatch.setattr(C, "load_tree", lambda: tree)  # cmd_run 内部还会 load 一次 —— 必须让它拿到同一份
    monkeypatch.setattr(engine, "_shell", _shell_returning(True, ""))
    rc = engine.cmd_run(argparse.Namespace(task="kb.check", extra=[]))
    captured = capsys.readouterr().out
    assert rc == 0
    assert "[自证] kb.check 将要执行:" in captured
    n = len(C.task_commands(task, tree.root, []))
    assert n > 1  # 这条用例专测「多命令压缩」—— 单命令 task 根本不出压缩行(2026-10-03 kb.index 收成一条后换 kb.check)
    assert f"…(共 {n} 条, 全量: show kb.check)" in captured
    assert captured.count("gen_all.py") == 1  # 只打首条, 其余不再全量展开


def test_run_timeout_names_command(monkeypatch, capsys):
    def _timeout_shell(*a, **k):
        raise subprocess.TimeoutExpired(cmd="pytest", timeout=300)

    monkeypatch.setattr(engine, "_shell", _timeout_shell)
    rc = engine.cmd_run(argparse.Namespace(task="doc.links", extra=[]))
    captured = capsys.readouterr().out
    assert rc == engine.FAILED
    assert "超时(180s)" in captured
    assert "check_doc_links" in captured  # 指名卡住的命令


def test_shell_kills_process_tree_on_timeout(monkeypatch):
    """超时必须杀**整棵进程树**, 且照旧上抛 TimeoutExpired。

    根因(2026-10-08 实报): `shell=True` 下直接子进程是 cmd.exe, 真正干活的工具是孙子; 旧实现走
    `subprocess.run(timeout=)` 只 kill 直接子进程 ⇒ 工具(yapf)被留成**孤儿**, 继续 100% CPU 烧着、
    还占着管道读端。守阵: 超时路径必须走 `_kill_tree(pid)`, 且**不得**只 `kill()` 直接子进程。
    """
    killed: list = []

    class _FakeProc:
        pid = 4242

        def communicate(self, timeout=None):
            raise subprocess.TimeoutExpired(cmd="yapf", timeout=timeout)

        def kill(self):  # 只杀直接子进程 = 正是要禁掉的旧行为
            raise AssertionError("不得只 kill 直接子进程 —— shell=True 下那是 cmd.exe, 孙子会成孤儿")

    monkeypatch.setattr(engine.subprocess, "Popen", lambda *a, **k: _FakeProc())
    monkeypatch.setattr(engine, "_kill_tree", lambda pid: killed.append(pid))
    try:
        engine._shell("yapf -i x.py", 1)
    except subprocess.TimeoutExpired:
        pass
    else:
        raise AssertionError("超时必须上抛 TimeoutExpired(cmd_run 靠它打「超时指名卡住的命令」)")
    assert killed == [4242], f"超时必须杀整棵进程树(且带真实 pid): {killed}"


def test_extra_argv_passthrough():
    # P2 契约: 含空格的路径必须原样到达脚本 argv —— 旧链路 join→split 会把它拆成两半
    tree = C.load_tree()
    task = tree.tasks["my-commit-flow.verify-ref"]
    cmds = C.task_commands(task, tree.root, ["R:/Temp/x y/a b.py"])
    assert '"R:/Temp/x y/a b.py"' in cmds[0]


def test_extra_run_type_quoted_on_substitution():
    # run 型(<args> 占位符): 文本替换前对每个元素统一加引号, 空格路径进命令串仍是完整一个
    tree = C.load_tree()
    task = tree.tasks["dev.fmt"]
    cmds = C.task_commands(task, tree.root, ["R:/Temp/x y/a b.py"])
    assert 'yapf -i "R:/Temp/x y/a b.py"' in cmds[0]


def test_utf8_self_stdio_reconfigures_text_layer():
    """助手单测: cp936 文本层被重配成 UTF-8 —— 与系统码页无关, 全平台确定。"""
    buf = io.BytesIO()
    stream = io.TextIOWrapper(buf, encoding="cp936")
    engine._utf8_self_stdio(stream)
    stream.write("何时用")
    stream.flush()
    assert buf.getvalue() == "何时用".encode("utf-8")


def test_engine_self_stdio_utf8_in_pipes():
    """管道 + 剥离全局 UTF-8 变量: 引擎自己的输出必须仍是 UTF-8(部分终端乱码的端到端回归)。

    真控制台走 WriteConsoleW 永不乱; 乱的是 stdout 被管道接住且进程没开 UTF-8 模式的
    场景(mintty / AI 工具捕获 / CI 日志) —— 剥变量就是在模拟它。strict 解码: 引擎若仍
    按本地码页出, 这里当场 UnicodeDecodeError, 静默乱码变硬失败。系统码页本就是 UTF-8
    的机器上本测试失去分辨力(不假红, 与 _local_codepage 的口径一致)。
    """
    env = {
        k: v
        for k, v in os.environ.items() if k not in ("PYTHONUTF8", "PYTHONIOENCODING", "PYTHONLEGACYWINDOWSSTDIO")
    }
    proc = subprocess.run(
        [sys.executable, str(Path(engine.__file__)), "show", "no-such.task"],
        capture_output=True,
        env=env,
        timeout=60,
        cwd=str(C.find_root()),
    )
    assert proc.returncode == 1
    text = proc.stderr.decode("utf-8")  # strict —— 引擎仍按 GBK 出的话这里当场炸
    assert "没有这个 task" in text
