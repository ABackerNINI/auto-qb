# 浏览器扩展 ↔ 本地端点

> 摘要: 扩展是**装在用户浏览器里**的交付物 —— pytest 跑不到它的运行期, 而浏览器 API 的报错几乎全指向不了根因; 2026-09-24 用户实测踩到两条(裸域名喂给权限 API / 端点没起只报 `Failed to fetch`)。
> 触发: 浏览器扩展, chrome 扩展, MV3, permissions.request, Invalid value for origin pattern, Missing scheme separator, Failed to fetch, host_permissions, localhost, 127.0.0.1, 本地端点, 归一化用户输入

## 两条实测报错 → 根因 → 处置

| 用户看到的 | 真实根因 | 处置 |
|---|---|---|
| `Invalid value for origin pattern pt.btschool.club: Missing scheme separator.` | 站点权限那一栏填了**裸域名**, 而 `chrome.permissions.request` 只接受**匹配模式**(必须带 scheme); 且它是**未捕获的 Promise 拒绝**, 页面上只留一行英文红字 | 输入先归一化: 裸域名补 `https://` 再补 `/*` ⇒ `https://pt.btschool.club/*`; 授权调用包 `try` + 逐个模式报错(一条坏不拖垮整批) |
| `TypeError: Failed to fetch` | ① 后端**端点根本没起** —— 它要三个开关同时满足(`hr_check.enabled` + 至少一个站点 `mode != off` + `hr_check.channel.enabled`), 缺一就没有监听, 浏览器只会给这一句; ② 地址写法不对(`127.0.0.1:8788` 无 scheme 会被当**相对地址**解析到扩展自己的 origin); ③ `localhost` 解析到 IPv6 回环而后端只 listen `127.0.0.1`; ④ 写成 `https://`(后端端点不提供 TLS) | ① 把手写清单写进文档最显眼处 + 选项页加**自测端点连通**按钮, 把"连不上 / 401 / 403"分开; ② 端点也走归一化(补 scheme / `localhost` 折成 `127.0.0.1` / 协议固定 `http`); ③ `host_permissions` 同时给 `127.0.0.1` 与 `localhost`、`[::1]` 别名 |

## 硬约束

- **用户输入一律先归一化, 再交给浏览器 API 或落盘** —— "直接喂原始输入"的代价是**看不懂的报错 + 未捕获拒绝**。
  归一化要覆盖: 补 scheme、主机别名归一、协议归一、非法输入**逐条**报错而不是整批失败。
- **网络层失败只有一句 `Failed to fetch`** ⇒ 必须自己翻译成可操作清单(后端在跑吗 / 哪几个开关 / 端口 / 主机写法),
  并把自测做成按钮(用户点一下就知道是"连不上"还是"401 token 不对"还是"403 来源被拒")。
- **归一化只留一份**: 选项页与后台 service worker 各写一遍必然漂移, 而漂移的症状是"配了不生效"。
  做法: 抽成纯函数文件, 选项页 `<script>` 载入、后台 `importScripts()` 载入, pytest 侧用 node 直接 eval 它跑用例。
- **`unhandledrejection` 兜底**: 事件回调里任何漏网的拒绝都要落到状态栏, 否则用户只能对着红字干看。
- **端点"何时才会启动"要写在文档第一屏**: 后端保守默认(全关)是对的, 但用户不会自己推出"要开三个开关"。

## 守阵

`tests/test_extension_proxy.py`(8 条): manifest 作用域(MV3 / 只申请回环 / **绝不 `<all_urls>`** / 站点走可选权限) ·
**真跑** `normalize.js`(裸域名 / localhost / https / 非法输入) · 归一化只有一份且载入顺序正确 ·
**与后端协议常量对照**(端点路径 / 鉴权头 / 回传字段名, 用 `HrResult.from_json` 实测) ·
调用顺序(归一化先于权限/存储 API) · 不得留裸拒绝。

⚠ 红验过: 去掉"补 scheme"那行 ⇒ `test_normalizers_behave` 当场变红。
⚠ `node --check` **看不见**运行期错(重构时就真出现过"本地副本删了、引用还在"的 `ReferenceError`), 所以这里必须**执行** JS 而不是只查语法。
