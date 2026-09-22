# 平台与文件系统

> 摘要: Windows / Linux 差异、长路径、稀疏文件、删除拦截层 —— 与宿主环境强相关的一类坑。
> 触发: 锁文件, 平台差异, Windows, Linux, 长路径, 稀疏文件, 删不掉, 磁盘空间, 回收站, 盘满

### 锁文件残留随平台不同 (是 `filelock` 语义, 不是 bug)

- **触发**: 改 `locking.py` / 写"锁文件该不该存在"的断言。
- **判别**: `locking.release()` 只删伴生 `meta.json`; `state.lock` 由 `filelock` 底层处理 ——
  **Windows(msvcrt) 释放时删, POSIX(flock) 不删**(flock 标准语义, 删锁文件反而不安全)。
  ⇒ Linux CI 上残留是**正常行为**。
- **处置**: 测试按 `os.name == "nt"` **分平台断言**。

### Windows 长路径必须加 `\\?\` 前缀

- **触发**: 访问深路径文件。
- **判别**: 超过 MAX_PATH 的路径在 Windows 上直接失败。
- **处置**: 磁盘文件检查走 `add_long_path_prefix_for_win`(`\\?\` 前缀); **新文件访问走同一工具**。

### NTFS 稀疏文件: 只有 `FSCTL_SET_SPARSE` → `SetEndOfFile` 才是稀疏的

- **触发**: 建大文件 / 建测试用树(2026-09-21 实测, 100 文件 × 64 MiB 对照)。
- **判别**: **正确序列** `CreateFileW` → `DeviceIoControl(h, FSCTL_SET_SPARSE)` →
  `SetFilePointerEx` + `SetEndOfFile` ⇒ 实占 **0 字节/文件**(仅 MFT ≈205 B), **0.23 ms/文件**(6 万文件 ≈ 14 s)。
  ❗**三种"看着对"的写法全部满额分配**: ①标记稀疏后再 `os.truncate` —— **truncate 会让稀疏标志失效**,
  实占整个逻辑大小; ②朴素 `f.seek(n); f.write(b"\0")` —— 非稀疏文件向后扩展时 NTFS 必须让新区域读到 0 ⇒ 满额;
  ③`fsutil file createnew` 先建再 `sparse setflag` —— **setflag 不回收**已分配的簇(256 MiB 实测先占 166 MB 且不释放)。
- **处置**: 走 `ctypes` + `DeviceIoControl`(**`fsutil` 是进程派生不是系统调用**, 每文件一次 spawn 在数万文件规模上不可接受)。
  ⚠ **踩过的现场**: 按错误写法在 R 盘(70 GB 虚拟盘, 当时仅剩 7.2 GB)建树, 第一个 4 GiB 文件实占 4 GiB、
  第二个文件 `OSError: 112 (ERROR_DISK_FULL)` —— **把盘写满**。**大文件稀疏建树前先建 1 个并校验分配量。**

### 本机"删除拦截层"只在 D 盘生效, 且 R 盘无回收站

- **触发**: 想真释放磁盘空间 / 删大目录(2026-09-21 实测)。
- **判别**: 工具环境删除 **D 盘**大目录会**进回收站而不释放空间**(360sd 在跑) ⇒ `shutil.rmtree` 后 `df` 纹丝不动。
  但 **R 盘 `$RECYCLE.BIN` 实测 0.00 MB、删除即释放** —— **别套用同一条经验**去 R 盘找回收站。
- **处置**: D 盘要真释放必须按 `$I` 元数据定位自己的条目再删(`$I` 偏移 16-24 是 FILETIME **UTC**、
  偏移 28 起是 UTF-16LE 原始路径; 同名 `$R` 是载荷 ——
  ❗**`$R` 若是目录必须 `shutil.rmtree`, 用 `os.remove` 只会报 `WinError 5`**)。

### 判断"两套 API 读数矛盾"前先确认是同一时刻

- **触发**: 比较两个来源的磁盘 / 内存读数(2026-09-21 教训)。
- **判别**: 曾拿"写入前"的 `Get-PSDrive` 读数与"写满后"的 `shutil.disk_usage` 读数对比,
  得出"三套空间 API 互相矛盾"的结论 —— **完全错误**; 同刻复核三口径**逐字节相同**
  (`GetDiskFreeSpaceExW` / `shutil` / `df`)。
- **处置**: 涉及"环境事实"的结论必须**同刻取样**, 否则会把两次状态差当成工具不一致。
