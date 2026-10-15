# 3411 —— HR 扩展「连接后端」区重排 + 实例状态入表 S4–S6(README 口径 / 守阵七项 / 图标状态色外框)

> 摘要: 按计划 `plans/26-10-16-0214-plan-hr-ext-connect-ui.html` §04 实施 S4–S6(S1–S3 已于 04:00 基线完成, 布局取 §03.1 纵向流基准 = 模板 A 形态)。S4: `extensions/hr-fetch-proxy/README.md` §2 布局块按①区新形态同步(状态卡/实例表真表头含状态列/动作行「重测全部」/「说明与排障」折叠), 「自测端点连通」→「重测全部」, 排障表补实例表状态列指路, 徽标描述统一「浏览器工具栏的扩展图标状态色外框」(R4 框式), 来源徽标「优先」→「手动/自动」(R2)。S6: 新增 `scripts/gen_ext_icons.py`(PIL 生成 8 个 PNG: 基础无框 + 绿/橙/红框 × 16/32px, 色框外加暗色描边, 中性深色底不随主题变, 框色与 BADGE 同源), manifest `action.default_icon` 指向基础图, `background.js::refreshBadge` 改 `setIcon({path})` 换图 + 徽标文字折中(平时清空零遮挡, 仅「发现失败」态红 `!` + setBadgeBackgroundColor), `badgeStateOf` 判据不变, try/catch 静默降级保留。S5: `tests/test_extension_proxy.py` 新增 6 个守阵(rowHealthOf 四态真值表 / probe-all 消息真跑落台账 / 重测全部走后台反向断言 / 图例措辞 / 来源徽标两值 / 图标映射+文件在盘+manifest), `test_options_swiss_wiring` 元素清单随 S1 更新 + 旧字面量反向断言, `test_badge_reflects_connection_state` 随 R4 翻转(OK/.. 文案废止)。
> 档案: memory-bank/tasks/26-10-16-webui-hr-ext-connect-ui.md
> 基线时间: 2026-10-16 04:20

**Refs:** memory-bank/tasks/26-10-16-webui-hr-ext-connect-ui.md

## TOTAL

```
TOTAL                                               17334    182   5842    158    99%
3411 passed, 4 skipped in 127.29s (0:02:07)
```

- 语句 17334 / 未覆盖 182; 分支 5842 / partial 158; 覆盖率 **99%**(`commands run test.full` 实测, Windows 侧)。
- 与上一基线 `26-10-16-0400-hr-ext-connect-ui-s1s3`(3405 passed + 4 skipped)差 **+6 passed**: 本波新增 6 个守阵函数(rowHealthOf 真值表 / probe-all 真跑 / 重测全部反向断言 / 图例措辞 / 来源徽标 / 图标映射), 既有用例零回归。TOTAL 语句/分支与上轮**逐字相同**(改动全在 JS/PNG/MD 侧, 不进 Python 覆盖统计)。
- **红绿双验**(V5): 三类突变均判红后还原复绿 —— ① `rowHealthOf` 红判据(401/403 分支)致 `test_row_health_of_four_states` 红; ② `BADGE_ICON.ok` 映射改错致 `test_badge_icon_frame_mapping` 红(纯函数映射 + 文件在盘双钉); ③ 图例措辞回潮「工具栏图标徽标」致 `test_badge_legend_says_browser_toolbar` 红。
- 附带修复: options.js 一处残留旧按钮名用户可见串(`先点「自测端点连通」按提示排查` → 「重测全部」, S3 遗漏, S5 反向断言前置)。
- 教训(已记坑档待办): 变异测试用 `git checkout --` 回退文件时, 把**本轮未提交**的 background.js / options.js 改动一并冲掉(已用 Edit 精确重放并复测 42 绿) —— 未提交工作区禁用 `git checkout -- <file>` 回退变异。
- Linux(WSL) 侧未重测 —— 纯扩展 JS/PNG/MD 改动, 无平台分支。

## 本改动面

- `extensions/hr-fetch-proxy/README.md` —— §2 ①区布局块 / 徽标描述(R4 框式) / 排障表 / 「怎么确认它在工作」按新形态同步
- `extensions/hr-fetch-proxy/background.js` —— BADGE 文案 R4 折中(仅发现失败态非空 `!`); 新增 BADGE_ICON + badgeIconOf 纯函数; refreshBadge 改 setIcon 换图; 判据(badgeStateOf)与触发点不变
- `extensions/hr-fetch-proxy/manifest.json` —— action.default_icon 指向 icons/icon16.png + icon32.png
- `extensions/hr-fetch-proxy/icons/`(新, 入库) —— 8 个 PNG(icon16/32 基础 + icon-ok/-warn/-bad × 16/32), scripts/gen_ext_icons.py 一次生成, 幂等
- `scripts/gen_ext_icons.py`(新, dev-only) —— PIL 生成 8 图标, 框色与 BADGE 同源
- `extensions/hr-fetch-proxy/options.js` —— 残留旧按钮名串修复 + 两处注释口径(自测→重测全部)
- `tests/test_extension_proxy.py` —— 头部测试计划补本计划小节; 新增 6 守阵; swiss_wiring 元素清单更新 + 反向断言; badge 用例随 R4 翻转

## 验收待办(计划 §06, 真机)

- V1 实例表状态列(停用某实例后端 ≤1 轮变橙/红 + 悬停 note) / V2 重测全部 / V7 图标四态外框 —— 已备桩服务 `scripts/hr_ext_stub.py`(发现端点 18788 + 双数据端点, /control 可实时翻转 ok/401/down), 待用户在 Chrome 加载已解压扩展验收
- 模板选型(A/B/C)从未记录, 布局按计划 §03.1 纵向流基准(= 模板 A 形态)落地, 已在 S1–S3 档案注明
