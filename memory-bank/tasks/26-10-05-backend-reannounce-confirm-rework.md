# 26-10-05-backend-reannounce-confirm-rework — 强制汇报确认机制重构实施

**Status:** Done
**Added:** 2026-10-05
**Updated:** 2026-10-05 12:02
**Topics:** backend-reannounce-confirm-rework
**Summary:** 按实施计划 26-10-05-0923 落地强制汇报确认重构(epoch 前跳证据门控)并完结: 判定提为纯函数 `_verdict_reannounce` 五分支(④先于②③判防 status4 重试排程假前跳误判成功; ②min 窗口守卫防推迟假瞬态; legacy 按行推断), baseline 形状 {status,updating,next,min}+epoch_mode, item 级 deadline=t0+max(30,min_e−t0+15) capped 600, 注册直判停止/推迟(>25s), runtime check_pending 三桶聚合+warn 回执+reannounce_background 后台核实(上限 500 丢最旧), 前端 _pollCmd warn 终结+三桶分流+sticky 文案, delete_flow 保守口径(warn 不放行删除); S0 探针三点实证(前跳 +5466s / TOL=3.0 维持 / min_e+1 冻结); test.full 2610 passed + 4 skipped / 覆盖率 98%(切片 26-10-05-1202); 计划外发现三项只记录未入池(endpoint status=6 不扰顶层聚合 / commands.js wait_ms 段缩进不齐 / waitCmd 其它消费方不受 warn 影响)。
**Refs:** memory-bank/plans/26-10-05-0923-plan-reannounce-confirm-rework.html,memory-bank/reports/26-10-05-0854-report-reannounce-confirm-api.html,memory-bank/testing/baselines/26-10-05-1202-reannounce-confirm-rework.md,memory-bank/pitfalls/backend/announce-epoch-semantics.md

## 原始请求

> 用户确认实施计划 [26-10-05-0923](../plans/26-10-05-0923-plan-reannounce-confirm-rework.html)(认领调研报告 [26-10-05-0854](../reports/26-10-05-0854-report-reannounce-confirm-api.html) 的后续落地轮), 逐项拍板 D1-D5 后下达实施指令; 分支 `feat/reannounce-confirm-rework`。首轮(T1)范围 = 拍板结果回写计划 + 立实施档案 + S0 真机只读探针; S1-S5 代码实施按计划推进。

## 思考过程与决策

- **D1 推迟路径 = 早回执 + 后台日志核实**(采纳推荐): 推迟路径检出即回「已受理: 推迟至 HH:MM」并移出回执跟踪, 后台在预计发送时刻后核实一次、只落日志。
- **D2 主判据 = TOL=3.0s + 语义(b)**(采纳推荐): 确认窗口内 tracker 收到新鲜汇报即成功; S0 探针复核 —— 实测前跳 +5466s ≫ 3.0s, **TOL=3.0 维持**(立即路径前跳按机制 ≥ tracker min_interval, 分钟级量级, 3.0s 余量充分)。
- **D3 版本闸门 = 字段存在性探测**(采纳推荐): 基线读时判 trackers 行有无 `next_announce` 键 → epoch/legacy 模式, 不调 `app_web_api_version`。
- **D4 = 偏离推荐, 取备选「新增 warn 状态」**(所有者选 warn 三值, 弃二值 ok/error + 前缀分流)。牵连改动面(计划 §3.4/§04/§05/§06 已按此口径改写): ① 前端 `_pollCmd`(commands.js:131) 终结条件纳入 warn; ② SSE 事件路径核对放行 warn; ③ 相关静态守阵同步; ④ 回执 status 列: 已确认→ok / 失败→error / 已受理·推迟→warn / 未确认·停止→warn / 未确认·超时→warn; ⑤ 聚合回执 status 规则: 任一 item error → error, 否则任一 warn → warn, 全 ok → ok; ⑥ toast 类型映射: ok→success 型 / error→error 型 / warn→timeout 型(复用现有 toast 类型); ⑦ 三个前缀常量保留作文案(人类可读), 机器分流依据从「前缀」改为「status」。
- **D5 = 非目标**(采纳推荐): 规则侧 `rules/actions/transfer.py` 本轮不动。
- **S0 = 用户确认现在跑真机探针**: 只读采样 + 计划 S0 范围内的 force reannounce 各一次, 数字回填本档案; 探针脚本放系统 TEMP 不入库。

## 实现计划

单点: [plans/26-10-05-0923](../plans/26-10-05-0923-plan-reannounce-confirm-rework.html)(§03 目标行为设计 / §04 分步实施 S0-S5 / §05 测试计划 / §06 风险与回滚)。

- **S0** 真机只读探针: ① 未联系行 `next_announce` 序列化值; ② 立即路径前跳幅度与 updating 窗口时长; ③ 推迟路径 next/min 同值冻结与 min_e 后同值移动。
- **S1** 判定核心重构(`webui/commands.py`): 常量组(含 REANNOUNCE_JUMP_TOL=3.0) + baseline 形状 `{status, updating, next, min}` + epoch_mode + `_verdict_reannounce` 纯函数 + item 级窗口/推迟检出。
- **S2** 轮询状态机(`webui/runtime.py` check_pending): item 级 deadline + 停止种子直判 + 三桶聚合(§3.4) + `reannounce_background` 后台核实(上限 500)。
- **S3** 前端 reannounce 分支(`static/shared/commands.js`): sticky 文案 + 按 `r.status` 三桶聚合与 toast 映射 + `_pollCmd` warn 终结(D4=warn 牵连) + SSE 放行核对 + 静态守阵同步; waitCmd 40s 上限不变。
- **S4** 测试守阵(`tests/test_web.py`, 用例清单见计划 §05, 含状态与前缀双契约)。
- **S5** 收尾回写(坑档 announce-epoch-semantics / effect-confirmation 锚点更新 / kb.index / test.full 基线)。

## 子任务状态表

| 步骤 | 内容 | 状态 |
|---|---|---|
| 拍板 | D1-D5 逐项确认(所有者) | Closed(D1/D2/D3/D5 采纳推荐; D4 取备选 warn) |
| 拍板回写 | 计划 v2: §01/§3.1/§3.3/§3.4/§04 S2·S3/§05/§06/§08 | Done |
| S0 | 真机只读探针 | Done(①无未联系行可采样; ②前跳 +5466s, TOL=3.0 维持; ③min_e+1 冻结→同值移动) |
| S1 | 判定核心重构 commands.py | Done(8873c889: `_verdict_reannounce` 五分支纯函数 + baseline {status,updating,next,min}+epoch_mode + item 级窗口/推迟检出) |
| S2 | 轮询状态机 runtime.py | Done(8873c889: item 级 deadline + 停止/推迟直判 + 三桶聚合 + reannounce_background 上限 500) |
| S3 | 前端 reannounce 分支 commands.js | Done(04b5899f: _pollCmd warn 终结 + SSE 透传 status + 三桶分流 + sticky 文案; waitCmd 40s 不变) |
| S4 | 测试守阵 test_web.py | Done(随各棒落地: 新增 9 重写 3 + min 窗口守卫加码, 净增 +7; T4 核验首跑即绿零涟漪) |
| S5 | 收尾回写 | Done(坑档 announce-epoch-semantics + effect-confirmation 锚点 + 计划 Done + 基线切片 26-10-05-1202 + kb.index/docmap + progress 登记) |

## 进度日志

- **2026-10-05 10:07** 拍板结果回写计划(meta doc-updated 26-10-05-0923 · §08 加 v2 行, 状态保持 Open 待 S5 收尾): §01 拍板点表加「拍板结果」列 + D4 拍板记录 callout(D4=warn 牵连面全列); §3.1 判据⑤ / §3.3 聚合流 / §3.4 回执契约表(status 三值 + 聚合规则 + toast 映射, 前缀改文案)按 D4=warn 改写; §04 S2③ 聚合 status 规则与 S3 改动清单(新增④ _pollCmd warn 终结 / SSE 核对 / 守阵同步)同步; §05 超时回执(warn)/推迟早回执(status=warn)/组聚合三桶(按 r.status 计数)/「前缀契约」扩为「状态与前缀双契约」; §06 R4 双侧契约。本档案立档(In Progress), Refs 双向: 计划 + 报告(报告 doc-refs 已补反向声明, 链闭环)。
- **2026-10-05 10:26** S0 真机探针完成(脚本放 `H:\Temp` 不入库, `uv run python` 跑; 只读 + 2 次 force reannounce, 计划 S0 范围内; 连接信息只读自 config.yml, 未动 config.yml / auto-qb-data / git):
  - **连通性**: qB `v5.2.3` / WebAPI `2.15.1`(≥2.13.0 闸门通过), 127.0.0.1:16585; 做种 80 个全扫描, real tracker 行 80 行(每种子 1 行), 全部 status=2。
  - **① 未联系行**: **无 status<2 行可采样**(80/80 均 working, 不阻塞)—— 未联系行 epoch 极值序列化值未证得, 判据③「基线 status ≥ 2」守卫按计划保留(无反证)。
  - **② 立即路径**(btschool 单 tracker, min 过期 5395s): 基线 `next=1791168212 / min=1791161189 / status=2 / msg=""` → call+0.91s `updating=True, next=min=1791166585`(发送态瞬态, ≈call+1s) → call+3.03s `next=1791173678 / min=1791166616`。**前跳 = new_next − baseline_next = +5466s ≫ 3.0s → TOL=3.0 维持**(min 同向前跳 +5427s 佐证); updating 窗口实测 ≈2.1s(报告估 ~0.5s 偏小, 2s tick 命中率比预估高); status 2→2、msg 恒空 —— 「已 working 种子唯一持久正向证据 = epoch 前跳」根因实证。
  - **③ 推迟路径**(hdtime 单 tracker, min_e − t0 = 112s): 基线 `next=min=1791166710` → call+0.91s 瞬态(`updating=True, next=min=1791166597`) → call+1.82s 起**冻结 `next=min=1791166711 = min_e+1`**, 冻结 ≥104s(t_rel 12.1s→116.23s 零变化) → min_e+~2.2s(t_rel 116.23)**next/min 同值移动**至 `1791168397`(resp+interval ≈ +1686s, 该站 interval==min_interval)。D1 机制实测成立: `min_e` 就是可靠的预计发送时刻, 冻结期 next==min 同值。实际发送时刻的 updating 窗口未被采样命中(2s 轻采样 + 密集段晚于移动点), 按口径记未完成, 判定设计不依赖。
  - **计划外观察(只记录, 不改不修)**: (a) 顶层 trackers 行是 **endpoints 聚合**——实测每行 7 个 endpoint(按本机网络接口, 全 bt_version 1), 顶层 next/min = 各 endpoint 最早值、updating = OR, 计划非目标「顶层够用」口径实测确认; (b) endpoint 级存在 **status=6**(msg「skipping tracker announce (unreachable)」), 不在 wiki 0-4 枚举内, 顶层仍聚合为 2 —— 判据④(status==4+msg)按顶层行判定不受扰; (c) 推迟路径 call+~1s 有 **~0.9s 的 updating=True 瞬态**(endpoint 发送态钉住所致)—— D1 早回执门控(min_e−t0>25s 不进轮询)遮蔽主路径; min_e−t0 ∈ (0,25] 的边界 item 若 2s tick 撞上瞬态会经判据②提前出「已确认」(实际汇报在 min_e+1 ≤ t0+26s 才发出, 若届时被拒则回执已出) —— 概率窄, 留给 S1 实现/S4 测试斟酌, 本轮不动设计; (d) hdtime msg="ook" 跨成功 announce 持续非空而 status=2 —— 佐证判据④必须 status==4 且 msg 非空, 只看 msg 会误判。
- **2026-10-05 11:14** S1+S2 落地(8873c889, 判定核心 + 轮询状态机一笔提交): 判定提为纯函数 `_verdict_reannounce` 五分支, **④先于②③判** —— 防 status4 行重试排程造成的 next 假前跳被误判成功(分支序偏离计划 §3.1 书面序, 判据集合一致); 判据②加 **min 窗口守卫**(基线 min 在未来时 updating 不作左证, 落地 S0 边界发现 c); legacy 模式按行推断(基线行无 next_announce 键 → ②/③′/④); baseline 形状 {status,updating,next,min}+epoch_mode; item 级 deadline=t0+max(30, min_e−t0+15) capped 600; 注册直判停止/推迟(min_e−t0>25s); runtime check_pending 三桶聚合 + warn 回执 + `reannounce_background` 后台核实(上限 500 丢最旧, 单写线程内)。server 侧核实: warn 零拦截 —— `/api/cmd/{id}` 原样透传, set_result/SSE 无状态白名单, 第三态只需前端放行。
- **2026-10-05 11:31** S3 落地(04b5899f, 前端一笔提交): `_pollCmd` 终结条件纳入 warn(D4 牵连, warn 回执不再挂死等待); `_cmdRecToResult` 透传 status(SSE 与轮询共用一出口); 聚合按 r.status 三桶分流(不再按前缀), 前缀常量只作文案; sticky 文案补推迟子句; waitCmd 40s 上限不变; **delete_flow 保守口径**(计划外拍板): warn 不放行删除 —— 推迟中的 announce 会随删除丢失, 私站 H&R 风险不可用回执语义交换, 文案诚实区分「未确认 ≠ 无事」。
- **2026-10-05 11:31** S4 核验(T4, 零文件改动): test.full **2610 passed + 4 skipped / 覆盖率 98%**(15705 语句 / 169 未覆盖) / pytest 30.53s, 首跑即绿零涟漪; §05 十一组用例全部落地(T2 棒新增 9 重写 3 + min 窗口守卫加码)。**基线口径注记**: 上一条 2581+4 基线实测于另一 clone(feat/hr-steady-throttle @ 9f096c09), 跨 clone 树漂移 22 项, 本计划净增 +7(test_web.py +8 新 −1 删 +2 原位重写), 同树覆盖率 98.94%→98.92% 持平 —— 明细落切片 26-10-05-1202。
- **2026-10-05 12:02** S5 收尾回写(本会话, 文档棒): 新坑档 [pitfalls/backend/announce-epoch-semantics.md](../pitfalls/backend/announce-epoch-semantics.md)(「绝对时间被当倒计时」判据方向事故: 方向反转 + 证据门控 + S0 实证数字 + 两条瞬态守卫); effect-confirmation.md 范本区锚点 `_confirm_reannounce_result` → `_verdict_reannounce`(五分支 + warn 第三态); 计划 doc-status Open → Done(§08 加 v3 完成行, doc-updated 抬 26-10-05-1202); 基线切片 testing/baselines/26-10-05-1202(实测数字 + 增量构成 + 跨 clone 口径漂移注记); activeContext 新建 impl 切片 + plan 切片收口迁出; progress/implemented-webui.md 登记; `commands run kb.index` 重建 + `kb.docmap --check` 绿; 终态 `commands run test.full` 复绿(数字单点在切片)。**计划外发现(只记录, 未入池未修)**: ①endpoint 级 status=6 存在但顶层聚合为 2(判定不受扰, S0 观察 b 的存档); ②commands.js wait_ms 埋点段既有缩进不齐(scope-guard 范围外未动); ③前端 waitCmd 其它消费方回执只会 ok/error, 不受 warn 新增影响(核对结论存档)。
