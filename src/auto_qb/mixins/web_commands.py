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
        reannounce 例外: handler 只发指令并登记确认跟踪(_reannounce_pending), 回执由
        _check_reannounce_pending 在 tracker 确认后写入 —— "已发送"不等于"汇报成功"。
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
            "reload_config": self._cmd_reload_config,
            "build_search_index": self._cmd_build_search_index,
        }
        try:
            while True:
                cmd, payload = self.web_commands.get_nowait()
                cmd_id = str(payload.get("cmd_id") or "")
                args = {k: v for k, v in payload.items() if k != "cmd_id"}
                try:
                    if cmd_id and cmd in ("reannounce_group", "reannounce_torrent"):
                        # handler 只发指令并登记确认跟踪; 回执由 _check_reannounce_pending 在
                        # tracker 确认后写入 —— "已发送"不等于"汇报成功", 故此处不写 ok
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
    def _cmd_reload_config(self, config: Config):
        self.apply_new_config(config)
