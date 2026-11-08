"""hr 通道状态与告警 mixin(自 service.py move-only 切出)

拆分(R5)只搬位置: 方法文本与 service.py 原文件逐字一致(保留缩进与注释)。
"""
import logging
from typing import Optional

from . import events
from . import log as hr_log
from .fetcher import HrExtensionNetwork, HrExtensionNoPermission
from .model import (
    CHANNEL_DISABLED,
    CHANNEL_NETWORK,
    CHANNEL_NO_PERMISSION,
    CHANNEL_OK,
    CHANNEL_SILENT,
    HrLaneState,
    HrSiteData,
)
from .service_common import CHANNEL_SILENCE_WARN, LANE_FAIL_ALERT_STREAK, logger, warn_gap_floor


class StatusMixin:
    """通道状态与告警域方法"""
    def channel_state(self, site: str, data: Optional[HrSiteData] = None) -> str:
        """通道状态: disabled / no-permission / network / silent / ok

        `no-permission`(扩展未授权该站点)与 `network`(扩展到站点的网络不通)来自落盘的
        `channel_last_error`(计划 26-10-29-0147 W3): 它们比 `silent` **更具体**, 故先判 ——
        「长期没有健康波」只能说明"没成过", 说不出"为什么没成", 而用户要的正是后者。

        !生效条件 `ts > healthy_ts`: 痕迹只在**上一次健康波之后**才算数。否则站点恢复后,
        旧痕迹会把卡片一直标红(展示层撒谎比不展示更糟)。
        """
        if not self.global_conf.channel.enabled:
            return CHANNEL_DISABLED
        if data is None:
            data, _err = self.store(site).read_unlocked()
        last = data.channel_last_error or {}
        kind = str(last.get("kind") or "")
        try:
            last_ts = float(last.get("ts") or 0.0)
        except (TypeError, ValueError):
            last_ts = 0.0
        if kind in (CHANNEL_NO_PERMISSION, CHANNEL_NETWORK) and last_ts > data.wave.healthy_ts:
            return kind
        if data.wave.healthy_ts <= 0:
            return CHANNEL_SILENT
        if self._now() - data.wave.healthy_ts > CHANNEL_SILENCE_WARN:
            return CHANNEL_SILENT
        return CHANNEL_OK

    # ---------- 告警(升级但行为不变, §5.2) ----------

    def _reset_warned_on_recovery(self, site: str, data: Optional[HrSiteData] = None) -> None:
        """站点恢复(本波拿到正常内容页) → 清通道/额度/登录三类「已告警过」去重标记。

        「每站只报一次」的准确语义是**每次状态变化报一次**: 恢复即重置,
        下次同类事件重新告警(此前无条件在 _finish_wave 末尾清, 每波都重报)。

        `data` 给定时同点清掉落盘的通道痕(`channel_last_error`) —— 告警态与展示态**必须同一个
        恢复点**, 否则会出现「日志说恢复了、站点卡还红着」。
        """
        self._no_channel_warned.discard(site)
        self._ext_quota_warned.discard(site)
        self._login_warned.discard(site)
        self._no_perm_warned.discard(site)
        self._network_warned.discard(site)
        if data is not None and data.channel_last_error:
            data.channel_last_error = {}

    def _warn_once(
        self,
        seen: set,
        site: str,
        *,
        dup_level: int,
        dup_msg: str,
        level: int,
        msg: str,
        event: str,
        silent: bool = False
    ) -> None:
        """「每站只报一次」单点(直到状态恢复, 由 `_reset_warned_on_recovery` 清标记)。

        三个 `_warn_*` 只在这里的参数上不同: 去重集合 / 去重时的日志级别与文案 / 告警级别与事件 /
        是否静默(`silent` = 只进后端 log, 不进前端错误历史、不弹通知)。
        """
        if site in seen:
            logger.log(dup_level, dup_msg)
            return
        seen.add(site)
        hr_log.emit(logger, level, msg, event=event, silent=silent)

    def _note_channel_error(self, data: HrSiteData, err: Exception) -> None:
        """把「通道层这次为什么不通」落成站点文件里的观测事实(计划 26-10-29-0147 W2)

        只记**两种要人处置的新形态**(缺站点权限 / 网络层失败); 「等回传超时」不记 —— 它的语义
        已经由 `healthy_ts` 陈旧 + `CHANNEL_SILENT` 表达, 再写一份只会多一个会过期的副本。
        清除点在 `_reset_warned_on_recovery`(拿到正常内容页), 两处必须同点, 否则会出现
        「告警已恢复、站点卡还红着」。
        """
        kind = ""
        if isinstance(err, HrExtensionNoPermission):
            kind = CHANNEL_NO_PERMISSION
        elif isinstance(err, HrExtensionNetwork):
            kind = CHANNEL_NETWORK
        if not kind:
            return
        data.channel_last_error = {"kind": kind, "detail": str(err)[:200], "ts": self._now()}

    def _warn_no_channel(self, site: str, err: Exception) -> None:
        """无通道告警: **每个站点只报一次**(直到通道恢复)

        通道层(含「等扩展超时」)统一在此出 —— 默认标 `silent`: 只进后端 log, 不进前端错误历史、
        不弹通知(计划 §03.2/D2 1: 「连不上浏览器」是**预期内**的环境态)。

        !两个例外(计划 26-10-29-0147 D7): 「扩展未授权该站点」与「网络层失败」虽然也归通道层,
        但**不会自己好** —— 前者要人去授权、后者要人查代理。前者提级到 ERROR 且可见(它值得一次
        主动通知: 2026-10-28 的故障就是被 silent 埋了 12h); 后者维持 WARNING + silent
        (它可能只是 VPN 抖动, 恢复即消音)。
        """
        if isinstance(err, HrExtensionNoPermission):
            self._warn_once(
                self._no_perm_warned,
                site,
                dup_level=logging.INFO,
                dup_msg=f"HR 站点 {site} | 扩展仍未授权该站点(已告警过, 本波不做在线核实): {err}",
                level=logging.ERROR,
                msg=events.site_not_permitted(site, err),
                event=events.EVENT_CHANNEL,
                silent=False,
            )
            return
        if isinstance(err, HrExtensionNetwork):
            self._warn_once(
                self._network_warned,
                site,
                dup_level=logging.DEBUG,
                dup_msg=f"HR 站点 {site} | 扩展到站点的网络仍不通(已告警过, 本波不做在线核实): {err}",
                level=logging.WARNING,
                msg=events.extension_network(site, err),
                event=events.EVENT_CHANNEL,
                silent=True,
            )
            return
        self._warn_once(
            self._no_channel_warned,
            site,
            dup_level=logging.DEBUG,
            dup_msg=f"HR 站点 {site} | 无可用取数通道(已告警过, 不重复): {err}",
            level=logging.WARNING,
            msg=events.channel_unavailable(site, err),
            event=events.EVENT_CHANNEL,
            silent=True,
        )

    def _warn_login(self, site: str, err: Exception) -> None:
        """登录失效告警: **每个站点只报一次**(直到登录恢复); 文案单点在 events.login_expired"""
        self._warn_once(
            self._login_warned,
            site,
            dup_level=logging.INFO,
            dup_msg=f"HR 站点 {site} | 登录态仍未恢复(已告警过, 本轮不做在线核实): {err}",
            level=logging.ERROR,
            msg=events.login_expired(site, err),
            event=events.EVENT_LOGIN,
        )

    def _warn_parse(self, site: str, detail: str) -> None:
        """页面形态异常告警(排序/字段/表头/防伪): WARNING 按 CHANNEL_SILENCE_WARN 节流"""
        warn_gap = warn_gap_floor(CHANNEL_SILENCE_WARN)
        now = self._now()
        if now - self._parse_warned_at.get(site, 0.0) < warn_gap:
            logger.info(f"HR 站点 {site} | 页面形态异常仍存在(节流期内不重复告警): {detail}")
            return
        self._parse_warned_at[site] = now
        hr_log.emit(logger, logging.WARNING, detail, event=events.EVENT_PARSE)

    def _maybe_alert_lane_fail(self, site: str, st: HrLaneState) -> None:
        """连续多波同档失效 → ERROR 告警(§5.2 告警升级): 只提示人, 不改变取数与判定行为"""
        if st.fail_streak >= LANE_FAIL_ALERT_STREAK:
            hr_log.emit(
                logger,
                logging.ERROR,
                events.lane_persistent_failure(site, st.lane, st.fail_streak, st.detail),
                event=events.EVENT_PARSE
            )

    def _warn_ext_quota(self, site: str, err: Exception) -> None:
        """扩展侧硬上限告警: 同样**只报一次**(超限会持续到下一个窗口)

        归通道层, 但**可见**: 它意味着后端频控失效, 是需要人看一眼的真问题(§07.2 不变项:
        `HrChannelQuota` 的现有出口不变)。
        """
        self._warn_once(
            self._ext_quota_warned,
            site,
            dup_level=logging.INFO,
            dup_msg=f"HR 站点 {site} | 扩展侧硬上限仍生效(已告警过, 本波让位): {err}",
            level=logging.WARNING,
            msg=f"HR 站点 {site} | 扩展侧硬上限挡下取数(第二道闸): 多半是后端频控失效(检查 hr_check 的间隔/日额配置"
            "与日志), 也可能是扩展上限本就低于后端配额(属正常优先)",
            event=events.EVENT_CHANNEL,
        )
