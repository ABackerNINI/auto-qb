# 410 passed + 2 skipped(gtm 工具侧) —— P2 平台与容错面: installer/identity/storage/config 错误出口全清, 阈值抬 93.5

> 摘要: gtm 工具侧 P2 完成 —— 补 38 例把 TOTAL 由 95.80% 推到 **99.42%**(净清偿 85 单位), 四个容错面档位全部进 98–99%; 阈值按阶梯抬到 **93.5** 并转绿; 变异红验 6 例中 5 杀 1 等价存活(实证一处冗余防御)
> 基线时间: 2026-10-21 02:24
**Refs:** memory-bank/plans/26-10-21-0120-plan-gtm-coverage-gate.html, memory-bank/tasks/26-10-21-test-gtm-coverage-gate.md

## 验收数字

gtm 工具侧(Windows 本机, `commands run test.gtm`, 2026-10-21 02:24, 串行无 xdist):

```
TOTAL                   1943      8    462      6    99%
410 passed, 2 skipped in 65.11s
Required test coverage of 93.5% reached. Total coverage: 99.42%
```

工具侧独立口径(分母 2405 单位), 未覆盖 **8 行 + 6 partial = 14 单位**; 与主仓 `test.full` 的 `--cov=src` 不可比、不可合算。

口径注记:

- **用例 372 → 410 (+38), skipped 2**: 两条 skipped 都是平台独占面的 `skipif`(macOS `os.getuid` 分支在 Windows 跳过; POSIX `/bin/sh` 代拉在 Windows 跳过)—— 它们在 ubuntu CI 上会真跑, 属双平台互补, 不是长期跳过的空位。
- **门槛行零 FAIL**: `--cov-fail-under=93.5` 生效即转绿, 余量 5.92 点。
- **逐档进展**: `config.py` 92% → **99%** / `identity.py` 92% → **98%** / `installer.py` 93% → **99%** / `storage.py` 93% → **99%** / `units.py` 98% → **100%**; `__main__` / `notifier` / `sampler` 保持 100%, `server` 保持 99%。
- **豁免行数(M5)**: 仍 **1 行**(`units.py:54`), 零新增。
- **耗时 65.1s**: 距 D3 的 180s 评估线仍远, 不加 xdist。
- **Linux 侧仍未取得数字**: 本机只能跑 Windows; ubuntu 侧以 CI `test-gtm` 首次运行为准。**本切片的 14 单位残余里有 3 处是 Windows 侧不可达的 POSIX 分支**(见下), 它们在 ubuntu 上应当被覆盖 —— 这也正是阈值取双平台低者的原因。

## 残余 14 单位(逐条带理由, P3 定档的输入)

| 位置 | 行数 | 类别 | 为什么到不了 |
|---|---|---|---|
| `config.py:138-139` | 2 | 防御性分支 | `_check_duration` 的 `math.isfinite` 是**二重防御**: `parse_duration` -> `_parse_number` 已对 inf/nan 抛 `UnitError`, 这行在正常调用链上不可达(要触发得绕过 units 层) |
| `identity.py:400` | 1 | 平台独占 | `kwargs["start_new_session"] = True` 是 POSIX 分支; Windows 走 `creationflags` |
| `identity.py:417` | 1 | 平台独占 | 代拉命令 `["/bin/sh", launch.sh]` 只在 POSIX 生效 |
| `installer.py:573` | 1 | 平台独占 | `os.getuid()` 只在 POSIX 存在 |
| `server.py:515-516` | 2 | 防御性分支 | 500 兜底里再兜一次: 连错误响应都写不出去(客户端已断开)时才走到, 写了也没人收 |
| `storage.py:194` | 1 | 等价冗余 | 搬迁时「目标已有同名文件则跳过」与前面的「目标非空则整体跳过」**行为等价**(M2 变异存活实证, 见下) |
| `storage.py:254->259` | 1 | 不可达 partial | `os.path.exists(tmp)` 为假只可能在 replace 成功后, 而成功后不会进 except |

平台独占 3 处 + 防御/等价 4 处 = **7 条**, 合计 14 单位; 没有一条是「本该测、只是没人测」的欠账。

## 变异红验(M3 · 新增 38 例抽 6 例 = 15.8%, 5 杀 1 等价存活)

| # | 变异 | 结果 |
|---|---|---|
| M1 | `installer._run` 的 `except FileNotFoundError` 改成 `except KeyError`(平台命令缺失不再包成 AutostartError) | 杀 ✓ `test_run_wraps_missing_platform_command` |
| M2 | `storage.migrate_legacy_data_dir` 去掉「旧目录与目标同址」早退 | **存活** —— 见下 |
| M3 | `config._check_int` 不再拒 bool | 杀 ✓ `test_validate_rejects_bool_on_every_numeric_field` |
| M4 | `identity.clear_deferred` 不再吞 OSError | 杀 ✓ `test_clear_deferred_swallows_oserror` |
| M5 | `storage._load_registry` 不再校验订阅条目的 endpoint 类型 | 杀 ✓ `test_recover_skips_corrupt_subscriber_entries` |
| M6 | `config._check_str` 不再拒空串/空白串 | 杀 ✓ `test_validate_rejects_bad_string_fields`(两个参数化用例同时红) |

**M2 存活是等价变异, 不是假绿**: 去掉同址早退后, 紧接着的「旧目录无 `history_traffic.dat`」与「目标非空」两道判据对同址场景给出同样结论(同址时目标里必然已有那个 dat, 于是判「非空」)。也就是说 `storage.py:179-180` 是**冗余防御**, 删掉它不改变任何可观测行为 —— 这条已记进上面的残余表, 属「值得知道但不必为它改产品结构」的一类。

产品码全部 `git checkout` 还原, 工作树零产品码改动。

## 本改动面

只补测试 + 一行阈值, **零产品码改动**:

| 文件 | 改动 |
|---|---|
| `tests/test_installer.py` | +9 例: 基类三个钩子 `NotImplementedError` / `_run` 的 FileNotFoundError 与 OSError 两支 / winreg 读值 OSError / 卸载「判存在与删之间被删」竞态 / 卸载 OSError / 惰性 import winreg / 解释器路径为空 / macOS uid 缺省取 `os.getuid`(skipif POSIX) |
| `tests/test_storage.py` | +11 例: `remove_endpoint` 的 OSError / 搬迁同址早退与中途中断 / `atomic_write_text` 空路径与「清理也失败」/ dat 非法日期行跳过 / 锁 meta 删除失败吞掉 / 锁 `with` 语法与持锁期间二次获取 / meta 写失败只 DEBUG / Storage `with` + 显式 `load()` / state 订阅条目局部损坏 / `close()` 最终落盘 |
| `tests/test_identity.py` | +6 例: `read_id_file` OSError 降级 / 补写 data_dir 失败只 WARNING / 清注记 OSError / `_spawn` 的 detached 无窗口形态 / POSIX 代拉形态(skipif Windows) / 认领竞争输家按赢家重判(**改成真竞态: 先 claim 再撞 PrimaryRecordExists**, 原写法在 `kind != "claim"` 就返回, 属夹具假绿, 已修) |
| `tests/test_config.py` | +12 例(含参数化): 载荷非映射 / 三类数值字段各自拒 bool / 非有限时间值 / 非正大小 / 字符串字段空与空白与非串 / 读配置 OSError / 迁移遇非映射 / 迁移遇校验失败不改写磁盘 |
| `pyproject.toml` | `--cov-fail-under` 91 → **93.5**(P2 DoD 验收动作) |

验收 DoD 对照: TOTAL ≥ 94.8%(**99.42%**)✓ / 阈值抬 93.5 且绿 ✓ / 基线切片 ✓ / 红验 ≥10%(**6 例 = 15.8%, 5 杀 1 等价**)✓ / install 侧不写真实注册表(hermetic 守阵全绿, 注册表一律 `FakeRegistry`)✓ / 豁免仍 1 行 ✓。
