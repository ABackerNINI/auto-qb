"""CLI 入口主路径守阵 (gtm.__main__): run 的启动/退出全序列 + 各命令错误出口.

设计单点: memory-bank/plans/26-10-21-0120-plan-gtm-coverage-gate.html (P1-T1.1)。

`cmd_run` 的 260-321 是「整条启动序列」—— 正主判定通过之后的每一步:
数据归属 -> 补写记录 -> 配置加载 -> Storage -> **单实例锁** -> 可选自启注册 ->
Sampler -> stop_event -> ControlServer -> 绑端口 -> 清注记 -> Notifier -> 恢复告警 ->
主循环 -> finally 三段收尾 + 释放锁。这段此前**没有任何用例走过**(覆盖率缺口 62 行),
而它恰好承载三条顺序不变式:

  S12/D8  锁必须早于 server.start()(绑端口)与采样循环 —— 抢输的第二实例不绑端口;
  S14/D13 自启注册排在锁之后、server.start() 之前 —— 抢输者不注册, 指针反映本次结果;
  收尾顺序 notifier.close -> server.stop -> storage.close -> release_lock,
          三者各自抛错只记不扩散(收尾阶段任何一步失败都不能吃掉后面的步骤)。

手法: 全部依赖用替身注入 (monkeypatch 换 `gtm.__main__` 命名空间里的名字),
不绑端口、不采样、不写真实指针目录 —— 与 tests/conftest.py 的 hermetic 守阵一致。

## 测试计划

- 主路径: 全序列顺序断言 (锁 -> 自启 -> server.start -> 清注记 -> 恢复 -> 主循环)
  + Storage/ControlServer/Notifier 收到的构造参数 (flush 参数 / 端口 / token 路径 /
  stop_event 同一对象)
- 自启: --autostart 且 config.autostart=true -> 注册且失败原因进指针; config=false
  -> 不注册; 无 --autostart -> 不注册; 注册抛 AutostartError -> 服务照常起 (不阻断)
- 早退: 身份层 IdentityError -> 1; 数据归属不符 -> 1; 配置校验失败 -> 1;
  锁被占 -> 1 (且不碰 server); 控制面端口占用 -> 1 + 释放锁
- 收尾: KeyboardInterrupt -> 0 且三段收尾齐全; 三段各自抛错 -> 仍 0 且后续步骤照做;
  recover 的告警进 WARNING 日志
- 主循环单轮容错: sample_once 抛错不杀循环 (下一轮重试); notify 抛错时 catch_up
  保持待补发 (首帧未消费)
- 其余出口: `_resolve_data_dir` 搬迁提示 / `_load_config_or_fail` 聚合报错与
  legacy 迁移提示 / `main()` 的 run 与 claim 分发 / `python -m gtm` 守卫 /
  `cmd_endpoint` 读失败与顶层非对象 / `cmd_claim` 身份失败与记录写入失败
"""

from __future__ import annotations

import argparse
import runpy
import sys
import threading

import pytest

from gtm import __main__ as cli
from gtm.config import Config
from gtm.identity import Decision, DeferredNote, Identity, IdentityError, PrimaryRecord
from gtm.installer import AutostartError, AutostartResult
from gtm.storage import SingleInstanceLockError

IDENTITY = Identity(install_root="/install/self", install_id="id-self")
PRIMARY = PrimaryRecord(id="id-self", install_path="/install/self", data_dir="/data/self")
OTHER = PrimaryRecord(id="id-other", install_path="/install/other", data_dir="")

# ---- 记录器 ----


class Recorder:
    """按发生顺序记录调用 (只记名字 + 关键参数, 供顺序不变式断言)."""
    def __init__(self) -> None:
        self.calls: list[tuple] = []

    def add(self, name: str, *detail) -> None:
        self.calls.append((name, ) + detail)

    def names(self) -> list[str]:
        return [c[0] for c in self.calls]

    def index(self, name: str) -> int:
        return self.names().index(name)

    def before(self, first: str, second: str) -> bool:
        return self.index(first) < self.index(second)


# ---- 替身 ----


class FakeStorage:
    """Storage 替身: 只实现 cmd_run 用到的面; 可配锁失败/恢复告警/收尾抛错."""
    def __init__(self, data_dir: str, recorder: Recorder, **opts) -> None:
        self.data_dir = data_dir
        self.dat_path = f"{data_dir}/traffic.dat"
        self._recorder = recorder
        self._opts = opts
        self.init_kwargs: dict = {}
        self.lock_held = False
        self.flush_params: tuple | None = None
        self.records: list = []

    def acquire_lock(self) -> None:
        self._recorder.add("storage.acquire_lock")
        exc = self._opts.get("lock_error")
        if exc is not None:
            raise exc
        self.lock_held = True

    def release_lock(self) -> None:
        self._recorder.add("storage.release_lock")
        self.lock_held = False

    def close(self) -> None:
        self._recorder.add("storage.close")
        exc = self._opts.get("close_error")
        if exc is not None:
            raise exc

    def recover(self, sampler) -> tuple[str, ...]:
        self._recorder.add("storage.recover")
        return tuple(self._opts.get("recover_warnings", ()))

    def set_flush_params(self, delta_bytes: int, interval_s: float) -> None:
        self.flush_params = (delta_bytes, interval_s)

    def record(self, result, snapshot) -> None:
        self.records.append((result, snapshot))


class FakeSampler:
    def __init__(self, adapter_filter=None) -> None:
        self.filter = adapter_filter
        self.samples = 0

    def sample_once(self):
        self.samples += 1
        return f"sample-{self.samples}"

    def snapshot(self):
        return {"snap": self.samples}


class FakeServer:
    """ControlServer 替身: 记录构造参数与 start/stop; 可配 start 抛 OSError (端口占用)."""

    instances: list["FakeServer"] = []

    def __init__(self, storage, sampler, holder, token_manager, recorder: Recorder, **opts) -> None:
        self.storage = storage
        self.sampler = sampler
        self.holder = holder
        self.token_manager = token_manager
        self.kwargs = opts
        self._recorder = recorder
        self.started = False
        self.stopped = False
        FakeServer.instances.append(self)

    def start(self) -> None:
        self._recorder.add("server.start")
        exc = self.kwargs.get("start_error")
        if exc is not None:
            raise exc
        self.started = True

    def stop(self) -> None:
        self._recorder.add("server.stop")
        self.stopped = True
        exc = self.kwargs.get("stop_error")
        if exc is not None:
            raise exc

    def url(self) -> str:
        return f"http://127.0.0.1:{self.kwargs.get('port', 0)}"


class FakeNotifier:
    instances: list["FakeNotifier"] = []

    def __init__(self, storage, holder, recorder: Recorder, **opts) -> None:
        self.storage = storage
        self.holder = holder
        self._recorder = recorder
        self._opts = opts
        self.notified: list[tuple] = []
        FakeNotifier.instances.append(self)

    def notify(self, result, *, catch_up: bool = False):
        self.notified.append((result, catch_up))
        exc = self._opts.get("notify_error")
        if exc is not None:
            raise exc
        return None

    def close(self) -> None:
        self._recorder.add("notifier.close")
        exc = self._opts.get("close_error")
        if exc is not None:
            raise exc


class FakeBackend:
    def __init__(self, recorder: Recorder, *, error: Exception | None = None) -> None:
        self._recorder = recorder
        self._error = error
        self.registered = 0

    def register(self):
        self._recorder.add("installer.register")
        self.registered += 1
        if self._error is not None:
            raise self._error
        return AutostartResult("registered", "已注册自启")

    def unregister(self):
        self._recorder.add("installer.unregister")
        return AutostartResult("unregistered", "已卸载自启")


class Harness:
    """一次 cmd_run 的全部可注入面 (默认全是「正常路径」, 用例按需覆盖单点)."""
    def __init__(self) -> None:
        self.recorder = Recorder()
        self.identity = IDENTITY
        self.identity_error: Exception | None = None
        self.decision = Decision("primary", PRIMARY, "本安装即注册正主")
        self.deferred: list[DeferredNote] = []
        self.cleared = 0
        self.relay_launcher: str | None = "/install/other/launch.cmd"
        self.ownership_error: Exception | None = None
        self.filled: list[tuple] = []
        self.config: Config | None = Config()
        self.config_errors: tuple[str, ...] = ()
        self.storage_opts: dict = {}
        self.sampler = FakeSampler()
        self.server_opts: dict = {}
        self.notifier_opts: dict = {}
        self.autostart_error: Exception | None = None
        self.loop_calls: list[tuple] = []
        self.loop_exc: BaseException | None = None
        self.install_calls: list[str] = []

    # -- 装配 --

    def install(self, monkeypatch) -> "Harness":
        rec = self.recorder

        def fake_identity():
            rec.add("identity")
            if self.identity_error is not None:
                raise self.identity_error
            return self.identity

        def fake_resolve(identity):
            rec.add("resolve_startup")
            return self.decision

        def fake_write_deferred(note):
            rec.add("write_deferred")
            self.deferred.append(note)

        def fake_clear_deferred():
            rec.add("clear_deferred")
            self.cleared += 1

        def fake_relay(install_root):
            rec.add("relay_launch", install_root)
            return self.relay_launcher

        def fake_ownership(data_dir, identity):
            rec.add("ensure_data_ownership", data_dir)
            if self.ownership_error is not None:
                raise self.ownership_error

        def fake_fill(identity, data_dir):
            rec.add("fill_primary_data_dir", data_dir)
            self.filled.append((identity, data_dir))

        def fake_load_config(data_dir):
            rec.add("load_config", data_dir)
            return self.config, self.config_errors

        def make_storage(data_dir, **kwargs):
            rec.add("Storage", data_dir)
            obj = FakeStorage(data_dir, rec, **self.storage_opts)
            obj.init_kwargs = kwargs
            return obj

        def make_sampler(*args, **kwargs):
            rec.add("Sampler")
            return self.sampler

        def make_server(storage, sampler, holder, token_manager, **kwargs):
            rec.add("ControlServer")
            opts = dict(self.server_opts)
            opts.update({k: v for k, v in kwargs.items() if k != "start_error" and k != "stop_error"})
            # 保留注入的异常开关 (不进 kwargs 断言面)
            for key in ("start_error", "stop_error"):
                if key in self.server_opts:
                    opts[key] = self.server_opts[key]
            return FakeServer(storage, sampler, holder, token_manager, rec, **opts)

        def make_token(path):
            rec.add("TokenManager", path)
            return argparse.Namespace(path=path)

        def make_notifier(storage, holder):
            rec.add("Notifier")
            return FakeNotifier(storage, holder, rec, **self.notifier_opts)

        def fake_loop(storage, sampler, holder, stop_event, notifier=None):
            rec.add("run_loop")
            self.loop_calls.append((storage, sampler, holder, stop_event, notifier))
            if self.loop_exc is not None:
                raise self.loop_exc

        def fake_build_installer(data_dir):
            rec.add("build_installer", data_dir)
            self.install_calls.append(data_dir)
            return FakeBackend(rec, error=self.autostart_error)

        for name, value in (
            ("load_or_create_install_id", fake_identity),
            ("resolve_startup", fake_resolve),
            ("write_deferred", fake_write_deferred),
            ("clear_deferred", fake_clear_deferred),
            ("relay_launch", fake_relay),
            ("ensure_data_ownership", fake_ownership),
            ("fill_primary_data_dir", fake_fill),
            ("_load_config_or_fail", fake_load_config),
            ("Storage", make_storage),
            ("Sampler", make_sampler),
            ("ControlServer", make_server),
            ("TokenManager", make_token),
            ("Notifier", make_notifier),
            ("_run_loop", fake_loop),
            ("build_installer", fake_build_installer),
        ):
            monkeypatch.setattr(cli, name, value)
        FakeServer.instances.clear()
        FakeNotifier.instances.clear()
        return self

    # -- 便利 --

    @property
    def server(self) -> FakeServer:
        return FakeServer.instances[0]

    @property
    def notifier(self) -> FakeNotifier:
        return FakeNotifier.instances[0]


def run_args(*, data_dir: str | None = "/data/self", autostart: bool = False) -> argparse.Namespace:
    return argparse.Namespace(command="run", data_dir=data_dir, autostart=autostart)


def run_cmd(monkeypatch, **harness_kwargs) -> tuple[int, Harness]:
    harness = Harness()
    for key, value in harness_kwargs.items():
        setattr(harness, key, value)
    harness.install(monkeypatch)
    return cli.cmd_run(run_args(autostart=harness_kwargs.get("autostart_flag", False))), harness


# ---- 主路径: 顺序不变式 ----


def test_run_primary_full_sequence_order(monkeypatch) -> None:
    """正主启动全序列: 判定 -> 归属 -> 配置 -> 锁 -> server.start -> 清注记 -> 主循环 -> 收尾.

    三条顺序不变式逐条断言: 锁早于 server.start; 清注记在 server.start 之后(权威时刻);
    收尾 notifier.close -> server.stop -> storage.close -> release_lock。
    """
    harness = Harness()
    harness.install(monkeypatch)
    code = cli.cmd_run(run_args())

    assert code == 0
    assert harness.recorder.names() == [
        "identity",
        "resolve_startup",
        "ensure_data_ownership",
        "fill_primary_data_dir",
        "load_config",
        "Storage",
        "storage.acquire_lock",
        "Sampler",
        "TokenManager",
        "ControlServer",
        "server.start",
        "clear_deferred",
        "Notifier",
        "storage.recover",
        "run_loop",
        "notifier.close",
        "server.stop",
        "storage.close",
        "storage.release_lock",
    ]
    # 顺序不变式 S12/D8: 锁早于绑端口
    assert harness.recorder.before("storage.acquire_lock", "server.start")
    # 顺序不变式: 清注记是「正主真正站起来」之后 (锁 + 端口齐备)
    assert harness.recorder.before("server.start", "clear_deferred")
    # 收尾顺序
    assert harness.recorder.before("notifier.close", "server.stop")
    assert harness.recorder.before("server.stop", "storage.close")
    assert harness.recorder.before("storage.close", "storage.release_lock")


def test_run_primary_constructs_with_live_objects(monkeypatch) -> None:
    """构造参数必须把活配置/同一 stop_event 传下去 (热重载与 /shutdown 都依赖这点)."""
    harness = Harness()
    harness.install(monkeypatch)
    assert cli.cmd_run(run_args()) == 0

    storage = harness.loop_calls[0][0]
    assert storage.init_kwargs == {
        "flush_delta_bytes": harness.config.flush_delta_bytes,
        "flush_interval_s": harness.config.flush_interval_s,
    }
    server = harness.server
    assert server.kwargs["host"] == harness.config.http_host
    assert server.kwargs["port"] == harness.config.http_port
    assert server.kwargs["autostart_error"] is None  # 未尝试注册
    stop_event = server.kwargs["stop_event"]
    assert isinstance(stop_event, threading.Event)
    assert stop_event.is_set()  # finally 置位: 主循环的 wait 不会残留
    # 主循环拿到的就是 server 绑定的同一个 stop_event (POST /shutdown 才能叫醒它)
    assert harness.loop_calls[0][3] is stop_event
    assert harness.loop_calls[0][4] is harness.notifier
    assert server.token_manager.path == "/data/self/monitor.token"
    # 归属补写: 只为自家记录补 data_dir
    assert harness.filled == [(IDENTITY, "/data/self")]


def test_run_primary_logs_recover_warnings(monkeypatch, caplog) -> None:
    """storage.recover 的告警逐条进 WARNING 日志 (启动可见, 不静默吞)."""
    harness = Harness()
    harness.storage_opts = {"recover_warnings": ("dat 坏行 3 条已跳过", "state 事件号回退")}
    harness.install(monkeypatch)
    with caplog.at_level("WARNING", logger="gtm"):
        assert cli.cmd_run(run_args()) == 0
    assert "dat 坏行 3 条已跳过" in caplog.text
    assert "state 事件号回退" in caplog.text


# ---- 自启 (S14/D13) ----


def test_run_autostart_registers_after_lock_before_server(monkeypatch) -> None:
    """--autostart 且 config.autostart=true: 注册排在锁之后、server.start 之前."""
    harness = Harness()
    harness.install(monkeypatch)
    code = cli.cmd_run(run_args(autostart=True))

    assert code == 0
    assert harness.recorder.before("storage.acquire_lock", "installer.register")
    assert harness.recorder.before("installer.register", "server.start")
    assert harness.server.kwargs["autostart_error"] is None
    assert harness.install_calls == ["/data/self"]  # 注册项写死的就是本次数据目录


def test_run_autostart_failure_reason_goes_into_endpoint(monkeypatch, caplog) -> None:
    """注册失败不阻断服务 (WARNING), 失败原因带进 ControlServer -> 落进发现指针."""
    harness = Harness()
    harness.autostart_error = AutostartError("Run 值超 260 字符")
    harness.install(monkeypatch)
    with caplog.at_level("WARNING", logger="gtm"):
        assert cli.cmd_run(run_args(autostart=True)) == 0
    assert harness.server.kwargs["autostart_error"] == "Run 值超 260 字符"
    assert harness.server.started  # 服务照常起来
    assert "Run 值超 260 字符" in caplog.text


def test_run_autostart_noop_when_config_disabled(monkeypatch, caplog) -> None:
    """用户显式关过 (config.autostart=false): 即便带 --autostart 也不注册 (不被装回)."""
    harness = Harness()
    harness.config = Config(autostart=False)
    harness.install(monkeypatch)
    with caplog.at_level("INFO", logger="gtm"):
        assert cli.cmd_run(run_args(autostart=True)) == 0
    assert harness.install_calls == []
    assert "autostart=false" in caplog.text


def test_run_without_autostart_flag_never_registers(monkeypatch) -> None:
    """无 --autostart: 不碰 installer (自启只由启动器/设置页触发)."""
    harness = Harness()
    harness.install(monkeypatch)
    assert cli.cmd_run(run_args(autostart=False)) == 0
    assert harness.install_calls == []
    assert "installer.register" not in harness.recorder.names()


# ---- 早退出口 ----


def test_run_lock_conflict_exits_1_without_touching_server(monkeypatch, capsys) -> None:
    """抢输的第二个实例: fail-fast 退出 1, 不绑端口、不写指针、不采样 (S12/D8)."""
    harness = Harness()
    harness.storage_opts = {"lock_error": SingleInstanceLockError("已有实例持有锁 /data/self/instance.lock")}
    harness.install(monkeypatch)
    code = cli.cmd_run(run_args())

    assert code == 1
    assert "已有实例持有锁" in capsys.readouterr().err
    assert "ControlServer" not in harness.recorder.names()
    assert "server.start" not in harness.recorder.names()
    assert "run_loop" not in harness.recorder.names()


def test_run_port_conflict_releases_lock_and_exits_1(monkeypatch, capsys) -> None:
    """控制面端口占用: 报错退出 1 并释放锁 (不把锁带进僵尸态)."""
    harness = Harness()
    harness.server_opts = {"start_error": OSError("address already in use")}
    harness.install(monkeypatch)
    code = cli.cmd_run(run_args())

    assert code == 1
    err = capsys.readouterr().err
    assert "控制面启动失败" in err and "address already in use" in err
    assert harness.recorder.names()[-1] == "storage.release_lock"
    assert "clear_deferred" not in harness.recorder.names()  # 没站起来 -> 不清注记
    assert "Notifier" not in harness.recorder.names()


def test_run_ownership_error_exits_1(monkeypatch, capsys) -> None:
    """数据归属不符 (跨版本接管): 退出 1, 不建 Storage (一个字节都不写)."""
    harness = Harness()
    harness.ownership_error = IdentityError("data-id 属于另一安装 (id=id-other)")
    harness.install(monkeypatch)
    code = cli.cmd_run(run_args())

    assert code == 1
    assert "id-other" in capsys.readouterr().err
    assert "Storage" not in harness.recorder.names()
    assert harness.filled == []  # 归属没过 -> 不补写记录


def test_run_config_invalid_exits_1(monkeypatch) -> None:
    """配置校验失败: fail-fast 退出 1 (不静默用默认值继续, 黄金法则 4)."""
    harness = Harness()
    harness.config = None
    harness.config_errors = ("sample_interval 必须形如 5S", )
    harness.install(monkeypatch)
    assert cli.cmd_run(run_args()) == 1
    assert "Storage" not in harness.recorder.names()


def test_run_identity_error_exits_1(monkeypatch, capsys) -> None:
    """身份层不可用: 退出 1, 不写注记 (身份故障不是让位)."""
    harness = Harness()
    harness.identity_error = IdentityError("安装 ID 落盘失败")
    harness.install(monkeypatch)
    assert cli.cmd_run(run_args()) == 1
    assert "安装 ID 落盘失败" in capsys.readouterr().err
    assert harness.deferred == []


def test_run_refuse_writes_note_and_exits_1(monkeypatch, capsys) -> None:
    """拒绝项 (拷贝件/被移动): 写注记 + 退出 1, 不建 Storage."""
    harness = Harness()
    harness.decision = Decision("refuse", OTHER, "拒绝启动: 疑似拷贝件")
    harness.install(monkeypatch)
    assert cli.cmd_run(run_args()) == 1
    assert "疑似拷贝件" in capsys.readouterr().err
    assert [n.reason for n in harness.deferred] == ["refused"]
    assert harness.deferred[0].target_id == "id-other"
    assert "Storage" not in harness.recorder.names()


def test_run_relay_launches_primary_and_exits_0(monkeypatch, capsys) -> None:
    """让位: 代拉正主 + 写 relayed 注记 + 退出 0 (让位是正常行为)."""
    harness = Harness()
    harness.decision = Decision("relay", OTHER, "已让位: 正主是另一安装")
    harness.install(monkeypatch)
    assert cli.cmd_run(run_args()) == 0
    assert "已让位" in capsys.readouterr().err
    assert harness.recorder.names().count("relay_launch") == 1
    note = harness.deferred[0]
    assert note.reason == "relayed"
    assert note.target_install == "/install/other"
    assert "启动器缺失" not in note.detail


def test_run_relay_launcher_missing_annotates_note(monkeypatch) -> None:
    """代拉启动器缺失: 照常写注记, 原因进 detail (auto-qb 状态区可见)."""
    harness = Harness()
    harness.decision = Decision("relay", OTHER, "已让位: 正主是另一安装")
    harness.relay_launcher = None
    harness.install(monkeypatch)
    assert cli.cmd_run(run_args()) == 0
    assert "代拉启动器缺失" in harness.deferred[0].detail


# ---- 收尾 (finally 三段) ----


def test_run_keyboard_interrupt_still_runs_full_teardown(monkeypatch) -> None:
    """Ctrl+C: 记 INFO 后走完整收尾 (最终落盘 + 停控制面 + 释放锁), 退出 0."""
    harness = Harness()
    harness.loop_exc = KeyboardInterrupt()
    harness.install(monkeypatch)
    assert cli.cmd_run(run_args()) == 0
    names = harness.recorder.names()
    for step in ("notifier.close", "server.stop", "storage.close", "storage.release_lock"):
        assert step in names
    assert harness.server.stopped


def test_run_teardown_errors_are_swallowed(monkeypatch, caplog) -> None:
    """收尾三段各自抛错: 只记 exception, 不扩散 —— 后续步骤 (含释放锁) 照做."""
    harness = Harness()
    harness.notifier_opts = {"close_error": RuntimeError("notifier close 炸了")}
    harness.server_opts = {"stop_error": RuntimeError("server stop 炸了")}
    harness.storage_opts = {"close_error": RuntimeError("storage close 炸了")}
    harness.install(monkeypatch)
    with caplog.at_level("ERROR", logger="gtm"):
        assert cli.cmd_run(run_args()) == 0
    names = harness.recorder.names()
    assert names[-1] == "storage.release_lock"  # 锁一定释放
    assert "通知器收尾失败" in caplog.text
    assert "控制面停止失败" in caplog.text
    assert "最终落盘失败" in caplog.text


# ---- 主循环单轮容错 ----


def test_run_loop_single_round_failure_does_not_kill_loop() -> None:
    """单轮 sample_once 抛错只记 ERROR, 循环继续 (下一轮自愈), 直到 stop_event 置位."""
    stop = threading.Event()

    class ExplodingSampler(FakeSampler):
        def sample_once(self):
            super().sample_once()
            raise OSError("Windows replace 竞态耗尽重试")

    sampler = ExplodingSampler()
    storage = FakeStorage("/data/self", Recorder())
    holder = type("H", (), {"current": Config(sample_interval=0.01)})()
    thread = threading.Thread(target=cli._run_loop, args=(storage, sampler, holder, stop, None), daemon=True)
    thread.start()
    try:
        # 等到至少两轮都抛过错 —— 说明异常没杀循环
        for _ in range(200):
            if sampler.samples >= 2:
                break
            threading.Event().wait(0.01)
        assert sampler.samples >= 2
        assert storage.records == []  # 抛错的那轮没落盘
    finally:
        stop.set()
        thread.join(timeout=3)
    assert not thread.is_alive()


def test_run_loop_notifier_failure_keeps_catch_up_pending() -> None:
    """notify 抛错时首帧未被消费: 下一轮仍带 catch_up=True (补发不丢)."""
    stop = threading.Event()
    holder = type("H", (), {"current": Config(sample_interval=0.01)})()

    class FlakyNotifier:
        def __init__(self):
            self.calls = []

        def notify(self, result, *, catch_up=False):
            self.calls.append(catch_up)
            if len(self.calls) == 1:
                raise OSError("订阅端点假死")
            if len(self.calls) >= 3:
                stop.set()

    notifier = FlakyNotifier()
    thread = threading.Thread(
        target=cli._run_loop,
        args=(FakeStorage("/data/self", Recorder()), FakeSampler(), holder, stop, notifier),
        daemon=True,
    )
    thread.start()
    thread.join(timeout=5)
    assert not thread.is_alive()
    assert notifier.calls[0] is True  # 首帧 catch_up
    assert notifier.calls[1] is True  # 上一轮抛错 -> 仍是首帧, 继续补发
    assert notifier.calls[2] is False  # 成功之后才消费掉首帧


# ---- 其余出口 ----


def test_resolve_data_dir_prints_migration_message(monkeypatch, capsys) -> None:
    """默认目录 + 旧用户目录搬迁: 搬迁结论打到 stderr (失败也照常启动)."""
    monkeypatch.setattr(cli, "default_data_dir", lambda: "/data/default")
    monkeypatch.setattr(cli, "migrate_legacy_data_dir", lambda target: "已从旧目录搬迁 3 个文件")
    assert cli._resolve_data_dir(None) == "/data/default"
    assert "已从旧目录搬迁 3 个文件" in capsys.readouterr().err


def test_resolve_data_dir_explicit_skips_migration(monkeypatch) -> None:
    """显式 --data-dir: 不搬迁 (用户说了算), 也不打印搬迁提示."""
    def boom(target):
        raise AssertionError("显式目录不该触发搬迁")

    monkeypatch.setattr(cli, "migrate_legacy_data_dir", boom)
    assert cli._resolve_data_dir("/data/explicit") == "/data/explicit"


def test_load_config_or_fail_prints_each_error(monkeypatch, capsys) -> None:
    """校验失败: 聚合错误逐条打到 stderr, 返回 (None, errors)."""
    monkeypatch.setattr(cli, "load_config", lambda path: (None, ("e1: 未知键 x", "e2: 端口越界")))
    config, errors = cli._load_config_or_fail("/data/self")
    assert config is None and errors == ("e1: 未知键 x", "e2: 端口越界")
    err = capsys.readouterr().err
    assert "e1: 未知键 x" in err and "e2: 端口越界" in err


def test_load_config_or_fail_reports_legacy_migration(monkeypatch, capsys) -> None:
    """加载成功 + 盘上是旧式裸数值: 迁移一次并打印提示 (只提示, 不改判定)."""
    config = Config()
    monkeypatch.setattr(cli, "load_config", lambda path: (config, ()))
    monkeypatch.setattr(cli, "migrate_legacy_config", lambda path: "已把 sample_interval 改写为 5S")
    assert cli._load_config_or_fail("/data/self") == (config, ())
    assert "已把 sample_interval 改写为 5S" in capsys.readouterr().err


def test_load_config_or_fail_silent_when_nothing_to_migrate(monkeypatch, capsys) -> None:
    """无旧值: migrate 返回空串 -> 不打印 (不制造噪音)."""
    config = Config()
    monkeypatch.setattr(cli, "load_config", lambda path: (config, ()))
    monkeypatch.setattr(cli, "migrate_legacy_config", lambda path: "")
    assert cli._load_config_or_fail("/data/self") == (config, ())
    assert capsys.readouterr().err == ""


def test_main_dispatches_run_and_claim(monkeypatch) -> None:
    """main() 的 run / claim 分发 (子命令 -> 处理函数, 返回码原样透传)."""
    seen: list[str] = []
    monkeypatch.setattr(cli, "cmd_run", lambda args: seen.append("run") or 7)
    monkeypatch.setattr(cli, "cmd_claim", lambda args: seen.append("claim") or 8)
    assert cli.main(["run", "--data-dir", "/d"]) == 7
    assert cli.main(["claim", "--data-dir", "/d"]) == 8
    assert seen == ["run", "claim"]


def test_module_main_guard_runs_cli(monkeypatch, capsys) -> None:
    """`python -m gtm` 守卫: 以 __main__ 跑模块 -> 无子命令打印帮助并 exit 0."""
    monkeypatch.setattr(sys, "argv", ["global-traffic-monitor"])
    with pytest.raises(SystemExit) as excinfo:
        runpy.run_module("gtm.__main__", run_name="__main__")
    assert excinfo.value.code == 0
    assert "usage: global-traffic-monitor" in capsys.readouterr().out


def test_endpoint_read_oserror_exits_1(tmp_path, monkeypatch, capsys) -> None:
    """发现指针读失败 (非「缺失」的 OSError): 报错退出 1, 不与「未运行」混淆."""
    ptr = tmp_path / "ptr"
    (ptr / "endpoint.json").mkdir(parents=True)  # 指针路径是目录 -> open 抛 IsADirectoryError
    monkeypatch.setattr("gtm.storage.pointer_dir", lambda: str(ptr))
    assert cli.main(["endpoint"]) == 1
    err = capsys.readouterr().err
    assert "读取发现指针失败" in err
    assert "未找到发现指针" not in err


def test_endpoint_payload_not_object_exits_1(tmp_path, monkeypatch, capsys) -> None:
    """指针顶层非对象 (JSON 合法但不是 dict): 报错退出 1, 不猜字段."""
    ptr = tmp_path / "ptr"
    ptr.mkdir()
    (ptr / "endpoint.json").write_text("[1, 2]", encoding="utf-8")
    monkeypatch.setattr("gtm.storage.pointer_dir", lambda: str(ptr))
    assert cli.main(["endpoint"]) == 1
    assert "顶层非对象" in capsys.readouterr().err


def test_claim_identity_error_exits_1(monkeypatch, capsys) -> None:
    """claim 前置身份失败: 退出 1 (还没碰锁与记录)."""
    monkeypatch.setattr(cli, "load_or_create_install_id", lambda: (_ for _ in ()).throw(IdentityError("ID 不可读")))

    def no_lock(*args, **kwargs):
        raise AssertionError("身份失败不该走到取锁")

    monkeypatch.setattr(cli, "SingleInstanceLock", no_lock)
    assert cli.main(["claim", "--data-dir", "/data/self"]) == 1
    assert "ID 不可读" in capsys.readouterr().err


def test_claim_primary_write_failure_exits_1(monkeypatch, capsys) -> None:
    """重登记写记录失败 (OSError): 退出 1 并给出记录路径 (人工修复入口)."""
    monkeypatch.setattr(cli, "load_or_create_install_id", lambda: IDENTITY)
    monkeypatch.setattr(cli, "_resolve_data_dir", lambda explicit: "/data/self")
    monkeypatch.setattr(cli, "ensure_data_ownership", lambda data_dir, identity: None)
    monkeypatch.setattr(cli, "primary_path", lambda: "/ptr/primary.json")

    def boom(record):
        raise OSError("拒绝访问")

    monkeypatch.setattr(cli, "write_primary", boom)

    class FakeLock:
        def __init__(self, path):
            self.path = path
            self.released = False

        def acquire(self):
            return None

        def release(self):
            self.released = True

    locks: list[FakeLock] = []

    def make_lock(path):
        locks.append(FakeLock(path))
        return locks[-1]

    monkeypatch.setattr(cli, "SingleInstanceLock", make_lock)
    assert cli.main(["claim", "--data-dir", "/data/self"]) == 1
    err = capsys.readouterr().err
    assert "重登记失败" in err and "/ptr/primary.json" in err
    assert locks[0].released  # 失败也释放锁 (finally)
