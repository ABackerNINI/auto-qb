# 26-09-22-backend-partial-hr-verify — 部分种子 HR 的在线核实

**Status:** Open
**Added:** 2026-09-22
**Updated:** 2026-09-24
**Summary:** 部分种子 HR 站点在线核实 (取 HR 统计页 + 取 .torrent 算 infohash 对账建索引) 的可行性分析与实施计划 **v1.8**（决策 5/5 已拍板 + 已做一轮文档漂移清理, 待开工）。取数通道 = **浏览器扩展** (手工 cookie 否决; 形态无关, 都跑在日常浏览器) ⇒ 后端零 cookie/passkey 依赖。判定 = **三态** (受管束 / 安全放行 / 未核实) + **站点侧权威** (触发与达标看站点侧, 治转移种子与多客户端漏管), `mode: all` 也纳入。多实例 = **站点分文件 + 每站点一把锁 + 持锁期间完成读/抓/写 + 有效期复用即计配额**; 取数节奏**与主循环 tick 解耦** (按 `poll_interval` 自醒, 视图只在数据实质变化时抬 `revision` ⇒ 版本未变主循环零工作); 线程三分职责 (取数线程持锁+发布只读视图, 主循环只读且是 state 唯一写者); **channel 推荐每台「本机有浏览器」的实例都启用** (多通道 + 同站点锁 ⇒ 不会双倍访问站点、无单点故障)。计划见 memory-bank/plans/26-09-22-2204-partial-hr-site-verify-plan.html, 决策记录与 M0 实测清单见其 §13。
**Topics:** backend-partial-hr-verify
**Refs:** memory-bank/plans/26-09-22-2204-partial-hr-site-verify-plan.html

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
| M0 实测收口 (download URL 形态 / BTSchool scope 与分页判据 / 后台标签页观感 / 共享目录 filelock 互斥) | Pending | 4 项实测 (**不阻塞 M1**, 可与 M1/M2 并行) |
| M1 核心管道 (离线可做) | Pending | 1–2 会话, 输入 = 实验脚本 |
| M2 取数通道 (扩展 + 本地端点) | Pending | 1–2 会话 |
| M3 判定联动 + 真机 `hr.once` 走查 | Pending | 1 会话 |
| M4 多站点与打磨 | Pending | 1 会话 |

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
- **2026-09-24 18:08** — 用户: 「审核该计划是否有问题和可优化的地方」+「更新计划, 否定手动填写 cookie … 比较两种扩展方式的实现维护成本与效果」。
  ① 审核 (只读, 未改任何文件): 查出 4 条事实性错误/过期 —— 计划不知 `scripts/hr_fetch_experiment.py` 已落地并部分验证 (bencode/infohash + 钉死向量 11 项 + myhr 解析 + 限速下载 + CDP 抓 cookie);
  `mixins/web_view.py` 路径不存在, 实为 `webui/views.py::_hr_view_fields` 且被 **Web 线程**调用 (`webui/server/routes/torrent_detail.py`);
  测试基线数字过期 (计划写 1190/1188, 单点 baseline.md 实为 1203/1202+1); `fetch_window` 全库无此键, notify 的同类项是**语义相反**的 `quiet_hours`。
  另 3 条架构判断需修正 (身份字段不能反向依赖 `manager.state`; partial 站点未配 `hr` 段则 `check_hr_condition` 恒 False、保护静默失效; 线程生命周期与 notify 跨线程),
  3 条内部矛盾 (配额口径"全站合计"vs"站点独立" / 抖动 ±25% 与"间隔 ≥ min"验收互斥 / dry-run"零请求"与 M1"报告含新增"互斥)。
  ② 用户否决手工填写 cookie (「解决麻烦不是制造新的麻烦」), 要求比较扩展的两条路线。v1.2 采纳**路线 1**: 扩展在后台标签页取 DOM 快照与 .torrent 二进制 → **回传后端解析** (扩展=哑取数器, 无策略/无解析/不碰 cookie API), 通道走拉取式任务 ⇒ 后端零 cookie/passkey 依赖、零凭据配置、cookie 风险整体移除; 路线 2 (扩展内解析) 判为改版成本落在用户侧 (要重装扩展) 且解析脱离 pytest/fixture 体系, 仅在"必须交互才出数据"的站点降级使用。新增通道安全边界 (token 鉴权 + origin/SSRF 白名单 + 防伪造注入) 作为替代风险面。
  ③ 计划 v1.2 落地: §6 重写 (通道对比表 + 两路线成本/效果表 + 结论 + 安全边界 + 分发成本 + 待真机验证四问), §8 重写 (取数线程+令牌作废 ⇒ 端点线程只入队 + 主循环唯一写者, 新数据流图, 生命周期复用 `webui/server/lifecycle.py`), §2/§3/§5/§7/§9/§10/§11/§12/§13 相应修订, 新增 §14 变更记录; `doc-updated` 抬到 26-09-24-1808, 加 `doc-refs` 与本档 `Refs:` 形成双向认领。待拍板收敛为 4 条, 第 1 条即"是否接受装一个 unpacked 扩展"(不接受则走 CDP 备选, 接口不变)。
  ④ 结构自检: 标签配平 (section 14/14 · svg 1/1 · figure 1/1 · table 10/10 · pre 2/2), dark 口径保留; 浏览器实渲染 §7 配置块与 §8 新数据流图, 可读性正常。替换 §8 figure 时曾把旧 `<svg>`/`<figcaption>` 整块残留在文件里 (只数配对不看数量就发现不了), 已清除并复盘进 `pitfalls/docs/html-edit.md`。
  ⑤ 收尾: 档案回写 + activeContext 切片更新 + `kb.index` 重建 + 全量 `test.full` = **1207 passed + 1 skipped / 9.06s** (与单点 `testing/baseline.md` 的 1208 collected = 1207+1 一致, 本次只改文档未加测试, 无需改基线)。
  下一步: 等用户拍板 (取数通道 + 频度默认) → M0 收口 (download URL 形态 + 扩展通道四问实测)。
- **2026-09-24 18:33** — 用户: 「打包的扩展应该也能实现 unpacked 的功能吧? 不需要专用浏览器; 另外"未核实的种子"必须确认好边界, 首要是不要漏 HR, 其次是没有 HR 的要安全放行 —— 更新计划」。
  ① **扩展形态澄清** (§6): 扩展能力与分发形态**无关** —— unpacked / 打包 `.crx` / 商店版是同一套 manifest 与 API (`host_permissions` / `alarms` / `scripting` / `tabs`), 差别只在**怎么装、怎么更新**; 因此**不需要专用浏览器** (扩展就跑在日常 Chrome/Edge; "专用浏览器"只是 CDP 备选通道的代价)。id 固定改为「优先固定, 否则白名单放通 + **强制 token**」—— 真鉴权是 token, origin 白名单只是第二道 (设计不依赖"id 一定能固定"这个前提)。另补一句坦白: 商店版可自动更新会削弱路线 2 的"用户侧重装"摩擦, 但审核/发版周期与"解析脱离 pytest 体系"两条仍在, 结论不变。
  ② **「未核实」边界收口** (§9, 本版核心): 判定改**三态** —— 受管束 (`hr`) / **安全放行** (`verified_non_hr`) / 未核实 (`unknown`); 穷举未核实四类边界: 从未成功刷新 · **刷新不完备** (分页未到底/scope 失败/解析可疑/登录失效) · **新鲜度闸门** (`added_on` 晚于 `hr_refresh[site].last_success_ts` ⇒ 恒按受管束, **不可被 `unknown_policy` 绕过**) · 身份缺位 (infohash 未回填/站点未匹配)。
  ③ **放行只由「完整核实过且不在清单内」产生**, 并**粘性长期有效**(写 `hr_verified`) —— 这修正了 v1.2 的「索引过期回落 unknown」: 那会让通道静默期全站回到 HR, 正好把本功能的主要收益抵掉; 需要收紧的只有新种子, 交给闸门。两个方向的取舍与代价 (policy=not-hr 等于自愿放弃第一重保证) 写进 §9 取舍块。
  ④ **支撑件**: §4 加抓取范围 (**只抓 A 会把"已达标"的 HR 种子误放行** ⇒ 默认 `A+B+C`, D 视为放行) 与**覆盖证明**字段 (`hr_refresh`); §5 state 加 `hr_verified` / `hr_refresh` 并写明放行粘性; §7 配置加 `hr_page_scopes`、`unknown_policy` 注记; §10 风险由"误判方向"一行拆成「漏判 HR (最危险)」与「过度保护」两条; §12 新增 三态矩阵 / 放行粘性 / 覆盖证明 / scope 完整性 四组守阵。
  ⑤ 自检: 标签配平 (section 14/14 · table 11/11 · pre 3/3 · ol 2/2 · div 62/62), dark 口径保留; 浏览器实渲染 §9 三态表与边界块正常。过程中一次替换把 `old` 只写到 `</figure>` 导致旧块残留、又一次多删了 `<div class="colophon">` 开标签 —— 均由上面的配平机检当场拦下 (坑已在 `pitfalls/docs/html-edit.md`)。
  下一步: 等用户拍板 4 条 (第 1 条 = 是否接受装扩展) → M0 收口。
- **2026-09-24 18:56** — 用户两轮追问把方案推进到 **v1.4**: ①「二次下载/二次触发 HR 覆盖了吗」 ②「多下载客户端是常态, 需要谨慎考虑」 ③「同一账号只在一个实例启用 hr_check 不现实, 除非两个实例数据互通; 转移种子很普遍 (A 客户端下载 → B 客户端保种, B 的 downloaded=0 被当辅种); 所以网站数据是权威数据; 更新计划」。
  ① **自查发现的漏洞 (已被 v1.4 修掉)**: v1.3 引入的「放行粘性长期有效」在多客户端下不成立 —— 账号在**别的客户端**下载时本地零信号, 若清单未更新就会继续放行 ⇒ 漏 HR; 另 D 档(已免罪)被当永久有效也不对 (免罪只针对那一次下载)。
  ② **v1.4 的四个决定 (全部按"站点数据权威 + 多实例常态"重排)**:
  (a) **站点侧驱动判定** (§9): partial 站点「是否触发/是否达标」一律看站点侧 —— 清单命中即**触发** (不再看本地 `downloaded`), 达标看档位(B/剩余为 0)优先于本地值、站点字段缺失才降级回本地并标注来源。直接治「转移种子 ⇒ B 的 downloaded=0 被当辅种 ⇒ 不打标不保护」这条漏管; 「纯辅种不触发」保留给非 partial 站点。四消费点调用点仍零改动, 但**语义变了**, 必须用回归钉住。
  (b) **放行有效期取代永久粘性** (§5/§9): 有效期 = `min(下一次成功完整刷新, verified_ts + verified_ttl)`, `verified_ttl` 默认 = `refresh_interval`; 通道正常时每轮刷新自动续期 (收益不减), 只有长期静默才回落保守。下载锚点 (added_on/downloaded/completion_on/progress) **降为辅助**信号 (只提前作废本实例放行), 不再当作放行的充分条件。
  (c) **多实例账号级状态互通** (§5/§6/§7): `role: publisher` 集中核实 + 原子发布 `hr_snapshot.json` (同目录 tmp + os.replace), `consumer` 只读订阅 (不访问站点/不占配额/不写账号级状态), 快照陈旧 ⇒ 放行失效 + 告警; 配额/熔断/已取记录随发布方集中 ⇒ 双倍访问站点风险消失, 扩展只挂 publisher。「同一账号只在一个实例启用」这条不现实约束**取消**。
  (d) **身份判定改只读视图** (§9): 稳定引用 + 内容原子替换 (先例: 搜索索引整体替换引用, Web 线程并发只读安全), record 读时现算三态 + 锚点 —— 取代 v1.2 的「主循环预取写字段 + 置脏」(锚点漂移不置脏, 那种写法会漏更新)。
  ③ 计划改动面: §2/§5/§6/§7/§9/§10/§11/§12/§13 + §14 变更行, 封面与 doc-updated 抬到 26-09-24-1856; §10 新增「转移种子 / 别处下载 / 多实例 / 快照陈旧 / 站点值滞后」五条风险; §12 新增「转移种子 / 放行有效期与锚点 / 共享快照 / 降级路径」四组守阵, 并删掉已作废的「放行粘性」用例; §13 开放问题回到 5 条 (新增部署形态: 谁做 publisher、shared_dir 放哪)。
  ④ 自检: 标签配平 (section 14/14 · table 11/11 · pre 3/3 · ol 2/2 · li 63/63 · div 63/63 · tr 88/88), dark 口径保留; 浏览器实渲染 §5 state 模型块正常; 文中残留「粘性」字样只在 §14 历史行与"修正 v1.3"说明里 (有意保留)。
  下一步: 等用户拍板 5 条 (第 1 条=是否接受装扩展; 第 5 条=publisher 部署形态) → M0 收口。
- **2026-09-24 19:48** — 用户四条指令把方案推进到 **v1.5**: ①「纯辅种不触发似乎是一个 BUG, 非 partial 站点似乎也需要纳入该体系」 ②「hr_channel 收入 hr_check 中」 ③「publisher/consumer 不能覆盖多实例站点配置不同 / publisher 未启用或已退出的情形」 ④ 判定规则: **「带锁访问是安全的关键 (即使有 bug 也不会同时读); 另一实例有锁就等下一轮; 抓数据等几分钟可接受但不能卡主循环; 站点数据分单文件保存、锁也是单文件一个锁; 数据记有效期 —— 有效期内把另一实例的数据当作此次抓取的数据并消耗配额; 主循环不需要管这些, 只向另一线程申请数据更新种子状态」**。
  ① **多实例改为「共享站点数据 + 带锁访问」** (§5 重写): 账号级状态**不进 state_file**, 改为**站点分文件** `<shared_dir>/hr/<site>.json` + **唯一一把锁** `hr.lock` (filelock, 项目直接依赖, `infra/locking.py::SingleInstanceLock` 是现成样板); **取数线程持锁期间完成「读→判有效期→必要时抓→写→释放」全程** (连分钟级抓取也在锁内) ⇒ 即使代码有 bug 也不可能两个实例同时读/写/抓; 拿不到锁**直接等下一轮** (不排队、不重试轰炸); **有效期 = 「本轮已完成」**: 读到效期内的数据即当作本次抓取结果直接采用并**照样记一次配额** (按窗口键幂等) ⇒ 站点访问频率由数据有效期决定, 与实例数/谁抓的无关; **能力即角色**: 只有启用 `channel` 的实例会抓, 无通道实例只读; **写者心跳 + revision 回退自检**锁是否真的生效 (失效 ⇒ 告警 + 退化单实例只读); **合并式写入** (写前必读, 只补自己新增的) ⇒ 各实例站点配置不同也能各抓各的、互不覆盖。publisher/consumer 与 `shared_stale_warn` 随之删除。
  ② **线程模型改三分职责** (§8 重写 + 新图): 扩展 / 端点线程(只入队) / **取数线程**(持锁 + 解析 + 算 infohash + 发布不可变只读视图) / 主循环(只读视图 + state 唯一写者); 主循环读视图**零等待**(原子引用替换), 需要时只 `wake()` 取数线程(非阻塞) —— **绝不与取数线程同步握手** ⇒ 抓取再慢也卡不住 2s 节拍, 完全符合"不能卡主循环"。取数线程**不碰 state_file / 任务队列 / store** (新守阵)。
  ③ **「纯辅种不触发」缺口修掉 + 非 partial 纳入** (§9): 该判断用本地 `downloaded` 近似账号级义务 —— **真辅种**(从未下载过该 tid) 结论碰巧对, **转移/重加/换客户端的保种副本**(downloaded=0 但账号欠 HR) 则**漏管**。⇒ `mode: all` 语义从「全站按 HR + 本地下载量触发」升级为「站点侧驱动 + 未核实默认受管束」, 与 `partial` 的唯一差别只剩未核实的默认值; 真辅种改由「完整核实 + 清单未命中 ⇒ 安全放行」给出同一结论。**零静默变更**: 只有配了 `hr_check` 段的站点走新语义, 也不全局改 `check_hr_condition` (未接入站点行为不变)。
  ④ **`hr_channel` 并入 `hr_check.channel`** (§7): 已核对 `config/impact.py` —— 它只按**顶层键**查 `SECTION_LEVELS` (只有 `trackers` 有逐字段特判), 所以合并后 `channel.*`(端口/token) 会被误判成 L0 而实际需重挂端点 ⇒ 必须在计划里写明**补一张 `HR_CHECK_FIELD_LEVELS` 内部字段表**(仿 `TRACKER_FIELD_LEVELS`), 这是合并的唯一代价。新增 `shared_dir` / `lock_timeout`。
  ⑤ 自检: 标签配平 (section 14/14 · svg 1/1 · figure 1/1 · table 11/11 · pre 4/4 · div 64/64 · tr 94/94), dark 口径保留; 浏览器实渲染 §8 新数据流图正常。过程中又踩一次"替换片段只盖到起始标记 ⇒ 旧 SVG 整块残留"(已按 `pitfalls/docs/html-edit.md` 的计数机检当场拦下并清除)。
  下一步: 等用户拍板 5 条 (第 1 条=是否接受装扩展; 第 5 条=shared_dir 放哪 + 哪台启用 channel + 实测 filelock 互斥) → M0 收口。
- **2026-09-24 19:59** — 用户两条澄清把方案推进到 **v1.6**: ①「锁单文件一个锁」= **每个站点一个数据文件一把锁** (减小数据更新延迟) ②「HR 通常按小时甚至天计算, 没必要每 tick 更新, 且更新只在数据更新时发生」。
  ① **锁粒度改为站点** (§2/§5/§8 SVG/§10/§11/§12/§13 + 封面): `<shared_dir>/hr/<site>.lock`, 一站一锁 (不再全局 `hr.lock`) ⇒ 抓站点 A 不阻塞站点 B, **数据更新延迟随站点切分下降**; 同站点仍严格互斥 (「持锁期间完成读→判有效期→抓→写→释放」全程不变, 安全性不降级)。副作用是好的: **跨站点天然无覆盖问题** (每实例只写自己的站点文件), 原先的「合并式写入防抹掉其它站点」收窄为「站点内读-改-写」(仍防同站已有条目丢失)。§10 锁竞争风险行从「另一实例本轮不干活」改为「该站点本轮不干活, 其它站点不受影响」; §13 实测项不变 (仍是「filelock 在该共享目录上是否真互斥」)。
  ② **节奏与 tick 解耦 + 只在数据变化时更新** (§5/§7/§8/§12): HR 粒度是小时~天 ⇒ 取数线程按**自己的定时器** `poll_interval` (新配置键, 默认 `1M`) 自醒检查「哪个站点过期/需抓」, **不随主循环 2s tick 跑**; 视图只在**数据实质变化** (抓取成功 / 熔断进入退出 / 通道状态翻转) 时才抬 `revision` 并原子发布 ⇒ **主循环每 tick 只做一次版本号比较, `revision` 没变就零工作** (满足"更新只在数据更新时发生", 同时保住"抓取再慢也卡不住主循环")。**时间敏感判定在读取时现算** (`now` vs `expires_at`): 「过期」只是读时结论, 不为时间流逝重发布视图。§12 新增守阵: 版本未变 ⇒ 不更新任何 record / 读取时过期现算 / 锁粒度=站点 (并发两站可同时进) / 取数线程不随 tick 唤醒。
  ③ 自检: 标签配平 (section 14/14 · svg 1/1 · figure 1/1 · table 11/11 · pre 4/4 · li 65/65 · div 64/64 · tr 95/95), dark 口径保留; 全文 `hr.lock` 字样仅剩 §14 v1.5 历史行 (有意保留, 由 v1.6 行说明修正); 浏览器实渲染 §5「多实例: 共享站点数据」块正常。
  ④ 本档回写时踩到一条新坑: 改 `**Updated:**` 的替换片段顺手带上了下一行 `**Summary:**` 标签, 把标签静默删掉 (md 无边标签 ⇒ 机检不报)。已当场回读修回, 并按动作记进 `pitfalls/docs/md-edit.md` (同类坑的 md 版; 顺手把 `html-edit.md` 里过期的计数示例校正为现值)。收尾 `kb.index` + `kb.check` 过, 全量 **1224 passed + 1 skipped / 8.56s** (与单点 baseline 的 1225 collected 一致; 本轮只动文档未加测试, 不改基线)。
  下一步: 等用户拍板 5 条 (第 1 条=是否接受装扩展; 第 5 条=shared_dir 放哪 + 哪台启用 channel + 实测 filelock 互斥) → M0 收口。
- **2026-09-24 20:09** — 用户把 5 项前置决策全部拍板 (另追问「channel 不应该都启用吗」) ⇒ 计划升 **v1.7** (定稿, 无待拍板项)。
  ① 决策: **接受装扩展** (unpacked 自用即可, 不必上商店; CDP 专用 profile 降为应急不排期) / **首站 BTSchool**, 页面数据实施时由用户提供 (已有 `myhr.php` 样张可开工) / **频度按推荐** (90S·12 每时·60 每天, 站点级独立) / **`unknown_policy=hr` + `verified_ttl=refresh_interval`** / **`shared_dir` 默认数据目录** (多实例由用户决定是否改共享目录)。§13 由「开放问题」改写为**决策记录表 + M0 实测清单** (4 项实测: download URL 形态 / BTSchool scope 与分页判据 / 后台标签页观感 / 共享目录 filelock 互斥), 封面状态改「决策齐备 · 待开工」, M1 写明首站与页面样本来源。
  ② **channel 改为「推荐都启用」** (§5/§6/§10/§11/§12): 用户问得对 —— 抓取能力的硬边界不是「名额」而是**本机有没有装扩展的浏览器**: 端点只听 `127.0.0.1`, 浏览器只能连本机 loopback, 所以**跨机器**的实例配了也驱动不了 (只能只读共享数据); 反过来凡是本机有浏览器的实例都该开 ⇒ ① 消掉「唯一能抓的那台退出 ⇒ 抓取能力消失」的单点故障 ② 站点配在哪台哪台自己能抓 ③ 多通道**不会**双倍访问站点 (同站点靠锁 + 有效期复用, 谁先拿到锁谁抓, 另一个复用并记一次配额)。扩展侧因此新增**实例端点列表** (`[{name, endpoint, token}]`, `chrome.alarms` 逐个拉 ⇒ 一个浏览器可服务同机多实例); §10 新增「同机多实例端口/token 撞车」风险行 (端口被占启动即 fail-fast; token 打错 ⇒ 401)。
  ③ **多实例部署引导** (§7 新增 note): `shared_dir` 留空 = `<data_dir>/hr/` 为默认; 程序**无法可靠判断「我是不是多实例」** ⇒ **只引导不强求** (功能开启且留空时记一条 INFO 提示, 不阻断启动, 由用户决定是否配置); 配套用户文档 + `hr.once` 顺带打印实际路径与锁自检 (M2 加)。
  ④ 自检: 标签配平 (section 14/14 · svg 1/1 · figure 1/1 · table 12/12 · pre 4/4 · tr 104/104 · td 265/265 · th 37/37 · p 48/48 · strong 363/363 · code 394/394), dark 口径保留; 浏览器实渲染 §13 决策表 + M0 实测清单正常。过程中 3 处手误当场被拦: 替换时误插了一个反引号、两处「跨机器」写成「跳机器」、§14 v1.7 行因 `old` 漏了 `</strong>` 首次替换失败 (重做)。
  下一步: **M1 可开工** (首站 BTSchool 离线管道, 不需要浏览器); M0 四项实测可与 M1/M2 并行。
- **2026-09-24 20:15** — 用户: 「文档经过多轮修改可能已有飘移, 最后更新一下文档」⇒ 计划升 **v1.8 (纯文档, 无设计变更)**, 逐节回扫清漂移:
  ① <strong>删矛盾表</strong>: §6 里还留着 **v1.1 的 cookie 分层方案表** (A 手工导入「M1 落地」/ B CDP「M4 落地·推荐目标形态」/ C 扩展「备选不排期」) —— 与现行「扩展主选 / 手工导入否决 / CDP 不排期」**直接矛盾**, 整表删除 (同类对比已由上一张 v1.2 通道表覆盖)。
  ② <strong>旧路径</strong>: §1 `mixins/web_view.py` → `webui/views.py` (v1.2 已更正但 §1 漏改)。
  ③ <strong>旧落点</strong>: §3 `state.hr_index` → 站点文件里的 `hr_index` (v1.5 已把账号级状态移出 `state_file`)。
  ④ <strong>旧口径</strong>: §4 流量字段「决策以 qB 本地值为准」→ 站点侧优先、本地兜底 (§9 自 v1.4 起已是站点侧权威)。
  ⑤ <strong>旧待办/旧措辞</strong>: §5 bencode「M0 拍板」→ 已定自写; §11 M0 「依赖: 开放问题拍板」→ 依赖无、可与 M1/M2 并行; 实验脚本 ±25% 抖动加注「正式实现只向上」; §2「许可令牌整体作废」补明取数线程 v1.5 以新职责回来。
  ⑥ <strong>旧角色</strong>: §9 判定表删「consumer 侧」行 (publisher/consumer 已于 v1.5 删除) → 改「本实例无通道且共享数据已过期」。
  ⑦ <strong>mode 语义补齐</strong>: §7 配置注释补 `all` 三态语义; §9 硬约束与判定表把「partial ⇒ hr 段必填」放宽为 **`mode != off` ⇒ hr 段必填** (`all` 站点同需参数); §9 未核实态补「`mode: all` 恒受管束」; §2/§13「partial 站点」→「接入 `hr_check` 的站点」。
  ⑧ 导航/措辞: 目录与节注释 §13「开放问题」→「决策记录」; CSS 注释「粘性目录」→「吸顶目录」(避开已废弃的「放行粘性」撞词)。
  ⑨ 自检: 标签配平 (section 14/14 · table 11/11 (删表后 -1) · svg/figure/pre/ul/ol/li/div/tr 均配平 · td 248/248 · th 32/32), 目录锚点 14 = 节数 14, dark 口径保留; 浏览器实渲染 §6 (删表处) 与 §13 正常; 漂移关键词终扫: `web_view`/`state.hr_index`/`consumer`/`开放问题` 仅存于 §14 历史行 (有意保留)。
  下一步: 仍为 **M1 可开工** (首站 BTSchool); 本轮不动代码, 不建 issue。
- **2026-09-22 22:32** — 用户补充 HR 页字段与防重下要求 ⇒ 计划升 v1.1: 索引改 (站点, tid) 主键 + infohash 回填; 新增 `hr_downloaded` 永久已下载层与 `hr_dl_fails` 重试记账 (新配置键 `max_download_retries`); 反查键 (站点, infohash) 跨站独立; 进度字段「展示/交叉核对, 判定以 qB 本地值为准」; 原开放问题「页面是否给要求值」解决, 新增「进度字段用途边界」, 余 4 条待拍板。
