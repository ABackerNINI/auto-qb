# Linux CI 4 条红: 签名表实参求值早于 windll 安全网(infra-win-dll-sig-order)

> 摘要: 用户贴来 CI 红(4 failed, 全部 `AttributeError: module 'ctypes' has no attribute 'WINFUNCTYPE'`)。真根因不在用例: 上一轮 infra dup-code 重构把 `_win_user32` 的签名表构造搬到了**实参位**(`_win_dll("user32", _WIN_USER32_SIGNATURES())`)—— Python 先求值实参, 于是构造里的 `ctypes.WINFUNCTYPE`(POSIX 不存在)在 `ctypes.windll` 探测**之前**就抛, "取不到返回 None" 这层安全网成了死代码(该重构自称"行为逐字不变", 实际改了行为)。修法: 签名表改**工厂**传参(`sigs_of`), 构造推到探测成功之后; 新增两平台守阵 `test_win_dll_missing_windll_returns_none`(红验报错与 CI 逐字一致)。
> 最后活动: 2026-10-13 09:33

## 已完成(迁出见 progress)

- **源** `src/auto_qb/infra/utils.py`: `_win_dll(name, sigs)` → `_win_dll(name, sigs_of)`(签名清单**工厂**), 两调用点去括号; docstring 补"别顺手改回传现成元组"警示(含求值时机理由)。
- **测试** `tests/test_utils.py`: 新增守阵 `test_win_dll_missing_windll_returns_none` —— **两平台**都删掉 `ctypes.windll` + `ctypes.WINFUNCTYPE` 造出 POSIX 等价形态, 断言 `_win_user32` / `_win_kernel32` 返回 None 不抛错; 同步文件头「## 测试计划」清单。
- **坑档** `pitfalls/backend/ctypes-x64-argtypes.md` 新增「签名表的构造别写在实参位」节: 含"缺的是环境的还是契约的"判别(与前一条 `_shim_posix_ctypes` 处置的分界)、泛化(实参位/默认值/装饰器参数/模块级常量都会把求值挪到安全网之外)。
- **验证**: Windows `test.full` 全绿; Linux 容器 `test.linux` 全绿(CI 那 4 条: 3 条转 pass、`test_win_user32_binds_signatures` 按契约转 skip), 两侧数字见 `kb.baseline`。
- **未立档**: 单会话 1 轮指令 / 改 2 文件, 未达立档阈值, 只记本切片。

## 待办 / 移交

- `pitfalls/testing/patching.md` 已到 10,086 字符(角色 cap 12,000)—— 本次新坑**未**写进去(会当场造出 cap 债务), 改落同族的 `pitfalls/backend/ctypes-x64-argtypes.md`; 将来若这两份再长, 该按「触顶外迁 `attachments/`」处置。
