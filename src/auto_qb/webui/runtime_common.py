"""WebUIRuntime 拆分伴生模块: 日志 / 模块级常量 / 模块级 helper / WebErrLogHandler。

move-only 自 runtime.py 切出(计划 26-11-02-2342 §07 R5), 未改语义。
logger 名显式写 "auto_qb.webui.runtime": 测试按该名字断言 caplog 记录, 迁文件不改日志命名空间。
"""
import logging
from typing import TYPE_CHECKING

from ..infra.logging import is_record_suppressed

if TYPE_CHECKING:  # 仅注解用途: WebUIRuntime 在根模块, 运行期导入会成环
    from .runtime import WebUIRuntime

logger = logging.getLogger("auto_qb.webui.runtime")

# Web 客户端活跃窗口: 超时无请求则主循环跳过视图组装(惰性), 关闭网页后 CPU 回落
WEB_VIEW_TTL = 10.0
# 回执保留窗口与容量上限: 前端轮询完即弃, 兜底防无界增长
WEB_RESULT_TTL = 120.0
WEB_RESULT_MAX = 64

# 真值直查(torrents/info)的分批大小: hashes 是拼在 URL 里的,
# 448 个 40 位 hash ≈ 18KB, 超多数服务端/代理的 URL 长度限制(被截断或 414) ⇒ 分批查。
TRUTH_QUERY_CHUNK = 50

# 单个 SSE 订阅者的事件队列上限: 超过就丢(慢消费者靠轮询补), 防无界增长
EVENT_QUEUE_MAX = 200
# SSE 空闲心跳间隔(秒): 必须 **< WEB_VIEW_TTL**, 否则连着的客户端会被判成不活跃
# ⇒ 主循环停止组装视图 ⇒ 推送自己也没内容可发(自锁)。
SSE_KEEPALIVE_S = 5.0
# SSE 一次性票据(查询串 ?ticket= 换票): 短 TTL + 单次消费 —— 查询串会进反代/中间层
# 访问日志, 只放短命票据, 不再放长期访问密钥(issue 26-09-21-1408 B-01)
EVENT_TICKET_TTL_S = 30.0
# 未消费票据上限: 防签发端无界堆积(签发需要凭证, 上限只是内存卫生)
EVENT_TICKET_MAX = 64

# ---- 错误历史环(WEBUI 错误历史 S2): 挂 auto_qb logger 的 WARNING+ 内存环 ----
# 容量写常量(零新配置键): 环满挤最旧, 200 条足够前端重连后补拉一段历史
WEB_ERR_RING_MAX = 200
# 单条消息截断上限: traceback 等长文案收集时压掉, 展示层不再处理
WEB_ERR_MSG_MAX = 500

# ---- 增量时间线(plan 26-10-07-0414 S2): qB 启发的自创窗口 —— deque 只存脏行键不存值(R1),
# 值回放时从当前已发布视图现取, 内存 O(代数 x 脏行键) 与库大小无关 ----
# 容量写常量(零新配置键): 40 代 ~= 60s @1.5s tick, 环满挤最旧(窗外客户端退化全量, R10)
_DELTA_TIMELINE_MAX = 40
# S3 启用矩阵(plan 26-10-07-0414): group/torrent 视图 S3 起启用; show 视图 S9b 解锁 ——
# 剧行键 = S8 剧键映射(_show_member_keys)派生, 局部重聚合按脏剧键整行重建(R8); 缺省
# (四数组)与未知 view 值仍一律 full(无视图上下文可裁剪, 保守默认)
_DELTA_VIEWS = frozenset({"group", "torrent", "show"})

# ---- 流量快照的轮询出口(计划 26-10-18-0813 A5/D5) ----


def public_traffic_view(view: dict) -> dict:
    """轮询载荷用的流量快照: **去掉 history 段**的浅拷贝(单点, 只此一处)

    history 是 dat 的逐日全量行(几百行, 且随数据积累线性增长), 前端从不从轮询里读它 ——
    弹层一律走 `/api/traffic/history`(dialogs.js 的 loadHistory)。此前 `/api/status`·
    `/api/state` 直接把快照引用塞进响应, 等于每轮把整份历史背一遍(设计注释早就写着"历史行
    不进轮询响应", 实现一直没跟上)。

    返回浅拷贝(.copy): 段对象仍是同一批引用(Web 线程只读), 只有 history 这一个键被摘掉 ——
    不给调用方"顺手改顶层键"的机会, 也不复制几百行数据。
    """
    if not view:
        return view
    out = dict(view)
    out.pop("history", None)
    return out


def _new_delta_buckets() -> dict:
    """增量键集桶结构(plan S2): 分视图 upsert/removed 键集; show 桶 S9b 起随剧键推导填充"""
    return {
        "upsert": {
            "torrent": set(),
            "group": set(),
            "show": set()
        },
        "removed": {
            "torrent": set(),
            "group": set(),
            "show": set()
        },
    }


def _cancel_delta_buckets(delta: dict) -> None:
    """R5 同键抵消: 同一桶内同时 upsert+removed 的行净变化为零(幂等)。

    规则单点: _publish_locked 分叉判定前与 _fold_delta_pending_locked 落代前各调一次
    (fold 段重跑一遍是幂等兜底)。循环走 upsert 的键(即 _new_delta_buckets 的键),
    新增桶维度不再漏。注意 _reduce_delta 的跨代单向让位(rm -= up)是另一条规则,
    不得换用本 helper。
    """
    upsert, removed = delta["upsert"], delta["removed"]
    for view in upsert:
        both = upsert[view] & removed[view]
        upsert[view] -= both
        removed[view] -= both


class WebErrLogHandler(logging.Handler):
    """auto_qb logger -> WEB 错误历史内存环(WARNING+; tray/app.py UiLogHandler 同款范式)

    emit 仅格式化 + 入环(持 runtime 的锁), 全程 try/except 静默 —— 收集器永不干扰
    业务日志; 环操作零 IO, 纯内存不进 state_file。环本体与 seq 计数器是 WebUIRuntime
    字段, handler 持引用写: 日志线程经 lock 写, Web 线程端点只读(单一写者纪律不破)。
    """
    def __init__(self, runtime: "WebUIRuntime"):
        super().__init__()
        self._runtime = runtime

    def emit(self, record: logging.LogRecord):
        try:
            if record.levelno >= logging.WARNING:
                # 只进后端 log 的记录(HR 通道/环境层的静默子类, 如「浏览器关着」)在此止步:
                # 环境态混进站点故障的错误历史是量级混淆(计划 26-10-09-0821 §03.3)。
                if is_record_suppressed(record):
                    return
                # 多行合一(换行等空白折叠成空格)+ 截断: 收集时一次处理, 展示层不管
                msg = " ".join(str(record.getMessage()).split())
                if len(msg) > WEB_ERR_MSG_MAX:
                    msg = msg[:WEB_ERR_MSG_MAX]
                self._runtime.append_err(msg, record.levelname)
        except Exception:
            pass
