# 303 passed(gtm 工具侧) —— 覆盖率门禁 P0 落地: 阈值 88 + 双 OS CI job + 一条命令 + 红验 3/3

> 摘要: gtm 工具侧覆盖率门禁 P0 落地 —— 阈值 **88** 生效即转绿(实测 **90.10%**), CI 新增 `test-gtm` 双 OS job, 本地一条 `commands run test.gtm` 出 TOTAL; 门禁自身红验 3/3 全红, 并实测出「88 阈值可容忍 ≈50 单位未测代码」这一余量事实
> 基线时间: 2026-10-21 01:54
**Refs:** memory-bank/plans/26-10-21-0120-plan-gtm-coverage-gate.html, memory-bank/tasks/26-10-21-test-gtm-coverage-gate.md

## 验收数字

gtm 工具侧(Windows 本机, `commands run test.gtm` = `uv run --directory tools/global-traffic-monitor pytest`, 2026-10-21 01:54, 串行无 xdist):

```
TOTAL                   1943    180    462     50    90%
303 passed in 45.08s
Required test coverage of 88% reached. Total coverage: 90.10%
```

**这是工具侧独立口径, 与主仓 `test.full` 的 `--cov=src` 是两套账**: 分母 = 1943 语句 + 462 分支出口 = 2405 单位, 未覆盖 180 行 + 50 partial = 230 单位。主仓最新切片(99.41%)与本切片**不可比、不可合算**(I1)。

口径注记:

- **与计划基线的差**: 计划里记的 90.4% 是**绕道口径**(隔离环境 + `PYTHONPATH=src` + `--cov=src/gtm`); 本切片是**包名口径**(`--cov=gtm`, 工具目录内 `uv run pytest`)的首次实测 = **90.10%**。两者差 0.3 点, 属两种口径的路径/行归属差异 —— 计划 §2.1 的警告「两种口径不可混着比」在此兑现, 后续一切数字只认包名口径。
- **用例 303 / 耗时 45.1s**(计划记 126.4s 是隔离环境首轮, 含依赖安装与冷缓存; 本机稳定在 45–49s)。串行不变(D3 不加 xdist)。
- **门槛行零 FAIL**: `--cov-fail-under=88` 首次生效即转绿, 余量 **2.10 点 ≈ 50 单位**。
- **豁免行数(M5)**: `# pragma: no cover` 全工具侧 **1 行**(`units.py:54`), 零新增。
- **缺口地图(包名口径, 与计划 §2.2 逐档一致)**: `__main__` 69 / `server` 50 / `storage` 31 / `config` 24 / `installer` 21 / `identity` 19 / `sampler` 8 / `notifier` 6 / `units` 2 = **230 单位**。
- **Linux 侧数字本机未取得**: 本机只能跑 Windows; ubuntu 侧真值以 CI `test-gtm` job 首次运行为准(阈值取双平台较低者定档的纪律不变, 88 已按「低侧 − 0.8」留足余量)。按 `testing/baseline.md` 常驻警告, 两侧都测到之前本切片只作 Windows 侧事实源。
- **本机取数绕道(必须记下来)**: 沙箱工作区目录带 Low 完整性标签, 工作区内新建的 venv 读不到自己的 `pyvenv.cfg`(exit 107), 故本机用 `UV_PROJECT_ENVIRONMENT` 指向工作区外跑; **命令配置里没有写死该变量**, CI 与用户本机照旧用子包内 `.venv`。成因与判别链见坑档 `pitfalls/testing/sandbox-venv-in-workspace.md`。

## 门禁自身红验(M3 · 3/3 全红)

三种注入各自变红, 验完全部还原(`git status` 产品码零改动, 阈值回到 88):

| # | 注入 | 结果 | 判定 |
|---|---|---|---|
| M1 | `--cov-fail-under` 临时抬到 **99** | `FAIL Required test coverage of 99% not reached. Total coverage: 90.10%` · exit 1 | 红 ✓ |
| M2 | 抽走一个测试档(`tests/test_storage.py` → 临时挪出) | `TOTAL 86.53%`(259 passed) · exit 1 | 红 ✓ |
| M3 | 新增一个**未被任何用例覆盖**的模块(3 个函数 / 96 单位) | `TOTAL 86.44%`(2039 语句) · exit 1 | 红 ✓ |

**M3 的余量事实(本轮新测得, 计划未写)**: 先用 32 单位的未测探针试注入, 结果 **88.34% 仍然绿** —— 88 阈值从 90.10% 起算**可容忍约 50 单位未测代码**而不响(与计划 §2.3「88 = 实测 − 2.4 ≈ 58 单位」的换算一致)。所以「加一个未测函数」这类小注入**不会**让 88 变红, 红验必须注入 ≥50 单位; 反过来说, 这也正是起步值不能再降到 85 的量化理由(85 可容忍 ≈123 单位)。

## 本改动面

只装闸门与跑法, **零产品码改动、零新增用例**(P0 的价值在「装上的那一刻」):

| 文件 | 改动 |
|---|---|
| `tools/global-traffic-monitor/pyproject.toml` | dev 组加 `pytest-cov`; `[tool.pytest.ini_options]` 补 `addopts = "-q --cov=gtm --cov-branch --cov-report=term-missing --cov-fail-under=88"`(阈值随阶段抬) |
| `tools/global-traffic-monitor/uv.lock` | `uv lock` 重生成(工具侧独立锁, +coverage 7.16.2 / +pytest-cov 7.1.0) |
| `.github/workflows/ci.yml` | 新增 `test-gtm` job: 双 OS(ubuntu + windows)× py3.12, `working-directory: tools/global-traffic-monitor`, 缓存 glob 指向工具锁, 上传 `coverage.xml`; 主仓 `test` / `test-windows` 两 job 未动 |
| `.commands/test/config.toml` | 新增 `test.gtm`(一条命令出 TOTAL, 门槛由 addopts 承担; 展开的命令定义只在包内留一份) |
| `tools/global-traffic-monitor/README.md` | 「开发」拆出「测试与覆盖率门槛」小节: 独立口径 / 阈值阶梯 / 单档必加 `--no-cov` / 两侧差异 / 豁免只减不增 / CI 同一份 addopts |
| `memory-bank/pitfalls/testing/sandbox-venv-in-workspace.md` | 新坑档: 沙箱工作区内 venv 自读 `pyvenv.cfg` 失败(exit 107)的判别链与 `UV_PROJECT_ENVIRONMENT` 处置 |

验收 DoD 对照: 两侧 `uv run pytest` 出 TOTAL ✓(Windows 已验; ubuntu 待 CI 首跑)/ 删测试档后门禁变红 ✓(M2)/ 加未测代码变红 ✓(M3, 需 ≥50 单位)/ 抬阈值变红 ✓(M1)/ CI `test-gtm` 已配置 ✓(真跑待首次 PR)/ `commands run test.gtm` 可用 ✓ / README 可复现 ✓ / 基线切片落盘 ✓ / 覆盖率数字不要求变化 ✓(90.10% 不变)。
