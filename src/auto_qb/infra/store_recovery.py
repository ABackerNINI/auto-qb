"""「主文件读坏 -> 留证 -> .bak 兜底」恢复链的公共骨架(hr 站点文件与 state.json 共用)

两条恢复链同族同纪律(issue 26-10-11-0240-refactor-hr-store-recover-lock-family-dup):
  1. 主文件读坏**不先删也不先写**: 先把现场保住(hr 挪走留证 / state 原地保留), 再试
     `.bak` —— 顺序反了的话, 一旦备份也不可用, 下一步写盘就把坏文件覆盖掉, 现场永远看不到;
  2. `.bak` 可用 -> 采用备份内容 + 自愈写回; `.bak` 也不可用 -> 保守回落空状态并告警;
  3. 自愈写回**不带** keep_backup —— 否则唯一一份好备份会被坏内容盖掉, 这次恢复等于白做。

语义差异**保留在各调用方**(回调 + 不传即默认, 不合并):
  - hr: 坏文件挪到 `.bad-<ts>` 留证(传 quarantine=store.quarantine); 备份解析走 schema
    迁移链; 结论拼进 `read_error`(status.py 的「站点文件读坏不抛」契约); 版本回退即拒
    **不算**坏文件(不挪也不从备份猜);
  - state: 坏文件原地保留待查(**不传** quarantine); 未来版本 SchemaVersionError fail-fast
    放出去(不算损坏 —— 备份里也是同一个新版本, 回退没有意义); _CORRUPT 三态(None=首启 vs
    损坏)由 `_read_state_file` 自己区分; 自愈写回立即执行且失败只告警不阻断启动。

本模块只收**编排**(先留证后读备份)与**挪文件**两段确定性纪律; 日志/消息口径由调用方定
(hr 要防轰炸去重, state 要 WARNING/INFO/ERROR 分级), 自愈写回的时机与载荷也不同
(hr 随下次 commit、state 立即写回)。
"""
import logging
import os
import time
from dataclasses import dataclass
from typing import Any, Callable, Optional, Tuple

__all__ = ["BadFileRecovery", "quarantine_bad_file", "recover_corrupt_file"]


@dataclass(frozen=True)
class BadFileRecovery:
    """recover_corrupt_file 的结论: 调用方据此写自己的消息/日志/自愈动作"""
    recovered: bool  #: 备份是否可用
    data: Any = None  #: 备份内容(recovered=True; 否则 None)
    backup_reason: str = ""  #: 备份不可用原因(recovered=False; 调用方决定是否引用)
    moved_to: str = ""  #: 坏文件被挪到的新路径(未挪/挪不动均为空串)
    move_failed: bool = False  #: 想挪但没挪成(未传 quarantine 口径下恒 False)


def quarantine_bad_file(path: str, *, logger: logging.Logger, what: str) -> str:
    """把坏文件挪到 `<path>.bad-<ts>`(**保留现场**, 不让下一次写盘把它覆盖掉)

    返回新路径; 文件不存在(无处可挪)或挪不动(被其它程序占用)返回空串 —— 调用方须知悉:
    没挪走意味着坏文件还压在目标路径上, 后续写盘会覆盖它(hr 据此把 keep_backup 置 False,
    见 HrSiteStore._write 的注释)。
    """
    p = str(path)
    if not os.path.exists(p):
        return ""
    target = f"{p}.bad-{int(time.time())}"
    try:
        os.replace(p, target)
    except OSError as e:
        logger.debug(f"{what} | 坏文件挪走失败(继续运行): {e}")
        return ""
    return target


def recover_corrupt_file(
    *,
    read_backup: Callable[[], Tuple[Any, str]],
    quarantine: Optional[Callable[[], str]] = None,
    logger: logging.Logger,
    what: str,
) -> BadFileRecovery:
    """读坏后的公共链: 先按调用方口径处置坏文件(不传 quarantine = 原地保留) -> 读 `.bak` -> 返回结论

    `read_backup` 契约与 hr `HrSiteStore.read_backup` 同形状: `() -> (数据, 不可用原因)`,
    原因为 None 即"可用" —— 两侧解析口径(迁移链 / _CORRUPT 三态)的差异封在各自回调里。
    `quarantine` = 坏文件处置回调 `() -> 新路径或空串`: hr 传 `store.quarantine`(其内部走
    本模块 `quarantine_bad_file` 单点); **不传 = 原地保留**(state.json 口径: 损坏文件原样
    保留待查, 不删除)。

    只编排 + 挪文件, **不写日志、不自愈**: WARNING/ERROR 由调用方按自身口径报(hr 有防轰炸
    去重, state 有分级), 自愈写回的时机与载荷两侧不同(hr 随下次 commit、state 立即写回)。
    """
    moved_to = quarantine() if quarantine is not None else ""
    data, reason = read_backup()
    if reason is None:
        return BadFileRecovery(
            recovered=True, data=data, moved_to=moved_to, move_failed=bool(quarantine) and not moved_to
        )
    return BadFileRecovery(
        recovered=False, backup_reason=reason, moved_to=moved_to, move_failed=bool(quarantine) and not moved_to
    )
