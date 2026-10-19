# 26-10-20-webui-pinned-first-cell-hover — WEBUI 必显列悬停闪竖带（首格过渡与行板不同源）

**Status:** Done
**Added:** 2026-10-20
**Updated:** 2026-10-20
**Summary:** 必显列悬停闪竖带修复: 行板 160ms 过渡而吸左首格无过渡 ⇒ 滑入/移出首帧错拍(实测 Δ14/18); 三皮肤补同源 `background-color var(--dur)` 过渡, 静态 + e2e 逐帧双守阵, 红绿双验已过
**Topics:** webui-pinned-first-cell-hover

## 原始请求

1. 「修复：WEBUI 3个主表的必显列在鼠标滑过时背景与其它列不一致, 短暂时间后恢复一致」(2026-10-20)。

## 思考过程与决策

- **现象定性**: 「短暂后恢复一致」= 过渡窗口内的**过程态**不一致, 不是稳态异色 ⇒ 先怀疑两边**过渡不同源**,
  而不是色值不同源(2026-10-14 那轮修的是稳态色值按面重锚)。
- **定位**: 行板 `.group-row` 带 `transition: background var(--dur)`(160ms); 吸左首格
  `.group-row > :first-child` 只有静态 `background`, **没有任何 transition** ⇒ 悬停首帧首格已 snap 到
  `--bg-hover`, 其余列还在从 `--bg-row` 渐入; 160ms 内行内一条硬边竖带, 过渡结束"恢复一致"。
- **取证**(真浏览器 rAF 逐帧, 临时探针已删): 三主表 × 双皮肤全中; 悬停首帧差 prism/frost Δ14、
  atlas/ocean Δ18; 移出方向同号反相(首格先回基色、行板还在渐出)。
- **处置取舍**: ①只补 `background-color` 过渡, **不**写 `background` 简写 —— expanded/selected/
  search-hit 的 tint 是 `background-image` 渐层(不可插值), 纳进简写无益; ②时长/缓动读 `var(--dur)` /
  `var(--ease)`, 与行板同源(禁字面毫秒, 否则行板调时长时静默错拍); ③**不**改行板时长、**不**删行板
  过渡(既有观感), 也**不**用 `background-color: inherit` 取巧 —— 会让透明行板的面(dt05/dt10)首格
  丢掉不透明遮罩, 兄弟列漏字; ④渐变状态(展开/选中/命中)切换的离散残留本轮不改(机制层、未量、
  用户未报), 已记入坑档 §⑨「残留」。
- **范围**: 只动三皮肤 `views.css` 同一行 + 两份守阵; 抽屉面共用同一条首格规则 ⇒ 一并受益(其按面
  重锚的色值规则一字未动)。

## 实现计划

1. 三皮肤 `.group-row > :first-child` 补同源过渡(`background-color var(--dur) var(--ease)`);
2. 静态守阵钉声明式契约: 行板时长基准 `background var(--dur)` + 首格同源声明 + 首格悬停镜像在位;
3. e2e 守阵钉行为: 三主表 × 双皮肤, 滑入/移出各逐帧采(差 ≤ 2 + 稳态同色**且确实变过色**);
4. 红绿双验: 抽掉该行 ⇒ 静态与 e2e 各红; 还原 ⇒ 绿 + 逐帧差 0;
5. 收尾回写: 坑档 `web-ui/frozen-column.md` §⑨ + 本档案 + 基线切片。

## 子任务状态表

| 步 | 内容 | 状态 |
|---|---|---|
| 1 | 三皮肤首格同源过渡 | Done(2026-10-20) |
| 2 | 静态守阵 `test_frontend_pinned_first_cell_hover_transition_parity` | Done(2026-10-20) |
| 3 | e2e 逐帧守阵 `e2e/main-table-pinned-hover.spec.mjs` | Done(2026-10-20) |
| 4 | 红绿双验(抽行双红 → 还原绿) | Done(2026-10-20) |
| 5 | 收尾回写(坑档 §⑨ / 档案 / 基线切片) | Done(2026-10-20) |
| 6 | 全仓同类面审计(抽屉 04–11 + 经典抽屉表 + 真 `<table>` 各面)+ 静态守阵第 ④ 款 | Done(2026-10-20) |
| 7 | 08 bad 行承光底修正(`--bg-card` → `--bg-row`)+ e2e `STATE_CASES['08']` + 静态守阵 08 条改口径 | Done(2026-10-20) |

## 进度日志

### R0 · 立档 (2026-10-20)

- 定位根因(行板 160ms 而首格无过渡), rAF 逐帧取证(Δ14/Δ18, 三表 × 双皮肤); 三皮肤各补一行
  `transition: background-color var(--dur) var(--ease)`; 新增静态守阵与 e2e 逐帧守阵; 红验(抽掉该行
  两份守阵各红)与绿验(还原后逐帧差 0)均过; 修复后全量数字见 kb.baseline 最新切片。

- 2026-10-20 01:39 修三主表必显列悬停闪竖带: 行板 .group-row 有 transition: background var(--dur)(160ms) 而吸左首格无过渡 ⇒ 滑过首帧首格 snap、其余列渐入, 160ms 内一条硬边竖带(用户报「短暂后恢复一致」); 三皮肤 views.css 补 transition: background-color var(--dur) var(--ease), 静态守阵 test_frontend_pinned_first_cell_hover_transition_parity + e2e main-table-pinned-hover.spec.mjs 逐帧采(滑入/移出各 ≤2, 修复前实测 14/18), 红绿双验已过

- 2026-10-20 02:01 按用户追问「其它位置的表格有没有此问题」做全仓审计: 首格镜像规则只有三皮肤 .group-row > :first-child 一条, 经典抽屉表与 04-11 变体面全部继承它; 真浏览器逐帧复测 06/07/09/10/11 + 经典抽屉面滑入/移出差全 0(10 有 0.5 取整), 04/05 是单内容根无兄弟列; 非 .group-row 的真表(HR 明细/波次/拉取历史、统计面板、hub 行)悬停是整行所有格同时换色且全链无 transition, 结构性不可能错拍。拾取一条非本例的静态残差: 08 bad 行静息态首格 vs 相邻列差 5.3(prism)/3.4(atlas), 远低于可辨阈, 未修、已记档。静态守阵补第 ④ 款(首格过渡只在皮肤单点, dt_table.css 与变体注入不得自带 transition)+ 红验

- 2026-10-20 02:52 按用户『非本例差异一并修』修 08 用户分组 bad 行首格: 逐层量出承光链 —— 行级 error-soft 叠在 section.dt08-grp(计算底 = --bg-row #f7fafd)上, 而首格合成取的抽屉卡底 --bg-card(#fdfeff), 两令牌差经 12% tint 后 5/4/2; dt_table.css 该条基色改 var(--bg-row) 即与行板逐通道一致; e2e dt-table-face-bg 补 STATE_CASES['08'] —— 一直漏测的位; 静态守阵 08 条改口径(必含 --bg-row / 禁 --bg-card), 两侧红绿双验; 全量 pytest 与全量 e2e 均绿
