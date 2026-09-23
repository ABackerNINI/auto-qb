# 26-09-22-backend-partial-hr-verify — 部分种子 HR 的在线核实

**Status:** Open
**Added:** 2026-09-22
**Updated:** 2026-09-22
**Summary:** 部分种子 HR 站点在线核实 (抓 HR 统计页 + 下载 .torrent 算 infohash 对账建索引) 的可行性分析与实施计划 v1.1 待拍板 (v1.1: HR 页八字段入模 / (站点,tid) 主键跨站隔离 / 防重复下载三层); 计划见 memory-bank/plans/26-09-22-2204-partial-hr-site-verify-plan.html, 开放问题 4 条待拍板后进 M0。
**Topics:** backend-partial-hr-verify

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
| 开放问题 5 条拍板 (首批站点 / 页面有无要求值 / 频度默认 / unknown_policy / cookie 分期) | Pending | 等用户; 拍板前不动代码 |
| M0 调研与拍板 (样本 fixture / URL 形态 / 解析器与 bencode 选型) | Pending | 0.5 会话 |
| M1 核心管道 (dry-run) | Pending | 1–2 会话 |
| M2 频控与后台化 | Pending | 1 会话 |
| M3 判定联动 + 真机走查 | Pending | 1 会话 |
| M4 cookie 自动化 (CDP / Firefox) | Pending | 1 会话, 可选顺序调整 |

## 进度日志

- **2026-09-22 22:04** — 可行性分析完成, 计划 v1 产出 ([../plans/26-09-22-2204-partial-hr-site-verify-plan.html](../plans/26-09-22-2204-partial-hr-site-verify-plan.html))。读路由: config-reference (keys / loading-and-write) · systemPatterns (taskqueue / web-runtime / client-and-state) · modules/overview · conventions/webui; 源码锚点: TorrentRecord.check_hr_* / mixins/tags._add_hr_tag_or_category / mixins/web_view._hr_view_fields / rules (conditions + expr/env) / qbmanager._create_global_tasks; 外部事实两条经 web_search 核实。立档 (阈值 #4: 产出计划文档)。下一步: 等开放问题拍板 → M0。
- **2026-09-22 22:10** — 全量闸门首跑红 1 条 (`test_doc_links_are_not_broken`): 本档案内链接深度误写 `../docs` (`memory-bank/tasks/` 到根 `docs/` 应为 `../../docs`), 修正后重跑全绿 (1189 passed + 1 skipped, TOTAL 91%, 与基线稳态一致)。该坑已有守阵 (test_memory_bank.py 链接机检) 兜住, 不另立 pitfalls 条目。
- **2026-09-22 23:00** — 用户指令: 同步远端 + 在 scripts/ 实现独立实验程序 (用现有 cookie 下载 HR 种子)。
  ① 同步: preflight 报落后 3 提交(按 origin/GitHub 快照), 实拉 gitee/develop 确认 3 提交 (e50755d 同步规则修正 / a61d0f4 README 同步 / 49eacb8 入池跨组交叉 issue), 恰好都动本轮两个脏文件 → 走 sync-pull 安全流程 (diff --output 备份 + restore + ff-only); restore 后 activeContext 仍幽灵 M 拒 ff, `git add`+`git reset` 刷新后 ff 成功 → 49eacb8; 会话回写已在新版本上重施 (activeContext 滚动链压缩了远端三条旧状态)。
  ② 页面解剖: 样张 `D:/Projects/站点页面/` (myhr.php, utf-8, 含 Darkreader 属性); HR 表在 `<td class=embedded>` 包裹表内 (两层嵌套), 表头 colhead 九列与用户描述一致; 页面无 download.php 链接 (按 NexusPHP 惯例拼 download.php?id={tid}); 状态过滤 hrtype=A考察中/B已达标/C未达标/D已免罪; 样张含 1 行 (tid 313852, 27.34 GB, 还需做种 2:42:17, 剩余达标 9天06:05:11)。
  ③ 交付 `scripts/hr_fetch_experiment.py` (独立实验, 不接主程序): bencode 解码 + infohash v1/v2 (原始字节切片) + 栈式树 HTML 解析 (容忍包裹表) + 离线 `--html` / 在线 `--cookie-file` 两模式 + 限速下载 (±25% 抖动, 已存在文件跳过防重下) + `--selftest` 钉死向量。
  ④ 验证: selftest 11 项全过 (2 infohash 向量 + 9 数值解析); 离线解析样张 1 行全部字段正确; **在线路径未验证 (需用户 cookie)**。过程中自测向量当场抓到一个真 bug: 向量生成器用 `data[start:-1]` 粗切 info 切片, 当 info 后还有顶层键 (private) 时期望值错 —— 修正生成器后确认解码器无误; 向量改 base64 装载避开二进制转义层。
  ⑤ 下一步: 用户拿 cookie 跑在线模式验证下载 URL 形态 (是否需 passkey) → 拍板开放问题 4 条 → M1。
- **2026-09-23 00:15** — 用户: 「我需要的是自动抓取cookie」⇒ 实验脚本升级 --auto-cookie / --auto-cookie-login:
  专用浏览器 profile + CDP (Storage.getCookies) 自动读 cookie —— Chrome 136+ 禁默认目录开调试端口的
  合规路线; 首次可见登录一次, 之后无头全自动; cookie 不落明文 (浏览器自己解密, 脚本只经内存)。
  实现: 浏览器探测 (chrome→edge, 可指定路径) + 极小 WebSocket 客户端 (手写帧/mask/ping-pong, 零新依赖)
  + Browser.close 优雅退出。
  实测三坑: ① 启动器进程秒退 (exit 0/21, ProcessSingleton 直方图证实移交) 而真实浏览器存活 —— 就绪判定
  只看调试端口, 不能用 proc.poll(); ② proc.terminate() 只杀启动器杀不掉浏览器树 —— 改按命令行匹配
  profile 路径 taskkill /T /F (不碰用户自己的浏览器); ③ 被杀残留的 profile 状态会让下次启动端口不再就绪
  (Edge 报 crashpad "Settings version is not 7") —— 加 --disable-crashpad + profile 绝对路径; 失败信息引导删
  profile 重登。
  验证: selftest 11/11; --auto-cookie 全新 profile 无登录态: 无头拉起→CDP 抓取(0 条)→干净报错→清理零残留,
  机器链路全通, 仅剩人工登录一步; 安全护栏拦了一次 rm profile 目录 (改用全新目录验证, 不重试删除);
  全量 1189 passed + 1 skipped (TOTAL 91%)。用户已令「提交」, 流水线进行中。
- **2026-09-22 22:32** — 用户补充 HR 页字段与防重下要求 ⇒ 计划升 v1.1: 索引改 (站点, tid) 主键 + infohash 回填; 新增 `hr_downloaded` 永久已下载层与 `hr_dl_fails` 重试记账 (新配置键 `max_download_retries`); 反查键 (站点, infohash) 跨站独立; 进度字段「展示/交叉核对, 判定以 qB 本地值为准」; 原开放问题「页面是否给要求值」解决, 新增「进度字段用途边界」, 余 4 条待拍板。
