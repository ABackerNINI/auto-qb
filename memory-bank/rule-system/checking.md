# checking 动作 (高风险)

> 摘要: `CheckAction` 的决策链与七道防护 —— 高风险动作单独成篇, 与 pitfalls/backend/high-risk-ops.md 互指。
> 触发: checking, 校验, full-checking, skip-checking, 跳检, 七道防护

## `checking` 动作 (rules/actions/checking.py 的 CheckAction, 决策链; full_checking.py/skip_checking.py 以 Mixin 组合进 CheckAction)

配置 (dict, fail-fast 校验, 未知键报错):
```yaml
- checking:
    basic_check: filelist            # filelist | piecehashes | custom (必填)
    custom_basic_check_program_path: prog.exe   # basic_check=custom 时必填; 参数: <hash> <保存路径>, rc=0 即为参考
    # skip_checking_tag 不在 checking spec 配置(全局统一, 校验层列为 spec 未知键): 跳检成功后打的标签, 带此标签者不作参考, 标签名 = 全局 config.skip_checking_tag
    with_reference:                  # 有参考种子段 (enabled/mode/auto_start)
        enabled: true
        mode: skip-checking          # skip-checking | full-checking
        auto_start: true
    without_reference:               # 无参考段 (结构同上; 无参考 skip-checking = 高风险)
        enabled: true
        mode: full-checking
        auto_start: true
```

决策链 (execute):
0. **只校验"暂停中未完成"种子**: `state_enum.is_stopped and progress < 1.0`; 已完成/活跃中一律 skip (防已完成种子被反复校验)。
1. 组内有活跃下载种子 (`_group_has_downloading`: is_downloading 且非 stopped 非 checking) → skip (整组未完成, 任何校验都不做)。
1.5 **组内校验串行** (`_wait_for_group_checking`): 组内其它成员 full-checking 在途 (`task_queue.active_check_hashes()` 或 store checking 态) → 让位等待 (返回 pending 规则断点让出, 创建 check-wait 等待任务轮询, 清空后 `add_task(origin)` 默认重置重走完整决策链; 等待任务独立 kind="check-wait" 普通入队, 不占 `_active_checks` — 否则多个等待成员互相视为校验中而互等, 仅超时可解)。组内共享同一物理文件, 并行全量校验只有重复 I/O; 成功者晋升 verified_references 后等待者自然命中参考。
1.6 **失败推断** (`_skip_on_group_check_failed`): 组内其它成员当日校验失败 (`recheck_fails`) 且两者文件映射一致 (`store.group_sizes[key]` 相等 = 同一物理数据) → skip ("校验结果必然相同"); 映射不一致不推断。
2. `_find_reference`: 按.basic_check 从组内参考候选 (`_group_reference_candidates`: is_complete 且非 checking — 暂停/停止做种的完成成员亦是有效参考, 参考用元数据 filelist/piece hashes 与暂停状态无关; 校验中 checkingUP 完整性存疑排除) 筛选 — `filelist`: 全部候选 (分组已保证文件列表相同); `piecehashes`: `torrents_piece_hashes` 与目标完全一致者; `custom`: 外部程序 rc=0 者。**再并入** `store.verified_references` 中同组成员 (历史 full-checking 通过者, 仅内存)。排除自身, 按 hash 去重。**带 `skip_checking_tag` 标签的种子(跳检成功, 未经哈希校验)一律排除** — 候选筛选与去重出口两处统一过滤 (`_is_tagged`), 防止"未验证"经参考链传播; 标签名运行时经 ctx 读全局 `config.skip_checking_tag` (`CheckAction._skip_tag`, 全局统一不按规则覆盖, spec 配同名键被校验拒绝; 默认值唯一来源在 config models, 动作类不硬编码常量)。
3. 有参考 → with_reference 段; 无参考 → without_reference 段; `enabled: false` → skip。
4. **前置检查** (两模式都强制): `manager.check_filelist` — 磁盘文件全部存在且大小一致, 未通过 skip。

**full-checking** (`_execute_full_checking`): 先 `add_task` 登记 check 轮询子任务 (interval=2s, 自动登记 `_active_checks`, 决策链 1.5 依赖; 重复提交返回 False → skip), 再同步发 `torrents_recheck` (发送失败返回 fail, 子任务下轮轮询自愈) → 返回 pending (规则断点, 本轮不重入队) → 见 systemPatterns.md 的完整时序。成功: `on_success()` 自行触发 (`verified_references.add` + auto_start) + `add_task(origin, keep_progress=True)` 续跑; 失败/异常/种子删除: `add_task(origin)` 默认重置重走决策链 (删除时由 origin 的删除守卫判死)。外部入口 (ctx 无 task) 不创建 origin, 轮询子任务仍工作但无规则可恢复。**事件规则 (trigger=on_*)** 的 origin 是 `_apply_event_rule` 传入的 rule-event 一次性任务 (非 None), 校验成功后由 `add_task(origin, keep_progress=True)` 重新入队, 下 tick `_handle_event_rule` 从断点续跑事件后续动作 — 事件触发的 checking 由此获得完整断点续跑语义, 与 interval 规则完全一致。

**skip-checking** (`_execute_skip_checking`, 高风险; 2026-09-06 重构为四阶段编排, 拆分为 `_skip_gates`/`_skip_delete`/`_skip_readd` 小函数 + `_poll_until` 轮询 helper + `store.restore_torrent` 快照恢复):

**阶段 1 前置闸门** (`_skip_gates`, 任一不过 → fail/skip 返回, 无副作用):
- 部分下载禁止跳检 (0<progress<1 → fail 提示改 full-checking; 预分配零块会被标记有效上传)
- 跨规则同日去重 (`skip_check_day[hash]==today` → skip; 多条规则都配 checking 时统计只丢一次; 顺带清理非当日记录防 state 无界增长)

**阶段 2 准备** (记录仍在, 均须删除前完成):
- `torrents_export` 导出 .torrent (失败/为空 → fail, 无损失)
- 拷贝 6 个属性 (`seq_dl/f_l_piece_prio/ratio_limit/seeding_time_limit/inactive_seeding_time_limit/share_limit_action`; 任一缺失 → fail, 不删除种子)
- `_infer_content_layout` 由 content_path/save_path/文件列表推断布局 (contentLayout 错位在跳检下不自愈)

**阶段 3 执行**:
- `torrents_delete(delete_files=False)` 删除种子 (失败 → fail, 无损失)
- `_poll_until` 确认种子已从客户端消失 (10×0.5s); 未消失 → 放弃 (重加会撞"种子已存在", 种子仍在无损失)
- 删除**之前** `.torrent` 落盘 `skip-check-backup/` + 元数据**立即落盘** (崩溃安全: 删除是第一个不可逆步骤, 备份挂在重加失败路径上时, 「删除已生效 → 重加未被接受」缝隙内崩溃会什么都不剩 —— issue 26-09-21-1347 已修); 备份写不进去则**不删除**直接 fail (无损失)
- `torrents_add(is_skip_checking=True, is_stopped=True)` 重加, 保留 save_path/category/tags/up_limit/dl_limit + 6 属性**直传** (0/负值有语义, 不得 `or None` 吞掉) + contentLayout; 失败 → 保留备份 → fail 提示手动恢复
- `_poll_until` 确认新种子出现 (3×0.3s), 未出现 → fail (保留备份)
- 重加确认成功 → `_clear_backup` 清掉备份文件 + 元数据 (立即落盘); 删除未生效 (种子仍在) 同样清理
- **`store.restore_torrent(torrent)` 恢复删除前快照记录** (tracker_conf/惰性缓存保留): `remove_torrent` 保留 `_known_hashes`, 重加的同 hash 种子不进 added 列表, 不恢复则永久未匹配 (生产 BUG 2026-09-06 已修)
- 记录 `skip_check_day[hash]=today` (跨规则同日去重写入)

**阶段 4 收尾**: 无参考 → warning (高风险); **跳检成功打标签** (标签名运行时经 ctx 读全局 `config.skip_checking_tag` (`_skip_tag`), 默认 zSkipChecked, 全局统一不按规则覆盖; `tag not in torrent.tags_set` 时经 Facade `torrents_add_tags` 打标并同步 store; 打标失败 try/except 仅 warning, 不影响跳检成功结论; 标签为空则跳过打标); `auto_start` → `torrents_start`。标签持久化在种子上 (跨重启), 后续 `_find_reference` 据此排除跳检种子作参考。

**风险须知** (写文档/日志时要传达): 跳检保留标签/分类/限速/路径, 但**丢失下载量/上传量/做种时长/分享率**; 文件内容错误会上传垃圾数据。另注意: 删除种子 → `store.remove_torrent` 立即从快照移除, 该种子后续动作/任务需容错 (这正是 commit e5ea9e7 修的 bug, 测试 test_checking.py 有覆盖)。 跳检重加成功后 `_execute_skip_checking` 会 `store.restore_torrent` 恢复删除前记录 (跳检流程内部); 其它路径下 `tracker_conf=None` 时 `tracker_name` 返回 "Unknown" (不回退 tor.client, 生产 TorrentDictionary 无此属性)。
