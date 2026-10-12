# 26-10-13-0027 WEBUI 抽屉三列表切换种子空态闪现修复(第九次复发)

> 摘要: 用户报「种子详情用户页切换种子时『暂无已连接用户』闪烁」, 随后指令「提交后修复 trackers/files 的同族问题」。前八次都在锚契约面/渲染驱动面, 本次病根在**数据落袋语义面**: 软切换(FX-29)的立命之本「保留旧数据撑几何 + 遮罩防串显, 数据全部到手才掀罩」中, 「到手」只判「响应回来了」—— **空响应同样算到手**: 它覆盖对应列表(drawer.peers/trackers/files)并把旧数据清掉, 且登记 `_drawerDone` 掀罩 ⇒ 渲染层判空 ⇒ 一帧空态; 而真机换目标后 qB 对新种子的**首个**列表响应常瞬时为空(连接/状态未就绪) ⇒ 观感「表格 → 空态 →(下一拍 5s)表格」。复现(临时探针, 已清): 80 对端真量级 + route 让切换目标首拍 /peers 返空 ⇒ classic 与 07/08/09 全部 `C80`→`E0`(~180 空态帧), 恒非空对照 0 帧。**为什么逃逸**: 桩 `ui_harness` 对每个种子恒灌数据(peers 1~7 对端 / trackers 多条 / files 两文件)**从不返回空**, 且 e2e 全部用例只 `dblclick nth=0` **单次打开**(无"切换种子"用例)⇒ 双零覆盖。修复: 上提为**三列表共用单点** `_drawerGraceHold` —— 换目标窗口内首个空响应视为「未就绪」(不落袋/不掀罩/1s 后快速重拉一次, 仍空才接受), 标记 `_drawerGrace` 由 `_switchDrawerTarget` 于 `_loadDrawerTab` **之后**置位, 重拉 timer 由 `_stopDrawerPoll` 收口。验证: 红验闭环(拆宽限 ⇒ e2e 三页签×双皮肤 6/6 全红) + 静态守阵 + 三页签 e2e; 全量数字见 `commands run kb.baseline`。

> 最后活动: 2026-10-13 00:54

**Refs:** memory-bank/pitfalls/web-ui/drawer-switch-flicker.md,memory-bank/testing/baselines/26-10-13-0054-webui-drawer-switch-empty-grace.md

## 背景

用户报「种子详情用户页切换种子时『暂无已连接用户』闪烁」—— 与 2026-10-07 那次(切片
`26-10-07-0411-webui-drawer-peers-empty-loading`)同一现象, 但那次修的是 `openTorrentDrawer`
入口「已开面板换目标交棒软切换」, 本次病根在更下游的**数据落袋语义**, 第五次的修法拦不住。
这是本坑第九次复发(`pitfalls/web-ui/drawer-switch-flicker.md`)。用户在本次修复提交后(c448ba8c)
随即指令「修复 trackers/files 的同族问题」—— 二者是**同一个落袋语义**, 一并收口(见下)。

## 根因(实测复现, 非推理)

前八次都在**锚契约面**或**渲染驱动面**; 本次在**数据落袋语义面**:

1. `_switchDrawerTarget` 保留旧列表数据(FX-29 本意)✓
2. 但列表 fetcher 的落袋判据只有「响应回来了」—— **空响应也算**: 覆盖 `drawer.peers/trackers/files`
   (旧数据被清)+ 登记 `_drawerDone`(待到集合清空 ⇒ 掀罩)
3. 渲染层判空 ⇒ 一帧空态(用户页「暂无已连接用户」/ Tracker 页「暂无 tracker」/ 内容页「无文件列表」)
4. 真机换目标后 qB 对新种子的**首个**列表响应常瞬时为空(连接/状态未就绪) ⇒ 用户看到「闪一下」;
   下一拍(5s)真实数据到达再顶回表格

**复现证据**(临时探针, 跑完即删): 注入 80 对端真量级 + route 让切换目标**首拍** /peers 返空
—— classic / 07 / 08 / 09 **全部复现**(逐帧 rAF 采样 `C80`=80 行表格 → `E0`=空态, ~180 帧);
**恒非空对照**全部 0 空态帧(275 帧全 `C80`)。

**为什么前八次没修到 / e2e 漏网**(两条同时成立才逃逸): ①桩 `ui_harness.py` 对每个种子恒灌数据
(peers 1~7 对端 / trackers 多条 / files 两文件), **从不返回空**; ②e2e 全部 drawer spec 只
`dblclick nth=0` 单次打开(唯一涉及软切换的 `drawer-bridge-stub.spec.mjs` 路径C 只断言"桥稳定存活",
不断言无空态)。

## 修复(三列表共用单点)

- `src/auto_qb/webui/static/shared/drawer_store.js`:
  - 新增 `_drawerGraceHold(src, hash, count, refetch)` —— 三列表共用宽限单点: 标记守卫 +
    **一次性消费**(首次非 silent 落袋即消费本 src 标记: 非空 → 正常落袋; 空 → 宽限重拉) +
    1s `setTimeout` 重拉(含 面板仍开/种子形态/目标未换 复核)
  - `_fetchDrawerPeers` / `_fetchDrawerTrackers` / `_fetchDrawerFiles` 三者接入: `!silent && _drawerGraceHold(...)`
    ⇒ `deferred = true` + `return`, finally 里 `if (deferred) return;`(不落袋/不 `_dtNotify`/保持 loading)
  - `_switchDrawerTarget` 结束处置 `this._drawerGrace = { peers: true, trackers: true, files: true }`
    (必须在 `_loadDrawerTab` **之后** —— 其内 `_startDrawerPoll→_stopDrawerPoll` 会清空标记)
  - `_stopDrawerPoll` 收口: 逐个 `clearTimeout(this._drawerGraceRetry[src])` + `this._drawerGrace = null`
- `e2e/drawer-switch-empty-grace.spec.mjs`(新增): 三页签(用户/Tracker/内容)× 双皮肤, route 让
  切换目标首拍列表响应返空, 逐帧 rAF 采样空态 + 断言重拉后列表就位
- `e2e/drawer-peers.spec.mjs`: 上一轮落在本文件的单页签用例**迁出**到上述合并 spec, 原位只留指针
  (避免同一机制两处各自演化)
- `tests/test_webui_static_dom_panel.py`: 守阵由 `test_drawer_peers_switch_empty_grace_wiring`
  改造为 `test_drawer_list_switch_empty_grace_wiring`(钉单点语义 + 三 fetcher 接入 + 置位次序 + timer 收口)

## 验证

| 项 | 结果 |
|---|---|
| 红验(拆宽限置位) | e2e 三页签 × 双皮肤 **6/6 全红**(逐条命中各页签空态文案); 还原即绿 |
| 探针(复现) | classic/07/08/09 均 `C80`→`E0`; 恒非空对照 0 空态帧 |
| e2e(三页签 spec) | 6/6 绿(prism+atlas) |
| 全量 e2e | 见基线切片 |
| test.full | 见基线切片(`commands run kb.baseline`) |

## 遗留 / 范围外

- 口径取舍: 「空响应 = 未就绪 vs 真没有」前端无法区分, 本方案取「宁可多等 1s 也不误报空」——
  真没数据的种子会先显示 1s 加载态再落空态(已记坑档)。
- 本坑的**渲染/锚契约面**历史结论(前八次)仍有效; 本条新增的是**数据落袋语义面**, 两者互不替代。
- 全量 e2e 中 `drawer-peers-sticky-flush` 的 atlas 亚像素几何(±1px 容差边缘)有既发 flaky(单独复跑
  两轮 4/4 绿), 与本波无关, 未入池。
