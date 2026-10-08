# 2772 —— 认领复验 issue 26-10-08-0818 基线(判为重复报告, 零代码改动)

> 摘要: 用户指派「认领并修复」issue [26-10-08-0818](../../issues/26-10-08-0818-test-webui-e2e-stub-fidelity-s7-memo.html)
> (e2e 存量 6 条失败)。认领后**先复验锚点** —— `commands run dev.e2e` 实测 **94 passed / 10 skipped /
> 0 failed (3.2m)**, 6 条失败全数复绿。逐条对账: 两条根因均已在本件入池取证(10-07 13:36)之后、
> 入池(10-08 08:18)之前由 `312165f8`(FakeTorrent.to_dict 快照分则)+`17dc0fc7`(装饰记忆化输入指纹)
> 按建议修法修复, 故本件为**重复报告** → 关 Done。**本会话零代码改动**(仅改 memory-bank 文档:
> issue 状态 + activeContext 切片 + S10 基线追记), 故 pytest 面数字**逐位持平**(只作收尾留痕)。
> 相对上基线 26-10-08-0713(2772+4, 同 16476/165/5694/149): 全档 ±0。
> 基线时间: 2026-10-08 08:39

**Refs:** memory-bank/issues/26-10-08-0818-test-webui-e2e-stub-fidelity-s7-memo.html, [26-10-07-1336-webui-delta-sync-s10-baseline.md](26-10-07-1336-webui-delta-sync-s10-baseline.md), [26-10-08-0713-webui-qb-traffic-head-layout.md](26-10-08-0713-webui-qb-traffic-head-layout.md)

## test.full 实测

- 分支: `develop`(工作树含本专题回写件: issue HTML / 切片 / S10 基线追记 —— 均 memory-bank 文档)
- 命令: `commands run test.full`(Windows, 单次采样 —— 耗时口径见 testing/baseline.md「必须带区间」)
- **实测 (Windows)**: **2772 passed + 4 skipped, 0 failed, 31.40s, 覆盖率 TOTAL 99%**
  (16476 语句 / 165 未覆盖 / 5694 分支 / 149 partial; 门槛 98% 达标)
- 相对上基线 [26-10-08-0713](26-10-08-0713-webui-qb-traffic-head-layout.md)
  (2772 passed + 4 skipped @ 34.76s, 同 16476 / 165 / 5694 / 149):
  passed **±0** / 语句 **±0** / 未覆盖 **±0** / 分支 **±0** / partial **±0**。
- 增量明细: **未新增测试函数** —— 本会话零代码改动(tests/ 与 src/ 未动), pytest 面数字必然逐位不变;
  本切片只为收尾留痕与「认领→复验→裁定」事实锚。4 skipped 仍为 Windows 侧 POSIX 专属存量。

## e2e 复验实测(本会话核心证据)

- 命令: `commands run dev.e2e`(桩环境 `scripts/ui_harness.py`, 默认 300 档, chromium 1440x900)
- **实测: 94 passed / 10 skipped / 0 failed (3.2m)** —— S10 基线记录的 6 failed 全数复绿。
- 与 issue 预期「92 passed」的差: +2 条, 是 S10 之后新增 `e2e/drawer-peers.spec.mjs`
  (双皮肤 @fast, 计划外小步 26-10-07-2309)所致, 非根因相关。**后续 e2e 对照点以 94/10/0 为准**。

## 本专题面要点(非 pytest)

- 根因 A(`312165f8`, 2026-10-07 14:13): `FakeTorrent.to_dict` 弃 `vars()` 全导出, 改按
  `compat._SNAPSHOT_FIELDS` 只导快照字段 —— 非快照字段 `hr_link`(HrRuntime 桥引用)不再进 JSON,
  `/api/torrents/{hash}` 不再恒 500。现 `tests/helpers.py:679` = `{f: getattr(self,f) for f in _SNAPSHOT_FIELDS}`。
- 根因 B(`17dc0fc7`, 2026-10-07 14:13): `decorate.js` 的 `_decoCache` 条目带输入指纹
  (`_decoFpBuild`/`_decoFpHit`, 覆盖 `members` 引用 + 逐成员 `kind/size/category/site/tags` + 首成员
  `save_path`), 命中前逐槽比对 —— 乐观补丁原地 `Object.assign kind` 后指纹失配即重算回填,
  组行 `status.primary` 恢复随乐观值传导。`commands.js` 零改动(计划零改动区)。
- 两修复均 `git merge-base --is-ancestor <sha> HEAD` 成立(已在主线 develop)。

## 对照判据(后续沿用)

- 以本切片(2772+4 / 16476 / 165 / 5694 / 149)为对照点: 预期 passed 只升不降、未覆盖 / partial 不升。
- **e2e 对照点**: `dev.e2e` **94 passed / 10 skipped / 0 failed**(取代 S10 基线的 86/10/6)。
