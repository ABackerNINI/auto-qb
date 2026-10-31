# 1666 collected / 1665 passed + 1 skipped —— 种子页表头「ETA」改「剩余时间」

> 摘要: 单文件一行 `label`(列 key 仍 `eta` —— 列宽/显隐/顺序按 key 存, 改文案不动既有偏好, 不升 `COLS_STORE_KEY` 版本); 数字为**合并工作树重测**(含并行入库的 versioning / button / settings / hr-popup 四线, 本线在其上 ±0 条 —— 纯前端文案, 未增删用例)
> 基线时间: 2026-09-26 08:40

(同步路径: `git stash -u` → ff 合并远端 7 提交至 `08b2a63` → `stash pop`, 无冲突; 合并前先 `cp -a .git` 备份。)

- **±0 条**: `shared/app.js` 的 `TORRENT_COLUMNS` 里 `{ key: "eta" }` 的 `label: "ETA"` → `"剩余时间"`, 段首注释的默认可见列清单同口径。atlas / prism 两套 UI 共用 `shared/app.js`, 一处生效。
- **列宽 `tpl` 未动**: 真浏览器量到种子页第 10 列表头 = 「剩余时间」, 84px 且 `scrollWidth == clientWidth` ⇒ 不截断(表头 11px 等宽字 + 4 汉字 ≈ 46px + 右内边距 10px + 排序箭头)。
- **未动**: `shared/drawer.js:461` 详情抽屉 General 分组另有一条 `label: "ETA"`(用户只说"种子页"); `progress/implemented-webui.md` 已贴 cap, 本轮未加条目。
- 口径回写: `modules/webui-static-contract.md` 与 `checklists/manual-walkthrough.md` 的「时长列(做种时长/活跃时间/ETA)」→ 标出「剩余时间[原 ETA 表头, 列 key 仍 eta]」。
- ⚠ 本轮**未建 `activeContext/` 切片**: 该目录已在守卫上限(40 张, `SLICE_COUNT_LIMIT`), 加一张即红 —— 记录并入本切片。目录该整理(蒸馏进 `progress/` / 任务档案)属既有事实, 不在本轮范围。

TOTAL **92%**(11211 语句 / 783 未覆盖 / 3692 分支 / 331 partial)。
浏览器冒烟: harness 桩(`--port 8107`, 默认 8099 被上一轮遗留服务占着) + playwright, **96 项 / 失败 0**; 表头实测见上(atlas 与 prism 同值)。
