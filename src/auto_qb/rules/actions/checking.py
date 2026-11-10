"""checking 校验动作(CheckAction): 决策链 + 参考筛选

本模块只做配置解析与决策链编排(0-4 闸门)。执行体经 FullCheckingMixin /
SkipCheckingMixin 委托到 ops 模块(core/modules/ops_mod.OpsModule, rules → ops ← web,
plan 26-09-30-0109 P2'): full-checking 提交+轮询在 ctx.ops.recheck, 跳检四阶段在
ctx.ops.skip_check; 组内串行化闸门(决策链 1.5)与失败推断闸门(1.6)留在 FullCheckingMixin。
"""
import logging
import subprocess
from typing import Any

from ...infra import utils
from ..base import ActionResult, BaseAction, RuleContext
from ..checking_meta import RECHECK_COOLDOWN_DEFAULT
from .full_checking import FullCheckingMixin
from ..registry import register_action
from .skip_checking import SkipCheckingMixin

logger = logging.getLogger(__name__)

# custom 程序单次执行超时缺省(C27 超时保险丝的缺省档; schema 侧同值写作 "10M"): 超时保险丝
# 必须无条件存在(变异测试真洞 #32/#35), 可配置只调档位, 不提供「关掉」语义
CUSTOM_CHECK_TIMEOUT_DEFAULT = 600.0


@register_action(validator="checking")
class CheckAction(FullCheckingMixin, SkipCheckingMixin, BaseAction):
    """校验动作(checking): 用 basic_check 确定参考种子, 按有/无参考分段执行

    配置(仅 dict, fail-fast):
      - basic_check(必填): filelist(已完成且未校验的同组种子, 宽松) | piecehashes(同前且 piece
        hash 列表相同, 相对严格) | custom(运行 custom_basic_check_program_path 程序判定)
      - custom_basic_check_program_path: basic_check=custom 时必填; 参数: <种子hash> <保存路径>
      - custom_basic_check_timeout: custom 程序单次执行超时(时间串, 缺省 600s), 超时该候选视为非参考
      - recheck_fail_cooldown: 校验失败冷却窗口(时间串, 缺省 1h, 不可关闭), full-checking 判
        FAILED 后窗口内不再重复校验(记录/清除在 ops 层, 见决策链 0.5)
      - with_reference / without_reference: 各含 mode(skip-checking|full-checking) + auto_start(默认 false)

    跳检标签名不在 spec 配置(全局统一, 校验层已列为 spec 未知键): 运行时经 ctx 读全局
    config.skip_checking_tag(默认 zSkipChecked, 默认值唯一来源在 config models)。

    决策链(想法2):
      dedup. 跨规则同日去重(26-11-05-0019, 排最前): 当日已跳检成功过 -> skip「今日已跳检过
         该种子(跨规则去重)」; 谓词经 ctx.ops.skip_checked_today 只读 helper(与 ops 闸门组
         同源)。必须排在链 0 之前 —— 跳检成功 ⇒ 种子必已完成 ⇒ 链 0「非暂停中未完成」恒先拦,
         ops dedup 闸门对规则源结构性不可达(与 ops 侧 26-10-11-2045 同构)
      0. 仅"暂停中未完成"种子(is_paused 且 progress<1, 如跨种添加后的 pausedDL)才校验,
         已完成(progress=1)/活跃中(下载/做种中)种子一律跳过(避免已完成种子被反复校验)
      0.5. 校验失败冷却窗口(26-11-08-1717): 该种子处于失败冷却窗口内 -> skip(记录点在 ops
         层轮询 FAILED 判定, rule 源; 不消耗 recheck_fails 额度, 与其分工见 execute 注释)
      1. 组内有活跃下载种子(is_downloading) -> skip(整组未完成, 不进行任何校验, 包括跳检)
      1.5. 组内其它成员 full-checking 在途 -> 让位等待(组内校验串行, FullCheckingMixin)
      1.6. 组内其它成员校验失败且文件映射一致 -> 结果必然相同, skip(失败推断, FullCheckingMixin;
           记录指向已完成/已删除成员时先自愈清除 —— 假失败不得参与推断)
      2. 判组内有无参考种子(basic_check 模式首个命中即提前返回, 并集内存 verified_references)
      3. 有参考 -> with_reference 段; 无参考 -> without_reference 段
      4. skip-checking: 同日去重 -> 自身当日校验失败 -> skip(26-10-05-0402 G9 镜像, mode-scoped:
         谓词与 WEB 侧 ops G9 同源, full-checking 治疗路径不受影响) -> 前置文件存在+大小检查 ->
         导出->删除->重加(is_skip_checking,paused)
         -> 确认 -> auto_start(无参考时警告高风险)
         full-checking: 同步发送 recheck, 返回 pending(规则断点, 本轮不重入队), 创建校验
         结果轮询子任务(快速队列, interval=CHECK_RESULT_INTERVAL): 每 2s 轮询 store 快照; 成功
         (progress>=1) -> on_success()(晋升 verified_references(仅内存) + auto_start) + 重新
         入队 origin(resume_index 保留 -> 规则续跑执行后续动作, 由 Rule.process 统一记录执行);
         失败(曾见 checking 后落回未完成, 或 CHECK_START_GIVEUP 宽限耗尽仍未开检)/异常 ->
           origin.reset() + 重新入队(重走决策链); 种子删除 -> 仅子任务消亡(规则任务终了);
           宽限窗口内「未见 checking」的样本只 REQUEUE 不计败(首样本竞态修复)
    """
    name = "checking"

    def __init__(self, spec: Any) -> None:
        super().__init__(spec)
        # spec 合法性(dict/已知键/basic_check/段结构/mode)由 config 校验阶段保证, 此处直接解析
        self.basic_check = str(spec["basic_check"])
        self.custom_program = str(spec.get("custom_basic_check_program_path") or "")
        # custom 程序超时(时间串如 "10M"/"600S", parse_time): 格式/正值由 config 校验期
        # fail-fast(_validate_checking_action_spec), 此处直接解析; 键缺省 = 600s 缺省档
        timeout_raw = spec.get("custom_basic_check_timeout")
        self.custom_timeout = (
            utils.parse_time(timeout_raw) if timeout_raw not in (None, "") else CUSTOM_CHECK_TIMEOUT_DEFAULT
        )
        # 校验失败冷却窗口(26-11-08-1717, 时间串如 "1H"/"30M"): full-checking 判 FAILED 后
        # 窗口内不再重复校验(决策链 0.5)。正值由 config 校验期 fail-fast(_validate_checking_
        # action_spec, 不可关闭 —— 窗口只在真实校验失败后生效), 此处直接解析; 键缺省 = 1h
        # 缺省档。键放动作 spec 而非全局 config: 唯一消费方是本闸门(ops 层记录时间戳/成功
        # 清除都不需要窗口值), 与 custom_basic_check_timeout 同形制。
        cooldown_raw = spec.get("recheck_fail_cooldown")
        self.recheck_fail_cooldown = (
            utils.parse_time(cooldown_raw) if cooldown_raw not in (None, "") else RECHECK_COOLDOWN_DEFAULT
        )
        self.with_reference = self._parse_section(spec, "with_reference")
        self.without_reference = self._parse_section(spec, "without_reference")

    def _skip_tag(self, ctx: RuleContext) -> str:
        """跳检成功标签名: 直接读全局 config.skip_checking_tag(全局统一, 不按规则覆盖)"""
        return ctx.manager.config.skip_checking_tag

    @staticmethod
    def _parse_section(spec: dict, name: str) -> dict:
        if name not in spec:
            return {"enabled": False, "mode": "", "auto_start": False}

        seg = spec[name]
        return {
            "enabled": utils.parse_bool(seg.get("enabled", False)),
            "mode": str(seg.get("mode")),
            "auto_start": utils.parse_bool(seg.get("auto_start", False)),
        }

    def execute(self, ctx: RuleContext) -> ActionResult:
        if ctx.dry_run:
            return ActionResult.ok("校验决策链(状态判定+失败冷却+组内下载判定+组内校验串行/失败推断+参考确定+分段执行)")
        manager = ctx.manager

        # 跨规则同日去重(26-11-05-0019): 排最前 —— 谓词一次 dict 查询全链最便宜(对齐 ops 侧
        # dedup 排最前先例, ops_verdict._skip_gates_detail); 只读 ops 的 skip_check_day(经
        # skip_checked_today 单点), 不碰 qB 快照, 不属 S2 让位闸门防的「陈旧状态出决策」面。
        # 覆盖 skip/full 两模式: 跳检成功 ⇒ 数据已验证, 同日 full recheck 同样无收益; 边缘
        # (当日删种重加后 recheck 被拦)方向保守且次日自愈, 与 ops 侧跳检 dedup-first 口径一致。
        if manager.ctx.ops.skip_checked_today(ctx.hash):
            return ActionResult.skip("今日已跳检过该种子(跨规则去重)")

        # S2 deferral 闸门(D-3, A 系 26-10-13-0540): 目标种子或**其所在组任一成员**刚被自有
        # 停/起、qB 快照尚未回流 ⇒ 决策链 0(暂停中未完成)/链 1(组内有活跃下载)读到的状态陈旧,
        # 本轮不出决策、让位下一 tick(收回陈旧-放行窗口)。
        # 用 skip(而非 pending): pending 需轮询子任务恢复 origin, 本闸无此驱动, 会丢任务;
        # task 线的「下一 tick 重排」由 D-1 队列级闸门承担(qbmanager._own_write_defer_gate),
        # 本闸补拦事件即时分派等不经队列的路径。有界: own_writes 逐出/TTL 到期即恢复。
        if manager.store.own_write_pending(ctx.hash):
            return ActionResult.skip("本程序刚下发过停/起操作, 状态尚未从 qB 回流; 本轮校验决策让位下一 tick")

        # 决策链 0: 只校验"暂停中未完成"的种子(跨种添加后的典型状态), 其余状态一律跳过:
        # - 已完成(progress>=1, 无论状态): 已通过哈希校验, 重复 recheck/跳检无意义
        # - 活跃中(downloading/uploading 等非暂停): 正在运行, 无需校验
        # 此闸门覆盖 full-checking/skip-checking 及有/无任务队列全部路径, 修复完成种子被反复校验的问题
        if not (ctx.torrent.state_enum.is_stopped and ctx.torrent.progress < 1.0):
            return ActionResult.skip("种子非暂停中未完成状态, 无需校验")

        # 决策链 0.5: 校验失败冷却窗口(26-11-08-1717 销 TODO): full-checking 判定 FAILED 后
        # (生效后未完成 / progress 回落), 记录点在 ops 层轮询终态(rule 源); 数据不随重试改变,
        # 窗口内重试只烧 I/O 与 recheck_fails 额度 —— 直接 skip, 一次失败即冷却, 不烧 3 次
        # 失败额度。与 ops 层 3 次/日失败冷却(recheck_fails)分工: 本闸在前(不消耗额度),
        # recheck_fails 在提交点兜底(窗口过期后的重试失败仍被它计数, 3 次/日封顶)。
        # WEB 源不经决策链(ctx.ops.recheck 直达), 手动排障不受限 —— 记录路径只认 rule 源
        # 失败; 清除路径在校验成功时全来源执行(见 ops_mod SUCCESS 分支), WEB 语义不受影响。
        # 窗口时长按本动作 spec(recheck_fail_cooldown)取值;
        # 记录 {hash: 失败时刻} 在 state_file(键 RECHECK_COOLDOWN_KEY), 时间戳过期自然失效,
        # 校验通过时 ops 层清除(pop 先例对齐 recheck_fails)。
        cooldown_remain = manager.ctx.ops.recheck_cooldown_remaining(ctx.hash, self.recheck_fail_cooldown)
        if cooldown_remain > 0:
            return ActionResult.skip(
                f"校验失败冷却中(距上次校验失败 {self.recheck_fail_cooldown - cooldown_remain:.0f}s, "
                f"窗口剩余 {cooldown_remain:.0f}s), 窗口内不重复校验"
            )

        # 决策链 1: 组内有活跃下载种子 -> 整组未完成, 不进行任何校验(包括跳检)
        grouping = manager.host.get("grouping")
        members = grouping._group_members(ctx.hash)
        if grouping._group_has_downloading(members):
            return ActionResult.skip("组内有种子正在下载, 整组未完成, 不进行任何校验")

        # 决策链 1.5: 组内已有其它成员 full-checking 在途 -> 让位等待, 完成后重走决策链按结果分流
        # (组内成员共享同一物理文件, 并行全量校验只有重复 I/O; 等待成功者晋升 verified_references)
        wait = self._wait_for_group_checking(ctx, members)
        if wait is not None:
            return wait

        # 决策链 1.6: 组内其它成员校验失败且文件映射一致(同一物理数据) -> 结果必然相同, 不再校验
        inferred = self._skip_on_group_check_failed(ctx, members)
        if inferred is not None:
            return inferred

        # 决策链 2: 判组内有无参考种子(basic_check 模式谓词 + 内存 verified_references 并集,
        # 找到首个即提前返回)
        reference = self.has_reference(ctx, members)

        # 决策链 3: 有参考 -> with_reference 段; 无参考 -> without_reference 段
        segment = self.with_reference if reference else self.without_reference

        # 跳过未启用的检查
        if segment["enabled"] is False:
            which = "有参考" if segment is self.with_reference else "无参考"
            return ActionResult.skip(f"{which}校验段未启用")

        # 决策链 4(skip-checking 段): 自身当日校验失败 -> 不再跳检(26-10-05-0402 G9 规则侧镜像)
        # 谓词经 ctx.ops.self_recheck_failed_today(单点 checking_meta.self_recheck_failed_today,
        # 与 WEB 侧 ops_verdict G9 同源)。规则侧自动化无 force 概念, 保守硬 skip; WEB 侧同谓词为
        # case-2 可强制 —— 两边强度差异是拍板 D2' 的故意的。mode-scoped 到 skip-checking:
        # full-checking 是自身失败种子的唯一翻案路径(治疗路径保护, 拍板 D4), 不被拦。
        if segment["mode"] == "skip-checking" and manager.ctx.ops.self_recheck_failed_today(ctx.hash):
            return ActionResult.skip("该种子今日校验失败, 数据完整性未证实, 不再跳检; "
                                     "请改用 full-checking 修复(通过即解除, 次日计数重置)")

        # 决策链 4: 前置检查: 文件全部存在且大小一致
        # 虽然同group文件已经确定存在且大小一致, 但为了安全, 再次检查
        err = manager.ctx.ops.check_filelist(ctx.api, ctx.torrent)
        if err is not None:
            return ActionResult.skip(f"全量校验前置检查未通过: {err}")

        if segment["mode"] == "full-checking":
            return self._execute_full_checking(ctx, segment)
        return self._execute_skip_checking(ctx, segment, reference)

    def has_reference(self, ctx: RuleContext, members: list) -> bool:
        """判组内有无可用参考种子: 按 basic_check 模式找到首个即提前返回, 并集内存 verified_references

        带 skip_checking_tag 标签的种子(跳检成功, 未经哈希校验)一律排除: 其数据可信度仅来自
        文件存在与大小一致, 不能作为其它种子跳检/校验的参考, 防止"未验证"经参考链传播。
        标签名运行时经 ctx 读全局 config.skip_checking_tag(见 _skip_tag)。
        """
        tag = self._skip_tag(ctx)

        def _is_tagged(t: Any) -> bool:
            return bool(tag) and tag in t.tags_set

        # 候选即排除带标种子(避免 piecehashes 模式对其发无意义的 API 请求)
        grouping = ctx.manager.host.get("grouping")
        candidates = [
            c for c in grouping._group_reference_candidates(members) if c.hash != ctx.hash and not _is_tagged(c)
        ]
        if self.basic_check == "filelist":
            if candidates:  # 分组已保证文件列表相同, 无需重复对比
                return True
        elif self.basic_check == "piecehashes":
            # 严格模式: 候选须与目标种子 piece hash 列表完全相同(torrents_piece_hashes API, 无需导出 .torrent)
            try:
                target = ctx.api.torrents_piece_hashes(ctx.hash)
            except Exception as e:
                logger.warning(f"获取 piece hashes 失败({ctx.hash}), 视为无参考: {e}")
                target = None
            if target is not None:
                for cand in candidates:
                    try:
                        if ctx.api.torrents_piece_hashes(cand.hash) == target:
                            return True
                    except Exception as e:
                        logger.warning(f"获取参考种子 piece hashes 失败({cand.hash}): {e}")
        else:  # custom: 运行自定义程序判定候选, 首个通过即提前返回(不再对后续候选发请求)
            for cand in candidates:
                if self._run_custom_check(ctx, cand):
                    return True
        # 内存 verified_references 并集: 历史 full-checking 通过的组内成员也可作参考(重启后重新
        # 积累), 排除自身与带标种子(排除语义与候选路径一致)
        by_hash = grouping._group_by_hash()
        for h in ctx.manager.store.verified_references:
            if h in members and h != ctx.hash and h in by_hash and not _is_tagged(by_hash[h]):
                return True
        return False

    def _run_custom_check(self, ctx: RuleContext, candidate: Any) -> bool:
        """运行自定义 basic_check 程序判定候选是否为参考种子, 参数: <候选hash> <候选保存路径>

        判据不变: rc==0 即参考(输出不参与判定)。错误面三分类(对齐 core/traffic_source/agent
        run_claim 形制): 超时 / OSError(程序缺失、不可执行等环境性失败, 如容器未装程序) ->
        WARNING 视为非参考(可自愈, 不按错误刷屏); 其它异常 -> ERROR; 非零 rc -> INFO(程序正常
        给出「非参考」结论)。timeout 恒传 subprocess.run(C27 守阵: 超时保险丝必须无条件存在,
        挂死的外部程序不得无限阻塞规则线程)。
        """
        try:
            r = subprocess.run(
                [self.custom_program, candidate.hash, candidate.save_path],
                capture_output=True,
                text=True,
                timeout=self.custom_timeout,
            )
        except subprocess.TimeoutExpired:
            logger.warning(
                f"自定义校验程序超时(配置 {self.custom_timeout:g}s 未结束, {self.custom_program} "
                f"候选 {candidate.hash[:8]}), 视为非参考"
            )
            return False
        except OSError as e:
            logger.warning(f"自定义校验程序执行失败({self.custom_program} 候选 {candidate.hash[:8]}): {e}, 视为非参考")
            return False
        except Exception as e:
            logger.error(f"自定义校验程序执行异常({candidate.hash[:8]}): {e}")
            return False
        if r.returncode == 0:
            return True
        logger.info(f"自定义校验判定非参考({candidate.hash[:8]}): rc={r.returncode} {r.stderr.strip()[:200]}")
        return False
