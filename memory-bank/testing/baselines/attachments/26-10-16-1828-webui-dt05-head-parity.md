# 3483 passed + 4 skipped —— 05 面列头与值格错位修复(几何变量同源)

> 摘要: GitHub CI 的 e2e 几何守阵在 05 健康分组面判红(列头首格比行内容根右移 14px, prism/atlas 一致): 承接 `9b7ec767` 的 05 外壳接线修复 —— 内层 `.dt05-list` 补上后, 变体六条 `.group-row` 版式规则由空转转为生效, 行的横向内距从皮肤默认 `--tbl-pad-x:14px` 变成 0, 列头留在 14px。修法 = 06/11 既定范式(变体只声明变量值, 列头与行同取): 行容器作用域声明 `--tbl-pad-x:0px` + 行内距改写为读同一变量。修前两皮肤各 1 例红, 修后复绿。
> 基线时间: 2026-10-16 18:28

- test.full: 3483 passed + 4 skipped / TOTAL 17684 语句 245 未覆盖 6012 分支 180 partial / 98%(闸门过)。耗时 **193.3s**(单次采样; 口径见 baseline.md)。⚠ 同树首次采样(坑档与切片已落盘、索引未重建)有 3 条 KB 自洽红(`tests/test_memory_bank.py`: `gen_all --check` / `kb_index` 重建 / 索引与文件双向一致); `commands run kb.index` 后复绿 —— 本条为复绿后数字。
- 全量 e2e: **270 passed / 10 skipped / 0 failed**(280 例收集, 耗时 10.9m)。与 CI 逐位对齐 —— CI 报 268 passed + 2 failed(即本轮修复面) + 10 skipped; 本地修前复现同值(`leftDiff=[{i:0,d:14}]`, prism 与 atlas 各 1 条), 修后该 2 条消失。相关三份 spec(几何 / 背景族 / 05 分组)全绿 = 60 passed; 触碰层静态守阵两文件 = 62 passed(`test_webui_static_skins.py` / `test_webui_static_dom_panel.py`); `node --check` 过。
- 本改动面: `src/auto_qb/webui/static/shared/drawer_tpl/05-trackers-health-groups-low.js`(1 处: `.drawer .dt05-list { --tbl-pad-x:0px }` + 行内距 `padding:2px var(--tbl-pad-x, 0px)` + 口径注释)。语义 = 列头与行单点同源, 以后改内距只动一处。
- 环境事实: 全量 e2e(280 例 ≈ 11 分钟)已超 `dev.e2e` 包内 600s 预算 —— 实测被引擎强杀(`[FAIL] dev.e2e 超时(600s)`); 本轮全量轮改为绕过引擎直跑。全量轮的实际入口待用户定(抬该 task timeout / 另收一条命令)。
- 知识库: 新坑 `memory-bank/pitfalls/web-ui/tbl-pad-x-single-point.md`(复发 1: 几何守阵**不在 @fast 子集**里, 这类几何回归只在全量轮露头) + 切片 `memory-bank/activeContext/26-10-16-1821-webui-dt05-head-parity.md`; 生成物 `memory-bank/pitfalls/web-ui/_index.md` 已随 `commands run kb.index` 重建。
- Linux 侧未跑 —— 改动为前端静态件(CSS 变量, 两皮肤量值一致), 无平台分支; 本条 Windows 侧数字为事实源。

## 本改动面

- `src/auto_qb/webui/static/shared/drawer_tpl/05-trackers-health-groups-low.js`: 行容器作用域新声明 `--tbl-pad-x:0px`(该面行是整宽容器、观感归内容根 `.dt05-rowin`), `.group-row` 横向内距改读同一变量, 注释写明口径与复发判据(几何守阵 + 快门禁盲区)。
- `memory-bank/pitfalls/web-ui/tbl-pad-x-single-point.md`(新) · `memory-bank/activeContext/26-10-16-1821-webui-dt05-head-parity.md`(新) · `memory-bank/pitfalls/web-ui/_index.md`(生成物, 随 kb.index 重建)。
