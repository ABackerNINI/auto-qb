"""linux_ci.py 守阵 —— docker exec 常驻容器形态(计划 26-11-12-0152 S2)的行为钉面。

只测**纯函数与生成的脚本文本**: 真起容器跑全量属 `test.linux` 本体 —— 慢、要网, 不做守阵。
生成面(bash 脚本)是纯文本, 文本断言即行为断言 —— 拆掉任一被钉面(排除清单项 / 内层 timeout /
pid 标记 / 双条件清扫 / delta 路线)对应用例即红。容器网络纯函数(container_env / rewrite_proxy)
钉面沿用 2026-10-11 立的阵: 回环改写 + no_proxy 恒并回环(缺任一 => 回环端点用例假红)。

跑法: python <包>/scripts/test_linux_ci.py  ·  uv run pytest .commands -q --no-cov (test.pkg 口径)

## 测试计划
- test_loopback_proxy_rewritten_to_host_gateway   回环代理 -> host.docker.internal(容器直收 -e)
- test_non_loopback_proxy_passes_through          真网关代理原样透传
- test_no_proxy_always_covers_loopback            no_proxy 恒并入回环(缺它 => 回环用例被代理拦截)
- test_lang_is_pinned_for_utf8_output             LANG 仍钉 C.UTF-8
- test_safety_probe_admits_action_without_args    `--safety` 自认 action-without-args(闸门别白跑全量)
- test_excludes_match_plan_d4_list                tar 排除清单逐项对齐计划 D4(不多不少)
- test_tar_cmd_streams_whole_tree_with_git        打包整棵工作树进 stdin 流, .git 不在排除面
- test_extract_script_unpacks_to_work_code        解包前同 slug 存活守卫(exit 30), 解包段先写标记再快照 rm, 落 $AQB_WORK/code
- test_pick_venv_template_d3_both_baked           3.12/3.13 双模板路径, 其余版本响亮拒绝
- test_auto_slug_shape                            自动 slug = aqb-<pid>-<时刻>
- test_sanitize_name_rejects_unsafe               --name 收紧 slug 安全集, 路径毒字符拒收
- test_run_script_inner_timeout_layering          timeout 与 pytest 本体单条钉紧耦合, 值 < 引擎 1800 且余量 >= 240s
- test_run_script_exports_testbed_profile         pytest 前 export AUTO_QB_TESTBED=1(挂钟性能基准选 testbed 档: 容器配额/并行会话放大非回归)
- test_run_script_writes_and_clears_run_pid       .run-pid 开头写、记 bash $$、EXIT trap 自清(R6, 覆盖 venv 准备段)
- test_run_script_uses_export_pip_delta_route     delta 走 export --no-hashes + uv pip install, 无 uv sync; 准备段失败 rc 20-24 各带 [FAIL]+NEXT
- test_run_script_copies_template_venv            首建 cp -a 模板 venv, 不全建(S1 拍板 R4)
- test_sweep_double_condition_and_bounded_root    清扫 = pid 死 + mtime 超龄双条件, 值钉 12h(对齐 _tmp_bootstrap), 只动 /root/auto-qb-tests/
- test_engine_timeout_pinned_1800                 config.toml 的 test.linux 引擎 timeout 钉 1800(防回退 900)
"""

from __future__ import annotations

import importlib.util
import re
import tomllib
from pathlib import Path

import linux_ci

LOOPBACK = {"127.0.0.1", "localhost", "::1"}
ENGINE_TIMEOUT_LIMIT = 1800  # .commands/test/config.toml 里 test.linux 的引擎包装超时

# ---- 代理透传(保留面) ----


def test_loopback_proxy_rewritten_to_host_gateway() -> None:
    pairs = linux_ci.container_env({
        "http_proxy": "http://127.0.0.1:4085",
        "HTTPS_PROXY": "http://localhost:8080/",
    })
    env = dict(pairs)
    assert env["http_proxy"] == "http://host.docker.internal:4085"
    assert env["HTTPS_PROXY"] == "http://host.docker.internal:8080/"


def test_non_loopback_proxy_passes_through() -> None:
    pairs = linux_ci.container_env({"http_proxy": "http://10.1.2.3:3128"})
    assert dict(pairs)["http_proxy"] == "http://10.1.2.3:3128"


def test_no_proxy_always_covers_loopback() -> None:
    for seed in ({}, {"no_proxy": "example.com"}, {"http_proxy": "http://127.0.0.1:4085"}):
        env = dict(linux_ci.container_env(seed))
        bypass = set(env["no_proxy"].split(","))
        assert LOOPBACK <= bypass, seed
        assert env["no_proxy"] == env["NO_PROXY"]
        if "example.com" in (seed.get("no_proxy") or ""):
            assert "example.com" in bypass, "宿主已有的放行项不许被覆盖"


def test_lang_is_pinned_for_utf8_output() -> None:
    assert dict(linux_ci.container_env({}))["LANG"] == "C.UTF-8"


def test_safety_probe_admits_action_without_args() -> None:
    assert linux_ci.main(["--safety"]) == 0


# ---- D4 推模式: tar 流 ----


def test_excludes_match_plan_d4_list() -> None:
    assert set(linux_ci.EXCLUDES) == {
        "__pycache__",
        ".venv",
        "node_modules",
        "dist",
        ".tools",
        ".coverage",
        ".coverage.*",
        ".pytest_cache",
        ".ruff_cache",
        "auto-qb-data",
        "tmp-analysis",
    }
    assert all(not p.startswith("/") for p in linux_ci.EXCLUDES), "排除模式必须是相对形态"


def test_tar_cmd_streams_whole_tree_with_git() -> None:
    root = Path("repo-root")
    cmd = linux_ci.tar_cmd(root)
    assert cmd[:2] == ["tar", "-C"] and cmd[2] == str(root), "打包基准 = 仓库根"
    for pat in linux_ci.EXCLUDES:
        assert pat in cmd, f"排除清单项漏传: {pat}"
    assert "-cf" in cmd and cmd[-2:] == ["-", "."], "输出走 stdin 流, 打包整棵树"
    assert ".git" not in linux_ci.EXCLUDES, ".git 必须随拷(find_root 坑)"


def test_extract_script_unpacks_to_work_code() -> None:
    script = linux_ci.extract_script()
    # 同 slug 存活守卫(D5): 前一轮孤儿/同名并发双启时, 不许在活进程头顶删 code 双跑 pytest
    assert "kill -0" in script and "exit 30" in script, "标记 pid 仍活 -> [FAIL] exit 30 拒删 code"
    assert "[FAIL]" in script and "NEXT:" in script, "存活拒绝行自带 NEXT(换 --name / 等结束或清扫)"
    guard = script.index("kill -0")
    rm = script.index('rm -rf "$AQB_WORK/code"')
    marker = script.index('printf \'%s\\n\' "$$" > "$m"')
    assert guard < marker < rm, "顺序: 存活核验 -> 写解包段标记 -> 才许 rm(快照语义)"
    assert "trap" not in script, "解包段标记不设 trap(被杀 = bash 死 pid 留存, 交下轮 sweep 回收)"
    assert script.index('mkdir -p "$AQB_WORK/code"') > rm, "先删后建再解(顺序错了快照语义失效)"
    assert "tar -xf - -C" in script, "从 stdin 解 tar 流"


# ---- 会话面(D5) ----


def test_pick_venv_template_d3_both_baked() -> None:
    assert linux_ci.pick_venv_template("3.12") == "/opt/venv-3.12"
    assert linux_ci.pick_venv_template("3.13") == "/opt/venv-3.13"
    try:
        linux_ci.pick_venv_template("3.14")
    except ValueError as exc:
        assert "3.12" in str(exc) and "3.13" in str(exc), "失败行带已烘版本指引"
    else:
        raise AssertionError("未烘的版本必须响亮拒绝, 不许静默回落")


def test_auto_slug_shape() -> None:
    assert re.fullmatch(r"aqb-\d+-\d{8}T\d{6}", linux_ci.auto_slug()), "aqb-<pid>-<时刻>"


def test_sanitize_name_rejects_unsafe() -> None:
    assert linux_ci.sanitize_name("My-Run") == "my-run", "大写折小写(只此一处静默变换)"
    for bad in ("../evil", "a b", "my_run", "-lead", "", "x" * 65):
        try:
            linux_ci.sanitize_name(bad)
        except ValueError:
            continue
        raise AssertionError(f"毒 slug 应拒收: {bad!r}")


# ---- 容器内主脚本 ----


def test_run_script_exports_testbed_profile() -> None:
    script = linux_ci.run_script()
    assert "export AUTO_QB_TESTBED=1" in script and script.index("export AUTO_QB_TESTBED=1") < script.index(
        ".venv/bin/python -m pytest"
    ), "pytest 前必须置 testbed 档标记: 挂钟性能基准按容器实测档判(并行会话放大非回归)"


def test_run_script_inner_timeout_layering() -> None:
    script = linux_ci.run_script()
    # 单条钉紧耦合: timeout 必须直接包裹 pytest 本体 —— 拆成两条独立子串断言时,
    # 变异把 timeout 挪去包裹别的命令而两段子串各自仍在, 会假绿。
    assert (
        f"timeout -k {linux_ci.TIMEOUT_KILL_GRACE} {linux_ci.INNER_PYTEST_TIMEOUT} "
        ".venv/bin/python -m pytest tests -q"
    ) in script, "pytest 必须被容器内 timeout 内层直接包裹(R6: 内层先到先干净退出)"
    margin = ENGINE_TIMEOUT_LIMIT - linux_ci.INNER_PYTEST_TIMEOUT
    assert margin >= 240, f"内外层余量 {margin}s < 240s: tar 推送 + venv 准备没地方放"


def test_run_script_writes_and_clears_run_pid() -> None:
    script = linux_ci.run_script()
    marker = 'printf \'%s\\n\' "$$" > "$AQB_WORK/.run-pid"'
    assert marker in script, "标记在脚本开头写入且记 bash 自身 pid(覆盖 venv 准备段, 客户端被杀即死)"
    assert script.index(marker) < script.index("cd \"$AQB_WORK/code\""), "标记先于一切准备步(后置会漏准备段)"
    assert 'trap \'rm -f "$AQB_WORK/.run-pid"\' EXIT' in script, "EXIT trap 自清(正常/准备段失败均清; SIGKILL 不跑 trap = 留给 sweep)"
    assert "$PT_PID" not in script, "旧形态(timeout 子进程 pid)已退役"


def test_run_script_uses_export_pip_delta_route() -> None:
    script = linux_ci.run_script()
    assert "uv export --frozen --format requirements-txt --no-hashes" in script, \
        "delta 走 export --no-hashes(S1 拍板: 锁文件绝对 URL 不吃镜像索引, 计划 §10 R4)"
    assert "uv pip install" in script and "-e . --no-deps" in script, "editable 补装项目本体"
    assert "uv sync" not in script, "禁 uv sync --frozen(下载源按锁文件绝对 URL 直连, 镜像索引无效)"
    for code in ("exit 20", "exit 21", "exit 22", "exit 23", "exit 24"):
        assert code in script, f"准备段失败须独立 rc({code})与 pytest 失败可分辨"
    fail_lines = [line for line in script.splitlines() if "[FAIL]" in line]
    assert len(fail_lines) == 5 and all("NEXT:" in line for line in fail_lines), \
        "准备段每步失败行自带 NEXT(生产口径)"


def test_run_script_copies_template_venv() -> None:
    script = linux_ci.run_script()
    assert 'cp -a "$AQB_VENV/." .venv/' in script, "首建 cp -a 模板 venv(不全建)"
    assert '[ ! -x .venv/bin/python ]' in script, "已有 venv 时跳过 cp(幂等复用)"


# ---- R6 兜底清扫 ----


def test_sweep_double_condition_and_bounded_root() -> None:
    script = linux_ci.sweep_script(linux_ci.SWEEP_AGE_SECONDS)
    assert f"-ge {linux_ci.SWEEP_AGE_SECONDS}" in script, "mtime 超龄条件在"
    assert "kill -0" in script, "内嵌 pid 已死条件在 —— 双条件缺一不可, 绝不按名字猜删"
    assert '[ -f "$m" ] || continue' in script, "无 .run-pid 标记的目录绝不碰"
    root = linux_ci.TESTS_ROOT
    assert f'root="{root}"' in script and "$root" in script, "清扫只动 /root/auto-qb-tests/ 面"
    assert script.count('rm -rf "$d"') == 1, "只 rmtree 整个 workdir, 不钻子树"
    # 阈值强钉: 常量注入再核对自身是同义反复, 阈值漂离 12h 须红 —— 对齐单点
    # tests/_tmp_bootstrap.py::CLEAN_AGE_HOURS(与 linux_ci 头注宣称口径一致)。
    spec = importlib.util.spec_from_file_location(
        "_tmp_bootstrap_pin",
        Path(linux_ci.__file__).resolve().parents[3] / "tests" / "_tmp_bootstrap.py",
    )
    assert spec is not None and spec.loader is not None
    bootstrap = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(bootstrap)
    assert linux_ci.SWEEP_AGE_SECONDS == int(bootstrap.CLEAN_AGE_HOURS * 3600), \
        "清扫 mtime 阈值须对齐 _tmp_bootstrap.CLEAN_AGE_HOURS(头注宣称同款纪律)"


# ---- 引擎面 ----


def test_engine_timeout_pinned_1800() -> None:
    cfg_path = Path(linux_ci.__file__).resolve().parents[1] / "config.toml"
    with cfg_path.open("rb") as fh:
        cfg = tomllib.load(fh)
    timeout = cfg["tasks"]["test.linux"]["timeout"]
    assert timeout == ENGINE_TIMEOUT_LIMIT, \
        f"引擎包装超时钉 {ENGINE_TIMEOUT_LIMIT}(900s 旧值连推送带全量必超, issue 26-11-12-0053)"
    assert linux_ci.INNER_PYTEST_TIMEOUT < timeout, "内层必须先于引擎包装到点, 否则分层失效"
