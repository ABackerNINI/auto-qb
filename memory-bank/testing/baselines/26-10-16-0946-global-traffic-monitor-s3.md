# 3413 passed + 4 skipped —— 全局流量监视小工具 S3 控制面(工具测试新增 38 条, 根集数字不变)

> 摘要: 用户「继续S3」(对 S3 的显式授权, S4–S10 不动)。config.py 全量实现(~240 行: Config frozen dataclass §05 全参数; validate_payload 全量聚合校验[未知键/类型/bool 陷阱/正数/端口/有限数值/非法正则]; load/save; ConfigHolder 热重载持有者) + server.py 全量实现(~360 行: TokenManager[urlsafe(32) 启动即原子生成, compare_digest]; ControlServer[ThreadingHTTPServer 强制 127.0.0.1, Windows 关抢占式 allow_reuse_address 才 fail-fast, 端口占用 OSError]; GET /status/PUT /config[聚合校验->原子写->热重载]/subscribe+heartbeat+unsubscribe[租约 180s 懒剔除]) + storage.py 扩展(state.json 载荷并入 subscribers+last_event_id, RLock 串行化采样线程与 HTTP 线程读-改-写, 每次写盘完整镜像[最近快照+注册表+事件号]) + __main__.py _run_loop 抽出可测循环 + cmd_run 接线 + pyproject 依赖 +pyyaml 6.0.3 + tests/test_config.py 17 条 + tests/test_server.py 21 条(全 hermetic) + test_storage.py +2 条, 改 4 文件+2 新文件+1 依赖零 auto-qb 触碰。出口判据全过: 鉴权 401 双形态/租约剔除单测/端口冲突 fail-fast 实测(WinError 10048 exit 1)/热重载不丢采样(真循环+并发 PUT, 线程存活+帧数增长); 工具 98/98; 红验 6 条突变全判红字节恒等还原复绿; 真机冒烟 token 首启生成->鉴权全端点->热重载 5.0->2.0->kill -9 重启注册表续存+配置跨重启保留。两处真缺陷(测试/冒烟暴露已修): 热重载静默杀循环(AdapterFilter 单正则串误传 list 致线程猝死; 修为 | 并入+非法正则校验层拒+重建进 try)与 token 惰性生成鸡生蛋(修为 start 即生成)。本切片为根 test.full 回归闸门数字(工具测试不在根 testpaths 内, 不进本 TOTAL, 与 S0/S1/S2 基线逐位一致)。
> 基线时间: 2026-10-16 09:46

- test.full: 3413 passed + 4 skipped / TOTAL 17343 182 5846 159 99%; 耗时 121.83s(单次采样, 口径见 baseline.md)。与 S0(26-10-16-0601)/S1(26-10-16-0815)/S2(26-10-16-0855)切片数字逐位一致 —— S3 零 auto-qb 触碰且工具测试不进根 testpaths, 符合预期。
- 工具侧自测(独立 venv, 不计入根 TOTAL): `uv run pytest -q` 98 passed(4 条 S0 冒烟 + 29 条 S1 采样守阵 + 27 条 S2 落盘守阵 + 17 条 S3 配置守阵 + 21 条 S3 控制面守阵), ~12s。
- 红验(临时脚本 H:/Temp/gtm-s3-redverify.py, bytes 层, 锚点 count==1, 还原后字节恒等, 基线复跑放还原后, 解释器钉死工具 venv 绝对路径 —— 形态十一): 6 条单行锚点突变全 RED —— 鉴权绕过(compare_digest->True) / 租约永不剔除(expired=[]) / 未知键不拒(if False) / 心跳未知 id 放行(return False->True) / 热重载失效(replace->pass) / 注册表丢失(payload subscribers->{}); 全部字节恒等还原后 98 passed 复绿。
- 鉴权(计划 S3 出口): 无 token/错 token -> 401(compare_digest); 写端点同样过闸(PUT/POST 无凭证 401)。
- 租约剔除(计划 S3 出口): last_heartbeat+lease_ttl<now 懒剔除(每个已鉴权请求入口先 prune); 注入 now 单测: 超租约剔除/未超保留; HTTP 层: 拨回心跳时间后 /status subscriber_count 1->0。
- 端口冲突 fail-fast(计划 S3 出口实测, Windows): 首实例持 8099, 第二实例(不同 data-dir 绕开单实例锁)绑定即 `[WinError 10048]` -> stderr `gtm: 控制面启动失败 (端口 8099 被占用?)` exit 1 —— 证明 Windows 上必须关掉抢占式 allow_reuse_address(默认 True 会让第二进程静默双监听, 坑档 platform-fs/web 同族)。
- 配置热重载不丢采样(计划 S3 出口): 真 _run_loop + 并发 PUT /config 集成测试 —— 改 sample_interval 5->0.05s + adapter_exclude 后循环线程存活、采样帧数持续增长; 首版曾因 AdapterFilter 收单正则串而误传 list 致线程猝死(静默丢采样), 已修为模式列表 `|` 并入 + 非法正则在 config 校验层聚合拒绝 + 过滤器重建进 try。
- 真机冒烟(Windows, 临时 data_dir H:/Temp/gtm-s3-smoke-*, 全程后清理): ①首启 monitor.token 原子生成(43 字符, 启动即落盘 —— 首版惰性生成致"没文件读不出密钥/没密钥又不发生成"鸡生蛋, 真机冒烟暴露已修); ②带 token GET /status 全字段(day/累计/末事件号/订阅者数/路径/配置回显/uptime); ③subscribe 返回 id + lease 180s; ④PUT /config {sample_interval:2} -> 热重载即时生效(5.0->2.0)且 config.yml 落盘; ⑤kill -9 重启: state 快照恢复(day_total 累计接续) + 注册表续存(subscriber_count 1) + 配置跨重启保留(sample_interval 2.0)。
- Linux/macOS 侧未跑 —— S3 为 stdlib http.server + 文件原子写, 三平台统一; 绑定语义按平台分流(Windows 关抢占式 SO_REUSEADDR, POSIX 保留 True 绕 TIME_WAIT)已在单测覆盖。本条 Windows 侧数字为事实源。

## 本改动面

- `src/gtm/config.py` 占位 -> 全量实现(~240 行: Config frozen dataclass §05 全参数; validate_payload 全量聚合校验 [未知键/类型/bool 陷阱/正数/端口范围/有限数值/非法正则]; load_config [缺失/空文件->默认, YAML 坏->错误]; save_config [yaml.safe_dump + atomic_write_text]; ConfigHolder 热重载持有者)
- `src/gtm/server.py` 占位 -> 全量实现(~360 行: TokenManager [urlsafe(32) 原子生成/加载, compare_digest 验]; ControlServer [ThreadingHTTPServer 强制 127.0.0.1, 平台分流 allow_reuse_address, start 即生成 token, 端口占用 OSError fail-fast]; 端点 GET /status [采样状态+当日累计+末事件号+订阅者数+路径+配置回显+uptime] / PUT /config [校验->原子写->热重载] / subscribe+heartbeat+unsubscribe [校验+租约]; 懒剔除; 请求体上限 1MiB; 日志走 gtm logger)
- `src/gtm/storage.py` 扩展(~+160 行: state.json 载荷并入 subscribers + last_event_id; RLock 串行化采样线程与 HTTP 线程的读-改-写; _persist_state_locked 完整镜像 [最近快照+注册表+事件号]; upsert/touch/remove_subscriber; prune_expired_subscribers; recover 提取注册表 [坏条跳过]; set_flush_params 热重载)
- `src/gtm/__main__.py`: _run_loop 抽出可测循环函数(stop_event.wait 可中断 sleep; 每轮读 holder.current 热生效; 过滤器重建进 try); cmd_run 配置加载 fail-fast 聚合报错 -> 锁 -> recover -> 控制面启动(端口占用 exit 1) -> 循环 -> 优雅退出(停 server+落盘+释放锁)
- `pyproject.toml`: 运行时依赖 +pyyaml(6.0.3, 与主仓同版本; 理由: config.yml 与 auto-qb WebUI 同格式同解析器, 拒手搓 YAML 子集)
- `tests/test_config.py` 新文件 17 条; `tests/test_server.py` 新文件 21 条(全 hermetic: tmp_path + 端口 0 + 注入计数器); `tests/test_storage.py` +2 条(载荷合并)
- `README.md` / `src/gtm/__init__.py`: 控制面端点表 + 运行说明 + 进度注记(S3 落地)
- 坑档: `pitfalls/testing/redverify-anchor-lineendings.md` 复发+1 + 形态十一(红验脚本解释器漂移致假红: 系统 python 无 pytest -> rc!=0 被按"守阵杀变异"判 KILLED; 处置=钉死目标 venv 解释器 + 突变循环前先跑无变异基线)

**Refs:** memory-bank/tasks/26-10-16-backend-global-traffic-monitor.md
