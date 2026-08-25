"""RuleManager: 统一管理所有规则插件, 维护状态持久化与上传量快照"""
import json
import logging
from datetime import date, datetime

from .base import Rule, RuleContext

logger = logging.getLogger("auto-qb.rules")

DEFAULT_STATE_FILE = "auto-qb-state.json"


class RuleManager:
    """统一管理所有规则插件

    - 从 config 的 `*_rules` 段加载规则集, 每条规则是一个 Rule 插件
    - 维护 state_file: 规则执行历史 / 上传量快照 / always_check_first_one 记录
    - process_torrent 按配置顺序执行规则, 支持 stop_following_rules_if
    """

    def __init__(self, config, state_file: str = None):
        self.config = config
        self.client = None  # 由 PTManager 连接后赋值
        self.state_file = (
            state_file or getattr(config, "state_file", None) or DEFAULT_STATE_FILE
        )
        self.state = self._load_state()

        self.rules = []
        rules_config = getattr(config, "rules_config", {}) or {}
        for group_name, group in rules_config.items():
            if not isinstance(group, dict):
                continue
            for rule_name, spec in group.items():
                self.rules.append(Rule(f"{group_name}.{rule_name}", spec, self))
        self.enabled_rules = [r for r in self.rules if r.enabled]
        if self.rules:
            logger.info(
                f"rules 框架: 加载 {len(self.rules)} 条规则, 启用 {len(self.enabled_rules)} 条"
            )

    # ---------- 每轮生命周期 ----------

    def begin_round(self, torrents):
        """每轮处理前调用: 维护上传量快照(每日/每周/每月), 周期切换时重建基线"""
        if not self.enabled_rules:
            return
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

    def upload_delta(self, torrent, kind: str) -> int:
        """周期上传增量: 当前 uploaded - 周期开始时快照, 下限 0(防种子重加/客户端重启归零)"""
        bucket = self.state.get("upload_snapshots", {}).get(kind, {})
        baseline = bucket.get("baseline", {})
        base = baseline.get(torrent.hash, 0)
        return max(0, torrent.uploaded - base)

    # ---------- 处理 ----------

    def process_torrent(self, torrent, dry_run: bool) -> bool:
        """处理单个种子. 返回 True 表示有规则执行了动作"""
        if not self.enabled_rules:
            return False
        ctx = RuleContext(self, self.client, self.config, torrent, dry_run)

        # 规则选择: 匹配的 tracker 若配置了 rules 引用则只用引用的规则, 否则用全部启用规则
        refs, force_continue = self._tracker_rule_refs(ctx)
        if refs:
            rules = self._resolve_refs(refs)
            if not rules:
                return False
        else:
            rules = self.enabled_rules

        handled = False
        for rule in rules:
            h, stop = rule.process(ctx)
            if h:
                handled = True
            # tracker 级 ignore_next_rule_error: true 时忽略所有规则的 stop_following_rules_if
            if stop and not force_continue:
                break
        if handled and not dry_run:
            self.save_state()
        return handled

    # ---------- tracker 规则引用 ----------

    def _tracker_rule_refs(self, ctx):
        """收集种子匹配 tracker 的 rules 引用, 返回 (refs列表, ignore_next_rule_error标志)"""
        refs, force_continue = [], False
        for conf in ctx.matched_tracker_confs():
            for ref in getattr(conf, "rules", []) or []:
                ref = str(ref).strip()
                if ref == "ignore_next_rule_error: true":
                    force_continue = True
                elif ref.startswith("@"):
                    refs.append(ref[1:])
        return refs, force_continue

    def _resolve_refs(self, refs) -> list:
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

    # ---------- 执行历史(去重) ----------

    def record_execution(self, rule_name: str, torrent_hash: str):
        now = datetime.now()
        history = self.state.setdefault("exec_history", {})
        history[f"{rule_name}:{torrent_hash}"] = {
            "ts": now.timestamp(),
            "date": now.date().isoformat(),
            "hour": now.hour,
        }

    def get_exec_record(self, rule_name: str, torrent_hash: str):
        return self.state.get("exec_history", {}).get(f"{rule_name}:{torrent_hash}")

    # ---------- 状态持久化 ----------

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
