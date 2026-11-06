"""nav 导航页数据层: 在 gen_doc_map.collect() 之上做一层薄 enrich, 产出导航页所需的全量 dict。

单点装配 (服务层 nav_server.py 与 --gen-static 静态导出共用): import 同目录 gen_doc_map 的
collect() 取四形态全量条目, **不改其本体** (它是闸门/守阵消费单点)。enrich 内容 (固化自
tmp-analysis/nav-design/ 三套原型已验证的数据装配逻辑, 计划 26-10-04-0952 §02):
    issue 侧 : issue-type / issue-tier / issue-summary (重读该 issue 文件的 meta 补齐, collect 不带)
    全形态   : doc-updated (HTML 读 doc-updated meta; 缺省回落条目 stamp; md 档案即 stamp)
               doc-age-days / doc-stale (2026-11-05 计划 26-11-05-1049 §07 P4): 只做**陈旧度软提示**,
               plan / report 冻结不审, 其余按 `_common.STALE_DAYS_REFERENCE`; 只提示不拦截
    派生     : topics[] (专题键 + live 标记 + forms 列表, live 口径同 gen_doc_map.is_live)
               counts (各形态 x 状态计数; 缺状态归 "(无状态)" 桶, 同 gen_doc_map 的宁多展示口径)
               targets[] (2026-11-07 关联图): 每条 ref 解析成 {t, st, raw}, st 五态 --
                   ok       = 落在台账四类件里 (可下钻)
                   ext      = 文件在 memory-bank/ 内但不在台账扫描面 (pitfalls/testing/...), 可打开
                   repo     = 文件在仓库根下 (resources/ 等), 存在但导航页不代理, 只标示不可点
                   basename = 声明路径失效, 按 basename 在 testing/baselines/attachments/ 找回
                   dead     = 真找不到
               不用 collect() 的 refs 原值直接画图: 实测 1811 条 ref 里 578 条目标"看起来不存在",
               其中 325 条其实在库内、253 条是被归档搬走的基线 —— 页面渲染成灰字「(未入库)」而
               守卫是绿的 (kb.check 有归档回退), 图会有一半是悬空边。
     ext      : {库外件路径: [声明了它的台账 link]} —— 库外件 (坑档 / 基线 / 切片) 的 Ref 反向边。
                只扫**已被台账件引用到的**库外件 (有界集合, 实测 ~320 个), 不扩 collect() 的扫描面:
                那是 kb.docmap / kb.check / 索引生成共同消费的单点, 动它等于改「台账件」的定义。
输出 {"stamp", "items", "topics", "counts", "ext"} 单个 dict, 可直接 json.dumps; stamp 取数据自带的
最新 doc-updated / issue-stamp (混格式按字典序取最大, 前缀日期 < 带时分, 同日带时分者胜),
**stamp 不依赖当前时钟**(纪律同 gen_doc_map); 唯一读时钟的是年龄提示字段, 它只是显示辅助,
不参与排序或新戳判定。
"""
from __future__ import annotations

import html
import re
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _common import STALE_DAYS_REFERENCE  # noqa: E402
from gen_doc_map import (  # noqa: E402
    FORM_ORDER, META_RE, _refs_of, collect, group_by_topic, is_live,
)

NO_STATUS = "(无状态)"
MB_PREFIX = "memory-bank/"  # refs 声明的是仓库根相对路径, 台账 link 是 memory-bank 相对路径
BASELINE_ATTACH = ("testing", "baselines", "attachments")  # 归档回退根 (kb.check 同口径)
# 仓库根下这些前缀一律不进导航 (config.yml 是真生产配置, auto-qb-data/ 是运行数据, 见 pitfalls/ops/prod-files.md)
REPO_DENY = ("config.yml", "auto-qb-data", ".git", ".env")

# 数据自带时间戳的两种体例: `YY-MM-DD-HHMM` (HTML) / `YY-MM-DD` (md 档案)
_AGE_STAMP_RE = re.compile(r"^(\d{2})-(\d{2})-(\d{2})(?:-(\d{4}))?$")

# plan / report 出厂即冻结 (doc-forms: 拍板后冻结 / 快照完成即终态), 不做陈旧度提示
_STALE_EXEMPT_FORMS = ("plan", "report")


def _age_days(stamp: str, now: datetime) -> int | None:
    """时间戳 → 距今天数 (只到日精度); 解析不了返回 None (不猜)。"""
    m = _AGE_STAMP_RE.match(stamp)
    if not m:
        return None
    yy, mm, dd, hhmm = m.groups()
    try:
        when = datetime(2000 + int(yy), int(mm), int(dd))
        if hhmm:
            when = when.replace(hour=int(hhmm[:2]), minute=int(hhmm[2:]))
    except ValueError:
        return None
    return max(0, (now - when).days)


def _enrich_item(item: dict, mb: Path, now: datetime) -> None:
    """就一条 collect() 条目原地补 enrich 字段。HTML 重读一次 meta (collect 已丢弃原文, 383 件二次读 <1s)。"""
    path = mb / item["link"]
    meta: dict[str, str] = {}
    if path.suffix == ".html":
        # meta 值是 HTML 属性原文 (已转义): 数据层先反转义, 前端 esc() 只转义一次 —— 否则标题/
        # 摘要里的 "->" 会显示成 "-&gt;" (2026-10-31 用户报; 同 gen_issues_index.meta 的口径)
        meta = {k: html.unescape(v) for k, v in META_RE.findall(path.read_text(encoding="utf-8"))}
    if item["form"] == "issue":
        item["issue-type"] = meta.get("issue-type", "")
        item["issue-tier"] = meta.get("issue-tier", "")
        item["issue-summary"] = meta.get("issue-summary", "")
    item["doc-updated"] = meta.get("doc-updated", "") or item["stamp"]
    age = _age_days(item["doc-updated"], now)
    item["doc-age-days"] = age
    item["doc-stale"] = bool(age is not None and age > STALE_DAYS_REFERENCE and item["form"] not in _STALE_EXEMPT_FORMS)


def _topic_list(items: list[dict]) -> list[dict]:
    """专题派生: 专题键 + live 标记 (口径同 gen_doc_map.is_live) + 形态清单 (按 FORM_ORDER 定序)。"""
    groups = group_by_topic(items)
    topics: list[dict] = []
    for key in sorted(groups):
        group = groups[key]
        topics.append(
            {
                "topic": key,
                "live": is_live(group),
                "forms": [f for f in FORM_ORDER if any(i["form"] == f for i in group)],
            }
        )
    return topics


def _form_status_counts(items: list[dict]) -> dict[str, dict[str, int]]:
    """各形态 x 状态计数 (视图 B 四工位统计带的数据源); 缺/未知状态归 NO_STATUS 桶。"""
    counts: dict[str, dict[str, int]] = {}
    for form in FORM_ORDER:
        bucket: dict[str, int] = {}
        for item in items:
            if item["form"] == form:
                status = item["status"] or NO_STATUS
                bucket[status] = bucket.get(status, 0) + 1
        counts[form] = dict(sorted(bucket.items()))
    return counts


def _rel_of(ref: str) -> str:
    """ref 是仓库根相对路径 (memory-bank/...), 台账 link 是 memory-bank 相对路径 —— 去掉前缀再比。"""
    return ref[len(MB_PREFIX):] if ref.startswith(MB_PREFIX) else ref


def _inside(base: Path, cand: Path) -> bool:
    """resolve 后仍落在 base 内才认 —— ref 里写 `memory-bank/../config.yml` 这类穿越路径时,
    否则会被标成 ext 并生成可点链接 (静态导出件点开就是红线文件); 服务模式则会先被浏览器
    规范化成 /config.yml 变 404, 压根走不到静态映射的 403 判据。"""
    try:
        real = cand.resolve()
    except (OSError, ValueError):
        return False
    return real == base or base in real.parents


def _denied(rel: str, root: Path) -> bool:
    """红线路径不进导航: 即便它解析后确实在仓库根下, ref 声明了也不该变成一条可点的「仓库根」链接。

    判的是 resolve 之后的真实落点 —— 拿 rel 字面量判会被 `memory-bank/../config.yml` 绕过。
    """
    try:
        head = (root / rel).resolve().relative_to(root.resolve()).parts[0]
    except (OSError, ValueError):
        return True  # 落不进仓库根 (越界): 一律拒绝
    return head in REPO_DENY


def _basename_index(mb: Path) -> dict[str, str]:
    """归档回退索引: basename -> memory-bank 相对路径 (基线迁移到 attachments/ 后 refs 没跟着改)。

    与 gen_doc_map.check_claim_chain 的归档回退同一判据, 只是那边用于闸门、这里用于导航;
    basename 冲突时按路径字典序取第一个 (确定性优先, 不猜语义)。
    """
    base = mb.joinpath(*BASELINE_ATTACH)
    index: dict[str, str] = {}
    if not base.is_dir():
        return index
    for path in sorted(base.rglob("*")):
        if path.is_file():
            index.setdefault(path.name, path.relative_to(mb).as_posix())
    return index


def _resolve_targets(items: list[dict], mb: Path) -> None:
    """就地把每条 ref 解析成 {t, st, raw}; 只在命中时才建归档索引 (绝大多数库用不上)。

    判据与 gen_doc_map.check_claim_chain 对齐 (ref 是**仓库根相对**路径, 不是 memory-bank 相对):
    先剥前缀查台账件, 再按 memory-bank 定位查库内文件, 再按仓库根定位 (resources/ 这类库内但
    导航页不代理的文件), 最后才是 baselines 归档回退 —— 回退同样**只对 testing/baselines/ 开头的
    ref 生效** (守卫同款闸门), 否则台账件被删而同名基线切片还在时, 会把真死链说成"可打开"。
    """
    root = mb.parent
    mb_real = mb.resolve()
    root_real = root.resolve()
    links = {item["link"] for item in items}
    index: dict[str, str] | None = None
    for item in items:
        targets: list[dict] = []
        for raw in item["refs"]:
            rel = _rel_of(raw)
            if rel in links:
                state, path = "ok", rel
            elif _inside(mb_real, mb / rel) and (mb / rel).is_file():
                state, path = "ext", rel
            elif _inside(root_real, root / raw) and (root / raw).is_file() and not _denied(raw, root):
                state, path = "repo", raw  # 仓库根相对: 文件在库内但不在 memory-bank/ 下
            else:
                hit = None
                if raw.startswith(MB_PREFIX + "testing/baselines/"):
                    if index is None:
                        index = _basename_index(mb)
                    hit = index.get(Path(rel).name)
                state, path = ("basename", hit) if hit else ("dead", rel)
            targets.append({"t": path, "st": state, "raw": raw})
        item["targets"] = targets


def _ext_backrefs(items: list[dict], mb: Path) -> dict[str, list[str]]:
    """库外件的反向边: 只扫已被台账件引用到的库外件 (有界), 读它们的 Ref 声明回指台账件的那些。

    没有这一步, 「一个坑档被谁认领」永远看不见 —— 库外件不进 DATA.items, 反向引用自然为空。
    单个文件读失败按无引用处理 (导航页不该因为一个坏件整体空白)。
    """
    links = {item["link"] for item in items}
    pool: list[str] = []
    seen: set[str] = set()
    for item in items:
        for target in item.get("targets", []):
            path = target["t"]
            if target["st"] in ("ext", "basename", "repo") and path not in links and path not in seen:
                seen.add(path)
                pool.append(path)
    back: dict[str, list[str]] = {}
    for rel in pool:
        path = mb / rel
        if not path.is_file():
            path = mb.parent / rel  # repo 态 (resources/ 等) 落在仓库根
        try:
            refs = _refs_of(path)
        except (OSError, UnicodeDecodeError):
            continue  # 二进制 / 非 UTF-8 的库外件: 当无引用, 不炸整页 (/api/data 只兜 OSError)
        hits = [ref for ref in map(_rel_of, refs) if ref in links]
        if hits:
            back[rel] = hits
    return back


def collect_nav(mb: Path, now: datetime | None = None) -> dict:
    """导航页全量数据装配单点: {stamp, items[], topics[], counts, ext}。

    `now` 只用于 `doc-age-days` / `doc-stale` 软提示; 测试传固定值即可确定性断言。
    """
    items = collect(mb)
    now = now or datetime.now()
    for item in items:
        _enrich_item(item, mb, now)
    _resolve_targets(items, mb)
    ext = _ext_backrefs(items, mb)
    stamp = max((i["doc-updated"] for i in items), default="")
    return {
        "stamp": stamp,
        "items": items,
        "topics": _topic_list(items),
        "counts": _form_status_counts(items),
        "ext": ext,
    }
