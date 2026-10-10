# 2958 —— hr/model·store·queue 序列化与持久化变异守阵(issue 26-10-10-1108-serialization)基线

> 摘要: 认领 `issues/26-10-10-1108-test-hr-mutation-serialization.html`(hr 首轮变异审计里 **model 185 + store 45 + queue 41** 的存活, 首轮建议「`model.from_json` 145 条是最大单点; 次为 store 锁有效性 revision 比较与原子写回退」)。本轮**三个文件一次做全**: 逐条读带 diff 的存活清单三分类, 补 **41 个新守阵**(`test_hr_store.py` 24 + `test_hr_queue.py` 15 + `test_hr_status.py` 2)+ **1 处既有用例补断言**; 红验 **245 KILLED / 26 SURVIVED**(dump 驱动同构变异逐条 apply → 定向守阵变红 → 原字节还原, 主仓 `src/` 零残留), 26 条存活**逐条判为等价变异**(理由见下)。S6 复跑(目标逐文件 `**/hr/model.py` / `**/hr/store.py` / `**/hr/queue.py` · 池 = R14 同一份 15 文件 · `--no-refresh`): **model 844 变异 / 杀 843 / 存活 1(99.88%)** · **store 205 / 192 / 13(93.66%)** · **queue 140 / 126 / 12 / 超时 2(90.00%)**; 对 R14 的**逐文件存活对差 271 → 28(净 −243)**(model 185→1 · store 45→13 · queue 39+2超时→12+2超时)。**零 `src/` 改动**(纯补测 + 文档)。**issue 置 `Done`**(三个文件全部覆盖)。
> 档案: memory-bank/tasks/26-10-08-test-mutation-audit.md
> 基线时间: 2026-10-10 14:58

**Refs:** memory-bank/tasks/26-10-08-test-mutation-audit.md, memory-bank/issues/26-10-10-1108-test-hr-mutation-serialization.html

## 变异面实测(S6 复跑, 逐文件)

- **目标(glob)**: `**/hr/model.py` · `**/hr/store.py` · `**/hr/queue.py`(R14 是整包 `**/hr/*.py`; 本轮按文件收窄 —— 见下「为什么可比」)
- **选择池(逐文件, 与 R14 完全一致 —— 换池数字不可比)**: `tests/test_hr_service.py` · `tests/test_hr_parse.py` · `tests/test_hr_runtime.py` · `tests/test_hr_resolve.py` · `tests/test_hr_server.py` · `tests/test_hr_worker.py` · `tests/test_hr_store.py` · `tests/test_hr_report.py` · `tests/test_hr_status.py` · `tests/test_hr_channel.py` · `tests/test_hr_fetcher_channel.py` · `tests/test_hr_bencode.py` · `tests/test_hr_queue.py` · `tests/test_hr_ratelimit.py` · `tests/test_hr_multisite.py`
- **工具 / 参数**: mutmut **3.8.0** · `process_isolation=forkserver` · `-n 0 --no-cov` · `--max-children 3` · 机器 = WSL2 `Ubuntu-26.04`(8 核, `.wslconfig` 限)
- **专用镜像** `~/auto-qb-mut-hr`(`--mirror`) · 复跑带 **`--no-refresh`**(硬约束 11), 且**先 `cp` 三个改过的测试文件进镜像**

| 轮次 | 目标 | 变异总数 | 杀 | 存活 | `no tests` | 超时 | 杀死率 | 墙时 |
|---|---|---|---|---|---|---|---|---|
| R14(26-10-10-1108, 整包) model 面 | `**/hr/*.py` | (整包 8027) | — | **185** | — | — | — | — |
| R14(同上) store 面 | `**/hr/*.py` | (整包 8027) | — | **45** | — | — | — | — |
| R14(同上) queue 面 | `**/hr/*.py` | (整包 8027) | — | **39** | — | **2** | — | — |
| **本轮 model** | `**/hr/model.py` | **844** | **843** | **1** | **0** | **0** | **99.88%** | **5m16s**(3.23 变异/s) |
| **本轮 store** | `**/hr/store.py` | **205** | **192** | **13** | **0** | **0** | **93.66%** | **3m21s**(1.37 变异/s) |
| **本轮 queue** | `**/hr/queue.py` | **140** | **126** | **12** | **0** | **2** | **90.00%** | **3m50s**(0.78 变异/s) |

- **逐文件对差(R14 存活 vs 本轮)**: model **185 → 1**(净 −184)· store **45 → 13**(净 −32)· queue **39+2超时 → 12+2超时**(净 −27); 三文件合计 **271 → 28**(净 **−243**)。
- **为什么目标收窄仍可比**: mutmut 的变异**逐文件**生成, 单条变异体「是否被池杀死」只取决于该变异 + 池。R14 的各文件存活数来自整包目标的同一份 15 文件池; 本轮把 `only_mutate` 收到单文件不改变该文件的变异体集合与池行为 ⇒ 两者的存活集合可直接对差。收窄的收益是墙时从整包 ≈96 min 降到三文件合计 ≈12.5 min。
- 结果清单: `R:/Temp/auto-qb/mutants/26-10-10-1447-hr-model-py-results.txt`(1 行)· `26-10-10-1451-hr-store-py-results.txt`(13 行)· `26-10-10-1455-hr-queue-py-results.txt`(14 行)。
- **镜像工作树残留(本轮踩到并处置)**: 专用镜像 `~/auto-qb-mut-hr` 的 `src/auto_qb/hr/queue.py` 里残留着**上一轮被中断的 mutmut apply 变异体**(`left = deadline + time.monotonic()` = `wait__mutmut_19`), 而 `git status` / `git diff` / `git update-index --really-refresh` **全判净**(stat 缓存: 同长度替换) —— 不处置会让 `--no-refresh` 轮带着残留跑。处置: 跑前 `git checkout -f -- src/` 强制还原(验证别用 sha1 —— 镜像行尾与主仓不同, 用 `grep` 关键行); 已记入 [mutants-mirror-dirty-worktree](../../pitfalls/testing/mutants-mirror-dirty-worktree.md)。

## S3 三分类 + 本轮守阵面

| 文件 | 存活(R14) | 本轮新杀 | 存活(本轮) | 等价(不追) | 说明 |
|---|---|---|---|---|---|
| `model.py` | 185 | 184 | 1 | 1 | 全字段往返钉 `to_json`/`from_json` 键名与取值; 键缺省走字段默认; `_opt_int`/`_opt_float` 的 None 原样穿过; `infohash_of` 索引优先; `index_by_infohash` 的 `continue` 语义; `HrSiteData` 的 schema_version/writer 回退/放行入账闸 |
| `store.py` | 45 | 32 | 13 | 13 | 构造默认 / `_read_full` 与 `_parse` 的 recoverable 旗标 / 三条错误路径的取证串 / `_write` 默认留 `.bak` 与 `ensure_ascii`+`sort_keys` / 心跳自检严格下界 / 坏文件挪不走时保留好备份 |
| `queue.py` | 39(+2超时) | 27 | 12(+2超时) | 12 | 初始叫停原因 / put 默认值 / task_id 长度 / 单批上限 1 / 推代语义 / abort 两条清理 / 回传 URL 回落 / TTL 严格边界 / 小假时钟 / 代变放弃等待 / 零与亚秒超时 |

- **等价变异(26 条, 逐条记理由, 不追)**:
  - **日志/错误文案**(11 条): `logger.warning(None)` / `logger.debug(None)` / `logger.error(None)` / `_warn_unsafe(None)` / `_warn_unsafe("XX..XX")` / `_log_migration_once(None)` —— 文案只进日志, 无程序消费方(store `quarantine`·`_warn_read_error`·`_check_lock_effective`×3·`_warn_unsafe`·`_parse`; queue `submit`×2)。
  - **编码等价**(5 条): `read_text(encoding=None)` / `encoding="UTF-8"` —— 本机与 WSL 均 **UTF-8 模式**(`sys.flags.utf8_mode=1`), `None` 与大小写变体都解析成 utf-8(store `_read_full`×2 · `read_backup`×2; `_write` 的 `ensure_ascii=None` 同为假值)。
  - **`pop(k, )` 去掉默认值**(4 条): 该 key 在调用点**已保证存在**(循环项 / 前置 `in` 判定) ⇒ `pop(k)` 与 `pop(k, None)` 同行为(queue `wait`·`submit`·`_expire_locked`×2)。
  - **死字段 / 绝对值**(6 条): `HrTaskQueue._name` 全仓只赋值不读取(5 条); `__init__` 的 `self._epoch = 0 → 1`(只比较变化, 绝对值不可观测)。
  - **边界等价**(2 条): `prune_history` 的 `len(kept) > CAP → >=`(恰好 `== CAP` 时 `kept[-CAP:]` 是恒等切片); `wait` 的 `left <= 0 → < 0`(恰好 `left == 0` 时 `wait(0)` 立即返回, 下一轮即 `left < 0`, 结果同)。
  - **路径去空白**(1 条): `hr_dir` 的 `str(data_dir).rstrip("/\\") → rstrip(None)`(`rstrip(None)` 去空白; 路径不含尾部空白时与 `os.path.join` 归一后同值)。
- **超时 2 条**(queue `wait__mutmut_19` / `wait__mutmut_25`): 变异体使等待永不返回(mutmut 记 `timeout`, 非存活) —— 与 R14 同一对。

## 补测(S5)与红验

- **新增 41 个测试函数 + 1 处既有用例补断言**:
  - `tests/test_hr_store.py` **24** 个: model 全字段往返 12 个(`HrEntry` 全字段/可选全 None/键全缺 · `HrDownloaded`/`HrVerified`/`HrLaneState`/`HrWaveMeta`/`HrRateLedger` 往返+键缺省 · `HrHistoryEvent` 键缺省与 notes 里 None · `HrSiteData` 全字段往返/schema_version+writer 回退/放行入账闸)+ store 12 个(instance_id 长度 · hr_dir 尾部 · 构造默认 · recoverable 旗标 · 三条错误路径取证串 · `_file_hint` 三态 · `_write` 默认留备份 · unicode+sorted keys · read_alerted · 心跳 0 不下界 · 挪不走保留好备份)。
  - `tests/test_hr_queue.py` **15** 个(见「守阵面」行)。
  - `tests/test_hr_status.py` **2** 个: `infohash_of` 索引优先 · `index_by_infohash` 的 `continue` 跳过而非 `break` 停表。
  - **既有补断言 1 处**: `test_field_parse_failure_reported` 加 `"开头" in err`(取证串带文件开头)。
- **红验 245/271 KILLED**: 脚本 `tmp-analysis/r17_redverify.py` —— 从 R14 dump 取每条候选的**同构变异块**, 按「**函数体范围**(变异 id 的 qualname → `class`/`def` 定位)+ **strip 后内容唯一命中**」定位, 以「源码行缩进 − dump 行缩进」为位移把新增行还原到源码缩进后替换; 命中数 `!= 1` 报 `ANCHOR-MISS` 停手; 逐条 apply → 跑**定向守阵** → 原字节回写还原(主仓 `src/` 零残留)。自检: 271 条**全部** apply 后 `ast.parse` 通过且 revert 字节恒等。**超时类变异致守阵挂起时按「未绿 = 被杀」处理**(与 mutmut 的 `timeout` 同口径), 故脚本对子进程设 30s 超时。
- **踩到的已记坑**: [redverify-anchor-lineendings](../../pitfalls/testing/redverify-anchor-lineendings.md) **复发 +1** —— 本轮新增**形态五**: ①dump 的 hunk 行号是**函数相对**(不是文件相对) —— 首版按文件行号套变异 ⇒ 271 条全 `ANCHOR-MISS`; ②mutmut id 的 `ǁ` 分隔符**字形不可靠**(首版按字面 `ǁ` split 失败) ⇒ 改用「非标识符字符」判据解析 qualname; ③去缩进对 **docstring 续行不生效**(与形态四的「续行不归一」同源, 但触发源是 docstring 而非反斜杠续行)。**为什么没命中**: 坑里形态四写的是「反斜杠续行不归一」, 本轮是 docstring 续行 + 函数相对行号 + 分隔符字形三处新触发; 但「`count != 1` 停手」的兜底与「strip 后内容唯一命中」的处置**都按预期工作**。已把形态五补进坑档。

## test.full 实测

- 分支: `develop`(工作树含本轮补测 + 文档时实测; 开工已同步远端)
- 命令: `commands run test.full`(Windows, 单次采样 —— 耗时/波动口径见 [../baseline.md](../baseline.md)「必须带区间」)
- **实测**: **2958 passed + 4 skipped / 0 failed / 覆盖率 TOTAL 99%**(16568 语句 / 165 未覆盖 / 5716 分支 / 142 partial)
- 相对 R16 切片 [26-10-10-1408](../baselines/26-10-10-1408-mutants-hr-service.md): passed **+42**(≈ 本轮新增用例; 余数来自开工同步进来的远端提交, 非本轮)· 未覆盖 167 → 165 · partial 142 持平。
- `src/` **零改动**。Linux(WSL 沙箱)侧未重测 —— 本轮只加平台无关的断言用例, 未改平台相关代码(口径见 baseline.md 常驻警告)。
