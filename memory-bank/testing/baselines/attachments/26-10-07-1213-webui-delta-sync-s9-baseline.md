# 2744 —— WebUI rid 式增量同步实施计划 S9 关键步基线 (feat/webui-delta-sync, 追剧重聚合 + show 视图解锁)

> 摘要: 计划 [26-10-07-0414-plan-webui-delta-sync.html](../../plans/26-10-07-0414-plan-webui-delta-sync.html)
> S9 关键步(本步 = S9b: 时间线 show 桶启用 + 剧键局部重聚合 + show 视图 delta 解锁)落地后重立
> test.full 基线, 对比 S4 基线(2720+4 / 40.11s / 99%)。
> 基线时间: 2026-10-07 12:13

**Refs:** memory-bank/plans/26-10-07-0414-plan-webui-delta-sync.html,
[26-10-07-0805-webui-delta-sync-s4-baseline.md](26-10-07-0805-webui-delta-sync-s4-baseline.md)

## test.full 实测

- 分支: feat/webui-delta-sync(本地分支, S9 关键步不做 sync; 工作树含 S9b 未提交改动时实测)
- 命令: `commands run test.full`(Windows, 单次采样 —— 耗时口径见 testing/baseline.md「必须带区间」)
- **实测 (Windows)**: **2744 passed + 4 skipped, 0 failed, 32.47s, 覆盖率 TOTAL 99%**
  (16254 语句 / 166 未覆盖 / 5684 分支 / 150 partial; 门槛 98% 达标)
- 相对 S4 基线 [26-10-07-0805](26-10-07-0805-webui-delta-sync-s4-baseline.md)
  (2720 passed + 4 skipped @ 40.11s, 16017 语句 / 167 未覆盖 / 5560 分支 / 147 partial):
  passed **+24** / 未覆盖 −1 / 分支 +124 / partial +3。passed 增量归因: S5-S9a 五步入库的
  新增守阵测试函数 18 条(S5 镜子 11 + S6 等价/引用 2 + S8 剧键映射 4 + S9a 单剧可调用 1,
  中间步非关键步不立切片) + 本步 S9b 新增 6 条(delta 文件 3: 局部重聚合等价/引用稳定、
  show 视图归约、折叠面降级; 镜子文件 3: M10 成员迁移、M11 季级 gaps、M12 剧名频次);
  语句总数 16017 → **16254**(+237)超出在账 ±200 摆动簇, 全部来自 S9b 的服务端增量接线
  (runtime.py show 桶推导/局部重聚合/折叠面检测/归约分支)与上述守阵, 逐条有测试对应。
  4 skipped 为 Windows 侧 POSIX 专属存量, 与在账一致。
- 耗时 40.11s → 32.47s: 单次采样含机器噪声, 不作收益判据(量级收益以 S10 真机分档实测为准)。
- e2e 轨: 本步未重跑(计划把 e2e 复测归档排在 S10; 对照点沿用 S4 切片
  dev.e2e 90 passed / 10 skipped / 0 failed, delta-sync.spec 6 条)。

## S9b 步改动面(对照判据的"该段改动")

- `src/auto_qb/webui/runtime.py`(核心接线):
  - 时间线 show 桶启用: `_drain_delta_locked` 推导剧键 —— removed 成员旧键在 S8 映射清理
    **前**捕获、added/delta_fields 新键在映射更新**后**现算, 两个方向都进 upsert(重建候选);
    `_merge_pending_show_migrations_locked`(新)把 S8 迁移暂存两侧并入 show 桶后清空
    (「候选允许过宽, 重聚合按当前库态定行止」)。
  - `_publish_locked`: 键集定型段并迁入; `has_keys` 接入 show 桶; **折叠面检测器**(新,
    R11): 变更 hash 用全量同款 `_parse_show_member` 分类, 「现分类未识别」≠「原居折叠区」
    或被删 hash 原居折叠区 → `show_unrecognized` 本代 full(协议无未识别桶, S4 前端 delta
    轮对 unrecognized「不动」); 精确不放大 —— 静止未识别种子(下载中的电影)抖动不触发。
    全量路径按现视图行止校准 show 桶(无行的重建候选: 原居旧视图转 removed / 纯未识别键撤候选)。
  - `_publish_partial_locked` show 分支(新): 脏剧键经 `_show_member_keys` 反查成员集 →
    逐成员 `_parse_show_member` 重解析(KIND_UNKNOWN 剔出剧行, 与全量分类对齐) →
    `_build_show_row` 整行重建; 全删剧(重算无成员且原居视图)转 removed; 未脏剧行引用
    原样保留(四视图同轮发布硬约束不破); pending 文件兑底接线同款(True 侧)。
  - 启用矩阵翻开: `_DELTA_VIEWS` 加 show; `_reduce_delta` show 归约(up_s/rm_s 窗口并集、
    R5 跨代抵消、缺行防御 full、removed.shows 回剧键; show 视图连带 groups/singles 桶)。
- `src/auto_qb/webui/views.py`: 零改动(S9a 已备好 `_parse_show_member`/`_build_show_row` 接缝)。
- 前端: 零改动(S4 `applyStateRows` 已按通用合并实现 shows 桶行级合并, 本步起服务端开始供给)。
- 测试: `tests/test_webui_delta.py` 扩 S9b 三用例 + 启用矩阵/JSON 守阵/S8 暂存消费断言改写;
  `tests/test_webui_delta_mirror.py` 断言器扩 show 视图(DeltaClient 认 {list, unrecognized}
  形状 + unrecognized 增量轮不动语义), M8 改写为「show 已启用且增量正确」, 新增 M10-M12,
  fuzz 加 show 客户端(操作序列与 rng 种子不变, 三客户端每轮 B ≡ A)。

## 正确性边界 1-4 落位(M10-M12 守阵)

- 边界 1 成员迁移: M10 —— 多成员剧旧剧行重建为减员内容(直剔会漏行, 暂存两侧都作重建候选),
  单成员剧旧剧行 removed + 新剧行 upsert。
- 边界 2 季级聚合: M11 —— 同剧某集变化, 该 (剧,季) covered/gaps 整季重算(补齐清空/删除重现)。
- 边界 3 剧名频次: M12 —— 展示名(众数)按当前成员集局部重扫, 频次反超即翻转。
- 边界 4 状态归并: 集行 state 取 min 本就剧内局部, 随 `_build_show_row` 整行重建携带
  (`_s9b_show_partial_rebuild_equal_and_reference_stable` 的局部/全量逐字段等价覆盖)。

## 对照判据(S10 沿用)

- 以本切片(2744+4 / 16254 / 166 / 5684 / 150)为 S9 后对照点: 预期 passed 只升不降、
  未覆盖 / partial 不升; 回退先查该段改动。应急回退单点: `_DELTA_VIEWS` 去掉 show
  (单行, 回 S8 态)。
- e2e 对照点: S10 复测归档时以 S4 切片 e2e 段为 before。
- 量级收益(服务端重建段)以 S10 真机分档实测对照 S0 切片「before」段。
