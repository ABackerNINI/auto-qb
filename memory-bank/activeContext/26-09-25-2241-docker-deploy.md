# Docker 部署 (真机验收通过 + 缺陷修复 + 文档重写) — 已入库 5fe4530

> 摘要: 真机验收(Docker Desktop · Windows, 全功能关闭冒烟配置连真实 qB 127.0.0.1:16585)**全部通过**: build 223s/252MB(重建 9s)、up→healthy 12~21s、`/api/status` connected:true+91 种子、stop 退出码 0(state.json mtime==停止日志瞬间)、双开拒锁退出码 1、WebUI token/401/写回(.bak 落 /data)/热重载/状态续接全过, **91 种子库零写入**(前后快照 tags/category 零差异); 计划 §5 的「未实测项」全部实测回填(数字单点: docs/deployment.md §14)。验收揪出并修复三件: ①非托管首连失败退出码 0≠文档承诺的 1 → `QbConnectError` 干净退出(qbmanager.py, 托管模式不变, behavior-core 的 `or` 有意语义未动; 测试 +2 改 2); ②「WEB UI 已启动」「配置热重载完成」WARNING→INFO(alert-levels 契约; 守阵 +2 —— ⚠ 抓日志要用挂目标 logger 的 Grab handler, caplog 挂 root 会被 setup_logging 清掉); ③`config/` 部署凭据目录补进 .gitignore。docs/deployment.md 重写为 14 节手册(含 web.enabled↔healthcheck 耦合、退出码契约表、Git Bash `MSYS_NO_PATHCONV=1` 坑 → 已记 pitfalls/ops/msys-container-path.md)。全量 **1619 collected: 1618 passed + 1 skipped, 92%**(baseline.md 顶部)。任务档案 `tasks/26-09-25-deps-docker-deploy.md`(进度日志 2026-09-26 01:33 条)。现场已清(down -v, 容器/卷/网络无残留; config/config.yml 留作即用配置, 已 gitignore)。
> 最后活动: 2026-09-26 04:09
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
