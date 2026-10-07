# tests/test_web.py 拆分 —— S0–S3 已执行, 待 S4

> 摘要: 用户指令「实施计划S3」。**S0 开工前置**、**S1 勘察与映射表**、**S2 拆分工具与红验**、**S3 批 1 试切** 已完成。S2 产出一次性工具 [scripts/split_test_web.py](../../scripts/split_test_web.py)(AST 顶层块「gap 归属」切块 + 映射表 + 归属闭包 + import 裁剪 + docstring 条目逐条重分布)。**S3 批 1 落地**: 节 1 → `tests/test_web_auth.py`(14 fn / 409 行) + `tests/test_web_api_core.py`(7 fn / 189 行); 新建 `tests/webui_helpers.py`(437 行 / 21 共享件); `tests/test_web.py` 余量 13,567 行(余 308 fn); `tests/conftest.py` +`web_env`(197→219)。校验 1–4 + 内容/行守恒全绿, collect-only **337 项 / 329 名 == 源**; `test.one` 14+7、`test.quick` **2771+4**、`test.full` **2771+4 / 99%**(与开工基线逐位持平)。**批模式暴露并修复了 S2 工具的 4 处「仅全量模式验证过」缺陷**(校验1 误比余量 / 内容守恒漏未选中桶 / 余量重复 helpers·conftest + 行守恒含 conftest / collect-only 收集整 tests/)。S3 另纠偏: 全仓活引用 ~18 处(S1 只扫 tests/ 漏报 2 处), 留 S8 统一处置。任务档案 [26-10-08-backend-test-web-split](../tasks/26-10-08-backend-test-web-split.md)(Status **In Progress**, §S3)。
> 最后活动: 2026-10-08 03:58

**Refs:** memory-bank/tasks/26-10-08-backend-test-web-split.md

## 现状数字(当轮实测)

- 源 `tests/test_web.py` 拆分前 **14,556 行**; 顶层 **382** 函数 = 327 `test_*` + 2 `testhr_*` + 53 辅助; docstring 计划条目 **312**(0 幽灵, 17 函数无条目)。
- 映射表 **329 fn → 16 文件**(节 3 拆两份 / 节 2 panel·page / 节 1 14-7)。
- 归属闭包: 跨文件非 fixture 辅助 **16** + 常量 **3** + 类 **2** = **21 项 → `tests/webui_helpers.py`**; fixture `web_env` **1 → conftest**; 随唯一使用域 **47**(36 辅助 + 11 常量)。
- **S3 后**: 余量 `tests/test_web.py` **13,567 行 / 308 fn**; 已迁 **21 fn**(auth 14 + api_core 7)。

## 正在进行

- S0–S3 均在 `develop`。**下一步 S4**(尚未开工): 批 2 —— 节 2 webui 静态守阵 → `test_webui_static_skins.py`(8 fn) + `test_webui_static_dom_panel.py`(28) + `test_webui_static_dom_page.py`(27); 全计划最大批(63 fn), 迁后跑 `test.one` 三新文件 + `test.quick` + **`test.full` 里程碑**。
- 批通用命令: `uv run python scripts/split_test_web.py --out-dir tests --rewrite-source --emit-conftest tests/conftest.py --files <逗号分隔> --collect`(conftest 已含 `web_env`, 幂等跳过)。

## 未决项

- 全仓活引用 ~18 处(`src/auto_qb/webui/**`、`static/shared/*.js`、`e2e/*.mjs`、`scripts/ui_harness.py`)指向 `test_web.py` —— **S8 全仓验收 grep** 统一处置(多数指向后续批才迁的函数, 现在改会指向尚不存在的文件)。
- 节 3 杂项里的 6 个 HR 系测试留在 `test_web_backend_misc.py`; 若并入 `test_web_hr.py`, 说一声即可。
- P-03(次大文件 test_hr_service 等续拆)按计划另立, 不混入本批。
- `scripts/split_test_web.py` 去留: 计划 S7 说「迁完删」(若想留作以后复用, 批 commit 前提出)。
