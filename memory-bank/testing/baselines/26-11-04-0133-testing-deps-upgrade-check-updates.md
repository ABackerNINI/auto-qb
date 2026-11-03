# 5038 passed + 2 skipped(根) —— deps-upgrade 巡检脚本测试回归网全量基线(issue 26-11-03-1209 认领修复后)

> 摘要: deps-upgrade 巡检脚本测试回归网全量基线(issue 26-11-03-1209 认领修复后)
> 基线时间: 2026-11-04 01:33
**Refs:** memory-bank/issues/26-11-03-1209-test-test-deps-upgrade-check-updates-uncovered.html

## 验收数字

`commands run test.full` 实测(develop, Windows 并行 + 覆盖率):

```text
[ok] test.full (165.4s)
  TOTAL                                                23325    167   7956    152    99%
  5038 passed, 2 skipped in 163.30s (0:02:43)
```

口径: 根目录全量(`pytest.ini` 默认并行 + 覆盖率); wrapper 外层耗时 165.4s; 覆盖率闸 Windows 99.0(`tests/conftest.py` 单点)。与上基线的逐位差值看 `commands run kb.baseline -n 2`, 本文不手抄对比。上基线(gtm-day-total-inflation, 26-11-03 23:52)同为 99% 闸过, TOTAL 表行 23328→23325 的 3 语句差来自两次基线间入库的他人提交, 非本轮改动。

同轮旁证: 本轮首跑全量曾因 activeContext 切片 R 行手抄裸 passed 数字触发 2 条 KB 措辞/数字守卫红, 修正措辞后复跑全绿 —— 同一覆盖率数据行(TOTAL 表逐位相同)下, 闸门结果随是否存在失败用例翻转(失败轮报 Total coverage 98.94%, 全绿轮过 99.0 闸), 排障时先看有没有失败用例再怀疑覆盖率面。

## 本改动面

- `tests/test_deps_upgrade_check_updates.py`(新增, 21 用例): `.agents/skills/deps-upgrade/scripts/check_updates.py` 的回归网 —— `version_segments` 参数化(CalVer 前导零 / rc 预发布粘段 / v 前缀 / 位数不等 / 非数字段)、`delta_kind` 参数化(none/patch/minor/major-line/pre-tag diff/check-lower 六类 + 数字序非字典序)、watch 侧 tags 整源失败与单条日期失败降级、支持矩阵 NEW 触发行、pin 侧单 PyPI 源失败降级与计数隔离、direct/joint/support 列判定。进程内 importlib 加载(注册 sys.modules 后 exec), 网络访问全 monkeypatch 打桩, 零真实网络零仓库外副作用。
- 红绿双验: 源码 2 处突变(delta_kind 层级互换 / pin 失败行改上抛)均被杀死后精确还原, 源码零残留(git diff 空)。
- `memory-bank/issues/26-11-03-1209-test-test-deps-upgrade-check-updates-uncovered.html`: 状态 Open→Done, 补认领与实际修法状态日志(索引已重建)。
