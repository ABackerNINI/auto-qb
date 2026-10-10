# 2886 —— config 校验器闭区间端点逐值守阵(issue 26-10-08-0903-boundary-guards)基线

> 摘要: 认领并修复 `issues/26-10-08-0903-test-config-mutation-boundary-guards.html` —— 首轮 config 变异审计入池的 6 条 `test` issue 中**最后一条**(校验器闭区间端点位移类变异全套件杀不掉)。issue 只给变异形态 + grep 锚点、没给 id 清单, 故按 skill 硬约束 13 走**形态级手搓复验**: 脚本 `tmp-analysis/mut_bg.py`(bytes 层读写、锚点命中数 `!= 1` 直接 `ANCHOR-MISS` 停手、每条跑完原字节还原)对校验器里**每一处闭区间**造 **103 条**同构变异, 补测前 **83 KILLED / 20 SURVIVED**(issue 前提成立且已部分失效)。补 **5 个守阵**(`tests/test_config.py` 2 + `tests/test_hr_config.py` 3); 红验 **103/103 KILLED**。S6 同目标同池 `--no-refresh` 复跑: 存活 **476 → 443(净 −33, 新增存活 0)**, 杀死率 **89.33% → 90.02%**, **33 条新杀全部落在 `config/validation`**。**零 `src/` 改动**(纯补测 + 文档)。
> 档案: memory-bank/tasks/26-10-08-test-mutation-audit.md
> 基线时间: 2026-10-10 10:45

**Refs:** memory-bank/tasks/26-10-08-test-mutation-audit.md, memory-bank/issues/26-10-08-0903-test-config-mutation-boundary-guards.html

## 变异面实测(S6 复跑, 同目标同池)

- **目标(glob)**: `**/config/*.py`(与首轮 / R6 / R8 / R10 / R11 完全一致)
- **选择池(逐文件, 与首轮一致 —— 换池数字不可比)**: `tests/test_config.py` · `tests/test_config_writer.py` · `tests/test_hr_config.py` · `tests/test_config_schema.py` · `tests/test_impact.py` · `tests/test_config_key_surface.py`
- **工具 / 参数**: mutmut **3.8.0** · `--max-children 4` · 机器 = WSL2 `Ubuntu-26.04`(8 核, `.wslconfig` 限)
- **复跑带 `--no-refresh`**(硬约束 11), 且**先 `cp` 新 `tests/test_config.py` + `tests/test_hr_config.py` 进镜像**(否则被 `git checkout -f` 冲掉)

| 轮次 | 变异总数 | 杀 | 存活 | `no tests` | 杀死率 |
|---|---|---|---|---|---|
| R11 基线(26-10-10-0921, loader-defaults) | 4799 | 4287 | 476 | 36 | 89.33% |
| **本轮(26-10-10-1045, boundary-guards)** | **4799** | **4320** | **443** | **36** | **90.02%** |

- **逐 id 对差**: 本轮新杀 **33** · 新增存活 **0**; **33 条全部在 `config/validation`**(sections 31: `_validate_hr_check` 12 · `_validate_hr_site_entry` 12 · `_validate_qb_traffic` 7; core 2)—— 与本轮守阵面逐模块一致、无旁支归因争议。
- 结果清单: `R:/Temp/auto-qb/mutants/26-10-10-1045-config-py-results.txt`(479 行 = 443 存活 + 36 `no tests`)。

## S4 形态复验(手搓 103 条同构变异, 不是 mutmut id)

issue 只给了**变异形态**(`<=`→`<`、端点 ±1、`>`→`>=`、报错语句删除)与 grep 锚点, 没给 id 清单, 故本轮用手搓锚点做复验与红验(字节级替换, 保留 CRLF; 端口锚点逼到「行首 + 缩进」以免 12/20 空格两种缩进互相误命中):

| 闭区间面 | 条数 | 复验(补测前) |
|---|---|---|
| `sections` 三处 port(`qbittorrent.port` / `web.port` / 一处内层 port) —— 比较符翻转 + 端点 ±1 | 15 | 全 KILLED(已被 R2 `test_validate_exact_boundaries` 杀死) |
| `sections` `log.max_bytes` [1MiB, 1GiB] —— 逐字节两端 ±1B | 12 | 2 SURVIVED(逐字节侧) |
| `sections` `_validate_notify` 三键 —— 比较符翻转 / 端点 ±1 | 12 | 全 KILLED |
| `sections` `_validate_qb_traffic` 采样 / 落盘 / 两保留窗 | 16 | 2 SURVIVED(`raw_window` 上界) + 1 SURVIVED(`flush_interval` 整数秒拦截侧) |
| `sections` `_validate_hr_check` 频控四键(`min_interval` / 日额 / 页上限) —— 两端 | 14 | 12 SURVIVED |
| `sections` `_validate_hr_site_entry` `refresh_interval` / `idle_refresh_interval` [60s, 30D] | 8 | 3 SURVIVED(refresh 一侧完全没喂过越界值 + idle 松匹配被交叉校验顶替) |
| `sections` `_validate_hr_site_bindings` 分享率 | 4 | 全 KILLED |
| `curves` `_validate_curve_points` 阈值 `<= 0` / `<= prev` | 8 | 全 KILLED(R2 已覆盖曲线阈值) |
| `core` `validate_config` 顶层各区间(`max_tasks_per_tick` / `_try_time` 正性) | 14 | 全 KILLED |

- **合计 20 条 SURVIVED** —— 「两端没被**逐值**喂过」的判定成立: min_interval/日额/页上限/request_timeout 的**端点本身**(5S / 1D / 1 / 100000 / 3600S)与站点 refresh 的越界值从无用例; `log.max_bytes` 旧用例取 1023KiB / 1025MiB 这种「隔一档」值, 挡不住**逐字节**位移; `flush_interval` 的「须为整数秒」拦截分支(append 报错语句)从无输入撞到。
- **为什么不直接用 `mutants.verify`**: 它按 mutmut id 逐条跑全套件(≈15s/条), 而本轮要验的是**形态**; 手搓脚本 103 条 × ≈1.8s = ≈3.1min 即完成复验 + 红验两轮。代价是这些变异**不等于** mutmut 的编号(故上表的「新杀 33」与这里的 103 条不逐 id 对应; mutmut 也不生成 `1024**2 - 1` 这类形态)。

## 补测(S5)与红验

新增 **5** 个测试函数:

| 守阵 | 文件 | 钉住的闭区间端点 |
|---|---|---|
| `test_validate_exact_boundaries_size_and_window_tail` | test_config | `log.max_bytes` [1MiB,1GiB] **逐字节**两端(1MiB±1B / 1GiB±1B)· `raw_window` 上界两端(90D/91D)· `flush_interval` 须整数秒的**拦截侧**(此前只有通过侧) |
| `test_validate_schema_version_lower_endpoint` | test_config | `schema_version` 下界(1 合法 / 0 非法) |
| `test_hr_check_range_endpoints` | test_hr_config | `hr_check.min_interval` [5s,1D] 与 `max_requests_per_day`/`max_pages_per_wave` [1,100000] 的**两端**(上界端点 100000 此前没喂过) |
| `test_hr_check_request_timeout_endpoints` | test_hr_config | `channel.request_timeout` [5s,3600s] 两端(旧用例只给远离端点的 1S/2H) |
| `test_hr_site_interval_range_endpoints` | test_hr_config | `refresh_interval`/`idle_refresh_interval` [60s,30D] 的**未覆盖半边**(refresh 侧越界 + idle 下界精确文案) |

- **红验 103/103 KILLED**: 同脚本逐条 apply → 跑池内两文件 → 原字节回写还原(主仓 `src/` 零残留)。补测后 20 条原存活变异全部转红, 另 83 条保持红(**无回退**)。
- **关键发现(既有守阵是假绿)**: `test_idle_refresh_interval_range` 用 `"须 >=" in e` 这种**松匹配**断言 idle 的 59S, 而**交叉校验文案里也带「须 >= 拉取间隔(...)」** —— 交叉校验报错把断言顶替掉了, 范围判据本身从未被验证(实测 idle 下界 −1 的变异因此存活)。本轮新守阵改用「**完整路径 + 精确下限文案**」(`config.hr_check.sites.btschool.idle_refresh_interval: 须 >= 60s`)才钉住。

## test.full 实测

- 分支: `develop`(工作树含本轮补测 + 文档时实测; 开工已同步远端)
- 命令: `commands run test.full`(Windows, 单次采样 —— 耗时/波动口径见 [../baseline.md](../baseline.md)「必须带区间」)
- **实测**: **2886 passed + 4 skipped / 0 failed / 覆盖率 TOTAL 99%**(16568 语句 / 167 未覆盖 / 5716 分支 / 143 partial)
- 本轮新增用例 **5**(相对上基线 [26-10-10-1000](../baselines/26-10-10-1000-mutation-audit-skill-feedback.md) 净 +8, 余数来自开工同步进来的远端提交, 非本轮)。
- `src/` **零改动**。Linux(WSL 沙箱)侧未重测 —— 本轮只加平台无关的断言用例, 未改平台相关代码(口径见 baseline.md 常驻警告; 与上两轮切片同处理)。
