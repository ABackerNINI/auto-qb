# 打开目标文件夹置前 · 第二轮(真根因: ctypes x64 传参)

> 摘要: 用户二次报障"资源管理器仍有概率不弹出至顶层"。首轮(26-09-30-08:25 切片)停在"前台锁 +
> AttachThreadInput + SetForegroundWindow", **真根因不在这里**: 置前链路每个
> `ctypes.windll.user32.*` 调用都没绑 `argtypes`, HWND 被按 32 位 int 传而它是指针宽度 ⇒
> `SetWindowPos` **ret=0 且 `GetLastError()` 仍为 0**(静默失败), 是否翻车取决于寄存器残留 ——
> "有概率"四个字由此而来。2026-09-30 23:54 修复完成, **未提交**(等用户显式指令)。
> 档案: 基线 testing/baselines/26-09-30-2354-open-path-foreground-round2.md;
> 坑 pitfalls/backend/ctypes-x64-argtypes.md(新)+ explorer-foreground.md(根因更正)。
> 最后活动: 2026-09-30 23:54

## 实测证据(Win11 本机, 同一窗口同一时刻, 唯一变量是有没有 argtypes)

| 调用方式 | `SetWindowPos(hwnd, HWND_TOPMOST, …)` | Z 序 index |
|---|---|---|
| 不绑 argtypes | **ret=0**, `GetLastError()`=0 | 63 → 63(纹丝不动) |
| 绑了 argtypes | ret=1 | 63 → **56**(压过占着前台的 notepad) |

推广后果: 凡取 HWND 参数的调用都吃同一套随机概率 —— `GetClassNameW`(快照可能失真)、
`GetWindowTextW`(标题取成空 ⇒ 复用窗口兜底匹配不上)、`SetForegroundWindow`(抢不到焦点)。

## 本轮改动

1. **签名绑定**(收口到单点): 新增 `_WIN_USER32_SIGNATURES()` 签名表 + `_win_bind()`, 由
   `_win_user32()` / `_win_kernel32()` 逐个绑(user32 14 个 / ole32 2 个 / kernel32 1 个);
   `_win_explorer_hwnds` 改走绑定后的句柄。先判 `is_windows()` 再取缓存 —— 否则单测 patch
   平台后会拿到真句柄。
2. **置前三层升级**, 每层独立失败静默、互不为前置条件(`_win_force_foreground`, 返回是否真取焦):
   ①Z 序 `SetWindowPos(TOPMOST→NOTOPMOST, SWP_NOACTIVATE)`(后台进程唯一必定被受理, 实测
   提升后前台仍属 notepad 而窗口已压到它之上 —— "看得见"与"抢焦点"解耦);
   ②`AttachThreadInput` 借权限 + `SetForegroundWindow`; ③`SwitchToThisWindow` 硬切兜底。
3. **找窗口双策略每轮都试**(`_win_wait_explorer`): 新窗口差集优先 + 复用窗口标题匹配 ——
   首轮把后者当 2s 超时后的**一次性兜底**, 慢于 2s 的复用导航整个漏掉, 是"仍有概率"的第二源头。
   超时 2s→5s, 找到后封顶重试 4 次(渐进间隔)。

## 验收

- `test.full` 1890 passed + 3 skipped / 91%(较 26-09-30-2253 的 1881/91 净 +9, 本轮新增 8 条用例)。
- 真机: notepad 占着前台 → 新窗口场景与**复用窗口**场景都在首个 0.25s 采样点成为前台;
  `_win_topmost_once` 单独验证 Z 序位移, 前台保持属别人 —— 分离断言正是首轮漏过的那一步。
- 遗留: 等用户在 WebUI / 托盘的日常使用中再验一轮(浏览器占着前台才是它原本的场景)。

