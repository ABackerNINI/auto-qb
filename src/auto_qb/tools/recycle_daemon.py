"""recycle_daemon: fastresume 收尾回收 daemon(计划 26-11-05-0808 §3.1 daemon 段/§3.2, D11-D13)

职权(D11 换位): 等 qB 下线窗口, 批量改写 pending 成员的 fastresume 双键, journal 落账。
**绝不**做: 删链(主循环在线做, D11)/碰 state.json(D13 账本契约, 与旧 guardian 同契约)/
taskkill(进程红线)/窗口外任何 fastresume 落盘(N1 铁律: qB 运行期秒级重写, 0.5s 实测覆盖)。

形制(D12 简化): 每 qB 实例至多一个 watcher;触发只有「qB 下线」一个事件 —— 无 TCP
nudge/无端口文件/无兜底扫;窗口开头现读 pending 集(supersede/取消即时生效, 窗口内逐拍
现读续保);进窗判据 = 三证(进程不在 + 端口拒连 + 稳定 STABLE_WINDOW) —— 判据函数已随
finalize_watch.py 整文件退役原样随迁进本模块(本文件是其唯一 home, S4);退位 = pid 抢占 +
旧 daemon 自检自杀, 绝不 taskkill;心跳 = daemon.json(pid/ts)每 HEARTBEAT_INTERVAL touch。

账本(D13/D8): 只写 job journal(rewrites 成员账 + rewritten 相位), 绝不碰 state.json;
每个下线窗口限一轮会话, 窗口内失败重试至成功或 qB 回升, 失败计数(fails)进账;qB 抢先
回升 = 本轮放弃, 无害(N4 实证自愈: 成员经别名正常加载, journal 待重放, 下一窗口重放)。
半途崩溃/退位/回升都留下一致账态(逐成员即改即记账, 原子写), 下一窗口按账重放。

发现面: 扫 <data_dir>/relocate/*.spec.json 中属于本实例(host/port 字面相等, 与
bt_backup_path_of 同口径)且带 bt_backup 字段(新链 spec 必带 —— S1 五闸保证 armed 前
bt_backup 已配置)的 job;pending 口径单点在
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
from typing import Dict, Optional

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
    out = subprocess.run(["ps", "-eo", "comm="], capture_output=True, text=True, timeout=10)
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
    守门粒度 = 每次落盘之前(与 guardian run 循环同款两证合取)。"""
    return _proc_absent(_qb_process_names(), host, port) and _port_refused(host, port)


# ---------------------------------------------------------------- 实例级观测通道(计划 26-11-10-0318 §03.1, W1)
# O1 owner 归属(LISTENING 表解析 + qB 映像名交叉校验 => {pid, ct, ts})与 O2 全机 qB
# 身份枚举(pid + create_time; 驱动新面孔状态机, 状态机本体是 W1b 的活)。证据语义铁律:
# 解析不出/超时/通道异常 = 本拍观测不可用 => 返回 None/空 + warning 留痕, 调用方必须退回
# L2 全机口径(_proc_absent), 绝不产生假证据(宁可不进窗, 不许假进窗)。零新依赖(禁
# psutil), 子进程一律 10s 超时; warning 节流(60s 一次, 不刷屏)属 W2 接线面的职责。

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


def _owner_pid_from_netstat(port: int) -> Optional[int]:
    """Windows: netstat -ano -p tcp 的 LISTENING 行归属目标端口 => owner pid | None

    解析口径: TCP 数据行恒五列(协议 本地地址 外部地址 状态 PID), 状态字各语言版一致为
    英文 LISTENING(计划 §07 R2 的假设, W1 本机实测中英文输出; 不成立则解析不出 => None
    退 L2, 不产假证据); 0.0.0.0 通配监听与具体地址监听同算, 本地端口按最后一个 ':' 取
    (兼容 [::]:port 的 IPv6 形)。编码: 数据行恒 ASCII, 表头本地化文本按 UTF-8+replace
    解出的乱码不影响解析(pitfalls/ops/console-encoding.md 的「显式声明不靠 locale」口径)。
    归属不唯一(同端口多个 LISTENING pid)=> None + warning(不猜)。
    """
    out = subprocess.run(
        ["netstat", "-ano", "-p", "tcp"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=10,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    pids = set()
    for line in (out.stdout or "").splitlines():
        parts = line.split()
        if len(parts) != 5 or parts[0].upper() != "TCP" or parts[3].upper() != "LISTENING":
            continue  # 表头/空行/标题行/UDP 行/非监听行: 一律跳过
        local_port = parts[1].rsplit(":", 1)[-1]
        if not local_port.isdigit() or int(local_port) != int(port) or not parts[4].isdigit():
            continue
        pids.add(int(parts[4]))
    if len(pids) > 1:
        logger.warning("端口 %s 的 LISTENING 归属不唯一(%s), 不猜归属", port, sorted(pids))
        return None
    return next(iter(pids)) if pids else None


def _owner_pid_from_procnet(port: int) -> Optional[int]:
    """Linux: /proc/net/tcp{,6}(st==0A)端口 => socket inode => /proc/<pid>/fd 归属
    => owner pid | None。tcp6 缺失常见(未启用 IPv6), 只当该表无监听; /proc/<pid>/fd
    扫不动(权限/进程消失)逐项跳过; 归属不唯一 => None + warning(不猜)。"""
    inodes = set()
    for table in ("/proc/net/tcp", "/proc/net/tcp6"):
        try:
            with open(table, "r", encoding="utf-8") as f:
                rows = f.read().splitlines()[1:]  # 首行表头
        except OSError:
            continue
        for row in rows:
            cols = row.split()
            # 列制: sl local rem st ... inode(第 10 列); 列数不足/st 非 0A(LISTENING)/端口不合跳过
            if len(cols) < 10 or cols[3].upper() != "0A":
                continue
            local = cols[1].rsplit(":", 1)
            try:
                if len(local) == 2 and int(local[1], 16) == int(port):
                    inodes.add(int(cols[9]))
            except ValueError:
                continue
    if not inodes:
        return None
    pids = set()
    for pid in os.listdir("/proc"):
        if not pid.isdigit():
            continue
        try:
            fds = os.listdir(f"/proc/{pid}/fd")
        except OSError:
            continue  # 权限/已消失: 无从归属, 跳过
        for fd in fds:
            try:
                m = _SOCKET_LINK_RE.match(os.readlink(f"/proc/{pid}/fd/{fd}"))
            except OSError:
                continue
            if m and int(m.group(1)) in inodes:
                pids.add(int(pid))
    if len(pids) > 1:
        logger.warning("端口 %s 的 /proc socket 归属不唯一(%s), 不猜归属", port, sorted(pids))
        return None
    return next(iter(pids)) if pids else None


def _listening_owner_pid(port: int) -> Optional[int]:
    """LISTENING 归属分派(O1 前半; 单点 dispatch, 与 _qb_process_names 同款平台分叉)。

    证据语义: 返回 None = 观测不可用(端口无监听行/归属不唯一/通道异常), 调用方必须退回
    L2 全机口径, 绝不当 owner 死证用。O1 只在端口可达时调用(计划 §03.1)—— 可达而无
    监听行本身就是通道异常, 一律 warning 留痕。
    """
    try:
        owner = _owner_pid_from_netstat(port) if os.name == "nt" else _owner_pid_from_procnet(port)
    except Exception:  # noqa: BLE001 - 归属不出: 保守(观测不可用, 不产假证据)
        logger.warning("端口 %s LISTENING 归属通道异常, 本拍观测不可用", port, exc_info=True)
        return None
    if owner is None:
        logger.warning("端口 %s LISTENING 未归属成功(无监听行或归属不唯一), 本拍 owner 观测不可用", port)
    return owner


def _qb_processes_from_powershell() -> Optional[Dict[int, dict]]:
    """Windows: 单次 PowerShell 批量枚举全机 qB 进程(O2)=> {pid: {name, ct}} | None

    证据语义: 返回 None = 观测不可用, 调用方必须退回 L2 全机口径; {} = 通道健康且全机无
    qB 进程(有效观测)。{} 与 None 的分界 = 健康标记行(_PS_QB_SCRIPT 里管线+标记整体包
    try): Where-Object 零匹配走正常空管线 ⇒ 标记在 ⇒ {}(健康零观测); 任何终止型失败
    (语句终止/script 终止/输出截断/启动失败)⇒ 标记不在 ⇒ None —— 命令级真失败与健康
    零观测在解析侧不可混。**部分清单不冒充全量**: 任何条目身份不完整(StartTime 不可读
    等)或出现形制外的行, 聚合整体判不可用 —— 新面孔状态机拿不完整的 (pid, ct) 集会把
    在跑的 qB 当「不存在」, 那是假证据方向, 宁可整拍退 L2(黄金法则 2; 被剔除条目已逐条
    warning 留痕, per-process 容错在剔除这一层, 计划 §03.1)。
    """
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
            logger.warning("PowerShell qB 枚举输出行形制异常(%r), 该条目剔除", line[:80])
            continue
        pid, name, ft = (p.strip() for p in parts)
        if not pid.isdigit() or not name:
            dropped += 1
            logger.warning("PowerShell qB 枚举条目 pid/映像名异常(%r), 该条目剔除", line[:80])
            continue
        if not ft.isdigit():
            dropped += 1
            logger.warning("qB 进程 pid=%s 的 StartTime 不可读, 该条目剔除(部分清单不冒充全量)", pid)
            continue
        procs[int(pid)] = {"name": name.lower(), "ct": _filetime_to_epoch(int(ft))}
    if not healthy:
        logger.warning("PowerShell qB 枚举输出缺健康标记(%s), 本拍观测不可用", _PS_QB_END_MARK)
        return None
    if dropped:
        return None
    return procs


def _qb_processes_from_proc() -> Optional[Dict[int, dict]]:
    """Linux: /proc/*/comm 含 qbittorrent + /proc/<pid>/stat starttime 换算 epoch 秒(O2)
    => {pid: {name, ct}} | None。create_time = /proc/stat btime + starttime/SC_CLK_TCK。
    逐项容错分两向: comm/stat 读时进程已消失(FileNotFoundError)= 死进程无威胁, 条目整体
    忽略不算枚举不完整; 其余 OSError/解析失败 = 身份不可得, 条目剔除且**聚合判不可用**
    (部分清单不冒充全量, 与 PowerShell 支同口径)。"""
    try:
        with open("/proc/stat", "r", encoding="utf-8") as f:
            btime = next(int(cols[1]) for cols in (ln.split() for ln in f) if cols and cols[0] == "btime")
        hz = os.sysconf("SC_CLK_TCK")
    except (OSError, StopIteration, ValueError, IndexError, AttributeError) as e:
        # AttributeError = 本平台无 os.sysconf(Windows): 与 /proc 缺失同按「枚举不可用」保守
        logger.warning("/proc/stat btime 或 SC_CLK_TCK 不可得(%s), 全机 qB 枚举不可用", e)
        return None
    if hz <= 0:
        logger.warning("SC_CLK_TCK 非法(%s), 全机 qB 枚举不可用", hz)
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
            logger.warning("pid=%s 的 comm 不可读, 该条目剔除(部分清单不冒充全量)", pid)
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
            logger.warning("pid=%s 的 starttime 不可得(%s), 该条目剔除(部分清单不冒充全量)", pid, e)
            continue
        procs[int(pid)] = {"name": name, "ct": btime + starttime / hz}
    if dropped:
        return None
    return procs


def _qb_processes() -> Optional[Dict[int, dict]]:
    """全机 qB 进程身份枚举(O2; 单点 dispatch, 与 _qb_process_names 同款平台分叉与容错)。

    证据语义: 返回 None = 观测不可用(通道异常/枚举不完整), 调用方必须退回 L2 全机口径;
    {} = 通道健康且全机无 qB 进程(有效观测, 名册空的强证)。每 poll 至多取一次并与
    _observe_owner 共用(单次 PowerShell 调用面, 计划 §03.1)。
    """
    try:
        if os.name == "nt":
            return _qb_processes_from_powershell()
        return _qb_processes_from_proc()
    except Exception:  # noqa: BLE001 - 枚举不出: 保守(观测不可用, 不产假证据)
        logger.warning("全机 qB 身份枚举通道异常, 本拍观测不可用", exc_info=True)
        return None


def _observe_owner(port: int, qb_processes: Optional[Dict[int, dict]], now: float) -> Optional[dict]:
    """O1: 端口 LISTENING 归属 + qB 映像名交叉校验 => owner 记录 {pid, ct, ts} | None

    前后两半(计划 §03.1): 归属 pid 的映像名必须含 qbittorrent(大小写不敏感)才记录 ——
    非 qB 服务占端口的保守面(不记录, 绝不把别人的监听当 owner 证据)。证据语义: 返回
    None = 本拍未取得 owner 记录(观测通道不可用/端口无监听行/占用者非 qB/身份不完整),
    调用方一律退回 L2 全机口径, 绝不当 owner 死证用。qb_processes 传 None(枚举通道故障)
    => 直接 None —— 交叉校验没有名册就没有证据。
    """
    if qb_processes is None:
        return None
    pid = _listening_owner_pid(port)
    if pid is None:
        return None
    ident = qb_processes.get(pid)
    if ident is None or "qbittorrent" not in str(ident.get("name") or "").lower():
        logger.warning("端口 %s 的 LISTENING 归属 pid=%s 非全机 qB 名册成员, 不记录 owner(非 qB 服务占端口的保守面)", port, pid)
        return None
    return {"pid": pid, "ct": float(ident["ct"]), "ts": float(now)}


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
    - not_found / FastresumeError/ValueError/OSError -> not_found/failed: 不出账,
      fails 计数承前累计 +1(每失败一次进一账), 窗口内随拍重试(D8)、下一窗口重放
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
        return {"status": "not_found", rj.REWRITE_FAILS_KEY: fails + 1}
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
    sleep=time.sleep
) -> str:
    """一个下线窗口的改写会话(D8: 每窗口限一轮会话; 窗口内失败重试至成功或 qB 回升)。

    每拍/每次落盘前的闸门(顺序即成本序):
      1. 归属(beat): 被退位 ⇒ deposed(自杀, 未落盘的成员留给新主/下一窗口);
      2. pending 现读: journal 已终态的 job 剔除(取消/收口即时生效), 已收口成员出账;
      3. 全收口 ⇒ settled(相位翻正交给主循环拍间 scan 的 flip);
      4. 窗口仍开(瞬时两证: 进程不在 + 端口拒连)—— 任一证失守 = qB 有生命迹象 ⇒
         立即放弃本轮(qb_back; N4: 已写成员经别名正常加载, 未写成员 journal 待重放)。
    """
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
        if not _window_open(host, port):
            return "qb_back"
        for job, pend in remaining:
            job_id = job["job_id"]
            for member in pend:
                now = clock()
                if not owner.beat(now):
                    return "deposed"
                if not _window_open(host, port):
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
                if not rj.record_rewrites(data_dir, job_id, {mkey: rec}, ts=now, pid=owner.pid):
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
    收敛不变量: 窗口外零 fastresume 落盘(三证进窗 + 每次落盘前瞬时两证复验); journal
    是唯一账面, 任一退出路径都留一致账态, 下一窗口可重放(D8/N4)。
    """
    key = rj.instance_key(host, port)
    owner = _Owner(data_dir, key, os.getpid(), host, port, heartbeat=heartbeat)
    started = clock()
    if owner.claim(clock(), HEARTBEAT_MAX_AGE) == "already_running":
        return "already_running"
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
