# WEBUI 键盘快捷键 · W1-W4 第一波已实施(引擎/光标/_actCore/A-D 绑定) → 待提交 + W5-W7 第二波

> 摘要: 计划 plans/26-09-28-0354 §06 W1-W4 全量落地(2026-09-30, 未提交)。**W1 引擎**
> shared/shortcuts.js: e.code+固定修饰序归一化 / IME isComposing+229 双保险 / 输入元素+模态层
> 屏蔽 / repeat+纯修饰键+defaultPrevented 前置 / 保留键黑名单 / 注册表单一事实源 / 适配器桩
> window.AQB_KEYS.load 内存实现(W6 换 GET/PUT /api/keys 引擎零改动)。**W2 光标**: kbCursor 按
> 身份不按下标(根选项 data), 滚动进视口 getBoundingClientRect 差值 + _rowWindow 留存 _rowPre
> 前缀和(**禁 scrollIntoView**)。**W3 统一出口**: commands._actCore, act/actTorrent/bulkAct/
> actEpisode 四入口收敛(端点按目标形态路由; recheck 恒 bulk; reannounce 恒逐目标)。
> **W4 绑定**: A-D 组 30 条默认键位(§08 v4 危险档二键 Shift+D/Y/A + 键盘路径 confirmDialog),
> Delete 直连 _kbDelete->_deleteFlow(注册表外), 模态确认框默认焦点「确定」(ref=modalOk,
> Enter 即确认)。守阵 tests/test_web_shortcuts.py 10 条; test.full 1802 passed / 91%;
> Playwright 探针 30 项功能验证全过。注册表落地 55 条(51 默认+4 空位), 与计划 58 的偏差见档案。
> 最后活动: 2026-09-30 05:55 (W1-W4 完成, 全量 1802 passed, 未提交)

## 正在进行

- **W1-W4 已完成待提交**(基线 [26-09-30-0555](../testing/baselines/26-09-30-0555-webui-keyboard-w1w4.md)); 改动面 22 文件: 新增 shortcuts.js + test_web_shortcuts.py, 接线 app.js/三 index.html/lifecycle/state/columns/console_hub.css, 重构 commands/shows/dialogs, 模板 groups/torrents/shows/popovers。
- 下一步: ①用户「提交」指令走 ship.commit; ②W5-W7 第二波(E-H 组接线 + 局部作用域 drawer/settings + Esc 链尾 + 后端 webui-keys.json + GET/PUT /api/keys + 金清单+2 + 自定义面板/录制器 + 收尾守阵/真机走查/文档回写), 开工前先 sync。
- 冒烟既有失败 3 项(先在, stash 对照确认, 已入池 26-09-30-0602-test-ui-smoke-ctx03-multiselect(前两条) 与 26-09-30-0602-test-ui-smoke-colwidth-hidden-preserve(第三条)): 追剧集行 CTX-03 多选右键(确定性) / 辅种组行 CTX-03(抖动) / 列设置隐藏列宽保留(确定性)。

## 关键决策

- 决策点① v4 终版 (2026-09-30 用户五轮拍板收敛): **无修饰单键为主, 单手操作优先**; 危险操作**一律二键组合** (一个修饰键+字母; 非裸键、非三键), 确认框兜底 (默认按钮「确定」, Enter 即确认): **删除 = Shift+D**, 且 **Delete 键保留为额外删除操作无需绑定** (直连 _deleteFlow) —— 删除共两个快捷键入口; **重新校验 = Shift+Y** (验; Shift+C 已被复制名称占), **强制汇报 = Shift+A** (reAnnounce; Shift+F 已被强制开始占); 裸键 D/C/F 释放为空位; 注册表 58 条 (52 默认+6 空位); 面板 danger 条目标「⚠ 危险操作 (有确认框)」, 自绑裸键提示但允许。
- 决策点③ (2026-09-30 用户拍板, 改向): Shift 族保留 (E 组 7 条 + Shift+T/F), 否决「本期砍掉」建议案。
- 决策点②④ (2026-09-30 用户拍板): 均按建议案 —— 组行线性链 / 不加顶栏按钮。
- 决策点⑤ (2026-09-30 用户拍板, 改向): 取消「W1-W7 一次做完」, 按原拆口 **W1-W4 第一波** (默认键位开箱即用, 含当波守阵, 可单独提交) + **W5-W7 第二波** (局部作用域 + 自定义面板 + 收尾)。
- 决策点⑥ (2026-09-30 用户拍板): 后端独立文件 webui-keys.json + GET/PUT /api/keys。
- 模板机制 (2026-09-30 用户确认): **缓议·仅预埋** —— 存储 schema 预埋 {schema_version, template, overrides} 派生形状 (§4.7), 生效表 = 模板 ⊕ overrides; 多模板切换/派生/导入导出预研可行 (+150-250 行, 导入导出零新增端点), 本期不做。
- 存储选后端独立文件的三个决定性证据: 成熟产品零 localStorage 先例(JupyterLab 服务端文件与本案最同构); 本项目列偏好已被浏览器清站点数据静默清空过(应用外失效通道实证); 快捷键是「用户录制的配置」信息价值错配 localStorage 档位, 而后端方案总成本仅 ~200 行含测试。
- 引擎不引库: 录制器/冲突/黑名单/作用域接线没有库覆盖, 活跃库的 keyCode 匹配与 e.code 设计相抵; tinykeys 源码是最佳细节参照。
- state.json 不可用: 黄金法则 5 主循环单写线程, web 线程保存快捷键必须走独立文件(web.token 同寻址先例); config.yml 红线排除。
- 跨标签语义明示「刷新后生效」, 与 config 保存既有语义一致; 混合镜像(后端真值+localStorage 缓存)缓议, 适配器 AQB_KEYS.load/save 单点保后路。
