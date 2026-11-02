"""测试端口单点(计划 26-11-02-0657 §02.7 端口分层)。

`_free_port` 原本是各测试文件各自复制一份的裸 bind(0) —— bind(0) 取号与真正监听之间存在
TOCTOU 窗口(取到的端口在 socket 关闭后被别的进程抢走), 高机载/xdist 并发下偶发假红。
本模块收敛为单一实现: 至多取 3 个不同端口, 逐个**回绑自验**(候选被抢即换下一个),
三次都被抢才失败。调用方语义不变(仍返回一个当前可用端口号)。

引用纪律与 tests/_tmp_bootstrap.py::TMP_ROOT_CANDIDATES 相同: 全仓库唯一一份,
别处不得复制 `def _free_port` 实现(散落守卫见 tests/test_free_port.py::test_free_port_single_source)。
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
