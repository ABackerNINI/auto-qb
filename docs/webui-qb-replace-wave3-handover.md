# WEBUI 替代 qB 界面 · 波次三 实施交接文档

> 交接对象: 接手波次三剩余工作的编排者 / agent 集群。
> 生成时间: 2026-09-17。事实来源: `git` 实测 + 代码静态核对 + `uv run pytest tests -q` 实跑。
> 计划文档: [webui-qb-replace-wave3-plan.html](webui-qb-replace-wave3-plan.html) · 派工契约: `.cluster/webui-w3/{plan.md,contract.md}`

---

## 0. 结论摘要（先读这段）

1. **波次三主干已落地，合并靶状态干净且质量口径稳定**：`agentAutoClaw/develop` = `e7093b7`，工作区干净，全量测试 **988 passed / 0 skipped / 92% 分支覆盖率**（实测 30.5s）。按工作项计：**完全完成 16 项、仅差棱镜镜像 15 项、完全未做 3 项**（详见 §3 矩阵）。
2. **剩余工作 87% 集中在同一件事上：棱镜（prism）镜像欠账**。W1 表格层、W4 导航、W5 详情/设置的全部改动**只落在星图（atlas）+ 共享层（shared）**，棱镜模板与样式基本没跟。计划的 **W1d「移植到棱镜」从未执行**。
3. **另有 4 项与 UI 无关的独立欠账**：TBL-07（两 UI 都没做，只有一份未提交的星图草稿）、CTX-01/CTX-02（两 UI 都没做，无任何提交）、RFB-02 件4 视觉打磨（有孤儿提交 `48836d7` 未入库）。
4. **文档层完全滞后**：`testing.md`/`README.md` 仍写 949 用例（实际 988）；`memory-bank/activeContext.md` 停在 2026-09-15，波次三实施过程零记录；`想法.md` 勾选未回写。
5. **未回流主线**：波次三的 76 个提交全部只在 `agentAutoClaw/develop`，生产 `develop` 停在波次二后的分叉点（`merge-base = b9066c7`），需要一次 merge 收口。

**接手第一件事建议**：按 §7 的「批次 A」派工，把棱镜补到与星图同构；这是唯一能解锁「双 UI 走查 + 终验 + 合并回 develop」的前置。

---

## 1. 版本控制全景

### 1.1 工作树（9 个）

| 工作树 | 分支 | HEAD | 工作区状态 | 角色 |
|---|---|---|---|---|
| `D:\Projects\auto-qb` | `develop` | `5aa47b3` | ⚠️ `M 想法.md`（未提交） | **生产主工作树，禁碰**（红线） |
| `D:\Projects\auto-qb-autoclaw` | `agentAutoClaw/develop` | `e7093b7` | 干净（仅未跟踪 `.openclaw-attachments/`） | **合并靶 / 编排主线** |
| `D:\Projects\auto-qb-backend` | `backend/develop` | `f408dea` | ⚠️ 未跟踪 `tests/test_zz_probe_scratch.py`（探针残留） | 后端车道 |
| `D:\Projects\auto-qb-frontend` | `frontend/develop` | `beb8642` | ⚠️ `M src/auto_qb/web_ui/static/atlas/style.css`（TBL-07 草稿，未提交） | 星图车道 |
| `D:\Projects\auto-qb-trae` | `agentTrae/develop` | `e7093b7` | 干净 | 棱镜/兼容车道 |
| `D:\Projects\auto-qb-zcode` | `agentZCode/develop` | `e7093b7` | ⚠️ 未跟踪 `w1b1_punct_scan.py`（扫描脚本残留） | 机动车道 |
| `D:\Projects\auto-qb-other` | `other/develop` | `07925ae` | 干净 | 备用 |
| `…\auto-qb-other\.worktrees\be` | `feature/qb-replace-be` | `ed7a3c3` | 干净 | 波次二遗留（已内容入库） |
| `…\auto-qb-other\.worktrees\fe` | `feature/qb-replace-fe` | `46642f1` | 干净 | 波次二遗留（已内容入库） |

**关键点**：除 `develop`（生产）与两个波次二遗留分支外，**所有车道分支都已在 `agentAutoClaw/develop` 历史中**（`git log agentAutoClaw/develop..<分支>` 全部为空），即车道已全部合并回主线，也不存在"某车道有独有提交未合"的情况。

### 1.2 分支关系

```
b9066c7  ← merge-base（波次二收口点）
├── develop (5aa47b3)                    +3 提交（.github/skills → .agents/ 搬家，与波次三无关）
└── agentAutoClaw/develop (e7093b7)     +76 提交（波次三全部）
```

- `develop` 与 `agentAutoClaw/develop` **已分叉**（`3 / 76`），回流必须 `merge --no-ff`，不能快进。
- `develop` 领先 `origin/develop` 2 提交、`master` 领先 `origin/master` 2 提交，**远端未推送**（本地正常工作态）。
- 生产工作树 `D:\Projects\auto-qb` 的 `想法.md` 有未提交改动，内含**一条新需求**（见 §5.6）。

---

## 2. 波次完成度总表

| 波次 | 内容 | 计划规模 | 实际状态 |
|---|---|---|---|
| W0 | 缺陷快修 7 项 | XS/S | ✅ 7/7 完成（星图+棱镜+后端） |
| W1 | 表格呈现层 10 项 | L（主战场） | ⚠️ 星图 10/10、后端 ✅、**棱镜 ≈1/10（仅 `32e6134` 吸顶 top 解耦）** |
| W2 | 弹窗/右键/棱镜追剧 8 项 | M | ⚠️ 弹窗 4/4 双 UI ✅、棱镜追剧 ✅、**右键 2 项 0/2** |
| W3 | 限速体系 4 项 | M | ⚠️ SPD-01/02/03 ✅，**SPD-04 星图 ✅ / 棱镜 ❌** |
| W4 | 导航 IA 重排 3 项 | L | ⚠️ 星图 4/4 ✅、**棱镜 0/4** |
| W5 | 大面重构 2 项 | L | ⚠️ RFB-01 星图 ✅ / 棱镜 ❌；RFB-02 3.5/4 件、**件4 未入库且棱镜未跟** |
| 终验 | pytest + CDP 双 UI 冒烟 + 文档回写 + 交付报告 | — | ❌ 未做 |

**已完成（按合并靶主线提交，从旧到新）**

| 工作项 | 主线提交 | 落地面 |
|---|---|---|
| FIX-01 peers 端点 | `7763087` | 后端 |
| FIX-02 管理标签 hover / FIX-05 棱镜清除筛选 | `ec83199` | 星图 + 棱镜 ✅ |
| FIX-03 吸顶配色去撞 + 防透缝 | `9b95418` | **仅星图** |
| FIX-04 统计空值 + 防闪烁（a/b/补遗/prism 版） | `65d058f` `d8464d4` `b779e58` `8d21a8c` | 星图 + 棱镜 ✅ |
| CTX-03 全局右键屏蔽 | `bba2352` | 共享层（双 UI）✅ |
| NAV-02 双 UI 切换图标 | `c7cd69b` | 双 UI ✅ |
| TBL-04 数据源透出（后端） | `984f73b` | 后端 |
| TBL-01/02/04 渲染 + FIX-07 Esc 栈 | `33aa157` | **仅星图 + 共享层** |
| 中文标点恢复 | `179217c` | 共享层 |
| TBL-03 状态底 + 数值色阶 + 去名称图标 | `5449b3f` | **仅星图 + 共享层** |
| TBL-05 表头拖动重排 + 右键列选择器 | `ce8cbb3` | **仅星图 + 共享层** |
| TBL-06 补列 + FIX-06 已选栏并入筛选行 | `69404d3` | **仅星图 + 共享层** |
| 棱镜吸顶 top 与 --bulk-h 解耦 | `32e6134` | 棱镜 ✅ |
| TBL-08 rail 退役 + 底部状态栏 | `327611c`（`a6051ba`+`d02618d`） | **仅星图 + 共享层** |
| W1c 修复补遗（冲突标记清理 + 状态栏限速入口） | `1f8af8c` `c599947` | 星图 |
| DLG-01/02/03/04 前端 | `13344e6` `3f1e720` | 星图 + 共享层 ✅ |
| DLG-04 `/api/paths` + DLG-02 bulk keys | `f408dea` | 后端 |
| DLG-03/04 棱镜移植 | `1db09ef` | 棱镜 ✅ |
| DLG-01/02 棱镜对齐 | `f97b1b5` | 棱镜 ✅ |
| PRS-01 棱镜追剧视图 | `225977d` | 棱镜 ✅ |
| SPD-01 末档 clamp 回归锁定 | `9b08b5b` | 后端 |
| SPD-01 多曲线合并用例 | `ecd4f1d` | 后端测试 |
| SPD-03 enabled 全管线 | `9b08b5b`（+ `bf10e15` 裁决去重） | 后端 + 共享层 |
| SPD-02 预览末档压缩 / SPD-04 限速弹窗 | `81537a7`（`ec2969c`） | **仅星图 + 共享层** |
| W4 日志→设置 / 三态导航 / 设置右移 / 动态 logo | `82c5d16` `78672fa` `9c9d1de` `2b4ad3b` | **仅星图 + 共享层** |
| RFB-01 详情抽屉纯展示重构 | `ada3d77`（`f78aeea`+`1760108`+`6021399`） | **仅星图 + 共享层** |
| RFB-02 件1 栅格令牌 / 件2 统一注记 / 件3 文案+toast | `beb8642` `f781985` `1371bdb` | 件1/2 **仅星图**；件3 共享层（双 UI）✅ |

---

## 3. 32 工作项逐项对照矩阵

图例：✅ 完成 · ⚠️ 部分 · ❌ 未做 · — 不适用

| ID | 星图 | 棱镜 | 后端 | 状态 | 证据 / 缺口 |
|---|---|---|---|---|---|
| FIX-01 peers 端点 | — | — | ✅ | 完成 | `web.py:396 sync_torrent_peers(torrent_hash=hash)` |
| FIX-02 管理标签 hover | ✅ | ✅ | — | 完成 | `atlas/style.css:1555`、`prism/css/components.css:552` |
| FIX-03 吸顶配色+透缝 | ✅ | ❌ | — | 半完成 | `9b95418` 只改 `atlas/style.css` |
| FIX-04 统计空值+闪烁 | ✅ | ✅ | ✅ | 完成 | atlas 骨架常驻 + prism `8d21a8c` |
| FIX-05 清除筛选常显低饱和 | — | ✅ | — | 完成 | `ec83199` |
| FIX-06 已选栏并入筛选行 | ✅ | ❌ | — | 半完成 | atlas `.bulk-inline`；prism 仍独立 `.bulk-bar` |
| FIX-07 Esc 可取消栈 | ✅ | ✅ | — | 完成 | 逻辑在 `shared/app.js:865`（共享）；模板层弹层顺序已对 |
| TBL-01 空值空白 | ✅ | ❌ | — | 半完成 | atlas `fmtSpeed/fmtSize` 返空；prism 表体仍走 `fmtSpeedOrDash`/`fmtSizeOrDash`（`index.html:492-502,553-556,638-674,776-788,809-812`） |
| TBL-02 移除"不限速" | ✅ | ✅ | — | 完成 | 共享 `app.js:1429 fmtLimitBytes`（0 → 空串）；棱镜种子页 `up_limit/dl_limit` 已调用该方法，仅 `rail` 提示文案（`index.html:423`）与 `fmtLimit`（`:396`，随 rail 退役）需一并核对 |
| TBL-03 状态底+数值色阶+去图标 | ✅ | ❌ | — | 半完成 | atlas `.tone-low/.tone-high` + `numTone()`；prism 无 tone 类、`.g-status` 仍在名称前（`index.html:487-490`、`638-641` 等） |
| TBL-04 做种/用户 qB 格式 | ✅ | ❌ | ✅ | 半完成 | 后端已透出 4 字段；prism 种子页仍是 `{{ m.num_seeds \|\| 0 }}`（`index.html:655-656`），未用 `fmtPeersQb` |
| TBL-05 列拖动排序+右键隐藏 | ✅ | ❌ | — | 半完成 | atlas 四表 `startColDrag`；prism 表头无 mousedown/落点线 |
| TBL-06 组表/明细表补列 | ✅ | ❌ | ✅ | 半完成 | 列模型在 `shared/app.js`（prism 会继承列集合）；prism 模板未渲染新列分支 |
| TBL-07 全宽 + 横向滚动遮挡 | ❌ | ❌ | — | **未做** | 仅 `frontend` 工作区有未提交草稿（atlas 3 处 `max-width:2560px` 未删）；prism `views.css:9,208,553` 仍在 |
| TBL-08 底部状态栏 + rail 退役 | ✅ | ❌ | — | 半完成 | atlas `.statusbar` + `--statusbar-h`；prism `.rail` 整块仍在（`index.html:332-430`、`views.css:12-36,482,574`） |
| DLG-01 删除确认框调大+去明细 | ✅ | ✅ | — | 完成 | `--modal-wide-w: 840px` 双端；`modal.details` 仅保留计数摘要 |
| DLG-02 删除语义计数 | ✅ | ✅ | ✅ | 完成 | `app.js:2190-2201 bulkDeleteLabel()`；后端 bulk 组键模式 |
| DLG-03 添加种子改版 | ✅ | ✅ | — | 完成 | `addStart`（添加后开始，默认不勾）+ 链接折叠 + combobox |
| DLG-04 位置选择 | ✅ | ✅ | ✅ | 完成 | `web.py:178 /api/paths`（D3 方案 A：已知目录聚合） |
| CTX-01 彩色图标集 | ❌ | ❌ | — | **未做** | 无任何提交；右键菜单仅 4 个语义色（play/pause/sync/danger），其余灰；统计/日志/主题/HR 筛选器图标仍灰 |
| CTX-02 触发源强调 | ❌ | ❌ | — | **未做** | 无任何提交；`app.js` 无 `menu.src`/触发源高亮状态 |
| CTX-03 屏蔽非导航栏右键 | ✅ | ✅ | — | 完成 | `app.js:903`（`header.topbar` 与输入元素白名单） |
| SPD-01 末档 clamp | — | — | ✅ | 完成 | `curves.py` 末档延续 + 回归用例锁定（`9b08b5b`/`ecd4f1d`） |
| SPD-02 预览末档压缩 | ✅ | ✅ | — | 完成 | 共享 `config_editor.js:855-946`（按档位边界分段等宽 + ∞ 提示） |
| SPD-03 enabled 配置 | ✅ | ✅ | ✅ | 完成 | `models.py:174-179`、`validation/curves.py:26-28`、`config_editor.js:753` |
| SPD-04 限速改弹窗 | ✅ | ❌ | — | 半完成 | atlas `.speed-dialog`；prism `views.css:574 .rail-speed-ov` 表单仍在 |
| NAV-01a 统计入状态栏 | ✅ | ❌ | — | 半完成 | atlas `.statusbar` 内 `统计` 按钮；prism 无状态栏 |
| NAV-01b 日志移入设置 | ✅ | ❌ | — | 半完成 | atlas `cfg.activeGroup === '__logs'`；prism 仍顶栏 `openLogs` + `page==='logs'` |
| NAV-01 导航三态+设置右移 | ✅ | ❌ | — | 半完成 | atlas `nav.tabs-right` + `goView()`；prism 仍 辅种管理/设置/统计/日志 四页 |
| NAV-02 切换图标 | ✅ | ✅ | — | 完成 | `i-prism` / `i-orbit` 双端 |
| NAV-03 动态 logo | ✅ | ❌ | — | 半完成 | atlas `.brand-orbit` 12s 旋转 + `prefers-reduced-motion`；prism 仍 `icon.png` 静态图 |
| RFB-01 详情抽屉纯展示 | ✅ | ❌ | — | 半完成 | atlas 移除 9 按钮 + `.f-row` 图标字段行 + 860px；prism `index.html:1503-1511` 9 按钮仍在 |
| RFB-02 设置页重构 | ⚠️ | ❌ | — | 半完成 | 件1(`5179092`)/件2(`f781985`) 仅 atlas；件3(`1371bdb`) 共享层已双 UI；**件4 视觉打磨 `48836d7` 未入库** |
| PRS-01 棱镜追剧视图 | — | ✅ | — | 完成 | `225977d` |

**统计**（矩阵共 34 行 = 32 项 + NAV-01a/01b 两个子项）：**完全完成 16 行 / 部分完成 15 行 / 完全未做 3 行（TBL-07、CTX-01、CTX-02）**，另有 RFB-02 件4 未入库。
在 15 行"部分完成"里，**13 行只差棱镜**（FIX-03、FIX-06、TBL-01、TBL-03、TBL-04、TBL-05、TBL-06、TBL-08、SPD-04、NAV-01、NAV-01a、NAV-01b、NAV-03、RFB-01、RFB-02 中的棱镜部分）——即"批次 A 补棱镜"一次可消解绝大部分欠账。

---

## 4. 代码静态事实（接手者不必重新摸底）

### 4.1 双 UI 共享层是"逻辑单一来源"，但模板层各一份

- 共享（改动即双 UI 生效）：`web_ui/static/shared/app.js`（183KB，Vue 逻辑全部）、`config_editor.js`、`config_rules.js`。
- 各一份：`atlas/index.html`(160KB)+`atlas/style.css`(116KB) 与 `prism/index.html`(159KB)+`prism/css/*.css`。
- **列模型与持久化键是共享的**：`shared/app.js:120 COLS_STORE_KEY = "autoqb_cols_v4"`，列序（`colOrder`）、隐藏集合、列宽 per-page 全部落在同一个 localStorage 键 → **棱镜会继承星图设置的列序与列宽**，它只是没有拖动交互 UI。这点决定了 TBL-05 的棱镜补做只需加"交互入口"。
- 部分能力已经在共享层落地，棱镜只是"没有调用"：`fmtPeersQb`（TBL-04）、`fmtLimitBytes`（TBL-02）、`bulkDeleteLabel`（DLG-02）、`drawerGeneralSections()`（RFB-01 数据）、Esc 栈（FIX-07）、`confirmDialog`/`modal.wide`（DLG-01）。

### 4.2 后端改动面（波次三累计，相对波次二基线 `3e57917`）

```
src/auto_qb/web.py                                   +40/-?    ← peers 修复、/api/paths、speed/mode enabled 语义
src/auto_qb/mixins/web_view.py                        +5      ← 成员/单种透出 num_seeds/num_leechs/num_complete/num_incomplete
src/auto_qb/mixins/web_commands.py                   +28/-?    ← bulk 组键模式
src/auto_qb/mixins/speed_curve.py                     +5/-?    ← enabled 短路
src/auto_qb/curves.py                                （末档语义已满足，回归用例锁定）
src/auto_qb/config/models.py                          +2      ← GlobalSpeedLimitCurve.enabled
src/auto_qb/config/validation/curves.py               +8/-?    ← enabled 键校验
src/auto_qb/config/loaders.py                         +8      ← enabled 解析
src/auto_qb/config/schema/{groups,rules,trackers}.py 文案用户化 84 处（RFB-02 件3）
tests/{helpers,test_config,test_speed_curve,test_sync,test_web}.py  +438/-9
```

### 4.3 测试闸门（实测）

```
uv run pytest tests -q    →   988 passed, 0 skipped, 2 warnings, 30.53s, TOTAL 分支覆盖 92%
```

- 波次二闸门 971 → 波次三 **+17 个用例**。
- 已知环境性红项 `test_ui.py::test_autostart_windows_registry`（真写 HKCU）本次**通过**。
- `test_web.py` 是主要落点（+255 行），覆盖 peers、/api/paths、bulk keys、speed mode 等新端点。

---

## 5. 未完成清单（按优先级）

### 5.1 P0-BLOCKER · 棱镜（prism）镜像欠账

计划的 **W1d**（"把 W1a-c 视觉与交互移植到棱镜"）从未执行，加之 W4/W5 的原生实现也全在星图侧，导致棱镜落后一整个波次。**这是唯一阻塞终验的项**（终验要求"同一操作双 UI 对拍"）。

需补做（精确锚点）：

| # | 内容 | 锚点 | 对应项 |
|---|---|---|---|
| P-1 | 顶栏 IA 重构：辅种管理/设置/统计/日志 四页 → 左侧 分组/种子/追剧 三态 + 右侧设置；移除顶栏日志与统计入口 | `prism/index.html:128-148`（`nav.tabs`），参照 `atlas/index.html:126-235` | NAV-01 / NAV-01b / W4(2/4,3/4) |
| P-2 | rail 整块退役 → 底部状态栏（速度摘要 + 统计入口 + 限速入口 + 状态徽章），新增 `--statusbar-h` 并做内容区底部预留 | `prism/index.html:332-430 .rail`、`prism/css/views.css:12-36,482-483` | TBL-08 / NAV-01a |
| P-3 | 日志页 → 设置页 `__logs` 章节（`openLogs()` 转章节入口，删 `page==='logs'`） | `prism/index.html:145,1435 logs-page` | NAV-01b |
| P-4 | 已选/批量条并入筛选行（删独立 `.bulk-bar` 吸顶） | `prism/index.html:432-449`、`views.css:185-191` | FIX-06 |
| P-5 | 表头拖动重排 + 右键即席列选择器（落点指示线、`drag-src` 态） | prism 四张表表头（对照 `atlas/index.html:351-365,429-437,503-517,598-612`） | TBL-05 |
| P-6 | 移除名称前状态图标；行状态底色 + 七列三档数值色阶（`.tone-low/.tone-high`） | `prism/index.html:487-490`、`prism/css/views.css`（补 tone 规则） | TBL-03 |
| P-7 | 空值空白化：`fmtSpeedOrDash/fmtSizeOrDash` → `fmtSpeed/fmtSize`；做种/用户 → `fmtPeersQb` 口径；组表/明细表/追剧表/内容表逐列核对 | `prism/index.html:492-502,553-556,638-674,721-781,808-812` | TBL-01 / TBL-02 / TBL-04 |
| P-8 | TBL-06 新列在棱镜模板中的渲染分支（添加于/保存路径/最近添加等） | 同上表体分支 | TBL-06 |
| P-9 | 详情抽屉纯展示化：移除 9 个操作按钮，改 `.f-row` 图标字段行排版（数据函数 `drawerGeneralSections()` 已共享） | `prism/index.html:1503-1511,1532-1560` | RFB-01 |
| P-10 | 限速改弹窗：删 `.rail-speed-ov` 覆盖表单，接入 `openSpeedDialog()`（共享逻辑已在 `app.js:3230+`） | `prism/index.html:409-423`、`views.css:574-588` | SPD-04 |
| P-11 | 设置页栅格令牌化 + 宽度放开 + `.ce-note` 注记体系 | `prism/css/views.css:269`（190px 硬编码）、`.ce-page` | RFB-02 件1/件2 |
| P-12 | 动态 logo（`i-orbit` 旋转 + `.qb` 字样比例） | `prism/index.html:118`（`icon.png` 静态）、prism 顶栏样式 | NAV-03 |
| P-13 | 吸顶表头配色去撞 + 吸顶链受控重叠防透缝 | prism 对应 `.sticky-head` 规则 | FIX-03 |

**注意**：棱镜 `prism/css/*.css` 是 **CRLF 行尾**，编辑锚必须匹配原行尾或采用追加式修改，严禁整文件重排行尾（历次踩坑）。

### 5.2 P0 · TBL-07 全宽 + 横向滚动遮挡（两 UI 均未完成）

- 现状：`atlas/style.css:299,1561,1602` 与 `prism/css/views.css:9,208,553` 都还有 `max-width: 2560px; margin: 0 auto;`。
- 星图已有一份**未提交**草稿，位于 `D:\Projects\auto-qb-frontend`（`git diff` 可见）：删 3 处 `max-width`、`padding` 由 `16px 18px` 收到 `16px 12px`。
- 缺口：① 该草稿未提交未入库；② 棱镜同改未做；③ 用户诉求里的"横向滚动时被两侧背景遮挡"需一并实测复现再定方案（可能是 `overflow` 容器 + 背景层叠问题，草稿未必覆盖）。

### 5.3 P1 · CTX-01 / CTX-02（两 UI 均未实施，无提交）

- **CTX-01 彩色图标集**：右键菜单绝大多数项仍是单色 `#i-*`；点名需彩色的还有 **统计 / 日志 / 主题 / HR 筛选器** 图标。做法建议：新增语义色类（复用既有 `--green/--blue/--warn/--violet/--cyan` 令牌），避免引入第二套 sprite；注意主题切换令牌与 WCAG 对比度（prism 五主题）。
- **CTX-02 触发源强调**：菜单 open 时给触发源（行/按钮）挂 accent 类，close 时移除；`menu` 状态在 `shared/app.js`，**需新增触发源引用字段**（当前无 `menu.src`），双 UI 模板各自绑定。

### 5.4 P1 · RFB-02 件4（设置页视觉打磨）未入库

- 孤儿提交 `48836d7`（"设置页视觉打磨(件4)：折叠头内边距统一 8px、段间距 8px、标题分级 group 13.5/section 13/subcard 12、subcard 行高 7px、段内奇偶区隔、hover 提亮统一"）在 `agentZCode` 旧线上，**不在 `HEAD` 历史中，且没有重放版**。
- 同批被裁决重放的兄弟提交：`66f4111`/`f38eb32`/`3da9f1a`/`ab9a863` → 已由 `82c5d16`/`78672fa`/`9c9d1de`/`2b4ad3b` 重放；`f359390`/`f396972` → 已由 `1371bdb` 按字节核验入库。**唯独 `48836d7` 遗漏**。
- 处置建议：`git show 48836d7 -- src/auto_qb/web_ui/static/atlas/style.css` 逐块核验后重放（不要直接 cherry-pick，旧基线行号会冲突）；核验后回写该提交已有内容是否被后续 `beb8642`/`f781985` 部分覆盖。

### 5.5 P1 · 终验与文档回写（全部未做）

| 项 | 现状 | 目标 |
|---|---|---|
| 全量 pytest | 已跑，988 passed | 回写基线 |
| Edge CDP 双 UI 冒烟 | 未做（波次三全程未做浏览器冒烟） | 按波次计划 §7 四闸门执行，截图落 `.openclaw/tmp/wave3/` |
| 真机 `--dry-run` | 未做（SPD-01/03 改的是生产限速逻辑，**必须**观察一个档位周期） | 观察通过后关闭 W3 |
| `memory-bank/testing.md` | 写 `949 passed` | 改 `988 passed`（单点） |
| `README.md` | 第 25 行写 `949 个用例`；Web UI 章节仍是旧拓扑 | 改数字；按新导航拓扑重写 Web UI 章节 |
| `memory-bank/activeContext.md` | 最后更新 2026-09-15，**波次三实施零记录**（只有 09-16 的计划会话条目） | 补会话纪要 + 收敛"正在进行" |
| `memory-bank/progress.md` / `pitfalls.md` / `modules.md` / `systemPatterns.md` | 无波次三内容 | 补（尤其 prism CRLF、--bulk-h 退役、rail 退役、状态栏令牌等新坑） |
| `想法.md` | WEB UI 章节仍是旧定位（"不是要做一个 qb 的 web ui"），30 条诉求未勾选 | 回写勾选 + 更正定位 |
| `docs/webui-qb-replace-wave3-plan.html` | 无执行状态标注 | 加状态回写（各 ID 完成度） |
| 交付报告 | `DELIVERY/` 目录**不存在** | 补 `DELIVERY/webui-qb-replace-wave3-report.md`（波次二有先例） |

### 5.6 P2 · 分支回流与工作区清理

1. **回流 `develop`**：`agentAutoClaw/develop`(76 提交) → `develop`，`merge --no-ff`（已分叉，不能 FF）。`develop` 侧新 3 提交是 `.github/skills → .agents/` 目录搬家，冲突面预计在根目录结构，需实测。
2. **清理工作区残留**（都不该提交）：
   - `D:\Projects\auto-qb-frontend`：`M atlas/style.css`（TBL-07 草稿）→ 要么补完提交，要么 `checkout -- .` 丢弃后重做。
   - `D:\Projects\auto-qb-backend`：未跟踪 `tests/test_zz_probe_scratch.py`（探针）→ 删除。
   - `D:\Projects\auto-qb-zcode`：未跟踪 `w1b1_punct_scan.py`（扫描脚本）→ 删除或归档。
   - `D:\Projects\auto-qb`（生产）：`M 想法.md` → 内含**新需求一条**，见下；按"生产工作树禁提交"红线，应把该条目摘出后在非生产分支回写。
3. **生产工作区新增需求（未纳入 32 项）**：
   > `"0分钟"做种时长且没有HR要求改为不显示`
   （位于 `d:\Projects\auto-qb\想法.md` 约 219 行，紧跟 peers 报错条目之后，未提交。）
   这条是用户新追加的 UI 显示规则，**尚未进入任何计划或波次**，建议纳入棱镜镜像批次之后的小修单。

### 5.7 P2 · 未尽事项（计划 §7 收尾清单）

- 对照 qB WebUI 功能面复核「替代 qB 界面」差距清单，决定是否开启**波次四**。
- 波次计划 §6 已记录但本轮未发生的坑：残留服务/端口占用导致冒烟假败、`--bulk-h` 语义变化、工作树脏状态挡合并——接手时按需复核。

---

## 6. 红线与工程约束（每单必带）

### 6.1 项目红线（AGENTS.md）

- **`config.yml` 与 `auto-qb-data/`**：生产文件，任何 agent 不许改 / 提交 / 顺手格式化。生产主工作树 `D:\Projects\auto-qb` 禁碰（除只读摸底）。
- **黄金法则 4**：新配置键必须进 `validate_config` 并同步 `config/schema/`，守卫测试会查。（SPD-03 `enabled` 已合规：`models.py` + `validation/curves.py` + `loaders.py` + `config_editor.js` 特殊段。）
- **黄金法则 1**：限速动作幂等——SPD-01 改的是档位查找，不许引入跨 tick 状态。
- **测试基线单点**在 `memory-bank/testing.md` 顶部，回写只改那里。
- 新增测试必须同步该测试文件头部 docstring 的「测试计划」清单（项目明文规定）。

### 6.2 JS↔DOM 契约（改前端不得破坏）

`.group-head` / `.detail-head` / `gridStyle` 列数 / `.search-hit` / `.ctx-menu` / `.sticky-head` + `--head-h` / `.bulk-bar` + `--bulk-h`（**已在 `69404d3` 退役，勿复活**）/ `tpl-ce-field` / sprite `#i-*` / toast 确认框单例 / 列宽记忆（`autoqb_cols_v4`）/ `watch(page)` 切页时表格卸载与列宽重实体化 / 底部状态栏 `--statusbar-h`。

### 6.3 已固化的新令牌

| 令牌 | 值 | 用途 |
|---|---|---|
| `--statusbar-h` | `34px` | 底部状态栏自身高度 + 内容区底部预留（共用，防取整透缝） |
| `--modal-wide-w` | `840px` | 删除类宽确认框（双端一致） |
| `--ce-label-w` / `--ce-ctl-gap` / `--ce-input-max` | `200px` / `12px` / `720px` | 设置页字段行栅格（**目前仅星图声明**，棱镜仍是 190px 硬编码） |

### 6.4 环境坑（历次实证，接手必读）

- **prism 的 `css/*.css` 是 CRLF 行尾**——编辑锚按原行尾匹配或追加式修改。
- **PowerShell 编码**：写中文/补丁文件一律 UTF-8；不要用 `>` 重定向生成 git patch（会产生 UTF-16 坏补丁，用 `--output`）。
- **bot 单窗口 20 分钟**装不下大型前端任务——按单工作项派发 + 给代码地图 + 允许从落盘现场续作。波次三已多次出现"超时 agent 落盘、主线抢救入库"，接手时请预期同样节奏。
- **冒烟前清场**：按端口杀残留进程、每轮独立 Edge profile（同 `user-data-dir` 会单例移交并产生幽灵操作）。
- **吸顶缝隙类 bug**：`margin`/`gap` 计入补偿变量是历史根因；改完必须做"窄视口 + 滚动"联动冒烟。
- **工作树脏状态挡合并**：各 worktree 提交前 `checkout -- .` 清理冗余脏状态。
- **沙箱不可用**：本机 `run_in_terminal` 沙箱因 DACL 权限失败（`BaseContainer is unavailable`），git/pytest 一律需非沙箱执行。

---

## 7. 建议续作路线图

### 批次 A（P0，解锁终验）· 棱镜镜像补做

- **A1**（1 agent，棱镜车道）：P-1 ~ P-5 —— 顶栏 IA、底部状态栏、日志入设置、批量条并入筛选行、列拖动重排。
  - 内部顺序：IA 骨架 → 状态栏 → 批量条 → 列拖动（后两项依赖布局稳定）。
- **A2**（1 agent，棱镜车道，与 A1 串行）：P-6 ~ P-13 —— 色阶/空值语义/补列/抽屉/限速弹窗/设置页栅格/动态 logo/吸顶配色。
- **A3**（1 agent，任意前端车道）：TBL-07 双 UI 全宽 + 横向滚动遮挡实测修（先复现，再改；星图有半成品草稿可参考，但不建议直接沿用未验证草稿）。
- **闸门**：全量 pytest 保持 988+ 全绿；星图↔棱镜"同一操作双 UI 对拍"清单逐项走查。

### 批次 B（P1，独立小单，可与 A 并行）

- **B1** CTX-01 彩色图标集（双 UI，含统计/日志/主题/HR 筛选器图标；五主题对比度自查）。
- **B2** CTX-02 触发源强调（需在 `shared/app.js` 新增 `menu.src` 字段）。
- **B3** RFB-02 件4 重放（核验 `48836d7` 后补入库）。
- **B4** 新需求 `"0分钟"做种时长且无 HR 要求不显示`（小单，星图+棱镜同步）。

### 批次 C（P1，收尾）

- **C1** Edge CDP 双 UI 冒烟（截图落 `.openclaw/tmp/wave3/`）+ 真机 `--dry-run`（限速档位周期）。
- **C2** 文档回写：`testing.md`(988) / `README.md` / `activeContext.md` / `progress.md` / `pitfalls.md` / `modules.md` / `systemPatterns.md` / `想法.md` / 计划文档状态。
- **C3** 工作区清理（§5.6）+ `DELIVERY/webui-qb-replace-wave3-report.md`。
- **C4** `merge --no-ff` 回流 `develop`，再按需评估波次四。

---

## 8. 附录 · 核对命令

```bash
# 工作树与分支
git worktree list
git branch -avv
foreach ($b in @('backend/develop','frontend/develop','agentTrae/develop','agentZCode/develop')) { git log --oneline agentAutoClaw/develop..$b }

# 波次三改动面
git log --oneline --first-parent 3e57917..agentAutoClaw/develop
git diff --stat 3e57917..HEAD -- tests/ src/auto_qb/web.py src/auto_qb/mixins/ src/auto_qb/config/

# 测试闸门
uv run pytest tests -q                    # 期望 988 passed / 92%

# 双 UI 差距速查（棱镜侧应为空/应改）
Select-String -Path src/auto_qb/web_ui/static/prism/index.html -Pattern 'startColDrag|statusbar|__logs|f-row|tone-'
Select-String -Path src/auto_qb/web_ui/static/prism/css/views.css -Pattern 'max-width: 2560px|\.rail'
Select-String -Path src/auto_qb/web_ui/static/atlas/style.css,src/auto_qb/web_ui/static/prism/css/views.css -Pattern 'max-width: 2560px'
```

**遗留未跟踪/未提交文件**（接手时清理）：

```
D:\Projects\auto-qb\想法.md                                   M  （含新需求一条）
D:\Projects\auto-qb-frontend\src\auto_qb\web_ui\static\atlas\style.css   M  （TBL-07 草稿）
D:\Projects\auto-qb-backend\tests\test_zz_probe_scratch.py    ?? （探针）
D:\Projects\auto-qb-zcode\w1b1_punct_scan.py                  ?? （扫描脚本）
```
