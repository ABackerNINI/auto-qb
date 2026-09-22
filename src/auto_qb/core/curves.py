"""Traffic Monitor 流量数据处理与全局限速曲线计算(纯逻辑, 无项目内依赖, 便于单测)

数据源格式(history_traffic.dat):
    lines: "30"                      # 首行为行数说明, 跳过
    2026/09/04 64033621/104743685    # 每行: 日期 上传KB/下载KB(单位 KB, ×1024 转字节)
    2026/09/03 23295975/37857445
    ...
行序任意(样例为日期倒序); 每行是"某日已累计上传/下载量"(当天行随流量增长, 跨天重置)。

累计口径(period, 由 normalize_period 归一化):
    day    当天累计: 取日期 == today 的行(今天行缺失视为 0 -> 自动回落放宽)
    month  当月累计: 同年月所有行求和(缺某日不影响)
    Nd     最近 N 个自然日滚动累计: [today-N+1, today] 窗口内的行求和(窗口内缺失日期视为 0)

档位语义(全程分档覆盖, 方案B): 阈值升序 (t1,v1)..(tn,vn), 累计量 X:
    X < t1              -> v1   (首档覆盖低端区间, "低于指定值也按首档限速")
    t_{j-1} <= X < t_j  -> v_j  (尚未达到本档阈值前, 一直用本档速度限制)
    X >= tn             -> vn   (末档延续, 不再降速)
等价实现: 返回第一个 threshold > X 的档位速度; 不存在(超过末档)则返回末档速度。
档位速度 0 = 该档不限速(仅用于某档显式放开)。
"""
import re
from datetime import date, timedelta
from typing import List, Optional, Tuple

# dat 数值单位: KB, 按 1024 字节换算(与用户确认)
KB = 1024

# 历史行记录: (日期, 上传字节, 下载字节)
HistoryRow = Tuple[date, int, int]


def normalize_period(value) -> str:
    """period 配置归一化: day/1D/D -> "day"; month -> "month"; ND(N>=1) -> "ND"。非法抛 ValueError"""
    s = str(value).strip().upper()
    if s in ("DAY", "D", "1D"):
        return "day"
    if s == "MONTH":
        return "month"
    m = re.fullmatch(r"(\d+)D", s)
    if m and int(m.group(1)) >= 1:
        return f"{int(m.group(1))}D"
    raise ValueError(f"无效 period(支持: day/1D, month, ND 如 7D): {value}")


# TODO: Traffic Monitor的history_traffic.dat目前是每天一行倒序排列, 可以只读取 N 行, 比如31+5行
# TODO: 或者第一次读取N行, 剩下的只读取2行(除首行), 更新今天和昨天的数值就可以了
def parse_history_dat(text: str, scale: int = KB) -> Tuple[List[HistoryRow], int]:
    """解析 history_traffic.dat 文本 -> (行记录列表按日期升序, 坏行数)

    - 首行(lines: "N")与空行忽略
    - 坏行(格式不匹配/非法日期)跳过并计数
    - 重复日期取最后一行
    - 数值单位 KB, × scale 转字节
    """
    rows_by_date: dict = {}
    bad = 0
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.lower().startswith("lines:"):
            continue
        m = re.fullmatch(r"(\d{4})/(\d{1,2})/(\d{1,2})\s+(\d+)/(\d+)", line)
        if not m:
            bad += 1
            continue
        y, mo, d, up, down = m.groups()
        try:
            day = date(int(y), int(mo), int(d))
        except ValueError:  # 非法日期, 如 2026/13/40
            bad += 1
            continue
        rows_by_date[day] = (int(up) * scale, int(down) * scale)
    return [(d, up, down) for d, (up, down) in sorted(rows_by_date.items())], bad


def aggregate(rows: List[HistoryRow], period: str, today: date = None) -> Tuple[int, int]:
    """按 period 聚合历史行 -> (上传字节, 下载字节)

    today 可注入(测试); 窗口内缺失日期视为 0(不贡献流量)。
    """
    today = date.today() if today is None else today
    if period == "day":
        selected = [r for r in rows if r[0] == today]
    elif period == "month":
        selected = [r for r in rows if (r[0].year, r[0].month) == (today.year, today.month)]
    else:  # Nd: 最近 N 个自然日
        n = int(period[:-1])
        start = today - timedelta(days=n - 1)
        selected = [r for r in rows if start <= r[0] <= today]
    up = sum(r[1] for r in selected)
    down = sum(r[2] for r in selected)
    return up, down


def curve_speed(x_bytes: int, points) -> int:
    """全程分档覆盖(方案B): 累计量 x_bytes -> 档位限速(字节/秒, 0 = 不限速)

    points: 按阈值升序的档位序列, 每个元素需有 threshold_bytes / speed_bytes_per_s
    (鸭子类型, 接受 config.CurvePoint, 避免模块间依赖)。
    """
    for p in points:
        if x_bytes < p.threshold_bytes:
            return p.speed_bytes_per_s
    return points[-1].speed_bytes_per_s


def merge_direction(speeds: List[int]) -> Optional[int]:
    """同方向多条 period 曲线的档速(字节/秒)合并 -> 该方向最终限速

    - 取最小非零值 = 最严约束(各口径曲线都要满足)
    - 全为 0(所有曲线该方向均不限速) -> 0
    - 空列表(该方向无任何曲线) -> None(该方向不管理)
    """
    if not speeds:
        return None
    nonzero = [s for s in speeds if s > 0]
    return min(nonzero) if nonzero else 0


def bytes_to_kib(v_bps: int) -> int:
    """字节/秒 -> KiB/s(qB 全局速度整数单位; 半值向上取整 = 略严; 0/负数归 0)"""
    if v_bps <= 0:
        return 0
    return int(v_bps / 1024 + 0.5)
