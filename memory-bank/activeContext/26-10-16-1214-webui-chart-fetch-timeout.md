# 26-10-16-1214-webui-chart-fetch-timeout — 前端请求级超时 + 流量图 loading 悬挂兜底(issue 26-10-16-0954 认领与修复)

> 摘要: 用户「认领并修复 memory-bank/issues/26-10-16-0954-bug-webui-chart-fetch-no-timeout.html」。走 issue §06 方案 **#1 + #2**(报告点明「同一处改动的两面, 建议一起做」): **#2 已落盘**(`qb_traffic_chart.js` 轮询 tick 的 `loading` 悬挂兜底: 置位超 30s 视为悬挂、强制续拉 + 一次 `console.warn`); **#1 请求级超时的落盘经历两次核验**：先被工作区「凭据字面量」判据**整文件级**拦下(误判命中既有行 —— 报出的行号 55 / 83 与磁盘内容还对不上, 两次写入均被拒), 按判据口径停手并出逐字交接件; 用户手工应用后 agent 只读复核(常量在 `auth.js:13-14` 顶层、`_request` 内 `AbortController`/15s 定时器/外部 signal 链接/`signal: ctl.signal`/`AbortError` 翻译/`finally` 清定时器齐全、既有 Authorization 行未被误删、`node --check` 过), 随后补 #1 守阵(四层静态锚 + 六型行为电池)与红绿双验(真文件写不进去 ⇒ 对副本注入三类突变, 逐类判红)。复验(防过期原则第 5 条)先于改动: 两条锚点用 node 探针在未修的树上重放, 读数与报告逐字吻合(请求无 signal / 零定时器 / 400ms 后仍 pending; `loading` 卡死后 8 拍零续拉) ⇒ **仍复现**。红绿双验三类突变全判红(合体式早归回潮 / tick 无条件挡拍 / 去掉计时起点), 其中一次还原漏行被新守阵当场抓住(补回后复绿)。全量测试数字见基线切片。

> 最后活动: 2026-10-16 12:56
> 状态: Done(#2 本会话落盘 + #1 用户手工应用后只读复核, 两件守阵 + 全量收口)
> 档案: memory-bank/tasks/26-10-16-webui-chart-fetch-timeout.md

**Refs:** memory-bank/tasks/26-10-16-webui-chart-fetch-timeout.md

## 本轮落点(代码事实)

- `src/auto_qb/webui/static/shared/qb_traffic_chart.js`: 新增模块级常量 `_QB_LOAD_STALL_MS = 30000`(请求级超时 15s 的两倍余量) + 方法 `_qbLoadStalled(scope)`; `_qbLoad` 置位 `loading` 处写入计时起点 `this._qbLoadAt[scope] = Date.now()`(**`finally` 不擦** —— 换目标场景下旧请求的 `finally` 晚于新请求置位到达且 stale 分支故意不复位 loading, 擦一次就把新请求的起点抹成 0); 轮询 tick 的三判据拆开: `!def.active(this) || document.hidden` 照旧早退, `this[def.loading]` 单独一段经 `_qbLoadStalled` 判悬挂 —— 未悬挂才挡拍, 悬挂则 `console.warn` 一条并强制续拉(新一拍同步重写起点, 故下一拍照常挡拍、警告每段悬挂只一条)。
- `tests/test_webui_static_dom_panel.py`: 新增 `test_frontend_qb_traffic_load_stall_fallback`(三层静态锚 + node 行为电池 8 项: 未悬挂挡拍 / 悬挂放行且警告一条 / 新起点生效 / 图不活跃跳过 / 页面隐藏跳过 / 判据边界 29s·31s·无起点)与头部测试计划同步; 既有 `test_frontend_qb_traffic_chart_wiring` 里钉「tick 三判据」的那条断言按**被修复语义**改钉(原文钉合体式书写形态 `document.hidden || this[def.loading]` —— 该形态正是本次缺陷成因; 现按语义钉「该在的判据都在 + 兜底在」, 细分行为移交给新守阵)。
- 复验/验收探针(scratch, 未入库): `.openclaw/tmp/probe_webui_fetch_timeout.js` —— 用本 tree 真实源码跑两条锚点, 同一探针在修复前后各跑一次(②的读数 0 → 8)。

## 阻塞事项(已解决, 存档留疼)

- **`shared/auth.js` 的写入曾被工作区判据拦下**(`artifact_secret_detected` 报「形如凭据赋值的字面量(键名 `Token`)」, 整文件扫描命中既有行; 该文件里没有任何真实凭据)。已由用户手工应用交接件解除; 环境事实入坑档 `pitfalls/ops/agent-write-guard-secret-false-positive.md`。
- **首轮核对的教训**: 用户说「已应用」时磁盘上其实没有改动(mtime 停在 10-15、全仓与四个相邻 clone 均零命中) —— 核对必须看**磁盘事实**(mtime + 命中数 + 语法/行为), 不能只听汇报; 同时也别自作主张到别的 clone 去写。
- **别的会话留在本 clone 工作树的未提交改动**(非本项目改动, 未触碰): `memory-bank/pitfalls/testing/no-uv-fallback.md`(mtime 11:41:29, 内容为「uv 不在 PATH ⇒ 把 `~/.local/bin` 前置进 PATH」的新首选处置, 实测记录里提到 ship.commit 329.5s 成功推送 —— 非本轮经历) 与随之重跑的 `memory-bank/pitfalls/testing/_index.md`。提交前需用户确认这两处的归属。

## 下一步 / 移交

- **本专题已收口**: issue 置 `Done`; 数字唯一权威 = 基线切片 `26-10-16-1256-webui-chart-fetch-timeout-r2.md`(收口态)与 `26-10-16-1226-*`(半落态快照, 保留不改 —— 切片出厂即冻结)。
- 两条**裸 fetch 旁路**未处置(范围守恒): `commands.js` 的导出下载与 `shortcuts.js` 的 `/api/keys` 读写绕过 `_request`, 同样没有超时 —— 是否入池成独立 issue 待用户拍板。
- 立档阈值: 3 个源文件(2 前端 + 1 测试)⇒ 命中阈值(≥3), 已建 `tasks/26-10-16-webui-chart-fetch-timeout.md`; 认领链双向闭合(档案 Refs ↔ issue doc-refs)。
- 基线债务(转告, 本轮不修): `activeContext/` 切片数超阈值 + `26-10-15-0728-qb-traffic-restart-spike-gap.md` 超 cap —— 需另开会话清理。
