# 26-10-21-test-gtm-coverage-gate — gtm 工具侧覆盖率门槛实施 (门禁落地 → 96 区间)

**Status:** Done
**Added:** 2026-10-21
**Updated:** 2026-10-21
**Summary:** 把覆盖率第二轮计划 P2-T2.6 的评估结论落成实施并完结: 给 tools/global-traffic-monitor 装独立门禁(双 OS CI job + 一条 `test.gtm`), 四阶段把可测面从实测 90.4% 推到 **99.42%**(用例 303 → 410), 阈值阶梯 88 → 91 → 93.5 → **98.5** 每档落地当轮转绿; 残余 **14 单位 / 7 条**全部带理由登记, 无一条属本该测没人测; 口径与主仓彻底独立, 跨进程契约(M6)同轮跑规则已写入 README
**Topics:** test-gtm-coverage-gate
**Refs:** memory-bank/plans/26-10-21-0120-plan-gtm-coverage-gate.html, memory-bank/pitfalls/testing/sandbox-venv-in-workspace.md, memory-bank/testing/baselines/26-10-21-0154-gtm-coverage-gate-p0.md, memory-bank/testing/baselines/26-10-21-0216-gtm-coverage-gate-p1.md, memory-bank/testing/baselines/26-10-21-0224-gtm-coverage-gate-p2.md, memory-bank/testing/baselines/26-10-21-0229-gtm-coverage-gate-p3.md

## 原始请求

1. 「gtm 工具侧覆盖率门槛实施计划: 根据上一轮覆盖率提升的结论写一个针对 gtm 的计划」(用户指令, 2026-10-21 01:15)
2. 隐含约束: 上一轮覆盖率第二轮计划(`plans/26-10-20-2101-plan-test-coverage-uplift-2.html`)把「gtm 工具侧覆盖率门槛实施」明确列为**范围外**, 只在 P2-T2.6 出了评估结论 —— 本轮就是接这条结论立实施计划。

## 思考过程与决策

- **先补实测, 不抄结论里的数字**: T2.6 当时因为工具 `.venv` 坏(`pyvenv.cfg` 不可读, exit 107)没取到数, 只给了「起步 85」这个保守下限。本轮用隔离环境 + `PYTHONPATH=src` + `--cov=src/gtm` 实测到真值: **303 passed / 126.4s / TOTAL 90.4%**(1943 语句 + 462 分支 = 2405 单位; 缺口 180 行 + 50 partial = 230 单位)。计划里一切换算都基于这一轮实测, 并明确标注「这是绕道取的口径, P0 修好 venv 后以工具目录内 `uv run pytest` 为准」。
- **起步阈值从 85 上调到 88, 并把理由写进计划**: 85 距实测 5.4 点 ≈ 130 个单位的回沉空间, 等于允许塞 130 行未测代码而闸门不响; 88(实测 − 2.4 ≈ 58 单位)既留了双平台差异与口径迁移的缓冲, 又拦得住一个中等功能的量级。**偏离前序结论必须给理由, 不能默默改**。
- **门禁先立, 覆盖后补**: P0 一个用例都不写, 只装闸门(dev 组 pytest-cov / addopts 门槛 / CI 新 job / `test.gtm` / README / 切片)。理由是闸门的价值在「装上的那一刻」就成立, 不必等覆盖率涨完 —— 这也是主仓第二轮「先赎绿门槛再冲刺」的同一条经验。
- **口径坚决独立**: 不把 `src/gtm` 并进主仓 `--cov=src`。并入会稀释主仓刚赎绿的 99.41%(分母多 2405 单位)、把平台差异放大到 4 个 CI 组合、并破坏工具侧「只依赖 psutil/filelock/pyyaml、不受 auto-qb 依赖变动影响」的设计。三害换一便, 不换。
- **终点不追 99**: 主仓 99% 的口径套到工具侧不成立 —— installer 的 winreg 分支只在 Windows 可执行、`os.getuid` 只在 POSIX, 平台独占面天然到不了; 硬追只能靠 pragma, 与「豁免只减不增」冲突。定 96 区间(实测定档), 残余逐条登记理由。
- **缺口形态决定阶段顺序**: `__main__.py` 的 CLI 入口全路径(`run()` 主体 260-321 + `main()` 分发, 69 单位)与 `server` 路由守卫矩阵(50 单位)是「没测过」而非「测不到」, 且正好是顺序不变式与跨进程契约所在 → 放 P1 先清; 容错出口(OSError 长尾)放 P2 批量扫; 平台独占面留 P3 定档。

## 实现计划

1. 立计划制品(`plans/26-10-21-0120-plan-gtm-coverage-gate.html`, Open, 待拍板 D1–D5) + 本档案 + 双向认领 + 索引重生成。
2. **P0 门禁落地**(零覆盖增量): 修 venv → dev 组 pytest-cov + addopts 门槛 88 → CI `test-gtm` job(双 OS × py3.12) → `test.gtm` 命令 → README 口径 → 门禁自身红验 3/3 → 基线切片。
3. **P1 主路径整块**: `run()` 全路径 + 路由 400 守卫矩阵 + notifier/sampler 余量 → ≥92.5% → 阈值抬 91。
4. **P2 平台与容错面**: installer 三后端注入 / storage 搬迁恢复 / identity 让位代拉 / config 读写错误 → ≥94.8% → 阈值抬 93.5。
5. **P3 定档收尾**: 边角收尾 + 残余逐条登记 + 阈值 = 低侧实测 − 0.8 + 契约联动规则成文 → 计划转 Done。
6. 机制 M1–M6 随阶段验收落地(阈值阶梯 / 双平台切片 / 变异红验 / 增量不欠账 / 豁免治理 / 与主仓契约联动)。

## 子任务状态表

| 步 | 内容 | 状态 |
|---|---|---|
| 0 | 立档 + 计划制品(Open) + 认领链 + 索引重生成 | Done (2026-10-21) |
| 1 | P0 · 门禁落地(阈值 88, 零覆盖增量) | Done (2026-10-21) |
| 2 | P1 · 主路径整块与路由守卫(≥92.5, 阈值 91) | Done (2026-10-21) |
| 3 | P2 · 平台后端与容错出口(≥94.8, 阈值 93.5) | Done (2026-10-21) |
| 4 | P3 · 定档与残余登记(95.5–96.5, 阈值 = 实测 − 0.8) | Done (2026-10-21) |

### P3 子任务明细

| # | 任务 | 状态 | 落点 |
|---|---|---|---|
| T3.1 | 边角收尾(+15–25 单位) | **主动不做** | P2 结束时残余已全为不可达(平台独占面在 Windows 物理不可达), 再写用例属「为数字写用例」 |
| T3.2 | 残余逐条登记(≤ 80 单位) | Done | 计划 §10.1 + 本档案下方「残余登记」节; **14 单位 / 7 条**, 为上限的 17.5% |
| T3.3 | 阈值定档 | Done | `pyproject.toml` → `--cov-fail-under=98.5`(= 99.42 − 0.8 = 98.62 → 向下取 0.5 倍数), 余量 0.92 点转绿 |
| T3.4 | 联动说明(跨进程契约) | Done | `README.md` 新增「### 跨进程契约: 与主仓同轮跑(M6)」+ 本档案 M6 节 |

## 进度日志

### R0 · 立档 (2026-10-21)

**实测(2026-10-21 01:2x, Windows / CPython 3.13.15)**: 工具侧 303 passed, 126.4s 串行; TOTAL **90.4%**, 分母 1943 语句 + 462 分支 = 2405 单位, 缺口 180 行 + 50 partial = 230 单位; 每单位 ≈ 0.0416 点。

**取数方式(必须记下来)**: 工具目录 `.venv` 已坏 —— `pyvenv.cfg` 存在但任何 `.venv/Scripts/python.exe` 调用都 `Cannot read ... pyvenv.cfg`, exit 107, `uv run` 直接失败。改用隔离环境跑:

```
PYTHONPATH=src uv run --isolated --no-project --python 3.13 \
  --with pytest --with pytest-cov --with psutil --with filelock --with pyyaml \
  pytest -q --cov=src/gtm --cov-branch --cov-report=term-missing
```

→ 这只是排障口径。**P0-T0.1 修好 venv 后, 一切数字以工具目录内 `uv run pytest`(`--cov=gtm` 包名口径)为准, 两种口径不可混比**。

**缺口地图**: `__main__.py` 69 / `server.py` 50 / `storage.py` 31 / `config.py` 24 / `installer.py` 21 / `identity.py` 19 / `sampler.py` 8 / `notifier.py` 6 / `units.py` 2(已是 pragma 防御支)。前三档合计 150 单位 = 65%, 全是「本该测没人测」; 真正到不了的只有 installer 平台独占面与少量真机探测, 约 70 单位。

**与前序结论的偏离**: T2.6 给「起步 85」, 本计划改 88 —— 85 距实测 5.4 点(≈130 单位)会让门禁形同虚设。理由与换算见计划 §2.3。

**计划形态**: P0 门禁落地(零覆盖增量, 阈值 88) → P1 ≥92.5(阈值 91) → P2 ≥94.8(阈值 93.5) → P3 95.5–96.5(阈值 = 低侧实测 − 0.8); 机制 M1–M6; 待拍板 D1–D5(起步阈值 / CI 矩阵 / 是否并行 / 终点口径 / `test.gtm` 形态)。

- 2026-10-21 01:20 gtm 门禁计划入库: 立计划(plans Open, 待拍板 D1–D5) + 认领档案, 双向认领链与索引重生成

- 2026-10-21 01:23 gtm 门禁计划入库: 实测 90.4% 基线 + 计划(Open, 待拍板 D1–D5) + 认领档案, 双向链与索引重生成

### R1 · P0 门禁落地 (2026-10-21 01:54)

**结果**: 303 passed / 45.08s / TOTAL **90.10%**, 阈值 **88** 生效, 余量 2.10 点。**零用例新增** —— P0 只装闸门。

**落地件**: dev 组加 `pytest-cov` + `uv lock` 重生成(+119 行) / `[tool.pytest.ini_options] addopts` 带 `--cov=gtm --cov-branch --cov-fail-under=88` / CI 新增 `test-gtm` job(双 OS × py3.12, `fail-fast: false`) / `.commands/test/config.toml` 新增 `test.gtm`(一行 `uv run --directory`) / README「测试与覆盖率门槛」小节 / 基线切片。

**门禁自身红验 3/3**: ①阈值抬 99 → 红; ②删一个测试档 → 红; ③加一个 96 单位的未测探针模块 → 86.44% 红。**顺带测到一条有用的事实**: 32 单位的探针仍停在 88.34% 绿 —— 即 88 档能容忍约 50 单位未测代码, 起步阈值定位准确(见 P0 切片)。

**踩到的坑(已立 pitfall)**: 工具目录 `.venv` 坏到 `uv sync` 都起不来(`exit 107` / `uv trampoline ... permission denied (os error 5)`)。根因是**工作区目录带 Low 完整性标签 + 能力 SID ACL**, 工作区内 venv 的 `python.exe` 读不到自己的兄弟文件 `pyvenv.cfg`; 把 venv 拷到工作区外就能跑。修法: `export UV_PROJECT_ENVIRONMENT=/tmp/gtm-venv`。**没有把这个环境变量硬编码进 `.commands/test/config.toml`** —— 它是机器局部缺陷的绕道, 不是项目配置。归档为 `pitfalls/testing/sandbox-venv-in-workspace.md`。

### R2 · P1 主路径整块 (2026-10-21 02:16)

**结果**: 372 passed(+69) / 62.64s / TOTAL **95.80%**, 阈值抬 **91**, 余量 4.80 点。净清偿 ≈137 单位。

**做了什么**: 新建 `tests/test_main_run.py`(约 30 例, 816 行)把 `__main__.run()` 全路径打通 —— 用 `Recorder` + 5 个 Fake(Storage/Sampler/Server/Notifier/Backend)+ `Harness.install()` 打 15 个猴子补丁, 核心断言是**完整有序调用序列**:

```
identity → resolve_startup → ensure_data_ownership → fill_primary_data_dir →
load_config → Storage → acquire_lock → Sampler → TokenManager → ControlServer →
server.start → clear_deferred → Notifier → storage.recover → run_loop →
notifier.close → server.stop → storage.close → storage.release_lock
```

这条序列同时守住了 S12/D8(单实例锁先于 `server.start()`)与 S14/D13(autostart 注册在锁之后、`server.start()` 之前)两条顺序不变式, 以及 teardown 四段固定次序。另含 5 条早退路径、`KeyboardInterrupt` + 收尾异常吞掉、`_run_loop` 单轮异常不杀循环、catch_up 待办保留、`main()` 分发、`runpy` 的 `__main__` 守卫。

`tests/test_server.py` 加「路由守卫矩阵」: 用**裸 socket** 发原始 HTTP 请求(绕开 urllib 的规范化), 5 条写路由 × 非对象载荷 / 空体各 400; 另有非法 `Content-Length`、超大 body、坏 JSON、非 UTF-8、`_dispatch` 500 兜底。

**红验 7/7 全杀**。**一处修了自己的假绿**: 认领竞争用例原夹具第一次就返回 `relay`, 于是 `decision.kind != "claim"` 提前返回, `claim_primary` 根本没被调到 —— 改成真竞态形态(`claim` 先返回 → 撞 `PrimaryRecordExists` → 重判为 `relay`)。

### R3 · P2 平台与容错面 (2026-10-21 02:24)

**结果**: 410 passed + 2 skipped(+38) / 65.11s / TOTAL **99.42%**, 阈值抬 **93.5**, 余量 5.92 点。净清偿 ≈85 单位。

**做了什么**: `test_installer.py` +9 / `test_storage.py` +11 / `test_identity.py` +6 / `test_config.py` +12。四个容错面档位全进 98–99%。两条 skipped 是平台独占面的 `skipif`(macOS `os.getuid`、POSIX `/bin/sh` 代拉), 在 ubuntu CI 上真跑 —— 双平台互补, 不是空位。

**红验 6 例 5 杀 1 等价存活**。存活那例(M2: 去掉 `storage.migrate_legacy_data_dir` 的「同址早退」)是**等价变异, 不是假绿**: 去掉后紧接着的「旧目录无 dat」与「目标非空」两道判据对同址场景给出同样结论。**据此判定该行是冗余防御, 记进残余表, 但没有为它改产品码**(范围守恒)。

### R4 · P3 定档与残余登记 (2026-10-21 02:29)

**结果**: 410 passed + 2 skipped / 63.61s / TOTAL **99.42%**, 阈值定档 **98.5**, 余量 **0.92** 点转绿。**零新增用例, 零产品码改动。**

**定档算式**: `99.42 − 0.8 = 98.62` → 向下取 0.5 的整数倍 = **98.5**。

为什么减 0.8 而不是 1.0: 0.8 点 ≈ 19 单位。残余的 14 单位全是平台独占/防御性/等价冗余, 不会再被正常开发顺手覆盖; 真正需要缓冲的是**双平台差异**。19 单位足以吸收一次平台分支翻转, 又不会宽到放行一个中等功能。

为什么不是 99: 距实测仅 0.42 点 = 10 单位。CI runner 的 psutil 版本差异导致某探测提前返回就会假红; **假红一旦常态化, 阈值就会被当噪音绕过, 那比没有门禁更糟**。

**T3.1 主动不做**: P2 结束时残余已全为不可达, 再写用例只能撞平台独占面(Windows 物理不可达), 属「为数字写用例」。

**T3.4 契约联动规则成文**(`README.md` + 下方 M6 节): 主仓 `webui/tool_client.py` 与 gtm `server.py` 是同一契约两端, 改端点/字段/状态码 → `test.one` + `test.gtm` **必须同轮跑**, 任一侧红即阻断。

## 残余登记(T3.2 交付物 · 14 单位 / 7 条)

| 位置 | 单位 | 类别 | 为什么到不了 |
|---|---|---|---|
| `config.py:138-139` | 2 | 防御性二重 | `math.isfinite` 已被 `parse_duration` → `_parse_number` 前置拦截, 正常链不可达 |
| `identity.py:400` | 1 | 平台独占 | `start_new_session` 是 POSIX 分支, Windows 走 `creationflags` |
| `identity.py:417` | 1 | 平台独占 | `/bin/sh` 代拉只在 POSIX 生效 |
| `installer.py:573` | 1 | 平台独占 | `os.getuid()` 在 Windows 不存在 |
| `server.py:515-516` | 2 | 防御性二重 | 500 兜底里再兜一次(客户端已断开, 写了也没人收) |
| `storage.py:194` | 1 | 等价冗余 | 「目标已有同名文件」与「目标非空整体跳过」行为等价(M2 存活实证) |
| `storage.py:254->259` | 1 | 记账产物 | `os.path.exists(tmp)` 为假只在 `os.replace` 成功后, 而成功后不进 except |

**没有一条是「本该测、只是没人测」的欠账。** DoD 上限 80 单位, 实际 14 = 17.5%。**残留处置: 不追第三轮** —— 再追只能靠 `pragma: no cover`(违反 M5 豁免只减不增)或改产品结构(违反 I3 不为数字改结构)。

## 常态机制(M1–M6 落地状态)

| 机制 | 状态 | 落点 |
|---|---|---|
| **M1** 阈值阶梯 | 生效 | `88 → 91 → 93.5 → 98.5`, 每档落地当轮转绿; 写在 `pyproject.toml` addopts, 附换算注释 |
| **M2** 双平台切片 | 生效 | 四份切片(`26-10-21-0154/0216/0224/0229-gtm-coverage-gate-p{0..3}.md`) |
| **M3** 变异红验 | 生效 | P0 3/3 · P1 7/7 · P2 6 例 5 杀 1 等价 |
| **M4** 增量不欠账 | 生效 | 阈值 98.5 即拦截器; 新增端点/配置键不同轮带测试必红 |
| **M5** 豁免治理 | 生效 | `pragma: no cover` 恒为 **1 行**(`units.py:54`), 四阶段零新增 |
| **M6** 契约联动 | 生效 | README「跨进程契约」节 + 下方规则 |

### M6 · 跨进程契约同轮跑规则

主仓 `webui/tool_client.py` 与 gtm `server.py` 是**同一契约的两端**(`POST /subscribe`、`/heartbeat`、`/unsubscribe`, `PUT /config`)。改任一侧的**端点、字段名、字段类型、状态码**时:

```
commands run test.one -- tests/test_traffic_monitor_client.py   # 主仓侧
commands run test.gtm                                          # 工具侧
```

**两条都跑, 任一侧红即阻断。** 只跑一侧等于放任契约单边漂移 —— 而这类漂移不会在提交时红, 只会在用户那边以「订阅莫名其妙失效」的形式出现(这正是本计划 §1 立论)。

- 2026-10-21 02:30 P3 定档完成: 阈值 98.5 落地转绿(余量 0.92), 残余 14 单位/7 条登记完毕, D1-D5 拍板回填, 计划与档案双转 Done; 残留处置=不追第三轮
