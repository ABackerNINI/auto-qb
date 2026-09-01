"""内置动作插件: add_tags, remove_tags, add_category, remove_category, start, stop,
checking(基础检查确定参考种子 + 有/无参考分段校验), move_to, reannounce,
upload_speed_limit, download_speed_limit"""
import logging
import os
import time
from datetime import date
from typing import List

from .. import utils
from .base import ActionResult, BaseAction
from .registry import register_action

logger = logging.getLogger(__name__)


@register_action
class AddTagsAction(BaseAction):
    """添加标签, 支持 ${required_seeding_time} 变量"""
    name = "add_tags"

    def __init__(self, spec, ignore_error=False):
        super().__init__(spec, ignore_error)
        self.tags = list(spec) if isinstance(spec, list) else [spec]

    def execute(self, ctx):
        tags = [ctx.replace_vars(t) for t in self.tags if ctx.replace_vars(t)]
        current = set(t.strip() for t in (ctx.torrent.tags or "").split(",") if t.strip())
        new = [t for t in tags if t and t not in current]
        if not new:
            return ActionResult.skip("标签已存在")
        if not ctx.dry_run:
            ctx.api.torrents_add_tags(tags=new, torrent_hashes=ctx.torrent.hash)
        return ActionResult.ok(f"添加标签 {new}")


@register_action
class RemoveTagsAction(BaseAction):
    """删除标签, 支持 regex: 和 ${required_seeding_time} 变量"""
    name = "remove_tags"

    def __init__(self, spec, ignore_error=False):
        super().__init__(spec, ignore_error)
        self.patterns = list(spec) if isinstance(spec, list) else [spec]

    def execute(self, ctx):
        current_tags = set(t.strip() for t in (ctx.torrent.tags or "").split(",") if t.strip())
        expanded_patterns = self._expand_patterns(ctx)
        to_remove = [t for t in current_tags if utils.match_tag_patterns(t, expanded_patterns)]

        if not to_remove:
            return ActionResult.skip("无匹配标签")
        if not ctx.dry_run:
            ctx.api.torrents_remove_tags(tags=list(to_remove), torrent_hashes=ctx.torrent.hash)
        return ActionResult.ok(f"删除标签 {to_remove}")

    def _expand_patterns(self, ctx) -> List[str]:
        return [ctx.replace_vars(pat) for pat in self.patterns]


@register_action
class AddCategoryAction(BaseAction):
    """添加分类, 支持 ${required_seeding_time} 变量和 overwrite 覆盖"""
    name = "add_category"

    def __init__(self, spec, ignore_error=False):
        super().__init__(spec, ignore_error)
        self.format = str(spec.get("format", ""))
        self.overwrite = utils.parse_bool(spec.get("overwrite", False))

    def execute(self, ctx):
        category = ctx.replace_vars(self.format)
        old_category = ctx.torrent.category or ""
        if old_category == category:
            return ActionResult.skip("分类已设置")

        auto_categories = ctx.manager.state.setdefault("auto_categories", {})

        # 定义一个内部函数可以利用if短路
        def can_update_previous():
            previous_auto_category = auto_categories.get(ctx.torrent.hash)
            return not self.overwrite and old_category == previous_auto_category

        if old_category and not self.overwrite and not can_update_previous():
            return ActionResult.skip(f"已有分类 {old_category}, 不覆盖")
        if not ctx.dry_run:
            try:
                if category not in ctx.manager.store.all_categories():  # 走 store 惰性缓存
                    ctx.api.torrents_create_category(name=category)
            except Exception:
                pass
            ctx.api.torrents_set_category(category=category, torrent_hashes=ctx.torrent.hash)
            if not self.overwrite:
                auto_categories[ctx.torrent.hash] = category
        return ActionResult.ok(f"设置分类 {category}")


@register_action
class RemoveCategoryAction(BaseAction):
    """清空分类"""
    name = "remove_category"

    def execute(self, ctx):
        if not (ctx.torrent.category or "").strip():
            return ActionResult.skip("分类为空")
        if not ctx.dry_run:
            ctx.api.torrents_set_category(category="", torrent_hashes=ctx.torrent.hash)
        return ActionResult.ok("清空分类")


@register_action
class StartAction(BaseAction):
    """开始种子"""
    name = "start"

    def execute(self, ctx):
        if not ctx.torrent_record.is_paused:
            return ActionResult.skip("已开始")
        if not ctx.dry_run:
            ctx.api.torrents_start(torrent_hashes=ctx.torrent.hash)
        return ActionResult.ok("开始")


@register_action
class StopAction(BaseAction):
    """暂停种子"""
    name = "stop"

    def execute(self, ctx):
        if ctx.torrent_record.is_paused:
            return ActionResult.skip("已停止")
        if not ctx.dry_run:
            ctx.api.torrents_stop(torrent_hashes=ctx.torrent.hash)
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
         full-checking: 异步提交 recheck(慢速队列), 完成回调 auto_start + 晋升 verified_references(仅内存)
    """
    name = "checking"
    _VALID_BASIC = ("filelist", "piecehashes", "custom")
    _VALID_MODES = ("skip-checking", "full-checking")

    def __init__(self, spec, ignore_error=False):
        super().__init__(spec, ignore_error)
        if not isinstance(spec, dict):
            raise ValueError("checking 动作只接受 dict 配置, 旧字符串形式已移除, 请参考示例改写")
        self._validate(spec)
        self.basic_check = str(spec["basic_check"])
        self.custom_program = str(spec.get("custom_basic_check_program_path") or "")
        self.with_reference = self._parse_section(spec, "with_reference")
        self.without_reference = self._parse_section(spec, "without_reference")

    def _validate(self, spec: dict):
        known = {"basic_check", "custom_basic_check_program_path", "with_reference", "without_reference"}
        unknown = set(spec) - known
        if unknown:
            raise ValueError(
                f"checking 动作未知配置键: {sorted(unknown)} "
                f"(always_check_first_one/poll_timeout/顶层 mode 已移除, 校验模式请在 with_reference/without_reference 段内配置)"
            )
        if "basic_check" not in spec:
            raise ValueError("checking 动作必须配置 basic_check")
        if spec["basic_check"] not in self._VALID_BASIC:
            raise ValueError(f"checking 动作 basic_check 取值非法: {spec['basic_check']}, 可选: {list(self._VALID_BASIC)}")
        if spec["basic_check"] == "custom" and not str(spec.get("custom_basic_check_program_path") or "").strip():
            raise ValueError("checking 动作 basic_check=custom 时必须配置 custom_basic_check_program_path")
        for seg in ("with_reference", "without_reference"):
            if seg not in spec:
                raise ValueError(f"checking 动作必须配置 {seg} 段")
            if not isinstance(spec[seg], dict):
                raise ValueError(f"checking 动作 {seg} 段必须是 dict")
            seg_mode = str(spec[seg].get("mode", ""))
            if seg_mode not in self._VALID_MODES:
                raise ValueError(f"checking 动作 {seg}.mode 取值非法: {seg_mode}, 可选: {list(self._VALID_MODES)}")

    @staticmethod
    def _parse_section(spec: dict, name: str) -> dict:
        seg = spec[name]
        return {
            "mode": str(seg.get("mode")),
            "auto_start": utils.parse_bool(seg.get("auto_start", False)),
        }

    def execute(self, ctx):
        if ctx.dry_run:
            return ActionResult.ok("checking 校验(决策链: 状态判定+组内下载判定+参考确定+分段执行) [dry-run]")
        manager = ctx.manager
        torrent_hash = ctx.torrent.hash

        # 决策链 0: 只校验"暂停中未完成"的种子(跨种添加后的典型状态), 其余状态一律跳过:
        # - 已完成(progress>=1, 无论状态): 已通过哈希校验, 重复 recheck/跳检无意义
        # - 活跃中(downloading/uploading 等非暂停): 正在运行, 无需校验
        # 此闸门覆盖 full-checking/skip-checking 及有/无任务队列全部路径, 修复完成种子被反复校验的问题
        if not (ctx.torrent_record.is_paused and (ctx.torrent.progress or 0.0) < 1.0):
            return ActionResult.skip("种子非暂停中未完成状态, 无需校验")

        # 决策链 1: 组内有活跃下载种子 -> 整组未完成, 不进行任何校验(包括跳检)
        members = manager._group_members(torrent_hash)
        if manager._group_has_downloading(members):
            return ActionResult.skip("组内有种子正在下载, 整组未完成, 不进行任何校验")

        # 决策链 2: 确定参考种子(basic_check 模式 + 内存 verified_references 并集)
        reference = self._find_reference(ctx, members)

        # 决策链 3: 有参考 -> with_reference 段; 无参考 -> without_reference 段
        segment = self.with_reference if reference else self.without_reference
        if segment["mode"] == "full-checking":
            return self._execute_full_checking(ctx, segment)
        return self._execute_skip_checking(ctx, segment, bool(reference))

    def _find_reference(self, ctx, members: list) -> list:
        """按 basic_check 模式从组内已完成+上传中成员筛选参考种子, 并集内存 verified_references(排除自身)"""
        candidates = [c for c in ctx.manager._group_reference_candidates(members) if c.hash != ctx.torrent.hash]
        refs = []
        if self.basic_check == "filelist":
            refs = list(candidates)  # 分组已保证文件列表相同, 无需重复对比
        elif self.basic_check == "piecehashes":
            # 严格模式: 候选须与目标种子 piece hash 列表完全相同(torrents_piece_hashes API, 无需导出 .torrent)
            try:
                target = ctx.api.torrents_piece_hashes(ctx.torrent.hash)
            except Exception as e:
                logger.warning(f"获取 piece hashes 失败({ctx.torrent.hash}), 视为无参考: {e}")
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
        own = ctx.torrent.hash
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

    def _run_custom_check(self, ctx, candidate) -> bool:
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
            logger.info(f"自定义 basic_check 判定非参考({candidate.hash}) rc={r.returncode}: {r.stderr.strip()[:200]}")
            return False
        except Exception as e:
            logger.warning(f"自定义 basic_check 程序执行异常({candidate.hash}): {e}")
            return False

    def _execute_full_checking(self, ctx, segment: dict):
        """full-checking: 异步提交 recheck(慢速队列), 完成回调 auto_start + 晋升 verified_references(仅内存)"""
        tq = getattr(ctx.manager, "task_queue", None)
        if tq is None:
            # 无任务队列(旧用法/同步环境): 直接发送请求
            ctx.api.torrents_recheck(torrent_hashes=ctx.torrent.hash)
            return ActionResult.ok("full-checking 校验")
        rule_name = ctx.rule_name
        torrent_hash = ctx.torrent.hash
        api = ctx.api
        manager = ctx.manager
        auto_start = segment["auto_start"]

        def send():
            api.torrents_recheck(torrent_hashes=torrent_hash)

        def done(task):
            # 主循环线程执行: state_file 仅主循环写, 线程安全
            if task.send_error is not None:
                logger.warning(f"规则: {rule_name} | 校验请求发送失败: {torrent_hash}: {task.send_error}")
                return
            logger.info(f"规则: {rule_name} | 校验完成: {torrent_hash}")
            # 晋升参考(仅内存, 不写 state_file): 校验通过说明文件与元数据一致, 可作同组参考
            manager.store.verified_references.add(torrent_hash)
            if auto_start:
                api.torrents_start(torrent_hashes=torrent_hash)
                logger.info(f"规则: {rule_name} | 校验完成自动开始: {torrent_hash}")
            manager.record_execution(rule_name, torrent_hash)

        if tq.submit_check(torrent_hash, send, done, timeout=0):
            return ActionResult.ok("full-checking 校验请求已提交, 等待完成")
        return ActionResult.skip("该校验任务已在队列中")

    def _execute_skip_checking(self, ctx, segment: dict, has_reference: bool):
        """辅种跳检(高风险): 导出 .torrent -> 删除种子(保留文件) -> 重加跳过校验 -> 可选自动开始

        风险控制:
        - 强制前置 filelist 检查(文件全部存在且大小一致), 未通过不执行
        - 同日去重: 同规则对同种子每天最多跳检一次(防误配置反复删/加, 覆盖 execute_once 兜底)
        - 无参考种子跳检: 高风险(仅基础文件存在与大小对比, 内容错误会传垃圾数据), 警告但允许
        - 重加失败时 .torrent 落盘备份并记录元数据, 提示手动恢复
        - 删除种子会清空该种子本地统计, 属固有风险, 需规则显式配置
        """
        # 0. 同日去重(安全兜底, 与 execute_once 无关)
        record = ctx.manager.get_exec_record(ctx.rule_name, ctx.torrent.hash)
        if record and record.get("date") == date.today().isoformat():
            return ActionResult.skip("今日已跳检, 跳过")

        # 1. 强制前置检查: 文件全部存在且大小一致
        err = utils.check_filelist(ctx.api, ctx.torrent)
        if err is not None:
            return ActionResult.fail(f"跳检前置检查未通过: {err}")

        # 2. 导出 .torrent
        try:
            data = ctx.api.torrents_export(torrent_hashes=ctx.torrent.hash)
        except Exception as e:
            return ActionResult.fail(f"导出 .torrent 失败: {e}")
        if not data:
            return ActionResult.fail("导出 .torrent 为空")

        # 3. 删除种子(保留文件)
        try:
            ctx.api.torrents_delete(torrent_hashes=ctx.torrent.hash, delete_files=False)
        except Exception as e:
            return ActionResult.fail(f"删除种子失败(未删除, 无损失): {e}")

        # 4. 重加(跳过校验, 先暂停)
        try:
            ctx.api.torrents_add(
                torrent_files=[data],
                save_path=ctx.torrent.save_path,
                category=ctx.torrent.category or None,
                tags=ctx.torrent.tags or None,
                is_skip_checking=True,
                paused=True,
            )
        except Exception as e:
            backup = self._backup_torrent(ctx, data)
            return ActionResult.fail(f"重加种子失败: {e}; 种子已从客户端移除(文件保留), "
                                     f".torrent 已备份: {backup}, 请手动重加")

        # 5. 轮询确认新种子出现(跳检不进入 checking, 重加即出现)
        appeared = False
        for _ in range(3):
            try:
                if ctx.api.torrents_info(torrent_hashes=ctx.torrent.hash):
                    appeared = True
                    break
            except Exception:
                pass
            time.sleep(0.3)
        if not appeared:
            return ActionResult.fail("重加后未确认到种子, 请检查客户端")

        # 6. 无参考高风险警告 + 自动开始
        if not has_reference:
            logger.warning(f"规则: {ctx.rule_name} | 无参考种子跳检(高风险): 仅做文件存在与大小对比, "
                           f"内容错误时会传垃圾数据: {ctx.torrent.hash}")
        if segment["auto_start"]:
            try:
                ctx.api.torrents_start(torrent_hashes=ctx.torrent.hash)
            except Exception as e:
                return ActionResult.fail(f"自动开始失败: {e}")
            return ActionResult.ok("skip-checking 跳检完成并自动开始")
        return ActionResult.ok("skip-checking 跳检完成")

    def _backup_torrent(self, ctx, data: bytes) -> str:
        """重加失败时把 .torrent 落盘备份并记录元数据(便于手动恢复), 返回备份路径"""
        backup_dir = os.path.join(os.path.dirname(ctx.manager.state_file) or ".", "skip-check-backup")
        os.makedirs(backup_dir, exist_ok=True)
        path = os.path.join(backup_dir, f"{ctx.torrent.hash}.torrent")
        with open(path, "wb") as f:
            f.write(data)
        backup_meta = ctx.manager.state.setdefault("skip_check_backup", {})
        backup_meta[ctx.torrent.hash] = {
            "path": path,
            "save_path": ctx.torrent.save_path,
            "category": ctx.torrent.category,
            "tags": ctx.torrent.tags,
            "ts": time.time(),
        }
        return path


@register_action
class MoveToAction(BaseAction):
    """移动种子到新路径"""
    name = "move_to"

    def __init__(self, spec, ignore_error=False):
        super().__init__(spec, ignore_error)
        self.path = str(spec.get("path", "")) if isinstance(spec, dict) else str(spec)

    def execute(self, ctx):
        if not self.path:
            return ActionResult.fail("move_to.path 为空")
        if not ctx.dry_run:
            ctx.api.torrents_set_location(torrent_hashes=ctx.torrent.hash, location=self.path)
        return ActionResult.ok(f"移动到 {self.path}")


@register_action
class ReannounceAction(BaseAction):
    """强制汇报 tracker(注意: 应配合 execute_once/daily 使用, 避免高频announce)"""
    name = "reannounce"

    def execute(self, ctx):
        # TODO: 添加限制
        if not ctx.dry_run:
            ctx.api.torrents_reannounce(torrent_hashes=ctx.torrent.hash)
        return ActionResult.ok("强制汇报tracker")


class _SpeedLimitAction(BaseAction):
    """限速动作基类: 设置单种上传/下载限速"""
    api_method = ""  # torrents_set_upload_limit / torrents_set_download_limit
    direction = ""  # 上传 / 下载

    def __init__(self, spec, ignore_error=False):
        super().__init__(spec, ignore_error)
        self.value = utils.parse_speed(str(spec))

    def execute(self, ctx):
        if not ctx.dry_run:
            if "upload" in self.api_method:
                current_limit = ctx.torrent_record.up_limit
            else:
                current_limit = ctx.torrent_record.dl_limit

            # 不覆盖单数值
            if (current_limit / 1024) % 2 == 1:
                return ActionResult.skip("用户已设置")
            if current_limit == self.value:
                return ActionResult.skip("已设置")
            getattr(ctx.api, self.api_method)(torrent_hashes=ctx.torrent.hash, limit=self.value)
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
