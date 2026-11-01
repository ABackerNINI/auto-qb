"""把 mutmut 的目标与测试池写进镜像仓的 pyproject.toml(覆盖式重写, 幂等)。

**只做一件事**: 删掉已有的 `[tool.mutmut]` 段, 再按参数重写一份。stdlib only ——
它在镜像仓里由 `uv run python` 执行, 不引第三方依赖。

用法::

    python set_conf.py --target '**/config/*.py' --pool tests/test_config.py [tests/...] \
        [--pyproject pyproject.toml] [--also-copy a b c] [--deselect x y] \
        [--timeout-multiplier 15.0] [--print]

设计要点(逐条对应可行性报告 26-10-08-0231 §10 的坑; 改这里之前先读那份):

- ``source_paths`` 必须写**整个 src** —— 写单文件会因包内相对 import 失败; 目标用 ``only_mutate`` 收窄。
- ``pytest_add_cli_args`` 必带 ``-n 0 --no-cov``(抵消 pytest.ini addopts 里的 ``-n 8``, 以及
  tests/conftest.py 按平台设的覆盖率闸)
  以及**文本层守阵**的 ``--deselect``: mutmut 把变异体写进同一份文件, 凡「读源码文本做断言」的守阵
  在基线就红, 整轮直接中断(实测两条, 见 ``DEFAULT_DESELECT``; 它们会随测试文件拆分漂移, 报错时先核这里)。
- ``process_isolation = "forkserver"`` —— 默认 ``fork`` 会让注册表类守阵假红。
- ``timeout_multiplier`` **必须显式写**(默认值 = mutmut 自身默认 15.0): 此前只在镜像里手工改
  (W5/W6 的 ``= 2``), 每次本脚本覆盖式重写都会静默抹掉, 于是「这一轮的超时口径」不可复现、
  TIMEOUT 数无法归因。``--timeout-multiplier`` 可覆盖(轮次宽/紧各档都要留痕)。
- ``also_copy`` 默认按镜像仓**顶层目录推导**(排除 vcs / 依赖 / 生成物), 漏一个基线就红;
  要精确控制用 ``--also-copy`` 覆盖(空串表示不写该键)。
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# 文本层守阵: 它们读源码文本做断言, 会被 mutmut 的变异体撑爆(实测报告 §10 #9)。
# 该表**会随测试文件拆分漂移**(test_web.py 已拆成 tests/test_web_*.py), 跑红时先核这里。
DEFAULT_DESELECT = (
    "tests/test_sim_corpus.py::test_fs_mock_coverage_static_guard",
    "tests/test_web_seed_center.py::test_api_enqueue_wakes_main_loop",
    "tests/test_traffic_store.py::test_v4_parse_skeleton_single_point",
    # W6(R30) 宽池轮新增: 以下 5 条读 core 目标源码文本(qbmanager/module 经 getsource/read_text
    # 或全 src 扫描), 在变异树里对 src 文本敏感 —— 同 R28 test_v4_parse_skeleton 先例 deselect。
    "tests/test_qbmanager.py::test_periodic_flush_is_wired_in_run_loop",
    "tests/test_qbmanager.py::test_qbmanager_source_has_no_web_state_fields",
    "tests/test_core_modules.py::test_no_private_notify_access_from_outside",
    "tests/test_facade_modules.py::test_kernel_run_wiring_delegates_to_host",
    "tests/test_sync.py::test_no_synthetic_state_write_site",
    # W8(R32) S5a 起: test_spawn_args_pinned 断言 Windows-only 的 subprocess.CREATE_NO_WINDOW
    # (测试缺平台守卫, 同 issue 26-10-31-1539-deselect-guards 族), WSL 镜像里基线恒红 ——
    # 不 deselect 会打断 stats 收集(首轮曾靠镜像内临时第 9 条绕过, 这里固化成默认)。
    "tests/test_relocate_exec.py::test_spawn_args_pinned",
)

# also_copy 推导时的排除项: vcs / 依赖 / 生成物 / 本工具自身产物 —— 都不该进 mutants/ 副本。
DENY = {
    ".git",
    ".venv",
    "venv",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "htmlcov",
    "coverage",
    "mutants",
    "mutmut-cache.db",
    "playwright-report",
    "test-results",
    "tmp-analysis",
    ".zcode-tmp",
    ".workbuddy-ai",
    ".codebuddy",
    ".idea",
    "src",  # source_paths
    "tests",  # mutmut 自动带
    "uv.lock",  # mutmut 自动带
    "pyproject.toml",  # 本文件就是它
}

HEADER = "[tool.mutmut]"

#: 变异体超时倍数(mutmut: 相对「基线单测墙时」的倍数, 工具自身默认 15.0)。**显式写进 [tool.mutmut]**:
#  只在镜像里手工加的值会在下一次覆盖式重写时被静默抹掉(W5/W6 的 `timeout_multiplier = 2` 实证),
#  于是轮次参数不可复现、TIMEOUT 数无法归因。--timeout-multiplier 可按轮次覆盖, 但每次都会留痕。
DEFAULT_TIMEOUT_MULTIPLIER = 15.0


def strip_section(text: str, header: str = HEADER) -> str:
    """删掉 ``[tool.mutmut]`` 整段(含其下所有键), 保留其余内容与空行结构。"""
    lines = text.splitlines(keepends=True)
    out: list[str] = []
    skipping = False
    for line in lines:
        stripped = line.strip()
        if not skipping and stripped == header:
            skipping = True
            continue
        if skipping:
            # 段到下一个表头(或文件尾)为止; 注释与空行都算段内。
            if stripped.startswith("[") and stripped.endswith("]"):
                skipping = False
            else:
                continue
        out.append(line)
    # 去掉尾部多余空行, 统一以一个换行收尾
    return "".join(out).rstrip("\n") + "\n"


def derive_also_copy(root: Path) -> list[str]:
    """镜像仓顶层条目里「测试可能用到」的那批 —— 排除项见 ``DENY``。"""
    names = []
    for entry in sorted(root.iterdir()):
        name = entry.name
        if name in DENY or name.startswith(".coverage"):
            continue
        names.append(name)
    return names


def render(
    target: str,
    pool: list[str],
    also_copy: list[str],
    deselect: list[str],
    timeout_multiplier: float = DEFAULT_TIMEOUT_MULTIPLIER
) -> str:
    def arr(items: list[str]) -> str:
        return "[" + ", ".join('"' + i + '"' for i in items) + "]"

    cli = ["-x", "-q", "-n", "0", "--no-cov"]
    for d in deselect:
        cli += ["--deselect", d]
    body = [
        HEADER,
        'source_paths = ["src"]',
        f"only_mutate = {arr([target])}",
        f"timeout_multiplier = {timeout_multiplier:g}",
        f"pytest_add_cli_args = {arr(cli)}",
        'process_isolation = "forkserver"',
        "use_git_change_detection = false",
    ]
    if pool:
        body.append(f"pytest_add_cli_args_test_selection = {arr(pool)}")
    if also_copy:
        body.append(f"also_copy = {arr(also_copy)}")
    return "\n".join(body) + "\n"


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--target", required=True, help="只变异的目标 glob(相对仓库根), 例 '**/config/*.py'")
    p.add_argument("--pool", nargs="*", default=[], help="测试选择池(相对仓库根); 留空=全 tests(不推荐, 会打挂 WSL)")
    p.add_argument("--pyproject", default="pyproject.toml", help="要改写的 pyproject.toml(默认当前目录)")
    p.add_argument("--also-copy", nargs="*", default=None, help="覆盖 also_copy(留空串=不写该键); 不传则按顶层目录推导")
    p.add_argument("--deselect", nargs="*", default=list(DEFAULT_DESELECT), help="文本层守阵(留空串=不 deselect)")
    p.add_argument(
        "--timeout-multiplier",
        type=float,
        default=DEFAULT_TIMEOUT_MULTIPLIER,
        help=f"变异体超时倍数(默认 {DEFAULT_TIMEOUT_MULTIPLIER:g}, 与 mutmut 默认一致; 显式写入才算轮次参数可复现)"
    )
    p.add_argument("--print", dest="to_stdout", action="store_true", help="只打印新段, 不落盘(自证用)")
    args = p.parse_args(argv)

    if not args.target.strip():
        sys.stderr.write("[FAIL] --target 不能为空\n")
        return 2
    if args.timeout_multiplier <= 0:
        sys.stderr.write(f"[FAIL] --timeout-multiplier 必须 > 0(收到 {args.timeout_multiplier:g})\n")
        return 2
    for f in args.pool:
        if not (Path(f).suffix == ".py" or "::" in f or Path(f).is_dir()):
            sys.stderr.write(f"[WARN] 池项看着不像测试文件: {f}\n")

    path = Path(args.pyproject)
    root = path.resolve().parent
    also_copy = derive_also_copy(root) if args.also_copy is None else [x for x in args.also_copy if x]
    deselect = [x for x in args.deselect if x]
    section = render(args.target, args.pool, also_copy, deselect, args.timeout_multiplier)

    if args.to_stdout:
        sys.stdout.write(section)
        return 0

    if not path.is_file():
        sys.stderr.write(f"[FAIL] 找不到 {path}\n")
        return 3
    old = path.read_text(encoding="utf-8")
    path.write_text(strip_section(old) + "\n" + section, encoding="utf-8")
    sys.stdout.write(f"[OK] {path}: only_mutate={args.target} pool={len(args.pool)} also_copy={len(also_copy)}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
