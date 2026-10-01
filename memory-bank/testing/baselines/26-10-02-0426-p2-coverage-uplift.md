# 基线 · 2278 passed + 3 skipped / 99% —— 测试覆盖率提升 P2 收官(P2-a 长尾 + P2-b tray 攻坚)

> 摘要: 计划 26-10-01-2157(测试覆盖率提升 91%→96%)P0–P2 三阶段收官基线 —— P2-a core/torrents/rules 长尾清偿 + P2-b tray 逻辑缝攻坚落地, 综合覆盖率 96.49% → 99.06%, 大幅越过计划 96% 终点, 计划转 Done。
> 档案: [plans/26-10-01-2157-plan-test-coverage-uplift.html](../../plans/26-10-01-2157-plan-test-coverage-uplift.html)。
> 基线时间: 2026-10-02 04:26, develop @ 1c237504(阈值抬 98 后 test.full 复跑实测; 工作树含本笔收尾回写与阈值改动, 未提交)。
> Linux 侧: 待补(仅 Windows 侧重测, 见 baseline.md 常驻警告 —— 两侧都重测前不当作两侧事实源)。

TOTAL **2278 passed + 3 skipped / 99%**(13284 语句 / 83 未覆盖 / 4424 分支 / 82 partial,
test.full 30.09 / 30.26s 两采样, rc=0)。**精确综合口径**(coverage json 导出, 行 + 分支出口合计):
**17,541 / 17,708 = 99.06%**(语句 13,201/13,284 = 99.37%, 分支 4,340/4,424 = 98.10%)。
相对 P1 基线(26-10-02-0203: 17,196/17,822 = 96.49%)**+345 已覆盖单位**;
分母 −114(P2-b tray 4 处 pragma 豁免排除为主 —— 仅 tray/app.py 即排除 165 行/88 语句,
期间合流的远端提交 bc24631b / 54db09f2 带入少量新代码部分抵消, 并各带自带测试)。
**tray/app.py 行覆盖 36% → 98.43%**(254 语句缺 4, 验收线 ≥60% 大幅越过);
全仓 pragma 豁免 2 处/52 行 → **6 处/217 行**(P2 新增 4 处逐块注明理由, 台账进入记录面)。

## 三阶段 commit 链与改动面 (测试覆盖率提升全程: 只补测试, 产品代码零改动)

- **P0 快赢轮 f6c3f239**(10-02 00:28): T0.1–T0.7 纯逻辑与 A 类整块空洞, 90.83% → 93.24% →
  切片 26-10-02-0025-p0-coverage-uplift(阈值 92)。
- **P1 服务与路由层 29f1841a**(10-02 02:06): T1.1–T1.4 hr 错误路径系统补齐 + hr/webui/infra
  二线长尾, 93.24% → 96.49%(hr 包行覆盖 99.71%) → 切片 26-10-02-0203-p1-coverage-uplift(阈值 94)。
- **P2-a 长尾清偿 8b7831cd**(10-02 03:37): T2.2+T2.3 core/modules(ops_mod / grouping_mod /
  qbmanager / rules_mod / maintenance_mod / tvshows) + torrents + rules/actions, 96.49% → 97.53%(+186 单位)。
- **P2-b tray 攻坚 1c237504**(10-02 04:18): T2.1 tests/test_tray.py 新建(45 函数/59 例) ——
  UiLogHandler 边界 / IPC 端口文件协议(写读残) / poll 队列消费 / 状态→UI 映射 headless 逻辑缝全清;
  widget 主体 4 块(_build_window / _card / _build_tray / run)逐块 `# pragma: no cover` 并注明豁免理由。
- **P2-c 收尾(本笔)**: 阈值 94 → 98 + 本切片 + 计划 HTML 三处转 Done; 只动 pytest.ini 与
  memory-bank/, 测试与产品代码零改动。

## 红验汇总 (三阶段累计 25/25)

- 变异红验全部当场红、逐条精确还原(还原后 `git status src/` 干净): P0 6/6 · P1 7/7(含两轮
  mutant 选点修正: bencode 夹具按 unreached-branch-guard 收紧、commands 补齐维度换种子) ·
  P2-a 7/7(含抓到一处假绿后收紧夹具) · P2-b 5/5。

## 阈值与防回沉

- P3-M1 阈值随本切片抬起: pytest.ini `--cov-fail-under` 94 → **98**(实测 99.06% − 1 个点的整数档,
  口径见计划 §5「阈值永远 = 当期实测 − 1 个点」单点规则; 计划 P2 DoD 字面预估档 95 是按 96% 终点
  倒推的, 实测已大幅越过, 以 §5 为准; 抬后 test.full 复跑全绿确认阈值生效; test.quick 的
  --no-cov 豁免不动)。
- 豁免治理(§5): 全仓 pragma 2 处/52 行 → 6 处/217 行, P2 后进入基线切片记录面, 只减不增。
