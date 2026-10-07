# 2771 —— ui_harness peers 数据补全 + e2e peers 内容断言基线

> 摘要: 专题 webui-peers-harness(认领并修复 issue 26-10-07-2309)—— 桩服务补合成 `sync/torrentPeers`
> 数据 + 新增 `e2e/drawer-peers.spec.mjs`(双皮肤 @fast)。**pytest 侧零改动**(e2e spec 不被 pytest 收集,
> 本次未新增任何 pytest 用例)⇒ 相对上基线 26-10-08-0157(2771+4)逐位持平; 覆盖增量在 e2e 轨道
> (全量轮 +2 test)。
> 档案: memory-bank/tasks/26-10-08-test-webui-peers-harness.md
> 基线时间: 2026-10-08 02:23

**Refs:** memory-bank/issues/26-10-07-2309-test-webui-peers-harness.html,memory-bank/tasks/26-10-08-test-webui-peers-harness.md

## test.full 实测

- 分支: develop(已同步 `f5315a8d`; 工作树含本次改动与回写的未提交改动时实测)
- 命令: `commands run test.full`(Windows, 单次采样 —— 耗时口径见 testing/baseline.md「必须带区间」)
- **实测 (Windows)**: **2771 passed + 4 skipped, 0 failed, 58.1s, 覆盖率 TOTAL 99%**
  (16476 语句 / 165 未覆盖 / 5694 分支 / 149 partial; 门槛 98% 达标, 实测 98.56%)
- 相对上基线 [26-10-08-0157](26-10-08-0157-webui-qb-traffic-seed-vacuum.md)
  (2771 passed + 4 skipped @ 42.3s, 16476 语句 / 165 未覆盖 / 5694 分支 / 149 partial):
  passed **±0** / 语句 **±0** / 未覆盖 **±0** / 分支 **±0** / partial **±0**。
- 增量明细: **无 pytest 侧新增** —— 本次改动为桩脚本数据面(`scripts/ui_harness.py`)+ 新增 e2e spec
  (`e2e/drawer-peers.spec.mjs`), 二者均不进 `testpaths(tests/)`。4 skipped 为 Windows 侧 POSIX 专属存量。
- (首次采样时收尾回写未完成, 两条 KB 守卫 `test_claim_chain_is_bidirectional` / `test_gen_all_check_is_green`
  先红; 补齐档案/基线/索引后复跑转绿, 上列数字为回写后实测。)

## 本专题面要点(非 pytest)

- 桩侧: `scripts/ui_harness.py` 新增 `_PEER_SCENES`(7 场景) + `_make_peers_response(i)`(对端数 1~7 轮转,
  `peers` 为 `"ip:port"` 键的 dict, 与真 qB 同形), 起盘按 `enumerate(torrents)` 写入 `mgr.client.peers_map`。
- e2e 侧: `e2e/drawer-peers.spec.mjs` 双皮肤 `@fast` —— 开详情抽屉 → 切「用户」页签 → 断言经典 peers 表
  渲染出对端行(>0)+ 首行地址列 `ip:port` + 空态「暂无已连接用户」不出现。
- 红验: 临时禁用桩注入 ⇒ 本 spec **2 failed**(prism/atlas, `table.drawer-table` 不可见); 还原 ⇒ **2 passed**。
- e2e 全量轮: `commands run dev.e2e` **94 passed / 10 skipped / 0 failed(3.4m)**(含新增 2 条)。
- @fast 门禁: `npm run test:e2e:fast` **8 passed(19.4s)**(改前 6, +2 = 本次新增双皮肤)。
- 无 API / 响应形状 / 存储 / 配置 / 生产前端改动; 回滚 = revert 桩脚本与 spec 文件。

## 对照判据(后续沿用)

- 以本切片(2771+4 / 16476 / 165 / 5694 / 149)为对照点: 预期 passed 只升不降、未覆盖 / partial 不升。
- 回退先查本次改动: `scripts/ui_harness.py` 的 `_PEER_SCENES`/`_make_peers_response` 与起盘注入循环;
  `e2e/drawer-peers.spec.mjs`。
