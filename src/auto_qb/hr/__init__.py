"""HR 在线核实(部分种子 HR 站点): 取 HR 统计页 + 取 .torrent 算 infohash 对账建索引。

模块分工(与计划 §5/§6/§8 的职责三分一致):
- bencode    infohash 计算的正确姿势(原始字节切片, 不重编码)
- parse      HR 统计页的通用解析件(表格抽取 + 数值容错), 零新依赖
- adapters   站点隔离: URL 拼接 + 页面解析(现只有 NexusPHP `myhr.php` 形态)
- model      站点文件内的账号级状态(索引 / 放行 / 已取记录 / 配额 / 熔断)
- store      站点分文件 + 每站点一把锁(持锁期间完成读-判-抓-写-释放全程)
- ratelimit  间隔 + 只向上抖动 + 两级配额 + 失败退避熔断 + 时间窗
- fetcher    取数通道抽象(后端零 cookie、零直连站点; 取数由浏览器扩展完成)
- resolve    三态判定(受管束 / 已核实不受管束 / 未核实)+ 不可变只读视图
- service    刷新管道(持锁 → 读 → 判有效期 → 必要时抓 → 写 → 释放)
- channel    通道协议与安全边界(token / origin 白名单 / URL 白名单)
- queue      任务队列(端点线程与取数线程之间的唯一交接面)
- server     本地端点(127.0.0.1, 只入队)
- worker     取数线程 + 只读视图发布(自唤醒, 不随主循环 tick)
- runtime    运行时门面(端点 + 取数线程 + 热重载重挂)

❗本模块只读写 hr 文件与返回结果对象: **不碰 state_file / 任务队列 / store**
(线程三分职责的硬约束, 见计划 §8)。
"""
from .adapters import available_adapters, build_adapter
from .bencode import bdecode, compute_infohashes, info_span, torrent_display_name
from .channel import (
    API_RESULT,
    API_TASKS,
    TASK_PAGE,
    TASK_TORRENT,
    TOKEN_HEADER,
    ChannelStatus,
    HrChannelBindError,
    HrChannelError,
    UrlPolicy,
    resolve_token,
)
from .fetcher import (
    ChannelFetcher,
    HrChannelUnavailable,
    HrFetchError,
    HrFetcher,
    NullFetcher,
    build_channel_fetcher,
    is_available,
)
from .queue import HrTaskQueue
from .runtime import HrRuntime, HrRuntimeStatus
from .server import HrChannelServer, HrEndpointHandle
from .model import (
    ALL_LANES,
    CHANNEL_DISABLED,
    CHANNEL_OK,
    CHANNEL_SILENT,
    LANE_EXEMPT,
    LANE_SATISFIED,
    LANE_SCOPE,
    LANE_UNSATISFIED,
    SCHEMA_VERSION,
    SOURCE_EXEMPT,
    SOURCE_NOT_LISTED,
    HrDownloaded,
    HrDlFail,
    HrEntry,
    HrFuse,
    HrQuota,
    HrRefreshMeta,
    HrSiteData,
    HrVerified,
)
from .parse import parse_datetime, parse_duration, parse_ratio, parse_size
from .ratelimit import HrLimits, next_allowed_at, quota_left, try_consume
from .resolve import (
    POLICY_HR,
    POLICY_NOT_HR,
    HrAnchor,
    HrIdentity,
    HrResolution,
    HrSiteView,
    HrViewSet,
    build_site_view,
    resolve_identity,
)
from .service import (
    ACTION_DISABLED,
    ACTION_ERROR,
    ACTION_LOCKED,
    ACTION_NO_CHANNEL,
    ACTION_PARTIAL,
    ACTION_REFRESHED,
    ACTION_REUSED,
    ACTION_WAITING,
    HrRefreshResult,
    HrRefreshService,
)
from .store import HrLockBusy, HrSiteStore, hr_dir, instance_id
from .worker import HrViewPublisher, HrWorker

__all__ = [
    # bencode / 解析
    "bdecode",
    "compute_infohashes",
    "info_span",
    "torrent_display_name",
    "parse_datetime",
    "parse_duration",
    "parse_ratio",
    "parse_size",
    # adapter
    "available_adapters",
    "build_adapter",
    # 数据模型
    "ALL_LANES",
    "CHANNEL_DISABLED",
    "CHANNEL_OK",
    "CHANNEL_SILENT",
    "LANE_EXEMPT",
    "LANE_SATISFIED",
    "LANE_SCOPE",
    "LANE_UNSATISFIED",
    "SCHEMA_VERSION",
    "SOURCE_EXEMPT",
    "SOURCE_NOT_LISTED",
    "HrDownloaded",
    "HrDlFail",
    "HrEntry",
    "HrFuse",
    "HrQuota",
    "HrRefreshMeta",
    "HrSiteData",
    "HrVerified",
    # 存储与频控
    "HrLimits",
    "HrLockBusy",
    "HrSiteStore",
    "hr_dir",
    "instance_id",
    "next_allowed_at",
    "quota_left",
    "try_consume",
    # 取数通道
    "HrChannelUnavailable",
    "HrFetchError",
    "HrFetcher",
    "NullFetcher",
    "is_available",
    "ChannelFetcher",
    "build_channel_fetcher",
    # 取数通道(M2): 协议 / 队列 / 端点 / 取数线程 / 运行时门面
    "API_RESULT",
    "API_TASKS",
    "TASK_PAGE",
    "TASK_TORRENT",
    "TOKEN_HEADER",
    "ChannelStatus",
    "HrChannelBindError",
    "HrChannelError",
    "HrChannelServer",
    "HrEndpointHandle",
    "HrRuntime",
    "HrRuntimeStatus",
    "HrTaskQueue",
    "HrViewPublisher",
    "HrWorker",
    "UrlPolicy",
    "resolve_token",
    # 判定
    "POLICY_HR",
    "POLICY_NOT_HR",
    "HrAnchor",
    "HrIdentity",
    "HrResolution",
    "HrSiteView",
    "HrViewSet",
    "build_site_view",
    "resolve_identity",
    # 刷新管道
    "ACTION_DISABLED",
    "ACTION_ERROR",
    "ACTION_LOCKED",
    "ACTION_NO_CHANNEL",
    "ACTION_PARTIAL",
    "ACTION_REFRESHED",
    "ACTION_REUSED",
    "ACTION_WAITING",
    "HrRefreshResult",
    "HrRefreshService",
]
