# 1641 collected / 1640 passed + 1 skipped —— 两线合流: HR D 档已免罪来源单列 (v3.4) × webui 种子级标签/分类编辑

> 摘要: 两轮并行开发后的合并树重测, 数字与两侧单线持平; 基线时间考据自合并记录 d72a538/c8f98f4 (04:28–04:38), 文件名沿计划定案取合流切片 1700 (该切片时钟偏移); 当日序位第 8
> 基线时间: 2026-09-26 04:38
> 档案: 26-09-22-backend-partial-hr-verify (v3.4) · 26-09-26-webui-torrent-meta-edit

(档案 `26-09-22-backend-partial-hr-verify` v3.4 + `26-09-26-webui-torrent-meta-edit`; 两轮并行开发, 本条为**合并树重测**)。

- **HR v3.4 轮 +2 条**: test_hr_resolve.py +2(`test_judge_record_carries_verified_source` D 档放行记录透传
  `verified_source=SOURCE_EXEMPT`、两种缺席式放行恒空串 / `test_safety_display_site_exempt_split_from_released`
  D 档已免罪「在线·已免罪」与缺席证据「在线·已核实，安全放行」分开编码); test_web.py +0 改 2 处
  (`test_hr_view_fields_three_state` 加 D 档字段级断言块 `hr_safety_src == "site_exempt"` /
  `test_frontend_hr_safety_wiring` SRC_* 常量数守阵 8→9)。落地面: `hr/resolve.py` 新增
  `SRC_SITE_EXEMPT` + `HrResolution.released_src` / `HrJudgement.verified_source` 透传 +
  `safety_display` 分流; 前端 `shared/hr.js` 两张映射表各 +1 键(徽标「在线」/ 来源桶「在线核实」,
  无新 CSS —— 徽标 class 固定 hr-src)。
- **种子级标签/分类编辑轮 +3 条**(test_web.py): `test_api_t_bulk_tags_category_enqueue` bulk 标签/分类动作入队
  (tags 过滤空段非空才透传 / category 按键存在性透传, 空串=清除分类要保留 / 未提供时载荷不带键历史形态不变) /
  `test_drain_web_commands_bulk_torrents_tags_category` 标签/分类命令执行(单次调用带全部在册 hash /
  缺 tags 或缺 category 键 error 回执 / 空串分类合法) / `test_frontend_meta_dialog_paired` 标签/分类对话框守阵
  (双 UI 成对: metaOpen 对话框 + 浮条/批量菜单/单种子菜单三处入口; shared 接线 openMetaDialog 锁定目标 +
  metaToggleTag 走 bulk 链路; .meta-dialog/.opt-pill 两套 CSS 成对)。落地面: `/api/torrents/bulk` 动作表扩
  add_tags/remove_tags/set_category(载荷加 tags/category 键) + 前端即时编辑对话框(shared/dialogs.js,
  .opt-pill 切换胶囊, atlas 首次引入该组件)。

TOTAL **92%**(11013 语句 / 787 未覆盖 / 3656 分支 / 331 partial)。
