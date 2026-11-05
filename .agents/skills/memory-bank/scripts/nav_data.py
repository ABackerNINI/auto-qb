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
输出 {"stamp", "items", "topics", "counts"} 单个 dict, 可直接 json.dumps; stamp 取数据自带的
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
from gen_doc_map import FORM_ORDER, META_RE, collect, group_by_topic, is_live  # noqa: E402

NO_STATUS = "(无状态)"

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
    item["doc-stale"] = bool(
        age is not None and age > STALE_DAYS_REFERENCE and item["form"] not in _STALE_EXEMPT_FORMS
    )


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


def collect_nav(mb: Path, now: datetime | None = None) -> dict:
    """导航页全量数据装配单点: {stamp, items[], topics[], counts}。

    `now` 只用于 `doc-age-days` / `doc-stale` 软提示; 测试传固定值即可确定性断言。
    """
    items = collect(mb)
    now = now or datetime.now()
    for item in items:
        _enrich_item(item, mb, now)
    stamp = max((i["doc-updated"] for i in items), default="")
    return {
        "stamp": stamp,
        "items": items,
        "topics": _topic_list(items),
        "counts": _form_status_counts(items),
    }
