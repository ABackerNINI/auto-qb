# search-row-view-converge

> 摘要: 修复 issue 26-10-29-1320(b-r16b01): search_torrents._view 收敛为 {**_member_view, by} + 守阵; 全量绿(数字见 commands run kb.baseline)
> 最后活动: 2026-10-29 18:11

**R0(2026-10-29 18:10):** 修复 issue 26-10-29-1320(b-r16b01): search_torrents._view 收敛为 {**_member_view, by} + 守阵(test_search_row_view_converged_on_member_view, 红验过); 全量与覆盖率实测见 `commands run kb.baseline`
**R1(2026-10-29 18:11):** issue 置 Done + 基线切片 26-10-29-1809 落数字; 改动随本专题入库(涉及 views.py/test_web_hr.py/issues/基线/切片)
