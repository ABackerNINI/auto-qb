# 4803 passed + 2 skipped —— 全量测试基线: 远端 77 笔并行合流后 + 合流面三条守阵重钉

> 摘要: 全量测试基线: 远端 77 笔并行合流后 + 合流面三条守阵重钉
> 基线时间: 2026-11-01 22:11
**Refs:** memory-bank/tasks/26-10-08-test-mutation-audit.md

## 验收数字

- **目标**: 全量 pytest 套件(`tests/` 全量 + `src/` 覆盖率报表), 提交态 `b3633b87`(工作树干净)
- `commands run test.full` 实测(wrapper 墙时 126.1s, 2026-11-01 22:11, Windows 本机):
  - 汇总行: `4803 passed, 2 skipped in 124.08s (0:02:04)`
  - TOTAL 表: `TOTAL  22482  164  7708  134  99%`(stmts / miss / branch / partial / 覆盖率)
  - 覆盖率闸: Windows 阈值 99, 达标
- **环境 / 工具**: Windows 本机(win32 10.0.26300 x64 · 32 逻辑核)· Python 3.13.14 · pytest 9.2.0 · pytest-xdist 3.8.0 · `addopts = -n 8 --cov=src --cov-report=term-missing --cov-branch`; `TMPDIR` 由 `test.full` 包内内置(不手工加前缀)
- **口径注记**: 全量 pytest 含覆盖率报表; 相对上基线逐位对比不写, 看差值 `commands run kb.baseline -n 2`。本条只记全量测试基线, **不放逐轮变异数字**(那属于各轮切片)。

## 本次语境

- **合流**: 本地 37 笔提交 rebase 到远端新基 `6a390e76`(远端侧新增 77 笔并行工作, `git rev-list --count 6a390e76 ^0250e2f3` 实测 77), 零手写件冲突; 工具链缺陷已入池 `26-11-01-2140`(档案 R35)。
- **三条守阵重钉(档案 R36, 提交 `b3633b87`)**: 合流带来两笔语义面变更 —— `477df090`(W3-B choose 编排块: 动作循环 `self.actions` → 构造期派生 `self.steps`)与 `e820d2bb`(issue `26-10-31-1029` 断连自动重连: 断连稳态守卫 + `_ran_line` 恢复检测门)。三条守阵写于旧基 `0250e2f3`, 逐条判为**守阵过紧、零上游回退**: rules 两条 pending 断点协议守阵注入点 `rule.actions` → `rule.steps`; qbmanager 一条 connect 替身补落 `mgr.client`(与真实现 `_note_conn_ok()` 同构)。红验三种同构变异先红后还原, 收尾 `git diff --stat src/` 为空。

## 本改动面

- 测试面: 3 条既有守阵改注入点/替身合同(零新增用例面, 不增删测试文件)。
- 零 `src/` 改动; 其余为本轮知识库面(档案 R35/R36、坑档复发、issue 入池)与切片本身。
