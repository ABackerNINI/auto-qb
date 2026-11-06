# R4 路线小结(存量评审 R4 · webui-py·CSS 机制)

owner: clone2-main · freeze: f088329291e6 · 快照: D:\Projects\zcode\auto-qb-review4-snap\auto-qb-zcode-clone2
终态: 4/4 批完成 · findings 共 44 条全部过引文校验(major 2 / minor 23 / nit 19) · refute 1(1 条幻觉引文被 review.check 弃,未入册)

## 批次勾选表

| 批 | 内容 | findings 过检 | 状态 |
|---|---|---|---|
| R4-1 | webui commands 面 ≈2.1K | 13 (minor 8 / nit 5) | done |
| R4-2 | webui 视图与运行时 ≈3.7K | 15 (major 1 / minor 10 / nit 4) | done |
| R4-3 | webui server 全域 ≈3.7K | 11 (major 1 / minor 5 / nit 5) | done |
| R4-4 | CSS 机制 + 模板 HTML(减配抽查)≈20.8K | 5 (nit 5) | done |

major 2 条(S6 聚合会话呈报拍板用)——
1. webui/runtime_views.py:378 HR 波次只堵了重建分叉、没堵时间线落代:hr_wave 为真时未登记 _pending_full_reasons,fold 落 full=False 条目,delta 客户端 HR 列可陈旧一个 full 周期(正是 :370-374 注释声称要堵的「ensure_state 触发发布不经 flush 判定点」缺口,重建侧堵了时间线侧没堵)。
2. webui/server/routes/torrent_detail.py:45 响应体泄敏缺口:/api/torrents/{hash} 详情与 /api/state、/api/groups 行视图把 qB tracker 字段原文外发,私站 announce URL 内嵌 passkey 进浏览器内存/截图/复制,与自家 mask_tracker_entry 泄敏纪律相悖。

## R2 复验结论

- **E-01 已消失**: R2 点名的 torrent_cmds.py/torrent_detail.py 全部裸 int()/float() 位置现均经 common.int_param/float_param 转换(畸形值 400),快照内 webui/server 无残留。
- T-02/T-04/T-05 锚在 gtm/* 文件,不在本路线批内文件,未复验(T-04 已由 R3 路线确认消失)。

## 自弃发现记录(主要项)

- 面1(R4-2): 组加入/离开的 partial 幽灵行(group_key_migrations 强制 full 不可达)/ relocate_chain 缓存对象覆写(每次响应覆写无可观察后果)/ call_tool 非 dict 返回 AttributeError(可信伴生进程契约固定)等 10 条。
- 面2(R4-2): errlog 环/搜索 rev/SSE 票据纯内存不落盘(设计口径非黄金法则 3 违反)/ → ⇒ ∈ · 等符号不在禁令枚举类(全库通行)等 8 条。
- 面1(R4-3): NotifyGate 事件号工具重启回退(gtm 侧持久化不回退)/ /api/log 整文件读(RotatingFileHandler 有界)等 7 条。
- 面2(R4-3): SSE 订阅数无上限(本机单用户理论 DoS)/ fs.py mkdir TOCTOU(行为良性)/ skip_local_verify loopback(跨源不可读+Origin 闸)等 10 条。
- 面1(R4-4): !important 13 处全部有段注且四皮肤同构 / prism 五主题令牌差异为有意覆盖 / 守阵引用抽查 14 处零失准。
- 面2(R4-4): shared js 70+ 处「三皮肤」同族措辞漂移与 nit 合并不逐条报 / boot.js 内联超时(注释钉明单点不可用)/ flux 静态挂 fx 三件(双重钉住设计如此)。

## 执行备注(供 S6 聚合会话参考)

- review.check 快照用法: R4 沿用 R3 的 workaround——快照根预建空 `.git` 目录绕过 _resolve_root 存在性误拒(issue 26-11-06 已入池)。建议 S6 前若该 issue 已修,重跑一次校验自证。
- 面拆分: R4-1 两面(正确性+安全 / 测试缺口+文档漂移);R4-2/R4-3 三面(正确性 / 安全+机制 / 测试缺口+文档漂移);R4-4 两面(CSS 机制 / 模板 HTML+加载序),全部串行派遣无并发。R4-3 面1 与面2 各自独立核实了 E-01(消失)与泄敏缺口,无撞车。
- 测试覆盖印象: commands/runtime/views/server 各面均报「覆盖密度显著高于常规水位」,实质零覆盖缺口仅 3 条(traffic_qb hash 400 分支 / ALT 限速真机准入 / tracker 报错真机准入)+ gtm 订阅真机债务 1 条(记账在案)。
- 文档漂移多为「指向已拆分/已删除的文件名」类陈旧指针(commands_common.py 守阵名 / views.py 旧模块名 / fs.py、keys.py 测试文件名 / drawer_head.js 幽灵排序引用),另 1 条涉 memory-bank/pitfalls/backend/effect-confirmation.md 权威口径与 D2 定案矛盾(建议 S6 呈报时单列)。
