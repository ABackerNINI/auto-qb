"""relocate 共用叶: logger / 常量 / 模块级 helper(自 relocate_mod move-only 切出)

拆分(R5)只搬位置: 区段文本与 relocate_mod.py 原文件逐字一致, 仅 logger 名显式沿用原模块名。
"""
import logging
import os
from typing import Any, Iterable, Optional, Set, Tuple

from ...infra import utils
from ...infra.file_access import FileAccess

logger = logging.getLogger("auto_qb.core.modules.relocate_mod")

# qB 未完成文件的孪生后缀(单点 utils.QB_INCOMPLETE_SUFFIX / qb_incomplete_twin_path;
# 组内出现即判「数据未落定」, §3.1 拒绝行)
_QB_TEMP_SUFFIX = utils.QB_INCOMPLETE_SUFFIX

# 每 tick 建链接的条数上限(单步有界: 主循环零阻塞, 验收判据「单步 < 50ms」)
_LINK_CHUNK = 200


def _native(path: str, rel: str) -> str:
    """save_path + qB 相对路径(正斜杠) -> 本机路径(只拼接, 不触盘)"""
    parts = [p for p in str(rel).replace("\\", "/").split("/") if p]
    return os.path.join(path, *parts) if parts else path


def _top_children(files: Iterable[Tuple[str, int]]) -> Set[str]:
    """组文件在内容根下的直接子级名集合(用于目录 listing 的归属分类)"""
    out = set()
    for name, _size in files:
        parts = [p for p in str(name).replace("\\", "/").split("/") if p]
        if len(parts) > 1:
            out.add(parts[1])
        else:
            out.add(parts[0])
    return out


def _volume_free_resolved(fa: FileAccess, target: str) -> Optional[int]:
    """目标卷剩余(字节): 叶子目录未创建时上溯最近存在祖先(plan 26-11-02-0134 R1 方案A)

    shutil.disk_usage 要求路径已存在 —— 目标目录尚未创建是迁移的正常输入(qB 落地时
    libtorrent create_directories), 卷剩余对「将要新建的目录」是确定事实; junction /
    卷挂载点之下新建目录物理落在「最近存在祖先」所在卷, 语义正确。逐级上溯第一个
    可用层取 disk_usage; 上溯到根仍不可用(盘不存在/未就绪/UNC 不可达) => None,
    交 GATE_SPACE 照旧硬拦(真不可判定, 保守默认不破)。
    """
    cur = str(target or "").strip().replace("\\", "/")
    for _ in range(64):  # 层数上限: 防御病态超长/环状路径, 远超现实深度
        if not cur:
            return None
        try:
            return fa.disk_usage(cur).free
        except Exception:  # noqa: BLE001 - 本层不可用(不存在/盘未就绪/不可达): 上溯
            pass
        parent = os.path.dirname(cur)
        if parent == cur:
            return None  # 卷根已失败 => 整卷不可判定
        cur = parent
    return None


def _same_volume_resolved(alias_fs_mod: Any, sys_src: str, sys_target: str) -> Optional[bool]:
    """同卷判定: 目标叶子未创建时上溯最近存在祖先比 st_dev(plan 26-11-02-0134 R1 方案A 同一机制)

    alias_fs.same_volume 用 os.stat 取 st_dev, 叶子不存在 => None => 按跨卷保守处理,
    文件链接形态会被降级/拒绝 —— 新建目录物理落在最近存在祖先所在卷, 与
    _volume_free_resolved 同一语义。源侧可读, 故 None 只会来自目标层不可读:
    逐层上溯第一个可读层即得判定; 全链不可读 => None(真不可判定)。
    """
    cur = str(sys_target or "").strip().replace("\\", "/")
    for _ in range(64):
        if not cur:
            return None
        verdict = alias_fs_mod.same_volume(sys_src, cur)
        if verdict is not None:
            return verdict
        parent = os.path.dirname(cur)
        if parent == cur:
            return None
        cur = parent
    return None
