"""linux_e2e.py 守阵 —— test.linux-e2e(计划 26-11-12-0152 S3)的行为钉面。

只测**纯函数与生成的脚本文本**: 真起容器跑 e2e 属 `test.linux-e2e` 本体 —— 小时级、要浏览器,
不做守阵。生成面(bash 脚本)是纯文本, 文本断言即行为断言 —— 拆掉任一被钉面(symlink 接挂 /
fast 子集默认 / 动态端口 / UV_NO_SYNC / 内层 timeout / pid 标记)对应用例即红。
组件复用面钉「不复制」: tar 推送/slug/清扫/venv 语义单点在 linux_ci, 本模块不得自带第二份。

跑法: python <包>/scripts/test_linux_e2e.py  ·  uv run pytest .commands -q --no-cov (test.pkg 口径)

## 测试计划
- test_attach_plan_symlink_to_baked_template    接挂定案 = symlink /opt/e2e-node/node_modules(先 rm 再 ln -s), npm ci 不在运行路径
- test_attach_failure_rc26_distinct             接挂失败独立 rc 26 且 main 有对应 [FAIL] 行
- test_fast_subset_is_default                   默认 --grep @fast(与 Windows npm run test:e2e:fast 同口径), --full 去掉
- test_extra_args_passthrough_after_ddash       `--` 后参数原样追加(排障筛选透传面)
- test_no_fixed_port_injected                   脚本文本零固定口: 不出现 --port / E2E_PORT / UI_HARNESS_PORT(纪律单点 harness.mjs)
- test_uv_no_sync_exported                      export UV_NO_SYNC=1(HARNESS_CMD 是 uv run, 不许 sync 检查)
- test_auto_qb_testbed_not_exported             AUTO_QB_TESTBED 不导出(唯一消费方是 pytest 挂钟基准, e2e 不跑 pytest)
- test_env_base_lang_only_no_proxy              容器 -e 面只有 LANG 且 main 真消费该常量(代理不透传: 桩/chromium/npm 接挂面零外呼)
- test_run_pid_marker_and_exit_trap             .run-pid 开头写、记 bash $$、EXIT trap 自清(R6)
- test_venv_prep_same_route_as_linux_ci         venv 四步与 linux_ci 同款: cp 模板 + export --no-hashes + delta, 失败 rc 20-24
- test_inner_timeout_layering                   timeout 与 playwright test "$@" 单条钉紧耦合(消费端 $@ 同钉), 值 == INNER_E2E_TIMEOUT 字面 10800 且引擎 - 内层 >= 余量
- test_engine_timeout_pinned_in_config          config.toml 的 test.linux-e2e 引擎 timeout == ENGINE_TIMEOUT 字面 11400(防漂移)
- test_parse_args_flags_and_ddash               --python/--name/--full 解析; 未知旗标响亮拒绝; -- 分隔透传
- test_safety_probe_admits_action_without_args  `--safety` 自认 action-without-args(闸门别白跑小时级 e2e)
- test_no_component_duplication_from_linux_ci   不复制 linux_ci 组件: EXCLUDES/tar_cmd/extract_script/sweep_script/sanitize_name/auto_slug/pick_venv_template 无第二份
"""

from __future__ import annotations

import tomllib
from pathlib import Path

import linux_ci
import linux_e2e

SCRIPT = linux_e2e.run_script()
ROOT = Path(__file__).resolve().parents[3]  # <root>/.commands/test/scripts/test_linux_e2e.py

# ---- 接挂方案(计划 D4/S3 定案面) ----


def test_attach_plan_symlink_to_baked_template() -> None:
    assert linux_e2e.E2E_NODE_MODULES == "/opt/e2e-node/node_modules"
    # 悬空守卫先行(评审 major): ln -s 对不存在目标照样建悬空链接, 缺层 6 必须在接挂处
    # 响亮 exit 26, 不能等 playwright 期以 rc 127 炸出被误归因「docker exec 自身失败」
    assert f"[ -d {linux_e2e.E2E_NODE_MODULES} ] ||" in SCRIPT
    assert f"rm -rf node_modules && ln -s {linux_e2e.E2E_NODE_MODULES} node_modules" in SCRIPT
    assert "npm ci" not in SCRIPT, "npm ci 是回退路线不是定案, 不许回到运行路径(理由见模块 docstring)"


def test_attach_failure_rc26_distinct() -> None:
    assert "exit 26" in SCRIPT
    src = Path(linux_e2e.__file__).read_text(encoding="utf-8")
    assert "elif rc == 26:" in src and "node_modules 接挂失败(rc=26)" in src


# ---- 子集选择 ----


def test_fast_subset_is_default() -> None:
    assert linux_e2e.e2e_playwright_args(full=False, extra=[]) == ["--grep", "@fast"]
    assert linux_e2e.e2e_playwright_args(full=True, extra=[]) == []


def test_extra_args_passthrough_after_ddash() -> None:
    args = linux_e2e.e2e_playwright_args(full=False, extra=["--reporter=line"])
    assert args == ["--grep", "@fast", "--reporter=line"]
    _, _, full, extra = linux_e2e._parse_args(["--full", "--", "-k", "抽屉"])
    assert full and extra == ["-k", "抽屉"]


# ---- 动态端口 ----


def test_no_fixed_port_injected() -> None:
    for banned in ("--port", "E2E_PORT", "UI_HARNESS_PORT"):
        assert banned not in SCRIPT, (
            f"脚本文本不得出现 {banned}: e2e 端口纪律单点在 e2e/harness.mjs(--port 0 OS 分配 "
            "+ webServer.wait 捕获), 本 task 不引入固定口不覆盖端口变量"
        )


# ---- env 取舍 ----


def test_uv_no_sync_exported() -> None:
    assert "export UV_NO_SYNC=1" in SCRIPT


def test_auto_qb_testbed_not_exported() -> None:
    assert "AUTO_QB_TESTBED" not in SCRIPT
    assert all("AUTO_QB_TESTBED" not in f"{k}={v}" for k, v in linux_e2e.E2E_ENV_BASE)


def test_env_base_lang_only_no_proxy() -> None:
    assert linux_e2e.E2E_ENV_BASE == (("LANG", "C.UTF-8"),
                                     ), ("e2e 容器 -e 面只有 LANG: 代理不透传(桩/chromium/npm 接挂面零外呼, 取舍见模块 docstring)")
    # 常量钉住还不够(评审): 换回 container_env() 全量 env 常量仍绿 —— 消费点必须真用 E2E_ENV_BASE
    src = Path(linux_e2e.__file__).read_text(encoding="utf-8")
    assert "_exec_env(list(E2E_ENV_BASE)" in src, (
        "main 的 docker exec -e 面必须从 E2E_ENV_BASE 取值, 不许改回 linux_ci.container_env()"
        "(那会把宿主代理透传给 chromium, e2e 不需要)"
    )


# ---- 容器内主脚本其余钉面 ----


def test_run_pid_marker_and_exit_trap() -> None:
    assert 'printf \'%s\\n\' "$$" > "$AQB_WORK/.run-pid"' in SCRIPT
    assert "trap 'rm -f \"$AQB_WORK/.run-pid\"' EXIT" in SCRIPT


def test_venv_prep_same_route_as_linux_ci() -> None:
    assert 'cp -a "$AQB_VENV/." .venv/' in SCRIPT  # S1 拍板: cp 模板, 不 uv sync 全建
    assert "uv export --frozen --format requirements-txt --no-hashes" in SCRIPT
    assert "uv sync" not in SCRIPT  # R4: sync --frozen 不吃镜像索引(机制事实)
    for rc in (20, 21, 22, 23, 24):  # 24 = workdir/code 不在守卫(姊妹阵 test_linux_ci 同钉全段)
        assert f"exit {rc}" in SCRIPT


def test_inner_timeout_layering() -> None:
    # 单条钉紧耦合含消费端 "$@": timeout 行被改掉 "$@" 后 --full/-- 透传会静默失效, 守阵必须红
    assert (
        f'timeout -k {linux_e2e.TIMEOUT_KILL_GRACE} {linux_e2e.INNER_E2E_TIMEOUT} '
        'node_modules/.bin/playwright test "$@"'
    ) in SCRIPT
    assert linux_e2e.INNER_E2E_TIMEOUT == 10800, "预算字面钉死(实测全量 59.2m 的 ~3x), 防静默放宽/收窄"
    assert linux_e2e.ENGINE_TIMEOUT - linux_e2e.INNER_E2E_TIMEOUT >= linux_e2e.ENGINE_TIMEOUT_MARGIN


def test_engine_timeout_pinned_in_config() -> None:
    assert linux_e2e.ENGINE_TIMEOUT == 11400, "引擎预算字面钉死(内层 10800 + 余量 600), 防静默漂移"
    cfg = tomllib.loads((ROOT / ".commands" / "test" / "config.toml").read_text(encoding="utf-8"))
    task = cfg["tasks"]["test.linux-e2e"]
    assert task["timeout"] == linux_e2e.ENGINE_TIMEOUT
    assert task["script"] == "linux_e2e.py"


# ---- 入口面 ----


def test_parse_args_flags_and_ddash() -> None:
    py, name, full, extra = linux_e2e._parse_args(["--python", "3.12", "--name", "s3-x"])
    assert (py, name, full, extra) == ("3.12", "s3-x", False, [])
    assert linux_e2e._parse_args([]) == (linux_ci.DEFAULT_PYTHON, "", False, [])
    for bad in (["--bogus"], ["--python"]):  # 未知旗标 / 缺值
        try:
            linux_e2e._parse_args(bad)
        except ValueError:
            pass
        else:
            raise AssertionError(f"{bad} 应响亮拒绝")


def test_safety_probe_admits_action_without_args() -> None:
    import io
    import contextlib

    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = linux_e2e.main(["--safety"])
    assert rc == 0 and buf.getvalue().strip() == "action-without-args"


# ---- 组件复用面 ----


def test_no_component_duplication_from_linux_ci() -> None:
    for name in (
        "EXCLUDES", "tar_cmd", "extract_script", "sweep_script", "sanitize_name", "auto_slug", "pick_venv_template"
    ):
        assert not hasattr(linux_e2e, name), (f"{name} 单点在 linux_ci, 本模块不许复制第二份(改哪处只改一处)")
    assert linux_e2e.CONTAINER == linux_ci.CONTAINER
    assert linux_e2e.TIMEOUT_KILL_GRACE == linux_ci.TIMEOUT_KILL_GRACE


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    failed = 0
    for fn_name, fn in sorted(globals().items()):
        if fn_name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"PASS {fn_name}")
            except AssertionError as exc:
                failed += 1
                print(f"FAIL {fn_name}: {exc}")
    sys.exit(1 if failed else 0)
