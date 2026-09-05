"""内置动作插件: add_tags, remove_tags, add_category, remove_category, start, stop,
checking(基础检查确定参考种子 + 有/无参考分段校验), move_to, reannounce,
upload_speed_limit, download_speed_limit"""
import logging
import os
import time
from datetime import date
from typing import List, Optional
from qbittorrentapi import TorrentDictionary

from .. import utils
from ..config import ConfigError
from ..taskqueue import Task
from ..torrents import TorrentRecord
from .base import ActionResult, BaseAction, RuleContext
from .registry import register_action

logger = logging.getLogger(__name__)

# full-checking 校验结果轮询间隔(秒): 与主循环 MAIN_TICK 对齐, 需求指定 2s
CHECK_RESULT_INTERVAL = 2.0

# 同一种子当日连续校验失败上限: 防止损坏文件导致 recheck 死循环(次日重置)
RECHECK_FAIL_LIMIT = 3


def _recheck_fail_count(manager, hash: str) -> int:
    """同一种子当日连续校验失败次数(按自然日重置, 与 upload_size_today 口径一致)"""
    rec = manager.state.get("recheck_fails", {}).get(hash)
    if rec and rec.get("date") == date.today().isoformat():
        return rec.get("count", 0)
    return 0


def _bump_recheck_fail(manager, hash: str) -> int:
    """累加当日校验失败次数并返回当前次数"""
    fails = manager.state.setdefault("recheck_fails", {})
    rec = fails.setdefault(hash, {"date": "", "count": 0})
    today = date.today().isoformat()
    if rec.get("date") != today:
        rec["date"] = today
        rec["count"] = 0
    rec["count"] += 1
    return rec["count"]


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


@register_action
class AddTagsAction(BaseAction):
    """添加标签, 支持 ${required_seeding_time} 变量"""
    name = "add_tags"

    def __init__(self, spec, ignore_error=False):
        super().__init__(spec, ignore_error)
        self.tags = list(spec) if isinstance(spec, list) else [spec]

    def execute(self, ctx: RuleContext):
        tracker_conf = ctx.torrent.tracker_conf
        tags = [utils.replace_vars(t, tracker_conf) for t in self.tags]
        current = ctx.torrent.tags_set
        new = [t for t in tags if t and t not in current]
        if not new:
            return ActionResult.skip(f"标签已存在: {tags}")
        if not ctx.dry_run:
            ctx.api.torrents_add_tags(tags=new, torrent_hashes=ctx.hash)
        return ActionResult.ok(f"{new}")


@register_action
class RemoveTagsAction(BaseAction):
    """删除标签, 支持 regex: 和 ${required_seeding_time} 变量"""
    name = "remove_tags"

    def __init__(self, spec, ignore_error=False):
        super().__init__(spec, ignore_error)
        self.patterns = list(spec) if isinstance(spec, list) else [spec]

    def execute(self, ctx: RuleContext):
        current_tags = ctx.torrent.tags_set
        expanded_patterns = self._expand_patterns(ctx)
        to_remove = [t for t in current_tags if utils.match_tag_patterns(t, expanded_patterns)]

        if not to_remove:
            return ActionResult.skip("无匹配标签")
        if not ctx.dry_run:
            ctx.api.torrents_remove_tags(tags=list(to_remove), torrent_hashes=ctx.hash)
        return ActionResult.ok(f"{to_remove}")

    def _expand_patterns(self, ctx) -> List[str]:
        return [utils.replace_vars(pat, ctx.torrent.tracker_conf) for pat in self.patterns]


@register_action
class AddCategoryAction(BaseAction):
    """添加分类, 支持 ${required_seeding_time} 变量和 overwrite 覆盖"""
    name = "add_category"

    def __init__(self, spec, ignore_error=False):
        super().__init__(spec, ignore_error)
        self.format = str(spec.get("format", ""))
        self.overwrite = utils.parse_bool(spec.get("overwrite", False))

    def execute(self, ctx: RuleContext):
        category = utils.replace_vars(self.format, ctx.torrent.tracker_conf)
        old_category = ctx.torrent.category or ""
        if old_category == category:
            return ActionResult.skip("分类已设置")

        auto_categories = ctx.manager.state.setdefault("auto_categories", {})

        # 定义一个内部函数可以利用if短路
        def can_update_previous():
            previous_auto_category = auto_categories.get(ctx.hash)
            return old_category == previous_auto_category

        if old_category and not self.overwrite and not can_update_previous():
            return ActionResult.skip(f"已有分类 {old_category}, 不覆盖")

        if not ctx.dry_run:
            try:
                if category not in ctx.manager.store.all_categories():  # 走 store 惰性缓存
                    ctx.api.torrents_create_category(name=category)
            except Exception:
                pass
            ctx.api.torrents_set_category(category=category, torrent_hashes=ctx.hash)
            auto_categories[ctx.hash] = category
        return ActionResult.ok(category)


@register_action
class RemoveCategoryAction(BaseAction):
    """清空分类"""
    name = "remove_category"

    def execute(self, ctx: RuleContext):
        if not (ctx.torrent.category or "").strip():
            return ActionResult.skip("分类为空")
        if not ctx.dry_run:
            ctx.api.torrents_set_category(category="", torrent_hashes=ctx.hash)
        return ActionResult.ok("清空分类")


@register_action
class StartAction(BaseAction):
    """开始种子"""
    name = "start"

    def execute(self, ctx: RuleContext):
        if not ctx.torrent.state_enum.is_stopped:
            return ActionResult.skip("已开始")
        if not ctx.dry_run:
            ctx.api.torrents_start(torrent_hashes=ctx.hash)
        return ActionResult.ok("开始")


@register_action
class StopAction(BaseAction):
    """暂停种子"""
    name = "stop"

    def execute(self, ctx: RuleContext):
        if ctx.torrent.state_enum.is_stopped:
            return ActionResult.skip("已停止")
        if not ctx.dry_run:
            ctx.api.torrents_stop(torrent_hashes=ctx.hash)
        return ActionResult.ok("暂停")


@register_action
class CheckAction(BaseAction):
    """校验动作(checking): 用 basic_check 确定参考种子, 按有/无参考分段执行

    配置(仅 dict, fail-fast):
      - basic_check(必填): filelist(已完成+上传中的同组种子, 宽松) | piecehashes(同前且 piece
        hash 列表相同, 相对严格) | custom(运行 custom_basic_check_program_path 程序判定)
      - custom_basic_check_program_path: basic_check=custom 时必填; 参数: <种子hash> <保存路径>
      - with_reference / without_reference: 各含 mode(skip-checking|full-checking) + auto_start(默认 false)

    决策链(想法2):
      0. 仅"暂停中未完成"种子(is_paused 且 progress<1, 如跨种添加后的 pausedDL)才校验,
         已完成(progress=1)/活跃中(下载/做种中)种子一律跳过(避免已完成种子被反复校验)
      1. 组内有活跃下载种子(is_downloading) -> skip(整组未完成, 不进行任何校验, 包括跳检)
      2. 按 basic_check 从同组"已完成+上传中"成员筛选参考种子, 并集内存 verified_references
      3. 有参考 -> with_reference 段; 无参考 -> without_reference 段
      4. skip-checking: 同日去重 -> 前置文件存在+大小检查 -> 导出->删除->重加(is_skip_checking,paused)
         -> 确认 -> auto_start(无参考时警告高风险)
         full-checking: 同步发送 recheck, 触发任务让位(defer)并返回 pending(规则断点), 创建校验
         结果轮询任务(快速队列, interval=CHECK_RESULT_INTERVAL): 每 2s 轮询 store 快照; 成功
         (progress>=1) -> 触发任务 resume(触发 resume_cb: 晋升 verified_references(仅内存) +
         auto_start; resume_index 保留 -> 规则续跑执行后续动作, 由 Rule.process 统一记录执行);
         失败/删除/异常 -> 清断点 + reschedule 重新入队重走决策链(再次校验)
    """
    name = "checking"
    _VALID_BASIC = ("filelist", "piecehashes", "custom")
    _VALID_MODES = ("skip-checking", "full-checking")

    def __init__(self, spec, ignore_error=False):
        super().__init__(spec, ignore_error)
        if not isinstance(spec, dict):
            raise ConfigError("checking 动作只接受 dict 配置, 旧字符串形式已移除, 请参考示例改写")
        self._validate(spec)
        self.basic_check = str(spec["basic_check"])
        self.custom_program = str(spec.get("custom_basic_check_program_path") or "")
        self.with_reference = self._parse_section(spec, "with_reference")
        self.without_reference = self._parse_section(spec, "without_reference")

    def _validate(self, spec: dict):
        known = {"basic_check", "custom_basic_check_program_path", "with_reference", "without_reference"}
        unknown = set(spec) - known
        if unknown:
            raise ConfigError(
                f"checking 动作未知配置键: {sorted(unknown)} "
                f"(always_check_first_one/poll_timeout/顶层 mode 已移除, 校验模式请在 with_reference/without_reference 段内配置)"
            )
        if "basic_check" not in spec:
            raise ConfigError("checking 动作必须配置 basic_check")
        if spec["basic_check"] not in self._VALID_BASIC:
            raise ConfigError(f"checking 动作 basic_check 取值非法: {spec['basic_check']}, 可选: {list(self._VALID_BASIC)}")
        if spec["basic_check"] == "custom" and not str(spec.get("custom_basic_check_program_path") or "").strip():
            raise ConfigError("checking 动作 basic_check=custom 时必须配置 custom_basic_check_program_path")
        for seg in ("with_reference", "without_reference"):
            if seg not in spec:
                continue
            if not isinstance(spec[seg], dict):
                raise ConfigError(f"checking 动作 {seg} 段必须是 dict")
            seg_mode = str(spec[seg].get("mode", ""))
            if seg_mode not in self._VALID_MODES:
                raise ConfigError(f"checking 动作 {seg}.mode 取值非法: {seg_mode}, 可选: {list(self._VALID_MODES)}")

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
            return ActionResult.ok("校验决策链(状态判定+组内下载判定+参考确定+分段执行)")
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
        """按 basic_check 模式从组内已完成+上传中成员筛选参考种子, 并集内存 verified_references(排除自身)"""
        candidates = [c for c in ctx.manager._group_reference_candidates(members) if c.hash != ctx.hash]
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
        # 去重(按 hash), 过滤无效
        seen, result = set(), []
        for t in refs:
            if t is None or t.hash in seen:
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

    def _execute_full_checking(self, ctx: RuleContext, segment: dict):
        """full-checking: 同步发送 recheck 后创建校验结果轮询任务(快速队列, interval=CHECK_RESULT_INTERVAL)

        触发流程:
          1) 同步发送 torrents_recheck(API 同步返回, 校验后台异步), 失败则直接失败(不建任务)
          2) 触发任务(origin)让位(defer: 不入队不消亡), 动作返回 pending(规则断点), 由轮询任务
             在完成后决定恢复方式
          3) 轮询任务每 CHECK_RESULT_INTERVAL 秒检查 store 快照, 退出 checking* 即完成:
             成功(progress>=1) -> origin.resume(触发 resume_cb: 晋升 verified_references +
               auto_start; resume_index 保留 -> 规则续跑执行后续动作, 执行历史由 Rule.process 统一记录)
             失败(progress<1)/种子删除/异常 -> 清断点 + origin.reschedule(重走决策链再次校验)
        """
        manager = ctx.manager
        hash = ctx.hash

        # 失败冷却: 当日连续校验失败达上限后不再重试(防损坏文件导致 recheck 死循环), 次日重置
        if _recheck_fail_count(manager, hash) >= RECHECK_FAIL_LIMIT:
            return ActionResult.skip(f"校验连续失败 {RECHECK_FAIL_LIMIT} 次, 今日不再重试")

        tq = ctx.manager.task_queue
        origin = getattr(ctx, "task", None)  # 触发本次校验的规则任务(任务队列驱动); 外部入口为 None
        rule_name = ctx.rule_name
        api = ctx.api
        auto_start = segment["auto_start"]

        def on_success():
            """校验成功完成处理: 晋升参考(仅内存, 不写 state_file) + auto_start
            执行历史由恢复后的规则任务(Rule.process 续跑)统一记录
            """
            manager.store.verified_references.add(hash)
            manager.state.get("recheck_fails", {}).pop(hash, None)  # 校验通过: 清除失败冷却计数
            if auto_start and not ctx.dry_run:
                api.torrents_start(torrent_hashes=hash)
                logger.info(f"规则[{rule_name}] {ctx.torrent.log_repr} | 校验成功自动开始")

        def poll(task: Task, dry_run: bool) -> bool:
            try:
                if manager.store.get(hash) is None:
                    # 种子已删除: 让位任务清断点重新入队(下一轮规则执行时自然消亡)
                    logger.warning(f"规则[{rule_name}] {hash[:8]} | 校验轮询: 种子已删除")
                    manager.state.get("recheck_fails", {}).pop(hash, None)
                    if origin is not None:
                        origin.resume_index = None
                        tq.reschedule(origin, time.time())
                    return False
                if ctx.torrent.state_enum.is_checking:
                    return True  # 仍在校验中, 下一轮轮询
                if ctx.torrent.progress >= 1.0:
                    logger.info(f"规则[{rule_name}] {ctx.torrent.log_repr} | 校验成功")
                    if origin is not None:
                        origin.resume_cb = on_success
                        tq.resume(origin, time.time())  # resume_index 保留 -> 规则续跑后续动作
                    else:
                        on_success()  # 无触发任务(外部入口): 直接执行完成处理
                else:
                    fail_count = _bump_recheck_fail(manager, hash)
                    logger.warning(
                        f"规则[{rule_name}] {ctx.torrent.log_repr} | "
                        f"校验未通过(第{fail_count}次, progress={ctx.torrent.progress})"
                    )
                    if origin is not None:
                        origin.resume_index = None  # 失败: 清断点重走完整决策链(重新校验)
                        tq.reschedule(origin, time.time())
                return False
            except Exception as e:
                logger.warning(f"规则[{rule_name}] {hash[:8]} | 校验轮询异常: {e}")
                if origin is not None:
                    origin.resume_index = None
                    tq.reschedule(origin, time.time())
                return False

        task = Task(
            "check",
            "check-checking-result",
            hash=hash,
            interval=CHECK_RESULT_INTERVAL,
            handler=poll,
        )
        if not tq.add_check_task(task):
            return ActionResult.skip("该校验任务已在队列中")
        # 先登记成功再让位(顺序保证: 失败绝不 defer, 杜绝原任务永久让位)
        if origin is not None:
            tq.defer(origin)
        try:
            api.torrents_recheck(torrent_hashes=hash)
        except Exception as e:
            return ActionResult.fail(f"发送 recheck 失败: {e}")
        if origin is not None:
            # 任务队列驱动: 返回 pending, 规则记录断点中断, 由轮询任务 resume/reschedule 恢复
            return ActionResult.pending("full-checking 校验已提交")
        return ActionResult.ok("full-checking 校验已提交")

    def _execute_skip_checking(self, ctx: RuleContext, segment: dict, has_reference: bool):
        """辅种跳检(高风险): 导出 → 删除(保留文件) → 确认消失 → 重加(跳过校验) → 确认出现 → 恢复快照

        四阶段: 前置闸门(无副作用) / 准备(删除前读取) / 执行(删除→恢复) / 收尾。
        风险控制:
        - 部分下载(0<progress<1)禁止跳检: 预分配零块会被当作有效数据上传
        - 跨规则同日去重: 多条规则都配 checking 时, 同一种子当日也只跳检一次(统计只丢一次)
        - 强制前置 filelist 检查(文件全部存在且大小一致), 未通过不执行(execute() 中)
        - 删除后轮询确认消失(qB 删除异步), 重加前未消失则放弃(种子仍在, 无损失)
        - 重加属性直传(0/负值有语义) + contentLayout 推断(布局错位不自愈)
        - 重加成功恢复删除前快照记录(tracker_conf/惰性缓存保留, 否则永久未匹配)
        - 无参考种子跳检: 高风险(仅基础文件存在与大小对比, 内容错误会传垃圾数据), 警告但允许
        - 重加失败时 .torrent 落盘备份并记录元数据(立即落盘), 提示手动恢复
        - 删除种子会清空该种子本地统计, 属固有风险, 需规则显式配置
        """
        torrent = ctx.torrent

        # ---- 阶段 1: 前置闸门 (任一不过 → fail/skip 返回, 无副作用) ----
        gate = self._skip_gates(ctx, torrent)
        if gate is not None:
            return gate

        # ---- 阶段 2: 准备 (导出/校验属性/布局推断, 均须在删除前完成) ----
        try:
            data = ctx.api.torrents_export(torrent_hash=ctx.hash)
        except Exception as e:
            return ActionResult.fail(f"导出 .torrent 失败: {e}")
        if not data:
            return ActionResult.fail("导出 .torrent 为空")

        # 重加所需的 6 属性存在性已由启动期 schema 校验保证(refresh 首次拉取时验证
        # REQUIRED_TORRENT_FIELDS, 含 RE_ADD_FIELDS); 直接引用原始 TorrentDictionary
        # (删除不会改变 Python 对象内容)
        tor = torrent.tor

        # 布局推断依赖 content_path/save_path/文件列表(惰性缓存, filelist 前置检查已填充);
        # 删除后 store 记录已移除, 必须在此之前完成
        content_layout = self._infer_content_layout(torrent, ctx.client)

        # ---- 阶段 3: 执行 (删除 → 确认消失 → 重加 → 确认出现 → 恢复快照) ----
        failed = self._skip_delete(ctx, torrent)
        if failed is not None:
            return failed
        failed = self._skip_readd(ctx, torrent, data, tor, content_layout)
        if failed is not None:
            return failed

        # ---- 阶段 4: 收尾 ----
        # 无参考高风险警告(用删除前捕获的 torrent: 真实流程中删除后 ctx.torrent 为 None)
        if not has_reference:
            logger.warning(f"规则[{ctx.rule_name}] {torrent.log_repr} | 无参考跳检(高风险): "
                           f"仅文件存在与大小对比, 内容错误会传垃圾数据")
        if segment["auto_start"]:
            try:
                ctx.api.torrents_start(torrent_hashes=ctx.hash)
            except Exception as e:
                return ActionResult.fail(f"自动开始失败: {e}")
            return ActionResult.ok("skip-checking 跳检完成并自动开始")
        return ActionResult.ok("skip-checking 跳检完成")

    def _skip_gates(self, ctx: RuleContext, torrent: TorrentRecord) -> Optional[ActionResult]:
        """跳检前置闸门: 部分下载禁止 + 跨规则同日去重。返回 None = 全部通过。

        - 部分下载(0<progress<1)禁止: 预分配使文件尺寸=完整尺寸, filelist 尺寸检查无法
          发现未下载的零块, is_skip_checking 会把全部块标记有效 -> 零块被上传(垃圾数据)。
          仅 progress==0(全新辅种, 数据完整)可跳检; full-checking 对部分下载安全, 不设限。
        - 跨规则同日去重: 多条规则都配 checking 时, 同一种子当日只跳检一次(跳检必然清空
          本地统计, 重复跳检只会再丢一次而毫无收益); 顺带清理非当日记录(防 state 无界增长)。
        """
        progress = torrent.progress
        if 0.0 < progress < 1.0:
            return ActionResult.fail(f"部分下载的种子禁止跳检(progress={progress}), 请改用 full-checking")

        today = date.today().isoformat()
        skip_day = ctx.manager.state.setdefault("skip_check_day", {})
        if skip_day.get(ctx.hash) == today:
            return ActionResult.skip("今日已跳检过该种子(跨规则去重)")
        for h in [h for h, d in skip_day.items() if d != today]:
            del skip_day[h]
        return None

    def _skip_delete(self, ctx: RuleContext, torrent: TorrentRecord) -> Optional[ActionResult]:
        """跳检步骤: 删除种子(保留文件)并轮询确认已从客户端消失(qB 删除为异步)。

        返回 None = 已确认消失; ActionResult = 失败(种子未删除或消失未确认, 无损失,
        放弃跳检避免重加撞"种子已存在")。
        """
        try:
            logger.info(f"规则[{ctx.rule_name}] {torrent.log_repr} | 跳检删除种子(保留文件)")
            ctx.api.torrents_delete(torrent_hashes=ctx.hash, delete_files=False)
        except Exception as e:
            return ActionResult.fail(f"删除种子失败(未删除, 无损失): {e}")
        gone = _poll_until(lambda: not ctx.api.torrents_info(torrent_hashes=ctx.hash), attempts=10, interval=0.5)
        if not gone:
            return ActionResult.fail("删除后种子仍在客户端, 放弃跳检(重加会撞已存在的种子)")
        return None

    def _skip_readd(
        self, ctx: RuleContext, torrent: TorrentRecord, data: bytes, tor: TorrentDictionary,
        content_layout: Optional[str]
    ) -> Optional[ActionResult]:
        """跳检步骤: 以跳过校验方式重加(先暂停), 轮询确认出现, 恢复删除前快照记录。

        属性直传不用 `or None` —— ratio/seeding limit 的 0/负值是有语义的(不限速/跟随
        全局), 吞掉会使重加后行为漂移到 qB 新种缺省。重加成功后 store.restore_torrent
        恢复删除前记录(保留 tracker_conf/惰性缓存): remove_torrent 保留 _known_hashes,
        重加的同 hash 种子不进下轮 added 列表, 不恢复则永久未匹配(生产 BUG 2026-09-06)。

        返回 None = 成功; ActionResult = 失败(种子已从客户端移除, 已备份提示手动恢复)。
        """
        try:
            ctx.api.torrents_add(
                torrent_files=[data],
                save_path=torrent.save_path,
                category=torrent.category or None,
                tags=torrent.tags or None,
                upload_limit=torrent.up_limit,
                download_limit=torrent.dl_limit,
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
            backup = self._backup_torrent(ctx.manager, torrent, data)
            return ActionResult.fail(f"重加种子失败: {e}; 种子已从客户端移除(文件保留), "
                                     f".torrent 已备份: {backup}, 请手动重加")
        appeared = _poll_until(lambda: ctx.api.torrents_info(torrent_hashes=ctx.hash), attempts=3, interval=0.3)
        if not appeared:
            return ActionResult.fail("重加后未确认到种子, 请检查客户端")
        ctx.manager.store.restore_torrent(torrent)
        # 跳检完成: 记录跨规则同日去重(此后同种子当日任何规则的 checking 都不再跳检)
        ctx.manager.state.setdefault("skip_check_day", {})[ctx.hash] = date.today().isoformat()
        return None

    def _infer_content_layout(self, torrent, client) -> Optional[str]:
        """推断原内容布局(qB 种子信息无直接字段): 重加后数据路径必须与现存文件一致,
        跳检状态下布局错位不会自愈(直接 missingFiles/空传)。无法推断返回 None(用 qB 默认)。

        须在删除种子前调用(传入删除前捕获的记录): 删除后 store 记录已移除, 且文件列表
        惰性缓存挂在记录上(空缓存时会向已删除的种子发请求)。

        - 文件路径均以 种子名/ 开头(.torrent 自带根目录): content==save -> NoSubfolder(原布局剥根),
          content==save/种子名 -> Original
        - 无根目录(含单文件): content==save -> Original; content==save/种子名 -> Original
        """
        save = utils.path_normalize(torrent.save_path)
        content = utils.path_normalize(torrent.content_path or "")
        if not content:
            return None
        name = utils.path_normalize(torrent.name)
        files = torrent.files(client)  # store 惰性缓存(filelist 前置检查已填充)
        has_root = bool(files) and all(utils.path_normalize(f.name).startswith(f"{name}/") for f in files)
        if content == save:
            return "NoSubfolder" if has_root else "Original"
        if content == f"{save}/{name}":
            return "Original"
        return None

    def _backup_torrent(self, manager, torrent, data: bytes) -> str:
        """重加失败时把 .torrent 落盘备份并记录元数据(便于手动恢复), 返回备份路径

        用删除前捕获的 torrent 记录(删除后 store 记录已移除, ctx.torrent 为 None)。
        元数据立即落盘(非常规路径, 不适用"仅退出时落盘"的写放大规避): 备份后程序一旦
        崩溃, 没有 state 里的元数据指引, 用户不知道 .torrent 备份的存在与原始保存路径。
        """
        backup_dir = os.path.join(os.path.dirname(manager.state_file) or ".", "skip-check-backup")
        os.makedirs(backup_dir, exist_ok=True)
        path = os.path.join(backup_dir, f"{torrent.hash}.torrent")
        with open(path, "wb") as f:
            f.write(data)
        backup_meta = manager.state.setdefault("skip_check_backup", {})
        backup_meta[torrent.hash] = {
            "path": path,
            "save_path": torrent.save_path,
            "category": torrent.category,
            "tags": torrent.tags,
            "ts": time.time(),
        }
        manager.save_state()
        return path


@register_action
class MoveToAction(BaseAction):
    """移动种子到新路径"""
    name = "move_to"

    def __init__(self, spec, ignore_error=False):
        super().__init__(spec, ignore_error)
        self.path = str(spec.get("path", "")) if isinstance(spec, dict) else str(spec)

    def execute(self, ctx: RuleContext):
        if not self.path:
            return ActionResult.fail("move_to.path 为空")
        if not ctx.dry_run:
            ctx.api.torrents_set_location(torrent_hashes=ctx.hash, location=self.path)
        return ActionResult.ok(f"移动到 {self.path}")


@register_action
class ReannounceAction(BaseAction):
    """强制汇报 tracker(高风险): 运行时最小间隔保护, 独立于规则 execute_once/cooldown 兜底

    高频 announce 会被 tracker 判定异常封号, 因此动作自身强制限频, 不依赖用户配置去重。
    """
    name = "reannounce"
    MIN_INTERVAL = 600.0  # 同一种子两次 reannounce 的最小间隔(秒)

    def execute(self, ctx: RuleContext):
        if ctx.torrent.state_enum.is_stopped:
            return ActionResult.skip("种子已暂停, 无需汇报")
        history = ctx.manager.state.setdefault("reannounce_ts", {})
        now = time.time()
        if now - history.get(ctx.hash, 0) < self.MIN_INTERVAL:
            return ActionResult.skip(f"距上次 reannounce 不足 {int(self.MIN_INTERVAL)}s")
        if not ctx.dry_run:
            ctx.api.torrents_reannounce(torrent_hashes=ctx.hash)
            history[ctx.hash] = now
        return ActionResult.ok("强制汇报tracker")


class _SpeedLimitAction(BaseAction):
    """限速动作基类: 设置单种上传/下载限速"""
    api_method = ""  # torrents_set_upload_limit / torrents_set_download_limit
    direction = ""  # 上传 / 下载

    def __init__(self, spec, ignore_error=False):
        super().__init__(spec, ignore_error)
        self.value = utils.parse_speed(str(spec))

    def execute(self, ctx: RuleContext):
        if not ctx.dry_run:
            if "upload" in self.api_method:
                current_limit = ctx.torrent.up_limit
            else:
                current_limit = ctx.torrent.dl_limit

            # 不覆盖单数值
            if utils.is_manual_speed_limit(current_limit):
                return ActionResult.skip("用户已设置")
            if current_limit == self.value:
                return ActionResult.skip("已设置")
            getattr(ctx.api, self.api_method)(torrent_hashes=ctx.hash, limit=self.value)
        return ActionResult.ok(f"设置{self.direction}限速: {utils.fmt_speed(self.value)}")


@register_action
class UploadSpeedLimitAction(_SpeedLimitAction):
    """单种上传限速, 如 '1000KiB/s'"""
    name = "upload_speed_limit"
    api_method = "torrents_set_upload_limit"
    direction = "上传"


@register_action
class DownloadSpeedLimitAction(_SpeedLimitAction):
    """单种下载限速, 如 '1000KiB/s'"""
    name = "download_speed_limit"
    api_method = "torrents_set_download_limit"
    direction = "下载"
