---
name: deps-upgrade
description: '依赖版本抬升与上游版本巡检: watch 型(外部程序, 只产出兼容性分析)与 pin 型(uv.lock 可 bump)二分管理, 三特殊依赖(qBittorrent/libtorrent/qbittorrent-api)联合分析, 检测与决策分离。USE FOR: 用户说"巡检依赖更新"/"查查上游有没有新版本"/"升级/抬升某依赖"/"qB 新版本出了要不要跟" 时; 依赖巡检结果出来后决定 bump 还是入池时。DO NOT USE FOR: 普通功能开发、与依赖版本无关的 bug 修复、新依赖选型引入(那是计划/架构决策)。'
user-invocable: true
---

# deps-upgrade:依赖版本抬升

源自 qB 5.3 升级分析(报告 `memory-bank/reports/26-10-31-0548-report-qb-5-3-upgrade-impact.html`)固化的可复用流程。**架构 = 检测与决策分离**(借鉴 Renovate automerge 判定链 / uv 显式升级纪律):检测脚本只读、无状态、产出报告;一切写动作(改 pin、bump、提交)都发生在决策之后。

## 何时用 / 何时不用

| 用 | 不用 |
|---|---|
| 常规依赖巡检("看看有什么更新") | 计划内本来就要做的功能开发 |
| 某依赖出了新版本, 评估跟不跟 | 新依赖的选型与引入(架构决策) |
| 三特殊依赖任一有更新, 做联合分析 | 与版本无关的 bug(bug 就是 bug, 不靠升级治) |
| 巡检后按分档表决定 bump / 入池 | |

## 依赖二分(本 skill 的第一判定)

读 `project/deps.toml` 获取本项目事实;通用定义:

- **watch 型**:外部目标程序(本项目=qBittorrent、libtorrent)。不进 uv.lock、**无 bump 动作**;上游更新只产出兼容性分析/issue。按分支线分开报(stable vs dev)。
- **pin 型**:进 uv.lock 的全部依赖(含 qbittorrent-api、filelock 等普通依赖),可 bump:改 `pyproject.toml` 的 `==` pin → `env.sync`。
- **三特殊联动**:`project/deps.toml` `[joint]` 列出的依赖(qbittorrent / libtorrent / qbittorrent-api)**任何一者有更新都要联合分析**——一个的升级影响另两个的适配。runbook 在 `project/impact-map.md` §3。

## 流程

**第 0 步(开工,硬性)**:`commands run my-commit-flow.sync`,结果行贴进回复;落后分支禁止开工。
**请求边界(硬性)**:本轮是问答/巡检 → 只出报告不改文件。**bump 不等于 commit**:green 档的 bump 也只改 pyproject/uv.lock + 跑测试,commit/push 必须等用户显式指令("提交/入库/推上去")。四类动作(新建文件/入池/认领/commit push)逐项显式确认,不引用旧授权。

**第 1 步:检测(纯只读)**

```bash
uv run python .agents/skills/deps-upgrade/scripts/check_updates.py           # 全量
uv run python .agents/skills/deps-upgrade/scripts/check_updates.py --quick   # 只查三特殊依赖
```

输出 markdown(stdout):watch 型按分支线报最新 tag/发布时间;pin 型从 `uv.lock` 读当前钉定版、PyPI 查最新,列「当前→最新」+ 版本线 + 是否已支持(对照 `deps.toml` 支持矩阵)。单源失败标 `[unreachable]` 不炸整体。**脚本无缓存无 state,不写任何文件。**

**第 2 步:判定更新性质**

1. pin 型且不在 `[joint]` → 按分档表走。
2. pin 型且在 `[joint]`(qbittorrent-api),或 watch 型有未分析版本(报告标 `NEW vs matrix`)→ **联合分析**(`project/impact-map.md` §3 四工位 runbook),分析完成前不做任何 bump。
3. watch 型常规更新 → 第 3 步 watch 行。

**第 3 步:决策分档表**(借鉴 Renovate automerge checklist,四条件全绿才自动)

| 档 | 条件 | 动作 |
|---|---|---|
| **🟢 零码改动,直接 bump** | 四条件全绿:①`commands run test.full` 绿 ②更新类型在白名单(`deps.toml` `bump_whitelist`) ③非 0.x / 非 major(0.x 的 minor 当 major,major 一律降档) ④无 deprecated 警告恶化 | 改 `pyproject.toml` pin → `commands run env.sync` → 复跑 `test.full`;测试红→**回滚 bump** 转人工。**commit/push 等用户显式指令**。零码 bump 不建进展件,收尾 `kb.wrap` 切片 R 行记录 |
| **🟡 涉码改动** | 任一绿条件不满足 / 升级需要改本项目代码 | 入池 issue(create-issue skill)等人工确认认领;不自行 bump |
| **🔵 新能力/优化可利用** | 升级带来可选改进(如新端点合并请求、性能修正) | 巡检结果里报告,可入便签 issue;**特性检测优先于抬版本下界** |
| **watch 型** | 外部程序有更新 | 只产出分析:轻量=切片 R 行;**跨大版本首次适配=正式报告**(`kb.new report`,口径见 `project/impact-map.md` §5) |

**第 4 步:执行与收尾**

- 🟢 bump:一次只动一个包(uv 锁粘性,diff 最小,回滚=revert 一个变更单元);升级后新基线数字走 `kb.baseline` 切片口径。
- 记录与矩阵回写:分析完成的新 stable/rc 版本补进 `deps.toml` `[[support]]`(带报告锚点);`impact-map.md` 的事实层变化(新调用点/新坑)一并回写。
- 支持矩阵口径:**alpha/beta 只跟踪不承诺,rc+stable 才入矩阵**。最终目的=支持 qB v5.2.3 及之后所有版本 → 新能力=加探测项(字段存在性/响应双形态),**不是抬版本下界**。
- 收尾按 memory-bank skill 5 步 DoD。

## project/ 目录(移植边界)

**凡本项目具体事实一律在 `project/`,SKILL.md 只留通用流程**。移植到其它项目 = 只替换 `project/`:

- `deps.toml`:watch 条目(上游 repo/分支线/tag 过滤)+ pin 扫描开关与豁免 + `[joint]` 联动清单 + `[[support]]` 支持矩阵锚点(检测脚本的数据源,改这里不改脚本)。
- `impact-map.md`:依赖盘点 / 影响面指要(写路径引用,不整抄)/ 联合分析 runbook / 本仓库 task id / 报告与 issue 落盘口径。

`scripts/check_updates.py` 移植时零改动:Python 标准库 only,不引入新依赖,自身禁 emoji 纯 ASCII。
