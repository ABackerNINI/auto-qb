"""recycle_daemon: fastresume 收尾回收 daemon(计划 26-11-05-0808 §3.1 daemon 段/§3.2, D11-D13)

职权(D11 换位): 等 qB 下线窗口, 批量改写 pending 成员的 fastresume 双键, journal 落账。
**绝不**做: 删链(主循环在线做, D11)/碰 state.json(D13 账本契约, 与旧 guardian 同契约)/
taskkill(进程红线)/窗口外任何 fastresume 落盘(N1 铁律: qB 运行期秒级重写, 0.5s 实测覆盖)。

形制(D12 简化): 每 qB 实例至多一个 watcher;触发只有「qB 下线」一个事件 —— 无 TCP
nudge/无端口文件/无兜底扫;窗口开头现读 pending 集(supersede/取消即时生效, 窗口内逐拍
现读续保);进窗判据三层(计划 26-11-10-0318)—— L1 实例级证据链(owner 死证 + 新面孔
无害化, 证据齐即立即进窗无稳定期, 拍板 D2, 接线单点 _observe_poll/_l1_window_open);
L2 全机口径 = 三证(进程不在 + 端口拒连 + 稳定 STABLE_WINDOW, 判据函数已随 finalize_watch.py
整文件退役原样随迁进本模块, 本文件是其唯一 home, S4);L3 = L2 名册探测失败时的端口单证
降级支(原样);退位 = pid 抢占 + 旧 daemon 自检自杀, 绝不 taskkill;心跳 = daemon.json
(pid/ts)每 HEARTBEAT_INTERVAL touch。

账本(D13/D8): 只写 job journal(rewrites 成员账 + rewritten 相位), 绝不碰 state.json;
每个下线窗口限一轮会话, 窗口内失败重试至成功或 qB 回升, 失败计数(fails)进账;qB 抢先
回升 = 本轮放弃, 无害(N4 实证自愈: 成员经别名正常加载, journal 待重放, 下一窗口重放)。
半途崩溃/退位/回升都留下一致账态(逐成员即改即记账, 原子写), 下一窗口按账重放。

发现面: 扫 <data_dir>/relocate/*.spec.json 中属于本实例(host/port 字面相等, 不做
localhost/127.0.0.1 智能匹配)且带 bt_backup 字段(新链 spec 必带 —— S1 五闸保证 armed 前
config.relocate.bt_backup 已配置, 26-11-11-0259 S1 起为单实例标量)的 job;pending 口径单点在
relocate_journal.pending_members = 已记账(spec 成员清单)且 journal.rewrites 未收口
(REWRITE_SETTLED 之外)的成员。

与主循环的串行化(§07 并发写账行): daemon 只在 qB 离线时动 fastresume;主循环的
setLocation/取消/再迁移只在 qB 在线时可达;两侧写不同文件(job journal vs state.json)。

用法: `python -m auto_qb.tools.recycle_daemon --data-dir <dir> --host <host> --port <port>`
(独立 CLI 入口, 可手动运行做验证;规格/账本全经文件传递 —— 路径可能含非 ASCII, 不经
命令行;不 import 主循环 store/state/config)
"""
import argparse
import logging
import os
import re
import socket
import subprocess
import sys
import time
from typing import Any, Callable, Dict, Optional

from ..core import fastresume
from ..infra import relocate_journal as rj

logger = logging.getLogger(__name__)

HEARTBEAT_INTERVAL = 10.0  # daemon.json 心跳周期(D12: 每 10s touch)
HEARTBEAT_MAX_AGE = 60.0  # 心跳过期线(对账判挂死/重拉的口径, 与旧 guardian 判过期同量级)
POLL_INTERVAL = 5.0  # 主循环节拍(也是窗口内失败重试的节拍, D8)
GRACE_EXIT = 60.0  # pending 集空后的宽限退出时长(D12)

# ---------------------------------------------------------------- 三证判据(随 finalize_watch.py 整文件退役原样随迁, S4)
# 「qB 下线」进窗判据的三证: 进程不在(证一) + 端口拒连(证二) + 该状态稳定 STABLE_WINDOW
# 秒(证三)。严于 WebUI 探测 —— 这是 N1 铁律(qB 运行期秒级重写 fastresume)的守门粒度。


def _port_refused(host: str, port: int, timeout: float = 1.0) -> bool:
    """证二: 端口连不上 ⇒ 拒连(超时同按连不上处理: 我们要的是「qB 不在」, 不是诊断网络)"""
    if not port:
        return True  # 无端口可判 ⇒ 视为连不上(配合进程证一起才算三证)
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return False
    except OSError:
        return True


def _names_from_tasklist() -> tuple:
    """Windows: tasklist CSV 首列(引号内的映像名)"""
    out = subprocess.run(
        ["tasklist", "/NH", "/FO", "CSV"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=10,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    names = []
    for line in (out.stdout or "").splitlines():
        if line.startswith('"'):
            names.append(line.split('"')[1].lower())
    return tuple(names)


def _names_from_proc() -> tuple:
    """Linux: /proc/<pid>/comm(容器里普遍可用, 零子进程)"""
    names = []
    for pid in os.listdir("/proc"):
        if not pid.isdigit():
            continue
        try:
            with open(f"/proc/{pid}/comm", "r", encoding="utf-8") as f:
                names.append(f.read().strip().lower())
        except OSError:
            continue
    return tuple(names)


def _names_from_ps() -> tuple:
    """其它 POSIX: ps -eo comm="""
    out = subprocess.run(
        ["ps", "-eo", "comm="],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=10,
    )
    return tuple(n.strip().lower() for n in (out.stdout or "").splitlines())


def _qb_process_names() -> tuple:
    """进程名清单(跨平台尽力而为: 判不出返回空, 调用方按「未能证明进程不存在」处理)"""
    try:
        if os.name == "nt":
            return _names_from_tasklist()
        if os.path.isdir("/proc"):
            return _names_from_proc()
        return _names_from_ps()
    except Exception:  # noqa: BLE001 - 判不出进程表: 保守(不算「已退出」)
        return ()


def _proc_absent(names: tuple, host: str = "", port: int = 0) -> bool:
    """证一: 该端点的 qB 进程不存在; 名册可用时「进程不在 AND 端口拒连」双判合取(评审 #6)

    全机口径(复核纠正: 非「实例级判定」—— 进程名册分不出实例, 只能按全机判): 名册见
    任一 qB(任一实例, 日常库/测试库)⇒ 判「进程在」。多实例部署下窗口可用性让位于
    N1 铁律, 宁可不进窗 —— 收尾窗等全部 qB 进程退场才可能开(P7 真机实测形态: 日常
    实例在跑 ⇒ daemon 等不到窗口)。进程证与端口证**合取**(防「三证退化单证」的假
    阳性进窗 —— 端口拒连只证明 WebUI 不可达(被关/挂死/远程链路断而 BT_backup 文件
    系统可达), 不证明进程不在; 假阳性进窗 = daemon 在 qB 运行期改写 fastresume,
    N1 零写入铁律被破):
    - 名册可用: 名册见 qB(任一实例)⇒ 证一不成立 —— 即使端口拒连(N1 铁律, 宁可不进窗);
      名册无 qB ⇒ 再看端口证, 拒连才算成立。qB 真死时两证自然同向, 合取不损窗口可用性;
    - 名册不可用(探测命令异常 => 空名册): 退回端口单证, 但告警降级说明(证据链弱化必须
      留痕, 不许静默); 无端口可判(port=0)且无名册 ⇒ 未证明(False, 保守);
    - 无端口可判(port=0) ⇒ 退回全机名册单证(旧行为, 兼容无端口场景)。

    W2a 三层定位(计划 26-11-10-0318 §03): 本函数 = **L2 全机口径**的证一实现 —— 触发条件:
    L1 不成立(含无 owner 记录/owner 在位/证据未齐)或 L1 名册通道不可判(l1_open None);
    现状保留的原因 = 弱证据配 30s 稳定期
    (黄金法则 2: 观测缺失/通道故障保守退化, 行为与实例级证据接线前完全等价)。函数内部
    「名册不可用退端口单证」支 = **L3**(现状降级路径, 原样不动)。实例级增强路径(**L1**:
    owner 死证 + 新面孔无害化 + 端口拒连, 证据齐即立即进窗)见 _Observation/l1_open 与
    接线面 _observe_poll/_l1_window_open;方案单点文档 =
    memory-bank/plans/26-11-10-0318-plan-recycle-daemon-instance-evidence.html §03。
    """
    refused = bool(port) and _port_refused(host or "127.0.0.1", port)
    if names:
        if any("qbittorrent" in n for n in names):
            return False  # 名册见 qB: 进程证不成立(端口拒连 != 进程不在, 评审 #6)
        return refused or not port  # 名册无 qB: 与端口证合取; port=0 退回名册单证
    if not port or not refused:
        return False  # 无端口可判 / 端口在服务: 未证明(保守)
    logger.warning("进程名册不可用(探测命令异常), qB 下线判据退化为端口单证(WebUI 不可达被当进程不在)"
                   " —— N1 防线弱化, 请检查进程探测通道")
    return True


STABLE_WINDOW = 30.0  # 证三: 连续判定「qB 不在」这么久才算下线窗口开启


def _window_open(host: str, port: int) -> bool:
    """窗口开启判据的瞬时复验 = 证一+证二(进程不在 + 端口拒连; 证三「稳定 30s」只在
    进窗时要求一次, 见 run)。名册现读不用快照: qB 可能在任何毫秒起身 —— N1 铁律的
    守门粒度 = 每次落盘之前(与 guardian run 循环同款两证合取)。

    W2a 三层定位(计划 26-11-10-0318): 本函数是 **L2/L3 窗**的复验闸(现状两证, 签名与
    行为原样不动 —— 既有窗内替身以两参形态挂在本名上);本窗以 L1 实例级证据开启时, 复验
    升级为 §03.3 全套现读现判, 单点在 _l1_window_open —— 两闸分派在 _process_window
    (按本窗开启层选闸: 复验粒度必须与进窗判据同级)。"""
    return _proc_absent(_qb_process_names(), host, port) and _port_refused(host, port)


# ---------------------------------------------------------------- 实例级观测通道(计划 26-11-10-0318 §03.1, W1)
# O1 owner 归属(LISTENING 表解析 + qB 映像名交叉校验 => {pid, ct, ts})、O2 全机 qB 身份
# 枚举(pid + create_time)与 O3 全机 LISTENING 映射(W1b: 归属与 §03.2 监听集指纹共用的
# 读取底座, 每 poll 至多一次读取喂两个消费面); 消费这些观测的判据状态机本体在文件后段
# (W1b 的 _Observation)。证据语义铁律:
# 解析不出/超时/通道异常 = 本拍观测不可用 => 返回 None/空 + warning 留痕, 调用方必须退回
# L2 全机口径(_proc_absent), 绝不产生假证据(宁可不进窗, 不许假进窗)。零新依赖(禁
# psutil), 子进程一律 10s 超时; warning 节流(60s 一次, 不刷屏)属 W2 接线面的职责
# (已落地: WARNING_THROTTLE/_throttled_warn + 通道函数族的 warn 形参 —— 缺省 logger.warning
# 直落, 直接调用方/既有测试零感知; 接线面 _observe_poll 传节流绑定, 持续故障每(实例, 类)
# 1 条/60s)。

WARNING_THROTTLE = 60.0  # §03.1 通道纪律: 接线面告警节流周期(每实例每类一条, 不刷屏)

# 通道函数族的告警 sink 形参类型: 签名 (msg, *args, **kwargs) 与 logger.warning 兼容 ——
# 缺省直落(logger.warning), 接线面传 _warn_sink 的节流绑定(kwargs 透传, exc_info 不丢)
WarnSink = Callable[..., Any]


def _throttled_warn(flags: Dict[str, float], key: str, now: float, msg: str, *args: object, **kwargs: Any) -> None:
    """接线面告警节流(计划 §03.1 通道纪律): 同实例同类告警 WARNING_THROTTLE 秒内只首拍落
    log。flags 由调用方持有(run 每实例一份 => 天然「每实例每类」), now 用注入时钟(测试可
    钉节流边界, 与项目时钟注入风格一致)。两类消费: (a)接线点自身的新增告警(_observe_poll
    的观测账写失败/名册不可判/指纹通道不可用三处处置留痕, 与 _l1_window_open 复验拍的
    verdict None 处置留痕键 'reverify'); (b)通道函数经 warn 形参收到的
    节流绑定(_listening_map/_qb_processes/_observe_owner 全族 —— 持续故障形态下每 poll
    重复触发的通道告警在 sink 内被节流)。**kwargs 透传 logger.warning(exc_info 等不丢)。"""
    last = flags.get(key)
    if last is not None and now - last < WARNING_THROTTLE:
        return
    logger.warning(msg, *args, **kwargs)
    flags[key] = now


def _warn_sink(flags: Dict[str, float], key: str, now: float) -> WarnSink:
    """把 _throttled_warn 绑定成通道函数 warn 形参的直落形态((msg, *args, **kwargs) 签名,
    与 logger.warning 可互换)。每 poll 构造一次, 捕获当拍 now —— 节流判据用注入时钟,
    测试可钉节流边界。"""
    return lambda msg, *args, **kwargs: _throttled_warn(flags, key, now, msg, *args, **kwargs)


def _warn_kw(warn: Optional[WarnSink]) -> dict:
    """warn 形参的传递包装: 缺省(None)=> {} —— 平台分派对下层的调用表达式与 W1 原形
    字节级一致(既有测试的窄签名替身零感知, T3 评审 A1 硬要求「缺省路径字节级不变」);
    接线面传节流绑定后才带 warn 键下沉。"""
    return {} if warn is None else {"warn": warn}


# Windows FILETIME 纪元差: 1601-01-01 与 1970-01-01 之间的 100ns ticks(epoch 换算单点)
_FILETIME_1601_TO_EPOCH_TICKS = 116444736000000000
# /proc/<pid>/fd/* 读链接的 socket 形制(Linux LISTENING 归属用)
_SOCKET_LINK_RE = re.compile(r"^socket:\[(\d+)\]$")
# PowerShell 输出的健康标记行: 单次调用的管线走完才会输出, 缺它 = 管线半途而废 => 观测
# 不可用(区分「通道健康且全机无 qB({})」与「通道故障(None)」的唯一凭据)
_PS_QB_END_MARK = "qb-obs-end"

# 单次 PowerShell 调用批量取全机 qB 进程的 Id/ProcessName/StartTime(O1 的 ct 与 O2 的
# 枚举共用这一口, 计划 §03.1)。枚举形态: Get-Process 无参全量 + Where-Object 按映像名
# 过滤 —— 零匹配是**正常空管线**(语义即「健康零观测」), 不像 -Name 无匹配那样产生被
# SilentlyContinue 吞掉的命令级错误、把「健康零观测」与「命令失败」搅在一起。命令级真
# 失败在解析侧**不可读成 {}**: 管线与健康标记行整体包进外层 try, 任何终止型失败
# (语句终止/script 终止/-ErrorAction Stop 升级都算 —— PS 语句终止默认只中止当前管线、
# 脚本会继续走后续语句, 实测 2026-11-10)都被 catch 吞掉且**跳过标记行**, 解析侧见不到
# 标记一律 None(见 _qb_processes_from_powershell)。输出编码显式钉 UTF-8
# (pitfalls/ops/console-encoding.md: PS 管道输出按控制台码页编码, 中文 Windows = GBK ——
# 启动后第一句锁 [Console]::OutputEncoding, try/catch 兜无控制台场景; 数据行恒 ASCII
# (pid|name|filetime), 钉码失败也不损解析, 解码失败/异形输出由「无健康标记 => None」兜底)。
# StartTime 逐进程容错: 读不到(权限/已退出)该条目输出空 filetime, 由解析侧剔除 ——
# 聚合侧部分清单不冒充全量。
_PS_QB_SCRIPT = (
    "$ErrorActionPreference='SilentlyContinue';"
    "try { [Console]::OutputEncoding=[System.Text.Encoding]::UTF8 } catch {};"
    "try {"
    "Get-Process | Where-Object { $_.ProcessName -like '*qbittorrent*' } | ForEach-Object {"
    "$ft=''; try { $ft=[string]$_.StartTime.ToFileTimeUtc() } catch {};"
    "'{0}|{1}|{2}' -f $_.Id,$_.ProcessName,$ft };"
    f"'{_PS_QB_END_MARK}'"
    "} catch {}"
)


def _filetime_to_epoch(ft: int) -> float:
    """Windows FILETIME(1601-01-01 起的 100ns ticks)=> epoch 秒"""
    return (ft - _FILETIME_1601_TO_EPOCH_TICKS) / 10**7


def _listening_map_netstat(text: str, *, warn: Optional[WarnSink] = None) -> Optional[Dict[int, frozenset]]:
    """netstat 输出纯解析 => {pid: 监听本地端口集}(只取 LISTENING 行, 通配/具体/[::] 同算)

    warn: 告警 sink(缺省 logger.warning 直落; 接线面传节流绑定, 每实例每类 1/60s, T3 评审
    A1)—— 本函数全部告警经它出, 下同。

    解析口径与单端口归属同款(计划 §07 R2 的假设: TCP 数据行恒五列, 状态字各语言版一致
    为英文 LISTENING, W1 本机实测中英文输出); 本地端口按最后一个 ':' 取, 兼容 [::]:port
    的 IPv6 形; 非 LISTENING 行/列数不合/端口非数字逐行跳过, 不产假条目。证据语义(通道
    健康标记, T2 评审按 §07 R2「解析不出就退」收紧): **零条 LISTENING 行解析成功**(空
    输出/表头孤行/整包乱码/TCP 前缀行在而状态字或列数全不合)=> None + warning —— 真实
    Windows 机器恒有监听套接字(RPC/SMB 等), 零解析成功 = 格式漂移嫌疑; 没有这个标记,
    「整包乱码 => 人人空监听集 => 未决成员 30s 假 settle 吸收」正是假证据方向(黄金法则
    2), 宁可整拍退 L2。类型签名保留 Optional, {} 不再产出。
    """
    warn = warn or logger.warning
    ports_by_pid: Dict[int, set] = {}
    for line in text.splitlines():
        parts = line.split()
        if not parts or parts[0].upper() != "TCP":
            continue
        if len(parts) != 5 or parts[3].upper() != "LISTENING" or not parts[4].isdigit():
            continue
        local_port = parts[1].rsplit(":", 1)[-1]
        if not local_port.isdigit():
            continue
        ports_by_pid.setdefault(int(parts[4]), set()).add(int(local_port))
    if not ports_by_pid:
        warn("netstat 输出无任何 LISTENING 行解析成功, 全机 LISTENING 映射不可用(格式漂移嫌疑)")
        return None
    return {pid: frozenset(ports) for pid, ports in ports_by_pid.items()}


def _listening_map_windows(*, warn: Optional[WarnSink] = None) -> Optional[Dict[int, frozenset]]:
    """Windows: 一次 netstat -ano -p tcp 读取 => 全机 LISTENING 映射(归属与指纹共用底座)。

    子进程钉法(encoding=utf-8 + errors=replace + timeout=10 + CREATE_NO_WINDOW)与单端口
    归属同款(pitfalls/ops/console-encoding.md 的「显式声明不靠 locale」口径: 数据行恒
    ASCII, 表头本地化文本按 UTF-8+replace 解出的乱码不影响解析)。子进程异常(超时/命令
    缺失)向上抛, 由 _listening_map dispatch 兜底。warn 透传解析层(_listening_map_netstat)。"""
    out = subprocess.run(
        ["netstat", "-ano", "-p", "tcp"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=10,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    return _listening_map_netstat(out.stdout or "", **_warn_kw(warn))


def _listening_map_proc(*, warn: Optional[WarnSink] = None) -> Optional[Dict[int, frozenset]]:
    """Linux: /proc/net/tcp(+tcp6 best-effort)st==0A 行端口->inode => /proc/<pid>/fd
    socket 链接归组 => {pid: 监听端口集}。一次表读 + 一次 fd 扫描同时喂端口归属(O1)与
    监听集指纹(§03.2 settle)两个消费面。warn 语义见 _listening_map_netstat。

    证据语义: /proc/net/tcp 不可读 => None(v4 主表缺席时把全体 pid 判成空监听集是假证据
    方向); tcp6 缺失常见(未启用 IPv6), 只当该表无监听(与单端口归属同口径 —— 该畸形下
    IPv6-only 监听不进指纹, 但「绑我们端口」的方向另有端口证与归属通道兜底)。fd 目录打
    不开(权限/进程消失)的 pid 无从归组, 不进映射(跨用户 fd 不可见形态的已知边界: 该
    形态下 owner 归属同样不可得, L1 无 owner 记录不会开窗)。零条 LISTENING 行解析成功
    (表全不可读之外, 行在而 st 全非 0A/列制全不合)=> None + warning(T2 评审按 §07 R2
    「解析不出就退」收紧: 真实 Linux 机器恒有监听套接字, 零解析成功 = 格式漂移嫌疑);
    {} 仅在 fd 全不可见角落可产出(LISTENING 行解析成功而 fd 扫描零归组 —— 全体监听者
    跨用户/权限不可见的跨用户边界, 行为安全)。"""
    warn = warn or logger.warning
    inode_port: Dict[int, int] = {}
    for i, table in enumerate(("/proc/net/tcp", "/proc/net/tcp6")):
        try:
            with open(table, "r", encoding="utf-8") as f:
                rows = f.read().splitlines()[1:]  # 首行表头
        except OSError:
            if i == 0:
                warn("/proc/net/tcp 不可读, 全机 LISTENING 映射不可用")
                return None
            continue  # tcp6 缺失常见: 只当该表无监听
        for row in rows:
            cols = row.split()
            # 列制: sl local rem st ... inode(第 10 列); 列数不足/st 非 0A(LISTENING)/解析失败跳过
            if len(cols) < 10 or cols[3].upper() != "0A":
                continue
            local = cols[1].rsplit(":", 1)
            try:
                inode_port[int(cols[9])] = int(local[1], 16)
            except ValueError:
                continue
    if not inode_port:
        warn("/proc/net/tcp{,6} 无任何 LISTENING 行解析成功, 全机 LISTENING 映射不可用(格式漂移嫌疑)")
        return None
    pids_ports: Dict[int, set] = {}
    for pid in os.listdir("/proc"):
        if not pid.isdigit():
            continue
        try:
            fds = os.listdir(f"/proc/{pid}/fd")
        except OSError:
            continue  # 权限/已消失: 无从归组, 跳过
        for fd in fds:
            try:
                m = _SOCKET_LINK_RE.match(os.readlink(f"/proc/{pid}/fd/{fd}"))
            except OSError:
                continue
            port = inode_port.get(int(m.group(1))) if m else None
            if port is not None:
                pids_ports.setdefault(int(pid), set()).add(port)
    return {pid: frozenset(ports) for pid, ports in pids_ports.items()}


def _listening_map(*, warn: Optional[WarnSink] = None) -> Optional[Dict[int, frozenset]]:
    """全机 LISTENING 映射单点 dispatch(O3; 与 _qb_process_names 同款平台分叉)。O1 端口
    归属与 §03.2 监听集指纹的共用底座 —— W2a 接线每 poll 至多调用一次, 两个消费面都从
    这一份派生, 不重复起子进程(计划 §07 R1 预算「3 个左右」)。warn 语义见
    _listening_map_netstat(接线面传节流绑定: 持续故障每实例每类 1/60s)。证据语义: None =
    本拍观测不可用(通道异常/解析不出/零条 LISTENING 解析成功的格式漂移嫌疑, T2 评审收紧),
    调用方退 L2 全机口径, 且未决成员本拍不得 settle 吸收; {} 仅 Linux 支的 fd 全不可见角落
    可产出(LISTENING 行解析成功而 fd 扫描零归组, 跨用户边界, 行为安全)—— {} 与 None
    在 tick 的分叉承载语义(settle 走不走), 维护者勿当 {} 不可达。"""
    try:
        if os.name == "nt":
            return _listening_map_windows(**_warn_kw(warn))
        return _listening_map_proc(**_warn_kw(warn))
    except Exception:  # noqa: BLE001 - 解析不出: 保守(观测不可用, 不产假证据)
        (warn or logger.warning)("全机 LISTENING 映射通道异常, 本拍观测不可用", exc_info=True)
        return None


def _owner_pid_from_map(listen_map: Dict[int, frozenset],
                        port: int,
                        *,
                        warn: Optional[WarnSink] = None) -> Optional[int]:
    """从全机 LISTENING 映射派生端口归属(判据与单端口归属同款: 同端口多 pid 归属不唯一
    => None + warning, 不猜)。warn 语义见 _listening_map_netstat。"""
    warn = warn or logger.warning
    pids = {pid for pid, ports in listen_map.items() if int(port) in ports}
    if len(pids) > 1:
        warn("端口 %s 的 LISTENING 归属不唯一(%s), 不猜归属", port, sorted(pids))
        return None
    return next(iter(pids)) if pids else None


def _owner_pid_from_netstat(port: int, *, warn: Optional[WarnSink] = None) -> Optional[int]:
    """Windows: netstat -ano -p tcp 的 LISTENING 行归属目标端口 => owner pid | None

    W1b 起内部经 _listening_map_windows 的全机映射派生(与监听集指纹共用一次 netstat
    读取)。返回值判据与 W1a 直读一致(解析不出/归属不唯一 => None 不猜); 唯一新增可观测
    面(T2 评审声明): 输出零条 LISTENING 解析成功时映射侧多一条「格式漂移嫌疑」warning
    (健康标记收紧)。行解析/容错口径见 _listening_map_netstat; 通道异常向上抛(由
    _listening_owner_pid 兜底)。warn 透传映射层。"""
    listen_map = _listening_map_windows(**_warn_kw(warn))
    if listen_map is None:
        return None
    return _owner_pid_from_map(listen_map, port, **_warn_kw(warn))


def _owner_pid_from_procnet(port: int, *, warn: Optional[WarnSink] = None) -> Optional[int]:
    """Linux: /proc/net/tcp{,6}(st==0A)端口 => socket inode => /proc/<pid>/fd 归属
    => owner pid | None。W1b 起内部经 _listening_map_proc 的全机映射派生(与监听集指纹
    共用一次表读 + fd 扫描)。与 W1a 直读实现的两处可观测偏差(T2 评审声明, 返回值判据
    不变): 偏差一 —— 归属不唯一的警告文本统一为「端口 %s 的 LISTENING 归属不唯一」
    (旧文本为「/proc socket 归属不唯一」); 偏差二 —— /proc/net/tcp 主表不可读 => 判
    通道不可用 None(旧实现跳过续读 tcp6 —— 该角落实际不可达, 且指纹面要求保守读法)。
    归属不唯一 => None + warning(不猜); 其余异常向上抛(由 _listening_owner_pid 兜底)。
    warn 透传映射层。"""
    listen_map = _listening_map_proc(**_warn_kw(warn))
    if listen_map is None:
        return None
    return _owner_pid_from_map(listen_map, port, **_warn_kw(warn))


def _listening_owner_pid(
    port: int, listen_map: Optional[Dict[int, frozenset]] = None, *, warn: Optional[WarnSink] = None
) -> Optional[int]:
    """LISTENING 归属分派(O1 前半; 单点 dispatch, 与 _qb_process_names 同款平台分叉)。

    listen_map 传入(W2a 每 poll 共用的那份全机映射)时不另起子进程, 直接从映射派生 ——
    归属与监听集指纹一次读取喂两个消费面(计划 §07 R1 预算); 缺省(None)按旧路径自取。
    warn 语义见 _listening_map_netstat。

    证据语义: 返回 None = 观测不可用(端口无监听行/归属不唯一/通道异常), 调用方必须退回
    L2 全机口径, 绝不当 owner 死证用。O1 只在端口可达时调用(计划 §03.1)—— 可达而无
    监听行本身就是通道异常, 一律 warning 留痕。
    """
    _own = warn or logger.warning  # 自身告警的 sink; 下沉用 _warn_kw(warn) 保缺省路径字节级不变
    try:
        if listen_map is not None:
            owner = _owner_pid_from_map(listen_map, port, **_warn_kw(warn))
        else:
            owner = (
                _owner_pid_from_netstat(port, **_warn_kw(warn))
                if os.name == "nt" else _owner_pid_from_procnet(port, **_warn_kw(warn))
            )
    except Exception:  # noqa: BLE001 - 归属不出: 保守(观测不可用, 不产假证据)
        _own("端口 %s LISTENING 归属通道异常, 本拍观测不可用", port, exc_info=True)
        return None
    if owner is None:
        _own("端口 %s LISTENING 未归属成功(无监听行或归属不唯一), 本拍 owner 观测不可用", port)
    return owner


def _qb_processes_from_powershell(*, warn: Optional[WarnSink] = None) -> Optional[Dict[int, dict]]:
    """Windows: 单次 PowerShell 批量枚举全机 qB 进程(O2)=> {pid: {name, ct}} | None

    warn: 告警 sink(缺省 logger.warning 直落; 接线面传节流绑定 —— 持续故障下逐条剔除与
    缺标记告警同属一类, 每(实例, 类)1/60s, T3 评审 A1)。

    证据语义: 返回 None = 观测不可用, 调用方必须退回 L2 全机口径; {} = 通道健康且全机无
    qB 进程(有效观测)。{} 与 None 的分界 = 健康标记行(_PS_QB_SCRIPT 里管线+标记整体包
    try): Where-Object 零匹配走正常空管线 ⇒ 标记在 ⇒ {}(健康零观测); 任何终止型失败
    (语句终止/script 终止/输出截断/启动失败)⇒ 标记不在 ⇒ None —— 命令级真失败与健康
    零观测在解析侧不可混。**部分清单不冒充全量**: 任何条目身份不完整(StartTime 不可读
    等)或出现形制外的行, 聚合整体判不可用 —— 新面孔状态机拿不完整的 (pid, ct) 集会把
    在跑的 qB 当「不存在」, 那是假证据方向, 宁可整拍退 L2(黄金法则 2; 被剔除条目已逐条
    warning 留痕, per-process 容错在剔除这一层, 计划 §03.1)。
    """
    warn = warn or logger.warning
    out = subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-Command", _PS_QB_SCRIPT],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=10,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    procs: Dict[int, dict] = {}
    dropped = 0
    healthy = False
    for line in (out.stdout or "").splitlines():
        line = line.strip()
        if not line:
            continue
        if line == _PS_QB_END_MARK:
            healthy = True
            continue
        parts = line.split("|")
        if len(parts) != 3:
            dropped += 1
            warn("PowerShell qB 枚举输出行形制异常(%r), 该条目剔除", line[:80])
            continue
        pid, name, ft = (p.strip() for p in parts)
        if not pid.isdigit() or not name:
            dropped += 1
            warn("PowerShell qB 枚举条目 pid/映像名异常(%r), 该条目剔除", line[:80])
            continue
        if not ft.isdigit():
            dropped += 1
            warn("qB 进程 pid=%s 的 StartTime 不可读, 该条目剔除(部分清单不冒充全量)", pid)
            continue
        procs[int(pid)] = {"name": name.lower(), "ct": _filetime_to_epoch(int(ft))}
    if not healthy:
        warn("PowerShell qB 枚举输出缺健康标记(%s), 本拍观测不可用", _PS_QB_END_MARK)
        return None
    if dropped:
        return None
    return procs


def _qb_processes_from_proc(*, warn: Optional[WarnSink] = None) -> Optional[Dict[int, dict]]:
    """Linux: /proc/*/comm 含 qbittorrent + /proc/<pid>/stat starttime 换算 epoch 秒(O2)
    => {pid: {name, ct}} | None。create_time = /proc/stat btime + starttime/SC_CLK_TCK。
    warn 语义见 _qb_processes_from_powershell。逐项容错分两向: comm/stat 读时进程已消失
    (FileNotFoundError)= 死进程无威胁, 条目整体忽略不算枚举不完整; 其余 OSError/解析失败
    = 身份不可得, 条目剔除且**聚合判不可用**(部分清单不冒充全量, 与 PowerShell 支同口径)。"""
    warn = warn or logger.warning
    try:
        with open("/proc/stat", "r", encoding="utf-8") as f:
            btime = next(int(cols[1]) for cols in (ln.split() for ln in f) if cols and cols[0] == "btime")
        hz = os.sysconf("SC_CLK_TCK")
    except (OSError, StopIteration, ValueError, IndexError, AttributeError) as e:
        # AttributeError = 本平台无 os.sysconf(Windows): 与 /proc 缺失同按「枚举不可用」保守
        warn("/proc/stat btime 或 SC_CLK_TCK 不可得(%s), 全机 qB 枚举不可用", e)
        return None
    if hz <= 0:
        warn("SC_CLK_TCK 非法(%s), 全机 qB 枚举不可用", hz)
        return None
    procs: Dict[int, dict] = {}
    dropped = 0
    for pid in os.listdir("/proc"):
        if not pid.isdigit():
            continue
        try:
            with open(f"/proc/{pid}/comm", "r", encoding="utf-8") as f:
                name = f.read().strip().lower()
        except FileNotFoundError:
            continue  # 进程刚退出: 死进程无威胁, 条目整体忽略
        except OSError:
            dropped += 1
            warn("pid=%s 的 comm 不可读, 该条目剔除(部分清单不冒充全量)", pid)
            continue
        if "qbittorrent" not in name:
            continue
        try:
            with open(f"/proc/{pid}/stat", "r", encoding="utf-8") as f:
                # comm 字段可含空格/括号: 按最后一个 ')' 切尾, starttime(字段 22)在尾段
                # 第 19 个(字段 3 起计), 见 proc(5)
                tail = f.read().rsplit(")", 1)[1].split()
            starttime = int(tail[19])
        except FileNotFoundError:
            continue  # 进程刚退出: 同上, 条目整体忽略
        except (OSError, IndexError, ValueError) as e:
            dropped += 1
            warn("pid=%s 的 starttime 不可得(%s), 该条目剔除(部分清单不冒充全量)", pid, e)
            continue
        procs[int(pid)] = {"name": name, "ct": btime + starttime / hz}
    if dropped:
        return None
    return procs


def _qb_processes(*, warn: Optional[WarnSink] = None) -> Optional[Dict[int, dict]]:
    """全机 qB 进程身份枚举(O2; 单点 dispatch, 与 _qb_process_names 同款平台分叉与容错)。

    warn 语义见 _qb_processes_from_powershell(接线面传节流绑定: 持续故障每实例每类 1/60s)。
    证据语义: 返回 None = 观测不可用(通道异常/枚举不完整), 调用方必须退回 L2 全机口径;
    {} = 通道健康且全机无 qB 进程(有效观测, 名册空的强证)。每 poll 至多取一次并与
    _observe_owner 共用(单次 PowerShell 调用面, 计划 §03.1)。
    """
    try:
        if os.name == "nt":
            return _qb_processes_from_powershell(**_warn_kw(warn))
        return _qb_processes_from_proc(**_warn_kw(warn))
    except Exception:  # noqa: BLE001 - 枚举不出: 保守(观测不可用, 不产假证据)
        (warn or logger.warning)("全机 qB 身份枚举通道异常, 本拍观测不可用", exc_info=True)
        return None


def _observe_owner(
    port: int,
    qb_processes: Optional[Dict[int, dict]],
    now: float,
    listen_map: Optional[Dict[int, frozenset]] = None,
    *,
    warn: Optional[WarnSink] = None,
    owner_warn: Optional[WarnSink] = None
) -> Optional[dict]:
    """O1: 端口 LISTENING 归属 + qB 映像名交叉校验 => owner 记录 {pid, ct, ts} | None

    前后两半(计划 §03.1): 归属 pid 的映像名必须含 qbittorrent(大小写不敏感)才记录 ——
    非 qB 服务占端口的保守面(不记录, 绝不把别人的监听当 owner 证据)。listen_map 传入
    (W2a 每 poll 共用的那份全机映射)时不另起子进程, 归属从映射派生; 缺省按旧路径自取。
    warn 语义见 _listening_map_netstat(归属层告警 —— 归属不唯一/未归属成功/通道异常, 接线
    面绑 'obs_listen' 类下沉); owner_warn = 占用者告警 sink(占用者非 qB 名册成员, 接线面
    绑 'obs_owner' 类)—— 两类各自独立 60s 节流互不顶掉(评审轮 2 N1: 归属告警与占用者
    告警共键会在 60s 内互相顶掉); owner_warn 缺省随 warn(单 sink 直调形态与原形等价)。
    证据语义: 返回 None = 本拍未取得 owner 记录(观测通道不可用/端口无监听行/占用者非 qB/
    身份不完整), 调用方一律退回 L2 全机口径, 绝不当 owner 死证用。qb_processes 传 None
    (枚举通道故障)=> 直接 None —— 交叉校验没有名册就没有证据。
    """
    _own = owner_warn or warn or logger.warning  # 占用者告警 sink(缺省随 warn); 归属层下沉用 _warn_kw(warn) 保缺省路径字节级不变
    if qb_processes is None:
        return None
    pid = _listening_owner_pid(port, listen_map, **_warn_kw(warn))
    if pid is None:
        return None
    ident = qb_processes.get(pid)
    if ident is None or "qbittorrent" not in str(ident.get("name") or "").lower():
        _own("端口 %s 的 LISTENING 归属 pid=%s 非全机 qB 名册成员, 不记录 owner(非 qB 服务占端口的保守面)", port, pid)
        return None
    return {"pid": pid, "ct": float(ident["ct"]), "ts": float(now)}


# ---------------------------------------------------------------- 实例级判据面(计划 26-11-10-0318 §03.2/§03.3, W1b)
# 消费上方观测通道的纯逻辑状态机: owner 记录维护 + 新面孔四行转移 + L1 进窗判据 + obs 载荷
# 出入。纯逻辑铁律: 时钟显式注入、零 I/O —— 每拍观测(名册/owner 候选/监听集指纹)由 tick
# 参数喂入(接线单点 _observe_poll, W2a), 本类不读文件、不起子进程、不落盘(落盘时机已由
# 接线面承接: tick 返回 True = 持久面变更 => write_obs(to_payload(now)), §03.4「状态变更
# 即写」)。

# §03.2 未决 settle 界。有界赌注(§07 R3): qB WebUI 监听绑定是启动早期动作(秒级), 30s
# 不绑即非目标 profile —— 30s 为 10 倍量级余量; 独立常量可调, 数值依据见计划 §07 R3 与
# pitfalls P7 专档(W3 立)。
NEW_FACE_SETTLE = 30.0


def _roster_ct(ident: dict) -> Optional[float]:
    """名册条目(_qb_processes 契约形 {name, ct})的 create_time 读取; 读不出 => None,
    调用方按「身份不完整」保守处置(不开安全口子)。"""
    try:
        return float(ident["ct"])
    except (KeyError, TypeError, ValueError):
        return None


class _Observation:
    """实例级观测状态机(§03.2/§03.3): owner 死证维护 + 新面孔无害化 + L1 进窗判据持有者。

    证据语义: owner 记录 = 最后一次确认「绑我们 host:port 的 qB 实例」({pid, ct, ts},
    ts = 最后存活时刻); owner 死后出现的 qB 进程分不清「目标 profile 新身」还是「别的
    实例新身」, 但目标 profile 的实例终将监听我们的端口, 别的不会 —— 四行转移按此收敛
    (见 tick)。场景 X 论证(目标重启间隙立即进窗的安全性根基, 拍板 D2)见计划 §03.3
    callout: 新身完全未起时落盘无 qB 运行、无竞争; 「已创建未绑端口」的尾部由未决态挡住。

    字段分两面(§03.2 hint):
    - 持久面 owner/absorbed: 对齐 obs schema, 经 to_payload/from_payload 出入 obs 文件,
      daemon 重启后恢复 —— 覆盖「daemon 停机期间目标死亡」的判定(记录仍是有效死证)。
      owner 死亡时记录保留(它就是死证), 只有复活/换身才覆盖;
    - 内存面 pending(pid -> {ct, first_seen, fp}): 未决成员的 settle 计时与监听集指纹,
      重启即弃 —— settle 重算, 代价 NEW_FACE_SETTLE(计划明钉), 换来不把跨重启的观察间隙
      当「稳定」证据; 名册条目 ct 读不出的面同样停在未决(真挡, 不参与 settle)。

    tick 契约(W2a 每 poll 接线, 单点 _observe_poll):
        changed = obs.tick(roster, owner_cand, listen_map, now)
      roster      _qb_processes() 结果; None = 名册通道不可用 => 本拍整拍不可判, 状态机
                  不动(也不清 absorbed —— 不能把「看不见」当「消失」), 恒返回 False;
      owner_cand  端口可达(非拒连)时 _observe_owner(port, roster, now, listen_map) 的
                  结果, 拒连时恒传 None; None = 本拍无人绑我们端口或归属不可得;
      listen_map  _listening_map() 结果, 每 poll 至多取一次(归属与指纹共用); None =
                  指纹通道不可用 => 本拍不得 settle 吸收(未决成员计时重置, 继续挡窗);
      返回 True   持久面变更(owner 建档/换身/吸收/清出)=> 调用方应 write_obs 落盘;
                  owner 在位续证的 ts 刷新只在内存、不单独触发落盘(§03.4 写时机 = 变更即写,
                  频率低; 同拍有其它变更时随 to_payload 一并落盘 —— 非隔离快照, T3 评审 B1)。

    判据契约(W2a 每 poll, 与 tick 同一份 roster):
        verdict = obs.l1_open(roster, refused)
      True    L1 证据链齐(owner 死 + 端口拒连 + 无未决)=> 立即进窗, 无稳定期(拍板 D2);
      False   不成立(含无 owner 记录 => L1 不适用, 调用方退 L2);
      None    roster 为 None, 本拍不可判 —— 与「不成立」可区分, 调用方退 L2 并留痕。

    复验专用读(W2a 编排方裁决, 纯分类不转移):
        faces = obs.unclassified_faces(roster)
      现读名册里状态机此刻不能出具「无害」结论的面(pid 升序)—— 窗内复验除 l1_open True
      外还须 faces 为空才算通过(消费单点 _l1_window_open), 见方法 docstring。
    """
    def __init__(self, host: str, port: int):
        self.host = str(host)
        self.port = int(port)
        self.owner: Optional[dict] = None  # {pid, ct, ts}: 持久面
        self.absorbed: list = []  # [{pid, ct, ts}]: 持久面
        self.pending: Dict[int, dict] = {
        }  # pid -> {ct, first_seen, fp}: 内存面(settle 计时; ct=None = 身份读不出的真挡面, 不参与 settle)

    def _owner_self(self, pid: int, ct: Optional[float]) -> bool:
        """(pid, ct) 是否 owner 记录本尊(身份谓词单点: tick 逐面分类与 unclassified_faces
        共用, 消逐字复制 —— T3 评审 B6; 比较口径与 tick 原形一致: pid 按记录 pid 比,
        ct 为 None 恒不等)。"""
        return self.owner is not None and int(pid) == int(self.owner["pid"]) and ct == float(self.owner["ct"])

    def _absorbed_hit(self, pid: int, ct: Optional[float]) -> bool:
        """(pid, ct) 是否命中 absorbed 条目(身份谓词单点: 同上两消费面共用; ct 为 None 恒
        不命中 —— absorbed 写侧只收有效 ct, 无身份不出具吸收结论)。"""
        return any(int(e["pid"]) == pid and float(e["ct"]) == ct for e in self.absorbed)

    def tick(
        self,
        roster: Optional[Dict[int, dict]],
        owner_cand: Optional[dict],
        listen_map: Optional[Dict[int, frozenset]],
        now: float,
    ) -> bool:
        """喂一拍观测并推进 §03.2 四行转移; 返回持久面是否变更(落盘时机见类 docstring)。

        行一阈值(同域, T2 评审 major 修正): 零赌注吸收只认 ct < owner.ct —— ct 与
        owner.ct 同为 OS create_time 域, 同域比较消钟差(旧实现比 owner.ts 属混域比,
        时钟步进/回拨可把目标新身误判 ct<ts 即时吸收、旁路未决挡窗, N1 暴露)。ct 落在
        [owner.ct, ts_last) 的 gap 带改走未决 settle 管道(30s 指纹稳定后吸收, 场景 Y
        代价 ~33s 计划已定价, 方向只会更保守、从不开安全口子); ct >= ts_last 原新面孔
        逻辑不变。已知残余: 时钟回拨跨越 owner 创建边界的角落(回拨后新身 ct 落到
        owner.ct 之前被即时吸收)—— 外部观测原理上堵不死, 记 W3b pitfalls P7 专档与
        计划 §03.2 行一加固注记(编排方收口)。
        行序取舍: 行二(绑端口转 owner)先于行一判 —— 绑我们端口是目标实例唯一外部可验证
        的身份信号; 即时吸收阈值锚在 owner.ct, 行二的 ts 刷新不移动它, gap 面在两序下
        都走 settle(最终一致, 测试钉死)。「ct < owner.ct 却绑着端口」只剩关锁双开角落
        (§07 R4), 该角落里端口证本就挡窗, 按 owner 记账两向都不开安全口子。行一(零赌注
        吸收)不需要指纹通道(listen_map=None 照常生效); 行三(settle 吸收)必须有指纹证据,
        通道不可用一律退回未决; 名册条目 ct 读不出的面进未决真挡(无有效 ct 写不进合法
        absorbed 条目, 绝不自动吸收)。
        """
        if roster is None:
            return False  # 名册不可用: 整拍不可判, 不动持久面(不把「看不见」当「消失」)
        now = float(now)
        changed = False
        # 行二: 绑我们端口的 qB 就是 owner(复活/换身/在位续证)
        if owner_cand is not None:
            cand_pid = int(owner_cand["pid"])
            cand_ct = float(owner_cand["ct"])
            cur = self.owner
            if cur is None or int(cur["pid"]) != cand_pid or float(cur["ct"]) != cand_ct:
                self.owner = {"pid": cand_pid, "ct": cand_ct, "ts": now}  # 建档/复活/换身: 覆盖旧记录
                changed = True
                self.pending.pop(cand_pid, None)  # 升格 owner: 未决出队
                if any(int(e["pid"]) == cand_pid for e in self.absorbed):
                    self.absorbed = [e for e in self.absorbed if int(e["pid"]) != cand_pid]
                    changed = True  # 绑回端口: 它是 owner, 出 absorbed
            else:
                cur["ts"] = now  # 在位续证: 只刷内存 ts, 不单独触发落盘(§03.4 写时机 = 变更即写; 同拍有其它变更时随 to_payload 一并落盘, 非隔离快照)
        # 消失清出(先清后分类): (pid, ct) 不在名册 = 旧进程已死 —— 死进程无威胁, absorbed
        # 清出(文件不膨胀)/未决出队; pid 在而 ct 不等 = PID 被复用, 旧条目同样清出, 新面孔
        # 按下一循环重走分类; 名册条目身份读不出时不当消失(保守)。
        kept = []
        for e in self.absorbed:
            ident = roster.get(int(e["pid"]))
            ct = _roster_ct(ident) if ident is not None else None
            if ident is not None and (ct is None or ct == float(e["ct"])):
                kept.append(e)  # 同进程仍在
            else:
                changed = True  # 消失/PID 复用: 旧进程已死, 清出
        self.absorbed = kept
        for p, pst in list(self.pending.items()):
            ident = roster.get(p)
            if ident is None:
                del self.pending[p]  # 消失: 出队(重现按新面孔重算)
            else:
                ct = _roster_ct(ident)
                if ct is not None and ct != pst["ct"]:
                    del self.pending[p]  # PID 复用: 旧未决出队
        # 逐面分类(四行的行一/行三/行四; 行二已在上面处理)
        owner_pid = int(self.owner["pid"]) if self.owner else None
        owner_ct = float(self.owner["ct"]) if self.owner else None
        for pid, ident in roster.items():
            ct = _roster_ct(ident)
            if self._owner_self(pid, ct):
                continue  # owner 本尊在位
            if ct is None:
                # 名册条目身份读不出: 进未决真挡 —— 无有效 ct 写不进合法 absorbed 条目,
                # 绝不自动 settle 吸收, 直到从名册消失或绑端口转 owner(喂入面防御; 契约上
                # _qb_processes 不产这种条目)
                if pid not in self.pending:
                    self.pending[pid] = {"ct": None, "first_seen": now, "fp": None}
                continue
            if self._absorbed_hit(pid, ct):
                continue  # 已吸收(同 pid 同 ct): 留到消失清出
            if owner_ct is not None and ct < owner_ct:
                # 行一: 零赌注吸收(同域阈值: ct 与 owner.ct 同为 OS create_time 域, 混域比
                # owner.ts 已废 —— 时钟步进/回拨可把目标新身误判即时吸收旁路未决挡窗)。该面
                # 证得早于 owner 实例本身存在, 若同 profile 与 owner 双开被单实例锁/WebUI
                # 端口冲突排挤(§03.2; 用户关锁双开属 §07 R4 原理性残余)
                self.absorbed.append({"pid": int(pid), "ct": ct, "ts": now})
                self.pending.pop(pid, None)
                changed = True
                continue
            # gap 带 [owner.ct, ts_last) 与 ct >= ts_last 同走未决 settle 管道(行三/行四):
            # 前者旧实现被混域零赌注即时吸收, 现改 30s 指纹稳定后吸收(更保守); 绑我们端口
            # 的面已在行二升格(或尚无 owner 记录)
            fp = listen_map.get(int(pid), frozenset()) if listen_map is not None else None
            st = self.pending.get(pid)
            if st is None or st["ct"] != ct:
                self.pending[pid] = {"ct": ct, "first_seen": now, "fp": fp}  # 新未决
                continue
            if fp is None or fp != st["fp"]:
                st["first_seen"] = now  # 指纹通道不可用/指纹变了: settle 重算(不把观察间隙当稳定)
                st["fp"] = fp
                continue
            if now - st["first_seen"] < NEW_FACE_SETTLE:
                continue  # 行四: 未决(挡窗), 直到转 owner/被吸收/消失
            if self.port in fp:
                continue  # 指纹含我们端口: 绑定证据已在, 不 settle(行二未命中 = 归属没跟上, 保守挡)
            # 行三: 指纹稳定 NEW_FACE_SETTLE 且不含我们端口 => 吸收(§07 R3 有界赌注)
            del self.pending[pid]
            self.absorbed.append({"pid": int(pid), "ct": ct, "ts": now})
            changed = True
        return changed

    def l1_open(self, roster: Optional[Dict[int, dict]], refused: bool) -> Optional[bool]:
        """L1 进窗判据(计划 §03.3 精确语义; 纯读, 不动状态)。

        进窗(L1) ⇔ 1. owner 记录存在且 owner 已死 —— pid 无进程 / pid 在但 create_time
        不等 / pid 在但映像名非 qbittorrent(后两条 = PID 复用防御: 被别的程序/别的 qB
        实例复用都判「原实例已死」); 2. 端口拒连(_port_refused 原样); 3. 无未决成员
        (§03.2)。三者同时成立 ⇒ 立即进窗, 无 down_since 计时(拍板 D2)。

        返回: True = 进窗; False = 不成立(含无 owner 记录 —— L1 不适用, 调用方退 L2);
        None = roster 为 None(名册通道不可用), 本拍不可判 —— 与「不成立」可区分, 调用方
        退 L2 并按通道故障留痕(W2a 接线面职责)。名册条目身份不完整 = 无法证明死亡 =>
        按不成立(开窗是危险方向, 死证必须证得, 不许默认)。
        """
        if roster is None:
            return None
        if self.owner is None or not self._owner_dead(roster):
            return False
        if not refused or self.pending:
            return False
        return True

    def _owner_dead(self, roster: Dict[int, dict]) -> bool:
        """owner 死证三形态(§03.3)。形态三对 _qb_processes 名册结构性不可达(名册只收
        映像名含 qbittorrent 的进程), 保留为判据完整性/PID 复用防御(直接喂非过滤名册时
        生效)。"""
        o = self.owner or {}
        ident = roster.get(int(o.get("pid") or 0))
        if ident is None:
            return True  # 形态一: pid 无进程
        ct = _roster_ct(ident)
        if ct is None:
            return False  # 身份不完整: 无法证明死亡(保守)
        if ct != float(o.get("ct") or 0.0):
            return True  # 形态二: ct 不等(PID 复用 => 原实例已死)
        if "qbittorrent" not in str(ident.get("name") or "").lower():
            return True  # 形态三: 映像名非 qB(PID 被别的程序复用)
        return False

    def unclassified_faces(self, roster: Dict[int, dict]) -> list:
        """纯分类读(§03.3 复验第 3 条件「现判」化的单点, W2a 编排方裁决): 对现读名册逐面
        分类, 返回状态机**此刻**不能出具「无害」结论的未分类面 pid 清单(升序)。

        分类口径 = tick 四行转移的只读镜像(不代行转移 —— 建档/吸收是 tick 的写权, 复验只读):
        - owner 记录身份命中(pid 与 ct 均等)⇒ owner 本尊在位: l1_open 条件 1 本就不过, 等价挡;
        - absorbed 命中(pid 与 ct 均等)⇒ 已吸收(§03.2 无害面), 不挡;
        - pending 命中(pid 在未决集)⇒ 已在未决挡窗: l1_open 条件 3 本就不过, 等价挡;
        - 其余一律未分类 ⇒ 挡 —— 含 ct 读不出的面(身份不完整, 与 tick 缺 ct 面停未决真挡
          同向)、ct < owner.ct 尚未及吸收的新面(tick 会零赌注吸收, 但**此刻**还没吸收,
          状态机不能立即出具无害结论)、owner pid 被复用的面(pid 命中而 ct 不等, 不算
          owner 身份命中)、以及一切全新面。
        语义(裁决原文方向): 「若此刻 tick, 这些面会进未决或触发转移 —— 凡状态机不能立即
        给出『无害』结论的面, 复验不过」。挡是暂态不是死锁: 下一 poll 窗顶 _observe_poll
        的 tick 会把新面正规分类(进未决 → settle → absorbed 或零赌注吸收), 届时清单变空,
        窗可重开 —— 与状态机设计自洽(复验不过仍走现状 qb_back 中止/重试语义, 零新增行为)。
        消费单点 = _l1_window_open(l1_open True 之外还须本清单为空才算复验通过)。
        纯读铁律: 不动 owner/absorbed/pending, 不判端口证(调用方另有 refused), 不需要
        listen_map(指纹只影响 settle 时长, 不影响「是否未分类」), 不起子进程。roster 契约
        同 l1_open: 只收健康名册 dict(None 由调用方的 l1_open None 分支先行处理)。"""
        out = []
        for pid, ident in roster.items():
            ct = _roster_ct(ident)
            if self._owner_self(pid, ct):
                continue  # owner 本尊在位: l1_open 条件 1 挡(等价)
            if self._absorbed_hit(pid, ct):
                continue  # absorbed 命中: 已出具无害结论的面
            if pid in self.pending:
                continue  # 已在未决: l1_open 条件 3 挡(等价)
            out.append(int(pid))
        return sorted(out)

    def to_payload(self, now: float) -> dict:
        """持久面快照 => obs schema 载荷(计划 §03.4: {host, port, owner, absorbed, ts};
        schema_version 由 write_obs 写侧强制钉上, 这里不出)。内存面(pending)不进载荷 ——
        重启即弃, settle 重算(代价 NEW_FACE_SETTLE, 计划明钉)。"""
        return {
            "host": self.host,
            "port": self.port,
            "owner": dict(self.owner) if self.owner else None,
            "absorbed": [dict(e) for e in self.absorbed],
            "ts": float(now),
        }

    @classmethod
    def from_payload(cls, payload: object, host: str, port: int) -> Optional["_Observation"]:
        """obs 载荷 => 状态机实例(daemon 重启恢复面); **坏形整体弃 => 返回 None**(不抛 ——
        与 read_obs 保守语义同款: 半残记录不冒充证据, 调用方按无记录冷启动退 L2)。

        校验走 read_obs 同款严格判型(rj._obs_entry_ok 单点, 不复刻判型防漂移): owner 为
        None 或 {pid, ct, ts} 实记录、absorbed 为其清单(缺键也判废 —— 非本链产物)、host
        为非空 str 且与本实例字面相等、port 为正 int 且相等(obs 文件按实例键分家, 键内
        身份不符 = 跨实例污染, 拒载)。顶层 ts 只入文件不入状态(read_obs 已闸), 不在此校验。
        """
        if not isinstance(payload, dict):
            return None
        h = payload.get("host")
        if not isinstance(h, str) or not h.strip() or h != str(host):
            return None
        p = payload.get("port")
        if isinstance(p, bool) or not isinstance(p, int) or int(p) != int(port):
            return None
        owner = payload.get("owner")
        if owner is not None and not rj._obs_entry_ok(owner):
            return None
        absorbed = payload.get("absorbed")
        if not isinstance(absorbed, list) or not all(rj._obs_entry_ok(e) for e in absorbed):
            return None
        inst = cls(host, port)
        inst.owner = dict(owner) if owner is not None else None
        inst.absorbed = [dict(e) for e in absorbed]
        return inst  # pending 恒空: settle 重算(重启即弃, §03.2 hint)


def _l1_window_open(
    host: str,
    port: int,
    obs: _Observation,
    *,
    warn_flags: Optional[Dict[str, float]] = None,
    now_fn: Optional[Callable[[], float]] = None,
) -> bool:
    """L1 窗的瞬时复验(计划 §03.3 全套现读现判; 编排方裁决补强): 新读全机 qB 身份名册 +
    现测端口拒连, l1_open 纯读判条件 1/2/3, **加 unclassified_faces 现判** —— 条件 3 的
    「无未决」不能只看进窗时的 pending 快照: 现读名册里凡状态机此刻不能立即出具「无害」
    结论的面(owner 身份命中/absorbed 命中/pending 在册之外的都算, 含 ct 读不出与未及吸收
    的新面)一律复验不过 —— 复验粒度与进窗判据同级, 是「立即进窗」(拍板 D2)安全性的必要
    条件。False/None(l1_open 不成立或名册通道不可判)与未分类面非空都算不过 —— 通道故障
    绝不冒充通过(保守向);复验不过由 _process_window 走现状 qb_back 中止语义, 零新增行为;
    新面由下一 poll 窗顶 _observe_poll 的 tick 正规分类(进未决 → settle → absorbed)后清单
    变空, 窗可重开 —— 与状态机设计自洽。名册只现读一次喂两判(l1_open 与分类同一份, 不
    二次起子进程)。与 _window_open(L2/L3 两证)的分派单点在 _process_window(按本窗开启层
    选闸)。

    告警面(评审轮 2 N2): warn_flags(run 持有的节流记账 dict)+ now_fn(注入时钟)成对
    传入时, 复验拍名册通道的告警经 _warn_sink 节流绑定下发、verdict None 补处置留痕 ——
    键空间: 通道告警复用 'obs_roster'(读的是同一条 qB 身份枚举通道, 根因类与主循环
    _observe_poll 相同, 共键后「每实例每类 1 条/60s」覆盖 poll→窗边界, 持续故障不因复验
    加倍刷屏); verdict None 处置留痕用新键 'reverify'(复验不可判直接导致 qb_back 中止
    本轮, 与主循环 verdict None 的「退 L2 继续等」是不同处置事件 —— 若与接线点 'roster'
    键共键会被主循环先前的同根因留痕顶掉, 丢失中止留痕)。两者缺省(None)=> 原形直落
    路径: 通道告警走通道函数族缺省 logger.warning, verdict None 静默返回 False(直接调用
    方/既有测试零感知)。纯读铁律不变: 不写 _Observation、不落盘; warn_flags 是 run 级
    节流记账 dict(非观察状态), 允许写。"""
    throttled = warn_flags is not None and now_fn is not None
    now = float(now_fn()) if throttled else 0.0
    sink = _warn_sink(warn_flags, "obs_roster", now) if throttled else None
    roster = _qb_processes(**_warn_kw(sink))
    verdict = None if roster is None else obs.l1_open(roster, _port_refused(host, port))
    if verdict is None:
        if sink is not None:
            _throttled_warn(
                warn_flags,
                "reverify",
                now,
                "实例 %s:%s L1 复验拍名册通道本拍不可判(qB 身份枚举不可用), 复验不过中止本轮(qb_back)",
                host,
                port,
            )
        return False  # 名册通道不可判(l1_open None)/不成立: 都算不过, 通道故障不冒充通过
    if verdict is not True:
        return False
    return not obs.unclassified_faces(roster)


def _observe_poll(
    data_dir: str,
    key: str,
    obs: _Observation,
    host: str,
    port: int,
    now: float,
    flags: Dict[str, float],
) -> Optional[bool]:
    """每 poll 观测维护(W1b tick 契约的接线单点, 计划 §03.1「每 poll, pending 非空时维护」;
    调用点在 run 主循环且仅当该实例有 pending job —— 空载拍零通道调用, §07 R1 子进程预算
    只花在有活的拍上)。

    数据流(W1b tick 契约): 全机 LISTENING 映射每 poll 至多取一次(归属 + 监听集指纹两消费
    面共用, §07 R1 预算)-> 端口证现测 -> 全机 qB 身份名册现读(None = 通道不可用,
    {} = 健康零观测)-> 端口可达时归属 owner 候选(拒连恒 None)-> tick 推进状态机(返回
    True = 持久面变更 => write_obs 落盘; 写失败节流告警留痕, 内存态继续 —— 重启丢观测退
    L2, 安全向)-> l1_open 纯读出 L1 verdict(与 tick 同一份名册, 不二次起子进程)。

    告警面(T3 评审 A1, §03.1 通道纪律「每(实例, 类)1 条/60s」)两层分工:
    - 通道函数层: 三条通道各传 _warn_sink 节流绑定 —— sink 类键 'obs_listen'(映射/归属
      通道, 格式漂移/归属不唯一/未归属成功)/'obs_roster'(名册枚举, 缺健康标记/剔除/通道
      异常)/'obs_owner'(占用者非 qB 名册成员)。持续故障下通道函数每 poll 的重复告警在
      sink 内被节流; 同类多条(如解析逐行剔除)只首拍落, 根因文本不刷屏;
    - 接线点层: 本函数自身的处置留痕 —— 'obs_write'(落盘失败)/'roster'(verdict None 退
      L2)/'listen'(指纹通道不可用, 未决面本拍不 settle)。与 sink 键空间刻意分开: 同一
      拍通道根因与接线处置各留一条(不同类), 处置文本不被根因文本顶掉。

    返回: True = L1 证据链齐(owner 死 + 端口拒连 + 无未决)⇒ 调用方立即进窗(拍板 D2);
    False = 不成立(含无 owner 记录 => L1 不适用)⇒ 调用方走 L2 现状判据(不告警 —— 正常
    路径); None = 名册通道本拍不可判 ⇒ 调用方退 L2(本函数已节流告警留痕, 每实例每类一条)。
    """
    listen_map = _listening_map(warn=_warn_sink(flags, "obs_listen", now))
    refused = _port_refused(host, port)
    roster = _qb_processes(warn=_warn_sink(flags, "obs_roster", now))
    owner_cand = None if refused else _observe_owner(
        port,
        roster,
        now,
        listen_map=listen_map,
        warn=_warn_sink(flags, "obs_listen", now),  # 归属层告警(归属不唯一/未归属成功/通道异常)
        owner_warn=_warn_sink(flags, "obs_owner", now),  # 占用者非 qB 名册成员
    )
    if listen_map is None:
        _throttled_warn(
            flags,
            "listen",
            now,
            "实例 %s:%s 指纹通道本拍不可用(LISTENING 映射缺席), 未决面本拍不 settle 挡窗",
            host,
            port,
        )
    if obs.tick(roster, owner_cand, listen_map, now):
        if not rj.write_obs(data_dir, key, obs.to_payload(now)):
            _throttled_warn(
                flags,
                "obs_write",
                now,
                "实例 %s:%s 观测账落盘失败, 内存态继续(重启丢观测退 L2, 安全向)",
                host,
                port,
            )
    verdict = obs.l1_open(roster, refused)
    if verdict is None:
        _throttled_warn(
            flags,
            "roster",
            now,
            "实例 %s:%s L1 名册通道本拍不可判(qB 身份枚举不可用), 退 L2 全机口径",
            host,
            port,
        )
    return verdict


class _Owner:
    """daemon.json(pid/ts)的归属与心跳编排(协议原语单点在 relocate_journal, 本类只做
    节流与判定; Windows 残留锁/进程探测的坑都在 _alive 单点里, 此处不重复)。"""
    def __init__(
        self, data_dir: str, key: str, pid: int, host: str = "", port: int = 0, heartbeat: float = HEARTBEAT_INTERVAL
    ):
        self.data_dir = data_dir
        self.key = key
        self.pid = int(pid)
        self.host = str(host or "")
        self.port = int(port or 0)
        self.heartbeat = float(heartbeat)
        self._last_touch: Optional[float] = None

    def claim(self, now: float, max_age: float) -> str:
        """pid 抢占: 现存记录是健康 watcher(心跳未过期且 pid 活, daemon_stale 判据单点)
        ⇒ already_running 让路(至多一个 watcher, D12);否则(无记录/记录 pid 已死/心跳
        过期)落自己的 pid 接管 —— 旧主(若还醒着)在下一次自检看见外来 pid 即退位自杀。
        """
        if not rj.daemon_stale(self.data_dir, self.key, max_age=max_age, now=now):
            return "already_running"
        rj.write_daemon_state(self.data_dir, self.key, self.pid, host=self.host, port=self.port, ts=now)
        self._last_touch = now
        return "claimed"

    def beat(self, now: float) -> bool:
        """每拍归属自检 + 节流心跳 touch; False = 已被退位(记录 pid 非我)⇒ 调用方自杀退出。
        记录缺失(异常消失)⇒ touch 重新落盘认主(daemon 不因账文件消失而白死)。"""
        cur = rj.read_daemon_state(self.data_dir, self.key)
        if cur is not None and int(cur.get("pid") or 0) != self.pid:
            return False
        if self._last_touch is None or now - self._last_touch >= self.heartbeat:
            if not rj.touch_daemon_state(self.data_dir, self.key, self.pid, ts=now):
                return False
            self._last_touch = now
        return True

    def release(self) -> bool:
        return rj.release_daemon_state(self.data_dir, self.key, self.pid)


def _scan_jobs(data_dir: str, host: str, port: int) -> list:
    """扫本实例的待收尾 job(「窗口开头现读 pending 集」与主循环节拍共用的入口)。

    口径: spec 属本实例(host/port 字面相等, 不做 localhost/127.0.0.1 智能匹配)且带
    bt_backup 字段(新链 opt-in; 旧链 spec 无此字段不归本模块); journal 已终态
    (done/cancelled/failed)的 job 跳过 —— 取消/收口/失败终态即时生效(D12)。src/dst
    缺项的残缺 spec 跳过(arm 侧责任, daemon 不猜)。
    返回 [{job_id, spec, pending, flip}]; flip = pending 空 + 改写账非空 + 相位未翻
    (窗口中崩溃错过翻相)⇒ 主循环补翻 rewritten。
    """
    out = []
    for job_id in rj.list_spec_jobs(data_dir):
        spec = rj.read_spec(data_dir, job_id)
        if not isinstance(spec, dict):
            continue
        if str(spec.get("host") or "") != str(host or ""):
            continue
        try:
            spec_port = int(spec.get("port") or 0)
        except (TypeError, ValueError):
            spec_port = 0
        if spec_port != int(port or 0):
            continue
        if not str(spec.get("bt_backup") or "").strip():
            continue
        if not str(spec.get("src") or "").strip() or not str(spec.get("dst") or "").strip():
            continue
        journal = rj.read_journal(data_dir, job_id) or {}
        if str(journal.get("phase") or "") in rj.STOP_PHASES:
            continue
        raw_rewrites = journal.get("rewrites")
        rewrites = raw_rewrites if isinstance(raw_rewrites, dict) else {}
        pending = rj.pending_members(spec, rewrites)
        out.append(
            {
                "job_id": job_id,
                "spec": spec,
                "pending": pending,
                "flip": not pending and bool(rewrites) and str(journal.get("phase") or "") != rj.PHASE_REWRITTEN,
            }
        )
    return out


def _rewrite_member(spec: dict, member: dict, prev: Optional[dict]) -> dict:
    """单成员改写 + 记账构造(纯构造不落账; 落账由调用方走 record_rewrites 单点)。

    记账取舍(already/unmatched 按语义入账, 见 REWRITE_SETTLED):
    - written -> rewritten(双键已落盘, 逐键明细随账)
    - unchanged 且有键 already -> already(已在目标值: 幂等重放证据 —— 出账, 否则重放
      永不收敛, 违反黄金法则 1)
    - unchanged 且纯 unmatched(含无任何路径键) -> unmatched(确定性无操作: 全部路径键
      都不命中旧根; 相对形态键已按 profile base 解析改写(issue 26-11-07-2336), 落到
      unmatched = 解析失败或解析后不命中旧新根 —— 重放无意义; 真错向由主循环重启后
      逐成员 save_path 核验兜住(S4), 账留逐键明细供诊断) —— 出账
    - not_found -> member_gone(R4 配套, 计划 26-11-13-0448 §03 R4): BT_backup 定位不到
      fastresume 按成员已被删等价收口(主源 = E5 实证: qB 5.2.3 删种即删 fastresume,
      仅账面 0.03s / 连文件 0.02s 内消失; 缺失源不可分辨 —— locate 在 BT_backup 目录
      消失/键空时同样返回 None, 成员已删或 BT_backup 部署态漂移, 计划 §07 接受等价
      收口)—— 跳过并按 settled 收口, 不计失败不重试(原 not_found 留账会随窗口无限
      重放, 永不收敛); 成员是否收缩由主循环按 qB 快照缺席判(R4), daemon 不越权改
      job 账
    - FastresumeError/ValueError/OSError -> failed: 不出账, fails 计数承前累计 +1
      (每失败一次进一账), 窗口内随拍重试(D8)、下一窗口重放
    """
    backup = str(spec.get("bt_backup") or "")
    old_root = str(spec.get("src") or "")
    new_root = str(spec.get("dst") or "")
    h1 = str(member.get("hash_v1") or "")
    h2 = str(member.get("hash_v2") or "")
    fails = int((prev or {}).get(rj.REWRITE_FAILS_KEY) or 0)
    try:
        report = fastresume.retarget(backup, h1, h2, old_root, new_root)
    except (fastresume.FastresumeError, ValueError, OSError) as e:
        return {"status": "failed", "error": str(e), rj.REWRITE_FAILS_KEY: fails + 1}
    if report.status == "written":
        return {
            "status": "rewritten",
            "path": report.path or "",
            "keys": list(report.rewritten),
            "already": list(report.already),
            "unmatched": list(report.unmatched),
            rj.REWRITE_FAILS_KEY: fails,
        }
    if report.status == "not_found":
        # R4 配套(计划 26-11-13-0448 §03 R4): fastresume 缺失 = 成员已被删(E5 实证),
        # 跳过并记 settled 收口(不再随窗口无限重放); 不计失败 —— 删种不是改写故障
        return {"status": rj.REWRITE_MEMBER_GONE, rj.REWRITE_FAILS_KEY: fails}
    if report.already:
        return {
            "status": "already",
            "path": report.path or "",
            "keys": list(report.already),
            "unmatched": list(report.unmatched),
            rj.REWRITE_FAILS_KEY: fails,
        }
    return {
        "status": "unmatched",
        "path": report.path or "",
        "keys": [],
        "unmatched": list(report.unmatched),
        rj.REWRITE_FAILS_KEY: fails,
    }


def _process_window(
    data_dir: str,
    jobs: list,
    owner: _Owner,
    host: str,
    port: int,
    *,
    started: float,
    max_wait: float,
    poll: float,
    clock=time.time,
    sleep=time.sleep,
    obs: Optional[_Observation] = None,
    warn_flags: Optional[Dict[str, float]] = None,
    now_fn: Optional[Callable[[], float]] = None,
) -> str:
    """一个下线窗口的改写会话(D8: 每窗口限一轮会话; 窗口内失败重试至成功或 qB 回升)。

    obs(计划 26-11-10-0318 W2a) = 本窗的开启层标记: None = L2/L3 全机口径窗(现状, 复验
    两证原样);传 _Observation = L1 实例级证据窗(拍板 D2 立即进窗的那一档, 复验升级)。

    每拍/每次落盘前的闸门(顺序即成本序):
      1. 归属(beat): 被退位 ⇒ deposed(自杀, 未落盘的成员留给新主/下一窗口);
      2. pending 现读: journal 已终态的 job 剔除(取消/收口即时生效), 已收口成员出账;
      3. 全收口 ⇒ settled(相位翻正交给主循环拍间 scan 的 flip);
      4. 窗口仍开(复验粒度与进窗判据同级, §03.3): L1 窗 = 全套现读现判(_l1_window_open:
         新读名册 + 现测拒连, l1_open 条件 1/2/3 + unclassified_faces 现判 —— 现读名册里
         状态机不能立即出具「无害」结论的新面一律复验不过, 条件 3 不只看进窗时 pending
         快照); L2/L3 窗 = 现状两证(_window_open 原样)—— 任一不过 = qB 有生命迹象/证据链
         不齐 ⇒ 立即放弃本轮(qb_back; N4: 已写成员经别名正常加载, 未写成员 journal 待
         重放; 中止/重试语义与现状一致, 不新增行为)。

    warn_flags/now_fn(评审轮 2 N2): L1 复验闸(_l1_window_open)的节流面透传(run 持有的
    节流记账 dict 与注入时钟; 成对缺省 => 复验告警直落, 直接调用方/既有测试零感知)。
    L2/L3 路径零改动(_window_open 原样, 不接节流)。
    """
    def _still_open() -> bool:
        # 窗口仍开的瞬时复验(W2a): 按本窗开启层选闸 —— L1 全套现读现判(含未分类面现判,
        # 复验拍通道告警经 warn_flags 节流 + verdict None 处置留痕) / L2/L3 两证
        return (
            _l1_window_open(host, port, obs, warn_flags=warn_flags, now_fn=now_fn)
            if obs is not None else _window_open(host, port)
        )

    while True:
        now = clock()
        if not owner.beat(now):
            return "deposed"
        if max_wait and now - started > max_wait:
            return "timeout"
        remaining = []
        for job in jobs:
            journal = rj.read_journal(data_dir, job["job_id"]) or {}
            if str(journal.get("phase") or "") in rj.STOP_PHASES:
                continue
            raw_rewrites = journal.get("rewrites")
            rewrites = raw_rewrites if isinstance(raw_rewrites, dict) else {}
            pend = rj.pending_members(job["spec"], rewrites)
            if pend:
                remaining.append((job, pend))
        if not remaining:
            return "settled"
        if not _still_open():
            return "qb_back"
        for job, pend in remaining:
            job_id = job["job_id"]
            for member in pend:
                now = clock()
                if not owner.beat(now):
                    return "deposed"
                if not _still_open():
                    return "qb_back"
                journal = rj.read_journal(data_dir, job_id) or {}
                if str(journal.get("phase") or "") in rj.STOP_PHASES:
                    break  # 本 job 已收口(取消): 剩余成员全跳
                # 窗口内逐成员现读 spec(评审 #4): supersede 的账面改道(retarget_spec)不需要
                # qB 在线, 可落在本窗口中段 —— 沿用窗口 scan 时的快照会把剩余成员改写到旧
                # dst, 违背本模块 docstring「窗口内逐拍现读续保(supersede 即时生效)」。现读
                # 失败(残缺/并发重写撕态)按 scan 同款容错: 本 job 本拍放弃, 绝不拿旧快照
                # 改写, 留下一拍/下一窗口按新账重放(D8)。
                spec = rj.read_spec(data_dir, job_id)
                if not isinstance(spec, dict):
                    break
                raw_prev = journal.get("rewrites")
                prev = raw_prev if isinstance(raw_prev, dict) else {}
                mkey = rj.member_key(member)
                rec = _rewrite_member(spec, member, prev.get(mkey))
                recorded = rj.record_rewrites(data_dir, job_id, {mkey: rec}, ts=now, pid=owner.pid)
                if recorded and str(rec.get("status") or "") == rj.REWRITE_MEMBER_GONE:
                    # R4 配套留痕(R4 评审轮 1 修 4: 落在 record_rewrites 成功之后 —— 拒写
                    # 路径账里无收口记录, 不得提前宣称「已收口」): fastresume 缺失按
                    # member_gone 等价收口(缺失源不可分辨: 成员已删或 BT_backup 部署态
                    # 漂移, 计划 26-11-13-0448 §07 接受; 主源 = qB 删种即删, E5 实证)
                    # —— 不失败不重试, 收缩判定归主循环(R4)
                    logger.warning(
                        f"recycle_daemon | job {job_id}: 成员 {mkey[:8]} 的 fastresume 已缺失"
                        "(主源: qB 删种即删; 缺失源不可分辨) —— 跳过改写, 已记 member_gone 收口;"
                        "组账收缩由主循环判定"
                    )
                if not recorded:
                    break  # 拒写 = 对账刚收口: 放弃本 job(下拍 scan 剔除)
        sleep(poll)


def run(
    data_dir: str,
    host: str,
    port: int,
    *,
    stable: float = STABLE_WINDOW,
    poll: float = POLL_INTERVAL,
    grace: float = GRACE_EXIT,
    heartbeat: float = HEARTBEAT_INTERVAL,
    max_wait: float = 0.0,
    clock=time.time,
    sleep=time.sleep
) -> str:
    """daemon 主循环; 返回结论(供 CLI 与测试断言)。

    - already_running: 本实例已有健康 watcher(心跳未过期且 pid 活) —— 不重复拉起;
    - idle: pending 集空持续 grace 秒(无事可做/已全收口) ⇒ 宽限退出;
    - deposed: daemon.json 记录 pid 非我(被新主抢占) ⇒ 自检自杀, 绝不恋战;
    - timeout: max_wait 到点(0 = 不限, 窗口内同样生效) —— pending 原样保留, 对账续拉。
    进窗分派(计划 26-11-10-0318 三层): 有 pending 的拍先做观测维护(_observe_poll, §03.1
    每 poll 口径, 空载拍零通道调用)—— L1 verdict True(owner 死证 + 端口拒连 + 无未决
    新面孔)⇒ 立即进窗, 无 down_since 计时(拍板 D2: 强证据不配稳定期); False(L1 不成立,
    含无 owner 记录/owner 在位/证据未齐)/ None(名册通道不可判, _observe_poll 已节流告警)
    ⇒ L2 现状三证判据原样(30s 稳定期保留, 单实例窗口时序不早于接线前 —— 等价面硬要求)。
    收敛不变量: 窗口外零 fastresume 落盘(三层进窗判据 + 每次落盘前同级瞬时复验: L1 窗
    全套现读现判 / L2 窗两证); journal 是唯一账面, 任一退出路径都留一致账态, 下一窗口可
    重放(D8/N4)。
    """
    key = rj.instance_key(host, port)
    owner = _Owner(data_dir, key, os.getpid(), host, port, heartbeat=heartbeat)
    started = clock()
    if owner.claim(clock(), HEARTBEAT_MAX_AGE) == "already_running":
        return "already_running"
    # 实例级观测状态(计划 26-11-10-0318 §03.4): 认领成功即从 obs 文件恢复(前世 daemon 的
    # 归档跨重启有效 —— 覆盖「daemon 停机期间目标死亡」的死证判定);坏形/缺失 => 新建空
    # _Observation, 走 L2 直到目标下次上线建档(D3: 冷启动仅首次部署/清数据形态)。本 daemon
    # 是 obs-<key>.json 的单写者(daemon.json 是归属心跳面, 语义不混)。
    obs = _Observation.from_payload(rj.read_obs(data_dir, key), host, port) or _Observation(host, port)
    warn_flags: Dict[str, float] = {}  # 接线面告警节流(_throttled_warn; 每实例每类一条)
    down_since = 0.0
    grace_since = 0.0
    try:
        while True:
            now = clock()
            if not owner.beat(now):
                return "deposed"
            jobs = _scan_jobs(data_dir, host, port)
            pending_any = False
            for job in jobs:
                if job["pending"]:
                    pending_any = True
                elif job["flip"]:
                    # 全员已收口而相位未翻(窗口中崩溃/错过翻相)⇒ 补翻 rewritten; 拒写 =
                    # 对账已收口(终态), 下拍 scan 自然剔除 —— journal 写不限窗口(D13)
                    rj.record_rewrites(data_dir, job["job_id"], {}, phase=rj.PHASE_REWRITTEN, ts=now, pid=owner.pid)
            if not pending_any:
                if not grace_since:
                    grace_since = now
                elif now - grace_since >= grace:
                    return "idle"
            else:
                grace_since = 0.0
                verdict = _observe_poll(data_dir, key, obs, host, port, now, warn_flags)
                if verdict is True:
                    # L1(计划 §03.3, 拍板 D2): owner 死证 + 端口拒连 + 无未决新面孔 => 证据链
                    # 齐, 立即进窗, 无 down_since 计时(强证据不配稳定期); 窗内复验同级升级
                    # (obs 传入 _process_window, 见其闸门 4: l1_open + unclassified_faces
                    # 现判 —— 进窗判据读的是 tick 后状态, 窗内新面由复验分类读兜住, 未分类
                    # 一律 qb_back, 下一拍 tick 正规分类后窗可重开)
                    outcome = _process_window(
                        data_dir,
                        jobs,
                        owner,
                        host,
                        port,
                        started=started,
                        max_wait=max_wait,
                        poll=poll,
                        clock=clock,
                        sleep=sleep,
                        obs=obs,
                        warn_flags=warn_flags,
                        now_fn=clock,
                    )
                    down_since = 0.0
                    if outcome in ("deposed", "timeout"):
                        return outcome
                    continue  # settled/qb_back: 回主循环重扫(pending 决定续等或宽限退出)
                # L2/L3(现状判据原样): verdict False = L1 不成立(含无 owner 记录/owner 在位/
                # 证据未齐; 全部落入与接线前字节等价的 L2 分支, 不告警)/ None = 名册通道不可判
                # (_observe_poll 已节流告警留痕)—— 本段行为与实例级证据接线前完全等价(等价面硬要求)
                names = _qb_process_names()
                down = _proc_absent(names, host, port) and _port_refused(host, port)
                if down:
                    if not down_since:
                        down_since = now
                    if now - down_since >= stable:
                        outcome = _process_window(
                            data_dir,
                            jobs,
                            owner,
                            host,
                            port,
                            started=started,
                            max_wait=max_wait,
                            poll=poll,
                            clock=clock,
                            sleep=sleep
                        )
                        down_since = 0.0
                        if outcome in ("deposed", "timeout"):
                            return outcome
                        continue  # settled/qb_back: 回主循环重扫(pending 决定续等或宽限退出)
                else:
                    down_since = 0.0
            if max_wait and now - started > max_wait:
                return "timeout"
            sleep(poll)
    finally:
        owner.release()


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="fastresume 收尾回收 daemon(等 qB 下线窗口批量改写)")
    ap.add_argument("--data-dir", required=True, help="运行时数据目录(与 config.data_dir 同源)")
    ap.add_argument("--host", required=True, help="qB 实例 host(与 spec/journal 字面相等判定)")
    ap.add_argument("--port", type=int, required=True, help="qB 实例 port")
    ap.add_argument("--stable", type=float, default=STABLE_WINDOW)
    ap.add_argument("--poll", type=float, default=POLL_INTERVAL)
    ap.add_argument("--grace", type=float, default=GRACE_EXIT)
    ap.add_argument("--heartbeat", type=float, default=HEARTBEAT_INTERVAL)
    ap.add_argument("--max-wait", type=float, default=0.0, help="最长运行秒数(0 = 不限)")
    args = ap.parse_args(argv)
    result = run(
        args.data_dir,
        args.host,
        args.port,
        stable=args.stable,
        poll=args.poll,
        grace=args.grace,
        heartbeat=args.heartbeat,
        max_wait=args.max_wait,
    )
    key = rj.instance_key(args.host, args.port)
    print(
        f"recycle_daemon: instance {args.host}:{args.port} -> {result}"
        f"(daemon.json: {rj.daemon_state_path(args.data_dir, key)})"
    )
    return 0 if result in ("idle", "deposed", "already_running") else 1


if __name__ == "__main__":
    sys.exit(main())
