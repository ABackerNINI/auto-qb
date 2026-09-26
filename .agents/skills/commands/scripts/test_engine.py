"""引擎输出契约测试 —— RESULT 协议 / 无裸 rc / 自证压缩 / 超时指名(计划 26-09-26-2345 P1)。

被测对象是 commands 引擎本体(.agents/skills/commands/scripts/run.py), 测试贴着引擎放;
test.pkg 收集面 = .commands + .agents/skills/commands, 改引擎必被收到(修复"闸门空转")。
不碰真实仓库状态: cmd_run 的 _shell 全部 monkeypatch, load_tree 只读真实包配置。

## 测试计划
- test_digest_keeps_result_lines         摘要必保 RESULT/WHY/NEXT/EVIDENCE 协议行
- test_digest_fallback_without_protocol  无协议行 → 维持"末 N 行 + 异常行"旧行为
- test_run_failure_transcribes_protocol  失败路径: [FAIL] 行后转述协议行, 文本无裸 rc
- test_run_failure_without_protocol      失败且无协议行 → 退回旧摘要, 不炸
- test_run_success_keeps_evidence        成功路径协议行(证据)存活
- test_run_selfcheck_compressed          risky 自证 = 首条 + 条数, 不再全量打印
- test_run_timeout_names_command         超时指名卡住的命令
"""

import argparse
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import _config as C  # noqa: E402
import run as engine  # noqa: E402


def _shell_returning(ok: bool, out: str):
    return lambda *a, **k: (ok, out)


def test_digest_keeps_result_lines():
    lines = [f"noise {i:02d}" for i in range(30)]
    lines[5] = "RESULT: FAIL 落后远端 3 个提交"
    lines += ["EVIDENCE: remote=abc local=def", "WHY: 收尾回写必须落在合并后的新基线上", "NEXT: git fetch gitee develop"]
    picked, _ = engine._digest("\n".join(lines), limit=3)
    text = "\n".join(picked)
    for needle in ("RESULT: FAIL", "EVIDENCE: remote=abc", "WHY: 收尾回写", "NEXT: git fetch"):
        assert needle in text, f"协议行被摘要截掉: {needle}"


def test_digest_fallback_without_protocol():
    lines = [f"noise {i:02d}" for i in range(30)]
    lines[10] = "[WARN] 中段的警告内容"
    picked, skipped = engine._digest("\n".join(lines), limit=3)
    text = "\n".join(picked)
    assert "[WARN] 中段的警告内容" in text  # 异常行照旧保留
    assert "noise 29" in text  # 末 N 行照旧
    assert skipped == 30 - len(picked)


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
    assert "[FAIL] doc.links" in captured  # 退回旧 [FAIL] 摘要, 不炸
    assert "ValueError: boom" in captured


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
    tree.tasks["kb.index"].risky = True  # 借多命令 task 冒充 risky(进程内改动, 不落盘)
    monkeypatch.setattr(C, "load_tree", lambda: tree)  # cmd_run 内部还会 load 一次 —— 必须让它拿到同一份
    monkeypatch.setattr(engine, "_shell", _shell_returning(True, ""))
    rc = engine.cmd_run(argparse.Namespace(task="kb.index", extra=[]))
    captured = capsys.readouterr().out
    assert rc == 0
    assert "[自证] kb.index 将要执行:" in captured
    assert "…(共 4 条, 全量: show kb.index)" in captured
    assert captured.count("gen_tasks_index") == 1  # 只打首条, 其余三条不再全量展开


def test_run_timeout_names_command(monkeypatch, capsys):
    def _timeout_shell(*a, **k):
        raise subprocess.TimeoutExpired(cmd="pytest", timeout=300)

    monkeypatch.setattr(engine, "_shell", _timeout_shell)
    rc = engine.cmd_run(argparse.Namespace(task="doc.links", extra=[]))
    captured = capsys.readouterr().out
    assert rc == engine.FAILED
    assert "超时(180s)" in captured
    assert "check_doc_links" in captured  # 指名卡住的命令


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
