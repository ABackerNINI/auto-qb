"""内置条件插件: path, size, tags, category, trackers, state, hr, date_time, seedtime,
upload_ratio, upload_size, upload_size_today/this_week/this_month, freespace"""
import re
import shutil
from datetime import datetime, time as dtime

from . import utils
from .base import BaseCondition
from .registry import register_condition

# 语义状态 -> qB 原始 state 集合(与想法.md "状态映射表" 一致)
_STATE_MAP = {
    "checking": {"checkingDL", "checkingUP", "checkingResumeData"},
    "downloading": {"downloading", "forcedDL", "metaDL", "forcedMetaDL"},
    "complete": {"uploading", "stalledUP", "pausedUP", "forcedUP", "queuedUP", "stoppedUP"},
    "uploading": {"uploading", "forcedUP", "stalledUP"},
    "errored": {"missingFiles", "error", "unknown"},
    "stopped": {"pausedDL", "pausedUP", "stoppedDL", "stoppedUP"},
}


def _in_range(value: int, spec: str) -> bool:
    spec = str(spec).strip()
    if "-" in spec:
        a, b = spec.split("-", 1)
        return int(a) <= value <= int(b)
    return value == int(spec)


def _parse_hm(text: str):
    h, m = str(text).strip().split(":")
    return int(h), int(m)


@register_condition
class PathCondition(BaseCondition):
    """路径条件: 匹配 save_path/content_path 前缀, 支持 regex: 前缀, 列表为或关系"""
    name = "path"

    def __init__(self, spec):
        self.patterns = spec if isinstance(spec, list) else [spec]

    def match(self, ctx):
        candidates = [ctx.torrent.save_path, ctx.torrent.content_path]
        for p in self.patterns:
            p = str(p)
            if p.startswith("regex:"):
                try:
                    rx = re.compile(p[6:])
                except re.error:
                    continue
                if any(rx.search(c) for c in candidates if c):
                    return True
            else:
                if any(c and c.startswith(p) for c in candidates):
                    return True
        return False


@register_condition
class SizeCondition(BaseCondition):
    """种子总大小条件, 如 '>=100MiB'"""
    name = "size"

    def __init__(self, spec):
        self.op, self.value = utils.parse_compare(str(spec), utils.parse_fsize)

    def match(self, ctx):
        return utils.compare(self.op, ctx.torrent.size, self.value)


@register_condition
class TagsCondition(BaseCondition):
    """标签条件: 每组内逗号分隔为与, 组间为或, 支持 regex: 和 ${hr-time}"""
    name = "tags"

    def __init__(self, spec):
        spec = spec if isinstance(spec, list) else [spec]
        self.groups = [[p.strip() for p in g.split(",") if p.strip()] for g in spec]

    def match(self, ctx):
        current = set(t.strip() for t in (ctx.torrent.tags or "").split(",") if t.strip())
        for group in self.groups:
            ok = True
            for pat in group:
                pat = ctx.replace_vars(pat)
                if not pat:
                    continue
                if pat.startswith("regex:"):
                    try:
                        rx = re.compile(pat[6:])
                    except re.error:
                        ok = False
                        break
                    if not any(rx.search(t) for t in current):
                        ok = False
                        break
                else:
                    if pat not in current:
                        ok = False
                        break
            if ok:
                return True
        return False


@register_condition
class CategoryCondition(BaseCondition):
    """分类条件: 列表为或关系, 支持 regex:"""
    name = "category"

    def __init__(self, spec):
        self.patterns = spec if isinstance(spec, list) else [spec]

    def match(self, ctx):
        category = (ctx.torrent.category or "").strip()
        for pat in self.patterns:
            pat = str(pat)
            if pat.startswith("regex:"):
                try:
                    rx = re.compile(pat[6:])
                except re.error:
                    continue
                if rx.search(category):
                    return True
            elif category == pat:
                return True
        return False


@register_condition
class TrackersCondition(BaseCondition):
    """tracker 条件: 匹配 tracker 配置名, 列表为或关系, 支持 regex:"""
    name = "trackers"

    def __init__(self, spec):
        self.patterns = spec if isinstance(spec, list) else [spec]

    def match(self, ctx):
        names = ctx.matched_tracker_names()
        for pat in self.patterns:
            pat = str(pat)
            if pat.startswith("regex:"):
                try:
                    rx = re.compile(pat[6:])
                except re.error:
                    continue
                if any(rx.search(n) for n in names):
                    return True
            elif pat in names:
                return True
        return False


@register_condition
class StateCondition(BaseCondition):
    """状态条件: 语义状态(checking/downloading/complete/uploading/errored/stopped),
    每组内 & 连接为与, 组间为或"""
    name = "state"

    def __init__(self, spec):
        spec = spec if isinstance(spec, list) else [spec]
        self.groups = [str(g).split("&") for g in spec]

    def match(self, ctx):
        state = ctx.torrent.state
        for group in self.groups:
            if all(state in _STATE_MAP.get(s.strip(), set()) for s in group):
                return True
        return False


@register_condition
class HrCondition(BaseCondition):
    """HR 条件: condition-met / condition-not-met / satisfied"""
    name = "hr"

    def __init__(self, spec):
        self.mode = str(spec)

    def match(self, ctx):
        confs = [c for c in ctx.matched_tracker_confs() if c.hr_rule]
        if not confs:
            return False
        if self.mode == "condition-not-met":
            return not any(ctx.check_hr_condition(c) for c in confs)
        if self.mode == "satisfied":
            return any(ctx.check_hr_condition(c) and ctx.check_hr_satisfied(c) for c in confs)
        # condition-met
        return any(ctx.check_hr_condition(c) for c in confs)


@register_condition
class DateTimeCondition(BaseCondition):
    """日期时间条件: day_of_month / day_of_week / time"""
    name = "date_time"

    def __init__(self, spec):
        self.day_of_month = spec.get("day_of_month")
        self.day_of_week = spec.get("day_of_week")
        self.time_range = spec.get("time")

    def match(self, ctx):
        now = datetime.now()
        if self.day_of_month and not _in_range(now.day, str(self.day_of_month)):
            return False
        if self.day_of_week and not _in_range(now.isoweekday(), str(self.day_of_week)):
            return False
        if self.time_range:
            start_s, end_s = str(self.time_range).split("-", 1)
            t_min = dtime(*_parse_hm(start_s))
            t_max = dtime(*_parse_hm(end_s))
            t_now = now.time()
            if t_min <= t_max:
                if not (t_min <= t_now <= t_max):
                    return False
            else:  # 跨午夜
                if not (t_now >= t_min or t_now <= t_max):
                    return False
        return True


@register_condition
class SeedtimeCondition(BaseCondition):
    """做种时长条件, 如 '<24H'"""
    name = "seedtime"

    def __init__(self, spec):
        self.op, self.value = utils.parse_compare(str(spec), utils.parse_time)

    def match(self, ctx):
        return utils.compare(self.op, ctx.torrent.seeding_time, self.value)


@register_condition
class UploadRatioCondition(BaseCondition):
    """上传比率条件, 如 '>1.5'"""
    name = "upload_ratio"

    def __init__(self, spec):
        self.op, self.value = utils.parse_compare(str(spec), float)

    def match(self, ctx):
        return utils.compare(self.op, ctx.torrent.ratio, self.value)


@register_condition
class UploadSizeCondition(BaseCondition):
    """总上传大小条件, 如 '>10GiB'"""
    name = "upload_size"

    def __init__(self, spec):
        self.op, self.value = utils.parse_compare(str(spec), utils.parse_fsize)

    def match(self, ctx):
        return utils.compare(self.op, ctx.torrent.uploaded, self.value)


class _UploadDeltaCondition(BaseCondition):
    """周期上传增量条件基类: 基于 RuleManager 维护的快照, 取 max(0, 增量)"""
    kind = ""  # daily / weekly / monthly

    def __init__(self, spec):
        self.op, self.value = utils.parse_compare(str(spec), utils.parse_fsize)

    def match(self, ctx):
        delta = ctx.manager.upload_delta(ctx.torrent, self.kind)
        return utils.compare(self.op, delta, self.value)


@register_condition
class UploadSizeTodayCondition(_UploadDeltaCondition):
    """今日上传大小条件(自然日)"""
    name = "upload_size_today"
    kind = "daily"


@register_condition
class UploadSizeThisWeekCondition(_UploadDeltaCondition):
    """本周上传大小条件(ISO周)"""
    name = "upload_size_this_week"
    kind = "weekly"


@register_condition
class UploadSizeThisMonthCondition(_UploadDeltaCondition):
    """本月上传大小条件"""
    name = "upload_size_this_month"
    kind = "monthly"


@register_condition
class FreespaceCondition(BaseCondition):
    """磁盘可用空间条件: path + amount, 如 {path: 'R:\\', amount: '<100GiB'}"""
    name = "freespace"

    def __init__(self, spec):
        self.path = str(spec.get("path", ""))
        self.op, self.value = utils.parse_compare(str(spec.get("amount", "")), utils.parse_fsize)

    def match(self, ctx):
        if not self.path:
            return False
        try:
            free = shutil.disk_usage(self.path).free
        except OSError:
            return False
        return utils.compare(self.op, free, self.value)
