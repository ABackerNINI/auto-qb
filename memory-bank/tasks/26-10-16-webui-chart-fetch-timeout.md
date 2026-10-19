# 26-10-16-webui-chart-fetch-timeout — 前端请求级超时 + 流量图 loading 悬挂兜底(issue 26-10-16-0954 认领与修复)

**Status:** Done
**Added:** 2026-10-16
**Updated:** 2026-10-16
**Summary:** 用户指令「认领并修复 memory-bank/issues/26-10-16-0954-bug-webui-chart-fetch-no-timeout.html」。走 issue §06 建议修法 **#1 + #2**(报告点明「同一处改动的两面, 建议一起做」): **#1 请求级超时** —— `shared/auth.js::_request` 对裸 `fetch` 无超时, 连接静默失效时 `await` 永不返回 ⇒ 调用方 `finally` 不复位 `loading` ⇒ 轮询守卫把自己挡死(流量图停在旧帧、无提示、不自愈); 改挂 `AbortController` + `setTimeout`(15s), 悬挂被翻译成一次**可报的失败**(「请求超时(15s)」), `finally` / 错误态路径照常执行。**#2 loading 悬挂兜底** —— `shared/qb_traffic_chart.js` 的轮询 tick 判据从「`loading` 为真即跳过」改为「`loading` 且**置位未超过 30s**(= 请求级超时两倍)才跳过」, 超过即视为悬挂、强制续拉并留一次 `console.warn` 痕迹。**#3(连续失败给用户提示)有意不做**: 既有错误空态(`qbCurError` + warn 图标, 成功落袋才清)已承担该提示面, 新增状态会与 P4 接缝提示的那条状态行争同一块位置。**量化口径零改动**: 两处都是纯前端兜底, 采样 / 存储 / 接口契约逐字未动。**收口**：本会话落 #2 并双向验证; #1 因工作区写入判据误判拦下(见「未做 / 残留」), 改由用户手工应用交接件、agent 只读复核(逐字正确 + 语法 OK + 行为电池), 随后补 #1 守阵与红绿双验。测试数字唯一权威在基线切片(见 **Refs:**)。
**Topics:** webui-polling

**Refs:** memory-bank/issues/26-10-16-0954-bug-webui-chart-fetch-no-timeout.html, memory-bank/testing/baselines/26-10-16-1226-webui-chart-fetch-timeout.md, memory-bank/testing/baselines/26-10-16-1256-webui-chart-fetch-timeout-r2.md, memory-bank/pitfalls/web-ui/inflight-flag-no-timeout.md, memory-bank/pitfalls/ops/agent-write-guard-secret-false-positive.md, memory-bank/issues/26-10-16-1303-bug-webui-raw-fetch-bypass-no-timeout.html
## 原始请求

> 用户(2026-10-16): 「认领并修复 26-10-16-0954-bug-webui-chart-fetch-no-timeout.html」

## 思考过程与决策

- **请求边界判定**: 执行任务(改代码 + 认领 issue)。用户显式「认领并修复」= 指派 + 修复双授权; 收尾档位(立档 + 基线切片)按协议随本轮走。
- **为什么 #1 是主路径(而非可选优化)**: issue §03 的影响面是**全链** —— `api()` 是前端唯一取数口(状态栏轮询 / 抽屉 / 流量图三挂点 / 命令回执全走它)。悬挂时**所有**调用方的 `finally` 都不执行: 流量图 `loading` 卡死(可见症状), 而 `polling.js::refresh` 那条链更彻底 —— 它在 `await` 之后才 `scheduleNext()`, 悬挂即**永久停表**(连守卫都没有)。请求级超时是唯一能同时兜住这两条形状的落点, 故它是主修; #2 只是流量图上「万一 `finally` 也没跑起来」的第二层。
- **超时取值 15s**(issue 建议值, 采纳): 本机 WEBUI 直连(127.0.0.1), 后端路由自带超时与降级返回(`meta.stale` 通道), 正常响应亚秒级 —— 全仓最重的 `/api/state` 全量轮也是秒级。15s 只兜「连接层静默失效」, 不误杀慢查询。**不做 per-call 覆盖参数**: 全仓 60 余个 `api()` 调用点没有任何一个需要更长预算(重活都走 `waitCmd` 的异步命令回执通道: POST 立即返回 `cmd_id`, 再由前端轮询 40s —— 那 40s 是**前端自己的等待上限**, 不依赖单次请求时长), 加一个没人用的旋钮就是新的事实源。
- **AbortError 必须翻译**(不是顺手美化): 原始文案是 `The operation was aborted.` / `signal is aborted without reason`, 用户看不懂、也分不出「超时」与「取消」; 翻译后 `_qbLoad` 的既有错误态直接显示「请求超时(15s)」—— **零新增 UI 就拿到了「有提示」**(这也是 #3 可以不做的依据)。
- **外部 `signal` 兼容**: `_request` 现在恒传自己的 signal, 若调用方自带 signal 会被顶掉 —— 用「外部 signal 链接到本 controller」处理(`{ once: true }` 监听 + 已 aborted 立即转发), 语义上「外部取消」仍然生效, 与超时归因分开(`timedOut` 只标记超时那条)。今天全仓无人传 signal(已 grep), 这层是防止未来加取消时**静默失效**。
- **#2 阈值 30s = 请求级超时(15s)的两倍余量**: 正常在途请求(哪怕正好被请求级超时兜到 15s 那一发)不会触发本兜底 —— 只有「连 abort 都没能让 `finally` 跑起来」才走这里, 它是兜底的兜底。
- **计时起点只在 `_qbLoad` 置位处写、`finally` 不擦**: 擦会把「并发在途」的场景擦错 —— 换目标场景下旧请求的 `finally` 晚于新请求的置位时刻到达(`stale` 分支**故意不复位 loading**, 见既有注释), 擦一次就把新请求的计时抹成 0(兜底从此永不触发)。不擦是安全的: `loading` 为假时守卫根本不读它, 每次置位都重写。
- **#2 的兜底是「强制续拉」而不是「只复位标志」**: issue 原文写「超时则强制释放并记一次前端警告」, 实做把它并进同一拍 —— 释放标志与发起新请求是同一件事的两面(复位后立刻 `_qbLoad`, 新一拍自带新的计时起点), 分成两步会多一个「标志复位但没在拉」的中间态。警告**每段悬挂只出一条**(新 `_qbLoad` 同步重写计时起点, 下一拍照常挡拍)。
- **范围守恒(黄金法则 6)**: 两条**裸 fetch 旁路**(`commands.js` 的导出下载 / `shortcuts.js` 的 `/api/keys` 读写)未一并处置 —— 它们不经 `_request`, 不在本 issue 的定位锚点里; 只在回复里转告, 是否入池由用户拍板。`_qbDrawGaps` / 轮询间隔 / 既有 stale 谓词等相邻逻辑零触碰。

## 实现计划

| 步 | 内容 | 状态 |
|---|---|---|
| S1 | 开工同步(`my-commit-flow.sync`, 已同步 cc4b6bec) + 复验(node 探针重放两条锚点) | Done |
| S2 | 认领: issue `Open → In Progress`(meta + 徽标 + 状态日志 + 复验小节 + `doc-refs` 认领链) + 本档案 | Done |
| S3 | `shared/auth.js`: 请求级超时(`AQB_FETCH_TIMEOUT_S/MS` + `AbortController` + 外部 signal 链接 + AbortError 翻译 + `finally` 清定时器) | Done(用户手工应用交接件, agent 只读复核) |
| S4 | `shared/qb_traffic_chart.js`: `_QB_LOAD_STALL_MS` + `_qbLoadStalled` + 轮询 tick 悬挂兜底 + `_qbLoad` 计时起点 | Done |
| S5 | 守阵: 新用例两件(图表侧静态三层锚 + 8 项行为电池; 请求侧四层静态锚 + 六型行为电池) + 红绿双验 | Done |
| S6 | 全量测试 + 基线切片 | Done(数字见基线切片) |
| S7 | 收尾: issue 置 `Done`(实际修法 / 验证方式 / 测试数字) + 文档回写 + `kb.index` / `kb.check` | Done |

## 子任务状态表

| 子任务 | 状态 | 说明 |
|---|---|---|
| 复验(两条锚点 + 探针) | Done | 探针读数「无 signal / 零定时器 / 400ms 仍 pending」与「卡死后 8 拍零续拉」, 现象仍在 |
| 请求级超时(auth.js) | Done | 用户手工应用后 agent 只读复核(逐字正确 + `node --check` 过 + 行为电池过); 红绿双验经副本注入(真文件写入被判据拦, 副本逐字节同源) |
| 悬挂兜底(qb_traffic_chart.js) | Done | 常量 + 判据方法 + tick 接线 + 置位处计时; 三挂点共用同一段(无分叉) |
| 守阵用例 + 红绿双验 | Done | 两件新用例各三类突变逐类判红; 还原后复绿(一次还原漏行被守阵抓住后补回) |
| 全量测试与基线切片 | Done | 数字见基线切片, 正文不手抄 |
| 文档回写(坑档 + 主题文档) | Done | 两条新坑档(web-ui 在用标志无超时链 / ops 写入判据误判) + 索引重建 |

## 进度日志

- **2026-10-16 11:46 开工 + 路由**: 开工同步 → 已同步 `cc4b6bec`(零 HEAD 改写)。按路由读 `pitfalls/_index.md` → `pitfalls/web-ui/_index.md`(前端改动类)→ 本 issue 全文 → 取数链三处源码(`auth.js::_request` / `qb_traffic_chart.js::_qbLoad` / `_qbPollStart`)。锚点行号与 issue 取证一致(`auth.js:23` 裸 fetch 行), 零漂移。
- **2026-10-16 11:49 复验(防过期原则第 5 条)**: scratch 探针用本 tree 真实源码重放 —— ①请求层: `fetch` 收到的 options **无 signal**、`_request` 排出**零个定时器**、400ms 后请求仍 `pending`; ②消费层: `loading` 置真并连打 8 拍, 续拉**零次**。**结论: 仍复现**。
- **2026-10-16 11:49 认领**: issue `Open → In Progress`(meta + 封面徽标 + 状态日志 + 复验小节), `doc-refs` 指本档; 本档 `**Refs:**` 反向声明(认领链双向闭合)。
- **2026-10-16 11:52–12:05 S4 + S5**: 图表侧兜底与守阵落地; 既有 `test_frontend_qb_traffic_chart_wiring` 的「tick 三判据」断言按被修复语义改钉(原文钉的是本次缺陷成因的合体式书写形态, 现按语义钉「该在的判据都在 + 兜底在」)。
- **2026-10-16 12:05 红绿双验(突变 → 判红 → 还原)**: ①tick 守卫退回合体式 ⇒ 新守阵判红; ②tick 无条件挡拍(修复前行为) ⇒ 判红; ③去掉 `_qbLoad` 计时起点 ⇒ 判红。还原后定向用例复绿; 其中一次还原漏了一行 `console.warn` 被新守阵当场抓住(行为电池的「警告只一条」判据), 补回后复绿。
- **2026-10-16 12:09 S6 全量**: `commands run test.full` 跑完 —— 除「索引未重建 / 档案引用了尚未创建的切片与基线」这 5 条(本轮 DoD 未走完导致, 收尾时消除)与 1 条既有守阵按旧书写形态钉的断言(已按被修复语义改钉)外全绿; 最终数字见基线切片。
- **2026-10-16 12:12 S3 阻塞**: `shared/auth.js` 的两次写入均被 `artifact_secret_detected` 拒(报「形如凭据赋值的字面量(键名 `Token`)」, 报出的行号 55 / 83 与磁盘内容对不上; 逐行核过该文件无任何真实凭据字面量)。按判据要求停手、不绕过; 已备好逐字 OLD/NEW 的交接件供人工应用。
- **2026-10-16 12:47–13:05 S3 落地后复核(用户手工应用)**: 首次核对报告「无改动」(mtime 停在 10-15 / 全仓零命中 / 四个相邻 clone 也零命中); 用户重新保存后逐项复核通过 —— 常量在顶层(`auth.js:13-14`, 在 `window.AQB_AUTH` 之前)、`_request` 内 `AbortController`/定时器/外部 signal 链接/`signal: ctl.signal`/`AbortError` 翻译/`finally` 清定时器齐全、既有 Authorization 行未被误删、`node --check` 通过。
- **2026-10-16 12:50 S5 补 #1 守阵 + 红绿双验**: 新用例 `test_frontend_api_request_timeout`(四层静态锚 + node 六型电池) + 头部测试计划一行; 红绿双验经**副本**注入三类突变(真文件写不进去) —— ①裸 fetch ⇒ 静态判红 + 电池「无输出」(悬挂把探针 await 挂住, 该失败形态已写进守阵的空输出断言); ②翻译判空 ⇒ 静态 + 电池 3 项; ③`finally` 空 ⇒ 静态 + 电池 2 项; 对照组两层全绿, 副本删除后与磁盘逐字节一致。
- **2026-10-16 12:56 S6 全量(收口)**: `commands run test.full` 两采样全绿(数字与耗时区间见新基线切片 `26-10-16-1256-*`); `kb.index` / `kb.check` / `kb.docmap --check` 全绿(仅 2 项既有 cap 债务)。issue 置 `Done`。

- **2026-10-16 13:03 用户指令「入池然后提交」**: 「同类未处置」清点后入池成新 issue —— 实际是 **4 文件 5 处**旁路(`boot.js` 分片装载 / `lifecycle.js` 免鉴权判定 / `commands.js` 导出下载 / `shortcuts.js` 密钥读写×2), 含机制、逐字证据(凭据段出网头不复制)、锚点、根因待查与三条候选修法; 认领链双向(本档 Refs ↔ 新件 `doc-refs`)。随后按指令提交(全量提交: 工作树另含其他会话的 KB 坑档改动, 已由用户知晓并要求一并入库)。

## 未做 / 残留(转告)

- **#1 的落盘经人工应用(环境约束, 非本次计划缺口)**: 工作区写入判据对 `auth.js` 整文件级拦下(误判命中既有行), 交接件 `.openclaw/tmp/auth_js_timeout_patch.txt` 由用户手工应用, agent 只读复核; 已记坑档 `pitfalls/ops/agent-write-guard-secret-false-positive.md`。
- **两条裸 fetch 旁路未处置**(范围守恒): `commands.js` 的导出下载(`/api/torrents/{hash}/export`)与 `shortcuts.js` 的 `/api/keys` 读写绕过 `_request`, 同样没有超时。它们不在本 issue 的定位锚点里, 本轮一行未动; 是否入池成独立 issue 待用户拍板。
- **`polling.js::refresh` 那条链的「无守卫」形状保留原样**: 它的自愈完全依赖请求级超时(本轮的 #1), 没有另加兜底计时 —— 与流量图不同, 它没有 `loading` 标志可卡, 悬挂修好后 `scheduleNext()` 照常续排。
- **别的会话留在本 clone 工作树的未提交改动**(非本轮): `memory-bank/pitfalls/testing/no-uv-fallback.md` 与其重跑生成的 `pitfalls/testing/_index.md` —— 提交前需用户确认归属。
