"""WebviewMixin: WEB UI 视图**构建器**(分组/单种子/追剧/平铺视图 + 搜索索引)

从 qbmanager.py 拆出(2026-09-15 大文件拆分批次一)。2026-09-20 二次拆分后本模块只留
**构建**: 每个 `_build_*` 都是纯读(读 store / config 产出 dict), 不碰快照、版本号与锁 ——
那些归 `web_runtime.WebUIRuntime`(门面), 由它调本模块的构建器并在同一临界区内发布。

!新增视图必须挂进 `WebUIRuntime._publish_locked`, 不要在调用点各建一份: 四份视图共用
一个版本号回传, 漏建一份会让前端把陈旧数组当成新数据换上去(2026-09-18 实测事故)。

依赖的宿主属性:
- self.store                种子数据层 TorrentStore(分组索引/by_hash/视图脏标记)
- self.client               qB 原始客户端(搜索索引拉取文件列表用)
- self.web                  WebUIRuntime(快照 / 脏标记 / 搜索索引 / 命令投递)
"""
from typing import TYPE_CHECKING, Dict, List, Optional, Tuple

from qbittorrentapi import TorrentState, TrackerStatus

from ..hr.resolve import safety_display
from ..infra.utils import VIRTUAL_TRACKER_PREFIXES
from ..torrents import TorrentRecord

if TYPE_CHECKING:
    from ..core.tvshows import ParsedRelease

from .views_common import (
    ERROR_REASON_TTL,
    SEARCH_INDEX_BUILD_BUDGET,
    SITE_ALERT_MSG_MAX,
    SITE_ALERT_NO_CONF,
    SITE_ALERT_NO_CONF_TEXT,
    SITE_ALERT_TRACKER,
    TRACKER_DEBOUNCE_WINDOW,
    TRACKER_HEALTH_BUDGET,
    TRACKER_HEALTH_TTL,
    TRACKER_LIT_TTL,
    TRACKER_SUSPECT_TTL,
    VIEW_ARRAYS,
    _ETA_SENTINEL,
    _SEARCH_SEP_RE,
    _SHOW_STATE_RANK,
    _SHOW_STATE_RANK_LAST,
    _TRACKER_ERROR_STATUSES,
    _VIRTUAL_TRACKER_PREFIXES,
    _parse_query,
    _search_norm,
    logger,
)
from .views_episodes import EpisodesMixin
from .views_group import GroupMixin
from .views_relocate import member_relocate
from .views_row import RowMixin
from .views_search import SearchMixin


class WebviewMixin(GroupMixin, RowMixin, EpisodesMixin, SearchMixin):
    @staticmethod
    def state_kind(rec: TorrentRecord) -> str:
        """状态语义分类(前端着色): 错误红/校验蓝/下载蓝/做种绿/暂停灰/移动中紫/其它

        注意 is_stopped 须先于 is_downloading/is_uploading 判定: 暂停的种子
        (stoppedDL/stoppedUP)同时命中下载/做种类别, 暂停态优先展示。

        !MOVING/ALLOCATING 必须**显式判**, 不能靠上面的谓词: qbittorrent-api 的
          TorrentState 里这两个成员**不属于任何谓词集合**(is_downloading/is_uploading/
          is_complete/is_checking/is_errored/is_stopped 全都不含), 走到最后一行会被兜底
          成 "other" ⇒ 前端显示"其他"。          这是上游设计而非缺陷, 所以补的分类只写在这里, **不得去 patch 第三方枚举**。
          两者都归类为 moving: ALLOCATING(分配存储)当前版本 qB 已不再产出
          (qB v5.3.0 源码全文无此符号; libtorrent allocating=6 也已被 ABI v1 标弃用),
          仅在回连旧版 qB 时才可能出现; 它同属"qB 在动磁盘、不传输"的合成态, 合流进来
          最坏也只是显示成"移动中"而不是"其他"。
        """
        e = rec.state_enum
        if e.is_errored:
            return "error"
        if e.is_checking:
            return "checking"
        if e is TorrentState.MOVING or e is TorrentState.ALLOCATING:
            return "moving"
        if e.is_stopped:
            return "paused"
        if e.is_downloading:
            return "downloading"
        if e.is_uploading:
            return "seeding"
        return "other"

    @staticmethod
    def _error_reason(rec: TorrentRecord) -> str:
        """错误状态种子的**具体原因**(前端状态列据此替代笼统的"错误"; 非错误状态返回空串)

        - missingFiles: 状态本身即原因(文件丢失), 不依赖任何 API
        - error: 主循环预取的 tracker 报错文本(如 "torrent not registered with this
          tracker"); 取不到时(纯磁盘/IO 错误, 或预取尚未跑到)回退状态文本"错误"

        取数单点: 前端只展示这里的字符串, 不得在 JS 里按 state 猜原因(与 HR 标签同约定)。
        """
        e = rec.state_enum
        if e is TorrentState.MISSING_FILES:
            return "文件丢失"
        if e is TorrentState.ERROR:
            return rec.tracker_error_msg or "错误"
        return ""

    def _relocate_snapshot(self):
        """主循环发布的只读 job 快照(relocate 关 / 模块缺失 / 无 job => None)

        构建期只取引用, 不遍历任何 job 表(plan 26-11-04-1042 P0-1)。
        """
        ctx = getattr(self, "ctx", None)
        conf = getattr(getattr(ctx, "config", None), "relocate", None)
        if not getattr(conf, "enabled", False):
            return None
        mod = getattr(ctx, "relocate", None)
        getter = getattr(mod, "jobs_snapshot", None)
        return getter() if callable(getter) else None

    def _relocate_member(self, torrent_hash: str) -> Optional[dict]:
        """成员/种子页条目的迁移标注(快照 O(1) 查找; 无 job => None)"""
        snap = self._relocate_snapshot()
        job = snap.job_for(torrent_hash) if snap is not None else None
        return member_relocate(job, torrent_hash)

    @staticmethod
    def _fetch_tracker_error(rec: TorrentRecord, client) -> Optional[str]:
        """从 tracker 列表提取报错文本(取第一条非空错误 msg)

        返回三态(与"没报错"必须可分, 否则取数失败会被当成"恢复"把图标灭掉):
        - `None` 取不到(qB 断连 / 异常) —— 调用方不动现值, 只推进 TTL 时间戳
        - `""`   取到了且无报错
        - 非空串 取到了, 该站点 tracker 报错

        虚拟条目(DHT/PeX/LSD)跳过 —— 其 msg 与真实站点无关。单条拉取失败不阻塞整体,
        下个 TTL 周期自然重试。
        """
        try:
            entries = client.torrents_trackers(rec.hash) or []
        except Exception as e:
            logger.debug(f"读取 tracker 状态失败({rec.log_repr}): {e}")
            return None
        for t in entries:
            if str(t.get("url") or "").startswith(_VIRTUAL_TRACKER_PREFIXES):
                continue
            if t.get("status") in _TRACKER_ERROR_STATUSES and (t.get("msg") or "").strip():
                return t["msg"].strip()
        return ""

    @staticmethod
    def _tracker_health_due(rec: TorrentRecord, is_error_state: bool) -> float:
        """该记录下次允许观测的时刻(TTL 分档)

        - 疑似 -> TRACKER_SUSPECT_TTL(30s 后复查确认, 去抖的复查频率靠它而非轮转)
        - 已亮 -> TRACKER_LIT_TTL(60s 探恢复)
        - 其余 -> TRACKER_HEALTH_TTL(常规全库轮转); error 态种子另受 ERROR_REASON_TTL 约束
          (展示原因 300s 重取, 与改造前行为一致) —— 取两者中更早的那个
        """
        if rec.tracker_suspect_since:
            return rec.tracker_health_ts + TRACKER_SUSPECT_TTL
        if rec.tracker_health_msg:
            return rec.tracker_health_ts + TRACKER_LIT_TTL
        due = rec.tracker_health_ts + TRACKER_HEALTH_TTL
        if is_error_state:
            due = min(due, rec.tracker_error_ts + ERROR_REASON_TTL)
        return due

    def _observe_tracker_health(self, rec: TorrentRecord, client, now: float, changed: set) -> None:
        """单次 /trackers 观测 -> 写 error 态展示原因 + 健康状态机(同一份 msg, 两个消费方)

        去抖状态机(计划 §3.2, 按**墙钟**不按观测次数):
          无报错        -> 清 health_msg 与 suspect_since(恢复即灭)
          有报错·首次   -> 只置 suspect_since(不亮), 调度器 30s 后复查
          有报错·满窗   -> 写 health_msg(亮)并清 suspect_since, 此后按 60s 复查等恢复
          有报错·已亮   -> 保持已亮(报错文本变了就换), 不回疑似去抖循环
          有报错·未满窗 -> 不动, 等下次复查
        取数失败(None): 不动任何现值 —— 只保留本次已推进的 TTL 时间戳。

        不变量(issue 26-11-07-0536): 疑似与已亮**互斥** —— 亮灯即清 suspect_since,
        已亮记录由此落入 _tracker_health_due / refresh_tracker_health 的 LIT_TTL(60s)
        分档。修复前 health_msg 非空 ⟹ suspect_since 非零, suspect 分支把已亮记录吃进
        SUSPECT_TTL(30s)档, buckets[1] 恒不可达(/trackers 请求量对已亮记录翻倍)。
        """
        rec.tracker_health_ts = now
        is_err = self.state_kind(rec) == "error"
        if is_err:
            rec.tracker_error_ts = now  # 先记时间戳: 拉取失败也不在 TTL 内反复重试
        msg = self._fetch_tracker_error(rec, client)
        if msg is None:
            return  # 取不到: 现值不动(断连/异常不等于"恢复")
        if is_err and msg != rec.tracker_error_msg:
            rec.tracker_error_msg = msg
            changed.add(rec.hash)
        if not msg:
            if rec.tracker_health_msg or rec.tracker_suspect_since:
                rec.tracker_health_msg = ""
                rec.tracker_suspect_since = 0.0
                changed.add(rec.hash)
            return
        if rec.tracker_health_msg:
            # 已亮且仍报错: 保持已亮(报错文本变了就换), 不回疑似去抖循环 —— 否则每次复查
            # 都重走 30s 去抖, 已亮分档(LIT_TTL)失效
            if msg != rec.tracker_health_msg:
                rec.tracker_health_msg = msg
                changed.add(rec.hash)
            return
        if not rec.tracker_suspect_since:
            rec.tracker_suspect_since = now  # 首次疑似: 不亮, 30s 后复查确认
            return
        if now - rec.tracker_suspect_since < TRACKER_DEBOUNCE_WINDOW:
            return  # 未满窗: 等下次复查
        # 满窗确认 -> 亮灯, 同时清疑似起点(疑似与已亮互斥, issue 26-11-07-0536): 已亮记录
        # 由此落入 LIT_TTL(60s)分档, 而非被 suspect 分支吃进 SUSPECT_TTL(30s)
        rec.tracker_health_msg = msg
        rec.tracker_suspect_since = 0.0
        changed.add(rec.hash)

    def refresh_tracker_health(self) -> None:
        """主循环调用: 统一的 tracker 健康取数器(error 态展示原因 + 站点 chip 健康图标)

        扫描范围: 活跃态(seeding / downloading / checking)+ error 态; paused / other 跳过
        (暂停种子不会汇报, 报错文本无意义)。
        预算分配顺序(计划 §3.2): 疑似 -> 已亮 -> error 态 -> 全库轮转。前三类数量有界
        (通常几十个), 余下预算推进全库 —— 靠"取过就推 TTL"自然推进游标, 不另存游标:
        每轮把所有到期记录按桶序取前 TRACKER_HEALTH_BUDGET 条, 取过的下轮不再到期。

        记录离开 error 态时清空展示原因缓存 —— 否则恢复做种后仍挂着旧原因。

        原因/健康都不是快照字段, `store.view_changed` 覆盖不到, 故变化时显式置
        `web.group_view_dirty`(与"由配置派生的展示值"同一判别法: 种子数据一字未变时该值也会变),
        并按**行级归约**接线增量时间线(note_error_reason_hashes 登记, 落代前并入 torrent/
        group 桶 upsert), 不走 full 降级 —— delta 客户端本代即拿到这些行的新值。

        plan 26-10-19-2007 S1: 由 refresh_error_reasons 改造而来(ERROR_REASON_BUDGET 退役,
        预算/分档 TTL 见模块常量)。
        """
        client = self.client
        if client is None:
            return  # qB 断开: 无 API 可用, 保持现值待连接恢复后刷新
        now = self._clock.now()  # 宿主 = QbManager, _clock 为 core 域注入的取时单点(D8)
        changed: set = set()  # 本轮改写了行级展示派生字段的行(行级脏)
        buckets: Tuple[List, List, List, List] = ([], [], [], [])  # 0 疑似 / 1 已亮 / 2 error 态 / 3 全库轮转
        for rec in self.store.by_hash.values():
            kind = self.state_kind(rec)
            is_err = kind == "error"
            # 原因自明 / 已离开错误态: 展示原因**立刻**清掉(不依赖 TTL —— 否则恢复做种后
            # 仍挂着旧原因)。missingFiles 的原因由状态本身给出("文件丢失"), 不是 tracker 的错。
            if (not is_err or rec.state_enum is TorrentState.MISSING_FILES) and rec.tracker_error_msg:
                rec.tracker_error_msg = ""
                rec.tracker_error_ts = 0.0
                changed.add(rec.hash)
            if is_err and rec.state_enum is TorrentState.MISSING_FILES:
                continue  # 不取数、不点健康图标(文件丢失不是站点问题)
            if not is_err and kind not in ("seeding", "downloading", "checking"):
                # paused / moving / other: 不扫描(这些状态不会汇报, 报错文本无意义)。
                # !moving 是靠**不在上面的集合里**才被跳过的 —— 恰好正确(qB 搬迁期间 tracker
                #   不可达, 扫了只会误判站点异常), 但属于"撞对"而非"写死": 将来往那个元组里
                #   加任何一项都可能连 moving 一起带进去。动这个元组时回想一下这句话。
                # 健康态保留 —— 暂停期间没有观测证据, 不拿"没看"当成"好了"。
                continue
            if now < self._tracker_health_due(rec, is_err):
                continue  # 未到期: 直接复用现值
            if rec.tracker_suspect_since:
                buckets[0].append(rec)
            elif rec.tracker_health_msg:  # 已亮(suspect 已清, 与疑似互斥): LIT_TTL 分档
                buckets[1].append(rec)
            elif is_err:
                buckets[2].append(rec)
            else:
                buckets[3].append(rec)
        budget = TRACKER_HEALTH_BUDGET
        for bucket in buckets:
            if budget <= 0:
                break
            for rec in bucket:
                if budget <= 0:
                    break  # 本轮预算用尽: 余下种子下一轮续取
                budget -= 1
                self._observe_tracker_health(rec, client, now, changed)
        if changed:
            self.web.mark_dirty()
            self.web.note_error_reason_hashes(changed)

    @staticmethod
    def _site_alert(rec: TorrentRecord) -> Tuple[str, str]:
        """站点 chip 左槽的持久健康告警 -> (site_alert, site_alert_msg)

        判定单点(前端只展示这里给出的字符串, 不得在 JS 里按 state 猜):
        - `no_site_conf`: 有真实 tracker 但 tracker_conf is None(站点未配) —— 该种子后续限速 /
          HR / 规则全部不生效, 属于静默降级, 比报错更根本, 故优先
        - `tracker_error`: 该站点 tracker 已确认报错(去抖后), msg 为报错原文(截断)
        - `""`: 健康 / 不适用(纯 DHT/磁力无真实 tracker 不算缺配置)
        """
        if rec.tracker_conf is None:
            url = rec.tracker or ""
            if url and not url.startswith(_VIRTUAL_TRACKER_PREFIXES):
                return SITE_ALERT_NO_CONF, SITE_ALERT_NO_CONF_TEXT
            return "", ""
        if rec.tracker_health_msg:
            return SITE_ALERT_TRACKER, rec.tracker_health_msg[:SITE_ALERT_MSG_MAX]
        return "", ""

    @staticmethod
    def hr_view_fields(rec: TorrentRecord) -> dict:
        """该成员的 HR 展示字段(标签文本 + 要求/达成布尔 + 三态与依据), 供前端渲染 H&R 栏与对照列

        - hr_tag / hr_tag_done: 已触发未达标 / 已达标时应有的标签(供前端按文本着色)
        - hr_triggered / hr_satisfied: 本机下载条件满足(展示辅助, 区分「本机下载」与「疑似辅种」;
          管理语义在 hr_managed, 不再由本字段表达) / 是否已达成要求
        - hr_excluded: 是否命中 HR 排除表(计划 26-09-28-1805) —— True 时触发/达标恒 False、
          站点侧字段全空, 前端在做种时长列的悬停弹窗里提示(2026-09-29 起撤掉行内「已排除」徽标,
          与来源标记同批非文字化; 不得在 JS 里重算匹配, 只消费本布尔)
        - hr_excluded_by: 排除命中来源 token("tag" / "category" / "tag+category", 未命中 = ""),
          供弹窗依据行说明「按什么排除」—— 匹配单点在 record.hr_excluded_by, 前端只映射文字
        - hr_req_time: 要求做种时长(秒) = required_total_seeding_time(req + extra)
        - hr_req_ratio: 要求分享率(0 = 不要求)
        - hr_state / hr_state_text / hr_reason: 站点侧判定(hr / verified_non_hr / unknown /
          exempt=超龄豁免) + 中文说法 + 依据; 接入站点才非空(未接入 = "", 前端据此不显示三态行)
        - hr_safety / hr_safety_text / hr_safety_src: 删除安全档位(danger/failed/safe/warning/none,
          failed = 未达标终态红档, 2026-09-25 用户修正; warning = 本地未达标且疑似辅种黄档,
          计划 26-09-30-0559) + 含来源的人话短语 + 来源档位 token —— 派生单点在
          hr.resolve.safety_display(不新造判定, 只转译既有结论); 站点未配 HR 全空串(前端整列
          不显示), 命中排除表同样短路成空串(「不适用」空白由组装层保证)
        - hr_site_lane / hr_site_need / hr_site_remain / hr_site_ratio / hr_site_dl: 命中行的
          **站点侧值**(档位 / 还需做种 / 剩余达标 / 分享率 / 下载量) —— 与本地实时值对照用:
          本地值实时但会被重加/转移清零, 站点值是账号级权威但滞后一个刷新周期(计划 §9)
          未命中/未接入一律空串 ""(未知与 0 必须可分: `hr_site_remain == 0` 是"已达标")

        判定委托 TorrentRecord.check_hr_condition/check_hr_satisfied, 标签文本经
        utils.replace_vars 解析 ${required_seeding_time}, 与维护流程(打 HR 标签)完全同源 ——
        前端只做展示比较, 不得在 JS 里重算模板或阈值(否则自定义标签格式/阈值会立即失效)。
        未配置 HR 站点返回全空值(前端据此整列显示"—"), 不做 None 防御(早暴露配置匹配错误)。
        """
        from ..infra import utils as _utils

        conf = rec.tracker_conf
        hr = conf.hr if conf is not None else None
        if hr is None:
            return {
                "hr_tag": "",
                "hr_tag_done": "",
                "hr_triggered": False,
                "hr_satisfied": False,
                "hr_excluded": False,
                "hr_excluded_by": "",
                "hr_req_time": 0,
                "hr_req_ratio": 0.0,
                "hr_state": "",
                "hr_state_text": "",
                "hr_reason": "",
                "hr_safety": "",
                "hr_safety_text": "",
                "hr_safety_src": "",
                "hr_site_lane": "",
                "hr_site_need": "",
                "hr_site_remain": "",
                "hr_site_ratio": "",
                "hr_site_dl": "",
            }
        # 排除态在组装层短路成空串(计划 26-09-30-0559 §5): safety_display 的 None 分支无法区分
        # 「排除」与「未接入」, 排除种子维持「不适用」空白必须由这里保证。
        # excluded_by 与 excluded 同源一次算出(来源 token 给弹窗依据行, 前端不重算匹配)
        excluded_by = rec.hr_excluded_by()
        excluded = bool(excluded_by)
        triggered = rec.check_hr_condition()
        # v3: satisfied 独立于 triggered —— 命中 B(终态放行)不再受管束但达标结论成立(毕业)
        satisfied = rec.check_hr_satisfied()
        judged = rec.hr_judgement()  # 站点未接入返回 None(下面四个字段留空)
        facts = judged.facts if judged is not None else None
        # 排除态在组装层短路成空串(计划 26-09-30-0559 §5): safety_display 的 None 分支无法区分
        # 「排除」与「未接入」, 排除种子维持「不适用」空白必须由这里保证。
        safety = None if excluded else safety_display(judged, triggered=triggered, satisfied=satisfied)
        fields = {
            "hr_tag":
                "",
            "hr_tag_done":
                "",
            "hr_triggered":
                triggered,
            "hr_satisfied":
                satisfied,
            "hr_excluded":
                excluded,
            "hr_excluded_by":
                excluded_by,
            "hr_req_time":
                hr.required_total_seeding_time,
            "hr_req_ratio":
                hr.required_share_ratio,
            "hr_state":
                judged.identity.value if judged is not None else "",
            "hr_state_text":
                judged.state_text if judged is not None else "",
            "hr_reason":
                judged.reason if judged is not None else "",
            "hr_safety":
                safety.safety if safety is not None else "",
            "hr_safety_text":
                safety.text if safety is not None else "",
            "hr_safety_src":
                safety.src if safety is not None else "",
            "hr_site_lane":
                facts.lane if facts is not None else "",
            "hr_site_need":
                facts.need_seed_seconds if facts is not None and facts.need_seed_seconds is not None else "",
            "hr_site_remain":
                facts.remain_seconds if facts is not None and facts.remain_seconds is not None else "",
            "hr_site_ratio":
                facts.ratio if facts is not None and facts.ratio is not None else "",
            "hr_site_dl":
                facts.downloaded_bytes if facts is not None and facts.downloaded_bytes is not None else "",
        }
        if triggered:
            if satisfied:
                fields["hr_tag_done"] = _utils.replace_vars(hr.add_tag_for_satisfied, conf)
            else:
                fields["hr_tag"] = _utils.replace_vars(hr.add_tag, conf)
        return fields

    def build_search_index(self) -> None:
        """主循环线程调用: 增量构建搜索索引(hash -> {name, files[文件名], files_q[归一文件名]}), 单次限流拉取。

        **原子交换契约**: 每轮在**新字典**上重组(消失的种子不进新字典即淘汰), 完成后整体替换
        `_search_index` 引用 —— 绝不就地增删旧字典, 否则 Web 线程正在迭代时会抛
        "dictionary changed size during iteration"。已建条目只刷新名称(值替换不改结构, 并发只读安全),
        新种子拉取文件列表(rec.files 惰性拉取 + 记录 _files 跨 tick 缓存, 只在主循环线程), 单条失败
        跳过(该 hash 不进新字典, 保持脏由下轮续建重试 —— 不把空文件列表当正式条目缓存)不阻塞整体。
        限流: 单次最多拉取 SEARCH_INDEX_BUILD_BUDGET 条, 未拉完保持 web.search_index_dirty=True,
        由后续调用(下一 tick 推进 / 前端据 building 重查投递)续建 —— 避免首轮 N 次 API 长时间阻塞主循环。
        """
        if self.client is None:
            # qB 断开中: 无文件 API 可用, 保持脏待连接恢复后重建(不能把空文件列表当成"已建完")
            self.web.search_index_dirty = True
            return
        prev = self.web.search_index if self.web.search_index is not None else {}
        idx: dict = {}
        budget = SEARCH_INDEX_BUILD_BUDGET
        added = 0  # 本轮新增条目数(追剧视图文件兑底的重建触发依据)
        fetch_failed = False  # 本轮有文件拉取失败: 失败 hash 不进索引, 保持脏下轮重试
        for h, rec in self.store.by_hash.items():
            entry = prev.get(h)
            if entry is not None:
                entry["name"] = rec.name
            elif budget > 0:
                budget -= 1
                try:
                    files = [f.name for f in rec.files(self.client)]
                except Exception:
                    # 拉取失败(issue 26-11-07-0536): 该 hash 不进新字典 —— 不把空文件列表当
                    # 正式条目缓存(修复前 files=[] 永久生效, 文件兑底与文件行搜索失效到重启);
                    # 下轮续建时该 hash 仍是"新种子", 自然重试
                    fetch_failed = True
                    continue
                added += 1
                entry = {"name": rec.name, "files": files, "files_q": [_search_norm(f) for f in files]}
            else:
                # 预算用尽: 剩余种子本轮不进新字典(下次调用续建), 保持脏
                self.web.search_index = idx
                self.web.search_index_dirty = True
                self._trigger_shows_rebuild_if_pending(added)
                return
            idx[h] = entry
        self.web.search_index = idx
        self.web.search_index_dirty = fetch_failed  # 有失败: 保持脏(待重试), 全部成功才视为已建完
        self._trigger_shows_rebuild_if_pending(added)

    def _group_hashes(self, key: tuple) -> List[str]:
        return [h for h in self.store.groups.get(key, []) if h in self.store.by_hash]
