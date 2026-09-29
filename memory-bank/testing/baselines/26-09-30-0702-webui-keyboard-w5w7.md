# 基线 · 1813 passed + 3 skipped / 91% —— WEBUI 键盘快捷键 W5-W7 第二波 (局部作用域/后端持久化/自定义面板/收尾)

> 摘要: 计划 plans/26-09-28-0354 §06 波次 W5-W7 全量落地(2026-09-30) —— W5 绑定 E/F/G/I 组
> (次要动作 Shift 族 / 队列与开关 / 反选等空位条目; 单目标动作目标解析要求恰一 hash, 复用
> editMove/editRename/copyTorrentInfo/torrentCmd 既有单种链) + 局部作用域(引擎 _kbScope 三档
> settings/drawer/list 全量生效, 抽屉 Alt+1-4 切页, 设置页 Ctrl+S inputSafe, 模态白名单分流:
> 模态内只响应模态键位; 浮层打开只放行焦点局部键位) + Esc 链尾(帮助浮层进退栈链/escBusy/
> _kbOverlayBusy 三处名单同步)。W6 后端持久化(新 routes/keys.py: GET/PUT /api/keys, 存储
> auto-qb-data/webui-keys.json 与 web.token 同寻址, 读时兜底链 主文件->.bak->默认表, PUT 结构
> 校验 422 + atomic_write keep_backup, 金清单 +2) + 适配器接通(AQB_KEYS reload/save, load 保持
> 同步快照, startPolling 唯一汇合点拉真值) + 自定义面板(设置页「快捷键」分区: VS Code 按下即录
> 录制器(捕获段监听+stopPropagation) / 纯修饰键拒收 / Esc 取消 / 黑名单当场拒绑 / 冲突三选一
> 交换-覆盖对方置空-取消 / 单条与全部重置 / 空串=显式禁用 / 保存 PUT 失败本地回滚 / 离开未保存
> 先确认) + 帮助浮层(Shift+Slash 只读速查 + 前往设置自定义)。W7 守阵扩充(+6 前端 +5 后端)。
> 基线时间: 2026-09-30 07:02 (develop @ 3113627) **未提交**(等用户显式指令)。

TOTAL **1813 passed + 3 skipped / 91%**(12653 语句 / 997 未覆盖 / 4262 分支 / 416 partial, test.full 25.4s, rc=0) ——
较上基线 26-09-30-0555(1802)增 11 条: test_web_shortcuts.py +6(W5 局部作用域接线 / 模态白名单
分流 / 录制器与面板全链 / 适配器与后端单点 / 帮助浮层接线 / 设置页分区; 另 Delete 直连断言随
引擎重构同步收紧浮层+作用域守卫), test_web.py +5(/api/keys 缺省默认表 / PUT 往返与空串禁用
保留 / PUT 非法 422 不触碰磁盘 / 坏 JSON 兜底链 WARN+.bak / schema_version 不识别回默认)。

## 浏览器功能验证(Playwright 探针, ui_harness 真前端, 28 项全过)

- 帮助浮层: Shift+Slash 开 / 速查行 55 条 / Esc 关(退栈链); 「前往设置自定义」直跳设置页
  keys 分区, 面板 55 行渲染。
- 录制器: 空位条目录 KeyU 即时试用(引擎 _kbTable 立即可见); Ctrl+W 黑名单当场拒绑(提示文本
  含「浏览器保留」); 冲突三选一(与超级做种撞 KeyU -> 覆盖对方置空后新条目拿键/对方未绑定);
  重置单条删 override 回默认; 禁用=空串保留在草稿; 保存 PUT 落盘且刷新后改键仍生效(服务端真值)。
- 局部作用域: I 键开抽屉 -> Alt+2 切 Tracker 页 / Alt+4 切内容页; 抽屉内全局键(Digit2)被屏蔽;
  Esc 关抽屉归退栈链。
- E/F 组(种子页平铺行光标): Shift+V 开移动对话框(Esc 关); Ctrl+ArrowUp 队列上移回执
  「已执行: 队列上移」; Shift+C 复制名称成功; K 开列选择器。
- 设置页 Ctrl+S: inputSafe 输入态放行, preventDefault 生效无浏览器保存框, 停留设置页。
- 冒烟对照: dev.harness 96 项 prism 与基线同败 2 项(追剧集行 CTX-03 多选右键 / 隐藏列宽保留,
  均已入池 issues/26-09-30-0602-*; 辅种组行 CTX-03 抖动项本轮未复现), 无新增失败,
  探针无 pageerror(唯一 console 400 为 /api/config 既有「过期页签」保存守卫, 属桩环境现象,
  本波未触碰 config 保存路径)。

## 本轮改动面

- 后端 2: server/routes/keys.py 新增(GET/PUT /api/keys + 兜底链 + 结构校验)、
  routes/__init__.py(ROUTE_BUILDERS 注册)。
- 引擎 1: shortcuts.js(E/F/G/H/I 组 run 全量接线 + _kbSingleHash/_kbEditAct/_kbTorrentCmd/
  _kbTorrentToggle/_kbInvertSel + _kbScope 三档 + _kbOnKeyDown 重构(Delete 并入无条目分支并带
  浮层/作用域守卫) + AQB_KEYS 适配器(reload/save/apply/_sanitize) + 面板与录制器方法族 +
  kbSerialWithDraft/kbDisplayName 模块级单点)。
- 接线 6: polling.js(startPolling 拉键位真值)、state.js(kbHelpOpen/kbDraft/kbSaved/kbRecId/
  kbConflict/kbKeysLoading 根选项)、lifecycle.js(Esc 链挂 kbHelpOpen)、dialogs.js(escBusy 同步)、
  config_hub.js(首页卡/hubNow/hubRestore 认 "keys" + hubGo/hubBack 离开守卫 + 进入拉真值)。
- 模板/CSS 3: settings-detail.html(keys 分区分支: 录制/禁用/重置/冲突三选一/保存放弃全套)、
  popovers.html(帮助浮层)、console_hub.css(.kb-row/.kb-grp-t/.kb-help/.kb-conflict/.kb-danger)。
- 守阵 2: test_web_shortcuts.py(10->16, 头部测试计划同步)、test_web.py(金清单 +2 + keys 后端
  5 条, 头部测试计划同步)。
- 与计划的偏差: ①「模态作用域」本期注册表无 modal 条目, 引擎按 §5.1 预留白名单分流(探针未
  覆盖该分支, 由静态守阵 test_modal_whitelist_branch 钉住); ②列选择器键盘再按被浮层屏蔽,
  关闭走 Esc(K 开/Esc 关, 注册表注释已注明)。
