# 基线 · 1760 passed + 2 skipped —— 弹窗下拉悬停接管修复轮 (comboHoverIdx + CSS 单路高亮)

> 摘要: issue 26-09-29-2142-bug-dialog-hover-keynav-fight(站点搜索闪烁同族)修复轮 ⇒ 三处弹窗下拉
> (添加种子分类/标签、编辑分类)悬停接管改 @mousemove + 3px 位移门限共享小工具 comboHoverIdx,
> 开层单点复位门限坐标, 三皮肤 CSS data-hi 行摘 :hover(.on 单路)。守阵
> test_frontend_dialog_combo_hover_takeover(已红验)。真机 A/B: 改前 ↓×16 两次被拽回、Enter 选错
> cat-06; 改后轨迹 1→16 纯净、Enter cat-16、零位移合成 mousemove 被门限挡住。
> 基线时间: 2026-09-29 23:16 (develop @ 2ceb914a + 本轮未提交改动; 开工前 my-commit-flow.sync 已同步)
> 档案: tasks/26-09-29-webui-dialog-hover-keynav.md

TOTAL 1760 passed + 2 skipped / 91%(12480 语句 / 999 未覆盖, test.full 30.90s, rc=0) —— 0 failed。
较上轮切片 26-09-29-2210(1751 / 12442)+9 passed / +38 语句: 本轮新守阵 1 条(tests/test_web.py),
其余 8 条来自会话开始 sync 合并的远端提交(HR 计数对平 M1, test_hr_service.py +239 行)。
改动面: shared/{state,dialogs,add_torrent}.js / shared/tpl/{dialogs-mgr,popovers}.html /
atlas+console dialogs.css 与 prism components.css(data-hi 行 hover 中和) / tests/test_web.py。
