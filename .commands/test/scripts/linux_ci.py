"""本机复现 Linux CI: Docker testbed 常驻容器形态(计划单点:
[memory-bank/plans/26-11-12-0152-plan-linux-testbed-docker.html](../../../memory-bank/plans/26-11-12-0152-plan-linux-testbed-docker.html)
§03「代码同步(D4)」「workdir 布局与并行(D5)」/ §04 S2 / §06 D4-D8)。

**形态**(S2 起, 替代旧 docker run --rm 一次性容器): 前置 `commands run test.linux-env`
建好的常驻容器 auto-qb-testbed(D1); 本脚本每轮:

1. 前置核验: 容器不在/不在跑 -> [FAIL] 指引 `commands run test.linux-env`, **不自动构建**
   (环境面与测试面分离, 构建可能十几分钟且要人工开代理, 不能藏在测试入口里)。
2. workdir 就绪: `/root/auto-qb-tests/<slug>/`(slug: `--name` 传参或自动
   `aqb-<pid>-<时刻>`; D5 每会话独立, 互不相见)。
3. 代码推送(D4 推模式, 可测未提交 WIP): 宿主 `tar --exclude=<清单>` 打包工作树(含
   `.git` 与 WIP)经管道进 `docker exec -i` 解到 `<work>/code`。解包前先核同 slug 存活
   标记(pid 活 -> [FAIL] exit 30, 不在活进程头顶删 code 并发全量, D5), 解包是**快照
   语义**(先 `rm -rf` 旧 code 再解: 推模式本就是全量树, 复用同名 slug 重跑时宿主已删/
   改名的文件不会以旧残留留在容器里被 pytest 收到; 旧 .venv 一并重来, cp 模板秒级可接受)。
   **`.git` 必须随拷** —— `test_commands_engine` 的 find_root() 靠向上找 `.git`, 删了多
   5 条假红(坑档单点 pitfalls/testing/attachments/patching-local-linux-repro.md
   「Docker 等价复现」节)。排除清单见 EXCLUDES(计划 D4 逐项); auto-qb-data 在清单内 =
   不读不拷, 红线面零接触。
4. venv 就绪(取舍留痕, S1 拍板 2026-11-12): **cp -a 模板 venv**(`/opt/venv-3.12` 或
   `/opt/venv-3.13`)而非 uv sync 全建 —— uv sync --frozen 的下载源按 uv.lock 里 787 个
   files.pythonhosted.org 绝对 URL 直连, 烘进镜像的国内索引对它无效(计划 §10 R4 机制事实)。
   依赖 delta 走 **uv export --no-hashes + uv pip install**(吃镜像索引; 模板 venv 已含全部
   钉版依赖时 `uv pip install -r` 秒级 no-op —— 2026-11-12 容器内实测 0.17s), 再
   `uv pip install -e . --no-deps` 补项目 editable。计划 D4 的「cp 模板 vs uv sync 全建
   取快者」由 T2b 全量实跑计时裁决, 当前 cp+delta 路线即为此形态(全建路线本就因 R4 弃用)。
   venv 准备段各步失败独立报 rc 20-24 并带 [FAIL]+NEXT(生产口径, 与 pytest 自身失败可分辨)。
5. 容器内跑全量: **timeout 内层包裹 pytest**(R6 分层超时: 内层 1500s 先到 -> pytest 收
   SIGTERM 干净退出、FAILED 明细照出; 引擎包装 1800s 只兜外层 —— 两层差 300s 付给 tar
   推送 + venv 准备。健康全量时长由 T2b 实测后校准内层值)。输出全文透传。
   pytest 前置 `export AUTO_QB_TESTBED=1`: 挂钟型性能基准(test_rebuild_benchmark_5000_seeds)
   按 testbed 档判 —— 容器 8 vCPU 配额与并行会话(16 worker)对挂钟的放大是合法调度非回归
   (2026-11-12 S2 双开实证: solo rebuild 中位 1.1ms, 双开偶发越开发机严格档 4.0ms)。
6. 下轮兜底清扫(R6): 开跑前扫 `/root/auto-qb-tests/` 下带 `.run-pid` 标记的 workdir,
   「内嵌 pid 已死(容器内 kill -0) + mtime 超龄(12h, 与 tests/_tmp_bootstrap.py
   CLEAN_AGE_HOURS 同款)」**双条件缺一不可**, 只 rmtree 整个 workdir、不钻子树、不碰
   无标记目录、不越出该单根。标记**全程段在场**: 解包 exec 一开始就写(记解包 bash 自身
   pid, 不设 trap —— 被杀即死, kill -0 可判), run_script 随后覆盖为自身 pid 并设 EXIT
   trap 自清 —— 解包段/venv 准备段/pytest 段任一处被杀都有标记可回收(标记只挂在
   run_script 会漏解包段: 那段被杀时 workdir 无标记, sweep 永远不碰它)。

**代理透传(保留面, 计划 §04 S2 明示)**: 宿主代理变量里的回环主机改写成
host.docker.internal(Docker Desktop 内建 DNS, 容器内免 --add-host, 2026-11-12 getent 实证),
`no_proxy` 恒并入回环 —— 注了代理不放行回环时 `tests/test_hr_server.py` 回环端点用例假红
(实测 6 failed + 2 errors, 2026-10-11)。容器只接收显式 -e, 不透传宿主整张环境表。
坑档单点: pitfalls/testing/patching.md「容器网络坑」。

**MSYS_NO_PATHCONV 坑(Git Bash)**: 在 Git Bash 里**手工**敲 `docker exec ... bash -c
'mkdir /root/...'` 时, MSYS 会把容器绝对路径转成 Windows 路径(实测 /opt 被改写成
'D:/Program Files/Git/opt'), 必须前缀 `MSYS_NO_PATHCONV=1`。本脚本走 python subprocess
argv 列表, 不经 MSYS 转换层, 不受影响 —— 该坑只伤手工排障, 别把手工复现的报错当成脚本 bug。

守阵: `scripts/test_linux_ci.py`(红验: 拆掉排除清单任一项 / 内层 timeout / 双条件清扫即红)。
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

import linux_env  # 同包脚本: 容器名/状态单点, 不复制字面量

CONTAINER = linux_env.CONTAINER_NAME
#: 测试态单根(容器内; G3), 本脚本一切读写不越出它
TESTS_ROOT = "/root/auto-qb-tests"
#: 默认 Python(对齐 CI 矩阵与 .python-version=3.13); `--python 3.12` 切变体(D3 双模板)
DEFAULT_PYTHON = "3.13"
VENV_TEMPLATE = {"3.12": "/opt/venv-3.12", "3.13": "/opt/venv-3.13"}
#: D4 排除清单(计划 §03 实证面): 拷代码不拷构建/运行产物; .git / memory-bank / resources /
#: docs / tools / .commands / .agents 必须随拷(不在清单即随拷)
EXCLUDES = (
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
)
#: R6 分层超时: 内层(pytest)先到, 引擎包装 1800s(.commands/test/config.toml)兜外层
INNER_PYTEST_TIMEOUT = 1500
#: 清扫 mtime 超龄阈值(秒), 对齐 tests/_tmp_bootstrap.py::CLEAN_AGE_HOURS
SWEEP_AGE_SECONDS = int(12.0 * 3600)
TIMEOUT_KILL_GRACE = 30  # 内层 timeout 到点后 SIGKILL 前的宽限

# ---- 代理透传(保留面, 理由见模块 docstring) ----
LOOPBACK_HOSTS = ("127.0.0.1", "localhost", "::1", "[::1]")
PROXY_KEYS = ("http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY")
NO_PROXY_KEYS = ("no_proxy", "NO_PROXY")
NO_PROXY_ALWAYS = ("127.0.0.1", "localhost", "::1")


def rewrite_proxy(value: str) -> tuple[str, bool]:
    """代理 URL 里的回环主机 -> `host.docker.internal`; 返回 (新值, 是否改写过)。

    只动主机段(`//` 之后、端口/路径之前), 免得不小心碰上路径里恰好出现的同名字符串。
    """
    out, changed = value, False
    for host in LOOPBACK_HOSTS:
        pat = rf"(?<=//){re.escape(host)}(?=[:/]|$)"
        new = re.sub(pat, "host.docker.internal", out, count=1, flags=re.IGNORECASE)
        if new != out:
            out, changed = new, True
    return out, changed


def container_env(environ: dict[str, str] | None = None) -> list[tuple[str, str]]:
    """宿主环境 -> 容器 `-e` 列表(docker exec 用)。

    - 代理变量照传, 但回环主机改写(否则容器拿它指自己, 走不出宿主代理)。
    - `no_proxy` / `NO_PROXY` 恒并入回环 —— 注了代理却不放行回环时, 回环端点用例集体假红。
    - 宿主其余变量(含 TMPDIR)**一律不透传**: 容器内 TMPDIR 由 tests/_tmp_bootstrap.py
      在 pytest 进程内自举, 宿主值漏进去会触发外部 TMPDIR 拒收(rc=4)。
    """
    env: dict[str, str] = dict(os.environ if environ is None else environ)
    pairs: list[tuple[str, str]] = [("LANG", "C.UTF-8")]
    for key in PROXY_KEYS:
        raw = (env.get(key) or "").strip()
        if not raw:
            continue
        val, _changed = rewrite_proxy(raw)
        pairs.append((key, val))
    bypass = set(NO_PROXY_ALWAYS)
    for key in NO_PROXY_KEYS:
        bypass.update(p.strip() for p in re.split(r"[,\s]+", env.get(key) or "") if p.strip())
    bypass_line = ",".join(sorted(bypass))
    pairs.extend((key, bypass_line) for key in NO_PROXY_KEYS)
    return pairs


def pick_venv_template(py_ver: str) -> str:
    """`--python` 值 -> 模板 venv 绝对路径; 只认烘进镜像的两个版本(D3), 其余响亮拒绝。"""
    if py_ver not in VENV_TEMPLATE:
        raise ValueError(
            f"不支持的 Python 版本: {py_ver}(镜像只烘了 {'/'.join(sorted(VENV_TEMPLATE))}; "
            "要加版本先改 .commands/test/docker/Dockerfile 层 5 再重跑 test.linux-env)"
        )
    return VENV_TEMPLATE[py_ver]


def auto_slug() -> str:
    """自动会话名: aqb-<pid>-<时刻>, 与 D5「pid+时刻」口径一致(可读且不撞)。"""
    return f"aqb-{os.getpid()}-{time.strftime('%Y%m%dT%H%M%S')}"


def sanitize_name(name: str) -> str:
    """`--name` 会话名收紧为 slug 安全集([a-z0-9-], 作容器内路径段), 不合即响亮拒绝。"""
    slug = name.strip().lower()
    if not slug or not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,63}", slug):
        raise ValueError(f"--name 不合 slug 安全集: {name!r}(只收小写字母/数字/连字符, 首字符字母或数字, <=64 字符)")
    return slug


def tar_cmd(root: Path) -> list[str]:
    """宿主侧 tar 打包命令(D4 推模式): stdin 流, 排除清单逐项, 工作树整棵含 .git 与 WIP。"""
    cmd = ["tar", "-C", str(root)]
    for pat in EXCLUDES:
        cmd += ["--exclude", pat]
    return cmd + ["-cf", "-", "."]


def extract_script() -> str:
    """容器侧解包脚本(docker exec -i 的 stdin 是 tar 流)。

    三件事(顺序即安全性):
    1. 同 slug 存活守卫: 标记 pid 仍活 -> [FAIL] exit 30, 不删其 code 不并发全量(D5:
       前一轮孤儿 sweep 正确跳过 / 同名会话并发双启时, 头顶删 code 双跑 pytest 必互踩假红);
    2. 解包段标记: mkdir 后立刻写 `$$`(不设 trap —— 解包 exec 被杀 = bash 死 pid 留存,
       下轮 sweep 按双条件可回收; run_script 随后覆盖为自身 pid 并设 EXIT trap);
    3. 快照语义: rm 旧 code 再解 —— 推模式本就是全量树, 复用同名 slug 重跑时宿主已删/
       改名的文件不许以旧残留留在容器里被 pytest 收到(旧 .venv 一并重来, cp 模板秒级)。
    """
    return """set -eu
mkdir -p "$AQB_WORK"
m="$AQB_WORK/.run-pid"
if [ -f "$m" ]; then
  opid=$(cat "$m" 2>/dev/null || true)
  case "$opid" in ''|*[!0-9]*) ;; *)
    if kill -0 "$opid" 2>/dev/null; then
      echo "[FAIL] 同 slug 会话仍在容器内跑(pid $opid)—— 不删其 code 不并发全量(D5)。NEXT: 换 --name 另起会话, 或等该轮结束/被下轮双条件清扫后重跑。"
      exit 30
    fi
  ;;
esac
fi
printf '%s\\n' "$$" > "$m"
rm -rf "$AQB_WORK/code"
mkdir -p "$AQB_WORK/code" && tar -xf - -C "$AQB_WORK/code" && echo "[linux-ci] 代码已推送: $AQB_WORK/code"
"""


def sweep_script(age_seconds: int) -> str:
    """下轮兜底清扫(R6): 双条件(内嵌 pid 已死 + mtime 超龄), 只 rmtree 带 .run-pid 标记的
    workdir, 不钻子树不越出 /root/auto-qb-tests/。无标记目录 = 不是本体系落的, 绝不碰。"""
    return f"""set -u
root="{TESTS_ROOT}"
[ -d "$root" ] || exit 0
now=$(date +%s)
for d in "$root"/*/; do
  d=${{d%/}}
  m="$d/.run-pid"
  [ -f "$m" ] || continue
  pid=$(cat "$m" 2>/dev/null || true)
  case "$pid" in ''|*[!0-9]*) continue ;; esac
  mtime=$(stat -c %Y "$d" 2>/dev/null || echo "$now")
  age=$(( now - mtime ))
  [ "$age" -ge {age_seconds} ] || continue
  if kill -0 "$pid" 2>/dev/null; then
    echo "[linux-ci] 清扫跳过(进程仍活): $d (pid $pid)"
    continue
  fi
  if rm -rf "$d"; then
    echo "[linux-ci] 清扫残留 workdir: $d (pid $pid 已死, mtime 龄 ${{age}}s >= {age_seconds}s)"
  else
    echo "[linux-ci] 清扫失败(手动 docker exec rm -rf): $d"
  fi
done
exit 0"""


def run_script(inner_timeout: int = INNER_PYTEST_TIMEOUT) -> str:
    """容器侧主脚本: venv 就绪(cp 模板 + export/pip delta) -> timeout 内层包裹全量 pytest。

    标记面 `.run-pid`: 解包段已写一版(extract bash 的 pid), 此处**覆盖为自身 pid($$)** 并
    设 EXIT trap 自清 —— venv 准备段与 pytest 段任一处被杀都有标记可回收(客户端被杀 =
    bash 被 SIGKILL, trap 不跑、pid 即死, 下一轮按双条件回收, R6)。
    准备段各步失败独立 exit 20-24(cd/模板cp/export/delta/editable)且 [FAIL] 行自带
    NEXT, 与 pytest 自身失败可分辨(main 按段归类)。
    """
    return f"""set -eu
mkdir -p "$AQB_WORK"
printf '%s\\n' "$$" > "$AQB_WORK/.run-pid"
trap 'rm -f "$AQB_WORK/.run-pid"' EXIT
cd "$AQB_WORK/code" || {{ echo "[FAIL] workdir/code 不在(解包段未跑或被清)。NEXT: 重跑本 task(每轮先解包); 复现排查看上方 docker exec 输出。"; exit 24; }}
echo "[linux-ci] 阶段: venv 就绪(cp 模板 + export/pip delta)"
if [ ! -x .venv/bin/python ]; then
  echo "[linux-ci] 首建 venv: cp -a $AQB_VENV -> .venv"
  cp -a "$AQB_VENV/." .venv/ || {{ echo "[FAIL] cp 模板 venv 失败($AQB_VENV -> .venv)。NEXT: 看上方 cp 真实报错; 模板不在先重跑 commands run test.linux-env 重建镜像。"; exit 20; }}
fi
uv export --frozen --format requirements-txt --no-hashes --no-emit-project --quiet -o "$AQB_WORK/delta-req.txt" || {{ echo "[FAIL] uv export 出钉版清单失败。NEXT: 核对 pyproject/uv.lock 完整性; 镜像索引不可达按 R9 换源(Dockerfile ARG UV_INDEX)或手动开代理后重跑。"; exit 21; }}
uv pip install -q --python .venv/bin/python -r "$AQB_WORK/delta-req.txt" || {{ echo "[FAIL] 依赖 delta 补装失败(uv pip install -r)。NEXT: 看上方 uv 报错; 国内镜像站不可达按 R9 换源或手动开代理后重跑。"; exit 22; }}
uv pip install -q --python .venv/bin/python -e . --no-deps || {{ echo "[FAIL] 项目 editable 补装失败(-e . --no-deps, hatchling 构建面)。NEXT: 看上方 uv 报错; 构建依赖拉不动按 R9 换源或手动开代理后重跑。"; exit 23; }}
echo "[linux-ci] 阶段: 容器内 timeout {inner_timeout}s 包裹全量 pytest(内层先到, 干净退出)"
export AUTO_QB_TESTBED=1  # 性能基准选 testbed 档(tests/test_modules_p5.py::_perf_limit_key): 容器配额+并行会话的挂钟放大是合法调度, 非回归
rc=0
timeout -k {TIMEOUT_KILL_GRACE} {inner_timeout} .venv/bin/python -m pytest tests -q || rc=$?
exit $rc"""


def _exec_env(pairs: list[tuple[str, str]], work: str, venv: str) -> list[str]:
    """docker exec 的 -e 面: 代理透传对 + 脚本参数(路径走 env, 不进命令串防引号坑)。"""
    cmd: list[str] = []
    for key, val in pairs:
        cmd += ["-e", f"{key}={val}"]
    cmd += [
        "-e",
        f"AQB_WORK={work}",
        "-e",
        f"AQB_VENV={venv}",
    ]
    return cmd


def _parse_args(argv: list[str]) -> tuple[str, str]:
    """argv -> (python 版本, slug); 未知旗标响亮拒绝(rc 2 由 main 落)。"""
    py_ver, name = DEFAULT_PYTHON, ""
    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg == "--python" and i + 1 < len(argv):
            py_ver = argv[i + 1]
            i += 2
        elif arg == "--name" and i + 1 < len(argv):
            name = argv[i + 1]
            i += 2
        else:
            raise ValueError(f"未知参数: {arg}(本 task 只认 --python <3.12|3.13> 与 --name <slug>)")
    return py_ver, name


def main(argv: list[str]) -> int:
    # 闸门安全过滤探针(判据单点: .commands/my-commit-flow/scripts/_pipeline.py::_safe_files):
    # 无参跑本脚本 = 一次可能十几分钟的全量 pytest, 必须自认 action-without-args 让闸门摘掉
    # —— 否则冒烟探针只能等 10s 超时(同款形态见 linux_env.py)。
    if "--safety" in argv:
        print("action-without-args")
        return 0
    try:
        py_ver, name = _parse_args(argv)
        venv = pick_venv_template(py_ver)
        slug = sanitize_name(name) if name else auto_slug()
    except ValueError as exc:
        print(f"[STOP] {exc}")
        return 2
    if shutil.which("docker") is None:
        print("[STOP] 没装 docker: testbed 以 Docker 常驻容器为宿主(D1), 没 docker 跑不了")
        return 1
    state = linux_env.container_state()
    if state is None or not state[0]:
        print(
            f"[FAIL] 常驻容器 {CONTAINER} 不在或未运行 —— test.linux 不自动构建环境(环境面与"
            f"测试面分离)。NEXT: 先跑 `commands run test.linux-env`(幂等, 镜像已存在时秒级), "
            f"再重跑本 task。"
        )
        return 1
    root = Path(__file__).resolve().parents[3]  # <root>/.commands/test/scripts/linux_ci.py
    work = f"{TESTS_ROOT}/{slug}"
    pairs = container_env()
    print(f"[linux-ci] 会话 {slug}(python {py_ver}) -> {CONTAINER}:{work}")
    passed = [k for k, _ in pairs if k.lower().endswith("_proxy") and not k.lower().startswith("no_")]
    if passed:
        print(f"[linux-ci] 代理透传: {', '.join(passed)}(回环已改写; no_proxy 恒并入回环)")

    # R6 兜底清扫(开跑前): 双条件回收旧残留, 失败不挡本轮
    subprocess.run(
        ["docker", "exec", *_exec_env(pairs, work, venv), CONTAINER, "bash", "-c",
         sweep_script(SWEEP_AGE_SECONDS)],
        check=False,
    )

    # D4 推模式: 宿主 tar 流 -> docker exec -i 解包(含 .git 与未提交 WIP)
    tar_proc = subprocess.Popen(tar_cmd(root), stdout=subprocess.PIPE)
    assert tar_proc.stdout is not None
    extract = subprocess.Popen(
        ["docker", "exec", "-i", *_exec_env(pairs, work, venv), CONTAINER, "bash", "-c",
         extract_script()],
        stdin=tar_proc.stdout,
    )
    tar_proc.stdout.close()  # 让 tar 在下游先退时收到 SIGPIPE, 不挂死
    if extract.wait() != 0:
        tar_proc.wait()
        if extract.returncode == 30:
            print(
                f"[FAIL] 同 slug 会话仍在容器内跑, 本轮拒绝在活进程头顶删 code 并发全量(D5)—— "
                f"上方 [FAIL] 行带存活 pid。NEXT: 换 --name 另起会话, 或等该轮结束/被清扫后重跑。"
            )
        else:
            print(
                "[FAIL] 代码推送失败(tar 流或容器内解包出错, 上方 docker 输出)。NEXT: 同步失败即重试"
                "(R4: 快照瞬时性, .git 中间态撞并发 git 操作时重试即可); 复现排查可在 Git Bash 手工"
                "敲 docker exec(容器绝对路径前缀 MSYS_NO_PATHCONV=1, 见本文件头注)。"
            )
        return extract.returncode or 1
    tar_rc = tar_proc.wait()
    if tar_rc != 0:
        print(
            f"[FAIL] 宿主 tar 打包失败(rc={tar_rc}) —— 先确认仓库树可读(红线 auto-qb-data 在"
            "排除清单内, 不会读它); NEXT: 手工跑 tar_cmd 里的命令复现。"
        )
        return tar_rc

    # 容器内: venv 就绪 + timeout 内层包裹全量 pytest; 输出全文透传(排障要看 FAILED 明细)
    rc = subprocess.run(
        ["docker", "exec", *_exec_env(pairs, work, venv), CONTAINER, "bash", "-c",
         run_script()],
        check=False,
    ).returncode
    if rc == 124:
        print(
            f"[FAIL] 容器内 timeout({INNER_PYTEST_TIMEOUT}s)先到, pytest 被干净终止 —— 要么全量"
            f"时长超内层预算(健康跑由 T2b 实测校准), 要么有用例挂死。NEXT: 看上方 pytest 停在"
            f"哪个用例; 挂死归因走 flaky 台账, 预算不够则上调 INNER_PYTEST_TIMEOUT(须保持 < "
            f"引擎 1800s 且留推送/venv 准备余量)。"
        )
    elif 20 <= rc <= 24:
        print(
            f"[FAIL] venv 准备段失败(rc={rc}: 20=cp 模板/21=uv export/22=delta 补装/23=editable "
            f"补装/24=workdir/code 不在) —— pytest 未启动, 上方 [FAIL] 行已带 NEXT。"
        )
    elif rc >= 125:
        print(
            f"[FAIL] docker exec 自身失败(rc={rc}; 125=exec 启动失败/126=命令不可执行/127=找不到"
            f"命令)。NEXT: 先跑 `commands run test.linux-env` 核容器健康; 若容器被重建过, 镜像"
            f"内容变化见 .commands/test/docker/Dockerfile 头注。"
        )
    return rc


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
