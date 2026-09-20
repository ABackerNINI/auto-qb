"""my-commit-flow 的配置与探测工具 —— 换项目时**尽量只改本文件**, 且多数项能自动探测。

设计原则(可复用性):
- **能探测的不写死**: 仓库根(向上找 `.git`)、分支(跟当前分支)、主线/镜像远端(按 URL 特征或候选名)、
  代理(从 `git config` 读 per-URL 代理) —— 全部运行期探测, 代码里不写死任何 URL。
- **写死的只有项目特有项**: `RED_LINES` / `WARN_LINES`(红线文件)、`GATES`(提交前闸门)、
  `LINUX_CHECK_HINTS`(平台差异关键词)、镜像策略。换项目改这些。
- **配置留空 = 用探测结果**: `BRANCH` / `MAIN_HOST_MARK` / `MIRROR_URL` 留空即自动。

本 skill 依赖本仓环境(Windows 工具 shell 的删除拦截层、Gitee 主线 + GitHub 镜像、多 worktree 并行),
不是通用 git 工作流; 拿到别的项目前至少过一遍 `RED_LINES` 与 `GATES`。
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from urllib.parse import urlparse

SCRIPTS_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPTS_DIR.parent

# ---------------------------------------------------------------- 可选覆盖项(留空 = 自动探测)

BRANCH = ""  # 留空 = 跟当前分支; 填了就用填的(如 "main")
MAIN_HOST_MARK = "gitee.com"  # 主线 URL 特征; 留空 = 不校验, 按候选名顺序取第一个存在的
# 主线远端候选名(按序) —— **别假定项目一定用 Gitee**: 只有 GitHub 的项目里 github 就是主线
REMOTE_MAIN_CANDIDATES = ("gitee", "origin", "github")
MIRROR_HOST_MARK = "github.com"  # 镜像 URL 特征; 留空 = 只用 REMOTE_MIRROR 这个名字
REMOTE_MIRROR = "github"  # 镜像远端名
MIRROR_URL = ""  # 缺远端时提示用; 留空 = 只提示补远端、不给 URL

# ---------------------------------------------------------------- 项目特有的写死项(换项目要改)

# 红线: 出现即 STOP(不得进暂存清单)
RED_LINES = (
    "config.yml",  # 用户真实生产配置, 非示例
    "auto-qb-data/",  # 运行时数据(state.json / 锁 / 日志 / 跳检备份)
)
# 高危: 出现需人工确认(可能是用户自己的在途改动)
WARN_LINES = (
    "想法.md",
    ".workbuddy-ai/",  # 项目数据目录(.gitignore 已忽略, 出现即为异常)
)
# 闸门: 改动命中哪些文件 → 提交前必须跑什么(脚本只提示, 由执行者跑; <skill-dir> 见 SKILL.md)
GATES: tuple[tuple[tuple[str, ...], tuple[str, ...], str], ...] = (
    (("src/", "tests/"), ("yapf -i <改过的 py 文件>", "uv run pytest tests -q"), "Python 改动: 先格式化再跑全量测试"),
    (("memory-bank/issues/", ),
     ("python <create-issue skill>/scripts/gen_issues_index.py --check", ),  # 不假定与它同目录
     "issue 池改动: 索引是生成物, 必须 --check 通过"),
    (("memory-bank/tasks/", ), ("python scripts/gen_tasks_index.py --check", ), "任务档案改动: 索引需自洽"),
    ((".agents/skills/", ), ("python <改动的脚本> --help", ), "skill 改动: 冒烟跑一遍被改的脚本"),
)
# 平台差异: 命中这些关键词的改动, Windows 全绿不算数, 建议去 Linux 复现
LINUX_CHECK_HINTS = ("winreg", "shutil.rmtree", "dir_fd", "socket", "subprocess", "os.open")
# 提交后若 staged 超过这个阈值 → 高度怀疑「分支 ref 被别的会话回退」(见 pitfalls)
STAGED_PANIC = 200

# ---------------------------------------------------------------- 探测工具


def git(*args: str) -> str:
    """跑 git 命令, 失败返回空串(调用方按"取不到"处理, 不要假装成功)。"""
    proc = subprocess.run(["git", *args], capture_output=True, text=True, encoding="utf-8", errors="replace")
    return proc.stdout.strip() if proc.returncode == 0 else ""


def find_root(start: Path | None = None) -> Path:
    """仓库根: 从 start(默认脚本目录)向上找 `.git`(目录或 worktree 的 .git 文件)。

    不按 skill 的安装深度反推 —— 换目录结构(`.agents/skills/` / `.codebuddy/skills/` / 用户级)都能用。
    """
    cur = (start or SCRIPTS_DIR).resolve()
    for parent in (cur, *cur.parents):
        if (parent / ".git").exists():
            return parent
    return Path(__file__).resolve().parents[4]  # 兜底: 上四级


def resolve_branch() -> str:
    """分支: 配置优先, 否则跟当前分支。"""
    if BRANCH:
        return BRANCH
    return git("rev-parse", "--abbrev-ref", "HEAD") or "main"


def push_urls() -> dict[str, str]:
    """远端名 → push URL。"""
    out: dict[str, str] = {}
    for line in git("remote", "-v").splitlines():
        parts = line.split()
        if len(parts) >= 3 and parts[2] == "(push)":
            out[parts[0]] = parts[1]
    return out


def resolve_main_remote() -> tuple[str, str]:
    """主线远端 (名字, URL)。

    判据(按序): ① 候选里第一个 **URL 含 `MAIN_HOST_MARK`** 的 —— 按 URL 特征而不是按名字,
    因为历史 clone 的 `origin` 可能是镜像; ② 没配 mark 或谁都不匹配 → 候选里第一个**存在**的
    (**回退**: 只有 GitHub 的项目里 github 就是主线, 别假定一定用 Gitee);
    ③ 都没有 → ("", "")。调用方可用 `main_matches_mark()` 判断是否走了 ②, 是的话应 WARN 提示。
    """
    urls = push_urls()
    if MAIN_HOST_MARK:
        for name in REMOTE_MAIN_CANDIDATES:
            url = urls.get(name, "")
            if url and MAIN_HOST_MARK in url:
                return name, url
    for name in REMOTE_MAIN_CANDIDATES:  # 回退: 按顺序取第一个存在的
        if name in urls:
            return name, urls[name]
    return "", ""


def main_matches_mark(url: str) -> bool:
    """主线 URL 是否命中 `MAIN_HOST_MARK`(没配 mark 时视为命中) —— 用于提示"是不是走了回退"。"""
    return not MAIN_HOST_MARK or MAIN_HOST_MARK in url


def resolve_mirror_remote() -> tuple[str, str]:
    """镜像远端 (名字, URL): 按 `MIRROR_HOST_MARK` 找 —— **排除主线自己**(只有 GitHub 的项目里
    没有镜像, 不能把主线当镜像), 再退回 `REMOTE_MIRROR` 这个名字。"""
    urls = push_urls()
    main_name, _ = resolve_main_remote()
    if MIRROR_HOST_MARK:
        for name, url in urls.items():
            if name != main_name and MIRROR_HOST_MARK in url:
                return name, url
    if REMOTE_MIRROR in urls and REMOTE_MIRROR != main_name:
        return REMOTE_MIRROR, urls[REMOTE_MIRROR]
    return "", ""


def proxy_disable_args(target_url: str) -> tuple[str, ...]:
    """生成禁用 per-URL 代理的 `-c` 参数(**从 git config 读, 不写死 key 与端口**)。

    读 `git config --get-regexp '^http\\..*\\.proxy$'`, 优先禁用与 target_url 同 host 的那条;
    一条都没配 → 返回空(表示无需禁用)。
    """
    out = git("config", "--get-regexp", r"^http\..*\.proxy$")
    keys = [line.split()[0] for line in out.splitlines() if line.strip()]
    if not keys:
        return ()
    host = urlparse(target_url).netloc if target_url else ""
    for key in keys:
        if host and host in key:
            return ("-c", f"{key}=")
    return ("-c", f"{keys[0]}=")
