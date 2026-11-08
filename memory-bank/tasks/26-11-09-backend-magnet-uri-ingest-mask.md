# 26-11-09-backend-magnet-uri-ingest-mask — magnet_uri 入库泄敏单点(issue 26-11-08-0043)

**Status:** Done
**Added:** 2026-11-09
**Updated:** 2026-11-09
**Summary:** magnet_uri 槽位入库掩码单点(apply_delta 之二, 同 tracker 批B 口径), 详情响应体/表达式面自动全覆盖; 复制 magnet 出掩码版, 入口处置另入池 0639
**Topics:** backend-magnet-uri-ingest-mask
**Refs:** memory-bank/issues/26-11-08-0043-bug-webui-torrent-detail-magnet-leak.html, memory-bank/issues/26-11-09-0639-bug-webui-copy-magnet-masked-degrade.html

## 本篇只回答

issue 26-11-08-0043(详情响应体 magnet_uri 泄敏)怎么修的、修到哪条边界、复制 magnet 功能的拍板去向 —— 单 issue 修复档案。

## 原始请求

1. 「修复memory-bank/issues/26-11-08-0043-bug-webui-torrent-detail-magnet-leak.html」
2. 拍板(AskUserQuestion): magnet_uri 槽位入库掩码后, 复制 magnet 功能处置 = 「移除:复制出掩码版」—— 本修不动前端, 入口移除/改造为后续独立任务。

## 思考过程与决策

- 复验先行(2026-11-09, HEAD eefda04f): 泄露面 = 内存槽位(apply_delta 原文落槽) + 详情响应体(`rec.to_dict()` 全库唯一消费面 = torrent_detail.py:45) + 表达式面(`rules/expr/env.py` 名字表从快照字段自动派生) 三处; state.json 不落盘(field_snapshots 只存监听字段 tags/category)。
- 修法取舍: 建议修法给了「快照入库」与「响应装配掩码/剥离」两条 —— 选入库单点: `to_dict()` 消费面唯一 + 表达式面自动派生, 槽位单点即全覆盖, 响应装配多点必然漏新面(26-11-07-0536 批B 已证)。
- 复用先例: qbmanager `_mask_magnet_tracker_urls`(26-11-07-0527 debug 导出先例)下沉为 `infra/utils.py::mask_magnet_tracker_urls` 公开单点, apply_delta 与 `_mask_debug_torrent_dict` 共用 —— 不造第二份口径。
- 产品拍板: 复制 magnet 的用途就是拿可用链接贴到别的客户端, 掩码版不可用; 用户选口径从紧(复制出掩码版), 功能语义处置(移除入口 vs 专用端点按需取原文)另入池 26-11-09-0639 待拍板。
- 评审: 分面两轮(411+ 行超 400 限 → 派发 2 按面拆: 正确性/泄敏面 + 测试/文档面)。首轮(旧锚 86430a04)零发现; 二轮测/文档面报 2 major(两处掩码钉面对回退无牙: fixture 是 percent-encoded 形态, 裸串断言恒真)+1 nit(0639 文案引用对不上 03 模板), 检 3/3 全过检, 当场加牙(`!= raw` + unquote 后逐位比对 sha256 掩码期望, 测试侧独立重算不同源 mask 函数)+文案拆开; 终轮复评零 actionable(突变有效性核实: 删掩码分支必红)。

## 实现计划

1. 掩码函数下沉: qbmanager `_mask_magnet_tracker_urls` → `infra/utils.py::mask_magnet_tracker_urls`(公开单点, 函数体逐字等价)。
2. `torrents/record.py apply_delta` 增设入库泄敏单点之二: `magnet_uri` 分支同 tracker 批B 口径(掩码在相等比较之前/空值不掩/确定性一致零假变化), tr= 掩码值落槽。
3. 注释口径同步: record 槽位注、详情路由 docstring、views_row 契约注释(复制 magnet 出掩码版 + 指向 0639)。
4. 钉面测试: `test_utils_parse.py::test_mask_magnet_tracker_urls`(tr= 掩码/多 tr=/非 magnet 与空原样/确定性)、`test_sync.py::test_apply_delta_masks_magnet_uri_tr_values`(落槽即掩/重复喂同原文零假变化/无 tr= 原样)、`test_web_seed_center.py::test_api_torrent_detail_endpoint` 扩(响应体 passkey 原文不外发); 三文件 docstring 测试计划同步。
5. issue 回写: 0043 复验行 + 修复后补充 + Done; 前端入口处置入池 0639。

## 子任务状态表

| 步 | 内容 | 状态 |
|---|---|---|
| 1 | 掩码函数下沉 infra/utils 单点 | Done(2026-11-09) |
| 2 | apply_delta 入库单点之二 | Done(2026-11-09) |
| 3 | 注释口径同步(路由/视图/槽位) | Done(2026-11-09) |
| 4 | 三处钉面测试 + 测试计划清单 | Done(2026-11-09) |
| 5 | issue 0043 回写 Done + 0639 入池 | Done(2026-11-09) |

## 进度日志

### R0 · 立档+修复实施 (2026-11-09)

- 复验仍复现 → 单点掩码实施全步走完; 评审分面两轮(首轮零发现; 二轮 2 major 钉面无牙当场加牙 + 1 nit 文案引用, 检 3/3 · 修 3 · 轮 3, 终轮零 actionable); 全量绿(见 kb.baseline); 真机不适用(纯桩可验: 掩码为纯字符串变换, 不涉 qB 真执行/文件系统/进程; qB 侧 magnet_uri 形态已由 debug 导出先例钉面)。
- 附带产出: 0639 入池(复制 magnet 入口处置待拍板)。

- 2026-11-09 06:53 认领并修复 issue 26-11-08-0043(已翻 Done): magnet_uri 槽位入库掩码单点(apply_delta 之二, 同 tracker 批B 口径), 掩码函数自 qbmanager 下沉 infra/utils 单点共用; 详情响应体/表达式面自动全覆盖; 复制 magnet 出掩码版(用户拍板口径从紧), 入口处置入池 0639 待拍板; 评审分面两轮终轮零 actionable(检 3/3 · 修 3 · 轮 3); 全量绿(见 kb.baseline); 真机不适用(纯桩可验: 纯字符串变换不涉 qB 真执行)
