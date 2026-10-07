# tests/test_web.py 拆分 —— S0–S2 已执行, 待 S3 试切

> 摘要: 用户指令「实施计划S2」。**S0 开工前置**、**S1 勘察与映射表**、**S2 拆分工具与红验** 已完成。S2 产出一次性工具 [scripts/split_test_web.py](../../scripts/split_test_web.py): AST 顶层块按「gap 归属」切块 + 映射表(读任务档案) + 辅助/常量「定义→使用」传递闭包定归属 + 每文件 import 头按 used-names 裁剪 + docstring「## 测试计划」条目按函数名逐条重分布(逐字取源行); 内建**校验 4 条**(①集合恒等 ②各恰一次 ③docstring 反幽灵 + 条目守恒(钉 312) ④可编译 + `--collect` 计数恒等)+ **内容/行守恒** 2 条。**演练(不触生产)**: 全量拆到 `R:/Temp/auto-qb/split-drill-s2`(testpaths 之外) → 全绿, `pytest --collect-only` = **337 项 / 329 函数名 == 源**; 块体行 14,180 逐行搬移。**红验 3 条**(§5.3, 临时副本注入)**6/6 先红后修**。**S2 纠偏**: 日志辅助类 `module_log`/`_ListLogHandler` 实跨 3 目标文件(非计划说的「内聚随节 13」)⇒ 共享件实为 **21 项**(16 辅助 + 3 常量 + 2 类)。`test.quick` **2771 passed + 4 skipped**(与开工基线逐位持平, 未动 tests/ 与 src/ 一行)。任务档案 [26-10-08-backend-test-web-split](../tasks/26-10-08-backend-test-web-split.md)(Status **In Progress**, §S2)。
> 最后活动: 2026-10-08 03:32

**Refs:** memory-bank/tasks/26-10-08-backend-test-web-split.md

## 现状数字(当轮实测)

- 源 `tests/test_web.py` **14,556 行**; 顶层 **382** 函数 = 327 `test_*` + 2 `testhr_*` + 53 辅助; 类 2; 顶层常量 14; docstring 计划条目 **312**(0 幽灵, 17 函数无条目)。
- 映射表 **329 fn → 16 文件**(节 3 拆两份 / 节 2 panel·page / 节 1 14-7)。
- 归属闭包: 跨文件非 fixture 辅助 **16** + 常量 **3** + 类 **2** = **21 项 → `tests/webui_helpers.py`**; fixture `web_env` **1 → conftest**; 随唯一使用域 **47**(36 辅助 + 11 常量)。
- 工具演练: 输出 16 文件 + `webui_helpers.py`; 最大单文件 `test_webui_static_dom_panel.py` **2,232 行**(≤2,500 硬上限); 块体行 **14,180**。

## 正在进行

- S0–S2 已在 `develop`(S0–S1 于 `136a42bf`/`591797e5`; S2 随本专题入库)。**开工发现工作区脏**(本档一笔提交后写入的陈旧草稿), 已 `git checkout --` 复原。
- 下一步 **S3**(尚未开工): 批 1 试切 —— `--out-dir tests --rewrite-source --files test_web_auth.py,test_web_api_core.py --emit-conftest tests/conftest.py`; 迁后跑 `test.one` 两新文件 + `test.quick`; 同步改 2 处活注释(`tests/helpers.py:277`、`tests/test_facade_modules.py:39`)。

## 未决项

- 节 3 杂项里的 6 个 HR 系测试留在 `test_web_backend_misc.py`; 若并入 `test_web_hr.py`, 说一声即可。
- P-03(次大文件 test_hr_service 等续拆)按计划另立, 不混入本批。
- `scripts/split_test_web.py` 去留: 计划 S7 说「迁完删」(若想留作以后复用, 批 commit 前提出)。
