"""状态持久化服务: state.json 读写的单点(plan kernel-module-refactor P0 从 RuleEngineMixin 迁出)

能力服务不是模块(plan §3.1): 无生命周期、无启用开关, 内核与模块共同消费 —— 规则执行历史、
跳检冷却、备份元数据、字段变化基线都落在这份 dict 上。QbManager 经委托方法保持旧调用面
(_load_state / save_state / _maybe_flush_state ...), 测试 31 处状态方法调用零改动。

!单一写线程约束不变(pitfalls/backend/concurrency.md): save / maybe_flush / record_execution
只在主循环线程调用; 服务自身无锁、无线程, 不引入绕开该假设的并发代码(黄金法则 5)。
"""
import json
import logging
import os
from datetime import datetime
from typing import Optional

from ..infra import utils
from ..infra.versioning import CURRENT_VERSIONS, migrate
from ..torrents import TorrentStore

logger = logging.getLogger(__name__)

# 哨兵: 状态文件"存在但内容不可用"(与"文件不存在"区分 —— 后者是首启, 属正常, 不该告警)
_CORRUPT = object()


class StateService:
    """state.json 的读写 / 迁移 / 周期落盘 / 执行历史, 一处收拢"""
    def __init__(self, state_file: str) -> None:
        self.state_file = state_file
        # 落盘载荷即运行期真相(QbManager.state 委托这里; 整体替换发生在启动加载, 见 load 调用方)
        self.data: dict = {}
        # 周期落盘到期点: run() 加载状态后重置为首个到期点(manager._next_state_flush_at 委托)
        self.next_flush_at: float = 0.0
        # 最近一次 load 发生的 schema 迁移描述("v1→v2"; 无迁移为空串) —— 供 run() 持锁后物化
        self.migration_desc: str = ""

    # ---------- 加载 / 迁移 ----------

    def load(self) -> dict:
        """加载状态; 主文件损坏时回退 `<state_file>.bak`(由 atomic_write 的 keep_backup 维护)

        - 主文件不存在: 首启, 静默返回 {}
        - 主文件损坏: 记 WARNING(损坏文件原样保留、不删) → 读到合法 .bak 即用(INFO 记录
          "用了备份"), 并把恢复出的内容**写回主文件**(自愈): 否则下次 save 会把损坏
          内容复制成新的 .bak, 把唯一一份好备份盖掉 —— 那等于这次恢复白做
        - 备份也不可用: 返回 {}(与修复前一致, 不阻塞启动, 但一路告警留痕)

        读回的 dict 一律过 schema 升级链(versioning.migrate, 计划 26-09-26-0506): 磁盘版本
        落后则在内存完成迁移, 描述记入 migration_desc 供 run() 持锁后物化落盘; 版本
        比程序新 / 非法值 -> SchemaVersionError 直接放出去 fail-fast —— **不算** _CORRUPT:
        版本问题不是内容损坏, 混进三态模型会触发错误的 .bak 回退(备份里也是同一个新版本)。
        """
        self.migration_desc = ""
        data = self._read_state_file(self.state_file)
        if data is not _CORRUPT:
            return self._migrate_state_dict(data if isinstance(data, dict) else {})

        bak_path = self.state_file + utils.BACKUP_SUFFIX
        logger.warning(f"状态文件损坏, 无法解析(原样保留待查, 不删除): {self.state_file}")
        bak = self._read_state_file(bak_path)
        if isinstance(bak, dict):
            logger.info(f"已用备份恢复状态: {bak_path}({len(bak)} 个键) —— 执行历史与跨日去重以备份为准")
            bak = self._migrate_state_dict(bak)
            self._write_back_recovered(bak)
            return bak
        logger.error(f"备份 {bak_path} 也不可用 -> 状态从空开始: 规则执行历史与跨日去重记录会丢失(同一天可能重复跳检)")
        return {}

    def _read_state_file(self, path: str):
        """读单个状态文件: dict(可用) / None(不存在) / _CORRUPT(存在但内容不是合法 dict)

        None 与 _CORRUPT 必须分开: 前者是首启(静默开始), 后者是损坏(要告警 + 回退备份),
        混为一谈正是"损坏时静默清空"的根因。UnicodeDecodeError 同样算损坏 —— 位翻转可能
        先坏掉编码而不是 JSON 语法。OSError(权限等)不在此吞: 那不是内容问题, 静默会掩盖
        真正的运行环境故障。
        """
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except FileNotFoundError:
            return None
        except (json.JSONDecodeError, UnicodeDecodeError):
            return _CORRUPT
        return data if isinstance(data, dict) else _CORRUPT

    def _migrate_state_dict(self, data: dict) -> dict:
        """加载出的状态过 schema 升级链; 迁移描述记入 migration_desc(供物化点与测试)

        空 dict(首启 / 非 dict JSON 兜底)直接原样返回: 无内容可迁移, 若走链会被盖章成
        "已迁移", 诱发首启无意义落盘, 也破坏"首启静默返回 {}"语义。
        """
        if not data:
            return data
        data, desc = migrate("state", data)
        if desc:
            self.migration_desc = desc
            logger.debug(f"state.json schema 已迁移 {desc}(内存生效)")
        return data

    def _state_write_payload(self, data: dict) -> dict:
        """落盘载荷: 顶部盖 schema_version 章(不改内存真相) —— save / _write_back_recovered 共用"""
        return {**data, "schema_version": CURRENT_VERSIONS["state"]}

    def _write_back_recovered(self, data: dict) -> None:
        """把从备份恢复出的状态写回主文件(**不带** keep_backup: 免得把损坏内容复制成新的 .bak)

        自愈失败只告警、不阻断启动: 内存里已是恢复出的状态, 下次正常落盘同样能修好主文件。
        写回载荷盖 schema_version 章(备份与主文件同版本, 盖章让恢复出的文件即刻带上版本标记)。
        """
        try:
            utils.atomic_write(
                self.state_file, lambda f: json.dump(self._state_write_payload(data), f, ensure_ascii=False, indent=2)
            )
        except OSError as e:
            logger.warning(f"把备份状态写回 {self.state_file} 失败(不阻断启动, 下次落盘会再试): {e}")

    def cleanup_orphan_tmp(self) -> None:
        """清理 atomic_write 遗留的孤儿临时文件 `<state_file>.<随机>.tmp`

        atomic_write 只清**自己**的异常路径; 崩溃落在 mkstemp 与 os.replace 之间时临时文件就留在盘上,
        启动又没人清 ⇒ 每崩一次留一个, 久了状态目录里堆一片。
        **判据 = 持锁后才清**: 持锁 ⇒ 没有别的实例在写, 同目录里任何匹配文件都是上次崩溃的遗留;
        未持锁的只读模式(`--export-yaml` 等)根本不调用本方法(见 `QbManager.__init__`)。
        只认 `<state_file>.<随机>.tmp` 这一个形状 —— `.bak` 与别人的 `.tmp` 一概不碰; 删除失败只告警。
        """
        directory = os.path.dirname(os.path.abspath(self.state_file))
        prefix = os.path.basename(self.state_file) + "."
        suffix = utils.TMP_SUFFIX
        try:
            names = os.listdir(directory)
        except OSError as e:
            logger.warning(f"无法列出状态目录(跳过孤儿临时文件清理): {directory} - {e}")
            return
        removed = 0
        for name in names:
            # 空随机段(如 `state.json..tmp`)不是 mkstemp 的产物 —— 不碰, 免得误删别人的文件
            if not (name.startswith(prefix) and name.endswith(suffix)) or len(name) <= len(prefix) + len(suffix):
                continue
            try:
                os.remove(os.path.join(directory, name))
                removed += 1
            except OSError as e:
                logger.warning(f"删除孤儿临时文件失败(跳过): {name} - {e}")
        if removed:
            logger.info(f"清理 {removed} 个孤儿临时文件: {prefix}*{suffix}")

    # ---------- 落盘 ----------

    def save(self) -> None:
        """落盘状态文件: 原子写(tmp + os.replace)并保留一份 .bak

        原实现 `open(path, "w")` 会先 truncate: 写盘途中进程被杀 / 磁盘满 ⇒ state.json 变成半截
        文件, 而 state 没有备份 ⇒ 执行历史(exec_history)与跨日去重(skip_check_day)全丢, 重启后
        规则重放(同一天可能对同一种子重复跳检)。原子写保证目标文件"要么全旧、要么全新",
        .bak 再兜一层"新内容本身写错了"的情况。写前盖 schema_version 章(见 _state_write_payload)。
        """
        try:
            utils.atomic_write(
                self.state_file,
                lambda f: json.dump(self._state_write_payload(self.data), f, ensure_ascii=False, indent=2),
                keep_backup=True,
            )
        except OSError as e:
            logger.error(f"保存状态文件失败: {e}")

    def materialize_migration(self, dry_run: bool) -> None:
        """启动序列的迁移物化: 磁盘状态文件版本 < CURRENT 时立即落盘一次新版本(计划 26-09-26-0506)

        调用点在 run() 内 —— 只在**已持锁**后执行(与 cleanup_orphan_tmp 同判据: 持锁 ⇒ 没有
        别的实例在写); __init__ 的早期加载只做内存迁移、不落盘(未持锁写盘违背单一写线程判据)。
        dry-run 不落盘(与退出路径 `if not dry_run` 口径一致), 只留 INFO 说明内存已迁移。
        幂等性: 迁移链的输入是磁盘上的真实版本, 落盘前崩溃则文件保持旧版本完整内容,
        下次启动从旧版本重放同一条链(黄金法则 1)。
        """
        if not self.migration_desc:
            return
        if dry_run:
            logger.info(f"state.json schema 已迁移 {self.migration_desc}(dry-run 仅内存生效, 不落盘)")
            return
        logger.info(f"state.json schema 已迁移 {self.migration_desc}, 物化落盘")
        self.save()

    def maybe_flush(self, now: float, interval: float) -> None:
        """周期落盘(仅主循环线程调用): 把非优雅终止的状态丢失窗口压到 state_save_interval 以内

        save 原本仅优雅退出可达 —— taskkill /F / 原生崩溃 / 断电不产生 Python 异常,
        run() 的 finally 永不执行, 整个运行期的执行历史与去重记录全丢(issue 26-09-21-1347)。
        主循环每轮到期检查一次: 间隔读 state_save_interval(0 = 关闭, 回到仅退出落盘的旧行为;
        配置端下限 30s 防误配置写放大), 状态真实变更频率为小时~天级, 分钟级小文件写盘的
        写放大可忽略(生产实测 state.json ~37KB)。
        !interval 由调用方每调用现读传入(热重载 L0 语义: 改间隔即刻生效), 服务自身不持配置。
        刻意不做写点级 dirty 插桩: state 写点散在多个模块/动作文件, 逐点插桩必漏,
        周期兜底对未来新增写点同样生效。单一写线程约束不变 —— 本方法只在主循环线程跑。
        """
        if interval <= 0:
            return
        if now >= self.next_flush_at:
            self.save()
            self.next_flush_at = now + interval

    # ---------- 执行历史(规则去重依据) ----------

    def record_execution(self, rule_name: str, hash: str) -> None:
        """记录规则执行历史(execute_once/cooldown 去重依据); 仅主循环线程调用, 线程安全"""
        now = datetime.now()
        history = self.data.setdefault("exec_history", {})
        history[f"{rule_name}:{hash}"] = {
            "ts": now.timestamp(),
            "date": now.date().isoformat(),
            "hour": now.hour,
        }

    def get_exec_record(self, rule_name: str, hash: str) -> Optional[dict]:
        return self.data.get("exec_history", {}).get(f"{rule_name}:{hash}")

    # ---------- 字段变化基线 ----------

    def bind_field_snapshots(self, store: TorrentStore) -> None:
        """把 store.field_snapshots 绑定到 state 顶层键(同一对象)

        store 的 update_field_snapshots 原地更新该 dict —— 原地改即落盘内容, 不需要
        每次落盘前回拷。每次 self.data 被整体替换(启动加载)后必须重新绑定。
        """
        store.field_snapshots = self.data.setdefault("field_snapshots", {})


__all__ = ["StateService"]
