#!/usr/bin/env python3
"""`kb.new` —— 按族注册表新建文档制品 (计划 memory-bank/plans/26-10-17-0527 P1)。

设计轴: **一次逻辑动作 = 一条命令 + 一次填空, 一切派生面零手写** —— 时间戳(timekit 单点)、
文件名(含查重)、头部字段全量、HTML 族 dark CSS、骨架段落 + SLOT 标记、建后重建该族索引,
全部由本命令派生; agent 只剩「替换 SLOT 标记」一次编辑。

族注册表(`_common.FAMILIES`)是命名 / 模板 / 词表 / 索引动作的**单点**: 本命令与
`check_doc_templates`(守卫) import 同一份, 不造第二套规范。

判据与边界 (计划 §03 / §05):
- 目标文件已存在即 rc=1 拒绝 (幂等); 档案族撞名 = 同专题已存在, 提示「追加不新建」并给路径
  (同 clone 按 slug 忽略日期前缀比对 + 跨 clone `../auto-qb-*/memory-bank/tasks/` 只读 ls)
- `--refs` **D4 反向认领自动补链 (P2 交付)**: 目标件**自动补/并** `doc-refs` meta (HTML) 或
  `**Refs:**` 行 (md) —— 只动元数据行, 合并为英文逗号列表, 幂等; 杀「单向链闸门红」整类问题。
  目标必须存在且在 memory-bank 内 (fail-fast; 生成物 `_` 前缀文件不作目标)
- `slice` 族不由本命令建 (拍板: 切片统一由 `kb.wrap` 收尾处理) —— 传了即拒绝并指路
- 建后末尾固定输出「剩余人工 N 项(判断 a · 条件 b · **机械 0**)」契约 (§5.4 收录断言)

用法 (从仓库根; `<skill-dir>` = 加载 memory-bank skill 时它实际所在的目录):
    python <skill-dir>/scripts/new_doc.py plan --title ".." --topic <kebab> [--refs p1,p2]
    python <skill-dir>/scripts/new_doc.py task --title ".." --topic <领域>-<专题> [--refs p1,p2]
    python <skill-dir>/scripts/new_doc.py --root <dir> --mb-dir <dir> plan ...   # 覆盖探测
退出码: 0 成功 / 1 拒绝或校验失败 (原因与下一步打在输出里)
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import timekit  # noqa: E402  (时间单点: UTC+8 naive 墙钟, 与 kb.time 同源)
from _common import (  # noqa: E402
    FAMILIES,
    SKILL_DIR,
    SLOT_RE,
    TASK_DOMAINS,
    StatusVocabularyError,
    find_root,
    html_meta,
    html_set_refs,
    match_domain,
    md_field,
    md_set_refs,
    rebuild_index,
    rel_posix,
    resolve_doc_path,
    resolve_mb_dir,
    split_refs,
)

SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
TASK_DATE_PREFIX_RE = re.compile(r"^\d{2}-\d{2}-\d{2}-")


def _fail(msg: str) -> int:
    sys.stderr.write(f"[STOP] {msg}\n")
    return 1


def _utf8_stdout() -> None:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")


def _html_escape(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _sibling_tasks_dirs(root: Path) -> list[Path]:
    """跨 clone 的 tasks/ 目录 (`../auto-qb-*/memory-bank/tasks/`, 只读 ls; 排除自己)。"""
    out: list[Path] = []
    try:
        siblings = sorted(root.parent.glob("auto-qb-*"))
    except OSError:
        return out
    for sib in siblings:
        if sib.resolve() == root.resolve():
            continue
        tasks = sib / "memory-bank" / "tasks"
        if tasks.is_dir():
            out.append(tasks)
    return out


def _check_duplicate(topic: str, mb: Path, root: Path) -> str | None:
    """档案族查重: 本 clone + 跨 clone 按 slug(忽略日期前缀)比对。命中返回拒绝原因。"""
    hits: list[str] = []
    for tasks_dir in [mb / "tasks", *_sibling_tasks_dirs(root)]:
        for path in sorted(tasks_dir.glob("*.md")):
            if path.name.startswith("_"):
                continue
            if TASK_DATE_PREFIX_RE.sub("", path.stem) == topic:
                hits.append(path.as_posix())
    if hits:
        where = hits[0]
        more = f" 等 {len(hits)} 处" if len(hits) > 1 else ""
        return (f"同专题档案已存在: {where}{more} —— 追加不新建; "
                "续作请直接编辑该档案 (收尾的进度日志行由 kb.wrap 追加)")
    return None


def _render(spec, values: dict[str, str]) -> str:
    text = (SKILL_DIR / "templates" / spec.template).read_text(encoding="utf-8")
    for key, value in values.items():
        text = text.replace(f"@@{key}@@", value)
    return text


def _resolve_refs(raw: str, root: Path, mb: Path) -> tuple[list[str], list[Path]] | str:
    """`--refs` 解析 (D4): 目标必须存在、在 memory-bank 内、不是生成物 (`_` 前缀)。

    返回 (规范化仓库根相对 refs, 目标路径); 失败返回错误消息字符串 (调用方 rc=1)。
    接受绝对 / 仓库根相对 / mb 相对三形态 (docmap 输出 mb 相对, 照抄最自然)。
    """
    refs: list[str] = []
    targets: list[Path] = []
    for raw_ref in split_refs(raw):
        path = resolve_doc_path(raw_ref, root, mb)
        if not path.is_file():
            return f"refs 目标不存在: {raw_ref} (三形态都不命中) —— 先建好目标件再建本件"
        try:
            path.resolve().relative_to(mb.resolve())
        except ValueError:
            return f"refs 目标不在 memory-bank 下: {raw_ref} —— 认领链只串库内件"
        if path.name.startswith("_"):
            return f"refs 目标不能是生成物 (`_` 前缀的索引/about): {raw_ref}"
        rel = rel_posix(path, root)
        if rel not in refs:
            refs.append(rel)
            targets.append(path)
    return refs, targets


def _chain_refs(rendered: str, refs: list[str], ext: str) -> str:
    """本件自己的正向声明: HTML 写 `doc-refs` meta, md 写 `**Refs:**` 行 (只动元数据行)。"""
    set_refs = html_set_refs if ext == ".html" else md_set_refs
    for rel in refs:
        rendered = set_refs(rendered, rel)
    return rendered


def _reverse_chain(targets: list[Path], self_rel: str, root: Path) -> list[str]:
    """D4 反向补链: 在目标件补/并对本件的反向声明 (只动元数据行, 幂等)。

    返回每份目标的处置说明 (新插入 / 已合并 / 已声明幂等)。I/O 失败抛给调用方 —— 本件已建,
    链断了必须让人知道 (gen_doc_map --check 会红), 处置: 手工补那一条反向行。
    """
    lines: list[str] = []
    for target in targets:
        text = target.read_text(encoding="utf-8")
        is_html = target.suffix == ".html"
        new_text = html_set_refs(text, self_rel) if is_html else md_set_refs(text, self_rel)
        if new_text == text:
            how = "已声明 (幂等)"
        else:
            value = html_meta(new_text, "doc-refs") if is_html else md_field(new_text, "Refs")
            total = len(split_refs(value or ""))
            how = f"反向声明已并入 (共 {total} 条)" if total > 1 else "新插入反向声明"
            target.write_text(new_text, encoding="utf-8", newline="\n")
        lines.append(f"{rel_posix(target, root)} ({how})")
    return lines


def _rebuild_index(spec, root: Path, mb: Path) -> list[Path]:
    """建后重建**该族受影响的那份索引** —— 单点 `_common.rebuild_index` (kb.status / kb.bump 共用)。"""
    return rebuild_index(root, mb, spec.index_script)


def _print_remaining(family: str, slots: list[str]) -> None:
    """§5.4 输出契约: 三分类清单 + 「机械 0」收录断言。"""
    slot_text = " / ".join(slots) if slots else "(无)"
    if family == "plan":
        print("剩余人工 2 项(判断 1 · 条件 1 · 机械 0)")
        print(f"【判断】SLOT: {slot_text} (一次编辑填完)")
        print('【条件】立档阈值命中 → commands run kb.new task --title ".." --topic <领域>-<专题>')
    else:  # task
        print("剩余人工 1 项(判断 1 · 条件 0 · 机械 0)")
        print(f"【判断】SLOT: {slot_text} (一次编辑填完; Summary 已由 --title 预填, 可精修)")


def main(argv: list[str] | None = None) -> int:
    _utf8_stdout()
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("family", choices=sorted(FAMILIES), help="文档族 (plan / task; slice 走 kb.wrap)")
    parser.add_argument("--title", required=True, help="制品标题 (档案族的 Summary 预填, 裁定 A1)")
    parser.add_argument("--topic", required=True, help="专题主键: plan=kebab; task=<领域>-<专题>")
    parser.add_argument(
        "--refs",
        default="",
        help="引用目标 (英文逗号分隔; 绝对/仓库根相对/mb 相对三形态) —— D4 自动双向补链: "
        "本件写 doc-refs / **Refs:**, 目标件反向声明本件 (只动元数据行, 幂等)"
    )
    parser.add_argument("--root", help="仓库根 (默认向上找 .git)")
    parser.add_argument("--mb-dir", help="memory-bank 目录 (默认 <root>/memory-bank)")
    args = parser.parse_args(argv)

    family = args.family
    spec = FAMILIES[family]

    if family == "slice":
        return _fail(
            "slice 族不由 kb.new 建 (拍板: 切片统一由 kb.wrap 收尾处理) —— "
            '用 commands run kb.wrap --topic <slug> --did ".." (不存在则按模板建, 存在则抬最后活动)'
        )

    root = Path(args.root).resolve() if args.root else find_root()
    mb = resolve_mb_dir(root, args.mb_dir)

    # --- 取时 (timekit 单点) 与命名校验 (fail-fast: 之后假定命名合法)
    moment = timekit.now()
    if not SLUG_RE.match(args.topic):
        return _fail(f"--topic 必须是 kebab (小写英文数字 + 短横线): {args.topic!r}")
    if family == "plan":
        filename = f"{moment.strftime('%y-%m-%d-%H%M')}-plan-{args.topic}.html"
        values = {
            "TITLE": _html_escape(args.title),
            "TOPIC": _html_escape(args.topic),
            "STAMP": moment.strftime("%y-%m-%d-%H%M"),
        }
    else:  # task
        # 领域段 = 最长前缀匹配 (`_common.match_domain` 单点): 枚举含短横线项
        # (`memory-bank`), 首段切分会让它永远不可达 (P1 缺陷, P2 补)
        domain = match_domain(args.topic)
        if domain is None:
            return _fail(f"--topic 首段必须是领域枚举之一 ({', '.join(TASK_DOMAINS)}): 现为 {args.topic.split('-', 1)[0]!r}")
        filename = f"{moment.strftime('%y-%m-%d')}-{args.topic}.md"
        values = {
            "STEM": Path(filename).stem,
            "TITLE": args.title,
            "DATE": moment.strftime("%Y-%m-%d"),
            "TOPIC": args.topic,
        }

    target = mb / spec.dir / filename
    if target.exists():
        return _fail(f"目标文件已存在: {rel_posix(target, root)} —— 幂等拒绝; 改版请直接编辑该文件")

    if family == "task":
        dup = _check_duplicate(args.topic, mb, root)
        if dup:
            return _fail(dup)

    # --- D4 反向认领: 先解析 refs (fail-fast, 不落半文件), 本件正向声明写进渲染结果
    ref_targets: list[Path] = []
    if args.refs:
        resolved = _resolve_refs(args.refs, root, mb)
        if isinstance(resolved, str):
            return _fail(resolved)
        refs, ref_targets = resolved

    # --- 渲染后一次落盘 (渲染失败即停, 不落半文件)
    try:
        rendered = _render(spec, values)
    except OSError as exc:
        return _fail(f"读模板失败: {exc}")
    if ref_targets:
        rendered = _chain_refs(rendered, refs, spec.ext)

    slots = [s.strip() for s in SLOT_RE.findall(rendered)]
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(rendered, encoding="utf-8", newline="\n")

    print(f"已建 {rel_posix(target, root)} ({len(slots)} 处 SLOT 待填)")

    # --- D4 反向补链: 目标件补/并对本件的反向声明 (只动元数据行, 幂等)
    if ref_targets:
        chained = _reverse_chain(ref_targets, rel_posix(target, root), root)
        for line in chained:
            print(f"已双向补链 {line}")

    # --- 建后重建该族索引 (与 kb.index 同一 build 实现)
    try:
        rebuilt = _rebuild_index(spec, root, mb)
    except StatusVocabularyError as exc:
        sys.stderr.write(f"[STOP] 文件已建, 但索引重建失败 (词表问题必须先修): {exc}\n"
                         "处置后运行 commands run kb.index 重建索引\n")
        return 1
    if rebuilt:
        print("已重建索引: " + ", ".join(rel_posix(p, root) for p in rebuilt))

    print()
    _print_remaining(family, slots)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
