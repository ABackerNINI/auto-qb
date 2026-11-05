# 断言有效性 · 守阵「量程」原文(外迁)

> 摘要: `pitfalls/testing/assertions.md`「守阵的『量程』」条原文整体外迁(2026-11-05 压缩), 正文原样照搬, 标题降一级以避开坑档条目扫描。
> 触发: CSS 守阵, 子串命中, 量程, 生效面, 聚合, 共用层, shared, CSS 收敛, 底形规则, 删了照样绿, _ui_css_effective, _ui_css_aggregate

## 守阵的「量程」: `assert ".a .b" in css` 会被 `.a .b.mod` 子串命中, 且聚合不等于生效面 (2026-10-21)

- **触发**: 给「三皮肤成对」类 CSS 守阵补断言; 或把一批规则从皮肤文件搬进共用层(shared)之后。
- **判别**: 两种失效形态, 都不报错:
  - **① 子串命中(断言恒真)**: 想钉「底形规则在」写成 `assert ".hr-detail-table .hr-pres" in css`, 而同文件里有
    `.hr-detail-table .hr-pres.hr-pres-on { … }` —— 前者是后者的**子串**, 底形本体删掉也照样绿。本轮红验实测:
    删掉 atlas 的 `.hr-pres { … }` 后守阵**仍然通过**。
  - **② 量错对象(恒红 / 反向放过)**: 守阵惯用 `_ui_css_aggregate(ui)`(只拼该皮肤自己的 CSS 文件)当「这套 UI 的
    样式面」。规则搬进 `shared/console_hub.css` 后该聚合里**永远找不到**它 ⇒ 恒红; 若图省事改成「共用层里有就算过」,
    又变成**任何皮肤漏改都放过**(判据脱离具体皮肤)。问一句: 断言里的「CSS」是「某几个文件」还是「浏览器最终
    生效的那张表」? 存在共用层时二者不等价。
- **处置**: ① 断言末尾带**规则边界**(`{` 或 `:`), 别让更长的同类选择器替你满足它; ② 判「三皮肤成对」改用
  `_ui_css_effective(ui)` = 皮肤聚合 + shell 里挂的 shared CSS(link 序) —— 判据落在**该皮肤实际吃到的级联面**上;
  ③ 收敛类改动的等价性别靠人眼: 对改前/改后各现算一次「最终生效规则表」(按 link 序拼接后取每个 selector 的最后
  一条声明), 逐条比 selector→body, 再查生效表内有无重复声明 —— 三者全等才算「搬了位置、没改结果」。
- **守阵**: `tests/test_webui_static_skins_table.py::test_frontend_hr_detail_table_wiring`(反向断言: 徽章底形族必须在各
  皮肤自己的 CSS 里) / `tests/webui_helpers.py::_ui_css_effective`。
- **复发**: 0
