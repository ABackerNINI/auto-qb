# 条件与动作 (含 expr 速查)

> 摘要: 条件组合树 (`all`/`any`/`not`, W3) + choose 编排块 (`choose`/`default`/`when`/`then`, W3-B) + 13 种条件 + `expr` 速查 + 12 种动作 + `checking` spec 逐键参考 + 限速单数值保护 + 状态映射表 + 变量替换。
> 触发: 条件, 组合树, all, any, not, 逗号分组, 动作, choose, 分支, default, when, then, expr, 表达式, checking, basic_check, with_reference, without_reference, 跳检, 参考种子, 状态映射, 变量替换, 限速保护, 禁止下载, stop 压制

## 条件组合树 (W3, plan 26-11-01-0106)

规则的 `conditions` 规范化后是**一个节点**: 组合节点 `all: [节点...]` / `any: [节点...]` / `not: 节点`, 或叶子 `{条件名: spec}`。旧扁平单键 dict 列表由载入层 `config/compat.normalize_conditions` 包一层隐式 `all:`(语义 = 旧「列表内全部 AND」), 引擎与校验器只认树形(防漂移铁律: 不存在读 legacy 扁平列表的第二语义分支)。

```yaml
conditions:
  all:                                  # 全部满足(旧扁平列表 = 隐式 all, 行为零变化)
    - path: ["regex:^R:/"]              # 叶子: 13 种条件之一, spec 语义不变
    - any:                              # 任一满足(嵌套/短路求值)
        - tags: ["HR,low", "z"]         #   组内逗号=与, 组间=或(叶子内既有语义, 见下表)
        - not: {trackers: nope}         # not 取反, 孩子是单个节点
```

- **求值**: 递归 + 短路(all 首个 False / any 首个 True 后不再求值其后叶子); 叶子求值异常 -> `verdict: error` 本条规则本轮不命中, 不影响其它规则(W2 语义)。
- **fail-fast**: 组合键拼错按「未知条件」报错; 多键节点 / `all`/`any` 值非列表 / `not` 孩子非节点 / 嵌套超 16 层(`CONDITION_TREE_MAX_DEPTH`, compat 单点)全部在载入校验期拒绝。
- **「逗号分组」映射(G4)**: 各条件的行内分组/OR 语义**全部留在叶子内**, normalize 零改写(逐条件核对表 = `compat.CONDITION_GROUPING_MAP`; `tags` 组内逗号=AND、`state` 组内 `&`=AND 且**非逗号**, 组间都是列表=OR)。组合树的 `any`/`not` 是新增显式写法, 不改写既有叶子语义; `hr` 的双语义分歧(`conditions.py` 无站点/无 HR 分支 vs 表达式侧 `tor.hr_satisfied`)维持现状不单边改齐。

## choose 编排块 (W3-B, plan 26-11-01-0106 G6/D3)

动作序列扁平无分支的补位(G6): 动作列表项可为 `choose` 编排块, 与普通动作项混排 —— `choose: [{when: <条件树节点>, then: [动作项...]}, ...]` + 可选 `default: [动作项...]`。

```yaml
actions:
  - add_tags: ["基础"]                   # 普通动作项与 choose 混排, 按序执行
  - choose:
      - when:                            # when 与 conditions 同款组合树(可嵌套 all/any/not)
          all:
            - size: ">=10GiB"
            - state: ["is_uploading"]
        then:
          - upload_speed_limit: 5MiB/s   # then 内是普通动作项(含 on_error, 与顶层同语义)
      - when: {hr: condition-met}        # 按序求 when, 首个命中执行其 then(其后分支短路)
        then:
          - add_tags: ["HR-watch"]
    default:                             # 全部未命中时执行; 省略且无命中 = 空操作(no_op)
      - add_tags: ["check-manual"]
```

- **求值**: 按序求 when, 首个命中执行其 then(其后分支**短路不再求值**); 无命中且有 `default` 执行 default; 无命中且无 default = 空操作(与空动作表一致, `verdict: no_op`)。
- **错误策略**: then/default 内动作失败按其自身 `on_error` 三档分派, **与顶层动作同一语义单点**(base.py `_dispatch_result`, 无第二语义分支); choose 本体无 on_error(策略挂块内动作项)。块内 retry 的断点记 choose 块首(续跑轮整块重新求值重新分派), pending 记块后(块内不细粒度续跑)。
- **嵌套约束**: `choose` 内不再允许 `choose`(编排块只允许一层, 防递归爆炸; 校验器 fail-fast + 引擎构造期双拦); when 条件树深度复用 `CONDITION_TREE_MAX_DEPTH`(16 层, 从 1 起独立计, 与顶层 conditions 同口径)。
- **fail-fast**: 块级键面 `choose`/`default`、分支键面 `when`/`then`(compat.CHOOSE_KNOWN_KEYS / CHOOSE_BRANCH_KEYS 单点); 缺 when / 缺 then / choose 非列表 / 空分支列表 / then·default 非 list / 嵌套 choose / when 内未知条件全部在载入校验期拒绝, 坐标按树形如实报(`choose[i].when` / `choose[i].then[j]`)。
- **normalize 单点**: choose 结构识别/分支建树/块内动作缺省 on_error 注入全在 `config/compat.normalize_choose_block`(幂等); when 扁平列表同样包隐式 `all`。
- **触发白名单**: `on_torrent_deleted` 的动作白名单同样约束 choose 块内 then/default 的动作(删除后种子无活现场, 块内动作同径拒绝)。
- 样例: 无独立样例文件(原 `test_yamls/test_actions/test_choose.yml` 随 `test_yamls/` 样例目录于 2026-11-01 整体移除)。

## 13 种条件 (conditions.py, 全部 `match(ctx) -> bool`, 组内与组间逻辑见各条)

> **`expr` 表达式条件**(2026-09 新增, 现注册 13 种里最晚的一种): 一条字符串自由组合种子字段与额外值, 语义覆盖下表全部旧条件。**旧 12 个条件保留不删**, 两种写法可混用(同一条规则里 `- expr: ...` 与其它条件仍是 AND 关系)。完整语法 / 取值表 / 迁移对照见 [计划文档](../plans/26-09-20-2225-rule-conditions-expression-plan.html), 本节只留速查。

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
- **容器比较口径**(2026-10-06, issue 26-10-06-0027): `==` / `!=` 两侧同为 LIST 时按**集合语义**比较 —— 求值侧把两侧统一转 set 再比(不挑容器形态: `tor.tags` 是 frozenset、`tracker.groups` 是 list、列表字面量是 tuple, 跨形态比较现已对齐), `tor.tags == ["HR", "1080p"]` 即精确全量匹配(乱序 / 重复元素不影响); 真子集 / 超集**不算**相等 —— 「包含」语义用 `in`(单元素)或 `~`(模式)。
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
| `hr` | `"condition-met"` | `condition-met`(需管束 = `hr_managed`: 考察中 ∨ 无站点证据/未接入且未达标, 26-09-30-0559 触发语义重构 —— 旧「本机下载触发」语义迁往表达式 `tor.hr_local_triggered`) / `condition-not-met`(补集) / `satisfied`(义务已了单条件: 站点达标结论 ∨ 做种时长/分享率达标, 不再有触发前置); 依赖 tracker_conf.hr, 无 HR 可判定显式分支(2026-11-01 按现行为修正, W3-A 报告计划外发现): 未匹配站点(`tracker_conf=None`)仅 `condition-not-met` 为真; 站点已匹配但无 HR 配置(`conf.hr=None`)非 `condition-met` 全真(`satisfied=True`, 与表达式侧 `tor.hr_satisfied` 同场景恒 false 是有意分歧勿单边改齐) |
| `date_time` | `{day_of_month: 1-31, day_of_week: 1-7, time: "10:00-23:00"}` | 全部可省略(省略=不检查); 区间 `a-b` 或单值; time 支持跨午夜; day_of_week 用 isoweekday (1=周一) |
| `seedtime` | `"<24H"` | 比较 seeding_time (秒) |
| `upload_ratio` | `">1.5"` | 比较 ratio |
| `expr` | `'(tor.size >= 10GiB) and (tor.ratio > 1.5)'` | 一行表达式自由组合种子字段与额外值(语义覆盖全部旧条件, 可与旧条件混用 AND), 完整语法/取值表/门控见上节速查; spec 深度校验在配置期完成(compile + validate + 数据源门控), 表格补记 2026-11-01(W5 registry 文档一致性核对: 注册表中此条原先漏列) |
| `freespace` | `{path: "R:/", amount: "<100GiB"}` | shutil.disk_usage; path 为空 → False; OSError(盘不可读/盘符掉线) → 抛 `ExprError` 停规则(2026-10-06 拍板 P-07, 绝不降级成假值 —— 与映射 miss / expr 形式 `freespace()` 同口径; 磁盘故障时规则显式停 + ERROR, 不再静默失活) |

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
| `checking` | 见「`checking` 动作详解」节 | 校验/跳检, 最复杂动作 |
| `move_to` | `{path: "/new"}` | set_location; path 空 → fail |
| `reannounce` | `true` | ⚠️ 有风险: 运行时最小间隔 10M(同种子, state 键 `reannounce_ts`, 独立于规则去重兜底) + 暂停种子跳过 + 未配 execute_once/cooldown 时加载 WARNING; 高频 announce 会被封号 |
| `upload_speed_limit` | `"1000KiB/s"` | 见下"限速保护" |
| `download_speed_limit` | 同上 | 同上 |
| `print_torrent_details` | `true` | **只读留档动作** (2026-09-12): 读取 `ctx.torrent` 快照字段 + tracker 派生信息, logger.info 输出单行详情; 纯读取无副作用, dry-run 照常打印, 恒 success。种子已删除时 `ctx.torrent` 回退删除前快照副本 (snapshot), 仍可打印 — 是 `on_torrent_deleted` 白名单里唯一允许的动作 |

> ⚠️ **没有「禁止下载」类动作**: 能影响下载方向的只有 `stop`(暂停 —— 需**反复压制**, 且对 `checkingDL`/`metaDL` 同样生效)与 `download_speed_limit`(限速 ≠ 禁止)。故「禁止某分类的种子开始下载」只能近似表达为「发现即暂停(**条件须带 `state: ["is_downloading"]`**, 否则会误伤做种)+ 缺省 interval 每 tick 兜底」, 且**不能**配 `execute_once: once/daily` —— 完整状态矩阵 / 去重实测 / 竞态与绑定前提见 [报告 26-09-27-0047](../reports/26-09-27-0047-report-rule-iyuu-stop-guard.html)。

## `checking` 动作详解 (spec 逐键参考, 2026-11-05 issue 26-09-28-1946 清偿)

> 逐键口径与 schema 插件表(`ACTION_PLUGINS` 的 checking 项 `Plugin.fields` + `CHECKING_SECTION_FIELDS`)及深度校验 `_validate_checking_action_spec` 一一对应; 键面守卫 `test_config_key_surface` 对插件 spec 键**不再豁免**, 改键忘回写本节当场报。

`checking` 是 object 动作: 按「组内能否找到已完成且**可信**的同内容参考种子」分两分支, 各分支的校验方式(跳检/强校验)独立配置; 推荐配法 = 有参考配跳检、无参考配强制校验。**可信**由顶层 `basic_check` 统一判定。执行体在 ops 层(规则侧 `ctx.ops.skip_submit` 一行委托, 异步 job); 跳检会**删种重加**(期间停止做种), 请配 `cooldown`/去重避免反复执行。

```yaml
- action: checking
  basic_check: filelist            # 参考判定方式
  with_reference:                  # 找到参考种子时
    enabled: true
    mode: skip-checking            # 跳检(删种重加, 不再哈希校验)
    auto_start: true
  without_reference:               # 找不到参考种子时
    enabled: false
    mode: full-checking            # 强制完整哈希校验
    auto_start: false
```

顶层键:

| 键 | 类型/取值 | 缺省 | 语义 |
|----|-----------|------|------|
| `basic_check` | enum: `filelist`/`piecehashes`/`custom` | 必配 | 如何确认候选参考种子数据可信: `filelist` 比对文件列表(快); `piecehashes` 比对分片哈希(慢但更严); `custom` 调用自定义脚本 |
| `custom_basic_check_program_path` | path | `""` | 仅 `basic_check: custom` 时必配(否则校验报错); 以 `<候选参考种子hash> <其保存路径>` 为参数对每个候选逐个执行, 退出码 0 = 该候选可信 |
| `with_reference` | object | 未配 = 该分支跳过 | 组内能找到已完成且可信的同内容种子(参考种子)时的处理方式 |
| `without_reference` | object | 未配 = 该分支跳过 | 找不到参考种子时的处理方式; 选跳检属高风险(未做哈希校验直接开始), 建议强制校验或不开该分支 |

分支段(`with_reference` / `without_reference` 同键面, 即 `CHECKING_SECTION_FIELDS`):

| 键 | 类型/取值 | 缺省 | 语义 |
|----|-----------|------|------|
| `enabled` | bool | `false` | 不启用时该分支整体跳过(日志里记跳过原因) |
| `mode` | enum: `skip-checking`/`full-checking` | `skip-checking` | `skip-checking` 跳检(删种重加, 不再哈希校验); `full-checking` 强制完整哈希校验 |
| `auto_start` | bool | `false` | 完成后自动开始该种子(重加/校验通过后种子处于暂停, 开启后才恢复运行) |

校验要点(fail-fast, 配置期 `_validate_checking_action_spec`): spec 只接受 dict(旧字符串形式已移除); 未知键报错 —— `skip_checking_tag` 是全局配置, spec **不可**配同名键; 子段键面同样 fail-fast(拼错 `enabled` = 分支静默不启用, issue 26-10-06-0028 D-02)。全局「跳检成功标签」种子未经哈希校验, 参考判定一律排除(防"未验证"经参考链传播)。

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
