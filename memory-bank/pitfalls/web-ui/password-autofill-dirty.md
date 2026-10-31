# 密码框的浏览器自动填充会凭空写脏配置树

> 摘要: 密码框的浏览器自动填充会凭空写脏配置树
> 等级: L0
> 触发: 有改动还没保存, 一进设置就脏, 自动填充, autofill, 密码框, 密码管理器, autocomplete, new-password, 脏标记凭空变真, 配置树被写

### 配置页的密码框被浏览器/密码管理器自动填充, 让脏标记凭空变真

- **触发**: 设置页里 `kind=password` 的字段(qB 密码 / WEB 密钥)被模板渲染成「隐藏 username + password」的**表单形状**(为消 Chrome 的可访问性警告), 而密码 input 没写 `autocomplete` —— 同源登录页(那里是 `autocomplete=current-password`)保存过凭据时, 浏览器 / 密码管理器把它当登录表单**自动填**, 并在**未聚焦**时派发 `input` 事件; 原 `@input="set()"` 把填充值原样写进配置树。2026-10-20 用户报「点进常规就显示有改动还没保存」即此形态。
- **判别**: ①症状只在**含密码框的分区**出现(本项目 = 常规的 qB 密码 / API Key / WEB 存取密钥, 以及 HR 在线核实的「端点密钥」—— 每个只有密码框的那一页都会中, 用户 2026-10-20 就先后报了这两页); ②框里显示的是掩码, 用户说不出改了哪一项; ③干净浏览器 / 没装密码管理器的环境**复现不了**(排查时别因此判「无缺陷」); ④浏览器实测判据: 对**未聚焦**的密码框赋值 + `dispatchEvent(new Event('input', { bubbles: true }))`, 旧实现 `cfgDirty` 立刻为真、actbar 翻「有改动还没保存」。
- **处置**: ①密码 input 加 `autocomplete="new-password"` —— 从源头劝退保存凭据的自动填充; ②写回改走专用 `setSecret(ev)`: **事件到达时 `document.activeElement !== el` 一律不写树**, 并 `el.value = this.textValue()` 把显示拉回树值(否则界面显示填充值、树里还是掩码, 两套值)。真实键入 / 粘贴 / 密码管理器下拉选取都必然先聚焦, 守卫不挡正常编辑; ③新增密码类字段照抄这两条 —— 模板只有一个密码分支, 全 kind 覆盖。
- **守阵**: `tests/test_webui_static_dom_page.py::test_frontend_password_field_ignores_autofill`(模板 `autocomplete` + `setSecret` 接线 + 守卫三件, 三皮肤聚合模板逐一断言); `e2e/views.spec.mjs` 两条(双皮肤共 4 条):「设置-常规: 密码框被自动填充不得造脏」(未聚焦 input 不造脏且显示回填 + 聚焦键入照旧写树)、「设置-HR 在线核实: 端点密钥同样不被自动填充写脏」(桩里无 hr_check 段, 用 page.route 现注入带 channel.token 的配置树 —— 以后 HR 若换专用控件/写回, 这条直接红)。
- **复发**: 0
