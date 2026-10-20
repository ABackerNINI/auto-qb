"""TrafficSnapshotModule: 流量快照的所有者(计划 26-10-18-0813 A1/A2; 拍板 D3/D8/D9/D10)

**为什么要有这个模块**: 快照原先由限速曲线任务独家发布 —— 曲线没配, 任务根本不注册, 历史流量图
就永远是空的(结构性死角); 而且同一个方法里既算历史/累计(来源职责)又算目标/实际限速(曲线职责),
两条刷新路径(定时整份替换 / 事件浅拷贝覆写)语义还各说各话。本模块把**来源侧**拿过来:

- 拥有 `ts` / `date` / `source` / `periods` / `history` 五键, 由自注册任务按
  `traffic_source.refresh_interval`(与曲线 `interval` 解绑)周期刷新;
- **事件零读盘补丁**(26-10-21, 用户拍板「读盘本身就是副作用, 要尽量减少读盘」): gtm 阈值
  事件自带当日权威累计, `publish_event` 只改 periods 的 day 行、一次读盘都没有 —— 文件
  读盘全部收拢在 refresh_interval 一个闸门(定时 / 切源 / 兜底)。day 行带**每日高水位
  钳制**: 崩溃恢复时首个 catch-up 事件可能偏低(state.json 比 dat 旧), 钳制抹掉这个
  闪跳, 按日清零;
- 曲线的 `limit` 段经 `publish_limit()` 写入 —— 段级契约代替整体替换: 谁写哪一段写进 API,
  而不是靠"两个任务别同时发"的约定;
- 顶层 `state` 是**派生值**: 一律 `derive_state(source.state, limit.state)`, 没有第二个真相源。

段隔离(D10): 三个 publisher 内部都是「读旧快照 -> 只改自己那段 -> 一次 set_traffic_view」,
所以来源刷新不会把限速浮层的目标值清空, 曲线一轮也不会把历史图清空。

边界: 本模块只读流量文件 + 发布内存快照, **不碰 qB**(不读不写全局限速, 那是曲线模块的事);
事件路径(publish_event)连文件都不读 —— 读盘是成本, 全部收拢在 refresh_interval 闸门。
"""
import logging
import time
from datetime import date
from typing import Iterable, List, Optional, Sequence, Tuple

from .. import curves
from ..module import AppContext, ApplyResult, BaseModule
from ..taskqueue import REQUEUE, Task
from ..traffic_source import paths as traffic_paths
from ..traffic_source.reader import read_source_rows

logger = logging.getLogger(__name__)

MODULE_NAME = "traffic_snapshot"

#: 任务名刻意与模块名不同名(沿用 speed_curve -> speed_limit_curve 的既有做法): 模块名是装配面,
#: 任务名是队列面; 同名会让"找模块"与"找任务"的排障检索互相干扰。
TASK_NAME = "traffic_snapshot_refresh"

#: 快照 periods 的**固定**两行(A2): 唯一消费点是 `period == "day"`(顶栏「今日流量」pill),
#: month 供口径对照。曲线侧要的 ND 累计仍由曲线模块自己 `curves.aggregate` 算, 不进快照 ——
#: 快照的 periods 不再是"各曲线 period 的并集", 所以曲线增删不改变快照形状。
PERIODS: Tuple[Tuple[str, str], ...] = (("day", "今日"), ("month", "本月"))

# 段状态取值(契约面; 前端逐批迁移到细分字段, 顶层 state 恒为 derive 结果)
SOURCE_OK, SOURCE_STALE, SOURCE_OFF = "ok", "stale", "off"
LIMIT_OK, LIMIT_DRY_RUN, LIMIT_DISABLED, LIMIT_STALE = "ok", "dry_run", "disabled", "stale"


def derive_state(source_state: str, limit_state: str) -> str:
    """两个段状态 -> 顶层 state(单点纯函数, D8)

    优先级逐格与今日语义对齐(今日只有一个 state, 三处前端消费点按它分流):

    | 今日的发布者与形态                          | 新契约                       | 派生值     |
    |--------------------------------------------|------------------------------|------------|
    | 来源总开关关(曲线任务发 off)                | source=off                   | off        |
    | dat 缺失/无有效行(曲线任务发 stale)         | source=stale                 | stale      |
    | 曲线未配置 / enabled=false                  | limit=disabled               | disabled   |
    | dry_run                                     | limit=dry_run                | dry_run    |
    | 正常轮                                      | 两者皆 ok                    | ok         |

    顺序即优先级: 来源关 > 数据不可用(来源段或限速段) > 曲线未启用 > 试运行 > 正常。

    **为什么 limit=stale 也算 stale**(计划表里只列了来源段): 今日「读档失败 -> stale」的判定方
    是曲线任务, 解耦后两个模块读同一份 dat、各自都能先发现不可用 —— 谁先命中都得报 stale,
    否则会出现「曲线已判定读档失败、顶层 state 仍是 ok」的窗口(限速浮层显示"正常"却没有目标值)。
    这一格是与今日语义对齐, 不是新增状态。
    """
    if source_state == SOURCE_OFF:
        return SOURCE_OFF
    if source_state == SOURCE_STALE or limit_state == LIMIT_STALE:
        return SOURCE_STALE
    if limit_state == LIMIT_DISABLED:
        return LIMIT_DISABLED
    if limit_state == LIMIT_DRY_RUN:
        return LIMIT_DRY_RUN
    return "ok"


def _source_state_of(view: dict) -> str:
    """旧快照的来源态; 段缺失按 ok(「该段没有异议」) —— 不臆造关闭/不可用(保守默认的另一面:
    段缺失是"还没发布过", 不是"来源关了")"""
    return str(((view.get("source") or {}).get("state")) or SOURCE_OK)


def _limit_state_of(view: dict) -> str:
    """旧快照的限速态; 段缺失按 ok(同 _source_state_of 口径)"""
    return str(((view.get("limit") or {}).get("state")) or LIMIT_OK)


def _history_rows(rows: Sequence[curves.HistoryRow]) -> List[dict]:
    """dat 行 -> 历史流量快照行(按日升序): Web 端经 /api/traffic/history 读取

    历史行**不进轮询响应**(A5: /api/status·/api/state 用 public_traffic_view 摘掉), 几百行
    每轮回传是纯浪费; 弹层打开/快照 ts 变化时走专用端点。
    """
    return [{"date": d.isoformat(), "up": up, "down": down} for d, up, down in rows]


def _period_rows(rows: Sequence[curves.HistoryRow], today: date) -> List[dict]:
    """来源侧固定发布 day + month 两行(单位: 字节)"""
    out: List[dict] = []
    for period, label in PERIODS:
        up, down = curves.aggregate(list(rows), period, today)
        out.append({"period": period, "label": label, "up": up, "down": down})
    return out


def _limit_segment(target=None, actual=None, reasons: Iterable[dict] = (), state: str = LIMIT_OK) -> dict:
    """limit 段形状单点(方向键恒存在, 缺失方向为 None = 该方向不管理)"""
    return {
        "target": dict(target or {
            "up": None,
            "down": None
        }),
        "actual": dict(actual or {
            "up": None,
            "down": None
        }),
        "reasons": list(reasons),
        "state": state,
    }


class TrafficSnapshotModule(BaseModule):
    """traffic_snapshot 模块: 来源段所有者 + 段级发布 API"""

    name = MODULE_NAME

    def __init__(self, ctx: AppContext) -> None:
        self._ctx = ctx
        #: 每日事件补丁高水位(26-10-21): day -> (已发布最大 up, 已发布最大 down)。
        #: 事件路径零读盘, 但崩溃恢复时工具内存可能低于 dat 已有值(state.json 比 dat 旧),
        #: 首个 catch-up 事件载荷会偏低 —— 钳制让 pill 不回退, 按日清零只留今天的键。
        self._hw: dict = {}

    def sections(self) -> tuple[str, ...]:
        """**只**消费来源段 —— 不声明 `global_speed_limit_curve` 正是解耦的判据(A1 守阵):
        曲线关掉/没配, 本模块照跑; 若哪天有人给它加上曲线段, 说明职责又被混回去了。
        """
        return ("traffic_source", )

    # ---------- 生命周期 ----------

    def start(self, ctx: AppContext, dry_run: bool) -> None:
        """任务自注册: dry_run 不影响注册(dry_run 只影响曲线写不写 qB, 本模块不碰 qB)。
        **无配置门槛** —— 这正是"没配曲线也能看历史图"的落点: 任务照跑, 历史照发。
        """
        self._register_global_task(ctx)

    def subscribe(self, phases) -> None:
        phases.on("queue_rebuilt", self._on_queue_rebuilt)

    def _on_queue_rebuilt(self, event) -> None:
        """L2 热重载整体重建队列后重新入队(新 interval; 已在队列则幂等跳过)"""
        self._register_global_task(self._ctx)

    def apply(self, old, new) -> ApplyResult:
        """热重载: 来源段一变就同步节奏(已在队列的任务**就地**改 interval, 不重复入队)

        为什么就地改而不是重新注册: 队列是按 next_run 排序的堆, 新增/删除任务要维护堆序;
        而 interval 只被 `_requeue` 在**下一轮收尾**读 —— 就地改只影响下一次排期, 零结构变更。
        当前这一轮的到期时刻保持原值(最多等一个旧间隔), 之后按新间隔走。
        """
        if getattr(old, "traffic_source", None) == getattr(new, "traffic_source", None):
            return ApplyResult(self.name)  # 段相等短路(热重载统一挂载口语义)
        task = self._registered_task()
        if task is not None:
            task.interval = max(1.0, float(self._interval_of(new)))
            logger.info(f"流量快照 | 刷新间隔热更新为 {task.interval:.0f}s")
        return ApplyResult(self.name, "reloaded")

    def _register_global_task(self, ctx: AppContext) -> None:
        """任务自注册(骨架走 BaseModule.register_global_tasks 单点); 已入队则幂等跳过"""
        self.register_global_tasks(ctx, [(TASK_NAME, self.handle_traffic_snapshot, self._interval_of(ctx.config))])

    def _registered_task(self) -> Optional[Task]:
        queue = self._ctx.task_queue
        return queue.named(TASK_NAME) if queue is not None else None

    @staticmethod
    def _interval_of(config) -> float:
        """来源侧刷新节奏(A3): 缺键(桩配置/老调用方)回退 600s, 与 models 默认同值"""
        ts = getattr(config, "traffic_source", None)
        return float(getattr(ts, "refresh_interval", None) or 600.0)

    # ---------- 全局任务执行体 ----------

    def handle_traffic_snapshot(self, task: Task, dry_run: bool) -> bool:
        """全局任务执行体: 读来源 -> 发布来源段; 恒 REQUEUE(周期任务, 数据不可用也不停表)"""
        self.refresh()
        return REQUEUE

    def refresh(self) -> bool:
        """读一次来源并发布来源段 -> 是否发布了**新数据**(命令回执与日志据此区分"已刷新/跳过")

        这是「来源刷新」的**唯一执行路径**(A5/D11): 定时任务与 `refresh_traffic` 命令(工具事件
        通知 / 配置切源)都走这里, 不各写一份读盘逻辑。

        三种结局:
        - 来源总开关关 -> 发布 off 快照(不读盘), 返回 False(没有新数据);
        - 数据源不可用(缺文件/无有效行) -> 发布 source=stale(清 periods/history), 返回 False;
        - 正常 -> 发布 source=ok + history/periods, 返回 True。
        """
        if not traffic_paths.source_enabled(self._ctx.config):
            logger.info("流量快照 | 来源总开关关闭(traffic_source.enabled=false), 发布 off 快照")
            self.publish_off("流量来源已关闭(traffic_source.enabled=false): 已停止取数")
            return False
        dat_path = traffic_paths.dat_path(self._ctx.config)
        rows, bad, fail = read_source_rows(dat_path)
        if fail is not None:
            logger.warning(f"流量快照 | {fail['log']}")
            self.publish_source([], SOURCE_STALE, [{"dir": "", "code": fail["code"], "text": fail["text"]}])
            return False
        if bad:
            logger.warning(f"流量快照 | 流量数据 {bad} 行无法解析已跳过({dat_path})")
        self.publish_source(rows, SOURCE_OK)
        today = date.today().isoformat()
        day = next((r for r in rows if r[0].isoformat() == today), None)
        # DEBUG: 定时任务与通知链路共用 refresh(), 大流量日通知刷新可达数百次 —— INFO 会刷屏
        # (26-10-18 用户要求降级); 读盘失败/坏行两条 WARNING 不降, 异常仍要响亮。
        logger.debug(f"流量快照 | 发布历史流量: {len(rows)} 行" + (f", 今日 上传 {day[1]}B/下载 {day[2]}B" if day else ""))
        return True

    def publish_event(self, day: str, up, down) -> bool:
        """事件载荷补丁(26-10-21): **零读盘**, 只把当日累计写进 periods 的 day 行

        gtm 阈值事件六键自带当日权威累计(up_bytes/down_bytes; 工具推送前已强制落盘, dat 与
        事件值一致) —— 顶栏「今日流量」pill 的数据源就是 periods 的 day 行, 补丁不需要读
        dat: 文件读盘全部收拢在 refresh_interval 闸门(用户拍板「读盘本身就是副作用, 要尽量
        减少读盘」), 事件路径一次读盘都没有、零额外网络调用(事件本身那次 HTTP 之外)。

        高水位钳制: 取 max(载荷, `_hw[day]`) 后发布并记回 `_hw` —— 崩溃恢复时工具内存可能
        低于 dat 已有值, 首个 catch-up 事件载荷会偏低, 钳制抹掉这个闪跳; 按日清零(只保留
        今天的键)。文件读盘路径(`publish_source` 的 ok 分支)同样不低于该水位, 两条发布
        路径都不让 day 行回退。

        返回是否**发布了新值**(命令回执与日志据此区分"已补丁/未变化")。非当日 / 关源 ->
        False(端点通常已拦; 执行期竞态兜底, 那天的累计由兜底读盘覆盖)。
        """
        today = date.today().isoformat()
        if day != today or not traffic_paths.source_enabled(self._ctx.config):
            return False
        hw_up, hw_down = self._hw.get(today, (0, 0))
        new_up, new_down = max(int(up), hw_up), max(int(down), hw_down)
        self._hw = {today: (new_up, new_down)}
        view = dict(self._ctx.web.traffic_view or {})
        periods = [dict(row) for row in (view.get("periods") or [])]
        row = next((r for r in periods if r.get("period") == "day"), None)
        if row is None:
            # 冷启动后首个事件先于任何文件读盘: 建 day 行(month 行等首次读盘补上,
            # 前端按 period 取行, 缺 month 不渲染本月对照, 不影响 pill)
            periods.insert(0, {"period": "day", "label": "今日", "up": new_up, "down": new_down})
            changed = True
        else:
            changed = (row.get("up"), row.get("down")) != (new_up, new_down)
            row["up"], row["down"] = new_up, new_down
        if not changed:
            return False
        self._publish(periods=periods)
        logger.debug(f"流量快照 | 事件补丁今日流量({today}): 上传 {new_up}B/下载 {new_down}B(零读盘)")
        return True

    # ---------- 段级发布 API(D10: 全模块唯一改动 traffic_view 的入口) ----------

    def publish_source(
        self, rows: Sequence[curves.HistoryRow], state: str = SOURCE_OK, reasons: Iterable[dict] = ()
    ) -> None:
        """写来源段: ts / date / source / periods / history —— **保留旧 limit 段**

        rows 是 dat 的按日行(不是快照行): periods 与 history 由同一份行派生, 两者不会漂移。
        state 只允许 ok / stale(off 走 publish_off): 来源关闭时 periods/history 必须一起清空。

        26-10-21 起 ok 分支的 day 行带**高水位钳制**: 不低于 `_hw[今天]`(事件补丁记的最大值)
        —— 崩溃恢复后工具内存可能低于 dat 已有值, 文件读盘不许把 pill 刷回更小的数; 两条发布
        路径(本方法 / publish_event)都不让 day 行回退。stale/off 分支不钳: 清空/归零是它们
        的语义。
        """
        today = date.today()
        periods = _period_rows(rows, today)
        if state == SOURCE_OK:
            hw = self._hw.get(today.isoformat())
            if hw is not None:
                row = next((r for r in periods if r["period"] == "day"), None)
                if row is not None:
                    row["up"], row["down"] = max(row["up"], hw[0]), max(row["down"], hw[1])
        self._publish(
            source={
                "state": state,
                "reasons": list(reasons)
            },
            periods=periods,
            history=_history_rows(rows),
        )

    def publish_limit(
        self,
        target: Optional[dict] = None,
        actual: Optional[dict] = None,
        reasons: Iterable[dict] = (),
        state: str = LIMIT_OK,
    ) -> None:
        """写 limit 段(曲线模块的唯一入口) —— **不动** source / periods / history

        单位契约不变: target/actual 为 KiB/s(0 = 不限速, None = 该方向不管理)。
        """
        self._publish(limit=_limit_segment(target, actual, reasons, state))

    def publish_off(self, reason: str = "") -> None:
        """来源关闭: source 翻 off、清 periods/history、limit 复位 disabled

        limit 的 target/actual 一并归 None: 来源关了就没有"命中目标"可言, 与今日 off 快照
        逐字段一致(限速浮层此时不列任何受管方向)。
        """
        self._publish(
            source={
                "state": SOURCE_OFF,
                "reasons": [{
                    "dir": "",
                    "code": "source_off",
                    "text": reason or "流量来源已关闭",
                }],
            },
            periods=[],
            history=[],
            limit=_limit_segment(state=LIMIT_DISABLED),
        )

    # ---------- 内部 ----------

    def _publish(self, **segments) -> None:
        """段级写的唯一执行点: 读旧快照 -> 合并自有键 -> 派生 state -> 一次 set_traffic_view

        - 引用整体替换(Web 线程只读单引用, 无锁即自洽; 与 runtime.set_traffic_view 同一契约);
        - 顶层 state **不接受外部入参**, 一律 derive_state(段状态) —— 派生的单点在这里, 调用方
          想改状态只能改段(D8 防"第二真相源");
        - ts/date 两条发布路径都刷新(与今日"每轮整份替换"的 ts 语义等价): 前端监听 ts 变化
          重拉历史弹层, 行为不变。
        """
        view = dict(self._ctx.web.traffic_view or {})
        view.update(segments)
        view["ts"] = time.time()
        view["date"] = date.today().isoformat()
        view["state"] = derive_state(_source_state_of(view), _limit_state_of(view))
        self._ctx.web.set_traffic_view(view)


__all__ = [
    "MODULE_NAME",
    "TASK_NAME",
    "PERIODS",
    "TrafficSnapshotModule",
    "derive_state",
    "LIMIT_DISABLED",
    "LIMIT_DRY_RUN",
    "LIMIT_OK",
    "LIMIT_STALE",
    "SOURCE_OFF",
    "SOURCE_OK",
    "SOURCE_STALE",
]
