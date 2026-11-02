# Tasks: flux 浮动层不透明兜底

- [x] T1 令牌: flux/style.css 增 `--bg-pop: #1c2a3f`; atlas/console style.css、prism/css/tokens.css 增 `--bg-pop: var(--bg-elev)`（惰性补名）。
- [x] T2 flux components.css: `.col-menu/.pop-menu`、`.ctx-menu`、`.ctx-sub`、`.ce-chart-tip` 底 token 换 `--bg-pop`。
- [x] T3 flux dialogs.css: `.speed-pop`、`.hr-pop`、`.hp-arrow`、`.hr-full-modal`、`.add-drop-box` 底 token 换 `--bg-pop`（保留渐变/切角/描边）。
- [x] T4 flux views.css: `.hist-tip`、`.col-ghost` 底 token 换 `--bg-pop`。
- [x] T5 flux dialogs.css 末尾新增 flux 作用域覆盖块: `html[data-fx-preset] .hb-pop`（`background-color` 保留渐变）、`.hb-pop-arrow`、`.hb-tr-drop`、`.search-help-pop`、`.aq-tip`、`.err-panel`、`.rowlang-menu` → `--bg-pop`。
- [x] T6 收口 grep: flux 内 `position: fixed|absolute` + 半透明底色未挂 blur 的残留；核查 `.login-mask`; 有新遗漏按同规则纳入并记入核对清单。
- [x] T7 验证 `commands run test.quick`: blur 预算=4、CSS ≤700 行、令牌名集相等; 记录实测结果。
- [x] T8 输出中文报告: 根因 / 修改清单(文件+选择器) / 核对清单 / 验证与限制; 贴 `已同步 8867f75e`。

## 验收
- flux 下所有列出的浮动层不再透出正文; 其它三皮肤视觉零变化; 无新增 backdrop-filter; 未提交未推送。
