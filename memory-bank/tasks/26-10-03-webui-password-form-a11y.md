# 26-10-03-webui-password-form-a11y — WEBUI 密码字段两条 Chrome 可访问性警告修复

**Status:** Done
**Added:** 2026-10-03
**Updated:** 2026-10-03 22:57
**Summary:** 用户按一段对话里的推荐方法要求修复 Chrome 控制台两条可访问性警告: ①「Password forms should have (optionally hidden) username fields」来自登录页三皮肤(atlas/prism/console)的密码表单 —— 只有密码框、无用户名字段; ②「Password field is not contained in a form」来自设置页共享行模板 `xtpl.html` 的密码控件(如 qbittorrent.password / hr.password) —— 裸 input 无 form 祖先。修法: 登录表单内补 `type="text" autocomplete="username"` 的 display:none 隐藏用户名槽位; xtpl 新增 `f.kind === 'password'` 独立分支, 控件包进 `display:contents` 的 `<form @submit.prevent>`(form 不生成盒子, 控件仍作 `.hb-ct` 的 flex 子项, 布局零变化)并补同款隐藏用户名。纯模板改动 4 文件, JS / 后端零改动。
**Topics:** webui
**Refs:** memory-bank/testing/baselines/26-10-03-2257-webui-password-form-a11y.md

## 原始请求

用户上传一段说明两条 Chrome 可访问性警告的文案, 要求「根据对话中的推荐方法修复报错」:

- `[DOM] Password forms should have (optionally hidden) username fields for accessibility`
- `[DOM] Password field is not contained in a form`

## 思考过程与决策

- **定位两处来源**(grep 全静态目录): 生产密码控件只有两类 —— ①三皮肤 shell 的登录表单(`v-model="tokenInput" type="password"`, 已在 `<form>` 内但缺用户名字段 → 警告1); ②`shared/tpl/xtpl.html` 的 `f.kind === 'password'` 叶子控件(无 form 祖先 → 警告2)。`resources/*-templates/` 是设计观摩稿(不随服务下发), 不动。
- **警告1修法**: 按推荐在密码框前补 `type="text" name="username" autocomplete="username"` + `display:none` 的隐藏槽位 —— Chrome 措辞本身写明「optionally hidden」, 即用户名字段可视觉隐藏(但不可是 `type="hidden"`)。访问密钥无真实用户名, 取固定占位 `auto-qb` 与密码关联。
- **警告2修法取舍**: 「包进 form」若用默认块盒会改变 `.hb-ct` flex 布局(输入框不再直接是 flex 子项, `.hb-ct .hb-input { flex: 0 1 250px }` 失效) —— 改用 `style="display:contents"` 让 form **不生成盒子**, 子控件继续作 `.hb-ct` 的 flex 子项, 视觉零变化。form 无提交语义, `@submit.prevent` 兜底。同时给该 form 补隐藏用户名槽位 —— 否则加了 form 会立刻触发警告1(缺用户名)。
- **不重复造抽象**: xtpl 内保留一条 `form(密码) / input(其余文本)` 二分链, 只重复输入框元素; 单位 span 与「跟随全局」按钮保持单份共享, 避免多份漂移。
- **不动 `resources/`**: 设计观摩稿(`01-login.html` / `settings-page-templates`)白底极简形态是设计本体(conventions/webui.md 例外条款), 且不随服务下发, 不套本次修复。

## 实现计划

| # | 改动 | 主点 |
|---|---|---|
| 1 | atlas / prism / console `index.html` | 登录表单密码框前补隐藏用户名槽位(`type=text autocomplete=username` + `display:none`) |
| 2 | `shared/tpl/xtpl.html` | 新增 `f.kind === 'password'` 分支: 控件包进 `display:contents` 的 `<form @submit.prevent>` + 隐藏用户名; 兜底文本框分支改回 `type="text"` |

## 子任务状态表

| 子任务 | 状态 |
|---|---|
| 定位两处密码控件来源 | Done |
| 登录页三皮肤补隐藏用户名 | Done |
| xtpl 密码叶子包 form + 隐藏用户名 | Done |
| test.quick / test.full 回归 | Done |
| 基线切片 + 切片回写 | Done |

## 进度日志

- 2026-10-03 22:57: 全部完成。test.quick 2416 passed + 3 skipped; test.full **2416 passed + 3 skipped / 99%**(14,395 语句 / 131 未覆盖 / 4,810 分支 / 104 partial, 39.3s, @ 7cdf555a); 基线切片 `testing/baselines/26-10-03-2257-webui-password-form-a11y.md`。改动集中在模板, 无 JS / 后端面。未做真浏览器目检(登录 / 设置页需真 qB 起服务)。未提交(等用户指令)。