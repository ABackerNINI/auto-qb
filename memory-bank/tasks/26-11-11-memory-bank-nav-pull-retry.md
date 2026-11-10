# 26-11-11-memory-bank-nav-pull-retry — kb.nav 拉取按钮 git 层有界重试

**Status:** In Progress
**Added:** 2026-11-11
**Updated:** 2026-11-11
**Summary:** nav 拉取按钮 git 层加 20s 超时+3 次有界重试(移植 my-commit-flow 三档判据), Gitee 抖动首拉失败同请求自愈; 评审 2 面 2 轮修 5 条(1 major 挂死), 全绿
**Topics:** memory-bank-nav-pull-retry

## 本篇只回答

kb.nav 顶栏「拉取」按钮(POST /api/pull)的网络容错为什么这么设计、怎么实现的 —— 判据单点与坑在哪, 换口径前先读这篇。

## 原始请求

1. 「kb.nav 同步时采用 3 次重试, 参考 my-commit-flow.sync, 错误尽量自动处理」
2. 「注: gitee 经常抖动, 首次 pull 失败」

## 思考过程与决策

- **口径移植不造新轮**: 重试判据整体照搬 `.commands/my-commit-flow/scripts/_pipeline.py` 的「单次超时 + 有界重试」三档(网络子命令失败即重试 / 非幂等本地写只给超时 / 只读救超时与瞬时签名), 单点复制不 import(commands 包是 .commands 私产, memory-bank skill 零新依赖); 集合与 _pipeline 保持同源(含 pull —— 它非幂等但本服务从不调用, 同源的代价, 注释已注明)。
- **单次超时 60→20s**: 同 _pipeline 2026-10-06 的理由 —— Gitee 间歇卡住时 60s 只够等出一次失败, 20s + 重试才能在同一请求里自愈; 最坏 3 次 ≈63s 仍有界。
- **仅快进红线不动**: my-commit-flow.sync 的自动 rebase 不搬 —— 那是会话开工动作, 拉取按钮保守口径(分叉/重叠一律失败交人)是既有设计, 不因重试改变。
- **评审修 major(1 条)**: 首版 `_git_once` 用裸 `subprocess.run(timeout=)`, 评审指出 Windows 上只 kill 直属进程、孙进程(git-remote-https)继承管道句柄令 communicate 永久挂住且请求线程持着 `_PULL_LOCK` —— 正是本功能动机场景的重灾区。重写为 Popen + 看门狗线程 + `_kill_tree` 定点杀树 + 弃线程兜底, 同 `_pipeline.run_capture`。**教训: 移植口径要连防御性实现一起移植, 只搬参数不搬看门狗等于没搬**。
- **其余修复**: stdin 接 DEVNULL(凭据提示不白等超时)、`_subcommand` docstring 按本版事实改写、NETWORK_SUBCOMMANDS 注释与集合对齐、补 rc=-1 哨兵码直驱测试。

## 实现计划

1. `_git` 层加有界重试: `_git_once`(Popen+看门狗) + `_retryable` 三档判据 + `retry_note`, `_git` 循环 3 次。
2. `pull_ff_only` 失败行接 retry_note(离线/快进被拒两处)。
3. 补测试 5 条 + 文件头测试计划清单; `.commands/kb/config.toml` kb.nav note 同步口径。

## 子任务状态表

| 步 | 内容 | 状态 |
|---|---|---|
| 1 | _git 层有界重试 + 看门狗杀树 + stdin DEVNULL | Done(2026-11-11) |
| 2 | pull_ff_only 失败行接 retry_note | Done(2026-11-11) |
| 3 | 测试 5 条 + 测试计划清单 + config note | Done(2026-11-11) |
| 4 | 真机验证(起服务 POST /api/pull 打真 git/真 Gitee) | Done(2026-11-11) |
| 5 | test.full + 基线切片 | Done(2026-11-11) |

## 进度日志

### R0 · 立档 (2026-11-11)

用户报 Gitee 抖动致首拉失败, 要求 3 次重试参考 my-commit-flow.sync。实现 + 分批评审(2 面派遣: 正确性 / 安全+测试缺口)5 条发现全修(1 major 看门狗挂死), 复评轮零 actionable, review.check 5/5 过检; 真机 POST /api/pull 实跑通过; test.full 全绿(见 kb.baseline)。

### R1 · 收尾补记 (2026-11-11)

过程教训(记给下轮, 勿再踩): 首轮评审发现**应在其交回当下立即跑 `review.check`** —— 本轮拖到修复后才跑, 引文锚的行已被修复改写, 只能把引文重新锚定到修复落点才过检。若早就跑, 一次校验即闭合。另外闸门预跑(ship.gate)只在首轮 pack 前做了, 复评轮 pack 前未重跑 —— skill 说复评轮不豁免, 下轮补上。

- 2026-11-11 06:59 nav 拉取按钮 git 层加 20s 超时+3 次有界重试(移植 my-commit-flow _pipeline 三档判据), Gitee 抖动首拉失败同请求自愈; 评审 2 面 2 轮修 5 条(1 major 看门狗挂死), 复评零 actionable; 真机 POST /api/pull 过; 全量绿(见 kb.baseline)
