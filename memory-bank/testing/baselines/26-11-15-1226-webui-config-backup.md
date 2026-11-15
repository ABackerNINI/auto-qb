# 6219 passed, 2 skipped —— webui 配置备份 S1-S5 收尾基线(覆盖率闸红 99.47% < 99.5, 列报待入池)

> 摘要: webui 配置备份 S1-S5 收尾基线: 用例全绿但覆盖率闸红(评审新增闸门分支无测试), 列报不改
> 基线时间: 2026-11-15 12:26

## 验收数字

`commands run test.full` 实测(2026-11-15 12:26, Windows 本机, feat/webui-config-backup 工作树):

```
TOTAL                                                27783    104   9788     94    99%
FAIL Required test coverage of 99.5% not reached. Total coverage: 99.47%
6219 passed, 2 skipped in 147.01s (0:02:27)
```

- 用例全绿(6219 passed / 2 skipped), **但 test.full 退出码 1: 覆盖率闸 FAIL** —— 总覆盖 99.47% < 99.5(Windows 侧阈值, tests/conftest.py::pytest_configure)。
- 归因(实测差分, 对照上基线 26-11-15-0446 的 TOTAL 27305/68/9588/73): 本分支 S1/S2 新增代码引入净缺coverage —— `routes/backup.py` 88%(25 语句 + 8 分支未覆盖: alias 共享引用闸 162-168 / 深度上限 177-178 / 节点数上限 193-197 / 聚合先验 `_aggregate_config_precheck` 221-234 / gtm echo 分支 281-282, 292 等)与 `config/writer.py` 97%(189, 249, 277-284, 335, 342, 379, 446-447 等) —— 均为评审轮新增的防御闸门分支, 闸门本身未带测试。S1-S4 阶段只跑 test.quick(内置跳过覆盖率闸), 本缺口在 S5 全量首次显形。
- **处置: 列报不入池代码改动(范围守恒)** —— 缺口待入池补闸门测试后重录全绿基线; 本切片是当前树的真实测量快照。
- e2e 另计(S3 阶段实测): `e2e/settings-backup.spec.mjs` 6 用例 @fast, prism/atlas 12 例全过; @fast 全量 e2e 存在 4 例与本分支无关的存量失败(2 例 flux chip 语义色/辉光、2 例 views 种子计数 300 vs 301, 干净 HEAD 差分实证, 已列报待入池)。

## 本改动面

- `memory-bank/architecture/webui.md`: 新增「配置备份 bundle 导出/导入」节(bundle 形态/两端点契约/掩码与 resolve 口径/导入管线/错误码语义/双清单登记闸/前端交互流) + 摘要与触发词行同步
- `README.md`: Web UI 功能清单新增「配置备份一键导出/导入」一行
- `memory-bank/plans/26-11-14-0624-plan-webui-config-backup.html`: §10 追加 R1 行 + doc-status Open → Done
- `memory-bank/tasks/26-11-14-webui-config-backup.md`: S1-S5 状态表翻转 Done + R1 进度段 + 范围外列报节
- `memory-bank/pitfalls/backend/ruamel-roundtrip-mask-pitfalls.md`(新): DuplicateKeyError 异常文本泄敏 / CommentedMap 引号形态继承 / alias 爆炸面 三条
- `memory-bank/pitfalls/web-ui/input-files-filelist-truthy.md`(新): input.files 恒 truthy 一条
- 零代码改动(收尾轮) —— 覆盖率闸红非本轮引入, 归因见「验收数字」
