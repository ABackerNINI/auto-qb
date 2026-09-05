"""单实例锁: 防止同一配置文件并发两个以上正常 run 实例

仅正常 `run()` 模式获取; `--export-yaml` / `--export-torrents_info` 等只读模式不持锁。
基于第三方 `filelock`(跨平台 fcntl/msvcrt 统一封装, 句柄随进程退出自动释放),
伴生 `<lock>.meta.json` 记录 PID/启动时间/配置绝对路径, 报错时告知持有者信息。

陈旧锁策略: OS 进程退出/崩溃自动释放句柄; 不实现 PID 存活检测 + 强制接管(边界 case 多,
必要时用户手动删除锁文件即可)。
"""
import json
import logging
import os
from datetime import datetime

from filelock import FileLock, Timeout

from .config.errors import ConfigError

logger = logging.getLogger(__name__)


class SingleInstanceLockError(ConfigError):
    """锁竞争或锁文件错误, 走 ConfigError 通道 (CLI 退出码 1, stderr 无堆栈)"""


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
        # 例: 'logs/auto-qb-state.json' -> 'logs/auto-qb-state.lock' / 'state.json' -> 'state.lock'
        # 状态文件: 'logs/auto-qb-state.json' (config.models 字段默认)
        sf = state_file or "logs/auto-qb-state.json"
        base, dot, ext = sf.rpartition(".")
        self.lock_path = f"{base}.lock" if dot else f"{sf}.lock"
        self.meta_path = self.lock_path + ".meta.json"
        self._lock = FileLock(self.lock_path, timeout=0)
        self._held = False

    def acquire(self) -> None:
        """非阻塞获取锁; 失败抛 SingleInstanceLockError 含持有者信息"""
        holder_info = self._read_meta()
        try:
            self._lock.acquire()
        except Timeout as e:
            detail = f" (PID {holder_info['pid']}, {holder_info['started_at']}, config {holder_info['config']})" if holder_info else ""
            raise SingleInstanceLockError(
                f"另一实例已持有锁 {self.lock_path}{detail}; auto-qb 仅允许同一配置一个运行实例"
            ) from e
        self._held = True
        self._write_meta()

    def release(self) -> None:
        """释放锁与伴生 meta (idempotent: 重复调用无副作用)

        filelock 的 Windows 实现持有文件句柄到进程退出; 显式 close() 提前释放,
        让测试临时目录清理时不再 PermissionError。
        """
        if self._held:
            try:
                self._lock.release()
            except Exception:
                pass
            try:
                self._lock._lock_file.close()  # noqa: SLF001  # filelock 内部句柄
            except Exception:
                pass
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
