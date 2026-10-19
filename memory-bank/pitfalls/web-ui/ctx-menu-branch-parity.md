# 右键菜单分支项集漂移 (单组 vs 多选)

> 摘要: `shared/tpl/ctx-menus.html` 的右键菜单按上下文分四支, 其中 `menu.multi`(多选批量)与 `v-else`(单组)是**同一批动作的两条入口** —— 给一支加动作项时漏了另一支, 两条路径项集就静默分叉, 用户在某条路径上「找不到该动作」(不报错、不白屏, 纯"菜单里没这个选项")。
> 触发: 加右键菜单项, 改 ctx-menus.html, 单组菜单缺选项, 多选批量菜单, 项集不一致, 菜单缺项

**Refs:** memory-bank/tasks/26-10-09-webui-ctx-menu-group-actions.md

### 给批量分支加项时, 单组分支会静默落后

- **触发**: 给 `menu.multi`(多选批量)分支加菜单项 / 改其动作集。
- **判别**: 四分支里 `menu.multi` 与 `v-else`(单组)覆盖**同一批动作**的两条入口; 只在 `menu.multi` 加项, 单组路径就少那一项 —— 不报错、不白屏, 纯「菜单里没这个选项」。2026-10-09 用户报「辅种页单组右键菜单缺选项」: 计划 `26-10-02-1955` 给多选分支补 限速/移动/跳检/导出(另含 重新校验/标签分类)时, 单组分支停在旧项集(只有 开始/暂停/汇报 + 打开文件夹/流量图/删除)。
- **处置**:
  1. 给一支加动作, **同步补另一支**(组菜单独有的 打开文件夹/流量图 除外)。
  2. 组级入口**复用多选链路**(目标 = 该组全部成员, 走 `_groupTargets`, 下游交 `_actCore` / `_skipCheckDialog` / `_exportHashes` / `openMetaDialog`), **不另开旁路** —— 两处口径漂移的根都在"各写一套"。
  3. 目标取**成员 hash** 而非组 key: 组键在 `_bulkTargets` 口径里算 1 个目标, 单组场景会把「N 个目标」显示成「1 个目标」。
  4. 守阵 `test_frontend_ctx_menu_group_actions_parity`(`tests/test_webui_static_dom_panel.py`)钉单组支六入口(读注册表 `group` 支的 id 集)+ 跳检项 `gate` 字段 + 六入口复用多选下游链路 —— 再加/删单组项而不同步守阵即红。

### 根治后仍然会踩的三种"菜单里没有那一项"(2026-10-20)

- **触发**: 项集已收敛到注册表单点(计划 26-10-20-0024 W2/W3)之后, 仍然收到"某某菜单里没有某项"的报障。
- **判别**: 按下面顺序排, 前三种都**不是**注册表少项:
  1. **用户自己的布局**(最常见): `config.yml` 的 `web.ctx_menu` 里该项被 `hidden`, 或在 `sub.order`
     (被移进「更多操作」)里 —— 默认布局 ≠ 用户看到的布局。让他去设置页「WebUI」卡勾回来/移出来。
  2. **开关关着**: `web.skip_check_menu` 关闭时跳检项按设计不渲染(fail-closed), 菜单与 web 端点同口径;
     `flags.qb_traffic_enabled` 关闭时「qB 口径流量图」同理。
  3. **支判据不对**: 该支根本不是你以为的那一支(多选批量 vs 单组 vs 单种子 vs 整集整剧), 由
     `menu.multi/episode/hash/v-else` 决定 —— 用 `trigger-scope.spec.mjs` 的 T-1~T-5 矩阵对照。
  4. 以上都不是, 才是注册表真的少了: `CTX_ITEM_DEFS[支]` 里没有该 id。
- **处置**:
  1. 加项: 在注册表对应支加**一行**(`label` 是函数时必须同时给 `labelText` 静态名, 定制面板求不出
     动态文案); 要跨支一致就加到多支 —— 同一行定义被多处引用, 不再有两份文本可漏改。
  2. 模板不许回潮: `ctx-menus.html` 四支只能 `v-for` 消费 `ctxItems('<支>')` + `ctxRun(it)`,
     逐项 `@click="actTorrent(...)"` 直写由 `test_ctx_menu_template_consumes_registry` 拦下。
  3. 守阵比对面都读**注册表定义序**(组级奇偶六入口 / T4 动作族奇偶 / 批量分支成对), 模板文本
     token 断言在 v-for 化后没有意义 —— 改注册表要同步改这些断言。
  4. 面板写出的布局必须过后端校验: `test_ctx_custom_write_shape_passes_config_contract` 在 node 里
     跑真写路径再喂 `validate_config`(支级/次级键集合与 `_CTX_BRANCH_KEYS`/`_CTX_LAYER_KEYS` 对齐)。
