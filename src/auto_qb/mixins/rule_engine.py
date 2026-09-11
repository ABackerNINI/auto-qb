"""规则引擎 mixin: 规则加载 / 状态持久化(执行历史+上传量快照) / 种子级规则任务 / process_torrent 兼容入口

由 QbManager 组合(mixin), 依赖实例属性: config/rules/enabled_rules/logger/state_file/state/client/task_queue。
"""
import json
import logging
from datetime import date, datetime
from typing import Any, List, Optional
from qbittorrentapi import Client

from ..config import Config
from ..taskqueue import FINISHED, REQUEUE, Task, TaskQueue
from ..rules import Rule, RuleContext
from .. import utils
from ..torrents import TorrentRecord

logger = logging.getLogger(__name__)


class RuleEngineMixin:
    """规则引擎: 规则加载/状态持久化/种子级规则任务"""

    config: Config
    client: Optional[Client]
    state_file: str
    state: dict
    rules: List[Rule]
    enabled_rules: List[Rule]
    task_queue: TaskQueue

    # ---------- 规则: 加载 / 状态持久化 ----------

    def _load_rules(self):
        """从 config 的 `*_rules` 段加载规则集(条件+动作插件); Rule 的 manager 即本对象

        幂等: 重复调用先清空(init 与 run 都会调用)。
        """
        self.rules = []
        self.enabled_rules = []
        for group_name, group in self.config.rules_config.items():
            if not isinstance(group, dict):
                continue
            for rule_name, spec in group.items():
                self.rules.append(Rule(f"{group_name}.{rule_name}", spec, self))
        self.enabled_rules = [r for r in self.rules if r.enabled]
        if self.rules:
            logger.info(f"加载规则 {len(self.rules)} 条(启用 {len(self.enabled_rules)} 条)")

    def _load_state(self) -> dict:
        try:
            with open(self.state_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return data
        except (FileNotFoundError, json.JSONDecodeError):
            pass
        return {}

    def save_state(self):
        try:
            with open(self.state_file, "w", encoding="utf-8") as f:
                json.dump(self.state, f, ensure_ascii=False, indent=2)
        except OSError as e:
            logger.warning(f"保存状态文件失败: {e}")

    def record_execution(self, rule_name: str, hash: str):
        """记录规则执行历史(execute_once/cooldown 去重依据); 仅主循环线程调用, 线程安全"""
        now = datetime.now()
        history = self.state.setdefault("exec_history", {})
        history[f"{rule_name}:{hash}"] = {
            "ts": now.timestamp(),
            "date": now.date().isoformat(),
            "hour": now.hour,
        }

    def get_exec_record(self, rule_name: str, hash: str):
        return self.state.get("exec_history", {}).get(f"{rule_name}:{hash}")

    def begin_round(self, torrents: List[TorrentRecord]):
        """维护上传量快照(按自然日/周/月, 周期切换时重建基线) — 由 refresh 任务调用, 幂等"""
        snaps = self.state.setdefault("upload_snapshots", {})
        today = date.today()
        buckets = {
            "daily": today.isoformat(),
            "weekly": f"{today.isocalendar().year}-W{today.isocalendar().week:02d}",
            "monthly": today.strftime("%Y-%m"),
        }
        for kind, key in buckets.items():
            bucket = snaps.setdefault(kind, {})
            if bucket.get("key") != key:
                bucket.clear()
                bucket["key"] = key
                bucket["baseline"] = {t.hash: t.uploaded for t in torrents}

    def upload_delta(self, torrent: TorrentRecord, kind: str) -> int:
        """周期上传增量: 当前 uploaded - 周期开始时快照, 下限 0(防种子重加/客户端重启归零)"""
        bucket = self.state.get("upload_snapshots", {}).get(kind, {})
        baseline = bucket.get("baseline", {})
        base = baseline.get(torrent.hash, 0)
        return max(0, torrent.uploaded - base)

    # ---------- 规则: 种子级任务 ----------

    def _rules_for_torrent(self, torrent: TorrentRecord) -> list:
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
            store=self.store,
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
        ctx = RuleContext(self, self.client, self.config, task.hash, dry_run, task=task)
        try:
            handled, _stop = rule.process(ctx)
        except Exception as e:
            logger.warning(f"任务[{task.log_tag}] | 规则执行异常: {e}", exc_info=True)
            return REQUEUE
        # 有未消费断点(pending 等待子任务恢复) -> 本轮不重入; 否则周期重入队
        return FINISHED if task.has_breakpoint else REQUEUE

    # ---------- 事件触发规则(trigger=on_*) ----------

    def _rules_by_trigger(self, trigger: str) -> list:
        """按触发时机过滤启用的规则(事件分派按 trigger 分流)"""
        return [r for r in self.enabled_rules if r.trigger == trigger]

    def _dispatch_events(self, added: list, removed: list, dry_run: bool, removed_snapshots=None, tors=None) -> list:
        """事件分派总入口: 同步执行各事件规则(即时, 不排队).

        各事件规则按种子的 tracker 引用(rules: @规则集)绑定, 与 interval 规则同语义 ——
        `_torrent_event_rules` 取"该种子引用规则 ∩ 指定触发器"的交集。

        - on_torrent_added: 新增种子匹配 tracker 配置(复用 _match_tracker_conf, 与主循环
          added 循环同语义)后触发; 未匹配的种子由主循环 added 循环负责告警。
        - on_torrent_deleted: 种子已从 store 移除, 用删除前快照副本作 ctx.torrent,
          只读动作(print_torrent_details)仍可打印留档。
        - on_torrent_state_enum_changed: 对比上一轮 state_snapshot 与当前状态枚举, 变化的
          种子触发(新增种子无上一轮记录, 不视为状态变化)。

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

        # on_torrent_state_enum_changed: 上一轮快照对比当前状态枚举
        if self._rules_by_trigger("on_torrent_state_enum_changed") and tors is not None:
            prev = self.store.state_snapshot
            for t in tors:
                h = t.hash
                if h in prev and prev[h] != t.state_enum:
                    tor = self.store.get(h)
                    if tor is None or tor.tracker_conf is None:
                        continue
                    for rule in self._torrent_event_rules(tor, "on_torrent_state_enum_changed"):
                        self._apply_event_rule(rule, h, dry_run=dry_run)
                        triggered.append(h)

        # on_torrent_added: 匹配 tracker 配置并触发(命中者由主循环做后续自有动作)
        if self._rules_by_trigger("on_torrent_added") and added:
            for h in added:
                tor = self.store.get(h)
                if tor is None:
                    continue
                if tor.tracker_conf is None:
                    tor.tracker_conf = self._match_tracker_conf(tor)
                if tor.tracker_conf is None:
                    continue  # 未匹配 tracker: 主循环 added 循环负责告警
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
            store=self.store,
            interval=rule.interval,
            handler=lambda t, d, r=rule, s=snapshot: self._handle_event_rule(r, t, s, d),
        )
        ctx = RuleContext(self, self.client, self.config, hash, dry_run, task=task, snapshot=snapshot)
        try:
            rule.process(ctx)
        except Exception as e:
            logger.warning(f"事件规则[{rule.name}] {hash[:8]} | 执行异常: {e}", exc_info=True)
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
        ctx = RuleContext(self, self.client, self.config, task.hash, dry_run, task=task, snapshot=snapshot)
        try:
            rule.process(ctx)
        except Exception as e:
            logger.warning(f"事件规则[{rule.name}] {task.hash[:8]} | 续跑异常: {e}", exc_info=True)
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
