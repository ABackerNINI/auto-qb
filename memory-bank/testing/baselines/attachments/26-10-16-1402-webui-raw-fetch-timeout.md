# 3452 passed + 4 skipped —— 前端旁路裸 fetch 收口(issue 26-10-16-1303 收口)

> 摘要: 5 处**有意或历史地**绕开 `_request` 的裸 `fetch`(启动分片装载 / 本机免鉴权判定 / 导出下载 / 快捷键密钥读写 x2)收敛到新低层单点 `shared/fetch_low.js::aqbFetch`(`AbortController` + 15s + `AbortError` 翻译, 返回**原始 Response** 不解析); `boot.js` 在清单脚本之前执行、用不了单点, 自带等价内联超时(10s → 既有 `fail()` 可读占位, 不再白屏)。两处超时常量与 `auth.js::_request` 同值(同一条口径的两处实现, 守阵钉相等)。守阵 1 条(四层静态锚 + 两份 node 行为电池) + 红绿双验 5 类突变逐类判红。**环境事实**: `lifecycle.js` 的写入被工作区「凭据字面量」判据**整文件**拦下(误判既有行) —— 属主授权做**形态等价改写**(属性名走 `AQB_TOKEN_FIELD` 常量 + 空值占位走 `AQB_BLANK` 空串, 语义不变), 该文件随之恢复可写; 判据形状经 scratch 探针问清(声明形态豁免; 凭据族键名 + 赋值/冒号一律命中, 只报第一个命中行)。
> 基线时间: 2026-10-16 14:02
> 档案: memory-bank/tasks/26-10-16-webui-raw-fetch-timeout.md

- test.full: 3452 passed + 4 skipped / TOTAL 17362 语句 214 未覆盖 5912 分支 166 partial / 98%(闸门过)。耗时 **192.0s / 206.9s**(本片两次采样, 区间 192–207s; 口径见 baseline.md)。
- 本轮新增守阵 1 条(`test_frontend_raw_fetch_timeout_single_point`): 五层静态锚 —— ①单点常量与 `_request` 同值 + 毫秒值由秒值派生; ②**裸 fetch 零回潮**(全 `shared/` 除 vendor 外, 出现调用点 `fetch(` 的文件只允许 `fetch_low.js` / `auth.js` / `boot.js`; 扫源码调用点前先抹注释与字符串, 免得说明文字假红); ③`boot.js` 内联件齐(常量 10s / `new AbortController()` / `signal: ctl.signal` / `clearTimeout(timer)` / AbortError 翻译); ④四个旁路调用点全部改调单点; ⑤`lifecycle.js` 采纳行的等价格式与「旧密钥优先、取不到空串占位」语义。行为面两份 node 电池: 单点七型(信号透传 / 15s 定时器 / 悬挂→「请求超时(15s)」+ `timeout` 标记 / 原始 Response 透传不解析 / 非 abort 错误原样上抛 / 外部取消不冒充超时 / method+headers 透传 / 定时器清理)与 boot 悬挂四项(信号在 / 10s 定时器在 / 悬挂→可读失败文案 / 定时器清掉)。
- 红绿双验(5 类突变, 逐类判红; 真文件注入 → 判红 → 还原 → SHA256 比对; boot 探针 `.openclaw/tmp/probe_1303_boot_hang.js` 未入库): ①单点去掉 `signal` ⇒ ①层静态红; ②`boot.js` 去掉 `signal` ⇒ boot 电池 4/6 项红(悬挂无兜底、`#app` 恒空白); ③`commands.js` 旁路回潮(`aqbFetch` → `fetch`)⇒ ②层红(`{'commands.js': [809], 'lifecycle.js': [201]}`); ④单点超时值 15 → 20 ⇒ ①层红(与 `_request` 不等); ⑤`lifecycle.js` 旁路回潮 ⇒ ②层红(`{'lifecycle.js': [213]}`)。每次还原后五个前端文件哈希与注入前逐字一致。
- ⚠ 判据层面(环境事实): 工作区写入判据对 `lifecycle.js` **整文件**拒写(命中既有行「把含 Token 的字段复位」, 与该文件本轮要改的那处无关; 把 `oldText` 缩到单行、不含命中行也照拒)。scratch 探针(`.openclaw/tmp/probe_guard_*.js`, 未入库)问清形状: 声明形态(`const x = localStorage.getItem("autoqb_token")`)与计算属性名(`this[常量] = …`)通过; 「凭据族键名 + 赋值/冒号」命中(对象字面量 `token:` 与中性对象成员赋值 `x.token =` 均命中, 且只报第一个命中行)。属主授权后按等价改写落地, 该文件恢复可写 —— 已回写 `pitfalls/ops/agent-write-guard-secret-false-positive.md`。
- 仍未处置(范围守恒): 后端脚本与 e2e 里的裸 `fetch` 未清点; `shortcuts.js` 的 `kbKeysLoading` 未加第二层计时兜底(与流量图 `_qbLoadStalled` 不同: 那里兜的是「连 abort 都没能让 finally 跑起来」); `_request` 与单点的两处常量未合并(`auth.js` 本轮不可写)。
- Linux 侧未跑 —— 改动为前端静态件与其守阵, 无平台分支; 本条 Windows 侧数字为事实源。

## 本改动面

- `src/auto_qb/webui/static/shared/fetch_low.js`(新): 低层单点 —— 顶层 `AQB_FETCH_LOW_TIMEOUT_S/MS` + `aqbFetch(path, opts)`(原始 Response 透传; 不挂 `window.*`, 非 mixin 片段)。
- `src/auto_qb/webui/static/shared/boot.js`: `BOOT_PART_TIMEOUT_MS = 10000` + `partErrText(err)` + 分片 fetch 带 `signal`/`finally` 清定时器 → 悬挂 = 可读占位(与分片 404 同一路径)。
- `src/auto_qb/webui/static/shared/commands.js` / `shortcuts.js`: 导出下载与密钥读写改调单点(注释同步说明悬挂症状)。
- `src/auto_qb/webui/static/shared/lifecycle.js`: 免鉴权判定改调单点 + 属主授权的等价形态(`AQB_TOKEN_FIELD` / `AQB_BLANK`, 见上)。
- 三份 `src/auto_qb/webui/static/{atlas,prism,console}/index.html`: `tpl-manifest.scripts` 第 3 项登记 `/shared/fetch_low.js`。
- `tests/test_webui_static_dom_panel.py`: 新守阵 + `_js_fetch_call_lines` + 两份 node 探针 + 头部测试计划一行。
- `memory-bank/`: issue `26-10-16-1303` 置 `Done`; 档案收口(`tasks/26-10-16-webui-raw-fetch-timeout.md`); 坑档两条(web-ui 族的处置/守阵补旁路收口; ops 的写入判据复发 +1、影响面与处置更新); `modules/webui-static-contract.md` 新增「请求级超时单点」条 + 拆分详情件 JS 层清单。

**Refs:** memory-bank/tasks/26-10-16-webui-raw-fetch-timeout.md
