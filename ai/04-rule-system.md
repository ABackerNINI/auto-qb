# 04 规则系统详解

> 代码: `rules/base.py` (Rule/RuleContext/ActionResult), `rules/conditions.py`, `rules/actions.py`, `rules/registry.py`; 调度: `mixins/rule_engine.py`; 配置加载: `config.py` (`rules_config`)。

## 规则的定义与绑定

- 配置中 `config` 段下**所有以 `_rules` 结尾的键**是规则集: `{规则集名: {规则名: spec}}` → Rule 全名 `{规则集名}.{规则名}` (如 `example_rules.rule1`)。
- 规则加载在 `run()` 中 (`_load_rules`), **不在构造时** (`--export-yaml` 模式不需要)。
- tracker 通过 `rules: ["@规则集", "@规则集.规则名"]` 引用规则 (`_resolve_refs` 按名称去重)。
- **规则是种子级任务**: 新种子被检测到时, 为其匹配 tracker 引用的每条规则各建一个 Task (kind=rule, interval=规则自身的 interval, 默认 0 → 归一化为每 tick)。未匹配 tracker 配置的种子不创建任何任务。
- 规则执行 = 该 Task 到期 → `_handle_rule` → 构造 `RuleContext(manager, client, config, hash, dry_run, task=task)` → `rule.process(ctx)`。

## 触发时机 (trigger)

| 触发 | 状态 | 说明 |
|------|------|------|
| `interval` | ✅ 已实现 | 规则任务按自身 interval 循环; `spec["interval"]` 解析为秒 |
| `on_torrent_state_changed` / `on_torrent_added` / `on_torrent_deleted` | 🚧 规划中 | 尚未实现 (见 09-roadmap) |

注: `trigger` 键目前实际未从 spec 读取 (默认行为即 interval 循环), 规划中的键不要在代码中假设存在。

## Rule.process() 执行语义 (base.py, 核心函数)

```
process(ctx) -> (handled: bool, stop: bool)
```

1. **断点续跑**: 若 `ctx.task.resume_index` 非空 → 读取并清零, **跳过条件评估与去重**, 直接从断点动作继续 (用于 full-checking pending 后的恢复)。
2. **条件评估**: `matches()` = 所有条件 AND; 条件抛异常 → warning + 视为不匹配 (`handled=False, stop=False`)。
3. **去重**: `_dedup_allowed` (见下节) 不通过 → 不执行。
4. **动作顺序执行**:
   - `ActionResult.ok` → `ok_action=True`, 记录日志继续。
   - `ActionResult.skip` → 不算失败, 继续 (如标签已存在)。
   - `ActionResult.fail` → `failed=True`; 若该动作未设 `ignore_error` → **break** 中断后续动作。
   - `ActionResult.pending` → 任务队列驱动时: 记录 `task.resume_index = i+1`, 返回 `(True, True)` 中断 (校验轮询任务完成时 resume/reschedule); 无任务时视为成功继续。
5. **执行历史**: `ok_action` 且非 dry_run 且有动作 → `manager.record_execution(name, hash)` (幂等去重依据)。注意: 只要有任一动作成功就记录, 包括后续动作失败的场合 (断点续跑时 ok_action 初始为 True)。
6. **stop 计算** (`stop_following_rules_if`): `conditions-met`(默认, 匹配即停) / `always` → stop=True; `action-failed` 且 failed → True; `all-actions-succeed` 且 not failed → True; `conditions-not-met` → 不匹配时 stop=True; `never` → 永不停。
7. 返回 `handled`: `not result.is_skipped` (最后一个动作非 skipped); 空循环(断点后无动作)时返回 `ok_action`。

### 去重语义 (`execute_once` / `cooldown`)

- `execute_once: never`(默认) 且 `cooldown: 0S` → 每次条件满足都执行, **只适合幂等动作** (加/删标签、设分类)。
- 非幂等动作 (校验/开始/强制汇报/限速) 必须配 `execute_once: once/daily/hourly` 或 `cooldown`。
- `cooldown` 优先于 `execute_once` 粒度: 距上次执行成功不足 cooldown 则跳过。
- 记录键: `state["exec_history"]["{rule_name}:{hash}"] = {ts, date, hour}`; `daily` 按自然日切换 (与 upload_size_today 口径一致), `hourly` = 同日同小时。
- 另有**独立于规则去重的兜底**: `CheckAction` 跳检自带同日去重 (每规则每种子每天最多跳检一次)。

### ActionResult 四态

| 状态 | 含义 | 对 stop_following_rules_if=action-failed 的影响 |
|------|------|------|
| `success` | 动作执行成功 (dry-run 也返回 success) | 不算失败 |
| `skipped` | 条件不满足未执行 (标签已存在/已设置/状态不符/段未启用) | 不影响 |
| `failed` | API 非 200 / 抛异常 / 前置检查未通过 | 触发 |
| `pending` | 已提交等待异步完成 (仅 full-checking), 规则中断待恢复 | 中断执行流 |

`ignore_next_action_error: true` 是伪动作: Rule 构造时解析, 给**下一个**动作设 `ignore_error=True`, 失败不 break 继续执行。

## 15 种条件 (conditions.py, 全部 `match(ctx) -> bool`, 组内与组间逻辑见各条)

| 条件 | spec 示例 | 语义要点 |
|------|-----------|----------|
| `path` | `/path` 或列表 | 匹配 save_path **或** content_path; `match_path_patterns`: 精确(规范化斜杠后全等)/`regex:` 前缀(re.search)/`:ignore_case` 后缀 |
| `size` | `">=100MiB"` | parse_compare + parse_fsize; 比较种子 size |
| `tags` | `["tag1,tag2", "tag3"]` | 列表=组间**或**; 组内逗号分隔=**与**; 支持 `regex:` 与 `${required_seeding_time}`; ⚠️ 暂不支持 `:ignore_case` (TODO) |
| `category` | `["cat", "regex:^HR"]` | 或关系; 精确=全等, regex=search; ⚠️ 暂不支持 ignore_case |
| `trackers` | `["tracker1"]` | 匹配 tracker_conf.name (配置名, 非域名); 或关系; ⚠️ 暂不支持 ignore_case |
| `state` | `["is_complete&is_uploading"]` | 组内 `&` 连接为与, 组间或; 直接取 `state_enum` 枚举属性 (is_checking/is_downloading/is_complete/is_uploading/is_errored/is_stopped) |
| `hr` | `"condition-met"` | `condition-met`(满足触发条件) / `condition-not-met` / `satisfied`(触发+做种时长或分享率达标); 依赖 tracker_conf.hr, 无 HR 配置一律 False |
| `date_time` | `{day_of_month: 1-31, day_of_week: 1-7, time: "10:00-23:00"}` | 全部可省略(省略=不检查); 区间 `a-b` 或单值; time 支持跨午夜; day_of_week 用 isoweekday (1=周一) |
| `seedtime` | `"<24H"` | 比较 seeding_time (秒) |
| `upload_ratio` | `">1.5"` | 比较 ratio |
| `upload_size` | `">10GiB"` | 比较 uploaded (总) |
| `upload_size_today` | `">10GiB"` | 基于 state_file 基线的自然日增量 (`upload_delta(kind=daily)`) |
| `upload_size_this_week` | 同上 | ISO 周增量 |
| `upload_size_this_month` | 同上 | 自然月增量 |
| `freespace` | `{path: "R:/", amount: "<100GiB"}` | shutil.disk_usage; path 为空/OSError → False |

比较表达式统一: `> < >= <= == = !=` 前缀, 缺省 `==`; 值解析失败在构造时抛 (fail-fast)。

## 11 种动作 (actions.py, 全部 `execute(ctx) -> ActionResult`)

| 动作 | spec 示例 | 要点 |
|------|-----------|------|
| `add_tags` | `["tag-${required_seeding_time}"]` | 已存在则 skip; 变量替换 |
| `remove_tags` | `["regex:^tag", "tag2"]` | 正则/精确匹配现存标签; 无匹配 skip |
| `add_category` | `{format: "cat", overwrite: false}` | 已设置→skip; 不覆盖且已有分类(且非本程序上次自动设置)→skip; 分类不存在先 create (走 store 缓存); 成功后记 `state["auto_categories"][hash]` |
| `remove_category` | `true` | 分类为空 skip |
| `start` | `true` | 非 `is_stopped` → skip("已开始") |
| `stop` | `true` | 已 `is_stopped` → skip |
| `checking` | 见下节 | 校验/跳检, 最复杂动作 |
| `move_to` | `{path: "/new"}` | set_location; path 空 → fail |
| `reannounce` | `true` | ⚠️ 有风险: 运行时最小间隔 10M(同种子, state 键 `reannounce_ts`, 独立于规则去重兜底) + 暂停种子跳过 + 未配 execute_once/cooldown 时加载 WARNING; 高频 announce 会被封号 |
| `upload_speed_limit` | `"1000KiB/s"` | 见下"限速保护" |
| `download_speed_limit` | 同上 | 同上 |

### 限速的"单数值保护" (tracker.py 与 actions.py 同逻辑)

```python
if (current_limit / 1024) % 2 == 1:   # 当前限速为奇数 KiB/s
    return ActionResult.skip("用户已设置")  # 视为用户手动设置, 不覆盖
```
用户约定: 手动设置且不希望被覆盖时限速用奇数 KiB/s (如 2001KiB/s)。全局限速曲线同样尊重奇数 (cur > 0 and cur % 2 == 1 → 跳过该方向)。

## `checking` 动作 (actions.py CheckAction, 决策链)

配置 (dict, fail-fast 校验, 未知键报错):
```yaml
- checking:
    basic_check: filelist            # filelist | piecehashes | custom (必填)
    custom_basic_check_program_path: prog.exe   # basic_check=custom 时必填; 参数: <hash> <保存路径>, rc=0 即为参考
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
2. `_find_reference`: 按.basic_check 从组内参考候选 (`_group_reference_candidates`: is_uploading 且非 checking) 筛选 — `filelist`: 全部候选 (分组已保证文件列表相同); `piecehashes`: `torrents_piece_hashes` 与目标完全一致者; `custom`: 外部程序 rc=0 者。**再并入** `store.verified_references` 中同组成员 (历史 full-checking 通过者, 仅内存)。排除自身, 按 hash 去重。
3. 有参考 → with_reference 段; 无参考 → without_reference 段; `enabled: false` → skip。
4. **前置检查** (两模式都强制): `manager.check_filelist` — 磁盘文件全部存在且大小一致, 未通过 skip。

**full-checking** (`_execute_full_checking`): 同步发 `torrents_recheck` → 规则任务 defer + 返回 pending → 创建 check 轮询任务 (interval=2s, add_check_task 去重) → 见 02-architecture 的完整时序。成功 resume: `verified_references.add` + auto_start + 规则续跑; 失败/删除/异常: 清断点 reschedule 重走决策链。无 task_queue (旧用法) 时退化为仅发请求不跟踪。

**skip-checking** (`_execute_skip_checking`, 高风险):
1. 同日去重 (`get_exec_record().date == today` → skip, 独立于规则 execute_once)。
2. `torrents_export` 导出 .torrent (失败/为空 → fail, 无损失)。
3. 拷贝 6 个属性 (`seq_dl/f_l_piece_prio/ratio_limit/seeding_time_limit/inactive_seeding_time_limit/share_limit_action`; 任一缺失 → ValueError → fail, 不删除种子)。
4. `torrents_delete(delete_files=False)` 删除种子。
5. `torrents_add(is_skip_checking=True, is_stopped=True)` 重加, 保留 save_path/category/tags/up_limit/dl_limit + 上述 6 属性; 失败 → .torrent 落盘 `skip-check-backup/` + 元数据记入 state → fail 提示手动恢复。
6. 轮询确认新种子出现 (3 次 × 0.3s), 未出现 → fail。
7. 无参考 → warning (高风险); `auto_start` → `torrents_start`。

**风险须知** (写文档/日志时要传达): 跳检保留标签/分类/限速/路径, 但**丢失下载量/上传量/做种时长/分享率**; 文件内容错误会上传垃圾数据。另注意: 删除种子 → `store.remove_torrent` 立即从快照移除, 该种子后续动作/任务需容错 (这正是 commit e5ea9e7 修的 bug, 测试 test_checking.py 有覆盖)。

## 状态映射表 (state 条件与 qB 枚举)

`TorrentRecord.state_enum = TorrentState(state字符串)`, 条件用枚举布尔属性判定 (与 qB 官方语义一致, 跨版本):

| 语义状态 | 覆盖 qB state | 说明 |
|----------|---------------|------|
| `is_checking` | checkingDL, checkingUP, checkingResumeData | 校验中 |
| `is_downloading` | downloading, forcedDL, metaDL, forcedMetaDL, checkingDL, queuedDL, stalledDL, pausedDL, stoppedDL | 下载中 (含暂停/排队/校验下载) |
| `is_complete` | uploading, stalledUP, pausedUP, forcedUP, queuedUP, stoppedUP, checkingUP | 已完成下载 |
| `is_uploading` | uploading, forcedUP, stalledUP, queuedUP, checkingUP | 做种中 |
| `is_errored` | missingFiles, error | 出错 |
| `is_stopped` | pausedDL, pausedUP, stoppedDL, stoppedUP | 已暂停/停止 |

注意: `is_downloading` **包含** pausedDL/stoppedDL; 条件不支持 `!` 取反; "正在做种" 用 `is_complete&is_uploading`。未识别 state 字符串 → `TorrentState.UNKNOWN` (所有属性 False)。

## 变量替换

`utils.replace_vars(text, tracker_conf)` (2026-09 迁至 utils, 原在 RuleContext): 当前仅 `${required_seeding_time}` → tracker 的 `hr.required_seeding_time_raw` (如 `"3D"`; tracker_conf=None 或无 HR 配置 → 留原文不替换)。用于 add_tags/remove_tags/add_category 的格式串与 HR 标签/分类格式。新增变量在 `utils.replace_vars` 扩展。
