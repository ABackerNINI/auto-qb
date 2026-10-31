# 3682 passed + 2 skipped(根), 98% 覆盖 —— 免重启整组迁移 P2 别名单元与只读预检落地后全量基线

> 摘要: 免重启整组迁移 P2 别名单元与只读预检落地后全量基线
> 基线时间: 2026-10-18 22:57
**Refs:** memory-bank/plans/26-10-18-1604-plan-group-relocate-restart-free.html

## 验收数字

`commands run test.full` 实测(2026-10-18 22:53, 启动前已 `my-commit-flow.sync` 同步到 86ed631a):

```
TOTAL    19454    292    6526    213    98%
3682 passed, 2 skipped in 133.47s (0:02:13)
```

逐条口径: 总数 3682(通过); 2 skipped(既有 skip, 与本改动无关); 覆盖率 98%(fail-under=98 达标)。上一条基线为 P1(26-10-18 20:38, slug group-relocate-restart-free-p1), 相对差值看 `commands run kb.baseline -n 2`, 本切片不手抄。

## 本改动面

P2 别名单元 + 闸门(计划 26-10-18-1604 §04 P2, 只读预检面):

- `src/auto_qb/core/modules/relocate_units.py`(新): 纯决策层 —— `plan()` 别名形态分流
  (文件数阈值/目录专属/平铺/硬上限/长路径能力校正先于阈值) + `RelocateJob` 相位机值对象
  (终态判定/作用域谓词/未收尾拦截) + `GroupFacts`/`evaluate_group()` 组闸门(目标同名冲突/
  .!qB/空间/同卷证明带抖动容差/平台能力/幂等/第三方文件链接与硬链接拒迁/目录级链接识别) +
  `AddFacts`/`evaluate_add()` 添加种子落点三分流(§3.6 第 1/3/8/15 行)
- `src/auto_qb/core/modules/relocate_mod.py`: RelocateModule P2 引擎入口 —— `relocate_precheck`
  (多选按组拆开逐组判定, 只读)/`precheck_add`/`capability_view`; 事实收集(file_access 三态/
  alias_fs 探测/store.server_state 同卷证明); 内存 job 登记表(P3 执行体落账前的骨架); start/apply
  的能力探测接线(enabled 时才探, R15 口径)
- `src/auto_qb/core/module.py` + `core/qbmanager.py`: `ctx.relocate` 模块句柄接线
- `src/auto_qb/webui/server/routes/torrent_cmds.py`: `POST /api/torrents/relocate/precheck` 与
  `POST /api/relocate/precheck-add`(403 门控 relocate.enabled fail-closed + 路由层 400 参数校验)
- `src/auto_qb/webui/commands.py`: `relocate_precheck`/`relocate_precheck_add` 命令 handler +
  DEFERRED_RECEIPT_COMMANDS 登记(回执经 truth 字段带出)
- 测试: 新 `tests/test_relocate_units.py`(21 例, 表驱动 §3.2 五行 x 阈值 7/8/9 + §3.6 行) 与
  `tests/test_web_relocate.py`(19 例, 模块/路由/drain 三层 + 零副作用证明); 守阵同步
  `test_web_route_manifest`(82->84 条)/`tests/webui_helpers.py`(替身配置补 relocate 段)
- 文档: 基线切片本条; 无新增配置键(keys.md/configuration.md 不动)

