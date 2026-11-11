# 计划 S6 真机复测·探测面收尾 + RM04-21 近似拓扑整组迁移: 四判据全 PASS(③经拍板近似拓扑替代走通)

> 摘要: issue `issues/26-11-11-2305-test-bt-backup-probe-real-retest.html` 复测(计划
> `plans/26-11-11-0259-plan-relocate-bt-backup-scalar-probe.html` §04 S6 判据①-④), 环境2
> C盘机, P1 判据①② + P2 判据③两阶段取证, P3 本轮清场记账, 四判据全 PASS(§01)。**③ 经用户
> 拍板近似拓扑替代走通**: RM04-21 钉死拓扑(R:/D: 异盘)本机不可达(C盘机无 R:), 同盘形态近似 ——
> 迁移落位 dst 零 recheck / 离线窗 daemon 改写 fastresume(journal + 字节三版双证) / 重启逐值读回
> / 收尾 done + 组键归一 dst。纯取证复测轮, 产品源码与用例代码零改动, 无基线更新(test.full 未跑)。
> 基线时间: 2026-11-12 00:29-01:53(P1 截图起 + P2 ts 01:14:52-01:53:51), 清场记账 02:00-02:30(P3)
> 基线 commit: 703ceb6c(分支 relocate-bt-backup-real-retest, 本地无远端; 实测全程 HEAD 未动)
**Refs:** memory-bank/issues/26-11-11-2305-test-bt-backup-probe-real-retest.html · memory-bank/plans/26-11-11-0259-plan-relocate-bt-backup-scalar-probe.html · memory-bank/testing/real-baselines/26-11-11-0804-real-relocate-bt-backup-probe.md · memory-bank/tasks/26-11-11-backend-relocate-bt-backup-probe.md

## 01 三态结论(四判据)

| 判据 | 三态 | 说明 |
|---|---|---|
| ① hit UI 回填→保存落盘 | **PASS** | 直探 hit → 草稿回填测试便携路径 → PUT 200 → 派生配置落盘(§03.1) |
| ② offline 组 | **网络层 PASS / UI 渲染形态不可达(产品面发现)** | 200 + manual-set + online=false 未自证(§03.2); 根因见 §05-6 |
| ③ RM04-21 形态整组迁移 fastresume 收尾 | **PASS(近似拓扑替代版)** | 四断言面全过(§03.3); 形态差异四条见 §04 |
| ④ 收尾清场 | **PASS** | 五步全走完(§06); guard 复跑判红如实记录(实例 down 预期形态) |
| 产品缺陷 | **0** | 全部行为与计划 §3.2 表 / N10 文档口径一致 |

## 02 环境指纹

| 项 | 值 |
|---|---|
| 环境 | 环境2(C盘机, 用户裁决改用 —— 本机 D: 空 CD-ROM, 环境1 EXE 不存在), `QBT_REAL_ENV=2`, qB v5.2.3 |
| 实例 | 主 56589 = `C:\Programs\qBittorrent-testing`(pid 轮换 7472→11604→17220) / 副 56590 = `...testing2`(pid=11088 全程未动), 均 firewalled; hit 期望路径 = 主便携 `C:\Programs\qBittorrent-testing\profile\qBittorrent\data\BT_backup` |
| 产品 webui | `commands run dev.webui -- --qb-port 56589 --no-open`; WEB 端口 OS 分配: P1 51407 → P2 59048; 派生配置 = `%LOCALAPPDATA%\Temp\auto-qb-dev-webui\config.yml`(schema v8, port="56589", skip_local_verify=true); **产品 data_dir 默认仓库根 auto-qb-data/**(journal/spec/daemon 账落彼处, 已删净) |
| P2 组成员 | 2 枚共享文件假种子(piece_len 16384/32768, 1MiB 单文件, real-fake): h1=97fcea9d / h2(mover)=52679e5e, src=`%LOCALAPPDATA%\Temp\qbt-fake-retest\src` → dst 同根(C盘机无 R:, 同盘近似) |
| 逐字证据全量 | `tests-real/.work/probe-retest/notes.md`(P1+P2 节) + `p2_evidence.json`(已随清场清掉, 事实蒸馏本切片) |

## 03 实测证据

### 3.1 判据① hit 回填→保存落盘(P1, PASS)

- 干净态直探: POST /api/relocate/bt_backup_probe → 200, `verdict=hit, online=true, storage_type=Legacy`,
  reason 逐字: `2 个候选合格, hash 自证消歧命中唯一: C:\Programs\qBittorrent-testing\profile\qBittorrent\data\BT_backup`
  (对账旧切片 0804 §3.2 的 4 候选: 本轮缺 `D:\Programs\qBittorrent-2` 生产侧候选(C盘机未装该实例);
  生产默认 profile 候选本轮目录不存在转不合格 ⇒ 3 候选中 2 合格 = 主便携(hash 命中) + 副便携(仅 queue);
  消歧机制同构)。
- UI(Playwright/Chromium, p1_hit_ui.mjs): 空态 placeholder 与 verdict 提示行(`已探测到 BT_backup 目录,
  已回填到上方输入框(尚未保存, 点「保存并应用」才落盘)`) → **草稿回填 = 该便携路径** → 「保存并应用」→
  **PUT /api/config 200**(payload tree.config.relocate.bt_backup = 该路径)→ actbar `已与磁盘同步`。
- 磁盘落盘逐字(派生 config L44-46): `relocate:` / `bt_backup:`(folded plain scalar 下行) = 该路径;
  safe_load = 精确路径, schema v8; 重载回读逐字一致。
- 截图 5 张: `attachments/26-11-12-0029-real-relocate-bt-backup-retest-01-home.png` /
  `attachments/26-11-12-0029-real-relocate-bt-backup-retest-02-editor-empty.png` /
  `attachments/26-11-12-0029-real-relocate-bt-backup-retest-03-hit-backfill-verdict.png` /
  `attachments/26-11-12-0029-real-relocate-bt-backup-retest-04-saved-reload.png` /
  `attachments/26-11-12-0036-real-relocate-bt-backup-retest-05-offline-probe-ui.png`。

### 3.2 判据② offline 组(P1, 网络层 PASS)

- real.down(56589 优雅退出)后 curl 直探: HTTP 200, `verdict=manual-set`(判据①已落盘 ⇒ manual-set
  分支优先: D5 显式>推断), `online=false, manual_set=true, storage_type=""`; reason 逐字:
  `relocate.bt_backup 已手动配置(显式 > 推断): 探测仅供核对, 配置一字不改(D5)`; 离线标注:
  `qB /torrents/info 不可达(APIConnectionError): 按离线降级, hash 自证未参与`。
- UI 态: 输入框零改动, actbar 保持 `已与磁盘同步`, 顶栏 qB 断开徽标亮 —— 但 verdict 渲染形态不可达(§05-6)。

### 3.3 判据③ 整组迁移四断言面(P2, 全 PASS)

| 断言面 | 证据 |
|---|---|
| 1 迁移落位 | POST /api/torrents/{mover}/location {location: dst} → started: mover 52679e5e / form file_links / alias_kind file / same_volume true; 日志逐字 `迁移发起(2 成员, 形态 file_links, mover 52679e5e)` + `别名作用域重归组 2 个种子` + `已武装收尾(别名 1 条, 形态 file)`; mover 落位 dst, 非 mover 留 src 经链接位可读; completion_on 前后相等(零 recheck), 零 error/missing, progress 全 1.0, job=armed, journal 无 rewrites 账 |
| 2 offline 窗 fastresume 改写 | 窗前路径键 = 相对形态(save_path lt 键 `..\..\..\..\Users\...\src` + qBt-savePath 正斜杠, 同盘符 ⇒ N10 相对化); real.down 优雅退出 1.4s; journal(auto-qb-data/relocate/jr-9c974d82dbd9.json) phase=rewritten: 非 mover keys=[save_path, qBt-savePath], unmatched=[qBt-downloadPath(空串, 良性)], mover=already(qB 自搬已自写 dst 相对键); **字节三版双证**: V0 窗前基线(存 .work, sha 9899fb1b…) → V1 .bak(qB 优雅 shutdown 写回, 仅四个会话元数据键变, 路径键不动 = 优雅写回硬证据) → V2 daemon 改写后(1487B): 双键 = dst 绝对形态(N10 文档口径) |
| 3 重启落位 | real.up 后逐字读回: 两成员 stalledUP progress=1 save_path=dst, completion_on 与迁移前锚逐值相等(改写链零 recheck); 启动瞬态 checkingResumeData → stalledUP 自愈 |
| 4 收尾归一 | job 终态 phase=done reason=finalized; 日志逐字 `收尾完成(全员核验通过, 删链门依赖清零, 已在线删除别名 1 条) —— 成员直读新位置 ...dst`; src hardlink lexists=False(删链门删净); 组键解码 = `[dst, ["rm04c21-retest.bin"]]`(归一 dst, 组不裂, 成员不在 singles) |

## 04 形态差异(RM04-21 钉死口径 vs 本轮近似拓扑, 拍板记录)

用户拍板: C盘机无 R:, 允许同盘近似走通判据③, 不改耐久文件。四条差异:

1. **别名 hardlink 非 symlink**: src/dst 同 C: 盘 ⇒ alias_fs 探测同盘选硬链(nlink=2), qB mover =
   同卷 rename; RM04-21 跨卷唯一选项 symlink。file_links 形态本体一致(1 文件 < 阈值 8)。
2. **fastresume 相对键走 N10 相对解析分支**: 便携 profile 与 basePath 同盘符 ⇒ 窗前键相对形态
   (RM04-21 钉死拓扑靠绝对形态) —— 恰好覆盖 N10 相对分支; 改写产物 = 绝对 dst 形态(文档口径)。
3. **收尾链跨产品进程重启完成**: 原产品实例(webui+daemon)~01:21 静默死亡(§05-1) ⇒ journal rewritten
   相位由新实例启动对账镜像合并 → ACT_VERIFY 收尾 —— 意外额外验了重启对账消费面。
4. **组键归一终态经「新实例带 tracker 配置启动重新归组」观测**: grouping 为内存态不落盘, 旧实例组随
   死亡丢失; 迁移驱动的组跟随有旧实例「别名作用域重归组 2 个种子」日志行为证。

## 05 计划外发现(只记录不修, 逐字照 P2 报告)

1. **产品 webui(pid 6468, 00:21:26 起)与其拉起的回收 daemon(pid 13160)于 ~01:21 静默死亡**: 产品最后
   state 落盘 01:20:57, daemon 最后心跳 01:21:08(恰 qB down 时刻); 日志止于 01:16:44 无任何错误行,
   WER 无 python 崩溃事件, 原因未深挖。后果: daemon 窗内改写未发生, 经文档化手动入口补跑(见#2);
   产品重启后整链收尾仍走通(健壮性实证)。
2. **手动补跑 = 产品自留 CLI 入口** `python -m auto_qb.tools.recycle_daemon --data-dir auto-qb-data
   --host 127.0.0.1 --port 56589`(模块 docstring 明示「可手动运行做验证」): 零 wrapper/零旁路, 窗判据
   走产品 L1 实例级证据链(obs 账 owner pid=11604 死证 + 新面孔无害化吸收 11088 + 端口拒连 ⇒ 立即进窗),
   与产品拉起完全同一条代码路径。
3. **dev.webui 每次启动无条件重生成最小配置**(relocate/trackers 的 PUT 落盘被冲掉), WEB 端口 OS 分配
   (P1 51407 → P2 59048); P1 落盘的 relocate.bt_backup 键在 P2 被冲一次(重走 PUT 恢复); 产品实际
   data_dir 默认仓库根 auto-qb-data/(journal/spec/daemon 账落 prod 数据目录, 已随清场删净, job 已终态
   无重放风险)。
4. **未匹配 tracker 配置的种子不进 torrents_added 相位**(qbmanager matched_added 过滤) ⇒
   grouping._assign_new_torrent 不跑 ⇒ **组不成立** —— 最小配置(trackers:{})下必须补一条 tracker
   域名条目种子才会归组(RM04 用例配置自带 trackers.rm04fake 同款, 此为其存在原因)。
5. **runner.cmd_guard 未传 skip_tags**: guard CLI 行「真实种子 N 个」把 real-fake 计入并暂停(real.seed
   里的 guard 行传了 skip_tags 所以显示 0)。P1 P2 两轮都撞(复发 2 次); 我方种子被暂停为 stoppedUP。
6. (P1 已记两条备查) offline 服务端探测延迟实测 25.16s/17.14s > 前端 AQB_FETCH_TIMEOUT_S=15s ⇒
   offline verdict 渲染形态 UI 结构性不可达; qB 5.2.3 /api/v2/torrents/resume 404(本轮未再触碰,
   探针只认 BT_backup hash 集无影响)。

## 06 收尾状态(判据④ 清场五步, P3 02:00-02:30)

1. **停 webui**: 先核验 59048 监听进程归属(python.exe, 命令行含 `-m auto_qb Temp/auto-qb-dev-webui/config.yml`)
   → `commands run dev.port-kill -- 59048` → pid 15736 killed(先核身份再定点杀; 未用 taskkill)。
2. **种子清场**: `real.seed.rm -- --port 56589 --all --yes` → `[ok] 删除 ae370f14 real-probe-l0.bin + 文件`;
   `real.seed.rm -- --all --yes`(56590) → 命中 0(P2 组成员已随 P2 step8 删净); `real.seed.clean -- --yes`
   → `[ok] 已清空 tests-real\.work`(202 文件 989.3K, 含 probe-retest 证据 —— 事实已蒸馏本切片)。
3. **实例下线**: `commands run real.down` → `[ok] 56589 优雅退出 pid=17220` / `[ok] 56590 优雅退出 pid=11088`(3.0s)。
4. **guard 复跑**: rc=1 判红 —— `[FAIL] 56589: 端口 56589 没有监听进程(实例没起? 用 real.up 拉起)` +
   `[FAIL] 56590: 同款`。**如实记录**: 实例已按第 3 步 down, guard 的静态端口核验判红属预期形态,
   不硬凑绿; 种子占用面已由第 2 步 rm 输出证净(两实例命中合计 1, 已删)。
5. **零遗留核对**: `git status` 工作树净; 仓库根 config.yml 零触碰; auto-qb-data/relocate/ 已空
   (P2 step8 删净 spec/journal/obs 四件)。**遗留备查(未动, 红线区)**: auto-qb-data/config.yml.bak 与
   .v1.bak(mtime 01:43/01:53, P2 窗口内产生, 内容 = P2 测试配置快照) —— data_dir 默认落仓库根的连带
   产物, 留主会话/用户裁决; Temp 派生配置 relocate.bt_backup 保持 P1 值(下次启动重生成, 无害);
   Temp/qbt-fake-retest 仅剩空目录壳。
- 本轮**纯取证复测轮**: 产品源码与用例代码零改动, 不跑 test.full, 无基线切片更新。
- 计划外五条是否入池由主会话向用户确认(本切片只记录)。
