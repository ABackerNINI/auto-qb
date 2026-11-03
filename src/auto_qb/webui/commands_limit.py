"""LimitMixin: 限速 / 分享限制域命令处理器

move-only 自 commands.py 切出(计划 26-11-02-2342 §07 R5), 未改语义。
"""
from typing import Optional

from .commands_common import logger


class LimitMixin:
    def _speed_action(self, upload_kib: int, download_kib: int, method: str, verb: str) -> None:
        """全局/备用限速写命令单点: 只差方法名与日志动词(0 = 不限)"""
        getattr(self.api, method)(upload_kib=int(upload_kib or 0), download_kib=int(download_kib or 0))
        logger.info(f"WEB UI | {verb}: 上 {upload_kib} / 下 {download_kib} KiB/s")

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
        """种子分享限制; 缺失维度按 -2(使用全局默认)补齐; share_limits_mode 恒传 "Default"
        (= qB 全局分享限制模式, 即 5.2 旧行为; 5.3 起该端点必填此参, 缺失 400); share_limit_action
        恒传 "Default"(= 到限执行 qB 全局默认动作; qB 5.0/Web API 2.10.4 起必填, 缺失 400,
        issue 26-11-01-2102)

        哨兵语义(与 qbittorrent-api torrents_set_share_limits 文档一致):
        -2 = 使用全局分享限制默认值; -1 = 不限制; 正数 = 限制值(比例/分钟)。
        """
        if self.store.get(hash) is None:
            return
        self.api.torrents_set_share_limits(
            ratio_limit=-2.0 if ratio_limit is None else float(ratio_limit),
            seeding_time_limit=-2 if seeding_time_limit is None else int(seeding_time_limit),
            inactive_seeding_time_limit=-2 if inactive_seeding_time_limit is None else int(inactive_seeding_time_limit),
            share_limits_mode="Default",
            share_limit_action="Default",
            torrent_hashes=[hash],
        )
        logger.info(
            f"WEB UI | 种子 {hash[:8]} 分享限制更新(ratio={ratio_limit}, seeding_time={seeding_time_limit}, "
            f"inactive={inactive_seeding_time_limit}, mode=Default; -1=不限制, -2=用全局)"
        )

    def _cmd_speed_override(self, upload_kib: int = 0, download_kib: int = 0):
        """全局限速手动覆盖(D2): 曲线启用时为"临时覆盖"——曲线任务下一档位切换写回目标值;
        曲线停用即常态设置。不做"暂停曲线接管"状态。"""
        self._speed_action(upload_kib, download_kib, "set_global_speed_limits", "全局限速手动覆盖")

    def _cmd_speed_alt_set(self, upload_kib: int = 0, download_kib: int = 0):
        """备用速度限制设置(ALT-01): app/setPreferences(alt_*), 与主速度覆盖互不触碰;
        曲线任务只写主速度(transfer 端点), 备用速度无接管方。"""
        self._speed_action(upload_kib, download_kib, "set_alt_speed_limits", "备用速度限制设置")

    def _cmd_speed_alt_toggle(self):
        """主/备速度模式切换(ALT-01, 状态栏乌龟按钮): qB toggle 端点;
        新状态由主轮询 server_state.use_alt_speed_limits 回读, 此处不回传。"""
        self.api.toggle_speed_limits_mode()
        logger.info("WEB UI | 速度模式已切换(主/备)")
