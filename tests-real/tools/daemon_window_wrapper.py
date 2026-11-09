"""测试侧回收 daemon wrapper(E2c 复验收编; 用户授权的实例级开窗判据旁路)。

授权(两层, 各自独立成立, 均 2026-11-10 经 AskUserQuestion):
[1] 源会话层 —— 2336 E2c 复验(clone1): 明示选择「授权测试侧实例级旁路」—— 全机名册
  判据在多实例测试机上让 daemon 永不开窗(生产实例 26586/16585 在跑且有活跃连接, 实验
  绝对不可碰), 而目标测试实例已下线且其 BT_backup 与生产完全隔离; 本文件即收编自该实验
  的 scratch 原件(见下收编说明), 该层授权是其出处。
[2] 本任务层 —— 计划 26-11-10-0230 S4 真机闭环(本仓): 明示选择「授权旁路(推荐)」,
  权威记录 = tests-real/.work/relocate-rlfn-e2e/evidence/authorization.md。
判据与旁路配方见 memory-bank/pitfalls/testing/relocate-window-machine-roster.md; 消费方 =
计划 26-11-10-0230 的 S4 真机闭环(环境1)。收编说明: 原件在 E2c 实验 scratch(tests-real/
.work/e2c_recheck/, gitignored, real.seed clean 可清), 2026-11-10 收编入库耐久化,
唯一改动 = 决策留痕落点移到 gitignored 的 .work/tools-daemon-wrapper/(原版写 scratch
内 evidence/)。

边界(零扩大):
- 盘上产品代码零改动: 本 wrapper 只在 daemon 进程内替换模块级 `_proc_absent` 一个函数
  (两处调用点 —— run() 主循环判 down 与 _window_open 进窗复验 —— 都汇到它, 单点生效);
- 实例级名册: 只把「镜像路径在测试白名单前缀 D:\\Programs\\qBittorrent-testing* 下的
  qbittorrent.exe」计为测试 qB 在场 —— 生产实例不计入(其 BT_backup 与目标完全隔离);
- 端口拒连(_port_refused)+ 30s 稳定窗(STABLE_WINDOW)两证保持产品原样零改动;
- daemon 其余全链(scan/journal/rewrite/record/宽限退出/pid 抢占)全走产品原码;
- 每次决策留痕见 LOG; PowerShell 探测异常 => 保守判「测试 qB 在场」(不开窗), 与产品
  「判不出=保守」口径一致。
"""
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
LOG = HERE.parent / ".work" / "tools-daemon-wrapper" / "daemon_wrapper.log"
TEST_PREFIX = "d:\\programs\\qbittorrent-testing"  # 环境注册表 image_prefix(小写比对, 前缀覆盖 testing/testing2)


def _log(msg: str) -> None:
    line = f"{time.strftime('%Y-%m-%d %H:%M:%S')} {msg}"
    try:
        LOG.parent.mkdir(parents=True, exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except OSError:
        pass


def _qb_paths() -> list[str] | None:
    """带镜像路径枚举 qbittorrent.exe; 探测失败返回 None(调用方保守判「在场」)。"""
    try:
        r = subprocess.run(
            [
                "powershell", "-NoProfile", "-Command",
                "Get-Process qbittorrent -ErrorAction SilentlyContinue | ForEach-Object { $_.Path }"
            ],
            capture_output=True,
            text=True,
            timeout=20,
        )
    except Exception as e:  # noqa: BLE001 — 探测异常按保守面
        _log(f"probe error: {e!r}")
        return None
    return [l.strip() for l in (r.stdout or "").splitlines() if l.strip()]


def patch() -> None:
    import auto_qb.tools.recycle_daemon as rd

    orig = rd._proc_absent

    def instance_scoped(names, host="", port=0):
        paths = _qb_paths()
        if paths is None:
            return False  # 探测不可用: 保守 = 测试 qB 视为在场, 不进窗
        test_present = [p for p in paths if p.lower().startswith(TEST_PREFIX)]
        refused = bool(port) and rd._port_refused(host or "127.0.0.1", port)
        verdict = (not test_present) and refused
        _log(
            f"instance_scoped: all_qb={len(paths)} test_qb={len(test_present)} "
            f"test_paths={test_present!r} port={port} refused={refused} => absent={verdict}"
        )
        return verdict

    rd._proc_absent = instance_scoped
    _log(f"patched rd._proc_absent (orig={getattr(orig, '__name__', orig)!r}); TEST_PREFIX={TEST_PREFIX}")


def main() -> int:
    _log(f"wrapper start argv={sys.argv[1:]!r}")
    patch()
    from auto_qb.tools import recycle_daemon as rd
    rc = rd.main(sys.argv[1:])
    _log(f"wrapper exit rc={rc}")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
