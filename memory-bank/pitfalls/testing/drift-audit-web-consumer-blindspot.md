# 漂移体检盲区: glob 只盖产品模块面, 漏数据消费面

> 摘要: 真机片漂移体检若只按产品模块 glob 核对面, 会漏掉用例实际消费的 WEB 端点/store 形态 —— 形态类漂移(字段改引用式/加键)单测全绿、产品零回归, 只有真机面炸; RM04 片A 实测: 体检判「需改造 0」, 实跑 18/21 用例过时。
> 触发: 漂移体检, 漂移排查, 体检 glob, WEB 读面, 数据消费面, members hash 引用式, P-02, 用例过时, 需改造预判, 真机体检
**Added:** 2026-11-17 08:44 (RM04 片A 轮实测证伪, 切片 26-11-17-0756-real-rm04-sliceA)
**Refs:** memory-bank/testing/real-machine.md §07, memory-bank/plans/26-11-11-0630-plan-webui-group-hash-ref.html, memory-bank/testing/real-baselines/26-11-17-0756-real-rm04-sliceA.md

## 事故形态

RM04 片漂移体检(plan 26-11-17-0636 §02)按片 glob(relocate_mod/relocate_units/grouping_mod/torrents/relocate_journal/alias_fs)判定, 结论「用例面零漂移、需改造 0 条」。片A 实跑 **21 条里 18 条 FAIL, 全部用例过时**(产品回归 0): 最大族群(15 条)死于 `/api/groups` 的 members 字段改 hash 字符串数组(P-02 二期 hash 引用式, 计划 26-11-11-0630)—— `views_group.py` 改动**不在 RM04 片 glob 内**, 体检根本没看过它。

## 根因

- 体检把「片」等同于「产品模块 glob」, 但真机用例的数据面大量来自 **WEB 读端点/store 形态**(测试 helper 消费 API 返回结构), 这些消费面文件不在 glob 里, 形态变更(哪怕纯展示层重构)直接打爆用例。
- 评审 R2 在轮 1 已警告「WEB 读面可能不在体检面」(未列正式发现), 轮内没升级 —— 判据面缺陷的警告应升格为发现, 不留口头。

## 坑传递要点

- 漂移体检的面 = 产品模块 glob ∪ **该片用例实际消费的数据面**(WEB 端点 handler / store 键形态 / truth.cls 真值形态); 后者从用例的断言取数点反查(哪些端点/哪些状态键), 逐个纳入 `git log <base>..HEAD` 核对面。
- 「需改造 0 条」的预判必须写依据(取数点清单), 不能只写结论; 片A 的反例: 0 改造预判 → 实测 18/21 要改造。
- 形态类漂移(字段改引用式/加键/加视图)不改变产品行为, 单测全绿 —— 只有真机/端到端面会炸, 恰是真机轨体检要抓的。
