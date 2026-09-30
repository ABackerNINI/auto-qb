# 26-09-30-memory-bank-timekit — memory-bank 取时间标准化 (UTC+8 单点 + 守卫 + 移植)

**Status:** Open
**Added:** 2026-09-30
**Updated:** 2026-09-30
**Topics:** memory-bank-timekit
**Refs:** memory-bank/plans/26-09-30-0931-plan-memory-bank-timekit.html
**Summary:** KB 日期全凭 agent 手写: 约定要求「时间戳用命令取当前值」但那条命令不存在, 守卫只查形状不查值 (gen_active_recent 静默回退), 唯一脚本化取时点 (create-issue stamp) 未钉时区。方案: timekit.py UTC+8 单点 + commands run kb.time 流程接入 + 三层日期守卫 (文件名/元数据/正文) 接 kb.check 与提交闸门 + 守卫脚本随 skill 移植。

## 原始请求

「文档取的时间有时候不准, 包括文档名以及文档内部, 尤其是文档内部的格式没有统一, 文档名甚至会出现未来的时间, 需要添加标准化的取时间流程, 以 UTC+8 为准, 由脚本自动取, 且要添加守卫, 都放入 memory-bank 中。同时将关于 memory-bank 的守卫脚本都放入 memory-bank 中。memory-bank 是独立的 skill, 需要方便移植到其它项目。」

收尾指令: 「计划入档, 暂不实施」—— 本轮只产出计划文档并入档, 实施待用户显式启动。

## 思考过程与决策

- **根因不是没人守规矩, 是规矩从未具备执行条件**: `doc-forms.md:31` / `webui.md:59` 早写着「时间戳用命令取当前值」, 但 `.commands/` 全包 grep 取时命令 0 命中 —— 日期实际全是 agent 按会话上下文手敲的。修复的锚点是**让命令真实存在** + 值级机检, 不是再写一条约定。
- **时区实现取 naive UTC+8 墙钟** (`datetime.now(timezone(timedelta(hours=8))).replace(tzinfo=None)`): 与全库现有 naive 解析一致, 不引入 aware/naive 混算; 机器时区无关性由测试钉住。
- **守卫分三层、严宽有别**: 文件名前缀与元数据 (Added/Updated/最后活动/doc-added/doc-updated) 查「合法 + 非未来」; 正文只查体例 (规范 token 不查未来 —— 排期/里程碑是合法的未来引用); md 跳过代码块, 行内 `<!-- time:allow -->` 豁免。**过去日期的错值如实兜不住**, 靠流程规避。
- **守卫脚本随 skill 走**: 探索确认 memory-bank 守卫逻辑本就在 skill scripts 里 (项目无关), 唯 `check_doc_links.py` 在根 scripts/ —— 耦合极低 (根探测改 `_common.find_root()` 即可), 迁入后 kb/闸门接线全走 `<skill-dir:memory-bank>` 占位符零改动, `references/PORTING.md` 记移植清单。
- **AGENTS.md 不动**: 7978/8000 字符仅余 22, 时间口径放 SKILL.md (余量 6347/15000), 路由经 skill 收尾链路自然触达。
- **收口顺序敏感**: `gen_active_recent.py:87` 静默回退的收口必须在存量清洗**之后** (8 处坏「最后活动」现存数据, 先收口闸门即红)。

## 实现计划

方案与取舍单点在 [plans/26-09-30-0931-plan-memory-bank-timekit.html](../plans/26-09-30-0931-plan-memory-bank-timekit.html) (本节只放步骤概要, 不复制方案):

0. sync → 1. timekit.py + 单测 → 2. 立档/计划落盘 (kb.time 首个使用者) → 3. SKILL.md 口径节 + conventions 指针 + doc.caps → 4. kb config + 提交闸门 → 5. create-issue 钉 +08 → 6. 存量清洗 → 收口静默回退 → 7. check_doc_links 迁入 skill → 8. references/PORTING.md → 9. dev.fmt → test.full → 收尾 DoD (切片/kb.index/基线/pitfalls 记坑)。

## 子任务状态表

| # | 子任务 | 状态 |
|---|---|---|
| 1 | `timekit.py` (date/time/stamp/check) + 单测 (三层守卫种子 + TZ 无关性) | ⬜ |
| 2 | 立档 + 计划 HTML 落盘 (2026-09-30 09:31 已完成首版入档) | ✅ |
| 3 | SKILL.md「时间口径与取时」节 + doc-forms/webui 指针 + doc.caps | ⬜ |
| 4 | `.commands/kb/config.toml` (kb.time / kb.check) + 提交闸门 | ⬜ |
| 5 | create-issue `stamp()`/`long_date()` 钉 UTC+8 | ⬜ |
| 6 | 存量清洗 (8 坏最后活动 + 1 缺行 + 10 紧凑 + 1 ISO-T) → 收口静默回退 | ⬜ |
| 7 | `check_doc_links.py` 迁入 skill scripts + 改闸门/pytest 引用 | ⬜ |
| 8 | `references/PORTING.md` 移植清单 | ⬜ |
| 9 | dev.fmt → test.full → 收尾 DoD + pitfalls 记坑 | ⬜ |

## 进度日志

- **2026-09-30 09:36**: 计划定稿并入档。两轮探索确认根因 (约定命令不存在 / 守卫只查形状 / 唯一脚本化取时点裸本地时区) 与存量数字 (未来日期 0, 坏「最后活动」8+1, 紧凑 8 位 10, ISO-T 1)。计划文档 `plans/26-09-30-0931` (dark 单文件, doc-status Open); 本档案立档 (查重通过: 本 clone 与全部跨工作区 clone 无同名 slug)。**用户指令「暂不实施」** —— 子任务 1/3-9 待用户显式启动后按实现计划推进。
- **2026-09-30 09:41**: 收尾机检首跑红一次 —— `test_docs_forms::test_claim_chain_is_bidirectional`: 计划 doc-refs 首版写成 memory-bank 相对 + 本档案漏 `**Refs:**` 反向声明。踩的是**已记坑** `pitfalls/kb/refs-rename.md` 第 3 条, 已复发 +1 (→2); **为什么没命中**: 产出前只读了 `doc-forms.md`(「相对路径」未写解析基准), 没路由到 pitfalls —— 与 09-27 首次复发同一模式。双向补齐后 test.full 复跑全绿 1831 passed / 90%, 基线切片 `baselines/26-09-30-0941`。
