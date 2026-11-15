# 6266 passed, 2 skipped —— 状态栏速度组定宽 26-11-16-0130 S4: 全量基线

> 摘要: 状态栏速度组定宽 26-11-16-0130 S4: 全量基线
> 基线时间: 2026-11-16 02:36

## 验收数字

`commands run test.full` 实测(2026-11-16 02:36, Windows 开发机; 复跑轮):

```text
TOTAL                                                27855     73   9822     78    99%
6266 passed, 2 skipped in 164.70s (0:02:44)
```

- 汇总: 6266 passed / 2 skipped, 覆盖率 99%(实测表尾 99%, 汇总行 99.59%)。
- 首轮曾 1 红(`tests/test_checking_skip.py::test_checking_skip_backup_precedes_delete_and_cleared_on_success`, 与本改动面无交集); 单跑与整文件复跑均绿、全量复跑绿未复现 —— 一次性假红候选, 未复现不入台账, 留档于此备查。
- 配套面: `commands run test.quick` 6266 passed / 2 skipped(56.71s); `commands run test.one -- tests/test_flaky_timing_guards.py` 11 passed; `commands run dev.e2e -- e2e/statusbar-speed-geometry.spec.mjs` 四皮肤 4 passed(56.5s)+ 摘 CSS 红验 1 failed(变异自证)+ 还原复跑 1 passed; `commands run dev.e2e -- e2e/statusbar-kbd-entry.spec.mjs e2e/views.spec.mjs` 40 passed(1.5m, R7 既有断言零松动)。
- 缺口净额(M8): 本片 151 单位(miss 73 + partial 78) 减上片 26-11-15-1546 的 152 单位(miss 73 + partial 79) = -1; 分母与上片持平(27855 / 9822)。负 1 来自守阵文件自身行数变化带来的行归属漂移, 无新进榜模块。

## 本改动面

- `src/auto_qb/webui/static/shared/console_hub_panels.css`(S1): 尾段新增状态栏速度组定宽三行 —— `.sb-speed .sb-spd .val { min-width: 13ch; text-align: right; }` / `.sb-speed .sb-spd .lim { min-width: 13ch; text-align: left; }` / `@media (max-width: 900px)` 内 `.lim { min-width: 4ch; }`(含 15 行动机注释)。
- `tests/webui_static_scan_css.py`(S2): 新增 `_css_rules_layered`(按 @media 花括号深度分层拆规则)与 `_scan_statusbar_speed_width`(shared 层 13ch/4ch 分层钉值 + 四皮肤 `.sb-spd ... .val/.lim` 零 min-width 覆盖 + 基础 `.sb-err` flex: 0 0 auto 钉)及子串匹配助手 `_sb_spd_target`。
- `tests/webui_static_scan_js.py`(S2 接线): 导入 + `_scan_frontend_assets` 调用 + docstring 第 24 项。
- `tests/test_webui_static_skins_skin.py`(S2 接线): 导入面补 `_scan_statusbar_speed_width`。
- `e2e/statusbar-speed-geometry.spec.mjs`(S3 新增): 四皮肤 @fast, 页内步序注入(速度四档/限速三态/徽标两位数)+ rAF/4ms 双路逐帧采样, 宽视口组内元素左右缘 <=1px + 窄视口只保 .sb-speed 右缘 + 覆盖性自证。
- 红绿双验: S2 五变异(12ch/皮肤等特异性/皮肤高特异性/摘 .sb-err flex/删 @media 4ch)全红 + sha256 还原复核; S3 摘 CSS 全宽断言红。
