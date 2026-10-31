# 2698 —— tracker URL 脱敏方案 B S4b 收口基线(5 组守阵红验 + conventions 回写完成)

> 摘要: 实施计划 [26-10-07-0055](../../plans/26-10-07-0055-plan-tracker-url-sanitize-planb.html)
> S4b 收尾基线。S1–S3(mask 函数 R1–R9 / 编辑下线 / 收口切换)与 S4a(5 组守阵落码)之后,
> 本轮完成逐组红验(5 组全红全还原, 明细见下)与 `conventions/code-style.md`「凭据脱敏」条
> 升级(越界即脱敏), 全量实测落本切片。本分支首条基线 —— 此前该分支无切片, 增量对照取
> develop 侧最新一条 [26-10-07-0138](26-10-07-0138-ship-autoresolve-stale-config.md)。
> 基线时间: 2026-10-07 03:37

**Refs:** memory-bank/tasks/26-10-07-webui-tracker-url-sanitize.md,memory-bank/plans/26-10-07-0055-plan-tracker-url-sanitize-planb.html(§04 S4 / §06 验收)

- 分支: feat/tracker-url-sanitize-planb @ **a46c1df7**(S4a 守阵落码; 本轮会话开工 sync 因离线
  拿不到远端, 按本地 a46c1df7 实测; 测量时工作树仅含 conventions 回写与本切片两处 memory-bank 改动)
- 命令: `commands run test.full`(Windows —— 耗时口径见 [../baseline.md](../baseline.md)「必须带区间」)
- **实测 (Windows)**: **2698 passed + 4 skipped + 2 failed(存量, 见下), 覆盖率 TOTAL 99%(98.54%)**。
  语句 **15863** / 未覆盖 **163** / 分支 **5496** / partial **143**。
  耗时: 两次采样 **39.31s** / **40.13s**(wrapper 40.2s) ⇒ 区间约 **39~41s**。
  副作用台账: 共 4755 条, 越界 0 条(两次采样一致)。
- **存量 2 红**(与本计划无关, 开工前已在树上): `tests/test_memory_bank.py` 的
  `test_kb_active_context_slices_are_valid` 与 `test_timekit_check_is_green_on_current_kb` ——
  `memory-bank/activeContext/26-10-06-0751-webui-detail-panel-design.md:4` 的「最后活动」为叙述文本
  而非严格 `YYYY-MM-DD HH:MM`。develop 侧 0138 基线同名守卫绿(该分支树上切片文件为旧拷贝);
  离线同步不了 develop 的修复, 按范围守恒不入本轮修, 留收尾流程处置。
- 相对上一条 [26-10-07-0138](26-10-07-0138-ship-autoresolve-stale-config.md)
  (2686 + 4 / 16021 / 163 / 5472 / 143, develop @ `20bd2157`):
  收集口径 2690 → 2704 = **+14**(test_utils.py mask 组 6 条 + test_web.py 8 条 = 守阵①②③④⑤ +
  `test_cmd_remove_tracker_mask_roundtrip` + 详情面板守阵 2 条); planb 侧净增 **12 条**
  (mask 6 + 守阵/roundtrip 6)。**无新增红** —— failed 2 条即上述存量 KB 守卫
  (develop 绿、本分支树红), 新增 14 条全过。语句 −158 / 分支 +24 / 未覆盖与 partial ±0:
  分支侧可归因的是 planb S1–S4a 的 src 净改(infra/utils.py +84 mask 规格; S2 编辑链路删除;
  commands/torrent_cmds/torrent_detail/qbapi/record/views 改道), 其余含两分支各自未互合的
  并行提交, 不逐一归因(体例同 [26-10-06-1620](26-10-06-1620-webui-detail-panel-s7.md) 的处理)。
- **红验五组**(临时改源码 → 守阵红 → `git checkout --` 还原 → 复跑回绿; 全部还原后
  `git status --short` 除 memory-bank 回写外零残留):
  1. 守阵①+⑤(`torrent_detail.py` 路由 lambda 去掉 `mask_tracker_entry` 改回裸透传):
     ①红于 :11541「url 应为 mask 值」(响应体拿到原文); ⑤红于 :12053「_cached_read 取数
     lambda 里没有 mask_tracker_entry」(canary 先于①报)。还原后 2 passed。
  2. 守阵②+roundtrip(`commands.py _cmd_remove_tracker` 改回直传 mask 值):
     ②红于 :11950「qB 必须恰收到一次 remove 且 urls == A 的原文」(实测收到 mask hash 值);
     roundtrip 红于 :11906「qB 必须收到原文」。还原后 2 passed。
  3. 守阵③(`torrent_cmds.py` 临时加回 `/api/torrents/{hash}/trackers/edit` 端点):
     红于 :11972「trackers/edit 必须不落到任何处理器(404/405), 实际 200 —— 路由被加回来了?」。
     还原后 1 passed。
  4. 守阵④(`_trackers_baseline` key 临时过 `mask_tracker_url`):
     红于 :12034「基线 key 必须等于 fake client 的原文 url」(key 集合变成 mask hash 值)。
     还原后 1 passed。
- 改动面(本轮留存): `memory-bank/conventions/code-style.md`「凭据脱敏」条升级
  (日志前脱敏 → **越界即脱敏**, 补 mask_tracker_url/entry 外发口径 + R1/R6 铁律 + 守阵指针)
  + 本切片。零 `src/`、零 `tests/` 残留。未跑 `kb.index`(协调者收尾统一重建)。
- 行尾: 本切片为 **LF**(仓库 2026-10-02 起 `text=auto eol=lf`)。
