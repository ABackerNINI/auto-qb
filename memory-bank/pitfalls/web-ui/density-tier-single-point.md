# 单档化后「档制判据」不得散落成字面量(缺省/兜底/候选集各写一处必然漂移)

> 摘要: 移除「经典 / 变体」两档制的一方时(删经典档或删变体档), 真正危险的不是删组件, 而是**档制判据散落在四五处**: 菜单候选集(`[{id:"classic"}].concat(options(tab))`)、缺省读侧(`readSel` 的 out 初始化)、各消费方(`|| CLASSIC`、`|| "classic"` 五处)、渲染失败兜底(`this.drawerTplSel[st.tab] = CLASSIC`)、持久化写侧(`|| "classic"`)。删掉经典档后这些字面量**全部静默失真** —— 不缺报错、不白屏, 只表现为「某页签偶发改不动模板」「菜单永远只有一个项」「刷新后选择回落」。判据: 任何「档位/模板/渲染路径」的集合变更, 先把判据收成**一个注册表 API 组**(可用性 + 缺省档 + 候选集), 再让所有点消费; 收口后全层不得再出现 `|| CLASSIC` 类字面量(静态守阵可钉)。
> 等级: L0
> 触发: 档制单档化, 删经典档, 删变体档, defaultSel, CLASSIC_TABS, hasClassic, choices, 缺省档, 渲染失败兜底, 补落经典, 菜单只有一个项, 菜单候选集, 兜底失真, readSel, dtPersistSel, 旧存值回落, drawerTplSel 缺键

**Refs:** memory-bank/tasks/26-10-14-webui-detail-classic-removal.md

### 判据五处漂移: 菜单候选 / 缺省读侧 / 各消费方 / 渲染兜底 / 持久化写侧

- **触发**: 2026-10-14「移除四内容页签经典 UI」时(用户令: 种子详情面板除流量页外的 4 个经典 UI + 流量页/qB 流量页的除经典外的 UI 全删), 初版思路是「删组件 + 把菜单里的 `[{id:"classic"}]` 去掉」—— 那会漏掉另外四处, 且每一处都是**静默**的:
  ① `readSel()` 的初值全 `CLASSIC` → 四内容页签永远缺省回「经典」, 而经典已不存在 ⇒ `dtVueTab` 恒真但宿主不挂, 内容页**恒空**(不白屏, 无报错);
  ② 五处消费方 `(this.drawerTplSel||{})[tab] || CLASSIC` / `|| "classic"` → 缺键时取到已删除的档;
  ③ `_dtRender` 的 catch 把 `drawerTplSel[tab] = CLASSIC` → 渲染失败后复位到不存在的档, 下一拍仍挂不上;
  ④ `dtPersistSel()` 写 `|| "classic"` → 刷新后把缺档写进存储;
  ⑤ `initialDrawerTpl()` 的防御字面量仍全 classic。
  node 探针能抓到 ③④, 但 ①②只有真机/静态守阵能抓。
- **判别**: 「档位集合」被单边删/加时, `grep -n "CLASSIC\|\"classic\""` 全层扫一遍, 命中处**逐个问**「这一处的缺省/兜底目标现在还存在吗」。凡出现同一个缺省语义写在两处以上, 就是漂移现场。
- **处置**: 收成注册表一组 API: `hasClassic(tab)`(可用性)、`defaultSel(tab)`(缺省档: 有经典→classic, 否则该页签**首个注册变体**)、`choices(tab)`(菜单候选集, 含经典则经典在首位), 再加一个 mixin 取值口 `_dtSel(tab)` 让全层消费; 全层不许再写 `|| CLASSIC`。渲染失败兜底也走 `defaultSel`(经典档整体删除后四内容页签的兜底 = 该页签首个变体; 缺省档自身抛错则留空 + console.error 留痕, 不再有第二实现可退)。旧存值(四页签 `"classic"`、流量页签 `13/14/15`)经 `readSel` 白名单自然失效回落 —— **不需要写迁移脚本**。
- **衍生**: 候选集长度 < 2 的页签(本例流量页签变体删光后只剩经典一档)会让模板菜单退化成「单选项菜单」= 半残 UI, 入口侧必须早退(`openDrawerMenu` 判 `choices(tab).length < 2 && !dtMenuMergeOn` 则不弹), 而不是把菜单留着弹出唯一一项。
