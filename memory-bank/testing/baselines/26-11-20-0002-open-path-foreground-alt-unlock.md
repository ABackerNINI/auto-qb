# 6488 passed + 6 skipped —— 置前四层修复后全量基线

> 摘要: 置前四层修复后全量基线
> 基线时间: 2026-11-20 00:02

## 验收数字

实测树: develop tip `da64220d` + 本批工作树(修复 + 评审修复 + 回写, 随本专题入库)。`commands run test.full` 实测(2026-11-20 00:0x, 184.7s):

```
TOTAL                                                28929     44  10326     61    99%
6488 passed, 6 skipped, 7 warnings in 184.72s (0:03:04)
```

与上一条切片(26-11-19-2333, 6486P/6S)对比: +2 passed —— 本批新增 `test_win_alt_unlock_foreground_contract` 与 `test_win_force_foreground_alt_layer_before_hard_switch` 两条; 覆盖率门槛 99.5% 达标(实测 99% 为展示取整, 输出行 `Required test coverage of 99.5% reached`)。

## 本改动面

- `src/auto_qb/infra/utils.py`: 置前链路升级四层 —— `_WIN_USER32_SIGNATURES` 补 `keybd_event` 绑定(第4参 dwExtraInfo 是 ULONG_PTR, 按 `c_void_p` 指针宽度绑); 新增 `_win_alt_unlock_foreground`(合成一次裸 ALT 按下-抬起解锁前台锁后重试 SetForegroundWindow, 真拿到前台才 True, 缺导出/user32 缺席静默 False); `_win_force_foreground` 在「借权限」与「硬切兜底」之间插入该层, docstring 三层→四层。
- `tests/test_utils_windows.py`: `_P1FakeUser32` 补 `keybd_event` 记账替身; 新增 `test_win_alt_unlock_foreground_contract`(键击成对/顺序 + SFG 恰一次重试 + 前台恒为他人 False + 缺导出/缺席静默)与 `test_win_force_foreground_alt_layer_before_hard_switch`(借权限被拒 → ALT 解锁成功 → 不走硬切); matrix 测试 docstring 三层→四层 + 补注; 头部测试计划同步 3 条目。
- KB: 坑档 `pitfalls/backend/explorer-foreground.md` 第三轮真机取证改写(焦点层判别 GetGUIThreadInfo / 处置四层 / 真机验收改 schtasks 冷后台 + 双断言); `pitfalls/testing/tmpdir.md` 复发 11(直跑 pytest 与 ship.gate 预跑两处 rc=4); `_index-1.md` 等生成物 `kb.index` 重建; 基线切片本件。
- 真机轨已做: 本功能属"必须碰真进程/窗口"一类 —— schtasks 起冷后台进程(父进程 svchost, 无前台权限)实调 `open_path`, 修复前前台整整 6s 拿不到(键盘焦点留在 ZCode), 修复后 0.5s 内拿到前台且 `GetGUIThreadInfo().hwndFocus` 1s 内落进 Shell 视图(`DirectUIHWND`)并稳定; 诊断脚本与临时窗口全部清理。
