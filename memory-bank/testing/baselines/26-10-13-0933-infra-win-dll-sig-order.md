# 3193 —— 修 Linux CI 红: 签名表实参求值早于 windll 安全网

> 摘要: 用户贴来 CI 红 4 条(全 `AttributeError: module 'ctypes' has no attribute 'WINFUNCTYPE'`, 本机 Windows 全绿)。真根因是上一轮 infra dup-code 重构把 `_win_user32` 的签名表构造搬到**实参位**(`_win_dll("user32", _WIN_USER32_SIGNATURES())`)—— Python 先求值实参, `ctypes.WINFUNCTYPE`(POSIX 不存在)在 `ctypes.windll` 探测**之前**就抛, "取不到返回 None" 的安全网成死代码。修法: `_win_dll(name, sigs_of)` 改收签名清单**工厂**, 构造推到探测成功之后; 新增两平台守阵 `test_win_dll_missing_windll_returns_none`(红验报错与 CI 逐字一致)。**两侧都重测**(平台相关改动): Windows 全绿 / Linux 容器全绿, CI 那 4 条 3 转 pass + 1 转 skip(该条契约本就是 None)。
> 基线时间: 2026-10-13 09:33

## 验收数字

- **Windows** `test.full`: **3193 passed + 4 skipped** / `TOTAL 16785 157 5720 140 99%`; 耗时 **51.6s**(本机并行默认, 单次采样)。
- **Linux 容器** `test.linux`(python3.12-bookworm-slim): **3191 passed + 6 skipped / 0 failed** / `TOTAL 16785 168 5720 143 99%`(Required 98% reached, 实际 98.59%); 耗时 **60.3s**。
- 两侧收集面同(16785 语句 / 5720 分支), skipped 差 2 = Windows 专属用例在 POSIX 上 skip。
- 较上基线看差值: `commands run kb.baseline -n 2`。

## 本改动面

- **源**: `src/auto_qb/infra/utils.py` —— `_win_dll(name, sigs)` → `_win_dll(name, sigs_of)`(参数改签名清单工厂, 循环内 `sigs_of()`); 两调用点 `_win_dll("user32", _WIN_USER32_SIGNATURES)` / `("kernel32", _WIN_KERNEL32_SIGNATURES)` 去括号; docstring 补求值时机警示。行为面: Windows 逐字不变(探测成功后才构造, 结果同); POSIX 恢复"返回 None"契约。
- **测试**: `tests/test_utils.py` 新增 `test_win_dll_missing_windll_returns_none` + 文件头「## 测试计划」清单一行。
- **文档**: `pitfalls/backend/ctypes-x64-argtypes.md`(新节) · activeContext 切片 `26-10-13-0933-infra-win-dll-sig-order.md` · 本基线切片 · `kb.index` 生成物重建。

## 已知偏差 / 移交

- **修法选择**: 备选是"给这 4 条用例补 `_shim_posix_ctypes`"(即 `pitfalls/testing/patching.md` 记录的旧处置, 生产代码零改动)。**未采用** —— 该处置针对"用例要跑 Windows 分支而 POSIX 无门面", 缺门面不是被测代码的缺陷; 本条相反, "取不到返回 None" 是被测代码的契约(`test_win_user32_binds_signatures` 的 `pytest.skip("非 Windows 宿主…")` 分支就是契约的书面证据), 补门面只把契约破裂盖住。判别法与泛化已写进坑档。
- **新坑落点偏离默认**: 该坑按主题本应进 `pitfalls/testing/patching.md`(Linux CI 平台差异), 但它已 10,086/12,000 字符, 写进去当场造出 cap 债务 ⇒ 落同族 `pitfalls/backend/ctypes-x64-argtypes.md`(2,105 → 约 4,300 字符)。
