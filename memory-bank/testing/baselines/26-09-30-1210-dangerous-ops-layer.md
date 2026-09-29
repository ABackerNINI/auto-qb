# 基线 · 1829 passed + 3 skipped / 91% —— 危险操作独立操作层 (P1+P2')

> 摘要: 计划 plans/26-09-30-0109 全量实施(P1 提交点检查 + P2' 操作层抽取) —— ops 层
> core/mixins/ops.py(OpsMixin: ops_recheck/ops_skip_check, rules → ops ← web), R1 WEB recheck
> 提交点拒绝(单发 + bulk 第二入口), R2 跳检实时复核, 右键跳检(POST /api/torrents/{hash}/skip-check
> + 确认框), 保护按 source 区分(冷却仅 rule / 在途互斥·R2·同日去重全来源), webui 不 import rules
> 静态守阵。测试 +12(test_ops 7 / test_checking R2 1 / test_web 4); 路由金清单 +1(共 66)。
> 基线落在**合并远端 87d154c7 之后的新基线上**(键盘快捷键 W1-W7 + HR 触发语义两专题的远端
> 提交一并计入; 上一基线之后的 3 个既有文档守阵失败已由远端 26-09-28 计划 doc-status 置 Done 消掉)。
> 基线时间: 2026-09-30 12:40 (develop @ 87d154c7 + 本轮提交) 制品: plans/26-09-30-0109 已置 Done。

TOTAL **1829 passed + 3 skipped / 91%**(12650 语句 / 1012 未覆盖 / 4320 分支 / 429 partial,
test.full 24.82s, rc=0) —— 较上基线 26-09-30-0450(1792 passed + 3 skipped)增 37:
本轮 +12(test_ops 7: web 源登记/释放与无晋升、在途拒绝、快照 checking 拒绝、无冷却、rule 源
冷却+重入队回归、跨来源同日去重、web 无高风险告警; test_checking 1: R2 复核种子已删零副作用;
test_web 4: recheck 单发拒绝、bulk 在途跳过计数、右键跳检全流程、webui_no_rules_import 守阵),
远端两专题 +25(键盘快捷键 W1-W7 与 HR 触发语义)。路由金清单 65→66(POST /api/torrents/{hash}/skip-check)。

## 本轮改动面

- 新建 2 文件: core/mixins/ops.py(474, OpsMixin — R1/R2/四阶段/poll/备份清理随迁, 保护按 source;
  头注导入防环: 常量与冷却 helper 单点留 full_checking.py)、tests/test_ops.py(7)。
- rules 3 文件改薄: full_checking.py(276→178, 留 1.5/1.6 闸门+常量 helper; 执行体改一行委托,
  on_success 只做晋升)、skip_checking.py(284→28, 一行委托)、checking.py(docstring 更新, 决策链 0-4 不动)。
- core 2 文件: mixins/__init__ 与 qbmanager(OpsMixin 组合进 QbManager)。
- webui 3 文件: commands.py(recheck_torrent/skip_check_torrent handler 经 ops 自写回执, 入
  DEFERRED_RECEIPT; bulk recheck 分流 _bulk_recheck_via_ops 逐个提交+聚合回执; recheck 移出
  _BULK_ACTIONS)、server/routes/torrent_cmds.py(+skip-check 路由)、static(drawer.js skipCheckTorrent
  危险确认框 + ctx-menus.html 菜单项「跳检…」)。
- 测试 3 文件适配: test_checking/test_actions(patch 目标 6 处迁 ops 模块; _infer_content_layout/
  _backup_torrent 归属 OpsMixin; 4 个 R2 桩补灌 client.torrents 或 info 故障后移)、
  test_web(金清单+1; bulk recheck 断言改逐个提交; recheck 回执改 handler 自写, 真值登记断言移 c2;
  4 条新测试)。
- 无新配置键、无新线程、无 state_file schema 变更; skip_check_day / recheck_fails / 备份元数据键语义不变。
