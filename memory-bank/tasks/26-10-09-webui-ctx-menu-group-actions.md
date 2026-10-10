# 26-10-09-webui-ctx-menu-group-actions — 单组右键菜单补齐(与多选批量菜单同项集)

**Status:** Done
**Added:** 2026-10-09
**Updated:** 2026-10-09
**Summary:** 用户报「辅种页单组右键菜单缺选项, 参考选中多组时右键菜单」。根因: `shared/tpl/ctx-menus.html` 右键菜单分四支, 其中 `menu.multi`(多选批量)分支 10 项, 而 `v-else`(单组)分支只有 开始/暂停/汇报 + 打开文件夹/流量图/删除 —— 同一批动作在「右键 1 组」与「Ctrl 选 2 组」两条路径上项集不一致。修法: 单组分支按批量菜单同序同图标补 6 项(重新校验/跳检/限速/移动/标签分类/导出), 目标 = 该组全部成员(`_groupTargets`), 下游整份复用多选链路(bulk 合单 / `_skipCheckDialog` / `_exportHashes` / `openMetaDialog`), 不为组级另开旁路。新增守阵 `test_frontend_ctx_menu_group_actions_parity`; 同步放宽 `skipCheckMulti` 的签名锚定(可选参)。实测数字见 `commands run kb.baseline`。
**Topics:** webui-ctx-menu-group-actions
**Refs:** memory-bank/pitfalls/web-ui/ctx-menu-branch-parity.md,memory-bank/testing/baselines/26-10-09-0933-webui-ctx-menu-group-actions.md

## 原始请求

用户(2026-10-09 09:19): 「WEBUI辅种页单组右键菜单缺选项, 参考选中多组时右键菜单」。属执行任务(报障 + 指方向), 非问答。

## 思考过程与决策

- **根因定位**: 右键菜单在 `shared/tpl/ctx-menus.html` 按上下文分四支(`menu.multi` 多选批量 / `menu.episode` 整集整剧 / `menu.hash` 单种子 / `v-else` 单组)。计划 `26-10-02-1955` 只给**多选分支**补了 限速/移动/跳检/导出(另含 重新校验/标签分类), 单组分支一直停在旧项集 —— 项集在两条路径上静默分叉。
- **修法选择: 复用多选链路, 不另开旁路**。组级入口把目标定为**该组全部成员** —— `_groupTargets()` 返回与 `_bulkTargets` 同形状的 `{groupKeys: [], memberHashes: memberHashesOf(g.members)}`, 下游整份交多选同一套(bulk 合单 / 跳检预检对话框 / 导出逐个下载 / `openMetaDialog`)。
  - **为什么目标取成员 hash 而非组 key**: 组键在 `_bulkTargets` 口径里算 **1 个目标** ⇒ 各对话框/回执的「N 个目标」在单组场景会显示成「1 个目标」而误导; 取成员 hash 后 N 直接等于**种子数**。后端 `_cmd_bulk_torrents` 的 keys/hashes 双通道语义等价(组键展开成员后与 hashes 合并去重), 故行为不变。
  - **跳检沿用预检状态机**: `skipCheckMulti` 加可选 `targets` 形参, 单组入口 `skipCheckGroup` 传该组目标 —— 三分流预检 / R2 实时复核 / 同日去重 / 备份 / 打标全部原样保留(只是聚合层复用)。
  - **`exportMulti` 抽 `_exportHashes`**: 多选(selHashSet 全量展开)与单组(该组成员)共用同一套串行下载核心, 零后端改动。
- **跳过新增 e2e**: 本改动纯加项, 新项与既有项结构逐字同构(Vue 渲染风险极低); 静态守阵已钉「项集 + 接线」, 与既有 CTX-03 多选守阵同机制。现有 e2e 全量复跑无回归(见基线切片)。

## 实现计划

单会话单轮: 模板补 6 项 → `commands.js` 组级入口 + 导出核心抽取 → `drawer.js` 三对话框加可选 `targets`/`scope` → 守阵 + 放宽既有签名锚定 → `test.full` + `dev.e2e` 复跑 → 收尾回写。

## 子任务状态表

| 子任务 | 内容 | 状态 |
|---|---|---|
| S1 | `ctx-menus.html` 单组(`v-else`)分支补 6 项(同序同图标 + 跳检 `flags.skip_check_menu` 门控) | Done |
| S2 | `commands.js` 新增 `_groupTargets` + 6 组级入口; `exportMulti` 抽 `_exportHashes` | Done |
| S3 | `drawer.js` 的 `editLimitsMulti`/`editMoveMulti`/`skipCheckMulti` 加可选 `targets`/`scope` | Done |
| S4 | 守阵 `test_frontend_ctx_menu_group_actions_parity` + 放宽 `test_skip_check_dialog_precheck_wired` 签名锚定 + 红验 | Done |
| S5 | `test.full` + `dev.e2e` 复跑 + 收尾回写(档案 / 切片 / 基线 / 坑档) | Done |

## 进度日志

- **2026-10-09 09:19**: 用户报障; 定位到 `ctx-menus.html` 四分支项集分叉(多选 10 项 vs 单组 6 项)。
- **2026-10-09 09:33**: S1–S4 落地。守阵红验通过(临时删单组分支的 `recheckGroup()` → 用例变红, 已还原); 三个改动 JS 过 `node --check`。`test.full` 与 `dev.e2e` 全绿(数字见 `commands run kb.baseline`)。
- **2026-10-09 09:33**(收尾): S5 —— 本档案立档 + activeContext 切片 + 基线切片 + 坑档 `pitfalls/web-ui/ctx-menu-branch-parity.md` + `conventions/webui.md` 菜单「分支项集一致」条; `kb.index` 重建。顺带回写 `web.skip_check_menu` 门控面文案(该键现在门控**单选/单组/多选**三处菜单项, 原「单选与多选」已不完整): `config/schema/groups.py` help / `docs/configuration.md` / `minimal.yml` / `memory-bank/config-reference/keys.md` 四处同步。
