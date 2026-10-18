# 链接能力探测: reparse 结构 / 1314 二义性 / drvfs 只在挂载选项里

> 摘要: 链接能力探测: reparse 结构 / 1314 二义性 / drvfs 只在挂载选项里
> 触发: 别名, junction, symlink, 硬链接, reparse, REPARSE_DATA_BUFFER, MountPointReparseBuffer, 1314, 提权, 长路径, drvfs, WSL, 9p, /proc/mounts, 能力探测, 跨 OS, 链接不可见, 建链成功但读不了
**Refs:** memory-bank/tasks/26-10-18-backend-group-relocate-restart-free.md

### 手写 REPARSE_DATA_BUFFER 建 junction: MountPointReparseBuffer 没有 Flags 字段

- **触发**: 不用 `mklink /J`(要起子进程、Unicode 路径要过命令行)而用 `DeviceIoControl(FSCTL_SET_REPARSE_POINT)`
  自己拼 `REPARSE_DATA_BUFFER` 建 junction。照着 `SymbolicLinkReparseBuffer` 的记忆把 4 个 USHORT 后面
  再写一个 `ULONG Flags`。
- **判别**: 建链调用直接抛 `ValueError: Can only assign sequence of same size`(ctypes 数组切片赋值长度
  对不上), 或内核拒绝 / 建出坏链接。根因是**布局错位**: mount point 的用户数据结构是
  `4 个 USHORT + PathBuffer`, **没有 Flags**(Flags 只属于 SymbolicLinkReparseBuffer);
  多算 4 字节会把 PathBuffer 整体后移 4 字节。
- **处置**: 正确布局 —— 头 8 字节(`ULONG tag` / `USHORT ReparseDataLength` / `USHORT Reserved`),
  其后 `SubstituteNameOffset(0)` / `SubstituteNameLength` / `PrintNameOffset(=SubLen+2)` /
  `PrintNameLength` 各 2 字节, **PathBuffer 从偏移 16 开始**;
  `ReparseDataLength = 8 + len(PathBuffer)`, 总长 `8 + ReparseDataLength`;
  SubstituteName 用 NT 命名空间 `\??\<绝对路径>`, 两段名字各自以 `\x00\x00` 结尾(长度不含结尾)。
  建完必须**回读验证**(`alias_kind_of == junction` + 穿透读一个文件), 不能只看调用返回值。
- **守阵**: `tests/test_alias_fs.py::test_junction_roundtrip`(Windows: 建 -> 形态识别 -> 穿透读 -> 删)、
  `test_probe_junction_platform`

### `WinError 1314` 有二义性: 长路径与「权限不足」同一个码

- **触发**: Windows 上建符号链接失败, 拿到 `1314 (ERROR_PRIVILEGE_NOT_HELD)`, 直接按「请提权」给用户文案。
- **判别**: 路径本身已 ≥260 字符时也会报 1314 —— 用户按文案提权后**依然失败**(同一码, 不同分支)。
  实测: 259 字符可建、260 起一律 1314, 带 `\\?\` 前缀同样失败; 而 ctypes 直调
  `CreateSymbolicLinkW` 可能返回成功但链接**不可见**。
- **处置**: 归因顺序固定 —— **先按路径长度分类**(`len(os.path.abspath(link)) >= 260` 一律判长路径,
  出路是改用目录别名或缩短路径), **再按错误码分类**(<260 且 1314/EPERM/EACCES 才判需提权)。
  顺序反了就是把长路径误诊成权限问题。单点: `infra/alias_fs.py::classify_link_failure`。
- **守阵**: `tests/test_alias_fs.py::test_classify_link_failure_order`(两条分支各一断言, 且注明
  「别拿长路径的 1314 冒充权限的 1314」)

### WSL 的 Windows 盘: fstype 是 `9p`, 「drvfs」只写在挂载选项里

- **触发**: 想按 `/proc/mounts` 的 fstype 判断「这块盘是不是 Windows 宿主提供的」(跨 OS 容器组合的
  闸门判据)。WSL2 内核 6.18 实测: `/mnt/d` 是 `9p`, `aname=drvfs;path=D:\;...` 在**第 4 列选项**里。
- **判别**: 只看 fstype 时 `/mnt/d` 与普通 9p 网络共享同形 -> 判成「本地盘」-> 漏掉「Linux 进程在
  NTFS 上建的链接 Windows 侧读不了」这条已实测的反例(WSL 里 `ln -s` 成功, Windows 侧 `open()` 报
  `Errno 22`、`os.path.islink` 为 False)。
- **处置**: 判据两条, 命中任一即「Windows 宿主提供」: ①挂载选项或 fstype 含 `drvfs`;
  ②WSL 里挂载点形如 `/mnt/<单个盘符>`(兜底, 不依赖选项文本)。Docker Desktop 的 `9p`/`virtiofs`
  共享挂载**不要**顺手归进来 —— 同一形态在 macOS 宿主上可用, 容器内分不出宿主 OS,
  记「未实测」而不是猜。单点: `infra/alias_fs.py::windows_backed_mount`。
- **守阵**: `tests/test_alias_fs.py::test_mount_info_and_windows_backed`(注入真实挂载表文本)、
  `test_probe_capability_notes_foreign_mount`(整机探测落到 `container_cross_os` 拒绝)
