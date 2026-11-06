# R5 路线小结(存量评审 R4 · static 契约·scripts)

owner: clone3-main · freeze: f088329291e6 · 快照: C:\Users\11059\Desktop\Projects\zcode\auto-qb-review4-snap\auto-qb-zcode-clone3
(执行中逐批追加;终态节在 review.lane.done 后定稿)

## 批次勾选表

| 批 | 内容 | findings 过检 | 状态 |
|---|---|---|---|
| R5-1 | shared 启动与状态: app/state/boot/lifecycle/auth/polling/fetch_low/ui_feedback (3581行) | 24 (major 1 / minor 11 / nit 12) | done |

## R5-1 批记录(2 面精评: 正确性+安全 / 测试缺口+文档漂移)

- **major 1 条**:polling.js:85 SSE 断线沿判定+换票重连状态机零行为回归测试(唯一守阵为字符串锚)。
- minor 11 条:模态框 resolve 悬空 / 登出不断 SSE+换票重开竞态 / 5 个匿名监听不撤除+句柄堆叠 / ver 驱动 refresh 绕过后台门控 / stopPoll 跳过 onEnd / _esDisconnectEdge 探针声明不存在 / _errlogReseed 探针声明不存在 / 退避曲线零测试 / 列播种语义零测试 / 错误环形缓冲零行为测试 / boot.js「三套 UI」计数漂移。
- 同根双报 1 组已去重:lifecycle.js 匿名监听器(面1 正确性锚 :265 与 面2 测试缺口锚 :181),保留面1 条目。
- py↔js 契约对账(面1 只读对 routes/state.py、routes/events.py、runtime_views.py delta、runtime_stream.py errlog、infra/clock.py):delta/removed/rid/status/errlog/ticket/flags 字段口径无错位。
- 底册复验:R2 终表零命中本批;Open issues 0149(抽屉开合态)/0411(/api/state 分页)仍 Open 未重报。

### 自弃发现(13 条留痕)

面1(6):boot.js fail() innerHTML 拼接无攻击者输入不构成 XSS / token 存 localStorage 系用户拍板设计 / startPoll chain 抛错静默死亡现网不可达 / _logout 不清 pendingOps 窗口极窄 / 超时+AbortError 翻译三处实现系文档化例外(守阵钉同值) / _esDisconnectEdge(undefined) 首次断线 toast 系设计口径。
面2(7):退避注释 2s→15s 系代表性举例 / 401 不断 SSE 属面1 已报不越面 / delta 合并有 e2e 真页面测试担忧不成立 / 字符串锚守阵属既定范式不构成缺口 / boot 超时值守阵核实属实 / auth.js「60 余个 api()」计数值必然漂移 / 底册两条未重报。

## 执行备注(路线级)

- review.check --root 快照 的 .git 强检查误拒仍在(R2 首报,58849374 只定位根因):本路线用 R3 的 workaround——快照根建空 .git 目录绕过,零代码改动。
- 提交闸门 review.trace 对纯盘点数据提交按累计口径计行(认领提交曾滚入他 clone R4-2 数据),走 Review-Skip「纯盘点数据落盘」豁免。
