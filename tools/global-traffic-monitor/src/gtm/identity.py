"""正主注册与让位判定 (计划 26-10-20-1316 §03, 工具侧身份层).

同机多个 gtm 安装 (auto-qb A/B 各带一份) 共用一个用户级指针目录: 谁握笔写
数据必须定死, 否则工具死亡后先启动的一方拉起自己那份安装、占领指针与数据
落点, 两份数据不互通。本模块把「谁是正主」变成机器级显式事实:

三处 ID (文件名同为 tool-id; uuid; 不跨机有意义):
  - 安装目录 <install>/tool-id      : 我是谁 (先于数据可读, 定引导顺序)
  - 指针目录 primary.json           : 机器注册的正主 {schema, id, install_path,
                                      data_dir(信息位), version(信息位)}
  - 数据目录 <data>/tool-id         : 这份数据归谁写 (版本血统防线)

启动判定矩阵 (cmd_run 在取单实例锁/绑端口/解析数据目录之前调用):
  ① 无记录      -> O_EXCL 原子认领 -> 正主路径
  ② id 同 path同 -> 正主路径
  ③ id 同 path异 -> 拒绝启动 (拷贝件 / 安装被移动) + 写注记, 人工改记录重认
  ④ id 异        -> 记录自洽校验 -> 自洽: 代拉正主后立即退出; 矛盾: 写注记退出

设计纪律 (与指针/锁同族):
  - 认领用 O_EXCL 建文件本身做原子占位 (非 tmp+replace —— replace 会互相覆盖);
    此后记录零自动刷新 (移动/易主/归并全部人工, 计划 D3); 唯一例外是正主启动
    时补写为空的 data_dir 信息位 (不削弱 ③: 被 ③ 拒绝的进程走不到写文件那步)。
  - 记录/注记损坏或 schema 未知 -> 一律按「无记录/矛盾」降级并 WARNING, 不猜
    字段 (照 ENDPOINT_SCHEMA 旧例); 永不死锁、不静默。
  - 镜像常量: 文件名与 schema 版本 auto-qb 侧 (core/traffic_source/agent.py)
    各持一份同值 —— 工具是独立包, auto-qb 不 import 它。
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import sys
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from gtm import __version__
from gtm.storage import atomic_write_text, pointer_dir, resolve_tool_root

logger = logging.getLogger("gtm.identity")

#: 记录文件 (指针目录): 机器注册的正主, 只此一份
PRIMARY_FILE_NAME = "primary.json"
#: 注记文件 (指针目录): 让位/被拒时书写, 正主启动或 claim 成功时由权威方清除
DEFERRED_FILE_NAME = "deferred.json"
#: ID 文件名 (安装目录与数据目录同名): 我是谁 / 这份数据归谁
ID_FILE_NAME = "tool-id"
#: 记录 schema 版本: 读到未知值只告警按无记录处理, 不猜字段 (指针同族纪律)
PRIMARY_SCHEMA = 1
#: 注记 schema 版本 (同上)
DEFERRED_SCHEMA = 1
#: claim 启动器文件名 (D4/D19): 安装内第二启动器, 零参数人工易主通道 (claim 子命令)
CLAIM_LAUNCHER_WINDOWS = "claim.cmd"
CLAIM_LAUNCHER_POSIX = "claim.sh"


class IdentityError(RuntimeError):
    """身份层不可用 (install-id 落盘失败 / 记录存在但无法解析): 启动 fail-fast."""


class PrimaryRecordExists(RuntimeError):
    """并发认领竞争: 另一进程抢先 O_EXCL 建了记录 (输家按赢家记录重新判定)."""


@dataclass(frozen=True)
class Identity:
    """本安装的身份: 安装根 (realpath) + 安装 ID."""

    install_root: str
    install_id: str


@dataclass(frozen=True)
class PrimaryRecord:
    """机器注册的正主: id + install_path (realpath) + data_dir (信息位)."""

    id: str
    install_path: str
    data_dir: str = ""
    version: str = ""


@dataclass(frozen=True)
class DeferredNote:
    """让位/被拒注记: 谁让位、代拉目标、结论、时间 (auto-qb 只读展示)."""

    reason: str
    from_install: str
    target_install: str = ""
    target_id: str = ""
    detail: str = ""


# ---------------- 路径单点 (测试按需 monkeypatch 重定向) ----------------

def install_id_file() -> str:
    """本安装 ID 文件路径: <install_root>/tool-id (resolve_tool_root 单点)."""
    return os.path.join(resolve_tool_root(), ID_FILE_NAME)


def data_id_file(data_dir: str) -> str:
    """数据归属 ID 文件路径: <data_dir>/tool-id."""
    return os.path.join(data_dir, ID_FILE_NAME)


def primary_path() -> str:
    """正主记录路径: 指针目录/primary.json (与 endpoint.json 同址, 用户级)."""
    return os.path.join(pointer_dir(), PRIMARY_FILE_NAME)


def deferred_path() -> str:
    """注记路径: 指针目录/deferred.json."""
    return os.path.join(pointer_dir(), DEFERRED_FILE_NAME)


# ---------------- 安装 ID: 生成 / 加载 ----------------

def load_or_create_install_id() -> Identity:
    """加载本安装 ID; 缺失 -> 生成 uuid4 并原子落盘 (幂等: 已有原样加载).

    落盘失败 (安装目录只读等) -> IdentityError: 没有持久身份的安装每次启动都是
    新身份, 会让正主判定随机漂移, 必须 fail-fast 而不是静默用内存值。
    """
    root = os.path.realpath(resolve_tool_root())
    path = install_id_file()
    try:
        with open(path, "r", encoding="utf-8") as f:
            existing = f.read().strip()
    except FileNotFoundError:
        existing = ""
    except OSError as e:
        raise IdentityError(f"读取安装 ID 失败 ({path}): {e}") from e
    if existing:
        return Identity(install_root=root, install_id=existing)
    new_id = uuid.uuid4().hex
    try:
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        atomic_write_text(path, new_id + "\n")
    except OSError as e:
        raise IdentityError(
            f"安装 ID 落盘失败 ({path}): {e} —— 安装目录不可写? 没有持久身份的安装"
            "无法参与正主判定, 请修复安装目录权限后重试"
        ) from e
    logger.info("已生成本安装 ID (%s): %s", path, new_id)
    return Identity(install_root=root, install_id=new_id)


def read_id_file(path: str) -> Optional[str]:
    """读任意 ID 文件 (安装或数据); 缺失 -> None, 读失败只告警按缺失处理."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            value = f.read().strip()
    except FileNotFoundError:
        return None
    except OSError as e:
        logger.warning("读取 ID 文件失败 (%s): %s", path, e)
        return None
    return value or None


# ---------------- 正主记录: 读 / 认领 / 补写 ----------------

def read_primary() -> Optional[PrimaryRecord]:
    """读 primary.json; 缺失 -> None, 坏 JSON/schema 未知/关键字段缺 -> None + WARNING.

    一律按「无记录」降级 (调用方走认领分支); 认领的 O_EXCL 会在记录真实存在时
    抛 PrimaryRecordExists, 由那里转入「记录不可解析」的人工处置, 不会死循环。
    """
    path = primary_path()
    try:
        with open(path, "r", encoding="utf-8") as f:
            payload = json.load(f)
    except FileNotFoundError:
        return None
    except (OSError, ValueError) as e:
        logger.warning("正主记录读取失败 (%s): %s —— 按无记录处理", path, e)
        return None
    if not isinstance(payload, dict):
        logger.warning("正主记录格式非法 (顶层非对象, %s) —— 按无记录处理", path)
        return None
    schema = payload.get("schema")
    if schema != PRIMARY_SCHEMA:
        logger.warning("正主记录 schema 非预期 (读到 %r, 期望 %d, %s) —— 不猜字段, 按无记录处理", schema, PRIMARY_SCHEMA, path)
        return None
    record_id = str(payload.get("id") or "").strip()
    install_path = str(payload.get("install_path") or "").strip()
    if not record_id or not install_path:
        logger.warning("正主记录缺关键字段 (id/install_path, %s) —— 按无记录处理", path)
        return None
    return PrimaryRecord(
        id=record_id,
        install_path=os.path.realpath(install_path),
        data_dir=str(payload.get("data_dir") or ""),
        version=str(payload.get("version") or ""),
    )


def claim_primary(identity: Identity, *, data_dir: str = "", version: str = "") -> PrimaryRecord:
    """O_EXCL 原子认领: 记录不存在才建; 已存在 -> PrimaryRecordExists (输家重判).

    不用 tmp+replace: replace 会让并发认领互相覆盖, O_EXCL 建文件本身就是
    不可分割的占位动作。data_dir 由正主启动时补写 (fill_primary_data_dir)。
    """
    path = primary_path()
    record = PrimaryRecord(
        id=identity.install_id,
        install_path=identity.install_root,
        data_dir=data_dir,
        version=version or __version__,
    )
    payload = {
        "schema": PRIMARY_SCHEMA,
        "id": record.id,
        "install_path": record.install_path,
        "data_dir": record.data_dir,
        "version": record.version,
    }
    try:
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
                f.flush()
                os.fsync(f.fileno())
        except BaseException:
            os.remove(path)  # 认领写半途失败: 撤掉占位, 不留坏记录挡后来者
            raise
    except FileExistsError as e:
        raise PrimaryRecordExists(f"正主记录已被并发认领 ({path})") from e
    except OSError as e:
        raise IdentityError(f"正主记录认领失败 ({path}): {e}") from e
    logger.info("已认领正主注册: id=%s install=%s (%s)", record.id, record.install_path, path)
    return record


def write_primary(record: PrimaryRecord) -> None:
    """原子重写正主记录 (claim 子命令用; 常规启动零自动刷新, D3)."""
    payload = {
        "schema": PRIMARY_SCHEMA,
        "id": record.id,
        "install_path": record.install_path,
        "data_dir": record.data_dir,
        "version": record.version,
    }
    atomic_write_text(primary_path(), json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n")


def fill_primary_data_dir(identity: Identity, data_dir: str) -> None:
    """正主启动时补写记录里为空的 data_dir 信息位 (仅此一个自动写点, D3).

    仅当记录 id == 自己且 data_dir 为空时才写; 读-改写之间记录被换 (并发 claim)
    的风险由再读判定兜底: 重读后不是「自己的空记录」就不写。非空/非己不动。
    """
    record = read_primary()
    if record is None or record.id != identity.install_id or record.data_dir:
        return
    try:
        write_primary(
            PrimaryRecord(id=record.id, install_path=record.install_path, data_dir=data_dir, version=record.version)
        )
    except OSError as e:
        logger.warning("补写正主记录 data_dir 失败 (忽略, 信息位而已): %s", e)


# ---------------- 数据归属: 写前校验 (版本血统防线) ----------------

def ensure_data_ownership(data_dir: str, identity: Identity) -> None:
    """校验/认领数据归属: <data_dir>/tool-id 缺失 -> 写入本安装 id; 相同 -> 过;
    不同 -> IdentityError (该数据属于其它安装, 拒绝跨版本接管).

    调用方须保证 data_dir 已存在 (由 _resolve_data_dir 的 makedirs/搬迁保证)。
    """
    path = data_id_file(data_dir)
    existing = read_id_file(path)
    if existing is None:
        try:
            atomic_write_text(path, identity.install_id + "\n")
        except OSError as e:
            raise IdentityError(f"数据归属 ID 落盘失败 ({path}): {e}") from e
        logger.info("已认领数据归属: %s -> id=%s", path, identity.install_id)
        return
    if existing != identity.install_id:
        raise IdentityError(
            f"拒绝写入: 数据目录 {data_dir} 属于其它安装 (tool-id={existing}, 本安装 {identity.install_id})"
            " —— 跨版本接管需人工: 停工具, 确认版本兼容后删除该 tool-id 再启动, 或改用 env/--data-dir 另指目录"
        )


# ---------------- 注记: 写 / 清除 (auto-qb 只读展示) ----------------

def write_deferred(note: DeferredNote) -> None:
    """写让位/被拒注记 (原子; 失败只 WARNING —— 注记是可见性便利, 不阻断让位)."""
    payload = {
        "schema": DEFERRED_SCHEMA,
        "version": __version__,
        "reason": note.reason,
        "from_install": note.from_install,
        "target_install": note.target_install,
        "target_id": note.target_id,
        "detail": note.detail,
        "at": datetime.now().astimezone().isoformat(timespec="seconds"),
    }
    try:
        os.makedirs(os.path.dirname(os.path.abspath(deferred_path())), exist_ok=True)
        atomic_write_text(deferred_path(), json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    except OSError as e:
        logger.warning("让位注记写入失败 (忽略, 不影响让位动作): %s", e)


def clear_deferred() -> None:
    """清除注记 (幂等): 正主成功启动 / claim 成功 —— 权威时刻由调用方负责."""
    try:
        os.remove(deferred_path())
    except FileNotFoundError:
        pass
    except OSError as e:
        logger.warning("让位注记删除失败 (忽略): %s", e)


# ---------------- 启动判定矩阵 ----------------

@dataclass(frozen=True)
class Decision:
    """一次启动判定的结论: kind + 依据记录 + 人读说明."""

    kind: str  # "primary" (含认领成功) / "refuse" / "relay"
    record: Optional[PrimaryRecord]
    message: str


def evaluate_startup(identity: Identity) -> Decision:
    """按 primary.json 判定本安装该走哪条路 (矩阵 ①②③④, 不动任何状态).

    ③ 拒绝项覆盖「拷贝件」与「安装被移动」两个场景: id 同 (数据认得出我) 但
    path 异 (记录的安装根不是我) —— 放行拷贝件会让两份同 id 数据静默分叉。
    """
    record = read_primary()
    if record is None:
        return Decision("claim", None, "无正主记录, 本安装尝试认领")
    if record.id != identity.install_id:
        return _evaluate_relay(identity, record)
    if record.install_path != identity.install_root:
        return Decision(
            "refuse",
            record,
            f"拒绝启动: 本安装与注册正主 ID 相同但安装路径不同 (记录 install_path={record.install_path},"
            f" 本安装 {identity.install_root}) —— 疑似拷贝件, 或本安装被移动过。人工处置: 编辑 {primary_path()}"
            " 修正 install_path, 或删除该记录后重启本安装重新认领",
        )
    return Decision("primary", record, "本安装即注册正主")


def _evaluate_relay(identity: Identity, record: PrimaryRecord) -> Decision:
    """④ 让位分支: 先做记录自洽校验, 自洽才代拉 (矛盾则写注记退出).

    矛盾两种: 记录指向的安装根就是本安装 (记录说我不是我, 自相矛盾); 记录指向
    的安装目录里已有 tool-id 且与记录 id 不符 (记录张冠李戴)。代拉一个坏目标
    只会把两个安装绕进互拉死循环, 所以矛盾时拒绝代拉、交人工。
    """
    if record.install_path == identity.install_root:
        return Decision(
            "refuse",
            record,
            f"拒绝启动: 正主记录的 install_path 指向本安装, 但记录的 id 与本安装不符"
            f" (记录 id={record.id}, 本安装 {identity.install_id}) —— 记录自相矛盾, 请人工检查 {primary_path()}",
        )
    target_id = read_id_file(os.path.join(record.install_path, ID_FILE_NAME))
    if target_id is not None and target_id != record.id:
        return Decision(
            "refuse",
            record,
            f"拒绝代拉: 记录指向 {record.install_path}, 但该安装的 tool-id ({target_id}) 与记录 id"
            f" ({record.id}) 不符 —— 记录自相矛盾, 请人工检查 {primary_path()}",
        )
    return Decision(
        "relay",
        record,
        f"已让位: 注册正主是另一安装 ({record.install_path}), 本安装不写任何数据, 尝试代拉正主后退出",
    )


def _spawn(args: list, **kwargs) -> None:
    """detached 拉起的可注入单点 (生产走真 Popen; 测试替换本函数).

    窗口形态与 auto-qb agent.launch_tool 同口径: Windows CREATE_NO_WINDOW (无窗口
    控制台, 不与调用方共享控制台 —— 关掉谁都不连带谁), POSIX start_new_session。
    """
    kwargs.setdefault("stdin", subprocess.DEVNULL)
    kwargs.setdefault("stdout", subprocess.DEVNULL)
    kwargs.setdefault("stderr", subprocess.DEVNULL)
    kwargs.setdefault("close_fds", True)
    if sys.platform.startswith("win"):
        kwargs["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
    else:
        kwargs["start_new_session"] = True
    subprocess.Popen(args, **kwargs)


def relay_launch(install_root: str) -> Optional[str]:
    """代拉正主: 执行记录指向安装根下的 D19 启动器 (零参数, 意图在脚本里).

    返回启动器路径 (只表示「已尝试」, 就绪判据是探活, 不看退出码 —— detached
    拿不到); 启动器缺失 -> None (调用方照常写注记退出, 原因进 auto-qb 状态区)。
    """
    launcher = os.path.join(install_root, "launch.cmd" if sys.platform.startswith("win") else "launch.sh")
    if not os.path.isfile(launcher):
        logger.warning("代拉失败: 未找到正主启动器 %s", launcher)
        return None
    if sys.platform.startswith("win"):
        args = ["cmd.exe", "/c", launcher]
    else:
        args = ["/bin/sh", launcher]
    try:
        _spawn(args, cwd=install_root)
    except OSError as e:
        logger.warning("代拉启动正主失败 (%s): %s", launcher, e)
        return None
    logger.info("已代拉正主安装: %s", launcher)
    return launcher


def resolve_startup(identity: Identity) -> Decision:
    """cmd_run 的启动判定入口: 矩阵判定 + 认领 (含并发输家重判).

    认领竞争: 并发首启的输家拿到 PrimaryRecordExists, 按赢家的记录重新判定
    (多半转 ④ 让位); 若重新判定仍是「无记录」态, 说明记录文件存在但解析不出
    来 (schema 未知/损坏/缺字段) —— 不覆盖不猜, IdentityError 交人工。
    """
    decision = evaluate_startup(identity)
    if decision.kind != "claim":
        return decision
    try:
        record = claim_primary(identity)
    except PrimaryRecordExists:
        decision = evaluate_startup(identity)
        if decision.kind == "claim":
            raise IdentityError(
                "正主记录存在但无法解析 (schema 未知 / 损坏 / 缺关键字段) —— 不覆盖、不猜字段, "
                f"请人工检查或删除 {primary_path()} 后重启"
            )
        return decision
    return Decision("primary", record, "已认领正主注册, 本安装为正主")



