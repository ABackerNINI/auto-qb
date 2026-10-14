# 3209 — webui 跨层常量守阵补齐(cross-layer-constant 批次)执行基线

**Refs:** memory-bank/tasks/26-10-11-webui-dup-code-fixes.md

> 摘要: 用户「认领并修复」`26-10-11-0310-refactor-webui-cross-layer-constant-convention-dup`(webui dup-code 轮当期三条延后项之一的跨层常量批次) → 走 issue 建议第一支「保持守阵 + 补全机械比对」(未触前端构建面): 四组常量对中 ② REANNOUNCE 已有逐项守阵不动; ① 补 STATE_RANK_LAST↔_SHOW_STATE_RANK_LAST 比对(views.py 表外兜底秩提为命名常量); ③ 新增 ETA 哨兵全静态树扫描(_ETA_SENTINEL ↔ format.js + 3 处 tpl 比较点, 零命中即红); ④ 新增键位正则跨层逐字比对(_KEYS_SERIAL_RE ↔ KB_DEF_RE), 并消 test_web_shortcuts.py 第三份手抄(改导入后端单点)。三条新守阵全部过红验(值漂移/声明缺失/零命中三类突变)+ 3 个活性探针; 全量 3209 passed + 4 skipped / 99%。
> 基线时间: 2026-10-15 04:50

上一基线: memory-bank/testing/baselines/26-10-15-0423-notify-tray-icon-path-dup.md

## 验收数字

- `test.full`: **3209 passed + 4 skipped, 0 failed** / 覆盖率 `TOTAL 16840 162 5724 143 99%`(过 98% 闸门)。
- 耗时: pytest 151.72s(单次采样, 全绿跑; 口径见 baseline.md)。
- 单文件前置跑: `test.one tests/test_webui_static_skins.py tests/test_web_shortcuts.py` 50 passed(改完先跑两个守阵文件绿再收口)。
- 红验(守阵活性, 逐项突变后判红再还原): format.js 哨兵 8640000→8640001 判红(报出文件行号); shortcuts.js KB_DEF_RE `[A-Z]`→`[A-Za-z]` 判红(两侧正则源对照); app.js STATE_RANK_LAST 9→8 判红(两侧兜底秩对照); 3 个活性探针(ETA 零命中 / KB_DEF_RE 声明缺失 / STATE_RANK_LAST 声明缺失)均报红 —— "没扫到"与"没违规"可区分(坑档 guard-dead-branch 口径)。
- Linux 侧未重测(改动为纯测试守阵 + 常量命名化 + 注释, 零行为变化, 无平台分支)。

## 本波改动面

- **常量命名单点**: `src/auto_qb/webui/views.py` 新增 `_SHOW_STATE_RANK_LAST = 9`(表外 kind 兜底秩, 原为 `.get(k, 9)` 裸字面量), 集行聚合处改引命名常量; `_ETA_SENTINEL` 注释补守阵指针。
- **守阵补齐**(全在既有文件, 未新建测试文件): `tests/test_webui_static_skins.py` — `_scan_state_rank` 扩展 STATE_RANK_LAST 比对; 新增 `_scan_eta_sentinel`(全静态树 .js/.html 除 vendor 扫 `sec/eta >= <数>` 比较点, 逐个对 `_ETA_SENTINEL`, 零命中即红)与 `_scan_keys_serial_re`(bundle 内 KB_DEF_RE 字面量剥定界符与 `_KEYS_SERIAL_RE.pattern` 逐字比对); 注册进 `_scan_frontend_assets` 并同步其文档字符串与文件头测试计划清单。
- **消第三份表示**: `tests/test_web_shortcuts.py` 手抄的 `KB_DEF_RE` 正则改 `from auto_qb.webui.server.routes.keys import _KEYS_SERIAL_RE as KB_DEF_RE`(单一事实源在后端)。
- **注释指针**: `src/auto_qb/webui/server/routes/keys.py` 与 `src/auto_qb/webui/static/shared/shortcuts.js` 的"改一边必须改另一边"注释补守阵位置(shortcuts.js 注释未引入 `*/` 序列, 守阵自身 node 语法校验过)。
- **回写**: 任务档案 `26-10-11-webui-dup-code-fixes` R2 续轮段(Summary/子任务表/未做项出账/Refs/进度日志) + activeContext 切片新建 + issue 置 Done(两处徽标+meta + doc-refs 认领链 + 实际修法/验证方式) + `kb.index` 重建 + 本基线切片。

## 已知偏差 / 移交

- issue 入池时记的"ETA 哨兵 4 处 tpl"复验为 3 处 —— 系 26-10-11-1722 计划明细单元格收敛(4 份行模型渲染器 → 单份 `<aq-member-cells>`)所致, 非漂移; 守阵按全树扫描不硬编码文件表, 该变化自动适配。
- 建议的第二支「后端出常量 + 前端构建期注入」未走(触前端构建面, 收益中/风险中) —— 本轮把机械守阵补全后漂移可即刻判红, 构建期注入留待真有第二处跨层常量增长时再评估; 已在 issue「与建议修法改道原因」段留痕。
- 移交: webui dup-code 池内另两条延后项(`partial-publish-merge` 热路径 / `route-cmd-boilerplate` 表驱动)仍 `Open` 未动。
