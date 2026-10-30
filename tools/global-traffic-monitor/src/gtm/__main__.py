"""global-traffic-monitor 命令行入口 (包名仍为 gtm; D16)。

子命令:
  run [--data-dir DIR] [--autostart]
                                  采样-落盘-通知主循环 (单写线程; 控制面随 run 启动)
                                  --autostart: 本次拉起顺带幂等注册开机自启 (S14/D13)
                                  启动先过正主注册判定 (计划 26-10-20-1316 §03): 让位方
                                  代拉注册正主后立即退出, 自身不写任何数据
  install-autostart               三平台自启幂等注册 (S5)
  uninstall-autostart             三平台自启幂等卸载 (S5)
  endpoint                        读发现指针打印当前端点 host:port / token_path / data_dir
                                  (S13/D9: 端口随机后用户无从得知端口, 此命令回告)
  claim [--data-dir DIR]          人工易主唯一通道: 重登记本安装为正主 (计划 §03/D5;
                                  工具运行中或数据归属不符则拒绝, 非零退出)
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import threading
from typing import Optional

from gtm import __version__
from gtm.config import Config, ConfigHolder, load_config, migrate_legacy_config
from gtm.installer import AutostartError, UnsupportedPlatformError, build_installer
from gtm.identity import (
    Decision,
    DeferredNote,
    Identity,
    IdentityError,
    PrimaryRecord,
    clear_deferred,
    ensure_data_ownership,
    fill_primary_data_dir,
    load_or_create_install_id,
    primary_path,
    relay_launch,
    resolve_startup,
    write_deferred,
    write_primary,
)
from gtm.notifier import Notifier
from gtm.sampler import AdapterFilter, Sampler
from gtm.server import ControlServer, TokenManager
from gtm.storage import (
    ENDPOINT_SCHEMA,
    SingleInstanceLock,
    SingleInstanceLockError,
    Storage,
    default_data_dir,
    endpoint_path,
    instance_lock_path,
    migrate_legacy_data_dir,
)

logger = logging.getLogger("gtm")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="global-traffic-monitor",
        description="全局流量监视小工具 (TrafficMonitor 替代)",
    )
    parser.add_argument(
        "-V",
        "--version",
        action="version",
        version=f"global-traffic-monitor {__version__}",
        help="打印版本号并退出",
    )
    sub = parser.add_subparsers(dest="command", metavar="<命令>")
    run = sub.add_parser("run", help="前台运行采样-落盘主循环 (自启机制拉起的前台服务)")
    run.add_argument(
        "--data-dir",
        default=None,
        metavar="DIR",
        help=f"工具数据目录 (dat/state/lock/config 落点); 默认 {default_data_dir()!r} 或环境变量 GLOBAL_TRAFFIC_MONITOR_DATA_DIR",
    )
    # S14/D13: 布尔开关, 只表示「本次拉起顺带幂等注册」, 不承载 true|false 取值 ——
    # 是否真注册由工具 config autostart 唯一裁决 (用户显式关过 -> 本次 no-op, 不被装回)。
    run.add_argument(
        "--autostart",
        action="store_true",
        help="本次拉起顺带幂等注册开机自启; 是否真注册由工具 config autostart 裁决 (用户关过则 no-op)",
    )
    install = sub.add_parser("install-autostart", help="注册开机自启 (三平台, 幂等)")
    install.add_argument(
        "--data-dir",
        default=None,
        metavar="DIR",
        help="写进注册项的数据目录 (解析成绝对路径写死; 自启拉起不依赖环境变量)",
    )
    sub.add_parser("uninstall-autostart", help="卸载开机自启 (三平台, 幂等)")
    sub.add_parser("endpoint", help="读发现指针打印当前端点 (host:port / token_path / data_dir; 端口随机后手工调试用)")
    claim = sub.add_parser(
        "claim",
        help="重登记本安装为整机正主 (唯一人工易主通道; 工具运行中/数据归属不符则拒绝)",
    )
    claim.add_argument(
        "--data-dir",
        default=None,
        metavar="DIR",
        help=f"重登记指向的数据目录; 默认 {default_data_dir()!r} 或环境变量 GLOBAL_TRAFFIC_MONITOR_DATA_DIR",
    )
    return parser


def _resolve_data_dir(explicit: Optional[str]) -> str:
    """解析实际数据目录: --data-dir 显式优先 (不搬迁); 否则默认目录 + 旧用户目录一次性搬迁 (D12)。

    搬迁只对「用了新默认目录」的场景生效 —— 用户显式给了目录就按他说的来, 不擅自从
    旧位置搬数据进去。搬迁失败只 WARNING 不阻断启动 (migrate_legacy_data_dir 内部容错)。
    """
    if explicit:
        return explicit
    target = default_data_dir()
    msg = migrate_legacy_data_dir(target)
    if msg:
        print(f"global-traffic-monitor: {msg}", file=sys.stderr)
    return target


def _build_adapter_filter(config: Config) -> AdapterFilter:
    """配置 -> 适配器过滤 (采样循环每轮重建: PUT /config 改 include/exclude 热生效).

    模式列表以 `|` 并入单个正则 (AdapterFilter 收单正则串; 空列表 -> None)。
    过滤集变更会让采样器的合计口径与既有基线错位一次: 下次 delta 判定为计数器
    重置 (记 0 + WARNING) 后自愈, 属预期降级而非数据损坏。
    非法正则已在 config 校验层拒掉 (聚合报错), 到不了这里。
    """
    include = "|".join(config.adapter_include) or None
    exclude = "|".join(config.adapter_exclude) or None
    return AdapterFilter(include=include, exclude=exclude)


def _run_loop(
    storage: Storage,
    sampler: Sampler,
    holder: ConfigHolder,
    stop_event: threading.Event,
    notifier: Notifier | None = None,
) -> None:
    """采样-落盘-通知主循环 (每轮读 holder.current: PUT /config 热重载即时生效)。

    stop_event.wait 替代 time.sleep: 停止信号即时响应 (不空等一个采样间隔)。
    单轮异常只记 ERROR 不杀循环 (与「通知失败不阻断落盘」对称)。

    通知 (S4): 阈值参数每轮现读 (热重载生效); **首个成功帧**走 catch_up 补发一次
    —— 启动/崩溃恢复后订阅者的视图可能已陈旧 (计划 §04 S4)。catch_up 只在派发
    成功后才算完成 (notify 抛错时保持待补发, 下一轮重试)。
    """
    first_frame = True
    while not stop_event.is_set():
        cfg = holder.current
        try:
            # 过滤器重建也进 try: 配置侧万一漏过非法正则, 只丢一轮不杀循环
            sampler.filter = _build_adapter_filter(cfg)
            storage.set_flush_params(cfg.flush_delta_bytes, cfg.flush_interval_s)
            result = sampler.sample_once()
            storage.record(result, sampler.snapshot())
            if notifier is not None:
                notifier.notify(result, catch_up=first_frame)
                first_frame = False
        except Exception:
            # 单轮采样/落盘/通知失败 (Windows replace 竞态耗尽重试/磁盘满/state 写失败
            # 等) 不杀守护进程: ERROR 可见, 下一轮重试自愈 (与「通知失败不阻断落盘」
            # 对称)
            logger.exception("采样/落盘/通知本轮失败, 下一轮重试")
        stop_event.wait(cfg.sample_interval)


def _note_from(reason: str, identity: Identity, decision: Decision) -> DeferredNote:
    """从判定结论构造让位/被拒注记 (工具侧写, auto-qb 只读展示 —— 镜像常量各持一份).

    detail 直接带判定 message (人读处置指引); target 字段在 refuse 分支多为记录
    自身 (拷贝件场景记录指向的就是「另一份同 id 安装」), 在 relay 分支是正主。
    """
    record = decision.record
    return DeferredNote(
        reason=reason,
        from_install=identity.install_root,
        target_install=record.install_path if record else "",
        target_id=record.id if record else "",
        detail=decision.message,
    )


def cmd_run(args: argparse.Namespace) -> int:
    logging.basicConfig(
        stream=sys.stderr,
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    # 正主注册判定 (计划 §03 矩阵): 排在取锁/绑端口/解析数据目录之前 —— 身份不定,
    # 后面每一步都可能在替别人的安装打工。让位方绝不自身启动 (Q1-a): 代拉正主后
    # 立即退出 (exit 0 —— 让位是正常行为, auto-qb 探活会等到正主应答); 拒绝/矛盾
    # 落注记交人工 (exit 1)。
    try:
        identity = load_or_create_install_id()
        decision = resolve_startup(identity)
    except IdentityError as e:
        print(f"global-traffic-monitor: {e}", file=sys.stderr)
        return 1
    if decision.kind == "refuse":
        # ③ 拷贝件/安装被移动/记录矛盾: 不写任何数据, 注记进指针目录 (auto-qb 状态区展示)
        write_deferred(_note_from("refused", identity, decision))
        print(f"global-traffic-monitor: {decision.message}", file=sys.stderr)
        return 1
    if decision.kind == "relay":
        # ④ 让位: 代拉注册正主安装后立即退出; 启动器缺失也照常写注记 (原因进 detail)
        launcher = relay_launch(decision.record.install_path)
        note = _note_from("relayed", identity, decision)
        if launcher is None:
            note = DeferredNote(
                reason=note.reason,
                from_install=note.from_install,
                target_install=note.target_install,
                target_id=note.target_id,
                detail=note.detail + " (代拉启动器缺失, 正主未能自动拉起)",
            )
        write_deferred(note)
        print(f"global-traffic-monitor: {decision.message}", file=sys.stderr)
        return 0
    # claim/primary: 本安装即 (或刚认领为) 正主, 继续既有启动序列
    logger.info(
        "正主判定 | %s | id=%s install=%s",
        decision.message,
        identity.install_id,
        identity.install_root,
    )
    data_dir = _resolve_data_dir(args.data_dir)
    # 数据归属 (版本血统防线): 本安装要写的这份数据必须认得出本安装; 只为自家记录
    # 补写空的 data_dir 信息位 (唯一自动写点, 不削弱拷贝件拒绝 —— 被拒的进程走不到这)
    try:
        ensure_data_ownership(data_dir, identity)
    except IdentityError as e:
        print(f"global-traffic-monitor: {e}", file=sys.stderr)
        return 1
    fill_primary_data_dir(identity, data_dir)
    # 配置加载: 校验失败 fail-fast 并聚合报错 (黄金法则 4; 不静默用默认值继续)
    config, _ = _load_config_or_fail(data_dir)
    if config is None:
        return 1
    holder = ConfigHolder(config)
    storage = Storage(
        data_dir,
        flush_delta_bytes=config.flush_delta_bytes,
        flush_interval_s=config.flush_interval_s,
    )
    try:
        storage.acquire_lock()  # fail-fast: 二次启动即报错 (单实例)
        # 顺序不变式 (S12/D8): 锁必须早于 server.start() (绑端口) 与采样循环 ——
        # 抢输的第二个进程在此 fail-fast, 不绑任何端口、不写发现指针、不采样。
    except SingleInstanceLockError as e:
        print(f"global-traffic-monitor: {e}", file=sys.stderr)
        return 1
    autostart_error: Optional[str] = None
    if getattr(args, "autostart", False):
        # S14/D13 自启意图: 锁已到手才注册 (抢输的第二实例不注册)。排在 server.start()
        # 之前 —— start() 写发现指针时会现货态探测 autostart_registered, 让指针反映
        # 本次注册结果 (指针与真值一致, 免一轮滞后); 失败原因同路带进指针 (issue
        # 26-10-17-1455: 只有「未注册」没有原因, 用户无从排障)。
        autostart_error = _maybe_register_autostart(data_dir, config)
    sampler = Sampler(adapter_filter=_build_adapter_filter(config))
    # 优雅退出信号 (26-10-17-1737 S3): 先于 ControlServer 构造 —— POST /shutdown 置位它,
    # 主循环的 stop_event.wait 即时醒; 退出仍走下方既有 finally (最终落盘 + 释放锁 +
    # 停控制面 + 删指针), 不新造收尾路径。
    stop_event = threading.Event()
    server = ControlServer(
        storage,
        sampler,
        holder,
        TokenManager(f"{data_dir}/monitor.token"),
        host=config.http_host,
        port=config.http_port,
        autostart_error=autostart_error,
        stop_event=stop_event,
    )
    try:
        server.start()  # fail-fast: 控制面端口占用即报错 (计划 §03 S3)
    except OSError as e:
        print(f"global-traffic-monitor: 控制面启动失败 (端口 {config.http_port} 被占用?): {e}", file=sys.stderr)
        storage.release_lock()
        return 1
    # 权威时刻: 单实例锁 + 控制面端口 + 发现指针齐备, 正主真正站起来 —— 清掉
    # 让位/被拒注记 (注记是 auto-qb 状态区的临时可见性, 权威方成功即失效)
    clear_deferred()
    notifier = Notifier(storage, holder)
    try:
        for w in storage.recover(sampler):
            logger.warning("恢复告警 | %s", w)
        logger.info(
            "global-traffic-monitor 启动 | data_dir=%s dat=%s sample_interval=%ss 通知阈值=%dMiB 控制面=%s",
            data_dir,
            storage.dat_path,
            config.sample_interval,
            config.notify_threshold_bytes // (1024 * 1024),
            server.url(),
        )
        _run_loop(storage, sampler, holder, stop_event, notifier)
    except KeyboardInterrupt:
        logger.info("收到中断, 优雅退出 (最终落盘 + 释放锁 + 停控制面)")
    finally:
        stop_event.set()
        try:
            notifier.close()  # 有界等待在途推送 (守护线程, 超时即弃)
        except Exception:
            logger.exception("通知器收尾失败")
        try:
            server.stop()
        except Exception:
            logger.exception("控制面停止失败")
        try:
            storage.close()
        except Exception:
            logger.exception("最终落盘失败 (下次启动从 state/dat 恢复)")
        storage.release_lock()
    return 0


def _maybe_register_autostart(data_dir: str, config: Config) -> Optional[str]:
    """run --autostart 的顺带幂等注册 (S14/D13): 裁决权在工具 config autostart.

    仅 config.autostart 为真才调 installer.register(); 用户显式关过 (false) -> 本次
    no-op, 不被自动装回。注册失败只 WARNING 不阻断服务 —— 工具已在跑, 自启是便利,
    不是本次运行的成立前提 (与「发现指针写失败不阻断服务」同口径 §09)。幂等性由
    installer 的期望态判据保证 (已注册 -> skipped, 不重复建项)。

    返回**失败原因** (成功/未尝试 -> None): 调用方把它带进 ControlServer, 写发现指针
    时落进 `autostart_error` —— 否则用户只看到设置页「未注册」, 不知为什么 (issue
    26-10-17-1455)。
    """
    if not config.autostart:
        logger.info("--autostart: 工具 config autostart=false (用户已关闭), 本次不注册")
        return None
    try:
        backend = build_installer(data_dir)
        result = backend.register()
    except AutostartError as e:
        logger.warning("--autostart 注册失败 (忽略, 不阻断服务): %s", e)
        return str(e)
    logger.info("--autostart: %s", result.message)
    return None


def _load_config_or_fail(data_dir: str) -> tuple[Config | None, tuple[str, ...]]:
    """加载 config.yml; 校验失败 -> 聚合错误逐条打到 stderr 并返回 (None, errors).

    加载成功后顺带做一次**旧式裸数值的迁移** (S7/D13): D13 之前盘上是
    `sample_interval: 5.0` / `flush_delta_bytes: 1048576`, 现在契约只认复合串
    (`"5S"` / `"1MiB"`)。读侧本来就兼容旧值 (units.parse_*), 这里把盘也一次性改写
    成规范形态 —— 只在真有旧值时写, 否则不碰文件 (migrate_legacy_config 内判)。
    """
    path = f"{data_dir}/config.yml"
    config, errors = load_config(path)
    if config is None:
        for e in errors:
            print(f"global-traffic-monitor: config 校验失败: {e}", file=sys.stderr)
        return config, errors
    message = migrate_legacy_config(path)
    if message:
        print(f"global-traffic-monitor: {message}", file=sys.stderr)
    return config, errors


def cmd_autostart(args: argparse.Namespace, *, install: bool) -> int:
    """自启注册/卸载 (S5): 幂等, 结果打到 stdout, 退出码供 S6 设置页判成败.

    退出码: 0 = 达成期望态 (含 skipped/absent 两种 no-op) · 1 = 平台命令失败/前置
    条件缺失 · 2 = 平台不支持 (非 Windows/Linux/macOS)。
    卸载不需要数据目录 (注册项按固定名称定位), 故 uninstall-autostart 无 --data-dir。
    """
    data_dir = _resolve_data_dir(getattr(args, "data_dir", None))
    try:
        backend = build_installer(data_dir)
    except UnsupportedPlatformError as e:
        print(f"global-traffic-monitor: {e}", file=sys.stderr)
        return 2
    except AutostartError as e:
        print(f"global-traffic-monitor: 自启{'注册' if install else '卸载'}失败: {e}", file=sys.stderr)
        return 1
    try:
        result = backend.register() if install else backend.unregister()
    except AutostartError as e:
        print(f"global-traffic-monitor: 自启{'注册' if install else '卸载'}失败: {e}", file=sys.stderr)
        return 1
    print(f"global-traffic-monitor: {result.message}")
    return 0


def cmd_endpoint(args: argparse.Namespace) -> int:
    """读发现指针 endpoint.json 打印当前端点 (S13/D9): host:port + token_path + data_dir。

    端口随机后端口不对用户可见, 此命令是手工调试的出口: 工具在跑 -> 指针存在, 解析后
    打印三字段。未运行/指针缺失/损坏 -> 报错退出 1。指针 schema 非本版本已知值只告警
    (§05: 不猜字段), 已知字段仍打印。
    """
    path = endpoint_path()
    try:
        with open(path, "r", encoding="utf-8") as f:
            raw = f.read()
    except FileNotFoundError:
        print(f"global-traffic-monitor: 未找到发现指针 {path} (工具似乎未在运行)", file=sys.stderr)
        return 1
    except OSError as e:
        print(f"global-traffic-monitor: 读取发现指针失败 {path}: {e}", file=sys.stderr)
        return 1
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"global-traffic-monitor: 发现指针损坏 {path}: {e}", file=sys.stderr)
        return 1
    if not isinstance(payload, dict):
        print(f"global-traffic-monitor: 发现指针格式非法 (顶层非对象): {path}", file=sys.stderr)
        return 1
    if payload.get("schema") != ENDPOINT_SCHEMA:
        print(
            f"global-traffic-monitor: 发现指针 schema={payload.get('schema')!r} 与本版本 ({ENDPOINT_SCHEMA}) 不符, 字段或有变 (仅供参考)",
            file=sys.stderr,
        )
    print(f"http://{payload.get('host')}:{payload.get('port')}")
    print(f"token_path: {payload.get('token_path')}")
    print(f"data_dir: {payload.get('data_dir')}")
    return 0


def cmd_claim(args: argparse.Namespace) -> int:
    """claim: 唯一人工易主通道 (计划 §03 / D5) —— 把本安装重登记为正主.

    护栏顺序 (D5, 与启动矩阵共用判据, 无第二套):
      1. 非阻塞试单实例锁: 工具正在跑 -> 拒绝 (提示先停止; 运行中的正主本就持锁,
         此时重登记会与它的启动路径对写记录);
      2. 数据归属: data-id 异 -> 拒绝 (跨版本接管同启动矩阵口径, 删 id 是显式人工);
      3. 原子重写 primary.json (id/install_path/data_dir 三项全用自己的事实) +
         清让位注记 (权威时刻) -> 释放锁, 退出 0.
    输出一人读结论行; 拒绝原因进 stderr (退出码非 0), 供 auto-qb 原样展示。
    """
    logging.basicConfig(
        stream=sys.stderr,
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    try:
        identity = load_or_create_install_id()
    except IdentityError as e:
        print(f"global-traffic-monitor: {e}", file=sys.stderr)
        return 1
    # 1) 非阻塞试锁 (timeout=0): 争则拒, 不排队不等待
    lock = SingleInstanceLock(instance_lock_path())
    try:
        lock.acquire()
    except SingleInstanceLockError as e:
        print(f"global-traffic-monitor: 工具正在运行, 请先停止再重登记 ({e})", file=sys.stderr)
        return 1
    try:
        # 2) 数据归属 (与 cmd_run 同一 ensure_data_ownership, 拒绝跨版本接管)
        data_dir = _resolve_data_dir(args.data_dir)
        try:
            ensure_data_ownership(data_dir, identity)
        except IdentityError as e:
            print(f"global-traffic-monitor: {e}", file=sys.stderr)
            return 1
        # 3) 原子重写记录 + 清注记 (记录损坏时本条路径同时也是修复入口)
        try:
            write_primary(
                PrimaryRecord(
                    id=identity.install_id,
                    install_path=identity.install_root,
                    data_dir=data_dir,
                    version=__version__,
                )
            )
        except OSError as e:
            print(f"global-traffic-monitor: 重登记失败 (记录写入 {primary_path()}): {e}", file=sys.stderr)
            return 1
        clear_deferred()
        print(
            f"global-traffic-monitor: 已重登记为正主: install={identity.install_root} "
            f"data={data_dir} (id={identity.install_id})"
        )
        return 0
    finally:
        lock.release()


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "run":
        return cmd_run(args)
    if args.command == "install-autostart":
        return cmd_autostart(args, install=True)
    if args.command == "uninstall-autostart":
        return cmd_autostart(args, install=False)
    if args.command == "endpoint":
        return cmd_endpoint(args)
    if args.command == "claim":
        return cmd_claim(args)
    # 无子命令: 打印帮助
    build_parser().print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
