# 3016 —— hr/ 运行时与取数线程变异守阵(runtime / worker / fetcher / events / adapters / log)基线

> 摘要: 认领 `issues/26-10-10-1108-test-hr-mutation-runtime-worker.html`(hr 首轮变异审计里 runtime 133 + worker 126 + fetcher 39 + events 41 + adapters 44 + log 3 的存活, 另含 runtime 12 / adapters 2 条 `no tests`)。**六个文件一次做全**: 逐条读带 diff 的存活清单三分类 → 补 **96 新守阵**(含**新建 `tests/test_hr_events.py`**)→ 红验按文件逐条同构变异复验 → S6 同池逐文件复跑。红验 **366/400 KILLED**(余 34 条逐条判等价 + 1 条假存活)。S6 对 R14 **逐文件存活对差 386 → 34**(净 **−352**)。**零 `src/` 改动**; **issue 置 `Done`**(六文件全覆盖)。
> 档案: memory-bank/tasks/26-10-08-test-mutation-audit.md
> 基线时间: 2026-10-10 19:40

**Refs:** memory-bank/tasks/26-10-08-test-mutation-audit.md, memory-bank/issues/26-10-10-1108-test-hr-mutation-runtime-worker.html

## 变异面实测(S6 复跑, 逐文件)

- **目标(glob)**: 逐文件 `**/hr/log.py` · `events.py` · `fetcher.py` · `adapters/__init__.py` · `adapters/base.py` · `adapters/carpt.py` · `adapters/nexusphp.py` · `runtime.py` · `worker.py`(R14 是整包 `**/hr/*.py`; 本轮按文件收窄 —— 见下「为什么可比」)
- **选择池**: R14 的 15 文件(`test_hr_service` / `parse` / `runtime` / `resolve` / `server` / `worker` / `store` / `report` / `status` / `channel` / `fetcher_channel` / `bencode` / `queue` / `ratelimit` / `multisite`)+ **`tests/test_hr_events.py`(本轮新建)**。
  - **池变更如实记**: `events.py` / `log.py` 此前**没有任何池内专属文件**(只有间接消费方), 整片文案/分层分支必然落进 `survived` —— 按 skill 硬约束 9(「目标包公开函数没有对应池内用例就先补进池」)新建该文件并**一并算作池**。对其余 4 个文件(自然池文件本就在 R14 池内)新增文件不可能杀它们的变异, 故对差仍直接可比; 对 events/log 的对差则**含池变更**(正是本轮要补的守阵)。
- **工具 / 参数**: mutmut **3.8.0** · `forkserver` · `-n 0 --no-cov` · `--max-children 3` · WSL2 `Ubuntu-26.04`(8 核) · **专用镜像** `~/auto-qb-mut-hr`(`--mirror`)+ **`--no-refresh`**(新守阵先 `cp` 进镜像 —— 硬约束 11)

| 目标 | 变异总数 | 杀 | 存活 | `no tests` | 超时 | 杀死率 |
|---|---|---|---|---|---|---|
| R14(整包) runtime 面 | (整包 8,027) | — | **133** | **12** | **2** | — |
| R14(同上) worker 面 | (整包 8,027) | — | **126** | 0 | 0 | — |
| R14(同上) fetcher 面 | (整包 8,027) | — | **39** | 0 | 0 | — |
| R14(同上) events 面 | (整包 8,027) | — | **41** | 0 | 0 | — |
| R14(同上) adapters 面 | (整包 8,027) | — | **44**(nexusphp 21 / base 17 / carpt 5 / `__init__` 1) | **2**(`__init__`) | 0 | — |
| R14(同上) log 面 | (整包 8,027) | — | **3** | 0 | 0 | — |
| **本轮 log.py** | **10** | **9** | **1** | **0** | **0** | **90.00%** |
| **本轮 events.py** | **71** | **67** | **4** | **0** | **0** | **94.37%** |
| **本轮 fetcher.py** | **156** | **153** | **3** | **0** | **0** | **98.08%** |
| **本轮 adapters/`__init__.py`** | **10** | **10** | **0** | **0** | **0** | **100%** |
| **本轮 adapters/base.py** | **25** | **25** | **0** | **0** | **0** | **100%** |
| **本轮 adapters/carpt.py** | **15** | **15** | **0** | **0** | **0** | **100%** |
| **本轮 adapters/nexusphp.py** | **194** | **193** | **1** | **0** | **0** | **99.48%** |
| **本轮 runtime.py** | **333** | **317** | **14** | **0** | **2** | **95.20%** |
| **本轮 worker.py** | **375** | **364** | **11** | **0** | **0** | **97.07%** |

- **逐文件对差(R14 → 本轮)**: log 3→1 · events 41→4 · fetcher 39→3 · adapters 44→1 · runtime 133+12`no tests`+2超时 → 14+2超时 · worker 126→11; 六文件合计 **386 → 34**(净 **−352**)。
- **为什么目标收窄仍可比**: mutmut 的变异**逐文件**生成, 单条「是否被池杀死」只取决于该变异 + 池。R14 各文件存活数来自整包目标的同一份池; 本轮把 `only_mutate` 收到单文件不改变该文件的变异体集合与池行为 ⇒ 存活集合可直接对差(收益: 墙时从整包 ≈96 min 降到单文件 1–20 min)。
- 结果清单落 `R:/Temp/auto-qb/mutants/` 的 `*-hr-<file>-py-results.txt`(runtime 16 行 = 14 存活 + 2 超时 · worker 11 行 · 其余 0–4 行)。

## S3 三分类 + 本轮守阵面

| 文件 | 存活(R14) | 新杀 | 存活(本轮) | 等价 | 守阵面 |
|---|---|---|---|---|---|
| `runtime.py` | 133(+12 `no tests`) | 119 | 14(+2 超时) | 14 | 启动/重挂/关停三分支的精确文案与「端点不重绑」· `_web_active` 现读与异常保守 · `judge` 的 anchor+now 原样转交 · `sleeper` 两处 raise 与 0s 下界 · `_build` 实参接线(目录/owner/persist/端点 identity/force_fn/worker endpoint/poll/回调)· `status` 各字段 · `_anchors`/`_site_origins` 逐条跳过 · `request_refresh` 受理与回执 |
| `worker.py` | 126 | 116 | 11 | 10 | `stable_key`/`pacing_class` 空与未命中 · `view_signature` 健康时刻取整 · `__init__` 各初始位 · `start` 文案+线程属性 · `stop` 叫停原因/句柄/精确文案/缺省超时 · `wake`/`request_refresh` 序号与累加 · `_loop` 忙等与 exc_info 堆栈 · `run_once` 锚点三态 · `_build_views` 快照优先 · `_note` 三档文案+两条边界(60s 下界、恰好到点)· `_check_channel_silence` 基准/标签/门限/小时数/事件层 |
| `fetcher.py` | 39 | 36 | 3 | 4 | 空通道缺省 reason 与两类报错串 · 真通道缺省 180s · 任务缺省 scope+tid · 下发带站点与 URL · 未监听/超时/登录页/空内容四条报错串 · 下发后叫停 · `build_channel_fetcher` 未启用 reason · `_scope_of`/`_tid_of` 只切第一个 `?`&`=` |
| `events.py` | 41 | 37 | 4 | 4 | `prefix` 已知/未登记两路 · 九条事件文案的标签前缀+动作引导+尾注(XX 包裹类须钉首尾)· `channel_silent` 三证据分支+站点拼接+note 尾 |
| `adapters/` | 44(+2 `no tests`) | 43 | 1 | 1 | 注册表名录 · 工厂透传站点名 · 构造默认(page_param/site/`_root` 无 scheme/未知档位回落字母)· 三条降级路径保 scope · 缺失率逐行累计 · 残行缺列不越界+行档位取 scope · `_is_blank` 下标边界 · 两站登录判据单标记各自成立 · 挑战页五特征词逐个 |
| `log.py` | 3 | 2 | 1 | 1 | `emit` 的层/档位挂载(默认可见 + 已知事件层 + 未登记空层) |

- **等价变异(34 条, 逐条记理由, 不追)**:
  - **默认值与字段/形参默认同值**(6): runtime `_build` 删 `persist=True` · 删 `poll_interval=POLL_INTERVAL` · `status` 删 `listening=False`; worker `_note` 的 `_pacing_at.get(site, X)` ×3 与 `_last_warn_at.get(site, X)` ×3 —— 该键**恒与 `_pacing_key` 同生**(同一分支成对写入)⇒ 缺省永不取用。
  - **不可达分支**(4): runtime `start` 的 `if self.service or True`(`_build` 必先建 service)· `start` 的 `mode else "XXXX"`(同上)· `apply` 的 `if worker is None or endpoint is None`(endpoint 只在 fetch_enabled 时存在, 那时 worker 必在)· `_site_origins` 的 `scheme` 三元 else(无 `://` 时 `host_of` 恒空 ⇒ 已 `continue`)。
  - **被后续赋值覆写**(1): runtime `apply` 的 `self.worker = ""`(`_build` 紧接着重赋真对象)。
  - **排障展示/单分隔符下各 split 变体同值**(7): `_site_origins` 的 `split("://", …)`/`rsplit` 四个变体(现实 URL 只有一个 `://`)· `sleeper` 的 `remain < 0` 与 `<= 0`(两次 `monotonic()` 之间恒有正耗时, 相等是测度零事件)。
  - **纯文案/证据串只在单一分支消费**(6): worker `_check_channel_silence` 的 `last_contact_ts` 缺省 `None` · `rejected_contacts` 缺省 `None` · `evidence` 缺省 `"XXnoneXX"` / `"NONE"` ×2(`channel_silent` 的 else 分支对三者等价)· events `channel_silent` 的 `evidence` 缺省 ×2(同源)。
  - **阈值/派生值恰不可分 / 死字段**(8): events `counter_mismatch` 的 `streak` 缺省 `0→1`(`>1` 阈值下 0 与 1 同尾注)· `retention_violation` 的 `*101`(`int(0.7*101)==int(0.7*100)==70`)· log `emit` 的 `event` 缺省 `""→"XXXX"`(都未登记 ⇒ 同为空层)· fetcher `getattr(..., "request_timeout", None/无/181.0)` ×3(`HrChannelConfig` 恒有该字段)· `ChannelFetcher.__init__` 的 `self._now = None`(死字段)。

## 补测(S5)与红验

- **新增守阵 96**: runtime 24 · worker 32 · fetcher 13 · parse 12 · **新建 `tests/test_hr_events.py` 15**(events 14 + log 1); 各文件头部「## 测试计划」同步。
- **红验 366/400 KILLED**(脚本 `tmp-analysis/r18_redverify.py` —— dump 驱动同构变异逐条 apply → 定向守阵 → 原字节回写还原; 命中数 `!= 1` 报 `ANCHOR-MISS` 停手): log 2/3 · events 37/41 · fetcher 35/39 · adapters 45/46 · runtime 131/145 · worker 116/126; 余 34 条逐条判等价(见上)。
  - **S6 与红验差 1 条 = 假存活**: worker `stop__mutmut_1`(`timeout=10.0 → 11.0`)**手工复验为 KILLED**(池内 `test_stop_default_timeout_is_ten_seconds` 必红)—— 疑与坑 `mutants-mirror-dirty-worktree` 同源(同长度替换让 stat/缓存比对失效); 以红验为准。
  - **判据污染防护(本轮现踩)**: ①开工先 `git checkout -- src/`(残留变异体让锚点整体失配 —— 实测 `parse_page m44` 报 ANCHOR-MISS); ②变异体会写**仓外产物**(runtime `data_dir=None` 变体在仓根造 `None/hr/*.json`), 开工一并清; ③**红验跑着时别手工改同一文件**(手工 `git checkout` 会还原正在跑的变异体, 实测把 worker `start m10`/`request_refresh m11` 伪判 SURVIVED)。
  - **坑 `redverify-anchor-lineendings` 复发 +1(形态六)**: dump 的 hunk **带上下文行**, 且**去缩进对 docstring 续行不生效**(同 hunk 内代码行 −4 / docstring 行 −0)⇒ 不能拿「首行缩进差」当统一位移(首版整块替换把上下文行也吃掉, 6 条 APPLY-ERROR)。处置 = 只用 `-` 行定位与取缩进; 歧义时用整块定位但只替换 `-` 区间。
  - **红验暴露的真缺口(已当场补上)**: ①`apply` 重挂端点 INFO 被 service 的「重挂端点」节流文案**顶替**(松匹配假绿); ②`sleeper` **第二处** raise(等待循环内)无人钉; ③`_note` 的**节流分支**边界与**告警分支**是两条独立变异, 只钉了一条; ④`_loop` 的 `exc_info=False` 让 `record.exc_info` 变 `False`(非 None), `is not None` 拦不住 ⇒ 改 `isinstance(..., tuple)`。

## test.full 实测

- 命令: `commands run test.full`(Windows, 单次采样 —— 耗时/波动口径见 [../baseline.md](../baseline.md)「必须带区间」)
- **实测**: **3054 passed + 4 skipped / 0 failed / 覆盖率 TOTAL 99%**(16568 语句 / 156 未覆盖 / 5716 分支 / 141 partial)
- 相对 R17 切片 [26-10-10-1458](../baselines/26-10-10-1458-mutants-hr-serialization.md): passed **+96**(= 本轮新增守阵 96); 未覆盖 165 → 156 · partial 142 → 141。`src/` **零改动**。
