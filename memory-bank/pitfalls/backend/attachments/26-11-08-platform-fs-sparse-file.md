# platform-fs · NTFS 稀疏文件(原文归档)

> 外迁自 memory-bank/pitfalls/backend/platform-fs.md · 26-11-08 cap 清零 —— 「NTFS 稀疏文件」条目逐字外迁, **原样保留**(唯一改动: 指向 long-evidence 的相对链接随本件位置去 `attachments/` 前缀)。
> 主档案: [../platform-fs.md](../platform-fs.md)

### NTFS 稀疏文件: 只有 `FSCTL_SET_SPARSE` → `SetEndOfFile` 才是稀疏的

- **触发**: 建大文件 / 建测试用树(2026-09-21 实测, 100 文件 × 64 MiB 对照)。
- **判别**: **正确序列** `CreateFileW` → `DeviceIoControl(h, FSCTL_SET_SPARSE)` →
  `SetFilePointerEx` + `SetEndOfFile` ⇒ 实占 **0 字节/文件**(仅 MFT ≈205 B), **0.23 ms/文件**(6 万文件 ≈ 14 s)。
  ❗**三种"看着对"的写法全部满额分配**: ①标记稀疏后再 `os.truncate` —— **truncate 会让稀疏标志失效**,
  实占整个逻辑大小; ②朴素 `f.seek(n); f.write(b"\0")` —— 非稀疏文件向后扩展时 NTFS 必须让新区域读到 0 ⇒ 满额;
  ③`fsutil file createnew` 先建再 `sparse setflag` —— **setflag 不回收**已分配的簇(256 MiB 实测先占 166 MB 且不释放)。
- **处置**: 稀疏建树走 `ctypes` + `DeviceIoControl`, 完整步骤与写满盘的现场见 [platform-fs-long-evidence.md](platform-fs-long-evidence.md)。
