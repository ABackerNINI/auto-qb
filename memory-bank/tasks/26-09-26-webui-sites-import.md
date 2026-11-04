# 26-09-26-webui-sites-import — WEB UI 一键导入缺失站点（对齐 CLI --export-yaml --only-missing）

**Status:** Done
**Added:** 2026-09-26
**Updated:** 2026-11-05
**Summary:** 设置页「站点」pill 行新增「⤓ 导入缺失站点」按钮：`GET /api/sites/missing`（新路由模块 `routes/sites.py`，只读）复用 `core/exporter.py` 同一套构件（`collect_all_tracker_hostnames` / `find_missing_domains` 双向包含匹配 / `build_tracker_entry` 默认条目）扫描 qB 全部种子的 tracker 域名，找出未配置站点并生成默认配置；前端确认对话框列出站点名(域名)后填入编辑器**待审**（不自动保存，示例值不未经审阅生效），用户核对后走既有「保存」→ PUT /api/config 校验/备份/热重载生效。`exporter.py` 提取 `gen_tracker_name`（既有占用/批内同名 → `_N` 后缀）供 CLI 导出与 webui 扫描共用。2026-11-05 修复批量失败误报：collector 带失败计数、过半(严格多数)即 502/TrackerScanBatchError 拒出结果，不拿空集冒充「无缺失站点」。**已入库 `e3fb35d`**（提交后合流远端 9 笔，合并提交 `8bacfae` 推送）。
**Topics:** webui-sites-import
**Refs:** memory-bank/plans/26-11-03-2337-plan-missing-site-tracker-merge.html,memory-bank/issues/26-11-04-2347-bug-missing-scan-partial-failure.html

## 原始请求

> 为webui添加一键导入站点功能，类似--export-yaml --only-missing，生成默认配置

（经 EnterPlanMode 计划模式调研并获用户批准后实施；询问「导入后保存方式」用户未作答，按推荐方案执行：填入编辑器待审、不自动保存。）

## 思考过程与决策

- **站点 = 配置 `trackers` 段**：与 CLI 导出同一套构件可直接复用，匹配口径（tracker 域名与已配置 domains 双向包含）与默认值（tags 自动生成 / `0KiB/s` 占位限速 / hr 示例值 3D·0·12H·80%）零漂移。
- **D1 只加一个后端端点（预览），写路径复用既有 PUT /api/config**：扫描端点只读返回缺失站点与默认条目；合并进树、校验、掩码还原、备份、热重载全部走前端既有 `cfgSave()` 路径 —— 不在服务端复刻第二套"合并+落盘+热重载"逻辑。
- **D2 填入编辑器待审而非确认即保存（保守默认，黄金法则 2）**：CLI 导出的条目带 hr 示例值与占位限速，注释标明「需用户修改」；webui 里一旦保存即对站点实际生效（HR 管束/限速），未经审阅直接生效违背保守默认。UI 上确认框明示「默认限速为不限、HR 为示例值 —— 保存前请在编辑器中核对」，填入后靠既有「有改动还没保存」LED + 「保存」按钮完成闭环。
- **D3 web 线程直调 qB API 有既有先例**（torrent_detail.py 同模式 `touch_web_client` + `require_client`）：扫描是只读 qB 查询，不碰任务队列与 state_file，不违反单一写线程假设；断连 `require_client()` 503（不拿空扫描冒充"没有缺失站点"），扫描中途 qB 调用失败映射 502 带原因。
- **D4 站点名生成提取单点 `gen_tracker_name(domain, taken)`**：原内联在 `export_yaml_template` 的命名循环（非法字符→`_`、冲突加 `_N`）提取成函数，`taken` 就地登记；CLI 导出与 webui 扫描共用，行为不变（既有 test_exporter 守护），新单测直钉。
- **D5 前端合并跳过已存在同名键**：防「扫描后、保存前」窗口内待生效热重载引入同名站点的竞态覆盖；atlas / prism 两套 UI 模板各自成块，按钮两处成对加（shared 层逻辑单点）。

## 实现计划

1. `core/exporter.py`：提取 `gen_tracker_name`，`export_yaml_template` 改调（行为不变）。
2. 新路由模块 `webui/server/routes/sites.py`：`GET /api/sites/missing`（只读）→ `{torrents, domains, sites:[{name, domain, entry}]}`；`routes/__init__.py` 注册（追加在 `_hr` 后）。
3. 前端：`config_hub.js::hubImportSites()`（防重入 `hub.importing` → 扫描 → 无缺失 toast / 有缺失 confirmDialog → 合并跳重 → toast 引导保存）；两套 UI `index.html` 站点 pill 行加按钮。
4. 测试：金清单 +1；后端 5 条（默认条目结构/名称冲突/全覆盖空/断连 503/502）；前端接线守阵 1 条；`gen_tracker_name` 单测 1 条；两文件「## 测试计划」docstring 同步。
5. 文档：docs/configuration.md 站点配置注释补 webui 一键导入入口。

## 子任务状态表

| 子任务 | 状态 | 说明 |
|---|---|---|
| exporter 提取 `gen_tracker_name` | Done | CLI 导出与 webui 扫描共用命名规则；既有 test_exporter 全绿（行为不变） |
| 路由模块 `routes/sites.py` + 注册 | Done | `GET /api/sites/missing` 只读；断连 503 / 扫描失败 502；金清单 61→62 |
| 前端 `hubImportSites()` + 两套 UI 按钮 | Done | 填入编辑器待审；跳过同名键防竞态；atlas / prism 成对 |
| 测试（+7）与守阵同步 | Done | 见 baseline 顶部；「## 测试计划」docstring 已同步 |
| 文档回写 | Done | docs/configuration.md / README 设置页段 / progress/implemented-webui / baseline |
| 真机走查 | Pending | 需真实 qB：设置 → 站点 → 导入按钮 → 确认框 → 填入编辑器 → 保存热重载全链走查（本会话无真机 qB，未做浏览器冒烟）。2026-11-04 合并扩展轮已补「设置 → 站点 → 导入 → 确认框 → 填入编辑器」三路径浏览器冒烟（桩载荷，零保存）；保存/热重载通道另由 RM09-11 真机覆盖，全链同轮未串跑 |

## 进度日志

- **2026-09-26 (一次落地全绿)** — 调研（两路 Explore：exporter 语义 + webui 结构）→ EnterPlanMode 计划获批 → 实施。
  ① 后端：`gen_tracker_name` 提取 + `routes/sites.py`（40 行只读端点）+ `ROUTE_BUILDERS` 注册；金清单测试同步。
  ② 前端：`config_hub.js` 新增 `hubImportSites()`（约 40 行），两套 UI 模板按钮成对加（`hb-pill` 样式与「＋ 新增站点」一致）。
  ③ 测试：首跑 2 红 —— 根因是替身 `torrents_info` 给了 dict 而 `collect_all_tracker_hostnames` 按 `tor.hash` **属性**取值，AttributeError 被 try/except 吞掉 → 扫描恒空；改 `SimpleNamespace(hash=...)` 后全绿（CLI 侧 FakeClient 无此问题，因其返回 FakeTorrent 对象）。
  ④ 验证：test_exporter + test_cli 33 绿；test_web 定向 7 绿、全文件 155 passed + 1 skipped；**全量 test.full 1623 passed + 1 skipped, TOTAL 92%**（10952 语句 / 785 未覆盖 / 3624 分支 / 326 partial）。
  ⑤
- **2026-09-26 (合流推送)** — 用户令「提交」。本地提交 `e3fb35d` 后发现远端 develop 领先 9 笔(多 clone 并行):
  按 pitfalls/git/history-integration「单提交重放」纪律 `cp -a .git` 备份 → `git merge-tree` 只读判冲突(4 处:
  README / baseline.md / baseline-history.md / _doc-map) → `git merge` 手工解冲突(README 同句并集; baseline 我方
  条目按**合并树重测** 1636 collected 置顶、远端 1629 降上一态、旧 1617 条让位; history 并集后触 24,000 cap
  最老 1 条外迁 attachments; 生成物 kb.index 重建) → 合并树 test.full 两采样全绿(**1636 collected: 1635 passed
  + 1 skipped, TOTAL 92%** / 10993 语句 / 787 未覆盖; 金清单 62 条) → 合并提交 `8bacfae` → `ship.push` 推 Gitee
  成功(ls-remote 核对一致)。回写状态随本条; 真机走查仍待真实 qB。
- **2026-11-04 (缺失站点 tracker 合并扩展收口)** — 计划 `memory-bank/plans/26-11-03-2337-plan-missing-site-tracker-merge.html` 的 M1~M5 此前已完成（R1），本轮补齐最后一项 M4 验收：**GUI 冒烟三路径**。用 `scripts/ui_harness.py` + Playwright 真浏览器，在 `/api/sites/missing` API 边界注入三形态载荷：无缺失只出 toast；全单组走原两钮逐域名确认；多域名两组弹三钮框（拆分 `ghost`/合并 `primary`/默认焦点合并），合并填入 2 组共 4 域名，拆分二次确认后填入 4 站点；三路径零 `PUT /api/config`、零 console error。真实 groups 数据面已由 RM10/RM08 双附加轮覆盖；纯观感仍归用户目视清单。计划 doc-status 置 **Done**，计划内无剩余未完成项。
- **2026-11-04 (计划级 code review 与修复)** — 对计划 `26-11-03-2337` 全代码面（M1 exporter 分组构件 / M2 CLI `--split-trackers` / M3 `/api/sites/missing` groups）+ 收口回写做整计划评审。base 取任务起点 commit `62b5cbcf` 的 parent `1102e8b4`（`git show --parents` 核验；无上次收口 commit）。`review.pack` 分三面，派三个只读子代理串行（正确性 / 安全 / 测试缺口），交回 8 条发现全部经 `review.check` 引文校验通过。裁决 **blocker 0**：已修 ① groups 组名复用 sites 的 taken 导致 `_1` 后缀，与 CLI 同规则不符 → 改用独立 `taken_groups`；② 前端判重 `trackers[name]` 命中 `constructor`/`__proto__` 继承属性 → 两处改 `hasOwnProperty.call`；③ 补 CLI `--split-trackers` 透传/缺省两用例并修正原 `only_missing` 断言漏 `assert`；④ 补追加模式 + split 组合用例；⑤ 合并明细截断三件套加入接线守阵。入池：GUI 冒烟依赖一次性 harness 脚本 + gitignored 证据、无仓库内可复跑回归 → issue `26-11-04-2312-test-webui-sites-import-gui-smoke`。裁决不相关并保留痕迹：exporter 逐种 tracker 查询异常吞空集经 review base 旧实现复核属既有语义、本计划未引入，不修但入池 issue `26-11-04-2347-bug-missing-scan-partial-failure`。修复后定向用例与 test.quick 全绿；计划仍 Done。

- 2026-11-05 01:08 修复 issue 26-11-04-2347: collector 带失败计数+过半判据, WebUI 502/CLI TrackerScanBatchError 拒出空结果; 新测试 6 条; review 分面两面 blocker 0 修 4 入池 0; 基线 5211 passed(TOTAL 99%, 见 kb.baseline)
