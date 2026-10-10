# 3103 —— hr/ 判定内核与边界变异守阵(resolve / bencode / ratelimit / parse)基线

> 摘要: 认领 `issues/26-10-10-1108-test-hr-mutation-judgment-core.html`(hr 首轮变异审计里 resolve 126 + bencode 89 + ratelimit 38 + parse 39 = 292 条存活)。**四文件一次做全**: 逐条读带 diff 的存活清单三分类 → 补 **47 新守阵** → 红验按文件逐条同构变异复验 → S6 同池逐文件复跑。红验 **170/292 KILLED**(余 118 条逐条判等价 + 4 条超时)。S6 对 R14 **逐文件存活对差 292 → 122**(净 **−170**)。**零 `src/` 改动**; **issue 置 `Done`**(四文件全覆盖)。
> 档案: memory-bank/tasks/26-10-08-test-mutation-audit.md
> 基线时间: 2026-10-10 20:44

**Refs:** memory-bank/tasks/26-10-08-test-mutation-audit.md, memory-bank/issues/26-10-10-1108-test-hr-mutation-judgment-core.html

## 变异面实测(S6 复跑, 逐文件)

- **目标(glob)**: 逐文件 `**/hr/resolve.py` · `bencode.py` · `ratelimit.py` · `parse.py`(R14 是整包 `**/hr/*.py`; 本轮按文件收窄 —— 见下「为什么可比」)
- **选择池(逐个文件, 跨轮必须一致)**: R14 的 15 文件(`test_hr_service` / `parse` / `runtime` / `resolve` / `server` / `worker` / `store` / `report` / `status` / `channel` / `fetcher_channel` / `bencode` / `queue` / `ratelimit` / `multisite`)—— 本轮**无池变更**(四个目标文件各自的专属池文件本就在 R14 池内)
- **工具 / 参数**: mutmut **3.8.0** · `forkserver` · `-n 0 --no-cov` · `--max-children 4` · WSL2 `Ubuntu-26.04`(8 核) · **专用镜像** `~/auto-qb-mut-hr`(`--mirror`)+ **`--no-refresh`**(新守阵先 `cp` 进镜像 —— 硬约束 11)

| 目标 | R14 存活 | 本轮变异 | 杀 | 存活 | 超时 | 杀死率 |
|---|---|---|---|---|---|---|
| **本轮 `resolve.py`** | 126 | **353** | **330** | **23** | **0** | **93.48%** |
| **本轮 `bencode.py`** | 89(85 + 4 超时) | **310** | **237** | **69** | **4** | **76.45%** |
| **本轮 `ratelimit.py`** | 38 | **142** | **131** | **11** | **0** | **92.25%** |
| **本轮 `parse.py`** | 39 | **326** | **311** | **15** | **0** | **95.40%** |
| **四文件合计** | **292** | **1131** | **1009** | **118** | **4** | **89.21%** |

- **逐文件对差(R14 → 本轮)**: resolve **126 → 23**(新杀 **103**)· bencode **89 → 73**(新杀 **16**)· ratelimit **38 → 11**(新杀 **27**)· parse **39 → 15**(新杀 **24**); 四文件合计 **292 → 122**(净 **−170**)。
- **为什么目标收窄仍可比**: mutmut 的变异**逐文件**生成, 单条「是否被池杀死」只取决于该变异 + 池。R14 各文件存活数来自整包目标的同一份池; 本轮把 `only_mutate` 收到单文件不改变该文件的变异体集合与池行为 ⇒ 存活集合可直接对差(收益: 墙时从整包 ≈96 min 降到单文件 1–2 min)。
- 结果清单落 `R:/Temp/auto-qb/mutants/` 的 `*-hr-<file>-py-results.txt`(resolve 23 行 · bencode 73 行 = 69 存活 + 4 超时 · ratelimit 11 行 · parse 15 行)。
- **bencode 存活偏高说明**: 剩余 73 条**全部**是「错误文案 / MAX_DEPTH 深度计数 / 漏 pos 实参」类 —— 见下等价变异表; 该文件语义面(infohash 原始切片)的真洞本轮已全清, 其余是文案与深链边界(与 R17/R18 对文案类的一贯口径一致, 不追)。

## S3 三分类 + 本轮守阵面

| 文件 | 存活(R14) | 新杀 | 存活(本轮) | 等价 | 守阵面 |
|---|---|---|---|---|---|
| `resolve.py` | 126 | 103 | 23 | 23 | 四行判定表三档(A/B/C/D)人话逐字 · 行 3 放行来源文案三档(D/B/缺席)· 行 4 默认文案与 `notes` 覆盖(or 而非 and)· infohash 缺位与透传字段(reason/site)· `HrSiteFacts.of` 四字段搬运 · 锚点 `completion_on>=0` 边界(0 值快照)· 平局合并(管束取小 remain / C 终态保先到不被更强放行依据顶掉 / 同强 B 保先到 / D>B)· `safety_display` 全分支 text 逐字 · `build_site_view` 六字段落视图 + 未知档位 `continue` 而非 `break` |
| `bencode.py` | 89 | 16 | 73(69 + 4 超时) | 69 | `_read_int` 负单数字与 0 · 空格/两位前导零拒 · `_read_bytes` 零长字节串 · 字典解码返回位置(闭合 e 之后)· 位置 > 0 的嵌套字典 · 深嵌套字典 MAX_DEPTH · `_skip` 嵌套列表位置 · `torrent_display_name` 非法 UTF-8 按 replace |
| `ratelimit.py` | 38 | 27 | 11 | 11 | `HrLimits.merge` 三字段(allow_window 不丢)· `day_key` 精确 `%Y-%m-%d` 格式 · `next_day_reset` 精确次日零点(含秒/微秒归零)· `window_start_on` 取起点端 + 顺延 + 精确归零 + 恰等 now 顺延 · `next_allowed_at` 多门槛取最晚者与对应原因 · 候选全 `<= now` 时原因为空串 · due 恰等 now 视为已满足 |
| `parse.py` | 39 | 24 | 15 | 15 | `parse_size` 千分位逗号剥除 · `parse_duration` 大写 D / `0天`→None / 段内非数字→None · `_TableTree` 多文本段累加 + `<th>` 认作单元格 · `extract_table` 空行不越界 · `has_next_page` 大小写不敏感 · `order_violations` 证据不足/全相等分支带 comparable/total + 方向由首对推断 + 相邻相等不算违反 · `cross_page_violation` asc 边界相等不算违反 |

- **等价变异(118 条, 逐条记理由, 不追)**:
  - **错误/异常文案变体**(bencode 主导, ~55 条): `raise ValueError(f"...")` → `ValueError(None)` / 消息串被 `XX..XX` 包裹 / 大小写改 / `text[:16]`→`text[:17]` —— 池内守阵一律 `pytest.raises(ValueError)` 不带 `match`, 异常类型与语义不变 ⇒ 等价(与 R17/R18 对文案类的一贯口径一致)。
  - **MAX_DEPTH 深度计数 / 边界**(bencode ~12 条): `_depth=0→1` · `>MAX_DEPTH→>=` · 递归 `_depth+1→+2/-1/缺省` —— 只在**恰好**深度 64/65 处可观测, 池内深链用例(200 层)一律仍拒 ⇒ 等价。
  - **find 起点 / `>= len` 边界**(bencode ~9 条): `_read_int` 的 `pos+1→pos-1/+2`(`e` 不可能出现在整数 token 内)· `if end<0→<=0/<1` · `pos>=len→pos>len`(越界仍抛)⇒ 等价。
  - **`start` 初值**(parse 3 条): `extract_table` 的 `start=-1/+1/-2` —— 命中表头时恒被循环覆写, 未命中时提前 return ⇒ 初值不可观测。
  - **`text or ""` 占位串**(parse 3 条): `parse_size`/`parse_ratio`/`parse_datetime` 的 `text or "XXXX"` —— 空串走占位串仍无匹配 ⇒ 等价。
  - **`while len(nums)<3` / 切片变体**(parse 3 条): 段数恒 ≤3, `<3`→`<=3`/`<4`/`[-3:]`→`[-4:]` 产出逐位相同。
  - **`handle_endtag` 的 `tr`/`th` 大小写**(parse 2 条): `tag == "TR"` / `"XXtrXX"` —— HTMLParser 恒把标签名小写化 ⇒ 分支永不触发, 与 `"tr"` 同效。
  - **`has_next_page` 默认 page_file 大小写**(parse 1 条): 判据带 `re.IGNORECASE` ⇒ `"MYHR.PHP"` 与 `"myhr.php"` 同效。
  - **`order_violations` 的 `direction=None` / `first_at` 边界**(parse 3 条): `""→None` 恒被覆写或只作 `if not direction` 判据 · `first_at<0→<=0/<1` 在 `i+1>=1` 下逐位相同。
  - **`next_allowed_at` 门槛边界**(ratelimit 6 条): `and→or` / `>0→>=0/>1` / `>=0` / `retry_after_until>now→>=now` —— 在 `last_fetch_ts=0`(候选值远小于 now)或等值时产出相同。
  - **`window_start_on` 单分隔符 split 变体**(ratelimit 3 条): `split("-",1)`→`split("-")`/`rsplit`/`split("-",2)` —— spec 只有一个 `-` ⇒ 同值。
  - **缺省实参 / 死值**(resolve 8 条): `now: 0.0→1.0`(该形参在 `resolve_identity`/`judge_record` 内**未被消费**, 只原样转发)· `best_entry=""`(恒被后续赋值覆写)· `_RANK.get(id,0/None/1)` 与 `_RELEASE_SRC_STRENGTH` 缺省(所有身份/来源都在表内 ⇒ 缺省不可达)· `_tie_prefer` 的 `and→or`(rank 相等 ⇒ 同身份, and/or 同效)· `<→<=`(等值 facts 相同)· NO_EVIDENCE 平局 `return False→True`(无差异)。
  - **文案变体**(resolve 8 条): `drift_reason` 四条人话的 `XX..XX` 包裹 / 大小写 —— 纯展示, 判据(返回非空)不变。

## 补测(S5)与红验

- **新增守阵 47**: `tests/test_hr_resolve.py` 19 · `tests/test_hr_bencode.py` 8 · `tests/test_hr_parse.py` 13 · `tests/test_hr_ratelimit.py` 7; 各文件头部「## 测试计划」同步。
- **红验 170/292 KILLED**(脚本 `tmp-analysis/r19_redverify.py` —— dump 驱动同构变异逐条 apply → 定向守阵 → 原字节回写还原): resolve **103/126** · bencode **16/89** · ratelimit **27/38** · parse **24/39**; 余 **118** 条逐条判等价 + **4** 条超时(见上)。
  - **与 S6 逐文件一致**: 四个文件的新杀数**逐位吻合**(103 / 16 / 27 / 24)。
  - **一次采样抖动(如实记)**: ratelimit 的 S6 **首跑**采样为 130 杀 / 12 存活(91.55%), 复跑为 **131 / 11**(92.25%) —— 差的一条是 `next_allowed_at__mutmut_10`(把 `rng` 换成 `None` 走全局随机), 与池内该用例的随机抖动判据有关; 复跑与红验一致, **取 131 / 11**。
  - **坑 `redverify-anchor-lineendings` 复发 +1(新增形态七)**: 首版 applier 用「整段 hunk(上下文行 + 删除行)」定位后, 取**首行**缩进作 `add` 行缩进基准 —— 当 hunk 首行是 `def`/docstring(缩进 0)而被改行在函数体内(缩进 4)时, 重排出的 `add` 行**丢缩进** ⇒ `IndentationError` ⇒ pytest 收集失败被**伪判 KILLED**(实测 bencode `bdecode m3` 等 ~52 条虚高, 首版红验 242/292 与 S6 严重不符)。处置: 缩进基准改取**首个删除行**对应的源行, 并在 apply 后 `ast.parse` 自检(不通过记 `APPLY-ERROR` 而非跑测试)。**「命中数 != 1 停手」的兜底仍生效**(报 `ANCHOR-MISS` 而非假绿)。

## test.full 实测

- 命令: `commands run test.full`(Windows, 单次采样 —— 耗时/波动口径见 [../baseline.md](../baseline.md)「必须带区间」)
- **实测**: **3103 passed + 4 skipped / 0 failed / 覆盖率 TOTAL 99%**(16568 语句 / 156 未覆盖 / 5716 分支 / 141 partial)
- `src/` **零改动**(纯补测 + 文档)。
