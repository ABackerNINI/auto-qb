# 5203 —— 删辅种明细做种数(总)/用户(总)重复列后全量基线

> 摘要: 删辅种明细做种数(总)/用户(总)重复列后全量基线
> 基线时间: 2026-11-04 23:36
**Refs:**

## 验收数字

- 汇总行: `5203 passed, 2 skipped in 156.32s (0:02:36)`(commands run test.full, 2026-11-04)
- TOTAL: `24404 statements, 211 miss, 8356 branch, 166 partial, 99%`(达标线 99.0%)
- 口径注记: 首跑曾出现 1 例偶发失败(test_hr_discovery 的端口绑定用例, 单跑通过、与本改动无关——本轮只动静态 JS/HTML), 重跑全量即全绿, 上记数字取重跑实测。

## 本改动面

- `src/auto_qb/webui/static/shared/app.js`: DETAIL_COLUMNS 删除 `num_complete`(做种数(总)) / `num_incomplete`(用户(总)) 两列 —— 做种数/用户列按 qB 口径自带 "(总数)" 括注(fmtPeersQb), 独立总数列纯重复; 注释改记删除缘由。
- `src/auto_qb/webui/static/shared/tpl/xtpl.html`: `<aq-member-cells>` 删除上述两列的值单元格死分支(守阵 _scan_column_cells_paired 配对同步)。
- 不动后端: views_row.py 等仍透出 num_complete/num_incomplete 字段(抽屉各变体 fmtPeersQb 括注仍消费)。
- 测试: 同类排查覆盖 GROUP/TORRENT/SHOW 列模型与抽屉各变体表 —— 均无同型重复列; e2e 引用的 num_complete 是抽屉 tracker 行字段, 不受影响。
