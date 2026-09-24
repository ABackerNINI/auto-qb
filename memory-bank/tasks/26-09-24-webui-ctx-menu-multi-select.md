# 26-09-24-webui-ctx-menu-multi-select — 多选右键菜单目标 = 整个选中集合

**Status:** Done
**Added:** 2026-09-24
**Updated:** 2026-09-24
**Summary:** 用户报"多选时右键菜单应该对所有选择的种子生效, 当前仅对鼠标指向的触发右键的种子生效"。根因: 四个 `open*Menu`(组/成员/剧/集)只记 anchor(`key`/`hash`/`episode`), 动作端点直接拿它拼 URL ⇒ 无论选了多少都只动被点的那一个(菜单照常弹出、照常成功、无任何报错)。修法: `menu.js::_ctxMulti` 判"这一行属于选中集合且集合范围 ≠ 该行自身范围", 四个入口各写 `menu.multi`; 双 UI 模板加 `v-if="menu.multi"` 批量分支, 动作整份复用批量浮条链路(`ctxAct`→`bulkAct` / `ctxDelete`→`bulkDelete`)。同轮另修一个既有缺陷: 生成物的"怎么重建"提示(`_common.gen_cmd`)指错命令 ⇒ 让 `kb.index`/`kb.check` 覆盖面 ⊇ 提交闸门判红的生成物集合 + 提示按脚本查表。新增静态守阵 + 冒烟 12 条(双 UI × 六条), 均两处红验过。**已入库 `907890b`**(与主线 `5c518b3` 合流后实测: 全量 1376 passed + 1 skipped / 冒烟 ok 84/0 · error 84/0 · hang 8/0)。
**Topics:** webui-ctx-menu-multi-select

## 原始请求

> 修复BUG: 多选时右键菜单应该对所有选择的种子生效, 当前仅对鼠标指向的触发右键的种子生效, 检查辅种/种子/追剧视图以及两套UI

## 思考过程与决策

### 这不是"新功能", 而是 2026-09-15 计划里漏做的一条

`plans/26-09-15-0658-webui-optimization-plan.html` 的 §04.3 明确写了
「**右键**: 有选中集合时弹批量菜单; 无选中时保持现状(组菜单/单种子菜单)」,
阶段 E(R03)的验证清单里也有"批量删除中途失败停止"。**批量浮条(R03 的另一半)落地了,
右键这一半没落地** —— 于是同一批目标存在两套口径: 浮条一次动 N 个, 右键只动 1 个。

### 根因

`openMenu` / `openMemberMenu` / `openShowMenu` / `openShowEpMenu` 四个入口只把 **anchor**
写进 `this.menu`(组 key / 成员 hash / 剧集 hash 列表), 而 `act` / `actTorrent` / `actEpisode` /
`delGroup` / `delTorrent` / `delEpisode` / `torrentCmd` 全部直接消费 anchor 拼端点
(`/api/groups/{key}/pause`、`/api/torrents/{hash}/pause` …)。选中集合(`selGroups` / `selMembers`)
从头到尾没参与 ⇒ 菜单**看起来完全正常**(弹得出、点得动、有成功 toast), 只是作用域小了。

### 判据取舍: "集合等同于这一行自身的范围", 而不是"选中数 > 1"

一开始想用"选中数 > 1 就升级", 推演后发现两个反例, 于是改成比较**范围**:

| 场景 | 集合 | 该行范围 | 应给什么菜单 |
|---|---|---|---|
| 选中 1 个辅种 + 右键它自己 | {组 g} | {组 g} | 普通组菜单(文案"暂停整组"才对) |
| 选中 1 个辅种 + 右键它的**成员行** | {组 g} | {成员 h} | **批量菜单** —— 否则文案说"暂停该种子"、实际动整组 |
| 选中 N 个种子 + 右键其中之一 | N 个 hash | {该 hash} | 批量菜单 |
| 选中整集 + 右键该集行 | 该集全部 hash | 该集全部 hash | 普通集菜单(它本来就是批量的) |

⇒ 判据 = `selScope != anchorScope` 且 anchor 属于 selScope。
"属于"对成员/集/剧行用 **some**(行可能只是**半选** —— 由组选择经 `selHashSet` 派生命中的,
那时仍应视为"在集合里", 否则用户右键自己刚选中的行却拿到单行菜单)。

### 动作链路: 直接复用批量浮条, 不另拆一遍

`bulkAct` / `bulkDelete` 已经正确实现"选中集合 → 目标拆解"(`_bulkTargets`: 虚拟行转单种子、
组展开成员、已失效 key 跳过), 且批量删除已有统一确认框链路(`_deleteFlow`)。
所以批量菜单**不新增任何命令逻辑**, 只加两个瘦入口:

```js
ctxAct(action)  { this.menu.visible = false; return this.bulkAct(action); }
ctxDelete()     { this.menu.visible = false; return this.bulkDelete(); }
```

`this.menu.visible = false` 是必需的: 菜单根节点是 `@click.stop`(见 index.html),
全局"点空白关闭"接不到, 而 `bulkAct`/`bulkDelete` 是给浮条写的, 没有关菜单的责任。

### 批量菜单里放什么 / 不放什么

**放**: 开始 / 暂停 / 强制汇报 / 重新校验 / 删除 —— 与批量浮条**逐项对齐**。
**不放**: 详细信息 / 限速 / 移动 / 重命名 / 导出 .torrent / 复制族 / 队列 / 超级做种 / 强制开始 /
TMM / 分享率 / 打开目标文件夹 —— 它们对 N 个目标没有明确语义(打开 N 个文件夹尤其荒谬)。
要单目标操作就不选中任何行(或右键未选中的行)再右键。文案统一用 **"批量X"** 前缀,
与单目标菜单的"暂停该种子 / 暂停整组"一眼可分; 计数不进菜单(菜单 min-width 196px 会撑宽,
而 `_menuPos` 按 214px 估算做视口钳位 ⇒ 长文案会让靠右锚点的菜单伸出屏幕) ——
计数由批量浮条("已选 N 个辅种、M 个种子")与执行后的 toast / 删除确认框承担。

### 不做的两件事(以及为什么)

1. **右键未选中行时不清空选择**: 标准 OS 行为是"右键重新锚定并清选择", 但本仓库的普通左键
   (组行=展开、成员行=无操作)**一律不清选择**(`selection.js` 的既有口径), 且清空会毁掉用户
   刚建好的选择。故取**加法语义**: anchor 不在集合里 → 就只作用于 anchor, 选择原样保留;
   此时 `.ctx-src`(CTX-02)会把"菜单指的是哪一行"标出来, 不会歧义。
2. **不把批量菜单做成"菜单内可切换"**: 一个菜单一种作用域, 少一个状态维度。

## 实现计划

| # | 文件 | 改动 |
|---|---|---|
| 1 | `shared/menu.js` | 新增 `_ctxScopeKey` / `_ctxMulti`; `openMenu` / `openMemberMenu` 写 `menu.multi` |
| 2 | `shared/shows.js` | `openShowMenu` / `openShowEpMenu` 写 `menu.multi` |
| 3 | `shared/commands.js` | 新增 `ctxAct` / `ctxDelete`(复用 `bulkAct` / `bulkDelete`) |
| 4 | `shared/app.js` | `menu` 初值补 `multi: false` |
| 5 | `atlas/index.html` · `prism/index.html` | `.ctx-menu` 内新增 `v-if="menu.multi"` 批量分支(两套逐项一致) |
| 6 | `tests/test_web.py` | 新增静态守阵 `test_frontend_ctx_menu_multi_select_targets_selection` |
| 7 | `scripts/ui_smoke.cjs` | 新增 CTX-03 六条(双 UI × 六) |

## 子任务状态表

| 子任务 | 状态 |
|---|---|
| 定位根因(四入口 + 动作消费点) | Done |
| `menu.js` 目标判定 + 四入口写 `multi` | Done |
| `commands.js` `ctxAct` / `ctxDelete` | Done |
| 双 UI 模板批量分支 | Done |
| 静态守阵(三处成对关系) + 两处红验 | Done |
| 冒烟 CTX-03 六条 + 对 HEAD 红验 | Done |
| 全量测试 + 三模式冒烟 | Done |
| 知识库回写(pitfalls / baseline / smoke) | Done |
| 修既有缺陷: 生成物重建提示指错命令 | Done |
| 提交 / 推送 | Done(已入库 `907890b`) |

## 待用户处置

1. ~~提交~~ —— **已完成**: `907890b` 已推 Gitee(`ls-remote` == 本地) + GitHub 镜像同步成功。
2. ~~既有缺陷(范围守恒, 仅报告, 未修)~~ —— **已按用户指令修复**, 见下方「进度日志 21:5x」。

## 进度日志

- 2026-09-24 21:0x 开工。`git fetch gitee develop` → 本地 HEAD == 远端(`434e019`), 无需同步。
  读 `pitfalls/web-ui/_index.md` + `overlays.md`(多选/右键那一类)。
- 复现判据(读代码即可确认): 四个 `open*Menu` 均无选中集合参与; `act`/`actTorrent`/`actEpisode`
  直接消费 `menu.key`/`menu.hash`/`menu.episode`。查 `plans/26-09-15-0658` §04.3 找到原始设计意图
  ("有选中集合时弹批量菜单") —— 确认是**漏做**, 不是设计变更。
- 实现 1–5 项。`node --check` 全绿; 前端静态守阵 `-k frontend` 10 passed。
- 新增守阵: **红验两处** —— ①摘掉 `openMenu` 的 `multi:` ⇒ 变红; ②摘掉棱镜批量分支 ⇒ 变红。
- 冒烟: 桩服务 3000 种子。**首轮 80 项 1 失败**, 失败项是棱镜"剧行乐观"(与本次改动无关);
  用"临时还原静态文件到 HEAD"的办法对照 —— 同一桩服务下 HEAD 版该条 **PASS**,
  但**换全新桩服务后带改动的版本也 PASS** ⇒ 判定为**长驻桩服务状态累积**导致的已知抖动
  (见 `testing/smoke.md`「桩服务的行为」: 跑过整剧暂停后跨轮残留), 非回归。
  顺带用同一手法完成**冒烟红验**: HEAD 版下 CTX-03 三条变红
  ("选中行右键 -> 批量菜单" 菜单里是"开始该种子" / "合单为一条 bulk" 实测 bulk 0 次)。
- 补三视图断言(追剧 Ctrl 选两集 / 辅种 Ctrl 选两组 → 批量菜单), 全部用**真实修饰键路径**,
  不走 `vm` 直调。全新桩服务复跑: **ok 84/0 · error 84/0 · hang 8/0**。
- 全量: 首次 `commands run test.full` 报 2 failed(`test_commands_engine.py` 的两条 GBK 码页守阵)。
  定位为**本工具 shell 注入 `PYTHONUTF8=1` / `LC_ALL=C.UTF-8`** ⇒ `locale.getpreferredencoding(False)`
  返回 utf-8 ⇒ `_decode` 的 GBK 回退不可达。`env -u PYTHONUTF8 -u PYTHONIOENCODING` 后 **24 passed**;
  干净环境全量 **1233 passed + 1 skipped** / TOTAL 91%(7782 / 622 / 2648)。**非本次改动引入**, 未修(范围守恒)。
- 回写: `pitfalls/web-ui/overlays.md`(新条目 CTX-03)· `testing/baseline.md` + `baseline-history.md` ·
  `testing/smoke.md`(冒烟规模 72 → 84)。**已随 `907890b` 入库**。
- 回写踩到两个**生成物/容量**问题(均当场解决):
  ① `testing/baseline-history.md` 本就在 cap 边缘(HEAD 实测 23,4xx / 24,000 字符), 追加一条后
     **24,469 越线** ⇒ 按 `_common.LOG_ROTATE_KEEP`(2/3)从最老一端切 15 条到
     `testing/attachments/baseline-history-old.md` 的**最前**(保持"最新在上"), 主文件落到 15,210 字符;
     条目逐字未改, 条目数守恒(HEAD 33 + 本轮 1 = 34 = 主 19 + 附件新增 15)。
  ② `memory-bank/_doc-map.md` 是生成物且 `kb.index` **不覆盖它** —— 它的报错文案却写"请运行
     `commands run kb.index`"(`_common.gen_cmd` 对所有脚本返回同一句)。按 `commands run kb.index`
     跑完仍红, 需另跑 `.agents/skills/memory-bank/scripts/gen_doc_map.py`。**该文案与任务定义的
     不一致属既有缺陷, 按范围守恒未修**(见"待用户处置")。
  ③ 新档案的 `**Topics:**` 必须是**单个 slug**(生成器整串当主题) —— 写成逗号列表会把
     `webui, ctx-menu, multi-select` 当做一个主题名进 `_doc-map.md`。
- 收尾复核: 干净环境全量 **1233 passed + 1 skipped** / TOTAL 91%; 知识库与文档守阵
  (`test_memory_bank.py` + `test_docs_forms.py`) 33 passed。
- ⚠ **行尾坑复发 3**(`pitfalls/kb/cap-counting.md`): 新建的档案与切片经 Write 工具落成**纯 LF**
  (146/146、49/49), 拼装外迁附件的脚本替换串又带了 3 个裸 `\n` ⇒ 附件变 MIXED。
  `git diff` 的 `LF will be replaced by CRLF` 警告本轮**出现两次都被当噪音放过**。
  **为什么没命中**: 本轮按"改前端"路由, 只读了 `pitfalls/web-ui/_index.md`, 没进 `kb` 类 ——
  而该条住在 `kb`, 触发动作(追加流水 / 轮转 / attachments / 新建文件)全发生在**收尾回写**阶段,
  不在开工路由的视野里。已按 CRLF 归一 3 个文件并逐个复核
  (`bytes.count(b"\n") == bytes.count(b"\r\n")`), cap 重量: 档案 6,789 / 切片 2,811 / 主流水 15,210。
- 2026-09-24 21:5x **用户指令「修复既有缺陷然后提交」** —— 修上面第 ② 条, 两条一起做:
  ①**`kb.index` / `kb.check` 的覆盖面 ⊇ 提交闸门判红的生成物集合**: 补上 `gen_docs_index.py` 与
     `gen_doc_map.py`。闸门(`my-commit-flow` 的 `memory-bank/` 一条)早就把这四条的 `--check` 挂上了,
     而 `kb.index` 只跑前两条 ⇒ **"闸门能红、却没有一条能修的命令"**。`kb.index` 的 note 写死这条口径。
  ②**`_common.gen_cmd()` 按脚本查表**(新增 `GEN_CMD_BY_SCRIPT`), 不再一律返回 `kb.index` ——
     只校验不写文件的 `gen_active_recent.py` 指向 `kb.active --check`(它的"重跑"是校验, 不是重建)。
  ③守阵 `test_memory_bank.py::test_gen_cmd_hints_name_real_tasks`: 调用点全覆盖 + task id 真实存在 +
     **提示说跑 `kb.index` 的脚本必须真的在它的 run 列表里**。**两处红验**: `kb.index` 退回旧的两条 ⇒ 红;
     删掉一条 `GEN_CMD_BY_SCRIPT` 登记 ⇒ 红。
  ④**端到端复现原症状**: 故意写坏 `_doc-map.md` → `gen_doc_map.py --check` 报"请运行
     `commands run kb.index`" → 照做 → 再 `--check` **PASS**(修前这一步仍红)。
  ⑤实测: `kb.index` 现输出 4 段(任务索引 / 16 个 kb 索引 / plans+reports 索引 / `_doc-map.md`);
     `kb.check` 5 段全绿; `commands run test.pkg` **47 passed**; 全量 **1234 passed + 1 skipped**。
  ⑥新坑入库 `pitfalls/kb/discipline.md`「闸门能判红, 却没有一条能修的命令」(判据 = "照它做一遍, 红会不会
     消失", 而不是"提示里写了命令"), 并扩了该文件的三行头摘要/触发。
- 2026-09-24 22:0x **提交 + 推送完成(`907890b`)**:
  ①**提交前发现主线已前进**(`434e019` → `5c518b3` "HR 在线核实 M1", +142 条 / 46 个文件) ⇒
    按「移出改动 → `merge --ff-only` → 施回改动」同步: `git diff --output` 出补丁(88,893 字节 / 21 文件)
    + 另存 2 个新文件, `git restore .` 清树, `git merge --ff-only FETCH_HEAD` 快进, 再
    `git apply --3way` 施回(**排除** 6 个生成物/重叠文件手工处置)。**全程未用 stash/rebase**。
  ②**排除路径写错一处**: 我写的 `--exclude=memory-bank/testing/baseline-history-old.md` 漏了
    `attachments/` 那一级 ⇒ 我并进 `-old.md` 的 15 条被施回。发现后 `git restore --staged --worktree`
    撤回 —— 因为主线的轮转是**两级方案**(`-archive.md` = 中间段 / `-old.md` = 最老段), 那 15 条已在
    `-archive.md` 里, 两份就是重复。
  ③重叠 4 文件的处置: 生成物(`tasks/_index.md` / `_doc-map.md` / `pitfalls/kb/_index.md`)重跑 `kb.index`;
    `baseline-history.md` 取主线版 + 我的新条目插在**条目区最前**(沿用主线的顶部 blockquote 指针);
    `baseline.md` 数字取**合流后实测** `1375 → 1377`。
  ④**闸门首跑被既有环境问题拦下**(与本任务无关): 本工具 shell 注入 `PYTHONUTF8=1` / `LC_ALL=C.UTF-8`
    ⇒ `locale.getpreferredencoding(False)` 返回 utf-8 ⇒ `_decode` 的 GBK 回退不可达 ⇒
    `test_commands_engine.py` 两条恒红。按上一轮已入库的判据加
    `env -u PYTHONUTF8 -u PYTHONIOENCODING -u LC_ALL -u LANG` 前缀跑, 闸门即绿(整条提交/推送链都带)。
  ⑤提交 `907890b`(22 文件 / **+720 −23**), 闸门 `test.quick` **1374 passed + 1 skipped**(4 worker),
  ref 三处一致; 推送 Gitee 成功(`ls-remote` == 本地 `907890b`)→ GitHub 镜像**直连成功**
  (`1845c9f..907890b`); 幽灵 diff 0。
