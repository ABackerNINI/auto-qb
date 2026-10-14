"""单实例锁: 防止同一配置文件并发两个以上正常 run 实例; 兼全项目文件锁的单点入口

仅正常 `run()` 模式获取; `--export-yaml` / `--export-torrents_info` 等只读模式不持锁。
基于第三方 `filelock`(跨平台 fcntl/msvcrt 统一封装, 句柄随进程退出自动释放),
伴生 `<lock>.meta.json` 记录 PID/启动时间/配置绝对路径, 报错时告知持有者信息。

filelock 的构造与释放只在**本模块**出现(issue 26-10-11-0240): hr 每站点锁此前各自
`from filelock import FileLock` 裸构造, 与 SingleInstanceLock 同族两套 —— 超时默认值 /
释放失败吞异常 / 句柄清理纪律分处两地, 改一处必漏另一处。`open_file_lock` /
`release_file_lock` 是两侧共用的构造/释放单点。

陈旧锁策略: OS 进程退出/崩溃自动释放句柄; 不实现 PID 存活检测 + 强制接管(边界 case 多,
必要时用户手动删除锁文件即可)。
"""
import json
import logging
import os
from datetime import datetime
from typing import Optional

from filelock import FileLock, Timeout

from .errors import AutoQbError

logger = logging.getLogger(__name__)


def open_file_lock(path: str, timeout: float = 0.0) -> FileLock:
    """filelock 的统一构造入口(**未获取**; 单点见模块 docstring, issue 26-10-11-0240)

    构造后由调用方自行 acquire/release —— 超时异常(filelock.Timeout)由调用方翻译成
    各自领域错误(SingleInstanceLock -> SingleInstanceLockError 含持有者信息;
    hr 站点锁 -> HrLockBusy「等下一轮」)。
    """
    return FileLock(str(path), timeout=timeout)


def release_file_lock(lock, *, logger: Optional[logging.Logger] = None, what: str = "文件锁") -> None:
    """释放文件锁; 任何失败静默(释放失败不影响主流程正确性), 有 logger 时记 debug

    释放纪律单点(issue 26-10-11-0240): filelock 的句柄清理随平台/版本行为不一(历史
    Windows 实现 release 后仍持句柄到进程退出, 需显式 close; 现版本由库内部按 fd 生命周期
    自理, 外部 close 仅作旧版兜底) —— 该差异收在本函数, 调用方不再各写 try/except。
    """
    if lock is None:
        return
    try:
        lock.release()
    except Exception as e:
        if logger is not None:
            logger.debug(f"释放{what}失败: {e}", exc_info=True)
        return
    try:
        lock._lock_file.close()  # noqa: SLF001  # filelock 内部句柄(旧版 Windows 兜底; 现版本无该属性即静默跳过)
    except Exception:
        pass


class SingleInstanceLockError(AutoQbError):
    """锁竞争或锁文件错误, 走 AutoQbError 通道 (CLI 退出码 1, stderr 无堆栈)"""


class SingleInstanceLock:
    """单实例锁: state_file 派生锁文件, 持锁时持锁文件 + 伴生 meta

    用法:
        lock = SingleInstanceLock(state_file)
        lock.acquire()        # 失败抛 SingleInstanceLockError
        try:
            ...
        finally:
            lock.release()
    """
    def __init__(self, state_file: str):
        # 锁文件路径: <state_file 去掉扩展名>.lock (与 state 文件同目录不同名, 不会冲突)
        # 例: 'auto-qb-data/state.json' -> 'auto-qb-data/state.lock' / 'state.json' -> 'state.lock'
        # 状态文件: 'auto-qb-data/state.json' (config.models 字段默认)
        sf = state_file or "auto-qb-data/state.json"
        base, dot, ext = sf.rpartition(".")
        self.lock_path = f"{base}.lock" if dot else f"{sf}.lock"
        self.meta_path = self.lock_path + ".meta.json"
        self._lock = open_file_lock(self.lock_path)
        self._held = False

    def acquire(self) -> None:
        """非阻塞获取锁; 失败抛 SingleInstanceLockError 含持有者信息"""
        holder_info = self._read_meta()
        try:
            self._lock.acquire()
        except Timeout as e:
            detail = f" (PID {holder_info['pid']}, {holder_info['started_at']}, config {holder_info['config']})" if holder_info else ""
            raise SingleInstanceLockError(f"另一实例已持有锁 {self.lock_path}{detail}; auto-qb 仅允许同一配置一个运行实例") from e
        self._held = True
        self._write_meta()

    def release(self) -> None:
        """释放锁与伴生 meta (idempotent: 重复调用无副作用)

        释放走 infra 单点 `release_file_lock`(issue 26-10-11-0240): filelock 的句柄清理
        随平台/版本行为不一(历史 Windows 实现持句柄到进程退出), 差异收在单点内; 本方法只
        保留自己的 `_held` 幂等与 meta 卸载。
        """
        if self._held:
            release_file_lock(self._lock)
            self._held = False
        try:
            os.remove(self.meta_path)
        except FileNotFoundError:
            pass
        except OSError:
            pass

    def __enter__(self):
        self.acquire()
        return self

    def __exit__(self, *args):
        self.release()

    # ---------- 伴生 meta: 持锁者信息 (供报错时告知) ----------

    def _write_meta(self) -> None:
        meta = {
            "pid": os.getpid(),
            "started_at": datetime.now().astimezone().isoformat(timespec="seconds"),
            "config": os.environ.get("AUTO_QB_CONFIG", "") or "(config 路径未传环境变量, 见 process cmdline)",
        }
        try:
            with open(self.meta_path, "w", encoding="utf-8") as f:
                json.dump(meta, f, ensure_ascii=False)
        except OSError as e:
            # meta 写失败不阻塞持锁(锁是主防线, meta 仅辅助报错)
            logger.debug(f"锁伴生 meta 写入失败: {e}")

    def _read_meta(self) -> dict:
        try:
            with open(self.meta_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (OSError, json.JSONDecodeError):
            return {}
