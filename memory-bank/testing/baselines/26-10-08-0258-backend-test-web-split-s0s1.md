# 2771 —— test_web.py 拆分 S0–S1(建档 + 勘察映射)基线

> 摘要: 专题 test-web-split 的 S0–S1 收口 —— 纯文档轮(新增任务档案含 329 fn 全量映射表 + P-01/P-02 拍板 + 更新切片/索引), `tests/` 与 `src/` 零改动 ⇒ 相对上基线 26-10-08-0223(2771+4)逐位持平。本切片作为该拆分专题的开工基线(committed HEAD `feat/test-web-split`)。
> 档案: memory-bank/tasks/26-10-08-backend-test-web-split.md
> 基线时间: 2026-10-08 02:58

**Refs:** memory-bank/tasks/26-10-08-backend-test-web-split.md

## test.full 实测

- 分支: `feat/test-web-split`(自 `34356f49` 起; 工作树含本专题回写件时实测)
- 命令: `commands run test.full`(Windows, 单次采样 —— 耗时口径见 testing/baseline.md「必须带区间」)
- **实测 (Windows)**: **2771 passed + 4 skipped, 0 failed, 56.3s, 覆盖率 TOTAL 99%**
  (16476 语句 / 165 未覆盖 / 5694 分支 / 149 partial; 门槛 98% 达标)
- 相对上基线 [26-10-08-0223](26-10-08-0223-test-webui-peers-harness.md)
  (2771 passed + 4 skipped @ 58.1s, 同 16476 语句 / 165 未覆盖 / 5694 分支 / 149 partial):
  passed **±0** / 语句 **±0** / 未覆盖 **±0** / 分支 **±0** / partial **±0**。
- 增量明细: **零 pytest 侧改动** —— 本轮只增/改 `memory-bank/` 文档(任务档案 + 切片 + 索引生成物),
  均不进 `testpaths(tests/)`。4 skipped 为 Windows 侧 POSIX 专属存量。
- 同树复测区间: 53.6s ~ 57.5s(同日两次采样; 单次数字不单独作基准)。

## 本专题面要点(非 pytest)

- 纯文档轮: 新增 `memory-bank/tasks/26-10-08-backend-test-web-split.md`(S0–S8 执行档案, 含 329 fn
  全覆盖映射表 + 共享件归属 + P-01/P-02 拍板结果); 更新 activeContext 切片与 `tasks/_index.md`。
- 拆分尚未落码(S2 起才动 `tests/`); 本切片即该专题的**开工基线**。
- 勘误(本轮实测): 计划口径 323 函数 / 306 docstring 条目 / 基线 2757 均已陈旧 → **329 / 312 / 2771**;
  节 3 内容异质(55 fn 仅 18 是流量) → 拍板**拆两份**, 目标文件 15→**16**。

## 对照判据(后续沿用)

- 以本切片(2771+4 / 16476 / 165 / 5694 / 149)为对照点: 预期 passed 只升不降、未覆盖 / partial 不升。
- 拆分各批(S2–S7)以「函数集合恒等(329)/ docstring 条目守恒(312)/ pytest 收集数恒等(337 项)」
  为主判据, passed 与覆盖率应保持不降。
