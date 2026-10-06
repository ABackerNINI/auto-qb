"""包快照自举: 把本包复制到**仓库之外**的临时目录后再运行 —— 让一次调用只认一个版本。

根因(详见 `memory-bank/pitfalls/git/self-rewrite-imports.md` 与 `self-rewrite-config.md`): 本包脚本与
配置**就住在被它自己操作的仓库里**(`<仓库根>/.commands/my-commit-flow/`), 而流水线的内部同步
(`sync.run_sync`)会把远端新版包脚本 / 配置 rebase 进工作区。于是同一次调用里, "提交前"与"提交后"
跑的**可能不是同一版代码 / 同一份规则**。此前靠"在选定的几个点上重取配置 / 热刷新模块"打补丁,
覆盖不全: 入口脚本自身无法热刷新、`importlib.reload` 不重绑调用方已导入的名字、配置重取只覆盖两个点 ——
"旧代码 × 新树"的组合空间无法穷举, 只会不断复发。

治本 = **快照语义**: 入口脚本启动时把整包复制到仓库之外的临时目录, 从**副本**重入。
副本不受 `git rebase` 影响 ⇒ **一次调用 = 一个版本**, 中途的自我改写对本进程彻底不可见;
新版本从**下一次调用**生效。与"引擎不能中途换零件"同构。

契约(由本模块注入, 供包内其它脚本读取):
    COMMAND_FLOW_SNAPSHOT=1           已在快照里(防止无限重入)
    COMMAND_FLOW_PACK_DIR=<副本>       覆盖引擎注入的原包路径 ⇒ 配置 / 模块一律从副本读
    COMMAND_FLOW_REPO_ROOT=<根>        真仓库根(副本在仓库外, 向上找不到 `.git`, 必须显式注入)
    COMMAND_FLOW_ORIGINAL_PACK=<原包>   诊断 / 排障(报错里的 `__file__` 是副本路径)
    COMMAND_FLOW_SNAPSHOT_KEEP=1       保留临时副本(排障 / 测试; 否则子进程退出即删)

入口脚本用法(置于 `__main__` 分支, 在任何"真动作"之前; 见 commit.py / sync.py / push.py / verify_ref.py):
    from _snapshot import maybe_respawn
    _rc = maybe_respawn(__file__)
    if _rc is not None:
        raise SystemExit(_rc)          # 已由子进程接管

本模块是**叶子**(只依赖标准库) —— 入口脚本在 import 任何本包其它模块之前就能用它。
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

SNAPSHOT_ENV = "COMMAND_FLOW_SNAPSHOT"
REPO_ROOT_ENV = "COMMAND_FLOW_REPO_ROOT"
ORIG_PACK_ENV = "COMMAND_FLOW_ORIGINAL_PACK"
PACK_DIR_ENV = "COMMAND_FLOW_PACK_DIR"
KEEP_ENV = "COMMAND_FLOW_SNAPSHOT_KEEP"
SNAPSHOT_PREFIX = "my-commit-flow-"
SWEEP_AGE = 24 * 3600  # 超过一天的旧快照目录清掉(崩溃 / 强杀时 finally 不跑, 只能靠定期扫)

# 纯信息入口: 不碰工作树, 且必须作用在**原包**上 —— 尤其 `--init` 要把配置写进真包, 不能写进临时副本。
# `--safety` / `--help` 是冒烟闸门的探针(见 `.my-commit-flow.toml` 的 `|--with-safety` 节)。
INFO_FLAGS = ("--help", "-h", "--safety", "--show-config", "--init")


def _pack_dir(entry_file: str) -> Path:
    """原包目录 = 入口脚本的上一级目录的上一级(`<包>/scripts/xxx.py` → `<包>`)。"""
    return Path(entry_file).resolve().parent.parent


def _find_repo_root(start: Path) -> Path | None:
    """从 start 向上找 `.git`(目录或 worktree 的 `.git` 文件); 找不到返回 None(不注入, 让脚本走自己的兜底)。"""
    for parent in (start, *start.parents):
        if (parent / ".git").exists():
            return parent
    return None


def _sweep_old() -> None:
    """清掉过期的旧快照目录 —— 崩溃 / 强杀时 finally 不跑, 只能靠定期扫。"""
    base = Path(tempfile.gettempdir())
    now = time.time()
    for entry in base.glob(SNAPSHOT_PREFIX + "*"):
        try:
            if entry.is_dir() and now - entry.stat().st_mtime > SWEEP_AGE:
                shutil.rmtree(entry, ignore_errors=True)
        except OSError:
            pass


def make_snapshot(src_pack: Path) -> Path:
    """把 src_pack 整包复制到临时目录, 返回副本路径(仓库之外 ⇒ 免疫 rebase)。

    副本含**工作区未提交改动**(所见即所跑) —— 正在改流水线自己时, 跑的正是手上这一版。
    """
    _sweep_old()
    dest = Path(tempfile.mkdtemp(prefix=SNAPSHOT_PREFIX))
    shutil.copytree(src_pack, dest / "pack", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    return dest / "pack"


def maybe_respawn(entry_file: str, argv: list[str] | None = None) -> int | None:
    """未在快照里 → 复制 + 重入并返回子进程退出码; 已在快照里 / 纯信息入口 → 返回 None(继续正常执行)。

    重入用 `subprocess.call`(不用 `os.execv`): Windows 上 exec 语义不可靠(不真正替换进程、stdio 继承
    有坑), 多一层进程换来的是稳定 —— 代价可忽略(副本仅十余个小文件, 实测复制 avg 26ms)。

    `cwd` 原样透传: 流水线依赖 cwd 找仓库 / 跑 git, 换 cwd 会静默改变语义。
    """
    if os.environ.get(SNAPSHOT_ENV) == "1":
        return None  # 已在快照里 —— 正常执行
    args = list(sys.argv[1:] if argv is None else argv)
    if any(flag in args for flag in INFO_FLAGS):
        return None  # 纯信息入口: 不复制, 直接作用于原包
    src_pack = _pack_dir(entry_file)
    repo_root = _find_repo_root(src_pack)
    snap_pack = make_snapshot(src_pack)
    child = snap_pack / "scripts" / Path(entry_file).name
    env = {
        **os.environ,
        SNAPSHOT_ENV: "1",
        PACK_DIR_ENV: str(snap_pack),
        ORIG_PACK_ENV: str(src_pack),
    }
    if repo_root is not None:
        env[REPO_ROOT_ENV] = str(repo_root)  # 副本在仓库外, 必须显式告诉它真根在哪
    try:
        rc = subprocess.call([sys.executable, str(child), *args], env=env, cwd=os.getcwd())
    finally:
        if os.environ.get(KEEP_ENV) != "1":
            shutil.rmtree(snap_pack.parent, ignore_errors=True)
    return rc
