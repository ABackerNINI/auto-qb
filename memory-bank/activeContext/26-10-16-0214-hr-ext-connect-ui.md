# 26-10-16-0214-hr-ext-connect-ui — S1–S6 全波完成(①区重构 / 台账 state + probe-all / 表格化渲染 / README 口径 / 守阵 / 图标外框)

> 摘要: 按计划 §04 逐波推进, S1–S6 全部完成。布局取计划 §03.1 纵向流规格(模板 A 形态 —— 模板选型在档案里从未记录, 以计划自身结构规格为裁量, 已在档案与基线注明)。改动: extensions/hr-fetch-proxy 三文件 + manifest + icons/(新 8 PNG) + scripts/gen_ext_icons.py(新) + scripts/hr_ext_stub.py(新, 验收桩) + tests/test_extension_proxy.py 新增 6 守阵。test.full 全绿(数字见基线切片 testing/baselines/26-10-16-0420-hr-ext-connect-ui-s4s6.md)。S4(README)/S5(守阵七项)/S6(图标外框)已于本波落地; 真机验收 V1/V2/V7 待用户(桩服务已起)。
> 最后活动: 2026-10-16 04:34
> 状态: S1–S6 Done; 真机验收 V1/V2/V7 待用户; ⚠事故: 起验收桩时误杀用户生产实例(已停桩释放端口, 坑档 pitfalls/ops/port-kill-prod-instance.md)

**Refs:** memory-bank/tasks/26-10-16-webui-hr-ext-connect-ui.md

## 本轮落点(S4–S6, 2026-10-16 04:20–04:30)

- S4 `extensions/hr-fetch-proxy/README.md`: §2 ①区布局块按新形态同步(状态卡/实例表真表头含状态列/动作行「重测全部」/「说明与排障」折叠); 「自测端点连通」→「重测全部」(页面串 + 排障表 + 「怎么确认它在工作」); 徽标描述统一「浏览器工具栏的扩展图标状态色外框」(R4 框式); 来源徽标「优先」→「手动/自动」(R2)。
- S6 图标外框(R4): `scripts/gen_ext_icons.py`(PIL, dev-only)生成 8 个 PNG 入库 icons/(基础无框 + 绿/橙/红框 × 16/32px, 中性深色底不随主题变, 框色与 BADGE 同源, 色框外暗色描边); manifest `action.default_icon` 指向基础图; `background.js::refreshBadge` 改 `setIcon({path})` 换图 + 徽标文字折中(平时清空零遮挡, 仅「发现失败」态红 `!` + setBadgeBackgroundColor); `badgeStateOf` 判据与触发点不变, try/catch 静默降级保留; 新增纯函数 `badgeIconOf`。
- S5 守阵七项: `tests/test_extension_proxy.py` 新增 6 用例(rowHealthOf 四态真值表含 C2 降级 / probe-all 真跑三实例落台账 / 重测全部走后台反向断言+旧字面量不得回潮 / 图例「浏览器工具栏」措辞 / 来源徽标只有手动自动 / 图标映射+8 文件在盘+manifest); `test_options_swiss_wiring` 元素清单随 S1 更新(helpTroubleshoot/connStateDot/Text/Meta); `test_badge_reflects_connection_state` 随 R4 翻转(OK/.. 文案废止); 上游 `[优先]` 徽标断言在历史测试中不存在, 无需翻转(已核)。
- 附带修复: options.js 一处 S3 遗漏的旧按钮名用户可见串(`先点「自测端点连通」按提示排查` → 「重测全部」)。
- 验证: `commands run test.full` 全绿(覆盖率与数字见基线切片; 比 0400 基线净增 = 本波新增守阵数); 红绿双验三类突变判红(rowHealthOf 红判据删 / BADGE_ICON.ok 改错 / 图例措辞回潮)后还原复绿。
- 验收桩 `scripts/hr_ext_stub.py`(dev-only)已冒烟(发现端点 18788 + 双数据端点, /control 实时翻转 ok/401/down); ⚠**04:31 事故**: 桩起时 18788 绑不上, 未核实监听 pid 19168 身份即跑 `scripts/port_kill.py -- 18788`, **杀掉的是用户的生产 auto-qb 主程序**; 桩已停、端口已释放(TIME_WAIT 不挡重绑), 生产数据未动, 重启生产实例待用户决定。教训入坑档 `pitfalls/ops/port-kill-prod-instance.md`(杀进程前必须能说出 pid 是什么程序; dev 桩不得默认占生产端口 18788)。期间「扩展已在轮询桩」的观察实际是桩在应答, 不是生产后端。

## 下一步 / 移交

- 真机验收(计划 §06): V1 实例表状态列(切 down/401 后点「重测全部」或等 1 分钟轮询) / V2 重测全部 / V7 图标四态外框(发现地址改 127.0.0.1:19999 演示红框 + 角标 !)。
- 教训(待入坑档): 变异测试用 `git checkout --` 回退时冲掉了本轮未提交的 background.js / options.js 改动 —— 未提交工作区禁用 `git checkout -- <file>` 回退变异, 应用精确 Edit 重放。
- 模板选型(A/B/C)从未记录, 布局按 §03.1 纵向流基准(= 模板 A 形态)落地, 档案与基线均已注明。
