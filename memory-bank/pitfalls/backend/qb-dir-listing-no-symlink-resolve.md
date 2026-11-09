# qB 列目录(app/getDirectoryContent)不解析文件级 symlink —— 拿列目录元数据当「跟随读」代理的判定必假阴性

> 摘要: qB(Windows, 5.2.3 实测)目录列举对文件级 symlink 返回 reparse point 自身元数据(size=0/mtime=建链时刻), 不解析目标 —— 凡拿「列目录元数据」当「qB 能否经链接读数据」代理的判定必假阴性; 修复 = 链接对象判别(qB 条目 == 链接自身 lstat 双字段一致 → 不可判, skipped); 设计教训: 列目录语义 ≠ 打开读语义, 列举跟随行为跨平台/跨形态不一致, 证据通道要按形态分别验证。
> 触发: getDirectoryContent, 列目录, symlink, 链接跟随, 运行时F, 假阴性, 链接对象
**Refs:** memory-bank/plans/26-11-10-0230-plan-relocate-listing-false-negative.html

## 本篇只回答

「qB 侧链接跟随自检」为何对 file_links+symlink 形态必假阴性、怎么判别「qB 报的是链接对象而非目标数据」、修法与设计教训 —— 裂组口径回写在 `architecture/hr-groups.md` 整组迁移节, 现场恢复 runbook 在计划(Refs)§4.1, 本篇不复述。

### qB 列目录返回链接对象自身元数据(size=0/mtime=建链时刻), 拿它当「跟随读」代理比对 → 必假阴性

- **触发**: 任何拿「qB 列目录(app/getDirectoryContent)元数据」当「qB 能否经链接读数据」代理的判定(relocate 运行时F自检 `_d_evidence` name_filter 支即首例)。Windows qB 5.2.3 目录列举走 FindFirstFile 语义, 对文件级 symlink 返回 reparse point **自身**元数据、不解析目标 —— 拿它去和 dst 真文件 stat 比对必全不等 → 误判「qB 读不到」。
- **现象**(2026-11-10 生产 26586): job `jr-a2ce556d0165` Blood 组 8 颗(file_links)整组迁移 H:→I:,qB 搬迁+建链成功、本机穿透校验过,自检 NEGATIVE 判 `failed`(qb_side_check_failed),组视图裂两组;数据与做种全程无损,失败账与 H: 链接留现场(现场保留语义)。
- **判别**(三视角实测, 2026-11-10 只读):

  | 视角 | size | mtime | 读法 |
  |---|---|---|---|
  | qB `app/getDirectoryContent` 列 H: 内容根 | 0 | 1794242228 | qB 视角(自检实际拿到的东西) |
  | 本机 `lstat` H: symlink 本身 | 0 | 1794242228 | 与 qB 条目逐字一致 → qB 报的是链接对象 |
  | 本机 `stat` H:(穿透)/ `stat` I: / qB 列 I: | 5691143274 | 1789747190 | 三处一致(对照组) |

  分流: 同相对路径条目 (size, mtime) 与源侧链接自身 `lstat` **双字段一致** = 命中本形态(真伪不可判);与 dst 一致 = 正常 POSITIVE;两者都不符 = 真失败。
- **处置**: 修复 = **链接对象判别**(`relocate_proof._link_object_hit`, 2026-11-10): qB 条目与源侧同路径链接自身 `lstat` size+mtime 双字段一致 → 该条记 inconclusive(列目录语义未解析链接), 抽样全 inconclusive → `skipped`(不 fail 不挡武装, rt 记排查笔);汇总口径/源侧定位(lstat 失败保守按「不等」保真失败判定)/兼容面见计划 §3.1。代价 D1 拍板接受: symlink 形态自检对真失败降为不可判, 兜底 = 缺文件联动(整组暂停+MISSING)/errored 下游抓取。**设计教训**: 列目录语义 ≠ 打开读语义 —— 目录列举的跟随行为跨平台/跨形态不一致(junction 列举返回目标侧真实条目 / file_links+硬链接条目即同 inode 数据、size/mtime 与 dst 一致 / POSIX qB 列举 stat 跟随 symlink), 证据通道要按形态分别验证, 不能假设「列目录所见 = 打开可读」。
- **别踩面**: 未来任何「qB 视角 vs 本机视角」的元数据比对功能(自检/校验/一致性巡检/对账)都吃同一形态 —— 比对前先分清「qB 条目是链接对象还是目标数据」;新 qB 版本/新平台/新链接类型上线, 先实测列目录返回什么再写判定。
- **守阵**: `tests/test_relocate_proof.py` 三态: `test_link_follow_link_object_entry_skipped`(事故形态 → skipped) · `test_link_follow_resolved_target_still_positive`(目标元数据 → POSITIVE 不回归) · `test_link_follow_neither_target_nor_link_negative`(两不符 → NEGATIVE 不回归) · `test_link_follow_mixed_link_object_and_true_mismatch_negative`(混合抽样仍 NEGATIVE) · `test_d_precheck_branch_ignores_link_object_form`(预检 D 级常规支零改动)。
- **复发**: 0
