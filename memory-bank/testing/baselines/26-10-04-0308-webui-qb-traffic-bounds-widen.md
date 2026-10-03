# 基线切片 26-10-04-0308 — qB 流量图配置校验边界放宽 (采样 1.5s / raw 90d / rollup 无上限)

> 摘要: 用户报设置保存被 `validate_config` 拦 (sample_interval 须 >= 15s / raw_window 须 <= 259200s)。
> 三边界放宽: `sample_interval` 15s→**1.5s** 下限(采样零 qB 请求, 仅剩写放大代价) / `raw_window`
> 72h→**90D** 上限(用户接受体量换 3 个月高分辨率) / `rollup_window` 取消 90d 上限(**无上限 = 设得
> 足够久即等效永久**, 淘汰逻辑对超大窗自然不淘汰零机制改动)。连带修 24h 栅格桶宽 `int()` →
> `math.ceil`(小数间隔下 floor 取 1s 桶宽 → 采样行隔桶为空 = 伪断线); `_try_time` 整数秒报错出
> 普通数字(`_fmt_s`)。端到端冒烟 6 用例: 旧被拒组合(10S+75H)/1.5S/90D/3650D 全 PASS, 1.4S/91D/6D 拒。

- 时间: 2026-10-04 03:08 (GMT+8); 会话起点 sync 至 13e2646f(远端无更新, 基线即此)
- 分支: develop @ 13e2646f(+ 本轮未提交改动: sections.py / core.py / models.py / groups.py /
  loaders.py / traffic_grid.py / test_traffic_sample.py / test_traffic_grid.py + memory-bank 回写件)
- 命令: `commands run test.full`
- 实测: **2423 passed + 3 skipped, 29.81s, 覆盖率 TOTAL 99%**(14416 语句 / 132 未覆盖 / 4820 分支 / 105 partial)
- 相对上基线(26-10-04-0240: 2419 passed)净增 4 用例: 边界矩阵改造(旧 91D 拒 → 合法, 增 100 年合法与
  1.4S 拒) + 新增 `test_build_grid_fractional_interval_ceils_bucket_width`(ceil 桶宽)
- 未验证面: 真机(WebUI 设置页实际保存 1.5S/90D/永久窗)待用户走查; 1.5s 采样 + 90d raw 的磁盘体量
  (≈5.7 万行/天/系列)属用户拍板接受的设计取舍
