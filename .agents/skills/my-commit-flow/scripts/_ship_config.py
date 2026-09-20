"""提交流水线的**外置配置**加载器 —— 项目特有项不在代码里内置, 强制逐仓库显式声明。

设计(与可复用性直接相关):
- **流程**内置(禁 `add -A` / ref 三处核对 / 推送顺序 / 幽灵 diff 判据) —— 任何仓库都一样。
- **项目事实**外置: 红线文件、高危文件、提交前闸门、平台关键词 —— 全部来自 `<仓库根>/.commit-flow.toml`。
- **没有配置就停下来引导生成**, 不静默回退到"猜一份默认" —— 猜错比停下来更贵。

用法:
    cfg, src = load_config()                 # 缺配置抛 ConfigMissing(带引导文案)
    path = init_config(root)                 # 生成初稿(按仓库特征猜, 需人工确认)
    python <skill-dir>/scripts/preflight.py --init | --show-config
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from urllib.parse import urlparse

try:
    import tomllib  # Python 3.11+
except ModuleNotFoundError:  # pragma: no cover
    tomllib = None  # type: ignore[assignment]

SCRIPTS_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPTS_DIR.parent
CONFIG_NAME = ".commit-flow.toml"

# 配置里**省略**这些键时的兜底(不是"没配置文件时的默认值" —— 没配置文件直接 STOP)
KEY_DEFAULTS: dict = {
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
}


class ConfigMissing(RuntimeError):
    """仓库里没有外置配置 —— 调用方应打印本异常文案并停手。"""

    def __init__(self, root: Path) -> None:
        super().__init__(
            f"[STOP] 缺少外置配置: {root / CONFIG_NAME}\n"
            "本 skill 不在代码里内置项目配置(红线文件 / 闸门命令 …), 必须逐仓库显式声明。\n"
            "生成初稿后**人工确认**再继续:\n"
            "    python <skill-dir>/scripts/preflight.py --init\n"
            "    python <skill-dir>/scripts/preflight.py --show-config   # 看生效值与来源")


def git(*args: str) -> str:
    """跑 git 命令, 失败返回空串(调用方按"取不到"处理, 不要假装成功)。"""
    proc = subprocess.run(["git", *args], capture_output=True, text=True, encoding="utf-8", errors="replace")
    return proc.stdout.strip() if proc.returncode == 0 else ""


def find_root(start: Path | None = None) -> Path:
    """仓库根: 从 start(默认脚本目录)向上找 `.git`(目录或 worktree 的 .git 文件)。"""
    cur = (start or SCRIPTS_DIR).resolve()
    for parent in (cur, *cur.parents):
        if (parent / ".git").exists():
            return parent
    return Path(__file__).resolve().parents[4]  # 兜底: 上四级


def load_config(root: Path | None = None, explicit: str | None = None) -> tuple[dict, Path]:
    """加载外置配置, 返回 (配置, 来源路径); 找不到 → 抛 `ConfigMissing`。"""
    if tomllib is None:
        raise RuntimeError("需要 Python 3.11+ 的 tomllib 才能读取 .commit-flow.toml")
    path = Path(explicit).expanduser().resolve() if explicit else (root or find_root()) / CONFIG_NAME
    if not path.exists():
        raise ConfigMissing(path.parent)
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    cfg = dict(KEY_DEFAULTS)
    cfg.update({k: v for k, v in data.items() if k in KEY_DEFAULTS})
    return cfg, path


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


def _host(url: str) -> str:
    return urlparse(url).netloc if url else ""


def _detect_gates(root: Path) -> list[dict]:
    """按项目特征猜闸门初稿 —— 只作起点, 生成后必须人工确认。"""
    gates: list[dict] = []
    if (root / "pyproject.toml").exists() or (root / "tests").exists():
        gates.append({
            "match": ["src/", "tests/"],
            "run": ["<格式化命令, 例: yapf -i <改过的文件>>", "<测试命令, 例: uv run pytest tests -q>"],
            "note": "Python 改动",
        })
    if (root / "package.json").exists():
        gates.append({"match": ["src/", "tests/"], "run": ["npm test"], "note": "前端改动"})
    if (root / "Makefile").exists():
        gates.append({"match": ["Makefile"], "run": ["make test"], "note": "有 Makefile 时"})
    return gates


def _detect_lines(root: Path) -> tuple[list[str], list[str]]:
    """高危初稿: 从 `.gitignore` 取被忽略的目录 —— 它们不该出现在暂存清单里。"""
    gi = root / ".gitignore"
    warn: list[str] = []
    if gi.exists():
        for line in gi.read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and line.endswith("/"):
                warn.append(line)
    return [], warn[:5]


def render_template(root: Path) -> str:
    """配置初稿文本(带注释, 需人工确认)。"""
    urls = push_urls()
    names = list(urls)
    main_mark = _host(urls[names[0]]) if names else ""
    mirror_mark = _host(urls[names[1]]) if len(names) > 1 else ""
    red, warn = _detect_lines(root)
    gates = _detect_gates(root)

    def arr(items) -> str:
        return "[" + ", ".join(f'"{i}"' for i in items) + "]"

    out = [
        "# 提交流水线配置 —— 初稿由脚本生成, 请**逐项确认/修改**后再用",
        "# 查看生效值与来源: python <skill-dir>/scripts/preflight.py --show-config",
        "",
        'branch = ""                    # 留空 = 跟当前分支',
        f"main_candidates = {arr(names or ['origin'])}",
        f'main_host_mark  = "{main_mark}"   # 主线 URL 特征; 留空 = 按候选名顺序取第一个存在的',
        f'mirror          = "{names[1] if len(names) > 1 else ""}"',
        f'mirror_host_mark = "{mirror_mark}"',
        "",
        "# 出现即 STOP(例: 生产配置 / 运行时数据)",
        f"red_lines = {arr(red)}",
        "# 出现需人工确认(例: 用户的在途改动)",
        f"warn_lines = {arr(warn)}",
        "",
        f"platform_hints = {arr(KEY_DEFAULTS['platform_hints'])}",
        f"staged_panic = {KEY_DEFAULTS['staged_panic']}",
        "",
    ]
    for gate in gates:
        out += [
            "[[gates]]",
            f"match = {arr(gate['match'])}",
            f"run   = {arr(gate['run'])}",
            f'note  = "{gate["note"]}"',
            "",
        ]
    return "\n".join(out)


def init_config(root: Path | None = None, force: bool = False) -> Path:
    """写配置初稿; 已存在则报错(不覆盖), 除非 force。"""
    root = root or find_root()
    path = root / CONFIG_NAME
    if path.exists() and not force:
        raise FileExistsError(f"已存在, 不覆盖: {path}")
    path.write_text(render_template(root), encoding="utf-8")
    return path
