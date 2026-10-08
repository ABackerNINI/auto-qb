# 沙箱内 yapf 挂住/刷磁盘 (deps 工具链)

> 摘要: 用户报「yapf 挂住, 一直占高 CPU, 且一直写磁盘」。取证: yapf **import 期**就要把语法 pickle 写进 <code>%LOCALAPPDATA%\Google\YAPF\Cache\0.43.0</code>(platformdirs 的 Win32 已知文件夹 API 决定, <b>环境变量改不动</b>), 该目录不在 agent 工具 shell 沙箱白名单 ⇒ 写入被拒; 又因目录<b>已存在</b>, CPython <code>tempfile._mkstemp_inner</code> 把 Windows 上的 <code>PermissionError</code> 当"重名"⇒ 最多 10000 次紧循环 ⇒ 挂住 + 100% 单核 + 刷磁盘 + 漏临时文件(6 周 2574 个 / 22MB, 最终缓存从未落成)。三处修复: ①<code>run.py::_shell</code> 超时改杀<b>整棵进程树</b>(旧 <code>subprocess.run(timeout=)</code> 只杀 cmd.exe, 把 yapf 留成孤儿继续烧); ②<code>dev.fmt</code> 改用<b>项目内</b> yapf(<code>uv run yapf</code>, dev 依赖钉 0.43.0) + timeout 60s; ③fmt gate timeout 120→60(保留 auto=true)。<b>口径修正</b>: 收尾复测时沙箱内 yapf 多数时候 &lt;1s 正常返回 ⇒ 挂死是<b>间歇</b>的, 故不降级闸门, 只做"短超时 + 整树 kill"兜底。残留: 缓存目录清理与"白名单放行"需用户侧做(agent 删这些路径同样被拒)。坑档 [sandbox-tool-cache](../pitfalls/testing/sandbox-tool-cache.md)。
>
> 最后活动: 2026-10-08 15:39

**Refs:** memory-bank/tasks/26-10-08-deps-sandbox-yapf-hang.md

## 正在进行

- 四方向已落地(S1–S5); <b>S6 残留交用户侧</b>: ①在**无沙箱**终端删掉 <code>%LOCALAPPDATA%\Google\YAPF\Cache\0.43.0</code>(agent 侧删除被拒) —— 目录<b>不能留</b>, 留着就会触发紧循环; ②彻底消除 = 把它加进沙箱白名单。档案 [26-10-08-deps-sandbox-yapf-hang](../tasks/26-10-08-deps-sandbox-yapf-hang.md)。

## 本轮完成

- 引擎: <code>run.py</code> 新增 <code>_kill_tree</code>, <code>_shell</code> 改 Popen + 超时杀<b>整棵树</b>再收尸、照旧上抛 <code>TimeoutExpired</code>; 守阵 <code>test_engine.py::test_shell_kills_process_tree_on_timeout</code>(<b>红验</b>: 抽掉 kill 行即红 → 还原复绿)。
- 工具: <code>pyproject.toml</code> dev 组加 <code>yapf==0.43.0</code>(uv.lock 随之更新) + <code>env.sync</code>; <code>dev.fmt</code> → <code>uv run yapf -i &lt;args&gt;</code>, timeout 300→60。
- 闸门: fmt gate timeout 120→60, 保留 <code>auto = true</code>(注释写明判据与"彻底消除"条件)。
- 坑档: <code>pitfalls/testing/sandbox-tool-cache.md</code>(触发/判别/处置 + 五步判别法 + 复发=1)。
- 取证方法沉淀(可复用): <code>faulthandler.dump_traceback_later(N, exit=True)</code> 抓烧 CPU 进程的 Python 栈; "同命令关沙箱跑立刻成功"的对照实验切开工具 bug 与沙箱约束。