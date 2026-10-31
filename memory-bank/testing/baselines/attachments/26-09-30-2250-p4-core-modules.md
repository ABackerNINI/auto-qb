# 基线 · 1879 passed + 3 skipped / 91% —— 内核化重构 P4 (中坚模块: grouping / ops+checking)

> 摘要: plan plans/26-09-30-1819 P4 全量实施 —— GroupingMixin(387 行)迁 GroupingModule
> (core/modules/grouping_mod.py), 认领四个刷新相位 transitions / torrents_added / removed_scan /
> post(§4.2 相位表), `grouping.enabled` 开关与缺文件扫描轮内去重集合(_missing_scanned_keys)归
> 模块自管, 内核 _refresh_torrents 的分组调用点改相位广播(transitions 每轮无条件 emit —— 去重
> 清零时序归其相位入口); OpsMixin(474 行)+CheckingMixin(39 行, 决策点 D2)迁 OpsModule
> (core/modules/ops_mod.py)升 **ctx.ops 服务**, web 命令 recheck/右键跳检/bulk 改走 ctx.ops,
> 规则侧经 manager 旧名委托(plan §7.2, P5 收口); rules 轮询常量与冷却 helper 迁 rules 包中性叶
> **rules/checking_meta.py**(ops 与 rules 单向化: ops → 中性叶 + rules.base ActionResult 是唯一
> import 方向, rules 消费经 ctx.ops 运行时调用; actions/__init__ 改从 checking_meta 取常量,
> full_checking.py 再导出保测试导入路径)。mixins 包删三文件, manager 增 P4 委托层(grouping 12
> 单行 + ops 3 单行); AppContext 增 maintenance/ops 句柄(分组打标经 ctx.maintenance.add_tags,
> 不 import 兄弟模块)。
> 守阵: tests/test_modules_p4.py 8 例(新建: ctx 装配+序 / 四相位各恰一订阅者 / enabled 自判+
> 去重清零时序 / torrents_added 相位归组 / removed_scan+post 相位 / ctx.ops 直调与旧名委托共享
> 在途互斥 / check_filelist 双路可达 / sections 认领锁定); test_module_host 装配断言改九模块;
> test_checking patch 目标随迁 ops_mod(5 处); test_file_access _bare_grouping 改造模块 fake-ctx
> 宿主; test_utils/test_actions CheckingMixin/OpsMixin 引用改 OpsModule; test_grouping 去重清零
> 与 group_key_of 改经模块; scripts/qb_capture.py import 随迁。「缺文件扫描与跳检代表种两口径
> 不混」断言保留(_valid_for_representative vs _group_reference_candidates 各自单点, docstring
> 互指)。
> 基线时间: 2026-09-30 23:05, develop @ e3936326(合并远端 cap 债务计划后复核, 数字不漂) + 本轮改动。

TOTAL **1879 passed + 3 skipped / 91%**(13176 语句 / 1052 未覆盖 / 4390 分支 / 427 partial,
test.full 26.6s, rc=0) —— 较上基线 26-09-30-2142(1871 passed + 3 skipped / 91%)增 8:
本轮 +8(tests/test_modules_p4.py: 装配与序 1 / 四相位接线 1 / enabled 自判+去重清零 1 /
torrents_added 归组 1 / removed_scan+post 相位 1 / ctx.ops 直调+在途互斥 1 / check_filelist
双路 1 / sections 认领锁定 1)。

## 本轮改动面

- 新建 rules/checking_meta.py(~60 行): CHECK_RESULT_INTERVAL / RECHECK_FAIL_LIMIT /
  GROUP_CHECK_WAIT_LIMIT / CHECK_START_GIVEUP + _recheck_fail_count / _bump_recheck_fail
  自 actions/full_checking.py 迁入(plan §5「迁到 rules 包中性位置; ops 与 rules 单向依赖」);
  本模块是 rules 包内叶子, 不 import actions / core; 冷却 helper 宿主参数按鸭子类型收敛为
  「.state dict + .save_state()」(manager 与 OpsModule 都满足)。
- 新建 core/modules/grouping_mod.py(~390 行, GroupingModule): GroupingMixin 全部方法原样迁入
  (store/api/config 改经 ctx 现取, client 经 ctx.api.client 现取)+ group_key_of 纯函数随迁
  (scripts/qb_capture.py 语料抓取器单一事实源)+ sections ("grouping"); subscribe 四相位:
  _on_transitions 入口先清 _missing_scanned_keys 再判 enabled(原内核每轮开头无条件 clear 的
  时序等价)→ _handle_state_transitions; _on_torrents_added → _assign_new_torrent(hash 自
  payload); _on_removed_scan → _handle_removed_torrents; _on_post → _handle_save_path_changes
  + _check_download_conflicts; MISSING 打标改 ctx.maintenance.add_tags(模块句柄经 ctx, 不
  import 兄弟模块)。
- 新建 core/modules/ops_mod.py(~560 行, OpsModule): OpsMixin 全部迁入
  (ops_recheck→recheck / ops_skip_check→skip_check 两个公开动词, 保护策略按 source 口径随迁)
  + CheckingMixin.check_filelist 并入(决策点 D2, 静态方法); state 属性/save_state() 经
  ctx.state 门面(供 checking_meta helper 鸭子类型); _backup_torrent 的 state_file 经
  ctx.state.state_file; sections ("skip_checking_tag")。
- qbmanager.py 1030→~1050(净变化小, 委托层扩容): mixins 基类删三个(CheckingMixin/
  GroupingMixin/OpsMixin, 只剩 RuleEngineMixin); 装配清单挂 GroupingModule + OpsModule
  (maintenance 先挂 ctx.maintenance 句柄再注册); _missing_scanned_keys 字段删除;
  _refresh_torrents 四个分组调用点改 events.emit(transitions / torrents_added / removed_scan /
  post, guard 全部移交模块自判); P4 委托层 15 个单行方法(§7.2: 测试与 rules 动作点名零改动)。
- rules/actions/full_checking.py: 常量与冷却 helper 迁出, 从 ..checking_meta 再导出(noqa F401,
  测试 `from ...full_checking import _bump_recheck_fail` 不变); actions/__init__ 改从
  ..checking_meta 取三常量。
- webui/commands.py 三处 self.ops_recheck / ops_skip_check 改 self.ctx.ops.recheck /
  skip_check(plan P4 指定)。
- 测试适配: test_checking.py patch 目标 5 处(auto_qb.core.mixins.ops.* →
  auto_qb.core.modules.ops_mod.*, 含 OpsMixin._backup_torrent → OpsModule); test_file_access.py
  _bare_grouping 改 GroupingModule fake-ctx 宿主(ctx.config/api/maintenance); test_utils.py
  CheckingMixin→OpsModule 8 处; test_grouping.py 2 处(去重清零经 host.get("grouping") +
  group_key_of import 路径); test_actions.py patch 3 处 + _infer_content_layout 改
  mgr.ctx.ops; test_module_host.py 装配断言九模块 + ctx.maintenance/ops 同对象。
- 文档回写: code-style.md 日志目录两行 owner 改模块名; systemPatterns/taskqueue.md 与
  rule-system/checking.md 的 ops 执行体指针改 ops_mod; modules/mixins.md 加「P0-P4 已迁出」
  警示头(历史快照定位); 1819 计划拍板注记与 colophon 加 P4。

## 与计划的偏差

- 无方向性偏差。执行细节两处: ①transitions 相位内核**无条件 emit**(计划 §4.2 表格原顺序带
  `grouping.enabled` guard) —— enabled 判定移交模块后, guard 留在内核会让去重集合在 disabled
  轮不清零, enable 翻转后残留 key 会吞掉首轮合法扫描; 无条件 emit + 模块入口先清零再判 enabled
  才是逐字节等价编码。②torrents_added 相位本段只有 grouping 认领(归组一步), 维护/限速/建任务/
  集数仍在内核逐行调用 —— plan P5「逐种子管线分派为模块订阅」时并入同一相位。
