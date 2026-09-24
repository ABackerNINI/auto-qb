"""HR 在线核实的运行时门面(计划 §7/§8 · M2): 端点 + 取数线程 + 视图发布 + 热重载重挂。

主循环只见这个门面(与 `WebUIRuntime` 同款): 附属线程与文件句柄的生命周期不进核心域。

启用口径:
- `hr_check.enabled=true` 且至少一个站点 `mode != off` ⇒ 建立服务与取数线程;
- 再满足 `channel.enabled=true` 才起**端点**(能力即角色) —— 没装扩展的实例仍然跑取数线程,
  但它 `allow_fetch=False`: 只读共享站点文件(别人抓的), 顺手把视图发布出来给主循环消费。
  这正是多实例分工(who 有浏览器谁抓), 也是「跨机器实例只能只读」的落地形态。

❗共享目录引导(计划 §7): 功能开启但 `shared_dir` 为空 ⇒ 记一条 INFO —— 程序**无法可靠判断
  「我是不是多实例」**, 故只引导不强求, 不阻断启动, 由用户决定是否配置。
"""
import logging
import time
from dataclasses import dataclass
from typing import Mapping, Optional, Tuple

from ..config.models import HrCheckConfig, SiteHrCheckConfig
from .channel import ChannelStatus, describe_token_source, resolve_token, token_path
from .fetcher import HrFetcher, NullFetcher, build_channel_fetcher, is_available
from .queue import HrTaskQueue
from .resolve import HrViewSet
from .server import HrChannelServer
from .service import HrRefreshService
from .store import hr_dir, instance_id
from .worker import HrViewPublisher, HrWorker

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class HrRuntimeStatus:
    """运行时自检快照(供 hr.once 报告与状态展示; 不含密钥内容)"""

    enabled: bool = False
    sites: Tuple[str, ...] = ()
    shared_dir: bool = False
    data_dir: str = ""
    sites_dir: str = ""
    writer: str = ""
    fetch_enabled: bool = False
    worker_running: bool = False
    poll_interval: float = 0.0
    view_revision: int = 0
    channel: Optional[ChannelStatus] = None
    token_path: str = ""
    token_source: str = "none"
    note: str = ""


class HrRuntime:
    """HR 在线核实的运行时(端点 + 取数线程 + 视图)"""
    def __init__(self, manager) -> None:
        self._manager = manager
        self.publisher = HrViewPublisher()
        self.queue: Optional[HrTaskQueue] = None
        self.endpoint: Optional[HrChannelServer] = None
        self.worker: Optional[HrWorker] = None
        self.service: Optional[HrRefreshService] = None
        self.fetcher: HrFetcher = NullFetcher("HR 在线核实未启动")
        self.token = ""

    # ---------- 配置读取 ----------

    @property
    def config(self):
        return self._manager.config

    @property
    def global_conf(self) -> HrCheckConfig:
        return self.config.hr_check

    def site_confs(self) -> Mapping[str, SiteHrCheckConfig]:
        return {name: tc.hr_check for name, tc in self.config.trackers.items() if tc.hr_check is not None}

    @property
    def enabled(self) -> bool:
        """是否需要这套运行时: 总开关 + 至少一个站点接入"""
        return bool(self.global_conf.enabled) and bool([c for c in self.site_confs().values() if c.enabled])

    @property
    def fetch_enabled(self) -> bool:
        """本实例是否具备抓取能力(装了扩展才为真; 否则只读共享数据)"""
        return self.enabled and bool(self.global_conf.channel.enabled)

    # ---------- 生命周期 ----------

    def start(self) -> bool:
        """按配置启动; 返回是否真的启动了。端点端口被占 ⇒ 抛 HrChannelBindError(不静默降级)"""
        self.stop()
        if not self.enabled:
            logger.debug("HR 在线核实未启用(总开关关或没有站点 mode != off), 不启动取数线程")
            return False
        self._advise_shared_dir()
        self._build()
        if self.fetch_enabled:
            assert self.endpoint is not None
            self.endpoint.start()
        if self.worker is not None:
            self.worker.start()
        sites = ", ".join(self.service.enabled_sites()) if self.service else ""
        mode = "端点 + 取数" if self.fetch_enabled else "只读共享(本实例无取数通道)"
        logger.warning(f"HR 在线核实已启动({mode}): 站点 {sites}; 站点文件目录 {self._sites_dir()}")
        return True

    def stop(self) -> None:
        """停取数线程 -> 停端点

        ⚠ 线程可能正持着站点锁等扩展回传 —— `HrWorker.stop()` 会**先叫停取数通道**再 join,
        否则一次正常关停要白等到 `channel.request_timeout`(默认 180s), 期间该站点锁死、
        进程退出也被拖住。
        """
        if self.worker is not None:
            self.worker.stop()
            self.worker = None
        if self.endpoint is not None:
            self.endpoint.stop()
            self.endpoint = None
        self.service = None

    def apply(self, old: HrCheckConfig) -> None:
        """配置热重载(L1): `channel` 段与 `shared_dir` 变了要**重挂**(先停旧、等线程退出、再启新)

        其余字段(间隔/配额/策略...)是取数线程每轮现读的 L0 项, 但服务对象把配置**按值**持有着,
        所以只要 hr_check 段有任何变化就重建服务与线程(它们无状态, 重建代价可忽略);
        端点的**监听身份**(enabled/port/extension_id/token)没变则不拆 —— 免得白白重绑端口。
        """
        new_ident = self._identity(self.global_conf)
        old_ident = self._identity(old)
        if new_ident != old_ident:
            logger.warning(f"HR 取数通道监听身份变化 {old_ident} -> {new_ident}: 重挂端点与取数线程")
            self.start()
            return
        if not self.enabled:
            # 关掉了: 收掉线程与端点(幂等)
            if self.worker is not None or self.endpoint is not None:
                logger.warning("HR 在线核实已关闭: 停止端点与取数线程")
            self.stop()
            return
        # L0 字段变化: 用新配置重建服务与线程, 端点保持不变
        running = self.worker is not None
        self.service = None
        if self.worker is not None:
            self.worker.stop()
            self.worker = None
        self._build(keep_endpoint=True)
        if running and self.worker is not None:
            self.worker.start()
        logger.info("HR 在线核实配置已热应用(L0 字段; 端点未重绑)")

    def wake(self) -> None:
        """非阻塞叫醒取数线程(主循环用)"""
        if self.worker is not None:
            self.worker.wake()

    # ---------- 视图(M3 的消费入口) ----------

    def view_set(self) -> HrViewSet:
        """当前只读视图(主循环每 tick 读它零等待)"""
        return self.publisher.latest()

    def view_snapshot(self) -> Tuple[int, HrViewSet]:
        """一次性取 (revision, views): 版本没变就不必做任何 record 更新"""
        return self.publisher.snapshot()

    @property
    def revision(self) -> int:
        return self.publisher.revision

    # ---------- 内部 ----------

    def _build(self, *, keep_endpoint: bool = False) -> None:
        """建立队列 / 服务 / (端点) / 取数线程"""
        conf = self.global_conf
        site_confs = self.site_confs()
        if self.queue is None:
            self.queue = HrTaskQueue()
        # 清掉上次关停留下的叫停标记(重启/热重载后必须能正常等回传)
        self.queue.resume()
        self.fetcher = build_channel_fetcher(
            channel_conf=conf.channel, enabled=self.enabled, queue=self.queue, site_confs=site_confs
        )
        self.service = HrRefreshService(
            data_dir=self.config.data_dir,
            global_conf=conf,
            site_confs=site_confs,
            fetcher=self.fetcher,
            owner=instance_id(),
            persist=True,
            # 无通道实例只读共享数据(别人抓的), 不发起任何请求
            allow_fetch=self.fetch_enabled,
        )
        if self.fetch_enabled:
            self.token = resolve_token(conf.channel.token, self.config.data_dir)
            if not (keep_endpoint and self.endpoint is not None):
                self.endpoint = HrChannelServer(
                    queue=self.queue,
                    token=self.token,
                    port=conf.channel.port,
                    extension_id=conf.channel.extension_id,
                )
        elif not keep_endpoint:
            self.endpoint = None
            self.token = ""
        self.worker = HrWorker(
            service=self.service,
            publisher=self.publisher,
            endpoint=self.endpoint,
            poll_interval=conf.poll_interval,
            anchors_fn=self._anchors,
        )

    def _anchors(self) -> Mapping[str, Mapping[str, object]]:
        """本地种子锚点: 由主循环以不可变数据交接(M3 接入; 现在没有提供者)"""
        provider = getattr(self._manager, "_hr_anchors", None)
        if provider is None:
            return {}
        got = provider() if callable(provider) else provider
        return got or {}

    def _advise_shared_dir(self) -> None:
        if self.config.hr_check.shared_dir:
            return
        logger.info(
            "hr_check.shared_dir 未配置: HR 站点文件落在 <data_dir>/hr/(单实例足够)。"
            "多实例共享同一账号时, 请把它指向所有实例都能看到的同一目录(网络盘可以, 云同步盘不可用 —— "
            "锁与原子替换都不保证), 并让各实例用不同的 hr_check.channel.port"
        )

    def _sites_dir(self) -> str:
        return hr_dir(self.config.data_dir, self.config.hr_check.shared_dir)

    @staticmethod
    def _identity(conf: HrCheckConfig) -> Tuple:
        """端点监听身份: 只有这些变了才需要重绑端口(与 web 段的 enabled/host/port 同款)"""
        return (
            bool(conf.enabled), bool(conf.channel.enabled), conf.channel.port, conf.channel.extension_id,
            conf.channel.token, conf.shared_dir
        )

    # ---------- 自检 ----------

    def status(self) -> HrRuntimeStatus:
        """自检快照(供 hr.once 报告: 路径 / 端点 / 锁 / 通道静默一次摊开)"""
        conf = self.global_conf
        channel = None
        if self.endpoint is not None:
            channel = self.endpoint.status(enabled=True)
        elif self.fetch_enabled:
            channel = ChannelStatus(enabled=True, listening=False, port=conf.channel.port, note="端点未启动")
        return HrRuntimeStatus(
            enabled=self.enabled,
            sites=tuple(self.service.enabled_sites()) if self.service else (),
            shared_dir=bool(conf.shared_dir),
            data_dir=self.config.data_dir,
            sites_dir=self._sites_dir(),
            writer=instance_id(),
            fetch_enabled=self.fetch_enabled,
            worker_running=bool(self.worker is not None and self.worker.started),
            poll_interval=conf.poll_interval,
            view_revision=self.publisher.revision,
            channel=channel,
            token_path=token_path(self.config.data_dir),
            token_source=describe_token_source(conf.channel.token, self.config.data_dir),
            note="取数通道未启用(只读共享数据)" if not self.fetch_enabled else "",
        )

    @property
    def fetcher_available(self) -> bool:
        return is_available(self.fetcher)


__all__ = ["HrRuntime", "HrRuntimeStatus"]
