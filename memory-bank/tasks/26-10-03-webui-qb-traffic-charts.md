# 26-10-03-webui-qb-traffic-charts — WebUI qB 口径流量图 (可行性 + 方案C 实施计划)

**Status:** Open
**Added:** 2026-10-03
**Updated:** 2026-10-03
**Summary:** 为 WebUI 新增 3 种仅展示的 qB 口径流量图 (全局实时/单种子/辅种分组) 调研成熟方案并出可行性报告 26-10-03-0757 (13 节 dark 单文件, 主 issue 26-09-27-1248 本轮范围收窄为纯展示、不恢复 condition): 可行性高 —— 三图实时值已随主循环 1.5s 增量同步在内存 (种子级 uploaded/downloaded + server_state + _build_group_view 组级聚合), 零新增 qB 请求; 推荐方案A (internal 全局任务 30-60s 采样 + 内存环 24h@30s + 小时 rollup 30 天落 state.json, v3→v4 纯加法) + uPlot vendor 单文件; 单种 uploaded/downloaded 为 all-time 口径随 fastresume 跨 qB 重启持久 (源码级证据, 报告留 5 条待真机验证清单); 方案 B (纯前端不落盘) 判不满足需求, 方案 C (每组 dat 文件) 与 state_file 黄金法则有张力。主会话只委派, 4 个子智能体串行 (代码盘点 → 外部调研 → 报告撰写 → 拍板记录回写) 全部一次成功 0 异常失败。**用户拍板 (2026-10-03): 先不实施 (P1-P5 五阶段方案保留待启动); 前端定 uPlot; 采样间隔/保留窗口做成可配置项 (新键须进 validate_config + config/schema.py); 停机空洞表达与分组换 key 旧历史策略之后决定。拍板记录已回写报告 §08。** **第二轮拍板 (同日): 总方案 C (采样管线 + 逐系列 dat 文件落 `<data_dir>/qb-traffic/` 子目录, 推翻报告推荐 A) + 停机空洞 null 断线; 分组换 key 旧历史策略按用户要求给三选项详细对比、待拍板默认「不保留」; 产出实施计划 plans/26-10-03-0946-plan-qb-traffic-charts-c.html (P1-P6 六段独立可提交, ≈6-8.5 人日; state 零改动免 v4)。**

**Topics:** torrent-traffic-stats

## 原始请求

用户指令: 为 WebUI 新增 3 种仅展示的 qB 口径流量图 —— 全局实时 / 单种子 / 辅种分组 —— 调研成熟方案并出可行性报告。主 issue `26-09-27-1248-feat-stats-redesign-torrent-traffic` (Open, 单种统计重设计), 本轮范围收窄为**纯展示、不恢复 condition**; 相关 issue `26-10-01-2138-question-webui-traffic-history-chart` (Dropped, 混淆了 Traffic Monitor 全局与 qB 流量)。工作方式: 主会话只委派不实施, 子智能体分阶段串行; 收尾按 memory-bank DoD 回写 (禁止 git 写操作)。

## 思考过程与决策

- **四子智能体串行委派** (主会话只委派): 代码盘点 → 外部调研 → 报告撰写 → 拍板记录回写, 全部一次成功 0 异常失败。
- **可行性核心发现**: 三图实时值已随主循环 1.5s 增量同步在内存 —— 种子级 uploaded/downloaded + server_state + `_build_group_view` 组级聚合, **零新增 qB 请求**; 缺的只是历史序列的采样与存储。
- **方案裁决**: 方案 A (internal 全局任务 30-60s 采样 + 内存环 24h@30s + 小时 rollup 30 天落 state.json, v3→v4 纯加法) 推荐; 方案 B (纯前端不落盘) 判不满足需求; 方案 C (每组 dat 文件) 与 state_file 黄金法则 (状态统一进 state_file) 有张力。前端选型 uPlot (vendor 单文件, 与仓库单文件交付约束相容)。
- **口径发现**: 单种 uploaded/downloaded 为 **all-time 口径**、随 fastresume 跨 qB 重启持久 (源码级证据); 报告留 5 条待真机验证清单 (P5 前置)。
- **用户拍板 4 项** (2026-10-03, 已回写报告 §08): ① 先不实施 (P1-P5 五阶段方案保留待启动); ② 前端定 uPlot; ③ 采样间隔/保留窗口做成**可配置项** (新键须进 validate_config + 同步 config/schema.py, 黄金法则 #4); ④ 停机空洞表达 (null 断线 vs 补0) 与分组换 key 旧历史策略**之后决定**。
- **本档案不声明 `**Refs:**`**: 报告出厂冻结且本轮可改文件清单不含报告/issue 的 doc-refs meta, 单向声明会触发认领链守卫「目标未反向声明本件」; 三件制品 (issue ↔ 报告 ↔ 本档案) 由同键 `torrent-traffic-stats` 在 doc-map 专题视图归组, 正文链接不构成声明 (check_claim_chain 只扫声明方)。
- **第二轮拍板 (2026-10-03)**: 总方案 C (推翻报告推荐 A, 数据落 `<data_dir>/qb-traffic/` 子目录) + 停机空洞 null 断线; 分组 key 策略用户点名「详细对比」→ 计划 §04 三层对比: key 本体沿用内容指纹 (与分组视图同键同源, 不新造) / 文件名 sha1[:12]+index.json (base64url 全量撞 Windows MAX_PATH) / 换 key 旧历史三选项 (甲不保留=默认 / 乙按 save_path 归并 / 丙组别名), P4 前可改判乙丙且不回改 P1-P2。
- **方案C 合规化裁决** (计划 §01): 流量历史定性为**观测数据** (append-only 纯展示、丢失无一致性后果、体量日志型), 不属黄金法则 3 的「跨轮次状态」→ 不入 state_file; 报告点名 C 三负担 (文件数/半行/清理) 逐条给机制。
- **对报告 §9.1 的设计修正**: `_build_group_view` 是 web 层懒建 (runtime.py:635 脏标记时才重建), 采样器不能复用也不得构成 core→webui 反向依赖 → 采样器自算组级 sum, 口径对齐 views.py:424-429/459-460。
- **计划轮新发现**: ① 新配置键须同步 `tests/fixtures/config_key_surface.txt` (155 行键面冻结, 报告未提此件, 漏了 test_config_key_surface 必红); ② C 下差分基线不落盘 → state 零改动免 v4, 重启首窗 null 与停机空洞语义一致; ③ raw 段落盘使 24h 高分辨率段跨重启存活 (优于 A 的内存环); ④ uPlot 降采样不需要 (30d 窗 720 hour 点 / 24h 窗 2880 点都在直渲染余量内)。

## 实现计划

实施计划单点 = [plans/26-10-03-0946-plan-qb-traffic-charts-c.html](../plans/26-10-03-0946-plan-qb-traffic-charts-c.html) (方案C 版, 本节只留骨架), 六段独立可提交, 合计 ≈6-8.5 人日:

- **P1 采样器核心** (2-2.5 天): internal 任务自注册 (仿 speed_curve_mod) + 三系列采样 + 差分基线/重置 + 单种内存环; 纯内存不落盘不接 UI。
- **P2 dat 落盘** (1.5-2 天): `<data_dir>/qb-traffic/` writer/reader (行式 v1 + 半行容错) + 小时封口 rollup + rewrite 原子裁剪 + index.json + 启动 reconcile。
- **P3 清理与体量** (0.5-1 天): 冻结文件按龄淘汰 + `qb_traffic` 配置键全链 (enabled/sample_interval/raw_window/rollup_window, 含键面 fixture)。
- **P4 API 端点** (0.5-1 天): 三 GET + 栅格离散/null 语义 + 金清单 72→75。
- **P5 前端三图** (1-2 天): uPlot vendor + 双系列组件 + 三挂点 (全局弹层/抽屉页签/分组弹层)。
- **P6 真机收尾** (0.5 天): 报告 §11.2 五条 + C 特有三条 (长停机接续/组解散淘汰/半行手工构造)。

前置: ~~停机空洞表达~~ 已拍板 **null 断线** (26-10-03); 分组换 key 旧历史策略默认按「不保留」实施, **P4 前可改判** (计划 §04.3, 改判只动分组查询聚合层 + index 元数据, 不回改 P1-P2)。

## 子任务状态表

| 段 | 内容 | 状态 |
|----|------|------|
| ① 代码盘点 | 三图数据源盘点 (内存已有实时值 / 主循环 1.5s 增量同步 / 组级聚合) | 完成(26-10-03) |
| ② 外部调研 | 成熟方案调研与三方案选型 (A/B/C) + 前端库选型 (uPlot) | 完成(26-10-03) |
| ③ 报告撰写 | reports/26-10-03-0757 (13 节 dark 单文件) + reports/_index.md 登记 | 完成(26-10-03) |
| ④ 拍板记录回写 | 用户拍板 4 项回写报告 §08 | 完成(26-10-03) |
| ⑤ 收尾回写 | 立档 + activeContext 切片 + 主 issue 补状态日志 + kb.index + test.full | 完成(26-10-03) |
| ⑥ 方案C 拍板+计划 | 总方案 C + `<data_dir>/qb-traffic/` + null 断线拍板回执; 计划 26-10-03-0946 (12 节, 含分组 key 详细对比 §04) | 完成(26-10-03) |
| ⑦ P1 采样器核心 | internal 任务 + 三系列采样 + 差分基线/重置 + 单种环 (纯内存) | pending |
| ⑧ P2 dat 落盘 | writer/reader 半行容错 + 小时封口 rewrite + index/reconcile | pending |
| ⑨ P3 清理与体量 | 冻结淘汰 + qb_traffic 配置键全链 (含键面 fixture) | pending |
| ⑩ P4 API+金清单 | 三 GET + 栅格离散/null 语义 + 金清单 72→75 | pending |
| ⑪ P5 前端三图 | uPlot vendor + 双系列组件 + 三挂点 | pending |
| ⑫ P6 真机收尾 | 报告 §11.2 五条 + C 特有三条 | pending |

> 前置状态: 停机空洞已拍板 null 断线; 分组换 key 旧历史默认「不保留」(P4 前可改判, 计划 §04.3)。⑨ 依赖 config_key_surface fixture 同步 (计划 §06); ⑥-⑫ 段间依赖单向向下, 每段独立可提交。

## 进度日志

- **2026-10-03 可行性报告轮**: 主会话只委派, 4 个子智能体串行 (代码盘点 → 外部调研 → 报告撰写 → 拍板记录回写) 全部一次成功 0 异常失败。取证基线 c91be940, 收尾前已同步至 dd180a11。产出 `memory-bank/reports/26-10-03-0757-report-qb-traffic-charts.html` (13 节 dark 单文件, 58.1KB) + `reports/_index.md` 登记行 (专题 torrent-traffic-stats)。核心结论: 可行性高 —— 零新增 qB 请求; 推荐方案A + uPlot; 方案 B 判不满足需求, 方案 C 与 state_file 黄金法则有张力。
- **2026-10-03 拍板与收尾**: 用户拍板 4 项 (先不实施 / uPlot / 采样间隔与保留窗口可配置 / 两项策略后定), 拍板记录回写报告 §08。立档 (阈值 #4 命中: 已产出 reports/ HTML 制品) + activeContext 切片 + 主 issue 26-09-27-1248 补状态变更日志行 (状态保持 Open) + `kb.index` 重建。**零代码改动, docs-only 豁免新建基线切片** (依据: 同型先例 26-10-03-webui-delete-tag-scope-confusion「无代码变更沿用最近基线」; test.full 数字记本段, 基线事实源仍走 `kb.baseline` 不手抄): test.full 实测 (2026-10-03 08:47 单次采样) **2325 passed / 3 skipped / 31.30s**, 覆盖率 TOTAL **99%** (13531 语句 / 88 未覆盖 / 4542 分支 / 89 partial); `kb.index` 幂等重跑 7 个再生索引字节一致。
- **2026-10-03 方案C 拍板与实施计划轮**: 用户拍板 3 项 —— 总方案 **C** (推翻报告推荐 A, 数据落 `<data_dir>/qb-traffic/` 子目录) / 停机空洞 **null 断线** / 分组 key 策略**详细对比** (计划 §04 给三选项, 默认甲「不保留」待拍板, P4 前可改判)。产出 `memory-bank/plans/26-10-03-0946-plan-qb-traffic-charts-c.html` (12 节 dark 单文件, 50.4KB): 存储设计 (行式 dat v1 + index/reconcile + 冻结淘汰 + 单种不落盘)、采样器 (speed_curve_mod 同款自注册; **修正报告 §9.1** —— `_build_group_view` 系 web 层懒建 runtime.py:635, 采样器自算组级 sum 口径对齐 views.py:424-429/459-460)、`qb_traffic` 配置键 4 键全链 (**新发现**: `tests/fixtures/config_key_surface.txt` 键面冻结须同步, 报告未提此件)、null 断线栅格语义、P1-P6 派发 (≈6-8.5 人日; 报告 C 行 3-5 的差额 = 金清单/清理对账/键面/真机段显式化)。C 关键取舍: 差分基线不落盘 → state 零改动免 v4; raw 段落盘使 24h 段跨重启存活 (优于 A 内存环)。取证基线 0a66c7c0 (报告 c91be940 后 8 commit, 后端锚点零漂移, Explore 代理 15 项全量复核)。docs-only 豁免新建基线切片; test.full 实测 (2026-10-03 09:52, 首跑 2 处索引守卫红 = 新计划/档案改名后未重建, `kb.index` 后复跑) **2326 passed / 3 skipped / 27.47s**, 覆盖率 TOTAL **99%** (13531 语句 / 88 未覆盖 / 4542 分支 / 89 partial); `kb.docmap --check` 主键纪律 OK (357 份/211 专题) + 认领链 OK。
