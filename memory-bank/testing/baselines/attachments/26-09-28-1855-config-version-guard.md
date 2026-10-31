# 1823 passed / 3 skipped —— 配置版本升级守卫: 键面基线冻结快照(计划 26-09-28-1834)

> 摘要: 拦「改 config 键不走版本升级流程」—— 新增守卫测试 `tests/test_config_key_surface.py` 三条: ①键面比对(生成器从 schema Field 树 + validation 常量派生 170 键路径, 动态段归一通配; 与冻结基线 `tests/fixtures/config_key_surface.txt` 比对, 不一致按「消失键=破坏→抬版本+注册迁移 / 纯新增=非破坏→重生成 / 版本已抬→重生成」三现场分流报错并指路 versioning.py 口径与计划 26-09-26-0506) ②config 迁移链完整性静态断言(原只在运行时 migrate() fail-fast) ③参考文档出处钩(叶键须在 keys.md + rule-system/conditions-and-actions.md 反引号 span 有出处; 插件 spec 内部键暂豁免, 权威单点 schema 插件表)。再生命令 `commands run test.keys-update`(收录进 test 包)。keys.md 机械补齐: `fs` 行(此前整行缺失的既有漂移) + `hr` 输出键反引号化 + 规则段插件指针。
> 基线时间: 2026-09-28 18:55
> 档案: tasks/26-09-28-config-version-guard.md(新建)

- test.full: **1823 passed / 3 skipped**, TOTAL **91%**(12543 语句 / 918 未覆盖 / 4222 分支 / 389 partial), 耗时 23.2s(本批三次全量区间 20.7–23.6s), 较前基线(26-09-28-1738)净增 3 条守卫用例, 其余零回归。
- 抖动一笔: 中间一次全量 `test_qbmanager.py::test_run_loop_throttles_without_stop_event` 挂过一次(计时敏感), 单跑即绿、复跑全量绿 —— 与本批改动无接触面(守卫只读 schema/validation 常量, 不触 qbmanager)。
- 守卫有效性突变自检: 删基线一行键 → 用例红且文案正确分流; 还原后 3 passed。
