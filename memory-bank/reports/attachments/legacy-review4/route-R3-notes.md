# R3 路线小结(存量评审 R4 · hr·新代码)

owner: clone2-main · freeze: f088329291e6 · 快照: C:\Users\11059\Desktop\Projects\zcode\auto-qb-review4-snap\auto-qb-zcode-clone2

## 批次勾选表

| 批 | 内容 | findings 过检 | 状态 |
|---|---|---|---|
| R3-1 | transfer 全域(新模块) + torrents/store | 4 (major 1 / minor 2 / nit 1) | done |
| R3-2 | torrents 杂件 + tray + cli + tools | - | pending |
| R3-3 | hr service 族: service_wave/service/service_common/service_status/module | - | pending |
| R3-4 | hr 模型状态: model/status/resolve | - | pending |
| R3-5 | hr 运行时: runtime/server/channel/worker/threadlifecycle/queue/events | - | pending |
| R3-6 | hr 取数解析: discovery/report/parse/fetcher/store/bencode/log/ratelimit + adapters | - | pending |

## R2 复验结论

- **T-04 已消失**: gtm/__init__.py:8-11 进度注已更新到 S0-S9 落地+S10 待授权;「重读历史文件」措辞在 gtm README 全文件 grep 零命中,现为「零读盘直达」口径;根 README:62 的「读历史文件」指 TrafficMonitor 传统来源语义准确非漂移。

## 自弃发现记录

reviewer 自弃 7 条(run_batch 外层 create_adapter 防御性 raise 生产不可达 / TrDownloaderStub.add_torrent 有意设计失败安全 / all_categories 不拷贝但调用方全只读 / 两个 __init__ docstring「单点导入」措辞与实际分叉导入不符无功能影响 / _verify 内部结果 hash 字段被重包丢弃 / _AUTH_FAILURE_NEEDLE 文案耦合纯理论 / _verify 空 state 按成功无可观察场景);本批 review.check 被弃条目:0 条(4/4 全过)。

## 执行备注

- review.check --root 快照 在快照根建空 .git 目录绕过 _resolve_root 存在性误拒(R2 用 diff 等价通路,本路线改用更直接 workaround,零代码改动)。
