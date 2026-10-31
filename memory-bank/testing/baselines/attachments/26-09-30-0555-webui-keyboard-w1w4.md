# 基线 · 1802 passed + 3 skipped / 91% —— WEBUI 键盘快捷键 W1-W4 第一波 (引擎/光标/_actCore/A-D 绑定)

> 摘要: 计划 plans/26-09-28-0354 §06 波次 W1-W4 全量落地(2026-09-30) —— W1 引擎
> shared/shortcuts.js(e.code+固定修饰序归一化 / IME isComposing+229 双保险 / 输入元素三段屏蔽 /
> 模态层屏蔽 / repeat+纯修饰键+defaultPrevented 前置 / 浏览器保留键黑名单 / 适配器桩
> window.AQB_KEYS.load 内存实现, W6 换 GET/PUT /api/keys 引擎零改动); W2 光标模型(kbCursor
> 按身份不按下标, 辅种页组行/种子页平铺/追剧集单元线性链, 滚动进视口走 getBoundingClientRect
> 差值 + columns.js._rowWindow 留存 _rowPre 前缀和, **禁 scrollIntoView**); W3 commands.js 抽
> _actCore 统一动作出口(act/actTorrent/bulkAct/actEpisode 四入口全收敛, 端点按目标形态路由:
> 单组->组级 / 单种子->种子级 / 多目标与 recheck->bulk / reannounce 恒逐目标); W4 A-D 组 30 条
> 默认键位(数字切页 / 光标族 / Space+Shift+方向选择 / Ctrl+A / P S I M O / 危险档二键
> Shift+D/Y/A + 键盘路径 confirmDialog), Delete 键直连 _kbDelete->_deleteFlow(注册表外),
> 模态确认框默认焦点落「确定」钮(Enter 即确认, popovers.html ref=modalOk)。
> 危险档终版按 §08 v4: 删除 Shift+KeyD / 重新校验 Shift+KeyY / 强制汇报 Shift+KeyA, 裸键
> D/C/F 释放空位。基线时间: 2026-09-30 05:55 (develop @ da860d2) **未提交**(等用户显式指令)。

TOTAL **1802 passed + 3 skipped / 91%**(12587 语句 / 995 未覆盖 / 4240 分支 / 414 partial, test.full 24.4s, rc=0) ——
较上基线 26-09-30-0450(1792)增 10 条: 新文件 test_web_shortcuts.py(当波守阵: 注册表单一事实源 /
危险档二键组合+三条逐字钉住 / 默认键无冲突不碰黑名单 / run 成员存在 / 三 shell 挂载成对+Esc 链序 /
引擎六道拦截 / Delete 注册表外直连 / 危险档键盘确认框 / 模态默认焦点 / 光标滚动禁 scrollIntoView)。
另修复实施前既有红 3 条: 任务档案 Status「Ready」不在守阵词表(改 In Progress)+索引分区
+计划 doc-status 越词(改 In Progress) —— 计划会话遗留, 非本波改动。

## 浏览器功能验证(Playwright 探针, ui_harness 真前端, 30 项全过)

- W2 光标: ArrowDown/Home/End 落行+移动, 光标行挂 .kb-cursor; W4 Space 选中 / Ctrl+A 全选 /
  Esc 清选择(引擎不抢退栈链)。
- W4 动作: P 走组级端点整组乐观暂停; Shift+D/Delete/Shift+Delete 均弹删除确认框(正文含 HR
  汇报建议); Shift+Y 弹重新校验确认框, Enter 确认后 recheck 命令入队; Ctrl+, 开设置;
  Digit1/2/3 切三视图; Slash 聚焦搜索。
- 屏蔽: 搜索框内 p 入词不触发暂停(IME/输入态); 设置页 p 不串扰; Digit1 全局键在设置页可用。
- 冒烟对照: dev.harness 96 项与基线同败 3 项(追剧集行 CTX-03 / 辅种组行 CTX-03 抖动 / 隐藏列宽
  保留 —— stash 前后对照确认全部先在, 与本波改动无关), 其余 93 项含命令链/右键/乐观 UI 全绿,
  无 console.error / pageerror。

## 本轮改动面

- 新增 2: shared/shortcuts.js(引擎+注册表 55 条=51 默认+4 空位+适配器桩)、
  tests/test_web_shortcuts.py(当波守阵)。
- 接线 8: app.js(mixin)+ 三份 index.html(manifest 排 app.js 前)+ lifecycle.js(keydown 注册于
  Esc 链后+unmounted 撤除+_rowPre/_kbTableCache 缓存)+ state.js(kbCursor 根选项 data)+
  columns.js(_rowWindow 留存前缀和)+ console_hub.css(.kb-cursor)。
- 重构 3: commands.js(_actCore 抽取, _actionText 补 recheck)+ shows.js(actEpisode 薄包装)+
  dialogs.js(openMetaDialog 接受 {groupKeys,memberHashes} 目标对象, 键盘组行/剧集单元路径)。
- 模板 4: groups/torrents/shows 行挂 kb-cursor 绑定, shows 剧/集行补 data-key 锚点;
  popovers.html 确定钮 ref=modalOk。
- 与计划文字的两处偏差(已在档案记录): ①注册表 55 条而非 58 —— H2(面板 Esc)归 W6 面板自身
  不进注册表, I 组文件优先级 x4/按列排序不注册(0822 自评"需二层光标复杂度不划算/绑键不现实"),
  W6 做面板时再议; ②危险档确认框由模态默认焦点统一实现(Enter=确定钮原生激活), 无逐条新增接线。
