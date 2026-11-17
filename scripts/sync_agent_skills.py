#!/usr/bin/env python3
"""把 .agents/skills 下的 skill 链接到 WorkBuddy 实际扫描的目录。

背景 (2026-09-18 排查结论)
--------------------------
内置 CLI 运行时 `cli/dist/codebuddy.js` 的 SkillLoader 扫描的技能根目录是:

    * 项目级: <workspace>/.codebuddy/skills        <- PathUtils.getProjectSkillsDir()
    * 用户级: <CODEBUDDY_CONFIG_DIR>/skills        <- PathUtils.getHomeSkillsDir()
    * 附加级: $CODEBUDDY_SESSION_SKILL_DIRS (path.delimiter 分隔, 仅当次会话有效)

也就是说 **不是** `.workbuddy-ai/skills` —— 那个目录该 CLI 不读, 故不再保留
兼容链接 (2026-09-18 移除), 只挂 `.codebuddy/skills` 这一处。

另外 `scanSkillsDirectory()` 会递归最深 5 层收集所有 `SKILL.md`, 所以把整棵
`.agents/skills` 直接挂上去会带进 193 个 autoclaw 设计预设 + 1 份重复副本,
共 213 条技能挤占系统提示上下文。因此本脚本只链接顶层 skill 目录, 并按
`.agents/skills/.config/sync.toml` 的 `[exclude]` 跳过体积型 / 重复的包。

排除项与挂载目标外置在 `.agents/skills/.config/sync.toml` (计划 26-11-17-0010
S9, 点前缀目录 `.config/` 防被 skill 遍历/链接当成 skill): 配置缺失/节缺失时
回落内置默认并打一行提示 (禁静默降级), 坏 TOML fail-fast, 显式空列表 = 合法配置。

用法
----
    python scripts/sync_agent_skills.py            # 建立 / 补齐链接 (幂等)
    python scripts/sync_agent_skills.py --prune    # 额外清理失效链接
    python scripts/sync_agent_skills.py --dry-run  # 只打印将要做的事

说明
----
* Windows 下用目录联接 (junction) 而非软链: 不需要管理员权限, 且对
  `readdir(withFileTypes)` + `stat()` 表现为真实目录, 扫描器可正常递归。
* 链接是单向指针, 源目录 `.agents/skills` 仍是唯一事实源 (已入库),
  两边读写同一份文件, 不存在副本漂移。
"""

from __future__ import annotations

import argparse
import ntpath
import os
import stat
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILL_SOURCE = REPO_ROOT / ".agents" / "skills"

# 配置单点 (S9, 计划 26-11-17-0010): 排除项与挂载目标外置在 .config/sync.toml,
# 点前缀目录 (D19) 防被 skill 遍历/链接当成 skill —— list_source_skills 过滤点前缀名。
SYNC_CONFIG = SKILL_SOURCE / ".config" / "sync.toml"

# 内置默认 (D3 分散自管): 配置缺失/节缺失时回落, 语义与出厂 sync.toml 一致;
# 逐条动机注释单点在 sync.toml, 这里不重复。
DEFAULT_EXCLUDED = ("autoclaw-design-capability", )
DEFAULT_LINK_TARGETS = (".codebuddy/skills", )


def _default_targets() -> list[Path]:
    return [REPO_ROOT / p for p in DEFAULT_LINK_TARGETS]


def load_sync_config() -> dict:
    """读 sync 配置; 文件缺失 -> `{}` (调用方回落内置默认并打提示, D13 禁静默降级)。

    坏 TOML -> 抛 `tomllib.TOMLDecodeError` fail-fast (坏配置不是「缺失」, 静默回落会让
    排除表/挂载面悄悄漂移)。tomllib 只在配置存在时才需要 (Python 3.11+; 老解释器 +
    无配置面的行为与配置化之前一致)。
    """
    if not SYNC_CONFIG.is_file():
        return {}
    try:
        import tomllib  # Python 3.11+
    except ModuleNotFoundError as exc:  # pragma: no cover - 环境面
        raise SystemExit(f"找到 {SYNC_CONFIG} 但当前 Python 缺 tomllib (<3.11): "
                         f"用 Python 3.11+ 跑, 或删除该文件回落内置默认") from exc
    with SYNC_CONFIG.open("rb") as fh:
        return tomllib.load(fh)


def _str_list(cfg: dict, section: str, key: str) -> list[str] | None:
    """取 `[section] key` 字符串数组; 节缺失/非表/值非数组/混型含非 str -> `None` (回落+提示)。

    WARN: 元素必须逐个 str 校验 (对齐 memory-bank `_common.py` 口径) —— 放过混型数组
    (如 `names = ["x", 2]`) 会让下游 `', '.join(...)` 抛 TypeError 裸栈, 而形态不对该走
    的是回落提示不是崩溃。显式空列表是合法配置 (返回 `[]`, 不回落不提示)。
    """
    node = cfg.get(section)
    if not isinstance(node, dict):
        return None
    values = node.get(key)
    if not isinstance(values, list) or not all(isinstance(v, str) for v in values):
        return None
    return values


def resolve_sync_config() -> tuple[set[str], list[Path], list[str]]:
    """sync.toml -> (排除项, 挂载目标, 回落提示行)。

    回落语义 (D13 权衡, 报告留痕): 排除表不是「校验类守卫」, 缺了不会假绿; 但排除表
    失效会把 213 条体积型预设挤回系统提示上下文, 静默回落 = 用户看不见配置被误删/
    改名已经生效失败, 故回落必打一行提示 (R-7「宽容回落被误读为静默降级」同源);
    提示走 stderr, 不污染正常输出与闸门判定。
    """
    cfg = load_sync_config()
    if not cfg:
        return set(DEFAULT_EXCLUDED), _default_targets(), [f"提示: {SYNC_CONFIG} 缺失或为空, 回落内置默认"]

    hints: list[str] = []
    names = _str_list(cfg, "exclude", "names")
    if names is None:
        hints.append("提示: [exclude] names 缺失/形态不对, 回落内置默认排除项")
        excluded = set(DEFAULT_EXCLUDED)
    else:
        excluded = set(names)

    paths = _str_list(cfg, "link_targets", "paths")
    if paths is None:
        hints.append("提示: [link_targets] paths 缺失/形态不对, 回落内置默认挂载目标")
        targets = _default_targets()
    else:
        # 绝对路径原样采用, 判定必须平台/版本稳定: os.path.isabs 在 Windows 3.13 起
        # 不再把根锚定的 '/x' 视为绝对 (历史语义 True), 会走 REPO_ROOT / p 分支且 pathlib
        # 保留左操作数盘符 (-> C:/x) 静默改写配置意图。盘符/UNC 交 ntpath.isabs (语义
        # 稳定), 根锚定 '/x' 与 '\x' 交纯字符串判定 p[:1] (3.13+ ntpath 对反斜杠根锚定
        # 同样 False) —— Linux 与 Windows 行为一致。
        targets = [Path(p) if ntpath.isabs(p) or p[:1] in ("/", "\\") else REPO_ROOT / p for p in paths]
    return excluded, targets, hints


def _run(cmd: list[str]) -> subprocess.CompletedProcess:
    """跑一条 Windows 命令。cmd 输出是 GBK, 解码必须容错, 否则抛 UnicodeDecodeError。"""
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
    )


def is_junction(path: Path) -> bool:
    """判断 path 是否是目录联接 / 符号链接 (重解析点)。"""
    if not path.exists():
        return False
    if path.is_symlink():
        return True
    # Python 对 Windows junction 的 is_symlink() 并不总是为 True, 兜底查文件属性
    try:
        st = os.stat(str(path), follow_symlinks=False)
    except OSError:
        return False
    reparse_point = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    return bool(getattr(st, "st_file_attributes", 0) & reparse_point)


def create_junction(link: Path, target: Path) -> bool:
    """创建目录联接, 成功返回 True。"""
    if sys.platform != "win32":
        link.parent.mkdir(parents=True, exist_ok=True)
        link.symlink_to(target, target_is_directory=True)
        return True
    link.parent.mkdir(parents=True, exist_ok=True)
    return _run(["cmd", "/c", "mklink", "/J", str(link), str(target)]).returncode == 0


def remove_junction(link: Path) -> bool:
    """删除目录联接本身, 不动目标目录内容。

    只对重解析点执行: os.rmdir 在 junction 上等价于 RemoveDirectory, 摘掉链接
    而不递归进入目标目录 (用 cmd 的 rmdir 会被路径里的 / 误判成命令行开关)。
    """
    if not is_junction(link):
        return False
    try:
        os.rmdir(str(link))
    except OSError:
        return False
    return True


def list_source_skills(excluded: set[str]) -> list[str]:
    """顶层 skill 目录名 (点前缀名一律跳过 —— .config/ 等配置面不会被当成 skill)。"""
    if not SKILL_SOURCE.is_dir():
        return []
    return sorted(
        entry.name for entry in SKILL_SOURCE.iterdir()
        if entry.is_dir() and not entry.name.startswith(".") and entry.name not in excluded
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="同步 .agents/skills 到 WorkBuddy 技能扫描目录")
    parser.add_argument("--prune", action="store_true", help="清理源目录已不存在 / 已排除的失效链接")
    parser.add_argument("--dry-run", action="store_true", help="只打印将要执行的操作")
    args = parser.parse_args()

    excluded, link_targets, hints = resolve_sync_config()
    for line in hints:
        print(line, file=sys.stderr)

    skills = list_source_skills(excluded)
    if not skills:
        print(f"源目录无可用 skill: {SKILL_SOURCE}", file=sys.stderr)
        return 1

    print(f"源目录: {SKILL_SOURCE}")
    excluded_note = f" (已排除 {', '.join(sorted(excluded))})" if excluded else ""
    print(f"待链接: {len(skills)} 个{excluded_note}")
    print()

    exit_code = 0
    for root in link_targets:
        print(f"== {root}")
        if root.exists() and not root.is_dir():
            print("   跳过: 同名非目录已存在", file=sys.stderr)
            exit_code = 1
            continue
        root.mkdir(parents=True, exist_ok=True)

        existing = {entry.name for entry in root.iterdir()} if root.exists() else set()

        for name in skills:
            link = root / name
            target = SKILL_SOURCE / name
            if link.is_dir() and not is_junction(link):
                print(f"   = {name} (真实目录, 保留)")
                continue
            if is_junction(link):
                print(f"   = {name} (链接已存在)")
                continue
            if args.dry_run:
                print(f"   + {name} -> {target}")
                continue
            ok = create_junction(link, target)
            print(f"   {'+' if ok else '!'} {name} -> {target}")
            if not ok:
                exit_code = 1

        stale = sorted(existing - set(skills))
        for name in stale:
            link = root / name
            if not is_junction(link):
                continue
            if args.dry_run:
                print(f"   - {name} (失效链接, 待清理)")
                continue
            if args.prune:
                ok = remove_junction(link)
                print(f"   {'-' if ok else '!'} {name} (已清理)")
                if not ok:
                    exit_code = 1
            else:
                print(f"   ? {name} (失效链接, 加 --prune 清理)")
        print()

    print("完成。重启会话后新技能才会出现在技能列表中。")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
