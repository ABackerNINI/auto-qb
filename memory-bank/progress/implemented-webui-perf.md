# 已实现 · WEB UI(跟手性 / 拆分 / 乐观 UI)

> 摘要: 摘要: 前端性能、交互时序与状态色的落地记录 —— app.js 拆分 / 轮询节拍 / 跟手性三波次 / 乐观 UI / 状态色收口 / 组件库 / rid 式增量同步。
> 触发: 跟手性, 性能, 乐观 UI, 轮询节拍, 状态色, app.js 拆分, 组件库, 命令埋点, 增量同步, delta, rid

## 已实现 (✅, 有单测覆盖)

- **qB 流量图 v3 S6 活尾合流 (2026-10-05, 计划 [26-10-04-1957](../plans/26-10-04-1957-plan-qb-traffic-storage-v3.html) / 档案 [26-10-04-backend-qb-traffic-storage-v3](../tasks/26-10-04-backend-qb-traffic-storage-v3.md))**: 写侧每轮发布不可变 LiveTail 快照 + store 纯函数 `v3_live_tail_slots`(中途 flush 后从写侧游标倒推槽位) + grid 合流(镜像保证: 同记录写侧与落盘重算槽 ts 恒等), raw 段窗随采样节拍实时; agg 段窗缺口入池 issue 26-10-05-1015。
- **qB 流量采样 1.5s 档修复 (2026-10-05)**: `_apply_interval` 把块头 B 行整秒口径误赋 `task.interval` ⇒ 1.5s 被静默抬 2s; 生效间隔保持浮点 + dat 格式放宽「整秒 → >=1 允许小数秒」(纯放宽零迁移)。

- **WEB UI rid 式增量同步全量落地 (2026-10-07, 计划 26-10-07-0414 S0-S10 全步 + 收尾)**: /api/state 在既有 rid 门控之上叠加 delta 载荷 —— 服务端键集时间线(deque 40 代**只存键不存值**, 值回放从当前已发布视图现取; 跨拍累积器 R4 / 交叉抵消 R5 / full 降级源 R11: config_reload·unkeyed_command_source·hr_revision·row_key_unresolvable·cross_group·show_unrecognized·shows_pending 归位)+ `delta=1` 协商协议(P-01: 未协商客户端逐字节兼容)+ 前端 `applyStateRows` 行级合并(S4, delta=1 默认声明); group/torrent/show 三视图全启用, S6/S9 脏键**局部重聚合**(未脏行对象引用原样保留, S7 前端 WeakMap 装饰记忆化; S8 剧键等价映射), S5 镜子测试 M1-M12 + fuzz 220 轮兜正确性。P-03 裁决: pending_ver 消费门控**保留**(增量下成本=一次键集追加)。机制单点 [../systemPatterns/web-runtime.md](../systemPatterns/web-runtime.md)「rid 式增量同步」段; 分档实测(delta 载荷 1,809B ≈ 全量回包 1/4800、HTTP delta 轮 ~4ms、前端 delta 轮 29-43ms 与档位无关)见 [../testing/baselines/26-10-07-1336-webui-delta-sync-s10-baseline.md](../testing/baselines/attachments/26-10-07-1336-webui-delta-sync-s10-baseline.md); 坑档 [../pitfalls/testing/stub-bypass-apply.md](../pitfalls/testing/stub-bypass-apply.md) + [../pitfalls/backend/last-round-snapshot-stale.md](../pitfalls/backend/last-round-snapshot-stale.md)。

- **PERF-01 · 星图卡顿 / 点状态栏历史流量卡顿修复 (2026-09-24)**: 用户报「atlas UI 卡顿, 特别是点击状态栏历史流量显示卡顿, prism UI 无此问题」。**定位**: 逻辑层 `shared/app.js` 两套共用 ⇒ 单边卡顿的差异只可能在 CSS; 按属性统计两套 CSS, box-shadow(44:44) / transition(59:58) / animation(22:19) 全对齐, **只有 `backdrop-filter` 6:2** —— 星图挂了 5 处(`.topbar` blur(12px) / `.status-strip` blur(10px) / `.modal-mask` blur(3px) / `.ce-actions` blur(10px) / `.drawer-mask` blur(2px)), 棱镜只有 `.drawer-mask` 一处。**根因 = 嵌套毛玻璃**: `.modal-mask` 铺开时它的 backdrop 里正压着 `.topbar` 与 `.status-strip` 两块毛玻璃, 浏览器每帧回读 + 重复模糊整个视口, 叠上弹层内 `hist-draw` 描边动画的主线程逐帧重绘即为卡顿; 棱镜 `.modal-mask` 从不带 backdrop-filter ⇒ 无嵌套 ⇒ 无症状。**修法**(仅 atlas/style.css): 摘掉遮罩与吸顶/吸底条的 blur, `--glass` 改不透明 `#131a26`(与棱镜 `--glass: #111e31` 同口径, 摘掉模糊后继续半透明会让滚动内容从条下透出), 遮罩 .62 → .72 补观感; `.drawer-mask` blur(2px) 保留(已是唯一毛玻璃层, 单边改会破"成对改"纪律)。**守阵**: `test_frontend_static_bundle_health` 新增第 13 项 `_scan_backdrop_filter`(位置禁令 + 两套数量相等), 已红验(把 blur 加回 `.status-strip` ⇒ 两条断言同时红)。**验证**: 全量 **1201 passed + 1 skipped / TOTAL 91%**(与基线一致, 只加断言未加用例); 真浏览器冒烟桩服务 **70/70 PASS** 双 UI 0 console.error; 定向实测脚本确认两套 UI 的 `.modal-mask`/`.topbar`/`.status-strip` computed backdrop-filter 均为 `none`。⚠ **性能证据是结构性的**(parity + 嵌套毛玻璃是 Chromium 公认病态路径), headless 复现不出 GPU 合成开销(修复前后耗时同量级), 未编造耗时差。详见 [../pitfalls/web-ui/css-perf-parity.md](../pitfalls/web-ui/css-perf-parity.md)。

> 已外迁: 2026-09-17~09-24 的 11 条 → [attachments/implemented-webui-perf-archive-2026-09.md](attachments/implemented-webui-perf-archive-2026-09.md)

- **🆕 列设置重置 · 双轨模型重设计 —— 已实施完毕(已入库 `e5c31d1`), 剩真机走查**: 用户定性"修复了很多次,
  急需重新设计, 简化模型, 从根本上杜绝"; 计划
  [memory-bank/plans/26-09-21-1551-column-prefs-intent-redesign-plan.html](../plans/26-09-21-1551-column-prefs-intent-redesign-plan.html),
  D1(升 v5+迁移)/D2(fit=回全自动)/D3(origin 空存储提示)已按推荐全部落地。
  **新模型**: 存储只存意图(`colHidden/colOrder/colW`, `w=null`=全自动页), 生效宽度 `colWidths` 由
  `recomputeEffective()` 按窗口现算**绝不落盘**; 唯一漏斗 `persistPage(page)`(全仓唯一 setItem,
  v5 按页子树 RMW); `migrateLegacyToV5` 内存迁移(v4 固化页保宽 / 非固化页污染 px 清零); manual 标志删除;
  六个意图动作统一走漏斗, 拖宽/双击自适应以 merge 保隐藏列 px(封掉 S4 的 11→10 通道)。
  **验证**: 静态守阵 1 换 4(唯一 setItem / 只收意图 / 标志位不得复活 / 键链必挂迁移), 红验 4/4;
  冒烟双 UI 64 项失败 2 项(均既有「P0-3 乐观态落回真值」, 与列偏好无关; ~~该 2 条~~ 2026-09-22 已修, 现三模式全绿), 新 4 场景(异视口互不吞+F3 /
  全自动页不落px / 隐藏列保宽 / v4→v5 迁移)双 UI 全 PASS; 全量 **1142 passed**(39.88s, Windows)。
  **真机走查清单**: ①固定地址双标签各改列宽/显隐互刷不丢 ②固化页隐藏一列→拖宽→再显示 px 原样回来
  ③"适应窗口"=回全自动(继续随窗口自适应, 不再固化快照 —— 行为变化点) ④换地址打开出 origin 提示(一次)。
  ⚠ 用户实例是 `D:\Projects\auto-qb` 的 editable install —— 已入库 `e5c31d1`, 需在那边拉取后才生效。
- **乐观 UI「撤下」改造 (P0–P3)** —— **详述已外迁**: [attachments/optimistic-ui.md](attachments/optimistic-ui.md)
