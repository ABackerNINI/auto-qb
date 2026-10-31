# 4302 passed + 2 skipped —— deps-upgrade 例行巡检 9 包零码 bump 后全量

> 摘要: deps-upgrade 例行巡检(2026-10-31), 逐包零码 bump 9 个 pin 型依赖(pytest 直依赖 + 8 个锁内传递依赖), 每包 test.full 验证全绿; 4 条 major/0.x 降档升级已入池 issue(专题 deps-upgrade-2026-10)
> 基线时间: 2026-10-31 08:37

## 验收数字

`commands run test.full`(pytest `-n 4 --cov=src --cov-branch --cov-fail-under=99`(pytest.ini addopts); 2026-10-31 实测, 全量 143.92s, 建档 08:37):

```
  TOTAL                                                21803     145   7400    121    99%
  4302 passed, 2 skipped in 143.92s (0:02:23)
```

- 汇总行: **4302 passed + 2 skipped(Windows)**; 覆盖率门槛 99% 通过(TOTAL 行 99%)。
- 逐条口径注记: 纯依赖抬升, 代码与测试文件零改动; 语句/分支总数与 bump 前各轮逐位一致
  (miss 145 vs 148、partial 121 vs 122 为并行覆盖率采集抖动, 同树多轮在 145-148 间波动)。
- 逐包验证: 9 个包每包 bump 后各跑一次 test.full, 全部绿(记录于会话过程, 数字同树同量级)。

## 本改动面

- `pyproject.toml`: pytest pin 9.1.1 → 9.2.0(唯一有 pin 变更的直依赖)。
- `uv.lock`: 传递依赖 8 包逐个 `uv lock --upgrade-package` 抬升 —— certifi 2026.10.23 /
  charset-normalizer 3.5.2 / coverage 7.17.0 / idna 3.20 / iniconfig 2.3.1 /
  platformdirs 4.14.0 / pluggy 1.7.0 / urllib3 2.8.0。
- `memory-bank/issues/`: 新入池 4 条 chore(26-10-31-0830 前缀, fastapi+uvicorn / filelock /
  pillow / pyobjc)+ `_index.md` 重建物。
- 未动: fastapi / uvicorn / filelock / pillow / pyobjc 五项 major/0.x 降档, 已入池等人工认领。
