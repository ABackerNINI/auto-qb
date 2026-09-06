"""基础种子操作动作: add_tags, remove_tags, add_category, remove_category, start, stop"""
import logging
from typing import List

from ... import utils
from ..base import ActionResult, BaseAction, RuleContext
from ..registry import register_action

logger = logging.getLogger(__name__)


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
