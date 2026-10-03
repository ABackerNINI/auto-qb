"""本机复现 Linux CI: 起容器跑全量测试, 与 Windows 侧对照(平台差异排查)。

**为什么是脚本而不是一行 `run`**: 这条命令里全是 `&&` / `;` / `|` 与多层引号, 而引擎在 Windows 上
走 `cmd.exe`(`shell=True`) —— 引号地狱必踩。脚本用 argv 列表调 docker, 零引号问题。

**配方与两个必踩点**(单点在 [pitfalls/testing/patching.md](../../../memory-bank/pitfalls/testing/patching.md)
「Docker 等价复现」节, 本文件不复述理由):
① **不要删容器内 `/work/.git`** —— `test_commands_engine` 的 `find_root()` 靠向上找 `.git`, 删了多 5 条假红;
② 先删宿主的 Windows `.venv` 再由 `uv sync` 重建(否则 Linux 上拿到 Windows 二进制)。

镜像钉 `python3.12`(与 CI 矩阵的 3.12 对齐; 3.13 用 `<args>` 换镜像即可)。
输出全文透传 —— 平台差异排查要看的是 FAILED 明细与覆盖率行, 不是只有结论。
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

IMAGE = "ghcr.io/astral-sh/uv:python3.12-bookworm-slim"

# 容器内: 拷仓库(保留 .git) → 丢宿主的 .venv 与 .coverage → uv sync → 全量
INNER = (
    "mkdir -p /work && cp -a /src/. /work/ 2>/dev/null; "
    "rm -f /work/.coverage; "
    "rm -rf /work/.venv && cd /work && uv sync -q 2>&1 | tail -1 && "
    "uv run pytest tests -q"
)


def main(argv: list[str]) -> int:
    image = argv[0] if argv else IMAGE
    if shutil.which("docker") is None:
        print("[STOP] 没装 docker: 本 task 用容器复现 Linux CI, 没 docker 跑不了")
        return 1
    root = Path(__file__).resolve().parents[3]  # <root>/.commands/test/scripts/linux_ci.py
    # 挂载路径用正斜杠: docker CLI 在 Windows 上对 `D:\x:/src` 这种"盘符冒号 + 分隔冒号"易误判
    mount = str(root).replace("\\", "/") + ":/src:ro"
    cmd = ["docker", "run", "--rm", "-v", mount, "-e", "LANG=C.UTF-8", image, "bash", "-lc", INNER]
    print(f"[linux-ci] {root} -> {image}")
    return subprocess.run(cmd, check=False).returncode


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
