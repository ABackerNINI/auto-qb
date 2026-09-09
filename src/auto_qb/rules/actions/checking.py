"""checking 校验动作(CheckAction): 决策链 + 参考筛选

执行体由 FullCheckingMixin(full-checking + 组内串行化闸门)与
SkipCheckingMixin(跳检四阶段)提供, 本模块只做配置解析与决策链编排。
"""
import logging

from ... import utils
from ..base import ActionResult, BaseAction, RuleContext
from .full_checking import FullCheckingMixin
from ..registry import register_action
from .skip_checking import SkipCheckingMixin

logger = logging.getLogger(__name__)


@register_action
class CheckAction(FullCheckingMixin, SkipCheckingMixin, BaseAction):
    """校验动作(checking): 用 basic_check 确定参考种子, 按有/无参考分段执行

    配置(仅 dict, fail-fast):
      - basic_check(必填): filelist(已完成且未校验的同组种子, 宽松) | piecehashes(同前且 piece
        hash 列表相同, 相对严格) | custom(运行 custom_basic_check_program_path 程序判定)
      - custom_basic_check_program_path: basic_check=custom 时必填; 参数: <种子hash> <保存路径>
      - with_reference / without_reference: 各含 mode(skip-checking|full-checking) + auto_start(默认 false)

    跳检标签名不在 spec 配置(全局统一, 校验层已列为 spec 未知键): 运行时经 ctx 读全局
    config.skip_checking_tag(默认 zSkipChecked, 默认值唯一来源在 config models)。

    决策链(想法2):
      0. 仅"暂停中未完成"种子(is_paused 且 progress<1, 如跨种添加后的 pausedDL)才校验,
         已完成(progress=1)/活跃中(下载/做种中)种子一律跳过(避免已完成种子被反复校验)
      1. 组内有活跃下载种子(is_downloading) -> skip(整组未完成, 不进行任何校验, 包括跳检)
      1.5. 组内其它成员 full-checking 在途 -> 让位等待(组内校验串行, FullCheckingMixin)
      1.6. 组内其它成员校验失败且文件映射一致 -> 结果必然相同, skip(失败推断, FullCheckingMixin)
      2. 按 basic_check 从同组"已完成且未校验"成员筛选参考种子, 并集内存 verified_references
      3. 有参考 -> with_reference 段; 无参考 -> without_reference 段
      4. skip-checking: 同日去重 -> 前置文件存在+大小检查 -> 导出->删除->重加(is_skip_checking,paused)
         -> 确认 -> auto_start(无参考时警告高风险)
         full-checking: 同步发送 recheck, 返回 pending(规则断点, 本轮不重入队), 创建校验
         结果轮询子任务(快速队列, interval=CHECK_RESULT_INTERVAL): 每 2s 轮询 store 快照; 成功
         (progress>=1) -> on_success()(晋升 verified_references(仅内存) + auto_start) + 重新
         入队 origin(resume_index 保留 -> 规则续跑执行后续动作, 由 Rule.process 统一记录执行);
         失败/异常 -> origin.reset() + 重新入队(重走决策链); 种子删除 -> 仅子任务消亡(规则任务终了)
    """
    name = "checking"

    def __init__(self, spec, ignore_error=False):
        super().__init__(spec, ignore_error)
        # spec 合法性(dict/已知键/basic_check/段结构/mode)由 config 校验阶段保证, 此处直接解析
        self.basic_check = str(spec["basic_check"])
        self.custom_program = str(spec.get("custom_basic_check_program_path") or "")
        self.with_reference = self._parse_section(spec, "with_reference")
        self.without_reference = self._parse_section(spec, "without_reference")

    def _skip_tag(self, ctx) -> str:
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

    def execute(self, ctx: RuleContext):
        if ctx.dry_run:
            return ActionResult.ok("校验决策链(状态判定+组内下载判定+组内校验串行/失败推断+参考确定+分段执行)")
        manager = ctx.manager

        # TODO: 未完成且暂停的种子若 recheck 后仍未完成，下一轮会再次校验, 需处理

        # 决策链 0: 只校验"暂停中未完成"的种子(跨种添加后的典型状态), 其余状态一律跳过:
        # - 已完成(progress>=1, 无论状态): 已通过哈希校验, 重复 recheck/跳检无意义
        # - 活跃中(downloading/uploading 等非暂停): 正在运行, 无需校验
        # 此闸门覆盖 full-checking/skip-checking 及有/无任务队列全部路径, 修复完成种子被反复校验的问题
        if not (ctx.torrent.state_enum.is_stopped and ctx.torrent.progress < 1.0):
            return ActionResult.skip("种子非暂停中未完成状态, 无需校验")

        # 决策链 1: 组内有活跃下载种子 -> 整组未完成, 不进行任何校验(包括跳检)
        members = manager._group_members(ctx.hash)
        if manager._group_has_downloading(members):
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

        # 决策链 2: 确定参考种子(basic_check 模式 + 内存 verified_references 并集)
        reference = self._find_reference(ctx, members)

        # 决策链 3: 有参考 -> with_reference 段; 无参考 -> without_reference 段
        segment = self.with_reference if reference else self.without_reference

        # 跳过未启用的检查
        if segment["enabled"] is False:
            which = "有参考" if segment is self.with_reference else "无参考"
            return ActionResult.skip(f"{which}校验段未启用")

        # 决策链 4: 前置检查: 文件全部存在且大小一致
        # 虽然同group文件已经确定存在且大小一致, 但为了安全, 再次检查
        err = manager.check_filelist(ctx.api, ctx.torrent)
        if err is not None:
            return ActionResult.skip(f"全量校验前置检查未通过: {err}")

        if segment["mode"] == "full-checking":
            return self._execute_full_checking(ctx, segment)
        return self._execute_skip_checking(ctx, segment, bool(reference))

    # TODO: 优化为has_reference() -> bool, 提前返回
    def _find_reference(self, ctx: RuleContext, members: list) -> list:
        """按 basic_check 模式从组内已完成且未校验成员筛选参考种子, 并集内存 verified_references(排除自身)

        带 skip_checking_tag 标签的种子(跳检成功, 未经哈希校验)一律排除: 其数据可信度仅来自
        文件存在与大小一致, 不能作为其它种子跳检/校验的参考, 防止"未验证"经参考链传播。
        标签名运行时经 ctx 读全局 config.skip_checking_tag(见 _skip_tag)。
        """
        tag = self._skip_tag(ctx)

        def _is_tagged(t) -> bool:
            return bool(tag) and tag in t.tags_set

        # 候选即排除带标种子(避免 piecehashes 模式对其发无意义的 API 请求)
        candidates = [
            c for c in ctx.manager._group_reference_candidates(members)
            if c.hash != ctx.hash and not _is_tagged(c)
        ]
        refs = []
        if self.basic_check == "filelist":
            refs = list(candidates)  # 分组已保证文件列表相同, 无需重复对比
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
                            refs.append(cand)
                    except Exception as e:
                        logger.warning(f"获取参考种子 piece hashes 失败({cand.hash}): {e}")
        else:  # custom: 运行自定义程序判定候选
            refs = [c for c in candidates if self._run_custom_check(ctx, c)]
        # 内存 verified_references 并集: 历史 full-checking 通过的种子也可作参考(重启后重新积累)
        by_hash = ctx.manager._group_by_hash()
        own = ctx.hash
        for h in ctx.manager.store.verified_references:
            if h in members and h != own and h in by_hash:
                refs.append(by_hash[h])
        # 去重(按 hash), 过滤无效与带跳检标签的种子(verified_references 并集在此统一排除)
        seen, result = set(), []
        for t in refs:
            if t is None or t.hash in seen or _is_tagged(t):
                continue
            seen.add(t.hash)
            result.append(t)
        return result

    # TODO: 重新设计自定义校验流程
    def _run_custom_check(self, ctx: RuleContext, candidate) -> bool:
        """运行自定义 basic_check 程序判定候选是否为参考种子, 参数: <候选hash> <候选保存路径>"""
        import subprocess
        try:
            r = subprocess.run(
                [self.custom_program, candidate.hash, candidate.save_path],
                capture_output=True,
                text=True,
                timeout=600,
            )
            if r.returncode == 0:
                return True
            logger.info(f"自定义校验判定非参考({candidate.hash[:8]}): rc={r.returncode} {r.stderr.strip()[:200]}")
            return False
        except Exception as e:
            logger.warning(f"自定义校验程序执行异常({candidate.hash[:8]}): {e}")
            return False
