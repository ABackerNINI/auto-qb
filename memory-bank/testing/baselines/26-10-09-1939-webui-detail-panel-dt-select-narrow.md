# 2871 —— WEBUI 详情面板模板选择框收窄 240→150 基线

> 摘要: 用户报「种子详情页模板选择框太长, 长度需保持固定防切页签其它元素移位」—— `.dt-select` 定宽 240→150px(只改定宽值, 定宽口径不变、不回退内容驱动宽), 收起摘要 `.dt-summary` 维持 240px 独立定宽(各按内容域取值不必等宽); 守阵 `test_drawer_tpl_select_fixed_width_tab_independent` / `test_drawer_tpl_cross_seed_fold_and_select_width` 同步 150 并加「240 不得残留」反向断言; 真浏览器双皮肤取证: 四页签 offsetWidth 恒 150(置 auto 探针后还原仍 150), 最长 label(英雄行·键值栅格)自然宽 117px 不截断。2 个源文件(1 源 + 1 守阵), 不命中立档阈值, 切片沿用 26-10-06-0751(同专题追加)。
> 基线时间: 2026-10-09 19:39

**Refs:** memory-bank/activeContext/26-10-06-0751-webui-detail-panel-design.md

## test.full 实测

- 分支: `develop`(HEAD `19175361`, 工作树含本轮改动 + 回写件时实测)
- 命令: `commands run test.full`(Windows, 单次采样 —— 耗时口径见 testing/baseline.md「必须带区间」)
- **实测 (Windows)**: **2871 passed + 3 skipped, 0 failed, 覆盖率 TOTAL 99%**
  (16567 语句 / 167 未覆盖 / 5716 分支 / 143 partial; 门槛 98% 达标)
- 与上基线的差值: `commands run kb.baseline -n 2` 现列(切片正文只写自己的 TOTAL, 不抄逐位对比)。
- **收集面未变**: 本轮 `src/` 仅改 1 处 CSS 定宽值, `tests/` 仅修改既有守阵断言(新增反向断言不新增用例) ⇒ pytest 收集数不变。passed/skip 与上基线各差 1 的成因: `test_commands_engine.py:226` 的 PYTHONUTF8 环境条件用例在本轮 shell 环境实跑(上轮被跳), 与本轮改动无关(该用例 skip 消息自带条件说明)。
- 增量明细(本轮真正新增): 无新文件 —— `src/auto_qb/webui/static/shared/drawer_templates.js`(定宽值与注释)与 `tests/test_webui_static_dom_panel.py`(守阵同步)均为原文件修改; 回写件 `progress/implemented-webui.md` 新条目、切片 26-10-06-0751 追加; 本基线切片。
