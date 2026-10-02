"""TrackerModule: tracker 配置匹配服务 + 单种限速(plan kernel-module-refactor P3)

匹配知识从 TrackerMixin 迁入本模块, 经 ctx.trackers 服务暴露(决策点 D3: 规则上下文与
全量轮重匹配都要用, 服务化避免事件回传的时序绕弯)。全量轮重匹配改订阅 full_round 相位
(plan §4.2) —— 内核只报「全量轮」这个时机, 重匹配是模块认领的事(内核知道「何时」,
不知道「何事」)。

!client 经 ctx.api.client **现取**(不缓存): 重连换客户端时 QbApi.bind 同步更新
  (manager.client setter 的同步链), 模块侧永远拿到当前客户端。
!apply(plan 26-10-03-0436 Step 1)只做重绑: trackers 段整段变化时把存量记录的
  tracker_conf 立即重匹配到当前配置 —— L2 重建判据只比较绑定三元组(domains/rules/groups),
  hr_check / hr 等派生与配置值类字段的变化不触发重建, full_round 又只补 tracker_conf
  is None 的记录; 存量记录不重绑就永远指向旧配置对象, 判定入口(hr_judgement / 锚点收集)
  读到 hr_check=None 恒走「站点未接入」本地兜底。段相等即短路; qB 断开跳过(留给下轮
  full_round / L2 兑现); 重绑是纯内存 O(存量数), tracker_urls 走惰性缓存零 qB API 调用。
"""
import logging
from typing import Optional

from qbittorrentapi import Client

from ...config import TrackerConfig
from ...infra import utils
from ...torrents import TorrentRecord
from ..module import AppContext, ApplyResult, BaseModule

logger = logging.getLogger(__name__)


class TrackerModule(BaseModule):
    """tracker 模块: sections 认领 trackers 段; 匹配/限速每轮现读配置, apply 段变即重绑存量记录"""

    name = "tracker"

    def __init__(self, ctx: AppContext) -> None:
        self._ctx = ctx

    def sections(self) -> tuple[str, ...]:
        return ("trackers", )

    # ---------- 热重载(plan 26-10-03-0436 Step 1: trackers 段变化立即重绑存量记录) ----------

    def apply(self, old, new) -> ApplyResult:
        if old.trackers == new.trackers:
            return ApplyResult(self.name)
        if self._ctx.api.client is None:  # qB 断开: match 无从取 URLs, 留给下轮 full_round / L2 兑现
            return ApplyResult(self.name)
        n = 0
        for rec in self._ctx.store.by_hash.values():
            if rec.tracker_conf is not None:
                rec.tracker_conf = self.match(rec)
                n += 1
        return ApplyResult(self.name, f"rebound {n}")

    # ---------- 相位订阅(plan §4.2 full_round + torrents_added) ----------

    def subscribe(self, phases) -> None:
        phases.on("full_round", self._on_full_round)
        phases.on("torrents_added", self._on_torrent_added)

    def _on_full_round(self, event) -> None:
        """全量轮重匹配: 热重载 L2 置空的 tracker_conf 在此兑现(存量记录不走 added 分支,
        事件分派/维护任务都依赖 conf 已就位) —— 原 _refresh_torrents 全量轮循环随迁"""
        for rec in self._ctx.store.by_hash.values():
            if rec.tracker_conf is None:
                rec.tracker_conf = self.match(rec)

    def _on_torrent_added(self, event) -> None:
        """逐新增种子管线的「限速」一步(plan §4.2; P5 收口前经内核委托调用):
        tracker_conf 由内核 added 循环先行匹配, 这里只消费"""
        torrent = self._ctx.store.get(event.payload["hash"])
        if torrent is None:
            return
        self.apply_speed_limit(torrent, torrent.tracker_conf, event.payload.get("dry_run", False))

    # ---------- 能力服务(plan §3.2: ctx.trackers.match, rules / store 都消费) ----------

    def match(self, torrent: TorrentRecord) -> Optional[TrackerConfig]:
        """根据种子的 tracker URLs 按 hostname 精确匹配配置中的 tracker(含子域名)

        与规则绑定(utils.match_tracker_confs)同语义, 避免子串误匹配(如配置 hhanclub.net
        误匹配 fakehhanclub.net)。返回第一个匹配的 TrackerConfig, 若无匹配则返回 None;
        匹配到多个 tracker 配置时打印 WARNING 日志(仍返回第一个; 配置歧义的自动降级,
        非未预期异常)。
        """
        client: Optional[Client] = self._ctx.api.client
        confs = utils.match_tracker_confs(self._ctx.config.trackers, torrent.tracker_urls(client))
        if len(confs) > 1:
            desc = ", ".join(f"{c.name}({', '.join(c.domains)})" for c in confs)
            logger.warning(f"种子匹配到多个 tracker 配置, 使用第一个: {desc} {torrent.log_repr}")
        return confs[0] if confs else None

    # ---------- 单种限速(added 管线的 tracker 认领项, 经 torrents_added 相位调用) ----------

    def apply_speed_limit(self, torrent: TorrentRecord, tracker_conf: TrackerConfig, dry_run: bool) -> None:
        self._apply_single_speed_limit(torrent, "torrents_set_upload_limit", tracker_conf.upload_speed_limit, dry_run)
        self._apply_single_speed_limit(
            torrent, "torrents_set_download_limit", tracker_conf.download_speed_limit, dry_run
        )

    def _apply_single_speed_limit(self, torrent: TorrentRecord, api_method: str, value: int, dry_run: bool):
        """应用单个速度限制"""
        if "upload" in api_method:
            current_limit = torrent.up_limit
            direction = "上传"
        else:
            current_limit = torrent.dl_limit
            direction = "下载"

        if current_limit == value:
            return

        # 不覆盖单数值
        if utils.is_manual_speed_limit(current_limit):
            return

        if not dry_run:
            getattr(self._ctx.api, api_method)(torrent_hashes=torrent.hash, limit=value)

        logger.info(f"维护 {torrent.log_repr} | 设置{direction}限速: {utils.fmt_speed(value)}")
