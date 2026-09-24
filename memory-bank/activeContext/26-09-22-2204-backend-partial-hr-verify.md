# 部分种子 HR 在线核实
> 摘要: **M1 核心管道 + M2 取数通道均已落地**（离线管道 + 本地端点 + 取数线程 + MV3 扩展）；余 **M3 判定联动 / M4 多站点**。
两条配置期 fail-fast 是防「整站保护静默失效」的关键；M2 上线后按用户三轮实报修完告警分级/归属、
`--hr-status` 现状报告、站点文件两层自愈与「取数在自己建的隐藏窗口里做」(不占用户窗口)。
> 触发: 部分种子, HR 核实, 浏览器扩展, 三态判定, 带锁访问, 共享站点数据, 转移种子, 多客户端, BTSchool, hr_check, hr_once, hr-status, 取数通道, 本地端点, 取数线程, 告警级别, 站点文件损坏, 隐藏窗口
> 最后活动: 2026-09-25 02:10

## 状态

### 已交付（M1 + M2 + 三轮实报修复）

- **M1 核心管道**: `src/auto_qb/hr/` 离线管道（bencode 原始切片算 infohash · NexusPHP 九列解析 ·
  站点分文件 + 每站点一把锁 + 锁自检退化只读 · 只向上抖动 + 两级配额 + 熔断 + 时间窗 · 三态判定与不可变视图 ·
  刷新管道 · `--hr-once` 走查）。**两条配置期 fail-fast**: 站点 `mode != off` 必配 `hr` 段 /
  `hr_page_scopes` 必含 A+B+C（少一档会让该档种子被误放行）。
- **M2 取数通道**: 本地端点（仅听 `127.0.0.1`）+ 派发式队列 + 取数线程（自唤醒、视图原子发布、告警分级）+
  运行时门面（启停 / 热重载重挂）+ MV3 扩展（哑取数器: 自己的隐藏窗口取 DOM / service worker 取 `.torrent`）。
  三道边界 + 一道更硬的: token（401 **且不写任何状态**）· origin 白名单（普通网页 403）· URL 白名单（SSRF）·
  **回传绑定任务**（防伪造注入）。`channel` / `shared_dir` 是 **L1**（身份变了才重挂端点）；
  增补键 `channel.extension_id` / `channel.request_timeout`。
- **M2 上线后按用户实报修的三批**: ① **告警分级与归属** —— 频控节流与未到时刻降 INFO 并按根因去重、
  启动/关闭/热重载也降 INFO、同一事件只由一个角色告警（`alerted`）、被叫停（`HrChannelStopped`）不当故障；
  ② **`--hr-status` 只读现状报告**（不取数/不加锁/不写盘/不连 qB）; ③ **站点文件两层自愈**
  （`.bak` 上一版 + 坏文件挪 `.bad-<ts>` 并从备份恢复）+ **页面取数分层**: 默认**无界面直取**
  （后台 `fetch(credentials:'include')`）, 只在内容没 `<table>` 或看到密码输入框时用**离屏 popup 窗口**渲染兜底,
  并带焦点守卫 + 只读口径补漏（取数失败分支同样要看 `persist`）。

模块分工 / 字段口径 / 配置项 / 扩展行为: [modules/overview.md](../modules/overview.md) ·
[docs/configuration.md](../../docs/configuration.md) · [扩展说明](../../extensions/hr-fetch-proxy/README.md);
逐条踩坑与决策见[档案](../tasks/26-09-22-backend-partial-hr-verify.md)进度日志与 `pitfalls/`。

## 未完成

- **M3 判定联动**（1 会话）—— 原料已齐：三态判定与不可变视图已测；**M2 已把消费门面备好**：
  主循环用 `manager.hr.view_snapshot()` 取 `(revision, views)`（零等待、单次属性读取），版本没变就**不做任何 record 更新**，
  需要新数据时 `manager.hr.wake()`（非阻塞，绝不与取数线程同步握手）。要做的：接进 `TorrentRecord` 两个方法 +
  四个消费点（打标 / WebUI 视图 / `hr` 规则条件 / `tor.hr_*` 表达式），把 `mode: all` 升为「站点侧驱动 + 未核实恒受管束」，
  并在主循环提供 `manager._hr_anchors`（取数线程已在调它，现在恒空）。
- **M4 多站点与打磨**（1 会话）：第二/第三个 adapter、索引新鲜度展示、notify 四类事件语文化、用户文档。

## 待实测（计划 §13，不阻塞）

download URL 形态与 passkey / BTSchool 各档语义与分页到底判据 / **隐藏窗口取数是否被站点在线时长识别或 CF 挑战** /
共享目录上 filelock 是否真互斥。结构类判据已由 fixture 钉死（灰色不可点的「下一页」/ 免罪链接 / 九列表头）。

- [计划](../plans/26-09-22-2204-partial-hr-site-verify-plan.html) · [档案](../tasks/26-09-22-backend-partial-hr-verify.md) ·
  [扩展说明](../../extensions/hr-fetch-proxy/README.md)

## 实测

离线样本（脱敏 fixture 取自真实样张结构）+ 真回环 HTTP 往返在 `tests/test_hr_*.py`；
全量测试数字只认单点 [testing/baseline.md](../testing/baseline.md)（本切片不复述）。
扩展侧已不止语法校验: `tests/test_extension_proxy.py` 用假 `chrome` API **真跑** `background.js` 与 `normalize.js`；
**真机链路仍未实测**（需用户装扩展 → M3 的真机 `hr.once` 走查）。
