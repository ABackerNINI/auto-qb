"""Memory Bank 结构守卫测试 (TASK010; 2026-09-18 随任务档案改名同步更新)。

守什么: 知识库的"跨会话连续性"完全依赖 `memory-bank/tasks/` 与入口文件的**结构化约定** —
一旦索引与档案脱钩 (登记了没文件 / 有文件没登记)、状态分区与档案 `Status` 不一致、
必备章节缺失, 下次会话就无法从 `tasks/` 续作; 一旦会话纪要回流进 `activeContext.md`,
该文件会重新膨胀成流水账 (2026-09-17 复盘的真实故障)。这些判定都是纯静态的, 用测试守住成本极低。

2026-09-18 起档案命名由 `TASKnnn-<slug>.md` 改为 `YY-MM-DD-<slug>.md`(全局序号在 9 个并行
worktree 下必然撞号)。本文件在兼容期内同时接受两种命名, 主键一律取"去掉编号 / 日期前缀后的 slug"。

## 测试计划

- test_tasks_index_and_files_are_bijective: `_index.md` 登记的键与 `tasks/*.md` 文件双向一致
- test_slug_is_unique_ignoring_date_prefix: 去掉日期 / 编号前缀后 slug 唯一 + 索引同键只登记一次 (防并行分支同专题两份档案)
- test_task_file_naming_and_sections: 文件名符合 `YY-MM-DD-<slug>.md`(兼容旧 `TASKnnn-<slug>.md`), 且五个必备章节齐全
- test_task_status_matches_index_section: 档案 `**Status:**` 与索引所在分区一致
- test_index_has_all_status_sections: 索引保留四个状态分区标题
- test_index_is_regenerated: `_index.md` == `scripts/gen_tasks_index.py` 的生成结果
- test_active_context_has_no_rolled_up_session_log: `activeContext.md` 不出现 `^- 2026-` 流水账纪要行
- test_session_protocol_is_exposed_in_always_on_entries: skill 载体存在且含阈值/DoD, AGENTS 与 copilot-instructions 均声明阈值并指向 skill
"""

from __future__ import annotations

import importlib.util
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MB = ROOT / "memory-bank"
TASKS = MB / "tasks"
INDEX = TASKS / "_index.md"
GEN = ROOT / "scripts" / "gen_tasks_index.py"
SKILL = ROOT / ".agents" / "skills" / "memory-bank" / "SKILL.md"

STATUSES = ("In Progress", "Pending", "Completed", "Abandoned")
REQUIRED_SECTIONS = ("## 原始请求", "## 思考过程与决策", "## 实现计划", "## 子任务状态表", "## 进度日志")

DATE_PREFIX_RE = re.compile(r"^\d{2}-\d{2}-\d{2}-")
LEGACY_PREFIX_RE = re.compile(r"^TASK\d{3}-")
FILE_RE = re.compile(r"^(?:TASK\d{3}-|\d{2}-\d{2}-\d{2}-)[a-z0-9]+(?:-[a-z0-9]+)*\.md$")
INDEX_ID_RE = re.compile(r"- \[(TASK\d{3}|\d{2}-\d{2}-\d{2}-[a-z0-9]+(?:-[a-z0-9]+)*)\]")
STATUS_RE = re.compile(r"\*\*Status:\*\* (In Progress|Pending|Completed|Abandoned)")


def _task_files() -> list[Path]:
    return sorted(p for p in TASKS.glob("*.md") if not p.name.startswith("_"))


def _slug_of(path: Path) -> str:
    """去掉编号前缀 (`TASKnnn-`) 或日期前缀 (`YY-MM-DD-`) 后的专题 slug。"""
    stem = path.stem
    stem = LEGACY_PREFIX_RE.sub("", stem)
    return DATE_PREFIX_RE.sub("", stem)


def _indexed_sections() -> dict[str, str]:
    sections: dict[str, str] = {}
    current = ""
    for line in INDEX.read_text(encoding="utf-8").splitlines():
        if line.startswith("## "):
            current = line[3:].strip()
            continue
        for key in INDEX_ID_RE.findall(line):
            sections[key] = current
    return sections


def test_tasks_index_and_files_are_bijective() -> None:
    indexed = set(_indexed_sections())
    on_disk = {path.stem for path in _task_files()}

    assert indexed == on_disk, (f"索引与档案文件不一致: 仅索引登记={sorted(indexed - on_disk)}, "
                                f"仅有文件={sorted(on_disk - indexed)}")


def test_slug_is_unique_ignoring_date_prefix() -> None:
    """并行 worktree 各自立档会产出重复: 同一专题两份档案 (2026-09-18 实测 TASK014/TASK015 逐字节相同)
    + 索引里重复登记。重复条目在 dict 式解析里会静默覆盖, 双向一致与状态分区两个守卫都发现不了,
    所以必须单独守。改名后同一专题在不同日期建档会产生不同文件名, 因此比对必须**忽略日期前缀**。"""
    slugs: dict[str, list[str]] = {}
    for path in _task_files():
        slugs.setdefault(_slug_of(path), []).append(path.name)
    dup_slugs = {slug: names for slug, names in slugs.items() if len(names) > 1}

    assert not dup_slugs, f"存在同 slug 的重复任务档案 (同一专题两份, 需合并): {dup_slugs}"

    indexed = INDEX_ID_RE.findall(INDEX.read_text(encoding="utf-8"))
    dup_ids = sorted({key for key in indexed if indexed.count(key) > 1})

    assert not dup_ids, f"索引中同一档案被重复登记: {dup_ids}"


def test_task_file_naming_and_sections() -> None:
    files = _task_files()
    assert files, "tasks/ 下没有任何任务档案"

    for path in files:
        assert FILE_RE.match(path.name), (
            f"任务文件名不符合 YY-MM-DD-<slug>.md (slug 为英文小写连字符): {path.name}")
        text = path.read_text(encoding="utf-8")
        assert STATUS_RE.search(text), f"{path.name} 缺少合法的 `**Status:**` 行"
        for section in REQUIRED_SECTIONS:
            assert section in text, f"{path.name} 缺少必备章节 `{section}`"


def test_task_status_matches_index_section() -> None:
    sections = _indexed_sections()
    for path in _task_files():
        match = STATUS_RE.search(path.read_text(encoding="utf-8"))
        assert match, f"{path.name} 缺少 `**Status:**`"
        assert sections[path.stem] == match.group(1), (
            f"{path.name} 档案 Status={match.group(1)} 与索引分区 "
            f"`## {sections[path.stem]}` 不一致"
        )


def test_index_has_all_status_sections() -> None:
    text = INDEX.read_text(encoding="utf-8")
    for status in STATUSES:
        assert f"## {status}" in text, f"_index.md 缺少状态分区 `## {status}`"


def test_index_is_regenerated() -> None:
    """`_index.md` 是生成物: 冲突不再靠人工合并, 而是"任一方重跑一次脚本"。
    本守卫保证磁盘上的索引确实是脚本产物, 而不是有人手改过。

    **不跑子进程**: 本项目测试禁止启动外部进程 (`tests/sidefx.py` 的 POPEN 记账会判越界),
    所以这里在进程内 import 生成器并比对渲染结果, 语义与 `--check` 一致。
    """
    assert GEN.exists(), "缺少 scripts/gen_tasks_index.py (索引将无法重建)"
    spec = importlib.util.spec_from_file_location("gen_tasks_index", GEN)
    assert spec and spec.loader, "无法加载 scripts/gen_tasks_index.py"
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    rendered = module.render(module.collect())
    current = INDEX.read_text(encoding="utf-8")

    assert current == rendered, "请运行 `python scripts/gen_tasks_index.py` 重建索引"


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
