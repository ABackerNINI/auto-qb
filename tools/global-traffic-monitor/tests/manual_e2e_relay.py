"""手动 e2e 复算脚本(计划 26-10-20-1316 §04 P3 验收) —— **不进 pytest 套件**.

为什么手动: 复算要**真起两个 gtm 进程**(安装 A/B 各一份), 而 tests/sidefx.py 的
POPEN 白名单只放行 node 与临时 wrapper —— 真拉 python 子进程会被判越界让整套测试
红。机制本身由 hermetic 单测守阵(矩阵/注记/claim/路由/前端接线), 本脚本补的是
**真进程链**: 拷贝件身份 -> 认领 -> 崩溃 -> B 先起 -> 代拉 -> A 指针回来 -> 同一 dat。

跑法(在仓库根, 用**仓库 venv** 的 python —— 它没装 gtm, PYTHONPATH 才指得动拷贝件;
工具 venv 的 editable finder 会拦截 `gtm` Import, 让两份拷贝共用真实源码身份):

    .venv/Scripts/python.exe tools/global-traffic-monitor/tests/manual_e2e_relay.py

环境(全部重定向到临时目录, 不碰真实指针目录与真实安装):
  - LOCALAPPDATA/(XDG_DATA_HOME) -> <tmp>/ptr       指针目录(primary.json/deferred.json)
  - PYTHONPATH -> <tmp>/inst-a/src(或 inst-b)       安装身份(resolve_tool_root 溯源)
                 + 工具 venv site-packages          依赖(psutil/filelock/pyyaml)

场景(原痛点复算, §02 时间线):
  ① A 的工具起 -> 认领正主, 指针+数据落 A/data
  ② A 崩溃(SIGKILL/terminate, 留残留指针 —— 与真实崩溃同态)
  ③ B 先起 -> 读记录(id 异) -> 代拉 A 的启动器后立即退出(让位方绝不自身启动)
  ④ A 的工具被代拉起来 -> 清注记、写指针、数据继续落 A/data(同一 dat)
  ⑤ claim 护栏: A 在跑时 B claim -> 拒绝; 停 A 后 B claim -> 成功易主
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
TOOL_ROOT = REPO_ROOT / "tools" / "global-traffic-monitor"
TOOL_SRC = TOOL_ROOT / "src"
IS_WINDOWS = os.name == "nt"
LAUNCHER = "launch.cmd" if IS_WINDOWS else "launch.sh"

# 工具 venv site-packages(依赖来源; 与安装源码解耦, 拷贝件只带 src + pyproject.toml)


def _venv_site_packages() -> str:
    if IS_WINDOWS:
        return str(TOOL_ROOT / ".venv" / "Lib" / "site-packages")
    for cand in sorted((TOOL_ROOT / ".venv" / "lib").glob("python*/site-packages")):
        return str(cand)
    raise SystemExit("找不到工具 venv 的 site-packages(先在 tools/global-traffic-monitor 里 uv sync)")


def child_env(install_src: Path, ptr_root: Path) -> dict:
    """子进程环境: 安装身份走 PYTHONPATH, 指针目录走平台数据根 env, 其余继承."""
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join([str(install_src), _venv_site_packages()])
    env["LOCALAPPDATA"] = str(ptr_root)      # Windows 指针根
    env["XDG_DATA_HOME"] = str(ptr_root)     # POSIX 指针根
    return env


def make_install(tmp: Path, name: str) -> Path:
    """造一份安装拷贝: src/gtm + pyproject.toml(resolve_tool_root 溯源到它) + 自写启动器."""
    inst = tmp / name
    (inst / "src").mkdir(parents=True)
    shutil.copytree(TOOL_SRC / "gtm", inst / "src" / "gtm")
    shutil.copy2(TOOL_ROOT / "pyproject.toml", inst / "pyproject.toml")
    # 启动器: 代拉目标(正主)的执行入口。真实部署里它是 %~dp0.venv/pythonw -m gtm run;
    # 这里等价形态 = 显式把 PYTHONPATH 指回**本安装**的 src(否则继承来的 B 侧 PYTHONPATH
    # 会让 A 的启动器起出 B 的身份, 互拉死循环)。
    launcher = inst / LAUNCHER
    if IS_WINDOWS:
        launcher.write_text(
            f"@echo off\r\nset \"PYTHONPATH={inst / 'src'};{_venv_site_packages()}\"\r\n"
            f"\"{sys.executable}\" -m gtm run\r\n",
            encoding="utf-8",
        )
    else:
        launcher.write_text(
            f"#!/bin/sh\nexport PYTHONPATH=\"{inst / 'src'}:{_venv_site_packages()}\"\n"
            f"exec \"{sys.executable}\" -m gtm run\n",
            encoding="utf-8",
        )
    return inst


def probe_endpoint(ptr_root: Path, timeout: float = 20.0):
    """读指针 + GET /status 探活(就绪只认 200, 与 auto-qb 同口径); 超时 -> None."""
    deadline = time.monotonic() + timeout
    ep_file = ptr_root / "global-traffic-monitor" / "endpoint.json"
    while time.monotonic() < deadline:
        try:
            payload = json.loads(ep_file.read_text(encoding="utf-8"))
            base = f"http://{payload['host']}:{payload['port']}"
            token = Path(payload["token_path"]).read_text(encoding="utf-8").strip()
            req = urllib.request.Request(f"{base}/status", headers={"Authorization": f"Bearer {token}"})
            with urllib.request.urlopen(req, timeout=2) as resp:
                if resp.status == 200:
                    return payload
        except (OSError, ValueError, KeyError, urllib.error.URLError):
            pass
        time.sleep(0.4)
    return None


def tool_call(base: str, token_path: str, path: str) -> tuple:
    token = Path(token_path).read_text(encoding="utf-8").strip()
    req = urllib.request.Request(f"{base}{path}", data=b"{}", method="POST",
                                 headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return e.code, {}


def spawn_tool(inst: Path, ptr_root: Path):
    return subprocess.Popen(
        [sys.executable, "-m", "gtm", "run"],
        env=child_env(inst / "src", ptr_root),
        cwd=str(inst),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )


def run_claim(inst: Path, ptr_root: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "gtm", "claim"],
        env=child_env(inst / "src", ptr_root),
        cwd=str(inst),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=60,
    )


def main() -> int:
    tmp = Path(tempfile.mkdtemp(prefix="gtm-e2e-"))
    ptr_root = tmp / "ptr"
    inst_a = make_install(tmp, "inst-a")
    inst_b = make_install(tmp, "inst-b")
    procs = []
    print(f"[e2e] tmp={tmp}")
    print(f"[e2e] A={inst_a}\n[e2e] B={inst_b}\n[e2e] ptr={ptr_root}")
    try:
        # ① A 先起: 认领正主
        procs.append(spawn_tool(inst_a, ptr_root))
        ep = probe_endpoint(ptr_root)
        assert ep is not None, "① A 的工具未就绪"
        assert str(inst_a) in json.dumps(ep) or Path(ep["data_dir"]) == inst_a / "data", f"① 数据落点不是 A: {ep}"
        print(f"[e2e] ① A 已认领正主并就绪: data_dir={ep['data_dir']}")

        # ② A 崩溃(强杀, 留残留指针 —— 与真实崩溃同态)
        dead = procs.pop()
        dead.kill()
        dead.wait(timeout=5)
        time.sleep(1.0)
        print("[e2e] ② A 已崩溃(残留指针留着, 探活失败)")

        # ③ B 先起: 应代拉 A 后立即退出(exit 0), 自身不写任何数据
        proc_b = spawn_tool(inst_b, ptr_root)
        procs.append(proc_b)
        try:
            rc = proc_b.wait(timeout=30)
        except subprocess.TimeoutExpired:
            proc_b.kill()
            raise AssertionError("③ B 未在 30s 内退出(应代拉后立即退出)")
        out = proc_b.stdout.read() if proc_b.stdout else ""
        assert rc == 0, f"③ B 退出码 {rc}(应 0), 输出: {out}"
        print(f"[e2e] ③ B 已让位退出(rc=0): {out.strip().splitlines()[-1] if out.strip() else ''}")

        # ④ A 被代拉起: 指针回来, 数据仍落 A/data(同一 dat), 注记被清
        ep2 = probe_endpoint(ptr_root)
        assert ep2 is not None, "④ 代拉后 A 的工具未就绪"
        assert Path(ep2["data_dir"]) == inst_a / "data", f"④ 数据落点漂了: {ep2['data_dir']}"
        assert (inst_a / "data" / "tool-id").is_file(), "④ A/data 缺数据归属 tool-id"
        assert not (inst_b / "data").exists(), "④ B 竟然写了数据目录(让位方必须零写入)"
        note = ptr_root / "global-traffic-monitor" / "deferred.json"
        assert not note.exists(), "④ 正主成功启动后注记应被清除"
        print(f"[e2e] ④ A 被代拉起并就绪: data_dir={ep2['data_dir']}(注记已清)")

        # ⑤ claim 护栏: A 在跑 -> B claim 拒绝; 停 A -> B claim 成功易主
        r = run_claim(inst_b, ptr_root)
        assert r.returncode != 0 and "正在运行" in r.stdout, f"⑤ 运行中 claim 应被拒绝: rc={r.returncode} {r.stdout}"
        print(f"[e2e] ⑤a A 在跑时 B claim 被拒绝: {r.stdout.strip().splitlines()[-1]}")
        code, _ = tool_call(f"http://{ep2['host']}:{ep2['port']}", ep2["token_path"], "/shutdown")
        assert code == 200, f"⑤ 停 A 失败: {code}"
        procs.clear()  # A 优雅退出后进程列表清空(下面只 claim, 不再起工具)
        # A 的退出是异步的(最终落盘 -> 释放锁): claim 重试到锁让出来为止(拒绝原因即"正在运行")
        r2 = None
        for _ in range(10):
            r2 = run_claim(inst_b, ptr_root)
            if r2.returncode == 0:
                break
            time.sleep(1.0)
        assert r2 is not None and r2.returncode == 0, f"⑤b 停后 claim 应成功: rc={r2.returncode} {r2.stdout}"
        record = json.loads((ptr_root / "global-traffic-monitor" / "primary.json").read_text(encoding="utf-8"))
        assert Path(record["install_path"]) == inst_b and record["id"] == (inst_b / "tool-id").read_text().strip(), \
            f"⑤b 记录未换成 B: {record}"
        assert (inst_b / "data" / "tool-id").is_file(), "⑤b claim 后 B/data 应认领数据归属"
        print(f"[e2e] ⑤b 停 A 后 B claim 成功: 正主={record['install_path']} data={record['data_dir']}")

        print("[e2e] PASS: 原场景复算成立(代拉 -> 同一 dat -> claim 护栏两态)")
        return 0
    finally:
        # 代拉起的那份 A 没有进程句柄(relay 是 detached spawn): 指针还在就尽力调一次
        # /shutdown 把它收掉, 别给开发机留孤儿进程
        try:
            ep_last = probe_endpoint(ptr_root, timeout=0.5)
            if ep_last is not None:
                tool_call(f"http://{ep_last['host']}:{ep_last['port']}", ep_last["token_path"], "/shutdown")
                time.sleep(1.5)
        except Exception:
            pass
        for p in procs:
            try:
                p.kill()
                p.wait(timeout=5)
            except Exception:
                pass
        print(f"[e2e] 现场保留在 {tmp}(排查用, 可手动删)")


if __name__ == "__main__":
    sys.exit(main())
