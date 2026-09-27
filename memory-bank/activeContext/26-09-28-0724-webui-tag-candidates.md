# WEBUI 标签候选剔除程序自动维护标签

> 摘要: 添加种子窗口/「标签/分类…」弹窗标签候选改走 /api/tags?exclude_auto=1 剔程序自动维护标签; 范围经拍板: 隐藏站点/HR/集数, MISSING/zSkipChecked 暂留, 弹窗共同携带标签并回保摘除。
> 最后活动: 2026-09-28 07:24

- 已完成: 范围排查(6 来源枚举 + 本机 22 站点实况) → 两项拍板(集数标签隐藏保摘除/事件标记暂留) → utils.auto_managed_tag_rules + /api/tags?exclude_auto=1 → 前端三处(shared add_torrent/dialogs/state) → 单测+端点测试 → test.full 1820 passed(基线 26-09-28-0724) → 档案 tasks/26-09-28-webui-tag-candidates.md。
- 待办: 等待用户说「提交」; 真机打开窗口确认候选观感(浏览器冒烟未跑)。
