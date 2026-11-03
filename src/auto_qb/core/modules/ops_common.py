"""ops 共用叶: logger / 常量 / GateVerdict / SkipJob(自 ops_mod move-only 切出)

拆分(R5)只搬位置: 区段文本与 ops_mod.py 原文件逐字一致, 仅 logger 名显式沿用原模块名。
"""
import logging
from dataclasses import dataclass
from typing import Any, Optional

from ...torrents import TorrentRecord

logger = logging.getLogger("auto_qb.core.modules.ops_mod")

# R1/R2 拒绝文案(自解释: checking 态在种子列表可见, 用户能对上原因)
_RECHECK_BUSY_MSG = "校验进行中, 请等待当前校验完成"
_SKIP_GONE_MSG = "种子已被移除(可能被用户删除), 放弃跳检"
_RECHECK_GONE_MSG = "种子已被移除(可能被用户删除), 放弃校验"  # 快照无记录时用(与 _SKIP_GONE_MSG 同族)

# 跳检闸门三分流标签(plan 26-10-05-0314 §03/§04, cls 与谓词同点定义):
#   blocked = 确定性危害/零收益, 一律硬拒(force 也不放行, case 1);
#   force   = 真不确定(判决窗口抢跑), 可被 skip_check(force=True) 显式豁越(case 2);
#   ok      = 通过(不进未过列表 —— _skip_gates_detail 只返回未过闸门)。
GATE_BLOCKED = "blocked"
GATE_FORCE = "force"
GATE_OK = "ok"


@dataclass(frozen=True)
class GateVerdict:
    """单道跳检闸门的判定结果(不可变值对象): gate 闸门 id / cls 三分流标签 / text 拒绝文案

    gate 取值: "G3"(已完成) / "G4"(活跃中) / "G5"(同 hash 校验在途) / "G6"(组内活跃下载) /
    "G7"(组内其它成员校验在途) / "G8"(组内成员校验失败推断) /
    "partial"(部分下载) / "dedup"(同日去重) / "filelist"(前置文件检查) / "gone"(预检时种子已不在
    客户端, 仅 skip_check_precheck 产出)。拒绝文案按「原因+后果+出路」三段式(plan §03)。
    """
    gate: str
    cls: str
    text: str


# 跳检相位机(计划 26-10-21-1857 §5): 每步至多 1 次写 + 1 次存在性读, 步间用毫秒级退避
# 代替原来的 500ms 轮询; 运行状态一个字不写(等 qB 上报), 删除也不摘记录(keep_record)。
SKIP_PHASE_PREPARING = "preparing"
SKIP_PHASE_DELETING = "deleting"
SKIP_PHASE_GONE = "gone"
SKIP_PHASE_ADDING = "adding"
SKIP_PHASE_APPEARED = "appeared"
SKIP_PHASE_FINISHING = "finishing"
SKIP_PHASE_DONE = "done"
SKIP_PHASE_FAILED = "failed"

_SKIP_TERMINAL = frozenset({SKIP_PHASE_DONE, SKIP_PHASE_FAILED})
# 相位重试退避(毫秒): 10/20/50/50/50 —— 覆盖 qB 删除/重加异步生效的典型窗口
_SKIP_BACKOFF_MS = (10, 20, 50, 50, 50)
# 单条跳检的总上限(秒): 删除→重加窗口不许无限拉长(PT/HR 视角种子长期不在客户端)
SKIP_DRIVE_TIMEOUT = 30.0
# 终态结果缓存条数(纯观测面: 规则侧/测试取异步终态 + 进度事件回放; 不参与判定)
_SKIP_RESULT_KEEP = 64


@dataclass
class SkipJob:
    """一条跳检的相位机状态(纯内存; 崩溃恢复账本见计划 S4)

    字段即相位推进所需的全部上下文: tor 是**删除前**的记录快照(备份/布局推断/打标判断都用它),
    data/content_layout 在 PREPARING 一次备齐(删除后取不到)。
    """

    hash: str
    tor: TorrentRecord
    source: str
    auto_start: bool
    has_reference: bool
    phase: str = SKIP_PHASE_PREPARING
    attempts: int = 0
    next_run: float = 0.0
    started_at: float = 0.0
    data: bytes = b""
    content_layout: Optional[str] = None
    backup: str = ""
    error: str = ""
    # 终态结算面(同步入口不传; 异步入口经 skip_submit 传入)
    on_done: Any = None  # 终态回调(web 批量聚合回执)
    origin: Any = None  # 规则任务(终态重新入队, 与 recheck 同构)
    result: Any = None  # 终态 ActionResult(同步入口直接返回它)
    settled: bool = False
