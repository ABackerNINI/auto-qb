"""视图公共层: 常量 / 解析排序归一化 helper / logger(从 views.py 拆出, 仅搬移)"""

import logging
import re
from typing import List, Tuple

from qbittorrentapi import TorrentState, TrackerStatus

from ..infra.utils import VIRTUAL_TRACKER_PREFIXES

logger = logging.getLogger("auto_qb.webui.views")

SEARCH_INDEX_BUILD_BUDGET = 500  # 搜索索引单次构建最多拉取的文件列表数(限流, 避免首轮 N 次 qB API 阻塞主循环)

# 搜索匹配口径: 种子名/文件名是 scene 命名(点/下划线/连字符等作分隔), 查询词却以空格分词 ——
# 裸子串匹配时 "cat and" 对不上 "The.Cat.and…"。两侧统一把非文字字符折叠为单空格再匹配;
# 下划线属 \w 须显式并入折叠集, \w 保留 Unicode 文字(CJK 名称可搜)。
_SEARCH_SEP_RE = re.compile(r"[\W_]+")


def _search_norm(s: str) -> str:
    """搜索匹配归一: 分隔符折叠为单空格 + 小写 + 去首尾空 —— 查询词与种子名/文件名配对使用"""
    return _SEARCH_SEP_RE.sub(" ", s).lower().strip()


def _parse_query(q: str) -> Tuple[List[str], List[str]]:
    """搜索查询解析(宽容, 永不报错): 返回 (正词, 负词), 词均为 _search_norm 归一后的子串口径。

    语法(websearch 惯例, 调研报告 26-09-26-1918 §5): 空格分词隐式 AND; 词首单个 `-`(后随非空白)
    为排除; `"…"` 短语整段归一为**连续**子串(可含空格), `-"…"` 排除短语; 其余宽容 —— 孤立 `-`
    忽略, 未闭合引号收至行尾, 词中引号无特殊含义(随归一折叠), 纯标点 token 丢弃。
    词法判定在**原始查询**上进行, 与归一化互不干扰: `-DV` 切词阶段即识别为负词; `web-dl` 不以
    `-` 开头是正词(scene 命名里的连字符经归一折叠为空格, 不会被误判成排除符)。
    """
    pos: List[str] = []
    neg: List[str] = []
    i, n = 0, len(q)
    while i < n:
        if q[i].isspace():
            i += 1
            continue
        negative = q[i] == "-" and i + 1 < n and not q[i + 1].isspace()
        if negative:
            i += 1
        if i < n and q[i] == '"':
            j = q.find('"', i + 1)
            raw = q[i + 1:(n if j == -1 else j)]
            i = n if j == -1 else j + 1
        else:
            j = i
            while j < n and not q[j].isspace():
                j += 1
            raw = q[i:j]
            i = j
        term = _search_norm(raw)
        if term:
            (neg if negative else pos).append(term)
    return pos, neg


# tracker 健康取数(计划 26-10-19-2007 S1): qB torrents/info **不含**错误文本, 报错原因与站点
# 健康都只能从 torrents/trackers 的 msg 取。**一个取数入口、两个消费方**:
#   1. error 态种子的展示原因(状态列"错误"背后的具体原因, ERROR_REASON_TTL 控制重取间隔)
#   2. 站点 chip 左槽的健康图标(缺配置 / tracker 报错, 见 site_alert)
# 两套机制共用同一次 /trackers 调用 —— 否则 error 态种子会被各查一次(计划 §3.2 aside)。
# !qB **无批量接口**, 只能逐种子 GET /torrents/trackers; 故全库轮转靠预算 + TTL 摊开。
TRACKER_HEALTH_BUDGET = 20  # 每 tick 最多发起的 /trackers 请求数(S0 实测 0.38ms/次 -> 20 条约 7.5ms, 占 1.5s tick 的 0.5%)
TRACKER_HEALTH_TTL = 600.0  # 常规全库轮转周期(5000 种子 × tick 2s / 20 ≈ 500s 扫完一轮 < TTL)
TRACKER_SUSPECT_TTL = 30.0  # 疑似(首次观测到报错、未确认)的复查间隔 —— 去抖靠它, 不靠轮转自然覆盖
TRACKER_LIT_TTL = 60.0  # 已亮(确认报错)的恢复检测间隔(恢复即灭, 60s 内可发现)
# 去抖窗口(墙钟): 首次观测只置疑似, 满窗后复查仍报错才亮。
# !不能写成"连续 2 次观测": 常规 TTL 600s 下两次观测相隔 20 分钟, 去抖等于没有(计划 R1)。
TRACKER_DEBOUNCE_WINDOW = 30.0
# error 态种子展示原因的重取间隔(秒): tracker msg 随站点状态变化, 过期重取。行为与改造前一致。
ERROR_REASON_TTL = 300.0
# "tracker 报错"状态集合(qB TrackerStatus): 4=not working / 5=tracker error / 6=unreachable
_TRACKER_ERROR_STATUSES = frozenset(
    int(s) for s in (TrackerStatus.NOT_WORKING, TrackerStatus.TRACKER_ERROR, TrackerStatus.UNREACHABLE)
)
# 虚拟 tracker 条目(DHT/PeX/LSD, 非真实站点): 与强制汇报确认同一口径, 不参与报错文本提取
# 单点定义在 infra/utils(与 mask 的 R1 透传共用, 消双源, 计划 26-10-07-0055 S1)
_VIRTUAL_TRACKER_PREFIXES = VIRTUAL_TRACKER_PREFIXES

# 站点健康告警的取值域(前端只消费字符串 + 符号, 不在 JS 里按 state 猜原因):
#   ""            健康 / 不适用
#   "no_site_conf" 该种子有真实 tracker 但配置里匹配不到站点(后续限速/HR/规则全部不生效, 静默降级)
#   "tracker_error" 该站点 tracker 确认报错(tracker_health_msg 非空)
# 优先级 no_site_conf > tracker_error: 配置缺失时连报错文本都不可信(计划 §3.1 aside)。
SITE_ALERT_NO_CONF = "no_site_conf"
SITE_ALERT_TRACKER = "tracker_error"
# 缺站点配置时的固定文案(前端 title 用; 不拼 HTML, 纯文本绑定)
SITE_ALERT_NO_CONF_TEXT = "站点未在配置中"
# site_alert_msg 截断长度(计划 R7): 站点自定义报错文案可能几百字符, 直接塞 title 会撑爆弹窗
SITE_ALERT_MSG_MAX = 200

# 集节点聚合状态优先级: 错误 > 下载 > 校验 > 做种 > 暂停 > 移动 > 其它(前端按 state 着色)
# !做种必须排在**暂停之前**: 组/集内"部分暂停部分做种中"是常态(整组只有个别站点被暂停),
#   取 paused 会让整个做种中的行变成灰的(2026-09-21 用户报"辅种页状态色错误")。
#   与前端 `shared/app.js::STATE_RANK` 逐项一致由 tests/webui_static_scan_js.py::_scan_state_rank 静态守阵机械比对。
# !moving 插在 paused 之后 other 之前, 不扰动上面这段踩过坑的相对顺序(2026-10-29 满分):
#   两者同属"非典型态", 且 moving 是强遮蔽态(qB 源码 Moving 顺位高于 MissingFiles/Error),
#   让它在争夺里压过常规态会把整组落成"正在搬", 与实际观感不符。
_SHOW_STATE_RANK = {"error": 0, "downloading": 1, "checking": 2, "seeding": 3, "paused": 4, "moving": 5, "other": 6}
# 表外 kind 的兜底秩(排最后): 与前端 `shared/app.js::STATE_RANK_LAST` 同值,
# 逐项一致由 tests/webui_static_scan_js.py::_scan_state_rank 静态守阵机械比对(issue 26-10-11-0310 补钉)。
_SHOW_STATE_RANK_LAST = 9

# P1-1 按视图回传: 每个视图实际要用的数组。四视图共享同一版本号(rid), 所以"只回一部分"
# 不会让别的视图停在旧数据上 —— 前端切视图时会把 lastRid 置空强制取一次全量。
# 键未列出 / view 为空 ⇒ 回传全部(保守默认)。
VIEW_ARRAYS = {
    # 辅种页: 分组表 + 未归组单种子 + **种子平铺数组**。singles 是同页的兜底行, 必须一起回;
    # P-02 二期(hash 引用式)后 group 行 members 也只是一串 hash(同 shows), memberByHash
    # 索引源 = singles ∪ torrents ⇒ 不回 torrents 则组行成员明细还原不出 —— 连带 torrents
    # (与 shows 视图当年连带 groups+singles 同款 ride-along 先例)
    "group": ("groups", "singles", "torrents"),
    # 种子页: 全部种子一行一条的平铺数组
    "torrent": ("torrents", ),
    # 追剧页: 剧→季→集聚合 + **成员索引**。
    # !shows 里的 members 只是一串 hash(见前端 memberByHash 注释: 明细成员经索引取, 不随 shows
    #   重复回传), 而 group 行 members 经 P-02 二期同样 hash 化 ⇒ 索引生效源 = singles ∪
    #   torrents(groups 段不再贡献明细) ⇒ 只回 shows 时前端索引为空, decoratedShows 的成员
    #   解析全部落空: **刷新后停在追剧页会得到一张永久空表**(2026-09-19 实测: groups=0 /
    #   memberByHash=0 / 0 行; 且 rid 已记住 ⇒ 后续每轮都是"版本未变不回传", 自己不会恢复,
    #   必须切一次视图)。故追剧页必须连带成员索引一起回(singles + torrents)。
    "show": ("shows", "groups", "singles", "torrents"),
}


def _ep_sort_key(nkey: tuple):
    """集节点排序键: 整季包(覆盖全季)最先, 其余按集号起点/终点; 日期桶内按日期字符串"""
    if nkey[0] == "pack":
        return (0, 0, "")
    if nkey[0] == "ep":
        return (0, nkey[1], "")
    if nkey[0] == "range":
        return (0, nkey[1], "")
    return (1, 0, nkey[1])  # date


# qB eta 哨兵: 8640000 = 无 ETA(与前端 format.js::fmtEta 口径一致; 跨层一致由
# tests/webui_static_scan_js.py::_scan_eta_sentinel 机械守阵, issue 26-10-11-0310);
# 时间点哨兵 -1/0 = 从未(fmtTs 空白)
_ETA_SENTINEL = 8640000


def _min_valid_eta(values) -> int:
    """组级剩余时间聚合: 组内**最小有效 eta**。

    依据: 下载冲突检查(_check_download_conflicts)保证同组至多一个成员在下载(两个同时下载 /
    下载中与已完成并存都会被暂停整组), 它下完其余成员经 recheck 从同一份文件直接变完成 ——
    故最小有效 eta 就是"全组下完"的时间。哨兵(8640000=无 ETA)与非正值不参与, 全无效回 0
    (前端 fmtEta 对 0 显示空白)。"""
    valid = [v for v in values if 0 < v < _ETA_SENTINEL]
    return min(valid) if valid else 0


def _max_valid_ts(values) -> int:
    """组级时间点聚合("最近活动"): 取组内最新, 哨兵(-1/0 = 从未)不参与; 全组从未回 0(前端空白)"""
    valid = [v for v in values if v and v > 0]
    return max(valid) if valid else 0
