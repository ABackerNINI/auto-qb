"""test.random-order —— pytest-randomly 随机序周巡检入口(计划 26-11-05-0118 S6/D10/D13)。

用法(经 commands 引擎调进来, `--` 后传参):
    commands run test.random-order --                     # 1 轮, 随机 seed
    commands run test.random-order -- --samples 3         # 3 轮统计采样, 各轮独立随机 seed
    commands run test.random-order -- --seed 42           # 固定 seed 复现某一轮(红灯复现用)
    commands run test.random-order -- -- -k hr            # `--` 后再传参透传给 pytest

设计:
- **主套件默认顺序不动**: pytest.ini addopts 以 `-p no:randomly` 整体禁用该插件; 本入口用
  `-o addopts=...` 整体替换 ini addopts(去掉禁用行), 插件才加载 —— 随机序只在这条入口发生。
- **可复现**: 每轮打印 `--randomly-seed=<N>`(pytest-randomly 头部输出); 红灯时额外打印
  固定 seed 的完整复现命令。
- **统计采样 = 多轮独立运行**, 不用 rerun 插件: 任一轮红即退出非零(D9 口径 —— reruns 不作
  遮羞布, 红灯拿 seed 复现归因后走 flaky 台账, 台账见 memory-bank/testing/flaky-ledger.md
  「巡检约定」节)。
- **不改生产面**: pytest-randomly 是 dev 依赖, 本入口不碰 config.yml / 生产配置键。

TMPDIR: 原样透传环境(由子进程 pytest 的 tests/_tmp_bootstrap.py 自举探测, 外部 TMPDIR 会被
rc=4 拒收 —— 与 test.pkg.scoped 同口径)。
"""

from __future__ import annotations

import random
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]  # .commands/test/scripts/ → 仓库根

# 覆盖 pytest.ini addopts 的替换值: 保留并行度, 去掉 `-p no:randomly`(插件因此加载)与
# 覆盖率旗标(巡检是采样不是门禁, 不吃覆盖率开销; pytest-cov 插件仍自动加载, 语义不变)。
ADDOPTS_OVERRIDE = "-n 8"


def plan(argv: list[str]) -> tuple[int, int | None, list[str]]:
    """argv → (轮数, 固定 seed 或 None, 透传给 pytest 的额外参数)。纯函数, 便于单测。

    `--` 之后的参数原样透传; `--` 之前只认 --samples/--seed, 其它一律报错(exit 由调用方处理:
    返回 ValueError 让 main 打用法)。
    """
    samples, seed, extra, passthrough = 1, None, [], False
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--":
            passthrough = True
        elif passthrough:
            extra.append(a)
        elif a == "--samples":
            i += 1
            if i >= len(argv):
                raise ValueError("--samples 缺值")
            samples = int(argv[i])
            if samples < 1:
                raise ValueError(f"--samples 必须 >= 1, 得到 {samples}")
        elif a == "--seed":
            i += 1
            if i >= len(argv):
                raise ValueError("--seed 缺值")
            seed = int(argv[i])
        else:
            raise ValueError(f"未知参数: {a}(透传给 pytest 的参数放在 `--` 之后)")
        i += 1
    return samples, seed, extra


def build_cmd(seed: int, extra: list[str]) -> list[str]:
    """单轮 pytest 命令(纯函数, 便于单测): -o addopts= 整体替换 ini addopts 是随机序的开关。"""
    return [
        "uv", "run", "pytest", "tests", "-q", "--no-cov", "-o", f"addopts={ADDOPTS_OVERRIDE}",
        f"--randomly-seed={seed}", *extra
    ]


def reproduction_cmd(seed: int, extra: list[str]) -> str:
    return subprocess.list2cmdline(build_cmd(seed, extra))


def main(argv: list[str] | None = None) -> int:
    try:
        samples, fixed_seed, extra = plan(list(sys.argv[1:] if argv is None else argv))
    except ValueError as e:
        print(f"[STOP] {e}\n用法见本文件头部 docstring", file=sys.stderr)
        return 2
    failed: list[tuple[int, int]] = []  # (轮次, seed)
    for n in range(1, samples + 1):
        seed = fixed_seed if fixed_seed is not None else random.SystemRandom().randrange(1, 2**31)
        print(f"[random-order] === 第 {n}/{samples} 轮, seed={seed} ===", flush=True)
        proc = subprocess.run(build_cmd(seed, extra), cwd=str(REPO_ROOT))
        if proc.returncode != 0:
            failed.append((n, seed))
            print(f"[random-order] 第 {n} 轮红(seed={seed})。固定 seed 复现:\n  {reproduction_cmd(seed, extra)}", flush=True)
    if failed:
        print(
            f"[random-order] {len(failed)}/{samples} 轮失败: {failed} —— 红灯先固定 seed 复现归因, "
            f"再走 flaky 台账(memory-bank/testing/flaky-ledger.md 巡检约定), reruns 不是修复",
            file=sys.stderr
        )
        return 1
    print(f"[random-order] {samples} 轮全绿(seeds: 见各轮头部)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
