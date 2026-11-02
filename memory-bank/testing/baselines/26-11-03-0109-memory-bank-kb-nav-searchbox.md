# 4906 passed + 10 skipped(根, 99%) —— kb.nav 搜索修复 + 真机守阵环境独立化后全量基线

> 摘要: kb.nav 搜索修复 + 真机守阵环境独立化后全量基线
> 基线时间: 2026-11-03 01:09

## 验收数字

`commands run test.full` 实测(根套件):

- 汇总行: `4906 passed, 10 skipped, 3 warnings in 218.61s (0:03:38)`
- TOTAL 表: `22531 语句 / 152 未覆盖 / 7732 分支 / 134 部分覆盖 / 99%`
- 口径: rebase 合入远端 `61b04b85` 后的 `e0cc7d6b` + 本轮真机守阵修复工作树上热跑; `test.one` 定向复跑 57 passed。

## 首跑红及处置

- 红: `tests/test_real_machine_safety.py::test_small_target_guard_rejects_unsafe_paths` 期望 `reparse`/`hidden`, 实际先在「拒绝对系统卷执行: C:」/「路径含 hidden/system 属性: C:\Users\...\AppData」处拒绝。该守阵由远端 `61b04b85` 新增, 受控桩分支默认依赖 `tmp_path` 所在卷与祖先目录属性; 本机 `TMP=C:` 且临时目录在 hidden 的 AppData 下, 必然误红。
- 处置: 桩分支内 `monkeypatch.setenv("SystemDrive", "Z:")` + `_get_attrs` 桩为 0 (仅 `hid` 返回 hidden), 使控制流测试不依赖环境; 复跑定向 57 passed, 随后全量全绿。

## 本改动面

- `.agents/skills/memory-bank/scripts/nav_page.html`: 搜索单点 `navSearchText()` / `navSearchQuery()` (标题 / 专题 / issue 摘要 + link + memory-bank/link), 台账/控制台频道/卡片墙统一消费; 另修 vnu 规范错误 (台账外层 `section` 改 `div`)。
- `tests/test_kb_nav.py`: 新增 `test_search_matches_file_name_and_relative_path` 并同步「## 测试计划」清单。
- `tests/test_real_machine_safety.py`: 受控桩分支环境独立化 (`SystemDrive` 桩 + 祖先属性桩), 同步头部测试计划说明。
- `memory-bank/progress/implemented-tooling.md`: 追加搜索修复落地记录。
- 数据层 `nav_data.py` / 服务层 `nav_server.py` 零改动; 未改产品 `src/`、`config.yml`、`auto-qb-data/`。

