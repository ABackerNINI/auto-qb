# 测试基线 · 变更流水

> 摘要: 测试基线的**逐次增量流水**(最近在上), 每次增删用例都记一条 —— 用来回答"这个数字是怎么来的"。
> 触发: 基线为什么是这个数, 某条用例何时加的, 覆盖率变化, 历史增量

> 迁移说明(2026-09-22 W3): 本节原在 `testing.md` 顶部的 ```bash 围栏里当注释, 现原样外迁 ——
> **只把 bash 注释标记转成 markdown 列表缩进**(内容逐字未改)。**当前数字**见 [baseline.md](baseline.md)。

> **更早的流水已外迁** → [attachments/baseline-history-archive.md](attachments/baseline-history-archive.md)
> (append-only 流水触顶时的处置: 从最老一端切到本文件 ≤ 16,000 字符, 原位留本行指针)

- ↑ 收集数 **1375 → 1377**(**+2**; 2026-09-24 **WEB UI 多选右键菜单目标 = 整个选中集合** + **生成物重建提示指错命令**):
  ①`test_web.py::test_frontend_ctx_menu_multi_select_targets_selection` —— 用户报"多选时右键菜单
  应该对所有选择的种子生效, 当前仅对鼠标指向的触发右键的种子生效"。根因: 四个 `open*Menu`(组/成员/剧/集)
  只记 anchor(`key`/`hash`/`episode`), 动作端点直接拿它拼 URL ⇒ 无论选了多少都只动被点的那一个
  (菜单照常弹出、照常成功、**无任何报错**, 肉眼难辨)。修法: `menu.js::_ctxMulti` 判"这一行属于选中集合
  且集合范围 ≠ 该行自身范围"(判据**不是**"选中数 > 1" —— 否则"选中 1 个辅种 + 右键它的成员行"会给出
  文案说"该种子"、实际动整组的错菜单), 四入口各写 `menu.multi`; 双 UI 模板加 `v-if="menu.multi"` 批量分支,
  动作整份复用批量浮条链路(`commands.js::ctxAct`→`bulkAct` / `ctxDelete`→`bulkDelete`), 不另拆目标集合。
  守阵钉三处成对关系(四入口写 `multi` / 双 UI 分支逐项一致 / `ctxAct` 复用 `bulkAct`), 两处红验过;
  冒烟 `scripts/ui_smoke.cjs` +12 条 CTX-03(双 UI × 六: 三视图批量菜单 / 未选中行负向对照 /
  合单一条 bulk / 乐观覆盖), 已对 HEAD 红验(prism 三条变红)。冒烟三模式 84/84/8 全 0 失败。
  ②`test_memory_bank.py::test_gen_cmd_hints_name_real_tasks` —— 修上一条报告、本轮由用户指令
  「修复既有缺陷然后提交」的既有缺陷: `_common.gen_cmd()` 忽略传入的脚本名、一律返回
  `commands run kb.index`, 而 `kb.index` 只跑 `gen_tasks_index` + `gen_kb_index` ⇒ `_doc-map.md` /
  `plans|reports/_index.md` 的报错文案把用户指向一条**跑完仍然红**的命令(提交闸门 `my-commit-flow`
  的 `memory-bank/` 一条早就挂了这四条的 `--check` ⇒ "闸门能红、却没有一条能修的命令")。
  修法两条一起: `kb.index` / `kb.check` 补上 `gen_docs_index.py` + `gen_doc_map.py`(与闸门**同集**) +
  `_common.GEN_CMD_BY_SCRIPT` 按脚本查表(`gen_active_recent.py` → `kb.active --check`, 它是只校验的)。
  守阵钉"调用点全覆盖 / task id 真实存在 / 提示说跑 `kb.index` 的脚本必须真在它的 run 列表里",
  两处红验过, 并端到端复现原症状(写坏 `_doc-map.md` → 照文案跑 `kb.index` → `--check` PASS)。
  ⚠ 本批与主线 `5c518b3`(HR 在线核实 M1, +142)合流: 按「移出改动 → `merge --ff-only` → 施回改动」
  同步(全程未用 stash/rebase), 基线数字取**合流后实测**; 流水轮转沿用主线的**两级方案**
  (`-archive.md` = 中间段 / `-old.md` = 最老段) —— 我此前并入 `-old.md` 的那 15 条**已撤**,
  因为它们已在 `-archive.md` 里(避免同一段历史存两份)。

- ↑ 收集数 **1233 → 1375**(+142; 2026-09-24 **HR 在线核实 M1: 核心管道**):
  用户令「实施该计划」(部分种子 HR 的在线核实), 并指定页面样本 `D:/Projects/站点页面/BTSchool`
  与前期实验脚本 `scripts/hr_fetch_experiment.py` 为输入。本轮落地计划的 **M1(离线可做)**:
  新包 `src/auto_qb/hr/` —— `bencode`(infohash 取 info 的**原始字节切片**, 定位跨度时只跳不建对象) /
  `parse`(栈式表格抽取 + 数值容错) / `adapters`(NexusPHP `myhr.php` 九列形态) /
  `model`(站点文件内的账号级状态) / `store`(**每站点一个 JSON + 一把 filelock**, 持锁期间完成
  「读→判有效期→必要时抓→写→释放」; revision 回退 / 心跳被覆盖 ⇒ 退化只读) /
  `ratelimit`(间隔 **只向上抖动** + 小时/天两级配额 + 失败退避熔断 + 时间窗) /
  `resolve`(**三态判定** = 受管束 / 已核实不受管束 / 未核实 + 不可变只读视图) /
  `service`(刷新管道; `dry_run` 零请求零写入、`hr.once` 抓取但不写盘) / `report`(`--hr-once` 走查) /
  `fetcher`(取数通道协议; 后端零 cookie、不直连站点)。
  配置接入全链路: `KNOWN_*_KEYS` + 校验器(**站点 mode != off 但没配 hr 段 ⇒ 配置期直接报错**,
  否则 `check_hr_condition` 恒 False、整站保护静默失效) + `config/schema/hr.py` + 新分组 +
  `HR_CHECK_FIELD_LEVELS`(热重载分级) + loaders; 设置页 Hub 补 `hr_check` 文案 / 未启用判定 / 读数。
  新增 8 个测试文件 + 共享夹具 `tests/hr_helpers.py` 与**脱敏页面 fixture**(取自真实样张结构:
  含 `<td class="embedded">` 包裹表、灰色不可点的「下一页」、免罪链接); 覆盖 bencode 钉死向量 /
  原始切片 vs 重编码(钉死计划 §5 的坑) / 畸形输入 / 表头缺失=改版 vs 表头在 0 行=合法空 /
  防重取三层 / 有效期复用零请求 / 翻页未到底 ⇒ 覆盖证明不成立 / **判定表逐行** /
  **新鲜度闸门不可被 `unknown_policy` 绕过** / 熔断 / 并发锁粒度 = 站点。
  红验方式: 11 条首跑真红(见提交说明), 逐条定位后全绿。
  全量 **1374 passed + 1 skipped** / TOTAL 91%(9278 语句 / 727 未覆盖 / 3128 分支 / 277 partial) /
  sidefx 台账 2212 / 越界 0。⚠ 余下 **M2(取数通道 + 取数线程) / M3(判定联动四消费点) / M4(多站点)**
  未落地 —— 本档案「子任务状态表」逐项记状态。

- ↑ 收集数 **1232 → 1233**(+1; 2026-09-24 **WEB UI 添加种子回执与 optional 选项**):
  用户报"添加种子显示失败 + 桌面弹 WARNING 但实际添加成功, 且「添加后开始」不生效"。三条根因:
  ① 回执只认 `"Ok." in str(result)`, 而 qB 5.2+(Web API 2.14.0)的 `/torrents/add` 已改回 JSON 元数据
  (`TorrentsAddedMetadata`, dict 子类)⇒ 判定恒假; ② 停止位被"False 就不传"的过滤器吞掉 ⇒ qB 回落到
  **会话级**默认 `isAddTorrentStopped()`, 勾了也按停止添加; 另 qbittorrent-api 的
  `is_paused or is_stopped` 会把 `is_paused=False` 折成 `None`(实测请求体空串)⇒ 只能用 `is_stopped=`;
  ③ 成功路径记 WARNING, 而 NotifyHandler 挂在 `auto_qb` logger 上 ⇒ 每次成功都推桌面弹窗。
  同轮按用户"修复同类隐患"把 `use_auto_torrent_management` 一并改成恒显式(它同为 `std::optional`,
  未勾 + 未填保存路径时会吃 qB 全局管理模式); 判据升级为"看 `addtorrentparams.h` 的字段类型 ——
  optional 的必须显式, 普通 bool 省略安全"。
  修法: 新增 `webui/commands.py::_add_outcome` 双形态判定 + 恒显式下发 `is_stopped` /
  `use_auto_torrent_management` + 成功 INFO / 未受理才 WARNING。替身同步补 `is_stopped` 与
  `is_stopped_raw`(保真度)。用例名 `test_add_torrent_receipt_and_optional_flags`(四条断言全红验)。
  两条新坑写进 [pitfalls/backend/qb-api.md](../pitfalls/backend/qb-api.md) 与
  [pitfalls/testing/stubs-sim.md](../pitfalls/testing/stubs-sim.md)(含 `make_manager` 清 root handlers
  ⇒ 用例体内建 manager 时 caplog 恒空)。⚠ 本轮开工时与主线齐平, 提交前发现主线已前进 2 个提交
  (`9d7a3eb` / `2e2e2b5`)⇒ 按"移出改动 → `merge --ff-only` → 施回改动"同步(重叠仅 3 个文件:
  两个基线文档 + 生成物 `tasks/_index.md`), 故本条收集数在**合流后**的 1232 基础上 +1。
  全量 **1232 passed + 1 skipped** / TOTAL 91%(7782 语句 / 622 未覆盖 / 2648 分支) / sidefx 2067 / 越界 0。

- ↑ 收集数 **1225 → 1232**(+7; 2026-09-24 **commands 引擎子进程编码**):
  用户报「跑 `commands run kb.index` 输出乱码」。取证: 引擎自己的 stdout 是 UTF-8(`uv run` 给的),
  但它 `shell=True` 起的**孙进程**(`kb.index` 的第二条包脚本)的 stdout 被管道接住时按**本地码页 cp936**
  输出 ⇒ 引擎按 UTF-8 硬解 ⇒ 「已生成 16 个索引」变 `������ 16 ������`。拓原始字节确认是 GBK
  (`b'\xd2\xd1\xc9\xfa\xb3\xc9 16 \xb8\xf6\xcb\xf7\xd2\xfd'`), **退出码照旧 0** —— 静默的坏, 只影响人读。
  修法(引擎单点, 不动任何包脚本): ① 子进程环境注入 `PYTHONIOENCODING=utf-8`(只影响 stdio, 不像
  `PYTHONUTF8=1` 连 `open()` 默认编码一起改; 放在 pack env 之前, 包仍可覆盖) ② `_shell` 改**按字节收** +
  `_decode` 兜底解(UTF-8 → 本地码页 → `errors="replace"`) —— 非 Python 子进程仍可能给 GBK, 这一层兜住。
  新增 7 条守阵(全在 `tests/test_commands_engine.py`), **红验**用 A/B 对照(修前解出 `������ 16 ������`,
  守阵对差异敏感)。❗测试里**不真起子进程** —— `tests/sidefx.py` 的 POPEN 记账会判越界,
  所以用假 `subprocess.run` 直接给字节。坑与判据写进
  [pitfalls/ops/console-encoding.md](../pitfalls/ops/console-encoding.md), 引擎约定写进
  [`.agents/skills/commands/references/howto-add-command.md`](../../.agents/skills/commands/references/howto-add-command.md)。
  全量 **1231 passed + 1 skipped** / TOTAL 91%(7768 语句 / 623 未覆盖) / sidefx 台账 2049 / 越界 0。

- ↑ 收集数 **1216 → 1225**(+9; 2026-09-24 **commands W7: wrapper 入口**):
  用户要求「真正实现 `commands run <task.id>`」。先实测三个 shell 对 cwd 的搜索规则(Git Bash 与 PowerShell
  **都不搜**, 只有 cmd.exe 搜)⇒ 只落仓库根达不到目标, 与用户确认后落 **cwd + PATH 目录**两处: 新增生成器
  `install_wrapper.py`(幂等 / 只认自己的标记行 / 生成物 gitignore / 装完自证), 解释器优先 `uv run python`
  (包脚本以引擎的 `sys.executable` 执行, 这决定它们跑在系统 python 还是项目 venv)。
  实测撞到 6 个坑, 全部写进 [pitfalls/backend/platform-fs.md](../pitfalls/backend/platform-fs.md):
  批处理 `rem` 含引号/括号/反引号 → 静默退出 2 且无输出 · `.cmd` 必须 CRLF · 消息必须 ASCII ·
  CreateProcess 不认 shebang(WinError 193) · Git Bash 的 PATH 条目是 MSYS 形态(直接比永远不相等) ·
  `os.access(W_OK)` 在 Windows 目录上给假否定。同轮把「低噪音包」八条判据写进 `howto-add-command.md`。
  新增 9 条守阵(含端到端真跑 wrapper), 全量 **1224 passed + 1 skipped** / TOTAL 91%(7768 语句 / 623 未覆盖)
  / sidefx 2051 / 越界 0(sidefx 放行面收窄到「临时目录里的 `commands` / `commands.cmd`」)。

- ↑ 收集数 **1208 → 1216**(+8; 2026-09-24 **commands 引擎的会话噪音治理**):
  用户走查上一轮提交流程后指出"噪音多、没达到设计初衷"。逐条取证后改: 引擎 `run` 的摘要从
  "只取末 3 行"改成**末几行结论 + 异常行**(只取末行会让检查表里 "2 项 WARN" 的**内容**消失,
  实测逼出一次预检重跑 21s×2)、task id 认包路径限定写法(`包/子包.<task>`)、闸门 PASS 行从
  ≈1.5 KB 命令全文收成一行、开工自检给出**可执行的同步配方**(含文件重叠判定)、
  包/引擎的 47 条脚本测试首次挂上闸门。新增 `tests/test_commands_engine.py` **8 条**(均已在还原版上红验);
  包内测试 34 → **47 条**(+13: `sync_recipe` 判定矩阵 / `summarize_gates` / `_short`)。
  全量 **1215 passed + 1 skipped** / TOTAL 91%(7768 语句 / 623 未覆盖 / 2646 分支) / sidefx 2036 / 越界 0。
  细节见 [pitfalls/kb/scripts.md](../pitfalls/kb/scripts.md)(摘要要按异常行挑)与
  [tasks/26-09-23-commands-unified-surface.md](../tasks/26-09-23-commands-unified-surface.md) 的 W6。

- ↑ 收集数 **1203 → 1208**(+5; 2026-09-24 **WEB 事件循环断连噪音降级**):
  用户报障 `ERROR - Exception in callback _ProactorBasePipeTransport._call_connection_lost(None)`
  (`ConnectionResetError [WinError 10054]`) —— 判定为**网络波动**(对端 RST 后 asyncio 仍调
  `sock.shutdown`), 非本项目 bug。修法: `webui/server/lifecycle.py` 新增
  `_web_loop_exception_handler`(波动型降级为一行 INFO + 60s 窗口节流, 其余异常照旧交给
  asyncio 默认处理器) + `_QuietLoopConfig.get_loop_factory()` 把处理器挂到服务循环上。
  新增 5 条守阵(降级 / 节流 / 真 bug 不吞 / 判定矩阵 / 处理器装载), **均已在还原版上红验**;
  真机复现: 原生 `uvicorn.Config` 打 ERROR + traceback, 换 `_QuietLoopConfig` 后同一异常只剩一行 INFO。
  `lifecycle.py` 覆盖率 **96%**; 全量 **1207 passed + 1 skipped** / TOTAL 91%
  (7768 语句 / 623 未覆盖 / 2646 分支) / sidefx 2034 条 / 越界 0。
  判别法与处置见 [pitfalls/backend/platform-fs.md](../pitfalls/backend/platform-fs.md)。

- ↑ 收集数 **1202 → 1203**(+1; 2026-09-24 **浏览器站点级"关闭时清除站点数据"取证 + 空存储提示加固**):
  新增 `test_frontend_cols_empty_hint_names_browser_clear_cause` —— 钉住"空存储提示"必须同时点名
  ①origin 隔离(换地址/端口) ②浏览器站点级「关闭窗口时清除 Cookie 和站点数据」(Chromium cookie
  例外 `setting=4` = SESSION_ONLY, 会连 localStorage 一起清), 给出自查路径, 并要求用 sessionStorage
  做"同一次会话只弹一次"的兜底(清站点数据的环境下 localStorage 里的去重标记也会一起没)。
  全量 **1202 passed + 1 skipped** / TOTAL 91%(7729 语句 / 623 未覆盖 / 2636 分支; 串行实测) / 越界 0。
  取证原文与机理见 [pitfalls/web-ui/columns-persist.md](../pitfalls/web-ui/columns-persist.md)。

- ↑ 收集数**不变**(**1192**; 2026-09-23 **全量测试耗时归因与优化**, 见 [tasks/26-09-23-test-suite-perf.md](../tasks/26-09-23-test-suite-perf.md)):
  **未增删用例**, 只做三处实测优化 + 补一份坑档 —— ①`tests/sidefx.py` 的 `report()` 把 `violations`
  提到循环外(原写法每种 kind 重算一次 = 8 次 × 约 1600 条路径 × `os.path.realpath`)⇒ 收尾 teardown
  **4.71~8.97s → 1.04~1.20s**; ②`tests/test_web.py` 的前端 JS 语法守阵由"20 次 `node --check` 进程"
  改为**单进程批量**(`node -e` + `Module.wrap`; 裸 `vm.Script` 会把顶层 `return` 判错, 已对齐为
  与 `--check` **8/8 一致**)⇒ 7.375s → 0.378s, `test_frontend_static_bundle_health` 4.06s → 0.27s;
  ③修三处临时目录泄漏(`test_web` / `test_expr_eval` / **探针新查出** `test_trigger_events`)⇒
  探针实测"每次全量建 **577** 个临时目录, 收尾残留 **2 → 1**", 剩下的 1 个是
  `test_checking.py:155` 的模块级持有者, 进程退出即回收。全量 1191 passed + 1 skipped / TOTAL 91% / 越界 0。
  ⚠ **耗时数字改口径**: 旧记录写单值(139.07s), 本轮同一条命令多次实测为
  **62~114s**(中位约 75s, 极差 1.8 倍; 逐次枚举见 [baseline.md](baseline.md))
  ⇒ 基线耗时**改为区间**, 理由与成因见 [baseline.md](baseline.md) 与
  [pitfalls/testing/perf-measurement.md](../pitfalls/testing/perf-measurement.md)。
  同日续: 用户把**三盘 Temp 目录**加入文件安全白名单后复测, **写 20.19 → 0.58ms(34×)**、
  串行中位 **75 → 61s**(54~81s); 但 `os.remove` 14.6ms / `os.rmdir` 52.7ms **仍被拦**
  (一次全量 577 个临时目录 ⇒ 删除类 ≈ 26s, 占 44%)。并行 `-n 4` 中位 ~31s 但尾部最坏 209.77s。
  同日再续: 用户继续调整设置后**删除也被治好** —— 四类操作全部 <1ms
  (`mkdir` 0.13 / 写 0.21 / `remove` 0.16 / `rmdir` 0.14ms)⇒ 串行 **19.37~20.16s**(中位 ~19.6s),
  并行 `-n 4` **5.00 / 5.06s**(波动消失)⇒ 相较最初的 75s 量级共 **3.8×**(并行 15×)。
  ⚠ 这 3.8× 全部来自**环境**, 不是代码优化; 并行条目已从"不建议"翻转为"建议 `-n 4`" ——
  见 [pitfalls/testing/parallel-run.md](../pitfalls/testing/parallel-run.md)。
  另: 原候选"C 把 basetemp 钉进 TMPDIR 以省掉会话起始清理"实测**被推翻**(只把删除从收尾挪到起始 ——
  `_pytest/tmpdir.py` 对显式给定且已存在的 basetemp 会先 `rm_rf`, RUN H setup 段 19.85s), **未实施**。

- ↑ 收集数不变(**1192**; 2026-09-23 **tasks 索引渲染口径改造**): 未增删用例, 只消红 ——
  `gen_tasks_index.SUMMARY_MAX = 80`(摘要截断成一行) 让 `tasks/_index.md` **12,299 → 5,710**,
  那条既有红 `test_kb_files_respect_caps` 随之消失, 全量 **1191 passed + 1 skipped** / 139.07s / TOTAL 91%。
  为什么不按"轮转老档案"化解(实测数据): 可动档案仅 16 个 `Completed`(另 16 个 In Progress 是活的),
  其中 **15 个有外部引用** —— 搬走会让 `check_doc_links.py` 变红; 且 33 条平均 350 字符/行, 全搬也只够一次。
  病根是「索引把 `Summary` 全文打进一行」, 见 [pitfalls/kb/cap-counting.md](../pitfalls/kb/cap-counting.md) 第三节。

- ↑ 1190 → 1191(**+1**; 2026-09-23 **activeContext 切片化**(plan 26-09-22-2350 v1.1):
  新增守阵 `test_kb_active_context_slices_are_valid`(切片命名定宽前缀 / 三行头 / 每个 ≤6,000 / 总数 ≤40),
  并把 `test_kb_active_context_within_cap` 改判**存根合法性**(旧 12 KB「易变层硬顶」在切片化后失去对象)、
  `test_active_context_has_no_rolled_up_session_log` **语义重定义**(切片本身就是流水账, 原判据 `^- 2026-`
  在切片化后恒绿 = 等于没守; 改为只管 `activeContext.md` 本体 + 断言切片目录存在)。
  ⚠ 该轮全量实测 1189 passed + 1 skipped + 1 failed —— 那条 failed 是**既有红**
  (`test_kb_files_respect_caps`: `tasks/_index.md` 超 index-auto cap, 与本轮改动无关);
  **同日晚已由索引渲染截断解决, 见上一条**。TOTAL 91%, 143.77s。Linux 侧未重测。

- ↑ 1186 → 1188(**+2**; 2026-09-22 **web.py→web/ 包拆分 · issue 26-09-21-1408**(plan 26-09-22-1857):
  新增守阵 `test_web_route_manifest_frozen`(60 条 (method,path) 金清单集合比对; ❗本仓 FastAPI 的
  `include_router` 走 `_IncludedRouter` 懒解析, 清点须下钻 `original_router.routes` —— 首版因此假红)
  + `test_create_app_is_thin_assembly`(create_app ≤150 行且无内联 `@app.*`, 红=拆分前 926 行双红)。
  既有用例零改动(1 处管线性: open_path patch 目标 → `auto_qb.web.common.open_path`); 冒烟双 UI
  ok/error 两模式 70 项 0 失败。全量 1188 passed + 1 skipped, sidefx 越界 0)。

- ↑ 1188 → 1190 collected(**净 +2 用例**; 2026-09-22 **两案合流(2d4720b) + web 拆分合入**两次 merge 先后入库:
  config 取值范围收紧(issue 26-09-22-1937, 本侧 +1 守阵)
  × 状态周期落盘 + 热重载修复(对侧), core.py 冲突块手工合流(双方意图全保留); 
  合并树实测 deselect throttle 全量 1188 passed + 1 skipped + 1 deselected(throttle 文件级/全量跑因
  sleep 精度容差偶发假红, 已入池 26-09-22-2052); TOTAL 91% 7600 语句)
- ↑ 1176 → 1177(**+1**; 2026-09-22 **config 取值范围收紧实施**(issue 26-09-22-1937, 合流前单树实测):
  新增 `test_validate_value_ranges`(聚合验证 interval/main_tick/sync_interval 上下界、max_tasks_per_tick 上界、
  log.max_bytes 轮转区间、required_share_ratio 拦 nan/inf/负数、hr.condition 百分比与下载量边界、
  notify 上界、规则 interval 正时间); test_parse_hr_condition 补 4 条边界断言。
  助手层: 新增 `_try_number`(isfinite 拦 nan/inf)、`_try_time` 增 min_s/max_s、`_try` 返回解析值。
  全量 1177 passed + 1 skipped, sidefx 越界 0。首次全量曾现 test_run_loop_throttles_without_stop_event
  假失败(时序抖动: 单跑与复跑均绿, 与本次改动无关))
- ↑ 1185 → 1186(**+1**; 2026-09-22 issue 26-09-21-1347 **热重载 L2 state 回滚修复**:
  新增守阵 `test_apply_new_config_l2_preserves_runtime_state`(L2 热重载不得重读磁盘 state
  回滚运行期内存态; 修前红验必红 —— 实测 mgr.state 被换成磁盘旧版 `{'stale_marker': True}` →
  1 failed; 删 qbmanager.py:503 一行后转绿)。合流前单树实测: 语句 7542→7541(删 1 条已覆盖语句),
  miss ±1 的逐次抖动判为 server 线程路径的度量噪声; 覆盖率口径以本次实测为准。
  全量 1186 passed + 1 skipped, sidefx 越界 0)。
- ↑ 1176 → 1185(**+9**; 2026-09-22 **状态周期落盘 · issue 26-09-21-1347**:
  新键 `state_save_interval`(默认 120s / 配置端下限 30s 防误配置写放大 / 0=关闭) +
  主循环周期落盘钩子 + `skip_check_day`/`recheck_fails` 写点即时落盘。守阵 9 条:
  周期触发/关闭逃生口/脏退出验收阵与 interval=0 对照/跳检标记即时落盘/冷却计数即时落盘/
  配置校验/L0 分级/主循环接线。红验: 运行期把 `_maybe_flush_state` 与 `save_state` 打回 no-op,
  3 条行为守阵全红(KeyError/FileNotFoundError = 状态从未上盘); 还原全绿。
  全量 1185 passed + 1 skipped, sidefx 越界 0)。
- ↑ 1175 → 1176(**+1**; 2026-09-22 同任务 **W8 收尾 · 重写 `memory-bank.instructions.md`**:
  新增 `test_memory_bank_instructions_match_current_structure`。
  为什么值得单独钉: 该文件 `applyTo: memory-bank/**`, **只在编辑 memory-bank 时注入** ——
  不重写的话, 目录化重构后的新结构在改库那一刻**根本不在上下文里**, 于是又会按旧的 8 文件结构去写。
  旧版(12,073 字符)还在教「read ALL memory bank files at the start of every task」——
  那正是本库涨到 50 万字符、「必读」退化成「不读」的直接原因。重写后 **4,830 字符**,
  改为「先索引、后 grep、禁止整读」+ 当前目录树 + 三行头 + cap 分级表 + 档案五必备章节(标注按行首标题比)。
  另把 `.github/` 纳入 `check_doc_links.py` 的扫描面(规则载体也有链接, 之前扫不到)。
  全量 1176 passed + 1 skipped, sidefx 越界 0)。
- ↑ 1174 → 1175(**+1**; 2026-09-22 同任务 **W8 机检化 + 回归演练**:
  新增 `test_doc_links_are_not_broken`(全库相对链接存在性, 检查器 `scripts/check_doc_links.py`,
  **进程内 import**)。⚠ 它首跑就抓出 **73 处坏链**, 全是目录化搬家导致的**相对深度错位**
  (文件进了子目录、链接还按原深度写) —— 这正是"改名/搬家后的坏链不会让任何测试失败"那条坑,
  记了很久、一直只靠人工扫, 本波把它变成判据。修完 **192 个文件 0 处坏链**。
  全量 1175 passed + 1 skipped, sidefx 越界 0)。
- ↑ 1173 → 1174(**+1**; 2026-09-22 同任务 **W7 `tasks/` 档案消肿** —— 与远端合流后实测):
  ⚠ 本波提交时远端已领先 6 个提交(另一个 clone 的 tracker URL 脱敏 + 两次基线更新), 推送被拒(non-fast-forward)。
  **按纪律没跑 rebase**(本 shell 里必炸), 走 `format-patch` → `reset --hard` → `apply --3way` 重放;
  唯一冲突是 `baseline.md`(远端 1173 vs 本地 1171), 取远端为底, **在最终树上重跑全量**得 1174。
  ⇒ 教训: **跨 clone 的基线数字必须以"最终树实测"为准**, 两边各自的 +N 不能直接相加(远端那 1173 已含它自己的 +2)。
- ↑ 1170 → 1171(**+1**; 2026-09-22 同任务 **W7 `tasks/` 档案消肿**(本 clone 侧):
  新增 `test_kb_task_archives_within_cap` —— 本波把 `task` 角色纳入 `check_kb_structure` 默认角色集
  ⇒ **`check_caps` 的全部角色至此都被默认检查**(W1 故意留在门外的 `volatile` 在 W4 纳入, `task` 在本波纳入),
  这是「守卫按波次激活」这条设计的收口。
  实测: 最大档案 26,871 → **21,881 字符**(cap 24,000); 另把 `26-09-15-webui-qb-replacement.md` 的
  9,413 字符纪要段(超 8,000 子上限)外迁。全量 1171 passed + 1 skipped, sidefx 越界 0)。
 + `config-reference/` + `rule-system/` 目录化**:
  只动文档, 未增删用例。三文件(15,283 / 11,779 / 15,964 字符)→ **4 + 2 + 3 个主题文件 + 存根**;
  `checking` 高风险动作按计划**单独成篇**并与 [../pitfalls/backend/high-risk-ops.md](../pitfalls/backend/high-risk-ops.md) 互指。
  全量 1170 passed + 1 skipped, sidefx 越界 0)。
 + `modules/` 目录化**:
  只动文档, 未增删用例。`systemPatterns.md`(31,678 字符)→ **8 个主题文件**, `modules.md`(30,324 字符)→ **7 个**,
  两处源文件各留 ≤1 KB 存根。⚠ 顺带**纠正一处归属错误**: 原先「WEB UI 线程模型 / 前端渲染与响应性 /
  图形化配置编辑」三节(合计约 21 KB)挂在「任务队列」名下, 它们属于 **WEB UI 运行时**, 不属于队列。
  全量 1170 passed + 1 skipped, sidefx 越界 0)。
 + `progress/` 拆分**:
  `test_kb_active_context_within_cap` 是 W1 就写好但**按波次未启用**的那条 —— 本波把 `activeContext.md`
  压到 12 KB 硬顶之下(实测 **4,783** 字符), 才把它纳入 `check_kb_structure` 的默认角色集(`volatile`)。
  ⇒ **守阵按波次"激活"**是这套重构的一条设计: 检查器先写全, 目录/内容没到位时空转通过, 一落地就生效。
  全量 1170 passed + 1 skipped, sidefx 越界 0)。
: 只动文档与 skill 脚本, 未增删用例 ——
  `testing.md`(6,706 字符 / 489 行)拆成 **9 个主题文件 + 存根**; **基线数字的单点从 `testing.md` 顶部
  迁到 [baseline.md](baseline.md)**, 变更流水原样外迁到本文件; `techContext.md` 的浏览器自动化两条轨道
  迁入 [browser-env.md](browser-env.md)(techContext 6,706 → 3,542 字符)。全量 1169 passed + 1 skipped, sidefx 越界 0)。
: 只动文档与 skill 脚本, 未增删用例 ——
  但 9 条知识库守卫从「目录未建时空转」变成**真跑**(索引 == 生成结果 / 索引↔目录双向一致 / 三行头元数据 /
  cap 策略 / 类名与文件名 / 无孤儿索引 / 存根合法 / pitfalls 条目三字段 / 4 脚本可 import)。
  全量 1169 passed + 1 skipped, sidefx 越界 0)。
