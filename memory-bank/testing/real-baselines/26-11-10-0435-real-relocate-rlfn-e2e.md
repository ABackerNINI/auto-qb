# relocate 运行时F假阴性修复: 真机闭环 E2E(2 颗共享文件 file_links+symlink 形态)—— 13 项全 PASS

> 摘要: 计划 `plans/26-11-10-0230-plan-relocate-listing-false-negative.html` §03.3 S4a(环境1 D盘机, 主实例 36595)。
> 2 颗假种子共享同一 1MB 文件(异 infohash), src=R:/qbt-fake(异盘) → 整组迁移 dst=.work(D:) →
> **qB 侧自检 skipped**(「未解析文件级 symlink」, 修复生效第一证据; 不再 qb_side_check_failed)→ armed →
> real.down 优雅退出窗(wrapper 名册窄化开窗, 授权旁路)→ daemon 改写非 mover fastresume → real.up 重启 →
> 全员 save_path==dst + 删链门删净别名 + job done + **组不裂**。生产 16585/26586 全程零触碰(只读识别留痕)。
> RM04 用例沉淀升档不在本切片范围(另一子任务)。产品 src/ 零 diff。
> 基线时间: 2026-11-10 04:33-04:38
> 基线 commit: 7f0e07c0
**Refs:** memory-bank/plans/26-11-10-0230-plan-relocate-listing-false-negative.html · memory-bank/pitfalls/testing/relocate-window-machine-roster.md · tests-real/tools/daemon_window_wrapper.py, memory-bank/tasks/26-11-10-backend-relocate-listing-false-negative.md

## 01 验收数字

实验 harness `tests-real/.work/relocate-rlfn-e2e/run_exp.py` 六相位(setup/seeds/migrate/window/verify/cleanup),
全链墙钟 04:33-04:38(t0=04:32:55, 实测总耗时 272.95s)。各相位命令面:

```text
commands run real.env            # 环境1(D盘机) 主 36595 / 副 36596
commands run real.up -- --port 36595    # 两次: 开工 + 收尾窗后重启(各 3s 启动成功)
commands run real.guard          # 开工: [ok] 36595 pid=32856 vv5.2.3 firewalled 真实种子 0 个
                                 # (36596 FAIL 行 = 按实验设计下线: wrapper 名册按 testing* 前缀同时覆盖两实例)
commands run real.down -- --port 36595  # 两次优雅退出, 各 1.4-1.5s pid=32856/10228
commands run real.seed.clean -- --dir R:/qbt-fake --yes   # 0 个文件(证据落点含 evidence/ 故不用无参全扫)
commands run real.seed.list -- --port 36595  # 收尾: 共 0 个种子, 自造 0 个
```

核心断言链(逐条见 §03): skipped 日志留痕 + armed + rewritten + done + 组归一, 13 项全 **PASS**, 0 FAIL, 0 BLOCKED。

## 02 环境指纹

| 项 | 值 |
|---|---|
| 环境 | 环境1(D盘机), `QBT_REAL_ENV` 未设(按 EXE 探测) |
| 实例 | 主 36595 = `D:\Programs\qBittorrent-testing`(pid 32856 → 重启后 10228); 副 36596 全程下线(开窗判据要求两测试实例全下线) |
| 实例版本 | qBittorrent v5.2.3(与生产同版本) |
| connection_status | `firewalled`(开工自检, 非 disconnected —— §2.4 假红陷阱已核) |
| 真实种子 | 36595 开工 0 个 / 收尾 0 个(整实例 0 种子, 保护面为空) |
| 生产实例 | 16585(pid 17488)/26586(pid 18056) 常驻在跑 —— 实验全程零请求零触碰(仅 netstat 只读识别留痕) |
| BT 监听 | 36595=26803 |
| 拓扑 | src=`R:/qbt-fake/rlfn-exp`(R: 内存盘, 与 qB CWD D: 异盘 ⇒ fastresume 保存键绝对形态) → dst=`tests-real/.work/relocate-rlfn-e2e/dst`(D:, 与 src 异盘 ⇒ file_links+symlink; 1 文件 < 阈值 8) |
| 成员 | 2 颗共享同一 `rlfn.bin`(1MB, 同内容异 infohash: piece_len 16K/32K)—— 跨站辅种组形态(Blood 组 8 颗共享一个 mkv 的最小化) |
| daemon 离线窗 | 授权旁路(用户 2026-11-10 AskUserQuestion「授权旁路(推荐)」): 实验进程内替换 `_spawn_daemon`(产品 docstring 自留测试接缝)经 `tests-real/tools/daemon_window_wrapper.py` 拉起 daemon; 名册窄化 `D:\Programs\qBittorrent-testing*` 前缀; 端口拒连+30s 稳定窗两证产品原样 |
| 产品解释器 | `.venv` → CPython(uv 管理); 产品配置 = tests-real/.work/relocate-rlfn-e2e/case/config.yml(schema_version 6, grouping on, relocate.enabled=true, bt_backup 查表) |

## 03 逐条断言与实测结果

job = `jr-c3500b132cfc`; mover = `1355226b`(save_path 先翻 dst), 非 mover = `d43fd97d`。

| # | 断言 | 三态 | 实测结果 |
|---|---|---|---|
| 1 | real.guard 自检 + real.up + connection_status 非 disconnected | **PASS** | `36595 pid=32856 vv5.2.3 firewalled 真实种子 0 个`; guard.check_online 过(非 disconnected) |
| 2 | 产品实例(tests-real 派生配置, relocate.enabled=true + bt_backup 指测试实例 profile) | **PASS** | WEB 45s 内起; 配置含 `bt_backup: {"127.0.0.1:36595": "D:/Programs/qBittorrent-testing/profile/qBittorrent/data/BT_backup"}`; 生产配置零触碰 |
| 3 | 2 颗共享文件假种子 + 归组成组 | **PASS** | `/api/groups` 两颗同组(n_members=2), 组键 base64url 解码 = `["R:/qbt-fake/rlfn-exp", ["rlfn.bin"]]`(归组键 = save_path + 文件相对路径); 另有第 3 颗对照不存在(组内仅 2 成员) |
| 4 | 整组迁移发起(origin=web 语义) | **PASS** | `POST /api/torrents/{hash}/location {confirm:true}` → 回执 `cls=started`, 日志「迁移发起(2 成员, **形态 file_links**, mover 1355226b)」—— 事故形态复现 |
| 5 | **qB 侧自检 skipped(修复生效第一证据)** | **PASS** | 日志 `qB 侧自检跳过(qB 列目录未解析文件级 symlink(条目=链接对象元数据), 真伪不可判(rlfn.bin))`; 全程零 `qb_side_check_failed` 行(修复前此形态判 NEGATIVE → failed, 即生产事故链) |
| 6 | job armed(已武装收尾) | **PASS** | 「已武装收尾(别名 1 条, 形态 file)」; state.json `relocate.jobs.jr-c3500b132cfc.phase=armed` |
| 7 | armed 现场: src 链接位 symlink + 非 mover fastresume 未被触碰 | **PASS** | `R:\qbt-fake\rlfn-exp\rlfn.bin` lstat size=0, readlink=`\\?\D:\...\dst\rlfn.bin`, 穿透读 1MB; 非 mover fastresume 三键仍指 SRC(`qBt-downloadPath` 空串为良性特类) |
| 8 | real.down 优雅退出 → wrapper 名册窄化开窗 | **PASS** | wrapper 决策日志: 36595 在线时 `all_qb=3 test_qb=1 refused=False => absent=False`; 优雅退出后 `all_qb=2 test_qb=0 refused=True => absent=True` 连续 ≥30s(STABLE_WINDOW)→ 开窗; **生产 2 颗全程在场不挡窗**(名册窄化实证) |
| 9 | daemon 改写账落盘(fastresume save_path → dst) | **PASS** | journal `rewrites`: mover=`already`(keys=[save_path, qBt-savePath]); 非 mover=`rewritten`(keys 同上, unmatched=[qBt-downloadPath] 空串键良性); 改写产物字节三路径键全指 dst 绝对形态; journal 相位翻 `rewritten` |
| 10 | real.up 重启 → 全员 save_path==dst | **PASS** | 重启后全员 save_path == `...\relocate-rlfn-e2e\dst`, progress 1.0, 零 checking, 零 error/missing 状态 |
| 11 | job 终态 done + 删链门删净别名 | **PASS** | 「收尾完成(全员核验通过, 删链门依赖清零, 已在线删除别名 1 条)」; `phase=done, reason=finalized, alias_paths=[]`; `R:\qbt-fake\rlfn-exp\rlfn.bin` lexists=False |
| 12 | 组不裂(两颗仍同组) | **PASS** | `/api/groups` 终态两颗仍单组(n_members=2), 组键整体迁移为 `["D:/Projects/.../relocate-rlfn-e2e/dst", ["rlfn.bin"]]`(全期无裂组两行) |
| 13 | 收尾清场(不残留自造物 + 生产零触碰) | **PASS** | 产品优雅退出(sentinel SIGTERM); qB 内自造 2 颗删净(连数据); `R:/qbt-fake` 与 dst/case 目录已清; BT_backup 逐种子文件开工前后零改动(仅 qB 自身 `queue` 记账文件 mtime 会话期合法变化, 留痕 cleanup.json); 实例回到开工态(双实例下线) |

## 04 改动面与取证

- **产品 src/ 零 diff**: 本实验只读运行产品(修复本体 = 提交 7f0e07c0 的 relocate_proof.py 链接对象判别支, 本轮真机验证其行为)。
- 实验面: `tests-real/.work/relocate-rlfn-e2e/`(gitignored): `run_exp.py`(六相位 harness, 含 daemon 旁路 runner)
  + `evidence/`(authorization.md 授权记录 · bypass_authorization.json · config_used.yml · receipt.json ·
  log_armed_excerpt.txt / log_verify_excerpt.txt(修复证据行原文) · journal_after_window.json ·
  fr_at_armed/fr_after fastresume 原始字节 · wrapper_log_excerpt.txt · group_before/group_after.json ·
  seeds/armed/verify/cleanup.json · timeline.json · cmd_*.txt 命令面留痕)。
- wrapper 决策日志: `tests-real/.work/tools-daemon-wrapper/daemon_wrapper.log`(wrapper exit rc=0, 宽限优雅退位)。
- 本轮 harness 侧两处断言校准(非产品缺陷): ①armed/改写后 fastresume 的空串 `qBt-downloadPath` 为良性特类
  (daemon unmatched 原样保留, E2c 同口径), 相等性断言需剔除空值; ②BT_backup 残留比对面只认逐种子文件,
  qB 自身 `queue` 记账文件会话期合法变化(同一形态任何 real.guard/优雅退出轮都会发生)。
- 范围外观察(记录不顺手修): 无新增 —— 终态留账无清理出口与启动计数文案两件已按计划 S0 入池; job done 后
  `R:/qbt-fake/rlfn-exp` 空内容根目录由 harness 清理(产品不删空目录, 与生产 H: 现场一致, 设计内)。
- 收尾核净: 36595 收尾 0 种子 / 0 自造; R:/qbt-fake 空; 副实例 36596 全程未起; 生产零触碰; 本轮未 commit/push。
- 用例落位(§03 预告的沉淀子任务, 2026-11-10 完成): 13 断言面沉淀为耐久用例 RM04-20 `tests-real/rm04_relocate/test_rm04_relocate_window.py`(L2, real.run 两遍 PASS 92.7s/91.8s + real.guard 还原过; 拓扑/授权旁路/断言逐条跟随本切片, 细节见用例 docstring)。
