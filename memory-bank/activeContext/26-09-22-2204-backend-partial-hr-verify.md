# 部分种子 HR 在线核实
> 摘要: **M1 核心管道 + M2 取数通道 + M3 判定联动 + M4 多站点与打磨均已落地**；v2.6 修复「种子下载不触发」的根因链
（**扩展轮询 5 分钟 vs 后端 request_timeout 180s 的时序错配** + 复用轮 60s/60s 竞速 + 页面失败跳过回填 +
下载阶段让位异常被计成 tid 失败）；只差**真机走查**（M0 余三项实测 + 扩展 reload 后跑一轮）。
M3 把三态判定接进 `TorrentRecord`（站点侧驱动、四个消费点未改调用点、`mode: all` 升维、锚点提供者、WebUI 三态与两套值）；
M4 补上四类事件语文化、站点级状态单点与 WebUI 出口、多站点隔离守阵与接入指南。
两条配置期 fail-fast 是防「整站保护静默失效」的关键；M2 上线后按用户实报修完告警分级/归属、
`--hr-status` 现状报告、站点文件两层自愈与「取数在自己建的隐藏窗口里做」(不占用户窗口)。
> 触发: 部分种子, HR 核实, 浏览器扩展, 三态判定, 带锁访问, 共享站点数据, 转移种子, 多客户端, BTSchool, hr_check, hr_once, hr-status, 取数通道, 本地端点, 取数线程, 告警级别, 站点文件损坏, 隐藏窗口, 多站点, 站点状态, 四类事件, 登录失效, 轮询周期, request_timeout, 复用轮, 回填
> 最后活动: 2026-09-25 (v2.6 通道时序与饿死残留修复)

## 状态

### 已交付（M1 + M2 + M3 + M4 + 五批实报修复）

- **M1 核心管道 + M2 取数通道 + M2 上线后三批实报修复**: 离线管道(bencode 原始切片 · NexusPHP 解析 ·
  站点分文件+锁 · 频控 · 三态判定) / 本地端点+队列+取数线程+MV3 扩展 / 告警分级归属 · `--hr-status` ·
  站点文件自愈与无界面直取 —— **明细已迁出**, 见[档案](../tasks/26-09-22-backend-partial-hr-verify.md)进度日志
  与计划 v1.9-v2.2 变更行; 两条配置期 fail-fast(`mode != off` 必配 `hr` 段 / scopes 必含 A+B+C)仍在生效。
- **M3 判定联动**（2026-09-25）: 收口在 `hr/resolve.py::judge_record` + `HrJudgement`（身份 / 最终布尔 / 依据 /
  站点侧达标结论与展示值 `HrSiteFacts`）, 门面入口 `HrRuntime.judge()`; 记录侧只加 `hr_link` / `hr_judgement()` /
  `hr_anchor()` —— **四个消费点（打标 / WebUI 视图 / `hr` 规则条件 / `tor.hr_*` 表达式）调用点一行未动**,
  站点侧优先、站点没给再回落本地。判定桥是 `QbManager.hr` 的**稳定引用**（热重载不换对象）, 由 `TorrentStore`
  在记录构建/变更时挂上, **读取时现算** ⇒ 锚点漂移与视图更新不需要记录置脏。**零静默变更两道门**:
  站点配了 `hr_check` 且 `mode != off` + 全局 `hr_check.enabled`（未接入站点行为逐字未变）。
  `manager._hr_anchors()` 按站点给出 `{infohash: HrAnchor}`。WebUI 加三态/依据/来源 + 站点侧值（档位·还需做种·
  剩余达标·分享率·站点下载量）, 详情抽屉两行, 安全放行用中性色条。两处实现期拍板（详见计划 v2.3）:
  站点**还没发布过视图** ⇒ 回落本地（否则 `mode: all` 启动窗口里整站集体打标）; 站点行**缺达标字段 ≠ 未达标**。
- **第四批实报修复（2026-09-25, 入库 `9a3dd28`）**: 用户报「种子似乎没有下载成功」⇒ 三个真缺陷（都不是扩展的问题）——
  ① **下载被页面饿死**: 频控门槛是「相邻两次**请求**间隔」而流水线「先页面后 `.torrent`」⇒ 每窗口唯一名额总被页面吃掉；
  修法是**复用轮只补下载**（`_backfill_on_reuse`: 不碰页面, 名额全给待回填 `.torrent`）。
  ② **生产路径不等间隔**: 计划 §8 本意「连分钟级抓取也在锁内」, 实现只把 `sleeper` 给了走查 ⇒ 一轮只发得出第一个请求
  （`complete=False` ⇒ **永远没有安全放行**）；修法是门面提供**可中断**的锁内等待 + 两道上限（单次 300s / 一轮 900s）。
  ③ **无可用索引键 ⇒ 整站按受管束打标**: `HrSiteView.has_lookup_keys` 为假时 `judge_record` 回 **None(回落本地)**，
  `mode: all` 不受此闸门影响。另按用户指定数值加**扩展侧第二道闸** `site-caps.js`（访问 10/时·50/天, 下种 50/时·200/天,
  按域名分计, 超限**拒发** + `kind=ext-quota`）⇒ 后端 `HrChannelQuota` 落 ACTION_WAITING **让位而不计失败**。
  测试 +15 条, ★红验 4 处；合流后全量 1541 passed + 1 skipped。
- **M4 多站点与打磨（2026-09-25）**: ① **四类事件语文化** `hr/events.py`(文案单点 + 标签前缀 `[HR 登录失效]` /
  `[HR 熔断]` / `[HR 页面改版]` / `[HR 通道静默]`); **登录失效从熔断里摘出来**(`HrLoginExpired`: 不计失败、不推熔断,
  只报一次并给动作 —— 判据同 `HrChannelQuota`: 能不能靠重试解决; 原因仍写 `refresh.reason` 供报告/界面看,
  **但绝不碰** fetched_at / 覆盖证明 / 新鲜度基准); 通道静默告警补**受影响站点**。
  ② **站点级状态单点** `hr/status.py::site_status()`: CLI 与界面同一套数(新增下次刷新 / 回填进度 / `blocking`
  「现在为什么不放行」), `report.py` 改为消费它(CLI 文本逐字未变)。
  ③ **WebUI 出口**: 只读 `GET /api/hr/status` + 设置页「HR 站点状态」章节(**两个入口** × **两套 UI** 成对改,
  与日志页同款不轮询) + **前端字段一致性守阵**(模板引用的字段 ⊆ 后端快照键)。
  ④ **多站点**: `tests/test_hr_multisite.py` 5 条钉死「第二站点只改配置」与隔离(文件/锁/配额/熔断/索引不串味);
  `docs/configuration.md` 补接入指南与四类事件标签表。全量 **1561 passed + 1 skipped**。
  ⑤ 坑已回写 `pitfalls/testing/assertions.md`(守阵锢点扫到空块 ⇒ 恒真; 红验篡改逃出正则 ⇒ 假绿)。
- **第五批审查修复(2026-09-25, 计划 v2.6)**: 用户令审查实施并点名「种子下载不触发」⇒ 根因四层 ——
  ① **通道时序错配(主因)**: 扩展轮询 5 分钟 > 后端等待窗口 180s ⇒ 每条任务约四成概率超时
  (烧配额 + 计失败 ⇒ 3 次页面失败 = 12h 熔断); 修: 扩展 `POLL_MINUTES` 5 → **1**、`DEFAULT_POLL_HINT` 300 → 60,
  计划 §6 补「轮询周期必须小于等待窗口」。
  ② **复用轮 60s/60s 竞速**: 不完备有效期 == poll ⇒ 下一轮永远晚一个 ε ⇒ `_backfill_on_reuse` 从不发生;
  修: 有效期 `max(120s, 2×poll)`(判定不读 expires_at, 拉长不产生放行)。
  ③ **页面失败跳过回填** ⇒ 新 `_backfill_on_page_failure`(待回填来自已持久化索引)。
  ④ **下载阶段让位/人工事件被计成 tid 失败**(三者都是 `HrFetchError` 子类) ⇒ 原样上抛 + `_guarded_backfill`
  折备注; 扩展 fetchBinary 检测登录页 ⇒ 新 `KIND_LOGIN_PAGE` ⇒ `HrLoginExpired`。
  ⑤ 边角: 配额展示按窗口键折算 / Retry-After 封顶 / `--hr-status` 去硬编码后缀 / ext-quota 文案补
  「扩展上限本就低于后端配额」。M0 下载 URL 实测收口: `https://pt.btschool.club/download.php?id=<tid>`。
  测试 +11, ★红验 7 条; 全量 **1570 passed + 1 skipped**(HR 包 93%)。
  ❗**用户侧动作: chrome://extensions 里 reload 扩展**(1 分钟轮询与登录页检测要重载才生效)。

模块分工 / 字段口径 / 配置项 / 扩展行为: [modules/overview.md](../modules/overview.md) ·
[docs/configuration.md](../../docs/configuration.md) · [扩展说明](../../extensions/hr-fetch-proxy/README.md);
逐条踩坑与决策见[档案](../tasks/26-09-22-backend-partial-hr-verify.md)进度日志与 `pitfalls/`。

## 未完成

- **真机走查**（需用户装扩展）: ❗先在 chrome://extensions **reload 扩展**(v2.6 的 1 分钟轮询与登录页检测要重载生效),
  再跑 `--hr-once` + 主程序一轮, 确认取到 `.torrent` 后索引长出 infohash 键、三态在 WebUI 与日志上对得上;
  之前 `fuse.failures=2` 已定位 = 页面请求在「5 分钟轮询 vs 180s 窗口」错配下超时(v2.6 已修)。
- **非 NexusPHP 形态的第三个站点**（需站点样本）: 本仓只龙过 NexusPHP 的 `myhr.php` 九列表形态;
  若某站有更便宜的来源(JSON 接口 / 逐种标记), 按 `adapters/__init__.py` 的注册协议加一个 adapter ——
  **不拿到真实样本不猜着写**。
- ⛔ **待用户定**: `config.yml` 被 git 跟踪且含明文 qB 凭据 —— 入不入池 issue。

## 待实测（计划 §13，不阻塞）

~~download URL 形态~~ ✅ 已实测收口(2026-09-25): `https://pt.btschool.club/download.php?id=<tid>`; 余:
BTSchool 各档语义与分页到底判据 / **隐藏窗口取数是否被站点在线时长识别或 CF 挑战** /
共享目录上 filelock 是否真互斥。结构类判据已由 fixture 钉死（灰色不可点的「下一页」/ 免罪链接 / 九列表头）。

- [计划](../plans/26-09-22-2204-partial-hr-site-verify-plan.html) · [档案](../tasks/26-09-22-backend-partial-hr-verify.md) ·
  [扩展说明](../../extensions/hr-fetch-proxy/README.md)

## 实测

离线样本（脱敏 fixture 取自真实样张结构）+ 真回环 HTTP 往返在 `tests/test_hr_*.py`；
全量测试数字只认单点 [testing/baseline.md](../testing/baseline.md)（本切片不复述）。
扩展侧已不止语法校验: `tests/test_extension_proxy.py` 用假 `chrome` API **真跑** `background.js` 与 `normalize.js`；
**真机链路仍未实测**（需用户装扩展 → M3 的真机 `hr.once` 走查）。
