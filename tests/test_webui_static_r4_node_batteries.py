"""test_webui_static_r4_node_batteries 测试计划: 存量评审 R4 static 主题清池 P03 —— 行为修复回归 + 纯逻辑 node 电池

## 测试计划(每个测试函数一条)
- test_r4_winmembers_sorted_window_same_source: R5#35(major) 修复回归 —— winMembers/memberPadTop/memberPadBottom 先 sortedMembers 再开窗: 明细列排序激活且成员 >= ROW_WIN_EST_MIN 时, 切片/占位/前缀和(_rowPre.member)与渲染数组同源同序, 键盘行序(shortcuts _kbRows 同走 sortedMembers)与前缀和逐行对齐(修复前 memberWin 按未排序 list 开窗必红)
- test_r4_groupwin_expand_backoff: R5#57 —— groupWin 退避判据 = 「当前真的有面板」: expandedKey 命中在场组才退避全量; 原组被筛掉/已删与未展开都保持 active 窗口(不得为一个不存在的面板永久退化成全量渲染)
- test_r4_apply_col_order_boundaries: R5#53 —— applyColOrder 落点折算四类边界: 向后移 at=dropIdx-1 / 向前移原位插入 / 末尾边界兜底 push / 非法输入(隐藏列/越界)no-op; 全程隐藏列相对次序不动且尊重既有 colOrder 头部; 26-11-17-0059 W2(1) 增 locked 双保险面: locked 列拖序 no-op(不写不落库)且同场非 locked 列不误伤
- test_r4_col_drag_locked_reject: 26-11-17-0059 W2(1)(E7/R7) —— startColDrag locked 列拒绝启动拖序手势 node 电池: locked 列 mousedown 不挂 move/up 监听、不 preventDefault(表头点击排序/resizer 拖宽不被牵连); 非 locked 列手势照常(守卫不误伤); 落点层兜底(applyColOrder locked no-op)由 test_r4_apply_col_order_boundaries 场景 6 承担, 摘除两处守卫任一即红(红绿双验锚)
- test_r4_col_persist_intent_merge_and_gates: R5#52(major) + R5#37/R5#38 修复回归 —— 意图升格三层 merge: 拖拽/双击自适应后既有隐藏列 px 仍在、可见列被渲染快照冻结、被拖/适配列被终值覆盖; 纯点击零位移不升格意图不落盘不拦 click(R5#37); 拖拽尾 capture 拦截下一拍自清(R5#38); 微动未过阈值不把起始快照写进生效轨(issue 26-11-08-0229 #10)
- test_r4_selection_state_machine: R5#51(major) —— AQB_SELECTION 真跑: _selSyncGroups 四态(补选/移出/未知 key 保留/种子页降级: 不补选但降级照做)、_selAnchor 兜底链四态(显式锚点/光标/展开组/首行)、selSizeSummaryOf occ_key 取 max 去重
- test_r4_partial_groups_predicate_five_forms: 部分组判定单点守阵(计划 26-11-11-0820 S1, 拍板 D2) —— _partialGroupsOf(keys, hashes) -> [{key, name, sel, total}] 是删除确认框行(S2)/迁移关确认框(S3)/迁移开披露条(S4) 三落点共用的「部分组」唯一判定面; 判定 = 真实组(!virtual 且 total>1)有成员命中 hashes ∧ 组键不在 keys ∧ sel<total。静态锚: 判定单点 _partialGroupsOf 与聚合单点 _partialGroupsSummary 对称设锚, 各自在 selection.js 定义形态(裸名+(参数)+`{`, 接收者调用与注释散文不计)恰一次(其它 shared 文件零平行定义 —— 消费方内联判定或聚合任一即红)、方法体走 this.decoratedGroups 与 _findGroup 同源解析面且零 filteredGroups 独走、判据含 g.virtual 豁免。五形态 node 电池真跑: 组键整组入选不触发(含双向联动组键与成员 hash 同存面)/成员全选不触发(组键已晋升 + 种子页降级未晋升 sel===total 两面)/部分选中触发且 sel/total/name 逐字段正确/跨组混合(整组 A + 部分组 C 并存)只列部分组/单成员组与虚拟行均不触发(专设双成员虚拟行钉住 virtual 判据独立于 total<=1); 边界面: 空入参不抛/hash 不属任何组不触发/name 缺失兜组 key/decoratedGroups 缺失(R6 极端竞态)空返回不抛不误拦 —— 摘除判定或换解析面即红
- test_r4_delete_details_partial_group_row: 删除链部分组行落点级真跑(计划 26-11-11-0820 S2, 拍板 D5) —— _deleteDetails(delete_flow.js)在删除目标含部分组时于既有行流末尾追加一行(tone error/wide/#i-warn, HR 风险行同款), 判定单点消费 selection.js::_partialGroupsOf(带接收者调用)。正例: 部分组目标恰一行且单组文案逐字段(组名/已选 M/N/钉住词「将缺文件」); 多组聚合一行(已选/总数与缺口用合计); 四组触发组名列前 3 +「等 K 个」(照 _hrRiskOf 模式); 跨组混合(整组 A 组键入选 + 部分组 C 散员, D2 触发面)行照出且只列 C。负例(D2 不触发面): 整组删除(组键入选)/成员全选未晋升/单成员组/虚拟行/hash 不属任何组均无该行。恒显面(D5): _deleteDetails 形参只有 keys/hashes(无 delete_files 勾选入参, 行与勾选状态无关恒显由结构保证)且行为行流末行(既有五行/六行结构零改动只追加)。电池合并 selection.js + delete_flow.js 两 mixin 方法(app.mixin 同实例注入等价), 无 node 静默跳过
- test_r4_move_dialog_partial_group_gate: 迁移关部分组确认框落点级真跑(计划 26-11-11-0820 S3, 拍板 D3) —— submitMoveDialog(drawer.js)在目标含部分组且 flags.relocate_enabled===false 时首次投递前弹确认框(tone error/danger/wide), 确认才发, 取消留在设定位置框; 判定单点消费 selection.js::_partialGroupsOf、聚合单点消费 _partialGroupsSummary(与删除链 S2 行共用)。正例: 部分组+迁移关恰弹一次且弹层顺序先收 moveOpen 再开确认框(R3 防双遮罩互盖, 照 confirm 回路先例), 文案钉住词「将缺文件」+「整组迁移」逐字段, 确认后首发带 confirm=true(后端部分组闸放行位, issue 26-11-11-0823), 成功后框收; 取消零投递带原路径重开; 确认后投递失败带原路径重开(框已被闸先收, 照 confirm 回路失败分支, 手输路径不丢), 非闸直发失败维持现状无重开; 四组聚合前 3 +「等 K 个」合计口径; 跨组混合(整组 A 组键入选+部分组 C 散员, D2 触发面)闸照触发且文案只列 C。负例(D3): 整组入选/成员全选未晋升/单成员组/虚拟行/hash 不属任何组直发零新增弹层。旗标两态: 迁移开直发零弹层(S4 披露条的面); flags/relocate_enabled 解析不出(R6)静默直发不误拦; decoratedGroups 缺失不抛不误拦。电池合并 selection.js + drawer.js 两 mixin 方法, 无 node 静默跳过
- test_r4_move_dialog_partial_disclosure_bar: 迁移开部分组披露条落点级真跑(计划 26-11-11-0820 S4, 拍板 D4) —— openMoveDialog(drawer.js)在 flags.relocate_enabled===true 时开框瞬间算一次部分组聚合(_partialGroupsOf+_partialGroupsSummary 带接收者, 判定/聚合单点只在 JS 侧)存非下划线状态 movePartialDisclosure 供 move-dialog.html 披露条消费(R2: Vue 模板编译器不解析 _ 前缀标识符, 模板只读本字段)。正例: 部分组+迁移开披露非 null 且单组 names/sel/total/gap 逐字段; 四组聚合前 3 +「等 K 个」合计口径; 跨组混合(整组 A 组键入选+部分组 C 散员, D2 触发面)披露只列 C; 非部分组负例(整组入选/成员全选未晋升/单成员组/虚拟行/hash 不属任何组)无条。降级面(R6/D4): 迁移关(relocate_enabled===false, S3 确认框的面, 含 S3 取消重开路径)无条; flags/relocate_enabled 解析不出无条不抛; decoratedGroups 缺失无条不抛。接线面: 开框既有状态机零破坏(moveOpen/moveCount/movePathInput 照常)。静态守阵(照 delete_flow.js WARN 原注/_scan_mixin_wiring 范式): move-dialog.html 剥注释后零 _ 前缀标识符; 文案钉住「整组迁移」+「将按整组迁移扩展至全组」+「个成员」; drawer.js 接线形态(先复位 null + relocate_enabled===true 门 + 带接收者单点调用); state.js 显式建字段; 四皮肤 dialogs.css 各有 .move-note.move-note-warn warn 档。电池合并 selection.js + drawer.js 两 mixin 方法, 无 node 静默跳过
- test_r4_load_col_state_seeding: R5#18 —— loadColState 默认隐藏播种三态: 空存储播种 / 仅空 hidden 不播(「刻意全开」合法偏好) / 有任一偏好键不播; 附坏 JSON 走完整流程、locked 列忽略、w 白名单洗净(洗净后三键全缺照播)
- test_r4_sort_domain: R5#54 —— AQB_SORT 真跑: setSort 三态循环(经典 gk/gd 与 dyn dtSortState 两形态) + 默认升序非空键默认列首击切降序(用户表 addr/1、Tracker sev/1 缺陷修复; 修复前三击全 no-op)与非默认列/空键三态零误伤 + _dtStrCompare(IPv4 逐段数值序/端口数值/等值/非 IP localeCompare 回落) + sortedDrawer 空值两方向恒末位与 IPv4 数值序
- test_r4_format_ladder_family: R5#55 —— format 函数族档位边界: _fmtLadder 梯顶回落(top 命中/缺省/档名写错回落整梯)与字节/速度两族、fmtEta 8640000 哨兵与非正值、fmtDuration 三段进位边界、fmtPeersQb 缺省只显已连接
- test_r4_prog_band_boundaries: S3(计划 26-11-20-0009) —— 进度分档纯函数 progBand/progBandClass(format.js 新增)边界: 编码 0=空端点档/1..5=五档(左开右闭, 20/40/60/80 右闭整点归当档)/6=终点档; 0/0.1/20/20.01/40/40.01/60/60.01/80/80.01/99.9/100 逐点 + 负值/NaN/undefined 归空端点不抛错 + >100 归终点 + 类装配 csb-0/csb-1..csb-5/csb-t 逐档互证 + progPct 钳制联动(>1 比例钳 100 落终点档)
- test_r4_speed_band_and_num_scale: S4(计划 26-11-20-0009) —— 速度分档 speedBand/speedBandClass(format.js 新增)全边界: 编码 0=无档(bytes<=0 / 分母 0=不限/null=undefined=未知, 归 0 不产类)/1..5=五档(左开右闭, 20/40/60/80% 右闭整点归当档)/6=over(>100% 严格大于, 恰 100%=分母 仍第 5 档); 20% 端点双侧/40/60/80 同构/99.9/over 双侧逐点 + 类装配 ''/csp-1..csp-5/csp-over 逐档互证 + **75% 旧档不受扰**(numTone 0.75 阈值双侧原样且与新档互不干扰, 两套类链由 cellSpeedTone 三态互斥派发: current 逐值 == numTone / off 恒空串 / 选谱 == speedBandClass)+ 数值列三判定(numScaleRatio/numScaleAvail/numScaleEta)翻转端点双侧各一例(ratio=1.0 / availability=1.0 不着色 / eta=60s / eta=8640000 哨兵与 <=0、-1 未知面)+ 消费面经 ctx 真跑(colStyle 状态桩 + hrRatioClass 伴值桩): cellNumScaleRatio 空白格不染(progress=0)与 HR 伴值共存形态(伴值行 pending/reached 不产 cst-*, D10 让位; 无伴值行正常; 组行无 HR 字段自然落判定)+ cellNumScaleAvail numeric 开关互斥(off == numTone(v,1) 原样 / on = D10 完整语义, 0.75 档让位)
- test_r4_unit_parts_family: S5(计划 26-11-20-0009) —— 单位拆分 parts 家族(fmtSizeParts/fmtSpeedParts, format.js 新增)与拆分单点 _fmtLadderParts: **parts ≡ fmt 串逐字一致**(非 null 时 v+u == fmtSize/fmtSpeed 输出; 大小族全梯 B~PiB: 档下原值/1024 进制恰端点命中/档内中值/2^60 超大值封 PiB/负数不进档; 速度族 B/s~GiB/s 同构 + 超 GiB 封顶) + 零值 dash null 形态(0/null/undefined/NaN -> null, 与 fmtSizeOrDash/fmtSpeedOrDash 空串口径逐值互证) + u 前导空格归属(拼串含空格, 文本总宽不变)与字段形态恰 {v, u, c} + 档类/族标记(大小族 csu-B/csu-KiB..csu-PiB, 速度族 csu-Bs/csu-KiBs..csu-GiBs, 类名 's' 尾即速度族, 与单位串含 /s 互证) + 小数位 toFixed(2)/负数/超大值边界 + 上下限列消费面(fmtLimitBytes 空串门与 parts null 门逐值等价, 非零串形态逐字同) + 拆分单点回归(_fmtLadder == parts 拼接投影, top 档名回落/取整兜底语义原样)
- test_r4_fx_mount_toast_split_and_rows_ghost: R5#193 —— flux fx 挂载层 node 电池(fx-mount.js 是 IIFE,
  桩 DOM/BOM 后真跑): TOAST_SPLIT 拆段正则族(主标题+说明两段落地/无分隔符与括号头与超 14 字头与
  说明不足 2 字单行 —— trim 后计长, 分隔符后连接空格不算门槛/全角冒号与逗号分隔/单行也挂 toast-txt)+ toastSync 差分 stamp(rise/队列牌/倒计时
  只归 own 条/danger 原位升级)+ rows 行差分(首轮只建缓存/增删检出排一帧/退场幽灵克隆定格 row-out
  附回原容器/入场行 stamp row-in + --fx-row-h 实测覆写/入场毕摘 stamp(animationend 名/目标守卫,
  属性与行内行高一并清, 监听自摘)/无增删不排帧; 2026-11-14 顺手修扩)
- test_r4_dt05_advice_dispatch: R5#95(P13) —— 05 adviceFor 五类关键词分派经 rowsFn 真跑(失败桶
  failRowOf 装配路径, 不经字符串锚): not registered/passkey/ban/timeout/maintenance 每类一条
  命中各自文案 + 通用兜底分支(零覆盖的纯判据, node 电池直跑)
- test_r4_dt05_tier_sort_missing_last: R5#81(P13) 修复回归 —— 05 ok 组 tier 升序对缺失/非法
  tier 记 9 殿后(与 04/06 的 tierN 兜底同口径), 稳定序保 qB 原序; 修复前折算 0 把 tier 缺失
  tracker 插到所有 tier0 之前必红
- test_r4_drawer_general_rows_qb_sentinels: issue 26-11-08-0229 #2 修复回归 —— drawerGeneralSections
  契约层传输行(做种数/完整下载中/连接)对 qB -1/null 哨兵降级(单值槽 —, 连接上限 -1 译「不限」,
  与 fmtPeersQb/01 英雄行 peerNum/connLimit 同口径), 真值形态逐字不变; 01/02/03 三变体共同消费
  该单点, 电池直跑生产函数不经字符串锚
- test_r4_drawer_rows_path_wide_conditional: issue 26-11-08-1621 修复回归 —— drawerGeneralSections
  契约层路径段 下载路径/根路径 wide 改条件式(值非空才 wide:true, 空值/缺失/null 行 wide 不置位
  按普通行渲染, text 兜底「—」保留, 真值行 wide 与文本透传不变); 沙箱口径与哨兵电池同式
- test_r4_dt_table_layout_geometry_equivalence: dt_table 几何等价性探针(计划 26-11-10-0027 W1(1),
  「先证后改」; 覆盖面 13 张**不含 HR 三表**(沙箱不加载 hr_status.js, HR 等价性由例外清单
  守阵静态形态钉承担, 真跑喂桩归 W3 parity e2e —— 函数 docstring 有口径)—— 对 ALL_TABLE_DEFS
  全部 13 张表的真实列定义(全列有 tpl 前提显式钉住)× 5 类
  colWidths/列态场景(无覆盖/单列覆盖/全列覆盖/隐藏一列(其固化宽不漏轨)/自定义列序), 断言现役
  columns_grid._gridTemplate 轨道串 ≡ DT_TABLE.layout().gridTemplate(逐字符)、colAlignCss 实测
  CSS 的 text-align 序列 ≡ layout().aligns(逐列; 每一面两侧消费同一份列定义与宽度输入); 页数实算
  钉 13, 五类场景逐类存在性断言(scene 标签落袋 —— 条件类的触发前提回归致静默消失即红)。探针红
  = 轨道语义冲突 = 计划 R1 停手条款(failed 项带两侧输出全文, 不改生产代码凑绿); 探针绿是 W1(2)
  委托改造的前置证据。沙箱口径: app.js 截断切片 + columns 域聚合同一 eval + dt_table.js require。
  node 电池真跑(无 node 静默跳过)
- test_r4_dt_table_exception_list_geometry_guard: dt_table 例外清单守阵(计划 26-11-10-0027
  W2(2), 拍板 D4; 评审 2 三条 minor 当场修后口径) —— 清单(HR 三表 hrDetail/hrWave/hrKv +
  04 卡片形态面)之外零旁路几何:
  1. camelCase 产物(gridTemplateColumns)白名单恰两件(内核 assertLayout 读 / 引擎
  _renderedWidths 读), 之外零命中; table.js **不在白名单**而是双向钉死(原文提及恰 1 处 =
  契约头注文档仍在 + 掩码后零命中 = 提及确在块注释内, 代码产物零放行 —— 白名单死条目会把
  真实旁路放行成恒绿); 2. columns_computed 每条恰 _gridTemplate 单点委托形共 16 条且 id 集
  与表注册表 ALL_TABLE_DEFS 键互对(新表漏接单点 computed 即红; 26-11-17-0059 W1(1)(2) E6
  并入翻面: HR 三表定义源在 hr_status.js 的 HR_TABLE_DEFS, 经 window.AQB_HR_TABLE_DEFS 桥
  并进 ALL_TABLE_DEFS —— 逐 id 落 app.js 或 hr_status.js 两空格字面行之一, 桥合并/桥导出在盘,
  不旁路第二注册表); 3. kebab 声明
  (grid-template-columns)命中表面容器(.group-head/.group-row/.group-table/.detail-head/
  .h-cell/data-table)的规则恰 = D4 例外清单 1 条(04 的 .dt04-list .group-table 两列卡片栅格),
  且 .js 侧钉「选择器与首条声明同行」惯例(命中行必自带 { —— 多行规则形即红不静默逃逸,
  .css/.html 侧保留规则解析双轨); 4. 例外条目存在性(04 规则本体 + HR 三表注册/tpl 全列/stickyHead:false +
  settings-detail HR grid 几何恰 3 处与零旁路拼轨 —— 26-11-17-0059 W1(3) 翻面, 旧「零 grid 几何」「借壳形态在」随 thead 借壳退役); 5. 单点完整性(_gridTemplate 委托 DT_TABLE.layout
  且无 .join 拼轨回潮 + colAlignCss 取 layout().aligns); 6. assert 侧豁免清单本体钉死
  (columns_grid.ASSERT_SKIP_FACES 键集恰 {drawerTrackerV04, drawerStubV0} +
  _assertLayoutPair 含 empty-row 行级豁免字面 —— 豁免被删 = 04 面刷 console.error 噪声, 即红)。
  node 电池真跑(无 node 静默跳过)
- test_r4_outgoing_rowh_reprobe_kills_pad_jump: issue 26-11-15-0332 产品侧修复回归 —— 行窗口化
  出窗最后一探(_rowWindow 重建 pre[] 前用仍在场的旧窗口行量真值顶掉 _rowHs 陈旧存值): 红验
  (关掉重探)逐行复现 padTop 按 69.609 超量替换, 绿验断言真值 65.781 落地 / padTop 与 _rowPre
  按真值重建 / 前后差恰 +3.828px; 不踩全表作废坑(键数/_rowHVer/_rowH/_rowHSig/_winMeasured
  零改动)、同拍 sig 去重(memberPadTop/Bottom/winMembers 三入口只量一次)、rowWin 关零重探、
  抽屉 content-visibility:auto 未渲染行跳过(28px intrinsic 不得改坏 27px 真值); 第二根因同钉:
  _measureRowH 量齐后 _rowH 估算基准冻结(新量一行不连坐搬 pad 区上百行), 首访量齐那一拍与
  「存值非正」两支仍照常校准基准
- test_r4_hr_cells_registry_restore_and_assert_anchor: 26-11-17-0059 W2(2)(3)(4) —— HR 三表
  值格渲染注册化 + 还原链读/写两侧 + 列宽动作 + assert headDom 锚 node 电池(沙箱
  dt_table.js -> hr_status.js -> [app.js 截断切片 + columns 域聚合文本] 同一次 eval,
  columns 方法体裸名引用 app.js 列模型常量须同 eval; 装载序骨架与生产 manifest 同序):
  1. 注册面(E2) AQB_HR_CELLS_REGISTER 真跑后 DT_TABLE.CELLS 名字集恰 20 且与列定义**双向
  互对**(漏注册与列 key 漂移都红; 互对/计数两检查物理落位第 2 节块尾)+ 逐页计数
  10/8/2/cellOf 取回/未注册名抛错, 注册前
  CELLS 为空钉住注册点在 app.js 装载序末位(hr_status.js 模块层先于 dt_table.js 载入,
  registerCell 不可达); 2. 保真锚 逐列渲染器输出对照迁移前模板 DOM 载体(hr-lane/hr-vsrc/
  hr-pres 徽章色义 + hr-sub 副行两段/mono-cell 载体/数值列 hrsSize·hrsRatio 缺失回落
  —/name wrap/kv-k/mono-cell+色档合并 root/kv act 置位 —— 按钮本体在模板, 注册化不吞交互);
  3. 还原链读侧 v5 三表子树经 loadColState 读回(宽/序/隐, 序喂脏载荷钉重复 key 去重 +
  非法 key 丢弃 + locked k 列还原侧忽略 + w 白名单 + 空存储 HR 页无播种), HR 三页在
  ALL_TABLE_PAGES(16); 4. 静态锚 columns_grid._assertLayouts headDom 分支(HR 三表经枚举面
  覆盖, 未展开 v-show 无盒 = 未挂载豁免 R4)/headDom: true 恰 3/settings-detail 三表
  hrCellOf 消费口 + 逐列手写 v-if 链零残留/app.js 注册调用点在 HR mixin 之后/注册函数
  fail-fast; 5. 写侧 round-trip persistPage 真跑三 HR 页(store 形态 {hidden,order,w} 与
  内存意图一致 + loadColState 读回同值); 6. 列宽动作(stub ctx) fitColumnsToWindowAll/
  resetAllColumnWidthsAll 波及 HR 三页且 colW[p]===null(回全自动不固化快照)+ fitAll
  未展开态(_headEl 无盒)recomputeEffective 对三 HR 页 colWidths 零宽度条目(键置 {} 是
  「立即回弹性模板」设计行为, 垃圾轨语义 = 无 px 条目)。红绿双验锚见函数 docstring。
  无 node 静默跳过
- test_r4_rowh_zoom_rescale_follows_root_zoom: issue 26-11-16-0716 产品侧修复回归 —— 运行时
  root zoom 变化, _measureRowH 开头比对 _rootZoomOf() 与上次校准基线 _rowHZoom, 变了就全表乘
  zNew/zOld 原地重标 _rowHs/_rowH(不删键不翻 _winMeasured 不动冻结门, _rowHVer bump 一次);
  配套 _reprobeRenderedRowH 过渡拍让路(系统性差值不得当行高真变, 不烧签名)。电池十三项: 首拍落
  基线 / 全表等比例重标 / est 同比例跟随 / 键数·量齐态·签名零改动 / 重标后与逐行 gBR 逐位一致 /
  同 z 幂等 / body 读到 null 不误判成 z=1(1↔z 抖动坑) / 过渡拍让路 / 重标后照常重探 /
  _winSigExtra 令牌两态口径 / 携带x重标共存(跨拍配对优先读 _rowHs 重标现值, 快照只兜底) /
  携带回落(旧键被签名作废剔键面时才落快照值)

加载口径: columns 域经 webui_helpers.bundle_file("columns.js") 聚合(根 + 五片段清单序, 与拆分前
同一份代码); 单文件域(selection/sort/format)直接 eval。app.js 以 loadColState 截断切片加载
(该函数依赖的列模型常量/洗净函数全部在其上方, createApp 接线段不进沙箱)。
窗口化/列模型常量(单点在 app.js)由电池自给 —— 与 webui_dom_page_support._NODE_WIN_SRC_PROBE 同口径。
无 node 静默跳过(与既有 node 电池同口径, 不引入 pytest skip)。
"""

import json
import os
import re
import shutil
import subprocess
import tempfile

from webui_helpers import STATIC_ROOT, bundle_file


def _run_probe(probe, *args):
    """跑一个 node 电池: 无 node 静默跳过(返回 None); 输出末行必须是 {ok, total, failed} JSON"""
    node = shutil.which("node")
    if not node:
        return None
    proc = subprocess.run(
        [node, "-e", probe, *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    assert proc.returncode == 0, f"node 电池跑挂: {proc.stderr.strip()}"
    return json.loads(proc.stdout.strip().splitlines()[-1])


def _assert_battery(report, what):
    assert report is not None, "无 node: 本电池静默跳过(与既有电池同口径)"
    assert report["failed"] == [], f"{what} {report['ok']}/{report['total']} 过, 失败: {report['failed']}"


# R5#35 修复回归: winMembers 三个入口先排序再开窗, 切片/前缀和/占位同源 ------------------
_NODE_WINMEMBER_PROBE = r"""
const fs = require("fs");
// 行窗口化常量(单点在 app.js, 电池自给 —— 与 _NODE_WIN_SRC_PROBE 同口径)
global.ROW_WIN_MIN = 200;
global.ROW_WIN_OVERSCAN = 10;
global.ROW_WIN_EST_MIN = 200;
global.ROW_WIN_EST_H = { torrent: 42, group: 44, member: 34, drawerContent: 27 };
global.ROW_WIN_GAP_FALLBACK = 0;
global.window = {};
// winMembers 依赖排序域的 sortedMembers(AQB_SORT) —— 真机两域同混进一个组件实例, 这里同混
const srcCols = fs.readFileSync(process.argv[1], "utf8");
const srcSort = fs.readFileSync(process.argv[2], "utf8");
eval(srcCols + "\n;globalThis.__W2__ = window.AQB_COLUMNS;");
eval(srcSort + "\n;globalThis.__W3__ = window.AQB_SORT;");
const M = Object.assign({}, globalThis.__W2__.methods, globalThis.__W3__.methods);

const GAP = 6;
const N = 300;
// 成员: hash m0..m299; 排序键 uploaded = (i*7919)%300(与 N 互质 = 0..299 的真排列, 排序必打乱原序);
// 行高两档按**原序**交替(排序后相邻行高错落, 前缀和对"序"敏感 —— 按错序累积必对不上)
const mkMembers = () => Array.from({ length: N }, (_, i) => ({
  hash: "m" + i, uploaded: (i * 7919) % N, site: "s" + (i % 7), __i: i,
}));
const hOf = (i) => (i % 2 ? 65.4 : 43.7);
const mkCtx = () => Object.assign({}, M, {
  rowWin: true,
  detailSortKey: "uploaded", detailSortDir: -1,  // 明细列排序激活(R5#35 触发条件之一)
  _winMeasured: { torrent: true, group: true, member: true, ctr: true, drawerContent: true },
  _rowH: { torrent: 50, group: 50, member: 50, ctr: 50, drawerContent: 50 },
  _rowHVer: 1,
  _winViewH: 800,
  _winScrollY: 3000,  // 滚到中段: padTop/padBottom 非零, 切片错位必现
  _winTop: { torrent: 0, group: 0, member: 0, ctr: 0, drawerContent: 0 },
  _rowHs: {},
  _rowPre: {},
  _winGapFor: () => GAP,
  // pad 缩放换算(issue 26-11-14-0844)默认桩: 容器不在场 = 有效 zoom 恒 1, 老场景逐位零差异
  _winContainer: () => null,
  memberHashesOf: (list) => (list || []).map((m) => (typeof m === "string" ? m : (m && m.hash) || "")).filter(Boolean),
});
const checks = [];
const ok = (name, cond) => checks.push([name, !!cond]);

const c = mkCtx();
const list = mkMembers();
list.forEach((m, i) => { c._rowHs["member:" + m.hash] = hOf(i); });
const hOfM = (m) => hOf(m.__i);
const sorted = M.sortedMembers.call(c, list);
ok("场景有效: 排序真的打乱了原序(否则本电池空转)",
   JSON.stringify(sorted.map((m) => m.hash)) !== JSON.stringify(list.map((m) => m.hash)));

// 1. 渲染切片 = 在排序序上开窗的切片(窗口与前缀和同一数组)
const w = M.memberWin.call(c, sorted);
const rendered = M.winMembers.call(c, list);
const want = sorted.slice(w.start, w.end);
ok("winMembers 切片与渲染数组同序(排序激活下窗口按 sortedMembers 序开窗)",
   w.active && want.length < N &&
   JSON.stringify(rendered.map((m) => m.hash)) === JSON.stringify(want.map((m) => m.hash)));

// 2. 前缀和按排序序逐行累积(_rowPre.member 供键盘视口换算文档 y, 必须与 _kbRows 同序)
const pre = c._rowPre.member;
let preOk = !!pre && pre.length === N + 1 && pre[0] === 0;
if (preOk) {
  for (let i = 0; i < N; i++) {
    if (Math.abs(pre[i + 1] - pre[i] - (hOfM(sorted[i]) + GAP)) > 1e-9) { preOk = false; break; }
  }
}
ok("_rowPre.member 前缀和按排序后行高累积(修复前按未排序序累积必红)", preOk);

// 3. 占位与排序序窗口一致(调用点同步传排序后数组)
const padTop = M.memberPadTop.call(c, list);
const padBottom = M.memberPadBottom.call(c, list);
ok("memberPadTop 与排序序窗口一致", padTop > 0 && Math.abs(padTop - w.padTop) < 1e-9);
ok("memberPadBottom 与排序序窗口一致", padBottom > 0 && Math.abs(padBottom - w.padBottom) < 1e-9);

// 4. 键盘视口回落取行不岔: 前缀和第 i 行 = 键盘行序(shortcuts 同走 sortedMembers)第 i 行
const kb = c.memberHashesOf(sorted);
ok("前缀和与键盘行序逐行对齐(切片首行 + 窗口末行)",
   M._rowKeyOf.call(c, "member", sorted[w.start]) === "member:" + kb[w.start] &&
   M._rowKeyOf.call(c, "member", sorted[w.end - 1]) === "member:" + kb[w.end - 1]);

// 5. 排序未激活/窗口关闭 = 原行为(零差异回退)
const c2 = mkCtx();
c2.detailSortKey = "";
c2.rowWin = false;
const r2 = M.winMembers.call(c2, mkMembers());
ok("窗口关闭且未排序时全量回退", r2.length === N);
ok("排序未激活时 sortedMembers 原样返回", M.sortedMembers.call(c2, list) === list);
console.log(JSON.stringify({
  ok: checks.filter((c) => c[1]).length, total: checks.length,
  failed: checks.filter((c) => !c[1]).map((c) => c[0]),
}));
"""

# R5#57: groupWin 退避判据(「当前真的有面板」) -------------------------------------
_NODE_GROUPWIN_BACKOFF_PROBE = r"""
const fs = require("fs");
global.ROW_WIN_MIN = 200;
global.ROW_WIN_OVERSCAN = 10;
global.ROW_WIN_EST_MIN = 200;
global.ROW_WIN_EST_H = { torrent: 42, group: 44, member: 34, drawerContent: 27 };
global.ROW_WIN_GAP_FALLBACK = 0;
global.TABLE_DEFS = { group: { tableRef: null }, torrent: { tableRef: null } };
global.window = {};
const src = fs.readFileSync(process.argv[1], "utf8");
eval(src + "\n;globalThis.__W2__ = window.AQB_COLUMNS;");
const M = globalThis.__W2__.methods;
const C = globalThis.__W2__.computed;

const GAP = 6;
const N = 300;
const mkGroups = () => Array.from({ length: N }, (_, i) => ({ key: "g" + i }));
const mkCtx = (expandedKey) => Object.assign({}, M, {
  rowWin: true,
  filteredGroups: mkGroups(),
  expandedKey,
  _winMeasured: { torrent: true, group: true, member: true, ctr: true, drawerContent: true },
  _rowH: { torrent: 50, group: 50, member: 50, ctr: 50, drawerContent: 50 },
  _rowHVer: 1,
  _winViewH: 800,
  _winScrollY: 6000,
  _winTop: { torrent: 0, group: 0, member: 0, ctr: 0, drawerContent: 0 },
  _rowHs: {},
  _rowPre: {},
  _winGapFor: () => GAP,
  // pad 缩放换算(issue 26-11-14-0844)默认桩: 容器不在场 = 有效 zoom 恒 1, 老场景逐位零差异
  _winContainer: () => null,
});
const checks = [];
const ok = (name, cond) => checks.push([name, !!cond]);

// 1. 展开组在场: 退避全量(.detail 高度不定, 窗口的"第 i 行在 pre[i]"假设失效)
const wOn = C.groupWin.call(mkCtx("g150"));
ok("expandedKey 命中在场组 -> 退避 off 全量(end=n, 占位 0)",
   wOn.active === false && wOn.end === N && wOn.padTop === 0 && wOn.padBottom === 0);
// 2. 展开态跨视图带回后原组已被筛掉/已删: 不为一个不存在的面板退避, 保持 active 窗口
const wGone = C.groupWin.call(mkCtx("gone"));
ok("expandedKey 指向不在场的组 -> active 窗口(不误退避)", wGone.active === true);
// 3. 未展开: active 窗口
const wOff = C.groupWin.call(mkCtx(""));
ok("expandedKey 空 -> active 窗口", wOff.active === true);
// 4. 窗口切片与占位合理(2/3 的窗口是真窗口, 不是退到另一边)
ok("active 窗口切片是严格子集且占位非零", wOff.end - wOff.start < N && wOff.padTop > 0 && wOff.padBottom > 0);
console.log(JSON.stringify({
  ok: checks.filter((c) => c[1]).length, total: checks.length,
  failed: checks.filter((c) => !c[1]).map((c) => c[0]),
}));
"""

# R5#53: applyColOrder 落点折算四类边界 --------------------------------------------
_NODE_APPLY_COL_ORDER_PROBE = r"""
const fs = require("fs");
global.window = {};
// TABLE_COLUMNS 是 app.js 模块级常量, 方法体按裸名引用(走作用域链, 不走 this) —— 必须真挂全局
global.TABLE_COLUMNS = { p: [{ key: "a" }, { key: "b" }, { key: "c" }, { key: "d" }, { key: "e" }] };
// columnDef 同在 app.js(生产里先于本片段载入, 作用域链可达) —— 电池自给同款实现
// (26-11-17-0059 W2(1) 起 applyColOrder 有 locked 双保险直接引用它, 缺它即 ReferenceError)
global.columnDef = (p, k) => (global.TABLE_COLUMNS[p] || []).find((c) => c.key === k) || null;
const src = fs.readFileSync(process.argv[1], "utf8");
eval(src + "\n;globalThis.__W2__ = window.AQB_COLUMNS;");
const M = globalThis.__W2__.methods;

// 可视列空间 a b c e(d 隐藏); 全序列 a b c d e
const mkCtx = (order) => {
  const c = Object.assign({}, M, {
    colHidden: { p: ["d"] },
    colOrder: { p: order || [] },
    colWidths: {},
    colW: {},
    persisted: [],
    persistPage: (page) => c.persisted.push(page),
    $nextTick: (fn) => fn(),
    recomputeEffective() {},
  });
  return c;
};
const orderOf = (c) => c.colOrder.p;
const checks = [];
const ok = (name, cond) => checks.push([name, !!cond]);

// 1. 向后移: a(vis 0) 拖到 dropIdx 2(c 之前) -> 移除自身后 at=1, 插在 b 与 c 之间
let c = mkCtx();
M.applyColOrder.call(c, "p", "a", 2);
ok("向后移: dropIdx 2 -> [b,a,c,d,e](隐藏列相对次序不动)", JSON.stringify(orderOf(c)) === JSON.stringify(["b", "a", "c", "d", "e"]));
ok("落库即持久化该页", c.persisted.length === 1 && c.persisted[0] === "p");

// 2. 向前移: e(vis 3) 拖到 dropIdx 0 -> 移除自身后 at=0, 插在最前
c = mkCtx();
M.applyColOrder.call(c, "p", "e", 0);
ok("向前移: dropIdx 0 -> [e,a,b,c,d]", JSON.stringify(orderOf(c)) === JSON.stringify(["e", "a", "b", "c", "d"]));

// 3. 末尾边界: a 拖到 dropIdx 4(== 可视列数) -> 跳隐藏列计 seen 后仍插不进, 兜底 push 到末尾
c = mkCtx();
M.applyColOrder.call(c, "p", "a", 4);
ok("末尾边界: dropIdx=vis.length -> [b,c,d,e,a](兜底 push)", JSON.stringify(orderOf(c)) === JSON.stringify(["b", "c", "d", "e", "a"]));

// 4. 非法输入一律 no-op: 负 dropIdx / 越界 / 隐藏列自身(可视空间里找不到)
c = mkCtx();
M.applyColOrder.call(c, "p", "a", -1);
M.applyColOrder.call(c, "p", "a", 5);
M.applyColOrder.call(c, "p", "d", 1);
ok("非法输入(负/越界/隐藏列)no-op(colOrder 不写)", !c.colOrder.p || c.colOrder.p.length === 0);
ok("非法输入不触发持久化", c.persisted.length === 0);

// 5. 尊重既有 colOrder 头部(_orderedKeys): 自定义序 e d c b a(d 隐藏) 下, a(vis 3) 移到 0
c = mkCtx(["e", "d", "c", "b", "a"]);
M.applyColOrder.call(c, "p", "a", 0);
ok("既有自定义序下向前移 -> [a,e,d,c,b]", JSON.stringify(orderOf(c)) === JSON.stringify(["a", "e", "d", "c", "b"]));

// 6. locked 双保险(26-11-17-0059 W2(1)/E7): locked 列不可被拖走 —— 落点层直接调用面 no-op
//    (不写 colOrder 不落库; 非 locked 同场列不受牵连照常换位)
global.TABLE_COLUMNS = { p: [{ key: "k", locked: true }, { key: "x" }, { key: "y" }] };
c = mkCtx();
M.applyColOrder.call(c, "p", "k", 0);
ok("locked 列拖序 no-op(colOrder 不写不落库)", (!c.colOrder.p || c.colOrder.p.length === 0) && c.persisted.length === 0);
M.applyColOrder.call(c, "p", "x", 0);
ok("同场非 locked 列拖序照常(守卫不误伤)", JSON.stringify(orderOf(c)) === JSON.stringify(["x", "k", "y"]));
console.log(JSON.stringify({
  ok: checks.filter((c) => c[1]).length, total: checks.length,
  failed: checks.filter((c) => !c[1]).map((c) => c[0]),
}));
"""

# 26-11-17-0059 W2(1): startColDrag locked 列拒绝启动拖序手势 ------------------------
_NODE_COLDRAG_LOCKED_PROBE = r"""
const fs = require("fs");
global.window = {};
// 列模型常量与 columnDef 单点都在 app.js(生产先于本片段载入) —— 电池自给(同 applyColOrder 电池口径)
global.TABLE_COLUMNS = { p: [{ key: "k", locked: true }, { key: "x" }, { key: "y" }] };
global.columnDef = (p, k) => (global.TABLE_COLUMNS[p] || []).find((c) => c.key === k) || null;
const listeners = [];
global.document = {
  addEventListener: (t, fn, cap) => { listeners.push({ type: t, fn, capture: !!cap, op: "add" }); },
  removeEventListener: (t, fn, cap) => { listeners.push({ type: t, fn, capture: !!cap, op: "remove" }); },
};
const src = fs.readFileSync(process.argv[1], "utf8");
eval(src + "\n;globalThis.__W2__ = window.AQB_COLUMNS;");
const M = globalThis.__W2__.methods;

const mkCtx = () => Object.assign({}, M, { _visibleCols: () => [{ key: "k" }, { key: "x" }, { key: "y" }] });
const checks = [];
const ok = (name, cond) => checks.push([name, !!cond]);
let prevented = 0;
const mkEv = () => ({
  button: 0,
  clientX: 100, clientY: 100,
  target: { closest: () => ({ classList: { add() {}, remove() {} } }) },
  preventDefault: () => { prevented += 1; },
});
const byType = (t) => listeners.filter((l) => l.type === t && l.op === "add");

// 1. locked 列: 拒绝启动 —— 不挂监听不 preventDefault(点击排序照常冒泡到 headActivate 的前提)
let c = mkCtx();
M.startColDrag.call(c, mkEv(), "p", "k");
ok("locked 列拒绝启动: 零监听注册(mousemove/mouseup 都不挂)",
   byType("mousemove").length === 0 && byType("mouseup").length === 0);
ok("locked 列拒绝启动: 不 preventDefault(表头点击/文本选择行为不被劫持)", prevented === 0);

// 2. 非 locked 列: 手势照常启动(守卫不误伤) —— move/up 各注册一且 preventDefault 已调
listeners.length = 0; prevented = 0;
c = mkCtx();
M.startColDrag.call(c, mkEv(), "p", "x");
ok("非 locked 列手势照常: mousemove+mouseup 各注册一",
   byType("mousemove").length === 1 && byType("mouseup").length === 1);
ok("非 locked 列手势照常: preventDefault 已调(抑制文本选择)", prevented === 1);

console.log(JSON.stringify({
  ok: checks.filter((x) => x[1]).length, total: checks.length,
  failed: checks.filter((x) => !x[1]).map((x) => x[0]),
}));
"""


def test_r4_col_drag_locked_reject():
    """26-11-17-0059 W2(1)(E7/R7): startColDrag locked 列拒绝启动拖序手势 node 电池 ——
    locked 列(主表 name/site/url/act/prio 族 + hrKv k 列)mousedown 不挂 move/up 监听、
    不 preventDefault(表头点击排序/resizer 拖宽不被牵连); 非 locked 列手势照常(守卫不误伤)。
    落点层兜底(applyColOrder locked no-op)由 test_r4_apply_col_order_boundaries 场景 6 承担;
    守阵口径: 摘除 columns_drag.js 两处 locked 检查任一, 两电池之一即红(红绿双验锚)。"""
    report = _run_probe(_NODE_COLDRAG_LOCKED_PROBE, bundle_file("columns.js"))
    _assert_battery(report, "startColDrag locked 拒绝电池")


# R5#52 意图升格三层 merge + R5#37 纯点击门槛 + R5#38 拦截自清 ----------------------
_NODE_COLPERSIST_MERGE_PROBE = r"""
const fs = require("fs");
// 列模型常量(单点在 app.js, 电池自给)
global.MIN_COL_PX = 56;
global.MAX_FIT_PX = 520;
global.RESIZE_DRAG_THRESHOLD = 3;
const listeners = [];   // {type, fn, capture, op: "add"|"remove"}
const timers = [];      // {fn, ms}
global.document = {
  addEventListener: (t, fn, cap) => { listeners.push({ type: t, fn, capture: !!cap, op: "add" }); },
  removeEventListener: (t, fn, cap) => { listeners.push({ type: t, fn, capture: !!cap, op: "remove" }); },
};
global.setTimeout = (fn, ms) => { timers.push({ fn, ms }); return timers.length; };
global.window = {};
const src = fs.readFileSync(process.argv[1], "utf8");
eval(src + "\n;globalThis.__W2__ = window.AQB_COLUMNS;");
const M = globalThis.__W2__.methods;

const SNAP = { a: "200px", b: "150px", c: "120px", e: "90px" };  // 起始渲染快照(只含可见列)
const VIS = [{ key: "a" }, { key: "b" }, { key: "c" }, { key: "e" }];
const mkCtx = () => {
  const c = Object.assign({}, M, {
    colW: { p: { hid: "111px" } },      // 既有意图: 隐藏列的 px(merge 必须保住的那部分)
    colHidden: { p: ["hid"] },
    colWidths: {},
    persisted: [],
    recomputed: 0,
    persistPage: (page) => c.persisted.push(page),
    $nextTick: (fn) => fn(),
    recomputeEffective() { c.recomputed++; },
    _visibleCols: () => VIS,
    _renderedWidths: () => ({ ...SNAP }),
  });
  return c;
};
const evAt = (x) => ({ target: { closest: () => ({}) }, clientX: x, shiftKey: false });
const byType = (t) => listeners.filter((l) => l.type === t);
const fire = (t, ev) => {
  const reg = byType(t).filter((l) => l.op === "add");
  if (reg.length) reg[reg.length - 1].fn(ev);
};
const resetRec = () => { listeners.length = 0; timers.length = 0; };
const checks = [];
const ok = (name, cond) => checks.push([name, !!cond]);

// 1. 拖拽意图升格三层 merge(R5#52): {colW 旧值(含隐藏列) ∪ 渲染快照 ∪ 拖拽终值}
let c = mkCtx();
M.startResize.call(c, evAt(100), "p", "a");   // 注册 move/up; startVal = 200
fire("mousemove", { clientX: 220 });          // 位移 120 > 阈值 3 -> dragged=true, w = max(56, 320) = 320
ok("拖拽中生效宽度已推到终值且邻居列按快照固化",
   c.colWidths.p && c.colWidths.p.a === "320px" && c.colWidths.p.b === "150px");
fire("mouseup", {});
ok("意图升格: 既有隐藏列 px 仍在(旧实现整段替换正是抹掉它的根因)", c.colW.p.hid === "111px");
ok("意图升格: 被拖列被拖拽终值覆盖", c.colW.p.a === "320px");
ok("意图升格: 可见列被起始渲染快照冻结", c.colW.p.b === "150px" && c.colW.p.e === "90px");
ok("拖拽落定走唯一持久化漏斗", c.persisted.length === 1 && c.persisted[0] === "p" && c.recomputed === 1);
// R5#38: 拦截下一拍自清 —— click capture 监听在册 + 定时器排了自清; 自清/自注销都指向同一函数
const clickAdds = byType("click").filter((l) => l.op === "add");
const timersBefore = timers.length;
ok("拖拽尾挂了 capture 拦截层", clickAdds.length === 1 && clickAdds[0].capture === true);
ok("mouseup 后下一拍自清已排程", timersBefore >= 1 && timers[timers.length - 1].ms === 0);
timers[timers.length - 1].fn();               // 触发自清
const lastRemove = byType("click").filter((l) => l.op === "remove").pop();
ok("自清按同一 (click, capture) 注销拦截层", !!lastRemove && lastRemove.fn === clickAdds[0].fn && lastRemove.capture === true);
const evFlags = { stopped: false, prevented: false };
clickAdds[0].fn({ stopPropagation: () => { evFlags.stopped = true; }, preventDefault: () => { evFlags.prevented = true; } });
ok("拦截层 stopPropagation+preventDefault 且拦完即注销", evFlags.stopped && evFlags.prevented);

// 2. 纯点击零位移(R5#37 修复回归): 不升格意图/不落盘/不拦 click
resetRec();
c = mkCtx();
M.startResize.call(c, evAt(100), "p", "a");
fire("mouseup", {});                          // 零位移: move 从未触发
ok("纯点击: colW 意图不被污染(页面保持全自动)", c.colW.p.hid === "111px" && !c.colW.p.a);
ok("纯点击: 不落盘/不重算/不挂拦截层/不排自清",
   c.persisted.length === 0 && c.recomputed === 0 &&
   byType("click").filter((l) => l.op === "add").length === 0 && timers.length === 0);

// 2-b 微动未过阈值(issue 26-11-08-0229 #10 修复回归): 位移 <=3px 不把起始快照写进生效轨 colWidths
resetRec();
c = mkCtx();
M.startResize.call(c, evAt(100), "p", "a");
fire("mousemove", { clientX: 102 });          // 位移 2 <= 阈值 3: dragged 仍 false
ok("微动未过阈值: 生效轨不被起始快照污染", !c.colWidths.p);
fire("mousemove", { clientX: 220 });          // 位移 120 > 阈值: 过阈值后照常写生效轨
ok("过阈值后生效轨照常写入", c.colWidths.p && c.colWidths.p.a === "320px" && c.colWidths.p.b === "150px");
fire("mouseup", {});
ok("微动后真拖拽: 意图升格/落盘/拦截层照常",
   c.colW.p.a === "320px" && c.colW.p.hid === "111px" && c.persisted.length === 1 &&
   byType("click").filter((l) => l.op === "add").length === 1);

// 3. 双击自适应(R5#52 后半): 同一套 merge, 适配列被适配备覆盖、隐藏列 px 仍在
resetRec();
c = mkCtx();
const headEl = { children: [{ scrollWidth: 400 }], parentElement: { querySelectorAll: () => [] } };
M.autoFitColumn.call(c, { target: { closest: () => headEl } }, "p", "a");
ok("双击自适应: 适配备 = 内容宽 + 18(夹在 [MIN, MAX_FIT_PX])", c.colW.p.a === "418px");
ok("双击自适应: 隐藏列 px 仍在 + 可见列被快照冻结", c.colW.p.hid === "111px" && c.colW.p.b === "150px");
ok("双击自适应: 生效态同步且落盘", c.colWidths.p.a === "418px" && c.persisted.length === 1);
console.log(JSON.stringify({
  ok: checks.filter((c) => c[1]).length, total: checks.length,
  failed: checks.filter((c) => !c[1]).map((c) => c[0]),
}));
"""

# R5#51: AQB_SELECTION 选择联动状态机 ----------------------------------------------
_NODE_SELECTION_PROBE = r"""
const fs = require("fs");
global.window = {};
const src = fs.readFileSync(process.argv[1], "utf8");
eval(src + "\n;globalThis.__W2__ = window.AQB_SELECTION;");
const M = globalThis.__W2__.methods;

const memberHashesOf = (list) => (list || []).map((m) => (typeof m === "string" ? m : (m && m.hash) || "")).filter(Boolean);
// 真实组 A(两成员) / B(单成员) + 虚拟行 u-h9(未归组命中种子)
const GROUPS = [
  { key: "A", members: [{ hash: "h1" }, { hash: "h2" }] },
  { key: "B", members: [{ hash: "h3" }] },
  { key: "u-h9", virtual: true, members: [{ hash: "h9" }] },
];
const mkCtx = (over) => Object.assign({}, M, {
  memberHashesOf,
  decoratedGroups: GROUPS,
  filteredGroups: GROUPS,
  filteredTorrents: [],
  selGroups: [],
  selMembers: [],
  selAnchorGroup: null,
  selAnchorMember: null,
  selAnchorUnit: null,
  kbCursor: null,
  expandedKey: null,
  viewMode: "groups",
  page: "groups",
}, over);
const checks = [];
const ok = (name, cond) => checks.push([name, !!cond]);

// --- _selSyncGroups 四态 ---
// 1. 补选: 成员凑齐 -> 组入选(成员 -> 组方向)
let c = mkCtx({ selMembers: ["h1", "h2"], selGroups: [] });
M._selSyncGroups.call(c);
ok("回扫补选: 组内成员全选 -> 组入选", JSON.stringify(c.selGroups) === JSON.stringify(["A"]));
// 2. 移出: 撤到不全 -> 组移出
c = mkCtx({ selMembers: ["h1"], selGroups: ["A", "B"] });
M._selSyncGroups.call(c);
ok("回扫移出: 撤掉一个成员 -> 不完整的组移出", c.selGroups.length === 0);
// 3. 未知 key 保留: 虚拟行/已消失的组不在回扫面里, 一律保留
c = mkCtx({ selMembers: ["h1", "h2"], selGroups: ["A", "Z", "u-h9"] });
M._selSyncGroups.call(c);
ok("不可解析的 key(未知组/虚拟行)保留不清理",
   c.selGroups.includes("Z") && c.selGroups.includes("u-h9") && c.selGroups.includes("A"));
// 4. 种子页降级: 不补选(decoratedGroups 只是冻结快照)但降级照做(不残留组 key 卷进批量载荷)
c = mkCtx({ viewMode: "torrents", selMembers: ["h1", "h2"], selGroups: [] });
M._selSyncGroups.call(c);
ok("种子页: 凑齐的组不补选(用户心智是我选了这些种子)", c.selGroups.length === 0);
c = mkCtx({ viewMode: "torrents", selMembers: ["h1"], selGroups: ["B"] });
M._selSyncGroups.call(c);
ok("种子页: 不完整的组仍降级移出(撤选残留组 key 会卷进批量载荷)", c.selGroups.length === 0);

// --- _selAnchor 兜底链(组) ---
c = mkCtx({ selAnchorGroup: "g2" });
ok("起点兜底链 1: 显式锚点在列表内 -> 用它", M._selAnchor.call(c, "group", ["g1", "g2", "g3"]) === "g2");
c = mkCtx({ selAnchorGroup: "gX", kbCursor: { kind: "group", id: "g3" } });
ok("起点兜底链 2: 锚点失效 -> 当前光标", M._selAnchor.call(c, "group", ["g1", "g2", "g3"]) === "g3");
c = mkCtx({ selAnchorGroup: "gX", kbCursor: { kind: "torrent", id: "h1" }, expandedKey: "g1" });
ok("起点兜底链 3: 光标不在此列表 -> 当前展开的组", M._selAnchor.call(c, "group", ["g1", "g2", "g3"]) === "g1");
c = mkCtx({});
ok("起点兜底链 4: 全缺 -> 列表首行", M._selAnchor.call(c, "group", ["g1", "g2", "g3"]) === "g1");
c = mkCtx({});
ok("空列表 -> null(调用方按无起点处理)", M._selAnchor.call(c, "group", []) === null);
// 成员 kind: 光标 kind=torrent 映射 member(键鼠统一模型)
c = mkCtx({ kbCursor: { kind: "torrent", id: "h5" } });
ok("成员起点: 光标 torrent 即成员上下文", M._selAnchor.call(c, "member", ["h4", "h5"]) === "h5");

// --- selSizeSummaryOf: occ_key 取 max 去重 ---
const sum = M.selSizeSummaryOf([
  { hash: "h1", occ_key: "k", size: 100 },
  { hash: "h2", occ_key: "k", size: 250 },
  { hash: "h3", size: 70 },
]);
ok("实际占用按 occ_key 单元取 max 去重(250+70), 合计逐成员求和(420)",
   sum.total === 420 && sum.occupy === 320);
ok("无选中 -> {0,0}", JSON.stringify(M.selSizeSummaryOf([])) === JSON.stringify({ total: 0, occupy: 0 }));
console.log(JSON.stringify({
  ok: checks.filter((c) => c[1]).length, total: checks.length,
  failed: checks.filter((c) => !c[1]).map((c) => c[0]),
}));
"""

# 部分组判定单点(计划 26-11-11-0820 S1, 拍板 D2): 五形态真跑 ------------------------
_NODE_PARTIAL_GROUPS_PROBE = r"""
const fs = require("fs");
global.window = {};
const src = fs.readFileSync(process.argv[1], "utf8");
eval(src + "\n;globalThis.__W2__ = window.AQB_SELECTION;");
const M = globalThis.__W2__.methods;

const memberHashesOf = (list) => (list || []).map((m) => (typeof m === "string" ? m : (m && m.hash) || "")).filter(Boolean);
// 真实组 A(两成员) / C(三成员) / B(单成员) + 虚拟行 u-h9(单成员) + 双成员虚拟行 u-v2
// (u-v2 专钉 virtual 判据: 若判定只看 total<=1, 双成员虚拟行会被误触发)
const GROUPS = [
  { key: "A", name: "组A", members: [{ hash: "h1" }, { hash: "h2" }] },
  { key: "C", name: "组C", members: [{ hash: "h4" }, { hash: "h5" }, { hash: "h6" }] },
  { key: "B", name: "组B", members: [{ hash: "h3" }] },
  { key: "u-h9", virtual: true, members: [{ hash: "h9" }] },
  { key: "u-v2", virtual: true, members: [{ hash: "v1" }, { hash: "v2" }] },
];
const mkCtx = (over) => Object.assign({}, M, {
  memberHashesOf,
  decoratedGroups: GROUPS,
  filteredGroups: GROUPS,
}, over);
const P = (keys, hashes, over) => M._partialGroupsOf.call(mkCtx(over || {}), keys, hashes);
const checks = [];
const ok = (name, cond) => checks.push([name, !!cond]);

// --- 形态1: 组键整组入选 -> 不触发(返回不含该组) ---
ok("形态1: 组键整组入选 -> 不触发", P(["A"], []).length === 0);
ok("形态1: 组键入选且成员 hash 也在袋里(双向联动同存) -> 仍不触发", P(["A"], ["h1", "h2"]).length === 0);
// --- 形态2: 成员全选(自动晋升组键) -> 不触发 ---
ok("形态2: 成员全选+组键已晋升 -> 不触发", P(["A"], ["h1", "h2"]).length === 0);
ok("形态2: 成员全选但组键未晋升(种子页降级场景) -> 不触发(sel===total)", P([], ["h1", "h2"]).length === 0);
// --- 形态3: 部分选中 -> 触发且 sel/total 正确 ---
const p1 = P([], ["h1"]);
ok("形态3: 部分选中 -> 恰触发一例", p1.length === 1);
ok("形态3: sel/total/name 逐字段正确", p1.length === 1 && p1[0].key === "A" && p1[0].sel === 1 && p1[0].total === 2 && p1[0].name === "组A");
// --- 形态4: 跨组混合(整组 A 与部分组 C 并存) -> 只列部分组 ---
const p2 = P(["A"], ["h4"]);
ok("形态4: 整组 A + 部分组 C 并存 -> 只列 C", p2.length === 1 && p2[0].key === "C" && p2[0].sel === 1 && p2[0].total === 3);
// --- 形态5: 单成员组 + 虚拟行(未归组命中) -> 均不触发 ---
ok("形态5: 单成员组入口 -> 不触发(total<=1)", P([], ["h3"]).length === 0);
ok("形态5: 单成员虚拟行 -> 不触发", P([], ["h9"]).length === 0);
ok("形态5: 双成员虚拟行 -> 不触发(virtual 判据独立于 total<=1)", P([], ["v1"]).length === 0);
// --- 边界面: 不误拦(R6)/入参健壮性/name 兜底 ---
ok("空入参 -> 空返回(不抛)", P([], []).length === 0 && P(null, null).length === 0);
ok("hash 不属任何组 -> 不触发", P([], ["zz"]).length === 0);
ok("name 缺失 -> 兜组 key", (() => {
  const r = M._partialGroupsOf.call(
    { memberHashesOf, decoratedGroups: [{ key: "X", members: [{ hash: "a" }, { hash: "b" }] }] },
    [], ["a"]);
  return r.length === 1 && r[0].name === "X" && r[0].sel === 1 && r[0].total === 2;
})());
ok("decoratedGroups 缺失(极端竞态) -> 空返回不抛", (() => {
  try { return M._partialGroupsOf.call({ memberHashesOf }, [], ["h1"]).length === 0; }
  catch (e) { return false; }
})());
console.log(JSON.stringify({
  ok: checks.filter((c) => c[1]).length, total: checks.length,
  failed: checks.filter((c) => !c[1]).map((c) => c[0]),
}));
"""

# S2 删除链部分组行(计划 26-11-11-0820 S2, 拍板 D5)落点级真跑 ------------------------
_NODE_DELETE_PARTIAL_ROW_PROBE = r"""
const fs = require("fs");
global.window = {};
global.L10N_GROUP = "辅种";  // app.js 顶部常量, _deleteDetails 多目标分支引用
const selSrc = fs.readFileSync(process.argv[1], "utf8");
eval(selSrc + "\n;globalThis.__SEL__ = window.AQB_SELECTION;");
const delSrc = fs.readFileSync(process.argv[2], "utf8");
eval(delSrc + "\n;globalThis.__DEL__ = window.AQB_DELETE;");
// 两 mixin 方法合并进同一 ctx(生产是 app.mixin 逐个注入同一 Vue 实例, this 等价):
// _deleteDetails 经 this._findGroup/_partialGroupsOf/selSizeSummaryOf 跨模块消费 selection.js
const M = Object.assign({}, globalThis.__SEL__.methods, globalThis.__DEL__.methods);

const memberHashesOf = (list) => (list || []).map((m) => (typeof m === "string" ? m : (m && m.hash) || "")).filter(Boolean);
// 组 A(两成员)/C(三成员)/E/F(各两成员)/B(单成员) + 虚拟行 u-h9(同 S1 电池族谱)
const GROUPS = [
  { key: "A", name: "组A", members: [{ hash: "h1", size: 10, site: "s1", save_path: "/p1" }, { hash: "h2", size: 10 }] },
  { key: "C", name: "组C", members: [{ hash: "h4", size: 5 }, { hash: "h5", size: 5 }, { hash: "h6", size: 5 }] },
  { key: "E", name: "组E", members: [{ hash: "e1", size: 7 }, { hash: "e2", size: 7 }] },
  { key: "F", name: "组F", members: [{ hash: "f1", size: 3 }, { hash: "f2", size: 3 }] },
  { key: "B", name: "组B", members: [{ hash: "h3", size: 1 }] },
  { key: "u-h9", virtual: true, members: [{ hash: "h9", size: 1 }] },
];
const memberByHash = new Map();
for (const g of GROUPS) for (const m of g.members) memberByHash.set(m.hash, m);
const mkCtx = (over) => Object.assign({}, M, {
  memberHashesOf,
  memberByHash,
  decoratedGroups: GROUPS,
  filteredGroups: GROUPS,
  fmtSize: (v) => String(v),  // 电池不打大小文案, 桩掉 format.js 依赖
}, over);
const D = (keys, hashes, over) => M._deleteDetails.call(mkCtx(over || {}), keys, hashes);
const partialRows = (rows) => rows.filter((r) => r.label === "部分组");
const checks = [];
const ok = (name, cond) => checks.push([name, !!cond]);

// --- 正例: 部分组目标 -> 确认框 details 恰含一行(tone error/wide/#i-warn, HR 风险行同款) ---
const rows1 = D([], ["h1"]);
const row1 = partialRows(rows1)[0];
ok("部分组目标 -> details 恰含一行部分组行", partialRows(rows1).length === 1);
ok("行形态同款 HR 风险行: tone=error / wide / icon=#i-warn", row1 && row1.tone === "error" && row1.wide === true && row1.icon === "#i-warn");
ok("单组文案逐字段: 组名/已选 1/2/钉住词「将缺文件」", row1 && row1.value === "辅种组「组A」: 已选 1/2 个 —— 若勾选『同时删除磁盘文件』,其余 1 个成员将缺文件");

// --- 多组聚合: 已选/总数与缺口用合计, 不逐组多行 ---
const rows2 = D([], ["h1", "h4", "h5"]);
const row2 = partialRows(rows2)[0];
ok("两组部分选中 -> 一行聚合(不逐组多行)", partialRows(rows2).length === 1);
ok("聚合 M/N 用合计(1+2 / 2+3), 缺口 2", row2 && row2.value === "辅种组「组A」「组C」: 已选 3/5 个 —— 若勾选『同时删除磁盘文件』,其余 2 个成员将缺文件");

// --- 组名上限 3 个 +「等 K 个」(照 _hrRiskOf 模式) ---
const rows3 = D([], ["h1", "h4", "e1", "f1"]);
const row3 = partialRows(rows3)[0];
ok("四组部分选中 -> 组名列前 3 个 + 等 4 个, 合计 4/9 缺口 5", row3 && row3.value === "辅种组「组A」「组C」「组E」等 4 个: 已选 4/9 个 —— 若勾选『同时删除磁盘文件』,其余 5 个成员将缺文件");

// --- 跨组混合(D2 触发面, S5 落点级钉): 整组 A 组键入选 + 部分组 C 散员 -> 行照出且只列 C ---
// (落点若引入「keys 非空即短路」类回归, S1 谓词电池不红, 本断言兜住)
const rowsMix = D(["A"], ["h4"]);
const rowMix = partialRows(rowsMix)[0];
ok("跨组混合(整组 A 组键入选 + 部分组 C 散员) -> 恰一行且只列 C(整组 A 不进文案)",
   partialRows(rowsMix).length === 1 && rowMix &&
   rowMix.value === "辅种组「组C」: 已选 1/3 个 —— 若勾选『同时删除磁盘文件』,其余 2 个成员将缺文件");

// --- 负例(D2 不触发面) -> 无该行 ---
ok("整组删除(组键入选) -> 无该行", partialRows(D(["A"], [])).length === 0);
ok("成员全选未晋升(种子页降级 sel===total) -> 无该行", partialRows(D([], ["h1", "h2"])).length === 0);
ok("单成员组种子 -> 无该行", partialRows(D([], ["h3"])).length === 0);
ok("虚拟行(未归组命中) -> 无该行", partialRows(D([], ["h9"])).length === 0);
ok("hash 不属任何组 -> 无该行", partialRows(D([], ["zz"])).length === 0);
ok("空入参 -> 无该行不抛", partialRows(D([], [])).length === 0);

// --- 恒显面(D5): 行与 delete_files 勾选状态无关恒显由结构保证 ---
ok("_deleteDetails 形参只有 keys/hashes(无勾选入参)", M._deleteDetails.length === 2);
ok("部分组行是行流末行(既有五行/六行结构零改动, 只追加)", rows1[rows1.length - 1] === row1);

console.log(JSON.stringify({
  ok: checks.filter((c) => c[1]).length, total: checks.length,
  failed: checks.filter((c) => !c[1]).map((c) => c[0]),
}));
"""

# S3 迁移关部分组确认框(计划 26-11-11-0820, 拍板 D3)落点级真跑 ------------------------
_NODE_MOVE_PARTIAL_GATE_PROBE = r"""
const fs = require("fs");
global.window = { AQB_DRAWER_TPL_REG: { helpers: {} } };
const selSrc = fs.readFileSync(process.argv[1], "utf8");
eval(selSrc + "\n;globalThis.__SEL__ = window.AQB_SELECTION;");
const drawerSrc = fs.readFileSync(process.argv[2], "utf8");
eval(drawerSrc + "\n;globalThis.__DRW__ = window.AQB_DRAWER;");
// 两 mixin 方法合并进同一 ctx(生产是 app.mixin 逐个注入同一 Vue 实例, this 等价):
// submitMoveDialog 经 this._partialGroupsOf/_partialGroupsSummary 跨模块消费 selection.js
const M = Object.assign({}, globalThis.__SEL__.methods, globalThis.__DRW__.methods);

const memberHashesOf = (list) => (list || []).map((m) => (typeof m === "string" ? m : (m && m.hash) || "")).filter(Boolean);
// 组族谱与 S2 电池同款: A(两成员)/C(三成员)/E/F(各两成员)/B(单成员)+ 虚拟行 u-h9
const GROUPS = [
  { key: "A", name: "组A", members: [{ hash: "h1" }, { hash: "h2" }] },
  { key: "C", name: "组C", members: [{ hash: "h4" }, { hash: "h5" }, { hash: "h6" }] },
  { key: "E", name: "组E", members: [{ hash: "e1" }, { hash: "e2" }] },
  { key: "F", name: "组F", members: [{ hash: "f1" }, { hash: "f2" }] },
  { key: "B", name: "组B", members: [{ hash: "h3" }] },
  { key: "u-h9", virtual: true, members: [{ hash: "h9" }] },
];
const mkCtx = (over) => {
  const c = Object.assign({}, M, {
    memberHashesOf,
    decoratedGroups: GROUPS,
    filteredGroups: GROUPS,
    flags: { relocate_enabled: false },
    moveBusy: false, moveOpen: true, movePathInput: "/dst",
    moveSingleHash: "h1", moveTargets: { groupKeys: [], memberHashes: ["h1"] }, moveScope: "",
    modalResult: true, postResult: true,
    modalCalls: [], posts: [], reopens: [], toasts: [],
  }, over);
  c.toast = (msg, kind) => c.toasts.push({ msg, kind });
  c._openModal = async (cfg) => { c.modalCalls.push({ cfg, moveOpenAtCall: c.moveOpen }); return c.modalResult; };
  c.openMoveDialog = (targets, scope, singleHash, prefill) => {
    c.reopens.push({ targets, scope, singleHash, prefill });
    c.moveOpen = true;
  };
  c._editPost = async (hash, action, body) => { c.posts.push({ via: "single", hash, action, body }); return c.postResult; };
  c._bulkEditPost = async (targets, action, extra) => { c.posts.push({ via: "bulk", targets, action, extra }); return c.postResult; };
  return c;
};
const checks = [];
const ok = (name, cond) => checks.push([name, !!cond]);

(async () => {
  // --- 正例: 部分组 + 迁移关 -> 确认框拦截, 确认后正常发单 ---
  let c = mkCtx({});
  await c.submitMoveDialog();
  ok("部分组+迁移关: 恰弹一次确认框, 投递恰一次", c.modalCalls.length === 1 && c.posts.length === 1);
  ok("弹层顺序(R3): 确认框打开时设定位置框已先收", c.modalCalls[0].moveOpenAtCall === false);
  const cfg = c.modalCalls[0].cfg;
  ok("确认框形态: tone error / danger 钮 / wide / #i-warn",
     cfg.tone === "error" && cfg.danger === true && cfg.wide === true);
  const row = cfg.details[0];
  ok("行形态: label=部分组 / tone=error / wide / icon=#i-warn",
     row.label === "部分组" && row.tone === "error" && row.wide === true && row.icon === "#i-warn");
  ok("文案钉住词: 「将缺文件」+「整组迁移」", /将缺文件/.test(row.value) && /整组迁移/.test(row.value));
  ok("单组文案逐字段(组名/已选 1/2/其余 1/建议语)",
     row.value === "辅种组「组A」: 已选 1/2 个,其余 1 个成员将缺文件;建议改选整组或开启整组迁移");
  ok("确认后首发带 confirm=true(后端部分组闸放行位, issue 26-11-11-0823)",
     c.posts[0].via === "single" && c.posts[0].body.location === "/dst" && c.posts[0].body.confirm === true);
  ok("发单成功后设定位置框保持收起, 确认框不重开", c.moveOpen === false && c.modalCalls.length === 1);

  // --- 取消: 留在设定位置框(带原路径重开), 零投递 ---
  c = mkCtx({ modalResult: false });
  await c.submitMoveDialog();
  ok("取消: 零投递(确认才发)", c.posts.length === 0);
  ok("取消: 带原路径重开设定位置框", c.reopens.length === 1 && c.reopens[0].prefill === "/dst" && c.moveOpen === true);

  // --- 确认后投递失败: 框已被闸先收 -> 照 confirm 回路失败分支带原路径重开(手输路径不丢) ---
  c = mkCtx({ postResult: false });
  await c.submitMoveDialog();
  ok("确认+投递失败: 恰弹一次确认框 + 恰一次投递", c.modalCalls.length === 1 && c.posts.length === 1);
  ok("确认+投递失败: 带原路径重开设定位置框", c.reopens.length === 1 && c.reopens[0].prefill === "/dst" && c.moveOpen === true);
  // 对照: 非闸失败(直发, 框从未收)维持现状口径 —— 留开着不重开
  c = mkCtx({ postResult: false, moveTargets: { groupKeys: ["A"], memberHashes: [] } });
  await c.submitMoveDialog();
  ok("非闸失败(直发): 框从未收, 无重开", c.reopens.length === 0 && c.moveOpen === true && c.modalCalls.length === 0);

  // --- 多组聚合(与 S2 共用 _partialGroupsSummary 单点): 前 3 + 等 K 个, 合计口径 ---
  c = mkCtx({ moveTargets: { groupKeys: [], memberHashes: ["h1", "h4", "e1", "f1"] }, moveSingleHash: "" });
  await c.submitMoveDialog();
  ok("四组聚合: 组名前 3 + 等 4 个, 合计 4/9 缺口 5",
     c.modalCalls[0].cfg.details[0].value ===
       "辅种组「组A」「组C」「组E」等 4 个: 已选 4/9 个,其余 5 个成员将缺文件;建议改选整组或开启整组迁移");
  ok("批量目标(无 singleHash)确认后走 _bulkEditPost", c.posts.length === 1 && c.posts[0].via === "bulk");

  // --- 跨组混合(D2 触发面, S5 落点级钉): 整组 A 组键入选 + 部分组 C 散员 -> 闸照触发且只列 C ---
  // (落点若引入「keys 非空即短路」类回归, S1 谓词电池不红, 本断言兜住)
  c = mkCtx({ moveTargets: { groupKeys: ["A"], memberHashes: ["h4"] }, moveSingleHash: "" });
  await c.submitMoveDialog();
  ok("跨组混合(整组 A 组键入选 + 部分组 C 散员): 闸照触发, 文案只列 C(整组 A 不进文案)",
     c.modalCalls.length === 1 && c.posts.length === 1 &&
     c.modalCalls[0].cfg.details[0].value ===
       "辅种组「组C」: 已选 1/3 个,其余 2 个成员将缺文件;建议改选整组或开启整组迁移");

  // --- 负例(D3): 非部分组直发零新增弹层 ---
  c = mkCtx({ moveTargets: { groupKeys: ["A"], memberHashes: [] } });
  await c.submitMoveDialog();
  ok("整组入选(组键级联)+迁移关: 直发零弹层", c.modalCalls.length === 0 && c.posts.length === 1);
  c = mkCtx({ moveTargets: { groupKeys: [], memberHashes: ["h1", "h2"] } });
  await c.submitMoveDialog();
  ok("成员全选未晋升(sel===total): 直发零弹层", c.modalCalls.length === 0 && c.posts.length === 1);
  c = mkCtx({ moveTargets: { groupKeys: [], memberHashes: ["h3"] } });
  await c.submitMoveDialog();
  ok("单成员组种子: 直发零弹层", c.modalCalls.length === 0 && c.posts.length === 1);
  c = mkCtx({ moveTargets: { groupKeys: [], memberHashes: ["h9"] } });
  await c.submitMoveDialog();
  ok("虚拟行(未归组命中): 直发零弹层", c.modalCalls.length === 0 && c.posts.length === 1);
  c = mkCtx({ moveTargets: { groupKeys: [], memberHashes: ["zz"] } });
  await c.submitMoveDialog();
  ok("hash 不属任何组: 直发零弹层", c.modalCalls.length === 0 && c.posts.length === 1);

  // --- 旗标两态(D3/R6): 迁移开不弹(S4 披露条的面); 旗标解析不出静默直发不误拦 ---
  c = mkCtx({ flags: { relocate_enabled: true } });
  await c.submitMoveDialog();
  ok("迁移开(relocate_enabled)+部分组: 直发零弹层(S4 披露条的面)", c.modalCalls.length === 0 && c.posts.length === 1);
  c = mkCtx({ flags: undefined });
  await c.submitMoveDialog();
  ok("flags 解析不出(R6): 静默直发不误拦", c.modalCalls.length === 0 && c.posts.length === 1);
  c = mkCtx({ flags: { relocate_enabled: undefined } });
  await c.submitMoveDialog();
  ok("relocate_enabled 解析不出(R6): 静默直发不误拦", c.modalCalls.length === 0 && c.posts.length === 1);
  c = mkCtx({ decoratedGroups: undefined });
  await c.submitMoveDialog();
  ok("decoratedGroups 缺失(R6 竞态): 不抛不误拦, 直发", c.modalCalls.length === 0 && c.posts.length === 1);
})().then(() => {
  console.log(JSON.stringify({
    ok: checks.filter((x) => x[1]).length, total: checks.length,
    failed: checks.filter((x) => !x[1]).map((x) => x[0]),
  }));
}).catch((e) => { console.error(e && e.stack || e); process.exit(1); });
"""

# S4 迁移开部分组披露条(计划 26-11-11-0820, 拍板 D4)落点级真跑 ------------------------
_NODE_MOVE_PARTIAL_DISCLOSURE_PROBE = r"""
const fs = require("fs");
global.window = { AQB_DRAWER_TPL_REG: { helpers: {} } };
const selSrc = fs.readFileSync(process.argv[1], "utf8");
eval(selSrc + "\n;globalThis.__SEL__ = window.AQB_SELECTION;");
const drawerSrc = fs.readFileSync(process.argv[2], "utf8");
eval(drawerSrc + "\n;globalThis.__DRW__ = window.AQB_DRAWER;");
// 两 mixin 方法合并进同一 ctx(生产是 app.mixin 逐个注入同一 Vue 实例, this 等价):
// openMoveDialog 经 this._partialGroupsOf/_partialGroupsSummary 跨模块消费 selection.js
const M = Object.assign({}, globalThis.__SEL__.methods, globalThis.__DRW__.methods);

const memberHashesOf = (list) => (list || []).map((m) => (typeof m === "string" ? m : (m && m.hash) || "")).filter(Boolean);
// 组族谱与 S3 电池同款: A(两成员)/C(三成员)/E/F(各两成员)/B(单成员)+ 虚拟行 u-h9
const GROUPS = [
  { key: "A", name: "组A", members: [{ hash: "h1" }, { hash: "h2" }] },
  { key: "C", name: "组C", members: [{ hash: "h4" }, { hash: "h5" }, { hash: "h6" }] },
  { key: "E", name: "组E", members: [{ hash: "e1" }, { hash: "e2" }] },
  { key: "F", name: "组F", members: [{ hash: "f1" }, { hash: "f2" }] },
  { key: "B", name: "组B", members: [{ hash: "h3" }] },
  { key: "u-h9", virtual: true, members: [{ hash: "h9" }] },
];
const mkCtx = (over) => {
  const c = Object.assign({}, M, {
    memberHashesOf,
    decoratedGroups: GROUPS,
    filteredGroups: GROUPS,
    flags: { relocate_enabled: true },
    moveOpen: false, movePartialDisclosure: "stale",  // 非开框残留值: 验证开框必复位
    $refs: {}, loadMoveOptionsCalls: 0,
  }, over);
  c.loadMoveOptions = () => { c.loadMoveOptionsCalls += 1; };
  c.$nextTick = (fn) => fn();
  c.ensureWebFlags = async () => {};  // 沙箱无 web flags 层: openMoveDialog 入口惰性补拉接线(e1fbd849), 照 loadMoveOptions 范式 stub —— 缺桩则开框即 TypeError
  return c;
};
const checks = [];
const ok = (name, cond) => checks.push([name, !!cond]);

// --- 正例: 部分组 + 迁移开 -> 披露条数据非 null, 逐字段 ---
let c = mkCtx({});
c.openMoveDialog({ groupKeys: [], memberHashes: ["h1"] }, "", "h1", "");
ok("部分组+迁移开: 披露数据非 null(开框即算)", c.movePartialDisclosure !== null);
ok("单组逐字段(names/sel/total/gap = 组A 1/2 缺 1)",
   c.movePartialDisclosure.names === "「组A」" && c.movePartialDisclosure.sel === 1
   && c.movePartialDisclosure.total === 2 && c.movePartialDisclosure.gap === 1);
ok("开框既有状态机零破坏(moveOpen/moveCount/movePathInput/候选拉取照常)",
   c.moveOpen === true && c.moveCount === 1 && c.movePathInput === "" && c.loadMoveOptionsCalls === 1);

// --- 多组聚合(与 S2/S3 共用 _partialGroupsSummary 单点): 前 3 + 等 K 个, 合计口径 ---
c = mkCtx({});
c.openMoveDialog({ groupKeys: [], memberHashes: ["h1", "h4", "e1", "f1"] }, "", "", "");
ok("四组聚合: 组名前 3 + 等 4 个, 合计 4/9 缺口 5",
   c.movePartialDisclosure && c.movePartialDisclosure.names === "「组A」「组C」「组E」等 4 个"
   && c.movePartialDisclosure.sel === 4 && c.movePartialDisclosure.total === 9
   && c.movePartialDisclosure.gap === 5);

// --- 跨组混合(D2 触发面, S5 落点级钉): 整组 A 组键入选 + 部分组 C 散员 -> 披露只列部分组 ---
// (落点若引入「keys 非空即短路」类回归, S1 谓词电池不红, 本断言兜住)
c = mkCtx({});
c.openMoveDialog({ groupKeys: ["A"], memberHashes: ["h4"] }, "", "", "");
ok("跨组混合(整组 A 组键入选 + 部分组 C 散员): 披露只列 C(整组 A 不进文案), 1/3 缺 2",
   c.movePartialDisclosure && c.movePartialDisclosure.names === "「组C」"
   && c.movePartialDisclosure.sel === 1 && c.movePartialDisclosure.total === 3
   && c.movePartialDisclosure.gap === 2);

// --- 负例(D2 不触发面): 非部分组开框无条 ---
c = mkCtx({});
c.openMoveDialog({ groupKeys: ["A"], memberHashes: [] }, "", "", "");
ok("整组入选(组键级联)+迁移开: 无条", c.movePartialDisclosure === null);
c = mkCtx({});
c.openMoveDialog({ groupKeys: [], memberHashes: ["h1", "h2"] }, "", "", "");
ok("成员全选未晋升(sel===total)+迁移开: 无条", c.movePartialDisclosure === null);
c = mkCtx({});
c.openMoveDialog({ groupKeys: [], memberHashes: ["h3"] }, "", "", "");
ok("单成员组种子+迁移开: 无条", c.movePartialDisclosure === null);
c = mkCtx({});
c.openMoveDialog({ groupKeys: [], memberHashes: ["h9"] }, "", "", "");
ok("虚拟行(未归组命中)+迁移开: 无条", c.movePartialDisclosure === null);
c = mkCtx({});
c.openMoveDialog({ groupKeys: [], memberHashes: ["zz"] }, "", "", "");
ok("hash 不属任何组+迁移开: 无条", c.movePartialDisclosure === null);

// --- 降级面(R6/D4): 迁移关(S3 的面)/旗标解析不出/组数据缺失 一律无条不抛 ---
c = mkCtx({ flags: { relocate_enabled: false } });
c.openMoveDialog({ groupKeys: [], memberHashes: ["h1"] }, "", "h1", "");
ok("迁移关(relocate_enabled===false)+部分组: 无条(S3 确认框的面)", c.movePartialDisclosure === null);
c = mkCtx({ flags: undefined });
c.openMoveDialog({ groupKeys: [], memberHashes: ["h1"] }, "", "h1", "");
ok("flags 解析不出(R6): 无条不抛", c.movePartialDisclosure === null);
c = mkCtx({ flags: { relocate_enabled: undefined } });
c.openMoveDialog({ groupKeys: [], memberHashes: ["h1"] }, "", "h1", "");
ok("relocate_enabled 解析不出(R6): 无条不抛", c.movePartialDisclosure === null);
c = mkCtx({ decoratedGroups: undefined });
c.openMoveDialog({ groupKeys: [], memberHashes: ["h1"] }, "", "h1", "");
ok("decoratedGroups 缺失(R6 竞态): 无条不抛, 开框不阻断", c.movePartialDisclosure === null && c.moveOpen === true);

// --- 重开复位: 残留值必被清(S3 取消重开路径迁移关无条; 迁移开重开现算) ---
c = mkCtx({ flags: { relocate_enabled: false } });
c.openMoveDialog({ groupKeys: [], memberHashes: ["h1"] }, "", "h1", "");
c.openMoveDialog({ groupKeys: [], memberHashes: ["h1"] }, "", "h1", "");
ok("迁移关重开(含 S3 取消带原路径重开): 无条", c.movePartialDisclosure === null);
c = mkCtx({});
c.openMoveDialog({ groupKeys: [], memberHashes: ["h1"] }, "", "h1", "");
c.openMoveDialog({ groupKeys: [], memberHashes: ["zz"] }, "", "", "");
ok("迁移开重开现算: 上一框的披露被新目标覆盖(部分组 -> 非部分组无条)",
   c.movePartialDisclosure === null);

console.log(JSON.stringify({
  ok: checks.filter((x) => x[1]).length, total: checks.length,
  failed: checks.filter((x) => !x[1]).map((x) => x[0]),
}));
"""


# R5#18: loadColState 默认隐藏播种语义 ---------------------------------------------
def _app_head_source():
    """app.js 截到 loadColState 结束(其后是模块级 initialColState 消费与 createApp 接线, 不进沙箱)"""
    src = open(os.path.join(STATIC_ROOT, "shared", "app.js"), encoding="utf-8").read()
    marker = "const initialColState = loadColState();"
    return src[:src.index(marker)]


_NODE_LOADCOLSTATE_PROBE = r"""
const fs = require("fs");
global.Vue = { createApp: () => ({}) };   // app.js 头部 `const { createApp } = Vue;`
global.window = {};
let store = {};
global.localStorage = {
  getItem: (k) => (k in store ? store[k] : null),
  setItem: (k, v) => { store[k] = String(v); },
  removeItem: (k) => { delete store[k]; },
};
const src = fs.readFileSync(process.argv[1], "utf8");
// 函数声明与 const 都在同一份 eval 里, 断言闭包捕获后从外面驱动
eval(src + "\n;globalThis.__X = { LC: loadColState, pages: ALL_TABLE_PAGES, cols: TABLE_COLUMNS, hidden: DEFAULT_HIDDEN_KEYS };");
const LC = globalThis.__X.LC;
const PAGES = globalThis.__X.pages;
const COLS = globalThis.__X.cols;
const DEF = globalThis.__X.hidden;
const lockedKey = (p) => { const c = COLS[p].find((c) => c.locked); return c ? c.key : null; };
const defaultsOf = (p) => COLS[p].map((c) => c.key).filter((k) => DEF.has(k));
const setStore = (pages) => {
  store = { autoqb_cols_v5: JSON.stringify({ v: 5, origin: "http://x", pages }) };
};
const checks = [];
const ok = (name, cond) => checks.push([name, !!cond]);

// 1. 空存储: 每页播种 = 本表列 key 与 DEFAULT_HIDDEN_KEYS 的交集
setStore({});
let out = LC();
let seedOk = true;
let anyDefault = false;
for (const p of PAGES) {
  const want = defaultsOf(p);
  if (want.length) anyDefault = true;
  if (JSON.stringify(out.hidden[p] || []) !== JSON.stringify(want)) { seedOk = false; break; }
}
ok("空存储: 从无偏好的页按 DEFAULT_HIDDEN_KEYS 交集播种", seedOk && anyDefault);
ok("空存储: order/w 全空", Object.keys(out.order).length === 0 && Object.keys(out.w).length === 0);

// 2. 仅空 hidden: 该页不播(「刻意全开」是合法偏好), 未定制过的页照播
setStore({ group: { hidden: [] } });
out = LC();
ok("仅空 hidden 的页不播(刻意全开不被默认值覆盖)", JSON.stringify(out.hidden.group || []) === "[]");
const torrentDefaults = defaultsOf("torrent");
ok("未定制过的页照常播种(提前 return 会把默认隐藏列全放出来)", torrentDefaults.length > 0 &&
   JSON.stringify(out.hidden.torrent || []) === JSON.stringify(torrentDefaults));

// 3. 有任一偏好键(哪怕只定制了 order): 该页不播; locked 列即使被写进存储也忽略
const lk = lockedKey("torrent");  // torrent 表的 locked 列 = "name"
setStore({ torrent: { hidden: [lk, "amount_left"] }, group: { order: ["name"] } });
out = LC();
ok("仅定制 order 的页不播(三键全缺才播)", !out.hidden.group && out.order.group[0] === "name");
ok("存储里的 locked 列被忽略, 非 locked 默认隐藏列保留",
   !(out.hidden.torrent || []).includes(lk) && (out.hidden.torrent || []).includes("amount_left"));

// 4. w 白名单洗净: 只收合法列 key 的 "<num>px"; 洗净后三键全缺照播
setStore({ torrent: { w: { name: "120px", bogus: "50px", size: "1.5px", eta: "0px" } } });
out = LC();
ok("w 白名单: 非法 key/小数 px 丢弃, 合法 <num>px 收下",
   JSON.stringify(out.w.torrent) === JSON.stringify({ name: "120px", eta: "0px" }));
ok("w 洗净后非空的页不播", !out.hidden.torrent);
setStore({ detail: { w: { bogus: "50px", size: "1.5px" } } });
out = LC();
ok("w 全被洗净 = 三键全缺 -> 该页照播(坏数据也走完整流程)", JSON.stringify(out.hidden.detail || []) === JSON.stringify(defaultsOf("detail")));

// 5. 坏 JSON: 归空意图 + 播种照常(与空存储同形)
store = { autoqb_cols_v5: "{broken" };
out = LC();
ok("坏 JSON: 走完整流程, 播种不缺席", JSON.stringify(out.hidden.torrent || []) === JSON.stringify(defaultsOf("torrent")));
console.log(JSON.stringify({
  ok: checks.filter((c) => c[1]).length, total: checks.length,
  failed: checks.filter((c) => !c[1]).map((c) => c[0]),
}));
"""

# R5#54: AQB_SORT 三态循环 + 比较器 ------------------------------------------------
_NODE_SORT_PROBE = r"""
const fs = require("fs");
// 排序注册表(单点在 app.js, 电池自给): 经典 gk/gd 形态 + dyn(dtSortState 映射)形态各一
global.ALL_TABLE_DEFS = {
  group: { sort: { gk: "sortKey", gd: "sortDir", defKey: "added_on", defDir: -1 } },
  d0: { sort: { dyn: true, defKey: "added_on", defDir: -1 } },
  // defKey 非空 + 默认升序(用户表 addr/1、Tracker sev/1): 默认列首击必须切降序, 三击全 no-op 是缺陷
  dPos: { sort: { dyn: true, defKey: "addr", defDir: 1 } },
  dEmpty: { sort: { dyn: true, defKey: "", defDir: 1 } },
};
global.VIEW_TABLE = { groups: "group" };
global.DRAWER_TABLE_DEFS = { d0: { sort: { dyn: true, defKey: "", defDir: -1 } } };
global.window = {};
const src = fs.readFileSync(process.argv[1], "utf8");
eval(src + "\n;globalThis.__W2__ = window.AQB_SORT;");
const M = globalThis.__W2__.methods;
const mkCtx = (over) => Object.assign({}, M, {
  viewMode: "groups",
  sortKey: "added_on", sortDir: -1,
  dtSortState: {},
}, over);
const checks = [];
const ok = (name, cond) => checks.push([name, !!cond]);

// 1. 经典三态: 新键降序 -> 同键升序 -> 第三击回默认
let c = mkCtx();
M.setSort.call(c, "name");
ok("三态一击: 新键降序", c.sortKey === "name" && c.sortDir === -1);
M.setSort.call(c, "name");
ok("三态二击: 同键升序", c.sortKey === "name" && c.sortDir === 1);
M.setSort.call(c, "name");
ok("三态三击: 恢复默认(最近添加降序)", c.sortKey === "added_on" && c.sortDir === -1);

// 2. dyn 形态(dtSortState 映射): 同一三态循环, 单元懒建
c = mkCtx();
M.setSort.call(c, "size", "d0");
ok("dyn 一击: 新键降序(cell 懒建保响应式)",
   c.dtSortState.d0 && c.dtSortState.d0.key === "size" && c.dtSortState.d0.dir === -1);
M.setSort.call(c, "size", "d0");
ok("dyn 二击: 同键升序", c.dtSortState.d0.dir === 1);
M.setSort.call(c, "size", "d0");
ok("dyn 三击: 回默认键", c.dtSortState.d0.key === "added_on" && c.dtSortState.d0.dir === -1);

// 2b. 默认升序非空键(dPos: addr/1)默认列首击: 修复前初始 cell==(addr,1), 三击全 no-op;
//     修复后一击降序 -> 二击升序 -> 三击仍降序(默认列不原地复位), 非默认列三态照常复位默认
c = mkCtx();
ok("默认升序键: 初始 cell=默认(addr/1)", c.dtSortState.dPos === undefined &&
   JSON.stringify(M.dtSortCell.call(c, "dPos")) === JSON.stringify({ key: "addr", dir: 1 }));
M.setSort.call(c, "addr", "dPos");
ok("默认升序键: 默认列一击=降序(缺陷修复核心)", c.dtSortState.dPos.key === "addr" && c.dtSortState.dPos.dir === -1);
M.setSort.call(c, "addr", "dPos");
ok("默认升序键: 默认列二击=升序", c.dtSortState.dPos.dir === 1);
M.setSort.call(c, "addr", "dPos");
ok("默认升序键: 默认列三击=降序(非 no-op)", c.dtSortState.dPos.dir === -1);
c = mkCtx();
M.setSort.call(c, "client", "dPos");
ok("默认升序键: 非默认列一击=降序", c.dtSortState.dPos.key === "client" && c.dtSortState.dPos.dir === -1);
M.setSort.call(c, "client", "dPos");
ok("默认升序键: 非默认列二击=升序", c.dtSortState.dPos.dir === 1);
M.setSort.call(c, "client", "dPos");
ok("默认升序键: 非默认列三击=复位默认(addr/1)", c.dtSortState.dPos.key === "addr" && c.dtSortState.dPos.dir === 1);
// 空默认键 + 默认升序(dEmpty): 首击任意列=降序, 三击复位空键 —— 与修复前逐位一致(零误伤)
c = mkCtx();
M.setSort.call(c, "sev", "dEmpty");
ok("空默认键: 首击=降序(零误伤)", c.dtSortState.dEmpty.key === "sev" && c.dtSortState.dEmpty.dir === -1);
M.setSort.call(c, "sev", "dEmpty");
ok("空默认键: 二击=升序", c.dtSortState.dEmpty.dir === 1);
M.setSort.call(c, "sev", "dEmpty");
ok("空默认键: 三击=复位空键", c.dtSortState.dEmpty.key === "" && c.dtSortState.dEmpty.dir === 1);
// 3. _dtStrCompare: IPv4(+可选端口)逐段数值序; 端口数值; 等值 0; 非 IP localeCompare 回落
const cmp = (a, b) => M._dtStrCompare(a, b);
ok("IPv4 段内数值序: 10.10.2.3 < 10.10.10.1(字典序会排反)", cmp("10.10.2.3:51413", "10.10.10.1:80") < 0);
ok("端口按数值比较: 8080 > 443", cmp("1.2.3.4:8080", "1.2.3.4:443") > 0);
ok("等值 -> 0", cmp("1.2.3.4", "1.2.3.4") === 0);
ok("非 IP 回落 localeCompare", cmp("b", "a") > 0 && cmp("a", "b") < 0);

// 4. sortedDrawer: 空值两方向恒末位(不反转) + IPv4 数值序 + 数值走 _raw 侧
const rows = [
  { id: 1, _raw: { addr: "1.2.3.10" } },
  { id: 2, _raw: { addr: "1.2.3.9" } },
  { id: 3, _raw: { addr: "" } },
];
const draw = (dir) => M.sortedDrawer.call(mkCtx({ dtSortState: { d0: { key: "addr", dir } } }), "d0", rows).map((r) => r.id);
ok("升序: 1.2.3.9 在 1.2.3.10 前(段内数值序), 空值恒末位", JSON.stringify(draw(1)) === JSON.stringify([2, 1, 3]));
ok("降序: 空值仍恒末位(两方向不反转)", JSON.stringify(draw(-1)) === JSON.stringify([1, 2, 3]));
const nums = [{ id: 1, _raw: { size: 300 } }, { id: 2, _raw: { size: 20 } }];
const drawNum = (dir) => M.sortedDrawer.call(mkCtx({ dtSortState: { d0: { key: "size", dir } } }), "d0", nums).map((r) => r.id);
ok("数值键按 _raw 侧数值比较(显示值字符串比较会错序)", JSON.stringify(drawNum(1)) === JSON.stringify([2, 1]));
ok("空键 = 后端原序(排序永远可逆)", JSON.stringify(M.sortedDrawer.call(mkCtx({ dtSortState: {} }), "d0", rows.map((r) => r.id && { id: r.id })) ) === JSON.stringify([{ id: 1 }, { id: 2 }, { id: 3 }]));
console.log(JSON.stringify({
  ok: checks.filter((c) => c[1]).length, total: checks.length,
  failed: checks.filter((c) => !c[1]).map((c) => c[0]),
}));
"""

# R5#55: format 函数族档位边界 ------------------------------------------------------
_NODE_FORMAT_PROBE = r"""
const fs = require("fs");
global.window = {};
const src = fs.readFileSync(process.argv[1], "utf8");
eval(src + "\n;globalThis.__W2__ = window.AQB_FORMAT;");
const M = globalThis.__W2__.methods;
const checks = [];
const ok = (name, cond) => checks.push([name, !!cond]);

// _fmtLadder: 命中档位 / 梯下回落(roundFallback 取整) / 梯顶截断 / 档名写错回落整梯
ok("字节梯命中 GiB", M._fmtLadder(2 ** 31, "bytes", 2, false) === "2.00 GiB");
ok("字节梯命中 KiB 下界(1024 = 恰一档)", M._fmtLadder(2 ** 10, "bytes", 2, false) === "1.00 KiB");
ok("梯下原值不取整", M._fmtLadder(500.6, "bytes", 1, false) === "500.6 B");
ok("roundFallback 取整兜底", M._fmtLadder(500.6, "bytes", 1, true) === "501 B");
ok("梯顶截断: PiB 体量按 TiB 档显示(曲线图轴标口径)", M._fmtLadder(2 ** 50, "bytes", 2, false, "TiB") === "1024.00 TiB");
ok("top 档名写错回落整张梯(不静默错值)", M._fmtLadder(2 ** 50, "bytes", 2, false, "ZiB") === "1.00 PiB");
ok("速度梯: KiB/s 下界", M.fmtSpeed(2 ** 10) === "1.00 KiB/s");
ok("速度梯楼层 B/s", M._fmtLadder(512, "speed", 2, false) === "512 B/s");
ok("fmtSpeed 0 值口径", M.fmtSpeed(0) === "0 B/s");
ok("fmtSize 缺失/0 值口径", M.fmtSize(null) === "-" && M.fmtSize(0) === "0 B");

// fmtEta: qB 哨兵 8640000 = 无 ETA; 非正数 = 未知/缺失 —— 均空白
ok("ETA 哨兵 8640000 空白", M.fmtEta(8640000) === "");
ok("ETA 非正数空白", M.fmtEta(0) === "" && M.fmtEta(-5) === "");
ok("ETA 哨兵-1s 空白(最大合法值 8639999 正常显示)", M.fmtEta(8639999) === "99天23时");
ok("ETA 普通值走 fmtDuration", M.fmtEta(3600) === "1时00分");

// fmtDuration 三段进位边界
ok("0 -> 0分钟", M.fmtDuration(0) === "0分钟");
ok("<1h 不带秒位", M.fmtDuration(59) === "0分钟" && M.fmtDuration(60) === "1分钟" && M.fmtDuration(3599) === "59分钟");
ok("时段进位(分补零)", M.fmtDuration(3600) === "1时00分" && M.fmtDuration(3660) === "1时01分");
ok("天界(23时59分 -> 1天00时)", M.fmtDuration(86399) === "23时59分" && M.fmtDuration(86400) === "1天00时");
ok("天 + 时进位", M.fmtDuration(90000) === "1天01时");
ok("小数秒向下取整", M.fmtDuration(90.7) === "1分钟");
ok("undefined 兜 0", M.fmtDuration(undefined) === "0分钟");

// fmtPeersQb: qB 口径 "已连接 (总数)"; 总数缺失(-1/null)只显已连接; 已连接缺失全空白
ok("双值 -> c (t)", M.fmtPeersQb(5, 10) === "5 (10)");
ok("总数缺失/负哨兵 -> 只显已连接", M.fmtPeersQb(5, null) === "5" && M.fmtPeersQb(5, -1) === "5");
ok("已连接缺失(null/undefined/负)全空白", M.fmtPeersQb(null, 10) === "" && M.fmtPeersQb(undefined, 10) === "" && M.fmtPeersQb(-1, 10) === "");
ok("已连接 0 是有效值(确实零连接)", M.fmtPeersQb(0, 10) === "0 (10)");
console.log(JSON.stringify({
  ok: checks.filter((c) => c[1]).length, total: checks.length,
  failed: checks.filter((c) => !c[1]).map((c) => c[0]),
}));
"""

# R5#193: fx 挂载层(fx-mount.js) -------------------------------------------------
# fx-mount.js 是 IIFE, 顶层就要 window.AQB_FX 与 document —— 桩最小 DOM/BOM 后 eval 真跑;
# TOAST_SPLIT/rows 是模块私有, 经导出面 toastSync/rows 驱动(与浏览器消费点同一入口)。
_NODE_FX_MOUNT_PROBE = r"""
const fs = require("fs");
const rafQ = [];
let scans = 0;
function mkEl(tag) {
  const el = {
    tagName: String(tag).toUpperCase(),
    children: [], className: "", textContent: "",
    _classes: [], attrs: {},
    parentElement: null, isConnected: true,
    scrollTop: 0, scrollLeft: 0,  // 真实 DOM 默认 0(幽灵定格几何要用)
    _rect: { top: 0, left: 0, width: 800, height: 40 },
    style: {
      _props: {},
      setProperty(k, v) { el.style._props[k] = v; },
      removeProperty(k) { delete el.style._props[k]; },
    },
    _listeners: {},
    addEventListener(t, fn) { (el._listeners[t] = el._listeners[t] || []).push(fn); },
    removeEventListener(t, fn) {
      const q = el._listeners[t] || [];
      const i = q.indexOf(fn);
      if (i >= 0) q.splice(i, 1);
    },
    classList: {
      add: (c) => el._classes.push(c),
      remove: () => {}, toggle: () => {},
    },
    appendChild(c) { el.children.push(c); return c; },
    querySelector: () => null,
    setAttribute(k, v) { el.attrs[k] = v; },
    getAttribute(k) { return k in el.attrs ? el.attrs[k] : null; },
    hasAttribute(k) { return k in el.attrs; },
    removeAttribute(k) { delete el.attrs[k]; },
    cloneNode() { const c = mkEl("div"); c.attrs = Object.assign({}, el.attrs); c._rect = el._rect; return c; },
    getBoundingClientRect() { return el._rect; },
  };
  return el;
}
const bySel = {};
const wrap = mkEl("div");
wrap.querySelectorAll = () => wrap.children;
global.window = { CSS: null };
global.window.AQB_FX = { reduced: () => false, ripple() {}, dir() {}, scan() { scans++; }, viewTransition(fn) { fn(); } };
global.document = {
  addEventListener: () => {}, removeEventListener: () => {},
  documentElement: { classList: { add() {}, remove() {} } },
  querySelector: (sel) => (sel === ".toast-wrap" ? wrap : bySel[sel] || null),
  querySelectorAll: () => [],
  createElement: (tag) => mkEl(tag),
};
global.requestAnimationFrame = (cb) => { rafQ.push(cb); return rafQ.length; };
const src = fs.readFileSync(process.argv[1], "utf8");
eval(src);
const checks = [];
const ok = (n, c) => checks.push([n, !!c]);
const MNT = window.AQB_FX_MOUNT;

// ---------- TOAST_SPLIT 拆段正则(经 toastSync 消费面驱动) ----------
function mkToast(text, cls, id) {
  const span = mkEl("span");
  span.textContent = text;
  const n = mkEl("div");
  n.children.push(span);
  n.attrs["class"] = cls || "toast";
  if (id != null) n.attrs["data-id"] = id;
  return { n, span };
}
const t1 = mkToast("已执行: 重命名", "toast", "id1");
const t2 = mkToast("无分隔符的一句话", "toast", "id2");
const t3 = mkToast("一二三四五六七八九十甲乙丙丁戊: 说明超限", "toast", "id3");  // 头 15 字 > 14 上限
const t4 = mkToast("一二三四五六七八九十甲乙丙丁: 边界十四字", "toast", "id4");  // 头恰 14 字
const t5 = mkToast("复制(3): 文件", "toast", "id5");                            // 括号不是分隔符
const t6 = mkToast("已执行:x", "toast", "id6");                                 // 说明不足 2 字(无空格)
const t7 = mkToast("已执行: 重命名", "toast", "id7");                           // 全角冒号
const t8 = mkToast("已复制, 名称已写入剪贴板", "toast", "id8");                  // 逗号分隔
const t9 = mkToast("保存失败: 磁盘已满", "toast error", "id9");                  // danger 原位升级
const t10 = mkToast("已执行: x", "toast", "id10");  // 说明侧 trim 后 1 字: 连接空格不算门槛 -> 单行(issue 26-11-08-0229 #12)
const t11 = mkToast("已复制: 名称 ", "toast", "id11");  // 尾随空格容忍: 说明 trim 后恰 2 字 -> 照拆
const toasts = [t1, t2, t3, t4, t5, t6, t7, t8, t9, t10, t11];
wrap.children.push(...toasts.map((t) => t.n));
MNT.toastSync(4000, "id1");
ok("拆段: 半角冒号两段落地(标题+说明)", t1.span.children.length === 2
  && t1.span.children[0].className === "toast-t" && t1.span.children[0].textContent === "已执行"
  && t1.span.children[1].className === "toast-s" && t1.span.children[1].textContent === "重命名");
ok("拆段: 全角冒号同族", t7.span.children.length === 2
  && t7.span.children[0].textContent === "已执行" && t7.span.children[1].textContent === "重命名");
ok("拆段: 逗号分隔(说明为名字/计数)", t8.span.children.length === 2
  && t8.span.children[0].textContent === "已复制" && t8.span.children[1].textContent === "名称已写入剪贴板");
ok("拆段: 头恰 14 字上界命中", t4.span.children.length === 2
  && t4.span.children[0].textContent === "一二三四五六七八九十甲乙丙丁");
ok("残留单行: 无分隔符", t2.span.children.length === 0 && t2.span._classes.includes("toast-txt"));
ok("残留单行: 头 15 字超上限(拆段退回单行)", t3.span.children.length === 0);
ok("残留单行: 括号不是分隔符", t5.span.children.length === 0);
ok("残留单行: 说明不足 2 字(无空格)", t6.span.children.length === 0);
ok("残留单行: 说明侧 trim 后 1 字(分隔符后连接空格不计入门槛, issue 26-11-08-0229 #12)", t10.span.children.length === 0);
ok("拆段: 说明 trim 后恰 2 字且带尾随空格照拆", t11.span.children.length === 2
  && t11.span.children[0].textContent === "已复制" && t11.span.children[1].textContent === "名称");
ok("单行也挂 toast-txt(flex:1/min-width:0 生效)", t2.span._classes.includes("toast-txt"));
ok("stamp: 新条 rise + 队列牌(栈内已有多条)", t1.n.attrs["data-fx"] === "rise" && t1.n.attrs["data-fx-queue"] === "");
ok("stamp: 倒计时只归 own 条(ttl 精确命中 data-id)", t1.n.attrs["data-fx-cd"] === "" && t2.n.attrs["data-fx-cd"] === undefined);
ok("stamp: danger 条原位升级 rise danger", t9.n.attrs["data-fx"] === "rise danger");
ok("文本安全: 标题/说明经 textContent 落地(非 innerHTML)", t1.span.children[0].textContent === "已执行");
ok("扫描: FX.scan 被触发", scans > 0);

// ---------- rows 行差分与幽灵退场 ----------
const cont = mkEl("div");
const rowN = { a: mkEl("div"), b: mkEl("div"), c: mkEl("div") };
rowN.a.parentElement = cont; rowN.a._rect = { top: 10, left: 0, width: 800, height: 44 };
rowN.b.parentElement = cont; rowN.b._rect = { top: 54, left: 0, width: 800, height: 44 };
rowN.c.parentElement = cont; rowN.c._rect = { top: 98, left: 0, width: 800, height: 44 };
bySel['[data-hash="a"]'] = rowN.a;
bySel['[data-hash="b"]'] = rowN.b;
bySel['[data-hash="c"]'] = rowN.c;
const row = (h) => ({ hash: h });
const scansBefore = scans;
MNT.rows([row("a"), row("b")], "hash");
ok("rows 首轮只建缓存(零 rAF 零扫描)", rafQ.length === 0 && scans === scansBefore);
MNT.rows([row("a"), row("c")], "hash");
ok("rows 差分: 检出增删后排一帧", rafQ.length === 1);
rafQ.shift()();
ok("幽灵退场: b 行克隆以 row-out 附回原容器", cont.children.length === 1
  && cont.children[0].getAttribute("data-fx") === "row-out");
ok("幽灵定格: top/宽写进内联样式", cont.children[0].style.top === "54px"
  && cont.children[0].style.width === "800px");
ok("幽灵定格: --fx-row-h 覆写实际行高(44px)", cont.children[0].style._props["--fx-row-h"] === "44px");
ok("入场行: c 行 stamp row-in", rowN.c.getAttribute("data-fx") === "row-in");
ok("入场行: --fx-row-h 按实测行高覆写(摘除不跳变)", rowN.c.style._props["--fx-row-h"] === "44px");
ok("差分扫描: FX.scan 被触发", scans > scansBefore);
// 入场毕摘 stamp(D4-7 生命周期, 2026-11-14 顺手修): animationend 名/目标双守卫,
// 守卫不匹配不摘; 匹配则摘属性+行内 --fx-row-h 并自摘监听(主路; 280 与 spawnGhost
// 兜底同值 —— spawnGhost 本身是纯超时单路, 本处为 animationend 主路+超时兜底双路;
// 电池同步口径只驱动主路, 兜底在位由 fx_wiring 静态钉)。
(rowN.c._listeners["animationend"] || [])[0]({ animationName: "fx-sheen", target: rowN.c });
ok("摘除守卫: 异名动画不误摘", rowN.c.getAttribute("data-fx") === "row-in");
(rowN.c._listeners["animationend"] || [])[0]({ animationName: "fx-row-in", target: rowN.b });
ok("摘除守卫: 对名错目标(后代冒泡形态)不误摘", rowN.c.getAttribute("data-fx") === "row-in");
(rowN.c._listeners["animationend"] || [])[0]({ animationName: "fx-row-in", target: rowN.c });
ok("摘除主路: animationend 命中即摘属性", rowN.c.getAttribute("data-fx") === null);
ok("摘除主路: 行内 --fx-row-h 一并清掉", rowN.c.style._props["--fx-row-h"] === undefined);
ok("摘除主路: 监听自摘(无残留)", (rowN.c._listeners["animationend"] || []).length === 0);
MNT.rows([row("a"), row("c")], "hash");
ok("rows 无增删: 不排帧(幂等重扫不空转)", rafQ.length === 0);

console.log(JSON.stringify({
  ok: checks.filter((c) => c[1]).length, total: checks.length,
  failed: checks.filter((c) => !c[1]).map((c) => c[0]),
}));
"""


def test_r4_winmembers_sorted_window_same_source():
    """R5#35(major) 修复回归: winMembers 三入口先排序再开窗, 切片/前缀和/占位/键盘行序同源"""
    report = _run_probe(
        _NODE_WINMEMBER_PROBE,
        bundle_file("columns.js"),
        os.path.join(STATIC_ROOT, "shared", "sort.js"),
    )
    _assert_battery(report, "winMembers 同源电池")


def test_r4_groupwin_expand_backoff():
    """R5#57: groupWin 退避判据 = 当前真的有面板; 不在场/未展开保持窗口"""
    report = _run_probe(_NODE_GROUPWIN_BACKOFF_PROBE, bundle_file("columns.js"))
    _assert_battery(report, "groupWin 退避电池")


def test_r4_apply_col_order_boundaries():
    """R5#53: applyColOrder 落点折算四类边界 + 隐藏列相对次序不动 + 尊重既有 colOrder"""
    report = _run_probe(_NODE_APPLY_COL_ORDER_PROBE, bundle_file("columns.js"))
    _assert_battery(report, "applyColOrder 边界电池")


def test_r4_col_persist_intent_merge_and_gates():
    """R5#52(major) + R5#37/R5#38: 意图升格三层 merge + 纯点击门槛 + 拦截自清"""
    report = _run_probe(_NODE_COLPERSIST_MERGE_PROBE, bundle_file("columns.js"))
    _assert_battery(report, "列持久化意图升格电池")


def test_r4_selection_state_machine():
    """R5#51(major): _selSyncGroups 四态 / _selAnchor 兜底链 / selSizeSummaryOf 去重"""
    report = _run_probe(_NODE_SELECTION_PROBE, os.path.join(STATIC_ROOT, "shared", "selection.js"))
    _assert_battery(report, "选择联动状态机电池")


# 定义形态锚(判定/聚合双单点对称, 接缝终审修法): mixin 方法定义位是「裸名 + (参数) + {」,
# 调用恒带接收者前缀(this. / .)不计; 注释散文里的 name(... 形态因要求收尾 `) {` 不计 ——
# 后续消费方接线写 this._partialGroupsOf(...) / this._partialGroupsSummary(...) 时守阵不误红。
# 聚合单点 _partialGroupsSummary 与判定单点 _partialGroupsOf 同族设锚: 消费方将来内联一份聚合时守阵同红。
_PARTIAL_GROUP_ANCHORS = {
    "_partialGroupsOf": "判定",
    "_partialGroupsSummary": "聚合",
}


def _partial_group_def_re(symbol):
    return re.compile(r"(?<![.\w$])" + symbol + r"\s*\([^)]*\)\s*\{")


def test_r4_partial_groups_predicate_five_forms():
    """部分组判定单点守阵(计划 26-11-11-0820 S1, 拍板 D2): 五形态 + 解析面 + 不误拦 ---

    _partialGroupsOf(keys, hashes) -> [{key, name, sel, total}] 是删除确认框行(S2)/设定位置
    迁移关确认框(S3)/迁移开披露条(S4) 三落点共用的「部分组」唯一判定面。判定(D2 拍板口径):
    真实组(!virtual 且 total>1)有成员命中 hashes 且组键不在 keys 且 sel<total。

    静态锚(解析面单点; 锚「定义形态」= 裸名 + (参数) + `{`, 调用恒带接收者前缀 this./. 不计,
    注释散文里的 name(... 形态因要求收尾 `) {` 不计, 后续消费方接线写 this._partialGroupsOf(...) /
    this._partialGroupsSummary(...) 不误红):
      1. 判定单点 _partialGroupsOf 与聚合单点 _partialGroupsSummary 对称设锚: 各自在 selection.js
         定义形态恰一次(其它 shared 文件零平行定义 —— 三落点不得各写判定, 也不得各写聚合);
      2. hash->组反向查走 this.decoratedGroups(与 _findGroup 同源解析面), 方法体内零
         filteredGroups —— 筛选面独走会漏被筛掉的组且混入虚拟行;
      3. 判据含 g.virtual 豁免(虚拟行不是真实组)。

    node 电池五形态真跑(接线在不等于判得对):
      形态1 组键整组入选 -> 不触发(含双向联动袋里组键与成员 hash 同存的形态);
      形态2 成员全选 -> 不触发(组键已晋升 + 种子页降级未晋升 sel===total 两个面);
      形态3 部分选中 -> 触发且 sel/total/name 逐字段正确;
      形态4 跨组混合(整组 A + 部分组 C 并存) -> 只列部分组;
      形态5 单成员组 + 虚拟行 -> 均不触发(专设双成员虚拟行钉住 virtual 判据独立于 total<=1)。
    边界面: 空入参不抛 / hash 不属任何组不触发 / name 缺失兜组 key / decoratedGroups 缺失
    (R6 极端竞态)空返回不抛 —— 判定降级为无提示, 绝不阻断正常操作。
    """
    sel_path = os.path.join(STATIC_ROOT, "shared", "selection.js")
    sel_src = open(sel_path, encoding="utf-8").read()
    # 1. 判定/聚合双单点: 各自定义形态(裸名+(参数)+{, 接收者调用与注释散文不计)恰一次,
    #    且不在任何其它 shared 文件里重复实现
    other_srcs = {
        name: open(os.path.join(STATIC_ROOT, "shared", name), encoding="utf-8").read()
        for name in os.listdir(os.path.join(STATIC_ROOT, "shared"))
        if name != "selection.js" and name.endswith(".js") and not name.startswith("vendor")
    }
    for symbol, role in _PARTIAL_GROUP_ANCHORS.items():
        def_re = _partial_group_def_re(symbol)
        assert len(def_re.findall(sel_src)) == 1, \
            f"selection.js 里 {symbol} 定义形态不恰一次(单点被复制或改名)"
        for name, other in other_srcs.items():
            assert not def_re.search(other), \
                f"{name} 出现 {symbol} 定义形态(平行{role}) —— 消费方只许带接收者调用, {role}不许另写"
    # 2. 解析面: 方法体走 decoratedGroups, 零 filteredGroups(与 _findGroup 同源, 不得筛选面独走)
    body = sel_src[sel_src.index("_partialGroupsOf(keys, hashes)"):sel_src.index("computed:")]
    assert "this.decoratedGroups" in body, \
        "_partialGroupsOf 未走 decoratedGroups(与 _findGroup 同源解析面被拆散)"
    assert "this.filteredGroups" not in body, \
        "_partialGroupsOf 引入 filteredGroups 独走(筛选面漏被筛掉的组且混入虚拟行)"
    assert "g.virtual" in body, "判定缺 g.virtual 豁免(虚拟行/未归组命中不是真实组)"
    # 3. 五形态语义真跑(node 电池, 无 node 静默跳过 —— 与 _NODE_SELECTION_PROBE 同口径)
    report = _run_probe(_NODE_PARTIAL_GROUPS_PROBE, sel_path)
    _assert_battery(report, "部分组判定五形态电池")


def test_r4_delete_details_partial_group_row():
    """删除链部分组行落点级真跑(计划 26-11-11-0820 S2, 拍板 D5) ---

    _deleteDetails(delete_flow.js)在删除目标含部分组时于既有行流末尾追加一行(tone error/
    wide/#i-warn, HR 风险行同款), 判定单点消费 selection.js::_partialGroupsOf(带接收者
    调用, 电池经合并 mixin 的 this 真跑该接线, 不经字符串锚)。

    正例: 部分组目标 -> 恰一行且单组文案逐字段(组名/已选 M/N/钉住词「将缺文件」);
          多组聚合一行(已选/总数与缺口用合计); 四组触发 -> 组名列前 3 +「等 K 个」
          (照 _hrRiskOf 模式); 跨组混合(整组 A 组键入选 + 部分组 C 散员, D2 触发面) ->
          行照出且只列 C(整组不进文案; 落点「keys 非空即短路」类回归 S1 谓词电池不红, 本断言兜住)。
    负例(D2 不触发面): 整组删除(组键入选)/成员全选未晋升(种子页降级)/单成员组/虚拟行/
          hash 不属任何组 -> 均无该行。
    恒显面(D5): _deleteDetails 形参只有 keys/hashes(无 delete_files 勾选入参 —— 行与
          勾选状态无关恒显由结构保证), 且部分组行是行流末行(既有五行/六行结构零改动,
          只追加一行)。

    无 node 静默跳过(与既有电池同口径)。
    """
    report = _run_probe(
        _NODE_DELETE_PARTIAL_ROW_PROBE,
        os.path.join(STATIC_ROOT, "shared", "selection.js"),
        os.path.join(STATIC_ROOT, "shared", "delete_flow.js"),
    )
    _assert_battery(report, "删除链部分组行电池")


def test_r4_move_dialog_partial_group_gate():
    """迁移关部分组确认框落点级真跑(计划 26-11-11-0820 S3, 拍板 D3) ---

    submitMoveDialog(drawer.js)在目标含部分组且明确知道整组迁移关
    (flags.relocate_enabled === false)时, 首次投递前弹确认框(tone error/danger/wide),
    确认才发, 取消留在设定位置框; 判定单点消费 selection.js::_partialGroupsOf、聚合单点消费
    _partialGroupsSummary(与删除链 S2 行共用同一份实现, 电池经合并 mixin 的 this 真跑接线)。

    正例: 部分组+迁移关 -> 恰弹一次确认框且弹层顺序为先收 moveOpen 再开确认框(R3 防双遮罩
          互盖, 照 confirm 回路先例), 行文案钉住词「将缺文件」+「整组迁移」逐字段, 确认后
          首发 body 带 confirm=true(后端部分组闸放行位, issue 26-11-11-0823 —— S3 确认框
          就是后端 confirm 闸的那道确认), 成功后设定位置框保持收起;
          取消 -> 零投递, 带原路径重开设定位置框; 四组聚合 -> 组名前 3 +「等 4 个」合计口径; 跨组混合(整组 A 组键入选 + 部分组 C 散员, D2 触发面)闸照触发且文案只列 C。
    负例(D3): 整组入选(组键级联)/成员全选未晋升/单成员组/虚拟行/hash 不属任何组 -> 直发
          零新增弹层。
    旗标两态: 迁移开(relocate_enabled=true)直发零弹层(S4 披露条的面); flags 与
          relocate_enabled 解析不出(R6)静默直发不误拦; decoratedGroups 缺失(快照竞态)
          不抛不误拦。
    失败收口: 闸内确认后投递失败 -> 框已被闸先收, 照 confirm 回路失败分支带原路径重开
          设定位置框(手输路径不丢); 非闸直发失败维持现状(框从未收, 无重开)。

    无 node 静默跳过(与既有电池同口径)。
    """
    report = _run_probe(
        _NODE_MOVE_PARTIAL_GATE_PROBE,
        os.path.join(STATIC_ROOT, "shared", "selection.js"),
        os.path.join(STATIC_ROOT, "shared", "drawer.js"),
    )
    _assert_battery(report, "迁移关部分组确认框电池")


# R2 模板形态面: _ 前缀标识符(Vue 模板编译器不解析, delete_flow.js WARN 原注 2026-09-17 实测)
_TEMPLATE_UNDERSCORE_RE = re.compile(r"(?<![\w$.])_[A-Za-z_]\w*")


def test_r4_move_dialog_partial_disclosure_bar():
    """迁移开部分组披露条落点级真跑(计划 26-11-11-0820 S4, 拍板 D4) ---

    openMoveDialog(drawer.js)在 flags.relocate_enabled === true 时开框瞬间算一次部分组聚合
    (判定单点 _partialGroupsOf + 聚合单点 _partialGroupsSummary 均带接收者, 只在 JS 侧)存入
    非下划线状态 movePartialDisclosure, move-dialog.html 披露条(warn 档, 开框即见)消费该字段
    —— R2 硬约束: Vue 模板编译器不解析 _ 前缀标识符(delete_flow.js WARN 原注), 模板只读本字段。

    node 电池(接线真跑, 合并 selection.js + drawer.js 两 mixin 方法):
      正例: 部分组+迁移开 -> 披露非 null 且单组 names/sel/total/gap 逐字段; 四组聚合 ->
            组名前 3 +「等 4 个」合计口径(与 S2/S3 共用 _partialGroupsSummary); 跨组混合
            (整组 A 组键入选 + 部分组 C 散员, D2 触发面)披露只列 C; 开框既有
            状态机零破坏(moveOpen/moveCount/movePathInput/候选拉取照常)。
      负例(D2 不触发面): 整组入选/成员全选未晋升/单成员组/虚拟行/hash 不属任何组 -> 无条。
      降级面(R6/D4): 迁移关(relocate_enabled===false, S3 确认框的面, 含取消重开路径)无条;
            flags/relocate_enabled 解析不出无条不抛; decoratedGroups 缺失无条不抛且开框不阻断。
      重开复位: 残留值必被清, 重开现算(上一框的披露被新目标覆盖)。

    静态守阵(照 delete_flow.js:36 WARN 原注 / _scan_mixin_wiring 形态面范式):
      1. move-dialog.html 剥 HTML 注释后零 _ 前缀标识符(模板消费面 R2);
      2. 文案钉住「整组迁移」+「将按整组迁移扩展至全组」+「个成员」(R4 双向钉, 改文案必改守阵);
      3. drawer.js 接线形态: openMoveDialog 内先复位 null + relocate_enabled===true 门 +
         带接收者单点调用(this._partialGroupsOf/_partialGroupsSummary);
      4. state.js 显式建 movePartialDisclosure 字段;
      5. 四皮肤 dialogs.css 各有 .move-note.move-note-warn(warn 档, 色取主题令牌)。

    无 node 静默跳过(与既有电池同口径)。
    """
    # 1. R2 模板形态面: move-dialog.html 剥注释后零 _ 前缀标识符
    tpl_path = os.path.join(STATIC_ROOT, "shared", "tpl", "move-dialog.html")
    tpl_src = open(tpl_path, encoding="utf-8").read()
    stripped = re.sub(r"<!--.*?-->", "", tpl_src, flags=re.S)
    hits = _TEMPLATE_UNDERSCORE_RE.findall(stripped)
    assert not hits, f"move-dialog.html 模板消费面出现 _ 前缀标识符 {hits} —— Vue 模板编译器不解析(R2)"
    # 2. 文案钉住(R4): 披露条文案与形态关键词
    assert "move-note-warn" in stripped, "披露条未挂 warn 档类名 move-note-warn"
    assert 'v-if="movePartialDisclosure"' in stripped, "披露条未走 movePartialDisclosure 门控"
    for kw in ("整组迁移", "将按整组迁移扩展至全组", "个成员", "已选"):
        assert kw in stripped, f"披露条文案缺钉住词「{kw}」(改文案必须同步本守阵, R4)"
    # 3. drawer.js 接线形态: 复位 + 旗标门 + 带接收者单点调用
    drawer_src = open(os.path.join(STATIC_ROOT, "shared", "drawer.js"), encoding="utf-8").read()
    body = drawer_src[drawer_src.index("openMoveDialog(targets"):drawer_src.index("closeMove()")]
    assert "this.movePartialDisclosure = null" in body, "openMoveDialog 未先复位披露状态(残留值漏清)"
    assert "this.flags && this.flags.relocate_enabled === true" in body, \
        "披露条未钉 relocate_enabled===true 门(迁移关是 S3 确认框的面, 旗标解析不出降级无条, R6)"
    assert "this._partialGroupsSummary(this._partialGroupsOf(" in body, \
        "披露条聚合未走判定/聚合单点(带接收者), 判定不许另写"
    # 4. state.js 显式建字段(新状态键漏建 = Vue 响应式失效)
    state_src = open(os.path.join(STATIC_ROOT, "shared", "state.js"), encoding="utf-8").read()
    assert "movePartialDisclosure: null" in state_src, "state.js 未显式建 movePartialDisclosure"
    # 5. 四皮肤 CSS 各有 warn 档规则(色取主题令牌 --warn, 不写死色值)
    for skin in ("prism", "atlas", "console", "flux"):
        css = open(os.path.join(STATIC_ROOT, skin, "css", "dialogs.css"), encoding="utf-8").read()
        assert ".move-note.move-note-warn { color: var(--warn); }" in css, \
            f"{skin} 皮肤 dialogs.css 缺 .move-note.move-note-warn warn 档规则"
    # node 电池真跑
    report = _run_probe(
        _NODE_MOVE_PARTIAL_DISCLOSURE_PROBE,
        os.path.join(STATIC_ROOT, "shared", "selection.js"),
        os.path.join(STATIC_ROOT, "shared", "drawer.js"),
    )
    _assert_battery(report, "迁移开部分组披露条电池")


def test_r4_load_col_state_seeding():
    """R5#18: loadColState 播种三态(空存储/仅空 hidden/任一偏好键) + 坏数据 + 白名单洗净"""
    # 落点带 pid: xdist worker 共用实例根, 固定名会被别的 worker 截断成 0 字节(同 bundle_file 竞态)
    head_path = os.path.join(tempfile.gettempdir(), f"aqb_app_head_for_probe_{os.getpid()}.js")
    assert str(os.getpid()) in os.path.basename(head_path), "head 探针落点缺 pid(同 bundle_file 竞态)"
    with open(head_path, "w", encoding="utf-8", newline="\n") as f:
        f.write(_app_head_source())
    report = _run_probe(_NODE_LOADCOLSTATE_PROBE, head_path)
    _assert_battery(report, "loadColState 播种电池")


def test_r4_sort_domain():
    """R5#54: setSort 三态循环(经典/dyn 两形态) + _dtStrCompare + sortedDrawer 空值恒末位"""
    report = _run_probe(_NODE_SORT_PROBE, os.path.join(STATIC_ROOT, "shared", "sort.js"))
    _assert_battery(report, "排序域电池")


def test_r4_format_ladder_family():
    """R5#55: _fmtLadder 梯顶回落 + fmtEta 哨兵 + fmtDuration 三段进位 + fmtPeersQb 缺省"""
    report = _run_probe(_NODE_FORMAT_PROBE, os.path.join(STATIC_ROOT, "shared", "format.js"))
    _assert_battery(report, "format 函数族电池")


# S3(计划 26-11-20-0009): 进度分档纯函数 progBand/progBandClass 边界电池 ----------------
# 沙箱口径与 format 函数族电池同式(format.js 桩 window 后 eval, 取 window.AQB_FORMAT.methods)。
# 编码(报告口径): 0=空端点档(csb-0) / 1..5=五档(左开右闭) / 6=终点档(csb-t)。
_NODE_PROG_BAND_PROBE = r"""
const fs = require("fs");
global.window = {};
const src = fs.readFileSync(process.argv[1], "utf8");
eval(src + "\n;globalThis.__W2__ = window.AQB_FORMAT;");
const M = globalThis.__W2__.methods;
const checks = [];
const ok = (name, cond) => checks.push([name, !!cond]);
const B = (p) => M.progBand(p);
const C = (p) => M.progBandClass(p);

// 五档左开右闭: (0,20]/(20,40]/(40,60]/(60,80]/(80,100) —— 右闭整点归当档, 0.1/xx.01 归上档
ok("0 = 空端点档 0", B(0) === 0);
ok("0.1 归第 1 档((0,20] 左开端点)", B(0.1) === 1);
ok("20 归第 1 档(右闭整点, 不进位)", B(20) === 1);
ok("20.01 归第 2 档(左开)", B(20.01) === 2);
ok("40 归第 2 档(右闭整点)", B(40) === 2);
ok("40.01 归第 3 档", B(40.01) === 3);
ok("60 归第 3 档(右闭整点)", B(60) === 3);
ok("60.01 归第 4 档", B(60.01) === 4);
ok("80 归第 4 档(右闭整点)", B(80) === 4);
ok("80.01 归第 5 档", B(80.01) === 5);
ok("99.9 仍第 5 档((80,100) 上端不闭)", B(99.9) === 5);
ok("100 = 终点档 6", B(100) === 6);
// 超界: 负值/NaN/undefined 归空端点档, >100 归终点档
ok("负值归空端点档 0", B(-1) === 0 && B(-0.5) === 0);
ok("NaN/undefined 归空端点档 0(不抛错)", B(NaN) === 0 && B(undefined) === 0);
ok(">100 超界归终点档 6", B(100.1) === 6 && B(120) === 6);
// progBandClass 装配: 0->csb-0 / 1..5->csb-1..csb-5 / 6->csb-t(类只表档位, 不产颜色值)
ok("类装配 0/0.1/80.01/100 -> csb-0/csb-1/csb-5/csb-t",
   C(0) === "csb-0" && C(0.1) === "csb-1" && C(80.01) === "csb-5" && C(100) === "csb-t");
ok("类装配右闭整点 20/40/60/80 -> csb-1..csb-4",
   C(20) === "csb-1" && C(40) === "csb-2" && C(60) === "csb-3" && C(80) === "csb-4");
ok("progBand 与 progBandClass 全边界逐档互证", [0, 0.1, 20, 20.01, 40, 40.01, 60, 60.01, 80, 80.01, 99.9, 100, 120].every((p) => {
  const b = B(p);
  return C(p) === (b === 6 ? "csb-t" : "csb-" + b);
}));
// progPct 钳制联动(渲染器真实调用形态, progPct 吃比例): progress>1 的比例经 progPct 钳 100 后落终点档
ok("progPct(1.2) 钳 100 -> 终点档", B(M.progPct(1.2)) === 6 && C(M.progPct(1.2)) === "csb-t");
ok("progPct(0) -> 空端点档 / progPct(0.5)=50% -> 第 3 档", B(M.progPct(0)) === 0 && C(M.progPct(0.5)) === "csb-3");
console.log(JSON.stringify({
  ok: checks.filter((c) => c[1]).length, total: checks.length,
  failed: checks.filter((c) => !c[1]).map((c) => c[0]),
}));
"""


def test_r4_prog_band_boundaries():
    """S3(计划 26-11-20-0009): 进度分档纯函数 progBand/progBandClass(format.js 新增)边界电池
    —— 编码 0=空端点/1..5=五档(左开右闭)/6=终点; 0/0.1/20/20.01/40/40.01/60/60.01/80/80.01/
    99.9/100 逐点 + 负值/NaN/undefined 归空端点 + >100 归终点 + 类装配 csb-0..csb-5/csb-t
    逐档互证 + progPct 钳制联动(>1 比例钳 100 落终点档)"""
    report = _run_probe(_NODE_PROG_BAND_PROBE, os.path.join(STATIC_ROOT, "shared", "format.js"))
    _assert_battery(report, "进度分档电池")


# S4(计划 26-11-20-0009): 速度分档 speedBand/speedBandClass + 数值列色阶判定三件
# (numScaleRatio/numScaleAvail/numScaleEta)与渲染器消费面(cellSpeedTone/cellNumScaleRatio/
# cellNumScaleAvail)电池 ---------------- 沙箱口径与进度分档电池同式(format.js 桩 window 后
# eval, 取 window.AQB_FORMAT.methods); 消费面经 ctx 真跑(方法互调走 this): ctx = methods
# 全集 + colStyle 状态桩 + hrRatioClass 桩(HR mixin 在 hr.js, 不随 format.js 进沙箱, 伴值
# 形态由桩回报, 判定单点"有伴值即让位"照真跑)。编码(报告口径): speedBand 0=无档(不产类)/
# 1..5=五档(左开右闭)/6=over(>100% 严格大于); 数值维翻转端点: ratio=1.0 / availability=1.0
# / eta=60s 与 eta=8640000 哨兵。
_NODE_SPEED_BAND_PROBE = r"""
const fs = require("fs");
global.window = {};
const src = fs.readFileSync(process.argv[1], "utf8");
eval(src + "\n;globalThis.__W2__ = window.AQB_FORMAT;");
const M = globalThis.__W2__.methods;
const checks = [];
const ok = (name, cond) => checks.push([name, !!cond]);
const mkCtx = (colStyle) => Object.assign({ colStyle: colStyle }, M, {
  hrRatioClass: (m) => m.__hrRatio || "",
});
const B = (b, l) => M.speedBand(b, l);
const C = (b, l) => M.speedBandClass(b, l);

// ---- speedBand 全边界: 无效面(速度 0/负/NaN, 分母 0=不限/null=undefined=未知)恒无档 ----
ok("bytes=0 -> 无档 0(本就空白 fmtSpeedOrDash)", B(0, 1000) === 0);
ok("分母 0(不限)-> 无档 0", B(500, 0) === 0 && B(999999, 0) === 0);
ok("分母 null(未知)-> 无档 0", B(500, null) === 0);
ok("分母 undefined -> 无档 0(不抛错)", B(500, undefined) === 0);
ok("bytes 负值/NaN/undefined -> 无档 0(不抛错)", B(-5, 1000) === 0 && B(NaN, 1000) === 0 && B(undefined, 1000) === 0);
// 五档左开右闭: (0,20%]→1 … (80,100%]→5 —— 右闭整点归当档(20%/40%/60%/80%), xx.1% 归上档
ok("20% 恰端点归第 1 档(右闭)", B(200, 1000) === 1 && B(20, 100) === 1);
ok("20.1% 归第 2 档(左开) / 19.9% 仍第 1 档", B(201, 1000) === 2 && B(199, 1000) === 1);
ok("40% 归第 2 档(右闭) / 40.1% 归第 3 档", B(400, 1000) === 2 && B(401, 1000) === 3);
ok("60% 归第 3 档(右闭) / 60.1% 归第 4 档", B(600, 1000) === 3 && B(601, 1000) === 4);
ok("80% 归第 4 档(右闭) / 80.1% 归第 5 档", B(800, 1000) === 4 && B(801, 1000) === 5);
ok("99.9% 仍第 5 档((80,100] 上段)", B(999, 1000) === 5);
// over 面: 严格大于 100% 才 over; 分母=limit 恰 100% 仍第 5 档(不进 over)
ok("恰 100%(bytes==limit)仍第 5 档, 不是 over", B(1000, 1000) === 5 && B(100, 100) === 5 && B(5, 5) === 5);
ok(">100% 归 over 档 6(双侧: 恰超一点/翻倍)", B(1001, 1000) === 6 && B(2000, 1000) === 6);

// ---- speedBandClass 装配: 0->'' / 1..5->csp-N / 6->csp-over(类只表档位, 不产颜色值) ----
ok("类装配 0/1/5 档 -> ''/csp-1/csp-5", C(0, 1000) === "" && C(200, 1000) === "csp-1" && C(999, 1000) === "csp-5");
ok("类装配 over -> csp-over", C(1001, 1000) === "csp-over" && C(2000, 1000) === "csp-over");
ok("类装配与 speedBand 全边界逐档互证", [[0,1000],[1,1000],[199,1000],[200,1000],[201,1000],[400,1000],[401,1000],[600,1000],[601,1000],[800,1000],[801,1000],[999,1000],[1000,1000],[1001,1000],[2000,1000]].every(([b, l]) => {
  const band = B(b, l);
  return C(b, l) === (band === 0 ? "" : band === 6 ? "csp-over" : "csp-" + band);
}));

// ---- 75% 旧档不受扰: numTone 0.75 阈值语义原样, 与新档互不干扰 ----
ok("numTone 0.75 阈值双侧原样(0.749->tone-low / 0.75->tone-high)",
   M.numTone(749, 1000) === "tone-low" && M.numTone(750, 1000) === "tone-high");
ok("numTone 无效面原样(value<=0 或分母缺失 -> '')",
   M.numTone(0, 1000) === "" && M.numTone(500, 0) === "" && M.numTone(500, null) === "");
ok("75% 点两套判定各归各档互不干扰(tone-high 且 speedBand 4 档, 0.75*5=3.75)",
   M.numTone(750, 1000) === "tone-high" && B(750, 1000) === 4 && B(749, 1000) === 4);

// ---- cellSpeedTone 三态互斥派发(current=原链 / off=空串 / 谱=csp-*) ----
const cur = mkCtx({ speedramp: "current" });
const off = mkCtx({ speedramp: "off" });
const cool = mkCtx({ speedramp: "cool" });
ok("current: cellSpeedTone 逐值 == numTone(类链一字不动)", [0, 500, 749, 750, 2000].every((b) => cur.cellSpeedTone(b, 1000) === M.numTone(b, 1000)));
ok("off: cellSpeedTone 恒空串(高低值/无效分母均无类)", off.cellSpeedTone(500, 1000) === "" && off.cellSpeedTone(2000, 1000) === "" && off.cellSpeedTone(500, 0) === "");
ok("选谱: cellSpeedTone == speedBandClass(csp-*)", [199, 200, 201, 999, 1000, 1001].every((b) => cool.cellSpeedTone(b, 1000) === C(b, 1000)) && cool.cellSpeedTone(200, 1000) === "csp-1" && cool.cellSpeedTone(1001, 1000) === "csp-over");

// ---- 数值列三判定翻转端点双侧 ----
ok("numScaleRatio: 0.99->cst-warn / 1.0 翻转点->cst-good / 1.5->cst-good / 0->cst-warn",
   M.numScaleRatio(0.99) === "cst-warn" && M.numScaleRatio(1.0) === "cst-good" && M.numScaleRatio(1.5) === "cst-good" && M.numScaleRatio(0) === "cst-warn");
ok("numScaleAvail: 0.99->cst-warn / 1.0 翻转点->不产类(不着色) / 1.5->不产类",
   M.numScaleAvail(0.99) === "cst-warn" && M.numScaleAvail(1.0) === "" && M.numScaleAvail(1.5) === "");
ok("numScaleAvail: qB 未知哨兵 -1 与缺失 null/undefined -> 不产类(不抛错)",
   M.numScaleAvail(-1) === "" && M.numScaleAvail(null) === "" && M.numScaleAvail(undefined) === "");
ok("numScaleEta: 59->cst-soon / 60 翻转点->不产类 / 8639999->不产类",
   M.numScaleEta(59) === "cst-soon" && M.numScaleEta(60) === "" && M.numScaleEta(8639999) === "");
ok("numScaleEta: 8640000 哨兵与 <=0(未知/缺失)-> 不产类(不抛错)",
   M.numScaleEta(8640000) === "" && M.numScaleEta(0) === "" && M.numScaleEta(-5) === "" && M.numScaleEta(undefined) === "");

// ---- cellNumScaleRatio: 空白格不染 + HR 伴值共存(D10: 伴值行不产 cst-*, 无伴值行正常) ----
const numOnCtx = mkCtx({ numeric: "on" });
ok("无伴值行: ratio<1 -> cst-warn / >=1 -> cst-good", numOnCtx.cellNumScaleRatio({ progress: 1, ratio: 0.5 }) === "cst-warn" && numOnCtx.cellNumScaleRatio({ progress: 1, ratio: 1.2 }) === "cst-good");
ok("空白格不染(progress=0 -> cellRatio '' -> 不产类)", numOnCtx.cellNumScaleRatio({ progress: 0, ratio: 0.5 }) === "");
ok("HR 伴值共存: 伴值行(pending/reached)不产 cst-*(D10 HR 优先)", [{ __hrRatio: "pending" }, { __hrRatio: "reached" }].every((m) => numOnCtx.cellNumScaleRatio(Object.assign({ progress: 1, ratio: 0.5 }, m)) === ""));
ok("组行形态(无 HR 字段)自然落数值判定", numOnCtx.cellNumScaleRatio({ progress: 1, ratio: 2.0 }) === "cst-good");

// ---- cellNumScaleAvail: numeric 开关在类链源头互斥(开=D10 / 关=既有 numTone 原样) ----
const numOffCtx = mkCtx({ numeric: "off" });
ok("numeric=off: cellNumScaleAvail 逐值 == numTone(v,1)(现状链原样)", [0, 0.5, 0.749, 0.75, 1.5].every((v) => numOffCtx.cellNumScaleAvail(v) === M.numTone(v, 1)));
ok("numeric=on: <1 -> cst-warn / >=1 -> 不产类(D10 完整语义, 0.75 档让位)", numOnCtx.cellNumScaleAvail(0.5) === "cst-warn" && numOnCtx.cellNumScaleAvail(0.9) === "cst-warn" && numOnCtx.cellNumScaleAvail(1.0) === "" && numOnCtx.cellNumScaleAvail(1.5) === "");
ok("numeric=on: 未知哨兵 -1 -> 不产类", numOnCtx.cellNumScaleAvail(-1) === "");
console.log(JSON.stringify({
  ok: checks.filter((c) => c[1]).length, total: checks.length,
  failed: checks.filter((c) => !c[1]).map((c) => c[0]),
}));
"""


def test_r4_speed_band_and_num_scale():
    """S4(计划 26-11-20-0009): 速度分档 speedBand/speedBandClass 边界电池 + 数值列色阶判定
    三件(numScale*)翻转端点 + 渲染器消费面(cellSpeedTone/cellNumScaleRatio/cellNumScaleAvail)
    三态互斥与 HR 伴值共存形态 —— speedBand 编码 0=无档(bytes<=0 / 分母 0=不限/null=undefined
    =未知)/1..5=五档(左开右闭)/6=over(严格 >100%, 恰 100% 仍第 5 档); 类装配 ''/csp-1..
    csp-5/csp-over 逐档互证; numTone 0.75 旧档双侧原样且与新档互不干扰; 消费面经 ctx 真跑
    (colStyle 状态桩 + hrRatioClass 伴值桩): current 逐值 == numTone / off 恒空串 / 选谱 ==
    speedBandClass; 数值维 ratio=1.0、availability=1.0、eta=60s 翻转点双侧各一例 + eta=8640000
    哨兵; HR 伴值行不产 cst-*(D10 让位)且空白格(progress=0)不染, 组行形态(无 HR 字段)
    自然落判定"""
    report = _run_probe(_NODE_SPEED_BAND_PROBE, os.path.join(STATIC_ROOT, "shared", "format.js"))
    _assert_battery(report, "速度分档与数值色阶电池")


# S5(计划 26-11-20-0009): 单位拆分 parts 家族(fmtSizeParts/fmtSpeedParts)与拆分单点
# _fmtLadderParts 电池 ---------------- 沙箱口径与进度/速度分档电池同式(format.js 桩 window 后
# eval, 取 window.AQB_FORMAT.methods)。判定口径: 非 null 时 parts.v + parts.u 与
# fmtSize/fmtSpeed 输出**逐字一致**(u 携带前导空格 = 空格归属单位 span, 拼串即串形态);
# null = 零值 dash 形态不拆, 与 fmtSizeOrDash/fmtSpeedOrDash 的空串口径同源(0/null/
# undefined/NaN 全 falsy); 档类 c: 大小族 csu-B/csu-KiB..csu-PiB、速度族 csu-Bs/csu-KiBs..
# csu-GiBs(类名 's' 尾即速度族标记 —— 与单位串含 /s 互证), 颜色一律 CSS 派生, JS 不产色值。
_NODE_UNIT_PARTS_PROBE = r"""
const fs = require("fs");
global.window = {};
const src = fs.readFileSync(process.argv[1], "utf8");
eval(src + "\n;globalThis.__W2__ = window.AQB_FORMAT;");
const M = globalThis.__W2__.methods;
const checks = [];
const ok = (name, cond) => checks.push([name, !!cond]);

// ---- parts ≡ fmt 串逐字一致(全单位梯): 非 null 时 v+u == fmtSize/fmtSpeed 输出 ----
// 大小族 B~PiB: 档下原值(含小数)/1024 进制恰端点命中/档内中值/2^60 超大值封 PiB/负数
const sizeVals = [1, 0.5, 512, 1023, 1024, 1536, 2 ** 20, 1.5 * 2 ** 20, 2 ** 30, 2 ** 40, 2 ** 50, 2 ** 60, -5, -1536];
ok("fmtSizeParts 全梯逐字一致(档下/各档恰端点/中值/超大值/负数)", sizeVals.every((v) => {
  const p = M.fmtSizeParts(v);
  return p !== null && p.v + p.u === M.fmtSize(v);
}));
// 速度族 B/s~GiB/s 同构(速度梯 3 档 + 楼层; 2^34 = 16 GiB/s 超档封顶同形)
const speedVals = [1, 512, 1023, 1024, 1536, 2 ** 20, 2 ** 30, 2 ** 34, -100];
ok("fmtSpeedParts 全梯逐字一致(楼层/各档恰端点/中值/超 GiB 封顶/负数)", speedVals.every((v) => {
  const p = M.fmtSpeedParts(v);
  return p !== null && p.v + p.u === M.fmtSpeed(v);
}));

// ---- 零值 dash null 形态: 与 OrDash 空串口径同源(0/null/undefined/NaN 全 falsy 不拆) ----
ok("零值 dash 形态不拆(0/null/undefined/NaN -> null, 两族同口径)",
   M.fmtSizeParts(0) === null && M.fmtSizeParts(null) === null && M.fmtSizeParts(undefined) === null && M.fmtSizeParts(NaN) === null &&
   M.fmtSpeedParts(0) === null && M.fmtSpeedParts(null) === null && M.fmtSpeedParts(undefined) === null && M.fmtSpeedParts(NaN) === null);
ok("null 门与 OrDash 空串门逐值等价(全梯 + 零值, 两族)", [0, null, undefined, NaN, ...sizeVals, ...speedVals].every((v) =>
  (M.fmtSizeParts(v) === null) === (M.fmtSizeOrDash(v) === "") && (M.fmtSpeedParts(v) === null) === (M.fmtSpeedOrDash(v) === "")));

// ---- u 前导空格归属(拼串含空格, 文本总宽不变)与字段形态恰 {v, u, c} ----
ok("u 恒携带前导空格(空格归属单位 span)", sizeVals.every((v) => M.fmtSizeParts(v).u.charAt(0) === " ") && speedVals.every((v) => M.fmtSpeedParts(v).u.charAt(0) === " "));
ok("字段形态恰 {v, u, c}", [1023, 1024, 1536, 2 ** 50, 512, 2 ** 20].every((v) => {
  const p = M.fmtSizeParts(v), q = M.fmtSpeedParts(v);
  return [p, q].every((r) => Object.keys(r).length === 3 && "v" in r && "u" in r && "c" in r);
}));

// ---- 档类/族标记: 大小族无 's' 尾, 速度族 's' 尾; 与单位串含 /s 互证 ----
ok("大小族档类逐档正确(B/KiB/MiB/GiB/TiB/PiB, 超大值封 PiB)",
   M.fmtSizeParts(500).c === "csu-B" && M.fmtSizeParts(1023).c === "csu-B" && M.fmtSizeParts(2 ** 10).c === "csu-KiB" &&
   M.fmtSizeParts(2 ** 20).c === "csu-MiB" && M.fmtSizeParts(2 ** 30).c === "csu-GiB" && M.fmtSizeParts(2 ** 40).c === "csu-TiB" &&
   M.fmtSizeParts(2 ** 50).c === "csu-PiB" && M.fmtSizeParts(2 ** 60).c === "csu-PiB");
ok("速度族档类逐档正确(Bs/KiBs/MiBs/GiBs, 类名 's' 尾即族标记)",
   M.fmtSpeedParts(500).c === "csu-Bs" && M.fmtSpeedParts(1023).c === "csu-Bs" && M.fmtSpeedParts(2 ** 10).c === "csu-KiBs" &&
   M.fmtSpeedParts(2 ** 20).c === "csu-MiBs" && M.fmtSpeedParts(2 ** 30).c === "csu-GiBs" && M.fmtSpeedParts(2 ** 34).c === "csu-GiBs");
ok("族标记与单位串互证(u 含 /s 当且仅当档类 's' 尾, 全梯)", [...sizeVals, ...speedVals].every((v) => [M.fmtSizeParts(v), M.fmtSpeedParts(v)].every((p) =>
  p === null || (p.u.indexOf("/s") >= 0) === (p.c.charAt(p.c.length - 1) === "s"))));

// ---- 小数位/负数/超大值边界: toFixed(2) 口径与串形态同源 ----
ok("小数位 toFixed(2) 口径(1.50 KiB / 1.50 KiB/s 形态)", M.fmtSizeParts(1536).v === "1.50" && M.fmtSizeParts(1536).u === " KiB" && M.fmtSpeedParts(1536).v === "1.50" && M.fmtSpeedParts(1536).u === " KiB/s");
ok("负数不进档(负值 < 全部档阈值, 楼层原值串)", M.fmtSizeParts(-1536).v === "-1536" && M.fmtSizeParts(-1536).u === " B" && M.fmtSpeedParts(-100).v === "-100" && M.fmtSpeedParts(-100).u === " B/s");
ok("超大值封 PiB 档(2^60 = 1024.00 PiB, 梯顶不截断)", M.fmtSizeParts(2 ** 60).v === "1024.00" && M.fmtSizeParts(2 ** 60).u === " PiB");
ok("速度族楼层 B/s(512 -> 512 B/s)", M.fmtSpeedParts(512).v === "512" && M.fmtSpeedParts(512).u === " B/s");

// ---- 上下限列消费面: fmtLimitBytes 空串门与 parts null 门逐值等价, 非零串形态逐字同 ----
ok("fmtLimitBytes == fmtSpeedParts 投影(缺失/0 = 不限速 -> '', 非零 v+u)", [0, null, undefined, 1024, 1536].every((v) => {
  const p = M.fmtSpeedParts(v);
  return M.fmtLimitBytes(v) === (p === null ? "" : p.v + p.u);
}));

// ---- 拆分单点回归: _fmtLadder 是 _fmtLadderParts 的拼接投影(top 回落/取整兜底语义原样) ----
ok("_fmtLadder == parts 拼接(top 档名回落/梯顶截断/取整兜底语义原样)",
   M._fmtLadder(2 ** 50, "bytes", 2, false, "TiB") === "1024.00 TiB" && M._fmtLadder(2 ** 50, "bytes", 2, false, "ZiB") === "1.00 PiB" &&
   M._fmtLadder(2 ** 50, "bytes", 2, false) === "1.00 PiB" && M._fmtLadder(500.6, "bytes", 1, true) === "501 B" &&
   M._fmtLadder(500.6, "bytes", 1, false) === "500.6 B" && M._fmtLadder(512, "speed", 2, false) === "512 B/s");
console.log(JSON.stringify({
  ok: checks.filter((c) => c[1]).length, total: checks.length,
  failed: checks.filter((c) => !c[1]).map((c) => c[0]),
}));
"""


def test_r4_unit_parts_family():
    """S5(计划 26-11-20-0009): 单位拆分 parts 家族 fmtSizeParts/fmtSpeedParts(format.js 新增)
    与拆分单点 _fmtLadderParts 电池 —— parts ≡ fmt 串逐字一致(大小族全梯 B~PiB + 速度族
    B/s~GiB/s, 非 null 时 v+u == fmtSize/fmtSpeed 输出)/零值 dash null 形态(与 OrDash 空串
    口径逐值互证)/u 前导空格归属与字段形态恰 {v, u, c}/档类与族标记(csu-B..csu-PiB 与
    csu-Bs..csu-GiBs, 's' 尾即速度族, 与单位串含 /s 互证)/小数位 toFixed(2)/负数/超大值
    封 PiB 边界/上下限列消费面(fmtLimitBytes == parts 投影)/拆分单点回归(_fmtLadder ==
    parts 拼接, top 回落/取整兜底语义原样)"""
    report = _run_probe(_NODE_UNIT_PARTS_PROBE, os.path.join(STATIC_ROOT, "shared", "format.js"))
    _assert_battery(report, "单位拆分 parts 家族电池")


def test_r4_fx_mount_toast_split_and_rows_ghost():
    """R5#193: fx 挂载层 node 电池 —— TOAST_SPLIT 拆段正则族 + rows 行差分与幽灵退场 + row-in stamp 生命周期"""
    report = _run_probe(_NODE_FX_MOUNT_PROBE, os.path.join(STATIC_ROOT, "flux", "fx-mount.js"))
    _assert_battery(report, "fx 挂载层电池")


# R5#95/R5#81(P13): 05 变体 rowsFn 真跑(node 电池) ------------------------------------------
# 沙箱口径: drawer_templates.js 在无 DOM 下自发布 window.AQB_DRAWER_TPL_REG(dtInjectCss 等
# 载荷全部自带 typeof document 守卫); 05 IIFE 消费真 reg(dtHtml/helpers/trackers 单源)自注册,
# 电池经 reg.get 取回 rowsFn —— 判据走生产函数, 不经字符串锚。ctx 桩只给 rowsFn 需要的四件
# (drawer.trackers / drawerTrackerVirtual / drawerReannounceGate / fmtPeersQb)。
_NODE_DT05_ROWSFN_PRELUDE = r"""
const fs = require("fs");
const checks = [];
const ok = (name, cond) => checks.push([name, !!cond]);
global.window = {};
let reg = null;
try {
  eval(fs.readFileSync(process.argv[1], "utf8"));  // drawer_templates.js -> window.AQB_DRAWER_TPL_REG
  reg = global.window.AQB_DRAWER_TPL_REG;
} catch (e) { ok("drawer_templates.js 加载失败: " + e.message, false); }
if (!reg || !reg.trackers) ok("reg/trackers 未发布(沙箱口径漂移)", false);
let def = null;
if (reg && reg.trackers) {
  try {
    eval(fs.readFileSync(process.argv[2], "utf8"));  // 05-trackers-health-groups-low.js
    def = reg.get("trackers", "05");
  } catch (e) { ok("05 变体加载失败: " + e.message, false); }
}
if (!def || typeof def.rowsFn !== "function") ok("05 rowsFn 未注册", false);
// rowsFn 需要的 ctx 四件(drawer.trackers / 虚拟判据 / 重报闸门 / peers 计数格式化)
const mkCtx = (trackers) => ({
  drawer: { trackers: trackers },
  drawerTrackerVirtual: () => false,
  drawerReannounceGate: () => ({ ok: true, title: "" }),
  fmtPeersQb: (a) => String(a == null ? 0 : a),
});
const segRow = (trackers, segKey, i) => {
  const segs = def.rowsFn(mkCtx(trackers));
  const seg = segs.find((s) => s.key === segKey);
  return seg && seg.rows[i] ? seg.rows[i] : null;
};
"""

_NODE_DT05_ADVICE_PROBE = _NODE_DT05_ROWSFN_PRELUDE + r"""
// R5#95: adviceFor 五类关键词分派(经 err 桶 failRowOf 装配路径 = 生产行对象 .advice)。
// 样本逐条核对过分派序(unregistered -> passkey -> ban -> timeout -> maintenance -> 兜底),
// 互不越档命中。
const CASES = [
  ["not registered 类", "torrent not registered with this tracker", "站点删除"],
  ["passkey 类", "invalid passkey", "鉴权信息疑似失效"],
  ["ban 类", "you are banned by the tracker", "客户端或行为可能被站点限制"],
  ["timeout 类", "connection timed out", "网络层不可达"],
  ["maintenance 类", "site is under maintenance", "站点侧暂时不可用"],
];
for (const [name, msg, marker] of CASES) {
  const row = segRow([{ url: "https://t.example/announce", status: 4, tier: 0, msg: msg }], "err", 0);
  ok(name + "走失败处置块形态(kind=fail)", !!row && row.kind === "fail");
  ok("adviceFor " + name + " 分派命中各自文案", !!row && String(row.advice).indexOf(marker) >= 0);
}
// 通用兜底分支: 零命中 -> 「先点强制重新汇报」通用话术(此前五类 + 兜底全无覆盖, R5#95)
const fb = segRow([{ url: "https://t.example/announce", status: 4, tier: 0, msg: "weird unknown failure" }], "err", 0);
ok("adviceFor 通用兜底分支", !!fb && String(fb.advice).indexOf("先点「强制重新汇报」") >= 0);
const failed = checks.filter((c) => !c[1]).map((c) => c[0]);
console.log(JSON.stringify({ ok: checks.length - failed.length, total: checks.length, failed: failed }));
"""

_NODE_DT05_TIER_PROBE = _NODE_DT05_ROWSFN_PRELUDE + r"""
// R5#81: ok 组 tier 升序的缺失/非法 tier 兜底。a=T1 / b=缺 tier / c=T0 / d=非法 "x":
// 修后(记 9)序 = c(0), a(1), b(9), d(9)(9 档并列保 qB 原序: b 先于 d);
// 修前(折算 0)序 = b, c, d, a —— tier 缺失的 tracker 插到所有 tier0 之前。
const mk = (url, tier) => {
  const t = { url: url, status: 2, msg: "", num_seeds: 1, num_complete: 1,
    num_leeches: 0, num_incomplete: 0, num_downloaded: 0 };
  if (tier !== undefined) t.tier = tier;
  return t;
};
const trackers = [
  mk("https://a.example/announce", 1),
  mk("https://b.example/announce"),        // tier 缺失
  mk("https://c.example/announce", 0),
  mk("https://d.example/announce", "x"),   // 非法 tier(负值/非数值同档)
];
const segs = def.rowsFn(mkCtx(trackers));
const seg = segs.find((s) => s.key === "ok");
const order = (seg ? seg.rows : []).map((r) => r.host);
ok("ok 组恰 4 行(缺 tier 不得跌出 ok 桶)", order.length === 4);
ok("tier0(c)居首(修复前缺失 tier(b)插队最前)", order[0] === "c.example");
ok("tier 升序次位 = tier1(a)", order[1] === "a.example");
ok("缺失 tier(b)与非法 tier(d)殿后且保 qB 原序(记 9 稳定序)", order[2] === "b.example" && order[3] === "d.example");
const failed = checks.filter((c) => !c[1]).map((c) => c[0]);
console.log(JSON.stringify({ ok: checks.length - failed.length, total: checks.length, failed: failed }));
"""


def test_r4_dt05_advice_dispatch():
    """R5#95(P13): 05 adviceFor 五类关键词分派 + 通用兜底 —— rowsFn 真跑不经字符串锚"""
    report = _run_probe(
        _NODE_DT05_ADVICE_PROBE,
        os.path.join(STATIC_ROOT, "shared", "drawer_templates.js"),
        os.path.join(STATIC_ROOT, "shared", "drawer_tpl", "05-trackers-health-groups-low.js"),
    )
    _assert_battery(report, "05 adviceFor 分派电池")


def test_r4_dt05_tier_sort_missing_last():
    """R5#81(P13) 修复回归: 05 ok 组 tier 排序缺失/非法 tier 记 9 殿后(与 04/06 同口径)"""
    report = _run_probe(
        _NODE_DT05_TIER_PROBE,
        os.path.join(STATIC_ROOT, "shared", "drawer_templates.js"),
        os.path.join(STATIC_ROOT, "shared", "drawer_tpl", "05-trackers-health-groups-low.js"),
    )
    _assert_battery(report, "05 tier 兜底电池")


# issue 26-11-08-0229 #2: drawerGeneralSections 契约层传输行 qB -1/null 哨兵守卫(node 电池) --
# 沙箱口径: drawer_rows.js 是 Object.assign(window.AQB_DRAWER.methods, ...) 片段, 电池自给
# AQB_DRAWER 域后 eval; this 桩只给 drawerGeneralSections 消费的格式化方法族(恒真值, 不参与
# 哨兵判据) —— 判据走契约层生产函数(peerNum/connLimit 本尊), 不经字符串锚。
_NODE_DRAWER_ROWS_SENTINEL_PROBE = r"""
const fs = require("fs");
const checks = [];
const ok = (name, cond) => checks.push([name, !!cond]);
global.window = { AQB_DRAWER: { methods: {} } };
try {
  eval(fs.readFileSync(process.argv[1], "utf8"));  // drawer_rows.js -> AQB_DRAWER.methods
} catch (e) { ok("drawer_rows.js 加载失败: " + e.message, false); }
const M = global.window.AQB_DRAWER.methods;
if (typeof M.drawerGeneralSections !== "function") ok("drawerGeneralSections 未加载", false);
// this 桩: drawerGeneralSections 消费的格式化族(返回恒真值, 保证非哨兵行正常装配)
const mkVm = (detail) => ({
  drawer: { detail },
  fmtDuration: (v) => "d" + v, fmtTs: () => "ts", fmtSize: (v) => "s" + v,
  fmtSizeOrDash: (v) => "s" + v, fmtSpeedOrDash: () => "v", fmtEta: () => "e",
  relocateStateText: (s) => s, relocateOriginText: (s) => s,
});
const trRow = (detail, label) => {
  const secs = M.drawerGeneralSections.call(mkVm(detail));
  const tr = secs.find((s) => s.title === "传输");
  const r = tr && tr.rows.find((x) => x.label === label);
  return r ? r.text : null;
};

// 场景1 私有种子: num_complete/num_incomplete/connections_limit = -1 是「无数据/不限」哨兵
// (修复前裸拼渲染 完整/下载中 -1 / -1、连接 8 / -1)
ok("私有种子: 做种数真值照显", trRow({ num_seeds: 3, num_complete: -1, num_incomplete: -1, connections_count: 8, connections_limit: -1 }, "做种数") === "3");
ok("私有种子: 完整/下载中哨兵降级 — / —", trRow({ num_seeds: 3, num_complete: -1, num_incomplete: -1, connections_count: 8, connections_limit: -1 }, "完整/下载中") === "— / —");
ok("私有种子: 连接上限 -1 译「不限」", trRow({ num_seeds: 3, num_complete: -1, num_incomplete: -1, connections_count: 8, connections_limit: -1 }, "连接") === "8 / 不限");

// 场景2 字段缺失(null/undefined): ?? 0 只兜缺失, 守卫后统一降级 —
ok("缺失字段: 做种数 null 降级 —", trRow({ num_seeds: null, num_complete: null, num_incomplete: null, connections_count: null, connections_limit: null }, "做种数") === "—");
ok("缺失字段: 完整/下载中降级 — / —", trRow({ num_seeds: null, num_complete: null, num_incomplete: null, connections_count: null, connections_limit: null }, "完整/下载中") === "— / —");
ok("缺失字段: 连接降级 — / —", trRow({ num_seeds: null, num_complete: null, num_incomplete: null, connections_count: null, connections_limit: null }, "连接") === "— / —");

// 场景3 真值形态逐字不变(守卫不得改动正常数据的显示)
ok("真值: 做种数照显", trRow({ num_seeds: 3, num_complete: 10, num_incomplete: 5, connections_count: 8, connections_limit: 100 }, "做种数") === "3");
ok("真值: 完整/下载中照显", trRow({ num_seeds: 3, num_complete: 10, num_incomplete: 5, connections_count: 8, connections_limit: 100 }, "完整/下载中") === "10 / 5");
ok("真值: 连接照显", trRow({ num_seeds: 3, num_complete: 10, num_incomplete: 5, connections_count: 8, connections_limit: 100 }, "连接") === "8 / 100");

const failed = checks.filter((c) => !c[1]).map((c) => c[0]);
console.log(JSON.stringify({ ok: checks.length - failed.length, total: checks.length, failed: failed }));
"""


def test_r4_drawer_general_rows_qb_sentinels():
    """issue 26-11-08-0229 #2 修复回归: 传输行 做种数/完整下载中/连接 对 -1/null 哨兵降级, 真值不变"""
    report = _run_probe(_NODE_DRAWER_ROWS_SENTINEL_PROBE, os.path.join(STATIC_ROOT, "shared", "drawer_rows.js"))
    _assert_battery(report, "drawer 传输行哨兵电池")


# issue 26-11-08-1621: 路径段 下载路径/根路径 wide 改条件式(值非空才 wide) ----------------
# 沙箱口径与哨兵电池同式: drawer_rows.js 自给 AQB_DRAWER 域后 eval, 直跑契约层生产函数。
_NODE_DRAWER_ROWS_PATH_WIDE_PROBE = r"""
const fs = require("fs");
const checks = [];
const ok = (name, cond) => checks.push([name, !!cond]);
global.window = { AQB_DRAWER: { methods: {} } };
try {
  eval(fs.readFileSync(process.argv[1], "utf8"));  // drawer_rows.js -> AQB_DRAWER.methods
} catch (e) { ok("drawer_rows.js 加载失败: " + e.message, false); }
const M = global.window.AQB_DRAWER.methods;
if (typeof M.drawerGeneralSections !== "function") ok("drawerGeneralSections 未加载", false);
const mkVm = (detail) => ({
  drawer: { detail },
  fmtDuration: (v) => "d" + v, fmtTs: () => "ts", fmtSize: (v) => "s" + v,
  fmtSizeOrDash: (v) => "s" + v, fmtSpeedOrDash: () => "v", fmtEta: () => "e",
  relocateStateText: (s) => s, relocateOriginText: (s) => s,
});
const pathRow = (detail, label) => {
  const secs = M.drawerGeneralSections.call(mkVm(detail));
  const sec = secs.find((s) => s.title === "路径");
  const r = sec && sec.rows.find((x) => x.label === label);
  return r || null;
};
const DETAIL = { save_path: "S:/save", content_path: "S:/save/c", download_path: "X:/dl", auto_tmm: true };

// 值非空: wide 照常占整行折行位
ok("下载路径 真值: wide:true 且文本透传", (() => { const r = pathRow(DETAIL, "下载路径"); return r && r.wide === true && r.text === "X:/dl"; })());
ok("根路径 真值: wide:true 且文本透传", (() => { const r = pathRow(Object.assign({}, DETAIL, { root_path: "R:/root" }), "根路径"); return r && r.wide === true && r.text === "R:/root"; })());

// 值空(修复点, issue 26-11-08-1621): wide 不置位(空值行按普通行渲染), text 兜底「—」保留
ok("下载路径 空串: wide 不置位且兜底 —", (() => { const r = pathRow(Object.assign({}, DETAIL, { download_path: "" }), "下载路径"); return r && !r.wide && r.text === "—"; })());
ok("根路径 缺失: wide 不置位且兜底 —", (() => { const r = pathRow(DETAIL, "根路径"); return r && !r.wide && r.text === "—"; })());
ok("下载路径 null: wide 不置位且兜底 —", (() => { const r = pathRow(Object.assign({}, DETAIL, { download_path: null }), "下载路径"); return r && !r.wide && r.text === "—"; })());

const failed = checks.filter((c) => !c[1]).map((c) => c[0]);
console.log(JSON.stringify({ ok: checks.length - failed.length, total: checks.length, failed: failed }));
"""


def test_r4_drawer_rows_path_wide_conditional():
    """issue 26-11-08-1621 修复回归: 路径段 下载路径/根路径 wide 改条件式(值非空才 wide:true,
    空值行 wide 不置位按普通行渲染, text 兜底「—」保留)"""
    report = _run_probe(_NODE_DRAWER_ROWS_PATH_WIDE_PROBE, os.path.join(STATIC_ROOT, "shared", "drawer_rows.js"))
    _assert_battery(report, "drawer 路径行条件 wide 电池")


# 计划 26-11-10-0027 W1(1): dt_table 几何等价性探针 -----------------------------------------
# 「先证后改」: 委托改造(W1(2) 动 _gridTemplate/colAlignCss 内部)之前, 先用**真实列定义**证明
# 现役拼轨(columns_grid._gridTemplate)与内核(DT_TABLE.layout)输出逐面相等。探针红 = 轨道
# 语义冲突 = 计划 R1 停手条款(不改生产代码、不改断言凑绿、不自选改道, 冲突明细在 failed 项
# 里带两侧全文输出)。
# 沙箱口径: app.js 以 loadColState 截断切片(与 _app_head_source 同口径, createApp 接线段不进
# 沙箱) + columns 域聚合文本(bundle_file("columns.js"), 与拆分前同一份代码)并入**同一次 eval**
# —— columns 方法体按裸名引用 app.js 列模型常量(TABLE_COLUMNS/ALL_TABLE_DEFS), 生产里两段
# <script> 共享同一全局词法作用域, 合并 eval 与之同构; dt_table.js 单文件 require(只依赖
# global.window)。三份源消费同一份真实列定义与宽度输入。
_NODE_DT_LAYOUT_EQUIV_PROBE = r"""
const fs = require("fs");
global.Vue = { createApp: () => ({}) };   // app.js 头部 `const { createApp } = Vue;`
global.window = {};
let store = {};
global.localStorage = {
  getItem: (k) => (k in store ? store[k] : null),
  setItem: (k, v) => { store[k] = String(v); },
  removeItem: (k) => { delete store[k]; },
};
const checks = [];
// 第三位 = 场景类标签(scene): 供循环后的逐类存在性断言, 条件场景静默消失即红
const ok = (name, cond, scene) => checks.push([name, !!cond, scene || ""]);
// 相等断言: 失败时把两侧输出全文挂进检查名(探针红即停手, 明细要能直接进报告做逐字符 diff)
const okEq = (name, a, b, scene) => checks.push([a === b ? name : name + " | 现役=" + JSON.stringify(a) + " layout=" + JSON.stringify(b), a === b, scene || ""]);

require(process.argv[2]);
const DT = global.window.DT_TABLE;
ok("dt_table.js 加载出 window.DT_TABLE.layout", !!DT && typeof DT.layout === "function");

const appSrc = fs.readFileSync(process.argv[3], "utf8");
const marker = "const initialColState = loadColState();";
const cut = appSrc.indexOf(marker);
ok("app.js 找到截断锚(装载体裁未漂移)", cut > 0);
const headSrc = appSrc.slice(0, cut);
const colsSrc = fs.readFileSync(process.argv[1], "utf8");
eval(headSrc + "\n" + colsSrc + "\n;globalThis.__X__ = { TC: TABLE_COLUMNS, DEFS: ALL_TABLE_DEFS, PAGES: ALL_TABLE_PAGES, W: window.AQB_COLUMNS };");
const TC = globalThis.__X__.TC;
const PAGES = globalThis.__X__.PAGES;
const M = globalThis.__X__.W.methods;
const C = globalThis.__X__.W.computed;
ok("columns 域加载出 _visibleCols/_gridTemplate", typeof M._visibleCols === "function" && typeof M._gridTemplate === "function");
ok("columns 域加载出 colAlignCss", typeof C.colAlignCss === "function");
ok("表注册表非空(ALL_TABLE_PAGES 与 ALL_TABLE_DEFS 同构)", PAGES.length > 0 && PAGES.length === Object.keys(globalThis.__X__.DEFS).length);

// 前提钉: 两侧在「列定义缺 tpl」时回退语义不同(_gridTemplate 落空串, layout 落 DEFAULT_TRACK)
// —— 真实列定义必须全列声明 tpl, 否则等价性不成立, 本条先把这一前提显式化
let noTpl = [];
for (const p of PAGES) for (const c of (TC[p] || [])) if (!c || !c.tpl) noTpl.push(p + "/" + (c ? c.key : "?"));
ok("全部真实列定义都声明 tpl(双链回退语义分叉的前提不存在)", noTpl.length === 0);

const mkCtx = (widths, hidden, order) => Object.assign({}, M, {
  colHidden: hidden || {},
  colOrder: order || {},
  colWidths: widths || {},
});
// colAlignCss 产出的是 CSS 文本, align 藏在 text-align 里 —— 按 [data-table=page] 锚解析出逐列序列
const cssAlignsOf = (css, page) => {
  const re = new RegExp(':where\\(\\[data-table="' + page + '"\\]\\) > :nth-child\\((\\d+)\\) \\{ text-align: (\\w+);', "g");
  const byIdx = [];
  let m;
  while ((m = re.exec(css))) byIdx.push([parseInt(m[1], 10), m[2]]);
  byIdx.sort((a, b) => a[0] - b[0]);
  return byIdx.map((x) => x[1]);
};

let pagesChecked = 0;
let colFaceChecks = 0;
for (const p of PAGES) {
  const defs = TC[p] || [];
  if (!defs.length) { ok("[" + p + "] TABLE_COLUMNS 有列定义", false); continue; }
  // 场景 = colWidths 抽样(无覆盖/单列覆盖/全列覆盖) + 列态抽样(隐藏一列/自定义列序),
  // 每一面两侧消费**同一份**列定义与宽度输入
  const allW = {};
  for (const c of defs) allW[c.key] = "77px";
  const scens = [
    { tag: "无覆盖", scene: "plain", widths: null, hidden: null, order: null },
    { tag: "单列覆盖", scene: "single", widths: { [defs[0].key]: "123px" }, hidden: null, order: null },
    { tag: "全列覆盖", scene: "full", widths: allW, hidden: null, order: null },
  ];
  const unlock = defs.find((c) => !c.locked);
  if (unlock) {
    // 隐藏一列: 该列的固化宽不得漏进轨道串(两侧都只对可见列取宽), 另留一列覆盖验混合态
    scens.push({ tag: "隐藏一列", scene: "hidden", widths: { [unlock.key]: "321px", [defs[0].key]: "123px" }, hidden: [unlock.key], order: null });
  }
  if (defs.length > 1) scens.push({ tag: "自定义列序", scene: "reorder", widths: null, hidden: null, order: defs.map((c) => c.key).slice().reverse() });
  for (const s of scens) {
    const ctx = mkCtx(s.widths ? { [p]: s.widths } : {}, s.hidden ? { [p]: s.hidden } : {}, s.order ? { [p]: s.order } : {});
    const cols = M._visibleCols.call(ctx, p);
    const lay = DT.layout(cols, s.widths || {});
    const gt = M._gridTemplate.call(ctx, p);
    okEq("[" + p + "/" + s.tag + "] 轨道串逐字符相等", gt, lay.gridTemplate, s.scene);
    const cssAligns = cssAlignsOf(C.colAlignCss.call(ctx), p);
    okEq("[" + p + "/" + s.tag + "] aligns 逐列相等", JSON.stringify(cssAligns), JSON.stringify(lay.aligns), s.scene);
    if (cssAligns.length !== cols.length) ok("[" + p + "/" + s.tag + "] colAlignCss 规则数=可见列数(解析完整性)", false, s.scene);
    colFaceChecks += cols.length;
  }
  pagesChecked += 1;
}
ok("覆盖面: 全部表都过场景(实算 13 张, 现跑 " + pagesChecked + ")", pagesChecked === PAGES.length && pagesChecked === 13);
// 场景类逐类存在性(评审 minor 修复): 隐藏一列/自定义列序是条件场景, 触发前提(unlock 查找/多列
// 判定)回归会让该类静默消失而列面总量下限照绿 —— 五类各自断言 checks 里有落袋项, 任一类坍缩即红
for (const sc of ["plain", "single", "full", "hidden", "reorder"]) {
  ok("覆盖面: 场景类存在(scene:" + sc + " 有检查项落袋)", checks.some((c) => c[2] === sc));
}
ok("覆盖面: 列面样本量(" + colFaceChecks + " 列次, >=120)", colFaceChecks >= 120);
const failed = checks.filter((c) => !c[1]).map((c) => c[0]);
console.log(JSON.stringify({ ok: checks.length - failed.length, total: checks.length, failed: failed, pages: pagesChecked, colFaces: colFaceChecks }));
"""


def test_r4_dt_table_layout_geometry_equivalence():
    """计划 26-11-10-0027 W1(1) 等价性探针: 现役 _gridTemplate 轨道串与 colAlignCss 对齐序列
    ≡ DT_TABLE.layout 输出(ALL_TABLE_DEFS 真实列定义全量 + colWidths/列态抽样场景)。
    探针红 = 轨道语义冲突 = 计划 R1 停手条款。
    覆盖面口径(26-11-17-0059 评审记档): 实算 13 张**不含 HR 三表** —— 沙箱只截断加载 app.js
    (不加载 hr_status.js, 桥常量 HR_DEFS_BRIDGE 空对象兜底, HR 键不进 ALL_TABLE_DEFS/页数枚举),
    HR 三表的轨道/对齐等价性由例外清单守阵的静态形态钉承担(tpl 全列 + computed 单点委托),
    真跑喂桩(打开 HR 面 × 列态场景)归 W3 parity e2e(T6), 本电池不加 HR 机器。"""
    report = _run_probe(
        _NODE_DT_LAYOUT_EQUIV_PROBE,
        bundle_file("columns.js"),
        os.path.join(STATIC_ROOT, "shared", "dt_table.js"),
        os.path.join(STATIC_ROOT, "shared", "app.js"),
    )
    _assert_battery(report, "dt_table 几何等价性探针")


# W2(2)(计划 26-11-10-0027, 拍板 D4): 例外清单守阵 —— 清单之外零旁路几何 ---------------
_NODE_DT_EXC_LIST_PROBE = r"""
const fs = require("fs");
const path = require("path");
const ROOT = process.argv[1];
const checks = [];
const ok = (name, cond) => checks.push([name, !!cond, ""]);

/* 表面容器的判定 token: 命中即「引擎表格面的几何」(表头/行容器/格), 它们的轨道串只许出自
 * 单点(gridStyle 内联)或 D4 例外清单; 未命中 = 变体外壳的版式栅格(卡片阵/双栏 wrap 等),
 * 与表格列几何无关, 不在本守阵语义内。 */
const TABLE_TOKEN = /\.group-(head|row|table)|\.detail-head|\.h-cell|data-table/;
const rel = (p) => path.relative(ROOT, p).split("\\").join("/");

function walk(dir, out) {
  for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
    const p = path.join(dir, e.name);
    if (e.isDirectory()) walk(p, out);
    else if (/\.(js|html|css)$/.test(e.name)) out.push(p);
  }
  return out;
}
const files = walk(ROOT, []);
ok("扫描面非空(静态目录在盘)", files.length > 100);

/* 块注释剥离(跨行): 注释里的提及(components.css 有「此处不写 grid-template-columns 以免
 * 误导」的纪律注)不是代码事实, 不进判定 —— 只 mask 块注释 /*..*／, 行注释不动(不冒 URL 误伤)。 */
function maskBlockComments(lines) {
  const out = [];
  let inBlock = false;
  for (const ln of lines) {
    let s = "", rest = ln;
    while (rest.length) {
      if (!inBlock) {
        const a = rest.indexOf("/*");
        if (a < 0) { s += rest; break; }
        s += rest.slice(0, a);
        rest = rest.slice(a + 2);
        inBlock = true;
      } else {
        const b = rest.indexOf("*/");
        if (b < 0) { rest = ""; break; }
        inBlock = false;
        rest = rest.slice(b + 2);
      }
    }
    out.push(s);
  }
  return out;
}

/* 1. camelCase 生产者(gridTemplateColumns, JS 内联样式产物与 computed 读取):
 *    白名单恰两件(内核/引擎 computed 读), table.js 不在白名单、双向钉死(见下), 之外零命中
 *    —— 新旁路产物(手拼轨道串写 style)即红。 */
const camByFile = {};
for (const f of files) {
  const masked = maskBlockComments(fs.readFileSync(f, "utf8").split(/\r?\n/));
  masked.forEach((ln, i) => {
    if (ln.indexOf("gridTemplateColumns") >= 0) (camByFile[rel(f)] || (camByFile[rel(f)] = [])).push({ n: i + 1, ln: ln });
  });
}
const CAMEL_ALLOW = {
  /* dt_table.js: assertLayout 的 computed 读(自查, 非产物) */
  "shared/dt_table.js": 1,
  /* columns_grid.js: _renderedWidths 的 computed 读(列宽引擎, 非产物) */
  "shared/columns_grid.js": 1,
  /* !table.js 刻意**不在**白名单: 它对 gridTemplateColumns 的唯一提及是对外契约头注里的
   * 文档性提及(块注释内), maskBlockComments 后本文件命中应为 0 —— 放进白名单会让
   * 「恰好 1 处真实代码旁路产物」借文档提及的壳恒绿(评审 2 #1 死条目), 故双向钉死如下。 */
};
for (const f of Object.keys(camByFile)) {
  if (f === "shared/columns_computed.js") continue;  /* 单点 computed 家族, 下一节逐条对形 */
  const allow = CAMEL_ALLOW[f];
  ok("[camel] " + f + " 命中恰 " + allow + " 处(实得 " + (camByFile[f].length) + ")",
     allow !== undefined && camByFile[f].length === allow);
}
ok("[camel] 两个 computed 读位仍在(内核/引擎没被搬走)",
   camByFile["shared/dt_table.js"] && camByFile["shared/dt_table.js"].length === 1 &&
   camByFile["shared/columns_grid.js"] && camByFile["shared/columns_grid.js"].length === 1);
/* table.js 双向钉(评审 2 #1): 原文提及恰 1 处(契约头注文档仍在, 被顺手删注释也红) +
 * 掩码后零命中(提及确在块注释内 —— table.js 出现任何**代码**产物本条即红, 无白名单可借)。 */
const tblRaw = fs.readFileSync(path.join(ROOT, "shared", "table.js"), "utf8");
ok("[camel] table.js 原文提及恰 1 处(契约头注文档仍在)",
   tblRaw.split("gridTemplateColumns").length - 1 === 1);
ok("[camel] table.js 掩码后零命中(文档提及确在块注释内, 代码产物零放行)",
   !camByFile["shared/table.js"]);

/* 2. columns_computed.js: 每条都恰是单点委托形 this._gridTemplate("<id>"), id 集与表注册表
 *    (ALL_TABLE_DEFS 键)逐一互对 —— 新表注册了却没接单点 computed / 旁路 computed 即红。
 *    计划 26-11-17-0059 W1(1)(2) E6 并入翻面: HR 三表(hrDetail/hrWave/hrKv)的定义源在
 *    hr_status.js 的 HR_TABLE_DEFS(P5), 经 window.AQB_HR_TABLE_DEFS 桥并进 app.js 的
 *    ALL_TABLE_DEFS(桥常量 HR_DEFS_BRIDGE) —— computed 计数冻结值随三表注册升到 16;
 *    id 互对口径 = 每 id 落到「app.js 两空格字面行 或 hr_status.js HR_TABLE_DEFS 字面行」
 *    之一, 且桥合并/桥导出在盘(HR 三表经 ALL_TABLE_DEFS 走单点, 不旁路第二注册表)。 */
const ccHits = camByFile["shared/columns_computed.js"] || [];
const ids = [];
for (const h of ccHits) {
  const m = h.ln.match(/return \{ gridTemplateColumns: this\._gridTemplate\("(\w+)"\) \};/);
  if (m) ids.push(m[1]);
}
ok("[computed] 每条都是单点委托形(实得 " + ids.length + "/" + ccHits.length + " 条)",
   ids.length === ccHits.length && ccHits.length === 16);
const appSrc = fs.readFileSync(path.join(ROOT, "shared", "app.js"), "utf8");
const hrRegSrc = fs.readFileSync(path.join(ROOT, "shared", "hr_status.js"), "utf8");
const HR_BRIDGE_IDS = ["hrDetail", "hrWave", "hrKv"];
ok("[computed] id 集与表注册表互对(逐 id 是 ALL_TABLE_DEFS 键; HR 三表经 window 桥并入, W1(1)(2) E6)",
   ids.length === 16 && ids.every((id) => new RegExp("^  " + id + ": \\{", "m").test(HR_BRIDGE_IDS.indexOf(id) >= 0 ? hrRegSrc : appSrc))
   && HR_BRIDGE_IDS.every((id) => new RegExp("^  " + id + ": \\{", "m").test(hrRegSrc))
   && /\.\.\.HR_DEFS_BRIDGE \}/.test(appSrc)
   && /window\.AQB_HR_TABLE_DEFS = HR_TABLE_DEFS;/.test(hrRegSrc));
const gridKeys = appSrc.match(/grid: "\w+"/g) || [];
ok("[app] app.js 字面表恰一对 computed(grid: 恰 13 处, 实得 " + gridKeys.length + ")", gridKeys.length === 13);

/* 3. kebab 声明(grid-template-columns, CSS 规则面): 命中表面 token 的规则只许是 D4 例外
 *    清单条目 —— 现清单恰 1 条(04 卡片形态面: 引擎行容器被变体覆写成两列卡片栅格);
 *    新表面旁路(含未来变体把别的面的行容器覆写成栅格)即红。 */
const D4_EXCEPTIONS = [
  { f: "shared/drawer_tpl/04-trackers-status-cards-tall.js", token: ".dt04-list .group-table",
    why: "04 卡片形态面: 行容器两列卡片栅格(非列状数据, D4 例外)" },
];
const surfHits = [];
const jsMultiline = [];  /* .js 命中行不带 { 的多行规则形(非常规, 见下) */
for (const f of files) {
  const r = rel(f);
  const lines = maskBlockComments(fs.readFileSync(f, "utf8").split(/\r?\n/));
  lines.forEach((ln, i) => {
    if (ln.indexOf("grid-template-columns") < 0) return;
    if (/\.js$/.test(r)) {
      /* .js(CSS 字符串): 机制一致性取舍(评审 2 #2) —— 选择器-配对大括号解析在 .js 侧会被
       * 代码大括号与非 CSS 字符串(querySelector 选择器等)拼出幻影规则, 故不复制 .css/.html
       * 的规则解析, 改把「选择器与首条声明同行」的 drawer_tpl CSS 字符串惯例**钉成断言**:
       * 命中行必须自带 {。多行规则形(选择器行/声明行分离)不是静默逃逸而是本断言红 ——
       * 要么回到单行惯例, 要么显式改本守阵(与 .css/.html 解析对齐)。12 处既有命中全合规。 */
      if (ln.indexOf("{") < 0) jsMultiline.push(r + ":" + (i + 1));
      const win = [lines[i - 1] || "", ln, lines[i + 1] || ""].join("\n");
      if (TABLE_TOKEN.test(win)) surfHits.push({ f: r, n: i + 1, ctx: win });
      return;
    }
    /* .css/.html(真样式表): 前后一行窗口 + 整段规则解析(选择器到配对大括号), 双轨都算命中面。 */
    const win = [lines[i - 1] || "", ln, lines[i + 1] || ""].join("\n");
    if (TABLE_TOKEN.test(win)) surfHits.push({ f: r, n: i + 1, ctx: win });
  });
  if (/\.(css|html)$/.test(r)) {
    const cssText = lines.join("\n");
    const re = /([^{}]*)\{([^{}]*)\}/g;
    let m;
    while ((m = re.exec(cssText))) {
      if (m[2].indexOf("grid-template-columns") >= 0 && TABLE_TOKEN.test(m[1] + m[2])) {
        if (!surfHits.some((h) => h.f === r && h.ctx.indexOf(m[2].trim()) >= 0)) {
          surfHits.push({ f: r, n: 0, ctx: (m[1] + "{" + m[2] + "}").slice(-200) });
        }
      }
    }
  }
}
ok("[kebab-js] 惯例钉死: .js 命中行必自带 {(多行规则形即红, 实得 " +
   (jsMultiline.join(" | ") || "无") + ")", jsMultiline.length === 0);
ok("[kebab] 表面几何规则恰 " + D4_EXCEPTIONS.length + " 条 = D4 例外清单(实得 " +
   surfHits.map((h) => h.f + ":" + h.n).join(" | ") + ")",
   surfHits.length === D4_EXCEPTIONS.length &&
   D4_EXCEPTIONS.every((e) => surfHits.some((h) => h.f === e.f && h.ctx.indexOf(e.token) >= 0)));

/* 4. D4 例外清单存在性: 清单点名的东西必须真实在盘(条目漂移即红, 防「例外清空了守阵却照绿」)
 *    a. 04 卡片栅格条目本体(.dt04-list .group-table 两列栅格)在 04 变体里恰 1 处;
 *    b. HR 三表(hrDetail/hrWave/hrKv)经 ALL_TABLE_DEFS 走单点 + settings-detail grid 几何
 *       恰 3 处 —— 26-11-17-0059 W1(3) 迁 grid 翻面: 旧口径「HR 三表零 grid 几何」「settings-detail
 *       零 grid 几何」「hrDetail 借壳形态在(thead 模式)」随 thead 借壳退役删除(HR 三表已是
 *       引擎 grid 面, 几何合法出自 DT_TABLE.layout 单点); 新钉: 三表注册在盘、全列带 tpl(几何
 *       唯一来源)、stickyHead:false(模态头不进主表头高测量)、settings-detail 每表恰一座
 *       aq-table 表头 + 一处行 gridStyle + 一处行 data-table 锚, 且生产面零 gridTemplateColumns
 *       字面量(旁路拼轨即红)。 */
const f04 = fs.readFileSync(path.join(ROOT, "shared", "drawer_tpl", "04-trackers-status-cards-tall.js"), "utf8");
const l04 = f04.split(/\r?\n/).filter((ln) => ln.indexOf("group-table") >= 0 && ln.indexOf("grid-template-columns") >= 0);
ok("[D4] 04 条目在盘(.dt04-list .group-table 两列卡片栅格恰 1 处)",
   l04.length === 1 && /\.dt04-list \.group-table/.test(l04[0]) && /repeat\(2, minmax\(0, 1fr\)\)/.test(l04[0]));
const hrSrc = fs.readFileSync(path.join(ROOT, "shared", "hr_status.js"), "utf8");
for (const id of ["hrDetail", "hrWave", "hrKv"]) {
  ok("[D4] HR 条目在盘: HR_TABLE_DEFS." + id, new RegExp("^  " + id + ": \{", "m").test(hrSrc));
}
const hrTplCount = (hrSrc.match(/tpl: "/g) || []).length;
ok("[D4] HR 三表列定义全列带 tpl(几何唯一来源 = DT_TABLE.layout 单点, W1(3) 翻面: 实得 " + hrTplCount + "/20)",
   hrTplCount === 20);
ok("[D4] HR 三表描述符 stickyHead: false 恰 3 处(模态头不参与主表 sticky-head/--head-h 测量, W1(3) T2 拍板)",
   (hrSrc.match(/^    stickyHead: false,$/gm) || []).length === 3);
const setDetail = fs.readFileSync(path.join(ROOT, "shared", "tpl", "settings-detail.html"), "utf8");
ok("[D4] settings-detail HR 三表 grid 几何恰 3 处(每表一座: aq-table 表头 + 行 gridStyle + 行 data-table 锚)",
   (setDetail.match(/<aq-table table-id="hr/g) || []).length === 3 &&
   (setDetail.match(/gridStyle\('hr/g) || []).length === 3 &&
   (setDetail.match(/data-table="hr/g) || []).length === 3);
ok("[D4] settings-detail 零旁路拼轨(gridTemplateColumns 字面量零残留)",
   !/gridTemplateColumns|grid-template-columns/.test(setDetail));

/* 5. 单点完整性: _gridTemplate 委托 DT_TABLE.layout 且无旁路拼接; colAlignCss 对齐取自
 *    layout().aligns —— 委托松开 = W1 成果回退。 */
const cgSrc = fs.readFileSync(path.join(ROOT, "shared", "columns_grid.js"), "utf8");
ok("[单点] _gridTemplate 委托 DT_TABLE.layout(旁路 .map/.join 拼轨零回潮)",
   /_gridTemplate\(page\) \{\s*\n\s*return window\.DT_TABLE\.layout\(this\._visibleCols\(page\), this\.colWidths\[page\] \|\| \{\}\)\.gridTemplate;/.test(cgSrc) &&
   !/_gridTemplate\(page\) \{[\s\S]{0,400}\.join\(/.test(cgSrc));
const ccSrc = fs.readFileSync(path.join(ROOT, "shared", "columns_computed.js"), "utf8");
ok("[单点] colAlignCss 对齐序列取自 DT_TABLE.layout().aligns", /DT_TABLE\.layout\(/.test(ccSrc));

/* 6. assert 侧豁免清单本体(D4 的 assert 落点, 评审 2 #3): 几何例外之外还有一层 —— 渲染自查
 *    对计数语义不成立的面/行的豁免(ASSERT_SKIP_FACES 两键 + empty-row 行级豁免)。豁免被删
 *    不会让几何变错, 但 04 面将每拍刷 console.error 噪声(e2e 运行期错误守阵全红), 故豁免
 *    清单本体也钉死: 键集恰两键、行级豁免字面在 _assertLayoutPair —— 删豁免即红, 与
 *    「例外明文化」同纪律(例外只许显式改, 不许静默消失)。 */
const mSkip = cgSrc.match(/var ASSERT_SKIP_FACES = \{([\s\S]*?)\};/);
const skipKeys = mSkip
  ? (mSkip[1].match(/^\s*(\w+):/gm) || []).map((s) => s.trim().replace(/:$/, ""))
  : [];
ok("[assert豁免] ASSERT_SKIP_FACES 键集恰 {drawerTrackerV04, drawerStubV0}(实得 " +
   skipKeys.join(",") + ")",
   skipKeys.length === 2 && skipKeys.indexOf("drawerTrackerV04") >= 0 &&
   skipKeys.indexOf("drawerStubV0") >= 0);
ok("[assert豁免] empty-row 行级豁免仍在 _assertLayoutPair(删占位行豁免即红)",
   /contains\("empty-row"\)/.test(cgSrc));

const failed = checks.filter((c) => !c[1]).map((c) => c[0]);
console.log(JSON.stringify({ ok: checks.length - failed.length, total: checks.length, failed: failed }));
"""

# issue 26-11-15-0332 产品侧修复回归: 出窗最后一探 ---------------------------------------
_NODE_OUTGOING_ROWH_PROBE = r"""
const fs = require("fs");
global.ROW_WIN_MIN = 200;
global.ROW_WIN_OVERSCAN = 10;
global.ROW_WIN_EST_MIN = 200;
global.ROW_WIN_EST_H = { torrent: 42, group: 44, member: 34, drawerContent: 27 };
global.ROW_WIN_GAP_FALLBACK = 0;
global.window = {};
const src = fs.readFileSync(process.argv[1], "utf8");
eval(src + "\n;globalThis.__W2__ = window.AQB_COLUMNS;");
const M = globalThis.__W2__.methods;

const GAP = 6;
const N = 300;
const TRUE_H = (i) => (i % 2 ? 65.781 : 43.7);
const STALE_I = 61;            // 取证里那一行: 真值 65.781
const STALE_H = 69.609;        // 首渲存下的陈旧值(字体交换前的量值)
const DELTA = STALE_H - TRUE_H(STALE_I);   // +3.828px, 取证里的跳变量
let gbrCalls = 0;
// 桩 DOM: 旧窗口的行此刻**仍在场**, gBR 报的是当前真值(字体已换好)
const mkRow = (i, h, visible) => ({
  getAttribute: (a) => a === "data-hash" ? "t" + i : (a === "data-dt-key" ? "k" + i : null),
  getBoundingClientRect: () => { gbrCalls++; return { height: h === undefined ? TRUE_H(i) : h }; },
  checkVisibility: () => visible !== false,
});
const rows = Array.from({ length: N }, (_, i) => mkRow(i));
global.document = {
  querySelectorAll: (sel) => sel === '.torrent-row[data-table="torrent"][data-hash]' ? rows : [],
  querySelector: () => null,
};
const mkList = () => Array.from({ length: N }, (_, i) => ({ hash: "t" + i }));
const mkCtx = () => Object.assign({}, M, {
  rowWin: true,
  // 0553 换键携带块(issue 26-11-11-0553)在 group kind 上读 this.filteredGroups —— 生产是
  // filters.js 的 computed(恒为数组); 本桩只做行高电池、不建模筛选面, 给空集 = 无换键面,
  // 两侧待领池恒空、携带分支零副作用, 不干扰本电池的任何判据。
  filteredGroups: [],
  _winMeasured: { torrent: true, group: true, member: true, drawerContent: true },
  _rowH: { torrent: 50, group: 50, member: 50, drawerContent: 50 },
  _rowHVer: 1,
  _rowHSig: { torrent: "s", group: "s", member: "s", drawerContent: "s" },
  _winResize: 0,
  _winViewH: 800,
  _winScrollY: 8000,
  _winTop: { torrent: 0, group: 0, member: 0, drawerContent: 0 },
  _rowHs: {},
  _rowProbeSig: {},
  _rowPre: {},
  _winGapFor: () => GAP,
  _winContainer: () => null,
});
const seed = (c) => {
  mkList().forEach((m, i) => { c._rowHs["torrent:" + m.hash] = TRUE_H(i); });
  c._rowHs["torrent:t" + STALE_I] = STALE_H;
  return c;
};
const checks = [];
const ok = (name, cond) => checks.push([name, !!cond]);

// --- 红验: 关掉重探 = 修复前行为, padTop 按陈旧存值超量替换 ---
const before = seed(mkCtx());
before._reprobeRenderedRowH = () => {};
const wBefore = M._rowWindow.call(before, "torrent", mkList(), null);
let sumBefore = 0;
for (let i = 0; i < wBefore.start; i++) sumBefore += (i === STALE_I ? STALE_H : TRUE_H(i)) + GAP;
ok("场景有效: 窗口 active 且陈旧行已被 pad 顶掉(start > 陈旧行下标)",
   wBefore.active && wBefore.start > STALE_I && wBefore.padTop > 0 && wBefore.padBottom > 0);
ok("红验: 无重探时 padTop 逐行按陈旧存值累加", Math.abs(wBefore.padTop - (sumBefore - GAP)) < 1e-9);

// --- 绿验: 出窗最后一探把陈旧存值顶成真值, 同一拍 pre[] 按真值累加 ---
gbrCalls = 0;
const c = seed(mkCtx());
const rowHBefore = JSON.stringify(c._rowH);
const sigBefore = JSON.stringify(c._rowHSig);
const w = M._rowWindow.call(c, "torrent", mkList(), null);
let wantPadTop = 0;
for (let i = 0; i < w.start; i++) wantPadTop += TRUE_H(i) + GAP;
wantPadTop -= GAP;
ok("绿验: _rowHs 的陈旧键被出窗真值顶掉", Math.abs(c._rowHs["torrent:t" + STALE_I] - TRUE_H(STALE_I)) < 1e-9);
ok("绿验: padTop 按真值累加(不再超量替换)", Math.abs(w.padTop - wantPadTop) < 1e-9);
ok("修复前后 padTop 差恰 = 陈旧-真值(用户可见跳变消失)",
   wBefore.start === w.start && Math.abs((wBefore.padTop - w.padTop) - DELTA) < 1e-6);
ok("前缀和留存(_rowPre)同步按真值重建(键盘跨窗换算不吃陈旧值)",
   Math.abs(c._rowPre.torrent[STALE_I + 1] - c._rowPre.torrent[STALE_I]
            - (TRUE_H(STALE_I) + GAP)) < 1e-9);

// --- 不踩全表作废坑: 只刷新已有键, 零响应式/签名/均值改动 ---
ok("零全表作废: 键数不变(不删旧键不加新键)", Object.keys(c._rowHs).length === N);
ok("零响应式自激: _rowHVer / _rowH 不动", c._rowHVer === 1 && JSON.stringify(c._rowH) === rowHBefore);
ok("零签名/量齐态作废: _rowHSig / _winMeasured 不动",
   JSON.stringify(c._rowHSig) === sigBefore && c._winMeasured.torrent === true);

// --- 同拍去重: 一拍里 _rowWindow 多次调用只量一次, 几何变了才重量 ---
ok("首拍重探量遍在场行", gbrCalls === N);
M._rowWindow.call(c, "torrent", mkList(), null);
ok("同几何重渲不重复付 gBR(memberPadTop/Bottom/winMembers 三入口同拍)  ", gbrCalls === N);
c._winScrollY = 8100;
M._rowWindow.call(c, "torrent", mkList(), null);
ok("滚动几何变了才再量一次", gbrCalls === N * 2);
const cOff = seed(mkCtx());
cOff.rowWin = false;
M._rowWindow.call(cOff, "torrent", mkList(), null);
ok("rowWin 关闭零重探(早退分支不产出 pad)", gbrCalls === N * 2);

// --- 抽屉 content-visibility:auto 守卫: 未渲染行不得用 intrinsic 占位高改坏真值 ---
gbrCalls = 0;
const cHidden = mkCtx();
cHidden._rowHs["drawerContent:k" + STALE_I] = 28;
cHidden._rowHProbeRows = () => ({ rows: [mkRow(STALE_I, 27, false)], drawer: true });
M._reprobeRenderedRowH.call(cHidden, "drawerContent", "sig-hidden");
ok("抽屉未渲染行(content-visibility:auto)跳过, 且零 gBR",
   cHidden._rowHs["drawerContent:k" + STALE_I] === 28 && gbrCalls === 0);
const cShown = mkCtx();
cShown._rowHs["drawerContent:k" + STALE_I] = 28;
cShown._rowHProbeRows = () => ({ rows: [mkRow(STALE_I, 27, true)], drawer: true });
M._reprobeRenderedRowH.call(cShown, "drawerContent", "sig-shown");
ok("抽屉已渲染行照常量真值(行键取 data-dt-key)",
   cShown._rowHs["drawerContent:k" + STALE_I] === 27 && gbrCalls === 1);

/* --- 抽屉探测位必须按「在场变体锚」收窄(评审 #3) ---
 * 上面两条把 _rowHProbeRows 换成桩, 抽屉分支本体(锚收窄 / segs 跳过 / dtBridgeTbl 门 /
 * data-dt-key 键)一行都没被执行: 退回裸扫 `.group-row[data-dt-key]` 时三层全绿, 而合并态
 * 同屏的 peers/trackers 桥行会被记成 drawerContent 行高(代码注释警告的正是这个)。 */
const contentRow = mkRow(STALE_I, 27, true);   // 真·content 桥行
const peersRow = mkRow(STALE_I, 99, true);     // 别座表(peers)桥行: 同 data-dt-key, 高 99
const segsRow = mkRow(STALE_I, 88, true);      // segs 描述符(显式不接窗): 也不许采
global.window.AQB_DRAWER_TPL_DEFS = {
  drawerSegs: { window: "drawerContent", variantTab: "segs", segs: true },
  drawerContent: { window: "drawerContent", variantTab: "content" },
  drawerPeers: { window: "drawerContent", variantTab: "peers" },
};
const realQ = global.document.querySelector;
const realQSA = global.document.querySelectorAll;
const blockOf = (rows) => ({ querySelectorAll: () => rows });
global.document.querySelector = (sel) => {
  if (sel === '[data-dt-table-anchor="drawerContent"] .group-table') return blockOf([contentRow]);
  if (sel === '[data-dt-table-anchor="drawerPeers"] .group-table') return blockOf([peersRow]);
  if (sel === '[data-dt-table-anchor="drawerSegs"] .group-table') return blockOf([segsRow]);
  return null;
};
// 回归形态(裸扫)的结果集必须照实给出 —— 三座表的桥行都在里面, 否则钉不住这条
global.document.querySelectorAll = (sel) =>
  sel === ".group-row[data-dt-key]" ? [contentRow, peersRow, segsRow] : [];
gbrCalls = 0;
const cDrawer = mkCtx();
cDrawer.dtBridgeTbl = (tab) =>
  ({ content: "drawerContent", peers: "drawerPeers", segs: "drawerSegs" })[tab];
cDrawer._rowHs["drawerContent:k" + STALE_I] = 28;
M._reprobeRenderedRowH.call(cDrawer, "drawerContent", "sig-anchor");
ok("抽屉探测位按在场变体锚收窄: 只采 content 桥行(peers/segs 行不得写进 drawerContent 键)",
   cDrawer._rowHs["drawerContent:k" + STALE_I] === 27 && gbrCalls === 1);
global.document.querySelector = realQ;
global.document.querySelectorAll = realQSA;
global.window.AQB_DRAWER_TPL_DEFS = undefined;

/* --- 空探不记账(评审 #2): 行在场但 gBR 全报 0 的那一拍不得烧掉去重签名 ---
 * 两种变异都能骗过旧电池(实测): 把 probed++ 挪到 h>0 检查之前, 或在 `cache[kind] === sig`
 * 之后立刻落盘。后果一致 —— 该滚动几何永久不再重探, 那一批行的陈旧存值再也修不回来,
 * 正是本 issue 要修的病。 */
gbrCalls = 0;
const cEmpty = mkCtx();
cEmpty._rowHs["torrent:t" + STALE_I] = STALE_H;
const qsaOf = (h) => (sel) =>
  sel === '.torrent-row[data-table="torrent"][data-hash]' ? [mkRow(STALE_I, h)] : [];
global.document.querySelectorAll = qsaOf(0);       // 行在场(可见)但高度报 0
M._reprobeRenderedRowH.call(cEmpty, "torrent", "sig-zero");
ok("空探(行在场但 gBR 全 0)不烧去重签名", !(cEmpty._rowProbeSig || {}).torrent);
global.document.querySelectorAll = qsaOf(65.781);  // 下一拍量到真值
M._reprobeRenderedRowH.call(cEmpty, "torrent", "sig-zero");
ok("同几何下一拍照常重探且不把 0 写进 _rowHs",
   gbrCalls === 2 && cEmpty._rowHs["torrent:t" + STALE_I] === 65.781);
global.document.querySelectorAll = realQSA;

// --- 第二根因: 占位估算基准冻结(_measureRowH 量齐后不许再动 _rowH) ---
// flux 取证: pad 区 106 行未量, 均值 65.770→65.806 就把渲染行整体推了 +3.8px。
global.TABLE_DEFS = {
  group: { cols: "gCols", tableRef: null },
  torrent: { cols: "tCols", tableRef: null },
  detail: { cols: "mCols", tableRef: null },
};
const estCtx = () => {
  const e = mkCtx();
  e.tCols = [{}, {}, {}]; e.gCols = [{}, {}, {}]; e.mCols = [{}, {}, {}];
  e._rowHSig = { torrent: "0|3|3|3", group: "0|3|3|3", member: "0|3|3|3", drawerContent: "" };
  return e;
};
const cFrozen = estCtx();
cFrozen._rowH.torrent = 65.770123;
M._measureRowH.call(cFrozen);
ok("量齐后 _rowH 估算基准冻结(新量一行不连坐搬动 pad 区上百行)",
   Math.abs(cFrozen._rowH.torrent - 65.770123) < 1e-9);
ok("冻结不误伤逐行实测: 在场行仍被记进 _rowHs", cFrozen._rowHs["torrent:t" + STALE_I] !== undefined);
const cCal = estCtx();
cCal._rowH.torrent = 0;
cCal._winMeasured.torrent = false;
M._measureRowH.call(cCal);
ok("首访量齐那一拍仍校准估算基准(列集合/窗宽变化后同路径重校)",
   cCal._rowH.torrent > 0 && cCal._winMeasured.torrent === true);
/* 冻结门的**第二支**单独隔离(评审 #1): 上一项同时把 _winMeasured 翻 false, 只压到第一支;
 * 这一项保持「已量齐」, 只把基准置 0 —— 若把门写成 `if (!this._winMeasured[kind])`, 基准就
 * 永远停在 0, est 回落成 ROW_WIN_EST_H 常量, 未量行 pad 恒短。 */
const cZero = estCtx();
cZero._rowH.torrent = 0;
cZero._winMeasured.torrent = true;
M._measureRowH.call(cZero);
ok("存值非正(=还没校准)时即便已量齐也重校, 不把 0 冻死",
   cZero._rowH.torrent > 0);

console.log(JSON.stringify({
  ok: checks.filter((x) => x[1]).length, total: checks.length,
  failed: checks.filter((x) => !x[1]).map((x) => x[0]),
}));
"""


def test_r4_outgoing_rowh_reprobe_kills_pad_jump():
    """issue 26-11-15-0332 产品侧修复回归: 出窗最后一探顶掉 _rowHs 陈旧行高。

    取证(issue 26-11-14-1323 像素判据): 单行存值 69.609 vs 实际 65.781, 窗口下滑时
    padTop 按存值超量替换 → 渲染行整体跳 +3.828px。node 电池真跑 _rowWindow, 红验
    (关掉重探)逐行复现陈旧累加, 绿验(产品实现)断言 _rowHs 被真值顶掉、padTop 与
    _rowPre 按真值重建且前后差恰 3.828px; 同时钉住「不踩全表作废坑」(键数/_rowHVer/
    _rowH/_rowHSig/_winMeasured 零改动)、同拍 sig 去重(三入口只量一次、几何不变零 gBR)、
    rowWin 关闭零重探、抽屉 content-visibility:auto 未渲染行跳过(intrinsic 占位高 28 不得
    改坏真值 27)、冻结门**两支各自**都有行为断言(首校 / 存值非正重校)。无 node 静默跳过。"""
    report = _run_probe(_NODE_OUTGOING_ROWH_PROBE, bundle_file("columns.js"))
    if report is not None:
        assert report["total"] == 22, (f"出窗最后一探电池应有 22 项检查(实测 {report['total']})—— 少项 = 检查被删或"
                                       "中途提前 return, 守阵会静默变弱")
    _assert_battery(report, "出窗最后一探电池")


# issue 26-11-16-0716 修复回归: 运行时 root zoom 变化, 行高基准按比例原地重标 -----------
_NODE_ZOOM_RESCALE_PROBE = r"""
const fs = require("fs");
global.ROW_WIN_MIN = 200;
global.ROW_WIN_OVERSCAN = 10;
global.ROW_WIN_EST_MIN = 200;
global.ROW_WIN_EST_H = { torrent: 42, group: 44, member: 34, drawerContent: 27 };
global.ROW_WIN_GAP_FALLBACK = 0;
global.window = {};
const src = fs.readFileSync(process.argv[1], "utf8");
eval(src + "\n;globalThis.__W2__ = window.AQB_COLUMNS;");
const M = globalThis.__W2__.methods;

const N = 300;
const TRUE_H = (i) => (i % 2 ? 65.781 : 43.7);
let Z = 1;   // 当前根缩放: body 比值与逐行 gBR 同步缩放 = 真实浏览器语义(zoom 是纯线性缩放)
let gbrCalls = 0;
const mkRow = (i) => ({
  getAttribute: (a) => a === "data-hash" ? "t" + i : null,
  getBoundingClientRect: () => { gbrCalls++; return { height: TRUE_H(i) * Z }; },
});
const rows = Array.from({ length: N }, (_, i) => mkRow(i));
const mkDoc = () => ({
  querySelectorAll: (sel) => sel === '.torrent-row[data-table="torrent"][data-hash]' ? rows : [],
  querySelector: () => null,
  body: { offsetWidth: 100, getBoundingClientRect: () => ({ width: 100 * Z }) },
});
global.document = mkDoc();
global.TABLE_DEFS = {
  group: { cols: "gCols", tableRef: null },
  torrent: { cols: "tCols", tableRef: null },
  detail: { cols: "mCols", tableRef: null },
};
const mkCtx = () => Object.assign({}, M, {
  rowWin: true,
  // 0553 换键携带块(issue 26-11-11-0553)在 group kind 上读 this.filteredGroups(生产是
  // filters.js 的 computed, 恒为数组) —— 本桩不建模筛选面, 给空集 = 无换键面, 携带分支
  // 零副作用; 重标块对携带值同样按比例平移(携带值是 gBR 视觉量值, 与全表同空间)。
  filteredGroups: [],
  _winMeasured: { torrent: true, group: true, member: true, drawerContent: true },
  _rowH: { torrent: 50, group: 50, member: 50, drawerContent: 50 },
  _rowHVer: 1,
  _rowHSig: { torrent: "0|3|3|3", group: "0|3|3|3", member: "0|3|3|3", drawerContent: "0|3" },
  _winResize: 0,
  tCols: [{}, {}, {}], gCols: [{}, {}, {}], mCols: [{}, {}, {}],
  _rowHs: {},
  _rowProbeSig: {},
  _rowPre: {},
});
const seed = (c) => { for (let i = 0; i < N; i++) c._rowHs["torrent:t" + i] = TRUE_H(i); return c; };

const checks = [];
const ok = (name, cond) => checks.push([name, !!cond]);

// --- 首拍只落基线: _rowHZoom 未定义 = 现有存值本就在当前缩放下量的, 记值不重标 ---
const c = seed(mkCtx());
const ver0 = c._rowHVer;
M._measureRowH.call(c);
ok("首拍落基线: _rowHZoom 记当前 z, 存值/est/版本零改动",
   c._rowHZoom === 1 && c._rowHVer === ver0
   && Math.abs(c._rowHs["torrent:t1"] - TRUE_H(1)) < 1e-9 && c._rowH.torrent === 50);

// --- z 变 1→0.9: 全表按 zNew/zOld 等比例重标, 不删键不翻量齐态(全量重渲坑零触发) ---
Z = 0.9; gbrCalls = 0;
const keys0 = Object.keys(c._rowHs).length;
const measured0 = JSON.stringify(c._winMeasured);
const sig0 = JSON.stringify(c._rowHSig);
M._measureRowH.call(c);
ok("z 变: _rowHs 全表按比例重标(视觉量值 ×zNew/zOld)",
   Math.abs(c._rowHs["torrent:t1"] - TRUE_H(1) * 0.9) < 1e-9
   && Math.abs(c._rowHs["torrent:t0"] - TRUE_H(0) * 0.9) < 1e-9);
ok("z 变: est 基准同比例跟随(未量行 pad 不再按旧缩放偏大 ~11%)",
   Math.abs(c._rowH.torrent - 45) < 1e-9 && Math.abs(c._rowH.drawerContent - 45) < 1e-9);
ok("z 变: 不删键不翻 _winMeasured 不动 _rowHSig, 仅 _rowHVer +1(响应式重算一次)",
   Object.keys(c._rowHs).length === keys0 && measured0 === JSON.stringify(c._winMeasured)
   && sig0 === JSON.stringify(c._rowHSig) && c._rowHVer === ver0 + 1);
ok("z 变: 重标后与当前缩放的逐行 gBR 逐位一致(重标 = 重新实测的等价形式, 零改写)",
   gbrCalls === N
   && Math.abs(c._rowHs["torrent:t7"] - TRUE_H(7) * 0.9) < 1e-9);

// --- 同 z 再拍: 幂等(黄金法则 1), 零重标零 bump ---
gbrCalls = 0;
const snap = JSON.stringify(c._rowHs);
M._measureRowH.call(c);
ok("同 z 再拍幂等: 零重标零 bump(逐行 gBR 照付但不改值)",
   c._rowHVer === ver0 + 1 && JSON.stringify(c._rowHs) === snap && gbrCalls === N);

// --- body 读不到(null): 跳过重标, 不误判成「缩放回 1」(issue §06 方案 A 点名的 1↔z 抖动坑) ---
const noBody = mkDoc(); delete noBody.body;
global.document = noBody;
M._measureRowH.call(c);
ok("z 读不到(null)跳过重标, _rowHZoom 基线与存值都不动",
   c._rowHZoom === 0.9 && Math.abs(c._rowHs["torrent:t1"] - TRUE_H(1) * 0.9) < 1e-9
   && c._rowHVer === ver0 + 1);

// --- 出窗重探的过渡拍让路: zoom 变了但重标块还没跑的拍, 系统性差值不得当行高真变 ---
Z = 0.9;
global.document = mkDoc();
const cT = seed(mkCtx());
cT._rowHZoom = 1;                    // 上次校准在 z=1
cT._rowHs["torrent:t61"] = 69.609;   // 陈旧键(故意, 旧缩放量值)
M._reprobeRenderedRowH.call(cT, "torrent", "sig-t");
ok("过渡拍让路: 不探不写(全表系统性差值不是个别行真变), 且不烧去重签名",
   cT._rowHs["torrent:t61"] === 69.609
   && Math.abs(cT._rowHs["torrent:t0"] - TRUE_H(0)) < 1e-9
   && !(cT._rowProbeSig || {}).torrent);
// 重标落地后(_rowHZoom 追平 + 存值已按比例平移)同几何照常重探, 只顶真陈旧的键
for (const k in cT._rowHs) cT._rowHs[k] *= 0.9;
cT._rowHs["torrent:t61"] = 69.609;   // 重标后仍是陈旧值的键(真正要修的)
cT._rowHZoom = 0.9;
M._reprobeRenderedRowH.call(cT, "torrent", "sig-t");
ok("重标后同几何照常重探: 陈旧键被新缩放真值顶掉, 签名照常落盘",
   Math.abs(cT._rowHs["torrent:t61"] - TRUE_H(61) * 0.9) < 1e-9
   && cT._rowProbeSig.torrent === "sig-t");

// --- _rootZoomOf 单点复用: 令牌回落口径与既有 _winSigExtra 行为逐位一致 ---
delete global.document;
const cS = mkCtx();
ok("_rootZoomOf 读不到 → _winSigExtra 缩放令牌回落 1(与 26-11-14-0844 既有口径一致)",
   M._winSigExtra.call(cS).endsWith("1.0000"));
global.document = mkDoc(); Z = 0.9;
ok("_rootZoomOf 有值 → _winSigExtra 缩放令牌随 body 比值",
   M._winSigExtra.call(cS).endsWith("0.9000"));

// --- 0553 携带 x zoom 重标共存(评审轮 3, issue 26-11-16-0716): 跨拍配对窗口(先删后加隔拍
// 交付)里发生过 zoom 变化时, 孤儿快照 rec.h 是捕获时刻旧缩放值(重标块只平移 _rowHs 不动模块
// 级池) —— 配对必须优先读 _rowHs 旧键现值(已被重标平移), 快照只兜底(旧键被签名作废剔除面) ---
const cCarry = seed(mkCtx());
cCarry._rowHs["group:old"] = 90;   // 旧键现值: 已被重标平移过的新缩放量值
ROWH_ORPHANS.clear(); ROWH_FRESH.clear(); ROWH_LIVE = null;
ROWH_ORPHANS.set("old", { h: 100, ts: Date.now() });   // 捕获时刻快照: 旧缩放值(未随重标平移)
ROWH_FRESH.set("new", Date.now());
M._measureRowH.call(cCarry);
ok("携带 x 重标: 跨拍配对优先读 _rowHs 旧键现值(新缩放), 快照旧缩放值不落新键",
   cCarry._rowHs["group:new"] === 90);
const cFall = seed(mkCtx());
ROWH_ORPHANS.clear(); ROWH_FRESH.clear(); ROWH_LIVE = null;
ROWH_ORPHANS.set("gone", { h: 100, ts: Date.now() });
ROWH_FRESH.set("fresh", Date.now());
M._measureRowH.call(cFall);
ok("携带回落: 旧键已不在 _rowHs(签名作废剔键面)时回落孤儿快照",
   cFall._rowHs["group:fresh"] === 100);
ROWH_ORPHANS.clear(); ROWH_FRESH.clear(); ROWH_LIVE = null;  // 池复位, 不串扰后续电池

console.log(JSON.stringify({
  ok: checks.filter((x) => x[1]).length, total: checks.length,
  failed: checks.filter((x) => !x[1]).map((x) => x[0]),
}));
"""


def test_r4_rowh_zoom_rescale_follows_root_zoom():
    """issue 26-11-16-0716 产品侧修复回归: 运行时 root zoom 变化, 行高基准按比例原地重标。

    根因: _rowHs/_rowH 存的是 gBR 视觉量值, 而重校签名(_winResize|可见列数)不含 zoom ——
    运行时改 root zoom 门恒关, 缩放 1→0.9 后未量行仍按旧缩放估高(偏大 ~11%, 只胖 pad 总高/
    滚动条长度, 不搬已渲染内容)。修复 = _measureRowH 开头比对 _rootZoomOf() 与上次校准基线
    _rowHZoom, 变了就全表乘 zNew/zOld(不删键不翻 _winMeasured 不动冻结门), _rowHVer bump 一次;
    配套 _reprobeRenderedRowH 过渡拍让路(否则「旧缩放存值 vs 新缩放 gBR」的系统性差值会被当
    行高真变写进 _rowHs, 随后重标再乘一遍 = 双重缩放)。
    电池十三项: 首拍只落基线 / 全表等比例重标 / est 同比例跟随 / 键数·量齐态·签名零改动 /
    重标后与逐行 gBR 逐位一致 / 同 z 幂等 / body 读不到(null)不误判成 z=1(1↔z 抖动坑) /
    过渡拍让路不烧签名 / 重标后照常重探 / _winSigExtra 令牌两态口径 / 携带x重标共存(跨拍配对
    优先读 _rowHs 重标现值, 快照只兜底) / 携带回落(旧键被签名作废剔键面时才落快照值)。
    无 node 静默跳过。"""
    report = _run_probe(_NODE_ZOOM_RESCALE_PROBE, bundle_file("columns.js"))
    if report is not None:
        assert report["total"] == 13, (f"缩放重标电池应有 13 项检查(实测 {report['total']})—— 少项 = 检查被删或"
                                       "中途提前 return, 守阵会静默变弱")
    _assert_battery(report, "缩放重标电池")


def test_r4_dt_table_exception_list_geometry_guard():
    """计划 26-11-10-0027 W2(2), 拍板 D4: dt_table 例外清单守阵 —— 清单之外零旁路几何。

    例外清单(D4 拍板明文化, 本守阵是其机械面):
      - HR 三表(hrDetail/hrWave/hrKv): 注册面随 26-11-17-0059 W1(1)(2) E6 并入、渲染面随
        W1(3) 迁 grid 同步翻面 —— 定义源在 hr_status.js 的 HR_TABLE_DEFS(P5), 经
        window.AQB_HR_TABLE_DEFS 桥并进 app.js 的 ALL_TABLE_DEFS, 本电池钉「经 ALL_TABLE_DEFS
        走单点 + 桥在盘 + 全列带 tpl(几何唯一来源)+ stickyHead:false + settings-detail grid
        几何恰 3 处(每表一座 aq-table 表头/行 gridStyle/行 data-table 锚)」; 旧形态断言
        (HTML thead 借壳 / HR 面零 grid 几何)已随 thead 借壳退役删除(W1(3)(5) 同笔);
      - 04 卡片形态面(drawerTrackerV04): 引擎行容器被变体有意覆写成两列卡片栅格
        (行是卡片非列状数据, parity e2e 另有「卡片形态规格」守阵), 例外条目 = 该 CSS 规则恰 1 处。
    断言六节: camelCase 产物白名单(恰两件; table.js 双向钉死 —— 原文提及恰 1 处 + 掩码后
    零命中, 白名单死条目会把真实代码旁路放行成恒绿)/ columns_computed 每条恰单点委托形共
    16 条(13 张 app.js 字面表 + HR 三表经 window 桥并入)且 id 集与表注册表互对(逐 id 落
    app.js 或 hr_status.js 字面行之一, 桥合并/桥导出在盘)/ kebab 声明中命中表面容器的规则恰 =
    D4 例外清单(.js 侧另钉「选择器与首条声明同行」惯例断言 —— 多行规则形即红不静默逃逸;
    .css/.html 侧保留规则解析双轨)/ 例外条目存在性(04 本体 + HR 三表注册/tpl 全列/stickyHead + settings-detail grid 几何恰 3 处与零旁路拼轨)/
    单点完整性(_gridTemplate 委托 + 无拼轨回潮)/ assert 侧豁免清单本体(ASSERT_SKIP_FACES
    键集恰两键 + empty-row 行级豁免字面在 _assertLayoutPair —— 豁免被删即 04 面刷噪声,
    删豁免即红)。node 电池真跑(无 node 静默跳过)。"""
    report = _run_probe(_NODE_DT_EXC_LIST_PROBE, STATIC_ROOT)
    _assert_battery(report, "dt_table 例外清单守阵")


# 26-11-17-0059 W2(2)(3)(4): HR 三表还原链 + 值格渲染注册化 + assert headDom 锚 ------------
_NODE_HR_CELLS_RESTORE_PROBE = r"""
const fs = require("fs");
// 沙箱: window/localStorage/location 桩 + dt_table.js -> hr_status.js -> [app.js 截断切片 +
// columns 域聚合文本] **并入同一次 eval**(与生产 manifest 同序骨架: dt_table 先于 app.js;
// hr_status 先于 app.js 经桥并入全集; columns 方法体按裸名引用 app.js 列模型常量
// (COLS_STORE_KEY/readColStateRaw), 生产里两段 <script> 共享同一全局词法作用域, 合并 eval
// 与之同构 —— persistPage 真跑(round-trip)必须同 eval, 分开 eval 裸名不可达), 真跑注册/
// 读侧还原/写侧 round-trip/列宽动作。
global.window = {};
global.location = { origin: "http://x" };
let store = {};
global.localStorage = {
  getItem: (k) => (k in store ? store[k] : null),
  setItem: (k, v) => { store[k] = String(v); },
  removeItem: (k) => { delete store[k]; },
};
global.Vue = { createApp: () => ({}) };
const [dtPath, hrPath, headPath, colsPath, tplPath, gridPath, appPath] = process.argv.slice(1);
eval(fs.readFileSync(dtPath, "utf8"));
eval(fs.readFileSync(hrPath, "utf8"));
eval(fs.readFileSync(headPath, "utf8") + "\n" + fs.readFileSync(colsPath, "utf8")
  + "\n;globalThis.__X = { LC: loadColState, pages: ALL_TABLE_PAGES, cols: TABLE_COLUMNS, hidden: DEFAULT_HIDDEN_KEYS, COLM: window.AQB_COLUMNS.methods };");
const LC = globalThis.__X.LC, PAGES = globalThis.__X.pages, COLS = globalThis.__X.cols;
const DT = window.DT_TABLE;
const checks = [];
const ok = (name, cond) => checks.push([name, !!cond]);

// ---- 1. 注册面: 六口子(registerCell/cellOf/CELLS)全活, 名字集恰 20 ----------------
const WANT = [
  "hrDetail.lane", "hrDetail.name", "hrDetail.tid", "hrDetail.uploaded_bytes", "hrDetail.downloaded_bytes",
  "hrDetail.ratio", "hrDetail.need_seed_seconds", "hrDetail.done_iso", "hrDetail.verified_ts", "hrDetail.last_seen",
  "hrWave.lane", "hrWave.status", "hrWave.pages", "hrWave.rows", "hrWave.cutoff", "hrWave.fail_streak",
  "hrWave.count", "hrWave.detail", "hrKv.k", "hrKv.v",
];
ok("注册前 CELLS 为空(注册点在 app.js, 不在 hr_status.js 模块层)", Object.keys(DT.CELLS).length === 0);
window.AQB_HR_CELLS_REGISTER();
ok("注册后 CELLS 名字集恰 20 且逐名对上(漂移/漏注册即红)",
   Object.keys(DT.CELLS).length === 20 && WANT.every((n) => typeof DT.CELLS[n] === "function"));
ok("cellOf 取回注册函数; 未注册名抛错(fail-fast, 不许渲染空白)",
   typeof DT.cellOf("hrDetail.lane") === "function"
   && (() => { try { DT.cellOf("nope.nada"); return false; } catch (e) { return true; } })());

// ---- 2. 保真锚: 渲染器输出逐列 = 迁移前模板 DOM 载体(root/tokens/act) --------------
const api = Object.assign({}, window.AQB_HR_STATUS.methods, {
  fmtSize: (n) => "SZ" + n,
  fmtTs: (ts) => (ts ? "T" + ts : ""),
});
const cell = (name, row) => DT.cellOf(name)(api, row);
// hrDetail 三列重组(拍板 4): 档位徽章 / 核实结论(徽章+副行) / 在列(徽章+副行)
const lane = cell("hrDetail.lane", { lane: "A", lane_text: "考察中" });
ok("hrDetail.lane: 裸文本格(root 空串) + hr-lane 徽章段(色义 hrsLaneCls 复用)",
   lane.root === "" && lane.tokens.length === 1
   && lane.tokens[0].cls === "hr-lane hr-lane-a" && lane.tokens[0].text === "A 考察中");
const nameC = cell("hrDetail.name", { name: "x" });
const nameEmpty = cell("hrDetail.name", {});
ok("hrDetail.name: root wrap + 缺失回落 —(与模板插值 e.name || 同形)",
   nameC.root === "wrap" && nameC.tokens[0].text === "x"
   && nameEmpty.root === "wrap" && nameEmpty.tokens[0].text === "—");
ok("hrDetail.tid/done_iso: mono-cell 载体(完成时间取日期段)",
   cell("hrDetail.tid", { tid: 7 }).root === "mono-cell"
   && cell("hrDetail.done_iso", { done_iso: "2026-01-02T03:04:05Z" }).root === "mono-cell"
   && cell("hrDetail.done_iso", { done_iso: "2026-01-02T03:04:05Z" }).tokens[0].text === "2026-01-02");
const num = cell("hrDetail.uploaded_bytes", { uploaded_bytes: 1024 });
const numNull = cell("hrDetail.uploaded_bytes", {});
ok("数值列: fmtSize 复用 + null 回落 —(hrsSize 单点)", num.tokens[0].text === "SZ1024" && numNull.tokens[0].text === "—");
ok("ratio: null 回落 — / 数值两位小数(hrsRatio 单点)",
   cell("hrDetail.ratio", {}).tokens[0].text === "—"
   && cell("hrDetail.ratio", { ratio: 1.234 }).tokens[0].text === "1.23");
ok("need_seed_seconds: 人话复用 hrsNeedSeed(- 哨兵回落 —)",
   cell("hrDetail.need_seed_seconds", { need_seed_text: "3 天" }).tokens[0].text === "3 天"
   && cell("hrDetail.need_seed_seconds", { need_seed_text: "-" }).tokens[0].text === "—");
const ver = cell("hrDetail.verified_ts", { verified_source: "satisfied", verified_source_text: "已达标", verified_ts: 1700000000 });
ok("hrDetail.verified_ts(已核实): hr-vsrc+色档主层 + hr-sub 副行两段",
   ver.root === "" && ver.tokens.length === 2
   && ver.tokens[0].cls === "hr-vsrc hr-vsrc-b" && ver.tokens[0].text === "已核实"
   && ver.tokens[1].cls === "hr-sub" && ver.tokens[1].text === "已达标 · T1700000000");
const verMid = cell("hrDetail.verified_ts", { lane: "B", lane_text: "B 达标", active: true });
const verNone = cell("hrDetail.verified_ts", {});
ok("hrDetail.verified_ts(中间态/未核实): 色档与文案走 hrsSrcCls/hrsVerdictText 单点",
   verMid.tokens[0].cls === "hr-vsrc hr-vsrc-d" && verMid.tokens[0].text === "在列·B 达标"
   && verNone.tokens[0].cls === "hr-vsrc" && verNone.tokens[0].text === "未核实");
const pres = cell("hrDetail.last_seen", { active: true, missing_streak: 2, last_seen: 1700000000 });
const presOut = cell("hrDetail.last_seen", { verified_source: "absent" });
ok("hrDetail.last_seen: hr-pres 色档主层 + 副行(观察期/最近被见到经 hrsPresenceSub)",
   pres.tokens[0].cls === "hr-pres hr-pres-on" && pres.tokens[0].text === "在列"
   && pres.tokens[1].text.indexOf("观察期 2") >= 0
   && presOut.tokens[0].cls === "hr-pres hr-pres-out" && presOut.tokens[0].text === "已移出");
// hrWave: 状态格 mono 载体 + 色档合并 root; 数值列裸文本
ok("hrWave.status: mono-cell+色档合并 root(failed=error / count_match=false=warn)",
   cell("hrWave.status", { status: "failed", status_text: "s" }).root === "mono-cell error"
   && cell("hrWave.status", { count_match: false, status_text: "s" }).root === "mono-cell warn"
   && cell("hrWave.status", { status_text: "s" }).root === "mono-cell");
ok("hrWave.pages/detail: 裸文本与 mono-cell 载体(detail 缺省回落 —)",
   cell("hrWave.pages", { pages: 3 }).tokens[0].text === 3
   && cell("hrWave.detail", {}).root === "mono-cell" && cell("hrWave.detail", {}).tokens[0].text === "—");
// hrKv: k/v 对 + act 按钮位(按钮本体在模板, E2 硬要求: 注册化不吞交互)
const kvv = cell("hrKv.v", { v: "零行波 · 未确认", cls: "warn", act: 1 });
const kvvPlain = cell("hrKv.v", { v: "x" });
ok("hrKv.k: kv-k 载体; hrKv.v: mono-cell+kv.cls 合并 root + act 置位",
   cell("hrKv.k", { k: "配额" }).root === "kv-k"
   && kvv.root === "mono-cell warn" && kvv.act === true
   && kvvPlain.root === "mono-cell" && !kvvPlain.act);
// 双向互对(评审 minor 修复): 渲染器漏注册与列 key 漂移(改名/增删列)都红 —— 单向 WANT
// 钉不住后者(列 key 改名全守阵照绿而运行时 cellOf 抛错在用户页爆), 集合相等才双向都盖住
const fromCols = ["hrDetail", "hrWave", "hrKv"].flatMap((p) => COLS[p].map((c) => p + "." + c.key)).sort();
const inCells = Object.keys(DT.CELLS).sort();
ok("全部 20 渲染器均注册为函数(名字集与列定义双向互对: 漏注册/列 key 漂移都红)",
   JSON.stringify(inCells) === JSON.stringify(fromCols));
const byPage = (p) => Object.keys(DT.CELLS).filter((n) => n.indexOf(p + ".") === 0).length;
ok("逐页渲染器计数与列定义对齐(hrDetail 10 / hrWave 8 / hrKv 2)",
   byPage("hrDetail") === 10 && byPage("hrWave") === 8 && byPage("hrKv") === 2);

// ---- 3. 还原链读侧: v5 三表子树 -> loadColState(全集遍历, HR 页随并入自动覆盖) ------
ok("HR 三页在 ALL_TABLE_PAGES 全集(16 页)且列登记进 TABLE_COLUMNS(10/8/2)",
   ["hrDetail", "hrWave", "hrKv"].every((p) => PAGES.includes(p)) && PAGES.length === 16
   && COLS.hrDetail.length === 10 && COLS.hrWave.length === 8 && COLS.hrKv.length === 2);
store = { autoqb_cols_v5: JSON.stringify({ v: 5, origin: "http://x", pages: {
  hrDetail: { hidden: ["tid"], order: ["name", "tid", "lane", "tid", "ghost"], w: { tid: "150px", lane: "90px" } },
  hrKv: { hidden: ["k"] },
  hrWave: { hidden: ["pages"], w: { pages: "88px", bogus: "5px" } },
} }) };
let out = LC();
ok("宽还原: HR 页意图宽度读回(固化轨首帧即正确)", out.w.hrDetail.tid === "150px" && out.w.hrDetail.lane === "90px");
ok("序还原: colOrder.hrDetail 洗净读回(脏载荷: 重复 key 去重 + 非法 key ghost 丢弃)",
   JSON.stringify(out.order.hrDetail) === JSON.stringify(["name", "tid", "lane"]));
ok("隐还原: colHidden.hrDetail/hrWave 读回", (out.hidden.hrDetail || []).includes("tid") && (out.hidden.hrWave || []).includes("pages"));
ok("locked k 列还原侧兜底: 写进存储也忽略(loadColState 既有守卫对 HR 页生效)", JSON.stringify(out.hidden.hrKv || []) === "[]");
ok("w 白名单对 HR 页生效(非法 key/残留丢弃)", JSON.stringify(out.w.hrWave) === JSON.stringify({ pages: "88px" }));
store = {};
out = LC();
ok("空存储: HR 页无 DEFAULT_HIDDEN_KEYS 交集 -> 不播种(零列态恢复入口 = 列选择器 E6)",
   ["hrDetail", "hrWave", "hrKv"].every((p) => !(out.hidden[p] || []).length));

// ---- 4. 静态锚: assert headDom 枚举 + 模板消费口 + 注册调用点 ---------------------
const tpl = fs.readFileSync(tplPath, "utf8");
const grid = fs.readFileSync(gridPath, "utf8");
const appSrc = fs.readFileSync(appPath, "utf8");
const hrSrc = fs.readFileSync(hrPath, "utf8");
ok("columns_grid._assertLayouts 含 headDom 分支(HR 三表经枚举面覆盖, 桥面仍走钩子)",
   grid.indexOf("(!def.headRef && !def.headDom)") >= 0);
ok("hr_status.js headDom: true 恰 3 处(三表逐表声明)",
   (hrSrc.match(/^    headDom: true,/gm) || []).length === 3);
ok("settings-detail 三表各挂 hrCellOf 消费口(cellOf -> CELLS)",
   ["hrDetail", "hrWave", "hrKv"].every((t) => tpl.indexOf("hrCellOf('" + t + "'") >= 0));
ok("settings-detail HR 逐列手写 v-if 链零残留(注册化后模板只剩通用壳)",
   !/v-if="c\.key ===/.test(tpl));
ok("app.js 注册调用点在 AQB_HR_STATUS mixin 之后且未被注释(行首语句, 注释旁路即红)",
   appSrc.indexOf("app.mixin(window.AQB_HR_STATUS);") >= 0
   && /^window\.AQB_HR_CELLS_REGISTER\(\);/m.test(appSrc)
   && appSrc.search(/^window\.AQB_HR_CELLS_REGISTER\(\);/m) > appSrc.indexOf("app.mixin(window.AQB_HR_STATUS);"));
ok("hr_status.js 注册函数在盘且 fail-fast(DT_TABLE 缺席即抛)",
   /window\.AQB_HR_CELLS_REGISTER = function/.test(hrSrc)
   && hrSrc.indexOf("DT_TABLE 不在场") >= 0);

// ---- 5. 写侧 round-trip(评审 major 修复): persistPage(唯一写入口)真跑三 HR 页 ------------
// 载荷三键形态先断 store 侧(pages.<p> = {hidden,order,w} 与内存意图一致), 再喂回 loadColState
// 断读回同值 —— 写侧形态破坏(键名漂移/漏 w 段)在回退时无守阵会静默红, 此节钉住。
const CM = globalThis.__X.COLM;
const INTENT = {
  hrDetail: { hidden: ["tid"], order: ["name", "tid", "lane"], w: { name: "150px" } },
  hrWave: { hidden: ["pages"], order: ["lane", "status"], w: { cutoff: "88px" } },
  hrKv: { hidden: [], order: ["k", "v"], w: null },
};
for (const p of Object.keys(INTENT)) {
  const it = INTENT[p];
  store = {};
  const ctx = Object.assign({}, CM, {
    colHidden: { [p]: it.hidden }, colOrder: { [p]: it.order }, colW: { [p]: it.w },
  });
  CM.persistPage.call(ctx, p);
  const raw = JSON.parse(store.autoqb_cols_v5);
  ok("[" + p + "] persistPage 落盘 v5 形态: pages." + p + " = {hidden,order,w} 与内存意图一致",
     raw && raw.v === 5 && raw.origin === "http://x"
     && JSON.stringify(raw.pages[p]) === JSON.stringify({ hidden: it.hidden, order: it.order, w: it.w }));
  const back = LC();
  ok("[" + p + "] round-trip: loadColState 读回同值(hidden/order/w)",
     JSON.stringify(back.hidden[p] || []) === JSON.stringify(it.hidden)
     && JSON.stringify(back.order[p] || []) === JSON.stringify(it.order)
     && JSON.stringify(back.w[p] || null) === JSON.stringify(it.w));
}

// ---- 6. 列宽动作波及 HR 面 + 未展开态零垃圾轨(评审 minor 修复, stub ctx) ----------------
// stub 口径: persistPage 换记录器(只记页名), $nextTick 即时, _headEl 恒 null = 未展开 v-show
// 无盒(R4 口径的沙箱模拟)。断三层: 动作波及三 HR 页 / colW[p] 回 null(全自动, 不固化快照) /
// recomputeEffective 对无盒面零垃圾轨。垃圾轨语义 = colWidths[p] 无**宽度条目** —— 键本身会被
// 置 {}(生产注释「立即回弹性模板」的设计行为, e2e 轮询 JSON.stringify(colWidths[p]||{}) 同口径),
// 键在而条目空 = 无垃圾 px。
{
  const persisted = [];
  const ctx = Object.assign({}, CM, {
    colHidden: {}, colOrder: {},
    colW: { hrDetail: { name: "150px" }, hrWave: { cutoff: "88px" }, hrKv: { v: "40px" } },
    colWidths: {},
    persistPage: (page) => persisted.push(page),
    $nextTick: (fn) => fn(),
    _headEl: () => null,
  });
  ctx.fitColumnsToWindowAll();
  ok("fitColumnsToWindowAll 波及 HR 三页(persisted 含 hrDetail/hrWave/hrKv)",
     ["hrDetail", "hrWave", "hrKv"].every((p) => persisted.includes(p)));
  ok("fitAll 后 HR 三页 colW[p] === null(回全自动, 不固化窗口快照)",
     ["hrDetail", "hrWave", "hrKv"].every((p) => ctx.colW[p] === null));
  ok("fitAll 未展开态(_headEl 无盒)recomputeEffective 零垃圾轨: 三 HR 页 colWidths 无宽度条目",
     ["hrDetail", "hrWave", "hrKv"].every((p) => Object.keys(ctx.colWidths[p] || {}).length === 0));
  ctx.resetAllColumnWidthsAll();
  ok("resetAllColumnWidthsAll 波及 HR 三页且 colW[p] === null(清意图宽度回全自动)",
     ["hrDetail", "hrWave", "hrKv"].every((p) => ctx.colW[p] === null));
}
console.log(JSON.stringify({
  ok: checks.filter((c) => c[1]).length, total: checks.length,
  failed: checks.filter((c) => !c[1]).map((c) => c[0]),
}));
"""


def test_r4_hr_cells_registry_restore_and_assert_anchor():
    """26-11-17-0059 W2(2)(3)(4): HR 三表还原链读/写两侧 + 值格渲染注册化 + assert headDom 锚电池。

    六段真跑(沙箱 = window/localStorage/location 桩 + dt_table.js -> hr_status.js -> [app.js
    截断切片 + columns 域聚合文本] 并入同一次 eval —— columns 方法体按裸名引用 app.js 列模型
    常量(COLS_STORE_KEY/readColStateRaw), 生产里两段 <script> 共享同一全局词法作用域, 合并
    eval 与之同构; 装载序骨架与生产 manifest 同序):
      1. 注册面(E2): AQB_HR_CELLS_REGISTER 真跑后 DT_TABLE.CELLS 名字集恰 20 且与列定义
         **双向互对**(渲染器漏注册与列 key 漂移都红)+ 逐页计数 10/8/2(互对/计数两检查物理
         落位第 2 节块尾), cellOf 取回函数且
         未注册名抛错(fail-fast); 注册前 CELLS 为空 = 注册点确在 app.js(hr_status.js 模块层
         不注册 —— 它先于 dt_table.js 载入, 模块层 registerCell 不可达)。
      2. 保真锚(E2): 渲染器输出逐列对照迁移前模板 DOM 载体 —— hrDetail 三列重组(档位
         hr-lane 徽章 / 核实结论 hr-vsrc+hr-sub 两段 / 在列 hr-pres+hr-sub 两段, 色义/人话全走
         hrs* 单点)、mono-cell 载体(tid/done_iso)、数值列 hrsSize/hrsRatio 缺失回落 —、
         name 列 wrap + — 回落、hrWave 状态格 mono-cell+色档合并 root、hrKv kv-k / mono-cell+
         kv.cls 合并 root + act 置位(按钮本体在模板 —— E2 硬要求: 注册化不吞交互, 行为面由
         e2e hr-history 兜)。
      3. 还原链读侧(W2(2)): v5 三表子树经 loadColState 全集遍历读回(宽/序/隐三键, 序还原喂
         脏载荷钉重复 key 去重 + 非法 key 丢弃 + locked k 列还原侧忽略 + w 白名单洗净对 HR 页
         生效 + 空存储 HR 页无播种), HR 三页在 ALL_TABLE_PAGES(16)且列登记齐(10/8/2)。
      4. 静态锚(W2(3)/W2(4)): columns_grid._assertLayouts 含 headDom 分支(HR 三表经枚举面
         覆盖, 未展开 v-show 无盒 = 未挂载豁免 R4 口径; 桥面仍走钩子)+ hr_status.js
         headDom: true 恰 3 + settings-detail 三表 hrCellOf 消费口 + 逐列手写 v-if 链零残留 +
         app.js 注册调用点在 HR mixin 之后 + 注册函数 fail-fast 字面。
      5. 写侧 round-trip(W2(2)): persistPage(唯一写入口)真跑三 HR 页 —— store 侧 pages.<p>
         = {hidden,order,w} 三键形态与内存意图一致(v/origin 齐全), 喂回 loadColState 读回
         同值(写侧键名漂移/漏段在回退时无守阵会静默红, 本节钉住)。
      6. 列宽动作(W2(2), stub ctx: persistPage 记录器 / $nextTick 即时 / _headEl 恒 null =
         未展开无盒沙箱模拟): fitColumnsToWindowAll/resetAllColumnWidthsAll 波及 HR 三页且
         colW[p] === null(回全自动不固化窗口快照); fitAll 未展开态 recomputeEffective 对三
         HR 页 colWidths **零宽度条目**(垃圾轨语义 = 无 px 条目; 键被置 {} 是生产「立即回
         弹性模板」的设计行为, 与 e2e 轮询 JSON.stringify(colWidths[p]||{}) 同口径)。

    红绿双验锚: 摘 app.js 注册调用 -> **仅第 4 节注册调用点锚红**(第 1/2 节测注册函数本体,
    探针自调, 与调用点解耦; 生产运行时由 hrCellOf -> cellOf fail-fast 兜); 渲染器改名/漏注册
    或列 key 漂移 -> 第 2 节尾双向互对红; 摘 headDom 分支或 headDom 声明 -> 第 4 节对应项红;
    模板退回逐列 v-if 链 -> 第 4 节消费口/零残留两项红; persistPage 落盘形态破坏 -> 第 5 节红;
    列宽动作旁路 HR 或对无盒面固化垃圾轨 -> 第 6 节红。无 node 静默跳过(与既有电池同口径)。
    """
    shared = os.path.join(STATIC_ROOT, "shared")
    # app.js 截到 loadColState 结束(接线段不进沙箱; 注册调用点用原文静态钉, 不依赖切片)
    head_path = os.path.join(tempfile.gettempdir(), f"aqb_app_head_hr_cells_{os.getpid()}.js")
    src = open(os.path.join(shared, "app.js"), encoding="utf-8").read()
    marker = "const initialColState = loadColState();"
    with open(head_path, "w", encoding="utf-8", newline="\n") as f:
        f.write(src[:src.index(marker)])
    report = _run_probe(
        _NODE_HR_CELLS_RESTORE_PROBE,
        os.path.join(shared, "dt_table.js"),
        os.path.join(shared, "hr_status.js"),
        head_path,
        bundle_file("columns.js"),
        os.path.join(shared, "tpl", "settings-detail.html"),
        os.path.join(shared, "columns_grid.js"),
        os.path.join(shared, "app.js"),
    )
    if report is not None:
        assert report["total"] == 40, (
            f"HR 注册/还原电池应有 40 项检查(实测 {report['total']}) —— "
            "少项 = 检查被删或中途提前 return, 守阵会静默变弱"
        )
    _assert_battery(report, "HR 值格注册/还原链电池")
