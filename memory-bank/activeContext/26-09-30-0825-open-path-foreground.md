# 打开目标文件夹置前修复(首轮 · 已被 23:54 第二轮更正根因)

> 摘要: 用户报障"打开目标文件夹(资源管理器)有概率不弹出至顶层"已修复, **未提交**(等用户显式指令)。
> ⚠ **本切片的首轮处置不完整 —— 用户二次报障仍然复现**, 真根因是 ctypes x64 传参未绑签名,
> 见 [26-09-30-2354-open-path-foreground-round2.md](26-09-30-2354-open-path-foreground-round2.md)
> 与新坑 [../pitfalls/backend/ctypes-x64-argtypes.md](../pitfalls/backend/ctypes-x64-argtypes.md)。
> 根因 = Windows 前台锁: 后台进程(WebUI 端点 / 托盘线程)经 Shell 弹窗, 新窗口拿不到前台激活。
> 处置 = open_path 打开前后快照差集(CabinetWClass)找新窗口 → AttachThreadInput 借前台权限 →
> SetForegroundWindow(实现 utils._win_foreground_new_explorer / _win_force_foreground, 失败静默)。
> 顺带实测更正旧事实: 目录 pidl 也是"开父窗口选中条目"(非"打开进入"); Win11 标题带
> " - 文件资源管理器" 后缀。真机两次弹窗验收通过; test.full 1833 passed / 90%。
> 档案: 基线 testing/baselines/26-09-30-0825-open-path-foreground.md;
> 坑 pitfalls/backend/explorer-foreground.md + windows-long-path.md(打开层条目更正)。
> 最后活动: 2026-09-30 08:25
