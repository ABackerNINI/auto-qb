# 部分种子 HR 在线核实
> 摘要: **M1-M4 已全部落地, 七批实报修复完 + v2.9 超龄豁免 + v3.0 达标来源优先级(档位即结论), 余真机走查**。核心链路: 浏览器扩展代取(登录态不出浏览器) →
后端解析算 infohash → (站点, tid) 索引对账 → 三态判定(受管束/安全放行/未核实 + 超龄豁免, 站点侧权威)进四个消费点。
站点分文件 + 每站一把锁 + 频控(90s 间隔 · 12/时 · 60/天) + 扩展侧第二道闸(访问 10/时·50/天, 下种 50/时·200/天)。
> 触发: 部分种子, HR 核实, 浏览器扩展, 三态判定, 达标来源优先级, 档位即结论, 带锁访问, 共享站点数据, 转移种子, 多客户端, BTSchool, hr_check, hr_once, hr-status, 取数通道, 本地端点, 取数线程, 告警级别, 站点文件损坏, 多站点, 站点状态, 四类事件, 登录失效, 轮询周期, request_timeout, 复用轮, 回填, 明细表, 超龄豁免, completed_age_limit, 翻页早停
> 最后活动: 2026-09-26 01:30 (v3.3 落地: 风格 A 终态实施 + 两表 + 日志收起, 本 clone3)

## 状态

### 已交付(明细都在[档案](../tasks/26-09-22-backend-partial-hr-verify.md)进度日志与[计划](../plans/26-09-22-2204-partial-hr-site-verify-plan.html)变更行, 此处只留结论)

- **M1 核心管道 + M2 取数通道**(2026-09-24): 离线管道(bencode 原始切片 · NexusPHP 解析 · 站点分文件+锁 ·
  频控 · 三态判定) / 本地端点+取数线程+MV3 扩展 / 端点与凭据安全(token·origin·URL 白名单·凭据归零)。
  两条配置期 fail-fast 仍在生效: `mode != off` 必配 `hr` 段 / scopes 必含 A+B+C。
- **M3 判定联动**(2026-09-25): 收口 `hr/resolve.py::judge_record`, 门面 `HrRuntime.judge()`;
  **四个消费点(打标/视图/规则条件/表达式)调用点一行未动**, 站点侧优先、缺字段回落本地;
  判定桥稳定引用 + 读取时现算(不置脏)。零静默变更两道门。实现期拍板: 站点没发布过视图 ⇒ 回落本地;
  站点行缺达标字段 ≠ 未达标。
- **M4 多站点与打磨**(2026-09-25): 四类事件语文化 `hr/events.py`(登录失效从熔断摘出); 站点级状态单点
  `hr/status.py::site_status()`(CLI 与 WebUI 同一套数); WebUI 出口 `GET /api/hr/status` + 设置页章节
  + 前端字段守阵; 多站点守阵 `test_hr_multisite.py`。
- **七批实报修复**(2026-09-24/25, 详见档案): 告警分级归属(节流态 INFO 按根因去重) / 站点文件自愈(.bak) /
  `--hr-status` 现状报告 / 取数改扩展隐藏窗口→无界面直取 / 下载被页面饿死(复用轮只补下载) + 生产不等间隔
  (可中断锁内等待) + 无索引键整站打标(回落本地) + 扩展侧第二道闸 `site-caps.js`(让位不计失败) /
  通道时序错配(扩展轮询 5→1 分钟) + 复用轮 60s/60s 竞速 + 页面失败跳过回填 + 让位异常计 tid 失败 /
  增量落盘(每页每 .torrent 当场提交, 治「Ctrl+C 后才落盘」)。
- **第七批: 取证误读修复**(2026-09-25 05:01): ① `hr_downloaded[].ts` 改记**各 .torrent 自己的取回时刻**
  (原整批共用开始时刻, 同批微秒级相同 ⇒ 取证误读为瞬间批量下载); ② `--hr-status` 明细表改版 ——
  列 = tid/档位(考察中等实际意思, `status.LANE_TEXTS`)/上传量/下载量/分享率/还需做种(镜像站点
  HH:MM:SS 形态)/名称(按显示格宽截断)/infohash, **剩余达标时间不再显示**(它是考核窗口 9d21h,
  会被误读成还需做种 9 天); CJK 双宽对齐走自写 `_dwidth/_pad`。测试 +2, 全量 1573 passed + 1 skipped。
- **v2.9 超龄豁免**(2026-09-25, clone2): 用户指令「完成时间超过一年(可配)的种子不必验证 HR, 也不必再翻页」⇒
  新站点级键 `completed_age_limit`(0=关闭, 1D~3650D): 判定收口给第四态 `EXEMPT`「超龄豁免」
  (压过清单命中与 unknown_policy, mode=all 也认, 排在「无可查键回落本地」之前); 取数侧超龄行不入索引/
  不回填, 整页超龄且页内+跨页倒序成立才早停(覆盖证明照常成立; 证据不全照常翻 —— 错误方向是多花配额)。
  测试 +17, 红验 10 条全红; 全量 1593 passed + 1 skipped。待真机确认: BTSchool 页面排序是否完成时间倒序。

- **v3.0 达标判定来源优先级: 档位即结论**(2026-09-25 17:37, clone2): 用户指令钉死「在线考察中 > 在线已达标 >
  在线未达标 > 本地」⇒ `hr/model.py::satisfied_verdict` A/B/C 三档**全部档位即结论**(A/C ⇒ 未达标,
  B ⇒ 已达标), 删「A/D 档看剩余达标时间归零 ⇒ 已达标」推导(v2.8 已实证该字段是考核窗口倒计时, 方向相反)
  与缺字段回落本地(本地不得越级推翻站点清单结论); `hr/resolve.py::judge_record` 双命中(hybrid 两 hash)
  改按达标档位序取(A>B>C, 新增 `_lane_rank`, 删「首命中即 break」); `check_hr_satisfied` 分支逻辑不变
  (site_satisfied 非 None 即采纳), 四个消费点调用点零改动。测试 +2 + 改写 1, 红验 3 条全红; 全量
  1601 passed + 1 skipped。

- **v3.1+v3.2 扩展配置简化**(2026-09-25/26, clone3): 用户令「插件配置尽量自动: 站点权限直接勾选已支持站点 /
  配置好后端后只需申请权限; 设置页做三个简单模板供选择」。端点新增只读 `GET /api/hr/sites`
  (`runtime._site_origins` **每次请求现读**配置派生 `scheme://host/*` —— 热重载加站点不重绑端点也能拿到;
  sites_fn 异常回 200+空清单+error 不炸); 扩展选项页**整页三模板**(v3.2 纠偏: 三档是整页而非实例端点):
  极简 = 粘 token + 自动拉站点 + 一键授权(收起多实例/兜底/硬上限/日志), 标准 = + 那些区块,
  完整 = + 「表单 / JSON 直接编辑」切换; 选择持久化 `uiTemplate`(全新安装默认极简、存量用户默认标准),
  站点权限**拉清单勾选 + 一键授权**(进页面自动拉, 勾选持久化 `siteSelections`, 手动填域名降级兜底)。
  切档靠全局 `[hidden]{display:none!important}` 兜底(div.row 等作者样式会盖过 UA 的 [hidden])。
  测试 +7, 全量 1617 passed + 1 skipped(含远端 c46e67e 的 full-checking +3)。

模块分工 / 字段口径 / 配置项 / 扩展行为: [modules/overview.md](../modules/overview.md) ·
[docs/configuration.md](../../docs/configuration.md) · [扩展说明](../../extensions/hr-fetch-proxy/README.md)。

## 未完成

- **真机走查**(需用户装扩展): ❗先在 chrome://extensions **reload 扩展**(v2.6 的 1 分钟轮询与登录页检测要重载生效;
  v3.1 的新选项页也要 reload 后才见), 再跑 `--hr-once` + 主程序一轮, 并走一遍新配置面
  「模板一 → 粘 token → 自动拉站点 → 一键授权 → 立即拉取」, 确认取到 `.torrent` 后索引长出 infohash 键、
  三态在 WebUI 与日志上对得上; 之前 `fuse.failures=2` 已定位 = 5 分钟轮询 vs 180s 窗口错配超时(v2.6 已修)。
- **非 NexusPHP 形态的第三个站点**(需站点样本): 只啃过 NexusPHP `myhr.php` 九列表形态;
  有更便宜来源(JSON 接口/逐种标记)按 `adapters/__init__.py` 注册协议加 adapter —— **不拿到真实样本不猜着写**。
- ⛔ **待用户定**: `config.yml` 被 git 跟踪且含明文 qB 凭据 —— 入不入池 issue。

- **v3.3 已落地**(2026-09-26 01:30, clone3): 风格 A 瑞士网格终态实施完成 —— 后台 events 事件环双写 +
  选项页两表(③站点现状 / ④取数明细) + 日志收进折叠区; 三档共存实现已被样张 A 终态**替换**;
  全量 1624 passed + 1 skipped。待真机: reload 扩展核两表可读性。
- ⛔ **待用户定**: 选项页风格选型档案([26-09-26-0031](../plans/26-09-26-0031-plan-hr-ext-options-style.html))
  doc-status 仍为 In Progress —— 实施已落地, 是否改为 Done 由用户定(连同 v3.1+v3.2 未提交改动的处置)。

## 待实测(计划 §13, 不阻塞)

~~download URL 形态~~ ✅ 已收口: `https://pt.btschool.club/download.php?id=<tid>`; 余:
BTSchool 各档语义与分页到底判据 / **HR 页排序是否按完成时间倒序**(v2.9 翻页早停的实际生效前提,
不倒序只是不省配额不会错判) / **后台取数是否被站点在线时长识别或 CF 挑战** / 共享目录 filelock 真互斥。
结构类判据已由 fixture 钉死(灰色「下一页」/ 免罪链接 / 九列表头)。

- [计划](../plans/26-09-22-2204-partial-hr-site-verify-plan.html) · [档案](../tasks/26-09-22-backend-partial-hr-verify.md) ·
  [扩展说明](../../extensions/hr-fetch-proxy/README.md)

## 实测

离线样本(脱敏 fixture 取自真实样张结构) + 真回环 HTTP 往返在 `tests/test_hr_*.py`;
全量测试数字只认单点 [testing/baseline.md](../testing/baseline.md)(本切片不复述)。
扩展侧已不止语法校验: `tests/test_extension_proxy.py` 用假 `chrome` API **真跑** `background.js` 与 `normalize.js`;
**真机链路仍未实测**(需用户装扩展 → M3 的真机 `hr.once` 走查)。
