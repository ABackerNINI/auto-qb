# 6266 —— 行窗口化 pad 等高替换修复批全量基线(issue 26-11-15-0332)

> 摘要: 行窗口化 pad 等高替换修复批全量基线(issue 26-11-15-0332)
> 基线时间: 2026-11-16 03:53

## 验收数字

`commands run test.full` 实测(2026-11-16 04:22, Windows; 机器上有常驻服务在跑, 故 3m38s):

```
TOTAL                                                27855     73   9822     79    99%
Required test coverage of 99.5% reached. Total coverage: 99.59%
6266 passed, 2 skipped in 217.66s (0:03:37)
```

e2e 侧(本批对象): `e2e/drawer-dock-stability.spec.mjs` + `row-window-zoom` + `window-invalidation` + `kbd-scroll-band` 四 spec 串行 **47 passed / 10 skipped**(2.5m, 0 failed); 像素三例 T7 顶界带 / S-A 首开遮挡 / S-C 越过带 单跑 **7 passed / 2 skipped**(flux 专属两条在 prism/atlas 上 skip)。

红验(撤产品修复、保留去预热的判据): T7 前置带 `行顶-列头底 = 5.8125 > 4` 红; S-A 公式落点 `-11 > -14` 红(偏差 5px); node 电池把重探调用停掉后 **11/22 过、8 项红**(绿验四条全红: 陈旧键没被顶掉 / padTop 仍按 69.609 超量累加 / 修复前后差不成立 / `_rowPre` 仍是陈旧前缀和, 另加首拍量遍、三入口同拍去重等), 静态守阵同红(调用点位置断言)。绿验: 全部通过。

## 评审轮(2026-11-16, code-review skill)

评审包 544 行 / 8 文件, 基 `832e8595`, 基哈希 `e2579aafc0a9`, 安全敏感面「无」, 红线预警「无」。只读评审子代理返回 7 条(major 1 / minor 5 / nit 1), 引文 7/7 机检通过(`review.check`), 全部处置:

| # | 严重度 | 发现 | 处置 |
|---|---|---|---|
| 1 | major | `ROW_H_MAIN_PROBES` 的 group 探测位裸写 `.group-row:not(.torrent-row)[data-key]`, 剧集页的 `.show-row` / `.ep-row` 也带 `data-key`, 会把别座表的行记成 group 行高并污染 `_rowHAvgOf("group")`(冻结基准的来源) | **修**: 三 kind 一律带 `[data-table="torrent"/"group"/"detail"]` 收窄(逐模板核对: 三座表的行容器都带 data-table; 不带的两处 —— 抽屉桥行只有 `data-dt-key`、`.unrecognized-row` 没有 `data-hash` —— 本来就不落进探测位)。守阵加「裸选择器不得回潮」断言 |
| 2 | minor | 冻结只在 `n|首行键|末行键` 变时重校, 注释里的「数据刷新」是过度承诺(刷新同一批行、只改行高时签名不变) | **修(注释)**: 改成如实描述 + 显式写明边界取舍(逐行实测照常收敛, 只有从未渲染过的行仍按旧基准估高; 为了不把滚动中的 pad 搬走, 行集不变时基准宁可不重算) |
| 3 | minor | 重探会写入 `h = 0`(视图被 v-show 收走/容器换掉那一瞬), 把真值抹成 0, 同一拍 padTop 少一整行 | **修**: `if (!(h > 0)) continue;`, 与 `_measureRowH` 的 `_rowH[kind] > 0` 兜底同口径 |
| 4 | minor | 去重签名在探针解析前就落盘, 空探(抽屉换座/整表被 content-visibility 跳过)会烧掉该几何, 后续同几何不再重探 | **修**: 改为「真的量到行(`probed > 0`)之后」才落盘, 空探下一拍自然重试 |
| 5 | minor | 静态守阵断言整行源码字符串, 对无害重构过敏 | **部分修**: 关键两条改成容错正则(`old === undefined` 后接 continue/return、`cache[kind] === sig` 后接 return), 结构性黑名单(禁 `delete`/`_rowHVer++`/`_winMeasured`/`_rowHSig`/`viewMode`/`_winResize++`)与选择器单点断言保留 —— 那几条钉的是「不踩全表作废坑」这个不可退让的约束 |
| 6 | minor | e2e 把两侧都取整再按 ≤1 判, 等于把容差放宽到 ~1.5px | **修(更好的方向)**: 弃用取整比较, 采样器加分数精度 `rowBf`/`rowTf`, 判据回到 gBR 原值。实测真相: prism 基线 482.0625 → 落定 481.0625, **真实位移恰 1.0px**(选中行开抽屉自身箱变, 修复前 HEAD 上同样存在), 原先的 1.0625 全是 `round(481.0625) - 482.0625` 造出来的量化偏置; atlas/flux 位移 0。分数比较下 1px 恰读 1、2px 回潮读 2 |
| 7 | nit | 电池里「陈旧-真值 = +3.828px」是两个字面量的纯算术, 任何产品改动都撞不红 | **修**: 删掉该检查(22 检查; 收口轮减 3 项 → 18, 复评轮补 1 项 → 19, 见下两节), 3.828 的语义仍由「修复前后 padTop 差恰 = 陈旧-真值」这条行为断言承担 |

零 blocker。修完重跑: 全量 6266 passed / 2 skipped; e2e 四 spec 47 passed / 10 skipped / 0 failed; 像素三例 7 passed / 2 skipped; `ship.gate` 全绿(9 条命中 / 17 条命令 / 117.6s)。

## 收口轮(2026-11-16, 自审)

评审修完后又过了一遍自己新加的东西, 揪出一条**设计缺陷**, 处置是整块删除而非补丁:

1. **「换行集重校」根本做不到**(致命于该机制本身): `_rowHAvgOf` 汇总 `_rowHs` 的**全部**键, 而键只在「列集合 / 窗宽签名变」时才按 kind 剪枝。于是行集签名变了、重算出的均值仍是被上一批 population 稀释的混合值 —— 那不是重校, 是假重校; 真重校必须先按 kind 剔掉旧批键, 而这对 `member` 是灾难(成员列表是逐组子集, 换一次组剔一次 = 每次展开都重新实测全部成员行)。权衡后**删除整个机制**: 冻结门回到两支(`!_winMeasured[kind]` 首校 / `!(this._rowH[kind] > 0)` 存值非正兜底), `_rowHFrozen` / `_rowHListSig` 两个缓存从 `created()` 一并撤掉, 边界(冻结后不随行集/数据刷新重算)写进代码注释「已知边界(刻意不做)」与坑档, 守阵加断言**这两个缓存不许回潮**。理由: 估偏只影响「从未渲染过的行」的占位与滚动条长度, 而基准一动, 滚动中的内容就整段跳 —— 后者正是本 issue 要修的病。
2. **陈旧 docstring**(nit): `_rowHAvgOf` 头部还写着「估算偏差单调收敛」, 与新冻结直接矛盾。改为如实描述: 本函数只负责算, 冻结与否由调用方定, 三个主 kind 首校后即冻结(所以「缓慢收敛」在主表上不成立), 抽屉内容桥不冻结。
3. **守阵断言过宽**(nit): `old === undefined` 后的分支从 `(continue|return)` 收窄到 `continue` —— `return` 会让重探在首行未量时整体退出, 那不是「跳过新增键」而是「放弃这一拍」。
4. 电池随之 **22 → 18 项**(撤掉三条重校检查), 项数断言同步改 18; 每次减项都由项数断言当场抓出, 无静默变弱。

收口后重跑: 静态守阵 + 电池 **50 passed**(4.3s); 全量 **6266 passed / 2 skipped / 99.59%**(3m44s); e2e 四 spec **47 passed / 10 skipped / 0 failed**(38+9); `ship.gate` 全绿。

## 复评轮(2026-11-16, code-review skill 第 2 轮)

收口改动后重打评审包(基 `832e8595`, 518 行, 基哈希 `2f18bd0ee24a`), 复评返回 10 条(0 blocker / 0 major / 4 minor / 6 nit), 引文 **10/10** 机检通过, 全部采信并处置:

| # | 严重度 | 发现 | 处置 |
|---|---|---|---|
| 1 | minor | 电池文档声称冻结门两支都被行为断言钉住, 但那一项同时翻了 `_winMeasured`, 只压到第一支; 变异「删掉 `\|\| !(this._rowH[kind] > 0)`」后电池仍 19/19 全绿 | **修**: 新增第 19 项单独隔离(保持已量齐、只把基准置 0), 断言重校后 `> 0`。变异复验: 18/19, 恰该条红 |
| 2 | minor | `probed++` 在 `h>0` 检查**之前**, 全零探也算「量到」→ 去重签名被空探烧掉, 与「空探不记账」直接矛盾 | **修**: 计数移到有效性检查之后(它记的是「真量到几行」) |
| 3 | minor | 守阵只断言「调用在 `const hs` 之前」, 「所有早退之后」没钉; 变异「调用挪到函数开头」两层全绿 | **修**: 取 `pre[]` 之前最后一个 `return off;` 作早退界, 断言调用在其后。变异复验: 守阵当场红。注意不能 `rfind` 全函数 —— start/end 归一化之后还有一条合法 `if (start >= end) return off;` |
| 4 | minor | active-context 新档写的是已删机制(「按行集签名重校」)与 23 检查 | **修**: 改写为最终态并补 R1~R3 活动行 |
| 5 | nit | `>0` 分支的理由写「v-show 收走时行仍在 DOM」, 但三个主视图是 `v-if`, 切页时行被摘掉, 走的是 `rows.length===0` 早退 —— 该支当前是安全网而非热路径 | **修(注释)**: 改为「安全网」并列出真实可触发情形(祖先 display:none / 行刚插入未布局 / 将来改 v-show), 同时写明「别因为现在走不到就删」 |
| 6 | nit | 「随逐行实测单调收敛」不成立: 真值比基准高时换真值反而让总偏变大 | **修(注释)**: 改为「单调递减的是未量行数, 不是估偏」 |
| 7 | nit | 探测位注释说「抽屉桥行只有 data-dt-key」—— 事实错误, 桥行也带 `:data-table="dtBridgeTbl(tab)"`(xtpl.html:373), 只是取值恒为 peers/trackers/content 且无 data-hash/data-key | **修(注释)**: 改为三重条件都不满足才不落进探测位, 并提醒「别以为 data-table 一条就够」 |
| 8 | nit | e2e 采样器注释写反: `rowBf`/`rowTf` 标成「诊断用」, 实际是 S-C/T7 的唯一判据源 | **修**: 注释对调 |
| 9 | nit | 分数判据容差 `<= 1` 零余量(已知良性箱变恰 1px), 任一 1/64 抖动即假红 | **修**: 三处改 `1.5` —— 2px 级回潮仍判红, 本 issue 回潮量 3.8~5px |
| 10 | nit | issue §02 行号在本批注释插入后全部偏移 | **修**: 复校为 425 / 629 / 598 / 726 |

零 blocker。复评后重跑: 静态守阵 + 电池 **50 passed**; 全量 **6266 passed / 2 skipped / 99.59%**; e2e 四 spec **47 passed / 10 skipped / 0 failed**; `ship.gate` 全绿(9 条命中 / 17 条命令)。

## 分面复评轮(2026-11-16, 提交前 · 并行 2 路)

批次已 >400 行, 提交闸门要求 `· 派发 ≥2`(首轮拓扑派遣)。按评审包自带的「分面」分档并行派两路:
**正确性面**(冻结语义 / 探针顺序 / 与 `_measureRowH` 的交错 / 探测位作用域 / 抽屉分支)与
**测试缺口 + 安全面**(变异抗性 / 注释可满足性 / e2e 容差余量 / 选择器注入)。返回 4 条
(0 blocker / 2 major / 2 minor), 引文 4/4 机检通过。

| # | 严重度 | 发现 | 处置 |
|---|---|---|---|
| 1 | minor | 冻结基准是**视觉 px** 量值, 而重校签名只看布局宽度代与可见列数 —— 运行时改 root zoom 不翻 `_winMeasured`, 基准按旧缩放估高(偏大 ~11%), 修复前靠逐拍重算自愈、冻结后不自愈 | **入池** `26-11-16-0716-bug-webui-rowwin-frozen-est-zoom-drift`(Open): 影响面仅 pad 总高/滚动条长度, 不搬内容; 两条修法都要动 `_winZoomOf` 换算面, 不在本批末尾改。代码补「已知边界」注释指向该 issue |
| 2 | major | 「空探不记账」只靠代码正确性: 变异「`probed++` 挪到 `h>0` 检查之前」与「在 `cache[kind] === sig` 后立刻落盘」都能让守阵 + 电池全绿(实测) —— 该几何永久不再重探, 正是本 issue 要修的病 | **修**: 电池加「行在场但 gBR 全报 0」两拍用例(签名不落盘 + 下一拍照常重探且不写 0)。两条变异复验: **20/22, 恰这两条红** |
| 3 | major | 两条抽屉用例都把 `_rowHProbeRows` 换成桩, 抽屉分支本体(锚收窄 / `segs` 跳过 / `dtBridgeTbl` 门 / `data-dt-key` 键)一行都没被执行 —— 退回裸扫 `.group-row[data-dt-key]` 三层全绿 | **修**: 电池改用**真** `_rowHProbeRows`, 造三座锚(content / peers / segs)各一桥行, 裸扫结果集照实返回三个。变异「退回裸扫」复验: **21/22, 恰该条红** |
| 4 | minor | 守阵第 1/5 段断言跑在**原文**上, 注释可满足: 把调用整段包进 `/* */` 或把门写成 `if (false) {` 再把旧条件留注释里, 全绿(实测) | **修**: 新增 `_strip_js_comments`(只剥 `/* */` 与整行 `//`, 不剥行内 `//` 以免截断字符串), 全段断言改跑剥后文本。变异「调用包进注释」复验: 当场红 |

零 blocker。修完重跑: 静态守阵 + 电池 **50 passed**(电池 22 项); 全量 **6266 passed / 2 skipped / 99.59%**; e2e `drawer-dock-stability` **38 passed / 4 skipped**; `ship.gate` 全绿。

## 本改动面

- `src/auto_qb/webui/static/shared/columns_grid.js`(+130/−7):
  - 新增 `ROW_H_MAIN_PROBES` 单点(主表三 kind 探测位, `_measureRowH` 与重探共用; 原来选择器写死在 `_measureRowH` 内)。三 kind 各自带 `[data-table="torrent"/"group"/"detail"]` 收窄 —— 剧集页 `.show-row`/`.ep-row` 也带 `data-key`, 裸 `.group-row:not(.torrent-row)` 会把别座表的行记成 group 行高并污染冻结基准的来源均值(评审 #1)。
  - 新增 `_rowHProbeRows(kind)`(解析「此刻还在 DOM 里」的该 kind 行; 抽屉桥按在场变体锚现拼, 不裸扫 `.group-row[data-dt-key]`)与 `_reprobeRenderedRowH(kind, sig)`(出窗最后一探: 只刷已有键、`h<=0` 不采信、同拍 sig 去重且只在真量到行后落盘、抽屉 `content-visibility:auto` 守卫、零全表作废)。
  - `_rowWindow` 一处: 早退之后 / `pre[]` 之前调 `_reprobeRenderedRowH`; 其余不变。
  - `_measureRowH` 主表分支: 占位基准从「每拍跟随均值」改为「首校即冻结」, 门恰两支 —— `!_winMeasured[kind]`(首访量齐)与 `!(this._rowH[kind] > 0)`(存值非正 = 还没校准, 兜住 v-show 收走时 gBR 全报 0 把均值校成 0 的情形, 否则切回来 est 恒回落成 `ROW_WIN_EST_H` 常量)。冻结后新量行只把自己那一项从估算换成真值, 不再连坐搬整段 pad。抽屉内容桥分支不动(仍需逐拍收敛 28→27)。
  - `_rowHAvgOf` 头部注释改写(收口 #2): 不再承诺「估算偏差单调收敛」, 改为「本函数只负责算, 冻结与否由调用方定」+ 抽屉例外。
- `src/auto_qb/webui/static/shared/lifecycle.js`(+4): 根 `created()` 初始化 `_rowProbeSig` 一个非响应式纯缓存(进 data 会每拍多触发一轮整表重渲)。
- `tests/test_webui_static_dom_page_layout.py`(+137): 新增 `test_frontend_outgoing_rowh_reprobe_guard`(调用点位置 / 只刷已有键且必须是 `continue` / 零全表作废黑名单 / 同拍去重且空探不记账 / `h<=0` 跳过 / 抽屉守卫 / 探测位单点且 group 必须带 data-table / 冻结门恰两支 + 已删缓存不许回潮 / 抽屉不冻 / created 初始化)+ 测试计划 docstring 一条。
- `tests/test_webui_static_r4_node_batteries.py`(+236): 新增 node 电池 `test_r4_outgoing_rowh_reprobe_kills_pad_jump`(22 检查, 含项数断言防静默变弱; 红验复现 padTop 按 69.609 超量替换, 绿验真值 65.781 落地且前后差恰 +3.828px; 另钉零全表作废 / 三入口同拍去重 / 几何变了才重探 / rowWin 关闭零重探 / 抽屉未渲染行跳过 / 冻结门两支 / 抽屉不冻)+ docstring。
- `e2e/drawer-dock-stability.spec.mjs`(+36/−34): 删 `preheatRowWindow()` 预热辅助与两处调用(T7 对齐前 / S-A 让位前), 换成「刻意不预热」说明 —— 判据变回真回归探测器; 采样器加分数精度 `rowBf`/`rowTf`, S-C/T7 的位移判据改用分数值比分数基线(原先「取整帧 vs 分数基线」最多带 0.5px 量化偏置, 会把 1px 的选中行箱变读成 1.0625 假红 —— 实测真相是恰 1.0px, 且该箱变在修复前 HEAD 上同样存在)。
- `memory-bank/`: issue 26-11-15-0332 置 Done(§02 位置复校 / §03 处置填实 / 状态日志); 坑档 `pitfalls/web-ui/rowwin-stale-rowh-pad-jump.md` 重写(两根因 + 守阵三面, 原「处置」是已退役的测试侧预热); `testing/flaky-ledger.md` 原 drawer-dock 行补产品侧修复去向; 本基线切片。

## 未做

- 未 commit / 未 push(需用户显式指令)。
- 未改 `_winZoomOf` / `_winCtnSync` / 行高签名因子 —— 本批刻意不碰 rowh-sig-and-transition-geometry 的两个已知坑面。
- 未做「行集变了就重算占位基准」—— 收口轮论证过做不到(见上), 只留边界注释。
- `e2e/kbd-scroll-band.spec.mjs` 的 Home/End(prism)在三 spec 合跑时红过一次, 单独复跑与再次合跑均绿(机器上有常驻服务在跑), 判为负载抖动, 未改动该用例; 与本批改动无因果关系(该用例不涉行高存值, 且红时行窗路径未变)。
