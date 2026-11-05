"""测试端口单点(计划 26-11-02-0657 §02.7 端口分层)。

`_free_port` 原本是各测试文件各自复制一份的裸 bind(0) —— bind(0) 取号与真正监听之间存在
TOCTOU 窗口(取到的端口在 socket 关闭后被别的进程抢走), 高机载/xdist 并发下偶发假红。
本模块收敛为单一实现: 至多取 3 个不同端口, 逐个**回绑自验**(候选被抢即换下一个),
三次都被抢才失败。调用方语义不变(仍返回一个当前可用端口号)。

引用纪律与 tests/_tmp_bootstrap.py::TMP_ROOT_CANDIDATES 相同: 全仓库唯一一份,
别处不得复制 `def _free_port` 实现(散落守卫见 tests/test_free_port.py::test_free_port_single_source)。

两个入口: `free_port()` 给"只要一个空闲端口"的用例; `hold_run(n)` 给"需要连续 n 个可绑端口
并当场占住"的连号候选表用例(base 单验不等于整段可绑, 见 issue 26-11-06-0330)。
"""
from __future__ import annotations

import socket

RETRIES = 3  # bind(0) 取号次数上限; TOCTOU 只压窗口不可消除, 3 次连抢不到即真有端口压力


def free_port(host: str = "127.0.0.1") -> int:
    """取一个当前空闲端口, 回绑自验后返回; 连抢 RETRIES 次都被占则 RuntimeError(响亮失败)。"""
    last_err: OSError | None = None
    for _ in range(RETRIES):
        with socket.socket() as s:
            s.bind((host, 0))
            candidate = s.getsockname()[1]
        try:
            with socket.socket() as probe:
                probe.bind((host, candidate))  # 回绑自验: 窗口内被抢则 OSError(10048/98)
        except OSError as exc:
            last_err = exc
            continue
        return candidate
    raise RuntimeError(f"连续 {RETRIES} 次取端口后回绑均被抢({host}) —— 端口压力异常, 先查残留进程") from last_err


def hold_run(count: int = 3, host: str = "127.0.0.1") -> tuple[int, list[socket.socket]]:
    """占住**连续 count 个**端口, 返回 (基址, 句柄列表); 调用方负责 close。

    「连号候选表」用例(发现端点 base/base+1/base+2)要的不是"一个空闲端口", 而是"一段连续
    可绑端口": bind(0) 只保证**基址**可用, base+1/base+2 可能落进 Windows 动态排除段
    (`netsh interface ipv4 show excludedportrange protocol=tcp`; Hyper-V/WSL 开机预留,
    每次开机不同)或被独占进程占住 —— 显式 bind 抛 WinError 10013/10048。issue
    26-11-06-0330 的假红就是"基址自验过了, 连号后两位没验"。

    故整段逐个 bind 且**不释放**(自验与持有是同一次 bind, 调用方拿到即已在手, 不存在"验完再绑"
    的窗口; 取号那一步仍走 bind(0), 基址被抢就让整段失败重来); 任一位失败就关掉
    整段换新基址重试, 连抢 RETRIES 次都不成则 RuntimeError(响亮失败, 不交半截坏段)。
    """
    last_err: OSError | None = None
    for _ in range(RETRIES):
        with socket.socket() as s:
            s.bind((host, 0))
            base = s.getsockname()[1]
        if base + count - 1 > 65535:
            continue  # 越界不试: 候选表本身在 65535 截断, 连号语义已不成立
        socks: list[socket.socket] = []
        try:
            for offset in range(count):
                sock = socket.socket()
                socks.append(sock)
                sock.bind((host, base + offset))  # 逐位真绑: 排除段/独占拒绝当场暴露
        except OSError as exc:
            last_err = exc
            for sock in socks:
                sock.close()
            continue
        return base, socks
    raise RuntimeError(f"连续 {RETRIES} 次都取不到 {count} 个连续可绑端口({host}) —— 先查残留进程与排除段") from last_err
