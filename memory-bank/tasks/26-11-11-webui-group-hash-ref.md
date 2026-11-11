# 26-11-11-webui-group-hash-ref — webui 组行 hash 引用式联合立项: 联合复验+grilling+计划入库

**Status:** In Progress
**Added:** 2026-11-11
**Updated:** 2026-11-11
**Summary:** 两件 perf issue(26-10-07-1420 组行 hash 引用式 / 26-10-08-0411 /api/state 全量轮瘦身)联合复验均仍复现 → grilling 五问拍板(D1-D5 全按推荐) → 联合计划 26-11-11-0630 入库(Open): 主线 C(hash 引用式)先行, S0 成本拆分置首步, B/A 转条件裁决; S0-S6 等显式开工, 两 issue 状态保持 Open
**Topics:** webui-group-hash-ref
**Refs:** memory-bank/plans/26-11-11-0630-plan-webui-group-hash-ref.html, memory-bank/issues/26-10-07-1420-perf-webui-group-row-hash-ref.html, memory-bank/issues/26-10-08-0411-perf-webui-api-state-pagination.html

## 本篇只回答

本档案只回答: 联合立项这轮做了什么、拍板了什么、下一步从哪进(S0 开工动作与认领时机)——方案本体与取舍的单点在计划 26-11-11-0630(§03/§05/§06), 不在此复述。

## 原始请求

1. 「memory-bank/issues/26-10-07-1420-perf-webui-group-row-hash-ref.html / memory-bank/issues/26-10-08-0411-perf-webui-api-state-pagination.html 两个issue联合复验, 然后grilling, 出一个计划」
2. grilling 五问批复: 「全按推荐」(D1-D5, 见计划 §06)

## 思考过程与决策

- **复验先行重锚**: 大文件拆分(deb1168d, 9 个后端大文件拆域子模块)后两件锚点整体迁移(views.py → views_group/views_row/views_common/views_episodes; runtime.py → runtime_views/runtime_common), 按符号+grep 重定位后逐一核对——两件均仍复现, 结构性事实无变化; 复验行+重锚已回写两 issue §04/§07, 状态保持 Open。
- **新事实进计划**: ①前端 g.members 消费面经全树 grep 盘点 60 处/17 文件(入池树 f07cc562 全树口径即 50 处/13 文件——代码消费面大体持平, 扩的是入池锚点只记 decorate.js 两段的审计覆盖); ②协议耦合: VIEW_ARRAYS group/show 视图须连带 torrents 数组否则 memberByHash 索引拼不出(shows 视图当年「连带 groups+singles」同款先例); ③静态 UI no-cache+ETag + 同仓同进程发布 → 旧标签页刷新即愈, 协议形状演进不背长期共存面。
- **grilling D1-D5(全按推荐, 2026-11-11)**: D1 单计划联合立项 / D2 C 先行(issue 2 §05 的「先拆分再选」降级为计划内 S0 步骤, B/A 转条件裁决 G1/G2) / D3 直接改形状+version-reload 小机制(协商参数/双字段是长期复杂度税) / D4 C1 组行整体 upsert(R8 不破; C2 只作实测触发条件项 G3) / D5 复验行当轮回写、认领留 S0 开工。
- **评审**: 分批只读评审 3 轮(轮 1 十条 minor7/nit3 → 全修; 轮 2 四条 minor2/nit2 → 全修; 轮 3 零发现出口), 累计 14 发现全过检全修, 零 blocker 零入池。主要修两类: grep 口径统一为全树(53/15 仅-JS 与 50/13 全树并置未标注 → 60/17 全树, 模板 tpl/ 2 文件 7 处计入验收口径)与推算自洽(去「19 键」改粗估、40/5 对应「≈8 倍」非「≈9 倍」); `_reduce_delta` 行号指针两处按实码重锚(窗外 :684-689 / 窗内 full 代 :691-692 / 缺行防御 :713-749, return 717/723/728/749)。

## 实现计划

计划单点: `memory-bank/plans/26-11-11-0630-plan-webui-group-hash-ref.html`(§04 实施步骤 S0-S6)。总体: S0 sim 实测成本拆分(开工动作 = 两 issue kb.status In Progress 补认领链)→ S1 后端 hash 引用式 → S2 前端物化接缝(spike 定缝, 验收 60 处消费位零 diff)→ S3 version-reload → S4 e2e → S5 复评与条件裁决(G1/G2/G3)→ S6 收尾(两 issue 翻 Done + webui.md 回写)。

## 子任务状态表

| 步 | 内容 | 状态 |
|---|---|---|
| 1 | 开工同步(a950f353→90764579) | Done(2026-11-11) |
| 2 | 联合复验(锚点重定位+现状核对+回写两 issue) | Done(2026-11-11) |
| 3 | grilling 五问拍板(D1-D5) | Done(2026-11-11) |
| 4 | 联合计划入库+双向补链+评审 3 轮零 actionable | Done(2026-11-11) |
| 5 | S0 成本构成实测拆分(计划 §04 首步) | Done(2026-11-11, @3000+@5000 双档实测完成, 见「S0 实测数字」; 两 issue 保持 In Progress 待 S1 开工) |
| 6 | S1-S6(计划 §04 余步) | Open |

## 进度日志

### R0 · 立档 (2026-11-11)

联合复验(两件仍复现)→ grilling D1-D5 全按推荐 → 计划 26-11-11-0630 入库(Open, doc-refs 与两 issue 双向闭环)→ 评审 3 轮(14 发现全修, 轮 3 零 actionable 出口)。零生产代码改动; 全部变更随本专题入库。

- 2026-11-11 07:03 联合复验两件仍复现(重锚回写)+grilling D1-D5 全按推荐+计划 26-11-11-0630 入库(Open)+评审 3 轮 14 发现全修零 actionable; S0-S6 等显式开工, 两 issue 保持 Open
- 2026-11-11 07:03 提交轮评审收口(共 5 轮, T=16/P=12, 修 12 过检全修, 零 blocker 零入池): 轮 2 的 4 条(minor2/nit2)**未过 review.check 即修——流程偏差**, 由轮 3 逐条回验闭合(行号指针/索引源原文/比值自洽均逐字核对), 后续轮次引文过检照 ⑤ 执行; 轮 4 微复评 2 nit(口径注记不齐)过检即修; 轮 5 终确认零发现出口。远端 tip 评审窗口推进至 0d88dc3d(本地缺对象「无法核实」), 齐平走 ship.commit 提交先行 rebase。

### R1 · S0 开工 + 环境与口径 (2026-11-11)

S0 开工动作完成: 两件 issue 经 kb.status 翻 **In Progress**(开工自检发现的既有产出, 主会话裁决接受续跑)。测量改道: 计划 §04 S0 原写 sim 沙箱, 用户拍板改道**测试 qB 真机轨 + 1KiB real-fake 假种子**(环境1 = 36595/36596, 免鉴权, connection_status=firewalled 合规; 开工时实例已在跑, cmdline 核对白名单镜像路径 `D:\Programs\qBittorrent-testing*` 通过, 起始空库)。

**库形与注入口径**(与在账 6.3 MiB@3000 的真实库形**不同构**, 数字对比时注意): 通用库 = 725 组 × 4 成员(全部归组、无 singles), 外加 1 个 100 成员抖动组 = 3000 种; 真实辅种库多为 2-3 成员小组 + 一定量 singles, 本库形是「全分组」的偏重形状(members 内嵌份额偏高, 对 hash 引用式收益评估偏保守)。

**假种子配方**(实测验证): 单文件种子, 同 savepath + 同文件名 + 同内容(确定性 payload), **piece_len 逐成员不同**(16384/32768/65536/131072 …)→ infohash 互异、全部可校验做种、落同一辅种组。组键 = `(path_normalize(save_path), (文件名,))`(grouping_mod.group_key_of); **多文件 + info.name 变体配方不可行**(qB 5.2.3 files API 的 name 含 info 根目录, file_map 不同组)。入库走 qB 原生 `skip_checking`(默认逐种子校验排队 ~1/s, 3000 种 = 45 分钟不可接受; skip 后 3000 种入库 40s)。announce = `http://127.0.0.1:59999/announce`(未监听口, 连接即拒零外网; **归组管线要求 tracker 配置匹配** —— 产品 qbmanager: 未匹配 tracker 的种子直接 continue 进不了 torrents_added 相位, 永不归组; 产品配置加 `trackers.S0FAKE.domains: [127.0.0.1, 192.168.1.122]` 后归组成立)。

**已踩坑(都是本轮新坑, 待收尾入 pitfalls)**:
1. 首同步风暴丢归组: 产品启动一次性发现 3000 新种子时, 每组**首个成员**(piece_len=16384)的 trackers_info 匹配失败(~24%)→ 落单 single 且**永不自愈**(post 相位只重归组已归组者)。修复 = 删净落单者 → 等两轮 sync → 逐个低速重加(20/s, 删加同轮内完成产品看不到变化, 必须跨轮)。**@5000 复核**: 修复后的库(全员自带 announce)重启归组 5s 一次到位零落单——丢归组的根因面是「成员缺 announce」而非风暴本身, 风暴只是放大器。
2. qB 默认入库逐种子校验吞吐 ~1/s(checking_memory_use 调 1024 无效), 3000 种校验 45 分钟 —— 大批量注入必须 skip_checking。
3. **批量注入脚本的「配方漂移」面**: @5000 首轮注入(inject_monster.py)相对已验证配方(inject.py add_group)漂移了三处——①没写 payload 数据文件(skip_checking 信任的是「文件已就位」, 没写文件 = 全组 missingFiles); ②除 0 号外 1999 成员没给 announce(死口 59999 也是 announce, 产品归组管线要求 tracker 域名匹配, 无 announce = 永不归组, prod.log 连刷 2000 行「未匹配 tracker 配置」); ③leech 等一个永远不存在的 seeder。三处全坏但脚本不报错(rc 路径只在成员数不达标时失败)。教训: 新注入变体必须复用 add_group(写文件+announce 面)而不是手搓 build 循环; 修复走 400/批 WebAPI delete(`deleteFiles` 字段, 不是 `delete_files`)→ inject.py 原配方重注入(同 infohash, 副实例 leech 无需重加)。
4. **后台 dev.run 实例外部停机三路全堵**(Windows): ①CTRL_C_EVENT 广播无效——后台任务链(cmd→uv→python)整树继承「忽略 Ctrl+C」旗标(SetConsoleCtrlHandler(NULL,TRUE) 可继承, 只豁免 CTRL_C); ②组定向 CTRL_C(GenerateConsoleCtrlEvent(0, pid))无效——产品非进程组长, 新组 CREATE_NEW_PROCESS_GROUP 默认禁 CTRL_C 同样绕不开; ③CTRL_BREAK 广播**可达但默认致命**——CPython 对 SIGBREAK 无 handler → 0xC000013A 控制台级终止, 产品的 SIGTERM→KeyboardInterrupt 优雅路径根本不经过(Windows os.kill(SIGTERM)=TerminateProcess 同样不通)。实测两次均硬停(丢失 ≤120s state 窗口, 测试态可弃; 锁由 OS 自动释放)。**结论: 经 `commands run dev.run` 后台起的实例, agent 外部只能控制台事件硬停; 要优雅停机需前台控制台直接 Ctrl+C, 或未来在 cli 装 SIGBREAK handler / webui 停机端点(产品面改动, 另行立项)。**

测量口径(逐项数字见下节, 随测随写):
- 服务端两段在真产品(develop HEAD 4de921a9, `scripts/dev_run.py` + `.work/s0/config.yml`, WEB 18211, 连 36595)实测: 序列化段 = Starlette JSONResponse 同参数 `json.dumps(ensure_ascii=False, allow_nan=False, separators=(",",":"))` 对真实回包回环复量(字节级相等已验证才采信); 构建段 = 全行置脏后的单请求重聚合(`_publish_partial_locked` 对全部行重建, S6 守阵语义 == 全量构建; 冷启动首请求另测, 含归组管线等待不计入请求)。
- 网络段 = curl `time_total - time_starttransfer`(同机回环)+ 同字节静态文件回环 GET 双口径互证。
- 前端两段 = Playwright(chromium)直连真产品页面: JSON.parse 段 = 页内同源 fetch 同一端点同字节串直接量 `JSON.parse`(前端走原生 `resp.json()` 不可拦截, 此为同解析器同字节的替代口径); 整表替换段 = 应用自带 `renderMs`(applyStateRows 赋值+多选交集, polling.js:443)+ 强制全量轮 window 内 longtask(渲染管线主线程占用)双口径。

- 2026-11-11 23:52 R1 收尾: @5000 档三件实测完成(①四段占比服务端+前端 / ②字节拆分 / ③monster 2000 成员抖动轮 delta 2.33 MB/轮——@3000 外推命中 <1%), 全部数字入下节; 上一棒坏 monster 注入(2000 missingFiles+无 announce)按坑 3 处置重注入; 归组 727 组 5s 一次到位零修复; 现场已按 real 规程处置(real.seed.rm 删净 5000+2 leech 连数据、伪 tracker 已随 m3 stop、产品实例控制台事件停机——外部优雅停机三路全堵见坑 4, 交主会话裁决是否立产品面停机出口的 issue); 测试 qB 实例(36595/36596)未动留原样; .work/s0 脚本与 results 证据保留(results/ 已复制 results_3000 存 @3000 原始证据)。
- 2026-11-12 P1 批次评审收口(**本地分支态**, 分面档 2 派遣串行): gate 预跑全绿(命中 6/执行 14 命令); review.pack 基 4de921a9, 可评 14 行 = 两 issue 状态面(任务档案为记账排除面), 基哈希 011a9b4203fd; 正确性面(状态两处一致/链行同构/计划口径吻合/HTML 完好)与安全面(改动行无敏感信息/红线未触/翻转无误改安全断言)两分面均**零发现**, T=0/P=0, 修 0 入池 0, 零 actionable 出口。

## S0 实测数字

环境: Windows 10 x64 / 环境1(36595 主 / 36596 副, qB 5.2.3, 免鉴权) / 产品 HEAD 4de921a9 / 测量日 2026-11-11。库形与口径见 R1 节。**粗估(计划 §02/§03)与实测并置**。

### 注入

| 项 | 粗估/计划 | 实测 @3000 | 实测 @5000 |
|---|---|---|---|
| 注入耗时(种子生成+入库, skip_checking) | — | **40s**(通用库 37s + 抖动组 2s) | **34s**(monster 2000 单轮 build+入库+settle; 另 2000 坏注入删除 ~2s, 见下注) |
| 实际种子数 | 3000 | 3000(726 组: 725×4 + 1×100; singles 0) | 5000(727 组: 725×4 + jit 100 + monster 2000; singles 0; 全部 stalledUP) |
| 产品首轮归组(启动→726 组齐) | — | ~90s(含 725 个首成员匹配失败修复重加) | **~25~30s**(启动→727 组齐一次到位, singles 0, 零修复; 全员自带 announce 后风暴未复现, 与 @3000 修复后重启行为一致) |

@5000 注入注: 上一棒 inject_monster.py 的 monster 注入**从根上坏**(①没写 payload 文件 → qB 2000 种全 missingFiles; ②2000 成员里 1999 个连 announce 都没给(只 0 号有)→ 产品「未匹配 tracker 配置」永不归组, prod.log 09:05:42 连刷 2000 行; ③leech 永远等不到 seeder, stalledDL 15h)——与 inject.py add_group 的已验证配方(先写数据文件+全员 DEAD_ANNOUNCE/0 号伪 tracker)不符。处置 = 2000 坏种全删(WebAPI deleteFiles=false, 400/批 ×5)→ `inject.py --monster 2000 --skip-check` 按原配方重注入(同 infohash, 副实例 leech 36cace89 无需重加)。重注入后 5000 全部 stalledUP、monster.bin 8 MiB payload 单文件服务全组。jit.bin leech 在本轮会话内自然下载完成(progress 1.0), jit 抖动源结束——①② 测在静库上, ③ 由 m3 起伪 tracker 激活 monster 传输链。

### ①全量轮四段占比 @3000(服务端三段; 库形 9.6 MiB 全量 / 3.8 MiB view=group)

| 段 | 口径 | full(缺省 4 数组) 9,597,644 B | view=group 3,800,557 B |
|---|---|---|---|
| 服务端·序列化(json.dumps) | 真实回包回环 `json.dumps(JSONResponse 同参数)`, 字节级相等已验证; n=20 median | **60.6ms**(57.7~65.1) | **23.6ms**(22.4~26.7) |
| 服务端·构建 | 全行置脏(pause-all)单请求重聚合(S6 语义 == 全量构建), 3 次采样 169/183/314ms 减稳态基线 64~72ms | **≈110~240ms(噪声大)** | 同左(按 view=group 量) |
| 网络传输 | 双口径: curl total−ttfb **22.2ms**(full)/6.4ms(group); 同字节静态文件回环 16.1ms@3.8MB(基线 1.0ms@2B) | ≈**15~22ms** | ≈**6~16ms** |
| 稳态全量轮墙钟(客户端, keep-alive) | n=10 median, 含以上全部+传输解码 | **125.4ms**(99~153) | **59.7ms**(45~63) |
| 稳态 TTFB(curl, 构建+序列化+首字节) | n=5 median | 72.3ms | 30.3ms |

单视图全量(view=torrent 5,669,319 B = 81.6ms / view=show 3,929,594 B = 69.7ms)同口径在账。粗估对照: 在账「3000 种一轮序列化+网络+解析 ≈63ms」(runtime.py:793 注释口径, 2026-09-19)——本轮稳态 view=group 墙钟 59.7ms 与同量级(库形不同不可逐位比)。

冷启动首请求(产品重启后第一发 /api/state, 真全量构建): TTFB **156.7ms** / total **187.8ms** @ 9,567,719 B; 第二/三发 TTFB 67.7/83.4ms(total 101.6/124.2ms)→ **冷启动全量构建增量 ≈80~90ms**(与上表 pause-all 重聚合口径 110~240ms 同量级, 互证)。本轮重启零匹配失败(726 组/3000 members 一次到位, 首同步风暴丢归组为间歇性)。

### ①全量轮四段占比 @3000(前端两段; Playwright chromium 直连真产品页面, prism/atlas 双皮肤)

| 段 | 口径 | view=group(3.8 MiB) | full(9.6 MiB) |
|---|---|---|---|
| 前端·JSON.parse | 页内同源 fetch 同字节串直接量 ×3 median(prism; atlas 3.3/7.4ms 同值) | **3.4ms** | **8.4ms** |
| 前端·fetch+原生 resp.json()(下载+解析合并, 不可拆) | vm.api() 打点, 3 轮 54~75ms | **65~75ms** | (未量, 按字节比 ≈1.6×) |
| 前端·赋值(applyStateRows+快照) | 打点 ×3 | **≈0.1ms**(纯引用替换) | 同 |
| 前端·整表替换 DOM(渲染管线) | 强制全量轮窗口 longtask: prism 59/80/57ms, atlas 69/82/59ms | **≈57~82ms/轮** | 同(视图渲染的是窗口行, 载荷变大不直接放大此段) |
| 前端·强制全量轮总耗时(vm.lastRid=null → await vm.refresh()) | ×5: prism 116~152ms / atlas 126~155ms | **≈118~152ms** | 同口径 |

前端分段读法: 一轮全量(view=group)客户端 ≈125~146ms = api 65~75(其中真 JSON.parse 仅 ≈3.4ms, 余为下载+缓冲)+渲染 flush 57~82+赋值 0.1。**JSON.parse 与赋值都不是大头, 渲染管线整表替换是前端最大段**; 服务端序列化(23.6ms)约为前端同字节解析(3.4ms)的 7 倍。粗估对照: 在账「3000 种 refresh 309ms」(2026-09-19, ui_harness 桩库形)——本轮真产品 118~152ms, 量级一致偏快(库形不同: 本库 726 组全分组 vs 桩库 2600 singles 平铺)。

### ②全量回包按数组字节拆分 @3000(字节级精确: 全量 re-dump 与服务器回包逐字节相等已验证)

总 9,592,173 B:

| 数组/段 | 字节 | 占比 |
|---|---|---|
| torrents(平铺, _seed_view) | **5,664,645 B** | **59.1%** |
| groups(组行, 内嵌 members) | **3,797,187 B** | **39.6%** |
| shows(list 0 行 + unrecognized 3000 hash = 129,028 B) | 129,028 B | 1.3% |
| status+rid+updated | 1,240 B | ~0% |
| singles | 2 B(0 行) | ~0% |
| envelope(键名/引号/逗号) | 71 B | ~0% |

**members 明细重复份额**(本库 3000 种全归组, 重复份额即最大):
- groups 行内嵌 members 明细 **3,501,707 B = 全量的 36.5%**(3,000 条, 平均 **1,167 B/条**——57 字段的 _member_view 实测字节; 本库 save_path/tracker 字段偏长, 真实库按行字段会略瘦);
- 同 hash 在 torrents 平铺的行 **5,661,644 B = 59.0%**(平铺行 = _member_view 超集, 是**另一份全量级副本**)——hash 引用式后这份保留, 内嵌那份塌成 hash 数组;
- groups 行去掉 members 后 286,767 B;
- **hash 引用式投影**(members→hash 数组, ≈46 B/成员): groups 段 3.80 MiB → ≈0.42 MiB, **全量收缩 ≈3.36 MB(35.1%)**; 若 view=group 单看: 组行明细不再内嵌(成员明细改由 torrents 桶承载), 3.8 MiB → ≈0.43 MiB 响应体 + torrents 桶按需连带(§03 计划预期「未必变小」在此库形下成立与否取决于是否连带 torrents: 连带则 ≈5.66+0.43≈6.1 MiB 反而略大——**计划 §03 对 view=group「不预写承诺」的判断被实测证实**)。
- G3 输入: jit 100 成员组行实测 **115,252 B**(其中 members 114,849 B)——计划粗估 ≈40 KB@100 成员, 实测为粗估的 **2.9 倍**(差异源 = 成员行字段实测字节 1,167 B/条 vs 粗估假设 ≈400 B/条, 结构判断不变、绝对量更差)。

### ③monster/jitter 组抖动轮 delta @3000(100 成员组, L2 真流量)

口径: 抖动组 0 号成员经伪 tracker(本机 38901, 固定口)与副实例(36596, dl 限速 1KiB/s)做 L2 真传输(8 MiB ≈ 2.3h 持续)→ 做种端 upspeed 逐秒抖动 → 组行每 tick 置脏。测量轮询 = `GET /api/state?rid=<ver>&view=group&delta=1` 1s 间隔 ×30 轮, 服务端 delta 归约产物(R1 时间线只存键/行内容现取自当前视图)。

| 项 | 计划粗估 | 实测(25/30 轮为抖动轮) |
|---|---|---|
| 抖动轮 delta 中**组行**字节 | ≈40 KB(≈8 倍于稳态) | **median 116,005 B**(115,571~116,007) |
| 抖动轮 delta 响应整体(组行+status 段+removed 桶) | — | **median 117,369 B**(多组同轮时 max 219,829) |
| 零变化轮对照(delta 空桶) | — | 5 轮, median 1,277 B(即恒回传 status 段; 在账稳态 delta 1,809 B 同量级) |
| delta 请求墙钟 | — | median 20ms(归约+序列化 117KB) |
| full 回退轮 | — | 5/30 轮(见口径注) |

口径注: ①抖动轮抖的只有 jit 组, 但其它组偶发进 delta(g0xxx 同轮出现)——死端口 announce 的 tracker 状态翻转会让**别的种子行**的 tracker/last_activity 类字段跟着变, 属本库形噪声, 真实库(活 tracker)更低; 脏组一多服务端按折叠阈值落**全量代**(R11 家族), 即 full 回退轮的来源之一。②**成员级抖动脏整条组行**的放大比实测: 116 KB/抖动轮 vs 稳态 delta 1.8 KB ≈ **65 倍**, 与计划「一个量级倒挂」判断方向一致、幅度更陡。③2000 成员 monster 的抖动轮 delta 在 @5000 节补测(按成员行字节线性外推 ≈2.3 MB/轮, 待实测验证)。

### ①全量轮四段占比 @5000(服务端三段; 库形 15.8 MiB 全量 / 6.1 MiB view=group; 测于静库, jit 传输已自然完成)

| 段 | 口径 | full(缺省 4 数组) 15,763,896 B | view=group 6,116,198 B | @3000 对照 |
|---|---|---|---|---|
| 服务端·序列化(json.dumps) | 真实回包回环, 字节级相等已验证; n=20 median | **103.0ms**(97.6~109.0) | **39.9ms**(38.5~42.1) | 60.6 / 23.6ms(≈1.7×, 与字节比 1.64× 同步) |
| 服务端·构建 | 全行置脏(pause-all)单请求重聚合, 3 次 289/296/273ms 减稳态基线 85~97ms | **≈180~210ms** | 同左(按 view=group 量) | ≈110~240ms(≈1.6×) |
| 网络传输 | curl total−ttfb 39.4ms(full)/17.6ms(group); 同字节静态回环 42.9ms@6.12MB(基线 1.1ms@2B, 抖 18~60ms) | ≈**35~43ms** | ≈**18~43ms** | 15~22 / 6~16ms |
| 稳态全量轮墙钟(客户端, keep-alive) | n=10 median | **186.6ms**(169~210) | **102.2ms**(91~107) | 125.4 / 59.7ms |
| 稳态 TTFB(curl, 构建+序列化+首字节) | n=5 median | 126.2ms | 53.8ms | 72.3 / 30.3ms |

单视图全量(view=torrent 9,436,375 B = 136.1ms / view=show 6,332,458 B = 104.2ms)。四段结构占比与 @3000 同构: 序列化与构建均近线性于字节量(1.64×字节 → 1.7×/1.6×耗时), 无超线性拐点。

### ①全量轮四段占比 @5000(前端两段; Playwright chromium 直连真产品页面, prism/atlas 双皮肤; 静库)

| 段 | 口径 | view=group(6.1 MiB) | full(15.8 MiB) | @3000 对照 |
|---|---|---|---|---|
| 前端·JSON.parse | 页内同源 fetch 同字节串直接量 ×3 median(prism; atlas 5.7/12.4ms 同值) | **5.4ms** | **13.4ms** | 3.4 / 8.4ms(≈1.6×, 与字节同步) |
| 前端·fetch+原生 resp.json()(下载+解析合并, m1_fe2 api_done ×3) | vm.api() 打点 | **105~157ms** | (未量) | 65~75ms(≈1.7×) |
| 前端·赋值(applyStateRows+快照) | 打点 ×3 | **≈0.1~0.2ms**(纯引用替换) | 同 | ≈0.1ms(不变) |
| 前端·整表替换 DOM(渲染管线) | longtask ×5: 162/139/175/138/145ms, ≈1.5 任务/轮 | **≈138~175ms/任务, flush ≈140~215ms/轮** | 同 | 57~82ms/轮(**≈2×, 超字节线性**——行数同 727, 涨在 5000 成员物化面的响应式消费) |
| 前端·强制全量轮总耗时(vm.lastRid=null → await vm.refresh()) | ×5: prism 285~427 / atlas 247~363 | **≈247~427ms** | 同口径 | 118~152ms(≈2.3×) |

前端分段读法 @5000: 一轮全量(view=group)客户端 ≈250~430ms = api 105~157(真 JSON.parse 仅 ≈5.4ms)+渲染 flush 140~215+赋值 0.1。渲染管线仍是最大段且**出现超字节线性增长**(组行数不变, 涨点在成员物化 5000 条后的响应式消费面——hash 引用式(S1/S2)把 members 从组行摘除后此段是直接受益者); JSON.parse/赋值依旧不是大头; 服务端序列化(39.9ms)与前端同字节解析(5.4ms)比值 ≈7.4 倍(与 @3000 的 7 倍一致)。

### ②全量回包按数组字节拆分 @5000(字节级精确: 全量 re-dump 与服务器回包逐字节相等已验证)

总 15,776,102 B:

| 数组/段 | 字节 | 占比 | @3000 占比 |
|---|---|---|---|
| torrents(平铺, _seed_view) | **9,439,972 B** | **59.8%** | 59.1% |
| groups(组行, 内嵌 members) | **6,119,784 B** | **38.8%** | 39.6% |
| shows(list 0 行 + unrecognized 5000 hash = 215,028 B) | 215,028 B | 1.4% | 1.3% |
| status+rid+updated | 1,245 B | ~0% | ~0% |
| singles | 2 B(0 行) | ~0% | ~0% |
| envelope(键名/引号/逗号) | 71 B | ~0% | ~0% |

**members 明细重复份额**(5000 种全归组):
- groups 行内嵌 members 明细 **5,823,151 B = 全量的 36.9%**(5,000 条, 平均 **1,165 B/条**——与 @3000 的 1,167 B/条一致, 单行成本不随规模变化);
- 同 hash 在 torrents 平铺的行 **9,434,971 B = 59.8%**(另一份全量级副本, hash 引用式后保留);
- groups 行去掉 members 后 287,908 B;
- **hash 引用式投影**(members→hash 数组 ≈46 B/成员): groups 段 6.12 MiB → ≈0.52 MiB(517,908 B), **全量收缩 ≈5.59 MB(35.5%)**(@3000 3.36 MB/35.1%——收缩**比例**与规模无关, 绝对值随成员数线性);
- view=group 单看: ≈0.52 MiB 响应体 + torrents 桶按需连带(连带则 ≈9.44+0.52≈9.95 MiB 反而略大)——@3000 的「计划 §03 不预写承诺被实测证实」在 @5000 同构成立;
- G3 输入: jit 100 成员组行实测 **115,145 B**(members 114,734 B)与 @3000 的 115,252/114,849 一致; monster 2000 成员组行字节见 ③@5000 组行实测。

### ③monster 2000 成员抖动轮 delta @5000(2000 成员组, L2 真流量; jit 传输已完成后测, 抖动源仅 monster)

口径同 @3000 ③: monster 0 号成员(36cace89, piece_len 16384)经伪 tracker(本机 192.168.1.122:38901, m3 现起)与副实例 leech(36596, 全局 dl 限速 1KiB/s)做 L2 真传输; `GET /api/state?rid=<ver>&view=group&delta=1` 1s ×30 轮。传输启动 ≤40s(强制 reannounce 3 次内)。

| 项 | @3000 外推(计划粗估) | 实测(23/30 轮为抖动轮) |
|---|---|---|
| 抖动轮 delta 中**组行**字节 | 116,005 B×20 ≈ **2.32 MB** | **median 2,333,851 B ≈ 2.33 MB**(2,332,075~2,333,855; **外推命中, 偏差 <1%**) |
| 抖动轮 delta 响应整体 | — | **median 2,335,213 B**(max 2,672,361 = 多组同轮) |
| 零变化轮对照(delta 空桶) | 1,277 B(@3000) | 7 轮, median **1,277 B**(与 @3000 同值) |
| delta 请求墙钟 | 20ms(117 KB) | **median 45ms**(归约+序列化 2.33 MB) |
| full 回退轮 | 5/30 轮 | 7/30 轮 |

口径注: ①组行 2,333,851 B ÷ 2000 成员 = **1,167 B/条**, 与 @3000 逐成员行字节完全一致——抖动轮 delta 成本**严格随组成员数线性**, monster 级组(2000)每轮抖动重传 2.33 MB 组行, 即稳态 delta(1.3 KB)的 **≈1800 倍**(@3000 100 成员组实测 65 倍, 放大比随组规模线性恶化)。②其它组偶发进 delta 的噪声与 @3000 同源(死端口 tracker 状态翻转)。③对 hash 引用式的含义: 抖动轮组行 2.33 MB 里 members 明细 ≈2.33 MB(组行本体仅 ≈0.16 MB)——引用式后抖动轮塌缩到 ≈0.16 MB+hash 数组 ≈92 KB ≈ **减 96%**。
