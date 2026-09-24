# 26-09-25-webui-ext-hr-logging — 浏览器扩展运行日志(分级 + 环形上限 + 选项页④区)

**Status:** Done
**Added:** 2026-09-25
**Updated:** 2026-09-25
**Summary:** 用户要求浏览器扩展(hr-fetch-proxy)加日志: 条数可设(最多 10000)、分级可过滤、明细要详细(时间/收到的命令/请求站点/请求类型/请求结果/后端返回等)。实现: background.js 内联 logger(不新建文件, 遵守"新建文件需确认"边界) —— MV3 SW 随时被回收 ⇒ 唯一事实源 `chrome.storage.local`(键 `logs`), 内存环形缓冲 + 防抖 300ms **整份写回**(读改写在并发 log 间互相覆盖丢条); 四级 debug/info/warn/error, 记录阈值(默认 info)与显示过滤独立; 条数 10–10000 可设(默认 1000); 明细单字段超长截断 400 字符。记录点: 轮询开始/结束、收到的命令(每条任务 kind·id·站点)、拉清单/页面直取/页面渲染/种子下载(HTTP·耗时·字节数)、回传结果与后端响应体快照、扩展侧硬上限拒发、渲染兜底。选项页加④区(设置即时生效 + 分级过滤 + 刷新/清空 + 自动刷新 + esc 转义 + 限渲染 3000 行)。守阵真跑当场抓到 **flush 链自引用死锁**(回调按名字引用已被重赋值的 chain ⇒ 等自己, 首刷即死锁且无报错)—— 修复入坑 `pitfalls/web-ui/extension-bridge.md`; 顺带修选项页轮询周期文案漂移(停在"每 5 分钟", 实际 1 分钟)并加文案↔`POLL_MINUTES` 防漂守阵。全量 **1579 collected: 1576 passed + 1 skipped**(+3 守阵)/ TOTAL 91% 不变。
**Topics:** webui-ext-hr-logging

## 原始请求

> 为浏览器扩展添加日志记录功能, 日志可记录设定的条目数, 最多10000条, 日志需要分级, 可分级显示,
> 日志需要详细: 时间, 收到的命令, 发出请求的站点, 请求的类型, 请求结果, 返回后端结果, 等等

(续作指令: 「修复文案, 然后提交」 —— 修选项页轮询周期过时文案 + 走收尾 DoD 与提交推送。)

## 思考过程与决策

### 形态: 不新建文件

AGENTS.md 请求边界: 新建文件须用户逐项显式确认 ⇒ logger 内联在 background.js(选项页只读 storage, 不需要共享模块);
manifest 零改动(`storage` 权限已有)。

### 落盘口径: 唯一事实源是 storage

- MV3 service worker 随时被回收 ⇒ 内存环形缓冲只是加速: SW 醒来第一次 `log()` 时把存量读进内存当缓冲底,
  之后只增删内存数组, 防抖 300ms **整份写回**。
- ❗整份写回(而非读→append→写)是故意的: `log()` 是 fire-and-forget, 读改写在两个并发 log 的 await 间隙
  会互相覆盖丢条 —— 内存数组是唯一写入口。
- 10000 条 × 单字段截断 400 字符 ≈ 数 MB < storage.local 10MB 配额; 页面 HTML 绝不整份进日志。
- 外部清空采纳: 选项页在后台没应答时会直接把 storage 的 `logs` 置空 ⇒ 后台 onChanged 必须采纳(否则下次
  落盘把"已清空"盖回去); 用 `logSelfWriteAt`(1 秒窗口)区分自己写的与外部改的。

### 分级与过滤是两个独立设置

记录阈值(`logLevel`, 默认 info, 低于直接丢弃不占额度)在后台生效; 显示过滤(选项页下拉)只影响渲染。
条数上限(`logMax`)经 `chrome.storage.onChanged` 实时应用到后台缓存, 收紧时顺手裁剪。

### 真抓到的 bug: promise 串行链自引用死锁

`flushLogs` 原写法 `p = init.then(() => chain.then(doWrite)); chain = p.catch(...)` —— 回调执行时 `chain`
**已被同步重赋值为 p 自己** ⇒ 等自己 = 首刷即死锁, **无报错无日志**(node 事件循环排空 rc=0 静默退出;
浏览器侧表现为日志永远落不了盘)。修复: 回调前先把队尾存**局部变量**再排队。其它守阵没抓到是因为
它们不 await flush; 新守阵 `await sandbox.log(...)` + `await sandbox.flushLogs()` 才暴露。

### 顺手修的文案漂移(用户明确要求)

options.html「启用轮询(每 5 分钟一次)」停在 v2.6 前(POLL_MINUTES 已是 1)⇒ 改为「每 1 分钟向端点拉一次
任务清单, 空轮询不碰站点」, 并加守阵 `test_options_poll_label_matches_background` 把文案与常量钉在一起。

## 实现计划

| # | 文件 | 改动 |
|---|---|---|
| 1 | `extensions/hr-fetch-proxy/background.js` | logger 块(常量/compactDetail/log/initLogBuffer/applyLogSettings/flushLogs/clearLogs/onChanged) + `noteStatus(patch, lvl)` 同步进日志 + 全部事件点接入(轮询/命令/请求/回传/配额/渲染/任务失败) |
| 2 | `extensions/hr-fetch-proxy/options.html` | ④运行日志区(条数/记录级别/显示过滤 + 刷新/清空 + `#logView`)与样式; 修轮询周期文案 |
| 3 | `extensions/hr-fetch-proxy/options.js` | 读/过滤渲染/清空(clear-logs 协议 + storage 兜底)/设置即时生效 + onChanged 自动刷新 + esc 转义 |
| 4 | `tests/test_extension_proxy.py` | 三个 node 桩补 `chrome.storage.onChanged`; 新增 logger 行为(真跑)/选项页接线/文案防漂 3 条守阵 |
| 5 | `extensions/hr-fetch-proxy/README.md` | ④运行日志节(记什么/分级/存哪/清空/限制) + 配置示例补③④ |

## 子任务状态表

| 子任务 | 状态 |
|---|---|
| logger 块 + noteStatus 改造 + 事件点接入 | Done |
| 选项页④区(HTML/JS/样式) + clear-logs 协议 | Done |
| 守阵 3 条(真跑抓到死锁并修复) + 桩更新 | Done |
| 文案修复(轮询周期) + 防漂守阵 | Done |
| 知识库回写(扩展 README / extension-bridge / tmpdir / baseline / overview / 根 README / progress) | Done |
| 全量测试(test.full 1576+1, 2 假红) | Done |
| 提交 / 推送 | Done(用户已显式指令「提交」) |

## 进度日志

- 2026-09-25 05:0x 开工。`my-commit-flow.sync`: 与主线齐平(275817d0), 树脏(本轮改动)。
- 实现 1–5 项; 守阵首跑即红 ⇒ 定位 flush 链自引用死锁(最小 repro 复现) ⇒ 修复转绿(扩展守阵 18/18)。
- ⚠ tmpdir 坑复发 4: 裸跑 `uv run pytest` 撞 `PermissionError … pytest-current`(默认 TMPDIR=H:\Temp)——
  已按协议在 `pitfalls/testing/tmpdir.md` 复发 +1; 改走 `commands run test.*`。
- 全量: `test.full` ⇒ **1579 collected: 1576 passed + 1 skipped**, 2 failed = `test_commands_engine` 两条
  GBK 码页守阵(本 shell 注入 `PYTHONUTF8=1` 的**已知假红**, 基线有载, `env -u` 后转绿)。
  TOTAL 91%(10905/789/3582/327, 无 .py 源码变更四项不变); sidefx 越界 0。
- 知识库回写: 扩展 README④区节; `pitfalls/web-ui/extension-bridge.md`(MV3 落盘口径 + promise 死锁条目 +
  守阵 12→14); `pitfalls/testing/tmpdir.md` 复发 4; baseline + history(+3 条); 档案(本文件) + activeContext
  切片 + progress/implemented-core 条目 + overview/根 README 各补一句; `kb.index` 重建。
- 2026-09-25 05:5x 收到「修复文案, 然后提交」: 文案已修 + 防漂守阵; 收尾 DoD 走完, `ship.commit` + `ship.push` 入库。
