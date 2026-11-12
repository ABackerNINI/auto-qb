# 26-11-11-webui-group-hash-ref — webui 组行 hash 引用式联合立项: 联合复验+grilling+计划入库

**Status:** In Progress
**Added:** 2026-11-11
**Updated:** 2026-11-11
**Summary:** 两件 perf issue(26-10-07-1420 组行 hash 引用式 / 26-10-08-0411 /api/state 全量轮瘦身)联合复验均仍复现 → grilling 五问拍板(D1-D5 全按推荐) → 联合计划 26-11-11-0630 入库(Open): 主线 C(hash 引用式)先行, S0 成本拆分置首步, B/A 转条件裁决; S0-S6 等显式开工, 两 issue 状态保持 Open
**Topics:** webui-group-hash-ref
**Refs:** memory-bank/plans/26-11-11-0630-plan-webui-group-hash-ref.html, memory-bank/issues/26-10-07-1420-perf-webui-group-row-hash-ref.html, memory-bank/issues/26-10-08-0411-perf-webui-api-state-pagination.html, memory-bank/issues/26-11-12-2345-chore-real-seed-clean-evidence-guard.html

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
| 6 | S1 后端 hash 引用式(协议+守阵同批) | Done(2026-11-11, 22a35b18 前身批 392 行, 评审轮 2 零 actionable) |
| 7 | S2 前端物化接缝(spike→ingestion 拷贝物化) | Done(2026-11-12, 本批; spike 裁决与已知边界见 R2 节) |
| 8 | S3-S6(计划 §04 余步) | Open |

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

### R2 · S2 前端物化接缝 (2026-11-12)

**S2a spike 裁决(polling.js 注释指路单点)**: 缝 = **ingestion 物化**(三入口: applyStateRows 全量/delta + auth.js bootstrap), 产**成员行浅拷贝**而非计划 §03 原推荐的 canonical 行引用 —— 偏差动因: 乐观链 `_forEachRow`(commands_optimistic.js:30-34/:64-72)prev 采集「后命中覆盖前命中」隐含「同 hash 多命中各为独立对象」, 别名化下第二命中读到已打补丁值, `op.prev` 被污染 → 失败回滚静默失效; 浅拷贝与 S1 前服务端成员字典同构, 52 处消费位零波及、补丁链代码零改动。delta 桶序 torrents/singles 先于 groups 合并 ⇒ 物化时索引恒新鲜; full 分支索引直接吃载荷数组。缺项防御: 保留原 hash 字符串不产 undefined + `_rematQueue` 登记、后续轮 `_rematDrain` 补物化(后端「成员脏⇒同代组脏」不变式下常规不可达, 纯兜底)。评审 P3 轮 1 修 1 major: `_rematDrain` 调用点从赋值前挪到赋值后(原位登记行未进 `this.groups`, `cur.includes` 恒 false, 队列当轮空转)。

**已知语义边界(评审确认接受)**: `_snapshotTruth` 组员源换成本地物化拷贝后, 误判窗口 = 组脏(他员变化)+ 该组另有成员 pending —— 提前撤 hold 且 op.prev 同窗污染; **成功路径观感不变, 失败/停滞路径补丁值停留至该成员下次变化或下一次全量轮(长期滞留, 非一轮弹回)**。绿色向守阵 = node 电池 `test_r4_truth_snapshot_materialized_members`(8 断言; 场景 1 平铺桶只放 A + 守门断言钉「快照确实经组员拷贝取到 B」, 判别面真落在物化源上)。三入口接线覆盖落点(P5 评审修复后如实, 旧表述「留 S4 e2e 覆盖」只对 delta 桶序一入口成立): delta 桶序(torrents/singles 先于 groups 合并)+ 重组后 members 仍物化对象形 = S4 e2e 乐观用例(组员拷贝补丁不触字段 `state` == 平铺真值行的新鲜度档 + 暂停真值轮 delta.groups 形状钉, e2e/group-hash-ref.spec.mjs); 待补清账 drain 赋值后时序(P3 修复点)= node 电池 `test_r4_remat_drain_after_assign_two_beat`(两拍缺项 delta, drain 挪回赋值前即红); auth.js bootstrap 同缝 = 同电池静态钉(`_materializeGroupRows` 调用先于 `this.groups` 赋值, 跨度比较钉顺序)+ 节点级声明 —— e2e 桩恒免鉴权(ui_harness skip_local_verify), 登录快照轮 e2e 不可达, 不由 e2e 覆盖; 「先物化后赋值」的响应式时序半边无直接断言面(物化挪到赋值后产物相同, 仅 Vue 代理旁路差异), 由 polling.js 注释声明 + e2e 产物面(组行 members 物化形)间接覆盖。

**数字**: 行数口径(git numstat)polling.js +113/-2 → 评审修复后 +117/-2; auth.js +5; 电池 +105/-5 → 评审三轮修复后 +115/-5; 测试面(定向 e2e 8 红全转绿 / S2b 补跑 25 spec 全绿 / test.quick)数字只记本批提交信息, 收口立基线切片后统一改「见 kb.baseline」, 不在此手抄。g.members 消费位 52 处/17 文件零 diff(全树 grep 口径)。

### R3 · S5a 复评取数第一段(@3000 档) (2026-11-12)

S5a 开工自检过(HEAD==d7e6bc23 树净; 36595/36596 WebAPI 清点 0/0 与 S0 收尾删净一致, 无不明种子; 本地分支无远端, 开工同步不适用且任务禁 git 状态变更)。测量全程零生产代码改动, 脚本适配全在 gitignored scratch 面。三件实测数字见「S5 复评数字」节(随测随写)。

- 环境重建: inject.py --skip-check 43s(725×4+jit100 全 stalledUP, 副实例 jit leech 带 1KiB/s 限速)→ 产品 dev.run 后台起(.work/s0/config.yml, WEB 18211, state 起始空态 90B)→ 首轮归组 <30s 到 726 组; 首成员缺 announce 落单 725(坑 1 照旧)→ fix_singles.py 3000(尾判 5000 参数化)删净重加 → 726 组 3000 members 0 singles。
- 实测: ①四段(服务端 steady/curl/serialize/network/build + 前端 m1_fe/m1_fe2) ②字节拆分 m2_payload(全量 -35.3%, S0 投影 35.1% 偏差 0.2pp 命中; G1 粗估扩展段净可裁 ≈7.4% 全量) ③抖动轮 m3_delta(组行 median 4,711 B, 24.6× 塌缩, 预期 5-6 KB 量级命中)。
- 脚本适配面: m1_fe/m1_fe2 等待条件 5000→3000; fix_singles 尾判参数化; **m2_payload 认新形状**(members=hash 数组、S0 投影块退役改实测对照、新增 G1 逐字段字节表); m3_delta 补量 delta.torrents 桶; 三测量脚本 OUT 改道 **results/s5/**。
- **踩坑(待收尾入 pitfalls)**: 复用脚本先跑后改, m1_perf steady 首跑在 OUT 改道前执行, **S0 @5000 的 5 个 steady_*.json(results/)被覆盖**不可恢复——@5000 steady 原始轮次数组丢失, 关键数字(median/min/max/字节)在档案 @5000 表已誊写未失; 其余 @5000 证据(build/serialize/payload_split/delta_*/fe*_5000)mtime 未动。教训: 复用既有测量脚本, 第一步核对输出路径指向(或先 mv 旧证据), 再跑。
- 现场处置: real.seed.rm 删净(36595 逐删 3000 + 36596 leech 1, 连数据, R:/qbt-fake/s0 只余空目录壳)→ 产品经 dev.port-kill 停(核归属: PID cmdline = dev_run.py + s0 config, python 监听者免 --yes; 坑 4 外部优雅停机三路全堵照旧)→ 伪 tracker 已随 m3 脚本退出停止(38901 无监听)→ state.json 回 90B 空态; 测试 qB 36595/36596 本体未动留原样。证据: results/s5/ 11 件(steady×5/serialize/build/curl 在 build.json/payload_split/fe_results/fe2_prism/delta_jit), S0 的 results/ 与 results_3000/ 未再动。S5b 接手面: @5000+monster 档同口径复评 + G1/G2/G3 裁决回填(③ 注有 monster 外推 0.09 MB/轮待验证; inject.py --monster 2000 配方见坑 3)。
- 2026-11-12 09:5x S5b(@5000+monster 档)完成: 开工自检过(HEAD==d7e6bc23, 树恰 1 修改件=本档案)→ 36595/36596 WebAPI 清点 0/0(与 S5a 删净一致)→ 注入 86s(通用库 40+jit 3+monster 2000 入库 43, 全 stalledUP, 副 2 leech)→ 产品 dev.run 后台起, 首轮归组 <40s 到 727 组(零修复; monster/jit 0 号自带 announce)+ 725 库组首成员落单(坑 1 照旧)→ fix_singles.py 5000 删净重加 → 727 组 5000 members 0 singles。三件实测(①四段/②字节拆分/③monster 抖动轮真值 86,430 B, 外推命中 <0.1%)全部入「S5 复评数字」节 @5000 小节; 输出路径事故教训照办: 脚本 OUT 复用前逐个核对改道 **results/s5/5000/**(11 件), results/ 与 results_3000/ 与 results/s5/(S5a)均未动; **G3 STOP 条件命中**(monster 86,430 B > 64 KB 且 21/30 轮频发, 合成极端库形)→ 按指令不裁决不回填计划, 对照分析与三个选项入「裁决状态」节交主会话问用户; G1/G2 数据面(7.7% vs 30% 阈值; 82~110ms vs 300ms 阈值)同节在案。现场处置照 S5a 规程(见下条)。
- 2026-11-12 现场处置收尾(本轮; 补上一棒被配额切断欠写的「下条」, 只清场零测量): 到达态即净——36595/36596 两测试实例**已停机**(netstat 36595/36596/18211(产品 WEB 口, .work/s0/webui/config.yml 口径)/38901(伪 tracker)全无监听; 产品与伪 tracker 上一棒已停, 无进程归属可核; 本机仅用户自有 qB 两实例 Program Files/qBittorrent-2, 非测试镜像)。种子面复核走全规程: real.up 拉起两实例 → WebAPI 双口径(seed.list + /api/v2/torrents/info)**均 0 种** → real.seed.rm --all --yes 两实例 0 命中(幂等, 连数据口径) → real.down 优雅停回; **终态: 两实例停机 0 种**。R:/qbt-fake 仅余空目录壳(lib 下 725 个 g* 空目录 + jit/jit-leech/monster/monster-leech 顶层 4 壳, 0 文件), 随 real.seed.clean --yes 清壳回空。**新事故如实记**: real.seed.clean 真实语义是**整目录清空 tests-real/.work**(不止种子残留; 「已清空」即其正常输出), 本轮误判为「只扫种子残留」连带清掉 **.work/s0 全树**——S0 原始证据(results/ @5000 余件 + results_3000/ 全部)、S5a results/s5/ 11 件、S5b results/s5/5000/ 11 件、.work 复用脚本(inject/m1/m2/m3/fix_singles 等)与 s0 state.json(90B 空态)全部丢失; 该面 gitignored、shutil 直删不进回收站, git 不可恢复, memory-bank 无副本。**蒸馏数字不受影响**(「S0 实测数字」「S5 复评数字」两节誊写在案), 但全部原始测量证据自此不可复核; 89 行旧事故(results/ 顶层 steady_*.json 被 S5a 覆盖)随目录一并消失。教训(与 89 行并案待入 pitfalls): **跑 real.seed.clean 前必须先确认 .work 内无待留证据——它清的是整树, 不是「种子残留」**。红线未触: auto-qb-data/(空)/config.yml 未动, git 树仍恰 1 修改件(本档案)。

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

## S5 复评数字(hash 引用式后; S5a @3000 档, 2026-11-12)

环境: 与 S0 严格同构(同机 / qB 5.2.3 环境1 36595/36596 / 同库形 725×4+jit100 / 免鉴权), 产品 HEAD **d7e6bc23**(feat/webui-group-hash-ref, S1-S4 已入库) vs S0 的 4de921a9。测量脚本原样复用 .work/s0(m1_perf/m1_fe/m1_fe2/m2_payload/m3_delta), 输出改道 **results/s5/**(results/=S0 @5000 证据, results_3000/=S0 @3000 证据, 均未动)。产品配置同 .work/s0/config.yml(WEB 18211 连 36595, S0FAKE)。

### 注入与环境

| 项 | S0 @3000 | S5 @3000(改造后) |
|---|---|---|
| 注入耗时(skip_checking) | 40s | **43s**(同配方; 副实例 jit leech 已带 1KiB/s 限速) |
| 产品首轮归组 | ~90s(含 725 首成员修复重加) | **<30s 到 726 组**; 首成员缺 announce 落单 725(坑 1 照旧)→ fix_singles.py 3000 删净重加(带 announce)→ 726 组 3000 members 0 singles 一次到位 |
| 状态文件起始 | 空态 | 空态(.work/s0/webui/state.json 90 B, S0 收尾已清) |

### ①全量轮四段占比 @3000(服务端三段; 改造后库形 **6.21 MiB 全量 / 6.08 MiB view=group**; S0 9.60/3.80 MiB)

| 段 | 口径 | full 6,212,229 B | view=group 6,083,195 B | S0 @3000 对照 |
|---|---|---|---|---|
| 服务端·序列化(json.dumps) | 真实回包回环, 字节级相等已验证; n=20 median | **42.9ms**(37.2~48.4) | **42.0ms**(34.9~49.2) | 60.6ms@9.6MB / 23.6ms@3.8MB —— **每字节耗时同带(≈6.9µs/KB)**, 序列化成本跟随连带后的实际字节 |
| 服务端·构建 | pause-all 重聚合 3 次 187/203/222ms 减稳态基线 90~111ms | ≈**90~130ms** | 同左 | ≈110~240ms(噪声大)—— 同量级 |
| 网络传输 | curl transfer(total−ttfb) / 同字节静态回环 43.8ms@6.08MB(基线 1.1ms) | ≈**13.4ms**(curl) | ≈**20.7ms**(curl) | 22.2 / 6.4ms(curl); 16.1ms@3.8MB(静态) |
| 稳态全量轮墙钟(客户端, keep-alive) | n=10 median | **81.8ms**(64.1~96.7) | **80.9ms**(68.0~89.0) | 125.4ms@9.6MB / 59.7ms@3.8MB —— **full 收缩 35%(125.4→81.8ms)**; view=group 因连带 torrents 变大(59.7→80.9ms), S0 投影「连带则 ≈6.1 MiB 反而略大」被实测证实 |
| 稳态 TTFB(curl, n=5 median) | | 48.3ms | 53.8ms | 72.3 / 30.3ms |
| 单视图全量 | | view=torrent 73.4ms@5,659,419 B / view=show 77.8ms@6,212,235 B | | 81.6@5.67MB / 69.7@3.93MB —— show 视图连带源从 groups+singles 改为 torrents(索引源 = singles∪torrents), 3.93→6.21 MB |

### ①全量轮四段占比 @3000(前端两段; Playwright chromium 直连真产品页面, prism/atlas 双皮肤)

| 段 | 口径 | view=group(6.08 MiB) | full(6.21 MiB) | S0 对照 |
|---|---|---|---|---|
| 前端·JSON.parse | 页内同源 fetch 同字节串直接量 ×3 median | **4.7ms** | 4.4~5.8ms | 3.4ms@3.8MB / 8.4ms@9.6MB —— 每字节同带(≈0.9µs/KB) |
| 前端·fetch+原生 resp.json()(下载+解析合并) | m1_fe2 api_done ×3 | **91~148ms** | (未量) | 65~75ms@3.8MB —— 1.6× 字节同步 |
| 前端·赋值(applyStateRows+快照) | 打点 ×3 | **6.0~8.0ms** | 同 | **≈0.1ms** —— **+6~8ms 为 S2 物化接缝的新增 ingestion 成本**(全量轮 3000 成员浅拷贝物化+索引), 绝对量仍小 |
| 前端·整表替换 DOM(渲染管线) | longtask: prism 86/87ms, atlas 76/89/81ms; flush(raf2−apply)68~90ms | **≈76~89ms/任务** | 同 | 57~82ms/轮 —— 轻微上浮(~15%), 组行数同 726 |
| 前端·强制全量轮总耗时(vm.lastRid=null → await vm.refresh()) | ×5 | prism 166~267 / atlas 166~301 | 同口径 | 118~152ms —— 涨在 api 下载段(字节 1.6×), 渲染段仅微涨 |

前端分段读法: 一轮全量(view=group)客户端 ≈166~300ms = api 91~148(真 JSON.parse 仅 ≈4.7ms)+渲染 flush 68~90+赋值 6~8。渲染管线仍是前端最大段; 服务端序列化(42.0ms)与前端同字节解析(4.7ms)比值 ≈8.9 倍(S0 为 7 倍)。

### ②全量回包按数组字节拆分 @3000(改造后; 字节级精确: 全量 re-dump 与服务器回包逐字节相等已验证)

总 **6,206,929 B**(S0: 9,592,173 B → **-3,385,244 B = -35.3%**; S0 投影 -3.36 MB/-35.1%, **偏差 0.2pp 命中**):

| 数组/段 | 字节 | 占比 | S0 @3000 占比 |
|---|---|---|---|
| torrents(平铺, _seed_view) | **5,651,379 B** | **91.0%** | 59.1%(5,664,645 B)—— 平铺段字节几乎不变(±0.2%), 占比上升纯因 groups 塌缩 |
| groups(聚合行+hash 数组) | **425,205 B** | **6.9%** | 39.6%(3,797,187 B)—— **塌缩 8.9×**: 聚合行 286,766 B(与 S0「组行去掉 members 后 286,767 B」逐字节吻合)+ hash 数组 129,726 B(3,000 条, **43 B/条**; S0 投影假设 ≈46 B/条) |
| shows(list 0 行 + unrecognized 3000 hash) | 129,028 B | 2.1% | 1.3%(同值) |
| status+rid+updated | 1,244 B | ~0% | ~0% |
| singles | 2 B(0 行) | ~0% | ~0% |
| envelope(键名/引号/逗号) | 71 B | ~0% | ~0% |

- **G3 输入(新形状)**: jit 100 成员组行整行 **4,703 B**(members hash 数组 4,301 B)—— S0 同行 115,252 B(members 114,849 B), **塌缩 24.5×**。
- **G1 裁决输入(「按视图再裁一层字段集」可省份额, 粗估)**: flat 行(_seed_view, 90 字段)逐字段字节求和 —— **_member_view 段之外的平铺扩展段(33 字段, views_row.py:97-138)合计 504,624 B = 平铺段 8.9% / 全量 8.1%**。粗估口径: 消费面按静态 grep 判定 —— 组页成员明细表 DETAIL_COLUMNS(app.js:86)与选择摘要/乐观补丁/筛选面只吃 _member_view 段; 扩展段中非抽屉引用仅 ctx 菜单/快捷键的 auto_tmm/force_start/super_seeding 三布尔(45,000 B), 其余扩展字段引用全在抽屉面(drawer_rows/drawer_tpl/drawer.js), 而抽屉数据源 = `/api/torrents/{hash}` 按需全字段(drawer_store.js detail.url; drawer_rows `d = this.drawer.detail` 缺 detail 渲染空、不回退轮询行)⇒ **view=group 场景净可裁 ≈459,624 B ≈ 平铺段 8.1% / 全量 7.4%**(把三布尔也裁掉的上界为 8.1%/8.9%); 扩展段大头 = content_path 122,100 + comment 117,000(合计占扩展段 47%)。注: 本库形 save_path/tracker/occ_key 偏长, 真实库逐字段字节分布会略异; _member_view 段内部进一步裁剪未展开, 本数字只回答「扩展段整层」量级。

### ③monster/jitter 组抖动轮 delta @3000(改造后; 100 成员组, L2 真流量)

口径同 S0 @3000 ③: jit 0 号成员(802ebce9)经伪 tracker(本机 38901, m3 现起)与副实例(36596, dl 限速 1KiB/s)做 L2 真传输 → 做种端 upspeed 逐秒抖动; `GET /api/state?rid=<ver>&view=group&delta=1` 1s ×30 轮。传输启动 <40s(2 次 announce 内)。

| 项 | S0 @3000 | S5 @3000(改造后) |
|---|---|---|
| 抖动轮 | 25/30 轮 | 23/30 轮 |
| 抖动轮 delta 中**组行**字节 | median **116,005 B**(115,571~116,007) | median **4,711 B**(4,710~4,713)—— **塌缩 24.6×**; 预期「≈5-6 KB 量级(聚合+hash 列表)」命中 |
| 抖动成员明细行 | (内嵌在组行 members 里, 114,849 B) | median **1,897 B** —— 明细行改经 **delta.torrents 桶**回传(只抖动的那一条), 组行不再背全组成员明细 |
| 抖动轮 delta 响应整体 | median 117,369 B(max 219,829 = 多组同轮) | median **7,995 B**(max 57,900 = 多组同轮)—— **塌缩 14.7×** |
| 零变化轮对照(delta 空桶) | 5 轮, median 1,277 B | 7 轮, median **1,277 B**(与 S0 同值) |
| delta 请求墙钟 | median 20ms | median 19ms |
| full 回退轮 | 5/30 轮 | 7/30 轮 |
| 其它组偶发进 delta 噪声 | g0xxx 同轮出现(死端口 announce 的 tracker 状态翻转) | 同源(g0236/g0194/g0057/g047 等同轮出现, 噪声组行各 ≈5 KB) |

口径注: ①组行 4,711 B = 聚合行 ≈411 B + 100 条 hash 数组 ≈4,300 B(43 B/条, 与 ② 实测一致)—— 抖动轮组行成本从「随成员数 ×1,167 B/条明细」变成「随成员数 ×43 B/条 hash」,**放大比从 ≈65 倍(组行/稳态 delta)塌到 ≈6.3 倍(整轮 7,995 vs 零变化 1,277)**。②monster 2000 成员外推: 组行 ≈0.41 KB 聚合 + 2000×43 B ≈ 86 KB ≈ **0.09 MB/轮**(S0 实测 2.33 MB → 预期塌缩 ≈25×), 待 S5b @5000 实测验证。③多组同轮时整体被噪声组行(各 ≈5 KB)抬高, 真实库(活 tracker)该噪声更低。

### ①全量轮四段占比 @5000(S5b 2026-11-12, 改造后服务端三段; 库形 **9.70 MiB 全量 / 9.50 MiB view=group**; S0 15.8/6.1 MiB)

| 段 | 口径 | full 10,172,980 B | view=group 9,957,943 B | S0 @5000 对照 |
|---|---|---|---|---|
| 服务端·序列化(json.dumps) | 真实回包回环, 字节级相等已验证; n=20 median | **61.7ms**(60.0~64.3) | **60.7ms**(57.7~66.4) | 103.0ms@15.8MB / 39.9ms@6.1MB —— 每字节同带(≈6.1µs/KB), 序列化跟随连带后实际字节 |
| 服务端·构建 | pause-all 重聚合 3 次 326/278/311ms 减稳态基线 137~185ms | ≈**140~190ms** | 同左 | ≈180~210ms —— 同量级 |
| 网络传输 | curl transfer 38.6ms(full)/49.8ms(group); 同字节静态回环 64.0ms@9.96MB(基线 0.9ms) | ≈**39~64ms** | ≈**50~64ms** | 35~43 / 18~43ms; 42.9ms@6.12MB |
| 稳态全量轮墙钟(客户端, keep-alive) | n=10 median | **129.8ms**(102.9~167.8) | **136.2ms**(117.7~163.2) | 186.6ms@15.8MB / 102.2ms@6.1MB —— **full 收缩 30%(186.6→129.8ms)**; view=group 因连带 torrents 变大(102.2→136.2ms), S0 投影「连带则 ≈9.95 MiB 反而略大」逐位命中(实测 9.96 MiB) |
| 稳态 TTFB(curl, n=5 median) | | 73.9ms | 71.8ms | 126.2 / 53.8ms |
| 单视图全量 | | view=torrent 136.2ms@9,447,746 B / view=show 147.6ms@10,172,980 B | | 136.1@9.44MB / 104.2@6.33MB |

### ①全量轮四段占比 @5000(S5b 2026-11-12, 改造后前端两段; Playwright chromium 直连真产品页面, prism/atlas 双皮肤)

| 段 | 口径 | view=group(9.50 MiB) | full(9.70 MiB) | S0 @5000 对照 |
|---|---|---|---|---|
| 前端·JSON.parse | 页内同源 fetch 同字节串直接量 ×3 median(prism; atlas 7.0/7.0ms 同值) | **6.8ms** | **7.2ms** | 5.4ms@6.1MB / 13.4ms@15.8MB —— 每字节同带 |
| 前端·fetch+原生 resp.json()(下载+解析合并, m1_fe2 api_done ×3) | vm.api() 打点 | **115~146ms** | (未量) | 105~157ms@6.1MB —— 同带 |
| 前端·赋值(applyStateRows+物化+快照) | 打点 ×3 | **4.3~9.2ms** | 同 | ≈0.1~0.2ms —— **+4~9ms 为 S2 物化接缝 ingestion 成本**(5000 成员浅拷贝), 绝对量仍小 |
| 前端·整表替换 DOM(渲染管线) | longtask: prism [98,100], atlas [110,100,102]; m1_fe2 6 task 82~109ms; flush(raf2−api)83~86ms | **≈82~110ms/任务, flush ≈83~86ms/轮** | 同 | **138~175ms/任务, flush 140~215ms/轮** —— **降 ≈30~40%**(组行数同 727, S0 超字节线性涨点=5000 成员物化面的响应式消费, hash 引用式后组行不再背明细, 直接受益) |
| 前端·强制全量轮总耗时(vm.lastRid=null → await vm.refresh()) | ×5: prism 223~334 / atlas 218~265 | **≈218~334ms** | 同口径 | 247~427ms |

前端分段读法 @5000(改造后): 一轮全量(view=group)客户端 ≈218~334ms = api 115~146(真 JSON.parse 仅 ≈6.8ms)+渲染 flush 83~86+赋值 4~9。**S0 @5000 的前端最大段(整表替换 138~175ms/任务)降到 ≈82~110ms/任务**, G2 的「首屏整表替换」输入因此从 S0 超字节线性面回落; 渲染管线仍是前端最大段。

### ②全量回包按数组字节拆分 @5000(S5b 2026-11-12, 改造后; 字节级精确: 全量 re-dump 与服务器回包逐字节相等已验证)

总 **10,170,310 B**(S0 @5000: 15,776,102 B → **-5,605,792 B = -35.5%**; S0 @5000 投影 -5.59 MB/-35.5%, **偏差 0.0pp 逐位命中**):

| 数组/段 | 字节 | 占比 | S0 @5000 占比 |
|---|---|---|---|
| torrents(平铺, _seed_view) | **9,442,336 B** | **92.8%** | 59.8%(9,439,972 B)—— 平铺段字节几乎不变(+0.03%), 占比上升纯因 groups 塌缩 |
| groups(聚合行+hash 数组) | **511,628 B** | **5.0%** | 38.8%(6,119,784 B)—— **塌缩 12.0×**: 聚合行 287,176 B(S0 组行去 members 后 287,908 B, 同量级)+ hash 数组 215,727 B(5,000 条, **43 B/条**, 与 @3000 一致) |
| shows(list 0 行 + unrecognized 5000 hash) | 215,028 B | 2.1% | 1.4%(同值) |
| status+rid+updated | 1,245 B | ~0% | ~0% |
| singles | 2 B(0 行) | ~0% | ~0% |
| envelope(键名/引号/逗号) | 71 B | ~0% | ~0% |

- **G3 输入(新形状)**: jit 100 成员组行整行 **4,703 B**(hash 数组 4,301 B)与 @3000 改造后同值; **monster 2000 成员组行整行 86,422 B**(hash 数组 86,001 B)—— S0 同行抖动轮 delta 2,333,851 B, **塌缩 27.0×**; 86,422 B 已超 64 KB 阈值, ③ 抖动轮真值待测(合成极端库形, 裁决面交主会话)。
- **G1 裁决输入 @5000**(「按视图再裁一层字段集」可省份额, 粗估, 口径同 S5a): seed_view 扩展段(33 字段, views_row.py:97-138)合计 **855,127 B = 平铺段 9.1% / 全量 8.4%**; 消费面静态 grep 判定同 S5a(组页成员明细/选择摘要/乐观补丁只吃 _member_view 段, 非抽屉引用仅 ctx 菜单/快捷键的 auto_tmm/force_start/super_seeding 三布尔 75,000 B)⇒ **view=group 场景净可裁 ≈780,127 B ≈ 平铺段 8.3% / 全量 7.7%**(上界 8.4%/9.1%); 扩展段大头 = content_path 202,100 + comment 195,000(合计占扩展段 46%, @3000 为 47%, 同构)。与 S5a @3000 的 7.4% 同带 —— **@5000 档未出现与 @3000 明显不同的数字**。

### ③monster 2000 成员抖动轮 delta @5000(S5b 2026-11-12, 改造后真值; 2000 成员组, L2 真流量)

口径同 S0 @5000 ③: monster 0 号成员(36cace89)经伪 tracker(192.168.1.122:38901, m3 现起)与副实例 leech(36596, dl 限速 1KiB/s)L2 真传输; `GET /api/state?rid=<ver>&view=group&delta=1` 1s ×30 轮。传输启动 <40s。**与 S0 口径的一处对齐: 副实例 jit leech 测前暂停**(S0 @5000 时 jit 传输已自然完成=抖动源仅 monster; 本轮 jit 传输未完成, 不暂停会当第二噪声源)——实测零噪声组: 30 轮进 delta 的组仅 monster.bin 一组, 比 S0/S5a 的 g0xxx 噪声面干净。

| 项 | S0 @5000(改造前) | S5 @5000(改造后) | S5a @3000 外推 |
|---|---|---|---|
| 抖动轮 | 23/30 轮 | **21/30 轮** | — |
| 抖动轮 delta 中**组行**字节 | median **2,333,851 B ≈ 2.33 MB** | median **86,430 B**(86,429~86,431)—— **塌缩 27.0×** | ≈86 KB(聚合 ≈0.41 KB + 2000×43 B)—— **外推命中, 偏差 <0.1%**(与 ② 全量组行 86,422 B 差 8 B, 同行字段实时值抖动) |
| 抖动成员明细行 | (内嵌在组行 members 里) | median **1,927 B** —— 经 delta.torrents 桶回传(只抖动那一条) | — |
| 抖动轮 delta 响应整体 | median 2,335,213 B | median **89,744 B**(max 93,652)—— **-96.2%** | ≈0.09 MB/轮 |
| 零变化轮对照 | 7 轮, median 1,277 B | 9 轮, median **1,277 B**(与 S0/S5a 同值) | — |
| delta 请求墙钟 | median 45ms | median **7ms** | — |
| full 回退轮 | 7/30 轮 | 9/30 轮(monster 每 tick 置脏, 折叠阈值(R11 家族)落全量代更频) | — |
| 进 delta 的其它组噪声 | g0xxx 同轮出现 | **无**(jit leech 已暂停, 零噪声组) | g0xxx 噪声(各 ≈5 KB) |

口径注: ①组行 86,430 B = 聚合行 ≈430 B + 2000 条 hash 数组 86,001 B(43 B/条)—— 抖动轮组行成本随成员数 ×43 B/条, 与 @3000 ②③ 逐位一致; C1 已把合成极端库形(2000 成员组)的抖动轮成本从 2.33 MB 压到 0.087 MB。②**86,430 B > 64 KB(65,536 B)阈值 —— G3 的机械判据在合成极端库形上命中**; 按任务指令这是 STOP 条件: 不自行裁决、不回填计划 §05/§06, 对照分析交主会话问用户(见下节「裁决状态」)。

### 裁决状态(G3 STOP, 2026-11-12): 三点数据在案, 裁决与计划回填待主会话问用户

三档实测(@3000 见 S5a 节, @5000 见上三节)对 §05 三阈值的面:

- **G1(B 按需字段, 阈值: 裁剪可省 >30%)**: 数据 = @3000 净可裁 ≈7.4% 全量(S5a)、@5000 ≈7.7% 全量(本轮)—— 两档同带, 均**远低于阈值**, 机械判据方向为不触发。
- **G2(A 分页, 阈值: 前端首屏整表替换 >300ms @3000)**: 数据 = 改造后 @3000 整表替换(渲染管线 longtask)76~89ms/任务(S5a)、@5000 82~110ms/任务(本轮)—— **远低于阈值**, 机械判据方向为不触发; 且 S0 @5000 的超字节线性面(138~175ms/任务)已被 C1 回落到 ≈82~110ms。
- **G3(C2, 阈值: 抖动轮 delta >64 KB 且频发)**: **STOP 条件命中** —— monster 2000 成员组(合成极端库形)实测抖动轮组行 86,430 B > 64 KB 且 21/30 轮频发。按任务指令不自行裁决、不回填计划 §05/§06, 以下对照交主会话问用户:
  1. **实测 vs 阈值**: 86,430 B 超 64 KB 约 32%; 但超阈完全来自 members hash 数组 86,001 B(43 B/条 × 2000)—— 组行聚合部分仅 ≈430 B。
  2. **合成极端 vs 真实库形**: monster 2000 是 S0 特意构造的最坏情形(验证线性外推用), 非真实观察; 在账库形注记(R1 节)= 真实辅种库多为 **2-3 成员小组 + 一定量 singles**, 在账真实库总量 3000 种 —— 2000 成员单组意味着**全库 2/3 挤进一个组**, 在账资料(计划/两 issue/本档案)无任何真实库组规模分布记录支持这种组形存在。@100 成员组(合成但更接近可想象上限)实测仅 4,711 B = 阈值的 1/14。
  3. **阈值算术(改造后形状)**: 抖动轮组行 ≈430 B 聚合 + 43 B/成员, 加抖动成员行(torrents 桶)≈1.9 KB ⇒ **>64 KB 需要单组 ≳1,470 成员**; 「频发」在真实库 = 该组有持续传输的成员。⇒ G3 是否真实可达, 取决于**真实生产库是否存在 ≥≈1500 成员且高频抖动的组** —— 本轮红线禁触 `auto-qb-data/`, 无法只读采样核实, 需用户拍板: ①用户提供/授权采样真实库组规模分布后再裁; ②或按「合成极端不立判」维持 §05 默认不立项(100 成员组实测 4.7 KB 远低于阈值, C1 已拿走 27.0× 塌缩收益); ③或按机械判据字面触发 C2 追加分期。
  4. 若将来真实库确实出现千五级成员组: C2 剩余收益 = 抖动轮再省 hash 数组(86 KB 量级/轮), 协议手术面 = R8 再评估 + 重建判定 + 「S6==全量」守阵重做(计划 §05 G3 行原文)。

**回填面**: 计划 §05 裁决收口段已回填(2026-11-12, 用户拍板): **G1 不立项**(净可裁 @3000 ≈7.4% / @5000 ≈7.7%, 远低 30% 阈值)/ **G2 不立项**(整表替换 @3000 76~89ms / @5000 82~110ms, 远低 300ms 阈值, S0 超字节线性面已被 C1 回落)/ **G3 不立项(用户拍板「维持默认不立项」)** —— 合成极端库形字面命中(86,430 B > 64 KB 且频发)但合成但接近可想象上限的 100 成员组实测 4,711 B 远低阈值、C1 已拿走 27.0×、阈值算术需单组 ≳1,470 成员且高频抖动; **再议触发条件 = 真实生产库出现 ≥≈1,500 成员且高频抖动的组**。另: real.seed.clean 事故(整清 .work 连测量证据)经用户拍板「教训入 pitfalls + 工具保护改动入池 issue」—— pitfalls 随 S6 收尾, issue 随本批入池。
