# 1466 → 1468 (+2) —— WEB UI 多选右键菜单目标 = 整个选中集合 + 生成物重建提示指错命令

> 摘要: 四个 open*Menu 只记 anchor ⇒ 多选只动被点的一个; _ctxMulti 判选中集合; gen_cmd 按脚本查表(修"跑完仍红"的提示); 合流后实测; 时分不可考; 当日序位第 3 (09-24)
> 基线时间: 2026-09-24 00:00
> 档案: 26-09-24-webui-ctx-menu-multi-select

- ↑ 收集数 **1466 → 1468**(**+2**; 2026-09-24 **WEB UI 多选右键菜单目标 = 整个选中集合** + **生成物重建提示指错命令**):
  ①`test_web.py::test_frontend_ctx_menu_multi_select_targets_selection` —— 用户报"多选时右键菜单
  应该对所有选择的种子生效, 当前仅对鼠标指向的触发右键的种子生效"。根因: 四个 `open*Menu`(组/成员/剧/集)
  只记 anchor(`key`/`hash`/`episode`), 动作端点直接拿它拼 URL ⇒ 无论选了多少都只动被点的那一个
  (菜单照常弹出、照常成功、**无任何报错**, 肉眼难辨)。修法: `menu.js::_ctxMulti` 判"这一行属于选中集合
  且集合范围 ≠ 该行自身范围"(判据**不是**"选中数 > 1" —— 否则"选中 1 个辅种 + 右键它的成员行"会给出
  文案说"该种子"、实际动整组的错菜单), 四入口各写 `menu.multi`; 双 UI 模板加 `v-if="menu.multi"` 批量分支,
  动作整份复用批量浮条链路(`commands.js::ctxAct`→`bulkAct` / `ctxDelete`→`bulkDelete`), 不另拆目标集合。
  守阵钉三处成对关系(四入口写 `multi` / 双 UI 分支逐项一致 / `ctxAct` 复用 `bulkAct`), 两处红验过;
  冒烟 `scripts/ui_smoke.cjs` +12 条 CTX-03(双 UI × 六: 三视图批量菜单 / 未选中行负向对照 /
  合单一条 bulk / 乐观覆盖), 已对 HEAD 红验(prism 三条变红)。冒烟三模式 84/84/8 全 0 失败。
  ②`test_memory_bank.py::test_gen_cmd_hints_name_real_tasks` —— 修上一条报告、本轮由用户指令
  「修复既有缺陷然后提交」的既有缺陷: `_common.gen_cmd()` 忽略传入的脚本名、一律返回
  `commands run kb.index`, 而 `kb.index` 只跑 `gen_tasks_index` + `gen_kb_index` ⇒ `_doc-map.md` /
  `plans|reports/_index.md` 的报错文案把用户指向一条**跑完仍然红**的命令(提交闸门 `my-commit-flow`
  的 `memory-bank/` 一条早就挂了这四条的 `--check` ⇒ "闸门能红、却没有一条能修的命令")。
  修法两条一起: `kb.index` / `kb.check` 补上 `gen_docs_index.py` + `gen_doc_map.py`(与闸门**同集**) +
  `_common.GEN_CMD_BY_SCRIPT` 按脚本查表(`gen_active_recent.py` → `kb.active --check`, 它是只校验的)。
  守阵钉"调用点全覆盖 / task id 真实存在 / 提示说跑 `kb.index` 的脚本必须真在它的 run 列表里",
  两处红验过, 并端到端复现原症状(写坏 `_doc-map.md` → 照文案跑 `kb.index` → `--check` PASS)。
  ⚠ 本批与主线 `5c518b3`(HR 在线核实 M1, +142)合流: 按「移出改动 → `merge --ff-only` → 施回改动」
  同步(全程未用 stash/rebase), 基线数字取**合流后实测**; 流水轮转沿用主线的**两级方案**
  (`-archive.md` = 中间段 / `-old.md` = 最老段) —— 我此前并入 `-old.md` 的那 15 条**已撤**,
  因为它们已在 `-archive.md` 里(避免同一段历史存两份)。
  ⚠ 本条的绝对数字已按**合流后链条**改写: 它落在地下一条(HR 在线核实 M2, +91 ⇒ 1466)之**后**, 故起点是 1466、终点 1468; 远端提交时记的「合流后实测 1375 → 1377」是只并到 M1 时的读数。
