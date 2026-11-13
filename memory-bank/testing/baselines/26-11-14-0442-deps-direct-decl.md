# 6086 —— requests 直接依赖声明基线

> 摘要: requests/anyio/starlette 裸 import 显式化批(issue 26-11-12-0739): test.full 6086+19 覆盖 99%
> 基线时间: 2026-11-14 04:42

## 验收数字

`commands run test.full` 实测(Linux 宿主, issue 26-11-12-0739 修复收尾, 基线时间即建件时点):

- 汇总行: `6086 passed, 19 skipped in 116.36s (0:01:56)`
- TOTAL 表: `27115 stmts / 219 miss / 9480 branch / 89 miss / 99%`
- 对照上切片(26-11-14-0136, 6085+19 同宿主): 本批零新增测试, +1 passed 来自开工快进的
  远端 10 笔提交面, 非本批引入; skipped 组 19 与同宿主一致
- 依赖面零版本变更: requests/anyio/starlette 三包 uv.lock 锁定版本与本批前完全一致,
  仅根包 dependencies/requires-dist 与 dev 组登记(纯声明显式化)

## 本改动面

- `pyproject.toml` — requests==2.34.2 进 dependencies(issue 主修面); anyio==4.15.1 /
  starlette==1.10.0 进 dev 组(顺带排查同款脆弱面)。
- `uv.lock` — 根包登记三包直接依赖(零版本变更); revision 3→5 为本地 uv 0.13.7 经
  env.sync 的固有格式抬升, 机械面。
- `.agents/skills/deps-upgrade/project/impact-map.md` — §1.2 直接依赖清单事实回写。
- `memory-bank/issues/26-11-12-0739-chore-requests-direct-decl.html` — 翻 Done + §05 修复后补充。
- `.agents/skills/deps-upgrade/project/impact-map.md` §1.1/§1.3 与 `deps.toml` current —
  qbittorrent-api 钉值漂移修正(2026.8.1→2026.10.1, 与 pyproject 实钉对齐; 用户授权 doc drift,
  评审轮 3 发现), 随本批附带入库。
