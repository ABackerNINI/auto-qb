# 3235 —— hr/ 本地通道与端点变异守阵(channel / server)基线

> 摘要: 认领 `issues/26-10-10-1108-test-hr-mutation-channel-server.html`(hr 首轮里 channel 126 + server 210 存活)。**两文件一次做全**: 复跑基线(同池 `--no-refresh`, 未改测试)现值 **channel 121 + server 200** 条存活 → 逐条读带 diff 的存活清单三分类 → 补 **23 新守阵** → 红验按文件逐条同构变异复验 → S6 同池逐文件复跑。红验 **195/321 KILLED**(余 126 条逐 id 判等价)。S6 对复跑基线 **两文件存活 321 → 125**(净 **−196**)。**零 `src/` 改动**; **issue 置 `Done`**(两文件全覆盖)。
> 档案: memory-bank/tasks/26-10-08-test-mutation-audit.md
> 基线时间: 2026-10-15 09:27

**Refs:** memory-bank/tasks/26-10-08-test-mutation-audit.md, memory-bank/issues/26-10-10-1108-test-hr-mutation-channel-server.html

## 变异面实测(S6 复跑, 逐文件)

- **目标(glob)**: 逐文件 `**/hr/channel.py` · `**/hr/server.py`(R14 是整包 `**/hr/*.py`; 本轮按文件收窄 —— 见下「为什么可比」)
- **选择池(逐个文件, 跨轮必须一致)**: R14 的 15 文件(`test_hr_service` / `parse` / `runtime` / `resolve` / `server` / `worker` / `store` / `report` / `status` / `channel` / `fetcher_channel` / `bencode` / `queue` / `ratelimit` / `multisite`)—— 本轮**无池变更**(两个目标文件各自的专属池文件本就在 R14 池内)
- **工具 / 参数**: mutmut **3.8.0** · `forkserver` · `-n 0 --no-cov` · `--max-children 4` · WSL2 `Ubuntu-26.04`(8 核) · **专用镜像** `~/auto-qb-mut-hr`(`--mirror`)+ **`--no-refresh`**(新守阵先 `cp` 进镜像 —— 硬约束 11)
- **复跑基线**(2026-10-15 06:01 / 06:18, 同池 `--no-refresh`, 测试未改): channel **121** + server **200**(199 存活 + 1 超时)—— R14 的 126/210 里宽池已-被杀 5/10 条(编号/归类漂移同), 复跑现值取基线

| 目标 | 复跑基线存活 | 本轮变异 | 杀 | 存活 | 超时 | 杀死率 |
|---|---|---|---|---|---|---|
| **本轮 `channel.py`** | 121 | **540** | **483** | **57** | **0** | **89.44%** |
| **本轮 `server.py`** | 200(199 + 1 超时) | **550** | **482** | **67** | **1** | **87.64%** |
| **两文件合计** | **321** | **1090** | **965** | **124** | **1** | **88.53%** |

- **逐文件对差(复跑基线 → 本轮)**: channel **121 → 57**(新杀 **64**)· server **200 → 68**(新杀 **132**, 超时 1 不变); 两文件合计 **321 → 125**(净 **−196**)。
- **为什么目标收窄仍可比**: mutmut 的变异**逐文件**生成, 单条「是否被池杀死」只取决于该变异 + 池。复跑基线各文件存活数来自整包目标的同一份池; 本轮把 `only_mutate` 收到单文件不改变该文件的变异体集合与池行为 ⇒ 存活集合可直接对差(收益: 墙时从整包 ≈96 min 降到单文件 1–2 min)。
- 结果清单落 `R:/Temp/auto-qb/mutants/` 的 `*-hr-<file>-py-results.txt`(复跑基线 0601/0618 · S6 0853/0911: channel 57 行 · server 68 行 = 67 存活 + 1 超时)。
- **channel 红验 vs S6 差一条(如实记)**: 红验 63 杀 vs S6 新杀 64 —— 差一条 `x_resolve_token__mutmut_10`: 红验同构复判**等价**(SURVIVED), S6 现被池守阵**杀**(疑同构复原与 mutmut 真变异体在该 id 上差, 或池守阵非定向面杀它); **以 S6 为准记存活 57**。server 两口径**逐位吻合**(132 / 132)。
- **按目标跑里 `.meta` 只末目标存**(本轮实证): channel 的 `.meta` 被 server 跑冲掉 ⇒ 判据取 diff 清单 / 复生成, 不靠 `.meta`。

## S3 三分类 + 本轮守阵面

| 文件 | 存活(复跑基线) | 新杀 | 存活(本轮) | 等价 | 守阵面 |
|---|---|---|---|---|---|
| `channel.py` | 121 | 64 | 57 | 57 | `_absolute_download` 的 URL 解析边界(scheme/host/path 三段 split · 相对与绝对路径 · 白名单拒文案逐字)· `host_of`/`path_of`/`_scheme_of` 的缺-scheme/缺-`/` 空串契约 · `resolve_token` 的 `what` 文案与 token 形态 · `HrResult.from_json`/`to_json` 与 `HrTask.to_json` 的逐键往返 + 错误契约(`decode_json` 的异常与 `parse_results` 逐键)· `UrlPolicy.require` 白名单与 `site_of` 未登记空串契约 |
| `server.py` | 200 | 132 | 68(67 + 1 超时) | 67 | `route` 的 401/403 体与头逐键 · refresh/result/sites 全契约(参数/状态码/头逐键)· 节流边界与文案 · 线头 `Server`/`Content-Type`/`Content-Length` 逐字 · `_json` 的紧凑分隔(`", "`/`": "`)与 CJK 不转原原(`ensure_ascii`)· `_content_length` 的 UTF-8 字节长度 |

- **等价变异(126 条, 逐 id 判, 不追)**:
  - **单分隔符 split/rsplit/maxsplit 变同值**(channel/server 主导): `split("/", 1)`→`split("/")`/`rsplit`/`split("/", 2)` —— 该段里分隔符**恰单 occurrence** ⇒ 同值(与 R19 ratelimit 同口径)。
  - **文案/注释/docstring 变体**: 错误串与人话文案的 `XX..XX` 包裹 / 大小改 —— 判据(返回非空 / 异常类型)不变。
  - **`encoding` 大小写变同**: `"utf-8"`→`"UTF-8"`/`"Utf8"` —— 解码/编码同效。
  - **死默认与恒-真分支恒等**: 形参默认未被消费 / `if True` 类恒真下变同。
- **超时 1 条**(server, `_json` 类): 红验按「未绿 = 被杀」30s 超时口径记 KILLED; S6 记 timeout —— 两口径一致该条**非存活**。

## 补测(S5)与红验

- **新增守阵 23**: `tests/test_hr_channel.py` 11 · `tests/test_hr_server.py` 12; 两文件头部「## 测试计划」同步(server 补 R21 段条目)。**全绿**(test.quick 收面含两文件)。
- **红验 195/321 KILLED**(脚本 `tmp-analysis/r20_redverify.py` —— dump 驱动同构变异逐条 apply → 定向守阵变红 → 原字节还原; 自检 apply 后 `ast.parse` + revert 字节恒等): channel **63/121**(61 自动 + 2 条 `ANCHOR-MISS(2)` 的 `""→"XXXX"` 双命中, 手工同构复验两位各 KILLED)· server **132/200**; 余 **126** 条逐 id 判等价(与 S3 逐 id 一致: 61+77+1 减 13 条现被既有/新守阵杀)。
  - **坑 [redverify-anchor-lineendings](../../pitfalls/testing/redverify-anchor-lineendings.md) 复发 +1(新增形态九)**: 重排 `add` 行缩进**复原按 `min` 位移** —— 同 hunk 内 docstring 续行位移(−0)与代码行(−4)时, 按 min 把代码行**少缩进** ⇒ `IndentationError` ⇒ 首版红验 180/321 与 S6 不符, 虚低被**伪判 SURVIVED**(与形态七的伪判 KILLED 方向相反)。处置: 位移取 **`max`** + apply 后 `ast.parse` 自检记 `APPLY-ERROR`; 改按 max 后红验 195/321 与 S6 逐文件吻合(channel 差一条见上, 以 S6 为准)。

## test.full 实测

- 命令: `commands run test.full`(Windows, 单次采样 —— 耗时/波动口径见 [../baseline.md](../baseline.md)「必须带区间」)
- **实测**: **3235 passed + 4 skipped / 0 failed / 覆盖率 TOTAL 99%**(16828 语句 / 157 未覆盖 / 5712 分支 / 140 partial, 总 **98.66%**)
- `src/` **零改动**(纯补测 + 文档)。
