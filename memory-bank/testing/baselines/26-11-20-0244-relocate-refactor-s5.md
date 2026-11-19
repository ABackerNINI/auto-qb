# 6495 passed, 6 skipped —— relocate 重构第二批 S5(跨模块接口显式化)收尾全量基线

> 摘要: relocate 重构第二批 S5(跨模块接口显式化)收尾全量基线
> 基线时间: 2026-11-20 02:44

## 验收数字

`commands run test.full` 实测(2026-11-20, Windows 开发机, relocate-s5-iface @ 80d8ea09):

```text
TOTAL                                                28901     44  10308     62    99%
Required test coverage of 99.5% reached. Total coverage: 99.73%
6495 passed, 6 skipped, 8 warnings in 159.97s (0:02:39)
```

- 汇总: 6495 passed / 6 skipped / 0 failed; **覆盖率闸门达标** —— 99.73% ≥ Windows 阈 99.5(tests/conftest.py `COVERAGE_FLOOR_WIN`), 与第一批收尾(99.31% 未达)对照收敛; 耗时单次采样 159.97s(并行 -n 8, 本轮三次采样区间 135.5~160.0s)。
- 缺口净额(M8): 本片 106 单位(miss 44 + partial 62) 减上片 26-11-19-2346 的 105 单位(miss 44 + partial 61) = **+1**; 分母由语句 28915 / 分支 10322 变为 28901 / 10308(S5 批净删码 −14 语句 / −14 分支); 净额 ≤ +15 无点名 —— 本批触碰面 relocate_lifecycle 100% / relocate_units 99% / qbapi 100%, 新增面无新进榜缺口。
- 差值口径: 上一基线 [26-11-19-2346](26-11-19-2346-webui-kbd-scroll-band-rescroll.md) 6486P/6S → 本片 6495P/6S, +9 passed; 增量主体 = S5 两笔提交新增用例(S5-1 净 +3(新增 4 退役 1): ops_skip 让路专测 3 + fuse 摘句柄防御 1, quick 面 6490→6493; S5-2 守卫 `tests/test_relocate_interface_guard.py` 6 条, quick 面 6493→6499); quick/full 两跑法 skip 面不同(2 vs 6), 逐位对比读两片现算。
- 本轮两次中断轮记账: 首轮 1F = 坑档退役注记以裸 `###` 小节落盘缺 触发/判别/处置 三字段(check_kb_structure 条目守卫红, 当轮改写为三字段条目修复); 次轮 1F = `test_hr_discovery` 连号端口抢占环境性 flake(WinError 10048, Windows 动态排除段/残留占用, 非本批改动面 —— 本批零代码改动, 重跑即绿)。

## 本改动面

- 两笔提交(relocate S5 第二批, 计划 26-11-15-2340 刀3 跨模块接口显式化):
  - a652290f(S5-1 登记集退役+派生查询): store 三登记集(relocating_hashes/resuming_hashes 声明 + relocating_alias_roots 惰性动态属性)与 _sync_relocating/_sync_resuming 写入面及 7 个重算挂点整体退役; relocate_units 增纯派生函数 relocating_hashes_of/resuming_hashes_of; RelocateModule(LifecycleMixin) 增公开查询 relocating_hashes()/resuming_hashes()/alias_roots(); fuse/grouping/ops_skip/qbapi 五个直读消费点迁 ctx.relocate 句柄(getattr None→空集); qbapi 增 ctx 注入(可选参默认 None); 删链门循环改四元组解包, 旧形 str 登记分支结构性退役; 替身收敛 FakeRelocateQueries 单点; 新增 ops_skip 让路专测 3 条 + fuse 摘句柄防御用例 1 条, 退役 2 用例留注释(727 行)。
  - 80d8ea09(S5-2 常量收口+AST 守卫): TAG_PROBE 定义迁 relocate_units(probe 再导出) + units 增 is_probe_torrent(rec) 谓词, qbapi 探测豁免改谓词调用; _RESUME_RETRY_MAX 改名 RESUME_RETRY_MAX 迁 units(值 3 不动); views_relocate.py 跨层私有 import 行删除 —— 全仓 src 侧 relocate 家族私有名跨界 import 清零; units 增显式 `__all__`(顶层公开名 113 个); 新建 tests/test_relocate_interface_guard.py 四判据 AST 守卫 + 反空转共 6 条(599 行)。
- 收尾回写随本批入库, 纯文档零代码: 计划 26-11-15-2340(R4 变更行 + §06 D11-D13 + §04-S5 达成口径注记)/任务档案 S5 翻 Done/conventions/modules.md 协作先例/pitfalls/backend/derived-registry-sync-points.md 退役条目/本切片/kb.wrap 切片行。
