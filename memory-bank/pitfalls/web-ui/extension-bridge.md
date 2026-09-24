# 浏览器扩展 ↔ 本地端点

> 摘要: 扩展是**装在用户浏览器里**的交付物 —— pytest 跑不到它的运行期, 而浏览器 API 的报错几乎全指向不了根因; 2026-09-24 用户实测踩到两条(裸域名喂给权限 API / 端点没起只报 `Failed to fetch`), 2026-09-25 又踩到一条(`active:false` 的后台标签仍被抬出来抢版面)。
> 触发: 浏览器扩展, chrome 扩展, MV3, permissions.request, Invalid value for origin pattern, Missing scheme separator, Failed to fetch, host_permissions, localhost, 127.0.0.1, 本地端点, 归一化用户输入, 后台标签, tabs.create, active false, 抢焦点, 弹窗, 隐藏窗口, windows.create, 直取, fetch, credentials include, SameSite, 登录页, 离屏, offscreen, popup

## 两条实测报错 → 根因 → 处置

| 用户看到的 | 真实根因 | 处置 |
|---|---|---|
| `Invalid value for origin pattern pt.btschool.club: Missing scheme separator.` | 站点权限那一栏填了**裸域名**, 而 `chrome.permissions.request` 只接受**匹配模式**(必须带 scheme); 且它是**未捕获的 Promise 拒绝**, 页面上只留一行英文红字 | 输入先归一化: 裸域名补 `https://` 再补 `/*` ⇒ `https://pt.btschool.club/*`; 授权调用包 `try` + 逐个模式报错(一条坏不拖垮整批) |
| `TypeError: Failed to fetch` | ① 后端**端点根本没起** —— 它要三个开关同时满足(`hr_check.enabled` + 至少一个站点 `mode != off` + `hr_check.channel.enabled`), 缺一就没有监听, 浏览器只会给这一句; ② 地址写法不对(`127.0.0.1:8788` 无 scheme 会被当**相对地址**解析到扩展自己的 origin); ③ `localhost` 解析到 IPv6 回环而后端只 listen `127.0.0.1`; ④ 写成 `https://`(后端端点不提供 TLS) | ① 把手写清单写进文档最显眼处 + 选项页加**自测端点连通**按钮, 把"连不上 / 401 / 403"分开; ② 端点也走归一化(补 scheme / `localhost` 折成 `127.0.0.1` / 协议固定 `http`); ③ `host_permissions` 同时给 `127.0.0.1` 与 `localhost`、`[::1]` 别名 |
| 「抓数据时浏览器被弹到前台 / 开出一个新标签或新窗口」(用户 2026-09-25 两轮实报) | 页面取数原本需要真实渲染的 DOM ⇒ 只能开标签/窗口; 而 `chrome.tabs.create({active:false})` **只保证「不是那个窗口的活动标签」**, 不保证窗口不被抬起来; 换成自建窗口 + `state:'minimized'` 后, 用户又看到**新窗口**弹出 —— 最小化在部分平台仍会先显示一下 | ① **能直取就别开界面**(见下方口径) ② 真要渲染就用**离屏 popup 窗口**(`left/top = -32000` + `type:'popup'` + `focused:false`), 用完连窗口一起删 ③ 加**焦点守卫**(被抢则把焦点还回原窗口) |

## 硬约束

- **用户输入一律先归一化, 再交给浏览器 API 或落盘** —— "直接喂原始输入"的代价是**看不懂的报错 + 未捕获拒绝**。
  归一化要覆盖: 补 scheme、主机别名归一、协议归一、非法输入**逐条**报错而不是整批失败。
- **网络层失败只有一句 `Failed to fetch`** ⇒ 必须自己翻译成可操作清单(后端在跑吗 / 哪几个开关 / 端口 / 主机写法),
  并把自测做成按钮(用户点一下就知道是"连不上"还是"401 token 不对"还是"403 来源被拒")。
- **归一化只留一份**: 选项页与后台 service worker 各写一遍必然漂移, 而漂移的症状是"配了不生效"。
  做法: 抽成纯函数文件, 选项页 `<script>` 载入、后台 `importScripts()` 载入, pytest 侧用 node 直接 eval 它跑用例。
- **`unhandledrejection` 兜底**: 事件回调里任何漏网的拒绝都要落到状态栏, 否则用户只能对着红字干看。
- **端点"何时才会启动"要写在文档第一屏**: 后端保守默认(全关)是对的, 但用户不会自己推出"要开三个开关"。
- **后台取数不得借用用户的窗口**: 「后台标签」≠「不影响用户」—— `active:false` 管不住窗口被抬升,
  而 `state:'minimized'` 也不是灵药(实测会被用户看成「弹出一个新窗口」)。真口径是**分层**:
  ①**零界面优先** —— 服务端渲染的页面用扩展后台的 `fetch(credentials:'include')` 直取, 连标签都不开;
  ②只有「没表格 / 出现密码输入框」这类**通用结构信号**才升级到渲染通道;
  ③渲染通道用**离屏 popup**(`type:'popup'`, 屏幕外坐标, `focused:false`, 逐个降级尝试), 用完删窗口,
  并带一道**焦点守卫**。代价: 最小化/离屏窗口里的页面脚本可能被节流 ⇒ 只在兜底路径上, 且有 60s 上限。

## 直取与渲染的分工(2026-09-25 定型)

- **直取优先的理由不只是“安静”**: 它更快、不需要界面权限, 也不受窗口/标签生命周期影响。
  站点侧页面(NexusPHP 这类)本来就是**服务端渲染**的表格 ⇒ 直取即可。
- ❗**必须留一道 SameSite 安全网**: 无 `SameSite` 属性的 cookie 按 Lax 对待, 而扩展发起的 fetch 算
  **跨站子资源请求** ⇒ 有可能不带 cookie 而拿到**登录页**。此时若只有一个“有没有表格”的判据,
  登录页(它确实有表格)会被当成正常页面 ⇒ 后端把它读成“表头缺失/疑似改版”, **把排查引到错误方向**。
  所以升级判据要加上「**页面里有密码输入框**」这条与站点无关的结构信号(守阵
  `test_page_fetch_renders_when_direct_fetch_hits_login_page`)。

## 守阵

`tests/test_extension_proxy.py`(**12 条**): manifest 作用域(MV3 / 只申请回环 / **绝不 `<all_urls>`** / 站点走可选权限) ·
**真跑** `normalize.js`(裸域名 / localhost / https / 非法输入) · 归一化只有一份且载入顺序正确 ·
**与后端协议常量对照**(端点路径 / 鉴权头 / 回传字段名, 用 `HrResult.from_json` 实测) ·
调用顺序(归一化先于权限/存储 API) · 不得留裸拒绝 ·
**用假 chrome API 真跑** `background.js` 的四个场景(直取零界面 / 内容不像页面时用离屏 popup / 登录页也得升级 /
焦点被抢后还回去)。

⚠ 红验过: 去掉“补 scheme”那行 ⇒ `test_normalizers_behave` 当场变红;
强制走渲染通道 ⇒ `test_page_fetch_is_headless_when_html_looks_fine` 当场变红。
⚠ `node --check` **看不见**运行期错(重构时就真出现过"本地副本删了、引用还在"的 `ReferenceError`), 所以这里必须**执行** JS 而不是只查语法。
