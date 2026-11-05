# 种子转移 3 修复后真机再验收: API 面 12 行 + UI 面 11 项全 PASS(23/0/0), TR-05 跳过形态 / TR-09 正斜杠命中 / api_key 通路 / UI-06c 两分支全部解锁补验通过

> 摘要: 计划 26-10-31-0306 上轮真机验收入池的三处修复(26-11-01-0334 已存在 409 误判 bug / 26-11-01-0334 path_map 分隔符归一化 / 26-11-01-0335 transfer 目标 api_key 通路)后的定点再验收, 并解锁上轮 BLOCKED 的 UI-06c 单组支「选中集优先/否则整组成员」两分支补验; 面向与上轮同: API 驱动 `/api/transfer/test`·`/api/transfer/run` + 浏览器 GUI 黑盒, 8 真实种子全程 paused 零触碰。
> 基线时间: 2026-11-01 03:1x–05:1x(手工两相位驱动, 非 real.suite —— 功能再验收而非 RM 切片, 用例为一次性驱动脚本, 落 tests-real/.work/transfer-accept/(results-api.md / results-ui.md, 已随收尾 real.seed.clean 清除), 断言口径与逐字证据全部誊入本切片)
> 基线 commit: 07b0719c(实测时刻 HEAD; 含 4 修复 commit: f556b11f 409探针兜底 / 26cdbe48 api_key后端 / 88a6aceb api_key前端编辑器 / f731de07 path_map分隔符归一化)
> hash 等价映射(2026-11-01 合流 rebase 改写, 内容零差异): 07b0719c->8a6b7b29, f556b11f->c0ecf7b9, 26cdbe48->4c014cff, 88a6aceb->07a90b1c, f731de07->59b3669a, fa0c2e11->b172f416; 本切片正文与 issue HTML 里引用的旧 hash 按此表换算
> 环境: 36595 v5.2.3 connected pid=41868(8 真实种子 paused) / 36596 v5.2.3 firewalled pid=39300(与上轮同 pid); 两相位驱动: 相位1 config95.yml(主连接=36595, web :39000)→相位2 config96.yml(主连接=36596, web :39001), 产品配置来源 tests-real/.work/transfer-accept/(非仓库根 config.yml); 源端=产品主连接(orchestrator 只读主连接), 上轮方向 36595→36596 走相位1、TR-新 方向 36596→36595 走相位2, 同一 targets 表

## 01 验收数字

**API 面 12 行(驱动脚本逐项断言, 全部走真双实例; 全 PASS):**

| 用例 | 内容 | 结果 |
|---|---|---|
| TR-01 | `/api/transfer/test` 四态: test-qb-96→ok truth.info="qBittorrent v5.2.3"; badcred-95→error「目标 badcred-95: 登录失败(检查用户名/密码)」; tr-stub→error「暂未实现: Transmission 目标暂不支持转移(当前版本仅支持 qBittorrent 目标)」; test-qb-95-key(api_key 纯 token)→ok truth.info="qBittorrent v5.2.3" | PASS×4 |
| TR-02 | 单选转移+字段落位: 目标 state=stoppedUP progress=1 save_path=R:\qbt-fake\tr\plain(原样) category=trcat02 tags="real-fake, trtag02"; 限速 up=131072/dl=262144(props), ratio=2.5/seedtime=3600(maindata —— qB 5.2.3 的 /properties 不含 ratio/seeding_time, 本轮实测事实); 目标数据文件在; 源任务已删除+源数据文件在(deleteFiles=false 不变量) | PASS |
| TR-03 | 多选批量 2 颗同批全成功(回执 summary success=2/skipped=0/failed=0), 目标落位 [True, True], 源残留 [False, False] | PASS |
| TR-04 | keep_source=true → 成功且回执注明「按勾选保留源种子」, 源保留 True | PASS |
| TR-05 | 已存在注入(36596 预置同 hash)→**跳过**: 「目标已存在(添加被拒且目标查得同 hash); 源已保留」, summary={success 0, skipped 1, failed 0}, 源保留 True —— 上轮 FAIL 的修复定点(§03-1) | PASS |
| TR-06 | 认证失败注入(badcred-95, 2 颗)→逐项「失败: 目标登录失败(检查用户名/密码); 源已保留」不中断批次, 源保留 [True, True] | PASS |
| TR-07 | stalledDL 预检拦截: 单发→跳过「下载管线态(stalledDL), 不可转移」源保留; 混批(stalledDL+好种)→summary success=1/skipped=1 不中断 | PASS |
| TR-08 | 未完成(stoppedDL progress 0)→自动降级注明「未完成, 已自动改为校验添加」, 目标 state=stoppedDL progress=0 save_path=R:\qbt-fake\tr\nodata(非跳检添加); 源任务已删除 | PASS |
| TR-09 | 路径映射: 反斜杠 from(回归)→状态=成功 目标 save_path=R:\qbt-fake\tr\bdst 前缀命中=True 数据可达=True 源删除=True; 正斜杠 from(定点)→R:\qbt-fake\tr\fdst 前缀命中=True 数据可达=True 源删除=True —— 上轮正斜杠静默不命中的修复定点(§03-2) | PASS×2 |
| TR-11 | 负向: 空 hashes→http=400「未提供任何 hash(转移批次不能为空)」; 未知 target→http=400「转移目标不存在: no-such-target(见配置键 web.transfer.targets)」 | PASS×2 |
| TR-热重载 | PUT /api/config 给 test-qb-96.path_map 追加第 3 条规则(rld→rldst)→http=200 {"applied": true, "changes": ["web"], "restart_required": []}, 下一跑目标 save_path=R:\qbt-fake\tr\rldst 新规则命中=True 数据可达=True | PASS |
| TR-新 | api_key 通路(36596 源→36595 目标, §03-3): 第 1 颗成功落位 newsrc(state=checkingResumeData, save_path=R:\qbt-fake\tr\newsrc), 目标数据文件在+源任务已删除(36596); 第 2 颗带预置字段全字段落位(category=trcatN2 tags="real-fake, trtagN2" ratio=1.5 seedtime=7200 up=262144 dl=131072, state=stoppedUP progress=1), 目标数据文件在+源任务已删除+源数据文件在 | PASS×2 |

**UI 面 11 行(浏览器 GUI 黑盒; 证据=当轮 DOM 快照/页面文案逐字誊录, 按既定口径不留截图):**

| 用例 | 内容 | 结果 |
|---|---|---|
| UI-01 | 种子列表渲染: 15 行=7 假+8 真实, tr07 行「0.0% 下载」其余全「100.0% 暂停」, 筛选计数「下载 1 / 暂停 14」; dark 主题渲染无异常无重叠截断 | PASS |
| UI-02 | 设置卡「种子转移」: 4 目标卡逐字在列(test-qb-96 / test-qb-95-key / badcred-95 / tr-stub); 测试连接四态回显(test-qb-96 与 test-qb-95-key 绿「连接成功: qBittorrent v5.2.3」/badcred-95 红「连接失败: 目标 badcred-95: 登录失败(检查用户名/密码)」/tr-stub「连接失败: 暂未实现: …」); 编辑器字段全落位(密码框 placeholder「已设置, 留空 = 不修改」/保存路径 checkbox [checked][disabled] 锁死必开/超级做种默认不勾/转移后状态单选「保持原状态」[checked]/映射区「有序 from → to 前缀替换, 首条命中生效…」+「+ 添加映射规则」); 未触改动「保存并应用」disabled=true 未写盘 | PASS |
| UI-02补充 | API Key 输入框(26-11-01-0335 前端验收点): test-qb-95-key 编辑器内「API Key」框存在 input.type=password(遮显同密码), 占位符逐字「已设置, 留空 = 不修改」, 值空不回显真值 | PASS |
| UI-03 | 单种子支全流程(tr06a→test-qb-96): 右键单种子支菜单全项 data-count="1" 含「转移到(has-sub)」submenu 4 目标; 四段式确认弹窗全文逐字(语义说明「转移只移动下载任务, 不动任何数据文件…」/目标+「将转移 1 个种子」/转移字段 6 项+保存路径恒转移/路径映射「3 条规则(有序前缀替换, 首条命中生效)…」+诚实预览「未命中映射: 1 个种子保存路径原样」/「仅本次保留源种子」); 结算 toast 逐字「转移结算(目标 test-qb-96): 成功 1, 跳过 0, 失败 0(源任务已删除, 数据文件未动)」+行消失; 后端回读 36596 落位(state=stoppedUP progress=1 save_path=plain 原样), 源/目标数据文件均在 | PASS |
| UI-04a | 重复 infohash→跳过形态(26-11-01-0334 修复定点复验): tr05 与 36596 预置 dup 夹具同 hash→toast 逐字「转移结算(目标 test-qb-96): 成功 0, 跳过 1, 失败 0; 目标已存在(添加被拒且目标查得同 hash); 源已保留」—— **修复后形态: 计入跳过, 非失败**; 行内图标 class=`ico sx sx-warn`(warn 非 error); 源保留(行仍在+后端回读源在) | PASS |
| UI-04b | 真失败注入(tr06b→badcred-95 错密码): toast 逐字「转移结算(目标 badcred-95): 成功 0, 跳过 0, 失败 1; 目标添加请求失败(身份认证失败次数过多，您的 IP 地址已被封禁。); 源已保留」—— 失败分类+诚实回传 qB 原文(瞬时 IP 封禁为短时, 事后直连 36595 API 200 恢复); 行内图标 class=`ico sx sx-error`; 源保留 | PASS |
| UI-05 | 预检拦截(tr07 stalledDL): 确认弹窗不开(open=false), toast 逐字「没有可转移的种子: 1 个全部被预检排除(下载管线态(stalledDL), 不可转移)」; tr07 行保留; 前端预检与后端状态门同口径 | PASS |
| UI-06a | 多选支(ctrl 点选 tr04+trnew): kind=multi data-count="2" 含「转移到」; 弹窗「将转移 2 个种子」; 混合批次逐项结算 toast 逐字「转移结算(目标 test-qb-96): 成功 1, 跳过 1, 失败 0; 目标已存在(添加被拒且目标查得同 hash); 源已保留」(trnew 成功行消失, tr04 因 36596 已有同 hash 被跳过且源保留行仍在) | PASS |
| UI-06b | 整集整剧支(追剧视图剧集行「超甜 -HHWEB」2 集合): 右键 kind=episode data-count="2" 菜单含「转移到」(只验存在未执行 —— 真实种子不转移红线) | PASS |
| UI-06c | 单组支两分支(解锁后补验): 解锁配方(RM04 口径)=grouping.enabled=true+新增 trackers 段 uifake(domains=["192.168.1.122"] 本机局域网 IP, announce=http://192.168.1.122:1/announce 死端口连接即 RST 零外连; 真实种子 tracker 域名均非本机 IP 不进管线); 同名同目录异 piece_len(16K/32K/64K)假种子 3 颗归同组, 组行 3 员+展开 detail 3 条 member-row。**分支B(无选中→整组成员)**: kind=group data-count="3"→弹窗「将转移 3 个种子」→toast 逐字「转移结算(目标 test-qb-96): 成功 3, 跳过 0, 失败 0(源任务已删除, 数据文件未动)」→组行消失(解散)。**分支A(选中集优先)**: 点选两组(共 3 员)右键仅 2 员的 ui6c2→菜单升级 kind=multi data-count="3"(选中集优先于整组成员)→toast「成功 3, 跳过 0, 失败 0(源任务已删除, 数据文件未动)」→两组均解散; 成员行半选时右键组行不升级 multi(count=整组), 与 selection.js `_ctxMulti`「组级 key 才计入 selGroups」判据一致, 非缺陷 | PASS×2 |
| UI-07 | 空目标态: PUT /api/config 全目标 enabled=false 热重载({"applied": true, "changes": ["web"], "restart_required": []})→「转移到」submenu 灰项 data-item=transfer-empty class=`ctx-item is-gated` 文案逐字「未配置目标, 去设置」; 复原 enabled=true 复核 4 目标恢复 | PASS |

**三态合计: PASS 23 / FAIL 0 / BLOCKED 0。**

## 02 不变量核验(计划 §01 设计底线六条, 本轮逐条实测)

| 底线 | 本轮实测 |
|---|---|
| 数据文件永不移动/删除 | TR-02 目标数据文件在(R:\qbt-fake\tr\plain\fake-256K-tr02.bin)且源数据文件在; TR-新 两颗目标数据文件在+第 2 颗源数据文件在; TR-09 两方向数据可达=True; UI-03 源/目标数据文件均在(R:\qbt-fake\tr\plain\fake-256K-tr06a.bin); 成功 toast 文案明示「数据文件未动」 |
| 不成功路径不碰源 | TR-05 跳过→源保留 True; TR-06 失败 2 颗→源保留 [True, True]; TR-07 跳过→源保留 True; UI-04a/04b 行保留+后端回读源在 |
| 未完成种子绝不跳检添加 | TR-08 自动降级注明「未完成, 已自动改为校验添加」, 目标 state=stoppedDL progress=0; UI-05 前端预检拦截与后端状态门同口径(tr07 stalledDL 弹窗不开) |
| 同机硬约束 | 目标=同机 36596/36595; save_path 原样(plain/nodata)与映射别名落点(bdst/fdst/rldst/newsrc)全部数据可达=True |
| 凭据只从服务端出网 | 目标凭据只在产品配置(tests-real/.work/transfer-accept/config95.yml/config96.yml); UI-02 API Key 框 type=password 值空不回显真值, 密码框「已设置, 留空 = 不修改」; 测试连接错误回显只给文案不暴露凭据 |
| 删源只删任务 | TR-02 源任务已删除 True 且源数据文件在 True; TR-09 两方向源删除=True 且数据可达=True; TR-新 源任务已删除(36596) True 且目标数据文件在; UI-03 后端回读源任务删除+源数据文件在 |

## 明细索引(外迁)

修复定点复核(上轮入池三处, 本轮逐一复验不复现) / 环境与收尾核净 等明细逐字外迁: [attachments/26-11-01-0516-real-torrent-transfer-r3.md](attachments/26-11-01-0516-real-torrent-transfer-r3.md)。

本文保留: 题头(摘要/基线时间/基线 commit) + 验收数字与判据; 数字与时间戳原样未改。
