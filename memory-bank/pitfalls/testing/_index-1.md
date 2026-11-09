# testing — 测试 / 冒烟 / 仿真纪律 · 卷 1/5

> **本文件是生成物, 不要手改** —— 由 `commands run kb.index` 生成; 主索引 [_index.md](_index.md) 是分卷路由。
> 本卷主题: `annotations-lazy-eval.md` … `fakeclock-migration-missed-forms.md`(共 22 条); 主题越多时索引按文件名分卷, 每卷 ≤ 8,000 字符。
> **检索纪律**: 先读本索引定位, 再按需打开单个主题文件 —— **不要整读本目录**。

## 主题

| 主题 | 一句话 | 触发词 |
|---|---|---|
| [annotations-lazy-eval.md](annotations-lazy-eval.md) | Python 3.14 起 PEP 649 让注解默认惰性求值 —— 模块级注解引用未导入的 typing 名字(如 Dict)在导入期**不报错**, 只在 ≤3.13 的解释器上炸; import-all 守卫必须显式 `inspect.get_annotations(obj… | Dict, typing, 注解, NameError, import 报错, 3.14, PEP 649, 惰性求值, import-all, 守卫, 假绿灯, 红验, TYPE_CHECKING, 前向引用, 引号, 字符串注解, 循环… |
| [assertions.md](assertions.md) | 恒真 / 恒红 / 安慰剂 / 量错对象 —— 断言失去意义的所有已知形态(含"样本与配置脱节"), 以及红验与 A/B 归因的纪律, 外加"存量失败登记前必须先重跑锚点"(取证时刻≠登记时刻)。 | 写断言, 红验, 反向对照, 阈值, 恒真, 摆设断言, 顺序断言, 冒烟失败归因, flaky, 反查表长度, infohash v1 v2, 手写样本, 配置没被读到, 存量失败, 入池前复跑, 历史数字, 重复报告, 复验锚点, 预期… |
| [ast-migration-fidelity.md](ast-migration-fidelity.md) | 机械拆分/迁移文件时, **AST 只给结构, 内容必须从源行取** —— `ast.get_docstring` 返回的是**求值后**的字符串(转义已解开), 拿它写回会把 `\\p{L}` 吃成 `\p{L}`(内容被静默改写 + 触发 SyntaxWarning); 另一… | 拆分文件, 迁移脚本, 逐行搬移, ast.get_docstring, 求值串, 转义被吃, `\\p`, SyntaxWarning, 生成模块, 自我 import, 循环 import, 行守恒, 保真校验, 分批迁移, 批模式,… |
| [base-schema-version-staleness.md](base-schema-version-staleness.md) | tests-real 各片基座(write_cfg/CONFIG_TEMPLATE)写死 `schema_version: <当时现行版>` 避免迁移改写 —— 产品 config schema 一 bump, 该字面量立即过期, 启动物化(materialize_schema_… | schema_version, 基座, 版本字串, 迁移改写, config.yml.v5.bak, 版本备份, CURRENT_VERSIONS, 启动物化, materialize_schema_migration, v5→v6, 版本… |
| [baseline-merge-order.md](baseline-merge-order.md) | 基线切片的合流序漂移: 最新切片数字与当前树实测不符 | 基线, kb.baseline, 数字对不上, 最新切片, 合流, sync, 快进, 多clone, 扶正 |
| [bg-process-cleanup.md](bg-process-cleanup.md) | 本工具环境里 `commands run dev.sim/dev.run` 这类长跑命令挂后台后, TaskStop / kill 只杀外层 (uv 或 commands 包装进程), 真正的 python 子进程继续持有 state.lock / 日志文件 / 端口 —— 复跑… | 后台进程, dev.run 停不下来, state.lock 删不掉, Device or resource busy, 端口占用, TaskStop, 杀进程, 孤儿进程 |
| [browser-verify-iab.md](browser-verify-iab.md) | 本机没有 node 时 Playwright e2e 链路不可用, 可用 ZCode IAB 浏览器 + evaluate 替代 —— 但 evaluate 返回嵌套对象是序列化假象 `{}`。 | 浏览器验证, IAB, evaluate, 无 node, 冒烟跑不了, 序列化, 假空对象, cfgRaw, 绑定状态 |
| [bulk-rename.md](bulk-rename.md) | 分批迁移类机械改名(W2 测试面 700+ 处)最易翻车的两处 —— ①正则替换串忘回填接收者, 整批替换全毁; ②名字按域分批 × 文件按域分批两个维度对不齐时, 该名字的替换规则不进脚本, 静默漏迁且**测试照样全绿**(旧名转发还在)。防御 = 捕获组回填 + 替换后畸形形… | 批量改名, 机械替换, re.subn, sed, 分批迁移, 迁移脚本, 旧名残留, 验收 grep, 漏迁, 接收者, 改名脚本, W3 删除波 |
| [ci-env-var-profile.md](ci-env-var-profile.md) | 通用 CI 变量在本仓库开发机入口常态为真, 拿它判「是否 CI」会让本地严格档永不生效(假绿) | CI, GITHUB_ACTIONS, 环境变量判档, 阈值分档, dev.e2e, playwright, 严格档失效, 假绿, 回归检测力, 性能基准 |
| [ci-only-guard.md](ci-only-guard.md) | 多类守阵/用例**只在与开发机不同的那一侧 CI job 上现形**, 本机单平台绿不构成"守阵成立"的证据 —— ①跨平台断言把**前缀切片长度写死**(`args[:2]`), nt 侧凑巧成立而 POSIX 侧恒红; ②并发守阵的**活性阈值绑机器速度**("写者写满 30… | CI 红本机绿, 跨平台断言, os.name, sys.platform, 写死切片长度, 前缀长度, 仅一侧存在的模块常量, CREATE_NO_WINDOW, 活性阈值, 并发守阵, 读次数, flaky, gtm, atomic_w… |
| [commands-wrapper-from-python.md](commands-wrapper-from-python.md) | python 脚本里 `subprocess.run(["commands", "run", ...])` 必 FileNotFoundError(WinError 2) —— commands wrapper 是 bash 侧脚本, 不在 Windows CreateProce… | subprocess, commands wrapper, WinError 2, FileNotFoundError, 造种脚本 |
| [config-validation-test-input.md](config-validation-test-input.md) | 给 config 校验器写测试时, 走 `load_config`/`_load_errors` 这条真实链路(而非直调校验函数)最省事, 但**输入必须先过两道加工**再进校验器: ①YAML 用 **BaseLoader** 读, **所有标量一律是字符串** —— `- 1… | 写 config 校验测试, 校验器测试, _load_errors, load_config, BaseLoader, 标量全是字符串, 空串被剥, _strip_none, _check_str_list, 第 N 项必须是非空字符串,… |
| [consecutive-port-run.md](consecutive-port-run.md) | 「连续 N 个候选端口」类用例(发现端点 base/base+1/base+2)若只用 `_free_port()` 取基址、再自己逐个显式 bind, 后 N-1 位从未被验证: 落进 Windows 动态排除段(Hyper-V/WSL 开机预留, 每次开机不同)或被独占进程占… | 连号候选端口, base+1, base+2, 排除段, WinError 10013, 10048, _hold_ports, discovery_candidates, 端口单点, hold_run, 假红, netsh exclude… |
| [corpus-capture.md](corpus-capture.md) | `scripts/qb_capture.py` 实施时实测的一批坑 —— 代理、rid 序列、秒分辨率时钟、伪名化撞车、判据空壳。 | 抓语料, 脱敏, qb_capture, 代理, rid, 伪名化, 等价类判据, 红验, argparse |
| [corpus-fs-mock.md](corpus-fs-mock.md) | 脱敏要连"藏在 .gz 里的第二层 key"一起做; 窗口合并必须按序推进; 回放 config 的 tracker 段不能只信权威映射。 | 语料回放, disk.json, fs mock, 窗口合并, tracker 段, 脱敏 key, 反查表, group_exact |
| [coverage-export.md](coverage-export.md) | 手工做覆盖率分析时, 导出文件叫 `.coverage.json` 会被 coverage 当成并行数据文件去读, 报 `Couldn't use data file ... not a database` + `Combined 0 files, 1 file errored`… | coverage report, coverage json, 导出覆盖率, not a database, CoverageWarning, Combined 0 files, 缺口分析 |
| [coverage-floor-platform.md](coverage-floor-platform.md) | 覆盖率闸单阈值在双 OS 上必有一侧恒红 —— Windows 独有代码(ctypes/junction/注册表后端)在 Linux 上跑不到, 实测 Windows 99.27% / Linux **98.74%**, 于是 `--cov-fail-under=99` 让 ub… | 覆盖率闸, cov-fail-under, 双 OS, ubuntu CI 恒红, pytest-cov, config.option 不生效, 平台定档, 分母不同, Windows 独有代码 |
| [credential-shape-write-guard.md](credential-shape-write-guard.md) | 工具写入判据把「凭据键名(Authorization/token 等) + 值不回显」的任何赋值形态当凭据字面量拦截 —— 测试里合法的鉴权头字典字面量(值是运行期读桩令牌, 无字面凭据)会让**整个文件**不可写; 且输出层掩码会把「凭据键名 + 分隔符 + 值」的片段显示改写… | 改含鉴权头字典字面量的测试文件被 artifact_secret_detected 拦, docstring 写 token 冒号键值形态, 凭显示层所见拼 oldText 永远匹配不上, 配置夹具凭据键, yaml 夹具凭据键 |
| [cross-thread-teardown-assert.md](cross-thread-teardown-assert.md) | starlette 1.6 把 SSE 的同步生成器包进 `iterate_in_threadpool`, 它跑在 anyio 工作线程里; 该线程帧里的最后一个引用(`item`/`func`/`args` 元组)是在 `call_soon_threadsafe` **之后**… | 跨线程终态断言, 断流退订, subscriber_count, anyio 工作线程, iterate_in_threadpool, 生成器 finally 退订, 单点采样, 竞态, 偶发红, 句柄堆叠, aclose 后仍订阅, gc… |
| [event-handler-mock.md](event-handler-mock.md) | `mock.patch.object(模块实例, "_on_xxx")` 拦不住 EventBus 已注册的相位 handler —— 注册期捕获的是绑定方法对象, patch 换的是实例属性, 总线里的引用不变; 守相位接线用「订阅计数 + emit 返回值」, 守行为直调真… | EventBus, 相位, subscribe, mock.patch.object, handler 断言, assert_called_once, P5 守阵 |
| [fake-config-shared-mutables.md](fake-config-shared-mutables.md) | helpers 的 `FakeConfig` 段对象是类属性(dataclass/dict/list), 任一测试原地改 | FakeConfig, 类属性, 测试隔离, xdist 分布, 偶发失败, make_manager, 原地改配置 |
| [fakeclock-migration-missed-forms.md](fakeclock-migration-missed-forms.md) | 把多套旧假钟批量迁到统一假钟(tests/clock.py)时, 按类名/替换表机械改最易漏两类形态 —— 直接调用旧假钟实例的 `clock()` 方法形(新假钟 API 是 `now()`/`monotonic()`, 类名相同但方法名不同), 与绕过属性、位置参数直构旧类的… | 假钟迁移, 旧假钟, tests/clock.py, clock() 调用形, 位置参数直构, 直构位, _FixedClock, 迁移漏改, 裸取时残留, 批量替换 |
