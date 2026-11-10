"""测试端口单点(计划 26-11-02-0657 §02.7 端口分层)。

`_free_port` 原本是各测试文件各自复制一份的裸 bind(0) —— bind(0) 取号与真正监听之间存在
TOCTOU 窗口(取到的端口在 socket 关闭后被别的进程抢走), 高机载/xdist 并发下偶发假红。
本模块收敛为单一实现: 至多取 3 个不同端口, 逐个**回绑自验**(候选被抢即换下一个),
三次都被抢才失败。调用方语义不变(仍返回一个当前可用端口号)。

引用纪律与 tests/_tmp_bootstrap.py::TMP_ROOT_CANDIDATES 相同: 全仓库唯一一份,
别处不得复制 `def _free_port` 实现(散落守卫见 tests/test_free_port.py::test_free_port_single_source)。

三个入口: `free_port()` 给"只要一个空闲端口"的用例; `hold_run(n)` 给"需要连续 n 个可绑端口
并当场占住"的连号候选表用例(base 单验不等于整段可绑, 见 issue 26-11-06-0330);
`http_server(handler)` 给"用例内自起回环 HTTP 假服"的用例 —— **禁裸 `ThreadingHTTPServer`**:
它继承 `HTTPServer.allow_reuse_address = 1`(SO_REUSEADDR), Windows 上允许抢绑已监听端口,
-n 8 并行下两把带 REUSEADDR 的 bind(0) 可能拿到同一端口双绑, 客户端连接被递给别人的假服/
已关闭的 socket ⇒ ConnectionError(被中止) 假红(issue 26-11-11-0114; 生产侧同款口径
src/auto_qb/hr/server.py::_EndpointServer)。散落守卫: test_free_port.py::test_http_server_single_point。
"""
from __future__ import annotations

import http.server
import socket
import socketserver

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


#: 假服 backlog 上限: TCPServer 默认 5, -n 8 并发下(同机 8 worker 真回环流量 + CPU 饱和
#: 拉慢 accept)突发的并发连接会顶满 ⇒ Windows 对满 backlog 直接 RST ⇒ 客户端 ConnectionError。
#: 与 free_port 的回绑自验同哲学: 窗口压小, 不是消除 —— 但这里压小的代价只是内核排队, 零成本。
HTTP_SERVER_BACKLOG = 128


class _ExclusiveHTTPServer(http.server.ThreadingHTTPServer):
    """测试假服基座: 独占 bind + 启动期零 DNS(逐字对齐生产 src/auto_qb/hr/server.py::_EndpointServer 两项口径)。

    - `allow_reuse_address = False`: 裸 ThreadingHTTPServer 的 SO_REUSEADDR 在 Windows 上允许
      抢绑已监听端口 —— 并行下双绑 ⇒ 连接串线 ⇒ ConnectionError(被中止) 假红(issue 26-11-11-0114)。
      关掉它, bind(0) 取号才真正互斥, 假服之间不会拿到同一端口。
    - `server_bind` 只绑不查 FQDN: HTTPServer.server_bind 调 socket.getfqdn(127.0.0.1) 可能触发
      反向 DNS, 弱网/无网机器上一次能抱几秒且发生在构造器里(同步) —— 测试启动期为它付出纯延迟。
    """

    allow_reuse_address = False
    request_queue_size = HTTP_SERVER_BACKLOG

    def server_bind(self) -> None:  # type: ignore[override]
        socketserver.TCPServer.server_bind(self)
        host, port = self.server_address[:2]
        self.server_name = host
        self.server_port = port


def http_server(handler: type[http.server.BaseHTTPRequestHandler], host: str = "127.0.0.1") -> _ExclusiveHTTPServer:
    """构造一个用例内回环 HTTP 假服: bind (host, 0) 当场独占占住, 返回未 start 的 server 实例。

    调用方自己 `threading.Thread(target=srv.serve_forever, daemon=True).start()` / `srv.shutdown()`
    / `srv.server_close()`(与裸 ThreadingHTTPServer 用法一致, 只换构造这一行)。端口取 0 由 OS
    分配: 构造即 bind+listen(同步), 返回时端口已在监听, 不存在"起线程前端口未就绪"的窗口。
    """
    return _ExclusiveHTTPServer((host, 0), handler)
