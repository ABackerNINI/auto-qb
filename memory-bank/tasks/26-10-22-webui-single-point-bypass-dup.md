# 26-10-22-webui-single-point-bypass-dup — 前端单点已存在但被绕过 7 族收敛(cfgBool/hubKey/directionKey/Bearer/KiB/单位梯/hrGroupTitle)

**Status:** Done
**Added:** 2026-10-22
**Updated:** 2026-10-22
**Summary:** 前端 7 族单点绕过全部收敛: 提 cfgTruthy/aqbAuthHeaders/kibToBytes/bytesToKib/AQB_UNIT_LADDER/hrEpTitle 六个新单点, 合并 cfgPathKey 第二份 path→key 单点, 11 处内联改调且单点处补禁内联注释; 全量与 e2e 双绿(数字见基线切片)
**Topics:** webui-single-point-bypass-dup
**Refs:** memory-bank/issues/26-10-20-2231-refactor-fe-single-point-bypass-dup.html, memory-bank/testing/baselines/26-10-22-0324-webui-single-point-bypass-dup.md

## 原始请求

1. 「认领并修复 memory-bank/issues/26-10-20-2231-refactor-fe-single-point-bypass-dup.html」—— 用户显式指派(认领合法, 非 agent 自行认领)。

## 思考过程与决策

1. **复验先行**(防过期原则 5): 7 族锚点全部仍复现(grep 2026-10-22 02:45), 行号有漂移(如 cfgBool 单点 359→354), 按符号名重新定位, 不影响定性。
2. **单点形态按消费方约束选**: Bearer 族取**顶层函数** `aqbAuthHeaders`(auth.js)而非 mixin 方法 —— `shortcuts.js` 的 `AQB_KEYS_ADAPTER` 不是 Vue mixin 单例、拿不到 `this`(与 `aqbFetch` 先例同款裸调形态); 且 node 探针 `_NODE_API_TIMEOUT_PROBE` 只 eval `auth.js` 单文件并用合成实例调 `_request`, 同文件顶层函数是唯一不破探针的形态。
3. **加载序约束**: `config_editor.js` 在 `format.js` **之前**加载 ⇒ 单位梯数据表(`AQB_UNIT_LADDER`)放 format.js, 曲线图侧经 `this._fmtLadder` 方法跨文件消费(方法体运行时才求值, 顺序无关; 与 hr.js 经 `this.fmtDuration` 调 format.js 同范式)。
4. **单位梯精度分歧保留**: 审计明言"表格 toFixed(2)+原样兜底+梯顶 PiB / 曲线图 toFixed(1)+取整兜底+梯顶 TiB 是**当前设计**" ⇒ 收敛为数据单点 + 参数化(digits/roundFallback/top), 不统一行为; 阶梯值核对两梯均纯 1024 进制, KB/1000 制仅存于 `_sizeMultiplier`(曲线阈值解析, 刻意双支持) ⇒ issue 担心的"KiB vs KB 口径差写坏配置"不存在。
5. **hrEpTitle 保留 ep 行短文案**: 与 `hrGroupTitle` 长文案的措辞分歧是现存用户可见行为, 机械收敛不改文案(统一属另一决策); 若后续要统一, 把 `hrEpTitle` 改成转调 `hrGroupTitle` 即可, 注释已写明。
6. **连带发现(超出 issue 清单)**: `config_editor.js::cfgPathKey` 与 `hubKey` 是同一事实的**第二份单点**(逐字同构) —— 比内联更隐蔽(看着像合法单点), 按审计 R20-C-18 建议的"提共享 pathKey"思路合并: `cfgPathKey` 转调 `hubKey`。
7. **模板侧单位梯复验为已收敛**: hub-field 的 `unitOptions/unitLabel` computed 已转发 `cfgUnitOptions/cfgUnitLabel`(前轮修复), 本轮仅在 `cfgUnitOptions` 补"禁止另抄阶梯"注释, 不改代码。

## 实现计划

总体思路 = 逐族"提单点(或确认既有单点) → 调用侧改调 → 单点处加禁内联注释", 每族独立可验:

1. cfgBool 族: `cfgTruthy(v)` 纯函数(config_editor.js, cfgBool 转调) + 3 处内联改调(config_rules/config_hub×2)。
2. hubKey 族: config_rules 两处内联 join 改调 hubKey; cfgPathKey 转调 hubKey(第二份单点合并)。
3. directionKey 族: cfgCurvePointAdd 内联三元改调 cfgCurveDirectionKey。
4. Bearer 族: auth.js 顶层 `aqbAuthHeaders(token)` + 4 处改调(auth/shortcuts×2/commands)。
5. KiB 族: format.js `kibToBytes`/`bytesToKib` + fmtLimit 与 drawer.js 三处改调。
6. 单位梯族: format.js `AQB_UNIT_LADDER` + `_fmtLadder` 参数化单点, fmtSpeed/fmtSize 与 config_editor 曲线图两函数改调。
7. hrGroupTitle 族: hr.js `hrEpTitle(e)` + xtpl-cells.html ep 行改调。
8. 验证: node --check 全文件 → test.full → dev.e2e 三规格 → 内联回归 grep。

## 子任务状态表

| 步 | 内容 | 状态 |
|---|---|---|
| 1 | cfgBool 族收敛(cfgTruthy 单点 + 3 处改调) | Done (2026-10-22) |
| 2 | hubKey/directionKey 族收敛(3 处内联 + cfgPathKey 合并) | Done (2026-10-22) |
| 3 | Bearer 族收敛(aqbAuthHeaders 顶层单点 + 4 处改调) | Done (2026-10-22) |
| 4 | KiB↔bytes 族收敛(kibToBytes/bytesToKib + 4 处改调) | Done (2026-10-22) |
| 5 | 单位梯族收敛(AQB_UNIT_LADDER + _fmtLadder + 2 处改调; 模板侧已收敛仅补注释) | Done (2026-10-22) |
| 6 | hrGroupTitle 族收敛(hrEpTitle + ep 行模板改调) | Done (2026-10-22) |
| 7 | 验证: test.full 全量 + e2e 三规格(views/multiselect-shows/hr-history) + node --check + 内联回归 grep, 双绿(数字见基线切片) | Done (2026-10-22) |

## 进度日志

### R0 · 立档 (2026-10-22)

7 族全部改调既有单点并在单点处补「禁止内联重写」注释(收敛 issue 编号 + 台账号); 连带合并 cfgPathKey 第二份单点; 单位梯收敛为数据单点 + 参数化格式化(保留表格/图轴设计分歧); 改动 10 个源文件(auth/commands/config_editor/config_hub/config_rules/drawer/format/hr/shortcuts + xtpl-cells.html)。验证: test.full 全绿(数字见基线切片), e2e views/multiselect-shows/hr-history 三规格全绿(三皮肤), node --check 全过, 7 族惯用式回归 grep 仅剩单点自身定义处。issue 置 Done; 契约回写 webui-static-contract.md。
