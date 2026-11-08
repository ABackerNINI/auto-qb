"""ops 共用叶: logger / 常量 / GateVerdict / SkipJob / 跳检重加回传 kwargs 单点(自 ops_mod move-only 切出)

拆分(R5)只搬位置: 区段文本与 ops_mod.py 原文件逐字一致, 仅 logger 名显式沿用原模块名。
skip_readd_kwargs 是后补的共用单点(issue 26-11-07-0527 R1#94): 正常重加与崩溃恢复重加
共一个参数面构造点, 防两条路径口径漂移。
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
# 相位重试退避(毫秒): 10/20/50/50/50, 每相位至多 5 拍(首拍 10ms 生效, 耗尽即 FAILED) ——
# 覆盖 qB 删除/重加异步生效的典型窗口
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


def skip_readd_kwargs(src: Any, content_layout: Optional[str]) -> dict:
    """跳检重加 torrents_add 的属性回传 kwargs 单点(issue 26-11-07-0527 R1#94)

    正常重加(_skip_add_call)传 TorrentRecord, 崩溃恢复重加(_recover_skip_backups)传备份
    元数据 dict —— 两条路径共用本函数, 保证恢复回传与正常重加恒同口径: contentLayout 与
    限速/分享限制任一缺失 = 恢复出的种子被 qB 默认值静默重置(布局错位 missingFiles /
    PT 刷量义务丢失)。0/负值有语义(不限速/跟随全局)不吞。

    - src 为 TorrentRecord 等对象: 属性**缺失直接抛 AttributeError**(fail-fast, 字段改名
      不得静默吞成 None); 为 dict 时键名与 TorrentRecord 属性一致(_backup_torrent 记账
      口径), **缺键取 None**(旧格式备份兼容: None 值键库不发, wire 与缺省参数相同)。
    - content_layout 单独入参: 布局是推断产物挂在 job 上(不是 tor 的属性), 恢复侧取自
      备份元数据; camelCase 键名同服务端(见 shareLimitsMode 注)。
    - shareLimitsMode 是 qB 5.3 新增分享限制模式: camelCase kwarg 经 facade 纯透传, 库
      (无具名参)对未知 kwargs 经 _format_payload 并进 POST data —— 键名必须与服务端
      camelCase 一致; 5.2 快照无该字段恒 None -> requests 对 None 值键不发(wire 不变)。
    """
    if isinstance(src, dict):
        get = src.get
    else:

        def get(key: str) -> Any:
            return getattr(src, key)

    return dict(
        save_path=get("save_path"),
        category=get("category") or None,
        tags=get("tags") or None,
        upload_limit=get("up_limit"),
        download_limit=get("dl_limit"),
        is_sequential_download=get("seq_dl"),
        is_first_last_piece_priority=get("f_l_piece_prio"),
        contentLayout=content_layout,
        ratio_limit=get("ratio_limit"),
        seeding_time_limit=get("seeding_time_limit"),
        inactive_seeding_time_limit=get("inactive_seeding_time_limit"),
        share_limit_action=get("share_limit_action"),
        shareLimitsMode=get("share_limits_mode"),
    )
