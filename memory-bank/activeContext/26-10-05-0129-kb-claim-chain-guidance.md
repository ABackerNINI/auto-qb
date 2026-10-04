# 认领链引导补位 (memory-bank skill + create-issue skill) — 闸门拦截复盘改进 (Done)

> 摘要: 另一会话提交前被 `gen_doc_map --check` 闸门拦 (任务档案 **Refs:** 行用 `·` 分隔多目标 + issue/基线切片/坑档未反向声明档案), 闸门起效但暴露引导缺位 —— 立档/收尾/入池文档只字未提 Refs 格式, agent 只能看生成器源码与既有件先例现场反推。**第一笔 (memory-bank skill 侧)**: [doc-forms.md「认领链」](../conventions/doc-forms.md)(协议单点, 闸门报错指向处) 补「多目标一律英文逗号、全部目标写一行、视觉分隔符把整串当单一路径」+ 合法目标枚举对齐真实机制(补基线切片/坑档); [SKILL.md](../../.agents/skills/memory-bank/SKILL.md)「任务档案规范」加 Refs 行写法与双向认领链 bullet + 收尾 DoD 步骤4(基线切片)/步骤6(坑档) 各补反向声明条款。**第二笔 (create-issue skill 侧)**: 两个 issue 模板补空 `doc-refs` meta 行(与 doc-forms meta 协议对齐, 认领时填; 冒烟透传验证过) + [SKILL.md](../../.agents/skills/create-issue/SKILL.md) 四处引导(新建段声明位 / 修一条 issue 时插「填认领链反向声明」第 3 步 / 可移植性 meta 行 / 反模式 1 条)。附带: 本 clone 盘上 11 个生成 `_index.md` 残留旧生成器 CRLF 产物, `kb.index` 重建转绿, 坑档 editing-traps.md 该条 `复发 +1`(记跨 clone 残留侧面)。test.full 2537 passed + 4 skipped / 99% (基线 [26-10-05-0143](../testing/baselines/26-10-05-0143-create-issue-claim-chain-guidance.md), 第一笔 [26-10-05-0129](../testing/baselines/26-10-05-0129-kb-claim-chain-guidance.md))。
> 最后活动: 2026-10-05 01:43

**Refs:** memory-bank/conventions/doc-forms.md, .agents/skills/memory-bank/SKILL.md, .agents/skills/create-issue/SKILL.md

## 现状

- 两笔引导补位均完成; 守卫与生成器零改动 (gen_doc_map.py / test_docs_forms.py / create-issue scripts/ 原样)。
- 已入库: memory-bank SKILL.md / doc-forms.md / create-issue SKILL.md / 两模板 / 两基线切片 / 本切片 + 盘上 CRLF 重建的生成 `_index.md`(内容零 diff), 随认领链引导补位提交一并暂存。
