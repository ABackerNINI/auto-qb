# 条件与动作 (含 expr 速查)

> 摘要: 17 种条件 + `expr` 速查 + 12 种动作 + 限速单数值保护 + 状态映射表 + 变量替换。
> 触发: 条件, 动作, expr, 表达式, 状态映射, 变量替换, 限速保护

## 17 种条件 (conditions.py, 全部 `match(ctx) -> bool`, 组内与组间逻辑见各条)

> 第 17 种是 **`expr` 表达式条件**(2026-09 新增): 一条字符串自由组合种子字段与额外值, 语义覆盖下表全部旧条件。**旧 16 个条件保留不删**, 两种写法可混用(同一条规则里 `- expr: ...` 与其它条件仍是 AND 关系)。完整语法 / 取值表 / 迁移对照见 [计划文档](../plans/26-09-20-2225-rule-conditions-expression-plan.html), 本节只留速查。

### `expr` 速查

```yaml
conditions:
  - expr: '(tor.seeding_time >= 3D) and (tor.ratio > 1.5)'          # 种子字段
  - expr: '(freespace(tor.save_path) < 200GiB) and (tor.size > 50GiB)'  # 额外值(盘空间)
  - expr: '(sys.dow <= 5) and ((sys.time_of_day >= 22:30) or (sys.time_of_day <= 7:00))'
  - expr: '("HR" in tor.tags) and (not (tor.category ~ "regex:^z"))'
```

- **前缀**: `tor.*`(种子 70 个快照字段 + 派生) / `tracker.*`(主站点 = `tracker_conf`) / `sys.*`(时间/计数/qB 全局状态/全局流量)。函数无前缀: `freespace(path)`、`disk_total(path)`、`exists(path)`、`file_count()`、`raw("字段")`、`len/abs/min/max/round/days/hours`。
- **一层一个运算符, 没有例外**: 同一括号内出现第二个运算符(含 `not`、含同种连续如 `a and b and c`)即报错并给出改写提示; 括号组对该层不透明 —— 因此没有优先级表可查, 也不会误读。
- **字面量带单位**: `10GiB` / `24H` / `1MiB/s` / `22:30`(当日分钟, 配 `sys.time_of_day`)。单位解析复用 `utils`, 写 `10GB` 会报须用 iB。
- **出错语义**: 名字拼错 / 函数写错 / 类型不符 / 结果不是布尔 → **配置期**即报错(fail-fast, 聚合进 `ConfigError`); 运行期数据源拿不到(如 `server_state` 未同步) → `ExprError` → 按上面的「出错即停规则」处理。**绝不降级成假值**: `sys.dl_speed` 拿不到就是报错, 不返回 0(返回 0 会让「全局速度低于阈值」在数据源失效时静默成真)。
- **「值不存在」≠「求值出错」**: 未匹配站点 `tracker.name = "Unknown"`、无 HR 配置 `tor.hr_condition_met = false` 是有定义的缺省, 正常参与求值(与旧条件同语义)。
- **数据源门控**: `sys.upload_today / sys.download_today / sys.upload_month` 需要配置 `global_speed_limit_curve.traffic_source`, **没配则该名字禁用**(配置期即拒绝使用)。
- **⚠ 昂贵取值要配 `interval`**(2026-09-21 基准实测的结论): 求值缓存是 **ctx 级**的, 而生产**每条规则新建 ctx** ⇒ 缓存只对同一条规则内多次出现有效, **跨规则不复用**。于是含 `freespace()` / `file_count()` / `sys.*_count` 的规则若 `interval: 0S`, 每轮每个种子都会触发一次系统调用 / API  / 全库遍历(3000 种子实测: 每轮数千次)。这类规则**必须配 `interval`**。
- **⚠ YAML 引号**: 表达式里出现 `*`(别名)、`&`(锚点)、`#`(注释)、`{}[]`(流集合)、`: ` 都有 YAML 语义 —— 一律用单引号或块标量包裹。
- **试算**: 配置编辑器里表达式字段下方有「试算」按钮(`POST /api/expr/eval`) —— 留空种子 hash 只做编译+语义校验, 填 hash 则用该种子求值并列出**每个取值的中间值**(排查"为什么不匹配"最有用的一条信息)。

| 条件 | spec 示例 | 语义要点 |
|------|-----------|----------|
| `path` | `/path` 或列表 | 匹配 save_path **或** content_path; `match_path_patterns`: 精确(规范化斜杠后全等)/`regex:` 前缀(re.search)/`:ignore_case` 后缀 |
| `size` | `">=100MiB"` | parse_compare + parse_fsize; 比较种子 size |
| `tags` | `["tag1,tag2", "tag3"]` | 列表=组间**或**; 组内逗号分隔=**与**; 支持 `regex:`、`:ignore_case` 与 `${required_seeding_time}` (统一走 utils.match_value) |
| `category` | `["cat", "regex:^HR"]` | 或关系; 精确=全等, regex=search; 支持 `:ignore_case` |
| `trackers` | `["tracker1"]` | 匹配 tracker_conf.name (配置名, 非域名); 或关系; 支持 `:ignore_case` |
| `tracker_group` | `["国内"]` | 匹配站点 `groups` 字段声明的分组 (站点配置层声明, 不写种子, 与 grouping 辅种种子分组无关); 或关系; 支持 `regex:`/`:ignore_case`; 无 tracker_conf 一律 False (2026-09-15) |
| `state` | `["is_complete&is_uploading"]` | 组内 `&` 连接为与, 组间或; 直接取 `state_enum` 枚举属性 (is_checking/is_downloading/is_complete/is_uploading/is_errored/is_stopped) |
| `hr` | `"condition-met"` | `condition-met`(满足触发条件; **完全下载即触发**边界 — 未达触发量/比例的种子 `is_fully_downloaded` (`progress>=1.0` 或 `amount_left==0`, `total_size<=0` 除外) 也视为触发, 2026-09-12) / `condition-not-met` / `satisfied`(触发+做种时长或分享率达标); 依赖 tracker_conf.hr, 无 HR 配置一律 False |
| `date_time` | `{day_of_month: 1-31, day_of_week: 1-7, time: "10:00-23:00"}` | 全部可省略(省略=不检查); 区间 `a-b` 或单值; time 支持跨午夜; day_of_week 用 isoweekday (1=周一) |
| `seedtime` | `"<24H"` | 比较 seeding_time (秒) |
| `upload_ratio` | `">1.5"` | 比较 ratio |
| `upload_size` | `">10GiB"` | 比较 uploaded (总) |
| `upload_size_today` | `">10GiB"` | 基于 state_file 基线的自然日增量 (`upload_delta(kind=daily)`) |
| `upload_size_this_week` | 同上 | ISO 周增量 |
| `upload_size_this_month` | 同上 | 自然月增量 |
| `freespace` | `{path: "R:/", amount: "<100GiB"}` | shutil.disk_usage; path 为空/OSError → False |

比较表达式统一: `> < >= <= == = !=` 前缀, 缺省 `==`; 值解析失败在构造时抛 (fail-fast)。

## 12 种动作 (actions.py, 全部 `execute(ctx) -> ActionResult`)

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
| `print_torrent_details` | `true` | **只读留档动作** (2026-09-12): 读取 `ctx.torrent` 快照字段 + tracker 派生信息, logger.info 输出单行详情; 纯读取无副作用, dry-run 照常打印, 恒 success。种子已删除时 `ctx.torrent` 回退删除前快照副本 (snapshot), 仍可打印 — 是 `on_torrent_deleted` 白名单里唯一允许的动作 |

### 限速的"单数值保护" (tracker.py 与 actions.py 同逻辑)

```python
if (current_limit / 1024) % 2 == 1:   # 当前限速为奇数 KiB/s
    return ActionResult.skip("用户已设置")  # 视为用户手动设置, 不覆盖
```
用户约定: 手动设置且不希望被覆盖时限速用奇数 KiB/s (如 2001KiB/s)。全局限速曲线同样尊重奇数 (cur > 0 and cur % 2 == 1 → 跳过该方向)。

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

注意: `is_downloading` **包含** pausedDL/stoppedDL; 条件不支持 `!` 取反; "正在做种" 用 `is_complete&is_uploading`。未识别 state 字符串 → `TorrentState.UNKNOWN` (所有属性 False)。属性名合法性由 **config 校验阶段**(`_validate_state_condition_spec`)检查: 仅接受 `is_*` 类别属性 (裸枚举成员名在实例上恒真值, 拒绝), 非法名在 load_config 即抛 `ConfigError`。配置校验全部集中在 config, 插件类不再自查 (06 模块职责约定)。

## 变量替换

`utils.replace_vars(text, tracker_conf)` (2026-09 迁至 utils, 原在 RuleContext): 当前仅 `${required_seeding_time}` → tracker 的 `hr.required_seeding_time_raw` (如 `"3D"`; tracker_conf=None 或无 HR 配置 → 留原文不替换)。用于 add_tags/remove_tags/add_category 的格式串与 HR 标签/分类格式。新增变量在 `utils.replace_vars` 扩展。
