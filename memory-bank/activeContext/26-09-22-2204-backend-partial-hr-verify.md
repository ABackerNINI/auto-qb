# 部分种子 HR 在线核实
> 摘要: **M1-M4 已全部落地, 六批实报修复完, 余真机走查**。核心链路: 浏览器扩展代取(登录态不出浏览器) →
后端解析算 infohash → (站点, tid) 索引对账 → 三态判定(受管束/安全放行/未核实, 站点侧权威)进四个消费点。
站点分文件 + 每站一把锁 + 频控(90s 间隔 · 12/时 · 60/天) + 扩展侧第二道闸(访问 10/时·50/天, 下种 50/时·200/天)。
> 触发: 部分种子, HR 核实, 浏览器扩展, 三态判定, 带锁访问, 共享站点数据, 转移种子, 多客户端, BTSchool, hr_check, hr_once, hr-status, 取数通道, 本地端点, 取数线程, 告警级别, 站点文件损坏, 多站点, 站点状态, 四类事件, 登录失效, 轮询周期, request_timeout, 复用轮, 回填, 明细表
> 最后活动: 2026-09-25 05:01 (第七批: 明细表改版 + 逐文件 ts)

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

模块分工 / 字段口径 / 配置项 / 扩展行为: [modules/overview.md](../modules/overview.md) ·
[docs/configuration.md](../../docs/configuration.md) · [扩展说明](../../extensions/hr-fetch-proxy/README.md)。

## 未完成

- **真机走查**(需用户装扩展): ❗先在 chrome://extensions **reload 扩展**(v2.6 的 1 分钟轮询与登录页检测要重载生效),
  再跑 `--hr-once` + 主程序一轮, 确认取到 `.torrent` 后索引长出 infohash 键、三态在 WebUI 与日志上对得上;
  之前 `fuse.failures=2` 已定位 = 5 分钟轮询 vs 180s 窗口错配超时(v2.6 已修)。
- **非 NexusPHP 形态的第三个站点**(需站点样本): 只啃过 NexusPHP `myhr.php` 九列表形态;
  有更便宜来源(JSON 接口/逐种标记)按 `adapters/__init__.py` 注册协议加 adapter —— **不拿到真实样本不猜着写**。
- ⛔ **待用户定**: `config.yml` 被 git 跟踪且含明文 qB 凭据 —— 入不入池 issue。

## 待实测(计划 §13, 不阻塞)

~~download URL 形态~~ ✅ 已收口: `https://pt.btschool.club/download.php?id=<tid>`; 余:
BTSchool 各档语义与分页到底判据 / **后台取数是否被站点在线时长识别或 CF 挑战** / 共享目录 filelock 真互斥。
结构类判据已由 fixture 钉死(灰色「下一页」/ 免罪链接 / 九列表头)。

- [计划](../plans/26-09-22-2204-partial-hr-site-verify-plan.html) · [档案](../tasks/26-09-22-backend-partial-hr-verify.md) ·
  [扩展说明](../../extensions/hr-fetch-proxy/README.md)

## 实测

离线样本(脱敏 fixture 取自真实样张结构) + 真回环 HTTP 往返在 `tests/test_hr_*.py`;
全量测试数字只认单点 [testing/baseline.md](../testing/baseline.md)(本切片不复述)。
扩展侧已不止语法校验: `tests/test_extension_proxy.py` 用假 `chrome` API **真跑** `background.js` 与 `normalize.js`;
**真机链路仍未实测**(需用户装扩展 → M3 的真机 `hr.once` 走查)。
