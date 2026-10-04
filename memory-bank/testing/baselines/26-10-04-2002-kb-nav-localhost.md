# 基线切片 26-10-04-2002 — kb.nav 打开地址改 localhost (监听仍绑 127.0.0.1)

> 摘要: 用户「kb.nav 使用 localhost 地址打开, 127 地址有历史遗留问题」。nav_server.py 拆出两个常量
> `BIND_HOST`(仍 127.0.0.1, 只绑回环 IPv4, sidefx 放行) / `OPEN_HOST`(改 localhost); `serve()` 里监听用
> BIND_HOST、浏览器打开与启动行用 `http://localhost:<port>`, bind 失败提示行沿用 BIND_HOST。配置端
> `.commands/kb/config.toml` 的 kb.nav note 同步为「默认绑 127.0.0.1:8765、浏览器开 localhost:8765」。
> **零守阵增减**(纯常量 / 接线改动, 用户只要求改行为), 故测试数持平。

> 基线时间: 2026-10-04 20:02
> 档案: memory-bank/activeContext/26-10-04-0952-kb-nav-page.md (第五跟进轮)

**Refs:** memory-bank/activeContext/26-10-04-0952-kb-nav-page.md · .commands/kb/config.toml

- 分支: develop @ f498bc8a (+ 本轮未提交改动: .agents/skills/memory-bank/scripts/nav_server.py /
  .commands/kb/config.toml / memory-bank/activeContext/26-10-04-0952-kb-nav-page.md /
  memory-bank/progress/implemented-tooling.md / 本切片)
- 命令: `commands run test.full`(Windows, 单次采样 —— 耗时口径见 testing/baseline.md「必须带区间」)
- **实测 (Windows)**: **2515 passed + 4 skipped, 39.92s (引擎计 41.5s), 覆盖率 TOTAL 99%**
  (14821 语句 / 152 未覆盖 / 4964 分支 / 112 partial; 门槛 98% 达标)
- 相对上基线 (26-10-04-1849: 2515 passed + 4 skipped / 99% / 37.45s): passed **持平**(本轮无守阵增减);
  耗时 39.92s vs 37.45s 属单次采样噪声, 不构成回归(口径见 testing/baseline.md「必须带区间」)。
- 冒烟: `nav_server.py --no-open --port 8799` 启动行打印 `[nav] serving http://localhost:8799`;
  `curl localhost:8799/` 与 `curl localhost:8799/api/data` 均 **200**(证明本机 localhost 可回落到只绑
  IPv4 的服务, 无需改绑定); 测毕已 `taskkill` 停进程。
- Linux 侧未重测(nav 脚本纯 stdlib 无平台分支), 下次 `test.linux` 自然复核。
