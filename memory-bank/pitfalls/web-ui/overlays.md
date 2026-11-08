# 浮层与交互

> 摘要: 弹层 / 浮层 / 遮罩 / 多选与命令回执 —— "点了没反应"这类症状的固定排查顺序; 含浮层几何(视口钳位 / 尺寸估算)与 Esc 退栈顺序。
> 触发: 浮层, 弹层, 右键菜单, 遮罩, 点了没反应, 多选, 命令回执, 强制汇报, 起点, anchor, Shift 连选, 落起点, selAnchor, 视口钳位, 菜单高度, 溢出视口, 菜单项点不到, outside of the viewport, ESC 退栈, 退栈顺序, Esc 关错层, 两图同开, 层叠顺序, 透出正文, 背景透明, 毛玻璃, 半透明底, 浮层底, --bg-pop

**Refs:** memory-bank/tasks/26-10-13-memory-bank-kb-nav-esc.md, memory-bank/plans/26-10-02-1955-plan-webui-multi-ctx-actions.html, memory-bank/tasks/26-10-06-webui-ctx-menu-viewport.md, memory-bank/reports/26-10-31-0104-report-webui-speed-esc-vimium.html

### 浮层能透出下方正文: 先查「该皮肤的表面令牌带不带 alpha」, 不是 blur 没写好

- **触发**: 用户报「弹窗/下拉/右键菜单/悬停卡背景透明, 能看见下面正文」; 给浮层排查毛玻璃失效。
- **判别**: 逐项核对 `backdrop-filter` 是错方向 —— 先看该皮肤 `--bg-card/--bg-elev` 的取值。四皮肤里只有 flux 把这两个
  写成 `rgba(...,.82)` / `rgba(...,.92)`(另三套是不透明 hex), 而 flux 的毛玻璃预算钉死 4 处(顶栏/状态栏/抽屉/弹窗),
  **没挂 blur 的浮层读这两个令牌 = 半透明底直接透正文**。判据: 该浮层规则里是否有 `backdrop-filter`; 没有就不该读带 alpha 的表面令牌。
- **处置**: 详细步骤与实测证据见 [attachments/overlays-details.md](attachments/overlays-details.md)

### 全屏遮罩错误浮层无 dismiss 路径 = 整页操作锁 ≤ 轮周期

- **触发**: 错误/提示遮罩 (`position:fixed; inset:0` 全屏) 弹后, 用户"全屏无法操作一段时间"。
- **判别**: 遮罩 dismiss 只在**下一数据轮**里跑 (kb.nav 实测: `hideError()` 只 `applyData()`, 轮 `POLL_MS=30000` ⇒ 拉取失败即整页 ≤30s 不可点击); 遮罩 z 值压其余浮层之上 (nav: overlay 50 > ctxMenu 40 > drawer 30) —— 按 Esc 或点其余层都吃遮罩。
- **处置**: 详细步骤与实测证据见 [attachments/overlays-details.md](attachments/overlays-details.md)

### 浮层"点了没反应"首先查**定位祖先**

- **触发**: 浮层点了没反应 / 面板看不见。
- **判别**: `.pop-menu` 是 `position:absolute` + `top: calc(100% + 4px)`, 容器**必须**有 `position: relative`,
  否则最近定位祖先变成 `.modal-mask`(`inset:0`)⇒ 面板被渲染到**视口外**。
  **同类坑已出现两次。**
- **处置**: 详细步骤与实测证据见 [attachments/overlays-details.md](attachments/overlays-details.md)

### "聚焦即展开"的输入框必须同时 `@click.stop`

- **触发**: 输入框聚焦展开候选面板。
- **判别**: 全局 window click 监听统一关闭浮层, 而 `@focus` 由点击触发 ⇒ **面板开了又被当场关掉**。
- **处置**: 详细步骤与实测证据见 [attachments/overlays-details.md](attachments/overlays-details.md)

### 弹层"左对齐 + 固定宽度"在靠右锚点上会伸出视口

- **触发**: 靠右的锚点弹菜单。
- **判别**: 视口不够宽 ⇒ 菜单右半截在屏幕外。
- **处置**: 详细步骤与实测证据见 [attachments/overlays-details.md](attachments/overlays-details.md)

### 浮层钳位不能用**常量**估算高度 —— 菜单高度随分支差一倍, 下部锚点的底部项点不到

- **触发**: 给弹层/菜单做视口边界吸附; 加菜单项 / 加一条菜单分支 / 改菜单项内边距与字号。
- **判别**: "常量估算 + 光标处初值"的钳位只对**尺寸可预测**的浮层成立。右键菜单真实高度随分支变
  (单种子 14 项 / 批量 10 项 / 整集整剧 6 项 / 表头 5 项 / 文件优先级 4 项, 还受
  `flags.skip_check_menu` 加减项): 实测批量菜单 **393px**, 而 `_menuPos` 的常量写的是 `h=222`
  ⇒ 低估 171px, 判定"放得下"的锚点实际放不下, 菜单底越过视口下缘, 底部项**真实点击不可达**
  (e2e 报 `element is outside of the viewport` 重试到超时, 用户侧就是"点了没反应")。
  ⚠ 症状**与数据量无关**、纯几何: 锚点落在视口下部约 40% 区域即触发, 靠上时菜单向上弹则不触发。
  也**不会**被"页面能滚"救 —— 菜单是 `position:fixed`, 滚页面不会把它露出来。
- **处置**: 详细步骤与实测证据见 [attachments/overlays-details.md](attachments/overlays-details.md)

### Esc 退栈顺序 = 视觉层叠顺序(z-index), 不是打开先后 —— 两图同开时按层高关

- **触发**: 新增浮层 / 调 `lifecycle.js` 的 Esc 退栈链 / 两个浮层可能同开。
- **判别**: 退栈链是一串 `else if`, **书写顺序即优先级**; 这个顺序必须等于用户看到的层叠
  (z-index 高的先关), 否则那次 Esc 会**穿过上层去关底下被盖住的那层**。2026-10-06 报障:
  qB 口径流量图(停靠抽屉, z-index 80)与历史流量图(`.modal-mask` 遮罩, z-index 130)同开时,
  链上抽屉分支排在历史弹层**之前** ⇒ 第一次 Esc 关了看不见的抽屉, 第二次才关看得见的弹层 ——
  与视觉层叠正好相反。
- **处置**: 详细步骤与实测证据见 [attachments/overlays-details.md](attachments/overlays-details.md)

### 无遮罩浮层的三个细节

- **触发**: 做无遮罩浮层 / 自绘候选面板 / 想用原生 `<datalist>`。
- **判别**: ①不 `@click.stop` ⇒ 点输入框也关; ②自绘候选用 `@click` ⇒ 会**先移走焦点**;
  ③原生 `<datalist>` 不受主题控制、会自行超时消失。
- **处置**: 详细步骤与实测证据见 [attachments/overlays-details.md](attachments/overlays-details.md)

### 形态切换要连交互一起重新评审 —— 分栏语境的「保留搜索」移植到覆盖式浮层 = 死锁

- **触发**: 把命中列表/面板从占位布局改成悬浮浮层(或反向); 给覆盖式浮层加新触发交互。
- **判别**: 浮层显隐只由输入词驱动、收起只剩显式动作(清空钮/Esc/离开页面) ⇒ 用户视角就是
  「盖住内容且不消失」; 分栏时代拍板的「点命中只选中、保留搜索」在浮层态变死锁 —— 点完命中,
  切换效果全留在浮层底下看不见, 浮层还赖着(2026-09-28 站点搜索报障: 下拉盖详情且不主动消失;
  形态改浮层时 JS 零改动直接沿用旧交互是直接成因)。
- **处置**: 详细步骤与实测证据见 [attachments/overlays-details.md](attachments/overlays-details.md)

### 不可见的全屏遮罩会拦掉整页点击

- **触发**: 过渡未走完时点不动页面。
- **判别**: Vue 不移除元素, `opacity:0` 的 `position:fixed` 层**吃掉所有点击**。
- **处置**: 详细步骤与实测证据见 [attachments/overlays-details.md](attachments/overlays-details.md)

### flyout 次级菜单: hover 规则会连子面板一起染色 / 只挂 mouseenter 就永远不收

- **触发**: 改右键次级菜单(`.ctx-item.has-sub` + `.ctx-sub`)、改菜单图标 hover 态。
- **判别**: ① `.ctx-item:hover .ico { color: … }` 是**后代**选择器, 而子面板是父项的 DOM 后代 ⇒
  hover 父项会把**整个子面板**的图标一起刷成同一个颜色(用户报"二级菜单图标 hover 变灰");
  单纯加 `>` 还不够 —— 不带 `:where()` 时 hover 规则 0,3,0 会压过语义色规则 0,2,0, 有色图标照样变灰。
  ② 只写 `@mouseenter` 展开、不写收起 ⇒ 鼠标移到别的菜单项上子面板一直挂着(用户报"移出不消失")。
  ③ 收起**不能同步**: 面板 `left: calc(100% + 4px)`, 指针跨 4px 缝隙的瞬间不在父项也不在面板上,
  同步收起 = "鼠标根本进不去子面板"。
- **处置**: 详细步骤与实测证据见 [attachments/overlays-details.md](attachments/overlays-details.md)

### 删除编排在前端而非后端

- **触发**: 改"删除前强制汇报"。
- **判别**: 约定是**前端串行编排**(汇报 → 等回执 → 成功才投递删除), **后端不做复合命令**。
- **处置**: 详细步骤与实测证据见 [attachments/overlays-details.md](attachments/overlays-details.md)

### 多选保留策略: 增量刷新后按 key/hash 交集保留选中

- **触发**: 改多选 / 批量操作 / 整表替换后的选中状态。
- **判别**: 增量刷新(整表替换)会丢选中 ⇒ 必须按 key/hash 交集保留;
  **虚拟行 key(`u-<hash>`)不做存在性校验**; 批量目标拆解时**已消失的 key 跳过**。
- **处置**: 详细步骤与实测证据见 [attachments/overlays-details.md](attachments/overlays-details.md)

### 右键菜单的"目标"必须由**选中集合**决定, 不能只看被点的那一行 (CTX-03)

- **触发**: 改右键菜单 / 加菜单项 / 加视图(多一套 `open*Menu`)。
- **判别**: 菜单只记 anchor(`key`/`hash`/`episode`)而动作直接拿它拼端点 ⇒ **多选形同虚设**:
  选了 N 行右键, 菜单照常弹出、照常成功, 但**只动了被点的那一行** —— 没有任何报错, 肉眼也看不出来
  (真机实测: 选中 5 个种子点"暂停", 只有 1 个变灰; 批量浮条却一次动 5 个, 同一批目标两套口径)。
  ⚠ **判据是"选中集合是否等同于这一行自身的范围", 不是"选中数 > 1"**: 选中 1 个辅种再右键它自己,
  仍是"暂停整组"的普通菜单(集合与范围一致); 但选中 1 个辅种、右键它的**成员行**, 集合(组)≠范围(成员)
  ⇒ 必须升级为批量菜单 —— 否则文案说"暂停该种子"、实际动整个组。
- **处置**: 详细步骤与实测证据见 [attachments/overlays-details.md](attachments/overlays-details.md)

- 起点(anchor)与光标(focus)是两件事; 点击落起点的写入必须排除 Shift: 详见 [attachments/overlays-details.md](attachments/overlays-details.md)

### 命令回执机制: `cmd_id` 的生成与剔除


- **触发**: 改 WEB 命令投递 / 回执。
- **判别**: 入队生成 `cmd_id`, 主循环执行完写 `_web_results[cmd_id]`(**reannounce 例外**, 由确认跟踪器写),
  Web 线程经 `GET /api/cmd/{id}` **只读**; `_drain_web_commands` 把 `cmd_id` 从 args **剔除后才分发**
  (否则 handler TypeError)。
  ❗**下划线前缀键是元数据**(如 `_queued_ts`), drain 里过滤掉**不传 handler**; 测试断言入队参数时也要先 pop。
- **处置**: 详细步骤与实测证据见 [attachments/overlays-details.md](attachments/overlays-details.md)

### 强制汇报的"成功"回执是 **tracker 确认**而非 API 返回

- **触发**: 改 reannounce 的回执判定 / 写它的测试。
- **判别**: 判据 = `status==3`(updating) / `next_announce` 比 baseline 提前 >60 / status 非 2 变 2,
  `REANNOUNCE_CONFIRM_TIMEOUT=30s` 超时判失败。
  前提是**替身 trackers 带 `status` / `next_announce`** —— FakeClient 默认只返回 url ⇒ **永远无结论**。
- **处置**: 详细步骤与实测证据见 [attachments/overlays-details.md](attachments/overlays-details.md)
