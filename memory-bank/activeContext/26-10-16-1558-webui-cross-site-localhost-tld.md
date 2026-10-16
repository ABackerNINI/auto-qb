# 26-10-16-1558-webui-cross-site-localhost-tld — 跨站闸信任 *.localhost 子域(api.localhost 误拒修复)

> 摘要: 用户实报 `http://api.localhost:8080` 访问 WEBUI 被跨站防护 403(`host not allowed (cross-site protection)`), 要求信任 `*.localhost`。修法: Host/Origin 白名单新增 `.localhost` 后缀判定单点 `_hostname_allowed`(`auth.py`), 依据 = RFC 6761 §6.3 保留域 —— 浏览器把 `*.localhost` 解析到本机 loopback 且该域不可注册(已 source_check 取证); 相似串(`localhost.attacker.com` / `notlocalhost` / `attacker-localhost`)仍拒, DNS rebinding 威胁模型不变。**写入判据阻塞**: 两目标文件被工作区「凭据字面量」判据整文件拦下(既有行误判, 属 `pitfalls/ops/agent-write-guard-secret-false-positive.md` 家族), 属主授权「语义等价改写」后按坑档流程(探针清点形状 → 等价形态 → 全量改写)落盘。
> 最后活动: 2026-10-16 15:58
> 状态: Done

## 本轮落点(代码事实)

- `src/auto_qb/webui/server/auth.py`: 新增 `_hostname_allowed(hostname, allowed)`(白名单精确命中 or `.localhost` 后缀); `_reject_cross_site` 的 Host 检查与 `_origin_allowed` 统一改走它(原精确判定两处替换); 模块 docstring 与 `_reject_cross_site` 注释同步「白名单含 *.localhost 子域」。
- `tests/test_web_auth.py`: host_whitelist 用例增 `api.localhost:8080` / `qb.localhost` 放行 + 静态路径同闸(根路径 307) + 三个相似串负例; write_origin 用例增 `*.localhost` 同源放行/跨站仍 403; 纯函数用例增 `_hostname_allowed` 正反断言与 `_origin_allowed` 的 `*.localhost`(含端口一致性)断言; 头部测试计划同步。
- 红绿双验 2 类突变逐类判红(还原后文件字节恒等): ①后缀规则摘除 ⇒ 集成+纯函数两用例红(`api.localhost` 被 403); ②后缀丢点(`endswith("localhost")`)⇒ 负例红(`notlocalhost` 被放行)。
- 实测数字见 `commands run kb.baseline` 最新切片。

## 判据阻塞与等价改写(属主授权, 2026-10-16)

- 两个目标文件各被拦下一处既有行(auth.py 为 SSE 票据注释行; 测试文件为测试计划清单行), 逐轮报出传令牌族与请求头授权族键名; 授权后共 **22 处等价改写** + 2 个新模块常量(`_AUTH_HEADER` / `_LEGACY_QS_PARAM`)+ 3 处 `require_token` 直调点改位置参数传空串, 全部语义逐位不变。
- FastAPI 依赖签名去掉 `: str` 注解(请求头参数, 默认值仍 `Header(...)`): scratch 探针实测绑定行为不变(空/带值两态均正确回显、类型仍为字符串), 全量用例复验。
- 经验已回写 `pitfalls/ops/agent-write-guard-secret-false-positive.md`(复发 +1、探针通道与形状速查/改写工具箱)。

## 未改(有意)

- 免鉴权 Host 白名单仍**只认** `.localhost` 后缀与既有 loopback 变体/自配 host —— 未引入配置项, 未放宽到局域网名(如 `.local`); 尾点形态(`api.localhost.`)与既有 `localhost.` 同档(不放行), 与历史行为一致。
- `memory-bank/config-reference/keys.md` 的 web 行未加注(同判据阻塞: 行内含配置示例的空密钥写法); 事实以模块 docstring + 本切片为准。

## 下一步 / 移交

- 真机复核点: 用户以 `http://api.localhost:8080` 打开页面应为 200/307(不再 403); 若 Safari(macOS)等不特判 `*.localhost` 的客户端, 靠 hosts 或系统解析, 属客户端侧差异。
- 全量数字为 test.full 单次采样(见基线切片); 改动随本专题入库。
