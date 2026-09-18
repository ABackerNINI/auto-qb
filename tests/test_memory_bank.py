"""Memory Bank 结构守卫测试 (TASK010)。

守什么: 知识库的"跨会话连续性"完全依赖 `memory-bank/tasks/` 与入口文件的**结构化约定** —
一旦索引与档案脱钩 (登记了没文件 / 有文件没登记)、状态分区与档案 `Status` 不一致、
必备章节缺失, 下次会话就无法从 `tasks/` 续作; 一旦会话纪要回流进 `activeContext.md`,
该文件会重新膨胀成流水账 (2026-09-17 复盘的真实故障)。这些判定都是纯静态的, 用测试守住成本极低。

## 测试计划

- test_tasks_index_and_files_are_bijective: `_index.md` 登记的 TASKID 与 `tasks/TASK*.md` 文件双向一致
- test_task_ids_and_slugs_are_unique: 档案 slug 不重复、索引中同一 TASKID 不重复登记(并行 worktree 各自立档的重复档案/重复条目)
- test_task_file_naming_and_sections: 文件名符合 `TASKnnn-slug.md`, 且五个必备章节齐全
- test_task_status_matches_index_section: 档案 `**Status:**` 与索引所在分区一致
- test_index_has_all_status_sections: 索引保留四个状态分区标题
- test_active_context_has_no_rolled_up_session_log: `activeContext.md` 不出现 `^- 2026-` 流水账纪要行
- test_session_protocol_is_exposed_in_always_on_entries: skill 载体存在且含阈值/DoD, AGENTS 与 copilot-instructions 均声明阈值并指向 skill
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MB = ROOT / "memory-bank"
TASKS = MB / "tasks"
INDEX = TASKS / "_index.md"
SKILL = ROOT / ".agents" / "skills" / "memory-bank" / "SKILL.md"

STATUSES = ("In Progress", "Pending", "Completed", "Abandoned")
REQUIRED_SECTIONS = ("## 原始请求", "## 思考过程与决策", "## 实现计划", "## 子任务状态表", "## 进度日志")
INDEX_ID_RE = re.compile(r"- \[(TASK\d{3})\]")
FILE_RE = re.compile(r"^TASK\d{3}-[a-z0-9]+(?:-[a-z0-9]+)*\.md$")
STATUS_RE = re.compile(r"\*\*Status:\*\* (In Progress|Pending|Completed|Abandoned)")


def _task_files() -> list[Path]:
    return sorted(TASKS.glob("TASK*.md"))


def _indexed_sections() -> dict[str, str]:
    sections: dict[str, str] = {}
    current = ""
    for line in INDEX.read_text(encoding="utf-8").splitlines():
        if line.startswith("## "):
            current = line[3:].strip()
            continue
        for task_id in INDEX_ID_RE.findall(line):
            sections[task_id] = current
    return sections


def test_tasks_index_and_files_are_bijective() -> None:
    indexed = set(_indexed_sections())
    on_disk = {path.name[:7] for path in _task_files()}

    assert indexed == on_disk, (f"索引与档案文件不一致: 仅索引登记={sorted(indexed - on_disk)}, "
                                f"仅有文件={sorted(on_disk - indexed)}")


def test_task_ids_and_slugs_are_unique() -> None:
    """并行 worktree 各自立档会产出重复: 同一专题两份档案 (2026-09-18 实测 TASK014/TASK015 逐字节相同)
    + 索引里重复登记。重复条目在 dict 式解析里会静默覆盖, 双向一致与状态分区两个守卫都发现不了,
    所以必须单独守。"""
    slugs: dict[str, list[str]] = {}
    for path in _task_files():
        slugs.setdefault(path.name[8:-3], []).append(path.name)  # 去掉 `TASKnnn-` 前缀与 `.md`
    dup_slugs = {slug: names for slug, names in slugs.items() if len(names) > 1}

    assert not dup_slugs, f"存在同 slug 的重复任务档案 (并行分支各建一份): {dup_slugs}"

    indexed = INDEX_ID_RE.findall(INDEX.read_text(encoding="utf-8"))
    dup_ids = sorted({task_id for task_id in indexed if indexed.count(task_id) > 1})

    assert not dup_ids, f"索引中同一 TASKID 被重复登记: {dup_ids}"


def test_task_file_naming_and_sections() -> None:
    files = _task_files()
    assert files, "tasks/ 下没有任何任务档案"

    for path in files:
        assert FILE_RE.match(path.name), f"任务文件名不符合 TASKnnn-slug.md (slug 为英文小写连字符): {path.name}"
        text = path.read_text(encoding="utf-8")
        assert STATUS_RE.search(text), f"{path.name} 缺少合法的 `**Status:**` 行"
        for section in REQUIRED_SECTIONS:
            assert section in text, f"{path.name} 缺少必备章节 `{section}`"


def test_task_status_matches_index_section() -> None:
    sections = _indexed_sections()
    for path in _task_files():
        task_id = path.name[:7]
        match = STATUS_RE.search(path.read_text(encoding="utf-8"))
        assert match, f"{path.name} 缺少 `**Status:**`"
        assert sections[task_id] == match.group(1), (
            f"{task_id} 档案 Status={match.group(1)} 与索引分区 "
            f"`## {sections[task_id]}` 不一致"
        )


def test_index_has_all_status_sections() -> None:
    text = INDEX.read_text(encoding="utf-8")
    for status in STATUSES:
        assert f"## {status}" in text, f"_index.md 缺少状态分区 `## {status}`"


def test_active_context_has_no_rolled_up_session_log() -> None:
    text = (MB / "activeContext.md").read_text(encoding="utf-8")
    leaked = [line[:60] for line in text.splitlines() if re.match(r"^- 2026-\d\d-\d\d:", line)]

    assert not leaked, f"activeContext.md 出现流水账纪要行 (应迁入 tasks/ 档案对应专题): {leaked}"


def test_session_protocol_is_exposed_in_always_on_entries() -> None:
    assert SKILL.exists(), "缺少 skill 载体 .agents/skills/memory-bank/SKILL.md (会话协议将无法被触发)"
    skill_text = SKILL.read_text(encoding="utf-8")
    for token in ("立档阈值", "收尾 DoD", "会话开始"):
        assert token in skill_text, f"SKILL.md 缺少 {token}"

    for entry in (ROOT / "AGENTS.md", ROOT / ".github" / "copilot-instructions.md"):
        text = entry.read_text(encoding="utf-8")
        assert "立档阈值" in text, f"{entry.name} 未声明立档阈值"
        assert ".agents/skills/memory-bank/SKILL.md" in text, f"{entry.name} 未指向 memory-bank skill"
