# 26-10-31-deps-qb-5-3-support — qB 5.3 双版本支持落地(facade/重加/升库)

**Status:** In Progress
**Added:** 2026-10-31
**Updated:** 2026-10-31
**Summary:** qB 5.3 双版本支持 P1-P3 已落地(facade share_limits_mode 补参/跳检重加回传/升库 2026.10.1, 全量见基线); P4 真机走查与 P5 文档回写待 5.3 stable 发布。
**Topics:** deps-qb-5-3-support
**Refs:** memory-bank/plans/26-10-31-1119-plan-qb-5-3-support.html, memory-bank/issues/26-10-31-0711-bug-qbapi-share-limits-mode.html, memory-bank/issues/26-10-31-0711-bug-skip-readd-share-limits-mode.html, memory-bank/issues/26-10-31-0716-chore-qbittorrentapi-bump-dual-version.html, memory-bank/testing/baselines/26-10-31-1204-qb-5-3-p1p3-landing.md

## 原始请求

1. 「增加对qbv5.3.x的支持,先写一个详细的计划」—— 已产出计划 `plans/26-10-31-1119-plan-qb-5-3-support.html`(事实源: 报告 `26-10-31-0548-report-qb-5-3-upgrade-impact` + 5 份相关 issue)。
2. 拍板后「实施」: 先适配 5.3 beta/rc, stable 发布后再处理差异; 机会项不纳入(其 issue 保持 Open); 真机验证等 stable 发布后再做。

## 思考过程与决策

- 计划路径: `memory-bank/plans/26-10-31-1119-plan-qb-5-3-support.html`(§03 五期分期)。拍板: D1=P2 随 P1 同批补齐 / D2=先适配 5.3 beta/rc,stable 后处理差异(真机走查 P4 随之延后) / D3=🔵 机会项不纳入本计划,`feat/qb-5-3-new-capabilities` 保持 Open / D4=基线重测时点随分期(P3 后一次;P4 后那次随 P4 延后)。
- **P2 落点改道**(与 issue 建议修法不同,已回写 issue): `share_limits_mode` 进 `_EXTENSION_FIELDS` 而非 `RE_ADD_FIELDS` —— 后者同时喂 `REQUIRED_TORRENT_FIELDS`(qbmanager.py:836 启动期对 qB torrent info fail-fast),放进去 5.2(无该字段)会启动即报 `QbCompatError`;`_EXTENSION_FIELDS` 同样并入 `_SNAPSHOT_FIELDS`/快照 slots,重加透传不受影响。
- **camelCase kwarg 判定**: facade `torrents_add` 纯透传,库(2026.8.1 无具名参)对未知 kwargs 经 `request.py _format_payload` 并进 POST data —— 键名必须与服务端 camelCase 一致(`shareLimitsMode`);snake_case 的 `share_limits_mode=` 在 2026.8.1 会发错键名被 5.3 静默忽略(静默失效陷阱,已写入 wire 守阵测试与 ops_mod 注释)。
- 快照 slot 缺省 None(非 "Default"): 5.2 wire 完全不变(库对 None 不发键,实测见 `tests/test_qbapi_wire.py`)。
- 升库三项复验通过: seedMode 双发保留(库 torrents.py:427-428)/ RAISE_ERROR 旗标未设 / setShareLimits 签名含 share_limits_mode。

## 实现计划

P1 facade 补参+守阵(🔴) → P2 跳检重加回传(🟡) → P3 升库 2026.10.1(🟡) → P4 真机升 5.3.x + 六项走查 + 基线重测(等 stable) → P5 文档回写(P4 后)。本轮实施 P1-P3;P4/P5 随 stable 发布另轮推进;P6 机会项各自立项(不在本计划)。

## 子任务状态表

| 步 | 内容 | 状态 |
|---|---|---|
| P1 | facade `share_limits_mode="Default"` + `_cmd_set_share_limits` 透传 + docstring 修正 + 请求体级守阵 | Done(2026-10-31) |
| P2 | `share_limits_mode` 进 `_EXTENSION_FIELDS` + record slot + `_skip_add_call` camelCase 透传 + 两分支测试 | Done(2026-10-31) |
| P3 | 升库 2026.10.1 + env.sync + 复验三项 + wire 守阵复跑 | Done(2026-10-31) |
| P4 | 真机升 qB 5.3.x stable + 六项走查 + 基线重测 | Open |
| P5 | 文档回写: 双版本口径 + 部署注记 + 根 README | Open |
| P6 | 🔵 机会项各自立项(getSpeedLimits 等; 用户拍板不纳入本计划) | Open |

## 进度日志

### R0 · 立档 (2026-10-31)

计划产出 → 用户拍板 D1-D4 → 实施 P1-P3: facade/调用点/compat/record/ops_mod 五处代码 + `tests/test_qbapi_wire.py`(4 条请求体级守阵, FakeQbServer 加 bodies 台账)+ test_ops 两分支 + 桩 recording;升库 2026.8.1→2026.10.1(升库前改动面定向全绿作解耦实证, 升库后全量见基线切片 26-10-31-1204)。P4/P5 待 5.3 stable 发布。

- 2026-10-31 12:09 拍板 D1-D4 后实施 P1-P3: facade share_limits_mode 补参+docstring 修正 / 重加回传落点改道 _EXTENSION_FIELDS + camelCase kwarg / 升库 2026.10.1; 全量与基线切片 26-10-31-1204; P4/P5 待 5.3 stable
