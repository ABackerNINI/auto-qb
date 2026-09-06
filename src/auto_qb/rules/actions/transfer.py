"""传输相关动作: move_to, reannounce, upload_speed_limit, download_speed_limit"""
import time

from ... import utils
from ..base import ActionResult, BaseAction, RuleContext
from ..registry import register_action


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
