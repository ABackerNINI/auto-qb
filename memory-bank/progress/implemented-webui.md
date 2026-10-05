# 已实现 · WEB UI(界面 / 视图 / 状态色)

> 摘要: 摘要: 前端界面与视图的落地记录 —— 设置页 / 追剧视图 / 双界面 / 错误原因 / 各轮修复。
> 触发: WEB UI 做过没有, 前端功能, 设置页, 视图, 状态色, 修复轮次, 双界面

## 已实现 (✅, 有单测覆盖)

> 本文件只留近期条目; 2026-09-26~10-04 二十九条及更早的条目已按 cap 轮转**原文外迁** → [implemented-webui-history.md](implemented-webui-history.md)(下方各条留一行指针, 事实不变)。

- **WEB UI 强制汇报确认机制重构: epoch 前跳证据门控 + warn 第三态**(2026-10-05, 计划
  [plans/26-10-05-0923](../plans/26-10-05-0923-plan-reannounce-confirm-rework.html) S0-S5 全落地, 提交链
  `f251e301`(S0 真机探针三点实证: 前跳 +5466s / TOL=3.0 维持 / 推迟路径 min_e+1 冻结)→`8873c889`
  (S1+S2 webui/commands.py 判定提为纯函数 `_verdict_reannounce` 五分支: ②updating 直证 / ③
  `next > b_next+TOL` 前跳主判据 —— 方向反转, 旧判据 `na < b_na-60` 把 epoch 绝对秒当倒计时恒不触发是
  失效根因, 限基线 status≥2 行 + min 窗口假瞬态守卫 / ④status4+msg 判败先于②③防重试排程假前跳误判 /
  legacy 回退; runtime.py check_pending 三桶聚合 + item 级窗口 + `reannounce_background` 后台核实上限 500)
  →`04b5899f`(S3 static/shared/commands.js: `_pollCmd` 终结纳入 warn 第三态 / SSE 与轮询共用 status 透传 /
  三桶按 r.status 分流 / sticky 文案补推迟子句 / delete_flow 保守口径 warn 不放行删除), 分支
  feat/reannounce-confirm-rework 待并回): 推迟路径(min_interval 未过期)早回执「已受理: 推迟至 HH:MM」+
  后台日志核实, 停止种子直判「未确认」, 超时落 warn 诚实标签不再恒误报「失败」; 机器分流依据从「前缀」
  改为「status」(ok/error/warn)。§05 十一组用例全落地净增 +7; 新坑档
  [pitfalls/backend/announce-epoch-semantics](../pitfalls/backend/announce-epoch-semantics.md);
  test.full 2610 passed + 4 skipped / 98%(基线
  [26-10-05-1202](../testing/baselines/26-10-05-1202-reannounce-confirm-rework.md)); 档案
  [tasks/26-10-05-backend-reannounce-confirm-rework](../tasks/26-10-05-backend-reannounce-confirm-rework.md)(Done)。

- **WEB UI 危险动作防护: 重新校验确认框 + 跳检前置条件三分流预检**(2026-10-05, 计划
  [plans/26-10-05-0314](../plans/26-10-05-0314-plan-webui-danger-guards.html) S0-S5 全落地, 提交链
  `bcc2bce2`(S1a store 组级判定上移单点, grouping_mod 委托保签名)→`09683720`(S1b-1 ops
  `_skip_gates_detail` 三分流判定单点只读变体 + G3-G6 新闸门 + force 语义 + precheck dry-run +
  filelist 并入执行链, R2 live 复核前移到闸门之前)→`7d9595a7`(S1b-2 G7/G8 组内镜像闸门: 校验在途
  =force 可豁越 / 校验失败推断=blocked 硬拒)→`0ff19787`(S2 预检端点
  `POST /api/torrents/skip-check/precheck` + 单发/批量 force 透传)→`51e30393`(S3
  `_recheckConfirm` 共用确认框接入全部鼠标入口, 与键盘路径同文案)→`bd532d26`(S4 跳检预检对话框
  三分流状态机: 进框禁用→预检→按态渲染, force 钮必须先见赌注), 分支 webui-danger-guards 待并回):
  跳检「该不该允许」判定下沉 ops 单点与规则侧同谓词(规则侧零变化, test_checking 69 条全程绿),
  WEB 确认框升级「进框禁用→预检→按态渲染」三分流(case 1 禁止无逃生 / case 2 可显式强制 /
  case 3 放行), force 服务端裁决只豁越 G5/G7; 重新校验鼠标三通道补齐确认框。新守阵 22 条(每闸门
  一测 + 红验探针先红后恢复; T13/T24 首版经红验暴露突变盲区升级, 坑档
  [pitfalls/testing/static-guard-mutation](../pitfalls/testing/static-guard-mutation.md));
  test.full 2576 passed + 4 skipped / 99%(基线
  [26-10-05-0737](../testing/baselines/26-10-05-0737-webui-danger-guards.md)); 档案
  [tasks/26-10-05-webui-danger-guards](../tasks/26-10-05-webui-danger-guards.md)(Done)。

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

- WEB UI **WEB UI HR 拉取历史详情表(2026-10-04)**: 已外迁 → [implemented-webui-history.md](implemented-webui-history.md)(cap 轮转, 事实不变)
- WEB UI **WEB UI 添加种子三下拉 label 闪烁「第四轮」(JS 收层守卫单点加固)(2026-10-04)**: 已外迁 → [implemented-webui-history.md](implemented-webui-history.md)(cap 轮转, 事实不变)
- WEB UI **WEB UI qB 口径流量图三图(2026-10-04)**: 已外迁 → [implemented-webui-history.md](implemented-webui-history.md)(cap 轮转, 事实不变)
- WEB UI **WEB UI 添加种子三浮层互斥补双向(closeAddPopsExcept 单点)(2026-10-04)**: 已外迁 → [implemented-webui-history.md](implemented-webui-history.md)(cap 轮转, 事实不变)
- WEB UI **WEB UI 添加种子三下拉 label 闪烁「第三轮」(上轮修法未修住)(2026-10-04)**: 已外迁 → [implemented-webui-history.md](implemented-webui-history.md)(cap 轮转, 事实不变)
- WEB UI **WEB UI 抽屉出入过渡动画(2026-10-04)**: 已外迁 → [implemented-webui-history.md](implemented-webui-history.md)(cap 轮转, 事实不变)
- WEB UI **WEB UI 添加种子三下拉「第二轮遗留四项」(2026-10-03)**: 已外迁 → [implemented-webui-history.md](implemented-webui-history.md)(cap 轮转, 事实不变)
- WEB UI **WEB UI 添加种子三下拉「失焦即收 + 限高不出窗」(2026-10-03)**: 已外迁 → [implemented-webui-history.md](implemented-webui-history.md)(cap 轮转, 事实不变)
- WEB UI **WEB UI 种子详情抽屉重设计: 浮层 → 底部停靠属性面板 (方案A)(2026-10-03)**: 已外迁 → [implemented-webui-history.md](implemented-webui-history.md)(cap 轮转, 事实不变)
- WEB UI **WEB UI 站点级「显式空 = 覆盖为空」三态 + 「跟随全局」删键: 删除类标签全局/站点作用域混淆修复(2026-10-03)**: 已外迁 → [implemented-webui-history.md](implemented-webui-history.md)(cap 轮转, 事实不变)
- WEB UI ****WEB UI HR 判定新鲜度置脏 (2026-10-03, 计划(2026-10-03)**: 已外迁 → [implemented-webui-history.md](implemented-webui-history.md)(cap 轮转, 事实不变)
- WEB UI **多选右键菜单四项(限速/移动/跳检/导出 .torrent)+ 跳检菜单开关 `web.skip_check_menu`**: 已外迁 → [implemented-webui-history.md](implemented-webui-history.md)(cap 轮转, 事实不变)
- WEB UI **HR 站点状态区展示二轮改造(2026-10-02)**: 已外迁 → [implemented-webui-history.md](implemented-webui-history.md)(cap 轮转, 事实不变)
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
