# webui-qb-traffic-head-layout — 流量图版式改(控件上提头部 + 图例并入统计栏)

> 摘要: 用户报「流量图被其它元素占用了高度, 主要信息(图本身)被压缩」。拍板四条: ①时间档位(13 档)
> 与纵轴设置自正文工具条**上提到「qB流量图」头部标题栏**; ②两处注释(正文工具条「qB 口径 · 程序
> 运行期间…」+ 图下行「…· 悬停查看详情」)**全部移除**; ③上行/下行图例**并入统计栏**(窗口 N 桶
> 之前); ④统计栏与状态栏间距减小。标题缩短为「qB流量图」。**只改经典 UI**, `shared/drawer_tpl/`
> 15 个变体零改动。三挂点(全局/分组/单种)共用头部/正文, 同改全生效。已闭环。
> 最后活动: 2026-10-08 07:13

**Refs:** memory-bank/tasks/26-10-08-webui-qb-traffic-head-layout.md,memory-bank/testing/baselines/26-10-08-0713-webui-qb-traffic-head-layout.md

- 任务档案: [26-10-08-webui-qb-traffic-head-layout](../tasks/26-10-08-webui-qb-traffic-head-layout.md) —— 拍板记录、改动面、关键判据与实测数字都在档案, 本切片只留指针。
- 落地(纯前端静态层 + 测试侧, Python 产品代码零改动): `shared/tpl/drawer.html` 流量形态头部插入 `.qb-tabs`(13 档)+ `.qb-tools`(纵轴三态/手动输入/上限读数), 正文删 `.drawer-toolbar` 与 `.qb-tools` 与独立 `.hist-legend`, 统计栏首部加 `.hs-leg`(上/下行图例); `qb_traffic_chart.js` `qbTrafficTitle` 全局标题改 `"qB流量图"`; 三皮肤 `views.css` 新增 `.hs-leg` + 头部 `:has(> .qb-tabs)` 换行/不收缩规则 + `.hist-summary` 间距 10→6px。
- 关键判据(易被后人改坏): 控件落点=头部标题栏(挪回正文即压缩图高 = 本改动被回退); 独立 `.hist-legend` 行在本面板**必须不存在**(历史流量弹层 popovers.html 仍用, 属另一处); 头部仍 44px 未新增行(真浏览器实测)。
- 实测: test.full **2772 passed + 4 skipped / 0 failed / 34.76s / TOTAL 99%**(基线切片 [26-10-08-0713](../testing/baselines/26-10-08-0713-webui-qb-traffic-head-layout.md), 相对上基线 passed ±0 —— 只改断言口径未新增测试函数); 旁证真浏览器三皮肤目检: 头部 44px / 图 266px(吃满余量) / 统计栏贴面板底缘 / 零 pageerror / `.hist-legend` 计数 0 而 `.hs-leg` 计数 2。
- 未验证面: 窄视口(≤900px)头部换行的逐档观感未走查(规则已写, 靠 `:has` + `flex-wrap` 抗挤压); 面板默认高度语义(42vh)未动 —— 本次只把正文占用的高度还给图。
