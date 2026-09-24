# WEB UI 多选右键菜单: 目标 = 整个选中集合

> 摘要: 用户报"多选时右键菜单应该对所有选择的种子生效, 当前仅对鼠标指向的触发右键的种子生效"。根因是四个 `open*Menu` 只记 anchor、动作直接消费 anchor ⇒ 菜单照常弹出/照常成功但**只动一行**(无报错, 肉眼难辨)。修法: `menu.js::_ctxMulti` 判"该行属于选中集合且集合范围 ≠ 该行自身范围", 四入口各写 `menu.multi`; 双 UI 加 `v-if="menu.multi"` 批量分支, 动作整份复用批量浮条链路(`ctxAct`→`bulkAct` / `ctxDelete`→`bulkDelete`)。同轮另修一个既有缺陷(生成物重建提示指错命令)。**已入库 `907890b`**(含与主线 `5c518b3` 的合流)。
> 触发: 多选, 右键菜单, 批量, 选中集合, ctx-menu, menu.multi, ctxAct, CTX-03, 只对一个种子生效
> 最后活动: 2026-09-24 22:0x

## 状态

**已完成**(本 clone, 已随 `907890b` 入库):

- 根因: `openMenu`/`openMemberMenu`/`openShowMenu`/`openShowEpMenu` 只写 anchor(`key`/`hash`/`episode`),
  `act`/`actTorrent`/`actEpisode`/`del*`/`torrentCmd` 直接拿它拼端点 —— 选中集合从未参与。
  查 `plans/26-09-15-0658` §04.3「右键: 有选中集合时弹批量菜单」⇒ 确认是**漏做**, 非设计变更。
- 判据: **范围比较**(`selScope != anchorScope` 且 anchor ∈ selScope), 不是"选中数 > 1" ——
  否则"选中 1 个辅种 + 右键它的成员行"会给出文案说"该种子"、实际动整组的错菜单。
  成员/集/剧行用 **some** 判"属于"(行可能只是由组选择派生的半选)。
- 改动 6 个源文件: `shared/menu.js`(`_ctxScopeKey`/`_ctxMulti` + 两入口写 `multi`)·
  `shared/shows.js`(两入口写 `multi`)· `shared/commands.js`(`ctxAct`/`ctxDelete`)·
  `shared/app.js`(`menu.multi` 初值)· `atlas/index.html` · `prism/index.html`(批量分支, 逐项一致)。
- 批量菜单只放**批量有意义**的动作(开始/暂停/强制汇报/重新校验/删除), 与批量浮条逐项对齐;
  单目标项(详细信息/限速/重命名/导出/复制/打开文件夹…)不进批量菜单。
- 守阵 `test_web.py::test_frontend_ctx_menu_multi_select_targets_selection`(三处成对关系:
  四入口必须写 `multi` / 双 UI 分支逐项一致 / `ctxAct` 必须复用 `bulkAct`),
  **红验两处**(漏写 `multi` ⇒ 红; 摘掉棱镜分支 ⇒ 红)。
- 冒烟 `scripts/ui_smoke.cjs` +12 条 CTX-03(双 UI × 六): 三视图(种子/追剧/辅种)选中后右键出批量菜单 ·
  **未选中行右键仍是单目标菜单**(负向对照)· 点批量只发 **1** 条 bulk(0 条逐目标)· 乐观覆盖整个集合。
  追剧/辅种两条走**真实 Ctrl+点击**路径, 不用 `vm` 直调。**已对 HEAD 红验**(prism 三条变红)。
- **顺带修掉的既有缺陷(用户指令「修复既有缺陷然后提交」)**: `_common.gen_cmd()` 忽略脚本名、一律返回
  `commands run kb.index`, 而 `kb.index` 只跑两条生成器 ⇒ `_doc-map.md` / `plans|reports/_index.md`
  的报错文案把用户指向**跑完仍然红**的命令(闸门早就挂了这四条的 `--check`)。
  修法: ①`kb.index` / `kb.check` 补上 `gen_docs_index.py` + `gen_doc_map.py`, 与闸门**同集**;
  ②`_common.GEN_CMD_BY_SCRIPT` 按脚本查表(`gen_active_recent.py` → `kb.active --check`)。
  守阵 `test_memory_bank.py::test_gen_cmd_hints_name_real_tasks`(**两处红验**), 并端到端复现原症状验证。

**实测**(合流后、提交时刻口径):

- 全量 **1376 passed + 1 skipped** / TOTAL 91%(9278 语句 / 727 未覆盖 / 3128 分支 / 277 partial) / sidefx 越界 0。
- 冒烟(桩 3000 种子): ok **84/0** · error **84/0** · hang **8/0**。
- `commands run test.pkg` **47 passed** · `kb.check` 5 段全绿 · `doc.caps` 无阻塞项。
- 提交 `907890b`(22 文件 / +720 −23); Gitee `ls-remote` == 本地, GitHub 镜像同步成功; 幽灵 diff 0。

## 待用户处置

1. **行为变化需知情**: 选中行右键后菜单**只剩批量动作** —— 要"详细信息 / 限速 / 重命名 / 导出"
   必须先取消选择(或右键未选中的行)。若更希望"批量菜单里也带上单目标项(作用于 anchor)", 说一声即可改。
2. **未修的既有问题(范围守恒, 仅报告)**: `test_commands_engine.py` 的两条 GBK 码页守阵在本工具 shell 里
   恒红 —— 注入 `PYTHONUTF8=1` / `LC_ALL=C.UTF-8` 使 `locale.getpreferredencoding(False)` 返回 utf-8,
   `_decode` 的 GBK 回退不可达。`env -u PYTHONUTF8 -u PYTHONIOENCODING` 后 24 passed ⇒ **非代码缺陷**,
   判据已在 [../pitfalls/testing/patching.md](../pitfalls/testing/patching.md)(上一轮记的)。

## 单点指针

- 判据全文 → [../pitfalls/web-ui/overlays.md](../pitfalls/web-ui/overlays.md)(条目 CTX-03) ·
  生成物重建提示 → [../pitfalls/kb/discipline.md](../pitfalls/kb/discipline.md)
- 原始设计意图 → [../plans/26-09-15-0658-webui-optimization-plan.html](../plans/26-09-15-0658-webui-optimization-plan.html) §04.3
- 任务档案 → [../tasks/26-09-24-webui-ctx-menu-multi-select.md](../tasks/26-09-24-webui-ctx-menu-multi-select.md)
- 测试数字单点 → [../testing/baseline.md](../testing/baseline.md) · 冒烟规模 → [../testing/smoke.md](../testing/smoke.md)
