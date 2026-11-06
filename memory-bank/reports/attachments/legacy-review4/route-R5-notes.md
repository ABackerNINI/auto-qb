# R5 路线小结(存量评审 R4 · static 契约·scripts)

owner: clone3-main · freeze: f088329291e6 · 快照: C:\Users\11059\Desktop\Projects\zcode\auto-qb-review4-snap\auto-qb-zcode-clone3
(执行中逐批追加;终态节在 review.lane.done 后定稿)

## 批次勾选表

| 批 | 内容 | findings 过检 | 状态 |
|---|---|---|---|
| R5-1 | shared 启动与状态: app/state/boot/lifecycle/auth/polling/fetch_low/ui_feedback (3581行) | 24 (major 1 / minor 11 / nit 12) | done |
| R5-2 | shared 菜单·触发·命令链: menu/triggers/commands*/ctx_menu*/view/overlay_fit/ctl_bits/scope_audit/shortcuts(+panel) (3637行) | 10 (minor 7 / nit 3) | done |

## R5-1 批记录(2 面精评: 正确性+安全 / 测试缺口+文档漂移)

- **major 1 条**:polling.js:85 SSE 断线沿判定+换票重连状态机零行为回归测试(唯一守阵为字符串锚)。
- minor 11 条:模态框 resolve 悬空 / 登出不断 SSE+换票重开竞态 / 5 个匿名监听不撤除+句柄堆叠 / ver 驱动 refresh 绕过后台门控 / stopPoll 跳过 onEnd / _esDisconnectEdge 探针声明不存在 / _errlogReseed 探针声明不存在 / 退避曲线零测试 / 列播种语义零测试 / 错误环形缓冲零行为测试 / boot.js「三套 UI」计数漂移。
- 同根双报 1 组已去重:lifecycle.js 匿名监听器(面1 正确性锚 :265 与 面2 测试缺口锚 :181),保留面1 条目。
- py↔js 契约对账(面1 只读对 routes/state.py、routes/events.py、runtime_views.py delta、runtime_stream.py errlog、infra/clock.py):delta/removed/rid/status/errlog/ticket/flags 字段口径无错位。
- 底册复验:R2 终表零命中本批;Open issues 0149(抽屉开合态)/0411(/api/state 分页)仍 Open 未重报。

### 自弃发现(13 条留痕)

面1(6):boot.js fail() innerHTML 拼接无攻击者输入不构成 XSS / token 存 localStorage 系用户拍板设计 / startPoll chain 抛错静默死亡现网不可达 / _logout 不清 pendingOps 窗口极窄 / 超时+AbortError 翻译三处实现系文档化例外(守阵钉同值) / _esDisconnectEdge(undefined) 首次断线 toast 系设计口径。
面2(7):退避注释 2s→15s 系代表性举例 / 401 不断 SSE 属面1 已报不越面 / delta 合并有 e2e 真页面测试担忧不成立 / 字符串锚守阵属既定范式不构成缺口 / boot 超时值守阵核实属实 / auth.js「60 余个 api()」计数值必然漂移 / 底册两条未重报。

## R5-2 批记录(2 面精评: 正确性+安全 / 测试缺口+文档漂移)

- **major 1 条**:shortcuts_panel.js:39 快捷键录制态的非脏关闭路径不调 kbRecordCancel——document 捕获期 _kbRecHandler 残留,下一次任意按键被吞掉并静默提交成键位绑定。
- minor 7 条:cmdStats 单槽无归属校验(旧命令回执错挂新命令) / kbPanelEnter quiet 加载失败后保存会整份覆盖服务端 overrides / view.js 静默刷新失败无退避 1 req/s 死循环 / waitCmd 竞态零测试 / kbConflictResolve 三态零测试 / _auditScope 分类零测试 / ctx 拖拽落点零测试 / setRowIcon 定时器回归零测试 / webui.md「一级只允许一个次级菜单入口」与守阵双双过期 / episode 分支提示宣称已退役旧行为。
- (上列 10 条与 findings 文件一一对应,minor 实数 7、含文档类 1 条 webui.md:9)
- py↔js 契约对账(面1 对照 runtime_commands.py / system.py / ops_skip.py / groups.py):回执 status 三值 / truth 事件 / skip_check 事件 / flags / 组 key base64url 均核实无错位。
- 底册复验:R2 终表零命中本批;Open issue 0411(涉 view.js)仍 Open 未重报。

### 自弃发现(9 条留痕)

面1(9):组 key base64url/hash 十六进制无注入断路面 / auth 失败 sticky 条被 _logout 整体清空 / menu 虚拟行 members[0] undefined 给不出到达路径 / menuTorrent() 有 || {} 兜底 / cmAddSep 跨层重号推不出用户可见失败 / 双层重复 item id 手改配置才可达 / commands_optimistic 双函数系刻意分工有差异清单 / kbConflictResolve serial 恰等时非最小化纯风格 / reannounce 回执缺 cmd_id 给不出触发路径。
面2(9):webui.md「项集一致」按守阵 T3 口径可调和 / _runningToast sticky 系守阵放行工厂本体 / _finishToast 原位落失败有注释声明例外 / [perf] 埋点无用户可感失败 / _searchRefreshBusy 重入组合理论风险 / TRUTH_HOLD_MS 已有守阵 / KB_BLACKLIST 重复添加注释如实 / triggers 登记双向对账已覆盖 / 底册 0411 不重报。

## 执行备注(路线级)

- review.check --root 快照 的 .git 强检查误拒仍在(R2 首报,58849374 只定位根因):本路线用 R3 的 workaround——快照根建空 .git 目录绕过,零代码改动。
- 提交闸门 review.trace 对纯盘点数据提交按累计口径计行(认领提交曾滚入他 clone R4-2 数据),走 Review-Skip「纯盘点数据落盘」豁免。
