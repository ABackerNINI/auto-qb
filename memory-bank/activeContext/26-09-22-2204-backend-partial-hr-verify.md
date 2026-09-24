# 部分种子 HR 在线核实
> 摘要: **M1 核心管道 + M2 取数通道均已落地**（离线管道 + 本地端点 + 取数线程 + MV3 扩展）；余 **M3 判定联动 / M4 多站点**。两条配置期 fail-fast 是防「整站保护静默失效」的关键；M2 又挖出「关停时线程正等扩展回传 ⇒ 白等 180s 且持着站点锁」的真缺陷并修掉
> 触发: 部分种子, HR 核实, 浏览器扩展, 三态判定, 带锁访问, 共享站点数据, 转移种子, 多客户端, BTSchool, hr_check, hr_once, 取数通道, 本地端点, 取数线程
> 最后活动: 2026-09-24 22:30

## 状态

### M2 取数通道（2026-09-24 已交付）

| 模块 | 职责 |
|---|---|
| `hr/channel.py` | 协议（`HrTask`/`HrResult`）+ 密钥（落 `<data_dir>/hr.token`）+ origin 白名单 + URL 白名单（SSRF） |
| `hr/queue.py` | **派发式队列** = 端点线程与取数线程的**唯一**交接面；只接受「确实派发过且未作废」的回传，且回传域名须与任务一致 |
| `hr/server.py` | 本地端点（stdlib `ThreadingHTTPServer`，仅听 `127.0.0.1`）：`GET /api/hr/tasks` 下发清单 / `POST /api/hr/result` 收数据 |
| `hr/fetcher.py::ChannelFetcher` | 把「取一个 URL」变成一条任务并阻塞等回传；被叫停与等超时**分开上报** |
| `hr/worker.py` | 取数线程（按 `poll_interval` **自唤醒**，不随主循环 tick）+ 只读视图**原子发布**（单元组赋值，读方零等待）+ 告警节流 |
| `hr/runtime.py` | 门面 `QbManager.hr`：按配置启停、热重载重挂、自检快照（`hr.once` 与状态展示用它） |
| `extensions/hr-fetch-proxy/` | MV3 哑取数器：alarms 轮询 + **后台标签页**取 DOM（不抢焦点、能过挑战页）+ service worker 取 `.torrent`（`credentials: include`）+ 实例端点列表 |

三道边界 + 一道更硬的：**token**（常数时间比对；无 token/不符 ⇒ 401 **且不写任何状态**）、
**origin**（扩展放行、普通网页 403）、**URL 白名单**（任务 URL 只能由配置拼出 ⇒ 端点不会变成带登录态的任意站代理）、
**回传绑定任务**（防伪造注入）。

配置侧：`channel` / `shared_dir` 已转 **L1**（`impact.py` + `HR_CHECK_FIELD_LEVELS`）并在 `apply_new_config` 的
L1 分支接上 `HrRuntime.apply`：监听身份（启用 / 端口 / 扩展 id / token / 共享目录）变了才重挂端点，只改 L0 字段不白重绑端口。
新增两个键：`channel.extension_id`（按 id 钉死 origin）、`channel.request_timeout`（等回传上限，**必须有**）。

❗**关停必须叫停通道**：取数线程在锁内等扩展回传最长 `request_timeout`（默认 180s）。不叫停的话，正常关停会白等到超时，
该站点期间锁死、进程退出被拖住。已内建在 `HrWorker.stop()`（先 `queue.cancel_all` 再 join），
`HrRuntime._build` 用 `queue.resume()` 清残留标记。

### M1 核心管道（2026-09-24 已交付，离线可做，不需要浏览器）

| 模块 | 职责 |
|---|---|
| `bencode` | infohash 只取 **info 的原始字节切片**（定位跨度时只做字节跳跃，不解码 info）；畸形/深嵌套拒收 |
| `parse` | 栈式 `<tr>/<td>` 树（容忍 NexusPHP 的 `<td class="embedded">` 包裹表）+ 数值容错（认不出返回 None，不猜） |
| `adapters/` | 站点隔离；现只有 **NexusPHP `myhr.php` 九列形态**（首站 BTSchool）。`header_found` 是「改版」与「合法空结果」的唯一区分器 |
| `model` / `store` | 站点文件内容（`index`/`downloaded`/`fails`/`verified`/`refresh`/`quota`/`fuse`）；**每站点一个 JSON + 一把 filelock**，持锁期间完成「读→判有效期→必要时抓→写→释放」全程；revision 回退或心跳被覆盖 ⇒ 退化只读 |
| `ratelimit` | 间隔**只向上抖动** +0~25%、小时/天两级配额（按窗口键幂等）、失败退避熔断、`allow_window` 可跨午夜 |
| `resolve` | **三态**（受管束 / 已核实不受管束 / 未核实）+ 新鲜度闸门 + 锚点漂移 + 放行有效期；时间敏感判定**读取时现算** |
| `service` | 刷新管道。`persist` × `allow_fetch` 组合出三种口径：正常 / `--dry-run`（零请求零写入） / `hr.once`（抓但只读） |
| `report` + `cli --hr-once` | 只读走查（不加锁、不写盘、不连 qB），报告含**通道自检段**（端点 / 密钥来源 / 共享目录） |

**两条 fail-fast 是 M1 最值钱的防线**（都在配置期直接报错）：① 站点 `mode != off` 却没配 `hr` 段；
② `hr_page_scopes` 必须含 **A+B+C**（少抓一档会让该档种子被误放行）。

## 未完成

- **M3 判定联动**（1 会话）—— 原料已齐：三态判定与不可变视图已测；**M2 已把消费门面备好**：
  主循环用 `manager.hr.view_snapshot()` 取 `(revision, views)`（零等待、单次属性读取），版本没变就**不做任何 record 更新**，
  需要新数据时 `manager.hr.wake()`（非阻塞，绝不与取数线程同步握手）。要做的：接进 `TorrentRecord` 两个方法 +
  四个消费点（打标 / WebUI 视图 / `hr` 规则条件 / `tor.hr_*` 表达式），把 `mode: all` 升为「站点侧驱动 + 未核实恒受管束」，
  并在主循环提供 `manager._hr_anchors`（取数线程已在调它，现在恒空）。
- **M4 多站点与打磨**（1 会话）：第二/第三个 adapter、索引新鲜度展示、notify 四类事件语文化、用户文档。

## 待实测（计划 §13，不阻塞）

download URL 形态与 passkey / BTSchool 各档语义与分页到底判据 / **后台标签页取数是否被站点在线时长识别或 CF 挑战** /
共享目录上 filelock 是否真互斥。结构类判据已由 fixture 钉死（灰色不可点的「下一页」/ 免罪链接 / 九列表头）。

- [计划](../plans/26-09-22-2204-partial-hr-site-verify-plan.html) · [档案](../tasks/26-09-22-backend-partial-hr-verify.md) ·
  [扩展说明](../../extensions/hr-fetch-proxy/README.md)

## 实测

离线样本（脱敏 fixture 取自真实样张结构）+ 真回环 HTTP 往返在 `tests/test_hr_*.py` 14 个文件里；
全量测试数字只认单点 [testing/baseline.md](../testing/baseline.md)（本切片不复述）。
扩展侧只做语法校验（`node --check`），**真机链路未实测**（需用户装扩展 → M3 的真机 `hr.once` 走查）。
