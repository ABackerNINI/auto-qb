"""WebCommandsMixin: WEB UI 控制命令消费与回执(主循环线程侧执行体)

从 qbmanager.py 拆出(2026-09-15 大文件拆分批次一)。Web 线程只向 self.web_commands
投递命令并只读 self._web_results 回执; 本 mixin 全部方法都在主循环线程执行
(_tick 经 _drain_web_commands 消费命令, _check_reannounce_pending 每 tick 推进汇报确认)。

依赖的宿主属性(由 QbManager.__init__ 初始化):
- self.web_commands / self._web_results / self._reannounce_pending
- self.api(QbApi) / self.store / self.client
- self.apply_new_config(配置热重载, 定义于 QbManager 核心)
"""
import logging
import queue
import time
from typing import List, Optional

from ..config import Config

logger = logging.getLogger(__name__)

# 强制汇报的 tracker 确认窗口: reannounce 后 qB 立即重发 announce, 私站响应通常 1~10s;
# 留足慢站点余量取 30s(主循环 main_tick=2s -> 约 15 轮确认机会), 超时仍未确认即判失败。
REANNOUNCE_CONFIRM_TIMEOUT = 30.0


class WebCommandsMixin:
    def _drain_web_commands(self):
        """消费 WEB UI 控制命令(Web 线程投递, 主循环线程执行写操作——单一写者约束保持)

        命令带 cmd_id: 执行完立即写回执(_web_results), 供前端 /api/cmd/{id} 轮询执行结果。
        例外: reannounce 只发指令并登记确认跟踪(_reannounce_pending), 回执由
        _check_reannounce_pending 在 tracker 确认后写入 —— "已发送"不等于"汇报成功";
        bulk_torrents 的回执由 handler 聚合写(部分失败需报缺失计数)。
        """
        handlers = {
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
        try:
            while True:
                cmd, payload = self.web_commands.get_nowait()
                cmd_id = str(payload.get("cmd_id") or "")
                args = {k: v for k, v in payload.items() if k != "cmd_id"}
                try:
                    if cmd_id and cmd in ("reannounce_group", "reannounce_torrent", "bulk_torrents", "add_torrents"):
                        # handler 只发指令并登记确认跟踪(bulk: 聚合写回执; add: 依 qB 结果串写回执);
                        # 回执由后续 tick(汇报确认)或 handler 内部写入 —— 均不是简单的"执行完即 ok"
                        handlers[cmd](cmd_id=cmd_id, **args)
                    else:
                        handlers[cmd](**args)
                        if cmd_id:
                            self._set_web_result(cmd_id, "ok")
                except KeyError as e:
                    logger.warning(f"WEB UI 未知命令: {e}")
                    if cmd_id:
                        self._set_web_result(cmd_id, "error", f"未知命令: {e}")
                except Exception as e:
                    logger.error(f"WEB UI 命令执行失败: {cmd}: {e}", exc_info=True)
                    if cmd_id:
                        self._set_web_result(cmd_id, "error", str(e))
        except queue.Empty:
            pass

    def _set_web_result(self, cmd_id: str, status: str, error: str = "") -> None:
        """写入命令执行结果回执(主循环线程唯一写者); 顺手清理 2 分钟前的旧回执防无限增长"""
        now = time.time()
        if len(self._web_results) > 64:
            self._web_results = {k: v for k, v in self._web_results.items() if now - v.get("ts", 0) < 120}
        self._web_results[cmd_id] = {"status": status, "error": error, "ts": now}

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

    def _check_reannounce_pending(self):
        """每 tick 检查在途的强制汇报确认; 某 cmd_id 全部种子出结论后聚合写回执"""
        if not self._reannounce_pending:
            return
        now = time.time()
        finished = []
        for cmd_id, entry in self._reannounce_pending.items():
            for h, it in entry["items"].items():
                if it["done"]:
                    continue
                if now >= entry["deadline"]:
                    it["done"], it["ok"] = True, False
                    it["err"] = f"汇报确认超时({REANNOUNCE_CONFIRM_TIMEOUT:.0f}s 内未确认到 tracker 响应)"
                    continue
                if self.client is None:
                    continue  # qB 断连: 等恢复继续确认, 或按超时判失败
                try:
                    trackers = self.client.torrents_trackers(h) or []
                    r = self._confirm_reannounce_result(trackers, it["baseline"])
                except Exception as e:
                    it["done"], it["ok"], it["err"] = True, False, f"读取 tracker 状态失败: {e}"
                    continue
                if r is True:
                    it["done"], it["ok"] = True, True
                elif r is False:
                    it["done"], it["ok"], it["err"] = True, False, "tracker 未接受汇报(not working)"
            if all(it["done"] for it in entry["items"].values()):
                finished.append(cmd_id)
        for cmd_id in finished:
            entry = self._reannounce_pending.pop(cmd_id)
            items = list(entry["items"].values())
            fails = [it for it in items if not it["ok"]]
            if not fails:
                self._set_web_result(cmd_id, "ok")
                logger.info(f"WEB UI | 强制汇报确认成功({len(items)}个种子)")
            else:
                msg = f"{len(fails)}/{len(items)} 个种子汇报确认失败: " + "; ".join(it["err"] for it in fails[:3])
                self._set_web_result(cmd_id, "error", msg)
                logger.warning(f"WEB UI | {msg}")

    def _cmd_build_search_index(self):
        """WEB UI 命令: 构建搜索索引(Web 线程检测到索引脏后投递, 主循环线程执行)。

        限流构建可能需多轮: 仅在全部拉取完成(不再脏)时记录完成日志, 避免分批刷屏。
        """
        self._build_search_index()
        if not self._search_index_dirty:
            logger.info(f"WEB UI | 搜索索引已构建: {len(self._search_index)} 个种子")

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
        self._reannounce_pending[cmd_id] = {
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
        logger.info(f"WEB UI | 种子 {hash[:8]} 编辑 tracker: {orig_url} -> {new_url}")

    def _cmd_remove_tracker(self, hash: str, url: str = ""):
        if self.store.get(hash) is None:
            return
        if not url:
            raise ValueError("url 不能为空")
        self.api.torrents_remove_trackers(torrent_hash=hash, urls=[url])
        logger.info(f"WEB UI | 种子 {hash[:8]} 移除 tracker: {url}")

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

    def _cmd_bulk_torrents(self, hashes=None, action: str = "", cmd_id: str = "", delete_files: bool = False):
        """WEB UI 命令: 批量操作(单命令批量, 平铺视图多选); 回执由本 handler 聚合写

        - 未知 action / 空 hash 列表 -> error 回执
        - 不在快照中的 hash 跳过(删除守阵), 仍有缺失时回执 error 带缺失计数(部分成功也报错,
          前端可据列表刷新后重试); 全部命中 -> ok
        - API 只调一次: hashes 整体传给既有 api 调用(qB 端点原生接受批量)
        """
        req = [h for h in (hashes or []) if h]
        fn = self._BULK_ACTIONS.get(action)
        if fn is None:
            if cmd_id:
                self._set_web_result(cmd_id, "error", f"未知批量动作: {action}(可选 pause/resume/recheck/delete)")
            return
        if not req:
            if cmd_id:
                self._set_web_result(cmd_id, "error", "未提供任何 hash")
            return
        known = [h for h in req if self.store.get(h) is not None]
        missing = len(req) - len(known)
        if known:
            fn(self.api, known, delete_files)
        if missing:
            msg = f"{missing}/{len(req)} 个种子不存在或已被删除"
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

        回执由本 handler 依 qB 结果串写("Ok."=ok, 其余 error) —— "指令已发"与"qB 接受"分开;
        skip_checking 属高危选项, 前端默认关 + 警告, 此处照传(用户显式动作, 不做二次拦截)。"""
        kwargs = dict(
            save_path=save_path or None,
            category=category or None,
            tags=tags or None,
            is_paused=bool(paused),
            is_skip_checking=bool(skip_checking),
            is_sequential_download=bool(sequential),
            is_first_last_piece_priority=bool(first_last_piece_prio),
        )
        kwargs = {k: v for k, v in kwargs.items() if v not in (None, False)}
        if auto_tmm:
            kwargs["use_auto_torrent_management"] = True
        results = []
        if files:
            results.append(str(self.api.torrents_add(torrent_files=files, **kwargs)))
        if urls:
            results.append(str(self.api.torrents_add(urls=urls, **kwargs)))
        ok = bool(results) and all("Ok." in s for s in results)
        if cmd_id:
            if ok:
                self._set_web_result(cmd_id, "ok")
            else:
                self._set_web_result(cmd_id, "error", f"qB 未接受添加: {'; '.join(results) or '无结果'}")
        logger.warning(f"WEB UI | 添加种子: 文件 {len(files or [])} 个, 链接 {len(urls or [])} 条 -> {results}")
