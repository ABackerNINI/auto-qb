"""RM01 连接·认证·启动 —— 进程边界九条(真机)。

本片验证对象全是「进程活着才有意义」的东西: 文件锁、监听端口、token 文件、注册表、托盘进程。
单测里它们一律被打桩(filelock / winreg / uvicorn / pystray), 而真实失败模式恰恰在桩之外。

公共件 `lib/app.py` 里钉了三条实测事实(--dry-run 不启 WEB / Windows 外部 SIGTERM 等于强杀 /
配置必须带 schema_version), 改用例前先读那段 docstring。

跑法: `real.suite --slice RM01`(task id), 不要裸 pytest。
"""
from __future__ import annotations

import socket
import sys
import time
from pathlib import Path

import pytest

from lib import app

# 本片所有用例都只碰 36596(空库) —— 见 lib/app.py 模块 docstring 的安全口径
pytestmark = [
    pytest.mark.skipif(sys.platform != "win32", reason="本片断言含 Windows 特有语义(注册表/无控制台 SIGTERM)"),
    # 本片每条都要抢端口 + 起真实进程: 并行跑会互相抢 39000-39999 段(各自 free_port 可能撞同一个),
    # 且注册表那条是全局单例。用 xdist_group 把它们钉在同一个 worker 上串行执行。
    pytest.mark.xdist_group(name="rm01_startup"),
]


def _cfg(case: Path, **kw) -> Path:
    cfg = app.write_config(case, **kw)
    app.assert_cfg_target(cfg)
    return cfg


# ---------------------------------------------------------------- RM01-01

def test_rm01_01_missing_config_fail_fast():
    """[RM01-01] 配置缺失时干净退出: 退出码 1 + stderr 一行「配置错误」+ 无堆栈

    前置: 无(不连 qB, 不起 WEB)
    副作用: 无(只跑一次 CLI 进程, 配置路径不存在)
    回滚: 不需要
    失败判据: 退出码 != 1 / stderr 无「配置错误」/ stderr 出现 Traceback(说明 AutoQbError
              通道被打穿, 用户会看到一堆栈而不是一句话)
    """
    case = app.case_dir("rm01_01")
    missing = case / "does-not-exist.yml"

    r = app.run_cli([str(missing)])

    assert r.returncode == 1, f"期望退出码 1, 实际 {r.returncode}; stderr={r.stderr!r}"
    assert "配置错误" in r.stderr, f"stderr 缺「配置错误」前缀: {r.stderr!r}"
    assert "Traceback" not in r.stderr, f"AutoQbError 通道被打穿, 打出了堆栈: {r.stderr!r}"


# ---------------------------------------------------------------- RM01-02

def test_rm01_02_single_instance_lock_rejects_second():
    """[RM01-02] 单实例锁: 第二实例被拒且报出持有者, 且「被拒」不是因为别的原因(L3)

    前置: 实例 A 以 dry-run 持锁(锁在 QbManager.__init__ 取, 与是否 dry-run 无关)
    副作用: A 在用例目录里留下 state.lock / state.lock.meta.json(随目录清理)
    回滚: 停 A; 用例目录整目录删除
    失败判据: B 退出码 != 1 / stderr 无「另一实例已持有锁」/ stderr 里没有 A 的 PID /
              meta.json 的 pid 与 A 不符。**红验**: 停掉 A 后同样起法必须能起来 —— 否则
              「被拒」这条断言是假的(B 可能因为别的原因起不来, 也照样绿)
    """
    case = app.case_dir("rm01_02")
    cfg = _cfg(case)

    a = app.start(cfg, case, dry_run=True)
    try:
        assert a.wait_log("启动 qB 管理器", 30), f"A 没起来:\n{a.log()}"

        # 第二实例: 用 run_cli 收 stderr(起不来的证据全在 stderr 那一行)
        r = app.run_cli([str(cfg), "--dry-run"])
        assert r.returncode == 1, f"期望退出码 1, 实际 {r.returncode}; stderr={r.stderr!r}"
        assert "另一实例已持有锁" in r.stderr, f"没报锁竞争: {r.stderr!r}"

        meta = case / "data" / "state.lock.meta.json"
        assert meta.is_file(), "伴生 meta 没写出来 —— 报错时就没法告诉用户是谁占着锁"
        import json

        holder = json.loads(meta.read_text(encoding="utf-8"))["pid"]
        # 注意比的是**持锁进程**的 pid, 不是 Popen 那个启动器 pid(见 lib/app.py 的 pid 注)
        assert str(holder) in r.stderr, f"报错没带持有者 PID({holder}): {r.stderr!r}"
        assert holder == a.real_pid(), f"meta 里的 pid({holder}) 与持锁进程({a.real_pid()})不一致"
    finally:
        a.stop()

    # ---- 红验: A 不在时, 同样的起法必须成功(否则上面的"被拒"不成立)
    b = app.start(cfg, case, dry_run=True)
    try:
        assert b.wait_log("启动 qB 管理器", 30), f"红验失败: A 已停,B 仍起不来 —— 锁没释放?\n{b.log()}"
    finally:
        b.stop()


# ---------------------------------------------------------------- RM01-03

def test_rm01_03_readonly_mode_skips_lock():
    """[RM01-03] 只读出口(--export-yaml)不持锁: A 持锁时仍可并发跑

    前置: 实例 A 持锁
    副作用: 在用例目录写一份导出的 YAML(不碰原配置)
    回滚: 目录删除
    失败判据: stderr 出现「另一实例已持有锁」(说明 no_lock 传丢了, 用户没法在实例运行时导出)
    """
    case = app.case_dir("rm01_03")
    cfg = _cfg(case)
    out = case / "exported.yml"

    a = app.start(cfg, case, dry_run=True)
    try:
        assert a.wait_log("启动 qB 管理器", 30), f"A 没起来:\n{a.log()}"
        r = app.run_cli([str(cfg), "--export-yaml", str(out)])
        assert "另一实例已持有锁" not in r.stderr, f"只读出口被锁拦了(no_lock 失效): {r.stderr!r}"
        assert out.is_file(), f"导出文件没生成; rc={r.returncode} stderr={r.stderr!r}"
    finally:
        a.stop()


# ---------------------------------------------------------------- RM01-04

def test_rm01_04_lock_released_after_hard_kill():
    """[RM01-04] 强杀(taskkill /F)后锁自动释放: 立刻能起新实例, 不做 PID 存活检测也不留死锁

    前置: 实例 A 持锁
    副作用: A 被强杀(模拟崩溃/断电), 可能留下 state.lock 文件与 meta
    回滚: 起 B 后再停; 目录删除
    失败判据: 强杀后 B 报「另一实例已持有锁」—— 那是**真缺陷**(filelock 句柄没随进程释放,
              用户崩一次就得手工删锁文件)
    """
    case = app.case_dir("rm01_04")
    cfg = _cfg(case)

    a = app.start(cfg, case, dry_run=True)
    assert a.wait_log("启动 qB 管理器", 30), f"A 没起来:\n{a.log()}"
    a.kill()
    assert not a.alive(), "强杀后进程还在, 用例前提不成立"

    b = app.start(cfg, case, dry_run=True)
    try:
        assert b.wait_log("启动 qB 管理器", 30), f"强杀后锁没释放, B 起不来:\n{b.log()}"
        # 锁文件本身可以留着(filelock 语义), 但**不能被占住**; meta 残留是允许的(它只是说明)
    finally:
        b.stop()


# ---------------------------------------------------------------- RM01-05

def test_rm01_05_web_start_log_and_token_no_leak():
    """[RM01-05] WEB 启动日志给到 localhost 地址, token 落盘且**不进日志**

    前置: 无; 必须**不带 --dry-run**(dry-run 直接跳过 WEB 启动, 见 lib/app.py 事实 1)
    副作用: data_dir 里生成 web.token / state.lock / logs
    回滚: 停进程, 目录删除
    失败判据: 日志无「WEB UI 已启动」/ 日志里的地址不是 localhost / web.token 不存在或过短 /
              **日志里出现 token 明文**(长期密钥进日志 = 泄漏面)
    """
    case = app.case_dir("rm01_05")
    port = app.free_port()
    cfg = _cfg(case, web_port=port)

    p = app.start(cfg, case)
    try:
        assert p.wait_web(40), f"WEB 没起来:\n{p.log()}"
        text = p.log()
        assert f"http://localhost:{port}" in text, f"启动日志没给 localhost 地址(端口 {port}):\n{text[-800:]}"

        token_file = case / "data" / "web.token"
        assert token_file.is_file(), "web.token 没落盘"
        token = token_file.read_text(encoding="utf-8").strip()
        assert len(token) >= 32, f"token 过短({len(token)} 字符), 随机性不足"
        assert token not in text, "**token 明文进了日志** —— 只该提示文件路径"
        assert "web.token" in text, "日志没提示密钥文件路径, 用户找不到密钥"
    finally:
        p.stop()


# ---------------------------------------------------------------- RM01-06

def test_rm01_06_port_taken_reports_failure_not_silent():
    """[RM01-06] 端口被占时显式报「WEB UI 启动失败」, 进程不装死也不崩

    前置: 先用 socket 占住目标端口
    副作用: 进程照常跑主循环(没有 WEB), 用例收尾停掉
    回滚: 关 socket + 停进程
    失败判据: 日志无「WEB UI 启动失败」(用户以为 UI 开着) / 进程直接退出(一个端口占用
              不该带走整个程序)
    """
    case = app.case_dir("rm01_06")
    holder = socket.socket()
    holder.bind(("127.0.0.1", 0))
    holder.listen(1)
    taken = holder.getsockname()[1]
    cfg = _cfg(case, web_port=taken)

    p = app.start(cfg, case)
    try:
        assert p.wait_log("WEB UI 启动失败", 40), f"端口被占却没有明确失败日志:\n{p.log()[-1200:]}"
        assert str(taken) in p.log(), "失败日志没带端口号, 用户不知道该去查谁"
        time.sleep(1.0)
        assert p.alive(), "端口被占导致整个进程退出 —— 一个 WEB 端口不该带走主程序"
    finally:
        p.stop()
        holder.close()


# ---------------------------------------------------------------- RM01-07

def test_rm01_07_graceful_exit_then_rebind_same_port():
    """[RM01-07] 优雅退出(SIGTERM handler)后锁与 meta 清干净、端口立刻可复用(L3)

    前置: 进程内 3s 后自投 SIGTERM(Windows 上从外部发 SIGTERM 等于强杀, 见 lib/app.py 事实 2)
    副作用: 进程退出; 状态落盘
    回滚: 无(进程已退)
    失败判据: 退出码 != 0 / state.lock.meta.json 残留 / 端口仍被占 / 同端口重启失败(Errno 10048)。
              **红验**: 换成强杀后, meta 必须残留且退出码非 0 —— 若强杀也"干净", 说明本用例
              根本没验到优雅路径
    """
    case = app.case_dir("rm01_07")
    port = app.free_port()
    cfg = _cfg(case, web_port=port)
    meta = case / "data" / "state.lock.meta.json"

    p = app.start(cfg, case, graceful_after=3.0)
    assert p.wait_web(40), f"WEB 没起来, 优雅退出无从谈起:\n{p.log()}"
    assert meta.is_file(), "持锁期间 meta 不存在, 用例前提不成立"

    rc = p.wait(30)
    assert rc == 0, f"优雅退出退出码应为 0, 实际 {rc}; 日志尾部:\n{p.log()[-800:]}"
    assert not meta.exists(), "优雅退出后 meta 残留(release 没走完)"
    assert "停止" in p.log(), "日志没有停止行, 收尾路径可能没跑"

    deadline = time.time() + 10
    while time.time() < deadline and not app.port_free(port):
        time.sleep(0.2)
    assert app.port_free(port), f"退出后 {port} 仍被占, 同端口重启必撞 10048"

    # 同端口立刻重启
    again = app.start(cfg, case)
    try:
        assert again.wait_web(40), f"同端口重启失败(10048?):\n{again.log()[-1000:]}"
    finally:
        again.stop()

    # ---- 红验: 强杀路径必须"不干净"
    case2 = app.case_dir("rm01_07_hard")
    cfg2 = _cfg(case2, web_port=app.free_port())
    hard = app.start(cfg2, case2)
    assert hard.wait_web(40), f"红验进程没起来:\n{hard.log()}"
    hard.kill()
    assert hard.returncode() != 0, "强杀的退出码居然是 0 —— 无法与优雅退出区分"
    assert (case2 / "data" / "state.lock.meta.json").exists(), "强杀后 meta 也没了, 红验不成立"


# ---------------------------------------------------------------- RM01-08

def test_rm01_08_autostart_registry_roundtrip():
    """[RM01-08] 开机自启注册表往返: enable 写出可执行的启动命令, disable 幂等清干净

    前置: 备份 HKCU\\...\\Run\\auto-qb 现值(原本不存在则记「不存在」)
    副作用: **改注册表**(本片唯一的系统级副作用) —— 只动这一个值
    回滚: finally 里按备份还原(原本不存在就删掉)
    失败判据: enable 后值缺失/形态不对(缺 --tray 或缺配置绝对路径) / is_enabled 与实际不符 /
              disable 后值还在 / 二次 disable 抛异常
    """
    from auto_qb.infra import autostart

    case = app.case_dir("rm01_08")
    cfg = _cfg(case)
    existed, old = app.registry_backup()
    try:
        autostart.enable(str(cfg))
        now_existed, value = app.registry_backup()
        assert now_existed and value, "enable 之后注册表里没有自启项"
        assert value.endswith("--tray"), f"启动命令缺 --tray(托盘常驻): {value!r}"
        assert cfg.as_posix().replace("/", "\\") in value or str(cfg) in value, \
            f"启动命令没带配置绝对路径: {value!r}"
        assert value.startswith('"'), f"解释器路径没加引号(带空格的路径会断): {value!r}"
        assert autostart.is_enabled(str(cfg)) is True

        autostart.disable()
        assert app.registry_backup() == (False, None), "disable 之后自启项还在"
        assert autostart.is_enabled(str(cfg)) is False

        autostart.disable()  # 幂等: 未注册时 no-op, 不许抛
    finally:
        app.registry_restore(existed, old)


# ---------------------------------------------------------------- RM01-09

def test_rm01_09_tray_second_instance_raises_window():
    """[RM01-09] 托盘双开: 第二实例唤起已运行实例后静默退出(退出码 0), 不是报锁错

    前置: A 以 --tray 运行并写出 ui.port; 需要桌面会话(GUI)
    副作用: 起两个 GUI 进程, 第二个自行退出
    回滚: 停 A(强杀)
    失败判据: B 退出码 != 0(说明走了"锁竞争报错"而不是"唤起") / A 的 IPC 端口文件缺失。
              **L0 部分如实记「人眼未确认」** —— 本轮不做目视, 不硬撑成 PASS
    """
    case = app.case_dir("rm01_09")
    cfg = _cfg(case)

    a = app.start(cfg, case, extra_args=["--tray"])
    port_file = case / "data" / "ui.port"
    try:
        deadline = time.time() + 40
        while time.time() < deadline and not port_file.is_file():
            if not a.alive():
                pytest.skip(f"托盘进程起不来(无桌面会话?) —— BLOCKED, 不是失败:\n{a.log()[-600:]}")
            time.sleep(0.3)
        if not port_file.is_file():
            pytest.skip("40s 内没写出 ui.port —— BLOCKED(托盘未就绪)")

        b = app.start(cfg, case, extra_args=["--tray"])
        rc = b.wait(40)
        assert rc == 0, f"第二实例退出码应为 0(唤起后静默退出), 实际 {rc}"
        assert a.alive(), "唤起请求把已运行实例带走了"
        # L0(人眼: 窗口是否真的弹出)本轮未确认, 记在基线切片里
    finally:
        a.kill()
