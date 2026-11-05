# 26-11-05-backend-hr-fetch-gating — HR 取数侧强制 fetchable: 全站型(listing=none)不取数清偿 issue 26-10-05-0922

**Status:** Done
**Added:** 2026-11-05
**Updated:** 2026-11-05
**Summary:** 清偿 issue 26-10-05-0922: fetchable 原全仓零消费方, 新增 fetchable_sites() 取数集合单点, 三处取数入口(refresh_all / worker.run_once / request_refresh)改按「enabled 且清单型」受理; 展示/状态/判定口径不动
**Topics:** backend-hr-fetch-gating
**Refs:** memory-bank/issues/26-10-05-0922-refactor-hr-fetchable-dead-config.html

## 原始请求

1. 「认领issue. 旧issue清偿, 先验问题是否还存在:26-10-05-0922-refactor-hr-fetchable-dead-config.html」
2. 复验确认问题仍在后, 用户 AskUserQuestion 拍板: 「接上取数侧强制 (推荐)」—— 落地「全站型(listing=none)不取数」的设计意图, 不删字段。

## 思考过程与决策

- **复验(2026-11-05)**: fetchable 已由字段改 property(models.py), src 消费方仍零; enabled_sites() 仍只按 enabled 过滤(worker.run_once / refresh_all 都走它); 判定侧 resolve.py 已尊重 listing=none; preset 仍无 listing="none" → 潜在缺口原样, 非现行缺陷。
- **方案取舍**: 接上取数侧(poka-yoke, 未来 preset 出现 listing=none 时无清单页的站不会白烧配额) vs 删字段(YAGNI)。用户拍板前者。
- **口径二分(关键裁决)**: 取数口径 = fetchable(enabled 且 listing="list"); 展示/状态/判定口径维持 enabled —— 全站型照样出状态、视图照常发布(build_views 打底不依赖取数结果)、判定走 resolve 的 listing=none 恒行4分支。
- **listing=""(未绑定)语义**: 不取数(fail-safe, 无页面事实翻页必炸)。生产不可达: loaders._resolve_hr_site_bindings 对 enabled 站点必从档案派生填充 listing, validate_config 拦未绑定。测试工厂(hr_runtime_support)补 listing="list" 贴近生产形态。
- **收口评审**: 命中立档阈值(改动 3 个源文件) → code-review 全能档(93 行), 3 条 minor 引文全过、均判相关并当场修: ①走查头部/空集提示改取数口径(report.py) ②通道静默「受影响站点」改 fetchable_sites(worker.py) ③request_refresh 汇合点 note 在 requested 空时如实说明, 消除 WebUI 409 detail 自相矛盾(runtime.py)。blocker/major 清零。

## 实现计划

1. service.py 新增 fetchable_sites()(取数集合单点), refresh_all 改用它 — 独立可验: 新增过滤测试。
2. worker.py run_once / request_refresh 改按 fetchable 受理 — 独立可验: worker 级过滤测试。
3. models.py fetchable property docstring 补消费方单点指向。
4. 新增 service+worker 两条回归测试并同步测试计划 docstring。
5. 收口: code-review → test.full + 基线切片 → kb.wrap。

## 子任务状态表

| 步 | 内容 | 状态 |
|---|---|---|
| 1 | service.fetchable_sites() + refresh_all 过滤 | Done(2026-11-05) |
| 2 | worker run_once / request_refresh 按 fetchable 受理 | Done(2026-11-05) |
| 3 | models.py property docstring 消费方单点 | Done(2026-11-05) |
| 4 | 回归测试 ×2 + 测试计划同步 + 假配置补 listing | Done(2026-11-05) |
| 5 | 收口评审 + 修 3 minor + test.full 基线 | Done(2026-11-05) |

## 进度日志

### R0 · 立档 (2026-11-05)

认领并复验 issue 26-10-05-0922(仍复现) → 用户拍板接上取数侧强制 → 实现三处取数入口过滤 + 两条回归测试 → test.quick 全绿 → issue 置 Done → 收口评审(全能档, blocker 0, 3 minor 当场修)。真机轨豁免理由: 取数集合选择逻辑纯桩可验(单测全覆盖), 不涉 qB 真执行/真文件系统面。

- 2026-11-05 08:35 清偿 issue 26-10-05-0922: fetchable_sites() 取数集合单点, 三处取数入口按 fetchable 受理(展示/判定口径不动); 收口评审全能档 review: blocker 清零, 修 3, 入池 0; test.full 全绿后新建基线切片
