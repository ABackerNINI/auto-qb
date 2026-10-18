# 26-10-18-backend-group-relocate-restart-free — 免重启整组迁移(A/C) P0 能力探测

**Status:** In Progress
**Added:** 2026-10-18
**Updated:** 2026-10-18
**Summary:** 免重启整组迁移 P0 落地: 新 `infra/alias_fs.py` 真建真删式能力探测(junction/目录与文件 symlink/硬链接/同卷/容器/UNC/跨 OS 挂载) + 链接原语 + §3.3 能力矩阵纯函数; Windows 与 WSL 双平台实测对齐 §2.4; 启动/热重载接线随 P2
**Topics:** backend-group-relocate-restart-free
**Refs:** memory-bank/plans/26-10-18-1604-plan-group-relocate-restart-free.html, memory-bank/pitfalls/backend/alias-links.md, memory-bank/testing/baselines/26-10-18-1940-group-relocate-restart-free-p0.md

## 原始请求

1. 「实施P0:26-10-18-1604-plan-group-relocate-restart-free.html」—— 按计划 §04 的 P0 行开工, 其余期(P1-P7)不在本轮。

## 思考过程与决策

计划 P0 的验收判据是「探测函数覆盖 §3.3 七行组合(含 WSL-on-NTFS 反例); Windows 真机跑一次输出与
§2.4 表一致; WSL 里跑一次 POSIX 分支」。据此定了五条:

1. **探测必须真建真删, 不查平台/版本**: §2.4 已三次否掉「按平台推断」—— 本机开发者模式开着时
   `os.symlink` 全成功, 但用户环境未必; WSL 建链成功而 Windows 侧读不了; ctypes 直调可能「返回成功
   但链接不可见」。故每个探测都是「建 -> 校验可见 -> 校验可穿透读 -> 删」, `create` 的返回值不作数。
2. **`try_create` 是唯一注入点**(§8.6): `probe_symlink/probe_hardlink/probe_junction` 各带一个
   `try_create`(默认真实现), 不给分支留开关 —— 单测注入抛 `OSError(1314)` 的替身走**生产分支**。
   注意 `try_create=None` 在函数体内解析成 `os.symlink`, 而不是写成默认值: 默认值在 import 期绑定,
   会绕过测试期 sidefx 对 `os.symlink` 的记账。
3. **junction 走 DeviceIoControl, 不走 `mklink /J`**: 起子进程既是外部副作用(sidefx 的 POPEN 类),
   又把 Unicode 路径塞进命令行 —— §3.3 明确要求 Unicode 路径不经命令行参数。实测踩到一次
   `REPARSE_DATA_BUFFER` 布局错误: **MountPointReparseBuffer 没有 Flags 字段**(那是
   SymbolicLinkReparseBuffer 才有的), 多写 4 字节会把 PathBuffer 冲掉 -> 已记坑档。
4. **跨 OS 反例的判据不能只看 fstype**: 本机 WSL 把 Windows 盘挂成 `9p`, 「这是 drvfs」只写在
   挂载选项里(`aname=drvfs;path=D:\;...`)。只看 fstype 会把它当普通 9p 共享, 于是漏掉 §2.4 那条
   反例。判据改为「挂载带 drvfs 标记」或「WSL 里挂在 `/mnt/<单个盘符>`」。
5. **启动/热重载接线随 P2**: P0 只交付 `get_capability(refresh=True)` 这个单点缓存入口。真正调用点
   要挂在 P2 的 `RelocateModule` 上(P1 才建配置段, P0 阶段没有 `relocate.enabled` 可判); 而
   **开关默认关时开机就建删链接属于「为关着的功能做副作用」**, 违反黄金法则 2(保守默认)。
   残留项已写进子任务表 S6。

## 实现计划

1. **S1 平台事实层**: `_process_os`(走 `utils.is_*` 单点) / `container_evidence` / `is_wsl` /
   `mount_info_for_path` + `windows_backed_mount` / `is_unc` / `same_volume` / `volume_free`。
2. **S2 单项探测**: `probe_symlink`(文件/目录) / `probe_hardlink` / `probe_junction`, 统一
   「建-可见-穿透-删」四步 + `classify_link_failure`(先按路径长度再按错误码, 解 1314 二义性)。
3. **S3 链接原语**: `create_dir_alias` / `create_file_alias` / `alias_kind_of` / `alias_target` /
   `remove_alias`(非递归, 绝不跟随链接删目标)。
4. **S4 能力矩阵**: `AliasCapability`(含 `dir_alias_kind` / `file_alias_kind(same_volume)` 阶梯) +
   `platform_verdict()` 把 §3.3 七行落成纯函数(P2 闸门调用, 不另写一遍)。
5. **S5 整机探测与缓存**: `probe_capability(work_dir)`(按卷探测, 不抛异常) / `get_capability(refresh)`
   / `reset_capability_cache`。
6. **S6 接线(Open)**: 启动一次 + 配置热重载重探 —— 等 P1 配置段与 P2 模块句柄。

## 子任务状态表

| 步 | 内容 | 状态 |
|---|---|---|
| S1 | 平台事实层(容器/WSL/挂载表/UNC/同卷/剩余空间) | Done(2026-10-18) |
| S2 | 单项探测 + 失败归因(1314 二义性) | Done(2026-10-18) |
| S3 | 链接原语(建/读/删, 非递归) | Done(2026-10-18) |
| S4 | §3.3 能力矩阵纯函数 + 形态阶梯 | Done(2026-10-18) |
| S5 | 整机探测(按卷) + 缓存入口 | Done(2026-10-18) |
| S6 | 启动/热重载接线(P1 配置段 + P2 模块句柄到位后) | Open |
| S7 | 守阵 35 条 + 双平台实测证据 | Done(2026-10-18) |

## 进度日志

### R0 · 立档 (2026-10-18)

按计划 P0 行落地 `src/auto_qb/infra/alias_fs.py`(486 语句) 与 `tests/test_alias_fs.py`(35 条守阵):

- **Windows 真机**(H: / R: 两块盘各探一次): junction / 目录 symlink / 文件 symlink / 同卷硬链接
  四项全可建, 提权通道可用, `dir_alias=junction`、`file_alias(同卷)=hardlink`、`file_alias(跨卷)=symlink`
  —— 与 §2.4 表逐项一致; `same_volume(R:/Download/Testing, R:/)=True`、`H: vs R:=False`、
  不可读路径=None(不可判定, 不是「不同卷」)。
- **WSL(Ubuntu-26.04 / 内核 6.18.33.2)**: `/tmp` 走 POSIX 分支(symlink 可建、junction 明确「仅
  Windows」); `/mnt/d`(9p + `aname=drvfs`)判 `link_visible_to_host=False` -> `platform_verdict`
  落 `container_cross_os` 并拒绝 —— 即 §3.3 第 6 行反例, 与 §2.4 的 `Errno 22` 实测对上。
- 证据四元组式留证在 `tmp-analysis/relocate-e2e/`(不入库): `p0-windows.json` / `p0-wsl.txt`。
- 全量测试见 `commands run kb.baseline` 最新切片; 本轮新增 35 条用例。
- 踩坑一条已入池: `pitfalls/backend/alias-links.md`(reparse 结构无 Flags / 1314 二义性 /
  drvfs 只在挂载选项里)。

### R1 · 收尾 (2026-10-18)

全量测试绿、基线切片与坑档已出(数字只写基线切片, 见 `commands run kb.baseline`); 切片
`activeContext/26-10-18-0822-group-relocate-restart-free.md` 追加 R6。**残留**: S6 接线(启动一次 +
配置热重载重探)待 P1 配置段与 P2 模块句柄 —— 届时只需在 `RelocateModule` 的构造/热重载回调里调
`alias_fs.get_capability(refresh=True)`, 探测与缓存本身已就绪。
