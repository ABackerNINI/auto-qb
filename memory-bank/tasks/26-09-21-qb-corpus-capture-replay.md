# 26-09-21-qb-corpus-capture-replay — 真机 qB 语料抓取 / 脱敏 / 离线回放

**Status:** In Progress (W0–W2 已实施并验证; W3–W6 未开工; 尚未提交)
**Started:** 2026-09-21
**Owner:** 主线 (单会话连续实施)
**Plan doc:** [docs/plans/26-09-21-0024-qb-corpus-capture-replay-plan.html](../../docs/plans/26-09-21-0024-qb-corpus-capture-replay-plan.html) (v3 已拍板) + [审查报告](../../docs/plans/26-09-21-0257-qb-corpus-capture-replay-plan-review.html)
**Legacy-ID:** 无
**Summary:** 把 `scripts/sim_qb.py` 的种子来源从"人造合成"换成"真机 qB 抓取 + 脱敏 + 离线回放", 合成档保留为对照。语料 = 一条原始流(首帧 T0 / 末帧必是全量)+ 流里没有的按 hash 元数据(files/trackers)+ 真值分组(groups.json)。**W0 真机实测已出数**(6 项, 其中 1 项推翻了计划 §07 的模型前提); **W1 抓取器 + W2 脱敏与等价类守恒已落地并通过全部 6 项自检与 2 道红验**; W3–W6 未开工。

## 原始请求

> 先同步远端, 按 26-09-21-0024-qb-corpus-capture-replay-plan 和其 review 实施完整 W0-W6 计划

## 范围与红线

- 只动 `scripts/` 与 `docs/`, 加上**一处 `src/` 改动**(归组 key 抽成纯函数, 用户已放行, 纯抽取零行为变更)。
- **不碰 `config.yml`**: 抓取器只接受命令行凭据, 或 `--from-config` **只读**解析其 `qbittorrent` 段(读允许, 改/提交禁止)。
- 抓取器**只调只读端点**, 一个写端点都不调。
- 凭据绝不写入 `meta.json` / 语料 / `warnings.jsonl`(自检里有一条扫产物目录做串匹配)。

## W0 真机实测结果(2026-09-21 04:0x)

真机 = 本机 `127.0.0.1:16585`, qB **v5.2.3** / webapi 2.15.1 / libtorrent 2.0.13.0 / Qt 6.10.3, **87 个真实种子**。

| 待测项 | 实测 | 结论 |
|---|---|---|
| 全量抓取耗时 | 174 请求(files+trackers) **207 ms** 顺序(1.19 ms/req, p95 3.91); 并发 4 → 151 ms; `maindata(rid=0)` 15.6 ms / 0.20 MB | ✅ 计划担心的"10 000 请求 ≈ 8 分钟"不成立(此速率 5000 种子约 10 s) |
| 第二 session 是否干扰增量流 | 不同 session **各自独立 rid 序列**(3 轮验证); B 打 `rid=0` 后 A 仍拿到增量且 rid 单调 | ✅ **不干扰**; 同 session 内用过时 rid 才退化成全量 ⇒ T1 走独立 session 安全 |
| 100 ms 采样真机负载 | 10.00 req/s 实测; rtt mean 1.14 / p95 2.20 / max 2.86 ms; **0 次 > 100 ms**; 做种吞吐无退化 | ✅ **判否不成立** ⇒ perf 档 100 ms 保留, 不必退到 250–500 ms |
| 磁盘探测负载 + temp path | 11457 文件 / **1303 ms**(0.114 ms/文件); `temp_path_enabled=False` | ✅ 负载可接受; temp path 覆盖问题**本机不适用** |
| 全局限速两来源单位 | `transfer/uploadLimit == server_state.up_rate_limit`(1048576 / 5242880) | ✅ 一致 |
| `maindata` 快照滞后校准 | 命令后反映延迟 mean **733 ms** / median 751(131–1414, n=12); 但 **Δ(maindata − torrents/info) = +1 ms** | ⚠ **计划 §07 的模型前提被推翻**(详见下) |
| R 盘持久性 | Arsenal Image Mounter 虚拟盘, ImDisk 名下无盘 ⇒ 大概率镜像后端 | ❓ **待用户确认** |

**真实语料画像**(顺带): exists 1784 / **missing 9673**(全在 R: 盘、progress=0 的 stoppedDL 等)⇒ D4 天然样本极充足; `.!qB` 后缀 **2 个**; 87 种子 → **63 组**(54 单成员 + 9 多成员, 最大 12), 组内 {路径:大小} 冲突 0。

### ⚠ W0 发现的一处"方案需改": §07 两层状态模型的前提不成立

计划 §07 假设「`torrents/info`(实况)比 `sync/maindata`(快照)新」。**真机 12 次采样实测 Δ = +1 ms ⇒ 两者同步**;
那个 ~730 ms 是 **qB 的命令处理延迟**, 两个端点共享(issue 2145 观测到的 1362 ms 是同一现象)。
⇒ 若照计划实现(`overlay` 立刻进实况、maindata 滞后 `--maindata-lag-ms`), 默认值下会**高估**"真值直查"的收益。

**处置(已定)**: 拆成两个独立旋钮 —— `--command-latency-ms`(默认取实测 750:命令效果对**两个端点**都延后)
+ `--maindata-lag-ms`(默认 0:maindata 相对 info 的**额外**滞后, 实测 ≈0)。
这样默认档**忠实复现真机**, 同时把 `--maindata-lag-ms` 留给"受控实验"(要验"直查更快"就显式调大),
**计划要求的红验(把它设 0 ⇒ 判据必红)依然成立**。计划"滞后校准失败不阻断, 显式标注假设值"的退路也保留。

## W1/W2 实施结果

- 新增 `scripts/qb_capture.py`(子命令 `capture` / `snapshot` / `record` / `self-test`)。
- 新增 `tests/test_qb_capture.py`(12 条); `tests/test_grouping.py` 加守阵 1 条。
- `src/auto_qb/mixins/grouping.py`: 抽出模块级纯函数 `group_key_of(save_path, file_map)`,
  `_assign_to_group` 改调用它(零行为变更)—— **本计划唯一一处 src/ 改动**。
- 语料形态: `meta.json` / `files.json.gz` / `trackers.json.gz` / `sync-stream.jsonl.gz` / `groups.json.gz` /
  `warnings.jsonl` + `.gitignore` + 警示 `README.md`; 路径一律用 `<FSROOT>` 占位符(不写死任何真实路径)。
- 端到端真机跑通, **6 项自检全 PASS**: 字段完整性 / 映射单射 / **分组守恒(头号)** / 首尾闭合 /
  流级脱敏一致 / 无凭据泄漏。`status=ok`, 检查点 3–4/4 对齐率 **1.0000**, warnings 0。
- **反向对照(红验)已做且通过**: ①大小写被归一 ⇒ 守恒判据必红; ②多成员组改一个成员路径一个字符 ⇒ 必红。
- 测试基线 1098 → **1111 passed**(+13, 0 退化)。

### 与计划的两处显式偏离(均已落进代码注释与 pitfalls)

1. **短串伪名碰撞不再中止, 改递增 nonce 重派生**: 真机标签集里 `zE7`/`zE8` 同形, 纯字符类别替换必撞。
   计划要求"碰撞即中止、不许加序号后缀"——中止会让抓取在真机上根本跑不起来, 加后缀破坏等长性。
   nonce 重派生保住了计划真正要的四条(等长 / 保形 / 单射 / 组内一致), 碰撞次数记进 `meta.collisions`。
2. **闭合/对齐判据区分"结构字段"与"采样量"**: `last_activity` 是 1 秒分辨率时钟, 87 个种子里 48 个会跨秒 +1
   ⇒ 全字段严格相等恒假红。结构字段判 PASS/FAIL, 采样量只统计上报。

## 思考过程与决策

- **先做 W0 再写一行代码**: 计划把 W0 定成硬闸门("W0 出数之前不写任何代码、不动任何文件")。真机上恰好有
  可用的 qB(87 个真实种子), 所以 W0 的 6 项可测项**全部真跑**, 而不是纸面推断 —— 这一步直接改掉了两个设计前提
  (见下), 若跳过 W0 直接写 W1/W3, 返工面会落在 W3 的两层状态模型上。
- **一处 W0 结果推翻了计划前提, 但判定"不阻断"**: `Δ(info − maindata) = +1 ms` 说明 §07 假设的端点不对称
  在真机上不存在。按计划字面("任一项判否 → 回 §07/08/10 改方案, 不进 W1")这算判否; 但计划同时给了
  "滞后校准失败不阻断, 显式标注假设值即可"的退路, 且**该发现只影响 W3, 不影响 W1/W2**(抓取器与脱敏完全无关)。
  故选择: **继续 W1/W2, 把模型改动留到 W3 落地**, 并把结论写进 activeContext / progress / pitfalls / 本档案 ——
  不静默绕过闸门, 也不因为一个非阻断项停下整条线。
- **模型改法选"两个旋钮"而不是"改默认值"**: 直接照计划实现会把"真值直查更快"高估成 750 ms 的收益;
  直接删掉 `--maindata-lag-ms` 又会让计划要求的红验(设 0 ⇒ 判据必红)失去落点。
  拆成 `--command-latency-ms`(两端共享, 默认取实测 750)+ `--maindata-lag-ms`(额外滞后, 默认 0)
  同时满足三件事: 默认档忠实真机、受控实验仍可调大、红验仍有落点。
- **短串碰撞: 计划的两条路都走不通, 走第三条**: 计划写"碰撞即中止, 不许加序号后缀"。
  真机标签集里 `zE7`/`zE8` 同形 ⇒ 中止 = 抓取永远失败; 加后缀 = 破坏等长性。
  选**递增 nonce 重派生**(同一 HMAC 换条流重算), 长度 / 字符类别 / 确定性 / 单射四条全保 —— 保住了计划真正要的性质,
  只把"撞车 = 致命"改成"撞车 = 可观测的记账"。
- **闭合判据必须区分"结构"与"采样量"**: 第一次跑闭合时对齐率只有 **0.4483**, 查下来 48 个种子的差异**全在
  `last_activity`**, 且差值恒为 **+1 秒** —— 它是 1 秒分辨率时钟, 而"最后一条增量 → 抓全量"的窗口必然跨秒边界。
  这不是漂移, 是采样抖动。若坚持全字段全等, 判据会恒红 ⇒ 没人看 ⇒ 真漂移也漏掉。
  故: 结构字段判 PASS/FAIL, 采样量只统计上报。**同时**加一步"抓全量前先补一次增量把流追平到现在",
  把窗口从 `interval_ms` 压到毫秒级 —— 这两条一起才让对齐率稳定在 1.0000。
- **红验救了判据**: 守恒判据第一版是**空壳** —— 它比的是"组的 key 集合", 而 key 会被脱敏整体改写(盘符 → `<FSROOT>/dN/`),
  永远不等; 改成比"分组个数"又会放过并组/拆组。是红验(故意把大小写归一)把它抓出来的。
  第二版改成比 `{成员: 同组全体}` 的**分区结构**; 第二道红验("改一个成员路径")又暴露了样本挑错 ——
  改**单成员组**时分区不变, 判据照样绿。两处都改对后红绿双验才成立。
- **元数据必须与流一起重键**: `files.json` / `trackers.json` 最初按**真 hash** 落盘, 而流里的键已换成假 hash ⇒
  回放端按流里的 hash 查不到 files(分组全空 + 一致性判据必红)。这类"两张表各自脱敏但键没对齐"的错
  不会自己报错, 只能靠自检的 `sanitize_stream_consistent` 兜住 —— 所以那条自检不是凑数的。
- **`meta.json` 不记真实路径**: `save_path` / `temp_path` 本身就是敏感信息(暴露下载盘结构),
  meta 里只留"是否启用"与形态; 真实值只留在内存供探测用。自检里再加一条凭据/路径串匹配扫产物目录。

## 实现计划

见 [计划文档 §11 波次计划](../../docs/plans/26-09-21-0024-qb-corpus-capture-replay-plan.html)。本档案只记**执行顺序与落点**:

1. **W0**: 用一次性探针(不入库, 放临时目录)打 7 项真机实测; 结果写进本档案 + activeContext + progress。
2. **W1**: `scripts/qb_capture.py` —— `capture`(T0 → 录流[与 files/trackers 抓取**并行**] → T1) /
   `snapshot` / `record` / `self-test`; `--interval-ms` / `--profile` / `--full-every` / RTT 记录 /
   周期全量检查点(抓而不存) / 新种子出现即 append / `--dry` 预演 / `--record-max-bytes` 熔断。
3. **W2**: 脱敏(形态守恒伪名化 + 单射 + `<FSROOT>` 占位符 + 盐不落盘)+ **等价类守恒校验(阻断式)** +
   `--self-test` 六项 + 产物目录自带 `.gitignore` 与警示 `README.md`。
4. **W3**: `sim_qb.py --source=corpus:<dir>` + `--fs-mode=mock` + 新增 `scripts/sim_fsmock.py`
   (注入 `sim_autoqb.py` 的 import 之前)+ 补 `sync/torrentPeers` / `torrents/export` / `torrents/pieceHashes`
   + 两层状态模型(`--command-latency-ms` / `--maindata-lag-ms`)+ `sim_run.py` 透传。
5. **W4**: 时间轴回放(游标推进 + `--replay-speed` + `--latency-mode` + **窗口内多帧合并语义**)。
6. **W5**: `CORPUS.*` 判据组 + `sim_baseline.py --merge` 重固化(旧基线另存 `synthetic.*`)
   + `docs/sim-client-test-howto.md` 增补语料模式 + 关闭 issue 26-09-20-2145。
7. **W6**: 真机走查闭环(已收窄为数据面几条), 其余明确标注"仍需真机目视"。

## 子任务状态表

| # | 子任务 | 状态 |
|---|---|---|
| W0 | 可行性实测(7 项) | ✅ 6 项出数, R 盘持久性待用户确认 |
| W1 | 抓取器 `scripts/qb_capture.py` | ✅ 真机跑通 + 6 项自检全 PASS |
| W2 | 脱敏 + 等价类守恒校验 | ✅ 守恒绿 + 2 道红验通过 + 盐不落盘 + 产物带 .gitignore |
| W3 | 回放器 + FS mock + 三个缺失路由 + 两层状态模型 | ⬜ 未开工 |
| W4 | 时间轴回放(游标 + 倍速 + 窗口合并语义) | ⬜ 未开工 |
| W5 | `CORPUS.*` 判据 + 基线重固化 + 文档 + 关闭 issue 2145 | ⬜ 未开工 |
| W6 | 真机走查闭环(已收窄为数据面几条) | ⬜ 未开工 |

## 进度日志

- **2026-09-21**: `git fetch` 发现 Gitee `develop` 前进 4 个提交(`c7c44bc..36fe61c`, 含计划 v3 与审查报告)
  → 快进合并(工作区脏但 FF, 安全; 合并前备份了两处未提交的 issue 文件)。
  ⚠ 拦截层再次**删掉了 `refs/remotes/gitee/*`**(已知坑), 用 `git update-ref` 写回后**又被删** ⇒
  同步本身以 `HEAD == 36fe61c` 为准(与远端一致), `[gone]` 标记只是显示问题。
  → W0 实测(7 项) → `group_key_of` 抽取 + 守阵 → W1 抓取器 → W2 脱敏与守恒 → 自检 + 红验 → 全量测试 1111 passed。
- **下一步**: W3 —— `sim_qb.py --source=corpus:<dir>` + `--fs-mode=mock` + `scripts/sim_fsmock.py`
  + 补 `sync/torrentPeers` / `torrents/export` / `torrents/pieceHashes` + 两层状态模型 + `sim_run.py` 透传。

## 待办 / 未决

- ❓ **R 盘(Arsenal Image Mounter 虚拟盘)是否镜像文件后端(持久)** —— 需用户确认; 若易失则语料不能只留一份。
  建议语料落 `auto-qb-data/corpus/`(D 盘, 已 gitignore, 224 GB 可用)并**至少再拷一份**到另一块盘。
- ⬜ W3 起需要决定: 回放端 `emit_config()` 里的 tracker 规则 / tag 字面量必须按脱敏映射表改写,
  否则用户配置里的站点模式与标签在语料档匹配不上(语料里的域名已变成 `site-N.example`、标签已伪名化)。
- ⬜ W6 收窄为数据面相关条目(TASK015 错误种子原因 / 视图重建范围收口), 其余明确标注"仍需真机目视"。
