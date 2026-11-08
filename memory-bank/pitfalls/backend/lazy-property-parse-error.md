# 解析器的异常面在惰性 property 上: try 只包构造等于没包

> 摘要: 给解析器套 `try/except` 做 fail-closed 时, 若只把**构造函数**包进去, 而真正会抛的是结果对象的**惰性 property**(如 `urlsplit(...).port`), 异常照样穿透 —— 安全闸门于是变成 500, 而不是它该给的 403。
> 触发: 给解析/判定函数加 try 收口; 同族解析器有两侧(如 Host 头 / Origin 头); 生产路径出现「畸形输入报 500」。

## 条目

- **触发**: 2026-10-20(issue 26-10-20-2230)执行覆盖率提升计划第二轮补 fail-closed 断言时撞见: `_origin_allowed` 里 `parts.port` 写在 `try: urlsplit(origin)` **之外**, 喂 `http://127.0.0.1:notaport` 时 `ValueError: Port could not be cast to integer value as 'notaport'` 直接穿透到 FastAPI 全局异常处理。根因确认: `urlsplit` 本身**不抛**(它只切串), 抛的是随后访问 `.port` 那一刻 —— property 内部才做 `int()` 与越界校验。同文件上方的 `_host_header_parts` 早已把 `.port` 包进 try(返回 `("", None)`), 两侧口径不一致 ⇒ 同一份畸形输入, Host 侧 fail-closed、Origin 侧 500。
- **判别**: ①看 traceback 的**最后一行**落在哪 —— 落在标准库(`urllib/parse.py` 的 property)而不是你自己的调用行, 就是这个形状。②构造与取值**分处两行**是高危写法:`parts = urlsplit(x)` 独占 try, 后面再用 `parts.scheme` / `parts.hostname` / `parts.port`。③同族解析器 grep 一遍: 一侧有 try、一侧没有, 漏的那个迟早出事。④**只对"看起来会抛"的构造处加 try 是自证**: 没造过畸形输入跑一遍, 等于没验。
- **处置**: 把**构造 + 全部属性取值**一并放进同一个 try, `except ValueError` 分支返回 fail-closed 值(拒绝, 不是放行):
  ```python
  try:
      parts = urlsplit(origin)
      scheme = parts.scheme
      hostname = parts.hostname
      origin_port = parts.port   # property, 端口段非数字/越界时抛 ValueError
  except ValueError:
      return False
  ```
  顺手在 try 内把后续要用的属性一次取完 —— 后面再碰 `parts.port` 等于把炸弹挪远一格。
- **守阵**: 断言要**两半都锁** —— ①畸形输入**不抛异常**且返回 fail-closed 值(只断言「函数返回 False」不够: 抛异常时测试是 error 不是 fail, 但只写返回断言会漏掉穿透面); ②正常路径(端口一致 / 不一致 / 缺省 80 / https 缺省 443 / 跨站 host)行为逐位不变。本仓落地: `tests/test_web_auth.py::test_auth_host_origin_parsing_helpers` 的 4 条 Origin 非法端口断言。
- **复发**: 0(2026-10-21 首记; 首次发生在 2026-10-16 `*.localhost` 那轮 —— 当时只把 `_host_header_parts` 一侧收了口, `_origin_allowed` 未同步)。

> 交叉引用: 同一判据有多个消费侧的漏守, 另见 [verdict-scope-parity.md](verdict-scope-parity.md)。本条是它的**惰性取值**变体 —— 连"一个消费侧内部"的构造与取值两段都会分家。

**Refs:** memory-bank/issues/26-10-20-2230-bug-webui-origin-port-parse.html
