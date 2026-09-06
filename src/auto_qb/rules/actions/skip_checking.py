"""skip-checking 跳检四阶段(SkipCheckingMixin)

包含: 轮询 helper(_poll_until)与跳检全部阶段 —— 前置闸门(_skip_gates)、
删除确认(_skip_delete)、重加恢复(_skip_readd)、布局推断(_infer_content_layout)、
失败备份(_backup_torrent)。风险控制详见 _execute_skip_checking docstring。
"""
import logging
import os
import time
from datetime import date
from typing import Optional

from qbittorrentapi import TorrentDictionary

from ... import utils
from ...torrents import TorrentRecord
from ..base import ActionResult, RuleContext

logger = logging.getLogger(__name__)


def _poll_until(predicate, attempts: int, interval: float) -> bool:
    """轮询直至 predicate 为真或次数耗尽(异常视为未满足); 返回是否满足

    供跳检的删除/重加确认共用: qB 的删除与重加均为异步生效, 需短间隔轮询客户端状态。
    """
    for _ in range(attempts):
        try:
            if predicate():
                return True
        except Exception:
            pass
        time.sleep(interval)
    return False


class SkipCheckingMixin:
    """skip-checking 跳检四阶段: 由 CheckAction 组合, 依赖 self 的
    basic_check/with_reference/without_reference(checking.py 解析)"""
    def _execute_skip_checking(self, ctx: RuleContext, segment: dict, has_reference: bool):
        """辅种跳检(高风险): 导出 → 删除(保留文件) → 确认消失 → 重加(跳过校验) → 确认出现 → 恢复快照

        四阶段: 前置闸门(无副作用) / 准备(删除前读取) / 执行(删除→恢复) / 收尾。
        风险控制:
        - 部分下载(0<progress<1)禁止跳检: 预分配零块会被当作有效数据上传
        - 跨规则同日去重: 多条规则都配 checking 时, 同一种子当日也只跳检一次(统计只丢一次)
        - 强制前置 filelist 检查(文件全部存在且大小一致), 未通过不执行(execute() 中)
        - 删除后轮询确认消失(qB 删除异步), 重加前未消失则放弃(种子仍在, 无损失)
        - 重加属性直传(0/负值有语义) + contentLayout 推断(布局错位不自愈)
        - 重加成功恢复删除前快照记录(tracker_conf/惰性缓存保留, 否则永久未匹配)
        - 无参考种子跳检: 高风险(仅基础文件存在与大小对比, 内容错误会传垃圾数据), 警告但允许
        - 重加失败时 .torrent 落盘备份并记录元数据(立即落盘), 提示手动恢复
        - 删除种子会清空该种子本地统计, 属固有风险, 需规则显式配置
        """
        torrent = ctx.torrent

        # ---- 阶段 1: 前置闸门 (任一不过 → fail/skip 返回, 无副作用) ----
        gate = self._skip_gates(ctx, torrent)
        if gate is not None:
            return gate

        # ---- 阶段 2: 准备 (导出/校验属性/布局推断, 均须在删除前完成) ----
        try:
            data = ctx.api.torrents_export(torrent_hash=ctx.hash)
        except Exception as e:
            return ActionResult.fail(f"导出 .torrent 失败: {e}")
        if not data:
            return ActionResult.fail("导出 .torrent 为空")

        # 重加所需的 6 属性存在性已由启动期 schema 校验保证(refresh 首次拉取时验证
        # REQUIRED_TORRENT_FIELDS, 含 RE_ADD_FIELDS); 直接引用原始 TorrentDictionary
        # (删除不会改变 Python 对象内容)
        tor = torrent.tor

        # 布局推断依赖 content_path/save_path/文件列表(惰性缓存, filelist 前置检查已填充);
        # 删除后 store 记录已移除, 必须在此之前完成
        content_layout = self._infer_content_layout(torrent, ctx.client)

        # ---- 阶段 3: 执行 (删除 → 确认消失 → 重加 → 确认出现 → 恢复快照) ----
        failed = self._skip_delete(ctx, torrent)
        if failed is not None:
            return failed
        failed = self._skip_readd(ctx, torrent, data, tor, content_layout)
        if failed is not None:
            return failed

        # ---- 阶段 4: 收尾 ----
        # 无参考高风险警告(用删除前捕获的 torrent: 真实流程中删除后 ctx.torrent 为 None)
        if not has_reference:
            logger.warning(f"规则[{ctx.rule_name}] {torrent.log_repr} | 无参考跳检(高风险): "
                           f"仅文件存在与大小对比, 内容错误会传垃圾数据")
        if segment["auto_start"]:
            try:
                ctx.api.torrents_start(torrent_hashes=ctx.hash)
            except Exception as e:
                return ActionResult.fail(f"自动开始失败: {e}")
            return ActionResult.ok("skip-checking 跳检完成并自动开始")
        return ActionResult.ok("skip-checking 跳检完成")

    def _skip_gates(self, ctx: RuleContext, torrent: TorrentRecord) -> Optional[ActionResult]:
        """跳检前置闸门: 部分下载禁止 + 跨规则同日去重。返回 None = 全部通过。

        - 部分下载(0<progress<1)禁止: 预分配使文件尺寸=完整尺寸, filelist 尺寸检查无法
          发现未下载的零块, is_skip_checking 会把全部块标记有效 -> 零块被上传(垃圾数据)。
          仅 progress==0(全新辅种, 数据完整)可跳检; full-checking 对部分下载安全, 不设限。
        - 跨规则同日去重: 多条规则都配 checking 时, 同一种子当日只跳检一次(跳检必然清空
          本地统计, 重复跳检只会再丢一次而毫无收益); 顺带清理非当日记录(防 state 无界增长)。
        """
        progress = torrent.progress
        if 0.0 < progress < 1.0:
            return ActionResult.fail(f"部分下载的种子禁止跳检(progress={progress}), 请改用 full-checking")

        today = date.today().isoformat()
        skip_day = ctx.manager.state.setdefault("skip_check_day", {})
        if skip_day.get(ctx.hash) == today:
            return ActionResult.skip("今日已跳检过该种子(跨规则去重)")
        for h in [h for h, d in skip_day.items() if d != today]:
            del skip_day[h]
        return None

    def _skip_delete(self, ctx: RuleContext, torrent: TorrentRecord) -> Optional[ActionResult]:
        """跳检步骤: 删除种子(保留文件)并轮询确认已从客户端消失(qB 删除为异步)。

        返回 None = 已确认消失; ActionResult = 失败(种子未删除或消失未确认, 无损失,
        放弃跳检避免重加撞"种子已存在")。
        """
        try:
            logger.info(f"规则[{ctx.rule_name}] {torrent.log_repr} | 跳检删除种子(保留文件)")
            ctx.api.torrents_delete(torrent_hashes=ctx.hash, delete_files=False)
        except Exception as e:
            return ActionResult.fail(f"删除种子失败(未删除, 无损失): {e}")
        gone = _poll_until(lambda: not ctx.api.torrents_info(torrent_hashes=ctx.hash), attempts=10, interval=0.5)
        if not gone:
            return ActionResult.fail("删除后种子仍在客户端, 放弃跳检(重加会撞已存在的种子)")
        return None

    def _skip_readd(
        self, ctx: RuleContext, torrent: TorrentRecord, data: bytes, tor: TorrentDictionary,
        content_layout: Optional[str]
    ) -> Optional[ActionResult]:
        """跳检步骤: 以跳过校验方式重加(先暂停), 轮询确认出现, 恢复删除前快照记录。

        属性直传不用 `or None` —— ratio/seeding limit 的 0/负值是有语义的(不限速/跟随
        全局), 吞掉会使重加后行为漂移到 qB 新种缺省。重加成功后 store.restore_torrent
        恢复删除前记录(保留 tracker_conf/惰性缓存): remove_torrent 保留 _known_hashes,
        重加的同 hash 种子不进下轮 added 列表, 不恢复则永久未匹配(生产 BUG 2026-09-06)。

        返回 None = 成功; ActionResult = 失败(种子已从客户端移除, 已备份提示手动恢复)。
        """
        try:
            ctx.api.torrents_add(
                torrent_files=[data],
                save_path=torrent.save_path,
                category=torrent.category or None,
                tags=torrent.tags or None,
                upload_limit=torrent.up_limit,
                download_limit=torrent.dl_limit,
                is_sequential_download=tor.seq_dl,
                is_first_last_piece_priority=tor.f_l_piece_prio,
                contentLayout=content_layout,
                ratio_limit=tor.ratio_limit,
                seeding_time_limit=tor.seeding_time_limit,
                inactive_seeding_time_limit=tor.inactive_seeding_time_limit,
                share_limit_action=tor.share_limit_action,
                is_skip_checking=True,
                is_stopped=True,
            )
        except Exception as e:
            backup = self._backup_torrent(ctx.manager, torrent, data)
            return ActionResult.fail(f"重加种子失败: {e}; 种子已从客户端移除(文件保留), "
                                     f".torrent 已备份: {backup}, 请手动重加")
        appeared = _poll_until(lambda: ctx.api.torrents_info(torrent_hashes=ctx.hash), attempts=3, interval=0.3)
        if not appeared:
            return ActionResult.fail("重加后未确认到种子, 请检查客户端")
        ctx.manager.store.restore_torrent(torrent)
        # 跳检完成: 记录跨规则同日去重(此后同种子当日任何规则的 checking 都不再跳检)
        ctx.manager.state.setdefault("skip_check_day", {})[ctx.hash] = date.today().isoformat()
        return None

    def _infer_content_layout(self, torrent, client) -> Optional[str]:
        """推断原内容布局(qB 种子信息无直接字段): 重加后数据路径必须与现存文件一致,
        跳检状态下布局错位不会自愈(直接 missingFiles/空传)。无法推断返回 None(用 qB 默认)。

        须在删除种子前调用(传入删除前捕获的记录): 删除后 store 记录已移除, 且文件列表
        惰性缓存挂在记录上(空缓存时会向已删除的种子发请求)。

        - 文件路径均以 种子名/ 开头(.torrent 自带根目录): content==save -> NoSubfolder(原布局剥根),
          content==save/种子名 -> Original
        - 无根目录(含单文件): content==save -> Original; content==save/种子名 -> Original
        """
        save = utils.path_normalize(torrent.save_path)
        content = utils.path_normalize(torrent.content_path or "")
        if not content:
            return None
        name = utils.path_normalize(torrent.name)
        files = torrent.files(client)  # store 惰性缓存(filelist 前置检查已填充)
        has_root = bool(files) and all(utils.path_normalize(f.name).startswith(f"{name}/") for f in files)
        if content == save:
            return "NoSubfolder" if has_root else "Original"
        if content == f"{save}/{name}":
            return "Original"
        return None

    def _backup_torrent(self, manager, torrent, data: bytes) -> str:
        """重加失败时把 .torrent 落盘备份并记录元数据(便于手动恢复), 返回备份路径

        用删除前捕获的 torrent 记录(删除后 store 记录已移除, ctx.torrent 为 None)。
        元数据立即落盘(非常规路径, 不适用"仅退出时落盘"的写放大规避): 备份后程序一旦
        崩溃, 没有 state 里的元数据指引, 用户不知道 .torrent 备份的存在与原始保存路径。
        """
        backup_dir = os.path.join(os.path.dirname(manager.state_file) or ".", "skip-check-backup")
        os.makedirs(backup_dir, exist_ok=True)
        path = os.path.join(backup_dir, f"{torrent.hash}.torrent")
        with open(path, "wb") as f:
            f.write(data)
        backup_meta = manager.state.setdefault("skip_check_backup", {})
        backup_meta[torrent.hash] = {
            "path": path,
            "save_path": torrent.save_path,
            "category": torrent.category,
            "tags": torrent.tags,
            "ts": time.time(),
        }
        manager.save_state()
        return path
