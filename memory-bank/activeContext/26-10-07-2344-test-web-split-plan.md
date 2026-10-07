# tests/test_web.py 拆分 —— S0–S4 已执行, 待 S5

> 摘要: 用户指令「实施计划S3」「实施计划S4」。**S0 开工前置**、**S1 勘察与映射表**、**S2 拆分工具与红验**、**S3 批 1 试切**、**S4 批 2 webui 静态守阵** 已完成。工具 [scripts/split_test_web.py](../../scripts/split_test_web.py)(AST 顶层块「gap 归属」切块 + 映射表 + 归属闭包 + import 裁剪 + docstring 条目逐条重分布)。**S3 批 1 落地**: 节 1 → `tests/test_web_auth.py`(14 fn / 409 行) + `tests/test_web_api_core.py`(7 fn / 189 行); 新建 `tests/webui_helpers.py`(437 行 / 21 共享件); `tests/conftest.py` +`web_env`(197→219)。**S4 批 2 落地**(全计划最大批, 63 fn): 节 2 → `tests/test_webui_static_skins.py`(8 fn / 1,449 行) + `tests/test_webui_static_dom_panel.py`(28 / 2,232) + `tests/test_webui_static_dom_page.py`(27 / 1,131); `tests/test_web.py` 余量 8,809 行(余 245 fn); `webui_helpers.py`(436)与 `conftest.py`(217)本批未动。两批校验 1–4 + 内容/行守恒全绿, collect-only 恒 == 源; `test.quick`/`test.full` 均 **2771+4 / 99%**(与开工基线逐位持平)。**批模式共暴露并修复工具 5 处「仅全量模式验证过」缺陷**(S3 四 + S4 一: 共享模块被后续批清空 ⇒ 仅当本批有共享块才写 `webui_helpers.py`)。S4 另纠偏: `--expect-fn/--expect-entries` 是「当前源」口径(308/291 = 全量 329/312 − 已迁 21), 非计划全量。任务档案 [26-10-08-backend-test-web-split](../tasks/26-10-08-backend-test-web-split.md)(Status **In Progress**, §S4)。
> 最后活动: 2026-10-08 04:10

**Refs:** memory-bank/tasks/26-10-08-backend-test-web-split.md

## 现状数字(当轮实测)

- 源 `tests/test_web.py` 拆分前 **14,556 行**; 顶层 **382** 函数 = 327 `test_*` + 2 `testhr_*` + 53 辅助; docstring 计划条目 **312**(0 幽灵, 17 函数无条目)。
- 映射表 **329 fn → 16 文件**(节 3 拆两份 / 节 2 panel·page / 节 1 14-7)。
- 归属闭包: 跨文件非 fixture 辅助 **16** + 常量 **3** + 类 **2** = **21 项 → `tests/webui_helpers.py`**; fixture `web_env` **1 → conftest**; 随唯一使用域 **47**(36 辅助 + 11 常量)。
- **S4 后**: 余量 `tests/test_web.py` **8,809 行 / 245 fn**; 已迁 **84 fn**(S3 21 + S4 63: skins 8 + panel 28 + page 27)。

## 正在进行

- S0–S4 均在 `develop`。**下一步 S5**(尚未开工): 批 3 —— 节 3 + 节 4 → `test_web_traffic_qb.py`(18 fn) + `test_web_backend_misc.py`(37) + `test_web_hr.py`(51), 共 106 fn; 迁后跑 `test.one` 三新文件 + `test.quick`(计划批 3 无 `test.full` 里程碑)。
- 批通用命令: `uv run python scripts/split_test_web.py --out-dir tests --rewrite-source --emit-conftest tests/conftest.py --files <逗号分隔> --expect-fn <当前源函数数> --expect-entries <当前源条目数> --collect`(conftest 已含 `web_env`, 幂等跳过; `--expect-*` 按当前源填, S5 应为 **245 / 229**——已用 AST 现算)。

## 未决项

- 全仓活引用 ~18 处(`src/auto_qb/webui/**`、`static/shared/*.js`、`e2e/*.mjs`、`scripts/ui_harness.py`)指向 `test_web.py` —— **S8 全仓验收 grep** 统一处置(多数指向后续批才迁的函数, 现在改会指向尚不存在的文件)。
- 节 3 杂项里的 6 个 HR 系测试留在 `test_web_backend_misc.py`; 若并入 `test_web_hr.py`, 说一声即可。
- P-03(次大文件 test_hr_service 等续拆)按计划另立, 不混入本批。
- `scripts/split_test_web.py` 去留: 计划 S7 说「迁完删」(若想留作以后复用, 批 commit 前提出)。
