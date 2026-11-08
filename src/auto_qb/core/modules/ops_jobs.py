"""ops 作业叶: 同步线对账与文件完整性检查(自 ops_mod move-only 切出)

拆分(R5)只搬位置: 方法体与 ops_mod.py 原文件逐字一致。
"""
import os
from typing import Any

from ...infra import file_access, utils
from ...torrents import TorrentRecord
from .ops_common import logger, skip_readd_kwargs

# 备份元数据 R1#94 起补记的重加回传面字段(键名 = TorrentRecord 属性名, 见 _backup_torrent):
# 恢复时按其存在性判旧格式 —— 旧格式缺这些键, 重加按 qB 默认值(库对 None 不发键, wire 同缺省)
_SKIP_BACKUP_READD_KEYS = frozenset(
    (
        "content_layout",
        "up_limit",
        "dl_limit",
        "seq_dl",
        "f_l_piece_prio",
        "ratio_limit",
        "seeding_time_limit",
        "inactive_seeding_time_limit",
        "share_limit_action",
        "share_limits_mode",
    )
)


class JobsMixin:
    # ---------- 跳检崩溃恢复对账(计划 26-10-21-1857 §9) ----------

    def on_sync_line(self, force: bool) -> None:
        """同步线 hook: 首轮快照落地后做一次跳检备份对账(每进程一次)

        账本就是 `state.skip_check_backup` —— 它在删除**之前**落盘(崩溃安全的锚点), 所以
        "有备份" 等价于 "我们当时正准备删/已经删了这个 hash"。对账三分流:
        - 种子已回到客户端 -> 跳检已完成(或用户手动加回): 备份无意义, 清掉;
        - 种子不在且备份文件在 -> 崩溃发生在删除之后、重加之前: 用备份重加(seed_mode);
        - 种子不在且备份文件丢了 -> 只能报 ERROR 交人(没有恢复凭据)。
        """
        if self._skip_recovered or not self._ctx.store.by_hash:
            return
        self._skip_recovered = True
        self._recover_skip_backups()

    def _recover_skip_backups(self) -> None:
        """按备份账本对账(见 on_sync_line 三分流); 幂等: 处理过的条目会被清账"""
        backups = self.state.get("skip_check_backup") or {}
        if not backups:
            return
        for h in list(backups):
            meta = backups.get(h) or {}
            if h in self._ctx.store.by_hash:
                logger.info(f"跳检对账: {h[:8]} 已在客户端, 清理残留备份")
                self._clear_backup(h)
                continue
            path = meta.get("path") or ""
            if not path or not os.path.exists(path):
                logger.error(f"跳检对账: {h[:8]} 不在客户端且备份文件缺失({path or '无路径'}), 需人工处理")
                continue
            try:
                with open(path, "rb") as f:
                    data = f.read()
                if not (_SKIP_BACKUP_READD_KEYS & meta.keys()):
                    logger.warning(f"跳检对账: {h[:8]} 备份元数据为旧格式(缺重加回传面字段), "
                                   "布局/限速/分享限制按 qB 默认重加, 需人工复核")
                logger.warning(f"跳检对账: {h[:8]} 不在客户端(崩溃于删除之后), 用备份重加(未经哈希校验)")
                # 属性回传面与正常重加(_skip_add_call)共用 skip_readd_kwargs 单点(R1#94):
                # 旧格式备份缺键 -> None 值键库不发, wire 与改动前的重加完全一致
                self._ctx.api.torrents_add(
                    torrent_files=[data],
                    **skip_readd_kwargs(meta, meta.get("content_layout")),
                    is_skip_checking=True,
                    is_stopped=True,
                )
            except Exception as e:
                logger.error(f"跳检对账: {h[:8]} 重加失败({e}), 备份保留: {path}")
                continue
            self._clear_backup(h)

    # ---------- 文件完整性检查(checking 前置检查, 决策点 D2 并入 ops) ----------

    @staticmethod
    def check_filelist(api: Any, torrent: TorrentRecord) -> str:
        """检查种子文件是否存在且大小一致(api 为 QbApi Facade或兼容客户端). 返回错误描述字符串, 全部通过返回 None"""
        logger.debug(f"{torrent.log_repr} | 检查文件完整性")
        try:
            files = api.torrents_files(torrent.hash)
        except Exception as e:
            return f"获取文件列表失败: {e}"
        save_path = torrent.save_path
        fa = file_access.get_file_access()
        for f in files:
            full_path = os.path.normpath(os.path.join(save_path, f.name))
            exists = fa.exists(full_path)
            if exists is file_access.UNDETERMINED:
                # 映射 miss: 存在性不可判定 —— 显式报「不可判定」而非「文件缺失」,
                # 让跳检前置保守停住但不误报缺失语义(报告 §05 红线)
                return f"路径不可判定: '{full_path}'(未命中 fs.path_map 映射)"
            if not exists:
                # 孪生(.!qB)存在 -> 文案提示疑似 qB 搬运过渡态(仅诊断信息, 返回语义不变:
                # 跳检前置仍按缺失保守停住); 探测同样经文件访问层, 非 True 按无孪生处理
                if fa.exists(utils.qb_incomplete_twin_path(full_path)) is True:
                    return f"文件缺失: {f.name}(疑似 qB {utils.QB_INCOMPLETE_SUFFIX} 过渡态)"
                return f"文件缺失: {f.name}"
            try:
                if fa.getsize(full_path) != f.size:
                    return f"文件大小不一致: {f.name}"
            except OSError:
                return f"无法读取文件: {f.name}"
        return None
