# 9217 —— hr/ 展示导出面变异守阵(status / report)基线

> 摘要: 认领 `issues/26-10-10-1108-test-hr-mutation-display.html`(hr 首轮变异审计里 status 285 + report 276 = 561 条存活; 其中 report 的 21 条已被 R16–R19 轮守阵旁及杀, 本轮起点 540)。**两文件一次做全**: 逐条读带 diff 的存活清单三分类 → 补 **54 新守阵** → 红验按文件逐条同构变异复验 → S6 同池逐文件复跑。红验 **481/540 KILLED**(余 59 条逐条判等价, **0 ANCHOR-MISS**)。S6 对 R14 **逐文件存活对差 540 → 59**(净 **−481**)。**零 `src/` 改动**; **issue 置 `Done`**(两文件全覆盖)。
> 档案: memory-bank/tasks/26-10-08-test-mutation-audit.md
> 基线时间: 2026-10-15 08:46

**Refs:** memory-bank/tasks/26-10-08-test-mutation-audit.md, memory-bank/issues/26-10-10-1108-test-hr-mutation-display.html, memory-bank/pitfalls/testing/redverify-pycache-stale-verdict.md, memory-bank/pitfalls/testing/redverify-anchor-lineendings.md

## 变异面实测(S6 复跑, 逐文件)

- **目标(glob)**: 逐文件 `**/hr/status.py` · `report.py`(R14 是整包 `**/hr/*.py`; 本轮按文件收窄 —— 可比性见 R19 切片同节)
- **选择池(逐个文件, 跨轮必须一致)**: R14 的 15 文件(`test_hr_service` / `parse` / `runtime` / `resolve` / `server` / `worker` / `store` / `report` / `status` / `channel` / `fetcher_channel` / `bencode` / `queue` / `ratelimit` / `multisite`)—— 本轮**无池变更**(两个目标文件的专属池文件本就在 R14 池内)
- **工具 / 参数**: mutmut **3.8.0** · `forkserver` · `-n 0 --no-cov` · `--max-children 4` · WSL2 `Ubuntu-26.04`(8 核) · **专用镜像** `~/auto-qb-mut-hr-display`(`--mirror`)+ **`--no-refresh`**(新守阵先 `cp` 进镜像 —— 硬约束 11)

| 目标 | R14 存活 | 本轮起点 | 本轮变异 | 杀 | 存活 | 超时 | 杀死率 |
|---|---|---|---|---|---|---|---|
| **`status.py`** | 285 | 285 | **733** | **715** | **18** | **0** | **97.54%** |
| **`report.py`** | 276 | 255 | **691** | **650** | **41** | **0** | **94.07%** |
| **两文件合计** | **561** | **540** | **1424** | **1365** | **59** | **0** | **95.86%** |

- **逐文件对差(R14 → 本轮)**: status **285 → 18**(新杀 **267**)· report **255 → 41**(新杀 **214**; R14 的 276 中 21 条在本轮开始前已被 R16–R19 守阵旁及杀, 故起点 255); 两文件合计 **540 → 59**(净 **−481**)。
- **为什么目标收窄仍可比**: 见 R19 切片同节(mutmut 变异逐文件生成, 单条「是否被池杀死」只取决于该变异 + 池)。
- 结果清单落 `R:/Temp/auto-qb/mutants/` 的 `26-10-15-0837-hr-status-py-results.txt`(18 行)· `26-10-15-0839-hr-report-py-results.txt`(41 行); 无超时无 no-tests。

## S3 三分类 + 本轮守阵面

| 文件 | 存活(R14) | 新杀 | 存活(本轮) | 等价 | 守阵面 |
|---|---|---|---|---|---|
| `status.py` | 285 | 267 | 18 | 18 | `LaneStatus` 全字段透传 + text 组合逐字(页/行/全深度/声明/对不上/明细/连续失效)· 缺档位 `continue` 而非 `break` · 未知 status 回落原文 · `duration_text` 四档(1d2h/3h4m/5m6s/7s)逐字 · `ago_text` 的「前」后缀与「从未」· `stamp_text` 零值落「-」与格式 `%m-%d %H:%M:%S` · `need_seed_text` 天/时零填充与缺字段「-」· `lane_counts` 每档都计 · `_retention_text` ratio<0 不适用与达标/WARN 两态 · `entry_details` 排序(档位·负下载量; None 按 0)与字段面(含失踪行)· 未知 lane 回落原文 · `_history_lanes` 跳过非 dict 但保后续 + 缺键兜空串 · `history_rows` 稳定 tiebreak 与回落 · `site_status` 富快照全字段(quota.text 逐字/pending 的 and 口径/observing `>0` 且仅 A 档/keys/allow_window/blocking 不拦)· `_site_conf_interval` 两类波值(stub 对象缺属性与 0 值)· `blocking_reason` 全分支逐字 · `SiteStatus.to_dict` 42 键面 · `build_site_statuses` 显式站点序与 read_error 透出 |
| `report.py` | 276(起点 255) | 214 | 41 | 41 | `_print_status_rows` 空数据提示行逐字/排序公式/limit `>` 口径/表头数据行硬编码逐字(tid 右对齐·名称左对齐·行尾 infohash)/`_status_row_cells`(hash 取 12 位·v1 优先·双空落「-」·未知档位回落·量值缺省 0·ratio 三位)· `_dwidth` F/W 双宽 · `_pad` 方向与默认 · `_ellipsis` 边界 · `_print_channel` 逐行(端点/轮询/等回传/密钥来源/扩展 origin 两分支/共享目录两分支)· `_print_site` 逐行(action/reason 回落正常/锁自检/各档计数/视图行)· **`_print_status_site` 逐行**(此前零守阵: 头部四要素/文件+WARN/取波/各档+逐档明细/备注/守恒/零行三态/数据两行/频控)· 档位计数缺键回落 0 · 冻结态 · `run_hr_once` force 越复用窗·html_dir 透传·多站点 join·无通道提示逐字·视图行(双 hash 索引)· 各档回落「-」· `run_hr_status` 通道段落 buf·多站点 join·坏文件 WARN·收尾两行逐字·无 WARN 行 · `run_hr_confirm_empty` 备注累加/空 notes/提示两行逐字/enabled=false 提示·写盘心跳非 None·事件 kind/trigger/action · `LocalPageFetcher` 坏字节 replace |

- **等价变异(59 条, 逐条记理由, 不追)**:
  - **`locale`/编码等价**(report 3 条): `read_text(encoding="utf-8")` → `encoding=None`/删 encoding/`"UTF-8"` —— WSL `C.UTF-8` locale 下 `None` 即 utf-8, `"UTF-8"` 大小写不敏感; 且三变体都**保留 `errors="replace"`** ⇒ 坏字节仍替换不抛。
  - **falsy 同义 / 构造默认**(report ~14 条): `persist=False→None` · `allow_fetch=False→None` · `owner=...→None` · `sleeper=time.sleep→None`/删实参 · `sleep_max=X→None`/删实参 · `round_wait_max=0.0→None`/`1.0`/删实参 —— 三条入口的这几个形参在对应路径上**未被消费**(status/confirm 不取数; once 的假通道无等待路径), 或构造默认与传入值同为 `time.sleep`/同 falsy; `**extra` 删除在无 extra 调用时等价。
  - **`what` 参数**(report 4 条): `_gate_enabled_sites(..., what="走查"/"查看")` → `None`/`"XX..XX"` —— `what` 只进**门不通过**时的提示文案; 测试场景门通过 ⇒ 不可观测。
  - **`fetcher` 实参**(report ~8 条): `NullFetcher("...")` → `None`/`NullFetcher(None)`/改文案 —— status/confirm 不取数, fetcher 不被调用; `_reason` 只在异常消息里。
  - **`str.strip` 字符集等价**(report 4 条): `.strip("; ")` → `.strip(None)`(等价于 `.strip()`, 而 notes 首尾非空白/分号) · `.strip("XX; XX")`(字符集含原 `;` 与空格, 多出的 `X` 在数据首尾不存在) —— 测试数据下逐位相同。
  - **`_append_history` 的 site**(report 1 条): `site` → `None`/缺省 `"XXXX"` —— site 只用于 `store(site)` 的文件名/日志前缀与 `by` 字段(取 `owner`, 与 site 无关) ⇒ 事件内容不变。
  - **`CHANNEL_TEXTS.get(None, ...)`**(report 1 条): 表无 `None` 键 ⇒ 返回 default 即原 `view.channel_state` ⇒ 与原式同。
  - **档位计数键名/默认值**(report 6 条): `lanes.get('C'/'XXCXX'/'c', 0)` —— `lane_counts` 里 `'C'` 缺席 ⇒ 原式也是默认 0; 键名改形后的 get 同样落默认 ⇒ 逐位相同。`lanes.get(None, 0)` 同理。
  - **时刻域边界**(status 2 条): `ago_text` 的 `ts<=0→<0`(ts=0 已被 `not ts` 先捕) · `stamp_text` 的 `ts>0→>=0`(ts=0 已被 `ts and` 先捕) —— **0 值**在两步判据下不可区分。
  - **不可达回落分支**(status 6 条): `_lane_statuses` 的 `LANE_TEXTS.get(lane, lane)` → `None`/省略默认 —— 该函数遍历 `FETCH_LANES` 常量, `lane` 恒 A/B/C ⇒ **未知档位分支不可达**; 可达的同形落在 `_history_lanes`(由 `test_history_lanes_defaults_and_fallbacks` 守)。**探针勿放不可达分支**(坑档 `assertions.md` 同类)。
  - **形参未被消费**(status 4 条): `_lane_statuses(data, now)` 的 `now`(函数体不用) · `blocking_reason(..., site, ...)` 的 `site`(不参与判定) ⇒ 传 `None`/改默认值不可观测。
  - **`getattr` 缺省 falsy**(status 3 条): `getattr(wave, "idle_mode", False→None)` 及 `getattr(conf, "...interval", 0.0→None)` —— `None` 与 `False`/`0.0` 在 `if getattr(...)`/`... or 0.0` 下同效。
  - **`ver` 的 falsy 与 `if h` 短路**(status 2 条): `ver = None→""` 后续只用 `if ver` · `data.verified.get(h) if (h) or True` —— h 为空时 `get("")` 返回 `None`(表中无空键) ⇒ 同。
  - **默认值 / `**extra` 类**(status 1 + report 1 条): `history_rows(now: 0.0→1.0)`(测试恒显式传 now) · `_build_service` 的 `**extra` 删除(无 extra 调用)。

## 补测(S5)与红验

- **新增守阵 54**: `tests/test_hr_status.py` 31 · `tests/test_hr_report.py` 23; 两文件头部「## 测试计划」同步。另修 4 处既有探针缺陷(数据让变异体输出同值/缺场景/sub 串断言过松/假值默认与真实值巧合)与 1 处自证死循环(用被测 `_pad`/`_dwidth` 重建期望行 ⇒ 改硬编码)。
- **红验 481/540 KILLED**(脚本 `tmp-analysis/r20_redverify.py` —— dump 驱动同构变异逐条 apply → 定向池 → 原字节回写还原; 一级锚点 = 删除行 strip 序列在 **ast 函数体范围**内唯一命中, 二级 = 带上下文序列): status **267/285** · report **214/255**; 余 **59** 条逐条判等价(见上), **0 ANCHOR-MISS / 0 APPLY-ERROR / 0 TIMEOUT**。
  - **与 S6 逐 id 一致**: 两文件的存活 id 集合与 S6 结果文件**逐条吻合**(status 18 = 18 · report 41 = 41), 新杀数也逐位吻合(267 / 214)。
  - **坑 `redverify-anchor-lineendings` 复发 +1(新增形态八: 锚点命中数 > 1 的两级定位)**: 首版只用「删除行序列」定位, 27 条报 `ANCHOR-MISS(2)` —— 同一行文本(如 `file=out`、`print("-" * 92, file=out)`)在**同一函数体内出现多次**。处置 = 二级锚点: 用「上下文行 + 删除行」的 strip 序列(跳过 `+` 行)再定位一次, 命中唯一后按 `-` 行在序列中的偏移取替换区间; 上下文与 `-` 皆不唯一才报 ANCHOR-MISS。**「命中数 != 1 停手」的兜底仍生效**(27 条先报 `ANCHOR-MISS(2)` 而非静默取首个)。
  - **新坑 [redverify-pycache-stale-verdict](../../pitfalls/testing/redverify-pycache-stale-verdict.md)**: 红验首版**假 SURVIVED** —— `.pyc` 缓存判据 `(mtime, size)` 在**等长替换**(`get(None, view.channel_state)` ↔ `get(view.channel_state, None)`, 同长)+ **秒级 mtime 碰撞**(0.5s/条)下两条相同 ⇒ 子进程 import **复用上一条变异体的字节码**, 跑的不是当前文件 ⇒ 假存活且**稳定复现**(前两次全量给出逐条一致的 149/106 假数)。修 = 子进程加 `-B` + `PYTHONDONTWRITEBYTECODE=1` **并**开工清 `__pycache__`(只设环境变量不够: 旧 `.pyc` 仍被读)。与 `mutants-mirror-dirty-worktree`(git stat 缓存)同族。

## test.full 实测

- 命令: `commands run test.full`(Windows, 单次采样 —— 耗时/波动口径见 [../baseline.md](../baseline.md)「必须带区间」)
- **实测**: **3277 passed + 4 skipped / 0 failed / 覆盖率 TOTAL 99%**(16866 语句 / 158 未覆盖 / 5714 分支 / 142 partial)
- `src/` **零改动**(纯补测 + 文档)。
