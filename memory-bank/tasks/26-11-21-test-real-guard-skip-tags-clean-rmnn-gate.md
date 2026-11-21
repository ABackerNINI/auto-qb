# 26-11-21-test-real-guard-skip-tags-clean-rmnn-gate — 修 issue 26-11-21-0639 + 26-11-21-0638: guard 豁免单点兑现与 clean 整扫 B-严格闸

**Status:** In Progress
**Added:** 2026-11-21
**Updated:** 2026-11-21
**Summary:** 修 issue 26-11-21-0639 + 26-11-21-0638: guard 豁免单点兑现与 clean 整扫 B-严格闸
**Topics:** test-real-guard-skip-tags-clean-rmnn-gate
**Refs:** memory-bank/issues/26-11-21-0639-bug-real-guard-seed-count-real-fake-mislabeled.html, memory-bank/issues/26-11-21-0638-bug-real-seed-clean-rmnn-inner-blindspot.html, memory-bank/testing/baselines/26-11-21-1013-test-real-guard-skip-tags-clean-rmnn-gate.md

## 本篇只回答

真机轨两个守卫面缺陷怎么修与怎么钉: ①guard「真实种子」计数为何把 real-fake 假种子计入、豁免语义如何兑现成单点(issue 26-11-21-0639); ②real.seed.clean 证据保护闸的 rmNN 内层盲区用什么闸面形态收口(issue 26-11-21-0638)。

## 原始请求

1. 「修复 memory-bank/issues/26-11-21-0639-bug-real-guard-seed-count-real-fake-mislabeled.html memory-bank/issues/26-11-21-0638-bug-real-seed-clean-rmnn-inner-blindspot.html」(2026-11-21)。
2. 0638 修法方向 issue §06 标注「方向待裁决」, 经 AskUserQuestion 拍板: **B-严格**(rmNN 内层有文件整扫即整单拒跑, 空壳照收, --dir 豁免口不变)。

## 思考过程与决策

- 0639: 根因 = snapshot 的 skip_tags 豁免语义定义了但三处调用全走缺省空元组(rm08 conftest docstring 甚至早已声明「归零跳过 real-fake 标签」, 实际从未兑现)。决策: 标签常量收敛 lib 单点 `guard.REAL_FAKE_TAG` + 新增 `guard.fakes(qb)` 认领单点(seed.py TAG 改别名、_fakes 委托, seed_bulk_boot 经导入归一); 三处调用**显式**传参而不改缺省值(缺省改豁免会静默改变「想全暂停」调用方的语义, 显式 + 静态守阵更符合仓库 fail-closed 口径); cmd_guard/pause_all 输出改双口径(真实 N / 自造 M), 计划/切片的环境指纹誊写天然双数。conftest 保护面收窄的影响面已核实: 各用例前置自删残留(rm_all_fakes + wait_until), 无用例依赖「假种子被守卫暂停」。
- 0638: 建议两案(A 证据形态点名 / B 只删 .torrent/.bin 自建形态)都被否——形态清单/形态过滤会随证据落点演化失守(证据也可能落成 .bin, RM11 假种子恰是 .bin)。拍板 B-严格: 「有文件即拒」零维护、fail-closed, 与黄金法则「保守默认」同构; 零文件空壳豁免(没有文件就没有可丢的证据)保住 RM11 实证的「唯一需清 = 空目录壳」日常态; 拒跑信息逐 rmNN 列内层文件数 + 前 5 路径 = 把「clean 前先 ls 盘点」纪律机械化成免费盘点。
- 评审 4 轮: 轮1 minor(pause-all help 文案未随行为改)+nit(38 份实损分解口径); 轮2 零发现; 轮3 nit(注释「顶层」指涉歧义, 自行裁量修); 轮4 零发现出口。检 2/3 过检(R3 条目修后引文失配机械弃, 先例见切片 webui-refresh-inflight-coalesce)。

## 实现计划

总体思路(无分步计划文档, 两 issue 修法直接落在各自 §06 建议的收紧方向): 先回写后评审 —— 代码与守阵落地 → issue 翻 Done + 修复后补充 → 坑档/真机文档同步 → test.full → 评审循环至零 actionable。

## 子任务状态表

| 步 | 内容 | 状态 |
|---|---|---|
| 1 | guard.REAL_FAKE_TAG + fakes() 单点; 三处调用传 skip_tags; cmd 双口径 | Done(2026-11-21) |
| 2 | seed.py B-严格闸(CASE_DIR_RE/_dirty_case_dirs)+TAG 收敛+_fakes 委托 | Done(2026-11-21) |
| 3 | 守阵 6 条(静态 skip_tags 带活性探针/snapshot 语义/cmd 双口径×2/rmNN 拒跑/空壳契约)+docstring 测试计划 | Done(2026-11-21) |
| 4 | 两 issue 翻 Done+复验+修复后补充; 坑档处置行升级; real-machine.md §2.4; real 包 clean 文案 | Done(2026-11-21) |
| 5 | 评审 4 轮零 actionable; test.full 6665P/6S 99% | Done(2026-11-21) |

## 进度日志

### R0 · 立档 (2026-11-21)

单轮完成: 两 issue 修复 + 守阵 + 回写 + 评审 4 轮闭环, 细节见上方决策与 issue 修复后补充; 数字见基线切片。

- 2026-11-21 10:12 修 0639+0638 双 issue: guard 豁免单点 REAL_FAKE_TAG/fakes + 三处 snapshot 调用显式传 skip_tags + cmd 双口径; clean 整扫 B-严格闸(rmNN 内层有文件整单拒跑+拒跑信息自带清单, 空壳照收, --dir 豁免口不变); 守阵 6 条(静态 skip_tags 守阵带活性探针+snapshot 语义+cmd 双口径+rmNN 拒跑+空壳契约), 评审 4 轮 3 发现(minor pause-all help/nit 38 分解/nit 指涉歧义)全修零 actionable, test.full 6665P/6S 99%
