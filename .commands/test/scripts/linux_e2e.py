"""test.linux-e2e: Docker testbed 容器内跑 WEB UI e2e(playwright headless chromium)。

计划单点:
[memory-bank/plans/26-11-12-0152-plan-linux-testbed-docker.html](../../../memory-bank/plans/26-11-12-0152-plan-linux-testbed-docker.html)
§03 入口 task 族表(test.linux-e2e 行)/ §04 S3 / §06 D2。

**形态**(S3 起): 复用 test.linux(linux_ci.py)的既有组件 —— 常驻容器前置核验 / workdir
slug(D5 并行隔离)/ tar 推送(D4 推模式, 含 .git 与 WIP)/ 同 slug 存活守卫(exit 30)/
双条件兜底清扫(R6)/ cp 模板 venv + export+pip delta —— 本脚本不复制这些字面量, 直接
import linux_ci 复用; 差异只在容器内主脚本: e2e 不跑 pytest, 跑 playwright。

1. 前置核验: 容器不在/不在跑 -> [FAIL] 指引 `commands run test.linux-env`, 不自动构建(同 linux_ci)。
2. workdir 就绪 + tar 推送 + 同 slug 存活守卫: 与 linux_ci 同一套(EXCLUDES / tar_cmd /
   extract_script 原样复用; auto-qb-data 在排除清单内 = 红线面零接触)。
3. venv 就绪: 与 linux_ci 同款(cp -a 模板 + uv export --no-hashes + uv pip install delta +
   editable 补装, 失败 rc 20-24 各带 [FAIL]+NEXT) —— 桩服务(HARNESS_CMD = `uv run python
   scripts/ui_harness.py`)要真 auto_qb.webui + qbittorrentapi, 必须有这个 .venv。
4. **node_modules 接挂(计划 D4/S3 定案, 2026-11-12 容器内实测)**: **symlink 胜出** ——
   `ln -s /opt/e2e-node/node_modules` 实测 0.002s, per-workdir `npm ci`(npmmirror)冷 0.820s /
   页缓存热 0.469s(同 workdir 重装; 绝对差在秒级, 但 symlink 零外呼): npm ci 每轮要 registry
   可达 = 给运行期新增一个 D8 网络依赖面, symlink 与镜像烘焙层(层 6, npm ci 859ms 定稿的那份
   22M 树)严格同源且全程离线可用 —— 选 symlink, npm ci 实测数字留档作回退依据。接挂失败 rc 26。
5. 容器内跑 playwright: 默认 **@fast 子集**(`--grep @fast`, 与 Windows 侧 npm run
   test:e2e:fast 同口径); `--full` 跑全量(512 例, 耗时数字**不进基线口径** —— 计划明示 e2e
   数字锚 Windows 侧, 容器全量只作容量记录)。`--` 之后的参数原样透传 playwright(排障筛选用)。
   timeout 内层包裹(R6 分层超时, 引擎包装兜外层, 与 linux_ci 同款两层结构)。
6. 下轮兜底清扫: 复用 linux_ci.sweep_script(双条件: pid 死 + mtime 超龄 12h)。

**UV_NO_SYNC=1(取舍留痕)**: HARNESS_CMD 是 `uv run python scripts/ui_harness.py`, uv run
默认会做 lockfile/环境 sync 检查 —— 容器内 venv 已由第 3 步 delta 备齐, sync 检查多余, 且
UV_PYTHON_DOWNLOADS=never 下任何意外重建路径都会直接死(不许偷偷补下载)。export UV_NO_SYNC=1
让 uv run 直接用现成 .venv(uv 0.13.7 实测支持该 env; `uv run --help` 有 --no-sync)。

**AUTO_QB_TESTBED 不导出(取舍留痕, 对照 linux_ci.run_script 的 export)**: 该 env 的唯一
消费方是 pytest 挂钟型性能基准(tests/test_modules_p5.py::_perf_limit_key), e2e 不跑 pytest,
桩服务与浏览器断言都不读它 —— 导出是死重量, 还会误导人把容器 e2e 耗时往 testbed 档上解读
(e2e 数字本就不进基线, 见上)。

**代理不透传(取舍留痕, 对照 linux_ci.container_env)**: e2e 的稳定面全程容器内回环 —— 桩
127.0.0.1 与 chromium 同容器, playwright 二进制/chromium/npm 接挂面**零外呼**(三者都烘在镜像
里, npm 依赖走 symlink); **venv delta 段仍可能外呼 PyPI 索引**(uv pip install), 失败走 R9 换源
(Dockerfile ARG UV_INDEX, 经 test.linux-env 重建镜像), 不靠代理。透传宿主代理只会给 chromium
引入代理面变量(linux_ci 那套「回环改写 + no_proxy 恒并回环」防的是容器内外呼被代理拦, e2e
稳定面无外呼, 防线用不上)。容器 -e 面只给 LANG 与脚本参数。

**动态端口(纪律对应面)**: e2e 侧端口纪律单点在 e2e/harness.mjs —— 桩恒 `--port 0` 由 OS
分配(容器命名空间内), playwright webServer.wait 从启动行捕获实绑端口注入 UI_HARNESS_PORT,
spec 一律 baseUrl() 懒取值; 本脚本**不引入任何固定口也不覆盖任何端口变量**(E2E_PORT 残留
会被 harness.mjs 直接抛错)。tests/_test_ports.py 是 pytest 侧单点, 不跨面复制。

**软件渲染预期**: 容器内 chromium 走 swiftshader 软件渲染 + CPU 配额(与宿主其它容器共享),
单用例墙钟比 Windows 真渲染慢一个量级 —— 属合法形态差异非挂死; 判挂死看渲染器进程是否在周转
(renderer 每几十秒换代 = 在推进)。**2026-11-12 S3 实测**: @fast 344 例 342 绿 / 2 败(41.7m);
--full 512 例 490 绿 / 4 败 / 18 skip(59.2m)。4 败全是 spec 层计时敏感面被容器慢 CPU 显性化
(traffic-source-switch 的 route.fetch 测试结束后才 resolve 的竞态 x2 + settings-bt-backup
「探测 ambiguous」双皮肤 x2), 桩/浏览器/接挂面无一异常, Windows 侧同 spec 恒绿 —— 只记录不修
(范围守恒)。数字单点在任务档案 task note 与 config.toml note。

守阵: `scripts/test_linux_e2e.py`(红验: 接挂方案 / fast 子集默认 / 动态端口不引入固定口 /
UV_NO_SYNC / 引擎 timeout / 透传面即红)。
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import linux_ci  # 同包脚本: 容器核验/tar 推送/slug/清扫等组件单点, 不复制字面量
import linux_env

CONTAINER = linux_env.CONTAINER_NAME
#: node_modules 烘焙模板(镜像层 6 的 npm ci 产物; 接挂 = symlink 该处, 见模块 docstring 定案)
E2E_NODE_MODULES = "/opt/e2e-node/node_modules"
#: npm ci 回退路线的 registry(仅记录; 当前定案 symlink, 此值不进运行路径, 与 Dockerfile ARG 同源)
NPM_REGISTRY_FALLBACK = "https://registry.npmmirror.com"
#: R6 分层超时: 内层(playwright)先到, 引擎包装(.commands/test/config.toml)兜外层。
#: 容器软件渲染慢是形态差异(见 docstring), 预算按 --full 容量校准: 2026-11-12 S3 实测全量
#: 512 例 59.2m(3551s, 数字单点在任务档案 task note), 取 ~3x 余量 = 10800s(宿主负载/配额波动
#: 有真实形态差异, 不按实测值 1:1 钉死; fast 子集 41.7m 远在此内)。
INNER_E2E_TIMEOUT = 10800
TIMEOUT_KILL_GRACE = linux_ci.TIMEOUT_KILL_GRACE
#: 引擎包装超时(.commands/test/config.toml 的 test.linux-e2e 行), 守阵核它 >= 内层 + 最小余量
ENGINE_TIMEOUT = 11400
ENGINE_TIMEOUT_MARGIN = 600  # 引擎 - 内层最小余量(付 tar 推送 + venv 准备; 实测 ~15s, 放大兜底)
#: fast 子集默认 grep(与 Windows 侧 npm run test:e2e:fast 同口径); --full 才去掉
FAST_GREP = "@fast"

#: 容器 -e 面(e2e 口径): 只有 LANG; 代理不透传(取舍见 docstring), 其余靠镜像 ENV 与 run_script
E2E_ENV_BASE = (("LANG", "C.UTF-8"), )


def e2e_playwright_args(full: bool, extra: list[str]) -> list[str]:
    """playwright CLI 参数(run_script 里 `playwright test` 之后的 "$@" 尾巴):
    默认 @fast 子集(--grep @fast), --full 去掉 grep, `--` 后透传原样追加。

    参数不烘进 run_script 文本, 经 bash "$@" 从 exec argv 传入 —— 文本面只钉
    接挂/timeout/env 三面, 子集选择钉在本函数(守阵直接调它)。
    """
    args = [] if full else ["--grep", FAST_GREP]
    return args + extra


def run_script() -> str:
    """容器侧主脚本: venv 就绪(同 linux_ci 四步) -> symlink 接挂 node_modules -> UV_NO_SYNC
    -> timeout 内层包裹 `node_modules/.bin/playwright test`($@ = e2e_playwright_args 出口)。

    playwright.config.mjs 的 webServer 会按 HARNESS_CMD(`uv run python scripts/ui_harness.py
    --torrents ... --port 0`)起桩: 端口 OS 分配 + wait 捕获(纪律单点 harness.mjs, 本脚本不碰),
    桩进程由 playwright 托管起收, 本脚本不做任何桩生命周期管理。
    标记面 `.run-pid` 与 linux_ci.run_script 同款: 覆盖为自身 pid($$)并设 EXIT trap 自清,
    venv 准备段/接挂段/playwright 段任一处被杀都有标记可回收(R6)。失败 rc: 20-24 venv 准备段
    (与 linux_ci 同号同义)/26 node_modules 接挂失败; playwright 自身退出码原样透传。
    """
    return f"""set -eu
mkdir -p "$AQB_WORK"
printf '%s\\n' "$$" > "$AQB_WORK/.run-pid"
trap 'rm -f "$AQB_WORK/.run-pid"' EXIT
cd "$AQB_WORK/code" || {{ echo "[FAIL] workdir/code 不在(解包段未跑或被清)。NEXT: 重跑本 task(每轮先解包); 复现排查看上方 docker exec 输出。"; exit 24; }}
echo "[linux-e2e] 阶段: venv 就绪(cp 模板 + export/pip delta, 同 test.linux)"
if [ ! -x .venv/bin/python ]; then
  echo "[linux-e2e] 首建 venv: cp -a $AQB_VENV -> .venv"
  cp -a "$AQB_VENV/." .venv/ || {{ echo "[FAIL] cp 模板 venv 失败($AQB_VENV -> .venv)。NEXT: 看上方 cp 真实报错; 模板不在先重跑 commands run test.linux-env 重建镜像。"; exit 20; }}
fi
uv export --frozen --format requirements-txt --no-hashes --no-emit-project --quiet -o "$AQB_WORK/delta-req.txt" || {{ echo "[FAIL] uv export 出钉版清单失败。NEXT: 核对 pyproject/uv.lock 完整性; 镜像索引不可达按 R9 换源(Dockerfile ARG UV_INDEX)并重跑 commands run test.linux-env 重建镜像。"; exit 21; }}
uv pip install -q --python .venv/bin/python -r "$AQB_WORK/delta-req.txt" || {{ echo "[FAIL] 依赖 delta 补装失败(uv pip install -r)。NEXT: 看上方 uv 报错; 国内镜像站不可达按 R9 换源(Dockerfile ARG UV_INDEX)并重跑 commands run test.linux-env 重建镜像。"; exit 22; }}
uv pip install -q --python .venv/bin/python -e . --no-deps || {{ echo "[FAIL] 项目 editable 补装失败(-e . --no-deps, hatchling 构建面)。NEXT: 看上方 uv 报错; 构建依赖拉不动按 R9 换源(Dockerfile ARG UV_INDEX)并重跑 commands run test.linux-env 重建镜像。"; exit 23; }}
echo "[linux-e2e] 阶段: node_modules 接挂(symlink {E2E_NODE_MODULES}, 定案见模块 docstring)"
# 悬空守卫先行: ln -s 对不存在目标照样创建悬空链接, 缺层 6 必须在这里响亮 exit 26,
# 不能等 playwright 进程期才以 rc 127/模块解析错的形式炸出来被误归因 docker exec 自身失败
[ -d {E2E_NODE_MODULES} ] || {{ echo "[FAIL] 镜像缺烘焙模板 {E2E_NODE_MODULES}(层 6 未烘焙或镜像被重建改动)。NEXT: 重跑 commands run test.linux-env; 仍缺则核 .commands/test/docker/Dockerfile 层 6(`docker exec {CONTAINER} ls /opt/e2e-node`)。"; exit 26; }}
rm -rf node_modules && ln -s {E2E_NODE_MODULES} node_modules || {{ echo "[FAIL] node_modules symlink 接挂失败(目标在位, ln 本体失败, 看上方真实报错)。NEXT: 重跑本 task; 仍败核容器内 /root/auto-qb-tests 挂载/权限面。"; exit 26; }}
echo "[linux-e2e] 阶段: 容器内 timeout {INNER_E2E_TIMEOUT}s 包裹 playwright(内层先到, 干净退出)"
export UV_NO_SYNC=1  # HARNESS_CMD 是 uv run, 不许它做 sync 检查/意外重建(venv 已由上段备齐)
timeout -k {TIMEOUT_KILL_GRACE} {INNER_E2E_TIMEOUT} node_modules/.bin/playwright test "$@"
"""


def _parse_args(argv: list[str]) -> tuple[str, str, bool, list[str]]:
    """argv -> (python 版本, slug, full, 透传参数); `--` 之后原样透传 playwright。

    未知旗标响亮拒绝(rc 2 由 main 落); 透传参数不再校验 —— playwright 自己对非法参数报错。
    """
    if "--" in argv:
        sep = argv.index("--")
        left, extra = argv[:sep], argv[sep + 1:]
    else:
        left, extra = list(argv), []
    py_ver, name, full = linux_ci.DEFAULT_PYTHON, "", False
    i = 0
    while i < len(left):
        arg = left[i]
        if arg == "--python" and i + 1 < len(left):
            py_ver = left[i + 1]
            i += 2
        elif arg == "--name" and i + 1 < len(left):
            name = left[i + 1]
            i += 2
        elif arg == "--full":
            full = True
            i += 1
        else:
            raise ValueError(
                f"未知参数: {arg}(本 task 只认 --python <3.12|3.13> / --name <slug> / --full / "
                "-- <playwright 参数透传>)"
            )
    return py_ver, name, full, extra


def main(argv: list[str]) -> int:
    # 闸门安全过滤探针(判据单点: .commands/my-commit-flow/scripts/_pipeline.py::_safe_files):
    # 无参跑本脚本 = 一次小时级的容器 e2e, 必须自认 action-without-args 让闸门摘掉
    # —— 否则冒烟探针只能等 10s 超时(同款形态见 linux_ci.py / linux_env.py)。
    if "--safety" in argv:
        print("action-without-args")
        return 0
    try:
        py_ver, name, full, extra = _parse_args(argv)
        venv = linux_ci.pick_venv_template(py_ver)
        slug = linux_ci.sanitize_name(name) if name else linux_ci.auto_slug()
    except ValueError as exc:
        print(f"[STOP] {exc}")
        return 2
    if shutil.which("docker") is None:
        print("[STOP] 没装 docker: testbed 以 Docker 常驻容器为宿主(D1), 没 docker 跑不了")
        return 1
    state = linux_env.container_state()
    if state is None or not state[0]:
        print(
            f"[FAIL] 常驻容器 {CONTAINER} 不在或未运行 —— test.linux-e2e 不自动构建环境(环境面与"
            f"测试面分离)。NEXT: 先跑 `commands run test.linux-env`(幂等, 镜像已存在时秒级), "
            f"再重跑本 task。"
        )
        return 1
    root = Path(__file__).resolve().parents[3]  # <root>/.commands/test/scripts/linux_e2e.py
    work = f"{linux_ci.TESTS_ROOT}/{slug}"
    subset = "全量(--full)" if full else f"@fast 子集(默认 --grep {FAST_GREP})"
    print(f"[linux-e2e] 会话 {slug}(python {py_ver}, {subset}) -> {CONTAINER}:{work}")

    # R6 兜底清扫(开跑前, 复用 linux_ci 同一份脚本): 双条件回收旧残留, 失败不挡本轮
    subprocess.run(
        [
            "docker", "exec", *linux_ci._exec_env([], work, venv), CONTAINER, "bash", "-c",
            linux_ci.sweep_script(linux_ci.SWEEP_AGE_SECONDS)
        ],
        check=False,
    )

    # D4 推模式(复用 linux_ci 全套): 宿主 tar 流 -> docker exec -i 解包(含 .git 与未提交 WIP)
    tar_proc = subprocess.Popen(linux_ci.tar_cmd(root), stdout=subprocess.PIPE)
    assert tar_proc.stdout is not None
    extract = subprocess.Popen(
        [
            "docker", "exec", "-i", *linux_ci._exec_env([], work, venv), CONTAINER, "bash", "-c",
            linux_ci.extract_script()
        ],
        stdin=tar_proc.stdout,
    )
    tar_proc.stdout.close()  # 让 tar 在下游先退时收到 SIGPIPE, 不挂死
    if extract.wait() != 0:
        tar_proc.wait()
        if extract.returncode == 30:
            print(
                f"[FAIL] 同 slug 会话仍在容器内跑, 本轮拒绝在活进程头顶删 code 并发 e2e(D5)—— "
                f"上方 [FAIL] 行带存活 pid。NEXT: 换 --name 另起会话, 或等该轮结束/被清扫后重跑。"
            )
        else:
            print(
                "[FAIL] 代码推送失败(tar 流或容器内解包出错, 上方 docker 输出)。NEXT: 同步失败即重试"
                "(R4: 快照瞬时性); 复现排查可在 Git Bash 手工敲 docker exec(容器绝对路径前缀 "
                "MSYS_NO_PATHCONV=1, 坑档见 linux_ci.py 头注)。"
            )
        return extract.returncode or 1
    tar_rc = tar_proc.wait()
    if tar_rc != 0:
        print(
            f"[FAIL] 宿主 tar 打包失败(rc={tar_rc})(排除清单见 linux_ci.EXCLUDES, 红线 "
            "auto-qb-data 不在拷贝面); NEXT: 手工跑 linux_ci.tar_cmd 里的命令复现。"
        )
        return tar_rc

    # 容器内: venv 就绪 + 接挂 + timeout 内层包裹 playwright; 输出全文透传(排障要看失败明细)
    pw_args = e2e_playwright_args(full, extra)
    rc = subprocess.run(
        [
            "docker", "exec", *linux_ci._exec_env(list(E2E_ENV_BASE), work, venv), CONTAINER, "bash", "-c",
            run_script(), "bash", *pw_args
        ],
        check=False,
    ).returncode
    if rc == 124:
        print(
            f"[FAIL] 容器内 timeout({INNER_E2E_TIMEOUT}s)先到, playwright 被干净终止 —— 容器"
            f"软件渲染比 Windows 慢一个量级, 先核对是不是预算不足(对照任务档案 task note 实测数字), "
            f"再查挂死(渲染器进程几十秒换代 = 在推进)。NEXT: 预算不够上调 INNER_E2E_TIMEOUT"
            f"(须保持 < 引擎 {ENGINE_TIMEOUT}s 且留推送/venv 准备余量); 挂死归因走 flaky 台账。"
        )
    elif rc in (20, 21, 22, 23, 24):
        print(
            f"[FAIL] 准备段失败(rc={rc}: 20=cp 模板/21=uv export/22=delta 补装/23=editable "
            f"补装/24=workdir 或 code 不在) —— playwright 未启动, 上方 [FAIL] 行已带 NEXT。"
        )
    elif rc == 26:
        print(f"[FAIL] node_modules 接挂失败(rc=26) —— playwright 未启动, 上方 [FAIL] 行已带 NEXT。")
    elif rc >= 125:
        print(
            f"[FAIL] docker exec 自身失败(rc={rc}; 125=exec 启动失败/126=命令不可执行/127=找不到"
            f"命令)。NEXT: 先跑 `commands run test.linux-env` 核容器健康; 若容器被重建过, 镜像"
            f"内容变化见 .commands/test/docker/Dockerfile 头注。"
        )
    return rc


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
