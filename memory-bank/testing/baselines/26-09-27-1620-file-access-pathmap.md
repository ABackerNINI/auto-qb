# 1723 passed + 1 skipped —— 文件访问层 + 下载目录路径映射(W1–W4 落地)

> 摘要: plans/26-09-27-1407 实施轮。新增 `infra/file_access.py`(Local/Mapped + UNDETERMINED
> 三态哨兵)收编下载数据目录全部本地访问, 消费方(grouping/checking/env/conditions/fs 路由)全部
> 切包装层; 新配置键 `fs.path_map`(空 = 现状, R 级热重载)驱动容器路径映射, 映射 miss 一律
> 「不可判定」绝不判缺失。测试 +26(test_file_access.py 22 条 + 配置/schema 守阵扩面),
> sim_fsmock 探测点守阵随单点收编同步(探测函数移至 infra/file_access.py, mock 按模块属性
> 打桩覆盖不变)。数字取自合并远端 hr-site-presets 之后的合并树。W5 真机验收
> (Windows Docker Desktop + Linux 同路径对照)待执行。
> 基线时间: 2026-09-27 16:40
> 档案: 26-09-25-docker-deploy

- **测试增量**: 1688+1 → **1723+1**(+26 本轮 + 9 远端 hr-site-presets): tests/test_file_access.py
  新增 22 条(三态矩阵 / 匹配规则 / 前缀边界 / scandir 逻辑空间 / mkdir 双态 / 自检 / 消费方
  三态 / 配置校验); test_web 两处适配(前缀 spy 迁 `auto_qb.infra.utils` 单点、`_fs` 帮手删除);
  test_config_schema 加 fs 段参数; test_config docker 守阵加 `fs.path_map == ()` 断言;
  test_sim_corpus 探测点表随收编更新(_EXPECTED_PROBES → infra/file_access.py, 红验路径同步)。

TOTAL 91%(11531 语句 / 845 未覆盖 / 3832 分支 / 342 partial; test.full 15.8s, 1 采样;
覆盖率口径见 [../baseline.md](../baseline.md))。

