# 5623 passed + 2 skipped —— WebUI 设置页 bt_backup 接线收口基线(计划 26-11-07-0708 S6)

> 摘要: WebUI 设置页 bt_backup 接线收口基线(计划 26-11-07-0708 S6)
> 基线时间: 2026-11-07 09:34

## 验收数字

`commands run test.full` 实测 (2026-11-07, 本轮后台执行; TMPDIR 由 tests/_tmp_bootstrap.py 自举):

```text
TOTAL                                                25503      5   8796     27    99%
5623 passed, 2 skipped, 1 warning in 166.59s (0:02:46)
```

- 覆盖率 TOTAL 25503 stmts / 5 miss / 8796 branch / 27 partial / 99%(门槛 99.5 过); 缺口单位(miss+partial)= 5+27=32, 与上基线(26-11-07-0440)同值且集合不变(fastresume 尾闸 / relocate_exec 防御支), 本批零新增缺口。
- 差值: 相对 26-11-07-0440 切片(5597 passed + 2 skipped, 同 2-skip 权限面)净增 26 用例 —— 其中本计划四批可归因 +4(`test_bt_backup_editor.py` 守阵 1 + v5→v6 迁移 3), 其余为 0440 记录时点与本轮基点(9f69075a)之间入库的增量, 非本轮改动; `git diff c4d068c0..b1fb6bd4 -- tests/` 实证本批除上述 4 例外全是版本锚/键面守阵机械跟进, 零删用例。
- **计划预判的 5 个 os.symlink 环境性失败本轮未复现(0 failed)**: S2/S3+S4 批提交信息所记「test_alias_fs 3 + test_web_relocate 2, 本 shell os.symlink 权限环境性, 基线同现」是主会话工具 shell 的沙箱权限形态; 本验收环境 os.symlink 可用(探针 islink=True, `commands run test.one -- tests/test_alias_fs.py tests/test_web_relocate.py` 单跑 97 passed, SYMLINK 副作用台账 106 条越界 0)。换环境即消失, 记录在案不追修。
- e2e 全量轨(同轮实测, `commands run dev.e2e`, 数字仅此处存证): **433 passed / 1 failed / 18 skipped(18.9m)**。1 failed = `e2e/dt-live-update.spec.mjs:428` #11 千文件数据回路(prism)长任务预算 0 实测 1 —— 性能预算型 flaky(本轮 test.full 曾与全量轨并行抢核); 单文件复跑 **14 passed (56.6s)**(#11 prism 实测 longtask 无(合 0ms))确认绿, 存量 flaky 不追修。18 skipped = 模式矩阵非默认档门控(既有口径)。S5 新增 settings-bt-backup 双皮肤 2 例随全量轨通过(ok 365/366)。
- 截图留证(计划 S6①/D8 浏览器实测): ui_harness 桩 + `scripts/ui_harness_settings_shots.mjs` 真浏览器目检, 四断言 x 两皮肤 24 项断言全过, 10 张截图见 `attachments/26-11-07-bt-backup-prism-*.png` 与 `attachments/26-11-07-bt-backup-atlas-*.png`(清单见「本改动面」)。

## 本改动面

- 计划 26-11-07-0708 四批提交(c4d068c0..b1fb6bd4): c4d068c0 计划建档; 88082316(S3+S4)退役键 `relocate.finalize_timeout` 移除(config v5→v6, `_migrate_config_5_6` 幂等 pop)+ relocate 组 help 按代码实际行为换新(「下线窗口/可直接再迁/fastresume」新口径, 键面守阵 199→198 键); a106e210(S2)设置页「整组迁移」组内嵌 bt_backup 编辑组件(x-template 分片 + `bt_backup_editor.js` + app.js 注册, 四皮肤 index.html 同批接线); b1fb6bd4(S5)`e2e/settings-bt-backup.spec.mjs`(prism/atlas 各 1 例)。
- S6 验收新增(本切片): `scripts/ui_harness_settings_shots.mjs`(截图脚本, dev-only 非测试, 头注释载明用法/断言面/桩起停口径) + `attachments/` 下 10 张截图: 每皮肤 5 张 —— 01-maintenance-view(设置「自动化」维护视图全景, 整组迁移块与 bt_backup 编辑器在场) / 02-editor-empty(编辑器空态文案「映射为空 = fastresume 收尾功能整体未启用」) / 03-relocate-help(S3 换新后的块头 help 特写) / 04-row-added(增行 host:port+路径已填) / 05-reload-readback(保存+重载回读, 行值仍在)。四断言: 编辑器渲染+空态、增行保存回读、新口径 help 在场、旧口径(setLocation 收尾/拒绝再迁)与退役键 finalize_timeout 全量退场(body textContent 口径)。
- pytest 测试计划零新增(无新测试文件; 浏览器级断言守阵由 S5 spec 承载, 截图脚本按任务口径不计测试)。config.yml 与 auto-qb-data/ 红线未动; 全程零 git 同步/提交。
