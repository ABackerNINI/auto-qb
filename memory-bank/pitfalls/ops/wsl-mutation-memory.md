# WSL 12 GiB 下变异池的瓶颈是单 worker RSS; 单客户端会被缺省的 vmIdleTimeout 回收

> 摘要: 12 GiB 的 WSL VM 里, 中池变异目标的并发上限由**单 worker RSS**(实测 5.2–5.8 GB)决定, 不是由 8 核决定 —— `--children 2` 合计就顶穿 11.68 GiB, 三轮都死在第 80/1804 条; 另外 2026-11-02 04:29 版 `.wslconfig` 缺 `vmIdleTimeout` 时, 单客户端在 **91±1 秒**被回收(rc=1、无 stderr、distro 仍 Running、VM 内核未重启), 显式写 `vmIdleTimeout=600000` 后同一形态活 651 s、真实任务 624 s 跑完。长跑仍必须保持一个客户端全程连着。
> 触发: WSL, 变异测试, mutmut, 内存, OOM, 并发, children, RSS, setsid, nohup, distro, 失联, 常驻会话, vmIdleTimeout, 91秒回收, 客户端被切
**Refs:** .commands/mutants/references/why.md, .commands/mutants/config.toml

### 12 GiB VM 里, 变异池的并发上限由「单 worker 体积」定, 降并发救不了

- **触发**: 在 WSL 侧跑中池目标(`only_mutate = ["**/core/modules/traffic_sample_mod.py"]`, 池 = `tests/test_traffic_sample_*.py` / `test_traffic_limits.py` / `test_traffic_store.py`, `timeout_multiplier = 15`), 并按核数直觉只把 `--max-children` 从 3 降到 2。
- **判别**: ①三轮 2 路实测(2026-11-02 06:45 / 07:01 / 07:16, 三种不同启动方式)**全部停在第 80/1804 条**, 每轮只活 52–58 秒;
  ②采样峰值 `used` 10,587–11,468 MB(MemTotal 11,961 MB)、`avail` 最低 **493 MB**; 单进程 mutmut 峰值 **5,207–5,842 MB**, 进程和 9,050–9,999 MB;
  ③内存耗尽时**内核不一定留 OOM 记录**: 这几轮 kern.log 只有 `warn_alloc`, 07:19:04 的 Mem-Info 是 `inactive_anon 2,909,454 页 ≈ 11.1 GiB`、`free 19,264 页 ≈ 75 MB`、`Node 0 Normal free 30,296 kB < min 30,540 kB`、`all_unreclaimable? no`、`Free swap=0`; `wsl.exe` 会话本身先以 **rc=1** 断连(guest 控制面失联), 进程树随之消失;
  ④对照 3 路那轮: `1759/1804`、4638.8s、峰值 ≈10.7 GiB, 最后被内核 OOM 杀掉 `pid 3578 (mutmut)`(total-vm 3.96 GB / anon-rss 3.84 GB)。2 路并不更省, 只是把同样的峰值从「一小时累积」压成「一分钟冲顶」。
- **处置**: ①**别再按核数调并发** —— 单 worker 跑完整池套件的峰值就是 5.2–5.8 GB, 2 份 + 系统 ~1.5 GB 已超 11.68 GiB; 要在这台 12 GiB 的 VM 里跑完, 只能 `--children 1`、或**按测试池拆成多轮小池**(每轮只挂 1 份 worker), 或由用户决定抬 `.wslconfig` 的 `memory`(本轮明确禁止); ②停手判据用**采样**而不是 OOM 记录: `used` 逼近 MemTotal、`avail < 1 GB` 就该停, 继续等只会等到 `wsl.exe` rc=1/0x8007274C; ③报结论时必须同时给「单进程峰值」与「进程和峰值」——前者才是决定并发上限的量。
- **守阵**: 无自动守阵(资源类)。口径记在包内 `.commands/mutants/config.toml` 的 `--max-children` 注释与 `references/why.md` 排障表。

### `vmIdleTimeout` 缺省时, 单客户端在 91±1 秒被回收

- **触发**: 2026-11-02 09:09–10:21, 用 `wsl.exe` 跑任何长命令 —— 六种启动形态(前台流式 / 工具后台任务 / Python 孙进程 / 沙箱外 / WMI 进程树外 / 静默无输出)**全部在 91±1 秒结束**: guest 实际运行约 80 秒、**rc=1**、**无 stderr**、无 `[end]`; 08:20:46 起的 `round-a` 同签名(08:22:11 停)。
- **判别**: ①客户端消失瞬间(及 +8 秒)查 `wsl -l -v`, distro 仍是 **Running** —— 不是 distro 关停;
  ②guest `uptime -s` 全程恒为 `2026-11-02 04:29:14`, 即 **VM 内核没有重启**;
  ③对照 11-01 的 R29(单次 811.3 s)与 R30(单次 1,635 s 干净收尾), 说明该行为是 **11-02 04:29 重写 `.wslconfig` 之后**才出现(该版只有 `swap=0` / `memory=12 GiB` / `autoMemoryReclaim=Gradual`, **没有 `vmIdleTimeout`**); 12 GiB 内存下 `avail` 仍在 21.5 GiB(宿主)/ 正常水位, 排除 OOM。
- **处置**: ①在 `[wsl2]` 显式写 **`vmIdleTimeout=600000`**(10 分钟)并让 VM 重启后(判据: guest `uptime -s` 晚于 `.wslconfig` 的 mtime), 同一 650 秒哨兵实测 **651 s / rc=0 / 130 tick / 有 `[end]`**;
  ②真实任务实测 `ops_mod.py` + `tests/test_ops_*.py` **1,135 变异 / 624 s / rc=0**、结果文件 334,597 B, 跨过 600 s **未被切**;
  ③**该结论与 VM 同时重启共变**(mtime 10:58:28 → `uptime -s` 10:58:37), 尚未单变量钉死 —— 要钉死需回退该键再测一次(改配置要用户授权);
  ④`vmIdleTimeout` 是 **VM 空闲**计时, **有客户端连着就不计空闲**, 所以 600000 不是硬上限; 但**必须保持一个客户端全程连着**, 否则 distro 空闲关停(见下条); 需要彻底免掉空闲关 VM 时才考虑 `-1`。
- **守阵**: 无自动守阵(环境行为)。复现与取证脚本放 WSL 家目录(`sentinel6.sh` / `short_run.sh` / `round_run.sh` / `mem_trace.py`)。

### distro 被空闲关停后 PID1 重建, VM 内核不重启

- **触发**: 想让长跑脱离工具终端 —— `setsid nohup ... &`、`Start-Process wsl.exe ... -WindowStyle Hidden`、`Invoke-CimMethod Win32_Process Create`, 或在后台任务运行期间再跑一条前台 `wsl.exe` 命令(终端复用会杀掉后台命令)。
- **判别**: ①派生进程与采样脚本在**同一秒**消失, `pgrep` 无残留, 日志停在「会话结束 + ~10–30 秒」处, **kern.log 无新 OOM**;
  ②根因看 distro 的 systemd 启动时间: `ps -o lstart= -p 1` 变化(实测 `07:08:56`、`10:58:57`、`11:58:25`), 而 `uptime -s` 仍是 VM 内核启动时间 —— **内核没重启、distro 被关停又重建**; WSL 关闭 distro 时连带杀掉所有脱离会话的进程;
  ③另一种形态是 `Wsl/Service/0x8007274C`(WSAETIMEDOUT): 内存吃紧时 `wsl.exe` 连接本身超时返回, 会话里的进程一起没了。
- **处置**: ①长跑必须让**一个 `wsl.exe` 客户端全程保持连接**(前台阻塞, 或工具的后台任务且期间不跑任何前台 shell 命令); ②需要看进度时用**文件读取**(`\\wsl$\<distro>\home\<user>\...`)而不是再开 `wsl.exe` 命令; ③即使已设 `vmIdleTimeout=600000`, 这条仍成立 —— 客户端断开后 distro 照样空闲关停, 只是 91±1 秒那类「有客户端也切」的形态已消失。
- **守阵**: 无自动守阵(环境行为)。采样脚本与运行日志放 WSL 家目录而不是 `/tmp`(distro 重启后 `/tmp` 清空, 实测两次丢日志)。

**复发**: 0
