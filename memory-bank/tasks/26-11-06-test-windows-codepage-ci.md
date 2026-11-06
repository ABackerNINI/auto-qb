# 26-11-06-test-windows-codepage-ci — 修复 GitHub CI Windows 码页六红: 文本子进程显式 UTF-8 收端 + 全仓 AST 守阵

**Status:** Done
**Added:** 2026-11-06
**Updated:** 2026-11-06
**Summary:** GitHub windows-latest 的 cp1252 让 6 条 node 探针用例集体红; 根因是 `text=True` 让 locale 猜解码, 收端补齐 `encoding`/`errors` 16 处、超时统一 60s、落全仓 AST 守阵, 零产品代码改动。
**Topics:** test-windows-codepage-ci
**Refs:** memory-bank/testing/baselines/26-11-06-1950-test-windows-codepage-ci.md

## 本篇只回答

英文 Windows runner 上 node 探针为什么集体红、怎样一次收口且不再复发 —— 不涉及被测产品行为语义。

## 原始请求

1. 「修复github ci报错」(附 GitHub Actions `windows-latest` / Python 3.13.17 的 pytest 失败日志: 6 条用例红, 多条 `PytestUnhandledThreadExceptionWarning` 与 `UnicodeDecodeError: 'charmap' codec`)。
2. 「似乎没做code review」—— 指出本批越过累计 ≥50 行的分批评审硬线却漏评, 要求补做。
3. 「提交」—— commit + push, 并触发收尾 DoD。

## 思考过程与决策

- **六红归一族**: `subprocess.run(..., text=True)` 未显式编码时按 locale 解 node 写的 UTF-8 字节 → `UnicodeDecodeError` 抛在 `subprocess._readerthread` 后台线程 → `proc.stdout is None` → `json.loads(None)` 报 `NoneType` / `.strip()` 报 `AttributeError`。本机 `PYTHONUTF8=1` 把 preferred encoding 顶成 UTF-8, 所以本地恒绿、CI 恒红。
- **只写 `encoding="utf-8"` 不够**: 严格解码遇 stderr 混入码页字节会打死读线程、管道无人读、子进程卡在写管道 → `TimeoutExpired`(ghint 探针)。表象像 JS 死循环, 调超时是治症状; 定案要 `errors="replace"`。
- **口径拍板**: 收端 `encoding="utf-8"` + `errors="replace"` **两项必填**(不是可选项), node 电池超时统一 60s(与 `test_webui_static_dom_panel_drawer.py` / `panel_misc.py` 既有写法同口径)。不改产品/运行时 JS, 不改 `.github/workflows/ci.yml`。
- **守阵而非只修一遍**: `tests/test_platform_tolerance_guards.py` 加全仓 AST 对账(按函数名匹配 `run`/`check_output`/`check_call`/`Popen`, 罩住两种 import 形态)+ 合成源活性探针; 评审后升级为**校验字面量值**, 不只看关键字在不在。独立严格审计: 全仓文本子进程调用 0 不合规。
- **反面证据**: 本机 `PYTHONUTF8=0` 压回的是 cp936, **不是** runner 的 cp1252; 6 红里本机只复现出 5 红, 超时那条改前本机就绿、修复依据只有 CI 日志。本机全绿不等于等价验证, 最终判据仍是 `windows-latest` 实跑。
- **复发闭环**: 坑档 `memory-bank/pitfalls/ops/console-encoding.md`(L0) 与 `memory-bank/pitfalls/testing/ci-only-guard.md` 早已写同类陷阱。**为什么没命中** —— 旧 `处置` 把 `errors="replace"` 写成括号里的「可加」, 且没有任何机检, 新用例照抄旧写法; 两条坑档各记 `复发 +1`, 前者把口径收成两项必填, 后者补解码侧第 ⑤ 变体与复现局限。
- **评审决策**: 第一批全能档 1 个只读 reviewer, 4 条发现(1 major / 3 minor)全部引文校验通过、裁定相关, 全部当场修、入池 0; major 正是守阵只查键存在不校验值, 已重写并扩活性样本; 重写后另派只读子代理做接缝终审, 返回 0 发现。

## 实现计划

1. S1 复现: `env -u TMPDIR PYTHONUTF8=0` 下用 node 发中文的最小脚本, 坐实 `proc.stdout is None`; 重跑 6 条 CI 用例看红面。
2. S2 清点: AST 扫 `tests/**/*.py`, 分出「漏声明」与「只声明 encoding」两类调用。
3. S3 修复: 16 处调用补 `encoding="utf-8", errors="replace"`; `test_kb_nav_interaction.py` 四处补 `errors` 并抽 `NODE_PROBE_TIMEOUT = 60`。
4. S4 守阵: 全仓 AST 对账 + 合成源活性探针 + 模块 `## 测试计划` 清单。
5. S5 坑档: 两份坑档记 `复发 +1` / 第 ⑤ 变体 / 反面证据, 重跑 `kb.index` 与 `kb.check`。
6. S6 评审: 分批评审 + 4 条发现修复 + 接缝终审; 连带修掉滚入本批的两处非 ASCII 图形符号。
7. S7 收尾: 提交闸门 `dev.fmt` 格式化、`test.full` 实测并新建基线切片、随本专题入库。

## 子任务状态表

| 步 | 内容 | 状态 |
|---|---|---|
| S1 | 最小复现 + 6 条用例红面 | Done(2026-11-06) |
| S2 | AST 全仓清点两类漏声明 | Done(2026-11-06) |
| S3 | 16 处收端补齐 + 超时统一 60s | Done(2026-11-06) |
| S4 | AST 守阵 + 活性探针 + 测试计划清单 | Done(2026-11-06) |
| S5 | 两份坑档复发记录与口径收紧 | Done(2026-11-06) |
| S6 | 分批评审 4 发现全修 + 接缝终审 0 发现 | Done(2026-11-06) |
| S7 | 格式化 / 基线切片 / 入库 | Done(2026-11-06) |

## 进度日志

### R0 · 立档 (2026-11-06)

- 六红定位到同一收端解码族, 修复范围只落 `tests/` 与事实性坑档; `test.quick` 在常规与 `PYTHONUTF8=0` 模拟 CI 码页下均全绿(见 `commands run kb.baseline`), 两包脚本测试、`kb.check` 十道校验同样全绿。
- 复现局限已写进 `ci-only-guard.md`: cp936 只覆盖 5/6 红, 超时那条以 CI 日志为准。
- review: 全能档 1 个只读 reviewer, 4 条发现(1 major / 3 minor)逐字引文校验 4/4 通过、裁定全相关、blocker 0、修 4、入池 0; 修复增量约 30 行(<100 不强制二轮)仍派接缝终审, 逐项核守阵活性样本、跨文件计数、两处符号替换与范围守恒, 返回 0 发现。
- 提交闸门 `dev.fmt` 因本批含 `tests/` 改动而触发, 顺带把两份既有 `.commands/review/scripts/*.py` 格式化到项目 yapf 口径(HEAD 版本本就不合规); 格式化后守阵、受影响用例与 review 包 scoped 测试复验全绿。

- 2026-11-06 19:46 修复 GitHub CI windows-latest cp1252 下 6 条 node 探针红: 16 处收端显式 UTF-8+replace、超时统一 60s、全仓 AST 守阵与活性探针、两份坑档复发 +1; 分批评审 4 发现全修 + 接缝终审 0 发现, 全量与模拟码页全绿(见 kb.baseline), 随本专题入库
