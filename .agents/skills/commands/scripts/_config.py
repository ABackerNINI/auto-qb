"""包树的加载 / 校验 / 占位符展开。

引擎只认识两样东西: 「包」与「命令」。本模块**唯一读**的文件是 `<包>/config.toml` ——
包里还有什么(私有配置 / 说明 / 别的脚本), 引擎不读、不扫描、不知道它们存在。

schema 只有三块, 且都只描述**结构**, 不描述"我们在做什么事":

    [pack]          包自己: 叫什么 / 管什么事 / 是否启用 / 脚本目录 / 是否已确认
    [packs.<名>]    本包由哪些子包组成, 各自是否启用
    [tasks.<id>]    一条命令: 怎么跑 / 何时用 / 是否常显

凡是含义依赖"我们在做什么事"的键, 一律不属于这里 —— 它们该待在包自己的私有配置里,
由包的脚本自读。这样引擎才能对任何仓库、任何命令都成立。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

try:
    import tomllib  # Python 3.11+
except ModuleNotFoundError:  # pragma: no cover
    tomllib = None  # type: ignore[assignment]

CONFIG_NAME = "config.toml"
PACKS_DIRNAME = ".commands"
PACK_ENV = "COMMAND_FLOW_PACK_DIR"  # 调包脚本时注入: 本包目录(让脚本自己找自己的配置)

# 三块 schema 各自允许的键。块内出现其它键一律 STOP ——
# 拼错的键会**静默失效**(你以为配了, 其实没生效, 输出里连痕迹都没有),
# 那比直接报错坏得多。付的价钱: 新增键必须先加进这里。
PACK_KEYS = {"name", "when", "enabled", "version", "origin", "scripts_dir", "confirmed"}
SUBPACK_KEYS = {"enabled"}
TASK_KEYS = {"run", "script", "args", "when", "note", "timeout", "requires", "risky", "pin"}

DEFAULT_TIMEOUT = 600
MAX_DEPTH = 8  # 层级上限: 套得太深会让人下钻到迷路
MAX_PIN_PER_LEVEL = 8  # 一层视图里能浮出的常显命令上限 —— pin 是稀缺资源(见 _pin_warnings)

# `<skill-dir:NAME>` 的候选位置 —— 按此顺序找, 第一个存在的即命中。
SKILL_DIR_CANDIDATES = (
    ".agents/skills/{name}",
    ".codebuddy/skills/{name}",
    "~/.workbuddy-ai/skills/{name}",
    "~/.codebuddy/skills/{name}",
)

_PLACEHOLDER = re.compile(r"<([^<>\s]+)>")


class ConfigError(RuntimeError):
    """配置写错 / 展不开 —— 调用方应打印本异常文案并停手(退出码 1), 不静默降级。"""


# ------------------------------------------------------------------ 数据模型


@dataclass
class Task:
    """一条命令。`run` 与 `script` 二选一: 前者是命令行, 后者指向包内的脚本。"""

    id: str
    pack_path: str  # 所属包路径, 顶级为包名, 子包为 "<父>/<子>"
    run: list[str] = field(default_factory=list)
    script: str = ""
    args: list[str] = field(default_factory=list)
    when: str = ""
    note: str = ""
    timeout: int = DEFAULT_TIMEOUT
    requires: list[str] = field(default_factory=list)
    risky: bool = False
    pin: bool = False
    scripts_dir: Path | None = None  # 脚本所在目录(继承而来)

    @property
    def kind(self) -> str:
        return "script" if self.script else "run"


@dataclass
class Pack:
    """一个包。包是**复用单位**: 整包复制即可带走, 连它自己的私有配置一起。"""

    name: str
    path: str  # 树中路径, 顶级为包名, 子包为 "父/子"
    dir: Path
    when: str = ""
    enabled: bool = True
    version: str = ""
    origin: str = ""
    scripts_dir: Path | None = None
    tasks: dict[str, Task] = field(default_factory=dict)
    subs: dict[str, Pack] = field(default_factory=dict)


@dataclass
class Tree:
    root: Path
    packs: dict[str, Pack]  # 仅顶级
    tasks: dict[str, Task]  # 全树, id 唯一
    warnings: list[str] = field(default_factory=list)


# ------------------------------------------------------------------ 定位


def find_root(start: Path | None = None) -> Path:
    """仓库根: 从 start(默认本文件)向上找 `.git`(目录或 worktree 的 .git 文件)。"""
    cur = (start or Path(__file__).resolve()).resolve()
    if cur.is_file():
        cur = cur.parent
    for parent in (cur, *cur.parents):
        if (parent / ".git").exists():
            return parent
    raise ConfigError(f"[STOP] 找不到仓库根: 从 {cur} 向上没有 .git")


def find_skill_dir(name: str, root: Path | None = None) -> Path | None:
    """定位 skill 目录: 项目级 → 用户级; 都找不到返回 None(由调用方转 STOP)。

    **不猜**: 找不到就交给调用方停手, 而不是降级成"打印给人" —— 降级意味着
    "看起来跑过了", 那比报错坏得多。
    """
    base = Path(root or find_root())
    for tpl in SKILL_DIR_CANDIDATES:
        cand = Path(tpl.format(name=name)).expanduser()
        if not cand.is_absolute():
            cand = base / cand
        if cand.is_dir():
            return cand
    return None


# ------------------------------------------------------------------ 加载


def _read_toml(path: Path) -> dict:
    if tomllib is None:
        raise ConfigError("[STOP] 需要 Python 3.11+ 的 tomllib 才能读取 " + CONFIG_NAME)
    try:
        return tomllib.loads(path.read_text(encoding="utf-8"))
    except ValueError as exc:
        raise ConfigError(f"[STOP] {path} 不是合法 TOML: {exc}") from exc


def load_tree(root: Path | None = None) -> Tree:
    """扫描 `.commands/` 下的包树, 全量校验后返回; 任一项不合规则抛 `ConfigError`。"""
    root = Path(root or find_root()).resolve()
    base = root / PACKS_DIRNAME
    if not base.is_dir():
        raise ConfigError(f"[STOP] 缺少配置目录: {base}\n"
                          f"命令一律放在包里 —— 在 {PACKS_DIRNAME}/<包名>/ 下建 {CONFIG_NAME}。")

    tree = Tree(root=root, packs={}, tasks={})
    for entry in sorted(base.iterdir()):
        if not entry.is_dir():
            continue
        cfg = entry / CONFIG_NAME
        if not cfg.exists():
            tree.warnings.append(f"{entry.name}/ 下没有 {CONFIG_NAME} —— 不是包, 已跳过")
            continue
        pack = _load_pack(cfg, entry, tree, parent=None, enabled=True, depth=1)
        tree.packs[pack.name] = pack
    if not tree.packs:
        raise ConfigError(f"[STOP] {base} 下没有任何包")
    tree.warnings.extend(_pin_warnings(tree))
    return tree


def _pin_warnings(tree: Tree) -> list[str]:
    """每层视图里浮出的常显命令过多 → WARN。

    视图规则: 一层 = 本级包自己的命令 + **各子包标了 pin 的命令**(浮一级)。所以 pin 一多,
    这一层就变回一张平表 —— 与"不臃肿靠分层"的初衷相抵。这是纪律问题不是结构错误, 故 WARN 不 STOP。
    """
    out: list[str] = []
    stack: list[tuple[str, dict[str, Pack]]] = [("(一级)", tree.packs)]
    while stack:
        where, subs = stack.pop()
        pinned = [t.id for sub in subs.values() if sub.enabled for t in sub.tasks.values() if t.pin]
        if len(pinned) > MAX_PIN_PER_LEVEL:
            out.append(
                f"{where} 视图浮出 {len(pinned)} 条常显命令(上限 {MAX_PIN_PER_LEVEL}): "
                "pin 只给「每次会话都要用」的命令 —— 滥用等于把平表搬回一级"
            )
        stack += [(pack.path, pack.subs) for pack in subs.values() if pack.subs]
    return out


def _load_pack(cfg_path: Path, pack_dir: Path, tree: Tree, parent: Pack | None, enabled: bool, depth: int) -> Pack:
    if depth > MAX_DEPTH:
        raise ConfigError(f"[STOP] 包层级超过 {MAX_DEPTH} 层: {pack_dir}")
    data = _read_toml(cfg_path)

    # 顶层未知键只 WARN: 它可能正是包私有配置的残留(引擎本就不该认识它)。
    for key in sorted(set(data) - {"pack", "packs", "tasks"}):
        tree.warnings.append(f"{pack_dir.name}: 顶层未知键 `{key}`(引擎不认识, 若为包私有配置请移出本文件)")

    raw_pack = data.get("pack")
    if not isinstance(raw_pack, dict):
        raise ConfigError(f"[STOP] {cfg_path} 缺 [pack] 段")
    _check_keys(raw_pack, PACK_KEYS, f"[pack] @ {cfg_path}")

    name = raw_pack.get("name")
    if name != pack_dir.name:
        raise ConfigError(
            f"[STOP] {cfg_path}: [pack].name = {name!r} 与目录名 {pack_dir.name!r} 不一致"
            " —— 两处名字各写一份, 迟早会漂移"
        )
    if not raw_pack.get("confirmed"):
        raise ConfigError(f"[STOP] {cfg_path}: [pack].confirmed 缺失或为 false"
                          " —— 包是复用单位, 拷过来的包往往没核对过, 逐项确认后改为 true")

    scripts_name = raw_pack.get("scripts_dir") or ("scripts" if parent is None else None)
    if scripts_name:
        scripts_dir = pack_dir / scripts_name
    elif parent is not None:
        scripts_dir = parent.scripts_dir
    else:
        scripts_dir = pack_dir / "scripts"

    pack = Pack(
        name=str(name),
        path=pack_dir.name if parent is None else f"{parent.path}/{pack_dir.name}",
        dir=pack_dir,
        when=str(raw_pack.get("when", "")),
        enabled=bool(raw_pack.get("enabled", True)) if parent is None else enabled,
        version=str(raw_pack.get("version", "")),
        origin=str(raw_pack.get("origin", "")),
        scripts_dir=scripts_dir,
    )

    for tid, raw in sorted((data.get("tasks") or {}).items()):
        task = _load_task(tid, raw, pack, cfg_path)
        if task.id in tree.tasks:
            raise ConfigError(
                f"[STOP] task id 重复: {task.id}"
                f"({tree.tasks[task.id].pack_path} 与 {pack.path}) —— run 要能全局直达, 重名会让"
                "「调的是哪个」不可知"
            )
        tree.tasks[task.id] = task
        pack.tasks[task.id] = task

    for sub_name, raw in sorted((data.get("packs") or {}).items()):
        if not isinstance(raw, dict):
            raise ConfigError(f"[STOP] {cfg_path}: [packs.{sub_name}] 必须是个表")
        _check_keys(raw, SUBPACK_KEYS, f"[packs.{sub_name}] @ {cfg_path}")
        sub_dir = pack_dir / sub_name
        sub_cfg = sub_dir / CONFIG_NAME
        if not sub_cfg.exists():
            raise ConfigError(f"[STOP] {cfg_path} 注册了子包 {sub_name}, 但 {sub_cfg} 不存在")
        sub = _load_pack(sub_cfg, sub_dir, tree, parent=pack, enabled=bool(raw.get("enabled", True)), depth=depth + 1)
        pack.subs[sub.name] = sub

    return pack


def _load_task(tid: str, raw: object, pack: Pack, cfg_path: Path) -> Task:
    if not isinstance(raw, dict):
        raise ConfigError(f"[STOP] {cfg_path}: [tasks.{tid}] 必须是个表")
    _check_keys(raw, TASK_KEYS, f"[tasks.{tid}] @ {cfg_path}")

    run = raw.get("run", [])
    script = raw.get("script", "")
    if not run and not script:
        raise ConfigError(f"[STOP] {cfg_path}: tasks.{tid} 既无 run 也无 script")
    if run and script:
        raise ConfigError(f"[STOP] {cfg_path}: tasks.{tid} 的 run 与 script 只能二选一")
    if run:
        if not isinstance(run, list) or not all(isinstance(x, str) for x in run):
            raise ConfigError(f"[STOP] {cfg_path}: tasks.{tid} 的 run 必须是字符串数组")
    else:
        if not isinstance(script, str):
            raise ConfigError(f"[STOP] {cfg_path}: tasks.{tid} 的 script 必须是字符串")

    timeout = raw.get("timeout", DEFAULT_TIMEOUT)
    if isinstance(timeout, bool) or not isinstance(timeout, int) or timeout <= 0:
        raise ConfigError(f"[STOP] {cfg_path}: tasks.{tid} 的 timeout 非法: {timeout!r}(正整数秒)")

    def arr(key: str) -> list[str]:
        val = raw.get(key, [])
        if not isinstance(val, list) or not all(isinstance(x, str) for x in val):
            raise ConfigError(f"[STOP] {cfg_path}: tasks.{tid} 的 {key} 必须是字符串数组")
        return list(val)

    return Task(
        id=tid,
        pack_path=pack.path,
        run=list(run),
        script=str(script),
        args=arr("args"),
        when=str(raw.get("when", "")),
        note=str(raw.get("note", "")),
        timeout=int(timeout),
        requires=arr("requires"),
        risky=bool(raw.get("risky", False)),
        pin=bool(raw.get("pin", False)),
        scripts_dir=pack.scripts_dir,
    )


def _check_keys(raw: dict, allowed: set[str], where: str) -> None:
    for key in sorted(set(raw) - allowed):
        raise ConfigError(f"[STOP] {where} 出现未知键: {key}(允许: {', '.join(sorted(allowed))})")


# ------------------------------------------------------------------ 占位符


def expand(text: str, root: Path, args: str = "", strict: bool = True) -> str:
    """展开 `<root>` / `<skill-dir:NAME>` / `<args>`; 残留其它尖括号即 STOP。

    只留这三个通用占位符是有意的: 凡是需要"这次改了哪些文件"这类信息的,
    都是具体领域的概念, 该由包自己的脚本算, 不该让引擎认识。
    """
    def sub(m: re.Match[str]) -> str:
        token = m.group(1)
        if token == "root":
            return str(root)
        if token == "args":
            return args
        if token.startswith("skill-dir:"):
            name = token.split(":", 1)[1]
            found = find_skill_dir(name, root)
            if found is None:
                raise ConfigError(f"[STOP] 找不到 skill 目录: {name}(搜过 {', '.join(SKILL_DIR_CANDIDATES)})")
            return str(found)
        return m.group(0)

    out = _PLACEHOLDER.sub(sub, text)
    if strict:
        left = _PLACEHOLDER.search(out)
        if left:
            raise ConfigError(
                f"[STOP] 残留无法展开的占位符 <{left.group(1)}>: {text}"
                " —— 引擎只认 <root> / <skill-dir:NAME> / <args>"
            )
    return out


def task_commands(task: Task, root: Path, args: str = "", strict: bool = True) -> list[str]:
    """把一条 task 变成**可直接执行**的命令行数组(占位符已展开)。

    `args` 非空却**无处可去**时 STOP —— 静默丢掉调用方给的参数, 就是让"看起来跑过了"悄悄发生
    (与引擎其余判据同源: 不静默降级)。脚本类不吃这条: 额外参数会直接接到 argv 末尾。
    """
    if args and not _takes_args(task):
        raise ConfigError(
            f"[STOP] {task.id} 不接参数(run 里没有 <args> 占位符), 但传入了: {args}"
            " —— 要么去掉参数, 要么在包里给这条 run 补上 <args>"
        )
    if task.script:
        if task.scripts_dir is None:
            raise ConfigError(f"[STOP] {task.id}: 所属包没有脚本目录")
        script_path = task.scripts_dir / task.script
        if not script_path.exists():
            raise ConfigError(f"[STOP] {task.id}: 脚本不存在: {script_path}")
        return [" ".join(_quote(x) for x in _script_argv(script_path, task, args, strict))]
    return [expand(c, root, args, strict) for c in task.run]


def _takes_args(task: Task) -> bool:
    """这条 task 吃不吃额外参数: 脚本类吃(接到 argv 末尾); 命令类得写了 `<args>` 占位符才算吃。"""
    return bool(task.script) or any("<args>" in cmd for cmd in task.run)


def _script_argv(script_path: Path, task: Task, args: str, strict: bool) -> list[str]:
    import sys
    argv = [sys.executable, str(script_path)]
    argv += [expand(a, find_root(), args, strict) for a in task.args]
    if args:
        argv += args.split()
    return argv


def _quote(text: str) -> str:
    return f'"{text}"' if (" " in text and '"' not in text) else text


def pack_env(task: Task) -> dict[str, str]:
    """调包脚本时注入的环境: 只告知本包目录, 配置由脚本自己找。"""
    if task.scripts_dir is None:
        return {}
    return {PACK_ENV: str(task.scripts_dir.parent)}
