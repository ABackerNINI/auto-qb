# 2771 —— WEB UI 后端测试单文件拆分 S7–S8(收官)基线

> 摘要: 专题 test-web-split 的 S7–S8 收口 —— S7 批 5(节 10–15 → 4 平铺模块, 45 fn)落地 + `tests/test_web.py` 删除(拆分收官), 外加 S8 全仓活引用改指新文件(活代码/活文档 0 命中)与 kb 回写。纯机械迁移 ⇒ 相对开工基线 26-10-08-0258(2771+4)逐位持平。本切片即该拆分专题的收官基线。
> 档案: memory-bank/tasks/26-10-08-backend-test-web-split.md
> 基线时间: 2026-10-08 05:18

**Refs:** memory-bank/tasks/26-10-08-backend-test-web-split.md

## test.full 实测

- 分支: `develop`(工作树含本专题回写件时实测)
- 命令: `commands run test.full`(Windows, 单次采样 —— 耗时口径见 testing/baseline.md「必须带区间」)
- **实测 (Windows)**: **2771 passed + 4 skipped, 0 failed, 50.97s, 覆盖率 TOTAL 99%(98.56%)**
  (16476 语句 / 165 未覆盖 / 5694 分支 / 149 partial; 门槛 98% 达标)
- 相对开工基线 [26-10-08-0258](26-10-08-0258-backend-test-web-split-s0s1.md)
  (2771 passed + 4 skipped @ 56.3s, 同 16476 语句 / 165 未覆盖 / 5694 分支 / 149 partial):
  passed **±0** / 语句 **±0** / 未覆盖 **±0** / 分支 **±0** / partial **±0**。
- 增量明细: 拆分全程零 pytest 侧净增删 —— 329 函数由 `tests/test_web.py` 一文件平铺为 16 模块
  (auth / api_core / webui_static_skins / webui_static_dom_panel / webui_static_dom_page / traffic_qb /
  backend_misc / hr / commands / views_reload / admin / seed_center / route_manifest / keys /
  skip_check / longtail), 集合恒等、各恰存活一次。4 skipped 为 Windows 侧 POSIX 专属存量。
- 同树复测区间: 33.1s ~ 50.9s(同日多次采样; 单次数字不单独作基准)。

## 本专题面要点(非 pytest)

- 收官: `tests/test_web.py`(拆分前 14,556 行 / 329 fn)**已删除**; 16 个平铺模块在位(最大
  `test_webui_static_dom_panel.py` 2,230 行, 全部 ≤2,500 行硬上限); 共享件 `tests/webui_helpers.py`(436)
  与 `tests/conftest.py`(217) 就位。
- S7 末批首验「删除源文件」模式, 暴露并修复一次性工具第 6 处缺陷(collect 面误收集整个 out-dir);
  坑档 [tool-mode-coverage](../../pitfalls/testing/tool-mode-coverage.md) 补第三面 + 复发 +1。
- 一次性拆分脚本按用户拍板保留复用: `scripts/split_test_web.py` → `memory-bank/archive/split_test_web.py`。
- S8 全仓活引用改指新文件(活代码/活文档 0 命中); 历史档案/快照(plans / reports / baselines / 旧任务档案 /
  progress 流水 / issues)按计划 §08 不改。

## 对照判据(后续沿用)

- 以本切片(2771+4 / 16476 / 165 / 5694 / 149)为对照点: 预期 passed 只升不降、未覆盖 / partial 不升。
- 拆分已收官; P-03(次大文件 test_hr_service 2,464 / test_traffic_sample 2,125 / test_grouping 1,859
  续拆)按计划另立, 复用 `memory-bank/archive/split_test_web.py`。
