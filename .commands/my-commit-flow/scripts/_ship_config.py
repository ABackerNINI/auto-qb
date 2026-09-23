"""提交流水线的**外置配置**加载器 —— 项目特有项不在代码里内置, 强制逐仓库显式声明。

本文件属于 `my-commit-flow` **包**: 整包复制即可带走, 连配置一起。

设计(与可复用性直接相关):
- **流程**内置(禁 `add -A` / ref 三处核对 / 推送顺序 / 幽灵 diff 判据) —— 任何仓库都一样。
- **项目事实**外置: 红线文件、高危文件、提交前闸门、平台关键词 —— 全部来自
  **本包目录**下的 `.my-commit-flow.toml`(由引擎注入 `COMMAND_FLOW_PACK_DIR`, 找不到时退回脚本所在目录的上一级)。
- **没有配置就停下来引导生成**, 不静默回退到"猜一份默认" —— 猜错比停下来更贵。
- **初稿必须被确认**: `--init` 生成的配置 `confirmed = false`, 且红线不靠推断 —— 由 `draft_issues()`
  把"未确认 / 空红线 / 命令还是占位符"暴露出来, 防止照单全收。

用法:
    cfg, src = load_config()                 # 缺配置抛 ConfigMissing(带引导文案)
    path = init_config(root)                 # 生成初稿(按仓库特征猜, 需人工确认)
    python <包>/scripts/preflight.py --init | --show-config
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from urllib.parse import urlparse

try:
    import tomllib  # Python 3.11+
except ModuleNotFoundError:  # pragma: no cover
    tomllib = None  # type: ignore[assignment]

SCRIPTS_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPTS_DIR.parent
CONFIG_NAME = ".my-commit-flow.toml"
PACK_ENV = "COMMAND_FLOW_PACK_DIR"  # 由调用方(命令引擎)注入; 手工跑时退回脚本所在目录的上一级


def pack_dir() -> Path:
    """本包目录 —— 配置就在这里找。

    引擎调包脚本时会注入 `COMMAND_FLOW_PACK_DIR`; 直接手工跑时没有它,
    退回"脚本目录的上一级"(即 `<包>/scripts` → `<包>/`)。
    """
    env = os.environ.get(PACK_ENV, "").strip()
    return Path(env).resolve() if env else SCRIPTS_DIR.parent


# 配置里**省略**这些键时的兜底(不是"没配置文件时的默认值" —— 没配置文件直接 STOP)
KEY_DEFAULTS: dict = {
    "confirmed": False,  # --init 生成初稿时为 false; 人工核对完应改为 true
    "branch": "",  # 留空 = 跟当前分支
    "main_host_mark": "",  # 留空 = 不按 URL 特征挑, 直接按候选名取第一个存在的
    "main_candidates": ["origin"],
    "mirror_host_mark": "",
    "mirror": "",
    "red_lines": [],
    "warn_lines": [],
    "gates": [],
    "platform_hints": ["winreg", "dir_fd", "socket", "subprocess"],
    "staged_panic": 200,
    # 决策点指针: 预检在检查表末尾打印它。用来把「改代码 / 跑 git 前该读哪份陷阱索引」
    # 摆到执行者眼前 —— 库里的约束不接到决策点上就等于没写。留空 = 不打印。
    "pitfalls_index": "",
    "each_limit": 99,  # <each:GLOB> 的展开条数上限; 超了说明提交范围该拆, 不该静默跑下去
}

# 一个 [[gates]] 条目允许出现的键。出现在配置里的其它键一律 STOP ——
# gate 级原样透传、不做键过滤, `auto` 拼成 `auto_run` 会**静默**退回 "只打印":
# 你以为闸门自动跑了, 其实一条没跑, 输出里连痕迹都没有。见 draft_issues 的注释。
GATE_KEYS = {"match", "run", "note", "auto", "timeout"}

# <skill-dir:NAME> 的候选位置 —— 按此顺序找, 第一个存在的即命中。
# 项目级在前(同一份 skill 的 .codebuddy 版本是 .agents 的 junction), 用户级兜底。
SKILL_DIR_CANDIDATES = (
    ".agents/skills/{name}",
    ".codebuddy/skills/{name}",
    "~/.workbuddy-ai/skills/{name}",
    "~/.codebuddy/skills/{name}",
)


class ConfigMissing(RuntimeError):
    """仓库里没有外置配置 —— 调用方应打印本异常文案并停手。"""
    def __init__(self, root: Path) -> None:
        super().__init__(
            f"[STOP] 缺少外置配置: {root / CONFIG_NAME}\n"
            "本包不在代码里内置项目配置(红线文件 / 闸门命令 …), 必须逐仓库显式声明。\n"
            "生成初稿后**人工确认**再继续:\n"
            f"    python {SCRIPTS_DIR / 'preflight.py'} --init\n"
            f"    python {SCRIPTS_DIR / 'preflight.py'} --show-config   # 看生效值与来源"
        )


def git(*args: str) -> str:
    """跑 git 命令, 失败返回空串(调用方按"取不到"处理, 不要假装成功)。

    **只去掉末尾换行, 不能整段 strip()** —— 否则 `git status --porcelain` 首行的首列空格
    (表示"无暂存改动")会被吃掉, 进而把路径首字符也带歪, 红线匹配会静默放行。
    """
    proc = subprocess.run(["git", *args], capture_output=True, text=True, encoding="utf-8", errors="replace")
    return proc.stdout.rstrip("\n") if proc.returncode == 0 else ""


def find_root(start: Path | None = None) -> Path:
    """仓库根: 从 start(默认脚本目录)向上找 `.git`(目录或 worktree 的 .git 文件)。"""
    cur = (start or SCRIPTS_DIR).resolve()
    for parent in (cur, *cur.parents):
        if (parent / ".git").exists():
            return parent
    return pack_dir().parents[1]  # 兜底: <root>/.commands/<包> 的上两级


def load_config(root: Path | None = None, explicit: str | None = None) -> tuple[dict, Path]:
    """加载外置配置, 返回 (配置, 来源路径); 找不到 → 抛 `ConfigMissing`。

    配置在**包内**, 不在仓库根 —— 包是复用单位, 整包复制时配置跟着一起走。
    """
    if tomllib is None:
        raise RuntimeError(f"需要 Python 3.11+ 的 tomllib 才能读取 {CONFIG_NAME}")
    path = Path(explicit).expanduser().resolve() if explicit else pack_dir() / CONFIG_NAME
    if not path.exists():
        raise ConfigMissing(path.parent)
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    cfg = dict(KEY_DEFAULTS)
    cfg.update({k: v for k, v in data.items() if k in KEY_DEFAULTS})
    return cfg, path


def find_skill_dir(name: str, root: Path | None = None) -> Path | None:
    """定位 skill 目录: 项目级 → 用户级, 第一个存在的即命中; 都找不到返回 None(由调用方转 STOP)。

    `<skill-dir:NAME>` 占位符靠它解析。**不猜**: 找不到就交给调用方停手, 而不是降级成"打印给人" ——
    降级意味着"看起来跑过了", 那比报错坏得多。
    """
    base = root or find_root()
    for tpl in SKILL_DIR_CANDIDATES:
        cand = Path(tpl.format(name=name)).expanduser()
        if not cand.is_absolute():
            cand = base / cand
        if cand.is_dir():
            return cand
    return None


# ------------------------------------------------------------------ 远端探测(配置驱动)


def push_urls() -> dict[str, str]:
    """远端名 → push URL。"""
    out: dict[str, str] = {}
    for line in git("remote", "-v").splitlines():
        parts = line.split()
        if len(parts) >= 3 and parts[2] == "(push)":
            out[parts[0]] = parts[1]
    return out


def resolve_branch(cfg: dict) -> str:
    """分支: 配置优先, 否则跟当前分支。"""
    return cfg.get("branch") or git("rev-parse", "--abbrev-ref", "HEAD") or "main"


def resolve_main_remote(cfg: dict) -> tuple[str, str]:
    """主线远端 (名字, URL): 候选名里第一个 URL 含 `main_host_mark` 的; 都不匹配则回退到候选里
    第一个存在的(单远端项目里那个远端就是主线)。按 **URL 特征** 而不是按名字。"""
    urls = push_urls()
    mark = cfg.get("main_host_mark", "")
    if mark:
        for name in cfg.get("main_candidates", []):
            url = urls.get(name, "")
            if url and mark in url:
                return name, url
    for name in cfg.get("main_candidates", []):
        if name in urls:
            return name, urls[name]
    return "", ""


def main_matches_mark(cfg: dict, url: str) -> bool:
    """主线 URL 是否命中 `main_host_mark`(没配 mark 时视为命中) —— 用于提示"是不是走了回退"。"""
    mark = cfg.get("main_host_mark", "")
    return not mark or mark in url


def resolve_mirror_remote(cfg: dict) -> tuple[str, str]:
    """镜像远端 (名字, URL): 按 `mirror_host_mark` 找并**排除主线自己**; 再退回 `mirror` 这个名字。"""
    urls = push_urls()
    main_name, _ = resolve_main_remote(cfg)
    mark = cfg.get("mirror_host_mark", "")
    if mark:
        for name, url in urls.items():
            if name != main_name and mark in url:
                return name, url
    name = cfg.get("mirror", "")
    if name and name in urls and name != main_name:
        return name, urls[name]
    return "", ""


def proxy_disable_args(target_url: str) -> tuple[str, ...]:
    """生成禁用 per-URL 代理的 `-c` 参数(**从 git config 读, 不写死 key 与端口**)。"""
    out = git("config", "--get-regexp", r"^http\..*\.proxy$")
    keys = [line.split()[0] for line in out.splitlines() if line.strip()]
    if not keys:
        return ()
    host = urlparse(target_url).netloc if target_url else ""
    for key in keys:
        if host and host in key:
            return ("-c", f"{key}=")
    return ("-c", f"{keys[0]}=")


# ------------------------------------------------------------------ 初稿生成(--init)

# 被 gitignore 的目录里, 这些是构建/缓存产物 —— 不可能被 stage, 不该进候选(纯噪音)
BUILD_NOISE = (
    "__pycache__", ".venv", "venv", "node_modules", "dist", "build", "coverage", "htmlcov", ".pytest_cache",
    ".mypy_cache", ".ruff_cache", ".tox", ".nox", ".hypothesis", "site"
)


def _host(url: str) -> str:
    return urlparse(url).netloc if url else ""


def _ignored_dirs(root: Path) -> list[str]:
    """.gitignore 里的目录, 去掉构建/缓存噪音 —— 只留"像数据 / 本地状态"的候选。"""
    gi = root / ".gitignore"
    dirs: list[str] = []
    if gi.exists():
        for line in gi.read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and line.endswith("/"):
                if not any(n in line for n in BUILD_NOISE):
                    dirs.append(line)
    return dirs[:8]


# 各技术栈的"跨平台风险关键词"(不是通用的 Python 词 —— JS 仓库用 Python 关键词等于没有)
PLATFORM_HINTS: dict[str, list[str]] = {
    "python": ["winreg", "dir_fd", "socket", "subprocess", "os.open", "shutil.rmtree"],
    "node": ["child_process", "fs.rmSync", "spawnSync", "process.platform", "path.sep"],
    "make": ["uname", "getconf"],
}


def _detect_project(root: Path) -> tuple[list[dict], list[str], list[str]]:
    """识别项目类型与工具链, 返回 (闸门初稿, 判据说明, 平台关键词)。

    原则: **多证据才下判断, 判断不出就不猜** —— 猜错的闸门比没有闸门更危险(会让人以为该跑的跑过了)。
    判据随初稿写进注释, 便于一眼看出判错。
    """
    gates: list[dict] = []
    why: list[str] = []
    kinds: list[str] = []

    has_py = bool(list(root.glob("*.py"))) or (root / "src").exists() or (root / "tests").exists()
    py_cfg = [
        f for f in ("pyproject.toml", "setup.py", "setup.cfg", "requirements.txt", "Pipfile") if (root / f).exists()
    ]
    is_python = bool(py_cfg) and has_py

    if is_python:
        why.append("Python(依据: " + ", ".join(py_cfg) + " + 存在 .py 源码)")
        if (root / "uv.lock").exists():
            test, why_pack = "uv run pytest -q", "包管理器 uv(依据: uv.lock)"
        elif (root / "poetry.lock").exists():
            test, why_pack = "poetry run pytest -q", "包管理器 poetry(依据: poetry.lock)"
        elif (root / "Pipfile.lock").exists():
            test, why_pack = "pipenv run pytest -q", "包管理器 pipenv(依据: Pipfile.lock)"
        else:
            test, why_pack = "pytest -q", "未探测到包管理器 → 用裸 pytest"
        why.append(why_pack)
        run = [test]
        if (root / ".style.yapf").exists():
            run.insert(0, "yapf -i <changed:*.py>")
            why.append("格式化 yapf(依据: .style.yapf)")
        elif (
            (root / "ruff.toml").exists() or (root / ".ruff.toml").exists() or (
                (root / "pyproject.toml").exists() and
                "[tool.ruff]" in (root / "pyproject.toml").read_text(encoding="utf-8", errors="replace")
            )
        ):
            run.insert(0, "ruff format <changed:*.py>")
            why.append("格式化 ruff(依据: ruff 配置)")
        gates.append({"match": ["src/", "tests/"], "run": run, "note": "Python 改动", "auto": True})
        kinds.append("python")

    if (root / "package.json").exists():
        gates.append({"match": ["src/", "tests/"], "run": ["npm test"], "note": "前端改动", "auto": True})
        why.append("前端(依据: package.json)")
        kinds.append("node")

    if (root / "Makefile").exists() and not gates:
        gates.append({"match": ["Makefile"], "run": ["make test"], "note": "有 Makefile", "auto": True})
        why.append("Make(依据: Makefile, 且未识别到其它类型)")
        kinds.append("make")

    if not gates:
        why.append("**未识别项目类型** —— 故意不猜, 请手写 [[gates]]")

    hints: list[str] = []
    for kind in kinds:
        for hint in PLATFORM_HINTS.get(kind, []):
            if hint not in hints:
                hints.append(hint)
    return gates, why, hints


def render_template(root: Path) -> str:
    """配置初稿文本(带注释与判据, **必须人工确认**)。"""
    urls = push_urls()
    names = list(urls)
    main_mark = _host(urls[names[0]]) if names else ""
    mirror_mark = _host(urls[names[1]]) if len(names) > 1 else ""
    cands = _ignored_dirs(root)
    gates, why, hints = _detect_project(root)

    def arr(items) -> str:
        return "[" + ", ".join(f'"{i}"' for i in items) + "]"

    out = [
        "# 提交流水线配置 —— **初稿**(脚本按仓库特征生成, 未经确认)",
        "# 逐项确认/修改后把 confirmed 改成 true; 看生效值: preflight.py --show-config",
        "",
        "confirmed = false",
        "",
        'branch = ""                    # 留空 = 跟当前分支',
        f"main_candidates = {arr(names or ['origin'])}",
        "# ⚠ main_host_mark 取的是 `git remote -v` 里的**第一个**远端 —— 若它其实是镜像, 这里就填错了, 请核对",
        f'main_host_mark  = "{main_mark}"   # 主线 URL 特征; 留空 = 按候选名顺序取第一个存在的',
        f'mirror          = "{names[1] if len(names) > 1 else ""}"',
        f'mirror_host_mark = "{mirror_mark}"',
        "",
        "# 出现即 STOP —— **必须手填**: 生产配置 / 运行时数据 / 永不入 Git 的目录",
        "# 下列候选来自 .gitignore(已滤掉构建缓存), 只作提示, 请自行增删:",
    ]
    out += [f"#   - {c}" for c in cands] if cands else ["#   (未找到候选 —— 请按仓库的治理规则手写)"]
    out += [
        "red_lines = []",
        "",
        "# 出现需人工确认(例: 用户的在途改动 / 不该入库的项目数据)",
        "warn_lines = []",
        "",
        (f"platform_hints = {arr(hints)}" if hints else 'platform_hints = []   # 未识别技术栈 → 未给关键词, 请按真实跨平台风险手写'),
        f"staged_panic = {KEY_DEFAULTS['staged_panic']}",
        "",
        "# 提交前闸门 —— 判据: " + "; ".join(why),
    ]
    for gate in gates:
        out += [
            "[[gates]]",
            f"match = {arr(gate['match'])}",
            f"run   = {arr(gate['run'])}",
            f"auto  = {str(gate.get('auto', False)).lower()}   # true = 预检真的执行它(会改工作区), false = 只打印",
            f'note  = "{gate["note"]}"',
            "",
        ]
    out += [
        "# 占位符(由预检展开, 展开不了即 STOP): <root> · <skill-dir:NAME> · <changed:GLOB> · <each:GLOB>",
        "#   <changed:GLOB> 本次改动里匹配的文件 → 拼成一条命令(排除已删除的)",
        "#   <each:GLOB>    按匹配文件把这条 run 复制成多条命令, 每条替换一个文件; 条数上限 each_limit",
        "",
    ]
    if not gates:
        out += [
            "# (未识别项目类型, 未生成任何闸门 —— 请照下面格式手写, 否则提交前不会有任何机检)",
            "# [[gates]]",
            '# match = ["src/"]',
            '# run   = ["<未填: 测试命令>"]',
            '# auto  = true',
            '# note  = "改动源码"',
            "",
        ]
    return "\n".join(out)


def init_config(root: Path | None = None, force: bool = False) -> Path:
    """写配置初稿; 已存在则报错(不覆盖), 除非 force。"""
    root = root or find_root()
    path = pack_dir() / CONFIG_NAME
    if path.exists() and not force:
        raise FileExistsError(f"已存在, 不覆盖: {path}")
    path.write_text(render_template(root), encoding="utf-8")
    return path


def draft_issues(cfg: dict) -> list[str]:
    """初稿体检: 让"照单全收"立刻可见。

    - `confirmed` 仍为 false → 配置还是初稿, 未经确认
    - `red_lines` 为空 → 等于没有红线(「出现即 STOP」那层保护是关着的)
    - `gates` 为空 → 提交前不会有任何机检(测试 / 生成器 --check 都不会被提醒)
    - 闸门命令里仍有 `<未填…>` → 命令没填实

    注意: 只认 `<未填` 前缀 —— `<改过的 py 文件>` 这类是**运行时替换**的正常写法, 不算未填。
    """
    issues: list[str] = []
    if not cfg.get("confirmed"):
        issues.append("配置仍是初稿(confirmed = false) —— 逐项确认后改为 true")
    if not cfg.get("red_lines"):
        issues.append("red_lines 为空 = 没有红线, 「出现即 STOP」那层保护是关着的")
    if not cfg.get("gates"):
        issues.append("未声明 [[gates]] = 提交前没有任何机检(测试 / 生成器 --check 都不会被提醒)")
    for gate in cfg.get("gates", []):
        for cmd in gate.get("run", []):
            if "<未填" in cmd:
                issues.append(f"闸门命令仍有未填项: {cmd}")
    return issues


def config_problems(cfg: dict, path: Path | None = None) -> list[tuple[str, str]]:
    """分级体检, 返回 [(级别, 说明)], 级别为 "WARN" / "STOP"。

    与 `draft_issues()` 的分工: 后者只报"初稿还没确认"这类 WARN; 本函数额外报**配置写错** ——
    未知键 / `timeout` 非法一律 **STOP**。

    为什么是 STOP 不是 WARN: 闸门可能很贵(全量测试 / 格式化 / 索引自洽), 一个拼错的键让它
    **静默失效**, 比它直接报错坏得多 —— 报错会立刻被发现, 静默失效会让人以为"该跑的跑过了";
    而且 WARN 会被淹没在十来行的检查表里, 只有 STOP 会被处理。

    付的价钱: 以后新增配置键必须先加进 KEY_DEFAULTS / GATE_KEYS, 否则一写就挡住提交 —— 接受。
    """
    problems: list[tuple[str, str]] = []
    for issue in draft_issues(cfg):
        problems.append(("WARN", issue))

    # 顶层未知键: load_config 会把白名单外的键**静默丢掉**, 只有回读原文才看得见
    src = Path(path) if path else (pack_dir() / CONFIG_NAME)
    raw: dict = {}
    if src.exists() and tomllib is not None:
        try:
            raw = tomllib.loads(src.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:  # 读不了就如实说, 不假装没问题
            problems.append(("WARN", f"配置读取异常, 已跳过顶层键校验: {exc}"))
    for key in sorted(set(raw) - set(KEY_DEFAULTS)):
        problems.append(("STOP", f"顶层未知键: {key}"
                         f"(允许: {', '.join(sorted(KEY_DEFAULTS))})"))

    for gate in cfg.get("gates", []):
        note = gate.get("note", "(无 note)")
        for key in sorted(set(gate) - GATE_KEYS):
            problems.append(("STOP", f"gate「{note}」出现未知键: {key}"
                             f"(允许: {', '.join(sorted(GATE_KEYS))})"))
        timeout = gate.get("timeout", 600)
        if isinstance(timeout, bool) or not isinstance(timeout, int) or timeout <= 0:
            problems.append(("STOP", f"gate「{note}」的 timeout 非法: {timeout!r}(正整数秒)"))
    return problems
