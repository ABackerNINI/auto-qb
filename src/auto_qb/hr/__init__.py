"""HR 在线核实(部分种子 HR 站点): 取 HR 统计页 + 取 .torrent 算 infohash 对账建索引。

模块分工(v3 波次模型, 计划 26-09-28-1932):
- bencode    infohash 计算的正确姿势(原始字节切片, 不重编码)
- parse      HR 统计页的通用解析件(表格抽取 + 数值容错), 零新依赖
- adapters   站点隔离: URL 拼接 + 页面解析(现只有 NexusPHP `myhr.php` 形态)
- model      站点文件内的账号级状态(索引 / 放行 / 已取记录 / 档位波次状态 / 观察期)
- store      站点分文件 + 每站点一把锁(持锁期间完成读-判-抓-写-释放全程)
- ratelimit  单频控: 最小间隔 + 日额保险 + 时间窗(熔断/停用/退避已删除)
- fetcher    取数通道抽象(后端零 cookie、零直连站点; 取数由浏览器扩展完成)
- resolve    三态判定(受管束 / 放行 / 无证据本地兜底)+ 不可变只读视图
- service    波次引擎(持锁 → 对象集 → A/B/C 轮流翻页 → 行处理 → 防伪 → 放行/观察期 → 释放)
- channel    通道协议与安全边界(token / origin 白名单 / URL 白名单 / 配对码族)
- discovery  发现服务(发现端点 + 实例注册表 + 配对门; 去端口+跨机, 计划 26-10-14-1241)
- queue      任务队列(端点线程与取数线程之间的唯一交接面)
- server     本地数据端点(host 可配, 默认回环; 只入队)
- worker     取数线程 + 只读视图发布(自唤醒, 不随主循环 tick)
- threadlifecycle 线程生命周期骨架(幂 idempotent start + stop/join(timeout) + 退出/未退出日志), 取数线程与端点共用
- runtime    运行时门面(端点 + 取数线程 + 热重载重挂)

!本模块只读写 hr 文件与返回结果对象: **不碰 state_file / 任务队列 / store**
(线程三分职责的硬约束)。
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
    pairing_credential,
    pairing_display_code,
    pairing_needed,
    pairing_path,
    resolve_pairing_secret,
    resolve_token,
)
from .discovery import (
    API_DISCOVER,
    PAIRING_HEADER,
    HrDiscoveryServer,
    HrDiscoveryStatus,
    InstanceRegistry,
    default_registry_path,
    discovery_candidates,
)
from .fetcher import (
    ChannelFetcher,
    HrChannelStopped,
    HrChannelTimeout,
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
    FETCH_LANES,
    LANE_EXEMPT,
    LANE_SATISFIED,
    LANE_SCOPE,
    LANE_UNSATISFIED,
    SCHEMA_VERSION,
    SOURCE_EXEMPT,
    SOURCE_NOT_LISTED,
    SOURCE_SATISFIED,
    HrDownloaded,
    HrDlFail,
    HrEntry,
    HrLaneState,
    HrRateLedger,
    HrSiteData,
    HrVerified,
    HrWaveMeta,
)
from .parse import parse_datetime, parse_duration, parse_ratio, parse_size
from .ratelimit import HrLimits, next_allowed_at, quota_left, try_consume
from .resolve import (
    HrAnchor,
    HrIdentity,
    HrResolution,
    HrSiteView,
    HrViewSet,
    build_site_view,
    judge_record,
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
    REASON_BUDGET,
    REASON_NONE,
    REASON_PARSE,
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
    "FETCH_LANES",
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
    "SOURCE_SATISFIED",
    "HrDownloaded",
    "HrDlFail",
    "HrEntry",
    "HrLaneState",
    "HrRateLedger",
    "HrSiteData",
    "HrVerified",
    "HrWaveMeta",
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
    "HrChannelStopped",
    "HrChannelTimeout",
    "HrFetchError",
    "HrFetcher",
    "NullFetcher",
    "is_available",
    "ChannelFetcher",
    "build_channel_fetcher",
    # 取数通道: 协议 / 队列 / 端点 / 发现 / 取数线程 / 运行时门面
    "API_DISCOVER",
    "API_RESULT",
    "API_TASKS",
    "PAIRING_HEADER",
    "TASK_PAGE",
    "TASK_TORRENT",
    "TOKEN_HEADER",
    "ChannelStatus",
    "HrChannelBindError",
    "HrChannelError",
    "HrChannelServer",
    "HrDiscoveryServer",
    "HrDiscoveryStatus",
    "HrEndpointHandle",
    "HrRuntime",
    "HrRuntimeStatus",
    "HrTaskQueue",
    "HrViewPublisher",
    "HrWorker",
    "InstanceRegistry",
    "UrlPolicy",
    "default_registry_path",
    "discovery_candidates",
    "pairing_credential",
    "pairing_display_code",
    "pairing_needed",
    "pairing_path",
    "resolve_pairing_secret",
    "resolve_token",
    # 判定
    "HrAnchor",
    "HrIdentity",
    "HrResolution",
    "HrSiteView",
    "HrViewSet",
    "build_site_view",
    "judge_record",
    "resolve_identity",
    # 波次管道
    "ACTION_DISABLED",
    "ACTION_ERROR",
    "ACTION_LOCKED",
    "ACTION_NO_CHANNEL",
    "ACTION_PARTIAL",
    "ACTION_REFRESHED",
    "ACTION_REUSED",
    "ACTION_WAITING",
    "REASON_BUDGET",
    "REASON_NONE",
    "REASON_PARSE",
    "HrRefreshResult",
    "HrRefreshService",
]
