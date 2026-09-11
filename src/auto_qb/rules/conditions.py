"""内置条件插件: path, size, tags, category, trackers, state, hr, date_time, seedtime,
upload_ratio, upload_size, upload_size_today/this_week/this_month, freespace"""
import shutil
from datetime import datetime

from .. import utils
from .base import BaseCondition, RuleContext
from .registry import register_condition


def _in_range(value: int, spec: str) -> bool:
    spec = str(spec).strip()
    if "-" in spec:
        a, b = spec.split("-", 1)
        return int(a) <= value <= int(b)
    return value == int(spec)


@register_condition
class PathCondition(BaseCondition):
    """路径条件: 匹配 save_path/content_path 前缀, 支持 regex: 前缀, 列表为或关系"""
    name = "path"

    def __init__(self, spec):
        self.patterns = spec if isinstance(spec, list) else [spec]

    def match(self, ctx: RuleContext):
        candidates = [ctx.torrent.save_path, ctx.torrent.content_path]
        for path in candidates:
            if utils.match_path_patterns(path, self.patterns):
                return True
        return False


@register_condition
class SizeCondition(BaseCondition):
    """种子总大小条件, 如 '>=100MiB'"""
    name = "size"

    def __init__(self, spec):
        self.op, self.value = utils.parse_compare(str(spec), utils.parse_fsize)

    def match(self, ctx: RuleContext):
        return utils.compare(self.op, ctx.torrent.size, self.value)


@register_condition
class TagsCondition(BaseCondition):
    """标签条件: 每组内逗号分隔为与, 组间为或, 支持 regex:/:ignore_case 和 ${required_seeding_time}"""
    name = "tags"

    def __init__(self, spec):
        spec = spec if isinstance(spec, list) else [spec]
        self.groups = [[p.strip() for p in g.split(",") if p.strip()] for g in spec]

    def match(self, ctx: RuleContext):
        current = ctx.torrent.tags_set
        for group in self.groups:
            ok = True
            for pat in group:
                pat = utils.replace_vars(pat, ctx.torrent.tracker_conf)
                if not pat:
                    continue
                # 单模式包列表复用 utils.match_value(语法解析/regex:/:ignore_case 唯一实现)
                if not any(utils.match_value(t, [pat]) for t in current):
                    ok = False
                    break
            if ok:
                return True
        return False


@register_condition
class CategoryCondition(BaseCondition):
    """分类条件: 列表为或关系, 支持 regex:/:ignore_case"""
    name = "category"

    def __init__(self, spec):
        self.patterns = spec if isinstance(spec, list) else [spec]

    def match(self, ctx: RuleContext):
        category = (ctx.torrent.category or "").strip()
        return any(utils.match_value(category, [str(pat)]) for pat in self.patterns)


@register_condition
class TrackersCondition(BaseCondition):
    """tracker 条件: 匹配 tracker 配置名, 列表为或关系, 支持 regex:/:ignore_case"""
    name = "trackers"

    def __init__(self, spec):
        self.patterns = spec if isinstance(spec, list) else [spec]

    def match(self, ctx: RuleContext):
        conf = ctx.torrent.tracker_conf
        names = [conf.name] if conf is not None else []
        return any(any(utils.match_value(n, [str(pat)]) for n in names) for pat in self.patterns)


@register_condition
class StateCondition(BaseCondition):
    """状态条件: qB TorrentState 枚举类别属性(is_downloading/is_uploading/is_complete/
    is_checking/is_stopped/is_paused/is_errored), 与 qB 官方语义一致, 每组内 & 连接为与,
    组间为或。spec 合法性由 config 校验阶段保证(仅 is_* 类别属性), 此处直接使用"""
    name = "state"

    def __init__(self, spec):
        spec = spec if isinstance(spec, list) else [spec]
        self.groups = [str(g).split("&") for g in spec]

    def match(self, ctx: RuleContext):
        for group in self.groups:
            if all(getattr(ctx.torrent.state_enum, s) for s in group):
                return True
        return False


@register_condition
class HrCondition(BaseCondition):
    """HR 条件: condition-met / condition-not-met / satisfied"""
    name = "hr"

    def __init__(self, spec):
        self.mode = str(spec)

    # TODO: 重新梳理此功能
    def match(self, ctx: RuleContext):
        torrent = ctx.torrent
        conf = torrent.tracker_conf
        if self.mode == "condition-not-met":
            return not torrent.check_hr_condition()
        if self.mode == "satisfied":
            # 没有HR的站点默认满足HR做种条件
            return conf.hr is None or torrent.check_hr_condition() and torrent.check_hr_satisfied()
        # condition-met
        return torrent.check_hr_condition()


@register_condition
class DateTimeCondition(BaseCondition):
    """日期时间条件: day_of_month / day_of_week / time"""
    name = "date_time"

    def __init__(self, spec):
        self.day_of_month = spec.get("day_of_month")
        self.day_of_week = spec.get("day_of_week")
        self.time_range = spec.get("time")

    def match(self, ctx: RuleContext):
        now = datetime.now()
        if self.day_of_month and not _in_range(now.day, str(self.day_of_month)):
            return False
        if self.day_of_week and not _in_range(now.isoweekday(), str(self.day_of_week)):
            return False
        if self.time_range:
            if not utils.time_in_range(now.time(), self.time_range):
                return False
        return True


@register_condition
class SeedtimeCondition(BaseCondition):
    """做种时长条件, 如 '<24H'"""
    name = "seedtime"

    def __init__(self, spec):
        self.op, self.value = utils.parse_compare(str(spec), utils.parse_time)

    def match(self, ctx: RuleContext):
        return utils.compare(self.op, ctx.torrent.seeding_time, self.value)


@register_condition
class UploadRatioCondition(BaseCondition):
    """上传比率条件, 如 '>1.5'"""
    name = "upload_ratio"

    def __init__(self, spec):
        self.op, self.value = utils.parse_compare(str(spec), float)

    def match(self, ctx: RuleContext):
        return utils.compare(self.op, ctx.torrent.ratio, self.value)


@register_condition
class UploadSizeCondition(BaseCondition):
    """总上传大小条件, 如 '>10GiB'"""
    name = "upload_size"

    def __init__(self, spec):
        self.op, self.value = utils.parse_compare(str(spec), utils.parse_fsize)

    def match(self, ctx: RuleContext):
        return utils.compare(self.op, ctx.torrent.uploaded, self.value)


class _UploadDeltaCondition(BaseCondition):
    """周期上传增量条件基类: 基于 QbManager 维护的快照, 取 max(0, 增量)"""
    kind = ""  # daily / weekly / monthly

    def __init__(self, spec):
        self.op, self.value = utils.parse_compare(str(spec), utils.parse_fsize)

    def match(self, ctx: RuleContext):
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

    def match(self, ctx: RuleContext):
        if not self.path:
            return False
        try:
            free = shutil.disk_usage(self.path).free
        except OSError:
            return False
        return utils.compare(self.op, free, self.value)
