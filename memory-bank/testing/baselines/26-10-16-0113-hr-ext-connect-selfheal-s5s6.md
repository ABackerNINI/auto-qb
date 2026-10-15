# 3403 —— HR 扩展「连接自愈」S5/S6(README 口径同步 + 七条守阵与跨层机械比对)

> 摘要: 计划 `26-10-15-2357` 的 S5/S6 落地 —— S5 把 `extensions/hr-fetch-proxy/README.md` 口径翻到「手动端点 = 优先」(发现只补齐手动没覆盖的端点, 绝不覆盖/删除手动), 布局块同步为 S4 的「① 连接后端」合并形态, 新增「连接自愈 + 不静默」段(徽标四态 / 失败即发现 + 2 分钟周期 / 逐候选结果), 排障表「自动发现未命中」行补逐候选结果 + 徽标, 「怎么确认它在工作」补徽标与顶部总览。S6 在 `tests/test_extension_proxy.py` 补 **5 条新守阵**: 合并语义两条(手动优先 / 发现集整批替换含空集例外 C1) + `未知` 字面量与 reason 中文映射 + `storage.onChanged` 监听连接面 + **跨层机械比对**(徽标态 `background.js::badgeStateOf` 与顶部总览态 `options.js::connStateOf` 切出函数体真跑同一张真值表逐输入一致 + 四态键集同源 + 徽标图例与 `BADGE.label` 同源)。改动面 = 1 个扩展文档 + 1 个测试文件, **零源文件行为改动**(S1–S4 的代码面本轮一行未动)。
> 档案: memory-bank/tasks/26-10-16-webui-hr-ext-connect-selfheal.md
> 基线时间: 2026-10-16 01:13

**Refs:** memory-bank/tasks/26-10-16-webui-hr-ext-connect-selfheal.md, memory-bank/plans/26-10-15-2357-plan-hr-ext-connect-selfheal.html

## TOTAL

```
TOTAL                                               17337    182   5846    158    99%
3403 passed, 4 skipped in 131.42s (0:02:11)
```

- 语句 17337 / 未覆盖 182; 分支 5846 / partial 158; 覆盖率 **99%**(`commands run test.full` 实测, Windows 侧)。
- 耗时两次采样 131.42s / 135.62s(区间 131–136s; 单次采样无意义, 口径见 `testing/baseline.md`)。
- 与上一基线 `26-10-16-0048`(3398 passed + 4 skipped)差 **+5 passed, 已对账**: 恰为本轮 S6 新增的 5 条扩展守阵(2 条合并语义 + 1 条 reason 泄露 + 1 条监听面 + 1 条跨层机械比对), 无其它来源。
- 语句/分支总数与上一基线**逐位相同**(17337/182/5846/158)—— 覆盖率只测 `src/` 包, 本轮改动全在扩展侧文档/测试, 源包一行未动。
- 守阵红绿双验(突变判红后还原复绿, 5 类): ① `options.js::connStateOf` 的 C4 分支(`answered === false`→`true`)→ 跨层用例 1 红 / ② 选项页引入 `未知` 字面量 → 1 红 / ③ 删一个 `DISCOVERY_REASON_TEXT` 映射键 → 1 红 / ④ `storage.onChanged` 监听面去掉 `instances` → 1 红(**首版用子串判据漏判** `changes.instancesX`, 改词边界 `\b` 后红验通过, 已写进用例注释) / ⑤ `discovery.js` 空集不替换分支删除 → 1 红。还原后 `test.one -- tests/test_extension_proxy.py` 36 passed。
- 包内脚本测试(commands run test.pkg): 本轮未触 `.commands/` 与 `.agents/skills/commands/`, 未跑。
- Linux(WSL)侧未重测 —— 纯文档 + 扩展 JS 静态/沙箱守阵, 无平台分支, 本条 Windows 侧数字为事实源。

## 本改动面

- `extensions/hr-fetch-proxy/README.md`: ① §2 布局块改为「① 连接后端(自动发现自愈; 手动指定优先)」单区(总览行 → 自动发现 → 实例列表「优先/自动」徽标 → 折叠的手动端点 → 自测/拉取), 手动端点口径由「兜底」翻「优先」并写明发现只**补齐**未覆盖端点; ② 新增「连接自愈 + 不静默(2026-10-16)」段(徽标四态 + 失败即发现/2 分钟周期 + 逐候选结果); ③ 排障表「自动发现未命中」行补逐候选结果 + 徽标, 「退手动配置」改「退手动指定」; ④ 「怎么确认它在工作」补徽标与顶部总览; ⑤ 连带修三处随 S4 失效的引用(「① 自动发现 + 保存」步骤改为隐式保存、「④区是运行日志」与「④⑤ 的数据源」按 S4 新编号/折叠区改正)。
- `tests/test_extension_proxy.py`: 新增 `test_merge_instances_manual_priority` / `test_merge_instances_discovered_set_replaced`(复用既有 discovery 纯函数 trace, 把 `_NODE_RUN_DISCOVERY_HELPERS` 抽成缓存 `discovery_helpers_trace()`) / `test_no_opaque_reason_leaks` / `test_options_listens_instances_changes` / `test_conn_state_judgement_matches_badge`(新 `_NODE_RUN_CROSS_LAYER_STATE`: 从两个文件切出函数体真跑真值表) + 三个静态切块小工具(`_balanced_block` / `_js_object_block` / `_js_object_keys`); 文件头「## 测试计划」新增 S6 小节。
- 滚动面: 任务档案子任务状态表与进度日志 · activeContext 切片 · 计划 `doc-status` Open→Done · 本基线切片。
