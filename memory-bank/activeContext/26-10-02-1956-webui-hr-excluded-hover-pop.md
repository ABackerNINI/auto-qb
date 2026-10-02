# webui HR 排除辅种悬停弹窗补全 — Done

> 摘要: 用户实报种子页按分类排除的辅种做种时长格 hover 无信息。根因: 26-09-29 非文字化清理撤原生 title「已排除」后弹窗侧未接盘(排除态 hr_safety 组装层短路空串, hrPopData 对空档位一律不弹)。修法: record.py 排除匹配收敛单点 _hr_exclusion_hits + 新增 hr_excluded_by() 来源 token(tag/category/tag+category), hr_view_fields 双分支透出; hrPopData 排除行分支「已排除出 HR 管理」+ 依据行「命中 HR 排除表的分类规则…」; 三主题 CSS 成对 excluded 中性灰档(--fg-muted)。种子页/辅种组成员/追剧集共用单点一处修三处生效。守阵四处扩展 + FakeTorrent 鸭子兼容补。test.full 2292 passed + 3 skipped / 99%(27.5s @ f0c0f0ed, 基线 26-10-02-1956)。档案 tasks/26-10-02-webui-hr-excluded-hover-pop。
> 最后活动: 2026-10-02 19:56
