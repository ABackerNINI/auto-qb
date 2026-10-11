"""本机复现 Linux CI: 起容器跑全量测试, 与 Windows 侧对照(平台差异排查)。

**为什么是脚本而不是一行 `run`**: 这条命令里全是 `&&` / `;` / `|` 与多层引号, 而引擎在 Windows 上
走 `cmd.exe`(`shell=True`) —— 引号地狱必踩。脚本用 argv 列表调 docker, 零引号问题。

**配方与两个必踩点**(单点在 [pitfalls/testing/patching.md](../../../memory-bank/pitfalls/testing/patching.md)
「Docker 等价复现」节, 本文件不复述理由):
① **不要删容器内 `/work/.git`** —— `test_commands_engine` 的 `find_root()` 靠向上找 `.git`, 删了多 5 条假红;
② 先删宿主的 Windows `.venv` 再由 `uv sync` 重建(否则 Linux 上拿到 Windows 二进制)。

镜像钉 `python3.12`(与 CI 矩阵的 3.12 对齐; 3.13 用 `<args>` 换镜像即可)。
输出全文透传 —— 平台差异排查要看的是 FAILED 明细与覆盖率行, 不是只有结论。

**代理透传 (2026-10-11 加)**: 宿主常靠本地代理上网(`http://127.0.0.1:4085` 之类), 而**容器里那个地址
指向容器自己** ⇒ `uv sync` 直连 PyPI 会 `tls handshake eof` 起不来。本脚本自动把代理变量里的**回环主机
改写成 `host.docker.internal`** 并补 `--add-host host.docker.internal:host-gateway`, 同时**强制 `no_proxy`
含回环** —— 后者不是洁癖: 注了代理又不放行回环时, `urllib` 会把 `127.0.0.1` 的请求也交给代理,
`tests/test_hr_server.py` 那批回环端点用例会 **6 failed + 2 errors 假红**(实测); 补上即全绿。
坑档单点: [pitfalls/testing/patching.md](../../../memory-bank/pitfalls/testing/patching.md)「容器网络坑」。
守阵: `scripts/test_linux_ci.py`。
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

IMAGE = "ghcr.io/astral-sh/uv:python3.12-bookworm-slim"

# 容器内指向自己的主机名 —— 代理写在这些地址上时必须改写
LOOPBACK_HOSTS = ("127.0.0.1", "localhost", "::1", "[::1]")
PROXY_KEYS = ("http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY")
# 无论宿主有没有设, 都要把回环并进去(理由见模块 docstring)
NO_PROXY_KEYS = ("no_proxy", "NO_PROXY")
NO_PROXY_ALWAYS = ("127.0.0.1", "localhost", "::1")

# 容器内: 拷仓库(保留 .git) → 丢宿主的 .venv 与 .coverage → uv sync → 全量
INNER = (
    "mkdir -p /work && cp -a /src/. /work/ 2>/dev/null; "
    "rm -f /work/.coverage; "
    "rm -rf /work/.venv && cd /work && uv sync -q 2>&1 | tail -1 && "
    "uv run pytest tests -q"
)


def rewrite_proxy(value: str) -> tuple[str, bool]:
    """代理 URL 里的回环主机 → `host.docker.internal`; 返回 (新值, 是否改写过)。

    只动主机段(`//` 之后、端口/路径之前), 免得不小心碰上路径里恰好出现的同名字符串。
    """
    out, changed = value, False
    for host in LOOPBACK_HOSTS:
        pat = rf"(?<=//){re.escape(host)}(?=[:/]|$)"
        new = re.sub(pat, "host.docker.internal", out, count=1, flags=re.IGNORECASE)
        if new != out:
            out, changed = new, True
    return out, changed


def container_env(environ: dict[str, str] | None = None) -> tuple[list[tuple[str, str]], bool]:
    """宿主环境 → 容器 `-e` 列表 + 是否需要 `--add-host host.docker.internal`。

    - 代理变量照传, 但**回环主机改写**(否则容器拿它指自己 ⇒ `uv sync` 连不上 PyPI)。
    - `no_proxy` / `NO_PROXY` 恒并入回环 —— 注了代理却不放行回环时, 回环端点用例集体假红。
    """
    env: dict[str, str] = dict(os.environ if environ is None else environ)
    pairs: list[tuple[str, str]] = [("LANG", "C.UTF-8")]
    needs_gateway = False
    for key in PROXY_KEYS:
        raw = (env.get(key) or "").strip()
        if not raw:
            continue
        val, changed = rewrite_proxy(raw)
        needs_gateway = needs_gateway or changed
        pairs.append((key, val))
    bypass = set(NO_PROXY_ALWAYS)
    for key in NO_PROXY_KEYS:
        bypass.update(p.strip() for p in re.split(r"[,\s]+", env.get(key) or "") if p.strip())
    bypass_line = ",".join(sorted(bypass))
    pairs.extend((key, bypass_line) for key in NO_PROXY_KEYS)
    return pairs, needs_gateway


def main(argv: list[str]) -> int:
    # 冒烟安全过滤探针(判据单点: .commands/my-commit-flow/scripts/_pipeline.py::_safe_files):
    # 无参跑本脚本 = 真起容器跑全量 ⇒ 必须自认 action-without-args, 让闸门的 `<each:...|--with-safety>`
    # 直接摘掉 —— 否则探针只能等 10s 超时(还会白起一次 docker run), 每次提交都付这笔钱。
    if "--safety" in argv:
        print("action-without-args")
        return 0
    if argv and argv[0].startswith("-"):
        print(f"[STOP] 未知参数: {argv[0]}(本 task 只接一个可选镜像名)")
        return 2
    image = argv[0] if argv else IMAGE
    if shutil.which("docker") is None:
        print("[STOP] 没装 docker: 本 task 用容器复现 Linux CI, 没 docker 跑不了")
        return 1
    root = Path(__file__).resolve().parents[3]  # <root>/.commands/test/scripts/linux_ci.py
    # 挂载路径用正斜杠: docker CLI 在 Windows 上对 `D:\x:/src` 这种"盘符冒号 + 分隔冒号"易误判
    mount = str(root).replace("\\", "/") + ":/src:ro"
    env_pairs, needs_gateway = container_env()
    cmd = ["docker", "run", "--rm", "-v", mount]
    if needs_gateway:
        cmd += ["--add-host", "host.docker.internal:host-gateway"]
    for key, val in env_pairs:
        cmd += ["-e", f"{key}={val}"]
    cmd += [image, "bash", "-lc", INNER]
    print(f"[linux-ci] {root} -> {image}")
    passed = [k for k, _ in env_pairs if k.lower().endswith("_proxy") and not k.lower().startswith("no_")]
    if passed:
        print(f"[linux-ci] 代理透传: {', '.join(passed)}(回环已改写{'; 已加 --add-host' if needs_gateway else ''}; no_proxy 并入回环)")
    return subprocess.run(cmd, check=False).returncode


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
