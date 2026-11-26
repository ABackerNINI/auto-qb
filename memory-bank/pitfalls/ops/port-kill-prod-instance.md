# 按端口强杀前不核实进程身份 —— dev 桩杀掉了生产实例

> 摘要: 起 dev 桩时 18788(生产发现端点默认端口)绑不上, netstat 看到陌生 pid LISTENING, **没查它是什么程序**就跑 `commands run dev.port-kill -- 18788` 强杀 —— 杀掉的是用户的生产 auto-qb 主程序。三条纪律: 杀进程前必须能说出 pid 对应什么程序; port_kill 只清「本次会话起过又确认残留」的进程; dev 桩不得默认占用生产端口。(2026-11-17 追加: 多 clone 并存时端口归属不能靠"我起过 dev.run"推断 —— port_kill 已加 clone 域硬闸, 非 clone 域监听 `--yes` 也拒杀。)
> 触发: 端口绑不上, WinError 10013, 端口被占, port_kill, 杀进程, dev 桩起不来, 残留清理, 生产实例, 发现端点 18788, 核实进程身份, 多 clone 并存, 误杀其它 clone, outside-repo, webui 38080, 38081, --yes 越权
**Refs:** memory-bank/issues/26-11-23-0012-bug-port-kill-gbk-mojibake.html

## 事故形态(2026-10-16, hr-ext-connect-ui S4–S6 收尾 · 验收桩启动时)

- 起扩展 UI 验收 dev 桩时 18788 绑不上(`WinError 10013`; README 排障表把它归因 Hyper-V 排除段, 实为端口有主), netstat 见陌生 pid **未核实身份**即 `commands run dev.port-kill -- 18788` 强杀 —— 杀掉的是**用户的生产 auto-qb 主程序**(真实取数通道 + 发现端点); 桩随后占用 18788, 扩展轮询实际打在桩上。误杀后已立即停桩释放端口, 生产数据未动, 是否重启生产程序等用户决定。
- 完整事故经过见任务档案 `memory-bank/tasks/26-10-16-webui-hr-ext-connect-ui.md`; 四条根因全是纪律问题, 已收进下方「判别」。

## 判别

- netstat 看到**陌生 pid** 占端口时, 第一动作是**查身份**(`Get-Process <pid>` / `tasklist` 看可执行路径与启动时间), 不是杀;
- dev 工具(port_kill / TaskStop / kill)只清理「**本次会话明确起过、且确认是残留**」的进程 —— 对任何「说不上来是什么」的 pid, 一律不杀;
- dev 桩/任何 dev 服务**不得默认占用生产端口**(18788 及生产数据端口段); 绑不上就换端口(如 28788)或报错退出, 绝不「先杀了再说」;
- **杀进程 = 高风险外部动作, 默认不做**; 要做先问用户(与 AGENTS.md「请求边界 / 保守默认」同源)。

## 处置

1. 杀任何进程前必须能一句话说出「pid X 是 <程序路径>, 本次会话 <时刻> 起的 <什么>」—— 说不出就不杀;
2. `port_kill` 使用前先 `Get-Process <pid>` 核路径; 路径不在「本次会话起的进程」范围内就停手, 把身份报给用户;
3. dev 桩(hr_ext_stub 等)默认端口改出生产段; 启动时检测到非桩监听应**拒绝启动 + 提示 pid 身份**, 不提供也不暗示「杀了就能起」;
4. 误杀已发生: 立刻停掉自己的桩释放端口 → 如实报告用户(不遮掩、不甩锅给工具) → 是否重启生产程序**等用户决定**, 不擅自代劳;
5. 教训的元层面: 「绑不上」的第一解读是「端口有主」, 不是「端口有垃圾」—— 对生产环境的一切默认解读都该往「有人在用」这边倒。

## 事故形态(2026-11-17, webui 端口误杀两个其它 clone 的生产实例 · clone 域闸加固前)

- 一个子代理在 clone2 里要起主程序, dry-run 时 webui 端口 38080/38081 绑不上 —— 实际是 **dry-run 因端口被占静默不绑定**, 但当时把「没绑上」误读成「起好了、端口是别人占的」, 又进一步把占用者误认成「自己会话起过的残留」(两个都不对: 占用的是**其它 clone 的生产实例**)。于是逐个 `commands run dev.port-kill -- 38080 --yes` / `-- 38081 --yes` —— 闸门的归属核验明明把 `auto-qb.exe` + 其它 clone 的完整路径打印了出来, **核验输出没细看就 --yes**, 杀掉 D:\Projects\auto-qb 与 D:\Projects\auto-qb-long-seeding 两个 clone 的生产 auto-qb.exe。
- 根因链三条: ①端口归属推断错误 —— 多 clone 并存工作区里, 「我起过 dev.run」不构成端口归属的证据, 本 clone 没绑上端口 ≠ 占用者是自己的残留; ②闸门是「人审」不是「机审」 —— 旧 kill_decision 只把 name/cmdline 打印给人看, python 监听直杀、非 python 靠 --yes 人工确认, 核验输出被跳过时闸门形同虚设; ③同名副本不可分辨 —— 每个 clone 的 .venv 下都有同名 `auto-qb.exe`, 只看进程名无法区分归属, 必须看 cmdline 里的完整路径。
- **坑传递要点**: 多 clone 并存时端口归属不能靠「我起过 dev.run」推断; 判断占用者是否归本 clone, 唯一判据是归属信息(cmdline 完整路径)落在**本 clone 仓库根内**。凡是「查不到归属」「归属说不上来」「归属在别的 clone」的监听, 一律不杀。
- 加固(2026-11-17): port_kill 新增 **clone 域硬闸** —— kill_decision 在 verify-failed 判空之后做 clone 域判定、先于 python/--yes 流程(纯函数 in_clone_domain: 仓库根从脚本 `__file__` 上推, 候选 cmdline 归一化[大小写/分隔符/引号壳]后做带分隔符边界的前缀匹配), **非本 clone 的监听一律拒杀, `--yes` 也不能越过**; 被拒行标 `REFUSED(outside-repo)` 并打显眼 WARNING 行(含仓库根要点), rc=1。本 clone 进程的真实形态(.venv\Scripts\python.exe / uv.exe run / .commands 的 node / .venv 下 auto-qb.exe)cmdline 全部含仓库根路径, 照旧走原流程; verify-failed(查不到归属)维持 fail-safe 拒杀(判空闸在 clone 域闸之前)。守阵见 tests/unit/test_legacy_review4_scripts.py 三个 2026-11-17 加固用例。
