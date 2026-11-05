# 5462 passed + 2 skipped in 150.52s (TOTAL 24538 stmts, 99% cover, 36 miss; 评审修复轮 95a5a09a 后, 含远端合流面) —— S6 收口评审修复轮全量基线

> 摘要: S6 收口评审修复轮全量基线
> 基线时间: 2026-11-06 04:27
**Refs:**

## 验收数字

- 汇总行: **5462 passed + 2 skipped** in 150.52s(0:02:30, xdist 并行, TMPDIR 由 tests/_tmp_bootstrap.py 自举)。
- 覆盖率 TOTAL 表末行: **TOTAL 24538 stmts / 36 miss / 99%**(Windows 侧覆盖闸 99.0, PASS)。
- 口径注记: 相对上基线(26-11-06-0236, 5392)净增 70 = 本轮评审修复 +10(hatch_build 7 / 管线补测 10-7 / suggest 默认链 2 等) + 远端合流面(另一 clone 的 msg_check 收口评审与 sandbox-venv 坑档轮新增用例); 全绿, 副作用越界 0(test.quick 5427 侧复核过)。
- 差值对比: `commands run kb.baseline -n 2`。

## 本改动面

- S6 收口评审修复(基线 commit 95a5a09a, 分面档三面 27 条全修):
  - `release.merge` args 占位二跑形态 + SKILL ⑤ 两跑口径(发版轮 github 推送机械落点);
  - `release_page.py`: and/or 优先级 bug 修复 / Authorization Bearer 头(token 不进 URL)/ --tag 形态校验;
  - `ff_merge.py` rev-parse 剥 annotation / `ci_gate.py` JSON 解析异常收口 + rc 语义 / `hatch_build.py` atexit 兜底 / `suggest_bump.py` run_git timeout / `apply_bump.py` sync 失败恢复指引;
  - `SKILL.md`: ② 补 test.linux / ⑧ 发布件停留说明 / 删除「ship.push 已保证」虚假声明;
  - `.commands/release/scripts/test_release_pkg.py` 守阵升级(when+note 双扫 / 7-task 集合 / 项目事实钉死 / 旗标一致性扫描 / 钩子接线);
  - `tests/test_hatch_build.py`(新, 7 条)/ `tests/test_release_pipeline.py`(+10)/ `tests/test_release_suggest_bump.py`(+2)。
- 另: 入池 issue 26-11-06-0321(Windows CI 存量红, 双向认领链挂计划); gh CLI 安装(winget 2.103.3, token 用户自理)。
