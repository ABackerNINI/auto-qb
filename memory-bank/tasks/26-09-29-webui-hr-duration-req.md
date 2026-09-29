# 26-09-29-webui-hr-duration-req — 做种时长列/弹窗不再显示「要求」(未核/在线行)

**Status:** Done
**Added:** 2026-09-29
**Updated:** 2026-09-29
**Summary:** 用户实报「做种时长部分『未核』/『在线』的不显示要求时间了, 显示的是『未核实(本地不触发) 无时长要求』, 还有孤立的『未核』标识」。核对为**两处渲染门**叠加: ①表格 `.req`(要求)只在 `hr_triggered` 为真时渲染 ⇒ 未核/在线行被连要求一起藏掉、只剩来源芯片; ②弹窗把 `unverified` 与真放行/免罪一同收起成「无时长要求」徽记 ⇒ 未核行看不到本地要求(实测它 `hr_req_time=115200s`, 确有要求)。修复: 三份模板的要求渲染门改为「已做种非空 + 有要求」, 弹窗收起条件只留 `site_released`/`site_exempt`。守阵 `test_frontend_hr_safety_wiring` 增两条断言(红验: 回退即红)。test.full 1747 passed / 4 skipped (91%)。
**Topics:** webui-hr-popup

## 原始请求

用户实报: 「现在的做种时长部分『未核』/『在线』的不显示要求时间了, 显示的是『未核实(本地不触发) 无时长要求』, 还有孤立的『未核』标识」—— 未提供截图, 故先只读核对运行实例字段再动手。

## 思考过程与决策

- **现象是「上游修好后被点亮」而非回归**: 前几轮修好 HR 视图发布之前 `judged is None` ⇒ `hr_safety` 恒空串 ⇒ 整列回落历史外观(无芯片、无弹窗); 修好后 `hr_safety` 有值 ⇒ 来源芯片与悬停弹窗**第一次**上线, 那些从未在生产渲染过的分支里的口径问题才暴露。用户语气是"现在不显示了", 实际是"从没显示过"。
- **实况分布(只读 `/api/state` 实测)**: 108 个种子中 `hr_safety_src` = `local` 12 / `unverified` 8 / `site_satisfied` 2 / 空 86; `hr_req_time = 0` 有 77 行(未配 HR 的站点)。8 个未核行 `hr_req_time=115200s`(1.33 天)、`hr_triggered=false`(本地已满足 ⇒ 不触发 HR 条件) —— **要求是配置事实, 与是否触发无关**, 藏掉它纯属信息损失。
- **两处门**:
  ① `shared/tpl/{torrents,groups,shows}.html`: `<span v-if="cellSeedingTime(m) && m.hr_triggered && m.hr_req_time" class="req">/ …` —— 未触发即无要求, 于是单元格只剩一个来源芯片(用户说的"孤立标识")。
  ② `shared/hr.js::hrPopData`: `if (["site_released", "site_exempt", "unverified"].includes(src) || !(req > 0))` 收起轨道换「无时长要求」徽记 —— `unverified` 被与"真放行"同类处理。
- **决策**: 要求门只认「已做种非空 + 有要求」(`hr_req_time > 0`); 弹窗收起条件只留 `site_released`/`site_exempt`(义务已了, 收起合理), 未核实(本地不触发)改画本地轨 —— 与用户实报口径一致的最小改动。孤立芯片不单独处理: 要求回到它左边后即不再"孤立"。
- **未动**: 标签口径(`hr_tag`)、`hrTimeClass` 配色(未触发行保持中性色)、后端字段与判定语义(纯前端渲染门)。

## 实现计划

1. `static/shared/tpl/{torrents,groups,shows}.html`: 三处要求渲染门去掉 `m.hr_triggered &&`(必须同改, 单一语义源分片三份)。
2. `static/shared/hr.js`: 收起条件去掉 `unverified` + 文件头/分支注释同步(零冗余口径的例外处写明原因与实报出处)。
3. `tests/test_web.py::test_frontend_hr_safety_wiring`: 增两条断言 —— ①三份模板的要求门必须是 `"cellSeedingTime(m) && m.hr_req_time"`; ②收起条件含 `site_released`/`site_exempt` 且**不得**含 `unverified`。

## 子任务状态表

| 子任务 | 状态 | 备注 |
|---|---|---|
| 只读核对实况字段(哪个 src 受影响、req 是否为 0) | Done | 2026-09-29 本轮 |
| 三份模板要求渲染门 | Done | 未触发行也显示要求时长 |
| 弹窗收起条件(未核实不再收起) | Done | 注释写明例外原因 |
| 守阵两条 + 红验 | Done | 回退三模板+hr.js 即红 |
| 收尾回写(档案/基线/坑档/进度) | Done | 基线 26-09-29-1920 |

## 进度日志

- **2026-09-29**: 用户实报 → 只读核对运行实例(`hr_safety_src` 分布 + `hr_req_time`) → 定位两处渲染门 → 修复 + 守阵(红验回退即红) → test.full **1747 passed / 4 skipped (91%)** 全绿 → 回写。**未提交**(等用户显式指令)。
- **2026-09-29(同日, 收尾环节)**: 回写撞两处 KB cap —— `pitfalls/web-ui/contract-api.md` 6,275 > 6,000、`progress/implemented-webui.md` 10,751 > 10,000。处置: ①压**自己那条**(674 → 384, 判据全留); ②把进度文件**最老 4 条**(多选右键菜单 09-24 / 右键次级菜单三修 09-25 / 搜索负词定案 09-26-27 / 搜索匹配收敛 09-26)按 cap 轮转**原样外迁** `implemented-webui-history.md`(14,013 → 16,501)并在原位留一行指针(10,751 → 8,832)。教训已入 [pitfalls/kb/cap-counting.md](../pitfalls/kb/cap-counting.md)「追加内容前先看余量」(**复发 2**: 追加前没量余量, 又一次拖到守卫才红)。
