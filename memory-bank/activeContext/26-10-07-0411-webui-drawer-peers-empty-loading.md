# WEBUI 详情面板用户页空列表停"正在加载…"修复 — fetcher 落袋通知移进 finally (Done)

> 摘要: 用户报「WEBUI 种子详情页用户页显示好几秒'正在加载…', 然后才显示'暂无已连接用户'」。排查: 后端 `/api/torrents/{hash}/peers` 实测 2~3ms 非瓶颈, 经典包裹层走 Vue 响应式也无此窗口 —— 根因在变体渲染机制: 变体(dt07/08/09)**只在 `_dtNotify` 时重渲染**, 而列表 fetcher 原把通知放 try 块(数据落袋处), `peersLoading = false` 在 finally —— 通知那一刻 loading 还挂着, 空列表变体渲染"正在加载…", 随后 loading 清掉但无通知 ⇒ 停在旧态到下一拍 5s 轮询才翻空态。修法 = trackers/files/peers 三 fetcher 的 `_dtNotify` 移进 finally、在 loading 清掉之后(stale 响应仍不通知); trackers(dt04/05/06)与 files(dt10/11/12)是同款缺陷一并修, detail 不在列(general 变体不渲染 loading 态)。守阵: `test_web.py::test_drawer_tpl_registry_wiring` §4a 加次序断言(loading 清除先于通知)。新坑记入坑档 template-render.md(变体通知驱动渲染), kb.index 重建。不满足立档阈值(单会话、2 处源文件小修, 无任务档案)。test.full **2690 passed + 4 skipped / 99% / 33.8s**(基线切片 26-10-07-0411)。
> 最后活动: 2026-10-07 04:46

**Refs:** memory-bank/pitfalls/web-ui/template-render.md

## 现状

- **已提交并推上 Gitee**: `74b25a7b`(rebase 到远端分叉 `d2b2abf8` 之上后推送成功, 旧hash→新hash **74b25a7b→62e9d210**, Gitee develop = 62e9d210)。ship.commit 核 ref 步踩到坑档 [refs.md](../pitfalls/git/refs.md)「packed-refs 陈旧假红」(HEAD==loose 已一致, 仅 packed 落旧值)—— 失败行指引指向「分支 ref 被回退」条目, grep packed 才路由到正确条目, 按其处置(备份 .git → `pack-refs --all`)后 verify-ref 绿、补 `ship.push` 成功; 该条复发 +1, 并补「停手指引应直送本条形态」改进注。push 首跑报树脏挡路 —— 脏的是本会话自建的 `.git` 备份目录(未跟踪), 移出仓库后 sync 正常。
- 收尾件(坑档复发注 / 本切片 / kb.index 重建生成物)在推送之后落笔, 随下一笔提交入库。

## 追加: ship.commit 消息文件残留修复(2026-10-07 04:46, 同一切片续记 —— 未新建切片待授权)

用户报「my-commit-flow 有时未能正确删除 COMMIT_MSG_AI.txt」。实证: 本 clone `.git/COMMIT_MSG_AI.txt` 残留的正是上节 62e9d210 的消息 —— 上节核 ref 假红走了「提交失败、消息保留」出口, 随后手工修 packed-refs + 补 push 完成了入库, 消息文件从此无人消费(「保留现场」语义在恢复路径不闭环)。修法(commit.py 三处): ①核对失败出口判 `message_matches_head`(HEAD %B == 文件内容 = 分支 ref 已指向本次提交, 红只是 packed 滞后误报)→ 照常消费; ②入口残留扫描(约定文件内容 == HEAD 消息即删并拒跑, 在暂存计划之前 —— 树净形态下「没有可提交的改动」拒绝会把它挡死), 顺带拦旧消息被复用; ③unlink 3 次小步重试(Windows 瞬时共享冲突)。口径同步: 包 pipeline.md 消息文件节 / ship config.toml note / commit.py docstring。守阵 3 新 1 改(test_commit.py: consumed_on_verify_fail_when_head_matches / stale_message_residue_swept_at_entry / message_kept_when_nothing_to_commit; kept_on_verify_fail 改钉判定替身模拟 ref 真丢)。实测: test.pkg 145 passed; test.full 2690 passed + 4 skipped / 99%(16021/163/5472/143)与基线 26-10-07-0411 逐位持平(不触 src/)。

**提交与实机验证**(2026-10-07 04:46): 提交这轮 ship.commit 核 ref **又遇同款 packed-refs 假红**(refs.md 复发 +1 = 2, 停手指引仍误指「分支 ref 被回退」条目, 改进注已记但 verify_ref.py 代码未改属范围外) —— **修法①出口消费当场生效**: 输出带「消息文件已消费: HEAD 消息与之一致, 本次提交已落稳」, 处置(备份 .git → `pack-refs --all`)后 verify-ref 绿, 补 ship.push 一步过(入口扫描本轮未触发: 提交前消息文件已按协议重写, 本就应正常走)。提交 b7cea474 经 rebase 重放(远端领先 7 笔)为 **329a843c**, 已推 Gitee。本轮收尾件(refs.md 复发注 / 本段)随下一笔提交入库。
