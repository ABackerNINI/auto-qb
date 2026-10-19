# 26-10-19-webui-move-dialog-geometry — 设定位置弹窗几何修: 加宽 860 + 开层预留, 保存路径下拉完整落在对话框内

**Status:** Done
**Added:** 2026-10-19
**Updated:** 2026-10-19
**Summary:** 设定位置弹窗几何修: 宽度 560→860 + 开层预留 272px, 保存路径下拉完整落在对话框内、弹窗体零新增滚动; 静态 + e2e 双守阵(各做红验), 全量验证全绿(数字见基线切片)
**Topics:** webui-move-dialog-geometry
**Refs:** memory-bank/pitfalls/web-ui/combobox-focusout-close.md, memory-bank/testing/baselines/26-10-19-2207-webui-move-dialog-geometry.md

## 原始请求

「WEBUI设定位置弹窗太小, 新保存位置下拉显示不全, 需要滚动」—— 单条报障, 指向「设定位置…」
对话框(单种子右键/键盘、单组右键、多选批量右键三入口共用, 2026-10-13 建)。

## 思考过程与决策

- 复验先行(临时探针 spec, 真浏览器 1440x900, 桩 300 种子): 对话框实测仅 560x243; 点路径输入
  开下拉后, `.add-pop` 底缘超出对话框底沿 103px; `.add-dialog-body`(overflow-y:auto 滚动容器)
  scrollHeight 123→383(弹窗体内多出滚动条); elementFromPoint 逐项命中显示第 3 项起被
  `.modal-actions` 与遮罩盖住 = 真实不可点, 300 候选只露出约 2 项。
- 根因: 保存路径组合框是本表单**最后一项**, 而下拉朝下开(`.add-pop { top: calc(100% + 4px) }`)
  ⇒ 必伸到 body 底沿外; `_fitAddPop` 的净空算式量「输入行 → body 可见底沿」, 行贴底沿时净空
  为负, `avail > 0` 门恒不生效 ⇒ 前几轮修的限高兜底对这种形态完全无力。
- 决策(治法 = 给容器预留空间, 不是继续调限高值):
  ①宽度 `--modal-w-form`(560) → `--modal-w-add`(860, 与添加种子对话框同宽; 路径项 nowrap+ellipsis
    多显示, 且 860 档在 ≤900px 视口已有 `width:100%` 媒体查询兜底);
  ②模板根元素挂 `:class="{ 'pop-open': movePathMenu }"`, 三皮肤 CSS 成对加
    `.modal.move-dialog.pop-open .add-dialog-body { padding-bottom: 272px }`(面板头 ~46 + 列表 210
    + 顶距 4 + 余量 12)——预留后净空 ≈216px > 列表 210, 限高算式自然不再触发; 矮视口 modal
    自身滚动时 body 收缩、净空变小, 仍由限高兜底(不碰 `_fitAddPop` 逻辑本身)。
- 备选与否决: 下拉向上翻转(行上方只有 ~120px, 210px 列表放不下); 只加 max-height(治标不治本,
  净空为负时算式不生效); 把字段挪出末位(改表单结构, 范围外)。

## 实现计划

1. 模板 `move-dialog.html`: 根元素 `:class` pop-open 绑定 + 文件头注记几何修机理。
2. 三皮肤 CSS 成对(prism/console/atlas): 宽度 860 + `.pop-open` 开层预留 272px, 注释记推导。
3. 静态守阵 `test_frontend_move_dialog_combobox_wiring`: 增模板绑定 + 三皮肤几何规则断言。
4. e2e 新增 `move-dialog-fit.spec.mjs`(双皮肤 @fast): 自动开层态(开对话框即聚焦展开下拉)/
   Esc 收层态/再点重开态三轮 containment 断言; 量前等入场动画(modal-in scale .985 会压掉 4px)。
5. 验证: test.full + e2e fast + 全量 e2e; 两侧守阵各做一次红验(临时回退 CSS → 红 → 还原)。

## 子任务状态表

| 步 | 内容 | 状态 |
|---|---|---|
| 1 | 模板 pop-open 绑定 + 注记 | Done (2026-10-19) |
| 2 | 三皮肤 CSS: 860 宽档 + 272px 开层预留 | Done (2026-10-19) |
| 3 | 静态守阵几何断言 | Done (2026-10-19) |
| 4 | e2e 几何守阵 spec(双皮肤) | Done (2026-10-19) |
| 5 | 全量验证 + 红绿双验 + 坑档回写 | Done (2026-10-19) |

## 进度日志

### R0 · 立档 (2026-10-19)

用户报障「设定位置弹窗太小, 新保存位置下拉显示不全, 需要滚动」。临时几何探针复验(旧态: 下拉
超对话框底沿 103px、body scrollHeight 123→383、300 候选仅 ~2 项可点) → 定位根因(组合框是
表单最后一项, 净空算式 avail<0 恒不生效) → 落地「加宽 860 + 开层预留 272px」两路修(模板 +
三皮肤 CSS 成对) → 静态守阵与 e2e 几何守阵双双落地且各做红验 → test.full 与全量 e2e 全绿
(数字见基线切片) → 坑档 combobox-focusout-close 补第五轮条目(预留空间治法 + 量几何须等入场
动画两条教训)。修复后实测: 对话框 860x515, 下拉底缘落在对话框内(-79px), body/modal 零新增
滚动, 前 8 项(210px 列表全量)真实可点。

- 2026-10-19 22:10 设定位置弹窗几何修落地: 宽度 560→860 + 开层预留 272px, 保存路径下拉完整落在对话框内、弹窗体零新增滚动; 静态与 e2e 双守阵(各红验), test.full 与全量 e2e 全绿
