# 26-10-22-webui-kbd-esc-collapse-cursor — Esc 收起明细表后键盘光标退回被收起的父行

**Status:** Done
**Added:** 2026-10-22
**Updated:** 2026-10-22
**Summary:** 辅种页键盘光标进入明细表后按 Esc, 明细表收起的同时虚线框也跟着消失(用户表述为"锚点被清除"); 实测 Esc 从未清过 `kbCursor`, 是明细行随收起卸载把虚线框连坐带走、光标悬空指向链外 hash。修法 = Esc 退栈链三档收起分支「谁被收起, 光标退回谁」, 与 `←` 同归位口径, 追剧页两档一并收编
**Topics:** webui-kbd-esc-collapse-cursor
**Refs:** memory-bank/pitfalls/web-ui/kbd-cursor-collapse-dangling.md, memory-bank/testing/baselines/26-10-22-0227-webui-kbd-esc-collapse-cursor.md

## 原始请求

1. 用户(2026-10-22 01:35): 「WEBUI辅种页在键盘锚点进入明细表后按esc会退出明细表并清除键盘锚点, 后者应该改为锚点退回对应的辅种列」 —— 附 `grilling`, 要求先逼问清楚再动手。
2. 用户(2026-10-22 01:50)对第一轮六个问题答「Q1 确认是 kbCursor; 全部按推荐」。
3. 用户(2026-10-22 02:23): 「立档然后收尾提交」。

## 思考过程与决策

- **术语先行澄清(grilling 第一轮最大的收获)**: 代码里"锚点"有两个东西 —— `kbCursor`(虚线描边那条, 键盘光标)与 `selAnchorGroup/Member/Unit`(Shift 连选起点)。Esc 走 `clearSelection()` 清的是**后者**, 前者从头到尾没被碰过, 且被 `e2e/shift-select-anchor.spec.mjs` 显式钉死"Esc 不动光标"。所以用户看到的"锚点消失"**不是被清, 是被连坐**: 明细行随 `expandedKey=null` 一起卸载, `.kb-cursor` 类所在的宿主元素没了。Q1 拍板改的对象是 `kbCursor`。
- **真正的病灶是"悬空"而非"清除"**: 收起后 `kbCursor` 仍指着那个已不在 `_kbRows()` 链上的成员 hash, 于是下一次 ↑↓ 走 `_kbViewportRow` 无光标回落(落视口内首/末行) —— 观感是"光标丢了, 按键跳到别处"。这条写进了坑档 `pitfalls/web-ui/kbd-cursor-collapse-dangling.md`(复发 1: `←` 路径早在 2026-10-09 就收编了同形态, Esc 退栈链在另一个文件里没被覆盖)。
- **归位落点 = 被收起的父行, 不是"辅种页某一列"**: 辅种页是单表、没有列布局, `expandedKey` 单值 ⇒ 落点唯一。追剧页是两层展开(剧→集→版本行), 三档同构: `expandedKey`→`group` / `expandedShowEp`→`ep` / `expandedShows`→`show`。
- **不复用 `_kbCollapseRow`, 就地三行赋值**: `shortcuts.js` 的 `_kbCollapseRow` 已经做了完全一样的事, 但它在快捷键引擎里, Esc 退栈链在 `lifecycle.js` —— 跨文件调引擎内部方法等于让退栈链反向依赖引擎(注册序还有守阵盯)。就地写零新依赖, 且父行紧邻被收起的明细块、本就在视口内, 不需要滚动跟随(顺带避开禁 `scrollIntoView` 的红线)。守阵里禁的是**真调用** `this._kbCollapseRow(`, 注释点名同口径允许。
- **"有选中"那一档保持不动**: 退栈链是 `else if` 链、一次按键只退一层 —— `selMembers` 非空时 Esc 只清选择, 明细表不动、光标也不动。既有的 `shift-select-anchor.spec.mjs`「Esc 不动光标」断言因此**仍然成立**(已复跑验证)。
- **无条件归位**: 光标不在被收起的分支内(甚至为 null)时, Esc 依然把光标落到被收起的父行 —— 与 `←` 的无条件行为一致, 单 `expandedKey` 模型下"抢走别处光标"是罕见边角, 两处一致比边角正确更好记。
- **多剧同时展开的选支口径**: `expandedShows` 是数组(`shows.js` 可 push 多支), 归位优先退回**光标所在那一支**(走 `_kbParseEpId` 单点解析 ep id 的 showKey, 不手抄 id 形态), 否则退回首支 —— 避免一次 Esc 把光标横跳到屏幕另一头的剧。
- **范围: 追剧页两档一起改**(Q6 推荐被采纳): 同一条 `else if` 链、紧挨着的两档, 只改辅种页会在同一处留不对称缺口。
- **不碰 `selAnchor*`**: 本次对象只有 `kbCursor`(Q1), `menu.js::toggleExpand` 展开时写 `selAnchorGroup` 的行为不在本轮范围(范围守恒)。

## 实现计划

单会话: grilling 澄清(两轮) → 定位 Esc 退栈链与光标链 → `lifecycle.js` 三档改造 → 静态守阵(红验) → 浏览器 e2e 两条 @fast(红验) → 全量 `test.full` + e2e 全量复跑 → 立档(坑档 / 基线 / 档案) + `kb.wrap` + `kb.index` → 随本专题入库。

## 子任务状态表

| 步 | 内容 | 状态 |
|---|---|---|
| S1 | 定位: Esc 退栈链(`lifecycle.js`)· 光标模型(`state.js::kbCursor` / `shortcuts.js::_kbRows`)· `←` 既有归位(`_kbCollapseRow`)· 既有 e2e 断言 | Done (2026-10-22) |
| S2 | grilling 两轮定口径: 对象=`kbCursor` / 落点=被收起的父行 / 就地写不复用引擎 / 有选中那档不动 / 无条件归位 / 追剧页同收编 | Done (2026-10-22) |
| S3 | `lifecycle.js` 三档收起分支改造(含多剧选支 `_kbParseEpId`) | Done (2026-10-22) |
| S4 | 静态守阵 `test_esc_collapse_returns_cursor_to_parent` + 测试计划清单同步(红验) | Done (2026-10-22) |
| S5 | `e2e/kbd-members.spec.mjs` 加两条 @fast(辅种页 / 追剧页逐层), 头注覆盖清单同步(红验) | Done (2026-10-22) |
| S6 | 复跑: `test.full` + e2e 全量 + `shift-select-anchor` 回归 | Done (2026-10-22) |
| S7 | 立档(坑档 / 基线切片 / 本档案) + `kb.wrap` + `kb.index` + 随本专题入库 | Done (2026-10-22) |

## 进度日志

### R0 · 立档 (2026-10-22)

- 开工同步远端后定位到退栈链三档与光标链, 确认 Esc 从不清 `kbCursor`(既有 e2e 钉死), 病灶定性为"卸载连坐 + 光标悬空"。
- 按六问结论改 `lifecycle.js` 三档: 复位展开态的同时把光标退回父行; 多剧展开优先光标所在那一支。
- 新增静态守阵一条 + 浏览器用例两条, 均红验(改回"只复位"即红)。
- 复跑: `test.full` 与 e2e 全量双绿, `shift-select-anchor.spec.mjs` 的"Esc 不动光标"断言不受影响(它走的是清选择那一档)。实测数字见 `commands run kb.baseline`(裸数字只写在基线切片这一处)。
- 收尾: 新坑档 `pitfalls/web-ui/kbd-cursor-collapse-dangling.md`(复发 1, 记「为什么没命中」= 旧记录的扫描面只盯快捷键引擎, 不含 `lifecycle.js` 退栈链)+ 基线切片 + 本档案, 随本专题入库。

- 2026-10-22 02:28 Esc 退栈链三档收起分支改为复位展开态同时把 kbCursor 退回被收起的父行(辅种 group / 追剧 ep / show), 就地赋值不复用引擎; 新增静态守阵一条 + 浏览器用例两条, test.full 与 e2e 全量双绿; 立坑档/基线/档案
