# 3747 passed + 10 skipped(根, 覆盖率 98%) —— 设定位置弹窗几何修(加宽860+开层预留)后全量基线

> 摘要: 设定位置弹窗几何修(加宽860+开层预留)后全量基线
> 基线时间: 2026-10-19 22:07
**Refs:** memory-bank/tasks/26-10-19-webui-move-dialog-geometry.md

## 验收数字

`commands run test.full`(2026-10-19 21:47 实测, 31.5s):

```
3747 passed, 10 skipped in 30.15s
TOTAL    20256    394   6914    261    98%
```

口径: 根套件(pytest.ini 的 8 worker); `TOTAL` 列序 = 语句数 / 未覆盖 / 分支数 / 部分分支 / 覆盖率。
10 skipped 全为环境性(与本轮改动无关): 6× `test_alias_fs.py` + 2× `test_file_access.py`
符号链接权限(Windows 非特权缺 SeCreateSymbolicLinkPrivilege), 1× `test_grouping.py`
normcase 大小写折叠, 1× `test_web_hr.py` 仅大小写敏感 FS 成立的断言 —— 与上一条基线
(26-10-19-2005)同为 10 skip、总数一致(本轮纯前端改动, 采集数不变)。

前端门禁(本轮改前端, e2e 两侧都跑):

- `npm run test:e2e:fast`(@fast 子集, 2026-10-19 21:52 实测): **182 passed**(6.2m) —— 含本轮新增
  `e2e/move-dialog-fit.spec.mjs` 双皮肤两条。
- `commands run dev.e2e`(全量真浏览器, 2026-10-19 22:05 实测): **298 passed / 10 skipped**(9.8m) ——
  10 skipped 为 W5-off / hang 模式门控组(默认 ok/on 轮按设计跳过); 新增几何守阵两条在
  第 215/216 号位全绿。

守阵灵敏度红验(临时回退任一皮肤 CSS, 两侧均红后还原): e2e 几何 spec 在「宽度断言」与
「body 无滚动断言」两处判红; 静态守阵 `test_frontend_move_dialog_combobox_wiring` 在
宽度正则处判红。

## 本改动面

- `webui/static/shared/tpl/move-dialog.html`: 根元素挂 `:class="{ 'pop-open': movePathMenu }"`
  (下拉开层时对话框给 body 预留空间); 文件头注记 2026-10-19 几何修机理。
- `webui/static/{prism/css/components.css, console/css/dialogs.css, atlas/css/dialogs.css}`(三皮肤成对):
  `.modal.move-dialog` 宽度 `--modal-w-form`(560) → `--modal-w-add`(860, 与添加种子同宽);
  新增 `.modal.move-dialog.pop-open .add-dialog-body { padding-bottom: 272px }` 开层预留
  (面板头 ~46 + 列表 210 + 顶距 4 + 余量 12)。
- `tests/test_webui_static_dom_panel.py::test_frontend_move_dialog_combobox_wiring`: 增几何断言
  (模板 pop-open 绑定 + 三皮肤成对的 860 宽档与 272px 预留规则); docstring 同步。
- `e2e/move-dialog-fit.spec.mjs`(新增, 双皮肤 @fast): 自动开层态/Esc 收层态/再点重开态三轮
   containment 几何断言(下拉底缘不超 body 客户区、弹窗体零新增滚动、列表未限高截断、前 6 项
   elementFromPoint 命中); 量前 `getAnimations({subtree:true})` 等入场动画(modal-in scale .985
   会把宽度压掉 4px)。
- `memory-bank/pitfalls/web-ui/combobox-focusout-close.md`: 补第五轮条目(组合框是表单最后一项时
   净空为负、限高算式恒不生效 → 预留空间治法)+ 摘要/触发词; 索引由 kb.index 重建。
- 未动: `_fitAddPop` 限高逻辑本身(预留后净空 > 列表高, 算式自然不再触发; 矮视口仍由它兜底)。
