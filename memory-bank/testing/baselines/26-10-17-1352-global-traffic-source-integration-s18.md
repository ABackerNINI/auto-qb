# 3530 passed + 4 skipped(根) —— 全局流量来源集成 S18(守阵补口: 拉起不拼 uv/指针跨侧镜像/gitignore 覆盖 + 文档四处回写)

> 摘要: 全局流量来源集成 S18(守阵补口: 拉起不拼 uv/指针跨侧镜像/gitignore 覆盖 + 文档四处回写)
> 基线时间: 2026-10-17 13:52

## 验收数字

- 根 `test.full`(契约: 覆盖率门槛 98% + 包内 TMPDIR): **3530 passed + 4 skipped in 121.32s**; TOTAL **18169 260 6096 189 98%**(语句/未覆盖/分支/partial/覆盖率, 实测 98.13%)。本切片由 `commands run kb.new baseline` 从实测输出誊写(裁定 A4); 数字取**收尾后最终树**的那次全量跑(此前两次: 一次因并发改 KB 自扰判红、一次为中间态)。
- 本轮知识库回写后守卫单跑 `test.one`(`tests/test_memory_bank.py` + `tests/test_docs_forms.py`): **77 passed**, 副作用台账越界 0 条(覆盖新基线切片格式、档案/切片结构与认领链守阵、新坑条三行头)。
- 新增守阵 4 条均做过**红绿双验**(突变 → 判红 → 还原后复绿, 还原以 `git checkout` 保证字节级一致): ①agent.py 加一条含 `uv run gtm run` 的字符串常量 → `test_launch_path_has_no_uv_or_entry_names` 红; ②工具 `POINTER_DIR_NAME` 改 `gtm` → `test_pointer_constants_mirror_tool_side` 红; ③`.gitignore` 注释掉 `data/` 行 → `test_tool_runtime_dirs_are_gitignored` 红; ④`active_dat_path()` 工具面缺 `data_dir` 时回退 TM 路径 → `test_active_dat_path_provider_is_exclusive` 红。

## 本改动面

- `tests/test_traffic_source_agent.py` —— 新增 3 条守阵(头「测试计划」清单同步): `test_launch_path_has_no_uv_or_entry_names`(AST 扫 agent.py 非 docstring 字符串, 禁 `uv`/`gtm`/`-m`/`run`/`--autostart`/`--data-dir`; 运行时形状由既有 `test_launch_tool_builds_platform_command` 逐 token 钉住) · `test_pointer_constants_mirror_tool_side`(AST 读工具 `gtm/storage.py`, 指针目录名/文件名/schema 与 agent 同值) · `test_tool_runtime_dirs_are_gitignored`(读 `.gitignore` 文本断言 `tools/global-traffic-monitor/data/` 与 `run/` 在场, 不起 git 进程以免撞 sidefx POPEN 白名单)
- `tests/test_config_traffic_monitor.py` —— 新增 `test_active_dat_path_provider_is_exclusive`(两来源参数并存时只 provider 选中者参与取数; 工具面缺 `data_dir` 返回空, 不静默回退 TM)
- `docs/configuration.md` —— 全局限速曲线段去内联来源(改指向顶层 `traffic_source`); 工具章节整体改版: 全称 CLI `global-traffic-monitor`、数据目录 `<工具安装目录>/data` + 一次性搬迁、指针目录与 `instance.lock`、**随机端口**(`http_port` 0, 排障用 `endpoint` 子命令)、启动器 `launch.cmd/.sh`、自启裁决在工具 `config.autostart`(`POST /autostart` + 指针 `autostart_registered`); 新增「auto-qb 侧: 发现与自动拉起」与「auto-qb 侧配置(traffic_source)」两节; 迁移检查单重写(切来源 = 改 `provider` + 填 `data_dir`); 双写者禁令改口径
- `memory-bank/config-reference/keys.md` —— 修 S15 遗留的两处口径错: `tool_dir` 留空 = 仓库内默认目录(**不是** PATH 查找)、`tool_exe` 非空且存在则优先于启动器(**不是**默认名); `data_dir` 注明「取数用, 留空 = 无数据源」
- `README.md` —— 限速特性补「整机流量来源一键切换(自动发现 / 缺席自动拉起, 免配端口与密钥)」
- `memory-bank/pitfalls/backend/traffic-source-discovery-pointer.md`(**新**) —— 指针/锁锚用户级目录、就绪只认探活、锁前置、跨包镜像常量
- `memory-bank/pitfalls/backend/traffic-source-random-port.md`(**新**) —— 随机端口后一切写死端口失效; 端口唯一出口是指针; 订阅注册键须含基地址
- `memory-bank/pitfalls/git/runtime-data-in-repo.md`(**新**) —— 运行期数据落仓库内工具目录必须同笔补 `.gitignore`
- `memory-bank/pitfalls/{backend,git}/_index.md` 等 21 个生成物 —— `commands run kb.index` 重建
