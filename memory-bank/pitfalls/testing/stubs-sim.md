# 桩与仿真保真度

> 摘要: 测试替身"长得像"不等于"够用"; 仿真端最容易变成"自以为在测"的测假陷阱。
> 触发: 写替身, FakeClient, FakeTorrent, FakeQbServer, sim_qb, 仿真, 判据空壳, 反向对照, caplog, 日志断言, 回执判定, FakeConfig, 假配置, 新配置键

### `helpers.FakeConfig` 是**手写**桩: 真实 `Config` 新增字段时要同步补, 否则一批用例集体炸

- **触发**: 给 `Config` / 门面层(`QbManager.web` / `QbManager.hr` 等)加一个**构造期或热重载时会被读到**的字段
  (2026-09-24 M2 实测: `apply_new_config` 读 `config.hr_check` 与 `config.data_dir`)。
- **判别**: `tests/helpers.py::FakeConfig` 是**类属性式**手写桩(不是真 `Config`), 不会自动获得新字段;
  一旦真代码读它 ⇒ `AttributeError` **同一次跑里红一片**(实测 13 条跨 test_ui / test_qbmanager / test_web),
  报错信息是 `'FakeConfig' object has no attribute ...`, 很好认但很容易被当成"新代码写错"。
  同理还有那些**临时拼的 `SimpleNamespace(web=...)` 旧配置桩** —— 也得补。
- **处置**: 在 `FakeConfig` 里补一个**默认值等于真默认**的字段(默认关 / 默认空),
  让既有用例行为不变; 新字段的默认值**不要**随便选, 否则会让一批旧用例默默改行为。

### 测试替身的"成功路径"往往顺手把状态补全

- **触发**: 想测"动作成功但确认不到"。
- **判别**: `FakeClient.torrents_add` **无条件登记种子** ⇒ 靠"不预置"造不出该场景。
- **处置**: 必须在**替身动作之后**动手脚(子类化 + `super()` 后 `pop`)。

### 桩对象与真对象"长得像"不等于"够用"

- **触发**: 依赖替身覆盖某条链路。
- **判别**: `FakeTorrent` 缺 `to_dict()` ⇒ 详情端点**恒 500**, 于是
  **依赖详情的整条链路(详情抽屉 / 限速 / 分享率 / 移动 / 重命名 / 复制磁力)从未被冒烟覆盖**,
  且前端 catch 后**只弹 toast**, 断言看不到。
- **处置**: 加一条"**无 console.error**"断言, 并至少 GET 一次该链路。

### `FakeQbServer` 的出口必须可 JSON 序列化

- **触发**: 加替身端点。
- **判别**: 返回 `SimpleNamespace` ⇒ handler 内 `json.dumps` TypeError ⇒ 连接被**无响应关闭** ⇒
  客户端报 `APIConnectionError` 被主循环当**断连静默吞掉**(表现为"辅种分组永远为空")。
- **处置**: 出口只放可序列化类型。
  另: 桩服务的命令队列是 **2 元组** `(cmd, body)`, `cmd_id` 在 **body** 里。

### 桩服务"真的改状态"后必须**自愈**

- **触发**: 桩服务长驻跨轮。
- **判别**: 不自愈会让第二轮所有行都是 `paused`;
  **回弹必须是"真值被 `/api/state` 取走之后"再等 N ms, 不能是盲定时**
  (定时回弹会跑到前端观测之前把真值改回去)。
- **处置**: 判"已被取走"用 `_web_pending_ver` 被清空; 回弹记**最初**值(不是上次命令后的值)。

### 仿真端"自以为在测"的测假陷阱(写 `sim_qb.py` / `sim_run.py` 时实测, 通用)

- **触发**: 写 / 改仿真端。
- **判别**: 四条 ——
  ①**状态名必须合法**(`"errored"` 不是合法状态名, 解析成 UNKNOWN、缺文件扫描完全不触发);
  ②**辅种组内成员必须共享完全相同的文件相对路径**(只共享 `save_path` **不够** ⇒ 根本没归成组);
  ③**未配置站点的种子不归组** ⇒ 破坏性场景的"组内成员"必须以 **auto-qb 实际归组结果**为准;
  ④**首轮与稳态的 tick 间隔必须分开统计**(混算每次假红, 反而掩盖真正的稳态劣化)。
- **处置**: 四条逐项自查。

### 判据要能区分"没碰"和"没测到"

- **触发**: 写主判据。
- **判别**: 样本为空时主判据会**静默通过**。
- **处置**: 加一条 `*_seeded`(`>= 1`)确认样本真的存在;
  固化阈值时场景候选集要**分级**(稳态池只喂漂移阈值; 灌入期 / 带 WEB 负载记 BASELINE 不判红),
  且阈值**不要硬编码在调用处**(否则固化值永远用不上)。

### Windows 上硬 kill 拿不到 `state.json`

- **触发**: 想验证优雅退出。
- **判别**: `terminate()` = TerminateProcess, `finally` **不跑**;
  `CTRL_BREAK_EVENT` 也只得到 `0xC000013A`。
- **处置**: 用 `scripts/sim_autoqb.py` 启动包装(子进程装 `SIGBREAK → KeyboardInterrupt`),
  并加 `graceful_exit` **硬判据**。

### 反向对照必做

- **触发**: 加任何守卫 / 判据。
- **判别**: 不撤掉守卫跑一次, 可能只是装了个**永远不触发的空壳**
  (如把 `torrents_removed` 抹回 `[]`, `snapshot_drop` 由 20 掉到 0 才能证明该判据有效)。
- **处置**: 撤掉守卫 / 还原旧实现跑一次, 确认它**会报**。

### 替身"恒走默认分支"= 功能域整体缺席: 冒烟全绿不代表该形态渲染过

- **触发**: 给「站点接入后才生效」的前端展示排障, 或给 FakeTorrent 加新消费链路。
- **判别**: `FakeTorrent.hr_judgement()` **恒 None**(替身没接判定桥)⇒ 浏览器冒烟从头到尾只渲染过
  `judged=None` 的回落形态, safety_display 的**站点命中分支**(site_*/policy/unverified 的
  hr_safety_src token、详情抽屉站点侧值行)在前端**从未被真渲染过**。2026-09-25 生产首爆:
  BTSchool 接入后 `hrDurTitle -> hrSiteLine` 每行必走站点分支, 里面裸调用 `fmtDuration`
  ReferenceError ⇒ 整树白屏(见 ../web-ui/vue-reactivity.md)—— 而冒烟 96 项全绿。
- **处置**: `scripts/ui_harness.py --hr-site` 注入**真实 HrJudgement** 轮转全分支(含 judged=None 回落),
  站点接入形态的改动必须在 `--hr-site` 桩上跑冒烟; 新替身方法恒返回默认值时, 要自问
  "真对象的非默认形态有没有对应的注入开关"。

### 替身回不出"新响应形态" = 保真度缺口: 回执判定在替身上永远成立

- **触发**: 给写端点的回执 / 结果判定加守卫。
- **判别**: `FakeClient.torrents_add` 恒回**文本** `"Ok."`, 而真机 qB 5.2+(Web API 2.14.0)回的是
  **JSON 元数据**(`TorrentsAddedMetadata`)⇒ "添加成功却报失败"能一路全绿到线上(2026-09-24 实例,
  详见 [../backend/qb-api.md](../backend/qb-api.md) 的 `torrents/add` 响应形态一节)。
- **处置**: 新形态用**库自己的返回类型**顶替(`from qbittorrentapi.torrents import TorrentsAddedMetadata`),
  不要图省事用裸 dict —— 裸 dict 会把"库换了类型"这类回归一起放过; 替身里要写明它只模拟哪一版。

### `make_manager` 会清空 root handlers ⇒ 用例体内建 manager 时 `caplog` 抓不到任何日志

- **触发**: 用 `caplog` 断言日志级别 / 内容, 同时用例体内要建 manager。
- **判别**: `helpers.make_manager` 走 `setup_logging`, 其中 `logging.getLogger().handlers.clear()`
  会把 pytest 挂在 **root** 上的 caplog handler 一并清掉 ⇒ 之后所有记录都抓不到,
  症状是"日志断言恒空"(不是没打日志)。**fixture 里**建 manager 没事(采集 handler 在 call 阶段重新挂),
  **用例体内**建就会中招。
- **处置**: 给**模块 logger** 自建采集 handler(`logging.getLogger("auto_qb.webui.commands")`,
  它不受 root 清理影响), `try/finally` 里摘掉; 不要因此放弃日志断言 —— 日志级别即通知语义。

### 已知未修缺陷: qB 短暂断连后 auto-qb **无法自愈**

- **触发**: 排查断连后不恢复(供后续任务)。
- **判别**: 重连只在 `except APIConnectionError` 分支里做, 而该分支第一步 `self.client = None`;
  client 为 None 后 `sync_maindata()` 抛的是 **AttributeError** ⇒ 落进 `except Exception`(只打日志不重连)⇒ **死循环**。
  **通用教训: 凡是"异常处理器里改了状态、而这个状态又决定下次抛什么异常"的结构,
  都要警惕异常类型漂移导致分支永久失效。**
- **处置**: 单测要断言"**断连 N 秒后能自愈**", 而不是只断言"断连期间不崩"。

### 仿真配置格式

- **触发**: 写仿真配置。
- **判别**: 规则块必须落在 `config:` **之内**且键名**以 `_rules` 结尾**
  (顶层 `xxx_rules:` 是旧格式, 照抄会报"根节点: 未知键"); 规则内**没有** `log_level` 键。
- **处置**: 配置校验是 **fail-fast 且聚合报错**的, 一次列全。

### 顺带实测到的真实开销

- **触发**: 评估批量写请求。
- **判别**: `qbittorrent-api` **每次写请求前都要再查一次 `app/webapiVersion`**(库内无缓存)⇒
  **写请求量翻倍**; 叠加"逐种子打标签" ⇒ **批量提交可降一到两个数量级**。
- **处置**: 改批量路径时利用这条。
