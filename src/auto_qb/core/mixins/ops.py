"""OpsMixin: 危险操作独立操作层(rules → ops ← web, plan 26-09-30-0109 P2')

recheck / 跳检的 qB 交互序列、提交点检查与保护策略单点归本层; 规则(CheckAction 执行体)
与 WEB(webui/commands)都只做调用方 —— 修正 v2「WEB 接到规则侧体系」的反向依赖
(WEB 伪造 RuleContext / 适配规则私有 state 键, 依赖方向做反)。

保护策略按来源(source)区分(计划 §3.5, D1 拍板口径):
- 防「自动化频率失控」的保护只作用 source="rule": 3 次/日校验失败冷却(recheck_fails)。
  WEB 源是手动排障, 不受限 —— 限制它就是「按钮为什么不生效」。
- 防「真实冲突」的作用所有来源: 在途互斥(_active_checks 登记 / 快照 checking 态, R1)、
  跳检实时复核(R2)、跳检同日去重(skip_check_day)。判据: 被拒时用户能否从界面自行看出
  原因 —— checking 态种子列表可见(拒绝可自解释), 保留; 不可见窗口的拒绝一律不对 WEB 设。

执行模型不变: 两个调用方都在主循环线程(WEB 命令线 drain + 规则任务线), 单一写线程约束
原样成立。阻塞执行体 + 单一写线程是当前安全模型的一半 —— ops 方法必须留在主循环线程调用;
新来源(HR 联动 / 外部 API / 定时任务)接入 = 新增一个 source 调 ops, 不复制操作语义、不开旁路。

导入方向(防环): 本模块 -> rules.actions.full_checking 取轮询常量与冷却 helper(它们仍定义在
彼处, 供决策链 1.6 与既有测试导入路径使用); rules.actions.full_checking **不得**反向 import
本模块 —— 否则 ops -> rules.base(触发 rules 包 __init__ -> actions -> full_checking)成环。
"""
import logging
import os
import time
from datetime import date
from typing import Optional

from ...infra import utils
from ...rules.actions.full_checking import (
    CHECK_RESULT_INTERVAL,
    CHECK_START_GIVEUP,
    RECHECK_FAIL_LIMIT,
    _bump_recheck_fail,
    _recheck_fail_count,
)
from ...rules.base import ActionResult
from ...torrents import TorrentRecord
from ..taskqueue import FINISHED, REQUEUE, Task

logger = logging.getLogger(__name__)

# R1/R2 拒绝文案(自解释: checking 态在种子列表可见, 用户能对上原因)
_RECHECK_BUSY_MSG = "校验进行中, 请等待当前校验完成"
_SKIP_GONE_MSG = "种子已被移除(可能被用户删除), 放弃跳检"


def _poll_until(predicate, attempts: int, interval: float) -> bool:
    """轮询直至 predicate 为真或次数耗尽(异常视为未满足); 返回是否满足

    供跳检的删除/重加确认共用: qB 的删除与重加均为异步生效, 需短间隔轮询客户端状态。
    """
    for _ in range(attempts):
        try:
            if predicate():
                return True
        except Exception:
            pass
        time.sleep(interval)
    return False


class OpsMixin:
    """危险操作独立操作层: 组合进 QbManager, 依赖宿主的 api / store / state / task_queue / config"""

    # ---------- 日志 ----------

    @staticmethod
    def _ops_repr(torrent: Optional[TorrentRecord]) -> str:
        """日志标识: 活记录用 log_repr(名字+tracker+hash8), 记录已不在时退化裸 hash8"""
        return torrent.log_repr if torrent is not None else "(已不在库)"

    # ---------- full-checking: 提交点检查 + 提交 + 轮询 ----------

    def ops_recheck(
        self,
        hash: str,
        source: str = "rule",
        torrent: Optional[TorrentRecord] = None,
        auto_start: bool = False,
        on_success=None,
        origin=None,
    ) -> ActionResult:
        """full-checking 操作: R1 提交点检查 -> 登记轮询子任务 -> 发送 recheck -> 轮询结果

        自 rules/actions/full_checking.py._execute_full_checking 迁入(行为等价), 规则侧差异
        全部收进参数:
        - source: 保护策略按来源区分 —— 失败冷却(recheck_fails)仅 rule 源生效(D1);
          WEB 源手动排障不受冷却限制, on_success=None(成功即消亡, 无晋升无重入队)。
        - on_success: 校验成功时的**语义回调**(规则侧传晋升 verified_references; WEB 源 None),
          冷却清除与 auto_start 由本层统一收尾(它们是操作语义, 不属调用方)。
        - origin: 规则任务(重入队由本层负责: 成功 keep_progress 断点续跑, 失败/删除/
          宽限耗尽/异常 默认重置重走决策链); WEB 源 None —— 轮询结束即消亡, 无重入队副作用。
        - torrent: 可选活记录; None 时经 store 取(store 原地更新的活记录, 显式传参与缺省等价)。

        返回 ActionResult: rule 源 pending(规则断点, 规则任务本轮不重入队, 恢复由轮询负责) /
        web 源 ok(已提交, 结果经快照可见) / skip(R1 拒绝或冷却) / fail(发送失败)。
        """
        prefix = f"ops[{source}]"

        # ---- R1 提交点检查(在途互斥, 全来源): 规则轮询在途或快照已在校验态 -> 拒绝 ----
        # WEB->规则半边: 不重启规则正在轮询的校验(进度回落会误判失败/污染当日计数);
        # 规则->WEB/规则: 决策链 1.5 组内串行化经 _active_checks 感知到本层登记(双向闭环)。
        if hash in self.task_queue.active_check_hashes():
            logger.info(f"{prefix} {self._ops_repr(torrent or self.store.get(hash))} | recheck 拒绝: {_RECHECK_BUSY_MSG}")
            return ActionResult.skip(_RECHECK_BUSY_MSG)
        snap = self.store.get(hash)
        if snap is not None and snap.state_enum.is_checking:
            logger.info(f"{prefix} {snap.log_repr} | recheck 拒绝: {_RECHECK_BUSY_MSG}(快照 checking 态)")
            return ActionResult.skip(_RECHECK_BUSY_MSG)

        # ---- 失败冷却: 仅规则源(自动化 recheck 死循环自限频; WEB 手动排障不受限, D1) ----
        if source == "rule" and _recheck_fail_count(self, hash) >= RECHECK_FAIL_LIMIT:
            logger.info(f"{prefix} {self._ops_repr(torrent or snap)} | "
                        f"校验连续失败 {RECHECK_FAIL_LIMIT} 次, 今日不再重试")
            return ActionResult.skip(f"校验连续失败 {RECHECK_FAIL_LIMIT} 次, 今日不再重试")

        tor = torrent if torrent is not None else snap
        tq = self.task_queue

        def poll(task: Task, dry_run: bool) -> bool:
            """校验结果轮询: 读 store 活记录(原地更新, 不发 API 重查真值), 每 CHECK_RESULT_INTERVAL 一次

            等价性红线(plan §3.4): 这里必须继续读 store 活记录 —— 记录对象被同步线程原地
            更新, 逐轮读到最新 state/progress; 不得改为闭包创建时缓存字段值(快照失真),
            也不得改为每次 torrents_info 直查(把 2s 轮询变成 API 轰炸)。
            """
            nonlocal submitted, submitted_at, seen_checking
            try:
                if not submitted:
                    return FINISHED  # recheck 发送失败: 登记的轮询直接消亡(释放在途登记)
                rec = self.store.get(hash)
                if rec is None:
                    # 种子已删除: 规则源默认重置重新入队 origin, 由其删除守卫(_handle_rule)判死
                    logger.warning(f"{prefix} {hash[:8]} | 校验轮询: 种子已删除")
                    self.state.get("recheck_fails", {}).pop(hash, None)
                    if origin is not None:
                        tq.add_task(origin)
                    return FINISHED
                if rec.state_enum.is_checking:
                    seen_checking = True
                    return REQUEUE  # 仍在校验中, 下一轮轮询
                if rec.progress >= 1.0:
                    logger.info(f"{prefix} {rec.log_repr} | 校验成功")
                    if on_success is not None:
                        on_success()
                    self.state.get("recheck_fails", {}).pop(hash, None)  # 校验通过: 清除失败冷却计数
                    if auto_start:
                        self.api.torrents_start(torrent_hashes=hash)
                        logger.info(f"{prefix} {rec.log_repr} | 校验成功自动开始")
                    if origin is not None:
                        tq.add_task(origin, keep_progress=True)  # 显式保存进度: 断点续跑后续动作
                elif seen_checking:
                    # 曾见 checking 后落回未完成: 真实校验未通过(冷却仅规则源, D1)
                    if source == "rule":
                        fail_count = _bump_recheck_fail(self, hash)
                        logger.warning(f"{prefix} {rec.log_repr} | 校验未通过(第{fail_count}次, progress={rec.progress})")
                    else:
                        logger.warning(f"{prefix} {rec.log_repr} | 校验未通过(progress={rec.progress})")
                    if origin is not None:
                        tq.add_task(origin)  # 默认重置: 重走完整决策链(重新校验)
                elif time.time() - submitted_at >= CHECK_START_GIVEUP:
                    # 宽限耗尽仍未见校验启动: 判败防轮询活锁(qB 重启丢请求等极端情形);
                    # 判败后 origin 重走决策链会重新提交, 请求恢复生效后自然续上
                    if source == "rule":
                        fail_count = _bump_recheck_fail(self, hash)
                        logger.warning(
                            f"{prefix} {rec.log_repr} | "
                            f"校验启动超时({CHECK_START_GIVEUP:.0f}s 未见 checking, 第{fail_count}次, progress={rec.progress})"
                        )
                    else:
                        logger.warning(
                            f"{prefix} {rec.log_repr} | "
                            f"校验启动超时({CHECK_START_GIVEUP:.0f}s 未见 checking, progress={rec.progress})"
                        )
                    if origin is not None:
                        tq.add_task(origin)  # 默认重置: 重走完整决策链(重新校验)
                else:
                    # 未见 checking 且宽限未耗尽: recheck 尚未被 qB 应用(异步应用 + 快照滞后)
                    # 或排队未开检 —— 继续轮询, 不计失败(首样本竞态修复)
                    return REQUEUE
                return FINISHED  # 轮询子任务消亡(释放在途登记)
            except Exception as e:
                logger.error(f"{prefix} {hash[:8]} | 校验轮询异常: {e}")
                if origin is not None:
                    tq.add_task(origin)  # 默认重置: 重走完整决策链
                return FINISHED

        submitted = False  # recheck 是否发送成功(先登记后发送; 失败时轮询子任务据此消亡)
        submitted_at = time.time()  # 校验启动宽限窗口起点(recheck 发送成功时刻)
        seen_checking = False  # 本轮询周期内是否观察到过 checking 态(失败判定前提)

        task = Task(
            "check",
            "check-checking-result",
            hash=hash,
            store=self.store,
            interval=CHECK_RESULT_INTERVAL,
            handler=poll,
        )
        if not tq.add_task(task):
            # R1 已先行拒绝在途, 这里是单线程模型下的兜底(不可达; 保留防将来有第二个登记点)
            return ActionResult.skip("该校验任务已在队列中")
        try:
            self.api.torrents_recheck(torrent_hashes=hash)
            submitted = True
            submitted_at = time.time()
        except Exception as e:
            return ActionResult.fail(f"发送 recheck 失败: {e}")
        logger.info(f"{prefix} {self._ops_repr(tor)} | full-checking 校验已提交")
        if source == "rule":
            # pending: 规则记录断点, 规则任务本轮不重入队 —— 恢复由轮询子任务负责
            return ActionResult.pending("full-checking 校验已提交")
        return ActionResult.ok("校验已提交")

    # ---------- skip-checking: 跳检四阶段(含 R2 实时复核) ----------

    def ops_skip_check(
        self,
        hash: str,
        source: str = "rule",
        torrent: Optional[TorrentRecord] = None,
        auto_start: bool = False,
        has_reference: bool = True,
    ) -> ActionResult:
        """辅种跳检(高风险): 导出 → 删除(保留文件) → 确认消失 → 重加(跳过校验) → 确认出现 → 恢复快照

        自 rules/actions/skip_checking.py._execute_skip_checking 迁入(行为等价), R2 实时复核
        落在闸门通过后、导出之前 —— 两来源同时受保护(C2: 按陈旧快照执行会把用户刚删的种子
        复活; 复核在备份与删除之前, 拒绝零副作用)。

        来源差异:
        - has_reference 的「无参考跳检(高风险)」告警是规则侧语义, 仅 rule 源产生(WEB 前端
          危险确认框已承担风险告知, 不把规则告警泄漏进 WEB)。
        - 安全闸门全来源生效: 部分下载禁止跳检 / 跨规则同日去重(skip_check_day 跨来源共享,
          拒绝文案「今日已跳检过」自解释)。
        - torrent: 可选活记录; None 时经 store 取(规则侧 ctx.torrent 与缺省取值等价)。
        """
        prefix = f"ops[{source}]"
        tor = torrent if torrent is not None else self.store.get(hash)
        if tor is None:
            return ActionResult.skip(_SKIP_GONE_MSG)

        # ---- 阶段 1: 前置闸门 (任一不过 → fail/skip 返回, 无副作用) ----
        gate = self._skip_gates(hash, tor)
        if gate is not None:
            return gate

        # ---- R2 实时复核: 闸门读的是快照(≤2s 龄), 动手前重拉一次实时状态 ----
        # 种子已不在 -> 干净放弃: 发生在备份与删除之前, 零副作用、无孤儿备份(修 C2)。
        try:
            live = self.api.torrents_info(torrent_hashes=hash)
        except Exception as e:
            return ActionResult.fail(f"跳检前实时复核失败(未执行任何变更): {e}")
        if not live:
            logger.info(f"{prefix} {tor.log_repr} | 跳检放弃: {_SKIP_GONE_MSG}")
            return ActionResult.skip(_SKIP_GONE_MSG)

        # ---- 阶段 2: 准备 (导出/校验属性/布局推断, 均须在删除前完成) ----
        try:
            data = self.api.torrents_export(torrent_hash=hash)
        except Exception as e:
            return ActionResult.fail(f"导出 .torrent 失败: {e}")
        if not data:
            return ActionResult.fail("导出 .torrent 为空")

        # 重加所需的 6 属性(RE_ADD_FIELDS)存在性已由启动期 schema 校验保证(refresh 首次
        # 拉取时验证 REQUIRED_TORRENT_FIELDS); 记录对象删除后仍持有这些字段(_raw),
        # 故直接读 tor 属性即可(无需中间投影对象)

        # 布局推断依赖 content_path/save_path/文件列表(惰性缓存, filelist 前置检查已填充);
        # 删除后 store 记录已移除, 必须在此之前完成
        content_layout = self._infer_content_layout(tor, self.client)

        # 备份先于删除(崩溃安全): 删除是整条链上第一个不可逆步骤。备份若挂在重加的失败路径上,
        # 那么「删除已生效 → 重加未被 qB 接受」这一缝隙(含删除确认轮询的约 5s)内崩溃/强杀,
        # 种子从客户端消失、data 只存在于内存、state 无在途标记 —— 重启后无任何恢复凭据
        # (issue 26-09-21-1347)。备份写不进去就不删除: 此时放弃跳检没有任何损失。
        try:
            self._backup_torrent(tor, data)
        except Exception as e:
            return ActionResult.fail(f"跳检备份 .torrent 失败(未删除, 无损失): {e}")

        # ---- 阶段 3: 执行 (删除 → 确认消失 → 重加 → 确认出现 → 恢复快照) ----
        failed = self._skip_delete(hash, tor, prefix)
        if failed is not None:
            return failed
        failed = self._skip_readd(hash, tor, data, content_layout)
        if failed is not None:
            return failed

        # ---- 阶段 4: 收尾 ----
        # 无参考高风险警告(规则侧语义; 用删除前捕获的 tor: 真实流程中删除后 store 记录已移除)
        if source == "rule" and not has_reference:
            logger.warning(f"{prefix} {tor.log_repr} | 无参考跳检(高风险): "
                           f"仅文件存在与大小对比, 内容错误会传垃圾数据")
        # 跳检成功打标(skip_checking_tag): 标记该种子未经哈希校验, 后续查找参考种子时排除;
        # 标签名直接读全局 config.skip_checking_tag(默认 zSkipChecked, 不按规则覆盖);
        # 打标失败不影响跳检结果(跳检本身已完成), 仅记 warning
        skip_tag = self.config.skip_checking_tag
        if skip_tag and skip_tag not in tor.tags_set:
            try:
                self.api.torrents_add_tags(tags=[skip_tag], torrent_hashes=hash)
                logger.info(f"{prefix} {tor.log_repr} | 跳检完成, 已打标签 {skip_tag}(该种子不作参考种子)")
            except Exception as e:
                logger.warning(f"{prefix} {tor.log_repr} | 跳检打标签失败(不影响跳检结果): {e}")
        if auto_start:
            try:
                self.api.torrents_start(torrent_hashes=hash)
            except Exception as e:
                return ActionResult.fail(f"自动开始失败: {e}")
            return ActionResult.ok("skip-checking 跳检完成并自动开始")
        return ActionResult.ok("skip-checking 跳检完成")

    def _skip_gates(self, hash: str, tor: TorrentRecord) -> Optional[ActionResult]:
        """跳检前置闸门: 部分下载禁止 + 跨规则同日去重(跨来源共享)。返回 None = 全部通过。

        - 部分下载(0<progress<1)禁止: 预分配使文件尺寸=完整尺寸, filelist 尺寸检查无法
          发现未下载的零块, is_skip_checking 会把全部块标记有效 -> 零块被上传(垃圾数据)。
          仅 progress==0(全新辅种, 数据完整)可跳检; full-checking 对部分下载安全, 不设限。
        - 跨规则同日去重(全来源): 多条规则都配 checking 时, 同一种子当日只跳检一次(跳检必然
          清空本地统计, 重复跳检只会再丢一次而毫无收益); 顺带清理非当日记录(防 state 无界增长)。
        """
        progress = tor.progress
        if 0.0 < progress < 1.0:
            return ActionResult.fail(f"部分下载的种子禁止跳检(progress={progress}), 请改用 full-checking")

        today = date.today().isoformat()
        skip_day = self.state.setdefault("skip_check_day", {})
        if skip_day.get(hash) == today:
            return ActionResult.skip("今日已跳检过该种子(跨规则去重)")
        for h in [h for h, d in skip_day.items() if d != today]:
            del skip_day[h]
        return None

    def _skip_delete(self, hash: str, tor: TorrentRecord, prefix: str) -> Optional[ActionResult]:
        """跳检步骤: 删除种子(保留文件)并轮询确认已从客户端消失(qB 删除为异步)。

        返回 None = 已确认消失; ActionResult = 失败(种子未删除或消失未确认, 无损失,
        放弃跳检避免重加撞"种子已存在")。
        """
        try:
            logger.info(f"{prefix} {tor.log_repr} | 跳检删除种子(保留文件)")
            self.api.torrents_delete(torrent_hashes=hash, delete_files=False)
        except Exception as e:
            return ActionResult.fail(f"删除种子失败(未删除, 无损失): {e}")
        gone = _poll_until(lambda: not self.api.torrents_info(torrent_hashes=hash), attempts=10, interval=0.5)
        if not gone:
            # 种子没删掉(删除未生效) —— 删除前的备份也就没了意义, 清掉: 留着只剩一个孤儿
            # .torrent 文件 + 一条"待恢复"的误导性元数据(state 会指引用户去恢复一个还在的种子)
            self._clear_backup(hash)
            return ActionResult.fail("删除后种子仍在客户端, 放弃跳检(重加会撞已存在的种子)")
        return None

    def _skip_readd(self, hash: str, tor: TorrentRecord, data: bytes,
                    content_layout: Optional[str]) -> Optional[ActionResult]:
        """跳检步骤: 以跳过校验方式重加(先暂停), 轮询确认出现, 恢复删除前快照记录。

        属性直传不用 `or None` —— ratio/seeding limit 的 0/负值是有语义的(不限速/跟随
        全局), 吞掉会使重加后行为漂移到 qB 新种缺省。重加成功后 store.restore_torrent
        恢复删除前记录(保留 tracker_conf/惰性缓存): remove_torrent 会登记待报 removed,
        不恢复则重加的同 hash 种子下轮被误判为已删除(生产 BUG 2026-09-06)。

        返回 None = 成功; ActionResult = 失败(种子已从客户端移除, 已备份提示手动恢复)。
        """
        try:
            self.api.torrents_add(
                torrent_files=[data],
                save_path=tor.save_path,
                category=tor.category or None,
                tags=tor.tags or None,
                upload_limit=tor.up_limit,
                download_limit=tor.dl_limit,
                is_sequential_download=tor.seq_dl,
                is_first_last_piece_priority=tor.f_l_piece_prio,
                contentLayout=content_layout,
                ratio_limit=tor.ratio_limit,
                seeding_time_limit=tor.seeding_time_limit,
                inactive_seeding_time_limit=tor.inactive_seeding_time_limit,
                share_limit_action=tor.share_limit_action,
                is_skip_checking=True,
                is_stopped=True,
            )
        except Exception as e:
            # 备份在删除前已落盘(此处再调一次是幂等的覆盖写, 只为让失败信息带上备份路径)
            backup = self._backup_torrent(tor, data)
            return ActionResult.fail(f"重加种子失败: {e}; 种子已从客户端移除(文件保留), "
                                     f".torrent 已备份: {backup}, 请手动重加")
        appeared = _poll_until(lambda: self.api.torrents_info(torrent_hashes=hash), attempts=3, interval=0.3)
        if not appeared:
            # 种子已从客户端移除, 备份已在删除前落盘 —— 保留它(不清), 用户凭
            # skip-check-backup/<hash>.torrent + state 元数据可手动恢复; store 此刻也无记录,
            # 下轮不会执行 restore_torrent, 该种子会被误判为"用户主动删除"。
            backup = self._backup_torrent(tor, data)
            return ActionResult.fail(f"重加后未确认到种子(客户端可能尚未处理完), 请检查客户端; "
                                     f"种子已从客户端移除(文件保留), .torrent 已备份: {backup}")
        self.store.restore_torrent(tor)
        # 跳检完成: 记录跨规则同日去重(此后同种子当日任何来源的 checking 都不再跳检)
        self.state.setdefault("skip_check_day", {})[hash] = date.today().isoformat()
        # 去重标记即时落盘: 这是"今天已跳检过"的唯一凭据, 只靠退出/周期落盘的话, 跳检后
        # 崩溃会重复跳检(PT 本地统计再丢一次)。跳检是天级低频事件, 即时写一次代价可忽略 ——
        # 与备份路径的即时落盘同口径(issue 26-09-21-1347)。注意不能指望下面的 _clear_backup
        # 顺带落盘: 备份元数据为空时它提前 return, 不经过 save_state。
        self.save_state()
        # 种子已回到客户端: 删除前那份备份完成使命, 清掉(否则每次跳检都留一个孤儿文件)
        self._clear_backup(hash)
        return None

    def _infer_content_layout(self, tor, client) -> Optional[str]:
        """推断原内容布局(qB 种子信息无直接字段): 重加后数据路径必须与现存文件一致,
        跳检状态下布局错位不会自愈(直接 missingFiles/空传)。无法推断返回 None(用 qB 默认)。

        须在删除种子前调用(传入删除前捕获的记录): 删除后 store 记录已移除, 且文件列表
        惰性缓存挂在记录上(空缓存时会向已删除的种子发请求)。

        - 文件路径均以 种子名/ 开头(.torrent 自带根目录): content==save -> NoSubfolder(原布局剥根),
          content==save/种子名 -> Original
        - 无根目录(含单文件): content==save -> Original; content==save/种子名 -> Original
        """
        save = utils.path_normalize(tor.save_path)
        content = utils.path_normalize(tor.content_path or "")
        if not content:
            return None
        name = utils.path_normalize(tor.name)
        files = tor.files(client)  # store 惰性缓存(filelist 前置检查已填充)
        has_root = bool(files) and all(utils.path_normalize(f.name).startswith(f"{name}/") for f in files)
        if content == save:
            return "NoSubfolder" if has_root else "Original"
        if content == f"{save}/{name}":
            return "Original"
        return None

    def _clear_backup(self, hash: str) -> None:
        """跳检未真正移除种子时清掉删除前的备份(文件 + 元数据), 元数据立即落盘

        与 _backup_torrent 成对: 备份是"删除前的保险", 只在种子确实没回到客户端时才有意义。
        重加确认成功(种子已回)或删除未生效(种子没丢)时留着它只剩副作用 —— 一个孤儿
        .torrent 文件 + 一条指向"待恢复"的误导性元数据。清理失败只记 warning(跳检本身已完成)。
        """
        meta = self.state.get("skip_check_backup", {}).pop(hash, None)
        if not meta:
            return
        path = meta.get("path") or ""
        if path:
            try:
                os.remove(path)
            except OSError as e:
                logger.warning(f"清理跳检备份失败({path}): {e}")
        self.save_state()  # 元数据已改: 立即落盘, 否则崩溃后仍指向已删除的备份文件

    def _backup_torrent(self, tor, data: bytes) -> str:
        """删除前把 .torrent 落盘备份并记录元数据(便于手动恢复), 返回备份路径

        用删除前捕获的 tor 记录(删除后 store 记录已移除)。元数据立即落盘(非常规路径,
        不适用"仅退出时落盘"的写放大规避): 备份后程序一旦崩溃, 没有 state 里的元数据指引,
        用户不知道 .torrent 备份的存在与原始保存路径。

        调用时机是崩溃安全的关键: 必须**先于** torrents_delete(第一个不可逆步骤), 而不是
        挂在重加的失败路径上 —— 重加前那几秒缝隙内崩溃, 谁也来不及备份(issue 26-09-21-1347)。
        """
        backup_dir = os.path.join(os.path.dirname(self.state_file) or ".", "skip-check-backup")
        os.makedirs(backup_dir, exist_ok=True)
        path = os.path.join(backup_dir, f"{tor.hash}.torrent")
        with open(path, "wb") as f:
            f.write(data)
        backup_meta = self.state.setdefault("skip_check_backup", {})
        backup_meta[tor.hash] = {
            "path": path,
            "save_path": tor.save_path,
            "category": tor.category,
            "tags": tor.tags,
            "ts": time.time(),
        }
        self.save_state()
        return path
