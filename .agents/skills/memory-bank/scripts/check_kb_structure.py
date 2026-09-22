"""memory-bank 结构检查: cap 策略 / 元数据 / 双向一致 / 无孤儿 / 存根 / 条目字段。

供 `tests/test_memory_bank.py` 的守卫**在进程内 import** (本项目测试禁止起子进程, `tests/sidefx.py`
的 POPEN 记账会判越界), 与 `gen_tasks_index.py` 现做法一致。cap 与类枚举常量单点定义在
`_common.py`, 守卫 import 它, 不手抄。

用法(从仓库根; `<skill-dir>` = 加载 memory-bank skill 时它实际所在的目录):
    python <skill-dir>/scripts/check_kb_structure.py            默认角色集
    python <skill-dir>/scripts/check_kb_structure.py --all      全角色 (含易变层与任务档案)
    python <skill-dir>/scripts/check_kb_structure.py --roles index,pitfall

每条检查返回**问题清单** (空 = 通过), 便于守卫逐条断言、也便于 CLI 汇总打印。
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import gen_kb_index  # noqa: E402
from _common import (  # noqa: E402
    ABOUT_NAME,
    CAP_MIN_WARN,
    CAP_POLICY,
    EXCLUDED_DIRS,
    INDEX_NAME,
    PITFALL_CLASSES,
    REQUIRED_FIELDS,
    STUB_CANDIDATES,
    STUB_CAP,
    STUB_MARK,
    TOPIC_FILE_RE,
    char_count,
    find_root,
    is_topic_file,
    iter_index_files,
    iter_indexed_dirs,
    iter_topic_files,
    read_meta,
    rel_posix,
    resolve_mb_dir,
    role_of,
    split_pitfall_entries,
)

# 默认参与 cap 检查的角色 (易变层与任务档案在迁移完成后才纳入 —— 见 `--all`)
DEFAULT_ROLES = ("index", "index-auto", "pitfall", "evergreen", "reference", "log", "agents")
ALL_ROLES = DEFAULT_ROLES + ("volatile", "task")

LINK_RE = re.compile(r"\[[^\]]*\]\(([^)]+)\)")


def _mb_rel(root: Path, path: Path) -> str:
    return rel_posix(path, root)


# --------------------------------------------------------------------------- 1 索引是生成物


def check_index_regenerated(root: Path, mb: Path) -> list[str]:
    """每个索引目录的 `_index.md` == 生成结果 (索引是生成物, 漂移由重跑解决, 不手改)。"""
    problems: list[str] = []
    for directory in iter_indexed_dirs(mb):
        index = directory / INDEX_NAME
        rendered = gen_kb_index.render_dir(directory, root, mb)
        current = index.read_text(encoding="utf-8") if index.exists() else ""
        if current != rendered:
            problems.append(f"{_mb_rel(root, index)} 与生成结果不一致 (跑 gen_kb_index.py 重建, 不要手改)")
    return problems


# --------------------------------------------------------------------------- 2 双向一致


def check_bijection(root: Path, mb: Path) -> list[str]:
    """索引 ↔ 目录内容双向一致: 有文件没登记、登记了没文件, 都算问题。"""
    problems: list[str] = []
    for directory in iter_indexed_dirs(mb):
        index = directory / INDEX_NAME
        if not index.exists():
            problems.append(f"{_mb_rel(root, index)} 缺失")
            continue
        text = index.read_text(encoding="utf-8")
        targets = LINK_RE.findall(text)

        # 同目录主题文件 (链接里不带 `/`)
        referenced = {t for t in targets if "/" not in t and t.endswith(".md")}
        on_disk = {p.name for p in iter_topic_files(directory)}
        for name in sorted(on_disk - referenced):
            problems.append(f"{_mb_rel(root, index)} 未登记主题文件 {name}")
        for name in sorted(referenced - on_disk):
            problems.append(f"{_mb_rel(root, index)} 登记了不存在的主题文件 {name}")

        # 子目录类指针 (链接形如 `<class>/_index.md`)
        ref_classes = {t.split("/", 1)[0] for t in targets if t.endswith(f"/{INDEX_NAME}")}
        disk_classes = {d.name for d in directory.iterdir() if d.is_dir() and (d / ABOUT_NAME).is_file()}
        for name in sorted(disk_classes - ref_classes):
            problems.append(f"{_mb_rel(root, index)} 未登记类目录 {name}/")
        for name in sorted(ref_classes - disk_classes):
            problems.append(f"{_mb_rel(root, index)} 登记了不存在的类目录 {name}/")
    return problems


# --------------------------------------------------------------------------- 3 头部元数据


def check_metadata(root: Path, mb: Path) -> list[str]:
    """每个主题文件与 `_about.md` 都含三行头元数据 (`# 标题` / `> 摘要:` / `> 触发:`)。"""
    problems: list[str] = []
    for directory in iter_indexed_dirs(mb):
        about = directory / ABOUT_NAME
        if not read_meta(about).complete:
            problems.append(f"{_mb_rel(root, about)} 元数据不全 (需要 `# 标题` / `> 摘要:` / `> 触发:`)")
        for path in iter_topic_files(directory):
            if not read_meta(path).complete:
                problems.append(f"{_mb_rel(root, path)} 元数据不全 (需要 `# 标题` / `> 摘要:` / `> 触发:`)")
    return problems


# --------------------------------------------------------------------------- 4 cap


def _cap_candidates(root: Path, mb: Path, roles: tuple[str, ...]) -> list[Path]:
    files: list[Path] = []
    if (mb / "README.md").is_file():
        files.append(mb / "README.md")
    files.extend(iter_index_files(mb))
    for directory in iter_indexed_dirs(mb):
        files.append(directory / ABOUT_NAME)
        files.extend(iter_topic_files(directory))
    if (root / "AGENTS.md").is_file():
        files.append(root / "AGENTS.md")
    if "volatile" in roles and (mb / "activeContext.md").is_file():
        files.append(mb / "activeContext.md")
    if "task" in roles:
        files.extend(p for p in sorted((mb / "tasks").glob("*.md")) if not p.name.startswith("_"))
    return sorted(set(files))


def check_caps(root: Path, mb: Path, roles: tuple[str, ...] = DEFAULT_ROLES) -> tuple[list[str], list[str]]:
    """每个文件 ≤ 其角色的 cap。返回 (问题, 警告) —— 下限只 WARN, 不算问题。"""
    problems: list[str] = []
    warns: list[str] = []
    for path in _cap_candidates(root, mb, roles):
        rel = _mb_rel(root, path)
        role = __import__("_common").role_of(rel)
        if role not in roles:
            continue
        size = char_count(path)
        cap = CAP_POLICY[role]
        if size > cap:
            problems.append(f"{rel} 超 cap: {size:,} > {cap:,} 字符 (角色 {role})")
        elif is_topic_file(path) and size < CAP_MIN_WARN:
            warns.append(f"{rel} 过小: {size:,} < {CAP_MIN_WARN:,} 字符 —— 考虑并入邻文件")
    return problems, warns


# --------------------------------------------------------------------------- 5 类名与文件名


def check_names(root: Path, mb: Path) -> list[str]:
    """类名 ∈ 固定枚举; 主题文件名匹配 `^[a-z0-9]+(-[a-z0-9]+)*\\.md$`。"""
    problems: list[str] = []
    for directory in iter_indexed_dirs(mb):
        for path in iter_topic_files(directory):
            if not TOPIC_FILE_RE.match(path.name):
                problems.append(f"{_mb_rel(root, path)} 文件名不合规 (小写英文数字 + 短横线, 如 `push.md`)")
    pitfalls = mb / "pitfalls"
    if pitfalls.is_dir():
        for sub in sorted(pitfalls.iterdir()):
            if sub.is_dir() and (sub / ABOUT_NAME).is_file() and sub.name not in PITFALL_CLASSES:
                problems.append(
                    f"{_mb_rel(root, sub)}/ 不是合法类名 (枚举: {', '.join(PITFALL_CLASSES)});"
                    " 扩类须同步 `_common.PITFALL_CLASSES` 与 memory-bank/README.md"
                )
    return problems


# --------------------------------------------------------------------------- 6 无孤儿索引


def check_orphan_indexes(root: Path, mb: Path) -> list[str]:
    """每个**顶层** `_index.md` 都被 memory-bank/README.md 引用 (新增目录忘了登记就红)。

    嵌套索引由父索引引用 —— 那是生成物的职责, 已由第 2 条双向一致守住。
    """
    problems: list[str] = []
    readme = mb / "README.md"
    if not readme.is_file():
        return [f"{_mb_rel(root, readme)} 缺失 (库内细路由单点)"]
    text = readme.read_text(encoding="utf-8")
    for index in iter_index_files(mb):
        rel_dir = index.parent.relative_to(mb)
        if len(rel_dir.parts) != 1:
            continue  # 只查顶层
        rel = rel_posix(index, mb)
        if rel not in text:
            problems.append(f"{_mb_rel(root, index)} 未被 memory-bank/README.md 引用 (孤儿目录)")
    return problems


# --------------------------------------------------------------------------- 7 存根


def is_stub(path: Path) -> tuple[bool, str]:
    """存根判据: ≤1 KB + 含「已迁至」+ 不含正文 (无 `##` 标题、无列表条目)。"""
    text = path.read_bytes().decode("utf-8")
    size = len(text)
    if size > STUB_CAP:
        return False, f"{size:,} > {STUB_CAP:,} 字符 (存根必须 ≤1 KB)"
    if STUB_MARK not in text:
        return False, f"缺「{STUB_MARK}」标记"
    if re.search(r"^##\s", text, re.MULTILINE):
        return False, "仍含 `##` 标题 (正文未迁走)"
    if re.search(r"^\s*[-*]\s+\S", text, re.MULTILINE):
        return False, "仍含列表条目 (正文未迁走)"
    return True, ""


def check_stubs(root: Path, mb: Path) -> list[str]:
    """被拆文档的原路径必须是合法存根 (目录已建 = 该文档已迁走)。"""
    problems: list[str] = []
    for name in STUB_CANDIDATES:
        stub = mb / name
        if not (mb / stub.stem).is_dir():
            continue  # 该波尚未落地
        if not stub.is_file():
            problems.append(f"{_mb_rel(root, stub)} 缺失 —— 目录已建但存根不在, 400+ 处历史引用会断")
            continue
        ok, why = is_stub(stub)
        if not ok:
            problems.append(f"{_mb_rel(root, stub)} 不是合法存根: {why}")
    return problems


# --------------------------------------------------------------------------- 8 易变层硬顶


def check_active_context_cap(root: Path, mb: Path) -> list[str]:
    """`activeContext.md` ≤12 KB —— 超了就是内容该外迁的信号, 不是「这次先写着」。"""
    path = mb / "activeContext.md"
    if not path.is_file():
        return [f"{_mb_rel(root, path)} 缺失"]
    size = char_count(path)
    cap = CAP_POLICY["volatile"]
    if size > cap:
        return [f"{_mb_rel(root, path)} 超 cap: {size:,} > {cap:,} 字符 (易变层硬顶)"]
    return []


# --------------------------------------------------------------------------- 9 条目字段


def check_pitfall_entries(root: Path, mb: Path) -> list[str]:
    """pitfalls 条目含 触发 / 判别 / 处置 三必填字段 (`- **触发**: …`)。"""
    problems: list[str] = []
    pitfalls = mb / "pitfalls"
    if not pitfalls.is_dir():
        return problems
    for path in sorted(pitfalls.rglob("*.md")):
        if not is_topic_file(path):
            continue
        text = path.read_bytes().decode("utf-8")
        for title, block in split_pitfall_entries(text):
            missing = [f for f in REQUIRED_FIELDS if f"**{f}**" not in block]
            if missing:
                problems.append(f"{_mb_rel(root, path)} 条目「{title}」缺字段: {' / '.join(missing)}")
    return problems


# --------------------------------------------------------------------------- 汇总


def run_all(root: Path, mb: Path, roles: tuple[str, ...] = DEFAULT_ROLES) -> dict[str, list[str]]:
    """跑全部检查, 返回 {检查名: 问题清单}。"""
    cap_problems, _warns = check_caps(root, mb, roles)
    return {
        "索引是生成物": check_index_regenerated(root, mb),
        "索引双向一致": check_bijection(root, mb),
        "头部元数据": check_metadata(root, mb),
        "cap 策略": cap_problems,
        "类名与文件名": check_names(root, mb),
        "无孤儿索引": check_orphan_indexes(root, mb),
        "存根合法": check_stubs(root, mb),
        "易变层硬顶": check_active_context_cap(root, mb) if "volatile" in roles else [],
        "条目三字段": check_pitfall_entries(root, mb),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--all", action="store_true", help="全角色 (含易变层与任务档案)")
    parser.add_argument("--roles", help="逗号分隔的角色集, 覆盖默认")
    parser.add_argument("--quiet", action="store_true", help="只打印不通过项")
    parser.add_argument("--root", help="仓库根 (默认向上找 .git)")
    parser.add_argument("--mb-dir", help="memory-bank 目录 (默认 <root>/memory-bank)")
    args = parser.parse_args()

    root = Path(args.root).resolve() if args.root else find_root()
    mb = resolve_mb_dir(root, args.mb_dir)
    if not mb.is_dir():
        sys.stderr.write(f"memory-bank 目录不存在: {mb}\n")
        return 2

    if args.roles:
        roles = tuple(r.strip() for r in args.roles.split(",") if r.strip())
    else:
        roles = ALL_ROLES if args.all else DEFAULT_ROLES

    results = run_all(root, mb, roles)
    _, warns = check_caps(root, mb, roles)
    total = sum(len(v) for v in results.values())

    print(f"memory-bank 结构检查 (角色: {', '.join(roles)})\n")
    for name, problems in results.items():
        if problems:
            print(f"  [FAIL] {name} — {len(problems)} 项")
            for line in problems:
                print(f"         · {line}")
        elif not args.quiet:
            print(f"  [ OK ] {name}")
    for line in warns:
        if not args.quiet:
            print(f"  [WARN] {line}")
    print(f"\n共 {total} 项不通过。" if total else "\n全部通过。")
    return 1 if total else 0


if __name__ == "__main__":
    raise SystemExit(main())
