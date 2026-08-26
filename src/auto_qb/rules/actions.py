"""内置动作插件: add_tags, remove_tags, add_category, remove_category, start, stop,
check, basic_check, custom_basic_check_program_path, always_check_first_one,
move_to, reannounce, upload_speed_limit, download_speed_limit"""
import logging
import re

from . import utils
from .base import ActionResult, BaseAction
from .registry import register_action

logger = logging.getLogger("auto-qb.rules")

# 用于 start/stop 动作的幂等判断
_STARTED_STATES = {
    "uploading",
    "stalledUP",
    "downloading",
    "forcedDL",
    "forcedUP",
    "metaDL",
    "stalledDL",
    "queuedDL",
    "queuedUP",
    "checkingDL",
    "checkingUP",
    "checkingResumeData",
}
_STOPPED_STATES = {"pausedDL", "pausedUP", "stoppedDL", "stoppedUP"}


@register_action
class AddTagsAction(BaseAction):
    """添加标签, 支持 ${hr-time} 变量"""
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
            ctx.client.torrents_add_tags(tags=new, torrent_hashes=ctx.torrent.hash)
        return ActionResult.ok(f"添加标签 {new}")


@register_action
class RemoveTagsAction(BaseAction):
    """删除标签, 支持 regex: 和 ${hr-time} 变量"""
    name = "remove_tags"

    def __init__(self, spec, ignore_error=False):
        super().__init__(spec, ignore_error)
        self.patterns = list(spec) if isinstance(spec, list) else [spec]

    def execute(self, ctx):
        current = set(t.strip() for t in (ctx.torrent.tags or "").split(",") if t.strip())
        removed = set()
        for pat in self.patterns:
            pat = ctx.replace_vars(pat)
            if not pat:
                continue
            if pat.startswith("regex:"):
                try:
                    rx = re.compile(pat[6:])
                except re.error:
                    continue
                for t in current:
                    if rx.search(t):
                        removed.add(t)
            elif pat in current:
                removed.add(pat)
        if not removed:
            return ActionResult.skip("无匹配标签")
        if not ctx.dry_run:
            ctx.client.torrents_remove_tags(tags=list(removed), torrent_hashes=ctx.torrent.hash)
        return ActionResult.ok(f"删除标签 {removed}")


@register_action
class AddCategoryAction(BaseAction):
    """添加分类, 支持 ${hr-time} 变量和 overwrite 覆盖"""
    name = "add_category"

    def __init__(self, spec, ignore_error=False):
        super().__init__(spec, ignore_error)
        self.format = str(spec.get("format", ""))
        self.overwrite = utils.parse_bool(spec.get("overwrite", False))

    def execute(self, ctx):
        category = ctx.replace_vars(self.format)
        old = (ctx.torrent.category or "").strip()
        if old == category:
            return ActionResult.skip("分类已设置")
        if old and not self.overwrite:
            return ActionResult.skip(f"已有分类 {old}, 不覆盖")
        if not ctx.dry_run:
            try:
                if category not in (ctx.client.torrents_categories() or {}):
                    ctx.client.torrents_create_category(name=category)
            except Exception:
                pass
            ctx.client.torrents_set_category(category=category, torrent_hashes=ctx.torrent.hash)
        return ActionResult.ok(f"设置分类 {category}")


@register_action
class RemoveCategoryAction(BaseAction):
    """清空分类"""
    name = "remove_category"

    def execute(self, ctx):
        if not (ctx.torrent.category or "").strip():
            return ActionResult.skip("分类为空")
        if not ctx.dry_run:
            ctx.client.torrents_set_category(category="", torrent_hashes=ctx.torrent.hash)
        return ActionResult.ok("清空分类")


@register_action
class StartAction(BaseAction):
    """开始种子"""
    name = "start"

    def execute(self, ctx):
        if ctx.torrent.state in _STARTED_STATES:
            return ActionResult.skip("已开始")
        if not ctx.dry_run:
            ctx.client.torrents_start(torrent_hashes=ctx.torrent.hash)
        return ActionResult.ok("开始")


@register_action
class StopAction(BaseAction):
    """暂停种子"""
    name = "stop"

    def execute(self, ctx):
        if ctx.torrent.state in _STOPPED_STATES:
            return ActionResult.skip("已停止")
        if not ctx.dry_run:
            ctx.client.torrents_stop(torrent_hashes=ctx.torrent.hash)
        return ActionResult.ok("暂停")


@register_action
class CheckAction(BaseAction):
    """校验: full-checking(异步: 发送请求由工作线程执行, 主循环轮询校验完成, 可选完成后自动开始)
    / skip-checking(高风险, 暂未实现)"""
    name = "check"

    def __init__(self, spec, ignore_error=False):
        super().__init__(spec, ignore_error)
        if isinstance(spec, dict):
            self.mode = str(spec.get("mode", "full-checking"))
            self.auto_start = utils.parse_bool(spec.get("auto_start", False))
            self.poll_timeout = utils.parse_time(str(spec.get("poll_timeout", "0S")))
        else:
            self.mode = str(spec)
            self.auto_start = False
            self.poll_timeout = 0

    def execute(self, ctx):
        if self.mode == "full-checking":
            if ctx.dry_run:
                return ActionResult.ok("full-checking 校验(异步)")
            tq = getattr(ctx.manager, "task_queue", None)
            if tq is None:
                # 无任务队列(旧用法/同步环境): 直接发送请求
                if not ctx.dry_run:
                    ctx.client.torrents_recheck(torrent_hashes=ctx.torrent.hash)
                return ActionResult.ok("full-checking 校验")
            # 双队列: 发送请求交给异步工作线程, 主循环轮询校验完成
            rule_name = ctx.rule_name
            torrent_hash = ctx.torrent.hash
            client = ctx.client
            manager = ctx.manager
            dry_run = ctx.dry_run
            auto_start = self.auto_start

            def send():
                client.torrents_recheck(torrent_hashes=torrent_hash)

            def done(task):
                # 主循环线程执行: state_file 仅主循环写, 线程安全
                if task.send_error is not None:
                    logger.warning(f"规则: {rule_name} | 校验请求发送失败: {torrent_hash}: {task.send_error}")
                    return
                logger.info(f"规则: {rule_name} | 校验完成: {torrent_hash}")
                if auto_start and not dry_run:
                    client.torrents_start(torrent_hashes=torrent_hash)
                    logger.info(f"规则: {rule_name} | 校验完成自动开始: {torrent_hash}")
                manager.record_execution(rule_name, torrent_hash)
                manager.save_state()

            if tq.submit_check(torrent_hash, send, done, timeout=self.poll_timeout):
                return ActionResult.ok("full-checking 校验请求已提交, 等待完成")
            return ActionResult.skip("该校验任务已在队列中")
        if self.mode == "skip-checking":
            return ActionResult.fail("skip-checking 动作属于高风险(导出->删除->重加会清空本地统计且存在中断窗口), "
                                     "框架初版暂未实现, 请使用 full-checking")
        return ActionResult.fail(f"未知校验模式: {self.mode}")


@register_action
class BasicCheckAction(BaseAction):
    """基础检查: filelist(文件存在+大小) / piecehashes(暂未实现)"""
    name = "basic_check"

    def __init__(self, spec, ignore_error=False):
        super().__init__(spec, ignore_error)
        self.mode = str(spec)

    def execute(self, ctx):
        if self.mode == "filelist":
            err = utils.check_filelist(ctx.client, ctx.torrent)
            if err is None:
                return ActionResult.ok("文件列表检查通过")
            return ActionResult.fail(f"文件列表检查失败: {err}")
        if self.mode == "piecehashes":
            return ActionResult.fail("piecehashes 基础检查尚未实现(需导出.torrent对比piece哈希), 请使用 filelist")
        return ActionResult.fail(f"未知基础检查模式: {self.mode}")


@register_action
class CustomBasicCheckProgramAction(BaseAction):
    """运行自定义 basic_check 外部程序, 参数: <种子hash> <保存路径>"""
    name = "custom_basic_check_program_path"

    def __init__(self, spec, ignore_error=False):
        super().__init__(spec, ignore_error)
        self.program = str(spec)

    def execute(self, ctx):
        if ctx.dry_run:
            return ActionResult.ok(f"dry-run, 不执行外部程序 {self.program}")
        import subprocess
        try:
            r = subprocess.run(
                [self.program, ctx.torrent.hash, ctx.torrent.save_path],
                capture_output=True,
                text=True,
                timeout=600,
            )
            if r.returncode == 0:
                return ActionResult.ok(f"外部检查通过: {r.stdout.strip()[:200]}")
            return ActionResult.fail(f"外部检查失败 rc={r.returncode}: {r.stderr.strip()[:200]}")
        except Exception as e:
            return ActionResult.fail(f"外部检查异常: {e}")


@register_action
class AlwaysCheckFirstOneAction(BaseAction):
    """对同一保存路径"最后校验时间最久"的种子强制校验(简化: 记录每路径最近校验的hash, 不重复)"""
    name = "always_check_first_one"

    def execute(self, ctx):
        path = ctx.torrent.save_path
        checked = ctx.manager.state.setdefault("checked_paths", {})
        if checked.get(path) == ctx.torrent.hash:
            return ActionResult.skip(f"路径 {path} 已校验过种子 {ctx.torrent.hash}")
        checked[path] = ctx.torrent.hash
        if not ctx.dry_run:
            ctx.client.torrents_recheck(torrent_hashes=ctx.torrent.hash)
        return ActionResult.ok(f"路径 {path} 校验种子 {ctx.torrent.hash}")


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
            ctx.client.torrents_set_location(torrent_hashes=ctx.torrent.hash, location=self.path)
        return ActionResult.ok(f"移动到 {self.path}")


@register_action
class ReannounceAction(BaseAction):
    """强制汇报 tracker(注意: 应配合 execute_once/daily 使用, 避免高频announce)"""
    name = "reannounce"

    def execute(self, ctx):
        if not ctx.dry_run:
            ctx.client.torrents_reannounce(torrent_hashes=ctx.torrent.hash)
        return ActionResult.ok("强制汇报tracker")


class _SpeedLimitAction(BaseAction):
    """限速动作基类: 设置单种上传/下载限速"""
    api_method = ""  # torrents_set_upload_limit / torrents_set_download_limit
    direction = ""  # 上传 / 下载

    def __init__(self, spec, ignore_error=False):
        super().__init__(spec, ignore_error)
        self.value = utils.parse_speed(str(spec))

    def _fmt_speed(self) -> str:
        """将字节/秒格式化为可读字符串"""
        for unit, div in (
            ("PiB/s", 1024**5), ("TiB/s", 1024**4), ("GiB/s", 1024**3), ("MiB/s", 1024**2), ("KiB/s", 1024)
        ):
            if self.value >= div:
                return f"{self.value / div:.2f} {unit} ({self.value} B/s)"
        return f"{self.value} B/s"

    def execute(self, ctx):
        if not ctx.dry_run:
            if "upload" in self.api_method:
                getattr(ctx.client, self.api_method)(torrent_hashes=ctx.torrent.hash, upload_limit=self.value)
            else:
                getattr(ctx.client, self.api_method)(torrent_hashes=ctx.torrent.hash, download_limit=self.value)
        return ActionResult.ok(f"设置{self.direction}限速: {self._fmt_speed()}")


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
