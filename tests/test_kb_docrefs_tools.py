"""doc-refs 认领链机械化守阵 (issue 26-10-31-2226-feat-kb-docrefs-bidirectional-automation)。

守什么: 认领链双向声明从「人记两处」变成「机器保证」之后的三个不变量 ——
1. 写入器对**空值占位行**(模板自带)必须原位并值, 绝不另插一行 (复发 8 的 md/HTML 两版形态);
2. gen_doc_map --check 必须把「多行 doc-refs meta / 多行 **Refs:**」判红 (复发 8 根因此前无机检,
   解析器 search()/dict(findall()) 对重复行静默塌缩);
3. kb.ref(set_doc_refs)必须 fail-fast: 目标未落盘整笔拒写 (复发 6「先回填后落盘」悬空窗口)、
   plans/reports 不作目标 (复发 5 收敛法)、声明方/目标已有重复声明行拒写。

检查器与命令实现: memory-bank skill 的 `scripts/_common.py`(md_set_refs/html_set_refs) /
`scripts/gen_doc_map.py`(check_duplicate_declarations) / `scripts/set_doc_refs.py`, 进程内 import
—— 本项目测试禁止起子进程。

## 测试计划

- test_md_set_refs_fills_empty_placeholder_in_place: 空 `**Refs:**` 占位行原位并值, 全文仅一行声明
- test_md_set_refs_merges_into_existing: 已有声明行并值不丢旧值, 仍仅一行
- test_html_set_refs_fills_empty_meta_in_place: 空 doc-refs meta 原位并值, 全文仅一处 meta
- test_doc_map_flags_duplicate_declarations: 多行声明判红(HTML+md), 干净目录无报
- test_set_doc_refs_claims_bidirectionally: 双向补链 + 幂等重跑无改动 + 声明各仅一处
- test_set_doc_refs_refuses_missing_target: 目标未落盘整笔拒写(复发 6), 声明方零改动
- test_set_doc_refs_refuses_frozen_targets: plans/ 目标拒绝 (复发 5 收敛法)
- test_set_doc_refs_refuses_duplicate_declaration: 声明方已有重复 meta 拒写 (复发 8)
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL_SCRIPTS = ROOT / ".agents" / "skills" / "memory-bank" / "scripts"
sys.path.insert(0, str(SKILL_SCRIPTS))

from _common import html_set_refs, md_set_refs  # noqa: E402
from gen_doc_map import check_duplicate_declarations  # noqa: E402
import set_doc_refs as sdr  # noqa: E402

ISSUE_HTML = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="issue-status" content="Open">
<meta name="doc-topic" content="t">
<meta name="doc-refs" content="">
<meta name="doc-updated" content="26-10-31-2340">
</head>
<body></body>
</html>
"""

TASK_MD = """# 26-10-31-demo — demo

**Status:** In Progress
**Added:** 2026-10-31
**Updated:** 2026-10-31
**Summary:** demo
**Topics:** demo
**Refs:**

## 原始请求
"""


def _mb(tmp_path: Path) -> tuple[Path, Path]:
    root = tmp_path
    mb = root / "memory-bank"
    for sub in ("issues", "tasks", "plans", "reports"):
        (mb / sub).mkdir(parents=True, exist_ok=True)
    return root, mb


def test_md_set_refs_fills_empty_placeholder_in_place() -> None:
    out = md_set_refs(TASK_MD, "memory-bank/issues/x.html")
    lines = [ln for ln in out.splitlines() if ln.startswith("**Refs:**")]
    assert len(lines) == 1, f"声明必须只有一行, 实得 {len(lines)}"
    assert lines[0] == "**Refs:** memory-bank/issues/x.html"
    assert md_set_refs(out, "memory-bank/issues/x.html") == out  # 幂等


def test_md_set_refs_merges_into_existing() -> None:
    text = TASK_MD.replace("**Refs:**\n", "**Refs:** memory-bank/issues/a.html\n")
    out = md_set_refs(text, "memory-bank/issues/b.html")
    lines = [ln for ln in out.splitlines() if ln.startswith("**Refs:**")]
    assert len(lines) == 1
    assert "memory-bank/issues/a.html" in lines[0] and "memory-bank/issues/b.html" in lines[0]


def test_html_set_refs_fills_empty_meta_in_place() -> None:
    out = html_set_refs(ISSUE_HTML, "memory-bank/tasks/x.md")
    metas = [ln for ln in out.splitlines() if '<meta name="doc-refs"' in ln]
    assert len(metas) == 1, f"meta 必须只有一处, 实得 {len(metas)}"
    assert 'content="memory-bank/tasks/x.md"' in metas[0]
    assert html_set_refs(out, "memory-bank/tasks/x.md") == out  # 幂等


def test_doc_map_flags_duplicate_declarations(tmp_path: Path) -> None:
    root, mb = _mb(tmp_path)
    assert check_duplicate_declarations(mb) == []  # 干净目录
    (mb / "issues" / "bad.html").write_text(
        ISSUE_HTML.replace(
            '<meta name="doc-refs" content="">',
            '<meta name="doc-refs" content="">\n<meta name="doc-refs" content="memory-bank/tasks/x.md">'
        ),
        encoding="utf-8"
    )
    (mb / "tasks" / "bad.md").write_text(TASK_MD + "**Refs:** memory-bank/issues/bad.html\n", encoding="utf-8")
    problems = check_duplicate_declarations(mb)
    assert len(problems) == 2, problems
    joined = "\n".join(problems)
    assert "issues/bad.html" in joined and "tasks/bad.md" in joined
    assert "复发 8" in joined  # 报错必须指向病根形态, 不只报条数


def test_set_doc_refs_claims_bidirectionally(tmp_path: Path, capsys) -> None:
    root, mb = _mb(tmp_path)
    issue = mb / "issues" / "i.html"
    task = mb / "tasks" / "t.md"
    issue.write_text(ISSUE_HTML, encoding="utf-8")
    task.write_text(TASK_MD, encoding="utf-8")
    rc = sdr.main(["--root", str(root), str(issue), "--add", "memory-bank/tasks/t.md"])
    assert rc == 0
    issue_text = issue.read_text(encoding="utf-8")
    task_text = task.read_text(encoding="utf-8")
    assert 'content="memory-bank/tasks/t.md"' in issue_text
    assert "**Refs:** memory-bank/issues/i.html" in task_text
    assert len([ln for ln in issue_text.splitlines() if '<meta name="doc-refs"' in ln]) == 1
    assert len([ln for ln in task_text.splitlines() if ln.startswith("**Refs:**")]) == 1
    capsys.readouterr()
    rc2 = sdr.main(["--root", str(root), str(issue), "--add", "memory-bank/tasks/t.md"])
    assert rc2 == 0  # 幂等重跑
    assert "幂等, 无改动" in capsys.readouterr().out


def test_set_doc_refs_refuses_missing_target(tmp_path: Path) -> None:
    root, mb = _mb(tmp_path)
    issue = mb / "issues" / "i.html"
    issue.write_text(ISSUE_HTML, encoding="utf-8")
    before = issue.read_text(encoding="utf-8")
    rc = sdr.main(["--root", str(root), str(issue), "--add", "memory-bank/tasks/not-yet.md"])
    assert rc == 1
    assert issue.read_text(encoding="utf-8") == before, "拒写时声明方必须零改动 (复发 6 拦截)"


def test_set_doc_refs_refuses_frozen_targets(tmp_path: Path) -> None:
    root, mb = _mb(tmp_path)
    issue = mb / "issues" / "i.html"
    plan = mb / "plans" / "p.html"
    issue.write_text(ISSUE_HTML, encoding="utf-8")
    plan.write_text(ISSUE_HTML, encoding="utf-8")
    rc = sdr.main(["--root", str(root), str(issue), "--add", "memory-bank/plans/p.html"])
    assert rc == 1


def test_set_doc_refs_refuses_duplicate_declaration(tmp_path: Path) -> None:
    root, mb = _mb(tmp_path)
    issue = mb / "issues" / "bad.html"
    task = mb / "tasks" / "t.md"
    issue.write_text(
        ISSUE_HTML.replace(
            '<meta name="doc-refs" content="">',
            '<meta name="doc-refs" content="">\n<meta name="doc-refs" content="memory-bank/tasks/t.md">'
        ),
        encoding="utf-8"
    )
    task.write_text(TASK_MD, encoding="utf-8")
    before = issue.read_text(encoding="utf-8")
    rc = sdr.main(["--root", str(root), str(issue), "--add", "memory-bank/tasks/t.md"])
    assert rc == 1
    assert issue.read_text(encoding="utf-8") == before
