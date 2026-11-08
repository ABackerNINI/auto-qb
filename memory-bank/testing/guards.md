# 守阵清单

> 摘要: 全库**机械守阵**的汇总 —— 一条 = 守阵名 + 钉住的结论 + 怎么红验。新增守阵时登记到这里。
> 触发: 守阵, 静态守卫, 防回潮, 红验, 钉住, 加守卫, 守卫清单

> **守阵 = 把"靠人记的规则"变成"违反就红"的测试。** 必要性有两条反向实证: 已机检化的
> 「提交后核 ref 三处」与「脚本改名漏改的未定义名」此后**一次都没再犯**; 而只写在文档里、
> 靠人记的 `git rebase` 禁令在工具 shell 里出了**三次**事故。
> ⇒ **能变成红的, 从文本搬进守阵; 搬不动的, 必须在做那个动作的决策点可见。**
>
> **登记规则**: 新增守阵必须同时 ①在本表加一行 ②在被测文件头部 docstring 的「测试计划」清单加一行
> ③**做一次红验**(把被测修复临时还原 / 注入违例, 确认它真的变红)。

> **批次守阵外迁存档**: 主循环/WEB解耦 · 后端高风险动作 · S2-S6 四批次 · 仿真/语料/平台语义 · src 结构卫生 · 规则表达式内核 · 配置键面 · 提提交水线包 · 流量聚合封口 · 种子状态 A 系 —— 原文 → [attachments/guards-batches-archive.md](attachments/guards-batches-archive.md) (节标题同名, 检索按守阵名)。

## 知识库结构(`tests/test_memory_bank_*.py`, 检查器在 skill 的 `check_kb_structure.py`)

> 守卫清单与逐条结论由测试本身维护, 此处只留指针: 见 `tests/test_memory_bank_*.py`(四分)与 [file-conventions.md「`tests/test_memory_bank_*.py` 守知识库结构」](file-conventions.md); 逐条「钉住的结论 + 红验」表见 [attachments/guards-batches-archive.md](attachments/guards-batches-archive.md)「知识库结构守卫」; 检查器在 `.agents/skills/memory-bank/scripts/check_kb_structure.py`。

## 前端 / WEB UI

| 守阵 | 钉住的结论 | 红验 |
|---|---|---|
| `test_frontend_computed_not_invoked_as_function` | computed 不得当函数调用(`this.xxx()`); 注释行跳过 | 写 `this.unitParts()` |
| `test_frontend_member_window_functions_live_in_methods` | 成员行窗口的带参函数必须在 `methods:` 内 | 挪进 `computed:` |
| `test_frontend_static_bundle_health` | 静态资源健康 **11 项**: 冲突标记残留 / JS 注释孤儿续行 / `node --check` 真语法校验 / CSS 规则块漏闭合 / `<transition>` 吞弹窗 / 模板引用的静态资源存在 / `STATE_RANK` 与后端逐项一致 + `seeding` 严格先于 `paused` / 集成员取 hash 必含 `memberHashesOf(` / 筛选器走 `facetRows`+`_facetOptions` 单点 / 挂件类名在 CSS 有定义 | 注入各类违例(实测 5 种) |
| `test_frontend_dist_segments_aggregates_per_view` | 状态分布必须按 `viewMode` 分支取数 | 改回只数 `groups` |
| `test_frontend_cols_store_single_setitem_site` | 全仓**唯一** `setItem` 漏斗 | 加第二个 `setItem` |
| `test_frontend_persist_page_takes_intent_only` | 派生值(自适应 px)进不了持久化路径 | 把 `colWidths` 落盘 |
| `test_frontend_col_manual_flag_not_revived` | 已删的 `colManual` 标志不得复活 | 写回 `colManual` |
| `test_frontend_toast_duration_floor_by_kind` | toast 停留下限单点 `TOAST_MS_FLOOR` 对 error / timeout ≥8s 生效 + `toast()` / `_finishToast()` 两条排期路径都走 `toastMs(kind, ms)` 且 `ms` 缺省为 `null` | 下限降到 4s / 排期改回裸 `ms` / `ms = null` 写死 4000(三例实测全红) |
| `test_frontend_ctx_menu_refit_by_measured_size` | 浮层菜单开层**实测**钳位接线(issue 26-10-06-1717): `_menuFit` 按 `offsetWidth/offsetHeight` 算(常量估算回潮即红)且以视口为界 + 先复位兜底限高; 三个菜单容器 ref(`ctxMenu`/`headMenuEl`/`filePrioEl`)与三个开层 watcher 的 `(stateKey, refName)` 一一对上且都在 `$nextTick` 里量; `_menuFitRefit` 现读 `this[stateKey]`/`this.$refs[refName]` 并守 `visible` | 摘 `ref="ctxMenu"`(实测红在「ctx-menus.html 缺 ref」) |
| `test_api_state_skips_jsonable_encoder` | 热路径不得走 `jsonable_encoder`(计数替身; 清单排除 `/api/config/schema`) | `return payload` |
| `test_api_state_view_scoped_payload` | 按视图回传 + 未知 `view` 全回(保守默认) | 改 `VIEW_ARRAYS` |
| `test_ensure_group_state_show_view_carries_member_index` | 追剧页回传必须**连带成员索引**(groups+singles, 不回 torrents) | 只回 shows |
| `test_api_readonly_endpoints_short_cache` | 短缓存四边界: 窗口内合并 / **写命令后立即失效** / 断连仍 503 | 去掉失效接线 |
| `test_view_rebuild_waits_for_client_consume` | 上一版没被取走就不产下一版; **脏标记必须保留** + **`force=True` 必须绕过** | 去掉门控 |
| `test_api_fs_dirs_case_sibling_is_outside_whitelist` | 大小写兄弟目录判越界(**仅 Linux 真跑**, win32 skip) | 让 `_fs_real` 做 NTFS 折叠 |

## 流量聚合封口批次守阵 (26-10-13, 红验 26-10-13 @工作区)

> 已外迁: 5 条守阵(小时 cov 下限 / 亚秒跨日封口 / 同 epoch 重封 / 迟到补记 / 逐系列隔离) → [attachments/guards-batches-archive.md](attachments/guards-batches-archive.md) 「流量聚合封口批次守阵」。

## 种子状态 A 系批次守阵 (26-10-13-0540 S1 值层 / S2 deferral / S3 收尾, 红验 26-10-13 @工作区)

> 已外迁: 15 条守阵(own_writes 逐出/TTL/组判据/不落盘 · run_due defer_gate · 跳检与决策链让位 · 值层/值域/发射/一致性/端到端/幂等) + 语义主线与口径链接 → [attachments/guards-batches-archive.md](attachments/guards-batches-archive.md) 「种子状态 A 系批次守阵」。

## 任务队列 dry_run 契约 (26-11-03, 红验 26-11-03 @工作区)

| 守阵 | 钉住的结论 | 红验 |
|---|---|---|
| `test_taskqueue.py::test_run_due_passes_dry_run_to_handler` | `--dry-run` 的任务路径安全承诺压在三环实参链上: `run_due(dry_run=True)` → `_run_one(task, dry_run)` → `handler(task, dry_run)`; handler 第二实参必须是 dry_run 原值, 缺省 `False` 反向对照 | 运行时替换还原两种变异形态(`run_due` 传 None / `_run_one` 传 None)⇒ 两条实测全红(真值断言失败), 还原后绿; 同池 mutmut 复跑已转 KILLED(见切片 26-10-31-0518) |

> 本守阵由变异审计 core/ W1(R25 S5)补入, 对应 issue `26-10-31-0449-bug-taskqueue-dry-run-chain`。

## flaky 治理批次守阵 (26-11-06, S6 收口)

| 守阵 | 钉住的结论 | 红验 |
|---|---|---|
| `test_platform_tolerance_guards.py::test_repo_skipif_all_have_reason_and_owner` | tests/ 全部 `pytest.mark.skipif` 必须带 `reason=`(平台/环境语义依据)与 `# owner: <名>`(装饰器行范围内) —— 规范单点 `tests/platform_tolerance.py` | 删任一 owner 注释 ⇒ 红(2026-11-06 实测: `test_grouping_relocate.py:116` 注入后红在「缺负责人」); 合成源红验内建(缺 reason/缺 owner/双全三形态) |
| `test_platform_tolerance_guards.py::test_platform_tolerance_constants_sane` | 容差常量自洽: 下界余量 >= 2 tick(31.2ms)且 >= 历史最小充分余量 20ms, 刻度常量 15.6ms 不被无意改小 | 改 `WIN_TIMER_TICK_S`/`SLEEP_LOWER_MARGIN_S` 破坏不等式 ⇒ 红 |

> 规范正文: [file-conventions.md](file-conventions.md)「跨平台断言规范」节; 计时余量的判别与实证
> 见 [../pitfalls/testing/timing-tolerance.md](../pitfalls/testing/timing-tolerance.md)。
> 随机序周巡检(pytest-randomly)不是守阵而是巡检入口: `commands run test.random-order`,
> 约定见 [flaky-ledger.md](flaky-ledger.md)「巡检约定」节。

## 类型注解 / mypy allowlist (26-11-06, 计划 26-11-05-0635 §04 S4, 专题 type-annotations-mypy)

| 守阵 | 钉住的结论 | 红验 |
|---|---|---|
| `test_mypy_allowlist_guard.py`(11 例; 真仓对账面 = `test_repo_allowlist_matches_frozen`) | 钉住 `pyproject.toml` `[tool.mypy]` 三张清单: ignore_errors 整模块豁免面 / disable_error_code 的 (模块, 码) 豁免对 / 收紧面 disallow_untyped_defs 模块集合 —— 新增豁免红、递减不红, 但**递减须同步撤下冻结条目, 撤下后回加当场红**(递减不可逆) / 顶层 disable_error_code·ignore_errors 全局豁免一律红 / 收紧面回撤红、新增收紧不红 | 合成 TOML 回加已递减的 `auto_qb.core.qbclient[override]` 对(内建 `test_frozen_rejects_re_add_of_reduced_exemption`)⇒ 红; 2026-11-07 实测: 向真仓 pyproject 注入 `auto_qb.core.redprobe_tmp[union-attr]` ⇒ 红在「新增 disable_error_code 豁免对(守阵冻结外)」, 撤注入后 11 passed |

> 只做静态扫描, **不在 pytest 内跑 mypy** —— 豁免面外的类型正确性由 `commands run dev.typecheck` 验收(拍板 D3)。
> 登记来源: issue `26-11-06-0744-docs-guards-mypy-allowlist-unregistered`(守阵 2026-11-06 随 S4 落地但漏登记, 2026-11-07 补登记)。

## infra 依赖纪律 AST 守阵 (26-11-08, issue 26-11-08-0703)

| 守阵 | 钉住的结论 | 红验 |
|---|---|---|
| `test_infra_import_discipline.py::test_repo_infra_imports_follow_discipline` | `infra/` 全部 .py 的运行期 import 只允许 stdlib / 三方 / `auto_qb.infra*`; 解析到 `auto_qb` 根包或其余子包(config / core / webui / tray / ...)、爬出根包的相对导入一律红(白名单口径, 以后新增层自动罩住)。TYPE_CHECKING 块按 R4#18 放行, 但例外只许 `auto_qb.config*`, core / 表现层只做标注也不许上行; else 分支与函数内延迟导入照查 | 合成源 9 种上行形态逐条判红 + tmp 目录注入违例文件判红; 真仓 16 文件镜像注入 `from ..config import NotifyConfig` 实测恰好一条红(2026-11-08); **反空转**: 真仓断言文件数 >=10 且扫到 notify.py 的例外节点 |
| `test_infra_import_discipline.py` 其余 7 例 | 放行面(包内一层相对 / stdlib / 三方 / 绝对自引用) / config 例外不外扩 / TYPE_CHECKING 的 else 仍属运行期 / 延迟导入照查 | 合成源内建, 每条用例本身即红验样本 |

> 判据来源: [计划 26-09-22-2112 §04](../plans/26-09-22-2112-src-layout-restructure-plan.html) 依赖方向表 + `infra/__init__.py:15` 纪律声明; R4#18 把 notify.py 的 config 引用收进 TYPE_CHECKING(运行期零依赖)。用 AST 而非文本: 纪律声明本身就写在 `__init__.py` 的 docstring 里, 文本扫描会假红。

## xdist 临时脚本隔离 (26-11-09, issue 26-11-08-1955)

| 守阵 | 钉住的结论 | 红验 |
|---|---|---|
| `test_webui_static_r4_static_batteries.py::test_bundle_file_is_process_private` | `bundle_file` 落点掺 `os.getpid()` 且内容 == `read_shared` | 摘 pid ⇒ 红(2026-11-09 实测) |
| `test_extension_proxy_page_fetch.py::test_background_bundle_is_process_private` | `background_bundle` 落点掺 pid 且非空 | 摘 pid ⇒ 红(2026-11-09 实测) |

> 根因: xdist worker 共用自举实例根, 固定文件名被并发 `open(..., "w")` 截断 → node 读到 0 字节。判据见 [../pitfalls/testing/parallel-run.md](../pitfalls/testing/parallel-run.md)。

## 通用纪律

- **红验优先用运行时 monkeypatch 还原旧实现**(不碰工作区), `lru_cache` 记得先 `cache_clear()`。
- **一条守阵只钉一个结论**; 想同时钉两侧(过严 / 过松)就写两条断言 —— 只钉一侧会被"更严格"或"更宽松"两头骗过。
- **静态扫描类守阵必须先剥注释**: `os.path.normcase` / `colManual` 这些串就写在 docstring 与注释里当反例,
  纯文本扫描会被注释骗过(冒烟的 `_scan_filter_facets` 同理, 见 `_strip_js_comments`)。
- 相关坑的完整判据见 [../pitfalls/testing/assertions.md](../pitfalls/testing/assertions.md) 与
  [../pitfalls/testing/patching.md](../pitfalls/testing/patching.md)。
