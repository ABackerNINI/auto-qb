# WEBUI 密码字段 Chrome 可访问性警告修复

> 摘要: 用户按对话推荐修两条 Chrome 控制台可访问性警告 —— ①登录页三皮肤密码表单缺用户名
> (`Password forms should have username fields`); ②设置页 xtpl 密码控件不在 `<form>` 内
> (`Password field is not contained in a form`)。修法: 登录表单补 `display:none` 的
> `autocomplete=username` 隐藏槽位; xtpl 密码叶子独立分支, 控件包进 `display:contents` 的
> `<form @submit.prevent>`(布局零变化)并补同款隐藏用户名。纯模板 4 文件, JS / 后端零改动。
> 最后活动: 2026-10-03 22:57

## 已完成 (2026-10-03)

- **修复**: 三皮肤 shell [atlas](../../src/auto_qb/webui/static/atlas/index.html) /
  [prism](../../src/auto_qb/webui/static/prism/index.html) /
  [console](../../src/auto_qb/webui/static/console/index.html) 登录表单内补隐藏用户名槽位;
  [shared/tpl/xtpl.html](../../src/auto_qb/webui/static/shared/tpl/xtpl.html) 密码控件包 `display:contents` form + 隐藏用户名。
- **验证**: test.quick 2416 passed + 3 skipped; test.full **2416 passed + 3 skipped / 99%**。
- **基线**: [baselines/26-10-03-2257-webui-password-form-a11y.md](../testing/baselines/26-10-03-2257-webui-password-form-a11y.md)。
- **立档**: [tasks/26-10-03-webui-password-form-a11y.md](../tasks/26-10-03-webui-password-form-a11y.md)(阈值2: 改动 4 个源文件)。
- 未做真浏览器目检(登录 / 设置页需真 qB 起服务); 改动与推荐修法逐条对齐, 由静态守阵 + 全量测试兜底。

## 状态

修复与收尾完成, 待用户『提交』统一入库。