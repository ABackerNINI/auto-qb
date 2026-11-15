# 26-11-16-webui-statusbar-speed-jitter — WEBUI 状态栏速度组定宽: 冻结右钉组左缘漂移

**Status:** In Progress
**Added:** 2026-11-16
**Updated:** 2026-11-16
**Summary:** 状态栏上传/下载速度数值变化推动右钉速度组整体平移; 已出定宽修复计划(共享层 `.val`/`.lim` 各 13ch), S1-S5 待显式开工
**Topics:** webui-statusbar-speed-jitter
**Refs:** memory-bank/plans/26-11-16-0130-plan-webui-statusbar-speed-jitter.html

## 本篇只回答

本轮「出计划」交付了什么: 根因认定、定宽方案与 D1-D14 拍板结论、S 阶段拆分; 后续实施进度由各轮收尾追加。

## 原始请求

1. 「WEBUI状态栏上传/下载速度变化导致UI元素位置跳动，grilling然后出一个修改计划」
2. 第一轮 grilling 六问 → 「按推荐」
3. 第二轮 grilling 八问 → 「Q14 一并纳入。其余按推荐」
4. 对 Q15 定宽方案的表态: 「无未读时常驻多占 ~23px无法接受，不能往左边撑吗？速度在右边，左边空间那么多。」
5. 「出计划」

## 思考过程与决策

- **根因取证推翻了直觉**: 四皮肤 `.sb-spd .val/.lim` 早已是 mono + `tabular-nums`(`atlas/css/dialogs.css:471`、`prism/css/views.css:79`、`console/style.css:158-159`、`flux/style.css:166-167`), 跳动源不是字形宽, 而是 `fmtSpeed`(`format.js:35-38`) 的**整段字符串长度**随量级变; 右缘钉死的 `.sb-speed` 宽度一变, 左缘就带着整组平移。
- **为什么定 13ch**: `fmtSpeed` 有界档最长形 `"1023.99 KiB/s"` = 13 字符; `12ch` 会让这一档撑开, 方案即失效; GiB 档到 `"9999.99 GiB/s"` 仍是 13 字符(≈10 TiB/s)。
- **为什么不改 `fmtSpeed`**: 全局共用, 外溢到抽屉速度格、图表 y 轴轴标与后端 `utils.fmt_speed` 同口径断言; 改显示语义对生产项目不划算。
- **Q14 前提被推翻**: 取证发现 `.sb-spacer{flex:1}` 就在 `.sb-err` 左侧, 未读徽标出现只会让按钮向左挤 spacer, 速度组不动; 因此「定宽 53px」作废, 改判**零 CSS 改动** + e2e 几何守卫 + 窄屏裁切边界记录(用户对「往左撑」的追问正是这一步)。
- **计划**: `memory-bank/plans/26-11-16-0130-plan-webui-statusbar-speed-jitter.html`, D1-D14 见其 §06; 零代码改动, S1-S5 待显式开工。

## 实现计划

引用计划 §04: S1 共享层 CSS 定宽 + 窄屏退让 → S2 静态守阵 `_scan_statusbar_speed_width` → S3 新增 `e2e/statusbar-speed-geometry.spec.mjs`(四皮肤/`@fast`/4ms 逐帧) → S4 全量回归 + 基线切片 → S5 回写 `webui.md`/坑档 + 四皮肤目检 + 计划收口。

## 子任务状态表

| 步 | 内容 | 状态 |
|---|---|---|
| 计划入库 | 两轮 14 问拍板 + 计划落位 + 档案立档 | Done(2026-11-16) |
| S1 | `shared/console_hub_panels.css` 尾段 `.val`/`.lim` 定宽 13ch(右/左) + 窄屏 `@media` 退 4ch | Open |
| S2 | 静态守阵 `_scan_statusbar_speed_width`(钉值 + 四皮肤无覆盖 + `.sb-err` flex 不变量) | Open |
| S3 | e2e `statusbar-speed-geometry.spec.mjs`(四皮肤/逐帧/样本序列/徽标场景) | Open |
| S4 | `test.quick` → `test.full` 全绿 + 基线切片 | Open |
| S5 | 文档回写 + 坑档指链 + 四皮肤目检 + 计划转 Done | Open |

## 进度日志

### R0 · 立档 (2026-11-16)

grilling 两轮 14 问(D1-D14 全按推荐, Q14 追加纳入) + 两轮只读取证(状态栏模板/DOM、四皮肤 CSS、格式化链、flux 补间、守阵与 e2e 采样面、计划模板骨架) + 计划入库 Open + 档案立档。关键收益: 把「数字不等宽」这个直觉根因改判为「字符串长度变化」, 并测算出 13ch 硬上界; 同时推翻 Q14 的定宽前提(改判零改动 + 守卫)。零代码改动、未入池 issue、未 commit/push。

- 2026-11-16 01:32 grilling 两轮 14 问拍板 D1-D14 全按推荐(Q14 追加纳入后经取证改判零改动-向左挤 spacer) + 两轮只读取证(状态栏模板/四皮肤 CSS/format.js 链/flux 补间/守阵面) + 计划 26-11-16-0130 入库(Open, S1-S5 待显式开工, 共享层 .val/.lim 13ch) + 档案立档; 零代码改动, 未入池 issue, 未 commit

### R1 · 提交前评审修三轮 (2026-11-16)

计划提交前按 code-review 纪律跑四轮(全能档 1 子代理, 批 162 行): R1 修 8 条(1 major + 7 minor)、R2 修 3 条(1 major + 2 minor)、R3 修 2 条(minor)、R4 零 actionable 闭合。13 条全部过 review.check 引文校验、零 refute, 全部当场修完, 入池 0。实质修正三处: ① S2 守阵判据按 `@media` 层级分层(原「各恰 1 条」与 S1 的窄屏 `.lim` 第二条冲突会恒红), 并补三处接线与「共享层单独读」; ② 窄屏契约收窄为「只保 `.sb-speed` 右缘不动」—— `min-width` 只是下限, 长限速值仍撑开, 原「`.val` 右缘也不动」几何上不成立; ③ R5 覆盖面收窄为「更高特异性」(等/低特异性被后加载的共享层压掉)。另有 900px 断点依据修正(四皮肤共有断点有 900 与 1320 两档, 900 是最窄)、两处字符数(10 非 11)、图表 `10px` 是字号非每字符宽。计划 doc-updated 抬至 26-11-16-0154, §10 记 R1-R3 三行。

- 2026-11-16 01:55 提交前评审四轮闭合(R1 修 8 / R2 修 3 / R3 修 2 / R4 零 actionable, 13/13 过检零 refute, 入池 0) + 计划 §10 R1-R3 落行 + 档案进度日志; 仍零代码改动, S1-S5 待显式开工

- 2026-11-16 02:39 S1-S5 实施完成: S1 CSS 定宽(shared 尾段三行) / S2 静态守阵 _scan_statusbar_speed_width + 三处接线, 五变异红绿双验 / S3 e2e statusbar-speed-geometry 四皮肤逐帧几何(四皮肤 4 passed + 摘 CSS 红验 + flaky 守卫绿) / S4 test.full 6266+2 覆盖 99.59% 基线切片 26-11-16-0236, 既有 statusbar-kbd-entry + views.spec 40 passed 零松动 / S5 webui.md 硬规则节 + progress-bar.md 同族指链 + 计划 R4 转 Done; 真机目检留用户; commit 待用户显式指令。

- 2026-11-16 02:59 收尾评审: 全能档 1 派遣(379→381 行), R1 两条 minor 全修(① e2e 注入改经 withVm 唯一直径 ② _sb_spd_target 组合器间隔扩正则 + 组合器变异红验), 复评轮 R2 零 actionable; 检 2/2 全过, 修 2 入池 0 blocker 0; 末轮基哈希 92db296fbe72; commit 待用户显式指令。
