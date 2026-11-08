# 规则引擎

> 摘要: 规则模型与种子级任务绑定、七档 verdict 执行语义与断点续跑、条件组合树与 13 条件、expr 求值边界、12 动作族与 checking 决策链、registry 派生收口。
> 触发: 规则, 规则引擎, trigger, 触发器, process, verdict, 断点续跑, execute_once, cooldown, on_error, 条件树, choose, expr, checking, 跳检, registry, 插件

## 规则模型与绑定 (rules/ 包, 调度在 core/modules/rules_mod.py)

- 配置中所有以 `_rules` 结尾的键都是规则集 `{集名: {规则名: spec}}`, Rule 全名 = `{集名}.{规则名}`; tracker 经 `rules: ["@规则集", "@规则集.规则名"]` 引用(按名去重)。
- **规则是种子级任务**: 种子首现(torrents_added 相位)时为其匹配 tracker 引用的每条规则各建一个 Task(kind=rule, interval=规则自身 interval, 0 → 每 tick); 未匹配 tracker 配置的种子不建任务。L2 重建后 full_round 相位幂等补建, 同一 (kind, name, hash) 恰一份(黄金法则 1)。
- RulesModule 持有全部调度知识: 事件分派、建任务、热重载 L2 整段重建(判据 = 创建时固化的消费段, 整段相等即短路); 危险操作(recheck/跳检)一律经 `ctx.ops` 单点。
- 触发时机: `interval`(缺省)为周期任务; 四种事件触发**不建周期任务**, 分派点即时执行, 遇异步 checking 同走断点续跑: `on_torrent_added` 新增即分派 / `on_torrent_state_enum_changed` 状态枚举变化 / `on_torrent_deleted` 仅只读留档动作(白名单) / `on_torrent_field_changed` watch_fields 净变化(自写不自触发, 停机期补捕)(plans/26-09-27-1438-plan-field-changed-trigger.html)。

## process() 执行语义 (rules/base.py)

单值 verdict 返回(`VERDICT_*`, 引擎显式消费): `no_match`(条件不满足/种子已删) / `error`(本条跳过, 不影响它条) / `deduped` / `no_op`(满足但无动作效果) / `pending`(断点已记) / `executed` / `retry`(任务级 requeue)。

- **断点续跑**: `task.resume_index` 非空 → 从断点动作继续, **跳过条件评估与去重**; 正常完成才清零, 异常由队列收尾重置兜底。
- 全部条件 AND; 抛异常 → ERROR(同因节流) + verdict=error。
- **去重**: `execute_once`(once/daily/hourly)与 `cooldown`(优先), 记录键 `exec_history["{规则名}:{hash}"]`; 非幂等动作(校验/开始/汇报/限速)必须配去重。
- **动作顺序执行**, ActionResult 四态: `success` / `skipped`(不算失败, 如标签已存在) / `failed` / `pending`(记断点并中断)。失败按 per-step `on_error: {policy, retries, backoff}` 三档: `stop`(缺省, 中断链) / `continue`(WARNING 后继续) / `retry`(断点挂失败动作, 按 backoff 推迟重入队, 续跑跳过条件与去重, 上限 retries 耗尽按 stop); 缺省值载入链 normalize 单点注入。退役键 `stop_following_rules_if`/`ignore_next_action_error` 载入层转未启用, 等价写法 `on_error: continue`/`evaluation: first_match`(占位)(plans/26-11-01-0106-plan-rule-engine-redesign.html)。

## 条件: 组合树 + 13 种叶子 (rules/conditions.py)

`conditions` 规范化后是一个节点: 组合节点 `all/any/not` 或叶子 `{条件名: spec}`; 旧扁平列表由载入层包隐式 `all:`(行为零变化), 引擎与校验器只认树形。求值递归 + 短路; 键拼错/多键节点/嵌套超限在载入校验期拒绝(fail-fast)。「组内逗号=与、组间=或」语义留在叶子内。

13 种条件(path/size/tags/category/trackers/tracker_group/state/hr/date_time/seedtime/upload_ratio/expr/freespace), 要点:

- **hr 三值语义**(有意分歧, 勿单边改齐): `condition-met`=需管束(`hr_managed` 单点) / `satisfied`=义务已了(`check_hr_satisfied`); 无站点可判定时两值行为不同是有定义的缺省 —— 未匹配站点(tracker_conf=None)仅 condition-not-met 为真; 站点已匹配但无 HR 配置(conf.hr=None)则非 condition-met 全真, 与表达式侧 tor.hr_satisfied 同场景恒 false 为有意分歧。另见 hr-groups.md(`hr_managed`/`check_hr_satisfied` 单点)。
- **state** 用枚举布尔属性(is_* 六态); is_downloading 含 pausedDL/stoppedDL, 「正在做种」= `is_complete&is_uploading`。

### expr 表达式求值边界 (rules/expr/)

一条字符串自由组合种子字段(`tor.*`)/主站点(`tracker.*`)/系统量(`sys.*`)/函数(`freespace()` 等), 语义覆盖全部旧条件, 可混用 AND。

- **一层一个运算符**: 同层第二个运算符即报错并提示改写, 没有优先级表可查; 字面量带单位(`10GiB`); 容器 `==` 按集合语义(全量匹配, 包含用 `in`/`~`)。
- **出错语义两分**: 名字/类型错在**配置期**报错(聚合 ConfigError); 运行期数据源拿不到 → 报错, **绝不返回 0/假值**(数据源失效不得静默成真); 「值不存在」(未匹配站点/无 HR 配置)是有定义的缺省。
- **门控与成本**: `sys.*_today` 等需配 `traffic_source`, 没配则配置期禁用; 求值缓存 ctx 级不跨规则复用(每规则新建 ctx), 含 `freespace()`/`file_count()` 的规则**必须配 interval**(否则每轮每种子触发系统调用/API)。

## 动作: 12 种 (rules/actions/)

add_tags / remove_tags / add_category / remove_category / start / stop / checking / move_to / reannounce(高危, 运行时最小间隔兜底) / upload_speed_limit / download_speed_limit / print_torrent_details(只读, on_torrent_deleted 白名单内)。

- **没有「禁止下载」类动作**: 只能近似为「发现即暂停 + 每 tick 兜底」, 条件须带 `state: is_downloading`(否则误伤做种), 且不能配 execute_once —— 论证见 reports/26-09-27-0047-report-rule-iyuu-stop-guard.html。
- **限速单数值保护**: 限速为奇数 KiB/s 视为用户手动设置, 动作与全局曲线都不覆盖(用户约定「不想被覆盖就设奇数」); 变量替换 `${required_seeding_time}` 单点 `utils.replace_vars`。

## checking 动作: 跳检/强校验决策链 (高风险)

按「组内能否找到已完成且**可信**的同内容参考种子」分 `with_reference`/`without_reference` 两分支, 各配 `mode: skip-checking|full-checking` 与 `auto_start`; **可信**由顶层 `basic_check`(filelist/piecehashes/custom 脚本, custom 可配 `custom_basic_check_timeout`)统一判定, 推荐有参考跳检、无参考强校验; 前置检查(磁盘齐全)两模式强制。执行体单点在 ops 层(`rules → ops ← web`, 规则/WEB 右键同源), 保护按 source 区分: 失败冷却记录与高风险告警仅规则源(校验成功的清除全来源), 在途互斥/动手前实时复核/同日去重全来源生效(plans/26-09-30-0109-plan-dangerous-op-consolidation.html)。

决策链: 暂停中未完成才继续(其余 skip); 校验失败冷却窗口 → skip(rule 源校验 FAILED 后按 spec `recheck_fail_cooldown` 记录, 窗口内不重复校验不烧额度); 组内有活跃下载 → skip; 成员校验在途 → 让位等待(check-wait; 组内共享物理文件); 成员当日校验失败且文件映射一致 → skip(失败推断); 参考候选排除带跳检标签的种子(防「未验证」经参考链传播), `verified_references`(历史通过, 仅内存)并入。**full-checking**: 登记 check 轮询子任务 + 发 recheck → pending 断点, 成功续跑, 失败重置重走(达上限冷却)。**skip-checking 四阶段**: 闸门(部分下载禁止/同日去重) → 准备(导出 .torrent + 备份**先于删除**落盘, 删除是第一个不可逆步骤 —— 崩溃安全的关键) → 删种重加(保留标签/分类/限速/路径) → 收尾(打跳检标签, auto_start); 备份写不进就不删除, 重加失败保留备份。跳检**丢失做种时长/上传量/分享率**, 对 HR 在管种子有代价(见 hr-groups.md)。

## registry 派生收口与 choose 编排 (rules/registry.py)

条件/动作/choose 编排块统一入册, 条目 = 三元组 `类型名 -> 执行函数 + schema 声明(按名引用, 零复制) + 文档片段`; 深度校验器分发、触发器×动作兼容表(on_torrent_deleted 白名单 = `deleted_ok` 派生)、watch_fields 取值域、webui 插件表全部从条目**派生** —— 新增插件只注册一处即全链路可用; 派生与手写基准 diff 清零由守阵钉住。

choose 编排块: 动作列表项可为 `choose: [{when, then}...] + default`(when 同条件树), 首中执行其 then(其后短路), 无命中走 default; 只允许一层; 块内 on_error 与顶层同一语义单点。
