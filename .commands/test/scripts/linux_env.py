"""test.linux-env: 幂等构建 auto-qb-testbed 镜像并保活常驻容器(计划 S1 基建)。

计划单点: memory-bank/plans/26-11-12-0152-plan-linux-testbed-docker.html(§03 形态主线 /
§06 D1-D8 拍板 / §07 R1-R9)。本脚本只做环境面, 不跑测试 —— 测试面归 test.linux / test.linux-e2e。

三步(全部幂等):
1. 基底镜像就绪: 本地已有 ubuntu:24.04 直接用; 否则按候选镜像源逐家试拉(Docker Hub 国内源, 可
   覆盖); 候选全灭再试 docker.io 直连; 仍失败 -> [FAIL] 行带 D8 停手指引(手动开代理后重跑)。
2. 镜像构建: tag = auto-qb-testbed:<uv.lock sha256 前 8 位>, 已存在即秒级 no-op; 否则 docker
   build(四份清单文件拷进临时 context —— 不把 478M 工作树喂给 daemon, 也不把 auto-qb-data 带
   进构建面; context 细节见 Dockerfile 头注)。
3. 容器保活: auto-qb-testbed 不存在则按 --restart unless-stopped 常驻创建(D1: 基底对齐 CI
   ubuntu-latest); 已存在则对齐镜像版本 —— 镜像 ID 一致只确保运行, 不一致重建为净室。

网络策略(D8, 拍板 2026-11-12): 镜像与依赖一律国内镜像站优先; github 系直连; 连不上停手请用户
手动开代理后重跑 —— 本脚本不内置代理、不自动重试、代理地址不进代码。镜像源候选与切换方式:

- Docker Hub 基底: 环境变量 AUTO_QB_TESTBED_HUB_MIRRORS(逗号/空白分隔)覆盖默认候选;
  值 direct = 跳过镜像源直连 docker.io。默认候选(计划定, 实跑后把实测钉值回写任务档案 task
  note, R9 漂移即换下一家): docker.m.daocloud.io / docker.1ms.run / docker.xuanyuan.me /
  docker.mirrors.tuna.tsinghua.edu.cn
- apt / PyPI / npm / playwright 二进制的候选与切法在 Dockerfile 头注(单点, 本文件不复述)。

S2 交接注记: 运行期依赖 delta 也走导出+pip 同款路线(uv export --generate-hashes + uv pip
install --index-url 国内源)—— uv sync --frozen 的下载源按 uv.lock 记录的 files.pythonhosted.org
绝对 URL 直连, 镜像索引对它无效(计划 §10 R4); ENV 已烘 UV_DEFAULT_INDEX/UV_INDEX_URL,
只覆盖 export/pip 面(Dockerfile 层 4/5 头注是单点)。

守阵: S2 随 test.linux 后端切换一并补(scripts/test_linux_ci.py 届时重写); 本脚本纯函数
(lock_hash8 / hub_mirror_candidates)已按可单测形态写。
"""
from __future__ import annotations

import hashlib
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

IMAGE_REPO = "auto-qb-testbed"
CONTAINER_NAME = "auto-qb-testbed"
BASE_IMAGE_DEFAULT = "ubuntu:24.04"
HUB_MIRRORS_ENV = "AUTO_QB_TESTBED_HUB_MIRRORS"
DEFAULT_HUB_MIRRORS = (
    "docker.m.daocloud.io",
    "docker.1ms.run",
    "docker.xuanyuan.me",
    "docker.mirrors.tuna.tsinghua.edu.cn",
)
# Dockerfile 烘焙层 COPY 的四份清单文件(仓库根); 构建脚本逐份拷进临时 context
BUILD_MANIFESTS = ("pyproject.toml", "uv.lock", "package.json", "package-lock.json")
DOCKERFILE = Path(__file__).resolve().parents[1] / "docker" / "Dockerfile"

D8_BASE_FAIL = (
    "[FAIL] 基底镜像拉取失败: 镜像源候选全灭且 docker.io 直连不通(D8)。按拍板停手: 请手动开启代理"
    "(Docker Desktop 侧走系统代理即可), 然后重跑 `commands run test.linux-env`。本脚本不内置代理、"
    "不自动重试、代理地址不进代码; 换候选用环境变量 AUTO_QB_TESTBED_HUB_MIRRORS(逗号分隔, "
    "值 direct=跳过镜像源直连)。"
)
D8_BUILD_FAIL = (
    "[FAIL] 镜像构建失败(真实错误在上方 docker build 输出里)。注意: github 系资源(uv 托管 "
    "CPython 3.13, 源在 github releases)按 D8 直连 —— 若错误落在这一步: 停手, 请手动开启代理后重跑 "
    "`commands run test.linux-env`; 国内源(apt/PyPI/npm/playwright 二进制)失败则按 R9 换候选: "
    "编辑 Dockerfile 对应 ARG 默认值(APT_MIRROR / UV_INDEX / NPM_REGISTRY / "
    "PLAYWRIGHT_DOWNLOAD_HOST, 备选清单在其头注)后重跑本 task, 或手工 `docker build --build-arg "
    "<ARG>=<候选值>` 自行覆盖 —— 本 task 拒收参数, 不在脚本里自动扩面换源。"
)


def missing_manifest(root: Path) -> str | None:
    """烘焙层 COPY 需要的四份清单文件里第一份缺失的名字; 齐全返回 None。"""
    for name in BUILD_MANIFESTS:
        if not (root / name).exists():
            return name
    return None


def lock_hash8(root: Path) -> str:
    """uv.lock 的 sha256 前 8 位 —— 镜像 tag 的版本锁(依赖变更才重建依赖层)。"""
    return hashlib.sha256((root / "uv.lock").read_bytes()).hexdigest()[:8]


def hub_mirror_candidates(environ: dict[str, str] | None = None) -> list[str]:
    """Docker Hub 国内镜像源候选清单; 环境变量覆盖, 值 direct = 清空候选(直连)。"""
    raw = (os.environ if environ is None else environ).get(HUB_MIRRORS_ENV, "").strip()
    if raw.lower() == "direct":
        return []
    parts = [p for p in re.split(r"[,\s]+", raw) if p]
    return parts or list(DEFAULT_HUB_MIRRORS)


def inspect_image(ref: str) -> str | None:
    """本地镜像 ID(sha256:...), 不存在返回 None。"""
    proc = subprocess.run(
        ["docker", "image", "inspect", "--format", "{{.Id}}", ref],
        capture_output=True, text=True, encoding="utf-8", errors="replace", check=False,
    )
    if proc.returncode != 0:
        return None
    return proc.stdout.strip() or None


def container_state() -> tuple[bool, str] | None:
    """常驻容器状态 (running, 镜像 ID); 容器不存在返回 None。"""
    proc = subprocess.run(
        ["docker", "container", "inspect", "--format", "{{.State.Running}} {{.Image}}",
         CONTAINER_NAME],
        capture_output=True, text=True, encoding="utf-8", errors="replace", check=False,
    )
    if proc.returncode != 0:
        return None
    fields = proc.stdout.split()
    if len(fields) != 2:
        return None
    return fields[0] == "true", fields[1]


def ensure_base_image() -> tuple[str | None, str]:
    """基底镜像就绪: 本地有 -> 用; 否则候选镜像源逐家试拉 -> 全灭直连 docker.io。

    返回 (传给 --build-arg BASE_IMAGE 的引用, 来源说明行); 引用为 None = 全灭(D8 停手)。
    """
    if inspect_image(BASE_IMAGE_DEFAULT):
        return BASE_IMAGE_DEFAULT, "本地已有"
    for mirror in hub_mirror_candidates():
        ref = f"{mirror}/library/{BASE_IMAGE_DEFAULT}"
        print(f"[linux-env] 试拉基底镜像: {ref}")
        if subprocess.run(["docker", "pull", ref], check=False).returncode == 0:
            return ref, f"经镜像源 {mirror}"
    print(f"[linux-env] 镜像源候选全灭, 直连 docker.io: {BASE_IMAGE_DEFAULT}")
    if subprocess.run(["docker", "pull", BASE_IMAGE_DEFAULT], check=False).returncode == 0:
        return BASE_IMAGE_DEFAULT, "直连 docker.io"
    return None, "候选全灭且直连不通"


def build_image(root: Path, base_ref: str, tag: str) -> tuple[bool, int]:
    """docker build: context = 临时目录, 只装四份清单文件(Dockerfile COPY 不碰别的东西)。

    返回 (是否真执行了 docker build, 退出码) —— 清单缺失等构建前置失败不算执行,
    main 据此决定是否打 D8_BUILD_FAIL(那条文案引向 docker build 输出, 不能误导向不存在的日志)。
    清单存在性由 main 入口的 missing_manifest() 把门, 这里不再重复查。
    """
    with tempfile.TemporaryDirectory(prefix="auto-qb-testbed-build-") as tmp:
        ctx = Path(tmp)
        for name in BUILD_MANIFESTS:
            shutil.copy2(root / name, ctx / name)
        cmd = [
            "docker", "build",
            "-f", str(DOCKERFILE),
            "--build-arg", f"BASE_IMAGE={base_ref}",
            "-t", tag,
            "-t", f"{IMAGE_REPO}:latest",
            str(ctx),
        ]
        print(f"[linux-env] docker build -> {tag}(context 仅含清单文件, 非整棵工作树)")
        return True, subprocess.run(cmd, check=False).returncode


def ensure_container(tag: str) -> int:
    """容器保活: 缺则常驻创建; 镜像一致只确保运行; 钉在旧镜像上则重建为净室。"""
    image_id = inspect_image(tag)
    assert image_id is not None  # main 已保证 tag 存在才走到这
    state = container_state()
    if state is None:
        print(f"[linux-env] 创建常驻容器 {CONTAINER_NAME}({tag}; --restart unless-stopped)")
        return subprocess.run(
            ["docker", "run", "-d", "--name", CONTAINER_NAME,
             "--restart", "unless-stopped", tag],
            check=False,
        ).returncode
    running, cimg = state
    if cimg == image_id:
        if running:
            print(f"[linux-env] 容器 {CONTAINER_NAME} 已在运行且镜像一致: no-op")
            return 0
        print(f"[linux-env] 容器 {CONTAINER_NAME} 已存在(停止态), 启动")
        return subprocess.run(["docker", "start", CONTAINER_NAME], check=False).returncode
    print(f"[linux-env] 容器 {CONTAINER_NAME} 钉在旧镜像上({cimg[:19]}), 按 {tag} 重建为净室")
    if subprocess.run(["docker", "rm", "-f", CONTAINER_NAME], check=False).returncode != 0:
        print(f"[FAIL] 删旧容器 {CONTAINER_NAME} 失败(上方 docker 输出) —— 手动 `docker rm -f "
              f"{CONTAINER_NAME}` 后重跑本 task")
        return 1
    return subprocess.run(
        ["docker", "run", "-d", "--name", CONTAINER_NAME, "--restart", "unless-stopped", tag],
        check=False,
    ).returncode


def main(argv: list[str]) -> int:
    # 闸门安全过滤探针(判据单点: .commands/my-commit-flow/scripts/_pipeline.py::_safe_files):
    # 无参跑本脚本 = 可能是一次十几分钟的镜像构建, 必须自认 action-without-args 让闸门摘掉 ——
    # 否则冒烟探针只能等 10s 超时还白起一次构建(同款形态见 linux_ci.py)。
    if "--safety" in argv:
        print("action-without-args")
        return 0
    if argv:
        print(f"[STOP] 未知参数: {' '.join(argv)}(本 task 幂等, 无参即跑; 不接参数)")
        return 2
    if shutil.which("docker") is None:
        print("[STOP] 没装 docker: testbed 以 Docker 常驻容器为宿主(D1), 没 docker 跑不了")
        return 1
    root = Path(__file__).resolve().parents[3]  # <root>/.commands/test/scripts/linux_env.py
    # 清单存在性先于 hash 计算(uv.lock 缺失时 lock_hash8 会抛裸 FileNotFoundError)
    missing = missing_manifest(root)
    if missing:
        print(f"[FAIL] 构建清单缺失: {root / missing} —— Dockerfile 烘焙层 COPY 需要 "
              "pyproject/uv.lock/package*.json, 先检查仓库状态(别在残缺工作树上构建)")
        return 2
    hash8 = lock_hash8(root)
    tag = f"{IMAGE_REPO}:{hash8}"
    print(f"[linux-env] uv.lock hash8 = {hash8} -> 镜像 {tag}")
    if inspect_image(tag):
        print(f"[linux-env] 镜像 {tag} 已存在: 跳过构建(秒级 no-op)")
    else:
        base_ref, base_note = ensure_base_image()
        if base_ref is None:
            print(D8_BASE_FAIL)
            return 1
        print(f"[linux-env] 基底: {base_ref}({base_note})")
        ran_build, rc = build_image(root, base_ref, tag)
        if rc != 0:
            if ran_build:
                print(D8_BUILD_FAIL)
            return rc
    return ensure_container(tag)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
