# 工具数据默认落进仓库内工具目录: 不 ignore 就把运行态写进 git status

> 摘要: 把工具的默认数据目录从用户级改到「安装目录/data」(因为自启/被拉起时 cwd 不可信)后, 源码态的 data_dir 就落在**仓库内** —— 不补 .gitignore, 工具一跑 `git status` 就脏, 提交闸门会把 history_traffic.dat / 临时物当成改动。
> 等级: L0
> 触发: git status, 运行期数据, data/, run/, .gitignore, 树脏, 工具数据目录, 误提交

### 运行期数据默认落仓库内时, 忽略项是提交纪律的一部分

- **触发**: 给随仓工具定「数据默认落 `<工具安装目录>/data`」(计划 26-10-17-0339 D12), 源码态即
  `tools/global-traffic-monitor/data/`; 工具还会写 `run/` 等临时物。改默认落点的那一步若只改代码
  不补 `.gitignore`, 当场就把运行态引进版本库。
- **判别**: ①工具跑过一次后 `git status` 出现未跟踪的 `data/history_traffic.dat` /
  `state.json` / `monitor.token`; ②`ship.commit` 的暂存清单里混进运行期文件(它按整索引提交,
  暂存了什么就落什么); ③本仓「树脏即停」的同步/推送流程被运行态卡住。
- **处置**: ①`.gitignore` 增 `tools/global-traffic-monitor/data/` 与 `tools/global-traffic-monitor/run/`
  (目录尾斜杠, 只忽略目录不误伤同名文件); ②改默认落点与补忽略项放**同一笔**提交, 别留给后人;
  ③别用 `git add -A` / `git add .` 兜底 —— 一旦运行态已在树上, 会连带入库。
- **守阵**: `tests/test_traffic_source_agent.py::test_tool_runtime_dirs_are_gitignored`(读 .gitignore
  文本断言两条忽略项在场; 不起 git 进程 —— `tests/sidefx.py` 的 POPEN 白名单不放行)
- **复发**: 0 (复踩时在此行追加「+N (日期): 为什么没命中」, 无复发可删本行)
