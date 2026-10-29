# webui-main-table-dark-bg

> 摘要: 建计划 26-10-30-0217: 主表暗主题背景重设计, 现状取证(views.css:171/275, ocean.css:7-13) + 4 套可交互模板(对照/A平板/B斑马/C沉降卡/D幽灵行)写入 §03, 待拍板 D1-D3
> 最后活动: 2026-10-30 05:44

**R0(2026-10-30 02:22):** 建计划 26-10-30-0217: 主表暗主题背景重设计, 现状取证(views.css:171/275, ocean.css:7-13) + 4 套可交互模板(对照/A平板/B斑马/C沉降卡/D幽灵行)写入 §03, 待拍板 D1-D3

**R1(2026-10-30 04:19) 阶段 5 收尾核对完毕, 与计划的偏差两处(其余逐项过, 全量绿见 kb.baseline):**
- `tests/test_webui_error_history.py` 的 STORAGE_WRITE_BASELINE 补 `rowlang.js: 1` —— rowlang.js 按 §04-1 落 localStorage 持久化, shared/ 层 setItem 逐文件计数守阵首跑红; 修的文件超出本阶段任务书枚举的修复清单(只列了 test_webui_static_skins.py cap), 但属「本次改动引入的测试失败」, 修法即守阵失败信息行内注明的合法路径(改基线并行内注明)。
- `prism/css/components.css` 有改动(菜单条目 .rowlang-item 并选择器复用 theme-item 外观规则 + frost/golden 下 .rowlang-group 整组隐藏) —— 计划 §04-1 只单列「topbar.html 加分组」, 未列三皮肤 components.css 的条目样式接线; 属菜单挂载必要配套, 非行为偏差。
- 待办留给主会话: 计划 §10 变更记录未动(kb.bump 统一收尾)、kb.wrap 未跑、commit/push 未做(按本轮禁令)。

**R2(2026-10-30 05:44):** 实施完成 A/B 双语言可切换(五阶段子智能体串行): shared/rowlang.js+row_lang.css 单点+topbar 菜单+三皮肤挂载; 验收四轮迭代(星图console开关/斑马hover档差/左条旧规格/名称列闪变→color-mix纯色/左条双状态条); 全量与基线见 kb.baseline(切片 26-10-30-0419); 新坑 2 条(color-mix alpha 权重/无头亮主题假象)
