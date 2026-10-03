# 基线 · 2416 passed + 3 skipped / 99% —— 修密码字段两条 Chrome 可访问性警告(补隐藏用户名 / 包 form)

> 摘要: 用户按一段对话里的推荐方法要求修 Chrome 控制台两条可访问性警告 ——
> ①「Password forms should have (optionally hidden) username fields」= 登录页三皮肤(atlas/prism/console)
> 密码表单只有密码框、无用户名字段; ②「Password field is not contained in a form」= 设置页共享行模板
> `shared/tpl/xtpl.html` 的密码控件(如 `qbittorrent.password` / `hr.password`)裸 input 无 form 祖先。
> 修法: 登录表单内补 `type="text" autocomplete="username"` 的 `display:none` 隐藏用户名槽位;
> xtpl 新增 `f.kind === 'password'` 独立分支, 控件包进 `display:contents` 的 `<form @submit.prevent>`
> (form 不生成盒子, 控件仍作 `.hb-ct` 的 flex 子项, 布局零变化)并补同款隐藏用户名。
> 纯前端模板改动(3 个 shell `index.html` + `shared/tpl/xtpl.html`), 无 JS / 后端面变化。
> 基线时间: 2026-10-03 22:57, develop @ 7cdf555a + 工作区(本轮回写件未提交)。
> Linux 侧: 待补(仅 Windows 侧重测, 见 baseline.md 常驻警告)。

**Refs:** memory-bank/tasks/26-10-03-webui-password-form-a11y.md

TOTAL **2416 passed + 3 skipped / 99%**(14,395 语句 / 131 未覆盖 / 4,810 分支 / 104 partial,
test.full 39.3s, rc=0)。
相对上一切片(26-10-03-2228: 2416 passed + 3 skipped / 99%)**passed 持平**, 语句 / 分支数持平 ——
本单为模板内联改动, 无新增 / 删除用例(既有守阵 `test_frontend_template_split_wiring` 的聚合标签配平 /
shell ≤200 行 / 单分片 ≤400 行, 与 `test_frontend_hub_field_*` 的控件覆盖 / `:disabled` 计数,
均覆盖本次改动)。