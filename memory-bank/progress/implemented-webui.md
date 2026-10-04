# 已实现 · WEB UI(界面 / 视图 / 状态色)

> 摘要: 摘要: 前端界面与视图的落地记录 —— 设置页 / 追剧视图 / 双界面 / 错误原因 / 各轮修复。
> 触发: WEB UI 做过没有, 前端功能, 设置页, 视图, 状态色, 修复轮次, 双界面

## 已实现 (✅, 有单测覆盖)

> 本文件只留近期条目; 2026-09-26~10-02 十六条及更早的条目已按 cap 轮转**原文外迁** → [implemented-webui-history.md](implemented-webui-history.md)(下方各条留一行指针, 事实不变)。

- **WEB UI 复述型 tooltip 全量移除 67 处 + 不复活守卫**(2026-10-04, 判定报告
  [reports/26-10-04-0815](../reports/26-10-04-0815-report-webui-tooltip-declutter.html) 全量实施, 提交链
  `72a7d274`(报告)→`80220a82`(A 组状态栏 7 处 + A5 sbStats 精简)→`5c0412ff`(B 组顶栏 12)→`ae919a39`
  (追剧/详情抽屉 12)→`728f92ab`(对话框族 19)→`a33db037`(设置页/配置编辑器 16)→`e8203a3c`
  (H1 columns.js + 守卫), 分支 webui-tooltip-declutter 待并回): 133 处全量清点按 R1 复述 / R2 自明+无害 /
  R3 截断兜底 / R4 信息增量 / R5 不可发现交互+后果预告 五类判据判定, 移除 67 / 保留 66; 悬浮提示唯一
  通道仍是 shared/ui_feedback.js `.aq-tip` 拦截层, 移除 = 纯删 title 属性, 三皮肤零成对改; dialogs.js
  A5(statusbar 统计项)按报告「精简」只去复述半句。守阵: test_removed_redundant_tooltips_stay_removed
  (tests/test_web.py)断言代表性已删文案不写回。全量基线 [testing/baselines/26-10-04-0900](../testing/baselines/26-10-04-0900-webui-tooltip-declutter.md);
  档案 [tasks/26-10-04-webui-tooltip-declutter](../tasks/26-10-04-webui-tooltip-declutter.md)(Done)。

- **WEB UI HR 拉取历史详情表**(2026-10-04, 计划
  [plans/26-10-04-0312](../plans/26-10-04-0312-plan-webui-hr-fetch-history.html) S1-S6 全落地, 提交链
  `49da6d06`(拍板落定: ⑤=2000条/站点+6个月, 余推荐A)→`0227f25c`(S1 `HrHistoryEvent` +
  `HrSiteData.history` 环形留痕, 不抬 hr_site 版本链)→`4c88e8e2`(S2 波次/拦截(含 force-defer)/对账三类
  事件写入点, poll 跳过零写盘)→`2923ffa4`(S3 `history_rows()` 只读口径 + `GET /api/hr/history`)→
  `85a22f8a`(S4 全屏弹层表③: 懒加载/站点chips/仅看异常/行展开档位明细)→`ec697a08`(S5 ui_harness 桩
  五形态 + 表③断言与三皮肤目检), 分支 webui-hr-fetch-history 待并回): 「什么时间拉取了什么站点/解析
  结果」可考 —— 参照扩展选项页取数明细表且更细; 已知限制: 新旧版本混跑窗口期旧程序写盘丢 history 键
  (业务字段无损, 不做双写兼容)。test.full 2442 passed + 3 skipped / 30.93s / 99%(基线
  [26-10-04-0632](../testing/baselines/26-10-04-0632-webui-hr-fetch-history.md)); 三皮肤冒烟 207/207 +
  15 张截图目检; 档案 [tasks/26-10-04-webui-hr-fetch-history](../tasks/26-10-04-webui-hr-fetch-history.md)(Done)。

- **WEB UI 添加种子三下拉 label 闪烁「第四轮」(JS 收层守卫单点加固)**(2026-10-04): 用户报 594e247f
  三修后真机仍稳定复现。本轮探针自校验(摘掉 `@mousedown.prevent` → delay=150 完整闪烁链复现)证明
  三修代码在 Chromium 人手时序下干净(三皮肤 × 四场景 24/24 零翻转), 用户症状 = 浏览器跑的还是旧
  模板 —— SPA 的模板/JS 以页面加载时刻为准, 长开页签不刷新服务端更新到不了。代码侧加固 = 收层不再
  依赖「模板与 JS 同代到达」: `addPopBlurClose`/`metaCatBlurClose` 的 40ms 定时器收层前问
  `_popBlurShouldHold`(mounted 挂 mousedown capture 记录器, unmounted 对称移除) —— 焦点已回本族
  输入框或本族 label 转发 click 仍在途(350ms 新鲜度)→ 跳过收层; 模板修饰符在 = 纯 no-op, 缺位 =
  独立根除闪烁, 任何代际混合都安全。守卫 vs 旧模板 4/4(点空白/Tab/过期 blur 三条正常收层路径零误伤);
  守阵 combo 第 7 组 + 拖拽守阵 mounted 断言改子集语义; 用户侧验收 = 服务重启后整页强刷再走查。
  基线 [testing/baselines/26-10-04-0240](../testing/baselines/26-10-04-0240-webui-addcombo-label-round4.md)
  (2419 passed + 3 skipped / 31.86s / 99%, stash→sync 合并 2b10581a 后重测)。

- **WEB UI qB 口径流量图三图**(2026-10-04 实施完成, 方案C): 全局弹层 / 单种抽屉「流量」页签 / 分组弹层三挂点 (uPlot vendor 单文件, 三主题登记, 低频轮询); 后端采样管线 (core/modules/traffic_sample_mod.py, 全局恒采 + 单种活跃过滤) + dat 存储层 (core/traffic_store.py, `<data_dir>/qb-traffic/` global.dat + torrents/&lt;infohash&gt;.dat, 小时封口 catch-up 补封 + 半行容错/损坏隔离 + index/reconcile + 删种冻结/重加解冻/按龄淘汰) + 三 GET API (webui/server/traffic_qb.py, 栅格离散 null 断线 + 组读侧聚合, 金清单 75); 配置键 `qb_traffic`(enabled 缺省 false = 零开销)。P6 十条桩验证 10/10 过 (桩验证替代真机); 真机遗留: fastresume 单种 all-time 持久性 / alltime 回退幅度待观察。实施权威 = [计划 26-10-03-0946](../plans/26-10-03-0946-plan-qb-traffic-charts-c.html) + [档案 26-10-03-webui-qb-traffic-charts](../tasks/26-10-03-webui-qb-traffic-charts.md) (P6 验证记录节); test.full 2418 passed / 99%。**2026-10-04 跟进: 三挂点并入底部详情抽屉**(删两个模态弹层, 与种子详情「流量」页签共用同一段正文块与同一拖拽高度, `.drawer-dock` 落点上提 app 级 `tpl/dock.html` = 任意页可开, 图高改量宿主 clientHeight 并宽高双观察 -> 拖拽调高图实时跟随; 见 [activeContext 26-10-04-0405](../activeContext/26-10-04-0405-webui-qb-traffic-drawer-merge.md))。

- **WEB UI 添加种子三浮层互斥补双向(closeAddPopsExcept 单点)**(2026-10-04): issue 26-10-04-0130
  认领, 按建议方向二实施。原互斥矩阵单向(openAddPathPop 收 cat/tag, 反向 openAddCatMenu/
  openAddTagMenu 不收 addPathPop), 路径面板与下拉可同悬且面板盖住相邻字段 label 的点击(Playwright
  实测 "subtree intercepts pointer events"); 失焦合帧兜不住 —— 新字段 @focus 先 _addPopBlurCancel
  撤掉定时器。修法 = 抽 `closeAddPopsExcept(kind)` 三浮层互斥单点(收层带 Hi 复位), 三开层各调一次,
  后续加第四个浮层单点补分支即可; 守阵 `test_frontend_add_combo_blur_close_and_fit` 补第 6 组
  「互斥双向」静态断言。Playwright 走查 6/6(focus 迁移焦点避开面板几何拦截, 修复前反向缺口终态
  双开、修复后单浮层); 基线 [testing/baselines/26-10-04-0150](../testing/baselines/26-10-04-0150-webui-add-pop-mutex.md)
  (2419 passed + 3 skipped / 99%, 合并 4805f5f5 后重测)。

- **WEB UI 添加种子三下拉 label 闪烁「第三轮」(上轮修法未修住)**(2026-10-04): 用户报 a7ebbe14 后
  「点字段 label 稳定复现下拉闪烁」依旧。真浏览器事件埋点定位: 第二轮两个判断是错的 —— label 的
  **mousedown** 默认动作就会 blur 已聚焦的输入框(focusout related=null 实测在),"回焦 ~2ms"只是
  零延迟合成点击的假象, 真人按下到抬起隔 **80~150ms** ⇒ addPopBlurClose 的 40ms 合帧定时器在
  **按住期间**先收层, 松手 label click 默认动作回焦重开 = 每次必闪; 第二轮走查 39/39 全绿是因为
  Playwright 默认点击 down/up 只隔 ~2ms, 撞不上 40ms 窗。修法 = 四个字段 label(添加窗口三字段 +
  meta 分类)一律 `@mousedown.prevent`(mousedown 不产生 blur ⇒ 收层定时器不武装, 竞态从根上消失;
  @click.stop 保留挡 window 收层, 缺一即回归; 关闭态点 label 仍正常聚焦+开菜单, 实测)。守阵第 1 组
  扩为双断言; 坑档 [combobox-focusout-close(复发+1, 第三轮)](../pitfalls/web-ui/combobox-focusout-close.md)
  —— 教训: 合成零延迟点击验证不了按住时序竞态, 走查必须 `delay>=120ms`。基线
  [testing/baselines/26-10-04-0054](../testing/baselines/26-10-04-0054-webui-addcombo-label-round3.md)
  (2418 passed + 3 skipped / 99%, 合并 30143bda 后重测); 三皮肤 24/24(delay=150ms 人手时序)。

- **WEB UI 抽屉出入过渡动画** (2026-10-04): 用户报「抽屉出现与消失时很生硬」 —— 停靠面板占文档流,
  open 翻转时列表底部一帧被面板撑开/收回, 面板本体滑淡治不了布局跳变; JS 过渡钩子驱动 `.drawer-dock`
  槽位高度插值(drawer.js 出入过渡块 + drawer.html `<transition>` 接线), 收场同步收面板自身高 +
  dock 跟随, 动画期几何登记 `_drawerAnimTop` 供 `_kbViewBottom` 单点消费(行让位不读中间插值);
  seq 代际闸管快速往返, reduced-motion 与 D3 全屏态双豁免。守阵 `test_drawer_transition_dock_anim`;
  真浏览器探针三皮肤各 9/9; 基线 [testing/baselines/26-10-04-0015](../testing/baselines/26-10-04-0015-webui-drawer-transition-anim-done.md)
  (**2418 passed + 3 skipped / 99%**); 档案 [tasks/26-10-03-webui-drawer-redesign](../tasks/26-10-03-webui-drawer-redesign.md)

- **WEB UI 添加种子三下拉「第二轮遗留四项」**(2026-10-03): ①点字段 label **稳定**复现下拉闪烁 ——
  输入框已聚焦时点 label 不 blur(@focusout 不参与), 真链条是「label click 冒泡到 window 收层名单 →
  label 默认动作转发 click 给 for= 输入框 → 重开」⇒ 四个 combo 的字段 label 一律 `@click.stop`;
  ②三个 combobox 内嵌清空 x(`@mousedown.prevent` 保焦点 + `@click.stop` 挡 window 收层, 双修饰符
  缺一即"清完下拉没了"), 三皮肤 CSS 成对; ③拖选文字终点落在遮罩上抬手把窗口关了 —— click 的 target
  是 mousedown/mouseup 的**公共祖先**(= 遮罩), `@click.self` 误判 ⇒ 全仓 11 处遮罩统一改
  「mousedown 记臂位 + mouseup.self 才关」(dialogs.js 单点, 零残留); ④选中分类后逐字删除撑变形 ——
  开层限高按当时候选量算, 删字涨回全量时旧限高不更新 ⇒ 三个输入值各挂 watcher 重限(meta 侧同族);
  另排查出第 4 个 combo(meta 分类下拉)既无 @focusout 也不在 window click 名单 = 点别处悬着不收,
  一并补齐。守阵 `test_frontend_add_combo_label_clear_mask_and_refit`; 坑档
  [combobox-focusout-close(补第二轮)](../pitfalls/web-ui/combobox-focusout-close.md) +
  [modal-mask-click-self-drag(新)](../pitfalls/web-ui/modal-mask-click-self-drag.md);
  基线 [testing/baselines/26-10-03-2130](../testing/baselines/26-10-03-2130-webui-addcombo-round2.md)
  (2415 passed + 3 skipped / 99%); 三皮肤真机走查 39/39。

- **WEB UI 添加种子三下拉「失焦即收 + 限高不出窗」**(2026-10-03): 收层主判据 window click → `@focusout`
  + 40ms 合帧守卫(治点字段 label 转发回焦导致的「下拉闪烁再次出现/未失焦」, 概率性), 开层方法先撤销
  挂起收层; 开层 watcher `_fitAddPop` 量「输入行→滚动容器可见底沿」净空限高 + 候选异步重限(治菜单
  伸出窗口外把 `.add-dialog-body` 撑变形, 滚动条进窗)。守阵 `test_frontend_add_combo_blur_close_and_fit`;
  坑档 [pitfalls/web-ui/combobox-focusout-close.md](../pitfalls/web-ui/combobox-focusout-close.md);
  基线 [testing/baselines/26-10-03-1550](../testing/baselines/26-10-03-1550-webui-addcombo-blur-fit-done.md)
  (2391 passed + 3 skipped / 99%); 三皮肤真机走查 12/12 × 3。**未提交(等用户指令)**。

- **WEB UI 种子详情抽屉重设计: 浮层 → 底部停靠属性面板 (方案A)**(2026-10-03, 计划
  [plans/26-10-03-0917](../plans/26-10-03-0917-plan-webui-drawer-redesign.html) 五波, 提交链 `f994ce20`/`9c594e1e`/`b81a1ee4`/`a0b5d73f`,
  清偿 issue [26-10-01-2119-feat-webui-drawer-redesign](../issues/26-10-01-2119-feat-webui-drawer-redesign.html) +
  [26-10-01-2108-feat-webui-shortcuts-drawer-nav](../issues/26-10-01-2108-feat-webui-shortcuts-drawer-nav.html) +
  [26-10-01-2108-feat-webui-shortcuts-drawer-open](../issues/26-10-01-2108-feat-webui-shortcuts-drawer-open.html)):
  用户硬约束「抽屉打开时模糊列表、键盘切换看不清当前行」结构性消除 —— W1 浮层改列表下方全宽停靠面板
  (`.drawer-dock` sticky 吸底, boot.js "into" 支持选择器落点, 三皮肤 drawer 族 CSS 重写 + 下滑淡入),
  遮罩与 `backdrop-filter` 摘除 = **PERF-01 全站归零收尾**; W2 键盘跟随流: scope 存活(`_kbOverlayBusy` 摘 drawer.open,
  面板开着列表键位不灭)+ drawer-tab-* 四条 list scope 双态(Alt+1~4 关态开面板定位页签/开态切页)+
  详情防抖跟随单点 `_kbFollowDrawer`(200ms + seq 代际 + hash 短路, 挂 `_kbApplyCursor` 尾部)+
  D2 Enter 已开仅跟随不关; W3 高度治理: 拖拽调高夹取 [240px, 70vh] + 收起/展开钮 + 高度持久化 `autoqb.ui.drawerHeight`,
  D1 首屏默认收起(`drawerOpen` 只写不回读), tracker/peers 宽表全宽利用 ~97%; W4: D3 ≤900px 转全屏覆盖(纯 CSS)+
  计划内修复两处(停靠面板 sticky 吸底遮蔽以 `window.innerHeight` 为下界的滚动几何 → `_kbViewBottom` 单点下界让位面板顶缘;
  隐藏面板 5s 轮询收口 → 种子视图可见性守卫)+ kb-cursor 复检后未增强(三皮肤可辨, 与既有拍板打架)。
  坑: 模板 `_` 前缀裸标识符为已记坑复发(波及 drawer.html/popovers.html 复制钮, drawer.js 注释钉原因)。
  全量 **2329 passed + 3 skipped / 99%**(基线 [testing/baselines/26-10-03-1335](../testing/baselines/26-10-03-1335-webui-drawer-redesign-w4-done.md));
  冒烟走查单 24 项 × 三皮肤全过; 档案 [tasks/26-10-03-webui-drawer-redesign](../tasks/26-10-03-webui-drawer-redesign.md)

- **WEB UI 站点级「显式空 = 覆盖为空」三态 + 「跟随全局」删键: 删除类标签全局/站点作用域混淆修复**(2026-10-03, issue 26-10-01-2129 方案 B 完整形态, 三阶段提交 `18bde39c`/`42d3d90a`/`9c6bc499`): 根因三层(config 层 `_strip_none` 使 str/list「显式空=未定义」坍缩 / bool 开关恒写值从不删键单向锁死 / 回填用 schema 默认非全局生效值), 用户拍板 B 完整形态 + 配置版本升级。config 层: `Field.tri_state` 属性 + 4 站点 str 键标三态(hr.add_tag / add_category / add_tag_for_satisfied / add_category_for_satisfied)+ `_strip_none` 站点段豁免保 '' + validate 放行 + **配置 v3→v4 迁移**(经 infra.versioning 新增 migrate_with_notes 汇聚)清存量 '' 并逐键 WARNING, ruamel round-trip 保 '' 实测无损; keys.md / docs/configuration.md 同步。显示层: config_editor.js `SITE_FALLBACK_GLOBAL` 7 键回退链表 + cfgSiteFallbackPath/cfgFallbackValue 生效值回填 + siteBadge「站点/全局」来源徽标(站点 '' 原样显示)+ cfgIsDefault 链上键抑制「默认」矛盾徽标; 三皮肤零成对改。交互层: 「跟随全局」按钮接线死代码 cfgResetField/cfgDelPath(confirm danger + toast), str「清空保存=覆盖为空」与「跟随全局=删键」两动作区分, 9 键 help 三态文案(schema/trackers.py), 内联开关 tooltip risk+help 并接修复。守阵: config 层 v3→v4 迁移用例; 冒烟 118/118(atlas/prism/console, bool 三态走全 / str 覆盖为空 vs 删键 / 徽标回退链)。全量 **2325 passed + 3 skipped / 99%**(基线 [testing/baselines/26-10-03-0913](../testing/baselines/26-10-03-0913-webui-delete-tag-scope-confusion-done.md)); 档案 [tasks/26-10-03-webui-delete-tag-scope-confusion](../tasks/26-10-03-webui-delete-tag-scope-confusion.md); 报告 [reports/26-10-03-0504](../reports/26-10-03-0504-report-webui-site-scope-confusion.html); **随实施提交已入库**

- **WEB UI HR 判定新鲜度置脏 (2026-10-03, 计划
  [plans/26-10-03-0436](../plans/26-10-03-0436-plan-hr-hotreload-webui-stale-display.html) P2, `e4df1fc0`)**:
  HR 判定结果非 store 快照字段 —— 取数线程发布新视图(`HrViewPublisher.revision` 自增)无任何置脏消费方,
  WebUI 快照挂在旧值(热重载接入 HR 后恒显「本地·达标」的辅因; 独立缺陷: 运行期判定一变 UI 都要等别的原因
  碰巧置脏)。修法仿「错误原因」先例: `WebUIRuntime` 重建完成时记基线 `_hr_rev_at_build`(挂
  `_publish_locked` 末尾, 判空防御), `flush_views` 比对当前 `hr.revision` 与基线不等即 `mark_dirty()` ——
  基线随重建前移, 无循环置脏。守阵 test_web.py 两用例(直推 publisher 抬 revision → flush 置位
  group_view_dirty / 重建后基线前移不再置脏, 红验过)。坑档
  [pitfalls/backend/hot-reload-stale-bindings-derived-views.md](../pitfalls/backend/hot-reload-stale-bindings-derived-views.md);
  档案 [tasks/26-10-03-backend-hr-hotreload-stale-display](../tasks/26-10-03-backend-hr-hotreload-stale-display.md)

- WEB UI **多选右键菜单四项(限速/移动/跳检/导出 .torrent)+ 跳检菜单开关 `web.skip_check_menu`**
  (2026-10-02/03, 计划 [plans/26-10-02-1955](../plans/26-10-02-1955-plan-webui-multi-ctx-actions.html),
  五波六提交; 拍板 D1=A 前端循环(推翻推荐的后端 zip, 归档端点未建) / D2=是 fail-closed / D3=留空不改):
  W1 配置键全链路(models/loaders/validate/GUI schema/minimal.yml/keys.md/键面 fixture, `b71e1291`)+
  `GET /api/webui/flags` 端点、skip-check 端点 403 gate(只放 web 入口, rule 源零改动)、前端 flags
  显隐门控(v-if 对 undefined 静默隐藏)(`dff534b6`); W2 批量限速/移动(bulk 扩 limits/location,
  qbapi 原生收 hash 列表单次调用, 对话框前置不做乐观贴片, 留空方向不进载荷, `a4bfabbf`); W3 批量跳检
  (bulk 扩 skip_check 走 ops 逐 hash 串行聚合回执, danger 确认框, 复用跳检开关, `f5f62726`); W4 多选导出
  (`exportMulti` 按 selHashSet 全量展开含组选中, 前端循环逐个下载, 零后端改动, `4c0c6f66`); W5 冒烟走查
  汇总(`ui_harness.py` 跳检开关两态参数化 `--skip-check-menu` + `ui_smoke.cjs` 补多选四项齐/单选跳检项/
  确认后提交 bulk(action=skip_check)/限速与导出成功回执 toast/off 态 fail-closed 精简轮, on/off 双皮肤
  实跑, `9f1e2a32`)。test.full **2309 passed + 3 skipped / 99%**(32.13s, 基线
  [26-10-03-0542](../testing/baselines/26-10-03-0542-webui-multi-ctx-actions-done.md));
  档案 [tasks/26-10-02-webui-multi-ctx-actions](../tasks/26-10-02-webui-multi-ctx-actions.md);
  真机走查(用户自配 `web.skip_check_menu: true` 后)待用户执行

- WEB UI **HR 站点状态区展示二轮改造**(2026-10-02/03, 计划
  [plans/26-10-02-1936](../plans/26-10-02-1936-plan-webui-hr-status-display-rework.html),
  5 决策点拍板: ①用户改判「展开即覆盖式全屏, 不另设全屏钮」(原推荐覆盖式机制保留),
  ②a③a④a⑤a 按推荐): ①后端明细行只读标记 `local_present` —— `webui/server/routes/hr.py::
  mark_local_present` 单点(响应层 join `manager.store.by_hash`, infohash v1→v2 顺序 casefold
  探测; 本地存在含暂停 = 做种中, 不存在 = 老旧; 不落盘不进轮询载荷), 「毕业」用户可见 4 处
  改「已达标」(status.py:51,66 / resolve.py:234,350 / events.py:109), 注释按拍板②保留
  (`b50c2873`); ②站点状态块默认折叠(头部摘要行, hubGo 打开分区不再自动拉数只复位折叠态)
  + 「展开」即 fixed 覆盖式全屏弹窗(`.hr-full-mask`/`.hr-full-modal` 三套 UI CSS 成对, 让出
  顶栏/状态栏, 单节点 v-show 不搬 DOM, ESC/✕/遮罩三路关闭 —— ESC 挂 lifecycle 退栈链对话框
  层级、先于 26-10-02-1632「清全部面筛」兜底, dialogs.js escBusy 名单同步; 首次展开才拉数,
  折叠态点立即拉取/刷新 = 顺手展开再拉)(`888a0e29`); ③表① 前端老旧过滤(默认只看做种中,
  与档位 chips AND, 空态文案区分两口径)+ 十列三态排序(对齐 shared/sort.js 范式, 模块级纯
  函数比较器, 空值恒末位, 箭头复用 sprite 双图标)+ 三列重组(档位徽章 / 核实结论徽章 +
  「来源人话 · 时刻」副行 / 在列「在列 | 失踪 N 波」徽章 + 「观察期 · 最近被见到」副行,
  0 哨兵纪律不变)(`8cb2da59`); ④守阵复核 5 项(全屏 CSS 成对 / 默认折叠 / 毕业文案零残留 /
  三态比较器 / 无原生 title)零缺口(`ca77ff23`)。阶段 2/3 各做三套 UI 真浏览器目检(桩数据);
  atlas `.hb-cut` clip-path 裁剪 fixed 后代坑独立入档
  [pitfalls/web-ui/clip-path-clips-fixed](../pitfalls/web-ui/clip-path-clips-fixed.md)。
  test.full **2309 passed + 3 skipped / 99%**(34.59s, 基线
  [26-10-03-0440](../testing/baselines/26-10-03-0440-webui-hr-status-display-rework-done.md));
  档案 [tasks/26-10-02-webui-hr-status-display](../tasks/26-10-02-webui-hr-status-display.md);
  真机走查(真实 qB + HR 数据)待用户执行。
  **文案两轮修订**(2026-10-03): ①「显示老旧种子」→「显示未做种」(回应取证报告 B1);
  ②用户二次驳回「未做种/只看做种中」——「未做种」实为**本地已删除**(非"没在做种"),
  「做种中」反向态**含暂停/异常**, 定为「显示已删除种子 (N) / 只看本地仍在列 (M)」(空态
  文案与注释/守阵标签同步换词, 内部标识符 `oldOn` 族保留; 守阵加旧措辞零残留断言);
  test.full 2416 passed + 3 skipped / 99%(基线 [26-10-03-2335](../testing/baselines/26-10-03-2335-webui-hr-deleted-label.md))。

- WEB UI **HR 排除辅种补悬停弹窗**(2026-10-02): 已外迁 → [implemented-webui-history.md](implemented-webui-history.md)(cap 轮转, 事实不变)

- WEB UI **ESC 兜底清全部面筛**(2026-10-02): 已外迁 → [implemented-webui-history.md](implemented-webui-history.md)(cap 轮转, 事实不变)

- WEB UI **Shift 连选起点与键鼠联动统一**(2026-10-02): 已外迁 → [implemented-webui-history.md](implemented-webui-history.md)(cap 轮转, 事实不变)

- WEB UI **HR 在线核实详情两张表**(2026-10-01): 已外迁 → [implemented-webui-history.md](implemented-webui-history.md)(cap 轮转, 事实不变)

- WEB UI **设置页只读字段(程序托管/R 级)**(2026-10-01): 已外迁 → [implemented-webui-history.md](implemented-webui-history.md)(cap 轮转, 事实不变)

- WEB UI **web.token 生成改走 atomic_write**(2026-10-01): 已外迁 → [implemented-webui-history.md](implemented-webui-history.md)(cap 轮转, 事实不变)

- WEB UI **标签列全量展开, 移除「+1/+2」折叠**(2026-09-30): 已外迁 → [implemented-webui-history.md](implemented-webui-history.md)(cap 轮转, 事实不变)

- WEB UI **键盘快捷键全量落地(可自定义)**(2026-09-30, plans/26-09-28-0354 W1-W7 两波): 已外迁 → [implemented-webui-history.md](implemented-webui-history.md)(cap 轮转, 事实不变)

- WEB UI **做种时长列/弹窗的「要求」显示修复**(2026-09-29): 已外迁 → [implemented-webui-history.md](implemented-webui-history.md)(cap 轮转, 事实不变)

- WEB UI **前端大文件拆分 + 单一语义模板收敛 + 内核续拆**(2026-09-27, plans/26-09-26-2233 五波全落地): 已外迁 → [implemented-webui-history.md](implemented-webui-history.md)(cap 轮转, 事实不变)

- WEB UI **自绘悬浮提示 .aq-tip**(2026-09-28): 已外迁 → [implemented-webui-history.md](implemented-webui-history.md)(cap 轮转, 事实不变)

- WEB UI **设置页分类回归修复: 「常规/日志」成块 + 运行日志默认折叠**(2026-09-28): 已外迁 → [implemented-webui-history.md](implemented-webui-history.md)(cap 轮转, 事实不变)

- WEB UI **搜索框语法帮助入口: 框内幽灵「?」+ 锚定浮卡(方案A)**(2026-09-28): 已外迁 → [implemented-webui-history.md](implemented-webui-history.md)(cap 轮转, 事实不变)

- WEB UI **多选右键菜单作用于整个选中集合**(2026-09-24, 已入库 `907890b`): 已外迁 → [implemented-webui-history.md](implemented-webui-history.md)(cap 轮转, 事实不变)
- WEB UI **右键次级菜单三修**(2026-09-25, 已入库 `3a8dabd`): 已外迁 → [implemented-webui-history.md](implemented-webui-history.md)(cap 轮转, 事实不变)

- WEB UI **搜索负词种子级定案: 任一候选行含负词 ⇒ 整种子排除**(2026-09-26/27): 已外迁 → [implemented-webui-history.md](implemented-webui-history.md)(cap 轮转, 事实不变)

- WEB UI **搜索匹配收敛服务端单点: 三页(辅种/种子/追剧)统一消费 searchHits**(2026-09-26 晚): 已外迁 → [implemented-webui-history.md](implemented-webui-history.md)(cap 轮转, 事实不变)

- WEB UI **搜索查询语法强化: 词 AND + `-排除` + `"短语"`(行级语义)**(2026-09-26): 已外迁 → [implemented-webui-history.md](implemented-webui-history.md)(cap 轮转, 事实不变)

- WEB UI **做种时长悬停弹窗(T3 进度仪表)**(2026-09-26): 已外迁 → [implemented-webui-history.md](implemented-webui-history.md)(cap 轮转, 事实不变)

- WEB UI **设置页分组合并: 日志/界面(WebUI)/通知/运行日志 并入「常规」**(2026-09-26): 已外迁 → [implemented-webui-history.md](implemented-webui-history.md)(cap 轮转, 事实不变)

- WEB UI **种子级标签/分类即时编辑**(2026-09-26): 已外迁 → [implemented-webui-history.md](implemented-webui-history.md)(cap 轮转, 事实不变)

- WEB UI **一键导入缺失站点**(2026-09-26): 已外迁 → [implemented-webui-history.md](implemented-webui-history.md)(cap 轮转, 事实不变)

- WEB UI **站点接入数据白屏修复**(2026-09-25): 已外迁 → [implemented-webui-history.md](implemented-webui-history.md)(cap 轮转, 事实不变)
- WEB UI **HR 删除安全档位呈现**(2026-09-25): 已外迁 → [implemented-webui-history.md](implemented-webui-history.md)(cap 轮转, 事实不变)
- WEB UI **设置页控件两处打磨**(2026-09-25): 已外迁 → [implemented-webui-history.md](implemented-webui-history.md)(cap 轮转, 事实不变)
- WEB UI **设置页合一: 移除经典设置页**(2026-09-25): 已外迁 → [implemented-webui-history.md](implemented-webui-history.md)(cap 轮转, 事实不变)

> 注意区分: 下表部分功能作者在 README 中标注 🚧 = "已实现但未严格测试(实盘验证)", 如规则引擎的条件/动作/checking/去重语义等 — 有单测但作者尚不认为经过严格验证; 此类 🚧 ≠ 未实现, 勿移除 (语义详见 pitfalls.md)。
- **2026-09-21 设置页新版(Console Hub)落地**(含版式硬知识: 派生变量声明在使用层 / 发光负 spread / 切角与发光互斥; 无浏览器验证手段)与计划外发现(setUnitNum computed 误用, 已随经典页移除)**: 已外迁 → [implemented-webui-history.md](implemented-webui-history.md)(cap 轮转, 事实不变)
- **2026-09-19 打开目标文件夹修复 / 2026-09-18 视图重建收口·错误原因显示 / 2026-09-15 追剧视图 / 2026-09-17 第 9/10/11 轮修复 / 2026-09-15 三条(双界面命名目录化/旧版第八轮优化/新版界面与多主题)**: 已外迁 → [implemented-webui-history.md](implemented-webui-history.md)(cap 轮转, 事实不变)
