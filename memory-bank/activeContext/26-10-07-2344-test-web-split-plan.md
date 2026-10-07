# tests/test_web.py 拆分 —— S0–S1 已执行, 待 P-01 拍板

> 摘要: 用户指令「实施计划S0-S1」。**S0 开工前置**已完成: `已同步 34356f49`; 分支 `feat/test-web-split`; 基线复测 `test.full` = **2771 passed + 4 skipped / 16476-165-5694-149 / 99%**, 与切片 [26-10-08-0223](../testing/baselines/26-10-08-0223-test-webui-peers-harness.md) 逐位持平(计划基线 2757 已陈旧); 提交时按 DoD 落开工基线切片 [26-10-08-0258](../testing/baselines/26-10-08-0258-backend-test-web-split-s0s1.md)。**S1 勘察**已完成: AST 扫描 + 映射表 329 fn 全覆盖零遗漏(嵌入档案)。**P-01/P-02 已拍板**(2026-10-08 用户裁决): 节 3 拆两份 / 节 2 panel·page / 节 1 14-7 / 共享件 fixture→conftest + 辅助→`tests/webui_helpers.py`。**纠偏四处**: ①被收集测试函数 323→**329**(327 `test_*` + 2 `testhr_*`); ②docstring 计划条目 306→**312**(0 幽灵 / 17 函数无条目); ③基线 2757→**2771**; ④节 3 内容异质 —— 计划名 `test_web_traffic_qb.py` 的 55 fn 里**仅 18 是流量**, 另 37 为 config/token/sites/group-view/error-reason/hr-status ⇒ 拆两份, 目标文件数 15→**16**。任务档案 [26-10-08-backend-test-web-split](../tasks/26-10-08-backend-test-web-split.md)(Status **In Progress**)已落; 未动 tests/ 与 src/ 任何一行。
> 最后活动: 2026-10-08 02:58

**Refs:** memory-bank/tasks/26-10-08-backend-test-web-split.md

## 现状数字(当轮实测, HEAD `34356f49`)

- `wc -l`: test_web.py **14,556 行**(计划基线 0ae3212e 时 14,367)。
- 顶层函数 **382** = 327 `test_*` + 2 `testhr_*`(被 pytest 收集, 默认 `python_functions=test*`)+ 53 辅助; `pytest --collect-only` = **337 项 / 329 函数**(`test_state_kind_maps_states` 参数化 ×9)。
- 类 2 个(`_ListLogHandler` L13760 / `module_log` L13769, 均在节 13); 顶层常量 14 个。
- docstring 计划条目 **312**(0 幽灵, 17 函数无条目)。
- 节结构 15 标记: 5892 流量 / 7884 HR-refresh / 7927 sites / 8064 history / 9390 命令 / 10399 强制汇报 / 10776 视图热重载 / 11624 管理端点 / 12229 种子中心 / 13067 W0 守阵 / 13209 快捷键 / 13512 跳检 / 13757 P1 运行时长尾 / 14126 P1 路由长尾 / 14370 v3 活尾。
- 外部牵连复核: 无 import; 仅 2 处注释(tests/helpers.py:277、test_facade_modules.py:39); pytest.ini 平铺自动收集、无需改。

## 正在进行

- S0–S1 与 **P-01/P-02 拍板**均已闭环(2026-10-08 用户裁决): 节 3 **拆两份**(18 流量 → `test_web_traffic_qb.py` + 37 杂项 → `test_web_backend_misc.py`); 节 2 按内容分 `test_webui_static_dom_panel.py`(28)/`test_webui_static_dom_page.py`(27); 节 1 维持 14/7; 共享件 —— 仅 `web_env` 进 conftest, 16 个非 fixture 跨文件辅助 + 3 常量进新建 `tests/webui_helpers.py`。目标文件 15→**16**。
- 下一步 **S2**: 拆分脚本 `scripts/split_test_web.py` + 校验 4 条(①集合 = 329 / ③条目 = 312)+ 红验 3 条(尚未开工)。

## 未决项

- 节 3 杂项里的 6 个 HR 系测试(`test_api_hr_status_*` ×3 / `testhr_view_fields_*` ×2 / `test_build_group_view_hr_tags`)按「拆两份」留在 `test_web_backend_misc.py`; 若并入 `test_web_hr.py`, 说一声即可(当前保 hr = 51 与计划 §3.1 一致)。
- P-03(次大文件 test_hr_service 等续拆)按计划另立, 不混入本批。
- 计划原文 S0 写档案名 `26-10-07-...`; 按 kb.time 建档日口径实际落 `26-10-08-backend-test-web-split.md`。
