# 3971 passed + 10 skipped —— 三皮肤 CSS 分层归位: atlas 补字体令牌 + prism 新建 dialogs.css 后全量基线

> 摘要: 三皮肤 CSS 分层归位: atlas 补字体令牌 + prism 新建 dialogs.css 后全量基线
> 基线时间: 2026-10-21 05:35
**Refs:** memory-bank/issues/26-10-20-2231-refactor-fe-css-skin-token-layer-dup.html

## 验收数字

```text
TOTAL                                                20471      91   7012      93    99%
3971 passed, 10 skipped in 34.94s
```

口径注记:

- 上表是 pytest 全量口径(含覆盖率门槛); 相对上基线的逐位对比不写 —— 看差值 `commands run kb.baseline -n 2`。
- 真浏览器侧同轮跑过 `npm run test:e2e:fast`: 206 passed(双皮肤抽屉/弹窗/表头/菜单几何断言), 桩服务由 Playwright webServer 自起自收。
- 纯 CSS 改动 pytest-cov 不计入, 故 TOTAL 与上一条基线持平属预期。
- 裸数字只写基线切片这一处; 档案与报告正文引它而不抄(守卫 `check_wording.py` 判据族 B)。

## 本改动面

- `src/auto_qb/webui/static/atlas/style.css`: `:root` 开头补 `--font-ui` / `--font-display` / `--font-mono` 三个字体令牌(名集 86 → 89, 与 console/prism 相等); `html,body` 的字体改走 `var(--font-ui)`。副作用是修掉 atlas 自己 4 处 `var(--font-mono)` 裸引用的静默失效(状态栏速度读数 `.sb-spd .val/.lim`、`.kv b`、`.hg-end` 现在真成等宽 —— 真浏览器逐像素确认改动只落在这几处数值文本)。
- `src/auto_qb/webui/static/prism/css/dialogs.css`(**新建**, 603 行): 棱镜弹窗层 —— 确认框 / HR 全屏覆盖层 / 路径选择器 / 添加种子对话框 / DND + D4 预览 / 种子编辑 / HR 表②/ 统计·分类标签·设定位置·重命名对话框 / 抽屉网格行(自 components 迁入 313 行) + 抽屉壳与合并双列 / drawer-table / HR 表①③ / HR 站点状态 / 限速弹窗 / HR 悬停弹窗(自 views 迁入 264 行)。块序 = 原全局序, 纯字节搬运。
- `prism/css/components.css`(699 → 381 行) / `prism/css/views.css`(1085 → 818 行): 只减不增(搬走的段); views.css 因此进入守阵的"存量冻结"(只许减不许增)。
- `prism/index.html`: 新增 `/prism/css/dialogs.css` link(排在 views.css 之后、`shared/` 之前), shell 行数 cap 212 → 214。
- `tests/test_webui_static_skins.py`: 链接序守阵扩到 prism(tokens → 五主题 → base → components → views → dialogs) + 行数口径(prism 各文件 700 行, views.css 存量冻结 818) + 新增 `test_frontend_skin_css_token_parity`(三皮肤令牌名集相等)。
- `tests/test_web_shortcuts.py`(4 处) / `tests/test_web_backend_misc.py` / `tests/test_webui_static_dom_page.py` / `tests/test_webui_static_dom_panel.py`: 单文件路径硬编码改聚合或新路径; `.drawer-leave-active` 的 "inset: 0" 判据由"文件前段"改为"逐条抽该规则声明体"。
- 回写件: `memory-bank/conventions/webui.md`(令牌名集三皮肤相等 + 三皮肤 CSS 分层同构两条口径) / `memory-bank/pitfalls/web-ui/webui-css-block-move.md`(新建) / `memory-bank/pitfalls/web-ui/css-file-line-cap.md`(prism 已进检查面) / issue `26-10-20-2231-refactor-fe-css-skin-token-layer-dup.html`(置 Done + 实际修法) / 本切片。
- 等价性验证(结构改动的门禁口径, 见本次新建的坑档): ①静态 (媒体, 选择器, 属性) → 赢家值 表搬前/搬后逐项相等(3526 条, 0 处改变) + 11 处特异性平手交叉对逐条人判为互斥子树; ②真浏览器 5 态像素基线 prism 5/5 全 0 差异(改前先跑两遍验证基线可复现)。
