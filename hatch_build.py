"""wheel 构建钩子: 构建期把 git hash 注入 .dist-info/extra_metadata/BUILD_ID(计划 26-09-22-2318 v2 §4.2 双路径)。

Version 本体保持纯 SemVer 单源(hatchling 的 build_data 不暴露可变的 version 键,
METADATA 由版本源先定), hash 尾经 extra_metadata 侧车文件携带 —— 发布件装到别处后
可经 importlib.metadata.files("auto-qb") 读 BUILD_ID 定位构建树; 源码运行场景不走
本钩子(显示层运行时派生, 见计划 §4.2)。

机制(hatchling 语义): build_data["extra_metadata"] 是 {源文件路径: dist-info 相对目标}
的 force-include 式映射, 落点为 .dist-info/extra_metadata/<目标> —— 故本钩子先写临时
文件再映射, finalize 清理临时目录。

约定(评审与计划口径):
- hash 不可得(git 缺失/非 git 仓)时静默跳过, 构建不失败(保守默认);
- 树脏标 .dirty 后缀, 溯源时可识别"非净树构建"。
"""

from __future__ import annotations

import atexit
import shutil
import subprocess
import tempfile
from pathlib import Path

from hatchling.builders.hooks.plugin.interface import BuildHookInterface


def build_id_from_git(root: str) -> str | None:
    """g<short hash>(+ .dirty); git 不可用/非 git 仓返回 None。独立纯函数化便于守阵。"""
    try:
        proc = subprocess.run(
            ["git", "-C", root, "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=10,
        )
        if proc.returncode != 0 or not proc.stdout.strip():
            return None
        short = proc.stdout.strip()
        status = subprocess.run(
            ["git", "-C", root, "status", "--porcelain"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=10,
        )
        dirty = bool(status.returncode == 0 and status.stdout.strip())
        return f"g{short}" + (".dirty" if dirty else "")
    except (OSError, subprocess.SubprocessError):
        return None


class BuildHook(BuildHookInterface):
    """custom 钩子单点: 只往 extra_metadata 塞 BUILD_ID 侧车, 不碰其余构建面。"""
    def initialize(self, version: str, build_data: dict) -> None:
        build_id = build_id_from_git(str(self.root))
        if not build_id:
            return
        tmp_dir = Path(tempfile.mkdtemp(prefix="auto-qb-build-id-"))
        (tmp_dir / "BUILD_ID").write_text(build_id + "\n", encoding="utf-8")
        self._build_id_tmp_dir = tmp_dir
        # hatchling 钩子无 try/finally: 构建中途失败不调 finalize, atexit 兜底防 %TEMP% 累积(评审 R2-F5)。
        atexit.register(shutil.rmtree, tmp_dir, ignore_errors=True)
        # 映射方向 = {源: 目标相对路径}(与 force-include 同构), 落点 .dist-info/extra_metadata/BUILD_ID。
        build_data["extra_metadata"] = {str(tmp_dir / "BUILD_ID"): "BUILD_ID"}

    def finalize(self, version: str, build_data: dict, artifacts: list) -> None:
        tmp_dir = getattr(self, "_build_id_tmp_dir", None)
        if tmp_dir is not None:
            shutil.rmtree(tmp_dir, ignore_errors=True)
