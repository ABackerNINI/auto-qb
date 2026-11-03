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
from typing import List, Optional, Tuple

from qbittorrentapi import HTTP401Error, HTTP4XXError

from ..config import Config
from ..core.traffic_source import paths as traffic_paths
from ..infra.utils import VIRTUAL_TRACKER_PREFIXES, mask_tracker_url, sanitize_tracker_url
from ..transfer import TransferOrchestrator, TransferStatus, TransferAdapterError, create_adapter
from ..transfer.adapters import TrDownloaderStub

from .commands_common import (
    CMD_ID_COMMANDS,
    CMD_SLOW_MS,
    DEFERRED_RECEIPT_COMMANDS,
    QB_REJECT_HINTS,
    RC_DEFERRED_PREFIX,
    RC_FAIL_PREFIX,
    RC_UNCONFIRMED_PREFIX,
    REANNOUNCE_BACKGROUND_MAX,
    REANNOUNCE_BLOCKED_STATES,
    REANNOUNCE_CONFIRM_TIMEOUT,
    REANNOUNCE_DEFER_EARLY,
    REANNOUNCE_DEFER_MARGIN,
    REANNOUNCE_INACTIVE_SKIP,
    REANNOUNCE_JUMP_TOL,
    REANNOUNCE_WINDOW_CAP,
    RESYNC_COMMANDS,
    SELF_POSTED_COMMANDS,
    TRUTH_PUSH_CAP_MS,
    _OPTIMISTIC_BULK_ACTIONS,
    _add_outcome,
    _bulk_call_limits,
    _timing,
    is_deferred_receipt,
    logger,
    qb_reject_text,
    reannounce_blocked,
)
from .commands_config import ConfigMixin
from .commands_limit import LimitMixin
from .commands_logs import LogsMixin
from .commands_torrents import TorrentsMixin


class WebCommandsMixin(TorrentsMixin, ConfigMixin, LimitMixin, LogsMixin):
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
            "skip_check_torrent": self._cmd_skip_check_torrent,
            "skip_check_precheck": self._cmd_skip_check_precheck,
            "relocate_precheck": self._cmd_relocate_precheck,
            "relocate_precheck_add": self._cmd_relocate_precheck_add,
            "relocate_cancel": self._cmd_relocate_cancel,
            "transfer_run": self._cmd_transfer_run,
            "transfer_test": self._cmd_transfer_test,
            "super_seeding": self._cmd_super_seeding,
            "force_start": self._cmd_force_start,
            "set_torrent_limits": self._cmd_set_torrent_limits,
            "set_share_limits": self._cmd_set_share_limits,
            "set_torrent_location": self._cmd_set_torrent_location,
            "rename_torrent": self._cmd_rename_torrent,
            "queue_torrent": self._cmd_queue_torrent,
            "set_auto_tmm": self._cmd_set_auto_tmm,
            "add_trackers": self._cmd_add_trackers,
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
            "speed_alt_set": self._cmd_speed_alt_set,
            "speed_alt_toggle": self._cmd_speed_alt_toggle,
            "add_torrents": self._cmd_add_torrents,
            "reload_config": self._cmd_reload_config,
            "build_search_index": self._cmd_build_search_index,
            "refresh_traffic": self._cmd_refresh_traffic,
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

    def _trackers_baseline(self, hashes: List[str]) -> Tuple[dict, bool]:
        """读取汇报前各种子的 tracker 状态基线 -> (baseline, epoch_mode)

        baseline: {hash: {url: {"status", "updating", "next", "min"}}} —— 逐 real tracker 行
        记 status/updating 与 next_announce/min_announce(epoch 绝对秒); 行缺键时对应值为 None。
        排除 DHT/PeX/LSD 虚拟 tracker(url 以 **/[DHT]/[PeX]/[LSD] 开头, 它们不走 announce);
        前缀集复用 infra 单点 VIRTUAL_TRACKER_PREFIXES(issue webui-virtual-tracker-prefix-dup:
        本文件曾硬编码 3 份字面量, 增删前缀会漏改)。
        epoch_mode(D3 字段存在性探测): 任一种子的任一 real 行含 "next_announce" 键 = qB 5.2+
        epoch 语义; 全部行都不含 = legacy qB(无前跳判据可用)。同一 qB 实例版本一致, 全局任一
        即可判定。
        qB 断连等读取失败时异常上抛, 由命令分发层写 error 回执。
        """
        baseline = {}
        epoch_mode = False
        for h in hashes:
            trackers = self.client.torrents_trackers(h) or []
            real = {}
            for t in trackers:
                url = str(t.get("url") or "")
                if url.startswith(VIRTUAL_TRACKER_PREFIXES):
                    continue
                if "next_announce" in t:
                    epoch_mode = True
                real[url] = {
                    "status": t.get("status"),
                    "updating": t.get("updating"),
                    "next": t.get("next_announce"),
                    "min": t.get("min_announce"),
                }
            baseline[h] = real
        return baseline, epoch_mode

    # ---- 种子转移(计划 26-10-31-0306 W3): 执行体在主循环线程同步串行, 单一写线程假设同 bulk ----

    def _resolve_transfer_target(self, target_id: str, *, require_enabled: bool):
        """按 name 从 web.transfer.targets 查目标 -> (target, None) 或 (None, 错误文案)

        与路由层预检(routes/transfer.py._find_target)同字段判据(name 匹配 + enabled
        开关都取自 TransferTargetConfig), 两处各薄查一遍 —— 路由层即时 400(前端免轮询),
        本层兜底「投递-执行之间目标被删/停用」的热重载窗口: 查不到就写 error 回执,
        绝不带残缺目标执行(任何不成功路径不碰源, 计划 §01)。
        require_enabled: run 必须已启用(转移高风险, 保守默认); test 只要求存在
        (设置页对未启用目标先行测连通, W1 验收口径)。
        """
        transfer = getattr(self.config.web, "transfer", None)
        for target in (getattr(transfer, "targets", None) or ()):
            if str(getattr(target, "name", "")) == target_id:
                if require_enabled and not getattr(target, "enabled", False):
                    return None, f"转移目标未启用: {target_id}(配置键 web.transfer.targets[].enabled)"
                return target, None
        return None, f"转移目标不存在: {target_id}(见配置键 web.transfer.targets)"

    def _cmd_transfer_run(self, target_id: str = "", hashes=None, keep_source: bool = False, cmd_id: str = ""):
        """WEB UI 命令: 执行一次转移批次(计划 26-10-31-0306 W3) —— 转发 transfer.TransferOrchestrator

        串行逐种子在主循环线程**同步执行**(单一写线程假设; 批量无上限, 验证轮询期间
        主循环被占用是计划 §03 已知形态, 与整组迁移执行同量级)。逐种子状态门/导出/
        映射/添加/验证/删源全在 orchestrator(单一出处), 本层只聚合计数; 结果结构
        TorrentTransferResult.to_receipt() 直出 {hash, 状态(成功/跳过/失败), 原因}。
        回执形状(经 cmd 通道 truth): {results: [...], summary: {success, skipped, failed},
        target: 目标名}; 批次不中断(D6), 单种子失败只结算本条。
        """
        target, err = self._resolve_transfer_target(str(target_id or ""), require_enabled=True)
        if target is None:
            if cmd_id:
                self._set_web_result(cmd_id, "error", err)
            return
        req = [str(h) for h in (hashes or []) if h]
        results = TransferOrchestrator(self.api).run_batch(target, req, keep_source=bool(keep_source))
        summary = {status.value: 0 for status in TransferStatus}
        for item in results:
            summary[item.status.value] += 1
        if cmd_id:
            self._set_web_result(
                cmd_id,
                "ok",
                truth={
                    "results": [item.to_receipt() for item in results],
                    "summary": summary,
                    "target": target.name
                },
            )
        logger.info(
            f"WEB UI | 转移批次 -> {target.name}({len(req)}个): "
            f"成功 {summary['success']} / 跳过 {summary['skipped']} / 失败 {summary['failed']}"
        )

    def _cmd_transfer_test(self, target_id: str = "", cmd_id: str = ""):
        """WEB UI 命令: 测试目标下载器连通(计划 W3) —— create_adapter + test_connection

        只读探测: 不写 state、不动 qB、目标侧零变更(仅登录 + 取版本)。成功回执
        truth={info: 版本等描述}; 失败(TransferAdapterError, 含未知类型兜底)写 error
        回执 —— 协议约定文案面向用户可直接回显, 本层不另加工。tr stub 的
        test_connection 恒返回「暂未实现」文案而不抛(协议里唯一返回错误串的例外,
        D10 不做假接口) —— 按不可用处理写 error 回执。
        """
        target, err = self._resolve_transfer_target(str(target_id or ""), require_enabled=False)
        if target is None:
            if cmd_id:
                self._set_web_result(cmd_id, "error", err)
            return
        try:
            adapter = create_adapter(target)
            info = adapter.test_connection()
        except TransferAdapterError as exc:
            logger.warning(f"WEB UI | 转移目标测试失败 {target.name}: {exc}")
            if cmd_id:
                self._set_web_result(cmd_id, "error", str(exc) or "目标探测失败")
            return
        if isinstance(adapter, TrDownloaderStub):
            if cmd_id:
                self._set_web_result(cmd_id, "error", info)
            logger.info(f"WEB UI | 转移目标测试 {target.name}: {info}")
            return
        if cmd_id:
            self._set_web_result(cmd_id, "ok", truth={"info": info})
        logger.info(f"WEB UI | 转移目标测试 {target.name}: {info}")
