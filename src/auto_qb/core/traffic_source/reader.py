"""取数读取与失败判定的**单点**(计划 26-10-18-0813 A2/A4).

为什么在这里而不是某个模块里: 快照的所有权移交 `traffic_snapshot` 之后, **两个**模块都要读同一份
dat —— 来源模块发布历史/累计(快照), 曲线模块按曲线聚合查档(限速)。模块之间不许互相 import
(见 core/module.py 契约), 于是「怎么读、读到什么算失败」必须落在共享的 core 层单点; 谁读谁调,
判据不许各实现一遍(同族先例 pitfalls/backend/verdict-scope-parity.md)。

失败形状(调用方各自决定怎么用):
    {"code": stale 快照 reasons.code, "text": 快照文案, "log": 日志文案}
- 来源模块: 落 `source.state="stale"` + `source.reasons`
- 曲线模块: 落 `limit.state="stale"` + 一条 WARNING

边界: 本模块只管「读文件 + 解析 + 判定」, 不发布、不聚合、不碰 qB。
"""
from typing import List, Optional, Tuple

from .. import curves

#: 读不到文件 / 解析不出行时的原因码(快照 reasons.code 的契约面, 前端按码分流文案)
CODE_DAT_MISSING = "dat_missing"
CODE_DAT_EMPTY = "dat_empty"


def read_source_rows(dat_path: str) -> Tuple[List[curves.HistoryRow], int, Optional[dict]]:
    """读流量数据源(dat, 路径由调用方从 core.traffic_source.paths.dat_path() 取) ->
    (按日行, 无法解析行数, 失败 | None)

    失败判据只有两条: 读不到文件(OSError) / 有文件但无有效记录。两条都**不抛异常** ——
    调用方在数据不可用时一律「保留上一轮生效值 + 显式报不可用」, 不是崩溃退出。
    """
    try:
        with open(dat_path, "r", encoding="utf-8", errors="ignore") as f:
            text = f.read()
    except OSError as e:
        return [], 0, {
            "code": CODE_DAT_MISSING,
            "text": f"流量数据读取失败: {e}",
            "log": f"读取流量数据失败({dat_path}): {e}",
        }
    rows, bad = curves.parse_history_dat(text)
    if not rows:
        return [], bad, {
            "code": CODE_DAT_EMPTY,
            "text": "流量数据无有效记录",
            "log": f"流量数据无有效记录({dat_path})",
        }
    return rows, bad, None


__all__ = ["CODE_DAT_EMPTY", "CODE_DAT_MISSING", "read_source_rows"]
