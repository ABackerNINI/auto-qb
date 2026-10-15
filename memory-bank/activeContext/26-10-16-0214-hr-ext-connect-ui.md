# 26-10-16-0214-hr-ext-connect-ui — 实施 S1–S3(①区重构 / 台账 state + probe-all / 表格化渲染)

> 摘要: 按计划 §04 逐波推进, 本波完成 S1–S3。布局取计划 §03.1 纵向流规格(模板 A 形态 —— 模板选型在档案里从未记录, 以计划自身结构规格为裁量, 已在档案与基线注明)。改动全在 `extensions/hr-fetch-proxy/` 三文件: options.html ①区重排(状态卡 + 实例表真 table + 说明与排障折叠)、background.js(台账补结构化 state + probe-all 只读探测消息)、options.js(实例表四态色点 + 重测全部)。test.full 3405 passed + 4 skipped 全绿, 既有守阵零改动。S4(README)/S5(守阵七项)/S6(图标外框)待下一波。细节单点在档案 `tasks/26-10-16-webui-hr-ext-connect-ui.md` 与基线 `testing/baselines/26-10-16-0400-hr-ext-connect-ui-s1s3.md`。
> 最后活动: 2026-10-16 04:00
> 状态: In Progress(S1–S3 Done; S4–S6 Pending; 真机验收 V1/V2/V7 待用户)

**Refs:** memory-bank/tasks/26-10-16-webui-hr-ext-connect-ui.md

## 本轮落点

- S1 `options.html`: ①区纵向流重构(状态卡/发现行短句/实例表/动作行+反馈区/说明与排障折叠/手动端点折叠); 徽标图例改「浏览器工具栏的扩展图标状态色外框(常驻, 非本页元素)」+ 四态框式色样(R4 措辞提前落 S1, 行为随 S6); ③④两表加 .dot 色点 + 行 hover(C5 纯展示, 数据面零变化); 「自测端点连通」→「重测全部」(id `test` 保留)。
- S2 `background.js`: `noteInstanceHealth(endpoint, ok, note, state)` 第四参; `pollInstanceOnce` 全返回路径显式带 state(ok/401/403/http/down/bad-endpoint); 新增 `probeInstance`(只读 GET, C3)+ `probeAll` + 消息 `probe-all`(probe-one 随 R3 取消); 徽标/发现/自愈逻辑零改动(S2 硬约束)。
- S3 `options.js`: `renderInstList` 表格化(`rowHealthOf` 四态纯函数, 401/403 红优先于 ok; token 前 32 位指纹+悬停全值+未填标红 R1; 「手动/自动」徽标 R2; 操作列删仅手动、自动留空悬停说明 R3); `testEndpoint`→`retestAll`(sendMessage probe-all + C4 10s 禁用窗, 无实例给指路空态 V2); `renderConnOverview` 状态卡(大状态字+指标, C6 告警描边); `fillForm` 只留空态初始化。
- 验证: `commands run test.full` 全绿(既有守阵未改一字, 数字见 kb.baseline); `rowHealthOf` 10 例真值表(含 C2 旧台账降级)与 probe-all 三实例沙箱(ok/down/401)人工实跑全过。

## 下一步 / 移交

- S4: `extensions/hr-fetch-proxy/README.md` §2 布局与「重测全部 + 行内重测」口径同步(本波范围守恒未动)。
- S5: 守阵七项(计划 §04 S5), 上游 `[优先]` 徽标用例期望随 R2 翻转(口径演进)。
- S6: 工具栏图标状态色外框(R4: `scripts/gen_ext_icons.py` + `setIcon({path})`)。
- 真机验收(计划 §06): V1 实例表状态列 / V2 重测全部 / V3 折叠区外无长文 / V7 图标四态外框。
