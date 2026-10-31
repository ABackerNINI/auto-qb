"""WebUI 聚合内容映射 (dev-only, 只读) —— issue 26-10-31-2226-feat-webui-agg-content-map。

把 frontend-split.md 的十条「聚合读法」人读判别法搬进工具: 给内容关键词, 单点输出它在
shared/tpl / css / JS 域的落点 —— 拆分后单读 index.html / 单个 css / 单个 js 会假绿或假红,
改动的正确落点由本命令现算, 文档降为解释 (判据单点: memory-bank/pitfalls/web-ui/frontend-split.md)。

四域扫描面 (聚合口径与测试侧 _ui_aggregate/_app_bundle_text 同源):
- shell   : 三皮肤 index.html (atlas/console/prism) —— 命中按行分类: manifest 清单 / css link /
            head / sprite 段 / #app 内联 / 其它内联
- tpl     : shared/tpl/*.html 与 shared/drawer_tpl/*.html —— 附「哪些皮肤挂载、into 到哪」
            (清单 = tpl-manifest, 单一来源; 盘上有而清单没挂的分片会标 orphan)
- css     : static 下全部 *.css —— 附「被哪些皮肤 head link、link 序」; 未被 link 的标出
- js      : static/shared/*.js 与皮肤目录下 *.js —— 附「清单序 #k/N (tpl-manifest.scripts)」;
            盘上有而清单没挂的标 orphan (漏挂 = 那块功能整块不存在)

用法:
    commands run dev.ui-map -- <关键词> [更多关键词] [--regex]
    python scripts/ui_content_map.py site-chip --regex "draw[e]r"
退出码: 0 正常 (无命中也是 0, 结论在输出里) / 2 参数错
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "src" / "auto_qb" / "webui" / "static"
SKINS = ("atlas", "console", "prism")
MANIFEST_RE = re.compile(r'<script type="application/json" id="tpl-manifest">(.*?)</script>', re.S)
LINK_RE = re.compile(r'<link[^>]*href="([^"]+\.css)"')


def _utf8_stdout() -> None:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")


def _shells() -> dict[str, dict]:
    """三 shell 的清单/链接/内联分区 (一次解析, 全命令共用)。"""
    out: dict[str, dict] = {}
    for skin in SKINS:
        path = STATIC / skin / "index.html"
        text = path.read_text(encoding="utf-8")
        m = MANIFEST_RE.search(text)
        manifest = json.loads(m.group(1)) if m else {"parts": [], "scripts": []}
        css_links = [h for h in LINK_RE.findall(text[:text.find("</head>") if "</head>" in text else len(text)])]
        sprite_s = text.find('<svg class="icon-sprite"')
        sprite_e = text.find("</svg>", sprite_s) if sprite_s >= 0 else -1
        out[skin] = {
            "path": path,
            "text": text,
            "manifest_span": (m.start(), m.end()) if m else None,
            "parts": manifest.get("parts", []),
            "scripts": manifest.get("scripts", []),
            "css_links": css_links,
            "head_end": text.find("</head>"),
            "sprite_span": (sprite_s, sprite_e) if sprite_s >= 0 and sprite_e > sprite_s else None,
            "app_start": text.find('<div id="app"'),
            "line_offsets": [0],
        }
        acc = 0
        for line in text.splitlines(keepends=True):
            acc += len(line)
            out[skin]["line_offsets"].append(acc)  # 第 i 行 (1-based) 的起始字符偏移 = line_offsets[i-1]
    return out


def _shell_line_class(skin: dict, offset: int) -> str:
    s, e = skin["manifest_span"] or (-1, -1)
    if s <= offset < e:
        return "manifest 清单"
    if skin["sprite_span"] and skin["sprite_span"][0] <= offset < skin["sprite_span"][1]:
        return "sprite 段(三 shell 逐字 parity)"
    if offset < skin["head_end"]:
        return "head"
    if skin["app_start"] >= 0 and offset >= skin["app_start"]:
        return "#app 内联"
    return "shell 内联"


def _scan(path: Path, pats: list[re.Pattern]) -> list[tuple[int, str]]:
    hits = []
    for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        for p in pats:
            if p.search(line):
                hits.append((i, line.strip()))
                break
    return hits


def _mounted_by(src: str, shells: dict[str, dict]) -> str:
    """tpl 分片的挂载面: 'atlas,console,prism(into=app)' 形态; 未挂 = orphan 提示。"""
    row = []
    for skin_name, skin in shells.items():
        for part in skin["parts"]:
            if part.get("src") == src:
                row.append(f"{skin_name}(into={part.get('into', '?')})")
    if not row:
        return "orphan: 不在任何皮肤的 tpl-manifest (漏挂 = 那块不加载)"
    skins = ",".join(sorted({r.split("(")[0] for r in row}))
    intos = sorted({r.split("into=")[1].rstrip(")") for r in row})
    # 清单等价 = 每皮肤恰好一条且 into 一致 (不等价会被 test_frontend_template_split_wiring 判红,
    # 这里只是把疑点当场标出)
    note = "" if len(row) == len(shells) and len(intos) == 1 else " (清单不等价!)"
    return f"挂载 {skins} into={'+'.join(intos)}{note}"


def _css_links_of(rel_url: str, shells: dict[str, dict]) -> str:
    row = []
    for skin_name, skin in shells.items():
        if rel_url in skin["css_links"]:
            row.append(f"{skin_name}#{skin['css_links'].index(rel_url) + 1}")
    return f"head link {'|'.join(row)}" if row else "未被 head link (按需注入或孤儿)"


def _js_order_of(rel_url: str, shells: dict[str, dict]) -> str:
    orders = []
    for skin_name, skin in shells.items():
        if rel_url in skin["scripts"]:
            orders.append((skin_name, skin["scripts"].index(rel_url) + 1, len(skin["scripts"])))
    if not orders:
        return "orphan: 不在任何皮肤 scripts 清单"
    pos = {o[1] for o in orders}
    total = {o[2] for o in orders}
    shape = f"#{orders[0][1]}/{orders[0][2]}"
    note = "" if len(pos) == 1 and len(total) == 1 else " (清单序不等价!)"
    return f"清单序 {shape} ({'/'.join(o[0] for o in orders)}){note}"


def main(argv: list[str] | None = None) -> int:
    _utf8_stdout()
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("keywords", nargs="+", help="内容关键词 (子串匹配; 标识符区分大小写)")
    parser.add_argument("--regex", action="store_true", help="关键词按 Python 正则解释")
    args = parser.parse_args(argv)

    try:
        pats = [re.compile(k) if args.regex else re.compile(re.escape(k)) for k in args.keywords]
    except re.error as exc:
        print(f"WHY: 正则不合法: {exc}")
        return 2

    shells = _shells()
    print(f"扫描面: 三 shell + shared/tpl|drawer_tpl + static/**/*.css + shared|皮肤 *.js (聚合口径, 单点 frontend-split.md)")
    total = 0
    for kw, pat in zip(args.keywords, pats):
        print(f"\n=== 关键词 {kw!r} ===")
        count = 0

        for skin_name, skin in shells.items():
            for line_no, line in _scan(skin["path"], [pat]):
                count += 1
                cls = _shell_line_class(skin, skin["line_offsets"][line_no - 1])
                print(f"[shell/{skin_name}] {skin['path'].relative_to(ROOT).as_posix()}:{line_no} ({cls})")
                print(f"    {line[:110]}")

        tpl_dirs = (STATIC / "shared" / "tpl", STATIC / "shared" / "drawer_tpl")
        for d in tpl_dirs:
            if not d.is_dir():
                continue
            for path in sorted(d.glob("*.html")):
                rel_url = "/shared/" + ("tpl/" if d.name == "tpl" else "drawer_tpl/") + path.name
                hits = _scan(path, [pat])
                if not hits:
                    continue
                mount = _mounted_by(rel_url, shells)
                for line_no, line in hits:
                    count += 1
                    print(f"[tpl] {path.relative_to(ROOT).as_posix()}:{line_no}  {mount}")
                    print(f"    {line[:110]}")

        for path in sorted(STATIC.rglob("*.css")):
            hits = _scan(path, [pat])
            if not hits:
                continue
            rel_url = "/" + path.relative_to(STATIC).as_posix().replace("\\", "/")
            link = _css_links_of(rel_url, shells)
            skin = path.relative_to(STATIC).parts[0] if path.relative_to(STATIC).parts[0] in SKINS else "shared"
            for line_no, line in hits:
                count += 1
                print(f"[css/{skin}] {path.relative_to(ROOT).as_posix()}:{line_no}  {link}")
                print(f"    {line[:110]}")

        js_paths = sorted((STATIC / "shared").glob("*.js")
                         ) + sorted(p for skin in SKINS for p in (STATIC / skin).glob("*.js"))
        for path in js_paths:
            hits = _scan(path, [pat])
            if not hits:
                continue
            rel_url = "/" + path.relative_to(STATIC).as_posix().replace("\\", "/")
            order = _js_order_of(rel_url, shells)
            for line_no, line in hits:
                count += 1
                print(f"[js] {path.relative_to(ROOT).as_posix()}:{line_no}  {order}")
                print(f"    {line[:110]}")

        print(f"小计: {count} 处" if count else "无命中 (查大小写/试 --regex; 关键词也可能确实只在文档)")
        total += count
    print(f"\n总计 {total} 处命中。判别法解释: memory-bank/pitfalls/web-ui/frontend-split.md (本命令是它的机器索引)")
    print("NEXT: 改模板/加片段的接线清单(三份 manifest + app.mixin + 218 行硬顶)同见该坑档")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
