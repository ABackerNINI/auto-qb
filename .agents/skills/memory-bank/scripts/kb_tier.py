#!/usr/bin/env python3
"""`kb.tier` —— 知识库分级清理四动作 (计划 memory-bank/plans/26-10-31-0534 §03/§04 R0)。

四级生命周期 (计划 §3.1): L0 活跃(原样保留) / L1 降噪(删叙事不挪位置, 本命令不管) /
L2 外迁(整段搬 attachments/, 主档留指针) / L3 待删(观察期满, purge 三闸门)。
标记落点 (§3.2): 主题文件头部区第 4 行 `> 等级: L2`; 头部区 = 首个 `## ` 之前的行。
生成器只解析三行头的具名字段, 额外行不干扰索引生成 (已查证, 计划 §3.2)。

四动作:
- list --level L3       列出该等级全部文件 (行数/字符数); 未打标件单独呈现 (无 `> 等级:` 行 =
                        判据缺失, 不默认归任何级; list --level L0 全列, 其它级给一行汇总)。
                        扫描面 = pitfalls/<类>/ 主题文件 (R1/R2 的清理对象)。
- set <file> <level>    打标: 已有等级行原地改值; 没有则插为头部区第 4 行 (头部区不足 4 行
                        则插在头部区末尾)。只接受 L0/L1/L2/L3, 表外值 rc=1。
- migrate --level L2    整段叙事外迁: 首个正文行 (`## ` / `### `) 起到文件尾**逐字节原样**搬
                        pitfalls/<类>/attachments/<stem>-migrated-<stamp>.md, 主档留一行指针。
                        附件深度比主档深一层, 相对链接自动加一层 `../` 前缀 (唯一允许的字节差,
                        行数与 \\r\\n 计数必须与原文一致, 写完回读校验)。默认 dry-run。
- purge --level L3      删除该等级文件。默认 dry-run; 必须显式 --apply; 三道闸门任一不过
                        全体拒绝 (全或无, 删零个) 且 rc=1:
                        ①守阵齐全: 文件有非空 `守阵:` 行, 或头部区明确写「无需守阵」——
                          两个都没有 = 判据缺失, 不许删 (计划 §07 风险表)。
                        ②反向引用清零: 全仓文本文件 grep 文件名 (排除 .git / auto-qb-data /
                          本文件自身), 有任何引用即拒绝。
                        ③观察期人判项的机器标记: 头部区必须有一行 `> 观察通过: YYYY-MM-DD`
                          (本脚本定义的机器可读标记; 「跨越 2 轮零复发」是人判, 观察完成后
                          由人写进头部区, purge 只认标记不猜)。

用法 (从仓库根; `<skill-dir>` = 加载 memory-bank skill 时它实际所在的目录):
    python <skill-dir>/scripts/kb_tier.py list --level L2
    python <skill-dir>/scripts/kb_tier.py set memory-bank/pitfalls/git/sync-pull.md L2
    python <skill-dir>/scripts/kb_tier.py migrate --level L2 [--apply]
    python <skill-dir>/scripts/kb_tier.py purge --level L3 [--apply]
退出码: 0 成功 (dry-run 打印计划也算成功) / 1 拒绝或校验失败 (原因打在输出里)
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import timekit  # noqa: E402  (时间单点: UTC+8 naive 墙钟, 与 kb.status/kb.bump 同源)
from _common import (  # noqa: E402
    PITFALL_CLASSES, char_count, find_root, is_topic_file, rel_posix, resolve_mb_dir,
)

# 等级词表与标记行 (单点: set 写 / list·migrate·purge 读都走这两个常量)
LEVELS = ("L0", "L1", "L2", "L3")
TIER_LINE = "> 等级: {level}"
TIER_VALUE_RE = re.compile(r"^>\s*等级:\s*(L[0-3])\s*$")
# 观察期人判项的机器可读标记 (purge 闸门③; 定义单点在本 docstring 与 README)
OBS_PASS_RE = re.compile(r"^>\s*观察通过:\s*(\d{4}-\d{2}-\d{2})\s*$", re.MULTILINE)
# 守阵字段: `守阵:` 后同行有非空内容 (等价字段形态 `- **守阵**:` 也认)
GUARD_RE = re.compile(r"守阵[:：]\s*\S")
NO_GUARD_MARK = "无需守阵"  # 头部区明确判定「无需守阵」(计划 §07: 补齐守阵或明确判定)

# 附件命名: 沿用 pitfalls/web-ui/attachments/ 既有形态 (<stem>-<stamp>-<desc>.md 的变体,
# desc 放前面便于同专题多段外迁按名排序)
ATTACH_NAME = "{stem}-migrated-{stamp}.md"
POINTER_LINE = "> 已外迁: 叙事整段迁至 [{name}]({name}) (kb.tier migrate {stamp}; 判据单点见上方摘要)"

# 正文起点: 首个 `## ` / `### ` 行 (前者覆盖叙述型文档, 后者覆盖坑档条目)
BODY_START_RE = re.compile(r"^#{2,3}\s")

# markdown 相对链接: `](target)` 且 target 非 scheme 绝对 / 根相对 / 纯锚点 → 加一层 `../`
MD_LINK_RE = re.compile(r"\]\(([^)]+)\)")
SCHEME_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.-]*://")

# 反向引用扫描要跳过的目录 (.git 版本库本体; auto-qb-data 是红线运行时数据)
BACKREF_SKIP_DIRS = {".git", "auto-qb-data", "__pycache__", ".venv", "node_modules"}


def _fail(msg: str) -> int:
    sys.stderr.write(f"[STOP] {msg}\n")
    return 1


def _utf8_stdout() -> None:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")


def _read_lines(path: Path) -> list[str]:
    """按字节读入后按行切 (keepends) —— 不走 universal newlines, 行尾原样保留。"""
    return path.read_bytes().decode("utf-8").splitlines(keepends=True)


def _head_end(lines: list[str]) -> int:
    """头部区 = 首个 `## ` 之前的行 (计划 §3.2 的定义); 返回头部区结束下标。"""
    for i, ln in enumerate(lines):
        if ln.startswith("## "):
            return i
    return len(lines)


def _tier_of(lines: list[str], head_end: int) -> str | None:
    """头部区内的等级行值; 没有返回 None (未打标)。"""
    for ln in lines[:head_end]:
        m = TIER_VALUE_RE.match(ln.rstrip("\r\n"))
        if m:
            return m.group(1)
    return None


def _pitfall_files(mb: Path) -> list[Path]:
    """扫描面: pitfalls/<类>/ 的主题文件 (7 类; 附件与索引不在内)。"""
    out: list[Path] = []
    for cls in PITFALL_CLASSES:
        d = mb / "pitfalls" / cls
        if d.is_dir():
            out.extend(p for p in sorted(d.glob("*.md")) if is_topic_file(p))
    return out


def _pitfall_class(path: Path, mb: Path) -> str | None:
    """坑档所属类 (pitfalls/<类>/<file>); 不在该布局返回 None (migrate 拒绝)。"""
    try:
        parts = path.resolve().relative_to(mb.resolve()).as_posix().split("/")
    except ValueError:
        return None
    if len(parts) == 3 and parts[0] == "pitfalls" and parts[1] in PITFALL_CLASSES:
        return parts[1]
    return None


# --------------------------------------------------------------------------- list


def _cmd_list(mb: Path, root: Path, level: str) -> int:
    files = _pitfall_files(mb)
    marked: list[tuple[Path, str, int, int]] = []  # (path, level, lines, chars)
    unmarked: list[Path] = []
    for path in files:
        lines = _read_lines(path)
        tier = _tier_of(lines, _head_end(lines))
        if tier is None:
            unmarked.append(path)
        else:
            marked.append((path, tier, len(lines), char_count(path)))
    hits = [(p, n, c) for p, t, n, c in marked if t == level]
    print(f"等级 {level} (pitfalls 主题文件, 扫描 {len(files)} 件): {len(hits)} 件")
    for path, n, c in hits:
        print(f"  {rel_posix(path, root)}  {n} 行  {c:,} 字符")
    if level == "L0" and unmarked:
        print(f"未打标 (无 `> 等级:` 行 = 判据缺失, 不默认归任何级): {len(unmarked)} 件")
        for path in unmarked:
            print(f"  {rel_posix(path, root)}  待定 —— 用 `kb.tier set <file> <level>` 补标")
    elif unmarked:
        print(f"未打标 {len(unmarked)} 件 (不属本等级; `list --level L0` 查看明细)")
    return 0


# --------------------------------------------------------------------------- set


def _cmd_set(root: Path, mb: Path, raw: str, level: str) -> int:
    if level not in LEVELS:
        return _fail(f"等级 {level!r} 不在词表 ({'/'.join(LEVELS)}) —— 只认这四个值, 表外值一律拒绝")
    path = _resolve_md(raw, root, mb)
    if not path.is_file():
        return _fail(f"文件不存在: {raw} —— 路径三形态 (绝对/仓库根相对/mb 相对) 都不命中")
    try:
        rel = path.resolve().relative_to(mb.resolve()).as_posix()
    except ValueError:
        return _fail(f"{raw}: 不在 memory-bank 下 —— 分级只作用于知识库文档, 库外文件拒绝")
    if path.name.startswith("_") or "attachments" in rel.split("/"):
        return _fail(f"{rel}: 生成物 (_index/_about) 与 attachments/ 附件不打标 —— 拒绝")
    lines = _read_lines(path)
    head_end = _head_end(lines)
    tier_idx = next((i for i, ln in enumerate(lines[:head_end]) if TIER_VALUE_RE.match(ln.rstrip("\r\n"))), None)
    if tier_idx is not None:
        old = TIER_VALUE_RE.match(lines[tier_idx].rstrip("\r\n")).group(1)
        if old == level:
            print(f"{rel_posix(path, root)}: 等级已是 {level} —— 幂等, 无改动")
            return 0
        eol = "\r\n" if lines[tier_idx].endswith("\r\n") else "\n"
        lines[tier_idx] = TIER_LINE.format(level=level) + eol
        path.write_bytes("".join(lines).encode("utf-8"))
        print(f"已改值 {rel_posix(path, root)}: 等级 {old} → {level} (头部区原地改)")
        return 0
    # 没有等级行: 插为头部区第 4 行; 头部区不足 4 行则插在头部区末尾 (计划 §04 R0 表)
    eol = "\r\n" if (lines and lines[0].endswith("\r\n")) else "\n"
    pos = 3 if head_end >= 4 else head_end
    lines.insert(pos, TIER_LINE.format(level=level) + eol)
    path.write_bytes("".join(lines).encode("utf-8"))
    where = f"头部区第 {pos + 1} 行" if head_end >= 4 else "头部区末尾"
    print(f"已打标 {rel_posix(path, root)}: 等级 {level} (插入{where})")
    return 0


def _resolve_md(raw: str, root: Path, mb: Path) -> Path:
    """set 的路径三形态解析 (绝对 / 仓库根相对 / mb 相对), 同 flip_status 口径。"""
    cand = Path(raw)
    if cand.is_absolute():
        return cand.resolve()
    for base in (root, mb):
        probe = (base / cand).resolve()
        if probe.is_file():
            return probe
    return (root / cand).resolve()


# --------------------------------------------------------------------------- migrate


def _prefix_links(text: str) -> tuple[str, int]:
    """相对链接加一层 `../` 前缀 (附件深度 +1)。返回 (新文本, 改了几处)。

    只动 markdown 链接 `](target)` 的 target: scheme 绝对 / 根相对 / 纯锚点跳过,
    其余 (含已带 `../` 的) 一律再前缀一层 —— 搬深一层, 全部相对路径都要多退一级。
    """
    count = 0

    def repl(m: re.Match) -> str:
        nonlocal count
        target = m.group(1)
        if SCHEME_RE.match(target) or target.startswith(("/", "#")):
            return m.group(0)
        count += 1
        return f"](../{target})"

    return MD_LINK_RE.sub(repl, text), count


def _cmd_migrate(root: Path, mb: Path, level: str, apply: bool) -> int:
    if level not in LEVELS:
        return _fail(f"等级 {level!r} 不在词表 ({'/'.join(LEVELS)})")
    stamp = timekit.now().strftime("%y-%m-%d-%H%M")
    targets: list[tuple[Path, list[str], list[str], str]] = []  # (path, head, body, attach_name)
    for path in _pitfall_files(mb):
        lines = _read_lines(path)
        if _tier_of(lines, _head_end(lines)) != level:
            continue
        cls = _pitfall_class(path, mb)
        if cls is None:
            return _fail(f"{rel_posix(path, root)}: 不在 pitfalls/<类>/ 布局下, 不知道附件该放哪一类 —— 拒绝")
        body_start = next((i for i, ln in enumerate(lines) if BODY_START_RE.match(ln)), len(lines))
        if body_start >= len(lines):
            print(f"跳过 {rel_posix(path, root)}: 无正文段可迁 (整文件都是头部区)")
            continue
        name = ATTACH_NAME.format(stem=path.stem, stamp=stamp)
        targets.append((path, lines[:body_start], lines[body_start:], name))
    if not targets:
        print(f"等级 {level}: 没有可外迁的文件 (0 件)")
        return 0
    verb = "将外迁" if not apply else "已外迁"
    print(f"等级 {level}: {verb} {len(targets)} 件 (stamp {stamp})" + ("" if apply else " —— dry-run, 未写盘"))
    for path, head, body, name in targets:
        attach_rel = f"pitfalls/{_pitfall_class(path, mb)}/attachments/{name}"
        body_text = "".join(body)
        new_body, n_links = _prefix_links(body_text)
        print(f"  {rel_posix(path, root)} → {attach_rel} (相对链接 +../ 共 {n_links} 处)")
        if not apply:
            continue
        attach = path.parent / "attachments" / name
        attach.parent.mkdir(parents=True, exist_ok=True)
        attach.write_bytes(new_body.encode("utf-8"))
        # 写完校验行尾形态: 行数与 \r\n 计数必须与原文一致; 字节差只允许来自 ../ 前缀
        got = attach.read_bytes()
        expect = new_body.encode("utf-8")
        if got != expect:
            return _fail(f"{attach_rel}: 回读字节 != 写入字节 —— 写盘形态异常, 立即停止")
        body_crlf = body_text.count("\r\n")
        if got.count(b"\r\n") != body_crlf or got.decode("utf-8").count("\n") != body_text.count("\n"):
            return _fail(f"{attach_rel}: 行尾形态与原文不一致 (原文 \\r\\n={body_crlf}) —— 不合恪逐字节原样搬, 停止")
        # 主档: 头部区 (去尾部空行) + 空行 + 指针行 (行尾风格随原文件)
        eol = "\r\n" if (head and head[0].endswith("\r\n")) else "\n"
        while head and head[-1].strip() == "":
            head.pop()
        pointer = POINTER_LINE.format(name=name, stamp=stamp)
        data = "".join(head).rstrip("\r\n").encode("utf-8")
        data += (eol * 2).encode("utf-8") + pointer.encode("utf-8") + eol.encode("utf-8")
        path.write_bytes(data)
        print(f"    指针已留: {pointer}")
    if apply:
        print("已写盘; 外迁改变了相对链接深度 —— 重跑 commands run kb.check 与 doc.links 收口")
    return 0


# --------------------------------------------------------------------------- purge


def _backrefs(root: Path, path: Path) -> list[Path]:
    """全仓文本文件里引用了 `<stem>.md` 的文件 (排除本文件自身与扫描跳过目录)。"""
    needle = path.name.encode("utf-8")
    hits: list[Path] = []
    for cur, dirs, names in root.walk():
        dirs[:] = [d for d in dirs if d not in BACKREF_SKIP_DIRS]
        for name in names:
            p = cur / name
            if p == path or p.suffix.lower(
            ) not in (".md", ".html", ".py", ".toml", ".yml", ".yaml", ".txt", ".mjs", ".js"):
                continue
            try:
                if needle in p.read_bytes():
                    hits.append(p)
            except OSError:
                continue
    return hits


def _cmd_purge(root: Path, mb: Path, level: str, apply: bool) -> int:
    if level not in LEVELS:
        return _fail(f"等级 {level!r} 不在词表 ({'/'.join(LEVELS)})")
    if level != "L3":
        return _fail(f"purge 只接受 --level L3 (L0-L2 是保留/降噪/外迁, 不删) —— 拒绝 {level!r}")
    targets: list[Path] = []
    for path in _pitfall_files(mb):
        lines = _read_lines(path)
        if _tier_of(lines, _head_end(lines)) == level:
            targets.append(path)
    if not targets:
        print(f"等级 {level}: 没有可处理的文件 (0 件)")
        return 0
    verb = "将删除" if not apply else "已删除"
    print(f"等级 {level}: {verb} {len(targets)} 件" + ("" if apply else " —— dry-run, 未删 (需显式 --apply)"))
    # 两阶段 (全或无): 先对全体目标逐三闸门评估, 有任一不过则一个都不删 ——
    # 不允许「闸门全过的先删、没过的留着」这种部分删除 (计划 §04 R0: 任一不过即拒绝)
    deletable: list[Path] = []
    blocked = False
    for path in targets:
        rel = rel_posix(path, root)
        lines = _read_lines(path)
        text = "".join(lines)
        head = "".join(lines[:_head_end(lines)])
        # 闸门① 守阵齐全: 非空 `守阵:` 行 或 头部「无需守阵」; 都没有 = 判据缺失, 不许删
        if not GUARD_RE.search(text) and NO_GUARD_MARK not in head:
            print(f"  [闸门1 拒绝] {rel}: 无非空 `守阵:` 行, 头部也无「{NO_GUARD_MARK}」—— 判据缺失, 不进删除面 (计划 §07)")
            blocked = True
            continue
        # 闸门② 反向引用清零
        refs = _backrefs(root, path)
        if refs:
            shown = ", ".join(rel_posix(p, root) for p in refs[:5])
            more = f" 等 {len(refs)} 处" if len(refs) > 5 else ""
            print(f"  [闸门2 拒绝] {rel}: 全仓反向引用未清零 —— {shown}{more}")
            blocked = True
            continue
        # 闸门③ 观察期人判项的机器标记 (人判完跨 2 轮零复发后写进头部区)
        if not OBS_PASS_RE.search(head):
            print(f"  [闸门3 拒绝] {rel}: 头部缺 `> 观察通过: YYYY-MM-DD` (人判「跨 2 轮零复发」完成后写入; 标记定义见脚本 docstring)")
            blocked = True
            continue
        print(f"  {rel}  三闸门全过" + ("" if apply else ", --apply 后将删除"))
        deletable.append(path)
    if blocked:
        sys.stderr.write("[STOP] 存在闸门未过的文件 —— 全或无: 本次一个都不删, 处置完再跑\n")
        return 1
    if apply:
        for path in deletable:
            path.unlink()
        print("已删除; 生成物不手改 —— 重跑 commands run kb.index 重建索引")
    return 0


# --------------------------------------------------------------------------- main


def main(argv: list[str] | None = None) -> int:
    _utf8_stdout()
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="action", required=True)

    p_list = sub.add_parser("list", help="列出某等级的全部文件 (含行数/字符数; 未打标件区分呈现)")
    p_list.add_argument("--level", required=True, help="L0/L1/L2/L3")

    p_set = sub.add_parser("set", help="打标: 头部区第 4 行 `> 等级: L<n>` (已有则原地改值)")
    p_set.add_argument("file", help="目标文件 (绝对 / 仓库根相对 / memory-bank 相对)")
    p_set.add_argument("level", help="L0/L1/L2/L3")

    for name, help_ in (
        ("migrate", "整段叙事外迁到 attachments/, 主档留指针 (默认 dry-run)"), ("purge", "删除该等级文件, 三闸门全过才删 (默认 dry-run)")
    ):
        p = sub.add_parser(name, help=help_)
        p.add_argument("--level", required=True, help="L0/L1/L2/L3")
        p.add_argument("--apply", action="store_true", help="真写盘/真删除 (缺省 dry-run 只打印)")

    parser.add_argument("--root", help="仓库根 (默认向上找 .git)")
    parser.add_argument("--mb-dir", help="memory-bank 目录 (默认 <root>/memory-bank)")
    args = parser.parse_args(argv)

    root = Path(args.root).resolve() if args.root else find_root()
    mb = resolve_mb_dir(root, args.mb_dir)

    if args.action == "list":
        if args.level not in LEVELS:
            return _fail(f"等级 {args.level!r} 不在词表 ({'/'.join(LEVELS)})")
        return _cmd_list(mb, root, args.level)
    if args.action == "set":
        return _cmd_set(root, mb, args.file, args.level)
    if args.action == "migrate":
        return _cmd_migrate(root, mb, args.level, args.apply)
    return _cmd_purge(root, mb, args.level, args.apply)


if __name__ == "__main__":
    raise SystemExit(main())
