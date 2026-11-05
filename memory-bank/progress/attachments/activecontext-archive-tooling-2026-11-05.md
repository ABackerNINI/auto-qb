# activeContext 切片归档 · 知识库 / 文档 / 依赖 / 重构

> 摘要: 2026-11-05 activeContext 蒸馏轮逐字外迁的 31 条切片原文(2026-09-30~11-03, 知识库机制/code-review 3/文档漂移/提交链路/依赖与 dup-code 重构)。
> 触发: 知识库, memory-bank, kb, code-review, 文档漂移, 提交闸门, 依赖, dup-code, 切片归档
> 本文件为逐字归档(attachments 不计 cap); 蒸馏结论与指针写在各 progress 主题文件。
> 归档说明: 原文中的相对链接已因换目录统一补一级 ../, 其余逐字未改。
> 归档说明之二: 原文中的 Refs 声明行改题为「切片原文」以免被知识库认领链解析误读; 链接路径已补一级 ../; 其余逐字未改。

---

<!-- slice: 26-09-30-1007-commands-engine-self-stdio.md; 最后活动: 2026-10-01 07:20 -->

# commands 引擎自身 stdout 乱码修复(部分终端)

> 摘要: 用户报「部分终端 `commands run kb.active` 中文乱码」—— 子进程方向 9-24 已修, 这轮是引擎**自身** stdout 在管道下按本地码页出中文; 已修(`_utf8_self_stdio()` 在 main() 入口锁 UTF-8)并加 2 条守阵。**2026-10-01 复发轮**: 用户报「已同步仓库仍乱码」—— 引擎侧修复有效, 乱码源在**解码侧**(PowerShell 捕获类 / AI 工具 `-NoProfile` 外壳按 GBK 解 UTF-8), 已修两份 PS profile 并回写坑档; 引擎侧不变。
> 触发: 输出乱码, 部分终端, commands 引擎, 自身 stdout, 管道, cp936, reconfigure, run.py, mintty, PowerShell 捕获, -NoProfile, AI 工具终端
> 最后活动: 2026-10-01 07:20

## 状态

**Done**(2026-09-30, 小修, 未立项 —— 低于立档阈值)。用户报「部分终端运行 `commands run kb.active` 显示乱码」。

**根因(取证, 非猜测)**: 9-24 修的是**子进程→引擎**方向; 引擎**自己 print 的中文**(协议行 / 包摘要 / 透传正文)走 Python 自身 stdio —— 真控制台是 `WriteConsoleW`(Unicode, 永不乱), stdout 一旦被**管道**接住(mintty / AI 工具捕获 / CI)编码回退本地码页 cp936。实测: 剥离 `PYTHONUTF8`/`PYTHONIOENCODING` 后 `show kb.active` 首段中文是 GBK 字节, strict UTF-8 解码当场炸, 退出码照旧 0; 会话里的 UTF-8 变量是工具 shell 会话级注入(注册表 HKCU/HKLM 均无), 用户终端裸奔 —— 这就是"部分终端"的分界线。

**修法**(引擎单点 `run.py`, 与 9-24 同文件): `_utf8_self_stdio()` —— stdout+stderr `reconfigure(encoding="utf-8", errors="replace")`, `main()` 第一行调用(先于任何 print / argparse 输出)。真控制台不受影响; 管道对端从 GBK 变 UTF-8, 只修不破。

**守阵**: `test_engine.py` +2(cp936 文本层单测 / 剥变量+管道子进程端到端 strict 解码)。test.pkg 74 passed。

- [坑 (ops/console-encoding)](../../pitfalls/ops/console-encoding.md)
- [上一轮: 子进程方向](../../pitfalls/ops/console-encoding.md)（原切片 26-09-24-2029 已随 26-09-30 切片数守卫蒸馏, 内容归坑档）
- [测试基线](../../testing/baseline.md)

## 实测

修后剥离全部 UTF-8 环境变量 + 管道跑 `show kb.active`: strict UTF-8 解码 OK, 首行「何时用: 看会话滚动状态…」完好;
全量数字只认单点 [testing/baseline.md](../../testing/baseline.md)(本切片不复述)。

## 2026-10-01 复发轮: 解码侧(PS 捕获类 / AI 工具外壳)

用户纠错「代码已同步的仓库中仍乱码」→ 取证推翻「旧 clone 未同步」的初判(本机 clone3/4/5 确实旧, 但不是用户场景)。ConPTY 伪控制台探针逐类实测: 交互真控制台(cmd / PS5.1 / pwsh7)全干净; 乱的是 **PS 捕获路径**(管道 / 赋值 / `-Command` 外壳)——按 `[Console]::OutputEncoding`(GBK)解引擎的 UTF-8, `创建`→`鍒涘缓`。用户指认场景 = **AI 编码工具的终端**(此类工具多经 `powershell -NoProfile -Command` 跑命令, 内层 PS 按 GBK 解, 工具按 UTF-8 读 → 必乱)。

机制实测: PS 在**启动瞬间**快照控制台码页 —— 运行中 `chcp 65001` 救不了; 启动前已是 65001 时连 `-NoProfile` 捕获都正确。

**修法**(解码侧, 引擎不动): 两份 PS profile 加 `try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch {}`(用户授权); 端到端验证改前 `鍒涘缓` → 改后 `创建`(pwsh 7.6.6 + PS 5.1 双验)。`-NoProfile` 工具类 profile 救不了 —— 系统级「Beta: UTF-8」或该工具换 Git Bash shell, 用户自拍板(未做)。

- [坑档新增「解码侧」节](../../pitfalls/ops/console-encoding.md)(含复发标记与 chcp/cmd/PS 三方结论的边界)
- 本轮无仓库代码改动(仅坑档 + 用户级 profile), 未跑 test.full, 未提交

---

<!-- slice: 26-10-01-1758-issue-clearance-roadmap.md; 最后活动: 2026-10-02 18:50 -->

# issue-clearance-roadmap — Issue 全量清偿路线图(滚动执行)

> 摘要: 用户两轮要求的摸排-分波-排期任务,路线图已出至 **v2**:
> [plans/26-10-01-1758-plan-issue-clearance-roadmap.html](../../plans/26-10-01-1758-plan-issue-clearance-roadmap.html)(同文件改版, 变更记录见 §A)。
> v1(26-10-01)摸排 31 条分七波, 其后清偿 12 条(v1-W1 闸门波 5/5 全清、v1-W2 3/4, 明细迁
> progress/implemented-core.md · implemented-webui.md + issues Done 分区, 此处只留路标)。
> v2(26-10-02 02:34)在「清偿 12 条 + 新入池 46 条」后改版: 未决 31→**59 条**(58 Open + 1 In Progress),
> test 类型清零(闸门已绿, 基线 26-10-02-0203: 2143+3 / 96.49%), 重排**九波**:
> W1 后端速赢(凭据/状态/鉴权 4)→ W2 WebUI 正确性(7)→ W3 数据安全大件(3)→ W4 性能(4)→
> W5 HR/统计拍板簇(6)→ W6 体验批(13)→ W7 扩展(3)→ W8 穿插(13)→ W9 挂账(6, 不排期)。
> 关键标记: 26-09-22-2221(跨组交叉)用户曾排除, 开工需单独授权; transmission-compat 停在拍板(报告 26-10-01-2347);
> 热重载两条 / EXT 两条 / tag-category-dialog 开工先复验。滚动档案 = tasks/26-10-02-memory-bank-issue-clearance-roadmap.md。
> **待办**: W1 起逐波推进, 每波待用户显式授权; 未全清计划不转 Done; 实时以 issues/_index.md 为准。
> **W1 已收官(3/3, 用户授权后 26-10-02 当日完成)**: ① hr.token 生成改原子写(issue 26-10-01-2151
> → Done, 档案 [tasks/26-10-02-hr-token-atomic-write.md](../../tasks/26-10-02-hr-token-atomic-write.md));
> ② HrEntry.last_seen 写入点 + INDEX_RETENTION 清理复活(issue 26-10-01-2335 → Done,
> 档案 [tasks/26-10-02-hr-entry-last-seen-prune.md](../../tasks/26-10-02-hr-entry-last-seen-prune.md));
> ③ web 鉴权加固双件(issue 26-09-21-1408 CSRF + 鉴权三小件 → Done,
> 档案 [tasks/26-10-02-web-auth-hardening.md](../../tasks/26-10-02-web-auth-hardening.md))。
> 收官基线 26-10-02-0459: 2288+3 / 99.01%(阈值 98)。
> **W1 收官后范围外发现统一入池(26-10-02, 用户授权)**: ① `_sign_releases` 对已 verified
> infohash 不查重整条覆写(26-10-02-0526 bug/疑点, 可达性待核) ② hr/service.py 直调 time.time()
> 绕过 now_fn(26-10-02-0526 refactor/light) ③ O_TRUNC 直写静态守阵并入(26-10-02-0527 test/light,
> 生效条件已达成)。池内实测 Open 63 + In Progress 2(transmission + 26-09-25-1702 已被并行
> clone 认领出调研报告 be74bbe1; 含并行 clone 328a6704 入池 6 条);
> 新条目并入波次待路线图下次改版。**下一步: W2(WebUI 正确性 7 条)待用户显式授权。**
> **全表状态核对轮(2026-10-02, 用户指派「核对+加状态栏」, 主会话委派 5 批次串行子智能体,
> 每批次单独提交: a26123e5 结构+W1-W2 → 3e77fb57 W3-W5 → cfbfa712 W6 → d354745b W7-W8
> → 7c61e87a W9+复核+池计数刷新)**: 59 条逐一静态核对(读档案+查代码+git log 交叉, 不跑测试),
> 九张波次表各加「状态」列(五档: ✅已修复/🔶部分修复/⛔已过时/⏳待处理/📌挂账, 格内附依据),
> §1 末加图例与全表统计小结, §A 变更记录 v2.1-v2.5。最终分布 **✅8 / 🔶3 / ⛔4 / ⏳39 / 📌5**。
> 顺带回写池状态 7 份(meta+徽标+状态日志): Done 3(2108-selection-follow-mouse /
> 2108-esc-clear-filter / 1408-web-runtime-host-protocol) · Dropped 3(2129-batch-warning-notify /
> 2138-traffic-history-chart / 0052-hr-login-counter-attest) · Superseded 1(2129-hotreload-ext-vanish),
> `_index.md` 随每批次 kb.index 重建。**存疑留给用户**: login-counter-attest 判 ⛔ 的依据是负信号
> 守卫(5c518b3b)早于入池、入池前提当日即不成立, 不认可则一行改回 Open; W5 hr-online-vs-sitewide
> 配置收敛后混淆是否仍成立静态无法确证, 待拍板。核对期间池内又入 13 条 26-10-02 记录(不在 59 行内,
> 待下次改版并入), roadmap 封面计数已按 18:45 实测刷新。零生产代码改动, 无测试基线需求。
> **下一步**: 按状态列推进 —— 39 ⏳(W2 正确性簇 3 条仍未动) + 39 条中 W3 大件需方案先行;
> 逐波开工仍待用户显式授权。
> 最后活动: 2026-10-02 18:50

---

<!-- slice: 26-10-09-1529-transport-encryption.md; 最后活动: 2026-10-09 15:29 -->

# 本地通道传输安全调研(WebUI + HR 取数通道)

> 摘要: 用户命题「WebUI⇄auto-qb 与 auto-qb⇄扩展两条通道均为明文 HTTP, 有安全风险; 设想用 token 加密载荷; 要求调研成熟方案并对比成本优劣」。产出可行性报告 `reports/26-10-09-1529-report-transport-encryption-feasibility.html`(含威胁模型分层 T0-T4 / 五方案对比 / 落地路径)。**核心结论**: ①默认回环形态下明文残余风险有限(T0 同用户进程本就可读 token 文件, 传输加密无解), 加密边际收益小; ②通道一旦暴露到 LAN/跨机, 唯一正确且省事的答案是 **TLS(本地受信 CA / 反代 / VPN)**, 而非自研应用层加密; ③用户设想的「token 加密载荷」在回环下技术成立(回环是安全上下文, `crypto.subtle` 可用), 但**跨机 LAN 的 `http://<私网IP>` 页面不是安全上下文 ⇒ Web Crypto 不可用**, 恰在最需要它的场景失效; ④最该先做的是「暴露即提示/收口」而非默认上加密。**未写任何代码**; 落地需另立计划(随 `hr-channel-remote` 专题)。
> 最后活动: 2026-10-09 15:29

## 状态

- 已完成: 报告产出并入库(`reports/_index.md` 重建); 与 issue `26-10-09-0855`(HR 通道锁死回环)建立双向 `doc-refs（切片原文）` 认领链。
- 未做: 无代码改动; 未拍板落地方案。
- 下一步(待用户拍板): 是否立项「阶段 1 暴露即加密闸门 + 阶段 2 一键本地 CA」; 阶段 2 涉及新增 `cryptography`/`trustme` 依赖与 `web.tls.*` 配置键(须进 `validate_config` + `config/schema`)。

**Refs（切片原文）:** memory-bank/reports/26-10-09-1529-report-transport-encryption-feasibility.html,memory-bank/testing/baselines/attachments/26-10-09-1529-transport-encryption.md,memory-bank/tasks/26-10-09-backend-transport-encryption.md

---

<!-- slice: 26-10-15-0409-infra-fmt-ladder-dup-fix.md; 最后活动: 2026-10-15 04:14 -->

# infra fmt 阶梯单点 · dup-code-audit issue 认领与修复

> 摘要: 用户「认领并修复 memory-bank/issues/26-10-11-0352-refactor-infra-fmt-ladder-dup.html」→ dup-code-audit 专题 infra 轮(R18)第 4 条 refactor issue 认领并修复。口径沿用前修复轮(hr/webui/rules/core/infra R9): A 类抽单点收敛 + 保守口径(行为逐字不变)。复验定案: `infra/utils.py` 的 `fmt_speed` / `fmt_size` 阶梯循环仍逐字同(判据与格式化行各写一遍, 只差单位表 `/s` 后缀)。
> 最后活动: 2026-10-15 04:14

**Refs（切片原文）:** memory-bank/issues/26-10-11-0352-refactor-infra-fmt-ladder-dup.html

## 已完成(2026-10-15 单会话收口)

- issue 复验(锚点均在, `utils.py` 679/687 按取证 26-10-15 04:09)后置 `In Progress`, 修复完成置 `Done`, 状态变更日志留实际修法/验证方式/测试数字痕。
- 改动面: `src/auto_qb/infra/utils.py`(`_SIZE_UNITS` 单位表 + `_fmt_ladder(value, units, suffix)` 阶梯骨架单点, `fmt_speed` / `fmt_size` 降为委托 —— `fmt_size` 的 int 强转与 `"-"` 兜底保持在外) + `tests/test_utils.py`(行为用例 + 静态单点守阵, 头部「测试计划」清单同步两条); 全部过 `dev.fmt`。零跨包改动, `config.yml` / `auto-qb-data/` 未触碰。
- 验证: 定向 `test.one tests/test_utils.py` 全绿; 红验双验闭环 —— ①自抄阶梯回(fmt_speed 内内原循环)即静态守阵红(count 2), ②精度变异(`.2f`→`.1f`)即行为用例红(钉输出判), 还原即绿; 收口 `test.full` 全绿 —— 实测数字唯一权威在基线切片 `testing/baselines/attachments/26-10-15-0414-infra-fmt-ladder-dup-fix.md`(看数字 `commands run kb.baseline`, 此处不手抄)。
- 主档案 `26-10-10-backend-dup-code-audit.md` 进度记 R10 一行; infra 余 1 条(`infra-platform-detect-bypass-dup`)仍 `Open`。

---

<!-- slice: 26-10-12-2110-infra-dup-code-fixes.md; 最后活动: 2026-10-15 04:22 -->

# infra 修复轮 · dup-code-audit issue 认领与修复（url 分解 / 小样板 / win DLL 惰性绑定 / 平台判定单点）

> 摘要: 用户「认领并修复: 26-10-11-0352-refactor-infra-url-decompose-dup / -infra-utils-small-helper-dup / -infra-win-dll-lazy-bind-dup」→ 对 dup-code-audit 专题 infra 轮(R18)入池的 3 条 refactor issue 认领并修复, 全部置 `Done`。口径沿用前几轮(hr/webui/rules/core): A/C 类抽单点收敛, 保守口径(行为逐字不变, 既有守阵回归)。实际修法: ①`utils._split_url(url) -> (scheme, netloc, path, query)` 分解单点(去 userinfo / 缺 scheme path 首段兜底且首段消费后不回填 / 失败 None), `sanitize_tracker_url` 与 `mask_tracker_url` 共用(原建议形态, 零改道); ②`utils._hosts_of(urls)` 收敛 host 收集内联循环(条目 dict 列表经生成器适配), `file_access` 基类 `FileAccess._probe(os_fn, path)` + `_probe_path` 收编 exists/isdir/isfile 三连 —— 探针单点形态与原建议略有出入: os 判定三连收在基类, Local/Mapped 只实现 `_probe_path` 给 syscall 路径(原建议「各类传自己的 fn」抽完后基类仍留三份定义, 收口不彻底); ③`utils._win_dll(name, sigs)` 参数化惰性绑定骨架, `_bound_*` 全局与 monkeypatch 注入点保留, `is_windows()` 早退在缓存判定之前, 新增 `_WIN_KERNEL32_SIGNATURES()` 同 user32 口径。**连带修订**: 三态探针收编后 `os.path.exists` 由调用变基类属性引用, 静态守阵 `test_fs_mock_coverage_static_guard` 首轮全量红验(期望表未同步) —— 按守阵自身规矩更新 `_EXPECTED_PROBES`(去掉 exists 钉计数, 注释说明)与 `sim_fsmock.MockCoverage` 覆盖说明后复绿; mock 按模块属性打桩, 覆盖实质不变。infra 余 2 条(`infra-fmt-ladder-dup` / `infra-platform-detect-bypass-dup`)不在本轮范围, 留 `Open`。**第二轮(2026-10-15, 用户指派「认领并修复」第 4 条)**: `infra-platform-detect-bypass-dup` 复验锚点均在后置 `Done` —— 7 处旁路(`infra/autostart.py` 6 处 + `tray/app.py` 1 处)全改走 `utils.is_windows()/is_mac()` 单点(零行为变化, `is_windows` 的 "win" 前缀已覆盖旁路的 "win32"), 新增静态守阵 `test_platform_detect_single_point_static_guard`(src/ 全域禁裸 `sys.platform.startswith`, 单点自身豁免); infra 余 1 条(`infra-fmt-ladder-dup`)仍留 `Open`。详见下方第二轮段。
> 最后活动: 2026-10-15 04:22

**Refs（切片原文）:** memory-bank/issues/26-10-11-0352-refactor-infra-url-decompose-dup.html,memory-bank/issues/26-10-11-0352-refactor-infra-utils-small-helper-dup.html,memory-bank/issues/26-10-11-0352-refactor-infra-win-dll-lazy-bind-dup.html,memory-bank/issues/26-10-11-0352-refactor-infra-platform-detect-bypass-dup.html

## 已完成(2026-10-12 单会话收口)

- 三份 issue 复验(锚点均在, win-dll 行号漂移按 grep 事实定位)后置 `In Progress`, 修复完成置 `Done`, 状态变更日志逐条留痕(含实际修法/验证方式/测试数字)。
- 改动面: `src/auto_qb/infra/utils.py`(_split_url / _hosts_of / _win_dll + _WIN_KERNEL32_SIGNATURES) + `src/auto_qb/infra/file_access.py`(_probe/_probe_path) + `tests/test_sim_corpus.py`(静态守阵期望表) + `scripts/sim_fsmock.py`(MockCoverage 覆盖说明); 全部过 `dev.fmt`。
- 验证: 定向 `test_utils.py` + `test_file_access.py` 全绿; 收口 `test.full` 全绿 —— 实测数字唯一权威在基线切片 `testing/baselines/attachments/26-10-12-2125-infra-dup-code-fixes.md`(看数字 `commands run kb.baseline`, 此处不手抄)。
- 未 commit / 未 push(用户未要求); 重复代码审查主线(Phase 2 前端轮 20–23 / Phase 3 测试横切 24–25 / Phase 4 汇总 26)仍未开工。

## 第二轮(2026-10-15 单会话收口 · 用户指派「认领并修复」第 4 条)

- issue `26-10-11-0352-refactor-infra-platform-detect-bypass-dup`: 复验锚点均在(grep `sys.platform.startswith` = autostart.py 6 处 + tray/app.py:204; 单点口径 `"win"` 前缀, 旁路口径 `"win32"`)后置 `In Progress` → 修复完成置 `Done`, 状态变更日志逐条留痕(含实际修法/验证方式); 认领链双向(本切片 Refs ↔ issue doc-refs（切片原文）)。
- 修法(取 issue「建议」第一支, 零行为变化): `infra/autostart.py` 6 处(`is_enabled`/`enable`/`disable` 的 win/darwin 分支)经包内相对导入 `from .utils import is_mac, is_windows` 改调 `is_windows()`/`is_mac()` —— `is_windows` 匹配 `"win"` 前缀已覆盖 `"win32"`, 语义逐字等价; `sys` 导入保留(`sys.executable` 仍用)。`tray/app.py:204` 改调 `utils.is_windows()`(模块级已导入 utils), `import sys` 随之移除(该文件唯一用途)。未采纳「抽 `_platform()` 枚举」支: 调用点改函数调用即收口, 枚举是新抽象面, 保守口径不扩。
- 新增静态守阵 `tests/test_utils.py::test_platform_detect_single_point_static_guard`: 扫 src/ 全部 .py 禁裸 `sys.platform.startswith`(单点自身豁免; notify.py 取平台字符串值作标识非 startswith 判据, 不拦); 红验 = 临时注入旁路判红后删除临时文件。
- 改动面: `src/auto_qb/infra/autostart.py` + `src/auto_qb/tray/app.py` + `tests/test_utils.py`(守阵 + 测试计划清单同步) + 本 issue 状态流转; 全部过 `dev.fmt`。
- 验证: 定向 `test_utils.py`+`test_ui.py`+`test_tray.py` 全绿(coverage 未达标为子集运行预期); 收口 `test.full` 全绿 —— 实测数字唯一权威在基线切片 `testing/baselines/attachments/26-10-15-0422-infra-platform-detect-bypass-dup.md`(看数字 `commands run kb.baseline`, 此处不手抄)。
- infra 余 1 条(`infra-fmt-ladder-dup`)仍留 `Open`。

---

<!-- slice: 26-10-15-0412-notify-tray-icon-path-dup.md; 最后活动: 2026-10-15 04:23 -->

# 认领并修复 notify↔tray icon 路径推导重复(R19-A01)

> 摘要: 用户指令「认领并修复 memory-bank/issues/26-10-11-0352-refactor-notify-tray-icon-path-dup.html」。复验仍复现(源码随包迁移到 src/auto_qb/ 后行号未变, notify:48 与 tray/app:31-32 两级 dirname 表达式逐字同)→ 按 issue 建议的第二支「notify 导出 ICON_ICO、tray 引用」落地: **infra/notify.py 的 ICON_ICO 成为包 assets 目录推导唯一处**, tray/app.py 改为 import 该常量(ICON_PNG 由同目录派生), 全仓两级 dirname 表达式 3 处 → 1 处, **零行为变化**(运行期探针: 两模块 ICON_ICO 字节同、指向真实文件)。改动 2 个源文件(notify / tray-app), 未新增测试——既有守阵 test_notify_icon_ico_points_to_real_file 继续钉「路径指向真实文件」, 且低于立档阈值(3 源文件)故未建任务档案。issue 状态流水 Open → In Progress → Done; 全量测试数字见基线切片 `memory-bank/testing/baselines/attachments/26-10-15-0423-notify-tray-icon-path-dup.md`。
> 最后活动: 2026-10-15 04:23

**Refs（切片原文）:** memory-bank/issues/26-10-11-0352-refactor-notify-tray-icon-path-dup.html,memory-bank/testing/baselines/attachments/26-10-15-0423-notify-tray-icon-path-dup.md

## 正在进行

- **修复已落地并收口**: issue 两处徽标 + meta 已置 Done, 状态日志含复验 / 实际修法 / 与建议改道原因 / 验证方式四段; 认领链双向闭合(issue.doc-refs（切片原文） → 本切片, 本切片 Refs → issue + 基线, 基线 Refs → 本切片)。

## 关键结论(供后续执行参考)

- **修法取舍**: issue 建议的两支(①infra.assets_dir() 新单点函数 ②notify 导出 ICON_ICO、tray 引用)选 **②** —— 少改一个源文件(不动 infra/utils.py), 表达式净收敛(3→1), 且 tray 本就已从 notify import(WINDOWS_TOAST_APPID), 依赖方向不变; 包目录移动时仍只需改 notify 一处。
- **ICON_PNG 的派生口径**: `os.path.dirname(ICON_ICO) + "icon.png"` —— 与 tray 原 ICON_PNG 字节同(运行期探针实证), 不引入第二个 dirname 口径。
- **零行为变化验证**: 运行期断言 `tray.ICON_ICO == notify.ICON_ICO` 且 `os.path.isfile` 为真; notify 测试文件全量先跑绿; 全量见基线切片。
- **退回成本**: 若将来 assets 目录需要参数化(如打包路径可配), 再升级为 `infra.assets_dir()` 函数单点(现无常驻配置入口, 提前抽函数属过度设计)。
- **流程教训(已入坑档 `pitfalls/kb/refs-rename.md` 复发 6)**: 认领链必须**先建认领方件、后回填 doc-refs（切片原文）** —— 本轮先填 issue doc-refs（切片原文） 后写切片, 悬空窗口被同期 test.full 扫红 1 条, 复跑才绿。

---

<!-- slice: 26-10-15-0501-torrents-snapshot-view-field-dup-fix.md; 最后活动: 2026-10-15 05:01 -->

# torrents 视图字段表单点化 · dup-code-audit issue 认领与修复

> 摘要: 用户「认领并修复 memory-bank/issues/26-10-11-0352-refactor-torrents-snapshot-view-field-dup.html」(上一回合卡于分析, 本回合继续修复)→ dup-code-audit 专题 torrents 侧(R19-C01)refactor issue 认领并修复。口径沿用前修复轮(hr/webui/rules/core/infra): A 类抽单点收敛 + 保守口径(行为不变)。复验定案: `torrents/compat.py` `_EXTENSION_FIELDS`(43 项)与 `torrents/view.py` `_VIEW_FIELDS`(现代码 61 项, issue 记 65)仍手抄同一批 qB 字段名, 本面唯一 pylint R0801 命中。
> 最后活动: 2026-10-15 05:01

**Refs（切片原文）:** memory-bank/issues/26-10-11-0352-refactor-torrents-snapshot-view-field-dup.html

## 已完成(2026-10-15 单会话收口)

- issue 复验(grep `_EXTENSION_FIELDS` / `_VIEW_FIELDS` 锚点在)后置 `In Progress`, 修复完成置 `Done`, 状态变更日志留实际修法/验证方式/测试数字痕。
- 改完前派derive 等价预实测: view 61 项 ⊆ snapshot 70 项(`view - snapshot` 空), 缺口恰 9 项(`hash`/`completed` + 重加 4 + 做种限制 3)—— 缺口清单直接落地, 行为不变判据前置钉。
- 改动面: `src/auto_qb/torrents/view.py`(`_VIEW_EXCLUDED_FIELDS` 缺口 9 项 frozenset + `_VIEW_FIELDS = _SNAPSHOT_FIELD_SET - _VIEW_EXCLUDED_FIELDS` 派derive 单点, 61 项手抄 literal 退役; `from .compat import _SNAPSHOT_FIELD_SET` 接线, 同包私有名 import 与 record.py 同口径)+ `tests/test_torrents.py`(新增守阵 `test_view_fields_derived_from_snapshot`: 缺口 ⊆ 快照含 + 缺口字段不置脏 + 非缺口全进脏判定 + 静态接线 count == 1; 头部「测试计划」清单同步一条); 全部过 `dev.fmt`。零跨包改动, `config.yml` / `auto-qb-data/` 未触碰。
- 漂移方向改: 新增快照字段默认进脏判定(多余重建无害), 手抄漏方向(字段变化不置脏、视图静默不重建)即 issue 记的漂移风险 —— 退役。
- 验证: 定向 `test.one tests/test_torrents.py` 全绿; 红验三判据闭环 —— ① 自抄 61 项 literal 回(行为不变)即静态守阵红(接线 count 0), ② 缺口拼不错 `hash`→`hsh` 即含红, ③ 手抄漏字段 `name` 即行为红(新守阵 + 既有 `test_view_dirty_intersection` 两红), 还原即绿; 收口 `test.full` 全绿 —— 实测数字唯一权威在基线切片 `testing/baselines/attachments/26-10-15-0512-torrents-view-field-dup-fix.md`(看数字 `commands run kb.baseline`, 此处不手抄)。
- 主档案 `26-10-10-backend-dup-code-audit.md` 进度记 R11 一条; torrents+tray 池 3 条全部 `Done`(hr-entry-guard 前轮, icon-path 0423, 本条 0501)。

---

<!-- slice: 26-10-16-1533-ship-commit-omitted-note.md; 最后活动: 2026-10-16 17:04 -->

# 26-10-16-1533-ship-commit-omitted-note — ship.commit 子集提示与实际提交面对齐(issue 26-10-16-1523 认领与修复)

> 摘要: 用户「认领并修复 memory-bank/issues/26-10-16-1523-bug-ship-commit-omitted-note.html」。问题: 子集模式只限制 `git add` 清单, 而 `git commit` 提交的是**整个索引** —— 旧提示「未纳入」把已暂存的未传改动也读成"没进本笔", 与实际相反(入池实测: 10 个 `D ` 撤跟踪项被列成「未纳入」却全在同一笔里)。落盘(issue §06 方向 A; B「真正路径限定提交」不做 —— 会推翻坑档 `git/ship-commit-staged-delete.md` 已依赖的「已暂存删除项随整索引落笔」便利): `commit.py` 新增 `omitted_note()` 按索引状态分组(已暂存/未暂存各给计数与示例, 空组不列)、`omitted` 去重(MM 文件不再翻倍); 打印点改调它。守阵 4 条 + 红绿双验 3 类突变逐类判红(还原 SHA256 一致); 复验先于改动(探针临时仓库重放: 修复前仍复现 → 修复后与提交面逐条一致)。数字见基线切片与档案。另: 提交阶段被快照守阵两条既有红挡下(与本次改动无关), 已处置 —— ① 家目录空 `.git` 由机主移除; ② `-n 8` 并行竞态经用户授权按「用例私有临时根」修复(红绿双验 2 类; 见落点)。新坑已记 `pitfalls/testing/tmpdir.md`; 基线切片「包内脚本测试」节留有当时的失败记录。
> 最后活动: 2026-10-16 17:04
> 状态: Done

**Refs（切片原文）:** memory-bank/issues/26-10-16-1523-bug-ship-commit-omitted-note.html,memory-bank/tasks/26-10-16-ship-commit-omitted-note.md,memory-bank/testing/baselines/attachments/26-10-16-1551-ship-commit-omitted-note.md

## 本轮落点(代码事实)

- `.commands/my-commit-flow/scripts/commit.py`: 新增 `_sample(files, limit=3)` 与 `omitted_note(omitted, staged)` —— 打印前按索引状态把「未参与 add」的改动分两组: `已暂存 N 个(仍会随整索引进本笔: …)`(在 staged 清单里, 照样随整索引进本笔)与 `未暂存 N 个(不会进本笔: …)`(只在 unstaged 清单里), 空组不列; 打印点由平铺旧文案改调它。`resolve_stage_plan` 的 `omitted` 去重(`dict.fromkeys`, MM 文件同时在两份清单里、旧口径计数翻倍)。模块 docstring 流程第 3 步 + 函数 docstring 同步(记 issue 26-10-16-1523)。
- `.commands/my-commit-flow/scripts/test_commit.py`: 新增 4 条守阵(去重 / 分组与计数示例 / 示例截断且空组不列 / 真仓「提示与提交面逐条对齐」); 头部「测试计划」清单同步。
- `.commands/my-commit-flow/scripts/test_snapshot.py`(授权修, 为放行闸门): 两条存在性比较(`_snap_dirs`)改为在**本用例私有临时根**内进行 —— 新增 `_private_tmp()`(根 + 子进程 TMPDIR 一并指向它), `-n 8` 并行下不再因兄弟用例落进同一全局临时根而假红; 断言意图不变(import 不重入 / 不留临时副本)。红绿双验(泄漏 / import 重入两类突变判红, 还原 SHA256 一致)。
- `memory-bank/pitfalls/git/ship-commit-staged-delete.md`: 变体二补一行「提示已按索引状态分组, 不再混称『未纳入』」(含与本变体实测的对照)。
- `memory-bank/pitfalls/testing/tmpdir.md`: 新条目「约定盘缺席/不可见 → TMPDIR 静默回落」(识别口径 + 同日收口注)。
- `memory-bank/issues/26-10-16-1523-bug-ship-commit-omitted-note.html`: Open → In Progress(15:33, 复验后)→ Done(15:51); 认领链双向(本切片/档案 Refs ↔ issue doc-refs（切片原文）)。
- `memory-bank/testing/baselines/attachments/26-10-16-1551-ship-commit-omitted-note.md`: 本专题基线(test.full / 定向 / 红绿双验 / 既有失败记录)。

## 未做(有意, 范围守恒)

- 方向 B(真正路径限定提交)不做: 属行为面改动, 且会推翻「已暂存删除项随整索引落笔」的既有依赖(坑档 `git/ship-commit-staged-delete.md` 变体二的处方依赖于它)。
- 快照守阵的 ①(家目录 `.git` 形态)未做代码侧加固: 机器已修复; 若将来再现, 可考虑让「无仓库上溯」断言不依赖机器上溯形态。

## 下一步 / 移交

- 立档: 变更集 3 个源文件(`commit.py` + `test_commit.py` + `test_snapshot.py`)命中阈值 ⇒ 见 `memory-bank/tasks/26-10-16-ship-commit-omitted-note.md`(认领链双向)。
- 快照守阵既有红已解除(① 机主修复; ② 经授权修复); `.commands/` 提交闸门不再被挡(提交前 `test.pkg` 实测全绿, 数字见基线切片)。
- 转告(本会话不修): cap 债务 —— activeContext 切片数超阈值 + `26-10-15-0728-qb-traffic-restart-spike-gap.md` 超切片 cap; `pitfalls/testing/redverify-anchor-lineendings.md` 超 pitfall cap —— 另开会话清理。

---

<!-- slice: 26-10-18-0901-doc-topics-composite-split.md; 最后活动: 2026-10-18 09:01 -->

# doc-topics-composite-split

> 摘要: 入池 question 26-10-18-0858: 复合 Topics 键拆分为多主键与否待用户拍板(拆键改分组语义/单键改约定); 坑档已立, 存量数据未动
> 最后活动: 2026-10-18 09:01

**R0(2026-10-18 09:01):** 入池 question 26-10-18-0858: 复合 Topics 键拆分为多主键与否待用户拍板(拆键改分组语义/单键改约定); 坑档已立, 存量数据未动

---

<!-- slice: 26-10-30-0633-full-code-review-2-pooling.md; 最后活动: 2026-10-30 07:10 -->

# full-code-review-2-pooling

> 摘要: 二评 26 条发现入池落位: 17 新池位(6xP2 标准档 + 2 合并条 + 9 P3 逐条, 专题 full-code-review-2, 状态全 Open) + 3 处既有池备注回填(26-09-21-1408/26-10-20-2345/26-10-20-2231), 复验留待认领时做; kb.index/kb.check 全绿, 26/26 对账无落空
> 最后活动: 2026-10-30 07:10

**R0(2026-10-30 06:33):** 二评 26 条发现入池落位: 17 新池位(6xP2 标准档 + 2 合并条 + 9 P3 逐条, 专题 full-code-review-2, 状态全 Open) + 3 处既有池备注回填(26-09-21-1408/26-10-20-2345/26-10-20-2231), 复验留待认领时做; kb.index/kb.check 全绿, 26/26 对账无落空

**R1(2026-10-30 07:10):** 认领并修复二评批A 三条 relocate bug(resume_hashes 失败路径 / 相位机与撤销 dry_run 短路 / REBUILD-RESPAWN 退避与 attempts 上限): 11 处失败出口统一走 _fail 收口单点, on_task_line 与 relocate_cancel 补 dry_run 闸, 增 REBUILD_MAX_ATTEMPTS/REBUILD_BACKOFF/RESPAWN_BACKOFF 三常量; 三件 issue 复验仍复现后修复并置 Done

---

<!-- slice: 26-10-31-0223-kb-nav-multiselect.md; 最后活动: 2026-10-31 03:37 -->

# kb-nav-multiselect

> 摘要: kb.nav 多选与批量右键菜单: 壳 nav_page.html 多选状态/Ctrl-Shift 手势/右键批量升级(ctxTargets 单点+文案带N)/幂等批量/已选N chip/Esc 末档/Ctrl+A; 守阵 +6; test.full 全绿; Playwright 冒烟全过; 计划 26-10-31-0143 翻 Done; 基线切片 26-10-31-0219
> 最后活动: 2026-10-31 03:37

**R0(2026-10-31 02:23):** kb.nav 多选与批量右键菜单: 壳 nav_page.html 多选状态/Ctrl-Shift 手势/右键批量升级(ctxTargets 单点+文案带N)/幂等批量/已选N chip/Esc 末档/Ctrl+A; 守阵 +6; test.full 全绿; Playwright 冒烟全过; 计划 26-10-31-0143 翻 Done; 基线切片 26-10-31-0219

**R1(2026-10-31 03:20):** 验收返工: msel 靛蓝分家 + 弹窗拦截提醒; 守阵断言扩两处; 冒烟 24 项全过; 基线 26-10-31-0318

**R2(2026-10-31 03:37):** 验收返工R2: Shift 连选防原生文字选中(mousedown 守卫+click 双保险); 冒烟 25 项全过; 基线 26-10-31-0333

---

<!-- slice: 26-10-31-1209-deps-qb-5-3-support.md; 最后活动: 2026-10-31 12:09 -->

# deps-qb-5-3-support

> 摘要: 拍板 D1-D4 后实施 P1-P3: facade share_limits_mode 补参+docstring 修正 / 重加回传落点改道 _EXTENSION_FIELDS + camelCase kwarg / 升库 2026.10.1; 全量与基线切片 26-10-31-1204; P4/P5 待 5.3 stable
> 最后活动: 2026-10-31 12:09

**R0(2026-10-31 12:09):** 拍板 D1-D4 后实施 P1-P3: facade share_limits_mode 补参+docstring 修正 / 重加回传落点改道 _EXTENSION_FIELDS + camelCase kwarg / 升库 2026.10.1; 全量与基线切片 26-10-31-1204; P4/P5 待 5.3 stable

---

<!-- slice: 26-11-01-0010-memory-bank-recurrence-tooling.md; 最后活动: 2026-11-01 00:10 -->

# memory-bank-recurrence-tooling

> 摘要: 堆3四件 issue 认领并实施完成: e2e自检/写盘守卫/doc-refs（切片原文）机械化/ui-map 全部落码实测; 基线切片 26-11-01-0010
> 最后活动: 2026-11-01 00:10
**Refs（切片原文）:** memory-bank/tasks/26-10-31-memory-bank-recurrence-tooling.md

**R0(2026-11-01 00:10):** 堆3四件 issue 认领并实施完成: e2e自检/写盘守卫/doc-refs（切片原文）机械化/ui-map 全部落码实测; 基线切片 26-11-01-0010

---

<!-- slice: 26-11-01-0358-memory-bank-html-typo-fix.md; 最后活动: 2026-11-01 03:58 -->

# memory-bank-html-typo-fix

> 摘要: 修 reports/26-10-14-1110-report-hr-channel-portless-registration.html:320 同型笔误(code 闭合标签缺右尖括号致吞正文), Python 全库复扫该形态零命中, 浏览器实测 DOM 层级 LI-UL-SECTION-wrap 正常且无 code 元素吞块级内容
> 最后活动: 2026-11-01 03:58
**Refs（切片原文）:**

**R0(2026-11-01 03:58):** 修 reports/26-10-14-1110-report-hr-channel-portless-registration.html:320 同型笔误(code 闭合标签缺右尖括号致吞正文), Python 全库复扫该形态零命中, 浏览器实测 DOM 层级 LI-UL-SECTION-wrap 正常且无 code 元素吞块级内容

---

<!-- slice: 26-11-01-0442-commit-gate-scope.md; 最后活动: 2026-11-01 04:42 -->

# commit-gate-scope

> 摘要: 实测盘点 11 条提交闸门(本机单次热跑)并落收窄优化计划 26-11-01-0434: A=drift 按改动收窄(三条 run 自选) B=十连检引擎层并行 C=test.pkg 按包收窄; 用户拍板 D1 test.quick 暂不动; D2-D4 待拍板
> 最后活动: 2026-11-01 04:42
**Refs（切片原文）:**

**R0(2026-11-01 04:42):** 实测盘点 11 条提交闸门(本机单次热跑)并落收窄优化计划 26-11-01-0434: A=drift 按改动收窄(三条 run 自选) B=十连检引擎层并行 C=test.pkg 按包收窄; 用户拍板 D1 test.quick 暂不动; D2-D4 待拍板

---

<!-- slice: 26-11-01-0715-plan-status-audit.md; 最后活动: 2026-11-01 07:24 -->

# plan-status-audit

> 摘要: 五份计划完成度核实: 0434-commit-gate-scope/0705-real-machine-test/2354-webui-write-side/0446-gtm-source-acceptance 四份证据链核实完毕翻 Done(两份任务档案同步翻 Done, 0446 补收口 R2 行); 0306-torrent-transfer 维持 In Progress(W4 真机双 qB 手工验收留待用户); kb.check 全绿; 主计划 0339 S19 收口依据已具备待用户确认
> 最后活动: 2026-11-01 07:24
**Refs（切片原文）:**

**R0(2026-11-01 07:15):** 五份计划完成度核实: 0434-commit-gate-scope/0705-real-machine-test/2354-webui-write-side/0446-gtm-source-acceptance 四份证据链核实完毕翻 Done(两份任务档案同步翻 Done, 0446 补收口 R2 行); 0306-torrent-transfer 维持 In Progress(W4 真机双 qB 手工验收留待用户); kb.check 全绿; 主计划 0339 S19 收口依据已具备待用户确认

**R1(2026-11-01 07:19):** 用户指出 torrent-transfer 真机实测今天已做过: 查得 real-baselines 两切片(26-11-01-0244 首轮 20/1/1 三发现入池修复, 26-11-01-0516 再验收 23/0/0 全 PASS), 计划 §10 已有 R2/R3 记录仅头部状态滞后 —— 0306 翻 Done, 修正 0310 切片过时摘要; 至此五份计划全部 Done; kb.check 全绿

**R2(2026-11-01 07:21):** 用户指令一并更新主计划 26-10-17-0339: 核实其 doc-status 已于 26-10-31 05:40 (R5) 随 S19 验收完成收口 Done, 头部状态行与 §04 S19 验收记录均在, 零改动; 顺手修正验收档案遗留段两句过时表述(P3 已入池 0537 / S19 收口已执行); 六份计划全链路状态至此全部对齐

**R3(2026-11-01 07:24):** 提交收口: ship.commit 首跑被 v.Nu 增量闸门拦下(两计划三处存量 HTML 错误进检查面: 2354 qB<5.2 未转义 / 0446 chk span 未闭合), 就地修复后重跑过闸, 提交成功 ee12fa9c

---

<!-- slice: 26-11-01-0926-docs-action-result-pending-drift.md; 最后活动: 2026-11-01 09:26 -->

# docs-action-result-pending-drift

> 摘要: 认领修复 issue 26-11-01-0800(docs 便签): docs/configuration.md「动作结果与错误处理」段按 rules-and-triggers.md 口径补齐 ActionResult 四态(含 pending 触发条件) + on_error 三档 + 规则级 verdict 六档+retry; 纯 docs 单文件改动, issue 置 Done
> 最后活动: 2026-11-01 09:26
**Refs（切片原文）:**

**R0(2026-11-01 09:26):** 认领修复 issue 26-11-01-0800(docs 便签): docs/configuration.md「动作结果与错误处理」段按 rules-and-triggers.md 口径补齐 ActionResult 四态(含 pending 触发条件) + on_error 三档 + 规则级 verdict 六档+retry; 纯 docs 单文件改动, issue 置 Done

---

<!-- slice: 26-11-01-0439-memory-bank-html-syntax-guard.md; 最后活动: 2026-11-01 09:38 -->

# memory-bank-html-syntax-guard

> 摘要: 守卫落地: scripts/check_html.py(L1 行级正则 + L2 stdlib 解析器残缺标签名双网, script/style 遮蔽) 挂进 kb.check 与提交闸门; v.Nu 增量闸门行(changed:GLOB 只查本次改动) + kb.html-audit 全库巡检任务; 守阵四条 test_html_guard_* 入阵, test.quick 全绿(数字口径见 kb.baseline); 坑档 pitfalls/docs/html-endtag-missing-gt.md 复发 2; 存量基线 L1+L2 零命中, v.Nu 全库 320 条 error 留巡检清理
> 最后活动: 2026-11-01 09:38
**Refs（切片原文）:**

**R0(2026-11-01 04:39):** 守卫落地: scripts/check_html.py(L1 行级正则 + L2 stdlib 解析器残缺标签名双网, script/style 遮蔽) 挂进 kb.check 与提交闸门; v.Nu 增量闸门行(changed:GLOB 只查本次改动) + kb.html-audit 全库巡检任务; 守阵四条 test_html_guard_* 入阵, test.quick 全绿(数字口径见 kb.baseline); 坑档 pitfalls/docs/html-endtag-missing-gt.md 复发 2; 存量基线 L1+L2 零命中, v.Nu 全库 320 条 error 留巡检清理

**R1(2026-11-01 09:38):** 闸门扩面: v.Nu 增量面放开到全仓改动 HTML(match=.html + changed:**/*.html), 守阵/坑档/docstring 同步, 全量绿见基线切片 26-11-01-0938

---

<!-- slice: 26-11-02-0100-sync-generated-whitelist-drift.md; 最后活动: 2026-11-02 01:00 -->

# sync-generated-whitelist-drift

> 摘要: 认领并修复 issue 26-11-01-2140(bug): sync 生成物自动化解在远端新基引入新生成物路径时失效 —— 主因实证为重跑后只 add 冲突集(MM 态致 continue 被拒); 修法=暂存面扩到「白名单∩全部改动路径含新增」+ 失败行带原因分级与冲突清单; 最小复现守阵红验通过, 包级 153 过/全量见 kb.baseline 26-11-02-0059; issue 置 Done, 相邻坑档补已修注记
> 最后活动: 2026-11-02 01:00
**Refs（切片原文）:**

**R0(2026-11-02 01:00):** 认领并修复 issue 26-11-01-2140(bug): sync 生成物自动化解在远端新基引入新生成物路径时失效 —— 主因实证为重跑后只 add 冲突集(MM 态致 continue 被拒); 修法=暂存面扩到「白名单∩全部改动路径含新增」+ 失败行带原因分级与冲突清单; 最小复现守阵红验通过, 包级 153 过/全量见 kb.baseline 26-11-02-0059; issue 置 Done, 相邻坑档补已修注记

---

<!-- slice: 26-11-01-0016-memory-bank-status-drift-guard.md; 最后活动: 2026-11-02 20:30 -->

# memory-bank-status-drift-guard

> 摘要: 状态漂移机检四档判据落地联入守卫体系, 存量 B/C/D 清零(硬拦归零, 合法滞留+误报留档)
> 最后活动: 2026-11-02 20:30

**R0(2026-11-01 00:16):** 状态漂移机检四档判据落地联入守卫体系, 存量 B/C/D 清零(硬拦归零, 合法滞留+误报留档)

**Refs（切片原文）:** memory-bank/tasks/26-11-01-memory-bank-status-drift-guard.md

**R1(2026-11-02 20:30):** 低置信 C/D 清单默认收敛为一行计数并新增 --verbose 展开详情, A/B/anomalies 高置信逐条不变

---

<!-- slice: 26-10-31-0029-memory-bank-kb-nav-searchbox.md; 最后活动: 2026-11-03 01:10 -->

# memory-bank-kb-nav-searchbox

> 摘要: 搜索框清词(Esc)/快捷键聚焦 + 全局搜索支持文件名与相对路径 (navSearchText 单点, 台账/控制台频道/卡片墙共用); 守阵三条, 数字见 kb.baseline
> 最后活动: 2026-11-03 01:10
**Refs（切片原文）:** memory-bank/tasks/26-11-03-memory-bank-kb-nav-searchbox.md

**R0(2026-10-31 00:29):** 搜索框清词按钮(有词显形/syncGclear 单点)+ placeholder 移除(Esc 清空)+ / 快捷键聚焦(输入态/IME 不劫); 新守阵两条, test.full 全绿(见 kb.baseline)

**R1(2026-10-31 00:35):** 修实测居中漂移: .gsearch svg 后代选择器命中 #gclear 的 × 套了 absolute —— 收窄为 .gsearch > svg 只钉放大镜, × 回流内由 flex 居中(auto-qb .bt.icon 同机制); 守阵加 .gsearch > svg 判据; 真机几何实测 dx=0/dy=0, / 快捷键与清词点击实测过

**R2(2026-11-03 00:46):** 修 #gq 搜索按文件名/相对路径无命中: 新增 navSearchText 单点补 link 与 repository-root 相对形态, 台账/控制台频道/卡片墙三处统一消费, 正文不入索引且大小写/反斜杠归一; 原字段匹配与排序展示不变, 守阵 +1, 数字见 kb.baseline

**R3(2026-11-03 01:10):** 合流后 test.quick 红: 远端新真机守阵的受控桩依赖系统卷/祖先属性; 桩化 SystemDrive 与非 hid 属性后定向 57 passed, 最终 test.full 全绿, 处置见新基线切片首跑红节

---

<!-- slice: 26-11-03-0156-memory-bank-kb-nav-pin-zone.md; 最后活动: 2026-11-03 01:56 -->

# memory-bank-kb-nav-pin-zone

> 摘要: 置顶区标题行加折叠按钮(原生button+aria-expanded/aria-controls, 落mb-nav-pin-collapsed, 仅藏pzBody) + 置顶条目单击收成与主表共用 openRowDetail 单点(同一renderDrawer/sel高亮, Esc退档覆盖双区); 壳nav_page.html两处交互+守阵两条, 数据/服务层零改动
> 最后活动: 2026-11-03 01:56
**Refs（切片原文）:**

**R0(2026-11-03 01:56):** 置顶区标题行加折叠按钮(原生button+aria-expanded/aria-controls, 落mb-nav-pin-collapsed, 仅藏pzBody) + 置顶条目单击收成与主表共用 openRowDetail 单点(同一renderDrawer/sel高亮, Esc退档覆盖双区); 壳nav_page.html两处交互+守阵两条, 数据/服务层零改动

---

<!-- slice: 26-09-30-2112-memory-bank-cap-debt.md; 最后活动: 2026-11-03 03:59 -->

# 26-09-30-2112-memory-bank-cap-debt — cap 守卫改债务制 (WARN 不拦提交 + 独立清理会话)

> 摘要: cap 治理专题。守卫改造 2026-09-30 实施完成(除 AGENTS.md 外尺寸全降级为债务: 提交不拦、派生输出转告用户、清理另开会话; AGENTS.md 硬规定照拦), AGENTS.md 削薄已由 10-06 清理轮落地(6,853/8,000)。**2026-10-10 清理会话: 条数债务 125 > 70 清偿 —— 删 79 片留 46 片**(判据与覆盖去向见下), `SLICE_COUNT_LIMIT` 未抬、活跃片零删除。**2026-10-11 清理会话(用户令「清理 cap 债务」): 字符 cap 债务 5 项 → 0** —— 索引三件(issues 走**视图归档** `CLOSED_KEEP=60` + 全量归档索引落 `attachments/`; tasks / web-ui 类索引压渲染口径) + 手写两件按「切最老一半」外迁到 `attachments/`; 条数债务本就不超(64 ≤ 70)。判据与副产物见 [26-10-11-1745 切片](../../testing/baselines/attachments/26-10-11-1745-memory-bank-cap-cleanup.md) 与坑档 [index-archive-view(索引条目数撑爆 → 视图归档)](../../pitfalls/kb/index-archive-view.md)。**2026-10-19 清理会话: 条数债务 150 > 70 清偿 —— 删 90 片留 60 片**(冻结钉住/活跃档案/温片全保留; 49 片蒸馏复核全免蒸馏 —— 坑档纪律成熟后修复类切片全有归宿), 判据细化见下「债务判据速记」。
> 最后活动: 2026-11-03 03:59

## 状态

- 计划文档: `plans/26-09-30-2112-plan-memory-bank-cap-debt.html` (doc-status **Done**); 档案: `tasks/26-09-30-memory-bank-cap-debt.md` (Status **Done**, 状态收口轮见其进度日志 2026-10-07 条)。
- **D1/D2/D3 全部拍板 (2026-09-30)**: AGENTS.md = 硬规定(不套 50%、不入债务体系、无止损线); D2 —— 切片条数阈值归债务通道(`_common.SLICE_COUNT_LIMIT`)。
- **2026-10-09 清理轮**(档案外迁 + tasks/issues 索引压截断): 见基线切片 [26-10-09-0832](../../testing/baselines/attachments/26-10-09-0832-memory-bank-cap-cleanup.md); 当时明记「切片数 104 > 70 的条数债务仍在, 需另开清理会话」。
- **2026-10-10 本轮(用户令「存量 cap 债务: 基线切片数 125 > 70, 按规则修改」)**: `activeContext/` **125 → 46 片**(删 79), 判据沿用 26-10-06 清理轮成例三条件 + 两条硬约束:
  ①**硬约束一 —— 真实 md-link 入链不可删**: 全库扫描(链接目标逐个解析到真实目录, 区分同名基线切片)实测仅 5 片被 md 链接引用 —— 1 片被冻结基线链(`26-09-30-1007`, 基线是一次性快照不回写), 4 片被 append-only 流水 `implemented-webui-history.md` 链(2026-10-05 坑档判定 append-only 不可改)—— 全部保留; 其余 60+ 片的「引用」全是纯文本提及(`doc.links` 判据是相对链接存在性, 不扫纯文本), 删除不产生机检红。
  ②**硬约束二 —— 活跃状态不删**: 切片或其档案为 In Progress/Open 的 9 片全保留(热重载路线图被接替的例外: 计划已 Superseded, 状态事实经核实后按已完结处理)。
  ③**删除集 = 79**: 档案 Done 且 ≥12h 的 53 片(内容已在档案, 滚动状态完成使命) + 无档案且 ≥5 天的 26 片(蒸馏进 `progress/` 五个 implemented-*.md 后删除; 其中 kb-nav-page / shortcuts-toggle / drawer-merge-tabs / tracker-url 四片确认 progress 已有覆盖, 免蒸馏)。
  ④**保留 46**: 5 md-linked + 9 活跃 + cap-debt 专题片 + 近 5 天无档案的滚动状态片(26-10-10 当天片全留) + 26-10-10 清理轮自身。
- **蒸馏落点**: 无档案旧片按域压缩成 26 条新条目 —— core 7 / webui 5 / perf 2 / testing 9 / tooling 3(含 CI 计时口径、HR 守阵族、run_capture 看门狗等; 守阵与坑档单点均为事实源, 条目只留指针); 5 个 progress 文件全部仍在 20,000 cap 内。
- **链接改指**: 可编辑面 11 处(tasks 1 / progress 1 / cap-debt 片互链 1 / `docs/hr-online-verify-docs.md` 8 —— docs 不在守卫扫描面但属人读文档, 指向删除目标的链接改指档案/报告/progress)。冻结件(基线/报告/计划 HTML)零改动。
- 本轮改动全部随本提交入库; 收口机检 `kb.check` / `doc.links` / `doc.caps -- --strict` / `kb.active` 全绿(数字见基线切片)。

- **2026-10-11 清理轮(字符 cap 债务 5 → 0)**: 开工 `doc.caps -- --strict` 报 5 项 ——
  `issues/_index.md` 31,196 / `tasks/_index.md` 25,974 / `pitfalls/web-ui/_index.md` 25,940 /
  `progress/implemented-webui.md` 23,251 / `tasks/26-10-08-test-mutation-audit.md` 56,960。
  按「先量无摘要口径」分三路(详见 [26-10-11-1745 切片](../../testing/baselines/attachments/26-10-11-1745-memory-bank-cap-cleanup.md)):
  ①issues 侧无摘要口径 27,336 = cap **108%**(条目数撑爆)⇒ **视图归档**(文件不动, 只出索引);
  ②tasks / web-ui 侧无摘要口径仍 < cap ⇒ 压**渲染口径**; ③两件手写文档按「切最老一半」外迁。
  **未抬任何 cap、未调 `SLICE_COUNT_LIMIT`**。收口 `doc.caps` 0 债务 / `doc.links` 绿 / `kb.check` 全绿 /
  test.full **3124 passed + 4 skipped**(基线切片 `testing/baselines/attachments/26-10-11-1745-memory-bank-cap-cleanup.md`)。

- **2026-10-13 清理轮(用户令「清理cap债务」; 字符 cap 债务 3 → 0)**: 开工 `doc.caps` 报 3 项 ——
  `modules/webui-static-contract.md` 34,647 / `pitfalls/web-ui/drawer-switch-flicker.md` 16,813 /
  `testing/guards.md` 24,174 (条数债务 94>70 本会话不修, 治理政策未拍板不调)。三件按「触顶外迁原文到
  `attachments/` 留一行指针, 随迁相对链接整体上移一层」处置 —— 主档落 7,823 / 10,319 / 9,889 (≤ 50% 线);
  另 kb-nav-page 切片 13,988 撞 slice cap 蒸馏跟进轮九~十七进 `progress/implemented-tooling.md` → 5,675。
  收口 `doc.caps --strict` 0 债务 / `doc.links` 绿 / `kb.check` 全绿 / test.full **3192 passed + 4 skipped**
  (基线切片 `testing/baselines/attachments/26-10-13-0914-memory-bank-cap-debt-cleanup.md`)。

- **2026-10-19 清理轮(用户令「清理:切片总数 150 > 70」; 条数债务 90 片清偿, 150 → 60)**: 判据沿用 10-10 成例 + 机检判据细化三分(见速记 2026-10-19 补):
  ①**删除集 = 90**: 档案 Done/Dropped 且 ≥12h 的 41 片(其中 24 片先摘除 tasks 档案 `**Refs（切片原文）:**` 里的切片 token、空则整行删 —— docmap 声明方强校验目标存在, 不清即闸门红) + 无档案且 ≥5 天的 49 片(**蒸馏复核全免蒸馏** —— 逐片语义关键词 grep `progress/`+`pitfalls/`+`tasks/`, 全部已有专属坑档或同专题档案/报告/计划归宿; slug 字面搜索漏报率极高, 不得用它判覆盖)。
  ②**保留 60**: 冻结面钉住 16(基线 .md 真实 `](` 链接 ×2 / append-only 流水链接 ×4 / plans·reports·issues `doc-refs（切片原文）` ×10 —— 声明方冻结不可改, 切片必须留) + 活跃档案(In Progress/Open)22 + 近 5 天无档案温片 21 + 本专题片 1。
  ③收口 `kb.check`(主键 733 / 认领链双向闭环) / `doc.links` / `doc.caps` / `kb.active`(页脚 60 ≤ 70, 条数债务行消失) 全绿; test.full 数字见新基线切片。`SLICE_COUNT_LIMIT` 未动。两处超长切片(15-0728 19,375 / 16-0541 14,305)属字符债务, 随既有 4 项(doc.caps)另行清理。

- **2026-11-02 清理轮(用户令「只清偿一条 kb.check 债务: 切片总数 162 > 70」; 条数债务 92 片清偿, 162 → 70)**: 判据沿用 10-19 成例三查 + 声明方二分(冻结件指向谁谁留 / 可编辑 Refs 摘 token 后可删 / 纯文本提及容忍):
  ①**删除集 = 92**: 档案 Done/Dropped 且 ≥12h 的 47 片 + 无档案且 ≥5 天的 12 片 + 已完结且有落点的温片按「最老优先」补退 33 片(开放决策片不参与 —— 正文引用 Open/In Progress 件或所属档案未收口的一律留)。
  ②**保留 70**: 冻结声明方/链接钉住 26(plans·reports·issues `doc-refs（切片原文）` + 基线 `.md` 真实 `](` 链接 + append-only 流水链接, 含本专题片 1) + 活跃档案(In Progress/Open) 13 + 开放决策片(正文引用 Open/In Progress 件) 15 + 其余最新温片 24(三类重叠, 唯一保留 70)。
  ③**落点逐片核对, 本轮零 progress 新增**: 有档案 → 任务档案; 无档案 → Done issue/plan/report/baseline attachments/pitfall/skill(`testing/real-machine.md`、`deps-upgrade` skill 等); 纯代码修复 → 代码与守阵 + 对应坑档/基线切片。无「落点空白」片, 故不向已超 cap 的 `progress/` 追加。
  ④收口 `kb.check`(切片数 70 ≤ 70, 条数债务行消失) / 认领链 / docmap / 守卫测试见提交说明与基线切片。基线字符债务 `26-11-01-0722`(8,057 > 8,000)按用户边界**未动**。

## 债务判据速记(后续清理会话直接复用)

- 条数债务由 `commands run kb.active` 页脚现算(`SLICE_COUNT_LIMIT = 120` / `SLICE_COUNT_TARGET = 80`, `_common.py` 单点; 2026-11-03 拍板 70→120), 达到即告警、不拦提交; `doc.caps` 的债务组不含条数(它只管字符 cap), 所以会出现「doc.caps 报 0 债务而 kb.active 报条数超」的口径差。
- 清理动作 = 蒸馏进 progress/任务档案后删除, **不是调 cap**; 一次清理要做到 `SLICE_COUNT_TARGET`(80 条)以内, 抬 `SLICE_COUNT_LIMIT` 等于把收口线推走, 属治理政策(2026-11-03 已由用户拍板), 各会话不自行调数。
- 删前逐片三查: 档案状态 / 真实 md 入链(解析到目录, 别只匹配文件名 —— 同名基线切片是最大陷阱) / 是否开放决策片。
- 2026-10-19 机检判据细化: 「真实 md 入链」只是机检面的一半, **声明方在不在 docmap 决定 Refs 是否强校验** ——
  ①冻结声明方(plans/reports/issues HTML `doc-refs（切片原文）`、基线 .md 与 append-only 流水的 `](` 链接) ⇒ 指向谁谁就得留;
  ②可编辑声明方(tasks 档案 `**Refs（切片原文）:**` —— gen_doc_map 只认首个 Refs 行 —— 与可编辑 md 的 `](` 内链) ⇒ 摘 token/改指后可删, 空 Refs 行整行删;
  ③纯文本提及(基线 `**Refs（切片原文）:**`、坑档/progress/slices 的 Refs —— `doc.links` 与认领链都不扫) ⇒ 容忍不动。
  逐片蒸馏复核用**语义关键词** grep progress/pitfalls/tasks/conventions —— slug 字面搜不准(用词不同漏报率极高, 本轮 49/49 免蒸馏全靠语义命中)。

**R1(2026-10-19 23:00):** 条数债务清偿 150>70: 删 90 片留 60(16 冻结声明方/链接钉住 + 22 活跃档案 + 21 近5天温片 + 1 专题片), 49 片蒸馏复核全免蒸馏(坑档/同专题档案/报告/计划已覆盖), 29 档案 Refs 摘除死 token; 收口 kb.check/doc.links/kb.active 全绿, test.full 数字见新基线切片

**R2(2026-11-02 22:22):** 切片债务清偿 162->70: 退役 92 片(档案 Done/Dropped >=12h + 无档案 >=5d 按 2026-10-19 成例三查, 再按已完成/有落点/最老优先补退温片), 保留冻结链 26 + 活跃/开放决策片 + 最新温片 19; 落点为 Done 档案/issue/report/baseline/pitfall/skill; kb.check 切片数回落到 70

**R3(2026-11-03 03:59):** activeContext 切片上限 70→120、处置目标 80: 常量收敛 _common.SLICE_COUNT_LIMIT/TARGET, kb.active 达到即告警不拦(--check rc 0), 守阵 4 判据 + 协议文档口径同步

---

<!-- slice: 26-11-03-0637-memory-bank-code-review-3-s0.md; 最后活动: 2026-11-03 06:37 -->

# memory-bank-code-review-3-s0

> 摘要: S0 完成: 底册四表(Open 54→57 / 坑档 7 类 277 条 / 在途计划 5 件 / 二次 26 条去向)落 task 文档, 入池 3 条计划底数漂移, 报告骨架建成, 计划仅推进状态
> 最后活动: 2026-11-03 06:37
**Refs（切片原文）:**

**R0(2026-11-03 06:37):** S0 完成: 底册四表(Open 54→57 / 坑档 7 类 277 条 / 在途计划 5 件 / 二次 26 条去向)落 task 文档, 入池 3 条计划底数漂移, 报告骨架建成, 计划仅推进状态

---

<!-- slice: 26-11-03-0723-memory-bank-code-review-3-s1.md; 最后活动: 2026-11-03 07:23 -->

# memory-bank-code-review-3-s1

> 摘要: S1 完成: 479 文件三类打标(实质 294/move-only 185/未变 0), B1-B10 矩阵定稿 0 漏 0 重, R1-R4 配对表, 入池 3 条; 零代码改动
> 最后活动: 2026-11-03 07:23
**Refs（切片原文）:**

**R0(2026-11-03 07:23):** S1 完成: 479 文件三类打标(实质 294/move-only 185/未变 0), B1-B10 矩阵定稿 0 漏 0 重, R1-R4 配对表, 入池 3 条; 零代码改动

---

<!-- slice: 26-11-03-0903-memory-bank-code-review-3-s2.md; 最后活动: 2026-11-03 09:03 -->

# memory-bank-code-review-3-s2

> 摘要: S2 完成 B1-B4 共 53 件评审(零代码改动): 入池 3 条(1 P2 + 2 P3), test.quick 4927 passed/10 skipped, 计划 S2 已推进 Done
> 最后活动: 2026-11-03 09:03
**Refs（切片原文）:**

**R0(2026-11-03 09:03):** S2 完成 B1-B4 共 53 件评审(零代码改动): 入池 3 条(1 P2 + 2 P3), test.quick 4927 passed/10 skipped, 计划 S2 已推进 Done

---

<!-- slice: 26-11-03-1041-memory-bank-code-review-3-s3.md; 最后活动: 2026-11-03 11:24 -->

# memory-bank-code-review-3-s3

> 摘要: S3 就地收尾：B5 主体过目 + B6 四组 R12 等价(0/0) + 定向 e2e 148p/16s + 入池 P1 与 e2e 断裂两条, 留 flux CSS/config_rules 续接
> 最后活动: 2026-11-03 11:24
**Refs（切片原文）:**

**R0(2026-11-03 10:41):** S3 就地收尾：B5 主体过目 + B6 四组 R12 等价(0/0) + 定向 e2e 148p/16s + 入池 P1 与 e2e 断裂两条, 留 flux CSS/config_rules 续接

**R1(2026-11-03 11:24):** 补完 flux CSS 全量扫描(14 文件/350KB/33 冲突逐条判定)与 config_rules 契约对照, B5 覆盖闭合, 新增 3 条 issue, 状态转 Done

---

<!-- slice: 26-11-03-1150-memory-bank-code-review-3-s4.md; 最后活动: 2026-11-03 11:50 -->

# memory-bank-code-review-3-s4

> 摘要: S4 完成 B7 33 件 + B8 8 件逐文件评审；test.gtm 1 failed 已入池；4 条发现入池（P1×1/P2×1/P3×2）；扩展安全复核无新增可证实风险
> 最后活动: 2026-11-03 11:50
**Refs（切片原文）:**

**R0(2026-11-03 11:50):** S4 完成 B7 33 件 + B8 8 件逐文件评审；test.gtm 1 failed 已入池；4 条发现入池（P1×1/P2×1/P3×2）；扩展安全复核无新增可证实风险

---

<!-- slice: 26-11-03-1213-memory-bank-code-review-3-s5.md; 最后活动: 2026-11-03 12:13 -->

# memory-bank-code-review-3-s5

> 摘要: S5 完成 B9 245+40 件与 B10 系统漂移审计；6 条发现入池（test×2/docs×4）；拆分等价 0 丢失 0 重复；无 P0/P1
> 最后活动: 2026-11-03 12:13
**Refs（切片原文）:**

**R0(2026-11-03 12:13):** S5 完成 B9 245+40 件与 B10 系统漂移审计；6 条发现入池（test×2/docs×4）；拆分等价 0 丢失 0 重复；无 P0/P1

---

<!-- slice: 26-11-03-1232-memory-bank-code-review-3-s6.md; 最后活动: 2026-11-03 12:32 -->

# memory-bank-code-review-3-s6

> 摘要: S6：六对跨批契约核对（5 一致/1 不一致）+ 18 条分级终表（P0 0/P1 2/P2 8/P3 8）+ HEAD fbfc2825 可达性复验（P1 实证）+ 去重闭环 75=50+25 + test.gtm 绿；零代码改动，新增 issue 0
> 最后活动: 2026-11-03 12:32
**Refs（切片原文）:**

**R0(2026-11-03 12:32):** S6：六对跨批契约核对（5 一致/1 不一致）+ 18 条分级终表（P0 0/P1 2/P2 8/P3 8）+ HEAD fbfc2825 可达性复验（P1 实证）+ 去重闭环 75=50+25 + test.gtm 绿；零代码改动，新增 issue 0

---

<!-- slice: 26-11-03-2153-docs-doc-drift-sweep.md; 最后活动: 2026-11-03 21:53 -->

# docs-doc-drift-sweep

> 摘要: 7 条文档漂移 issue 全部认领并处置: 0557 计划域表补 src/auto_qb/tools 行(合计 479)、基线改引 0534/S7 切片 1245、在途清单按终验复验更新、底册按 S0 实测 54/2/359/3/6(合计 424, test 5)与 18 池位回写; 0221/1036 清理 9 条 v.Nu error 并恢复与 0557 双向 doc-refs（切片原文）; minimal.yml 16585→8080, config-reference 与 sim 文档端口口径修正; 全量 test.full 零源码改动(数字见基线切片 26-11-03-2146)。
> 最后活动: 2026-11-03 21:53
**Refs（切片原文）:**

**R0(2026-11-03 21:53):** 7 条文档漂移 issue 全部认领并处置: 0557 计划域表补 src/auto_qb/tools 行(合计 479)、基线改引 0534/S7 切片 1245、在途清单按终验复验更新、底册按 S0 实测 54/2/359/3/6(合计 424, test 5)与 18 池位回写; 0221/1036 清理 9 条 v.Nu error 并恢复与 0557 双向 doc-refs（切片原文）; minimal.yml 16585→8080, config-reference 与 sim 文档端口口径修正; 全量 test.full 零源码改动(数字见基线切片 26-11-03-2146)。

