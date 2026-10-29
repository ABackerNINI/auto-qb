# 4167 passed + 2 skipped(根) —— 二评批E/F2 两缺陷收口后全量

> 摘要: 二评批E(F2-03 drawer 合并补给无条件 bump seq)与批F2(E-01 路由层数值字段裸转换 500)两 issue 收口后全量基线
> 基线时间: 2026-10-30 07:49

## 验收数字

`commands run test.full`(pytest `-n 4 --cov=src --cov-branch --cov-fail-under=99`(pytest.ini addopts); 2026-10-30 实测, 全量 114.78s, 建档 07:49):

```
  TOTAL                                                21098     95   7134    100    99%
  4167 passed, 2 skipped in 114.78s (0:01:54)
```

- 汇总行: **4167 passed + 2 skipped(根)**; 覆盖率门槛 99% 通过(TOTAL 行 99%, missed 100)。
- 本轮新增守阵 2 条: test_web_longtail.test_api_numeric_params_malformed_string_400(12 型畸形值全 400 +
  路由层拒收不入队 + 合法值照常入队) + test_webui_static_dom_panel.test_drawer_merge_supply_seq_bump_conditional
  (node 电池七型: 双源有数据 / 双源在途 / 单源缺口 / 双源都缺 / tp 双源在途 / tp 有缺口 / 合并关)。

## 本改动面

- `src/auto_qb/webui/server/common.py`: 新增 int_param / float_param 单点(照 group_key_param 的
  400 口径: ValueError/TypeError → HTTPException(400, "数值字段非法"))。
- `src/auto_qb/webui/server/routes/torrent_cmds.py`: api_t_limits / api_t_share_limits /
  api_t_file_priority / api_t_bulk 四端点六处裸 int()/float() 改走 helper(issue E-01 五处定位中
  bulk 占两处); 合法数值行为零变化。
- `src/auto_qb/webui/server/routes/torrent_detail.py`: _cmd_speed_limits 两处(upload_kib/download_kib)
  改走 int_param。
- `src/auto_qb/webui/static/shared/drawer_store.js`: _drawerMergeSupply seq bump 移进「确有缺口要补」
  分支 —— gc/tp 各先算 needX, 两源都被数据/门挡住时早退不 bump(在飞取数不被打成 stale, loading 门
  照常由其 finally 清); tp 对 _startDrawerPoll 留在早退之外(起轮与代际无关)。
- `tests/test_web_longtail.py` / `tests/test_webui_static_dom_panel.py`: 新增守阵 2 条 + 头部测试计划清单同步。
