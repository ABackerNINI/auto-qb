# 部分种子 HR 在线核实
> 摘要: **M1 核心管道已落地**（`src/auto_qb/hr/` 10 模块 + 配置全链路 + `--hr-once` 只读走查）；余 **M2 取数通道 / M3 判定联动 / M4 多站点**。两条配置期 fail-fast 是防「整站保护静默失效」的关键
> 触发: 部分种子, HR 核实, 浏览器扩展, 三态判定, 带锁访问, 共享站点数据, 转移种子, 多客户端, BTSchool, hr_check, hr_once, 取数通道
> 最后活动: 2026-09-24 21:40

## 状态

**M1 已交付（2026-09-24，离线可做，不需要浏览器）**：新包 `src/auto_qb/hr/` —

| 模块 | 职责 |
|---|---|
| `bencode` | infohash 只取 **info 的原始字节切片**（定位跨度时只做字节跳跃，不解码 info）；畸形/深嵌套拒收 |
| `parse` | 栈式 `<tr>/<td>` 树（容忍 NexusPHP 的 `<td class="embedded">` 包裹表）+ 数值容错（认不出返回 None，不猜） |
| `adapters/` | 站点隔离；现只有 **NexusPHP `myhr.php` 九列形态**（首站 BTSchool）。`header_found` 是「改版」与「合法空结果」的唯一区分器 |
| `model` | 站点文件内容：`index` / `downloaded` / `fails` / `verified` / `refresh` / `quota` / `fuse` |
| `store` | **每站点一个 JSON + 一把 filelock**；持锁期间完成「读→判有效期→必要时抓→写→释放」全程；revision 回退或本实例心跳被覆盖 ⇒ 判锁不生效并**退化为只读** |
| `ratelimit` | 间隔**只向上抖动** +0~25%、小时/天两级配额（按窗口键幂等）、失败退避熔断、`allow_window` 可跨午夜 |
| `resolve` | **三态**（受管束 / 已核实不受管束 / 未核实）+ 新鲜度闸门 + 锚点漂移 + 放行有效期；不可变视图，时间敏感判定**读取时现算** |
| `service` | 刷新管道。`persist` × `allow_fetch` 组合出三种口径：正常 / `--dry-run`（零请求零写入） / `hr.once`（抓但只读） |
| `fetcher` | 取数通道协议 + `NullFetcher` —— 无通道时**如实上报**，绝不静默降级为后端直连（零 cookie 边界） |
| `report` + `cli --hr-once` | 真机只读走查：不加锁、不写盘、不连 qB，可正常实例运行期间跑 |

配置全链路已通：`KNOWN_CONFIG_KEYS` + `KNOWN_HR_CHECK_KEYS`/`KNOWN_HR_CHANNEL_KEYS`/`KNOWN_SITE_HR_CHECK_KEYS` +
校验器 + `config/schema/hr.py`（设置页新分组「HR 在线核实」+ 站点段 `hr_check`）+ `HR_CHECK_FIELD_LEVELS` +
loaders + 设置页 Hub 文案/读数。

**两条 fail-fast 是这一轮最值钱的防线**（都在配置期直接报错）：
① 站点 `mode != off` 却没配 `hr` 段 —— 否则 `check_hr_condition` 首行 `if not self.tracker_conf.hr` 恒 False，
整站保护**静默失效且无任何报错**；② `hr_page_scopes` 必须含 **A+B+C** —— 少抓一档会让该档种子在
「完整刷新」里未列出而被**误放行**（漏 HR）。

## 未完成

- **M2 取数通道**（1–2 会话）：MV3 薄代理（后台标签页取 DOM/.torrent + 回传，不碰 cookie API）+
  本地端点（`127.0.0.1` + token + origin/SSRF 白名单，只入队）+ **取数线程**（按 `poll_interval` 自醒，
  持锁，不碰 state_file/队列/store）+ 共享站点数据。
  ❗落地时**必须同时**把 `HR_CHECK_FIELD_LEVELS` 的 `channel` / `shared_dir` 改为 **L1**，并在
  `QbManager.apply_new_config` 的 L1 分支补端点「先停旧、等线程退出、再启新」的重挂
  （`tests/test_hr_config.py::test_impact_channel_field_is_l0` 就是那条改动的固定桩）。
- **M3 判定联动**（1 会话）：把三态接进 `TorrentRecord.check_hr_condition`/`check_hr_satisfied` 与四个消费点
  （打标 / WebUI 视图 / `hr` 规则条件 / `tor.hr_*` 表达式），含 **`mode: all` 语义升级**（站点侧驱动 +
  未核实恒受管束）与「转移种子」回归。判定逻辑本身已测好，缺的只是接线 + 前端 H&R facet。
- **M4 多站点与打磨**（1 会话）：第二/第三个站点 adapter、索引新鲜度展示、notify 四类事件、用户文档。

## 待实测（计划 §13，不阻塞）

`?page=N` 真实参数名与 passkey 形态 / BTSchool 各档语义与分页到底判据 / 后台标签页观感与 CF 挑战 /
共享目录上 filelock 是否真互斥。部分结构已由本轮 fixture 钉死（灰色不可点的「下一页」判到底 /
免罪链接 / 九列表头）。

- [计划](../plans/26-09-22-2204-partial-hr-site-verify-plan.html) · [档案](../tasks/26-09-22-backend-partial-hr-verify.md)

## 实测

全部离线样本（脱敏 fixture 取自真实样张结构）在 `tests/test_hr_*.py` 8 个文件里；
全量测试数字只认单点 [testing/baseline.md](../testing/baseline.md)（本切片不复述）。
