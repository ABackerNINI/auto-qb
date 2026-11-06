# R3 路线小结(存量评审 R4 · hr·新代码)

owner: clone2-main · freeze: f088329291e6 · 快照: C:\Users\11059\Desktop\Projects\zcode\auto-qb-review4-snap\auto-qb-zcode-clone2

## 批次勾选表

| 批 | 内容 | findings 过检 | 状态 |
|---|---|---|---|
| R3-1 | transfer 全域(新模块) + torrents/store | 4 (major 1 / minor 2 / nit 1) | done |
| R3-2 | torrents 杂件 + tray + cli + tools | 2 (major 1 / nit 1) | done |
| R3-3 | hr service 族: service_wave/service/service_common/service_status/module | 6 (major 1 / minor 3 / nit 2) | done |
| R3-4 | hr 模型状态: model/status/resolve | 8 (minor 4 / nit 4) | done |
| R3-5 | hr 运行时: runtime/server/channel/worker/threadlifecycle/queue/events | 8 (major 1 / minor 5 / nit 2) | done |
| R3-6 | hr 取数解析: discovery/report/parse/fetcher/store/bencode/log/ratelimit + adapters 14 文件 | 7 (minor 3 / nit 4) | done |

## R2 复验结论

- **T-04 已消失**: gtm/__init__.py:8-11 进度注已更新到 S0-S9 落地+S10 待授权;「重读历史文件」措辞在 gtm README 全文件 grep 零命中,现为「零读盘直达」口径;根 README:62 的「读历史文件」指 TrafficMonitor 传统来源语义准确非漂移。
- **A-05 已消失**: relocate_exec.py:494-518 _finalize_members 已改先按 finalize_scope_candidate 零成本过滤再取文件表(26-10-30-0616 修复实证)。
- **GH-01 部分复发**: ①读后心跳整包覆盖已消失——write_journal 前向合并拒非终态覆盖终态(finaalize_watch.py:193-194 + relocate_journal.py:80-84);③journal 头注「唯一写者」已消失——现明写两个写者+前向合并保序;②max_wait 缺省 0 **仍在**(finalize_watch.py:165/:249/:270),但 docstring/CLI help 已明示「0=不限,auto-qb 侧 finalize_timeout 才是最终兜底」,定级交聚合会话。

- **B-01 已消失**: 三处判据收敛到单点谓词 _lane_covers_done(service_common.py:360-380,cutoff_done<=0 显式判死),调用点 _freeze_terminal(service_wave.py:813)/_position_covered(service_common.py:395)/_absence_proven_all(service_common.py:415)无一绕开;锚点随拆分重定位。
- **B-01 沿用 R3-3 结论(已消失)**:本批 3 文件(model/status/resolve)未发现同语义新独立问题。

- **gtm 底册 T-01/T-02/T-05 全部已消失**(R3-5 批复验): T-01 _autostart/_put_config 已整段持 _config_write_lock(26-10-30-0624); T-02 新增 _check_http_host 回环约束 fail-fast(config.py:199-216); T-05 三处死码均已清(F401 import 收紧/uninstall 路由化/errors 全消费)。
- **B-02 已消失**(R3-6 批复验): discovery.py 中 is_loopback_host/_content_length grep 零命中,现 import 全部有使用点。B-01/T-04 沿用已消失(见上)。

## 自弃发现记录

reviewer 自弃 7 条(run_batch 外层 create_adapter 防御性 raise 生产不可达 / TrDownloaderStub.add_torrent 有意设计失败安全 / all_categories 不拷贝但调用方全只读 / 两个 __init__ docstring「单点导入」措辞与实际分叉导入不符无功能影响 / _verify 内部结果 hash 字段被重包丢弃 / _AUTH_FAILURE_NEEDLE 文案耦合纯理论 / _verify 空 state 按成功无可观察场景);本批 review.check 被弃条目:0 条(4/4 全过)。

R3-2 批自弃 6 条(_hr_guard 族 None 全调用方有守卫 / tray _poll 未包 try 举不出触发场景 / finalize_watch 端口探测双发冗余无害 / state_enum 恒真防御分支 / __all__ 未含包根直取项有实测依赖 / qB tags 数组疑点有真机坑档实证读回口径);本批 review.check 被弃条目:0 条(2/2 全过)。

R3-3 批自弃 6 条(→/⇒ 箭头全仓统一风格 / ① 全仓 106 处存量一致 / 防御性 getattr 属可留例外 / ACTION_LOCKED 展示边缘 / quota 让位路径 fetched_at 有 expires_at=0 兜底 / _mark_fetch_failed_lane 早退守卫无害);本批 review.check 被弃条目:0 条(6/6 全过)。

R3-4 批自弃 8 条(has_anchor_snapshot 全零边界方向保守 / done_epoch 超大年份纯理论 / site_conf_interval getattr 属可留类 / blocking_reason 625 重复实现谓词属风格 / resolve_identity 等现在形参 docstring 明示预留 / _as_int 折 0 手改坏极端边界 / →⇒ 箭头全库惯例非禁用类 / bool("false") 同范式手改坏噪音);本批 review.check 被弃条目:0 条(8/8 全过)。

R3-5 批自弃 10 条(RejectThrottle 警告键锁外读写仅日志重复 / stop 超时并存线程有文件锁兜底 / queue TTL<request_timeout 等效超时语义 / assert -O 剥离运行面不用 / _anchors O(n) 无正确性影响 / UrlPolicy 端口 userinfo 无攻击者输入路径 / OPTIONS 免 token 设计内 / build_views 跨实例写侧不在本批 / _note 状态变化才记 / ⇒·—— 不在禁用类);本批 review.check 被弃条目:0 条(8/8 全过)。

R3-6 批自弃 8 条(discovery stop/retry 竞态窗口实际闭合 / bencode 拒非规范编码理论风险 / parse_page 零行有设计门槛 / fetcher 注释措辞张力 / report 调私有方法风格面 / _pair_fail_times 无界无可达失败 / 退避熔断措辞非事实错误 / _replace_url_host IPv6 无端口仅响应文本);本批 review.check 被弃条目:0 条(7/7 全过)。

## 执行备注

- review.check --root 快照 在快照根建空 .git 目录绕过 _resolve_root 存在性误拒(R2 用 diff 等价通路,本路线改用更直接 workaround,零代码改动)。
- 本批含 1 条 docs 类发现(5 份 pitfalls 的 hr/service.py::<符号> 指路因拆分漂移),按口径只报不改,交 S6 聚合。
- R3-6 批 #3(ratelimit.py:8 失败路径绕过最小间隔)与 R3-3 批 major(service_wave.py:542 budget.mark 漏调)为同根双报,交 S6 聚合按 file+quote 去重合并。
