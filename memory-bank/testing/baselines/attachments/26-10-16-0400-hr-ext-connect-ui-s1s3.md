# 3405 —— HR 扩展「连接后端」区重排 + 实例状态入表 S1–S3(①区重构 / 台账 state + probe-all / 表格化渲染)

> 摘要: 按计划 `plans/26-10-16-0214-plan-hr-ext-connect-ui.html` §04 实施 S1–S3(布局取 §03.1 纵向流基准 = 模板 A 形态, 选型未记录时以计划自身结构规格为准)。S1: options.html ①区重排为「状态卡 → 发现操作行(一句短说明) → 实例表(真 table.swtab + 表头 + 状态列) → 动作行(重测全部/拉取) + 反馈区 → 「说明与排障」折叠区(收编三段机制长文 + 徽标图例改写「浏览器工具栏」+ 四态框式色样) → 手动端点折叠」; ③④两表加色点 + 行 hover(C5 纯展示)。S2: background.js `noteInstanceHealth` 增第四参 state(台账条目补结构化 state ∈ ok/401/403/http/down/bad-endpoint, pollInstanceOnce 全返回路径显式带 state), 新增 `probeInstance`(只读 GET /api/hr/tasks 复用拉清单一步, C3)与 `probeAll`, 消息面增 `probe-all`(probe-one 随 R3 取消); 徽标/发现/自愈逻辑零改动。S3: options.js `renderInstList` 重写为表格渲染(来源徽标「手动/自动」R2 / token 前 32 位指纹+悬停全值+未填标红 R1 / 行级四态色点纯函数 `rowHealthOf` / 最近联系 / 操作列删仅手动、自动留空悬停说明 R3;「载入」「自测端点连通」删除), `testEndpoint` 改「重测全部」(sendMessage probe-all + C4 10s 禁用窗), `renderConnOverview` 拆大状态字+指标(C6 告警描边), `fillForm` 只留空态初始化。既有守阵(接线/跨层/降噪场景)全绿未改一字。
> 档案: memory-bank/tasks/26-10-16-webui-hr-ext-connect-ui.md
> 基线时间: 2026-10-16 04:00

**Refs:** memory-bank/tasks/26-10-16-webui-hr-ext-connect-ui.md

## TOTAL

```
TOTAL                                               17334    182   5842    158    99%
3405 passed, 4 skipped in 152.41s (0:02:32)
```

- 语句 17334 / 未覆盖 182; 分支 5842 / partial 158; 覆盖率 **99%**(`commands run test.full` 实测, Windows 侧)。
- 与上一基线 `26-10-16-0331`(3403 passed + 4 skipped)差 **+2 passed**: 开工同步快进(13aa8c67→63b94ed3)带入远端 2 笔提交的用例; 本波**零新增 / 零修改测试**(S5 守阵补强是下一波)。TOTAL 语句 −3 / 分支 −4 同为远端带入(非本波改动, 本波全在 JS 侧, 不进 Python 统计)。
- 本轮改动面全在 `extensions/hr-fetch-proxy/` 三个文件(options.html / options.js / background.js), 无 Python/模板改动。
- 行级四态判据 `rowHealthOf` 与 `probe-all` 消息流(node 沙箱实跑)已额外人工验证: 10 例真值表(含 C2 旧台账无 state 降级、401 优先于 ok)全过; 三实例(活/死/401)探测响应 states = [ok, down, 401], 台账结构化落盘正确。
- Linux(WSL) 侧未重测 —— 纯扩展 JS 改动, 无平台分支。

## 本改动面

- `extensions/hr-fetch-proxy/options.html` —— ①区按纵向流重构(状态卡/实例表/动作行/说明与排障折叠); CSS: 状态卡 + .dot 四态色点 + 框式色样 + 行 hover, 删 .inst-row/.stale 死规则; 「自测端点连通」→「重测全部」; badgeLegend 迁入折叠区并改写「浏览器工具栏」
- `extensions/hr-fetch-proxy/background.js` —— noteInstanceHealth 第四参 state; pollInstanceOnce 全返回路径带 state; 新增 probeInstance/probeAll; 消息面 probe-all; 徽标/发现/自愈零改动
- `extensions/hr-fetch-proxy/options.js` —— renderInstList 表格化(rowHealthOf/token 指纹/来源徽标/操作列收窄); testEndpoint → retestAll(probe-all + C4 节流); renderConnOverview 状态卡结构; fillForm 空态化; ③④两表色点(纯展示)

## 下一波(S4/S5/S6, 计划 §04)

- S4: README §2 布局与「重测全部」口径同步(本波未动 README, 范围守恒)
- S5: 守阵七项(rowHealthOf 真值表 / probe-all 存在性 / 选项页无直接探测 fetch 反向断言 / 图例措辞 / 来源徽标两值 / 接线清单与「自测端点连通」「载入」反向断言 / 图标映射), 上游 `[优先]` 徽标期望随 R2 翻转
- S6: 工具栏图标状态色外框(R4, scripts/gen_ext_icons.py + setIcon 路径)
