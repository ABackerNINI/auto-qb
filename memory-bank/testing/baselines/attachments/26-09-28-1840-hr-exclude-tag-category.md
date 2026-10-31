# 1828 passed / 3 skipped —— HR 排除功能: 按标签/分类把种子排除出 HR 体系(计划 26-09-28-1805)

> 摘要: 新配置键 `hr.exclude_tags`/`exclude_categories`(全局与站点段, 站点段与全局取并集去重保序), 命中格式的种子不纳入 HR 体系 —— 判定单点 `TorrentRecord` 三入口(`check_hr_condition`/`check_hr_satisfied` 顶部短路 False, `hr_judgement` 顶部短路 None, 公开方法 `hr_excluded()` 供 WebUI)顶部各一行短路, 打标/规则条件/表达式/WebUI 四个消费点零散分支零新增。schema `HR_OUTPUT_FIELDS` 加两 `pattern_list` 字段(全局「HR 全局默认」卡与站点 hr 卡自动出现), 校验走 `KNOWN_HR_KEYS` + `_check_str_list`/`_check_regex_patterns`(全局与站点一处键集两处拦); impact/writer/migrations/`hr/` 取数包零改动(清单账号级全量, 排除不省站点配额, 锚点供给保持全量)。前端三套 UI 共享模板三处成员行挂「已排除」徽标 + 详情抽屉排除态行, `hr_excluded` 进 `_hr_view_fields` 两分支(字段一致性守阵 ④)。FakeTorrent 补 `hr_excluded` 鸭子影子并同步短路(防影子掩盖)。
> 基线时间: 2026-09-28 18:40
> 档案: plans/26-09-28-1805-plan-hr-exclude-tag-category.html(M1-M3 代码侧落地, 待提交)

- test.full: **1828 passed / 3 skipped**, TOTAL **91%**(12576 语句 / 917 未覆盖 / 4246 分支 / 390 partial), 耗时 17.05s, 较前基线(26-09-28-1738)passed +8(新增排除用例: test_torrents 4 + test_hr 1 + test_config 2 + test_web 1), 语句 +147 / 分支 +24。
- 中途踩过一次 `keys.md` 超 12,000 字符 cap(守卫红), 已压缩表述至 12,000 内。
