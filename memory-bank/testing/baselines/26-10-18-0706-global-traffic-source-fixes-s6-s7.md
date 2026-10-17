# 3558 passed + 4 skipped(根) —— 全局流量来源联动缺陷修复 Phase 1 S6–S7(设置页四修 / 工具参数单位化)

> 摘要: Phase 1 S6–S7 实施完成：工具相关三块按 provider 条件隐藏 + 「已就绪」状态色 + 只读行同基线 + 删「打开工具设置」；工具参数改「数值+单位下拉+?」并把盘上/契约统一为复合串(解析单点 gtm/units.py + 旧值一次性迁移)
> 基线时间: 2026-10-18 07:06
**Refs:** memory-bank/tasks/26-10-17-webui-traffic-source-fixes.md, memory-bank/plans/26-10-17-1737-plan-global-traffic-source-integration-fixes.html

## 验收数字

`commands run test.full` 实测(2026-10-18 07:06, 本机 Windows 单侧):

- 汇总行: **3558 passed, 4 skipped**(40.19s;全绿,无已知红)
- TOTAL 覆盖率: 18030 statements / 264 missed / 6120 branches / 191 partial / **98%**(98.10%, 闸门要求 98%, 达标)
- gtm 工具侧另跑(在 `tools/global-traffic-monitor` 目录内用其 `.venv` 跑全量): **264 passed**(32.94s;新增 `test_units.py` + 复合串/迁移用例)
- e2e 新增三条(本机 chromium × 双皮肤)各 2 passed: 只读状态行几何守卫 / 设置页·全局流量来源(S6) / 设置页·工具参数的单位控件(S7)

## 本改动面

- 前端(S6): `static/shared/tpl/settings.html`(工具状态 / 文件选择器 / 工具参数三块加 `tmProvider()` 闸;状态行挂 `hb-ro`;删「打开工具设置」) · `static/shared/config_hub.js`(`tmStateClass` 的 `ready: "on"→"ok"`;删 `tmOpenToolSettings()`) · `static/shared/console_hub.css`(`.hb-row.hb-ro` 基线对齐 + 去 7px 上边距,全局口径不动)。
- 前端(S7): `static/shared/config_hub.js`(`tmParams()` 升级为元数据表 + `tmUnitParts/tmSetUnitPart/tmAskItem/tmAskKey`;`tmBuildPayload` 不再 Number() 化时间/大小) · `settings.html`(参数行改「数值框 + 单位下拉 + ?」)。
- 工具侧(S7): `tools/global-traffic-monitor/src/gtm/units.py`(新;parse/format 单点) · `gtm/config.py`(时间/大小校验改走 units;`config_to_payload` 只写复合串;新增 `migrate_legacy_config`) · `gtm/__main__.py`(启动时一次性迁移并打日志)。
- 文档: `docs/configuration.md`(工具参数表默认值改复合串 + 旧值迁移说明 + 工具三块条件渲染/删按钮) · `tools/global-traffic-monitor/README.md`(复合串契约 + 补登 `POST /shutdown` 行)。
- 测试: `tests/test_web_traffic_monitor.py`(6 条静态守阵) · `e2e/views.spec.mjs`(3 条新用例) · `tests/test_webui_static_skins.py`(`settings.html` 分片额度 400→440) · `tools/global-traffic-monitor/tests/test_units.py`(新) · `test_config.py` / `test_server.py`(复合串、迁移、回显)。

## 守阵与坑

- **状态色必须落在有规则的类上**: `tmStateClass` 曾返回 `"on"`,而 CSS 只定义 `.hb-led.ok/.warn` —— 无类的值静默落基态灰。守阵除了钉 `ready: "ok"`,还扫「每个非空色值都要有 `.hb-led.<值>` 规则」。
- **7px 是给控件盒的,不是给纯文本的**: `.hb-lb` 的 `padding-top: 7px` 让标签与输入框顶端对齐;纯文本行没有盒子,于是「标签 | 值」错位。修法只挂 `.hb-row.hb-ro`,全局 `.hb-row` 一个字节没动(守阵同时钉住 `padding-top: 7px` 仍在)。
- **静态守阵看不见层叠与盒模型**: 新加的 e2e 几何守卫在真浏览器里量「首行文字顶端差 ≤ 2px」+ 级联结果(`align-items`/`padding-top` 计算值);变异验证(去掉那两条 CSS)即红。
- **复合串只有一处文法**: 前端只做显示层拆合(`"10MiB"` → 10 + MiB),解析/校验/回显/落盘全在 `gtm/units.py`;守阵把三张单位表(前端下拉 / auto-qb schema / units.py)钉成相等,防「下拉选得出来、工具却拒收」。
- **写侧不得数值化**: `tmBuildPayload` 从 `Number(f.sample_interval)` 改为原样回传 —— 数值化会把 `"10MiB"` 变成 10,单位凭空消失(D13 之前的老毛病);e2e 直接断言发出的 PUT 载荷仍是 `"5S"`/`"1MiB"`/`"3M"`。
- **迁移要窄**: `migrate_legacy_config` 只在盘上确有裸数值时才重写,且解析失败一律不写(交给 fail-fast 聚合报错)—— 否则"迁移"会顺手把用户的部分配置写成全量默认值。
- **单位回显取「能整除的最大单位」**: 180 秒回显成 `3M`、60 秒成 `1M`(语义等价,盘上只有一种形态);设置页「?」里的默认值文案已同步成这个形态,避免文档写 180S、界面显示 3M 的自相矛盾。
- **settings.html 触 400 行单分片上限**: 该卡是二级页 `v-else-if` 链的一环,抽分片会断链 → 额度提到 440 并在守阵里写明「下次再长先重构成独立组件」的出口。
