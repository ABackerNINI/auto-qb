# 26-10-14-1110-hr-channel-portless-registration — HR 取数通道去端口化可行性报告已出, 待拍板

> 摘要: 用户提案「扩展是被动连接, 可否去掉后端端口改随机、后端主动联系扩展注册、甚至扩展不需要固定端口由后端探测」。本轮为只读分析 + 报告轮(未改任何代码)。核心结论: 字面方案不可行(Chrome 扩展无监听套接字 API, 后端无法向扩展主动建链/探测); 但「用户零配置」可经路线 A(发现端口 + 临时数据端口 + token 自动分发, 保留轮询)达成, 「零端口 + 后端主动派发」可经路线 B(native messaging 桥 + 命名管道, 离屏文档持长连接)达成。报告已出: `memory-bank/reports/26-10-14-1110-report-hr-channel-portless-registration.html`(Done, 出厂冻结)。
> 最后活动: 2026-10-14 11:10
> 状态: Done(报告交付; 6 项待拍板, 拍板后另立计划)

## 本轮结论(报告 §01 速览)

- 去掉后端端口配置改随机: **可行**(端口 0 交 OS 分配, 寻址由发现端口或命名管道补上)。
- 后端主动联系扩展注册: **部分可行**(HTTP 路线做不到; native messaging 接通后后端可主动推送)。
- 扩展无固定端口、后端主动探测: **字面不可行**(扩展无监听套接字; 零端口形态只有 native messaging)。
- 附带收益: 同机多实例端口撞车/启动即错的约束随之消失。

## 关键事实(取证 de83fbe8)

- 现状拓扑与用户所述相反: 连接由扩展主动发起(MV3 SW 每 60s 轮询), 后端被动监听; 任务流才是后端派发、扩展取走。用户要消的是「抄端口 + 粘 token」两道手工配置(选项页实例列表)。
- 后端端点 = 标准库 ThreadingHTTPServer 绑 127.0.0.1 固定端口, `allow_reuse_address=False` 独占; 鉴权 = X-Hr-Token(自动生成到 `<data_dir>/hr.token` 0600) + Origin 白名单(chrome-extension://, 可选钉 extension_id); 硬约束 = 轮询周期(60s) < request_timeout(180s)。
- 可复用资产: WebUI SSE 推送先例(/api/events); `scripts/hr_fetch_experiment.py` 零依赖手写 WS 客户端先例; CDP 驱动浏览器路线 2026-09-24 已否决(专用 profile 无登录态), 任何新方案不得退回。
- 扩展 manifest host_permissions 已含 `http://127.0.0.1/*`(任意端口), 发现探测无需改 manifest; minimum_chrome_version 116 覆盖离屏文档 API。

## 待拍板(报告 §10, 6 项)

1. 路线选 A / B / C(推荐 A 先行, B 为完整形态二期)。
2. 发现端口默认值(建议 18788 —— 现产端口转正, 数据端口让位随机)。
3. 路线 A 是否要一次性配对码 HMAC 硬化(默认建议: 不要, 文档化残留风险)。
4. 多实例注册表落点(%LOCALAPPDATA%\auto-qb-hr\ 是否覆盖实际部署)。
5. 路线 B 桥分发形态(.cmd 包装 python -m vs PyInstaller 单文件)。
6. 路线 B 是否保留降级轮询兜底。

## 下一步 / 移交

- 拍板后按 delivery-artifact 立计划(`memory-bank/plans/`, 单文件 HTML), 本报告作事实背景引用; 计划未拍板前不动代码。
- 兼容口径已定: `port` 显式值 = 旧行为(存量零感知), `0`(默认)= 自动发现; 新扩展遇旧后端退手动配置。
- 本轮为纯文档轮: 未改代码、未加测试, 不需动测试基线; 未踩新坑, 无 pitfalls 入池。
