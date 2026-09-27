# 26-09-27-2138-webui-curve-chart — WEBUI 限速曲线预览图重构

> 摘要: 限速曲线预览图三修: ①X 轴从「每档等宽」(SPD-02)改为**按各档实际流量长度比例**, 末档与后端语义一致(curves.py: 末档速度从其下限起延续到 ∞, 末档阈值不改变速度函数)显示为 ∞ 区且**占宽 ≤30%**(单档独占全宽), 末档阈值不再入几何; ②悬停换算按 SVG 实际渲染缩放(letterbox 安全), tooltip 用真实像素定位; ③删共享 console_hub.css 残留 `.hb-chart svg{height:128px}`(特异性压过主题 aspect-ratio 把图压扁 = 「宽度不对」根因)。流程: 独立模板 5 用例实测 → 应用 6 文件 → 真实 JS+Vue 集成冒烟 → test.full 零回归。档案: tasks/26-09-27-webui-curve-chart.md。
> 最后活动: 2026-09-28 (二轮: 上传/下载配色区分 + 曲线默认折叠)

## 已完成

- 模板 `resources/curve-chart-template.html`: 5 用例(均匀/末档巨大/单档/六档悬殊/含0档)+ 可编辑档位表 + 测量条 + 宽度滑杆 + 旧版对照开关; 浏览器实测全部验收点通过(比例 35/35/30、悬停 50GiB→第1档与 ∞ 区翻转、标签避让、420–1200px)。
- 22:05 按用户反馈撤除 ∞ 水印(模板/冒烟页/真实代码/三主题 CSS 全清, infMark 字段删除); ∞ 语义仍由 X 轴刻度 + 图例表达, 复验与 test.quick 全绿。
- 应用: `config_editor.js`(_buildCurveChart 比例几何 + ∞ 封顶 + 标签避让; cfgChartHover 缩放安全换算 + 像素级 tooltip; note 改「纵轴上限」)、`settings-detail.html`(图例「按各档实际长度, 末档 ∞」)、三主题 components/views css(atlas 顺手并 `.ce-chart-tick` 单行保住 700 行守阵)、`shared/console_hub.css`(删压扁规则)。
- 集成冒烟 `resources/curve-chart-smoke.html`: 真实 config_editor.js + vendor Vue 渲染/悬停全对; 压扁容器探针点(viewBox x=120)新代码答「第2档/37.8GiB/12MiB/s」, 旧算法同点会答错档。
- test.quick / test.full: 1752 passed + 3 skipped / 91%(11730/849/3940/351), 与基线 26-09-27-2022 持平零回归(首跑 851 为并行统计抖动, 复跑稳定)。
- 收尾: 基线切片 + 本切片 + 档案立档 + 新坑 `pitfalls/web-ui/svg-chart-mapping.md` + kb.index。
- **2026-09-28 二轮(用户要求: 上传/下载颜色区分 + 每条曲线默认折叠)**: ①`config_editor.js` 加 `openCurves` 状态(缺省=折叠, 沿用 openSections 口径) + `cfgCurveOpen/cfgCurveToggle`, 新增曲线自动展开、删除中间条时展开态随序号前移搬移; ②`settings-detail.html` 曲线头部加「展开/收起」钮(复用日志块文案), `hb-curve-bd` 挂 v-if, 图表容器加 `ce-chart-up/down` 方向类 + 图例方向色标 + 方向组标题色条; ③配色上传 `--warn` / 下载 `--blue`(三主题族都有这对变量): console/prism 直接进 components/views.css, **atlas 因 components.css 700 行守阵贴顶放进 views.css**(加载序在后覆盖语义不变, components.css 还原零 diff)。test.quick 1818 passed + 3 skipped 零回归(守阵测试单独复跑 passed); test.full 基线切片 26-09-28-0401(91% / 12512 语句 / views.py 98%)。

## 正在进行

- 无(等待用户真机查看: 曲线默认折叠 + 双色预览; 未提交)。

## 下一步

- 用户验收后说「提交」走 my-commit-flow。
- 真机设置页(限速曲线分区)肉眼走查一遍: 双色对比 + 折叠态观感(冒烟页未覆盖本轮改动)。
