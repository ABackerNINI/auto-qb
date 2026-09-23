# 26-09-20-webui-column-prefs-reset — WebUI 列设置（顺序/显隐/宽度）被多标签页整份覆盖

**Status:** Done (2026-09-20 实施 → 09-21 双轨重设计 → **09-24 补齐真因**: 浏览器站点级"关闭窗口时清除 Cookie 和站点数据", 与应用无关; 剩用户真机走查)
**Started:** 2026-09-20
**Owner:** 主线 (单会话)
**Plan doc:** `memory-bank/plans/26-09-20-1836-webui-column-prefs-sync-plan.html`
**Issue:** `memory-bank/issues/26-09-20-1800-bug-webui-column-prefs-reset.html`
**Legacy-ID:** 无
**Summary:** 真浏览器复现并定位：列偏好丢失**不是**存储没写进去、也不是读入被洗净，而是每个标签各持一份"加载时的快照"，`saveColState()` 又写整份 ⇒ last-writer-wins，先改的标签被静默吞掉。修法 F1 写入改 read-modify-write + F2 监听 `storage` 事件跨标签同步 + F3 visibilitychange 补漏；后端零改动，不升 `COLS_STORE_KEY`。09-24 补齐真因: 浏览器站点级「关闭窗口时清除 Cookie 和站点数据」(cookie 例外 `setting=4`/SESSION_ONLY)会连 localStorage 一起清 —— 与应用无关。
**Topics:** webui-column-prefs

## 原始请求

> 记录BUG: column设置经常被重置, 比如栏的顺序, 显示, 宽度等

随后用户下「认领」，并确认触发场景 = **同时开多个标签页**（单标签刷新/重开没事；固定地址打开）。

## 思考过程与决策

- **先复现再定位，不要靠读代码猜**：入池时列的 4 条假设（写失败 / 读入被洗净 / 自适应覆盖 / v3→v4 迁移）**全部排除** —— 单标签六条路径（刷新 / 切视图 / 缩放 / 轮询 6s / 展开 / 二次刷新）全保持，新标签也能读到最新存储，说明读写链路是好的。真正的变量是"第二个标签"。
- **复现脚本走真实手势**（拖 resizer / 拖表头 / 点列选择器），不是直接改内存 —— 直接调方法会绕过"用户到底能不能触发"这一层。
- **决策 1（为什么 F1 单独不够）**：用户在两个标签里调的通常**就是同一个表**（辅种页 group）。按 page 粒度合并只在"改的是不同表"时有效，同表冲突仍然后写赢 ⇒ 必须让标签的内存态保持新鲜（F2 事件同步）。
- **决策 2（采用存储整份，不做逐项合并）**：`storage` 事件到达时整体采用存储值 + `$nextTick(materializeColumns)`。逐项/逐列合并需要"谁更新"的时间戳语义，代价远大于收益；整份采用与"刷新一次"等价，语义可预测。
- **决策 3（不升 `COLS_STORE_KEY`）**：升版本 = 清空用户偏好（pitfalls R10-09 的反转结论）。本次不动存储结构，只改读写时机。
- **决策 4（不做服务端化）**：用户已明确"只存浏览器"。
- **教训（可复用）**：**"设置/偏好被重置"类缺陷，先问"几个标签页 / 几个窗口"** —— 前端把存储读进内存当快照 + 整份写回，是多标签场景下的默认失效模式；单标签复现不出来时，别急着怀疑存储本身。

## 实现计划

1. F1: `columns.js::saveColState(page)` 改 read-modify-write（读回存储 → 只覆盖本 page 四段 → 写回），6 处调用点传 page
2. F2: `app.js::mounted` 注册 `storage` 事件监听 → `adoptColState()`（重读 + 洗净 + 整份替换 + nextTick materialize）
3. F3: 已有 `visibilitychange` 的可见分支加一次 adopt
4. F4: `scripts/ui_smoke.cjs` 加双标签冒烟项；F5 可选静态守阵
5. 验证：单标签六路径回归 + 双标签验收 + `uv run pytest tests -q`；issue 置 Fixed 并重建索引

## 子任务状态表

| # | 子任务 | 状态 | 产出 |
|---|---|---|---|
| 1 | 复现（真浏览器 + 桩服务） | ✅ | `col_repro.cjs` / `col_repro2.cjs`，多标签覆盖已复现 |
| 2 | 根因定位 + 排除 4 条原假设 | ✅ | issue 报告 05 节改写 |
| 3 | 计划文档 + 立档 | ✅ | 本档案 + `memory-bank/plans/26-09-20-1836-...html` |
| 4 | F1/F2/F3 实施 | ✅ | `shared/columns.js`(saveColState 改 read-modify-write + 新增 adoptColState) + `shared/app.js`(storage 监听 / visibilitychange 补漏 / unmounted 摘除) |
| 5 | 冒烟 + 单测 | ✅ | 新增「列设置多标签页互不覆盖」; ok 模式 56 项 0 失败 / error 模式 56 项 0 失败; `pytest` 1062 passed |
| 6 | 红验(守阵灵敏度) | ✅ | 摘掉第二个标签的 storage 监听 ⇒ 缺陷如期复现(`["total_size"]`) |
| 7 | 真机走查 | ⏳ | 需真实 qB: 两个标签各改一次列, 互相刷新确认都不丢。**09-24 追加前提**: 先确认浏览器没有站点级"关闭窗口时清除 Cookie 和站点数据"例外, 否则任何走查都会被它在关浏览器时清空(见 pitfalls/web-ui/columns-persist.md) |

## 进度日志

- **18:00** 用户报"column 设置经常被重置" ⇒ 入池 `26-09-20-1800-bug-webui-column-prefs-reset`（bug / standard / Open）。
- **18:1x** 单标签复现脚本：六条路径全部保持，**未复现**。
- **18:2x** 双标签复现脚本：**复现** —— A 隐藏「总大小」被 B 隐藏「分类」整份覆盖。向用户确认场景，答"同时开多个标签页 / 刷新重开没事 / 固定地址"。
- **18:33** 用户「认领」⇒ issue 置 `In Progress`（meta + 封面徽标两处）+ 报告补复验与根因 + 重建 issues 索引。
- **18:36** 出计划文档 + 立本档案。
- **18:4x** 实施 F1/F2/F3：`saveColState(page)` 改 read-modify-write（6 处调用点传 page）、新增
  `adoptColState()`、`app.js` mounted 注册 `storage` 监听 + unmounted 摘除 + visibilitychange 补漏。
- **18:5x** 验证：双标签复现脚本由 ✗ 转 ✓（`["uploaded","total_size","category"]` 三个改动都在）；
  单标签六路径无回归；ok 模式双 UI **56 项 0 失败**、error 模式 **56 项 0 失败**；
  **红验**（摘掉标签 2 的 storage 监听）⇒ 缺陷如期复现 ⇒ 守阵钉得住；`pytest` **1062 passed**（未退化）。
  知识库回写：`pitfalls.md`（R10-09 条目加 ③ 多标签整份覆盖 + 判别法）、`modules.md`（列偏好写侧两约束）、
  `testing.md`（冒烟 54→56）。issue 置 `Fixed` 并重建索引。**未提交**（用户未下触发词）。
- **09-21 12:48** 用户反馈仍复现 ⇒ 失败分析(`memory-bank/reports/26-09-21-1248-column-prefs-fix-failure-analysis.html`)实测:
  显隐/列序已稳, 宽度另有通道(非手动页自适应 px 落盘/跨窗口互写)→ 二次修复入库 `6c1b7f4`;
  "隐藏列宽被抹"与结构脆弱性仍敞着。
- **09-21 15:51** 用户定性"修复了很多次, 急需重新设计, 简化模型, 从根本上杜绝" ⇒ 双轨模型重设计计划
  `memory-bank/plans/26-09-21-1551-column-prefs-intent-redesign-plan.html`(意图/生效分轨 + v5 按页子树 +
  单一持久化漏斗), 待拍板 D1/D2/D3。
- **09-21 16:09** 用户"按推荐实施"(D1 升 v5+迁移 / D2 fit=回全自动 / D3 origin 空存储提示) ⇒
  W1 数据层(`app.js`: v5 键链 + `migrateLegacyToV5` 内存迁移 + 意图态 colHidden/colOrder/colW + origin 提示挂点)
  与 W2 交互层(`columns.js`: 唯一漏斗 `persistPage` + `recomputeEffective` + 六意图动作以 merge 保隐藏列宽
  + manual 标志删除)完成; W3 守阵 1 换 4(红验 4/4)+ 冒烟新增 4 场景; W4 提示已做(运行时注入 DOM, 模板零改动)。
- **09-21 22:4x** 验证收口: 全量 `uv run pytest tests -q` **1142 passed**(39.88s, Windows); 冒烟双 UI
  **64 项失败 2 项**(均为既有「P0-3 乐观态落回真值」, 与列偏好无关), 新 4 场景(异视口互不吞+F3 /
  全自动页不落px / 隐藏列保宽 / v4→v5 迁移)双 UI 全 PASS。知识库回写: pitfalls(双轨铁律 + 指纹不可达)/
  modules(列偏好持久化改写)/issue 状态日志。**未提交**(待用户触发词)。
- **09-24 04:0x** 用户把"浏览器重启后localStorage重置"写进 `想法.md` KNOWN BUGS 并要求修复 ⇒ **真因不在应用**:
  逐条核对(全仓无 `localStorage.clear()` / 唯一写入口 `persistPage` 只在用户操作时调 / 启动路径只读不写)
  后转去翻浏览器配置, 取证到 **Edge 与 Chrome 的 `Default/Preferences` 里各有一条**
  `content_settings.exceptions.cookies` = `127.0.0.1,*` `setting=4`(= `SESSION_ONLY`, 界面文案
  "关闭窗口时清除 Cookie 和站点数据"; Edge 设于 2023-12-11, Chrome 设于 2018) ⇒ 关浏览器时该 **host
  全部端口**的 Cookie 与 localStorage 一起被清, 于是 `127.0.0.1:38080`(auto-qb) 与 `:38081`(long-seeding)
  的偏好**一起**消失 —— 与"应用每次重置设置"完全同形, 也是前四轮修复从未覆盖的通道(会话内刷新正常、
  其它网站正常、全局 `clear_browsing_data_on_shutdown` 未开, 三条现象都与它自洽)。
  **处置**: ①删掉 Edge 那条例外(改前备份 `Preferences.bak-autoqb-20260924`; 实测 `protection.macs` 与
  `Secure Preferences` 都不含 `content_settings` ⇒ **无 MAC 保护**, 可直接改) —— **Chrome 那条待用户退出
  Chrome 后处理**; ②`columns.js::_showColsOriginHint` 文案改为"事实 + 两条成因 + 自查路径", 并补
  `sessionStorage` 会话级去重(清站点数据环境下 localStorage 里的去重标记也会一起没, 否则每次开浏览器都弹);
  ③新增守阵 `test_frontend_cols_empty_hint_names_browser_clear_cause`; ④知识库回写:
  `pitfalls/web-ui/columns-persist.md` 新增 ❗ 条("两种重置"改"三种")+ `想法.md` 该条补结论 +
  `testing/baseline.md` **1203 collected**。实测: 全量 **1202 passed + 1 skipped**(原 1201+1, 未退化),
  真浏览器(本 clone 桩服务 8200)验证提示条渲染与文案逐字一致。
