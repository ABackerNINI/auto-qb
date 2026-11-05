# 已实现 · WEB UI 历史轮次(外迁流水)

> 摘要: implemented-webui.md 超 cap 后外迁的早期长条目(2026-09-15 三条 + 2026-09-17 第 9/10/11 轮修复 + 2026-09-18/19 四条 + 2026-09-24/25 五条 + 2026-09-26 四条 + **2026-10-03 续迁 2026-09-26~10-02 十六条** + **2026-10-05 续迁 2026-10-02~10-04 十三条**) —— 冷库流水; implemented-webui.md 再超 cap 时最老条目续迁至此, 新条目仍回 implemented-webui.md。 2026-11-05 起前述更早条目再外迁至 attachments/implemented-webui-history-2026-09-10-03.md(47 条)。
> 触发: 第九轮, 第十轮, 第十一轮, FX-01, R10-16, 历史流水, 外迁, 键盘快捷键, 前端文件拆分, 搜索语法, 设置页分组合并
> 2026-09-15 ~ 2026-10-03 的 **47** 条记录已外迁(2026-11-05 log 轮转, 原文逐字): 见 [attachments/implemented-webui-history-2026-09-10-03.md](attachments/implemented-webui-history-2026-09-10-03.md)

- **WEB UI 种子详情抽屉重设计: 浮层 → 底部停靠属性面板 (方案A)**(2026-10-03, 计划
  [plans/26-10-03-0917](../plans/26-10-03-0917-plan-webui-drawer-redesign.html) 五波, 提交链 `dadc97a6`/`7d38e2ea`/`14a4d0e2`/`54d8b6fc`,
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
  全量 **2329 passed + 3 skipped / 99%**(基线 [testing/baselines/26-10-03-1335](../testing/baselines/attachments/26-10-03-1335-webui-drawer-redesign-w4-done.md));
  冒烟走查单 24 项 × 三皮肤全过; 档案 [tasks/26-10-03-webui-drawer-redesign](../tasks/26-10-03-webui-drawer-redesign.md)

- **WEB UI 站点级「显式空 = 覆盖为空」三态 + 「跟随全局」删键: 删除类标签全局/站点作用域混淆修复**(2026-10-03, issue 26-10-01-2129 方案 B 完整形态, 三阶段提交 `18bde39c`/`42d3d90a`/`9c6bc499`): 根因三层(config 层 `_strip_none` 使 str/list「显式空=未定义」坍缩 / bool 开关恒写值从不删键单向锁死 / 回填用 schema 默认非全局生效值), 用户拍板 B 完整形态 + 配置版本升级。config 层: `Field.tri_state` 属性 + 4 站点 str 键标三态(hr.add_tag / add_category / add_tag_for_satisfied / add_category_for_satisfied)+ `_strip_none` 站点段豁免保 '' + validate 放行 + **配置 v3→v4 迁移**(经 infra.versioning 新增 migrate_with_notes 汇聚)清存量 '' 并逐键 WARNING, ruamel round-trip 保 '' 实测无损; keys.md / docs/configuration.md 同步。显示层: config_editor.js `SITE_FALLBACK_GLOBAL` 7 键回退链表 + cfgSiteFallbackPath/cfgFallbackValue 生效值回填 + siteBadge「站点/全局」来源徽标(站点 '' 原样显示)+ cfgIsDefault 链上键抑制「默认」矛盾徽标; 三皮肤零成对改。交互层: 「跟随全局」按钮接线死代码 cfgResetField/cfgDelPath(confirm danger + toast), str「清空保存=覆盖为空」与「跟随全局=删键」两动作区分, 9 键 help 三态文案(schema/trackers.py), 内联开关 tooltip risk+help 并接修复。守阵: config 层 v3→v4 迁移用例; 冒烟 118/118(atlas/prism/console, bool 三态走全 / str 覆盖为空 vs 删键 / 徽标回退链)。全量 **2325 passed + 3 skipped / 99%**(基线 [testing/baselines/26-10-03-0913](../testing/baselines/attachments/26-10-03-0913-webui-delete-tag-scope-confusion-done.md)); 档案 [tasks/26-10-03-webui-delete-tag-scope-confusion](../tasks/26-10-03-webui-delete-tag-scope-confusion.md); 报告 [reports/26-10-03-0504](../reports/26-10-03-0504-report-webui-site-scope-confusion.html); **随实施提交已入库**

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
  汇总(`ui_harness.py` 跳检开关两态参数化 `--skip-check-menu` + 冒烟脚本补多选四项齐/单选跳检项/
  确认后提交 bulk(action=skip_check)/限速与导出成功回执 toast/off 态 fail-closed 精简轮, on/off 双皮肤
  实跑, `9f1e2a32`)。test.full **2309 passed + 3 skipped / 99%**(32.13s, 基线
  [26-10-03-0542](../testing/baselines/attachments/26-10-03-0542-webui-multi-ctx-actions-done.md));
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
  [26-10-03-0440](../testing/baselines/attachments/26-10-03-0440-webui-hr-status-display-rework-done.md));
  档案 [tasks/26-10-02-webui-hr-status-display](../tasks/26-10-02-webui-hr-status-display.md);
  真机走查(真实 qB + HR 数据)待用户执行。
  **文案两轮修订**(2026-10-03): ①「显示老旧种子」→「显示未做种」(回应取证报告 B1);
  ②用户二次驳回「未做种/只看做种中」——「未做种」实为**本地已删除**(非"没在做种"),
  「做种中」反向态**含暂停/异常**, 定为「显示已删除种子 (N) / 只看本地仍在列 (M)」(空态
  文案与注释/守阵标签同步换词, 内部标识符 `oldOn` 族保留; 守阵加旧措辞零残留断言);
  test.full 2416 passed + 3 skipped / 99%(基线 [26-10-03-2335](../testing/baselines/attachments/26-10-03-2335-webui-hr-deleted-label.md))。

