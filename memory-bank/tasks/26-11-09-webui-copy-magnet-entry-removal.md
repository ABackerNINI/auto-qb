# 26-11-09-webui-copy-magnet-entry-removal — 复制 magnet 三处入口移除 (issue 26-11-09-0639)

**Status:** Done
**Added:** 2026-11-09
**Updated:** 2026-11-09
**Summary:** 26-11-08-0043 掩码落地后的入口处置: 用户拍板候选①移除入口, 三处入口下线 + copyTorrentInfo 收窄 name/hash + 注释/守阵同步; 评审 2 轮终轮零 actionable; 全量绿见 kb.baseline
**Topics:** webui-copy-magnet-entry-removal
**Refs:** memory-bank/issues/26-11-09-0639-bug-webui-copy-magnet-masked-degrade.html

## 本篇只回答

issue 26-11-09-0639(复制 magnet 出掩码废链接)的入口处置怎么修的、修到哪条边界。

## 原始请求

1. 用户: 「修复 memory-bank/issues/26-11-09-0639-bug-webui-copy-magnet-masked-degrade.html」(用户指派认领)。
2. 拍板(AskUserQuestion): 修法候选①「移除入口」 vs ②「专用端点按需取原文」—— 用户选 **① 移除入口**。

## 思考过程与决策

- 三处入口(右键菜单/Shift+KeyG/抽屉标识卡 02+03 模板)全部从详情响应取 `d.magnet_uri`, 而 26-11-08-0043 后该字段入库即 tr= 掩码 —— 复制出的链接私站无法 announce, 功能语义已死, 移除是口径最紧且改动最小的处置。
- 生产 `config.yml:72` 存量布局引用 copy-magnet id: **红线不动**, 由 `ctxMergeLayout`「用户序里的未知 id 忽略(换版本不丢布局)」口径兜住(ctx_menu.js 合并层, 校验层本就宽松不查 id 存在性), 零校验风险。
- `copyTorrentInfo` 顺带收窄: 去 magnet 分支后不再 await, async 去掉(调用点仅 ctx_menu act 与 `_kbEditAct`, 返回值无人消费)。
- 复评提醒: 远端 tip 在评审窗口内前移(706e360c→77b649fc, 纯 docstring 修复批, 与本批零文件重叠), 修复后重新 sync 快进, 评审发现不作废(diff 未变)。

## 实现计划

单批单轮(115 行, 全能档 1 子代理评审): 前端三入口删除 → copyTorrentInfo 收窄 → 注释同步(6 处) → 守阵同步(2 文件) → 评审 → issue 翻 Done + 基线切片 + 本档案。

## 子任务状态表

| 步 | 内容 | 状态 |
|---|---|---|
| 1 | ctx_menu.js 删 copy-magnet 菜单项 + shortcuts.js 删 Shift+KeyG | Done(2026-11-09) |
| 2 | 02/03 模板删 magnet 标识行与 act==="magnet" handler | Done(2026-11-09) |
| 3 | drawer_files.js copyTorrentInfo 收窄 name/hash 两用 | Done(2026-11-09) |
| 4 | 关联注释同步(decorate/drawer_templates/commands_send/views_row/record/模板头部) | Done(2026-11-09) |
| 5 | 守阵同步(ctx_menu_registry EXPECT+计数; dom_panel_misc 复制族两项+零回潮断言) | Done(2026-11-09) |
| 6 | 评审 2 轮(轮 1: 3 minor 注释过时, 全修; 轮 2: 零 actionable, 检 3/3) | Done(2026-11-09) |
| 7 | issue 翻 Done + 基线切片 + test.full 实测 | Done(2026-11-09) |

## 进度日志

### R0 · 立档 (2026-11-09)

认领并修复 issue 26-11-09-0639(已翻 Done): 三处复制 magnet 入口移除(右键菜单/快捷键/抽屉标识卡), copyTorrentInfo 收窄 name/hash 两用; config.yml 存量 id 靠未知 id 忽略口径兜住不动; 评审 2 轮(轮 1 检 3/3 · 修 3, 轮 2 零 actionable); 全量 5876 passed + 2 skipped, 覆盖率 99%(见 kb.baseline 最新切片); 真机不适用(纯前端入口删除, 无后端行为面)。

- 2026-11-09 23:46 修复 issue 26-11-09-0639: 三处复制 magnet 入口移除(右键菜单/Shift+KeyG/抽屉标识卡 02+03), copyTorrentInfo 收窄 name/hash 两用, config.yml 存量 id 靠未知 id 忽略口径兜住; 注释同步 6 处 + 守阵 2 文件; 评审 2 轮(轮1 检3/3 修3, 轮2 零 actionable); issue 翻 Done, 全量 5876 passed + 2 skipped 覆盖率 99%, 基线切片 26-11-09-2344, 档案 26-11-09-webui-copy-magnet-entry-removal
