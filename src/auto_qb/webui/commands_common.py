"""WebCommandsMixin 公共件: 日志器 / 模块级常量 / 模块级纯 helper

move-only 自 commands.py 切出(计划 26-11-02-2342 §07 R5), 未改语义。
日志名显式钉为 "auto_qb.webui.commands" —— 消费方(测试/排障)按该名字取日志, 不能随模块漂移。
"""
import logging
from collections.abc import Mapping
from typing import Optional

from qbittorrentapi import HTTP401Error, HTTP4XXError

from ..infra.clock import SYSTEM_CLOCK, Clock

logger = logging.getLogger("auto_qb.webui.commands")

# 强制汇报确认常量组(plan 26-10-05-0923, epoch 语义重构)。
# !方向语义(事故根源): next_announce/min_announce 是 **Unix epoch 绝对秒**(qB 源码
#   toSecondsSinceEpoch), 汇报成功 = next **前跳(变大)**; 把它当倒计时用(next 变小 = 被重置
#   = 成功)方向正好相反 —— 判据方向的单点在 _verdict_reannounce 的 docstring。
# 立即路径基础窗口(epoch 语义): reannounce 后 qB 立即重发 announce(私站响应通常 1~10s);
# 30s 内仍未观测到 working 转换/前跳/拒绝证据则落「未确认」(warn, 不再判「失败」)。
# 主循环 main_tick=2s -> 约 15 轮确认机会。
REANNOUNCE_CONFIRM_TIMEOUT = 30.0
# 前跳判定容差(秒, D2): next > 基线 next + TOL 才算成功证据; TOL=3.0 依 S0 真机探针复核
# 维持(实测立即路径前跳 +5466s, 按机制 >= tracker min_interval, 分钟级量级, 余量充分)。
REANNOUNCE_JUMP_TOL = 3.0
# 推迟 item 的窗口外延: 立即路径 item 级 deadline = t0 + max(TIMEOUT, min_e - t0 + MARGIN)。
REANNOUNCE_DEFER_MARGIN = 15.0
# item 级窗口上限(秒): 防异常大的 min 值把确认窗口撑爆(公式见 _register_reannounce_pending)。
REANNOUNCE_WINDOW_CAP = 600.0
# 推迟检出阈值(秒, D1): epoch 模式下 min_e - t0 > 该值 -> item 立即「已受理: 推迟至 HH:MM」
# 并登记后台核实, 不进轮询(S0 实证 min 过期前 updating 是 ~0.9s 假瞬态, 轮询会误判成功)。
REANNOUNCE_DEFER_EARLY = 25.0
# 推迟后台核实结构上限(条): 超限丢最旧并 WARNING(防种子被删/断连等泄漏面, R5)。
REANNOUNCE_BACKGROUND_MAX = 500

# 回执文案前缀(§3.4 文案契约, D4=warn): 机器分流依据 = 回执 status(ok/error/warn),
# 前缀仅是人类可读文案; 前端按 status 三桶分流, 改前缀文案必须同步前端聚合分支(测试钉住)。
# 拼接规则:
# - 失败        = RC_FAIL_PREFIX + tracker msg
# - 已受理·推迟 = RC_DEFERRED_PREFIX + "HH:MM" + "(后台继续核实, 结果见日志)"
#                 (HH:MM 为基线 min_e 的本地时刻, 动态尾部不进常量; 括号段是固定尾文案)
# - 未确认·停止 = RC_UNCONFIRMED_PREFIX + "种子已停止, qB 静默忽略强制汇报"
# - 未确认·超时 = RC_UNCONFIRMED_PREFIX + "30s 内未观测到 working 转换/epoch 前跳/拒绝证据"
#                 (legacy 超时 = RC_UNCONFIRMED_PREFIX + "旧版 qB 无 epoch 字段, 仅未观测到拒绝")
RC_FAIL_PREFIX = "失败: tracker 未接受汇报(not working): "
RC_DEFERRED_PREFIX = "已受理: 最小间隔未过期, 推迟至 "
RC_UNCONFIRMED_PREFIX = "未确认: "

# ---------------------------------------------------------------------------------------
# 强制汇报"非活跃"状态集(qB 口径, 判据单点): 与前端 `decorate.js::REANNOUNCE_BLOCKED_STATES`
# **逐项同表**(守阵 test_frontend_reannounce_inactive_gate_wiring 钉住两边 key 集合相等, 防漂移)。
# 口径来源 = qBittorrent commit aa189a7(关闭 issue #12080): 该 commit 只在 GUI 给
# `actionForceReannounce->setEnabled(false)`(条件 !isPaused && !isChecking && !isQueued),
# **HTTP 端点侧没有门** —— 引擎侧的真拦截在 libtorrent(暂停种子 force_tracker_request 直接
# 空转, 排队种子内部也是 paused 故同样发不出去)。于是后端这一道的职责不是"防误汇报"(引擎
# 本来就不会汇报), 而是**收敛投递集合并免掉假回执**: 前端已收敛(见 reannouncePlan), 这里
# 是防"渲染到点击之间状态变了"与其它直连端点的调用方。
#
# !必须判 **qB 原始 state 串**, 不能用 state_enum 的谓词: 实测 queuedDL/queuedUP 命中
#   is_downloading/is_uploading(只有 paused*/stopped* 是 is_stopped、error/missingFiles 是
#   is_errored), 用谓词会把排队/校验中当活跃放过去 —— 与前端"单看 kind 判不出排队"是同一个坑。
# !反向的坑: `moving` **不属于任何谓词集合**(它不在 is_stopped/is_checking/is_errored/
#   is_downloading/is_uploading 任一族里 —— state_kind 是靠一条独立分支收它的, 2026-10-29
#   起为第 7 档), 谓词判定同样会把它当活跃放行。故它既要在 state_kind 里单独成档(显示与筛选),
#   也必须出现在下面这张表里(门控), 两处缺一即复刻 2026-10-29 那个"移动中显示成其它"的 bug。
REANNOUNCE_BLOCKED_STATES = frozenset(
    {
        "pausedDL",
        "pausedUP",
        "stoppedDL",
        "stoppedUP",
        "queuedDL",
        "queuedUP",
        "checkingDL",
        "checkingUP",
        "checkingResumeData",
        "error",
        "missingFiles",
        # 搬迁中: qB 处在 moving 期间所有 peer 传输都会让位给磁盘搬运(libtorrent 行为), 汇报
        # 换不回 peer; 且项目自己的搬迁模块把 moving 成员当禁区(relocate_units.py GATE_MOVING,
        # 排队下发会互相覆盖)。!注意 moving 不命中 TorrentState 的任何谓词, 只能按原始串判。
        "moving",
    }
)
# 非活跃目标的回执文案(第二道闸命中时用; 前端正常路径已被 reannouncePlan 收敛, 不会到这里)
# !此串被 tests/test_web_commands.py 与 test_webui_static_dom_panel.py 逐字断言(后者还有
#   "前后端文案漂移"守卫), 改一个字就要连带改三处 —— 本次 moving 入闸不在此列, 保持原样。
REANNOUNCE_INACTIVE_SKIP = "种子非活跃(暂停/停止/排队/校验中/错误), qB 静默忽略强制汇报"


def reannounce_blocked(rec) -> bool:
    """种子是否处于"qB 不会真的汇报"的状态(判据单点, 见上方状态表注释)

    rec 为 None(种子不在快照)判 False —— 与前端 `_reannounceVerdict`「解析不出不误拦」同口径,
    命令照发, 由 qB 的回执定论。
    """
    return bool(rec is not None and getattr(rec, "state", None) in REANNOUNCE_BLOCKED_STATES)


# **自投递**命令: 由 Web 侧在自己处理过程中 put 回队列(不是用户操作), 投递后**不唤醒**主循环。
# 目前只有 build_search_index —— web_view 在搜索索引脏时自投递(web_view.py:513/:699)。
# !若允许它唤醒会形成自激循环: 唤醒 -> drain(单轮最多 SEARCH_INDEX_BUILD_BUDGET=500 条文件 API)
# -> 索引仍脏 -> 再投递 -> 立刻再唤醒 …… 中间没有 tick 兜底, 直接打满 CPU 并冲垮 qB。
# 新增自投递命令时必须同步加进这里(测试守卫: tests/test_web_seed_center.py::test_api_enqueue_wakes_main_loop)。
SELF_POSTED_COMMANDS = frozenset({"build_search_index"})

# 执行后会**改变 qB 种子状态**的命令: 主循环在这批命令消费完后补一次完整刷新,
# 让真实状态立刻进快照, 而不必等下个节拍(P0-5)。按操作次数计费, 不是按时间计费。
# 用白名单而非黑名单: 配置/标签/分类类命令(reload_config/create_tags/edit_category …)
# 改的不是种子状态, 补刷新无收益; reannounce_* 的结果由 tracker 确认跟踪器单独推进。
RESYNC_COMMANDS = frozenset(
    {
        "pause_group",
        "resume_group",
        "delete_group",
        "pause_torrent",
        "resume_torrent",
        "delete_torrent",
        "recheck_torrent",
        "super_seeding",
        "force_start",
        "set_torrent_limits",
        "set_share_limits",
        "set_torrent_location",
        "rename_torrent",
        "queue_torrent",
        "set_auto_tmm",
        "add_trackers",
        "set_file_priority",
        "rename_fs",
        "bulk_torrents",
        "add_torrents",
        "skip_check_torrent",
        # 种子转移(计划 26-10-31-0306 W3): 转移成功即删源任务, 改 qB 种子状态 —— 补刷新同族
        "transfer_run",
    }
)

# **延迟回执**命令: handler 只发指令并登记确认跟踪, 真正的结果由后续 tick(tracker 确认)或
# handler 内部(依 qB 返回串写)写入 —— 它们不是"执行完即 ok", 所以 drain 侧**不**补写回执。
# recheck_torrent / skip_check_torrent 属 P1/P2' 提交点拒绝族(plan 26-09-30-0109): handler
# 经 ops 层提交并把结果**映射成回执**(拒绝回执带自解释文案), 同走本族。
# skip_check_precheck(plan 26-10-05-0314 S2): 只读 dry-run, 回执由 handler 自写 —— 判定数据
# (results/summary)经 truth 字段随回执带出(既有 cmd 通道的通用数据位), drain 不得用裸 ok 覆盖。
# relocate_precheck / relocate_precheck_add(计划 26-10-18-1604 P2): 同为只读 dry-run, 回执由
# handler 自写; 判定数据经 truth 字段带出(迁移 = {results, summary}, 添加 = 单 item)。
# relocate_cancel(计划 26-10-18-1604 §3.5.1): 撤销迁移两步走(先回成本、确认后删链接 + 搬回),
# 回执同样由 handler 自写(cls=confirm 带 cost / cls=ok 带 phase / cls=blocked 带原因)。
DEFERRED_RECEIPT_COMMANDS = frozenset(
    {
        "reannounce_group",
        "reannounce_torrent",
        "bulk_torrents",
        "add_torrents",
        "recheck_torrent",
        "skip_check_torrent",
        "skip_check_precheck",
        "relocate_precheck",
        "relocate_precheck_add",
        "relocate_cancel",
        # 种子转移(计划 26-10-31-0306 W3): 逐种子结果/版本信息经 truth 带出, handler 自写回执
        "transfer_run",
        "transfer_test",
    }
)

# 乐观白名单里的**批量**动作(与前端 shared/commands.js _optimisticPatch 同源: 只有 pause/resume)。
# 这些动作结果可预测、且必须能收到 `truth` 事件来收敛 —— 所以即使是 bulk_torrents 也不许走
# "handler 自写回执"的延迟回执族, 要回到 drain 的 defer_receipt 通路(与单种 resume_torrent 同路)。
# !bulk_torrents 是一个 handler 扛 8 种 action 的命令, 对"是否延迟回执"只能**按 action 分流** ——
#   整体归属会把 pause/resume 的真值出口一并切断(report 26-10-11-2017 §4.3): 那两条真值支路
#   (_truth_landed / _affected_hashes 的 bulk 分支)本已写好, 只是永远走不到。
_OPTIMISTIC_BULK_ACTIONS = frozenset({"pause", "resume"})

# 接受 cmd_id 关键字参数的命令集(handler 内可能读它写回执): 延迟回执族 + bulk_torrents。
# !与 DEFERRED_RECEIPT_COMMANDS **不同**: 后者是"handler 自写回执、drain 不补写"; 本集合只管
#   "drain 要不要把 cmd_id 传下去" —— bulk_torrents 的 pause/resume 回执由 drain 写, 但它的
#   错误回执(部分 hash 缺失 / 参数不合法)仍由 handler 写, 故 handler 必须拿到 cmd_id。
# set_torrent_location(计划 26-10-18-1604 P5): 整组迁移开时 handler 自写回执(带闸门判定
# truth: 集体相位/二次确认/拒绝原因), 故 drain 必须把 cmd_id 传下去 —— 与 bulk_torrents
# 同形态(「谁写回执」与「要不要传 cmd_id」是两件事)。
# pause/resume/delete_group(issue 26-10-31-1740): 常规回执仍由 drain 的 defer_receipt 写,
# 但「key 形状合法而 store 查无此组/成员已空」时 handler 要写显式 error 回执(不再静默 ok)
# —— 错误分支得拿到 cmd_id; handler 写过回执时 drain 靠 `cmd_id not in results` 不覆盖。
CMD_ID_COMMANDS = DEFERRED_RECEIPT_COMMANDS | {
    "bulk_torrents",
    "set_torrent_location",
    "pause_group",
    "resume_group",
    "delete_group",
}


def is_deferred_receipt(cmd: str, args: Optional[dict] = None) -> bool:
    """该命令是否由 handler 自写回执(drain 不补写、也不登记真值)

    单点: drain 分派(runtime.consume_commands)与 handler 内部的回执分支都调本函数 —— 两处各写
    一份必然漂移。bulk_torrents 的 pause/resume 例外返回 False: 它们的回执与真值登记由 drain 的
    defer_receipt 一并完成(与单种 pause_torrent/resume_torrent 完全同通路)。
    """
    if cmd == "bulk_torrents" and (args or {}).get("action") in _OPTIMISTIC_BULK_ACTIONS:
        return False
    return cmd in DEFERRED_RECEIPT_COMMANDS


def _timing(queued_ts: Optional[float], start_ts: float, clock: Optional[Clock] = None) -> dict:
    """P0-0 埋点: 把一次命令拆成两段耗时(毫秒), 供 /api/cmd/{id} 回传

    wait_ms = 出队时刻 - 投递时刻(命令排队等主循环的空档, P0-1 唤醒后应趋近 0)
    exec_ms = 执行完时刻 - 出队时刻(真正干活: 多数是 1 次 qB API 往返)

    clock: 取时注入(D8) —— start_ts 由调用方经同一只钟取, exec 段终点在这里现读;
    缺省取时单点(调用方不传时与真实行为同)。三段埋点必须同钟, 否则假钟下 exec_ms 是垃圾值。

    !这两段**只在回执里回传**, 要看就得开浏览器控制台 —— 真机上用户不一定开得了(嵌入式
    WebView / 手机 / 不愿开 F12)。故 drain 侧同时落一行日志(见 _log_cmd_timing),
    排查"点了要等几秒"时**不用控制台**。
    """
    if not queued_ts:
        return {}
    end_ts = (SYSTEM_CLOCK if clock is None else clock).now()
    return {
        "wait_ms": round((start_ts - queued_ts) * 1000, 1),
        "exec_ms": round((end_ts - start_ts) * 1000, 1),
    }


# 慢命令告警阈值(ms): 超过就按 WARNING 落日志, 便于在日志里直接捞
CMD_SLOW_MS = 300.0

# 真值推送的等待上限(ms): 命令执行完**立即发回执**(只表示"已执行"), 真值另走 `truth`
# 事件稍后推 —— 见 WebUIRuntime.defer_receipt / flush_truths。
# !2026-09-20 D2 定案: 原做法是"扣住回执等真值再发", 真机实测 qB 翻状态要 **1258ms**
#   (而命令执行只要 2.7ms)⇒ 扣着回执等 = 把撤下钉死在 1.25s+(实测撤下 2947ms)。
# !超时**不推**真值(宁可让前端超时回滚), 因为推一个未落地的真值 = 采纳命令前的旧值 ⇒ 弹回。
#   改这里必须同步前端 TRUTH_HOLD_MS(前端"值覆盖"的保持上限)—— 两边各写各的必然漂移,
#   已有静态守阵钉住。
TRUTH_PUSH_CAP_MS = 8000.0


def _add_outcome(result: object) -> tuple[str, str]:
    """判定一次 `torrents_add` 的结果 -> (受理态, 详情文案); 两种响应形态都要认

    - **Web API < 2.14.0**(qB 5.2 之前): 纯文本 `Ok.` / `Fails.`;
    - **Web API >= 2.14.0**(qB 5.2 起, 用户实测 5.2.3): JSON 元数据
      `{success_count, failure_count, pending_count, added_torrent_ids}`, qbittorrent-api 包成
      `TorrentsAddedMetadata`(**dict 子类**, 见库内 torrents.py 的 `resp.json()` 分支)。

    !2026-09-24 实测 bug: 老写法只认 `"Ok." in str(result)`, 在 5.2.3 上**恒为假** ——
    `str(TorrentsAddedMetadata(...))` 是 `"TorrentsAddedMetadata({'success_count': 1, ...})"`,
    于是"种子明明加进去了, WEB UI 却弹添加失败"。判据必须同时覆盖两形态。
    `pending_count > 0` = 已受理但仍在异步处理(magnet 元数据未就绪 / 走 search 插件下载),
    同样算受理成功 —— 它不是失败, 只是还没定下 info hash。

    受理态三值(2026-10-18 由布尔扩为三值, 见 `_cmd_add_torrents` 聚合):
      `ok`      = 这一次调用全部受理(无被拒);
      `partial` = **一部分受理一部分被拒**(仅新形态元数据可能出现) —— qB 对重复种子是
                  **整批里挑着拒**(HTTP 200 + failure_count>0), 不是整批 409 ⇒ "部分成功"
                  是常态路径。旧布尔判据把它与"全拒"压成同一个 False, 调用端只能二选一,
                  用户报「部分种子添加失败(已存在)时添加窗口不消失」;
      `fail`    = 全部被拒 / 调用未成功。
    全部失败时 qB 回 HTTP 409, 库直接抛 `Conflict409Error`, 走不到这里(由命令分发层写 error 回执)。
    """
    if isinstance(result, Mapping):
        success = int(result.get("success_count") or 0)
        failure = int(result.get("failure_count") or 0)
        pending = int(result.get("pending_count") or 0)
        detail = f"成功 {success} / 失败 {failure} / 待定 {pending}"
        if failure == 0 and (success + pending) > 0:
            return "ok", detail
        if (success + pending) > 0:
            return "partial", detail
        return "fail", detail
    text = str(result)
    return ("ok" if "Ok." in text else "fail"), text or "无结果"


# qB 业务拒绝(HTTP 4xx, 如 "必须启用 torrent 队列") 的**行动建议**表: 按 qB 返回文案子串匹配,
# 命中才附到回执文案尾部。qB 文案随其 WebUI 界面语言变化, 匹配不到就只给通用前缀(尽力而为,
# 不猜) —— 中文与英文各留一条 needle, 覆盖两种常见界面。
QB_REJECT_HINTS = (
    ("必须启用 torrent 队列", "请在 qB「设置 -> BitTorrent -> 队列」启用「启用队列」后重试"),
    ("torrent queueing", "enable queueing in qB: Settings -> BitTorrent -> Queueing"),
)


def qb_reject_text(exc: BaseException) -> Optional[str]:
    """qB 业务拒绝(HTTP 4xx, 401 除外) -> 面向用户的可读回执文案; 非此类返回 None

    !为什么要单独分类: qB 的 4xx 是**用户这次操作被 qB 拒绝**(未启用队列 / 名字已存在等),
      不是本程序未预期异常 —— 前端已有明确回执, 用户看得懂, 也无需立刻放下手头的事
      (弹窗测试 -> WARNING)。若混进命令分发层的通用 except, 既打 ERROR + 堆栈显得像程序 bug,
      又把库抛的原始文案原样丢给用户, 缺可行动建议。
    !401 排除在外: 鉴权失败是凭据/环境故障, 需人工介入, 属 ERROR, 与「业务拒绝」不同质。
    !文案单点: 「qB 拒绝执行: <qB 原文>(<行动建议>)」只在这里拼, 命令分发层不重复拼装。
    """
    if not isinstance(exc, HTTP4XXError) or isinstance(exc, HTTP401Error):
        return None
    detail = str(exc).strip() or "qB 拒绝了该操作"
    for needle, hint in QB_REJECT_HINTS:
        if needle in detail:
            return f"qB 拒绝执行: {detail}({hint})"
    return f"qB 拒绝执行: {detail}"


def _bulk_call_limits(api, hashes, delete_files, extra):
    """_BULK_ACTIONS["limits"] 的可调用体: 只调有值方向, 每方向一次调用传全 hashes

    不用 lambda 表达: 两个方向"各自可选"用单表达式写不出来, 逐枚循环又被禁止
    (qbapi 原生收 hash 列表)。签名与 _BULK_ACTIONS 其余条目统一(4 参)。
    """
    if extra["up_limit"] is not None:
        api.torrents_set_upload_limit(torrent_hashes=hashes, limit=int(extra["up_limit"]))
    if extra["dl_limit"] is not None:
        api.torrents_set_download_limit(torrent_hashes=hashes, limit=int(extra["dl_limit"]))
