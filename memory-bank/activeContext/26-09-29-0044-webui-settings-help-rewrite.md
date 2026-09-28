# WEBUI 设置页「?」说明改写(按计划 26-09-29-0003 实施)

> 摘要: 计划已实施完成(doc-status → Done): 六文件纯文案 —— schema/groups.py 10 行(data_dir 基准改 cwd、log.level 去通知基准说法、web.token 存储路径、dedup_window 去重口径、state_file 只读、interval 起算点、remove_similar_tags 范围、add_episode_tags×2、delete_tags risk)、hr.py 4 行(parse_missing_rate_max 预留化 + torrent_rate/max_torrents 回退链与 split 改义)、trackers.py 3 行(奇数句改种子当前限速口径 ×2 + add_tag_for_satisfied 两义消解)、rules.py 13 行(hr 条件反向修、move_to 真搬文件+risk、stop_following_rules_if 六枚举全解、path 补 content_path、freespace 报错路径、checking 分支制 + custom risk 参数主体、auto_start/day_of_month/amount 补 help、interval 起算点、限速奇数句 ×2)、config_hub.js(富文案数据源 qB 累计流量→Traffic Monitor + 删死键 rules.overview)、settings-detail.html 补 ND 滚动窗口句。test.full 1831 passed / 3 skipped(基线 26-09-29-0044)。
> 触发: webui-settings-help, 设置页说明, help 改写, parse_missing_rate_max, cap 收口
> 最后活动: 2026-09-29 00:44 (实施轮: 顺带修 KB 守卫三处存量红)

## 未完成 / 待拍板

- **parse_missing_rate_max 去留 —— 已定调(2026-09-29 用户)**: HR 在线核实正在改造, 该键不用管; 本轮只改了界面文案(标注「预留、当前不参与判定」), 不入池、不删键。
- **WEBUI 浮窗走查**: 计划批次建议的实机走查(开 WEBUI 核对浮窗渲染, 含富文案覆盖键)需真实 qB, 本轮未做。
- **pitfalls/kb/cap-counting.md 已贴顶**(5993/6000, 余 7): 本轮 _doc-map 超 cap 复发按该条既定路线改渲染口径收口(折行 400→4000 + 去 (N) 计数 ⇒ 12112, 余 88), 复发记录因无余量未入该文件 —— 下次触顶按其升级路线动 CAP_POLICY(须同步 SKILL.md cap 表)。
- **切片上限重校**: SLICE_COUNT_LIMIT 56→70(57/57 全活跃无可蒸馏, 按守卫自带 14 天节奏口径二次校准)。
