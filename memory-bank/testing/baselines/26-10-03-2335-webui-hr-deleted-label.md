# 基线切片 26-10-03-2335 — WEBUI HR 切换钮文案二次修订

> 摘要: 用户二次驳回切换钮文案「显示未做种 / 只看做种中」——「未做种」实为本地已删除, 「做种中」反向态含暂停等。改「显示已删除种子 (N) / 只看本地仍在列 (M)」, 空态文案与注释/守阵标签换词 + 加旧措辞零残留断言。

- 时间: 2026-10-03 23:35 (GMT+8)
- 分支: develop @ (本轮回写件, 待用户提交指令)
- 命令: `commands run test.full`
- 实测: **2416 passed + 3 skipped, 45.75s, 覆盖率 99%** (Required coverage of 98% reached. Total coverage: 98.76%)
- 改动面: `src/auto_qb/webui/static/shared/hr_status.js`(可见文案 3 处 + 注释 4 段)、`src/auto_qb/webui/static/shared/tpl/settings-detail.html`(模板注释 1 处)、`tests/test_web.py`(守阵 docstring ×2 + 扫描标签 ×2 + 断言换词 + 新增旧措辞零残留断言)
- 未验证面: 真机走查(需真实 qB + HR 数据)仍待用户执行
