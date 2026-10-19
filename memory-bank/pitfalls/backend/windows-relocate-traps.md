# Windows 进程探测/长路径/组键迁移三处陷阱

> 摘要: Windows 进程探测/长路径/组键迁移三处陷阱>   
> 触发: os.kill, TerminateProcess, guardian, 进程探测, 长路径, os.path.getsize, 组键迁移, 增量视图, 孤儿行, scope_hit

### `os.kill(pid, 0)` 在 Windows 会**杀掉**被探测进程 —— 进程存活探测自噬循环

- **触发**: 任何「探测 pid 是否还活着」的代码在 Windows 上用 `os.kill(pid, 0)`（POSIX 惯例写法）。Windows 上 `os.kill` 对非 `CTRL_*` 信号一律走 `TerminateProcess(handle, sig)` —— sig=0 就是「以退出码 0 结束」。
- **判别**: 被探测的长驻进程（如 relocate guardian）反复消失、日志周期性出现「心跳过期/重拉」、状态机永远停在 armed；`tasklist` 里该进程的 pid 一直在换。
- **处置**: 纯探测走 `OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION)` + `GetExitCodeProcess`（==259 STILL_ACTIVE），`CloseHandle` 收尾；POSIX 分支保留 `os.kill(pid, 0)`。单点实现在 `infra/relocate_journal._alive`。
- **守阵**: `tests/test_relocate_paths.py` 的 `_alive(os.getpid()) is True`（旧实现会当场终止测试进程）。

### 裸 `os.path` 处理超过 MAX_PATH 的路径 —— 长路径组的收尾永远不触发

- **触发**: 功能本身就是为了「285 字符长路径」而存在，但校验/收尾环节用 `os.path.isfile` / `os.path.getsize` 裸调用（Windows 上 >259 字符 OSError）。
- **判别**: 短路径组收尾正常（journal → removed），长路径组卡在 `failed(reason=verify_mismatch)` 或 `armed`；错误只在「目标侧路径 >260 字符」时出现。
- **处置**: 一律走 `file_access.get_file_access()`（`exists`/`getsize` 内部加 `\\?\` 前缀）或 `utils.add_long_path_prefix_for_win`；`os.walk` 同样要用前缀根，否则子目录静默不被遍历（写基线/比对脚本时也会踩）。
- **守阵**: `tests/test_relocate_paths.py::test_guardian_helpers` + S7 真机断言（285 字符 stat == qB 上报大小）。

### 组键迁移（save_path 变化 / 武装重归组）后 WebUI 组从视图消失或出现重复行

- **触发**: 组键是 `(物理目录, 文件元组)` 派生值 —— 迁移/回滚/重归组会让它**更换**；WebUI 增量视图的脏行推导只认 `member_to_key`（新键），旧键行既不在 upsert 也不在 removed；而 upsert/removed 桶的跨代抵消（R5）又会把「先 upsert 后 removed」的同键两清。
- **判别**: 迁移/撤销后 `/api/groups` 少一组或同组成员出现两行（旧键+新键）；重启 auto-qb 后恢复正常（全量重建）；store 侧 `groups/member_to_key` 实际自洽。
- **处置**: 归组路径（`_leave_group`/`_assign_to_group`）把旧/新键登记进 `store.group_key_migrations`；WebUI 排空段见待办即标**本代 full**（与 `row_key_unresolvable` 同口径，保守正确优先），并让「有 full 理由」本身触发一次重建（纯重键轮可能不伴随 `view_changed`）。
- **守阵**: `tests/test_webui_delta.py::test_group_key_migration_old_removed_new_upsert`。

### 作用域解析把「同 save_path 的别组」当成自己人 —— 单成员 direct 误判

- **触发**: `RelocateJob.scope` 对平铺组就是 save_path、对 direct 组就是内容根；`scope_hit` 若一律按「落在 scope 目录内」判定，会把同目录**别的组**的组键解析到 T。job 结束（终态）后 `_buckets` 用 S 键查不到组，退化为「仅本次选中成员」⇒ 多成员组被当单成员 direct 直搬（数据走了却不建链接，组裂）。
- **判别**: 迁移回执 `form=direct` 但 `hashes` 只有 1 个（组内实际 2 个）；`_finish_direct` 后另一成员的 save_path 仍指 S 而文件已不在。
- **处置**: `scope_covers_dir` 谓词 —— 只有**目录别名**（`alias_kind=="dir"`）才按目录覆盖；逐文件链接只认 `landing == scope`；直搬恒不命中；`finalize_members` 同步收窄（否则收尾会把同目录别组一并 setLocation 到 T）。
- **守阵**: `tests/test_relocate_units.py::test_scope_hit_flat_does_not_cover_subdirs` + `test_resolve_physical_and_finalize_members`。

### 守护进程「qB 不在」的证明按全机进程名册判 —— 同机多实例时永远凑不齐

- **触发**: 机器上同时跑着多个 qB（日常库 + 测试库，或容器内外），`_proc_absent` 用 `tasklist` 全机名册判「有没有 qbittorrent 进程」⇒ 恒「在」。
- **判别**: guardian 心跳正常但 journal 永远 `armed`；端口 36595 已无监听，`tasklist` 里仍有另一个 qbittorrent.exe。
- **处置**: 实例级判定 —— 端点（host:port）拒连即「该实例已退出」（同机别的 qB 与此无关）；无端口可判时才退回全机名册。
- **守阵**: `tests/test_relocate_paths.py::test_guardian_helpers`（`_proc_absent(("qbittorrent.exe",), "127.0.0.1", 1) is True`）。

