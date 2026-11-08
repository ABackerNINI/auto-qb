# UI 冒烟工装: 无头浏览器 + Vue 生产版句柄

> 摘要: 前端视觉改动的真浏览器冒烟: Vue 生产版拿不到 `app._instance`、无头 Edge 的 virtual-time 与 SSE 坑 —— 都有固定解法。
> 触发: UI 冒烟, 截图, 无头浏览器, 弹窗驱动, Vue 实例, createApp, 截图工装

### Vue 3 生产版 `app._instance` 恒为 null, 链路静默拿不到组件代理

- **触发**: 想在浏览器外驱动 Vue 应用(开弹窗/改状态)而按惯例写 `document.getElementById("app").__vue_app__._instance.proxy`(2026-09-26 按钮体系冒烟实测)。
- **判别**: 键**存在但值恒 null** —— `Object.keys(__vue_app__)` 里能看到 `_instance`, 取值却是 null; 轮询到超时也拿不到(挂载早已完成、页面渲染正常, 极易误判成"挂载没完成")。根因: 生产构建里 `app._instance = vnode.component` 只在 `__DEV__ || __FEATURE_PROD_DEVTOOLS__` 分支赋值, `vendor/vue.global.prod.js` 两者皆无。
- **处置**: 不摸内部对象, 改为**包装 createApp 捕获 mount 返回值** —— 在 `<script src="/shared/app.js">` 之前注入一小段(仅存在于冒烟工装的注入层, 不进仓库产物): 包一层 `Vue.createApp`, 劫持 `app.mount`, 把返回的组件代理存到 `window.__VM`; 驱动脚本轮询 `window.__VM` 即可调用任意 method(如 `vm.openAddTorrent()`)。

### 无头 Edge 截图驱动的三个固定写法

- **触发**: 搭 stub + 无头截图的 UI 冒烟工装(环境无 playwright 时; `msedge --headless=new --screenshot` 即可用)。
- **判别**: ①`--virtual-time-budget` 会快进 setTimeout 但**不等待**挂起的 SSE 长连 —— `/api/events` 要立即回一段注释后关闭, 否则驱动时序不稳; ②Vue 渲染完成晚于 load 事件 —— 驱动必须轮询等句柄, 且动作后把状态写进 `documentElement` 的 `data-drv` 属性用 `--dump-dom` 验到哪一级(写 document.title 不可靠); ③`--screenshot` 的目标路径**必须用 Windows 原生路径**(cygpath -w), 仓库相对路径会静默不落盘。
- **处置**: 驱动脚本由 stub 服务器在响应 index.html 时注入(替换 `<script src="/shared/app.js">` 前插 + `</body>` 前插), 按 `?shot=` 参数分发动作; 整页长图用超高 `--window-size` + Pillow 切片。工装样例: 临时目录 `stub_ui_server.py`(不入仓库)。

### 工装驱动不到的分支, 静态证据补位并如实报告

- **触发**: 某些 v-if 分支(如登录遮罩)在免鉴权 stub 下驱动不出(authRequired 置回后主界面仍渲染)。
- **判别**: 驱动标记停在中间态(data-drv 停在 `vm` 未到 `act-*`)。
- **处置**: 该分支改用静态证据(类名与 CSS 规则逐条对应)核验, 并在交付说明里**如实写明**"此项仅静态验证", 不得含糊成"已验证"。
