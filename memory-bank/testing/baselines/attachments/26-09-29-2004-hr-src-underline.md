# 基线 · 1749 passed + 1 skipped —— 做种时长列 HR 来源标记非文字化轮 (在线/本地/未核 两字芯片 → 底线)

> 摘要: 用户报「做种时长列尾部的『本地/在线』芯片把列撑长」⇒ 计划 plans/26-09-29-1905 三轮收敛定稿
> (M2: 线色 currentColor 随档位色、不引入新色; 编码 = 长度(在线整格 / 本地与未核实半格) + 线型(未核实
> 2px 点线 80%) + 明暗(本地 50% 兜底)) ⇒ 实施: hr.js 撤 HR_SRC_BADGES/hrSrcBadge、加 HR_SRC_CLASSES/
> HR_SRC_TITLES 与 hrSrcClass/hrSrcText/hrSrcFull/hrSrcHalf; 三处模板(torrents/groups/shows)同构换绑
> + 数值包 .dur-val 挂半格线; atlas/prism/console 三套 CSS 成对加 .m-dur .hr-line 规则; 守阵
> test_frontend_hr_safety_wiring 随换绑改写并扩到三套 CSS 对账(含「半格线必须显式 width:100%」)。
> 基线时间: 2026-09-29 20:04 (develop @ ae29a4f, 开工前 commands run my-commit-flow.sync 已同步)
> 制品: plans/26-09-29-1905 (doc-status In Progress —— 代码已落地, 待真机走查)

TOTAL 1749 passed + 1 skipped / 91%(12432 语句 / 999 未覆盖, test.full 29.3s)
另有 **2 failed 与本次改动无关**: tests/test_file_access.py::test_mapped_symlink_escape_treated_as_miss
与 ::test_mapped_mount_root_via_symlink —— 本机 Windows 符号链接解析的环境失败(断言的是
`map_to_container` 对挂载内 symlink 的逃逸判定), 改动面(前端静态资源 + 文档)零交集。
本轮中途还修掉 4 条自身引入的红: 计划 HTML 缺 `doc-*` meta(doc-type/topic/status/added/updated)
⇒ 补 meta + `commands run kb.index` 重建索引 ⇒ test_docs_forms.py 四项守阵转绿。

## 守阵随改动同步的部分(test_frontend_hr_safety_wiring)

- 映射表对账: `HR_SRC_BADGES` → `HR_SRC_CLASSES`(仍与后端 resolve.py 的 7 个 SRC_* 常量逐字一致),
  新增 `HR_SRC_TITLES` 三档非空文案校验(桶名表不能复用 —— `unverified` 桶名是空串, 拿来当 title 会空白)。
- 模板接线: `:class="hrDurClass(m)"` → `:class="[hrDurClass(m), hrSrcClass(m)]"`(各 3 处),
  `v-if="hrSrcBadge(m)"` → `v-if="hrSrcHalf(m)"` + `v-if="hrSrcFull(m)"`(各 3 处),
  并加「旧 hrSrcBadge 零残留」断言。
- CSS 对账: 从「两套」扩到**三套**(atlas/prism/console 聚合), 规则清单加 `.m-dur .hr-line`,
  并钉死 `.m-dur .dur-val > .hr-line { … width: 100% }` —— 空 `<i>` 绝对定位只给 `left:0` 时
  width:auto 会收缩成 0, 半格线整条不可见(真机已踩: 本地/未核实的线一度全看不见)。

## 第二轮复测(撤「已排除」chip, 2026-09-29 20:17)

用户追加指令「一并改成 title」⇒ 撤掉做种时长列最后一个行内文字 chip: `hr.js` 加 `HR_EXCLUDED_TITLE`
(文案单点) + `hrDurHint(m)`(来源文案 + 已排除说明拼进单元格 title), 三处模板 `:title` 换绑并删 chip 行;
三套 CSS 各删 `.m-pair .hr-src`(无消费方即死样式); 守阵加三条零残留断言(`HR_EXCLUDED_TITLE` 存在、
模板里 `class="hr-src"` / `>已排除<` 消失、CSS 里 `.m-pair .hr-src` 消失)与 `:title="hrDurHint(m)"` 各 3 处针脚。
❗方法名不能叫 `hrDurTitle` —— 守阵钉着它"不得出现"(那是被悬停弹窗取代的旧原生 title 绑定)。

TOTAL **1749 passed + 1 skipped / 91%**(test.full 29.6s), 2 failed 仍是同两条 file_access symlink 环境项 ——
与首轮数字完全一致, 改动面(前端静态资源 + 注释/文档)未触及被测逻辑。

## 第三轮复测(认领并修复 issue 26-09-29-2031, 2026-09-29 20:40)

前两轮那 2 条 failed 不是"环境噪声"而是**测试缺陷**, 本轮认领修复:
`_dir_symlink_or_skip`(tests/test_file_access.py) 旧实现只 `except (OSError, NotImplementedError)`,
本机 `os.symlink` 是**假成功** —— 不抛异常但 `os.path.lexists(link)` 为 False(连普通目录都没建出来,
比先例"落成真实目录"更彻底), `islink` 恒 False ⇒ "逃逸链接"不存在, 逃逸断言失去前提,
两条端到端用例 **failed 而非 skip**, 直接卡死 `ship.commit` 的 test.quick 闸门。
修法: 建链后补 `os.path.islink(link)` 复核(为 False 即 skip), `AttributeError` 一并进 except;
同步补 file-conventions.md「测试不得依赖宿主环境能力」第 ③ 例 + 通用形态(建链类 helper
异常路径之外必须再判 islink)。**生产代码未动**(SEC-1 逃逸判定未被证伪)。

TOTAL **1749 passed + 3 skipped / 91%**(12432 语句 / 999 未覆盖, test.full 33.7s, rc=0) ——
**0 failed**: skipped 由 1 变 3, 正是基线 26-09-27-1737 记的本机预期形态(无建链能力 ⇒ skip),
闸门恢复可用。覆盖率口径见 [baseline.md](../../testing/baseline.md)。

## 第四轮复测(整格线随列宽 → 随文字, 2026-09-29 21:0x)

真机走查报「在线的线随列宽而不是随文字」⇒ 根因: 行是 `display: grid`, 做种时长单元格是 **grid item
被拉满整列宽**(默认 stretch), 而整格线是 `.m-dur > .hr-line { width: 100% }` 的空 `<i>` ⇒ 线画成整列
一条。修法: 三处模板(torrents/groups/shows)把「数值 + 要求」包进**文字包裹层** `<span class="dur-body">`
(inline-flex / flex item ⇒ fit-content), 整格线改挂 `.dur-body`(`bottom: calc(-1 * var(--dur-pad))`,
与半格线同一条基线); 三套 CSS 成对加 `.m-dur .dur-body` 规则。**不缩单元格** —— 单元格保持整列宽,
悬停弹窗的触发面与 native title 命中区不变(缩 `.m-dur` 会让弹窗只在文字上才触发)。
守阵加四条针脚: 模板 `class="dur-body"` 各 3 处; CSS 必含 `.m-dur .dur-body` 与
`.m-dur .dur-body > .hr-line`(含显式 `width: 100%`); `.m-dur > .hr-line` **零残留**(挂回单元格即回归)。
计划 plans/26-09-29-1905 的 02/04/05 段与样式块随改同步(整格线挂包裹层的坑写进「实现坑二」)。

TOTAL **1749 passed + 3 skipped / 91%**(12432 语句 / 999 未覆盖, test.full 31.8s, rc=0) —— 0 failed,
数字与第三轮一致(改动面 = 三处模板 + 三套 CSS + 守阵, 未触及被测业务逻辑)。
