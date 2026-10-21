# 3995 passed + 2 skipped —— ts 推进断言粒度坍缩 flake 修复后全量基线(0 failed)

> 摘要: ts 推进断言粒度坍缩 flake 修复后全量基线(0 failed)
> 基线时间: 2026-10-22 01:21
**Refs:** memory-bank/pitfalls/testing/time-tick-collapse-strict-advance.md

## 验收数字

`commands run test.full` 实测(裸数字只写本切片这一处):

- 汇总行: **3995 passed, 2 skipped in 142.67s** —— **0 failed**(上一条基线 26-10-22-0102 的唯一 failed 即本条修复对象)
- 覆盖率: TOTAL **99%**(命令输出显示精度到整数)

逐条口径注记:

- 修复对象 `tests/test_traffic_snapshot.py::test_publish_event_patches_day_row_without_reading`: 本机背靠背 `time.time()` 同值(亚 µs 粒度坍缩) → `assert tv["ts"] > before_ts` 偶发相等假红; 修法为该用例钉每次 +1s 递增假钟
- 验证: 该用例连跑 20 遍全绿; 假钟临时改回常量精确复现原 flake 断言(红验); 整文件 19 passed
- 同形态排查(2026-10-22 追加): `tests/test_traffic_monitor_client.py:641`(`view["ts"] > ts_before`)形状相同但**不是**本坑 —— 探针实测 `ts_before` 取自 `_refresh_env` 种进视图的字面量 1.0, 断言实为「新发布 ts > 1.0」, 天然稳, 无需修; 判别锚点(追基线值来源)已写进坑档

## 本改动面

- `tests/test_traffic_snapshot.py` —— 唯一改动文件: 该用例入口钉递增假钟(`monkeypatch.setattr(time, "time", ...)`, 每次调用 +1.0s, 起始值取一次真钟); 文件头 `import time` 补齐; 用例 docstring 写明为什么必须假钟
- `memory-bank/pitfalls/testing/time-tick-collapse-strict-advance.md` —— 新坑档: 触发/判别/处置/守阵四段(与 timing-tolerance 的 OS 刻度余量形态区分的判别锚点: 失败值是两值完全相同而非差几毫秒)
- 随同笔提交 `c6b2f5e3` 一并入库的还有午夜窗口抖动修复(notify 导入时求值 + qb 00:00:00-00:00:30 几何分档)与坑档四次实证回写 —— 修 ts flake 时提交闸门被它挡下, 两件合并为一笔
