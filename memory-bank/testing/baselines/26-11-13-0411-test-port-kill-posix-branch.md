# 6075 —— 6075 passed + 19 skipped(env3 Linux, TZ 参考时区) —— port_kill/e2e_selfcheck POSIX 双支修复批次

> 摘要: 6075 passed + 19 skipped(env3 Linux, TZ 参考时区) —— port_kill/e2e_selfcheck POSIX 双支修复批次
> 基线时间: 2026-11-13 04:11

## 验收数字

```text
TOTAL                                                27113     219   9480     89    99%
6075 passed, 19 skipped in 115.40s (0:01:55)
```

(实测时点: 修复 + 评审分面 3 派遣 + 复评 2 轮 8 发现全修后收尾 `commands run test.full` 2026-11-13; 宿主 env3 原生 Linux(Ubuntu 24.04), 带 `TZ=Asia/Shanghai`(参考时区) 与 `PATH=$HOME/.local/node/bin:$PATH`(node 电池前置, 见坑档 env3-test-run-prereqs) —— 未带时该机 TZ 敏感存量用例(26-11-12-2347 已入池)与 node 电池族是既有红, 与本批无关; 上一切片 26-11-13-0344 在 Windows 根宿主 6084+2, 本切片 6075+19: 差值 = 本批 +8 守阵用例 +2 既有 skip 面(平台跳过形态), 零回归)

## 本改动面

- **`scripts/port_kill.py`**: 查询两函数(listening_pids/process_info)按 `os.name` 双支, nt 支逐字节保留; POSIX 支 /proc 直读零外部依赖(_listening_pids_posix: /proc/net/tcp{,6} Listen 态 inode -> /proc/*/fd socket 反查; _process_info_posix: comm/cmdline, NUL 拼空格); 实杀收进 _kill_pid 单点(nt=taskkill /F /PID 原样 / posix=os.kill SIGKILL, ProcessLookupError/PermissionError 落 kill-failed); 模块常量 PROC_ROOT(守阵假树注入)与 _SIGKILL(getattr 兜 9, Windows CPython 无该属性)。
- **`scripts/e2e_selfcheck.py`**: _proc_info 收编进 port_kill.process_info 单点(第三处 powershell 位移除); CLONE_HINT_RE 扩 posix 绝对路径形态; 摘要统一截 160。
- **`tests/test_legacy_review4_scripts.py`**: 既有 4 条旧用例(3 main 接线 + 1 process_info 解析)补 `os.name="nt"` 钉(任一平台跑 nt 支); 新增 8 条 -- posix /proc 全链解析与反查(含 TIME_WAIT/别 inode 不误报/tcp6)、posix 归属(comm/cmdline/缺席 fail-safe/posix 名形态过闸)、posix main 接线(SIGKILL/拒杀/--yes/verify-failure)、posix 实杀失败面(ProcessLookupError/PermissionError)、nt 实杀失败面(taskkill rc!=0)、nt listening 解析钉(含 -State Listen 过滤)、_proc_info 收编静态钉(e2e_selfcheck 无 powershell/Win32_Process 字面量)、_check_port 归属显示链行为钉(blocking/warn 分流); 测试计划清单同步。
- **文档面**: issue 26-11-13-0234 翻 Done(复验 + 修复后补充); 坑档 ci-only-guard.md 追加复发 +2(SIGKILL 镜像向: nt 宿主钉桩激活 POSIX 支引用 signal.SIGKILL) + 新档 env3-test-run-prereqs.md(env3 测试前置: node PATH 会话级 + TZ 参考时区) + `kb.index` 再生; 会话切片 26-11-13-0409; 档案 26-11-13-test-port-kill-posix-branch。
