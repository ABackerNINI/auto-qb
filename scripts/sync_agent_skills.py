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
EXCLUDED 跳过体积型 / 重复的包。

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
import os
import stat
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILL_SOURCE = REPO_ROOT / ".agents" / "skills"

# 挂载目标: 只有 .codebuddy/skills —— CLI 实际扫描的项目级路径。
# 产品文档里写的 .workbuddy-ai/skills 该 CLI 不读, 不保留兼容链接, 免得两处都要维护。
LINK_TARGETS = [
    REPO_ROOT / ".codebuddy" / "skills",
]

# 体积型包: 单个目录内含 193 个嵌套 SKILL.md (设计预设), 挂载成本高。
# (原先还有一份完整副本 autoclaw-design-capability_noqa, 2026-09-20 已删除, 故不在此列。)
EXCLUDED = {
    "autoclaw-design-capability",  # 18MB, 193 个嵌套预设
}


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


def list_source_skills() -> list[str]:
    if not SKILL_SOURCE.is_dir():
        return []
    return sorted(
        entry.name for entry in SKILL_SOURCE.iterdir()
        if entry.is_dir() and not entry.name.startswith(".") and entry.name not in EXCLUDED
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="同步 .agents/skills 到 WorkBuddy 技能扫描目录")
    parser.add_argument("--prune", action="store_true", help="清理源目录已不存在 / 已排除的失效链接")
    parser.add_argument("--dry-run", action="store_true", help="只打印将要执行的操作")
    args = parser.parse_args()

    skills = list_source_skills()
    if not skills:
        print(f"源目录无可用 skill: {SKILL_SOURCE}", file=sys.stderr)
        return 1

    print(f"源目录: {SKILL_SOURCE}")
    print(f"待链接: {len(skills)} 个 (已排除 {', '.join(sorted(EXCLUDED))})")
    print()

    exit_code = 0
    for root in LINK_TARGETS:
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
