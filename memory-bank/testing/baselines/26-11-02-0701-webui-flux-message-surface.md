# 4823 —— flux 消息面文字排版(标题+明细两行)后全量

> 摘要: flux 消息面文字排版(标题+明细两行)后全量
> 基线时间: 2026-11-02 07:01
**Refs:** memory-bank/testing/baselines/26-11-02-0645-webui-flux-message-surface.md

## 验收数字

`commands run test.full` 实测(2026-11-02 06:59, 四轮: 文字排版改 D6-2 骨架):

```text
TOTAL                                                22521    152   7726    135    99%
4823 passed, 10 skipped in 230.37s (0:03:50)
```

- 口径注记: 10 skipped 为既有跳过面(平台条件跳过, 与本轮改动无关); 覆盖率 99%。
- 守阵 `tests/test_webui_static_skins.py` 26 passed: 第 20 项追加「文字排版」三组断言
  (`.toast` 基座 `align-items: flex-start` + `font-weight: 600`; `.toast-txt` 的 `min-width: 0`;
  `.toast-s` 的 12px / `--fg-muted` / 400; **以及 fx-mount.js 的 toastSync 必须调
  `shapeToastText(n)`** —— 拆段器缺席时 CSS 守阵看不出"退回单行"), 用例数不变。
  红验四形态各精确报红、还原后绿: 摘 `.toast-s` 规则 / 基座字重回 400 / 图标回 `center` /
  抹掉 `shapeToastText(n);` 调用。
- 渲染面人工取证(桩服务 + Playwright, flux 不在 e2e `SKINS` 默认集合): 六条提示条实测 --
  拆开条(`添加种子失败` / `跳检失败`)为 13px/600 标题 + 12px/`rgb(163,179,201)` 明细两行、
  高 59px; 单行条(短回执 / 无常量分隔的长句)保持一行、600 字重; 图标 `align-items: flex-start`、
  `margin-top: 1px` 顶对齐; 控制台零错误。挑选台 D9 六张卡样例同排版。

## 本改动面

- `flux/css/components.css`(维持 700 行, 未越 cap): `.toast` 基座 —— `align-items: center` →
  `flex-start`(图标顶对齐)、新增 `font-weight: 600`(标题行字重)、`max-width: 380px` →
  `width: 340px` + `max-width: calc(100vw - 40px)`、`padding: 11px 15px` → `10px 12px`、
  补 `position: relative` + `overflow: hidden`(倒计时 `::after` 与方角裁剪就位)。
- `flux/css/views.css`(484 → 498 行): 新增「消息面文字区」段 —— `.toast-txt`(`flex: 1;
  min-width: 0; overflow-wrap: anywhere`)、`.toast-t`、`.toast-s`(12px / `--fg-muted` / 400)。
  落 views.css 而非 components.css: 后者卡 700 行体量上限。
- `flux/fx-mount.js`: 新增 `shapeToastText(n)` + 正则 `TOAST_SPLIT`, 在 `toastSync` 的节点循环里
  每次调用(按 `.toast-t` 是否存在判重: Vue 在 `.text` 变更时会 `hostSetElementText` 覆写 span
  子节点, 标记位会骗人)。纯结构拆段: 首个 `:`/`：` 前的动作短语(≤14 字、不含括号) → 标题,
  其后 ≥6 字 → 明细; 不满足即单行。文本一律 `textContent`(err.message 可含任意字符)。
- `fx/showcase.html`: D9 六张卡的 `.mst` 基座同步生产排版(顶对齐 / 10px 12px / 600 13px、
  `width: 340px` + `max-width: 100%`)、新增 `.mst-txt/.mst-t/.mst-s`; 样例三行改为
  「已强制汇报 3 个种子」/「部分目标已受理, 2 个推迟到最小间隔后重报」/
  「添加种子失败 + The torrent file is already in the list」(最后一行即拆段形态);
  区注补「文字排版已定」。D6-2 参考卡本体零改动。
- `tests/test_webui_static_skins.py`: `_scan_message_surface_parity` 增加 `typo` 收集 + 三组
  排版断言 + 拆段器(JS)断言, docstring 增第 ⑥ 条。
- `memory-bank/conventions/webui.md`: 新增「消息面文字排版: 标题行 + 明细行」段(参考物 / 三段落点 /
  拆段规则与判重理由 / 单行是短回执的正常形态)。
- 共享模板(`tpl/overlays.html`)、sprite、另三皮肤零改动 —— 模板仍是一条 `<span>{{ t.text }}</span>`,
  拆段全部在 flux 挂载层完成(范围守恒)。
