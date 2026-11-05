# 浏览器冒烟 · 归因与真实手势前置条件(外迁)

> 摘要: `pitfalls/testing/smoke.md` 三条原文整体外迁(2026-11-05 压缩): elementHandle.click 超时的 stash 对照、真实手势被拖拽收尾/离场动画吞掉、回归第一嫌疑是验错对象。正文原样照搬, 标题降一级以避开坑档条目扫描。
> 触发: elementHandle.click 超时, stash 对照, 归因, 存量 flaky, 拖拽 swallow, 离场动画, ctx-menu, 验错对象, 旧页签, Ctrl+F5

## 「冒烟整体执行 — elementHandle.click: Timeout」≠ 桩没起来 —— 归因先做 HEAD stash 对照

- **触发**: 双皮肤冒烟在同一用例位置报 `冒烟整体执行 — elementHandle.click: Timeout 30000ms exceeded`
  (2026-10-03 实测: 追剧集行 Ctrl+click 块, position {8,8} 落点被 `sticky-head`/`header.topbar`/`html`
  交替拦截, Playwright 重试 30s 耗尽; 3 轮双皮肤 + HEAD 对照 4/4 复现)。
- **判别**: 与上一条「桩没起来」**同名词不同因** —— 上一条卡在首条 waitForFunction(页面根本没渲染,
  症状像白屏); 本条页面全程活着、断言一路 PASS 到超时点(看最后一条 PASS 在哪即知中断位置)。
  是否存量: 把自己的脚本改动 `git stash push -- <脚本>` → 跑一轮 → `git stash pop`,
  HEAD 同位置同报错即与本轮改动无关(实测 stash 前后失败点逐字一致)。
- **处置**: ①先跑对照再动代码 —— 命中存量 flaky 不顺手修, 记录位置与签名即可;
  ②超时中断该皮肤后续断言(含末尾 console.error 总检), 汇报写"中断点之前全部通过"而不是"冒烟全绿"。
  本条暂无守阵(点击拦截面随布局漂移, 静态判不出)。
  复发: 1 —— HR 历史表③ 同位置同签名 3/3 复现, 按本条目做 HEAD 档案对照 4/4 实锤存量;
  按既有处置口径①绕行未修(命中存量不顺手修, 只记位置与签名)。

## 真实手势的前置条件: 拖拽收尾会吞掉紧随的 click / 浮层离场动画期间仍拦截点击

- **触发**: 在真浏览器里连做多个手势的用例(如"拖拽重排 → 右键 → 菜单里点一项"; "右键开菜单 →
  Escape → 拖宽"), 计划 26-10-11-1722 P1/P2 的表头四项交互取证实测。
- **判别**: 两个**假红**形态, 症状都像"改造把功能弄坏了":
  ① **拖拽收尾的 swallow**: `columns.js::startColDrag`/`startResize` 的 `up` 里会装一个
     **capture 阶段** `click` 监听(`swallow`)吃掉紧随的一次 click(防"调列宽/拖重排顺手触发排序",
     既有设计)。它只吃**一次**, 但会吃掉**下一个动作**的那次 click ⇒ 表现为"右键菜单点了没反应 /
     表头点了不排序", 而产品完全正常。
  ② **离场动画期的拦截**: 浮层是 `<transition name="pop">` 包裹的, `v-if` 置假后元素**要等离场动画
     结束才摘除** —— 期间它仍在文档流上盖住底下的表头。实测 `document.elementFromPoint(表头坐标)`
     返回 `DIV.ctx-menu pop-leave-active`: 此时按表头坐标 `mouse.down()` 落在**菜单**上, 拖宽静默
     不生效(`colW.show` 恒空), 不报错。
- **处置**: ①含拖拽的用例把**拖拽放到最后**, 或在拖拽后先做一次无关 click 把 swallow 消费掉;
  ②Escape 关浮层后**等元素真的摘除**再对底下元素做手势 —— `await expect.poll(() => page.locator('.ctx-menu').count()).toBe(0)`,
  别只等 `vm.headMenu.visible === false`(状态已假、DOM 还在)。排障时 `elementFromPoint` 是首选仪器:
  一眼看出"落点被谁接走了"。
- **复发**: 0

## 「回归」的第一嫌疑是验错对象: 旧桩进程 / 旧页签跑的是旧资源

- **触发**: 报「某个已修缺陷回归了」, 且带皮肤/页面差异(如「prism 正常, atlas 异常」)。2026-10-29 七修
  排查现场就是这一形态: 六修已全绿, 用户侧却稳定复现「无焦点点下拉即弹回」。
- **判别**: 先核对**服务端现在发的是什么字节**与**进程是否还活着**, 再谈代码 ——
  ① `curl -s --noproxy '*' -o /dev/null -w "%{http_code}" http://127.0.0.1:<启动行实端口>/atlas/` 返回 `000`
     (连接被拒)⇒ 那份桩早就死了, 用户测的不是它(旧进程 / 别的 clone / 旧页签);
  ② `curl -s .../shared/tpl/combo-input.html | grep -c "@mousedown.prevent"`、`.../atlas/css/dialogs.css |
     grep -c ":has(.add-pop)"` ⇒ 直接证明"服务端发的是不是当前代码", 比问「你刷新了吗」有效得多;
  ③ SPA 的模板与 JS 以**页面加载时刻**为准(boot.js fetch 注入), 页签长开不刷新 = 永远跑旧资源; 按皮肤
     分页签时极易只刷了一个(prism 刷了 / atlas 没刷)⇒ 看起来像**皮肤差异**, 实际是**页签代际差异**。
- **处置**: 复现与验收固定三步 —— 起**新**桩(并用 `run_in_background` 常驻, 不要 `&` 脱离: shell 退出
  进程就被回收, 上一份桩就是这么静默死掉的) → 核对发出的字节 → **两个皮肤都 Ctrl+F5**。同一份代码在
  12 条交互序列 × 5 种视口 × headless/headed 下全绿而用户侧稳定复现 ⇒ 先怀疑对象, 别先改代码。
- **复发**: 1(2026-10-29: 上一轮 8099 桩进程已死, 用户对着它测出「回归」; 换新进程 + 强刷后不复现)
