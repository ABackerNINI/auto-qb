"""WebCommandsMixin: WEB UI 控制命令**处理器**与命令表(主循环线程侧执行体)

从 qbmanager.py 拆出(2026-09-15 大文件拆分批次一)。2026-09-20 二次拆分后本模块只留
**命令实现**: 每个 `_cmd_*` 就是一次 qB 写操作, 由 `WebUIRuntime.consume_commands`
(门面)在主循环线程里分发执行 —— 排队、回执、写序号、自投递判据全部归门面, 不在本模块。

依赖的宿主属性:
- self.api(QbApi) / self.store / self.client
- self.web                  WebUIRuntime(回执 / 汇报确认跟踪 / 搜索索引状态)
- self.apply_new_config(配置热重载, 定义于 QbManager 核心)
"""
import logging
import time
from collections.abc import Mapping
from typing import List, Optional

from ..config import Config
from ..infra.utils import sanitize_tracker_url

logger = logging.getLogger(__name__)

# 强制汇报的 tracker 确认窗口: reannounce 后 qB 立即重发 announce, 私站响应通常 1~10s;
# 留足慢站点余量取 30s(主循环 main_tick=2s -> 约 15 轮确认机会), 超时仍未确认即判失败。
REANNOUNCE_CONFIRM_TIMEOUT = 30.0

# **自投递**命令: 由 Web 侧在自己处理过程中 put 回队列(不是用户操作), 投递后**不唤醒**主循环。
# 目前只有 build_search_index —— web_view 在搜索索引脏时自投递(web_view.py:513/:699)。
# ❗若允许它唤醒会形成自激循环: 唤醒 -> drain(单轮最多 SEARCH_INDEX_BUILD_BUDGET=500 条文件 API)
# -> 索引仍脏 -> 再投递 -> 立刻再唤醒 …… 中间没有 tick 兜底, 直接打满 CPU 并冲垮 qB。
# 新增自投递命令时必须同步加进这里(测试守卫: tests/test_web.py::test_api_enqueue_wakes_main_loop)。
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
    }
)

# **延迟回执**命令: handler 只发指令并登记确认跟踪, 真正的结果由后续 tick(tracker 确认)或
# handler 内部(依 qB 返回串写)写入 —— 它们不是"执行完即 ok", 所以 drain 侧**不**补写回执。
DEFERRED_RECEIPT_COMMANDS = frozenset({"reannounce_group", "reannounce_torrent", "bulk_torrents", "add_torrents"})


def _timing(queued_ts: Optional[float], start_ts: float) -> dict:
    """P0-0 埋点: 把一次命令拆成两段耗时(毫秒), 供 /api/cmd/{id} 回传

    wait_ms = 出队时刻 - 投递时刻(命令排队等主循环的空档, P0-1 唤醒后应趋近 0)
    exec_ms = 执行完时刻 - 出队时刻(真正干活: 多数是 1 次 qB API 往返)

    ❗这两段**只在回执里回传**, 要看就得开浏览器控制台 —— 真机上用户不一定开得了(嵌入式
    WebView / 手机 / 不愿开 F12)。故 drain 侧同时落一行日志(见 _log_cmd_timing),
    排查"点了要等几秒"时**不用控制台**。
    """
    if not queued_ts:
        return {}
    return {
        "wait_ms": round((start_ts - queued_ts) * 1000, 1),
        "exec_ms": round((time.time() - start_ts) * 1000, 1),
    }


# 慢命令告警阈值(ms): 超过就按 WARNING 落日志, 便于在日志里直接捞
CMD_SLOW_MS = 300.0

# 真值推送的等待上限(ms): 命令执行完**立即发回执**(只表示"已执行"), 真值另走 `truth`
# 事件稍后推 —— 见 WebUIRuntime.defer_receipt / flush_truths。
# ❗2026-09-20 D2 定案: 原做法是"扣住回执等真值再发", 真机实测 qB 翻状态要 **1258ms**
#   (而命令执行只要 2.7ms)⇒ 扣着回执等 = 把撤下钉死在 1.25s+(实测撤下 2947ms)。
# ❗超时**不推**真值(宁可让前端超时回滚), 因为推一个未落地的真值 = 采纳命令前的旧值 ⇒ 弹回。
#   改这里必须同步前端 TRUTH_HOLD_MS(前端"值覆盖"的保持上限)—— 两边各写各的必然漂移,
#   已有静态守阵钉住。
TRUTH_PUSH_CAP_MS = 8000.0


def _add_outcome(result: object) -> tuple[bool, str]:
    """判定一次 `torrents_add` 的结果 -> (是否受理, 详情文案); 两种响应形态都要认

    - **Web API < 2.14.0**(qB 5.2 之前): 纯文本 `Ok.` / `Fails.`;
    - **Web API >= 2.14.0**(qB 5.2 起, 用户实测 5.2.3): JSON 元数据
      `{success_count, failure_count, pending_count, added_torrent_ids}`, qbittorrent-api 包成
      `TorrentsAddedMetadata`(**dict 子类**, 见库内 torrents.py 的 `resp.json()` 分支)。

    ❗2026-09-24 实测 bug: 老写法只认 `"Ok." in str(result)`, 在 5.2.3 上**恒为假** ——
    `str(TorrentsAddedMetadata(...))` 是 `"TorrentsAddedMetadata({'success_count': 1, ...})"`,
    于是"种子明明加进去了, WEB UI 却弹添加失败"。判据必须同时覆盖两形态。
    `pending_count > 0` = 已受理但仍在异步处理(magnet 元数据未就绪 / 走 search 插件下载),
    同样算受理成功 —— 它不是失败, 只是还没定下 info hash。
    全部失败时 qB 回 HTTP 409, 库直接抛 `Conflict409Error`, 走不到这里(由命令分发层写 error 回执)。
    """
    if isinstance(result, Mapping):
        success = int(result.get("success_count") or 0)
        failure = int(result.get("failure_count") or 0)
        pending = int(result.get("pending_count") or 0)
        return (failure == 0 and (success + pending) > 0), f"成功 {success} / 失败 {failure} / 待定 {pending}"
    text = str(result)
    return ("Ok." in text), text or "无结果"


class WebCommandsMixin:
    def _web_command_handlers(self) -> dict:
        """WEB 控制命令 -> 处理器映射(命令表与处理器实现同处一处, 避免漏挂)

        由 `WebUIRuntime.consume_commands` 取用: 编排(排队/回执/写序号/自投递判据)在 runtime,
        命令表留在实现旁边 —— 新增命令只改这里, 不用去 runtime 里补映射。
        """
        return {
            "pause_group": self._cmd_pause_group,
            "resume_group": self._cmd_resume_group,
            "reannounce_group": self._cmd_reannounce_group,
            "delete_group": self._cmd_delete_group,
            "pause_torrent": self._cmd_pause_torrent,
            "resume_torrent": self._cmd_resume_torrent,
            "reannounce_torrent": self._cmd_reannounce_torrent,
            "delete_torrent": self._cmd_delete_torrent,
            "recheck_torrent": self._cmd_recheck_torrent,
            "super_seeding": self._cmd_super_seeding,
            "force_start": self._cmd_force_start,
            "set_torrent_limits": self._cmd_set_torrent_limits,
            "set_share_limits": self._cmd_set_share_limits,
            "set_torrent_location": self._cmd_set_torrent_location,
            "rename_torrent": self._cmd_rename_torrent,
            "queue_torrent": self._cmd_queue_torrent,
            "set_auto_tmm": self._cmd_set_auto_tmm,
            "add_trackers": self._cmd_add_trackers,
            "edit_tracker": self._cmd_edit_tracker,
            "remove_tracker": self._cmd_remove_tracker,
            "set_file_priority": self._cmd_set_file_priority,
            "rename_fs": self._cmd_rename_fs,
            "bulk_torrents": self._cmd_bulk_torrents,
            "create_category": self._cmd_create_category,
            "edit_category": self._cmd_edit_category,
            "remove_categories": self._cmd_remove_categories,
            "create_tags": self._cmd_create_tags,
            "delete_tags": self._cmd_delete_tags,
            "speed_override": self._cmd_speed_override,
            "add_torrents": self._cmd_add_torrents,
            "reload_config": self._cmd_reload_config,
            "build_search_index": self._cmd_build_search_index,
        }

    def _set_web_result(
        self,
        cmd_id: str,
        status: str,
        error: str = "",
        timing: Optional[dict] = None,
        truth: Optional[dict] = None
    ) -> None:
        """写回执(转发到 WebUIRuntime) —— 命令处理器内部写回执走这里, 实现不分家

        真实存储与过期清理在 `WebUIRuntime.set_result`。
        """
        self.web.set_result(cmd_id, status, error, timing, truth)

    def _trackers_baseline(self, hashes: List[str]) -> dict:
        """读取汇报前各种子的 tracker 状态基线: {hash: {url: (status, next_announce)}}

        排除 DHT/PeX/LSD 虚拟 tracker(url 以 **/[DHT]/[PeX]/[LSD] 开头, 它们不走 announce)。
        qB 断连等读取失败时异常上抛, 由命令分发层写 error 回执。
        """
        baseline = {}
        for h in hashes:
            trackers = self.client.torrents_trackers(h) or []
            real = {}
            for t in trackers:
                url = str(t.get("url") or "")
                if url.startswith(("**", "[DHT]", "[PeX]", "[LSD]")):
                    continue
                real[url] = (t.get("status"), t.get("next_announce"))
            baseline[h] = real
        return baseline

    @staticmethod
    def _confirm_reannounce_result(trackers: list, baseline: dict) -> Optional[bool]:
        """判定单个种子汇报确认结果: True=已确认成功 / False=已确认失败 / None=仍在进行

        逐 tracker 检查, 任一命中即结论:
        - status == 3 (updating)                    -> qB 正在汇报, 视为成功
        - next_announce 比基线提前(>60 单位, 秒/毫秒通用) -> next_announce 被重置, 视为成功
        - status 从非 working 变为 2 (working)      -> 视为成功
        - status == 4 (not working) 且带错误消息    -> tracker 拒绝, 视为失败
        """
        for t in trackers:
            url = str(t.get("url") or "")
            if url.startswith(("**", "[DHT]", "[PeX]", "[LSD]")):
                continue
            b_status, b_na = baseline.get(url, (None, None))
            status = t.get("status")
            na = t.get("next_announce")
            if status == 3:
                return True
            if na is not None and b_na is not None and na < b_na - 60:
                return True
            if status == 2 and b_status is not None and b_status != 2:
                return True
            if status == 4 and (t.get("msg") or ""):
                return False
        return None

    def _cmd_build_search_index(self):
        """WEB UI 命令: 构建搜索索引(Web 线程检测到索引脏后投递, 主循环线程执行)。

        限流构建可能需多轮: 仅在全部拉取完成(不再脏)时记录完成日志, 避免分批刷屏。
        """
        self._build_search_index()
        if not self.web.search_index_dirty:
            logger.info(f"WEB UI | 搜索索引已构建: {len(self.web.search_index)} 个种子")

    def _cmd_pause_group(self, key: tuple):
        hashes = self._group_hashes(key)
        if hashes:
            self.api.torrents_pause(torrent_hashes=hashes)
            logger.info(f"WEB UI | 暂停整组({len(hashes)}个种子)")

    def _cmd_resume_group(self, key: tuple):
        hashes = self._group_hashes(key)
        if hashes:
            self.api.torrents_resume(torrent_hashes=hashes)
            logger.info(f"WEB UI | 开始整组({len(hashes)}个种子)")

    def _cmd_reannounce_group(self, key: tuple, cmd_id: str = ""):
        hashes = self._group_hashes(key)
        if hashes:
            self.api.torrents_reannounce(torrent_hashes=hashes)
            # 发送仅是"已下发指令"; 成功回执由 tracker 确认跟踪器在后续 tick 写入
            baseline = self._trackers_baseline(hashes)
            self._register_reannounce_pending(cmd_id, hashes, baseline)
            logger.warning(f"WEB UI | 强制汇报整组({len(hashes)}个种子), 等待 tracker 确认")

    def _cmd_delete_group(self, key: tuple, delete_files: bool = False):
        hashes = self._group_hashes(key)
        if hashes:
            self.api.torrents_delete(torrent_hashes=hashes, delete_files=delete_files)
            logger.warning(f"WEB UI | 删除整组({len(hashes)}个种子, delete_files={delete_files})")

    def _cmd_pause_torrent(self, hash: str):
        if self.store.get(hash) is not None:
            self.api.torrents_pause(torrent_hashes=[hash])
            logger.info(f"WEB UI | 暂停种子 {hash[:8]}")

    def _cmd_resume_torrent(self, hash: str):
        if self.store.get(hash) is not None:
            self.api.torrents_resume(torrent_hashes=[hash])
            logger.info(f"WEB UI | 开始种子 {hash[:8]}")

    def _cmd_reannounce_torrent(self, hash: str, cmd_id: str = ""):
        if self.store.get(hash) is None:
            # 种子已不存在: 无法汇报, 直接给失败回执(删除流程据此不删除)
            if cmd_id:
                self._set_web_result(cmd_id, "error", "种子不存在或已被删除")
            return
        self.api.torrents_reannounce(torrent_hashes=[hash])
        baseline = self._trackers_baseline([hash])
        self._register_reannounce_pending(cmd_id, [hash], baseline)
        logger.warning(f"WEB UI | 强制汇报种子 {hash[:8]}, 等待 tracker 确认")

    def _register_reannounce_pending(self, cmd_id: str, hashes: List[str], baseline: dict) -> None:
        """登记汇报确认跟踪: 全部种子出结论(成功/失败/超时)后聚合写该 cmd_id 的回执"""
        if not cmd_id:
            return  # 无回执需求的调用(直接构造 manager 的场景): 只发指令不跟踪
        self.web.reannounce_pending[cmd_id] = {
            "deadline": time.time() + REANNOUNCE_CONFIRM_TIMEOUT,
            "items": {
                h: {
                    "done": False,
                    "ok": False,
                    "err": "",
                    "baseline": baseline[h]
                }
                for h in hashes
            },
        }

    def _cmd_delete_torrent(self, hash: str, delete_files: bool = False):
        if self.store.get(hash) is not None:
            self.api.torrents_delete(torrent_hashes=[hash], delete_files=delete_files)
            logger.warning(f"WEB UI | 删除种子 {hash[:8]}(delete_files={delete_files})")

    def _cmd_recheck_torrent(self, hash: str):
        if self.store.get(hash) is not None:
            self.api.torrents_recheck(torrent_hashes=[hash])
            logger.info(f"WEB UI | 重新校验种子 {hash[:8]}")

    def _cmd_super_seeding(self, hash: str, enable: bool = False):
        if self.store.get(hash) is not None:
            self.api.torrents_set_super_seeding(enable=enable, torrent_hashes=[hash])
            logger.info(f"WEB UI | 种子 {hash[:8]} 超级做种({'开' if enable else '关'})")

    def _cmd_force_start(self, hash: str, enable: bool = False):
        if self.store.get(hash) is not None:
            self.api.torrents_set_force_start(enable=enable, torrent_hashes=[hash])
            logger.info(f"WEB UI | 种子 {hash[:8]} 强制开始({'开' if enable else '关'})")

    def _cmd_set_torrent_limits(self, hash: str, up_limit: Optional[int] = None, dl_limit: Optional[int] = None):
        """种子传输限速(bytes/s, 0 = 不限); 只下发非 None 的方向, 快照 up_limit/dl_limit 同步更新"""
        if self.store.get(hash) is None:
            return
        if up_limit is not None:
            self.api.torrents_set_upload_limit(torrent_hashes=[hash], limit=int(up_limit))
        if dl_limit is not None:
            self.api.torrents_set_download_limit(torrent_hashes=[hash], limit=int(dl_limit))
        logger.info(f"WEB UI | 种子 {hash[:8]} 限速更新(up={up_limit}, down={dl_limit} bytes/s, 0=不限; 仅设置提供的方向)")

    def _cmd_set_share_limits(
        self,
        hash: str,
        ratio_limit: Optional[float] = None,
        seeding_time_limit: Optional[int] = None,
        inactive_seeding_time_limit: Optional[int] = None,
    ):
        """种子分享限制; 缺失维度按 -2(使用全局默认)补齐 —— 库不过滤 None, 直传会发字面量 "None"

        哨兵语义(与 qbittorrent-api torrents_set_share_limits 文档一致):
        -2 = 使用全局分享限制默认值; -1 = 不限制; 正数 = 限制值(比例/分钟)。
        """
        if self.store.get(hash) is None:
            return
        self.api.torrents_set_share_limits(
            ratio_limit=-2.0 if ratio_limit is None else float(ratio_limit),
            seeding_time_limit=-2 if seeding_time_limit is None else int(seeding_time_limit),
            inactive_seeding_time_limit=-2 if inactive_seeding_time_limit is None else int(inactive_seeding_time_limit),
            torrent_hashes=[hash],
        )
        logger.info(
            f"WEB UI | 种子 {hash[:8]} 分享限制更新(ratio={ratio_limit}, seeding_time={seeding_time_limit}, "
            f"inactive={inactive_seeding_time_limit}; -1=不限制, -2=用全局)"
        )

    def _cmd_set_torrent_location(self, hash: str, location: str = ""):
        if self.store.get(hash) is None:
            return
        if not location:
            raise ValueError("location 不能为空")
        self.api.torrents_set_location(torrent_hashes=[hash], location=location)
        # 组键含 save_path: 移动后下轮同步会按新 save_path 重归组(旧组解散/新组建立), 属预期行为
        logger.warning(f"WEB UI | 种子 {hash[:8]} 移动保存路径 -> {location}(将按新路径重归组, 属预期)")

    def _cmd_rename_torrent(self, hash: str, name: str = ""):
        if self.store.get(hash) is None:
            return
        if not name:
            raise ValueError("重命名名称不能为空")
        self.api.torrents_rename(torrent_hash=hash, new_torrent_name=name)
        # 只改 qB 显示名: 快照 name 不手工改, 下轮 sync 自然更新
        logger.info(f"WEB UI | 重命名种子 {hash[:8]} -> {name}")

    # 队列调整动作 -> QbApi 方法映射(qB 端点语义: top/bottom 置顶/置底, up/down 相邻交换)
    _QUEUE_ACTIONS = {
        "top": "torrents_top_priority",
        "up": "torrents_increase_priority",
        "down": "torrents_decrease_priority",
        "bottom": "torrents_bottom_priority",
    }

    def _cmd_queue_torrent(self, hash: str, action: str = ""):
        method = self._QUEUE_ACTIONS.get(action)
        if method is None:
            raise ValueError(f"未知队列动作: {action}(可选 top/up/down/bottom)")
        if self.store.get(hash) is None:
            return
        getattr(self.api, method)(torrent_hashes=[hash])
        logger.info(f"WEB UI | 种子 {hash[:8]} 队列调整: {action}")

    def _cmd_set_auto_tmm(self, hash: str, enable: bool = False):
        if self.store.get(hash) is not None:
            self.api.torrents_set_auto_management(enable=enable, torrent_hashes=[hash])
            logger.info(f"WEB UI | 种子 {hash[:8]} 自动管理({'开' if enable else '关'})")

    def _cmd_add_trackers(self, hash: str, urls=None):
        if self.store.get(hash) is None:
            return
        url_list = [u for u in (urls or []) if u]
        if not url_list:
            raise ValueError("urls 不能为空")
        self.api.torrents_add_trackers(torrent_hash=hash, urls=url_list)
        logger.info(f"WEB UI | 种子 {hash[:8]} 添加 {len(url_list)} 个 tracker")

    def _cmd_edit_tracker(self, hash: str, orig_url: str = "", new_url: str = ""):
        if self.store.get(hash) is None:
            return
        if not orig_url or not new_url:
            raise ValueError("orig_url/new_url 均不能为空")
        self.api.torrents_edit_tracker(torrent_hash=hash, original_url=orig_url, new_url=new_url)
        # 只用脱敏后的主地址: announce URL 的 query 里常内嵌 passkey 等凭据, 落盘日志即泄露面
        logger.info(
            f"WEB UI | 种子 {hash[:8]} 编辑 tracker: "
            f"{sanitize_tracker_url(orig_url)} -> {sanitize_tracker_url(new_url)}"
        )

    def _cmd_remove_tracker(self, hash: str, url: str = ""):
        if self.store.get(hash) is None:
            return
        if not url:
            raise ValueError("url 不能为空")
        self.api.torrents_remove_trackers(torrent_hash=hash, urls=[url])
        logger.info(f"WEB UI | 种子 {hash[:8]} 移除 tracker: {sanitize_tracker_url(url)}")

    # qB 文件优先级合法值(0=不下载, 1=普通, 6=高, 7=最大)
    _FILE_PRIORITIES = frozenset((0, 1, 6, 7))

    def _cmd_set_file_priority(self, hash: str, indices=None, priority: int = 0):
        if self.store.get(hash) is None:
            return
        idx = [int(i) for i in (indices or [])]
        prio = int(priority)
        if not idx:
            raise ValueError("indices 不能为空")
        if prio not in self._FILE_PRIORITIES:
            raise ValueError(f"非法文件优先级: {priority}(可选 0/1/6/7)")
        self.api.torrents_file_priority(torrent_hash=hash, file_ids=idx, priority=prio)
        logger.info(f"WEB UI | 种子 {hash[:8]} 文件优先级: {idx} -> {prio}")

    def _cmd_rename_fs(self, hash: str, old_path: str = "", new_path: str = "", is_folder: bool = False):
        if self.store.get(hash) is None:
            return
        if not old_path or not new_path:
            raise ValueError("old_path/new_path 均不能为空")
        if is_folder:
            self.api.torrents_rename_folder(torrent_hash=hash, old_path=old_path, new_path=new_path)
        else:
            self.api.torrents_rename_file(torrent_hash=hash, old_path=old_path, new_path=new_path)
        logger.info(f"WEB UI | 种子 {hash[:8]} 重命名{'文件夹' if is_folder else '文件'}: {old_path} -> {new_path}")

    # 批量动作 -> API 调用(单次调用传全部 hashes, 不逐个循环; delete 透传 delete_files)
    _BULK_ACTIONS = {
        "pause":
            lambda api, hashes, delete_files: api.torrents_pause(torrent_hashes=hashes),
        "resume":
            lambda api, hashes, delete_files: api.torrents_resume(torrent_hashes=hashes),
        "recheck":
            lambda api, hashes, delete_files: api.torrents_recheck(torrent_hashes=hashes),
        "delete":
            lambda api, hashes, delete_files: api.torrents_delete(torrent_hashes=hashes, delete_files=delete_files),
    }

    def _cmd_bulk_torrents(
        self, hashes=None, action: str = "", cmd_id: str = "", delete_files: bool = False, keys=None
    ):
        """WEB UI 命令: 批量操作(单命令批量, 平铺视图多选); 回执由本 handler 聚合写

        - 未知 action / 空 hash 列表 -> error 回执
        - 不在快照中的 hash 跳过(删除守阵), 仍有缺失时回执 error 带缺失计数(部分成功也报错,
          前端可据列表刷新后重试); 全部命中 -> ok
        - API 只调一次: hashes 整体传给既有 api 调用(qB 端点原生接受批量)
        - 组键模式(DLG-02): keys 为分组 key 列表(tuple, Web 层已解码), 逐组展开成员
          (经 _group_hashes 按快照过滤, 级联全部在册成员)并与 hashes 合并去重; 组不存在或
          成员全部不在快照计一个缺失组, 缺失文案与种子缺失分列(纯 hash 模式文案不变, 前端契约保持)
        """
        req = [h for h in (hashes or []) if h]
        keys = [k for k in (keys or []) if k]
        fn = self._BULK_ACTIONS.get(action)
        if fn is None:
            if cmd_id:
                self._set_web_result(cmd_id, "error", f"未知批量动作: {action}(可选 pause/resume/recheck/delete)")
            return
        if not req and not keys:
            if cmd_id:
                self._set_web_result(cmd_id, "error", "未提供任何 hash 或组")
            return
        known = [h for h in req if self.store.get(h) is not None]
        missing = len(req) - len(known)
        seen = set(known)
        missing_groups = 0
        for key in keys:
            members = [h for h in self._group_hashes(key) if h not in seen]
            if members:
                seen.update(members)
                known.extend(members)
            else:
                missing_groups += 1
        if known:
            fn(self.api, known, delete_files)
        msgs = []
        if missing:
            msgs.append(f"{missing}/{len(req)} 个种子不存在或已被删除")
        if missing_groups:
            msgs.append(f"{missing_groups}/{len(keys)} 个组不存在或成员为空")
        if msgs:
            msg = "; ".join(msgs)
            if cmd_id:
                self._set_web_result(cmd_id, "error", msg)
            logger.warning(f"WEB UI | 批量 {action}({len(known)}个种子): {msg}")
        else:
            if cmd_id:
                self._set_web_result(cmd_id, "ok")
            logger.warning(f"WEB UI | 批量 {action}({len(known)}个种子, delete_files={delete_files})")

    def _cmd_reload_config(self, config: Config):
        self.apply_new_config(config)

    # ---------- 管理命令(R2B: 分类/标签/限速覆盖/添加种子) ----------

    def _cmd_create_category(self, name: str, save_path: str = ""):
        self.api.torrents_create_category(name=name, save_path=save_path or None)
        logger.info(f"WEB UI | 新建分类: {name}" + (f"(保存路径 {save_path})" if save_path else ""))

    def _cmd_edit_category(self, name: str, save_path: str = ""):
        self.api.torrents_edit_category(name=name, save_path=save_path or None)
        logger.info(f"WEB UI | 修改分类: {name} -> 保存路径 {save_path or '(未设置)'}")

    def _cmd_remove_categories(self, names=None):
        self.api.torrents_remove_categories(categories=names)
        logger.warning(f"WEB UI | 删除分类: {', '.join(names)}")

    def _cmd_create_tags(self, tags=None):
        self.api.torrents_create_tags(tags=tags)
        logger.info(f"WEB UI | 新建标签: {', '.join(tags)}")

    def _cmd_delete_tags(self, tags=None):
        self.api.torrents_delete_tags(tags=tags)
        logger.warning(f"WEB UI | 删除标签: {', '.join(tags)}")

    def _cmd_speed_override(self, upload_kib: int = 0, download_kib: int = 0):
        """全局限速手动覆盖(D2): 曲线启用时为"临时覆盖"——曲线任务下一档位切换写回目标值;
        曲线停用即常态设置。不做"暂停曲线接管"状态。"""
        self.api.set_global_speed_limits(upload_kib=int(upload_kib or 0), download_kib=int(download_kib or 0))
        logger.warning(f"WEB UI | 全局限速手动覆盖: 上 {upload_kib} / 下 {download_kib} KiB/s")

    def _cmd_add_torrents(
        self,
        files=None,
        urls=None,
        save_path: str = "",
        category: str = "",
        tags=None,
        paused: bool = False,
        skip_checking: bool = False,
        sequential: bool = False,
        first_last_piece_prio: bool = False,
        auto_tmm: bool = False,
        cmd_id: str = ""
    ):
        """WEB UI 添加种子: .torrent 原始 bytes 经命令队列传给主循环线程, 内存直交 qB(qbittorrent-api
        _normalize_torrent_files 原生支持 bytes) —— 零临时文件。

        回执由本 handler 依 qB 结果串写(受理=ok, 否则 error, 两形态判定见 `_add_outcome`) ——
        "指令已发"与"qB 接受"分开; skip_checking 属高危选项, 前端默认关 + 警告, 此处照传
        (用户显式动作, 不做二次拦截)。

        选项下发口径: **qB 侧 `std::optional` 的两个选项(停止位 / 自动管理)恒显式传布尔**,
        其余普通 `bool` 选项为假时省略(缺省即 false, 省略安全) —— 判据见下方注释与
        `memory-bank/pitfalls/backend/qb-api.md`。"""
        kwargs = dict(
            save_path=save_path or None,
            category=category or None,
            tags=tags or None,
            is_skip_checking=bool(skip_checking),
            is_sequential_download=bool(sequential),
            is_first_last_piece_priority=bool(first_last_piece_prio),
        )
        kwargs = {k: v for k, v in kwargs.items() if v not in (None, False)}
        # ❗停止位是**唯一必须显式下发**的布尔选项(既不能省, 也不能用 is_paused 传), 两处坑叠加
        #   才会让前端「添加后开始」勾了等于没勾(2026-09-24 实测 bug):
        #   ① qB 侧 `stopped` 缺省时**不是** false, 而是回落到会话级默认 —— SessionImpl::
        #      initLoadTorrentParams 里 `addStopped.value_or(isAddTorrentStopped())`, 那个会话值由
        #      qB 自己的添加对话框/选项("不自动开始")写入 ⇒ 用户勾了「添加后开始」照样按停止添加;
        #   ② qbittorrent-api 的 `is_stopped = is_paused or is_stopped` 会把 **is_paused=False 折成
        #      None**(`False or None` == None) ⇒ 传 is_paused=False 等于没传(实测请求体为空字符串);
        #      只有 is_stopped=False 才会真的发出 `paused=false&stopped=false`。
        #   qB 自家 WebUI 同此口径: addtorrent.js 恒传 stopped=true/false, 从不省略。
        kwargs["is_stopped"] = bool(paused)
        # 自动管理同理**必须显式下发**(qB 侧 `useAutoTMM` 也是 `std::optional`):
        # 缺省时 `SessionImpl::initLoadTorrentParams` 走
        # `value_or(savePath 空 ∧ downloadPath 空 ∧ !isAutoTMMDisabledByDefault())`
        # ⇒ 不填保存路径且 qB 全局是"自动管理"时会被判成 True, 前端那个勾选框等于没勾。
        # (填了保存路径时缺省恰好也得 false, 所以这个隐患只在"未勾 + 未填路径"这一支暴露。)
        # qB 自家 WebUI 的 autoTMM 是 `<select name="autoTMM">`(Manual=false 默认 / Automatic=true),
        # 随表单恒提交 —— 同此口径。
        # ❗只有 qB 侧声明为 `std::optional` 的选项才需要这样显式下发; 普通 `bool` 的
        #   (sequential / firstLastPiecePriority / skip_checking) 缺省就是 false, 省略安全。
        kwargs["use_auto_torrent_management"] = bool(auto_tmm)
        results = []
        if files:
            results.append(self.api.torrents_add(torrent_files=files, **kwargs))
        if urls:
            results.append(self.api.torrents_add(urls=urls, **kwargs))
        outcomes = [_add_outcome(r) for r in results]
        ok = bool(outcomes) and all(o[0] for o in outcomes)
        detail = "; ".join(o[1] for o in outcomes)
        if cmd_id:
            if ok:
                self._set_web_result(cmd_id, "ok")
            else:
                self._set_web_result(cmd_id, "error", f"qB 未接受添加: {detail}")
        # 级别即通知语义(见 conventions/code-style.md 日志规范): 受理成功走 INFO —— 原写法用
        # WARNING, 而 NotifyHandler 挂在 auto_qb logger 上 ⇒ **每次添加成功都往桌面推一条
        # "auto-qb WARNING" 弹窗**, 用户据此以为添加失败。
        line = f"WEB UI | 添加种子: 文件 {len(files or [])} 个, 链接 {len(urls or [])} 条 -> {detail}"
        if ok:
            logger.info(line)
        else:
            logger.warning(line + "(qB 未接受)")
