"""RulesModule: 规则引擎的模块化封装(plan kernel-module-refactor P5 最大一刀)

RuleEngineMixin(状态持久化已于 P0 迁 core/state.py)整体迁入, 相位/服务接线:
- 事件分派: events_removed / events_added 相位(plan §4.2) —— 内核 _dispatch_events
  的两个调用点改广播, 分派知识(按 tracker 引用绑定 + trigger 分流)收进本模块;
- 逐种子管线: torrents_added 相位的「建任务」一步(plan §4.2: 维护→限速→建任务→归组→
  集数, 各家按装配序认领) —— 内核不再点名 _create_torrent_tasks;
- L2 结构重建(hot-reload W3 合并点): 重建任务队列与规则收进 apply, 整段相等即短路;
  级别分派层与三张手写表退役(W4), 重建判据单点在 _rebuild_needed;
- 段认领兜底(P6): rebuild_runtime 相位 —— 内核对「无认领面的变更段」广播, 本模块执行
  全量重建(与 L2 同一单点), 见 qbmanager.apply_new_config 与 impact.KERNEL_SECTIONS。

!Rule/RuleContext 的宿主面仍是 **QbManager**(构造期传入, 不换对象): 规则动作消费
  manager.store/state/task_queue/api/ctx.ops/group_* —— 换宿主面是 rules 动作层的
  独立改动面, 不混进本段。执行历史经 manager 委托走 ctx.state(P0 单点)。
!危险操作入口(P5 收口): 规则动作调 recheck/skip_check/check_filelist 改经
  manager.ctx.ops(P4 已把实现单点迁 OpsModule), manager 旧名只剩测试兼容委托。

!热重载语义(W4 表退役后, 消费知识单点在本模块):
  - apply 每次热重载无条件被调, _rebuild_needed 判整段相等即短路(§3.3 规则 1);
  - 重建判据 = 「创建时固化」的消费段: rules_config(规则定义)/interval(任务节奏)/
    delete_tags*/global_speed_limit_curve(全局任务集合)/trackers 绑定三元组
    (domains/rules/groups —— 匹配与规则绑定固化; tags/remove_tags/limits/hr_check
    运行时现读, 不触发重建, 过度重启族防线);
  - 重建不重读磁盘 state(运行期内存态 exec_history/skip_check_day 原对象保留,
    issue 26-09-21-1347); 重连复用内核 reconnect(client 换新 + rid 失效 → 下轮全量);
  - 事件重放保护: 挂总线 suppress 请求位(不置 live 旗标), 窗口协议见 EventBus.take_suppressed
    (内核刷新轮把它收敛到 events_removed/events_added 两个相位)。
"""
import logging
import time
from typing import List, Optional

from ...rules import Rule, RuleContext
from ..module import AppContext, ApplyResult, BaseModule
from ..taskqueue import FINISHED, REQUEUE, Task, TaskQueue

logger = logging.getLogger(__name__)


class RulesModule(BaseModule):
    """rules 模块: 规则加载 / 种子级规则任务 / 事件分派 / L2 结构重建"""

    name = "rules"

    def __init__(self, manager) -> None:
        # Rule/RuleContext 的宿主面(见模块 docstring): 规则动作仍按 QbManager 消费
        self._manager = manager
        # 规则结构(规则加载在 run() 中进行: --export-yaml 等只导出模式不需要)
        self.rules: List[Rule] = []
        self.enabled_rules: List[Rule] = []

    @property
    def _ctx(self) -> AppContext:
        """服务上下文(manager 现取, 与门面模块的「现取不缓存」同款)"""
        return self._manager.ctx

    def sections(self) -> tuple[str, ...]:
        return ("rules_config", "interval")

    # ---------- 相位订阅(plan §4.2: events_removed / events_added / torrents_added) ----------

    def subscribe(self, phases) -> None:
        phases.on("events_removed", self._on_events_removed)
        phases.on("events_added", self._on_events_added)
        phases.on("torrents_added", self._on_torrents_added)
        phases.on("rebuild_runtime", self._on_rebuild_runtime)

    def _on_rebuild_runtime(self, event) -> None:
        """段认领兜底(plan P6): 未认领段变更的保守全量重建, 语义与 L2 apply 同一单点

        内核只报「有变更段无人认领」这个时机(广播 rebuild_runtime 相位), 重建知识在本模块
        —— 与 queue_rebuilt 相位同款的非刷新类相位(P3 先例)。
        """
        self.rebuild_runtime()

    def _on_events_removed(self, event) -> None:
        """删除种子事件分派(带删除前快照); state/field 变化分派由同一相位承担
        (原内核调用点固定传 state_changed=True/field_changed=True, 见 qbmanager 相位表)"""
        p = event.payload
        self._dispatch_events(
            [],
            p.get("removed") or [],
            p.get("dry_run", False),
            removed_snapshots=p.get("snapshots") or {},
            state_changed=True,
            field_changed=True,
        )

    def _on_events_added(self, event) -> None:
        """新增种子(已匹配 tracker 配置)的事件规则分派"""
        p = event.payload
        self._dispatch_events(p.get("added") or [], [], p.get("dry_run", False))

    def _on_torrents_added(self, event) -> None:
        """逐新增种子管线的「建任务」一步(装配序在 maintenance/tracker/grouping 之后)"""
        self._create_torrent_tasks(event.payload["hash"])

    # ---------- 热重载(W3 合并点: L2 重建收进 apply; W4: 判据单点在本模块) ----------

    def apply(self, old, new) -> ApplyResult:
        if not self._rebuild_needed(old, new):
            return ApplyResult(self.name)
        logger.info("应用结构级配置变更: 重建任务队列/规则, 全部记录重匹配 tracker")
        self.rebuild_runtime()
        return ApplyResult(self.name, "rebuilt")

    def _rebuild_needed(self, old, new) -> bool:
        """L2 重建判据(W4 表退役后唯一单点; 整段相等即短路, hot-reload-simplify §3.3 规则 1)

        判据 = 创建/绑定时固化的消费段(判据依据见模块 docstring); 其余段要么运行时
        现读(换 config 对象即生效), 要么归各自模块 apply 认领。
        """
        if (
            old.rules_config != new.rules_config or old.interval != new.interval or
            old.delete_tags != new.delete_tags or
            old.delete_tags_if_has_no_torrents != new.delete_tags_if_has_no_torrents or
            old.global_speed_limit_curve != new.global_speed_limit_curve
        ):
            return True
        return self._tracker_bindings_changed(old.trackers, new.trackers)

    @staticmethod
    def _tracker_bindings_changed(old_t: dict, new_t: dict) -> bool:
        """tracker 绑定三元组(domains/rules/groups)是否变化; tracker 增删也视为绑定变化"""
        if old_t == new_t:
            return False
        for name in set(old_t) | set(new_t):
            o, n = old_t.get(name), new_t.get(name)
            if o is None or n is None:
                return True
            if (o.domains, o.rules, o.groups) != (n.domains, n.rules, n.groups):
                return True
        return False

    def rebuild_runtime(self) -> None:
        """L2 结构重建: 重建任务队列与规则, 运行期内存态原对象保留(issue 26-09-21-1347)

        - 不重读磁盘 state: state 平时不落盘, 磁盘上只有上次退出的旧版, 重读 = 回滚
          运行期内存态(exec_history/skip_check_day 等)。内存态即真相。
        - store.reset_runtime: 清分组索引/缓存, tracker_conf 置空 → 下轮全量 refresh 经
          full_round 相位重匹配(plan §4.2; 客户端重连使 rid 失效保证下轮是全量轮)。
        - queue_rebuilt 相位: 全局任务(delete_tags*/speed_limit_curve)由各模块自注册重入队。
        - 总线 suppress 请求位: 热重载首轮的 added 事件重放保护 —— 挂请求不置 live 旗标
          (挂位到消费点之间的相位照常送达, issue 26-10-01-0750), 窗口协议见 EventBus。
        """
        self._manager.task_queue = TaskQueue()
        self._ctx.store.reset_runtime()
        self._load_rules()
        self._manager.events.emit("queue_rebuilt")
        self._manager.events.request_suppression()
        self._manager.reconnect()

    # ---------- 规则: 加载(RuleEngineMixin 原样迁入, self.* 改 ctx/manager 现取) ----------

    def _load_rules(self):
        """从 config 的 `*_rules` 段加载规则集(条件+动作插件); Rule 的 manager 即宿主

        幂等: 重复调用先清空(init 与 run 都会调用)。
        收尾推导字段变化检测的监听集合(计划 26-09-27-1438): 所有 on_torrent_field_changed
        规则的 watch_fields 并集 ∪ (maintenance on_change 模式的 tags) —— 单点注入 store,
        无监听时 store 检测整体关闭(零基线、零对比开销)。
        """
        config = self._ctx.config
        self.rules = []
        self.enabled_rules = []
        for group_name, group in config.rules_config.items():
            if not isinstance(group, dict):
                continue
            for rule_name, spec in group.items():
                self.rules.append(Rule(f"{group_name}.{rule_name}", spec, self._manager))
        self.enabled_rules = [r for r in self.rules if r.enabled]
        if self.rules:
            logger.info(f"加载规则 {len(self.rules)} 条(启用 {len(self.enabled_rules)} 条)")
        watch: set = set()
        for r in self.rules:
            if r.trigger == "on_torrent_field_changed":
                watch.update(r.watch_fields)
        if getattr(config, "maintenance_tag_mode", "interval") == "on_change":
            watch.add("tags")  # maintenance B 路径: 外部 tags 变化检测不依赖任何规则配置(计划 §05)
        self._ctx.store.set_watch_fields(watch)

    # ---------- 规则: 种子级任务 ----------

    def _rules_for_torrent(self, torrent) -> list:
        """该种子应绑定的规则集: 匹配 tracker 的 rules 引用(@rule_set)

        torrent_conf 在 _refresh_torrents 阶段已匹配完成, 这里直接读取。
        不做防御性 fallback: conf=None 表示上游未走 refresh, 早崩溃便于定位调用路径。
        """
        refs = [ref[1:].strip() for ref in torrent.tracker_conf.rules if str(ref).strip().startswith("@")]
        if refs:
            rules = self._resolve_refs(refs)
            if rules:
                return rules
        return []

    def _create_rule_task(self, rule: Rule, hash: str) -> Optional[Task]:
        """为种子创建单条规则任务(interval = 规则内置 interval, 到期执行该规则于该种子)

        仅 interval trigger 规则创建周期任务; on_* 事件规则不建周期任务(返回 None, 由
        _create_torrent_tasks 过滤), 改由事件分派(_dispatch_events)按需以一次性 rule-event
        任务即时处理。调用方(add_tasks)不得收到 None —— 入队会 AttributeError。
        """
        if rule.trigger != "interval":
            return None
        return Task(
            "rule",
            rule.name,
            hash=hash,
            store=self._ctx.store,
            interval=rule.interval,
            handler=lambda t, d, r=rule: self._handle_rule(r, t, d),
        )

    def _handle_rule(self, rule: Rule, task: Task, dry_run: bool) -> bool:
        """种子级规则任务: 执行指定规则于该种子。

        - 种子已删除 -> False 任务消亡
        - pending 中断(校验提交, 断点已记录) -> False 本轮不重入, 由校验轮询子任务
          在完成后按情况重新入队(断点保留续跑 / reset 重走)
        - 其余(含异常) -> True 周期重入队
        """
        if task.torrent is None:
            return FINISHED
        ctx = RuleContext(self._manager, self._manager.client, self._ctx.config, task.hash, dry_run, task=task)
        try:
            handled, _stop = rule.process(ctx)
        except Exception as e:
            logger.error(f"任务[{task.log_tag}] | 规则执行异常: {e}", exc_info=True)
            return REQUEUE
        # 有未消费断点(pending 等待子任务恢复) -> 本轮不重入; 否则周期重入队
        return FINISHED if task.has_breakpoint else REQUEUE

    # ---------- 事件触发规则(trigger=on_*) ----------

    def _rules_by_trigger(self, trigger: str) -> list:
        """按触发时机过滤启用的规则(事件分派按 trigger 分流)"""
        return [r for r in self.enabled_rules if r.trigger == trigger]

    def _dispatch_events(
        self,
        added: list,
        removed: list,
        dry_run: bool,
        removed_snapshots=None,
        state_changed: bool = False,
        field_changed: bool = False,
    ) -> list:
        """事件分派总入口: 同步执行各事件规则(即时, 不排队).

        各事件规则按种子的 tracker 引用(rules: @规则集)绑定, 与 interval 规则同语义 ——
        `_torrent_event_rules` 取"该种子引用规则 ∩ 指定触发器"的交集。

        - on_torrent_added: 新增种子匹配 tracker 配置(与内核 added 循环同语义)后触发;
          未匹配的种子由内核 added 循环负责告警。
        - on_torrent_deleted: 种子已从 store 移除, 用删除前快照副本作 ctx.torrent,
          只读动作(print_torrent_details)仍可打印留档。
        - on_torrent_state_enum_changed: 用 store.state_changed(增量应用时按 **fetch 时状态**
          收集的 (hash, 新枚举))对比上一轮 state_snapshot, 变化的种子触发(新增种子无上一轮
          记录, 不视为状态变化)。state_changed 为 False 时完全跳过 —— 故本方法可在同轮
          多处调用而只有一次负责状态变化分派。
        - on_torrent_field_changed: 用 store.field_changed(增量应用时经 qB 增量 ∩ 监听字段
          后与持久化基线对比的净变化)触发; 首见/无基线/自写抑制的已在 store 侧剔除。
          field_changed 为 False 时完全跳过(同 state_changed 的"同轮多处调用只一次负责")。
          规则侧再按 watch_fields ∩ 实际变化字段过滤 —— 只关心本次变化字段的规则才触发。

        规则执行经 _apply_event_rule 建 rule-event 一次性 Task 作 ctx.task: 遇 checking 返回
        pending 时, 该 Task 作 origin 由轮询子任务 add_task(origin, keep_progress=True) 重新
        入队, 下 tick _handle_event_rule 断点续跑后 FINISHED 消亡(不自我周期循环)。
        事件即时分派不进入 _fast 队列, 不计入 max_tasks_per_tick。
        返回: 触发过事件的 hash 列表(测试断言用)。
        """
        triggered: list = []

        # on_torrent_deleted: 删除后种子无活现场, 快照副本作 ctx.torrent
        if self._rules_by_trigger("on_torrent_deleted") and removed:
            for h in removed:
                snap = (removed_snapshots or {}).get(h)
                if snap is None or snap.tracker_conf is None:
                    continue  # 无 tracker 配置, 无规则可绑定
                for rule in self._torrent_event_rules(snap, "on_torrent_deleted"):
                    self._apply_event_rule(rule, h, dry_run=dry_run, snapshot=snap)
                    triggered.append(h)

        # on_torrent_state_enum_changed: 本轮 state 字段变化的种子(增量应用时收集, O(变化数))
        if state_changed and self._rules_by_trigger("on_torrent_state_enum_changed"):
            prev = self._ctx.store.state_snapshot
            for h, cur in self._ctx.store.state_changed:
                if h not in prev or prev[h] == cur:
                    continue
                tor = self._ctx.store.get(h)
                if tor is None or tor.tracker_conf is None:
                    continue
                for rule in self._torrent_event_rules(tor, "on_torrent_state_enum_changed"):
                    self._apply_event_rule(rule, h, dry_run=dry_run)
                    triggered.append(h)

        # on_torrent_field_changed: 本轮监听字段的净变化种子(store 侧已对比持久化基线, O(变化数))
        if field_changed and self._rules_by_trigger("on_torrent_field_changed"):
            for h, fields in self._ctx.store.field_changed:
                tor = self._ctx.store.get(h)
                if tor is None or tor.tracker_conf is None:
                    continue
                for rule in self._torrent_event_rules(tor, "on_torrent_field_changed"):
                    if not set(rule.watch_fields) & fields:
                        continue  # 本次变化字段与该规则监听的无关
                    self._apply_event_rule(rule, h, dry_run=dry_run)
                    triggered.append(h)

        # on_torrent_added: 匹配 tracker 配置并触发(命中者由内核做后续自有动作)
        if self._rules_by_trigger("on_torrent_added") and added:
            for h in added:
                tor = self._ctx.store.get(h)
                if tor is None:
                    continue
                if tor.tracker_conf is None:
                    tor.tracker_conf = self._ctx.trackers.match(tor)
                if tor.tracker_conf is None:
                    continue  # 未匹配 tracker: 内核 added 循环负责告警
                for rule in self._torrent_event_rules(tor, "on_torrent_added"):
                    self._apply_event_rule(rule, h, dry_run=dry_run)
                    triggered.append(h)

        return triggered

    def _torrent_event_rules(self, tor, trigger: str) -> list:
        """该种子指定 trigger 的事件规则: 经 tracker 引用绑定的规则 ∩ 指定触发器(与 interval 同语义)"""
        return [r for r in self._rules_for_torrent(tor) if r.trigger == trigger]

    def _apply_event_rule(self, rule: Rule, hash: str, dry_run: bool = False, snapshot=None) -> Task:
        """为事件规则建 rule-event 一次性 Task 作 ctx.task, 同步执行 process(即时).

        rule-event 任务不进入 _fast 队列: 事件即时分派不排队。process 返回 pending 时该
        Task 记录断点(resume_index)并作 origin, 由轮询子任务 add_task(origin, keep_progress=True)
        重新入队, 下 tick _handle_event_rule 续跑。正常完成(无 pending)则 Task 不被入队, 自然消亡。
        返回该 rule-event Task(供测试断言其断点状态)。
        """
        task = Task(
            "rule-event",
            rule.name,
            hash=hash,
            store=self._ctx.store,
            interval=rule.interval,
            handler=lambda t, d, r=rule, s=snapshot: self._handle_event_rule(r, t, s, d),
        )
        ctx = RuleContext(
            self._manager, self._manager.client, self._ctx.config, hash, dry_run, task=task, snapshot=snapshot
        )
        try:
            rule.process(ctx)
        except Exception as e:
            logger.error(f"事件规则[{rule.name}] {hash[:8]} | 执行异常: {e}", exc_info=True)
        return task

    def _handle_event_rule(self, rule: Rule, task: Task, snapshot, dry_run: bool) -> bool:
        """事件规则 rule-event 任务的断点续跑 handler(恒返回 FINISHED, 不自我周期循环).

        种子已删除 -> 直接消亡(删除守卫); 否则重建 ctx(断点由轮询子任务
        add_task(keep_progress=True) 保留)续跑后续动作。续跑后再遇 pending(如连续多个
        checking)由新的轮询子任务重新入队, 本 handler 恒 FINISHED —— rule-event 任务不按
        interval 周期重入, 事件语义保持"一次性但可恢复"。
        """
        if task.torrent is None:
            return FINISHED
        ctx = RuleContext(
            self._manager, self._manager.client, self._ctx.config, task.hash, dry_run, task=task, snapshot=snapshot
        )
        try:
            rule.process(ctx)
        except Exception as e:
            logger.error(f"事件规则[{rule.name}] {task.hash[:8]} | 续跑异常: {e}", exc_info=True)
        return FINISHED

    # ---------- tracker 引用 ----------

    def _resolve_refs(self, refs: list[str]) -> list:
        """解析 '@rule_set' / '@rule_set.rule_name' 引用为 Rule 列表(按名称去重)"""
        result, seen = [], set()
        for ref in refs:
            if "." in ref:
                group, name = ref.split(".", 1)
                target = f"{group}.{name}"
                for r in self.enabled_rules:
                    if r.name == target and r.name not in seen:
                        result.append(r)
                        seen.add(r.name)
            else:
                for r in self.enabled_rules:
                    if r.name.startswith(ref + ".") and r.name not in seen:
                        result.append(r)
                        seen.add(r.name)
        return result

    # ---------- 种子级任务创建(原 qbmanager._create_torrent_tasks, torrents_added 相位认领) ----------

    def _create_torrent_tasks(self, hash: str):
        """
        为新增种子创建任务: 内置 maintenance + 所有符合条件的规则任务

        缺文件检查统一由分组事件驱动承担(_refresh_torrents 检测到删除/状态变化/
        保存路径变化立即触发组内扫描), 不再创建逐种子 missing_files 任务。
        每个任务有内置 interval(规则任务用规则自身 interval), 规则任务加入队列即立即到期(下一 tick 执行)。
        内置种子任务加入队列后下一个interval到期。
        """
        torrent = self._ctx.store.get(hash)
        if not torrent:
            return

        # 创建内置种子任务(handler 经 ctx.maintenance 模块句柄取, 不 import 兄弟模块)
        self._ctx.task_queue.add_task(
            Task(
                "internal",
                "maintenance",
                hash=hash,
                store=self._ctx.store,
                interval=self._ctx.config.interval,
                handler=self._ctx.maintenance.handle_maintenance_task_interface,
            ),
            time.time() + self._ctx.config.interval,
        )

        # 创建种子规则任务(仅 interval 规则建周期任务; on_* 事件规则不建, 由事件分派即时处理)
        tasks = []
        for rule in self._rules_for_torrent(torrent):
            task = self._create_rule_task(rule, hash)
            if task is not None:
                tasks.append(task)
        self._ctx.task_queue.add_tasks(tasks)
