# 2877 —— config loaders 键缺省走字段默认守阵(issue 26-10-08-0903-loader-defaults)基线

> 摘要: 认领并修复 `issues/26-10-08-0903-test-config-mutation-loader-defaults.html` —— 首轮 config 变异审计入池的 6 条 `test` issue 之一(`_get(spec, KEY, d.<field>)` 默认值换 None / 关键字实参被删, 全套件杀不掉)。形态复验: 手搓 **40 条**同构变异(脚本 `tmp-analysis/mut_ld.py`, 字节级读写保 CRLF)在补测前 **26 SURVIVED / 11 KILLED**(余 3 条锚点首版写错, 修正后并入), issue 前提成立。补 **7 个守阵**(`tests/test_config.py` 5 + `tests/test_hr_config.py` 2); 红验 **40/40 KILLED**。S6 同目标同池 `--no-refresh` 复跑: 存活 **533 → 476(净 −57, 新增存活 0)**, 杀死率 **88.14% → 89.33%**, **57 条新杀全部落在 `config/loaders`**。**零 `src/` 改动**(纯补测 + 文档)。
> 档案: memory-bank/tasks/26-10-08-test-mutation-audit.md
> 基线时间: 2026-10-10 09:25

**Refs:** memory-bank/tasks/26-10-08-test-mutation-audit.md

## 变异面实测(S6 复跑, 同目标同池)

- **目标(glob)**: `**/config/*.py`(与首轮 / R6 / R8 / R10 完全一致)
- **选择池(逐文件, 与首轮一致 —— 换池数字不可比)**: `tests/test_config.py` · `tests/test_config_writer.py` · `tests/test_hr_config.py` · `tests/test_config_schema.py` · `tests/test_impact.py` · `tests/test_config_key_surface.py`
- **工具 / 参数**: mutmut **3.8.0** · `--max-children 4` · 机器 = WSL2 `Ubuntu-26.04`(8 核, `.wslconfig` 限)
- **复跑带 `--no-refresh`**(硬约束 11), 且**先 `cp` 新 `tests/test_config.py` + `tests/test_hr_config.py` 进镜像**(否则被 `git checkout -f` 冲掉)

| 轮次 | 变异总数 | 杀 | 存活 | `no tests` | 杀死率 |
|---|---|---|---|---|---|
| R10 基线(26-10-09-1610, loop-guards) | 4799 | 4230 | 533 | 36 | 88.14% |
| **本轮(26-10-10-0921, loader-defaults)** | **4799** | **4287** | **476** | **36** | **89.33%** |

- **逐 id 对差**: 本轮新杀 **57** · 新增存活 **0**; **57 条全部在 `config/loaders`**(与本轮守阵面逐模块一致, 无旁支归因争议)。
- 结果清单: `R:/Temp/auto-qb/mutants/26-10-10-0921-config-py-results.txt`(512 行 = 476 存活 + 36 `no tests`)。

## S4 形态复验(手搓同构变异, 不是 mutmut id)

issue 只给了**变异形态**(默认值换 None / 删关键字实参)与函数名, 没给 id 清单, 故本轮用手搓锚点做复验与红验(字节级替换, 保 CRLF; 删行按 `strip()` 精确匹配单行):

| 形态 | 条数 | 复验(补测前) |
|---|---|---|
| `load_tracker_config` 的 `tags/remove_tags/upload_speed_limit/download_speed_limit/rules/groups/remove_similar_tags` | 7 | 4 SURVIVED / 3 KILLED |
| `load_tracker_hr` 的 `out()` / `out_bool()` 回退链末段 | 2 | 1 SURVIVED / 1 KILLED(bool 分支会当场抛「无效布尔值」, 被既有用例撞见) |
| `_resolve_hr_site_bindings` 删 `download_path=/page_param=/listing=/adapter=/hr_page_url=/required_seeding_time=` 实参 | 6 | 3 SURVIVED / 3 KILLED |
| `load_global_speed_limit_curve` 的 `interval=None` / `enabled=True` | 2 | 1 SURVIVED / 1 KILLED |
| `load_config` 顶层标量(`sync_interval`/`state_save_interval`/`max_tasks_per_tick`/`maintenance_tag_mode`/`remove_similar_tags`) | 5 | 4 SURVIVED / 1 KILLED |
| 段级 loader(`hr`/`hr_check`/`channel`/`sites` 条目/`log`/`qbittorrent`/`grouping`/`web`/`notify`) | 18 | 13 SURVIVED / 5 KILLED |

- **合计 26 条 SURVIVED** —— 「池内用例都显式给了该键, 没覆盖『键缺省 → 走 dataclass 字段默认』这条路径」的判定成立。
- **为什么不直接用 `mutants.verify`**: 它按 mutmut id 逐条跑全套件(≈15s/条), 而本轮要验的是**形态**; 手搓脚本 40 条 × ≈3s = 2.6min 即完成复验 + 红验两轮。代价是这些变异**不等于** mutmut 的编号(故上表的「新杀 57」与这里的 40 条不逐 id 对应)。

## 补测(S5)与红验

新增 **7** 个测试函数:

| 守阵 | 文件 | 钉住的默认值来源 |
|---|---|---|
| `test_loader_defaults_tracker_config_keys_absent` | test_config | `load_tracker_config`: 站点段只给 `domains` → `tags/remove_tags/限速/rules/groups/remove_similar_tags` 全走 `TrackerConfig` 字段默认 |
| `test_loader_defaults_tracker_hr_output_chain` | test_config | `load_tracker_hr`: 站点段 + 全局段都没写输出键 → 回退链末段 `getattr(d, key)`(而非 None) |
| `test_loader_defaults_config_top_level_scalars` | test_config | `load_config`: `sync_interval`/`state_save_interval`/`max_tasks_per_tick`/`maintenance_tag_mode`/`remove_similar_tags` 全缺省 |
| `test_loader_defaults_sections_when_absent` | test_config | 各段整段缺省走 `_get(cfg, "<段>", {})` 空字典分支 → 段内键逐个取该段字段默认(qbittorrent / log / grouping / web / notify / hr / fs / delete_tags) |
| `test_loader_defaults_gslc_optional_keys` | test_config | `load_global_speed_limit_curve`: `interval` 缺省 **None**(回退主 interval)/ `enabled` 缺省 True / 省略方向的曲线 **None** |
| `test_channel_partial_section_uses_channel_defaults` | test_hr_config | `load_hr_check_config` 的 channel 子段给了字典但缺键 → 缺的键走 `HrChannelConfig` 字段默认(token 与 port 各缺一次, 双向对照) |
| `test_site_binding_takes_preset_page_facts` | test_hr_config | `_resolve_hr_site_bindings` 的页面事实键取**档案值**; 用 monkeypatch 挂三项都非默认的合成档案(现网两个内置档案的 `download_path/page_param/listing` 恰与字段默认同值, 删了看不出差别) |

- **红验 40/40 KILLED**: 同脚本逐条 apply → 跑池内两文件 → 原字节回写还原(主仓 `src/` 零残留)。首版 `chan.token` 仍存活(用例只给了 `token` 显式值, 撞不到缺省分支)→ 补「只给 port, token 缺省」的反面对照后转 KILLED。
- **关键设计**: 段级 loader 有两条路 —— 「非字典 → 早退返回 `d` 实例」(旧用例多覆盖这条) 与「字典在但键缺 → `_get` 走字段默认」(本轮补的这条); 整段缺省走的是**后者**。

## test.full 实测

- 分支: `develop`(工作树含本轮补测 + 文档时实测; 开工已同步远端 15 笔)
- 命令: `commands run test.full`(Windows, 单次采样 —— 耗时/波动口径见 [../baseline.md](../baseline.md)「必须带区间」)
- **实测**: **2877 passed + 4 skipped / 0 failed / 覆盖率 TOTAL 99%**(16567 语句 / 167 未覆盖 / 5716 分支 / 143 partial)
- 本轮新增用例 **7**(相对上基线 [26-10-09-1611](../baselines/26-10-09-1611-mutants-config-loop-guards.md) 净 +9, 余 2 来自开工同步进来的远端提交, 非本轮); 未覆盖 / 分支 / partial 与上基线逐位持平。
- `src/` **零改动**。Linux(WSL 沙箱)侧未重测 —— 本轮只加平台无关的断言用例, 未改平台相关代码(口径见 baseline.md 常驻警告; 与上两轮切片同处理)。
