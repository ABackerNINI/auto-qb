# 26-09-22-backend-partial-hr-verify — 部分种子 HR 的在线核实

**Status:** Open
**Added:** 2026-09-22
**Updated:** 2026-09-25
**Summary:** 部分种子 HR 站点在线核实。**M1 核心管道 + M2 取数通道 + M3 判定联动 + M4 多站点与打磨均已落地**
(2026-09-24/25): M1 = 新包 `src/auto_qb/hr/` 离线管道 + 配置全链路 + `--hr-once`; M2 = 本地端点
(`/api/hr/tasks` + `/api/hr/result`, token + origin + URL 白名单) + 取数线程 (`hr/worker.py`) + 只读视图发布 +
MV3 扩展 (`extensions/hr-fetch-proxy/`) + `channel`/`shared_dir` 转 **L1** 并接上热重载重挂;
M3 = 三态接进 `TorrentRecord` 与四个消费点; M4 = 四类事件语文化 + 站点级状态单点与 WebUI 出口 +
多站点隔离守阵与接入指南。六批实报修复后 `--hr-status` 明细改版(档位人话/上传·下载·分享率·还需做种/
CJK 格宽对齐/剩余达标不显示)且 `hr_downloaded[].ts` 改记逐文件取回时刻。
**v2.9 超龄豁免已落地 (2026-09-25)**: 新站点级键 `completed_age_limit`(0=关闭) —— 完成时间超线的种子
判定侧直接豁免(第四态 `EXEMPT`, 压过清单命中), 取数侧超龄行不入索引/不回填 + 翻页早停(倒序证据成立才停)。
**v3.0 达标判定来源优先级已落地 (2026-09-25 17:37)**: 在线考察中 > 在线已达标 >
在线未达标 > 本地 —— 档位即站点的达标结论(A 恒未达标/B 已达标/C 未达标, 命中即停), 页面数值字段降为展示,
本地仅兜底; `satisfied_verdict` 删「A/D 档看剩余达标时间归零、缺字段回落本地」路径, `judge_record`
双命中按档位序取; +2 守阵红验 3 条全红, 全量 1601 passed + 1 skipped。
**v3.3 选项页终态已落地 (2026-09-26 01:30)**: 风格选型定 A(瑞士网格, 三套样张见 plans/26-09-26-0031)
后实施 —— 后台 events 结构化事件环 + 选项页两表(站点现状 / 取数明细) + 日志收起仅排障;
测试 +1(共 1624 passed + 1 skipped)。
**v3.1+v3.2 扩展配置简化已落地 (2026-09-25/26)**: 端点新增只读 `GET /api/hr/sites`(runtime `sites_fn` 现读配置,
热重载加站点即生效); 扩展选项页**整页三模板**(极简 = 粘 token + 一键授权 / 标准 = + 多实例管理 + 手动兜底 +
硬上限 + 日志 / 完整 = + JSON 直接编辑, 选择持久化 `uiTemplate`), 站点权限改后端拉清单勾选 + 一键申请
(手动填域名降级兜底); 测试 +7, 全量 1617 passed + 1 skipped。
**只差真机走查**(M0 四项实测 + 装扩展后跑一轮真实取数 + v3.1 新配置面走查) —— 计划见 memory-bank/plans/26-09-22-2204-partial-hr-site-verify-plan.html (§13 决策记录与 M0 实测清单)。
**Topics:** backend-partial-hr-verify
**Refs:** memory-bank/plans/26-09-22-2204-partial-hr-site-verify-plan.html, memory-bank/plans/26-09-25-1823-plan-webui-hr-safety-display.html, memory-bank/tasks/26-09-25-webui-hr-safety-display.md, memory-bank/plans/26-09-26-0031-plan-hr-ext-options-style.html

## 原始请求

> 当前部分站点实行部分种子HR策略, 即一个种子无法确定其是否为HR种子, 需要上对应的PT站点查询, 通常各站点都会有HR种子统计页, 可以将种子下载下来对比, 注意种子下载速度不能太快, 次数也需限制, 可配置, 访问站点尽量在后台进行, 且复用当前浏览器的cookie, 分析可行性并列一个计划

## 思考过程与决策

- **现状模型**: `trackers.<site>.hr` 是站点级静态配置, 配了即全站按 HR 管束; 判定收口在 `TorrentRecord.check_hr_condition` / `check_hr_satisfied`, 四个消费点 (打标 mixins/tags.py `_add_hr_tag_or_category` · WEB 视图 mixins/web_view.py `_hr_view_fields` · 规则条件 `hr` rules/conditions.py · 表达式 `tor.hr_*` rules/expr/env.py) 全部经它 —— 收口单一, 改造面最小, 这是方案的红利。
- **可行性总评**: 可行。抓取→下载→算 infohash→对账→建索引每步都落在既有架构 (全局任务 / state_file / httpx 已是依赖); cookie 是最大不确定项; 账号安全 (频度) 是最大运营风险, 恰是需求原始诉求。
- **cookie 技术墙 (已核实外部事实)**: ① Chrome/Edge v127 起 Windows 上 cookie App-Bound Encryption, DPAPI 直解失效 (SpecterOps 2025-08 / ElcomSoft 2026-01 / THN 2024-08), 绕过属窃密技术不做; ② Chrome 136 起 `--remote-debugging-port` 在默认 user-data-dir 被忽略 (chromedriver v136 报错可证), CDP 附着日常浏览器已死。⇒ 分层方案: A 手工导入 (M1) → B 专用 profile + CDP (M4); C 扩展备选不排期; D 直读否决 (Firefox cookies.sqlite 明文待 M0 验证, 可作 B 平替)。
- **infohash 关键细节**: 必须 sha1/sha256 over info dict 的原始字节切片, 不能 decode→re-encode (键序/整数表示漂移会算错 hash); bencode 倾向自写 ~60 行解析器 (记录偏移), 零新依赖, M0 拍板。
- **线程模型**: 主循环单写线程约束下, 站点请求 (1s~20s) 不能内联硬等 (2s tick 会卡) ⇒ 取数线程只做 HTTP+解析, 主循环按频控发许可令牌、收结果写 state —— 与 Web 线程 post_command/consume_commands 同款先例; fetcher 永不触碰 store/队列/state。
- **判定语义**: `hr_check.mode = all(现状)/partial(在线核实)/off`; partial 下索引未命中按 `unknown_policy` (默认 hr 保守, 首刷前整站按 HR = 等同现状, 无回退风险); 索引是反应式的 (页面列"已下载且受 HR 约束"的种子), 滞后段由 unknown_policy 兜底。
- **v1.1 增补 (2026-09-22 用户确认后)**: 页面行八字段 (HR 编号/名称/上传量/下载量/分享率/还需做种时间/完成时间/剩余达标时间) 全部入模; tid 站点内唯一、跨站不混用 ⇒ 索引改 (站点, tid) 主键, infohash 下载后回填, 反查键 (站点, infohash) 在内存重建; 同一内容辅种多站 HR 身份独立。防重复下载三层: hr_downloaded 永久层 (条目消失/翻页遗漏/超期都不重下) + 已有 infohash 只更新字段 + 失败重试上限冷却 (新键 `max_download_retries`); `index_retention` 只淘汰页面快照条目。进度字段定位「展示/交叉核对」, 判定仍以 qB 本地实时值为准 (重加清零场景两套值互补)。

## 实现计划

单点在 [计划文档](../plans/26-09-22-2204-partial-hr-site-verify-plan.html) (§11 分阶段): M0 调研拍板 → M1 核心管道 (dry-run, bencode/infohash + adapter + 对账建索引) → M2 频控与后台化 (取数线程+令牌 / 配额 / 熔断 / notify) → M3 判定联动 (TorrentRecord 收口 + 四消费点回归 + unknown_policy) → M4 cookie 自动化 (专用 profile + CDP; Firefox 路线视 M0 验证)。

## 子任务状态表

| 子任务 | 状态 | 说明 |
|---|---|---|
| 计划审核与 v1.2→v1.7 修订 | Done | 2026-09-24: v1.2 = 按审核 + 用户否决手工 cookie 重写 §6/§8; v1.3 = 扩展形态澄清 + 「未核实」边界收口 (三态); v1.4 = 站点侧权威 + 放行有效期; v1.5 = 站点分文件+带锁访问+有效期复用、线程三分职责、mode: all 纳入、hr_channel 并入 hr_check; v1.6 = 锁粒度改为**每站点一把锁** + 取数节奏与 tick 解耦; v1.7 = 5 项决策拍板后定稿 (§13 改决策记录 + M0 实测清单)、**channel 推荐都启用** (扩展侧加实例端点列表)、**shared_dir 多实例部署引导** |
| 独立实验程序 `scripts/hr_fetch_experiment.py` | Done | bencode/infohash (原始字节切片) + selftest 11 项 + myhr 解析样张 + 限速下载 + CDP 自动取 cookie (机器链路全通, 仅剩人工登录一步) |
| 文档漂移收尾 | Done | 2026-09-24 20:15 (计划 v1.8, 纯文档无设计变更): 删 §6 遗留 cookie 分层表 (与「扩展主选」矛盾) / 修 §1 旧路径 · §3 旧落点 · §4 旧判定口径 · §5 bencode 待办 · §11 M0 依赖与抖动口径 / 删 §9 consumer 残留行 + 补 mode 三态语义与 `mode != off ⇒ hr 段必填` / 目录与 CSS 注释更名 |
| 前置决策拍板 | Done | 2026-09-24 用户拍板 5 项: 接受装扩展 / 首站 **BTSchool** (页面数据实施时提供) / 频度按推荐 / `unknown_policy=hr` + `verified_ttl=refresh_interval` / `shared_dir` 默认数据目录; 另定 **channel 推荐都启用**。计划 §13 由「开放问题」改为「决策记录 + M0 实测清单」 |
| M0 实测收口 (download URL 形态 / BTSchool scope 与分页判据 / 后台标签页观感 / 共享目录 filelock 互斥) | Pending | 4 项实测 (**不阻塞 M1**, 可与 M1/M2 并行); 部分已由本轮测试**钉死结构**(灰色「下一页」判到底 / 免罪链接 / 九列表头), 仍需真机确认 `?page=N` 参数名与 passkey |
| M1 核心管道 (离线可做) | **Done** | 2026-09-24: `src/auto_qb/hr/` 10 个模块 (bencode/parse/adapters/model/store/ratelimit/resolve/service/fetcher/report) + 配置全链路 (校验/schema/impact/loader/Hub 文案) + `--hr-once` 只读走查; 8 个测试文件 + 共享夹具与脱敏 fixture, 全量 **1374 passed + 1 skipped** |
| M2 取数通道 (扩展 + 本地端点 + 取数线程) | **Done** | 2026-09-24: `hr/channel.py`(协议 + 密钥 + origin/URL 白名单) · `hr/queue.py`(派发式队列) · `hr/server.py`(stdlib 端点, 仅听回环) · `ChannelFetcher` · `hr/worker.py`(取数线程 + 视图原子发布 + 告警节流) · `hr/runtime.py`(`QbManager.hr` 门面) · 扩展 `extensions/hr-fetch-proxy/`; `channel`/`shared_dir` 已改 **L1** 并在 L1 分支接上 `HrRuntime.apply`。**本轮挖出并修掉一个真缺陷**: 线程正等扩展回传时关停会白等到 `request_timeout` 且持着站点锁 ⇒ 改为先叫停队列再 join |
| M3 判定联动 | **Done** | 2026-09-25: 判定收口 `hr/resolve.py::judge_record`(+ `HrJudgement` / `HrSiteFacts`)与门面入口 `HrRuntime.judge()`; 记录侧只加 `hr_link` / `hr_judgement()` / `hr_anchor()`, **四个消费点调用点一行未动**(改的是它们共同调的 `check_hr_condition` / `check_hr_satisfied`), 站点侧优先、缺字段回落本地; 判定桥由 `TorrentStore` 挂上(门面稳定引用, 读取时现算 ⇒ 不置脏/不重写全库); `manager._hr_anchors()` 按站点给出 `{infohash: HrAnchor}`; `mode: all` 升为站点侧驱动(未核实恒受管束, policy 绕不过); WebUI 加三态/依据/来源与站点侧值字段 + 详情抽屉两行。全量 **1519 passed + 1 skipped** |
| M3 真机 `hr.once` 走查 | Pending | 需用户装扩展后跑 `python src/auto-qb.py config.yml --hr-once` 与主程序, 确认: 端点拉得到任务 / 页面直取拿到表 / 三态在 WebUI 与日志上对得上。与 M0 四项实测同批做 |
| 实报修复: 下载被饿死 + 扩展第二道闸 | **Done** | 2026-09-25: 用户贴 `--hr-status` + 站点文件报「种子似乎没有下载成功」⇒ 三个真缺陷: ①**下载被页面饿死**(频控门槛是「相邻两次请求」而页面永远排前面; 复用轮只补下载) ②**生产路径不等间隔**(计划 §8 本意是在锁内等满; 一次刷新只能发第一个请求 ⇒ 覆盖证明永不成立) ③**无可用索引键 ⇒ 整站按受管束打标**(无键时回落本地); ④ 扩展侧硬上限 `site-caps.js`(访问 10/时·50/天, 下种 50/时·200/天, 超限拒发 + `kind=ext-quota` ⇒ 后端让位不计失败)。合流后全量 **1541 passed + 1 skipped**(本分支合流前 1534) |
| M4 多站点与打磨 | **Done** | 2026-09-25: 四块一起交付 —— ①**四类事件语文化** `hr/events.py`(文案单点 + 标签前缀; **登录失效从熔断里摘出来**: 不计失败/不推熔断/只报一次并给动作, 原因仍写 `refresh.reason` 但**不碰** fetched_at 与新鲜度基准) + 通道静默告警补**受影响站点** ②**站点级状态单一点** `hr/status.py::site_status()`(CLI 与界面同一套数, 新增下次刷新/回填进度/「现在为什么不放行」) ③**WebUI 出口**: `GET /api/hr/status` + 设置页「HR 站点状态」章节(经典与 Hub 两入口 × 两套 UI) + **前端字段一致性守阵** ④**多站点**: `tests/test_hr_multisite.py` 5 条钉死「第二站点只改配置」与隔离(配额/熔断/锁/索引不串味) + `docs/configuration.md` 接入指南。全量 **1561 passed + 1 skipped** |
| v2.9 超龄豁免 (判定侧豁免 + 翻页早停) | **Done** | 2026-09-25: 用户指令「完成时间超过一年(可配)的种子没有必要验证 HR, 甚至也没有必要往下翻页」⇒ 新站点级键 `completed_age_limit`(0=关闭, 1D~3650D): 判定收口 `judge_record` 对本地完成时刻超线的种子给第四态 `EXEMPT`(排在「无可查键回落本地」之前, 压过清单命中与 unknown_policy, mode=all 也认); 取数侧超龄行不入索引/不回填 + 整页超龄且页内跨页倒序成立才早停(覆盖证明照常成立)。判定 7 + 取数 8 + 门面 1 + 配置 1 = 17 条测试, 红验 10 条全红; 全量 **1593 passed + 1 skipped**。计划 v2.9 (§4/§7/§9/§13/§14) |
| v3.0 达标判定来源优先级 (档位即结论) | **Done** | 2026-09-25 17:37: 用户指令「在线信息.考察中 > 在线信息.已达标 > 在线信息.未达标 > 本地信息」⇒ 计划 v3.0 (17:10) 收口后当轮落地 —— ① `hr/model.py::satisfied_verdict` 三档全档位即结论 (A/C ⇒ False · B ⇒ True · D/未知档位才 None), 删「A/D 档看 remain_seconds==0 ⇒ 已达标」推导 (v2.8 已实证该字段是考核窗口倒计时, 方向相反) 与缺字段回落本地; ② `hr/resolve.py::judge_record` 双命中改按 (判定档位, 达标档位序) 取更保守者 (新增 `_lane_rank`, 删「首命中即 break」); ③ `check_hr_satisfied` 分支逻辑不变 (site_satisfied 非 None 即采纳), 仅 docstring 同步。测试 +2 (`test_lane_verdict_ignores_remain_and_local` / `test_judge_record_double_hit_prefers_lane_order`) + 改写 1, 红验 3 条全红; 全量 **1601 passed + 1 skipped**。计划 v3.0 (§9/§12/§13/§14) |

## 进度日志

- **2026-09-26 01:30 (v3.3 落地: 选项页终态实施 —— 风格 A 瑞士网格 + 两表 + 日志收起)** — 用户令「实施」
  (前情: 三套风格选型定 A, 见上一条选型结论)。用户另令「扩展需要 HR 在线核实详情表, 把冗长 log 总结成表格,
  log 收起仅排障用; 先计划两张表展示哪些信息, 更新模板 A」—— 两表规划已并入选型文档后一并实施。
  ① **后台事件环**(`background.js`): 新增 `events` 结构化环形缓冲(上限 50, 防抖整份写回, 与日志同源双写
  但各记各的 —— 日志给人排障, 事件环给表格渲染, 解析日志文案做表太脆), 字段
  `{t, host, kind(page/torrent), ok, status, ms, bytes, tag(ok/quota/login/error), note}`;
  五个事件点: 页面直取成功 / 离屏渲染成功(标「离屏渲染」—— 同一任务第二次真实访问, 便于用量对账) /
  种子下载成功 / runTask 失败(含 quota 与 login-page 分类); `pollAll` 收尾与日志一并落盘。
  ② **选项页重写**(`options.html`/`options.js`, 按样张 A): 自上而下 ①连接端点(表单, 存入即生效, 多实例列表
  保留) ②站点权限(自动拉清单勾选 + 一键授权, 手动兜底收进折叠 details) ③**站点现状表**(一行一站:
  最近活动/动作与结果/用量(本时·本日 访问·下种 —— 阈值从 `SITE_CAPS` 取不写死)/状态(正常·受限·登录失效·异常,
  由该站最近一条事件的 tag 定)) ④**最近取数明细表**(环形 50 条: 时间/站点/类型/结果/耗时/大小) → 状态行 +
  自测/拉取按钮 → **折叠区**(运行日志全套[过滤/清空/限渲染原样保留] + 硬上限展示 + 高级 JSON + 保存);
  「清空日志」只清日志不动两表; 两表随后台落盘经 `storage.onChanged` 防抖自动刷新。
  ③ **守阵**: `test_background_events_ring_dual_write`(真跑 background.js 六类场景钉事件契约) +
  `test_options_swiss_wiring`(替掉三档接线守阵, 钉单一风格终态 + 共存机制不回潮)。
  ④ 全量 **1624 passed + 1 skipped**(TOTAL 92% / 10952 / 786 / 3636 / 327; 含远端 443a785 的 docker +6);
  基线已回写; README §2 改为终态口径; 制品 meta/认领链(计划 ↔ 档案双向引用)已按守阵要求闭环。
  待真机: reload 扩展后核两表在真实取数下的可读性。

- **2026-09-26 00:15 (v3.2 修正: 三模板改为**整页**三档)** — 用户纠偏「三种模板指的是整个扩展设置页面 3 个模板,
  不是实例端点的模板」。重做选项页结构: 页顶「页面模板」三卡 **极简 / 标准 / 完整**, 选择持久化到新键
  `uiTemplate`(首次默认: 有存量实例 → 标准, 全新安装 → 极简)。极简 = 粘 token + 自动拉站点 + 一键授权,
  收起多实例管理(`multiTools`)/手动兜底/硬上限展示/运行日志; 标准 = 极简 + 那些区块; 完整 = 标准 +
  「表单 / JSON 直接编辑」切换(旧 JSON 文本域原样保留, `setMode` 双向互导不变)。
  上一轮的「实例端点三模板」按钮撤销, 换成表单常驻 + 全新安装自动按本机默认预填。
  实现细节: 切档靠 `[hidden]`, 但 `div.row` 的 display:flex 等作者样式会盖过 UA 的 `[hidden]` ⇒
  加全局 `[hidden]{display:none!important}` 兜底(守阵钉住); 极简档多实例时亮提示行(`multiNote`),
  实例数据不动、轮询全部生效。守阵 `test_options_templates_and_site_checks_wiring` 改钉新接线
  (三卡/两模式按钮/区块 id/`uiTemplate`/`[hidden]` 兜底); 全量 **1617 passed + 1 skipped**(TOTAL 91% /
  10942 / 792 / 3636 / 329; 含远端 c46e67e 的 full-checking +3), 基线已回写; README §2 改为整页三模板口径。
  **选型结论(2026-09-26)**: 用户澄清三模板是三套独立风格、选一套实施 —— 出三套样张
  ([26-09-26-0031-plan-hr-ext-options-style.html](../plans/26-09-26-0031-plan-hr-ext-options-style.html)),
  **选定 A · 瑞士网格, 实施暂缓**;工作区「三档共存」实现如何处置待用户定(站点勾选授权半边是原始需求、应保留)。

- **2026-09-25 23:43 (v3.1 落地: 扩展配置简化 —— 三模板 + 站点勾选一键授权)** — 用户指令「HR 在线核实插件配置
  需要简化, 尽量做到自动: 站点权限可直接勾选已支持的站点 / 配置好后端后只需申请权限; 实例端点改为点击或输入,
  先做三个简单的模板供选择」。
  ① **端点新增只读 `GET /api/hr/sites`**(`channel.py::API_SITES` + `server.py::route/_sites_response`):
  与 `tasks`/`result` 同一道门(token + origin 白名单, 401 前不写任何状态), 返回
  `{sites: [{site, origin}], error, server_time}`; `sites_fn` 由 `runtime._site_origins` 提供 —— **每次请求现读
  配置**(热重载加站点不改端点监听身份、不重绑, 构造期快照会把新站点漏在授权清单外), 从各站点
  `hr_page_url` 派生 `scheme://host/*`(与 UrlPolicy 同源), `mode=off`/空 URL 不出现; `sites_fn` 抛异常
  (配置重载窗口)回 200 + 空清单 + error, 不打死端点线程。
  ② **扩展选项页重构**(`options.html`/`options.js`): 实例端点改**表单**(地址默认 `127.0.0.1:8788` 只粘 token;
  「存入实例列表」**即时落盘**, 列表可载入/删除, 同地址覆盖; 高级 JSON 保留为可切入口 —— 该轮先做成
  「实例端点三模板」, 次轮 v3.2 按用户纠偏改为**整页**三档, 见上一条)。
  ②站点权限改**从后端拉清单勾选**: 进页面自动拉一次(失败保持安静), 「全选」+「申请勾选站点的权限」一键授权
  (合并手动兜底条目并去重; 授权窗前**无 await** 保持用户手势), 勾选状态持久化到新键 `siteSelections`;
  手动填域名降级为 `<details>` 兜底, `siteOrigins` 键语义不变(后台本就不消费它, 权限真门是 Chrome)。
  归一化守则不动(先 normalize 再进浏览器 API)、日志区不动。
  ③ **测试 +7**: `test_hr_server.py` 4 条(清单下发/同门 401·403/sites_fn 异常不炸/无 sites_fn 向后兼容) +
  `test_extension_proxy.py` 2 条(`API_SITES` 与 `hr.channel` 同源钉死 / 三模板与勾选面接线齐全) +
  `test_hr_runtime.py::test_site_origins_served_live_for_extension`(现读派生 + 热加站点即生效 + mode=off 不出现)。
  ④ 全量 **1614 passed + 1 skipped / 18.6s**(TOTAL 91% / 10920 语句 / 792 未覆盖 / 3626 分支 / 327 partial),
  sidefx 越界 0; 基线已回写; 扩展 README §2 改写为新配置面。
  待真机: 扩展 reload 后走一遍「模板一 → 粘 token → 自动拉站点 → 一键授权 → 立即拉取」。

- **2026-09-25 17:37 (v3.0 落地: 达标判定来源优先级 —— 档位即结论)** — 接上一条计划收口, 用户令「修复问题, 落地」。
  ① `hr/model.py::satisfied_verdict`: A/B/C 三档**全部档位即结论** (A 考察中 / C 未达标 ⇒ False, B 已达标 ⇒ True),
  删「A/D 档看 remain_seconds == 0 ⇒ 已达标」推导 (v2.8 已实证该字段是考核窗口倒计时, 归零 = 考核到期, 方向
  相反) 与「缺字段回落本地」路径 (本地值不得越级推翻站点清单结论); D 已免罪不进命中清单, 未知档位才 None。
  ② `hr/resolve.py::judge_record`: 双命中 (hybrid 两 hash 映两个 tid) 改按 `(判定档位, 达标档位序)`
  取更保守者 —— 新增 `_lane_rank` (A=3 > B=2 > C=1), 删「首命中即 break」; 与键序无关。
  ③ `torrents/record.py::check_hr_satisfied` 分支逻辑不变 (site_satisfied 非 None 即采纳; mode=all 未核实的
  None 仍回落本地), 仅 docstring 同步; 四个消费点调用点零改动。
  ④ 测试 **+2** (`test_lane_verdict_ignores_remain_and_local`: A 档命中 + remain 归零/缺失都 ⇒ False, 本地
  不可越级; `test_judge_record_double_hit_prefers_lane_order`: B+A 双命中取 A、C+B 取 B, 两键序同结论)
  + 改写 1 (`test_judge_record_carries_site_satisfied_verdict`: A 档期望 None → False); test_hr_parse 注释与
  测试计划 docstring 同步。★**红验 3 条全红** (临时还原旧实现: A 档回落 None + 去档位序) 后还原全绿。
  ⑤ 全量 **1601 passed + 1 skipped / 18.6·18.1s** (TOTAL 91% / 10950 / 791 / 3594 / 326; HR 包 93%:
  2814 / 147 / 774 / 93); 基线已回写; 计划 v3.0 标记已落地 (§14 落地实况⑤)。

- **2026-09-25 17:10 (计划 v3.0: 达标判定来源优先级 —— 仅计划修订, 代码待落地)** — 用户指令: 「HR在线核实优先级:
  在线信息.考察中 > 在线信息.已达标 > 在线信息.未达标 > 本地信息」。核查现行实现, 两处与该优先级冲突:
  ① `hr/model.py::satisfied_verdict` 对 A/D 档用「剩余达标时间 == 0 ⇒ 已达标」推导 —— v2.8 已实证该字段是
  **考核窗口倒计时**, 归零 = 考核到期(方向相反); ② A 档缺字段时 None 回落本地, 本地值越权推翻站点的明确清单结论。
  计划 v3.0 收口: §9 新增「达标判定的来源优先级」节(档位即结论: A 恒未达标 / B 已达标 / C 未达标, 命中即停,
  数值字段降为展示与进度参照; 本地仅在清单未命中 / 站点不可查时兜底; hybrid 双命中按 A>B>C 取);
  §2 判定边界补句 / §4 流量字段行改口径 / §9 三态表受管束行改写 / M3 落地实况拍板②标注取代 /
  §12 守阵更新(A 档命中+本地够线⇒仍未达标 · 双命中取序 · remain 退出推导) / §13 决策记录补行 /
  §14 变更记录 v3.0 / 封面元信息与 colophon。**纯文档修订, 无代码变更, 测试基线不变**;
  落地时改 `satisfied_verdict` + `judge_record` 并补 §12 新守阵。

- **2026-09-25 (v2.9: 超龄豁免 —— 判定侧豁免 + 翻页早停)** — 用户指令: 「忽略下载时间超过一定期限的种子,
  比如完成时间超过一年的种子没有必要验证 HR, 甚至也没有必要往下翻页」。同步: 本 clone 落后 Gitee
  develop 51 提交(本地 master 齐平 origin/master 但 develop 已前进), 备份 .git 后 `merge --ff-only`
  快进到 1516bd6 —— M1–M4 与 v2.6~v2.8 修复均已由其它 clone 交付, 本轮在现实现上加功能。
  ① **判定侧**: 新站点级键 `trackers.<站>.hr_check.completed_age_limit`(0 = 关闭, 默认行为不变;
  开启时 1D~3650D, 单位写错如 365S 配置期拦下 —— 按秒配等于把刚完成的种子集体豁免)。
  `judge_record` 对锚点里**本地完成时刻**超线的种子直接给第四态 `HrIdentity.EXEMPT`「超龄豁免」:
  排在「无可查键回落本地」闸门**之前**(豁免是 qB 侧事实, 不依赖索引建到哪), **压过清单命中**
  与 unknown_policy, `mode: all` 也认 —— 都是配置者显式取舍, 写进 schema help 与 §13。
  参数由记录侧 `hr_judgement()` 从 `tracker_conf` 带进, 门面只透传(不多一次配置遍历)。
  WebUI 沿用 `state_text` 单点显示「超龄豁免」, 前端零改动。
  ② **取数侧**: 页面上超龄的行**不入索引、不回填 .torrent**(判定会豁免它们, 索引行留着只会白烧
  下载配额; 完成时间不可解析的行保留 —— 不猜); 当前页整页超龄且**页内 + 跨页都呈完成时间倒序**
  才允许早停 —— 后续页只会更老, 本档位在豁免线内的清单已全覆盖, **覆盖证明照常成立**
  (complete 可达 ⇒ 放行照常产生; 若把早停算成「不完备」, 清单长过豁免线的站点会永远没有放行,
  功能自废)。倒序证据不成立(页内升序 / 跨页倒序链断裂 / 缺完成时间)就照常翻到底 ——
  错误方向是多花配额, 不是漏判; 早停在 `refresh.reason` 留痕(`--hr-status` 可见)。
  ③ **测试 +17**(判定 7: 压过清单命中 / 线内不豁免 / 0 关闭 / completion_on 缺位不猜 /
  无可查键仍豁免 / mode=all 认 / 边界含等号; 取数 8: 关闭不变 / 行过滤不回填 / 早停跳页 /
  线内行阻止早停 / 页内升序不早停 / 跨页断链不早停 / 缺完成时间不早停 / 上页无时刻不早停;
  门面透传 1; 配置 1), ★红验 3 处(豁免短路 / 早停 / 行过滤停用 ⇒ 10 条守阵全红, 还原后全绿)。
  全量 **1593 passed + 1 skipped**(TOTAL 91% / 10849 / 791 / 3598 / 327; 并行 19.9s +
  一次 36.8s 负载离群; 本 shell 2 条 GBK 假红按 pitfalls/testing/patching.md 复测通过)。
  基线已回写(baseline.md + history)。文档: 计划 v2.9(封面/§4 早停 note/§7 键/§9 两表/§13 决策行/§14) ·
  docs/configuration.md「超龄豁免」节 · config-reference/keys.md。
  待真机确认: BTSchool 页面排序是否完成时间倒序(决定早停是否实际生效; 不倒序只是不省配额, 不会错)。
 (第七批: 取证误读修复 —— `--hr-status` 明细表改版 + 已取记录逐文件 ts)** —
  用户拿 `hr/BTSchool.json` 取证问「是否短时间产生了大量种子下载」(分析结论: 无 —— 当天对站点仅 5 次请求
  = 3 页 + 2 个 .torrent, 全在频控内; `downloaded[]` 是「已取 .torrent」凭据不是 qB 下载), 顺带点出两处真问题:
  ① `hr_downloaded[].ts` **整批共用开始时刻**(同批两条微秒级相同 ⇒ 看着像瞬间批量下载, 取证误读);
  ② `--hr-status` 明细的「剩余达标」列(9d21h)会被读成「还要做种 9 天」—— 它实际是**考核窗口**
  (9d21h 内要完成做种要求), 真正的「还需做种时间」只有 16h57m。
  修: ① `_fill_infohashes` 的 ts 改记**各 .torrent 自己的取回时刻**(顺带同源的 `fail.last_ts` 一并修准);
  ② 明细表列 = tid / 档位(考察中·已达标·未达标·已免罪, 单点 `status.LANE_TEXTS`) / 上传量 / 下载量 / 分享率 /
  还需做种(镜像站点书写形态 HH:MM:SS·「N天HH:MM:SS」) / 名称(按**显示格宽**截断 40) / infohash;
  **剩余达标时间不再显示**; 列对齐走自写 `_dwidth/_pad`(str.format 按字符数对齐, CJK 双宽会错位)。
  测试 +2(service 1 钉逐文件 ts / report 1 钉 CJK 对齐·截断·列改版), 全量
  **1573 passed + 1 skipped**(TOTAL 91% / 10905 / 789 / 3582 / 327; HR 包 93%: 2782 / 143 / 766 / 91)。

- **2026-09-25 03:50 (v2.7 实报修复: 增量落盘)** — 用户删 hr_check 数据重启实测:「BTSchool.lock 长期被持有 /
  后端无落盘, Ctrl+C 后才落盘」。诊断(无死锁): v2.6 修好后一轮真实跨多个扩展轮询周期(3 页 + 回填, 中间夹
  间隔等待, 分钟级、按 §5/§8 **持锁进行**), Ctrl+C 打断的是**派发前的间隔睡眠**(sleeper 可中断, 日志
  「放弃本轮剩余的等待」即它), 轮次随即完成记账并落盘 —— 所以「Ctrl+C 后成功落盘」; 但落盘只在**轮尾**,
  中途断电/Ctrl+C 会丢已抓页面与配额账本。修: **每抓到一页**(complete=False 语义合并, 只置命中为 active)
  与**每个 .torrent 结果**(hr_downloaded 凭据 / fails 记账)当场提交; 轮尾仍按完整语义合并 + 写覆盖证明;
  叫停备注改「下载阶段被叫停」(叫停≠一定在取 .torrent)。⚠ `<site>.lock` 文件在释放后仍存在属正常
  (OS 级锁, 进程死即释放, 文件在 ≠ 被持有)。测试 +1, ★红验 1; 全量 **1571 passed + 1 skipped**(TOTAL 91% / HR 包 93%)。

- **2026-09-25 (审查修复: 通道时序错配 + 饿死残留, 计划 v2.6)** — 用户令「审查计划实施情况」并点名
  「种子下载不触发」, 中途补报 02:20 实测日志「tid=327727 取 .torrent 失败: 等待浏览器扩展取数超时(180s)」。
  审查结论: M1-M4 落地与计划一致、安全面(token/origin/SSRF/任务绑定/凭据归零)无高危, 但「不触发」的根因链清晰:
  ① **主因 = 通道时序错配**: 扩展 `chrome.alarms` 5 分钟轮询 vs 后端 `request_timeout=180s` ⇒ 轮询周期 300s >
  等待窗口 180s, 每条任务约四成概率因轮询相位落窗外直接超时(烧配额 + 计失败 ⇒ 3 次页面失败 = 12h 熔断);
  计划 §6 原是「批量清单」模型, 实现却是「派一条等一条」⇒ `MAX_BATCH=16` 永远只装得下 1 条。
  修: 扩展 `POLL_MINUTES` 5 → **1**(空轮询只打 loopback), `DEFAULT_POLL_HINT` 300 → 60, §6 补时序硬约束。
  ② **v2.4 P1 的饿死残留**: 不完备有效期 60s == poll 60s ⇒ 下一轮永远晚一个 ε ⇒ 复用轮补下载从不发生;
  且页面取数失败的 `except HrFetchError` 分支直接 return ⇒ 回填被一起跳过。修: 有效期 `max(120s, 2×poll)`
  (判定不读 expires_at, 拉长不产生放行) + `_backfill_on_page_failure`(页面失败后仍补一次下载, 待回填来自
  已持久化索引)。
  ③ **下载阶段异常语义**: `HrChannelStopped` / `HrChannelQuota` / `HrLoginExpired` 是 `HrFetchError` 子类,
  曾被 `_fill_infohashes` 吞掉计成 tid 失败(关停三次 = 12h 冷却) ⇒ 原样上抛 + `_guarded_backfill` 折成备注;
  扩展 fetchBinary 检测 download.php 返回 HTML(SameSite 剥 cookie 实测风险) ⇒ 新 `KIND_LOGIN_PAGE` ⇒
  后端按 `HrLoginExpired` 处置(不计失败)。
  ④ 展示与边角: 配额展示按窗口键折算(修「本小时 7/12 · 还能取 12 次」自相矛盾)、`--hr-status` 去掉
  「v1/v2 各一」硬编码后缀、Retry-After 以 cooldown 封顶、ext-quota 告警文案补「扩展上限本就低于后端配额」、
  qbmanager 死注释校准。
  ⑤ M0 实测收口: 下载 URL = `https://pt.btschool.club/download.php?id=<tid>`(用户实测, 计划 §13 已标)。
  测试 +11(service 7 / fetcher_channel 1 / ratelimit 1 / report 1 / extension_proxy 1), ★红验 7 条(还原旧实现
  全红); 全量 **1570 passed + 1 skipped**(TOTAL 91% / HR 包 93%; 本 shell PYTHONUTF8=1 的 2 条 GBK 假红
  单独复测通过)。扩展需在 chrome://extensions **reload 一次**才吃到 1 分钟轮询与登录页检测。
  计划文档已按用户令直接改原文档(v2.6 变更行 / 封面 / §6 / §13 / 页脚); 基线已回写。

- （本段更早的进度纪要已外迁: [attachments/26-09-22-backend-partial-hr-verify-log.md](attachments/26-09-22-backend-partial-hr-verify-log.md) —— 触顶处置见 `.agents/skills/memory-bank/scripts/_common.py` 的 `TASK_LOG_CAP`）
