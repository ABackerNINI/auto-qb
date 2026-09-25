# 给用户的访问地址只能写 localhost

> 摘要: 启动日志 / README / dev 脚本里指向本程序 WEB UI 的地址**只能**写 `localhost`, 不能写 `127.0.0.1`(2026-09-25 落地, 起因: 两者在浏览器眼里是两个 origin, 且 `127.0.0.1` 那份 localStorage 更容易被浏览器清掉); 而**绑定地址** `config.web.host` 恰恰相反 —— 必须留 `127.0.0.1`, 两件事混在一个变量里写就是本坑的复发形态。
> 触发: 启动日志, WEB UI 已启动, 访问地址, 打开浏览器, 127.0.0.1, localhost, origin 隔离, localStorage 被清, 偏好回默认, 改文档里的地址, dev_webui, display_host

## 绑定地址 ≠ 展示地址

- **触发**: 改 `webui/server/lifecycle.py` 的启动日志、README 快速开始、`scripts/dev_webui.py` 里"浏览器打开 …"那一行;
  或全局搜 `127.0.0.1` 想"顺手统一改掉"。
- **判别**: ①**绑定地址** = `config.web.host`(默认 `127.0.0.1`), 决定监听面, **不要改成 `localhost`** ——
  它会被解析成 `::1` + `127.0.0.1` 双栈绑定, IPv6 不可用的机器上可能整段启动失败;
  ②**展示地址** = 打印给用户 / 喂给 `webbrowser.open()` 的那个串, 回环**必须**写 `localhost`
  (服务只听 `127.0.0.1` 时 `localhost` 照样通, 2026-09-24 实测 200)—— 用户每次都落在同一个 origin,
  才不会"换着打开 = 偏好回默认"(机制见 [web-ui/columns-persist.md](../web-ui/columns-persist.md):
  浏览器站点级「关闭窗口时清除 Cookie 和站点数据」按 host 匹配, 本机取证到的例外正挂在 `127.0.0.1` 上)。
- **处置**: 统一走 `auto_qb.infra.utils.display_host()`: 回环的四种写法(IPv4 / IPv6 / IPv4-mapped)
  折成 `localhost`, **对外地址(含 `0.0.0.0`)原样返回** —— 把暴露面也折掉等于掩盖风险;
  非字符串原样返回(调用方都在日志路径上, 不该炸)。已接三处: `webui/server/lifecycle.py`
  (启动成功 / 失败两行)、`scripts/dev_webui.py`、`README.md` 快速开始。
- **守阵**: `tests/test_utils.py::test_display_host`(回环折 localhost / 对外原样 / 异常入参不炸)。

## 另有两类 `127.0.0.1` 不许跟着改

- **触发**: 上面那条"统一改掉"的冲动落在别处时。
- **判别**: ①**HR 取数端点**(`hr/server.py` 启动日志 / `hr/report.py` 端点行 / `hr_status.js`
  「监听 127.0.0.1:端口」/ 扩展 `options.html`·`normalize.js`·`README.md`): 消费方是**扩展的 fetch**,
  不经过浏览器页面, 没有 localStorage 这层问题; 而后端只 bind `127.0.0.1`, `localhost` 可能解析到 `::1`
  ⇒ **扩展连不上**(`normalize.js` 也只是把用户填的 `localhost` 折回 `127.0.0.1`)。
  ②**连接类地址**(`config.qbittorrent.host` 默认 / 托盘「打开 qBittorrent WebUI」): 同理,
  qB 通常只听 IPv4, 填 `localhost` 可能解析到 `::1` 而连不上。
- **处置**: 只改"用户在浏览器里打开本程序界面"这一条路径, 上面两类原地保留。
