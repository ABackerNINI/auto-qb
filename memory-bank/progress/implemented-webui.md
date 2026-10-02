# 已实现 · WEB UI(界面 / 视图 / 状态色)

> 摘要: 摘要: 前端界面与视图的落地记录 —— 设置页 / 追剧视图 / 双界面 / 错误原因 / 各轮修复。
> 触发: WEB UI 做过没有, 前端功能, 设置页, 视图, 状态色, 修复轮次, 双界面

## 已实现 (✅, 有单测覆盖)

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
  真机走查(真实 qB + HR 数据)待用户执行

- WEB UI **HR 排除辅种补悬停弹窗**(2026-10-02): 2026-09-29 做种时长列非文字化清理撤原生 title
  「已排除」提示后弹窗侧未接盘 —— 命中 HR 排除表(exclude_categories/exclude_tags)的辅种 hover
  完全真空(排除态 hr_safety 组装层短路空串, hrPopData 对空档位一律不弹)。后端 record.py 排除
  匹配收敛单点 `_hr_exclusion_hits`((标签命中, 分类命中)), 新增 `hr_excluded_by()` 来源 token
  (tag/category/tag+category, 与 hr_excluded 同单点恒一致), `hr_view_fields` 双分支透出
  `hr_excluded_by`; 前端 hrPopData 排除行分支 —— 「已排除出 HR 管理」+ 依据行「命中 HR 排除表的
  分类规则/标签规则/标签与分类规则」(`HR_EXCLUDED_BY_TEXT` 映射, 前端不重算匹配纪律不变),
  无轨道/站点值(排除行本就无, 画要求轨反误导为仍受管束); 三主题 CSS 成对新增
  `.hp-dot/.hp-verdict.excluded` 中性灰档(--fg-muted, 不占四档安全色); 种子页/辅种组成员行/
  追剧集行共用弹窗单点一处修三处生效。守阵: testhr_view_fields_excluded 扩展三命中形态 + 空配置
  键集; record 排除三测补 token 断言; 接线守阵 CSS 成对清单 +2; FakeTorrent 鸭子兼容补
  hr_excluded_by(裸替身直喂 _build_group_view 两场景全量暴露)。test.full **2292 passed +
  3 skipped / 99%**(27.5s @ f0c0f0ed, 基线 26-10-02-1956); 档案
  [tasks/26-10-02-webui-hr-excluded-hover-pop](../tasks/26-10-02-webui-hr-excluded-hover-pop.md)

- WEB UI **ESC 兜底清全部面筛**(2026-10-02, 清偿 question issue
  [26-10-01-2108](../issues/26-10-01-2108-question-webui-esc-clear-filter.html), 计划
  [plans/26-10-02-1632](../plans/26-10-02-1632-plan-webui-esc-clear-filters.html) 拍板方案 A):
  ESC 不进引擎键表(方案 B 双触发 + fixed 语义崩坏, 已否决), 接 lifecycle.js 退栈链**终端兜底**
  —— 16 层浮层 pop 与既有 4 兜底全部走完仍无层可退, 且门五件套(`authOk` / `page === "groups"` /
  无 hrPop 卡 / 非输入态 inInput / `facetsActive`)全过时清全部面筛 + toast 点名「已清除全部筛选
  (搜索词保留)」; filters.js 新增 computed `facetsActive`(与 clearFilters 字段清单同源,
  **不含 searchQuery** —— filtersActive 含搜索词不能当门); 键表零改动, `clear-filters` 保持空位
  供自定义, `clear-esc` label 补「清筛选」, shortcuts.js 三处文案。守阵 test_web_shortcuts.py
  新增 `test_esc_chain_clear_filters_fallback`(链序 / 门条件五件套 / Escape 唯一默认绑定 /
  facetsActive 纯度); 桩服务走查 8/8 项 / 34 断言通过(IME 组合态 CDP 真实组词态验证);
  档案 [tasks/26-10-02-webui-esc-clear-filters](../tasks/26-10-02-webui-esc-clear-filters.md);
  **已入库 `0d286cc5`**

- WEB UI **Shift 连选起点与键鼠联动统一**(2026-10-02, 计划
  [plans/26-10-02-0608](../plans/26-10-02-0608-plan-webui-shift-anchor.html) 方案 B, 用户指令
  「按推荐实施计划」直接拍板 + 4 决策点按建议案): 修「鼠标点过第 5 行, 按 Shift+↓ 却从**列表第一行**
  起选」—— 根因是方案 B 只统一了**光标**(`kbCursor`), 区间**起点**(`selAnchor*`)仍是另一套状态机
  (仅 Ctrl/⌘ 点击与展开写入), 为空时四处消费者一律兜底 `list[0]`。修法四条: ①起点解析/写入单点
  `_selAnchor(kind, list)` / `_selSetAnchor(kind, id)`(`selection.js`), 兜底链 **显式锚点 → 当前光标
  → [group: 展开的组] → 列表首行**, `shiftGroupSel`/`shiftMemberSel`/`shiftTorrentSel`/`_extendUnit`
  四处改调用, 消掉「四处各写一遍 `list[0]`」的口径漂移源; ②五个点击入口普通/Ctrl 路径补落起点,
  **`!event.shiftKey` 守卫排除 Shift**(法则 2: 起点在扩展期间不动, 否则 Shift+点击只选目标单行);
  ③`shortcuts.js` 新增 `_selSeedAnchorFromCursor`, `_kbExtend` 在 `_kbMove` **之前**以当前光标落
  「手势原点」(已有有效起点则不动); ④追剧页起点缺失改走 `_selAnchor("unit", units)` 形成区间, 不再
  退化为单单元切换。**行为口径未变**: 普通点击仍不选中(只写 `selAnchor*`) / 滚动仍只在键盘路径 /
  禁 `scrollIntoView` / FX-11 互斥清理不变 / 无 Python src·配置键·后端改动。守阵
  `test_web_shortcuts.py` 18 → 19(`test_shift_anchor_unified`); test.full **2290 passed + 3 skipped /
  99%**(基线 [testing/baselines/26-10-02-0635](../testing/baselines/26-10-02-0635-webui-shift-anchor.md));
  档案 [tasks/26-09-28-webui-keyboard-shortcuts](../tasks/26-09-28-webui-keyboard-shortcuts.md); **已入库 `fa79d526`**

- WEB UI **HR 在线核实详情两张表**(2026-10-01/02, 清偿 issue
  [26-10-01-2137-feat-webui-hr-detail-table](../issues/26-10-01-2137-feat-webui-hr-detail-table.html),
  计划 [plans/26-10-01-2216](../plans/26-10-01-2216-plan-webui-hr-detail-table.html) 拍板六项全按推荐):
  ①后端导出单点 `hr/status.py` `EntryDetail`/`entry_details()`(P0+P1 全集, 人话字段后端算好,
  档位·下载量排序含失踪行)+ 只读端点 `GET /api/hr/sites/{site}/entries`(未启用 400 / 未接入 404 /
  线程未启动 409; f5ce07bd); ②站点卡片**表① 全量详情表**(打开分区/手动刷新各拉一次不轮询,
  档位筛选 chips 本地过滤, 「数据截至」时间戳, 「上次核实(放行判定)」独立口径, 单元格不挂原生 title;
  d3d4d987); ③**表② 排障视图**(站点级 kv 行 `hrsKvRows` 拼行单点 + 各档波次明细, 原生 `<details>`
  默认收起, 数据全来自 /api/hr/status 零新请求, 展开态不持久化; b2b1e96d); `.hr-detail-table` 等
  三套 UI CSS 成对。阶段4 契约守阵 `test_frontend_hr_contract_keys_match_backend`(前端消费键 ⊆
  后端 to_dict 键集)钉两表字段面; 基线数字见 `commands run kb.baseline`;
  档案 [tasks/26-10-01-webui-hr-detail-table](../tasks/26-10-01-webui-hr-detail-table.md); **随本提交入库**

- WEB UI **设置页只读字段(程序托管/R 级)**(2026-10-01, 清偿 issue
  [26-09-28-2135-feat-webui-readonly-fields](../issues/26-09-28-2135-feat-webui-readonly-fields.html)):
  schema_version/data_dir/state_file/fs 段此前渲染为可编辑但保存必然被盖章/回退, 反馈还谎报「需重启才生效」。
  修法五条: ①`Field` 加 `readonly` 标志 + 四点位打标(fs 段与叶子 path_map 双标, 前端叶子只认自身标)
  + `readonly_config_paths()`; ②CE_FIELD_BASE 三 computed(readonly/readonlyComplex/readonlySummary),
  hub-field 只读摘要分支(fs.path_map 渲染「from: … · to: …」映射对, 替换 `[object Object]` text 控件)
  + 全控件 `:disabled` + 「程序维护」徽标 + settings-detail 块级 section 开关收口; ③cfgSave 反馈口径改
  「程序托管字段, 仅能在配置文件中修改, 本次未写入」; ④writer `_fallback_readonly_fields` 键面防线
  (schema_version 豁免 —— 盖章承担其只读, 回退会吞「高于本程序支持」精确错); ⑤守阵 +5(writer 3 /
  schema 1 / web 静态 1)。真浏览器定向验证徽标/禁用/摘要全符合设计。test.full **1929 passed + 3 skipped / 91%**
  (基线 [testing/baselines/26-10-01-2250](../testing/baselines/26-10-01-2250-webui-readonly-fields.md));
  档案 [tasks/26-10-01-webui-readonly-fields](../tasks/26-10-01-webui-readonly-fields.md); **随本提交入库**

- WEB UI **web.token 生成改走 atomic_write**(2026-10-01, 清偿 issue
  [26-09-21-1347-bug-web-token-non-atomic-write](../issues/26-09-21-1347-bug-web-token-non-atomic-write.html)):
  ensure_web_token 原用 O_TRUNC 直写, 生成瞬间非优雅终止会留下非空半截 token 被持久化 ⇒ 已存浏览器密钥 401。
  修法 = 改走 utils.atomic_write 单点(mkstemp 默认 0600, 落盘字节逐字节等价), 读取侧零改动;
  守阵暂不并入 O_TRUNC 静态扫描(hr/channel.py:104 同族直写未清, 待一并收)。守阵 +3(test_web:
  生成可读回 / 已有 token 不漂移 / 写一半中断自愈)。**已入库 `5965cc07`**(W2 清偿 1/3)

- WEB UI **标签列全量展开, 移除「+1/+2」折叠**(2026-09-30): 用户要求标签不再折叠。4 处模板(种子明细 / 组级+组内成员 / 追剧集行)去 `tagSlice(...,3)`/`slice(0,3)` 截断与 `+N` 徽标, 改 `v-for` 全量渲染; 三皮肤 `.g-tags, .m-tags` 加 `flex-wrap: wrap`(行高逐行实测的虚拟滚动承接变高行), 清 `.tag-more` 死样式; `decorate.js` 删 `tagSlice()`。单个超长标签仍 ellipsis(完整值在悬浮)。纯前端改动, 无 Python 源改动; 档案 [tasks/26-09-30-webui-tags-unfold](../tasks/26-09-30-webui-tags-unfold.md); **随本提交入库**

- WEB UI **键盘快捷键全量落地(可自定义)**(2026-09-30, plans/26-09-28-0354 W1-W7 两波): ①引擎 `shared/shortcuts.js` 注册表单一事实源 55 条(e.code+固定修饰序归一化 / IME isComposing+229 双保险 / 输入元素+模态层屏蔽 / repeat+纯修饰键+defaultPrevented 前置 / 浏览器保留键黑名单 Ctrl+W/T/N/Q 族; 适配器 `window.AQB_KEYS` 单一存储出口) ②光标模型 kbCursor 按身份不按下标(滚动进视口走 getBoundingClientRect 差值+`_rowPre` 前缀和, **禁 scrollIntoView**; 26-09-30 方案 B 键鼠衔接追加: selection.js 五个点击入口按所在行回写 kbCursor —— 落光标≠选中, 无光标回落改**视口就近行** `_kbViewportRow`, 明细成员行补 kb-cursor 视觉, 守阵 test_click_lands_cursor_and_viewport_fallback) ③`commands._actCore` 统一动作出口(act/actTorrent/bulkAct/actEpisode 四入口收敛) ④默认键位 A-I 组(§08 v4 危险档一律二键组合: 删除 Shift+D/重新校验 Shift+Y/强制汇报 Shift+A + 确认框默认「确定」Enter 确认; Delete 键额外删除入口直连 `_deleteFlow` 注册表外; E 组 Shift 族/F 组队列开关/G 组局部作用域 Alt+1-4+设置页 Ctrl+S inputSafe/H 组帮助浮层 Shift+Slash) ⑤作用域五值(global/list/drawer/settings/modal)全量生效, 模态白名单分流 ⑥后端持久化: `routes/keys.py` GET/PUT `/api/keys`(存储 `auto-qb-data/webui-keys.json` 与 web.token 同寻址, 读时兜底链 主文件→.bak→默认表, PUT 结构校验 422, 金清单 +2; 存储定案=后端独立文件, 决策点⑥) ⑦自定义面板: 设置页「快捷键」分区(按下即录录制器捕获段监听/纯修饰键拒收/黑名单拒绑/冲突三选一 交换-覆盖对方置空-取消/单条全部重置/空串=显式禁用/保存失败本地回滚/离开未保存先确认)+ 帮助浮层只读速查。守阵 test_web_shortcuts.py 16 条 + test_web.py keys 后端 5 条; 探针 28 项全过。全量 **1813 passed + 3 skipped**(TOTAL 91%, 基线 [26-09-30-0555 W1-W4](../testing/baselines/26-09-30-0555-webui-keyboard-w1w4.md) / [26-09-30-0702 W5-W7](../testing/baselines/26-09-30-0702-webui-keyboard-w5w7.md)); 档案 [tasks/26-09-28-webui-keyboard-shortcuts](../tasks/26-09-28-webui-keyboard-shortcuts.md); W1-W4 **已入库 `38ffec5`**, W5-W7 **未提交**

- WEB UI **做种时长列/弹窗的「要求」显示修复**(2026-09-29): 用户实报未核/在线行不显示要求时间、只剩孤立的「未核」芯片。定位为两处**渲染门**(纯前端, 判定与字段未动): ①三份模板 `.req` 只在 `hr_triggered` 为真时渲染 ⇒ 未触发行连配置事实(要求时长)一起被藏; ②`hr.js` 弹窗把 `unverified` 与真放行/免罪同类收起成「无时长要求」徽记(而它 `hr_req_time=115200s` 确有要求)。修复: 要求门只认「已做种非空 + `hr_req_time`」; 收起条件只留 `site_released`/`site_exempt`(义务已了), 未核实改画本地轨。**现象属「上游修好后才被点亮」** —— 前几轮修好 HR 视图发布后 `hr_safety` 从空变有值, 此前不可达的芯片/弹窗分支第一次上线(教训入 [pitfalls/web-ui/contract-api.md](../pitfalls/web-ui/contract-api.md))。守阵 `test_frontend_hr_safety_wiring` 增两条断言(回退即红)。全量 **1747 passed + 4 skipped**(TOTAL 91%, 基线 [testing/baselines/26-09-29-1920-webui-hr-duration-req](../testing/baselines/26-09-29-1920-webui-hr-duration-req.md)); 档案 [tasks/26-09-29-webui-hr-duration-req](../tasks/26-09-29-webui-hr-duration-req.md); **未提交**

- WEB UI **前端大文件拆分 + 单一语义模板收敛 + 内核续拆**(2026-09-27, plans/26-09-26-2233 五波全落地): ①模板: 两套 index.html(2555/2613 行)→ shell(166/177 行)+`shared/tpl/*.html` 14 分片**单一语义源** + `shared/boot.js` 按清单 fetch 注入(失败显式占位+停止); 双模板副本消灭, 模板级 UI 差异唯一入口 = `v-if="ui === 'atlas'|'prism'"` 条件块 + `ui-diff:` 注释(守阵收集为活差异清单, 现存 1 条: 棱镜主题切换器) ②样式: atlas style.css 1720 → 令牌+基线留根 200 + `css/{components,views,dialogs}.css`(全 ≤700, 连续字节切片级联序不变) ③内核: app.js 1281→411(常量单点+接线), `state.js`(data/computed/watch)/`lifecycle.js`(生命周期)经 `...window.X` 展开进**根组件选项**(不许 app.mixin —— 波及 hub-field 实例), `auth.js`/`polling.js`/`view.js` 走全局 mixin 方法域 ④守阵: 13 处直读改聚合读法 + 新增分片接线/差异口注册表/双 shell 清单一致性/整包成员查找 + JS 接线形态④。等价证明 = 切割聚合字节自验 + 真 API stub 冒烟改造前后渲染 DOM 双 UI 逐字节一致; 全量 **1688 passed + 1 skipped**(TOTAL 91%, 基线 [testing/baselines/26-09-27-1305-webui-kernel-split](../testing/baselines/26-09-27-1305-webui-kernel-split.md)); 计划 [plans/26-09-26-2233](../plans/26-09-26-2233-plan-webui-frontend-file-split.html); 档案 [tasks/26-09-26-webui-frontend-file-split](../tasks/26-09-26-webui-frontend-file-split.md); **已入库 `6fd1331`(三层拆分)/`aeca1fb`(收敛), 内核拆分随本批提交入库**

- WEB UI **自绘悬浮提示 .aq-tip**(2026-09-28): 原生 title 全局替换为自绘单例 —— `ui_feedback.js` 纯 DOM 委托(摘 title/350ms 延迟弹/收起还原, hasAttribute 探测保 Vue :title 绑定) + `console_hub.css` 发光按钮配方(三皮肤令牌自适应)。机制与配方**事实单点 = conventions/webui.md「WEB UI 悬浮提示 .aq-tip」节**。test.full 1820/3(基线 26-09-28-0744); **已入库 `c64b836f`**(切片 26-09-28-0730 蒸馏至此删除)

- WEB UI **设置页分类回归修复: 「常规/日志」成块 + 运行日志默认折叠**(2026-09-28): 治 26-09-26 分组合并(1905d6d)的回归 —— log/web/notify 三段因 `open=True` 被 cfgFlatten 平铺成无标题同级字段, 全部落进「常规/常规」。修复: 三段去 `open=True` 恢复成块展示(hubBlocks 自动渲染带标题且**永远展开**的块, 分类显性与 2026-09-15 平铺诉求同时满足), label 恢复合并前分组名 日志/WebUI/通知 + 补回旧分组一行 help; 运行日志块默认折叠、首次展开才拉 /api/log(`hubLogsToggle`/`hubLogsLoad`, 折叠态动等级/行数/刷新自动展开再拉), hubGo 去预取; hubHits/hubFieldCount 改递归进块(块内字段不再是展开顶层项); `open` 字段保留为通用能力(现仅 hr_check optional 段在用)。守阵 `test_config_schema_endpoint` 钉尾三段 kind=object 且不声明 open(防 open 平铺回归)。**三套 UI(atlas/prism/console)零成对改**: 设置页同吃 shared/tpl + config_hub.js, console 纯 CSS 换肤, manifest 一致性守阵钉住。全量 **1815 passed + 3 skipped**(TOTAL 91.39%, 基线 [testing/baselines/26-09-28-0212-webui-settings-categorize-logs](../testing/baselines/26-09-28-0212-webui-settings-categorize-logs.md)); 档案 [tasks/26-09-28-webui-settings-categorize-logs](../tasks/26-09-28-webui-settings-categorize-logs.md); **随本提交入库**

- WEB UI **搜索框语法帮助入口: 框内幽灵「?」+ 锚定浮卡(方案A)**(2026-09-28): 3 版交互式提案(计划 26-09-28-0201)用户拍板 A + 占位符简化为「搜索种子或文件名...」。实施: `topbar.html` 「?」恒显于清空钮左侧 + 浮卡(词 AND/`-词`/`"短语"`/`-"短语"` 四行 + 容错提示, 示例行点击回填即搜 `doSearch` + 焦点还输入框); 挂件样式入三 UI 共用层 `shared/console_hub.css`(mono 用 `var(--font-mono, 内联栈)` longhand —— 星图无该令牌, shorthand 遇未定义令牌整条失效), 皮肤差异只留 atlas pill 钮圆与 input 右内边距 52px; `searchHelpOpen` 状态 + `toggleSearchHelp`/`searchHelpFill`(view.js), 收起 = 点空白/Esc(lifecycle 既有链)+ goView/openSettings 导航收起; 守阵 `test_frontend_search_help_wiring`。实机 dev.harness+Playwright 三套 UI 全交互通过(示例 `"web dl"` 真实后端命中 35/60); 全量 **1815 passed + 3 skipped**(TOTAL 91%, 基线 26-09-28-0250); 档案 [tasks/26-09-26-webui-search-query-syntax](../tasks/26-09-26-webui-search-query-syntax.md); **未提交**

- WEB UI **多选右键菜单作用于整个选中集合**(2026-09-24, 已入库 `907890b`): 已外迁 → [implemented-webui-history.md](implemented-webui-history.md)(cap 轮转, 事实不变)
- WEB UI **右键次级菜单三修**(2026-09-25, 已入库 `3a8dabd`): 已外迁 → [implemented-webui-history.md](implemented-webui-history.md)(cap 轮转, 事实不变)

- WEB UI **搜索负词种子级定案: 任一候选行含负词 ⇒ 整种子排除**(2026-09-26/27): 已外迁 → [implemented-webui-history.md](implemented-webui-history.md)(cap 轮转, 事实不变)

- WEB UI **搜索匹配收敛服务端单点: 三页(辅种/种子/追剧)统一消费 searchHits**(2026-09-26 晚): 已外迁 → [implemented-webui-history.md](implemented-webui-history.md)(cap 轮转, 事实不变)

- WEB UI **搜索查询语法强化: 词 AND + `-排除` + `"短语"`(行级语义)**(2026-09-26): 修复「恶女 10」搜不到单文件发布物(旧口径整句归一后连续子串, 两词不连续必不中)+ 新增排除能力。后端 `views.py` 新增 `_parse_query` 纯函数(websearch 宽容词法: 空格分词隐式 AND / 词首 `-` 排除 / `"…"` 短语连续子串 / 孤立 `-`·未闭合引号·纯标点宽容降级, 词法判定在原始查询上进行与归一互不干扰), `search_torrents` 改**行级匹配** —— 候选行 = 归一种子名或单个归一文件名, 行通过 ⇔ 含全部正词且无负词, 种子命中 ⇔ 任一行通过(负词按行作废, 合集包非 DV 行不误杀; 跨行 AND 不命中是与种子级的分界, 26-09-26 拍板); 仅负词查询返回空 + `negative_only` 标记(与 Google 一致, 无正判据无从起搜)。响应加 `negative_only` 键(向后兼容)。前端: 两主题 placeholder 提示语法 + 5 处空态「只有排除词」提示(app.js `searchNegativeOnly` 状态单点)。**真机回访双修(同日)**: ①种子页 `filteredTorrents` 客户端过滤同步升级同语法 —— filters.js `_parseSearchQuery`/`_searchNorm`/`_torrentTextMatch` 单点(字段行级语义: 名称/站点/分类/路径/每标签各为一候选行; 仅负词返回空), hr.js 旧整句版删除, 守阵 test_frontend_search_syntax_wiring 以 vm 沙箱与 views.py **行为级对账**(当场抓到 `_` 折叠漂移; `\W` 会折叠掉 CJK 一并钉死); ②清除钮 `@mousedown.prevent` 两主题成对(focus 宽度过渡把按钮移出光标, 焦点态 click 落空)。+7 测试累计, 全量 **1680 passed + 1 skipped**(TOTAL 91%, 基线 26-09-26-2121); 调研与设计定稿见报告 [reports/26-09-26-1918-report-webui-search-query-syntax.html](../reports/26-09-26-1918-report-webui-search-query-syntax.html); 档案 [tasks/26-09-26-webui-search-query-syntax](../tasks/26-09-26-webui-search-query-syntax.md)

- WEB UI **做种时长悬停弹窗(T3 进度仪表)**(2026-09-26): 已外迁 → [implemented-webui-history.md](implemented-webui-history.md)(cap 轮转, 事实不变)

- WEB UI **设置页分组合并: 日志/界面(WebUI)/通知/运行日志 并入「常规」**(2026-09-26): 设置首页 10 张卡 → 6 张(常规/自动化/HR 在线核实/限速/站点/规则)。单点改动在 schema `groups.py`(log/web/notify 三段整段搬进 basic 组, 三个独立分组删除), 两套 UI 首页卡/搜索/富说明经 schema 派生自动跟随; config_hub.js 删 `__logs` 特制卡与分支(运行日志块移入常规分区页尾, 打开分区拉一次不轮询; 存量浏览器偏好 `__logs` 由 hubRestore 映射进 basic; web.host 暴露警示 LED 挪到常规卡; HUB_HELP 交叉引用「界面 →/通知 →」改「常规 →」); atlas/prism 模板成对改(`__logs` v-else-if 分支删除, v-if 链保持合法); web 段 label「WEB UI」→「WebUI」; `validate_config` 键集合不动(test_config_schema 守卫对齐)。守阵 test_web::test_config_schema_endpoint 同步新分组表 + 钉 log/web/notify 并入 basic 尾部。全量 **1665 passed + 1 skipped**(TOTAL 92%, 合并工作树重测, 含并行入库的 versioning/button 测试); 档案 [tasks/26-09-26-webui-settings-group-merge](../tasks/26-09-26-webui-settings-group-merge.md); **未提交**

- WEB UI **种子级标签/分类即时编辑**(2026-09-26): 补上"对种子加/删标签、设置分类"的用户能力 —— `/api/torrents/bulk` 动作表扩 `add_tags`/`remove_tags`/`set_category`(载荷加 `tags`/`category` 键, **提供才透传**, 空串分类=qB"清除分类"语义; `_BULK_ACTIONS` lambda 统一 4 参带 `extra`, 既有 4 动作忽略它; `bulk_torrents` 本就在 RESYNC/延迟回执两名单, 新动作零白名单改动自动继承补刷新与聚合回执), QbApi 侧三个方法早已就绪且同步 store 快照。前端「标签/分类」**即时编辑对话框**(shared/dialogs.js): 目标集合打开时锁定(批量 = `_bulkTargets()` 整个选中集合 / 单种子 = menu.hash), 全部标签以 `.opt-pill` 切换胶囊展示(亮 = 选中种子**共同拥有**, 点击即投递一条 bulk 命令), 分类 combobox 现有分类选择 + 自由输入(新分类/新标签**先建后设**, create 失败不阻断, 主循环 FIFO 保证顺序); 共同标签取交集但**不过滤站点同名标签**(那条是组级展示口径, 编辑场景要能移除它们)。三处入口双 UI 成对: 批量浮条按钮 / 批量右键菜单(CTX-03 链路 ctxMeta) / 单种子右键菜单(一级, 与限速/移动/重命名同级); `.opt-pill` 组件 atlas 首次引入(照 prism 同源搬入)。+3 测试, 全量 **1638 passed + 1 skipped**(TOTAL 92%); 双 UI 浏览器冒烟通过(harness 桩); 档案 [tasks/26-09-26-webui-torrent-meta-edit](../tasks/26-09-26-webui-torrent-meta-edit.md); **未提交**

- WEB UI **一键导入缺失站点**(2026-09-26): 已外迁 → [implemented-webui-history.md](implemented-webui-history.md)(cap 轮转, 事实不变)

- WEB UI **站点接入数据白屏修复**(2026-09-25): 已外迁 → [implemented-webui-history.md](implemented-webui-history.md)(cap 轮转, 事实不变)
- WEB UI **HR 删除安全档位呈现**(2026-09-25): 已外迁 → [implemented-webui-history.md](implemented-webui-history.md)(cap 轮转, 事实不变)
- WEB UI **设置页控件两处打磨**(2026-09-25): 已外迁 → [implemented-webui-history.md](implemented-webui-history.md)(cap 轮转, 事实不变)
- WEB UI **设置页合一: 移除经典设置页**(2026-09-25): 已外迁 → [implemented-webui-history.md](implemented-webui-history.md)(cap 轮转, 事实不变)

> 注意区分: 下表部分功能作者在 README 中标注 🚧 = "已实现但未严格测试(实盘验证)", 如规则引擎的条件/动作/checking/去重语义等 — 有单测但作者尚不认为经过严格验证; 此类 🚧 ≠ 未实现, 勿移除 (语义详见 pitfalls.md)。
- **2026-09-21 设置页新版(Console Hub)落地**(含版式硬知识: 派生变量声明在使用层 / 发光负 spread / 切角与发光互斥; 无浏览器验证手段)与计划外发现(setUnitNum computed 误用, 已随经典页移除)**: 已外迁 → [implemented-webui-history.md](implemented-webui-history.md)(cap 轮转, 事实不变)
- **2026-09-19 打开目标文件夹修复 / 2026-09-18 视图重建收口·错误原因显示 / 2026-09-15 追剧视图 / 2026-09-17 第 9/10/11 轮修复 / 2026-09-15 三条(双界面命名目录化/旧版第八轮优化/新版界面与多主题)**: 已外迁 → [implemented-webui-history.md](implemented-webui-history.md)(cap 轮转, 事实不变)
