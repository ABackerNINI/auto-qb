# Active Context — 当前焦点

> Memory Bank 核心文件之一: 回答"现在正在做什么 / 上次做到哪 / 下一步从哪继续"。**每次会话开始先读本文件。**
> 稳定事实在 projectbrief / productContext / systemPatterns / techContext 与各主题文档; 计划与完成状态在 [progress.md](progress.md); 本文件只放**易变的会话级状态**。
> 维护纪律 (完整规程见 [memory-bank skill](../.agents/skills/memory-bank/SKILL.md)): ①每次会话收尾更新本文件, 已完成条目沉淀到 [progress.md](progress.md) 或主题文档后**删除** — 本文件只放易变状态; ②命中立档阈值的任务在 [tasks/](tasks/_index.md) 立档并同步索引; ③**禁止**在本文件追加长流水账纪要 (会淹没真正的当前焦点)。

**最后更新**: 2026-09-21 (**最新: 两个 WEB UI 缺陷已修并验证, 未提交** ——
  ① **种子页筛选器无数据**: 筛选弹层选项一律遍历 `groups` 算, 而种子页按视图分片**不回 groups**
  ⇒ 改「取数面单点」`facetRows` + `_facetOptions`(计数口径随视图走: 组视图=组数, 种子页=种子数);
  ② **辅种组暂停整组后颜色 灰→绿→灰**: 真值(直查)比我们自己的同步快照新 ≤1.5s, 原先在真值事件里
  `delete pendingOps` ⇒ 期间一次陈旧快照就把行打回命令前的做种绿; 改成真值只改覆盖的值、
  **不结束覆盖**(收尾判据仍是"服务端快照同意")。单测 **1142 passed**(基线不变);
  冒烟 ok 68/**2**(2 条均为**既有**失败, 已定性: `80~1000ms` 下界随 D2"回执即撤"过时)/ error 68/0 / hang 8/0。
  详见 [tasks/26-09-21-webui-filter-data-and-color-flicker.md](tasks/26-09-21-webui-filter-data-and-color-flicker.md)
  与 [progress.md](progress.md)「已实现」首条) ——
  其前一条状态: 列设置双轨模型重设计已入库 `e5c31d1`(意图/生效分轨 + v5 按页子树 + 单一持久化漏斗), 剩真机走查;
  再往前: 辅种页「部分暂停部分做种中」状态色回归已修并入库 `ec368fb`(`seeding:3 / paused:4`, 两张表一起
  改回做种优先 + 顺序守阵); 真机语料抓取/脱敏/离线回放 W0–W6 全部落地(残留 ~13 条观感项);
  乐观 UI「撤下」已定案并推送 `4df80dc`, 两者均剩真机走查确认。

## 正在进行

- **🆕 列设置重置 · 双轨模型重设计 —— 已实施完毕(未提交), 剩真机走查**: 用户定性"修复了很多次,
  急需重新设计, 简化模型, 从根本上杜绝"; 计划
  [docs/plans/26-09-21-1551-column-prefs-intent-redesign-plan.html](../docs/plans/26-09-21-1551-column-prefs-intent-redesign-plan.html),
  D1(升 v5+迁移)/D2(fit=回全自动)/D3(origin 空存储提示)已按推荐全部落地。
  **新模型**: 存储只存意图(`colHidden/colOrder/colW`, `w=null`=全自动页), 生效宽度 `colWidths` 由
  `recomputeEffective()` 按窗口现算**绝不落盘**; 唯一漏斗 `persistPage(page)`(全仓唯一 setItem,
  v5 按页子树 RMW); `migrateLegacyToV5` 内存迁移(v4 固化页保宽 / 非固化页污染 px 清零); manual 标志删除;
  六个意图动作统一走漏斗, 拖宽/双击自适应以 merge 保隐藏列 px(封掉 S4 的 11→10 通道)。
  **验证**: 静态守阵 1 换 4(唯一 setItem / 只收意图 / 标志位不得复活 / 键链必挂迁移), 红验 4/4;
  冒烟双 UI 64 项失败 2 项(均既有「P0-3 乐观态落回真值」, 与列偏好无关), 新 4 场景(异视口互不吞+F3 /
  全自动页不落px / 隐藏列保宽 / v4→v5 迁移)双 UI 全 PASS; 全量 **1142 passed**(39.88s, Windows)。
  **真机走查清单**: ①固定地址双标签各改列宽/显隐互刷不丢 ②固化页隐藏一列→拖宽→再显示 px 原样回来
  ③"适应窗口"=回全自动(继续随窗口自适应, 不再固化快照 —— 行为变化点) ④换地址打开出 origin 提示(一次)。
  ⚠ 用户实例是 `D:\Projects\auto-qb` 的 editable install —— **本 clone 未提交前不会同步过去**, 需提交推送后拉取。

- **真机语料抓取 · 脱敏 · 离线回放 —— W0 已出数, W1/W2 已完成(未提交), 下一步 W3**: 计划
  [docs/plans/26-09-21-0024-qb-corpus-capture-replay-plan.html](../docs/plans/26-09-21-0024-qb-corpus-capture-replay-plan.html)
  (v1→v3 原地修订) + 审查报告
  [docs/plans/26-09-21-0257-qb-corpus-capture-replay-plan-review.html](../docs/plans/26-09-21-0257-qb-corpus-capture-replay-plan-review.html)。
  **目标**: 把 `sim_qb.py` 的种子来源从"人造合成"换成"真实 qB 抓取 + 脱敏 + 回放"; 合成档保留为对照档。
  **五项已拍板(2026-09-21 03:33)**: ①磁盘事实来源**默认 mock** —— 进程内 FS mock 注入 `sim_autoqb.py`
  (在 `from auto_qb.cli import main` 之前), **不物化任何文件**; FS 入口实测只有 4 个调用点
  (`grouping.py:239/244` · `checking.py:26/29` · `env.py:228` `exists` · `env.py:219` `disk_used`)
  ②归组 key 公式**抽成 `src/` 纯函数** `group_key_of(save_path, file_map)` ——
  **本计划唯一一处 `src/` 改动, 用户已放行**, 纯抽取零行为变更 + 配守阵单测
  ③语料位置改**参数**(`--out` / `--source=corpus:<dir>`, 不写死) ④回放 root 也改参数
  (`--root` / `--fs-root`) ⑤**一并消化 issue 26-09-20-2145**。

  ### W0 真机实测已出数(2026-09-21 04:0x, 真机 = 本机 127.0.0.1:16585, qB v5.2.3 / webapi 2.15.1 / 87 种子)
  - **全量抓取耗时**: 174 请求(files+trackers) 顺序 **207 ms**(1.19 ms/请求, p95 3.91); 并发 4 → 151 ms;
    `maindata(rid=0)` 15.6 ms / 0.20 MB。⇒ 真机上"10 000 次请求 ≈ 8 分钟"的担忧**不成立**(按此速率 5000 种子约 10 s)。
  - **第二 session 不干扰增量流** ✅: 不同 session 各自持有**独立 rid 序列**(3 轮验证: B 打 `rid=0` 后
    A 的后续请求仍是增量、rid 单调)。**同一 session 内**用过时 rid 才会退化成全量 ⇒ T1 走独立 session 的方案安全。
  - **100 ms 采样对真机负载: 判否不成立** ✅ —— 实测 10.00 req/s, rtt mean 1.14 ms / p95 2.20 / max 2.86,
    **0 次 > 100 ms**; 做种吞吐无退化。⇒ perf 档 100 ms **保留**, 不必退到 250–500 ms。
  - **磁盘探测**: 11457 文件 / **1303 ms**(0.114 ms/文件); `temp_path_enabled=False` ⇒ temp path 覆盖问题本机**不适用**。
  - **真实缺文件样本极充足**: exists 1784 / **missing 9673**(全部在 R: 盘、progress=0 的 stoppedDL 等);
    `.!qB` 后缀 **2 个**(真实下载中文件)。⇒ D4 天然样本不用人为注入。
  - **归组规模**: 87 种子 → **63 组**(54 单成员 + 9 多成员, 最大 12 成员), 组内 {路径:大小} 冲突 0。
  - **全局限速两来源单位一致** ✅: `transfer/uploadLimit == server_state.up_rate_limit`(1048576 / 5242880)。
  - **`maindata` 滞后校准**: 命令后 maindata 反映延迟 mean **733 ms** / median 751(131–1414, n=12),
    与 issue 2145 观测的 1362 ms 同量级; **但 Δ(maindata − torrents/info) = +1 ms ⇒ 两者同步**。
    ⇒ issue 2145 那条"info 比 maindata 新"的**前提在真机上不成立**; 真实滞后是 qB 命令处理延迟(两端共享)。
    W3 的模型据此改成两个独立旋钮(见 pitfalls 与任务档案), 并保留计划要求的红验。
  - **待用户确认**: R 盘(Arsenal Image Mounter 虚拟盘)是否镜像文件后端(持久)。

  ### W3 已实施(本轮)
  - 新增 `scripts/sim_fsmock.py`(进程内 FS mock: 拦 `os.path.exists`/`os.path.getsize`/`shutil.disk_usage`,
    **按路径前缀限定**、剥 `\\?\` + 大小写不敏感、时间源归播放器)+ `tests/test_sim_corpus.py`(17 条)。
  - `sim_qb.py` 语料档: `--source=corpus:<dir>` / `--fs-mode` / `--fs-root` / `--command-latency-ms` /
    `--maindata-lag-ms` / `--replay-speed` / `--latency-mode`; 补齐 `sync/torrentPeers` / `torrents/export` /
    `torrents/pieceHashes` / `_fsmock/state` 四个路由; `CorpusSource` / `merge_window` / `piece_hashes_of` /
    `corpus_tracker_section`(按语料派生 tracker 段, 否则站点匹配全落空)。
  - `sim_run.py` 透传 + 用**环境变量**注入 FS mock(不占 argv)。`sim_autoqb.py` 在 `import auto_qb.cli` **之前**装 mock。
  - **端到端**: `sim_run.py --source=corpus:<dir>` → **verdict OK**(87 种子 / 15 帧 / 63 组 / 0 物化文件,
    17 轮 sync、漂移 0.578s、0 traceback); mock 表 = 1239 exists / 9441 missing(与 W0 真机一致)。
  - 守阵: **`CORPUS.fs_mock_coverage` 静态守阵 + 红验**(换 pathlib 必红)、**两层状态模型红验**(滞后全 0 ⇒ 两端同刻)。
  - **修掉两个真 bug**: ①`disk.json.gz` 内层相对路径从未脱敏(隐私 P0, 真实资源名漏进语料)
    ②`disk_table()` 没读 disk.json ⇒ 退化成"全部存在", 抹掉 9673 个缺失样本(D4 假绿)。
  - 测试 1111 → **1128 passed**(+17, 0 退化); 合成档对照未被破坏。
  - ⚠ 一处越界已按 scope-guard"阻塞"例外处理: `sim_qb.main()` 的 `prune_runs(root,…)` 用了未定义的 `root`
    (自 `1703abf` 起既有, 只影响独立运行的收尾清理), 挡在 W3 验收路径上故改成 `args.root` —— **如不认同, 回退这一个词**。

  **下一步 = W4**: 时间轴回放 —— 把 `merge_window` 接到回放游标上(按 `--replay-speed` 推进 + `--latency-mode` 注入录到的 rtt)。
  **W5/W6 未开工**。

  ### W1/W2 已实施(上一批, 已入库)
  - 新增 `scripts/qb_capture.py`(capture / snapshot / record / self-test)+ `tests/test_qb_capture.py`(12 条)。
  - `src/auto_qb/mixins/grouping.py` 抽出 `group_key_of()`(唯一 src 改动)+ `tests/test_grouping.py` 守阵 1 条。
  - 端到端真机跑通: 6 项自检**全 PASS**(字段完整性 / 映射单射 / **分组守恒** / 首尾闭合 / 流级脱敏一致 / 无凭据泄漏),
    `status=ok`, 检查点 3–4/4 对齐率 **1.0000**, warnings 0; 语料已确认**真脱敏**(名字/路径/tags/tracker 均伪名化)。
  - **反向对照(红验)已做且通过**: ①大小写被归一 ⇒ 守恒判据必红 ②多成员组改一个成员路径一个字符 ⇒ 必红。
    (第一次写这两条时**判据是空壳**, 红验把它抓出来了 —— 见 pitfalls。)
  - 测试基线 1098 → **1111 passed**(+13, 0 退化)。

  ### W4 已实施(本轮)
  - 录播游标(帧的**可交付时刻** = 各帧实测 `dt_ms` 的累积和, 按墙钟 × `--replay-speed` 推进)
    + 窗口合并成一拍 + `--latency-mode`(recorded 用录到的真实 rtt / p50 / p95 / const:N)
    + `fs_delta` 按 t_seq 叠到 mock 磁盘状态 + 4 条 `CORPUS.*` 运行期判据。
  - **端到端(3× 倍速)**: 14/14 帧吐完、窗口 4 次、游标滞后 1402 ms(预算 9144 ms);
    `replay_stream_consumed` / `replay_timeline_aligned` / `fs_state_match` / `endpoints_covered` **全 PASS**;
    合成档自检仍全通过。测试 1128 → **1133 passed**。
  - ⚠ 游标滞后**天然受客户端轮询间隔 × 倍速限制**(客户端每 1.5 s 拉一次、游标却连续推进),
    故阈值按 `轮询间隔 × 倍速 × 2 裕度` 算 —— 拍常数会在换倍速 / 换轮询档时变成假红或假绿。
  - **W3 已推送**: `dacc991` → Gitee + GitHub。

  ### W5 已实施(本轮)
  - **头号判据 `CORPUS.group_exact`**: 走 auto-qb 自己的 `GET /api/state?rid=-1&view=group` 取它**实际**分的组,
    与 `groups.json` 真值分组**逐组逐 hash** 比。**实测 真值 63 组 / auto-qb 实际 63 组、未分出 0、多分出 0**
    (静态与 3× 时间轴两种档位都绿)。⚠ 需开 `--web-port`, 否则 BASELINE; 从 sim 侧重算会变空转判据。
    **三道反向对照红验**: 成员串组(组数仍相同)/ 一组被拆成两组 / 真值组没被分出 —— 只比组数会放过串组。
  - `CORPUS.maindata_lag_modeled`: 两个滞后都为 0 时判据必须转红 —— issue 26-09-20-2145 的验收凭据。
  - **基线两套分离**: `sim_baseline.py --corpus <dir> --merge` 写 `corpus.*` 阈值; `sim_run` 在语料档
    **只查 `corpus.` 前缀、不回落裸 id**; 合成档基线另存 `…synthetic.json`。
    实测差得很远(`corpus.P1.first_round_s` 2.91 vs 22.68)⇒ 混用必然假红/假绿。
    ⚠ `CORPUS.replay_timeline_aligned` 刻意**不固化**(按"轮询间隔 × 倍速 × 2 裕度"动态算)。
  - 文档: `docs/sim-client-test-howto.md` 新增第 7 节「语料模式」。
  - **issue 26-09-20-2145 已置 Fixed**(徽标 + meta 两处, 补"如何被覆盖"段含 W0 口径修正, 索引已进 Fixed 区)。
  - 测试 1133 → **1137 passed**。

  ### W6 已实施(本轮) —— 真机走查闭环(按计划 §11 收窄)
  - 对「待用户真机走查」清单(~15 条)做**数据面 / 观感**分档。只有 2 条是数据面:
    · **视图重建范围收口** → **语料回放已闭环, 迁出清单**(2× 倍速回放下 15 次相邻比对中 5 次观测到
      速度随回放推进而变化; 局限: 该版语料只有 1 个种子在动 ⇒ 机制已证、幅度未证)。
    · **TASK015 错误种子原因** → **语料验不了, 仍需真机**(该版语料  态 0 条, 走不到原因预取分支)。
  - 其余约 13 条是前端观感 ⇒ **明确标注"仍需真机目视, 不得计入闭环"**。

  **语料计划 W0–W6 全部落地。残留**: 约 13 条观感项待用户目视; TASK015 待含 error 态种子的语料。

- **⓪ 规则条件表达式化 (2026-09-20/21, W1 已提交 `93f1911`)**: 计划
  [docs/plans/26-09-20-2225-rule-conditions-expression-plan.html](../docs/plans/26-09-20-2225-rule-conditions-expression-plan.html)
  (v3: 五条拍板口径 + §11 动作是否纳入的三档分析, L1 动作参数表达式记为候选排在 python 插件之后)。
  **W1 已入库 `93f1911`**(语法内核: errors/lexer/parser + 15 条测试, 未接规则系统)。
  **W2 已入库 `a1841e9`**(取值面 env + 求值 eval + 类型规则 types + `ExprCondition` + `RuleContext.expr_cache` +
  **`base.py` 出错即停规则 `(False, True)`** + 校验/schema/前端接线)。
  **W3 收尾(本轮)**: `sys.upload_today/download_today/upload_month`(Traffic Monitor dat)+ **配置期数据源门控**
  (`_expr_gate` → `_validate_rules(rules_config, errors, cfg)` → expr 单独分发, 门控跑在曲线段校验之前故须容忍
  结构非法的 `traffic_source`)、前端 expr 渲染为多行文本框、知识库回写(rule-system.md 新增「表达式条件」章 +
  出错即停语义、`modules.md` 加 `expr/` 行、`conventions.md` 立「新条件字段一律先进 env.py」)。
  实测 1062 → **1094 passed**(Windows; Linux 侧未同步重测, 已在 testing.md 标注)。
  已知坑: ①解析器"一层一运算符"判定必须在消费二元运算符后给 `used` 赋值, 否则退化成笼统报错;
  ②语义校验(types.py)与运行期求值(eval.py)的报错文案不同源, 测试按文案匹配时容易写错预期。

- **⓪b 乐观 UI「撤下」改造已完成并入库 (2026-09-21, 提交 `2094a36`)**:
  ✅ 真机实测撤下 **2947ms → 85ms**; 服务端侧只占 21ms, 其余 64ms 在浏览器主线程
  (大库渲染, 属前端性能议题)。下列条目按时间留档, 含中途的方案修订过程。
  - **调查报告** [docs/26-09-20-1806-optimistic-ui-half-fix-report.html](../docs/26-09-20-1806-optimistic-ui-half-fix-report.html)
    —— 根因与实测留档(bulk 缺真值 / 撤下判据过严 / 真值落地 1362ms)。
  - **可行性报告** [docs/26-09-20-2131-optimistic-ui-event-driven-feasibility.html](../docs/26-09-20-2131-optimistic-ui-event-driven-feasibility.html)
    （延迟链路拆解 / 通道选型 / 风险）。
  - **⭐ 实施计划（当前以此为准）**
    [docs/plans/26-09-20-2139-webui-truth-direct-query-and-optimistic-removal-plan.html](../docs/plans/26-09-20-2139-webui-truth-direct-query-and-optimistic-removal-plan.html)
    —— **三条硬指令**: ① 真值**不得从 `/sync/maindata` 读**, 改 **`torrents/info` 直查**
    (`QbApi.torrents_info` 已在 qbapi.py:306); ② **事件驱动(SSE), 不依赖轮询**;
    ③ **端到端反应 ≤10ms ⇒ 移除整套乐观 UI**。
    ⚠ 已提示: qB 单次 pause/resume 就 8.4ms, 理论下界 ~15~25ms, **10ms 可能差一点**(决策 D2);
    批量 448 目标用 `hashes=` 拼 URL ≈18KB 会超限(决策 D3)。
    P0 = 先实测门槛(**sim_qb 需加"maindata 快照 1.5s / info 实时"模型**才能复现), 未达标不动代码。
  - 🔄 **计划已修订(22:12): 乐观 UI 由"移除"改为「保留 + 简化」** —— 用户指示"乐观 UI 不取消,
    不过需要简化模型, 当前的模型错误太多"。§04 已重写: 撤下链路现有 **6 处互相咬合的机制**
    (`_snapshotTruth` / `_optimisticSettled` / `_settleFromTruth` / `_pullTruthAfterCmd` /
    `_expirePending` 3s 兜底 / `via` 分档), **近几轮追到的 bug 几乎全部来自 2~5**,
    而不是来自"要不要乐观" ⇒ 删 2~5, **只留"贴上 + 等推送结果"两步**。
    红线"不采纳命令前旧值"**上移到服务端**(真值已改直查, `_truth_landed` 能可靠判"是否已生效",
    未生效就不发 ok) ⇒ 前端不必再自己判。
    P3 不再依赖 P0 门槛; 门槛数字现在只决定压暗还要不要(D2)与未知超时(D4, 建议 8s)。
  - **已实施 P1(真值改直查, 2026-09-20 21:55)**, 单测 **1062 → 1063 passed**:
    `WebUIRuntime._affected_truth` 改走 `torrents/info`(**不再读 `store.by_hash` 同步快照**),
    带分批 `TRUTH_QUERY_CHUNK=50`(448 个 hash ≈18KB 会超 URL 长度限制);
    取不到**返回 None 不回落快照**(回落会把"读不到"伪装成"读到了旧值")。
    新增守阵 `test_affected_truth_reads_qb_directly_not_sync_snapshot`(故意让快照与 qB 客户端
    不一致, 真值必须等于客户端那一侧)。另修了桩 `_make_grouped_manager` —— 它只 seed store、
    **`client.torrents` 是空的**, 与真机不符(直查会查不到)。
    实测(sim_qb 零滞后): 单种子暂停撤下 **228ms**(改前 90ms) —— **仿真里直查是纯开销**,
    因为没有快照滞后可省; 真机收益待 P0 确认。
    ⚠ **直查只在走 `defer_receipt` 的命令上生效**: `bulk_torrents`(整剧/整集/多选)仍走
    "handler 自写回执", **根本不调用 `_affected_truth`** ⇒ 整剧无直查、遥测仍 0 行,
    **必须在 P2 一并接入**。
  - ⚠ **顺带发现的既有缺陷(未改, 待定夺)**: `tests/test_web.py` 里
    `test_truth_hold_budget_matches_backend` **同名定义了两次**(约 3910/3933),
    Python 后者覆盖前者 ⇒ **第一条静态守阵从未被执行**。
  - **已实施 P2(事件驱动 SSE, 2026-09-20 22:45)**, 单测 **1063 passed**:
    · 后端 `WebUIRuntime.subscribe/unsubscribe/notify`(有界队列 `EVENT_QUEUE_MAX=200` +
      `put_nowait`, 满则丢) + `GET /api/events` SSE 端点; 推 `cmd`(`set_result` 处, 带 cmd_id)
      与 `ver`(`_publish_locked` 处, **只带版本号**)。**主循环只 put 队列、不碰 socket**。
      心跳 `SSE_KEEPALIVE_S=5s` —— **必须 < WEB_VIEW_TTL(10s)**, 否则客户端被判不活跃
      ⇒ 主循环停摆 ⇒ 推送自锁。订阅/退订各记一条 INFO 便于排查句柄堆叠。
    · 前端 `startEvents/stopEvents`(startPolling 接、unmounted 断); `waitCmd` 改为
      **推送与轮询赛跑**(SSE 断了自动退回); `ver` 事件去抖 60ms 触发 refresh。
    · 鉴权: `EventSource` **发不出 Authorization 头** ⇒ 服务端放行 `?token=` 兜底。
    · 实测(独立 SSE 客户端 ×3): 推送 202/299/239ms vs 轮询 244/321/278ms ⇒ **早 23~41ms**
      (落点不同最多省 ~500ms = 原 0→150→300→500ms 退避粒度)。
    ⚠ **验证前端改动要防浏览器缓存**: agent-browser 的 Chrome 缓存 `/shared/*.js`,
      页面可能仍在跑旧包(实测页面里 `AQB_COMMANDS` 只有 2 个键, 服务端文件是新的)。
  - ✅ **D2 已实施(2026-09-20 23:45)**, 单测 **1063 passed**:
    · 服务端 `defer_receipt` 改为**回执立即写**(**不带 truth**) + 真值登记 `truth_pending`;
      `flush_receipts` → **`flush_truths`**(直查 → 落地才推 `truth` 事件, **超时不推**)。
      `RECEIPT_WAIT_CAP_MS`(1200) → **`TRUTH_PUSH_CAP_MS`(8000)**。
    · 前端**压暗与值覆盖拆开**: 回执到 ⇒ `op.grey=false`(撤下) + `op.hold=true` 继续覆盖值;
      `truth` 事件到 ⇒ `onTruthEvent` 写真值 + 删 pendingOps。删掉三处
      `_settleFromTruth`/`_pullTruthAfterCmd`(1500ms 预算是撤下 2947ms 里的 1688ms 大头)。
      `_markCmdSettle` 判据从"pendingOps 清空"改为"没有 op 还在 grey"。
    · **实测①(sim_qb 注入 1250ms 延迟)**: `贴上 0ms / 回执 2ms / 撤下 9ms`。
    · ✅ **实测②(真机 23:53 暂停种子)**: `贴上 0ms / 回执 70ms / **撤下 85ms via=receipt**`,
      真值 1624ms 后独立推送(7 轮 ×~200ms)。**撤下 2947ms → 85ms(34.7 倍), 不弹回。**
      真值仍要 1.25~1.6s(qB 自身节奏) 但**不再影响观感** —— 压暗 85ms 就结束、
      值覆盖撑到真值事件到达。另: 真值等待轮次改打 DEBUG(一次 7~8 条 INFO 会刷屏)。
    · 顺带合并了重复守阵(两条 `test_truth_hold_budget_matches_backend` → 一条
      `test_truth_hold_matches_truth_push_cap`), issue 26-09-20-2212 的问题已消除。
    · **撤下 85ms 的归因已完成(00:26 真机 resume)**: 贴上 0 / POST 24 / 执行 2.3 /
      **事件 21**(服务端推送到浏览器) / 回执 61 / 撤下 85。
      ⇒ **服务端侧只占 21ms; 浏览器侧占 64ms**(事件→兑现 40ms 主线程排队 + 兑现→渲染 24ms)。
      剩余属**前端大库渲染性能**议题, 与真值链路无关 ⇒ **到此收尾, 可提交**。
      `[perf]` 现在无条件一行打全五段(贴上/POST/排队/执行/回执/事件/撤下), 便于后续归因。
  - ✅ **P3 收尾清理已完成(2026-09-21 01:10)**, 单测 **1092 passed**(上游 rebase 带进新用例):
    · **删死代码 58 行**: `_settleFromTruth` + `_pullTruthAfterCmd` —— 真值改 `truth` 事件推送后
      已无引用。静态守阵加了**反向守阵**(这两个不许复活)。
    · ⚠ **修了一个真遗漏**: `shows.js`(追剧页集行)**此前漏改**, 还在跑 1500ms 拉取预算,
      撤下比种子页慢一大截 ⇒ 已改成与种子页一致的路径(`via=receipt`)。
    · `via` 分档 5 档(含 truth/pull/stale) → **2 档**(receipt/push)。
    · ❗**刻意保留** `_snapshotTruth` / `_optimisticSettled` / `reapplyPending` —— 它们是
      **SSE 断线时的安全网**: 推送丢了以后, 轮询带回的 `/api/state` 一旦含真值就提前收工;
      没有它, SSE 一断就是"命令其实成功、8 秒后却回滚"的假失败。守阵注释已写明勿删。
    · 实测(sim 1250ms 延迟): 撤下 7ms、`via=receipt`。
    ✅ **P3 已提交 `59754eb`**(Gitee + GitHub 均推上)。与上一批 `0c18fcd` 分两个提交, 便于单独回看/回滚。
  - ✅ **后端 `[cmd]` 诊断日志全部降为 DEBUG(提交 `dbceef4`)**: 用户指示"后端的桩调为 DEBUG,
    前端保留" ⇒ SSE 订阅/退订、真值已推、真值未落地、补刷新、命令排队/执行的**正常分支**全降
    DEBUG; **异常(真值超时 / 补刷新>300ms / 直查失败)仍 WARNING**。前端 `[perf]` 一行保留。
    ⚠ 改动带出守阵: `test_cmd_timing_is_logged_without_browser` 写死了"快命令=INFO"的级别断言
    ⇒ 已改 DEBUG 并**补反向断言**(INFO 级别下必须捞不到), 防以后改回 INFO 不报警。
    ⚠ **GitHub 镜像本次直连失败**(21085ms 超时)—— 按约定只报一次、不重试; 主线 Gitee 已推上。
    镜像滞后一个提交(`dbceef4`), 后续提交会自动带上。
  - ✅🔴 **P0 已实测(2026-09-20 23:15 真机 · 暂停种子) —— E1 判定为分支 B, 计划的关键前提变了**:
    ```
    [cmd] pause_torrent: 执行 2.7ms / 补刷新 2.9ms
    连续 7 轮「等真值落地」(每轮 ~200ms) => 回执 1259ms(踩 1200ms 上限照发)
    [perf] pause: 贴上 0ms / 回执 1259ms / 撤下 2947ms via=pull  (1 个目标)
    ```
    ① 这是**暂停**不是开始, 且 qB 执行仅 2.7ms ⇒ **"暂停本来就快"这个旧推论也被推翻**;
    ② 真值此刻已走 P1 的 `torrents/info` **直查**, **连直查都要等 ~1.25s**
       ⇒ 滞后**不在我们的同步快照, 而在 qB 自己**;
    ③ ⇒ **E1 = 分支 B**: qB 自身把状态翻过来要 >1.2s, 我们绕不开。
    **结论: 「撤下 10ms」在"依据真值"的前提下不可达**(差两个数量级, 不是差一点)。
    但**仍值得做完 P2+P3**: 2947ms 里有 **1688ms**(2947−1259) 是我们自己的拉取开销, 可整段拿掉
    ⇒ 改造后 ≈ 1.25~1.3s。
    🔴 **新增阻塞决策 D2**: 建议服务端**不再为等真值扣留回执**(正是它把回执推到 1259ms),
    改为"执行完即发回执 + 真值稍后作为独立 truth 事件推送" ⇒ 撤下可降到 10~20ms 且不弹回。
  - **新增 `scripts/dev_webui.py`(2026-09-20 23:05)**: 一键起"只开 WEB UI"的 auto-qb 连真机,
    用来看界面/试交互。生成**最小配置**到独立数据目录(默认 `%TEMP%/auto-qb-dev-webui`),
    关掉所有带开关的自动任务(规则/集数标签/标签清理/缺文件扫描/站点标签), 只留同步快照+WEB UI,
    默认端口 8177 并自动开浏览器。已用仿真端当"假真机"验证通过(300 种子连通)。
    ⚠ 两条硬知识: ① **`dry_run` 不能用** —— 项目里 `if not dry_run and web.enabled` 才起
    WEB 服务, 开 dry_run 等于没界面; ② 规则是**按键名 `_rules` 结尾自动发现**的,
    "没有规则"= 不写任何 `*_rules` 段, 写 `rules_config: {}` 会被 `validate_config`
    判"未知键"(已实测报错)。③ WebUI 上的**手动**命令会真的作用到 qB(点暂停即真暂停)。
  - **已入池 issue**: ① `26-09-20-2145-test-sim-qb-maindata-snapshot-lag`
    (sim_qb 缺"maindata 快照滞后"模型) ② `26-09-20-2212-test-duplicate-test-name-shadowed-guard`
    (`test_truth_hold_budget_matches_backend` 同名两次, 前一条守阵从未执行)。
  - ⚠ **用户纠正了目标两次**: ① 不是"让撤下变快", 而是 **让真值更快到 + 撤下依据真值 +
    **事件驱动、不依赖轮询**; ② 曾误推"暂停已好"—— 90ms 是 sim_qb 零延迟的数, 真机不成立。
  - **结论**: 我们自己加在链路上的延迟约 **1.5~2s**(回执轮询退避 0/150/300/500ms +
    `_pullTruthAfterCmd` 1500ms 预算 + `/api/state` 轮询 1.5/2/3s), 事件驱动可整体去掉;
    **qB 那侧还有 ~1362ms**, 是"等 qB 内部"还是"等 sync 快照 1.5s 刷新"**尚未判定**。
  - 🔴 **阻塞项 E1(必须先做, 约半天)**: resume 后同时轮询 `torrents/info` 与 `/sync/maindata`,
    看谁先翻。分支 A(快照滞后) ⇒ 改直查即压到几十 ms; 分支 B(qB 内部慢) ⇒ resume 下界 1.4s,
    **「撤下 10ms」与「撤下依据真值」在 resume 上互斥**。
  - 通道选型 **SSE**(FastAPI 原生、零新依赖、自带重连);`websockets` **当前未安装**, WS 需新依赖。
    挂点: `set_result`/`flush_receipts`(推 cmd) + `_publish_locked`(推 ver);
    **主循环只 put 队列, 绝不直接写 socket**。
  - ⚠ **真值变快后, `「真值 == 预测值」`的严格相等会立刻成为新瓶颈**(resume 预测 2 种 vs 落地态
    6 种), 必须与推送同期改成**分动作判据**。
- **① 上轮计划复核的收尾(只剩第 7 项) (2026-09-19)**: 复核报表

- **② WEB UI 操作跟手性优化 (2026-09-19)**: 三波次全部入库(`10e06a8` 分层节拍 + 命令唤醒 + 乐观 UI + 批量合单
  / `5d1e52c` 请求超时 + 视图分片回传 + 只读缓存 / `366092d` 行窗口化)。计划
  [docs/plans/26-09-19-1241-webui-responsiveness-plan.html](../docs/plans/26-09-19-1241-webui-responsiveness-plan.html); 档案 [tasks/26-09-19-webui-responsiveness.md](tasks/26-09-19-webui-responsiveness.md)。
  **剩**: 真机走查(真实 qB 数据下的观感)。
- **③ 前端轮询按种子量分档 (2026-09-19, 待提交)**: 计划里唯一排在 P1 之后的项 —— 降轮询间隔会**放大**全量回传 + 整树重渲染, 顺序错了会加剧不跟手。档位实测而定: 1000 种子单轮 143ms / 3000 种子 353ms / 5000 种子 ~550ms ⇒ **≤1000 → 1.5s / 1000~3000 → 2s / >3000 → 3s**(主线程占用率 10%/15%/17%); 下界 1.5s = 服务端 `sync_interval`(再快只是多拿空响应)。实现: `pollSec` 字段退役(不留死字段), 新增 `basePollMs()`; 冒烟新增分档断言 ⇒ 30 项 0 失败。
- **④ WEB UI 视图重建范围收口 · 种子速度刷新滞后修复 (2026-09-18, 未提交)**: 真因是两条重建路径**范围不一致**(主循环 `_tick` 只重建 `_group_view` 却清掉共享脏标记 ⇒ singles/shows/flat 被饿死, 版本号照常自增 ⇒ 前端换上陈旧数组)。已改为唯一入口 `rebuild_views()` + 置脏移出门控 + 前端取消 idle 退避并把 `server_state` 并入 `/api/state`。基线 1018 → **1021 passed**。剩用户真机走查 → [tasks/26-09-18-webui-view-rebuild-scope.md](tasks/26-09-18-webui-view-rebuild-scope.md)
- **⑤ 浏览器冒烟能力 (2026-09-19, dev-only, 长期有效)**: `scripts/ui_harness.py`(真 `create_app` + `FakeClient` + 合成种子 + 命令泵 `ok|error|hang`)+ `scripts/ui_smoke.cjs`(Playwright, 双 UI **46 项断言** + 内置 A/B 基准)。**Windows 上可跑**, 攻破了"单测测不到前端交互"这个长期卡点。⚠ `--host` 现在只接受回环(免鉴权服务不得暴露到局域网)。⚠ **两种模式都要跑**: `ok` 看正向、`--expect-cmd error` 看回滚 —— 后者此前必红所以没人跑, 已按模式分流断言。

- **skills 全量安全审查 (2026-09-20, ✅ 已提交并推送 `a370354`, Gitee 主线成功; GitHub 镜像滞后 2 个提交)**: 按 skill-vetter 协议审查 26 个技能 —— 唯一红线是 `autoclaw-design-capability` 内 `design-skeletons/last30days` 的 `lib/chrome_cookies.py`(解密 Chrome cookie 取 X 会话 `auth_token`/`ct0`, 仅 macOS 可触发且该包被 sync 排除 ⇒ 不可达), 已**整体删除该骨架**; 另删 12MB 重复副本 `autoclaw-design-capability_noqa`, 同步清理 `sync_agent_skills.py` 的 `EXCLUDED` / autoclaw `INDEX.md`(骨架计数 83→82) / `NOTICE.md` / `pitfalls.md`。3 条次要发现已入池 `memory-bank/issues/`(hatch-pet 付费 API / 写 `USER.md` 口径冲突 / grill-me 空 stub)。审查报告 [docs/26-09-20-1429-skill-vetter-audit.html](../docs/26-09-20-1429-skill-vetter-audit.html)。**已补**: 实跑 `scripts/sync_agent_skills.py` 后 `my-commit-flow` 已链接进 `.codebuddy/skills`(现 24 个, = 25 个顶层 skill 减去被排除的 autoclaw), 读穿校验 OK、无悬空链接; **重启会话后才会出现在技能列表**。

- **5000 种子仿真客户端 · 独立安全/性能测试 (2026-09-19, W0–W6 全部走完)**: 已归档到 [tasks/26-09-19-sim-client-5000.md](tasks/26-09-19-sim-client-5000.md); 遗留 BUG-01(断连不自愈)按用户决定**暂不修**, 已立档在 `TODO.md`。
- **知识库瘦身 (2026-09-20, ✅ 已提交并推送 `9ccace6`, Gitee 与 GitHub 镜像均成功)**: 按"过时 / 重复 / 低价值"三分类清理根 `AGENTS.md` 与 `memory-bank/` —— **路由表与黄金法则单点收在 `AGENTS.md`**(`memory-bank/README.md` 改指针), 已完成条目从本文件迁出到 `progress.md` / 任务档案; `testing.md` 顶部基线数字**未动**(待补测 WSL 一侧再更)。提交时与上游 7 个提交 rebase, `AGENTS.md` 一处冲突按"保留上游新增的 HTML dark 主题规则 + 保留本轮压缩后的计划产出口径"解决。**知识库回写(pitfalls 新增「rebase --continue 被 VS Code 编辑器挂死 + packed-refs 陈旧致核 ref 假红」条目 + 本行状态更新)尚未提交。**

## 待用户真机走查 (代码/测试均已完, 只差真实 qB 数据下的观感确认)

> ### ⚠ W6 已对本清单做过"数据面 / 观感"分档(2026-09-21, 语料计划 W6)
> 原写"把 8 条待真机走查先过一遍", 实测清单**约 15 条**, 且绝大多数是**前端观感项** —— 回放 qB 数据面根本测不到。
> 故按计划 §11 收窄: 只处理**数据面相关**的条目, 其余**一律标注"仍需真机目视, 不得计入闭环"** ——
> 否则会把"没闭环"记成"闭环了"。
>
> | 条目 | 分档 | 语料回放结论 |
> |---|---|---|
> | **视图重建范围收口** —— 种子速度是否已随轮询刷新 | **数据面** | ✅ **已闭环, 从本清单迁出**。实测: 语料时间轴回放(2× 倍速)下周期性拉 `GET /api/state?rid=-1&view=torrent`, 15 次相邻比对里 **5 次**观测到种子速度随回放推进而变化, 流吐完后稳定在同一值 —— 即**视图确实随轮询刷新**。(局限: 这版语料里真机当时只有 1 个种子在动, 样本薄; 机制已证, 幅度未证。) |
> | **TASK015 错误种子原因** —— 错误态状态列是否显示 tracker 原文 | **数据面** | ⚠ **无法用语料验证, 仍需真机**。该版语料 T0 的状态分布是 `stalledUP 56 / stoppedDL 24 / stoppedUP 3 / stalledDL 1 / uploading 1 / missingFiles 1 / downloading 1` —— **`error` 态 0 条**, 走不到原因预取那支路径。要验需**重抓一份含 error 态种子的语料**(真机此刻无 error 种子, 只能等它自然出现或造一个)。 |
> | 其余约 13 条(Console Hub / 主循环解耦 / 跟手性三波次 / 本轮新修 4 处 / 热路径提速体感 / 追剧页打开目标文件夹 / TASK011-014 / 状态栏速度 / 今日流量目视 / 列设置多标签页 / 可用性列 / …) | **观感** | ❌ **仍需真机目视, 不得计入闭环** —— 回放数据面测不到观感。 |

- **两个 WebUI 缺陷的修复(2026-09-21, 未提交)** —— 建议真机顺路走查这两处:
  ① **种子页筛选器**: 切到种子页(或刷新后停在种子页)点标签/分类/站点/路径, 弹层应直接有选项且
     计数 = **种子数**(不再是"暂无数据"); 与辅种页的计数(组数)口径不同属预期。
  ② **辅种组整组暂停**: 右键整组暂停后, 组行应**一直是灰的**(修复前会闪一下做种绿再变灰)。
     判据看行色即可; 若仍闪, 记录 `[perf] 命令 … via=` 那行(console)。
- **设置页新版(Console Hub)· 2026-09-21, 已实施待目视**: 经典页页头「新版界面」切进去(选择存 localStorage)。
  重点看: ①首页 9 张卡的 LED 三态(绿/橙/灰)与读数对不对 ②点进分区后「块 → 行」两层级是否够紧凑、
  行尾 `?` 浮窗是否就近弹出且 Esc/点外部能关 ③**危险档(密码 / 界面监听地址)静息描边就是红色**、
  重要档(数据目录)是橙色 —— 不聚焦也能看出轻重 ④五个主题(含 frost/golden 两个亮色)下输入框/下拉/开关/发光
  有没有隐形或过曝 ⑤站点/规则/限速三个专段的切角小标签与档位格。
  (视觉是照 05-console-hub 样张复刻的, 样张本身是调过多轮才定的, 如有偏差请直接指出是哪一处。)
- **主循环 × WebUI 解耦** (`5691c6f`, 2026-09-20) —— 纯结构性重构, 行为应**完全无感**; 重点确认
  ① 各视图照常刷新、切页无空白 ② 右键命令(暂停/删除/汇报/限速…)照常生效且乐观态正常落回
  ③ 关闭网页后主循环不再做视图重建(日志里应看不到 `[cmd] 回执(补刷新后)已写` 之外的 Web 开销)
- **跟手性优化三波次** —— 右键菜单响应 / 切视图首帧 / 3000+ 种子滚动流畅度
- **本轮新修的 4 处(建议顺路走查)** —— ① 刷新页面时若上次停在**追剧页**, 现在应正常显示(修复前是永久空白);
  ② 右键**复制磁力**在辅种页/追剧页应真能复制(修复前 100% 提示"没有 magnet 链接");
  ③ 整组/整集暂停后**行本身**应立刻变灰(半透明 `is-pending`)且颜色即时切换;
  ④ 混合状态组的颜色可能与修复前不同(状态优先级已统一到后端口径, 只影响 2 种混合态)
- **热路径提速(§11, 建议重点体感)** —— 3000+ 种子库下切视图/滚动时数据到达更快(服务端 189 → 23.5 ms)。
  重点看: 种子页在**数据变化那几轮**是否还有"迟一拍"的观感; 若大库仍觉卡, 下一步就是报表 §08 第 7 项
- **追剧页剧/集右键「打开目标文件夹」** (`c888fba`) —— 剧 → 集 → 种子三级各点一次; 顺带确认整剧开始/暂停/删除已恢复
- ~~**视图重建范围收口** (`1021 passed`) —— 种子速度是否已随轮询刷新~~ ✅ **W6 已用语料回放闭环, 迁出本清单**
  (结论与实测见本节顶部 W6 分档表: 15 次相邻比对中 5 次观测到速度随回放推进而变化)
- **TASK015 错误种子原因** (`9723a76`) —— 错误态状态列是否显示 tracker 原文。
  ⚠ **W6 判定: 语料验不了** —— 该版语料 `error` 态 **0 条**, 走不到原因预取分支; **仍需真机**
  (或重抓一份含 error 态种子的语料后再验)
- **TASK013 / TASK012 / TASK011**(第九/十/十一轮修复) —— 逐轮走查反馈
- **TASK014 UI 组件库 20 式** (`fae019a`) —— 挑选与按需迭代

- **WEBUI 状态栏上传/下载速度恒为 0 (2026-09-20, ✅ 已修并验证 → issue 置 `Fixed`; 剩用户真机走查)**: 根因**已实测确认** —— 状态栏在前端对 `groups` 求和(`decorate.js:136-141`), 而 P1-1 按视图回传把 `groups` 从种子页裁掉了(`VIEW_ARRAYS["torrent"]=("torrents",)`, `web_view.py:48`) + 前端「键不存在保留原引用」(`app.js:883`) ⇒ 种子页上 `this.groups` 恒为 `[]` ⇒ 恒 0。次因: 合计漏 `singles`, 桩实测(50组+200未归组)**少算 88.7%**。复验方式: 起 `scripts/ui_harness.py --torrents 300` 直接 curl 两视图比对(种子页响应**无 groups 键**, 真值 15,206,400)。修法选定「服务端算 `status.totals` 恒回传 + 前端改读」(候选 C 用 `server.dl_info_speed` 因桩里 `server_state=null` 不可测, 仅备选)。计划 [docs/plans/26-09-20-1702-webui-statusbar-speed-fix-plan.html](../docs/plans/26-09-20-1702-webui-statusbar-speed-fix-plan.html); 档案 [tasks/26-09-20-webui-statusbar-speed.md](tasks/26-09-20-webui-statusbar-speed.md); 报告 [issues/26-09-20-1646-bug-webui-statusbar-speed-always-zero.html](issues/26-09-20-1646-bug-webui-statusbar-speed-always-zero.html)。⚠ 与 2026-09-19 的 BUG-8(追剧页成员索引被裁致永久空白)**同类**: 跨视图的常驻消费者去依赖按视图裁剪的阵列, 建议顺手排查还有没有第三个。
  **已实施(未提交)**: F1 `_build_speed_totals()`(`web_view.py`) / F2 `speed_totals` 与四视图同临界区发布(`web_runtime.py`) /
  F3 `status.totals` 恒回传(`web.py`, **并把 `ensure_group_state()` 提到 status 字典之前** —— 否则字典字面量先求值,
  totals 慢一拍且首轮为 0) / F4 前端 `totalDl|totalUl` 改读 `status.totals`(`decorate.js`, 两套模板零改动)。
  实测: 桩服务种子页 `totals={dl:15206400, ul:45926400}`(= groups+singles 真值; 修复前种子页无此键、合计仅 1723392);
  单测 **1059 → 1062 passed**(Windows) / WSL **1057 → 1060 passed + 2 skipped**, +3 守阵(端点恒回传 / 静态防回潮红绿双验过 /
  合计含未归组); 冒烟双 UI **54 项 0 失败**, DOM 实测 `14.50 MiB/s`。基线数字已回写 `testing.md`。

- **列设置被重置 = 多标签页整份覆盖 (2026-09-20/21, ✅ 两次修复均已入库 `11382ed`+`6c1b7f4` → issue 置 `Fixed`; 剩用户真机走查; 双轨重设计计划已出待拍板)**: 用户报"栏的顺序/显示/宽度经常被重置"。**根因实测确认**: 内存是**加载时读一次的快照**(`app.js:273 initialColState`) + `saveColState()` **整份写回** ⇒ **last-writer-wins**, 谁最后动一下存储就变成谁的快照, 先改的标签被静默吞掉(入池时猜的"写失败/读入洗净/自适应覆盖/v3→v4 迁移"**全部排除** —— 单标签六路径全保持, 只有第二个标签能复现)。修法: **F1** `saveColState(page)` 改 read-modify-write(以存储为底, 只覆盖本 page 四段; 6 处调用点传 page) + **F2** `storage` 事件 → `adoptColState()` 整份采用 + **F3** `visibilitychange` 回到可见补漏。**F1 单独不够** —— 用户两个标签改的通常是同一个表, page 级合并同表仍然后写赢。冒烟新增「列设置多标签页互不覆盖」⇒ ok/error 双模式各 **56 项 0 失败**; 红验(摘掉标签 2 的 storage 监听)确认守阵钉得住; 单测 **1062 passed** 未退化。后端零改动, **未升 `COLS_STORE_KEY`**。计划 [docs/plans/26-09-20-1836-webui-column-prefs-sync-plan.html](../docs/plans/26-09-20-1836-webui-column-prefs-sync-plan.html); 档案 [tasks/26-09-20-webui-column-prefs-reset.md](tasks/26-09-20-webui-column-prefs-reset.md); 报告 [issues/26-09-20-1800-bug-webui-column-prefs-reset.html](issues/26-09-20-1800-bug-webui-column-prefs-reset.html)。**真机走查**: 开两个标签各改一次列(隐藏 + 拖宽), 互相刷新确认都不丢。⚠ 09-21 用户反馈仍复现 →
  失败分析 [docs/26-09-21-1248-column-prefs-fix-failure-analysis.html](../docs/26-09-21-1248-column-prefs-fix-failure-analysis.html)
  实测确认宽度另有通道(非手动页自适应 px 落盘/跨窗口互写)已二次修复入库 `6c1b7f4`; 仍敞着
  "隐藏列宽被抹"与结构脆弱性 → **双轨模型重设计计划已出**(见「正在进行」首条), 待拍板后实施。

- **状态栏「今日流量」视觉重做 (2026-09-20, ✅ 已提交推送 `94c6857` → issue 26-09-20-1840 置 `Fixed`; 剩真机目视)**:
  图标换真图标 `#i-traffic`(上下行箭头)并改**双色** —— 两条 path 内联 `stroke: var(--today-down/--today-up)`, 靠 CSS 变量穿越 `<use>`
  影子树生效(外部选择器进不去); 数值去字面量 ↓/↑ 改用 `#i-arrow-down/up`; 历史入口图标弃粉改 lime(`--today-ico`);
  `.sb-today .v-*` 抬到 `.sb-item.sb-today .v-*`(修棱镜掉白的层叠根因); "今日" 标签与 "连接/剩余" 同格式; 速度区每方向合成
  `[方向图标] 速度 / 限速` **整组可点**按钮(状态栏不再单独给限速配图标)。⚠ **未做浏览器冒烟** —— `ui_harness.py` 桩不产 traffic
  数据(`v-if="todayTraffic"` 不渲染), 环境也没装 playwright。
  **真机走查**: ①双色是否分得清、箭头与数字 3px 间距是否合适 ②两套 UI / 五主题下 lime 历史图标是否协调 ③点速度区任一处都能弹限速浮层

- **种子页「可用性」列隐藏负数与暂停值 (2026-09-20, ✅ 已提交并推送 `7548e51`; 剩真机目视)**: 用户报该列出现负数
  (qB 拿不到 distributed_copies 时给 `-1`, 旧版 `toFixed` 出 "-1.00" 看着像真数值)且暂停中的种子也显示。修法沿用
  **单元格口径单点**: 新增 `cellAvailability(m)`(FX-26, `format.js`, 与 FX-03 的 `cellPeers` 同范式 —— 空串占位不摘节点),
  两套模板(atlas/prism 各一处)改引用它并补 `zero` 类。判据: `kind === "paused"` → 空; `availability < 0` 或缺失 → 空;
  **0 仍是有效值(确实零副本), 保留显示**。验证: `ui_harness.py --torrents 300` + Playwright 实测 —— paused 行 = 空、
  注入 `-1` = 空、注入 `2.5` = "2.50"、`0` = "0.00"; 双 UI 冒烟 **56 项 0 失败**且无 console 错误; 单测 130 passed。
  ⚠ **抽屉(drawer.js:442)仍是老口径** `(d.availability ?? 0).toFixed(2)`, 同样会显示 -1.00 —— 用户本次只点"可用性一栏",
  按范围守恒未动, 待确认是否一起改。

- **种子页「最近活动」列改相对时间 (2026-09-20, ✅ 已提交并推送 `7548e51`; 剩真机目视)**: 新增 `fmtRelTime(ts)`
  (FX-27, `format.js`) —— 刚刚 / N分钟前 / N小时前 / N天前 / **N个月前 / N年前**; 哨兵 `-1`(从未传输)仍为空白
  (TBL-01); 绝对时间点保留为 `title` 供悬停核对。
  ⚠ **口径(用户真机反馈后定的)**: 该列**一律相对, 不回落绝对日期** —— 首版写了"超 30 天回落日期", 真机上
  同一列里"有的 3天前、有的 08-11 21:06"被读成"没改干净", 故补月/年两档把长跨度也纳入相对。
  ⚠ **关键**: 相对时间必须读响应式时基 `nowSec`(新增于 `app.js` data + 30s ticker), **不能现取 `Date.now()`** ——
  后端该字段按分钟量化 + `rid` 未变不回传数组 ⇒ 行对象不变、Vue 不重渲染 ⇒ 相对值会永久冻在渲染那一刻
  (已入 pitfalls)。验证: 浏览器注入 20s/10min/2h/3d/-1/40d 六种情形实测文案正确; 把 `nowSec` 拨快 1 小时,
  文案整体加一档(证明时基生效); 双 UI 冒烟 **56 项 0 失败**、无 console 错误; 单测 130 passed。
  ⚠ **抽屉(drawer.js:488)「最近活动」仍是绝对时间**(`ts(d.last_activity)`), 同上面的可用性一样待确认是否一起改。

- **时间点列表头右键切换相对/绝对 (FX-28, 2026-09-20, ✅ 已提交并推送 `7548e51`; 剩真机目视)**: 覆盖**四个时间点列**
  —— 添加于 / 最近活动 / 完成于 / 追剧页「最近动静」(`TIME_FMT_KEYS`), 各列表头右键多两项「相对时间 / 绝对时间」,
  当前口径带勾标(`.ctx-tick`)。**按列独立**存 `data.timeFmt` {列key: "rel"|"abs"}, 持久化键 `autoqb_timefmt_v1`
  (刻意不进 `autoqb_cols_v4`: 那边是列集合/列宽/顺序 + 跨标签合并, 显示口径是另一条生命周期)。
  单元格一律走 `format.js` 的 `cellTime(ts, key)` / `cellTimeHint(ts, key)`, **所有时间点列不得再直接调
  `fmtTime`/`fmtTs`**(否则那列就没有开关); 两种口径互为 title。**默认值 = 改造前现状**(添加于/完成于/最近动静
  原为绝对, 最近活动已改相对) —— 加开关不顺手改观感。**时长列(做种时长/活跃时间/ETA)不参与**: 它们不是时间点,
  没有绝对/相对之分, 菜单里也不出现这两项。
  实测: 默认三列 = 绝对/相对/绝对; 只切「添加于」→ 另两列不动; 存储 `{"added_on":"rel","last_activity":"rel",
  "completion_on":"rel","latest":"abs"}`; 刷新保持; 分组页「添加于」与种子页共用同一设置(按列 key 不按 page);
  做种时长右键无切换项。冒烟 56 项 0 失败; 单测 130 passed。
  ✅ **跨标签同步已补(2026-09-20 21:52, 未提交)**: `adoptTimeFmt()`(`format.js`)整份采用存储值 ——
  F2 `storage` 监听(`_onTimeFmtStore`, 与列偏好**独立**监听: 两个 key 生命周期不同, 合一个监听只会让判据纠缠)
  + F3 回到可见时补对齐一次; `unmounted` 里撤监听。实测两标签双向同步(B 切相对 → A 立即跟随; A 切回绝对 → B 跟随)。

## 定案口径 (别改回去; 完整判据见 [pitfalls.md](pitfalls.md))

- **列偏好"升版本"**: 列集变更(加列/减列/重排)与存储结构扩展**一律不升版本**, 只有"旧缓存结构已无法被 `loadColState()` 正确解释"才升(如 v2 按列索引存), 且升版本必须同时挂 `LEGACY_COLS_KEYS` 迁移。**2026-09-21 双轨重设计(plan 26-09-21-1551, D1 拍板)已升 v5**(`autoqb_cols_v5`, 意图/生效分轨, 挂 v4/v3 迁移) —— 这正是该判据的合法使用, 原"无 v5 计划"口径同时作废。历史计划 `docs/plans/26-09-15-1042-webui-optimization-plan-v3.html` 里"重排列集则升 v4→v5"是当时口径, 已被第十轮计划取代 —— 存档未改动, **别照抄**。
- **第十轮两处已知限制**(非待办): ① 列偏好受 localStorage **origin 隔离** 影响(`localhost` 与 `127.0.0.1`/换端口 = 不同站点各存一份) —— 用户明确要求只存浏览器, 不做服务端化; ② 目录浏览器只能浏览**已有保存路径及其子目录**(安全边界), 全新位置需在输入框手填。
- **第十一轮定案**: 行/表头一律 `fit-content; min-width: 100%`(**底色跟内容**), **行内单元格必须 `min-width: 0`**(否则 nowrap 文本把行顶宽 ⇒ 列没溢出却常驻横滚条); 曾用"行定宽 100%"治假滚动条, 会让**溢出段没有底色**(用户实测"滚动后右边无背景条"), 已回退。
- **开工先拉分支 + 提交即推送 (2026-09-19/20 用户指定, 别照抄旧文档)**: 两条规则的**单点定义都在 `AGENTS.md`**(「会话协议 · 开始」与「提交 / PR」), 本文件只留指针: ①会话第一步必为 `git pull --rebase <远端> develop` (**分支名必须写**), 确认不落后才动手, **禁止在落后分支上改代码**; 拉取前先弄干净工作区 (脏工作区 + rebase 触发 stash 会损坏对象库)。②用户说"提交" = **commit + 自动推送** (先 commit → rebase → 推 Gitee → 尝试一次 GitHub 直连, 失败不重试)。⚠ `conventions.md` 里 2026-09-10 的"🔴 绝对不要 push"**已作废**, 只作历史沿革保留 —— 按它做会漏推, 而交付只看 Gitee 有没有该提交。**同一条协作规则不在知识库复述全文, 只留指针**; 该规则共 4 处入口 (`AGENTS.md` / `.github/copilot-instructions.md` / `.agents/skills/memory-bank/SKILL.md` / `.github/instructions/ai-lib.md`), 改规则要一次改全。
- **工作区模式: 多 clone 并行 (2026-09-20 用户拍板, **git worktree 已弃用**)**: 每个 AI 实例一份**完整克隆**(各自独立 `.git`), 跨工作区同步一律走 Gitee `develop`; 单点在 `AGENTS.md`「环境硬约束」与 `conventions.md`「协作约定」。原 8 个 worktree 目录已打包存档到 `D:/Projects/_archive/auto-qb-worktrees-2026-09-20/`(含 `MANIFEST.md` 与 `sha256.txt`), 目录已移除(5 个进回收站, `auto-qb-other` 因回收站报"不支持该功能"改移到存档区 `_removed-dirs/`), 8 个本地分支已删除 —— 删除前已核验全部 `ahead=0`, 无独有提交。新布局为 `D:/Projects/auto-qb`(主) + `auto-qb-clone1` / `auto-qb-clone2` / `auto-qb-long-seeding`。
- **`想法.md`**: 工作区**干净**(最后一次入库 `3bface9`)。它属于红线文件(与 `config.yml` / `auto-qb-data/` 同级), 提交前照例用 `git status --short` 确认一遍是否又有改动, 不进暂存区。

## 下一步候选 (来源: `想法.md` 待办 + progress.md 规划中)

- **上轮复核的收尾**(见「正在进行」第 ① 条) —— 只剩报表 §08 第 7 项(节拍对齐, **需先拍板方向**)
  与同类端点的同样改法(低优先); 第 1、2 批与 §11 已实施未提交
- WEB UI: WebSocket 推送; 多用户; **设置页全面重构**(`想法.md` 现存最大一条未做项)
- WEB UI: 窗口日志等级可选; 星图侧补齐第九轮的纯版式项(棱镜已做: FX-05/06/09/17~25)
- 规则系统: 条件取反 (`!`/非 logic); 重新梳理 ignore_next_action_error / stop_following_rules_if
- tracker 分组前端增强 (阶段 2/3, 2026-09-15 拍板后续): 设置页 groups 下拉快捷追加 (rules_ref 风格); 辅种管理页按组筛选 (web_view 透出 conf.groups + app.js filterDefs)
- 其它: 切分大文件; 种子未变动时不触发内置维护任务; 版本管理; 命中限速曲线强调显示; 插件系统
- 🚧 实机验证: README 标注 🚧 的功能 (alpha 阶段), 生产使用前先 `--dry-run` 观察

## 历史归档 (已迁出本文件)

2026-09-14 ~ 2026-09-19 的全部会话纪要已按专题迁移到 [tasks/](tasks/_index.md) 各档案的"历史会话纪要 (原文归档)"段 (原文未删改), 或已沉淀进 [progress.md](progress.md) 的「已实现」段。需要回查历史请走 `tasks/_index.md` 定位专题档案, 本文件只保留**当前焦点**。
