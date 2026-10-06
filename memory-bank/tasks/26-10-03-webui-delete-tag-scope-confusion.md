# 26-10-03-webui-delete-tag-scope-confusion — 全局/站点双设置作用域混淆分析与修复

**Status:** Done
**Added:** 2026-10-03
**Updated:** 2026-10-03
**Summary:** 认领 issue 26-10-01-2129(bug · 「删除类标签」全局/站点单设置语义混淆)。报告轮出根因报告 26-10-03-0504: 缺陷三层 —— config 层 `_strip_none`(validation/core.py)使 str/list 键「显式空=未定义」坍缩 / WebUI 层 bool 开关恒写值从不删键单向锁死(恢复入口 `cfgResetField` 死代码, 后端删键链路 writer.py 已在) / 回填显示用 schema 默认非合并生效的全局值; 受影响面 9 个全局/站点双层键。用户拍板方案 B 完整形态(D1)+「覆盖为空」是真实需求(D2)→ 直接 B, 并同时拍板走配置版本升级(存量显式置空移除 + 逐键 WARNING)。三阶段串行子智能体实施: `18bde39c` config 三态基座(Field.tri_state 4 站点 str 键 + v3→v4 迁移) → `42d3d90a` 显示层回退链回填 + 站点/全局来源徽标 → `9c6bc499` 「跟随全局」删键按钮 + str 覆盖为空/删键语义区分 + 9 键 help 三态文案。收尾实测 2325 passed + 3 skipped / 99%, 冒烟 118/118(三皮肤)。插曲: 另一 clone 档案标题后缀撞 test_memory_bank 行首锚阻塞提交通道, `1def00b7` 最小机械修复。

**Topics:** webui-delete-tag-scope-confusion

**Refs:** memory-bank/issues/26-10-01-2129-bug-webui-delete-tag-scope-confusion.html,memory-bank/reports/26-10-03-0504-report-webui-site-scope-confusion.html

## 原始请求

用户指派: 分析 issue 26-10-01-2129, 判断是否「config 层缺陷(config 层无法区分未定义与显式置空)+ WebUI 交互层缺陷(无删除配置/使用全局设置选项)」叠加所致, 并强调不限于「删除类似标签」—— 其它全局/站点双设置应都有此问题; 分析成熟解决方案、评估是否要填补 config 层缺陷, 出报告。工作方式约束: 主会话只委派不实施, 子智能体分阶段串行, 非代码任务不单独提交随本专题入库。后续轮次用户拍板按方案 B 完整形态实施(见进度日志实施轮)。

## 思考过程与决策

- **拆解为三阶段串行委派**(主会话只委派): 阶段1 代码事实取证 → 阶段2 成熟方案调研与选型 → 阶段3 报告撰写; 阶段间以 `tmp-analysis/phase{1,2}-*.md` 笔记交接(提交前已清理), 三阶段子智能体全部一次成功(0 次异常失败)。
- **一层假设修正为三层**: 用户假设的两层均属实, 但取证发现第三层独立缺陷 —— 回填显示 `boolValue()` 用 schema 默认 "false" 而非合并生效的全局值(config_editor.js), 全局 true + 站点未配置时开关显示 OFF 实际 ON, 这是用户感知「没分清」的直接来源。
- **config 层缺陷的定性是关键裁决点**: `_strip_none` 剥 None/`''` 是文档化设计取舍而非意外 bug; bool 键的 "false" 能穿过剥离, config 层对 bool 反而可区分 —— 「无法区分未定义与显式置空」只对 str/list 键成立。写回层 `_sync_mapping`(writer.py)对「树中缺键→磁盘删键」保真, 「未定义」信息只在载入合并期丢失。
- **报告轮的「是否填 config 层」结论 = 当前不填**: 反方论据(当时采纳) —— issue 只报「切不回全局」, 「覆盖为空」无真实诉求实证; 改 `_strip_none` 属设计决策且存量 `键: ''` 语义翻转需灰度迁移, 由本 bug 顺手带出违反范围守恒。正方论据(备用) —— 站点「本站不打标」config 层不可表达, bool 能显式 false 而 str 不能显式空的覆盖语义不对称是长期认知税。B 方案挂三个触发条件待命(出现覆盖为空真实场景 / 回退链键增长致同类 bug 复发 / 需对比审计视图), 升级路径平滑(C 的 UI 部分是 B 的子集)。**该结论随后被 D2 拍板推翻** —— 用户确认「覆盖为空」是真实需求, 触发条件命中, 直接走 B。
- **业界调研锚点**: 「恢复继承」的业界动词就是删键(git `--unset` / VS Code Reset Setting / dconf reset; dconf 与 qB 分类路径已联网核实, 其余常识级), 本项目后端删键链路已在, 修复纯前端接线; 显示失真靠前端用整棵树自算「站点→全局→默认」合并链 + 来源徽标解决。
- **主键修正**: 报告初版 doc-topic 误用 `webui-site-scope-confusion`, 提交前修正为 issue 既有主键 `webui-delete-tag-scope-confusion`(跨形态串联主键单点), 三方认领链(issue doc-refs ↔ 报告 doc-refs ↔ 本档案 Refs)双向互记。
- **结论落在报告, 不落在本档案**: 报告是快照(report 恒 Done, 出厂即冻结), 本档案只记执行过程与待拍板事项; 拍板后不回头改报告。
- **拍板后直接实施未另出 plan**: 2026-10-03 用户一次性拍板 D1(方案 B 完整形态)/ D2(「覆盖为空」是真实需求 → 直接 B)/ 配置版本升级(存量显式置空移除 + 逐键 WARNING)后, 主会话**未再走 plan 工位出计划文档**, 直接拆三阶段(config 层 / 显示层 / 交互层)串行子智能体实施, 各阶段独立提交推送 —— **实施链以三提交(`18bde39c` → `42d3d90a` → `9c6bc499`)为准**, 本档案只作过程与决策记录; 报告 26-10-03-0504 保持出厂冻结未改。

## 实现计划

拍板前无实施计划 —— 报告轮是根因分析, 零代码变更(范围守恒)。2026-10-03 用户拍板方案 B 完整形态后未另出 plan 文档, 由主会话拆三阶段直接实施, 实施链以三提交为准(阶段1 `18bde39c` config 层 → 阶段2 `42d3d90a` 显示层 → 阶段3 `9c6bc499` 交互层), 本档案为过程记录。

## 子任务状态表

| 段 | 内容 | 状态 |
|----|------|------|
| 阶段0 | 会话协议(sync 8cb2da59) + 定位 issue/规范 | 完成(26-10-03) |
| 阶段1 | 代码事实取证(config/WebUI 两层 + 9 键全量盘点 + state.json 不受影响确认) | 完成(26-10-03) |
| 阶段2 | 成熟方案调研(dconf/qB/git/VS Code 等) + 三方案选型 | 完成(26-10-03) |
| 阶段3 | 报告撰写(reports/26-10-03-0504, 单文件 HTML dark, meta 协议) | 完成(26-10-03) |
| 分析收尾 | 主键修正 + 三方认领链 + 立档 + 索引重建 + 提交 | 完成(26-10-03) |
| 拍板 | D1=方案 B 完整形态 / D2=「覆盖为空」是真实需求 → 直接 B / 附带拍板配置版本升级(存量 '' 移除 + WARNING) | 完成(26-10-03 用户拍板) |
| 阶段1 实施 | config 三态基座: Field.tri_state + 4 站点 str 键 + `_strip_none` 站点段豁免 + v3→v4 迁移清存量 '' 逐键 WARNING(`18bde39c`, 2325+3/99%) | 完成(26-10-03) |
| 阶段2 实施 | 显示层: SITE_FALLBACK_GLOBAL 7 键回退链生效值回填 + 站点/全局来源徽标 + cfgIsDefault 抑制(`42d3d90a`, 冒烟 55/55) | 完成(26-10-03) |
| 阶段3 实施 | 交互层: 「跟随全局」删键按钮(confirm danger + toast) + str「清空=覆盖为空」/「删键」两动作区分 + 9 键 help 三态文案 + 内联开关 tooltip 修复(`9c6bc499`, 冒烟 118/118) | 完成(26-10-03) |
| 闸门插曲 | 另一 clone 档案「实现计划」标题带后缀撞 test_memory_bank 行首锚, 阻塞 ship 通道; 最小机械修复单独一笔(`1def00b7`) | 完成(26-10-03) |
| 阶段4 收尾 | test.full 复跑 2325+3/99% + 冒烟复跑 118/118 + 基线切片 + progress 迁出 + issue 置 Done + tmp-analysis 去跟踪 + 坑档回写; 回写件留工作树待用户提交 | 完成(26-10-03) |

## 进度日志

- **2026-10-03 (报告轮)**: 报告轮完成 —— 三个子智能体串行执行全部一次成功; 产出报告 26-10-03-0504(42.8KB, dark 主题, 18 项结构自检全过) + 三方认领链 + 本档案; `kb.index` 重建 16 索引; 全程零代码改动, 无 test.full 基线(无代码变更, 沿用最近基线)。停在 D1/D2 拍板。
- **2026-10-03 (实施轮)**: 用户拍板 D1=方案 B 完整形态 / D2=「覆盖为空」是真实需求 → 直接 B, 并同时拍板走配置版本升级(存量显式置空移除 + 逐键 WARNING)。未另出 plan, 三阶段串行子智能体直接实施, 各自单独提交推送: 阶段1 `18bde39c`(config 层: Field.tri_state + hr.add_tag / add_category / add_tag_for_satisfied / add_category_for_satisfied 4 键标 tri_state + `_strip_none` 站点段豁免保 '' + validate 放行 + v3→v4 迁移经 infra.versioning 的 migrate_with_notes 汇聚逐键 WARNING + ruamel round-trip 保 '' 实测无损 + keys.md/docs/configuration.md 回写; 实测 2325 passed + 3 skipped / 99.00%) → 阶段2 `42d3d90a`(config_editor.js: SITE_FALLBACK_GLOBAL 7 键回退链表 + cfgSiteFallbackPath/cfgFallbackValue + siteBadge/sitePlaceholder + cfgInputValue 按存在性判定(站点 '' 原样显示) + xtpl.html 来源徽标 + cfgIsDefault 链上键抑制「默认」徽标; 冒烟 55/55 三皮肤) → 阶段3 `9c6bc499`(「跟随全局」按钮接线死代码 cfgResetField/cfgDelPath(confirm danger + toast) + str「清空保存=覆盖为空」与「跟随全局=删键」两动作区分 + 9 键 help 三态文案(schema/trackers.py) + 内联开关 tooltip risk+help 并接修复; 冒烟 118/118 三皮肤)。插曲: ship 通道被另一 clone 档案标题后缀撞 test_memory_bank 行首锚阻塞, 最小机械修复(标题复位纯行首)单独一笔 `1def00b7`。
- **2026-10-03 (收尾轮)**: 阶段4 收尾回写 —— test.full 复跑 **2325 passed + 3 skipped / 99%**(13,433 语句 / 88 未覆盖 / 4,542 分支 / 89 partial, 30.17s, rc=0, 与 0733 基线持平)+ 冒烟复跑 **118/118**(三皮肤; 先核对阶段 3 遗留桩进程归属本 clone 后杀掉重起再跑); 新建基线切片 26-10-03-0913; progress 迁出 implemented-webui.md; issue 26-10-01-2129 置 Done(修复落点三提交); tmp-analysis 误提交件去跟踪(`git rm --cached` phase2_smoke.cjs / report-extract.txt + .gitignore 追加 `tmp-analysis/`); 坑档回写(subagent-mixed-workspace 复发+1 / tasks-archive 补行首锚条)。**全程未 commit 未 push —— 全部回写件留工作树, 等用户提交指令统一入库。**
