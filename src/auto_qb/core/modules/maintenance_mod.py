"""MaintenanceModule: 标签 / 分类 / HR 标签 / 集数标签 / 维护任务的模块化封装(plan P3)

TagsMixin 全部 + QbManager 本体的 _handle_maintenance + delete_tags 全局任务 + 集数标签
一起迁入(plan §3.2 maintenance 行)。两个自注册点:
- start:      delete_tags / delete_tags_if_has_no_torrents 全局任务按配置入队;
- queue_rebuilt: L2 热重载整体重建队列后重新入队(新 interval; 已在队列则幂等跳过)。
内核的 _create_global_tasks 不再点名业务任务(plan §5)。

!站点 tags 部分的节奏由 maintenance_tag_mode 决定(计划 26-09-27-1438): interval(默认)
  每 interval 执行; on_change 仅添加路径或外部标签变化时重检 —— HR 部分不受影响, 恒按
  interval 节奏。维护任务本身由 rules 模块建任务时经 ctx.maintenance 句柄绑定
  (plan P5 收口); 逐新增种子的「维护/集数」两步经 torrents_added 相位由本模块执行。
!client 经 ctx.api.client **现取**(不缓存): 重连换客户端时 QbApi.bind 同步更新。
"""
import logging
from typing import List

from .. import episodes
from ...infra import utils
from ...hr.resolve import HrIdentity
from ...hr.service import SEED_EXEMPT_RATIO
from ...torrents import TorrentRecord
from ..module import AppContext, BaseModule
from ..taskqueue import FINISHED, REQUEUE, Task

logger = logging.getLogger(__name__)


def _seed_exempt_baseline(rec: TorrentRecord) -> float:
    """超额跳过线的做种要求基准(秒)(计划 26-09-30-0559 §4)

    已接入站点(hr_check 存在且启用)用站点档案预设 hr_check.required_seeding_time ——
    与取数侧对象集排除线同源, 同一颗种子不出现「取数跳过但打标不跳」的劈叉;
    未接入站点回落本地 hr.required_seeding_time。基准 <= 0 时调用方跳过线不生效
    (与取数侧 required_seeding_time > 0 前提一致)。
    """
    conf = rec.tracker_conf
    site_conf = conf.hr_check
    if site_conf is not None and site_conf.enabled:
        return site_conf.required_seeding_time
    return float(conf.hr.required_seeding_time)


class MaintenanceModule(BaseModule):
    """maintenance 模块: 标签/分类/HR 标签/集数标签 + 全局标签清理任务自注册

    sections 认领六个顶层段: delete_tags* 是全局清理任务的配置源, add_episode_tags/
    maintenance_tag_mode 是种子级维护的消费段, hr/remove_similar_tags 经载入期合并进
    tracker 后由本模块消费(P6 段认领补登, 见 sections() 注)。
    """

    name = "maintenance"

    def __init__(self, ctx: AppContext) -> None:
        self._ctx = ctx

    def sections(self) -> tuple[str, ...]:
        # hr / remove_similar_tags(P6 段认领补登): 全局默认在**载入期**合并进各 tracker
        # (站点优先, 见 config/loaders.load_tracker_hr), 运行期经 tracker_conf 消费 ——
        # 段变无重挂动作, 新匹配种子即生效(存量记录待 L2 重匹配兑现)
        return (
            "delete_tags",
            "delete_tags_if_has_no_torrents",
            "add_episode_tags",
            "maintenance_tag_mode",
            "remove_similar_tags",
            "hr",
        )

    # ---------- 生命周期 ----------

    def start(self, ctx: AppContext, dry_run: bool) -> None:
        # 全局标签清理任务自注册(plan §3.2): dry_run 不影响注册(handler 自带 dry_run 口径,
        # 原 _create_global_tasks 也不判 dry_run); 配置为空 = 无操作
        self._register_global_tasks(ctx)

    # ---------- 相位订阅 ----------

    def subscribe(self, phases) -> None:
        phases.on("queue_rebuilt", self._on_queue_rebuilt)
        phases.on("torrents_added", self._on_torrent_added)

    def _on_queue_rebuilt(self, event) -> None:
        """L2 热重载整体重建队列后重新入队(delete_tags* 是 L2 级配置, 重建即按新值生效)"""
        self._register_global_tasks(self._ctx)

    def _on_torrent_added(self, event) -> None:
        """逐新增种子管线的「维护」与「集数」两步(plan §4.2; P5 收口前经内核委托调用):
        维护 tags 部分强制执行(添加路径: on_change 模式的"添加时收敛一次"), 集数标签
        仅种子添加时触发 —— 两者都属本模块, 单订阅内按原顺序连续执行"""
        torrent = self._ctx.store.get(event.payload["hash"])
        if torrent is None:
            return
        dry_run = event.payload.get("dry_run", False)
        self.handle_maintenance(torrent, dry_run, force_tags=True)
        if self._ctx.config.add_episode_tags.enabled:
            self.add_episode_tags(torrent, dry_run)

    def _register_global_tasks(self, ctx: AppContext) -> None:
        """全局标签清理任务自注册: 已在当前队列的幂等跳过(黄金法则 1, 判据 TaskQueue.has_named);
        队列引用现取 ctx.task_queue(L2 重建后 manager 委托落回 ctx, 不存在旧队列)"""
        queue = ctx.task_queue
        if queue is None:
            return
        tasks = []
        if ctx.config.delete_tags and not queue.has_named("delete_tags"):
            tasks.append(
                Task(
                    "internal",
                    "delete_tags",
                    interval=ctx.config.interval,
                    handler=self.handle_delete_tags,
                )
            )
        if ctx.config.delete_tags_if_has_no_torrents and not queue.has_named("delete_tags_if_has_no_torrents"):
            tasks.append(
                Task(
                    "internal",
                    "delete_tags_if_has_no_torrents",
                    interval=ctx.config.interval,
                    handler=self.handle_delete_tags_if_has_no_torrents,
                )
            )
        if tasks:
            queue.add_tasks(tasks)
            logger.info(f"创建全局任务 {len(tasks)} 个: {[t.log_tag for t in tasks]}")

    # ---------- 种子级维护(原 TagsMixin + qbmanager._handle_maintenance) ----------

    def handle_maintenance_task_interface(self, task: Task, dry_run: bool) -> bool:
        return self.handle_maintenance(task.torrent, dry_run)

    def handle_maintenance(self, torrent: TorrentRecord, dry_run: bool, force_tags: bool = False) -> bool:
        """内置种子级任务: 添加/删除/相似标签 + HR 标签分类

        站点 tags 部分的节奏由 maintenance_tag_mode 决定(计划 26-09-27-1438):
        - interval(默认): 每 interval 执行 —— 与迁移前逐字节等价;
        - on_change: 仅 force_tags(添加路径)或该种子 tags 发生过**外部**变化时重检
          (store.external_tag_changes, 消费一次); HR 部分不受影响 —— 达标状态随时间演化,
          tags 变化捕捉不到, 恒按 interval 节奏。
        """
        if torrent is None:
            return FINISHED

        tracker_conf = torrent.tracker_conf

        on_change = getattr(self._ctx.config, "maintenance_tag_mode", "interval") == "on_change"
        recheck_tags = force_tags or not on_change or torrent.hash in self._ctx.store.external_tag_changes
        if recheck_tags and on_change:
            self._ctx.store.external_tag_changes.discard(torrent.hash)  # 待重检登记消费一次
        handled = False
        if recheck_tags:
            handled |= self.add_tags(torrent, tracker_conf.tags, dry_run)
            handled |= self.remove_tags(torrent, tracker_conf.remove_tags, dry_run)
            if tracker_conf.remove_similar_tags:  # 站点覆盖全局后的值
                handled |= self.remove_similar_tags(torrent, tracker_conf.tags, dry_run)
        if tracker_conf.hr:  # 站点合并全局默认后的 HR 设置
            handled |= self.add_hr_tag_or_category(torrent, dry_run)
        return REQUEUE

    def add_tags(self, torrent: TorrentRecord, tags: List[str], dry_run: bool, log_level: int = logging.INFO):
        """为种子添加标签（若不存在）; log_level 控制日志级别(如分组流程整组宣告后传 DEBUG 避免逐成员重复)"""
        if not tags:
            return False

        current_tags = torrent.tags_set
        new_tags = [t for t in tags if t not in current_tags]
        if new_tags:
            if not dry_run:
                self._ctx.api.torrents_add_tags(tags=new_tags, torrent_hashes=torrent.hash)
            logger.log(log_level, f"维护 {torrent.log_repr} | 添加标签: {new_tags}")
            return True
        return False

    def remove_tags(self, torrent: TorrentRecord, patterns: List[str], dry_run: bool):
        """为种子删除标签（若存在）."""
        if not patterns:
            return False

        current_tags = torrent.tags_set
        to_remove_tags = [tag for tag in current_tags if utils.match_tag_patterns(tag, patterns)]
        if to_remove_tags:
            if not dry_run:
                self._ctx.api.torrents_remove_tags(tags=to_remove_tags, torrent_hashes=torrent.hash)
            logger.info(f"维护 {torrent.log_repr} | 删除标签: {to_remove_tags}")
            return True
        return False

    def add_episode_tags(self, torrent: TorrentRecord, dry_run: bool):
        """种子添加时自动添加集数标签(如 zE1-5)

        仅种子添加时触发(added 管线调用, P5 收口前经内核委托), 非周期任务。
        名称已含集数标记(S01E01/EP01/第1集等) -> 跳过; 否则从文件列表解析集数(走 store 惰性缓存),
        如 01.mkv~05.mkv -> 添加自定义模板标签(单集用 add_tag_single, 多集用 add_tag_multi)。
        解析不到集数(电影/合集等)或集数非连续则不加标签, 避免错标。
        """
        cfg = self._ctx.config.add_episode_tags
        if not cfg.enabled:
            return
        episodes_list = episodes.extract_episodes_from_files(torrent.files(self._ctx.api.client))
        if not episodes_list:
            return  # 文件列表无集数(电影/合集), 不加标签
        tag = episodes.format_episode_tag(episodes_list, cfg.add_tag_single, cfg.add_tag_multi)
        if not tag:
            return  # 集数非连续(存在缺集/误提取), 放弃添加
        self.add_tags(torrent, [tag], dry_run)

    def remove_similar_tags(self, torrent: TorrentRecord, tags: List[str], dry_run: bool):
        """删除类似(单词相同大小写不同)的tag"""
        if not tags:
            return False

        current_tags = torrent.tags_set

        # 删除单词相同但大小写不一致的标签
        to_remove_tags = [tag for tag in current_tags if tag.lower() in [t.lower() for t in tags] and tag not in tags]
        if to_remove_tags:
            if not dry_run:
                self._ctx.api.torrents_remove_tags(tags=to_remove_tags, torrent_hashes=torrent.hash)
            logger.info(f"维护 {torrent.log_repr} | 删除相似标签: {to_remove_tags}")
            return True

        return False

    def set_category(self, torrent: TorrentRecord, category: str, overwrite: bool, dry_run: bool):
        """设置种子的分类"""
        old_category = torrent.category

        if old_category == category:  # 分类已存在
            return False

        auto_categories = self._ctx.state.data.setdefault("auto_categories", {})

        # 定义一个内部函数可以利用if短路
        def can_update_previous():
            previous_auto_category = auto_categories.get(torrent.hash)
            return old_category == previous_auto_category

        if not old_category or overwrite or can_update_previous():  # 分类为空、强制覆盖或更新此前自动分类
            self.create_category_if_not_exists(category, dry_run)

            # 设置分类
            if not dry_run:
                self._ctx.api.torrents_set_category(category=category, torrent_hashes=torrent.hash)
                auto_categories[torrent.hash] = category

            # 打印日志
            if old_category:
                logger.info(f"维护 {torrent.log_repr} | 修改分类: '{old_category}' -> '{category}'")
            else:
                logger.info(f"维护 {torrent.log_repr} | 设置分类: '{category}'")

            return True
        else:  # 存在分类但不覆盖
            logger.debug(f"维护 {torrent.log_repr} | 跳过设置分类: 已有分类 '{old_category}' 且不覆盖")
            return True

    def create_category_if_not_exists(self, category: str, dry_run: bool):
        """如果分类不存在则创建分类(全部分类走 store 惰性缓存, 创建后失效) """
        current_categories = self._ctx.store.all_categories()
        if category not in current_categories:  # 分类不存在
            if not dry_run:
                self._ctx.api.torrents_create_category(name=category)
            logger.info(f"创建分类: '{category}'")

    # ---------- HR ----------

    def add_hr_tag_or_category(self, torrent: TorrentRecord, dry_run: bool):
        """添加HR标签或分类(基于站点合并后的 hr 设置)

        门禁三段(计划 26-09-30-0559 §4): 放行短路 -> 超额跳过 -> satisfied 分流。
        - 放行(毕业达标 / 未达标终态 / 免罪 / 放行记录): 不打标 —— 终态结论不受本地做种影响;
        - 超额老种(做种 >= 3x 基准): 跳过不打标 —— 义务早已了结, 打卡无信息量;
          被动命中考察中仍打 HR 标签(站点权威);
        - 其余**全量纳入**(2026-09-30 拍板): 做种满 req+extra(或分享率达标)打达标标签,
          否则打 HR 标签 —— 含 downloaded=0 的转移种/纯辅种(本地「不触发」不代表无义务)。
        达标判定委托 TorrentRecord.check_hr_satisfied(单点语义); 命中排除表
        (hr.exclude_tags/exclude_categories)的种子恒早退, 已打的标记残留不回撤(计划 26-09-28-1805)。
        """
        hr = torrent.tracker_conf.hr
        if hr is None:
            return False
        if torrent.hr_excluded():
            return False

        judged = torrent.hr_judgement()
        if judged is not None and judged.identity is HrIdentity.RELEASED:
            return False  # 毕业/终态/免罪/放行记录: 不打标(维持现状)

        baseline = _seed_exempt_baseline(torrent)
        if baseline > 0 and torrent.seeding_time >= SEED_EXEMPT_RATIO * baseline \
                and not (judged is not None and judged.is_hr):
            return False  # 超额老种跳过; 被动命中考察中仍打 HR 标签(站点权威)

        added = False

        # 做种时长满足 或 分享率达标, 添加 satisfied 标签/分类
        if torrent.check_hr_satisfied():
            if hr.add_tag_for_satisfied:
                tag = utils.replace_vars(hr.add_tag_for_satisfied, torrent.tracker_conf)
                added |= self.add_tags(torrent, [tag], dry_run)
            if hr.add_category_for_satisfied:
                category = utils.replace_vars(hr.add_category_for_satisfied, torrent.tracker_conf)
                added |= self.set_category(torrent, category, hr.overwrite_category_for_satisfied, dry_run)
        else:  # 做种时长不够 且 分享率未达标: 添加 HR 标签/分类
            if hr.add_tag:
                tag = utils.replace_vars(hr.add_tag, torrent.tracker_conf)
                added |= self.add_tags(torrent, [tag], dry_run)
            if hr.add_category:
                category = utils.replace_vars(hr.add_category, torrent.tracker_conf)
                added |= self.set_category(torrent, category, hr.overwrite_category, dry_run)
        return added

    # ---------- 全局标签清理(全局任务自注册, 见 start/queue_rebuilt) ----------

    def handle_delete_tags(self, task, dry_run: bool) -> bool:
        """全局任务: 彻底删除匹配格式的标签(支持正则, regex: 前缀)

        匹配所有现有标签定义(含无种子的), 调用 torrents_delete_tags 从所有种子移除并删除定义。
        """
        patterns = self._ctx.config.delete_tags or []
        if not patterns:
            return REQUEUE
        try:
            all_tags = self._ctx.store.all_tags()  # 惰性缓存
        except Exception as e:
            logger.error(f"获取标签列表失败: {e}")
            return REQUEUE
        matched = [t for t in all_tags if utils.match_tag_patterns(t, patterns)]
        if not matched:
            return REQUEUE
        if not dry_run:
            self._ctx.api.torrents_delete_tags(tags=matched)
        logger.info(f"彻底删除标签: {matched}")
        return REQUEUE

    def handle_delete_tags_if_has_no_torrents(self, task, dry_run: bool) -> bool:
        """全局任务: 彻底删除无种子的标签(支持正则, regex: 前缀)

        仅当标签定义存在且没有任何种子使用(所有种子 tags 的并集之外)时才删除。
        """
        patterns = self._ctx.config.delete_tags_if_has_no_torrents or []
        if not patterns:
            return REQUEUE
        try:
            all_tags = self._ctx.store.all_tags()  # 惰性缓存
        except Exception as e:
            logger.error(f"获取标签列表失败: {e}")
            return REQUEUE
        if not all_tags:
            return REQUEUE

        # 从快照聚合标签使用情况(替代 torrents.info(tag=) 逐个查询), 使用数为 0 则删除
        used = self._ctx.store.tag_usage()
        matched = [tag for tag in all_tags if utils.match_tag_patterns(tag, patterns) and used.get(tag, 0) == 0]

        if not matched:
            return REQUEUE
        if not dry_run:
            self._ctx.api.torrents_delete_tags(tags=matched)
        logger.info(f"彻底删除无种子的标签: {matched}")

        return REQUEUE
