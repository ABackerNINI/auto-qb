"""规则引擎 mixin: 规则加载 / 状态持久化(执行历史+上传量快照) / 种子级规则任务 / process_torrent 兼容入口

由 QbManager 组合(mixin), 依赖实例属性: config/rules/enabled_rules/logger/state_file/state/client/task_queue/_get_torrent。
"""
import json
import logging
from datetime import date, datetime
from typing import Any, List, Optional
from qbittorrentapi import Client

from ..config import Config, TrackerConfig
from ..taskqueue import TaskQueue
from ..rules import Rule, RuleContext
from ..taskqueue import Task
from .. import utils
from ..torrents import TorrentRecord

logger = logging.getLogger(__name__)


class RuleEngineMixin:
    """规则引擎: 加载/状态持久化/种子级规则任务/向后兼容 process_torrent 入口"""

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
        rules_config = getattr(self.config, "rules_config", {}) or {}
        for group_name, group in rules_config.items():
            if not isinstance(group, dict):
                continue
            for rule_name, spec in group.items():
                self.rules.append(Rule(f"{group_name}.{rule_name}", spec, self))
        self.enabled_rules = [r for r in self.rules if r.enabled]
        if self.rules:
            logger.info(f"rules 框架: 加载 {len(self.rules)} 条规则, 启用 {len(self.enabled_rules)} 条")

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
        """该种子应绑定的规则集: 匹配 tracker 的 rules 引用(@rule_set)"""
        urls = torrent.tracker_urls(self.client)
        confs = utils.match_tracker_confs(self.config.trackers, urls)
        refs = []
        for conf in confs:
            for ref in getattr(conf, "rules", []) or []:
                ref = str(ref).strip()
                if ref.startswith("@"):
                    refs.append(ref[1:])
        if refs:
            rules = self._resolve_refs(refs)
            if rules:
                return rules
        return []

    def _create_rule_task(self, rule: Rule, hash: str, tracker_conf: TrackerConfig) -> Task:
        """为种子创建单条规则任务(interval = 规则内置 interval, 到期执行该规则于该种子)"""
        return Task(
            "rule",
            rule.name,
            hash=hash,
            tracker_conf=tracker_conf,
            interval=rule.interval,
            handler=lambda t, d, r=rule: self._handle_rule(r, t, d),
        )

    def _handle_rule(self, rule: Rule, task: Task, dry_run: bool) -> bool:
        """种子级规则任务: 执行指定规则于该种子; 种子已删除返回 False 任务消亡"""
        ctx = RuleContext(self, self.client, self.config, task.hash, dry_run, task=task)
        try:
            handled, _stop = rule.process(ctx)
        except Exception as e:
            logger.warning(f"规则执行异常({rule.name} {task.hash}): {e}")
            return True
        return True

    # ---------- 规则: 便捷入口与 tracker 引用 ----------


# TODO: 删除
#     def process_torrent(self, hash, dry_run: bool) -> bool:
#         """直接处理单个种子(全部启用规则, 含 tracker rules 引用过滤)
#
#         任务队列驱动时请用种子级规则任务; 此入口用于向后兼容(测试/脚本直接调用)。
#         """
#         if not self.enabled_rules:
#             return False
#         ctx = RuleContext(self, self.client, self.config, hash, dry_run)
#         refs, force_continue = self._tracker_rule_refs(ctx)
#         if refs:
#             rules = self._resolve_refs(refs)
#             if not rules:
#                 return False
#         else:
#             rules = self.enabled_rules
#         handled = False
#         for rule in rules:
#             h, stop = rule.process(ctx)
#             if h:
#                 handled = True
#             if stop and not force_continue:
#                 break
#         return handled
#
#     def _tracker_rule_refs(self, ctx: RuleContext) -> tuple[list[str], bool]:
#         """收集种子匹配 tracker 的 rules 引用, 返回 (refs列表)"""
#         refs, force_continue = [], False
#         for conf in ctx.matched_tracker_confs():
#             for ref in getattr(conf, "rules", []) or []:
#                 ref = str(ref).strip()
#                 if ref == "ignore_next_rule_error: true":
#                     force_continue = True
#                 elif ref.startswith("@"):
#                     refs.append(ref[1:])
#         return refs, force_continue

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
