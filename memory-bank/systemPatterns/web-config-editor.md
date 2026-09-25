# WEB UI 图形化配置编辑

> 摘要: `web.py` + `config/schema.py` + `config/writer.py` 三件套的分工。
> ⚠ **2026-09-22 方案 C 目录迁移已落地**: 文内单文件路径为迁移前快照 —— 旧根平铺 8 文件+mixins/ → `core(/mixins)/`, 6 个基础设施 → `infra/`, web_runtime/web/web_ui/ui → `webui/{runtime,server,static}`/`tray/`; 映射总表见 [overview.md](overview.md)。
> 触发: 图形化配置, 设置页, schema, writer, 配置树

## WEB UI 图形化配置编辑 (web.py + config/schema.py + config/writer.py, 2026-09-14)

- **模式**: 设置页不再直接编辑 YAML 全文 —— 每个配置项经图形控件增删改。(2026-09-25 注: 旧版「只读 YAML 预览」按钮随经典设置页移除, `POST /api/config/preview` 端点仍在但前端已无调用方。)
- **数据模型**: 前端持有与磁盘**同构的 YAML 树**(标量全为字符串, 与 `yaml.BaseLoader` 语义一致) → 编辑即就地增删改, 无格式往返转换、零语义漂移; 脏检测用 JSON 快照对比。
- **端点**: `GET /api/config/schema`(UI 元数据 + `impact` 的热重载级别表合并)、`GET /api/config`(树)、`PUT /api/config`(保存)、`POST /api/config/preview`(只读预览; 2026-09-25 起前端无调用方)。旧的 `GET/PUT /api/config/raw` 已移除。
- **保存管线 (config/writer.py)**: 结构自检(必须有 `config` 根段) → 落临时文件跑 `load_config`(与启动同一校验路径, 失败 400 且不碰磁盘) → `diff_config_impacts` 判定变更 → **R 级字段回退为磁盘旧值** → 备份到 **`<data_dir>/<配置名>.bak`**(备份路径由调用方传入, 不再在项目根目录产生 `config.yml.bak`; 父目录按需创建) → ruamel round-trip 写盘 → 投递 `reload_config` 命令(仍由主循环线程应用)。
- **注释与格式策略**: 已存在键的注释保留(`_sync_mapping` 递归同步 CommentedMap); **值未变化的键跳过赋值**, 从而保留磁盘原标量形态(否则 ruamel 会把无引号的 `16585`/`true` 重写为 `'16585'`/`'true'`); 新增/修改的标量走 `_plain_scalar`(数字/布尔样式写成原生标量, BaseLoader 下语义等价); **列表整体替换(项级注释不保留)**。
- **schema.py 的地位**: 纯声明的 UI 元数据(分组/字段/控件类型/单位/枚举/帮助/必填/可选段/插件 spec 表), **不承载正确性规则**(合法性唯一入口仍是 `validate_config`); 键集合与插件表由 `tests/test_config_schema.py` 守卫 —— 新增配置键或插件忘登记会直接测试失败。
- **前端结构(2026-09-25 更新)**: `config_editor.js`(加载保存/路径读写/列表与开关/站点与曲线专段读写) + `config_rules.js`(规则集与 16 条件/12 动作的 spec 编辑) + `config_hub.js`(Console Hub 视图状态/首页卡片/就近说明浮窗) 作为 Vue 全局 mixin 注入 `app.js` 的根实例; 字段渲染单点在 `hub-field` 组件(由 `CE_FIELD_COMPONENT` 派生, 经 `provide/inject` 复用根的 `cfg*` 方法) —— 嵌套 object 在 `cfgFlatten` 阶段扁平化为带缩进的渲染项, 因此组件**无需递归**。`config_editor.js` 里的分组导航/预览等方法已随经典页删除; `ce-field` 不再被任何模板直接挂载(仅作 hub-field 的方法基座)。
- **设置页只剩 Console Hub 一套(2026-09-25)**: 经典设置页整块移除(两套并存期 2026-09-21 ~ 2026-09-25, 曾由 `localStorage autoqb.settings.hub` 切换) —— 现在 `page==='settings'` 只渲染 `<main class="ce-page hub-page">`, 编辑能力仍**全部复用既有 `cfg*` 读写**(同一棵 YAML 树、同一套脏检测与保存)。HR 站点状态不再单列卡片/章节: 只读的「站点状态」块并入「HR 在线核实」分区页尾, 打开分区时拉一次 `/api/hr/status`、之后手动刷新。
- **UI 元数据扩展(2026-09-14 视觉打磨)**: `Field.icon`/`Group.icon`(侧栏与标题图标, sprite symbol id)、`Field.risk`(高风险项: 标签处盾牌徽标 + 控件下方醒目风险行)、`Field.grey_if=(同段键, 期望值)`(所属功能未启用时**灰显但仍可编辑**; 期望值按“配置值 else schema 默认值”判定, 故未显式配置的 `enabled: false` 也能正确判灰)、`Field.group_of=<父字段键>`(相关设置**子卡**: 前端在父字段之后渲染一张缩进小卡容纳该键, YAML 形状不变)。`Group.icon` 在侧栏与页头同时生效。
- **规则卡与添加交互(2026-09-14)**: 规则卡头固定(折叠仍可见名称/摘要/启用开关), 条件/动作按序号强调执行顺序且各自带说明; 新增条件/动作用**平铺选择面板**(`.ce-picker`, 每项带 help, 高风险项标 risk)替代裸下拉; "新增站点/规则集/规则"用图标(站点与规则集的 **+ 移到各自列表标题行**, 规则用 `ce-sub-head` 行)就地展开输入框(自动聚焦, Enter 确认 / Esc 取消); 限速曲线每条一张卡: 周期 + 上/下行分区(阶梯图预览 + 档位表), 图表由**前端**解析 `10GiB`/`6MiB/s` 的展示值绘制(解析失败只告警不阻断, 合法性仍归后端)。
- **设置页表单结构(2026-09-14 视觉重做)**: ①**可选段(optional object)渲染为默认折叠的 `section`** —— 折叠态一行(折叠箭头 + 写入开关 + 段名 + `已配置 n/m 项` 摘要), 展开才显示内部字段; 这与旧的"开关 + 子字段平铺"区别在于子字段**嵌套在 section 内**(因此 ce-field 会递归渲染, 与 subcard 同机制)。②**布尔型从属项(如 `add_category` 的"覆盖已有分类")改为父字段的**内联开关**(`ce-field` 标签右侧), 因为一个开关单独占一张子卡比父字段本身还显眼; 其余从属项仍走 `group_of` 子卡。③**普通 object 段的子字段不额外缩进**(旧版 `depth+1` 导致同页两组输入框左缘错 16px)。④`overwrite*` 类不再有 subcard。
- **折线图(2026-09-14 重做)**: 几何由 `config_editor._buildCurveChart(i, dir)` 计算(560×210, 留出左/下轴标签空间), 输出 line/area/**xTicks/yTicks**/`padL..padB`/`spanT`/`maxS`/`points`; 模板用 `v-for="ch in [cfgCurveChartOf(i,dir)]"` 做别名渲染(避免重复写十几次取值); **鼠标 `mousemove` → `cfgChartHover` 把像素位置反算回 (累计流量, 限速)** 并按阶梯语义(阈值=区间上限)定位到具体档位, 显十字线 + 标记点 + tooltip(靠右时 `.flip` 向左翻, 不溢出)。
