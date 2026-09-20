# 26-09-20-webui-decoupling — 主循环 × WebUI 解耦(门面 + 状态内聚)

**Status:** Completed (代码已提交并推送 Gitee `5691c6f`; 剩用户真机走查(用户侧) + 兼容层清理择机)
**Started:** 2026-09-20
**Owner:** 主线 (单会话连续实施)
**Plan doc:** [docs/plans/26-09-20-0234-webui-decoupling-plan.html](../../docs/plans/26-09-20-0234-webui-decoupling-plan.html)
**Summary:** QbManager 主循环里揉进了表现层的状态与节拍判据(19 个 Web 字段平铺在 `__init__`, 主循环替表现层做"要不要重建 / 要不要补刷新"的决策)。用 **门面(Facade)+ 空对象 + 沿用命令模式** 把状态与判据整体收进 `web_runtime.WebUIRuntime`, 主循环只剩四条语义调用; 行为逐条等价, 不引入新契约。**1055 → 1057 passed**(Windows) / **1055 + 2 skipped**(Linux WSL 沙箱), cov 92%, 红绿双验过; 浏览器冒烟已跑: ok / error 双模式各 **48 项 0 失败**(3000 种子桩服务, 双 UI, 当时脚本版本) —— 同日脚本扩项后复跑为 **54 项 0 失败**(见进度日志 04:10 与验收段)。

## 原始请求

> 目前的 qbmanager 主循环结构复杂, 融合了 webui 的逻辑, 需要拆分, 使用合适的设计模式将 webui 抽离出来, 抽象? 分析可行性, 给一份修改计划, 如果可行, 按计划执行

用户同时授权"可行即按计划执行" —— 本档案覆盖可行性分析 + 计划 + 实施全过程。

## 思考过程与决策

**诊断**: 耦合的性质是「**状态与门控**」耦合, 不是「控制流」耦合 —— Web 侧从不通写路径, 只投递
命令 + 只读快照, 边界对象早就存在(命令队列 + 视图快照), 只是边界两侧的字段被平铺在同一个 `self` 上。
这是两次增量改动叠出来的结果: 2026-09-15 拆 mixin 时**方法搬走了、状态没跟着搬**; 2026-09-19
三波跟手性优化又把命令唤醒 / 补刷新 / 节拍对齐三套门控就地写进了循环体。症状是想理解一次 tick
做了什么, 得同时读 `run()` / `_flush_views()` / `_task_line()` 三处, 并在脑子里把 Web 分支剔掉。

**为什么可行**: ①主循环里 Web 调用点只有 6 处且集中在 `run()` 一小段; ②19 个字段在 `__init__`
里连成一片(102 行中的约 60 行), 可整块搬; ③既有守阵(分层节拍 / 命令唤醒 / 节拍对齐)直接覆盖改动面。

**选型 —— 采用**: 门面(唯一能做到"主循环里不再出现 Web 判断"的结构: 把状态与判据一起收走)+
空对象(`is_active()` 未启用恒 False, 消除 `if web_enabled` 分支)+ 命令模式(沿用既有队列, 不新造)+
单向置脏(核心域 `web.mark_dirty()`, 依赖方向反转 —— 原先是直接写 `self._group_view_dirty`)。

**选型 —— 否决**:

| 否决 | 理由 |
|---|---|
| 事件总线 | 同步回调等价于直接调用, 只增加不可读的间接层; 对"单一写线程"无额外增益(约束靠的是队列不是总线) |
| MVC / MVP 全套 | 视图是 JSON 快照而非控件树, Presenter 的"更新控件"语义落空; 现有「主循环产快照 / Web 线程只读 / 按 rid 整表替换」本就是 Passive View 变体 |
| 独立进程 / RPC | 直接违反黄金法则第 5 条(单一写线程); 配置热重载还要跨进程同步 |
| 阶段管道注册表 | 钩子只有 2 个, 注册机制是过度设计, 且循环执行顺序不再能从上往下读出来 |

**刻意不搬**: `wake()` / `_wake_event` 留在核心域 —— 托盘 UI(`ui.py:507`)停止时也用它打断等待,
它是主循环的唤醒原语, Web 只是使用方之一。

## 实现计划

| 波次 | 内容 | gate |
|---|---|---|
| W1 | 新建 `web_runtime.py`: 19 个状态字段 + 全部节拍判据 + 门面方法(状态先落, 编排暂留 mixin) | 模块可导入, 无新增失败 |
| W2 | `web_view.py` 降为纯构建器(快照/版本/锁/索引全部改走 `self.web.*`); `web_commands.py` 降为命令处理器 + 命令表; `speed_curve.py` 直连 `web.traffic_view` | 1055 passed |
| W3 | `run()` 6 处调用 → 4 个门面方法; 删 `web_active` 判据与 `CMD_SLOW_MS` 计时块; 移除 `_flush_views` | 三条结构守阵绿 |
| W4 | 兼容层: `_WEB_STATE_ALIAS`(19 字段读写转发)+ 8 个入口转发; `web.py` 的 `_enqueue` 改走 `web.post_command`; 新增 2 条守阵 + 改 3 处既有守阵目标 | 1057 passed, 红绿双验 |
| W5 | 知识库回写 + 立档(modules / systemPatterns / testing / activeContext / 本档案) | 文档与代码一致 |

## 子任务状态表

| 子任务 | 状态 | 备注 |
|---|---|---|
| W1 `web_runtime.py`(457 行) | ✅ Done | 含状态、门面方法、命令编排、视图发布 |
| W2 mixin 降为构建器 / 处理器 | ✅ Done | `web_view` 741→645; `web_commands` 730→545 |
| W3 主循环收敛 | ✅ Done | 4 条门面调用, 无 `web_active` 分支 |
| W4 兼容层 + 守阵 | ✅ Done | 2 条新守阵, 红绿双验过 |
| W5 知识库回写 | ✅ Done | 基线数字已更新为 1057 / 1055+2 |
| 浏览器冒烟 `ui_smoke.cjs` | ✅ Done | ok / error 双模式各 **48 项 0 失败**, 与改动前 A/B 同数 |
| 用户真机走查 | ⬜ 未做 | 观感类, 需真实 qB 数据 |
| 兼容层清理(删别名表与转发) | ⬜ 择机 | 调用方全改新名后再做 |

## 进度日志

- **2026-09-20 02:34** — 拉取主线(工作区干净, 快进), 基线 **1055 passed**; 统计耦合面:
  `__init__` 102 行中 19 个表现层字段、`run()` 146 行中 6 处 Web 调用 + 3 处门控、
  `web.py` 反向引用 18 处、测试引用内部字段 200+ 处。产出计划文档(HTML, docs/plans/)。
- **02:45** — W1 落地 `web_runtime.py`; W2 批量改写两个 mixin 的状态访问(正则替换 + 删除迁走的方法块)。
- **03:00** — W3 主循环收敛; 首轮全量 **6 failed / 1049 passed**。失败集中在: 守阵打桩打在转发层、
  静态守卫正则失效、自投递 payload 多出埋点键、`_log_cmd_timing` 宿主变了。
- **03:10** — 逐条修完 + W4 兼容层 ⇒ **1055 passed**; 追加 2 条守阵 ⇒ **1057 passed**(cov 92%);
  红绿双验(注入 `self._group_view = []` ⇒ 守阵报 `['_group_view']`, 还原后绿)。
- **03:20** — Linux WSL 沙箱复跑: **1055 passed + 2 skipped**(与 Windows 收集数一致)。
- **03:30** — W5 知识库回写 + 立档; 机械守卫 `test_memory_bank.py` 先红(Status 取值 + 必备章节), 已补齐。
- **04:10** — **浏览器冒烟补齐**: 装 chromium + 复用 workspace 里的 playwright-core 1.62.0,
  起 3000 种子桩服务(**端口换 8231/8244 —— 8123 已被别的 worktree 桩服务占着**, 起之前先扫端口)。
  ok / error 双模式各 **48 项 0 失败**。
  ok 模式有一条 `[perf]` 提示「3000 目标撤下 3073ms(>2500ms 属异常)」⇒ **A/B 对照澄清**: 用
  `git archive HEAD src` 提取改动前代码到临时目录 + `PYTHONPATH` 前置跑同一场景, 得
  **3072 / 3049ms** —— 同一现象(大库轮询粒度), 非本次引入。**未提交。**

## 关键决策与偏差(相对计划)

- **保留兼容代理, 而不是改 200+ 处测试引用**: 代理只转发不存值(不存在两份真相), 由
  `test_web_state_alias_proxies_to_runtime` 钉死; 生产代码 `web.py` 也因此零改动。
  代价是 `qbmanager.py` 多了一层"魔法", 收益是回归风险大幅下降 —— 另配静态守阵防回潮。
- **`advance_slow_paths` 未合并**: 计划写"错误原因预取与搜索索引合并为一次调用", 实施拆成
  `advance_error_reasons()`(任务线开头)与 `advance_search_index()`(末尾)—— 合并会把索引构建提前到
  `run_due` 之前, 大库首轮会推迟任务执行。宁可多一次门面调用, 也要保时序等价。
- **主循环走新名、转发方法留给既有调用方**: 因此 `test_wake_drains_commands_without_extra_ticks`
  的 monkeypatch 目标必须改成 `mgr.web.consume_commands`(判据不变, 只换目标)。
- **web.py 只改 `_enqueue`**: 字段访问全改会连带要求重写 `test_web.py` 的 SimpleNamespace 替身,
  风险大于收益; 命令投递归口到门面已经消除了重复的 SELF_POSTED 判据。

## 踩到的坑

1. **静态守阵因重构而失效**: 自投递守卫正则原本只认 `web_commands.put(("…`, 改走 `web.post_command("…")`
   后匹配为 0 ⇒ `assert posted` 失败。守阵必须跟着代码走(已扩到两种写法都认)。
2. **自投递 payload 形状**: 给自投递也加 `_queued_ts` 破了两条 `payload == {}` 断言; 自投递没有回执
   消费者, 埋点是死重量 ⇒ 自投递只 put 原样 payload。
3. **打桩打在兼容层上会假绿**: 回执顺序守阵原本 spy `mgr._set_web_result`, 而门面内部调自己的
   `set_result` ⇒ spy 完全不生效。表现为**断言静默失效**而非报错 —— 这类问题只能靠"改完必跑"发现。
4. **`__getattr__` 递归防护**: 别名表里不含 `'web'`, 故 `self.web` 未建立时访问别名直接抛
   `AttributeError` 而非无限递归 —— 别名属性只在 `self.web` 建立之后可用。
5. **知识库机械守卫**: `Status` 只能取 `In Progress|Pending|Completed|Abandoned`; 任务档案必须含
   五个必备章节(原始请求 / 思考过程与决策 / 实现计划 / 子任务状态表 / 进度日志)。写中文状态会直接红。

## 验收

- Windows `uv run pytest tests -q` **1057 passed**, cov 92%; Linux WSL **1055 + 2 skipped**(收集数一致)
- 三条结构守阵全绿: 分层节拍 / 命令唤醒只走命令线 / 节拍对齐(上一版没被取走就不生产下一版)
- 新增 2 条: 静态防回潮(红绿双验过)+ 代理同源(读同一对象 / 写双向可见)
- **浏览器冒烟**: ok / error 双模式各 **48 项 0 失败**(3000 种子桩服务, 双 UI); 改动前 A/B 同数
  ⇒ 无回归。唯一 `[perf]` 提示(3000 目标撤下 3073ms)经 A/B 证明改动前即为 3072ms, 属大库轮询粒度
- **2026-09-20 10:20 复跑(脚本已扩项至 54 项; 提交前又 rebase 到 `4df80dc` 之上复跑一次, 数字不变)**:
  ok / error 双模式各 **54 项 0 失败**(3000 种子, 双 UI); 单测 **1058 passed / cov 92%**。
  环境确认 `playwright-core@1.62.0` + `chromium-1234`, 需带 `NODE_PATH` 指向托管 node workspace。
  `perf` 提示每轮 3 条:「3000 目标撤下 3081/3088ms」(同前, 非回归) + 「补丁 2033/2407ms、
  POST 2090/2475ms」(均为 **3000 目标**的批量命令, 补丁仍早于 POST 顺序无误)。
  ⬜ **该「补丁 2s」已定性并入池** —— 受控探针实测是 `applyOptimistic` 的
  **O(目标数 × 数据集规模)**(逐 hash 调 `_forEachRow` 线性扫三张全表), **不是抖动**:
  数据集 3000 时 100/500/1500/3000 目标 = 64 / 315.7 / 1036.3 / 2146.7 ms, 数据集 300 时
  100/300 目标 = 9.4 / 23.7 ms(单目标成本随库大小等比放大)。改动前 1693ms 同量级 ⇒ 非本次引入。
  详见 issue [26-09-20-1033-perf-webui-optimistic-patch-quadratic](../issues/26-09-20-1033-perf-webui-optimistic-patch-quadratic.html)
- **03:40** — 提交并推送: 提交前 `git pull --rebase origin develop` 撞上上游 `03ed9ed`
  (撤下加 via 路径标记 + 真值不一致时直接采纳) —— 该提交是**并行提交**(不在我方历史里), 在
  `web_commands.py` 上冲突: 它给 `_flush_deferred_receipts` 加了真值计数 + 排查标记日志, 而该方法
  本次已迁进 `web_runtime.flush_receipts`。解法: **取其意图落到迁移后位置** —— 计数与日志写进
  `flush_receipts`, 上游重复出现的 `_defer_receipt` / `_affected_hashes` / `_log_cmd_timing` 三法
  与迁移版逐字等价故丢弃上游副本。解冲突后重跑全量 **1057 passed**。
  推送 `03ed9ed..5691c6f` → Gitee develop; 事后核对 HEAD == refs/heads/develop == `5691c6f`(ref 未被拦截层丢弃)。
- ⚠ 顺带修正: 先前记录的规模数字有误(写的是 `web_commands` 623→545 / `qbmanager` 795→808 /
  `web_runtime` +451), 实测基线 **730 / 816**, 迁移后 web_runtime **457** 行 —— 已在提交消息、
  activeContext、本档案三处一并订正。教训: 规模数字要在**提交那一刻**按 `git show HEAD^:<file> | wc -l` 实测,
  别沿用会话中途的量。

## 后续(择机)

- 兼容层清理: 调用方全部改 `manager.web.<新名>` 后, 删 `_WEB_STATE_ALIAS` 与 8 个转发方法, 同步调整 2 条守阵
- 视图构建器可进一步降为纯函数模块(脱离 mixin, 直接 `(store, config) -> dict`), 收益有限, 未排期
