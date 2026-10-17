"""SpeedCurveModule: 全局限速曲线的模块化封装(plan kernel-module-refactor P3)

流量数据源(见 config.traffic_source) -> qB 全局速度限制, 知识从 SpeedCurveMixin 整体迁入:
- 曲线任务**自注册**(plan §3.2): start 时入队, 队列重建(L2 热重载)经 queue_rebuilt
  相位重新入队 —— 内核的 _create_global_tasks 不再点名业务任务;
- 流量快照改经 ctx.web.set_traffic_view **服务方法**推送(plan §5), 不再跨层直写
  _traffic_view 字段 —— 外围绕过边界直写私有面清零(与 P1 托盘改 ctx.notify 同口径);
- 手动保护的日志节流状态(_curve_manual_log)收进模块实例, 内核不再代持。

对应 config.global_speed_limit_curve(缺省 None 或 enabled: false = 不启用), 作为全局
任务按 config.interval 周期执行: 经 `core.traffic_source.paths.dat_path()` 取当前生效来源的
dat(工具来源是运行期事实, 不在配置里), 按每条 period 曲线聚合当前
累计上传/下载量, 查档得到该方向限速(方案B 全程分档覆盖), 同方向多条曲线取最严(最小
非零)速度, 有变化时经 QbApi.set_global_speed_limits 写 qB 全局偏好。

规则:
- 档位速度 0 = 不限速; 目标与当前均为 0 时幂等不写
- 不覆盖用户手动全局限速: 当前值为正奇数 KiB(如 2001KiB/s)时跳过该方向
  (每轮重读当前值, 手动取消后自动恢复接管)
- 手动保护的**日志节流**: 手动值是持续状态(用户不改就一直命中), 故进入该状态(或手动值变了)
  记一条 INFO, 之后同一状态每 `_MANUAL_REMIND_GAP` 才再提醒一次, 被去重的轮次降 DEBUG ——
  逐轮 INFO 会刷屏(判据见 pitfalls/ops/alert-levels.md 2.4.); 可见性另由 Web UI 的
  `reasons`(code=manual)承载, 不依赖这行日志
- 数据源文件缺失/整体无法解析 -> warning, 本轮不动限速(任务保留);
  dat 有行但当前 period 窗口内无数据(如今天行尚未写入) -> 累计视为 0, 自动回落放宽
- dry_run: 只计算并输出日志, 不读当前、不写 qB
- 监视器通知(S7): `refresh_traffic_view` 只重读数据源并重发快照(历史行 + 各曲线累计),
  不查档、不写限速 —— 「刷新图」是通知链路的唯一联动动作(黄金法则 2)
"""
import logging
import time
from datetime import date
from typing import List, Optional, Tuple

from ...infra import utils
from .. import curves
from ..module import AppContext, BaseModule
from ..state import prune_day_keys
from ..taskqueue import REQUEUE, Task
from ..traffic_source import paths as traffic_paths

logger = logging.getLogger(__name__)

_CN_DIGITS = "零一二三四五六七八九"

#: 手动保护命中的**周期提醒**间隔(秒): 同一状态在此期间只说明白一次, 其余轮次降 DEBUG。
#: 固定常量而非配置键 —— 这是日志节流, 不是行为开关(判据见 pitfalls/ops/alert-levels.md 4.)。
_MANUAL_REMIND_GAP = 3600.0

#: speed_limit_curve 日键的保留天数(issue A-03: 每天新增一日键、从不清 -> state 缓慢无界增长):
#: 该键仅供调试观察, 全仓无正确性消费方, 保 7 天足够; 固定常量而非配置键 —— 数据保留期
#: 不是行为开关, 不值得为它开配置面。
_CURVE_STATE_KEEP_DAYS = 7


def _fmt_bytes(n: int) -> str:
    """字节数 -> 可读字符串(如 60GiB / 1.5GiB)"""
    for unit, div in (("TiB", 1024**4), ("GiB", 1024**3), ("MiB", 1024**2), ("KiB", 1024)):
        if n >= div:
            return f"{n / div:.2f}".rstrip("0").rstrip(".") + unit
    return f"{n}B"


def _cn_number(n: int) -> str:
    """整数(0-99) -> 中文数字: 7->七, 30->三十"""
    if n <= 9:
        return _CN_DIGITS[n]
    tens, ones = divmod(n, 10)
    s = _CN_DIGITS[tens] + "十"
    return s + (_CN_DIGITS[ones] if ones else "")


def _period_label(period: str) -> str:
    """归一化 period -> 日志中文标签: day->今日, month->本月, 7D->七日"""
    if period == "day":
        return "今日"
    if period == "month":
        return "本月"
    n = int(period[:-1])  # "ND" -> N
    return f"{_cn_number(n) if n < 100 else n}日"


def _fmt_global_limit(kib: Optional[int]) -> str:
    """显示用: KiB/s -> 可读字符串(0/None = 不限速)"""
    if not kib:
        return "不限速"
    return f"{kib}KiB/s"


def _history_rows(rows: List[Tuple[date, int, int]]) -> List[dict]:
    """dat 行 -> 历史流量快照行(按日升序): Web UI 历史流量图的数据源

    随快照发布, Web 端经 /api/traffic/history 读取(不进轮询响应, 避免每轮回传几百行)。
    """
    return [{"date": d.isoformat(), "up": up, "down": down} for d, up, down in rows]


def _period_rows(period_stats: List[Tuple[str, int, int]]) -> List[dict]:
    """各曲线周期累计 -> 快照 periods 行(顶栏「今日流量」pill 的数据源, period == "day")"""
    return [
        {
            "period": period,
            "label": _period_label(period),
            "up": up,
            "down": down
        } for period, up, down in period_stats
    ]


def _read_source_rows(dat_path: str) -> Tuple[List[Tuple[date, int, int]], int, Optional[dict]]:
    """读流量数据源(dat, 路径由调用方从 core.traffic_source.paths.dat_path() 取) ->
    (按日行, 无法解析行数, 失败 | None)

    读法与失败判据的**单点**(任务轮与监视器通知刷新轮共用 —— 同一条判据不许两处各实现一遍,
    见 pitfalls/backend/verdict-scope-parity.md)。失败形状:
      {"code": stale 快照的 reasons.code, "text": 快照文案, "log": 日志文案}
    调用方各自决定怎么用: 任务轮落 `stale` 快照, 通知刷新轮只记一条日志(不发布)。
    """
    try:
        with open(dat_path, "r", encoding="utf-8", errors="ignore") as f:
            text = f.read()
    except OSError as e:
        return [], 0, {
            "code": "dat_missing",
            "text": f"流量数据读取失败: {e}",
            "log": f"读取流量数据失败({dat_path}): {e}",
        }
    rows, bad = curves.parse_history_dat(text)
    if not rows:
        return [], bad, {
            "code": "dat_empty",
            "text": "流量数据无有效记录",
            "log": f"流量数据无有效记录({dat_path})",
        }
    return rows, bad, None


class SpeedCurveModule(BaseModule):
    """speed_curve 模块: 曲线任务自注册 + 流量快照经 ctx.web 服务方法推送"""

    name = "speed_curve"

    def __init__(self, ctx: AppContext) -> None:
        self._ctx = ctx
        # 手动保护日志节流: {方向: (手动值 KiB/s, 上次记 INFO 时刻)} —— 模块实例自持
        # (手动值是持续状态, 状态变化才报 + 周期提醒; 退出手动保护时清键, 见 _log_manual_skip)
        self._curve_manual_log: dict = {}

    def sections(self) -> tuple[str, ...]:
        # 消费两个配置段: 曲线本体 + 顶层数据源(计划 26-10-17-0339 S15, dat 路径取自 traffic_source)
        return ("global_speed_limit_curve", "traffic_source")

    # ---------- 生命周期 ----------

    def start(self, ctx: AppContext, dry_run: bool) -> None:
        # 曲线任务自注册(plan §3.2): dry_run 不影响注册(任务 handler 自带 dry_run 口径,
        # 原 _create_global_tasks 也不判 dry_run); 未配置 = 无操作
        self._register_global_task(ctx)

    # ---------- 相位订阅 ----------

    def subscribe(self, phases) -> None:
        phases.on("queue_rebuilt", self._on_queue_rebuilt)

    def _on_queue_rebuilt(self, event) -> None:
        """L2 热重载整体重建队列后重新入队(新 interval/新配置; 已注册则幂等跳过)"""
        self._register_global_task(self._ctx)

    def _register_global_task(self, ctx: AppContext) -> None:
        """曲线任务自注册(骨架走 BaseModule.register_global_tasks 单点): 未启用判定
        在调用方(配置形状各模块不同); 缺省 interval 回退主 interval。"""
        gslc = ctx.config.global_speed_limit_curve
        if gslc is None:  # 未启用该功能: 不建任务(与原 _create_global_tasks 同判据)
            return
        self.register_global_tasks(
            ctx,
            [("speed_limit_curve", self.handle_speed_limit_curve, gslc.interval or ctx.config.interval)],
        )

    # ---------- 全局任务执行体 ----------

    def handle_speed_limit_curve(self, task: Task, dry_run: bool) -> bool:
        """全局任务: 读 TM dat -> 逐曲线聚合查档 -> 同方向取最严 -> 写 qB 全局限速"""
        # 数据来源总开关(S1/D1, 26-10-17-1737): 判定优先于 disabled —— 关源时曲线功能本身
        # 可能仍启用, 但取数已停; 快照发 off(前端灰显"来源已关闭"), 不读数据不动 qB
        if not traffic_paths.source_enabled(self._ctx.config):
            self._publish_traffic("off")
            return REQUEUE
        conf = self._ctx.config.global_speed_limit_curve
        if conf is None:  # 未启用该功能
            self._publish_traffic("disabled")
            return REQUEUE
        if not conf.enabled:  # 显式停用(enabled: false): 功能整体关闭, 不读数据不动 qB
            self._publish_traffic("disabled")
            return REQUEUE

        # 1. 读取数据源(路径走取数单点 traffic_source.paths.dat_path: 工具来源是运行期事实,
        #    不在配置里; 读法与失败判据单点在 _read_source_rows)
        dat_path = traffic_paths.dat_path(self._ctx.config)
        rows, bad, fail = _read_source_rows(dat_path)
        if fail is not None:
            logger.warning(f"限速曲线 | {fail['log']}, 本轮不动")
            self._publish_traffic("stale", reasons=[{"dir": "", "code": fail["code"], "text": fail["text"]}])
            return REQUEUE
        if bad:
            logger.warning(f"限速曲线 | 流量数据 {bad} 行无法解析已跳过({dat_path})")
        history = _history_rows(rows)

        # 2. 逐曲线聚合 + 查档(累计字节 -> 该方向档位限速); 各 period 聚合值保留供统计日志
        today = date.today()
        up_speeds: List[int] = []
        down_speeds: List[int] = []
        period_stats: List[Tuple[str, int, int]] = []  # (归一化 period, 上传字节, 下载字节)
        for pc in conf.curves:
            up_bytes, down_bytes = curves.aggregate(rows, pc.period, today)
            period_stats.append((pc.period, up_bytes, down_bytes))
            if pc.upload_points:
                up_speeds.append(curves.curve_speed(up_bytes, pc.upload_points))
            if pc.download_points:
                down_speeds.append(curves.curve_speed(down_bytes, pc.download_points))
        # 3. 同方向合并(取最严)并转 qB 单位(KiB/s)
        upload_kib = curves.bytes_to_kib(curves.merge_direction(up_speeds)) if up_speeds else None
        download_kib = curves.bytes_to_kib(curves.merge_direction(down_speeds)) if down_speeds else None
        # 各周期累计流量(Web 顶栏展示“今日上传/下载”的数据源)
        periods = _period_rows(period_stats)
        target = {"up": upload_kib, "down": download_kib}

        if dry_run:
            self._record_curve_state(today, upload_kib, download_kib, dry_run=True)
            self._publish_traffic("dry_run", periods=periods, target=target, history=history)
            return REQUEUE

        # 4. 读当前全局限速 -> 手动保护/幂等 -> 有变化才写
        current = self._ctx.api.get_global_speed_limits()
        apply_kwargs = {}
        reasons: List[dict] = []
        for label, cur_key, dir_key, kib in (
            ("上传", "upload_limit", "up", upload_kib),
            ("下载", "download_limit", "down", download_kib),
        ):
            if kib is None:
                continue  # 该方向无曲线, 不管理
            cur = current[cur_key]
            if utils.is_manual_speed_limit(cur * 1024):  # 奇数 KiB: 疑似用户手动设置
                self._log_manual_skip(dir_key, label, cur)
                reasons.append(
                    {
                        "dir": dir_key,
                        "code": "manual",
                        "text": f"{label}限速 {cur}KiB/s 为奇数(疑似手动设置), 本轮不覆盖",
                    }
                )
                continue
            # 已退出手动保护(用户取消 / 改成偶数): 忘掉节流记忆 —— 下次再进入要重新说明白
            self._curve_manual_log.pop(dir_key, None)
            if cur == kib:
                continue  # 幂等: 目标 == 当前(含均不限速), 不写
            apply_kwargs["upload_kib" if cur_key == "upload_limit" else "download_kib"] = kib
        if apply_kwargs:
            self._ctx.api.set_global_speed_limits(**apply_kwargs)
            applied = ", ".join(
                f"{'上传' if k == 'upload_kib' else '下载'}限速: {_fmt_global_limit(v)}" for k, v in apply_kwargs.items()
            )
            # 成功设置全局限速时, 按配置中各 period 曲线输出对应累计上传/下载(如 今日/七日/本月)
            stats = " ".join(
                f"{_period_label(period)}: {_fmt_bytes(up)}/{_fmt_bytes(down)}" for period, up, down in period_stats
            )
            logger.info(f"限速曲线 | 累计上传/下载 {stats}")
            logger.info(f"限速曲线 | 设置全局限速: {applied}")

        # 回读实际生效值(展示用): 写成功后 qB 侧应等于目标; 回读失败不影响已写入的限速,
        # 仅把 actual 退化为写前读数并附原因(展示层降级, 不掩盖写操作结果)
        actual = dict(current)
        if apply_kwargs:
            try:
                actual = self._ctx.api.get_global_speed_limits()
            except Exception as e:
                logger.warning(f"限速曲线 | 回读全局限速失败: {e}")
                reasons.append({"dir": "", "code": "read_failed", "text": f"回读实际限速失败: {e}"})

        self._record_curve_state(today, upload_kib, download_kib, dry_run=False)
        self._publish_traffic(
            "ok",
            periods=periods,
            target=target,
            actual={
                "up": actual["upload_limit"],
                "down": actual["download_limit"]
            },
            reasons=reasons,
            history=history,
        )
        return REQUEUE

    def refresh_traffic_view(self) -> bool:
        """重读数据源并重发限速/流量快照(**只读**: 不读不写 qB 限速; 计划 26-10-16-0541 S7)

        监视器通知到达时由 WEB 命令触发(主循环线程执行, 黄金法则 5), 把「盘上已经变了的数据」
        重新读一遍并发出去: 历史行 + 各曲线 period 累计**重算**, 其余字段(state / limit /
        target / actual / reasons)沿用上一次发布的快照 —— 本次不重新查档、不覆盖手动限速、
        不改任何限速决策(§07 黄金法则 2: 联动动作仅「刷新图」)。

        跳过(返回 False, 不发布)两种情形都只记一条 INFO, 路径人是排障而不是告警:
        - 段缺失 / enabled=false —— 保守默认: `disabled` 快照的语义是「不渲染流量/限速 pill」,
          不得被通知面绕过(曲线关了就不该因为监视器通知而冒出一个今日流量 pill);
        - 数据源不可用(缺文件 / 无有效行) —— 没有新数据可发。

        数据来源总开关关闭(S1/D1): 不跳过而是**发布 off 快照** —— 通知到达时来源已关,
        上一份快照可能还是 ok(旧数据), 必须显式翻成 off(前端据此灰显), 与曲线任务口径一致。
        """
        if not traffic_paths.source_enabled(self._ctx.config):
            logger.info("限速曲线 | 监视器通知刷新: 流量来源已关闭(traffic_source.enabled=false), 发布 off 快照")
            self._publish_traffic("off")
            return False
        conf = self._ctx.config.global_speed_limit_curve
        if conf is None or not conf.enabled:
            logger.info("限速曲线 | 监视器通知刷新跳过: 限速曲线未启用(快照保持 disabled)")
            return False
        dat_path = traffic_paths.dat_path(self._ctx.config)
        rows, bad, fail = _read_source_rows(dat_path)
        if fail is not None:
            logger.info(f"限速曲线 | 监视器通知刷新跳过: {fail['log']}")
            return False
        if bad:
            logger.warning(f"限速曲线 | 流量数据 {bad} 行无法解析已跳过({dat_path})")
        today = date.today()
        period_stats = [(pc.period, *curves.aggregate(rows, pc.period, today)) for pc in conf.curves]
        history = _history_rows(rows)
        # 整体替换引用(Web 线程只读单引用无锁): 从上一份快照复制后改三键, 保留 state / limit
        view = dict(self._ctx.web.traffic_view)
        view["periods"] = _period_rows(period_stats)
        view["history"] = history
        view["ts"] = time.time()
        view["date"] = today.isoformat()
        self._ctx.web.set_traffic_view(view)
        day = next((r for r in history if r["date"] == today.isoformat()), None)
        logger.info(
            f"限速曲线 | 监视器通知刷新历史流量: {len(history)} 行" +
            (f", 今日 上传 {_fmt_bytes(day['up'])}/下载 {_fmt_bytes(day['down'])}" if day else "")
        )
        return True

    # ---------- 内部 ----------

    def _log_manual_skip(self, dir_key: str, label: str, cur: int) -> None:
        """手动保护命中时的日志(状态变化 / 周期提醒, 其余轮次降 DEBUG)

        手动值是**持续状态** —— 用户不改 qB 里那个奇数限速就会一直命中, 逐轮记 INFO 等于同一行
        刷屏(实测 `interval: 10M` 下每天上百条, 且永远不停)。判据见 pitfalls/ops/alert-levels.md
        2.「同一根因只说明白一次」与 4.「持续状态不静默消失: 按周期再提醒, 被去重的轮次留 DEBUG」:
        进入该状态(或手动值变了)立即记一条 INFO, 之后同一状态每 `_MANUAL_REMIND_GAP` 再提醒一次。

        可见性不依赖这行日志: Web UI 的 `reasons`(code=manual)已显示锁图标与"命中/实际"两值。
        """
        now = time.time()
        prev = self._curve_manual_log.get(dir_key)
        if prev is None or prev[0] != cur or now - prev[1] >= _MANUAL_REMIND_GAP:
            self._curve_manual_log[dir_key] = (cur, now)
            logger.info(f"限速曲线 | {label}限速当前 {cur}KiB/s 为奇数, 疑似用户手动设置, 本轮不覆盖")
        else:
            logger.debug(f"限速曲线 | {label}限速当前 {cur}KiB/s 为奇数, 疑似用户手动设置(同状态不重复记)")

    def _record_curve_state(self, today: date, upload_kib: Optional[int], download_kib: Optional[int], dry_run: bool):
        """记录当日曲线计算结果到 state(供调试; 落盘走周期 save_state + 优雅退出)

        日键保 _CURVE_STATE_KEEP_DAYS 天(issue A-03: 每天新增一日键且从不清 -> state 缓慢
        无界增长; 淘汰口径走 prune_day_keys 单点, 对齐 ops_mod skip_check_day 的执行路径
        清理先例): 写入时顺带删掉保留期外的旧日键。仅主循环线程调用(黄金法则 5), 重复执行
        清理结果一致(幂等)。
        """
        curve_state = self._ctx.state.data.setdefault("speed_limit_curve", {})
        prune_day_keys(curve_state, today, _CURVE_STATE_KEEP_DAYS, lambda k, v: k)
        curve_state[today.isoformat()] = {
            "upload_kib": upload_kib,
            "download_kib": download_kib,
            "dry_run": dry_run,
        }

    def _publish_traffic(
        self,
        state: str,
        periods: Optional[List[dict]] = None,
        target: Optional[dict] = None,
        actual: Optional[dict] = None,
        reasons: Optional[List[dict]] = None,
        history: Optional[List[dict]] = None,
    ) -> None:
        """发布限速/流量只读快照(Web UI 顶栏 pill 的数据来源)

        经 ctx.web.set_traffic_view 服务方法**整体替换**(plan P3; Web 线程只读该引用,
        不原地修改) —— 无锁即可保证 Web 侧读到自洽的一份数据。state 语义(前端的渲染分支依据):
        - off:      数据来源总开关关闭(traffic_source.enabled=false, S1/D1) -> 不取数,
          前端灰显"来源已关闭"(判定优先于 disabled: 曲线功能可能仍启用, 停的是来源)
        - disabled: 未启用限速曲线 -> 不渲染流量/限速 pill
        - ok:       本轮正常读取并(必要时)写入限速, actual 为回读值
        - dry_run:  试运行: 只有目标限速, actual 为 None(不读不写 qB)
        - stale:    数据源缺失/无有效行, 本轮不动限速(仅提示数据不可用, periods 为空)

        单位: periods 为**字节**; target/actual 为 **KiB/s**(0 = 不限速, None = 该方向不管理);
        history 为按日升序的原始行(仅 ok/dry_run 发布), Web 端经 /api/traffic/history 读取。
        """
        self._ctx.web.set_traffic_view(
            {
                "ts": time.time(),
                "date": date.today().isoformat(),
                "state": state,
                "periods": periods or [],
                "history": history or [],
                "limit":
                    {
                        "target": target or {
                            "up": None,
                            "down": None
                        },
                        "actual": actual or {
                            "up": None,
                            "down": None
                        },
                        "reasons": reasons or [],
                    },
            }
        )
