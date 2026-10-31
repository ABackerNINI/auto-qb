# 3754 —— 整组迁移 P7 验收后全量

> 摘要: 整组迁移 P7 验收后全量
> 基线时间: 2026-10-19 14:21
**Refs:** memory-bank/plans/26-10-18-1604-plan-group-relocate-restart-free.html

## 验收数字

```
[ok] test.full (136.9s)
  TOTAL                                                20504    376   6914    256    98%
  3754 passed, 2 skipped in 134.88s (0:02:14)
```

- 口径: `commands run test.full`(pytest + 覆盖率报表); TOTAL 行 = statements 20504 / miss 376 / branches 6914 / partial 256 / 覆盖率 98%; 汇总行 = 3754 passed, 2 skipped。
- 覆盖率门槛 98% 达标(实测 97.64% 四舍五入显示 98% 的轮次曾出现, 本轮 3754 全过且无 FAILED)。
- 相对上基线(26-10-18-1912 那轮)逐位差值不在此抄写, 用 `commands run kb.baseline -n 2` 看。

## 本改动面

本轮 = 整组迁移 P7 真机验收(计划 26-10-18-1604 §8.7)与其暴露缺陷的修复:

**产品代码(6 文件)**
- `infra/relocate_journal.py` `_alive`: Windows 改 OpenProcess+GetExitCodeProcess(旧 `os.kill(pid,0)` 在 Windows 等价 TerminateProcess, 会把在跑的 guardian 杀掉再报「已在跑」⇒ 重拉自噬循环)
- `tools/finalize_watch.py`: `_proc_absent` 改实例级(端点拒连 ⇒ 该实例已退出, 不再按全机进程名册); `_verify_dst` 走 `file_access`(长路径通道, 旧裸 os.path 在 265 字符 dst 上 OSError ⇒ 长路径组永不收尾)
- `core/modules/relocate_units.py`: `RelocateJob.scope_covers_dir`(只有目录别名按目录覆盖); `scope_hit` 逐文件链接只认 landing==scope、直搬恒不命中; `finalize_members` 同步收窄; `blocks_relocation` 作用域分支只对目录别名; `evaluate_add` 的别名作用域判定改本地口径(落点是否在作用域目录内)
- `core/modules/relocate_mod.py`: 同卷证明与源/目标任一侧吻合即成立(反向迁移 T→S 时 qB 报的是默认路径那块盘); 组键迁移诊断日志清理
- `core/modules/grouping_mod.py`: `_leave_group`/`_assign_to_group` 双向登记 `store.group_key_migrations`(组键迁移待办)
- `torrents/store.py`: 新增 `group_key_migrations` 字段(纯内存, 排空段消费)
- `webui/runtime.py`: `_drain_delta_locked` 见迁移待办即标本代 full(行级 delta 无法表达组键更换, upsert/removed 跨代抵消会吞旧键); flush_views 触发条件补「有 full 理由即重建」
- `webui/commands.py` + `webui/server/routes/torrent_cmds.py`: 新增 `relocate_cancel` 命令与 `POST /api/relocate/cancel`(§3.5.1 撤销迁移的 HTTP 入口, 成本两步)
- `config/{models,loaders}.py` + `config/schema/groups.py` + `config/validation/sections.py`: 新增 `qbittorrent.api_key`(qB 5.x API Key, Bearer 直连)
- `config/writer.py`: `api_key` 纳入敏感键掩码
- `core/qbclient.py`: api_key 透传给 qbittorrentapi

**测试(8 文件)**
- `test_webui_delta.py`: 新增 `test_group_key_migration_old_removed_new_upsert`
- `test_relocate_units.py`: 新增 `test_scope_hit_flat_does_not_cover_subdirs`; 扩 `test_evaluate_group_unfinished_job_blocks`(目录别名 vs 逐文件 vs 同组) 与 `test_resolve_physical_and_finalize_members`(收尾集合收窄)
- `test_relocate_paths.py`: `_proc_absent` 实例级 + `_alive` 零副作用回归
- `test_grouping.py`: 组键迁移待办登记
- `test_web_relocate.py`: 撤销路由(403/400/入队形状) + drain 两步走 + 目录级链接误报回归
- `test_web_route_manifest.py`: 冻结清单 84->85(撤销端点)
- `test_config_key_surface.py`: `qbittorrent.api_key` 往返
- `test_relocate_exec.py` / `test_relocate_paths.py` 既有用例随修复口径同步

**文档**
- `memory-bank/plans/26-10-18-1604-...html`: 新增 §8.7 P7 真机执行记录 + R10 变更记录
- `memory-bank/config-reference/keys.md`: `qbittorrent.api_key`
