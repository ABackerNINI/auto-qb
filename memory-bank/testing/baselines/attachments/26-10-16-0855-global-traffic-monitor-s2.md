# 3413 passed + 4 skipped —— 全局流量监视小工具 S2 落盘(工具测试新增 27 条, 根集数字不变)

> 摘要: 用户「实施计划S2:26-10-16-0541-plan-global-traffic-monitor.html」(对 S2 的显式授权, S3–S10 不动)。storage.py 全量实现(~430 行: atomic_write_text 原子写单点[tmp+fsync+os.replace, Windows 读者持句柄 WinError 5/32 退避重试 5×50ms]/DatStore[TM 兼容 lines 头+新日在前+KB 向下取整+坏行跳过]/StateStore[每次采样必写, 丢失窗口 ≤ 采样间隔]/FlushPolicy[Δ≥1MiB 或 ≥30s, 首帧必落盘, 跨天 reset 新日基线]/SingleInstanceLock[filelock 0 超时+meta 持有者 PID, fail-fast]/Storage 编排[record: 跨天封存旧日 -> upsert -> dat 节流 -> state 必写; recover: state 权威、缺失/损坏/降级 -> dat 兜底; dat_text 内存活尾])+ __main__.py run 子命令 + sampler.py _DAT_ROW_RE -> 公共 DAT_ROW_RE(工具内 dat 行格式单点)+ tests/test_storage.py 新文件 27 条守阵 + test_smoke.py CLI 断言更新, 改 4 文件+1 新文件零 auto-qb 触碰。出口判据全过: 工具 60/60; 红验 6 条单行锚点突变全判红字节恒等还原复绿; 并发读守阵(线程+子进程)只见完整文件; curves.py 真解析器 oracle bad==0; 真机冒烟 kill -9 后 state 快照双恢复、双实例 fail-fast 带 PID。本切片为根 test.full 回归闸门数字(工具测试不在根 testpaths 内, 不进本 TOTAL, 与 S0/S1 基线逐位一致)。
> 基线时间: 2026-10-16 08:55

**Refs:** memory-bank/tasks/26-10-16-backend-global-traffic-monitor.md, memory-bank/pitfalls/backend/platform-fs.md

## 验收数字

- test.full: 3413 passed + 4 skipped / TOTAL 17343 182 5846 159 99%; 耗时 142.14s(单次采样, 口径见 baseline.md)。与 S0(26-10-16-0601)及 S1(26-10-16-0815)切片数字逐位一致 —— S2 零 auto-qb 触碰且工具测试不进根 testpaths, 符合预期。
- 工具侧自测(独立 venv, 不计入根 TOTAL): `uv run pytest -q` 60 passed(4 条 S0 冒烟 + 29 条 S1 采样守阵 + 27 条 S2 落盘守阵), ~4s。
- 红验(临时脚本 H:/Temp/gtm-s2-redverify.py, bytes 层, 锚点 count==1, 还原后字节恒等, 基线复跑放还原后): 6 条单行锚点突变全 RED —— 原子写失效(mkstemp->原地截断写) / replace 退避重试失效 / 节流阈值失效(恒落盘) / state 每次采样写失效 / 单实例锁竞争失效(锚点取唯一上下文行 except Timeout 偏移 -1, 形态三: self._lock.acquire() 在 SingleInstanceLock 与 Storage 两处出现) / dat 加载保留历史日失效; 全部字节恒等还原后 60 passed 复绿。
- 并发读守阵(计划 S2 出口判据): 线程读者 300 次写窗口内 >50 次读、子进程读者(启动握手 + 400 次写窗口, done 文件收尾) >100 次读, 违规数均为 0 —— 只见完整文件(空文件/截断/半行/坏行格式全部判违规)。
- curves 兼容(计划 S2 出口判据): 产出的 dat 经 importlib 加载 auto-qb 真解析器 `src/auto_qb/core/curves.py::parse_history_dat` 解析 bad==0 且值逐日一致(7MiB=7168KB 等); `sampler.restore_from_dat` 对产出文本 round-trip。
- 真机冒烟(Windows, 临时 data_dir H:/Temp/gtm-smoke-*, 全程后清理): ①首启 state 缺失 -> dat 兜底(无今天行 -> 0)WARNING 可见 + 基线采样(真计数器 up=130110220854 down=438244529987); ②第二实例 fail-fast: 「另一 gtm 实例已持有锁 ...(PID 47852, 启动于 2026-10-16 08:52:31+08:00); 工具仅允许单实例」; ③taskkill /F(kill -9)后重启: 「state 快照恢复 | day=2026-10-16 累计 up=1810801 down=212327, 基线 up=130112031655 down=438244742314」——累计+计数器基线双恢复(丢失窗口 ≤ 采样间隔); ④dat 首帧 `lines: "1"` + `2026/10/16 5283/488`, state.json day_up_bytes=5409876(5283KB 向下取整逐项吻合), 8s 会话 up≈5.4MB/down≈0.5MB 量级合理。
- Linux(WSL)侧未跑 —— S2 含 Windows 专属分支(replace 退避重试; POSIX 上不触发), 其余路径(psutil/stdlib)三平台统一; installer 平台分支在 S5。本条 Windows 侧数字为事实源。

## 本改动面

- `tools/global-traffic-monitor/src/gtm/storage.py`(S2 占位 -> 全量实现, ~430 行): `default_data_dir`(GTM_DATA_DIR 优先 + 三平台路径) · `atomic_write_text`(同目录 tmp -> flush -> fsync -> os.replace; 空路径报错; 失败清残留) · `_replace_retry`(PermissionError 退避 5×50ms, Windows 读者持句柄竞态) · `DatStore`(load/upsert/render/flush; lines 头 + 新日在前 + KB 向下取整 + 坏行跳过) · `StateStore`(read 缺失/JSON 坏/非对象 -> None; write 每次采样) · `FlushPolicy`(due/mark_flushed/reset; 首帧必落盘) · `SingleInstanceLockError` · `SingleInstanceLock`(filelock 0 超时 + meta 持有者 PID; release 幂等) · `Storage`(acquire_lock/release_lock/load/recover/record/flush/dat_text/close; state 权威、dat 兜底)。
- `tools/global-traffic-monitor/src/gtm/__main__.py`: `run` 子命令(--data-dir; acquire_lock fail-fast 干净退出码 1; recover 告警可见; 采样-落盘循环; 单轮失败 ERROR 可见下一轮重试不杀守护进程; Ctrl+C 优雅退出最终落盘+释放锁); 无子命令打印帮助。
- `tools/global-traffic-monitor/src/gtm/sampler.py`: `_DAT_ROW_RE` -> 公共 `DAT_ROW_RE`(dat 行格式工具内单点, storage.DatStore.load 共用防漂移; 行为零变化)。
- `tools/global-traffic-monitor/tests/test_storage.py`(新增, 27 条): dat 格式六态/KB 取整/加载容错/curves oracle/round-trip/原子写失败与重试(成功+耗尽)/并发读双形态(线程+子进程握手)/state 每次采样/节流四态(阈值恰界/区间恰界/首帧/活尾)/恢复五态(接续/dat 兜底/版本损坏/state 权威/跨天封存)/锁三形态(进程内/跨进程/幂等)/default_data_dir。全程注入替身 + tmp_path, hermetic。
- `tools/global-traffic-monitor/tests/test_smoke.py`: CLI 默认行为断言(S0 骨架提示 -> 无子命令打印帮助)。
- 滚动面(文档): 计划 HTML 就地更新(doc-updated=26-10-16-0855, 状态行 S0–S2, §04 R0 增 S2 行) · tasks 档案 R3 · activeContext 切片 R3 · 工具 README(run 用法+结构注记)/__init__ 进度 · pitfalls/backend/platform-fs.md 新增两节(Windows 原子写与并发读者双向瞬时拒绝; Git Bash MSYS pid 与 grep 行尾退化计数) · kb.index 重建 · 本基线切片新建。
