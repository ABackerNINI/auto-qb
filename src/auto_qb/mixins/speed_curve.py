"""全局限速曲线 mixin: Traffic Monitor 流量数据 -> qB 全局速度限制

由 QbManager 组合。对应 config.global_speed_limit_curve(缺省 None = 不启用), 作为
global 任务按 config.interval 周期执行: 读取 history_traffic.dat, 按每条 period 曲线
聚合当前累计上传/下载量, 查档得到该方向限速(方案B 全程分档覆盖), 同方向多条曲线
取最严(最小非零)速度, 有变化时经 QbApi.set_global_speed_limits 写 qB 全局偏好。

规则:
- 档位速度 0 = 不限速; 目标与当前均为 0 时幂等不写
- 不覆盖用户手动全局限速: 当前值为正奇数 KiB(如 2001KiB/s)时跳过该方向
  (每轮重读当前值, 手动取消后自动恢复接管)
- 数据源文件缺失/整体无法解析 -> warning, 本轮不动限速(任务保留);
  dat 有行但当前 period 窗口内无数据(如今天行尚未写入) -> 累计视为 0, 自动回落放宽
- dry_run: 只计算并输出日志, 不读当前、不写 qB
"""
import logging
from datetime import date
from typing import List, Optional

from ..config import GlobalSpeedLimitCurve
from .. import curves
from ..taskqueue import Task

logger = logging.getLogger(__name__)


def _fmt_global_limit(kib: Optional[int]) -> str:
    """显示用: KiB/s -> 可读字符串(0/None = 不限速)"""
    if not kib:
        return "不限速"
    return f"{kib}KiB/s"


class SpeedCurveMixin:
    """全局限速曲线(全局任务): Traffic Monitor 数据 -> qB 全局速度限制"""
    def _speed_curve_conf(self) -> Optional[GlobalSpeedLimitCurve]:
        """曲线配置(测试用 FakeConfig 无该字段, getattr 兜底)"""
        return getattr(self.config, "global_speed_limit_curve", None)

    def _handle_speed_limit_curve(self, task: Task, dry_run: bool) -> bool:
        """全局任务: 读 TM dat -> 逐曲线聚合查档 -> 同方向取最严 -> 写 qB 全局限速"""
        conf = self._speed_curve_conf()
        if conf is None:
            return True

        # 1. 读取数据源
        try:
            with open(conf.bat_path, "r", encoding="utf-8", errors="ignore") as f:
                text = f.read()
        except OSError as e:
            logger.warning(f"读取流量数据失败({conf.bat_path}): {e}, 本轮不动")
            return True
        rows, bad = curves.parse_history_dat(text)
        if not rows:
            logger.warning(f"流量数据无有效记录({conf.bat_path}), 本轮不动")
            return True
        if bad:
            logger.warning(f"流量数据 {bad} 行无法解析已跳过({conf.bat_path})")

        # 2. 逐曲线聚合 + 查档(累计字节 -> 该方向档位限速)
        today = date.today()
        up_speeds: List[int] = []
        down_speeds: List[int] = []
        for pc in conf.curves:
            up_bytes, down_bytes = curves.aggregate(rows, pc.period, today)
            if pc.upload_points:
                up_speeds.append(curves.curve_speed(up_bytes, pc.upload_points))
            if pc.download_points:
                down_speeds.append(curves.curve_speed(down_bytes, pc.download_points))
        # 3. 同方向合并(取最严)并转 qB 单位(KiB/s)
        upload_kib = curves.bytes_to_kib(curves.merge_direction(up_speeds)) if up_speeds else None
        download_kib = curves.bytes_to_kib(curves.merge_direction(down_speeds)) if down_speeds else None
        logger.info(
            f"全局限速曲线: 今日累计上传/下载换算后 -> 上传限速 {_fmt_global_limit(upload_kib)}, "
            f"下载限速 {_fmt_global_limit(download_kib)}"
        )

        if dry_run:
            self._record_curve_state(today, upload_kib, download_kib, dry_run=True)
            return True

        # 4. 读当前全局限速 -> 手动保护/幂等 -> 有变化才写
        current = self.api.get_global_speed_limits()
        apply_kwargs = {}
        for label, cur_key, kib in (
            ("上传", "upload_limit", upload_kib),
            ("下载", "download_limit", download_kib),
        ):
            if kib is None:
                continue  # 该方向无曲线, 不管理
            cur = current[cur_key]
            if cur > 0 and cur % 2 == 1:
                logger.info(f"全局限速曲线: {label}限速当前 {cur}KiB/s 为奇数, 疑似用户手动设置, 本轮不覆盖")
                continue
            if cur == kib:
                continue  # 幂等: 目标 == 当前(含均不限速), 不写
            apply_kwargs["upload_kib" if cur_key == "upload_limit" else "download_kib"] = kib
        if apply_kwargs:
            self.api.set_global_speed_limits(**apply_kwargs)
            applied = ", ".join(
                f"{'上传' if k == 'upload_kib' else '下载'}限速 {_fmt_global_limit(v)}" for k, v in apply_kwargs.items()
            )
            logger.info(f"设置全局限速曲线: {applied}")

        self._record_curve_state(today, upload_kib, download_kib, dry_run=False)
        return True

    def _record_curve_state(self, today: date, upload_kib: Optional[int], download_kib: Optional[int], dry_run: bool):
        """记录当日曲线计算结果到 state(供调试; 落盘由程序退出时统一 save_state)"""
        self.state.setdefault("speed_limit_curve", {})[today.isoformat()] = {
            "upload_kib": upload_kib,
            "download_kib": download_kib,
            "dry_run": dry_run,
        }
