# web-ui — 前端 / WEB UI 纪律

> **本文件是生成物, 不要手改** —— 由 `commands run kb.index` 扫描本目录主题文件的三行头元数据生成; 新增 / 改名 / 改摘要后重跑即可, 冲突也只需重跑。
> 库内细路由见 [memory-bank/README.md](../../README.md)。
> **检索纪律**: 先读本索引定位, 再按需打开单个主题文件 —— **不要整读本目录**。
> **摘要**: 前端改动的一整套判据 —— Vue 语义静默白屏、版式口径、列状态双轨模型、前后端数据契约、视图裁剪与刷新节奏。
> **触发**: 前端, WEB UI, 模板, CSS, 列设置, 视图, 轮询, 真值, 乐观 UI, 冒烟

## 主题

| 主题 | 一句话 | 触发词 |
|---|---|---|
| [columns-persist.md](columns-persist.md) | 列偏好"时不时被重置"的全部已知机制 —— 双轨模型是当前定案, 前四轮修复都栽在把意图与派生混在一个字段里。 | 改列设置, 列宽被重置, localStorage, 列隐藏, 列序, 拖列宽, colHidden, colOrder, colWidths |
| [contract-api.md](contract-api.md) | 前端不只是后端的镜像 —— 判"字段不一致"前必须沿派生链追到消费点; 跨视图裁剪与真值时序是两条反复出事的线。 | 字段不一致, 前后端契约, 视图回传, rid, 真值, 乐观 UI, 状态色, 占位符, HR 标签 |
| [css-perf-parity.md](css-perf-parity.md) | 「星图卡、棱镜不卡」这类单边性能问题的定位路径 —— 差异只在 CSS(JS 是共享层), 且两套 CSS 里唯一有实质差异的昂贵属性是 backdrop-filter; 嵌套毛玻璃的成本与摘法。 | 卡顿, 掉帧, 不跟手, 两套 UI 性能差, 一边卡一边不卡, 毛玻璃, backdrop-filter, 弹层卡, 改 CSS 后变慢, 星图卡 |
| [layout-css.md](layout-css.md) | 行宽口径、表头吸顶、sticky 层叠、flex 挤压、特异性之争 —— 前端版式类的固定判据。 | 改 CSS, 布局, 表格, 滚动条, 表头吸顶, sticky, flex, 省略号, 媒体查询, 颜色不对, 按钮, UA 默认色 |
| [overlays.md](overlays.md) | 弹层 / 浮层 / 遮罩 / 多选与命令回执 —— "点了没反应"这类症状的固定排查顺序。 | 浮层, 弹层, 右键菜单, 遮罩, 点了没反应, 多选, 命令回执, 强制汇报 |
| [perf-cadence.md](perf-cadence.md) | 主循环节拍、缓存边界、埋点与相对时间 —— 改热路径 / 改节拍 / 加埋点前必读。 | 性能, 热路径, jsonable_encoder, 节拍, 刷新, 轮询, 缓存, 埋点, 相对时间, 时间列, yapf |
| [search-views.md](search-views.md) | 搜索不是虚拟分组、脏标记是共享状态、鉴权判据不能靠"凭证串非空"、配置写盘要按 BaseLoader 语义比较。 | 改搜索, 改视图脏标记, 改鉴权, 改登录, 改设置页, 改配置写盘, rid 门控 |
| [template-render.md](template-render.md) | 模板与 CSS 的静默失效(挂件类名错配、规则被吞、变体被覆盖)与"两套 UI 必须成对改"的纪律。 | 改模板, 改 CSS, 加挂件类, 改主题, 两套 UI, 白屏, 静默失效, 缓存, 过渡, 组件变体 |
| [vue-reactivity.md](vue-reactivity.md) | Vue Options API 的三类静默白屏(computed 当函数 / 带参 computed / 三者同名)与 SVG 属性大小写 —— 都**没有运行时提示**。 | 改前端模板, 改 computed, 改 methods, 改 SVG, 加图标, 白屏, 整块不渲染 |
