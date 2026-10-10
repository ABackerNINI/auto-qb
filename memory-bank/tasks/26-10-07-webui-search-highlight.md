# 26-10-07-webui-search-highlight — WEBUI 移除冗余的搜索命中行级高亮

**Status:** Done
**Added:** 2026-10-07
**Updated:** 2026-10-07 03:58
**Summary:** 用户报「搜索后所有种子都是匹配的, 即所有种子都会高亮, 失去了意义」, 要求移除搜索命中种子的行级高亮。根因 = 行级 `search-hit` 高亮挂在"保留即命中"的行上 —— 种子页种子行、辅种页组行、追剧页集行/未识别行都是"显示了就必命中"(种子页 `filteredTorrents` 只留命中; 组/集/未识别行按成员命中整行保留), 恒亮无区分。**用户拍板范围: 只去冗余的行级高亮** —— 保留明细里"仅命中成员才亮"的高亮(辅种/追剧明细成员行 + 站点挂件, 那处仍能区分命中与未命中), 追剧**剧行**(`hit` = 该剧全部集都保留, 非恒亮)也保留。改动 = 4 处模板类绑定 + 清理 4 处随之失效的死数据/方法(`columns.js::isHit`、组对象 `hit`、集对象 `hit`、未识别行 `hit`)。CSS 三皮肤规则全保留(剧行/成员行/挂件仍在用)。test.full **2689 passed + 4 skipped / 99%**(基线切片 26-10-07-0358)。
**Topics:** webui-search-highlight
**Refs:** memory-bank/issues/26-10-01-2119-feat-webui-search-highlight.html, memory-bank/testing/baselines/26-10-07-0358-webui-search-highlight.md

## 原始请求

> WEBUI移除搜索匹配种子的高亮, 搜索后所有种子都是匹配的, 即所有种子都会高亮, 失去了意义

范围澄清(用户拍板): 移除范围 = **只去冗余的整行高亮**(种子页种子行、辅种页组行、追剧页集行/未识别行); **保留**明细里"仅命中成员才亮"的高亮。

## 思考过程与决策

- **病灶是"保留即命中"**: 行级 `search-hit` 高亮由服务端 `searchHits`(命中 hash 集合)驱动, 但**三视图的行级保留语义**决定了高亮的区分力:
  - 种子页 `filteredTorrents`: 只保留命中种子 ⇒ 每一显示行都命中 ⇒ 行级高亮恒亮(用户报障视图)。
  - 辅种页 `filteredGroups`: 组内任一成员命中即保留整组 ⇒ 组行恒亮(旧 `g.hit: true`); 但明细**成员行**只亮命中成员 ⇒ 有区分。
  - 追剧页 `decoratedShows`: 任一成员命中即保留整集 ⇒ 集行恒亮; 明细成员行只亮命中成员 ⇒ 有区分; **剧行** `hit` = 该剧**全部集**都保留(非恒亮)⇒ 有区分。
  - 未识别折叠区 `unrecognizedTorrents`: 只保留命中种子 ⇒ 行级高亮恒亮。
- **范围拍板(用户, 二选一)**: 只去"冗余"的恒亮行级高亮, 保留明细成员行/站点挂件的"仅命中成员才亮"。理由: 后者仍能区分命中与未命中, 删了是信息损失; 前者全亮等于没有信息。
- **不引入新呈现**: 本改动只删既有行级高亮, 不做逐词片段高亮 —— issue 26-10-01-2119 的「命中域标识 / 命中片段高亮」仍 Open、未实现, 本档案不认领它, 只在 Ref 里挂关联。
- **死数据一并清**: 类绑定删掉后, `group.hit` / `ep.hit` / 未识别行 `hit` 字段 / `columns.js::isHit` 方法均无消费者 ⇒ 同批删除, 防"看着还在用"的误导(留死字段会让后来者以为高亮仍在)。`show.hit`(剧行)与成员 `hit`(明细成员行/挂件)保留 —— 仍有消费点。
- **CSS 零改动**: `.group-row.search-hit` 仍被追剧**剧行**(`.group-row.show-row`)消费, `.member-row.search-hit` / `.site-chip.search-hit` 仍被明细成员行/挂件消费 ⇒ 三皮肤(console/atlas/prism)规则全保留。

## 实现计划

1. 删 4 处冗余行级类绑定: `tpl/torrents.html`(种子行) · `tpl/groups.html`(组行) · `tpl/shows.html`(集行 + 未识别行)。
2. 清死数据/方法: `columns.js::isHit` · `filters.js`(组对象 `hit`) · `shows.js`(集对象 `hit`) · `decorate.js`(未识别行 `hit`)。
3. 注释同步: `filters.js` / `shows.js` 块注释标注 26-10-07 口径变更。
4. 闸门: `commands run test.full`; 收尾: 本档案 + 切片 + 基线 + 事实回写 + `kb.index`。

## 子任务状态表

| 子任务 | 状态 | 备注 |
|---|---|---|
| 1 读码定位 + 范围澄清与拍板 | ✅ 完成 | 三视图行级保留语义; 用户选「只去冗余的整行高亮」 |
| 2 删 4 处行级类绑定 | ✅ 完成 | torrents / groups / shows 三模板 |
| 3 清死数据/方法 | ✅ 完成 | `isHit` + 组/集/未识别行 `hit` 字段 |
| 4 注释同步 | ✅ 完成 | filters.js / shows.js |
| 5 闸门 + 收尾回写 | ✅ 完成 | 数字见进度日志 |

## 进度日志

- **2026-10-07 03:52-03:58** 用户报「所有种子都高亮, 失去意义」→ 读码定位(三视图行级保留语义 vs 行级高亮) → `AskUserQuestion` 澄清范围(用户选"只去冗余的整行高亮") → 改 4 处模板绑定 + 清 4 处死数据/方法 → `node --check` 4 个 JS 全绿 → `test.full` **2689 passed + 4 skipped / 0 failed / 99% / 59.24s**(与上一条基线 26-10-07-0251 逐位持平, 本轮无测试增删)。收尾: 本档案 + activeContext 切片 + 基线切片 + 事实回写(`systemPatterns/web-responsiveness.md` 的 `isHit` 段) + 关联 issue 反向声明 + `kb.index`。**未提交 —— 等用户显式指令。**
