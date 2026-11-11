# 6070 passed + 2 skipped —— issue 26-11-11-0823 后端部分组闸门(delete 硬拒+location confirm 闸)+前端放行位+电池 6 条

> 摘要: issue 26-11-11-0823 后端部分组闸门(delete 硬拒+location confirm 闸)+前端放行位+电池 6 条
> 基线时间: 2026-11-12 05:50
**Refs:** memory-bank/tasks/26-11-12-webui-partial-group-backend-gate.md, memory-bank/issues/26-11-11-0823-feat-webui-partial-group-backend-gate.html

## 验收数字

`commands run test.full` 实测(2026-11-12 05:50, 本 clone HEAD 0d420c9d + 本批未提交改动):

```
TOTAL                                                27110     65   9478     68    99%
6070 passed, 2 skipped in 173.36s (0:02:53)
```

差值口径: 上一切片 26-11-12-0521(webui-kbd-hints)为 6064 passed + 2 skipped —— 本切片 +6 = 部分组闸门电池 6 条(test_web_commands_bulk.py 新增; 既有用例只扩载荷/改断言不增数: dispatch 矩阵第 7 类 + stay_silent 静默闸拒段、node 电池 S3 断言口径、drawer 电池零改动)。

## 本改动面

- `src/auto_qb/webui/commands_torrents.py`: 部分组闸门 —— 谓词单点 `_partial_groups_of`(前端 selection.js `_partialGroupsOf` 的 D2 口径镜像) + 拒单文案单点 `_partial_group_reject_msg`(组名 ≤3 连排 +「等 K 个组」+ 合计缺口) + `_cmd_bulk_torrents` 闸门块(delete×delete_files 硬拒; 迁移关 location 无 confirm 拒单、confirm=true 放行) + docstring;
- `src/auto_qb/webui/static/shared/drawer.js`: submitMoveDialog 闸放行位一行(`post(gated !== null)` —— S3 确认框确认后带 confirm=true, 即后端闸的那道确认);
- `tests/test_web_commands_bulk.py`: 新增电池 6 条(硬拒+confirm 免疫半面 / 放行矩阵五形态 / 双通道同批拒收 / 聚合文案两组合计+四组截断 / location confirm 闸 / 武装态不进闸)+ 测试计划 docstring 同步;
- `tests/test_web_commands_dispatch.py`: drain 电池 delete 用例改平铺全组(部分组×delete_files 已被闸硬拒)+ 重灌 HB; 无 cmd_id 早退矩阵六类→七类(闸拒第 7 类)+ stay_silent 补静默闸拒段;
- `tests/test_webui_static_r4_node_batteries.py`: S3 电池断言改「确认后首发带 confirm=true(后端闸放行位)」+ 两处 docstring 口径同步(ensureWebFlags 桩随远端 0d420c9d 已入库, 本批不再携带);
- `memory-bank/issues/26-11-11-0823-feat-webui-partial-group-backend-gate.html`: 认领链(In Progress→Done)+ 复验行 + 修复后补充。
