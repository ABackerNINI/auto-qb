# 真机语料抓取 · 脱敏 · 离线回放 (W0–W6 详述)

> 摘要: 语料线 W0–W6 的完整实施记录与真机实测数字(首轮耗时 / rid 会话语义 / 归组规模 / 滞后校准)。
> 触发: 语料, 抓取, 脱敏, 回放, sim_qb, corpus, W0, W6, 真机实测

> 迁移说明(2026-09-22 W4): 原在 `activeContext.md` 的「正在进行」里, 单条就超主题文件的 10 KB cap ⇒
> 按「超了就外迁」整条移到这里, **内容逐字未改**。

- **真机语料抓取 · 脱敏 · 离线回放 —— W0 已出数, W1/W2 已完成(未提交), 下一步 W3**: 计划
  [docs/plans/26-09-21-0024-qb-corpus-capture-replay-plan.html](../../../docs/plans/26-09-21-0024-qb-corpus-capture-replay-plan.html)
  (v1→v3 原地修订) + 审查报告
  [docs/plans/26-09-21-0257-qb-corpus-capture-replay-plan-review.html](../../../docs/plans/26-09-21-0257-qb-corpus-capture-replay-plan-review.html)。
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
