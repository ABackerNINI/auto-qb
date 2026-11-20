# 6493 passed + 6 skipped —— WEBUI 列风格切换 S1-S6 收口全量基线

> 摘要: WEBUI 列风格切换 S1-S6 收口全量基线
> 基线时间: 2026-11-20 08:39

## 验收数字

实测树: webui-column-style tip `4ff09f16` + 本收口批工作树(docs 回写 + 档案/计划翻 Done + 本切片, 随本专题入库)。`commands run test.full` 实测(2026-11-20 08:39, 204.4s):

```
TOTAL                                                28929     44  10326     61    99%
6493 passed, 6 skipped, 7 warnings in 204.42s (0:03:24)
```

与上一条切片(26-11-20-0002, 6488P/6S)对比: **+5 passed** —— 恰为本专题新增的 5 条 pytest 测试函数(引擎判定电池 `test_r4_prog_band_boundaries` / `test_r4_speed_band_and_num_scale` / `test_r4_unit_parts_family` / `test_r4_colstyle_engine_semantics` + 静态守阵 `test_frontend_colstyle_tpl_class_css_paired`; e2e 新 spec 24 例不在 pytest 计数, 由容器 e2e 轨承担)。覆盖率行与上一切片逐列相同, 门槛达标(exit 0; 99% 为展示取整)。

## 本改动面

WEBUI 列风格切换(计划 26-11-20-0009, 五维: 进度条样式/进度条颜色/速度色阶/数值列色阶/单位色组)七批 + 收口批:

- **S1 158384b6** 引擎与存储: 新文件 `shared/colstyle.js`(state↔html 五枚 data-cs-* 同步 + setColStyle 写入口 + adoptColStyle 整份采用)+ `app.js` COLSTYLE_* 常量/loadColStyle + `state.js` data.colStyle 注入与 watch + `lifecycle.js` 首帧同步/storage 监听/回场补齐/撤听 + `ui_prefs.js` 登记 + 四皮肤 index.html manifest 各挂一行。
- **S2 e3420f00** 表头菜单面: `ctx-menus.html` 五维项+flyout+色样 DOM / `menu.js` openSub 钳位锚 hostRef 参数化 + headMenuStyle* 五写链 / `console_hub.css` 色样规则族。
- **S3 2587c27a** 进度条两维: `format.js` progBand/progBandClass / `xtpl-cells.html` 进度格挂档位类 csb-* / `console_hub.css` 进度渲染面(--cs-fill 机制变量)/ 四皮肤基线色源原位改行; 计划外发现入池 issues/26-11-20-0321。
- **S4 94066579** 速度+数值色阶: `format.js` speedBand/cellSpeedTone 三态/numScale 三件+HR 让位 / `xtpl-cells.html` 速度与数值格分派 / `console_hub.css` 速度+数值渲染面; 计划外发现入池 issues/26-11-20-0404。
- **S5 725becb2** 单位拆分与色组: `format.js` fmtSizeParts/fmtSpeedParts(_fmtLadderParts 下沉单点)/ `xtpl-cells.html` 19 格双 span(cs-v/cs-u)/ `console_hub.css` 单位色组渲染面。
- **S6a a4254294** 测试面一: node 电池引擎语义(26 检查项)+ `test_webui_static_skins_skin.py` 模板类→CSS 配对守阵(红验双向实证)。
- **S6b 4ff09f16** 测试面二: 新文件 `e2e/colstyle.spec.mjs` 24 例(引擎面 prism/atlas + SKINS_ALL 四皮肤计算色, 现读 CSS 变量零写死色值); 生产代码与既有 spec 零改动。
- **收口批(随本切片入库)**: `memory-bank/architecture/webui.md`「列风格引擎」节 + `memory-bank/conventions/webui.md` 机制变量/片段模板配对两条纪律 + 根 README Web UI 节一句 + 任务档案翻 Done(R2 日志)+ 计划翻 Done(§10 补 R2)+ 本切片。
