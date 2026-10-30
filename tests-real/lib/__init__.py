"""真机实测轨的公共件 —— 客户端 / 种子构造 / 伪 tracker / 守卫 (RM00 建立)

为什么自己写而不用 qbittorrent-api: 本机有三处硬约束(见 plan 26-10-31-0705 §02):
  1. 环境带 HTTP_PROXY —— 任何走默认 opener 的请求打到 127.0.0.1 都会被代理转成 502, 必须 ProxyHandler({});
  2. qB 5.2 的种子字段是 upspeed / dlspeed(不是 up_speed, 按后者读直接 KeyError);
  3. 36596 已改为本机免鉴权, 带错 token 反而 403 ⇒ 客户端要能降级重试。
"""
