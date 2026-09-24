# auto-qb HR 取数代理(浏览器扩展)

一个**哑取数器**: 它只负责「在真实浏览器里取内容, 然后原样回传」, 不做解析、不做频控判断、
**不读也不传 cookie**。所有策略与解析都在 auto-qb 后端。

## 为什么是这个形态

- 站点访问必须带你的登录态, 但后端**不该持有 cookie**(Chrome 127+ 的 App-Bound Encryption
  已经让「后端直读 cookie 库」既不可靠也不合法; 手工填 cookie 等于把维护成本转嫁给你);
- 扩展跑在**你日常的浏览器**里, 登录态由浏览器自己带, cookie 全程不出浏览器;
- 页面用**后台标签页**取(不抢焦点, 拿的是渲染后 DOM, 能过 Cloudflare 挑战), `.torrent`
  由扩展的后台请求取(带 `credentials: 'include'`)。

## 安装

1. 打开 `chrome://extensions`(Edge 是 `edge://extensions`), 右上角开启 **开发者模式**;
2. 点 **加载已解压的扩展程序**, 选本目录(`extensions/hr-fetch-proxy`);
3. 点扩展的 **详情 → 扩展程序选项**(或在列表里点「扩展程序选项」)进入配置页。

## 配置

### 0. 先满足「端点会启动」的三个开关(缺一不可)

后端的本地端点只有在**同时**满足三件事时才启动; 任一没开, 扩展那边看到的就是一句
`TypeError: Failed to fetch`(浏览器对网络层失败只会给这句话, 查不出原因):

1. `hr_check.enabled: true` —— 总开关;
2. 至少一个站点 `trackers.<站点>.hr_check.mode` 不是 `off`(如 `partial`);
3. `hr_check.channel.enabled: true` —— 本实例装了扩展。

满足后, 后端启动日志会打一行(用这个端口去填扩展):

```
HR 取数通道端点已启动: http://127.0.0.1:8788(仅监听本机回环, 需 token 鉴权)
```

### 1. 后端侧(`config.yml`)

```yaml
hr_check:
  enabled: true
  channel:
    enabled: true
    port: 8788          # 同机多实例必须各不相同(被占 => 启动即报错)
    # token: ""         # 留空 = 自动生成到 <data_dir>/hr.token

trackers:
  pt.btschool.club:
    hr_check:
      mode: partial                  # 该站启用在线核实
      hr_page_url: "https://pt.btschool.club/myhr.php"
```

启动 auto-qb(主程序, 不是 `--hr-once` 走查)后, 密钥文件在 `<data_dir>/hr.token`(内容不打印到日志, 直接打开复制)。

### 2. 扩展侧(选项页)

地址写法有容错: **省 scheme 也行**, 保存时会自动归一化(但存进去的必须是归一化后的形式):

| 你写的 | 保存/授权时归一化为 |
|---|---|
| `127.0.0.1:8788` | `http://127.0.0.1:8788` |
| `http://localhost:8788/` | `http://127.0.0.1:8788`(localhost 可能解析到 IPv6 回环, 而后端只 listen `127.0.0.1`) |
| `https://127.0.0.1:8788` | `http://127.0.0.1:8788`(后端端点是明文 HTTP, 不提供 TLS) |
| `pt.btschool.club` | `https://pt.btschool.club/*`(Chrome 的站点权限只吃带 scheme 的**匹配模式**) |

```
① 实例端点(每行一个 JSON)
{"name":"本机","endpoint":"127.0.0.1:8788","token":"把 hr.token 的内容粘到这里"}

② 站点权限(每行一个站点, 只写域名也行)
pt.btschool.club
```

填完点 **保存**(会把归一化结果写回输入框, 看得见存的是什么), 再点 **申请站点权限** 授予站点访问权
(只申请你列出的站点, 不用 `<all_urls>`)。点 **自测端点连通** 先确认后端那边通了, 再点
**立即拉取一次** 走一整轮。

## 排障

| 现象 | 真实原因 | 怎么办 |
|---|---|---|
| `TypeError: Failed to fetch` | 后端端点**没在监听**(三个开关缺一 / 主程序没在跑 —— `--hr-once` 是只读走查, **不会**起端点), 或端口/主机写法不对 | 按上面 §0 逐个开关核对; 点选项页的 **自测端点连通**, 它会直接告诉你是「连不上」「401 token 不对」还是「403 来源被拒」 |
| `Invalid value for origin pattern xxx: Missing scheme separator.` | 站点权限那栏填了**裸域名**(如 `pt.btschool.club`), 而 Chrome 只收匹配模式 | 现在填裸域名也能用了(保存时自动补成 `https://pt.btschool.club/*`); 修正后重新 **保存** + **申请站点权限** |
| 拉清单报 `401` | 端点可达, 但 token 不对或该实例没启用通道 | 把 `<data_dir>/hr.token` 的内容整串复制到实例的 `token` 字段; 并确认 `channel.enabled: true` |
| 报 `403` | 非扩展 origin 被拒(或配了 `channel.extension_id` 但与本扩展 id 不一致) | 要么清空 `channel.extension_id`(靠 token 鉴权), 要么把本扩展 id 填进去 |
| 任务能拉但一直「无任务」 | 该站点未到刷新时机 / 数据还在有效期内 / 配额到顶 / 熔断中 | 看后端日志里该站点的 action 与原因(或跑 `auto-qb --hr-once` 只读走查看全景) |
| 站点页面取回来了但后端说「不完备」 | 分页没到底 / 档位没抓全 / 必填字段缺失超阈 | 确认 `hr_page_scopes` 含 A+B+C; 若页面确实改版, 后端会告警(改版只改后端, 扩展不用重装) |

## 怎么确认它在工作

- 选项页底部会显示每次轮询的结果(取了几条 / 回传 HTTP 状态), **自测端点连通** 会区分「连不上 / 401 / 403」;
- 后端日志(以及 `auto-qb --hr-once` 报告里的「取数通道」段)会显示端点、密钥来源与最近联系时间;
- 通道静默超过 `hr_check.channel_silence_warn` 会告警一次(浏览器没开 / 扩展被停用 / token 不一致)。

## 安全边界(设计如此, 不是省略)

| 项 | 做法 |
|---|---|
| cookie / passkey | 后端既不接收也不存储; 扩展不调用 `chrome.cookies`, 只回传页面 HTML 与 `.torrent` 字节 |
| 端点监听 | 仅 `127.0.0.1`; 必须带 `X-Hr-Token`, 无 token / token 不符 ⇒ 401 **且不写任何状态** |
| origin 白名单 | 只放行 `chrome-extension://`(配了 `channel.extension_id` 就只认那一个); 普通网页一律 403 |
| URL 白名单 | 任务 URL 只能由后端按配置拼出(域名 + 路径受限) ⇒ 端点不会变成「带登录态的任意站代理」 |
| 任务绑定 | 只有**后端确实派发过**的任务回传才被接受, 且回传 URL 域名须与任务一致 —— 伪造数据进不来 |
| 轮询节奏 | 由后端决定(扩展只按清单干活); 配额 / 熔断 / 时间窗的唯一权威在后端 |

## 已知限制

- 站点 `.torrent` 若校验 `Referer` 或要求 XHR 专用头, 可能取不到 —— 通道会把失败如实上报(计入退避),
  不会静默; 届时按站点实际情况调整策略(例如改由页面上下文取)。
- 扩展需要浏览器处于运行状态; 浏览器关闭期间通道静默, 后端保守回落「未核实」。
- 站点改版只需**改后端**(解析在后端), 扩展无需重装。
