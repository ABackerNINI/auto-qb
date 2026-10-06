# 扩展选项页明细表时间缺日期 — shortTime 补月-日

> 摘要: 用户报 `hr-fetch-proxy` 扩展选项页「最近取数明细」表时间列只有 `HH:MM:SS` 缺日期。
> 根因 = `options.js::shortTime()` 只渲染时分秒, 而事件环保留最近 50 条(可设到 10000)、
> 跨天是常态。修复 = `shortTime()` 改渲染 `MM-DD HH:MM:SS`; 站点现状表「最近活动」列同用
> 该函数, 两表口径一致。**已验证, 随本轮提交入库(hash 见 git log)。**
> 最后活动: 2026-10-06 19:28

**Refs:** memory-bank/testing/baselines/26-10-06-1928-ext-shorttime-add-date.md

## 已完成(本轮)

- 定位: `grep 取数` 命中 `extensions/hr-fetch-proxy/`, 明细表渲染在 `options.js::renderEvents`,
  时间列与站点现状表「最近活动」列共用 `shortTime()`(仅 2 个调用点)。
- 修复: `shortTime()` 补 `getMonth()+1` / `getDate()` 两位前导零, 前置注释写明「事件环跨天」动机;
  函数名不动(调用点零改动)。
- 验证: `commands run test.quick` 2678 passed + 4 skipped; `test.full` 基线切片
  [26-10-06-1928](../testing/baselines/26-10-06-1928-ext-shorttime-add-date.md)。
  扩展无 JS 单测, `tests/test_extension_proxy.py` 只查函数落点, 时间格式不在守阵面。

## 待办

- (无 —— 单行修复闭环)
