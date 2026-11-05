# 浏览器冒烟 · 桩服务没起来/旧进程的处置与现场(外迁)

> 摘要: `pitfalls/testing/smoke.md`「桩服务没起来 / 起来的是旧进程」条的处置、复发现场与端口取号现状原文外迁(2026-11-05 压缩), 正文原样照搬。
> 触发: 桩服务, ERR_CONNECTION_REFUSED, Errno 10048, 端口占用, 旧进程, 代理, E2E_PORT, Get-NetTCPConnection

## 处置、复发与现状

- **处置**: ①起桩服务用**常驻后台任务**(`run_in_background`)—— `ui_harness.py` **长驻**(uvicorn.run 阻塞),
  别指望 `dev.harness` 会返回; 不要 `(cmd &)`;
  ②起完**立刻看 harness 日志首行**(打印实绑地址与种子/组数), 显式指定口时若被占就换端口;
  ③怀疑服务不对先 `curl <base>/prism/` 必须 200(只 `curl /api/...` 会被旧进程蒙过去)。
  复发: 4 —— 多 clone 下 8099/8137 反复被**别会话 / 别 clone 的残留 harness** 占用(uvicorn 起不来只打
  `[Errno 10048]` 一行, 后台起桩任务全 failed 但无一行有效日志), 换 `E2E_PORT` 复跑即过, 勿杀占用进程;
  直接**复用**残留服务做交互探针, 改完代码验证"全 PASS"其实验的是**别的 clone 的旧代码**
  (残留 harness serve 的是它自己 clone 的静态目录; 12 项探针在旧代码上照样大半通过, 假信心比超时更危险)。
  判据: 怀疑服务归属时 `page.evaluate` fetch 静态 JS 比对特征串(如刚加的方法名), 不在 ⇒ 服务不是本 clone 的。
  处置: 改代码验证类冒烟**一律自己起桩**(后台任务 + 新端口), 残留服务只读不验。
  代理变体: 本环境有 HTTP_PROXY 透明代理, `curl` 直连被占端口拿到的是代理的 502「upstream connect failed」,
  而 node/Playwright 直连却 200 —— **curl 通不通不能当判据**, 以
  `Get-NetTCPConnection -LocalPort N -State Listen` 现查归属为准。
  *现状(2026-11-03, 计划 26-11-03-0316): e2e 端口已改为由脚本取号(`ui_harness --port 0` +
  Playwright `webServer.wait` 捕获回传), `E2E_PORT` 已取消(设置即报错); 残留桩归属按实绑端口 +
  命令行里的 clone 路径判。以上复发记录保留为当时的现场。*
