# 26-10-18-backend-group-relocate-restart-free — 免重启整组迁移(A/C) P0 能力探测

**Status:** Done
**Added:** 2026-10-18
**Updated:** 2026-10-30
**Summary:** 免重启整组迁移实施档案: P0 能力探测(alias_fs) / P1 配置面 / P2 别名单元与只读预检 /
P3-P6 执行体+组判定+三入口+guardian 收尾已落地(Fake qB 全替身); P7 真机验收 12 步全过(含 5 缺陷修复+2 补强, 全量 3754 通过)
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
| S6 | 启动/热重载接线(P1 配置段 + P2 模块句柄到位后) | Done(R2) |
| S7 | 守阵 35 条 + 双平台实测证据 | Done(2026-10-18) |
| P3 | 执行体状态机(预检→暂停→搬→轮询→校验→建链→穿透→重归组→落账→武装→恢复) | Done(R9) |
| P4 | 组判定三层物理解析 + regroup + 搬迁窗口让路(扫描/跳检) | Done(R9) |
| P5 | 三入口接线(单件/批量/规则)+ 添加落点预检二次确认 + 金清单 | Done(R9) |
| P6 | journal 两本账 + guardian 独立进程 + 对账表 8 行 + 撤销成本确认 | Done(R9) |
| P7 | 真机验收(需 qB 环境: setLocation 真搬/收尾/backup 交叉验证) | 待他人(本机无 qB) |

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

### R2 · P1 + P2 落地 (2026-10-18)

- **P1**(R7 切片): RelocateConfig 9 键 + loader/校验/schema 段 + 段认领桩; 基线 26-10-18-2038。
- **P2**(R8 切片, 基线 26-10-18-2257): 新 `core/modules/relocate_units.py` 纯决策层
  (`plan()` 五行分流 + 长路径校正先于阈值 + `RelocateJob` 相位机值对象 + `evaluate_group()`
  组闸门 + `evaluate_add()` 添加预检三分流)与 `relocate_mod.py` 只读预检引擎
  (`relocate_precheck` / `precheck_add` / `capability_view` / 内存 job 登记表);
  `ctx.relocate` 句柄接线; 两条预检路由(403 门控 `relocate.enabled` fail-closed, 金清单
  82->84)与命令 handler(DEFERRED_RECEIPT, truth 带判定数据)。表驱动测试 40 例
  (test_relocate_units 21 + test_web_relocate 19), 覆盖 §3.2 五行 x 阈值 7/8/9 与
  §3.6 第 1/3/8/14/15 行; 全量绿(数字见 kb.baseline, 基线切片 26-10-18-2257)。
- **S6 接线已闭合**: start(enabled 才探, R15 口径: 开关关时开机建删探测链接属副作用)/
  apply(段变重探)挂在 RelocateModule。
- **实施期裁定两笔**: ①同卷证明闸门带写盘抖动容差(§2.4「完全相等」是观测口径, 做闸门
  必然间歇误拒; 容差 = max(2%, 1GiB)); ②长路径校正按 T6「内容根 <260 且**专属**」执行,
  §8.3 S3 的「提议目录别名」在组①(分集同目录不专属)场景落 blocked 而非 confirm ——
  与 §3.2 硬前提一致, S3 判据(force/blocked + 文案含关键词)仍满足, P7 真机时注意。

### R3 · P3-P6 落地 (2026-10-19)

用户指令「实施P3-6」= **P3–P6 整批**(经确认, 非 P3 单期); 验证口径同时确认「Fake qB 集成测试,
真机 qB 留待他人」—— 本机无 qB 测试环境, 所有 qB 交互经 `tests/helpers.FakeClient` 替身驱动。

**P3 执行体(relocate_mod 任务线状态机)**

- 相位推进挂在模块 `on_task_line`(任务线 hook): 每 tick 只做**一个可观测推进**, 不在一次调用里
  跑完整个迁移 —— 大种子搬运跨很多 tick, 卡主循环会让整库同步停滞(验收判据「单步 < 50ms」)。
- 搬: 暂停运行中成员 → 等自有暂停快照回流(`own_write_pending`) → 下发 setLocation(mover)。
  **重启后不重发**(会排队/覆盖): `_load_jobs` 恢复的 job 一律 `issue=False`。
- 完成判据不看 qB 的 save_path(它在下发后立刻就是新值, 不可用作「搬完」信号), 而是
  「qB 已不在 moving 且目标侧文件数/大小全对齐」。
- 停滞判据(D12): `stall_verdict(sample_grew, qb_moving, elapsed, warn_after, stall_timeout, stalled_for)` ——
  moving 期间**永不判失败**(再久只 warn 转 watching), 只有「不在 moving 且 dst 不增长」累计超时
  才 `failed(move_stalled)`; 失败零成本: 只落 reason, 不搬回、不动数据。
- 链接按形态建: 逐文件链接分块(200/tick, 单步有界), 目录别名一条; **第 k 条失败** ⇒ 删已建
  k-1 条 → `removed(alias_partial)` 进收尾路径(不搬回 —— 链接失败多是权限, 修好重试是零数据移动)。
- 穿透校验经**原路径**逐文件 stat; 失败保留链接现场(`failed(alias_unreadable)`), 便于排查。
- 收尾后: regroup_scope(scope, src, job.hashes)(含 mover —— 它的 save_path 已到 dst 但旧组键还挂在 src)
  → 落账 armed → 拉起 guardian → 恢复 resume_hashes。单成员组 direct 无别名无 guardian, 直接 done。

**P4 组判定(三层物理解析)**

- 第 1 层(零 syscall): 活跃 job 作用域登记表 → dst; 第 2 层: save_path **本身**是 junction/symlink
  才用 realpath(避免把 /tmp→/private/tmp 这类父目录解析当成换盘); 第 3 层: 代表文件是第三方
  文件链接/硬链接只**打标**(`store.third_party_link_groups`)不并组(组键形态表达不了任意目标)。
- 消费点单点: `_assign_to_group` 的组键首元、`_handle_save_path_changes` 的比较、跨组交叉检测的
  目录解析, 全部经 `_physical_dir`。
- 搬迁窗口让路: `store.relocating_hashes`(非终态 job 成员并集, 纯内存) 让 `_scan_triggered_groups`
  跳过整组缺文件扫描、让 ops 跳检直接 skip —— 否则「文件正被搬走」会被判成缺文件 ⇒ 整组暂停 + MISSING。

**P5 三入口**

- 单件/批量移动位置: 开关开 ⇒ `relocate_execute`(闸门 + 执行体), 回执 `truth={results, summary}`
  (started/skip/confirm/blocked); 开关关 ⇒ 原调用路径逐字节不变(守阵钉住)。
- 规则 `move_to`: 发起 / 幂等 skip / 需确认 skip(规则侧无交互, 不替用户点「目录别名以后新种子也落新位置」)
  / 拒绝 fail 四态; dry-run 不触发任何写。
- 幂等先于闸门: 同组同目标的 job 在途 ⇒ skip —— 规则每轮都会命中同一目标, 落到「未收尾拦截」会天天报失败。
- 添加对话框: 提交前 `/api/relocate/precheck-add`, confirm 时弹「请求路径 → 实际落点 → 卷剩余」,
  取消即不提交; 预检不可用(403/网络/判不出落点名)一律放行(它不是闸门)。投递点已登记进 triggers 金清单。

**P6 收尾**

- 两本账: state.json(主循环线程唯一写) + `<data_dir>/relocate/<job>.json`(guardian 唯一写);
  第三份 `.spec.json` 是 auto-qb 写给 guardian 的规格 —— **路径可能含非 ASCII, 不经命令行参数**。
- guardian: pid 锁 → 心跳 10s → 三证(qB 进程不在 + 端口拒连 + 稳定 30s) → 校验目标数据 →
  先落 journal(removing) 再逐条删链接(非递归) → removed。**绝不**搬数据/调 setLocation/改 state。
- 对账表 8 行(纯函数 `reconcile`): wait / respawn / reguardian_delete / revert_intent / rebuild /
  finalize / failed_gone / done_external + 超时兜底。journal 只**向前**合并(不覆盖 moved, 否则重建好的
  job 会被旧 removed 反复拉回收尾判定); 重建成功即把 journal 写回 armed。
- 撤销: 先给成本(字节数 + 从哪到哪), 用户确认后才删链接 + setLocation 回源 + 恢复运行态。

**实施期裁定三笔**

1. 「已被外部完成」判据用**全组**都到 dst(不是只看 mover): mover 本来就是本 job 搬过去的, 用它
   会让刚武装的 job 立刻被判 done。
2. 物理位置解析第 2 层只认「save_path 自己是链接」: 无条件 realpath 会把父目录符号链接(如
   `/tmp → /private/tmp`)误当成换了物理位置, 把同盘同目录的组拆开。
3. `plan()` 的空文件表判定**前移**到「单成员组 direct」之前: 文件表读不到是事实缺失, 不是
   「单成员组不需要别名」—— 否则 files API 故障时单成员组会被当 direct 放行。

**遗留(交他人/后续)**

- P7 真机验收: 需真实 qB(本机未配)。走查清单: ① 同卷两组各 2 文件 → 移动 → 组不裂、图面进度不清零;
  ② 9 文件专属子目录 → 目录别名确认框 → 搬完 `Get-Item` 看 junction; ③ 迁移中 kill auto-qb → 重启不重发、
  继续建链; ④ 迁移中退出 qB → guardian 30s 后删链接 → 起 qB → 成员 missingFiles → auto-qb 收尾 setLocation
  → 进度回 1; ⑤ 收尾窗口内从 qB 客户端加同名种子 → 下落点提示; ⑥ 撤销: 成本确认后才搬回。
- 「外部添加(qB 客户端直接加)」的落点提示: 本轮只覆盖 WebUI 添加对话框; 外部添加当前由
  「未收尾拦截 + 添加预检」间接兜底, 若需界面横幅提示另立 issue。
- 本机 `auto-qb-data/` 不因测试写入: 测试 env 已显式把 `data_dir` 指到 tmp(早期跑测残留的
  `relocate/*.spec.json` 已清理)。
