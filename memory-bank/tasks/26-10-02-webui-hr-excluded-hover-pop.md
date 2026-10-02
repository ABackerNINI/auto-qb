# 26-10-02-webui-hr-excluded-hover-pop — WEBUI HR 排除辅种悬停弹窗补全

**Status:** Done
**Added:** 2026-10-02
**Updated:** 2026-10-02 19:56
**Summary:** 种子页命中 HR 排除表(按分类/标签排除)的辅种做种时长格 hover 真空 —— 2026-09-29 非文字化清理撤原生 title「已排除」后弹窗侧未接盘(排除态 hr_safety 组装层短路空串, hrPopData 对空档位一律不弹)。修法: record.py 排除匹配收敛单点 _hr_exclusion_hits + 新增 hr_excluded_by() 来源 token(tag/category/tag+category), hr_view_fields 双分支透出; hrPopData 排除行分支「已排除出 HR 管理」+ 依据行「命中 HR 排除表的分类规则…」(HR_EXCLUDED_BY_TEXT 映射, 前端不重算匹配); 三主题 CSS 成对 excluded 中性灰档(--fg-muted, 不占四档安全色)。种子页/辅种组成员行/追剧集行共用弹窗单点一处修三处生效。守阵: testhr_view_fields_excluded 扩展三命中形态 + 空配置键集、record 排除三测 token 断言、接线守阵 CSS 成对清单 +2、FakeTorrent 鸭子兼容补 hr_excluded_by。test.full 2292 passed + 3 skipped / 99%(27.5s @ f0c0f0ed, 基线 26-10-02-1956)。
**Topics:** webui-hr-popup

## 原始请求

用户: 「种子页做种时长按分类排除的辅种没有鼠标hover信息展示, 按照现有的信息展示风格添加」。

## 思考过程与决策

- **根因取证**: 做种时长格 hover 走 `hrPopEnter → hrPopData` 悬停弹窗(26-09-26-webui-hr-popup), 但 `hrPopData` 对无档位行(`!m.hr_safety || m.hr_safety === "none"`)返回 null 不弹; 而命中排除表的种子后端组装层刻意把 hr_safety 短路成空串(计划 26-09-30-0559 §5「不适用」空白)。2026-09-29 非文字化清理(hr-tooltip-overlap 坑)又撤掉旧原生 title 的「已排除」提示(HR_EXCLUDED_TITLE 退役) —— 两头都没接盘, 排除种子 hover 完全真空。
- **方案**: 按 hr-tooltip-overlap 处置口径「结论一律进 HR 弹窗(不回原生 title)」补弹窗分支, 不回退徽标/底线等行内视觉(那是 2026-09-29 用户拍板的非文字化定案, 不在本轮授权内)。
- **命中来源可见**: 用户措辞「按分类排除」—— 弹窗依据行应说明按什么排除。判定纪律「前端不得重算匹配」(views.py hr_view_fields 字段注释单点) ⇒ 后端必须透出来源 token: record.py 排除匹配收敛单点 `_hr_exclusion_hits`(返回 (标签命中, 分类命中)), `hr_excluded()` 改为其析因(bool 语义不变, 原 tag 命中早退变双查, 成本可忽略), 新增 `hr_excluded_by()` 输出 "tag"/"category"/"tag+category"(未命中空串); `hr_view_fields` 两个返回分支都带键(空配置分支全键集是前端字段一致性守阵的前提)。
- **文案与配色**: 结论复用详情抽屉同款短语「已排除出 HR 管理」; 依据行「命中 HR 排除表的分类规则/标签规则/标签与分类规则」(前端 HR_EXCLUDED_BY_TEXT 映射, 与 HR_SRC_BUCKETS 同一"后端 token 前端映射"范式); 弹窗 lane 新增 `excluded` 中性灰档(--fg-muted), 不占用 danger/failed/safe/warning 四档安全色 —— 排除行不属任何删除安全档位。
- **呈现边界**: 无轨道/站点值/滞后提示(kv 空、gauge null、lag false) —— 排除行站点侧字段本就为空, 且展示"要求 vs 已做种"会误导为仍受管束。
- **替换身**: 全量测试暴露 test_build_group_view_hr_tags/counts 把裸 FakeTorrent 直喂 `_build_group_view`, 按.helpers「FakeTorrent 鸭子兼容补」惯例镜像 `hr_excluded_by`(与 hr_excluded 同语义)。

## 实现计划

| # | 改动 | 主点 |
|---|---|---|
| 1 | record.py | `_hr_exclusion_hits` 单点 + `hr_excluded` 改析因 + 新增 `hr_excluded_by` |
| 2 | views.py | `hr_view_fields` docstring + 空配置/主路径双分支透出 `hr_excluded_by` |
| 3 | hr.js | `HR_EXCLUDED_BY_TEXT` 映射 + `hrPopData` 排除行分支(置顶于 hr_safety 判定前) |
| 4 | 三主题 CSS | prism views.css / atlas·console dialogs.css 成对 `.hp-dot.excluded` + `.hp-verdict.excluded` |
| 5 | 测试 | testhr_view_fields_excluded 扩展; test_torrents 排除三测 token 断言; 接线守阵 CSS 清单 +2; helpers.FakeTorrent 镜像 |

## 子任务状态表

| # | 子任务 | 状态 |
|---|---|---|
| 1 | 根因定位(弹窗空档位短路 + title 退役真空) | Done |
| 2 | 后端来源 token 单点 + 视图透出 | Done |
| 3 | 前端弹窗分支 + 三主题灰档 | Done |
| 4 | 守阵扩展 + 全量验证 | Done |

## 进度日志

- **2026-10-02 19:56**: 完成全部改动与验证。定向 7 passed(test.one -k hr); 全量 test.full **2292 passed + 3 skipped / 99%**(27.5s, @ f0c0f0ed, 基线切片 26-10-02-1956)。第一版双命中用例漏给 rec.category 赋值当场红, 修正后绿。未提交 → 用户发「提交」后随主提交入库。
