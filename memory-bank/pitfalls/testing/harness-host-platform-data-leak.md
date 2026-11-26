# e2e 桩只钉 config/data_dir 不够 —— 泄漏宿主「整机级用户级全局状态」会让断言前提随宿主环境翻转(实测: gtm 发现指针)

> 摘要: e2e/冒烟桩(ui_harness)给被测环境钉沙箱时, 容易只钉「项目自己的文件面」(config_path / data_dir / state 文件)而漏掉「整机共享的用户级平台目录」—— 代码若消费这类全局状态(本仓: gtm 发现指针 `pointer_dir()`, 单点解析到 %LOCALAPPDATA% / $XDG_DATA_HOME 或 ~/Library, 指针是**整机共享一处**的用户级文件), 断言前提就从「桩决定」变成「宿主机决定」: 宿主真跑 gtm 工具的开发机上 probe 真阳性 -> bundle.gtm 非 null -> settings-backup.spec 8 例确定性红, 而 Linux/容器机器上恒绿 —— 同一 spec 两台机器两种命运, 还会误判成 flaky/前提过期。**附带污染面更要命**: 可达后导入用例的真 POST 会经 `backup._apply_gtm_section` PUT 打到**宿主真实 gtm 工具**覆写其配置(复现轮在假 gtm 上捕到 2 笔 PUT 实证)。对策: 桩启动早期(任何 probe/create_app 之前)把发现单点重定向进桩私有目录 —— 合流机制是 `agent.pointer_dir` 单点 monkeypatch 到 `<tmp>/gtm-pointer`(`_isolate_gtm_discovery`); 加单测锁「隔离后指针面在桩私有目录」并用红验(调用前解析回宿主真实平台目录)证明判据非恒绿。
> 触发: e2e 桩, ui_harness, 沙箱隔离, 宿主泄漏, 用户级目录, XDG_DATA_HOME, LOCALAPPDATA, 整机级状态, gtm 指针, endpoint.json, pointer_dir, bundle.gtm, 单机红他机绿, 环境依赖断言, harness-host-platform-data-leak
**Refs:** memory-bank/issues/26-11-18-0308-test-e2e-settings-backup-gtm-bundle-drift.html

### 2026-11-17/18 实证: settings-backup.spec 8 例在 gtm 宿主上确定性红

- **触发**: 开发机真跑 gtm 工具 + `commands run dev.e2e`(或全量串行); Linux/容器机器(无指针)不复现 —— 容器 --full 轮仅 2/8 红的「形态差」其实就是宿主差异的回声。
- **现象**: `e2e/settings-backup.spec.mjs` 8 例红(导出 bundle.gtm 非 null、gtm pill 不灰显、导入 sections 混入 gtm 段、失败分支没走到), 单跑/串行同面同红。
- **机制**: 取证 2026-11-17, grep `pointer_dir` / `_platform_data_home`(`src/auto_qb/core/traffic_source/agent.py`): 发现层唯一事实源是用户级平台目录里的 `endpoint.json`; 而 `scripts/ui_harness.py` 只钉了 `mgr.config_path` 与 `mgr.config.data_dir` —— 桩进程里 agent 一调 `probe()` 读到的就是宿主真指针。
- **判别**: 「断言前提含桩环境假设 + 该假设依赖宿主机全局状态」即本族; 排除顺序: 先在宿主实跑探针面(本例 `probe()`), 非空即泄漏, 别先去翻 spec 断言对不对。
- **处置**(2026-11-18 已修, 两 clone 同题独立归因后合流): `scripts/ui_harness.py` 新增 `_isolate_gtm_discovery(tmp)` —— mkdtemp 之后、create_app 之前把 `agent.pointer_dir` 单点 monkeypatch 到 `<tmp>/gtm-pointer`(目录不存在 => endpoint.json / deferred.json 都读不到 => `discover()=None`); 另一 clone 探索过的等价方案是把 `XDG_DATA_HOME`/`LOCALAPPDATA` 两 env 键指进沙箱子目录(env 现读型重定向), 合流按单点 monkeypatch 落地(不动整机 env 面, 单测面更窄)。守阵 `tests/unit/test_ui_harness_gtm_sandbox.py`(隔离后 `pointer_dir()=<tmp>/gtm-pointer` + 红验: 调用前解析回宿主真实平台目录)。**通则**: 给桩钉沙箱时按「代码消费了哪些整机级状态」盘点, 不止项目内文件 —— 平台数据目录、HOME 展开面、共享缓存都在清单上; 新消费点上桩时同步扩隔离, 别等跨机红才回填。
