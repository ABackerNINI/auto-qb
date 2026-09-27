# Docker 部署 (真机验收通过 + 缺陷修复 + 文档重写) — 已入库 5fe4530

> 摘要: 真机验收(Docker Desktop · Windows, 全功能关闭冒烟配置连真实 qB 127.0.0.1:16585)**全部通过**: build 223s/252MB(重建 9s)、up→healthy 12~21s、`/api/status` connected:true+91 种子、stop 退出码 0(state.json mtime==停止日志瞬间)、双开拒锁退出码 1、WebUI token/401/写回(.bak 落 /data)/热重载/状态续接全过, **91 种子库零写入**(前后快照 tags/category 零差异); 计划 §5 的「未实测项」全部实测回填(数字单点: docs/deployment.md §14)。验收揪出并修复三件: ①非托管首连失败退出码 0≠文档承诺的 1 → `QbConnectError` 干净退出(qbmanager.py, 托管模式不变, behavior-core 的 `or` 有意语义未动; 测试 +2 改 2); ②「WEB UI 已启动」「配置热重载完成」WARNING→INFO(alert-levels 契约; 守阵 +2 —— ⚠ 抓日志要用挂目标 logger 的 Grab handler, caplog 挂 root 会被 setup_logging 清掉); ③`config/` 部署凭据目录补进 .gitignore。docs/deployment.md 重写为 14 节手册(含 web.enabled↔healthcheck 耦合、退出码契约表、Git Bash `MSYS_NO_PATHCONV=1` 坑 → 已记 pitfalls/ops/msys-container-path.md)。全量 **1619 collected: 1618 passed + 1 skipped, 92%**(baseline.md 顶部)。任务档案 `tasks/26-09-25-deps-docker-deploy.md`(进度日志 2026-09-26 01:33 条)。现场已清(down -v, 容器/卷/网络无残留; config/config.yml 留作即用配置, 已 gitignore)。
> 最后活动: 2026-09-27 13:52
> 下一步: 本轮已收口 —— **已入库 `5fe4530`**(gitee 与 github 双远端 `ls-remote` 均 == 本地, 幽灵 diff 空)。①待确认: `testing/baseline.md` 顶部数字是否由 1635 更新为 1638(差值 = 合流 `d0c39bf` 自带的 +3, 非本轮造成; 沿今日既有口径未改基线, 实测数字写在了提交消息里); ②P4 可选项(CI build / GHCR / 非 root)仍 Pending 不阻塞

## 追加(2026-09-26 03:58): 容器化后功能影响面分析(只分析 + 文档, 未改代码)

用户诉求: 已知 WebUI 右键「打开目标文件夹」失效 —— 要求**详细分析**容器部署后还有哪些功能失效/行为改变, 并补进 `docs/` 与 `memory-bank/`。

**方法**: 不靠推断 —— 直接在现成镜像 `auto-qb:latest` 里 `docker run --rm --entrypoint /bin/sh` 实测(二进制存在性、`os.path`/`open_path`/`PlatformChannel` 的实际返回值), 再按 "A 宿主路径不可见 / B 外部程序缺失 / C 无桌面会话 / D 网络身份与时区" 四类根因归拢代码里所有宿主依赖点。

**最要紧的发现(此前完全没记录)**: 失效的不止 WebUI 那一个按钮 —— **缺文件扫描会写坏 qB**。`grouping.py::_check_missing_files` 用 qB 报回的宿主 `save_path` 拼文件名后直接 `os.path.exists`, 容器里恒 False ⇒ 判定"文件缺失" ⇒ `torrents_stop` 暂停整组 + 打 `MISSING` 标签(**真实写入**)。而 `check_missing_files` 默认 `true`、`docker/config.example.yml` 未关 ⇒ **照抄示例配置就会踩**; 事件触发(组内删除/上传转暂停/errored/save_path 变化)而非每轮全扫 ⇒ 表现为"时不时一批种子被无故暂停", 难排查; 又因通知在容器里是哑的, 只能从 `docker compose logs` 发现。

**其余**: 跳检前置 `check_filelist` 恒判"文件缺失" ⇒ 跳检永不执行(保守, 不破坏数据); 规则 `exists()` 恒 False(静默)、`disk_*()` 直接 `ExprError`;`basic_check: custom` 全判非参考 + WARNING 刷屏; 目录浏览/新建 403/404;`notify` 静默 False;`--tray` 不可用;`/api/paths` 仍返回宿主路径(纯字符串, 手填可用)。

**产物**: `docs/deployment.md` §11 重写为「容器化后的功能变化」(四类根因 + 24 项矩阵 + 唯一会写坏 qB 的一条 + 必调配置表 + 挂下载目录的救回方案), §13 加 5 行排障, §4 修正"分组与容器无关"的错误口径;`docs/configuration.md` 三处补容器警示(`check_missing_files` / `custom` / `notify`);新建 [pitfalls/ops/docker-host-features.md](../pitfalls/ops/docker-host-features.md)(三行头 + 判别 + 实测证据 + 处置);`modules/webui-static-contract.md` 补三个 fs 端点的容器内返回码契约。

## 追加(2026-09-26 04:0x): 用户授权后落配置 + 守阵

- `docker/config.example.yml`: `grouping.check_missing_files: false` 落进示例(头注释"四处"→"五处"补第 ⑤ 项)。
- **守阵**: `tests/test_config.py::test_example_docker_config_yml_passes_fail_fast` 加一条
  `assert config.grouping.check_missing_files is False`(同步改文件头「## 测试计划」该行描述)。
  **已红验**: 把示例改回 `true` 时该用例 FAILED, 还原后 passed —— 不是摆设。
- 文档同步: `docs/deployment.md` §4 表格补第五行 + 注守阵测试; §11.3 由"示例未关会踩"改为"示例已关(2026-09-26 起), 手搓配置仍要关";
  `pitfalls/ops/docker-host-features.md` 两处同步。

## 追加(2026-09-27 13:52→14:07): 可行性验证 + 实施计划(已蒸馏进 plan/report, 此处只留指针)

- 13:52 可行性验证**结论: 成立** —— A 类只读触点全部救回, 映射层推翻 §11.5「Windows 宿主无解」; 两个设计前提(逻辑路径进/出 + miss 一律不可判定)与产物见 `reports/26-09-27-1352-report-docker-fs-wrapper-pathmap.html`。
- 14:07 实施计划 `plans/26-09-27-1407-plan-docker-fs-wrapper-pathmap.html`(W1–W5 波次 + 4 个已定取舍; 14:23 拍板放宽取舍③ mkdir 可写探测放行, 14:42 预演结论已补进计划)。

## 追加(2026-09-27 16:xx): 计划已实施(W1–W4 落地, 未提交; W5 真机验收待用户)

用户指令"实施计划 26-09-27-1407" → W1–W4 全部落地(单轮实施, 测试波次按计划的验收线执行):

- **W1+W2**: 新增 `infra/file_access.py`(FileAccess 抽象 + Local/Mapped 两实现 + `UNDETERMINED` 哨兵(隐式真值判断直接抛 TypeError, 防把不可判定当缺失) + `FileAccessError`(继承 OSError, 兼容既有 except OSError 兜底)/`NotSupported` + 单例 `init_file_access`/`get_file_access`); grouping/checking/env/conditions/fs 路由全部切包装层, 删散点 `add_long_path_prefix_for_win` 调用; `UNDETERMINED` 三态: 缺文件扫描跳过组 + WARNING / check_filelist 返回「路径不可判定」/ exists()·disk_*()·freespace → ExprError; fs.py 白名单保持在逻辑空间(scandir entry 译回逻辑空间, 报告 §04 的坑已对治), `realpath_lexical` Local 保留 realpath(保住符号链接逃逸防护, 既有 Linux 大小写兄弟/符号链接越界测试原样通过)、Mapped 纯词法; open-path 容器 501 显式降级(common.open_path 改走包装层, patch 地址不动)。
- **W3**: `fs.path_map` 配置键全链(models.FsConfig/PathMapEntry + loaders.load_fs_config + validation `_validate_fs`(from 绝对/to 根斜杠/尾斜杠归一/重复/前缀歧义聚合报错) + schema groups 登记(fs 段 optional object, path_map 用 text kind 降级 —— 改动面不含前端) + impact `fs: LEVEL_R`); Mapped 实现按拍板: mkdir 真实执行(只读挂载 OSError → fs 路由 403 语义化), open_path 恒 NotSupported, 匹配 casefold + 分隔符折叠 + `/` 边界 + 尾斜杠归一 + `\\?\` 剥离; 启动自检 `path_map_selfcheck`(挂载点存在性 WARNING / save_path 命中率 0% WARNING / 只读探测 INFO)挂 `_refresh_torrents` 首轮全量同步后一次性。
- **W4**: compose.yaml 挂载示例注释行 + Docker Desktop File Sharing 前提; docker/config.example.yml `fs: path_map: []` + 带映射注释样例(守阵加 `config.fs.path_map == ()` 断言); docs/deployment.md §11.2 矩阵 #1/3/4/6/7/8/9/10 改写、§11.3 处置补双重保险、§11.4 必调表改"不配映射时才必调"、§11.5 重写(同路径首选 + 映射表通用解, 删「Windows 宿主无解」)、§13 排障 +4 行、§14 加待实测行; docs/configuration.md `check_missing_files` 警示收敛 + 新增 fs.path_map 样例段; pitfalls/ops/docker-host-features.md 处置段更新(映射方案已落地 + 新代码一律走包装层)。
- **测试**: 新增 `tests/test_file_access.py` 22 条(三态矩阵/匹配规则/前缀边界/scandir 逻辑空间/mkdir 双态/自检/消费方三态/配置校验); test_web 两处适配(前缀 spy 地址迁 `auto_qb.infra.utils` 单点、`_fs` 帮手删除改断言 file_access 单点); test_config_schema 加 fs 段参数。受影响面 465 passed 先行确认, 全量另测。
- **回写**: progress/implemented-core.md 补条目; 计划 doc-status → In Progress; pitfalls 处置段已更新并重跑 kb.index。

**待办**: ①用户说「提交」后走 ship.commit(工作区还含本轮之前的 plans/reports 索引脏文件); ②**W5 真机验收**(Windows 宿主 + Docker Desktop: 缺文件扫描快照对比 / disk_usage vs fsutil / :ro·:rw mkdir 双态 / 跳检真触发; Linux 同路径对照; 91 种子库性能)—— 数字回填 deployment.md §14 与计划。
